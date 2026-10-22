"""Original farm entry return-door interaction with preserved source state."""
from pathlib import Path
import ctypes,json,math,sys,time
cap=Path(sys.argv[1]);deps=Path(sys.argv[2]);seed=Path(sys.argv[3]) if len(sys.argv)>3 and sys.argv[3] else None
sys.path.insert(0,str(deps));import checkpoint_runner18 as pad
pad.KEYS.update(fwd=(0x17,0),back=(0x25,0),rtrig=(0x2f,0),turnleft=(0x24,0),turnright=(0x26,0));pad.VK.update(fwd=0x49,back=0x4b,rtrig=0x56,turnleft=0x4a,turnright=0x4c)
pad.user32.PostMessageW.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_size_t,ctypes.c_ssize_t]
k=ctypes.WinDLL('kernel32',use_last_error=True);k.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];k.OpenProcess.restype=ctypes.c_void_p
k.QueryFullProcessImageNameW.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)]
k.GetProcessTimes.argtypes=[ctypes.c_void_p]+[ctypes.POINTER(ctypes.c_ulonglong)]*4;k.CloseHandle.argtypes=[ctypes.c_void_p]
waiting=time.monotonic()+15
while time.monotonic()<waiting:
 try: value=(cap/'flycast.pid').read_text().strip()
 except FileNotFoundError:value=''
 if value.isdigit() and (cap/'read-only-state.jsonl').exists():break
 time.sleep(.05)
else:raise SystemExit('No owned process/read-only observer; no controller input')
pid=int(value);h=k.OpenProcess(0x1000,False,pid);assert h
path=ctypes.create_unicode_buffer(32768);size=ctypes.c_ulong(len(path));assert k.QueryFullProcessImageNameW(h,0,path,ctypes.byref(size));assert Path(path.value).resolve()==(cap/'flycast.exe').resolve()
times=[ctypes.c_ulonglong() for _ in range(4)];assert k.GetProcessTimes(h,*[ctypes.byref(x) for x in times]);start=times[0].value
stage='approach';target_ptr=None;fired=0;seen={};last_frame=None;nav=0;stalls=0;last_position=None
if seed and (seed/'normal-farm-door-progress.json').exists():
 prior=json.loads((seed/'normal-farm-door-progress.json').read_text());stage=prior['stage'];target_ptr=prior['target_ptr'];fired=prior['fired'];nav=prior['nav']
logfile=(cap/'normal-farm-door-controller.jsonl').open('x')
def latest():
 rows=(cap/'read-only-state.jsonl').read_text().splitlines();return json.loads(rows[-1])
def record(row,**extra):
 item={'stage':stage,'host_s':time.monotonic(),'state':row,**extra};logfile.write(json.dumps(item)+'\n');logfile.flush()
 (cap/'normal-farm-door-progress.json').write_text(json.dumps({'stage':stage,'target_ptr':target_ptr,'fired':fired,'nav':nav,'last_sample':row},indent=2)+'\n')
def live():
 t=[ctypes.c_ulonglong() for _ in range(4)]
 if not k.GetProcessTimes(h,*[ctypes.byref(x) for x in t]) or t[0].value!=start or t[1].value:raise EOFError('Owned PID ended')
 windows=pad.windows_of(pid)
 if not windows:raise EOFError('Owned windows ended')
 return windows
def post(names,down):
 windows=live()
 for key in names:
  scan,ext=pad.KEYS[key];flags=1|(scan<<16)|(ext<<24)
  if not down:flags|=(1<<30)|(1<<31)
  for hwnd in windows:
   if not pad.user32.PostMessageW(hwnd,0x100 if down else 0x101,pad.VK[key],flags):raise ctypes.WinError(ctypes.get_last_error())
def pulse(names,hold,row):
 record(row,keys=names,hold=hold)
 if names in (['shoot'],['reload']):
  button='a' if names==['shoot'] else 'b';post(['rtrig'],True);time.sleep(.4);post([button],True);time.sleep(hold);post([button],False);time.sleep(.15);post(['rtrig'],False)
 else:post(names,True);time.sleep(hold);post(names,False)
 time.sleep(.35)  # Wait beyond observer cadence before deciding the next facing/input.

deadline=time.monotonic()+42;attempts=0
try:
 while time.monotonic()<deadline:
  try:row=latest()
  except (FileNotFoundError,IndexError,json.JSONDecodeError):time.sleep(.05);continue
  live();g=row.get('global',{});frame=g.get('frame')
  if g.get('player_life',0)<=0:record(row,status='AUTHENTIC_DEATH_NO_ROLLBACK');break
  if g.get('room')!=0x103:
   if g.get('rno',[])[:2]==[3,0] and g.get('stop')==0:stage='finished';record(row,status='ORIGINAL_FARM_RETURN_DOOR_NEW_ROOM_FREE_PLAY');break
   time.sleep(.05);continue
  if g.get('rno',[])[:2]!=[3,0] or g.get('stop')!=0 or row.get('ssloop') or row.get('event_start_cnt'):time.sleep(.05);continue
  if frame==last_frame:time.sleep(.05);continue
  last_frame=frame;px,py,pz=row['player']['pos'];yaw=row['player']['ang'][1]
  dx=-49731-px;dz=7670-pz;distance=math.hypot(dx,dz);err=(math.atan2(dx,dz)-yaw+math.pi)%(2*math.pi)-math.pi
  if abs(err)>.15:pulse(['turnleft' if err>0 else 'turnright'],min(.65,abs(err)/2.25),row);time.sleep(.07);continue
  if px<-48300 and 5800<pz<9500:
   stage='gate';pulse(['a'],.2,row);attempts+=1;record(row,status='ORIGINAL_FARM_RETURN_DOOR_A_INPUT');time.sleep(2)
   if attempts>=4:record(latest(),status='FARM_DOOR_INTERACTION_NEEDS_REVIEW');break
  else:pulse(['fwd'],min(.5,distance/1900),row);time.sleep(.08)
except (EOFError,OSError) as exc:
 try:record(latest(),controller_stop=str(exc))
 except Exception:pass
finally:k.CloseHandle(h);logfile.close()