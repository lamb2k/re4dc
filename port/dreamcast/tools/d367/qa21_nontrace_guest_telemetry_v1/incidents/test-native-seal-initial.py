"""Three bounded tiny Python host-child tests only; no emulator/RAM/input/image."""
import ctypes,importlib.util,os,pathlib,shutil,sys,tempfile,time,unittest
P=pathlib.Path(__file__).parent
def load(name,n):
 spec=importlib.util.spec_from_file_location(name,P/n);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
b=load('native_seal_backend','windows-backend.py');c=load('native_seal_core','guest-supervisor-core.py')
class Footprint:
 @staticmethod
 def measure(folder,disc):return {'charged_bytes':sum(p.stat().st_size for p in pathlib.Path(folder).rglob('*') if p.is_file())}
class Dummy(b.WindowsBackend):
 # No native input API is used. The only child is the retained Python interpreter.
 def release_inputs(self,g):
  if self.identity(g)!=g['identity']:raise RuntimeError('dummy retained identity changed')
  self.input_released=True
 def find_guest(self):
  if self.guest is not None:return self.guest
  h=self.checked(self.k.OpenProcess(0x101001,False,self.inner.pid))
  try:
   info=self.info(self.inner.pid,h)
   if info!=self.inner_identity:raise RuntimeError('dummy birth differs from retained spawned inner')
   member=ctypes.c_int();self.checked(self.k.IsProcessInJob(h,self.job,ctypes.byref(member)))
   if not member.value:raise RuntimeError('dummy outside private job')
   self.guest={'pid':self.inner.pid,'handle':h,'identity':info,'anchor':self.clock()};return self.guest
  except BaseException:self.k.CloseHandle(h);raise
 def tick(self):time.sleep(.005)
class Native(unittest.TestCase):
 def setUp(self):
  self.assertGreaterEqual(shutil.disk_usage('C:/').free,c.RUNTIME+4*1024**2);self.tmp=tempfile.TemporaryDirectory(prefix='qa21-telemetry-native-');self.p=pathlib.Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def backend(self):return Dummy(self.p,self.p,self.p,'no-emulator',Footprint)
 def test_actual_birth_retained_exit_final_resources_and_closed_job(self):
  v=self.backend();saved=[];cmd=[sys.executable,'-c','import sys,time;sys.stdin.buffer.readline();time.sleep(.08)'];r=c.monitor(v,cmd,lambda child:saved.append(child));self.assertTrue(r['qualified'],r);t=r['process_telemetry'];self.assertTrue(t['available']);self.assertEqual(t['identity']['pid'],saved[0].pid);self.assertGreater(t['creation_filetime'],0);self.assertGreater(t['exit_filetime'],t['creation_filetime']);self.assertEqual(t['actual_guest_seconds'],(t['exit_filetime']-t['creation_filetime'])/1e7);self.assertLess(t['actual_guest_seconds'],5);self.assertTrue(r['final_resources']['available']);self.assertIsNone(v.job);self.assertFalse(v.deadline_thread.is_alive());self.assertIsNotNone(saved[0].returncode)
 def test_exception_after_birth_reaps_descendant_and_retains_numeric_exit(self):
  v=self.backend();grand=[];ready=self.p/'reader-pid';release=v.release
  def released(proc):
   release(proc);end=time.monotonic()+2
   while not ready.exists():
    if time.monotonic()>end:raise RuntimeError('tiny child readiness deadline')
    time.sleep(.005)
   pid=int(ready.read_text());h=v.checked(v.k.OpenProcess(0x101001,False,pid));info=v.info(pid,h);member=ctypes.c_int();v.checked(v.k.IsProcessInJob(h,v.job,ctypes.byref(member)))
   if not member.value:v.k.CloseHandle(h);raise RuntimeError('tiny descendant outside private job')
   grand.append((h,info))
  v.release=released
  def fault():raise RuntimeError('injected after verified birth')
  v.tick=fault
  code="import pathlib,subprocess,sys,time;sys.stdin.buffer.readline();p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);pathlib.Path("+repr(str(ready))+").write_text(str(p.pid));time.sleep(30)"
  try:
   r=c.monitor(v,[sys.executable,'-c',code]);self.assertFalse(r['qualified']);self.assertIn('after verified birth',r['error']);self.assertTrue(r['process_telemetry']['available']);self.assertGreater(r['process_telemetry']['exit_filetime'],r['process_telemetry']['creation_filetime']);self.assertEqual(len(grand),1);self.assertEqual(v.k.WaitForSingleObject(grand[0][0],0),0);self.assertGreater(v.times(grand[0][0])[1],0);self.assertIsNone(v.job);self.assertFalse(v.deadline_thread.is_alive())
  finally:
   for h,_ in grand:v.k.CloseHandle(h)
 def test_closed_fd0_release_failure_still_waits_and_closes_owned_job(self):
  v=self.backend();saved=[];ready=self.p/'closed-ready';code="import os,pathlib,time;os.close(0);pathlib.Path("+repr(str(ready))+").write_text('ready');time.sleep(30)"
  def after_spawn(proc):
   saved.append(proc);end=time.monotonic()+2
   while not ready.exists():
    if time.monotonic()>end:raise RuntimeError('closed fd0 readiness deadline')
    time.sleep(.005)
  r=c.monitor(v,[sys.executable,'-c',code],after_spawn);self.assertFalse(r['qualified']);self.assertTrue('BrokenPipe' in r['error'] or 'OSError' in r['error']);self.assertIsNotNone(saved[0].returncode);self.assertIsNone(v.job);self.assertFalse(v.deadline_thread.is_alive());self.assertFalse(r['process_telemetry']['available']);self.assertTrue(r['final_resources']['available'])
if __name__=='__main__':
 if os.name!='nt':raise SystemExit('Windows only; never emulator')
 unittest.main(verbosity=2)
