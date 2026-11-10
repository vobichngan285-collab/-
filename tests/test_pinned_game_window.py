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


def test_full_screen_uses_bound_game_rect_and_always_reads_fresh_desktop(monkeypatch):
    from game_reader import win_screen
    binding = GameWindowBinding(foreground=lambda: 111,
                                process_id=lambda hwnd: {111: 34}.get(hwnd, 0),
                                own_pid=99)
    bound = binding.target()
    assert bound == 111
    shots = []
    monkeypatch.setattr(win_screen, "monitor_rect_at_cursor", lambda: (0, 0, 640, 480))
    monkeypatch.setattr(win_screen, "game_client_rect",
                        lambda hwnd: (10, 20, 500, 400) if hwnd == bound else None)

    # Simulate the user opening 'Start Game': same HWND, NEW visible pixels.
    def desktop_capture(**kwargs):
        shots.append(kwargs)
        scene_color = "navy" if len(shots) == 1 else "yellow"
        return Image.new("RGB", (490, 380), scene_color)
    monkeypatch.setattr(win_screen.ImageGrab, "grab", desktop_capture)
    metadata1, metadata2 = {}, {}
    first, origin1 = win_screen.grab_current_monitor(bound, report=metadata1)
    second, origin2 = win_screen.grab_current_monitor(bound, report=metadata2)
    assert origin1 == origin2 == (10, 20)
    assert first.getpixel((20, 20)) != second.getpixel((20, 20))
    assert first.size == second.size == (490, 380)
    assert shots == [{"bbox": (10, 20, 500, 400), "all_screens": True}] * 2
    assert metadata1["method"] == metadata2["method"] == "desktop_game_client"
    assert metadata1["bound_hwnd"] is metadata2["bound_hwnd"] is True


def test_no_bound_game_preserves_original_v12_full_monitor(monkeypatch):
    from game_reader import win_screen
    monkeypatch.setattr(win_screen, "monitor_rect_at_cursor",
                        lambda: (-1920, 0, 0, 1080))
    seen = []
    monkeypatch.setattr(win_screen.ImageGrab, "grab",
                        lambda **kw: seen.append(kw) or Image.new("RGB", (1920, 1080)))
    report = {}
    image, origin = win_screen.grab_current_monitor(report=report)
    assert image.size == (1920, 1080) and origin == (-1920, 0)
    assert seen == [{"bbox": (-1920, 0, 0, 1080), "all_screens": True}]
    assert report["method"] == "desktop_monitor"


def test_window_onto_monitor_is_intersected_without_fake_window_pixels(monkeypatch):
    from game_reader import win_screen
    monkeypatch.setattr(win_screen, "monitor_rect_at_cursor",
                        lambda: (0, 0, 1920, 1080))
    monkeypatch.setattr(win_screen, "game_client_rect", lambda hwnd: (-100, -20, 1300, 900))
    calls = []
    monkeypatch.setattr(win_screen.ImageGrab, "grab",
                        lambda **kw: calls.append(kw) or Image.new("RGB", (1300, 900)))
    image, origin = win_screen.grab_current_monitor(7)
    assert image.size == (1300, 900) and origin == (0, 0)
    assert calls == [{"bbox": (0, 0, 1300, 900), "all_screens": True}]


def test_minimized_or_other_monitor_game_reports_error_not_success(monkeypatch):
    import pytest
    from game_reader import win_screen
    monkeypatch.setattr(win_screen, "monitor_rect_at_cursor",
                        lambda: (0, 0, 1920, 1080))
    monkeypatch.setattr(win_screen, "game_client_rect", lambda hwnd: None)
    monkeypatch.setattr(win_screen.ImageGrab, "grab",
                        lambda **kwargs: (_ for _ in ()).throw(AssertionError("should not grab")))
    with pytest.raises(RuntimeError, match="游戏窗口"):
        win_screen.grab_current_monitor(7)
    monkeypatch.setattr(win_screen, "game_client_rect",
                        lambda hwnd: (2500, 0, 3000, 500))
    with pytest.raises(RuntimeError, match="不重叠"):
        win_screen.grab_current_monitor(7)


def test_hover_and_fixed_region_are_direct_desktop_crops(monkeypatch):
    from game_reader import win_screen, luna_capture
    observed = []
    monkeypatch.setattr(luna_capture, "_gdi_window_box",
                        lambda *args: (_ for _ in ()).throw(AssertionError("GDI prohibited")))
    box = (20, 40, 260, 180)
    monkeypatch.setattr(win_screen.ImageGrab, "grab",
                        lambda **kwargs: observed.append(kwargs) or Image.new("RGB", (240, 140)))
    image = win_screen.grab_game_rect(box, bound_hwnd=123)
    assert image.size == (240, 140)
    assert observed == [{"bbox": box, "all_screens": True}]
