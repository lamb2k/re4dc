from pathlib import Path
import json,hashlib
R=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/full-h2-prep-v1');P=R.parent/'kos-budget-retest-guest-exec-v3'
def row(p):b=p.read_bytes();return dict(size=len(b),sha256=hashlib.sha256(b).hexdigest())
inp=json.loads((P/'INPUT-PINS.json').read_text());h=Path(inp['helpers']['harness']['path']);root=h.parent
pins={'helpers':inp['helpers'],'template':inp['template'],**{k:inp[k] for k in ['pillow_launcher','pillow_manifest','pillow_seal']}}
pins['fixtures']={n:dict(path=str(root/'segments'/('h2-'+n+'.txt')),identity=row(root/'segments'/('h2-'+n+'.txt'))) for n in ['warp','pad']}
pins['parent_common']=row(P/'common.py');pins['parent_owned_process']=row(P/'owned_process.py')
(R/'INPUTS.json').write_text(json.dumps(pins,indent=2)+'\n');(R/'owned_process.py').write_bytes((P/'owned_process.py').read_bytes())