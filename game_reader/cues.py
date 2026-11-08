"""Two original audible but gentle Windows cues with explicit playback diagnostics.

This code reports the wave driver accepting data; it cannot prove the user has
an unmuted speaker or the game isn't sending sound to a different device.
"""
from __future__ import annotations

import io
import math
import random
import threading
import wave
from queue import Queue, Full


def make_click_wave(kind: str) -> bytes:
    if kind not in ("complete", "hover"):
        raise ValueError("Unknown cue kind")
    rate = 22050
    # Less than 120ms, but louder than V1.2's easily-missed -20dB cue.
    duration = 0.105 if kind == "complete" else 0.058
    rng = random.Random(1337 if kind == "complete" else 681)
    frames = bytearray()
    frequency = 1050 if kind == "complete" else 830
    decay = 29 if kind == "complete" else 61
    amplitude = 0.21 if kind == "complete" else 0.15
    for i in range(round(rate * duration)):
        t = i / rate
        resonant = math.sin(2 * math.pi * frequency * t) + (
            0.24 * math.sin(2 * math.pi * 2210 * t))
        transient = (rng.random() * 2 - 1) * math.exp(-t * 90)
        envelope = min(1.0, t * 400) * math.exp(-t * decay)
        val = max(-1.0, min(1.0, amplitude * (resonant * envelope + transient)))
        frames.extend(round(val * 32767).to_bytes(2, "little", signed=True))
    result = io.BytesIO()
    with wave.open(result, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(frames)
    return result.getvalue()


class CuePlayer:
    def __init__(self, on_error=None, on_event=None):
        self._queue = Queue(maxsize=4)
        self._audio = {kind: make_click_wave(kind) for kind in ("complete", "hover")}
        self._error = on_error
        self._event = on_event
        self._thread = threading.Thread(target=self._run, daemon=True, name="GameTextCues")
        self._thread.start()

    def _notify(self, message: str):
        if self._event:
            self._event(message)

    def _run(self):
        try:
            import winsound
        except Exception as exc:
            if self._error:
                self._error(f"无法加载 Windows 提示音组件: {exc}")
            return
        while True:
            kind = self._queue.get()
            if kind is None:
                return
            try:
                winsound.PlaySound(self._audio[kind],
                                   winsound.SND_MEMORY | winsound.SND_SYNC |
                                   winsound.SND_NODEFAULT)
                self._notify(f"{kind}: 音频播放接口已返回（不代表扬声器一定出声）")
            except Exception as exc:
                if self._error:
                    self._error(f"{kind} 播放失败: {type(exc).__name__}: {exc}")

    def play(self, kind: str):
        if kind not in self._audio:
            return
        try:
            self._queue.put_nowait(kind)
        except Full:
            self._notify(f"{kind}: 提示音队列已满，已丢弃")

    def shutdown(self):
        try:
            self._queue.put_nowait(None)
        except Full:
            pass
