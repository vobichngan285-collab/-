"""One warm OCR engine, CPU 2/4/6, DirectML switch and single-char filtering."""
from pathlib import Path
import sys
import types

from game_reader.text_filters import filter_speech_text, DEFAULT_FILTER_SETTINGS
from game_reader.ocr_backend import LocalOCR


def test_independent_single_chinese_character_only():
    config=dict(DEFAULT_FILTER_SETTINGS)
    assert filter_speech_text("开\n开始\n打开背包\n关\n继续游戏",config) == "开始\n打开背包\n继续游戏"
    config["filter_single_char"]=False
    assert filter_speech_text("开\n开始",config) == "开\n开始"


def test_thread_setting_only_accepts_2_4_6():
    assert [LocalOCR(t).threads for t in (2,4,6,8,0)] == [2,4,6,2,2]


def test_engine_is_created_once_and_uses_exact_small_models(monkeypatch,tmp_path):
    for name in ("PP-OCRv6_det_small.onnx","PP-OCRv6_rec_small.onnx"):
        (tmp_path/name).write_bytes(b"x"*100001)
    import game_reader.ocr_backend as b
    monkeypatch.setattr(b,"model_root",lambda:tmp_path)
    created=[]
    class FakeRapid:
        def __init__(self,params):created.append(params)
        def __call__(self,image,use_cls=False):
            assert use_cls is False
            return types.SimpleNamespace(boxes=[],txts=[],scores=[])
    enums=types.SimpleNamespace(ONNXRUNTIME="onnx",PPOCRV6="v6",SMALL="small")
    monkeypatch.setitem(sys.modules,"rapidocr",types.SimpleNamespace(
        RapidOCR=FakeRapid,ModelType=enums,EngineType=enums,OCRVersion=enums))
    monkeypatch.setitem(sys.modules,"onnxruntime",types.SimpleNamespace(
        get_available_providers=lambda:["DmlExecutionProvider","CPUExecutionProvider"]))
    engine=LocalOCR(4,gpu=True)
    engine.prepare()
    engine.prepare()
    assert len(created)==1
    p=created[0]
    assert p["EngineConfig.onnxruntime.use_dml"] is True
    assert p["EngineConfig.onnxruntime.intra_op_num_threads"] == 4
    assert p["EngineConfig.onnxruntime.inter_op_num_threads"] == 1
    assert Path(p["Det.model_path"]).name == "PP-OCRv6_det_small.onnx"


def test_no_dml_provider_means_cpu_not_crash(monkeypatch,tmp_path):
    for name in ("PP-OCRv6_det_small.onnx","PP-OCRv6_rec_small.onnx"):
        (tmp_path/name).write_bytes(b"x"*100001)
    import game_reader.ocr_backend as b
    monkeypatch.setattr(b,"model_root",lambda:tmp_path)
    config=[]
    class FakeRapid:
        def __init__(self,params):config.append(params)
        def __call__(self,*a,**kw):return None
    enum=types.SimpleNamespace(ONNXRUNTIME="onnx",PPOCRV6="v6",SMALL="small")
    monkeypatch.setitem(sys.modules,"rapidocr",types.SimpleNamespace(
        RapidOCR=FakeRapid,ModelType=enum,EngineType=enum,OCRVersion=enum))
    monkeypatch.setitem(sys.modules,"onnxruntime",types.SimpleNamespace(
        get_available_providers=lambda:["CPUExecutionProvider"]))
    engine=LocalOCR(2,gpu=True)
    engine.prepare()
    assert engine.gpu_available is False
    assert config[0]["EngineConfig.onnxruntime.use_dml"] is False


def test_dml_session_load_failure_falls_back_before_ready(monkeypatch, tmp_path):
    import sys
    import types
    import game_reader.ocr_backend as b
    for name in ("PP-OCRv6_det_small.onnx", "PP-OCRv6_rec_small.onnx"):
        (tmp_path / name).write_bytes(b"x" * 100001)
    monkeypatch.setattr(b, "model_root", lambda: tmp_path)
    params_seen = []
    class FakeRapid:
        def __init__(self, params):
            params_seen.append(params)
            if params["EngineConfig.onnxruntime.use_dml"]:
                raise RuntimeError("mock GPU is busy")
        def __call__(self, *args, **kwargs):
            return None
    enum = types.SimpleNamespace(ONNXRUNTIME="onnx", PPOCRV6="v6", SMALL="small")
    monkeypatch.setitem(sys.modules, "rapidocr", types.SimpleNamespace(
        RapidOCR=FakeRapid, ModelType=enum, EngineType=enum, OCRVersion=enum))
    monkeypatch.setitem(sys.modules, "onnxruntime", types.SimpleNamespace(
        get_available_providers=lambda: ["DmlExecutionProvider", "CPUExecutionProvider"]))
    engine = LocalOCR(4, gpu=True)
    engine.prepare()
    assert [item["EngineConfig.onnxruntime.use_dml"] for item in params_seen] == [True, False]
    assert engine.loaded_tier == "small" and not engine.gpu_active
    assert engine.gpu_fallback_error == "RuntimeError"
