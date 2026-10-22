"""Windows retained-handle/private-job backend. Constructor only on explicit future run.
Source/mock preparation does not instantiate this backend or launch any process.
"""
import csv,ctypes,hashlib,json,os,pathlib,subprocess,sys,time,threading

class WindowsBackend:
 def __init__(self,cap,invocation,disc,emu_sha,footprint,clock=time.monotonic):
  if os.name!='nt':raise RuntimeError('Windows runtime only')
  self.cap=pathlib.Path(cap);self.invocation=pathlib.Path(invocation);self.disc=pathlib.Path(disc);self.emu_sha=emu_sha;self.footprint=footprint;self.clock=clock;self.job=None;self.inner=None;self.guest=None;self.startup=self.clock();self.input_released=False;self.deadline_stop=threading.Event();self.deadline_thread=None;self.deadline_failure=None
  k=self.k=ctypes.WinDLL('kernel32',use_last_error=True)
  k.CreateJobObjectW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p];k.CreateJobObjectW.restype=ctypes.c_void_p
  k.SetInformationJobObject.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_ulong];k.AssignProcessToJobObject.argtypes=[ctypes.c_void_p,ctypes.c_void_p];k.IsProcessInJob.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_int)];k.TerminateJobObject.argtypes=[ctypes.c_void_p,ctypes.c_uint]
  k.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];k.OpenProcess.restype=ctypes.c_void_p
  k.QueryFullProcessImageNameW.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)];k.GetProcessTimes.argtypes=[ctypes.c_void_p]+[ctypes.POINTER(ctypes.c_ulonglong)]*4;k.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)];k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong];k.TerminateProcess.argtypes=[ctypes.c_void_p,ctypes.c_uint];k.CloseHandle.argtypes=[ctypes.c_void_p]
  k.GetSystemTimeAsFileTime.argtypes=[ctypes.POINTER(ctypes.c_ulonglong)]
  self.u=ctypes.WinDLL('user32',use_last_error=True);self.u.PostMessageW.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_size_t,ctypes.c_ssize_t]
 def checked(self,value):
  if not value:raise ctypes.WinError(ctypes.get_last_error())
  return value
 def times(self,h):
  v=[ctypes.c_ulonglong() for _ in range(4)];self.checked(self.k.GetProcessTimes(h,*[ctypes.byref(x) for x in v]));return [x.value for x in v]
 def info(self,pid,h):
  path=ctypes.create_unicode_buffer(32768);n=ctypes.c_ulong(len(path));self.checked(self.k.QueryFullProcessImageNameW(h,0,path,ctypes.byref(n)));return {'pid':pid,'start_filetime':self.times(h)[0],'path':os.path.normcase(os.path.abspath(path.value))}
 def create_private_job(self):
  SIZE=ctypes.c_size_t;U64=ctypes.c_ulonglong;D=ctypes.c_ulong
  class Basic(ctypes.Structure):_fields_=[('PerProcessUserTimeLimit',ctypes.c_longlong),('PerJobUserTimeLimit',ctypes.c_longlong),('LimitFlags',D),('MinimumWorkingSetSize',SIZE),('MaximumWorkingSetSize',SIZE),('ActiveProcessLimit',D),('Affinity',SIZE),('PriorityClass',D),('SchedulingClass',D)]
  class IO(ctypes.Structure):_fields_=[(n,U64) for n in ['ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount']]
  class Extended(ctypes.Structure):_fields_=[('BasicLimitInformation',Basic),('IoInfo',IO),('ProcessMemoryLimit',SIZE),('JobMemoryLimit',SIZE),('PeakProcessMemoryUsed',SIZE),('PeakJobMemoryUsed',SIZE)]
  job=self.checked(self.k.CreateJobObjectW(None,None))
  try:
   limits=Extended();limits.BasicLimitInformation.LimitFlags=0x2000;self.checked(self.k.SetInformationJobObject(job,9,ctypes.byref(limits),ctypes.sizeof(limits)))
  except BaseException:self.k.CloseHandle(job);raise
  self.job=job;return job
 def spawn_waiting(self,cmd,job):
  if job!=self.job:raise RuntimeError('foreign job')
  proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
  self.inner=proc
  try:
   self.inner_identity=self.info(proc.pid,int(proc._handle));self.checked(self.k.AssignProcessToJobObject(job,int(proc._handle)))
   member=ctypes.c_int();self.checked(self.k.IsProcessInJob(int(proc._handle),job,ctypes.byref(member)))
   if not member.value:raise RuntimeError('job assignment not verified')
   return proc
  except BaseException:
   # The child waits for release and cannot launch Flycast yet. Retained Popen owns it.
   try:
    if proc.poll() is None:proc.terminate()
    proc.wait(timeout=2)
   finally:proc._handle.Close();self.inner=None
   raise
 def arm_deadlines(self,inner):
  # Conservative independent wall clock starts BEFORE the release handshake.
  # Thus hashing, PID registration or a blocked sampler cannot extend guest life.
  # No post-exit process query races: core joins this thread before cleanup/close.
  origin=self.clock()
  def guard():
   try:
    while not self.deadline_stop.wait(.02):
     elapsed=self.clock()-origin
     guest=self.guest
     if guest is not None:elapsed=max(elapsed,self.clock()-guest['anchor'])
     if elapsed>=40.75 and guest is not None and not self.input_released:self.release_inputs(guest)
     if elapsed>=47.0:
      self.deadline_failure='independent47.0s conservative private-job deadline'
      self.stop_private_job(self.job);return
   except BaseException as error:
    self.deadline_failure='deadline thread: '+type(error).__name__+': '+str(error)
    try:self.stop_private_job(self.job)
    except BaseException as stop_error:self.deadline_failure+='; stop: '+str(stop_error)
  self.deadline_thread=threading.Thread(target=guard,name='owned-guest-deadline',daemon=True);self.deadline_thread.start()
 def check_deadlines(self):
  if self.deadline_failure:raise RuntimeError(self.deadline_failure)
 def stop_deadlines(self):
  self.deadline_stop.set()
  if self.deadline_thread is not None:
   self.deadline_thread.join(timeout=2)
   if self.deadline_thread.is_alive():raise RuntimeError('deadline thread failed to join; handles must stay valid')
 def release(self,inner):inner.stdin.write(b'owned-job-ready\n');inner.stdin.flush();inner.stdin.close()
 def close_release_pipe(self,inner):
  if inner.stdin and not inner.stdin.closed:inner.stdin.close()
 def free(self):return __import__('shutil').disk_usage('C:/').free
 def global_count(self):
  text=subprocess.check_output(['tasklist','/FI','IMAGENAME eq flycast.exe','/FO','CSV','/NH'],text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=2)
  return sum(1 for r in csv.reader(text.splitlines()) if r and r[0].lower()=='flycast.exe')
 def evidence_bytes(self):return self.footprint.measure(self.cap,self.disc)['charged_bytes']+self.footprint.measure(self.invocation,self.disc)['charged_bytes']
 def find_guest(self):
  f=self.cap/'flycast.pid'
  try:value=f.read_text().strip()
  except FileNotFoundError:value=''
  if not value.isdigit():
   if self.clock()-self.startup>30:raise RuntimeError('startup PID deadline')
   return self.guest
  pid=int(value)
  if self.guest is not None:
   if pid!=self.guest['pid']:raise RuntimeError('owned PIDfile changed')
   return self.guest
  h=self.checked(self.k.OpenProcess(0x101001,False,pid))
  try:
   info=self.info(pid,h);expected=os.path.normcase(str((self.cap/'flycast.exe').resolve()))
   if info['path']!=expected:raise RuntimeError('guest executable ownership mismatch')
   member=ctypes.c_int();self.checked(self.k.IsProcessInJob(h,self.job,ctypes.byref(member)))
   if not member.value:raise RuntimeError('guest outside private job')
   if hashlib.sha256((self.cap/'flycast.exe').read_bytes()).hexdigest()!=self.emu_sha:raise RuntimeError('guest executable hash mismatch')
   now=ctypes.c_ulonglong();self.k.GetSystemTimeAsFileTime(ctypes.byref(now));age=(now.value-info['start_filetime'])/1e7
   self.guest={'pid':pid,'handle':h,'identity':info,'anchor':self.clock()-age};return self.guest
  except BaseException:self.k.CloseHandle(h);raise
 def retained_identity(self,pid,handle,pinned):
  created,exited,*_=self.times(handle)
  if created!=pinned['start_filetime']:raise RuntimeError('retained start identity changed')
  if exited:
   if self.k.WaitForSingleObject(handle,0)!=0:raise RuntimeError('retained exit not finalized')
   # QueryFullProcessImageNameW can fail after exit (WinError31). A retained
   # process HANDLE cannot refer to a recycled PID; path was checked while live.
   return pinned.copy()
  return self.info(pid,handle)
 def identity(self,guest):return self.retained_identity(guest['pid'],guest['handle'],guest['identity'])
 def actual_seconds(self,guest):
  created,exited,*_=self.times(guest['handle'])
  if created!=guest['identity']['start_filetime']:raise RuntimeError('guest process-start identity changed')
  if exited:
   if self.k.WaitForSingleObject(guest['handle'],0)!=0:raise RuntimeError('exit timestamp not finalized')
   if exited<created:raise RuntimeError('invalid process timestamps')
   return (exited-created)/1e7
  now=ctypes.c_ulonglong();self.k.GetSystemTimeAsFileTime(ctypes.byref(now));return max((now.value-created)/1e7,self.clock()-guest['anchor'])
 def guest_alive(self,guest):
  code=ctypes.c_ulong();self.checked(self.k.GetExitCodeProcess(guest['handle'],ctypes.byref(code)));return code.value==259
 def inner_alive(self,inner):return inner.poll() is None
 def exit_code(self,inner):return inner.returncode
 def wait(self,inner):
  try:return inner.wait(timeout=2)
  except subprocess.TimeoutExpired:raise RuntimeError('private inner wait timeout')
 def wait_guest(self,guest):
  if self.k.WaitForSingleObject(guest['handle'],2000)!=0:raise RuntimeError('private guest wait timeout')
 def release_inputs(self,guest):
  if self.identity(guest)!=guest['identity']:raise RuntimeError('foreign PID/start/path; no keyups')
  if not self.guest_alive(guest):return
  # Only own PID windows, re-enumerated; releasing all fixed controller keys never presses any.
  W=ctypes.WINFUNCTYPE(ctypes.c_int,ctypes.c_void_p,ctypes.c_ssize_t);windows=[]
  self.u.EnumWindows.argtypes=[W,ctypes.c_ssize_t];self.u.GetWindowThreadProcessId.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
  def cb(hwnd,_):
   pid=ctypes.c_ulong();self.u.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
   if pid.value==guest['pid']:windows.append(hwnd)
   return 1
  self.u.EnumWindows(W(cb),0)
  for scan,vk in [(0x2d,0x58),(0x2e,0x43),(0x2f,0x56),(0x21,0x46),(0x17,0x49),(0x25,0x4b),(0x24,0x4a),(0x26,0x4c),(0x1c,0x0d)]:
   for hwnd in windows:self.u.PostMessageW(hwnd,0x101,vk,1|(scan<<16)|(1<<30)|(1<<31))
  self.input_released=True
 def stop_private_job(self,job):
  if job!=self.job:raise RuntimeError('refuse foreign job')
  if self.inner is not None and self.retained_identity(self.inner.pid,int(self.inner._handle),self.inner_identity)!=self.inner_identity:raise RuntimeError('retained inner identity mismatch')
  self.checked(self.k.TerminateJobObject(job,125))
 def close_owned_handles(self,job,inner,guest):
  if self.deadline_thread is not None and self.deadline_thread.is_alive():raise RuntimeError('refuse handle closure under live deadline thread')
  try:
   if guest is not None:self.k.CloseHandle(guest['handle'])
  finally:
   try:
    if inner is not None:inner._handle.Close()
   finally:
    if job is not None:
     if job!=self.job:raise RuntimeError('refuse foreign job close')
     self.k.CloseHandle(job);self.job=None
 def tick(self):time.sleep(.05)
