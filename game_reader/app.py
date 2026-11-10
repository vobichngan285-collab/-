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
                         grab_current_monitor, monitor_rect_at_cursor, monitor_rect_at_point)
from .speech import SpeechWorker, enumerate_sapi_voices
from .voice_info import preferred_voice_index, narrator_package_names, voice_diagnostic
from .ms_voice_discovery import (discover_natural_voices, load_user_config,
                                 inspect_local_voice_config)
from .cues import CuePlayer
from .hover_modes import (MOUSE_SIDE_VKS, DEFAULT_REGION, RelativeRegion,
                          HOTKEY_FIELDS, HOTKEY_LABELS, hotkey_label,
                          valid_hotkey, sanitize_hotkeys, parse_period_ms,
                          capture_box, normalized_text, next_mouse_mode,
                          cursor_still_near_capture)
from .region_picker import ScreenRegionPicker
from .foreground import foreground_class, foreground_window_id
from .hover_target import centered_region
from .fixed_region import (parse_fixed_region, parse_monitor, region_on_same_monitor,
                           screenshot_fingerprint, frame_has_changed,
                           parse_strategy, display_color, parse_thickness)
from .text_filters import (DEFAULT_FILTER_SETTINGS, filter_speech_text,
                           is_repeat_speech, similarity_threshold)

CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "GameTextReader"
CONFIG_PATH = CONFIG_DIR / "settings.json"
ERROR_LOG = CONFIG_DIR / "last_ocr_error.txt"
DEFAULTS = {"vk": 0x77, "hotkey_label": "F8",
            "mode_vk": 0x78, "mode_hotkey_label": "F9",
            "local_vk": 0x79, "local_hotkey_label": "F10",
            "pick_vk": 0x7A, "pick_hotkey_label": "F11",
            "clear_vk": 0x75, "clear_hotkey_label": "F6",
            "frame_vk": 0x76, "frame_hotkey_label": "F7",
            "period_ms": 500, "region": list(DEFAULT_REGION),
            "fixed_region": None, "fixed_monitor": None,
            "region_strategy": "change", "region_period_ms": 500,
            "frame_color": "#42DD9C", "frame_thickness": 3,
            "success_cue": True,
            "tier": "small", "voice": "", "rate": 0,
            "volume": 100, "dwell_ms": 0, "luna_config": "",
            **DEFAULT_FILTER_SETTINGS}
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
    monitor = parse_monitor(settings["fixed_monitor"])
    fixed = parse_fixed_region(settings["fixed_region"], monitor) if monitor else None
    settings["fixed_monitor"] = list(monitor) if fixed else None
    settings["fixed_region"] = list(fixed) if fixed else None
    settings["region_strategy"] = parse_strategy(settings["region_strategy"])
    try:
        settings["region_period_ms"] = parse_period_ms(settings["region_period_ms"])
    except ValueError:
        settings["region_period_ms"] = 500
    settings["frame_color"] = display_color(settings["frame_color"])
    settings["frame_thickness"] = parse_thickness(settings["frame_thickness"])
    settings["tier"] = "small"
    settings["dwell_ms"] = 0
    try:
        settings["similarity_threshold"] = similarity_threshold(
            settings["similarity_threshold"])
    except ValueError:
        settings["similarity_threshold"] = 2
    for key in DEFAULT_FILTER_SETTINGS:
        if key != "similarity_threshold":
            settings[key] = bool(settings[key])
    return settings


def write_settings(settings: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, CONFIG_PATH)


class ReaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Blue Star OCR · 游戏文字朗读助手")
        root.geometry("1120x900")
        root.minsize(960, 760)
        root.protocol("WM_DELETE_WINDOW", self.close)

        self.settings = read_settings()
        app_dir = (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False)
                   else Path(__file__).resolve().parents[1])
        # Prefer an actual local user file, not a hard-coded model path.
        if (app_dir / "config..json").is_file():
            self.settings["luna_config"] = str(app_dir / "config..json")
        self.events: Queue[tuple] = Queue()
        self.lines: list[OCRLine] = []
        self._full_capture_window = None
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
        self.region_ocr_busy = False
        self._region_job_id = 0
        self._region_next_due = float("inf")
        self._region_last_fingerprint = None
        self._region_last_text = ""
        self._region_last_window = None
        self._region_border_visible = True
        self._region_force_initial = False
        self.hover_ocr_busy = False
        self._hover_last_text = ""
        self._mode_announcement_until = 0.0
        self._hover_next_due = time.monotonic() + 0.5
        self.pending_full_capture = False
        self._region_picker = None
        self._choosing_region = False
        self._region_previous_root_state = "normal"
        self._picker_anchor = None
        self._picker_monitor = None
        self._picker_snapshot = None
        self._picker_foreground = None
        self._ocr_lock = threading.Lock()  # Never run concurrent work in RapidOCR.
        self._hover_spoken_cursor = None
        self._hover_spoken_foreground = None
        self.last_voice_timing = "尚未测量"
        self.hover = HoverTracker(0)
        self.speech = SpeechWorker(on_error=lambda e: self.events.put(("tts_error", e)),
                                   on_event=lambda e: self.events.put(("tts_timing", e)))
        self.speech.set_luna_config(self.settings.get("luna_config", ""))
        self.speech.set_rate(self.settings["rate"])
        self.speech.set_volume(self.settings["volume"])
        self.cues = CuePlayer(on_error=lambda e: self.events.put(("cue_error", e)))
        self.overlay = None
        self.scan_frame = None
        self.fixed_frame = None
        self._frame_style = None
        self.overlay_error = ""
        self._apply_frame_style()

        self.create_widgets()
        self.enable_accessibility()
        self.scan_voices()
        self.root.after(25, self.poll_input)
        self.root.after(40, self.poll_messages)

    def create_widgets(self):
        """Large-print, native-widget settings UI.

        No graphic-only interaction surfaces: every navigation item, checkbox,
        shortcut control and text field is a real focusable ttk widget with
        a distinct Windows accessibility name.
        """
        from .ui_theme import configure_theme, BG, SIDEBAR, TEXT, MUTED
        self.ui_style = configure_theme(self.root)

        top = ttk.Frame(self.root, padding=(22, 14))
        top.pack(fill="x")
        ttk.Label(top, text="Blue Star OCR", style="Heading.TLabel").pack(side="left")
        ttk.Label(top, text="  游戏文字朗读助手", style="Subheading.TLabel").pack(
            side="left", padx=(5, 0))

        body = ttk.Frame(self.root, padding=(10, 0, 12, 0))
        body.pack(fill="both", expand=True)
        sidebar = ttk.Frame(body, style="Sidebar.TFrame", width=230, padding=(12, 12))
        sidebar.pack(side="left", fill="y", padx=(0, 12))
        sidebar.pack_propagate(False)
        ttk.Label(sidebar, text="设置中心", style="Sidebar.TLabel").pack(
            anchor="w", pady=(5, 22))

        main = ttk.Frame(body)
        main.pack(side="left", fill="both", expand=True)
        self.page_title = tk.StringVar(value="OCR 与鼠标")
        ttk.Label(main, textvariable=self.page_title,
                  style="Heading.TLabel").pack(anchor="w", pady=(10, 14))
        self.page_host = ttk.Frame(main)
        self.page_host.pack(fill="both", expand=True)
        self.page_host.grid_columnconfigure(0, weight=1)
        self.page_host.grid_rowconfigure(0, weight=1)
        self._pages = {}
        self.nav_buttons = {}
        nav = (
            ("mouse", "OCR 与鼠标"),
            ("region", "区域跟踪"),
            ("voice", "语音设置"),
            ("fullscreen", "全屏 OCR"),
            ("filters", "内容过滤"),
            ("general", "通用设置"),
            ("about", "关于软件"),
        )
        for key, title in nav:
            self.nav_buttons[key] = ttk.Button(
                sidebar, text=title, style="Nav.TButton",
                command=lambda which=key: self.show_page(which))
            self.nav_buttons[key].pack(fill="x", pady=(0, 10))
            page = ttk.Frame(self.page_host, padding=(4, 0, 4, 4))
            page.grid(row=0, column=0, sticky="nsew")
            self._pages[key] = page

        def section(page, title):
            group = ttk.LabelFrame(page, text="  " + title + "  ", padding=(16, 12))
            group.pack(fill="x", pady=(0, 12))
            return group

        def row(group, space=8):
            container = ttk.Frame(group, style="Card.TFrame")
            container.pack(fill="x", pady=space)
            return container

        def card_label(group, title):
            return ttk.Label(group, text=title, style="Card.TLabel")

        def note(group, text):
            ttk.Label(group, text=text, style="CardMuted.TLabel",
                      wraplength=630).pack(anchor="w", pady=(4, 3))

        mouse = self._pages["mouse"]
        modes = section(mouse, "工作模式")
        self.mouse_mode_var = tk.StringVar(
            value="当前：默认模式（按 F9 循环切换三种模式）")
        choose = row(modes, 2)
        self.mouse_mode_button = ttk.Button(
            choose, text="鼠标模式", style="Accent.TButton",
            command=lambda: self.set_mouse_mode("hover"))
        self.mouse_mode_button.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.default_mode_button = ttk.Button(
            choose, text="默认模式", command=lambda: self.set_mouse_mode("pointer"))
        self.default_mode_button.pack(side="left", fill="x", expand=True, padx=(6, 6))
        self.region_mode_button = ttk.Button(
            choose, text="区域跟踪", command=lambda: self.set_mouse_mode("region"))
        self.region_mode_button.pack(side="left", fill="x", expand=True)
        ttk.Label(modes, textvariable=self.mouse_mode_var, style="CardMuted.TLabel").pack(
            anchor="w", pady=(0, 4))
        hotkeys = row(modes)
        card_label(hotkeys, "切换按键").pack(side="left")
        self.mode_key_button = ttk.Button(
            hotkeys, text=self.settings["mode_hotkey_label"], width=17,
            command=lambda: self.begin_hotkey("mode_vk"))
        self.mode_key_button.pack(side="left", padx=(12, 15))
        card_label(hotkeys, "手动局部 OCR").pack(side="left")
        self.local_key_button = ttk.Button(
            hotkeys, text=self.settings["local_hotkey_label"], width=15,
            command=lambda: self.begin_hotkey("local_vk"))
        self.local_key_button.pack(side="left", padx=(10, 0))
        self.mode_voice_var = tk.BooleanVar(value=self.settings["mode_voice_hint"])
        self.mode_voice_check = ttk.Checkbutton(
            modes, text="切换模式语音提示",
            variable=self.mode_voice_var, command=self.save_visual_settings)
        self.mode_voice_check.pack(anchor="w")

        selection = section(mouse, "绿色扫描框")
        pick_row = row(selection)
        card_label(pick_row, "重新框选").pack(side="left")
        self.pick_key_button = ttk.Button(
            pick_row, text=self.settings["pick_hotkey_label"], width=17,
            command=lambda: self.begin_hotkey("pick_vk"))
        self.pick_key_button.pack(side="left", padx=(12, 12))
        self.pick_region_button = ttk.Button(
            pick_row, text="鼠标起点自由框选并识别", command=self.select_region)
        self.pick_region_button.pack(side="left")
        self.show_frame_var = tk.BooleanVar(value=self.settings["show_scan_frame"])
        self.show_frame_check = ttk.Checkbutton(
            selection, text="显示绿色扫描框",
            variable=self.show_frame_var, command=self.save_visual_settings)
        self.show_frame_check.pack(anchor="w")
        self.region_info_var = tk.StringVar(
            value=self.format_region(RelativeRegion.from_settings(self.settings["region"])))
        ttk.Label(selection, textvariable=self.region_info_var,
                  style="CardMuted.TLabel").pack(anchor="w", pady=(4, 0))

        timing = section(mouse, "执行与去重")
        timing_row = row(timing)
        card_label(timing_row, "OCR 周期（毫秒）").pack(side="left")
        self.period_var = tk.StringVar(value=str(self.settings["period_ms"]))
        self.period_entry = ttk.Entry(timing_row, textvariable=self.period_var, width=9)
        self.period_entry.pack(side="left", padx=(12, 10))
        self.period_save_button = ttk.Button(
            timing_row, text="保存", command=self.save_period)
        self.period_save_button.pack(side="left")
        repeat_row = row(timing, 4)
        self.similarity_enabled_var = tk.BooleanVar(
            value=self.settings["similarity_enabled"])
        self.similarity_check = ttk.Checkbutton(
            repeat_row, text="过滤相似的重复文字",
            variable=self.similarity_enabled_var, command=self.save_visual_settings)
        self.similarity_check.pack(side="left")
        card_label(repeat_row, "文本阈值").pack(side="left", padx=(26, 10))
        self.similarity_var = tk.StringVar(
            value=str(self.settings["similarity_threshold"]))
        self.similarity_spin = ttk.Spinbox(
            repeat_row, from_=0, to=8, width=5, increment=1,
            textvariable=self.similarity_var)
        self.similarity_spin.pack(side="left")
        self.similarity_spin.bind("<FocusOut>", self.save_similarity)
        self.similarity_spin.bind("<Return>", self.save_similarity)
        action_row = ttk.Frame(mouse)
        action_row.pack(fill="x", pady=(3, 0))
        self.reset_mouse_button = ttk.Button(
            action_row, text="恢复默认", command=self.reset_mouse_preferences)
        self.reset_mouse_button.pack(side="left")
        self.apply_mouse_button = ttk.Button(
            action_row, text="应用设置", style="Accent.TButton",
            command=self.apply_mouse_settings)
        self.apply_mouse_button.pack(side="right")

        fixed_page = self._pages["region"]
        region_choice = section(fixed_page, "固定区域")
        region_toolbar = row(region_choice, 4)
        self.region_pick_button = ttk.Button(
            region_toolbar, text="F11 重新框选", command=self.select_region)
        self.region_pick_button.pack(side="left")
        self.region_preview_var = tk.StringVar(value=self.format_fixed_region())
        ttk.Label(region_choice, textvariable=self.region_preview_var,
                  style="Card.TLabel").pack(anchor="w", pady=(4, 2))
        frame_row = row(region_choice, 4)
        self.frame_key_button = ttk.Button(
            frame_row, text=self.settings["frame_hotkey_label"], width=10,
            command=lambda: self.begin_hotkey("frame_vk"))
        self.frame_key_button.pack(side="left")
        ttk.Label(frame_row, text="显示／隐藏区域框", style="Card.TLabel").pack(
            side="left", padx=(12, 0))

        strategy = section(fixed_page, "识别方式")
        self.region_strategy_var = tk.StringVar(value=self.settings["region_strategy"])
        ttk.Radiobutton(
            strategy, text="画面变化时识别", value="change",
            variable=self.region_strategy_var,
            command=self.save_region_preferences).pack(anchor="w")
        ttk.Radiobutton(
            strategy, text="周期识别", value="period",
            variable=self.region_strategy_var,
            command=self.save_region_preferences).pack(anchor="w")
        period_row = row(strategy, 3)
        card_label(period_row, "周期（毫秒）").pack(side="left")
        self.region_period_var = tk.StringVar(value=str(self.settings["region_period_ms"]))
        self.region_period_entry = ttk.Entry(
            period_row, width=10, textvariable=self.region_period_var)
        self.region_period_entry.pack(side="left", padx=(10, 10))
        self.region_period_button = ttk.Button(
            period_row, text="保存", command=self.save_region_preferences)
        self.region_period_button.pack(side="left")

        border_settings = section(fixed_page, "边框")
        self.frame_enabled_var = tk.BooleanVar(value=self.settings["show_scan_frame"])
        self.frame_enabled_check = ttk.Checkbutton(
            border_settings, text="默认显示边框",
            variable=self.frame_enabled_var, command=self.save_frame_preferences)
        self.frame_enabled_check.pack(anchor="w")
        border_row = row(border_settings, 4)
        card_label(border_row, "颜色").pack(side="left")
        self.frame_color_var = tk.StringVar(value=self.color_display_name())
        self.frame_color_select = ttk.Combobox(
            border_row, width=9, state="readonly", textvariable=self.frame_color_var,
            values=["绿色", "蓝色", "黄色", "红色", "白色"])
        self.frame_color_select.pack(side="left", padx=(10, 16))
        self.frame_color_select.bind("<<ComboboxSelected>>", self.save_frame_preferences)
        card_label(border_row, "粗细").pack(side="left")
        self.frame_thickness_var = tk.StringVar(value=str(self.settings["frame_thickness"]))
        self.frame_thickness_spin = ttk.Spinbox(
            border_row, from_=1, to=8, width=4, textvariable=self.frame_thickness_var)
        self.frame_thickness_spin.pack(side="left", padx=(10, 0))
        self.frame_thickness_spin.bind("<FocusOut>", self.save_frame_preferences)
        self.frame_thickness_spin.bind("<Return>", self.save_frame_preferences)

        voice = self._pages["voice"]
        voice_frame = section(voice, "本地系统语音")
        card_label(voice_frame, "当前音色").pack(anchor="w")
        self.voice_var = tk.StringVar(value="正在扫描本地语音...")
        self.voice_select = ttk.Combobox(
            voice_frame, textvariable=self.voice_var, width=55, state="readonly")
        self.voice_select.pack(fill="x", pady=(8, 12))
        self.voice_select.bind("<<ComboboxSelected>>", self.change_voice)
        vr = row(voice_frame, 2)
        self.rescan_button = ttk.Button(
            vr, text="重新扫描语音", command=self.scan_voices)
        self.rescan_button.pack(side="left")
        self.preview_button = ttk.Button(vr, text="试听", command=self.test_voice)
        self.preview_button.pack(side="left", padx=(10, 0))
        self.stop_button = ttk.Button(vr, text="停止朗读", command=self.speech.stop)
        self.stop_button.pack(side="left", padx=(10, 0))
        self.voice_note = tk.StringVar(value="自然语音已安装不代表能合成；请在本机试听。")
        self.voice_note_label = ttk.Label(
            voice_frame, textvariable=self.voice_note,
            style="CardMuted.TLabel", wraplength=640)
        self.voice_note_label.pack(anchor="w", pady=(6, 4))
        self.import_luna_button = ttk.Button(
            voice_frame, text="选择本机原版语音配置", command=self.import_luna_config)
        self.import_luna_button.pack(anchor="w", pady=7)

        voice_controls = section(voice, "语速与音量")
        rate_row = row(voice_controls)
        card_label(rate_row, "语速").pack(side="left")
        self.rate_var = tk.IntVar(value=int(self.settings["rate"]))
        self.rate_slider = ttk.Scale(
            rate_row, from_=-8, to=8, variable=self.rate_var, command=self.change_rate)
        self.rate_slider.pack(side="left", fill="x", expand=True, padx=12)
        self.rate_label = ttk.Label(
            rate_row, text=str(self.rate_var.get()), width=4, style="Card.TLabel")
        self.rate_label.pack(side="left")
        volume_row = row(voice_controls)
        card_label(volume_row, "音量").pack(side="left")
        self.volume_var = tk.IntVar(value=int(self.settings["volume"]))
        self.volume_slider = ttk.Scale(
            volume_row, from_=0, to=100, variable=self.volume_var,
            command=self.change_volume)
        self.volume_slider.pack(side="left", fill="x", expand=True, padx=12)
        self.volume_label = ttk.Label(
            volume_row, text=f'{self.settings["volume"]}%', width=5,
            style="Card.TLabel")
        self.volume_label.pack(side="left")
        diag_row = row(voice_controls)
        self.voice_diag_button = ttk.Button(
            diag_row, text="复制语音诊断", command=self.copy_voice_report)
        self.voice_diag_button.pack(side="left")

        fullscreen = self._pages["fullscreen"]
        full_frame = section(fullscreen, "原版 V1.2 Small OCR")
        full_hotkey = row(full_frame)
        card_label(full_hotkey, "全屏 OCR 快捷键").pack(side="left")
        self.key_button = ttk.Button(
            full_hotkey, text=self.settings["hotkey_label"], width=16,
            command=self.capture_hotkey)
        self.key_button.pack(side="left", padx=(18, 0))
        self.read_btn = ttk.Button(
            full_frame, text="立即截屏识别", style="Accent.TButton",
            command=self.capture_from_button)
        self.read_btn.pack(anchor="w", pady=(16, 8))
        clear_row = row(full_frame)
        card_label(clear_row, "手动清空 OCR 结果").pack(side="left")
        self.clear_key_button = ttk.Button(
            clear_row, text=self.settings["clear_hotkey_label"], width=16,
            command=lambda: self.begin_hotkey("clear_vk"))
        self.clear_key_button.pack(side="left", padx=(18, 0))
        cue_row = row(full_frame, 4)
        self.success_cue_var = tk.BooleanVar(value=self.settings["success_cue"])
        self.success_cue_check = ttk.Checkbutton(
            cue_row, text="识别成功提示音",
            variable=self.success_cue_var, command=self.save_visual_settings)
        self.success_cue_check.pack(side="left")
        self.test_cue_button = ttk.Button(
            cue_row, text="试听叮声", command=self.test_cue)
        self.test_cue_button.pack(side="left", padx=(20, 0))

        filtering = self._pages["filters"]
        filter_frame = section(filtering, "朗读内容过滤")
        self.filter_english_var = tk.BooleanVar(value=self.settings["filter_english"])
        self.filter_numbers_var = tk.BooleanVar(value=self.settings["filter_numbers"])
        self.filter_symbols_var = tk.BooleanVar(value=self.settings["filter_symbols"])
        self.filter_english_check = ttk.Checkbutton(
            filter_frame, text="过滤英文（例如 DLSS、Press）",
            variable=self.filter_english_var, command=self.save_visual_settings)
        self.filter_english_check.pack(anchor="w", pady=8)
        self.filter_numbers_check = ttk.Checkbutton(
            filter_frame, text="过滤数字（例如 18、173）",
            variable=self.filter_numbers_var, command=self.save_visual_settings)
        self.filter_numbers_check.pack(anchor="w", pady=8)
        self.filter_symbols_check = ttk.Checkbutton(
            filter_frame, text="过滤符号（例如 +、% 、★）",
            variable=self.filter_symbols_var, command=self.save_visual_settings)
        self.filter_symbols_check.pack(anchor="w", pady=8)

        general = self._pages["general"]
        tools = section(general, "常用工具")
        tools_row = row(tools)
        ttk.Button(tools_row, text="最小化到任务栏",
                   command=self.root.iconify).pack(side="left")
        ttk.Button(tools_row, text="清除全部结果",
                   command=lambda: self.invalidate("已清除全部识别结果。")).pack(
                       side="left", padx=12)
        ttk.Button(tools_row, text="复制失败诊断",
                   command=self.copy_error).pack(side="left")

        about = self._pages["about"]
        details = section(about, "Blue Star OCR")
        note(details, "Windows 11 · V1.2.1 · PP-OCRv6 Small")

        footer = ttk.Frame(self.root, padding=(22, 10, 22, 14))
        footer.pack(side="bottom", fill="x")
        self.status_var = tk.StringVar(value="就绪。F9 切换工作模式，F11 可调整扫描宽高。")
        self.status_label = ttk.Label(
            footer, textvariable=self.status_var, style="Muted.TLabel",
            wraplength=1000)
        self.status_label.pack(anchor="w", pady=(0, 6))
        self.output = tk.Text(
            footer, wrap="word", height=3, state="disabled",
            font=("Microsoft YaHei UI", 13),
            background="#102C4B", foreground="#F2F7FF",
            selectbackground="#0E8AE8", relief="flat",
            padx=10, pady=8)
        self.output.pack(fill="x")
        self.show_page("mouse")

    def show_page(self, which: str):
        if which not in self._pages:
            raise ValueError("未知设置页")
        titles = {
            "mouse": "OCR 与鼠标",
            "region": "区域跟踪",
            "voice": "语音设置",
            "fullscreen": "全屏 OCR",
            "filters": "内容过滤",
            "general": "通用设置",
            "about": "关于软件",
        }
        for key, page in self._pages.items():
            if key == which:
                page.grid()
                page.tkraise()
            else:
                # Actual unmapping is critical: NVDA/Windows UIA must NOT
                # tab into controls from a page hidden underneath this one.
                page.grid_remove()
            self.nav_buttons[key].configure(
                style="Selected.Nav.TButton" if key == which else "Nav.TButton")
        self.page_title.set(titles[which])
        self.current_page = which

    def save_visual_settings(self):
        for name, variable in (
            ("show_scan_frame", self.show_frame_var),
            ("success_cue", self.success_cue_var),
            ("mode_voice_hint", self.mode_voice_var),
            ("similarity_enabled", self.similarity_enabled_var),
            ("filter_english", self.filter_english_var),
            ("filter_numbers", self.filter_numbers_var),
            ("filter_symbols", self.filter_symbols_var),
        ):
            self.settings[name] = bool(variable.get())
        if not self.settings["show_scan_frame"] and self.scan_frame is not None:
            self.scan_frame.hide()
        self.persist()

    def save_similarity(self, _event=None):
        from .text_filters import similarity_threshold
        try:
            value = similarity_threshold(self.similarity_var.get())
        except ValueError as exc:
            self.status(str(exc))
            self.similarity_var.set(str(self.settings["similarity_threshold"]))
            return
        self.settings["similarity_threshold"] = value
        self.persist()
        self.status(f"文本相似度阈值已设置为 {value}。")

    def set_mouse_mode(self, desired: str):
        if desired not in ("pointer", "hover"):
            raise ValueError("未知鼠标模式")
        if self.mouse_mode != desired:
            self.toggle_mouse_mode()

    def apply_mouse_settings(self):
        try:
            period = parse_period_ms(self.period_var.get())
            threshold = similarity_threshold(self.similarity_var.get())
        except ValueError as exc:
            self.status(str(exc))
            return False
        self.settings["period_ms"] = period
        self.settings["similarity_threshold"] = threshold
        self._hover_next_due = time.monotonic() + period / 1000.0
        self.save_visual_settings()
        self.status("设置已应用：鼠标扫描、去重、模式语音和边框设置已保存。")
        return True

    def reset_mouse_preferences(self):
        """Reset mouse *preferences*, not voice license, saved hotkeys or OCR."""
        self.period_var.set("400")
        self.similarity_var.set("2")
        self.mode_voice_var.set(True)
        self.show_frame_var.set(True)
        self.similarity_enabled_var.set(True)
        self.settings["region"] = centered_region(
            RelativeRegion.from_settings(DEFAULT_REGION)).as_list()
        self.region_info_var.set(self.format_region(
            RelativeRegion.from_settings(self.settings["region"])))
        self.apply_mouse_settings()

    def enable_accessibility(self):
        """Name native controls for Windows UIA; fail explicit self-test if lost."""
        try:
            import tk_uia
            result = tk_uia.enable(self.root)
            targets = [
                (self.key_button, "全屏 OCR 截图快捷键"),
                (self.mouse_mode_button, "切换到鼠标模式"),
                (self.default_mode_button, "切换到默认模式"),
                (self.apply_mouse_button, "应用并保存鼠标 OCR 设置"),
                (self.reset_mouse_button, "恢复鼠标设置默认值，不清除语音授权"),
                (self.mode_key_button, "切换默认模式和鼠标模式的快捷键"),
                (self.local_key_button, "立即识别鼠标附近文字的快捷键"),
                (self.pick_key_button, "全局从鼠标位置开始自由拖框的快捷键"),
                (self.clear_key_button, "手动立即清空识别结果的快捷键"),
                (self.success_cue_check, "识别成功提示音开关"),
                (self.test_cue_button, "试听识别成功的金属叮声，不启动 OCR"),
                (self.period_entry, "鼠标局部 OCR 周期，单位毫秒"),
                (self.period_save_button, "保存局部 OCR 周期"),
                (self.similarity_check, "启用重复文本相似度过滤"),
                (self.similarity_spin, "文本相似度阈值零到八"),
                (self.show_frame_check, "显示跟随鼠标的绿色扫描框"),
                (self.mode_voice_check, "切换模式时说出鼠标模式或默认模式"),
                (self.pick_region_button, "从鼠标当前位置暗屏拖框并立即识别"),
                (self.voice_select, "选择本机微软云希晓晓或其他语音"),
                (self.rescan_button, "重新扫描本机语音"),
                (self.preview_button, "试听当前选中语音"),
                (self.stop_button, "立即停止朗读"),
                (self.voice_diag_button, "复制语音诊断"),
                (self.import_luna_button, "选择本机原版语音配置"),
                (self.rate_slider, "调整朗读语速"),
                (self.volume_slider, "调整朗读音量"),
                (self.read_btn, "立即截图进行原版全屏 OCR"),
                (self.filter_english_check, "过滤英文字母，开关"),
                (self.filter_numbers_check, "过滤数字，开关"),
                (self.filter_symbols_check, "过滤符号，开关"),
                (self.output, "最近一次 OCR 识别结果，原文"),
                (self.status_label, "当前工作模式和 OCR 状态"),
            ]
            for key, label in (
                ("mouse", "进入 OCR 与鼠标设置"),
                ("voice", "进入语音设置"),
                ("fullscreen", "进入全屏 OCR 设置"),
                ("filters", "进入内容过滤设置"),
                ("general", "进入通用设置"),
                ("about", "进入关于软件"),
            ):
                targets.append((self.nav_buttons[key], label))
            for widget, label in targets:
                if not widget.winfo_exists():
                    raise RuntimeError("控件不存在：" + label)
                tk_uia.set_acc_name(widget, label)
            self.accessibility_targets = targets
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
        self.begin_hotkey("vk")

    def begin_hotkey(self, field: str):
        if self._choosing_region:
            return
        if self.setting_hotkey:
            self.finish_hotkey()
        self.setting_hotkey = True
        self._binding_target = field
        self._hotkey_button(field).configure(text="请按键／侧键")
        self._side_previous = {vk: is_key_down(vk) for vk in MOUSE_SIDE_VKS}
        self.root.bind("<KeyPress>", self.accept_key)
        self.root.focus_force()
        self.status("按键盘单键或鼠标侧键1/2进行设置；Esc 取消。")

    def _hotkey_button(self, field: str):
        return {"vk": self.key_button, "mode_vk": self.mode_key_button,
                "local_vk": self.local_key_button,
                "pick_vk": self.pick_key_button,
                "clear_vk": self.clear_key_button}[field]

    def finish_hotkey(self):
        target = self._binding_target
        self.setting_hotkey = False
        self._binding_target = None
        self.root.unbind("<KeyPress>")
        if target:
            label = HOTKEY_LABELS[HOTKEY_FIELDS.index(target)]
            self._hotkey_button(target).configure(text=self.settings[label])

    def accept_key(self, event):
        if event.keysym == "Escape":
            self.finish_hotkey()
            self.status("已取消快捷键设置。")
            return "break"
        try:
            vk = int(event.keycode)
        except (TypeError, ValueError):
            return "break"
        self._apply_hotkey(vk, event.keysym)
        return "break"

    def _apply_hotkey(self, vk: int, keyname: str = "") -> bool:
        if not valid_hotkey(vk) or self._binding_target is None:
            self.status("仅接受键盘单键或两枚标准鼠标侧键；不接受左／右点击和修饰键。")
            return False
        field = self._binding_target
        for other in HOTKEY_FIELDS:
            if other != field and self.settings[other] == vk:
                self.status("该按键已用于其他功能，请换一个不冲突的键。")
                return False
        label_field = HOTKEY_LABELS[HOTKEY_FIELDS.index(field)]
        label = hotkey_label(vk, keyname)
        self.settings[field] = vk
        self.settings[label_field] = label
        if field == "mode_vk" and self.mouse_mode == "pointer":
            self.mouse_mode_var.set(f"当前：默认鼠标指向朗读（{label} 切换）")
        self._hotkey_previous[field] = True
        self.finish_hotkey()
        self.persist()
        self.status(f"快捷键已设为：{label}")
        return True

    def _capture_mouse_hotkey(self):
        # Tk KeyPress excludes XBUTTON1/XBUTTON2. Use the same native
        # Windows virtual-key state reader as the actual hotkey dispatcher.
        for vk in MOUSE_SIDE_VKS:
            down = is_key_down(vk)
            old = self._side_previous.get(vk, down)
            self._side_previous[vk] = down
            if down and not old and self.setting_hotkey:
                self._apply_hotkey(vk, hotkey_label(vk))
                return

    @staticmethod
    def format_region(region: RelativeRegion) -> str:
        return (f"鼠标相对扫描：{region.width} × {region.height} 像素；"
                f"水平偏移 {region.x:+d}，垂直偏移 {region.y:+d}。"
                "按 F11 从当前鼠标位置任意方向拉框，松开立即识别。")

    def save_period(self):
        try:
            period = parse_period_ms(self.period_var.get())
        except ValueError as exc:
            self.status(str(exc))
            return
        self.settings["period_ms"] = period
        self._hover_next_due = time.monotonic() + period / 1000.0
        self.persist()
        self.status(f"悬停 OCR 周期已设为 {period} 毫秒。")

    def select_region(self):
        """Global F11 can open a picker while an unrelated game is foreground.

        Keep root technically viewable but invisible. Tk child Toplevels of
        withdrawn/minimized roots can fail to map on Windows, which caused
        'works once, never again'. Restore the exact previous root state.
        """
        if self._choosing_region or self.closed:
            return
        if self.setting_hotkey:
            self.finish_hotkey()
        try:
            anchor = get_cursor()
            monitor = monitor_rect_at_cursor()
        except Exception as exc:
            self.status("无法获取显示器尺寸：" + type(exc).__name__)
            return
        self._picker_anchor = anchor
        self._picker_monitor = monitor
        self._picker_snapshot = None
        self._picker_foreground = foreground_window_id()
        self._choosing_region = True
        if getattr(self, "scan_frame", None) is not None:
            self.scan_frame.hide()
        # Cancel old queued OCR/audio before putting the selection overlay
        # on screen. Any image already being processed must be discarded.
        self.mode_generation += 1
        self._hover_last_text = ""
        self._hover_spoken_cursor = None
        self.speech.stop()
        self._region_previous_root_state = self.root.state()
        try:
            self.root.deiconify()
            self.root.attributes("-alpha", 0.0)
            self.root.update_idletasks()
            self.root.after(10, lambda: self._open_region_picker(monitor))
        except tk.TclError:
            self._region_picked(None)
            self.status("无法进入暗屏框选；窗口状态恢复。")

    def _open_region_picker(self, monitor):
        if self.closed or not self._choosing_region:
            return
        try:
            background = None
            try:
                if self.overlay is not None:
                    self.overlay.hide()
                # Screenshot before opening the picker, with our main UI
                # already invisible. No photo is stored or uploaded.
                background = ImageGrab.grab(bbox=monitor, all_screens=True)
            except Exception:
                pass  # Fall back to a semi-transparent overlay if capture fails.
            self._picker_snapshot = background
            self._region_picker = ScreenRegionPicker(
                self.root, monitor,
                RelativeRegion.from_settings(self.settings["region"]),
                self._region_picked, background=background,
                anchor=(self._picker_anchor[0] - monitor[0],
                        self._picker_anchor[1] - monitor[1]))
            self._region_picker.lift()
        except Exception as exc:
            self._region_picked(None)
            self.status("暗屏框选初始化失败：" + type(exc).__name__)

    def _region_picked(self, region: RelativeRegion | None):
        snapshot = getattr(self, "_picker_snapshot", None)
        monitor = getattr(self, "_picker_monitor", None)
        anchor = getattr(self, "_picker_anchor", None)
        focus = getattr(self, "_picker_foreground", None)
        self._picker_snapshot = None  # Raw screenshot lives in RAM only.
        self._region_picker = None
        self._choosing_region = False
        if self.closed:
            return
        try:
            self.root.attributes("-alpha", 1.0)
            if self._region_previous_root_state in ("iconic", "withdrawn"):
                self.root.iconify()
            else:
                self.root.deiconify()
        except tk.TclError:
            pass
        if region is None:
            self.status("框选已取消，原识别区域未改变。")
        else:
            self.settings["region"] = region.as_list()  # All four drag directions.
            self.region_info_var.set(self.format_region(region))
            self._hover_last_text = ""
            self._hover_spoken_cursor = None
            self.persist()
            if anchor is not None and monitor is not None:
                self._start_selected_ocr(region, anchor, monitor, snapshot, focus)
        self._hover_next_due = time.monotonic() + self.settings["period_ms"] / 1000.0

    def _start_selected_ocr(self, region: RelativeRegion, anchor, monitor,
                            snapshot, focus):
        """Recognize exactly the selected pixels as soon as the button is released.

        Reuse the original undimmed screenshot. No extra 250ms UI delay,
        no second screenshot and no model change.
        """
        try:
            box = capture_box(region, anchor, monitor)
        except ValueError as exc:
            self.status("框选区域无效：" + str(exc))
            return
        self.invalidate("框选已确认，正在识别文字…")
        request_id = self.capture_id
        self.busy = True
        self.read_btn.configure(state="disabled")

        def work():
            started = time.monotonic()
            try:
                if snapshot is not None:
                    ml, mt = monitor[:2]
                    image = snapshot.crop((box[0]-ml, box[1]-mt,
                                           box[2]-ml, box[3]-mt))
                else:
                    image = ImageGrab.grab(bbox=box, all_screens=True)
                capture_ms = round((time.monotonic() - started) * 1000)
                if image.size != (box[2]-box[0], box[3]-box[1]):
                    raise RuntimeError("框选截图尺寸与实际识别区域不一致")
                with self._ocr_lock:
                    lines = self.ocr_worker.recognize(image, box[:2], "small")
                infer_ms = round((time.monotonic() - started) * 1000) - capture_ms
                self.events.put(("ocr_ok", request_id, lines,
                                 round((time.monotonic() - started) * 1000),
                                 focus, "selection", (capture_ms, infer_ms)))
            except Exception:
                self.events.put(("ocr_fail", request_id, traceback.format_exc()))
        threading.Thread(target=work, daemon=True,
                         name="DragSelectionSmallOCR").start()

    def toggle_mouse_mode(self):
        # Startup already defaults to V1.2 pointer mode. Every press MUST
        # switch, including the first F9 after launching the program.
        self.mouse_mode = next_mouse_mode(self.mouse_mode)
        self.mode_generation += 1
        self._hover_last_text = ""
        self._hover_spoken_cursor = None
        self._hover_spoken_foreground = None
        self.hover.reset()
        self.last_target = None
        self.speech.stop()
        if self.overlay is not None:
            self.overlay.hide()
        if getattr(self, "scan_frame", None) is not None:
            self.scan_frame.hide()
        # Announcements are sent unfiltered, through the already-selected
        # voice. Reserve enough time before OCR can interrupt the short cue.
        announce = bool(self.settings.get("mode_voice_hint", True))
        self._mode_announcement_until = (
            time.monotonic() + 1.6 if announce else 0.0)
        if self.mouse_mode == "hover":
            self.mouse_mode_var.set("当前：鼠标模式（局部 OCR）")
            self._hover_next_due = max(
                time.monotonic() + 0.35, self._mode_announcement_until)
            if self.root.state() == "normal":
                self.root.iconify()
            self.status("已进入鼠标模式；局部扫描框跟随鼠标。")
            if announce:
                self.speak_selected("鼠标模式")
        else:
            self.mouse_mode_var.set("当前：默认模式（全屏 OCR 文字指向朗读）")
            self._hover_next_due = float("inf")
            self.update_output("\n".join(line.text for line in self.lines))
            self.status("已切换到默认模式。")
            if announce:
                self.speak_selected("默认模式")

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

    def test_cue(self):
        """Playback test works independently of the success-cue enable switch."""
        self.cues.play("complete")
        self.status("正在试听提示音；如果无声，请检查 Windows 音量混合器。")

    def copy_voice_report(self):
        report = (self.voice_report + "\n语音速度诊断：" + self.last_voice_timing +
                  "\nUI Automation: " + self.accessibility_status)
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

    def start_hover_ocr(self, manual: bool = False):
        """One mouse-relative screenshot; do not queue overlapping OCR jobs."""
        if (self.closed or self._choosing_region or self.mouse_mode != "hover"):
            if manual and self.mouse_mode != "hover":
                self.status("请先用模式快捷键切换到鼠标悬停 OCR。")
            return False
        if self.busy or self.hover_ocr_busy or self.pending_full_capture:
            if manual:
                self.status("OCR 正在处理上一张图；本次不排队。")
            return False
        if self.root.state() == "normal":
            if manual:
                self._hover_next_due = time.monotonic() + 1.0
                self.root.iconify()
                self.root.after(260, lambda: self.start_hover_ocr(True))
            return False
        try:
            cursor = get_cursor()
            captured_window = foreground_class()
            monitor = monitor_rect_at_cursor()
            # Preserve mouse-relative x/y offset chosen with F11.
            relative = RelativeRegion.from_settings(self.settings["region"])
            box = capture_box(relative, cursor, monitor)
        except Exception as exc:
            self.status("局部 OCR 截图区域错误：" + type(exc).__name__)
            return False

        self.hover_ocr_busy = True
        generation = self.mode_generation
        self._hover_next_due = time.monotonic() + self.settings["period_ms"] / 1000.0

        def work():
            started = time.monotonic()
            try:
                image = ImageGrab.grab(bbox=box, all_screens=True)
                capture_ms = round((time.monotonic() - started) * 1000)
                if image.size != (box[2] - box[0], box[3] - box[1]):
                    raise RuntimeError("局部截图尺寸与显示器范围不一致")
                with self._ocr_lock:
                    lines = self.ocr_worker.recognize(image, box[:2], "small")
                infer_ms = round((time.monotonic() - started) * 1000) - capture_ms
                self.events.put(("hover_ok", generation, lines, manual,
                                 round((time.monotonic() - started) * 1000),
                                 cursor, captured_window, (capture_ms, infer_ms)))
            except Exception:
                self.events.put(("hover_fail", generation,
                                 traceback.format_exc()))
        threading.Thread(target=work, daemon=True, name="MouseRegionSmallOCR").start()
        return True

    def _handle_hover_result(self, generation: int, lines: list[OCRLine],
                             manual: bool, elapsed: int,
                             capture_cursor=None, capture_foreground=None,
                             timings=None):
        self.hover_ocr_busy = False
        # Start-to-start interval: slow inference should not add another full
        # period before a fresh scan. 60ms prevents a tight CPU spin.
        self._hover_next_due = max(getattr(self, "_hover_next_due", 0.0),
                                   time.monotonic() + 0.06)
        if self.pending_full_capture:
            self.pending_full_capture = False
            self.capture()
            return
        if generation != self.mode_generation or self.mouse_mode != "hover":
            return
        if capture_cursor is not None:
            if (not cursor_still_near_capture(capture_cursor, get_cursor()) or
                    foreground_class() != capture_foreground):
                # Do not read a tooltip whose cursor has already left its
                # location before OCR finishes. A new frame can catch up.
                self._hover_last_text = ""
                return
        # The user wants the ORIGINAL V1.2 full-screen OCR reading logic,
        # only on a smaller pointer-centred screenshot. Do not rank by mouse
        # distance, do not guess which UI element is a game tooltip.
        raw = "\n".join(region.text for region in build_reading_regions(lines)).strip()
        speech_text = filter_speech_text(raw, self.settings)
        normalized = normalized_text(speech_text)
        repeated = is_repeat_speech(self._hover_last_text, normalized, self.settings)
        if not normalized:
            if self._hover_last_text or self._hover_spoken_cursor is not None:
                self.speech.stop()
                self._hover_spoken_cursor = None
                self._hover_spoken_foreground = None
            self._hover_last_text = ""
            self.update_output(raw)
            if manual:
                self.status("局部 OCR 没有可朗读文字；可在内容过滤中调整。")
            return
        if not repeated or manual:
            # The selected TTS engine already replaces its previous utterance.
            # Avoid adding a redundant stop ahead of each fresh mouse text.
            self.update_output(raw)  # Accessible raw OCR stays untouched.
            self._hover_last_text = normalized
            self._hover_spoken_cursor = capture_cursor
            self._hover_spoken_foreground = capture_foreground
            self.speak_selected(speech_text[:1900])
            timing_note = (f"（截图 {timings[0]} / 推理 {timings[1]} 毫秒）"
                           if timings is not None else "")
            self.status(f"局部 OCR 扫描 {len(lines)} 行，"
                        f"{elapsed} 毫秒{timing_note}；"
                        + ("手动重新朗读。" if manual else "新文字已朗读。"))

    def invalidate(self, reason: str):
        """Actually erase all text, coordinates, hover state and audio."""
        self.capture_id += 1
        # A canceled worker's late event is ignored. Release the UI busy flag
        # NOW or a clear-key press during OCR could disable future captures.
        self.busy = False
        if hasattr(self, "read_btn"):
            self.read_btn.configure(state="normal")
        self.mode_generation += 1  # Stale hover OCR must not revive erased text.
        self.pending_full_capture = False
        self._hover_last_text = ""
        self.expires_at = None
        self.lines = []
        self._full_capture_window = None
        self.last_target = None
        self._hover_spoken_cursor = None
        self._hover_spoken_foreground = None
        self.hover.reset()
        self.speech.stop()
        # A clear action must also discard ephemeral spoken-text audio cache.
        getattr(self.speech, "clear_cache", lambda: None)()
        if self.overlay is not None:
            self.overlay.hide()
        self.update_output("")
        self.status(reason)

    def clear_results(self):
        """Immediate manual clear; 60-second automatic expiry remains active."""
        self.invalidate("已手动清空识别结果和朗读；可重新截图。")

    def capture_from_button(self):
        self.root.iconify()
        self.root.after(250, self.capture)

    def capture(self):
        if self.hover_ocr_busy:
            # A manual full-screen hotkey takes precedence over periodic OCR.
            # Keep at most one pending full capture and never share an active
            # RapidOCR instance across simultaneous worker threads.
            self.pending_full_capture = True
            self.status("局部 OCR 正在结束；随后执行全屏截图（不排队）。")
            return
        if self.busy:
            return
        self.pending_full_capture = False
        self.invalidate("正在识别新画面...")
        capture_id = self.capture_id
        self.busy = True
        self.read_btn.configure(state="disabled")
        tier = self.settings["tier"]

        def worker():
            started = time.monotonic()
            phase = "截图"
            try:
                focus = foreground_window_id()
                image, origin = grab_current_monitor()
                capture_ms = round((time.monotonic() - started) * 1000)
                phase = f"离线OCR推理（{tier}）"
                with self._ocr_lock:
                    lines = self.ocr_worker.recognize(image, origin, tier)
                infer_ms = round((time.monotonic() - started) * 1000) - capture_ms
                self.events.put(("ocr_ok", capture_id, lines,
                                 round((time.monotonic() - started) * 1000),
                                 focus, "fullscreen", (capture_ms, infer_ms)))
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
                    _, capture_id, lines, milliseconds, focus, *extra = event
                    if capture_id != self.capture_id:
                        continue
                    self.busy = False
                    self.read_btn.configure(state="normal")
                    source = extra[0] if extra else "fullscreen"
                    timings = extra[1] if len(extra) > 1 else None
                    self.lines = build_reading_regions(lines)
                    self._full_capture_window = focus
                    self.hover.reset()
                    self.last_target = None
                    self.update_output("\n".join(region.text for region in self.lines))
                    if self.lines:
                        self.expires_at = time.monotonic() + RESULT_TTL_SECONDS
                    timing_note = (f"（截图 {timings[0]} / 推理 {timings[1]} 毫秒）"
                                   if timings is not None else "")
                    self.status(f"识别完成：{len(self.lines)} 个朗读区域；"
                                f"耗时 {milliseconds} 毫秒{timing_note}。"
                                "60 秒后自动清空。")
                    speakable = filter_speech_text(
                        "\n".join(region.text for region in self.lines), self.settings)
                    if (self.mouse_mode == "pointer"
                            and self.settings.get("success_cue", True)):
                        if speakable:
                            self.cues.play("complete")
                        elif self.lines:
                            self.status("识别到文字，但被内容过滤全部排除；未播放成功提示音。")
                    if source == "selection" and self.mouse_mode == "hover":
                        spoken = filter_speech_text(
                            "\n".join(line.text for line in self.lines), self.settings)
                        if spoken:
                            self.speak_selected(spoken[:1900])
                elif kind == "ocr_fail":
                    _, capture_id, detail = event
                    if capture_id != self.capture_id:
                        continue
                    self.busy = False
                    self.read_btn.configure(state="normal")
                    self.last_ocr_error = detail
                    try:
                        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                        ERROR_LOG.write_text(detail[-24000:], encoding="utf-8")
                    except OSError:
                        pass
                    self.status("识别失败。点击“复制失败诊断”查看错误。")
                    self.update_output("识别失败。")
                elif kind == "hover_ok":
                    _, generation, lines, manual, milliseconds, location, window_class, *extra = event
                    self._handle_hover_result(generation, lines, manual, milliseconds,
                                              location, window_class,
                                              extra[0] if extra else None)
                elif kind == "hover_fail":
                    _, generation, detail = event
                    self.hover_ocr_busy = False
                    self._hover_next_due = (time.monotonic() +
                                            max(1.0, self.settings["period_ms"] / 1000.0))
                    if self.pending_full_capture:
                        self.pending_full_capture = False
                        self.capture()
                    elif generation == self.mode_generation and self.mouse_mode == "hover":
                        self.last_ocr_error = detail
                        self.status("局部 OCR 失败。点击「复制失败诊断」查看。")
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
                elif kind == "tts_timing":
                    self.last_voice_timing = event[1]
                    self.status("语音速度诊断：" + event[1])
                elif kind == "tts_error":
                    self.status("TTS 出错：" + event[1])
                elif kind == "cue_error":
                    self.status("提示音播放异常：" + event[1])
                elif kind == "ui_error":
                    self.status("无障碍接口初始化异常：" + event[1])
        except Empty:
            pass
        self.root.after(40, self.poll_messages)

    def update_scan_frame(self):
        """Show the REAL cursor-centred capture rectangle, without stealing focus.

        Four small native transparent border windows remain OUTSIDE the
        captured pixels, so the green guide cannot contaminate OCR.
        """
        if self.scan_frame is None:
            return
        if (self._choosing_region or self.setting_hotkey
                or self.root.state() == "normal"
                or not self.settings.get("show_scan_frame", True)):
            self.scan_frame.hide()
            return
        try:
            cursor = get_cursor()
            monitor = monitor_rect_at_cursor()
            region = RelativeRegion.from_settings(self.settings["region"])
            left, top, right, bottom = capture_box(region, cursor, monitor)
            self.scan_frame.show(
                OCRLine("扫描框", left, top, right, bottom))
        except Exception:
            self.scan_frame.hide()

    def poll_input(self):
        if self.closed:
            return
        try:
            if self.setting_hotkey:
                self._capture_mouse_hotkey()
                # Holding a newly recorded side button must not immediately
                # trigger the just assigned action on the next polling frame.
                for field in HOTKEY_FIELDS:
                    self._hotkey_previous[field] = is_key_down(self.settings[field])
            elif not self._choosing_region:
                for field in HOTKEY_FIELDS:
                    vk = self.settings[field]
                    down = is_key_down(vk)
                    old = self._hotkey_previous.get(field, down)
                    self._hotkey_previous[field] = down
                    if not down or old:
                        continue
                    if field == "vk":
                        if self.root.state() == "normal":
                            self.capture_from_button()
                        else:
                            self.capture()
                    elif field == "mode_vk":
                        self.toggle_mouse_mode()
                    elif field == "local_vk":
                        self.start_hover_ocr(manual=True)
                    elif field == "pick_vk":
                        self.select_region()
                    elif field == "clear_vk":
                        self.clear_results()

            if self.expires_at is not None and time.monotonic() >= self.expires_at:
                if self.mouse_mode == "pointer":
                    self.invalidate("本次全屏 OCR 结果已满 60 秒，请重新截图。")
                else:
                    # The old pointer cache expires independently of a
                    # newly spoken hover tooltip. Do not cut off hover audio.
                    self.lines = []
                    self.expires_at = None

            if self._choosing_region or self.setting_hotkey:
                pass
            elif (self.mouse_mode == "pointer" and not self.busy and self.lines
                  and time.monotonic() >= getattr(self, "_mode_announcement_until", 0.0)):
                # No scene-change detector. Simply discard a screenshot when
                # the user has switched to another actual Windows window.
                if (self._full_capture_window and
                        foreground_window_id() != self._full_capture_window):
                    self.invalidate("检测到窗口切换，旧 OCR 坐标已清除；按全屏键重新截图。")
                else:
                    x, y = get_cursor()
                    target = hit_test(self.lines, x, y)
                    if target != self.last_target:
                        if self.overlay is not None:
                            self.overlay.show(target)
                        if self.last_target is not None and target is None:
                            self.speech.stop()  # Leaving text stops playback.
                        self.last_target = target
                    to_read = self.hover.update(target, time.monotonic() * 1000)
                    if to_read is not None:
                        spoken = filter_speech_text(to_read.text, self.settings)
                        if spoken:
                            self.speak_selected(spoken)
                        else:
                            self.speech.stop()  # New region was filtered empty.
            elif self.mouse_mode == "hover":
                self.update_scan_frame()
                if self._hover_spoken_cursor is not None:
                    moved = not cursor_still_near_capture(
                        self._hover_spoken_cursor, get_cursor())
                    focus_changed = (self._hover_spoken_foreground is not None and
                                     foreground_class() != self._hover_spoken_foreground)
                    if moved or focus_changed:
                        self.speech.stop()
                        self._hover_spoken_cursor = None
                        self._hover_last_text = ""
                if (not self.busy and time.monotonic() >= self._hover_next_due
                        and time.monotonic() >= self._mode_announcement_until):
                    self.start_hover_ocr(manual=False)
        except Exception as exc:
            self.status("鼠标／快捷键监听异常：" + str(exc))
        self.root.after(20, self.poll_input)

    def close(self):
        self.closed = True
        if self._region_picker is not None:
            try:
                self._region_picker.cancel()
            except tk.TclError:
                pass
        self.speech.shutdown()
        self.cues.shutdown()
        if getattr(self, "scan_frame", None) is not None:
            self.scan_frame.close()
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
