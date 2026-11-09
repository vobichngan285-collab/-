"""Original-config Windows natural voice adapter, following LunaTranslator's
WindowsTTS -> msnaturalvoice -> Microsoft Embedded Speech SDK sequence.

The user's unmodified Luna config is read LOCALLY at runtime. Neither licence
fields nor natural voice files are bundled, uploaded or written to diagnostics.
This adapter uses the config's voice type=1, selected package path and the
exact MicrosoftWindows.Voice.License value without rewriting it.

Microsoft decides whether the supplied voice assets and model entitlement
actually permit synthesis. Never treat a config or license notice as proof.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree
from xml.sax.saxutils import escape
import json
import os


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
    """Consume the exact original configuration fields, with no transformations."""
    document = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(document, dict):
        raise ValueError("Luna 配置文件不是 JSON 对象")
    reader = document.get("reader") or {}
    windows_tts = reader.get("windowstts") or {}
    selected = windows_tts.get("voice")
    if not windows_tts.get("use") or not isinstance(selected, list) or len(selected) != 2:
        raise ValueError("Luna 配置未启用 WindowsTTS 自然语音")
    if selected[0] != 1 or not isinstance(selected[1], str) or not selected[1]:
        raise ValueError("Luna 语音类型不是自然语音（type=1）")
    license_text = document.get("MicrosoftWindows.Voice.License")
    if not isinstance(license_text, str) or not license_text:
        raise ValueError("缺少原始配置字段 MicrosoftWindows.Voice.License")
    speech_license = document.get("MicrosoftWindows.Speech.License", "")
    if not isinstance(speech_license, str):
        raise ValueError("MicrosoftWindows.Speech.License 字段类型错误")
    # Important: never strip(), normalize, replace or re-encode these values.
    return LunaNaturalSelection(
        model_path=selected[1],
        license_text=license_text,
        speech_license_text=speech_license,
    )


def read_voice_metadata(model_path: str | Path) -> tuple[str, str]:
    """Same Tokens.xml attributes read by LunaTranslator's WindowsTTS."""
    tokens = Path(model_path) / "Tokens.xml"
    xml = ElementTree.parse(tokens).getroot()
    values = {}
    for element in xml.iter():
        name = element.attrib.get("name")
        if name in ("Name", "LicenseVersion"):
            values[name] = element.attrib.get("value", "")
    # The original adapter can work without Name, but we need diagnostics
    # to be explicit rather than inventing a voice name.
    return values.get("Name", ""), values.get("LicenseVersion", "0")


def default_runtime_directories() -> list[Path]:
    windows = Path(os.environ.get("WINDIR", "C:/Windows"))
    sysapps = windows / "SystemApps" / "MicrosoftWindows.Client.Core_cw5n1h2txyewy"
    return [sysapps / "SpeechSynthesizer", sysapps]


def make_ssml(content: str, speed: int = 0, pitch: int = 0) -> str:
    """LunaTranslator's SSML formula: 10%/+speed or 5%/-speed, pitch*5%."""
    if not isinstance(content, str) or not content:
        raise ValueError("文本不能为空")
    rate_pct = int(speed) * (10 if speed > 0 else 5)
    pitch_pct = int(pitch) * 5
    # Copy Luna's no-explicit-voice SSML structure; model path chooses voice.
    return ("<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' "
            "xml:lang='en-US'><prosody pitch='{}%' rate='{}%'>{}</prosody>"
            "</speak>").format(pitch_pct, rate_pct, escape(content))


def configure_embedded_speech(selected: LunaNaturalSelection, speechsdk):
    """Repeat Luna's FromPath + SynthModelKey + Riff24k setup, EXACT license."""
    if not Path(selected.model_path).is_dir():
        raise FileNotFoundError("此电脑找不到配置中选定的自然语音包目录")
    config = speechsdk.EmbeddedSpeechConfig.from_path(selected.model_path)
    # Luna msnaturalvoice.cpp explicitly sets this property, not the SAPI/WinRT
    # voice name. SDK may reject this entitlement; do not bypass its response.
    config.set_property(speechsdk.PropertyId.SpeechServiceConnection_SynthModelKey,
                        selected.license_text)
    config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)
    return config


def synthesize_exact_config(config_path: str | Path, text: str,
                            speed: int = 0, pitch: int = 0,
                            speechsdk=None) -> bytes:
    """Use actual Luna config unchanged, returning WAV only if Microsoft accepts."""
    selected = load_original_config(config_path)
    # Prevalidate presence without opening or extracting protected model data.
    if not Path(selected.model_path).is_dir():
        raise FileNotFoundError("选中的自然语音包不存在，无法在本电脑尝试合成")
    holders = []
    try:
        if os.name == "nt" and hasattr(os, "add_dll_directory"):
            for directory in default_runtime_directories():
                if directory.is_dir():
                    holders.append(os.add_dll_directory(str(directory)))
        if speechsdk is None:
            import azure.cognitiveservices.speech as speechsdk
        cfg = configure_embedded_speech(selected, speechsdk)
        # EmbeddedSpeechConfig wraps the ordinary SpeechConfig as on Microsoft
        # SDK docs; this matches C++ SpeechSynthesizer::FromConfig(cfg,...).
        if hasattr(cfg, "get_speech_config"):
            speech_config = cfg.get_speech_config()
        else:
            speech_config = cfg
        synth = speechsdk.SpeechSynthesizer(
            speech_config=speech_config, audio_config=None)
        result = synth.speak_ssml_async(make_ssml(text, speed, pitch)).get()
        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            detail = ""
            cancellation = getattr(result, "cancellation_details", None)
            if cancellation is not None:
                detail = str(getattr(cancellation, "error_details", ""))[:260]
            raise RuntimeError("微软嵌入式 SDK 拒绝自然语音合成" +
                               (": " + detail if detail else ""))
        audio = bytes(result.audio_data)
        if len(audio) < 1000 or audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
            raise RuntimeError("嵌入式 SDK 没有返回有效 WAV 音频")
        return audio
    finally:
        for holder in reversed(holders):
            holder.close()


def safe_diagnostic(config_path: str | Path) -> dict:
    """Redacted; license and private user paths must NEVER appear in logs."""
    try:
        selected = load_original_config(config_path)
        available = Path(selected.model_path).is_dir()
        metadata = ("", "unknown")
        if available:
            try:
                metadata = read_voice_metadata(selected.model_path)
            except (OSError, ElementTree.ParseError, ValueError):
                pass
        return {
            "config_valid": True,
            "type": 1,
            "selected_voice": selected.safe_label,
            "selected_package_exists": available,
            "tokens_name": metadata[0][:70],
            "tokens_license_version": metadata[1][:25],
            "voice_license_field_present": bool(selected.license_text),
            "speech_license_field_present": bool(selected.speech_license_text),
            "note": "Fields loaded exactly; Microsoft SDK acceptance not yet proven",
        }
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return {"config_valid": False, "error_type": type(exc).__name__}
