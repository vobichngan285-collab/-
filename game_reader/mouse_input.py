"""Non-blocking Windows wheel input. Never swallow the game's mouse messages.

The hook is deliberately used only for wheel events: ordinary keyboard and mouse
button state still use the existing GetAsyncKeyState logic.
"""
from __future__ import annotations

import ctypes
import threading
import time
from ctypes import wintypes
from queue import Empty, SimpleQueue

WHEEL_UP = -1001
WHEEL_DOWN = -1002
WM_MOUSEWHEEL = 0x020A
WM_QUIT = 0x0012
WH_MOUSE_LL = 14
WHEEL_DELTA = 120


class WheelAccumulator:
    """Convert high-resolution partial deltas to discrete steps."""
    def __init__(self):
        self.delta = 0

    def push(self, delta):
        delta = int(delta)
        if self.delta and (self.delta > 0) != (delta > 0):
            self.delta = 0
        self.delta += delta
        if self.delta >= WHEEL_DELTA:
            self.delta = self.delta % WHEEL_DELTA
            return WHEEL_UP
        if self.delta <= -WHEEL_DELTA:
            self.delta = -((-self.delta) % WHEEL_DELTA)
            return WHEEL_DOWN
        return None


class MouseWheelListener:
    """Read WH_MOUSE_LL on its own message-loop thread; CallNextHookEx always."""
    def __init__(self):
        self._queue = SimpleQueue()
        self._ready = threading.Event()
        self._thread_id = 0
        self._callback = None
        self._thread = None
        self.error = ""

    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._listen, daemon=True,
                                            name="BlueStarWheelHook")
            self._thread.start()

    def drain(self):
        found = []
        while True:
            try:
                found.append(self._queue.get_nowait())
            except Empty:
                return found

    def close(self):
        if self._thread_id:
            try:
                ctypes.WinDLL("user32", use_last_error=True).PostThreadMessageW(
                    self._thread_id, WM_QUIT, 0, 0)
            except (OSError, AttributeError):
                pass

    def _listen(self):
        if not hasattr(ctypes, "WinDLL"):
            self.error = "需要 Windows 才能读取全局滚轮。"
            self._ready.set()
            return

        class POINT(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

        class MSLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [("pt", POINT), ("mouseData", wintypes.DWORD),
                        ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
                        ("dwExtraInfo", ctypes.c_size_t)]

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int,
                                            wintypes.WPARAM, wintypes.LPARAM)
        user32.SetWindowsHookExW.argtypes = [ctypes.c_int, callback_type,
                                             wintypes.HINSTANCE, wintypes.DWORD]
        user32.SetWindowsHookExW.restype = wintypes.HHOOK
        user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int,
                                         wintypes.WPARAM, wintypes.LPARAM]
        user32.CallNextHookEx.restype = ctypes.c_ssize_t
        user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
        user32.UnhookWindowsHookEx.restype = wintypes.BOOL
        user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                                       wintypes.UINT, wintypes.UINT]
        user32.GetMessageW.restype = ctypes.c_int
        accumulator = WheelAccumulator()

        def callback(code, wparam, lparam):
            if code >= 0 and wparam == WM_MOUSEWHEEL:
                data = ctypes.cast(lparam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                delta = ctypes.c_short(data.mouseData >> 16).value
                key = accumulator.push(delta)
                if key is not None:
                    self._queue.put((key, time.monotonic()))
            return user32.CallNextHookEx(None, code, wparam, lparam)

        self._callback = callback_type(callback)
        self._thread_id = kernel32.GetCurrentThreadId()
        hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._callback, None, 0)
        if not hook:
            self.error = f"滚轮监听安装失败：Windows {ctypes.get_last_error()}"
            self._ready.set()
            self._thread_id = 0
            return
        self._ready.set()
        try:
            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            user32.UnhookWindowsHookEx(hook)
            self._thread_id = 0
            self._callback = None
