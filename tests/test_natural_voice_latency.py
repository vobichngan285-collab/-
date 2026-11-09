"""Isolated, license-free regression checks for persistent Microsoft natural TTS.

Never invoke a real Microsoft voice or store the user's private license in CI.
"""
from __future__ import annotations

import io
import json
import sys
from types import SimpleNamespace


def test_same_voice_reuses_original_native_engine(monkeypatch):
    import game_reader.natural_voice_session as m
    engines = []
    class FakeEngine:
        def __init__(self):
            engines.append(self)
            self.start_args = None
            self.closed = False
            self.messages = []
        def start(self, path, license_text):
            self.start_args = (path, license_text)
        def speak_ssml(self, ssml):
            self.messages.append(ssml)
            return b"RIFF\x00\x00\x00\x00WAVE"
        def close(self):
            self.closed = True

    monkeypatch.setattr(m, "OriginalLunaPipe", FakeEngine)
    monkeypatch.setattr(m, "discover_natural_voices", lambda: [object()])
    monkeypatch.setattr(m, "choose_natural_voice",
                        lambda voice_id, packages: SimpleNamespace(path="C:/FAKE_voice"))
    monkeypatch.setattr(m, "inspect_local_voice_config", lambda path: "ok")
    monkeypatch.setattr(m, "load_user_config", lambda path: ("FAKE_CI_VALUE", ""))
    monkeypatch.setattr(m, "runtime_directory", lambda: "C:/FAKE_runtime")

    with m.NaturalVoiceSession() as session:
        a = session.synthesize("C:/FAKE_config", "natural:Yunxi", "第一句话")
        b = session.synthesize("C:/FAKE_config", "natural:Yunxi", "第二句话")
        assert a.startswith(b"RIFF") and b.startswith(b"RIFF")
        assert session.starts == 1
        assert len(engines) == 1
        assert len(engines[0].messages) == 2
        assert not engines[0].closed
        session.synthesize("C:/FAKE_config", "natural:Xiaoxiao", "换音色")
        assert session.starts == 2
        assert len(engines) == 2
        assert engines[0].closed
    assert engines[1].closed


def test_frozen_worker_handles_multiple_requests_in_one_process(monkeypatch, capsys, tmp_path):
    import game_reader.natural_voice_session as ns
    from game_reader.luna_voice_worker import main
    instances = []
    class FakeSession:
        def __init__(self):
            instances.append(self)
            self.calls = []
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def synthesize(self, config, voice, text, speed=0):
            self.calls.append((voice, text))
            return b"RIFF\x00\x00\x00\x00WAVE"

    monkeypatch.setattr(ns, "NaturalVoiceSession", FakeSession)
    requests = [
        {"command": "speak", "config_path": "中文路径/FAKE.json",
         "voice_id": "natural:Yunxi", "text": "中文一"},
        {"command": "speak", "config_path": "中文路径/FAKE.json",
         "voice_id": "natural:Yunxi", "text": "中文二"},
        {"command": "exit"}
    ]
    wire = "".join(json.dumps(q, ensure_ascii=False) + "\n" for q in requests)
    class Input:
        def __init__(self, raw):
            self.buffer = io.BytesIO(raw)
    monkeypatch.setattr(sys, "stdin", Input(wire.encode("utf-8")))
    assert main() == 0
    replies = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert len(replies) == 2
    assert all(x["ok"] for x in replies)
    assert len(instances) == 1
    assert len(instances[0].calls) == 2


def test_stop_clears_audio_without_terminating_cached_worker():
    import threading
    from game_reader.luna_bridge import LunaNaturalBridge
    bridge = LunaNaturalBridge.__new__(LunaNaturalBridge)
    bridge._condition = threading.Condition(threading.RLock())
    bridge._generation = 4
    bridge._pending = (4, "old", 0, 1.0)
    bridge._closing = False
    proc = object()
    bridge._proc = proc
    calls = []
    bridge._stop_audio_locked = lambda: calls.append("stopped")
    bridge.stop()
    assert bridge._generation == 5
    assert bridge._pending is None
    assert bridge._proc is proc
    assert calls == ["stopped"]


def test_playback_lock_rejects_stale_voice_after_pointer_moved(monkeypatch):
    import threading
    import types
    from game_reader.luna_bridge import LunaNaturalBridge
    played = []
    fake = types.SimpleNamespace(
        SND_FILENAME=1, SND_ASYNC=2, SND_NODEFAULT=4,
        PlaySound=lambda *args: played.append(args)
    )
    monkeypatch.setitem(sys.modules, "winsound", fake)
    bridge = LunaNaturalBridge.__new__(LunaNaturalBridge)
    bridge._condition = threading.Condition(threading.RLock())
    bridge._generation = 9
    bridge._closing = False
    bridge._wav_path = None
    bridge._stop_audio_locked = lambda: None
    if sys.platform == "win32":
        assert bridge._play_if_current(8, b"RIFF\x00\x00\x00\x00WAVE") is False
        assert played == []
        assert bridge._play_if_current(9, b"RIFF\x00\x00\x00\x00WAVE") is True
        assert len(played) == 1
        bridge._wav_path.unlink(missing_ok=True)
