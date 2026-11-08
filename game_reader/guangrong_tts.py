"""Optional adapter for a user's OWN installed Guangrong TTS DLL.

The game reader does not bundle grtts.dll, NaturalVoice models or licenses.
The vendor DLL is isolated in a spawn child process, so a failed or
incompatible DLL cannot crash the OCR/UI process. We use the DLL's documented
names found in its public NVDA Python driver, not private Windows speech keys.

This integration is experimental until verified with the user's licensed DLL.
"""
from __future__ import annotations

import ctypes
import multiprocessing as mp
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import wave


MAX_AUDIO_BYTES = 32 * 1024 * 1024


def chosen_dll_path(value: str) -> Path | None:
    """Only an explicitly selected grtts.dll, or its immediate directory."""
    if not value or not isinstance(value, str):
        return None
    p = Path(value).expanduser()
    if p.name.lower() != "grtts.dll":
        p = p / "grtts.dll"
    try:
        if p.is_file() and p.name.lower() == "grtts.dll":
            return p.resolve()
    except OSError:
        pass
    return None


def _guangrong_worker(pipe, path: str):
    """All native vendor calls stay outside the application's process."""
    dll = None
    directory_handle = None
    original_dir = None
    synthesizing = threading.Lock()
    generation = [0]
    generation_lock = threading.Lock()
    send_lock = threading.Lock()

    def emit(*message):
        with send_lock:
            try:
                pipe.send(message)
            except (EOFError, OSError, BrokenPipeError):
                pass

    try:
        file = chosen_dll_path(path)
        if file is None:
            emit("error", "未找到 grtts.dll。请在已安装广荣的目录里选择原文件。")
            return
        if sys.platform != "win32":
            emit("error", "广荣 Windows DLL 只能在 Windows 上调用。")
            return

        directory_handle = os.add_dll_directory(str(file.parent))
        original_dir = os.getcwd()
        # The upstream NVDA DLL may look for .vl / NaturalVoiceS near itself.
        os.chdir(str(file.parent))
        dll = ctypes.CDLL(str(file))
        prototype = [
            ("YongDe_Initialize", ctypes.c_bool, []),
            ("YongDe_Uninitialize", None, []),
            ("YongDe_GetVoiceCount", ctypes.c_int, []),
            ("YongDe_GetVoiceName", ctypes.c_int,
             [ctypes.c_int, ctypes.c_wchar_p, ctypes.c_int]),
            ("YongDe_SetVoice", ctypes.c_bool, [ctypes.c_int]),
            ("YongDe_GetAudioFormat", None,
             [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
              ctypes.POINTER(ctypes.c_int)]),
            ("YongDe_TextToAudio", ctypes.c_bool,
             [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_void_p),
              ctypes.POINTER(ctypes.c_int)]),
            ("YongDe_FreeAudio", None, [ctypes.c_void_p]),
            ("YongDe_SetRate", None, [ctypes.c_int]),
            ("YongDe_SetVolume", None, [ctypes.c_int]),
        ]
        for name, ret, args in prototype:
            function = getattr(dll, name)
            function.restype = ret
            function.argtypes = args
        if not dll.YongDe_Initialize():
            emit("error", "广荣 DLL 初始化失败；可能缺少语音模型或依赖文件。")
            return
        names = []
        n = max(0, min(256, dll.YongDe_GetVoiceCount()))
        for idx in range(n):
            buf = ctypes.create_unicode_buffer(256)
            dll.YongDe_GetVoiceName(idx, buf, 256)
            names.append(buf.value or f"广荣声音 {idx}")
        emit("ready", names)
        if not names:
            emit("error", "广荣 DLL 已加载，但没有可用的声音。请检查原安装目录音库文件。")

        def synthesize(request_id: int, text: str):
            with synthesizing:
                with generation_lock:
                    if request_id != generation[0]:
                        return
                pointer = ctypes.c_void_p()
                size = ctypes.c_int(0)
                try:
                    start = time.perf_counter()
                    ok = dll.YongDe_TextToAudio(text, ctypes.byref(pointer),
                                                ctypes.byref(size))
                    elapsed = int((time.perf_counter() - start) * 1000)
                    if not ok or not pointer.value or not 0 < size.value <= MAX_AUDIO_BYTES:
                        emit("error", "广荣合成没有产生有效 PCM。此 DLL/音库可能不兼容独立调用。")
                        return
                    pcm = ctypes.string_at(pointer.value, size.value)
                    sr, bits, channels = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
                    dll.YongDe_GetAudioFormat(ctypes.byref(sr),
                                              ctypes.byref(bits), ctypes.byref(channels))
                    with generation_lock:
                        if request_id != generation[0]:
                            return
                    if sr.value not in (8000, 11025, 16000, 22050, 24000,
                                        32000, 44100, 48000, 96000):
                        raise ValueError("广荣返回无效采样率：" + str(sr.value))
                    if bits.value not in (8, 16, 24, 32) or channels.value not in (1, 2):
                        raise ValueError("广荣返回不支持的 PCM 格式")
                    emit("audio", request_id, pcm, sr.value, bits.value,
                         channels.value, elapsed)
                except Exception as exc:
                    emit("error", "广荣合成异常：" + type(exc).__name__ + ": " + str(exc)[:200])
                finally:
                    if pointer.value:
                        try:
                            dll.YongDe_FreeAudio(pointer)
                        except Exception:
                            pass

        while True:
            if not pipe.poll(0.08):
                continue
            try:
                item = pipe.recv()
            except (EOFError, OSError):
                break
            cmd = item[0]
            if cmd == "exit":
                break
            if cmd == "stop":
                with generation_lock:
                    generation[0] = max(generation[0], int(item[1]))
            elif cmd == "voice":
                with synthesizing:
                    if not dll.YongDe_SetVoice(int(item[1])):
                        emit("error", "广荣未能切换到指定语音编号。")
                    else:
                        emit("event", "广荣声音选择已传入底层引擎")
            elif cmd == "rate":
                dll.YongDe_SetRate(max(0, min(100, int(item[1]))))
            elif cmd == "volume":
                dll.YongDe_SetVolume(max(0, min(100, int(item[1]))))
            elif cmd == "speak":
                rid, content = int(item[1]), str(item[2])
                with generation_lock:
                    generation[0] = max(generation[0], rid)
                threading.Thread(target=synthesize, args=(rid, content),
                                 daemon=True, name="GuangrongNativeSynth").start()
    except BaseException as exc:
        emit("error", "广荣 DLL 运行环境错误：" + type(exc).__name__ + ": " + str(exc)[:220])
    finally:
        if dll is not None:
            try:
                # Native synth threads are daemon threads; the child may exit
                # without deinitializing a DLL while a native call is active.
                if not synthesizing.locked():
                    dll.YongDe_Uninitialize()
            except Exception:
                pass
        if directory_handle:
            try:
                directory_handle.close()
            except Exception:
                pass
        if original_dir:
            try:
                os.chdir(original_dir)
            except Exception:
                pass
        try:
            pipe.close()
        except Exception:
            pass


def list_guangrong_voices(path: str, timeout: float = 8.0):
    """Probe only a user-selected local DLL, in a disposable child process."""
    if chosen_dll_path(path) is None:
        return [], "尚未选择现有广荣 grtts.dll"
    if sys.platform != "win32":
        return [], "仅支持 Windows"
    parent, child = mp.Pipe(duplex=True)
    process = mp.Process(target=_guangrong_worker, args=(child, path),
                         daemon=True, name="GuangrongTTSProbe")
    try:
        process.start()
        child.close()
        if parent.poll(timeout):
            item = parent.recv()
            if item[0] == "ready":
                return list(item[1]), ""
            return [], str(item[1]) if len(item) > 1 else "广荣初始化失败"
        return [], "广荣 DLL 探测超时；没有影响其他语音引擎"
    except (EOFError, OSError, RuntimeError) as exc:
        return [], "广荣探测失败：" + str(exc)[:180]
    finally:
        try:
            if process.is_alive():
                process.terminate()
            process.join(timeout=1)
        except Exception:
            pass
        parent.close()


class GuangrongBridge:
    """Async native synth -> PCM -> per-request WAV -> default Windows endpoint."""
    def __init__(self, dll_path: str, on_error=None, on_event=None):
        if chosen_dll_path(dll_path) is None:
            raise FileNotFoundError("找不到用户选择的 grtts.dll")
        self.on_error, self.on_event = on_error, on_event
        self._generation = 0
        self._write_lock = threading.Lock()
        self._closed = False
        self._temp = tempfile.TemporaryDirectory(prefix="game-grtts-")
        self.pipe, child = mp.Pipe(duplex=True)
        self.proc = mp.Process(target=_guangrong_worker,
                               args=(child, dll_path),
                               daemon=True, name="GuangrongTTSEngine")
        self.proc.start()
        child.close()
        self._listener = threading.Thread(target=self._listen,
                                          daemon=True, name="GuangrongAudioListener")
        self._listener.start()

    def _send(self, *msg):
        with self._write_lock:
            if self._closed:
                return
            try:
                self.pipe.send(msg)
            except (OSError, EOFError, BrokenPipeError) as exc:
                if self.on_error:
                    self.on_error("广荣进程通讯中断：" + str(exc))

    def _listen(self):
        while not self._closed:
            try:
                if not self.pipe.poll(0.1):
                    if not self.proc.is_alive():
                        if self.on_error:
                            self.on_error("广荣语音进程意外退出")
                        break
                    continue
                msg = self.pipe.recv()
            except (OSError, EOFError):
                break
            kind = msg[0]
            if kind == "error":
                if self.on_error:
                    self.on_error(str(msg[1]))
            elif kind == "ready":
                if self.on_event:
                    self.on_event(f"广荣 DLL 运行成功，语音数量 {len(msg[1])}")
            elif kind == "event":
                if self.on_event:
                    self.on_event(str(msg[1]))
            elif kind == "audio":
                _, seq, pcm, sr, bits, channels, synth_ms = msg
                if seq == self._generation:
                    self._play_pcm(seq, pcm, sr, bits, channels, synth_ms)

    def _play_pcm(self, seq, data, sample_rate, bits, channels, synth_ms):
        try:
            import winsound
            from pathlib import Path
            file = Path(self._temp.name) / f"speech-{seq}.wav"
            with wave.open(str(file), "wb") as wav:
                wav.setnchannels(channels)
                wav.setsampwidth(bits // 8)
                wav.setframerate(sample_rate)
                wav.writeframes(data)
            if seq != self._generation:
                return
            winsound.PlaySound(None, 0)
            winsound.PlaySound(str(file),
                               winsound.SND_FILENAME | winsound.SND_ASYNC |
                               winsound.SND_NODEFAULT)
            if self.on_event:
                self.on_event(f"广荣生成 {len(data)} 字节 PCM，用时 {synth_ms}ms；"
                              "已向默认音频设备提交播放，尚需实际听音确认")
            # Limit leftover temp files; do not delete the active file.
            older = sorted(Path(self._temp.name).glob("speech-*.wav"))
            for prior in older[:-5]:
                try:
                    prior.unlink()
                except OSError:
                    pass
        except Exception as exc:
            if self.on_error:
                self.on_error("广荣 PCM 播放失败：" + type(exc).__name__ + ": " + str(exc))

    def select(self, voice_index: int):
        self.stop()
        self._send("voice", int(voice_index))

    def speak(self, text: str):
        self.stop()
        self._generation += 1
        self._send("speak", self._generation, text)

    def stop(self):
        self._generation += 1
        self._send("stop", self._generation)
        try:
            import winsound
            winsound.PlaySound(None, 0)
        except (OSError, RuntimeError):
            pass

    def set_rate(self, value: int):
        self._send("rate", max(0, min(100, 50 + int(value) * 5)))

    def set_volume(self, value: int):
        self._send("volume", max(0, min(100, int(value))))

    def close(self):
        self.stop()
        self._send("exit")
        self._closed = True
        try:
            if self.proc.is_alive():
                self.proc.join(timeout=0.4)
            if self.proc.is_alive():
                self.proc.terminate()
                self.proc.join(timeout=0.4)
        except Exception:
            pass
        self.pipe.close()
        try:
            self._temp.cleanup()
        except OSError:
            pass
