"""Prepare official PP-OCRv6 Small DET + Small/Medium REC on Windows CI.

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

for tier in ("small", "medium"):
    print(f"[models] Checking ONNX v6 {tier}", flush=True)
    engine = RapidOCR(params={
        "Det.engine_type": EngineType.ONNXRUNTIME,
        "Rec.engine_type": EngineType.ONNXRUNTIME,
        "Det.ocr_version": OCRVersion.PPOCRV6,
        "Rec.ocr_version": OCRVersion.PPOCRV6,
        "Det.model_type": ModelType.SMALL,
        "Det.limit_type": "max",
        "Det.limit_side_len": 1280 if tier == "small" else 1152,
        "Rec.model_type": (ModelType.SMALL if tier == "small" else ModelType.MEDIUM),
    })
    result = engine(image, use_cls=False)
    found = list(result.txts or [])
    print(f"[models] {tier} result: {found}", flush=True)
    if not any("GAME" in t.upper() or "SETTINGS" in t.upper() for t in found):
        raise RuntimeError(f"{tier}: unable to OCR a clean test image")
    del engine
    # Both run modes use Small DET; only the recognizer changes.
    for phase in (("det", "rec") if tier == "small" else ("rec",)):
        name = f"PP-OCRv6_{phase}_{tier}.onnx"
        source = PACKAGE_MODELS / name
        if not source.is_file() or source.stat().st_size < 100000:
            raise FileNotFoundError(f"ONNX {name} not downloaded to {source}")
        copy2(source, DEST / name)
        print(f"[models] bundled {name}: {(DEST/name).stat().st_size}", flush=True)

print("[models] Three real PP-OCRv6 models ready (Small DET, Small REC, Medium REC)", flush=True)
