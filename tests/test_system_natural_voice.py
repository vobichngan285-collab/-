"""Regression coverage for natural voice discovery without real licensed voice."""
from __future__ import annotations
import inspect
import json
from pathlib import Path

from game_reader.ms_voice_discovery import (
    packages_from_json, choose_natural_voice, load_user_config,
)
from game_reader.luna_voice_worker import process_request, VoiceSetupError
from game_reader.upstream_luna_pipe import make_exact_luna_argv
from game_reader.ocr_backend import LocalOCR, TIERS


def test_original_v12_small_params_not_replaced_with_faster_resize():
    source = inspect.getsource(LocalOCR.recognize)
    assert TIERS["small"] == ("PP-OCRv6_det_small.onnx", "PP-OCRv6_rec_small.onnx")
    assert "Det.limit_type" not in source
    assert "Det.limit_side_len" not in source
    assert "ModelType.MEDIUM" not in source


def test_installed_package_discovery_parses_tokens(tmp_path):
    folder = tmp_path / "MicrosoftWindows.Voice.zh-CN.Yunxi.1_1.0.0.0_x64__fake"
    folder.mkdir()
    (folder / "Tokens.xml").write_text(
        '<Root><Attribute name="Name" value="Yunxi" />'
        '<Attribute name="LicenseVersion" value="2" /></Root>',
        encoding="utf-8",
    )
    json_text = json.dumps([{
        "Name": "MicrosoftWindows.Voice.zh-CN.Yunxi.1",
        "InstallLocation": str(folder)
    }])
    result = packages_from_json(json_text)
    assert len(result) == 1
    assert result[0].name == "Yunxi"
    assert result[0].license_version == "2"
    assert choose_natural_voice("natural:MicrosoftWindows.Voice.zh-CN.Yunxi.1", result) == result[0]
    assert "待试听" in result[0].ui_label
    assert choose_natural_voice("natural:MicrosoftWindows.Voice.zh-CN.Xiaoxiao.1", result) is None


def test_json_license_never_exposed_in_UI_and_uses_local_file(tmp_path):
    path = tmp_path / "config..json"
    path.write_text(json.dumps({
        "MicrosoftWindows.Voice.License": "TEST_ONLY_SECRET_NEVER_LOG",
        "reader": {"windowstts": {"voice": [1, "C:/stale/version"]}}
    }), encoding="utf-8")
    license_text, old_path = load_user_config(str(path))
    assert license_text == "TEST_ONLY_SECRET_NEVER_LOG"
    assert old_path == "C:/stale/version"
    assert load_user_config(str(tmp_path / "none.json")) == ("", "")


def test_worker_returns_real_error_stages_instead_of_generic_runtime_error():
    base = {"command": "speak", "voice_id": "natural:MicrosoftWindows.Voice.zh-CN.Yunxi.1",
            "config_path": "", "text": "你好", "rate": 0}
    result = process_request(base, synthesize=lambda *a, **k: (_ for _ in ()).throw(
        VoiceSetupError("selected_voice_package_not_installed")))
    assert not result["ok"]
    assert result["stage"] == "discovery_or_setup"
    assert result["code"] == "selected_voice_package_not_installed"
    assert "license" not in str(result).lower()


def test_worker_conveys_valid_wav_and_uses_original_IPC_contract():
    base = {"command": "speak", "voice_id": "natural:MicrosoftWindows.Voice.zh-CN.Yunxi.1",
            "config_path": "", "text": "你好", "rate": 0}
    wav = b"RIFF" + b"\x00\x00\x00\x00WAVE" + b"data"
    result = process_request(base, synthesize=lambda *a, **k: wav)
    assert result["ok"] and result["audio_size"] == len(wav)
    assert make_exact_luna_argv("exe","pipe","event","map","model","sdk","local-license") == [
        "exe", "msnaturalvoice", "pipe", "event", "map", "model", "sdk", "local-license"
    ]


def test_invalid_requests_do_not_trigger_engine():
    assert process_request({"command":"speak", "text":""})["code"] == "invalid_text"
    assert process_request({"command":"speak", "text":"abc", "voice_id":"notnatural",
                            "config_path":""})["code"] == "invalid_voice_id"
