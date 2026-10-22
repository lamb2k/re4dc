"""Source-only1618 controls; reuse reviewed small1600 fixtures through new adapter."""
import os,sys,unittest
from pathlib import Path
from unittest.mock import patch
import immutable_append1618_writer as new
import test_immutable_append1600_writer as previous

class Reused1618WriterTests(previous.WriterTests):
 def setUp(self):
  super().setUp();self.adapter_patch=patch.object(previous,'w',new);self.adapter_patch.start()
 def tearDown(self):self.adapter_patch.stop();super().tearDown()
 def test_missing_dependency_never_reaches_resolution(self):
  with patch.object(new,'environment',return_value='SYNTHETIC'):super().test_missing_dependency_never_reaches_resolution()
 def test_native_allocation_only_known_unsupported_falls_back(self):
  for error in(1,50,120):self.assertEqual(new.charge_result(1,0xffffffff,0,error),4096)
  for error in(2,5,6,87,123):
   with self.subTest(error=error),self.assertRaises(OSError):new.charge_result(1,0xffffffff,0,error)
  self.assertEqual(new.charge_result(1,16384,0,0),16384);self.assertEqual(new.charge_result(5000,1,0,0),8192)
  self.assertEqual(new.charge_result(1,0xffffffff,0,0),0xffffffff)
 def test_both_root_environment_and_exact_fresh_charged_prefix(self):
  meta=self.root/'meta';meta.mkdir();cache=meta/'pycache';plan=dict(metadata_root=str(meta))
  with patch.object(sys,'dont_write_bytecode',True),patch.object(sys,'pycache_prefix',str(cache)),patch.dict(os.environ,{'PYTHONDONTWRITEBYTECODE':'1','PYTHONPYCACHEPREFIX':str(cache)}):
   self.assertEqual(new.environment(plan),str(cache))
   with patch.object(sys,'dont_write_bytecode',False),self.assertRaises(ValueError):new.environment(plan)
   with patch.dict(os.environ,{'PYTHONDONTWRITEBYTECODE':'0'}),self.assertRaises(ValueError):new.environment(plan)
   with patch.object(sys,'pycache_prefix',str(self.root/'outside')),self.assertRaises(ValueError):new.environment(plan)
   with patch.dict(os.environ,{'PYTHONPYCACHEPREFIX':'relative'}),self.assertRaises(ValueError):new.environment(plan)
   cache.mkdir()
   with self.assertRaises(ValueError):new.environment(plan)
 def test_no_bytecode_gate_precedes_local_imports(self):
  source=Path(new.__file__).read_text();self.assertLess(source.index('if not sys.dont_write_bytecode'),source.index('from file_charge import'))
  self.assertNotEqual(new.CAP,previous.w.CAP if previous.w is not new else 332828672)

if __name__=='__main__':unittest.main(verbosity=2)
