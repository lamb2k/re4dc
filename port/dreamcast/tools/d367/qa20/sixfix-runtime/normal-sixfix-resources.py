from pathlib import Path
import ctypes,json,math,sys,time,re,struct
from ctypes import wintypes as W
import fp_run_qa_sixfix as pad
from qa_owned_checkpoint import capture_checkpoint
cap=Path(sys.argv[1]);deadline=time.monotonic()+58
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,ctypes.POINTER(W.DWORD)]
k.GetProcessTimes.argtypes=[W.HANDLE]+[ctypes.POINTER(W.FILETIME)]*4
while time.monotonic()<deadline:
    if (cap/'owned-process.json').exists() and (cap/'readonly-combat-io.jsonl').exists() and (cap/'run-start.json').exists():break
    time.sleep(.1)
else:raise SystemExit('No own observer')
resume=Path(sys.argv[2]);meta=json.loads((cap/'run-start.json').read_text());prior=json.loads((resume/'run-start.json').read_text())
assert Path(meta['seed']).resolve()==(resume/'data').resolve(), 'Only exact supplied predecessor state'
assert meta['elf_sha256']==prior['elf_sha256']=='52a5d671203e22e9f20728a8fbc3b61e080f7ba44e06891df635248a374dd053'
assert meta['disc_sha256']==prior['disc_sha256']==json.loads((cap.parent/'sixfix-master/master-receipt.json').read_text())['track03_sha256']
owner=json.loads((cap/'owned-process.json').read_text());h=k.OpenProcess(0x1010,False,owner['pid']);assert h
path=ctypes.create_unicode_buffer(32768);size=W.DWORD(len(path));assert k.QueryFullProcessImageNameW(h,0,path,ctypes.byref(size))
assert Path(path.value).resolve()==Path(owner['path']).resolve()
c,e,kt,ut=(W.FILETIME() for _ in range(4));assert k.GetProcessTimes(h,ctypes.byref(c),ctypes.byref(e),ctypes.byref(kt),ctypes.byref(ut))
assert (c.dwHighDateTime<<32|c.dwLowDateTime)==owner['start_filetime']
(cap/'controller-source.py').write_bytes(Path(__file__).read_bytes())

k.ReadProcessMemory.argtypes=[W.HANDLE,W.LPCVOID,W.LPVOID,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
ram=int(re.findall(r'RAM\(16 MB\)\s+([0-9a-fA-F]+)',(cap/'flycast.log').read_text(errors='replace'))[-1],16)
def read(a,n):
 assert 0x8c000000<=a and a+n<=0x8d000000
 b=ctypes.create_string_buffer(n);got=ctypes.c_size_t();assert k.ReadProcessMemory(h,ram+a-0x8c000000,b,n,ctypes.byref(got))and got.value==n;return b.raw
u32=lambda a:struct.unpack('<I',read(a,4))[0]
pg=0x8c361c18;ss=0x8c395c84;im=0x8c360ef0
assert [z['address']for z in json.loads((cap.parent/'sixfix-elf-scoped-symbols.json').read_text())['symbols']if z['name']=='_SubScreenWk']==[ss]
assert [z['address']for z in json.loads((cap.parent/'sixfix-elf-scoped-symbols.json').read_text())['symbols']if z['name']=='_ItemMgr']==[im]

deadline=time.monotonic()+44;out=(cap/'normal-resource-controls.jsonl').open('x')
def write(z):out.write(json.dumps(z)+'\n');out.flush()
def latest():
 while time.monotonic()<deadline:
  try:return json.loads((cap/'readonly-combat-io.jsonl').read_text().splitlines()[-1])
  except (IndexError,json.JSONDecodeError):time.sleep(.05)
 raise TimeoutError('Observer row')
def stop(reason):
 tmp=cap/'owned-stop-request.tmp';tmp.write_text(json.dumps(dict(pid=owner['pid'],start_filetime=owner['start_filetime'],reason=reason))+'\n');tmp.replace(cap/'owned-stop-request.json')
def action(keys,hold=.16):
 z=latest();n=pad.press(owner['pid'],keys,hold);write(dict(before=z,keys=keys,hold=hold,windows=n));time.sleep(.18)
try:
 while time.monotonic()<deadline:
  z=latest()
  if z.get('world_safe')and 'player_pos'in z:break
  time.sleep(.05)
 assert z['health'][0]>=800 and z['room']==0x100
 initial=z;write(dict(checkpoint=capture_checkpoint(cap,'ambush-entry','Same-program original ambush entry','Original actors/events retained'),initial=z))
 until=time.monotonic()+9
 while time.monotonic()<until:
  z=latest();assert z.get('health',[0])[0]>=400
  if not z.get('world_safe'):time.sleep(.04);continue
  px,py,pz=z['player_pos'];en=[v for v in z['actors']if v['id']==18 and v['hp']>0 and int(v['be_flag'],16)&4]
  if not en:time.sleep(.15);continue
  target=min(en,key=lambda v:(v['pos'][0]-px)**2+(v['pos'][2]-pz)**2);dx=target['pos'][0]-px;dz=target['pos'][2]-pz;err=(math.atan2(dx,dz)-z['player_yaw']+math.pi)%(2*math.pi)-math.pi
  if abs(err)>.15:action(['turnleft'if err>0 else'turnright'],min(.35,abs(err)/2.25))
  elif math.hypot(dx,dz)<6500:action(['shoot'],.15);time.sleep(.35)
 time.sleep(1.2);before=latest();write(dict(checkpoint=capture_checkpoint(cap,'ambush-actions','Ordinary source ambush actions','Before Diagnostics'),before=before))
 logstart=len((cap/'run-output.txt').read_text(errors='replace'));action(['lt','rt','down'],.25);time.sleep(.3)
 assert 'qa: screen 0'in(cap/'run-output.txt').read_text(errors='replace')[logstart:],'Original QA chord did not open pause'
 action(['down']);action(['down']);action(['a']);time.sleep(.35)
 diag=read(0x8c42aa6c,3072).split(b'\0',1)[0].decode('ascii');assert diag.startswith('RE4DCQA1')and 'room=100'in diag
 (cap/'diagnostic-snapshot.txt').write_text(diag,encoding='utf-8');write(dict(diag=diag,checkpoint=capture_checkpoint(cap,'diagnostics','Original Diagnostics snapshot','Heap4/KOS/VRAM/drive/native alive rows, intentional pause')))
 frame=u32(pg+0x51e4);action(['b']);action(['b']);time.sleep(.5)
 while time.monotonic()<deadline:
  z=latest()
  if z.get('world_safe')and z['frame']>=frame+30:break
  time.sleep(.05)
 assert z.get('world_safe')and z['frame']>=frame+30
 write(dict(final=z,checkpoint=capture_checkpoint(cap,'diagnostics-return','Original Diagnostics close/gameplay return','Original heartbeat active; world advanced normally')))
 stop('SIXFIX_RESOURCE_GATE_COMPLETE')
except Exception as exc:
 import traceback
 write(dict(failure=repr(exc),traceback=traceback.format_exc()))
 try:write(dict(checkpoint=capture_checkpoint(cap,'resource-failure','Resource controller guard',repr(exc))))
 except Exception as shot:write(dict(screenshot_unavailable=repr(shot)))
 stop('SIXFIX_RESOURCE_CONTROL_GUARD')
finally:out.close();k.CloseHandle(h)
