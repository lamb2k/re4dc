import copy,ctypes,io,json,os,struct,subprocess,sys,tempfile,time,types,unittest
from pathlib import Path
from unittest.mock import patch
from observer import Invalid,Process
from observer69f import Coverage,Jsonl,Process04,collect_one,load_contract,observe
from phase_latch69f05 import StableReads
from fixture69f import Fixture

PLAN=os.environ.get('RE4_RUNTIME69F_PLAN')
class PureTests(unittest.TestCase):
 def test_retained_exit_race_and_real_query_error(self):
  for query in ([123],Invalid('times failed')):
   p=object.__new__(Process04);p.sync_h=44;p.start=123;p.guest_exit_verified=False;p.guest_exit_code=None;waits=iter((258,0))
   def code(h,out):self.assertEqual(h,44);out._obj.value=7;return True
   p.k=types.SimpleNamespace(WaitForSingleObject=lambda h,t:next(waits),GetExitCodeProcess=code)
   kwargs={'side_effect':query}if isinstance(query,Exception)else{'return_value':query}
   with patch.object(Process,'times',**kwargs):self.assertFalse(p.live())
   self.assertTrue(p.guest_exit_verified);self.assertEqual(p.guest_exit_code,7)
  p.k.WaitForSingleObject=lambda h,t:258
  with patch.object(Process,'times',side_effect=Invalid('identity query failed')),self.assertRaisesRegex(Invalid,'identity query failed'):p.live()
  with patch.object(Process,'times',return_value=[123]):self.assertTrue(p.live())
 def test_body_changes_rejected(self):
  seq=iter([b'abcd',b'efgh']);r=StableReads(lambda a,n:next(seq));r(0x8c100000,4)
  with self.assertRaisesRegex(Invalid,'verification'):r.verify()
 def test_same_range_changes_on_firstpass_rejected(self):
  seq=iter([b'abcd',b'efgh']);r=StableReads(lambda a,n:next(seq));r(0x8c100000,4)
  with self.assertRaisesRegex(Invalid,'first pass'):r(0x8c100000,4)
 def test_coverage_keeps_conflicts(self):
  c=Coverage(10,11);r={'scene':{'source_tick':10,'pose':[1]},'phase':{},'cpu_us':2};self.assertTrue(c.accept(r));self.assertFalse(c.accept(r));r=copy.deepcopy(r);r['scene']['pose']=[2];self.assertTrue(c.accept(r));s=c.summary();self.assertEqual(s['conflicting_frames'],[10]);self.assertEqual(s['target_missing_frames'],[11]);self.assertFalse(s['coverage_pass'])
 def test_output_cap_preserves_whole_rows(self):
  stream=io.BytesIO();j=Jsonl(stream,20);j.emit({'a':1})
  with self.assertRaisesRegex(Invalid,'budget'):j.emit({'long':'x'*40})
  self.assertEqual(j.rows,1);self.assertEqual(len(stream.getvalue()),j.bytes)
 def test_budget_stop_cannot_pass_coverage(self):
  c=Coverage(10,10);c.accept({'scene':{'source_tick':10},'phase':{},'cpu_us':2});self.assertTrue(c.summary()['coverage_pass']);c.reject('observer output budget reached');self.assertFalse(c.summary()['coverage_pass']);self.assertFalse(c.summary()['raw_output_complete'])
 def test_constructor_failure_closes_handle(self):
  closed=[]
  def fail(obj,pid,exe):obj.h=42;obj.k=types.SimpleNamespace(CloseHandle=lambda h:closed.append(h));raise Invalid('bad exe')
  with patch.object(Process,'__init__',fail):
   with self.assertRaises(Invalid):Process04(123,Path('wrong'))
  self.assertEqual(closed,[42])

@unittest.skipUnless(PLAN,'actual frozen plan supplied by qualification command')
class ActualBoundTests(unittest.TestCase):
 def setUp(self):self.f=Fixture(PLAN)
 def test_all_paths_scene_and_table(self):
  f=self.f;c=Coverage();r=collect_one(f.t,f.l,c);self.assertEqual(r['scene']['source_tick'],10);self.assertEqual(r['cpu_us'],1000);self.assertGreater(r['dependencies']['verification_bytes'],0);r=collect_one(f.t,f.l,c,True);self.assertTrue(r['body']['table']['selected'][0]['candidate_descriptor_match']);self.assertEqual(r['dependencies']['first_pass_bytes'],r['dependencies']['verification_bytes']);self.assertIn('source_pointers',r['phase'])
 def test_full_negative_phase_matrix(self):
  f=self.f
  cases=[('odd',f.stats,3,4),('zero sequence',f.stats,0,4),('reset',f.l.address('debug.cpp','proc_tick_idx'),0,4),('stale',f.stats+4,9,4),('menu',f.pg+f.G['Rno0'],2,1),('system',f.pg+f.G['System_flg'],0x400,4),('stop',f.pg+f.G['Stop_flg'],0x40000000,4),('aborted',f.stats+188,1,4),('no present',f.stats+184,0,4),('pace skipping',f.l.address('pace.cpp','re4dc_pace_skipping'),1,4)]
  cases += [(name,f.l.address('native_ui.cpp',name),n,f.audit['variables']['native_ui.cpp:'+name]['bytes']) for name,n in [('source_draws_finished',0),('frame_ready',0),('ui_order',1),('stream_aborted',1),('pace_skip_frame',1),('direct_open',1)]]
  for name,addr,value,width in cases:
   saved=f.read(addr,width);f.put(addr,value.to_bytes(width,'little'))
   with self.subTest(name=name),self.assertRaises(Invalid):f.l.capture()
   f.put(addr,saved)
 def test_skip_clock_five_and_wrapped_clock(self):
  f=self.f;f.w(f.pg+f.G['Frame_cnt'],15);f.var('native_ui.cpp','pace_skipped_frames',5);self.assertEqual(f.l.capture()['scene']['source_tick'],15)
  f.var('native_ui.cpp','pace_skipped_frames',4)
  with self.assertRaisesRegex(Invalid,'clock'):f.l.capture()
  f.w(f.stats+4,0xffffffff);f.var('native_ui.cpp','frame',0xffffffff);f.var('native_ui.cpp','pace_skipped_frames',16);self.assertEqual(f.l.capture()['scene']['source_tick'],15)
 def test_epoch_pointer_and_cursor_mutations_rejected(self):
  for name,mutate in [('epoch',lambda f:f.var('debug.cpp','zero_tick',999)),('player pointer',lambda f:f.w(f.t.sym('_pPL'),0x8c710100)),('source pointer',lambda f:f.w(f.t.sym('_pG'),0x8c700100)),('cursor',lambda f:f.var('debug.cpp','proc_tick_idx',19))]:
   f=Fixture(PLAN)
   def collect():r={'scene':f.t.scene()};mutate(f);return r
   with self.subTest(name=name),self.assertRaises(Invalid):f.l.capture(collect)
 def test_temporary_item_camera_and_next_frame_render_rejected(self):
  f=self.f
  # Render's temporary itemCamera interval occurs after begin advances UI,
  # before source Frame_cnt/CameraMove, while completed stats remain previous.
  f.var('native_ui.cpp','frame',11);f.var('native_ui.cpp','source_draws_finished',0)
  with self.assertRaises(Invalid):f.l.capture()
  f.var('native_ui.cpp','source_draws_finished',1)
  with self.assertRaises(Invalid):f.l.capture()
  # Even if a pose mutation hides behind an unchanged phase tuple, every body
  # dependency is reread; no camera matching or tolerance is used.
  f=Fixture(PLAN);addr=f.pg+f.G['Cam'];calls=[0]
  def hook(a,n):
   if a==addr:
    calls[0]+=1
    if calls[0]==2:f.put(addr,struct.pack('<f',7.0))
  f.read_hook=hook
  with self.assertRaisesRegex(Invalid,'dependency'):f.l.capture()
 def test_descriptor_pointer_changes_rejected(self):
  f=self.f;calls=[0]
  def hook(a,n):
   if a==0x8c750000:
    calls[0]+=1
    if calls[0]==2:f.w(a,0xa4002000)
  f.read_hook=hook
  with self.assertRaisesRegex(Invalid,'dependency'):collect_one(f.t,f.l,Coverage(),True)
 def test_bound_driver_mock_api_waits_then_collects(self):
  f=self.f;now=[0.];reads=[0]
  class Fake:
   ram=1;read_deadline=0
   def live(self):return True
   def read(self,a,n):
    reads[0]+=1
    if reads[0]==1:raise Invalid('waiting exact program anchors')
    if a==0x8c100000:return bytes(256)
    return f.read(a,n)
  proc=Fake();f.t.read=proc.read;f.l.read=proc.read;rows=[];c=Coverage(10,10)
  result=observe(proc,f.t,f.l,{'anchors':[{'address':0x8c100000,'hex':bytes(256).hex()}]},'.',.05,rows.append,c,clock=lambda:now[0],precise=lambda:now[0],sleep=lambda n:now.__setitem__(0,now[0]+n))
  self.assertTrue(result['anchors_verified']);self.assertTrue(c.summary()['coverage_pass']);self.assertIn('waiting exact program anchors',c.summary()['rejection_counts']);self.assertTrue(any(r['event']=='completed_phase_table' for r in rows))
 def test_contract_hashes_and_schema_fail_before_open(self):
  binding,plan,audit=load_contract(PLAN);self.assertEqual(binding['namespace'],'observer-runtime-69f')
  with tempfile.TemporaryDirectory() as d:
   # Missing namespace fails before any OpenProcess/read; no target directory copy.
   p=Path(d)/'observer-runtime-69f';p.mkdir();(p/'binding.json').write_text(json.dumps({**binding,'namespace':'old'}))
   with self.assertRaisesRegex(Invalid,'identity'):load_contract(d)
 def test_source_metadata_and_input_tamper_rejected(self):
  import observer69f
  original=observer69f.sha
  for name,message in [('phase_latch69f05.py','source dependency'),('phase-contract.json','metadata'),('plan-inputs.json','plan inputs')]:
   def altered(p):return '0'*64 if Path(p).name==name else original(p)
   with self.subTest(name=name),patch.object(observer69f,'sha',altered),self.assertRaisesRegex(Invalid,message):load_contract(PLAN)

@unittest.skipUnless(os.name=='nt','Windows read-only API only')
class WindowsApiTests(unittest.TestCase):
 def test_actual_verified_owned_exit_finalizes_cooperatively(self):
  child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(.2)'],creationflags=0x08000000)
  p=None
  try:
   p=Process04(child.pid,Path(sys.executable));deadline=time.monotonic()+3
   while p.live()and time.monotonic()<deadline:time.sleep(.005)
   self.assertTrue(p.guest_exit_verified);self.assertEqual(p.guest_exit_code,0);self.assertLess(time.monotonic(),deadline)
  finally:
   if p:p.close()
   child.wait(timeout=3)
 def test_own_python_process_read_and_deadline(self):
  b=ctypes.create_string_buffer(b'actual API read-only');p=Process04(os.getpid(),Path(sys.executable))
  try:
   p.ram=ctypes.addressof(b);self.assertTrue(p.live());self.assertEqual(p.read(0x8c000000,19),b.raw[:19]);p.read_deadline=time.monotonic()-1
   with self.assertRaisesRegex(Invalid,'window'):p.read(0x8c000000,1)
  finally:p.close();p.close()
 def test_actual_wrong_exe_closes_handles(self):
  k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCurrentProcess.restype=ctypes.c_void_p;k.GetProcessHandleCount.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
  def count():n=ctypes.c_ulong();self.assertTrue(k.GetProcessHandleCount(k.GetCurrentProcess(),ctypes.byref(n)));return n.value
  before=count()
  for _ in range(12):
   with self.assertRaisesRegex(Invalid,'executable'):Process04(os.getpid(),Path(sys.executable).with_name('not-own.exe'))
  self.assertEqual(count(),before)

@unittest.skipUnless(PLAN,'actual new69f plan required')
class CanonicalTests(unittest.TestCase):
 def setUp(self):self.f=Fixture(PLAN)
 def test_every_declared1004_and_original_descriptor_shape(self):
  f=self.f;self.assertEqual(len(f.plan['selected']),1004);self.assertEqual(len(f.plan['supplemental_originals']),36);self.assertEqual(len(f.plan['world_original_map']),36)
  for row in f.plan['selected']+f.plan['supplemental_originals']:
   with self.subTest(key=row['key']):self.assertEqual(len(bytes.fromhex(row['native_descriptor_hex'])),96);self.assertIn('width',f.t.expected_texture(row));self.assertIn('data_size',f.t.expected_texture(row))
 def test_full_descriptor_and_declaredCRC_mismatch_remain_unknown(self):
  f=self.f;H=f.t.t['native_ui']['types']['Header']['members'];f.w(0x8c740000+H['payload_crc32'],0);r=f.t.table()['selected'][0];self.assertFalse(r['canonical_descriptor_match']);self.assertEqual(r['admission'],'UNKNOWN')
  f=Fixture(PLAN);f.put(0x8c740030,b'wrongmaterial');r=f.t.table()['selected'][0];self.assertFalse(r['canonical_descriptor_match'])
 def test_coherent_direct_packet_staging_only_and_reject_changed_pointer(self):
  f=self.f
  for name,value in [('direct_open',1),('frame_ready',1),('stream_scene',1),('stream_aborted',0),('model_handle',f.t.entries),('model_used',0),('model_pending',1),('model_packets',0x8c760000)]:
   symbol=f.t.sy['__ZN12_GLOBAL__N_1L'+str(len(name))+name+'E'];f.put(symbol['address'],value.to_bytes(symbol['size'],'little'))
  f.put(0x8c760000,struct.pack('<8I',0x80840008,0,36,0xc8000200,0,0,0,0));r=f.t.witness();self.assertTrue(r['canonical_descriptor_match']);self.assertFalse(r['submitted_header']);self.assertFalse(r['draw']);self.assertEqual(r['chosen_LOD'],'UNAVAILABLE');self.assertEqual(r['snapshot']['entry_before'],r['snapshot']['entry_after'])
  calls=[0]
  def hook(a,n):
   if a==0x8c760000:
    calls[0]+=1
    if calls[0]==2:f.put(a,b'changed!')
  f.read_hook=hook
  with self.assertRaisesRegex(Invalid,'incoherent'):f.t.witness()
 def test_mock_owned_exit_returns_partial_without_waiting41(self):
  f=self.f;now=[0.];calls=[0]
  class Fake:
   ram=1;read_deadline=0;guest_exit_verified=False;guest_exit_code=None
   def live(self):
    calls[0]+=1
    if calls[0]>2:self.guest_exit_verified=True;self.guest_exit_code=0;return False
    return True
   def read(self,a,n):return bytes(256)if a==0x8c100000 else f.read(a,n)
  proc=Fake();f.t.read=proc.read;f.l.read=proc.read;rows=[];c=Coverage();r=observe(proc,f.t,f.l,{'anchors':[{'address':0x8c100000,'hex':bytes(256).hex()}]},'.',41,rows.append,c,clock=lambda:now[0],precise=lambda:now[0],sleep=lambda n:now.__setitem__(0,now[0]+n));self.assertLess(r['seconds'],.1);self.assertEqual(r['collection_ended'],'verified_owned_guest_exit');self.assertFalse(c.summary()['coverage_pass'])
if __name__=='__main__':unittest.main()
