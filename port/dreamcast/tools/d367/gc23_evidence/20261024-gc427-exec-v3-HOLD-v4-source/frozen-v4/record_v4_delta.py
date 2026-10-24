"""Record exact narrow successor and preserved independent HOLD references."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'kos-budget-retest-guest-exec-v3'
def row(p):
 raw=Path(p).read_bytes();return dict(size=len(raw),sha256=hashlib.sha256(raw).hexdigest())
if __name__=='__main__':
 assert row(OLD/'SOURCE-REVIEW-SEAL.json')==dict(size=5442,sha256='0296f5782e8c94ccc65a46cfcd5171fdf5d6c3348914b6af80190245961c4dbc')
 pins=json.loads((OLD/'SOURCE-REVIEW-SEAL.json').read_bytes())['members']
 for n,pin in pins.items():assert row(OLD/n)==pin
 changed=['bind_recovery.py','recovery_context.py','host_controls.py','README.md','seal_source.py']
 same=['common.py','controller.py','post_slot.py','launch.py','windows_entry.py','owned_process.py','judge.py','PLAN.json','INPUT-PINS.json','POSTSTAGE-READBACK-TEMPLATE.json','ROOT-RECOVERY-HANDOFF-TEMPLATE.json']
 for n in same:assert row(HERE/n)==row(OLD/n)
 delta=''
 for n in ['bind_recovery.py','recovery_context.py','host_controls.py']:
  delta+=''.join(difflib.unified_diff((OLD/n).read_text().splitlines(True),(HERE/n).read_text().splitlines(True),fromfile='0296/'+n,tofile='exec-v4/'+n))
 with (HERE/'V4-SOURCE-DELTA.patch').open('x') as f:f.write(delta)
 review=HERE.parent/'review-kos-budget-retest-guest-exec-v3-worldmeter'
 refs={n:dict(path=str(review/n),identity=row(review/n)) for n in ['REVIEW-HOLD.json','REVIEW.md','REVIEW-SEAL.json','ENCODED-COLLISION-REPRO.json']}
 assert refs['REVIEW-HOLD.json']['identity']['sha256']=='d6002af58bff6f68c3ab85edf9743a4328968809e5c8a9bb26c39839a2961edb'
 report=dict(status='NARROW_V4_CALLABLE_SHADOWING_REPAIR_SOURCE_ONLY',parent_source_seal=row(OLD/'SOURCE-REVIEW-SEAL.json'),changed={n:dict(before=row(OLD/n),after=row(HERE/n)) for n in changed},unchanged={n:row(HERE/n) for n in same},retained_roots=17,preserved_execV3_metadata_charged=True,independent_V3_HOLD=refs,regression='Actual binder statements drift through outputs execute successfully; same V3 statements raiseTypeError',actual_baseline=False,actual_binding=False,SDK=0,stage=0,guest=0)
 with (HERE/'V4-DELTA.json').open('x') as f:json.dump(report,f,indent=1);f.write('\n')
 actual=HERE.parent.parent/'rain-diag24/review-qa-media-ext4-v5-off-actual-v1'
 off_refs={n:dict(path=str(actual/n),identity=row(actual/n)) for n in ['ACTUAL-READBACK.json','BINDER-SUMMARY.json']}
 assert off_refs['ACTUAL-READBACK.json']['identity']['sha256']=='0c5601ca579b65dad85d5dd25c65de87262d405da832cabd374f304fe93028cd'
 with (HERE/'ROOT-ACTUAL-OFF-REFERENCE.json').open('x') as f:json.dump(dict(status='ROOT_REVIEWED_OFF_STATIC_REFERENCE_NOT_LOCAL_BINDING',references=off_refs,track03_sha256='e9cb88f5000c8fec83fc9d92715ffef164a4941153887b0444527308c998840e',actual_producer_source='8ce5ee2d00027268c3e69c9c300b819c1b14c63f',producer_tool_source='c3dd19b999d3c36e76318a4d3825f8d1ca7310ec',payload_comparison_source='427784b1f48aa30742850bb5025925ab619b740e',local_media_readback_or_baseline=False),f,indent=1);f.write('\n')
