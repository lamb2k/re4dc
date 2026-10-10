#!/usr/bin/env python3
"""ps2leon: limit a role's weight palette count (pack_coarse_actor.py makes one palette entry per distinct weight
tuple; the owner path's workspace is 114 B x the largest chunk's entries and the FTRV skin takes <= 256 per chunk).
Rounds the role's weights to multiples of 1/step (largest remainder, the tuple still sums to 1), smallest step that
reaches the limit, and reports the largest skinned position change in the captured game pose (mesh.json bones:
capture x rest^-1, as pack_coarse_actor.py's quantization check).

  snap_weights.py <mesh.json> <out mesh.json> <role> <max palettes>
"""
import json, sys
from pathlib import Path
import numpy as np

src, dst, role, limit = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
m = json.loads(src.read_text())
P = np.asarray(m['positions_mm'])
rest = np.asarray([b['rest'] for b in m['bones']]); cap = np.asarray([b['capture'] for b in m['bones']])
skin = cap @ np.linalg.inv(rest)
verts = sorted({c['vertex'] for t in m['triangles'] if t['source_info'] == role for c in t['corners']})


def pose(i, w):
    return sum(x * (skin[b] @ np.r_[P[i], 1])[:3] for b, x in w)


def snap(w, step):
    raw = [x * step for _, x in w]
    base = [int(np.floor(r)) for r in raw]
    left = step - sum(base)
    order = sorted(range(len(w)), key=lambda k: -(raw[k] - base[k]))
    for k in order[:left]:
        base[k] += 1
    out = [(b, n / step) for (b, _), n in zip(w, base) if n > 0]
    return tuple(sorted(out))


before = len({tuple((b, x) for b, x in m['weights'][i]) for i in verts})
chosen = None
for step in (256, 128, 96, 64, 48, 32, 24, 16, 12, 8):
    new = {i: snap(m['weights'][i], step) for i in verts}
    n = len(set(new.values()))
    dev = max(np.linalg.norm(pose(i, new[i]) - pose(i, m['weights'][i])) for i in verts)
    print(f'step 1/{step}: palettes {n} (before {before}), largest captured-pose change {dev:.3f} mm')
    if n <= limit:
        chosen = (step, new, n, dev)
        break
assert chosen, 'no step reaches the limit'
step, new, n, dev = chosen
for i, w in new.items():
    m['weights'][i] = [[b, x] for b, x in w]
m['policy'] += f' Role {role} weights rounded to 1/{step} (palettes {before} -> {n}; captured pose change <= {dev:.3f} mm).'
dst.write_text(json.dumps(m, separators=(',', ':')))
print(json.dumps(dict(role=role, step=step, palettes_before=before, palettes=n, captured_pose_max_change_mm=dev)))
