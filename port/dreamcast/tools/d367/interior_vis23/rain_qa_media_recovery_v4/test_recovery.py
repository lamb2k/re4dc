"""Recovery V4 public plan/path controls; no stage or data conversion."""
from pathlib import Path
import ast,hashlib,json,unittest
HERE=Path(__file__).resolve().parent
class Recovery(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.plan=json.loads((HERE/'PLAN.json').read_bytes())
 def test_reuse_is_explicitly_retired(self):
  x=self.plan['OFF_reuse'];self.assertIs(x['enabled'],False);self.assertIn('EvidenceCompaction',x['reason']);self.assertIn('NEW',x['new_media_identity'])
 def test_protected_fresh_paths(self):
  parent=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/rain-diag24-20261024/_qa-media-8ce-recovery-v4')
  for arm,p in self.plan['base_paths'].items():
   q=Path(p);self.assertEqual(q,parent/('base-'+arm));self.assertEqual(q,q.resolve());self.assertFalse(q.exists())
  for arm,p in self.plan['work_paths'].items():
   q=Path(p);self.assertEqual(q,Path('/root/probe/rain-diag24-qa-media-recovery-v4')/arm);self.assertFalse(q.exists())
 def test_original_limits_and_serial_jobs(self):
  c=self.plan['capacity'];self.assertEqual(c['owned_cap_bytes'],4*1024**3);self.assertEqual(c['C_admission_bytes'],26*1024**3);self.assertEqual(c['C_floor_bytes'],24*1024**3);self.assertLess(c['logical_estimate_bytes'],c['owned_cap_bytes']);self.assertEqual(self.plan['media_recovery']['per_arm_jobs'],1);self.assertEqual(self.plan['media_recovery']['serial_arms'],['off','on']);self.assertTrue(self.plan['media_recovery']['immutable_asset_links_shared'])
 def test_active_stager_has_no_reuse_branch(self):
  s=(HERE/'future_master.py').read_text();self.assertNotIn("if arm=='off' and plan.get('OFF_reuse'",s);self.assertIn("assert plan['OFF_reuse']['enabled'] is False",s);self.assertIn("copy_new(programme/'program.bin'",s);self.assertIn("os.link(fixture/key,dest)",s)
 def test_programme_contract(self):
  p=self.plan;self.assertEqual(p['source'],'8ce5ee2d00027268c3e69c9c300b819c1b14c63f');self.assertEqual(p['programmes']['off']['program.bin']['sha256'],'e0168b780b102356c9bc3ee785753a659be6a020b1d1d3f8db92f14a90c16de5');self.assertEqual(p['programmes']['on']['program.bin']['sha256'],'77dcbf2a619db123ded7388e0e86266e3cb8184bf95cea4cab962593cac34d09');self.assertEqual(p['assets']['files'],1697);self.assertEqual(p['host_python_path'],'/usr/bin/python3.12')
if __name__=='__main__':unittest.main(verbosity=2)
