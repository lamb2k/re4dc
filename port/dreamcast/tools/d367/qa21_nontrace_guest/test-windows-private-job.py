"""Small Python children only, no Flycast, RAM or input. Windows containment tests."""
import ctypes,importlib.util,json,os,pathlib,subprocess,sys,tempfile,time,unittest
P=pathlib.Path(__file__).parent
s=importlib.util.spec_from_file_location('backend',P/'windows-backend.py');b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
s=importlib.util.spec_from_file_location('supervisor',P/'guest-supervisor-core.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
class Footprint:
 @staticmethod
 def measure(*args):return {'charged_bytes':0}
class Dummy(b.WindowsBackend):
 def global_count(self):return 0 # no emulator exists in this test fixture
 def free(self):return c.ADMISSION+1 # mocked disk; these children create <1KiB
 def tick(self):time.sleep(.01)
 def evidence_bytes(self):
  if getattr(self,'sample_fault',False):raise RuntimeError('injected sampler')
  return 0
 def release_inputs(self,g):
  if self.identity(g)!=g['identity']:raise RuntimeError('dummy identity changed')
  self.input_released=True # no native key posts in this test
 def find_guest(self):
  if self.guest is not None:return self.guest
  h=self.checked(self.k.OpenProcess(0x101001,False,self.inner.pid));info=self.info(self.inner.pid,h)
  self.guest={'pid':self.inner.pid,'handle':h,'identity':info,'anchor':self.clock()};return self.guest
 def release(self,i):
  super().release(i)
  if getattr(self,'sampler_after_release',False):self.sample_fault=True
class Kernel(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory(prefix='qa21-dummy-');self.p=pathlib.Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def backend(self,clock=time.monotonic):return Dummy(self.p,self.p,self.p,'unused-no-emulator',Footprint,clock)
 def child(self,close0=False):
  ready=str(self.p/'ready')
  code=('import os,pathlib,sys,time; '+("os.close(0); " if close0 else "sys.stdin.buffer.readline(); ")+f"pathlib.Path({ready!r}).write_text('ready'); time.sleep(30)")
  return [sys.executable,'-c',code]
 def ready(self):
  limit=time.monotonic()+2
  while not (self.p/'ready').exists():
   if time.monotonic()>limit:raise RuntimeError('dummy readiness deadline')
   time.sleep(.005)
 def test_closed_stdin_release_and_close_failure_still_reaps(self):
  backend=self.backend();saved=[]
  def cb(proc):saved.append(proc);self.ready()
  result=c.monitor(backend,self.child(True),cb)
  self.assertFalse(result['qualified']);self.assertTrue('OSError' in result['error'] or 'BrokenPipeError' in result['error']);self.assertTrue(any('pipe close' in e for e in result.get('cleanup_errors',[])));self.assertIsNotNone(saved[0].returncode);self.assertIsNone(backend.job)
 def test_after_spawn_exception_reaps_private_child(self):
  backend=self.backend();saved=[]
  def cb(proc):saved.append(proc);raise ValueError('injected after spawn')
  result=c.monitor(backend,self.child(),cb);self.assertFalse(result['qualified']);self.assertIsNotNone(saved[0].returncode);self.assertIsNone(backend.job)
 def test_sampler_exception_reaps_after_release(self):
  backend=self.backend();backend.sampler_after_release=True;saved=[];result=c.monitor(backend,self.child(),lambda p:saved.append(p));self.assertFalse(result['qualified']);self.assertIsNotNone(saved[0].returncode);self.assertIsNone(backend.job)
 def test_independent_watchdog_terminates_private_job(self):
  origin=time.monotonic();backend=self.backend(lambda:(time.monotonic()-origin)*100);saved=[];backend.tick=lambda:time.sleep(.65)
  result=c.monitor(backend,self.child(),lambda p:saved.append(p));self.assertFalse(result['qualified']);self.assertIn('47.0s',result['error']);self.assertIsNotNone(saved[0].returncode);self.assertFalse(backend.deadline_thread.is_alive());self.assertIsNone(backend.job)
 def test_normal_exit_retained_handle_times_no_query_race(self):
  backend=self.backend();saved=[];cmd=[sys.executable,'-c','import sys,time;sys.stdin.buffer.readline();time.sleep(.08)']
  result=c.monitor(backend,cmd,lambda p:saved.append(p));self.assertTrue(result['qualified'],result);self.assertLess(result['actual_guest_seconds'],2);self.assertIsNotNone(saved[0].returncode);self.assertIsNone(backend.job)
 def test_inherited_reader_child_job_is_empty_before_close(self):
  backend=self.backend();saved=[];grand=[];ready=self.p/'grandchild';release=backend.release
  def released(proc):
   release(proc);limit=time.monotonic()+2
   while not ready.exists():
    if time.monotonic()>limit:raise RuntimeError('reader child readiness deadline')
    time.sleep(.005)
   pid=int(ready.read_text());h=backend.checked(backend.k.OpenProcess(0x101001,False,pid));info=backend.info(pid,h);member=ctypes.c_int();backend.checked(backend.k.IsProcessInJob(h,backend.job,ctypes.byref(member)))
   if not member.value:raise RuntimeError('reader child escaped private job')
   grand.append((h,info));backend.sample_fault=True
  backend.release=released
  code="import pathlib,subprocess,sys,time;sys.stdin.buffer.readline();p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);pathlib.Path("+repr(str(ready))+").write_text(str(p.pid));time.sleep(30)"
  try:
   result=c.monitor(backend,[sys.executable,'-c',code],lambda p:saved.append(p));self.assertFalse(result['qualified']);self.assertEqual(len(grand),1);self.assertIsNotNone(saved[0].returncode);self.assertIsNone(backend.job)
   self.assertEqual(backend.k.WaitForSingleObject(grand[0][0],0),0);self.assertGreater(backend.times(grand[0][0])[1],0)
  finally:
   for h,_ in grand:backend.k.CloseHandle(h)
if __name__=='__main__':
 if os.name!='nt':raise SystemExit('Windows only; no emulator is invoked')
 unittest.main(verbosity=2)
