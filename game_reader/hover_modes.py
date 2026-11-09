"""Pure interaction policy for keyboard/mouse shortcuts and pointer-relative OCR.

No capture, model load, Windows input hook, external service, or speech engine
is created here. Keep the original V1.2 Small recognizer untouched.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

VK_XBUTTON1 = 0x05
VK_XBUTTON2 = 0x06
MOUSE_SIDE_VKS = (VK_XBUTTON1, VK_XBUTTON2)
MODIFIER_VKS = (0x10, 0x11, 0x12, 0x5B, 0x5C)
HOTKEY_FIELDS = ("vk", "mode_vk", "local_vk", "pick_vk")
HOTKEY_LABELS = ("hotkey_label", "mode_hotkey_label", "local_hotkey_label", "pick_hotkey_label")
HOTKEY_DEFAULTS = (0x77, 0x78, 0x79, 0x7A)  # F8 / F9 / F10 / F11
DEFAULT_REGION = (-300, -140, 600, 400)
MIN_PERIOD_MS = 100
MAX_PERIOD_MS = 60000


def valid_hotkey(vk: int) -> bool:
    """Support single Windows keyboard keys plus the two standard mouse sides."""
    try:
        n = int(vk)
    except (TypeError, ValueError):
        return False
    return n in MOUSE_SIDE_VKS or (
        8 <= n <= 254 and n not in MODIFIER_VKS
        and n not in (0x01, 0x02, 0x04)  # ordinary clicks must not trigger OCR
    )


def hotkey_label(vk: int, keyname: str = "") -> str:
    if vk == VK_XBUTTON1:
        return "鼠标侧键1（后退）"
    if vk == VK_XBUTTON2:
        return "鼠标侧键2（前进）"
    if keyname:
        return str(keyname)[:40]
    if 0x70 <= vk <= 0x87:
        return f"F{vk - 0x6F}"
    if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
        return chr(vk)
    return f"VK {vk}"


def sanitize_hotkeys(config: dict) -> dict:
    """Repair old F8-only settings while preserving voice and private file paths."""
    reserved: set[int] = set()
    for field, label_field, fallback in zip(
            HOTKEY_FIELDS, HOTKEY_LABELS, HOTKEY_DEFAULTS):
        try:
            vk = int(config.get(field, fallback))
        except (TypeError, ValueError):
            vk = fallback
        repaired = not valid_hotkey(vk) or vk in reserved
        if repaired:
            vk = next(value for value in list(HOTKEY_DEFAULTS) + list(range(0x7A, 0x88))
                      if value not in reserved)
        config[field] = vk
        label = config.get(label_field)
        if (repaired or vk in MOUSE_SIDE_VKS or
                not isinstance(label, str) or not label or
                (label in ("F8", "F9", "F10", "F11") and
                 vk != {"F8": 0x77, "F9": 0x78, "F10": 0x79, "F11": 0x7A}[label])):
            config[label_field] = hotkey_label(vk)
        reserved.add(vk)
    return config


def parse_period_ms(value: object) -> int:
    """Return integer milliseconds; reject accidental zero/negative overload."""
    if isinstance(value, bool) or not re.fullmatch(r"\d{1,6}", str(value).strip()):
        raise ValueError("刷新间隔请输入 100 到 60000 之间的整数毫秒")
    n = int(str(value).strip())
    if not MIN_PERIOD_MS <= n <= MAX_PERIOD_MS:
        raise ValueError("刷新间隔请输入 100 到 60000 之间的整数毫秒")
    return n


@dataclass(frozen=True)
class RelativeRegion:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self):
        if not all(isinstance(x, int) and not isinstance(x, bool)
                   for x in (self.x, self.y, self.width, self.height)):
            raise ValueError("区域必须使用整数像素")
        if not 40 <= self.width <= 5000 or not 40 <= self.height <= 5000:
            raise ValueError("区域宽高范围为 40～5000 像素")
        if abs(self.x) > 10000 or abs(self.y) > 10000:
            raise ValueError("相对偏移超出安全范围")

    @classmethod
    def from_settings(cls, value) -> "RelativeRegion":
        try:
            if not isinstance(value, (tuple, list)) or len(value) != 4:
                raise ValueError
            return cls(*value)
        except (TypeError, ValueError):
            return cls(*DEFAULT_REGION)

    def as_list(self) -> list[int]:
        return [self.x, self.y, self.width, self.height]


def region_from_drag(drag: tuple[int, int, int, int],
                     anchor: tuple[int, int]) -> RelativeRegion:
    x1, y1, x2, y2 = drag
    left, top = min(x1, x2), min(y1, y2)
    return RelativeRegion(left - anchor[0], top - anchor[1],
                          abs(x2 - x1), abs(y2 - y1))


def capture_box(region: RelativeRegion, cursor: tuple[int, int],
                monitor: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """Keep the user-picked crop size if possible at any monitor edge.

    bbox is in Windows physical desktop coordinates, including negative origins
    for monitors positioned left of the primary display.
    """
    ml, mt, mr, mb = monitor
    if mr <= ml or mb <= mt:
        raise ValueError("显示器坐标无效")
    width = min(region.width, mr - ml)
    height = min(region.height, mb - mt)
    left = max(ml, min(cursor[0] + region.x, mr - width))
    top = max(mt, min(cursor[1] + region.y, mb - height))
    return left, top, left + width, top + height


def next_mouse_mode(current: str) -> str:
    return "hover" if current == "pointer" else "pointer"


def normalized_text(text: str) -> str:
    """Ignore OCR whitespace jitter, preserve words and original speech text."""
    return re.sub(r"\s+", "", text).strip()

def cursor_still_near_capture(start: tuple[int, int], current: tuple[int, int],
                              allowed_move: int = 45) -> bool:
    """Discard OCR text generated from a location the mouse already left."""
    if not all(isinstance(n, int) for n in (*start, *current)):
        return False
    dx, dy = current[0] - start[0], current[1] - start[1]
    return dx * dx + dy * dy <= allowed_move * allowed_move


def exclude_unrelated_desktop_text(foreground_class: str) -> bool:
    """Hover tooltip OCR should never read wallpaper/desktop icons."""
    return foreground_class in {"Progman", "WorkerW", "Shell_TrayWnd"}
