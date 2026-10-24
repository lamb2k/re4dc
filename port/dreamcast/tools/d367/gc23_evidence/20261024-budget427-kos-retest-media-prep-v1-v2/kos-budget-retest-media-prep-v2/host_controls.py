"""Read-only host guards and synthetic negatives; never stage/geniso/guest."""
from pathlib import Path
import copy,json,sys,tempfile,types,unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
def mod(name):
 p=HERE/(name+'.py');m=types.ModuleType(name);m.__file__=str(p);sys.modules[name]=m;exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
k=mod('core');st=mod('stage')
class Host(unittest.TestCase):
 def test_target_binding_actual(self):k.validate_binding(k.read(HERE/'BINDING.json'))
 def test_baseline_actual(self):k.baseline_check()
 def test_cumulative_actual(self):self.assertLess(k.capacity()['aggregate_bytes'],k.AGG)
 def test_manifest_off_actual(self):
  c,pins=k.adapter();b=types.ModuleType('bind');b.validate=k.validate_binding;sys.modules['bind']=b;rb=k.source('readback',k.OLD/'readback.py',pins['readback.py']['sha256']);v=rb.check('off',k.OFF);self.assertEqual(v['files'],1715)
 def test_hardlink_unique(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   p=Path(d);(p/'a').write_bytes(b'123');__import__('os').link(p/'a',p/'b');self.assertEqual(k.scan([p])[0],3)
 def test_duplicate_copy_counts(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   p=Path(d);(p/'a').write_bytes(b'123');(p/'b').write_bytes(b'123');self.assertEqual(k.scan([p])[0],6)
 def test_symlink_refused(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   p=Path(d);(p/'a').write_bytes(b'1');(p/'b').symlink_to(p/'a')
   with self.assertRaises(AssertionError):k.scan([p])
 def caps(self,prior,delta,free=30*1024**3):
  b={'roots':['/old'],'unique_bytes':prior};v=dict(size=delta,dev=2,ino=2,nlink=1)
  with patch.object(k,'read',return_value=b),patch.object(k,'scan',side_effect=[(prior,{},set()),(delta,{'/new':v},set()),(0,{},set()),(0,{},set())]),patch.object(k.os,'statvfs',return_value=types.SimpleNamespace(f_bavail=free,f_frsize=1)):return k.capacity()
 def test_delta_cap(self):
  with self.assertRaises(AssertionError):self.caps(5*1024**3,k.DELTA+1)
 def test_aggregate_cap(self):
  with self.assertRaises(AssertionError):self.caps(k.AGG-100,101)
 def test_C_floor(self):
  with self.assertRaises(AssertionError):self.caps(1,1,k.FLOOR-1)
 def test_baseline_bytes_drift(self):
  b=k.read(HERE/'BASELINE.json');b['unique_bytes']+=1
  original=k.read
  with patch.object(k,'read',side_effect=lambda x:b if Path(x)==HERE/'BASELINE.json' else original(x)),self.assertRaises(AssertionError):k.capacity()
 def test_wrong_review(self):
  b=copy.deepcopy(k.read(HERE/'BINDING.json'));b['target_review']['status']='MEMORY_PASS'
  with self.assertRaises(AssertionError):k.validate_binding(b)
 def test_wrong_programme(self):
  b=copy.deepcopy(k.read(HERE/'BINDING.json'));b['arms']['on']['programmes']['program.bin']['identity']['sha256']='0'*64
  with self.assertRaises(AssertionError):k.validate_binding(b)
 def grant(self):return dict(approved=True,scope='STAGE_ONLY_NO_GUEST_NO_SDK',source=k.SOURCE,baseline_identity=k.row(HERE/'BASELINE.json'),new_delta_cap=k.DELTA,aggregate_cap=k.AGG,existing_OFF_reuse_only=True,new_final_arms=['on'])
 def test_grant_valid(self):st.grant_guard(self.grant(),k)
 def test_unapproved_template(self):
  g=self.grant();g['approved']=False
  with self.assertRaises(AssertionError):st.grant_guard(g,k)
 def test_grant_both_new(self):
  g=self.grant();g['new_final_arms']=['off','on']
  with self.assertRaises(AssertionError):st.grant_guard(g,k)
 def test_grant_old_cap_reset(self):
  g=self.grant();g['aggregate_cap']=4*1024**3
  with self.assertRaises(AssertionError):st.grant_guard(g,k)
 def test_grant_delta_raise(self):
  g=self.grant();g['new_delta_cap']+=1
  with self.assertRaises(AssertionError):st.grant_guard(g,k)
 def test_proposal_four_exact(self):
  j=k.read(HERE/'GUEST-PROPOSAL.json');self.assertEqual([(v['arm'],v['fragment']) for v in j['cases']],[('off',0),('on',0),('off',1),('on',1)])
  for v in j['cases']:self.assertEqual((v['held'],v['harness_seconds'],v['exact_child_seconds']),(49152,45,55));self.assertTrue(v['cache_must_be_absent_before_Python_start']);self.assertFalse(Path(v['cache_WSL']).exists())
 def test_proposal_isolated_pillow(self):
  for v in k.read(HERE/'GUEST-PROPOSAL.json')['cases']:
   a=v['argv'];self.assertEqual(a[5:9],['-I','-S','-B','-X']);self.assertIn('pillow_launcher.py',a[10]);self.assertIn('census-bound-run.py',a[12])
 def test_no_stage_paths(self):self.assertFalse(k.FINAL.exists());self.assertFalse(k.WORK.exists())
if __name__=='__main__':
 assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Host));k.fresh(HERE/'HOST-CONTROLS.json',dict(tests=result.testsRun,success=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),SDK=0,geniso=0,stage=0,guests=0));raise SystemExit(not result.wasSuccessful())
