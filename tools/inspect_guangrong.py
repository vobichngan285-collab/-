"""CI-only inspection of vendor-published NVDA addon, no redistribution."""
import ctypes, hashlib, os, pathlib, sys, zipfile, traceback
a=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
print("addon_size",a.stat().st_size,"sha256",hashlib.sha256(a.read_bytes()).hexdigest(),flush=True)
with zipfile.ZipFile(a) as z:
    bad=z.testzip();print("bad_entry",bad,"file_count",len(z.namelist()),flush=True)
    wanted=[i for i in z.infolist() if (
        "grtts.dll" in i.filename.lower() or
        i.filename.lower().endswith(("license","license.txt","copying.txt","manifest.ini","addonmanifest.ini")) or
        i.filename.lower().startswith("synthdrivers/") and (
           i.filename.count("/")<3 and (i.filename.lower().endswith((".dll",".ini",".json",".vl",".xml"))))
        )]
    for info in wanted[:100]:print("entry",info.filename,info.file_size,flush=True)
    if bad:raise RuntimeError("invalid addon archive")
    files=z.namelist()
    for item in z.infolist():
        name=item.filename.replace("\\","/")
        if name.startswith("/") or ".." in pathlib.PurePosixPath(name).parts:raise RuntimeError("unsafe archive name")
    z.extractall(out)
paths=list(out.rglob("grtts.dll"))
print("dll_paths",[str(p.relative_to(out)) for p in paths],flush=True)
if not paths:sys.exit(2)
dll=paths[0]
if sys.platform=="win32":
    os.add_dll_directory(str(dll.parent))
    os.chdir(dll.parent)
    try:
        lib=ctypes.CDLL(str(dll))
        lib.YongDe_Initialize.argtypes=[]
        lib.YongDe_Initialize.restype=ctypes.c_bool
        ok=bool(lib.YongDe_Initialize())
        print("INDEPENDENT_INITIALIZATION",ok,flush=True)
        if ok:
            lib.YongDe_GetVoiceCount.argtypes=[]
            lib.YongDe_GetVoiceCount.restype=ctypes.c_int
            count=lib.YongDe_GetVoiceCount()
            print("VOICE_COUNT",count,flush=True)
            lib.YongDe_GetVoiceName.argtypes=[ctypes.c_int,ctypes.c_wchar_p,ctypes.c_int]
            for i in range(min(max(0,count),20)):
                b=ctypes.create_unicode_buffer(256)
                lib.YongDe_GetVoiceName(i,b,256)
                print("VOICE",i,repr(b.value),flush=True)
            lib.YongDe_Uninitialize.argtypes=[]
            lib.YongDe_Uninitialize.restype=None
            lib.YongDe_Uninitialize()
    except Exception as e:
        print("INDEPENDENT_ERROR",type(e).__name__,str(e),flush=True)
        traceback.print_exc()
