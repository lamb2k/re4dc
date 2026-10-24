"""Seal this pending preparation; does not seal a baseline or authorize guests."""
from pathlib import Path
import datetime,hashlib,json,sys
HERE=Path(__file__).resolve().parent
def row(p):
 raw=Path(p).read_bytes();return dict(size=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(p):return json.loads(Path(p).read_text())
def fresh(n,j):
 with (HERE/n).open('x') as f:json.dump(j,f,indent=1);f.write('\n')
if __name__=='__main__':
 if not (__debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):raise SystemExit('Isolated nonoptimized source only')
 for p,pin in read(HERE/'PREDECESSOR-PINS.json')['files'].items():assert row(p)==pin,'Frozen predecessor changed'
 assert read(HERE/'HOST-CONTROLS.json')['status']=='PASS'
 assert read(HERE/'BINDING-PENDING.json')['state']=='PENDING_ACTUAL_OFF'
 assert not (HERE/'CURRENT-BASELINE.json').exists()
 assert (HERE/'OLD-BASELINE-DISAPPEARANCE.json').read_bytes()==(HERE.parent/'kos-budget-retest-guest-prep-v1'/'BASELINE-DRIFT.json').read_bytes()
 files={p.name:row(p) for p in sorted(HERE.iterdir()) if p.is_file()}
 assert len(files)==len(list(HERE.iterdir())) and all(not p.is_symlink() for p in HERE.iterdir())
 fresh('PLAN-SEAL.json',dict(status='SEALED_SOURCE_PLAN_PENDING_OFF_NO_GUEST',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),members=files,production_media_read=0,SDK=0,stage=0,guest=0,baseline_frozen=False,guest_controller_v2_executable=False,scope='Preparation milestone only; exact runtime successor pending real protected OFF/readback'))
 for n,pin in files.items():assert row(HERE/n)==pin
 fresh('READBACK.json',dict(status='EXACT_SOURCE_PLAN_READBACK_PASS_NO_BASELINE_NO_GUEST',seal=row(HERE/'PLAN-SEAL.json'),members=len(files),bytes=sum(x['size'] for x in files.values()),no_actual_programmes_or_assets_copied=True))
