#!/usr/bin/env python3
"""poc-sheet.py OUT.png TITLE RUN_DIR[:LABEL] ...   (Windows Python, PIL + numpy; tools/d367/poc101)

POC101 still sheet: for each look-sweep run (fp_run.py capture with --period shots, fixture scene 11 = the look sweep,
game frozen, the same picture drawn ALL OFF then ALL ON), one row: ALL OFF | ALL ON | difference x4.
Which setting a shot shows is read from the banner (bench.cpp POC banner "NOT THE GAME - POC <setting>", native_ui.cpp):
its red box width is 12 px per character + 16, centred, at y 32..60. ALL OFF (26 characters) and ALL ON (25) differ
by 12 px; the middle matching shot of each is used. A shot whose banner is neither is skipped."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

W_OFF = len('NOT THE GAME - POC ALL OFF') * 12 + 16
W_ON = len('NOT THE GAME - POC ALL ON') * 12 + 16


def banner_w(a):
    row = a[46, :, :].astype(int)
    red = (row[:, 0] > 110) & (row[:, 1] < 60) & (row[:, 2] < 60)
    xs = np.nonzero(red)[0]
    return int(xs[-1] - xs[0] + 1) if len(xs) else 0


def pick(run):
    got = {}
    for d in sorted(Path(run, 'shots').iterdir()):
        seen = []
        for fb in ('fb0.png', 'fb1.png'):
            p = d / 'frames' / fb
            if not p.exists():
                continue
            a = np.asarray(Image.open(p).convert('RGB'))
            w = banner_w(a)
            cls = [n for n, ww in (('off', W_OFF), ('on', W_ON)) if abs(w - ww) <= 3]
            seen.append((cls[0] if cls else None, p, a))
        # both framebuffers show the same setting: the game is drawing it now (not a stale back buffer)
        if len(seen) == 2 and seen[0][0] and seen[0][0] == seen[1][0]:
            got.setdefault(seen[0][0], []).append(seen[0][1:])
    # the middle match of each setting: inside its slot (the first may be mid-switch, the last a stale back buffer)
    return {k: v[len(v) // 2] for k, v in got.items()}


def main(argv):
    out, title, runs = argv[0], argv[1], argv[2:]
    rows = []
    for r in runs:
        run, _, label = r.partition(':')
        g = pick(run)
        if 'off' not in g or 'on' not in g:
            print('%s: no %s shot' % (run, 'ALL OFF' if 'off' not in g else 'ALL ON'))
            continue
        a, b = g['off'][1].astype(int), g['on'][1].astype(int)
        diff = np.clip(np.abs(a - b) * 4, 0, 255).astype(np.uint8)
        diff[:64, :, :] = 0   # the banner differs by construction
        changed = float((np.abs(a - b)[64:420].sum(axis=2) > 24).mean() * 100)
        rows.append((label or Path(run).name, g['off'][0], g['on'][0], Image.fromarray(diff), changed))
        print('%s: off %s on %s, %.2f %% of pixels changed' % (run, g['off'][0], g['on'][0], changed))
    if not rows:
        return 1
    sw, sh, pad, top = 640, 480, 8, 40
    sheet = Image.new('RGB', (3 * sw + 4 * pad, top + len(rows) * (sh + 28 + pad)), (16, 16, 16))
    dr = ImageDraw.Draw(sheet)
    dr.text((pad, 12), title, fill=(255, 255, 255))
    for i, (label, off, on, diff, changed) in enumerate(rows):
        y = top + i * (sh + 28 + pad)
        for j, (img, cap) in enumerate(((Image.open(off), 'ALL OFF'), (Image.open(on), 'ALL ON'),
                                         (diff, 'DIFFERENCE x4 (%.2f %% of pixels changed)' % changed))):
            x = pad + j * (sw + pad)
            dr.text((x, y + 4), '%s - %s' % (label, cap), fill=(255, 255, 160))
            sheet.paste(img.convert('RGB').resize((sw, sh)), (x, y + 24))
    sheet.save(out)
    print('SHEET', out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
