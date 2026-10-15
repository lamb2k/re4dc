#!/usr/bin/env python3
"""look.py <dump dir> <out png> [title]: offline textured renders (orthographic, two views) GC vs ours for every
lookdump JSON in <dump dir>; one row per asset: GC view A | ours view A | GC view B | ours view B | pictures."""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

S = 200


def rot(yaw, pitch):
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    return rx @ ry


def render(tris, pics, R, box):
    img = np.full((S, S, 3), 40, np.uint8)
    zb = np.full((S, S), -1e30)
    lo, hi = box
    scale = (S - 16) / max(hi[0] - lo[0], hi[1] - lo[1], 1e-6)
    L = np.array([0.4, 0.7, 0.6]); L /= np.linalg.norm(L)
    for t in tris:
        P = np.array(t['p']) @ R.T
        n = np.cross(P[1] - P[0], P[2] - P[0]); nn = np.linalg.norm(n)
        if nn < 1e-9:
            continue
        shade = 0.45 + 0.55 * abs(n @ L) / nn
        xs = (P[:, 0] - lo[0]) * scale + 8
        ys = S - ((P[:, 1] - lo[1]) * scale + 8)
        x0, x1 = int(max(0, math.floor(xs.min()))), int(min(S - 1, math.ceil(xs.max())))
        y0, y1 = int(max(0, math.floor(ys.min()))), int(min(S - 1, math.ceil(ys.max())))
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(d) < 1e-9:
            continue
        a = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / d
        b = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / d
        c = 1 - a - b
        m = (a >= 0) & (b >= 0) & (c >= 0)
        if not m.any():
            continue
        z = a * P[0, 2] + b * P[1, 2] + c * P[2, 2]
        uv = np.array(t['uv'])
        u = a * uv[0, 0] + b * uv[1, 0] + c * uv[2, 0]
        v = a * uv[0, 1] + b * uv[1, 1] + c * uv[2, 1]
        pic = pics.get(t['tex'])
        if pic is None:
            col = np.stack([np.full(u.shape, 255), np.zeros(u.shape), np.full(u.shape, 255)], -1)
        else:
            h, w = pic.shape[:2]
            tx = (np.floor(u * w).astype(int)) % w
            ty = (np.floor(v * h).astype(int)) % h
            col = pic[ty, tx, :3].astype(float)
            mk = pics.get(t.get('mask')) if t.get('mask') is not None else None
            if mk is not None:
                mh, mw = mk.shape[:2]
                al = mk[(np.floor(v * mh).astype(int)) % mh, (np.floor(u * mw).astype(int)) % mw, 0].astype(float) / 255
                m = m & (al >= 0.25)
                col = col * al[..., None] + 40 * (1 - al[..., None])
        zz = zb[y0:y1 + 1, x0:x1 + 1]
        upd = m & (z > zz)
        zz[upd] = z[upd]
        block = img[y0:y1 + 1, x0:x1 + 1]
        block[upd] = np.clip(col[upd] * shade, 0, 255).astype(np.uint8)
    return img


def box(tris_list, R):
    pts = np.concatenate([np.array([p for t in tris for p in t['p']]) @ R.T for tris in tris_list])
    return pts.min(0), pts.max(0)


def main():
    d, out = Path(sys.argv[1]), Path(sys.argv[2])
    rows = []
    views = [rot(math.radians(35), math.radians(-25)), rot(math.radians(215), math.radians(-25))]
    for f in sorted(d.glob('*.json')):
        j = json.loads(f.read_text())
        load = lambda p: np.asarray(Image.open(p if Path(p).is_absolute() else d / p).convert('RGBA'))
        gcp = {int(k[2:]): load(v) for k, v in j['pics'].items() if k.startswith('gc')}
        ours = dict(gcp)
        for k, v in j['pics'].items():
            if k.startswith('ps2_'):
                ours[int(k[4:])] = load(v.replace('/mnt/c/', 'C:/') if v.startswith('/mnt/c/') else v.replace('/root/', '//wsl.localhost/Ubuntu-24.04/root/'))
        tiles = []
        for R in views:
            bx = box([j['gc'], j['ours'], j['ps2']], R)
            ps2p = {k: v for k, v in ours.items() if v is not gcp.get(k)}
            tiles += [render(j['gc'], gcp, R, bx), render(j['ours'], ours, R, bx), render(j['ps2'], ps2p, R, bx)]
        strip = Image.new('RGB', (6 * S + 2 * S, S + 18), (20, 20, 20))
        for k, t in enumerate(tiles):
            strip.paste(Image.fromarray(t), (k * S, 18))
        x = 6 * S
        for key in sorted(ours):
            for src, lab in ((gcp.get(key), 'GC'), (ours[key] if key in ours and ours[key] is not gcp.get(key) else None, 'PS2')):
                if src is None:
                    continue
                th = Image.fromarray(src).convert('RGB'); th.thumbnail((S // 2 - 4, S // 2 - 4))
                if x + th.width <= 8 * S:
                    strip.paste(th, (x, 18)); x += th.width + 4
        dr = ImageDraw.Draw(strip)
        dr.text((4, 2), '%s %s  GC %d tris | ours %d | PS2 %d   (cols: GC, ours, PS2 BIN direct; view A then B; pictures GC/PS2)' % (
            j['room'], j['name'], len(j['gc']), len(j['ours']), len(j['ps2'])), fill=(230, 230, 230))
        rows.append(strip)
    sheet = Image.new('RGB', (8 * S, sum(r.height for r in rows) + 30), (10, 10, 10))
    ImageDraw.Draw(sheet).text((4, 8), sys.argv[3] if len(sys.argv) > 3 else 'lane items look sheet (offline render)', fill=(255, 255, 255))
    y = 30
    for r in rows:
        sheet.paste(r, (0, y)); y += r.height
    sheet.save(out)
    print('sheet', out, len(rows))


if __name__ == '__main__':
    main()
