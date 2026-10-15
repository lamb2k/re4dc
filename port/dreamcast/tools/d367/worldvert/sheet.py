"""sheet.py [VIEWS...]: lane worldvert look sheets, r101 world level 0 vs wholesale levels 1..3 (WORLD_VERT_LEVEL).
Per view: full frames, two 2x crops (where the levels differ most, and the screen centre: the stake / landmark the
camera faces), and |level - level 0| x4. Labels: PS2 world TA vertices per frame (PS2MESH, last window) and the change.
The approach strip (a1..a3: 16 / 10 / 5 m from the stake) goes on one sheet, one row per distance.
Output: C:\\Game Dev\\Emulators\\worldvert-20261015\\sheets."""
import re, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

E = Path(r'C:\Flycast-Evidence\re4-dreamcast\worldvert-20261015')
OUT = Path(r'C:\Game Dev\Emulators\worldvert-20261015\sheets')
LEVELS = [('L0', 'level 0 (source, as shipped)'), ('L1', 'level 1'), ('L2', 'level 2'), ('L3', 'level 3')]
NAMES = dict(vc='benchmark cross view', vb='from the cross, facing away', vs='from the cross, side view',
             vw='worst projected view (em28 spot)', vt='typical view (door from r100)')
W, H, LAB = 640, 480, 58


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


def fonts():
    try:
        return ImageFont.truetype('arial.ttf', 15), ImageFont.truetype('arialbd.ttf', 20)
    except OSError:
        f = ImageFont.load_default()
        return f, f


def view_sheet(v, font, big):
    cells = [(a, name, shot('%s-%s' % (v, a)), counts('%s-%s' % (v, a))) for a, name in LEVELS]
    base, bc = cells[0][2], cells[0][3]
    crop = (160, 40, 480, 280)
    if base is not None:
        m = np.zeros((H, W), bool)
        for a, _, im, _ in cells[1:]:
            if im is not None:
                m |= np.asarray(ImageChops.difference(im, base)).max(axis=2) > 16
        ys, xs = np.nonzero(m)
        if len(xs):
            cx, cy = int(np.median(xs)), int(np.median(ys))
            x0 = min(max(0, cx - 160), W - 320); y0 = min(max(0, cy - 120), H - 240)
            crop = (x0, y0, x0 + 320, y0 + 240)
    centre = (160, 80, 480, 320)
    sheet = Image.new('RGB', (W * len(LEVELS), LAB + 4 * H), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    d.text((6, LAB + 4 * H - 20), 'r101 %s' % NAMES.get(v, v), fill=(255, 255, 255), font=font)
    for i, (a, name, im, pv) in enumerate(cells):
        x = i * W
        lab2 = 'no run' if pv is None else '%.1fk world verts/frame' % (pv / 1000) + (
            '' if not bc or a == 'L0' else ' (%+.1f%%)' % (100.0 * (pv - bc) / bc))
        d.text((x + 6, 2), name, fill=(255, 230, 120), font=big)
        d.text((x + 6, 26), lab2, fill=(230, 230, 230), font=font)
        if im is None:
            continue
        sheet.paste(im, (x, LAB))
        sheet.paste(im.crop(crop).resize((W, H), Image.NEAREST), (x, LAB + H))
        sheet.paste(im.crop(centre).resize((W, H), Image.NEAREST), (x, LAB + 2 * H))
        if base is not None:
            sheet.paste(ImageChops.difference(im, base).point(lambda q: min(255, q * 4)), (x, LAB + 3 * H))
        d.text((x + 6, LAB + H + 4), '2x crop where levels differ most (%d,%d)' % crop[:2], fill=(255, 255, 0), font=font)
        d.text((x + 6, LAB + 2 * H + 4), '2x crop, screen centre (landmark ahead)', fill=(255, 255, 0), font=font)
        d.text((x + 6, LAB + 3 * H + 4), '|level - level 0| x4', fill=(255, 255, 0), font=font)
    out = OUT / ('r101-%s.png' % v)
    sheet.save(out)
    print(out, ' '.join('%s=%s' % (a, None if pv is None else round(pv)) for a, _, _, pv in cells))


def strip_sheet(font, big):
    rows = ['a1', 'a2', 'a3']
    dist = dict(a1='16 m', a2='10 m', a3='5 m')
    sheet = Image.new('RGB', (W * len(LEVELS), (LAB + H) * len(rows)), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    for r, v in enumerate(rows):
        y = r * (LAB + H)
        bc = counts('%s-L0' % v)
        for i, (a, name) in enumerate(LEVELS):
            im, pv = shot('%s-%s' % (v, a)), counts('%s-%s' % (v, a))
            x = i * W
            d.text((x + 6, y + 2), '%s, %s from the stake' % (name, dist[v]), fill=(255, 230, 120), font=big)
            d.text((x + 6, y + 26), 'no run' if pv is None else '%.1fk world verts/frame%s' % (
                pv / 1000, '' if not bc or a == 'L0' else ' (%+.1f%%)' % (100.0 * (pv - bc) / bc)), fill=(230, 230, 230), font=font)
            if im is not None:
                sheet.paste(im, (x, y + LAB))
    out = OUT / 'r101-approach-strip.png'
    sheet.save(out)
    print(out)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    font, big = fonts()
    for v in (sys.argv[1:] or ['vc', 'vb', 'vs', 'vw', 'vt']):
        view_sheet(v, font, big)
    strip_sheet(font, big)


main()
