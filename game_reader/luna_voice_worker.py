"""One-shot isolated worker for installed Windows natural voice packages.

The original unmodified LunaSubprocess64.exe performs synthesis; this worker
only selects an installed system package and forwards the user's local license.
It never prints license text, private paths, or raw SDK error messages.
"""
from __future__ import annotations
import base64
import json
import sys

from .ms_voice_discovery import (discover_natural_voices, choose_natural_voice,
                                 load_user_config, inspect_local_voice_config)
from .luna_natural_voice import make_ssml
from .upstream_luna_pipe import OriginalLunaPipe, runtime_directory

MAX_TEXT = 2000
MAX_AUDIO = 16 * 1024 * 1024


class VoiceSetupError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def synthesize_with_installed_voice(config_path: str, voice_id: str, text: str, speed=0) -> bytes:
    """Luna upstream stages: find package -> locate SDK -> supply config -> speak."""
    found = discover_natural_voices()
    selected = choose_natural_voice(voice_id, found)
    if selected is None:
        raise VoiceSetupError("selected_voice_package_not_installed")
    config_code = inspect_local_voice_config(config_path)
    if config_code != "ok":
        raise VoiceSetupError(config_code)
    license_text, _ = load_user_config(config_path)
    if not license_text:
        # An externally edited file can change between preflight and load.
        raise VoiceSetupError("local_voice_config_changed_during_read")
    # Stage check is separated from native startup so failures are attributable.
    try:
        runtime_directory()
    except (OSError, FileNotFoundError):
        raise VoiceSetupError("natural_voice_runtime_not_found") from None
    with OriginalLunaPipe() as engine:
        engine.start(selected.path, license_text)
        return engine.speak_ssml(make_ssml(text, int(speed)))


def process_request(request: dict, synthesize=synthesize_with_installed_voice) -> dict:
    if isinstance(request, dict) and request.get("command") == "check_config":
        status = inspect_local_voice_config(request.get("config_path", ""))
        # Presence-only test: no license, local paths or JSON text in response.
        return {"ok": status == "ok", "stage": "config_read", "code": status}
    if not isinstance(request, dict) or request.get("command") != "speak":
        return {"ok": False, "stage": "request", "code": "unsupported_request"}
    content, config_path, voice_id = (request.get(k) for k in ("text", "config_path", "voice_id"))
    if not isinstance(content, str) or not 0 < len(content) <= MAX_TEXT:
        return {"ok": False, "stage": "request", "code": "invalid_text"}
    if not isinstance(voice_id, str) or not voice_id.startswith("natural:"):
        return {"ok": False, "stage": "selection", "code": "invalid_voice_id"}
    if not isinstance(config_path, str):
        return {"ok": False, "stage": "request", "code": "invalid_config_path"}
    try:
        wav = synthesize(config_path, voice_id, content, speed=int(request.get("rate", 0)))
        if len(wav) > MAX_AUDIO or wav[:4] != b"RIFF" or wav[8:12] != b"WAVE":
            return {"ok": False, "stage": "synthesis", "code": "invalid_wav"}
        return {"ok": True, "wav": base64.b64encode(wav).decode("ascii"),
                "audio_size": len(wav), "engine": "official_luna_unmodified"}
    except VoiceSetupError as exc:
        return {"ok": False, "stage": "discovery_or_setup", "code": exc.code}
    except FileNotFoundError:
        return {"ok": False, "stage": "native_engine", "code": "original_luna_engine_missing"}
    except PermissionError:
        return {"ok": False, "stage": "native_engine", "code": "windows_access_denied"}
    except TimeoutError:
        return {"ok": False, "stage": "native_engine", "code": "native_engine_timeout"}
    except RuntimeError:
        return {"ok": False, "stage": "synthesis", "code": "embedded_sdk_rejected_synthesis"}
    except (OSError, ValueError):
        return {"ok": False, "stage": "ipc_or_synthesis", "code": "native_pipe_or_audio_error"}
    except Exception:
        return {"ok": False, "stage": "unexpected", "code": "unexpected_voice_error"}


def main() -> int:
    """Serve newline-framed requests until EOF; keep Luna engine alive.

    This replaces a new Python+Luna process per speech request with a single
    session. It is still local and uses the original unmodified author EXE.
    """
    from .natural_voice_session import NaturalVoiceSession
    with NaturalVoiceSession() as session:
        while True:
            try:
                raw = sys.stdin.buffer.readline(MAX_TEXT * 4 + 12000)
                if not raw:
                    break
                request = json.loads(raw.decode("utf-8-sig"))
                if not isinstance(request, dict):
                    reply = {"ok": False, "stage": "request",
                             "code": "invalid_request_json"}
                elif request.get("command") == "exit":
                    break
                elif request.get("command") == "prepare":
                    try:
                        config_path = request.get("config_path", "")
                        voice_id = request.get("voice_id", "")
                        session.prepare(config_path, voice_id)
                        reply = {"ok": True, "stage": "voice_ready",
                                 "code": "native_engine_reused_or_ready"}
                    except VoiceSetupError as exc:
                        reply = {"ok": False, "stage": "discovery_or_setup", "code": exc.code}
                    except FileNotFoundError:
                        reply = {"ok": False, "stage": "native_engine",
                                 "code": "original_luna_engine_missing"}
                    except (TimeoutError, OSError):
                        reply = {"ok": False, "stage": "native_engine",
                                 "code": "native_engine_initialization_failed"}
                    except Exception:
                        reply = {"ok": False, "stage": "native_engine",
                                 "code": "native_engine_unexpected_failure"}
                else:
                    reply = process_request(request, synthesize=session.synthesize)
            except (ValueError, TypeError, UnicodeError):
                reply = {"ok": False, "stage": "request", "code": "invalid_request_json"}
            except Exception:
                reply = {"ok": False, "stage": "unexpected", "code": "worker_error"}
            # ASCII-only framing prevents Windows console code pages from
            # corrupting stdout; no private paths/license values are returned.
            print(json.dumps(reply, ensure_ascii=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
