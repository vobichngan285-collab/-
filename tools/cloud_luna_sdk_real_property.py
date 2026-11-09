"""Exercise the REAL Microsoft Embedded Speech SDK with a fake model folder.

Uses the same deprecated SynthModelKey property as LunaTranslator's C++.
This is a property-wiring test, not a license bypass or audio synthesis.
Neither real user configuration nor private model files enter CI.
"""
from __future__ import annotations
import json
from pathlib import Path
import tempfile

import azure.cognitiveservices.speech as speechsdk

with tempfile.TemporaryDirectory(prefix="GTR_original_config_property_") as root:
    model_dir = Path(root) / "MicrosoftWindows.Voice.zh-CN.Yunxi.FAKE"
    model_dir.mkdir()
    text = "TEST_FIXTURE_NOT_A_REAL_MODEL_ENTITLEMENT"
    report = {"sdk_embedded_api": hasattr(speechsdk,"EmbeddedSpeechConfig"),
              "voice_model": "fake metadata-only directory",
              "entitlement_source": "synthetic testing string",
              "actual_yunxi_audio": False}
    try:
        sdk_config = speechsdk.EmbeddedSpeechConfig.from_path(str(model_dir))
        sdk_config.set_property(
            speechsdk.PropertyId.SpeechServiceConnection_SynthModelKey,
            text)
        sdk_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)
        read_back = sdk_config.get_property(
            speechsdk.PropertyId.SpeechServiceConnection_SynthModelKey)
        report["actual_embedded_property_set"] = read_back == text
        report["actual_embedded_property_nonempty"] = bool(read_back)
        report["result"] = "PASS" if read_back == text else "FAILED"
    except Exception as exc:
        report["actual_embedded_property_set"] = False
        report["result"] = "BLOCKED_BY_SDK"
        report["error_type"] = type(exc).__name__
    Path("luna_sdk_property_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
