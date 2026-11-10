"""Next-version Windows input, mode clearing, and Luna screenshot regressions.

No game memory, private settings, speech license, or actual game is accessed.
"""
from __future__ import annotations
from types import SimpleNamespace
from PIL import Image

from game_reader.app import ReaderApp
from game_reader.hover_modes import (
    HOTKEY_DEFAULTS, HOTKEY_FIELDS, WHEEL_UP, WHEEL_DOWN,
    hotkey_label, sanitize_hotkeys, valid_hotkey
)
from game_reader.mouse_input import WheelAccumulator
from game_reader.luna_capture import capture_rect


def test_wheel_is_an_event_not_a_virtual_key_and_middle_is_a_real_key():
    assert (WHEEL_UP, WHEEL_DOWN) == (-1001, -1002)
    assert valid_hotkey(WHEEL_UP) and valid_hotkey(WHEEL_DOWN)
    assert valid_hotkey(4) and valid_hotkey(5) and valid_hotkey(6)
    assert not valid_hotkey(1) and not valid_hotkey(2)
    assert hotkey_label(WHEEL_DOWN) == "滚轮向下"
    assert hotkey_label(WHEEL_UP) == "滚轮向上"
    assert hotkey_label(4) == "鼠标中键"
    assert HOTKEY_DEFAULTS[4] == WHEEL_DOWN
    defaults = sanitize_hotkeys({})
    assert defaults["clear_vk"] == WHEEL_DOWN
    assert len({defaults[k] for k in HOTKEY_FIELDS}) == 6


def test_binding_collision_and_user_custom_keyboard_stay_unchanged():
    custom = sanitize_hotkeys({"clear_vk": 0x42, "clear_hotkey_label": "B"})
    assert custom["clear_vk"] == 0x42
    duplicate = sanitize_hotkeys({"vk": WHEEL_DOWN, "clear_vk": WHEEL_DOWN})
    assert len({duplicate[k] for k in HOTKEY_FIELDS}) == len(HOTKEY_FIELDS)
    assert duplicate["vk"] == WHEEL_DOWN
    assert duplicate["clear_vk"] != WHEEL_DOWN


def test_high_resolution_wheel_steps_and_direction_reversal():
    w = WheelAccumulator()
    assert w.push(30) is None
    assert w.push(30) is None
    assert w.push(60) == WHEEL_UP
    assert w.push(-20) is None
    assert w.push(-100) == WHEEL_DOWN
    assert w.push(120) == WHEEL_UP


def test_wheel_clear_is_debounced_and_normal_scroll_is_not_intercepted(monkeypatch):
    import game_reader.app as module
    hits = []
    app = ReaderApp.__new__(ReaderApp)
    app.root = SimpleNamespace(after=lambda *args: None, state=lambda: "iconic")
    app.closed = False
    app.setting_hotkey = False
    app._choosing_region = False
    app.settings = {"vk": 119, "mode_vk": 120, "local_vk": 121,
                    "pick_vk": 122, "clear_vk": WHEEL_DOWN, "frame_vk": 118}
    app._hotkey_previous = {k: False for k in HOTKEY_FIELDS}
    app._last_wheel_action_at = 0
    app.expires_at = None
    app.mouse_mode = "pointer"
    app.busy = False
    app.lines = []
    app.clear_results = lambda: hits.append("clear")
    app.wheel_listener = SimpleNamespace(
        drain=lambda: [(WHEEL_DOWN, 101.0),
                       (WHEEL_DOWN, 101.09), (WHEEL_DOWN, 101.30)])
    monkeypatch.setattr(module, "is_key_down", lambda vk: False)
    app.poll_input()
    assert hits == ["clear", "clear"]


def test_region_clear_forgets_saved_box_prevents_late_jobs_and_f7_is_separate():
    app = ReaderApp.__new__(ReaderApp)
    app.mouse_mode = "region"
    app.settings = {"fixed_region": [40, 50, 400, 250],
                    "fixed_monitor": [0, 0, 1920, 1080]}
    app._region_job_id = 7
    app._region_last_fingerprint = object()
    app._region_last_text = "old"
    app._region_prev_lines = ["old"]
    app.region_ocr_busy = True
    app._region_next_due = 0.0
    app._region_invalid_reported = True
    calls = []
    app.invalidate = lambda reason: calls.append(reason)
    app.persist = lambda: calls.append("persist")
    app.format_fixed_region = lambda: "尚未框选"
    app.region_preview_var = SimpleNamespace(set=lambda text: calls.append(text))
    app.fixed_frame = SimpleNamespace(hide=lambda: calls.append("hide"))
    app.clear_results()
    assert app.settings["fixed_region"] is None
    assert app.settings["fixed_monitor"] is None
    assert app._region_job_id == 8
    assert app._region_next_due == float("inf")
    assert not app.region_ocr_busy
    assert app._region_last_text == "" and app._region_prev_lines == []
    assert "persist" in calls and "hide" in calls


def test_hover_clear_pauses_scan_until_mode_reentered():
    app = ReaderApp.__new__(ReaderApp)
    app.mouse_mode = "hover"
    app.invalidate = lambda reason: None
    app._hover_scan_paused = False
    app.scan_frame = SimpleNamespace(hide=lambda: None)
    app.clear_results()
    assert app._hover_scan_paused
    assert app._hover_next_due == float("inf")


def test_luna_hwnd_first_and_desktop_fallback_keep_exact_pixels(monkeypatch):
    import game_reader.luna_capture as capture
    box = (100, 120, 350, 210)
    valid = Image.new("RGB", (250, 90), "#335577")
    calls = []
    monkeypatch.setattr(capture, "_gdi_window_box",
                        lambda hwnd, rect: calls.append(("hwnd", hwnd)) or valid)
    monkeypatch.setattr(capture.ImageGrab, "grab",
                        lambda **kwargs: calls.append(("fallback", kwargs)) or valid)
    assert capture_rect(box, hwnd=123).size == (250, 90)
    assert calls == [("hwnd", 123)]
    calls.clear()
    monkeypatch.setattr(capture, "_gdi_window_box", lambda hwnd, rect: None)
    assert capture_rect(box, hwnd=123).size == (250, 90)
    assert calls == [("fallback", {"bbox": box, "all_screens": True})]
