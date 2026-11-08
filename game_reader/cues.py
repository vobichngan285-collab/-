"""Audible original notification cues via the Windows file playback path.

V1.2/V1.3 used extremely short, quiet memory-only WAV playback. V1.4 caches
real WAV files in LOCALAPPDATA and requests asynchronous default-device
playback with error/diagnostic callbacks. All playback remains off the Tk UI.
"""
from __future__ import annotations
import io
import math
import os
from pathlib import Path
import random
import threading
import wave
from queue import Queue, Full

def make_click_wave(kind: str) -> bytes:
    if kind not in ("complete", "hover"):
        raise ValueError("Unknown cue")
    sr = 24000
    dur = 0.125 if kind == "complete" else 0.085
    main = 1220 if kind == "complete" else 950
    amplitude = .34 if kind == "complete" else .23
    decay = 25 if kind == "complete" else 54
    rng = random.Random(17 if kind == "complete" else 32)
    samples = bytearray()
    for i in range(round(sr * dur)):
        t = i / sr
        initial = .22 * (rng.random() * 2 - 1) * math.exp(-t * 100)
        ring = (math.sin(2 * math.pi * main * t) +
                .25 * math.sin(2 * math.pi * main * 2.33 * t))
        envelope = min(1.0, t * 460) * math.exp(-t * decay)
        v = max(-.98, min(.98, amplitude * (ring * envelope + initial)))
        samples += int(v * 32767).to_bytes(2, "little", signed=True)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(sr)
        out.writeframes(samples)
    return buf.getvalue()


def cue_directory() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "GameTextReader" / "cues"


class CuePlayer:
    def __init__(self, on_error=None, on_event=None):
        self._on_error = on_error
        self._on_event = on_event
        self._queue = Queue(maxsize=8)
        self._paths = {}
        try:
            directory = cue_directory()
            directory.mkdir(parents=True, exist_ok=True)
            for kind in ("complete", "hover"):
                data = make_click_wave(kind)
                path = directory / (kind + "_v14.wav")
                if not path.exists() or path.stat().st_size != len(data):
                    path.write_bytes(data)
                self._paths[kind] = path
        except OSError as exc:
            if self._on_error:
                self._on_error("不能创建提示音 WAV 文件：" + str(exc))
        self._thread = threading.Thread(target=self._run,
                                        name="WindowsUICues", daemon=True)
        self._thread.start()

    def _run(self):
        try:
            import winsound
        except ImportError as exc:
            if self._on_error:
                self._on_error("Windows winsound 不可用：" + str(exc))
            return
        while True:
            kind = self._queue.get()
            if kind is None:
                return
            try:
                if kind == "system_test":
                    # System event is independent of our generated click, helpful
                    # for distinguishing output routing / muted notification sound.
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                elif kind in self._paths:
                    path = self._paths[kind]
                    # File + async avoids the old SND_MEMORY restrictions.
                    winsound.PlaySound(str(path),
                                       winsound.SND_FILENAME | winsound.SND_ASYNC |
                                       winsound.SND_NODEFAULT)
                else:
                    raise RuntimeError("提示音文件不可用")
                if self._on_event:
                    self._on_event(f"{kind}: Windows 音频接口接受播放请求；"
                                   "实际听到声音仍取决于电脑音频输出和音量")
            except Exception as exc:
                if self._on_error:
                    self._on_error(f"{kind} 提示音失败: {type(exc).__name__}: {exc}")

    def play(self, kind: str):
        if kind not in ("complete", "hover", "system_test"):
            return
        try:
            self._queue.put_nowait(kind)
        except Full:
            if self._on_event:
                self._on_event("提示音队列满，已丢弃一次触发")

    def shutdown(self):
        try:
            self._queue.put_nowait(None)
        except Full:
            pass
