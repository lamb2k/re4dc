"""indoor.py <census work dir> x,y,z ...: for each eye, the census indoor test (opaque above within 12 m, walls hit
by 8 horizontal rays within 15 m) plus the first-hit distances along +-x, +-z, +-y (static opaque only)."""
import sys, struct
from pathlib import Path
import numpy as np

work = Path(sys.argv[1])
b = (work / 'tris.bin').read_bytes(); n = struct.unpack_from('<I', b, 0)[0]
rec = np.frombuffer(b, dtype=[('v', '<f4', (9,)), ('inst', '<u4'), ('flags', '<u4')], count=n, offset=4)
v = rec['v'].astype(np.float64).reshape(-1, 3, 3)
import json
meta = json.loads((work / 'meta.json').read_text())
occ = (rec['flags'] & 1) != 0
v = v[occ]
A = v[:, 0]; E1 = v[:, 1] - A; E2 = v[:, 2] - A


def first(o, d, tmax=30000.0):
    p = np.cross(d, E2); det = (E1 * p).sum(1); ok = np.abs(det) > 1e-9
    inv = np.where(ok, 1 / np.where(ok, det, 1), 0); s = o - A
    u = (s * p).sum(1) * inv; q = np.cross(s, E1); w = (q @ d) * inv; t = (q * E2).sum(1) * inv
    m = ok & (u >= 0) & (w >= 0) & (u + w <= 1) & (t > 1) & (t < tmax)
    return float(t[m].min()) if m.any() else None


for a in sys.argv[2:]:
    e = np.array([float(x) for x in a.split(',')])
    up = first(e, np.array([0, 1.0, 0]), 12000)
    walls = 0
    for k in range(8):
        ang = k * np.pi / 4
        if first(e, np.array([np.cos(ang), 0, np.sin(ang)]), 15000) is not None: walls += 1
    dist = {nm: first(e, np.array(d, float)) for nm, d in
            (('-x', (-1, 0, 0)), ('+x', (1, 0, 0)), ('-y', (0, -1, 0)), ('+y', (0, 1, 0)), ('-z', (0, 0, -1)), ('+z', (0, 0, 1)))}
    print(a, 'indoor' if (up is not None and walls >= 6) else 'outdoor', 'walls=%d' % walls,
          ' '.join('%s=%s' % (k, 'none' if x is None else int(x)) for k, x in dist.items()))
