"""Blue Star ↔ FULL ORIGINAL LunaTranslator process I/O adapter ONLY.

No OCR model, capture, frame analysis, OCR scheduling, or OCR postprocess
algorithm is implemented here. The untouched Luna v12.1.3.9 runtime performs
all those operations in its own process. This module only starts that process
and converts upstream OCR box coordinates into our existing OCRLine UI type.
"""
from __future__ import annotations
import json
from queue import Queue
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time

from .core import OCRLine

_CONTROL = ("127.0.0.1", 29380)
_TEXT = ("127.0.0.1", 29381)
_MAX_REPLY = 2_000_000


def packaged_luna_exe() -> Path:
    root = (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False)
            else Path(__file__).resolve().parents[1])
    return root / "LunaOriginal" / "LunaTranslator_x64" / "LunaTranslator.exe"


def _convert_original_boxes(payload, box):
    """Coordinates only; text and segmentation are ORIGINAL upstream results."""
    if not isinstance(payload, dict):
        raise ValueError("Luna original replied without JSON result")
    entries = payload.get("results", [])
    if not isinstance(entries, list):
        return []
    x0, y0 = box[0], box[1]
    result = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        txt = e.get("text")
        coords = e.get("box")
        if not isinstance(txt, str) or not txt.strip():
            continue
        if not isinstance(coords, list) or len(coords) != 4:
            continue
        try:
            xs = [float(p["x"]) for p in coords]
            ys = [float(p["y"]) for p in coords]
        except (KeyError, ValueError, TypeError):
            continue
        left = int(min(xs)) + x0
        top = int(min(ys)) + y0
        right = int(max(xs) + 0.999) + x0
        bottom = int(max(ys) + 0.999) + y0
        if left < right and top < bottom:
            result.append(OCRLine(txt, left, top, right, bottom, 1.0))
    return result


class LunaOriginalOCR:
    def __init__(self, event_sink=None):
        self.events = event_sink
        self.proc = None
        self._stop = threading.Event()
        self._udp = None
        self._controls = Queue()
        threading.Thread(target=self._control_loop, daemon=True,
                         name="OriginalLunaSerializedControls").start()
        self.last_preprocess_ms = 0
        self.last_engine_ms = 0
        if event_sink is not None:
            threading.Thread(target=self._listen, daemon=True,
                             name="OriginalLunaTextBridge").start()

    def _listen(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                self._udp = sock
                sock.bind(_TEXT)
                sock.settimeout(0.3)
                while not self._stop.is_set():
                    try:
                        payload, addr = sock.recvfrom(65536)
                    except socket.timeout:
                        continue
                    except OSError:
                        break
                    if addr[0] != "127.0.0.1":
                        continue
                    try:
                        message = json.loads(payload.decode("utf-8"))
                        if message.get("kind") == "original_ocr_text":
                            text = message.get("text")
                            if isinstance(text, str) and text.strip():
                                self.events.put(("luna_original_text", text))
                    except (UnicodeError, ValueError, AttributeError):
                        pass
        except OSError as exc:
            if self.events is not None:
                self.events.put(("luna_bridge_error",
                                 "无法接收 Luna 原版识别文字：" + str(exc)[:120]))

    def launch(self):
        if self._probe():
            return True
        exe = packaged_luna_exe()
        if not exe.is_file():
            raise FileNotFoundError(
                "缺少完整版 LunaTranslator 官方程序：请使用完整打包的新版本")
        if self.proc is None or self.proc.poll() is not None:
            self.proc = subprocess.Popen(
                [str(exe), "--userconfig", "userconfig_bluestar"],
                cwd=str(exe.parent),
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
        return True

    def _probe(self):
        try:
            result = self._call("ping", timeout=0.4, start=False)
            return bool(result.get("ok"))
        except (OSError, TimeoutError, ValueError, RuntimeError):
            return False

    def _call(self, action, timeout=15, start=True, **values):
        if start and not self._probe():
            self.launch()
        deadline = time.monotonic() + timeout
        request = json.dumps(dict(action=action, **values), ensure_ascii=False).encode("utf-8") + b"\n"
        while True:
            try:
                with socket.create_connection(_CONTROL, timeout=min(1.5, max(0.2, timeout))) as s:
                    s.settimeout(min(timeout, 15.0))
                    s.sendall(request)
                    buffer = bytearray()
                    while b"\n" not in buffer and len(buffer) <= _MAX_REPLY:
                        block = s.recv(min(65536, _MAX_REPLY + 1 - len(buffer)))
                        if not block:
                            break
                        buffer.extend(block)
                    if len(buffer) > _MAX_REPLY or b"\n" not in buffer:
                        raise RuntimeError("Luna 原版接口响应不完整")
                    response = json.loads(buffer.split(b"\n", 1)[0].decode("utf-8"))
                    if not isinstance(response, dict):
                        raise RuntimeError("Luna 原版返回非法数据")
                    if not response.get("ok", False):
                        raise RuntimeError(str(response.get("error", "Luna 原版 OCR 失败")))
                    return response
            except (ConnectionRefusedError, ConnectionResetError, OSError) as exc:
                if not start or time.monotonic() >= deadline:
                    raise RuntimeError("Luna 原版尚未启动或 IPC 不可用") from exc
                time.sleep(0.15)

    def recognize_box(self, box):
        left, top, right, bottom = tuple(map(int, box))
        reply = self._call("ocr", box=[left, top, right, bottom], timeout=25)
        return _convert_original_boxes(reply.get("result", {}), (left, top, right, bottom))

    def request_region(self, box, visible=True):
        result = self._call("region", box=list(map(int, box)), timeout=15)
        self.request_border(visible)
        self.request_resume()
        return result

    def request_clear(self):
        return self._call("clear", timeout=8)

    def request_pause(self):
        return self._call("pause", timeout=8)

    def request_resume(self):
        return self._call("resume", timeout=8)

    def request_border(self, visible):
        return self._call("border", visible=bool(visible), timeout=8)

    def _control_loop(self):
        while not self._stop.is_set():
            task = self._controls.get()
            if task is None:
                return
            method, values = task
            try:
                getattr(self, method)(*values)
            except Exception as exc:
                if self.events is not None:
                    self.events.put(("luna_bridge_error", str(exc)[:220]))

    def do_async(self, operation, *values):
        # Original Qt commands must preserve user-entered order across modes.
        if not self._stop.is_set():
            self._controls.put((operation, values))

    def close(self):
        self._stop.set()
        self._controls.put(None)
        if self._udp is not None:
            try:
                self._udp.close()
            except OSError:
                pass
        # Do not kill the upstream original GUI unexpectedly; the user may
        # continue using its settings, performance tools and range UI.
