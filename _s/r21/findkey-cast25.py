import sys, glob, hashlib
sys.path.insert(0, "/root/work/lanes/cast-ps2-25/port/dreamcast/tools/d367/charbake")
import types; sys.modules["numpy"]=types.ModuleType("numpy")
import cb_tex as cb
keys = sys.argv[1:]
paks = sorted(glob.glob("/root/re4data/private/*/dc/tex.pak") + glob.glob("/root/re4data/private/*/*/dc/tex.pak"))
for p in paks:
    for k in keys:
        try:
            b = cb.pak_get(p, cb.parse_key(k))
        except Exception as e:
            continue
        if b: print(k, hashlib.sha256(b).hexdigest()[:12], p)
