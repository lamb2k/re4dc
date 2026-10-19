"""occ_why.py <room.r4rc> <ex ey ez> <px py pz>: per occluder crossing eye -> enemy centre, which test fails."""
import sys
import numpy as np
import occ_eval as oe
V = oe.load(sys.argv[1])
E = np.array([float(v) for v in sys.argv[2:5]]); Pp = np.array([float(v) for v in sys.argv[5:8]])
R, H, M = oe.R, oe.H, oe.M
lo = Pp + np.array([-R - M, -100 - M, -R - M]); hi = Pp + np.array([R + M, H + M, R + M])
corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
C0 = Pp + np.array([0, 900.0, 0]); d = C0 - E
cx, cz = int((E[0] - V['x0']) // V['cs']), int((E[2] - V['z0']) // V['cs'])
f, cnt, _ = V['cells'][cx + cz * V['vw']]
lst = set(V['lists'][f:f + cnt])
for k, (C, half, side) in enumerate(V['occ']):
    n = np.cross(C[1] - C[0], C[3] - C[0]); n /= np.linalg.norm(n); n *= side
    dd = n @ C[0]
    den = n @ d
    if abs(den) < 1e-9:
        continue
    t = (dd - n @ E) / den
    if not 0 < t < 1:
        continue
    p = E + t * d
    ins = all(np.cross(C[(i + 1) % 4] - C[i], p - C[i]) @ n >= 0 for i in range(4)) or all(
        np.cross(C[(i + 1) % 4] - C[i], p - C[i]) @ n <= 0 for i in range(4))
    if not ins:
        continue
    se = n @ E - dd
    behind = np.all(corners @ n - dd < -half - 1)
    F, B = C + n * half, C - n * half
    print(k, 'inlist', k in lst, 'side_ok', se >= half + 50, 'behind', behind, 'shadowF', oe.quad_shadow(E, F, corners),
          'shadowB', oe.quad_shadow(E, B, corners), 'w', round(float(np.linalg.norm(C[1] - C[0]))),
          'h', round(float(np.linalg.norm(C[3] - C[0]))), 'ctr', np.round(C.mean(0)).astype(int))
