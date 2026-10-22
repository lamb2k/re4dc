"""Source-only AST/hash reviewer. Never imports candidate modules/test/Windows APIs."""
import ast,datetime,hashlib,json,pathlib
Q=pathlib.Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-qa21-death-repair\port\dreamcast\tools\d367');P=Q/'qa21_nontrace_observer_lifecycle_v1';B=Q/'qa21_nontrace_return_door_v2';OUT=pathlib.Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((P/'SOURCE_ONLY_MANIFEST.json').read_text());assert sha(P/'SOURCE_ONLY_MANIFEST.json')=='8f2d76dd31d29e7f093cd26b4287294cfc101c010b211f0287fafde58cd40a7c';pins=[]
for name,row in manifest['files'].items():
 p=P/name;assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],name;pins.append(dict(path=name,bytes=p.stat().st_size,sha256=sha(p)))
assert not (P/'source-manifest.json').exists()
runtime=['outer-driver.py','inner-adapter.py','windows-backend.py','guest-supervisor-core.py','input-deadlines.py','controller-core.py','policies.py','observe.py','observer-v2.py','layout-contract.py','capture-budget.py'];identities={n:dict(old=sha(B/n),new=sha(P/n),same=(B/n).read_bytes()==(P/n).read_bytes()) for n in runtime};assert [n for n,r in identities.items() if not r['same']]==['observe.py','observer-v2.py']
for n in ['guest-profile-v2.json','exact-log-symbols.json']:assert (P/n).read_bytes()==(B/n).read_bytes()
methods=lambda path,cls:{n.name:n for c in ast.parse(path.read_text()).body if isinstance(c,ast.ClassDef) and c.name==cls for n in c.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
dump=lambda n:ast.dump(n,include_attributes=False)
unchanged=[]
for file,cls,changed in [('observe.py','Observer',{'sample'}),('observer-v2.py','Reader',{'read','field'})]:
 old=methods(B/file,cls);new=methods(P/file,cls);assert old.keys()==new.keys()
 for name in old:
  if name not in changed:assert dump(old[name])==dump(new[name]),name;unchanged.append(file+':'+name)
sample=methods(P/'observe.py','Observer')['sample'];handlers=[n for n in ast.walk(sample) if isinstance(n,ast.ExceptHandler)];assert len(handlers)==1 and dump(handlers[0].type)==dump(ast.parse('a.RAMRangeError',mode='eval').body)
loops=[n for n in ast.walk(sample) if isinstance(n,ast.For)];assert len(loops)==1 and dump(loops[0].iter)==dump(ast.parse('range(4)',mode='eval').body)
phasecalls=[ast.unparse(n.args[0]) for n in ast.walk(sample) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='require_live'];assert len(phasecalls)==3
reader=methods(P/'observer-v2.py','Reader');read=reader['read'];assert 'raise RAMRangeError(addr, fmt)' in ast.unparse(read);assert 'self.raw(addr, size)' in ast.unparse(read)
readbody=read.body;assert isinstance(readbody[1],ast.If) and isinstance(readbody[2],ast.Assign)
errclass=next(n for n in ast.parse((P/'observer-v2.py').read_text()).body if isinstance(n,ast.ClassDef) and n.name=='RAMRangeError');assert [ast.unparse(b) for b in errclass.bases]==['ValueError']
text=(P/'observe.py').read_text();assert "'valid':False,'coherent':False" in text and "'global':None,'player':None,'qa_frames':None,'qa_flags':None" in text and 'self.buffer=None;self.last=None' in text
qualification=json.loads((P/'source-qualification.json').read_text());receipts=[]
for platform,pin in qualification['tests'].items():
 f=P/pin['path'];assert sha(f)==pin['sha256'];r=json.loads(f.read_text());assert r['returncode']==0
 for n,h in r['sources'].items():assert sha(P/n)==h,(platform,n)
 receipts.append(dict(platform=platform,path=pin['path'],sha256=sha(f),retained_tests=9,current_source_hashes=True,rerun=False))
fixture=json.loads((P/'captured-terminal-fixture.json').read_text());assert fixture['audit']['frame']==671 and fixture['audit']['room']==0x101 and fixture['state_sha256']=='640c9dadddf5b42a5b9b58e2781cbda3b797b0ac439b0ae78b180a10f7986ee0';assert len(fixture['reads'])==61
external=Q/'qa21_nontrace_run_preparation/return-door-v2-failure';externalpins=[]
for name in ['source-repair-reference.json','retained-inputs.json','terminal-replay.json']:
 f=external/name;externalpins.append(dict(path=str(f),bytes=f.stat().st_size,sha256=sha(f)))
report=dict(scope='Independent source/AST/hash review only; no candidate imports/tests/nativechildren/preflight/build/image/guest/reseal',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),candidate='7c17119ea2517c390acd2e143a33ea839334cc12',disposition='CLEAR bounded source-only lifecycle repair; NOT a launchseal/allocation',source_only_manifest=sha(P/'SOURCE_ONLY_MANIFEST.json'),pins=pins,runtime=identities,unchanged_AST_methods=unchanged,typed_exception_only=ast.unparse(handlers[0].type),attempt_loop=ast.unparse(loops[0].iter),require_live_phases=phasecalls,retained_receipts=receipts,external_metadata=externalpins,fixture=dict(bytes=(P/'captured-terminal-fixture.json').stat().st_size,sha256=sha(P/'captured-terminal-fixture.json'),sparse_reads=61,state=fixture['state_sha256'],frame=671,room=0x101),limits=json.loads((P/'guest-profile-v2.json').read_text())['limits'],launch_manifest_absent=True,limitations=['Original failinglive16MiBsnapshot not retained; exact rejectedaddress/field unavailable','Laterterminal fixture/control and injected host pointers do not replay lost livefailure','Managerinvalid reason itself does not throw/newgamefault not established','No new door/manual/AI/cinematic/Continue/performance/release/physical acceptance','Existing strict native/process/ABI/unrelatedValueError exceptions remain fatal','Main owns any fresh launch namespace/seal/output contract/allocation'])
(OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(disposition=report['disposition'],pins=len(pins),unchanged_runtime=9,unchanged_AST_methods=len(unchanged),retained_receipts=len(receipts),launch_manifest_absent=True)))