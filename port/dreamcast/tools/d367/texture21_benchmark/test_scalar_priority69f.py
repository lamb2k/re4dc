import ctypes,hashlib,json,os,struct,sys,tempfile,time,types,unittest
from pathlib import Path
from unittest.mock import patch
from fixture69f import Fixture
from observer import Invalid,Process
from observer69f import Coverage,Process04
from observer69f_scalar_first import load_successor
from scalar_priority69f import ScalarProcess,ScalarLatch,BufferedRows,observe_scalar,cadence_model

BASE=os.environ.get('RE4_RUNTIME69F_PLAN');SUCCESSOR=os.environ.get('RE4_RUNTIME69F_SUCCESSOR')

class SchedulingTests(unittest.TestCase):
 def test_precise_deadline_around_base_read_even_with_coarse_monotonic(self):
  p=object.__new__(ScalarProcess)
  with patch('scalar_priority69f.time.monotonic',return_value=100.),patch('scalar_priority69f.time.perf_counter',return_value=200.):p.set_window(200.004)
  self.assertAlmostEqual(p.read_deadline,100.08)
  with patch('scalar_priority69f.time.perf_counter',side_effect=[200.003,200.005]),patch.object(Process04,'read',return_value=b'a'),self.assertRaisesRegex(Invalid,'precise'):p.read(0x8c000000,1)
 def test_old_10ms_aliases_but_half_ms_covers_every_model_frame(self):
  old=cadence_model(33000000,2000000,121,10000000);new=cadence_model(33000000,2000000,121,500000)
  self.assertGreater(len(old['missing']),60);self.assertEqual(new['missing'],[])
 def test_all_initial_offsets_and_narrow_impossible_windows(self):
  for offset in range(0,1000000,50000):
   self.assertEqual(cadence_model(33000000,2000000,121,500000,start_ns=offset)['missing'],[])
  self.assertTrue(cadence_model(33000000,100000,121,500000)['missing'])
 def test_buffer_never_writes_until_finalization_and_no_partial_rows(self):
  b=BufferedRows(50);b.emit({'a':1})
  with self.assertRaisesRegex(Invalid,'budget'):b.emit({'x':'x'*80})
  self.assertEqual(b.rows,[b'{"a":1}\n'])
  with tempfile.TemporaryDirectory()as d:
   p=Path(d)/'rows';b.write(p);self.assertEqual(p.read_bytes(),b.rows[0])
   with self.assertRaises(FileExistsError):b.write(p)

@unittest.skipUnless(BASE and SUCCESSOR,'actual69f frozenbase and successor bindings required')
class BoundTests(unittest.TestCase):
 def setUp(self):self.f=Fixture(BASE);self.l=ScalarLatch(self.f.t,self.f.audit)
 def test_all_existing_phase_guards_and_full_rawstat_identity(self):
  self.assertTrue(self.l.peek_ready());r=self.l.capture_scalar();self.assertEqual(len(bytes.fromhex(r['body']['completed_native_raw192'])),192);self.assertEqual(r['body']['completed_native_fields']['frame'],10);self.assertEqual(r['dependencies']['first_pass_bytes'],r['dependencies']['verification_bytes'])
  for cu,name,value in [('debug.cpp','proc_tick_idx',0),('native_ui.cpp','frame',11),('native_ui.cpp','completed_frame',3)]:
   f=Fixture(BASE);f.var(cu,name,value);l=ScalarLatch(f.t,f.audit);self.assertFalse(l.peek_ready())
   with self.assertRaises(Invalid):l.capture_scalar()
 def test_hint_never_accepts_menu_skip_or_temporary_itemcamera(self):
  f=self.f;f.put(f.pg+f.G['Rno0'],b'\2');self.assertTrue(self.l.peek_ready())
  with self.assertRaisesRegex(Invalid,'ordinary'):self.l.capture_scalar()
  f.put(f.pg+f.G['Rno0'],b'\3');f.var('native_ui.cpp','pace_skip_frame',1)
  with self.assertRaises(Invalid):self.l.capture_scalar()
  f.var('native_ui.cpp','pace_skip_frame',0);f.var('native_ui.cpp','source_draws_finished',0)
  with self.assertRaises(Invalid):self.l.capture_scalar()
 def test_skipped_clock_five_wrap_and_reset_rejected(self):
  f=self.f;f.w(f.pg+f.G['Frame_cnt'],15);f.var('native_ui.cpp','pace_skipped_frames',5);self.assertEqual(self.l.capture_scalar()['scene']['source_tick'],15)
  f.var('native_ui.cpp','pace_skipped_frames',4)
  with self.assertRaisesRegex(Invalid,'clock'):self.l.capture_scalar()
  f.w(f.stats+4,0xffffffff);f.var('native_ui.cpp','frame',0xffffffff);f.var('native_ui.cpp','pace_skipped_frames',16);self.assertEqual(self.l.capture_scalar()['scene']['source_tick'],15)
  f.var('debug.cpp','proc_tick_idx',0)
  with self.assertRaises(Invalid):self.l.capture_scalar()
 def test_rawstats_and_processmarkers_mutation_rejected(self):
  for address in [self.f.stats+132,self.l.address('debug.cpp','proc_tick')]:
   f=Fixture(BASE);l=ScalarLatch(f.t,f.audit);calls=[0]
   def hook(a,n):
    if a<=address<a+n:
     calls[0]+=1
     if calls[0]==(3 if address==f.stats+132 else 2):f.w(address,37)
   f.read_hook=hook
   with self.subTest(address=address),self.assertRaises(Invalid):l.capture_scalar()
 def test_pointers_and_pose_mutation_still_rejected(self):
  f=self.f;calls=[0];camera=f.pg+f.G['Cam']
  def hook(a,n):
   if a==camera:
    calls[0]+=1
    if calls[0]==2:f.put(camera,struct.pack('<f',8.0))
  f.read_hook=hook
  with self.assertRaises(Invalid):self.l.capture_scalar()
 def test_conflicting_accepted_variants_retained_not_selected(self):
  c=Coverage(10,10);r=self.l.capture_scalar();self.assertTrue(c.accept(r));self.f.put(self.f.pg+self.f.G['Cam'],struct.pack('<f',8.0));other=self.l.capture_scalar();self.assertTrue(c.accept(other));self.assertEqual(c.summary()['conflicting_frames'],[10]);self.assertFalse(c.summary()['coverage_pass'])
 def test_contract_sources_base_and_actual_array_member_widths(self):
  b,base,plan,audit=load_successor(SUCCESSOR);self.assertEqual(b['namespace'],'observer-runtime-69f-scalar-first-01');self.assertEqual(audit['variables']['debug.cpp:proc_name']['bytes'],128)
  import observer69f_scalar_first as m
  original=m.sha
  for name in ['binding.json','scalar_priority69f.py']:
   with self.subTest(name=name),patch.object(m,'sha',lambda p:'0'*64 if Path(p).name==name else original(p)),self.assertRaises(Invalid):load_successor(SUCCESSOR)
 def test_cooperative_exit_partial_and_output_budget_failure(self):
  f=self.f;now=[0.];calls=[0]
  class P:
   ram=1;read_deadline=0;guest_exit_verified=False;guest_exit_code=None
   def live(self):
    calls[0]+=1
    if calls[0]>8:self.guest_exit_verified=True;self.guest_exit_code=0;return False
    return True
   def read(self,a,n):return bytes(256)if a==0x8c100000 else f.read(a,n)
  p=P();f.t.read=p.read;l=ScalarLatch(f.t,f.audit);l.read=p.read;buf=BufferedRows();c=Coverage();r=observe_scalar(p,l,{'anchors':[{'address':0x8c100000,'hex':bytes(256).hex()}]},'.',41,buf.emit,c,clock=lambda:now[0],precise=lambda:now[0],sleep=lambda s:now.__setitem__(0,now[0]+s));self.assertEqual(r['collection_ended'],'verified_owned_guest_exit');self.assertLess(r['seconds'],.01);self.assertFalse(c.summary()['coverage_pass']);self.assertTrue(c.summary()['accepted_attempts'])
 def test_deadline_and_cadence_bounded(self):
  for seconds,cadence in [(42,.0005),(41,.002),(41,0)]:
   with self.assertRaises(Invalid):observe_scalar(None,None,{},'.',seconds,None,Coverage(),cadence=cadence)
 def test_actual_latch_pipeline_all121_simulated_source_frames_and_stall(self):
  for stall in [False,True]:
   f=Fixture(BASE);now=[0];stalled=[False];period=33000000;duration=121*period
   class P:
    ram=1;read_deadline=0
    def live(self):return True
    def read(self,address,size):
     frame=now[0]//period;offset=now[0]%period;ui=239+frame
     f.w(f.stats,2*ui);f.w(f.stats+4,ui);f.var('native_ui.cpp','frame',ui);f.w(f.pg+f.G['Frame_cnt'],ui+1);f.var('native_ui.cpp','pace_skipped_frames',1);f.var('debug.cpp','zero_tick',100+frame);f.var('debug.cpp','proc_tick_idx',20 if period-2000000<=offset<period else 0)
     result=bytes(256)if address==0x8c100000 else f.read(address,size);now[0]+=1000;return result
   def sleep(s):
    if stall and not stalled[0]and now[0]//period==50 and now[0]%period>20000000:now[0]+=20000000;stalled[0]=True
    now[0]+=round(s*1e9)
   p=P();f.t.read=p.read;l=ScalarLatch(f.t,f.audit);c=Coverage();buf=BufferedRows();result=observe_scalar(p,l,{'anchors':[{'address':0x8c100000,'hex':bytes(256).hex()}]},'.',duration/1e9,buf.emit,c,clock=lambda:now[0]/1e9,precise=lambda:now[0]/1e9,sleep=sleep)
   with self.subTest(stall=stall):
    if not stall:self.assertTrue(c.summary()['coverage_pass']);self.assertEqual(c.summary()['target_missing_frames'],[])
    else:self.assertFalse(c.summary()['coverage_pass']);self.assertIn(290,c.summary()['target_missing_frames'])

@unittest.skipUnless(os.name=='nt'and BASE,'Windows ownprocess API source fixture only')
class NativeFixtureTests(unittest.TestCase):
 def test_actual_RPM_complete_scalar_rawstats_and_idempotent_cleanup(self):
  f=Fixture(BASE);buf=(ctypes.c_ubyte*len(f.raw)).from_buffer(f.raw);p=ScalarProcess(os.getpid(),Path(sys.executable));p.ram=ctypes.addressof(buf)
  try:
   p.set_window(time.perf_counter()+.004);f.t.read=p.read;l=ScalarLatch(f.t,f.audit);self.assertTrue(l.peek_ready());r=l.capture_scalar();self.assertEqual(r['scene']['source_tick'],10);self.assertEqual(r['body']['completed_native_fields']['sequence'],2)
  finally:p.close();p.close()
if __name__=='__main__':unittest.main()
