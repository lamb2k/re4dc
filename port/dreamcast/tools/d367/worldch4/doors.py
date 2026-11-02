#!/usr/bin/env python3
"""doors.py ROOM...   (WSL; lane world-ch4, 2026-11-02; test tooling)
The door areas (sce_at.h SceAtWork type 1, SceAtDoor payload) of each room's GameCube AEV (debug disc room archive):
area number, the area's centre (AreaData body read as an xz quad: four (x, z) float pairs, the common door shape), and
the destination room / position / angle / lock. Feeds the chapter 4 route files (worldch4/routes) and warp presets.
Output: one TSV row per door: room no cx cz dst_room dst_x dst_y dst_z dst_ang lock lockflag."""
import math, struct, sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[2])]
import ps2_objects as po  # noqa: E402
from assetpipe.rooms import GcIso  # noqa: E402

g = GcIso(po.GC_ISO)
keys = dict(g.rooms())
print('room\tno\tcx\tcz\tdst_room\tdst_x\tdst_y\tdst_z\tdst_ang\tlock\tlockflag')
for room in sys.argv[1:]:
    gd = g.read(keys[room])
    if gd[:32] == po.rs.CONTAINER_MAGIC:
        gd = po.rs.decode_das(gd)
    for t, s, e in po.rs.tagged_entries(gd, '>'):
        if t.rstrip(b'\0') != b'AEV':
            continue
        n = struct.unpack_from('>H', gd, s + 6)[0]
        for i in range(n):
            p = s + 16 + i * 156
            if gd[p + 0x35] != 1:
                continue
            q = struct.unpack_from('>8f', gd, p + 8)
            xs, zs = q[0::2], q[1::2]
            cx, cz = (sum(xs) / 4, sum(zs) / 4) if all(map(math.isfinite, q)) else (float('nan'),) * 2
            d = p + 0x5C
            x, y, z, a = struct.unpack_from('>4f', gd, d)
            st, rm, lk, lf = gd[d + 0x10], gd[d + 0x11], gd[d + 0x12], gd[d + 0x13]
            print('%s\t%d\t%.0f\t%.0f\tr%x%02x\t%.0f\t%.0f\t%.0f\t%.4f\t%d\t%d' % (room, gd[p + 0x36], cx, cz, st, rm, x, y, z, a, lk, lf))
