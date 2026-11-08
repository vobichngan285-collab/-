"""Minimal Windows 11 game screenshot -> OCR-coordinate -> local SAPI mouse reader.

No overlays, network calls, game injection, global keyboard hooks, or game mods.
Game input is never intercepted; if a chosen hotkey is used by the game, change it.
"""
from __future__ import annotations
import json
import os
import sys
import threading
import time
import traceback
import tkinter as tk
from pathlib import Path
from queue import Empty, Queue
from tkinter import ttk, messagebox

from .core import HoverTracker, OCRLine, hit_test
from .ocr_backend import LocalOCR
from .win_screen import enable_dpi_awareness, get_cursor, is_key_down, grab_current_monitor
from .speech import SpeechWorker, enumerate_sapi_voices

APP_NAME = "游戏文字助手"
CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "GameTextReader"
CONFIG_PATH = CONFIG_DIR / "settings.json"
ERROR_LOG = CONFIG_DIR / "last_ocr_error.txt"
DEFAULTS = {"vk": 0x77, "hotkey_label": "F8", "tier": "small", "voice": "",
            "rate": 0, "volume": 100, "dwell_ms": 150}
MODIFIER_KEYS = {16, 17, 18, 91, 92}


def read_settings() -> dict:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError()
        settings = DEFAULTS | {key: data[key] for key in DEFAULTS if key in data}
        settings["vk"] = int(settings["vk"])
        if not 1 <= settings["vk"] <= 254 or settings["vk"] in MODIFIER_KEYS:
            raise ValueError()
        if settings["tier"] not in ("small", "medium"):
            settings["tier"] = "small"
        return settings
    except (OSError, ValueError, TypeError):
        return dict(DEFAULTS)


def write_settings(settings: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, CONFIG_PATH)


class ReaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("游戏文字助手 V1.0 · 离线")
        self.root.geometry("580x620")
        self.root.minsize(500, 510)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.settings = read_settings()
        self.events: Queue[tuple] = Queue()
        self.last_ocr_error = ""
        self.lines: list[OCRLine] = []
        self.ocr_worker = LocalOCR()
        self.busy = False
        self.key_previous = False
        self.setting_hotkey = False
        self.hover = HoverTracker(self.settings["dwell_ms"])
        self.speech = SpeechWorker(on_error=lambda msg: self.events.put(("tts_error", msg)))
        self.speech.set_rate(self.settings["rate"])
        self.speech.set_volume(self.settings["volume"])
        self.voices: list[tuple[str, str]] = []
        self.voice_names: list[str] = []
        self.create_widgets()
        self.scan_voices()
        self.root.after(50, self.poll_messages)
        self.root.after(40, self.poll_input)

    def create_widgets(self):
        root = self.root
        p = ttk.Frame(root, padding=14)
        p.pack(fill="both", expand=True)
        title = ttk.Label(p, text="游戏文字助手", font=("Microsoft YaHei UI", 17, "bold"))
        title.pack(anchor="w")
        ttk.Label(p, text="按快捷键截取当前屏幕；鼠标指向哪行文字，就朗读哪行。",
                  wraplength=540).pack(anchor="w", pady=(3, 12))
        keys = ttk.LabelFrame(p, text="截图快捷键（支持单键）", padding=10)
        keys.pack(fill="x", pady=4)
        self.key_button = ttk.Button(keys, text=self.settings["hotkey_label"], command=self.capture_hotkey)
        self.key_button.pack(side="left")
        ttk.Label(keys, text="点击左侧按钮后，直接按想设置的单个键；Esc 取消。", wraplength=420).pack(side="left", padx=10)
        self.tier_var = tk.StringVar(value=self.settings["tier"])
        models = ttk.LabelFrame(p, text="本地 OCR 模型", padding=10)
        models.pack(fill="x", pady=4)
        ttk.Radiobutton(models, text="PP-OCRv6 Small · 速度优先", variable=self.tier_var,
                        value="small", command=self.change_model).pack(anchor="w")
        ttk.Radiobutton(models, text="PP-OCRv6 Medium · 识别优先", variable=self.tier_var,
                        value="medium", command=self.change_model).pack(anchor="w")
        voice_frame = ttk.LabelFrame(p, text="Windows 本地 TTS", padding=10)
        voice_frame.pack(fill="x", pady=4)
        self.voice_var = tk.StringVar(value="正在读取本地语音...")
        self.voice_select = ttk.Combobox(voice_frame, textvariable=self.voice_var,
                                         state="readonly", width=56)
        self.voice_select.pack(fill="x")
        self.voice_select.bind("<<ComboboxSelected>>", self.change_voice)
        vr = ttk.Frame(voice_frame)
        vr.pack(fill="x", pady=(6, 0))
        ttk.Button(vr, text="重新扫描语音", command=self.scan_voices).pack(side="left")
        ttk.Button(vr, text="试听", command=self.test_voice).pack(side="left", padx=8)
        ttk.Button(vr, text="停止朗读", command=self.speech.stop).pack(side="left")
        rate_frame = ttk.Frame(voice_frame)
        rate_frame.pack(fill="x", pady=(8, 0))
        ttk.Label(rate_frame, text="语速").pack(side="left")
        self.rate_var = tk.IntVar(value=self.settings["rate"])
        ttk.Scale(rate_frame, from_=-8, to=8, variable=self.rate_var,
                  command=self.change_rate).pack(side="left", fill="x", expand=True, padx=10)
        self.rate_label = ttk.Label(rate_frame, text=str(self.rate_var.get()), width=4)
        self.rate_label.pack(side="left")
        volume_frame = ttk.Frame(voice_frame)
        volume_frame.pack(fill="x", pady=(8, 0))
        ttk.Label(volume_frame, text="音量").pack(side="left")
        self.volume_var = tk.IntVar(value=self.settings["volume"])
        ttk.Scale(volume_frame, from_=0, to=100, variable=self.volume_var,
                  command=self.change_volume).pack(side="left", fill="x", expand=True, padx=10)
        self.volume_label = ttk.Label(volume_frame, text=f'{self.settings["volume"]}%', width=5)
        self.volume_label.pack(side="left")
        dwell_frame = ttk.Frame(voice_frame)
        dwell_frame.pack(fill="x", pady=(8, 0))
        ttk.Label(dwell_frame, text="鼠标停留").pack(side="left")
        self.dwell_var = tk.IntVar(value=self.settings["dwell_ms"])
        ttk.Scale(dwell_frame, from_=50, to=400, variable=self.dwell_var,
                  command=self.change_dwell).pack(side="left", fill="x", expand=True, padx=10)
        self.dwell_label = ttk.Label(dwell_frame, text=f'{self.settings["dwell_ms"]}ms', width=7)
        self.dwell_label.pack(side="left")
        actions = ttk.Frame(p)
        actions.pack(fill="x", pady=(10, 6))
        self.read_btn = ttk.Button(actions, text="立即截屏识别", command=self.capture_from_button)
        self.read_btn.pack(side="left")
        ttk.Button(actions, text="复制失败诊断", command=self.copy_error).pack(side="left", padx=(7, 0))
        ttk.Button(actions, text="最小化到任务栏", command=self.root.iconify).pack(side="left", padx=7)
        ttk.Button(actions, text="清除识别结果", command=self.clear).pack(side="left")
        self.status_var = tk.StringVar(value="就绪。建议先最小化窗口，再打开游戏菜单并按截图快捷键。")
        ttk.Label(p, textvariable=self.status_var, wraplength=530).pack(anchor="w", pady=(2, 6))
        viewer = ttk.LabelFrame(p, text="本次识别的文字（仅保存在内存，不上传）", padding=7)
        viewer.pack(fill="both", expand=True)
        self.output = tk.Text(viewer, wrap="word", height=8, state="disabled",
                              font=("Microsoft YaHei UI", 10))
        scroll = ttk.Scrollbar(viewer, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=scroll.set)
        self.output.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        ttk.Label(p, text="提示：切换菜单后再次按快捷键刷新；没有联网、后台连续 OCR 或读取游戏内存。",
                  wraplength=545).pack(anchor="w", pady=(6, 0))

    def status(self, value: str):
        self.status_var.set(value)

    def update_output(self, value: str):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("end", value)
        self.output.configure(state="disabled")

    def persist(self):
        try:
            write_settings(self.settings)
        except Exception as exc:
            self.status(f"保存设置失败：{exc}")

    def capture_hotkey(self):
        self.setting_hotkey = True
        self.key_button.configure(text="请按单键...")
        self.root.bind("<KeyPress>", self.accept_key)
        self.root.focus_force()

    def accept_key(self, event):
        if event.keysym == "Escape":
            self.setting_hotkey = False
            self.root.unbind("<KeyPress>")
            self.key_button.configure(text=self.settings["hotkey_label"])
            return
        vk = int(event.keycode)
        if vk in MODIFIER_KEYS or not 1 <= vk <= 254:
            self.status("请使用字母、数字、F 功能键或小键盘等单键，不支持单独 Ctrl/Alt/Shift。")
            return
        self.settings["vk"] = vk
        self.settings["hotkey_label"] = event.keysym
        self.setting_hotkey = False
        self.key_previous = True  # held capture key doesn't trigger immediately
        self.key_button.configure(text=event.keysym)
        self.root.unbind("<KeyPress>")
        self.persist()
        self.status(f"已设置截图快捷键：{event.keysym}。若与游戏按键冲突，可再次修改。")

    def change_model(self):
        self.settings["tier"] = self.tier_var.get()
        self.persist()

    def scan_voices(self):
        self.voice_select.configure(state="disabled")
        self.voice_var.set("正在扫描 Windows 本地语音...")
        def work():
            try:
                self.events.put(("voices", enumerate_sapi_voices()))
            except Exception as ex:
                self.events.put(("tts_error", str(ex)))
        threading.Thread(target=work, daemon=True).start()

    def change_voice(self, _event=None):
        idx = self.voice_select.current()
        if 0 <= idx < len(self.voices):
            self.settings["voice"] = self.voices[idx][0]
            self.speech.set_voice(self.settings["voice"])
            self.persist()

    def test_voice(self):
        self.speech.speak("你好，这是游戏文字助手本地语音试听。")

    def change_rate(self, _value):
        value = int(round(float(self.rate_var.get())))
        self.rate_label.configure(text=str(value))
        if self.settings["rate"] != value:
            self.settings["rate"] = value
            self.speech.set_rate(value)
            self.persist()

    def change_volume(self, _value):
        value = max(0, min(100, int(round(float(self.volume_var.get())))))
        self.volume_label.configure(text=f"{value}%")
        if self.settings["volume"] != value:
            self.settings["volume"] = value
            self.speech.set_volume(value)
            self.persist()

    def change_dwell(self, _value):
        value = max(50, int(round(float(self.dwell_var.get()) / 25) * 25))
        self.dwell_label.configure(text=f"{value}ms")
        self.hover.dwell_ms = value
        if self.settings["dwell_ms"] != value:
            self.settings["dwell_ms"] = value
            self.persist()

    def clear(self):
        self.lines = []
        self.hover.reset()
        self.speech.stop()
        self.update_output("")
        self.status("已清除当前截图识别结果。")

    def copy_error(self):
        if not self.last_ocr_error:
            self.status("当前没有可以复制的 OCR 失败诊断。")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.last_ocr_error)
        self.root.update_idletasks()
        self.status("错误诊断已复制，可直接粘贴给开发人员；不含截图或识别文字。")

    def capture_from_button(self):
        # Hide our own settings window before the capture, so it is not OCR'd.
        self.root.iconify()
        self.root.after(300, self.capture)

    def capture(self):
        if self.busy:
            return
        self.clear()
        self.busy = True
        self.read_btn.configure(state="disabled")
        self.status("正在截取当前屏幕并离线识别，稍后即可移动鼠标朗读...")
        tier = self.settings["tier"]
        def work():
            started = time.monotonic()
            phase = "Windows屏幕截图"
            try:
                image, origin = grab_current_monitor()
                phase = f"本地PaddleOCR加载或推理 ({tier})"
                lines = self.ocr_worker.recognize(image, origin, tier)
                self.events.put(("ocr_ok", lines, int((time.monotonic() - started) * 1000)))
            except Exception as exc:
                detail = ("phase: " + phase + "\n" +
                          "error: " + type(exc).__name__ + ": " + str(exc) + "\n" +
                          traceback.format_exc())
                self.events.put(("ocr_fail", detail))
        threading.Thread(target=work, daemon=True, name="LocalPaddleOCR").start()

    def poll_messages(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "ocr_ok":
                    _, lines, ms = event
                    self.busy = False
                    self.read_btn.configure(state="normal")
                    self.lines = lines
                    self.hover.reset()
                    self.update_output("\n".join(
                        f"{i+1:03d}  {line.text}    [{line.left},{line.top}]-[{line.right},{line.bottom}]"
                        for i, line in enumerate(lines)))
                    self.status(f"识别完成：{len(lines)} 行，{ms} 毫秒。鼠标指向文字即可朗读；菜单变化请再截图。")
                    if not lines:
                        self.speech.speak("未识别到清晰文字。")
                    else:
                        self.speech.speak(f"识别完成，共{len(lines)}行。")
                elif event[0] == "ocr_fail":
                    self.busy = False
                    self.read_btn.configure(state="normal")
                    self.last_ocr_error = event[1]
                    try:
                        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                        ERROR_LOG.write_text(self.last_ocr_error[-25000:], encoding="utf-8")
                    except OSError:
                        pass
                    self.status("识别失败。点击“复制失败诊断”获取具体错误；不会保存截图或文字。")
                    self.update_output(self.last_ocr_error.splitlines()[0] + "\n" +
                                       self.last_ocr_error.splitlines()[1])
                    self.speech.speak("识别失败。")
                elif event[0] == "voices":
                    self.voices = event[1]
                    names = [name for _, name in self.voices]
                    self.voice_select.configure(values=names, state="readonly" if names else "disabled")
                    if self.voices:
                        idx = next((i for i, (id_, _) in enumerate(self.voices)
                                    if id_ == self.settings["voice"]), 0)
                        self.voice_select.current(idx)
                        self.speech.set_voice(self.voices[idx][0])
                    else:
                        self.voice_var.set("未找到可调用的 SAPI 本地语音")
                        self.status("没有检测到本地 SAPI 语音，请检查 Windows 语音包。")
                elif event[0] == "tts_error":
                    self.status("本地语音接口异常：" + event[1])
        except Empty:
            pass
        self.root.after(60, self.poll_messages)

    def poll_input(self):
        try:
            down = is_key_down(self.settings["vk"])
            if not self.setting_hotkey and down and not self.key_previous:
                if self.root.state() == "normal":
                    self.capture_from_button()
                else:
                    self.capture()
            self.key_previous = down
            if not self.busy and self.lines:
                x, y = get_cursor()
                matched = hit_test(self.lines, x, y)
                if matched is None and self.hover.candidate is not None:
                    self.speech.stop()  # don't read stale text after moving away
                to_read = self.hover.update(matched, time.monotonic() * 1000)
                if to_read:
                    self.speech.speak(to_read.text)
        except Exception as exc:
            self.status("输入监听异常：" + str(exc))
        self.root.after(40, self.poll_input)

    def close(self):
        self.speech.shutdown()
        self.root.destroy()


def run():
    if sys.platform != "win32":
        raise SystemExit("此程序仅支持 Windows 11/10 x64。")
    enable_dpi_awareness()
    root = tk.Tk()
    try:
        ttk.Style(root).theme_use("vista")
    except tk.TclError:
        pass
    ReaderApp(root)
    root.mainloop()