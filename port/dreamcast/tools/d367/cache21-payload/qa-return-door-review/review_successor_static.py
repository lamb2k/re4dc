"""Successor static source/hash/AST review; no candidate imports/test execution."""
import ast,datetime,hashlib,json,pathlib
Q=pathlib.Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-qa21-death-repair\port\dreamcast\tools\d367');P=Q/'qa21_nontrace_return_door_v2';B=Q/'qa21_nontrace_return_door_v1';V=Q/'qa21_nontrace_guest_telemetry_v1';OUT=pathlib.Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((P/'source-manifest.json').read_text());profile=json.loads((P/'guest-profile-v2.json').read_text());reqpath=Q/'qa21_nontrace_run_preparation/return-door-child-v2/LAUNCH-REQUEST.json';req=json.loads(reqpath.read_text());records=[]
for name,pin in manifest['files'].items():
 p=P/name;actual=sha(p);assert p.stat().st_size==pin['bytes'] and actual==pin['sha256'],name
 records.append(dict(path=name,bytes=p.stat().st_size,sha256=actual,absolute=pathlib.PureWindowsPath(name).is_absolute()))
assert len(records)==108 and sum(r['absolute'] for r in records)==84
assert sha(P/'source-manifest.json')=='e25ba6a875a64d42fa44a1553e1d55b8f4055c404837e95af2fa23f54b5ead37'
assert sha(P/'guest-profile-v2.json')=='4c386fa2fd826d2b04f7bf5b8696dca3e339dd92485c11b8ec91b863d21ce99b'
assert sha(reqpath)=='3556d4f53fc05d48dbf5fd32227be15429a4164972739d39f8f76486278b134a'
runtime=['outer-driver.py','inner-adapter.py','windows-backend.py','guest-supervisor-core.py','input-deadlines.py','controller-core.py','policies.py','observe.py','observer-v2.py','layout-contract.py','capture-budget.py'];identities={};dependencies=[]
for name in runtime:
 assert (P/name).read_bytes()==(B/name).read_bytes(),name
 expected=(V/name).read_bytes()
 if name=='controller-core.py':expected=expected.replace(b"key='a';hold=.2;self.attempts+=1",b"key='a';hold=.15;self.attempts+=1")
 assert expected==(P/name).read_bytes(),name
 identities[name]=dict(child=sha(P/name),blocked=sha(B/name),accepted_v1=sha(V/name))
 for node in ast.walk(ast.parse((P/name).read_text())):
  target=None
  if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Div) and isinstance(node.left,ast.Name) and node.left.id=='P' and isinstance(node.right,ast.Constant) and isinstance(node.right.value,str):target=node.right.value
  elif isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='with_name' and len(node.args)==1 and isinstance(node.args[0],ast.Constant):target=node.args[0].value
  if target is not None:
   assert (P/target).is_file(),(name,node.lineno,target)
   assert target=='source-manifest.json' or target in manifest['files'],target
   dependencies.append(dict(module=name,line=node.lineno,target=target,sha256=sha(P/target),pinned=target in manifest['files']))
assert not (B/'exact-log-symbols.json').exists()
assert sha(B/'source-manifest.json')=='8d06f482b0a4587aef90a610e2b2db132fa0fb9a09c015496f7f93e836d5f500'
assert (P/'exact-log-symbols.json').read_bytes()==(V/'exact-log-symbols.json').read_bytes()
assert sha(P/'exact-log-symbols.json')=='b47debb79a4f68c9e07554fd77679468bf71941df80981d3bce86254a3a72b29'
symbols=json.loads((P/'exact-log-symbols.json').read_text());assert symbols['elf_sha256']==profile['fixed_runtime']['elf_sha256']
for name,size in [('_re4dc_logbuf',65536),('_re4dc_log_head',4),('_re4dc_stage',4)]:
 rows=symbols['symbols'][name];assert len(rows)==1 and rows[0]['bytes']==size and rows[0]['type']=='STT_OBJECT' and 0x8c000000<=rows[0]['address']<=0x8d000000-size
# Check actual startup AST identity; do not compile/exec the source assignments.
assigns=lambda p:[ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(p.read_text())) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('logs','syms') for t in n.targets)]
assert len(assigns(P/'inner-adapter.py'))==2 and assigns(P/'inner-adapter.py')==assigns(V/'inner-adapter.py')
syms=' '.join(hex(symbols['symbols'][n][0]['address']-0x8c000000) for n in ['_re4dc_logbuf','_re4dc_log_head','_re4dc_stage'])
assert req['argv'][-4:]==['--mode','return-door01','--seed',req['seed']['path']] and req['automatic_retry'] is False
assert req['argv'][1]==str(P/'outer-driver.py') and req['argv'][3]==str(P/'guest-profile-v2.json')
assert req['argv'][5]==sha(P/'guest-profile-v2.json') and req['argv'][7]==sha(P/'source-manifest.json')
cp=json.loads(pathlib.Path(req['seed']['path'],'checkpoint.json').read_text());qual=json.loads(pathlib.Path(req['seed']['path']).parent.joinpath('cold-shoot01-control/qualification.json').read_text());assert qual['qualified'] is True and qual['profile_sha256']==sha(P/'guest-profile-v2.json') and qual['program_sha256']==profile['fixed_runtime']['program_sha256']
assert cp['audit']['state_sha256']==req['seed']['state_sha256'] and cp['audit']['frame']==533
qualification=json.loads((P/'source-qualification.json').read_text());coverage=[]
for platform,pin in qualification['new_tests'].items():
 receiptpath=P/pin['path'];assert sha(receiptpath)==pin['sha256'];receipt=json.loads(receiptpath.read_text());assert receipt['returncode']==0
 for name,h in receipt['sources'].items():assert sha(P/name)==h,(platform,name)
 coverage.append(dict(platform=platform,receipt=pin['path'],sha256=sha(receiptpath),retained_tests=5,current_source_hashes=True,rerun=False))
pre=Q/'qa21_nontrace_run_preparation/return-door-child-v2/readonly-preflight.json';assert sha(pre)=='708841c129993c50e3cde0ca244d6f5fe1f5eb9ee229310f3c34b4fc24c0ce6c'
report=dict(scope='SOURCE/hash/AST only; no tests/imports/nativechildren/preflight/build/image/guest/sealmutation',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),candidate='a47c7204f1d49b34925582440ddb939ab7ba1e4c',disposition='CLEAR bounded source review; original514BLOCK preserved',manifest_sha256=sha(P/'source-manifest.json'),profile_sha256=sha(P/'guest-profile-v2.json'),request_sha256=sha(reqpath),verified_files=records,runtime_identical_to514=identities,local_dependencies=dependencies,actual_startup_assignments_AST_exact_v1=True,source_computed_syms=syms,local_symbols_sha256=sha(P/'exact-log-symbols.json'),retained_source_coverage=coverage,retained_preflight_sha256=sha(pre),preflight_rerun=False,parent=dict(state=cp['audit']['state_sha256'],frame=533,qualified=True,sameprofile=True),limits=profile['limits'],input_bounds=profile['input_pulse_bounds'],limitations=['Static read target now exists/pinned; no execution/door acceptance follows','Existing symbol-read ordering remains unchanged; corrupt/missing tools refuse fullmanifest before imports','Parent/guardian identity checked; actual checkpoint.verify/nativepreflight not rerun here','Main alone owns allocation and fresh peer/resource/native/source admission'])
(OUT/'review-a47c7204.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(disposition=report['disposition'],pins=len(records),absolute=84,runtime_identical=11,local_literal_dependencies=len(dependencies),syms=syms)))