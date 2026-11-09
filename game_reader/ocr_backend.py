"""Offline PP-OCRv6 hybrid OCR with latency-limited Small detection and per-tier recognition."""
from __future__ import annotations
import math
import sys
import threading
import time
from pathlib import Path

import numpy as np
from .core import OCRLine

# V1.4: The old full Medium detector caused multi-second F8 stalls.
# Use the proven Small detector for BOTH tiers, then Medium recognition only
# for the accuracy-oriented tier. This is a deliberate hybrid, not a full
# Medium detector disguised under the old label.
TIERS = {
    "small": ("PP-OCRv6_det_small.onnx", "PP-OCRv6_rec_small.onnx"),
    "medium": ("PP-OCRv6_det_small.onnx", "PP-OCRv6_rec_medium.onnx"),
}
DET_LONG_SIDE = {"small": 1280, "medium": 1152}



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
    def __init__(self, medium_rec_batch_num: int = 2,
                 medium_ort_threads: int | None = 2):
        # Only Medium REC batching is experimental. Small retains RapidOCR
        # defaults for a stable baseline and rapid F8 response.
        if not 1 <= medium_rec_batch_num <= 6:
            raise ValueError("Medium REC batch size must be between 1 and 6")
        self.medium_rec_batch_num = medium_rec_batch_num
        if medium_ort_threads not in (None, 1, 2, 4, 8):
            raise ValueError("Unsupported Medium ONNX CPU thread profile")
        self.medium_ort_threads = medium_ort_threads
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
        params = {
            "Det.engine_type": EngineType.ONNXRUNTIME,
            "Rec.engine_type": EngineType.ONNXRUNTIME,
            "Det.ocr_version": OCRVersion.PPOCRV6,
            "Rec.ocr_version": OCRVersion.PPOCRV6,
            "Det.model_type": ModelType.SMALL,
            # Avoid upscale-by-short-edge ('min') of a wide game screenshot:
            # cap the detector's LONGEST side at this tier's pixel budget.
            # RapidOCR maps detected boxes back to input image coordinates.
            "Det.limit_type": "max",
            "Det.limit_side_len": DET_LONG_SIDE[tier],
            "Rec.model_type": (ModelType.SMALL if tier == "small" else ModelType.MEDIUM),
            "Det.model_path": str(det),
            "Rec.model_path": str(rec),
        }
        if tier == "medium":
            params["Rec.rec_batch_num"] = self.medium_rec_batch_num
            if self.medium_ort_threads is not None:
                # Trial-only setting; leaves the Small OCR session unchanged.
                params["EngineConfig.onnxruntime.intra_op_num_threads"] = self.medium_ort_threads
        engine = RapidOCR(params=params)
        self.engine = engine
        self.loaded_tier = tier
        self._warmed = False

    def prepare(self, tier: str, still_current=None) -> int | None:
        """Warm selected tier only; abandon outdated queued warmup tasks.

        Callback is checked before and after acquiring the OCR lock. A warmup
        already running in ONNX cannot be interrupted safely.
        """
        started = time.perf_counter()
        if still_current is not None and not still_current():
            return None
        with self._lock:
            if still_current is not None and not still_current():
                return None
            self._load(tier)
            if still_current is not None and not still_current():
                return None
            if not self._warmed:
                # RapidOCR 3.10 lazily loads recognition ONLY when it sees
                # real text. A blank frame would warm DET but not REC.
                from PIL import Image, ImageDraw, ImageFont
                sample = Image.new("RGB", (580, 180), "white")
                draw = ImageDraw.Draw(sample)
                try:
                    font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 54)
                except OSError:
                    font = ImageFont.load_default()
                draw.text((30, 45), "CONTINUE GAME", fill="black", font=font)
                self.engine(np.asarray(sample), use_cls=False)
                self._warmed = True
        return _milliseconds(started)

    def recognize_timed(self, image, origin: tuple[int, int], tier: str):
        start = time.perf_counter()
        with self._lock:
            # Separate waiting behind background prewarm from model loading.
            # Keep model_ms stable for the existing UI/log consumers.
            model_lock_wait_ms = _milliseconds(start)
            load_started = time.perf_counter()
            self._load(tier)
            model_load_ms = _milliseconds(load_started)
            model_ms = _milliseconds(start)
            t0 = time.perf_counter()
            array = np.asarray(image if image.mode == "RGB" else image.convert("RGB"))
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
            "model_lock_wait_ms": model_lock_wait_ms,
            "model_load_ms": model_load_ms,
            "rec_batch_num": self.medium_rec_batch_num if tier == "medium" else 6,
            "medium_ort_threads": self.medium_ort_threads if tier == "medium" else None,
            "convert_ms": convert_ms,
            "inference_ms": inference_ms,
            "parse_ms": parse_ms,
            "raw_lines": len(raw) if raw is not None else 0,
            "accepted_lines": len(lines),
            "engine_stages": str(result_detail) if result_detail is not None else "n/a",
            "detector": "PP-OCRv6 Small",
            "recognizer": f"PP-OCRv6 {tier.capitalize()}",
            "det_max_side": DET_LONG_SIDE[tier],
        }

    def recognize(self, image, origin: tuple[int, int], tier: str) -> list[OCRLine]:
        return self.recognize_timed(image, origin, tier)[0]
