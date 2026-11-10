"""Keep one live game HWND across menu/page changes (LunaTranslator-style).

LunaTranslator's OCR text source stores its hwnd in hwndChanged() and reuses
that value for subsequent imageCutEx() calls. The caller's game-window binding
is separate from the screenshot implementation.
No game process is injected or modified; read-only Win32 window queries.
"""
from __future__ import annotations

import ctypes
import os
from ctypes import wintypes


def window_process_id(hwnd: int) -> int:
    """Return the owning process or zero for a destroyed/invalid HWND."""
    if not hwnd or not hasattr(ctypes, "WinDLL"):
        return 0
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.IsWindow.argtypes = [wintypes.HWND]
    user32.IsWindow.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND,
                                                 ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    if not user32.IsWindow(wintypes.HWND(hwnd)):
        return 0
    pid = wintypes.DWORD(0)
    if not user32.GetWindowThreadProcessId(wintypes.HWND(hwnd),
                                            ctypes.byref(pid)):
        return 0
    return int(pid.value)


def active_foreground() -> int:
    from .foreground import foreground_window_id
    return foreground_window_id()


class GameWindowBinding:
    """Bind on first game capture, release only when the HWND truly disappears.

    Foreground changes due to overlays, loading screens or child windows do
    not silently replace the game HWND. A new game can be bound after the
    previous window is destroyed.
    """

    def __init__(self, foreground=None, process_id=None, own_pid=None):
        self._foreground = foreground or active_foreground
        self._process_id = process_id or window_process_id
        self._own_pid = os.getpid() if own_pid is None else own_pid
        self.hwnd = 0
        self.pid = 0

    def target(self) -> int:
        if self.hwnd:
            if self._process_id(self.hwnd) == self.pid:
                return self.hwnd
            self.hwnd = self.pid = 0
        candidate = int(self._foreground() or 0)
        pid = self._process_id(candidate) if candidate else 0
        if pid and pid != self._own_pid:
            self.hwnd, self.pid = candidate, pid
        return self.hwnd

    def is_active(self) -> bool:
        """Do not read old coordinates over an unrelated foreground app."""
        if not self.hwnd or not self.pid:
            return True
        if self._process_id(self.hwnd) != self.pid:
            return False
        current = int(self._foreground() or 0)
        return current == self.hwnd or self._process_id(current) == self.pid
