"""Targeted NEW review regressions only; no old suites, emulator, RAM or native input."""
import ctypes,importlib.util,json,pathlib,struct,tempfile,threading,time,types,unittest
P=pathlib.Path(__file__).parent

def load(name,file):
 s=importlib.util.spec_from_file_location(name,P/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
o=load('repaired_observe','observe.py');b=load('repaired_backend','windows-backend.py');d=load('repaired_deadlines','input-deadlines.py');c=load('repaired_controller','controller-core.py');inner=load('repaired_inner','inner-adapter.py')
class Function:
 def __init__(self,fn):self.fn=fn
 def __call__(self,*a):return self.fn(*a)
class ObserverAfterSnapshot(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=pathlib.Path(self.tmp.name);self.obj=object.__new__(o.Observer);v=self.obj;v.cap=self.p;v.handle=99;v.start=123;v.pid=21;v.ram=0;v.last={'old':'must invalidate'};v.started=time.monotonic();v.last_log=0;v.last_key=None;v.buffer=None;self.bulk=0;self.after='live';self.timecalls=0;self.retry=False
  def times(h,*values):
   self.timecalls+=1
   values[0]._obj.value=124 if self.after=='changed' else 123;values[1]._obj.value=456 if self.after=='exited' else 0
   return 0 if self.after=='unavailable' else 1
  v.k=types.SimpleNamespace(GetProcessTimes=times)
  row=lambda:{'valid':True,'coherent':not self.retry,'global':{'frame':7,'rno':[3,0,0,0]},'player':{'ptr':0x8c200000,'rno':[0,0,0,0]}}
  v.adapter=types.SimpleNamespace(sy={'_pG':1,'_pPL':2},off=lambda *a:4,snapshot=row,actor_chain=lambda:{'actors':[]});v.layout={'found':{'GlobalWork':{'bytes':100}}};self.pplreads=0
  def read(addr,n):
   if n==16*1024**2:self.bulk+=1;return b'fixture bulk placeholder'
   if addr==1:return struct.pack('<I',0x8c100000)
   if addr==2:
    self.pplreads+=1
    if self.pplreads==self.trigger:self.after=self.failure
    return struct.pack('<I',0x8c200000)
   return struct.pack('<I',7)
  v.live_read=read;self.trigger=999;self.failure='live'
 def tearDown(self):self.tmp.cleanup()
 def test_exit_during_last_read_rejected_before_publish(self):
  self.trigger=2;self.failure='exited'
  with self.assertRaises(EOFError):self.obj.sample()
  self.assertIsNone(self.obj.last);self.assertFalse((self.p/'latest-state.json').exists())
 def test_start_change_after_bulk_rejected(self):
  self.trigger=2;self.failure='changed'
  with self.assertRaises(EOFError):self.obj.sample()
  self.assertIsNone(self.obj.last)
 def test_post_identity_unavailable_rejected(self):
  self.trigger=2;self.failure='unavailable'
  with self.assertRaises(EOFError):self.obj.sample()
  self.assertIsNone(self.obj.last)
 def test_exit_during_retry_stops_before_another_attempt(self):
  self.retry=True;self.trigger=4;self.failure='exited'
  with self.assertRaises(EOFError):self.obj.sample()
  self.assertEqual(self.bulk,2);self.assertIsNone(self.obj.last)
 def test_live_postcheck_allows_publish(self):
  self.obj.sample();self.assertTrue(self.obj.last['coherent']);self.assertGreaterEqual(self.timecalls,3);self.assertTrue((self.p/'latest-state.json').exists())
class KeyupDelivery(unittest.TestCase):
 def backend(self,enum_ok=True,windows=(100,),post_ok=True,recycle=False):
  v=object.__new__(b.WindowsBackend);v.input_released=True;guest={'pid':21,'identity':{'pid':21,'start_filetime':123,'path':'own'}};v.identity=lambda _:guest['identity'];v.guest_alive=lambda _:True;self.posts=[];self.lookups=0
  def pid(hwnd,pointer):
   self.lookups+=1;pointer._obj.value=22 if recycle and self.lookups>len(windows) else 21;return 1
  def enum(callback,_):
   for hwnd in windows:callback(hwnd,0)
   return int(enum_ok)
  def post(*a):self.posts.append(a);return int(post_ok)
  v.u=types.SimpleNamespace(EnumWindows=Function(enum),GetWindowThreadProcessId=Function(pid),PostMessageW=Function(post));return v,guest
 def test_enum_failure_never_sets_released(self):
  v,g=self.backend(enum_ok=False)
  with self.assertRaisesRegex(RuntimeError,'EnumWindows'):v.release_inputs(g)
  self.assertFalse(v.input_released);self.assertFalse(self.posts)
 def test_no_owned_live_window_never_sets_released(self):
  v,g=self.backend(windows=())
  with self.assertRaisesRegex(RuntimeError,'no exact owned'):v.release_inputs(g)
  self.assertFalse(v.input_released)
 def test_failed_required_post_keeps_release_unproved(self):
  v,g=self.backend(post_ok=False)
  with self.assertRaisesRegex(RuntimeError,'WM_KEYUP'):v.release_inputs(g)
  self.assertFalse(v.input_released)
 def test_recycled_hwnd_receives_no_post(self):
  v,g=self.backend(recycle=True)
  with self.assertRaisesRegex(RuntimeError,'HWND changed'):v.release_inputs(g)
  self.assertFalse(v.input_released);self.assertFalse(self.posts)
 def test_success_records_all_queued_keyups_only(self):
  v,g=self.backend();v.release_inputs(g);self.assertTrue(v.input_released);self.assertEqual(len(self.posts),9);self.assertEqual(v.input_release_receipt['queued_keyups'],9)
class FakeTimer:
 def __init__(self,delay,callback):self.delay=delay;self.callback=callback;self.cancelled=False
 def start(self):pass
 def cancel(self):self.cancelled=True
 def join(self,timeout=None):pass
 def is_alive(self):return False
class CaptureAndPulse(unittest.TestCase):
 def setUp(self):self.now=0;self.posts=[];self.failures=[];self.inputs=d.Inputs(lambda k,u:self.posts.append((k,u,self.now)),lambda:self.now,self.failures.append,clock=lambda:self.now,timer=FakeTimer)
 def tearDown(self):self.inputs.close()
 def test_capture_releases_and_syncs_before_blocking_work(self):
  self.inputs.down('a',.15);order=[]
  def sync(forced):order.append('sync');self.assertTrue(forced);self.assertEqual(self.inputs.keys(),set())
  def capture():order.append('capture');self.assertEqual(self.posts[-1][0:2],('a',True))
  d.release_before_capture(self.inputs,sync,capture);self.assertEqual(order,['sync','capture'])
 def test_failed_release_prevents_screenshot(self):
  self.inputs.down('a',.15);original=self.inputs.post
  def post(k,u):
   if u:raise RuntimeError('injected required keyup failed')
   original(k,u)
  self.inputs.post=post
  with self.assertRaises(RuntimeError):d.release_before_capture(self.inputs,lambda _:None,lambda:self.fail('capture must not start'))
  self.inputs.post=original
 def test_capture_before_shot_anchors_aim_at_actual_post(self):
  e=c.Shooting();e.stage='aim';e.held={'rtrig'};e.until=.4
  d.release_before_capture(self.inputs,lambda forced:c.released_events(e,'cold-shoot01',self.inputs.keys(),self.inputs.drain(),forced),lambda:None)
  self.assertFalse(e.done);self.assertEqual(e.held,set());fresh={'actual':'post capture sample'};c.actual_posted(e,'cold-shoot01','rtrig',3,fresh);self.assertIs(e.baseline,fresh);self.assertEqual(e.until,3.4);self.assertEqual(e.held,{'rtrig'})
 def test_forced_capture_release_interrupts_started_shot(self):
  e=c.Shooting();e.stage='fire';e.held={'rtrig','a'};self.inputs.down('rtrig',1.5);self.inputs.down('a',.15)
  d.release_before_capture(self.inputs,lambda forced:c.released_events(e,'cold-shoot01',self.inputs.keys(),self.inputs.drain(),forced),lambda:None);self.assertTrue(e.done);self.assertEqual(e.stage,'interrupted');self.assertEqual(e.held,set())
 def test_deadline_reconciles_A_settle_and_B_spacing(self):
  e=c.Shooting();e.stage='fire';e.held={'a','rtrig'};c.released_events(e,'cold-shoot01',{'rtrig'},[{'key':'a','reason':'deadline','elapsed':2}],False);self.assertEqual(e.stage,'settle');self.assertEqual(e.until,2.65)
  e=c.Cinematic();e.held={'b'};c.released_events(e,'cinematic01',set(),[{'key':'b','reason':'deadline','elapsed':2}],False);self.assertEqual(e.last_b,2);self.assertEqual(e.held,set())
 def test_manual_early_release_preserves_B_spacing(self):
  e=c.Cinematic();e.last_b=-100;c.released_events(e,'cinematic01',set(),[{'key':'b','reason':'engine-up','elapsed':2}],False);self.assertEqual(e.last_b,2)
 def test_timer_releases_while_observer_lock_is_held(self):
  released=threading.Event();fail=[];inputs=d.Inputs(lambda k,u:released.set() if u else None,time.monotonic,fail.append);observer_lock=threading.Lock()
  try:
   with observer_lock:
    inputs.down('a',.15);self.assertTrue(released.wait(.3));self.assertFalse(inputs.keys())
   self.assertFalse(fail)
  finally:inputs.close()
 def test_late_native_queue_is_disqualified(self):
  self.inputs.down('a',.15);self.now=.16;token=self.inputs.held['a'];self.inputs.expire('a',token);self.assertTrue(self.failures);self.assertFalse(self.inputs.keys())
 def test_conservative_cutoff_marker_blocks_later_down(self):
  with tempfile.TemporaryDirectory() as tmp:
   v=object.__new__(b.WindowsBackend);v.cap=pathlib.Path(tmp);v.disable_inputs('origin40.75 while guest39.9');self.assertTrue((v.cap/'inputs-disabled.json').exists())
   self.assertFalse(inner.input_allowed(tmp,False,39.9));self.assertFalse(inner.input_allowed(tmp,False,40.2))
  with tempfile.TemporaryDirectory() as tmp:
   self.assertTrue(inner.input_allowed(tmp,False,40.74));self.assertFalse(inner.input_allowed(tmp,False,40.75));self.assertFalse(inner.input_allowed(tmp,True,39))
 def test_input_failure_marker_forces_outer_qualification_abort(self):
  with tempfile.TemporaryDirectory() as tmp:
   v=object.__new__(b.WindowsBackend);v.cap=pathlib.Path(tmp);v.deadline_failure=None;(v.cap/'input-failure.json').write_text('{}')
   with self.assertRaisesRegex(RuntimeError,'input guard failed'):v.check_deadlines()
 def test_hard_deadline_remains_runnable_while_marker_IO_blocks(self):
  v=object.__new__(b.WindowsBackend);origin=time.monotonic();v.clock=lambda:(time.monotonic()-origin)*100;v.job=123;v.guest={'anchor':0};v.deadline_stop=threading.Event();v.deadline_thread=None;v.cutoff_thread=None;v.deadline_failure=None;entered=threading.Event();unblock=threading.Event();terminated=threading.Event();queued=threading.Event()
  def marker(reason):entered.set();unblock.wait(2)
  v.disable_inputs=marker;v.release_inputs=lambda _:queued.set();v.checked=lambda value:value;v.k=types.SimpleNamespace(TerminateJobObject=lambda job,code:terminated.set() or 1)
  try:
   v.arm_deadlines(None);self.assertTrue(entered.wait(.8));self.assertFalse(unblock.is_set());self.assertTrue(terminated.wait(.2));self.assertFalse(queued.is_set());self.assertIn('47.0s',v.deadline_failure)
  finally:
   unblock.set()
   with self.assertRaisesRegex(RuntimeError,'late deadline/cutoff failure'):v.stop_deadlines()
  self.assertFalse(v.deadline_thread.is_alive());self.assertFalse(v.cutoff_thread.is_alive())
 def test_exception_cleanup_stops_job_before_disarming_hard_deadline(self):
  core=load('repaired_supervisor','guest-supervisor-core.py');order=[]
  backend=types.SimpleNamespace(free=lambda:core.ADMISSION+1,global_count=lambda:0,create_private_job=lambda:'ownjob',spawn_waiting=lambda *a:'inner',stop_private_job=lambda _:order.append('stop-job'),stop_deadlines=lambda:order.append('disarm'),close_release_pipe=lambda _:order.append('pipe'),wait=lambda _:order.append('wait'),wait_private_job_empty=lambda _:order.append('empty'),close_owned_handles=lambda *a:order.append('close'))
  result=core.monitor(backend,[],lambda _:(_ for _ in ()).throw(RuntimeError('injected afterspawn')));self.assertFalse(result['qualified']);self.assertLess(order.index('stop-job'),order.index('disarm'));self.assertLess(order.index('stop-job'),order.index('pipe'));self.assertIn('empty',order)
 def test_unproved_job_empty_does_not_disarm_last_hard_guard(self):
  core=load('retained_hardguard_supervisor','guest-supervisor-core.py');order=[]
  def empty(_):raise RuntimeError('empty unavailable')
  backend=types.SimpleNamespace(free=lambda:core.ADMISSION+1,global_count=lambda:0,create_private_job=lambda:'ownjob',spawn_waiting=lambda *a:'inner',stop_private_job=lambda _:order.append('stop-job'),stop_deadlines=lambda:order.append('disarm'),close_release_pipe=lambda _:None,wait=lambda _:None,wait_private_job_empty=empty,close_owned_handles=lambda *a:order.append('close'))
  result=core.monitor(backend,[],lambda _:(_ for _ in ()).throw(RuntimeError('injected afterspawn')));self.assertFalse(result['qualified']);self.assertNotIn('disarm',order);self.assertIn('hard_deadline_retained',result)
 def test_late_cutoff_failure_cannot_be_lost_after_last_monitor_check(self):
  v=object.__new__(b.WindowsBackend);v.deadline_stop=threading.Event();v.deadline_thread=None;v.cutoff_thread=None;v.deadline_failure='injected cutoff error after final loop check'
  with self.assertRaisesRegex(RuntimeError,'late deadline/cutoff failure'):v.stop_deadlines()
 def test_final_capture_disables_newdowns_before_work(self):
  source=(P/'inner-adapter.py').read_text();self.assertIn("input_disabled=True;capture('final')",source);self.assertIn('if input_disabled:continue',source)
if __name__=='__main__':unittest.main(verbosity=2)
