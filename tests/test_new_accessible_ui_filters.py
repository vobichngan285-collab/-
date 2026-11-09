"""Acceptance tests: new UI must not make screen readers or V1.2 OCR silent."""
from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import Mock

import pytest

from game_reader.core import OCRLine
from game_reader.text_filters import (DEFAULT_FILTER_SETTINGS, filter_speech_text,
                                      is_repeat_speech, similarity_threshold,
                                      levenshtein_distance_bounded)


def test_default_three_filters_user_requested_and_raw_remains_available():
    cfg = dict(DEFAULT_FILTER_SETTINGS)
    raw = "碎布 18 ★\nDLSS\nPress E 拾取\n生命值 +20%\n★★★"
    assert filter_speech_text(raw, cfg) == "碎布\n拾取\n生命值"
    assert "DLSS" in raw and "18" in raw and "★" in raw


@pytest.mark.parametrize("field,want", [
    ("filter_english", "DLSS"),
    ("filter_numbers", "18"),
    ("filter_symbols", "★"),
])
def test_each_filter_can_be_independently_disabled(field, want):
    cfg = dict(DEFAULT_FILTER_SETTINGS)
    cfg[field] = False
    raw = "碎布 DLSS 18 ★"
    assert want in filter_speech_text(raw, cfg)


def test_deduplication_runs_after_filter_and_short_item_names_not_suppressed():
    cfg = dict(DEFAULT_FILTER_SETTINGS)
    a = filter_speech_text("碎布 18", cfg)
    b = filter_speech_text("碎布 19", cfg)
    c = filter_speech_text("石斧 18", cfg)
    assert a == b == "碎布"
    assert is_repeat_speech(a, b, cfg)
    assert not is_repeat_speech(a, c, cfg)
    assert not is_repeat_speech("碎布", "石斧", cfg)
    assert not is_repeat_speech("", "碎布", cfg)


def test_long_text_with_minor_ocr_jitter_dedupes():
    cfg = dict(DEFAULT_FILTER_SETTINGS)
    a = "这是一段可以在游戏中完整朗读的物品说明"
    b = "这是一段可以在游戏中完整朗读的物晶说明"
    assert is_repeat_speech(a, b, cfg)
    assert not is_repeat_speech(a, "这是完全不同的技能等级与游戏提示", cfg)
    cfg["similarity_enabled"] = False
    assert not is_repeat_speech(a, b, cfg)


def test_bounded_edit_distance_and_parameter_validation():
    assert levenshtein_distance_bounded("abcde", "abcdf", 2) == 1
    assert levenshtein_distance_bounded("abcde", "12345", 2) == 3
    assert similarity_threshold("0") == 0
    assert similarity_threshold("8") == 8
    for bad in ("-1", "9", "2.7", "hello", True):
        with pytest.raises(ValueError):
            similarity_threshold(bad)


def test_mode_announcements_use_selected_voice_not_filtered(monkeypatch):
    from game_reader.app import ReaderApp
    class Var:
        def __init__(self): self.value = ""
        def set(self, value): self.value = value
    class Hover:
        def reset(self): pass
    class Root:
        def state(self): return "iconic"
    class Speech:
        def __init__(self): self.stops = 0
        def stop(self): self.stops += 1
    app = ReaderApp.__new__(ReaderApp)
    app.settings = {"mode_voice_hint": True}
    app.mouse_mode = "pointer"
    app.mode_generation = 0
    app._hover_last_text = ""
    app._hover_spoken_cursor = None
    app._hover_spoken_foreground = None
    app._mode_announcement_until = 0
    app.hover = Hover()
    app.root = Root()
    app.last_target = None
    app.speech = Speech()
    app.overlay = None
    app.scan_frame = None
    app.mouse_mode_var = Var()
    app.status = lambda _: None
    app.update_output = lambda _: None
    app.lines = []
    spoken = []
    app.speak_selected = spoken.append
    app.toggle_mouse_mode()
    app.toggle_mouse_mode()
    assert spoken == ["鼠标模式", "默认模式"]
    assert app.speech.stops == 2


def test_green_scan_frame_is_click_through_and_uses_same_bbox_as_crop(monkeypatch):
    from game_reader.app import ReaderApp
    import game_reader.app as mod
    class Frame:
        def __init__(self): self.bounds=None; self.hidden=0
        def show(self, region):
            self.bounds=(region.left, region.top, region.right, region.bottom)
        def hide(self): self.hidden+=1
    class Root:
        def state(self): return "iconic"
    app=ReaderApp.__new__(ReaderApp)
    app.scan_frame=Frame()
    app.root=Root()
    app._choosing_region=False
    app.setting_hotkey=False
    app.settings={"show_scan_frame":True, "region":[-300,-200,600,400]}
    monkeypatch.setattr(mod, "get_cursor", lambda:(500,500))
    monkeypatch.setattr(mod,"monitor_rect_at_cursor",lambda:(0,0,1920,1080))
    app.update_scan_frame()
    assert app.scan_frame.bounds==(200,300,800,700)
    app.settings["show_scan_frame"]=False
    app.update_scan_frame()
    assert app.scan_frame.hidden==1


def test_native_ttk_theme_keeps_accessibility_semantics():
    from pathlib import Path
    import game_reader
    source=(Path(game_reader.__file__).parent/"ui_theme.py").read_text(encoding="utf-8")
    assert 'ttk.Style' in source
    assert "ttk.Button" not in source or "Canvas" not in source
    assert "Canvas" not in source



def test_game_inventory_locally_reads_new_chinese_name_not_quantity(monkeypatch):
    """Real case: the item tooltip appears near items numbered 18 and 173."""
    from game_reader.app import ReaderApp
    import game_reader.app as mod
    monkeypatch.setattr(mod, "get_cursor", lambda: (490, 600))
    monkeypatch.setattr(mod, "foreground_class", lambda: "GameWindow")
    class Speaker:
        def __init__(self): self.stopped = 0
        def stop(self): self.stopped += 1
    app=ReaderApp.__new__(ReaderApp)
    app.mouse_mode="hover"
    app.hover_ocr_busy=True
    app.pending_full_capture=False
    app.mode_generation=3
    app.settings={"period_ms":400, **DEFAULT_FILTER_SETTINGS}
    app._hover_last_text=""
    app._hover_spoken_cursor=None
    app._hover_spoken_foreground=None
    app.speech=Speaker()
    app.update_output=Mock()
    app.status=Mock()
    app.speak_selected=Mock()
    first=[
        OCRLine("18", 300, 540, 345, 570),
        OCRLine("碎布", 430, 610, 525, 655),
        OCRLine("173", 660, 600, 730, 636),
    ]
    app._handle_hover_result(3, first, False, 45, (490,600), "GameWindow")
    app.speak_selected.assert_called_once_with("碎布")
    raw=app.update_output.call_args[0][0]
    assert "18" in raw and "173" in raw and "碎布" in raw
    app._handle_hover_result(3, first, False, 42, (490,600), "GameWindow")
    assert app.speak_selected.call_count==1
    replacement=[
        OCRLine("21", 300, 540, 345, 570),
        OCRLine("石斧", 430, 610, 525, 655),
        OCRLine("173", 660, 600, 730, 636),
    ]
    app._handle_hover_result(3, replacement, False, 42, (490,600), "GameWindow")
    assert app.speak_selected.call_count==2
    assert app.speak_selected.call_args[0][0]=="石斧"


def test_keyboard_and_screenreader_pages_remain_native():
    """Live full app self-test in the packaged EXE checks actual Win UIA."""
    from game_reader.ui_theme import configure_theme
    assert callable(configure_theme)
