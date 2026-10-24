"""Pure metadata/source/preflight readback, no SDK/Make."""
from pathlib import Path
import json,copy
from prepare_successor import semantic,actual_preflight,feature_absent,feature_signature,q,b
P=Path(__file__).resolve().parent
plan=json.loads((P/'PREPARATION.json').read_text());root=Path(plan['root'])
assert semantic(plan)
q.verify(plan['input_pins']);q.verify(plan['original_normal_pair_manifest']);q.verify(plan['preserved_failed_root_manifest'])
for arm in plan['arm_order']:
 q.verify({str(root/arm/'source'/n):r for n,r in plan['source_manifests'][arm].items()})
 assert not (root/arm/'out').exists() and not (root/arm/'build.log').exists()
 assert actual_preflight(root/arm/'source',plan['commands'][arm])['returncode']==0
feature_absent(feature_signature(root/'baseline/source'))
assert b.used(root)+sum(b.used(Path(p)) for p in plan['budget']['additional_preserved_preparation_roots'])<plan['budget']['owned_bytes_cap']
s=(P/'run_qa_three_arm.py').read_text();compile(s,str(P/'run_qa_three_arm.py'),'exec')
assert "for key in ['GC_ASSET_GATE','GC_ASSET_CATALOG_SHA256','GC_ASSET_MOTION_UNKNOWN']:expect.pop(key)" in s
assert "plan['preserved_failed_root_manifest']" in s and "feature_absent(feature_signature(root/'baseline/source'))" in s
print(json.dumps(dict(status='SUCCESSOR_PURE_READBACK_PASS',removed=plan['removed_baseline_options'],baseline_feature_absent=True,actual_three_preflights=True,seven_semantic_negatives=plan['negative_controls'],preserved_initial_files=len(plan['preserved_failed_root_manifest']),normal_files=len(plan['original_normal_pair_manifest']),owned_total=b.used(root)+sum(b.used(Path(p)) for p in plan['budget']['additional_preserved_preparation_roots']),SDK=0,Make_queries=0),indent=2))
