"""Freeze source/plan metadata only; refuses overwrites, never inventories media."""
from pathlib import Path
import hashlib,json,os,sys
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'kos-budget-retest-guest-prep-v1'
STAGE=HERE.parent/'kos-budget-retest-media-prep-v2'
def ident(p):
 raw=Path(p).read_bytes();return dict(size=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(p):return json.loads(Path(p).read_text())
def fresh(n,j):
 with (HERE/n).open('x') as f:json.dump(j,f,indent=1);f.write('\n')
if __name__=='__main__':
 if not (__debug__ and os.name=='posix' and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):raise SystemExit('Use isolated WSL source invocation')
 assert ident(OLD/'TOOLCHAIN-SEAL.json')['sha256']=='7b5120956b13f1d25f50280120686a8efe45ed70f09ca14042722cb4eaa9997e'
 for n,v in read(OLD/'TOOLCHAIN-SEAL.json')['members'].items():assert ident(OLD/n)==v
 assert ident(STAGE/'TOOLCHAIN-SEAL.json')['sha256']=='2301e39cfb166ee25bab261f0323d1df27331155148b67453bc527ce7330bee1'
 for n,v in read(STAGE/'TOOLCHAIN-SEAL.json')['members'].items():assert ident(STAGE/n)==v
 drift=OLD/'BASELINE-DRIFT.json'
 with (HERE/'OLD-BASELINE-DISAPPEARANCE.json').open('xb') as f:f.write(drift.read_bytes())
 files=[OLD/n for n in ['TOOLCHAIN-SEAL.json','BASELINE-DRIFT.json','STATUS.json','controller.py','post_slot.py','launch.py','windows_entry.py','owned_process.py','judge.py','common.py','INPUT-PINS.json','PLAN.json','POSTSTAGE-PINS.json']]
 files += [STAGE/n for n in ['TOOLCHAIN-SEAL.json','BASELINE.json','core.py','BINDING.json','OFF-EXPECTED-MANIFEST.json','ON-EXPECTED-MANIFEST.json']]
 fresh('PREDECESSOR-PINS.json',dict(predecessors_are_immutable=True,files={str(p):ident(p) for p in files}))
 roots=read(STAGE/'BASELINE.json')['roots']
 roots += [str(STAGE),'/root/probe/gc-motion24-kos-budget-retest-media-v2','/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/kos-budget-retest-media-v2',str(OLD),str(HERE)]
 roots += [str(HERE.parent/n) for n in ['kos-budget-retest-stage-root-v1','review-kos-budget-retest-media-poststage-v1']]
 future_roots=[str(HERE.parent/n) for n in ['kos-budget-retest-guest-root-review-v1','kos-budget-retest-guest-root-review-v2','review-kos-budget-retest-media-poststage-v2']]
 fresh('RECOVERY-PLAN.json',dict(status='SOURCE_PLAN_ONLY_PENDING_PROTECTED_OFF_AND_FRESH_BOTH_MEDIA_READBACK',snapshot_utc='2026-10-24T13:26:05Z',source='427784b1f48aa30742850bb5025925ab619b740e',no_guest_grant=True,root_reported_compaction=dict(utc='2026-10-24T13:01:00Z',mechanism='hourly EvidenceCompaction -> Remove-StagedDiscs.ps1',count=2,independent_forensic_cause_verification=False,narrow_Name_guard_root_owned=True,KEEP_marker_additions_expected=True),retained_roots_to_revalidate=roots,finite_future_metadata_roots_record_absence_then_charge_all_new_inodes=future_roots,protected_shared_OFF_root=None,protected_shared_OFF_root_hint='_qa-media-8ce-recovery-v4/base-off (producer path pending)',new_baseline=None,new_baseline_may_finalize_only_after=['Protected OFF producer handback complete','Independent full OFF payload/IP/redirect/programme/track readback','Fresh corrected ON full payload/IP/redirect/programme/track readback','Explicit approved current root list','Full hash/dev/inode inventory of all current retained members and KEEP additions','Disappearance and all other current drift reconciled with root; no silent migration'],allocation=dict(new_delta_cap=5*1024**3//4,aggregate_cap=13*1024**3//2,C_start=26*1024**3,C_floor=24*1024**3,unique_inode_shared_OFF_charged_once=True,hash_equality_alone_does_not_deduplicate=True,prior_sealed_guards_unchanged=True),controller=dict(predecessor_seal='7b5120956b13f1d25f50280120686a8efe45ed70f09ca14042722cb4eaa9997e',reuse_exact_logic=['controller.py','post_slot.py','launch.py','windows_entry.py','owned_process.py','judge.py'],necessary_reviewed_delta_only=['current recovery context/capacity implementation','exact media roots/current baseline and receipts','fresh case paths and V2 grant bindings'],four_cases=[dict(arm=a,frag=f,held=49152) for a,f in [('off',0),('on',0),('off',1),('on',1)]],harness_seconds=45,exact_child_seconds=55,admission_seconds=180,runtime_seconds=95,overall_seconds=1300,root_slots=3,global_slots=16,H2=False,retry=False),qualification=dict(production_media_read=False,SDK=False,stage=False,guest=False,memory='NOT_RUN',future_executable_V2_adaptation='PENDING_ACTUAL_OFF_BINDING_AND_REVIEW')))
 fresh('BINDING-PENDING.json',dict(source='427784b1f48aa30742850bb5025925ab619b740e',predecessor_guest_seal='7b5120956b13f1d25f50280120686a8efe45ed70f09ca14042722cb4eaa9997e',state='PENDING_ACTUAL_OFF',old_baseline_disappearance_acknowledged=True,restored_old_image_identity=False,off_build_provenance='RAIN_PRODUCED_DISABLED_PAYLOAD_EQUIVALENT',off_program_sha256='e0168b780b102356c9bc3ee785753a659be6a020b1d1d3f8db92f14a90c16de5',off_root=None,on_root='/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/kos-budget-retest-media-v2/on',off_readback_path=None,on_readback_path=None,off_track_identity=None,on_track_identity=dict(size=1024618496,sha256='86d1f4107417912abc74af0e2005a3bbd79a2eed03e543721db6e022dd815dfa'),off_readback_identity=None,on_readback_identity=None,all14_exact=False,assets1697_exact=False,IP_exact=False,redirects6_exact=False))
