"""Regression tests for two independent mouse reading modes and native side keys.

These tests intentionally do not call an OCR model or the user's voice config.
"""
from __future__ import annotations

import time

import pytest

from game_reader.core import OCRLine
from game_reader.hover_modes import (
    RelativeRegion, capture_box, region_from_drag, normalized_text,
    valid_hotkey, sanitize_hotkeys, hotkey_label, parse_period_ms,
    next_mouse_mode,
)
from game_reader.app import ReaderApp


def test_old_voice_settings_migrate_without_medium_or_hotkey_conflict():
    old = {"vk": 0x78, "hotkey_label": "F9", "tier": "medium",
           "luna_config": "C:/private/中文 配置.json",
           "voice": "natural:MicrosoftWindows.Voice.zh-CN.Yunxi.1"}
    updated = sanitize_hotkeys(old)
    assert len({updated["vk"], updated["mode_vk"], updated["local_vk"]}) == 3
    assert updated["vk"] == 0x78
    assert updated["luna_config"] == "C:/private/中文 配置.json"
    assert updated["voice"].endswith("Yunxi.1")
    assert valid_hotkey(5) and valid_hotkey(6)
    assert not valid_hotkey(1) and not valid_hotkey(2)
    assert not valid_hotkey(16) and not valid_hotkey(17)
    assert hotkey_label(5).startswith("鼠标侧键1")
    assert hotkey_label(6).startswith("鼠标侧键2")


@pytest.mark.parametrize("value,expected", [
    ("100", 100), ("300", 300), ("500", 500), ("1000", 1000),
    (" 60000 ", 60000),
])
def test_user_enters_period_in_milliseconds(value, expected):
    assert parse_period_ms(value) == expected


@pytest.mark.parametrize("invalid", ["", "0", "-30", "99", "60001",
                                     "1.5", "2e3", "hello", None, True])
def test_invalid_period_rejected(invalid):
    with pytest.raises(ValueError):
        parse_period_ms(invalid)


def test_region_box_moves_with_pointer_and_clamps_edges():
    monitor = (0, 0, 1920, 1080)
    region = RelativeRegion(-280, 50, 600, 400)
    assert capture_box(region, (500, 250), monitor) == (220, 300, 820, 700)
    assert capture_box(region, (1900, 1060), monitor) == (1320, 680, 1920, 1080)
    assert capture_box(region, (0, 0), monitor) == (0, 50, 600, 450)
    left_monitor = (-1920, 0, 0, 1080)
    assert capture_box(region, (-100, 500), left_monitor) == (-600, 550, 0, 950)
    assert capture_box(RelativeRegion(-100, -100, 5000, 4000),
                       (50, 50), monitor) == monitor


def test_dark_screen_rectangle_is_stored_relative_to_center_crosshair():
    new = region_from_drag((290, 250, 890, 650), (640, 360))
    assert new.as_list() == [-350, -110, 600, 400]
    assert capture_box(new, (980, 520), (0, 0, 1920, 1080)) == (
        630, 410, 1230, 810)
    assert region_from_drag((890, 650, 290, 250), (640, 360)) == new
    with pytest.raises(ValueError):
        region_from_drag((100, 100, 110, 110), (640, 360))
    assert RelativeRegion.from_settings(["bad", 0, 400, 400]) == RelativeRegion(
        -300, -140, 600, 400)


def test_mode_toggle_and_dedupe_ignore_whitespace():
    assert next_mouse_mode("pointer") == "hover"
    assert next_mouse_mode("hover") == "pointer"
    assert normalized_text("制 作 技 能\n下一页") == normalized_text("制作技能 下一页")


class FakeSpeech:
    def __init__(self):
        self.stops = 0

    def stop(self):
        self.stops += 1


def fake_reader_for_hover_results():
    app = ReaderApp.__new__(ReaderApp)
    app.hover_ocr_busy = True
    app.settings = {"period_ms": 500, "filter_english": False,
                    "filter_numbers": False, "filter_symbols": False,
                    "similarity_enabled": True, "similarity_threshold": 2}
    app.pending_full_capture = False
    app.mode_generation = 3
    app.mouse_mode = "hover"
    app._hover_last_text = ""
    app._hover_spoken_cursor = None
    app._hover_spoken_foreground = None
    app.speech = FakeSpeech()
    app.output_values = []
    app.spoken_values = []
    app.status_values = []
    app.update_output = app.output_values.append
    app.speak_selected = app.spoken_values.append
    app.status = app.status_values.append
    return app


def test_periodic_hover_ocr_speaks_once_per_new_text_and_manual_can_repeat(monkeypatch):
    import game_reader.app as mod
    monkeypatch.setattr(mod, "get_cursor", lambda: (150, 130))
    monkeypatch.setattr(mod, "foreground_class", lambda: "GameWindow")
    app = fake_reader_for_hover_results()
    lines = [OCRLine("制作技能", 100, 120, 210, 148)]
    app._handle_hover_result(3, lines, False, 35, (150, 130), "GameWindow")
    assert app.spoken_values == ["制作技能"]
    assert app._hover_last_text == "制作技能"
    app._handle_hover_result(3, lines, False, 31, (150, 130), "GameWindow")
    assert app.spoken_values == ["制作技能"]
    app._handle_hover_result(3, lines, True, 40, (150, 130), "GameWindow")
    assert app.spoken_values == ["制作技能", "制作技能"]
    app._handle_hover_result(3, [OCRLine("技能详情", 90, 80, 200, 105)],
                             False, 45, (150, 130), "GameWindow")
    assert app.spoken_values[-1] == "技能详情"
    app._handle_hover_result(3, [], False, 31, (150, 130), "GameWindow")
    assert app._hover_last_text == ""


def test_stale_mode_result_is_discarded_without_speech():
    app = fake_reader_for_hover_results()
    app._handle_hover_result(2, [OCRLine("旧弹窗", 5, 5, 100, 30)], False, 30)
    assert app.spoken_values == []
    assert app._hover_last_text == ""


def test_one_busy_hover_ocr_is_skipped_not_queued():
    app = ReaderApp.__new__(ReaderApp)
    app.closed = False
    app._choosing_region = False
    app.mouse_mode = "hover"
    app.busy = False
    app.hover_ocr_busy = True
    app.pending_full_capture = False
    app.status = lambda msg: None
    assert app.start_hover_ocr(manual=True) is False


def test_hotkey_assignment_refuses_duplicates_and_records_side_button():
    app = ReaderApp.__new__(ReaderApp)
    app.settings = {"vk": 119, "hotkey_label": "F8",
                    "mode_vk": 120, "mode_hotkey_label": "F9",
                    "local_vk": 121, "local_hotkey_label": "F10",
                    "pick_vk": 122, "pick_hotkey_label": "F11",
                    "clear_vk": 117, "clear_hotkey_label": "F6"}
    app._binding_target = "mode_vk"
    app.mouse_mode = "hover"
    app._hotkey_previous = {}
    app.status_values = []
    app.status = app.status_values.append
    app.persist = lambda: None
    app.finish_hotkey = lambda: setattr(app, "_binding_target", None)
    assert app._apply_hotkey(119, "F8") is False
    assert app.settings["mode_vk"] == 120
    assert app._apply_hotkey(5, "side") is True
    assert app.settings["mode_vk"] == 5
    assert app.settings["mode_hotkey_label"].startswith("鼠标侧键1")
    assert app._hotkey_previous["mode_vk"] is True


def test_global_key_poll_handles_side_hotkeys_once_per_press(monkeypatch):
    import game_reader.app as mod

    class Root:
        def __init__(self):
            self.waits = []
        def after(self, ms, callback):
            self.waits.append(ms)
        def state(self):
            return "iconic"

    app = ReaderApp.__new__(ReaderApp)
    app.root = Root()
    app.closed = False
    app._choosing_region = False
    app.setting_hotkey = False
    app.settings = {"vk": 119, "mode_vk": 5, "local_vk": 6,
                    "pick_vk": 122, "clear_vk": 117, "period_ms": 500}
    app._hotkey_previous = {"vk": False, "mode_vk": False, "local_vk": False,
                            "pick_vk": False, "clear_vk": False}
    app.expires_at = None
    app.mouse_mode = "pointer"
    app.lines = []
    app.busy = False
    app._hover_next_due = float("inf")
    hits = []
    app.capture = lambda: hits.append("fullscreen")
    app.toggle_mouse_mode = lambda: hits.append("mode")
    app.start_hover_ocr = lambda manual: hits.append("local")
    app.status = lambda msg: hits.append("error")
    buttons = {119: False, 5: False, 6: False}
    monkeypatch.setattr(mod, "is_key_down", lambda vk: buttons.get(vk, False))
    buttons[5] = True
    app.poll_input()
    app.poll_input()
    assert hits == ["mode"]
    buttons[5] = False
    app.poll_input()
    buttons[6] = True
    app.poll_input()
    assert hits == ["mode", "local"]
    buttons[6] = False
    app.poll_input()
    buttons[119] = True
    app.poll_input()
    assert hits == ["mode", "local", "fullscreen"]
    assert app.root.waits == [20] * 6


def test_real_tk_picker_opens_selects_and_cancels_on_windows():
    import sys
    if sys.platform != "win32":
        pytest.skip("Windows Tk alpha overlay test")
    import tkinter as tk
    from types import SimpleNamespace
    from game_reader.region_picker import ScreenRegionPicker

    root = tk.Tk()
    root.withdraw()
    choices = []
    try:
        picker = ScreenRegionPicker(
            root, (0, 0, 1024, 768), RelativeRegion(-300, -140, 600, 400),
            choices.append)
        root.update()
        picker._start_drag(SimpleNamespace(x=180, y=200))
        picker._drag(SimpleNamespace(x=760, y=630))
        picker._finish_drag(SimpleNamespace(x=760, y=630))
        assert choices[0].as_list() == [-332, -184, 580, 430]

        second = ScreenRegionPicker(
            root, (0, 0, 1024, 768), RelativeRegion(-300, -140, 600, 400),
            choices.append)
        root.update()
        second.cancel()
        assert choices == [RelativeRegion(-332, -184, 580, 430), None]
    finally:
        root.destroy()


def test_every_mode_key_press_switches_immediately_first_hover_second_pointer():
    class Fake:
        def __init__(self):
            self.values = []
        def set(self, value):
            self.values.append(value)
        def reset(self):
            self.values.append("reset")
        def stop(self):
            self.values.append("stop")
        def play(self, name):
            self.values.append(name)
        def hide(self):
            self.values.append("hide")

    class FakeRoot:
        def state(self):
            return "iconic"

    app = ReaderApp.__new__(ReaderApp)
    app.root = FakeRoot()
    app.mouse_mode = "pointer"
    app.settings = {"mode_voice_hint": False}
    app.mode_generation = 0
    app._hover_last_text = ""
    app.hover = Fake()
    app.last_target = None
    app.speech = Fake()
    app.overlay = None
    app.mouse_mode_var = Fake()
    app.cues = Fake()
    app.lines = []
    app.status = lambda msg: None
    app.update_output = lambda text: None
    app.toggle_mouse_mode()
    assert app.mouse_mode == "hover"
    app.toggle_mouse_mode()
    assert app.mouse_mode == "pointer"
    app.toggle_mouse_mode()
    assert app.mouse_mode == "hover"
    assert app.mode_generation == 3


def test_f11_global_picker_has_separate_hotkey_and_does_not_conflict():
    from game_reader.hover_modes import HOTKEY_FIELDS, HOTKEY_DEFAULTS, sanitize_hotkeys
    assert HOTKEY_FIELDS == ("vk", "mode_vk", "local_vk", "pick_vk", "clear_vk")
    d = sanitize_hotkeys({"vk": 119, "mode_vk": 120,
                          "local_vk": 121, "pick_vk": 122, "clear_vk": 117})
    assert [d[k] for k in HOTKEY_FIELDS] == list(HOTKEY_DEFAULTS)


def test_stale_hover_crop_is_rejected_when_cursor_moves_or_foreground_changes(monkeypatch):
    import game_reader.app as mod
    app = fake_reader_for_hover_results()
    app._hover_spoken_cursor = None
    monkeypatch.setattr(mod, "get_cursor", lambda: (900, 550))
    monkeypatch.setattr(mod, "foreground_class", lambda: "GameWindow")
    old_text = [OCRLine("回收站", 20, 20, 120, 45)]
    app._handle_hover_result(3, old_text, False, 40,
                             (200, 300), "GameWindow")
    assert app.spoken_values == []
    assert app._hover_last_text == ""
    app._handle_hover_result(3, old_text, False, 40,
                             (900, 550), "Progman")
    assert app.spoken_values == []
    app._handle_hover_result(3, [OCRLine("制作技能", 850, 530, 960, 565)],
                             False, 40, (901, 551), "GameWindow")
    assert app.spoken_values == ["制作技能"]


def test_local_region_reads_whole_crop_in_order_not_nearest(monkeypatch):
    """Confirmed design: original full-screen OCR rules on a smaller screenshot."""
    import game_reader.app as mod
    from game_reader.hover_modes import cursor_still_near_capture
    monkeypatch.setattr(mod, "get_cursor", lambda: (450, 650))
    monkeypatch.setattr(mod, "foreground_class", lambda: "Progman")
    app = fake_reader_for_hover_results()
    lines = [OCRLine("七日杀", 400, 200, 530, 240),
             OCRLine("碎布", 400, 685, 490, 720)]
    app._handle_hover_result(3, lines, False, 45, (450, 650), "Progman")
    assert app.spoken_values == ["七日杀\n碎布"]
    assert cursor_still_near_capture((100, 200), (120, 220))
    assert not cursor_still_near_capture((100, 200), (800, 220))


def test_global_picker_reopens_repeatedly_after_cancel_on_real_windows(monkeypatch):
    import sys
    if sys.platform != "win32":
        pytest.skip("Real Windows Tk window lifecycle")
    import tkinter as tk
    import game_reader.app as mod

    try:
        root = tk.Tk()
    except tk.TclError:
        # GitHub hosted Python source runtime may lack Tcl auto.tcl,
        # while the frozen EXE has its own bundled Tcl runtime. The latter
        # is validated separately by the mandatory --self-test-picker.
        pytest.skip("Hosted source Python Tcl runtime unavailable; frozen UI test required")
    root.geometry("500x400")
    root.update()
    app = ReaderApp.__new__(ReaderApp)
    app.root = root
    app.closed = False
    app.setting_hotkey = False
    app._choosing_region = False
    app._region_picker = None
    app._region_previous_root_state = "normal"
    app._hover_last_text = ""
    app._hover_spoken_cursor = None
    app.mode_generation = 0
    from types import SimpleNamespace
    app.speech = SimpleNamespace(stop=lambda: None)
    app.settings = {"region": [-300, -140, 600, 400], "period_ms": 500}
    app.region_info_var = tk.StringVar(master=root, value="old")
    app.status = lambda message: None
    app.persist = lambda: None
    monkeypatch.setattr(mod, "monitor_rect_at_cursor", lambda: (0, 0, 1024, 768))
    try:
        for _ in range(3):
            app.select_region()
            root.after(50, lambda: None)
            import time
            time.sleep(0.07)
            root.update()
            picker = app._region_picker
            assert picker is not None, "Picker failed to reopen"
            assert picker.winfo_exists()
            picker.cancel()
            root.update()
            assert not app._choosing_region
            assert app._region_picker is None
            assert float(root.attributes("-alpha")) == pytest.approx(1.0)
    finally:
        root.destroy()


def test_f11_opens_picker_globally_and_window_switch_clears_old_ocr(monkeypatch):
    import game_reader.app as mod
    class FakeRoot:
        def after(self, ms, callback):
            pass
        def state(self):
            return "iconic"
    app = ReaderApp.__new__(ReaderApp)
    app.closed = False
    app.root = FakeRoot()
    app._choosing_region = False
    app.setting_hotkey = False
    app.settings = {"vk": 119, "mode_vk": 120,
                    "local_vk": 121, "pick_vk": 122, "clear_vk": 117, "period_ms": 500}
    app._hotkey_previous = {x: False for x in ("vk","mode_vk","local_vk","pick_vk","clear_vk")}
    app.expires_at = None
    app.mouse_mode = "pointer"
    app.busy = False
    app.lines = [OCRLine("旧桌面图标", 10, 10, 90, 40)]
    app._full_capture_window = 100
    calls = []
    app.select_region = lambda: calls.append("picker")
    def invalidate(reason):
        calls.append("old-coords-cleared")
        app.lines = []
    app.invalidate = invalidate
    app.status = lambda message: calls.append("unexpected")
    keys = {119: False, 120: False, 121: False, 122: True}
    monkeypatch.setattr(mod, "is_key_down", lambda vk: keys.get(vk, False))
    monkeypatch.setattr(mod, "foreground_window_id", lambda: 200)
    app.poll_input()
    assert calls == ["picker", "old-coords-cleared"]
    app.poll_input()
    assert calls == ["picker", "old-coords-cleared"]
