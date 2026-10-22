"""pix.py <armA dir> <armB dir> <out dir>: pair shots by order, auto pixel diff of fb0/fb1 (inv23 tier-2 look check)."""
import sys, os
from PIL import Image, ImageChops
a, b, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
sa = sorted(os.listdir(os.path.join(a, 'shots'))); sb = sorted(os.listdir(os.path.join(b, 'shots')))
for x, y in zip(sa, sb):
    best = None
    for fa in ('fb0.png', 'fb1.png'):
        for fb in ('fb0.png', 'fb1.png'):
            pa = os.path.join(a, 'shots', x, 'frames', fa); pb = os.path.join(b, 'shots', y, 'frames', fb)
            if not (os.path.exists(pa) and os.path.exists(pb)): continue
            ia = Image.open(pa).convert('RGB'); ib = Image.open(pb).convert('RGB')
            if ia.size != ib.size: continue
            d = ImageChops.difference(ia, ib).convert('L')
            n = sum(1 for v in d.getdata() if v > 8)
            if best is None or n < best[0]: best = (n, fa, fb, ia, ib)
    if best is None: print(x, y, 'no frames'); continue
    n, fa, fb, ia, ib = best
    tot = ia.size[0] * ia.size[1]
    print('%s %s best %s/%s differing_px=%d (%.3f%%)' % (x, y, fa, fb, n, 100.0 * n / tot))
    ia.save(os.path.join(out, '%s-before.png' % x)); ib.save(os.path.join(out, '%s-after.png' % x))
