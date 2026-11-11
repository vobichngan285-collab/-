"""Regression tests for immediate mode retirement, F7 and uncached region OCR.

All hardware, game, engine and voice operations are stubbed; Windows CI runs these.
"""
from __future__ import annotations

import time
from types import SimpleNamespace

from PIL import Image

from game_reader.app import ReaderApp
from game_reader.core import OCRLine
from game_reader.fixed_region import screenshot_fingerprint, frame_has_changed
from game_reader.hover_modes import HOTKEY_FIELDS


def _reader_for_switch():
    app = ReaderApp.__new__(ReaderApp)
    app.mouse_mode = "region"
    app.settings = {
        "show_scan_frame": True, "mode_voice_hint": False,
        "fixed_region": [10, 10, 210, 110],
        "fixed_monitor": [0, 0, 1920, 1080],
    }
    app.mouse_mode_var = SimpleNamespace(set=lambda value: None)
    app.root = SimpleNamespace(state=lambda: "iconic", iconify=lambda: None)
    app._region_border_visible = False
    app._region_job_id = 6
    app.capture_id = 11
    app.mode_generation = 7
    app.busy = True
    app.region_ocr_busy = True
    app.hover_ocr_busy = True
    app.pending_full_capture = True
    app._pending_full_trigger_at = 111
    app.expires_at = 99
    app.lines = [OCRLine("old", 1, 1, 70, 25)]
    app._full_capture_window = 42
    app._region_last_fingerprint = b"signature"
    app._region_last_text = "old"
    app._region_prev_lines = ["old"]
    app._hover_last_text = "old"
    app._hover_spoken_cursor = (3, 3)
    app._hover_spoken_foreground = 100
    app._region_force_initial = False
    app.last_target = object()
    app.hover = SimpleNamespace(reset=lambda: None)
    app.speech = SimpleNamespace(stop=lambda: None)
    app.overlay = None
    app.scan_frame = None
    app.fixed_frame = None
    app.read_btn = SimpleNamespace(configure=lambda **kwargs: None)
    app.outputs = []
    app.update_output = app.outputs.append
    app.status = lambda message: None
    return app


def test_f7_hidden_stays_hidden_across_switches_and_old_jobs_are_retired():
    app = _reader_for_switch()
    app._switch_mouse_mode("hover")
    assert app._region_border_visible is False
    assert app.lines == [] and app.expires_at is None
    assert not app.busy and not app.hover_ocr_busy and not app.region_ocr_busy
    assert not app.pending_full_capture and app._pending_full_trigger_at is None
    assert app.outputs[-1] == ""
    app._switch_mouse_mode("region")
    assert app._region_border_visible is False
    assert app._region_force_initial
    assert app._region_next_due <= time.monotonic()
    assert app._mode_announcement_until == 0.0
    assert app._region_job_id == 8
    assert app.mode_generation == 9 and app.capture_id == 13
    assert app._region_last_text == "" and app._region_prev_lines == []


def test_first_region_scan_is_forced_once_without_timer_gate(monkeypatch):
    import game_reader.app as module
    app = ReaderApp.__new__(ReaderApp)
    app.closed = False
    app.setting_hotkey = False
    app._choosing_region = False
    app.wheel_listener = None
    app._hotkey_previous = {field: False for field in HOTKEY_FIELDS}
    app.settings = dict(zip(HOTKEY_FIELDS, (0x77, 0x78, 0x79, 0x7A, -1002, 0x76)))
    app.expires_at = None
    app.mouse_mode = "region"
    app.busy = False
    app.region_ocr_busy = False
    app._region_next_due = 0
    app._mode_announcement_until = 0
    app._region_force_initial = True
    app.root = SimpleNamespace(after=lambda *a: None)
    app.update_scan_frame = lambda: None
    calls = []
    app.start_region_scan = lambda force=False: calls.append(force) or True
    monkeypatch.setattr(module, "is_key_down", lambda vk: False)
    app.poll_input()
    assert calls == [True]
    assert app._region_force_initial is False
    app.poll_input()
    assert calls == [True, False]


def test_retired_hover_result_cannot_clear_new_ocr_busy_flag():
    app = ReaderApp.__new__(ReaderApp)
    app.mode_generation = 12
    app.hover_ocr_busy = True
    app._handle_hover_result(11, [], False, 0)
    assert app.hover_ocr_busy is True


def test_change_gate_stores_small_bytes_not_a_snapshot():
    old = Image.new("RGB", (900, 440), "#151525")
    modified = old.copy()
    from PIL import ImageDraw
    ImageDraw.Draw(modified).rectangle((140, 120, 650, 162), fill="white")
    a, b = screenshot_fingerprint(old), screenshot_fingerprint(modified)
    assert type(a) is bytes and len(a) == 128 * 72
    assert not frame_has_changed(a, a)
    assert frame_has_changed(a, b)
    assert frame_has_changed(None, a)
