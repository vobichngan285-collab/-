"""Independent natural-voice synthesis worker for the original Luna JSON config.

Separate process isolates Microsoft's embedded SDK from the OCR/Tk process.
Input: single JSON request on stdin, containing only config-file path and text.
The original MicrosoftWindows.Voice.License stays ONLY in the user's file.
Output: a JSON message with base64 PCM WAV, or redacted error state.
"""
from __future__ import annotations

import base64
import json
import sys

from .luna_natural_voice import synthesize_exact_config

MAX_TEXT = 2000
MAX_AUDIO = 16 * 1024 * 1024


def process_request(request: dict, synthesize=synthesize_exact_config) -> dict:
    if not isinstance(request, dict) or request.get("command") != "speak":
        return {"ok": False, "error": "unsupported_request"}
    text = request.get("text")
    path = request.get("config_path")
    if not isinstance(text, str) or not 0 < len(text) <= MAX_TEXT:
        return {"ok": False, "error": "invalid_text"}
    if not isinstance(path, str) or not path:
        return {"ok": False, "error": "missing_local_config"}
    try:
        wav = synthesize(path, text, speed=int(request.get("rate", 0)))
        if len(wav) > MAX_AUDIO:
            return {"ok": False, "error": "audio_too_large"}
        return {"ok": True, "wav": base64.b64encode(wav).decode("ascii"),
                "audio_size": len(wav)}
    except FileNotFoundError:
        return {"ok": False, "error": "voice_package_unavailable"}
    except PermissionError:
        return {"ok": False, "error": "sdk_model_not_authorized"}
    except Exception as exc:
        # Do not propagate SDK error details: some SDK versions include source
        # paths or the exact license property in exception strings.
        return {"ok": False, "error": "embedded_sdk_synthesis_failed",
                "error_type": type(exc).__name__}


def main() -> int:
    try:
        line = sys.stdin.readline(MAX_TEXT * 4 + 10240)
        message = process_request(json.loads(line))
    except (ValueError, TypeError, json.JSONDecodeError):
        message = {"ok": False, "error": "invalid_request_json"}
    print(json.dumps(message, ensure_ascii=False), flush=True)
    return 0 if message.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
