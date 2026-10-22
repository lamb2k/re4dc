from pathlib import Path
import ctypes as C,ctypes.wintypes as W,json,time,re,struct,sys,hashlib,importlib.util,shutil,traceback
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');cap=Path(sys.argv[1]).resolve();assert cap==D/'route-walk-controlled-event002';events=[];rows=[];h=None;owner=None;baseline_y=None;baseline_clear=False;observed_held=False;last=None;first_frame=None;closed_sent=False;wave_seen=set()
spec=importlib.util.spec_from_file_location('controlled_fast_capture',L/'capture-original-J-fast-RGB565.py');fc=importlib.util.module_from_spec(spec);spec.loader.exec_module(fc)
k=C.WinDLL('kernel32',use_last_error=True);u=C.WinDLL('user32',use_last_error=True);k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE;k.GetProcessTimes.argtypes=[W.HANDLE]+[C.POINTER(W.FILETIME)]*4;k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)];k.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)];k.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD];k.CloseHandle.argtypes=[W.HANDLE];u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)];u.GetClassNameW.argtypes=[W.HWND,W.LPWSTR,C.c_int];u.PostMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM];CALL=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM);u.EnumWindows.argtypes=[CALL,W.LPARAM]
(D/(cap.name+'-observer-ready.json')).write_text(json.dumps(dict(scope='CONTROLLED EVENT COVERAGE, read-only observer/no input',observer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))+'\n')
def check():
 assert k.WaitForSingleObject(h,0)==258,'Owned process exited';b=C.create_unicode_buffer(32768);n=W.DWORD(32768);assert k.QueryFullProcessImageNameW(h,0,b,C.byref(n));assert Path(b.value).resolve()==cap/'flycast.exe';a,b,c,d=(W.FILETIME()for _ in range(4));assert k.GetProcessTimes(h,C.byref(a),C.byref(b),C.byref(c),C.byref(d));assert a.dwLowDateTime+(a.dwHighDateTime<<32)==owner['start_filetime']
def read(a,n):
 assert 0x8c000000<=a and a+n<=0x8d000000;buf=C.create_string_buffer(n);got=C.c_size_t();assert k.ReadProcessMemory(h,ram+a-0x8c000000,buf,n,C.byref(got))and got.value==n;return buf.raw
u32=lambda a:struct.unpack('<I',read(a,4))[0]
def close():
 global closed_sent
 if closed_sent:return
 check();wins=[]
 @CALL
 def cb(w,_):
  p=W.DWORD();u.GetWindowThreadProcessId(w,C.byref(p));b=C.create_unicode_buffer(256);u.GetClassNameW(w,b,256)
  if p.value==owner['pid']and b.value=='SDL_app':wins.append(int(w))
  return True
 assert u.EnumWindows(cb,0)and len(wins)==1;assert u.PostMessageW(wins[0],0x10,0,0);closed_sent=True;events.append(dict(exact_owned_WM_CLOSE=True))
def capture(label,row):
 check();assert shutil.disk_usage(D).free>=18*1024**3+64*1024**2;fb=re.findall(r'fb=[0-9a-f]+,[0-9a-f]+',(cap/'run-output.txt').read_text(errors='replace'));assert fb,'Framebuffer not ready';p=cap/'shots'/('controlled-'+label);p.mkdir(parents=True,exist_ok=False)
 for name in ['emu.cfg','flycast.log','flycast.pid']:shutil.copyfile(cap/name,p/name)
 (p/'boot.log').write_text(fb[-1]+'\n',encoding='utf-16');before=u32(row['pg']+0x51e4);fc.capture(p,p/'frames');after=u32(row['pg']+0x51e4);(p/'controlled-context.json').write_text(json.dumps(dict(scope='CONTROLLED teleport/scripted-event coverage; not authentic combat or hardware acceptance',source_frame_interval=[before,after],observation=row,pngs=[dict(path=str(x),sha256=hashlib.sha256(x.read_bytes()).hexdigest())for x in(p/'frames').glob('*.png')]),indent=2)+'\n');events.append(dict(screenshot=str(p),source_interval=[before,after]))
try:
 until=time.monotonic()+70
 while not(cap/'owned-process.json').exists():assert time.monotonic()<until;time.sleep(.05)
 owner=json.loads((cap/'owned-process.json').read_text());h=k.OpenProcess(0x1000|0x10|0x100000,False,owner['pid']);assert h;check();age0=time.time()-(owner['start_filetime']/1e7-11644473600);mono0=time.monotonic();age=lambda:age0+time.monotonic()-mono0
 start=json.loads((cap/'run-start.json').read_text());assert start['elf_sha256']=='4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f'and start['disc_sha256']=='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6'
 while True:
  check();m=re.findall(r'RAM\(16 MB\)\s+([0-9a-fA-F]+)',(cap/'flycast.log').read_text(errors='replace'))
  if m:ram=int(m[-1],16);break
  if age()>38:close();raise TimeoutError('ColdRAM deadline')
  time.sleep(.05)
 captured_before=False;out=cap/'controlled-events-observations.jsonl'
 with out.open('x')as f:
  while k.WaitForSingleObject(h,0)==258 and age()<39:
   check();pg=u32(0x8c2e91dc)
   if not 0x8c000000<=pg<0x8cffa000:time.sleep(.03);continue
   room=struct.unpack('<H',read(pg+0x4f9e,2))[0];phase=list(read(pg+0x20,2))
   if room!=0x201 or phase!=[3,0]:time.sleep(.03);continue
   pl=u32(0x8c39d700)
   if not 0x8c000000<=pl<0x8cffff00:time.sleep(.03);continue
   row=dict(pg=pg,process_age=age(),frame=u32(pg+0x51e4),room=hex(room),phase=phase,Stop=hex(u32(pg+0x170)),health=list(struct.unpack('<4H',read(pg+0x4fa4,8))),player_pos=list(struct.unpack('<3f',read(pl+0x94,12))),status1=hex(u32(pg+0x5010)),room_flags0=hex(u32(pg+0x174)),door_flags=hex(u32(pg+0x51cc)))
   rd=0x8c3b9314;nr=struct.unpack('<H',read(rd+2,2))[0];sv=u32(rd+0x18);rsf=None
   if 0<nr<256 and 0x8c000000<=sv<0x8cffff00:
    tb=read(sv,nr*0xd8);rsf=next((struct.unpack_from('<I',tb,i*0xd8+4)[0]for i in range(nr)if tb[i*0xd8:i*0xd8+2]==b'\x02\x01'),None)
   row['saved_RSF']=hex(rsf)if rsf is not None else None
   if first_frame is None:first_frame=row['frame']
   if rsf is not None and not(rsf&0x04000000):baseline_clear=True
   st=u32(0x8c3bdd64);door=u32(st+0x53*4)if 0x8c000000<=st<0x8cfff000 else 0
   if 0x8c000000<=door<0x8cfff000:
    dy=struct.unpack('<f',read(door+0x98,4))[0];row.update(door_Smd53=hex(door),door_y=dy)
    if baseline_y is None:baseline_y=dy;events.append(dict(initial_door_y=dy,frame=row['frame']))
    row['door_delta_y']=dy-baseline_y
   p=0x8c3b93cc+0x8c;seen=set();row['AEV0A_enabled']=None;row['areas']={}
   for _ in range(1024):
    v=u32(p)
    if v==0xffffffff:break
    p=v|0x80000000
    if not 0x8c000000<=p<0x8cffff00 or p in seen:break
    seen.add(p)
    if v&0x80000000:
     no=read(p+0x36,1)[0];row['areas'][hex(no)]=dict(enabled=bool(read(p+0x34,1)[0]&1),func=hex(u32(p+0x40)))
     if no==0xa:row['AEV0A_enabled']=bool(read(p+0x34,1)[0]&1);row['AEV0A']=hex(p)
   p=u32(0x8c39d3b8+0x14);seen=set();boss=None;row['actors']=[];row['switch']=None;row['barred']=[]
   while p and p not in seen and len(seen)<128:
    assert 0x8c000000<=p<0x8cfff000;seen.add(p);b=read(p,0x3a0)
    ar=dict(ptr=hex(p),id=b[0x100],type=b[0x101],source_list=b[0x398],hp=struct.unpack_from('<h',b,0x320)[0],be_flag=hex(struct.unpack_from('<I',b,4)[0]),routines=list(b[0xfc:0x100]),pos=list(struct.unpack_from('<3f',b,0x94)));row['actors'].append(ar)
    if ar['source_list']in[0x57,0x5b,0x5c]and ar['hp']>0:wave_seen.add(ar['source_list'])
    if ar['id']==0x4b:row['switch']=dict(ar,opened=struct.unpack('<i',read(p+0x5f4,4))[0],state=struct.unpack('<i',read(p+0x5f0,4))[0],etc_no=read(p+0x614,1)[0])
    if ar['id']==0x4c:row['barred'].append(dict(ar,status=struct.unpack('<i',read(p+0x61c,4))[0],open_flag=struct.unpack('<i',read(p+0x620,4))[0],etc_no=read(p+0x62e,1)[0]))
    if b[0x100:0x102]==bytes([0x1b,0xa]):boss=dict(ptr=hex(p),hp=struct.unpack_from('<h',b,0x320)[0],be_flag=hex(struct.unpack_from('<I',b,4)[0]),list_no=b[0x398],routines=list(b[0xfc:0x100]))
    p=struct.unpack_from('<I',b,8)[0]
   row['Garrador']=boss
   row['wave_lists_seen']=sorted(wave_seen)
   if u32(pg+0x5010)&0x10000000:observed_held=True
   row.update(baseline_RSF5_clear_seen=baseline_clear,event_hold_seen=observed_held);rows.append(row);last=row;f.write(json.dumps(row)+'\n');f.flush()
   if baseline_clear and not captured_before and row['frame']>=first_frame+60 and row['switch']:
    try:capture('before-switch-action',row);captured_before=True
    except Exception as e:events.append(dict(baseline_capture_pending=repr(e)))
   log=(cap/'run-output.txt').read_text(errors='replace')
   goal=bool(baseline_clear and rsf is not None and rsf&0x04000000 and observed_held and row['switch']and row['switch']['opened']==1 and any(x['etc_no']==0x10 and x['status']==1 and x['open_flag']==1 for x in row['barred'])and all(row['areas'].get(hex(no),{}).get('enabled')is False for no in [0,1,3,0x28,5])and wave_seen=={0x57,0x5b,0x5c}and not(u32(pg+0x5010)&0x10000000)and u32(pg+0x170)==0 and 'warp: goto 0 at room frame'in log)
   if goal:events.append(dict(original_switch_trap_and_primary_wave_observed=row));capture('original-switch-and-wave',row);close();break
   time.sleep(.025)
 if k.WaitForSingleObject(h,0)==258 and not closed_sent:
  if last:
   try:capture('inner-deadline',last)
   except Exception as e:events.append(dict(deadline_capture_unavailable=repr(e)))
  close()
except Exception as e:
 events.append(dict(observer_error=repr(e),traceback=traceback.format_exc()))
 if h and k.WaitForSingleObject(h,0)==258:
  try:close()
  except Exception as x:events.append(dict(close_error=repr(x)))
finally:
 if h:k.CloseHandle(h)
 if cap.exists():(cap/'controlled-events-observer.json').write_text(json.dumps(dict(scope='CONTROLLED SCRIPT EVENT COVERAGE, readonlyprocess observer plus exactowned WM_CLOSE only; no gameplay memory writes or combat inputs. Nativefixture carriesprior001RSF0SETUP; actualswitchRSF5/barred/trapcallback/waveobservedseparately; authentic294/127 neverseeded/modified.',owner=owner,baseline_door_y=baseline_y,baseline_RSF5_clear_seen=baseline_clear,events=events,last=last),indent=2)+'\n')
