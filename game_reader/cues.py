"""Windows original notification cues with independent waveOut audio playback.

V1.2/V1.3 used extremely short, quiet memory-only WAV playback. V1.4 caches
real WAV files in LOCALAPPDATA and requests asynchronous default-device
playback with error/diagnostic callbacks. All playback remains off the Tk UI.
"""
from __future__ import annotations
import io
import ctypes
import time
import math
import os
from pathlib import Path
import random
import threading
import wave
from queue import Queue, Full

def make_click_wave(kind: str) -> bytes:
    """Original bright 'ding' for F8 completion; old hover is legacy/test only."""
    if kind not in ("complete", "hover"):
        raise ValueError("Unknown cue")
    rate = 24000
    duration = .235 if kind == "complete" else .085
    sound = bytearray()
    for i in range(int(rate * duration)):
        t = i / rate
        if kind == "complete":
            # A single bright bell with a fast, smooth attack and soft decay.
            attack = min(1.0, t * 800)
            envelope = attack * math.exp(-16.5 * t)
            partials = (
                math.sin(2 * math.pi * 1568 * t)
                + .25 * math.sin(2 * math.pi * 2376 * t)
                + .09 * math.sin(2 * math.pi * 3220 * t)
            )
            value = .34 * partials * envelope
        else:
            # Kept to avoid breaking old tests; never triggered on hover in V1.5.
            value = .18 * math.sin(2 * math.pi * 950 * t) * math.exp(-55 * t)
        clipped = max(-.95, min(.95, value))
        sound += int(clipped * 32767).to_bytes(2, "little", signed=True)
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(sound)
    return output.getvalue()

def cue_directory() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "GameTextReader" / "cues"



def _play_independent_wave(wav_bytes: bytes):
    """Play on a separate waveOut handle; TTS cannot cancel this short sound."""
    class WAVEFORMATEX(ctypes.Structure):
        _fields_ = [
            ("wFormatTag", ctypes.c_ushort),
            ("nChannels", ctypes.c_ushort),
            ("nSamplesPerSec", ctypes.c_uint32),
            ("nAvgBytesPerSec", ctypes.c_uint32),
            ("nBlockAlign", ctypes.c_ushort),
            ("wBitsPerSample", ctypes.c_ushort),
            ("cbSize", ctypes.c_ushort),
        ]

    class WAVEHDR(ctypes.Structure):
        _fields_ = [
            ("lpData", ctypes.c_void_p),
            ("dwBufferLength", ctypes.c_uint32),
            ("dwBytesRecorded", ctypes.c_uint32),
            ("dwUser", ctypes.c_size_t),
            ("dwFlags", ctypes.c_uint32),
            ("dwLoops", ctypes.c_uint32),
            ("lpNext", ctypes.c_void_p),
            ("reserved", ctypes.c_size_t),
        ]

    with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
            raise ValueError("Cue format must be mono 16-bit PCM")
        rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())
    mm = ctypes.WinDLL("winmm", use_last_error=True)
    mm.waveOutOpen.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint,
                               ctypes.POINTER(WAVEFORMATEX),
                               ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
    mm.waveOutOpen.restype = ctypes.c_uint
    for fn in ("waveOutPrepareHeader", "waveOutWrite", "waveOutUnprepareHeader"):
        method = getattr(mm, fn)
        method.argtypes = [ctypes.c_void_p, ctypes.POINTER(WAVEHDR), ctypes.c_uint]
        method.restype = ctypes.c_uint
    mm.waveOutReset.argtypes = [ctypes.c_void_p]
    mm.waveOutClose.argtypes = [ctypes.c_void_p]

    fmt = WAVEFORMATEX(1, 1, rate, rate * 2, 2, 16, 0)
    handle = ctypes.c_void_p()
    code = mm.waveOutOpen(ctypes.byref(handle), 0xFFFFFFFF, ctypes.byref(fmt),
                          None, None, 0)
    if code:
        raise OSError(f"waveOutOpen 返回 {code}")
    prepared = False
    try:
        buffer = ctypes.create_string_buffer(frames)
        header = WAVEHDR()
        header.lpData = ctypes.cast(buffer, ctypes.c_void_p)
        header.dwBufferLength = len(frames)
        header.dwLoops = 1
        if mm.waveOutPrepareHeader(handle, ctypes.byref(header),
                                   ctypes.sizeof(header)):
            raise OSError("waveOutPrepareHeader 失败")
        prepared = True
        if mm.waveOutWrite(handle, ctypes.byref(header),
                           ctypes.sizeof(header)):
            raise OSError("waveOutWrite 失败")
        deadline = time.monotonic() + 0.6
        while not (header.dwFlags & 0x00000001) and time.monotonic() < deadline:
            time.sleep(0.006)
    finally:
        mm.waveOutReset(handle)
        if prepared:
            mm.waveOutUnprepareHeader(handle, ctypes.byref(header),
                                      ctypes.sizeof(header))
        mm.waveOutClose(handle)

class CuePlayer:
    def __init__(self, on_error=None, on_event=None):
        self._on_error = on_error
        self._on_event = on_event
        self._queue = Queue(maxsize=8)
        self._paths = {}
        self._audio = {}
        try:
            directory = cue_directory()
            directory.mkdir(parents=True, exist_ok=True)
            for kind in ("complete", "hover"):
                data = make_click_wave(kind)
                path = directory / (kind + "_v15.wav")
                if not path.exists() or path.stat().st_size != len(data):
                    path.write_bytes(data)
                self._paths[kind] = path
                self._audio[kind] = data
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
                    try:
                        _play_independent_wave(self._audio[kind])
                    except Exception as error:
                        # On drivers without waveOut, use standard async WAV.
                        path = self._paths[kind]
                        winsound.PlaySound(str(path),
                                           winsound.SND_FILENAME | winsound.SND_ASYNC |
                                           winsound.SND_NODEFAULT)
                        if self._on_event:
                            self._on_event(f"{kind}: waveOut 不可用，转用 winsound；原因：{error}")
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
