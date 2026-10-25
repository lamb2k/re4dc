#!/usr/bin/env python3
"""pairs.py <out.png> <ctl base> <cand base> <name>... [--shot tNNNN]: Flycast still pairs (fb0 of the chosen periodic
shot, frozen frame) side by side with labels, plus the pixel diff share. lane purge-props24 (Flycast captures)."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
E = Path(r'C:\Flycast-Evidence\re4-dreamcast\purge-props24')
a = sys.argv[1:]
shot = None
if '--shot' in a:
    i = a.index('--shot'); shot = a[i + 1]; del a[i:i + 2]
out, cb, tb, names = a[0], a[1], a[2], a[3:]
rows = []
for n in names:
    def pick(b):
        d = E / ('lk-%s-%s' % (n, b)) / 'shots'
        ss = sorted(d.iterdir()) if d.exists() else []
        if not ss:
            return None, '-'
        s = next((x for x in ss if x.name == shot), ss[-1])
        f = s / 'frames' / 'fb0.png'
        return (Image.open(f).convert('RGB') if f.exists() else None), s.name
    c, cs = pick(cb); t, ts = pick(tb)
    if c is None or t is None:
        print(n, 'missing'); continue
    diff = float(np.mean(np.any(np.asarray(c) != np.asarray(t), axis=2))) if c.size == t.size else -1
    row = Image.new('RGB', (c.width * 2 + 8, c.height + 20))
    row.paste(c, (0, 20)); row.paste(t, (c.width + 8, 20))
    ImageDraw.Draw(row).text((4, 4), '%s  release %s (%s)  |  candidate %s (%s)  changed px %.2f%%  (Flycast capture)' % (n, cb, cs, tb, ts, diff * 100), fill=(255, 255, 0))
    rows.append(row); print(n, cs, ts, '%.2f%%' % (diff * 100))
sheet = Image.new('RGB', (rows[0].width, sum(r.height for r in rows)))
y = 0
for r in rows:
    sheet.paste(r, (0, y)); y += r.height
sheet.save(out)
