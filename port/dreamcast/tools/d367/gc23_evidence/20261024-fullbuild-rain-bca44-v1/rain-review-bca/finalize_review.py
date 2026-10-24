import datetime,hashlib,json,pathlib,subprocess
P=pathlib.Path; R=P(__file__).resolve().parent; E=R.parent/'rain-r10c-experiment'
REPO=P('/root/work/lanes/water-rain24'); COMMIT='bca44d58a1fa0a51fd87ba94deba8cba925c8998';BASE='d291f814b5a873718c3f32b686eef5f1a8707f1d'
def sha(p):return hashlib.sha256(P(p).read_bytes()).hexdigest()
def load(p):return json.loads(P(p).read_text())
def put(n,x):
    with open(R/n,'x') as f:json.dump(x,f,indent=2);f.write('\n')
assert sha(E/'RECEIPT.json')=='6a79c0c4cc74d323f32ae2c74802148161a70fe1e9098e28de85590ef1660323'
receipt=load(E/'RECEIPT.json'); assert receipt['head']==COMMIT
assert subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()==COMMIT
assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain'],text=True).strip()
paths=subprocess.check_output(['git','-C',str(REPO),'diff','--name-only',BASE,COMMIT],text=True).splitlines()
assert len(paths)==5 and {'src/game/filter06.cpp','port/dreamcast/game/effects30.mk'}<=set(paths)
pins={}
for name,row in receipt['artifacts'].items():
    if name in paths:
        blob=subprocess.check_output(['git','-C',str(REPO),'show',COMMIT+':'+name])
        assert hashlib.sha256(blob).hexdigest()==row['sha256'] and len(blob)==row['bytes'],name
        pins[str(REPO/name)]=dict(git_blob_sha256=row['sha256'],physical_sha256=sha(REPO/name))
    else:
        p=E/name[len('evidence/'):] if name.startswith('evidence/') else E/name
        assert sha(p)==row['sha256'],name
        pins[str(p.resolve())]=dict(physical_sha256=sha(p))
host=load(R/'INDEPENDENT-HOST-RESULTS.json');assert host['status']=='PASS_HOST_SOURCE_ONLY' and host['mutants_defeated']==2
assert sha(R/'independent_controls.py')==host['controls_sha256']
put('SUPPLIED-SUITE-RERUN.json',dict(status='PASS_INDEPENDENT_RERUN',source_commit=COMMIT,
    command='wsl.exe -d Ubuntu-24.04 -u root -- env PYTHONDONTWRITEBYTECODE=1 python3 '+str(REPO/'port/dreamcast/tools/d367/water_rain24/test_rain_r10c.py'),
    observed_tool_exit_code=0,observed_tool_wall_seconds=7.3517064,controls=receipt['host_controls'],
    scope='Observed successful tool transcript, not another rerun; host/source only',SDK=False,guest=False))
for p in [E/'RECEIPT.json',R/'INDEPENDENT-HOST-RESULTS.json',R/'SUPPLIED-SUITE-RERUN.json',R/'independent_controls.py',R/'REVIEW.md']:
    pins[str(p)]=dict(physical_sha256=sha(p))
put('READBACK.json',dict(status='PASS_SOURCE_HOST_BINDING',source_commit=COMMIT,files=pins,changed_paths=paths,
    source_dirty=False,source_or_asset_write=False,SDK=False,guest=False))
put('REVIEW-CLEAR.json',dict(status='CLEAR',scope='Default-off source experiment and host controls only',source_commit=COMMIT,
    experiment_receipt_sha256=sha(E/'RECEIPT.json'),review_sha256=sha(R/'REVIEW.md'),readback_sha256=sha(R/'READBACK.json'),
    independent_host_receipt_sha256=sha(R/'INDEPENDENT-HOST-RESULTS.json'),supplied_suite_rerun_receipt_sha256=sha(R/'SUPPLIED-SUITE-RERUN.json'),
    generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),findings=[],independent_mutants_defeated=2,author_mutants_independently_rerun=11,
    OFF_preprocess_comparisons=12,Make_negatives=14,old_night_parity_scope='Night-only history; not after new r10c history',
    extra_persistent_source_bytes=8,SDK=False,guest=False,author_tree_edit=False,runtime_approved=False,
    target_object_identity_accepted=False,appearance_accepted=False,PS2_ancestry_accepted=False,I001_accepted=False,memory_performance_qualified=False))
print(json.dumps({n:sha(R/n) for n in ['REVIEW-CLEAR.json','REVIEW.md','READBACK.json','INDEPENDENT-HOST-RESULTS.json','SUPPLIED-SUITE-RERUN.json']}))
