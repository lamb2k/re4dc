from pathlib import Path
import ast,ctypes as C,ctypes.wintypes as W,types,json,hashlib,struct,copy
L=Path(__file__).parent;P=L/'observe-controlled-ch32-door020.py';tree=ast.parse(P.read_text());env=dict(C=C,W=W,struct=struct,owner=dict(pid=100),events=[])
for name in ['GuiThreadInfo','verified_owned_focus','ensure_owned_focus','native_input_ack','pulse_door','exact_command_write']:
 node=next(n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))and n.name==name);exec(compile(ast.Module(body=[node],type_ignores=[]),'actual020delta','exec'),env)
checks=[]
def ck(n,v):assert v,n;checks.append(n)
ck('native64-GUIThreadInfo72',C.sizeof(env['GuiThreadInfo'])==72 and env['GuiThreadInfo'].hwndActive.offset==8 and env['GuiThreadInfo'].hwndFocus.offset==16)
base=dict(gui_query_ok=True,owner_pid=100,hwnd=50,foreground_hwnd=50,active_hwnd=50,focus_pid=100,focus_hwnd=50,focus_is_owned_child=False)
ck('actualownedfocusready',env['verified_owned_focus'](base))
for k,v in [('gui_query_ok',False),('foreground_hwnd',51),('active_hwnd',51),('focus_pid',101),('focus_hwnd',51),('owner_pid',101)]:
 q=base.copy();q[k]=v;ck('reject-focus-'+k,not env['verified_owned_focus'](q))
for case in ['alreadyowned','ownedrequestworks','denied']:
 now=[1.];calls=[];evidence=[dict(base,foreground_hwnd=51)if case!='alreadyowned'else base]
 def focus(h):calls.append(h);evidence[0]=base if case=='ownedrequestworks'else evidence[0];return case=='ownedrequestworks'
 env.update(check=lambda:None,window_evidence=lambda h:evidence[0],time=types.SimpleNamespace(monotonic=lambda:now[0],sleep=lambda d:now.__setitem__(0,now[0]+d)),age=lambda:now[0],u=types.SimpleNamespace(SetForegroundWindow=focus),events=[])
 got=env['ensure_owned_focus'](50);ck('focus-'+case,got==(case!='denied')and calls==([]if case=='alreadyowned'else[50])and now[0]<1.37)
# Actual native acknowledgement reader: full64bitKey, stablepGframe, sourceeventack as separate path.
pg=0x8c400000;mode=['keys'];reads=[]
def u32(a):return pg if a==0x8c2e91dc else 100

def read(a,n):
 reads.append((a,n))
 if a==0x8c3a948c+8:return struct.pack('<3Q',0,0x80080480 if mode[0]=='keys'else(0x80080000<<32 if mode[0]=='upperonly'else 0),0)
 if a==pg+0x20:return bytes([4 if mode[0]=='effect'else 3,0])
 if a==pg+0x28:return struct.pack('<H',0x209)
 raise AssertionError((a,n))
env.update(check=lambda:None,u32=u32,read=read)
for case in ['keys','upperonly','effect','none']:
 mode[0]=case;q=env['native_input_ack'](dict(pg=pg),1);ck('nativeack-'+case,q['acknowledged']==(case in['keys','effect']))
ck('nativeKey24Bcorrectbase',reads[0]==(0x8c3a9494,24))
# Actual pulse function isolated: fakeEnumWindows/PostMessage/clock and sourceacks; no WinDLL/OpenProcess/OS/UI.
row=dict(pg=pg);owner=env['owner'];posts=[]
class FakeUI:
 def EnumWindows(self,cb,_):cb(50,0);return True
 def GetWindowThreadProcessId(self,hwnd,p):p._obj.value=owner['pid'];return 123
 def GetClassNameW(self,hwnd,b,n):b.value='SDL_app';return 7
 def PostMessageW(self,hwnd,msg,vk,lp):posts.append((hwnd,msg,vk,lp));return True
for case in ['nativeack','timeout','focusdenied','ackreaderror']:
 now=[1.];posts.clear();observations=[0];env.update(events=[],u=FakeUI(),CALL=lambda f:f,k=types.SimpleNamespace(WaitForSingleObject=lambda h,t:258),h=1,memory_ready=True,sample=lambda:row,door_ready=lambda r,s:True,ensure_owned_focus=lambda h:case!='focusdenied',window_evidence=lambda h:base,age=lambda:now[0],check=lambda:None,time=types.SimpleNamespace(monotonic=lambda:now[0],sleep=lambda d:now.__setitem__(0,now[0]+d)))
 def ack(r,s):
  observations[0]+=1
  if case=='ackreaderror':raise RuntimeError('mock-readerror')
  return dict(acknowledged=case=='nativeack'and observations[0]>=3)
 env['native_input_ack']=ack
 try:q=env['pulse_door'](1);failed=False
 except RuntimeError:failed=True;q=None
 if case=='focusdenied':ck('focusdenied-noinput',posts==[]and q['pressed']is False)
 else:
  ck(case+'-oneDown-oneUp-finally',[m[1]for m in posts]==[0x100,0x101]and all(m[0]==50 for m in posts))
  if case=='nativeack':ck('nativeack-releasesafterack',q['acknowledged']and now[0]<1.02)
  if case=='timeout':ck('timeout-noack-boundedrelease',q['pressed']and not q['acknowledged']and 1.75<=now[0]<1.76)
  if case=='ackreaderror':ck('readerror-propagatesafterownedkeyup',failed)
# Stage1 cannot publish; main marks each attempt before calling pulse, no implicit retry afterfalse result.
try:env['exact_command_write'](0,b'',1);ok=False
except AssertionError:ok=True
ck('no-firstplacementwrite',ok)
source=P.read_text();ck('attemptflag-beforecall',"attempted[stage]=True\n      try:\n       pulse_result=pulse_door(stage)"in source and'not attempted[stage]'in source)
ck('exactremaining29allowlist',"WRITE_ALLOWLIST=[{'address':hex(STAGES[2]['address']),'bytes':24}"in source and'controlled_setup_maximum_successful_bytes=29'in source)
r=dict(scope='Narrow actual020 extracted focus/ack/pulse/release/no-retry/no-firstwrite tests only; mockAPI/clock, no OSchild/guest/input. No44/17/31rerun.',observer_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),passed=len(checks),checks=checks);(L/'controlled020-owned-input-source-cases.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS',len(checks),r['observer_sha256'])