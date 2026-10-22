"""Static-only adapter authority/lifecycle/dependency review; no candidate imports."""
import ast,datetime,hashlib,json,pathlib
Q=pathlib.Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-qa21-death-repair\port\dreamcast\tools\d367');P=Q/'qa21_nontrace_owned_adapter_v1';B=Q/'qa21_nontrace_domains_exit_v1';V=Q/'qa21_nontrace_owned_runner_v2';OUT=pathlib.Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();dump=lambda n:ast.dump(n,include_attributes=False)
allfn=lambda p:{n.name:n for n in ast.walk(ast.parse(p.read_text())) if isinstance(n,ast.FunctionDef)}
integrity=json.loads((P/'SOURCE_ONLY_MANIFEST.json').read_text());assert sha(P/'SOURCE_ONLY_MANIFEST.json')=='15f215e3f784e0bf0e3b695e159b5399bf0327964142dfb45003743499cdbbb8';runtime=json.loads((P/'source-manifest.json').read_text());assert sha(P/'source-manifest.json')=='8eac4789a775333c218ede0292569e88cb54971ec295da9552d38b6332e956f1'
pins={}
for label,m in [('integrity',integrity),('runtime',runtime)]:
 rows=[]
 for name,row in m['files'].items():
  p=P/name;assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],name;rows.append(dict(path=name,bytes=p.stat().st_size,sha256=sha(p)))
 pins[label]=rows
frozen=['capture-budget.py','controller-core.py','exact-log-symbols.json','global-ui-ABI-supplement.json','guest-profile-v2.json','guest-supervisor-core.py','input-deadlines.py','layout-contract.py','observe.py','observer-v2.py','policies.py','windows-backend.py']
for n in frozen:assert (P/n).read_bytes()==(B/n).read_bytes(),n
reviewed=json.loads((P/'REVIEWED_COMPONENTS.json').read_text());assert reviewed['adopted_for_runtime'] is False
for n,h in reviewed['local_hooks'].items():assert sha(P/'reference-hooks'/n)==h and (P/'reference-hooks'/n).read_bytes()==(V/n).read_bytes(),n
assert sha(pathlib.Path(reviewed['review_path']))==reviewed['review_sha256']=='2c7d0e2fcfc5cf2064a411f942e3ab979986768b15a7006f2ec63948bf624061'
innerold=allfn(B/'inner-adapter.py');innernew=allfn(P/'inner-adapter.py');sameinner=[]
for name,node in innerold.items():
 if name!='main':assert dump(node)==dump(innernew[name]),name;sameinner.append(name)
outerold=allfn(B/'outer-driver.py');outernew=allfn(P/'outer-driver.py');changed=['validate_source_references','preflight','validate_seed','output_paths','parse_args','main'];sameouter=[]
for name,node in outerold.items():
 if name not in changed:assert dump(node)==dump(outernew[name]),name;sameouter.append(name)
main=outernew['main'];guard=next(n for n in main.body if isinstance(n,ast.If) and 'execute_root_allocation' in ast.unparse(n.test));hashline=min(n.lineno for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in ['hash_file','load']);assert guard.lineno<hashline
parser=ast.unparse(outernew['parse_args']);assert "'--execute-root-allocation', action='store_true', default=False" in parser
wire=allfn(P/'wiring-backend.py');close=ast.unparse(wire['close_owned_handles']);stop=ast.unparse(wire['stop_deadlines']);assert close.index('self.close_reference_service()')<close.index('super().close_owned_handles') and stop.index('self.close_reference_service()')<stop.index('super().stop_deadlines()')
release=ast.unparse(wire['release']);assert release.index('self.reference_service.start()')<release.index('inner.stdin.write(')
service=ast.unparse(wire['close_reference_service']);assert 'service.hold = True' in service and 'service.collector.hold = True' in service and 'raise' in service
constructor=wire['__init__'];assert ast.unparse(constructor).index('validate_authority(')<ast.unparse(constructor).index('super().__init__(')
core=allfn(P/'guest-supervisor-core.py')['monitor'];text=ast.unparse(core);assert text.index('backend.arm_deadlines(inner)')<text.index('backend.release(inner)')
innertext=(P/'inner-adapter.py').read_text();assert innertext.index("logs=json.loads((P/'exact-log-symbols.json')")<innertext.index('thread.start();started=True') and "if started:thread.join(timeout=2)" in innertext
assert 'runner.REFERENCE_HOOKS=reference_proxy' in innertext and "descriptor['context_path']" in innertext and 'readline(4097)' in ast.unparse(innernew['read_reference_release'])
# Exact future bytes/schema are data only. Never read/query the literal ROOT destination.
request=json.loads((P/'LAUNCH_REQUEST.json').read_text());allocation=json.loads((P/'FUTURE_ROOT_ALLOCATION_BYTES.json').read_text());assert sha(P/'LAUNCH_REQUEST.json')=='59ce668eff65fe289e14d6360d98d5766e505b42335c606d565c78ca0cea9ed6';assert sha(P/'FUTURE_ROOT_ALLOCATION_BYTES.json')=='b3d6d2cb9669de8ddb51967d2168b699f54aa3cce783678d75cd4dd9c1e3dc41'
argv=request['argv'];assert argv[1]=='-B' and argv[2]==str(P/'outer-driver.py') and argv[-1]=='--execute-root-allocation'
assert request['allocation_status']=='UNALLOCATED; source-only future request' and request['actual_authority_file_created_by_this_unit'] is False
assert argv[argv.index('--profile')+1]==str(P/'guest-profile-v2.json') and argv[argv.index('--tools-sha256')+1]==sha(P/'source-manifest.json') and argv[argv.index('--profile-sha256')+1]==sha(P/'guest-profile-v2.json')
assert argv[argv.index('--root-allocation')+1]==request['root_allocation_path'] and argv[argv.index('--root-allocation-sha256')+1]==sha(P/'FUTURE_ROOT_ALLOCATION_BYTES.json')
assert allocation['tools_sha256']==sha(P/'source-manifest.json') and allocation['contract_sha256']==sha(P/'reference-hooks/COLLECTOR_CONTRACT.json') and allocation['runner_sha256']==sha(P/'reference-hooks/checkpoint_runner18.child.py') and allocation['attempt_limit']==1
assert "if Path(path) != ALLOCATION" in ast.unparse(wire['validate_authority'])
coverage=[]
for platform,want in [('linux','96a039b6e09cdf4c3663e75d3d4e1efcdd1ef598872a33c2cc6b4f9ef0164ec7'),('windows','78fa0c6e218e16e996a8fd3a0b81a8f201b987a88c074350123e0f396f1712a8')]:
 p=P/('receipt-'+platform+'.json');assert sha(p)==want;r=json.loads(p.read_text());assert r['tests']==22 and r['successful'] is True
 for n,h in r['source_sha256'].items():assert sha(P/n)==h,(platform,n)
 coverage.append(dict(platform=platform,sha256=sha(p),retained_tests=22,current_source_pins=True,rerun=False))
report=dict(scope='SOURCE/hash/AST/retained receipts only; no imports/tests/nativequery/image/state/preflight/Flycast/allocation/reseal',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),candidate='1cb552bbe4d9f734ba2962b22307eb118bbfa297',disposition='CLEAR bounded source-only adapter wiring; not adoption/nativeinterop or execution permission',pins=pins,source_manifest=sha(P/'SOURCE_ONLY_MANIFEST.json'),runtime_manifest=sha(P/'source-manifest.json'),frozen505f=frozen,exact_v2_mirrors=reviewed['local_hooks'],unchanged_inner_AST=sameinner,unchanged_outer_AST=sameouter,default_execute_off_before_hash_import=True,root_authority_checked_before_native_constructor=True,broker_join_before_deadline_and_handle_close=True,failed_join_HOLD_no_baseclose=True,early_backend_guest_closed_even_core_none=True,inner_bounded_context_parser_and_thread_cleanup=True,retained_coverage=coverage,future_request=sha(P/'LAUNCH_REQUEST.json'),future_allocation_template=sha(P/'FUTURE_ROOT_ALLOCATION_BYTES.json'),literal_ROOT_destination_queried=False,limits=request['bounds'],limitations=['Runtime extension is defaultoff gated by exactseparateROOTfile/explicitflag; templateownpathcannotauthorize','No actualROOTfileabsence/currentnativefacts/image/state checked here','NativeWindows sharing/disposition/processduplication/IPC/timing interoperability remainsopen','NATIVE_INTEROP_PLAN is description only with no fixturehelper allocated','Cleanup namespace is nonatomic and anylatefailuredisqualifies/preservesremainingrefs','Original13bf observer01 staysFALSE; no manual/gameplay/performance/release/physicalacceptance follows'])
(OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(disposition=report['disposition'],integrity_pins=len(pins['integrity']),runtime_pins=len(pins['runtime']),frozenfiles=len(frozen),mirrors=len(reviewed['local_hooks']),innerAST=len(sameinner),outerAST=len(sameouter))))