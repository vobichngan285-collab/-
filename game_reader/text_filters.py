"""Only optional speech cleanup and text-difference control for local OCR.

Original OCR output is never modified or persisted by these functions. Latin
letters, Unicode decimal digits and symbols are removable independently.
Screen-reading controls, diagnostic strings and spoken mode announcements do
NOT pass through this module.
"""
from __future__ import annotations

import re
import unicodedata


DEFAULT_FILTER_SETTINGS = {
    "filter_english": True,
    "filter_numbers": True,
    "filter_symbols": True,
    "similarity_enabled": True,
    "similarity_threshold": 2,
    "show_scan_frame": True,
    "mode_voice_hint": True,
}


def filter_speech_text(raw: str, settings: dict) -> str:
    """Keep line order and word boundaries; never fabricate OCR words."""
    if not raw:
        return ""
    english = bool(settings.get("filter_english", True))
    numbers = bool(settings.get("filter_numbers", True))
    symbols = bool(settings.get("filter_symbols", True))
    output: list[str] = []
    for line in str(raw).splitlines():
        chars = []
        for char in line:
            name = unicodedata.name(char, "")
            category = unicodedata.category(char)
            if english and category.startswith("L") and "LATIN" in name:
                continue
            if numbers and category.startswith("N"):
                continue
            if symbols and category[:1] in ("P", "S"):
                continue
            chars.append(char)
        cleaned = re.sub(r"\s+", " ", "".join(chars)).strip()
        # Reject standalone punctuation/number/Latin-only result only when
        # the corresponding filters are actually selected.
        if cleaned:
            output.append(cleaned)
    return "\n".join(output)


def levenshtein_distance_bounded(a: str, b: str, cap: int) -> int:
    """Bounded edit distance; enough to tell whether a threshold is exceeded."""
    if a == b:
        return 0
    if cap < 0:
        raise ValueError("cap must be nonnegative")
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    if not a or not b:
        return min(max(len(a), len(b)), cap + 1)
    previous = list(range(len(b) + 1))
    for i, char in enumerate(a, 1):
        current = [i] + [cap + 1] * len(b)
        from_j = max(1, i - cap)
        to_j = min(len(b), i + cap)
        if from_j > to_j:
            return cap + 1
        for j in range(from_j, to_j + 1):
            current[j] = min(
                previous[j] + 1,
                current[j-1] + 1,
                previous[j-1] + (char != b[j-1])
            )
        if min(current[from_j:to_j+1]) > cap:
            return cap + 1
        previous = current
    return min(previous[-1], cap + 1)


def is_repeat_speech(previous: str, current: str, settings: dict) -> bool:
    """Treat brief distinct item names as different even with low edit distance.

    Short item names like 碎布 and 石斧 must ALWAYS trigger on change. For longer
    text, tolerate minor OCR jitter without suppressing a new short name.
    """
    if not previous or not current:
        return False
    left = re.sub(r"\s+", "", previous)
    right = re.sub(r"\s+", "", current)
    if left == right:
        return True
    if not settings.get("similarity_enabled", True):
        return False
    threshold = max(0, min(8, int(settings.get("similarity_threshold", 2))))
    if min(len(left), len(right)) <= 4 or threshold == 0:
        return False
    # Do not let a 2-character threshold hide meaningful 5-character labels.
    safe = min(threshold, max(0, min(len(left), len(right)) // 5))
    return safe > 0 and levenshtein_distance_bounded(left, right, safe) <= safe


def similarity_threshold(value) -> int:
    try:
        v = int(str(value).strip())
    except (ValueError, TypeError):
        raise ValueError("相似度阈值须为 0～8 的整数") from None
    if isinstance(value, bool) or not 0 <= v <= 8:
        raise ValueError("相似度阈值须为 0～8 的整数")
    return v
