"""Lightweight RapidOCR with the unchanged bundled V6 Small default and optional models."""
from __future__ import annotations
import math
import sys
from pathlib import Path
import numpy as np
from .core import OCRLine
from .ocr_models import model_installed, model_paths

TIERS = {
    "small": ("PP-OCRv6_det_small.onnx", "PP-OCRv6_rec_small.onnx"),
    "tiny": ("PP-OCRv6_det_tiny.onnx", "PP-OCRv6_rec_tiny.onnx"),
    "v5_mobile": ("ch_PP-OCRv5_det_mobile.onnx", "ch_PP-OCRv5_rec_mobile.onnx"),
}


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

    def recognize(self, image, origin: tuple[int, int], tier: str) -> list[OCRLine]:
        if tier not in TIERS:
            raise ValueError("Unsupported OCR tier")
        if tier != self.loaded_tier:
            from rapidocr import (RapidOCR, ModelType, EngineType, OCRVersion,
                                  LangDet, LangRec)
            if tier == "small":
                det, rec = (model_root() / name for name in TIERS[tier])
            else:
                if not model_installed(tier):
                    raise FileNotFoundError("可选 OCR 模型未安装或校验失败，请在设置里重新下载")
                det, rec = model_paths(tier)
            for path in (det, rec):
                if not path.is_file() or path.stat().st_size < 100000:
                    raise FileNotFoundError(f"缺少或损坏的离线 OCR 文件：{path}")
            # Preserve all original settings for bundled V6 Small.
            params = {
                "Det.engine_type": EngineType.ONNXRUNTIME,
                "Rec.engine_type": EngineType.ONNXRUNTIME,
                "Det.ocr_version": OCRVersion.PPOCRV6,
                "Rec.ocr_version": OCRVersion.PPOCRV6,
                "Det.model_type": ModelType.SMALL,
                "Rec.model_type": ModelType.SMALL,
                "Det.model_path": str(det),
                "Rec.model_path": str(rec),
            }
            if tier != "small":
                version = OCRVersion.PPOCRV5 if tier == "v5_mobile" else OCRVersion.PPOCRV6
                size = ModelType.MOBILE if tier == "v5_mobile" else ModelType.TINY
                params.update({
                    "Det.ocr_version": version,
                    "Rec.ocr_version": version,
                    "Det.model_type": size,
                    "Rec.model_type": size,
                    "Det.lang_type": LangDet.CH,
                    "Rec.lang_type": LangRec.CH,
                })
            candidate = RapidOCR(params=params)
            self.engine = candidate
            self.loaded_tier = tier
        result = self.engine(np.asarray(image.convert("RGB")), use_cls=False)
        return rapid_result_lines(result, origin)
