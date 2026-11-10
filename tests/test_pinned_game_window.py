"""Regression for LunaTranslator-style persistent HWND source binding.

Tests never open games, access voice licenses or store OCR screenshots.
"""
from __future__ import annotations
from PIL import Image

from game_reader.game_window import GameWindowBinding
from game_reader import luna_capture


def test_pinned_game_window_survives_menu_page_and_foreground_changes():
    present = {121: 6001, 122: 6001, 999: 7001}
    foreground = [121]
    binding = GameWindowBinding(foreground=lambda: foreground[0],
                                process_id=lambda hwnd: present.get(hwnd, 0),
                                own_pid=8888)
    assert binding.target() == 121
    assert binding.hwnd == 121 and binding.pid == 6001
    foreground[0] = 122  # Child game popup, same process and same game.
    assert binding.target() == 121
    assert binding.is_active()
    foreground[0] = 999  # Another application briefly overlays the game.
    assert binding.target() == 121
    assert not binding.is_active()
    foreground[0] = 121
    assert binding.target() == 121
    assert binding.is_active()
    del present[121]  # Game closed; reuse is now forbidden.
    assert binding.target() == 0
    foreground[0] = 999
    assert binding.target() == 999
    assert binding.pid == 7001


def test_never_bind_own_tk_or_overlay_window():
    foreground = [17]
    binding = GameWindowBinding(foreground=lambda: foreground[0],
                                process_id=lambda hwnd: {17: 8888, 42: 9009}.get(hwnd, 0),
                                own_pid=8888)
    assert binding.target() == 0
    foreground[0] = 42
    assert binding.target() == 42


def test_reused_hwnd_with_different_process_forces_rebinding():
    present = {100: 3, 200: 4}
    fg = [100]
    binder = GameWindowBinding(foreground=lambda: fg[0],
                               process_id=lambda hwnd: present.get(hwnd, 0),
                               own_pid=5)
    assert binder.target() == 100
    present[100] = 8  # Windows recycled the numerical handle.
    fg[0] = 200
    assert binder.target() == 200
    assert binder.pid == 4


def test_every_luna_capture_is_fresh_and_provenance_is_reported(monkeypatch):
    calls = []
    raw = Image.new("RGB", (200, 100), "white")
    def capture_gdi(hwnd, box):
        calls.append(("gdi", hwnd))
        return raw.copy()
    monkeypatch.setattr(luna_capture, "_gdi_window_box", capture_gdi)
    report1, report2 = {}, {}
    first = luna_capture.capture_rect((0, 0, 200, 100), 123, report1)
    second = luna_capture.capture_rect((0, 0, 200, 100), 123, report2)
    assert first is not second
    assert calls == [("gdi", 123), ("gdi", 123)]
    assert report1 == report2 == {"method": "window_gdi", "bound_hwnd": True}
    monkeypatch.setattr(luna_capture, "_gdi_window_box", lambda hwnd, box: None)
    monkeypatch.setattr(luna_capture.ImageGrab, "grab", lambda **kw: raw.copy())
    report3 = {}
    assert luna_capture.capture_rect((0, 0, 200, 100), 123, report3).size == (200, 100)
    assert report3 == {"method": "desktop", "bound_hwnd": True}


def test_full_screen_uses_saved_hwnd_even_if_foreground_is_another_window(monkeypatch):
    from game_reader import win_screen
    binder = GameWindowBinding(foreground=lambda: 111,
                               process_id=lambda hwnd: {111: 34}.get(hwnd, 0),
                               own_pid=99)
    bound = binder.target()
    assert bound == 111
    captured = []
    monkeypatch.setattr(win_screen, "monitor_rect_at_cursor", lambda: (0, 0, 640, 480))
    def fake_capture(box, hwnd, report=None):
        captured.append((box, hwnd))
        return Image.new("RGB", (640, 480), "gray")
    monkeypatch.setattr(win_screen, "capture_rect", fake_capture)
    report = {}
    assert win_screen.grab_current_monitor(bound, report=report)[1] == (0, 0)
    assert captured == [((0, 0, 640, 480), 111)]
