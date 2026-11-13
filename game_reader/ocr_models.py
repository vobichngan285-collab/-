"""Optional RapidOCR v3.10.0 ONNX model downloader.

Only the official version-pinned RapidAI/RapidOCR model catalog is used.
The bundled PP-OCRv6 Small remains untouched and fully offline.
Optional files are stored outside the frozen installation directory.
"""
from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import shutil
import tempfile
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

MODEL_HOME = (Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) /
              "GameTextReader" / "ocr_models")
CATALOG_BASE = ("https://www.modelscope.cn/models/RapidAI/RapidOCR/"
                "resolve/v3.10.0/onnx")
MAX_MODEL_BYTES = 100 * 1024 * 1024
MODEL_LABELS = {
    "small": "PP-OCRv6 Small（内置默认）",
    "tiny": "PP-OCRv6 Tiny（超轻量）",
    "v5_mobile": "PP-OCRv5 Mobile（上一代轻量）",
}
# File names and SHA-256 are copied from RapidAI/RapidOCR v3.10.0
# python/rapidocr/default_models.yaml. Download detection and recognition
# AS A PAIR; mixing variants can produce incorrect Chinese recognition.
OPTIONAL_FILES = {
    "tiny": (
        ("PP-OCRv6_det_tiny.onnx", CATALOG_BASE + "/PP-OCRv6/det/PP-OCRv6_det_tiny.onnx",
         "f42c0fbd294d95eac1a550e131b277dac97462c8025fa4b6c3cec1b7894bd3d5"),
        ("PP-OCRv6_rec_tiny.onnx", CATALOG_BASE + "/PP-OCRv6/rec/PP-OCRv6_rec_tiny.onnx",
         "e16e242de5937ad92609223f19bc2aff3727ee40b095f996907c24749bad251b"),
    ),
    "v5_mobile": (
        ("ch_PP-OCRv5_det_mobile.onnx", CATALOG_BASE + "/PP-OCRv5/det/ch_PP-OCRv5_det_mobile.onnx",
         "4d97c44a20d30a81aad087d6a396b08f786c4635742afc391f6621f5c6ae78ae"),
        ("ch_PP-OCRv5_rec_mobile.onnx", CATALOG_BASE + "/PP-OCRv5/rec/ch_PP-OCRv5_rec_mobile.onnx",
         "5825fc7ebf84ae7a412be049820b4d86d77620f204a041697b0494669b1742c5"),
    ),
}


def model_paths(tier: str, root: Path | None = None) -> tuple[Path, Path]:
    if tier not in OPTIONAL_FILES:
        raise ValueError("不是可下载的 OCR 模型")
    home = Path(root) if root is not None else MODEL_HOME
    return tuple(home / tier / name for name, _url, _hash in OPTIONAL_FILES[tier])


def _valid_file(path: Path, expected_sha: str) -> bool:
    try:
        if not path.is_file() or not 100_000 <= path.stat().st_size <= MAX_MODEL_BYTES:
            return False
        digest = sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(256 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest() == expected_sha
    except OSError:
        return False


def model_installed(tier: str, root: Path | None = None) -> bool:
    if tier == "small":
        return True  # The existing default model is bundled with the EXE.
    if tier not in OPTIONAL_FILES:
        return False
    return all(_valid_file(path, sha) for path, (_name, _url, sha)
               in zip(model_paths(tier, root), OPTIONAL_FILES[tier]))


def install_optional_model(tier: str, progress=None, root: Path | None = None) -> tuple[Path, Path]:
    """Stream the two verified ONNX files to a temporary directory then install.

    Downloads never overwrite the packaged default or change the active model.
    On failure, no half-downloaded model can be selected.
    """
    if tier not in OPTIONAL_FILES:
        raise ValueError("不支持下载此 OCR 模型")
    home = Path(root) if root is not None else MODEL_HOME
    if model_installed(tier, home):
        return model_paths(tier, home)
    home.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".ocr_pending_", dir=home))
    try:
        for index, (filename, url, expected_sha) in enumerate(OPTIONAL_FILES[tier], 1):
            if urlsplit(url).scheme != "https":
                raise RuntimeError("模型下载地址必须使用 HTTPS")
            if progress:
                progress(f"下载 {MODEL_LABELS[tier]}：文件 {index}/2")
            request = Request(url, headers={"User-Agent": "BlueStarOCR/2.0"})
            digest = sha256()
            total = 0
            with urlopen(request, timeout=45) as response:
                if urlsplit(response.geturl()).scheme != "https":
                    raise RuntimeError("模型下载跳转未使用 HTTPS")
                with (staging / filename).open("wb") as output:
                    while True:
                        block = response.read(256 * 1024)
                        if not block:
                            break
                        total += len(block)
                        if total > MAX_MODEL_BYTES:
                            raise RuntimeError("下载的模型超过安全大小限制")
                        digest.update(block)
                        output.write(block)
                        if progress:
                            progress(f"下载 {MODEL_LABELS[tier]} {index}/2：{total / (1024 * 1024):.1f} MB")
            if total < 100_000 or digest.hexdigest() != expected_sha:
                raise RuntimeError(f"{filename} 文件校验失败，请重试下载")
        destination = home / tier
        # Reinstall only a damaged optional directory, never the bundled Small.
        if destination.exists():
            if model_installed(tier, home):
                return model_paths(tier, home)
            shutil.rmtree(destination)
        os.replace(staging, destination)
        staging = None
        if not model_installed(tier, home):
            raise RuntimeError("模型文件写入后校验失败")
        return model_paths(tier, home)
    finally:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)
