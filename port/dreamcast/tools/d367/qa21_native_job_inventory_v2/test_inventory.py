"""v2 direct lineage/cleanup failure controls, no native/child calls."""
import copy,importlib.util,pathlib,types,unittest
P=pathlib.Path(__file__).parent

def load(name):
 s=importlib.util.spec_from_file_location(name,P/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
inventory=load('inventory');cleanup=load('cleanup');supervisor=load('supervisor')
PIN={'pid':7,'start_filetime':42,'path':'C:/python.exe'}
class Proc:
 pid=7;_handle=88;returncode=0
 def __init__(self,fail_wait=False):self.fail_wait=fail_wait;self.calls=[]
 def poll(self):self.calls.append('poll');return None
 def wait(self,timeout):
  self.calls.append('wait')
  if self.fail_wait:raise OSError('wait failed')
class Backend:
 def __init__(self,fail=(),stamp=None,status=0,identity=None):self.fail=fail;self.calls=[];self.stamp=stamp or [42,99,0,0];self.status=status;self.identity=identity or PIN.copy();self.k=types.SimpleNamespace(WaitForSingleObject=self.status_call)
 def call(self,name):
  self.calls.append(name)
  if name in self.fail:raise OSError(name+' failed')
 def close_release_pipe(self,p):self.call('pipe')
 def stop_private_job(self,j):self.call('stop')
 def wait(self,p):self.call('wait')
 def retained_identity(self,p,h,pin):self.call('identity');return self.identity
 def times(self,h):self.call('times');return self.stamp
 def status_call(self,h,t):self.call('status');return self.status
 def wait_private_job_empty(self,j):self.call('empty')
class Event:
 def __init__(self):self.flag=False;self.calls=[]
 def set(self):self.flag=True;self.calls.append('set')
 def is_set(self):return self.flag
 def wait(self,t):return self.flag
class Thread:
 def __init__(self):self.joined=False
 def join(self,timeout):self.joined=True
 def is_alive(self):return False
class Tests(unittest.TestCase):
 def capture(self,identity):
  rows=[];api=types.SimpleNamespace(job_pids=lambda j:[7])
  try:return inventory.capture(api,1,PIN,lambda pid:{'identity':identity},lambda row:rows.append(copy.deepcopy(row))),rows,None
  except Exception as exc:return None,rows,exc
 def test_original_pin_exact_pass(self):self.assertIsNone(self.capture(PIN.copy())[2])
 def test_original_birth_changed_refused_after_raw_saved(self):
  _,rows,exc=self.capture(dict(PIN,start_filetime=43));self.assertIsNotNone(exc);self.assertEqual(rows[0]['members'],[]);self.assertFalse(rows[-1]['members'][0]['matches_original_retained_pin'])
 def test_original_path_changed_refused(self):self.assertIsNotNone(self.capture(dict(PIN,path='C:/other.exe'))[2])
 def test_stop_failure_still_attempts_wait_telemetry_empty(self):
  b=Backend(fail=['stop']);errors=[];state=cleanup.job_cleanup(b,1,Proc(),PIN,errors)
  self.assertTrue(state['safe_to_disarm']);self.assertEqual(b.calls,['pipe','stop','wait','identity','times','status','empty']);self.assertEqual(errors[0]['operation'],'job_stop')
 def test_multiple_cleanup_failures_do_not_skip_empty(self):
  b=Backend(fail=['pipe','stop','wait','identity']);errors=[];state=cleanup.job_cleanup(b,1,Proc(),PIN,errors)
  self.assertIn('empty',b.calls);self.assertFalse(state['safe_to_disarm']);self.assertEqual(len(errors),4)
 def test_empty_failure_retains_guard_even_finalized_inner(self):
  state=cleanup.job_cleanup(Backend(fail=['empty']),1,Proc(),PIN,[]);self.assertTrue(state['inner_finalized']);self.assertFalse(state['safe_to_disarm'])
 def test_pending_timestamp_is_not_signaled(self):
  state=cleanup.job_cleanup(Backend(status=258),1,Proc(),PIN,[]);self.assertFalse(state['safe_to_disarm'])
 def test_changed_retained_birth_not_finalized(self):
  state=cleanup.job_cleanup(Backend(stamp=[43,99,0,0]),1,Proc(),PIN,[]);self.assertFalse(state['safe_to_disarm'])
 def test_missingproof_never_disarms_or_closes(self):
  e=Event();t=Thread();closed=[]
  with self.assertRaises(RuntimeError):cleanup.disarm_if_proven(False,e,t,lambda:closed.append(1))
  self.assertFalse(e.flag);self.assertFalse(t.joined);self.assertEqual(closed,[])
 def test_kill_and_wait_failure_still_queries_finalization(self):
  errors=[];calls=[]
  def kill(h):raise OSError('native terminate returned zero')
  def times(h):calls.append('times');return [42,0,0,0]
  state=cleanup.retained_cleanup(Proc(True),kill,times,lambda h:258,42,errors)
  self.assertEqual(calls,['times']);self.assertFalse(state['signaled_finalized']);self.assertEqual([e['operation'] for e in errors],['coordinator_terminate','coordinator_wait'])
 def test_killfailure_but_independently_signaled_is_safe_failure(self):
  errors=[]
  def kill(h):raise OSError('already exited')
  state=cleanup.retained_cleanup(Proc(True),kill,lambda h:[42,99,0,0],lambda h:0,42,errors)
  self.assertTrue(state['signaled_finalized']);self.assertEqual(len(errors),2)
 def test_absolute_killfailure_does_not_skip_signaledproof(self):
  done=Event();errors=[];exits=[]
  def kill(h):raise OSError('kill failed')
  state={'proc':Proc(),'terminate':kill,'times':lambda h:[42,99,0,0],'wait_status':lambda h:0,'birth':42,'errors':errors,'note':cleanup.note,'failure':cleanup.failure}
  old=supervisor.os._exit
  def exit(code):exits.append(code);done.set()
  supervisor.os._exit=exit
  try:supervisor.hard_parent(done,state)
  finally:supervisor.os._exit=old
  self.assertEqual(exits,[125]);self.assertEqual(errors[0]['operation'],'absolute_termination')
 def test_absolute_pending_failure_never_claims_safe_exit(self):
  done=Event();errors=[];exits=[]
  def kill(h):done.set();raise OSError('kill failed; still pending')
  state={'proc':Proc(),'terminate':kill,'times':lambda h:[42,0,0,0],'wait_status':lambda h:258,'birth':42,'errors':errors,'note':cleanup.note,'failure':cleanup.failure}
  old=supervisor.os._exit;supervisor.os._exit=lambda code:exits.append(code)
  try:supervisor.hard_parent(done,state)
  finally:supervisor.os._exit=old
  self.assertEqual(exits,[]);self.assertEqual(errors[0]['operation'],'absolute_termination')
if __name__=='__main__':unittest.main()
