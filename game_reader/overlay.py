"""Native click-through, non-activating Windows highlight frame.

Four thin layered WS_EX_TRANSPARENT native windows draw only the edges.
Colors get separate registered window classes and are never included inside
the exact OCR capture rectangle. No Tk focus or mouse events are consumed.
"""
from __future__ import annotations
import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WS_POPUP = 0x80000000
WS_EX_TOPMOST = 0x00000008
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
LWA_ALPHA = 2
SW_HIDE = 0
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = -1

_WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT,
                              wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", _WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.RegisterClassW.restype = wintypes.ATOM
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p,
]
user32.CreateWindowExW.restype = wintypes.HWND
user32.SetLayeredWindowAttributes.argtypes = [wintypes.HWND, wintypes.COLORREF,
                                              wintypes.BYTE, wintypes.DWORD]
user32.SetLayeredWindowAttributes.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND,
                                  ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_int, wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL
gdi32.CreateSolidBrush.argtypes = [wintypes.COLORREF]
gdi32.CreateSolidBrush.restype = wintypes.HBRUSH
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE

_REGISTRY = {}  # Color -> (class, brush, WNDPROC lifetime reference)


def _register(color: str):
    color = color.upper()
    if color in _REGISTRY:
        return _REGISTRY[color][0]
    if not (len(color) == 7 and color[0] == "#" and
            all(c in "0123456789ABCDEF" for c in color[1:])):
        raise ValueError("invalid_outline_color")
    r, g, b = (int(color[a:a+2], 16) for a in (1, 3, 5))
    brush = gdi32.CreateSolidBrush((b << 16) | (g << 8) | r)
    if not brush:
        raise ctypes.WinError(ctypes.get_last_error())
    callback = ctypes.cast(user32.DefWindowProcW, _WNDPROC)
    cls = WNDCLASSW()
    cls.style = 0
    cls.lpfnWndProc = callback
    cls.cbClsExtra = cls.cbWndExtra = 0
    cls.hInstance = kernel32.GetModuleHandleW(None)
    cls.hIcon = None
    cls.hCursor = None
    cls.hbrBackground = brush
    cls.lpszMenuName = None
    cls_name = "GameTextReaderVisualRegionOutline_" + color[1:]
    cls.lpszClassName = cls_name
    if not user32.RegisterClassW(ctypes.byref(cls)):
        code = ctypes.get_last_error()
        if code != 1410:  # Class registered in this process already
            raise ctypes.WinError(code)
    _REGISTRY[color] = (cls_name, brush, callback)
    return cls_name


class ClickThroughOutline:
    def __init__(self, *, alpha: int = 220, padding: int = 4,
                 thickness: int = 3, color: str = "#5CD537"):
        self.alpha = max(16, min(255, int(alpha)))
        self.padding = max(0, min(20, int(padding)))
        self.thickness = max(1, min(8, int(thickness)))
        self.color = color
        class_name = _register(color)
        self.handles = []
        self._current = None
        instance = kernel32.GetModuleHandleW(None)
        exstyle = (WS_EX_TOPMOST | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW |
                   WS_EX_LAYERED | WS_EX_NOACTIVATE)
        for _ in range(4):
            hwnd = user32.CreateWindowExW(
                exstyle, class_name, "", WS_POPUP, 0, 0, 1, 1,
                None, None, instance, None)
            if not hwnd:
                self.close()
                raise ctypes.WinError(ctypes.get_last_error())
            if not user32.SetLayeredWindowAttributes(hwnd, 0, self.alpha, LWA_ALPHA):
                user32.DestroyWindow(hwnd)
                self.close()
                raise ctypes.WinError(ctypes.get_last_error())
            user32.ShowWindow(hwnd, SW_HIDE)
            self.handles.append(hwnd)

    def show(self, line) -> None:
        if line is None:
            self.hide()
            return
        rect = (int(line.left), int(line.top), int(line.right), int(line.bottom))
        if self._current == rect:
            return
        self._current = rect
        pad, thick = self.padding, self.thickness
        left, top, right, bottom = rect
        left -= pad
        top -= pad
        right += pad
        bottom += pad
        width, height = max(10, right - left), max(10, bottom - top)
        segments = (
            (left, top, width, thick),
            (left, top + height - thick, width, thick),
            (left, top + thick, thick, max(1, height - 2*thick)),
            (left + width - thick, top + thick, thick, max(1, height - 2*thick)),
        )
        for hwnd, (xx, yy, ww, hh) in zip(self.handles, segments):
            if not user32.SetWindowPos(hwnd, HWND_TOPMOST, xx, yy, ww, hh,
                                       SWP_NOACTIVATE | SWP_SHOWWINDOW):
                raise ctypes.WinError(ctypes.get_last_error())

    def hide(self):
        if self._current is None:
            return
        self._current = None
        for hwnd in self.handles:
            user32.ShowWindow(hwnd, SW_HIDE)

    def close(self):
        for hwnd in self.handles:
            user32.DestroyWindow(hwnd)
        self.handles.clear()
        self._current = None
