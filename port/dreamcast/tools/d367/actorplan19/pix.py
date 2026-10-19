import sys, os
from PIL import Image, ImageChops
# pix.py <evidence root> <scene>...: fb0/fb1 of <scene>-k vs <scene>-p at every shot time both have
root = sys.argv[1]
for sc in sys.argv[2:]:
    a = os.path.join(root, '%s-k' % sc, 'capture', 'shots')
    b = os.path.join(root, '%s-p' % sc, 'capture', 'shots')
    for t in sorted(os.listdir(a)):
        for fb in ('fb0.png', 'fb1.png'):
            pa = os.path.join(a, t, 'frames', fb); pb = os.path.join(b, t, 'frames', fb)
            if not (os.path.exists(pa) and os.path.exists(pb)):
                print(sc, t, fb, 'missing'); continue
            ia = Image.open(pa).convert('RGB'); ib = Image.open(pb).convert('RGB')
            px = list(ImageChops.difference(ia, ib).getdata())
            n = sum(1 for p in px if max(p) > 0)
            print('%s %s %s changed=%d (%.3f%%) max=%d %s' % (sc, t, fb, n, 100.0 * n / len(px), max(max(p) for p in px), 'IDENTICAL' if n == 0 else 'DIFF'))
