from pathlib import Path
import sys,time,json,shutil,ctypes as C,ctypes.wintypes as W,threading
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');cap=Path(sys.argv[1]).resolve();assert cap.parent==D and cap.name.startswith('route-walk')
k=C.WinDLL('kernel32',use_last_error=True);u=C.WinDLL('user32',use_last_error=True)
k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE;k.GetProcessTimes.argtypes=[W.HANDLE]+[C.POINTER(W.FILETIME)]*4;k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)];k.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD];k.TerminateProcess.argtypes=[W.HANDLE,W.UINT];k.CloseHandle.argtypes=[W.HANDLE];k.GetExitCodeProcess.argtypes=[W.HANDLE,C.POINTER(W.DWORD)]
u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)];u.GetClassNameW.argtypes=[W.HWND,W.LPWSTR,C.c_int];u.PostMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM];CALL=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM);u.EnumWindows.argtypes=[CALL,W.LPARAM]
rows=[];actions=[];owner=None;h=None;identity_pinned=False;closed_identity=None;deadline=time.monotonic()+80
try:
 while not(cap/'owned-process.json').exists():assert time.monotonic()<deadline;time.sleep(.05)
 owner=json.loads((cap/'owned-process.json').read_text());assert Path(owner['path']).resolve()==cap/'flycast.exe';h=k.OpenProcess(0x100000|0x1000|1,False,owner['pid']);assert h
 def verify():
  global identity_pinned
  if identity_pinned and k.WaitForSingleObject(h,0)==0:return False
  a,b,c,d=(W.FILETIME()for _ in range(4));ok=k.GetProcessTimes(h,C.byref(a),C.byref(b),C.byref(c),C.byref(d))
  if not ok and identity_pinned and k.WaitForSingleObject(h,0)==0:return False
  assert ok,'Live process times query failed';assert a.dwLowDateTime+(a.dwHighDateTime<<32)==owner['start_filetime'],'Live process start identity mismatch'
  if k.WaitForSingleObject(h,0)==0:assert identity_pinned,'Process exited before initial identity pin';return False
  p=C.create_unicode_buffer(32768);n=W.DWORD(32768);ok=k.QueryFullProcessImageNameW(h,0,p,C.byref(n))
  if not ok and k.WaitForSingleObject(h,0)==0 and identity_pinned:return False
  assert ok,'Live image path query failed';assert Path(p.value).resolve()==cap/'flycast.exe','Live executable identity mismatch';identity_pinned=True
  return k.WaitForSingleObject(h,0)==258
 def collect_pinned_exit(reason):
  # A successful TerminateProcess request is asynchronous. Keep the ORIGINAL owned handle
  # until it signals, without any dead-PID path query and without extending47.5s.
  assert identity_pinned,'No initial live PID/path/start identity pin'
  while True:
   signal=k.WaitForSingleObject(h,0);now_age=baseage+time.monotonic()-t0
   if signal==0:
    code=W.DWORD();assert k.GetExitCodeProcess(h,C.byref(code))and code.value!=259,'Pinned handle lacks final exit code'
    a,b,c,d=(W.FILETIME()for _ in range(4));times_ok=bool(k.GetProcessTimes(h,C.byref(a),C.byref(b),C.byref(c),C.byref(d)))
    if times_ok:assert a.dwLowDateTime+(a.dwHighDateTime<<32)==owner['start_filetime'],'Retained creation time changed'
    observed_age=baseage+time.monotonic()-t0;assert observed_age<47.5,('Absolute process bound exceeded',observed_age)
    return dict(initial_live_identity_pinned=True,retained_handle_signaled=True,exit_code=code.value,postexit_times_available=times_ok,postexit_path_query=False,proof_reason=reason),observed_age
   assert signal==258,('Unexpected pinned handle wait status',signal)
   assert now_age<47.45,('Pinned process exit not witnessed before absolute margin',now_age)
   k.WaitForSingleObject(h,min(20,max(1,int((47.45-now_age)*1000))))

 verify();baseage=time.time()-(owner['start_filetime']/1e7-11644473600);t0=time.monotonic();close_sent=False
 stop_sample=threading.Event();latest={'time':time.monotonic(),'free':None,'logical':None,'error':None}
 def sample_resources():
  while not stop_sample.is_set():
   try:
    free=shutil.disk_usage(D).free;logical=0
    for p in cap.rglob('*'):
     try:
      if p.is_file():logical+=p.stat().st_size
     except FileNotFoundError:pass
    latest.update(time=time.monotonic(),free=free,logical=logical,error=None)
   except BaseException as e:latest.update(time=time.monotonic(),error=repr(e));return
   stop_sample.wait(.2)
 threading.Thread(target=sample_resources,daemon=True,name='owned-cap-resource-sampler').start()
 while k.WaitForSingleObject(h,0)==258:
  age=baseage+time.monotonic()-t0
  if age>=47.1:
   if not verify():continue
   assert k.TerminateProcess(h,73);actions.append(dict(action='exact_owned_absolute_termination',age=age,reason='47.5s absolute bound; WM_CLOSE grace exhausted'));break
  snap=dict(latest);assert not snap['error'],('Resource sampler failed',snap['error']);assert time.monotonic()-snap['time']<1,'Resource sampler stalled; fail closed'
  if snap['free']is None:time.sleep(.025);continue
  free,logical=snap['free'],snap['logical'];age=baseage+time.monotonic()-t0;rows.append(dict(monotonic=time.monotonic(),process_age_seconds=age,free=free,cap_logical_bytes=logical,sample_monotonic=snap['time']))
  if age>=47:continue
  if not close_sent and(age>=45 or free<18*1024**3+64*1024**2 or logical>60*1024**2):
   if not verify():continue
   wins=[]
   @CALL
   def cb(w,_):
    p=W.DWORD();u.GetWindowThreadProcessId(w,C.byref(p));c=C.create_unicode_buffer(256);u.GetClassNameW(w,c,256)
    if p.value==owner['pid']and c.value=='SDL_app':wins.append(int(w))
    return True
   assert u.EnumWindows(cb,0)
   if k.WaitForSingleObject(h,0)==0:continue
   assert len(wins)==1,wins;posted=u.PostMessageW(wins[0],0x10,0,0)
   if not posted and k.WaitForSingleObject(h,0)==0:continue
   assert posted;close_sent=True;actions.append(dict(action='exact_owned_SDL_WM_CLOSE',age=age,free=free,cap_logical_bytes=logical,hwnd=wins[0]))
  time.sleep(.05)
 closed_identity,exit_age=collect_pinned_exit('normal or absolute loop exit')
except BaseException as e:
 import traceback
 actions.append(dict(action='watcher_exception_fail_closed',error=repr(e),traceback=traceback.format_exc()))
 try:
  if h:
   if k.WaitForSingleObject(h,0)==258 and verify():
    assert k.TerminateProcess(h,74);actions.append(dict(action='exact_owned_fail_closed_termination_requested',reason=repr(e),age=baseage+time.monotonic()-t0))
   if identity_pinned:
    closed_identity,exit_age=collect_pinned_exit('exception fail-closed cleanup')
    actions.append(dict(action='exact_owned_fail_closed_exit_witnessed',age=exit_age,exit_code=closed_identity['exit_code']))
 except BaseException as cleanup_error:
  actions.append(dict(action='exception_cleanup_exit_proof_failed',error=repr(cleanup_error)))
 raise
finally:
 if 'stop_sample'in locals():stop_sample.set()
 process_exited=bool(h and k.WaitForSingleObject(h,0)==0)
 if h:k.CloseHandle(h)
 if cap.exists():(cap/'owned-resource-guard.json').write_text(json.dumps(dict(scope='Owned process resources/time only; PID/path/start verified. Filesystem sampler isolated on daemon thread; deadline loop never performs filesystem I/O. Fail closed if sampler stale1s. WM_CLOSE at45s or resource boundary, terminate only same verified process at47.1s if needed. Asynchronous termination cleanup retains pinned handle until exit proof within47.5, preserving failed run status; no gameplay memory writes.',owner=owner,closed_identity=closed_identity,process_exited=process_exited,runtime_floor=18*1024**3+64*1024**2,capture_cap=60*1024**2,inner_input_seconds=41,absolute_process_seconds=47.5,exit_age=locals().get('exit_age'),actions=actions,samples=rows),indent=2)+'\n')
