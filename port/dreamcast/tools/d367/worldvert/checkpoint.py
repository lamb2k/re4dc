"""checkpoint.py: ONE r101 world vertex ladder checkpoint sheet (lane worldvert 2026-10-15).
Top: rows = cameras, columns = L0 (today) / L1 / L2 / L3, same frozen frame per row (global tick 700), each cell
labelled with the PS2 world TA vertices per frame (PS2MESH) and the change vs L0.
Bottom: risk-spot crop strip: per camera, the 2 regions where L3 differs most from L0 (silhouettes, house edges,
ground, far hills show up there), 2x, L0..L3 side by side; plus the screen-centre crop of the cross view (the stake).
Writes WORLDVERT-R101-CHECKPOINT.png + .html (zoomable) in C:\\Game Dev\\Emulators\\worldvert-20261015."""
import re
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

E = Path(r'C:\Flycast-Evidence\re4-dreamcast\worldvert-20261015')
OUT = Path(r'C:\Game Dev\Emulators\worldvert-20261015')
CAMS = [('vc', 'cross (benchmark camera)'), ('vb', 'cross, facing away (buildings)'), ('vs', 'cross, side (tower)'),
        ('vw', 'worst view (em28 spot, wide)'), ('vt', 'typical (door from r100)'),
        ('a1', 'approach: 16 m from stake'), ('a2', 'approach: 10 m'), ('a3', 'approach: 5 m')]
LV = ['L0', 'L1', 'L2', 'L3']
CW, CH, LAB = 480, 360, 40


def counts(run):
    p = E / run / 'capture' / 'run-output.txt'
    if not p.exists():
        return None
    t = p.read_text(errors='replace')
    v = [(int(m.group(1)), int(m.group(2))) for m in
         re.finditer(r'PS2MESH frame=(\d+) strips=\d+ culled=\d+ clipped=\d+ vertices=(\d+)', t)]
    return (v[-1][1] - v[-2][1]) / (v[-1][0] - v[-2][0]) if len(v) >= 2 else None


def shot(run):
    ds = sorted((E / run / 'capture' / 'shots').glob('t*/frames/fb0.png'))
    return Image.open(ds[-1]).convert('RGB') if ds else None


def risk_boxes(a, b, n=2, w=160, h=120):
    d = np.asarray(ImageChops.difference(a, b)).max(axis=2).astype(np.float32)
    d[:60] *= 1.0
    out = []
    for _ in range(n):
        # block sums on a coarse grid
        best, bx = -1, None
        for y in range(0, 480 - h + 1, 20):
            for x in range(0, 640 - w + 1, 20):
                s = d[y:y + h, x:x + w].sum()
                if s > best:
                    best, bx = s, (x, y)
        if best <= 0:
            break
        out.append((bx[0], bx[1], bx[0] + w, bx[1] + h))
        d[bx[1]:bx[1] + h, bx[0]:bx[0] + w] = 0
    return out


def main():
    try:
        font = ImageFont.truetype('arial.ttf', 14); big = ImageFont.truetype('arialbd.ttf', 17)
    except OSError:
        font = big = ImageFont.load_default()
    data = {(c, l): (shot('%s-%s' % (c, l)), counts('%s-%s' % (c, l))) for c, _ in CAMS for l in LV}
    LW = 170
    top = Image.new('RGB', (LW + CW * 4, 30 + len(CAMS) * (CH + LAB)), (20, 20, 20))
    d = ImageDraw.Draw(top)
    for i, l in enumerate(LV):
        d.text((LW + i * CW + 6, 6), ['L0 (today, source)', 'L1', 'L2', 'L3'][i], fill=(255, 230, 120), font=big)
    totals = {l: [] for l in LV}
    for r, (c, name) in enumerate(CAMS):
        y = 30 + r * (CH + LAB)
        d.text((6, y + LAB + 6), name, fill=(255, 255, 255), font=big)
        b = data[(c, 'L0')][1]
        for i, l in enumerate(LV):
            im, pv = data[(c, l)]
            x = LW + i * CW
            if pv is not None:
                totals[l].append(pv)
            lab = 'no run' if pv is None else '%.2fk world verts/frame' % (pv / 1000) + (
                '' if l == 'L0' or not b else '  (%+.0f%%)' % (100.0 * (pv - b) / b))
            d.text((x + 6, y + 14), lab, fill=(230, 230, 230), font=font)
            if im is not None:
                top.paste(im.resize((CW, CH), Image.LANCZOS), (x, y + LAB))
    # risk strip
    rows = []
    for c, name in CAMS:
        a, z = data[(c, 'L0')][0], data[(c, 'L3')][0]
        if a is None or z is None:
            continue
        for bx in risk_boxes(a, z):
            rows.append((c, name, bx))
    rows.append(('vc', 'cross view, screen centre (stake)', (240, 150, 400, 270)))
    SW, SH = 320, 240
    strip = Image.new('RGB', (LW + SW * 4, 30 + len(rows) * (SH + 24)), (28, 28, 28))
    d2 = ImageDraw.Draw(strip)
    d2.text((6, 6), 'Risk-spot crops, 2x: where L3 differs most from L0 per camera (same box across levels)',
            fill=(255, 230, 120), font=big)
    for r, (c, name, bx) in enumerate(rows):
        y = 30 + r * (SH + 24)
        d2.text((6, y + 30), '%s\n%s' % (name, 'box %d,%d' % bx[:2]), fill=(255, 255, 255), font=font)
        for i, l in enumerate(LV):
            im = data[(c, l)][0]
            if im is not None:
                strip.paste(im.crop(bx).resize((SW, SH), Image.NEAREST), (LW + i * SW, y + 20))
                d2.text((LW + i * SW + 4, y + 2), l, fill=(255, 255, 0), font=font)
    sheet = Image.new('RGB', (max(top.width, strip.width), top.height + strip.height), (20, 20, 20))
    sheet.paste(top, (0, 0)); sheet.paste(strip, (0, top.height))
    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / 'WORLDVERT-R101-CHECKPOINT.png'
    sheet.save(png)
    (OUT / 'WORLDVERT-R101-CHECKPOINT.html').write_text(
        '<!doctype html><meta charset="utf-8"><title>Worldvert r101 checkpoint</title>'
        '<style>body{background:#141414;margin:0}img{width:100%;cursor:zoom-in}img.z{width:auto;cursor:zoom-out}</style>'
        '<img src="WORLDVERT-R101-CHECKPOINT.png" onclick="this.classList.toggle(\'z\')">')
    print(png)
    for l in LV:
        print(l, 'mean %.0f' % (sum(totals[l]) / len(totals[l])) if totals[l] else '-', [round(v) for v in totals[l]])


main()
