from pathlib import Path
import ctypes as C,json,time,runpy,sys,shutil,hashlib
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');target=L/'guard-resume-41inner-47absolute-resources-v2.py';out=L/'guard-v2-mocked-fault-tests.json';assert not out.exists();orig=C.WinDLL;origdisk=shutil.disk_usage;rows=[]
class Fn:
 def __init__(self,f):self.f=f
 def __call__(self,*a):return self.f(*a)
class Lib:pass
for case,age in [('disk_query_failure',5),('missing_SDL_window',46),('WM_CLOSE_failure',46),('ordinary_close',46),('absolute_stop',47.2)]:
 cap=D/('route-walk-resource-guard-faulttest-'+case);assert not cap.exists();cap.mkdir();owner=dict(pid=0,path=str(cap/'flycast.exe'),start_filetime=int((time.time()-age+11644473600)*1e7));(cap/'owned-process.json').write_text(json.dumps(owner));state=dict(alive=True,terminates=0,closes=0,handlecloses=0)
 k=Lib();u=Lib()
 def times(h,a,b,c,d):
  a._obj.dwLowDateTime=owner['start_filetime']&0xffffffff;a._obj.dwHighDateTime=owner['start_filetime']>>32;return 1
 def query(h,z,b,n):b.value=owner['path'];return 1
 def terminate(h,code):state['terminates']+=1;state['alive']=False;return 1
 def close(h):state['handlecloses']+=1;return 1
 k.OpenProcess=Fn(lambda *a:123);k.GetProcessTimes=Fn(times);k.QueryFullProcessImageNameW=Fn(query);k.WaitForSingleObject=Fn(lambda *a:258 if state['alive']else 0);k.TerminateProcess=Fn(terminate);k.CloseHandle=Fn(close)
 def enum(cb,x):
  if case!='missing_SDL_window':cb(456,0)
  return 1
 def pid(w,p):p._obj.value=0;return 1
 def cls(w,b,n):b.value='SDL_app';return 1
 def post(*a):
  state['closes']+=1
  if case=='WM_CLOSE_failure':return 0
  state['alive']=False;return 1
 u.EnumWindows=Fn(enum);u.GetWindowThreadProcessId=Fn(pid);u.GetClassNameW=Fn(cls);u.PostMessageW=Fn(post)
 C.WinDLL=lambda name,**kw:k if name=='kernel32'else u
 if case=='disk_query_failure':shutil.disk_usage=lambda p:(_ for _ in()).throw(OSError('injected disk query failure'))
 else:shutil.disk_usage=origdisk
 sys.argv=[str(target),str(cap)];error=None
 try:runpy.run_path(str(target),run_name='__main__')
 except BaseException as e:error=repr(e)
 assert not state['alive'] and state['handlecloses']==1,(case,state)
 receipt=json.loads((cap/'owned-resource-guard.json').read_text());assert receipt['process_exited']
 if case in ['disk_query_failure','missing_SDL_window','WM_CLOSE_failure']:assert error and state['terminates']==1
 else:assert error is None,(case,error)
 rows.append(dict(case=case,error=error,result=state,receipt=str(cap/'owned-resource-guard.json'),actions=receipt['actions']))
C.WinDLL=orig;shutil.disk_usage=origdisk
out.write_text(json.dumps(dict(scope='MOCKED Windows API supervisor fault tests ONLY; PID0 is synthetic, no real process/guest/input or game writes. Tests cover failclosed on diskquery/noSDL/PostMessage failure, ordinary45close, hard47.1stop.',watcher_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),tests=rows),indent=2)+'\n');print(out);print('PASS5 synthetic supervisor scenarios')
