"""PVS23-only frozen v4 native job. No native work at import."""
from pathlib import Path
import ctypes as C,ctypes.wintypes as W,datetime,hashlib,importlib.util,json,os,shutil,subprocess,sys,threading,time
HELPER=Path(r'C:\Game Dev\Emulators\codex-lanes\castle-controls21\owned-windows-writer-job.py')
HELPER_SHA='5dde0bbfd6f288b86bc8662bf3a7d2dfa654b39d83e523052b11fed21c7a4558'
API=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-qa21-death-repair\port\dreamcast\tools\d367\qa22_nontrace_detached_run_v1\reference-hooks\native_reference_api.py')
API_SHA='466d5cfb558b57dc03d08050012573a5e783dfe21c69990aa4fd4fdf6f35d255'
COUNTER=API.parent.parent/'native-process-count.py'
COUNTER_SHA='bb381698b1a731f630c7ca560628355f44575877643f15a566b7cc4642d5211b'
FLOOR=19394461696+1073741824
P=Path(__file__).parent

def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def all_guest_count():
 if sha(COUNTER)!=COUNTER_SHA:raise ValueError('native counter changed')
 m=load('backface_readonly_counter',COUNTER)
 class BothNames(m.Native):
  def normalize(self,ptr):
   e=ptr._obj;name=bytes(e.exe).decode('utf-16-le').split('\0',1)[0].casefold()
   if name=='flycast-console.exe':
    raw='flycast.exe'.encode('utf-16-le');e.exe[:]=[0]*260
    for i in range(0,len(raw),2):e.exe[i//2]=int.from_bytes(raw[i:i+2],'little')
  def Process32FirstW(self,h,ptr):
   value=self.k.Process32FirstW(h,ptr)
   if value:self.normalize(ptr)
   return value
  def Process32NextW(self,h,ptr):
   value=self.k.Process32NextW(h,ptr)
   if value:self.normalize(ptr)
   return value
 return m.count_flycasts(BothNames())

from policy import validate_profile

def validate_pixel(argv,output,authority):
 return validate_profile(argv,output,authority,P,sha,HELPER,API,COUNTER)

def run(argv,output,*,guard_seconds=59,closure_seconds=59.5,cap=60000000,control=None,authority=None):
 # Only this backface child or one explicit non-emulator control script is allowed.
 output=Path(output);base=P/'controls' if control else Path(r'C:\Flycast-Evidence\re4-dreamcast\pvs23-20261022')
 output.absolute().relative_to(base.absolute())
 if output.resolve()!=output.absolute() or output.exists():raise ValueError('fresh canonical backface output required')
 if Path(argv[0]).resolve()!=Path(sys.executable).resolve() or argv[1]!='-B':raise ValueError('exact native Python -B required')
 expected=P/('control_child.py' if control else 'stock_child.py')
 if Path(argv[2]).resolve()!=expected.resolve():raise ValueError('only backface child argv allowed')
 if control not in (None,'normal','deadline','assignfail','descendant','late','cap'):raise ValueError('unknown control')
 if control:
  if not .2<=guard_seconds<=2 or not guard_seconds<closure_seconds<=3:raise ValueError('control bound')
 elif (guard_seconds,closure_seconds)!=(59,59.5):raise ValueError('COMMON native59/59.5 contract required')
 profile=validate_pixel(argv,output,authority) if control is None else None
 if sha(HELPER)!=HELPER_SHA or sha(API)!=API_SHA:raise ValueError('native helper/API changed')
 n=load('retained_native_declarations',HELPER);k,STARTUP,PROCESS,EXTENDED,ACCOUNT=n.native()
 k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
 api=load('known_reference_api',API).WindowsApi()
 output.mkdir(parents=True);report={'qualified':False,'control':control,'argv':argv,'guard_seconds':guard_seconds,'closure_seconds':closure_seconds,'helper_sha256':HELPER_SHA,'errors':[],'events':[],'resumed':False,'assigned':False,'job_empty':False,'original_retained_finalized':False,'OS_never_returns':'Unbounded native OS calls are outside proven closure; never claim an impossible wall guarantee.'}
 errors=report['errors'];state={'closed':False,'inflight':False,'process':None,'assigned':False};done=threading.Event();sample_stop=threading.Event();latest={'at':0,'bytes':0,'free':0,'error':None};origin=time.monotonic();job=None;pi=PROCESS();hard=None;sampler=None;retained={}
 def note(e):
  if len(errors)<32:errors.append(str(e))
 def ok(x):
  if not x:raise C.WinError(C.get_last_error())
  return x
 def times(h):
  t=[W.FILETIME() for _ in range(4)];ok(k.GetProcessTimes(h,*[C.byref(x) for x in t]));return [x.dwLowDateTime+(x.dwHighDateTime<<32) for x in t]
 def close_gate(why):
  state['closed']=True
  if why not in errors:note(why)
  # No filesystem/logger/window or main creation lock on the hard path.
  if job:
   try:ok(k.TerminateJobObject(job,125))
   except BaseException as e:note('job termination: '+repr(e))
  h=state['process']
  if h and not state['assigned']:
   try:
    if k.WaitForSingleObject(h,0)==258:ok(k.TerminateProcess(h,125))
   except BaseException as e:note('unassigned termination: '+repr(e))
 def empty():
  a=ACCOUNT();ok(k.QueryInformationJobObject(job,1,C.byref(a),C.sizeof(a),None));report['active_processes']=a.ActiveProcesses;return a.ActiveProcesses==0
 def charge():
  # Windows FILE_STANDARD_INFO allocation; no compressed-size accounting.
  class Standard(C.Structure):_fields_=[('allocated',C.c_int64),('size',C.c_int64),('links',W.DWORD),('deleted',C.c_ubyte),('directory',C.c_ubyte)]
  k.CreateFileW.argtypes=[W.LPCWSTR,W.DWORD,W.DWORD,C.c_void_p,W.DWORD,W.DWORD,W.HANDLE];k.CreateFileW.restype=W.HANDLE;k.GetFileInformationByHandleEx.argtypes=[W.HANDLE,C.c_int,C.c_void_p,W.DWORD]
  total=4096
  for f in output.rglob('*'):
   try:
    if f.is_symlink() or (hasattr(f,'is_junction') and f.is_junction()):raise RuntimeError('output alias')
    if f.is_dir():total+=4096;continue
    h=k.CreateFileW(str(f),0x80,7,None,3,0x200000,None)
    if h in (None,0,C.c_void_p(-1).value):ok(False)
    try:
     a=Standard();ok(k.GetFileInformationByHandleEx(h,1,C.byref(a),C.sizeof(a)))
     tags=(W.DWORD*2)();ok(k.GetFileInformationByHandleEx(h,9,C.byref(tags),C.sizeof(tags)))
     if tags[0]&0x400:raise RuntimeError('native reparse refused')
     if a.deleted or a.directory or min(a.size,a.allocated)<0:raise RuntimeError('bad output extent')
     ref=profile['hardlink_refs'].get(str(f)) if profile else None
     if ref:
      st=f.stat();source=Path(ref['source'])
      if not f.samefile(source) or (st.st_size,st.st_ino,st.st_dev,st.st_nlink)!=(ref['bytes'],ref['inode'],ref['device'],ref['links_before']+1) or a.links!=st.st_nlink:raise RuntimeError('exact active hardlink identity changed')
     else:total+=max(a.size,a.allocated)
    finally:ok(k.CloseHandle(h))
   except FileNotFoundError:continue
  return total
 def sample():
  while not sample_stop.is_set():
   try:
    latest.update(at=time.monotonic(),bytes=charge(),free=shutil.disk_usage('C:/').free,error=None)
    if job:
     members=api.job_pids(job)
     if len(members)>8:raise RuntimeError('all-helper private job8 limit')
     for pid in members:
      if pid in retained:continue
      h=k.OpenProcess(0x101000,False,pid)
      if not h:
       # A PID is never rebound to a later process. A disappearing member is
       # covered by the final kernel job-empty proof, not a fabricated pin.
       if pid in api.job_pids(job):raise C.WinError(C.get_last_error())
       continue
      try:pin=api.process(h,job,require_live=True)
      except BaseException:
       k.CloseHandle(h)
       if pid in api.job_pids(job):raise
       continue
      retained[pid]=(h,pin)
    if profile and all_guest_count()>16:raise RuntimeError('global16 overflow')
   except BaseException as e:latest.update(at=time.monotonic(),error=repr(e));return
   sample_stop.wait(.05)
 def guard():
  while not done.wait(.01):
   age=time.monotonic()-origin
   if age>=guard_seconds:close_gate('guard deadline')
   if latest['error']:close_gate('sampler: '+latest['error'])
   if age>.5 and time.monotonic()-latest['at']>.5:close_gate('sampler stale')
   if latest['bytes']+65536>=cap:close_gate('output soft cap')
   if latest['free'] and latest['free']<FLOOR:close_gate('runtime floor')
 try:
  if shutil.disk_usage('C:/').free<FLOOR+cap+67108864:raise RuntimeError('fresh admission +sourcepeer64MiB')
  if profile:
   report['initial_global_guests']=all_guest_count()
   if report['initial_global_guests']>=16:raise RuntimeError('global16 admission')
  job=ok(k.CreateJobObjectW(None,None));limits=EXTENDED();limits.BasicLimitInformation.LimitFlags=0x2000|8;limits.BasicLimitInformation.ActiveProcessLimit=8;ok(k.SetInformationJobObject(job,9,C.byref(limits),C.sizeof(limits)))
  hard=threading.Thread(target=guard,name='backface-native-hardstop',daemon=True);hard.start()
  sampler=threading.Thread(target=sample,name='backface-resource-sample',daemon=True);sampler.start()
  si=STARTUP();si.cb=C.sizeof(si);state['inflight']=True;report['events'].append('guard armed before suspended CreateProcess')
  try:
   ok(k.CreateProcessW(str(argv[0]),C.create_unicode_buffer(subprocess.list2cmdline(argv)),None,None,False,4|8,None,str(P),C.byref(si),C.byref(pi)))
   # A delayed returned OS result is simulated only after an actual suspended child exists.
   if control=='late':time.sleep(guard_seconds+.1)
  finally:
   if pi.hProcess:state['process']=pi.hProcess
   state['inflight']=False
  if not pi.hProcess:raise RuntimeError('no returned process handle')
  created=times(pi.hProcess)[0];report['retained_pid']=int(pi.dwProcessId);report['creation_filetime']=created
  if state['closed'] or time.monotonic()-origin>=guard_seconds:raise RuntimeError('late create must never assign/resume')
  if control=='assignfail':raise OSError('injected assignment failure before native assign')
  ok(k.AssignProcessToJobObject(job,pi.hProcess));state['assigned']=True;report['assigned']=True;member=W.BOOL();ok(k.IsProcessInJob(pi.hProcess,job,C.byref(member)))
  if not member.value:raise RuntimeError('assigned membership missing')
  path=C.create_unicode_buffer(32768);count=W.DWORD(len(path));ok(k.QueryFullProcessImageNameW(pi.hProcess,0,path,C.byref(count)))
  if Path(path.value).resolve()!=Path(argv[0]).resolve():raise RuntimeError('retained executable path changed')
  if state['closed'] or time.monotonic()-origin>=guard_seconds:raise RuntimeError('late create/assignment must never resume')
  resume=k.ResumeThread(pi.hThread)
  if resume!=1:raise RuntimeError('unexpected suspended thread resume count: '+str(resume))
  report['resumed']=True
  while k.WaitForSingleObject(pi.hProcess,0)==258:
   if time.monotonic()-origin>=guard_seconds:close_gate('guard deadline')
   time.sleep(.01)
  code=W.DWORD();ok(k.GetExitCodeProcess(pi.hProcess,C.byref(code)));report['exit_code']=code.value
 except BaseException as e:note(type(e).__name__+': '+str(e));close_gate('exception cleanup')
 finally:
  # Never disarm while a late create can publish a live HANDLE.
  close_gate('final cleanup') if errors else None
  while True:
   finalized=not pi.hProcess
   if pi.hProcess:
    try:
     stamp=times(pi.hProcess);status=k.WaitForSingleObject(pi.hProcess,0);finalized=status==0 and stamp[1]>=stamp[0]>0 and stamp[0]==report.get('creation_filetime',stamp[0]);report['retained_times']=stamp;report['retained_wait']=status
    except BaseException as e:note('final identity: '+repr(e));finalized=False
   try:job_empty=not job or empty()
   except BaseException as e:note('job empty: '+repr(e));job_empty=False
   if finalized and job_empty and not state['inflight']:break
   close_gate('retained/job HOLD cleanup')
   if time.monotonic()-origin>=closure_seconds:report['closure_bound_failed']=True
   time.sleep(.01)
  report['job_empty']=job_empty;report['original_retained_finalized']=finalized;report['actual_root_seconds']=(report['retained_times'][1]-report['retained_times'][0])/1e7 if pi.hProcess else None
  sample_stop.set()
  if sampler:sampler.join(timeout=.1)
  while sampler and sampler.is_alive():
   note('sampler join HOLD; closure bound failed');report['closure_bound_failed']=True;sampler.join(timeout=.02)
  done.set()
  if hard:hard.join(timeout=.1)
  while hard and hard.is_alive():
   note('hardstop join HOLD; closure bound failed');report['closure_bound_failed']=True;hard.join(timeout=.02)
  threads_joined=not ((hard and hard.is_alive()) or (sampler and sampler.is_alive()))
  report['retained_members']=[]
  if threads_joined:
   for pid,(h,pin) in retained.items():
    try:
     row=api.process(h,job,pin)
     if row['phase']!='exited' or row['wait_status']!=0:raise RuntimeError('retained helper not finalized')
     report['retained_members'].append(row)
    except BaseException as e:note('retained member '+str(pid)+': '+repr(e))
  try:
   report['final_charged_bytes']=charge()
   if report['final_charged_bytes']+65536>=cap:note('final output cap/reserve')
  except BaseException as e:note('final resource sample: '+repr(e))
  if threads_joined:
   report['handles_closed']=True
   for h in (pi.hThread,pi.hProcess,*[v[0] for v in retained.values()],job):
    if h:
     try:ok(k.CloseHandle(h))
     except BaseException as e:note('handle close: '+repr(e));report['handles_closed']=False
  else:report['handles_closed']=False
  report['execution_closure_seconds']=time.monotonic()-origin;report['charged_bytes']=latest['bytes'];report['qualified']=bool(not errors and report['resumed'] and report.get('exit_code')==0 and finalized and job_empty and threads_joined and report.get('handles_closed') and not report.get('closure_bound_failed') and report['execution_closure_seconds']<=closure_seconds)
  if report['execution_closure_seconds']>closure_seconds:note('59.5/control closure exceeded');report['qualified']=False
  (output/'controller-result.json').write_text(json.dumps(report,indent=2)+'\n')
 return report
