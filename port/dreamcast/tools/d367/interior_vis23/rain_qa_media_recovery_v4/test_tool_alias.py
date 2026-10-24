"""Narrow alias controls; only public owned fake payloads are mutated."""
from pathlib import Path
import copy,hashlib,json,os,sys,tempfile,types,unittest
HERE=Path(__file__).resolve().parent
p=HERE/'common.py';c=types.ModuleType('common');c.__file__=str(p);sys.modules['common']=c;exec(compile(p.read_bytes(),str(p),'exec'),c.__dict__)
class Alias(unittest.TestCase):
 def fixture(self,root):
  target=root/'python3.12';target.write_bytes(b'public fake host tool');alias=root/'python3';alias.symlink_to('python3.12');return alias,target,{'link_text':'python3.12','canonical_path':str(target),'identity':c.row(target)}
 def test_exact_documented_alias(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as t:
   alias,target,fact=self.fixture(Path(t));c.verify_documented_alias(alias,fact);c.verify(target,fact['identity'])
 def test_alias_link_drift(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as t:
   root=Path(t);alias,target,fact=self.fixture(root);(root/'other').write_bytes(target.read_bytes());alias.unlink();alias.symlink_to('other')
   with self.assertRaisesRegex(RuntimeError,'alias link text drift'):c.verify_documented_alias(alias,fact)
 def test_canonical_target_payload_drift(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as t:
   alias,target,fact=self.fixture(Path(t));target.write_bytes(b'drift')
   with self.assertRaisesRegex(RuntimeError,'Pinned input changed'):c.verify_documented_alias(alias,fact)
 def test_canonical_target_symlink_refused(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as t:
   root=Path(t);alias,target,fact=self.fixture(root);(root/'other').write_bytes(target.read_bytes());target.unlink();target.symlink_to('other')
   with self.assertRaises(RuntimeError):c.verify_documented_alias(alias,fact)
 def test_generic_asset_alias_still_refused(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as t:
   alias,target,fact=self.fixture(Path(t))
   with self.assertRaisesRegex(RuntimeError,'Pinned input changed'):c.verify(alias,fact['identity'])
 def test_production_mapping_drift_refused(self):
  plan=c.read(HERE/'PLAN.json');plan['host_tool_aliases']['/usr/bin/python3']['link_text']='other'
  with self.assertRaisesRegex(RuntimeError,'Exact interpreter alias mapping'):c.verify_inputs(plan)
 def test_no_extra_alias_allowlist(self):
  plan=c.read(HERE/'PLAN.json');plan['host_tool_aliases']['/unapproved/asset']={}
  with self.assertRaisesRegex(RuntimeError,'Only documented interpreter alias'):c.verify_inputs(plan)
if __name__=='__main__':unittest.main(verbosity=2)
