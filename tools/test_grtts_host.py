"""Windows CI: test standalone native Guangrong host end-to-end using a fake DLL.

Never interpret this as evidence that the real publisher DLL loaded.
"""
import base64
import os
import pathlib
import subprocess
import sys
import tempfile

exe=pathlib.Path(sys.argv[1]).resolve()
dll=pathlib.Path(sys.argv[2]).resolve()
assert exe.is_file() and dll.is_file()
assert exe.name.lower()=="guangronghost.exe"

with subprocess.Popen([str(exe),"--server",str(dll)],stdin=subprocess.PIPE,
                      stdout=subprocess.PIPE,stderr=subprocess.PIPE) as p:
    lines=[p.stdout.readline().decode("ascii").strip() for _ in range(3)]
    print("INIT",lines,flush=True)
    assert lines[0]=="HELLO\t1", lines
    assert lines[1].startswith("VOICE\t0\t"), lines
    assert base64.b64decode(lines[1].split("\t")[2]).decode("utf-8")=="Native Host Test Voice"
    assert lines[2]=="READY", lines
    text=base64.b64encode("你好，这是一句本地语音测试。".encode("utf-8")).decode("ascii")
    p.stdin.write(("SPEAK\t1\t"+text+"\n").encode("ascii"))
    p.stdin.flush()
    header=p.stdout.readline().decode("ascii").strip()
    print("SYNTH_HEADER",header,flush=True)
    fields=header.split("\t")
    assert fields[:5]==["AUDIO","1","24000","16","1"],fields
    size=int(fields[5])
    assert size>=9000
    pcm=p.stdout.read(size)
    assert len(pcm)==size
    p.stdin.write(b"STOP\nQUIT\n")
    p.stdin.flush()
    p.wait(timeout=5)
    assert p.returncode==0
print("NATIVE_HOST_SYNTH_PASS",flush=True)

with tempfile.TemporaryDirectory() as d:
    broken=pathlib.Path(d)/"grtts_x64.dll"
    broken.write_bytes(b"NOT A WINDOWS DYNAMIC LIBRARY")
    p=subprocess.Popen([str(exe),"--server",str(broken)],
                       stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr=p.communicate(input=b"QUIT\n",timeout=8)
    print("INVALID_DLL",stdout.decode("ascii",errors="replace").strip(),flush=True)
    assert b"ERROR\t193\t" in stdout,stdout
    assert p.returncode!=0
print("NATIVE_HOST_INVALID_PE_PASS",flush=True)
