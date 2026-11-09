"""Entry point for the offline Windows game OCR reader."""
from __future__ import annotations
import multiprocessing
import sys


def packaged_ocr_selftest() -> int:
    """Run *the frozen executable* through the original V1.2 Small OCR model, no Tk window."""
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
        for tier in ("small",):
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




def packaged_picker_selftest() -> int:
    """Exercise the actual frozen Tk overlay three times, including cancellation.

    Hosted source Python sometimes lacks Tcl auto.tcl, so it is important
    this test runs with the very DLL/Tcl runtime shipped in the downloadable EXE.
    """
    import tempfile
    import traceback
    import time
    import tkinter as tk
    from pathlib import Path
    from types import SimpleNamespace
    from game_reader.app import ReaderApp

    log = Path(tempfile.gettempdir()) / "GameTextReader_picker_selftest.txt"
    root = None
    try:
        root = tk.Tk()
        root.geometry("500x350")
        root.update()
        app = ReaderApp.__new__(ReaderApp)
        app.root = root
        app.closed = False
        app.setting_hotkey = False
        app._choosing_region = False
        app._region_picker = None
        app._region_previous_root_state = "normal"
        app._hover_last_text = ""
        app._hover_spoken_cursor = None
        app.settings = {"region": [-300, -140, 600, 400], "period_ms": 500}
        app.region_info_var = tk.StringVar(master=root, value="old")
        app.persist = lambda: None
        app.status = lambda text: None
        for step in range(3):
            app.select_region()
            for _ in range(5):
                time.sleep(0.02)
                root.update()
            picker = app._region_picker
            if picker is None or not picker.winfo_exists() or not picker.winfo_viewable():
                raise RuntimeError(f"Picker #{step+1} did not map/appear")
            if step == 1:
                picker._start_drag(SimpleNamespace(x=120, y=120))
                picker._finish_drag(SimpleNamespace(x=490, y=350))
            else:
                picker.cancel()
            root.update()
            if app._choosing_region or app._region_picker is not None:
                raise RuntimeError("Picker did not release active status for next attempt")
            if abs(float(root.attributes("-alpha")) - 1.0) > 0.01:
                raise RuntimeError("Main window opacity did not recover")
        log.write_text("PASS\\nRepeated picker open/cancel/drag + state restoration",
                       encoding="utf-8")
        return 0
    except BaseException:
        log.write_text("FAIL\\n" + traceback.format_exc(), encoding="utf-8")
        return 1
    finally:
        if root is not None:
            root.destroy()


def packaged_app_selftest() -> int:
    """Run the ACTUAL V1.2 UI construction without requiring a game."""
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
            raise RuntimeError("V1.2 must never keep the old hover delay")
        if app.overlay is None:
            raise RuntimeError("Native green outline initialization failed: " +
                               app.overlay_error)
        if "PROVIDED" not in app.accessibility_status and "ANNOTATED" not in app.accessibility_status:
            raise RuntimeError("Accessible widget provider failed: " +
                               app.accessibility_status)
        app.close()
        root = None
        log.write_text("PASS\nFull V1.2 window, accessibility and frame ready", encoding="utf-8")
        return 0
    except BaseException:
        log.write_text("FAIL\n" + traceback.format_exc(), encoding="utf-8")
        return 1
    finally:
        if root is not None:
            root.destroy()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    if "--luna-worker" in sys.argv:
        from game_reader.luna_voice_worker import main as luna_worker
        raise SystemExit(luna_worker())
    if "--self-test-ocr" in sys.argv:
        raise SystemExit(packaged_ocr_selftest())
    if "--self-test-tts" in sys.argv:
        raise SystemExit(packaged_tts_selftest())
    if "--self-test-ui" in sys.argv:
        raise SystemExit(packaged_ui_selftest())
    if "--self-test-picker" in sys.argv:
        raise SystemExit(packaged_picker_selftest())
    if "--self-test-app" in sys.argv:
        raise SystemExit(packaged_app_selftest())
    from game_reader.app import run
    run()
