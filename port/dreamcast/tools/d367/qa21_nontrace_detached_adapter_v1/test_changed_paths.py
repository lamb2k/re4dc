"""Focused SOURCE fake-native/owned-lifecycle controls. No native query/process."""
import ast,ctypes as C,importlib.util,pathlib,tempfile,types,unittest
P=pathlib.Path(__file__).parent

def load(name,file):
 spec=importlib.util.spec_from_file_location(name,P/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
counter=load('counter','native-process-count.py');backend=load('backend','windows-backend.py');core=load('core','guest-supervisor-core.py');footprint=load('footprint','evidence-footprint-native.py')
class Snap:
 def __init__(self,names=(),next_error=18,first_error=18,handle=88,raise_next=False):self.names=names;self.index=-1;self.last=0;self.next_error=next_error;self.first_error=first_error;self.handle=handle;self.closed=[];self.raise_next=raise_next
 def CreateToolhelp32Snapshot(self,flags,pid):self.flags=(flags,pid);return self.handle
 def error(self):return self.last
 def put(self,ptr):
  entry=ptr._obj;entry.pid=self.index+1
  raw=self.names[self.index].encode('utf-16-le');entry.exe[:]=[0]*260
  for i in range(0,len(raw),2):entry.exe[i//2]=int.from_bytes(raw[i:i+2],'little')
 def Process32FirstW(self,h,ptr):
  if not self.names:self.last=self.first_error;return 0
  self.index=0;self.put(ptr);return 1
 def Process32NextW(self,h,ptr):
  if self.raise_next:raise ValueError('injected counter exception')
  self.index+=1
  if self.index>=len(self.names):self.last=self.next_error;return 0
  self.put(ptr);return 1
 def CloseHandle(self,h):self.closed.append(h);self.last=999;return 1
class Handle:
 def __init__(self):self.closed=False
 def __int__(self):return 88
 def Close(self):self.closed=True
class Proc:
 pid=7;returncode=None
 def __init__(self):self._handle=Handle()
class Life:
 def __init__(self):self.inner=Proc();self.alive=True;self.calls=[];self.deadline_thread=None;self.stops=0
 def free(self):return 100*1024**3
 def global_count(self):return 0
 def evidence_bytes(self):return 0
 def create_private_job(self):return 123
 def spawn_waiting(self,cmd,job):raise OSError('assignment failed; owned Popen retained')
 def arm_deadlines(self,inner):self.calls.append('arm');self.deadline_thread=object()
 def stop_private_job(self,job):
  self.calls.append('stop');self.stops+=1
  if self.stops==1:raise OSError('first stop denied')
  self.alive=False
 def close_release_pipe(self,inner):self.calls.append('pipe')
 def wait(self,inner):
  self.calls.append('wait')
  if self.alive:raise OSError('retained wait pending')
 def inner_shutdown_proof(self,inner):self.calls.append('proof');return {'finalized':not self.alive}
 def wait_private_job_empty(self,job):self.calls.append('empty') # inner was never assigned
 def stop_deadlines(self):
  if self.alive:raise AssertionError('unsafe early disarm')
  self.calls.append('join')
 def close_owned_handles(self,job,inner,guest):
  if self.alive or inner is not self.inner:raise AssertionError('lost/unsafe owned handle')
  self.calls.append('close');inner._handle.Close()
 def tick(self):pass
class Tests(unittest.TestCase):
 def test_all_invalid_snapshot_handles_refuse_without_close(self):
  for handle in (None,0,-1):
   with self.subTest(handle=handle):
    api=Snap(handle=handle);api.last=6
    with self.assertRaises(counter.QueryError) as caught:counter.count_flycasts(api)
    self.assertEqual(caught.exception.winerror,6);self.assertEqual(api.closed,[])
 def test_zero_last_error_is_failure_not_empty_success(self):
  for names,first,next_ in [((),0,18),(['flycast.exe'],18,0)]:
   with self.subTest(names=names):
    api=Snap(names,first_error=first,next_error=next_)
    with self.assertRaises(counter.QueryError) as caught:counter.count_flycasts(api)
    self.assertEqual(caught.exception.winerror,0);self.assertEqual(api.closed,[88])
 def test_snapshot_close_failure_refuses(self):
  api=Snap(['flycast.exe'])
  def close(h):api.closed.append(h);api.last=6;return 0
  api.CloseHandle=close
  with self.assertRaises(counter.QueryError) as caught:counter.count_flycasts(api)
  self.assertEqual(caught.exception.winerror,6);self.assertEqual(api.closed,[88])
 def test_duplicate_pid_refuses_partial_count(self):
  api=Snap(['flycast.exe','python.exe']);original=api.put
  def put(ptr):original(ptr);ptr._obj.pid=1
  api.put=put
  with self.assertRaises(RuntimeError):counter.count_flycasts(api)
  self.assertEqual(api.closed,[88])
 def test_native_counter_prototypes_without_native_query(self):
  calls=[]
  class Fn:
   def __call__(self,*args):raise AssertionError('must not query during binding')
  fake=types.SimpleNamespace(**{n:Fn() for n in ('CreateToolhelp32Snapshot','Process32FirstW','Process32NextW','CloseHandle')})
  old_name=counter.os.name;old_dll=getattr(C,'WinDLL',None)
  try:
   counter.os.name='nt';C.WinDLL=lambda *a,**k:(calls.append((a,k)) or fake);counter.Native()
  finally:
   counter.os.name=old_name
   if old_dll is None:del C.WinDLL
   else:C.WinDLL=old_dll
  self.assertEqual(fake.CreateToolhelp32Snapshot.restype,C.c_void_p)
  self.assertEqual(fake.Process32FirstW.argtypes,[C.c_void_p,C.POINTER(counter.Entry)])
  self.assertEqual(fake.Process32NextW.argtypes,fake.Process32FirstW.argtypes)
  self.assertEqual(len(calls),1)
 def test_startup_info_membership_failures_retain_original_handle(self):
  for phase in ('info','assign','query','missing','success'):
   with self.subTest(phase=phase):
    b=backend.WindowsBackend.__new__(backend.WindowsBackend);b.job=123;b.inner=None;proc=Proc();pin={'pid':7,'start_filetime':42,'path':'c:/python.exe'}
    def info(*a):
     if phase=='info':raise OSError('info denied')
     return pin
    def membership(h,j,ptr):ptr._obj.value=int(phase!='missing');return int(phase!='query')
    def checked(v):
     if not v:raise OSError('native call denied')
     return v
    b.info=info;b.checked=checked;b.k=types.SimpleNamespace(AssignProcessToJobObject=lambda *a:int(phase!='assign'),IsProcessInJob=membership)
    old=backend.subprocess.Popen;oldflag=getattr(backend.subprocess,'DETACHED_PROCESS',None);backend.subprocess.DETACHED_PROCESS=8;backend.subprocess.Popen=lambda *a,**k:proc
    try:
     if phase=='success':self.assertIs(b.spawn_waiting(['python'],123),proc)
     else:
      with self.assertRaises((OSError,RuntimeError)):b.spawn_waiting(['python'],123)
    finally:
     backend.subprocess.Popen=old
     if oldflag is None:del backend.subprocess.DETACHED_PROCESS
     else:backend.subprocess.DETACHED_PROCESS=oldflag
    self.assertIs(b.inner,proc);self.assertFalse(proc._handle.closed);self.assertEqual(b.inner_assigned,phase=='success');self.assertEqual(b.inner_identity,None if phase=='info' else pin)
 def test_empty_job_and_pending_inner_keeps_guard_and_handles_on_hold(self):
  b=Life();b.stop_private_job=lambda job:b.calls.append('stop-denied')
  def tick():raise InterruptedError('end fake persistent HOLD observation')
  b.tick=tick
  with self.assertRaises(InterruptedError):core.monitor(b,['not launched'])
  self.assertNotIn('join',b.calls);self.assertNotIn('close',b.calls);self.assertFalse(b.inner._handle.closed)
 def test_signaled_inner_but_nonempty_job_keeps_guard_and_handles_on_hold(self):
  b=Life();b.alive=False
  def notempty(job):b.calls.append('nonempty');raise OSError('job not empty')
  def tick():raise InterruptedError('end fake persistent HOLD observation')
  b.wait_private_job_empty=notempty;b.tick=tick
  with self.assertRaises(InterruptedError):core.monitor(b,['not launched'])
  self.assertNotIn('join',b.calls);self.assertNotIn('close',b.calls);self.assertFalse(b.inner._handle.closed)
 def test_owned_stop_attempts_unassigned_termination_even_when_job_stop_denied(self):
  b=backend.WindowsBackend.__new__(backend.WindowsBackend);b.job=123;b.inner=Proc();b.inner_identity=None;b.inner_assigned=False;calls=[]
  def checked(v):
   if not v:raise OSError('job termination denied')
   return v
  b.checked=checked;b.k=types.SimpleNamespace(TerminateJobObject=lambda *a:(calls.append('job') or 0),WaitForSingleObject=lambda *a:258,TerminateProcess=lambda *a:(calls.append(('inner',a[0])) or 1))
  with self.assertRaises(RuntimeError):b.stop_private_job(123)
  self.assertEqual(calls,['job',('inner',88)]);self.assertFalse(b.inner._handle.closed)
 def test_retained_inner_signaled_birth_and_exit_required(self):
  for stamp,status,pin,expected in [([42,99,0,0],0,None,True),([42,99,0,0],258,None,False),([42,0,0,0],0,None,False),([42,41,0,0],0,None,False),([42,99,0,0],0,{'pid':7,'start_filetime':41,'path':'c:/python.exe'},False)]:
   b=backend.WindowsBackend.__new__(backend.WindowsBackend);b.inner=Proc();b.inner_identity=pin;b.times=lambda h:stamp;b.k=types.SimpleNamespace(WaitForSingleObject=lambda *a:status);b.retained_identity=lambda *a:pin
   self.assertEqual(b.inner_shutdown_proof(b.inner)['finalized'],expected);self.assertFalse(b.inner._handle.closed)
 def test_native_allocation_excludes_only_exact_top_level_track_samefile(self):
  import os
  with tempfile.TemporaryDirectory() as tmp:
   top=pathlib.Path(tmp);disc=top/'disc';root=top/'own';disc.mkdir();root.mkdir();(disc/'track03.iso').write_bytes(b'fixed');os.link(disc/'track03.iso',root/'track03.iso');sub=root/'sub';sub.mkdir();(sub/'track03.iso').write_bytes(b'owned');(root/'flycast.exe').write_bytes(b'exe')
   result=footprint.measure(root,disc,lambda path,st:{'size':st.st_size,'allocated':4096})
   self.assertEqual(result['charged_bytes'],4096*4);self.assertEqual(len(result['excluded_exact_track_references']),1);self.assertEqual(result['excluded_exact_track_references'][0]['new_file_data_bytes'],0)
 def test_same_named_nonalias_track_is_charged(self):
  with tempfile.TemporaryDirectory() as tmp:
   top=pathlib.Path(tmp);disc=top/'disc';root=top/'own';disc.mkdir();root.mkdir();(disc/'track03.iso').write_bytes(b'fixed');(root/'track03.iso').write_bytes(b'fixed')
   result=footprint.measure(root,disc,lambda path,st:{'size':st.st_size,'allocated':8192})
   self.assertEqual(result['charged_bytes'],4096+8192);self.assertEqual(result['excluded_exact_track_references'],[])
 def test_bound_output_and_seed_changes_are_exact(self):
  base=P.parent/'qa21_nontrace_owned_adapter_v1'
  for file in ('inner-adapter.py','outer-driver.py'):
   text=(P/file).read_text();self.assertIn('return-door-domains02',text);self.assertNotIn('return-door-domains01',text)
  self.assertEqual((P/'SEED_CONTRACT.json').read_bytes(),(base/'SEED_CONTRACT.json').read_bytes())
  self.assertEqual((P/'guest-profile-v2.json').read_bytes(),(base/'guest-profile-v2.json').read_bytes())
  tree=ast.parse((P/'outer-driver.py').read_text());oldtree=ast.parse((base/'outer-driver.py').read_text())
  for name in ('fixed_profile','validate_seed','postflight'):
   def node(t):return next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name==name)
   self.assertEqual(ast.dump(node(tree)),ast.dump(node(oldtree)))

 def test_counter_casefold_exact_basename(self):
  api=Snap(['Flycast.EXE','python.exe','flycast.exe','flycast.exe.old']);self.assertEqual(counter.count_flycasts(api),2);self.assertEqual(api.flags,(2,0));self.assertEqual(api.closed,[88])
 def test_empty_no_more_is_only_valid_zero(self):
  api=Snap();self.assertEqual(counter.count_flycasts(api),0);self.assertEqual(api.closed,[88])
 def test_first_error_refuses_not_zero(self):
  api=Snap(first_error=5)
  with self.assertRaises(counter.QueryError) as caught:counter.count_flycasts(api)
  self.assertEqual(caught.exception.winerror,5);self.assertEqual(api.closed,[88])
 def test_next_error_code_captured_before_close(self):
  api=Snap(['python.exe'],next_error=299)
  with self.assertRaises(counter.QueryError) as caught:counter.count_flycasts(api)
  self.assertEqual(caught.exception.winerror,299);self.assertEqual(api.last,999);self.assertEqual(api.closed,[88])
 def test_exception_always_closes_snapshot(self):
  api=Snap(['python.exe'],raise_next=True)
  with self.assertRaises(ValueError):counter.count_flycasts(api)
  self.assertEqual(api.closed,[88])
 def test_unsigned_invalid_handle_never_closed_or_counted(self):
  api=Snap(handle=(1<<(C.sizeof(C.c_void_p)*8))-1);api.last=5
  with self.assertRaises(counter.QueryError):counter.count_flycasts(api)
  self.assertEqual(api.closed,[])
 def test_windows_struct_abi_fixed_utf16(self):
  if C.sizeof(C.c_void_p)==8:self.assertEqual(C.sizeof(counter.Entry),568);self.assertEqual(counter.Entry.heap.offset,16);self.assertEqual(counter.Entry.exe.offset,44)
  else:self.assertEqual(C.sizeof(counter.Entry),556);self.assertEqual(counter.Entry.exe.offset,36)
  self.assertEqual(C.sizeof(counter.Entry().exe),520)
 def test_new_backend_assignment_failure_keeps_owned_proc(self):
  b=backend.WindowsBackend.__new__(backend.WindowsBackend);b.job=123;b.inner=None;proc=Proc();pin={'pid':7,'start_filetime':42,'path':'c:/python.exe'};b.info=lambda p,h:pin;b.k=types.SimpleNamespace(AssignProcessToJobObject=lambda *a:0)
  def checked(value):
   if not value:raise OSError('assignment denied')
   return value
  b.checked=checked;old=backend.subprocess.Popen;oldflag=getattr(backend.subprocess,'DETACHED_PROCESS',None);backend.subprocess.DETACHED_PROCESS=8;calls=[]
  backend.subprocess.Popen=lambda *a,**k:(calls.append(k) or proc)
  try:
   with self.assertRaises(OSError):b.spawn_waiting(['python'],123)
  finally:
   backend.subprocess.Popen=old
   if oldflag is None:del backend.subprocess.DETACHED_PROCESS
   else:backend.subprocess.DETACHED_PROCESS=oldflag
  self.assertIs(b.inner,proc);self.assertEqual(b.inner_identity,pin);self.assertFalse(proc._handle.closed);self.assertEqual(calls[0]['creationflags'],8)
 def test_core_emptyjob_does_not_drop_unassigned_live_inner(self):
  b=Life();result=core.monitor(b,['not launched'])
  self.assertFalse(result['qualified']);self.assertIn('assignment failed',result['error']);self.assertGreaterEqual(b.stops,2);self.assertTrue(b.inner._handle.closed);self.assertGreater(b.calls.index('join'),b.calls.index('proof'));self.assertEqual(b.calls[-1],'close')
 def test_backend_pending_inner_refuses_handleclose(self):
  b=backend.WindowsBackend.__new__(backend.WindowsBackend);b.inner=Proc();b.inner_identity={'pid':7,'start_filetime':42,'path':'c:/python.exe'};b.times=lambda h:[42,99,0,0];b.retained_identity=lambda *a:b.inner_identity;b.k=types.SimpleNamespace(WaitForSingleObject=lambda *a:258)
  self.assertFalse(b.inner_shutdown_proof(b.inner)['finalized'])
  with self.assertRaises(RuntimeError):b.close_owned_handles(123,b.inner,None)
  self.assertFalse(b.inner._handle.closed)
 def test_perfile_native_extent_and_directory_charge(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);(root/'a').write_text('x');(root/'b').write_text('x')
   result=footprint.measure(root,root/'absent-disc',lambda path,st:({'size':1000,'allocated':256} if path.name=='a' else {'size':100,'allocated':4096}))
   self.assertEqual(result['charged_bytes'],4096+1000+4096);self.assertEqual(result['charged_allocated_bytes'],4352)
 def test_launch_membership_and_gameplay_sources_stay_strict(self):
  base=P.parent/'qa21_nontrace_owned_adapter_v1'
  for n in ['controller-core.py','policies.py','observe.py','observer-v2.py','input-deadlines.py','guest-profile-v2.json','reference-hooks/parent_reference_broker.py','reference-hooks/reference_collector.py','reference-hooks/native_reference_api.py']:
   self.assertEqual((P/n).read_bytes(),(base/n).read_bytes(),n)
  current=(P/'reference-hooks/checkpoint_runner18.child.py').read_text();old=(base/'reference-hooks/checkpoint_runner18.child.py').read_text()
  tree=ast.parse(current);count=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='count_flycasts');oldtree=ast.parse(old);oldcount=next(n for n in oldtree.body if isinstance(n,ast.FunctionDef) and n.name=='count_flycasts')
  oldbody='\n'.join(old.splitlines()[oldcount.lineno-1:oldcount.end_lineno]);newbody='\n'.join(current.splitlines()[count.lineno-1:count.end_lineno])
  self.assertEqual(current.replace(newbody,oldbody).replace('subprocess.DETACHED_PROCESS','subprocess.CREATE_NO_WINDOW'),old)
if __name__=='__main__':unittest.main()
