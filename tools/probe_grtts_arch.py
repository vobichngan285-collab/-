"""Architectural compatibility probe for publisher's unmodified Guangrong add-on.

Runs in separate Windows subprocess; no key/license patching or DLL modifications.
Outputs only initialization result, number of voices and synthesized PCM length.
"""
from __future__ import annotations
import ctypes
import os
from pathlib import Path
import struct
import sys
import time
import traceback

def run(directory: str):
    arch = 64 if struct.calcsize("P") == 8 else 32
    root=Path(directory).resolve()
    dll=root/("grtts_x64.dll" if arch==64 else "grtts.dll")
    print("ARCH_BITS",arch,flush=True)
    print("DLL_NAME",dll.name, "EXISTS",dll.exists(),flush=True)
    if not dll.exists():return 2
    print("DLL_BYTES",dll.stat().st_size,flush=True)
    os.chdir(root)
    cookie=os.add_dll_directory(str(root))
    kernel=ctypes.windll.kernel32
    # Test real LoadLibraryEx on explicitly selected publisher DLL.
    # No fiddling with licenses, import tables, or voice resources.
    try:
        h=kernel.LoadLibraryExW
        h.argtypes=[ctypes.c_wchar_p,ctypes.c_void_p,ctypes.c_uint]
        h.restype=ctypes.c_void_p
        # LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS.
        handle=h(str(dll),None,0x100|0x1000)
        if not handle:
            code=ctypes.get_last_error()
            if code==0: code=kernel.GetLastError()
            print("LOAD_LIBRARY_EX_FAILURE",code,ctypes.FormatError(code),flush=True)
            return 3
        print("LOAD_LIBRARY_EX_SUCCESS",hex(handle),flush=True)
        lib=ctypes.CDLL(str(dll),handle=handle)
        funcs={
            "YongDe_Initialize":(ctypes.c_bool,[]),
            "YongDe_GetVoiceCount":(ctypes.c_int,[]),
            "YongDe_GetVoiceName":(ctypes.c_int,[ctypes.c_int,ctypes.c_wchar_p,ctypes.c_int]),
            "YongDe_SetVoice":(ctypes.c_bool,[ctypes.c_int]),
            "YongDe_TextToAudio":(ctypes.c_bool,[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(ctypes.c_int)]),
            "YongDe_FreeAudio":(None,[ctypes.c_void_p]),
            "YongDe_GetAudioFormat":(None,[ctypes.POINTER(ctypes.c_int)]*3),
            "YongDe_Uninitialize":(None,[])
        }
        for name,(ret,args) in funcs.items():
            f=getattr(lib,name)
            f.restype=ret
            f.argtypes=args
        ok=bool(lib.YongDe_Initialize())
        print("YONGDE_INIT",ok,flush=True)
        if not ok:return 4
        try:
            n=int(lib.YongDe_GetVoiceCount())
            print("VOICES",n,flush=True)
            for i in range(min(max(n,0),12)):
                b=ctypes.create_unicode_buffer(256)
                lib.YongDe_GetVoiceName(i,b,256)
                print("VOICE",i,repr(b.value),flush=True)
            if n<1: return 5
            print("SET_VOICE",bool(lib.YongDe_SetVoice(0)),flush=True)
            p=ctypes.c_void_p()
            length=ctypes.c_int()
            t0=time.monotonic()
            ok=bool(lib.YongDe_TextToAudio("你好，这是一段本地语音测试。",ctypes.byref(p),ctypes.byref(length)))
            print("SYNTH_OK",ok,"AUDIO_LEN",length.value,"ELAPSED",round(time.monotonic()-t0,2),flush=True)
            if p.value:
                lib.YongDe_FreeAudio(p)
            return 0 if ok and length.value>0 else 6
        finally:
            lib.YongDe_Uninitialize()
    except Exception as e:
        print("UNHANDLED",type(e).__name__,str(e),flush=True)
        traceback.print_exc()
        return 7
    finally:
        cookie.close()
if __name__=="__main__":sys.exit(run(sys.argv[1]))
