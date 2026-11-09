"""Regression tests for GUI -> speech queue -> packaged voice-worker config routing.

All strings are fake test data. Never put real user voice keys in GitHub.
"""
from __future__ import annotations

import json
from pathlib import Path
from queue import Queue

from game_reader.app import ReaderApp
from game_reader.speech import SpeechWorker
from game_reader.ms_voice_discovery import inspect_local_voice_config
from game_reader.luna_voice_worker import process_request


class FakeCombobox:
    def __init__(self, index=0):
        self.index = index

    def current(self):
        return self.index


class FakeSpeech:
    def __init__(self):
        self.calls = []

    def speak(self, *args, **kwargs):
        self.calls.append((args, kwargs))


def test_preview_passes_live_gui_config_and_selected_voice_not_stale_setting(tmp_path):
    old = tmp_path / "old.json"
    current = tmp_path / "语音 配置 config.json"
    old.write_text('{"MicrosoftWindows.Voice.License":"OLD_FAKE"}', encoding="utf-8")
    current.write_text('{"MicrosoftWindows.Voice.License":"CURRENT_FAKE"}', encoding="utf-8")
    app = ReaderApp.__new__(ReaderApp)
    app.settings = {"voice": "natural:MicrosoftWindows.Voice.zh-CN.Old",
                    "luna_config": str(current)}
    app.voice_select = FakeCombobox(0)
    app.voices = [("natural:MicrosoftWindows.Voice.zh-CN.Yunxi.1", "Yunxi")]
    app.speech = FakeSpeech()
    app.test_voice()
    assert len(app.speech.calls) == 1
    args, kwargs = app.speech.calls[0]
    assert "本地语音试听" in args[0]
    assert kwargs == {
        "natural_voice_id": "natural:MicrosoftWindows.Voice.zh-CN.Yunxi.1",
        "config_path": str(current),
    }
    assert str(old) not in str(app.speech.calls)


def test_selection_changed_after_rescan_is_used_by_next_speak(tmp_path):
    config = tmp_path / "config.json"
    app = ReaderApp.__new__(ReaderApp)
    app.settings = {"voice": "sapi:previous", "luna_config": str(config)}
    app.voice_select = FakeCombobox(1)
    app.voices = [("sapi:old", "Old"),
                  ("natural:MicrosoftWindows.Voice.zh-CN.Xiaoxiao.1", "Xiaoxiao")]
    app.speech = FakeSpeech()
    app.speak_selected("新弹窗")
    assert app.speech.calls[-1][1]["natural_voice_id"].endswith("Xiaoxiao.1")
    assert app.speech.calls[-1][1]["config_path"] == str(config)


def test_speech_worker_places_config_and_voice_in_one_queue_command():
    worker = SpeechWorker.__new__(SpeechWorker)
    worker._commands = Queue()
    from threading import Lock
    worker._speech_lock = Lock()
    worker._speech_generation = 0
    worker.speak("你好", natural_voice_id="natural:MicrosoftWindows.Voice.zh-CN.Yunxi.1",
                 config_path=r"H:\语音 配置\config.json")
    kind, payload = worker._commands.get_nowait()
    assert kind == "latest_natural_speak"
    assert payload[0] == "你好"
    assert payload[1].endswith("Yunxi.1")
    assert payload[2] == r"H:\语音 配置\config.json"
    worker.speak("普通朗读")
    assert worker._commands.get_nowait() == ("latest_speak", ("普通朗读", 2))


def test_safe_config_status_covers_main_failure_stages(tmp_path):
    assert inspect_local_voice_config("") == "local_voice_config_not_selected"
    missing = tmp_path / "不存在.json"
    assert inspect_local_voice_config(str(missing)) == "local_voice_config_file_missing"
    corrupt = tmp_path / "broken.json"
    corrupt.write_text("NOT_JSON", encoding="utf-8")
    assert inspect_local_voice_config(str(corrupt)) == "local_voice_config_invalid_json"
    empty = tmp_path / "empty.json"
    empty.write_text('{"reader": {}}', encoding="utf-8")
    assert inspect_local_voice_config(str(empty)) == "local_voice_license_missing"
    valid = tmp_path / "中文 路径 config.json"
    valid.write_text(json.dumps({
        "MicrosoftWindows.Voice.License": "FAKE_LOCAL_TEST_VALUE"
    }), encoding="utf-8")
    assert inspect_local_voice_config(str(valid)) == "ok"
    reply = process_request({"command": "check_config", "config_path": str(valid)})
    assert reply == {"ok": True, "stage": "config_read", "code": "ok"}
    assert "FAKE_LOCAL_TEST_VALUE" not in str(reply)
    assert str(valid) not in str(reply)
    invalid_reply = process_request({"command": "check_config",
                                     "config_path": str(missing)})
    assert invalid_reply["code"] == "local_voice_config_file_missing"


def test_original_v12_small_core_and_reading_behavior_unchanged():
    from game_reader.ocr_backend import LocalOCR, TIERS
    import inspect
    assert list(TIERS) == ["small"]
    source = inspect.getsource(LocalOCR.recognize)
    assert "Det.limit_type" not in source
    assert "Det.limit_side_len" not in source
    assert "ModelType.SMALL" in source
    assert "use_cls=False" in source


def test_worker_main_ignores_legacy_stdin_codepage_for_chinese_paths(
        tmp_path, monkeypatch, capsys):
    """Regression for Windows --windowed frozen worker defaulting to cp1252."""
    import io
    import sys
    from game_reader.luna_voice_worker import main
    config = tmp_path / "我的语音 配置 config.json"
    config.write_text(json.dumps({
        "MicrosoftWindows.Voice.License": "FAKE_TEST_ONLY"
    }), encoding="utf-8")
    request = json.dumps({"command": "check_config", "config_path": str(config)},
                         ensure_ascii=False) + "\n"

    class LegacyCodepageStdin:
        encoding = "cp1252"
        def __init__(self, binary):
            self.buffer = io.BytesIO(binary)
        def readline(self, *args):
            raise AssertionError("Worker must use UTF-8 binary stdin, not cp1252 text")

    monkeypatch.setattr(sys, "stdin", LegacyCodepageStdin(request.encode("utf-8")))
    assert main() == 0
    response = json.loads(capsys.readouterr().out)
    assert response == {"ok": True, "stage": "config_read", "code": "ok"}
    assert "FAKE_TEST_ONLY" not in str(response)
