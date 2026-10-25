#!/usr/bin/env python3
"""seq.py <out.png> <name> <ctl> <cand> <shot>...: shot sequence, release row over candidate row (Flycast captures)."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
E = Path(r'C:\Flycast-Evidence\re4-dreamcast\purge-props24')
out, n, c, t, *shots = sys.argv[1:]
W, H = 320, 240
img = Image.new('RGB', (W * len(shots), H * 2 + 20))
d = ImageDraw.Draw(img)
for row, b in enumerate((c, t)):
    for i, s in enumerate(shots):
        f = E / ('lk-%s-%s' % (n, b)) / 'shots' / s / 'frames' / 'fb0.png'
        if f.exists():
            img.paste(Image.open(f).convert('RGB').resize((W, H)), (i * W, 20 + row * H))
        d.text((i * W + 4, 22 + row * H), '%s %s' % (b, s), fill=(255, 255, 0))
d.text((4, 4), '%s: top release (%s), bottom candidate (%s); Flycast captures, 2 s apart' % (n, c, t), fill=(255, 255, 255))
img.save(out)
