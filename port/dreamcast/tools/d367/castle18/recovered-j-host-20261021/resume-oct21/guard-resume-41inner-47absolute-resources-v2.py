from pathlib import Path
import sys,time,json,shutil,ctypes as C,ctypes.wintypes as W
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');cap=Path(sys.argv[1]).resolve();assert cap.parent==D and cap.name.startswith('route-walk')
k=C.WinDLL('kernel32',use_last_error=True);u=C.WinDLL('user32',use_last_error=True)
k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE;k.GetProcessTimes.argtypes=[W.HANDLE]+[C.POINTER(W.FILETIME)]*4;k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)];k.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD];k.TerminateProcess.argtypes=[W.HANDLE,W.UINT];k.CloseHandle.argtypes=[W.HANDLE]
u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)];u.GetClassNameW.argtypes=[W.HWND,W.LPWSTR,C.c_int];u.PostMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM];CALL=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM);u.EnumWindows.argtypes=[CALL,W.LPARAM]
rows=[];actions=[];owner=None;h=None;deadline=time.monotonic()+80
try:
 while not(cap/'owned-process.json').exists():assert time.monotonic()<deadline;time.sleep(.05)
 owner=json.loads((cap/'owned-process.json').read_text());assert Path(owner['path']).resolve()==cap/'flycast.exe';h=k.OpenProcess(0x100000|0x1000|1,False,owner['pid']);assert h
 def verify():
  a,b,c,d=(W.FILETIME()for _ in range(4));assert k.GetProcessTimes(h,C.byref(a),C.byref(b),C.byref(c),C.byref(d));assert a.dwLowDateTime+(a.dwHighDateTime<<32)==owner['start_filetime'];p=C.create_unicode_buffer(32768);n=W.DWORD(32768);assert k.QueryFullProcessImageNameW(h,0,p,C.byref(n));assert Path(p.value).resolve()==cap/'flycast.exe'
 verify();baseage=time.time()-(owner['start_filetime']/1e7-11644473600);t0=time.monotonic();close_sent=False
 while k.WaitForSingleObject(h,0)==258:
  age=baseage+time.monotonic()-t0
  if age>=47.1:
   verify();assert k.TerminateProcess(h,73);actions.append(dict(action='exact_owned_absolute_termination',age=age,reason='47.5s absolute bound; WM_CLOSE grace exhausted'));assert k.WaitForSingleObject(h,300)==0,'Exact process did not exit within absolute guard grace';break
  free=shutil.disk_usage(D).free;logical=0
  for p in cap.rglob('*'):
   try:
    if p.is_file():logical+=p.stat().st_size
   except FileNotFoundError:pass
  age=baseage+time.monotonic()-t0;rows.append(dict(monotonic=time.monotonic(),process_age_seconds=age,free=free,cap_logical_bytes=logical))
  if age>=47:continue
  if not close_sent and(age>=45 or free<18*1024**3+64*1024**2 or logical>60*1024**2):
   verify();wins=[]
   @CALL
   def cb(w,_):
    p=W.DWORD();u.GetWindowThreadProcessId(w,C.byref(p));c=C.create_unicode_buffer(256);u.GetClassNameW(w,c,256)
    if p.value==owner['pid']and c.value=='SDL_app':wins.append(int(w))
    return True
   assert u.EnumWindows(cb,0);assert len(wins)==1,wins;assert u.PostMessageW(wins[0],0x10,0,0);close_sent=True;actions.append(dict(action='exact_owned_SDL_WM_CLOSE',age=age,free=free,cap_logical_bytes=logical,hwnd=wins[0]))
  time.sleep(.05)
 verify();exit_age=baseage+time.monotonic()-t0;assert exit_age<47.5,('Absolute process bound exceeded',exit_age)
except BaseException as e:
 actions.append(dict(action='watcher_exception_fail_closed',error=repr(e)))
 if h and k.WaitForSingleObject(h,0)==258:
  verify();assert k.TerminateProcess(h,74);assert k.WaitForSingleObject(h,300)==0;actions.append(dict(action='exact_owned_fail_closed_termination',reason=repr(e)))
 raise
finally:
 process_exited=bool(h and k.WaitForSingleObject(h,0)==0)
 if h:k.CloseHandle(h)
 if cap.exists():(cap/'owned-resource-guard.json').write_text(json.dumps(dict(scope='Owned process resources/time only; PID/path/start verified. WM_CLOSE at45s or resource boundary, terminate only same verified process at47.1s if needed; no gameplay memory writes.',owner=owner,process_exited=process_exited,runtime_floor=18*1024**3+64*1024**2,capture_cap=60*1024**2,inner_input_seconds=41,absolute_process_seconds=47.5,exit_age=locals().get('exit_age'),actions=actions,samples=rows),indent=2)+'\n')
