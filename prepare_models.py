"""Prepare ONLY official PP-OCRv6 Small DET + Small REC on Windows CI.

Runtime OCR remains fully offline. Large Medium weights are deliberately excluded.
"""
from __future__ import annotations
from pathlib import Path
from shutil import copy2
from PIL import Image, ImageDraw, ImageFont
import rapidocr
from rapidocr import RapidOCR, ModelType, EngineType, OCRVersion

ROOT = Path(__file__).resolve().parent
DEST = ROOT / "models"
PACKAGE_MODELS = Path(rapidocr.__file__).resolve().parent / "models"
DEST.mkdir(exist_ok=True)

image = Image.new("RGB", (1400, 360), "white")
draw = ImageDraw.Draw(image)
font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 100)
draw.text((65, 45), "CONTINUE GAME", fill="black", font=font)
draw.text((65, 210), "SETTINGS", fill="black", font=font)

print("[models] Checking ONNX v6 Small DET+REC", flush=True)
engine = RapidOCR(params={
    "Det.engine_type": EngineType.ONNXRUNTIME,
    "Rec.engine_type": EngineType.ONNXRUNTIME,
    "Det.ocr_version": OCRVersion.PPOCRV6,
    "Rec.ocr_version": OCRVersion.PPOCRV6,
    "Det.model_type": ModelType.SMALL,
    "Det.limit_type": "max",
    "Det.limit_side_len": 1280,
    "Rec.model_type": ModelType.SMALL,
})
result = engine(image, use_cls=False)
found = list(result.txts or [])
print(f"[models] Small result: {found}", flush=True)
if not any("GAME" in t.upper() or "SETTINGS" in t.upper() for t in found):
    raise RuntimeError("Small recognizer unable to OCR clean test image")
del engine

for phase in ("det", "rec"):
    name = f"PP-OCRv6_{phase}_small.onnx"
    source = PACKAGE_MODELS / name
    if not source.is_file() or source.stat().st_size < 100000:
        raise FileNotFoundError(f"Missing official ONNX file: {source}")
    copy2(source, DEST / name)
    print(f"[models] bundled {name}: {(DEST / name).stat().st_size}", flush=True)
for name in ("PP-OCRv6_rec_medium.onnx", "PP-OCRv6_det_medium.onnx"):
    (DEST / name).unlink(missing_ok=True)

print("[models] Only two real Small model files ready", flush=True)
