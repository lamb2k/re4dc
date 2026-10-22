"""Read-only hashes/AST only. Never imports candidate modules or launches children."""
import ast,datetime,hashlib,json,pathlib
Q=pathlib.Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-qa21-death-repair\port\dreamcast\tools\d367')
P=Q/'qa21_nontrace_return_door_v1'; V=Q/'qa21_nontrace_guest_telemetry_v1'; OUT=pathlib.Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((P/'source-manifest.json').read_text());refs=json.loads((P/'referenced-readonly-files.json').read_text());profile=json.loads((P/'guest-profile-v2.json').read_text())
records=[]
for name,pin in manifest['files'].items():
 path=P/name;records.append(dict(path=name,absolute=pathlib.PureWindowsPath(name).is_absolute(),exists=path.is_file(),bytes=path.stat().st_size,sha256=sha(path),match=path.stat().st_size==pin['bytes'] and sha(path)==pin['sha256']))
assert all(x['match'] for x in records)
assert len(records)==83 and sum(x['absolute'] for x in records)==56
runtime=['outer-driver.py','inner-adapter.py','windows-backend.py','guest-supervisor-core.py','input-deadlines.py','controller-core.py','policies.py','observe.py','observer-v2.py','layout-contract.py','capture-budget.py']
identity={name:dict(base=sha(V/name),child=sha(P/name),same=(V/name).read_bytes()==(P/name).read_bytes()) for name in runtime}
assert [n for n,r in identity.items() if not r['same']]==['controller-core.py']
assert (P/'controller-core.py').read_bytes()==(V/'controller-core.py').read_bytes().replace(b"key='a';hold=.2;self.attempts+=1",b"key='a';hold=.15;self.attempts+=1")
relative=[]
for name in runtime:
 for node in ast.walk(ast.parse((P/name).read_text())):
  if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Div) and isinstance(node.left,ast.Name) and node.left.id=='P' and isinstance(node.right,ast.Constant) and isinstance(node.right.value,str):
   target=node.right.value;relative.append(dict(module=name,line=node.lineno,target=target,exists=(P/target).is_file(),pinned_locally=target in manifest['files']))
missing=[r for r in relative if not r['exists']]
assert {r['target'] for r in missing}=={'exact-log-symbols.json'}
logref=[n for n in refs['files'] if pathlib.PureWindowsPath(n).name=='exact-log-symbols.json'];assert len(logref)==1
inner=(P/'inner-adapter.py').read_text(); lines=inner.splitlines()
threadline=next(i+1 for i,l in enumerate(lines) if 'thread.start()' in l)
readline=next(i+1 for i,l in enumerate(lines) if "logs=json.loads((P/'exact-log-symbols.json')" in l)
runnerline=next(i+1 for i,l in enumerate(lines) if 'try:runner.main()' in l)
assert threadline<readline<runnerline
requestpath=Q/'qa21_nontrace_run_preparation/return-door-child-v1/LAUNCH-REQUEST.json';request=json.loads(requestpath.read_text());assert sha(requestpath)=='dadfedacf34803b339fa667854c6aa9d7bb570fbccb3db3e16794ed143b9c27d'
assert request['argv'][-4:]==['--mode','return-door01','--seed',request['seed']['path']]
assert sha(P/'guest-profile-v2.json')=='4c386fa2fd826d2b04f7bf5b8696dca3e339dd92485c11b8ec91b863d21ce99b'
assert sha(P/'source-manifest.json')=='8d06f482b0a4587aef90a610e2b2db132fa0fb9a09c015496f7f93e836d5f500'
cp=json.loads(pathlib.Path(request['seed']['path'],'checkpoint.json').read_text());qual=json.loads(pathlib.Path(request['seed']['path']).parent.joinpath('cold-shoot01-control/qualification.json').read_text())
assert qual['qualified'] is True and qual['profile_sha256']==sha(P/'guest-profile-v2.json')
assert cp['audit']['state_sha256']==request['seed']['state_sha256'] and cp['audit']['frame']==533
out=dict(scope='Independent SOURCE ONLY: no imports/tests/nativechildren/fullpreflight/build/image/guest/seal mutation',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),candidate_commit='514fe3b5a61c370addd8719eee32f6aa8ae079be',disposition='BLOCK: child-local exact-log-symbols.json absent',profile_sha256=sha(P/'guest-profile-v2.json'),tools_sha256=sha(P/'source-manifest.json'),request_sha256=sha(requestpath),manifest=records,runtime_identity=identity,direct_P_relative_literals=relative,blocking_missing=missing,existing_external_symbol_pin=logref[0],order=dict(thread_start=threadline,missing_read=readline,runner_main_try=runnerline),parent_source_metadata=dict(qualified=True,same_profile=True,state=cp['audit']['state_sha256'],frame=cp['audit']['frame']),limitations=['Static launch-blocking proof, not a guest execution','Absolute manifest pin verifies v1 file but does not redirect child P-relative read','Retained parent/test/resource receipts inspected, not rerun','Runtime timing/exit/job/resource byte identity confirmed only; no new door qualification'])
(OUT/'review-514fe3.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(disposition=out['disposition'],manifest=len(records),unchanged_runtime=10,missing=missing,order=out['order'])))