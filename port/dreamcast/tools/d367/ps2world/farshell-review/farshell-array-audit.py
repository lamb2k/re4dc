"""Windows numpy supplement to read-only far-shell census."""
from pathlib import Path
import json
import hashlib
import numpy as np

root=Path(r'C:\Game Dev\Emulators')
p=root/'_codex_cpu_t15_20261016/farshell-source-census.json'
d=json.loads(p.read_text())
peer=root/'farshell-20261016'
eyes=np.load(peer/'work/r101/eyes.npy')
d['peer_camera_samples']=dict(count=len(eyes), bounds_mm=[eyes.min(0).tolist(),eyes.max(0).tolist()],
    sha256=hashlib.sha256((peer/'work/r101/eyes.npy').read_bytes()).hexdigest(),
    limitation='Enemy route nodes plus 1.6m and explicit extras; not continuous player/camera coverage.')
w=np.load(peer/'work/r101/world.npz')
protected={r['placement'] for r in d['peer_source']['rows'] if r['category']!='immutable_candidate'}
mask=(w['pass_']==0)&np.isin(w['placement'],list(protected))
d['peer_opaque_input_protected']=dict(triangles=int(mask.sum()),
    placements=sorted(set(int(x) for x in w['placement'][mask])),
    input_triangles=int((w['pass_']==0).sum()),
    note='Protected source triangles are admitted to the BVH. Packed shell has no placement lineage, so final protected overlap is unproven.')
d.pop('numpy_unavailable',None)
p.write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({k:d[k] for k in ['peer_camera_samples','peer_opaque_input_protected']},indent=2))
