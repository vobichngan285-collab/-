"""Windows DPI-aware *visible desktop* game capture and physical cursor position.

Screenshot rule: read the pixels the user can actually see. A game HWND is used
ONLY to locate its current client rectangle, never as a GDI image source.
This keeps a menu switch from accidentally reading a stale BitBlt frame.
"""
from __future__ import annotations
import ctypes
from ctypes import wintypes
from PIL import Image, ImageGrab

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
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetClientRect.restype = wintypes.BOOL
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]
user32.ClientToScreen.restype = wintypes.BOOL


def enable_dpi_awareness():
    """Call before creating Tk widgets: screenshot and cursor share physical px."""
    try:
        shcore = ctypes.WinDLL("shcore")
        shcore.SetProcessDpiAwareness(2)
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
    # Mouse wheel events use negative logical IDs, not Windows virtual-key IDs.
    return vk is not None and int(vk) >= 0 and bool(user32.GetAsyncKeyState(int(vk)) & 0x8000)


def monitor_rect_at_point(x: int, y: int) -> tuple[int, int, int, int]:
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


def game_client_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    """Current client area in *physical desktop coordinates*; no window pixels read."""
    if not hwnd:
        return None
    handle = wintypes.HWND(hwnd)
    if not user32.IsWindow(handle) or user32.IsIconic(handle):
        return None
    r = RECT()
    if not user32.GetClientRect(handle, ctypes.byref(r)):
        return None
    if r.right <= r.left or r.bottom <= r.top:
        return None
    start = POINT(r.left, r.top)
    end = POINT(r.right, r.bottom)
    if not (user32.ClientToScreen(handle, ctypes.byref(start))
            and user32.ClientToScreen(handle, ctypes.byref(end))):
        return None
    box = (int(start.x), int(start.y), int(end.x), int(end.y))
    return box if box[2] > box[0] and box[3] > box[1] else None


def intersect_rect(a, b) -> tuple[int, int, int, int] | None:
    box = (max(a[0], b[0]), max(a[1], b[1]),
           min(a[2], b[2]), min(a[3], b[3]))
    return box if box[2] > box[0] and box[3] > box[1] else None


def visible_desktop_rect(box, report=None) -> Image.Image:
    """Capture fresh visible pixels. Never call HWND GetDC/BitBlt or use cached frames."""
    box = tuple(map(int, box))
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError("Invalid screenshot rectangle")
    image = ImageGrab.grab(bbox=box, all_screens=True)
    if image.size != (box[2] - box[0], box[3] - box[1]):
        raise RuntimeError("截图尺寸与屏幕区域不匹配")
    if report is not None:
        report["method"] = "desktop_visible"
    return image


def grab_current_monitor(bound_hwnd=None, report=None) -> tuple[Image.Image, tuple[int, int]]:
    """F8: game HWND selects the region; actual pixels always come from desktop.

    F8 without a bound game keeps the original V1.2 full-monitor behavior.
    Never quietly switch to a different window or use a stale GDI screenshot.
    """
    monitor = monitor_rect_at_cursor()
    box = monitor
    if bound_hwnd:
        game_box = game_client_rect(int(bound_hwnd))
        if game_box is None:
            raise RuntimeError("游戏窗口已关闭、最小化或无法取得实际位置；请返回游戏后再按F8")
        box = intersect_rect(game_box, monitor)
        if box is None:
            raise RuntimeError("游戏窗口与鼠标所在显示器不重叠；请将鼠标移到游戏窗口后重试")
    image = visible_desktop_rect(box, report)
    if report is not None:
        report["method"] = "desktop_game_client" if bound_hwnd else "desktop_monitor"
        report["bound_hwnd"] = bool(bound_hwnd)
    return image, (box[0], box[1])


def foreground_capture_hwnd() -> int:
    """Never bind the app's own settings window as a game."""
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
    """Hover/region/picker: supplied screen rectangle; HWND never changes pixels."""
    image = visible_desktop_rect(box, report)
    if report is not None:
        report["bound_hwnd"] = bool(bound_hwnd)
    return image
