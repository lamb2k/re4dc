#!/usr/bin/env python3
"""lookw.py <fixtures dir> <room:etNN[,etNN]>...: frozen still warps (look-<room>.txt) facing the converted etc model
placement nearest the room's castgc warp position (objs13 lookwarps.py rule: Leon D units from it toward the entry,
facing it, god, freeze 600). Positions from the GC ETS (big-endian). lane purge-props24."""
import math
import struct
import sys
T = '/root/work/lanes/purge-props24/port/dreamcast/tools'
sys.path[:0] = [T, T + '/../../../tools']
import room_smd as rs  # noqa
FX = sys.argv[1]
D = 1500
for spec in sys.argv[2:]:
    room, ids = spec.split(':')
    want = {int(x[2:4], 16) for x in ids.split(',')}
    gd = open('/root/work/lanes/purge-props24-scratch/gcarc/%s.arc' % room, 'rb').read()
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
    i, sl, (ox, oy, oz) = min(objs, key=lambda o: math.hypot(o[2][0] - ex, o[2][2] - ez))
    vx, vz = ex - ox, ez - oz
    n = math.hypot(vx, vz) or 1.0
    d = min(D, n)
    px, pz = ox + d * vx / n, oz + d * vz / n
    a = math.atan2(ox - px, oz - pz)
    out = ['name look-%s' % room] + keep + ['pos %d %d %d' % (px, oy, pz), 'ang %.4f' % a, 'god', 'freeze 600']
    open('%s/look-%s.txt' % (FX, room), 'w').write('\n'.join(out) + '\n')
    print(room, 'et%02x00 #%d at %d %d %d; leon %d %d ang %.3f' % (i, sl, ox, oy, oz, px, pz, a))
