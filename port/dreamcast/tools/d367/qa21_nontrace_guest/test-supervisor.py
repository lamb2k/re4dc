"""Deterministic no-process adversarial supervisor backend tests."""
import importlib.util,pathlib,unittest
s=importlib.util.spec_from_file_location('core',pathlib.Path(__file__).with_name('guest-supervisor-core.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Fake:
 def __init__(self,fault=None):self.t=0;self.calls=[];self.fault=fault;self.running=False;self.child=False;self.closed=False;self.id={'pid':21,'start':123,'path':'own/flycast.exe'};self.count=0
 def hit(self,n):
  self.calls.append(n)
  if self.fault==n:raise OSError(n)
 def free(self):self.hit('free');return m.ADMISSION+1
 def global_count(self):self.hit('count');return self.count
 def create_private_job(self):self.hit('job');return 'private'
 def spawn_waiting(self,cmd,job):self.hit('spawn');self.running=True;return 'inner'
 def arm_deadlines(self,i):self.hit('arm')
 def check_deadlines(self):self.hit('deadline')
 def stop_deadlines(self):self.hit('join')
 def release(self,i):self.child=True;self.hit('release')
 def evidence_bytes(self):self.hit('sample');return 0
 def find_guest(self):self.hit('find');return 'guest' if self.child else None
 def identity(self,g):self.hit('identity');return self.id.copy()
 def actual_seconds(self,g):self.hit('seconds');return self.t
 def release_inputs(self,g):self.hit('keyup')
 def inner_alive(self,i):self.hit('alive');return self.running and self.t<41
 def wait(self,i):self.running=False;self.hit('wait')
 def exit_code(self,i):return 0
 def guest_alive(self,g):return self.child and self.running
 def tick(self):self.t+=.25;self.hit('tick')
 def close_release_pipe(self,i):self.hit('pipe')
 def stop_private_job(self,j):self.child=False;self.running=False;self.hit('stop')
 def wait_guest(self,g):self.hit('guestwait')
 def close_owned_handles(self,j,i,g):self.closed=True;self.hit('close')
class Supervisor(unittest.TestCase):
 def runfake(self,f,callback=None):
  r=m.monitor(f,['not-launched'],callback);self.assertFalse(f.child);self.assertFalse(f.running);self.assertTrue(f.closed);return r
 def test_normal_and_input_release_before41(self):
  f=Fake();r=self.runfake(f);self.assertTrue(r['qualified']);self.assertEqual(r['actual_guest_seconds'],41);self.assertTrue(r['input_release_before41']);self.assertLess(f.calls.index('join'),f.calls.index('close'))
 def test_after_spawn_exception_no_orphan(self):
  f=Fake();r=self.runfake(f,lambda _:(_ for _ in ()).throw(ValueError('after spawn')));self.assertFalse(r['qualified']);self.assertIn('stop',f.calls)
 def test_sampler_and_pipe_failure_both_cleanup(self):
  f=Fake('sample');original=f.close_release_pipe
  def broken(i):f.calls.append('pipe');raise BrokenPipeError('already closed fd0')
  f.close_release_pipe=broken;r=self.runfake(f);self.assertFalse(r['qualified']);self.assertTrue(r['cleanup_errors']);self.assertIn('stop',f.calls)
 def test_every_post_spawn_fault_cleanup(self):
  for name in ['arm','release','deadline','sample','find','identity','seconds','alive','tick','keyup','pipe','join','wait','guestwait']:
   with self.subTest(name=name):
    f=Fake(name);r=self.runfake(f);self.assertFalse(r['qualified']);self.assertIn('stop',f.calls)
 def test_cleanup_wait_failure_cannot_skip_handleclose(self):
  f=Fake('guestwait');r=self.runfake(f);self.assertFalse(r['qualified']);self.assertTrue(f.closed)
 def test_evidence_cap(self):
  f=Fake();f.evidence_bytes=lambda:m.CAP;r=self.runfake(f);self.assertIn('60MB',r['error'])
 def test_runtime_floor(self):
  f=Fake();f.free=lambda:m.ADMISSION+1 if not f.child else m.RUNTIME-1;r=self.runfake(f);self.assertIn('runtime disk',r['error'])
 def test_global16_admission_and17_runtime(self):
  f=Fake();f.count=16;r=self.runfake(f);self.assertIn('admission',r['error']);self.assertNotIn('spawn',f.calls)
  f=Fake();f.global_count=lambda:17 if f.child else 15;r=self.runfake(f);self.assertIn('overflow',r['error'])
 def test_absolute_cap_independent_of_inner(self):
  f=Fake();f.inner_alive=lambda i:True;r=self.runfake(f);self.assertEqual(f.t,47.5);self.assertIn('47.5',r['error'])
 def test_changed_identity_refuses_foreign_keyups(self):
  f=Fake();old=f.identity
  def identity(g):
   v=old(g)
   if f.t>0:v['start']=999
   return v
  f.identity=identity;r=self.runfake(f);self.assertIn('identity changed',r['error']);self.assertNotIn('keyup',f.calls)
 def test_disappeared_guest_finalization_failure(self):
  f=Fake();f.actual_seconds=lambda g:(_ for _ in ()).throw(OSError('times unavailable'));r=self.runfake(f);self.assertFalse(r['qualified'])
 def test_assignment_fault_spawn_contract(self):
  f=Fake('spawn');r=self.runfake(f);self.assertFalse(r['qualified']);self.assertIn('stop',f.calls)
if __name__=='__main__':unittest.main(verbosity=2)
