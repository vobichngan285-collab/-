"""Windows cloud TTS capability experiment (no private device, models, or credentials).

Verifies actual SAPI WAV synthesis and WinRT stream synthesis; lists availability
of Narrator natural-voice packages by Windows package *name*. Does not copy,
read, decrypt, activate, or invoke Narrator's protected voice package files.
Does not attempt LunaTranslator's embedded-SDK model/license-key method.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import time
import wave


def status_probe(func):
    try:
        return func()
    except Exception as exc:
        return {"status": "error", "error_type": type(exc).__name__,
                "message": str(exc)[:300]}


def _powsh(script: str) -> list[str]:
    proc = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, timeout=18, check=False)
    if proc.returncode:
        raise RuntimeError("PowerShell query failed with exit code " +
                           str(proc.returncode))
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def narrator_packages():
    """Read installed Appx names only; never open the app packages or license."""
    names = _powsh(
        "Get-AppxPackage -Name 'MicrosoftWindows.Voice.zh-CN.*' "
        "| Select-Object -ExpandProperty Name")
    possible = ["Yunxi", "Xiaoxiao"]
    return {
        "status": "ok",
        "voice_package_names": names,
        "target_present": {n: any(n.lower() in p.lower() for p in names)
                           for n in possible},
        "note": "Package installed does not prove third-party speech permission",
    }


def runtime_components():
    root = Path(os.environ.get("WINDIR", r"C:\Windows"))
    candidate = root / "SystemApps" / "MicrosoftWindows.Client.Core_cw5n1h2txyewy" / "SpeechSynthesizer" / "Microsoft.CognitiveServices.Speech.extension.embedded.tts.dll"
    # Presence only: do not load a protected runtime or inspect its contents.
    return {"status": "ok", "narrator_embedded_runtime_present": candidate.is_file(),
            "note": "Runtime presence is not a license or authorization"}


def sapi_synthesize():
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    try:
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        voices = speaker.GetVoices()
        labels = [voices.Item(i).GetDescription() for i in range(voices.Count)]
        with tempfile.TemporaryDirectory(prefix="cloud_sapi_voice_") as folder:
            wav = str(Path(folder) / "real_sapi_synthesis.wav")
            stream = win32com.client.Dispatch("SAPI.SpFileStream")
            stream.Open(wav, 3, False)  # SSFMCreateForWrite
            speaker.AudioOutputStream = stream
            start = time.perf_counter()
            try:
                speaker.Speak("A real Windows cloud text to speech synthesis test.", 0)
            finally:
                stream.Close()
            ms = round((time.perf_counter() - start) * 1000)
            output_bytes = os.path.getsize(wav)
            with wave.open(wav, "rb") as content:
                frame_count = content.getnframes()
                sample_rate = content.getframerate()
            if frame_count <= 500 or output_bytes <= 1100:
                raise RuntimeError("SAPI returned no substantial WAV audio")
        return {
            "status": "real_audio_generated",
            "voices": labels,
            "audio_bytes": output_bytes,
            "frames": frame_count,
            "sample_rate_hz": sample_rate,
            "synthesis_ms": ms,
            "note": "SAPI real WAV, not Yunxi/Xiaoxiao unless specifically listed",
        }
    finally:
        pythoncom.CoUninitialize()


async def _winrt_synthesize():
    from winrt.windows.media.speechsynthesis import SpeechSynthesizer
    start = time.perf_counter()
    voices = list(SpeechSynthesizer.all_voices)
    names = [{"name": v.display_name, "language": v.language}
             for v in voices]
    if not voices:
        return {"status": "no_voices", "voices": names}
    synthesizer = SpeechSynthesizer()
    stream = await synthesizer.synthesize_text_to_stream_async(
        "A real Windows Runtime speech synthesis test.")
    size = int(stream.size)
    content_type = stream.content_type
    if hasattr(stream, "close"):
        stream.close()
    if size <= 1000:
        raise RuntimeError("WinRT produced an empty or implausibly small audio stream")
    return {"status": "real_audio_generated", "audio_bytes": size,
            "content_type": content_type, "voices": names,
            "synthesis_ms": round((time.perf_counter()-start)*1000),
            "target_in_list": {n: any(n.lower() in v["name"].lower()
                                     for v in names)
                               for n in ("Yunxi", "Xiaoxiao")},
            "note": "Standard WinRT only; no protected Narrator API access"}


def winrt_synthesize():
    return asyncio.run(_winrt_synthesize())


def main():
    result = {
        "experiment": "Windows SAPI/WinRT/narrator package voice feasibility",
        "environment": {"system": platform.system(),
                        "release": platform.release(),
                        "machine": platform.machine(),
                        "ci": bool(os.environ.get("GITHUB_ACTIONS"))},
        "sapi": status_probe(sapi_synthesize),
        "winrt": status_probe(winrt_synthesize),
        "narrator_packages": status_probe(narrator_packages),
        "narrator_runtime": status_probe(runtime_components),
        "not_tested": [
            "Actual user's PC and natural voice packages",
            "User's installed Yunxi or Xiaoxiao audio",
            "Microsoft embedded speech SDK requiring license/model entitlement",
            "LunaTranslator license-string/key workaround",
            "Guangrong native third-party DLL",
        ],
    }
    path = Path("cloud_voice_feasibility.json")
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    print("REPORT_PATH=" + str(path.absolute()))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if platform.system() != "Windows":
        raise SystemExit("This experiment requires a real Windows runner")


if __name__ == "__main__":
    main()
