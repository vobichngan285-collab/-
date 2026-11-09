"""Probe original official Guangrong DLL using our native C++ host on Windows CI.

No vendor binary is repackaged in the release; the archive is downloaded
directly from publisher and SHA-pinned. Probe does not patch any license.
"""
from __future__ import annotations
import os,subprocess,sys,zipfile,pathlib,hashlib
original=pathlib.Path(sys.argv[1])
exe=pathlib.Path(sys.argv[2])
expected="14ba0d4155549a1e4b76335687c960815c87e16f3e34907e1476d206c3609a77"
assert original.is_file() and hashlib.sha256(original.read_bytes()).hexdigest()==expected
out=pathlib.Path(os.environ["RUNNER_TEMP"])/"real-official-tts"
with zipfile.ZipFile(original) as z:
    assert z.testzip() is None
    z.extractall(out)
dll=out/"synthDrivers"/"grtts_x64.dll"
assert dll.is_file()
print("OFFICIAL_DLL_ARCHIVE_VERIFIED",dll.stat().st_size,flush=True)
proc=subprocess.Popen([str(exe),"--server",str(dll)],stdin=subprocess.PIPE,
                      stdout=subprocess.PIPE,stderr=subprocess.PIPE)
try:
    lines,err=proc.communicate(input=b"QUIT\n",timeout=12)
except subprocess.TimeoutExpired:
    proc.kill();lines,err=proc.communicate(timeout=3)
    print("OFFICIAL_DLL_TIMEOUT",flush=True);sys.exit(0)
print("OFFICIAL_EXIT",proc.returncode,"PROTOCOL",lines[:2500].decode("ascii",errors="replace"),flush=True)
if b"READY" in lines:
    print("OFFICIAL_DLL_INIT_SUCCESS",flush=True)
else:
    print("OFFICIAL_DLL_INIT_UNAVAILABLE",flush=True)
