"""Collect the M1 private capture from its own held Flycast instance."""
from pathlib import Path
import sys, ctypes as ct, re, struct, time, hashlib, json
import numpy as np
from PIL import Image
root = Path(__file__).resolve().parents[4]
sys.path.insert(0,str(root/"port/dreamcast/tools/flycast-harness"))
from read_pcs import Guest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"bake"))
from geometry import actor_strips
ev,room,symbol=Path(sys.argv[1]),int(sys.argv[2],16),int(sys.argv[3],16)
deadline=time.monotonic()+600
while not ((ev/"flycast.pid").exists() and (ev/"flycast.log").exists()):
    if time.monotonic()>deadline: raise TimeoutError("Flycast startup")
    time.sleep(.03)
g=Guest(str(ev))
k=ct.WinDLL("kernel32",use_last_error=True)
k.OpenProcess.restype=ct.c_void_p
hw=k.OpenProcess(0x28,False,g.pid)
if not hw: raise ct.WinError(ct.get_last_error())
k.WriteProcessMemory.argtypes=[ct.c_void_p,ct.c_void_p,ct.c_void_p,ct.c_size_t,ct.POINTER(ct.c_size_t)]
log=(ev/"flycast.log").read_text(errors="replace")
vbase=int(re.findall(r"VRAM64\(8 MB\) ([0-9A-Fa-f]+)",log)[-1],16)
off=symbol-0x8c000000
assert 0<=off<=0x1000000-44
resources=ev/"resources"
resources.mkdir()
def save_asset(data):
    ident=hashlib.sha256(data).hexdigest()
    f=resources/ident
    if not f.exists(): f.write_bytes(data)
    return ident
def ram(addr,size):
    addr &= 0x1fffffff
    offset=addr-0xc000000
    if not 0<=offset<=0x1000000-size: raise ValueError(f"RAM extent {addr:x} {size}")
    result=g.read(offset,size)
    if result is None: raise IOError("RAM read")
    return result
def still(pointer):
    offset=(pointer-0xa5000000)//2
    assert 0<=offset<=0x800000-640*480*2 and offset%4==0
    word=np.arange(offset//4,offset//4+640*480//2,dtype=np.uint32)
    mapped=(word&0xfffff)*2+(word>>20)
    lo,hi=int(mapped.min()),int(mapped.max())+1
    raw=g.read(vbase-g.base+lo*4,(hi-lo)*4)
    px=np.frombuffer(raw,dtype="<u4")[mapped-lo].view("<u2").reshape(480,640)
    rgb=np.stack([((px>>11)*255//31),((px>>5&63)*255//63),((px&31)*255//31)],axis=2)
    return Image.fromarray(rgb.astype("uint8"))
def actors(data):
    records=[]
    i=0
    while i<len(data):
        kind,n=struct.unpack_from("<II",data,i)
        item=data[i+8:i+8+n]
        if kind==3:
            model,info,part,pos,uv,serial,pals,stream_size,flags=struct.unpack_from("<9I",item)
            stream,norm,pc,nc,ps,ns,lod,crc,fnv,cull,blend=struct.unpack_from("<11I",item,84)
            blob=ram(stream,stream_size)
            ids=dict(stream=save_asset(blob),position=save_asset(ram(pos,pc*ps)),
                     normal=save_asset(ram(norm,nc*ns)) if norm and nc else None)
            # Coarse role descriptors alias info and part and submit unsigned UVs.
            # Native ModelData owns the signed/unsigned flag for its pTex.
            signed=False
            if info!=part:
                data=struct.unpack("<I",ram(info+12,4))[0]
                if data and struct.unpack("<I",ram(data+16,4))[0]==uv:
                    signed=bool(struct.unpack("<I",ram(data+32,4))[0]&0x80000000)
            last=max((ti for strip in actor_strips(blob,lod,signed) for _,_,ti in strip),default=-1)
            ids["uv_signed" if signed else "uv_unsigned"]=save_asset(ram(uv,4*(last+1)) if last>=0 else b"")
            records.append(ids)
        i+=8+n
    return records
import ctypes.wintypes as W
user=ct.windll.user32
@ct.WINFUNCTYPE(ct.c_int,W.HWND,W.LPARAM)
def title(h,_):
    owner=W.DWORD()
    user.GetWindowThreadProcessId(h,ct.byref(owner))
    if owner.value==g.pid: user.SetWindowTextW(h,"RE4DC eng-bench "+ev.name)
    return 1
peak=0
for pic in range(1,301):
    while time.monotonic()<deadline and g.alive():
        h=g.read(off,44)
        if h:
            seq,magic,r,num,frame,n,overflow,ptr,cap,fb,ack=struct.unpack("<11I",h)
            if seq==2*pic and magic==0x32434d46 and num==pic and r==room: break
        if pic==1: user.EnumWindows(title,0)
        time.sleep(.01)
    else: raise TimeoutError(f"waiting for picture {pic}")
    if overflow or not 0<n<=cap: raise ValueError(f"overflow {pic} at {n}/{cap}")
    data=ram(ptr,n)
    prefix=ev/f"picture-{pic:03d}"
    img=still(fb)
    ids=actors(data)
    prefix.with_suffix(".json").write_text(json.dumps(ids,separators=(",",":")))

    img.save(prefix.with_suffix(".png"),compress_level=1)
    prefix.with_suffix(".bin").write_bytes(h[:28]+data)
    assert g.read(off,44)==h, "guest advanced before ack"
    val=ct.c_uint32(seq)
    written=ct.c_size_t()
    if not k.WriteProcessMemory(hw,g.base+off+40,ct.byref(val),4,ct.byref(written)) or written.value!=4: raise ct.WinError(ct.get_last_error())
    peak=max(peak,n)
    if pic==1 or pic%50==0: print(f"picture {pic} game frame {frame} data {n} peak {peak} capacity {cap}",flush=True)
print("complete",flush=True)
