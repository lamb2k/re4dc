#!/usr/bin/env python3
"""atr.py: offline textured render of r117 BIN 0x1f, GC model + GC picture vs converted model + PS2 atlas (modelled,
not a game capture). Each triangle is split into 4 and coloured by the texel at each sub-triangle's UV centroid."""
import sys
from pathlib import Path
T = Path('//wsl.localhost/Ubuntu-24.04/root/work/lanes/purge-props24/port/dreamcast/tools')
sys.path[:0] = [str(T), str(T.parents[2] / 'tools')]
import ps2_objects as po, ps2_bin as pb, room_smd as rs, ps2_objects_tex as pt  # noqa
import numpy as np
from PIL import Image, ImageDraw
PS2 = 'C:/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso'
pe = {i + 4: (t, b) for i, t, b in pb.dat_entries(pb.afs_read(PS2, 'r117.dat', pb.afs_index(PS2)))}
gd = Path('//wsl.localhost/Ubuntu-24.04/root/work/lanes/purge-props24-scratch/gcarc/r117.arc').read_bytes()
ge = rs.tagged_entries(gd, '>')
gbin = gd[ge[0x1b][1]:ge[0x1b][2]]
atl, lay = po.room_atlas(gbin, pe[0x1f][1], pe[0x20], (256, 256))
pimg = pt.ps2_images(pe[0x20][1], 0)
W, H = lay['size']
can = np.zeros((H, W, 4), np.uint8)
for i, (x, y, w, h) in lay['rects'].items():
    sub, _, _ = pt.orient(pimg[int(i)][2], None, pimg[int(i)][3] & 1)
    can[y:y + h, x:x + w] = sub
gimg = pt.gc_image(gd[ge[0x1c][1]:], 0)
new, st = po.rebuild(gbin, pe[0x1f][1], atlas=atl)


def tris(m):
    out = []
    for p in m.parts:
        for t in p['tris']:
            out.append([(m.p(r[0]), m.uv(r[-1])) for r in t])
    return out


def render(ts, tex, box, view):
    S = 420
    img = Image.new('RGB', (S, S), (20, 20, 24)); d = ImageDraw.Draw(img)
    th, tw = tex.shape[:2]
    lo, hi = box; span = max(hi[a] - lo[a] for a in range(3)) or 1
    ax, ay, az = view

    def pr(p):
        return (10 + (p[ax] - lo[ax]) / span * (S - 20), S - 10 - (p[ay] - lo[ay]) / span * (S - 20))
    subs = []
    for t in ts:
        (a, ua), (b, ub), (c, uc) = t
        mid = lambda p, q: tuple((p[i] + q[i]) / 2 for i in range(len(p)))  # noqa: E731
        ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
        uab, ubc, uca = mid(ua, ub), mid(ub, uc), mid(uc, ua)
        for P, U in (((a, ab, ca), (ua, uab, uca)), ((ab, b, bc), (uab, ub, ubc)), ((ca, bc, c), (uca, ubc, uc)), ((ab, bc, ca), (uab, ubc, uca))):
            subs.append((P, U))
    for P, U in sorted(subs, key=lambda s: -sum(p[az] for p in s[0])):
        u = sum(x[0] for x in U) / 3; v = sum(x[1] for x in U) / 3
        col = tex[min(th - 1, max(0, int(v % 1.0001 * th))), min(tw - 1, max(0, int(u % 1.0001 * tw)))]
        d.polygon([pr(p) for p in P], fill=tuple(int(x) for x in col[:3]))
    return img


g = tris(po.GcModel(gbin)); n = tris(po.GcModel(new))
pts = [p for t in g for p, _ in t]
box = ([min(q[i] for q in pts) for i in range(3)], [max(q[i] for q in pts) for i in range(3)])
out = Image.new('RGB', (420 * 2 + 10, 420 * 2 + 10))
for k, view in enumerate(((0, 1, 2), (0, 2, 1))):
    out.paste(render(g, gimg, box, view), (0, k * 430)); out.paste(render(n, can, box, view), (430, k * 430))
ImageDraw.Draw(out).text((4, 4), 'r117 BIN 0x1f  GC + GC picture | converted + PS2 atlas (offline render: front, top)', fill=(255, 255, 0))
out.save(r'C:\Flycast-Evidence\re4-dreamcast\purge-props24\sheets\r117-atlas-render.png'); print('ok')
