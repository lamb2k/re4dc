"""Read-only exact012-state continuation observer for originalradio return; only owned WM_CLOSE."""
from pathlib import Path
import ctypes as C,ctypes.wintypes as W,json,time,re,struct,sys,hashlib,importlib.util,shutil,traceback
L=Path(__file__).parent;D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');cap=Path(sys.argv[1]).resolve();assert cap==D/'route-walk-controlled-native-radio013'
k=C.WinDLL('kernel32',use_last_error=True);u=C.WinDLL('user32',use_last_error=True)
k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE;k.GetProcessTimes.argtypes=[W.HANDLE]+[C.POINTER(W.FILETIME)]*4;k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)];k.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)];k.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD];k.CloseHandle.argtypes=[W.HANDLE]
u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)];u.GetClassNameW.argtypes=[W.HWND,W.LPWSTR,C.c_int];u.PostMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM];CALL=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM);u.EnumWindows.argtypes=[CALL,W.LPARAM]
h=None;events=[];last=None;closed_sent=False
(D/(cap.name+'-observer-ready.json')).write_text(json.dumps(dict(scope=__doc__,sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))+'\n')
def check():
 assert k.WaitForSingleObject(h,0)==258,'Owned process exited'
 p=C.create_unicode_buffer(32768);n=W.DWORD(32768);assert k.QueryFullProcessImageNameW(h,0,p,C.byref(n));assert Path(p.value).resolve()==cap/'flycast.exe'
 a,b,c,d=(W.FILETIME()for _ in range(4));assert k.GetProcessTimes(h,C.byref(a),C.byref(b),C.byref(c),C.byref(d));assert a.dwLowDateTime+(a.dwHighDateTime<<32)==owner['start_filetime']
def read(a,n):
 assert 0x8c000000<=a and a+n<=0x8d000000;buf=C.create_string_buffer(n);got=C.c_size_t();assert k.ReadProcessMemory(h,ram+a-0x8c000000,buf,n,C.byref(got))and got.value==n;return buf.raw
u32=lambda a:struct.unpack('<I',read(a,4))[0]
def close():
 global closed_sent
 if closed_sent:return
 check();wins=[]
 @CALL
 def cb(w,_):
  p=W.DWORD();u.GetWindowThreadProcessId(w,C.byref(p));c=C.create_unicode_buffer(256);u.GetClassNameW(w,c,256)
  if p.value==owner['pid']and c.value=='SDL_app':wins.append(int(w))
  return True
 assert u.EnumWindows(cb,0)and len(wins)==1;assert u.PostMessageW(wins[0],0x10,0,0);closed_sent=True;events.append(dict(exact_owned_WM_CLOSE=True,process_age=age()))
def sample():
 pg=u32(0x8c2e91dc)
 if not 0x8c000000<=pg<0x8cffa000:return None
 before=(u32(pg+0x51e4),read(pg+0x20,2))
 row=dict(process_age=age(),pg=pg,frame=before[0],phase=list(before[1]),room=hex(struct.unpack('<H',read(pg+0x4f9e,2))[0]),chapter=read(pg+0x4f8a,1)[0],Stop=hex(u32(pg+0x170)),health=list(struct.unpack('<4H',read(pg+0x4fa4,8))),CardStatus=hex(u32(pg+8)),status3=hex(u32(pg+0x5018)),partner_ptr=hex(u32(0x8c39d6fc)))
 card=u32(0x8c396744)
 if 0x8c000000<=card<0x8cfff000:row['card_source_correlated']=dict(pointer=hex(card),routines=list(read(card+4,4)),status=hex(u32(card+0x10)),type=struct.unpack('<i',read(card+0x14,4))[0],slot=read(card+0x1c,1)[0],save_no=read(card+0x1d,1)[0],error=struct.unpack('<i',read(card+0x20,4))[0])
 rd=0x8c3b9314;nr=struct.unpack('<H',read(rd+2,2))[0];sv=u32(rd+0x18)
 if 0<nr<256 and 0x8c000000<=sv and sv+nr*0xd8<=0x8d000000:
  tb=read(sv,nr*0xd8);rsf=next((struct.unpack_from('<I',tb,i*0xd8+4)[0]for i in range(nr)if tb[i*0xd8:i*0xd8+2]==bytes([2,4])),None);row['saved_RSF204']=hex(rsf)if rsf is not None else None
  if tb!=read(sv,nr*0xd8)or nr!=struct.unpack('<H',read(rd+2,2))[0]or sv!=u32(rd+0x18):return None
 if before!=(u32(pg+0x51e4),read(pg+0x20,2))or pg!=u32(0x8c2e91dc):return None
 return row
def capture(row,label):
 check();assert age()<38.5 and shutil.disk_usage(D).free>=18*1024**3+64*1024**2
 matches=re.findall(r'fb=[0-9a-f]+,[0-9a-f]+',(cap/'run-output.txt').read_text(errors='replace'))
 if not matches:
  pair=(u32(0x8c483e00+312),u32(0x8c483e00+320));assert pair==(u32(0x8c483e00+312),u32(0x8c483e00+320))and pair==(0x230980,0x630980),'Stable inherited frozenPVRpair required'
  matches=['fb=%x,%x'%tuple(((0xd2800000+(v&0x7fffff))*2)&0xffffffff for v in pair)]
 spec=importlib.util.spec_from_file_location('controlled_load_capture',L/'capture-original-J-fast-RGB565.py');fc=importlib.util.module_from_spec(spec);spec.loader.exec_module(fc)
 shot=cap/'shots'/('controlled-'+label);shot.mkdir(parents=True,exist_ok=False)
 for n in ['emu.cfg','flycast.log','flycast.pid']:shutil.copyfile(cap/n,shot/n)
 (shot/'boot.log').write_text(matches[-1]+'\n',encoding='utf-16');before=sample();fc.capture(shot,shot/'frames');after=sample()
 (shot/'controlled-context.json').write_text(json.dumps(dict(scope='Controlled originalradio continuation; inheritedRSF7/openlogs are not newexecution orcompletion. Actualclose/hash, Stop/frame progress and inspectedgameplay required.',observation=row,before=before,after=after,pngs=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())for p in(shot/'frames').glob('*.png')]),indent=2)+'\n')
try:
 until=time.monotonic()+70
 while not(cap/'owned-process.json').exists():assert time.monotonic()<until;time.sleep(.05)
 owner=json.loads((cap/'owned-process.json').read_text());h=k.OpenProcess(0x1000|0x10|0x100000,False,owner['pid']);assert h;check();age0=time.time()-(owner['start_filetime']/1e7-11644473600);mono0=time.monotonic();age=lambda:age0+time.monotonic()-mono0
 start=json.loads((cap/'run-start.json').read_text());assert start['elf_sha256']=='4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f'and start['disc_sha256']=='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6'
 cfg=(cap/'emu.cfg').read_text();assert re.search(r'(?m)^Dreamcast\.AutoLoadState = yes\s*$',cfg),'Controlled fullstate continuation requires AutoLoadState=yes'
 while True:
  check();matches=re.findall(r'RAM\(16 MB\)\s+([0-9a-fA-F]+)',(cap/'flycast.log').read_text(errors='replace'))
  if matches:ram=int(matches[-1],16);break
  assert age()<38,'Cold RAM deadline';time.sleep(.05)
 shots=set();close_age=None;close_frame=None
 with(cap/'controlled-load-observations.jsonl').open('x')as out:
  while k.WaitForSingleObject(h,0)==258 and age()<39:
   check();row=sample()
   if row:
    last=row;out.write(json.dumps(row)+'\n');out.flush()
    text=(cap/'run-output.txt').read_text(errors='replace')
    match=re.search(r'subscreen backing: close area=[^\n]*hash=([0-9a-f]+)\s+(ok|MISMATCH)\b',text)
    if close_age is None and match:
     close_age=age();close_frame=row['frame'];events.append(dict(backing_close_log=True,hash=match.group(1),result=match.group(2),process_age=close_age,frame=close_frame))
    labels=[]
    if 2<age()<37:labels.append('continued-radio')
    if close_age is not None and age()>=close_age+2 and row['phase'][0]==3 and age()<37:labels.append('after-radio-close')
    if 36<=age()<37:labels.append('deadline-context')
    for label in labels:
     if label not in shots:
      shots.add(label)
      try:capture(row,label)
      except Exception as e:events.append(dict(optional_capture_unavailable=repr(e),label=label))
   time.sleep(.04)
 if k.WaitForSingleObject(h,0)==258:close()
except BaseException as e:
 events.append(dict(observer_failure=repr(e),traceback=traceback.format_exc()))
 if h and k.WaitForSingleObject(h,0)==258:
  try:close()
  except Exception as x:events.append(dict(close_failed=repr(x)))
 raise
finally:
 if h:k.CloseHandle(h)
 if cap.exists():(cap/'controlled-native-load-observer-summary.json').write_text(json.dumps(dict(scope=__doc__,last=last,events=events,owned_close_sent=closed_sent,source_fields_not_acceptance_alone=True),indent=2)+'\n')
