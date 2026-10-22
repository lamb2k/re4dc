"""Static-only evidence domain and retained-exit review. No candidate imports/tests."""
import ast,datetime,hashlib,json,pathlib
Q=pathlib.Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-qa21-death-repair\port\dreamcast\tools\d367');P=Q/'qa21_nontrace_domains_exit_v1';B=Q/'qa21_nontrace_return_door_observer_v1';OUT=pathlib.Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();dump=lambda n:ast.dump(n,include_attributes=False)
fns=lambda p:{n.name:n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef)}
methods=lambda p,c:{n.name:n for x in ast.parse(p.read_text()).body if isinstance(x,ast.ClassDef) and x.name==c for n in x.body if isinstance(n,ast.FunctionDef)}
manifest=json.loads((P/'SOURCE_ONLY_MANIFEST.json').read_text());assert sha(P/'SOURCE_ONLY_MANIFEST.json')=='0b73077358b87a8b73325d6d823acd24c0037e57a7b653ad8f6f76a5bcc25e63';pins=[]
for name,row in manifest['files'].items():
 p=P/name;assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],name;pins.append(dict(path=name,bytes=p.stat().st_size,sha256=sha(p)))
assert not (P/'source-manifest.json').exists()
unchangedfiles=['controller-core.py','guest-supervisor-core.py','input-deadlines.py','capture-budget.py','guest-profile-v2.json','exact-log-symbols.json']
for n in unchangedfiles:assert (P/n).read_bytes()==(B/n).read_bytes(),n
samefn=[]
for file,names in [('policies.py',['valid_sample','free_play','shooting_safe','ordinary_weapon_ready','qa_safe','discharge']),('outer-driver.py',['load','no_alias','hash_file','fixed_profile','native_file_id','validate_source_references','preflight','validate_seed','output_paths','parse_args','main'])]:
 old=fns(B/file);new=fns(P/file)
 for n in names:assert dump(old[n])==dump(new[n]),(file,n);samefn.append(file+':'+n)
for file,cls,changed in [('windows-backend.py','WindowsBackend',{'retained_identity','actual_seconds','release_inputs'}),('observe.py','Observer',{'sample'}),('observer-v2.py','Reader',{'snapshot','actor_chain'})]:
 old=methods(B/file,cls);new=methods(P/file,cls)
 for n in old:
  if n not in changed:assert dump(old[n])==dump(new[n]),(file,n);samefn.append(file+':'+n)
expected=(B/'inner-adapter.py').read_text().replace("     manual='PlayingManual2' in (cap/'run-output.txt').read_text(errors='replace')\n","     manual='PlayingManual2' in (cap/'run-output.txt').read_text(errors='replace')\n     if core.policy.manual_ui_evidence(row):state['original_manual_witness']=True;state['manual_witness_state']=row\n").replace("     state['last']=observer.last;state['original_manual_witness']=manual and observer.last.get('subscreen_type')==64 and observer.last['global']['room']==0x101\n","     state['last']=observer.last\n")
assert (P/'inner-adapter.py').read_text()==expected
expectedlayout=(B/'layout-contract.py').read_text().replace("add('SUB_SCREEN',[('type','i'),('Loop','B')])","add('SUB_SCREEN',[('type','i'),('Loop','B'),('get_item_id','H'),('pBuf','I')]);add('GlobalWork',[('pStFnt','I')])")
assert (P/'layout-contract.py').read_text()==expectedlayout
supp=json.loads((P/'global-ui-ABI-supplement.json').read_text());layoutpath=pathlib.Path(supp['layout_path']);assert sha(layoutpath)==supp['layout_sha256'];layout=json.loads(layoutpath.read_text());assert layout['elf_sha256']==supp['elf_sha256']
for row in supp['extra_fields']:
 matches=[m for m in layout['found'][row['structure']]['members'] if m['name']==row['requested'] or m['name'].endswith('.'+row['requested'])];assert len(matches)==1
 m=matches[0];assert (m['offset'],m['bytes'],m['tag'])==(row['offset'],row['bytes'],row['tag'])
assert len(supp['extra_fields'])==3 and (supp['new_full_field_count'],supp['original_profile_field_count'])==(76,73)
# Typed UI evidence only; inspect exact guard expressions without evaluating code.
manual=ast.unparse(fns(P/'policies.py')['manual_ui_evidence']);assert "g['frame'] > 533" in manual and "u.get('get_item_id') == 174" in manual and "u.get('borrowed_window') is True" in manual and "u.get('transport_coherent') is True" in manual
observe=(P/'observe.py').read_text();assert 'ui_before==ui_inside==ui_after' in observe and "actor_reason=manager.pop('reason',None)" in observe and 'retained_identity_validated=True' in observe
backend=methods(P/'windows-backend.py','WindowsBackend');phase=ast.unparse(backend['retained_exit_phase']);assert "status == 0" in phase and "status == 258" in phase and "(-1, 4294967295)" in phase
assert "phase == 'exited'" in ast.unparse(backend['actual_seconds']) and 'return max(' in ast.unparse(backend['actual_seconds'])
release=ast.unparse(backend['release_inputs']);assert "self.input_released = False" in release and "'queued_keyups': 0" in release
qualification=json.loads((P/'source-qualification.json').read_text());coverage=[]
for platform,pin in qualification['tests'].items():
 p=P/pin['path'];assert sha(p)==pin['sha256'];r=json.loads(p.read_text());assert r['returncode']==0
 for name,h in r['sources'].items():assert sha(P/name)==h,(platform,name)
 coverage.append(dict(platform=platform,path=pin['path'],sha256=sha(p),retained_tests=13,current_source_hashes=True,rerun=False))
external=Q/'qa21_nontrace_run_preparation/return-door-observer01-failure';summary=json.loads((external/'actual-observation-summary.json').read_text());refs=json.loads((external/'retained-reference-identity.json').read_text());assert (summary['rows'],summary['valid_rows'],summary['typed_file_UI64_Loop1_rows'])==(164,161,19) and summary['old_attempt_qualified'] is False
assert refs['immutable_profile4c_expected_links']==2 and refs['current_links']==3
extpins=[dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)) for p in external.iterdir() if p.is_file()]
report=dict(scope='Independent source/hash/AST only; no imports/tests/preflight/nativechildren/guest/build/image/reseal',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),candidate='505f3ee487a1bb658199986f4988fdf14008c960',disposition='CLEAR bounded source-only domain/exit repair; launch prohibited until separate reviewed contract',manifest=sha(P/'SOURCE_ONLY_MANIFEST.json'),pins=pins,unchanged_files=unchangedfiles,unchanged_AST=samefn,inner_exact_only_latch_and_no_teardown_overwrite=True,ABI_exact_three_additions=supp,retained_coverage=coverage,external_metadata=extpins,timeline=dict(total_rows=164,legacy_valid_flags=161,coherent_UI_rows=19,original_qualified=False),reference_gap=dict(expected=2,current=3,guard_unchanged=True),limits=json.loads((P/'guest-profile-v2.json').read_text())['limits'],limitations=['UI evidence does not grant input or authenticate borrowed player/actor data','Old live wait result258 vsFAILED unavailable; new distinctions are source/mocked controls','Original41.8565468sexit0 run staysfalse/noinnercontrol despite separately observedPlayingManual2pixels','Terminal4717/frame1230/control plus161legacyvalid flags do not imply clean gameplay/playerstorage','No source-manifest launchseal/request/allocation; oldprofileguard2 must reject3links','Main owns future exactreference extension/outputcontract/seal/allocation'])
(OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(disposition=report['disposition'],pins=len(pins),unchanged_AST=len(samefn),unchanged_files=len(unchangedfiles),retained_receipts=len(coverage),ABIextra=3)))