"""Remove NON-OCR components from the installed original Luna runtime.

The upstream OCR source files, models, Qt GUI/region manager, CVUtils.dll,
NativeUtils.dll and OCR screenshot/timer logic are left byte-for-byte unchanged.
Deletion happens ONLY in the NEW staged experimental release directory.
The complete unmodified upstream GPL source stays in the release ZIP.

Unrelated providers (translation/dictionaries/TTS/remote OCR), game Hook,
Magpie, and the unused built-in v5 OCR model are excluded. Refuse build if
unexpected original folder structure or required OCR files are missing.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import sys

KEEP_PYTHON = {
    "translator": {"basetranslator.py", "__init__.py"},
    "tts": {"basettsclass.py", "__init__.py"},
    "cishu": {"cishubase.py", "__init__.py"},
    "ocrengines": {"baseocrclass.py", "local.py", "__init__.py"},
    "metadata": {"abstract.py", "__init__.py"},
    "transoptimi": {"__init__.py"},
}
CUT_DIRECTORIES = (
    "files/Magpie",
    "files/LunaHook",
    "files/ocrmodel",  # v5 fallback; v6 small is in cache/ocrmodel
)
CUT_EXECUTABLES = (
    "files/LunaSubprocess32.exe",
    "files/LunaSubprocess64.exe",
    # BlueStar's separately bundled LunaSubprocess64.exe for licensed
    # Microsoft natural voice is intentionally preserved.
)
CRITICAL = (
    "LunaTranslator.exe",
    "LunaTranslator/LunaTranslator.py",
    "LunaTranslator/textio/textsource/ocrtext.py",
    "LunaTranslator/ocrengines/local.py",
    "LunaTranslator/ocrengines/baseocrclass.py",
    "LunaTranslator/myutils/ocrutil.py",
    "LunaTranslator/gui/rangeselect.py",
    "LunaTranslator/textio/textoutput/bluestar.py",
    "files/DLL64/CVUtils.dll",
    "files/DLL64/NativeUtils.dll",
)
MODEL_REQUIRED = ("det.onnx", "rec.onnx", "dict.txt", "info.json")


def patch_non_ocr_startup_validation(root: Path) -> None:
    """Keep the author's OCR-DLL checks, omit checks for removed optional apps.

    Original main.py calls checkintegrity() unconditionally. It insists on
    Magpie.Core.exe, LunaHook*.dll and LunaSubProcess.exe even when disabled.
    The original GPL source is bundled separately, unchanged. This narrow
    compatibility adjustment changes only non-OCR startup requirements.
    """
    source = root / "LunaTranslator" / "myutils" / "config.py"
    code = source.read_text(encoding="utf-8-sig")
    function_at = code.index("def checkintegrity():")
    cut_start = code.index("    dllshared = [", function_at)
    cut_end = code.index("    collect = []", cut_start)
    section = code[cut_start:cut_end]
    for critical in ("LunaHost64.dll", "LunaHook64.dll",
                     "LunaSubProcess64.exe", "Magpie.Core.exe"):
        if critical not in section:
            raise RuntimeError("Official integrity check structure unexpectedly changed: "+critical)
    # All original DLL checks above, notably NativeUtils, CVUtils,
    # onnxruntime and DirectML, remain intact. No OCR source is changed.
    replacement = ("    # BlueStar OCR-only package: removed game Hook/Magpie/TTS apps.\n"
                   "    # Keep the original required OCR DLL checks above.\n")
    code = code[:cut_start] + replacement + code[cut_end:]
    source.write_text(code, encoding="utf-8")
    print("PASS: patched only ORIGINAL optional NON-OCR startup file check", flush=True)


def prune(root: Path) -> dict:
    root = root.resolve()
    if root.name != "LunaTranslator_x64":
        raise ValueError("Refusing to prune anything outside LunaTranslator_x64 staging folder")
    for name in CRITICAL:
        if not (root / name).is_file():
            raise FileNotFoundError("Required original OCR component missing: " + name)
    models = list((root / "cache" / "ocrmodel").glob("bluestar_official_*"))
    if len(models) != 1 or not all((models[0] / n).is_file() for n in MODEL_REQUIRED):
        raise RuntimeError("Do not prune before verifying original official v6_small model/dict")
    report = dict(files_removed=0, bytes_removed=0, features=[])
    def remove(path: Path, reason: str):
        if not path.exists():
            return
        if path.is_dir():
            files = [p for p in path.rglob("*") if p.is_file()]
            size = sum(p.stat().st_size for p in files)
            shutil.rmtree(path)
            count = len(files)
        else:
            size, count = path.stat().st_size, 1
            path.unlink()
        report["files_removed"] += count
        report["bytes_removed"] += size
        report["features"].append(reason + ":" + str(count))
    patch_non_ocr_startup_validation(root)
    report["features"].append("patched legacy startup check for disabled Magpie/Hook/TTS ONLY")
    for folder in CUT_DIRECTORIES:
        remove(root / folder, folder)
    for exe in CUT_EXECUTABLES:
        remove(root / exe, exe)
    for directory, keep in KEEP_PYTHON.items():
        folder = root / "LunaTranslator" / directory
        if not folder.is_dir():
            raise RuntimeError("Expected upstream package missing: " + directory)
        for path in list(folder.rglob("*.py")):
            if path.parent == folder and path.name in keep:
                continue
            remove(path, directory + " provider")
    # Avoid shipping two identical ZIPs. Full unmodified GPLv3 source
    # is retained at GameTextReader/UPSTREAM_LUNA_GPL_SOURCE_v12.1.3.9.zip.
    outer = root.parent.parent / "UPSTREAM_LUNA_GPL_SOURCE_v12.1.3.9.zip"
    embedded_duplicate = root.parent / "UPSTREAM_FULL_SOURCE_v12.1.3.9.zip"
    if not outer.is_file():
        raise RuntimeError("Refuse duplicate source removal unless outer GPL archive exists")
    remove(embedded_duplicate, "duplicate official GPL source")
    for name in CRITICAL:
        if not (root / name).is_file():
            raise AssertionError("Pruned required original OCR component: " + name)
    if not (root / "LunaTranslator/ocrengines/local.py").is_file():
        raise AssertionError("Pruned original OCR engine")
    print("OCR-ONLY TRIM OK:", report, flush=True)
    return report


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: prune_original_luna.py <staged LunaTranslator_x64>")
    prune(Path(sys.argv[1]))
