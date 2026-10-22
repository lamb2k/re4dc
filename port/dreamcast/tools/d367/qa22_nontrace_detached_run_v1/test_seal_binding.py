"""Focused changed binding checks; AST/pure functions/small metadata only."""
import argparse,ast,copy,hashlib,json,ntpath,pathlib,tempfile,unittest
P=pathlib.Path(__file__).parent;BASE=P.parent/'qa21_nontrace_detached_adapter_v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(n):return json.loads((P/n).read_text())
def extracted(file,name,env):
 tree=ast.parse((P/file).read_text());node=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name);exec(compile(ast.Module(body=[node],type_ignores=[]),file,'exec'),env);return env[name]
def literal(file,name):
 tree=ast.parse((P/file).read_text());return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
class Refusal(ValueError):pass
class Tests(unittest.TestCase):
 def test_runtime_seal_covers_every_mirror_and_exact_reviewed_bytes(self):
  provenance=read('SEALED_SOURCE_PROVENANCE.json');manifest=read('source-manifest.json');self.assertEqual(provenance['code_delta'],{});self.assertEqual(len(provenance['mirrored_runtime_files']),28)
  self.assertEqual(sha(BASE/'SOURCE_ONLY_MANIFEST.json'),provenance['frozen_source_manifest_sha256'])
  for name,pin in provenance['mirrored_runtime_files'].items():
   with self.subTest(name=name):self.assertEqual((P/name).read_bytes(),(BASE/name).read_bytes());self.assertEqual(sha(P/name),pin['sha256']);self.assertEqual(manifest['files'][name],pin)
  for name,pin in manifest['files'].items():self.assertEqual(sha(P/name),pin['sha256']);self.assertEqual((P/name).stat().st_size,pin['bytes'])
 def test_literal_argv_accepted_by_actual_parser_and_default_off(self):
  parse=extracted('outer-driver.py','parse_args',{'argparse':argparse,'pathlib':pathlib});r=read('LAUNCH_REQUEST.json');a=parse(r['argv'][3:]);self.assertTrue(a.execute_root_allocation);self.assertEqual(a.mode,'return-door01');self.assertEqual(a.tools_sha256,sha(P/'source-manifest.json'));self.assertEqual(a.profile_sha256,sha(P/'guest-profile-v2.json'));self.assertEqual(a.root_allocation_sha256,sha(P/'FUTURE_ROOT_AUTHORITY_BYTES.json'))
  self.assertFalse(parse(r['argv'][3:-1]).execute_root_allocation)
  self.assertEqual(ntpath.basename(str(a.profile)),'guest-profile-v2.json');self.assertEqual(ntpath.dirname(r['argv'][2]),ntpath.dirname(str(a.profile)));self.assertEqual(ntpath.basename(ntpath.dirname(r['argv'][2])),P.name)
 def test_actual_allocation_schema_accepts_exact_template_and_rejects_changed_fields(self):
  env={'ntpath':ntpath};canonical=extracted('reference-hooks/native_reference_api.py','canonical',env)
  env={'Path':pathlib.Path,'hashlib':hashlib,'json':json,'canonical':canonical,'PROFILE':literal('reference-hooks/parent_reference_broker.py','PROFILE'),'SOURCE':literal('reference-hooks/parent_reference_broker.py','SOURCE'),'Refusal':Refusal}
  proof=extracted('reference-hooks/parent_reference_broker.py','allocation_proof',env);r=read('LAUNCH_REQUEST.json');t=read('FUTURE_ROOT_AUTHORITY_BYTES.json');contract=sha(P/'reference-hooks/COLLECTOR_CONTRACT.json');runner=sha(P/'reference-hooks/checkpoint_runner18.child.py');tools=sha(P/'source-manifest.json')
  result=proof(P/'FUTURE_ROOT_AUTHORITY_BYTES.json',sha(P/'FUTURE_ROOT_AUTHORITY_BYTES.json'),r['cap'],r['control']+'/reference-hooks',contract,runner,tools);self.assertEqual(result['contents'],t)
  for field,value in [('tools_sha256','0'*64),('profile_sha256','0'*64),('runner_sha256','0'*64),('contract_sha256','0'*64),('cap',t['cap']+'x'),('control',t['control']+'x'),('attempt_limit',2),('private_job_seconds',48.0),('absolute_actual_seconds',48.0),('input_cutoff_seconds',41.0),('inner_seconds',42),('evidence_cap_bytes',60000001),('runtime_floor_bytes',0),('semantic_mode','cold-shoot01'),('tools_source','fc8f707efd980ac3cb98de529e52c5ec03c90286'),('attempt_limit',True)]:
   with self.subTest(field=field,value=value),tempfile.TemporaryDirectory() as tmp:
    changed=copy.deepcopy(t);changed[field]=value;path=pathlib.Path(tmp)/'inert-template-test.json';path.write_text(json.dumps(changed))
    with self.assertRaises(Refusal):proof(path,sha(path),r['cap'],r['control']+'/reference-hooks',contract,runner,tools)
 def test_wrong_template_hash_and_foreign_authority_path_refuse(self):
  canonical=extracted('reference-hooks/native_reference_api.py','canonical',{'ntpath':ntpath});env={'Path':pathlib.Path,'hashlib':hashlib,'json':json,'canonical':canonical,'PROFILE':literal('reference-hooks/parent_reference_broker.py','PROFILE'),'SOURCE':literal('reference-hooks/parent_reference_broker.py','SOURCE'),'Refusal':Refusal};proof=extracted('reference-hooks/parent_reference_broker.py','allocation_proof',env);r=read('LAUNCH_REQUEST.json')
  with self.assertRaises(Refusal):proof(P/'FUTURE_ROOT_AUTHORITY_BYTES.json','0'*64,r['cap'],r['control']+'/reference-hooks',sha(P/'reference-hooks/COLLECTOR_CONTRACT.json'),sha(P/'reference-hooks/checkpoint_runner18.child.py'),sha(P/'source-manifest.json'))
  authority=pathlib.Path(r['root_allocation_path']);env={'Path':pathlib.Path,'ALLOCATION':authority};fn=extracted('wiring-backend.py','validate_authority',env)
  with self.assertRaises(RuntimeError):fn(P/'FUTURE_ROOT_AUTHORITY_BYTES.json','0'*64,'0'*64,r['cap'],r['control'])
 def test_new_output_fields_reference_contract_and_template_agree(self):
  r=read('LAUNCH_REQUEST.json');t=read('FUTURE_ROOT_AUTHORITY_BYTES.json');c=read('reference-hooks/COLLECTOR_CONTRACT.json');self.assertEqual(c['new_output_contract_proposal']['output_name'],'return-door-domains02');self.assertEqual(c['new_output_contract_proposal']['control_name'],'return-door-domains02-control');self.assertEqual(ntpath.normcase(ntpath.normpath(r['cap'])),t['cap']);self.assertEqual(ntpath.normcase(ntpath.normpath(r['control']+'/reference-hooks')),t['control']);self.assertEqual(ntpath.normcase(ntpath.dirname(c['proposed_phase_rules']['staged_owned']['paths'][-1])),t['cap'])
  tree=ast.parse((P/'wiring-backend.py').read_text());value=next(n.value.args[0].value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='ALLOCATION' for x in n.targets));self.assertEqual(value,r['root_allocation_path'])
 def test_exact_seed_profile_reference_and_guards_stay_frozen(self):
  r=read('LAUNCH_REQUEST.json');s=read('SEED_CONTRACT.json');self.assertEqual((r['seed_state_sha256'],r['seed_frame']),(s['state_sha256'],s['frame']));self.assertEqual(s['frame'],533);self.assertEqual(r['profile_sha256'],'4c386fa2fd826d2b04f7bf5b8696dca3e339dd92485c11b8ec91b863d21ce99b');self.assertEqual(r['bounds'],read('guest-profile-v2.json')['limits'])
  for file in ('outer-driver.py','inner-adapter.py','guest-supervisor-core.py','windows-backend.py','reference-hooks/parent_reference_broker.py','reference-hooks/reference_collector.py','reference-hooks/native_reference_api.py'):self.assertEqual((P/file).read_bytes(),(BASE/file).read_bytes())
 def test_both_actual_counter_bindings_and_native_footprint_are_sealed(self):
  m=read('source-manifest.json');self.assertIn('native-process-count.py',m['files']);self.assertIn('evidence-footprint-native.py',m['files']);backend=(P/'windows-backend.py').read_text();runner=(P/'reference-hooks/checkpoint_runner18.child.py').read_text();self.assertIn("parent/'native-process-count.py'",backend);self.assertIn("parent.parent/'native-process-count.py'",runner)
  for file in ('outer-driver.py','inner-adapter.py'):self.assertIn("P/'evidence-footprint-native.py'",(P/file).read_text())
 def test_known_missing_image_is_explicit_block_and_no_authority_created(self):
  r=read('LAUNCH_REQUEST.json');metadata=read('IMAGE_PATH_METADATA.json');missing={row['path'] for row in metadata['rows'] if not row['exists'] and row['path'].endswith('track03.iso')};self.assertEqual(set(r['current_missing_aliases']),missing);self.assertEqual(len(missing),3);self.assertEqual(r['allocation_status'],'UNALLOCATED_BLOCKED_MISSING_EXACT_QA_IMAGE');self.assertFalse(r['actual_authority_file_created']);self.assertFalse(r['guest_allocated'])
if __name__=='__main__':unittest.main()
