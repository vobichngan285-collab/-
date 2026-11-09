"""Two short, original low-volume UI cues. No downloaded audio assets."""
from __future__ import annotations

import io
import math
import random
import threading
import wave
from queue import Empty, Queue


def make_click_wave(kind: str) -> bytes:
    """Create a small original PCM wave, not a prerecorded commercial sound."""
    if kind not in ("complete", "hover"):
        raise ValueError("Unknown cue kind")
    rate = 22050
    duration = 0.145 if kind == "complete" else 0.038
    rng = random.Random(1337 if kind == "complete" else 681)
    frames = bytearray()
    for i in range(int(rate * duration)):
        t = i / rate
        # Brief mechanical transient with a small resonant ring.
        metallic = (math.sin(2 * math.pi * (1240 if kind == "complete" else 980) * t)
                    + 0.35 * math.sin(2 * math.pi * 2790 * t))
        noise = (rng.random() * 2 - 1) * math.exp(-t * 110)
        decay = math.exp(-t * (25 if kind == "complete" else 97))
        amplitude = 0.17 if kind == "complete" else 0.065
        signal = max(-1.0, min(1.0, amplitude * (metallic * decay + noise)))
        frames.extend(int(signal * 32767).to_bytes(2, "little", signed=True))
    stream = io.BytesIO()
    with wave.open(stream, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(frames)
    return stream.getvalue()


class CuePlayer:
    def __init__(self, on_error=None):
        self._q = Queue(maxsize=8)
        self._audio = {kind: make_click_wave(kind) for kind in ("complete", "hover")}
        self._error = on_error
        self._thread = threading.Thread(target=self._run, daemon=True, name="Cues")
        self._thread.start()

    def _run(self):
        try:
            import winsound
        except ImportError:
            return
        while True:
            kind = self._q.get()
            if kind is None:
                return
            try:
                winsound.PlaySound(self._audio[kind],
                                   winsound.SND_MEMORY | winsound.SND_SYNC |
                                   winsound.SND_NODEFAULT)
            except Exception as ex:
                if self._error:
                    self._error(str(ex))

    def play(self, kind: str):
        if kind not in self._audio:
            return
        try:
            self._q.put_nowait(kind)
        except Exception:
            # Cues are disposable. Never block mouse or TTS.
            pass

    def shutdown(self):
        try:
            self._q.put_nowait(None)
        except Exception:
            pass
