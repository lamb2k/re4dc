#!/usr/bin/env python3
"""mshot.py <out.png> room:obj ...  (Windows py): offline flat-shaded GC | PS2 model pairs (obj = hex room BIN or etNNNN.bin).
Same three views (front, side, top) per model, both at the GC model's scale. Modelled render, not a game capture."""
import sys
from pathlib import Path
T = Path('//wsl.localhost/Ubuntu-24.04/root/work/lanes/purge-props24/port/dreamcast/tools')
sys.path[:0] = [str(T), str(T.parents[2] / 'tools')]
import ps2_objects as po  # noqa
import ps2_bin as pb  # noqa
import room_smd as rs  # noqa
from PIL import Image, ImageDraw  # noqa
ARC = Path('//wsl.localhost/Ubuntu-24.04/root/work/lanes/purge-props24-scratch/gcarc')
PS2 = 'C:/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso'
idx = pb.afs_index(PS2)
S = 200


def tris_gc(m):
    return [[m.p(r[0]) for r in t] for p in m.parts for t in p['tris']]


def render(tris, box):
    img = Image.new('RGB', (S * 3, S), (24, 24, 28))
    d = ImageDraw.Draw(img)
    lo, hi = box
    span = max(hi[a] - lo[a] for a in range(3)) or 1
    for v, (ax, ay, az) in enumerate(((0, 1, 2), (2, 1, 0), (0, 2, 1))):
        def pr(p):
            return (v * S + 10 + (p[ax] - lo[ax]) / span * (S - 20), S - 10 - (p[ay] - lo[ay]) / span * (S - 20))
        for t in sorted(tris, key=lambda t: -sum(p[az] for p in t)):
            a, b, c = t
            u = [b[i] - a[i] for i in range(3)]; w = [c[i] - a[i] for i in range(3)]
            n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
            ln = sum(x * x for x in n) ** 0.5 or 1
            sh = int(60 + 170 * abs(n[az]) / ln)
            d.polygon([pr(a), pr(b), pr(c)], fill=(sh, sh, int(sh * 0.9)), outline=(sh // 2, sh // 2, sh // 2))
    return img


rows = []
for spec in sys.argv[2:]:
    room, obj = spec.split(':')
    gd = (ARC / (room + '.arc')).read_bytes()
    ge = rs.tagged_entries(gd, '>')
    pe = {i + 4: (t, b) for i, t, b in pb.dat_entries(pb.afs_read(PS2, room + '.dat', idx))}
    if obj.endswith('.bin'):
        ei = next(i for i, (t, s, e) in enumerate(ge) if t.rstrip(b'\0') == b'ETM')
        gb = gd[ge[ei][1]:ge[ei][2]]
        g = next(gb[s + 0x40:e] for n, s, e in po.etm_entries(gb, '>') if n == obj)
        pbm = next(b for t, b in pe.values() if t == 'ETM')
        p = next(pbm[s + 0x40:e] for n, s, e in po.etm_entries(pbm, '<') if n == obj)
    else:
        a = int(obj, 16); t, s, e = ge[a - 4]; g = gd[s:e]; p = pe[a][1]
    gt = tris_gc(po.GcModel(g))
    pt = [[c['p'] for c in cs] for _, cs in pb.triangles(pb.parse_bin(p))]
    pts = [q for t in gt for q in t]
    box = ([min(q[i] for q in pts) for i in range(3)], [max(q[i] for q in pts) for i in range(3)])
    row = Image.new('RGB', (S * 6 + 10, S + 18), (0, 0, 0))
    row.paste(render(gt, box), (0, 18)); row.paste(render(pt, box), (S * 3 + 10, 18))
    ImageDraw.Draw(row).text((4, 2), '%s %s  GC %d tris  |  PS2 %d tris  (offline render, front / side / top)' % (room, obj, len(gt), len(pt)), fill=(255, 255, 255))
    rows.append(row)
out = Image.new('RGB', (rows[0].width, sum(r.height for r in rows)))
y = 0
for r in rows:
    out.paste(r, (0, y)); y += r.height
out.save(sys.argv[1])
print(sys.argv[1], len(rows))
