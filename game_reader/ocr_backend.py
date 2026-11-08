"""Offline PP-OCRv6 ONNX recognition with measurable cold-load and inference stages."""
from __future__ import annotations
import math
import sys
import threading
import time
from pathlib import Path

import numpy as np
from .core import OCRLine

TIERS = {
    tier: (f"PP-OCRv6_det_{tier}.onnx", f"PP-OCRv6_rec_{tier}.onnx")
    for tier in ("small", "medium")
}


def model_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "models"
    return Path(__file__).resolve().parents[1] / "models"


def rapid_result_lines(result, origin: tuple[int, int], minimum_score: float = 0.42) -> list[OCRLine]:
    boxes, texts, scores = result.boxes, result.txts, result.scores
    if boxes is None or texts is None:
        return []
    if len(boxes) != len(texts) or len(boxes) != len(scores):
        raise ValueError("RapidOCR quadrilaterals/text/score mismatch")
    x0, y0 = origin
    output = []
    for points, raw_text, raw_score in zip(boxes, texts, scores):
        text = str(raw_text).strip()
        if not text or float(raw_score) < minimum_score:
            continue
        quad = np.asarray(points, dtype=float)
        if quad.shape != (4, 2) or not np.isfinite(quad).all():
            continue
        left, top = int(math.floor(quad[:, 0].min())) + x0, int(math.floor(quad[:, 1].min())) + y0
        right, bottom = int(math.ceil(quad[:, 0].max())) + x0, int(math.ceil(quad[:, 1].max())) + y0
        if right <= left or bottom <= top:
            continue
        output.append(OCRLine(text, left, top, right, bottom, float(raw_score)))
    output.sort(key=lambda line: (line.top, line.left))
    return output


def _milliseconds(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)


class LocalOCR:
    """A single cached model pair: no duplicate medium/small memory residency.

    Preload the selected tier in a background thread before the first F8. Model
    switch replaces it; one lock keeps prewarm and recognition from racing.
    """
    def __init__(self):
        self.loaded_tier: str | None = None
        self.engine = None
        self._warmed = False
        self._lock = threading.RLock()

    def _load(self, tier: str) -> None:
        if tier not in TIERS:
            raise ValueError("Unsupported OCR tier")
        if self.engine is not None and self.loaded_tier == tier:
            return
        from rapidocr import RapidOCR, ModelType, EngineType, OCRVersion
        det, rec = (model_root() / name for name in TIERS[tier])
        for path in (det, rec):
            if not path.is_file() or path.stat().st_size < 100000:
                raise FileNotFoundError(f"缺少或损坏的离线 OCR 文件：{path}")
        engine = RapidOCR(params={
            "Det.engine_type": EngineType.ONNXRUNTIME,
            "Rec.engine_type": EngineType.ONNXRUNTIME,
            "Det.ocr_version": OCRVersion.PPOCRV6,
            "Rec.ocr_version": OCRVersion.PPOCRV6,
            "Det.model_type": (ModelType.SMALL if tier == "small" else ModelType.MEDIUM),
            "Rec.model_type": (ModelType.SMALL if tier == "small" else ModelType.MEDIUM),
            "Det.model_path": str(det),
            "Rec.model_path": str(rec),
        })
        self.engine = engine
        self.loaded_tier = tier
        self._warmed = False

    def prepare(self, tier: str) -> int:
        """Real inference required because RapidOCR 3.10 defers model loading."""
        started = time.perf_counter()
        with self._lock:
            self._load(tier)
            if not self._warmed:
                blank = np.full((128, 256, 3), 255, dtype=np.uint8)
                self.engine(blank, use_cls=False)
                self._warmed = True
        return _milliseconds(started)

    def recognize_timed(self, image, origin: tuple[int, int], tier: str):
        start = time.perf_counter()
        with self._lock:
            # A startup prewarm in progress is a genuine wait and is included
            # in the model stage. No second model initialization can overlap.
            self._load(tier)
            model_ms = _milliseconds(start)
            t0 = time.perf_counter()
            array = np.asarray(image.convert("RGB"))
            convert_ms = _milliseconds(t0)
            t1 = time.perf_counter()
            result = self.engine(array, use_cls=False)
            self._warmed = True
            inference_ms = _milliseconds(t1)
            t2 = time.perf_counter()
            lines = rapid_result_lines(result, origin)
            parse_ms = _milliseconds(t2)
        raw = getattr(result, "txts", None)
        result_detail = getattr(result, "elapse_list", None)
        return lines, {
            "tier": tier,
            "model_ms": model_ms,
            "convert_ms": convert_ms,
            "inference_ms": inference_ms,
            "parse_ms": parse_ms,
            "raw_lines": len(raw) if raw is not None else 0,
            "accepted_lines": len(lines),
            "engine_stages": str(result_detail) if result_detail is not None else "n/a",
        }

    def recognize(self, image, origin: tuple[int, int], tier: str) -> list[OCRLine]:
        return self.recognize_timed(image, origin, tier)[0]
