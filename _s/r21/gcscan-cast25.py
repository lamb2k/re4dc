import sys, struct
T="/root/work/lanes/cast-ps2-25/port/dreamcast/tools"
sys.path.insert(0,T)
from assetpipe.rooms import GcIso
import convert_tpl as ct, prepare_native_ui as pnu
want=set(sys.argv[1:])
g=GcIso("/root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso")
try:
    import room_smd as rs
except Exception as e:
    rs=None; print("no room_smd",e)
MAG=b"\x00\x20\xaf\x30"
n=0
for p in [q for q in sorted(g.files) if q.lower() in ("etc/core.das","etc/memcard.das","op/op01.das","op/op02.das","op/op03.das")]:
    try: d=g.read(p)
    except Exception: continue
    if p.lower().endswith(".das") and rs is not None and d[:32]==rs.CONTAINER_MAGIC:
        try: d=rs.decode_das(d)
        except Exception as e: print("das raw",p)
    i=d.find(MAG)
    while i>=0:
        try:
            for j,im in enumerate(ct.parse_tpl(d[i:])):
                k=pnu.image_identity(im)[0]; n+=1
                if k in want: print("HIT",k,p,hex(i),j,im.width,im.height,im.format,flush=True)
        except Exception: pass
        i=d.find(MAG,i+4)
print("images",n)
