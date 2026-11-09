"""Standalone Guangrong TTS bridge to an independent native Windows helper.

Unlike V1.4/V1.5, the publisher's grtts_x64.dll is NEVER loaded by the
PyInstaller-frozen Python process or multiprocessing fork child. The original
vendor DLL stays in the dedicated local app runtime; our own small x64 helper
uses the Windows loader and writes synthesized PCM over a local anonymous
pipe. No BaoYi or NVDA API is called. No cloud speech is used.

The publisher may still reject independent use (WinError 1114); that error is
reported accurately instead of claiming the voice works.
"""
from __future__ import annotations

import base64
import ctypes
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import wave

from .guangrong_setup import installed_x64_dll

MAX_AUDIO_BYTES = 32 * 1024 * 1024
CREATE_NO_WINDOW = 0x08000000


def chosen_dll_path(value: str) -> Path | None:
    if not value or not isinstance(value, str):
        return None
    file = Path(value).expanduser()
    if file.is_dir() or file.name.lower() not in ("grtts.dll", "grtts_x64.dll"):
        file = file / "grtts_x64.dll"
    elif file.name.lower() == "grtts.dll":
        file = file.with_name("grtts_x64.dll")
    try:
        if file.name.lower() == "grtts_x64.dll" and file.is_file():
            return file.resolve()
    except OSError:
        pass
    return None


def find_known_installed_guangrong() -> str:
    """Only discover engine installed for THIS application, not another reader."""
    file = installed_x64_dll()
    return str(file) if file else ""


def guangrong_host_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().with_name("GuangrongHost.exe")
    return Path(__file__).resolve().parents[1] / "native" / "GuangrongHost.exe"


def _popen_host(dll_path: str):
    file = chosen_dll_path(dll_path)
    if file is None:
        raise FileNotFoundError("独立广荣组件未安装完整；缺少 grtts_x64.dll")
    helper = guangrong_host_path()
    if not helper.is_file():
        raise FileNotFoundError("新版独立语音辅助程序 GuangrongHost.exe 缺失")
    # PyInstaller's bootloader changes the per-process Windows DLL search
    # directory to _internal. That setting is inherited by spawned processes,
    # causing the independent native helper to hang while loading its CRT.
    # Restore normal search for the few milliseconds of CreateProcess, then
    # restore the frozen app's original setting for its own Python extensions.
    kernel = ctypes.windll.kernel32 if sys.platform == "win32" else None
    frozen_dir = getattr(sys, "_MEIPASS", None) if getattr(sys, "frozen", False) else None
    if frozen_dir is not None and kernel is not None:
        kernel.SetDllDirectoryW(None)
    try:
        return subprocess.Popen(
            [str(helper), "--server", str(file)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            bufsize=0,
        )
    finally:
        if frozen_dir is not None and kernel is not None:
            kernel.SetDllDirectoryW(str(frozen_dir))


def _error_message(code: str, detail: str = "") -> str:
    messages = {
        "1114": "广荣官方原生 DLL 初始化失败（WinError 1114）；可能不能脱离原宿主程序运行",
        "193": "广荣 DLL 或依赖文件的 32/64 位不匹配（WinError 193）",
        "126": "广荣 DLL 依赖文件缺失（WinError 126）",
        "127": "广荣 DLL 未提供要求的 TTS 接口",
        "6": "广荣语音合成没有返回有效音频",
    }
    return messages.get(code, "独立广荣原生引擎错误 " + code) + (": " + detail if detail else "")


def _parse_probe(data: bytes) -> tuple[list[str], str]:
    voices: dict[int, str] = {}
    ready = False
    for raw in data.decode("ascii", errors="replace").splitlines():
        fields = raw.split("\t", 2)
        if not fields:
            continue
        if fields[0] == "ERROR":
            code = fields[1] if len(fields) > 1 else "?"
            detail = fields[2] if len(fields) > 2 else ""
            return [], _error_message(code, detail)
        if fields[0] == "VOICE" and len(fields) == 3:
            try:
                idx = int(fields[1])
                voice = base64.b64decode(fields[2], validate=True).decode("utf-8")
                if 0 <= idx < 256:
                    voices[idx] = voice or f"广荣声音 {idx}"
            except (ValueError, UnicodeDecodeError):
                continue
        if fields[0] == "READY":
            ready = True
    if not ready:
        return [], "广荣辅助进程没有完成初始化，请检查组件是否适用于独立运行"
    return [voices[k] for k in sorted(voices)], ""


def list_guangrong_voices(path: str, timeout: float = 8.0):
    """A disposable native subprocess checks real vendor load and voice list."""
    if chosen_dll_path(path) is None:
        return [], "尚未安装广荣 64 位语音引擎"
    proc = None
    try:
        proc = _popen_host(path)
        out, _ = proc.communicate(input=b"QUIT\n", timeout=timeout)
        return _parse_probe(out)
    except subprocess.TimeoutExpired:
        return [], "广荣原生程序初始化超时；已强制终止，不影响游戏文字助手"
    except (OSError, ValueError) as exc:
        return [], "无法启动广荣独立原生引擎：" + str(exc)[:200]
    finally:
        if proc is not None:
            if proc.poll() is None:
                proc.kill()
            try:
                proc.communicate(timeout=1)
            except (subprocess.TimeoutExpired, OSError):
                pass


class GuangrongBridge:
    def __init__(self, dll_path: str, on_error=None, on_event=None):
        self.on_error, self.on_event = on_error, on_event
        self._generation = 0
        self._write_lock = threading.Lock()
        self._closed = False
        self._temp = tempfile.TemporaryDirectory(prefix="game-grtts-audio-")
        self.proc = _popen_host(dll_path)
        self._listener = threading.Thread(target=self._listen, name="NativeGuangrongPCM",
                                          daemon=True)
        self._listener.start()

    def _send(self, command: str):
        with self._write_lock:
            if self._closed or self.proc.stdin is None:
                return
            try:
                self.proc.stdin.write(command.encode("ascii") + b"\n")
                self.proc.stdin.flush()
            except (BrokenPipeError, OSError, ValueError) as exc:
                if self.on_error:
                    self.on_error("广荣辅助进程未运行：" + str(exc))

    def _listen(self):
        stream = self.proc.stdout
        if stream is None:
            return
        while not self._closed:
            try:
                header = stream.readline(4096)
                if not header:
                    if self.on_error and not self._closed:
                        self.on_error("广荣原生进程退出，退出码：" + str(self.proc.poll()))
                    break
                fields = header.decode("ascii", errors="replace").strip().split("\t")
                kind = fields[0]
                if kind == "ERROR":
                    code = fields[1] if len(fields) > 1 else "?"
                    detail = fields[2] if len(fields) > 2 else ""
                    if self.on_error:
                        self.on_error(_error_message(code, detail))
                elif kind == "HELLO":
                    if self.on_event:
                        self.on_event("广荣独立原生引擎已连接，音色数量：" +
                                      (fields[1] if len(fields) > 1 else "?"))
                elif kind == "AUDIO" and len(fields) == 6:
                    seq, sr, bits, channels, size = map(int, fields[1:])
                    if size <= 0 or size > MAX_AUDIO_BYTES:
                        raise ValueError("广荣 PCM 长度异常")
                    chunks = bytearray()
                    remaining = size
                    while remaining:
                        part = stream.read(remaining)
                        if not part:
                            raise EOFError("广荣 PCM 数据被截断")
                        chunks.extend(part)
                        remaining -= len(part)
                    if seq == self._generation:
                        self._play_pcm(seq, bytes(chunks), sr, bits, channels)
            except (OSError, ValueError, EOFError) as exc:
                if self.on_error and not self._closed:
                    self.on_error("广荣输出流错误：" + str(exc)[:200])
                break

    def _play_pcm(self, seq, pcm, sr, bits, channels):
        try:
            if sr not in (8000, 11025, 16000, 22050, 24000, 32000, 44100, 48000, 96000):
                raise ValueError("无效采样率")
            if bits not in (8, 16, 24, 32) or channels not in (1, 2):
                raise ValueError("不支持的 PCM 格式")
            import winsound
            path = Path(self._temp.name) / ("speech-" + str(seq) + ".wav")
            with wave.open(str(path), "wb") as file:
                file.setnchannels(channels)
                file.setsampwidth(bits // 8)
                file.setframerate(sr)
                file.writeframes(pcm)
            if seq != self._generation:
                return
            winsound.PlaySound(None, 0)
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC |
                               winsound.SND_NODEFAULT)
            if self.on_event:
                self.on_event("广荣原生引擎已提交 " + str(len(pcm)) +
                              " 字节 PCM 给扬声器；真实发声仍需实机确认")
            old_files = sorted(Path(self._temp.name).glob("speech-*.wav"))
            for old in old_files[:-5]:
                try:
                    old.unlink()
                except OSError:
                    pass
        except Exception as exc:
            if self.on_error:
                self.on_error("广荣音频播放失败：" + type(exc).__name__ + ": " + str(exc))

    def select(self, voice_index: int):
        self.stop()
        self._send("VOICE\t" + str(int(voice_index)))

    def speak(self, text: str):
        self.stop()
        self._generation += 1
        encoded = base64.b64encode(str(text).encode("utf-8")).decode("ascii")
        self._send("SPEAK\t" + str(self._generation) + "\t" + encoded)

    def stop(self):
        self._generation += 1
        self._send("STOP")
        try:
            import winsound
            winsound.PlaySound(None, 0)
        except (OSError, RuntimeError):
            pass

    def set_rate(self, value: int):
        self._send("RATE\t" + str(max(0, min(100, 50 + int(value) * 5))))

    def set_volume(self, value: int):
        self._send("VOL\t" + str(max(0, min(100, int(value)))))

    def close(self):
        self.stop()
        self._send("QUIT")
        self._closed = True
        try:
            self.proc.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=1)
        finally:
            try:
                if self.proc.stdin: self.proc.stdin.close()
                if self.proc.stdout: self.proc.stdout.close()
                self._temp.cleanup()
            except OSError:
                pass
