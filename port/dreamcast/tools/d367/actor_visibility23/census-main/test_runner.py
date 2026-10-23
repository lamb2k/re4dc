"""Pure/mocked main-wrapper controls; never query native state or execute a guest."""
from pathlib import Path
import copy,datetime,importlib.util,json,tempfile,unittest
from unittest.mock import patch
import contracts as c
P=Path(__file__).parent
spec=importlib.util.spec_from_file_location('main_runner',P/'root-native-census-bea2.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
def resources():return dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),admitted=True,package_one_guest_admitted=True,errors=[],root_cap=16*1024**3,projected_peak=15*1024**3,guest_peak=60*1024**2,floor=c.FLOOR,package_cap=3758096384,package_current_bytes=100000)
def stage():return dict(status='ACTOR23_TWIN_STAGED_NO_GUEST',source=c.SOURCE,integration='0b4beb704902a1dc6b2aace056be344863b4a0c1',programme_receipt_sha256=c.PROGRAMME_SHA,ownership_audit=dict(sha256=c.AUDIT_SHA),fixture_pins={c.CASE:dict(sha256='6b28db8cdec172110720ab105fd9c3ce68b15f10d4607eb207dc19829d43cbe3')})
class RunnerTests(unittest.TestCase):
 def test_current_resource_and_zero_guest_contract(self):c.validate_resources(resources());c.require_no_guests(dict(global_live_guests=0,lane_live_guests=0))
 def test_stale_future_denied_peak_floor_package_or_type_refuses(self):
  for key,val in [('utc','2026-01-01T00:00:00+00:00'),('utc','2099-01-01T00:00:00+00:00'),('admitted',False),('package_one_guest_admitted',False),('errors',['missing']),('root_cap',17*1024**3),('projected_peak',17*1024**3),('guest_peak',1),('floor',0),('package_current_bytes',3758096384),('package_cap',1),('projected_peak',False)]:
   r=resources();r[key]=val
   with self.subTest(key=key,val=val),self.assertRaises(ValueError):c.validate_resources(r)
 def test_live_ambiguous_or_peer_guest_refuses(self):
  for r in ({},{'global_live_guests':1,'lane_live_guests':0},{'global_live_guests':0,'lane_live_guests':1},{'global_live_guests':False,'lane_live_guests':0}):
   with self.assertRaises(ValueError):c.require_no_guests(r)
 def test_current_stage_and_old_image_rebind_or_fixture_refuses(self):
  c.validate_stage(stage())
  for kind in ('source','programme','audit','case','fixture','rebind'):
   r=stage()
   if kind=='source':r['source']='10395a107045fd98934d47f4f903591640d4447c'
   elif kind=='programme':r['programme_receipt_sha256']='a'*64
   elif kind=='audit':r['ownership_audit']['sha256']='a'*64
   elif kind=='case':r['fixture_pins']={'r119-observe':{}}
   elif kind=='fixture':r['fixture_pins'][c.CASE]['sha256']='a'*64
   else:r['fixture_rebind']={}
   with self.subTest(kind=kind),self.assertRaises(ValueError):c.validate_stage(r)
 def test_default_main_never_executes_or_creates_profiles(self):
  argv=['runner','--stage','stage','--stage-sha256','a'*64,'--resources','resource','--resources-sha256','b'*64,'--wrapper-review','review','--wrapper-review-sha256','c'*64]
  with patch.object(runner.sys,'argv',argv),patch.object(c,'verify_source'),patch.object(c,'checked',side_effect=[stage(),resources()]),patch.object(runner,'execute')as execute:
   runner.main();execute.assert_not_called()
 def test_explicit_execute_dispatches_only_after_reviews_and_receipts(self):
  argv=['runner','--stage','stage','--stage-sha256','a'*64,'--resources','resource','--resources-sha256','b'*64,'--wrapper-review','review','--wrapper-review-sha256','c'*64,'--execute']
  with patch.object(runner.sys,'argv',argv),patch.object(c,'verify_source'),patch.object(c,'checked',side_effect=[stage(),resources()]),patch.object(runner,'execute')as execute:
   runner.main();execute.assert_called_once()
  with patch.object(runner.sys,'argv',argv),patch.object(c,'verify_source',side_effect=ValueError('review refused')),patch.object(runner,'execute')as execute:
   with self.assertRaises(ValueError):runner.main()
   execute.assert_not_called()
 def test_stage_and_resources_pin_changes_refuse(self):
  with tempfile.TemporaryDirectory(dir=P)as folder:
   path=Path(folder)/'input.json';path.write_text('{}')
   with self.assertRaises(ValueError):c.checked(path,'a'*64)
 def test_shell_explicit_execute_trace_and_no_game_hooks(self):
  text=(P/'root-native-census-bea2.sh').read_text();self.assertIn('TRACE_SLOTS=16',text);self.assertIn('TRACE_LOCK_OWNER=actor23-root-census-bea2r3',text);self.assertIn('execute=0',text);self.assertIn('[ "$arg" != --execute ]',text);self.assertIn('if [ "$execute" -eq 0 ]',text)
  code=(P/'root-native-census-bea2.py').read_text();self.assertNotIn('WriteProcessMemory',code);self.assertNotIn('capture_ui_vram(',code);self.assertIn("source_clean();held_trace()",code);self.assertIn('census(all_guest_count)',code)
if __name__=='__main__':unittest.main()
