"""V3 focused startup/cleanup source review only. No imports/tests/native actions."""
import ast,datetime,hashlib,json,pathlib
Q=pathlib.Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-qa21-death-repair\port\dreamcast\tools\d367');P=Q/'qa21_native_job_inventory_v3';B=Q/'qa21_native_job_inventory_v2';OUT=pathlib.Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();fn=lambda p,n:next(x for x in ast.walk(ast.parse(p.read_text())) if isinstance(x,ast.FunctionDef) and x.name==n);dump=lambda n:ast.dump(n,include_attributes=False)
assert sha(P/'manifest.json')=='85ab97fee4b8d41dc797c8bb7f393f6e2218f09f7f039648cb0a831b28151b65';assert sha(P/'SOURCE_MANIFEST.json')=='fdb5acc9d0f295c6888b996f688e220eb96eb8c01e288e4096eb40a5f936cc51';assert sha(P/'LAUNCH_REQUEST.json')=='d519e038c434f55b35c65b7456377addf8e1a383d138b11dcba72686a7bafc02'
pins={}
for label,file in [('integrity','SOURCE_MANIFEST.json'),('runtime','manifest.json')]:
 rows=[]
 for row in json.loads((P/file).read_text())['files']:
  p=pathlib.Path(row['path']) if row.get('absolute') else P/row['path'];assert sha(p)==row['sha256'],row['path']
  if 'bytes' in row:assert p.stat().st_size==row['bytes']
  rows.append(dict(path=row['path'],sha256=sha(p),bytes=p.stat().st_size))
 pins[label]=rows
parents={}
for dirname in ['qa21_native_job_inventory_v1','qa21_native_job_inventory_v2']:
 parent=Q/dirname;m=json.loads((parent/'SOURCE_MANIFEST.json').read_text())
 for r in m['files']:assert sha(parent/r['path'])==r['sha256']
 parents[dirname]=dict(manifest=sha(parent/'SOURCE_MANIFEST.json'),pins=len(m['files']))
byteexact=['supervisor.py','inventory.py','frozen-native-reference-api.py','frozen-windows-backend.py']
for n in byteexact:assert (P/n).read_bytes()==(B/n).read_bytes(),n
oldcoord=(B/'coordinator.py').read_text();expected=oldcoord.replace("cleanup=load('cleanup',P/'cleanup.py');inventory=", "startup=load('startup',P/'startup.py');cleanup=load('cleanup',P/'cleanup.py');inventory=").replace("inner=backend.spawn_waiting(cfg['inner_argv'],job)","inner=startup.spawn_retained(backend,cfg['inner_argv'],job)").replace("        pinned=getattr(backend,'inner_identity',None)","        inner=backend.inner  # Includes Popen whose startup raised before returning.\n        pinned=getattr(backend,'inner_identity',None)")
assert (P/'coordinator.py').read_text()==expected
for name in ['note','failure','retained_cleanup','disarm_if_proven']:assert dump(fn(P/'cleanup.py',name))==dump(fn(B/'cleanup.py',name)),name
startup=fn(P/'startup.py','spawn_retained');text=ast.unparse(startup)
assert text.index('backend.inner = proc')<text.index('backend.info(')<text.index('AssignProcessToJobObject')<text.index('IsProcessInJob')
assert not any(isinstance(n,ast.Attribute) and n.attr in ['Close','close','terminate','wait'] for n in ast.walk(startup))
assert 'backend.inner_identity = None' in text and 'stdin=subprocess.PIPE' in text and 'creationflags=subprocess.CREATE_NO_WINDOW' in text
job=ast.unparse(fn(P/'cleanup.py','job_cleanup'));assert 'if pinned is not None else None' in job and "'original_live_pin_available': pinned is not None" in job and 'status == 0' in job and "state['private_job_empty'] and state['inner_finalized']" in job
coverage=[]
for platform in ['linux','windows']:
 p=P/('receipt-'+platform+'.json');r=json.loads(p.read_text());assert r['test_count']==5 and r['status']=='PASS' and r['tests_sha256']==sha(P/'test_startup.py') and r['runtime_manifest_sha256']==sha(P/'manifest.json');coverage.append(dict(platform=platform,sha256=sha(p),retained_tests=5,current_test_manifest_pins=True,rerun=False))
plan=(P/'NATIVE_INVENTORY_PLAN.md').read_text();assert 'Root accepts the operational contract' in plan and 'persistent native denial is recorded HOLD' in plan
report=dict(scope='SOURCE/hash/AST/retainedreceipt only; no imports/tests/nativequery/launch/image/state/preflight/allocation',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),candidate='ac57068332ecf51467c552a80dd2334e2fe7fe2c',disposition='CLEAR focused v3 startup-retention correction under root conditional native-success/HOLD time contract; not native allocation',pins=pins,prior_immutable_pins=parents,byteexact_v2=byteexact,coordinator_exact_only_startup_load_call_and_finally_recovery=True,unchanged_cleanup_functions=['note','failure','retained_cleanup','disarm_if_proven'],startup_source=ast.get_source_segment((P/'startup.py').read_text(),startup),retained_coverage=coverage,contract=dict(native_success_child_seconds=5,native_success_parent_seconds=10,persistent_native_denial='HOLD; retain guards/owned handles, no unconditional hardboundPASS',new_containment=False),limitations=['Missingoriginalpathpin staysidentityNone/original_live_pin_availableFalse; creation-ownedhandle mayclose onlyafterretainedsignaledtimestamps+emptyjob','Startupfailure originalerror remainsqualifiedFalse, safeclosure isnotfixturePASS','Noactualnativeinteroperability or causeof55368 established','Oldv1/v2BLOCK evidence preserved; mainaloneactualfixture/allocation'])
(OUT/'review-ac570.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(disposition=report['disposition'],integritypins=len(pins['integrity']),runtimepins=len(pins['runtime']),byteexactv2=len(byteexact),retained_tests_each=5)))