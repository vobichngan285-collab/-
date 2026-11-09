"""Windows natural voice architecture experiment grounded in LunaTranslator's design.

Design parallels LunaTranslator's WindowsTTS:
  1. Discover Windows MicrosoftWindows.Voice.* packages.
  2. Parse the installed package's Tokens.xml display-name/version metadata.
  3. Locate the Windows embedded speech DLL.
  4. Use a SEPARATE process for the official Microsoft Embedded Speech SDK.
  5. Return WAV audio from the process when supplied with an appropriately
     licensed embedded voice model and actual, valid model entitlement.

No built-in synthesis keys; never copy system voice packages; never bypass
encryption; no cloud APIs, third-party credentials, licensing text or secrets.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from xml.etree import ElementTree as ET

RUNTIME_NAME = "Microsoft.CognitiveServices.Speech.extension.embedded.tts.dll"
VOICE_PREFIX = "MicrosoftWindows.Voice."
VOICE_NAMES = ("Yunxi", "Xiaoxiao")
REPORT = "natural_voice_architecture_report.json"


def parse_tokens_xml(path: Path) -> dict:
    """Read public-ish display metadata, not model files or licenses."""
    if path.name.lower() != "tokens.xml" or not path.is_file():
        raise ValueError("Expected installed Tokens.xml metadata file")
    root = ET.parse(path).getroot()
    props: dict[str, str] = {}
    for tag in root.iter():
        if tag.attrib.get("name") in ("Name", "LicenseVersion"):
            props[tag.attrib["name"]] = tag.attrib.get("value", "")
    return {"display_name": props.get("Name", ""),
            "license_version": props.get("LicenseVersion", "0")}


def _powershell(script: str) -> list[dict]:
    res = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, timeout=20, check=False)
    if res.returncode != 0:
        raise RuntimeError("Appx package discovery failed")
    if not res.stdout.strip():
        return []
    data = json.loads(res.stdout)
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    return []


def discover_narrator_packages() -> list[dict]:
    results = _powershell(
        "Get-AppxPackage -Name 'MicrosoftWindows.Voice.*' "
        "| Select-Object Name, InstallLocation | ConvertTo-Json -Compress")
    voices = []
    for item in results:
        name = str(item.get("Name") or "")
        directory = str(item.get("InstallLocation") or "")
        if not name.startswith(VOICE_PREFIX) or not directory:
            continue
        folder = Path(directory)
        metadata = {"display_name": "", "license_version": "unknown"}
        try:
            metadata = parse_tokens_xml(folder / "Tokens.xml")
        except (OSError, ValueError, ET.ParseError):
            pass
        voices.append({
            "package_name": name,
            "display_name": metadata["display_name"],
            "license_version": metadata["license_version"],
            # No package path or private data in cloud report. The worker can
            # re-enumerate it in-process if actually authorized to synthesize.
            "looks_like_target": any(
                x.lower() in name.lower() or x.lower() in metadata["display_name"].lower()
                for x in VOICE_NAMES
            ),
        })
    return voices


def runtime_available() -> bool:
    root = Path(os.environ.get("WINDIR", r"C:\Windows"))
    return (root / "SystemApps" /
            "MicrosoftWindows.Client.Core_cw5n1h2txyewy" /
            "SpeechSynthesizer" / RUNTIME_NAME).is_file()


def licensed_embedded_sdk_synthesize(model_path: str, voice_name: str,
                                     text: str, license_value: str) -> bytes:
    """Official Microsoft SDK, only for a model the caller is authorized to use.

    The user-pasted license NOTICE text is not a synthesized model license.
    The caller must supply authorization from the model publisher.
    """
    if not (license_value and model_path and voice_name):
        raise PermissionError("No licensed embedded voice model and model entitlement provided")
    if not Path(model_path).is_dir():
        raise FileNotFoundError("Authorized embedded model directory is unavailable")
    import azure.cognitiveservices.speech as speechsdk
    if not hasattr(speechsdk, "EmbeddedSpeechConfig"):
        raise RuntimeError("Embedded variant of the Microsoft Speech SDK not installed")
    config = speechsdk.EmbeddedSpeechConfig.from_path(model_path)
    config.set_speech_synthesis_voice(voice_name, license_value)
    config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)
    speech_config = config.get_speech_config()
    synth = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    result = synth.speak_text_async(text).get()
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        raise RuntimeError("Official SDK reported embedded synthesis failure")
    audio = bytes(result.audio_data)
    if len(audio) < 1000:
        raise RuntimeError("Official SDK returned empty audio")
    return audio


def worker_main() -> None:
    """Small independent process; host sends commands via stdin, JSON on stdout.

    This current cloud experiment supports only a capability probe. The
    synthesis function above is ready for legitimately provisioned models,
    but no models or keys are shipped by the game reader.
    """
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if request.get("command") != "probe":
                raise ValueError("This cloud experiment permits probe only")
            try:
                import azure.cognitiveservices.speech as speechsdk
                importable = hasattr(speechsdk, "EmbeddedSpeechConfig")
            except ImportError:
                importable = False
            result = {"status": "ok", "sdk_embedded_api_importable": importable,
                      "runtime_present": runtime_available(),
                      "packages": discover_narrator_packages(),
                      "licensed_model_available_in_ci": False}
            print(json.dumps(result, ensure_ascii=False), flush=True)
        except Exception as exc:
            print(json.dumps({"status": "error",
                              "error_type": type(exc).__name__}), flush=True)


def parent_main() -> None:
    fixture = """<?xml version="1.0" encoding="UTF-8"?>
    <Root><Attribute name="Name" value="Microsoft Yunxi" />
          <Attribute name="LicenseVersion" value="1" /></Root>"""
    with tempfile.TemporaryDirectory(prefix="voice_arch_fixture_") as d:
        p = Path(d) / "Tokens.xml"
        p.write_text(fixture, encoding="utf-8")
        fixture_result = parse_tokens_xml(p)
        assert fixture_result == {
            "display_name": "Microsoft Yunxi", "license_version": "1"
        }
        # Verify lack of a properly issued model entitlement fails closed,
        # even if this is a valid-looking OS voice package name.
        refused = False
        try:
            licensed_embedded_sdk_synthesize(d, "Microsoft Yunxi", "Test", "")
        except PermissionError:
            refused = True
        assert refused

    command = [sys.executable, str(Path(__file__).resolve()), "--worker"]
    proc = subprocess.run(command, input='{"command":"probe"}\n',
                          text=True, capture_output=True, timeout=45)
    if proc.returncode:
        raise RuntimeError("Natural-voice isolated process crashed")
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise RuntimeError("Natural-voice isolated process protocol broken")
    result = json.loads(lines[0])
    if result.get("status") != "ok":
        raise RuntimeError("Natural-voice isolated process failed to inspect runtime")

    report = {
        "experiment": "LunaTranslator-inspired OS package discovery + isolated Microsoft Embedded Speech worker",
        "platform": platform.system(),
        "fixture_tokens_xml_parse": "passed",
        "unlicensed_synthesis_refused": refused,
        "separate_worker": result,
        "caveat": "No Yunxi/Xiaoxiao model or legitimate embedded speech entitlement in cloud CI; "
                  "this does not claim natural voice audio has been generated.",
        "non_goals": [
            "No use of embedded key bundled in third-party source",
            "No bypass of Microsoft narrator model restrictions",
            "No copying installed protected natural voice package",
            "No change to GameTextReader V1.8",
        ]
    }
    Path(REPORT).write_text(json.dumps(report, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--worker":
        worker_main()
    else:
        parent_main()
