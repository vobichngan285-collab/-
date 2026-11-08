"""Pure screen-coordinate / OCR hit-testing primitives (independent of Windows GUI)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
import math


@dataclass(frozen=True)
class OCRLine:
    text: str
    left: int
    top: int
    right: int
    bottom: int
    confidence: float = 1.0

    @property
    def center(self) -> tuple[float, float]:
        return ((self.left + self.right) / 2, (self.top + self.bottom) / 2)


def parse_paddle_result(result: Any, offset_x: int = 0, offset_y: int = 0,
                        min_confidence: float = 0.42) -> list[OCRLine]:
    """Convert a PaddleOCR 3.x OCRResult (or its JSON) to absolute pixel boxes.

    OCR 3.x returns rec_texts / rec_scores / rec_boxes; JSON may contain a
    top-level 'res' object. Reject malformed/empty coordinates, never fabricate
    missing text. The caller provides capture's top-left desktop coordinates.
    """
    if hasattr(result, "json"):
        result = result.json
    if callable(result):
        result = result()
    if not isinstance(result, dict):
        raise ValueError("Unexpected PaddleOCR result type")
    obj = result.get("res", result)
    if not isinstance(obj, dict):
        raise ValueError("OCR result 'res' is not an object")
    texts, boxes = obj.get("rec_texts", []), obj.get("rec_boxes", [])
    scores = obj.get("rec_scores", [])
    if len(texts) != len(boxes):
        raise ValueError("Text and bounding box counts differ")
    out: list[OCRLine] = []
    for idx, (raw_text, raw_box) in enumerate(zip(texts, boxes)):
        text = str(raw_text).strip()
        if not text:
            continue
        score = float(scores[idx]) if idx < len(scores) else 1.0
        if not math.isfinite(score) or score < min_confidence:
            continue
        if hasattr(raw_box, "tolist"):
            raw_box = raw_box.tolist()
        if len(raw_box) == 4 and all(isinstance(v, (float, int)) for v in raw_box):
            x1, y1, x2, y2 = raw_box
        elif len(raw_box) >= 4 and hasattr(raw_box[0], "__len__"):
            xs, ys = [p[0] for p in raw_box], [p[1] for p in raw_box]
            x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
        else:
            continue
        if not all(math.isfinite(float(v)) for v in (x1, y1, x2, y2)):
            continue
        x1, y1, x2, y2 = (round(float(x1)), round(float(y1)),
                              round(float(x2)), round(float(y2)))
        if x2 <= x1 or y2 <= y1:
            continue
        out.append(OCRLine(text, x1 + offset_x, y1 + offset_y,
                           x2 + offset_x, y2 + offset_y, score))
    return sorted(out, key=lambda l: (l.top, l.left))


def hit_test(lines: Iterable[OCRLine], x: int, y: int,
             margin_x: int = 8, margin_y: int = 5) -> OCRLine | None:
    """Choose nearest OCR line under cursor; don't return text far away.

    Resolves overlapping expanded boxes by normalized distance to the original
    rectangle; chooses the shorter y-distance first so neighboring rows don't
    steal the hover target.
    """
    matches = []
    for line in lines:
        if not (line.left - margin_x <= x <= line.right + margin_x and
                line.top - margin_y <= y <= line.bottom + margin_y):
            continue
        dx = max(line.left - x, 0, x - line.right)
        dy = max(line.top - y, 0, y - line.bottom)
        cx, cy = line.center
        normalized = abs(x - cx) / max(line.right - line.left, 1)
        matches.append((dy, dx, normalized, line))
    return min(matches, key=lambda t: t[:3])[3] if matches else None


class HoverTracker:
    """One speech event per dwell on a line, rearmed when cursor leaves it."""
    def __init__(self, dwell_ms: int = 150):
        self.dwell_ms = max(0, int(dwell_ms))
        self.candidate: OCRLine | None = None
        self.candidate_since_ms: float = 0
        self.last_spoken: OCRLine | None = None

    def reset(self) -> None:
        self.candidate = None
        self.candidate_since_ms = 0
        self.last_spoken = None

    def update(self, target: OCRLine | None, now_ms: float) -> OCRLine | None:
        if target != self.candidate:
            self.candidate = target
            self.candidate_since_ms = now_ms
            # Leaving a row (even briefly over a different row) rearms it.
            self.last_spoken = None
            return None
        if target is not None and target != self.last_spoken and now_ms - self.candidate_since_ms >= self.dwell_ms:
            self.last_spoken = target
            return target
        return None
