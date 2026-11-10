"""V1.2.1 cue/audio and mouse speech speed regressions (no real voice license).

These tests are safe on CI runners without audio devices. Real Windows
speaker output must still be checked on the user's PC with 试听叮声.
"""
from __future__ import annotations

from collections import OrderedDict
import io
from queue import Queue
from threading import Condition, RLock, Event
import time
import wave

import pytest

from game_reader.cues import make_click_wave, CuePlayer
from game_reader.cue_audio_win import decode_cue
from game_reader.luna_bridge import LunaNaturalBridge
from game_reader.speech import SpeechWorker


def test_success_cue_is_audible_strength_and_valid_16bit_pcm():
    src = make_click_wave("complete")
    pcm, rate = decode_cue(src)
    assert 16000 <= rate <= 48000
    assert 0.17 <= len(pcm) / (rate * 2) <= 0.20
    import array
    signal = array.array("h")
    signal.frombytes(pcm)
    assert max(abs(s) for s in signal) >= 7500
    assert len(signal) >= 3500


def test_cue_decoder_rejects_invalid_sound():
    with pytest.raises((ValueError, EOFError, wave.Error)):
        decode_cue(b"not a wav")
    with pytest.raises(ValueError):
        decode_cue(b"x" * 600000)


def test_cue_player_does_not_wait_for_wave_output(monkeypatch):
    import game_reader.cues as cues_module
    started, release = Event(), Event()
    def fake_output(audio):
        started.set()
        release.wait(1)
    monkeypatch.setattr(cues_module, "play_cue", fake_output)
    player = CuePlayer()
    before = time.monotonic()
    player.play("complete")
    assert time.monotonic() - before < 0.08
    assert started.wait(0.5)
    release.set()
    player.shutdown()


def _cache_bridge():
    voice = LunaNaturalBridge.__new__(LunaNaturalBridge)
    voice._condition = Condition(RLock())
    voice._wave_cache = OrderedDict()
    voice._wave_cache_bytes = 0
    return voice


def test_short_label_cache_is_bounded_by_size_entries_and_time(monkeypatch):
    voice = _cache_bridge()
    for idx in range(24):
        voice._cache_save((str(idx), 0), b"W" * 2048)
    assert len(voice._wave_cache) == 16
    assert voice._wave_cache_bytes <= 4 * 1024 * 1024
    assert voice._cache_read(("23", 0)) == b"W" * 2048
    assert voice._cache_read(("23", 3)) is None
    assert voice._cache_read(("0", 0)) is None
    voice._cache_save(("long", 0), b"W" * (512 * 1024 + 1))
    assert voice._cache_read(("long", 0)) is None
    key = ("23", 0)
    wav, stamp = voice._wave_cache[key]
    voice._wave_cache[key] = (wav, time.monotonic() - 61)
    assert voice._cache_read(key) is None
    voice.clear_cache()
    assert not voice._wave_cache and voice._wave_cache_bytes == 0


def test_manual_clear_sends_cache_invalidation_without_extra_ocr():
    worker = SpeechWorker.__new__(SpeechWorker)
    worker._commands = Queue()
    worker.clear_cache()
    assert worker._commands.get_nowait() == ("clear_cache", None)


def test_success_cue_playback_uses_independent_waveout_not_winsound():
    import inspect
    from game_reader.cue_audio_win import play_cue
    source = inspect.getsource(play_cue)
    assert "waveOutWrite" in source and "waveOutOpen" in source
    assert "winsound.PlaySound" not in source
