"""Entry point for the offline Windows game OCR reader."""
from __future__ import annotations
import multiprocessing
import sys


def packaged_ocr_selftest() -> int:
    """Run *the frozen executable* through both real OCR models, no Tk window."""
    import os
    import tempfile
    import traceback
    from pathlib import Path

    log_path = Path(tempfile.gettempdir()) / "GameTextReader_ocr_selftest.txt"
    try:
        from PIL import Image, ImageDraw, ImageFont
        from game_reader.ocr_backend import LocalOCR
        os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "1"
        im = Image.new("RGB", (1400, 440), "white")
        draw = ImageDraw.Draw(im)
        font_path = "C:/Windows/Fonts/arialbd.ttf"
        font = ImageFont.truetype(font_path, 100)
        draw.text((75, 55), "CONTINUE GAME", fill="black", font=font)
        draw.text((75, 245), "SETTINGS", fill="black", font=font)
        engine = LocalOCR()
        report = []
        for tier in ("small", "medium"):
            lines = engine.recognize(im, (0, 0), tier)
            report.append(f"{tier}: {len(lines)} rows, texts=" +
                          "|".join(line.text for line in lines))
            if not any("GAME" in line.text.upper() or "SETTINGS" in line.text.upper()
                       for line in lines):
                raise RuntimeError(f"{tier}: recognizer returned no expected text")
        log_path.write_text("PASS\n" + "\n".join(report), encoding="utf-8")
        return 0
    except BaseException:
        log_path.write_text("FAIL\n" + traceback.format_exc(), encoding="utf-8")
        return 1


def packaged_tts_selftest() -> int:
    """Check imported speech modules and installed voices without requiring audio."""
    import tempfile
    import traceback
    from pathlib import Path
    log = Path(tempfile.gettempdir()) / "GameTextReader_tts_selftest.txt"
    try:
        from game_reader.speech import enumerate_sapi_voices, SpeechWorker
        from winrt.windows.media.speechsynthesis import SpeechSynthesizer
        from winrt.windows.media.playback import MediaPlayer
        voices = enumerate_sapi_voices()
        # Not all signed Narrator-only voices are public; this tests the API.
        log.write_text("PASS\\n" + "\\n".join(v[1] for v in voices), encoding="utf-8")
        return 0
    except BaseException:
        log.write_text("FAIL\\n" + traceback.format_exc(), encoding="utf-8")
        return 1


if __name__ == "__main__":
    multiprocessing.freeze_support()
    if "--self-test-ocr" in sys.argv:
        raise SystemExit(packaged_ocr_selftest())
    if "--self-test-tts" in sys.argv:
        raise SystemExit(packaged_tts_selftest())
    from game_reader.app import run
    run()
