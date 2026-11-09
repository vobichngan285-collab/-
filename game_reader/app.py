"""Windows 11 offline game menu OCR: immediate pointer reading + accessible UI.

The F8 capture uses the original V1.2 Small OCR parameters. It never
continuously scans the screen. Natural voices are discovered from installed
Windows packages and require a locally supplied authorized configuration.
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
from tkinter import ttk, filedialog
from PIL import ImageGrab

from .core import HoverTracker, OCRLine, hit_test, build_reading_regions
from .ocr_backend import LocalOCR
from .win_screen import (enable_dpi_awareness, get_cursor, is_key_down,
                         grab_current_monitor, monitor_rect_at_cursor)
from .speech import SpeechWorker, enumerate_sapi_voices
from .voice_info import preferred_voice_index, narrator_package_names, voice_diagnostic
from .ms_voice_discovery import (discover_natural_voices, load_user_config,
                                 inspect_local_voice_config)
from .cues import CuePlayer
from .hover_modes import (MOUSE_SIDE_VKS, DEFAULT_REGION, RelativeRegion,
                          HOTKEY_FIELDS, HOTKEY_LABELS, hotkey_label,
                          valid_hotkey, sanitize_hotkeys, parse_period_ms,
                          capture_box, normalized_text, next_mouse_mode)
from .region_picker import ScreenRegionPicker

CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "GameTextReader"
CONFIG_PATH = CONFIG_DIR / "settings.json"
ERROR_LOG = CONFIG_DIR / "last_ocr_error.txt"
DEFAULTS = {"vk": 0x77, "hotkey_label": "F8",
            "mode_vk": 0x78, "mode_hotkey_label": "F9",
            "local_vk": 0x79, "local_hotkey_label": "F10",
            "period_ms": 500, "region": list(DEFAULT_REGION),
            "tier": "small", "voice": "", "rate": 0,
            "volume": 100, "dwell_ms": 0, "luna_config": ""}
RESULT_TTL_SECONDS = 60.0


def read_settings() -> dict:
    """Migrate an existing V1.2/voice-fix settings file without losing voice."""
    try:
        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            payload = {}
    except (OSError, ValueError, TypeError):
        payload = {}
    settings = DEFAULTS | {k: payload[k] for k in DEFAULTS if k in payload}
    settings = sanitize_hotkeys(settings)
    try:
        settings["period_ms"] = parse_period_ms(settings["period_ms"])
    except ValueError:
        settings["period_ms"] = 500
    settings["region"] = RelativeRegion.from_settings(settings["region"]).as_list()
    settings["tier"] = "small"
    settings["dwell_ms"] = 0
    return settings


def write_settings(settings: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, CONFIG_PATH)


class ReaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("游戏文字助手 · V1.2 Small / 悬停 OCR 实验版")
        root.geometry("760x860")
        root.minsize(660, 710)
        root.protocol("WM_DELETE_WINDOW", self.close)

        self.settings = read_settings()
        app_dir = (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False)
                   else Path(__file__).resolve().parents[1])
        # Prefer an actual local user file, not a hard-coded model path.
        if (app_dir / "config..json").is_file():
            self.settings["luna_config"] = str(app_dir / "config..json")
        self.events: Queue[tuple] = Queue()
        self.lines: list[OCRLine] = []
        self.ocr_worker = LocalOCR()
        self.busy = False
        self.closed = False
        self.capture_id = 0
        self.expires_at = None
        self.last_target = None
        self.last_ocr_error = ""
        self.voice_report = "尚未扫描语音。"
        self.voices: list[tuple[str, str]] = []
        self.setting_hotkey = False
        self._binding_target = None
        self._hotkey_previous = {k: is_key_down(self.settings[k]) for k in HOTKEY_FIELDS}
        self._side_previous = {vk: is_key_down(vk) for vk in MOUSE_SIDE_VKS}
        self.mouse_mode = "pointer"
        self.mode_generation = 0
        self.hover_ocr_busy = False
        self._hover_last_text = ""
        self._hover_next_due = time.monotonic() + 0.5
        self.pending_full_capture = False
        self._region_picker = None
        self._choosing_region = False
        self.hover = HoverTracker(0)
        self.speech = SpeechWorker(on_error=lambda e: self.events.put(("tts_error", e)))
        self.speech.set_luna_config(self.settings.get("luna_config", ""))
        self.speech.set_rate(self.settings["rate"])
        self.speech.set_volume(self.settings["volume"])
        self.cues = CuePlayer()
        self.overlay = None
        self.overlay_error = ""
        try:
            from .overlay import ClickThroughOutline
            self.overlay = ClickThroughOutline()
        except Exception as ex:
            self.overlay_error = f"{type(ex).__name__}: {ex}"

        self.create_widgets()
        self.enable_accessibility()
        self.scan_voices()
        self.root.after(25, self.poll_input)
        self.root.after(40, self.poll_messages)

    def create_widgets(self):
        p = ttk.Frame(self.root, padding=12)
        p.pack(fill="both", expand=True)
        ttk.Label(p, text="游戏文字助手 · V1.2 Small OCR",
                  font=("Microsoft YaHei UI", 16, "bold")).pack(anchor="w")
        ttk.Label(p, text="按 F8 截图识别，鼠标进入文字区域立刻朗读；"
                  "识别结果保留 60 秒。系统自然语音需先试听确认。",
                  wraplength=570).pack(anchor="w", pady=(2, 8))
        keys = ttk.LabelFrame(p, text="截图热键", padding=8)
        keys.pack(fill="x", pady=3)
        self.key_button = ttk.Button(keys, text=self.settings["hotkey_label"],
                                     command=self.capture_hotkey)
        self.key_button.pack(side="left")
        ttk.Label(keys, text="按左侧按钮后直接按单键；Esc 取消。").pack(
            side="left", padx=10)

        models = ttk.LabelFrame(p, text="离线 OCR 模型", padding=8)
        models.pack(fill="x", pady=3)
        ttk.Label(models, text="PP-OCRv6 Small · V1.2 原始检测设置（唯一模型）").pack(anchor="w")

        voice_frame = ttk.LabelFrame(p, text="本地语音（系统已安装自然音色 / SAPI / WinRT）", padding=8)
        voice_frame.pack(fill="x", pady=3)
        self.voice_var = tk.StringVar(value="正在扫描本地语音...")
        self.voice_select = ttk.Combobox(voice_frame, textvariable=self.voice_var,
                                         width=56, state="readonly")
        self.voice_select.pack(fill="x")
        self.voice_select.bind("<<ComboboxSelected>>", self.change_voice)

        vr = ttk.Frame(voice_frame)
        vr.pack(fill="x", pady=(5, 0))
        self.rescan_button = ttk.Button(vr, text="重新扫描语音",
                                        command=self.scan_voices)
        self.rescan_button.pack(side="left")
        self.preview_button = ttk.Button(vr, text="试听",
                                         command=self.test_voice)
        self.preview_button.pack(side="left", padx=5)
        self.stop_button = ttk.Button(vr, text="停止朗读",
                                      command=self.speech.stop)
        self.stop_button.pack(side="left")
        self.voice_diag_button = ttk.Button(vr, text="复制语音诊断",
                                            command=self.copy_voice_report)
        self.voice_diag_button.pack(side="left", padx=5)

        self.voice_note = tk.StringVar(value="扫描到自然语音包仅代表已安装；试听成功后才算真正可朗读。")
        self.voice_note_label = ttk.Label(voice_frame, textvariable=self.voice_note,
                                          wraplength=560)
        self.voice_note_label.pack(anchor="w", pady=(5, 0))
        import_row = ttk.Frame(voice_frame)
        import_row.pack(fill="x", pady=4)
        self.import_luna_button = ttk.Button(
            import_row, text="选择本机原版语音配置", command=self.import_luna_config)
        self.import_luna_button.pack(side="left")
        ttk.Label(import_row, text="原始 config..json 留在本机；不写入 GitHub。").pack(
            side="left", padx=6)

        rate_row = ttk.Frame(voice_frame)
        rate_row.pack(fill="x", pady=3)
        ttk.Label(rate_row, text="语速").pack(side="left")
        self.rate_var = tk.IntVar(value=int(self.settings["rate"]))
        self.rate_slider = ttk.Scale(rate_row, from_=-8, to=8, variable=self.rate_var,
                                      command=self.change_rate)
        self.rate_slider.pack(side="left", fill="x", expand=True, padx=8)
        self.rate_label = ttk.Label(rate_row, text=str(self.rate_var.get()), width=4)
        self.rate_label.pack(side="left")

        volume_row = ttk.Frame(voice_frame)
        volume_row.pack(fill="x", pady=3)
        ttk.Label(volume_row, text="音量").pack(side="left")
        self.volume_var = tk.IntVar(value=int(self.settings["volume"]))
        self.volume_slider = ttk.Scale(volume_row, from_=0, to=100,
                                        variable=self.volume_var, command=self.change_volume)
        self.volume_slider.pack(side="left", fill="x", expand=True, padx=8)
        self.volume_label = ttk.Label(volume_row,
                                      text=f'{self.settings["volume"]}%', width=5)
        self.volume_label.pack(side="left")

        controls = ttk.Frame(p)
        controls.pack(fill="x", pady=(9, 4))
        self.read_btn = ttk.Button(controls, text="立即截屏识别",
                                   command=self.capture_from_button)
        self.read_btn.pack(side="left")
        ttk.Button(controls, text="复制失败诊断",
                   command=self.copy_error).pack(side="left", padx=5)
        ttk.Button(controls, text="最小化到任务栏",
                   command=self.root.iconify).pack(side="left")
        ttk.Button(controls, text="清除所有结果",
                   command=lambda: self.invalidate("已清除全部识别结果。")).pack(
                       side="left", padx=5)

        self.status_var = tk.StringVar(value="就绪。截图完成发短提示音；"
                                       "鼠标进入文字立即读，不需要等待。")
        self.status_label = ttk.Label(p, textvariable=self.status_var, wraplength=570)
        self.status_label.pack(anchor="w", pady=4)
        viewer = ttk.LabelFrame(p, text="本次识别的文字（无坐标，保留至过期）", padding=6)
        viewer.pack(fill="both", expand=True)
        self.output = tk.Text(viewer, wrap="word", height=8, state="disabled",
                              font=("Microsoft YaHei UI", 10))
        scroll = ttk.Scrollbar(viewer, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=scroll.set)
        self.output.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        ttk.Label(p, text="已关闭旧的画面变化检测；保留 V1.2 原始截图与 Small OCR 参数。",
                  wraplength=570).pack(anchor="w", pady=(6, 0))

    def enable_accessibility(self):
        try:
            import tk_uia
            result = tk_uia.enable(self.root)
            for widget, label in (
                (self.key_button, "设置单键截图快捷键"),
                (self.voice_select, "选择本地 TTS 声音"),
                (self.import_luna_button, "选择原版语音配置文件"),
                (self.rate_slider, "语速"),
                (self.volume_slider, "音量"),
                (self.output, "当前截图识别的文字"),
                (self.status_label, "OCR 与朗读状态"),
            ):
                tk_uia.set_acc_name(widget, label)
            self.accessibility_status = str(result)
        except Exception as exc:
            self.accessibility_status = "FAILED: " + str(exc)
            self.events.put(("ui_error", self.accessibility_status))

    def status(self, message: str):
        self.status_var.set(message)

    def update_output(self, text: str):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def persist(self):
        try:
            write_settings(self.settings)
        except Exception as ex:
            self.status("设置保存失败：" + str(ex))

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
            self.status("请使用字母、数字、F 功能键或小键盘单键。")
            return
        self.settings["vk"] = vk
        self.settings["hotkey_label"] = event.keysym
        self.setting_hotkey = False
        self.key_previous = True
        self.key_button.configure(text=event.keysym)
        self.root.unbind("<KeyPress>")
        self.persist()
        self.status(f"截图热键已设置：{event.keysym}")

    def import_luna_config(self):
        selected = filedialog.askopenfilename(
            parent=self.root, title="选择你电脑中的原版 config..json",
            filetypes=[("JSON 配置", "*.json"), ("所有文件", "*")])
        if not selected:
            return
        state = inspect_local_voice_config(selected)
        if state != "ok":
            self.status("原版配置检查未通过：" + state + "；原文件未修改。")
            return
        self.settings["luna_config"] = selected
        self.speech.set_luna_config(selected)
        self.persist()
        self.status("本机配置路径已更新，许可字段存在（不代表 SDK 已授权）。请点击试听。")
        self.scan_voices()

    def scan_voices(self):
        self.voice_select.configure(state="disabled")
        self.voice_var.set("正在扫描电脑已安装的语音包...")
        def work():
            try:
                natural = discover_natural_voices()
                voices = [(f"natural:{v.package}", v.ui_label) for v in natural]
                voices.extend(enumerate_sapi_voices())
                packages = narrator_package_names()
                has_config = inspect_local_voice_config(
                    self.settings.get("luna_config", "")) == "ok"
                self.events.put(("voices", voices, packages, len(natural), has_config))
            except Exception as exc:
                self.events.put(("tts_error", "语音扫描失败：" + type(exc).__name__))
        threading.Thread(target=work, daemon=True, name="VoiceDiscovery").start()

    def change_voice(self, _event=None):
        index = self.voice_select.current()
        if 0 <= index < len(self.voices):
            self.settings["voice"] = self.voices[index][0]
            self.speech.set_voice(self.settings["voice"])
            self.persist()

    def speak_selected(self, text: str):
        # Do NOT rely on the speech thread having applied an old
        # set_luna_config() event. Each natural voice request carries its
        # current GUI voice and config path as one immutable queue payload.
        index = self.voice_select.current()
        voice_id = (self.voices[index][0] if 0 <= index < len(self.voices)
                    else self.settings.get("voice", ""))
        if voice_id.startswith("natural:"):
            self.speech.speak(
                text, natural_voice_id=voice_id,
                config_path=self.settings.get("luna_config", ""))
        else:
            self.speech.speak(text)

    def test_voice(self):
        self.speak_selected("你好，这是电脑游戏文字助手的本地语音试听。")

    def copy_voice_report(self):
        report = self.voice_report + "\nUI Automation: " + self.accessibility_status
        self.copy_text(report, "语音和界面诊断已复制。")

    def copy_error(self):
        if not self.last_ocr_error:
            self.status("当前没有 OCR 失败诊断。")
        else:
            self.copy_text(self.last_ocr_error, "OCR 失败诊断已复制。")

    def copy_text(self, value: str, message: str):
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.root.update_idletasks()
        self.status(message)

    def change_rate(self, _value):
        value = max(-8, min(8, int(round(float(self.rate_var.get())))))
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

    def invalidate(self, reason: str):
        """Actually erase all text, coordinates, hover state and audio."""
        self.capture_id += 1
        self.expires_at = None
        self.lines = []
        self.last_target = None
        self.hover.reset()
        self.speech.stop()
        if self.overlay is not None:
            self.overlay.hide()
        self.update_output("")
        self.status(reason)

    def capture_from_button(self):
        self.root.iconify()
        self.root.after(250, self.capture)

    def capture(self):
        if self.busy:
            return
        self.invalidate("正在识别新画面...")
        capture_id = self.capture_id
        self.busy = True
        self.read_btn.configure(state="disabled")
        tier = self.settings["tier"]

        def worker():
            started = time.monotonic()
            phase = "截图"
            try:
                image, origin = grab_current_monitor()
                phase = f"离线OCR推理（{tier}）"
                lines = self.ocr_worker.recognize(image, origin, tier)
                self.events.put(("ocr_ok", capture_id, lines,
                                 round((time.monotonic() - started) * 1000)))
            except Exception as exc:
                self.events.put(("ocr_fail", capture_id,
                                 "phase: " + phase + "\n" +
                                 traceback.format_exc()))
        threading.Thread(target=worker, daemon=True, name="OneShotOCR").start()

    def poll_messages(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "ocr_ok":
                    _, capture_id, lines, milliseconds = event
                    self.busy = False
                    self.read_btn.configure(state="normal")
                    if capture_id != self.capture_id:
                        continue
                    self.lines = build_reading_regions(lines)
                    self.hover.reset()
                    self.last_target = None
                    self.update_output("\n".join(region.text for region in self.lines))
                    if self.lines:
                        self.expires_at = time.monotonic() + RESULT_TTL_SECONDS
                    self.status(f"识别完成：{len(self.lines)} 个朗读区域；"
                                f"耗时 {milliseconds} 毫秒。60 秒后自动清空。")
                    self.cues.play("complete")
                elif kind == "ocr_fail":
                    _, capture_id, detail = event
                    self.busy = False
                    self.read_btn.configure(state="normal")
                    if capture_id != self.capture_id:
                        continue
                    self.last_ocr_error = detail
                    try:
                        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                        ERROR_LOG.write_text(detail[-24000:], encoding="utf-8")
                    except OSError:
                        pass
                    self.status("识别失败。点击“复制失败诊断”查看错误。")
                    self.update_output("识别失败。")
                elif kind == "voices":
                    _, voices, packages, natural_count, has_config = event
                    self.voices = voices
                    self.voice_report = (voice_diagnostic(
                        [(v, n) for v, n in voices if not v.startswith("natural:")], packages)
                        + f"\n系统扫描到自然语音包：{natural_count} 个"
                        + f"\n已选择本地原配置：{has_config}"
                        + "\n扫描到语音包不代表合成成功；本机试听才是验收。")
                    names = [name for _, name in voices]
                    self.voice_select.configure(values=names,
                          state="readonly" if names else "disabled")
                    if voices:
                        index = preferred_voice_index(voices, self.settings["voice"])
                        self.voice_select.current(index)
                        self.speech.set_voice(voices[index][0])
                        if natural_count:
                            self.voice_note.set(
                                f"已发现 {natural_count} 个系统自然语音包，"
                                + ("请试听确认真实发声。" if has_config
                                   else "请先选择本机原版语音配置，再试听。"))
                        elif packages:
                            self.voice_note.set("系统有自然音色相关名称，但当前用户未枚举出可用安装位置。")
                        else:
                            self.voice_note.set("未发现系统自然语音包；其它系统音色仍可使用。")
                    else:
                        self.voice_var.set("未找到可调用的本地语音")
                elif kind == "tts_error":
                    self.status("TTS 出错：" + event[1])
                elif kind == "ui_error":
                    self.status("无障碍接口初始化异常：" + event[1])
        except Empty:
            pass
        self.root.after(40, self.poll_messages)

    def poll_input(self):
        if self.closed:
            return
        try:
            down = is_key_down(self.settings["vk"])
            if not self.setting_hotkey and down and not self.key_previous:
                if self.root.state() == "normal":
                    self.capture_from_button()
                else:
                    self.capture()
            self.key_previous = down

            if self.expires_at is not None and time.monotonic() >= self.expires_at:
                self.invalidate("本次 OCR 已满 60 秒：文字、坐标和框已全部删除。")
            if not self.busy and self.lines:
                x, y = get_cursor()
                target = hit_test(self.lines, x, y)
                if target != self.last_target:
                    if self.overlay is not None:
                        self.overlay.show(target)
                    if target is None and self.last_target is not None:
                        self.speech.stop()
                    self.last_target = target
                # Zero dwell. The first poll entering the region speaks once.
                to_read = self.hover.update(target, time.monotonic() * 1000)
                if to_read is not None:
                    self.cues.play("hover")
                    self.speak_selected(to_read.text)
        except Exception as exc:
            self.status("鼠标 / 边框监听异常：" + str(exc))
        self.root.after(20, self.poll_input)

    def close(self):
        self.closed = True
        self.speech.shutdown()
        self.cues.shutdown()
        if self.overlay is not None:
            self.overlay.close()
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
