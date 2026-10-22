import copy,datetime,unittest
from pathlib import Path
from contain import root_review_contract
from prepare_profile import console_contract,native_path
class Tests(unittest.TestCase):
 def profile(self):
  p=dict(source='1'*40,qa_source='2'*40,pair='pair02',fixture_name='f1',arm='C',stage_receipt_sha256='3'*64,lane_live_guests=0)
  p['root_review']={**{k:v for k,v in p.items()if k!='fixture_name'},'fixture':'f1','global_live_guests':2,'programme_and_asset_disc_closure_reviewed':True,'actual_sdk_source_reviewed':True,'capacity_reviewed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};return p
 def test_exact_root_review(self):root_review_contract(self.profile())
 def test_different_arm_refuses(self):
  p=self.profile();p['root_review']['arm']='ASM'
  with self.assertRaises(ValueError):root_review_contract(p)
 def test_stage_mismatch_refuses(self):
  p=self.profile();p['root_review']['stage_receipt_sha256']='4'*64
  with self.assertRaises(ValueError):root_review_contract(p)
 def test_lane_mismatch_refuses(self):
  p=self.profile();p['root_review']['lane_live_guests']=1
  with self.assertRaises(ValueError):root_review_contract(p)
 def test_global_overflow_refuses(self):
  p=self.profile();p['root_review']['global_live_guests']=16
  with self.assertRaises(ValueError):root_review_contract(p)
 def test_stale_root_review_refuses(self):
  p=self.profile();p['root_review']['capacity_reviewed_utc']=(datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(seconds=61)).isoformat()
  with self.assertRaises(ValueError):root_review_contract(p)
 def test_explicit_console(self):console_contract({'RE4DC_CONSOLE_EXE':'chosen.exe'},Path('chosen.exe'))
 def test_missing_console_refuses(self):
  with self.assertRaises(ValueError):console_contract({},Path('chosen.exe'))
 def test_mismatched_console_refuses(self):
  with self.assertRaises(ValueError):console_contract({'RE4DC_CONSOLE_EXE':'other.exe'},Path('chosen.exe'))
 def test_linux_path_maps_to_unc(self):self.assertEqual(str(native_path('/root/probe/current/file')),r'\\wsl.localhost\Ubuntu-24.04\root\probe\current\file')
 def test_unc_path_preserved(self):
  value=r'\\wsl.localhost\Ubuntu-24.04\root\probe\current\file';self.assertEqual(str(native_path(value)),value)
if __name__=='__main__':unittest.main()
