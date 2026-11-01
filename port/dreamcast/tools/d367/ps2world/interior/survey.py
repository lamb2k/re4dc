"""survey.py <census work dir> x0 x1 z0 z1 y step: a top-view map of a house: for each grid eye, up/down hit (ceiling /
floor height) and whether it's enclosed (8 horizontal rays hit within 15 m). Prints one row per z."""
import sys, struct
from pathlib import Path
import numpy as np
work = Path(sys.argv[1]); x0, x1, z0, z1, y, step = map(float, sys.argv[2:8])
b = (work / 'tris.bin').read_bytes(); n = struct.unpack_from('<I', b, 0)[0]
rec = np.frombuffer(b, dtype=[('v', '<f4', (9,)), ('inst', '<u4'), ('flags', '<u4')], count=n, offset=4)
v = rec['v'].astype(np.float64).reshape(-1, 3, 3)[(rec['flags'] & 1) != 0]
c = v.mean(1); keep = (c[:, 0] > x0 - 20000) & (c[:, 0] < x1 + 20000) & (c[:, 2] > z0 - 20000) & (c[:, 2] < z1 + 20000)
v = v[keep]; A = v[:, 0]; E1 = v[:, 1] - A; E2 = v[:, 2] - A
def first(o, d, tmax=30000.0):
    p = np.cross(d, E2); det = (E1 * p).sum(1); ok = np.abs(det) > 1e-9
    inv = np.where(ok, 1 / np.where(ok, det, 1), 0); s = o - A
    u = (s * p).sum(1) * inv; q = np.cross(s, E1); w = (q @ d) * inv; t = (q * E2).sum(1) * inv
    m = ok & (u >= 0) & (w >= 0) & (u + w <= 1) & (t > 1) & (t < tmax)
    return float(t[m].min()) if m.any() else None
for z in np.arange(z0, z1 + 1, step):
    row = []
    for x in np.arange(x0, x1 + 1, step):
        e = np.array([x, y, z]); up = first(e, np.array([0, 1.0, 0]), 12000)
        walls = sum(first(e, np.array([np.cos(k * np.pi / 4), 0, np.sin(k * np.pi / 4)]), 15000) is not None for k in range(8))
        row.append('#' if up is None else ('%d' % min(9, int((up + y) / 1000))) if walls >= 8 else '.')
    print('%7d %s' % (z, ''.join(row)))
print('x from %d step %d; digit = ceiling height in m (enclosed, 8 walls), . = roofed but open, # = no roof' % (x0, step))
