from pathlib import Path
import hashlib,json
R=Path(r'C:\Game Dev\Emulators\codex-lanes\gc-motion24\pillow-isolated-prep-v1')
def row(p):return {'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
x={'status':'HOST_SOURCE_CONTROLS_ONLY_NO_GUEST','members':{p.relative_to(R).as_posix():row(p) for p in sorted(R.rglob('*')) if p.is_file()},'unchanged_helpers':json.loads((R/'PILLOW-PINS.json').read_text())['inputs']}
assert not (R/'SOURCE-SEAL.json').exists();(R/'SOURCE-SEAL.json').write_text(json.dumps(x,indent=2)+'\n');print(row(R/'SOURCE-SEAL.json'))
