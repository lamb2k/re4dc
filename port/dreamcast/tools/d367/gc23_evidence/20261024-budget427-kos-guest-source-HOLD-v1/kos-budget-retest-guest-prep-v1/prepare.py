"""Source/input metadata only. No slots, SDK, stage or guest."""
from pathlib import Path
import json,sys,types
HERE=Path(__file__).resolve().parent
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
p=HERE/'common.py';c=types.ModuleType('guest_common');c.__file__=str(p);sys.modules[c.__name__]=c;exec(compile(p.read_bytes(),str(p),'exec'),c.__dict__)
k=c.context();old=c.read(HERE.parent/'kos-census-media-root-review-v1/ROOT-CALLER-GUEST-GRANT-v1.json');helpers={}
for name,v in old['helpers'].items():
 c.verify(v['path'],v['identity']);helpers[name]={**v,'windows_path':c.win(v['path'])}
helpers['WSL_python']={'path':'/usr/bin/python3','identity':c.row('/usr/bin/python3')}
template={}
for n,v in old['template'].items():
 p=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/d367-harness-par')/n;c.verify(p,v);template[n]={'path':str(p),'identity':v}
pillow=HERE.parent/'pillow-isolated-prep-v1';assert c.sha(pillow/'SOURCE-SEAL.json')=='3bcff1c5a4eb7f5823296be065c097a246251ffd3c3d3d42ecf11073eeb7add2'
fixtures={}
for frag in [0,1]:
 p=HERE.parent/'qa-memory-media-prep/fixtures'/('kos-fight-49152-'+str(frag)+'.txt');fixtures[str(frag)]={'path':str(p),'identity':c.row(p)}
ps=Path('/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe')
c.fresh(HERE/'INPUT-PINS.json',dict(helpers=helpers,template=template,fixtures=fixtures,powershell=c.row(ps),pillow_launcher=dict(path=str(pillow/'pillow_launcher.py'),windows_path=c.win(pillow/'pillow_launcher.py'),identity=c.row(pillow/'pillow_launcher.py')),pillow_manifest=dict(path=str(pillow/'PILLOW-PINS.json'),identity=c.row(pillow/'PILLOW-PINS.json')),pillow_seal=dict(path=str(pillow/'SOURCE-SEAL.json'),identity=c.row(pillow/'SOURCE-SEAL.json')),parent_caller=dict(path=str(HERE.parent/'kos-census-media-root-review-v1/root-caller-pair-v2.py'),identity=c.row(HERE.parent/'kos-census-media-root-review-v1/root-caller-pair-v2.py'))))
plan=c.read(c.MEDIA/'GUEST-PROPOSAL.json');plan.update(status='PREPARED_SOURCE_HOST_ONLY_POSTSTAGE_UNKNOWN',admission_seconds=180,runtime_parent_seconds=95,overall_seconds=1300,admission_handshake='exact case+fresh nonce+grant+kit+strict source/helper/disc/baseline/cap/cache+kernel locks before WindowsPython',metadata_roots=list(map(str,c.META_ROOTS)),no_automatic_RR_wait_or_retry=True)
c.fresh(HERE/'PLAN.json',plan)
c.fresh(HERE/'ROOT-GUEST-GRANT-TEMPLATE.json',dict(approved=False,authorization='FOUR_KOS48_CORRECTED427_CONSOLE_ONLY',scope='CAPTURES_AND_BOUNDED_KOS_JUDGEMENT_ONLY',source=c.SOURCE,kit_sha256='ROOT_PIN_FINAL_SEAL',media_kit_sha256=c.MEDIA_SEAL,case_order=[0,1,2,3],seconds=45,exact_child_seconds=55,parent_seconds=95,admission_seconds=180,overall_seconds=1300,new_delta_cap=k.DELTA,aggregate_cap=k.AGG,root_slots=3,global_slots=16,H2=False,poststage=dict(path=str(c.META_ROOTS[1]/'READBACK.json'),identity='UNKNOWN_UNTIL_POSTSTAGE_CLEAR'),metadata_allowlists={str(c.META_ROOTS[0]):['CONTROLLER.log','GRANT-IDENTITY.json','root-stage-observer.py','PROCESS.json'],str(c.META_ROOTS[1]):['ROOT_MUST_LIST_ACTUAL_SEALED_METADATA.json'],str(c.META_ROOTS[2]):['ROOT-GUEST-GRANT.json','root-guest-observer.py','CONTROLLER.log','PROCESS.json']}))
c.fresh(HERE/'POSTSTAGE-INPUT-TEMPLATE.json',dict(status='UNKNOWN_NOT_A_PASS',source=c.SOURCE,media_kit_sha256=c.MEDIA_SEAL,pair_complete_identity='UNKNOWN',arms={arm:dict(base=str(k.OFF if arm=='off' else k.FINAL/'on'),readback_path='ROOT_FRESH_INDEPENDENT_READBACK_'+arm,readback_identity='UNKNOWN',complete_identity='UNKNOWN') for arm in ['off','on']}))
print(json.dumps(dict(status=plan['status'],resources=c.capacity(k),stage_or_guest=0)))
