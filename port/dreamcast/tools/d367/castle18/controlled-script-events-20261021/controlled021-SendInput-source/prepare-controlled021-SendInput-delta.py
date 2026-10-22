from pathlib import Path
import json,hashlib
L=Path(__file__).parent;sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest();old=L/'observe-controlled-ch32-door020.py';assert sha(old)=='7edaf6ad057cd3291795b5260b52283091a0a6ed4fd808f46e7366978a4b2522';s=old.read_text().replace('door020','door021').replace('DOOR020','DOOR021').replace('allocated020','allocated021').replace('exact019state','exact020state').replace('actual019state','actual020state').replace('Exact019 fullstate','Exact020 fullstate').replace('>=3684','>=4761').replace('inherited019_placement','inherited020_placement').replace('669b920f06e89403a15d3796021878c39ee9807fe020487e6a8666220f635631','eba7a32afa7c59381ec7ce36918ea706feea187757e8fbb40a2fe5f2695ac008')
abi='''class KeyboardInput(C.Structure):
 _fields_=[('wVk',W.WORD),('wScan',W.WORD),('dwFlags',W.DWORD),('time',W.DWORD),('dwExtraInfo',C.c_size_t)]
class MouseInput(C.Structure):
 _fields_=[('dx',W.LONG),('dy',W.LONG),('mouseData',W.DWORD),('dwFlags',W.DWORD),('time',W.DWORD),('dwExtraInfo',C.c_size_t)]
class InputUnion(C.Union):
 _fields_=[('ki',KeyboardInput),('mi',MouseInput)]
class NativeInput(C.Structure):
 _anonymous_=('value',)
 _fields_=[('type',W.DWORD),('value',InputUnion)]
assert C.sizeof(KeyboardInput)==24 and C.sizeof(MouseInput)==32 and C.sizeof(NativeInput)==40 and NativeInput.value.offset==8
u.SendInput.argtypes=[W.UINT,C.POINTER(NativeInput),C.c_int];u.SendInput.restype=W.UINT
u.GetAsyncKeyState.argtypes=[C.c_int];u.GetAsyncKeyState.restype=W.SHORT
'''
s=s.replace('h=None;events=[];last=None;closed_sent=False',abi+'h=None;events=[];last=None;closed_sent=False')
a=s.index('def pulse_door(stage):');b=s.index('\ndef capture(row,label):',a)
new='''def async_x_state():
 value=int(u.GetAsyncKeyState(0x58))
 return dict(vk='0x58',signed_short=value,high_bit_down=bool(value&0x8000),scope='OS asynchronous key state; separate from nativeKey/SDLreceive')

def send_x_input(keyup):
 event=NativeInput();event.type=1;event.ki=KeyboardInput(0,0x2d,0x8|(0x2 if keyup else 0),0,0)
 C.set_last_error(0);count=int(u.SendInput(1,C.byref(event),C.sizeof(NativeInput)));error=C.get_last_error()
 proof=dict(keyup=keyup,requested=1,accepted_count=count,last_error=error,cbSize=C.sizeof(NativeInput),wVk=0,wScan='0x2d',flags=hex(event.ki.dwFlags),not_native_ack=True)
 events.append(dict(ordinary_scan_code_SendInput=proof,process_age=age()))
 return count==1

def pulse_door(stage):
 check();row=sample();result=dict(pressed=False,acknowledged=False,stage=stage,delivery='experimental SendInput scan-code; no causalfix claim')
 if not memory_ready or age()>=31.5 or not door_ready(row,stage):return result
 wins=[]
 @CALL
 def cb(w,_):
  p=W.DWORD();u.GetWindowThreadProcessId(w,C.byref(p));c=C.create_unicode_buffer(256);u.GetClassNameW(w,c,256)
  if p.value==owner['pid']and c.value=='SDL_app':wins.append(int(w))
  return True
 assert u.EnumWindows(cb,0)and len(wins)==1;hwnd=wins[0];pressed=False;ack=[];os_states=[]
 if not ensure_owned_focus(hwnd):return result
 try:
  check();assert memory_ready and age()<32;row=sample();focus=window_evidence(hwnd);baseline=async_x_state();os_states.append(baseline)
  if not door_ready(row,stage)or not verified_owned_focus(focus):return result
  if baseline['high_bit_down']:
   events.append(dict(preexisting_X_down=baseline,no_input_or_keyup=True,stage=stage));return result
  events.append(dict(immediate_native_door_A_recheck=row,stage=stage,owned_window_evidence=focus,OS_async_X_before=baseline))
  # Only the verified guest foreground receives this global ordinary-key experiment.
  # A source action and the current key state are rechecked immediately, no capture intervenes.
  check();focus=window_evidence(hwnd)
  if not verified_owned_focus(focus):return result
  baseline=async_x_state();os_states.append(baseline)
  if baseline['high_bit_down']:
   events.append(dict(preexisting_X_down=baseline,no_input_or_keyup=True,stage=stage));return result
  pressed=send_x_input(False);result['pressed']=pressed
  if not pressed:return result
  until=time.monotonic()+.75
  while time.monotonic()<until:
   check();assert age()<40.5;focus=window_evidence(hwnd)
   if not verified_owned_focus(focus):events.append(dict(owned_focus_lost_during_hold=focus,release_own_key=True));break
   os_states.append(async_x_state());proof=native_input_ack(row,stage);ack.append(proof)
   if proof['acknowledged']:result['acknowledged']=True;break
   time.sleep(.003)
 finally:
  # Release our accepted injection even on lostfocus/process exit/read error.
  # No keyup at all if user X was already down or keydown was not accepted.
  if pressed:
   released=send_x_input(True);events.append(dict(ordinary_own_X_finally_release=bool(released),stage=stage));assert released,'Own injected X keyup was not accepted'
 if pressed:events.append(dict(ordinary_owned_UI_pulse=('native204-Door4-A'if stage==1 else'native209-physicalDoor1-A'),stage=stage,maximum_hold_seconds=.75,one_keydown_only=True,result=result,ack_observations=ack,OS_async_X_observations=os_states,OS_async_X_after_release=async_x_state(),owned_window_after_release=window_evidence(hwnd),process_age=age()))
 return result
'''
s=s[:a]+new+s[b:];s=s.replace("allocation['allow_owned_window_focus']is True", "allocation['allow_owned_window_focus']is True and allocation['allow_scan_code_SendInput']is True");s=s.replace('acknowledgedowned-windowA','experimentalSendInputA');(L/'observe-controlled-ch32-door021.py').write_text(s,encoding='utf-8')
p=L/'run-controlled-ch32-door020.py';s=p.read_text().replace('door020','door021').replace('DOOR020','DOOR021').replace('allocated020','allocated021').replace('controlled020-','controlled021-').replace('exact019state','exact020state').replace('Exact019','Exact020').replace('actual019','actual020').replace('Inheritedactual019','Inheritedactual020').replace("seed=D/'route-walk-controlled-ch32-door019/data'","seed=D/'route-walk-controlled-ch32-door020/data'")
s=s.replace("allocation['allow_owned_window_focus']is True", "allocation['allow_owned_window_focus']is True and allocation['allow_scan_code_SendInput']is True")
s=s.replace("for name,digest in protected.items():assert sha(D/name)==digest", "protected['route-walk-controlled-ch32-door020/data/disc.state']='eba7a32afa7c59381ec7ce36918ea706feea187757e8fbb40a2fe5f2695ac008'\nprotected['route-walk-controlled-ch32-door020/data/T0000_vmu_save_A1.bin']='425595f75b099a23789e09bbbd8fa4a3661072539644eae6051aa884943400b0'\nfor name,digest in protected.items():assert sha(D/name)==digest",1)
s=s.replace('acknowledgedoneowned-windowA','experimental scan-code SendInputA with nativeack');(L/'run-controlled-ch32-door021.py').write_text(s,encoding='utf-8')
(L/'run-controlled-ch32-door021.sh').write_bytes((L/'run-controlled-ch32-door020.sh').read_bytes().replace(b'020',b'021').replace(b'\r\n',b'\n'))
c=json.loads((L/'controlled020-OWNED-INPUT-CONTRACT.json').read_text());c['scope']='SOURCEONLY021 fromactual020/source4761; experimentalordinaryscan-codeSendInput, notcausalfix. No guest/allocation.';c['seed_sha256']='eba7a32afa7c59381ec7ce36918ea706feea187757e8fbb40a2fe5f2695ac008';c['minimum_frame']=4761;c['inherited_position']='Actual020alreadyatDoor4/go1done/max2/count2; nofirstgoto/replay.';c['input_contract']='ONEacceptedscan-codeXdownperstage; exactownedforeground/GUIactive/focus and nativeDoorready plus OSasyncXnotheld beforedown. SendInput count/error independent from OSasyncX and coherentnative64Key/doorrequest. Hold<=.75s orack/focusloss; finallyonekeyup foracceptedowndown evenlostfocus/deadguest/readerror. No keyupwhenpreheldX/downcount0. No retries. ExclusiveGUIlease mandatory.';c['Windows_SendInput']=dict(INPUT_size=40,union_offset=8,KEYBDINPUT_size=24,MOUSEINPUT_size=32,word_bits=16,DWORD_bits=32,extraInfo_type='c_size_t/ULONG_PTR',scan='0x2d',wVk=0,down_flags='0x8',up_flags='0xa',count=1,GetAsyncKeyState_return='signedSHORT/high0x8000',extraInfo_offset=16);c['source_qualification']='Onlychanged SendInput helper/physical-X guard/finally/mock cases; no26/broad reruns.';c['exclusive_gui_input']=c['exclusive_gui_input'].replace('020','021');(L/'controlled021-OWNED-INPUT-CONTRACT.json').write_text(json.dumps(c,indent=2)+'\n')
j=json.loads((L/'controlled-ch32-door020-pins.json').read_text());out={}
for name,v in j.items():
 p=Path(name)
 if p.name in ['observe-controlled-ch32-door020.py','controlled020-OWNED-INPUT-CONTRACT.json']:p=L/p.name.replace('020','021')
 if 'route-walk-controlled-ch32-door019/data' in str(p).replace('\\','/'):p=Path(str(p).replace('door019','door020'))
 out[str(p)]=sha(p)
(L/'controlled-ch32-door021-pins.json').write_text(json.dumps(out,indent=2)+'\n')
print('observer',sha(L/'observe-controlled-ch32-door021.py'),'wrapper',sha(L/'run-controlled-ch32-door021.py'),'pins',sha(L/'controlled-ch32-door021-pins.json'))
