from pathlib import Path
import ast,ctypes as C,ctypes.wintypes as W,types,json,hashlib
L=Path(__file__).parent;P=L/'observe-controlled-ch32-door021.py';T=ast.parse(P.read_text());env=dict(C=C,W=W,owner=dict(pid=100),events=[])
for name in ['KeyboardInput','MouseInput','InputUnion','NativeInput','async_x_state','send_x_input','pulse_door']:
 n=next(n for n in T.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))and n.name==name);exec(compile(ast.Module(body=[n],type_ignores=[]),'actual021changedhelper','exec'),env)
checks=[]
def ck(name,ok):assert ok,name;checks.append(name)
ck('nativeWin64KEYBDINPUT24',C.sizeof(env['KeyboardInput'])==24 and env['KeyboardInput'].dwExtraInfo.offset==16)
ck('nativeWin64INPUT40union8',C.sizeof(env['MouseInput'])==32 and C.sizeof(env['InputUnion'])==32 and C.sizeof(env['NativeInput'])==40 and env['NativeInput'].value.offset==8)
base=dict(owned=True);row=dict(pg=1)
for case in ['nativeack','timeout','preheld','lowbitonly','focusdenied','focuslostpredown','focuslostduringhold','downrejected','ackreaderror','uprejected','guestexitedafterdown']:
 now=[1.];api=[];focuscalls=[0];ackcalls=[0];down=[False];released=[False];events=[]
 class UI:
  def EnumWindows(self,cb,_):cb(50,0);return True
  def GetWindowThreadProcessId(self,hwnd,p):p._obj.value=100;return 5
  def GetClassNameW(self,hwnd,b,n):b.value='SDL_app';return 7
  def GetAsyncKeyState(self,vk):
   assert vk==0x58
   return -32768 if case=='preheld'or(down[0]and not released[0])else(1 if case=='lowbitonly'else 0)
  def SendInput(self,count,p,size):
   event=p._obj;assert count==1 and size==40 and event.type==1 and event.ki.wVk==0 and event.ki.wScan==0x2d and event.ki.time==0 and event.ki.dwExtraInfo==0
   up=bool(event.ki.dwFlags&2);api.append(event.ki.dwFlags)
   if not up:down[0]=case!='downrejected'
   else:released[0]=case!='uprejected'
   return 0 if(case=='downrejected'and not up)or(case=='uprejected'and up)else 1
 def focus(h):
  focuscalls[0]+=1
  return dict(owned=not(case=='focuslostpredown'and focuscalls[0]>=2)and not(case=='focuslostduringhold'and focuscalls[0]>=3))
 def ack(r,s):
  ackcalls[0]+=1
  if case=='ackreaderror':raise RuntimeError('mock-read-failure')
  if case=='guestexitedafterdown':raise RuntimeError('mock-retained-handle-exited')
  return dict(acknowledged=case in['nativeack','lowbitonly']and ackcalls[0]>=3)
 env.update(u=UI(),CALL=lambda f:f,events=events,check=lambda:None,sample=lambda:row,door_ready=lambda r,s:True,memory_ready=True,age=lambda:now[0],ensure_owned_focus=lambda h:case!='focusdenied',window_evidence=focus,verified_owned_focus=lambda e:e['owned'],native_input_ack=ack,time=types.SimpleNamespace(monotonic=lambda:now[0],sleep=lambda d:now.__setitem__(0,now[0]+d)))
 failed=False
 try:result=env['pulse_door'](1)
 except (RuntimeError,AssertionError):failed=True;result=None
 if case in['preheld','focusdenied','focuslostpredown']:ck(case+'-no-down-or-up',api==[]and not failed and not result['pressed'])
 elif case=='downrejected':ck('rejected-down-no-owned-keyup',api==[8]and not failed and not result['pressed'])
 else:
  ck(case+'-exactly-one-down-up',api==[8,10])
  if case in['ackreaderror','guestexitedafterdown','uprejected']:ck(case+'-failure-not-suppressed',failed)
  else:ck(case+'-result',not failed and result['pressed']and result['acknowledged']==(case in['nativeack','lowbitonly']))
  if case=='timeout':ck('maxhold750ms',1.75<=now[0]<1.76)
  if case=='focuslostduringhold':ck('lostfocus-stops-hold-releases',now[0]<1.01 and released[0])
  if case in['nativeack','timeout','lowbitonly']:ck(case+'-api-os-native-records-separate',len([e for e in events if 'ordinary_scan_code_SendInput'in e])==2 and any('ordinary_owned_UI_pulse'in e and 'OS_async_X_observations'in e and 'ack_observations'in e for e in events))
old=ast.parse((L/'observe-controlled-ch32-door020.py').read_text());core=['check','read','sample','door_ready','native_input_ack','window_evidence','verified_owned_focus','ensure_owned_focus','exact_command_write','publish_current_entry_goto']
# Only names actually present in the frozen source are used, no import/execute of runtime module.
core=[n for n in core if any(isinstance(v,ast.FunctionDef)and v.name==n for v in old.body)]
for name in core:
 a=next(n for n in old.body if isinstance(n,ast.FunctionDef)and n.name==name);b=next(n for n in T.body if isinstance(n,ast.FunctionDef)and n.name==name);ck('unchanged-inherited-'+name,ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False))
receipt=dict(scope='ONLY extracted changed021 SendInput ABI/onepulse/preheld/focusloss/countfailure/finally source mocks; no actualOS input/child/guest. No26/broad rerun.',observer_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),passed=len(checks),checks=checks);(L/'controlled021-SendInput-source-cases.json').write_text(json.dumps(receipt,indent=2)+'\n');print('PASS',len(checks),receipt['observer_sha256'])
