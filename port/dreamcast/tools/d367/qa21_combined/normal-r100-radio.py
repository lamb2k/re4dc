"""Original r100 first kill, natural s20 and radio using read-only state + PID posts."""
from pathlib import Path
import ctypes,json,math,sys,time
cap=Path(sys.argv[1]);deps=Path(sys.argv[2]);seed=Path(sys.argv[3]) if len(sys.argv)>3 and sys.argv[3] else None
sys.path.insert(0,str(deps));import checkpoint_runner18 as pad
pad.KEYS.update(rtrig=(0x2f,0),turnleft=(0x24,0),turnright=(0x26,0));pad.VK.update(rtrig=0x56,turnleft=0x4a,turnright=0x4c)
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
stage='first_fight';target_ptr=None;fired=0;seen={};last_frame=None
if seed and (seed/'normal-combat-progress.json').exists():
 prior=json.loads((seed/'normal-combat-progress.json').read_text());stage=prior['stage'];target_ptr=prior['target_ptr'];fired=prior['fired']
logfile=(cap/'normal-combat-controller.jsonl').open('x')
def latest():
 rows=(cap/'read-only-state.jsonl').read_text().splitlines();return json.loads(rows[-1])
def record(row,**extra):
 item={'stage':stage,'host_s':time.monotonic(),'state':row,**extra};logfile.write(json.dumps(item)+'\n');logfile.flush()
 (cap/'normal-combat-progress.json').write_text(json.dumps({'stage':stage,'target_ptr':target_ptr,'fired':fired,'last_sample':row},indent=2)+'\n')
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

deadline=time.monotonic()+42
try:
 while time.monotonic()<deadline:
  try: row=latest()
  except (FileNotFoundError,IndexError,json.JSONDecodeError):time.sleep(.05);continue
  live();g=row.get('global',{});text=(cap/'run-output.txt').read_text(errors='replace')
  if 'route movie start: id=10020' in text and stage=='first_fight':stage='s20';record(row,status='ORIGINAL_FIRST_KILL_S20_STARTED')
  if 'route movie terminal=1 id=10020 frames=571/571' in text and stage in ('first_fight','s20'):stage='radio_wait';record(row,status='ORIGINAL_S20_NATURAL_EOF')
  if stage=='radio_wait':
   if 'SS/eng/ss_term.dat' in text and row.get('ssloop') and g.get('stop',0):
    seen.setdefault('radio',time.monotonic())
    if time.monotonic()-seen['radio']>=6:pulse(['start'],.15,row);stage='radio_return';time.sleep(.4)
   time.sleep(.05);continue
  if stage=='radio_return':
   if g.get('rno',[])[:2]==[3,0] and g.get('stop')==0 and row.get('ssloop')==0:stage='finished';record(row,status='ORIGINAL_RADIO_RETURN');break
   time.sleep(.05);continue
  if stage!='first_fight':time.sleep(.05);continue
  if g.get('player_life',0)<=0:record(row,status='AUTHENTIC_DEATH_NO_ROLLBACK');break
  if g.get('rno',[])[:2]!=[3,0] or g.get('stop')!=0 or row.get('ssloop'):time.sleep(.05);continue
  if g.get('frame')==last_frame:time.sleep(.05);continue
  last_frame=g['frame'];px,py,pz=row['player']['pos'];yaw=row['player']['ang'][1]
  actors=[a for a in row.get('actors',[]) if a['id']==0x12 and a['hp']>0 and a['alive']&4]
  if not actors:time.sleep(.1);continue
  target=min(actors,key=lambda a:(a['pos'][0]-px)**2+(a['pos'][2]-pz)**2)
  if target_ptr is None:target_ptr=target['ptr']
  dx=target['pos'][0]-px;dz=target['pos'][2]-pz
  if math.hypot(dx,dz)>6500:time.sleep(.1);continue
  err=(math.atan2(dx,dz)-yaw+math.pi)%(2*math.pi)-math.pi
  if abs(err)>.14:pulse(['turnleft' if err>0 else 'turnright'],min(.65,abs(err)/2.25),row);time.sleep(.07);continue
  pulse(['shoot'],.15,row);fired+=1;time.sleep(.35)
  if fired%5==0:pulse(['reload'],.15,row);time.sleep(1)
except (EOFError,OSError) as exc:
 try:record(latest(),controller_stop=str(exc))
 except Exception:pass
finally:
 k.CloseHandle(h);logfile.close()