"""Windows-only release gate: run ORIGINAL author's OCR after optional modules removed.

No OCR inference is implemented here. This process only uses the existing
BlueStar IPC plugin to request screenshot, region, and ORIGINAL local model.
"""
from __future__ import annotations

import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

HOST=("127.0.0.1", 29380)


def request(action, **kwargs):
    message=(json.dumps(dict(action=action,**kwargs),ensure_ascii=False)+"\n").encode()
    deadline=time.monotonic()+35
    last_error=None
    while time.monotonic()<deadline:
        try:
            with socket.create_connection(HOST,timeout=1.5) as sock:
                sock.settimeout(32)
                sock.sendall(message)
                response=bytearray()
                while b"\n" not in response and len(response)<=2_000_000:
                    block=sock.recv(8192)
                    if not block:
                        break
                    response.extend(block)
                if b"\n" not in response:
                    raise RuntimeError("Luna original OCR returned incomplete response")
                return json.loads(bytes(response).split(b"\n",1)[0].decode())
        except (ConnectionRefusedError, ConnectionResetError, TimeoutError, OSError) as exc:
            last_error=exc
            time.sleep(.2)
    raise RuntimeError("OCR-only original did not start") from last_error


def main(root):
    root=Path(root).resolve()
    required=[
        "LunaTranslator.exe",
        "LunaTranslator/textio/textsource/ocrtext.py",
        "LunaTranslator/ocrengines/local.py",
        "LunaTranslator/textio/textoutput/bluestar.py",
        "files/DLL64/CVUtils.dll",
        "files/DLL64/NativeUtils.dll",
    ]
    for name in required:
        assert (root/name).is_file(), f"Original required OCR component missing: {name}"
    removed=[
        "LunaTranslator/translator/google.py",
        "LunaTranslator/cishu/jisho.py",
        "LunaTranslator/tts/edgetts.py",
        "LunaTranslator/ocrengines/googlelens.py",
        "LunaTranslator/metadata/vn" + "db.py",
        "files/Magpie", "files/LunaHook","files/ocrmodel",
    ]
    for name in removed:
        assert not (root/name).exists(), f"Non-OCR component was still bundled: {name}"
    log_path=Path(tempfile.gettempdir())/"bluestar_trim_original_diagnostics.txt"
    logfile=log_path.open("wb")
    proc=subprocess.Popen(
        [str(root/"LunaTranslator.exe"),"--userconfig","userconfig_bluestar"],
        cwd=root,stdin=subprocess.DEVNULL,stdout=logfile,
        stderr=subprocess.STDOUT,
    )
    try:
        status=request("status")
        assert status.get("ok"), status
        x=status["status"]
        assert x["strategy"]=="period" and abs(x["interval_s"]-.4)<.00001,x
        assert x["model"]=="PP-OCRv6_small" and x["threads"]==4,x
        assert x["gpu_requested"] is True and x["main_window_hidden"] is True,x
        print("PASS ORIGINAL OCR-only runtime launched with user GPU/v6small/400ms",x)
        for action,args in [
            ("pause",{}), ("region",{"box":[70,70,450,260]}),
            ("border",{"visible":True}),
        ]:
            result=request(action,**args)
            assert result.get("ok"), (action,result)
        after=request("status")
        assert after.get("ok") and after["status"]["original_region_count"]==1,after
        assert after["status"]["original_regions_hidden"],after
        print("PASS original Qt ROI, scheduling and hidden pink GUI survive trim")
        original=request("ocr",box=[70,70,420,240])
        assert original.get("ok"), ("Original ONNX inference missing",original)
        assert isinstance(original.get("result"),dict),original
        assert isinstance(original["result"].get("results"),list),original
        print("PASS original screenshot+PP-OCRv6_small actual inference:",
              len(original["result"]["results"]),"lines")
        assert request("clear").get("ok")
        return 0
    except BaseException:
        logfile.flush()
        print("Original Luna stripped process exited with code:",proc.poll(),flush=True)
        if log_path.is_file():
            print("Original Luna stderr/stdout tail:\n",
                  log_path.read_bytes()[-16000:].decode("utf-8",errors="replace"),flush=True)
        raise
    finally:
        logfile.close()
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__=="__main__":
    raise SystemExit(main(sys.argv[1]))
