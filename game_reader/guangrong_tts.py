"""Optional adapter for an independently installed official Guangrong x64 DLL.

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
from .guangrong_setup import installed_x64_dll
import sys
import tempfile
import threading
import time
import wave


MAX_AUDIO_BYTES = 32 * 1024 * 1024


def chosen_dll_path(value: str) -> Path | None:
    """Load a 64-bit engine, never the older 32-bit grtts.dll.

    Accept a manually provided path only as an expert fallback. The primary
    path is our independently installed original publisher distribution.
    """
    if not value or not isinstance(value, str):
        return None
    p = Path(value).expanduser()
    if p.is_dir() or p.name.lower() not in ("grtts.dll", "grtts_x64.dll"):
        p = p / "grtts_x64.dll"
    elif p.name.lower() == "grtts.dll":
        p = p.with_name("grtts_x64.dll")
    try:
        if p.is_file() and p.name.lower() == "grtts_x64.dll":
            return p.resolve()
    except OSError:
        pass
    return None


def find_known_installed_guangrong() -> str:
    """Prefer our own local runtime; otherwise try a user's existing NVDA DLL."""
    local = installed_x64_dll()
    if local:
        return str(local)
    roaming = os.environ.get("APPDATA")
    if not roaming:
        return ""
    base = Path(roaming) / "nvda" / "addons"
    if not base.is_dir():
        return ""
    try:
        for folder in sorted(base.iterdir()):
            if not folder.is_dir():
                continue
            candidate = folder / "synthDrivers" / "grtts_x64.dll"
            if candidate.is_file():
                return str(candidate)
    except OSError:
        pass
    return ""


def _native_trace(stage):
    path = os.environ.get("GR_NATIVE_DEBUG_FILE")
    if path:
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(stage + "\\n")
        except OSError:
            pass


def load_guangrong_native(file: Path):
    """Load the isolated x64 vendor DLL via Windows' native loader.

    Avoid PyInstaller's ctypes library hook; frozen apps preload their own
    _internal DLL search directory, which can shadow external codec libraries.
    Only the dedicated vendor subprocess has its DLL search path reset.
    """
    _native_trace("native-enter")
    if sys.platform != "win32":
        raise RuntimeError("广荣独立 DLL 仅支持 Windows")
    if not file.is_file() or file.name.lower() != "grtts_x64.dll":
        raise FileNotFoundError("缺少官方广荣 x64 原始运行库")
    _native_trace("before-kernel-win-dll")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    _native_trace("after-kernel-win-dll")
    kernel.SetDllDirectoryW.argtypes = [ctypes.c_wchar_p]
    kernel.SetDllDirectoryW.restype = ctypes.c_bool
    _native_trace("before-reset-search")
    kernel.SetDllDirectoryW(None)  # restore ordinary Windows search in child
    _native_trace("after-reset-search")
    kernel.LoadLibraryExW.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_uint]
    kernel.LoadLibraryExW.restype = ctypes.c_void_p
    # LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS;
    # vendor dependencies are searched in the vendor's own directory first.
    _native_trace("before-load-library-ex")
    handle = kernel.LoadLibraryExW(str(file), None, 0x00000100 | 0x00001000)
    _native_trace("after-load-library-ex")
    if not handle:
        error = ctypes.get_last_error()
        reasons = {
            1114: "广荣官方 x64 DLL 初始化例程失败，可能不支持脱离原宿主软件运行",
            126: "广荣官方 DLL 的依赖文件不完整",
            193: "广荣 DLL 与进程位数或某个依赖 DLL 的位数不一致",
        }
        desc = reasons.get(error, "Windows 原生加载器未能加载广荣语音引擎")
        raise RuntimeError(f"{desc} [WinError {error}]")
    try:
        # Use the already-open native handle rather than PyInstaller's patched
        # ctypes.CDLL(path) behavior. The caller keeps this object alive.
        return ctypes.CDLL(str(file), handle=handle)
    except BaseException:
        kernel.FreeLibrary.argtypes = [ctypes.c_void_p]
        kernel.FreeLibrary(handle)
        raise


def _guangrong_worker(pipe, path: str):
    """All native vendor calls stay outside the application's process."""
    def trace_child(stage):
        # Opt-in CI diagnostics only. No text/voice content logged.
        out = os.environ.get("GR_NATIVE_DEBUG_FILE")
        if out:
            try:
                with open(out, "a", encoding="utf-8") as stream:
                    stream.write(stage + "\\n")
            except OSError:
                pass
    trace_child("worker-enter")
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
        trace_child("validating-path")
        file = chosen_dll_path(path)
        if file is None:
            emit("error", "未找到广荣 64 位 grtts_x64.dll。请点击“一键安装独立广荣”。")
            return
        if sys.platform != "win32":
            emit("error", "广荣 Windows DLL 只能在 Windows 上调用。")
            return

        trace_child("before-add-dll-dir")
        directory_handle = os.add_dll_directory(str(file.parent))
        original_dir = os.getcwd()
        # The upstream NVDA DLL may look for .vl / NaturalVoiceS near itself.
        os.chdir(str(file.parent))
        trace_child("before-native-load")
        dll = load_guangrong_native(file)
        trace_child("after-native-load")
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
        # The upstream Guangrong NVDA driver supports BOTH synchronous PCM
        # and the streaming synth interface. NaturalVoice may need streaming.
        streaming = all(hasattr(dll, name) for name in (
            "YongDe_StartStreamSynth", "YongDe_GetStreamChunk",
            "YongDe_FreeStreamChunk", "YongDe_IsStreamComplete",
            "YongDe_StopStreamSynth"))
        if streaming:
            api = [
                ("YongDe_StartStreamSynth", ctypes.c_bool, [ctypes.c_wchar_p]),
                ("YongDe_GetStreamChunk", ctypes.c_bool,
                 [ctypes.POINTER(ctypes.c_void_p),
                  ctypes.POINTER(ctypes.c_int)]),
                ("YongDe_FreeStreamChunk", None, [ctypes.c_void_p]),
                ("YongDe_IsStreamComplete", ctypes.c_bool, []),
                ("YongDe_StopStreamSynth", None, []),
            ]
            if hasattr(dll, "YongDe_GetStreamChunkEx"):
                api.append(("YongDe_GetStreamChunkEx", ctypes.c_bool,
                            [ctypes.POINTER(ctypes.c_void_p),
                             ctypes.POINTER(ctypes.c_int),
                             ctypes.POINTER(ctypes.c_int),
                             ctypes.POINTER(ctypes.c_int),
                             ctypes.POINTER(ctypes.c_int)]))
            for name, ret, args in api:
                method = getattr(dll, name)
                method.restype = ret
                method.argtypes = args
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

        def synthesize_stream(request_id: int, text: str):
            """Fallback to official Guangrong streaming functions, buffer PCM.

            Streams of different formats are never blindly concatenated.
            This intentionally does not duplicate NVDA's nvwave dependency.
            """
            if not streaming or not dll.YongDe_StartStreamSynth(text):
                return None
            frames = bytearray()
            fmt = None
            deadline = time.monotonic() + 20.0
            try:
                while time.monotonic() < deadline:
                    with generation_lock:
                        if request_id != generation[0]:
                            return None
                    if dll.YongDe_IsStreamComplete():
                        break
                    ptr = ctypes.c_void_p()
                    length = ctypes.c_int()
                    sr, bits, channels = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
                    if hasattr(dll, "YongDe_GetStreamChunkEx"):
                        got = dll.YongDe_GetStreamChunkEx(
                            ctypes.byref(ptr), ctypes.byref(length),
                            ctypes.byref(sr), ctypes.byref(bits),
                            ctypes.byref(channels))
                        if got:
                            incoming = (sr.value, bits.value, channels.value)
                            if fmt is None:
                                fmt = incoming
                            if fmt != incoming:
                                raise ValueError("广荣输出音频格式在一句话中发生变化")
                    else:
                        got = dll.YongDe_GetStreamChunk(
                            ctypes.byref(ptr), ctypes.byref(length))
                    if got and ptr.value and length.value > 0:
                        try:
                            if length.value > MAX_AUDIO_BYTES - len(frames):
                                raise ValueError("广荣输出音频长度超过上限")
                            frames.extend(ctypes.string_at(ptr.value, length.value))
                        finally:
                            dll.YongDe_FreeStreamChunk(ptr)
                    else:
                        time.sleep(0.006)
                if not frames:
                    return None
                if fmt is None:
                    sr, bits, channels = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
                    dll.YongDe_GetAudioFormat(ctypes.byref(sr),
                                              ctypes.byref(bits),
                                              ctypes.byref(channels))
                    fmt = (sr.value, bits.value, channels.value)
                return bytes(frames), fmt
            finally:
                try:
                    dll.YongDe_StopStreamSynth()
                except Exception:
                    pass

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
                    if ok and pointer.value and 0 < size.value <= MAX_AUDIO_BYTES:
                        pcm = ctypes.string_at(pointer.value, size.value)
                        sr, bits, channels = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
                        dll.YongDe_GetAudioFormat(ctypes.byref(sr),
                                                  ctypes.byref(bits),
                                                  ctypes.byref(channels))
                    else:
                        # Some installed Microsoft NeuralVoices are exposed
                        # only via the streaming path in the vendor DLL.
                        fallback = synthesize_stream(request_id, text)
                        if fallback is None:
                            emit("error", "广荣同步和流式合成均无有效音频。"
                                          "请核对原安装音库和 grtts.dll。")
                            return
                        pcm, fmt = fallback
                        sr, bits, channels = (ctypes.c_int(fmt[0]),
                                              ctypes.c_int(fmt[1]),
                                              ctypes.c_int(fmt[2]))
                    elapsed = int((time.perf_counter() - start) * 1000)
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
        trace_child("caught-" + type(exc).__name__)
        emit("error", "广荣独立引擎：加载或运行错误：" + type(exc).__name__ + ": " + str(exc)[:260])
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
        return [], "尚未安装广荣 64 位语音引擎"
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
            raise FileNotFoundError("找不到广荣 64 位引擎，请先一键安装官方组件")
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
