"""Download official PaddleOCR v6 det+rec pairs at BUILD time, copy into app.

Run on a connected Windows build agent. Runtime is deliberately offline.
"""
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / '.paddlex_build_cache'
MODELS = ROOT / 'models'
os.environ['PADDLE_PDX_CACHE_HOME'] = str(CACHE)
os.environ.setdefault('PADDLE_PDX_MODEL_SOURCE', 'bos')

from paddleocr import PaddleOCR  # noqa E402
from PIL import Image, ImageDraw  # noqa E402

pairs = [
    ('PP-OCRv6_small_det', 'PP-OCRv6_small_rec'),
    ('PP-OCRv6_medium_det', 'PP-OCRv6_medium_rec'),
]

im = Image.new('RGB', (640, 180), 'white')
ImageDraw.Draw(im).text((40, 60), 'GAME MENU OCR TEST 1234', fill='black')
for det, rec in pairs:
    print(f'[model] Initialize {det}, {rec}', flush=True)
    pipeline = PaddleOCR(
        text_detection_model_name=det,
        text_recognition_model_name=rec,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        device='cpu',
    )
    result = list(pipeline.predict(__import__('numpy').asarray(im)))
    print('[model] Smoke prediction rows:', len(result), flush=True)
    del pipeline
    for name in (det, rec):
        target = MODELS / name
        choices = [CACHE / 'official_models' / name,
                   Path.home() / '.paddlex' / 'official_models' / name]
        existing = next((p for p in choices if p.is_dir()), None)
        if existing is None:
            raise FileNotFoundError(f'Model folder not present after download: {name}; checked {choices}')
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(existing, target)
        print('[model] Bundled', target, sum(f.stat().st_size for f in target.rglob('*') if f.is_file()), flush=True)
for det, rec in pairs:
    for name in (det, rec):
        p = MODELS / name
        if not (p / 'inference.yml').exists():
            raise RuntimeError(f'Model directory is incomplete: {p} (no inference.yml)')
print('[model] All four official model folders ready.', flush=True)
