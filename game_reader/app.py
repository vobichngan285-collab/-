"""Windows 11 offline game menu OCR: immediate pointer reading + accessible UI.

The F8 capture is one-shot. There is NO background screen capture, scene-change classification, continuous
OCR, game injection, online service, or private voice-license workaround.
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
from tkinter import ttk

from .core import HoverTracker, OCRLine, hit_test, build_reading_regions
from .ocr_backend import LocalOCR
from .win_screen import enable_dpi_awareness, get_cursor, is_key_down, grab_current_monitor
from .speech import SpeechWorker, enumerate_sapi_voices
from .voice_info import preferred_voice_index, narrator_package_names, voice_diagnostic
from .cues import CuePlayer
from .guangrong_tts import list_guangrong_voices, chosen_dll_path
from .guangrong_setup import install_official_guangrong, installed_x64_dll

CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "GameTextReader"
CONFIG_PATH = CONFIG_DIR / "settings.json"
ERROR_LOG = CONFIG_DIR / "last_ocr_error.txt"
DEFAULTS = {"vk": 0x77, "hotkey_label": "F8", "tier": "small", "voice": "",
            "rate": 0, "volume": 100, "dwell_ms": 0, "guangrong_dir": ""}
MODIFIER_KEYS = {16, 17, 18, 91, 92}
RESULT_TTL_SECONDS = 60.0


def read_settings() -> dict:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Settings must be a dictionary")
        settings = DEFAULTS | {k: data[k] for k in DEFAULTS if k in data}
        settings["vk"] = int(settings["vk"])
        if not 1 <= settings["vk"] <= 254 or settings["vk"] in MODIFIER_KEYS:
            raise ValueError("Invalid hotkey")
        # Existing V1.7 settings can still contain "medium", but V1.8 has
        # only the Small model; always migrate the active tier at load time.
        settings["tier"] = "small"
        # Never keep V1.1's 150ms delay, even from an existing settings file.
        settings["dwell_ms"] = 0
        return settings
    except (OSError, ValueError, TypeError):
        return dict(DEFAULTS)


def write_settings(settings: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, CONFIG_PATH)


class ReaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("游戏文字助手 V1.8 · Small OCR 与保益语音调查")
        root.geometry("690x720")
        root.minsize(610, 650)
        root.protocol("WM_DELETE_WINDOW", self.close)

        self.settings = read_settings()
        local_dll = installed_x64_dll()
        # Strictly independent engine. Never bind to the user's running
        # screen reader or its installed engine directory.
        self.settings["guangrong_dir"] = str(local_dll) if local_dll else ""
        if not local_dll and self.settings.get("voice", "").startswith("grtts:"):
            self.settings["voice"] = ""
        self.events: Queue[tuple] = Queue()
        self.lines: list[OCRLine] = []
        self.ocr_worker = LocalOCR()
        self._prewarm_serial = 0
        self.busy = False
        self.capture_started_at = None
        self.capture_warned = False
        self.closed = False
        self.capture_id = 0
        self.expires_at = None
        self.last_target = None
        self.last_ocr_error = ""
        self.runtime_events: list[str] = []
        self.last_ocr_metrics: dict = {}
        self.voice_report = "尚未扫描语音。"
        self.voices: list[tuple[str, str]] = []
        self.setting_hotkey = False
        self.key_previous = False
        self.hover = HoverTracker(0)
        self.speech = SpeechWorker(
            on_error=lambda e: self.events.put(("tts_error", e)),
            on_event=lambda e: self.events.put(("audio_event", e)))
        self.speech.set_guangrong_directory(self.settings.get("guangrong_dir", ""))
        self.speech.set_rate(self.settings["rate"])
        self.speech.set_volume(self.settings["volume"])
        self.cues = CuePlayer(
            on_error=lambda e: self.events.put(("cue_error", e)),
            on_event=lambda e: self.events.put(("audio_event", e)))
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
        self.prewarm_model(self.settings["tier"])

    def create_widgets(self):
        p = ttk.Frame(self.root, padding=12)
        p.pack(fill="both", expand=True)
        ttk.Label(p, text="游戏文字助手 V1.8 · Small OCR 与保益语音调查",
                  font=("Microsoft YaHei UI", 16, "bold")).pack(anchor="w")
        ttk.Label(p, text="按 F8 截图识别，鼠标进入文字区域立刻朗读；"
                  "按 F8 更新旧结果，识别结果最多保留 60 秒。",
                  wraplength=570).pack(anchor="w", pady=(2, 8))
        keys = ttk.LabelFrame(p, text="截图热键", padding=8)
        keys.pack(fill="x", pady=3)
        self.key_button = ttk.Button(keys, text=self.settings["hotkey_label"],
                                     command=self.capture_hotkey)
        self.key_button.pack(side="left")
        ttk.Label(keys, text="按左侧按钮后直接按单键；Esc 取消。").pack(
            side="left", padx=10)

        models = ttk.LabelFrame(p, text="离线 OCR 引擎", padding=8)
        models.pack(fill="x", pady=3)
        ttk.Label(models, text="PP-OCRv6 Small（唯一引擎，保留快速识别）").pack(anchor="w")

        voice_frame = ttk.LabelFrame(p, text="独立本地朗读（广荣 TTS / Windows 语音）", padding=8)
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
        self.cue_test_button = ttk.Button(vr, text="试听提示音", command=self.test_cues)
        self.cue_test_button.pack(side="left", padx=5)
        self.stop_button = ttk.Button(vr, text="停止朗读",
                                      command=self.speech.stop)
        self.stop_button.pack(side="left")
        self.voice_diag_button = ttk.Button(vr, text="复制语音诊断",
                                            command=self.copy_voice_report)
        self.voice_diag_button.pack(side="left", padx=5)

        gr_row = ttk.Frame(voice_frame)
        gr_row.pack(fill="x", pady=(5, 0))
        self.grtts_button = ttk.Button(gr_row, text="一键准备独立广荣 TTS（首次需要联网）",
                                        command=self.install_guangrong)
        self.grtts_button.pack(side="left")
        self.system_test_button = ttk.Button(gr_row, text="试听系统提示音",
                                             command=lambda: self.cues.play("system_test"))
        self.system_test_button.pack(side="left", padx=6)
        ttk.Label(gr_row, text="单独安装到本软件目录，不使用保益通道。").pack(side="left")

        self.voice_note = tk.StringVar(value="初次点击“一键准备独立广荣”，不需要找 DLL；自然语音包不随基础插件提供。")
        self.voice_note_label = ttk.Label(voice_frame, textvariable=self.voice_note,
                                          wraplength=560)
        self.voice_note_label.pack(anchor="w", pady=(5, 0))

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
        self.runtime_log_button = ttk.Button(controls, text="复制链路日志",
                                              command=self.copy_runtime_log)
        self.runtime_log_button.pack(side="left", padx=5)
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
        ttk.Label(p, text="已移除自动画面检测：动画不会再误删结果。"
                  "新画面请按 F8 刷新；60 秒后自动清空。",
                  wraplength=570).pack(anchor="w", pady=(6, 0))

    def enable_accessibility(self):
        try:
            import tk_uia
            result = tk_uia.enable(self.root)
            for widget, label in (
                (self.key_button, "设置单键截图快捷键"),
                (self.voice_select, "选择本地 TTS 声音"),
                (self.grtts_button, "下载并安装广荣官方组件到游戏文字助手的独立目录"),
                (self.cue_test_button, "试听本程序提示音"),
                (self.system_test_button, "试听 Windows 系统提示音"),
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

    def trace(self, message: str):
        """Only numeric stages and audio states: no screenshot or recognized text."""
        stamp = time.strftime("%H:%M:%S")
        self.runtime_events.append(f"{stamp} {message}")
        self.runtime_events = self.runtime_events[-70:]

    def prewarm_model(self, tier: str):
        # Let a near-immediate F8 take priority over warmup. Only Small exists.
        self._prewarm_serial += 1
        serial = self._prewarm_serial

        def still_current():
            return (not self.closed and not self.busy and
                    self._prewarm_serial == serial and self.settings["tier"] == tier)

        def launch():
            if not still_current():
                return

            def work():
                try:
                    ms = self.ocr_worker.prepare(tier, still_current=still_current)
                    if ms is not None and still_current():
                        self.events.put(("model_ready", tier, ms))
                except Exception as exc:
                    if still_current():
                        self.events.put(("model_warm_error", tier,
                                         f"{type(exc).__name__}: {exc}"))
            threading.Thread(target=work, name="ModelPreload", daemon=True).start()

        # F8 immediately after launch initializes Small inside the capture path;
        # it does not compete with queued background warmup.
        self.root.after(750, launch)

    def copy_runtime_log(self):
        info = [
            "GameTextReader V1.8 | 仅数值与状态，不含截图和识别文字",
            f"当前模型：{self.settings['tier']}",
            f"当前识别文字区域：{len(self.lines)}",
            f"广荣独立组件已准备：{bool(installed_x64_dll())}",
            f"OCR 是否仍在运行：{self.busy}",
            f"当前选择的 TTS ID：{self.settings.get('voice') or '自动'}",
            f"广荣 DLL 已选择：{bool(chosen_dll_path(self.settings.get('guangrong_dir','')))}",
            "最近 OCR 阶段耗时：" + str(self.last_ocr_metrics),
            "最近事件：",
            *self.runtime_events[-70:],
        ]
        self.copy_text("\n".join(info), "已复制完整链路日志，不包含 OCR 文字。")

    def test_cues(self):
        self.trace("试听 F8 识别完成的单次清脆叮声")
        self.status("试听：单次识别完成提示音“叮”；鼠标移到文字时不再播放音效。")
        self.cues.play("complete")

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

     def install_guangrong(self):
        """Only explicit click starts a one-time download; never block Tk."""
        self.grtts_button.configure(state="disabled")
        self.status("正在从广荣作者官方发行页获取独立运行组件...")
        self.trace("用户同意一键准备独立广荣官方组件")
        def work():
            try:
                file = install_official_guangrong(
                    progress=lambda msg: self.events.put(("gr_install_progress", msg)))
                self.events.put(("gr_install_done", file))
            except Exception as exc:
                self.events.put(("gr_install_fail", type(exc).__name__ + ": " + str(exc)[:260]))
        threading.Thread(target=work, name="OfficialGuangrongSetup", daemon=True).start()

    def scan_voices(self):
        self.voice_select.configure(state="disabled")
        self.voice_var.set("正在扫描系统与广荣语音...")
        chosen_dir = self.settings.get("guangrong_dir", "")
        def work():
            try:
                voices = enumerate_sapi_voices()
                packages = narrator_package_names()
                gr_names, gr_error = list_guangrong_voices(chosen_dir)
                gr_voices = [(f"grtts:{i}", f"广荣 · {name}")
                             for i, name in enumerate(gr_names)]
                self.events.put(("voices", voices + gr_voices, packages, gr_error))
            except Exception as exc:
                self.events.put(("tts_error", str(exc)))
        threading.Thread(target=work, daemon=True, name="VoiceDiscovery").start()

    def change_voice(self, _event=None):
        index = self.voice_select.current()
        if 0 <= index < len(self.voices):
            self.settings["voice"] = self.voices[index][0]
            self.speech.set_voice(self.settings["voice"])
            self.persist()

    def test_voice(self):
        self.trace("TTS 试听：准备提交 21 字，独立于 OCR")
        self.speech.speak("你好，这是电脑游戏文字助手的本地语音试听。")

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
        self.root.after(100, self.capture)

    def capture(self):
        if self.busy:
            return
        self.invalidate("正在识别新画面...")
        capture_id = self.capture_id
        self.busy = True
        self.capture_started_at = time.monotonic()
        self.capture_warned = False
        self.read_btn.configure(state="disabled")
        tier = self.settings["tier"]
        self.trace(f"F8 截图触发，模型={tier}")

        def worker():
            started = time.perf_counter()
            phase = "截图"
            try:
                image, origin = grab_current_monitor()
                grab_ms = round((time.perf_counter() - started) * 1000)
                phase = f"离线OCR推理 ({tier})"
                lines, timing = self.ocr_worker.recognize_timed(image, origin, tier)
                total_ms = round((time.perf_counter() - started) * 1000)
                timing["grab_ms"] = grab_ms
                timing["total_ms"] = total_ms
                timing["input_resolution"] = f"{image.width}x{image.height}"
                self.events.put(("ocr_ok", capture_id, lines, timing))
            except Exception:
                self.events.put(("ocr_fail", capture_id,
                                 "phase: " + phase + "\n" + traceback.format_exc()))
        threading.Thread(target=worker, daemon=True, name="OneShotOCR").start()

    def poll_messages(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "ocr_ok":
                    _, capture_id, lines, timing = event
                    self.busy = False
                    self.capture_started_at = None
                    self.read_btn.configure(state="normal")
                    if capture_id != self.capture_id:
                        continue
                    self.lines = build_reading_regions(lines)
                    self.hover.reset()
                    self.last_target = None
                    self.update_output("\n".join(region.text for region in self.lines))
                    if self.lines:
                        self.expires_at = time.monotonic() + RESULT_TTL_SECONDS
                    self.last_ocr_metrics = dict(timing)
                    self.trace(f"OCR 完成：{timing}；可朗读区域 {len(self.lines)}")
                    if not self.lines:
                        self.status(f"{timing['tier']} OCR 完成，但没有有效文字。"
                                    "这不是 TTS 错误；请复制链路日志。")
                    else:
                        self.status(
                            f"{timing['tier']}：{len(self.lines)} 区域｜"
                            f"截图 {timing['grab_ms']}ms｜加载/等待 {timing['model_ms']}ms｜"
                            f"推理 {timing['inference_ms']}ms｜总 {timing['total_ms']}ms。"
                            "文字有效期 60 秒。")
                    self.cues.play("complete")
                elif kind == "ocr_fail":
                    _, capture_id, detail = event
                    self.busy = False
                    self.capture_started_at = None
                    self.read_btn.configure(state="normal")
                    if capture_id != self.capture_id:
                        continue
                    self.last_ocr_error = detail
                    self.trace("OCR 报错：" + detail.splitlines()[0])
                    try:
                        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                        ERROR_LOG.write_text(detail[-24000:], encoding="utf-8")
                    except OSError:
                        pass
                    self.status("识别失败。点击“复制失败诊断”查看错误。")
                    self.update_output("识别失败。")
                elif kind == "voices":
                    _, voices, packages, gr_error = event
                    self.voices = voices
                    self.voice_report = (voice_diagnostic(
                        [(id_, label) for id_, label in voices
                         if not id_.startswith("grtts:")], packages)
                        + "\n广荣语音数量：" + str(sum(
                            1 for id_, _ in voices if id_.startswith("grtts:")))
                        + "\n广荣状态：" + (gr_error or "已完成 DLL 语音枚举"))
                    names = [name for _, name in voices]
                    self.voice_select.configure(values=names,
                          state="readonly" if names else "disabled")
                    if voices:
                        index = preferred_voice_index(voices, self.settings["voice"])
                        self.voice_select.current(index)
                        self.speech.set_voice(voices[index][0])
                        available = any(n.lower() in label.lower()
                                        for _, label in voices
                                        for n in ("Yunxi", "Xiaoxiao"))
                        if any(id_.startswith("grtts:") for id_, _ in voices):
                            self.voice_note.set("已识别出广荣语音；可在上方选择并试听。"
                                                "真实播放要在你的电脑上验证。")
                        elif gr_error and chosen_dll_path(self.settings.get("guangrong_dir","")):
                            self.voice_note.set("广荣独立接口当前无法初始化：" + gr_error)
                        elif available:
                            self.voice_note.set("检测到可选的自然语音，请点击试听确认。")
                        elif packages:
                            self.voice_note.set("已安装讲述人自然语音，但 SAPI/WinRT 未开放。"
                                                "可以手动选择广荣 DLL 试用。")
                        else:
                            self.voice_note.set("普通 Windows 本地语音可选；"
                                                "云希、晓晓需广荣等兼容引擎。")
                    else:
                        self.voice_var.set("未找到可调用的本地语音")
                elif kind == "gr_install_progress":
                    self.status(str(event[1]))
                elif kind == "gr_install_fail":
                    self.grtts_button.configure(state="normal")
                    self.trace("广荣组件安装失败：" + str(event[1]))
                    self.status("独立广荣安装失败，仍可使用 Windows 本地语音。"
                                "详见“复制链路日志”。")
                elif kind == "gr_install_done":
                    self.grtts_button.configure(state="normal")
                    self.settings["guangrong_dir"] = event[1]
                    self.settings["voice"] = "grtts:0"
                    self.speech.set_guangrong_directory(event[1])
                    self.persist()
                    self.trace("独立广荣官方组件下载及校验成功；开始检测 64 位 DLL")
                    self.status("广荣官方组件已准备，正在检查能否独立合成语音...")
                    self.scan_voices()
                elif kind == "model_ready":
                    self.trace(f"{event[1]} 模型后台预热完成，耗时 {event[2]}ms")
                elif kind == "model_warm_error":
                    self.trace(f"{event[1]} 模型后台预热失败：{event[2]}")
                elif kind == "audio_event":
                    self.trace("音频：" + str(event[1]))
                elif kind == "cue_error":
                    self.trace("音效错误：" + str(event[1]))
                    self.status("提示音播放错误，详见“复制链路日志”。")
                elif kind == "tts_error":
                    self.trace("TTS 错误：" + str(event[1]))
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
            if self.busy and self.capture_started_at is not None:
                elapsed = time.monotonic() - self.capture_started_at
                if elapsed >= 7.0 and not self.capture_warned:
                    self.capture_warned = True
                    self.trace(f"OCR 运行已超过 {elapsed:.1f} 秒：仍在等待结果")
                    self.status("OCR 推理时间较长（超过 7 秒），仍在处理；"
                                "不会无声丢弃结果。可待完成后查看链路日志。")
            if not self.busy and self.lines:
                x, y = get_cursor()
                target = hit_test(self.lines, x, y)
                if target != self.last_target:
                    if self.overlay is not None:
                        self.overlay.show(target)
                    # Do not cancel a still-synthesizing sentence just because
                    # the pointer briefly left a box. The next target's speak
                    # command interrupts it. F8/clear/expiry still stop it.
                    self.last_target = target
                # Zero dwell. The first poll entering the region speaks once.
                to_read = self.hover.update(target, time.monotonic() * 1000)
                if to_read is not None:
                    self.trace(f"鼠标命中文字；向 TTS 提交 {len(to_read.text)} 字")
                    self.speech.speak(to_read.text)
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
