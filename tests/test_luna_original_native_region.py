"""Original LunaTranslator v12.1.3.9 native desktop capture integration tests.

The screenshot engine is the author's unmodified distributed NativeUtils.dll;
these fixtures simulate its documented callback without loading third-party
native code or grabbing the real user's screen.
"""
from __future__ import annotations

from io import BytesIO
import ctypes
import time
from types import SimpleNamespace
from PIL import Image
import pytest

import game_reader.luna_native_region as native
from game_reader.app import ReaderApp


def test_exact_author_cdecl_desktop_api_used_and_rgb_is_preserved(monkeypatch):
    box = (110, 220, 330, 310)
    image = Image.new("RGB", (220, 90), (27, 81, 169))
    stream = BytesIO()
    image.save(stream, format="BMP")
    payload = stream.getvalue()
    seen = []

    def author_export(hwnd, left, top, right, bottom, callback, curr):
        seen.append((hwnd, left, top, right, bottom, curr))
        data = (ctypes.c_ubyte * len(payload)).from_buffer_copy(payload)
        callback(data, len(payload))
        return True

    monkeypatch.setattr(native, "_load_original", lambda: author_export)
    monkeypatch.setattr(native.ImageGrab, "grab", lambda **kw:
                        (_ for _ in ()).throw(AssertionError("no Pillow full-screen fallback")))
    report = {}
    result = native.grab_region_original(box, report)
    assert seen == [(None, *box, 1)]  # 1 means author's DESKTOP mode, not HWND.
    assert report == {"method": "luna_original_native_desktop"}
    assert result.size == image.size
    assert result.getpixel((5, 7)) == image.getpixel((5, 7))


def test_original_native_failure_falls_back_to_known_good_desktop(monkeypatch):
    calls = []
    monkeypatch.setattr(native, "_load_original", lambda: None)
    monkeypatch.setattr(native.ImageGrab, "grab",
                        lambda **kwargs: calls.append(kwargs) or
                        Image.new("RGB", (170, 70), (44, 77, 110)))
    report = {}
    result = native.grab_region_original((20, 30, 190, 100), report)
    assert result.size == (170, 70)
    assert calls == [{"bbox": (20, 30, 190, 100), "all_screens": True}]
    assert report["method"] == "desktop_visible_fallback"


def test_original_native_blank_is_not_used_instead_of_current_game_pixels(monkeypatch):
    img = Image.new("RGB", (85, 40), (0, 0, 0))
    stream = BytesIO()
    img.save(stream, format="BMP")
    payload = stream.getvalue()

    def return_black(hwnd, x1, y1, x2, y2, callback, curr):
        data = (ctypes.c_ubyte * len(payload)).from_buffer_copy(payload)
        callback(data, len(payload))
        return True

    monkeypatch.setattr(native, "_load_original", lambda: return_black)
    monkeypatch.setattr(native.ImageGrab, "grab",
                        lambda **kwargs: Image.new("RGB", (85, 40), (17, 32, 125)))
    assert native.grab_region_original((0, 0, 85, 40)).getpixel((1, 1)) == (17, 32, 125)


def test_completed_ocr_gate_is_from_end_not_start(monkeypatch):
    import game_reader.app as app_module
    now = time.monotonic()
    app = ReaderApp.__new__(ReaderApp)
    app.closed = False
    app._choosing_region = False
    app.setting_hotkey = False
    app.mouse_mode = "region"
    app.busy = app.region_ocr_busy = app.hover_ocr_busy = False
    app.pending_full_capture = False
    app.root = SimpleNamespace(state=lambda: "iconic")
    app._region_job_id = 2
    app.mode_generation = 5
    app._region_invalid_reported = False
    app._region_last_fingerprint = None
    app._region_next_due = 0
    app._region_last_ocr_at = now
    app._fixed_region_box = lambda: (20, 20, 240, 110)
    app.settings = {"fixed_monitor": [0, 0, 320, 200],
                    "region_strategy": "change", "region_period_ms": 300}
    assert not app.start_region_scan(force=False)
    assert not app.region_ocr_busy
    assert app._region_next_due > now

    # Elapsed >300ms since completion permits normal screenshot/recognition.
    monkeypatch.setattr(app_module, "grab_region_original",
                        lambda b: Image.new("RGB", (220, 90), (32, 61, 98)))
    monkeypatch.setattr(app_module, "foreground_window_id", lambda: 42)
    from queue import Queue
    from threading import Lock
    app._region_last_ocr_at = now - 0.6
    app._ocr_lock = Lock()
    app.events = Queue()
    app.ocr_worker = SimpleNamespace(recognize=lambda image, origin, tier: [])
    assert app.start_region_scan()
    event = app.events.get(timeout=3)
    assert event[0] == "region_ok" and event[3] == []
