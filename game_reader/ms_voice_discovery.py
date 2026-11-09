"""Discover Windows installed natural voices before selecting a synthesis model.

Read-only: Get-AppxPackage (current user) and Tokens.xml for metadata.
Finding a package does not prove Microsoft Embedded Speech authorization.
Never embed a license, write registry keys, or change WindowsApps content.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree


@dataclass(frozen=True)
class NaturalVoice:
    package: str
    path: str
    name: str
    license_version: str

    @property
    def ui_label(self) -> str:
        short = self.name or self.package.rsplit(".", 1)[-1]
        return f"系统自然语音 · {short}（已安装，待试听）"


def _parse_tokens(folder: Path) -> tuple[str, str]:
    try:
        root = ElementTree.parse(folder / "Tokens.xml").getroot()
        attrs = {
            element.attrib.get("name"): element.attrib.get("value", "")
            for element in root.iter()
            if element.attrib.get("name") in ("Name", "LicenseVersion")
        }
        return attrs.get("Name", ""), attrs.get("LicenseVersion", "0")
    except (OSError, ElementTree.ParseError, ValueError):
        return "", "unknown"


def packages_from_json(stdout: str) -> list[NaturalVoice]:
    """Pure parser, also exercised on Windows CI without natural voice packages."""
    try:
        data = json.loads(stdout)
    except (TypeError, ValueError):
        return []
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []
    found: list[NaturalVoice] = []
    seen = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        package, location = item.get("Name"), item.get("InstallLocation")
        if not isinstance(package, str) or not package.startswith("MicrosoftWindows.Voice."):
            continue
        if not isinstance(location, str) or not location:
            continue
        root = Path(location)
        # WindowsApps metadata may be readable even when Python cannot stat
        # the protected package directory. Do not hide a real OS-listed voice.
        if package.lower() in seen:
            continue
        name, license_version = _parse_tokens(root)
        if not name:
            name = package.rsplit(".", 2)[-2] if package.count(".") >= 2 else package
        found.append(NaturalVoice(package, str(root), name[:120], license_version[:40]))
        seen.add(package.lower())
    return sorted(found, key=lambda v: v.name.casefold())


def discover_natural_voices() -> list[NaturalVoice]:
    if sys.platform != "win32":
        return []
    # The author's native FindPackages also searches installed Windows
    # packages. PowerShell is a public, read-only OS enumeration fallback.
    script = (
        "[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
        "$p=@(Get-AppxPackage -Name 'MicrosoftWindows.Voice.*' | "
        "Select-Object Name,InstallLocation);"
        "ConvertTo-Json -InputObject $p -Compress -Depth 3"
    )
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=12, creationflags=flags, check=False
        )
        return packages_from_json(result.stdout) if result.returncode == 0 else []
    except (OSError, subprocess.TimeoutExpired):
        return []


def choose_natural_voice(voice_id: str, installed: list[NaturalVoice]) -> NaturalVoice | None:
    """Saved UI IDs refer to package names, never to stale WindowsApps paths."""
    name = voice_id.removeprefix("natural:").lower()
    return next((v for v in installed if v.package.lower() == name), None)


def inspect_local_voice_config(path: str) -> str:
    """Safe local configuration preflight; do not return or log license content.

    Distinguishes missing selection, inaccessible file, invalid JSON and
    missing Voice.License. An 'ok' status checks presence, NOT authorization
    or successful synthesis.
    """
    if not isinstance(path, str) or not path.strip():
        return "local_voice_config_not_selected"
    try:
        blob = Path(path).read_bytes()
    except FileNotFoundError:
        return "local_voice_config_file_missing"
    except OSError:
        return "local_voice_config_unreadable"
    try:
        doc = json.loads(blob.decode("utf-8-sig"))
    except (UnicodeError, ValueError):
        return "local_voice_config_invalid_json"
    if not isinstance(doc, dict):
        return "local_voice_config_invalid_json"
    value = doc.get("MicrosoftWindows.Voice.License", "")
    if not isinstance(value, str) or not value:
        return "local_voice_license_missing"
    return "ok"


def load_user_config(path: str) -> tuple[str, str]:
    """Load only required fields from the user's OWN local JSON. No key logging."""
    if not path:
        return "", ""
    try:
        data = json.loads(Path(path).read_bytes().decode("utf-8-sig"))
        license_value = data.get("MicrosoftWindows.Voice.License", "")
        selected = (data.get("reader") or {}).get("windowstts") or {}
        voice = selected.get("voice") or []
        preferred = voice[1] if isinstance(voice, list) and len(voice) > 1 else ""
        return (license_value if isinstance(license_value, str) else "",
                preferred if isinstance(preferred, str) else "")
    except (OSError, ValueError, TypeError, AttributeError):
        return "", ""
