"""Direct retained-unassigned startup failure controls only; no native processes."""
import ctypes,importlib.util,pathlib,types,unittest
P=pathlib.Path(__file__).parent

def load(name):
 s=importlib.util.spec_from_file_location(name,P/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
startup=load('startup');cleanup=load('cleanup')
if not hasattr(startup.subprocess,'DETACHED_PROCESS'):startup.subprocess.DETACHED_PROCESS=8 # fake-only Linux control
PIN={'pid':7,'start_filetime':42,'path':'C:/python.exe'}
class Handle:
 def __init__(self):self.closed=False
 def __int__(self):return 88
 def Close(self):self.closed=True
class Proc:
 pid=7;returncode=None
 def __init__(self):self._handle=Handle();self.wait_failure=True
 def poll(self):return None
 def wait(self,timeout):
  if self.wait_failure:raise OSError('injected retained wait denial')
  self.returncode=125
class Backend:
 def __init__(self,assign=False,info_failure=False):
  self.job=123;self.inner=None;self.assign=assign;self.info_failure=info_failure;self.status=258;self.stamp=[42,0,0,0];self.calls=[]
  self.k=types.SimpleNamespace(AssignProcessToJobObject=self.assign_call,IsProcessInJob=self.member_call,WaitForSingleObject=lambda h,t:self.status)
 def checked(self,value):
  if not value:raise OSError('injected native assignment denial')
  return value
 def assign_call(self,j,h):self.calls.append('assign');return self.assign
 def member_call(self,h,j,ptr):ptr._obj.value=1;return 1
 def info(self,p,h):
  self.calls.append('info')
  if self.info_failure:raise OSError('live path query denied')
  return PIN.copy()
 def close_release_pipe(self,p):self.calls.append('pipe')
 def stop_private_job(self,j):self.calls.append('stop');raise OSError('injected job stop denial')
 def wait(self,p):self.calls.append('wait');p.wait(.1)
 def retained_identity(self,p,h,pin):self.calls.append('identity');return PIN.copy()
 def times(self,h):self.calls.append('times');return self.stamp
 def wait_private_job_empty(self,j):self.calls.append('empty') # Unassigned inner is absent from job.
class Event:
 def __init__(self):self.flag=False
 def set(self):self.flag=True
class Thread:
 def __init__(self):self.joined=False
 def join(self,timeout):self.joined=True
 def is_alive(self):return False
class Tests(unittest.TestCase):
 def spawn_failed(self,backend):
  proc=Proc();popen_calls=[]
  def popen(cmd,**kwargs):popen_calls.append((cmd,kwargs));return proc
  with self.assertRaises(OSError):startup.spawn_retained(backend,['python','-B','exact-frozen-inner'],123,popen)
  return proc,popen_calls
 def test_assignment_failure_retains_original_owned_handle_and_pin(self):
  b=Backend();proc,calls=self.spawn_failed(b)
  self.assertIs(b.inner,proc);self.assertEqual(b.inner_identity,PIN);self.assertFalse(proc._handle.closed)
  self.assertEqual(calls[0][0],['python','-B','exact-frozen-inner']);self.assertIn('stdin',calls[0][1]);self.assertEqual(calls[0][1]['creationflags'],startup.subprocess.DETACHED_PROCESS)
 def test_unassigned_live_inner_prevents_emptyjob_false_disarm(self):
  b=Backend();proc,_=self.spawn_failed(b);errors=[];state=cleanup.job_cleanup(b,123,b.inner,b.inner_identity,errors)
  self.assertTrue(state['private_job_empty']);self.assertFalse(state['inner_finalized']);self.assertFalse(state['safe_to_disarm'])
  done=Event();thread=Thread()
  with self.assertRaises(RuntimeError):cleanup.disarm_if_proven(state['safe_to_disarm'],done,thread,proc._handle.Close)
  self.assertFalse(done.flag);self.assertFalse(thread.joined);self.assertFalse(proc._handle.closed)
  self.assertIn('wait',b.calls);self.assertIn('empty',b.calls);self.assertEqual([e['operation'] for e in errors],['job_stop','inner_wait'])
 def test_unassigned_handle_closes_only_after_signaled_finalized(self):
  b=Backend();proc,_=self.spawn_failed(b)
  before=cleanup.job_cleanup(b,123,proc,b.inner_identity,[]);self.assertFalse(before['safe_to_disarm'])
  b.status=0;b.stamp=[42,99,0,0];proc.wait_failure=False
  after=cleanup.job_cleanup(b,123,proc,b.inner_identity,[]);self.assertTrue(after['safe_to_disarm'])
  done=Event();thread=Thread();cleanup.disarm_if_proven(after['safe_to_disarm'],done,thread,proc._handle.Close)
  self.assertTrue(done.flag);self.assertTrue(thread.joined);self.assertTrue(proc._handle.closed)
 def test_identity_query_failure_retains_handle_without_fabricated_pin(self):
  b=Backend(info_failure=True);proc,_=self.spawn_failed(b)
  self.assertIs(b.inner,proc);self.assertIsNone(b.inner_identity);self.assertFalse(proc._handle.closed)
  before=cleanup.job_cleanup(b,123,proc,None,[]);self.assertFalse(before['safe_to_disarm'])
  b.status=0;b.stamp=[42,99,0,0];proc.wait_failure=False
  after=cleanup.job_cleanup(b,123,proc,None,[]);self.assertTrue(after['safe_to_disarm']);self.assertIsNone(after['inner_exit']['identity']);self.assertFalse(after['inner_exit']['original_live_pin_available'])
 def test_success_uses_original_assignment_and_membership_semantics(self):
  b=Backend(assign=True);proc=Proc();self.assertIs(startup.spawn_retained(b,['python'],123,lambda *a,**k:proc),proc)
  self.assertEqual(b.inner_identity,PIN);self.assertEqual(b.calls,['info','assign']);self.assertFalse(proc._handle.closed)
if __name__=='__main__':unittest.main()
