import datetime, hashlib, json, subprocess
from pathlib import Path

R=Path(__file__).resolve().parent; L=R.parent; B=L/'boot-cand-fb254e82-v2'
S=Path('/root/probe/rr-safe-cycle23/port/dreamcast/tools/d367/rr_safe_cycle23')
H=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/rr-candidate-handback/fb254e82-20261024')
COMMIT='34a5c48bfe22c3d9718810166407048a906b8bcc'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text())
def put(n,row):
    with open(R/n,'x') as f: json.dump(row,f,indent=2); f.write('\n')
def local(p):
    p=p.replace('\\','/')
    if p.startswith('//wsl.localhost/Ubuntu-24.04'): return Path(p[len('//wsl.localhost/Ubuntu-24.04'):])
    assert p.startswith('C:/'); return Path('/mnt/c/'+p[3:])
seal=L/'limited-v2-final/SOURCE-SEAL.json'
assert sha(seal)=='9e2b85fa11522dd5972853c74bcd7c4130e6e4fbacc2ee4f4d770b539980479c'
assert subprocess.check_output(['git','-C',str(S.parents[4]),'rev-parse','HEAD'],text=True).strip()==COMMIT
assert not subprocess.check_output(['git','-C',str(S.parents[4]),'status','--porcelain'],text=True).strip()
sealed=load(seal); assert sealed['source_commit']==COMMIT
for n,row in sealed['files'].items(): assert sha(S/n)==row['sha256'] and (S/n).stat().st_size==row['bytes']
assert sha(seal.parent/'HOST-RESULTS.json')==sealed['host_results_sha256']
cfgpath=B/'ROOT-REVIEW-PENDING.json'; cfg=load(cfgpath)
assert sha(cfgpath)=='370ad23576222fb750ca3e2a5261e4008e08a780c3aea488e225114dd8c09402'
assert cfg['status']=='ROOT-REVIEW-PENDING' and cfg['execution_authorized'] is False and cfg['admission']['release_priority_granted'] is False
assert cfg['adapter_source_commit']==COMMIT and len(cfg['input_pins'])==49
assert cfg['admission']['maximum_new_c_bytes']==3*1024**3
assert sha(B/'capsule/CAPSULE.json')==cfg['capsule_manifest_sha256']=='08aca2ba8de8064872446a08b58991908bbe7bef0292bd7a263facbe297a63a9'
manifest=load(B/'capsule/CAPSULE.json')
pins={}
for n,digest in manifest['files'].items():
    assert sha(B/'capsule'/n)==digest; pins[str(B/'capsule'/n)]=digest
for n in ['capsule.py','console_guard.py']: assert (B/'capsule'/n).read_bytes()==(S/n).read_bytes()
closurepath=local(cfg['closure_receipt']); closure=load(closurepath)
assert sha(closurepath)==cfg['programme_assets_closure_receipt_sha256']=='d2fa4b5657d2d57fa664f2fbffa126d42a3e7ce5e3ba9195ab2b4b17fe6ea67e'
ins=load(H/'INSPECTION.json'); readback=load(H/'full-readback-manifest.json'); original=load(H/'original-release-manifest.json')
assert closure['source']==ins['source']==cfg['source']
assert closure['programme']['raw']['sha256']==readback['1ST_READ.BIN']['sha256']==ins['raw_main_sha256']
assert closure['programme']['elf']['sha256']==ins['elf']['sha256']
assert len(closure['programme']['overlays'])==14
for n,row in closure['programme']['overlays'].items():
    assert row['sha256']==ins['all14_overlays'][n]['sha256']==readback['dc/'+n]['sha256']
    assert cfg['input_pins']['//wsl.localhost/Ubuntu-24.04'+row['path']]==row['sha256']
assert len(readback)==len(original)==1712
changed={n for n in readback if readback[n]!=original[n]}
expected={'1ST_READ.BIN'}|{'dc/'+n for n in closure['programme']['overlays']}
assert changed==expected and len(readback)-len(changed)==1697
for n,row in closure['tracks'].items():
    assert row['sha256']==ins['tracks'][n]['sha256']
    assert cfg['input_pins']['C:'+row['path'][6:].replace('/','\\')]==row['sha256']
cap,argv=next(iter(cfg['expected_runs'].items())); assert len(cfg['expected_runs'])==1
assert argv==['--disc','C:\\Game Dev\\Emulators\\RE4DC-RR\\cand-fb254e82\\gdemu','--cap',cap,'--syms',closure['syms']['value'],
               '--seconds','45','--name','rr-current-candidate-fb254e82-console-boot-v2','--stop','state title=','--grace','5']
assert cfg['expected_env']=={cap:{'FP_NOLIMIT':'0'}} and not local(cap).exists() and not Path(cfg['lease_path']).exists()
assert cfg['admission']['command']==[cfg['windows_python_wsl'],cfg['wrapper_windows'],*argv]
# Rehash only bounded source/text/metadata pins. Never open actual binary/VMU/media/programme inputs.
text_extensions={'.json','.txt','.py','.cfg','.conf'}
for p,digest in cfg['input_pins'].items():
    path=local(p)
    if path.suffix.lower() in text_extensions:
        assert sha(path)==digest,str(path); pins[str(path)]=digest
for p in [cfgpath,seal,seal.parent/'HOST-RESULTS.json',B/'PREPARATION.json',B/'ROOT-REVIEW-CHECKLIST.md',R/'independent_controls.py',R/'HOST-RESULTS.json',R/'REVIEW.md']:
    pins[str(p)]=sha(p)
host=load(R/'HOST-RESULTS.json'); assert host['status']=='PASS' and host['methods']==10
put('READBACK.json',dict(source_commit=COMMIT,files=pins,metadata_assertions=dict(logical_members=1712,nonprogramme_unchanged=1697,overlays=14,input_pins=49),
    actual_binary_media_programme_read=False,source_seal_sha256=sha(seal),pending_config_sha256=sha(cfgpath),capsule_manifest_sha256=sha(B/'capsule/CAPSULE.json'),closure_sha256=sha(closurepath)))
put('REVIEW-CLEAR.json',dict(status='CLEAR',adapter_source_commit=COMMIT,adapter_source_seal_sha256=sha(seal),
    reviewed_parent_source_commit='d67699b259b056ed25fd559f9ab331f1923fc4cb',confirmed_parent_finding='Known BADRE/qualified DISCNOTE omissions repaired in34a5',
    pending_configuration_sha256=sha(cfgpath),capsule_manifest_sha256=sha(B/'capsule/CAPSULE.json'),programme_assets_closure_receipt_sha256=sha(closurepath),
    scope='Repaired limited single-boot source and pending v2 metadata/config shape; no execution admission',
    generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),findings=[],independent_host_methods=10,author20_receipt_read_not_rerun=True,
    host_receipt_sha256=sha(R/'HOST-RESULTS.json'),review_sha256=sha(R/'REVIEW.md'),readback_sha256=sha(R/'READBACK.json'),
    runtime_qualified=False,execution_admitted=False,whole_cycle_admitted=False,actual_guest=False,SDK=False,actual_process_kill=False,actual_binary_or_image_read=False,
    required_root_gates=['Separate approved config/alias/lease freeze','Current RR terminal/process and release priority','Fresh peak allocation and floors','Actual bound audit AND title-goal semantic decision']))
print(json.dumps({n:sha(R/n) for n in ['REVIEW-CLEAR.json','REVIEW.md','READBACK.json','HOST-RESULTS.json']}))
