"""Finite source delta receipt; no code execution beyond hashes/diff metadata."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'kos-budget-retest-guest-exec-v2'
def row(p):
 raw=Path(p).read_bytes();return dict(size=len(raw),sha256=hashlib.sha256(raw).hexdigest())
if __name__=='__main__':
 assert row(OLD/'SOURCE-REVIEW-SEAL.json')==dict(size=4112,sha256='533ef84d9edf445047fbc9bac6ebebba8ce93e937787a3360176499eaf2512f4')
 pins=json.loads((OLD/'SOURCE-REVIEW-SEAL.json').read_bytes())['members']
 for n,v in pins.items():assert row(OLD/n)==v
 allowed={'recovery_context.py','bind_recovery.py','host_controls.py','prepare_handoff_templates.py','seal_source.py','README.md','I001-COMPLETION-PLAN.md','POSTSTAGE-READBACK-TEMPLATE.json'}
 changes={}
 for n in allowed:
  if row(OLD/n)==row(HERE/n):continue
  changes[n]=dict(before=row(OLD/n),after=row(HERE/n))
 assert set(changes)==allowed
 same=['common.py','controller.py','post_slot.py','launch.py','windows_entry.py','owned_process.py','judge.py','PLAN.json','INPUT-PINS.json']
 for n in same:assert row(OLD/n)==row(HERE/n)
 text=''
 for n in ['recovery_context.py','bind_recovery.py']:
  text+=''.join(difflib.unified_diff((OLD/n).read_text().splitlines(True),(HERE/n).read_text().splitlines(True),fromfile='533ef/'+n,tofile='exec-v3/'+n))
 with (HERE/'V3-BINDING-DELTA.patch').open('x') as f:f.write(text)
 report=dict(status='NARROW_V3_HOST_BASE_BINDING_SOURCE_DELTA_NO_MEDIA',parent_source_seal=row(OLD/'SOURCE-REVIEW-SEAL.json'),changes=changes,unchanged={n:row(HERE/n) for n in same},fixed_retained_roots=16,old_execV2_metadata_included=True,actual_OFF_identity=None,actual_baseline=False,H2_controller=False)
 with (HERE/'V3-DELTA.json').open('x') as f:json.dump(report,f,indent=1);f.write('\n')
