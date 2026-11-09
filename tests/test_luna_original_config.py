"""Exact original config parsing and native upstream voice request tests."""
from __future__ import annotations
import json
from pathlib import Path

import pytest
from game_reader.luna_natural_voice import (
    load_original_config, make_ssml, safe_diagnostic, read_voice_metadata)
from game_reader.luna_voice_worker import process_request

LICENSE_VALUE = "Multiline original test value.\n  preserve exactly  \n"
PATH_SUFFIX = "MicrosoftWindows.Voice.zh-CN.Yunxi.1_1.0.5.0_x64__cw5n1h2txyewy"


def make_config(tmp_path):
    model = tmp_path / PATH_SUFFIX
    model.mkdir()
    path = tmp_path / "config..json"
    value = {"reader":{"windowstts":{"use":True,"voice":[1,str(model)],
                                      "name":"WindowsTTS","type":"offline"}},
             "MicrosoftWindows.Voice.License":LICENSE_VALUE,
             "MicrosoftWindows.Speech.License":"Other independent notice",
             "unrelated_key":{"must_remain":True}}
    path.write_text(json.dumps(value,ensure_ascii=False),encoding="utf-8")
    return path,model


def test_luna_original_json_license_field_exact(tmp_path):
    source,model=make_config(tmp_path)
    before=source.read_bytes()
    chosen=load_original_config(source)
    assert chosen.model_path==str(model)
    assert chosen.license_text==LICENSE_VALUE
    assert chosen.speech_license_text=="Other independent notice"
    assert chosen.safe_label=="云希"
    assert source.read_bytes()==before


def test_tokens_xml_same_attributes_as_upstream(tmp_path):
    _,model=make_config(tmp_path)
    (model/"Tokens.xml").write_text(
        '<R><Attribute name="Name" value="Microsoft Yunxi" />'
        '<Attribute name="LicenseVersion" value="1" /></R>',encoding="utf-8")
    assert read_voice_metadata(model)==("Microsoft Yunxi","1")


def test_original_ssml_formula_escapes_game_text():
    doc=make_ssml("<继续游戏> & 返回",speed=3,pitch=-2)
    assert "rate='30%'" in doc
    assert "pitch='-10%'" in doc
    assert "&lt;继续游戏&gt; &amp; 返回" in doc
    assert "xml:lang='en-US'" in doc
    assert "rate='-15%'" in make_ssml("hello",speed=-3)


def test_original_voice_license_not_leaked_in_log(tmp_path):
    cfg,model=make_config(tmp_path)
    diagnostic=safe_diagnostic(cfg)
    assert diagnostic["config_valid"]
    assert diagnostic["engine"]=="official_verbatim_LunaSubprocess64.exe"
    result=json.dumps(diagnostic,ensure_ascii=False)
    assert LICENSE_VALUE not in result
    assert str(cfg) not in result
    assert str(model) not in result


def test_missing_original_license_rejected(tmp_path):
    cfg,_=make_config(tmp_path)
    value=json.loads(cfg.read_text(encoding="utf-8"))
    value.pop("MicrosoftWindows.Voice.License")
    cfg.write_text(json.dumps(value,ensure_ascii=False),encoding="utf-8")
    with pytest.raises(ValueError,match="Voice.License"):
        load_original_config(cfg)


def test_worker_reports_real_upstream_selected_without_leaking(tmp_path):
    cfg,_=make_config(tmp_path)
    wav=b"RIFF"+b"\0"*4+b"WAVE"+b"\0"*2048
    def synth(path,text,speed):
        assert path==str(cfg) and text=="你好" and speed==-2
        return wav
    result=process_request({"command":"speak","config_path":str(cfg),
                            "text":"你好","rate":-2},synthesize=synth)
    assert result["ok"]
    assert result["engine"]=="official_luna_unmodified"
    assert LICENSE_VALUE not in json.dumps(result,ensure_ascii=False)
    assert str(cfg) not in json.dumps(result,ensure_ascii=False)


def test_worker_sdk_failure_never_logs_license():
    private="PRIVATE_NOTICE_TO_NOT_LEAK"
    def fail(*_args,**_kwargs):
        raise RuntimeError(private)
    result=process_request({"command":"speak","config_path":"a.json",
                            "text":"你好"},synthesize=fail)
    assert not result["ok"]
    assert private not in json.dumps(result)
