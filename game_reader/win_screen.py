"""Windows DPI-aware monitor screen capture and physical cursor position."""
from __future__ import annotations
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from PIL import Image, ImageGrab
from .luna_capture import capture_rect

user32 = ctypes.WinDLL("user32", use_last_error=True)

class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", RECT),
                ("rcWork", RECT), ("dwFlags", wintypes.DWORD)]

user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.MonitorFromPoint.argtypes = [POINT, wintypes.DWORD]
user32.MonitorFromPoint.restype = wintypes.HMONITOR
user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFO)]
user32.GetMonitorInfoW.restype = wintypes.BOOL
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short


def enable_dpi_awareness():
    """Call before creating Tk widgets: screenshot and cursor share physical px."""
    try:
        shcore = ctypes.WinDLL("shcore")
        shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except (AttributeError, OSError):
        try:
            user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def get_cursor() -> tuple[int, int]:
    pt = POINT()
    if not user32.GetCursorPos(ctypes.byref(pt)):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(pt.x), int(pt.y)


def is_key_down(vk: int) -> bool:
    # Wheel events have logical negative IDs, never Win32 virtual-key codes.
    return vk is not None and int(vk) >= 0 and bool(user32.GetAsyncKeyState(int(vk)) & 0x8000)


def monitor_rect_at_point(x: int, y: int) -> tuple[int, int, int, int]:
    """Actual monitor geometry at a fixed physical desktop coordinate."""
    monitor = user32.MonitorFromPoint(POINT(x, y), 2)
    if not monitor:
        raise ctypes.WinError(ctypes.get_last_error())
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(info)
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    r = info.rcMonitor
    return int(r.left), int(r.top), int(r.right), int(r.bottom)


def monitor_rect_at_cursor() -> tuple[int, int, int, int]:
    return monitor_rect_at_point(*get_cursor())


def grab_current_monitor(bound_hwnd=None, report=None) -> tuple[Image.Image, tuple[int, int]]:
    left, top, right, bottom = monitor_rect_at_cursor()
    target = foreground_capture_hwnd() if bound_hwnd is None else int(bound_hwnd)
    img = capture_rect((left, top, right, bottom), target, report=report)
    expected_size = (right - left, bottom - top)
    if img.size != expected_size:
        raise RuntimeError(f"Capture size mismatch: {img.size} vs {expected_size}")
    return img, (left, top)


def foreground_capture_hwnd() -> int:
    """Never use our own settings/overlay window as the game capture target."""
    from .foreground import foreground_window_id
    handle = foreground_window_id()
    if not handle:
        return 0
    try:
        user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND,
                                                    ctypes.POINTER(wintypes.DWORD)]
        process = wintypes.DWORD()
        user32.GetWindowThreadProcessId(wintypes.HWND(handle), ctypes.byref(process))
        import os
        return handle if process.value != os.getpid() else 0
    except (OSError, ValueError):
        return 0


def grab_game_rect(box, bound_hwnd=None, report=None):
    """Use the SAME pinned game HWND for each fresh screenshot."""
    target = foreground_capture_hwnd() if bound_hwnd is None else int(bound_hwnd)
    return capture_rect(box, target, report=report)
