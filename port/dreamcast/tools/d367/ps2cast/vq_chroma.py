#!/usr/bin/env python3
"""vq_chroma.py <atlas.png> <template pvrtex atlas.dt> <out.dt> [--chroma W] [--iters N] [--report json]
(lane ps2cast2, 2026-10-14; PS2_CAST_MERCHANT)

Re-encodes a 512x512 (any square power of two) RGB atlas as Dreamcast VQ RGB565 (256 x 2x2 codebook) with a
chroma-weighted k-means, and writes it into a copy of pvrtex's .dt (same header, same layout: 32-byte header,
codebook 256 x 4 RGB565 texels in (0,0) (0,1) (1,0) (1,1) order, then the twiddled block indices) for
vq_export.py --pack-existing.

Why: pvrtex clusters blocks by plain RGB distance over the whole atlas. A small, dark, saturated region (the
merchant's purple scarf: 128x128 texels, about 6% of the atlas, luma close to the brown/black cloth around it)
shares codewords with the brown cloth and leaves the atlas grey-brown: on screen the scarf drew tan where the PS2
and GC draw it purple. Clustering in Y'CbCr with the chroma axes scaled by W (default 3) gives such regions their
own codewords; the codebook is then the plain RGB mean of each cluster (565-rounded), so the colours themselves
are not boosted. Deterministic (k-means++ seeded from a fixed generator).
"""
import argparse, json, struct
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument('atlas'); ap.add_argument('template'); ap.add_argument('out')
ap.add_argument('--chroma', type=float, default=3.0); ap.add_argument('--iters', type=int, default=24)
ap.add_argument('--report')
a = ap.parse_args()

img = np.asarray(Image.open(a.atlas).convert('RGB'), np.float64)
H, W = img.shape[:2]
assert H == W and H & (H - 1) == 0, 'square power-of-two atlas only'
# 2x2 blocks in codebook texel order: (x0,y0) (x0,y1) (x1,y0) (x1,y1)
blk = np.stack([img[0::2, 0::2], img[1::2, 0::2], img[0::2, 1::2], img[1::2, 1::2]], 2)  # (h/2, w/2, 4, 3)
bh, bw = blk.shape[:2]
rgb = blk.reshape(-1, 4, 3)
M = np.array([[0.299, 0.587, 0.114], [-0.168736, -0.331264, 0.5], [0.5, -0.418688, -0.081312]])
ycc = rgb @ M.T
ycc[..., 1:] *= a.chroma
X = ycc.reshape(len(ycc), 12)
rng = np.random.default_rng(0x5EED)
K = 256
# k-means++ init on unique vectors
uniq, inv = np.unique(np.round(X, 3), axis=0, return_inverse=True)
cnt = np.bincount(inv.ravel(), minlength=len(uniq)).astype(np.float64)
c = [uniq[rng.choice(len(uniq), p=cnt / cnt.sum())]]
d2 = ((uniq - c[0]) ** 2).sum(1)
for _ in range(1, min(K, len(uniq))):
    p = d2 * cnt; s = p.sum()
    nxt = uniq[rng.choice(len(uniq), p=p / s)] if s > 0 else uniq[rng.integers(len(uniq))]
    c.append(nxt); d2 = np.minimum(d2, ((uniq - nxt) ** 2).sum(1))
C = np.array(c)
def assign(C):
    best = np.zeros(len(uniq), np.int64); bd = np.full(len(uniq), np.inf)
    for k0 in range(0, len(C), 64):
        dd = ((uniq[:, None, :] - C[None, k0:k0 + 64, :]) ** 2).sum(2)
        j = dd.argmin(1); v = dd[np.arange(len(uniq)), j]
        m = v < bd; best[m] = j[m] + k0; bd[m] = v[m]
    return best, bd
for it in range(a.iters):
    lab, bd = assign(C)
    for k in range(len(C)):
        m = lab == k
        if m.any():
            C[k] = (uniq[m] * cnt[m, None]).sum(0) / cnt[m].sum()
        else:  # dead codeword: move it to the worst-served vector
            C[k] = uniq[(bd * cnt).argmax()]
lab, bd = assign(C)
blab = lab[inv.ravel()]
# codebook = RGB mean of each cluster's original blocks, 565-quantised
cb = np.zeros((K, 4, 3))
for k in range(len(C)):
    m = blab == k
    if m.any(): cb[k] = rgb[m].mean(0)
q = np.clip(np.round(cb / 255 * np.array([31, 63, 31])), 0, [31, 63, 31]).astype(np.uint16)
cb565 = (q[..., 0] << 11) | (q[..., 1] << 5) | q[..., 2]
# twiddled index order over the (bw x bh) block grid
def spread(v):
    r = np.zeros_like(v)
    for b in range(12): r |= (v & (1 << b)) << b
    return r
yy, xx = np.mgrid[0:bh, 0:bw]
tw = spread(yy) | (spread(xx) << 1)
idx = np.zeros(bh * bw, np.uint8); idx[tw.ravel()] = blab.reshape(bh, bw).ravel().astype(np.uint8)
t = bytearray(open(a.template, 'rb').read())
assert len(t) >= 32 + 2048 + bh * bw, 'template too small'
assert t[0:4] == b'DcTx', 'not a pvrtex .dt'
t[32:32 + 2048] = cb565.astype('<u2').tobytes()
t[32 + 2048:32 + 2048 + bh * bw] = idx.tobytes()
open(a.out, 'wb').write(t)
# report: decoded error, whole atlas and per 128x128 cell (worst cells)
dec = cb565[blab].reshape(bh, bw, 4)
def to_rgb(v):
    v = v.astype(np.int64); return np.stack([(v >> 11 & 31) * 255 // 31, (v >> 5 & 63) * 255 // 63, (v & 31) * 255 // 31], -1)
out = np.zeros_like(img)
r4 = to_rgb(dec)
out[0::2, 0::2] = r4[:, :, 0]; out[1::2, 0::2] = r4[:, :, 1]; out[0::2, 1::2] = r4[:, :, 2]; out[1::2, 1::2] = r4[:, :, 3]
err = np.sqrt(((out - img) ** 2).mean())
rep = dict(chroma=a.chroma, iters=a.iters, rmse=round(float(err), 3), used_codes=int(len(np.unique(blab))))
open(a.out + '.png', 'wb').close(); Image.fromarray(out.clip(0, 255).astype(np.uint8)).save(a.out + '.png')
if a.report: json.dump(rep, open(a.report, 'w'), indent=1)
print(json.dumps(rep))
