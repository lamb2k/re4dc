"""edit_thinedge.py <tools dir>: worldtest16 B lesson from the r101 fence rails: ps2_world_vert_ladder.py --thin-edge-frac."""
import os, sys
D = sys.argv[1]
p = os.path.join(D, 'ps2_world_vert_ladder.py')
s = open(p).read()
pairs = [
    ("""    ve = {i: eps_of(p) for i, p in pos.items()}
    if a.thin_frac > 0:""", """    ve = {i: eps_of(p) for i, p in pos.items()}
    tef = getattr(a, 'thin_edge_frac', 0.0)
    if tef > 0:
        # --thin-edge-frac (lane worldtest16, 10-16): a vertex never moves more than this share of its shortest edge, at
        # every distance. The piece guard below misses thin parts fused into a larger piece (r101 mesh 0x17: the house
        # front and its fence rails are one connected piece, so the piece box is house-sized) and works only within
        # --thin-mm of the walk path; the rails 11-14 m from the village cross collapsed. Rails, slats, posts, frames and
        # chair legs have short cross edges, so they keep their shape; large ground and wall triangles are not limited.
        short = {}
        for t, _ in tris:
            for u, v in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                e = math.sqrt(sum((pos[u][k] - pos[v][k]) ** 2 for k in range(3)))
                if e > 0:
                    for x in (u, v):
                        if e < short.get(x, 1e30):
                            short[x] = e
        for i in ve:
            if i in short:
                ve[i] = min(ve[i], tef * short[i])
    if a.thin_frac > 0:"""),
    ("""    ap.add_argument('--thin-mm', type=float, default=0.0,""", """    ap.add_argument('--thin-edge-frac', type=float, default=0.0,
                    help='per-vertex mode: a vertex moves at most this share of its shortest incident edge, at any '
                         'distance (thin rails / slats / posts inside larger mixed pieces; 0 = off)')
    ap.add_argument('--thin-mm', type=float, default=0.0,"""),
]
for a, b in pairs:
    assert s.count(a) == 1, a[:60]
    s = s.replace(a, b)
assert 'import math' in s or 'math.' in s
open(p, 'w').write(s)
import ast; ast.parse(s)
print('edited', p)
