"""Regression coverage for user-confirmed Windows pointer OCR refinements.

Never load a Windows voice license, access a game, or invoke the ONNX model
from these pure interaction tests. Frozen EXE smoke tests run in Windows CI.
"""
from __future__ import annotations

import io
from queue import Queue
from threading import Lock
from types import SimpleNamespace
import wave

from PIL import Image

from game_reader.app import ReaderApp
from game_reader.core import OCRLine
from game_reader.cues import make_click_wave
from game_reader.hover_modes import (RelativeRegion, capture_box,
                                     region_from_drag, sanitize_hotkeys)


def test_pointer_drag_anchors_to_actual_cursor_and_preserves_all_offsets():
    # The old picker used the monitor centre, ignoring where the mouse was.
    cursor = (225, 165)
    left_up = region_from_drag((225, 165, 100, 80), cursor)
    right_down = region_from_drag((225, 165, 420, 275), cursor)
    assert left_up.as_list() == [-125, -85, 125, 85]
    assert right_down.as_list() == [0, 0, 195, 110]
    assert capture_box(left_up, (800, 600), (0, 0, 1920, 1080)) == (
        675, 515, 800, 600)
    assert capture_box(right_down, (800, 600), (0, 0, 1920, 1080)) == (
        800, 600, 995, 710)


def test_saved_region_keeps_offset_and_all_five_shortcuts_migrate(tmp_path, monkeypatch):
    import json
    import game_reader.app as module
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"region": [165, -105, 550, 300],
        "vk": 119, "mode_vk": 120, "local_vk": 121, "pick_vk": 122}),
        encoding="utf-8")
    monkeypatch.setattr(module, "CONFIG_PATH", settings_file)
    settings = module.read_settings()
    assert settings["region"] == [165, -105, 550, 300]
    assert settings["clear_vk"] == 0x75
    assert settings["success_cue"] is True
    assert len({settings[k] for k in
                ("vk", "mode_vk", "local_vk", "pick_vk", "clear_vk")}) == 5
    assert sanitize_hotkeys({"vk": 0x75})["clear_vk"] != 0x75


def test_picker_release_saves_relative_offset_and_starts_exact_region_ocr():
    app = ReaderApp.__new__(ReaderApp)
    app.closed = False
    app._region_picker = object()
    app._choosing_region = True
    app._region_previous_root_state = "iconic"
    app._picker_anchor = (420, 350)
    app._picker_monitor = (0, 0, 1920, 1080)
    snap = Image.new("RGB", (100, 80), "white")
    app._picker_snapshot = snap
    app._picker_foreground = 123
    app.root = SimpleNamespace(attributes=lambda *args: None,
                               iconify=lambda: None, deiconify=lambda: None)
    app.settings = {"period_ms": 500, "region": [-300, -140, 600, 400]}
    info, started, statuses = [], [], []
    app.region_info_var = SimpleNamespace(set=info.append)
    app.status = statuses.append
    app.persist = lambda: None
    app._hover_last_text = "old"
    app._hover_spoken_cursor = (1, 2)
    app._start_selected_ocr = lambda *args: started.append(args)
    selected = RelativeRegion(10, 70, 260, 150)
    app._region_picked(selected)
    assert app.settings["region"] == [10, 70, 260, 150]
    assert started == [(selected, (420, 350), (0, 0, 1920, 1080), snap, 123)]
    assert app._picker_snapshot is None
    assert "偏移" in info[-1]
    assert not app._choosing_region


def test_manual_clear_invalidates_full_and_inflight_hover_without_new_capture():
    app = ReaderApp.__new__(ReaderApp)
    app.capture_id = 7
    app.mode_generation = 9
    app.pending_full_capture = True
    app.expires_at = 5555
    app.lines = [OCRLine("旧内容", 5, 5, 70, 35)]
    app.last_target = app.lines[0]
    app._hover_last_text = "旧内容"
    app._full_capture_window = 1
    app._hover_spoken_cursor = (100, 100)
    app._hover_spoken_foreground = "GameWindow"
    app.hover = SimpleNamespace(reset=lambda: None)
    stops, displays, notices = [], [], []
    app.speech = SimpleNamespace(stop=lambda: stops.append("stop"))
    app.overlay = None
    app.update_output = displays.append
    app.status = notices.append
    app.clear_results()
    assert (app.capture_id, app.mode_generation) == (8, 10)
    assert app.lines == []
    assert app.expires_at is None and not app.pending_full_capture
    assert app._hover_last_text == "" and app._full_capture_window is None
    assert stops == ["stop"] and displays == [""]
    assert "清空" in notices[-1]


def test_success_chime_only_when_pointer_ocr_has_real_readable_regions():
    class FakeApp:
        def __init__(self):
            self.events = Queue()
            self.capture_id = 2
            self.busy = True
            self.read_btn = SimpleNamespace(configure=lambda **kw: None)
            self.lines = []
            self._full_capture_window = None
            self.hover = SimpleNamespace(reset=lambda: None)
            self.last_target = None
            self.expires_at = None
            self.mouse_mode = "pointer"
            self.settings = {"success_cue": True}
            self.cue_hits = []
            self.cues = SimpleNamespace(play=self.cue_hits.append)
            self.output = []
            self.update_output = self.output.append
            self.status = lambda msg: None
            self.root = SimpleNamespace(after=lambda ms, f: None)
    app = FakeApp()
    app.events.put(("ocr_ok", 2, [], 90, 100))
    ReaderApp.poll_messages(app)
    assert app.cue_hits == []
    app.events.put(("ocr_ok", 2, [OCRLine("碎布", 10, 10, 90, 36)], 80, 100))
    ReaderApp.poll_messages(app)
    assert app.cue_hits == ["complete"]
    app.settings["success_cue"] = False
    app.events.put(("ocr_ok", 2, [OCRLine("石斧", 10, 10, 90, 36)], 80, 100))
    ReaderApp.poll_messages(app)
    assert app.cue_hits == ["complete"]
    app.events.put(("ocr_ok", 1, [OCRLine("旧页", 10, 10, 90, 36)], 80, 100))
    ReaderApp.poll_messages(app)
    assert app.output[-1] == "石斧"


def test_cue_is_short_crisp_audio_not_a_long_blocking_music_asset():
    audio = make_click_wave("complete")
    with wave.open(io.BytesIO(audio), "rb") as f:
        assert f.getnchannels() == 1
        assert f.getsampwidth() == 2
        assert 0.12 <= f.getnframes() / f.getframerate() <= 0.20


def test_old_speech_messages_are_superseded_before_reaching_tts_engine():
    from game_reader.speech import SpeechWorker
    worker = SpeechWorker.__new__(SpeechWorker)
    worker._speech_lock = Lock()
    worker._speech_generation = 0
    worker._commands = Queue()
    worker.speak("旧物品")
    worker.stop()
    worker.speak("新物品")
    first, second, third = [worker._commands.get_nowait() for _ in range(3)]
    assert first == ("latest_speak", ("旧物品", 1))
    assert second == ("stop", None)
    assert third == ("latest_speak", ("新物品", 3))
    assert worker._speech_generation == 3


def test_hover_scheduler_does_not_add_a_full_period_after_slow_recognition(monkeypatch):
    import time
    import game_reader.app as module
    now = time.monotonic()
    monkeypatch.setattr(module, "get_cursor", lambda: (300, 300))
    monkeypatch.setattr(module, "foreground_class", lambda: "GameWindow")
    app = ReaderApp.__new__(ReaderApp)
    app.hover_ocr_busy = True
    app._hover_next_due = now - 0.5
    app.settings = {"period_ms": 400, "filter_english": False,
        "filter_numbers": False, "filter_symbols": False,
        "similarity_enabled": True, "similarity_threshold": 2}
    app.pending_full_capture = False
    app.mode_generation = 3
    app.mouse_mode = "hover"
    app._hover_last_text = ""
    app._hover_spoken_cursor = None
    app._hover_spoken_foreground = None
    app.update_output = lambda text: None
    app.status = lambda text: None
    app.speech = SimpleNamespace(stop=lambda: None)
    app._handle_hover_result(3, [], False, 600, (300, 300), "GameWindow")
    assert app._hover_next_due <= time.monotonic() + 0.12
