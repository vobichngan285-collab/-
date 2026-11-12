"""The full Luna original integration is I/O only.

Tests validate only coordinate and command boundaries, not rewritten OCR logic.
"""
from __future__ import annotations

from queue import Queue
from types import SimpleNamespace
import threading
import json

import pytest

from game_reader import luna_original_bridge as bridge
from game_reader.core import OCRLine


def test_original_luna_quadrilateral_coordinates_are_preserved():
    parsed = {"results": [
        {"text": "继续游戏", "box": [
            {"x": 11.5, "y": 21}, {"x": 131.5, "y": 21},
            {"x": 131.5, "y": 45}, {"x": 11.5, "y": 45}
        ]},
        {"text": "玩家档案", "box": [
            {"x": 20, "y": 55}, {"x": 102, "y": 55},
            {"x": 102, "y": 81}, {"x": 20, "y": 81}
        ]}
    ]}
    lines = bridge._convert_original_boxes(parsed, (100, 200, 400, 400))
    assert [x.text for x in lines] == ["继续游戏", "玩家档案"]
    assert (lines[0].left, lines[0].top, lines[0].right, lines[0].bottom) == (111, 221, 232, 245)
    assert (lines[1].left, lines[1].top) == (120, 255)


def test_original_luna_client_issues_ocr_request_only(monkeypatch):
    engine = bridge.LunaOriginalOCR()
    requests = []
    def invoke(action, **kw):
        requests.append((action, kw))
        return {"ok": True, "result": {"results": [
            {"text": "DLSS", "box": [
                {"x": 1, "y": 3}, {"x": 91, "y": 3},
                {"x": 91, "y": 25}, {"x": 1, "y": 25}]}
        ]}}
    monkeypatch.setattr(engine, "_call", invoke)
    lines = engine.recognize_box((30, 40, 260, 140))
    assert requests == [("ocr", {"box": [30, 40, 260, 140], "timeout": 25})]
    assert [(x.text, x.left, x.top, x.right, x.bottom) for x in lines] == [
        ("DLSS", 31, 43, 121, 65)]
    engine.close()


def test_original_region_setup_calls_author_in_order_and_preserves_border(monkeypatch):
    engine = bridge.LunaOriginalOCR()
    actions = []
    monkeypatch.setattr(engine, "_call", lambda action, **kw: (
        actions.append((action, kw)) or {"ok": True}
    ))
    engine.request_region((12, 13, 330, 240), visible=False)
    assert [x[0] for x in actions] == ["region", "border", "resume"]
    assert actions[1][1]["visible"] is False
    engine.close()


def test_original_plugin_must_not_implement_ocr_algorithms():
    # Do not accidentally regress to the partial-copy approach.
    from pathlib import Path
    plugin = Path(__file__).resolve().parents[1] / "experiments/luna_original_full/bluestar_outputer.py"
    text = plugin.read_text(encoding="utf-8")
    assert "from textio.textsource.ocrtext import imageCutEx" in text
    assert "from myutils.ocrutil import ocr_run" in text
    assert "source.newrangeadjustor()" in text
    assert "source.setrect(QRect" in text
    assert not any(term in text for term in (
        "RapidOCR(", "ImageGrab.grab", "cv2.", "OcrDetect(", "BitBlt("
    ))


def test_original_hud_does_not_reappear_when_f7_shows_blue_star_frame():
    """Only original UI/Qt bridges change; original OCR algorithms are untouched."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    plugin = (root / "experiments/luna_original_full/bluestar_outputer.py").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/build-windows-luna-original.yml").read_text(encoding="utf-8")
    assert 'source.showhiderangeui(False)' in plugin
    assert 'ui.hide_()' in plugin
    assert 'source.showhiderangeui(bool(payload["visible"]))' not in plugin
    assert "$defaults['startupautohide'] = $true" in workflow
    assert "$defaults['ocr_auto_method_v2'] = 'period'" in workflow
    assert "$defaults['ocr_interval'] = 0.4" in workflow
    assert "$defaults['multiregion'] = $true" in workflow
    assert "$defaults['ocr_text_diff'] = 1" in workflow
    assert "$defaults['ocrmergelines'] = $false" in workflow
    assert "install_official_v6small.py" in workflow
    assert "'model'] = 'PP-OCRv6_small'" in workflow
    assert "'gpu'] = $true" in workflow
    assert "'thread'] = 4" in workflow
    assert "$defaults['ocr_translation_overlay'] = $false" in workflow
    # Do not change the author's expensive GDI/similarity/inference source.
    assert "from textio.textsource.ocrtext import imageCutEx" in plugin
    assert "from myutils.ocrutil import ocr_run" in plugin



def test_pinned_game_hwnd_reaches_unmodified_luna_capture(monkeypatch):
    engine = bridge.LunaOriginalOCR()
    observed = []
    def invoke(action, **kw):
        observed.append((action, kw))
        return {"ok": True, "result": {"results": [
            {"text": "返回游戏", "box": [
                {"x": 10, "y": 10}, {"x": 110, "y": 10},
                {"x": 110, "y": 32}, {"x": 10, "y": 32}]}]}}
    monkeypatch.setattr(engine, "_call", invoke)
    rows = engine.recognize_box((400, 100, 700, 500), hwnd=1234567)
    assert observed == [("ocr", {"box": [400, 100, 700, 500],
                                 "timeout": 25, "hwnd": 1234567})]
    assert rows[0] == OCRLine("返回游戏", 410, 110, 510, 132, 1.0)
    engine.close()


def test_game_pointer_rows_remain_independent_after_native_ocr():
    from game_reader.core import keep_detected_rows, hit_test, build_reading_regions
    native = [
        OCRLine("继续向前行驶，直到看到下一个路口为止", 30, 76, 350, 102),
        OCRLine("你现在位于城市的中心区域，请注意安全", 30, 40, 348, 66),
        OCRLine("继续游戏", 30, 145, 170, 169),
    ]
    # Old paragraph fusion put both long rows in a combined rectangle.
    assert len(build_reading_regions(native)) == 2
    rows = keep_detected_rows(native)
    assert len(rows) == 3
    assert [line.top for line in rows] == [40, 76, 145]
    assert hit_test(rows, 70, 50).text == native[1].text
    assert hit_test(rows, 70, 85).text == native[0].text
    assert hit_test(rows, 70, 155).text == "继续游戏"


def test_repaired_runtime_disables_native_line_merge_and_uses_hwnd():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github/workflows/build-windows-luna-original.yml").read_text(encoding="utf-8")
    plugin = (root / "experiments/luna_original_full/bluestar_outputer.py").read_text(encoding="utf-8")
    app = (root / "game_reader/app.py").read_text(encoding="utf-8")
    assert "$defaults['ocrmergelines'] = $false" in workflow
    assert "$defaults['ocr_text_diff'] = 1" in workflow
    assert "imageCutEx(hwnd, QRect(" in plugin
    assert "recognize_box(box, hwnd=game_hwnd)" in app
    assert "self.lines = keep_detected_rows(lines)" in app
