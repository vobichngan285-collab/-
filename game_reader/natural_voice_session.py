"""Reuse the original author's unmodified native Microsoft voice engine.

Only one native process is kept alive for each selected voice/config pair.
The speech worker owns this session, avoiding per-utterance package scans,
DLL discovery, and nested process initialization. No license is persisted here.
"""
from __future__ import annotations

from .ms_voice_discovery import (discover_natural_voices, choose_natural_voice,
                                 inspect_local_voice_config, load_user_config)
from .luna_natural_voice import make_ssml
from .upstream_luna_pipe import OriginalLunaPipe, runtime_directory
from .natural_voice_errors import VoiceSetupError


class NaturalVoiceSession:
    def __init__(self):
        self.engine = None
        self.identity = None
        self.starts = 0

    def prepare(self, config_path: str, voice_id: str) -> None:
        key = (config_path, voice_id)
        if self.engine is not None and key == self.identity:
            return
        self.close()
        installed = choose_natural_voice(voice_id, discover_natural_voices())
        if installed is None:
            raise VoiceSetupError("selected_voice_package_not_installed")
        status = inspect_local_voice_config(config_path)
        if status != "ok":
            raise VoiceSetupError(status)
        license_text, _ = load_user_config(config_path)
        if not license_text:
            raise VoiceSetupError("local_voice_config_changed_during_read")
        try:
            runtime_directory()
        except (OSError, FileNotFoundError):
            raise VoiceSetupError("natural_voice_runtime_not_found") from None
        engine = OriginalLunaPipe()
        try:
            engine.start(installed.path, license_text)
        except Exception:
            engine.close()
            raise
        self.engine = engine
        self.identity = key
        self.starts += 1

    def synthesize(self, config_path: str, voice_id: str, text: str, speed=0) -> bytes:
        self.prepare(config_path, voice_id)
        return self.engine.speak_ssml(make_ssml(text, int(speed)))

    def close(self) -> None:
        old, self.engine = self.engine, None
        self.identity = None
        if old is not None:
            old.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
