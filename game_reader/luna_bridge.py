"""Windows playback bridge for system-discovered natural voice synthesis.

Never stores the license field in GameTextReader settings, command arguments
or diagnostics. A short-lived isolated subprocess reads the external JSON.
WAV playback uses Windows winsound; only async playback REQUEST is reported.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading


class LunaNaturalBridge:
    def __init__(self, config_path: str, voice_id: str, on_error=None, on_event=None):
        self.voice_id = voice_id
        self.config_path = str(config_path)
        self.on_error = on_error
        self.on_event = on_event
        self.rate = 0
        self.volume = 100
        self._lock = threading.RLock()
        self._generation = 0
        self._process = None
        self._wav_path: Path | None = None

    @staticmethod
    def _command() -> list[str]:
        if getattr(sys, "frozen", False):
            return [sys.executable, "--luna-worker"]
        return [sys.executable, "-m", "game_reader.luna_voice_worker"]

    def set_rate(self, rate):
        self.rate = max(-8, min(8, int(rate)))

    def set_volume(self, volume):
        self.volume = max(0, min(100, int(volume)))

    def stop(self):
        old_process = None
        old_wav = None
        with self._lock:
            self._generation += 1
            old_process, self._process = self._process, None
            old_wav, self._wav_path = self._wav_path, None
        if old_process is not None and old_process.poll() is None:
            old_process.terminate()
        if sys.platform == "win32":
            try:
                import winsound
                winsound.PlaySound(None, 0)
            except Exception:
                pass
        if old_wav is not None:
            try:
                old_wav.unlink(missing_ok=True)
            except OSError:
                pass

    def speak(self, text: str):
        self.stop()
        with self._lock:
            generation = self._generation
            path = self.config_path
            voice_id = self.voice_id
            rate = self.rate
            volume = self.volume
        threading.Thread(target=self._synthesize_play,
                         args=(generation, path, voice_id, text, rate, volume),
                         daemon=True, name="LunaNaturalEmbedded").start()

    def _synthesize_play(self, generation, config_path, voice_id, text, rate, volume):
        proc = None
        try:
            if not voice_id or not voice_id.startswith("natural:"):
                raise ValueError("尚未选择已安装的系统自然语音包")
            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            proc = subprocess.Popen(
                self._command(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                **kwargs)
            with self._lock:
                if generation != self._generation:
                    proc.terminate()
                    return
                self._process = proc
            request = json.dumps({"command": "speak",
                                  "config_path": config_path, "voice_id": voice_id, "text": text,
                                  "rate": rate}, ensure_ascii=False) + "\n"
            stdout, _ = proc.communicate(request, timeout=75)
            with self._lock:
                if generation != self._generation:
                    return
                self._process = None
            reply = json.loads(stdout.strip())
            if not reply.get("ok"):
                raise RuntimeError("stage=" + str(reply.get("stage", "unknown")) +
                                   "; code=" + str(reply.get("code", "unknown"))[:90])
            wav = base64.b64decode(reply["wav"], validate=True)
            if len(wav) > 16 * 1024 * 1024 or wav[:4] != b"RIFF":
                raise ValueError("语音工作进程返回的 WAV 无效")
            if sys.platform != "win32":
                raise RuntimeError("自然语音播放功能只在 Windows 上可用")
            import winsound
            with tempfile.NamedTemporaryFile(
                    prefix="GameTextReader_luna_", suffix=".wav",
                    delete=False) as handle:
                handle.write(wav)
                new_wav = Path(handle.name)
            with self._lock:
                if generation != self._generation:
                    new_wav.unlink(missing_ok=True)
                    return
                self._wav_path = new_wav
            # SND_ASYNC supports immediate mouse-hover interruption via stop().
            # Windows system volume is used; volume slider remains an SDK
            # synthesis property in a future implementation, not silently
            # simulated by altering PCM data.
            winsound.PlaySound(str(new_wav),
                               winsound.SND_FILENAME | winsound.SND_ASYNC |
                               winsound.SND_NODEFAULT)
            if self.on_event:
                self.on_event(f"Luna 自然语音已生成 WAV 并请求本地播放 {len(text)} 字；"
                              "不代表扬声器实际出声")
        except subprocess.TimeoutExpired:
            if proc is not None and proc.poll() is None:
                proc.kill()
            if self.on_error:
                self.on_error("Luna 微软自然语音合成超时")
        except Exception as exc:
            with self._lock:
                current = generation == self._generation
            if current and self.on_error:
                # These are our own fixed stage/code identifiers, never SDK's raw text.
                category = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
                self.on_error("系统自然语音合成失败：" + category[:160])
        finally:
            with self._lock:
                if self._process is proc:
                    self._process = None

    def close(self):
        self.stop()
