"""Read-only information about installed Windows voices; never bypass licensing.

Narrator's on-device natural voice packages can be visible to the OS while not
being callable through the documented SAPI / WinRT speech APIs. The diagnostic
must not claim that package discovery equals playback support.
"""
from __future__ import annotations

import subprocess
import sys


NATURAL_NAMES = ("Yunxi", "Xiaoxiao", "云希", "云溪", "云曦", "云熙", "晓晓")


def preferred_voice_index(voices: list[tuple[str, str]],
                          stored_voice_id: str = "") -> int:
    for i, (voice_id, _) in enumerate(voices):
        if stored_voice_id and voice_id == stored_voice_id:
            return i
    for name in NATURAL_NAMES:
        for i, (_, label) in enumerate(voices):
            if name.lower() in label.lower():
                return i
    for i, (_, label) in enumerate(voices):
        if ("zh-CN" in label or "中文" in label or "Huihui" in label or
                "Yaoyao" in label or "Kangkang" in label):
            return i
    return 0


def narrator_package_names() -> list[str]:
    """Ask the OS for *names*, without reading private WindowsApps files."""
    if sys.platform != "win32":
        return []
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        cmd = [
            "powershell.exe", "-NoProfile", "-NonInteractive",
            "-Command",
            "Get-AppxPackage -Name 'MicrosoftWindows.Voice.zh-CN.*' "
            "| Select-Object -ExpandProperty Name"
        ]
        output = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=8, creationflags=flags, check=False)
        return [s.strip() for s in output.stdout.splitlines()
                if ("Yunxi" in s or "Xiaoxiao" in s)]
    except (OSError, subprocess.TimeoutExpired):
        return []


def voice_diagnostic(voices: list[tuple[str, str]],
                     packages: list[str]) -> str:
    labels = [label for _, label in voices]
    callable_voices = [name for name in ("Yunxi", "Xiaoxiao")
                       if any(name.lower() in label.lower() for label in labels)]
    lines = [
        "游戏文字助手 V1.2 本地语音诊断",
        "可被 SAPI/WinRT 调用的系统语音：",
        *("- " + label for label in labels),
        "可调用的讲述人自然语音名称：" +
        (", ".join(callable_voices) if callable_voices else "未发现"),
        "系统已安装的自然语音包名称：" +
        (", ".join(packages) if packages else "未检测到或系统禁止枚举"),
        "说明：已安装 ≠ 可通过 SAPI/WinRT 播放。仅列出可调用语音供选择。",
        "不修改注册表、不提取密钥、不复制许可声明、不联网。",
    ]
    return "\n".join(lines)
