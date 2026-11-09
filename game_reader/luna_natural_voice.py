"""Read the user's ORIGINAL LunaTranslator config without changing a byte.

The speech synthesis engine is the upstream LunaSubprocess64.exe, copied
verbatim from the LunaTranslator official Windows release. This file does
NOT reimplement the Microsoft Embedded Speech SDK or alter model keys.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree
from xml.sax.saxutils import escape
import json


@dataclass(frozen=True)
class LunaNaturalSelection:
    model_path: str
    license_text: str
    speech_license_text: str

    @property
    def safe_label(self) -> str:
        folder = self.model_path.lower()
        if "xiaoxiao" in folder:
            return "晓晓"
        if "yunxi" in folder:
            return "云希"
        return "微软自然语音"


def load_original_config(path: str | Path) -> LunaNaturalSelection:
    """Read original voice fields exactly, including whitespace and newlines."""
    doc = json.loads(Path(path).read_bytes().decode("utf-8-sig"))
    if not isinstance(doc, dict):
        raise ValueError("原作者配置不是 JSON 对象")
    selected = (doc.get("reader") or {}).get("windowstts") or {}
    voice = selected.get("voice")
    if selected.get("use") is not True:
        raise ValueError("原作者配置未启用 WindowsTTS")
    if not isinstance(voice, list) or len(voice) != 2 or voice[0] != 1:
        raise ValueError("原作者配置不是自然语音模式 1")
    if not isinstance(voice[1], str) or not voice[1]:
        raise ValueError("原作者自然语音路径无效")
    voice_license = doc.get("MicrosoftWindows.Voice.License")
    if not isinstance(voice_license, str) or not voice_license:
        raise ValueError("缺少原作者 MicrosoftWindows.Voice.License 字段")
    speech_license = doc.get("MicrosoftWindows.Speech.License", "")
    if not isinstance(speech_license, str):
        raise ValueError("原作者 MicrosoftWindows.Speech.License 字段格式无效")
    return LunaNaturalSelection(voice[1], voice_license, speech_license)


def read_voice_metadata(model_path: str | Path) -> tuple[str, str]:
    """Same Tokens.xml Name and LicenseVersion attributes as upstream."""
    root = ElementTree.parse(Path(model_path) / "Tokens.xml").getroot()
    values = {}
    for tag in root.iter():
        if tag.attrib.get("name") in ("Name", "LicenseVersion"):
            values[tag.attrib["name"]] = tag.attrib.get("value", "")
    return values.get("Name", ""), values.get("LicenseVersion", "0")


def default_runtime_directories() -> list[Path]:
    from os import environ
    sysapps = (Path(environ.get("WINDIR", "C:/Windows")) /
               "SystemApps" / "MicrosoftWindows.Client.Core_cw5n1h2txyewy")
    return [sysapps / "SpeechSynthesizer", sysapps]


def make_ssml(content: str, speed: int = 0, pitch: int = 0) -> str:
    """Exact markup formula in upstream TTSbase.createSSML, no added voice."""
    if not isinstance(content, str) or not content:
        raise ValueError("文字不能为空")
    pitch_pct = int(pitch) * 5
    rate_pct = int(speed) * (10 if speed > 0 else 5)
    prosody = "<prosody pitch='{}%' rate='{}%'>{}</prosody>".format(
        pitch_pct, rate_pct, escape(content))
    return ("<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' "
            "xml:lang='en-US'>{}</speak>").format(prosody)


def safe_diagnostic(config_path: str | Path) -> dict:
    """Never reveal full license or user paths in app logs."""
    try:
        selected = load_original_config(config_path)
        installed = Path(selected.model_path).is_dir()
        name, license_version = "", "unknown"
        if installed:
            try:
                name, license_version = read_voice_metadata(selected.model_path)
            except (OSError, ValueError, ElementTree.ParseError):
                pass
        return {
            "config_valid": True, "mode": 1,
            "selected_voice": selected.safe_label,
            "selected_package_exists": installed,
            "tokens_name": name[:70],
            "tokens_license_version": license_version[:25],
            "voice_license_field_present": bool(selected.license_text),
            "speech_license_field_present": bool(selected.speech_license_text),
            "engine": "official_verbatim_LunaSubprocess64.exe",
            "note": "配置文件内容未修改；实际发声仍需本机模型验证",
        }
    except (OSError, ValueError, TypeError, UnicodeError):
        return {"config_valid": False, "error_type": "invalid_original_config"}
