"""Version 2.0: only speed level UI and hover-only text filtering.

Do not change OCR detection, screenshot logic, keyboard or mouse bindings.
"""
from __future__ import annotations

import json
from queue import Queue
from threading import Condition, RLock
from types import SimpleNamespace

import pytest

from game_reader.app import (ReaderApp, DEFAULTS, speech_rate_for_level,
                             level_for_speech_rate)
from game_reader.core import OCRLine, HoverTracker
from game_reader.hover_modes import HOTKEY_FIELDS
from game_reader.luna_bridge import LunaNaturalBridge


def test_new_speed_levels_preserve_old_range_and_expand_max_by_half():
    assert [speech_rate_for_level(i) for i in range(11)] == [
        -8, -6, -4, -2, 0, 2, 4, 6, 8, 10, 12]
    assert level_for_speech_rate(-8) == 0
    assert level_for_speech_rate(0) == 4
    assert level_for_speech_rate(8) == 8
    assert speech_rate_for_level(10) == 12


def test_saved_legacy_speech_speed_migrates_without_touching_voice_or_hotkeys(tmp_path, monkeypatch):
    import game_reader.app as module
    path = tmp_path / "settings.json"
    monkeypatch.setattr(module, "CONFIG_PATH", path)
    path.write_text(json.dumps({"rate": 8, "voice": "natural:myvoice", "vk": 119,
                                "mode_vk": 120, "pick_vk": 122}), encoding="utf-8")
    cfg = module.read_settings()
    assert cfg["rate_level"] == 8 and cfg["rate"] == 8
    assert cfg["voice"] == "natural:myvoice"
    assert cfg["vk"] == 119 and cfg["mode_vk"] == 120 and cfg["pick_vk"] == 122
    path.write_text(json.dumps({"rate_level": 10, "rate": 8}), encoding="utf-8")
    cfg = module.read_settings()
    assert cfg["rate_level"] == 10 and cfg["rate"] == 12
    path.write_text(json.dumps({"rate": 0}), encoding="utf-8")
    cfg = module.read_settings()
    assert cfg["rate_level"] == 4 and cfg["rate"] == 0


def test_natural_voice_bridge_allows_new_upper_rate_without_altering_synthesis():
    bridge = LunaNaturalBridge.__new__(LunaNaturalBridge)
    bridge._condition = Condition(RLock())
    bridge.rate = 0
    bridge.set_rate(12)
    assert bridge.rate == 12
    bridge.set_rate(99)
    assert bridge.rate == 12
    bridge.set_rate(-99)
    assert bridge.rate == -8


def test_fullscreen_result_chime_never_dropped_by_english_numeric_filters():
    app = ReaderApp.__new__(ReaderApp)
    app.events = Queue()
    app.capture_id = 7
    app.busy = True
    app.read_btn = SimpleNamespace(configure=lambda **_: None)
    app.lines = []
    app._full_capture_window = None
    app.hover = SimpleNamespace(reset=lambda: None)
    app.last_target = None
    app.expires_at = None
    app.mouse_mode = "pointer"
    app.settings = {**DEFAULTS, "filter_english": True,
                    "filter_numbers": True, "filter_symbols": True}
    played = []
    app.cues = SimpleNamespace(play=played.append)
    output = []
    app.update_output = output.append
    app.status = lambda _: None
    app.root = SimpleNamespace(after=lambda *args: None)
    app.events.put(("ocr_ok", 7, [OCRLine("Press 18 +", 1, 2, 200, 80)], 30, 100))
    app.poll_messages()
    assert played == ["complete"]
    assert "Press 18 +" in output[-1]


def test_pointer_mouse_reading_preserves_english_numbers_and_symbols(monkeypatch):
    import game_reader.app as module
    monkeypatch.setattr(module, "is_key_down", lambda vk: False)
    monkeypatch.setattr(module, "foreground_window_id", lambda: 100)
    monkeypatch.setattr(module, "get_cursor", lambda: (30, 20))
    app = ReaderApp.__new__(ReaderApp)
    app.closed = False
    app.setting_hotkey = False
    app._choosing_region = False
    app._hotkey_previous = {f: False for f in HOTKEY_FIELDS}
    app.wheel_listener = None
    app.root = SimpleNamespace(state=lambda: "iconic", after=lambda *args: None)
    app.settings = {**DEFAULTS, "filter_english": True,
                    "filter_numbers": True, "filter_symbols": True}
    app.lines = [OCRLine("Press 18 +", 1, 2, 200, 80)]
    app.mouse_mode = "pointer"
    app.busy = False
    app.expires_at = None
    app._full_capture_window = 100
    app._mode_announcement_until = 0.0
    app.last_target = None
    app.overlay = None
    app.hover = HoverTracker(0)
    app.speech = SimpleNamespace(stop=lambda: None)
    app.status = lambda _: None
    spoken = []
    app.speak_selected = spoken.append
    app.poll_input()
    assert spoken == ["Press 18 +"]


def test_hover_text_still_filtered_per_user_toggle(monkeypatch):
    from game_reader.text_filters import filter_speech_text
    settings = {**DEFAULTS, "filter_english": True,
                "filter_numbers": True, "filter_symbols": True}
    assert filter_speech_text("Press 18 + 拾取", settings) == "拾取"
    settings["filter_english"] = False
    assert "Press" in filter_speech_text("Press 18 + 拾取", settings)
