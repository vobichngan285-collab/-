"""Non-user-data regression tests for exact original Luna JSON call path."""
from __future__ import annotations

import base64
import json
from pathlib import Path
from types import SimpleNamespace

from game_reader.luna_natural_voice import (
    load_original_config, make_ssml, safe_diagnostic,
    synthesize_exact_config, read_voice_metadata
)
from game_reader.luna_voice_worker import process_request


FAKE_VOICE_LICENSE = "Example multi-line model NOTICE.\n  Preserve   all  spaces\nDo NOT log."
FAKE_SPEECH_LICENSE = "Separate speech license field; not sent to voice SDK."
FAKE_PACKAGE = "MicrosoftWindows.Voice.zh-CN.Yunxi.1_1.0.5.0_x64__cw5n1h2txyewy"


def fake_original_config(path: Path, model: Path):
    obj = {
        "MicrosoftWindows.Speech.License": FAKE_SPEECH_LICENSE,
        "MicrosoftWindows.Voice.License": FAKE_VOICE_LICENSE,
        "reader": {
            "windowstts": {
                "use": True,
                "name": "WindowsTTS",
                "type": "offline",
                "voice": [1, str(model)]
            }
        }
    }
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return obj


def test_original_json_is_not_edited_and_license_is_not_normalized(tmp_path):
    model = tmp_path / FAKE_PACKAGE
    model.mkdir()
    source = tmp_path / "config..json"
    before = fake_original_config(source, model)
    raw_before = source.read_bytes()
    selected = load_original_config(source)
    assert selected.model_path == str(model)
    assert selected.license_text == before["MicrosoftWindows.Voice.License"]
    assert selected.speech_license_text == before["MicrosoftWindows.Speech.License"]
    assert selected.safe_label == "云希"
    assert source.read_bytes() == raw_before


def test_uses_same_tokens_xml_name_and_license_version_as_luna(tmp_path):
    model = tmp_path / FAKE_PACKAGE
    model.mkdir()
    (model / "Tokens.xml").write_text(
        '<Tokens><Attribute name="Name" value="Microsoft Yunxi" />'
        '<Attribute name="LicenseVersion" value="1" /></Tokens>',
        encoding="utf-8")
    assert read_voice_metadata(model) == ("Microsoft Yunxi", "1")


def test_exact_license_reaches_microsoft_sdk_property_unmodified(tmp_path):
    model = tmp_path / FAKE_PACKAGE
    model.mkdir()
    file = tmp_path / "config..json"
    fake_original_config(file, model)
    calls = []
    wave_bytes = b"RIFF" + (b"\0" * 4) + b"WAVE" + (b"\0" * 2048)

    class EmbeddedConfig:
        @staticmethod
        def from_path(path):
            calls.append(("from_path", path))
            return EmbeddedConfig()
        def set_property(self, prop, value):
            calls.append(("set_property", prop, value))
        def set_speech_synthesis_output_format(self, fmt):
            calls.append(("set_format", fmt))
        def get_speech_config(self):
            calls.append(("get_speech_config",))
            return self

    class SpeechSynthesizer:
        def __init__(self, speech_config, audio_config):
            calls.append(("new_synthesizer", speech_config, audio_config))
        def speak_ssml_async(self, ssml):
            calls.append(("speak_ssml_async", ssml))
            return SimpleNamespace(get=lambda: SimpleNamespace(
                reason="SynthesizingAudioCompleted", audio_data=wave_bytes))

    fake_sdk = SimpleNamespace(
        EmbeddedSpeechConfig=EmbeddedConfig,
        PropertyId=SimpleNamespace(SpeechServiceConnection_SynthModelKey="SynthModelKey"),
        SpeechSynthesisOutputFormat=SimpleNamespace(Riff24Khz16BitMonoPcm="RIFF24K"),
        ResultReason=SimpleNamespace(SynthesizingAudioCompleted="SynthesizingAudioCompleted"),
        SpeechSynthesizer=SpeechSynthesizer)

    result = synthesize_exact_config(
        file, "<游戏开始> & 快速", speed=3, speechsdk=fake_sdk)
    assert result == wave_bytes
    assert calls[0] == ("from_path", str(model))
    assert calls[1] == ("set_property", "SynthModelKey", FAKE_VOICE_LICENSE)
    assert calls[2] == ("set_format", "RIFF24K")
    assert calls[3] == ("get_speech_config",)
    assert "rate='30%'" in calls[-1][-1]
    assert "&lt;游戏开始&gt; &amp; 快速" in calls[-1][-1]
    # Without the original license field, we must never claim success.
    document = json.loads(file.read_text(encoding="utf-8"))
    del document["MicrosoftWindows.Voice.License"]
    file.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    import pytest
    with pytest.raises(ValueError, match="Voice.License"):
        synthesize_exact_config(file, "尝试", speechsdk=fake_sdk)


def test_public_diagnostics_never_print_original_license_or_paths(tmp_path):
    path = tmp_path / FAKE_PACKAGE
    path.mkdir()
    cfg = tmp_path / "config..json"
    fake_original_config(cfg, path)
    output = safe_diagnostic(cfg)
    assert output["config_valid"]
    assert output["selected_package_exists"]
    assert "云希" == output["selected_voice"]
    printable = json.dumps(output, ensure_ascii=False)
    assert FAKE_VOICE_LICENSE not in printable
    assert FAKE_SPEECH_LICENSE not in printable
    assert str(cfg) not in printable
    assert str(path) not in printable


def test_worker_does_not_return_text_license_or_local_config(tmp_path):
    path = tmp_path / "config..json"
    def fake_synth(file, text, speed):
        assert file == str(path)
        assert text == "你好"
        assert speed == -2
        return b"RIFF" + (b"\0" * 4) + b"WAVE" + (b"\0" * 2048)
    result = process_request({"command": "speak", "config_path": str(path),
                              "text": "你好", "rate": -2}, synthesize=fake_synth)
    assert result["ok"]
    assert len(base64.b64decode(result["wav"])) > 2048
    assert "你好" not in json.dumps(result, ensure_ascii=False)
    assert str(path) not in json.dumps(result, ensure_ascii=False)


def test_worker_protects_error_details_and_limits_requests():
    secret = "UNSHAREABLE_USER_VOICE_LICENSE_STRING"
    def fails(*args, **kwargs):
        raise RuntimeError("SDK error with: " + secret)
    result = process_request({"command":"speak", "config_path":"a.json", "text":"hi"},
                             synthesize=fails)
    assert result["error"] == "embedded_sdk_synthesis_failed"
    assert secret not in json.dumps(result)
    assert not process_request({"command":"speak", "config_path":"a.json",
                                "text":"a" * 2001})["ok"]


def test_ssml_matches_luna_prosody_conventions():
    assert "rate='-15%'" in make_ssml("abc", speed=-3)
    assert "pitch='15%'" in make_ssml("abc", pitch=3)
