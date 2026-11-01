#!/usr/bin/env python3
"""lookw26.py <cg fixture dir> <out dir> <room:etNNNN[,etNNNN]>...: frozen still warps facing an etc model placement
(the purge24 lookw.py rule: Leon D units from the placement nearest the room's census warp, toward that warp, facing
the object, god, freeze 600). Placements from the GameCube room's ETS (big-endian), read from the GC disc.
lane props-ps2-26 (tier-2 stills of the props26 members)."""
import math
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1])]
import ps2_objects as po  # noqa: E402
import room_smd as rs  # noqa: E402
from assetpipe.rooms import GcIso  # noqa: E402

D = 1500
FX, OUT = sys.argv[1], sys.argv[2]
g = GcIso(po.GC_ISO)
for spec in sys.argv[3:]:
    room, ids = spec.split(':')
    want = {int(x[2:4], 16) for x in ids.split(',')}
    gd = g.read(next(k for rr, k in g.rooms() if rr == room))
    if gd[:32] == rs.CONTAINER_MAGIC:
        gd = rs.decode_das(gd)
    objs = []
    for tag, s, e in rs.tagged_entries(gd, '>'):
        if tag.rstrip(b'\0') != b'ETS':
            continue
        n = struct.unpack_from('>H', gd, s)[0]
        for k in range(n):
            p = s + 16 + k * 40
            i, sl = struct.unpack_from('>2H', gd, p)
            f = struct.unpack_from('>6f', gd, p + 16)
            if i in want:
                objs.append((i, sl, f[3:6]))
    lines = open('%s/cg-%s.txt' % (FX, room)).read().splitlines()
    ex = ez = ey = None
    keep = []
    for ln in lines:
        t = ln.split()
        k = t[0] if t else ''
        if k == 'pos':
            ex, ey, ez = float(t[1]), float(t[2]), float(t[3])
            continue
        if k in ('ang', 'goto', 'kill', 'killrep', 'census', 'freeze', 'god', 'name', 'act', 'alivelog', 'dump') or k.startswith('#'):
            continue
        keep.append(ln)
    if not objs:
        print(room, 'no placement of', ids)
        continue
    i, sl, (ox, oy, oz) = min(objs, key=lambda o: math.hypot(o[2][0] - ex, o[2][2] - ez))
    vx, vz = ex - ox, ez - oz
    n = math.hypot(vx, vz) or 1.0
    d = min(D, n)
    px, pz = ox + d * vx / n, oz + d * vz / n
    a = math.atan2(ox - px, oz - pz)
    out = ['name look-%s' % room] + keep + ['pos %d %d %d' % (px, oy, pz), 'ang %.4f' % a, 'god', 'freeze 600']
    Path(OUT, 'look-%s.txt' % room).write_text('\n'.join(out) + '\n')
    print(room, 'et%02x00 #%d at %d %d %d; leon %d %d ang %.3f' % (i, sl, ox, oy, oz, px, pz, a))
