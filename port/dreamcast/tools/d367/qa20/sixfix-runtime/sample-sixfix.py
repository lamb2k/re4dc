from pathlib import Path
import ctypes,json,re,struct,sys,time
from ctypes import wintypes as W
cap=Path(sys.argv[1]);deadline=time.monotonic()+58
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
k.ReadProcessMemory.argtypes=[W.HANDLE,W.LPCVOID,W.LPVOID,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,ctypes.POINTER(W.DWORD)]
k.GetProcessTimes.argtypes=[W.HANDLE]+[ctypes.POINTER(W.FILETIME)]*4
while time.monotonic()<deadline:
    if (cap/'owned-process.json').exists() and (cap/'flycast.log').exists() and (cap/'run-start.json').exists():
        match=re.findall(r'RAM\(16 MB\) ([0-9A-Fa-f]+)',(cap/'flycast.log').read_text(errors='replace'))
        if match:break
    time.sleep(.1)
else:raise SystemExit('No owned RAM')
assert json.loads((cap/'run-start.json').read_text())['elf_sha256']=='52a5d671203e22e9f20728a8fbc3b61e080f7ba44e06891df635248a374dd053', 'Exact candidate ELF identity required'
owner=json.loads((cap/'owned-process.json').read_text());h=k.OpenProcess(0x0010|0x0400,False,owner['pid']);assert h
path=ctypes.create_unicode_buffer(32768);size=W.DWORD(len(path));assert k.QueryFullProcessImageNameW(h,0,path,ctypes.byref(size))
assert Path(path.value).resolve()==Path(owner['path']).resolve()
c,e,kt,ut=(W.FILETIME() for _ in range(4));assert k.GetProcessTimes(h,ctypes.byref(c),ctypes.byref(e),ctypes.byref(kt),ctypes.byref(ut))
assert (c.dwHighDateTime<<32|c.dwLowDateTime)==owner['start_filetime']
ram=int(match[-1],16)
def read(a,n):
    b=ctypes.create_string_buffer(n);got=ctypes.c_size_t()
    if not k.ReadProcessMemory(h,ram+a-0x8c000000,b,n,ctypes.byref(got)) or got.value!=n:raise EOFError()
    return b.raw
u32=lambda a:struct.unpack('<I',read(a,4))[0]
SSLOOP_ADDR=0x8c395c84
start=time.monotonic();deadline=start+55
with (cap/'readonly-combat-io.jsonl').open('x') as out:
    while time.monotonic()<deadline:
        try:
            pg=0x8c361c18;room=struct.unpack('<H',read(pg+0x4f9e,2))[0]
            if room!=0x100:
                time.sleep(.05);continue
            world_safe=u32(pg+0x170)==0 and list(read(pg+0x20,2))==[3,0] and not(u32(pg+0x5010)&0x10000000) and read(SSLOOP_ADDR+0x28,1)[0]==0
            v=struct.unpack('<11I',read(0x8c3f170c,44));bindings=[]
            for j in (range(4) if world_safe else ()):
                a=0x8c3f1a84+48*j;arc,sz,records,n,slots,budget,hot,res=struct.unpack('<8I',read(a,32))
                if not arc:continue
                assert 0<n<=255;keys=[]
                slot_bytes=read(slots,16*n);record_bytes=read(records,20*n)
                for i in range(n):
                    ptr,pins,stamp=struct.unpack_from('<IIQ',slot_bytes,16*i)
                    if ptr or pins:
                        off,bytes_,crc,fnv,flags=struct.unpack_from('<5I',record_bytes,20*i)
                        keys.append([i,bytes_,f'{crc:08x}-{fnv:08x}',pins])
                bases=[u32(a+36),u32(a+40)];slab_bytes=u32(a+44);joined=bool(read(a+33,1)[0]);storage=[]
                for i in range(n):
                    ptr,pins,stamp=struct.unpack_from('<IIQ',slot_bytes,16*i)
                    if ptr:
                        bytes_=struct.unpack_from('<I',record_bytes,20*i+4)[0];owned=bases[:1] if joined else bases
                        cell=next((j for j,base in enumerate(owned) if base and base<=ptr and ptr+bytes_<=base+slab_bytes*(2 if joined else 1)),None)
                        storage.append(dict(entry=i,ptr=hex(ptr),pins=pins,reserved_region=cell,offset=ptr-owned[cell] if cell is not None else None))
                bindings.append(dict(bytes=sz,resident=res,budget=budget,bounded=read(a+32,1)[0],joined=joined,keys=keys,slab_bases=[hex(b)for b in bases],slab_bytes=slab_bytes,storage=storage))
            lh_names='pick_max_us async_max_us async_fails async_reads hit_max_us alloc_fails refills yields misses hits copies read_bytes reads'.split()
            lh=dict(zip(lh_names,struct.unpack('<13I',read(0x8c2de300,52))))
            lh.update(cells=list(struct.unpack('<4i',read(0x8c2de358,16))),slots=list(struct.unpack('<2i',read(0x8c2de36c,8))),want=list(struct.unpack('<2i',read(0x8c2de2bc,8))),job_state=u32(0x8c2de2f0))
            row=dict(host_s=round(time.monotonic()-start,3),frame=u32(pg+0x51e4),room=room,phase=list(read(pg+0x20,2)),stop=hex(u32(pg+0x170)),motion=dict(hits=v[0],misses=v[1],evictions=v[2],loads=v[3],failures=v[4],resident=v[5],peak_cache=v[6],pinned=v[7],peak_pinned=v[8],metadata=v[9],hot=v[10],bytes_read=struct.unpack('<Q',read(0x8c3f170c+44,8))[0],worst_wait_us=struct.unpack('<Q',read(0x8c3f170c+52,8))[0]),bindings=bindings,hand=lh,disc=dict(reads=u32(0x8c3b7454),bytes=struct.unpack('<Q',read(0x8c3b744c,8))[0],block_us=struct.unpack('<Q',read(0x8c3b7444,8))[0],last_sector=u32(0x8c3b7404),last_count=u32(0x8c3b7400)),weapon=list(read(pg+0x4fb0,4)),old_wep=read(0x8c370ee2,1)[0])
            row['texture']=dict(loads=u32(0x8c412104),preload_loads=u32(0x8c4190d8),load_opens=u32(0x8c41993c),metadata_evictions=u32(0x8c41bc3c))
            row['cache']={}
            for label,addr in [('data',0x8c41fb74),('inode',0x8c41fbb4)]:
                ptrs=struct.unpack('<16I',read(addr,64));row['cache'][label]=[u32(p+4) if 0x8c000000<=p<0x8cfffff0 else None for p in ptrs]
            actors=[];ptr=u32(0x8c355238+0x14) if world_safe else 0;seen=set()
            while ptr and len(actors)<64:
                if not 0x8c000000<=ptr<0x8cfff000 or ptr in seen:break
                seen.add(ptr);a=read(ptr,0x328)
                actors.append(dict(ptr=hex(ptr),be_flag=hex(struct.unpack_from('<I',a,4)[0]),id=a[0x100],type=a[0x101],routine=list(a[0xfc:0x100]),hp=struct.unpack_from('<h',a,0x320)[0],damage=list(a[0x324:0x328]),pos=struct.unpack_from('<3f',a,0x94)))
                ptr=struct.unpack_from('<I',a,8)[0]
            row['actors']=actors;row['world_safe']=world_safe;row['ssloop']=read(SSLOOP_ADDR+0x28,1)[0];row['health']=struct.unpack('<3H',read(pg+0x4fa4,6))
            pl=u32(0x8c355580) if world_safe else 0
            if 0x8c000000<=pl<0x8cfff000:
                row['player_routines']=list(read(pl+0xfc,4));row['player_pos']=struct.unpack('<3f',read(pl+0x94,12));row['player_yaw']=struct.unpack('<f',read(pl+0xa4,4))[0];row['health']=struct.unpack('<3H',read(pg+0x4fa4,6))
            out.write(json.dumps(row)+'\n');out.flush()
        except (EOFError,struct.error):break
        time.sleep(.05)
print('Read-only combat I/O sample complete')