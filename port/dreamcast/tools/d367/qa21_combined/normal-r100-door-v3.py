"""Original r100 window and road progression with preserved source collision/state."""
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
stage='house';target_ptr=None;fired=0;seen={};last_frame=None;nav=0;stalls=0;last_position=None
if seed and (seed/'normal-door-progress.json').exists():
 prior=json.loads((seed/'normal-door-progress.json').read_text());stage=prior['stage'];target_ptr=prior['target_ptr'];fired=prior['fired'];nav=prior['nav']
logfile=(cap/'normal-door-controller.jsonl').open('x')
def latest():
 rows=(cap/'read-only-state.jsonl').read_text().splitlines();return json.loads(rows[-1])
def record(row,**extra):
 item={'stage':stage,'host_s':time.monotonic(),'state':row,**extra};logfile.write(json.dumps(item)+'\n');logfile.flush()
 (cap/'normal-door-progress.json').write_text(json.dumps({'stage':stage,'target_ptr':target_ptr,'fired':fired,'nav':nav,'last_sample':row},indent=2)+'\n')
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

house=[(-83300,-38000),(-84200,-35000),(-84950,-32400)]
road=[(-89000,-28000),(-84000,-22000),(-76500,-17500),(-61000,-17200),(-53000,-15800),(-36000,-17000),(-14000,-15700),(8000,-13500),(45000,-10500),(76000,-11000),(97425,-9618)]
deadline=time.monotonic()+42
try:
 while time.monotonic()<deadline:
  try:row=latest()
  except (FileNotFoundError,IndexError,json.JSONDecodeError):time.sleep(.05);continue
  live();g=row.get('global',{});frame=g.get('frame')
  if g.get('player_life',0)<=0:record(row,status='AUTHENTIC_DEATH_NO_ROLLBACK');break
  if g.get('room')!=0x100:
   if g.get('rno',[])[:2]==[3,0] and g.get('stop')==0:stage='finished';record(row,status='ORIGINAL_DOOR_NEW_ROOM_FREE_PLAY');break
   time.sleep(.05);continue
  if g.get('rno',[])[:2]!=[3,0] or g.get('stop')!=0 or row.get('ssloop') or row.get('event_start_cnt'):
   time.sleep(.05);continue
  if frame==last_frame:time.sleep(.05);continue
  last_frame=frame;px,py,pz=row['player']['pos'];yaw=row['player']['ang'][1]
  if stage=='jump':
   if px<-87000:stage='road';nav=0;record(row,status='ORIGINAL_WINDOW_OUTSIDE')
   else:
    seen.setdefault('jump_wait',time.monotonic())
    if time.monotonic()-seen['jump_wait']<3:time.sleep(.1);continue
    if fired>=3:record(row,status='WINDOW_INPUT_NEEDS_SOURCE_ROUTE_REVIEW');break
    stage='house';nav=len(house);seen.pop('jump_wait',None);record(row,status='REALIGN_WINDOW_AFTER_SOURCE_SETTLE')
  if stage=='house' and nav>=len(house):
   err=(-math.pi/2-yaw+math.pi)%(2*math.pi)-math.pi
   if abs(err)>.18:pulse(['turnleft' if err>0 else 'turnright'],min(.65,abs(err)/2.25),row);time.sleep(.07);continue
   pulse(['a'],.2,row);fired+=1;stage='jump';record(row,status='ORIGINAL_JUMP_OUT_INPUT');time.sleep(1);continue
  if stage=='road' and nav>=len(road):
   stage='gate';record(row,status='ORIGINAL_EXIT_AEV_APPROACH')
  if stage=='gate':
   pulse(['a'],.2,row);fired+=1;time.sleep(2)
   if fired>=4:record(latest(),status='EXIT_INTERACTION_NOT_YET_TRANSITIONED');break
   continue
  points=house if stage=='house' else road;tx,tz=points[nav];dx=tx-px;dz=tz-pz;distance=math.hypot(dx,dz)
  if distance<(350 if stage=='house' else 850):nav+=1;stalls=0;last_position=None;record(row,status='WAYPOINT_REACHED');continue
  err=(math.atan2(dx,dz)-yaw+math.pi)%(2*math.pi)-math.pi
  if abs(err)>(.22 if stage=='house' else .3):pulse(['turnleft' if err>0 else 'turnright'],min(.65,abs(err)/2.25),row);time.sleep(.07);continue
  if last_position and math.hypot(px-last_position[0],pz-last_position[1])<100:stalls+=1
  else:stalls=0
  if stalls>=4:record(row,status='SOURCE_COLLISION_STALL_REQUIRES_ROUTE_REVIEW',target=[tx,tz]);break
  last_position=(px,pz)
  pulse(['fwd'] if stage=='house' else ['fwd','b'],min(.5 if stage=='house' else 1.1,distance/(1900 if stage=='house' else 3300)),row);time.sleep(.08)
except (EOFError,OSError) as exc:
 try:record(latest(),controller_stop=str(exc))
 except Exception:pass
finally:
 k.CloseHandle(h);logfile.close()