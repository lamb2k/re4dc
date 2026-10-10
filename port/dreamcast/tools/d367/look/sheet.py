#!/usr/bin/env python3
"""Look gallery sheet + metrics (look study 2026-10-10). Windows Python (numpy + PIL).

usage: sheet.py <gallery dir> [column ...] [--hwms hwms.json] [--out name]
<gallery>/gc/<shot>.png       GameCube reference (Dolphin raw XFB 512x448, or 640x480)
<gallery>/dc/<column>/<shot>.png  Dreamcast stills (Flycast framebuffer 640x480), one dir per build / knob set
Columns default to every dc/ dir (sorted; "cur" first when present). Close-up shots ("from" + "crop" in shots.json)
are crops of another shot. Writes <gallery>/<out>.png (rows = shots, columns = GC + each column) and
<gallery>/<out>.csv with, per shot and column: mean luma, contrast (luma p95 - p5 and sd), saturation (mean HSV S),
sharpness (mean |Laplacian| of luma), SSIM to the GC image (8x8 windows, luma, same crop), and the column's hw ms
from hwms.json ({column: {"sq": ms, "fight": ms, "note": text}}; measured on the SH-4 hardware model).
Images are compared inside the picture band (rows 60..419 of 640x480; the GC letterbox is the same band).
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
BAND = (0, 60, 640, 420)
TILE_W = 320


def load640(p):
    im = Image.open(p).convert('RGB')
    if im.size != (640, 480):
        im = im.resize((640, 480), Image.BILINEAR)   # GC 512x448 XFB -> the VI's 640x480 (bilinear, as gcan.py)
    return im


def luma(a):
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def metrics(im):
    a = np.asarray(im, np.float64)
    y = luma(a)
    mx, mn = a.max(-1), a.min(-1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    lap = np.abs(4 * y[1:-1, 1:-1] - y[:-2, 1:-1] - y[2:, 1:-1] - y[1:-1, :-2] - y[1:-1, 2:])
    p5, p95 = np.percentile(y, [5, 95])
    return dict(mean=y.mean(), spread=p95 - p5, sd=y.std(), sat=sat.mean(), sharp=lap.mean())


def ssim(a, b):
    """Mean SSIM of the luma over 8x8 blocks (no Gaussian), C1/C2 for 8-bit."""
    x, y = luma(np.asarray(a, np.float64)), luma(np.asarray(b, np.float64))
    h, w = (x.shape[0] // 8) * 8, (x.shape[1] // 8) * 8
    x = x[:h, :w].reshape(h // 8, 8, w // 8, 8).transpose(0, 2, 1, 3).reshape(-1, 64)
    y = y[:h, :w].reshape(h // 8, 8, w // 8, 8).transpose(0, 2, 1, 3).reshape(-1, 64)
    mx, my = x.mean(1), y.mean(1)
    vx, vy = x.var(1), y.var(1)
    cxy = ((x - mx[:, None]) * (y - my[:, None])).mean(1)
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    s = ((2 * mx * my + c1) * (2 * cxy + c2)) / ((mx * mx + my * my + c1) * (vx + vy + c2))
    return float(s.mean())


def main():
    args = sys.argv[1:]
    hwms_path, out = None, 'sheet'
    if '--hwms' in args:
        i = args.index('--hwms'); hwms_path = args[i + 1]; del args[i:i + 2]
    if '--out' in args:
        i = args.index('--out'); out = args[i + 1]; del args[i:i + 2]
    g = Path(args[0])
    spec = json.loads((HERE / 'shots.json').read_text())
    cols = args[1:] or sorted((p.name for p in (g / 'dc').iterdir() if p.is_dir()), key=lambda n: (n != 'cur', n))
    hw = json.loads(Path(hwms_path).read_text()) if hwms_path and Path(hwms_path).exists() else {}
    shots = spec['shots']
    th = int(TILE_W * (BAND[3] - BAND[1]) / (BAND[2] - BAND[0]))
    rowh, headh, labw = th + 30, 46, 150
    S = Image.new('RGB', (labw + TILE_W * (len(cols) + 1), headh + rowh * len(shots)), (16, 16, 16))
    d = ImageDraw.Draw(S)
    for c, name in enumerate(['GameCube (Dolphin 1x)'] + cols):
        x = labw + c * TILE_W
        d.text((x + 4, 4), name, fill=(255, 255, 0))
        if c and name in hw:
            h = hw[name]
            d.text((x + 4, 18), 'hw ms sq %s  fight %s' % (h.get('sq', '-'), h.get('fight', '-')), fill=(160, 220, 255))
            if h.get('note'):
                d.text((x + 4, 31), str(h['note'])[:48], fill=(160, 160, 160))
    rows = []
    for r, s in enumerate(shots):
        y0 = headh + r * rowh
        d.text((4, y0 + 4), s['name'], fill=(255, 255, 255))
        d.text((4, y0 + 18), s['title'][:24], fill=(170, 170, 170))
        if s.get('approx'):
            d.text((4, y0 + 32), 'approx. match', fill=(255, 140, 90))
        src = s.get('from', s['name'])
        box = tuple(s['crop']) if 'crop' in s else BAND
        gbox = tuple(s.get('gc_crop', box))
        gfile = s.get('gc') or next((x.get('gc') for x in shots if x['name'] == src), None)
        gp = g / 'gc' / gfile if gfile else None
        gim = load640(gp).crop(gbox) if gp and gp.exists() else None
        imgs = [gim] + [load640(g / 'dc' / c / (src + '.png')).crop(box) if (g / 'dc' / c / (src + '.png')).exists()
                        else None for c in cols]
        for c, im in enumerate(imgs):
            x = labw + c * TILE_W
            if im is None:
                d.text((x + 8, y0 + th // 2), 'missing', fill=(255, 80, 80))
                continue
            t = im.resize((TILE_W, th), Image.BILINEAR if 'crop' not in s else Image.NEAREST)
            S.paste(t, (x, y0))
            m = metrics(im)
            ss = ssim(im, gim.resize(im.size)) if (c and gim is not None) else None
            name = 'gc' if c == 0 else cols[c - 1]
            txt = 'L %.0f  C %.0f  S %.2f  E %.1f' % (m['mean'], m['spread'], m['sat'], m['sharp']) + \
                  ('  SSIM %.2f' % ss if ss is not None else '')
            d.text((x + 3, y0 + th + 3), txt, fill=(220, 220, 220))
            rows.append(dict(shot=s['name'], column=name, mean_luma=round(m['mean'], 1), contrast_p95_p5=round(m['spread'], 1),
                             luma_sd=round(m['sd'], 1), saturation=round(m['sat'], 3), sharpness=round(m['sharp'], 2),
                             ssim_vs_gc='' if ss is None else round(ss, 3),
                             hw_ms_sq=hw.get(name, {}).get('sq', ''), hw_ms_fight=hw.get(name, {}).get('fight', '')))
    S.save(g / (out + '.png'))
    with open(g / (out + '.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print('sheet', g / (out + '.png'), len(shots), 'shots x', len(cols) + 1, 'columns;', g / (out + '.csv'))


if __name__ == '__main__':
    main()
