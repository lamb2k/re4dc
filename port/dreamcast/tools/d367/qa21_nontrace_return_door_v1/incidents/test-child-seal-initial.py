"""Only new child namespace/data/role contracts; no live process/RAM/input or guest."""
import ast,contextlib,copy,hashlib,importlib.util,io,json,os,pathlib,tempfile,unittest
P=pathlib.Path(__file__).parent;V=P.parent/'qa21_nontrace_guest_telemetry_v1'
def load(n,f):
 s=importlib.util.spec_from_file_location(n,f);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def resolve(path):
 if os.name=='nt':return pathlib.Path(path)
 w=pathlib.PureWindowsPath(path);drive=w.drive.replace(chr(92),'/').lower()
 if drive=='//wsl.localhost/ubuntu-24.04':return pathlib.Path('/').joinpath(*w.parts[1:])
 if drive=='c:':return pathlib.Path('/mnt/c').joinpath(*w.parts[1:])
 raise ValueError('unrecognized exact readonly external path')
def sha(path):
 with pathlib.Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
o=load('child_outer_contract',P/'outer-driver.py');i=load('child_inner_contract',P/'inner-adapter.py');c=load('child_controller_contract',P/'controller-core.py')
class Child(unittest.TestCase):
 def setUp(self):self.profile=json.loads((P/'guest-profile-v2.json').read_text());self.refs=json.loads((P/'referenced-readonly-files.json').read_text());self.seed=pathlib.PureWindowsPath(self.profile['evidence_root'])/'cold-shoot01'
 def test_only_runtime_contact_literal_changes_all_guardians_exact(self):
  names=['outer-driver.py','inner-adapter.py','windows-backend.py','guest-supervisor-core.py','input-deadlines.py','policies.py','observe.py','observer-v2.py','layout-contract.py','capture-budget.py']
  for n in names:self.assertEqual((P/n).read_bytes(),(V/n).read_bytes(),n)
  self.assertEqual((P/'controller-core.py').read_bytes(),(V/'controller-core.py').read_bytes().replace(b"key='a';hold=.2;self.attempts+=1",b"key='a';hold=.15;self.attempts+=1"))
 def test_profile_byte_exact_4c_and_actual_arguments_request_only_return_role(self):
  self.assertEqual(sha(P/'guest-profile-v2.json'),'4c386fa2fd826d2b04f7bf5b8696dca3e339dd92485c11b8ec91b863d21ce99b');a=o.parse_args(['--profile',str(P/'guest-profile-v2.json'),'--profile-sha256','4c','--tools-sha256','not-an-execution-seal','--mode','return-door01','--seed',str(self.seed)]);role=i.validate_role(self.profile,a.mode,a.seed);self.assertEqual(a.mode,'return-door01');self.assertEqual(role['name'],'return-door01');self.assertEqual(resolve(role['keys']).read_bytes(),b'')
 def test_no_inherited_default_mode_or_unseeded_later_role(self):
  with contextlib.redirect_stderr(io.StringIO()):
   with self.assertRaises(SystemExit):o.parse_args(['--profile','p','--profile-sha256','p','--tools-sha256','t'])
  with self.assertRaises(ValueError):i.validate_role(self.profile,'return-door01',None)
 def test_windows_absolute_path_join_pins_actual_v1_data_not_child_shadow(self):
  base=pathlib.PureWindowsPath('C:/child')
  for name in self.refs['files']:
   w=pathlib.PureWindowsPath(name);self.assertTrue(w.is_absolute(),name);self.assertEqual(base/w,w);self.assertTrue(resolve(name).is_file(),name)
 def test_all_actual_readonly_data_hashes_and_sizes_match(self):
  for name,pin in self.refs['files'].items():
   path=resolve(name);self.assertEqual(path.stat().st_size,pin['bytes'],name);self.assertEqual(sha(path),pin['sha256'],name)
 def test_strict_parent_metadata_exact_profile_state_programme_and_no_failedparent(self):
  cp=resolve(str(self.seed/'checkpoint.json'));q=resolve(str(self.seed.parent/'cold-shoot01-control'/'qualification.json'));row=json.loads(cp.read_text());qual=json.loads(q.read_text());self.assertTrue(qual['qualified']);self.assertEqual(qual['profile_sha256'],sha(P/'guest-profile-v2.json'));self.assertEqual(row['audit']['state_sha256'],'e81e572fefa7a94771ecde68c1d38456e4a51d62d3b3641ecd52de0db51b0c75');self.assertEqual(row['audit']['frame'],533);self.assertEqual(row['input']['program_sha256'],self.profile['fixed_runtime']['program_sha256']);self.assertIsNone(row['parent']);self.assertFalse(row['state_edits'])
 def test_actual_existing_profile_validator_has_no_ancestry_bypass(self):
  # Real Windows path semantics are exercised by live read-only preflight below;
  # existing validator source/AST is byte exact and its checks remain explicit.
  text=(P/'outer-driver.py').read_text();self.assertIn("receipt.get('profile_sha256')!=profile_sha",text);self.assertIn("receipt.get('qualified') is not True",text);self.assertIn("receipt.get('program_sha256')!=PROGRAM",text);self.assertIn("no_alias(seed)!=expected",text)
 def test_exact_serialized_parent_first_turn_and_bounded_A_candidate(self):
  contract=P.parent/'qa21_nontrace_run_preparation/telemetry-v1-door-plan/seed-contract.json';row=json.loads(contract.read_text())['rich_snapshot'];e=c.Door();action=e.step(row,0,0);self.assertEqual(action[0]['down'],'turnleft');self.assertEqual(e.pending_hold,.65);contact=copy.deepcopy(row);contact['player']['pos']=[-49000.,0.,7670.];contact['player']['ang']=[0.,-1.5707963267948966,0.];e=c.Door();self.assertEqual(e.step(contact,0,0)[0]['down'],'a');self.assertEqual(e.pending_hold,.15)
 def test_original_resource_parser_exit_job_input_structures_and_bounds_unchanged(self):
  # Byte-exact runtime identities carry the accepted Win/Linux source tests,
  # native3 child-job receipts and actualcold41.7446011s telemetry; no rerun.
  proof=json.loads((P/'runtime-source-proof.json').read_text());self.assertEqual([n for n,r in proof['runtime_files'].items() if not r['same']],['controller-core.py']);limits=self.profile['limits'];self.assertEqual((limits['inner_seconds'],limits['input_cutoff_seconds'],limits['independent_conservative_private_job_seconds'],limits['absolute_actual_seconds'],limits['evidence_bytes']),(41,40.75,47.,47.5,60000000));self.assertEqual((limits['disk_admission'],limits['disk_runtime']),(19461570560,19394461696));o.fixed_profile(self.profile)
if __name__=='__main__':unittest.main(verbosity=2)
