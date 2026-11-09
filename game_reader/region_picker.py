"""Darkened full-monitor picker anchored to the user's physical mouse position.

Drag in any direction. Selected offsets are retained for the cursor-following
green guide, and releasing the mouse confirms the exact rectangle to OCR.
"""
from __future__ import annotations

import tkinter as tk
from PIL import ImageEnhance, ImageTk

from .hover_modes import RelativeRegion, region_from_drag


class ScreenRegionPicker(tk.Toplevel):
    def __init__(self, root: tk.Tk, monitor: tuple[int, int, int, int],
                 initial: RelativeRegion, on_done, background=None, anchor=None):
        super().__init__(root, bg="#10151d")
        self._done = on_done
        self._finished = False
        self._start = None
        self._selection = None
        self._monitor = monitor
        left, top, right, bottom = monitor
        self._width = right - left
        self._height = bottom - top
        self._anchor = ((self._width // 2, self._height // 2)
                        if anchor is None else
                        (max(0, min(self._width, int(anchor[0]))),
                         max(0, min(self._height, int(anchor[1])))))
        self.overrideredirect(True)
        self.geometry(f"{self._width}x{self._height}{left:+d}{top:+d}")
        self.attributes("-topmost", True)
        self.attributes("-alpha", 1.0 if background is not None else 0.52)
        self.canvas = tk.Canvas(
            self, width=self._width, height=self._height, bg="#111722",
            highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self._background_photo = None
        if background is not None:
            # Like a normal screenshot rectangle selector: darken the frozen
            # captured monitor instead of relying on live alpha compositing
            # over DirectX games. Keep the image in RAM only, never on disk.
            background = background.convert("RGB")
            if background.size != (self._width, self._height):
                raise ValueError("框选背景与屏幕尺寸不一致")
            dimmed = ImageEnhance.Brightness(background).enhance(0.36)
            self._background_photo = ImageTk.PhotoImage(dimmed, master=self)
            self.canvas.create_image(0, 0, image=self._background_photo,
                                     anchor="nw", tags="background")

        self.canvas.create_text(
            self._width // 2, 28,
            text="十字是当前鼠标位置｜按住左键往任意方向拖动，松开立即识别｜Esc 取消",
            fill="white", font=("Microsoft YaHei UI", 13, "bold"),
            tags="hint")
        self.canvas.create_text(
            self._width // 2, 56,
            text="支持左上、右上、左下、右下任意方向；保存偏移并与绿色框对应",
            fill="#9fdefa", font=("Microsoft YaHei UI", 10), tags="hint")

        ax, ay = self._anchor
        self.canvas.create_line(ax - 19, ay, ax + 19, ay,
                                fill="#fbfbfb", width=2, tags="anchor")
        self.canvas.create_line(ax, ay - 19, ax, ay + 19,
                                fill="#fbfbfb", width=2, tags="anchor")
        self.canvas.create_oval(ax - 3, ay - 3, ax + 3, ay + 3,
                                outline="#50d5ff", width=2, tags="anchor")
        self.canvas.create_text(ax + 10, ay + 28, text="按快捷键时的鼠标位置",
                                fill="#fbfbfb", anchor="nw", tags="anchor")
        self._draw_rectangle(ax + initial.x, ay + initial.y,
                             ax + initial.x + initial.width,
                             ay + initial.y + initial.height,
                             dashed=True)

        self.canvas.bind("<ButtonPress-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._finish_drag)
        self.bind("<Escape>", lambda _event: self.cancel())
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.lift()
        self.after(20, self._activate)
        self.after(160, self._activate)

    def _activate(self):
        if self._finished:
            return
        try:
            self.attributes("-topmost", True)
            self.lift()
            self.focus_force()
            if self.grab_current() is None:
                self.grab_set()
        except tk.TclError:
            pass

    def _coords(self, event) -> tuple[int, int]:
        return (max(0, min(self._width, int(event.x))),
                max(0, min(self._height, int(event.y))))

    def _draw_rectangle(self, x1, y1, x2, y2, dashed=False):
        self.canvas.delete("selection")
        self.canvas.create_rectangle(
            x1, y1, x2, y2, outline="#56e3ff", width=3,
            dash=(6, 3) if dashed else (), fill="",
            tags="selection")
        self.canvas.tag_raise("anchor")
        self.canvas.tag_raise("hint")

    def _start_drag(self, event):
        self._start = self._coords(event)
        self._draw_rectangle(*self._start, *self._start)

    def _drag(self, event):
        if self._start is not None:
            self._draw_rectangle(*self._start, *self._coords(event))

    def _finish_drag(self, event):
        if self._finished or self._start is None:
            return
        x2, y2 = self._coords(event)
        x1, y1 = self._start
        try:
            chosen = region_from_drag((x1, y1, x2, y2), self._anchor)
        except ValueError:
            self.canvas.delete("selection")
            self.canvas.create_text(
                self._width // 2, max(84, self._height - 40),
                text="区域至少 40 × 40 像素，请重新拖动；按 Esc 可取消",
                fill="#ffbd99", font=("Microsoft YaHei UI", 13),
                tags="selection")
            self._start = None
            return
        self._complete(chosen)

    def cancel(self):
        self._complete(None)

    def _complete(self, value: RelativeRegion | None):
        if self._finished:
            return
        self._finished = True
        try:
            self.grab_release()
        except tk.TclError:
            pass
        try:
            self.destroy()
        finally:
            self._done(value)
