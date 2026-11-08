"""PaddleOCR 3.7 locally-packaged Small / Medium models; no runtime downloads."""
from __future__ import annotations
import os
import sys
from pathlib import Path
import numpy as np
from .core import OCRLine, parse_paddle_result

TIERS = {
    "small": ("PP-OCRv6_small_det", "PP-OCRv6_small_rec"),
    "medium": ("PP-OCRv6_medium_det", "PP-OCRv6_medium_rec"),
}


def model_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "models"  # PyInstaller onedir _internal/models
    return Path(__file__).resolve().parents[1] / "models"


class LocalOCR:
    def __init__(self):
        self.loaded_tier = None
        self.engine = None

    def recognize(self, image, origin: tuple[int, int], tier: str) -> list[OCRLine]:
        if tier not in TIERS:
            raise ValueError("Unrecognized model tier")
        if tier != self.loaded_tier:
            det, rec = TIERS[tier]
            root = model_root()
            det_path, rec_path = root / det, root / rec
            for path in (det_path, rec_path):
                if not path.is_dir() or not any(path.iterdir()):
                    raise FileNotFoundError(f"缺少本地 OCR 模型：{path}. 请使用完整发布包安装。")
            os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "1"
            from paddleocr import PaddleOCR
            self.engine = PaddleOCR(
                text_detection_model_name=det,
                text_recognition_model_name=rec,
                text_detection_model_dir=str(det_path),
                text_recognition_model_dir=str(rec_path),
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                device="cpu",
            )
            self.loaded_tier = tier
        prediction = self.engine.predict(np.asarray(image.convert("RGB")))
        lines = []
        for item in prediction:
            lines.extend(parse_paddle_result(item, *origin))
        return lines
