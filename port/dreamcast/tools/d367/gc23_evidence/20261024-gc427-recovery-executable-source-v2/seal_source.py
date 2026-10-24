"""Freeze executable source for narrow review, with real media/baseline pending."""
from pathlib import Path
import datetime,difflib,hashlib,json,sys
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'kos-budget-retest-guest-prep-v1'
def row(p):return dict(size=Path(p).stat().st_size,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
def fresh(n,j):
 with (HERE/n).open('x') as f:json.dump(j,f,indent=1);f.write('\n')
if __name__=='__main__':
 if not (__debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):raise SystemExit('Isolated nonoptimized source')
 h=json.loads((HERE/'HOST-CONTROLS.json').read_bytes())
 if h['status']!='SOURCE_HOST_PENDING_OFF_PASS' or h['failures'] or h['errors']:raise SystemExit('Host checks fail')
 for n in ['controller.py','post_slot.py','launch.py','windows_entry.py','owned_process.py','judge.py']:
  if row(HERE/n)!=row(OLD/n):raise SystemExit('Controller logic changed')
 if any((HERE/n).exists() for n in ['CURRENT-BASELINE.json','RECOVERY-BINDING.json','TOOLCHAIN-SEAL.json','attempts']):raise SystemExit('Pending source seal requires unbound, unexecuted kit')
 delta=''.join(difflib.unified_diff((OLD/'common.py').read_text().splitlines(True),(HERE/'common.py').read_text().splitlines(True),fromfile='7b512/common.py',tofile='exec-v2/common.py'))
 with (HERE/'COMMON-SOURCE-DELTA.patch').open('x') as f:f.write(delta)
 fresh('SOURCE-STATUS.json',dict(status='EXECUTABLE_SOURCE_HOST_READY_FOR_REVIEW_PENDING_ROOT_OFF_HANDOFF',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),public_tests=h['tests'],public_pass=h['tests'],actual_poststage_and_resources='PENDING_NOT_PASS',original_six_controller_files_exact=True,new_actual_baseline=False,new_OFF_identity='UNKNOWN',SDK=0,stage=0,guest=0,production_locks=0,runtime_edits=0,scope='Reviewable executable plus strict binding/finalization code; root must hand back actual media before baseline is created'))
 files={p.name:row(p) for p in HERE.iterdir() if p.is_file()}
 fresh('SOURCE-REVIEW-SEAL.json',dict(status='SOURCE_HOST_EXECUTABLE_REVIEW_CANDIDATE_UNBOUND_NO_GUEST',source='427784b1f48aa30742850bb5025925ab619b740e',members=files))
 for name,pin in files.items():
  if row(HERE/name)!=pin:raise SystemExit('Source readback mismatch')
 fresh('SOURCE-READBACK.json',dict(status='EXACT_SOURCE_HOST_READBACK_PENDING_ACTUAL_OFF',seal=row(HERE/'SOURCE-REVIEW-SEAL.json'),members=len(files),bytes=sum(p['size'] for p in files.values()),guest_permission=False))
 print(json.dumps(dict(seal=row(HERE/'SOURCE-REVIEW-SEAL.json'),readback=row(HERE/'SOURCE-READBACK.json'))))
