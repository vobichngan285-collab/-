"""Windows CI: download OPTIONAL (not bundled) models, verify hashes, run real ONNX OCR."""
from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from game_reader import ocr_models
from game_reader.ocr_backend import LocalOCR


def main():
    image = Image.new("RGB", (1300, 310), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 92)
    draw.text((55, 60), "CONTINUE GAME", fill="black", font=font)
    with tempfile.TemporaryDirectory(prefix="BlueStarOptionalModelsCI_") as folder:
        ocr_models.MODEL_HOME = Path(folder)
        for tier in ("tiny", "v5_mobile"):
            print(f"DOWNLOAD {tier} from official RapidOCR catalog", flush=True)
            paths = ocr_models.install_optional_model(
                tier, progress=lambda message: print(message.encode("ascii", "backslashreplace").decode("ascii"), flush=True))
            assert all(path.is_file() for path in paths)
            assert ocr_models.model_installed(tier)
            print(f"RUN OCR {tier}", flush=True)
            reader = LocalOCR()
            regions = reader.recognize(image, (0, 0), tier)
            texts = [item.text for item in regions]
            print(f"OCR {tier} output {str(texts).encode('ascii', 'backslashreplace').decode('ascii')}", flush=True)
            if not texts:
                raise RuntimeError(f"{tier} produced zero real OCR results")
            assert reader.loaded_tier == tier
        print("PASS both optional model download + SHA256 + ONNX inference", flush=True)


if __name__ == "__main__":
    main()
