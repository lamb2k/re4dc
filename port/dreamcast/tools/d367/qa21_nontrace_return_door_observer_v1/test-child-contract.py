"""Only NEW fixed output-contract source tests; no guest/nativeprocess/RAM/input."""
import ast,contextlib,hashlib,importlib.util,io,json,os,pathlib,tempfile,unittest
P=pathlib.Path(__file__).parent;BASE=P.parent/'qa21_nontrace_observer_lifecycle_v1';F63=P.parent/'qa21_nontrace_guest_telemetry_v1'
def load(n,f):
 s=importlib.util.spec_from_file_location(n,f);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def resolve(n):
 if os.name=='nt':return pathlib.Path(n)
 w=pathlib.PureWindowsPath(n);return (pathlib.Path('/mnt/c') if w.drive.lower()=='c:' else pathlib.Path('/'))/pathlib.Path(*w.parts[1:])
def sha(f):return hashlib.sha256(pathlib.Path(f).read_bytes()).hexdigest()
def fn(f,n):return ast.dump(next(v for v in ast.parse(f.read_text()).body if isinstance(v,ast.FunctionDef) and v.name==n),include_attributes=False)
o=load('contract_outer',P/'outer-driver.py');inner=load('contract_inner',P/'inner-adapter.py');profile=json.loads((P/'guest-profile-v2.json').read_text())
class Contract(unittest.TestCase):
 def test_actual_parser_door_only_no_fallback_default_or_arbitrary_name(self):
  args=['--profile','p','--profile-sha256','p','--tools-sha256','t','--mode','return-door01','--seed','s'];self.assertEqual(o.parse_args(args).mode,'return-door01')
  for mode in ['cold-shoot01','cinematic01','return-door-observer01']:
   with contextlib.redirect_stderr(io.StringIO()):
    with self.assertRaises(SystemExit):o.parse_args(args[:7]+[mode]+args[8:])
  with contextlib.redirect_stderr(io.StringIO()):
   with self.assertRaises(SystemExit):o.parse_args(args+['--output-name','old'])
  for mode in ['cold-shoot01','cinematic01']:
   with self.assertRaises(ValueError):inner.validate_role(profile,mode,pathlib.Path('seed'))
  with self.assertRaises(ValueError):inner.validate_role(profile,'return-door01',None)
 def test_fixed_new_paths_create_only_new_control_and_preserve_old_failed_namespace(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);old=root/'return-door01';old.mkdir();(old/'failed.txt').write_bytes(b'preserve-failed');(root/'OWNED-BY.json').write_text(json.dumps({'lane':'qa21-combined-regression','programme':o.PROGRAM,'image':o.IMAGE}));cap,control,marker=o.output_paths({'evidence_root':str(root)},'return-door01');self.assertEqual(cap,root/'return-door-observer01');self.assertEqual(control,root/'return-door-observer01-control');self.assertFalse(cap.exists());self.assertTrue(control.is_dir());self.assertTrue(marker.is_file());self.assertEqual((old/'failed.txt').read_bytes(),b'preserve-failed')
 def test_existing_new_output_or_control_refuses_before_marker_mutation(self):
  for name in ['return-door-observer01','return-door-observer01-control']:
   with tempfile.TemporaryDirectory() as d:
    root=pathlib.Path(d);target=root/name;target.mkdir();(target/'keep').write_bytes(b'existing')
    with self.assertRaisesRegex(RuntimeError,'preserve existing'):o.output_paths({'evidence_root':str(root)},'return-door01')
    self.assertFalse((root/'OWNED-BY.json').exists());self.assertEqual((target/'keep').read_bytes(),b'existing')
 def test_inner_actual_cap_expression_refuses_old_failed_and_other_paths(self):
  tree=ast.parse((P/'inner-adapter.py').read_text());node=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and isinstance(n.test,ast.Compare) and isinstance(n.test.left,ast.Name) and n.test.left.id=='cap' and isinstance(n.test.ops[0],ast.NotEq));code=compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'<actual-inner-output-check>','exec');root=pathlib.Path(profile['evidence_root']);exec(code,{'cap':root/'return-door-observer01','pathlib':pathlib,'profile':profile})
  for cap in [root/'return-door01',root/'cold-shoot01',root/'elsewhere']:
   with self.assertRaisesRegex(RuntimeError,'fixed child output'):exec(code,{'cap':cap,'pathlib':pathlib,'profile':profile})
 def test_strict_original_parent_profile_and_alias_validators_remain_identical(self):
  for n in ['validate_seed','no_alias','fixed_profile','postflight']:self.assertEqual(fn(P/'outer-driver.py',n),fn(BASE/'outer-driver.py',n),n)
  self.assertEqual(sha(P/'guest-profile-v2.json'),'4c386fa2fd826d2b04f7bf5b8696dca3e339dd92485c11b8ec91b863d21ce99b');cp=json.loads((resolve(profile['evidence_root'])/'cold-shoot01/checkpoint.json').read_text());q=json.loads((resolve(profile['evidence_root'])/'cold-shoot01-control/qualification.json').read_text());self.assertTrue(q['qualified']);self.assertEqual(q['profile_sha256'],sha(P/'guest-profile-v2.json'));self.assertEqual(cp['audit']['frame'],533);self.assertEqual(cp['audit']['state_sha256'],'e81e572fefa7a94771ecde68c1d38456e4a51d62d3b3641ecd52de0db51b0c75')
 def test_reviewed_observer_pair_native_input_deadline_job_and_policy_bytes_exact(self):
  for n in ['observe.py','observer-v2.py','windows-backend.py','guest-supervisor-core.py','input-deadlines.py','controller-core.py','policies.py','layout-contract.py','capture-budget.py']:self.assertEqual((P/n).read_bytes(),(BASE/n).read_bytes(),n)
  o.fixed_profile(profile);expected=(BASE/'inner-adapter.py').read_text().replace("def validate_role(profile,mode,seed):\n roles=","def validate_role(profile,mode,seed):\n if mode!='return-door01':raise ValueError('this child seal allows only return-door01')\n roles=").replace(" profile=json.loads(a.profile.read_text());role=validate_role(profile,a.mode,a.seed);cap=a.cap\n"," profile=json.loads(a.profile.read_text());role=validate_role(profile,a.mode,a.seed);cap=a.cap\n if cap!=pathlib.Path(profile['evidence_root'])/'return-door-observer01':raise RuntimeError('wrong fixed child output contract')\n");self.assertEqual((P/'inner-adapter.py').read_text(),expected)
 def test_actual_startup_log_reads_and_literal_local_dependencies_present(self):
  t=ast.parse((P/'inner-adapter.py').read_text());nodes=[n for n in ast.walk(t) if isinstance(n,ast.Assign) and any(isinstance(a,ast.Name) and a.id in {'logs','syms'} for a in n.targets)];self.assertEqual(len(nodes),2);env={'P':P,'json':json};exec(compile(ast.fix_missing_locations(ast.Module(body=sorted(nodes,key=lambda n:n.lineno),type_ignores=[])),'<actual-symbol-read>','exec'),env);self.assertEqual(env['syms'],'0x3db360 0x3eb364 0x3eb360');self.assertEqual((P/'exact-log-symbols.json').read_bytes(),(F63/'exact-log-symbols.json').read_bytes())
  for file in P.glob('*.py'):
   if file.name.startswith(('test-','run-')):continue
   for n in ast.walk(ast.parse(file.read_text())):
    name=n.right.value if isinstance(n,ast.BinOp) and isinstance(n.op,ast.Div) and isinstance(n.left,ast.Name) and n.left.id=='P' and isinstance(n.right,ast.Constant) else n.args[0].value if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='with_name' and len(n.args)==1 and isinstance(n.args[0],ast.Constant) else None
    if isinstance(name,str) and name!='source-manifest.json':self.assertTrue((P/name).is_file(),(file.name,name))
 def test_actual_failed_evidence_remains_false_and_separate_from_accepted_parent(self):
  root=resolve(profile['evidence_root']);q=json.loads((root/'return-door01-control/qualification.json').read_text());self.assertFalse(q['qualified']);self.assertEqual(q['identity']['pid'],58596);self.assertEqual(sha(root/'return-door01/data/disc.state'),'640c9dadddf5b42a5b9b58e2781cbda3b797b0ac439b0ae78b180a10f7986ee0');self.assertFalse((root/'return-door-observer01').exists());self.assertFalse((root/'return-door-observer01-control').exists())
if __name__=='__main__':unittest.main(verbosity=2)
