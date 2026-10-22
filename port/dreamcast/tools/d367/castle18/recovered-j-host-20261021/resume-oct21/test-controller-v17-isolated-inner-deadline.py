from pathlib import Path
import ast,ctypes as C,ctypes.wintypes as W,json,hashlib
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');p=L/'owned-window-recovered-j-r201-South-escape-bell-quiet-combat-v17-still.py';tree=ast.parse(p.read_text());node=next(n for n in ast.walk(tree)if isinstance(n,ast.FunctionDef)and n.name=='check');cap=L/'synthetic-no-real-guest';owner=dict(start_filetime=123);messages=[]
class K:
 def QueryFullProcessImageNameW(self,h,z,b,n):b.value=str(cap/'flycast.exe');return 1
 def GetProcessTimes(self,h,a,b,c,d):a._obj.dwLowDateTime=123;a._obj.dwHighDateTime=0;return 1
class U:
 def IsWindow(self,w):return True
 def PostMessageW(self,*a):messages.append(a);return 1
active={'left','ready'};env=dict(C=C,W=W,k=K(),u=U(),h=123,hwnd=456,owner=owner,cap=cap,Path=Path,active=active,process_age=lambda:40.6,mapkeys={'left':(74,36),'ready':(86,47)},events=[])
exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual controller check() extracted>','exec'),env)
try:env['check']();raise AssertionError('Expected inner timeout')
except TimeoutError:pass
assert not active and len(messages)==2 and all(m[1]==0x101 for m in messages)
env['check']() # Identity verification remains usable after deadline once all keys are released.
out=L/'controller-v17-isolated-inner-deadline-test.json';assert not out.exists();out.write_text(json.dumps(dict(scope='Extracted actual check() with synthetic API handles/PID; no real process/window/input. Active left+ready release at40.6s, TimeoutError raised, then identitycheck still works for cleanup.',controller_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),keyups=messages,events=env['events'],passed=True),indent=2)+'\n');print(out)
