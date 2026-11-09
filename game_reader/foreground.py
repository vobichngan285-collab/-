"""Minimal, read-only Win32 foreground window classification.

Do not capture or log window titles; this is only to suppress scanning Windows
desktop icons and Explorer chrome when gaming tooltip OCR is active.
"""
from __future__ import annotations
import ctypes
from ctypes import wintypes


def foreground_class() -> str:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int
    handle = user32.GetForegroundWindow()
    if not handle:
        return ""
    buffer = ctypes.create_unicode_buffer(256)
    n = user32.GetClassNameW(handle, buffer, 256)
    return buffer.value if n > 0 else ""


def foreground_window_id() -> int:
    """Non-sensitive HWND identity, used only to discard stale full-screen OCR."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    return int(user32.GetForegroundWindow() or 0)
