"""Install the author's OFFICIAL PP-OCRv6_small model pack, not a homemade OCR.
The model URL and info.json metadata are read from the exact upstream
LunaTranslator /Resource/ocr_models service consumed by local.py.
Fails CLOSED: absent, invalid, or mismatched official model prevents release.
No OCR processing code is implemented here.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import urllib.request
import zipfile

MANIFEST = "https://lunatranslator.org/Resource/ocr_models"
TARGET_MODEL = "PP-OCRv6_small"
MAX_ARCHIVE_BYTES = 100_000_000
MAX_UNPACKED_BYTES = 150_000_000


def request_bytes(url: str, size_limit: int) -> bytes:
    if not url.startswith("https://"):
        raise ValueError("Official model download must use HTTPS")
    req = urllib.request.Request(url, headers={"User-Agent": "LunaTranslator/v12.1.3.9"})
    with urllib.request.urlopen(req, timeout=75) as stream:
        buf = bytearray()
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            buf.extend(block)
            if len(buf) > size_limit:
                raise ValueError("Official model download unexpectedly large")
        return bytes(buf)


def choose_official_model(manifest: object) -> dict:
    if not isinstance(manifest, list):
        raise ValueError("Expected the original Luna model-list array")
    matches = [entry for entry in manifest
               if isinstance(entry, dict) and entry.get("name") == TARGET_MODEL]
    if len(matches) != 1:
        raise ValueError("Official PP-OCRv6_small is missing or ambiguous")
    selected = matches[0]
    if not isinstance(selected.get("link"), str):
        raise ValueError("Official PP-OCRv6_small has no URL")
    return selected


def install(root: Path, manifest_data=None, archive_data=None) -> dict:
    if manifest_data is None:
        manifest_data = json.loads(request_bytes(MANIFEST, 3_000_000))
    metadata = choose_official_model(manifest_data)
    data = archive_data if archive_data is not None else request_bytes(
        metadata["link"], MAX_ARCHIVE_BYTES)
    sha = hashlib.sha256(data).hexdigest()
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise ValueError("Official model pack is not a ZIP")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        filelist = [f for f in z.infolist() if not f.is_dir()]
        if sum(f.file_size for f in filelist) > MAX_UNPACKED_BYTES:
            raise ValueError("Unpacked OCR model exceeds size limit")
        wanted = {}
        for name in ("det.onnx", "rec.onnx", "dict.txt"):
            candidates = [f for f in filelist if Path(f.filename).name == name]
            if len(candidates) != 1:
                raise ValueError("Missing/duplicate original model component: " + name)
            wanted[name] = candidates[0]
        if not all(wanted[n].file_size > limit for n,limit in
                   (("det.onnx", 100_000), ("rec.onnx", 100_000), ("dict.txt", 1000))):
            raise ValueError("Original small model contains truncated components")
        dest = root / "cache" / "ocrmodel" / ("bluestar_official_" + sha[:12])
        dest.mkdir(parents=True, exist_ok=True)
        for name, info in wanted.items():
            with z.open(info) as src, (dest / name).open("wb") as target:
                while True:
                    block = src.read(1024*1024)
                    if not block:
                        break
                    target.write(block)
        # Exactly upstream localmodels.writeinfos() semantics:
        # preserve existing archive info + overwrite with official manifest.
        info = {}
        original_info = [f for f in filelist if Path(f.filename).name == "info.json"]
        if len(original_info) == 1:
            info = json.loads(z.read(original_info[0]).decode("utf-8-sig"))
        if not isinstance(info, dict):
            raise ValueError("Official model info is not an object")
        info.update(metadata)
        if info.get("name") != TARGET_MODEL:
            raise ValueError("Wrong original OCR model name")
        (dest / "info.json").write_text(json.dumps(info,ensure_ascii=False,indent=2),
                                       encoding="utf-8")
    print("VERIFIED original Luna model:",TARGET_MODEL,
          "zip sha256:",sha,"folder:",dest,flush=True)
    return {"model":TARGET_MODEL,"archive_sha256":sha,"folder":str(dest)}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: install_official_v6small.py <official_Luna_root>")
    install(Path(sys.argv[1]).resolve())
