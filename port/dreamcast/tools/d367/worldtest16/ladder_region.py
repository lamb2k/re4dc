#!/usr/bin/env python3
"""ladder_region.py <ps2_world_vert_ladder.py args>: the ladder with region landmarks (worldtest16).
WT_PROTECT_BOX="x0,z0,x1,z1,maxsize[;...]" (world mm): every cluster with a placement box that overlaps the xz box and is
at most maxsize wide (x and z) keeps level 0, like a --protect-bins landmark. For rooms whose landmarks share a mesh bin
with the rest of the village (r101: the burning stake's crossbar and pyre planks are clusters of large bins)."""
import os, sys, importlib.util
T = os.environ.get('WT_TOOLS', '/root/probe/codex-cpu-t15-20261016/tree/port/dreamcast/tools')  # WT_TOOLS: another tools tree
sys.path.insert(0, T)
spec = importlib.util.spec_from_file_location('lad', T + '/ps2_world_vert_ladder.py')
lad = importlib.util.module_from_spec(spec); spec.loader.exec_module(lad)
BOXES = [tuple(float(v) for v in b.split(',')) for b in os.environ.get('WT_PROTECT_BOX', '').split(';') if b]
_init = lad.Ladder.__init__


def init(self, a):
    _init(self, a)
    n = c = 0
    for key, inf in self.info.items():
        for wl, wh in inf['box']:
            if any(wl[0] <= x1 and wh[0] >= x0 and wl[2] <= z1 and wh[2] >= z0 and max(wh[0] - wl[0], wh[2] - wl[2]) <= ms
                   for x0, z0, x1, z1, ms in BOXES):
                inf['bin'] = -1; n += 1; c += inf['corners']
                break
    if n:
        self.protect.add(-1)
        self.baked.discard(None)
    print('region landmarks: %d clusters, %d corners kept at level 0 (bin -1 in the report)' % (n, c), file=sys.stderr)


lad.Ladder.__init__ = init
# WT_PROTECT_VBOX="x0,y0,z0,x1,y1,z1[;...]" (world mm, per-vertex mode): vertices inside a box get a zero error bound, so no
# collapse moves them (the clusters of r101 span tens of metres: a cluster or bin rule cannot isolate the stake).
VBOXES = [tuple(float(v) for v in b.split(',')) for b in os.environ.get('WT_PROTECT_VBOX', '').split(';') if b]
_eps = lad.Ladder.eps_fn
HITS = [0]


def eps_fn(self, mi, px, scale):
    f = _eps(self, mi, px, scale)
    if not VBOXES:
        return f
    pls = self.mesh_pls.get(mi, []) or [((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0))]

    def g(p):
        for aff in pls:
            w = [aff[r][0] * p[0] + aff[r][1] * p[1] + aff[r][2] * p[2] + aff[r][3] for r in range(3)]
            if any(b[0] <= w[0] <= b[3] and b[1] <= w[1] <= b[4] and b[2] <= w[2] <= b[5] for b in VBOXES):
                HITS[0] += 1
                return 0.0
        return f(p)
    g.dist = f.dist
    return g


lad.Ladder.eps_fn = eps_fn
import atexit
atexit.register(lambda: print('vertex-box landmarks: %d zero-bound vertex queries' % HITS[0], file=sys.stderr))
if __name__ == '__main__':
    lad.main()
