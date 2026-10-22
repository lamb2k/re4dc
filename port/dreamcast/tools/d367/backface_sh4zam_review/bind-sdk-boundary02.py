from pathlib import Path
import hashlib,json
R=Path('/root/probe/codex-backface-sh4zam-fused');D=Path('/root/probe/codex-backface-sh4zam-review/port/dreamcast/tools/d367/backface_sh4zam_review');F=R/'port/dreamcast/tools/d367/backface_sh4zam_fused';O=R/'.fused-objects';M=json.loads((F/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
b=dict(scope='Read-only immutable stage1 to generic boundary02 identity mapping; no new execution',patch_sha256=sha(F/'0001-strip-sq-api.patch'),manifest_sha256=sha(F/'manifest.json'),patch_matches_manifest=sha(F/'0001-strip-sq-api.patch')==M['patch_sha256'],files={})
for name,pin in M['files'].items():b['files'][name]=dict(expected=pin,actual=sha(O/'boundary02/sdk'/name),exact=sha(O/'boundary02/sdk'/name)==pin)
b['elf_identity']={f:dict(old=sha(O/f),boundary02=sha(O/'boundary02'/f),exact=(O/f).read_bytes()==(O/'boundary02'/f).read_bytes())for f in ['walk-trace0.elf','walk-trace1.elf']}
assert b['patch_matches_manifest']and all(x['exact']for x in b['files'].values())and all(x['exact']for x in b['elf_identity'].values())
(D/'SDK-CALLER-BOUNDARY02-IDENTITY.json').write_text(json.dumps(b,indent=2)+'\n');print(json.dumps(b,indent=2))
