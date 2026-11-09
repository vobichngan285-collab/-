"""Persistent, interruptible playback bridge to the ORIGINAL Luna subprocess.

Keep one local Python worker and one unmodified Luna native engine warm for
multiple utterances. Speech requests are serialized, newest one wins, and
stale responses are never played. User license remains in the local JSON;
no key or private model is bundled or logged.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from queue import Empty, Queue
import subprocess
import sys
import tempfile
import threading
import time


class LunaNaturalBridge:
    RESPONSE_TIMEOUT = 30

    def __init__(self, config_path: str, voice_id: str, on_error=None, on_event=None):
        self.config_path = str(config_path)
        self.voice_id = voice_id
        self.on_error = on_error
        self.on_event = on_event
        self.rate = 0
        self.volume = 100
        self._condition = threading.Condition(threading.RLock())
        self._generation = 0
        self._pending = None
        self._warmup_requested = False
        self._closing = False
        self._proc = None
        self._replies = None
        self._wav_path = None
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="PersistentLunaNaturalVoice")
        self._thread.start()

    @staticmethod
    def _command() -> list[str]:
        if getattr(sys, "frozen", False):
            return [sys.executable, "--luna-worker"]
        return [sys.executable, "-m", "game_reader.luna_voice_worker"]

    def set_rate(self, rate):
        with self._condition:
            self.rate = max(-8, min(8, int(rate)))

    def set_volume(self, volume):
        with self._condition:
            self.volume = max(0, min(100, int(volume)))

    def warmup(self):
        """Prepare voice in the background after selection, before first hover."""
        with self._condition:
            if not self._closing:
                self._warmup_requested = True
                self._condition.notify()

    def _stop_audio_locked(self):
        if sys.platform == "win32":
            try:
                import winsound
                winsound.PlaySound(None, 0)
            except Exception:
                pass
        old, self._wav_path = self._wav_path, None
        if old is not None:
            try:
                old.unlink(missing_ok=True)
            except OSError:
                pass

    def stop(self):
        """Stop audio immediately; do not destroy a warm natural voice engine."""
        with self._condition:
            self._generation += 1
            self._pending = None
            self._stop_audio_locked()

    def speak(self, text: str):
        # No new thread/process for every mouse event. The single worker
        # handles at most one active request and one replacement request.
        self.stop()
        with self._condition:
            if self._closing:
                return
            self._pending = (self._generation, str(text), self.rate, time.perf_counter())
            self._condition.notify()

    def _read_stdout(self, process, reply_queue: Queue):
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                reply_queue.put(line)
        except (OSError, ValueError):
            pass
        reply_queue.put(None)

    def _ensure_process(self):
        if self._proc is not None and self._proc.poll() is None:
            return self._proc, self._replies
        self._drop_process()
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.Popen(
            self._command(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1,
            **kwargs)
        replies = Queue()
        self._proc, self._replies = proc, replies
        threading.Thread(target=self._read_stdout, args=(proc, replies),
                         daemon=True, name="LunaVoiceResponseReader").start()
        return proc, replies

    def _drop_process(self):
        old, self._proc = self._proc, None
        self._replies = None
        if old is None:
            return
        if old.poll() is None:
            try:
                old.terminate()
                old.wait(timeout=1.0)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    old.kill()
                except OSError:
                    pass
        for stream in (old.stdin, old.stdout):
            try:
                if stream is not None:
                    stream.close()
            except OSError:
                pass

    def _request(self, payload: dict):
        proc, replies = self._ensure_process()
        try:
            proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            proc.stdin.flush()
            line = replies.get(timeout=self.RESPONSE_TIMEOUT)
            if line is None:
                raise RuntimeError("persistent_voice_worker_exited")
            response = json.loads(line)
            if not isinstance(response, dict):
                raise RuntimeError("voice_response_invalid")
            return response
        except (Empty, BrokenPipeError, OSError, ValueError):
            self._drop_process()
            raise RuntimeError("persistent_voice_worker_timeout_or_pipe_error") from None

    def _play_if_current(self, generation: int, wav: bytes):
        if sys.platform != "win32":
            raise RuntimeError("Windows自然语音播放不可用于当前系统")
        import winsound
        with tempfile.NamedTemporaryFile(
                prefix="GameTextReader_luna_", suffix=".wav", delete=False) as handle:
            handle.write(wav)
            wav_path = Path(handle.name)
        with self._condition:
            if generation != self._generation or self._closing:
                wav_path.unlink(missing_ok=True)
                return False
            self._stop_audio_locked()
            self._wav_path = wav_path
            # Keep the lock until PlaySound has started. This prevents stop()
            # racing between the stale-generation check and playback.
            winsound.PlaySound(str(wav_path), winsound.SND_FILENAME |
                               winsound.SND_ASYNC | winsound.SND_NODEFAULT)
            return True

    def _run(self):
        try:
            while True:
                with self._condition:
                    while not self._closing and not self._warmup_requested and self._pending is None:
                        self._condition.wait()
                    if self._closing:
                        return
                    pending, self._pending = self._pending, None
                    warmup, self._warmup_requested = self._warmup_requested, False
                    config, voice = self.config_path, self.voice_id
                started = time.perf_counter()
                try:
                    if warmup and pending is None:
                        response = self._request({"command": "prepare",
                                                  "config_path": config, "voice_id": voice})
                        if not response.get("ok"):
                            raise RuntimeError(str(response.get("code", "voice_prepare_failed")))
                        if self.on_event:
                            self.on_event(f"自然语音预热 {int((time.perf_counter()-started)*1000)}ms")
                        continue
                    if pending is None:
                        continue
                    generation, text, rate, requested_at = pending
                    response = self._request({"command": "speak", "config_path": config,
                                               "voice_id": voice, "text": text, "rate": rate})
                    with self._condition:
                        if generation != self._generation or self._closing:
                            continue
                    if not response.get("ok"):
                        raise RuntimeError("stage=" + str(response.get("stage", "unknown")) +
                                           "; code=" + str(response.get("code", "unknown"))[:90])
                    wav = base64.b64decode(response["wav"], validate=True)
                    if (len(wav) > 16 * 1024 * 1024 or
                            wav[:4] != b"RIFF" or wav[8:12] != b"WAVE"):
                        raise ValueError("语音进程没有返回有效 WAV")
                    if self._play_if_current(generation, wav) and self.on_event:
                        self.on_event(f"自然语音请求到播放启动 {int((time.perf_counter()-requested_at)*1000)}ms")
                except Exception as exc:
                    self._drop_process()
                    with self._condition:
                        current = (pending is None or
                                   (pending[0] == self._generation and not self._closing))
                    if current and self.on_error:
                        # No raw config/license is ever sent through diagnostics.
                        self.on_error("微软自然语音：" + (
                            str(exc) if isinstance(exc, RuntimeError)
                            else type(exc).__name__)[:150])
        finally:
            self._drop_process()

    def close(self):
        with self._condition:
            self._closing = True
            self._generation += 1
            self._pending = None
            self._stop_audio_locked()
            self._condition.notify_all()
        # Close asynchronously so choosing another voice does not freeze Tk.
        proc = self._proc
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except OSError:
                pass
