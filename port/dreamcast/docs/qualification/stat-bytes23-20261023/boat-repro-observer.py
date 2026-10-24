"""Owned boat fixture observer. Host-only, read-only RAM; run under census-bound-run.py."""
import ctypes, hashlib, json, pathlib, re, runpy, struct, subprocess, sys, threading, time
harness=pathlib.Path(sys.argv[1]);ppl_symbol=int(sys.argv[2],0);pg_symbol=int(sys.argv[3],0)
args=sys.argv[4:];cap=pathlib.Path(args[args.index('--cap')+1]);original=subprocess.Popen
stop=threading.Event();worker=None
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];kernel.OpenProcess.restype=ctypes.c_void_p
kernel.ReadProcessMemory.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
kernel.CloseHandle.argtypes=[ctypes.c_void_p]
kernel.QueryFullProcessImageNameW.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)]
def observe(proc):
    rows=[];errors=[];shots=[];handle=None;ram=None;t0=time.monotonic();last_shot=-100;boat_shots=0
    receipt={'pid':proc.pid,'pPL_symbol':hex(ppl_symbol),'pG_symbol':hex(pg_symbol),'stat_offset':'0xfc','boat_pointer_offset':'0x50c','read_only':True,'limitations':'Asynchronous diagnostic RAM/VRAM reads; no branch-hit counter or exact simulation-tick match.'}
    def read(off,n):
        if not 0<=off<=0x1000000-n:raise ValueError('outside16MiB')
        data=ctypes.create_string_buffer(n);count=ctypes.c_size_t()
        if not kernel.ReadProcessMemory(handle,ram+off,data,n,ctypes.byref(count)) or count.value!=n:raise OSError('incomplete owned RAM read')
        return data.raw
    def ptr(v):
        if not 0x0c000000<=(v&0x1fffffff)<0x0d000000:raise ValueError('not Dreamcast main RAM pointer')
        return v&0xffffff
    try:
        handle=kernel.OpenProcess(0x0010|0x0400,False,proc.pid)
        if not handle:raise ctypes.WinError(ctypes.get_last_error())
        image=ctypes.create_unicode_buffer(32768);length=ctypes.c_ulong(len(image))
        if not kernel.QueryFullProcessImageNameW(handle,0,image,ctypes.byref(length)):raise ctypes.WinError(ctypes.get_last_error())
        if pathlib.Path(image.value).resolve()!= (cap/'flycast.exe').resolve():raise RuntimeError('unexpected owned process image')
        receipt['owned_image']=image.value
        while not stop.is_set() and proc.poll() is None:
            elapsed=time.monotonic()-t0
            try:
                if ram is None:
                    matches=re.findall(r'RAM\(16 MB\) ([0-9A-Fa-f]+)',(cap/'flycast.log').read_text(errors='replace'))
                    if not matches:stop.wait(.1);continue
                    ram=int(matches[-1],16);receipt['host_ram_base']=hex(ram)
                player=struct.unpack('<I',read(ppl_symbol&0xffffff,4))[0]
                if not player:stop.wait(.1);continue
                po=ptr(player);stat=read(po+0xfc,4);pg=struct.unpack('<I',read(pg_symbol&0xffffff,4))[0];go=ptr(pg)
                glob=read(go+0x4f9c,0x20);room=struct.unpack('<H',glob[2:4])[0];weapon=glob[0x17];pl_type=glob[0x1c]
                boat=struct.unpack('<I',read(po+0x50c,4))[0];boat_state=None
                if boat:
                    try:
                        bo=ptr(boat);data=read(bo+0xfc,8);boat_state={'routine_bytes':list(data[:4]),'id':data[4],'type':data[5]}
                    except (OSError,ValueError):pass
                row={'host_s':round(elapsed,3),'pPL':hex(player),'pG':hex(pg),'room':f'{room:03x}','weapon_no':weapon,'pl_type':pl_type,'routine_bytes':list(stat),'native_word':f'{int.from_bytes(stat,"little"):08x}','canonical_word':f'{int.from_bytes(stat,"big"):08x}','m_pBoat':hex(boat),'boat':boat_state,'pos':list(struct.unpack('<fff',read(po+0x94,12)))}
                in_boat=stat[0]==0 and stat[1]==0x0f
                row['boat_routine_0_0f']=in_boat;rows.append(row)
                if in_boat and boat_state and boat_state['id']==0x0f and boat_shots<4 and elapsed-last_shot>=4:
                    full=(cap/'run-output.txt').read_text(errors='replace');fb=re.findall(r'fb=[0-9a-f]+,[0-9a-f]+',full)
                    if fb:
                        import importlib.util,shutil
                        spec=importlib.util.spec_from_file_location('owned_boat_vram',cap/'capture_ui_vram.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
                        shot=cap/'boat-stills'/f's{boat_shots:02d}-{int(elapsed*1000):06d}';shot.mkdir(parents=True,exist_ok=False)
                        for name in ('emu.cfg','flycast.log','flycast.pid'):shutil.copyfile(cap/name,shot/name)
                        (shot/'boot.log').write_text(fb[-1]+'\n',encoding='utf-16')
                        row['shot']=str(shot.relative_to(cap));(shot/'observed-state.json').write_text(json.dumps(row,indent=2)+'\n')
                        mod.capture(shot,shot/'frames');shots.append(row.copy());boat_shots+=1;last_shot=elapsed
            except (OSError,ValueError) as exc:
                if len(errors)<20:errors.append({'host_s':round(elapsed,3),'error':str(exc)})
            stop.wait(.15)
    except Exception as exc:errors.append({'fatal':repr(exc)})
    finally:
        if handle:kernel.CloseHandle(handle)
        receipt.update(samples=len(rows),boat_samples=sum(bool(r['boat_routine_0_0f']) for r in rows),shots=shots,errors=errors)
        (cap/'boat-ram-samples.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        (cap/'boat-observation.json').write_text(json.dumps(receipt,indent=2)+'\n')
class ObservedPopen(original):
    def __init__(self,*a,**kw):
        global worker
        cmd=a[0] if a else kw.get('args',[])
        super().__init__(*a,**kw)
        if isinstance(cmd,(list,tuple)) and pathlib.Path(str(cmd[0])).name.lower()=='flycast.exe':
            if worker is not None:raise RuntimeError('second guest refused by observer')
            worker=threading.Thread(target=observe,args=(self,),daemon=True);worker.start()
subprocess.Popen=ObservedPopen
try:
    sys.argv=[str(harness),*args];runpy.run_path(str(harness),run_name='__main__')
finally:
    stop.set()
    if worker:worker.join(timeout=5)
