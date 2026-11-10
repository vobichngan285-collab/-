"""Lightweight offline ONNX Runtime driver for official PP-OCRv6 Small only.

Uses RapidOCR (PP-OCRv6 detection + recognition), without PaddlePaddle/PaddleX.
Only explicit, bundled file paths are allowed. No runtime model downloads.
"""
from __future__ import annotations
import math
import sys
import time
from pathlib import Path
import numpy as np
from .core import OCRLine

TIERS = {"small": ("PP-OCRv6_det_small.onnx", "PP-OCRv6_rec_small.onnx")}


def model_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "models"
    return Path(__file__).resolve().parents[1] / "models"


def rapid_result_lines(result, origin: tuple[int, int], minimum_score: float = 0.42) -> list[OCRLine]:
    """Keep original text, map each quadrilateral to physical screen coords."""
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
        left, top = int(math.floor(quad[:,0].min())) + x0, int(math.floor(quad[:,1].min())) + y0
        right, bottom = int(math.ceil(quad[:,0].max())) + x0, int(math.ceil(quad[:,1].max())) + y0
        if right <= left or bottom <= top:
            continue
        output.append(OCRLine(text, left, top, right, bottom, float(raw_score)))
    output.sort(key=lambda line: (line.top, line.left))
    return output


class LocalOCR:
    def __init__(self):
        self.loaded_tier = None
        self.engine = None
        self.last_preprocess_ms = 0
        self.last_engine_ms = 0

    def recognize(self, image, origin: tuple[int, int], tier: str) -> list[OCRLine]:
        if tier not in TIERS:
            raise ValueError("Unsupported OCR tier")
        if tier != self.loaded_tier:
            from rapidocr import RapidOCR, ModelType, EngineType, OCRVersion
            det, rec = (model_root() / name for name in TIERS[tier])
            for path in (det, rec):
                if not path.is_file() or path.stat().st_size < 100000:
                    raise FileNotFoundError(f"缺少或损坏的离线 OCR 文件：{path}")
            self.engine = RapidOCR(params={
                "Det.engine_type": EngineType.ONNXRUNTIME,
                "Rec.engine_type": EngineType.ONNXRUNTIME,
                "Det.ocr_version": OCRVersion.PPOCRV6,
                "Rec.ocr_version": OCRVersion.PPOCRV6,
                "Det.model_type": ModelType.SMALL,
                "Rec.model_type": ModelType.SMALL,
                "Det.model_path": str(det),
                "Rec.model_path": str(rec),
            })
            self.loaded_tier = tier
        t0 = time.monotonic()
        # ImageGrab/GDI already return RGB; avoid an unnecessary full-frame copy.
        pixels = np.asarray(image if image.mode == "RGB" else image.convert("RGB"))
        t1 = time.monotonic()
        result = self.engine(pixels, use_cls=False)
        self.last_preprocess_ms = round((t1 - t0) * 1000)
        self.last_engine_ms = round((time.monotonic() - t1) * 1000)
        return rapid_result_lines(result, origin)
