#!/usr/bin/env python3
"""charbake: UV coverage / overlap analysis of an approved render mesh (re4dc-approved-render-mesh-1 mesh.json) or of
a cast mesh, rasterised at the atlas size. numpy + PIL.

For every texel it records how many triangles cover it and whether two covering triangles map the texel to 3D points
further apart than --tol mm (a reused / mirrored texture region: a texture-space bake must average there). Writes a
coverage PNG (grey = used once, red = reused region, black = unused) and prints statistics.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))


def raster_tri(uv, size_w, size_h):
    """Texel centres inside a triangle (pixel coords): yields (ys, xs, barycentric [n,3])."""
    p = np.array([[u * size_w, v * size_h] for u, v in uv], np.float64)
    x0, y0 = np.floor(p.min(0)).astype(int)
    x1, y1 = np.ceil(p.max(0)).astype(int)
    x0, y0 = max(x0, 0), max(y0, 0)
    x1, y1 = min(x1, size_w - 1), min(y1, size_h - 1)
    if x1 < x0 or y1 < y0:
        return None
    ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1]
    cx, cy = xs + 0.5, ys + 0.5
    (ax, ay), (bx, by), (qx, qy) = p
    den = (by - qy) * (ax - qx) + (qx - bx) * (ay - qy)
    if abs(den) < 1e-12:
        return None
    l0 = ((by - qy) * (cx - qx) + (qx - bx) * (cy - qy)) / den
    l1 = ((qy - ay) * (cx - qx) + (ax - qx) * (cy - qy)) / den
    l2 = 1 - l0 - l1
    eps = -1e-9
    m = (l0 >= eps) & (l1 >= eps) & (l2 >= eps)
    if not m.any():
        return None
    return ys[m], xs[m], np.stack([l0[m], l1[m], l2[m]], -1)


def analyse(tris, positions, w, h, tol):
    first = np.full((h, w, 3), np.nan)
    count = np.zeros((h, w), np.int32)
    reused = np.zeros((h, w), bool)
    for t in tris:
        r = raster_tri(t['uv'], w, h)
        if r is None:
            continue
        ys, xs, bc = r
        P = np.array([positions[i] for i in t['v']], np.float64)
        pts = bc @ P
        prev = first[ys, xs]
        has = ~np.isnan(prev[:, 0])
        d = np.linalg.norm(prev - pts, axis=1)
        reused[ys[has & (d > tol)], xs[has & (d > tol)]] = True
        newm = ~has
        first[ys[newm], xs[newm]] = pts[newm]
        count[ys, xs] += 1
    return count, reused


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mesh')
    ap.add_argument('--size', default='512x512')
    ap.add_argument('--infos', default='0,1,2,3,4,5,6')
    ap.add_argument('--tol', type=float, default=8.0)
    ap.add_argument('--png')
    a = ap.parse_args()
    w, h = map(int, a.size.split('x'))
    m = json.loads(Path(a.mesh).read_text())
    infos = {int(x) for x in a.infos.split(',')}
    pos = m['positions_mm']
    tris = [dict(v=[c['vertex'] for c in t['corners']], uv=[c['uv'] for c in t['corners']])
            for t in m['triangles'] if t['source_info'] in infos]
    count, reused = analyse(tris, pos, w, h, a.tol)
    used = count > 0
    print(json.dumps(dict(triangles=len(tris), texels_used=int(used.sum()), used_fraction=round(float(used.mean()), 4),
                          texels_reused=int(reused.sum()), reused_fraction_of_used=round(float(reused.sum() / max(1, used.sum())), 4),
                          max_cover=int(count.max())), indent=1))
    if a.png:
        from PIL import Image
        img = np.zeros((h, w, 3), np.uint8)
        img[used] = (110, 110, 110)
        img[reused] = (230, 40, 40)
        Image.fromarray(img).save(a.png)


if __name__ == '__main__':
    main()
