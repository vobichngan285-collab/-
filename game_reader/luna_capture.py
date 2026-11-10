"""Window-based screenshot path copied in behavior from LunaTranslator v12.1.3.9.

Source: HIllya51/LunaTranslator, src/NativeImpl/NativeUtils/screenshot.cpp
GdiCropImage: screen rectangle -> ScreenToClient -> GetDC -> BitBlt;
reject blank HWND images, then fall back to a desktop capture.
Port of the Win32 algorithm, not a modification of the author's executable.
Original source GPL-3.0; copyright HIllya51 and contributors.
This derived implementation is distributed under GPL-3.0-or-later.
"""
from __future__ import annotations
import ctypes
from ctypes import wintypes
from PIL import Image, ImageGrab


SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0


class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG)]


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER),
                ("bmiColors", wintypes.DWORD * 3)]


def screen_to_client_box(hwnd: int, box, user32=None):
    """Exact Luna GdiCropImage coordinate mapping, in physical pixels."""
    if not hwnd:
        return None
    if user32 is None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
    if user32.IsIconic(wintypes.HWND(hwnd)):
        return None
    left, top, right, bottom = map(int, box)
    if right <= left or bottom <= top:
        return None
    client = RECT()
    if not user32.GetClientRect(wintypes.HWND(hwnd), ctypes.byref(client)):
        return None
    start, end = POINT(left, top), POINT(right, bottom)
    if (not user32.ScreenToClient(wintypes.HWND(hwnd), ctypes.byref(start))
            or not user32.ScreenToClient(wintypes.HWND(hwnd), ctypes.byref(end))):
        return None
    if not (0 <= start.x < end.x <= client.right
            and 0 <= start.y < end.y <= client.bottom):
        return None
    return start.x, start.y, end.x, end.y


def _gdi_window_box(hwnd: int, box):
    """GetDC(hwnd) + BitBlt, with one top-down DIB and explicit resource cleanup."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    handle = wintypes.HWND(hwnd)
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.GetDC.restype = wintypes.HDC
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateDIBSection.argtypes = [wintypes.HDC, ctypes.POINTER(BITMAPINFO),
                                      wintypes.UINT, ctypes.POINTER(ctypes.c_void_p),
                                      wintypes.HANDLE, wintypes.DWORD]
    gdi32.CreateDIBSection.restype = wintypes.HBITMAP
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
    gdi32.SelectObject.restype = wintypes.HANDLE
    gdi32.BitBlt.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int,
                            ctypes.c_int, ctypes.c_int, wintypes.HDC,
                            ctypes.c_int, ctypes.c_int, wintypes.DWORD]
    gdi32.BitBlt.restype = wintypes.BOOL
    gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    client_box = screen_to_client_box(hwnd, box, user32)
    if client_box is None:
        return None
    x1, y1, x2, y2 = client_box
    width, height = x2 - x1, y2 - y1
    if width * height > 40000000:
        return None
    source = user32.GetDC(handle)
    if not source:
        return None
    memory, bitmap, old = None, None, None
    try:
        memory = gdi32.CreateCompatibleDC(source)
        if not memory:
            return None
        info = BITMAPINFO()
        info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        info.bmiHeader.biWidth = width
        info.bmiHeader.biHeight = -height
        info.bmiHeader.biPlanes = 1
        info.bmiHeader.biBitCount = 32
        address = ctypes.c_void_p()
        bitmap = gdi32.CreateDIBSection(source, ctypes.byref(info),
                                         DIB_RGB_COLORS, ctypes.byref(address),
                                         None, 0)
        if not bitmap or not address.value:
            return None
        old = gdi32.SelectObject(memory, bitmap)
        if not old:
            return None
        if not gdi32.BitBlt(memory, 0, 0, width, height, source,
                            x1, y1, SRCCOPY):
            return None
        image = Image.frombytes("RGB", (width, height),
                                ctypes.string_at(address, width * height * 4),
                                "raw", "BGRX", 0, 1)
        # Like LunaTranslator's parseBMP(needcheck=True), don't use a
        # black/white placeholder when a game uses a non-GDI renderer.
        extrema = image.getextrema()
        if all(low == high and low in (0, 255) for low, high in extrema):
            return None
        return image
    finally:
        if old and memory:
            gdi32.SelectObject(memory, old)
        if bitmap:
            gdi32.DeleteObject(bitmap)
        if memory:
            gdi32.DeleteDC(memory)
        user32.ReleaseDC(handle, source)


def capture_rect(box, hwnd=0):
    """Capture absolute desktop coordinates; keep screenshot and origin 1:1.

    A failed window GDI capture must not be treated as a successful OCR image.
    The fallback is our original full-monitor ImageGrab path.
    """
    box = tuple(map(int, box))
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError("Invalid screen rectangle")
    if hwnd:
        try:
            image = _gdi_window_box(int(hwnd), box)
            if image is not None and image.size == (
                    box[2] - box[0], box[3] - box[1]):
                return image
        except (OSError, ValueError, ctypes.ArgumentError):
            pass
    return ImageGrab.grab(bbox=box, all_screens=True)
