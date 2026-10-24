"""Prepare only; never invoke guest/hold/build. Frozen capsule must already exist."""
import datetime,hashlib,json,pathlib,subprocess,sys
SRC='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2'; ADAPTER='34a5c48bfe22c3d9718810166407048a906b8bcc'
B=pathlib.Path('/root/probe/rr-safe-boot-fb254e82-v3')
E=pathlib.Path('/mnt/c/Flycast-Evidence/re4-dreamcast/rr-candidate-handback/fb254e82-20261024/bounded-console-boot-v3');H=E.parent
C=pathlib.Path('/mnt/c/Game Dev/Emulators/RE4DC-RR/cand-fb254e82');O=pathlib.Path('/root/probe/lanes/route/out-rrfb254e8rP')
T=pathlib.Path('/mnt/c/Flycast-Evidence/re4-dreamcast/d367-harness-par')
P=pathlib.Path('/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe')
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def win(p):
 s=str(p);return 'C:'+s[6:].replace('/','\\') if s.startswith('/mnt/c/') else '//wsl.localhost/Ubuntu-24.04'+s
unc=lambda p:'//wsl.localhost/Ubuntu-24.04'+str(p)
def fresh(p,value):
 with p.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2);f.write('\n')
ins=json.loads((H/'INSPECTION.json').read_text());identity=json.loads((C/'IDENTITY.json').read_text())
assert sha(H/'INSPECTION.json')=='d236b9d39f2d618d7c715f6d10c9d83bb10ebbabb7861b4064608a7ad7ecc447'
assert sha(H/'HANDBACK.json')=='bb0d3d044e276fc6860abe3974a140b0ba8f3d7d13abc2c7290e6d28588dffa8'
assert ins['source']==identity['source']==SRC
assert subprocess.check_output(['git','-C','/root/probe/rr-safe-cycle23','rev-parse','HEAD'],text=True).strip()==ADAPTER
assert subprocess.check_output(['git','-C','/root/work/lanes/rr','rev-parse','HEAD'],text=True).strip()==SRC
assert not subprocess.check_output(['git','-C','/root/work/lanes/rr','status','--porcelain'],text=True).strip()
actual={}
def add(p,expected=None):
 p=pathlib.Path(p);digest=sha(p)
 if expected is not None:assert digest==expected,str(p)
 actual[win(p)]=digest
 return dict(path=str(p),size=p.stat().st_size,sha256=digest)
readback=json.loads((H/'full-readback-manifest.json').read_text())
assert readback['1ST_READ.BIN']['sha256']==ins['raw_main_sha256']
programme=dict(raw=dict(member='1ST_READ.BIN',**readback['1ST_READ.BIN'],basis='actual-disc logical member from exact pinned full readback; not stale original release/tree main'),
               elf=add(O/'re4dc-game.elf',ins['elf']['sha256']),overlays={})
for name,pin in ins['all14_overlays'].items():programme['overlays'][name]=add(O/name,pin['sha256'])
assert len(programme['overlays'])==14
tracks={}
for name,pin in ins['tracks'].items():
 p=C/name;fp=[p.stat().st_size,p.stat().st_mtime_ns];assert fp==ins['media_fingerprints'][name],name
 if p.name!='track03.bin':add(p,pin['sha256'])
 else:actual[win(p)]=pin['sha256']
 tracks[name]=dict(path=str(p),**pin,current_stat_fingerprint=fp,binding='prior actual full hash plus current identical stat fingerprint; full hash checked by guard before guest' if p.name=='track03.bin' else 'full hash checked during preparation')
for p in (H/'INSPECTION.json',H/'HANDBACK.json',H/'full-readback-manifest.json',H/'original-release-manifest.json',C/'IDENTITY.json',C/'SHA256SUMS.txt',C/'QUALIFICATION-SHA256SUMS.txt',pathlib.Path(ins['asset_release_manifest']['path']),pathlib.Path(ins['recipe']['path']),pathlib.Path(ins['resolved_profile']['path']),O/'syms.txt',O/'stack.txt',O/'missing.txt'):add(p)
for field in ('asset_release_manifest','recipe','resolved_profile'):
 assert sha(pathlib.Path(ins[field]['path']))==ins[field]['sha256']
assert sha(H/'full-readback-manifest.json')==identity['assets']['readback_manifest']['sha256']
console=add('/mnt/c/Flycast-Evidence/re4-dreamcast/flycast-console-bin/flycast-console.exe','8e6c49871013c25b1a1c77c789167e3aaed8193e828adb7e2bbce9248d2add4a')
for p in [T/'emu.cfg',T/'read_log.py',T/'capture_ui_vram.py',*sorted((T/'data').glob('*'))]:
 if p.is_file():add(p)
python=add(P,'4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a')
for name in ('python312.dll','python3.dll','vcruntime140.dll','vcruntime140_1.dll'):
 p=P.parent/name
 if p.exists():add(p)
capsule=B/'capsule';harness=capsule/'fullplay/_fp_run_original.py'
for p in (harness,capsule/'console_guard.py',capsule/'capsule.py',capsule/'fullplay/fp_run.py',capsule/'CAPSULE.json'):actual[unc(p)]=sha(p)
closure=dict(status='PREPARED_INPUT_BINDING_ROOT_REVIEW_PENDING_NOT_RUNTIME_ACCEPTANCE',source=SRC,adapter_source=ADAPTER,
 prepared_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),candidate=str(C),programme=programme,tracks=tracks,
 source_handback=dict(path=str(H/'INSPECTION.json'),sha256=sha(H/'INSPECTION.json')),
 asset_readback=dict(files=1712,nonprogramme_unchanged=1697,manifest_sha256=sha(H/'full-readback-manifest.json'),basis='existing actual handback; not new full-disc readback'),
 console=console,python=python,syms=dict(path=str(O/'syms.txt'),sha256=sha(O/'syms.txt'),value=(O/'syms.txt').read_text().strip()),
 original_template_sha256=sha(T/'emu.cfg'),original_template_modified=False,
 requested_launch=dict(FP_NOLIMIT='0',aica_LimitFPS='yes',enforced_by_adapter_before_exact_Popen=True,prelimit_and_launch_cfg_preserved=True),media_copied=False,guest_launched=False,sdk_build=False,runtime_qualified=False)
fresh(E/'PROGRAMME-ASSETS-CLOSURE.json',closure)
actual[win(E/'PROGRAMME-ASSETS-CLOSURE.json')]=sha(E/'PROGRAMME-ASSETS-CLOSURE.json')
cap=E/'capture';assert not cap.exists()
argv=['--disc',win(C/'gdemu'),'--cap',win(cap),'--syms',(O/'syms.txt').read_text().strip(),'--seconds','45','--name','rr-current-candidate-fb254e82-console-boot-v3','--stop','state title=','--grace','5']
config=B/'ROOT-REVIEW-PENDING.json';command=[str(P),unc(capsule/'fullplay/fp_run.py'),*argv]
cfg=dict(status='ROOT-REVIEW-PENDING',source=SRC,adapter_source_commit=ADAPTER,profile='RR_FINAL_GDI_BOOT45_CHILD55_LIMITED_V2',
 console=win(pathlib.Path(console['path'])),console_sha256=console['sha256'],template_cfg=win(T/'emu.cfg'),base_cfg_sha256=sha(T/'emu.cfg'),harness=unc(harness),harness_sha256=sha(harness),
 input_pins=actual,closure_receipt=win(E/'PROGRAMME-ASSETS-CLOSURE.json'),programme_assets_closure_receipt_sha256=sha(E/'PROGRAMME-ASSETS-CLOSURE.json'),capsule_manifest_sha256=sha(capsule/'CAPSULE.json'),
 windows_python=win(P),windows_python_wsl=str(P),guard_windows=unc(capsule/'console_guard.py'),wrapper_windows=unc(capsule/'fullplay/fp_run.py'),config_windows=unc(config),
 lease_path=str(B/'ROOT-BOOT-LEASE.json'),expected_runs={win(cap):argv},expected_env={win(cap):{'FP_NOLIMIT':'0'}},capture_paths_wsl={win(cap):str(cap)},
 required_saved_launch_config={'aica.LimitFPS':'yes','FP_NOLIMIT':'0'},
 admission=dict(phase='FINAL_GDI_BOOT_ONLY',release_priority_granted=False,maximum_new_c_bytes=3221225472,staging_floor_bytes=24*1024**3,absolute_floor_bytes=20*1024**3,fresh_root_admission='PENDING_NOT_PERFORMED',command=command),
 semantic_boot_predicate=dict(component='capsule.py judge-boot',title='state title=',stopped='goal',seconds=45,grace_s=5,errors='none; HALT/FAULT/MISSING/OOM/bad-read and early exit rejected',process_bounds_required_separately=True),execution_authorized=False,runtime_qualified=False)
fresh(config,cfg)
sys.path.insert(0,str(capsule));import capsule as c
c.verify_capsule(cfg)
try:c.hold(config,command)
except ValueError as ex:assert str(ex)=='execution not admitted'
else:raise AssertionError('pending config executable')
assert not cap.exists() and not pathlib.Path(cfg['lease_path']).exists()
preparation=dict(status='PREPARED_ROOT_REVIEW_PENDING_NO_EXECUTION',adapter_source=ADAPTER,source=SRC,config=dict(path=str(config),sha256=sha(config)),capsule_manifest=dict(path=str(capsule/'CAPSULE.json'),sha256=sha(capsule/'CAPSULE.json')),closure=dict(path=str(E/'PROGRAMME-ASSETS-CLOSURE.json'),sha256=sha(E/'PROGRAMME-ASSETS-CLOSURE.json')),input_pins=len(actual),source_elf_all14_rehashed=True,raw_main_bound_to_actual_disc_readback=True,track03_rehashed_during_preparation=False,track03_prior_full_hash_current_fingerprint_bound=True,pending_entry_refusal_verified=True,capture_absent=True,lease_absent=True,SDK_guest_build_cleanup=False,root_resource_census_performed=False,requested_peak_new_c_bytes=3221225472,launch_permitted=False)
fresh(B/'PREPARATION.json',preparation)
for p in (config,capsule/'CAPSULE.json',E/'PROGRAMME-ASSETS-CLOSURE.json',B/'PREPARATION.json'):print(str(p),sha(p),p.stat().st_size)
print('pins',len(actual))
