from pathlib import Path
import json,hashlib
L=Path(__file__).parent;R=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21');D=R/'recovered-j-content-20261021';sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest();s=(L/'observe-controlled-ch32-door019.py').read_text().replace('door019','door020').replace('DOOR019','DOOR020').replace('allocated019','allocated020').replace('CONTROLLED exact018state: existing Goto slots/current-entry admission only; native204Door4 to209, physicalDoor1 then original leader cut.','CONTROLLED exact019state alreadyatnative204Door4: acknowledgedowned-windowA to209, remainingcurrententryGoto thenphysicalDoor1/originalleadercut.').replace('Exact018 fullstate','Exact019 fullstate').replace('CONTROLLED actual018state;','CONTROLLED actual019state;').replace("state_sha256='4d7178b9d7420156b39328396cae08661f92c297f4ed28794b145a3cfe03ecdc'","state_sha256='669b920f06e89403a15d3796021878c39ee9807fe020487e6a8666220f635631'").replace('>=2604','>=3684')
insert=s.index('h=None;events=');api='''class GuiThreadInfo(C.Structure):
 _fields_=[('cbSize',W.DWORD),('flags',W.DWORD),('hwndActive',W.HWND),('hwndFocus',W.HWND),('hwndCapture',W.HWND),('hwndMenuOwner',W.HWND),('hwndMoveSize',W.HWND),('hwndCaret',W.HWND),('rcCaret',W.RECT)]
assert C.sizeof(GuiThreadInfo)==72
u.GetForegroundWindow.argtypes=[];u.GetForegroundWindow.restype=W.HWND
u.GetGUIThreadInfo.argtypes=[W.DWORD,C.POINTER(GuiThreadInfo)];u.GetGUIThreadInfo.restype=W.BOOL
u.SetForegroundWindow.argtypes=[W.HWND];u.SetForegroundWindow.restype=W.BOOL
u.IsWindowVisible.argtypes=[W.HWND];u.IsWindowVisible.restype=W.BOOL
u.IsIconic.argtypes=[W.HWND];u.IsIconic.restype=W.BOOL
u.IsChild.argtypes=[W.HWND,W.HWND];u.IsChild.restype=W.BOOL
u.GetWindowThreadProcessId.restype=W.DWORD
''';s=s[:insert]+api+s[insert:]
s=s.replace("WRITE_ALLOWLIST=[{'address':hex(STAGES[1]['address']),'bytes':24},{'address':hex(STAGES[2]['address']),'bytes':24}","WRITE_ALLOWLIST=[{'address':hex(STAGES[2]['address']),'bytes':24}")
s=s.replace("def exact_command_write(address,data,stage):\n c=STAGES[stage]","def exact_command_write(address,data,stage):\n assert stage==2,'Inheritedfirstplacementmustnotbereplayed'\n c=STAGES[stage]")
s=s.replace('def publish_existing_goto(stage):\n check();row=sample();c=STAGES[stage]','def publish_existing_goto(stage):\n assert stage==2\n check();row=sample();c=STAGES[stage]')
a=s.index('def pulse_door(stage):');b=s.index('def capture(',a)
s=s[:a]+'''def window_evidence(hwnd):
 check();p=W.DWORD();thread=int(u.GetWindowThreadProcessId(hwnd,C.byref(p)));assert p.value==owner['pid']and thread
 fg=int(u.GetForegroundWindow()or 0);fp=W.DWORD()
 if fg:u.GetWindowThreadProcessId(fg,C.byref(fp))
 q=GuiThreadInfo();q.cbSize=C.sizeof(q);C.set_last_error(0);ok=bool(u.GetGUIThreadInfo(thread,C.byref(q)));error=C.get_last_error();focus=int(q.hwndFocus or 0);kp=W.DWORD()
 if focus:u.GetWindowThreadProcessId(focus,C.byref(kp))
 return dict(hwnd=int(hwnd),owner_pid=p.value,thread_id=thread,foreground_hwnd=fg,foreground_pid=fp.value,gui_query_ok=ok,gui_query_error=error,active_hwnd=int(q.hwndActive or 0),focus_hwnd=focus,focus_pid=kp.value,focus_is_owned_child=bool(focus and u.IsChild(hwnd,focus)),gui_flags=q.flags,visible=bool(u.IsWindowVisible(hwnd)),iconic=bool(u.IsIconic(hwnd)),process_age=age())

def verified_owned_focus(e):
 return bool(e.get('gui_query_ok')and e.get('owner_pid')==owner['pid']and e.get('foreground_hwnd')==e.get('hwnd')and e.get('active_hwnd')==e.get('hwnd')and e.get('focus_pid')==owner['pid']and(e.get('focus_hwnd')==e.get('hwnd')or e.get('focus_is_owned_child')))

def ensure_owned_focus(hwnd):
 before=window_evidence(hwnd);events.append(dict(owned_window_before_focus=before))
 if verified_owned_focus(before):return True
 # One reversible focus request targets only this exact guest-owned SDL window.
 # No foreign window receives an input/focus request; guest closure returns control to Windows.
 check();accepted=bool(u.SetForegroundWindow(hwnd));until=time.monotonic()+.35;after=before
 while time.monotonic()<until and age()<32:
  check();after=window_evidence(hwnd)
  if verified_owned_focus(after):events.append(dict(owned_window_focus_verified=after,SetForegroundWindow_returned=accepted));return True
  time.sleep(.01)
 events.append(dict(owned_window_focus_unverified=after,SetForegroundWindow_returned=accepted,no_input=True));return False

def native_input_ack(row,stage):
 check();pg=u32(0x8c2e91dc);assert pg==row['pg'];f=u32(pg+0x51e4);old,on,trg=struct.unpack('<3Q',read(0x8c3a948c+8,24));phase=list(read(pg+0x20,2));nextroom=struct.unpack('<H',read(pg+0x28,2))[0];stable=f==u32(pg+0x51e4)
 keys=stable and bool((on|trg)&0x80080000==0x80080000);effect=stable and stage==1 and phase[0]==4 and nextroom==0x209
 return dict(frame=f,coherent=stable,Key_old=hex(old),Key_on=hex(on),Key_trg=hex(trg),phase=phase,next_room=hex(nextroom),native_key_ack=keys,original_door_request_ack=effect,acknowledged=keys or effect)

def pulse_door(stage):
 check();row=sample();result=dict(pressed=False,acknowledged=False,stage=stage)
 if not memory_ready or age()>=31.5 or not door_ready(row,stage):return result
 wins=[]
 @CALL
 def cb(w,_):
  p=W.DWORD();u.GetWindowThreadProcessId(w,C.byref(p));c=C.create_unicode_buffer(256);u.GetClassNameW(w,c,256)
  if p.value==owner['pid']and c.value=='SDL_app':wins.append(int(w))
  return True
 assert u.EnumWindows(cb,0)and len(wins)==1;hwnd=wins[0];pressed=False;ack=[];vk=ord('X');scan=0x2d
 if not ensure_owned_focus(hwnd):return result
 try:
  check();assert memory_ready and age()<32;row=sample();focus=window_evidence(hwnd)
  if not door_ready(row,stage)or not verified_owned_focus(focus):return result
  events.append(dict(immediate_native_door_A_recheck=row,stage=stage,owned_window_evidence=focus));assert u.PostMessageW(hwnd,0x100,vk,1|(scan<<16));pressed=True;result['pressed']=True;until=time.monotonic()+.75
  while time.monotonic()<until:
   check();assert age()<40.5;proof=native_input_ack(row,stage);ack.append(proof)
   if proof['acknowledged']:result['acknowledged']=True;break
   time.sleep(.003)
 finally:
  if pressed and k.WaitForSingleObject(h,0)==258:
   check();p=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(p));assert p.value==owner['pid'];assert u.PostMessageW(hwnd,0x101,vk,1|(scan<<16)|0xc0000000)
 if pressed:events.append(dict(ordinary_owned_UI_pulse=('native204-Door4-A'if stage==1 else'native209-physicalDoor1-A'),stage=stage,maximum_hold_seconds=.75,one_keydown_only=True,result=result,ack_observations=ack,owned_window_after_release=window_evidence(hwnd),process_age=age()))
 return result
'''+s[b:]
s=s.replace('published={1:False,2:False};sent={1:False,2:False};placed={1:False,2:False};','published={1:True,2:False};sent={1:False,2:False};attempted={1:False,2:False};placed={1:True,2:False};')
s=s.replace('inherited017_firstcut_return=True,','inherited017_firstcut_return=True,inherited019_placement_already_consumed=True,').replace('controlled_setup_maximum_successful_bytes=58','controlled_setup_maximum_successful_bytes=29')
s=s.replace('placed[stage]and not sent[stage]and age()<32','placed[stage]and not attempted[stage]and age()<31.5')
s=s.replace('try:sent[stage]=pulse_door(stage)',"attempted[stage]=True\n      try:\n       pulse_result=pulse_door(stage);sent[stage]=pulse_result['pressed'];events.append(dict(single_action_attempt=pulse_result,no_automatic_retry=True))")
compile(s,'observer020','exec');(L/'observe-controlled-ch32-door020.py').write_text(s)
w=(L/'run-controlled-ch32-door019.py').read_text().replace('door019','door020').replace('DOOR019','DOOR020').replace('allocated019','allocated020').replace('exact018state','exact019state').replace("seed=D/'route-walk-controlled-ch32-door018/data'","seed=D/'route-walk-controlled-ch32-door019/data'").replace('actual018 fullstate','actual019 fullstate').replace('Controlled018 closed','Controlled020 closed');idx=w.index('for name,digest in protected.items():assert sha(D/name)==digest\ncompile');w=w[:idx]+"protected['route-walk-controlled-ch32-door019/data/disc.state']='669b920f06e89403a15d3796021878c39ee9807fe020487e6a8666220f635631'\nprotected['route-walk-controlled-ch32-door019/data/T0000_vmu_save_A1.bin']='425595f75b099a23789e09bbbd8fa4a3661072539644eae6051aa884943400b0'\n"+w[idx:];w=w.replace("[{'address':'0x8c47ff48','bytes':24},{'address':'0x8c47ff60','bytes':24}","[{'address':'0x8c47ff60','bytes':24}")
w=w.replace('Publish only existing Goto slot1/currententry2 for native204Door4; afteractual209 freeplay only publish slot2/currententry3 combined physicalDoor1/AEV0A. Maximum58B config setup, countlast perstage; twoordinaryA max.','Inheritedactual019alreadyatDoor4; acknowledgedoneowned-windowA, no firstgoto. ONLYafteractual209freeplay publishslot2/currententry3 combinedphysicalDoor1/AEV0A,29Bcountlast. PhysicaldoorA uses sameackmethod; maxonekeydownperstage.').replace('Existing Goto','Existing Goto')
compile(w,'wrapper020','exec');(L/'run-controlled-ch32-door020.py').write_text(w);(L/'run-controlled-ch32-door020.sh').write_bytes((L/'run-controlled-ch32-door019.sh').read_bytes().replace(b'019',b'020'))
pins=json.loads((L/'controlled-ch32-door019-pins.json').read_text());pins.pop(str(L/'observe-controlled-ch32-door019.py'))
for p in [L/'observe-controlled-ch32-door020.py',D/'route-walk-controlled-ch32-door019/data/disc.state',D/'route-walk-controlled-ch32-door019/data/T0000_vmu_save_A1.bin']:pins[str(p)]=sha(p)
(L/'controlled-ch32-door020-pins.json').write_text(json.dumps(pins,indent=2)+'\n');print('observer',sha(L/'observe-controlled-ch32-door020.py'),'wrapper',sha(L/'run-controlled-ch32-door020.py'),'pins',sha(L/'controlled-ch32-door020-pins.json'))