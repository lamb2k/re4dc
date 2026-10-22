"""No process/Windows runtime; review role and concrete retained-runner wiring."""
import importlib.util,json,pathlib,unittest
P=pathlib.Path(__file__).parent;s=importlib.util.spec_from_file_location('inner',P/'inner-adapter.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Contract(unittest.TestCase):
 def setUp(self):self.profile=json.loads((P/'guest-profile-v2.json').read_text())
 def test_cold_never_seed(self):
  m.validate_role(self.profile,'cold-shoot01',None)
  with self.assertRaises(ValueError):m.validate_role(self.profile,'cold-shoot01','old')
 def test_only_reviewed_roles_and_later_seed_required(self):
  for role in ['return-door01','cinematic01']:
   with self.assertRaises(ValueError):m.validate_role(self.profile,role,None)
  with self.assertRaises(ValueError):m.validate_role(self.profile,'farm-scheduledkill',None)
 def test_inner_limits_and_no_legacy_thresholds(self):
  source=(P/'inner-adapter.py').read_text();self.assertIn("'--seconds','41','--period','0'",source);self.assertIn("os.environ['RE4DC_MAX_FLYCASTS']='16'",source);self.assertIn('18*1024**3+64*1024**2',source);self.assertNotIn('>= 12',source);self.assertNotIn('>= 14',source);self.assertIn("elapsed()>=40.75",source)
 def test_cold_keys_select_entry_index4_no_scheduled_kill(self):
  keys=(P/'r103-cold-keys.txt').read_text();lines=[l for l in keys.splitlines() if l.strip() and not l.startswith('#')];screen2=next(i for i,l in enumerate(lines) if 'screen 2'in l);self.assertEqual(sum('down'in l for l in lines[screen2:]),4)
  assets=json.loads((P/'selected-assets.json').read_text());self.assertNotIn('kill ',assets['/dc/qa/r103.txt']['text']);self.assertIn('kill 0x12 150',assets['/dc/qa/r103f.txt']['text'])
 def test_source12_transition_sites_new_reader_program_identity(self):
  transitions=json.loads((P/'current-transitions.json').read_text());self.assertEqual(transitions['callsite_count'],12);self.assertEqual(transitions['source'],self.profile['fixed_runtime']['source']);self.assertEqual(len(self.profile['fixed_runtime']['all14']),14)
 def test_read_only_transport_no_memory_write_api(self):
  source=(P/'observe.py').read_text();self.assertIn('ReadProcessMemory',source);self.assertNotIn('WriteProcessMemory',source)
if __name__=='__main__':unittest.main(verbosity=2)
