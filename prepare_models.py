"""Prepare only the original V1.2 default Small PP-OCRv6 models with RapidOCR ONNX on the Windows CI runner.

Weights are downloaded only on CI and copied to models/. Runtime paths are
strictly local, and the distributed application must work without networking.
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

for tier in ("small",):
    print(f"[models] Checking ONNX v6 {tier}", flush=True)
    engine = RapidOCR(params={
        "Det.engine_type": EngineType.ONNXRUNTIME,
        "Rec.engine_type": EngineType.ONNXRUNTIME,
        "Det.ocr_version": OCRVersion.PPOCRV6,
        "Rec.ocr_version": OCRVersion.PPOCRV6,
        "Det.model_type": ModelType.SMALL,
        "Rec.model_type": ModelType.SMALL,
    })
    result = engine(image, use_cls=False)
    found = list(result.txts or [])
    print(f"[models] {tier} result: {found}", flush=True)
    if not any("GAME" in t.upper() or "SETTINGS" in t.upper() for t in found):
        raise RuntimeError(f"{tier}: unable to OCR a clean test image")
    del engine
    for phase in ("det", "rec"):
        name = f"PP-OCRv6_{phase}_{tier}.onnx"
        source = PACKAGE_MODELS / name
        if not source.is_file() or source.stat().st_size < 100000:
            raise FileNotFoundError(f"ONNX {name} not downloaded to {source}")
        copy2(source, DEST / name)
        print(f"[models] bundled {name}: {(DEST/name).stat().st_size}", flush=True)

for unused in ("PP-OCRv6_det_medium.onnx", "PP-OCRv6_rec_medium.onnx"):
    (DEST / unused).unlink(missing_ok=True)
print("[models] ONLY V1.2 Small DET+REC models ready", flush=True)
