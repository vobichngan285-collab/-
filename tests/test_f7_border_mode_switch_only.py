"""Regression: F7 is a display-only preference across F9 mode switches.

This test uses a lightweight ReaderApp fixture and never invokes game capture,
OCR inference, speech synthesis, Windows overlays or real input hardware.
"""
from __future__ import annotations

from types import SimpleNamespace
from game_reader.app import ReaderApp


def test_f7_hidden_region_border_stays_hidden_when_switching_back():
    app = ReaderApp.__new__(ReaderApp)
    app.mouse_mode = "region"
    app.settings = {
        "show_scan_frame": True,
        "mode_voice_hint": False,
        "fixed_region": [100, 200, 700, 500],
        "fixed_monitor": [0, 0, 1920, 1080],
    }
    app.mouse_mode_var = SimpleNamespace(set=lambda value: None)
    app.root = SimpleNamespace(state=lambda: "iconic")
    app.mode_generation = 0
    app._region_job_id = 0
    app._region_border_visible = True
    app.overlay = None
    app.scan_frame = None
    app.fixed_frame = None
    app.hover = SimpleNamespace(reset=lambda: None)
    app.speech = SimpleNamespace(stop=lambda: None)
    app.status = lambda text: None
    redraws = []
    app.update_scan_frame = lambda: redraws.append(app._region_border_visible)

    # Hide using F7's existing callback; this MUST NOT disable OCR globally.
    app.toggle_region_border()
    assert app._region_border_visible is False
    assert app.settings["show_scan_frame"] is True

    # Leaving and reentering through the public F9 mode switch preserves F7.
    app._switch_mouse_mode("hover")
    app._switch_mouse_mode("region")
    assert app._region_border_visible is False
    assert app.settings["show_scan_frame"] is True

    # A second F7 intentionally restores the green frame.
    app.toggle_region_border()
    assert app._region_border_visible is True
    assert redraws == [False, True]


def test_f7_visible_region_border_stays_visible_across_mode_switch():
    app = ReaderApp.__new__(ReaderApp)
    app.mouse_mode = "hover"
    app.settings = {"show_scan_frame": True, "mode_voice_hint": False,
                    "fixed_region": None, "fixed_monitor": None}
    app.mouse_mode_var = SimpleNamespace(set=lambda text: None)
    app.root = SimpleNamespace(state=lambda: "iconic")
    app.mode_generation = 0
    app._region_job_id = 0
    app._region_border_visible = True
    app.overlay = app.scan_frame = app.fixed_frame = None
    app.hover = SimpleNamespace(reset=lambda: None)
    app.speech = SimpleNamespace(stop=lambda: None)
    app.status = lambda text: None

    app._switch_mouse_mode("region")
    assert app._region_border_visible is True
