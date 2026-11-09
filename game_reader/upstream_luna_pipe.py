"""Unmodified LunaSubprocess64.exe bridge using LunaTranslator's native IPC contract.

Engine: official LunaTranslator v12.1.3.9 files/LunaSubprocess64.exe.
Original C++ implementation: src/NativeImpl/LunaSubprocess/msnaturalvoice.cpp.
The executable is copied byte-for-byte from the official release. No custom
Microsoft Speech SDK calls in this bridge, and no modification of the engine.

The adapter is NEW code ONLY for connection from GameTextReader. The exact
user-provided config is read at runtime; no voice model or license is bundled.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path
import os
import subprocess
import sys
import uuid

MAP_BYTES = 32 * 1024 * 1024
MAX_SSML_BYTES = 19998
WAIT_MS = 12000
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_MAP_READ = 0x0004
WAIT_OBJECT_0 = 0
PIPE_READMODE_MESSAGE = 0x00000002
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


def original_engine_path() -> Path:
    root = (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False)
            else Path(__file__).resolve().parents[1])
    # CI artifact places the upstream EXE outside PyInstaller's _internal.
    return root / "LunaSubprocess64.exe"


def make_exact_luna_argv(engine, pipe, event, mapping, voice_path,
                         sdk_directory, license_text):
    """LunaSubProcess.py: [exe, 'msnaturalvoice',pipe,event,map,path,dllp,lic]."""
    return [str(engine), "msnaturalvoice", pipe, event, mapping,
            voice_path, sdk_directory, license_text]


def runtime_directory() -> Path:
    from .luna_natural_voice import default_runtime_directories
    for folder in default_runtime_directories():
        if (folder / "Microsoft.CognitiveServices.Speech.extension.embedded.tts.dll").is_file():
            return folder
    raise FileNotFoundError("Windows 自然语音运行组件未找到")


class OriginalLunaPipe:
    """Connect to official Luna executable using original named pipe+shared map.

    Does NOT implement/reimplement embedded speech. The upstream process owns
    all SDK, voice model, synthesizer and WAV creation logic.
    """

    def __init__(self):
        self._process = None
        self._pipe = None
        self._event = None
        self._mapping = None
        self._memory = None
        self._k = None

    def _check(self, value, operation):
        if not value or value == INVALID_HANDLE_VALUE:
            raise OSError(f"官方 Luna 语音进程通信失败：{operation}（Win32={ctypes.get_last_error()}）")
        return value

    def start(self, model_path: str, license_text: str):
        if sys.platform != "win32":
            raise OSError("原作者的 Windows 语音进程只能在 Windows 上运行")
        if self._process is not None:
            raise RuntimeError("原作者语音进程不能重复启动")
        original = original_engine_path()
        if not original.is_file():
            raise FileNotFoundError("未找到原作者未经修改的 LunaSubprocess64.exe")
        dll_dir = runtime_directory()
        self._k = ctypes.WinDLL("kernel32", use_last_error=True)
        k = self._k

        k.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL,
                                   wintypes.LPCWSTR]
        k.CreateEventW.restype = wintypes.HANDLE
        k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k.WaitForSingleObject.restype = wintypes.DWORD
        k.WaitNamedPipeW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD]
        k.WaitNamedPipeW.restype = wintypes.BOOL
        k.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                                  wintypes.HANDLE]
        k.CreateFileW.restype = wintypes.HANDLE
        k.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
        k.OpenFileMappingW.restype = wintypes.HANDLE
        k.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
                                    wintypes.DWORD, ctypes.c_size_t]
        k.MapViewOfFile.restype = ctypes.c_void_p
        k.WriteFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                                ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
        k.WriteFile.restype = wintypes.BOOL
        k.ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                               ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
        k.ReadFile.restype = wintypes.BOOL
        k.SetNamedPipeHandleState.argtypes = [wintypes.HANDLE,
                                              ctypes.POINTER(wintypes.DWORD),
                                              ctypes.c_void_p, ctypes.c_void_p]
        k.SetNamedPipeHandleState.restype = wintypes.BOOL
        k.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
        k.UnmapViewOfFile.restype = wintypes.BOOL
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        k.CloseHandle.restype = wintypes.BOOL

        pipe = "\\\\.\\Pipe\\" + str(uuid.uuid4())
        event_name = str(uuid.uuid4())
        mapping_name = str(uuid.uuid4())
        try:
            # Create event first to avoid a race if original Luna signals early.
            self._event = self._check(k.CreateEventW(None, False, False, event_name),
                                      "CreateEventW")
            args = make_exact_luna_argv(original, pipe, event_name, mapping_name,
                                       model_path, str(dll_dir), license_text)
            self._process = subprocess.Popen(
                args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if k.WaitForSingleObject(self._event, WAIT_MS) != WAIT_OBJECT_0:
                raise TimeoutError("原作者语音进程未发送初始化事件")
            if not k.WaitNamedPipeW(pipe, WAIT_MS):
                raise TimeoutError("原作者语音进程未创建通信管道")
            self._pipe = self._check(
                k.CreateFileW(pipe, GENERIC_READ | GENERIC_WRITE,
                              0, None, OPEN_EXISTING, 0, None),
                "CreateFileW")
            read_mode = wintypes.DWORD(PIPE_READMODE_MESSAGE)
            if not k.SetNamedPipeHandleState(self._pipe,
                                              ctypes.byref(read_mode), None, None):
                raise OSError("设置原作者管道消息模式失败")
            self._mapping = self._check(k.OpenFileMappingW(
                FILE_MAP_READ, False, mapping_name), "OpenFileMappingW")
            self._memory = self._check(k.MapViewOfFile(
                self._mapping, FILE_MAP_READ, 0, 0, MAP_BYTES), "MapViewOfFile")
        except BaseException:
            self.close()
            raise

    def speak_ssml(self, ssml: str) -> bytes:
        if self._pipe is None or self._memory is None:
            raise RuntimeError("原作者语音进程没有准备好")
        if not isinstance(ssml, str):
            raise ValueError("SSML 格式错误")
        payload = ssml.encode("utf-16-le")
        if not payload or len(payload) > MAX_SSML_BYTES:
            raise ValueError("SSML 过长，原作者限定约 10000 个 UTF-16 字符")
        k = self._k
        n = wintypes.DWORD(0)
        buffer = ctypes.create_string_buffer(payload)
        if not k.WriteFile(self._pipe, buffer, len(payload), ctypes.byref(n), None):
            raise OSError("原作者语音子进程写入管道失败")
        if n.value != len(payload):
            raise OSError("原作者语音子进程未收到完整 SSML")
        size = ctypes.c_int32()
        got = wintypes.DWORD(0)
        if not k.ReadFile(self._pipe, ctypes.byref(size), 4,
                          ctypes.byref(got), None) or got.value != 4:
            raise OSError("原作者语音子进程没有返回音频长度")
        if size.value <= 0:
            # Native source uses negative lengths for SDK errors; do not
            # print untrusted SDK details that could contain the license.
            raise RuntimeError("原作者语音引擎没有返回 WAV；请检查语音包和许可")
        if size.value > MAP_BYTES:
            raise ValueError("原作者语音引擎返回的音频超过共享内存容量")
        wav = ctypes.string_at(self._memory, size.value)
        if wav[:4] != b"RIFF" or wav[8:12] != b"WAVE":
            raise ValueError("原作者语音引擎未返回合法的 WAV 文件")
        return wav

    def close(self):
        k = self._k
        if k is not None:
            if self._memory:
                k.UnmapViewOfFile(self._memory)
            self._memory = None
            if self._mapping:
                k.CloseHandle(self._mapping)
            self._mapping = None
            if self._pipe:
                k.CloseHandle(self._pipe)
            self._pipe = None
            if self._event:
                k.CloseHandle(self._event)
            self._event = None
        if self._process is not None:
            if self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._process.kill()
            self._process = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
