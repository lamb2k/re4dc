"""Metadata/source-only V3 relocation check; never imports or invokes adapter."""
import datetime,hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parent; L=R.parent
B=L/'boot-cand-fb254e82-v3'; OLD=L/'boot-cand-fb254e82-v2'
RT=Path('/root/probe/rr-safe-boot-fb254e82-v3')
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/rr-candidate-handback/fb254e82-20261024')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text())
def put(n,x):
    with open(R/n,'x') as f: json.dump(x,f,indent=2); f.write('\n')
cfg=load(RT/'ROOT-REVIEW-PENDING.json'); previous=load(OLD/'ROOT-REVIEW-PENDING.json')
assert sha(RT/'ROOT-REVIEW-PENDING.json')=='981d6f49363e4bb569ebcb6cef36b7c09f39ee9808b003fd6c0e5c9cc4099f0a'
assert (RT/'ROOT-REVIEW-PENDING.json').read_bytes()==(B/'ROOT-REVIEW-PENDING.json').read_bytes()
assert cfg['adapter_source_commit']==previous['adapter_source_commit']=='34a5c48bfe22c3d9718810166407048a906b8bcc'
assert cfg['status']=='ROOT-REVIEW-PENDING' and cfg['execution_authorized'] is False and cfg['admission']['release_priority_granted'] is False
unc='//wsl.localhost/Ubuntu-24.04'+str(RT)
for key,tail in [('config_windows','/ROOT-REVIEW-PENDING.json'),('guard_windows','/capsule/console_guard.py'),
                 ('wrapper_windows','/capsule/fullplay/fp_run.py'),('harness','/capsule/fullplay/_fp_run_original.py')]:
    assert cfg[key]==unc+tail
assert cfg['lease_path']==str(RT/'ROOT-BOOT-LEASE.json') and not Path(cfg['lease_path']).exists()
assert not any(p.replace('\\','/').startswith('//wsl.localhost/Ubuntu-24.04/mnt/c/') for p in cfg['input_pins'])
cap,argv=next(iter(cfg['expected_runs'].items())); assert len(cfg['expected_runs'])==1
newcap=E/'bounded-console-boot-v3/capture'; assert not newcap.exists()
assert cfg['capture_paths_wsl']=={cap:str(newcap)}
assert cap=='C:'+str(newcap)[6:].replace('/','\\')
assert argv==['--disc','C:\\Game Dev\\Emulators\\RE4DC-RR\\cand-fb254e82\\gdemu','--cap',cap,'--syms','0x3e16a0 0x3f16a4 0x3f16a0',
             '--seconds','45','--name','rr-current-candidate-fb254e82-console-boot-v3','--stop','state title=','--grace','5']
assert cfg['expected_env']=={cap:{'FP_NOLIMIT':'0'}}
assert cfg['admission']['command']==[cfg['windows_python_wsl'],cfg['wrapper_windows'],*argv]
for key in ['phase','maximum_new_c_bytes','staging_floor_bytes','absolute_floor_bytes']:
    assert cfg['admission'][key]==previous['admission'][key]
for key in ['profile','source','console','console_sha256','template_cfg','base_cfg_sha256','harness_sha256','windows_python',
            'windows_python_wsl','required_saved_launch_config','semantic_boot_predicate']:
    assert cfg[key]==previous[key]
manifest=load(RT/'capsule/CAPSULE.json')
assert sha(RT/'capsule/CAPSULE.json')==cfg['capsule_manifest_sha256']=='1113b56b10f8da664cf39534a336218f6096f1bf08a65596325f059d1fe8df53'
source=Path('/root/probe/rr-safe-cycle23/port/dreamcast/tools/d367/rr_safe_cycle23')
pins={}
for name,digest in manifest['files'].items():
    assert not Path(name).is_absolute() and '..' not in Path(name).parts
    assert sha(RT/'capsule'/name)==digest; pins[str(RT/'capsule'/name)]=digest
for name in ['capsule.py','console_guard.py']: assert (RT/'capsule'/name).read_bytes()==(source/name).read_bytes()
wrapper=(RT/'capsule/fullplay/fp_run.py').read_text()
assert "'/root/probe/rr-safe-boot-fb254e82-v3/capsule'+'/capsule.py'" in wrapper
closurepath=E/'bounded-console-boot-v3/PROGRAMME-ASSETS-CLOSURE.json'
assert sha(closurepath)==cfg['programme_assets_closure_receipt_sha256']=='d1b6f2127a960bea245a8f8384f152c89aa7eaaea2a94c28ce624c3f933a60ed'
closure=load(closurepath); oldclosure=load(E/'bounded-console-boot-v2/PROGRAMME-ASSETS-CLOSURE.json')
for key in ['source','adapter_source','candidate','programme','tracks','source_handback','asset_readback','console','python','syms',
            'original_template_sha256','original_template_modified','requested_launch','media_copied','guest_launched','sdk_build','runtime_qualified']:
    assert closure[key]==oldclosure[key],key
win=load(B/'WINDOWS-PINS.json')
assert sha(B/'WINDOWS-PINS.json')=='247cd1d513840742420f22efd66325182565cb5b675aa1c5bfc3ef95861ef071'
assert win['status']=='PASS_READ_ONLY_WINDOWS_ALL49' and win['count']==len(win['rows'])==len(cfg['input_pins'])==49
assert win['config_sha256']==sha(RT/'ROOT-REVIEW-PENDING.json')
assert win['runtime_config'].replace('\\','/')==cfg['config_windows']
assert win['actual_python']==cfg['windows_python']
assert win['actual_python_sha256']==cfg['input_pins'][cfg['windows_python']]
assert sha(B/'windows-pin-preflight.py')==win['preflight_source_sha256']=='eff93d39a724e8fac07490f5bbf3adb7333d7bd1c33aae586a7b171b7ea28339'
assert len({row['path'] for row in win['rows']})==49
for row in win['rows']:
    assert row['status']=='PASS' and row['expected_sha256']==row['actual_sha256']==cfg['input_pins'][row['path']]
assert not win['guest_launched'] and not win['adapter_imported_or_executed'] and not win['lease_created']
binding=load(B/'V3-BINDING.json')
assert sha(B/'V3-BINDING.json')=='62cc7c89ed2abe62b7ccdab5cbd69cb445d3080ae61ce35e050991452fc58fc6'
assert binding['runtime_config']['sha256']==sha(RT/'ROOT-REVIEW-PENDING.json')
assert binding['root_review_checklist_sha256']==sha(B/'ROOT-REVIEW-CHECKLIST.md')
refusal=E/'bounded-console-boot-v2/ROOT-PREFLIGHT-REFUSAL.json'
assert load(refusal)['status']=='REFUSED_BEFORE_GUEST'
assert sha(L/'reviewd676/REVIEW-CLEAR.json')=='6e70bd83bade582ae98f1fc764e30f509759c42a84d6ea2794356a7f0825641c'
for p in [RT/'ROOT-REVIEW-PENDING.json',RT/'capsule/CAPSULE.json',closurepath,B/'WINDOWS-PINS.json',B/'V3-BINDING.json',
          B/'windows-pin-preflight.py',B/'ROOT-REVIEW-CHECKLIST.md',refusal,L/'reviewd676/REVIEW-CLEAR.json',R/'check_binding.py',R/'REVIEW.md']:
    pins[str(p)]=sha(p)
put('READBACK.json',dict(status='PASS_METADATA_SOURCE_ONLY',files=pins,windows_pin_rows=49,source_unchanged=True,
                       binary_image_or_programme_read_by_reviewer=False,adapter_called=False,guest=False,process_kill=False))
put('REVIEW-CLEAR.json',dict(status='CLEAR',scope='V3 relocation/UNC and pending one-boot metadata binding only',
    adapter_source_commit=cfg['adapter_source_commit'],prior_source_review_sha256=sha(L/'reviewd676/REVIEW-CLEAR.json'),
    pending_configuration_sha256=sha(RT/'ROOT-REVIEW-PENDING.json'),capsule_manifest_sha256=sha(RT/'capsule/CAPSULE.json'),
    programme_assets_closure_receipt_sha256=sha(closurepath),windows_all49_preflight_receipt_sha256=sha(B/'WINDOWS-PINS.json'),
    readback_sha256=sha(R/'READBACK.json'),review_sha256=sha(R/'REVIEW.md'),generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    findings=[],execution_admitted=False,runtime_qualified=False,actual_guest=False,SDK=False,
    actual_binary_image_or_programme_read=False,source_tests_repeated=False,
    remaining_root_gates=['Approved config/alias/lease freeze','Fresh actual RR terminal/process/release/resource admission','Actual bound audit and title-goal decision']))
print(json.dumps({n:sha(R/n) for n in ['REVIEW-CLEAR.json','REVIEW.md','READBACK.json']}))
