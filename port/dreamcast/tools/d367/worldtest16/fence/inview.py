#!/usr/bin/env python3
"""inview.py <room dir> EYE_X,EYE_Z,YAW A0,A1 D0,D1 [stage file] [sidecar]: placements with triangles whose centroid lies in
an angular window (deg, + = atan2(-dz, dx) as diffverts.py) and distance window (m) of a camera; per placement: mesh bin,
dyn id, gated (rows 209..222), triangle counts at level 0 per part."""
import sys, os, math, struct, importlib.util, collections
T = '/root/probe/codex-cpu-t15-20261016/tree/port/dreamcast/tools'
sys.path.insert(0, T)
spec = importlib.util.spec_from_file_location('F', T + '/ps2_world_far_lod.py')
F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
D = sys.argv[1]; ex, ez, yaw = [float(v) for v in sys.argv[2].split(',')]
a0, a1 = [float(v) for v in sys.argv[3].split(',')]; d0, d1 = [float(v) * 1000 for v in sys.argv[4].split(',')]
mf = sys.argv[5] if len(sys.argv) > 5 else 'src.re4mesh'; sf = sys.argv[6] if len(sys.argv) > 6 else 'src.r4pw'
fx, fz = math.sin(yaw), math.cos(yaw)
p = F.read(open(os.path.join(D, mf), 'rb').read())
passes, pls = F.read_sidecar(os.path.join(D, sf), len(p['parts']))
_b = open(os.path.join(D, sf), 'rb').read()
TEX = [struct.unpack_from('<I', _b, 32 + 16 * i)[0] for i in range(len(p['parts']))]
bytex = collections.Counter(); bybin = collections.Counter(); bbox = {}
ids = open(os.path.join(D, 'src.ids'), 'rb').read()
hits = collections.defaultdict(lambda: collections.Counter())
ys = collections.defaultdict(lambda: [1e9, -1e9])
for row, (mi, aff) in enumerate(pls):
    m = p['meshes'][mi]; step, origin = m[11:14], m[8:11]
    for pi in range(m[6], m[6] + m[7]):
        c0, cn = p['plods'][pi]
        for ci in range(c0, c0 + cn):
            lv = p['levels'][p['clusters'][ci][6]]
            for li in range(lv[0], lv[0] + lv[1]):
                corners, strips = F.let_corners(p, p['lets'][li])
                for s in strips:
                    for t in F.crb.strip_triangles(s):
                        c = [0.0, 0.0, 0.0]
                        for k in t:
                            v = p['verts'][corners[k]]; mm = [origin[a] + step[a] * v[a] for a in range(3)]
                            for r in range(3):
                                c[r] += (aff[r][0] * mm[0] + aff[r][1] * mm[1] + aff[r][2] * mm[2] + aff[r][3]) / 3
                        dx, dz = c[0] - ex, c[2] - ez
                        fwd = dx * fx + dz * fz
                        if fwd <= 0: continue
                        ang = math.degrees(math.atan2(dx * fz - dz * fx, fwd)); dist = math.hypot(dx, dz)
                        if a0 <= ang <= a1 and d0 <= dist <= d1:
                            hits[row][(pi, passes[pi])] += 1; bytex[TEX[pi]] += 1; bybin[(m[0], TEX[pi])] += 1
                            bb = bbox.setdefault((m[0], TEX[pi]), [1e9, 1e9, 1e9, -1e9, -1e9, -1e9])
                            for r in range(3): bb[r] = min(bb[r], c[r]); bb[3 + r] = max(bb[3 + r], c[r])
                            ys[row][0] = min(ys[row][0], c[1]); ys[row][1] = max(ys[row][1], c[1])
for row in sorted(hits, key=lambda r: -sum(hits[r].values())):
    mi = pls[row][0]; m = p['meshes'][mi]
    print('row %3d mesh %3d bin 0x%04x id %3d %s y %6.0f..%-6.0f tris %4d parts %s' % (row, mi, m[0], ids[row] if row < len(ids) else -1,
          'GATED' if 209 <= row <= 222 else '     ', ys[row][0], ys[row][1], sum(hits[row].values()),
          ' '.join('%d/p%d:%d' % (pi, ps, n) for (pi, ps), n in sorted(hits[row].items()))))

print('by texture key:', ' '.join('%08x:%d' % kv for kv in sorted(bytex.items())))
KEY = os.environ.get('KEY')
if KEY:
    print('bins on', KEY, ' '.join('0x%x:%d' % (b, n) for (b, k), n in sorted(bybin.items()) if k == int(KEY, 16)))
if KEY:
    for (b, k), bb in sorted(bbox.items()):
        if k == int(KEY, 16): print('  0x%x box x %.0f..%.0f y %.0f..%.0f z %.0f..%.0f' % (b, bb[0], bb[3], bb[1], bb[4], bb[2], bb[5]))
