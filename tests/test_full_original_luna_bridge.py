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
        "RapidOCR(", "ImageGrab.grab", "cv2.", "OcrDetect(", "BitBlt("))
    )
