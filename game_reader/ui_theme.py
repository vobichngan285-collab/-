"""Accessible native-Tk blue palette: visual styling only, no custom UI controls.

All interactive widgets remain ttk.Button/Checkbutton/Entry/Combobox/Scale.
Use ttk rather than painting buttons into a Canvas or image, because Windows
UI Automation and keyboard focus must retain the original control semantics.
"""
from __future__ import annotations

from tkinter import ttk

BG = "#081C37"
SIDEBAR = "#061A33"
CARD = "#112B4B"
INPUT = "#193A5F"
HOVER = "#17436B"
ACCENT = "#0E8AE8"
GREEN = "#74D998"
TEXT = "#F2F7FF"
MUTED = "#C3D6E9"
FONT = ("Microsoft YaHei UI", 13)
LARGE = ("Microsoft YaHei UI", 18, "bold")


def configure_theme(root):
    root.configure(background=BG)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(".", font=FONT, background=BG, foreground=TEXT)
    style.configure("TFrame", background=BG)
    style.configure("Sidebar.TFrame", background=SIDEBAR)
    style.configure("Card.TFrame", background=CARD)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Card.TLabel", background=CARD, foreground=TEXT)
    style.configure("Muted.TLabel", background=BG, foreground=MUTED)
    style.configure("CardMuted.TLabel", background=CARD, foreground=MUTED)
    style.configure("Heading.TLabel", font=("Microsoft YaHei UI", 22, "bold"),
                    background=BG, foreground=TEXT)
    style.configure("Subheading.TLabel", font=LARGE, background=BG, foreground=TEXT)
    style.configure("Sidebar.TLabel", background=SIDEBAR, foreground=TEXT,
                    font=("Microsoft YaHei UI", 18, "bold"))
    style.configure("TButton", font=FONT, padding=(12, 8),
                    background=INPUT, foreground=TEXT, bordercolor=HOVER,
                    borderwidth=1, relief="flat")
    style.map("TButton", background=[("active", ACCENT), ("pressed", ACCENT)],
              foreground=[("disabled", MUTED)])
    style.configure("Accent.TButton", background=ACCENT, foreground=TEXT,
                    font=("Microsoft YaHei UI", 14, "bold"),
                    padding=(16, 10))
    style.map("Accent.TButton", background=[("active", "#39A7FF")])
    style.configure("Nav.TButton", background=SIDEBAR,
                    foreground=TEXT, anchor="w", padding=(14, 14),
                    font=("Microsoft YaHei UI", 15, "bold"),
                    borderwidth=0)
    style.map("Nav.TButton", background=[("active", HOVER)])
    style.configure("Selected.Nav.TButton", background=ACCENT,
                    foreground="#FFFFFF", anchor="w", padding=(14, 14),
                    font=("Microsoft YaHei UI", 15, "bold"), borderwidth=0)
    style.map("Selected.Nav.TButton", background=[("active", "#369FF4")])
    style.configure("TCheckbutton", background=CARD, foreground=TEXT,
                    font=FONT, padding=(5, 7))
    style.map("TCheckbutton", background=[("active", CARD)],
              foreground=[("disabled", MUTED)])
    style.configure("TEntry", fieldbackground=INPUT, foreground=TEXT,
                    insertcolor=TEXT, padding=(8, 7))
    style.configure("TCombobox", fieldbackground=INPUT, background=INPUT,
                    foreground=TEXT, arrowcolor=TEXT, padding=(7, 7))
    style.map("TCombobox", fieldbackground=[("readonly", INPUT)],
              foreground=[("readonly", TEXT)])
    style.configure("TSpinbox", fieldbackground=INPUT, foreground=TEXT,
                    arrowsize=14, padding=(5, 6))
    style.configure("TScale", background=CARD)
    style.configure("TLabelframe", background=CARD, bordercolor="#31597B",
                    borderwidth=1, relief="solid")
    style.configure("TLabelframe.Label", font=("Microsoft YaHei UI", 14, "bold"),
                    background=CARD, foreground=TEXT)
    return style
