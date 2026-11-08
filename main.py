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
            started = __import__("time").perf_counter()
            lines, diagnostics = engine.recognize_timed(im, (0, 0), tier)
            elapsed_ms = round((__import__("time").perf_counter() - started) * 1000)
            report.append(f"{tier}: {len(lines)} rows, {elapsed_ms}ms, "
                          f"stages={diagnostics}, texts=" +
                          "|".join(line.text for line in lines))
            if not any("GAME" in line.text.upper() or "SETTINGS" in line.text.upper()
                       for line in lines):
                raise RuntimeError(f"{tier}: recognizer returned no expected text")
        # Second scene: Chinese text on a dark menu-like background.
        # Server 2025 may not install any CJK font; do not fabricate glyphs.
        font_candidates = [
            "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/simsun.ttc"
        ]
        installed_font = next((p for p in font_candidates
                              if Path(p).is_file()), None)
        if installed_font:
            report.append("Chinese synthetic font=" + installed_font)
            dark = Image.new("RGB", (1400, 460), (25, 28, 37))
            dark_draw = ImageDraw.Draw(dark)
            cn = ImageFont.truetype(installed_font, 92)
            dark_draw.text((100, 50), "继续游戏", fill=(250, 250, 245), font=cn)
            dark_draw.text((100, 260), "游戏设置", fill=(245, 235, 185), font=cn)
            for tier in ("small", "medium"):
                cn_lines, cn_timing = engine.recognize_timed(dark, (0, 0), tier)
                report.append(f"{tier} Chinese dark: {len(cn_lines)} rows, "
                              f"timings={cn_timing}, text=" +
                              "|".join(row.text for row in cn_lines))
                if not any(any("一" <= ch <= "鿿" for ch in row.text)
                           for row in cn_lines):
                    raise RuntimeError(f"{tier}: no Chinese characters on dark menu; "
                                       f"raw={cn_timing['raw_lines']}, lines={cn_lines}")
        else:
            report.append("CJK font missing from CI runner; skip Chinese visual probe")
        log_path.write_text("PASS\n" + "\n".join(report), encoding="utf-8")
        return 0
    except BaseException:
        log_path.write_text("FAIL\n" + "\n".join(locals().get("report", [])) + "\n" + traceback.format_exc(), encoding="utf-8")
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
        log.write_text("PASS\n" + "\n".join(v[1] for v in voices), encoding="utf-8")
        return 0
    except BaseException:
        log.write_text("FAIL\n" + traceback.format_exc(), encoding="utf-8")
        return 1




def packaged_ui_selftest() -> int:
    """Smoke-test accessible Tk and real four-window pointer frame."""
    import tempfile
    import traceback
    from pathlib import Path
    log = Path(tempfile.gettempdir()) / "GameTextReader_ui_selftest.txt"
    root = None
    overlay = None
    try:
        import tkinter as tk
        from tkinter import ttk
        import tk_uia
        from game_reader.overlay import ClickThroughOutline
        from game_reader.core import OCRLine
        root = tk.Tk()
        root.withdraw()
        control = ttk.Button(root, text="Accessibility test")
        control.pack()
        result = tk_uia.enable(root)
        tk_uia.set_acc_name(control, "OCR 功能按钮")
        root.update_idletasks()
        overlay = ClickThroughOutline()
        overlay.show(OCRLine("Game", 120, 100, 200, 125))
        if len(overlay.handles) != 4:
            raise RuntimeError("Expected four separate click-through border windows")
        overlay.hide()
        overlay.close()
        overlay = None
        log.write_text("PASS\n" + str(result), encoding="utf-8")
        return 0
    except BaseException:
        log.write_text("FAIL\n" + traceback.format_exc(), encoding="utf-8")
        return 1
    finally:
        if overlay:
            overlay.close()
        if root:
            root.destroy()




def packaged_app_selftest() -> int:
    """Run the ACTUAL V1.3 UI construction without requiring a game."""
    import tempfile
    import traceback
    from pathlib import Path
    log = Path(tempfile.gettempdir()) / "GameTextReader_app_selftest.txt"
    root = None
    try:
        import tkinter as tk
        from game_reader.app import ReaderApp
        root = tk.Tk()
        root.withdraw()
        app = ReaderApp(root)
        root.update_idletasks()
        if app.hover.dwell_ms != 0:
            raise RuntimeError("V1.3 must never keep the old hover delay")
        if app.overlay is None:
            raise RuntimeError("Native green outline initialization failed: " +
                               app.overlay_error)
        if "PROVIDED" not in app.accessibility_status and "ANNOTATED" not in app.accessibility_status:
            raise RuntimeError("Accessible widget provider failed: " +
                               app.accessibility_status)
        app.close()
        root = None
        log.write_text("PASS\nFull V1.3 window, accessibility and frame ready", encoding="utf-8")
        return 0
    except BaseException:
        log.write_text("FAIL\n" + traceback.format_exc(), encoding="utf-8")
        return 1
    finally:
        if root is not None:
            root.destroy()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    if "--self-test-ocr" in sys.argv:
        raise SystemExit(packaged_ocr_selftest())
    if "--self-test-tts" in sys.argv:
        raise SystemExit(packaged_tts_selftest())
    if "--self-test-ui" in sys.argv:
        raise SystemExit(packaged_ui_selftest())
    if "--self-test-app" in sys.argv:
        raise SystemExit(packaged_app_selftest())
    from game_reader.app import run
    run()
