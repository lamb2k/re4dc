from pathlib import Path
import hashlib,json
D=Path('/root/probe/codex-backface-sh4zam-review/port/dreamcast/tools/d367/backface_sh4zam_review');R=Path('/root/probe/codex-backface-sh4zam/port/dreamcast');O=Path('/root/probe/backface-sh4zam-sdk-objects-20261022')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((O/'sdk-provenance.json').read_text());t=json.loads((O/'sdk-object-tests-final.json').read_text())
result={'source':'0f022725b','scope':'Read-only source/object receipt verification; no compiler or guest','provenance_exact':{},'objects_exact':{},'peer_source_exact':{},'sdk_provenance_sha256':sha(O/'sdk-provenance.json'),'object_tests_sha256':sha(O/'sdk-object-tests-final.json')}
for f,pin in p['source_hashes'].items():
 result['provenance_exact'][f]=sha(R/f)==pin
for f,pin in t['object_sha256'].items():result['objects_exact'][f]=sha(O/f)==pin
for f in ['game/platform/backface_sh4.S','game/platform/backface_sh4zam_area.inc','room/backface_sh4zam.hpp']:
 result['peer_source_exact'][f]=sha(R/f)==sha(Path('/root/probe/codex-backface-sh4zam-sdk/port/dreamcast')/f)
result['macro_pin_exact']=sha(R/'game/platform/backface_sh4zam_area.inc')==p['target_macro_sha256']
assert all(result['provenance_exact'].values())and all(result['objects_exact'].values())and all(result['peer_source_exact'].values())and result['macro_pin_exact']
(D/'SDK-0f022725b-REVIEW-IDENTITIES.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
