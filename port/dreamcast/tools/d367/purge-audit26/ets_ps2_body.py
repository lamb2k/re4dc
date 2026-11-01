"""Body proof: nearest PS2 scenario SMD geometry (pos + vertex*scale) to each dropped torch, per room."""
import struct, sys, re
T = __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), '../..')
sys.path[:0] = [T, T + '/../../../tools']
import ps2_objects as po, ps2_bin as pb
idx = pb.afs_index(po.PS2_ISO)
pts = {}
for line in open(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), 'ets-evidence-20261026.txt')):
    m = re.match(r'(r[0-9a-f]{3}) (et[0-9a-f]{4}#\d+) pos \(([^)]*)\)', line)
    if m and m.group(1) in sys.argv[1:]:
        pts.setdefault(m.group(1), []).append((m.group(2), tuple(float(v) for v in m.group(3).split(','))))
for room, lst in sorted(pts.items()):
    pd = pb.afs_read(po.PS2_ISO, room + '.dat', idx)
    smd = [b for i, t, b in pb.dat_entries(pd) if t == 'SMD'][0]
    n = struct.unpack_from('<H', smd, 2)[0]; t0 = struct.unpack_from('<I', smd, 4)[0]
    cache, W = {}, []
    for k in range(n):
        e = 0x10 + 0x40 * k
        b = struct.unpack_from('<H', smd, e + 0x30)[0]
        pos = struct.unpack_from('<3f', smd, e); sc = struct.unpack_from('<3f', smd, e + 0x20)
        if b not in cache:
            off = struct.unpack_from('<I', smd, t0 + 4 * b)[0]
            m = pb.parse_bin(smd[t0 + off:])
            cache[b] = [c['p'] for _, cs in pb.triangles(m) for c in cs]
        for v in cache[b]:
            W.append((pos[0] + v[0] * sc[0], pos[1] + v[1] * sc[1], pos[2] + v[2] * sc[2], k, b))
    for item, P in lst:
        near = [w for w in W if abs(w[0] - P[0]) < 150 and abs(w[1] - P[1]) < 150 and abs(w[2] - P[2]) < 150]
        pl = sorted({(w[3], w[4]) for w in near})
        print('%s %s pos %s verts<150 %d placements %s' % (room, item, tuple(round(x) for x in P), len(near),
              ['#%d@0x%x bin0x%x' % (k, 0x10 + 0x40 * k, b) for k, b in pl[:3]]))
