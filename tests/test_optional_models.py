"""Optional model download, validation, and original model regression tests."""
from __future__ import annotations

from hashlib import sha256
import io
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from game_reader import ocr_models
from game_reader.ocr_backend import LocalOCR, TIERS
from game_reader.app import read_settings


def test_catalog_contains_exact_v6_tiny_v5_mobile_and_offline_default():
    assert set(ocr_models.MODEL_LABELS) == {"small", "tiny", "v5_mobile"}
    assert set(ocr_models.OPTIONAL_FILES) == {"tiny", "v5_mobile"}
    assert set(TIERS) == {"small", "tiny", "v5_mobile"}
    for tier, pair in ocr_models.OPTIONAL_FILES.items():
        assert len(pair) == 2
        for name, url, digest in pair:
            assert name.endswith(".onnx")
            assert url.startswith(ocr_models.CATALOG_BASE + "/")
            assert len(digest) == 64
            int(digest, 16)


def _dummy_pair(monkeypatch, model_key="tiny"):
    files = [b"a" * 110001, b"b" * 113003]
    entries = ocr_models.OPTIONAL_FILES[model_key]
    patched = tuple((name, url, sha256(data).hexdigest())
                    for (name, url, _), data in zip(entries, files))
    monkeypatch.setattr(ocr_models, "OPTIONAL_FILES",
                        {**ocr_models.OPTIONAL_FILES, model_key: patched})
    class FakeResponse:
        def __init__(self, data):
            self.stream = io.BytesIO(data)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self, n):
            return self.stream.read(n)
        def geturl(self):
            return entries[0][1]
    return files, FakeResponse


def test_download_installs_both_files_atomically_and_offline(tmp_path, monkeypatch):
    files, Response = _dummy_pair(monkeypatch)
    requested = []
    data = iter(files)
    def fake_urlopen(request, timeout):
        requested.append(request.full_url)
        assert timeout == 45
        return Response(next(data))
    monkeypatch.setattr(ocr_models, "urlopen", fake_urlopen)
    updates = []
    paths = ocr_models.install_optional_model("tiny", updates.append, root=tmp_path)
    assert len(requested) == 2 and len(paths) == 2
    assert paths[0].read_bytes() == files[0] and paths[1].read_bytes() == files[1]
    assert ocr_models.model_installed("tiny", tmp_path)
    assert not list(tmp_path.glob(".ocr_pending_*"))
    assert any("2/2" in item for item in updates)
    # A second install is offline, no URL call.
    assert paths == ocr_models.install_optional_model("tiny", root=tmp_path)
    assert len(requested) == 2


def test_checksum_failure_keeps_old_install_intact(tmp_path, monkeypatch):
    files, Response = _dummy_pair(monkeypatch)
    requested = []
    def bad_urlopen(request, timeout):
        requested.append(request.full_url)
        return Response(b"wrong model" * 25000)
    monkeypatch.setattr(ocr_models, "urlopen", bad_urlopen)
    old_dir = tmp_path / "tiny"
    old_dir.mkdir()
    old_marker = old_dir / "old.txt"
    old_marker.write_text("existing data", encoding="utf-8")
    with pytest.raises(RuntimeError, match="校验失败"):
        ocr_models.install_optional_model("tiny", root=tmp_path)
    assert old_marker.read_text(encoding="utf-8") == "existing data"
    assert not list(tmp_path.glob(".ocr_pending_*"))
    assert len(requested) == 1
    assert not ocr_models.model_installed("tiny", tmp_path)


def test_model_selection_survives_restart_if_installed(tmp_path, monkeypatch):
    import game_reader.app as app
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"tier": "tiny", "rate_level": 10,
                                    "filter_english": True}), encoding="utf-8")
    monkeypatch.setattr(app, "CONFIG_PATH", settings)
    monkeypatch.setattr(app, "model_installed", lambda tier: tier in ("tiny", "small"))
    selected = read_settings()
    assert selected["tier"] == "tiny" and selected["rate_level"] == 10
    monkeypatch.setattr(app, "model_installed", lambda tier: tier == "small")
    selected = read_settings()
    assert selected["tier"] == "small"


def test_ocr_engine_parameters_match_selected_official_models(tmp_path, monkeypatch):
    from enum import Enum
    from PIL import Image
    import game_reader.ocr_backend as backend
    class E(Enum):
        ONNXRUNTIME = "onnxruntime"
        PPOCRV6 = "PP-OCRv6"
        PPOCRV5 = "PP-OCRv5"
        SMALL = "small"
        TINY = "tiny"
        MOBILE = "mobile"
        CH = "ch"
    observed = []
    class FakeRapidOCR:
        def __init__(self, params):
            observed.append(params)
        def __call__(self, img, use_cls=False):
            assert use_cls is False
            return SimpleNamespace(boxes=None, txts=None, scores=None)
    monkeypatch.setitem(sys.modules, "rapidocr", SimpleNamespace(
        RapidOCR=FakeRapidOCR, ModelType=E, EngineType=E,
        OCRVersion=E, LangDet=E, LangRec=E))
    for name in ("PP-OCRv6_det_small.onnx", "PP-OCRv6_rec_small.onnx",
                 "PP-OCRv6_det_tiny.onnx", "PP-OCRv6_rec_tiny.onnx",
                 "ch_PP-OCRv5_det_mobile.onnx", "ch_PP-OCRv5_rec_mobile.onnx"):
        (tmp_path / name).write_bytes(b"x" * 100001)
    monkeypatch.setattr(backend, "model_root", lambda: tmp_path)
    monkeypatch.setattr(backend, "model_installed", lambda tier: True)
    monkeypatch.setattr(backend, "model_paths", lambda tier: (
        tmp_path / backend.TIERS[tier][0], tmp_path / backend.TIERS[tier][1]))
    reader = LocalOCR()
    img = Image.new("RGB", (300, 120), "white")
    for tier in ("small", "tiny", "v5_mobile"):
        assert reader.recognize(img, (0, 0), tier) == []
        assert reader.loaded_tier == tier
    assert observed[0]["Det.ocr_version"] == E.PPOCRV6
    assert observed[0]["Rec.model_type"] == E.SMALL
    assert "Rec.lang_type" not in observed[0]  # unchanged V6 Small params
    assert observed[1]["Det.model_type"] == E.TINY
    assert observed[1]["Rec.ocr_version"] == E.PPOCRV6
    assert observed[2]["Det.model_type"] == E.MOBILE
    assert observed[2]["Rec.ocr_version"] == E.PPOCRV5
    assert observed[2]["Rec.lang_type"] == E.CH
    assert len(observed) == 3


def test_unknown_models_cannot_install(tmp_path):
    with pytest.raises(ValueError):
        ocr_models.install_optional_model("typo", root=tmp_path)
    assert not ocr_models.model_installed("typo", tmp_path)
    assert ocr_models.model_installed("small", tmp_path)
