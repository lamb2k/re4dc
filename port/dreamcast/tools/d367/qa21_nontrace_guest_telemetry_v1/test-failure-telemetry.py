"""New exception-telemetry tests only; fake clock/handles/jobs, no guest/input/RAM."""
import importlib.util,json,pathlib,tempfile,types,unittest
P=pathlib.Path(__file__).parent
def load(name,file):
 spec=importlib.util.spec_from_file_location(name,P/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
d=load('telemetry_deadlines','input-deadlines.py');i=load('telemetry_inner','inner-adapter.py');c=load('telemetry_core','guest-supervisor-core.py');b=load('telemetry_backend','windows-backend.py')
class Timer:
 def __init__(self,delay,fn):self.delay=delay
 def start(self):pass
 def cancel(self):pass
 def join(self,timeout=None):pass
 def is_alive(self):return False
class Pulse(unittest.TestCase):
 def setUp(self):self.now=10.;self.errors=[];self.receipt={'queued':True,'messages':[{'before_monotonic':10.16,'after_monotonic':10.161,'post_succeeded':True}]};self.input=d.Inputs(lambda k,u:self.receipt,lambda:self.now,self.errors.append,clock=lambda:self.now,timer=Timer)
 def tearDown(self):self.input.post=lambda *a:self.receipt;self.input.elapsed=lambda:self.now;self.now=10.;self.input.close()
 def late(self):self.input.down('a',.15);self.now=10.17;self.input.expire('a',self.input.held['a']);return self.errors[0]
 def test_late_numeric_receipt_preserves_existing_failure(self):
  e=self.late();p=e.pulse_telemetry;self.assertIn('after declared pulse bound',str(e));self.assertEqual(p['lease_start_monotonic'],10.);self.assertEqual(p['deadline_monotonic'],10.15);self.assertEqual(p['bound_seconds'],.15);self.assertEqual(p['keyup_attempt_monotonic'],10.17);self.assertEqual(p['keyup_return_monotonic'],10.17);self.assertAlmostEqual(p['queue_hold_upper_seconds'],.17);self.assertEqual(p['native_keyup'],self.receipt);self.assertTrue(p['keyup_queued']);self.assertFalse(self.input.keys())
 def test_native_queue_exception_preserves_partial_receipt_and_null_return(self):
  self.input.down('a',.15);partial={'queued':False,'messages':[{'post_succeeded':True}]}
  def failed(*a):
   e=RuntimeError('second owned window refused');e.native_queue_telemetry=partial;raise e
  self.input.post=failed;self.input.expire('a',self.input.held['a']);p=self.errors[0].pulse_telemetry;self.assertEqual(p['native_keyup'],partial);self.assertIsNone(p['keyup_return_monotonic']);self.assertIsNone(p['queue_hold_upper_seconds']);self.assertIsNone(p['keyup_queued']);self.assertEqual(self.input.keys(),{'a'})
 def test_exited_noop_is_not_recorded_as_successful_keyup(self):
  self.receipt={'queued':False,'messages':[],'reason':'already exited'};self.input.down('a',.15);self.now=10.01;self.input.up('a');self.assertFalse(self.input.drain()[0]['pulse_telemetry']['keyup_queued']);self.assertFalse(self.errors)
 def test_no_telemetry_callback_is_explicit_unavailable(self):
  self.receipt=None;self.input.down('a',.15);self.now=10.01;self.input.up('a');p=self.input.drain()[0]['pulse_telemetry'];self.assertIsNone(p['native_keyup']);self.assertIsNone(p['keyup_queued'])
 def test_atomic_marker_preserves_complete_numeric_failure(self):
  e=self.late()
  with tempfile.TemporaryDirectory() as tmp:
   i.publish_input_failure(tmp,e);p=pathlib.Path(tmp);j=json.loads((p/'input-failure.json').read_text());self.assertEqual(j['pulse_telemetry'],e.pulse_telemetry);self.assertFalse((p/'input-failure.pending').exists());self.assertIn('failed qualification',j['scope'])
 def test_first_failure_is_not_replaced(self):
  with tempfile.TemporaryDirectory() as tmp:
   i.publish_input_failure(tmp,RuntimeError('first'));i.publish_input_failure(tmp,self.late());j=json.loads((pathlib.Path(tmp)/'input-failure.json').read_text());self.assertEqual(j['error'],'first');self.assertIsNone(j['pulse_telemetry'])
 def test_serialization_failure_never_publishes_partial_final_marker(self):
  original=i.json.dump
  def failed(payload,f):f.write('{');raise OSError('injected write failure')
  try:
   i.json.dump=failed
   with tempfile.TemporaryDirectory() as tmp:
    with self.assertRaises(OSError):i.publish_input_failure(tmp,RuntimeError('bad'))
    self.assertFalse((pathlib.Path(tmp)/'input-failure.json').exists());self.assertTrue((pathlib.Path(tmp)/'input-failure.pending').exists())
  finally:i.json.dump=original
 def test_engine_up_queue_exception_publishes_before_controller_stringification(self):
  with tempfile.TemporaryDirectory() as tmp:
   self.input.fail=lambda e:i.publish_input_failure(tmp,e);self.input.down('a',.15)
   def failed(*a):raise RuntimeError('direct engine keyup failed')
   self.input.post=failed
   with self.assertRaisesRegex(RuntimeError,'direct engine'):self.input.up('a')
   j=json.loads((pathlib.Path(tmp)/'input-failure.json').read_text());self.assertEqual(j['pulse_telemetry']['reason'],'engine-up');self.assertEqual(j['pulse_telemetry']['deadline_monotonic'],10.15);self.assertIsNone(j['pulse_telemetry']['keyup_return_monotonic'])
 def test_release_all_queue_exception_publishes_before_aggregate_loses_attributes(self):
  with tempfile.TemporaryDirectory() as tmp:
   self.input.fail=lambda e:i.publish_input_failure(tmp,e);self.input.down('a',.15)
   def failed(*a):raise RuntimeError('normal release queue failed')
   self.input.post=failed
   with self.assertRaises(RuntimeError) as caught:self.input.release_all('normal-release')
   self.assertFalse(hasattr(caught.exception,'pulse_telemetry'));j=json.loads((pathlib.Path(tmp)/'input-failure.json').read_text());self.assertEqual(j['pulse_telemetry']['reason'],'normal-release');self.assertEqual(j['pulse_telemetry']['bound_seconds'],.15)
 def test_engine_up_elapsed_exception_preserves_successful_native_queue(self):
  with tempfile.TemporaryDirectory() as tmp:
   self.input.fail=lambda e:i.publish_input_failure(tmp,e);self.input.down('a',.15)
   def failed():raise RuntimeError('guest elapsed unavailable after native queue')
   self.input.elapsed=failed
   with self.assertRaisesRegex(RuntimeError,'elapsed unavailable'):self.input.up('a')
   j=json.loads((pathlib.Path(tmp)/'input-failure.json').read_text());self.assertTrue(j['pulse_telemetry']['keyup_queued']);self.assertEqual(j['pulse_telemetry']['keyup_return_monotonic'],10.);self.assertEqual(j['pulse_telemetry']['native_keyup'],self.receipt)
class ExitBackend(unittest.TestCase):
 def make(self,created=100000000,exited=425000000,signaled=0):
  v=object.__new__(b.WindowsBackend);ident={'pid':7,'start_filetime':100000000,'path':'owned/live/pinned.exe'};v.guest={'handle':99,'identity':ident,'pid':7};v.identity=lambda _:ident.copy();v.times=lambda _:[created,exited,22,33];v.checked=lambda x:x
  def code(h,p):p._obj.value=125;return 1
  v.k=types.SimpleNamespace(WaitForSingleObject=lambda *a:signaled,GetExitCodeProcess=code);return v
 def test_retained_exited_handle_has_exact_raw_times_duration_identity(self):
  v=self.make();r=v.final_process_telemetry();self.assertTrue(r['available']);self.assertEqual(r['actual_guest_seconds'],32.5);self.assertEqual(r['creation_filetime'],100000000);self.assertEqual(r['exit_filetime'],425000000);self.assertEqual(r['identity'],v.guest['identity']);self.assertEqual(r['exit_code'],125)
 def test_start_mismatch_refuses_recycled_identity(self):
  with self.assertRaisesRegex(RuntimeError,'start changed'):self.make(created=100000001).final_process_telemetry()
 def test_unfinalized_exit_has_no_invented_duration(self):
  for exit,signal in [(0,0),(425000000,258),(90000000,0)]:
   with self.subTest(exit=exit,signal=signal):
    with self.assertRaisesRegex(RuntimeError,'exit unavailable'):self.make(exited=exit,signaled=signal).final_process_telemetry()
 def test_no_retained_guest_is_explicit_unavailable(self):
  v=self.make();v.guest=None;self.assertFalse(v.final_process_telemetry()['available'])
class FailureCleanup(unittest.TestCase):
 def fake(self,telemetry_error=False):
  self.order=[];v=types.SimpleNamespace();v.guest={'pid':7};identity={'pid':7,'start_filetime':100000000,'path':'owned/live/pinned.exe'}
  v.free=lambda:c.ADMISSION+1;v.global_count=lambda:0;v.create_private_job=lambda:'job';v.spawn_waiting=lambda *a:'inner';v.arm_deadlines=lambda _:None;v.release=lambda _:None;v.check_deadlines=lambda:None;v.evidence_bytes=lambda:10;v.find_guest=lambda:v.guest;v.identity=lambda _:identity;v.actual_seconds=lambda _:1.;v.inner_alive=lambda _:True
  def tick():raise RuntimeError('injected after guest discovery')
  v.tick=tick;v.stop_private_job=lambda _:self.order.append('stop');v.close_release_pipe=lambda _:None;v.release_inputs=lambda _:None;v.wait=lambda _:self.order.append('innerwait');v.wait_guest=lambda _:self.order.append('guestwait');v.wait_private_job_empty=lambda _:self.order.append('empty');v.stop_deadlines=lambda:self.order.append('disarm');v.close_owned_handles=lambda *a:self.order.append('close')
  def telemetry():
   self.order.append('telemetry')
   if telemetry_error:raise RuntimeError('retained times unavailable')
   return {'available':True,'identity':identity,'creation_filetime':100000000,'exit_filetime':425000000,'actual_guest_seconds':32.5}
  v.final_process_telemetry=telemetry;return v
 def test_exception_keeps_false_original_error_and_exact_exit_before_close(self):
  r=c.monitor(self.fake(),[]);self.assertFalse(r['qualified']);self.assertIn('injected after guest',r['error']);self.assertEqual(r['actual_guest_seconds'],32.5);self.assertEqual(r['identity']['pid'],7);self.assertLess(self.order.index('guestwait'),self.order.index('telemetry'));self.assertLess(self.order.index('telemetry'),self.order.index('close'));self.assertLess(self.order.index('empty'),self.order.index('disarm'))
 def test_telemetry_exception_cannot_skip_privatejob_cleanup(self):
  r=c.monitor(self.fake(True),[]);self.assertFalse(r['qualified']);self.assertIn('injected after guest',r['error']);self.assertTrue(any('retained exit telemetry' in e for e in r['cleanup_errors']));self.assertEqual(self.order[-1],'close');self.assertIn('stop',self.order);self.assertIn('empty',self.order);self.assertFalse(r['process_telemetry']['available']);self.assertIn('retained times unavailable',r['process_telemetry']['reason'])
if __name__=='__main__':unittest.main(verbosity=2)
