"""Strict nearest-to-cursor OCR regression checks for the user's desktop/game case.

All coordinates are physical desktop pixels; no actual voice license, screenshots,
or installed Microsoft voice package is needed in these tests.
"""
from __future__ import annotations

from queue import Queue

import pytest

from game_reader.core import OCRLine
from game_reader.hover_target import (
    centered_region, distance_to_ocr_box, nearest_readable_text,
)
from game_reader.hover_modes import RelativeRegion, capture_box


def test_old_off_center_setting_becomes_true_mouse_centered_crop():
    # Old experiments used y=-140 for a 400px tall crop, displacing its
    # centre 60px below the pointer. The new scan ignores the saved offset.
    old = RelativeRegion(-300, -140, 600, 400)
    region = centered_region(old)
    assert region.as_list() == [-300, -200, 600, 400]
    assert capture_box(region, (500, 500), (0, 0, 1920, 1080)) == (
        200, 300, 800, 700)
    adjusted = centered_region(RelativeRegion(150, 130, 400, 300))
    assert adjusted.as_list() == [-200, -150, 400, 300]
    assert capture_box(adjusted, (500, 500), (0, 0, 1920, 1080)) == (
        300, 350, 700, 650)


def test_real_user_case_mouse_on_dlss_does_not_read_seven_days_above():
    # Simulates screenshot: label for "7 Days to Die" is well above cursor,
    # while "DLSS" is slightly below a pointed-to image icon.
    pointer = (445, 835)
    lines = [
        OCRLine("7 Days to Die", 375, 408, 530, 458),
        OCRLine("DLSS", 370, 870, 493, 905),
        OCRLine("Game Lens", 345, 1060, 535, 1090),
    ]
    target = nearest_readable_text(lines, pointer)
    assert target is not None
    assert target.text == "DLSS"
    assert target.distance_px == pytest.approx(35)
    assert "7 Days" not in target.text
    assert "Game Lens" not in target.text


def test_distance_uses_actual_rectangle_not_global_picture_order():
    pointer = (1000, 500)
    assert distance_to_ocr_box(
        OCRLine("near", 1000, 520, 1080, 548), pointer) == 20
    assert distance_to_ocr_box(
        OCRLine("far", 1000, 210, 1080, 238), pointer) == 262
    target = nearest_readable_text([
        OCRLine("Far above", 980, 205, 1130, 235),
        OCRLine("Nearest", 999, 530, 1070, 557),
    ], pointer)
    assert target.text == "Nearest"


def test_no_nearby_text_means_silence_not_read_whole_crop():
    pointer = (1000, 500)
    lines = [
        OCRLine("回收站", 400, 200, 470, 236),
        OCRLine("此电脑", 1600, 850, 1680, 888),
    ]
    assert nearest_readable_text(lines, pointer) is None
    assert nearest_readable_text([], pointer) is None
    assert nearest_readable_text([OCRLine("far", 400, 400, 430, 430)],
                                 pointer) is None
    with pytest.raises(ValueError):
        nearest_readable_text(lines, pointer, max_distance_px=0)


def test_multiline_wrapped_long_tooltip_stays_one_reading_region():
    pointer = (347, 120)
    lines = [
        OCRLine("This is a fairly long line of skill help", 310, 111, 620, 134),
        OCRLine("continued as another readable line", 310, 139, 565, 163),
        OCRLine("INVENTORY", 760, 300, 860, 330),
    ]
    target = nearest_readable_text(lines, pointer)
    assert target is not None
    assert "This is a fairly long line" in target.text
    assert "continued as another readable line" in target.text
    assert "INVENTORY" not in target.text


def test_negative_monitor_coordinates_and_screen_edge_clamping():
    region = centered_region(RelativeRegion(-123, 55, 400, 300))
    assert capture_box(region, (-1850, 50), (-1920, 0, 0, 1080)) == (
        -1920, 0, -1520, 300)
    assert capture_box(region, (-100, 980), (-1920, 0, 0, 1080)) == (
        -400, 780, 0, 1080)


def test_desktop_relative_crop_scans_even_when_progman_is_foreground(monkeypatch):
    """Desktop exclusion was the wrong policy; nearby icons must be eligible."""
    import threading
    from PIL import Image
    import game_reader.app as mod
    from game_reader.app import ReaderApp

    class Root:
        def state(self):
            return "iconic"

    class MockThread:
        def __init__(self, target, **_):
            self.target = target
        def start(self):
            self.target()

    app = ReaderApp.__new__(ReaderApp)
    app.root = Root()
    app.closed = False
    app._choosing_region = False
    app.mouse_mode = "hover"
    app.busy = False
    app.hover_ocr_busy = False
    app.pending_full_capture = False
    app.mode_generation = 4
    app.settings = {"region": [200, 200, 600, 400], "period_ms": 500}
    app.events = Queue()
    app.status = lambda message: None
    seen = {}

    class OCR:
        def recognize(self, img, origin, tier):
            seen["origin"] = origin
            seen["size"] = img.size
            seen["model"] = tier
            return [OCRLine("DLSS", 790, 730, 865, 760)]

    app.ocr_worker = OCR()
    app._ocr_lock = threading.Lock()
    monkeypatch.setattr(mod, "get_cursor", lambda: (540, 500))
    monkeypatch.setattr(mod, "foreground_class", lambda: "Progman")
    monkeypatch.setattr(mod, "monitor_rect_at_cursor",
                        lambda: (0, 0, 1920, 1080))
    def grab(*, bbox, all_screens):
        seen["box"] = bbox
        assert all_screens
        return Image.new("RGB", (bbox[2]-bbox[0], bbox[3]-bbox[1]))
    monkeypatch.setattr(mod.ImageGrab, "grab", grab)
    monkeypatch.setattr(threading, "Thread", MockThread)

    assert app.start_hover_ocr(False)
    assert seen == {
        "origin": (740, 680),
        "size": (600, 400),
        "model": "small",
        "box": (740, 680, 1340, 1080),
    }
    event = app.events.get_nowait()
    assert event[0] == "hover_ok"
    assert event[5:7] == ((540, 500), "Progman")


def test_same_text_can_be_reidentified_at_new_cursor_location():
    """Select based on coordinates, not global order or OCR result index."""
    lines = [
        OCRLine("设置", 100, 200, 180, 240),
        OCRLine("设置", 500, 200, 580, 240),
    ]
    left = nearest_readable_text(lines, (145, 190))
    right = nearest_readable_text(lines, (540, 190))
    assert left.text == right.text == "设置"
    assert left.bounds != right.bounds
