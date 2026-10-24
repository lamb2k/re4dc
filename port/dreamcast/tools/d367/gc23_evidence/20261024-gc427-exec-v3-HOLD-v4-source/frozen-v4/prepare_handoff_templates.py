"""Machine-readable UNKNOWN templates only; never approves root allocations."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent/'review-kos-budget-retest-media-poststage-v2'
OFF='/mnt/c/Flycast-Evidence/re4-dreamcast/rain-diag24-20261024/_qa-media-8ce-recovery-v4/base-off'
ON='/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/kos-budget-retest-media-v2/on'
def fresh(n,j):
 with (HERE/n).open('x') as f:json.dump(j,f,indent=1);f.write('\n')
if __name__=='__main__':
 fresh('ROOT-RECOVERY-HANDOFF-TEMPLATE.json',dict(approved_readonly_binding=False,scope='FULL_MEDIA_READBACK_AND_EXPLICIT_CURRENT_BASELINE_ONLY_NO_GUEST',source='427784b1f48aa30742850bb5025925ab619b740e',off_base=OFF,on_base=ON,poststage_identity=None,approved_old_to_current_drift_identity=None,explanation='Root verifies real fresh OFF first; ROOT-RECOVERY-HANDOFF.json at the fixed V2 independent review root binds actual READBACK and exact drift identity. No guest grant.'))
 fresh('POSTSTAGE-READBACK-TEMPLATE.json',dict(status='UNKNOWN_NOT_A_PASS',payload_contract_source='427784b1f48aa30742850bb5025925ab619b740e',media_producer=dict(tool_source='c3dd19b999d3c36e76318a4d3825f8d1ca7310ec',seal=dict(path=str(HERE.parent.parent/'rain-diag24/qa-media-observer-ext4-v5/TOOLCHAIN-SEAL.json'),identity=dict(size=8896,sha256='9377c8e8e06162def84513751ffe76dd78ef186bf0bef97a3ede53890eb39814')),off_complete=dict(path=OFF+'/COMPLETE.json',identity=None)),arms={a:dict(base=p,actual_producer_source='8ce5ee2d00027268c3e69c9c300b819c1b14c63f' if a=='off' else '427784b1f48aa30742850bb5025925ab619b740e',manifest=None,host_base_metadata=None,redirect_records=None,tracks=None) for a,p in [('off',OFF),('on',ON)]},scope='Template only. Final independent root READBACK must contain actual full manifest/redirect records/tracks, not expected placeholders. Actual producer V5 seal, OFF programme source8ce and payload comparison427 stay separate.'))
