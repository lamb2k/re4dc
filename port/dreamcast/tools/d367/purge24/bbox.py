#!/usr/bin/env python3
"""bbox.py <gcarc dir> room:hex ...: GC vs PS2 room BIN bounds (pairing check; lane purge-props24)."""
import sys
T = '/root/work/lanes/purge-props24/port/dreamcast/tools'
sys.path[:0] = [T, T + '/../../../tools']
import ps2_objects as po  # noqa
import ps2_bin as pb  # noqa
import room_smd as rs  # noqa
idx = pb.afs_index(po.PS2_ISO)


def bb(pts):
    pts = list(pts)
    return ' '.join('%7.0f..%-7.0f' % (min(p[a] for p in pts), max(p[a] for p in pts)) for a in range(3))


for spec in sys.argv[2:]:
    room, h = spec.split(':'); a = int(h, 16)
    gd = open('%s/%s.arc' % (sys.argv[1], room), 'rb').read()
    ge = rs.tagged_entries(gd, '>')
    t, s, e = ge[a - 4]
    m = po.GcModel(gd[s:e])
    g = [m.p(r[0]) for p in m.parts for tr in p['tris'] for r in tr]
    pe = {i + 4: (t, b) for i, t, b in pb.dat_entries(pb.afs_read(po.PS2_ISO, room + '.dat', idx))}
    pm = pb.parse_bin(pe[a][1])
    q = [c['p'] for _, cs in pb.triangles(pm) for c in cs]
    print('%s 0x%x GC  parts %d tris %4d %s' % (room, a, m.nd, len(g) // 3, bb(g)))
    print('%s 0x%x PS2 mats %d tris %4d %s' % (room, a, len(pm.materials), len(q) // 3, bb(q)))
