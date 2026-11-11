"""Fixed region game OCR regression: no user game, voice model or private config."""
from __future__ import annotations

from queue import Queue
from threading import Lock
from types import SimpleNamespace
from PIL import Image, ImageDraw
import time

import pytest

from game_reader.core import OCRLine
from game_reader.fixed_region import (
    parse_fixed_region, parse_monitor, region_on_same_monitor,
    screenshot_fingerprint, frame_has_changed, fresh_speech_lines,
    display_color, parse_thickness, parse_strategy)
from game_reader.hover_modes import (
    HOTKEY_FIELDS, HOTKEY_DEFAULTS, sanitize_hotkeys, next_mouse_mode,
    RelativeRegion)
from game_reader.app import ReaderApp


def test_three_mode_cycle_and_f7_conflict_safe():
    assert [next_mouse_mode(a) for a in ("pointer", "hover", "region")] == [
        "hover", "region", "pointer"]
    keys = sanitize_hotkeys({"vk": 0x76})
    assert keys["vk"] == 0x76
    assert len({keys[k] for k in HOTKEY_FIELDS}) == len(HOTKEY_FIELDS)
    assert keys["frame_vk"] != 0x76
    assert sanitize_hotkeys({})["frame_vk"] == 0x76
    assert len(HOTKEY_DEFAULTS) == 6


def test_saved_absolute_rect_checks_monitor_and_no_cursor_recenter():
    monitor = (0, 0, 1920, 1080)
    box = (150, 250, 890, 640)
    assert parse_fixed_region(list(box), monitor) == box
    assert region_on_same_monitor(box, monitor, monitor)
    assert not region_on_same_monitor(box, monitor, (0, 0, 2560, 1440))
    assert not region_on_same_monitor(box, monitor, (1920, 0, 3840, 1080))
    assert not region_on_same_monitor(box, monitor, None)
    assert parse_fixed_region((1850, 950, 2200, 1070), monitor) is None
    assert parse_fixed_region((150, 200, 160, 250), monitor) is None
    assert parse_fixed_region((True, 200, 500, 600), monitor) is None
    assert parse_monitor([-1920, 0, 0, 1080]) == (-1920, 0, 0, 1080)
    assert parse_fixed_region([-1800, 20, -1200, 520], (-1920,0,0,1080))


def test_change_detection_skips_identical_and_picks_up_small_text():
    base = Image.new("RGB", (600, 350), "#172A39")
    picture = base.copy()
    draw = ImageDraw.Draw(picture)
    draw.rectangle((130, 140, 470, 168), fill="white")
    prev, new = screenshot_fingerprint(base), screenshot_fingerprint(picture)
    assert not frame_has_changed(prev, screenshot_fingerprint(base))
    assert frame_has_changed(prev, new)
    assert frame_has_changed(None, prev)


def test_duplicate_labels_and_reappearing_text_are_spoken_exactly_once():
    assert fresh_speech_lines([], ["获得石斧"]) == ["获得石斧"]
    assert fresh_speech_lines(["获得石斧"], ["获得石斧"]) == []
    assert fresh_speech_lines(["获得石斧"], []) == []
    assert fresh_speech_lines([], ["获得石斧"]) == ["获得石斧"]
    assert fresh_speech_lines(["获得石斧", "获得石斧"],
                              ["获得石斧", "获得石斧", "获得碎布"]) == ["获得碎布"]
    assert fresh_speech_lines(["任务一"], ["任务一", "任务二"]) == ["任务二"]


@pytest.mark.parametrize("raw,expected",[
    ("bad", "change"), ("change", "change"), ("period", "period"),
])
def test_strategy_validation(raw,expected):
    assert parse_strategy(raw) == expected


def test_color_thickness_repair():
    assert display_color("#FFFFFF") == "#FFFFFF"
    assert display_color("#004400") == "#42DD9C"
    for bad in (True, 0, "9", -1, None):
        assert parse_thickness(bad) == 3
    assert parse_thickness("8") == 8


def _fake_region_reader(monkeypatch):
    import game_reader.app as module
    monkeypatch.setattr(module, "foreground_window_id", lambda: 42)
    app = ReaderApp.__new__(ReaderApp)
    app.mode_generation = 7
    app.mouse_mode = "region"
    app._region_job_id = 3
    app.region_ocr_busy = True
    app._region_next_due = 0
    app.pending_full_capture = False
    app._region_last_fingerprint = None
    app._region_last_text = ""
    app._region_prev_lines = []
    app._fixed_region_box = lambda: (100, 100, 500, 250)
    app.settings = {"filter_english": True, "filter_numbers": True,
                    "filter_symbols": True, "similarity_enabled": True,
                    "similarity_threshold": 2}
    app.speech = SimpleNamespace(stop=lambda: app.stops.append("stop"))
    app.stops = []
    app.spoken = []
    app.speak_selected = app.spoken.append
    app.outputs = []
    app.update_output = app.outputs.append
    app.status = lambda _: None
    return app


def test_fixed_region_new_text_blank_and_repeat(monkeypatch):
    app = _fake_region_reader(monkeypatch)
    sig = screenshot_fingerprint(Image.new("RGB", (100, 100), "black"))
    a = [OCRLine("获得石斧", 100, 110, 210, 145)]
    b = [OCRLine("获得石斧", 100, 110, 210, 145),
         OCRLine("获得碎布", 100, 155, 210, 190)]
    app._handle_region_result(7, 3, a, sig, 90, 42, (10, 80), True)
    assert app.spoken == ["获得石斧"]
    app._handle_region_result(7, 3, a, sig, 80, 42, (10, 70), True)
    assert app.spoken == ["获得石斧"]
    app._handle_region_result(7, 3, b, sig, 90, 42, (10, 80), True)
    assert app.spoken == ["获得石斧", "获得碎布"]
    app._handle_region_result(7, 3, [], sig, 70, 42, (10, 60), True)
    assert app.stops == ["stop"]
    app._handle_region_result(7, 3, a, sig, 70, 42, (10, 60), True)
    assert app.spoken == ["获得石斧", "获得碎布", "获得石斧"]


def test_old_mode_job_and_same_pixels_do_not_speak(monkeypatch):
    app = _fake_region_reader(monkeypatch)
    sig = screenshot_fingerprint(Image.new("RGB", (100, 100), "black"))
    app._handle_region_result(7, 2, [OCRLine("旧文字", 1,1,80,35)],
                              sig, 40, 42, (10,30))
    assert app.region_ocr_busy  # Old job cannot clear current busy.
    app._handle_region_result(7, 3, None, sig, 40, 42, (10,0))
    assert not app.region_ocr_busy
    assert app.spoken == []
    app.mode_generation = 8
    app._handle_region_result(7, 3, [OCRLine("过期文字", 1,1,80,35)],
                              sig, 40, 42, (10,30))
    assert app.spoken == []


def test_f7_toggle_is_purely_visual():
    app = ReaderApp.__new__(ReaderApp)
    app.mouse_mode = "region"
    app._region_border_visible = True
    shown, status = [], []
    app.update_scan_frame = lambda: shown.append(app._region_border_visible)
    app.status = status.append
    app.toggle_region_border()
    app.toggle_region_border()
    assert shown == [False, True]
    assert len(status) == 2
    app.mouse_mode = "hover"
    app.toggle_region_border()
    assert shown == [False, True]


def test_region_f11_persists_absolute_box_without_touching_mouse_relative():
    app = ReaderApp.__new__(ReaderApp)
    app.closed = False
    app.mouse_mode = "region"
    app._region_previous_root_state = "iconic"
    app._picker_anchor = (420,350)
    app._picker_monitor = (0,0,1920,1080)
    app._picker_snapshot = Image.new("RGB", (1920,1080), "black")
    app._picker_foreground = 42
    app.root = SimpleNamespace(attributes=lambda *args:None,
        state=lambda:"iconic", iconify=lambda:None, deiconify=lambda:None)
    app.settings = {"region": [-300,-140,600,400], "show_scan_frame": True}
    app.status = lambda s: None
    app.persist = lambda: None
    app.region_preview_var = SimpleNamespace(set=lambda s:None)
    app.update_scan_frame = lambda:None
    fired = []
    app.start_region_scan = lambda **kw: fired.append(kw)
    app._region_picked(RelativeRegion(10,70,260,150))
    assert app.settings["fixed_region"] == [430,420,690,570]
    assert app.settings["fixed_monitor"] == [0,0,1920,1080]
    assert app.settings["region"] == [-300,-140,600,400]
    assert fired and fired[0]["force"] is True


def test_original_luna_owns_region_capture_analysis_timing_and_ocr(monkeypatch):
    """No BlueStar screen grabs/OCR threads may run in upstream region mode."""
    import game_reader.app as module
    app = ReaderApp.__new__(ReaderApp)
    app.closed = False
    app._choosing_region = False
    app.setting_hotkey = False
    app.mouse_mode = "region"
    app.root = SimpleNamespace(state=lambda: "iconic")
    app._region_job_id = 0
    app._region_border_visible = False
    app._region_next_due = 0
    app._fixed_region_box = lambda: (10, 10, 200, 100)
    app.status = lambda message: None
    requests = []
    app.ocr_worker = SimpleNamespace(
        do_async=lambda method, *values: requests.append((method, values))
    )
    monkeypatch.setattr(module, "grab_game_rect",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("BlueStar capture forbidden")))
    assert app.start_region_scan(force=True)
    assert requests == [("request_region", ((10, 10, 200, 100), False))]
    assert app._region_next_due == float("inf")
    assert app._region_job_id == 1
    # The original program scans in its own process; no followup screenshot.
    assert requests == [("request_region", ((10, 10, 200, 100), False))]



def test_manual_clear_preserves_region_dedup_but_erases_visible_results():
    app = ReaderApp.__new__(ReaderApp)
    app.mouse_mode = "region"
    app._region_last_text = "获得石斧"
    app._region_prev_lines = ["获得石斧"]
    app._region_last_fingerprint = screenshot_fingerprint(
        Image.new("RGB", (90, 60), "black"))
    app.capture_id = 7
    app.mode_generation = 4
    app.busy = False
    app.pending_full_capture = False
    app._hover_last_text = ""
    app.expires_at = 10
    app.lines = [OCRLine("以前识别的句子", 1, 1, 80, 30)]
    app._full_capture_window = None
    app.last_target = None
    app._hover_spoken_cursor = None
    app._hover_spoken_foreground = None
    app.hover = SimpleNamespace(reset=lambda: None)
    calls = []
    app.speech = SimpleNamespace(stop=lambda:calls.append("stop"),
                                 clear_cache=lambda:calls.append("clear_cache"))
    app.overlay = None
    app.read_btn = SimpleNamespace(configure=lambda **kw:None)
    app.update_output = lambda s:calls.append(("output",s))
    app.status = lambda s:None
    app.invalidate("已清空")
    assert app.lines == []
    assert app._region_last_text == "获得石斧"
    assert app._region_prev_lines == ["获得石斧"]
    assert calls == ["stop", "clear_cache", ("output", "")]


def test_f7_shortcut_can_be_rebound_without_overwriting_f11():
    app = ReaderApp.__new__(ReaderApp)
    frame_button = object()
    app.frame_key_button = frame_button
    assert app._hotkey_button("frame_vk") is frame_button
    config = sanitize_hotkeys({"pick_vk": 0x76})
    assert config["pick_vk"] == 0x76
    assert config["frame_vk"] != 0x76
    assert len(set(config[k] for k in HOTKEY_FIELDS)) == 6


def test_win32_all_palette_outlines_remain_native_and_outside_ocr():
    import sys
    if sys.platform != "win32":
        pytest.skip("Windows native layered windows only")
    from game_reader.overlay import ClickThroughOutline
    for color in ("#42DD9C", "#38A8FF", "#FFD34D", "#FF7373", "#FFFFFF"):
        outline = ClickThroughOutline(color=color, thickness=8, padding=9)
        try:
            assert outline.padding >= outline.thickness + 1
            outline.show(OCRLine("test", 150, 150, 450, 300))
            outline.show(OCRLine("test", 150, 150, 450, 300))
            outline.hide()
        finally:
            outline.close()
