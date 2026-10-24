from pathlib import Path
import json,hashlib,difflib
R=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/full-h2-prep-v2');P=R.parent/'full-h2-prep-v1';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(P/'SOURCE-SEAL.json')=='bb0b32798e517b4220b120542c3cdf411137bde24df4838b58bcbf9c3faeb137'
for n,v in json.loads((P/'SOURCE-SEAL.json').read_text())['members'].items():assert (P/n).stat().st_size==v['size'] and sha(P/n)==v['sha256']
hold=R.parent/'review-full-h2-prep-v1/REVIEW-HOLD.json';assert sha(hold)=='16b24906d97de391ce4808b1ac6e357e12ca585555fe3477233cd2ac15d5b4bf'
(R/'PARENT-V1.json').write_text(json.dumps(dict(parent_source_seal=sha(P/'SOURCE-SEAL.json'),review_hold=dict(path=str(hold),sha256=sha(hold)),original_members_unchanged=15,grant_scope='Two confirmed timing/containment defects only',native_guest_execution=False),indent=2)+'\n')
patch=''
for n in ['core.py','run.py','windows_entry.py']:patch+=''.join(difflib.unified_diff((P/n).read_text().splitlines(True),(R/n).read_text().splitlines(True),fromfile='frozen-v1/'+n,tofile='v2/'+n))
(R/'SOURCE-DELTA.patch').write_text(patch)
for n in ['owned_process.py','INPUTS.json','ROOT-GRANT-TEMPLATE.json','test_host.py']:assert (P/n).read_bytes()==(R/n).read_bytes(),n
print(json.dumps(dict(V1_unchanged=True,accepted_inputs_and_original_controls_unchanged=True,delta_bytes=len(patch))))