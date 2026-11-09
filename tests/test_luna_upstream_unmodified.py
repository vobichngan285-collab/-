"""Verify exact connection to the unmodified official Luna engine."""
from __future__ import annotations
import json
from pathlib import Path

from game_reader.luna_voice_worker import process_request, synthesize_with_unmodified_luna
from game_reader.upstream_luna_pipe import make_exact_luna_argv
import game_reader.luna_voice_worker as worker


def test_original_executable_command_and_literal_license_are_preserved():
    lic = "A license-like sample NOTICE\n  exact whitespace  \n"
    argv = make_exact_luna_argv(
        "C:/example/LunaSubprocess64.exe",
        r"\\.\Pipe\123", "event-123", "map-123",
        "C:/WindowsApps/MicrosoftWindows.Voice.zh-CN.Yunxi.TEST",
        r"C:\Windows\SystemApps\MicrosoftWindows.Client.Core_cw5n1h2txyewy\SpeechSynthesizer", lic)
    assert argv[1] == "msnaturalvoice"
    assert argv[2:] == [
        r"\\.\Pipe\123", "event-123", "map-123",
        "C:/WindowsApps/MicrosoftWindows.Voice.zh-CN.Yunxi.TEST",
        r"C:\Windows\SystemApps\MicrosoftWindows.Client.Core_cw5n1h2txyewy\SpeechSynthesizer", lic]
    assert argv[-1].encode("utf-8") == lic.encode("utf-8")


def test_unmodified_subprocess_receives_original_json_model_and_license(tmp_path, monkeypatch):
    model = tmp_path / "MicrosoftWindows.Voice.zh-CN.Yunxi.1_1.0.5.0_x64__cw5n1h2txyewy"
    model.mkdir()
    config = tmp_path / "config..json"
    raw_license = "This is a test string\n with  exact   spacing  \n"
    settings = {
        "MicrosoftWindows.Speech.License": "other speech notice, not used as model key",
        "MicrosoftWindows.Voice.License": raw_license,
        "reader": {"windowstts": {"use": True, "voice": [1, str(model)]}},
    }
    config.write_text(json.dumps(settings, ensure_ascii=False), encoding="utf-8")
    original_bytes = config.read_bytes()
    observed = []
    wav = b"RIFF" + b"\0"*4 + b"WAVE" + b"\0"*2010

    class FakeOriginal:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def start(self, path, license_text):
            observed.append(("start",path,license_text))
        def speak_ssml(self, ssml):
            observed.append(("ssml",ssml))
            return wav

    monkeypatch.setattr(worker, "OriginalLunaPipe", FakeOriginal)
    audio = synthesize_with_unmodified_luna(config, "你好<云希>&晓晓", speed=-3)
    assert audio == wav
    assert observed[0] == ("start", str(model), raw_license)
    assert "rate='-15%'" in observed[1][1]
    assert "你好&lt;云希&gt;&amp;晓晓" in observed[1][1]
    assert config.read_bytes() == original_bytes


def test_frozen_worker_api_carries_no_private_license_in_reply(tmp_path, monkeypatch):
    file = tmp_path / "config..json"
    file.write_text('{"TEST":"NO_LICENSE"}')
    wav = b"RIFF" + b"\0"*4 + b"WAVE" + b"\0"*2000
    def fake(path, text, speed):
        assert path == str(file) and text == "你好"
        return wav
    x = process_request({"command":"speak", "config_path":str(file),
                         "text":"你好"}, synthesize=fake)
    assert x["ok"] and x["engine"] == "official_luna_unmodified"
    assert str(file) not in str(x)
    assert "NO_LICENSE" not in str(x)


def test_worker_exposes_no_reimplemented_embedded_sdk():
    source = Path(worker.__file__).read_text(encoding="utf-8")
    assert "import azure.cognitiveservices.speech" not in source
    assert "synthesize_exact_config" not in source
    assert "OriginalLunaPipe" in source
