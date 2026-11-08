"""Tiny visual page-change check; DOES NOT run OCR continuously.

Compare low-resolution screen signatures (160x90) for the monitor that was
explicitly scanned with F8. This is best-effort: animations can cause false
positives; tiny localized changes can be missed. The 60-second TTL is a
separate unconditional safety limit.
"""
from __future__ import annotations

from dataclasses import dataclass
from PIL import Image, ImageGrab

THUMB_SIZE = (160, 90)


@dataclass(frozen=True)
class Signature:
    pixels: bytes
    origin: tuple[int, int]
    screen_size: tuple[int, int]


def signature_from_image(image: Image.Image, origin: tuple[int, int]) -> Signature:
    thumbnail = image.convert("RGB").resize(THUMB_SIZE, Image.Resampling.BILINEAR)
    return Signature(thumbnail.tobytes(), tuple(origin), tuple(image.size))


def capture_signature(origin: tuple[int, int],
                      screen_size: tuple[int, int]) -> Signature:
    x, y = origin
    w, h = screen_size
    current = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True,
                             include_layered_windows=False)
    if current.size != screen_size:
        raise RuntimeError("Monitor geometry changed since the last OCR scan")
    return signature_from_image(current, origin)


def changed_pixel_fraction(previous: Signature, current: Signature,
                           channel_threshold: int = 52) -> float:
    """Fraction of low-resolution pixels whose RGB appearance changed a lot."""
    if (previous.origin != current.origin or
            previous.screen_size != current.screen_size):
        return 1.0
    old, new = previous.pixels, current.pixels
    if not old or len(old) != len(new) or len(old) % 3:
        return 1.0
    changed = 0
    for idx in range(0, len(old), 3):
        if (abs(old[idx] - new[idx]) >= channel_threshold or
            abs(old[idx + 1] - new[idx + 1]) >= channel_threshold or
            abs(old[idx + 2] - new[idx + 2]) >= channel_threshold):
            changed += 1
    return changed / (len(old) // 3)


class SceneGuard:
    """Trigger invalidation on a strong change or two smaller changes."""
    def __init__(self, initial: Signature):
        self.initial = initial
        self.moderate_count = 0

    def changed(self, current: Signature) -> bool:
        fraction = changed_pixel_fraction(self.initial, current)
        if fraction >= 0.18:
            return True
        if fraction >= 0.065:
            self.moderate_count += 1
        else:
            self.moderate_count = 0
        return self.moderate_count >= 2
