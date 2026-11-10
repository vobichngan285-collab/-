"""Fixed-screen region tracking policy: no Windows hooks, threads, or OCR engine.

Keep the region in absolute physical display coordinates. Screen/monitor
changes invalidate it rather than silently relocating it to a wrong location.
Change gating never replaces OCR-level textual deduplication.
"""
from __future__ import annotations

from PIL import Image, ImageChops


def parse_fixed_region(box, monitor=None):
    """Return validated (left, top, right, bottom) or None.

    Unlike the mouse-relative F11 area this is NOT recentered at the cursor.
    """
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        return None
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in box):
        return None
    left, top, right, bottom = box
    if not (40 <= right - left <= 5000 and 40 <= bottom - top <= 5000):
        return None
    if monitor is not None:
        m = parse_monitor(monitor)
        if m is None:
            return None
        ml, mt, mr, mb = m
        if not (ml <= left < right <= mr and mt <= top < bottom <= mb):
            return None
    return left, top, right, bottom


def parse_monitor(value):
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    if not all(isinstance(x, int) and not isinstance(x, bool) for x in value):
        return None
    a,b,c,d = value
    return (a,b,c,d) if c>a and d>b else None


def region_on_same_monitor(region, saved_monitor, live_monitor):
    """Reject stale coordinates if DPI, resolution or screen geometry changed."""
    saved = parse_monitor(saved_monitor)
    live = parse_monitor(live_monitor)
    return bool(saved and live and saved == live
                and parse_fixed_region(region, saved) is not None)


def screenshot_fingerprint(image: Image.Image) -> Image.Image:
    """Tiny grayscale copy (RAM only) for cheap difference detection."""
    return image.convert("L").resize((128, 72), Image.Resampling.BILINEAR)


def frame_has_changed(previous: Image.Image | None, current: Image.Image) -> bool:
    """Sensitive to changed text, tolerant of minor compression / pixel noise."""
    if previous is None or previous.size != current.size:
        return True
    difference = ImageChops.difference(previous, current)
    histogram = difference.histogram()
    pixels = current.width * current.height
    above_threshold = sum(histogram[13:])
    return (above_threshold >= max(8, int(pixels * 0.008))
            or sum(i * n for i,n in enumerate(histogram)) >= pixels * 1.8)


def parse_strategy(raw):
    return raw if raw in ("change", "period") else "change"


def display_color(raw):
    """Five high contrast colors for native Windows outlines."""
    return raw if raw in ("#42DD9C", "#38A8FF", "#FFD34D", "#FF7373", "#FFFFFF") else "#42DD9C"


def parse_thickness(raw):
    try:
        n = int(raw)
    except (ValueError, TypeError):
        return 3
    return n if not isinstance(raw, bool) and 1 <= n <= 8 else 3
