import datetime, hashlib, json, os, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent
LANE=ROOT.parent
SRC=Path('/root/probe/rr-safe-cycle23/port/dreamcast/tools/d367/rr_safe_cycle23')
REPO=SRC.parents[4]
COMMIT='2c6c62b483553c0788e9d12a15048b2c85ce7b34'
BASE='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(name,obj):
    with open(ROOT/name,'x',encoding='utf-8') as f: json.dump(obj,f,indent=2); f.write('\n')
assert subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()==COMMIT
assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain'],text=True).strip()
seal=json.loads((LANE/'SOURCE-SEAL.json').read_text())
for name,row in seal['files'].items(): assert sha(SRC/name)==row['sha256']
assert sha(LANE/'HOST-RESULTS.json')==seal['host_receipt_sha256']
sources={str(SRC/name):sha(SRC/name) for name in seal['files']}
for name in ['rr-cycle.sh','rr-jobs.sh','rr-flycast.sh','rr.sh']:
    p=Path('/root/rr/bin')/name; sources[str(p)]=sha(p)
for p in [Path('/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23/stat-guest-slot.sh'),Path('/mnt/c/Flycast-Evidence/re4-dreamcast/d367-harness-par/emu.cfg')]:
    sources[str(p)]=sha(p)
for name in ['fullplay/fp_run.py','fullplay/kos_squeeze.sh','fullplay/gdemu_gate.sh','trace_lock.sh']:
    spec=BASE+':port/dreamcast/tools/d367/'+name
    data=subprocess.check_output(['git','-C',str(REPO),'show',spec]); sources[spec]=hashlib.sha256(data).hexdigest()
assert sources[BASE+':port/dreamcast/tools/d367/fullplay/fp_run.py']=='646bd4eb42ff2063d4e07dc3754ab0c0d61e3b75348b934a48e7f63a25a07747'
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/rr-candidate-handback/fb254e82-20261024')
assert sha(E/'HANDBACK.json')=='bb0d3d044e276fc6860abe3974a140b0ba8f3d7d13abc2c7290e6d28588dffa8'
assert sha(E/'INSPECTION.json')=='d236b9d39f2d618d7c715f6d10c9d83bb10ebbabb7861b4064608a7ad7ecc447'
for name in ['HANDBACK.json','INSPECTION.json']: sources[str(E/name)]=sha(E/name)
C=Path('/mnt/c/Game Dev/Emulators/RE4DC-RR/cand-fb254e82')
handoff=json.loads((E/'HANDBACK.json').read_text())
for name,row in handoff['metadata_files'].items():
    assert sha(C/name)==row['sha256']; sources[str(C/name)]=sha(C/name)
st=Path('/root/rr/rr.lock').lstat()
import stat
assert stat.S_ISREG(st.st_mode)
host=json.loads((ROOT/'HOST-RESULTS.json').read_text()); assert host['status']=='PASS' and host['methods']==11
put('READBACK.json',dict(source_commit=COMMIT,files=sources,canonical_rr_lock_snapshot=dict(path='/root/rr/rr.lock',device=st.st_dev,inode=st.st_ino,regular=True,admission=False),actual_binary_or_image_read=False))
put('REVIEW-CLEAR.json',dict(status='CLEAR',adapter_source_commit=COMMIT,adapter_source_seal_sha256=sha(LANE/'SOURCE-SEAL.json'),
    scope='Frozen source only: separately admitted single final-GDI boot45/title/grace5; whole cycle refused',
    generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),findings=[],
    readback_sha256=sha(ROOT/'READBACK.json'),review_sha256=sha(ROOT/'REVIEW.md'),host_receipt_sha256=sha(ROOT/'HOST-RESULTS.json'),
    independent_host_methods=11,author_host_methods_read_not_rerun=16,whole_cycle_admitted=False,execution_admitted=False,
    actual_candidate_boot='PENDING',capsule_configuration='PENDING_ROOT_REVIEW',semantic_boot_decision='REQUIRED_SEPARATELY',
    actual_guest=False,SDK=False,actual_process_kill=False,console_or_image_read=False,media_mutation=False))
print(json.dumps({n:sha(ROOT/n) for n in ['REVIEW-CLEAR.json','REVIEW.md','READBACK.json','HOST-RESULTS.json']}))
