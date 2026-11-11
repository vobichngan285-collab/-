"""Call the author's ORIGINAL LunaTranslator v12.1.3.9 NativeUtils.dll.

This adapter does NOT implement/rewrite the author's GDI algorithm.
It calls the original exported GdiCropImage from screenshot.cpp, with
curr=1 (desktop-only), to avoid the known stale game-HWND/DirectX issue.

Upstream exactly: https://github.com/HIllya51/LunaTranslator/
  src/NativeImpl/NativeUtils/screenshot.cpp  (GdiCropImage)
  src/LunaTranslator/NativeUtils.py           (ctypes declaration)
Pinned upstream tag v12.1.3.9, commit 84677faeaa1e61bd7dd00b820090e9d2fe6c5142.
GPL-3.0. Verbatim original DLL and full original source are packaged.
"""
from __future__ import annotations

import ctypes
from ctypes import c_bool, c_int, c_size_t, c_ubyte, c_void_p, POINTER, CFUNCTYPE
from io import BytesIO
from pathlib import Path
import sys

from PIL import Image, ImageGrab


# The original NativeUtils.py uses CDLL and CFUNCTYPE (cdecl), not WinDLL.
_GDI_CALLBACK = CFUNCTYPE(None, POINTER(c_ubyte), c_size_t)
_native = None
_load_attempted = False
_native_error = ""


def _original_dll_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "NativeUtils.dll"
    return Path(__file__).resolve().parents[1] / "NativeUtils.dll"


def _load_original():
    global _native, _load_attempted, _native_error
    if _load_attempted:
        return _native
    _load_attempted = True
    path = _original_dll_path()
    try:
        if not path.is_file():
            raise FileNotFoundError("original NativeUtils.dll is not bundled")
        library = ctypes.CDLL(str(path))
        grab = library.GdiCropImage
        # Exact signature from the author's NativeUtils.py:
        # HWND, int x1, y1, x2, y2, callback(ptr,size), int curr
        grab.argtypes = [c_void_p, c_int, c_int, c_int, c_int, _GDI_CALLBACK, c_int]
        grab.restype = c_bool
        _native = grab
    except (OSError, AttributeError, ValueError) as exc:
        _native_error = type(exc).__name__
    return _native


def original_available() -> bool:
    return _load_original() is not None


def native_crop_desktop(box) -> Image.Image | None:
    """Call author's unchanged GdiCropImage(NULL, rect, callback, curr=1).

    Return None on failure or suspicious empty captures; caller preserves the
    previous known-good visible-desktop ImageGrab fallback.
    """
    left, top, right, bottom = tuple(map(int, box))
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0 or width * height > 40_000_000:
        return None
    grab = _load_original()
    if grab is None:
        return None
    payloads = []

    def on_image(pointer, size):
        # Original callback owns its memory; copy it before it returns.
        if pointer and 54 <= size <= width * height * 8 + 1024:
            payloads.append(ctypes.string_at(pointer, size))

    callback = _GDI_CALLBACK(on_image)
    try:
        success = grab(None, left, top, right, bottom, callback, 1)
        if not success or len(payloads) != 1 or payloads[0][:2] != b"BM":
            return None
        with Image.open(BytesIO(payloads[0])) as source:
            result = source.convert("RGB")
        if result.size != (width, height):
            return None
        # The native GDI desktop can be blank over some exclusive GPU frames.
        ext = result.getextrema()
        if all(lo == hi and lo in (0, 255) for lo, hi in ext):
            return None
        return result
    except (OSError, ValueError, OverflowError):
        return None


def grab_region_original(box, report=None):
    """Native author's region capture, never HWND GDI; safe old fallback."""
    box = tuple(map(int, box))
    image = native_crop_desktop(box)
    if image is not None:
        if report is not None:
            report["method"] = "luna_original_native_desktop"
        return image
    if report is not None:
        report["method"] = "desktop_visible_fallback"
    return ImageGrab.grab(bbox=box, all_screens=True)
