#!/usr/bin/env python3
"""vq_kmeans.py (lane look28, 2026-10-28): a better Dreamcast VQ RGB565 encoder for character atlases.

Same format, same VRAM: re-encodes an existing VQ package (2048-byte codebook of 256 x 2x2 16-bit blocks: RGB565,
ARGB4444 or ARGB1555 as shipped + one index
byte per 2x2 block, twiddled; mipmapped packages keep their chain layout: 1 prefix byte for the 1x1 level, then the
index levels 2x2 .. base, smallest first). Header, name, key, size, flags and payload size stay the shipped
package's; only the codebook and indices change. The shipped packages come from pvrtex (one k-means over plain RGB,
then truncation to 565). This encoder:

  * trains on the 8-bit source (the PS2 atlas.png, box-resized to the shipped size when the package is smaller), all
    mip levels included (box-averaged from the base), so the codebook also serves the smaller levels;
  * k-means++ seeding (fixed seed: deterministic), up to --iters Lloyd rounds, empty / near-empty clusters re-seeded
    at the worst-served blocks;
  * then 565-aware refinement: each codeword is rounded to the 565 level whose 8-bit expansion is nearest (not
    truncated), the blocks are re-assigned against the expanded codebook and the centroids re-fitted, --qiters times;
  * --weights R,G,B: per-channel error weights (default 1,1,1 = plain MSE, i.e. best PSNR);
  * --gain G: encode G x the source, rounded, clamped at 255 (LEON_LIGHT_HEADROOM atlases: G = 2).

Default output of every existing tool is unchanged: nothing calls this unless asked.

usage: vq_kmeans.py <source.png|.re4tex> <shipped VQ .re4tex> <out .re4tex> [--gain 2] [--iters 40] [--qiters 6]
                    [--weights 1,1,1] [--report out.json]
A .re4tex source is decoded (16-bit) and used as the 8-bit target. Python 3, numpy, Pillow. Private assets in and out.
"""
from __future__ import annotations

import argparse, json, struct, sys, zlib
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'charbake'))
import cb_tex as T  # noqa: E402

# per format: channel bit widths (R, G, B[, A]) and the packed shift of each channel
FMT = {T.RGB565: ((5, 6, 5), (11, 5, 0)), T.ARGB4444: ((4, 4, 4, 4), (8, 4, 0, 12)),
       T.ARGB1555: ((5, 5, 5, 1), (10, 5, 0, 15))}


def expand(q, bits):
    """levels [..., n] -> 8-bit expansion per channel (the PVR's bit replication)."""
    q = q.astype(np.int64)
    out = []
    for c, b in enumerate(bits):
        v = q[..., c]
        out.append(v * 255 if b == 1 else (v << (8 - b)) | (v >> (2 * b - 8)) if b < 8 else v)
    return np.stack(out, -1)


def quant(cb, bits):
    """float codebook [K, 4, n] (8-bit units) -> nearest levels by expanded value (not truncated)."""
    out = np.zeros(cb.shape, np.int64)
    for c, b in enumerate(bits):
        lv = np.arange(1 << b)
        ex = expand(np.repeat(lv[:, None], len(bits), 1), bits)[:, c].astype(np.float64)
        out[..., c] = np.abs(cb[..., c][..., None] - ex).argmin(-1)
    return out


def pack(q, fmt):
    bits, shifts = FMT[fmt]
    v = np.zeros(q.shape[:-1], np.int64)
    for c, sh in enumerate(shifts):
        v |= q[..., c] << sh
    return v.astype(np.uint16)


def blocks(img):
    """[h, w, n] -> [h/2 * w/2, 4n] in codebook texel order (0,0) (0,1) (1,0) (1,1) as (x, y)."""
    b = np.stack([img[0::2, 0::2], img[1::2, 0::2], img[0::2, 1::2], img[1::2, 1::2]], 2)
    return b.reshape(-1, 4 * img.shape[2])


def assign(X, C, wv):
    """nearest centroid (weighted squared error) for each row of X; chunked matmul."""
    Xw, Cw = X * wv, C * wv
    cn = (Cw * C).sum(1)
    lab = np.empty(len(X), np.int64); err = np.empty(len(X), np.float64)
    for s in range(0, len(X), 32768):
        x = X[s:s + 32768]
        d = cn[None, :] - 2.0 * (x @ Cw.T)
        j = d.argmin(1)
        lab[s:s + 32768] = j
        err[s:s + 32768] = d[np.arange(len(x)), j] + (Xw[s:s + 32768] * x).sum(1)
    return lab, np.maximum(err, 0)


def refit(X, lab, C, err):
    K = len(C)
    cnt = np.bincount(lab, minlength=K)
    sums = np.zeros_like(C)
    np.add.at(sums, lab, X)
    nz = cnt > 0
    C = C.copy(); C[nz] = sums[nz] / cnt[nz, None]
    # re-seed empty clusters at the worst-served blocks (distinct ones)
    empty = np.flatnonzero(~nz)
    if len(empty):
        worst = np.argsort(-err)[:len(empty) * 4]
        _, first = np.unique(X[worst].round(2), axis=0, return_index=True)
        pick = worst[np.sort(first)][:len(empty)]
        C[empty[:len(pick)]] = X[pick]
    return C


def kmeans(X, K, iters, wv, seed=0x5EED):
    rng = np.random.default_rng(seed)
    uniq, inv = np.unique(X.round(3), axis=0, return_inverse=True)
    cnt = np.bincount(inv.ravel(), minlength=len(uniq)).astype(np.float64)
    if len(uniq) <= K:
        C = np.zeros((K, X.shape[1])); C[:len(uniq)] = uniq; C[len(uniq):] = uniq[0]
        return C
    uw = uniq * np.sqrt(wv)
    c = [rng.choice(len(uniq), p=cnt / cnt.sum())]
    d2 = ((uw - uw[c[0]]) ** 2).sum(1)
    for _ in range(1, K):
        p = d2 * cnt; s = p.sum()
        n = rng.choice(len(uniq), p=p / s) if s > 0 else int(rng.integers(len(uniq)))
        c.append(n); d2 = np.minimum(d2, ((uw - uw[n]) ** 2).sum(1))
    C = uniq[c].astype(np.float64)
    prev = None
    for _ in range(iters):
        lab, err = assign(X, C, wv)
        e = err.mean()
        C = refit(X, lab, C, err)
        if prev is not None and prev - e < 1e-6 * prev:
            break
        prev = e
    return C


def encode(target, mip, iters=40, qiters=6, wv=None, seed=0x5EED, fmt=T.RGB565):
    """target float [h, w, n] 8-bit units (n = 3 RGB or 4 RGBA by format) -> (book uint16 [256, 4],
    [index arrays per level, smallest first], index of the 1x1 level)."""
    bits = FMT[fmt][0]; n = len(bits)
    wv = list(wv if wv is not None else (1, 1, 1)) + [1] * (n - 3)
    wv = np.repeat(np.asarray(wv[:n], np.float64)[None], 4, 0).reshape(4 * n)
    levels = [target]
    if mip:
        cur = target
        while cur.shape[0] > 2 and cur.shape[1] > 2:
            cur = cur.reshape(cur.shape[0] // 2, 2, cur.shape[1] // 2, 2, n).mean((1, 3))
            levels.append(cur)
    Xs = [blocks(l) for l in levels]
    X = np.concatenate(Xs).astype(np.float64)
    C = kmeans(X, 256, iters, wv, seed)
    for _ in range(qiters):
        Q = quant(C.reshape(256, 4, n), bits)
        Ce = expand(Q, bits).reshape(256, 4 * n).astype(np.float64)
        lab, err = assign(X, Ce, wv)
        C = refit(X, lab, Ce, err)
    Q = quant(C.reshape(256, 4, n), bits)
    Ce = expand(Q, bits).reshape(256, 4 * n).astype(np.float64)
    book = pack(Q, fmt)
    idx = []
    for l, x in zip(levels, Xs):
        lab, _ = assign(x.astype(np.float64), Ce, wv)
        idx.append(lab.reshape(l.shape[0] // 2, l.shape[1] // 2).astype(np.uint8))
    mean = target.reshape(-1, n).mean(0)
    one, _ = assign(np.tile(mean, 4)[None], Ce, wv)
    return book, idx[::-1], int(one[0])


def write_package(shipped, book, idx_small_first, one):
    p = T.read_package(shipped)
    w, h = p['width'], p['height']
    data = bytearray(shipped[p['data_offset']:p['data_offset'] + p['data_size']])
    body = bytearray(book.astype('<u2').tobytes())
    tw = b''
    for l in idx_small_first:
        hh, ww = l.shape
        t = np.zeros(hh * ww, np.uint8)
        t[T.twiddle_index(ww, hh).ravel()] = l.ravel()
        tw += t.tobytes()
    pad = len(data) - 2048 - len(tw)
    if pad not in (0, 1) or (pad == 1) != (len(idx_small_first) > 1):
        raise SystemExit('unexpected VQ layout: %d bytes, %d index bytes, %d levels' % (len(data), len(tw), len(idx_small_first)))
    body += bytes([one]) * pad + tw
    out = bytearray(shipped)
    out[p['data_offset']:p['data_offset'] + p['data_size']] = body
    return T._finish(out, p)


def load_target(src, w, h, gain, n=3):
    mode = 'RGB' if n == 3 else 'RGBA'
    if str(src).endswith('.re4tex'):
        img = (decode(Path(src).read_bytes()) if T.read_package(Path(src).read_bytes())['payload'] == T.VQ
               else T.decode(Path(src).read_bytes())[1])[..., :n].astype(np.float64)
        im = Image.fromarray(img.astype(np.uint8), mode)
    else:
        im = Image.open(src).convert(mode); img = None
    if im.size != (w, h):
        im = im.resize((w, h), Image.BOX); img = None
    if img is None:
        img = np.asarray(im).astype(np.float64)
    if gain != 1:   # colour only; alpha kept
        img = img.copy(); img[..., :3] = np.clip(np.floor(img[..., :3] * gain + 0.5), 0, 255)
    return img


def decode(blob):
    """VQ package -> base level RGBA uint8 [h, w, 4] (the base indices are the payload's last (w/2)(h/2) bytes, so
    mipmapped packages decode too; cb_tex.decode reads them right after the codebook)."""
    p = T.read_package(blob)
    w, h = p['width'], p['height']
    data = blob[p['data_offset']:p['data_offset'] + p['data_size']]
    book = np.frombuffer(data, '<u2', 1024).reshape(256, 4)
    n = (w // 2) * (h // 2)
    bi = np.frombuffer(data, np.uint8, n, len(data) - n)[T.twiddle_index(w // 2, h // 2)]
    t = book[bi]
    out = np.zeros((h, w), np.uint16)
    out[0::2, 0::2], out[1::2, 0::2], out[0::2, 1::2], out[1::2, 1::2] = t[..., 0], t[..., 1], t[..., 2], t[..., 3]
    return T.expand16(out, p['format'])


def psnr(a, b):
    m = float(((a.astype(float) - b.astype(float)) ** 2).mean())
    return 99.0 if m == 0 else 10 * np.log10(255 ** 2 / m)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('source'); ap.add_argument('shipped'); ap.add_argument('out')
    ap.add_argument('--gain', type=float, default=1.0); ap.add_argument('--iters', type=int, default=40)
    ap.add_argument('--qiters', type=int, default=6); ap.add_argument('--weights', default='1,1,1')
    ap.add_argument('--report')
    a = ap.parse_args(argv)
    shipped = Path(a.shipped).read_bytes()
    p = T.read_package(shipped)
    if p['payload'] != T.VQ or p['format'] not in FMT:
        raise SystemExit('%s: not a VQ 16-bit package' % a.shipped)
    mip = bool(p['flags'] & 4); n = len(FMT[p['format']][0])
    tgt = load_target(a.source, p['width'], p['height'], a.gain, n)
    book, idx, one = encode(tgt, mip, a.iters, a.qiters, [float(v) for v in a.weights.split(',')], fmt=p['format'])
    out = write_package(shipped, book, idx, one)
    assert len(out) == len(shipped)
    Path(a.out).write_bytes(out)
    before = psnr(decode(shipped)[..., :3], tgt[..., :3]); after = psnr(decode(out)[..., :3], tgt[..., :3])
    if n == 4:
        alpha = dict(alpha_psnr_shipped=round(psnr(decode(shipped)[..., 3], tgt[..., 3]), 2),
                     alpha_psnr_new=round(psnr(decode(out)[..., 3], tgt[..., 3]), 2))
    else:
        alpha = {}
    rep = dict(source=str(a.source), shipped=str(a.shipped), out=str(a.out), name=p['name'], size=[p['width'], p['height']],
               mip=mip, gain=a.gain, bytes=len(out), psnr_shipped=round(before, 2), psnr_new=round(after, 2),
               sha256=T.sha256(out), **alpha)
    print(json.dumps(rep))
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1))
    return rep


if __name__ == '__main__':
    main()
