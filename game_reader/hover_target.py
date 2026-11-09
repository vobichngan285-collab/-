"""Select the single OCR text region nearest to the physical mouse cursor.

The V1.2 PP-OCRv6 Small recognizer and absolute screen coordinates are left
unchanged. A pointer-centred snapshot is only an image collection area, never
permission to concatenate unrelated labels elsewhere inside that snapshot.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from .core import OCRLine, build_reading_regions
from .hover_modes import RelativeRegion


@dataclass(frozen=True)
class NearbyText:
    text: str
    bounds: tuple[int, int, int, int]
    distance_px: float


def centered_region(size: RelativeRegion) -> RelativeRegion:
    """Only width/height come from F11; the hover scan is ALWAYS cursor centred.

    Old settings may contain off-centre offsets from the previous experimental
    build. Ignoring those values prevents reading labels above/beside the mouse.
    """
    return RelativeRegion(-size.width // 2, -size.height // 2,
                          size.width, size.height)


def distance_to_ocr_box(line: OCRLine, cursor: tuple[int, int]) -> float:
    """Euclidean distance to rectangle edge; 0 means pointer inside the text."""
    x, y = cursor
    dx = max(line.left - x, 0, x - line.right)
    dy = max(line.top - y, 0, y - line.bottom)
    return math.hypot(dx, dy)


def nearest_readable_text(lines: Iterable[OCRLine], cursor: tuple[int, int],
                          *, max_distance_px: int = 155) -> NearbyText | None:
    """Return ONLY nearest readable text or silence if no nearby text.

    Wrapped, long paragraphs already grouped by V1.2 build_reading_regions()
    are treated as one candidate. Other text (e.g. '7 Days to Die' above
    'DLSS') is never appended just because it shares the cropped screenshot.

    The distance limit prevents speaking arbitrary unrelated text when the
    image contains no label near the pointer.
    """
    if max_distance_px < 1:
        raise ValueError("nearest text distance limit must be positive")
    regions = [line for line in build_reading_regions(lines)
               if line.text and line.right > line.left and line.bottom > line.top]
    if not regions:
        return None
    # Closest actual rectangle edge is the primary criterion. Ties prefer a
    # centre close to the mouse, then stable top-to-bottom OCR order.
    target = min(regions, key=lambda line: (
        distance_to_ocr_box(line, cursor),
        abs(line.center[0] - cursor[0]) + abs(line.center[1] - cursor[1]),
        line.top, line.left
    ))
    distance = distance_to_ocr_box(target, cursor)
    if distance > max_distance_px:
        return None
    return NearbyText(
        target.text,
        (target.left, target.top, target.right, target.bottom),
        distance,
    )
