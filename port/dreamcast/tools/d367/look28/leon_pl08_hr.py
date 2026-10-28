#!/usr/bin/env python3
"""leon_pl08_hr.py (lane look28, 2026-10-28): Leon's pl08 atlas 7506e95f-68cf2211 (no jacket: black shirt, vest, sleeves)
re-made at the LEON_LIGHT_HEADROOM x2 scale from 8-bit PS2 pictures, one VQ encode (vq_kmeans, mip chain kept).

Why: pl08n25 (pl08n.py) pasted the PS2 shirt (15f7e18c <- pl08 arc1 img8) and sleeve (878b23c0 <- pl08 arc 6d img0)
pictures into the atlas at x1, but the atlas is stored at x2 for LEON_LIGHT_HEADROOM (the binary halves Leon's
vertex colours). Measured on the shipped package: shirt tile / PS2 picture = 1.03, sleeves 1.00, while the shared face
tile is 1.93. So the black shirt and sleeves draw at half brightness: the "crushed" black wardrobe.

Tiles (leonatl24 src/pl08src.json layout; x, y from the bottom, w, h; 2-texel wrap gutter):
  shared with the pl00 atlas (face, hair, gloves, belt): leon_hr.py's 8-bit PS2 pl00 atlas (--pl00-png)
  23f6b950 <- pl08-1-6 (id), 2a8a368f <- pl08-1-8 (T), 15f7e18c <- pl08-1-8 (Tr), 878b23c0 <- pl08-6d-0 (id)
Every texel outside these tiles keeps the shipped package's value (decoded, /2). Then x2, rounded, clamped at 255.

usage: leon_pl08_hr.py <shipped pl08 .re4tex> <pl00 atlas8.png> <dir of pl08-*.png> <out .re4tex> [--png <x1 atlas>]
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vq_kmeans as V  # noqa: E402

OR = {'id': lambda a: a, 'T': lambda a: np.transpose(a, (1, 0, 2)), 'Tr': lambda a: np.transpose(a, (1, 0, 2))[::-1, ::-1]}
SHARED = [(0, 256, 256, 128), (384, 256, 64, 128), (448, 256, 64, 128), (256, 256, 128, 64), (0, 384, 256, 128)]
PL08 = [((384, 0, 128, 128), 'pl08-1-6', 'id'), ((256, 0, 128, 256), 'pl08-1-8', 'T'),
        ((0, 0, 256, 256), 'pl08-1-8', 'Tr'), ((384, 128, 128, 128), 'pl08-6d-0', 'id')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('shipped'); ap.add_argument('pl00png'); ap.add_argument('pics'); ap.add_argument('out')
    ap.add_argument('--png'); ap.add_argument('--iters', type=int, default=80)
    a = ap.parse_args()
    shipped = Path(a.shipped).read_bytes()
    p = V.T.read_package(shipped); W = p['width']
    img = V.decode(shipped)[..., :3].astype(np.float64) / 2.0
    pl00 = np.asarray(Image.open(a.pl00png).convert('RGB')).astype(np.float64)
    rep = {}
    for x, y, tw, th in SHARED:
        yy = W - y - th
        img[yy:yy + th, x:x + tw] = pl00[yy:yy + th, x:x + tw]
    for (x, y, tw, th), pic, o in PL08:
        yy = W - y - th
        src = np.ascontiguousarray(OR[o](np.asarray(Image.open(Path(a.pics) / (pic + '.png')).convert('RGB'))))
        inner = np.asarray(Image.fromarray(src).resize((tw - 4, th - 4), Image.LANCZOS)).astype(np.float64)
        before = img[yy + 2:yy + th - 2, x + 2:x + tw - 2].mean()
        img[yy:yy + th, x:x + tw] = np.pad(inner, ((2, 2), (2, 2), (0, 0)), mode='wrap')
        rep[pic + '@%d,%d' % (x, y)] = dict(shipped_x1_mean=round(before, 1), ps2_mean=round(inner.mean(), 1))
    if a.png:
        Image.fromarray(np.clip(np.floor(img + .5), 0, 255).astype(np.uint8)).save(a.png)
    tgt = np.clip(np.floor(img * 2 + 0.5), 0, 255)
    book, idx, one = V.encode(tgt, bool(p['flags'] & 4), a.iters, 6, fmt=p['format'])
    out = V.write_package(shipped, book, idx, one)
    Path(a.out).write_bytes(out)
    print(json.dumps(dict(out=a.out, sha256=V.T.sha256(out), bytes=len(out), tiles=rep,
                          psnr_x2_shipped=round(V.psnr(V.decode(shipped)[..., :3], tgt), 2),
                          psnr_x2_new=round(V.psnr(V.decode(out)[..., :3], tgt), 2))))


if __name__ == '__main__':
    main()
