#!/usr/bin/env python3
"""leon_hr.py (lane look28, 2026-10-28): Leon's LEON_LIGHT_HEADROOM atlas re-made from the 8-bit PS2 pictures.

leonatl24 (lane purge-cast24) built Leon's 512 atlas ec255e66-76812316 as: PS2 pl00 pictures -> cb_atlas_gc.py tiles,
RGB565 Floyd-Steinberg (ps2src.re4tex) -> pvrtex VQ -> cb_headroom doubles each codebook level (min(2v, max)). That
quantises three times (565 dither, VQ, then doubling a 5/6-bit level, which keeps only even levels: 4/5 bits of
precision in the stored atlas). This tool rebuilds the same tiles at 8 bits (the same Lanczos resample, orientation and
gutter rule as cb_atlas_gc.py's report), scales by 2 (rounded, clamped at 255: LEON_LIGHT_HEADROOM's convention,
same as cb_headroom), and VQ-encodes that once with vq_kmeans (same key, size, format, flags, payload size).

usage: leon_hr.py <ps2src.re4tex (cb_atlas_gc output)> <ps2src.json (its --report)> <dir of the tile pictures>
                  <shipped headroom .re4tex> <out .re4tex> [--png <out 8-bit x1 atlas.png>]
Texels outside the report's tiles keep ps2src.re4tex's (16-bit) values. Private assets in and out.
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vq_kmeans as V  # noqa: E402
T = V.T


def atlas8(src_blob, report, tiles_dir):
    p = T.read_package(src_blob)
    w, h = p['width'], p['height']
    img = T.decode(src_blob)[1][..., :3].astype(np.float64)
    for name, t in sorted(report['tiles'].items()):
        if 'gc' not in t:
            continue
        x, y, tw, th = t['tile']; iw, ih = t['inner']
        yy = h - y - th
        pic = np.asarray(Image.open(Path(tiles_dir) / t['gc']).convert('RGB'))
        if t.get('flipped'):
            pic = pic[::-1]
        inner = np.asarray(Image.fromarray(pic).resize((iw, ih), Image.LANCZOS)).astype(np.float64)
        img[yy:yy + th, x:x + tw] = np.pad(inner, ((2, 2), (2, 2), (0, 0)), mode=t.get('gutter', 'wrap'))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('report'); ap.add_argument('tiles'); ap.add_argument('shipped'); ap.add_argument('out')
    ap.add_argument('--png'); ap.add_argument('--iters', type=int, default=80)
    a = ap.parse_args()
    s8 = atlas8(Path(a.src).read_bytes(), json.loads(Path(a.report).read_text()), a.tiles)
    if a.png:
        Image.fromarray(s8.astype(np.uint8)).save(a.png)
    tgt = np.clip(np.floor(s8 * 2 + 0.5), 0, 255)
    shipped = Path(a.shipped).read_bytes()
    p = T.read_package(shipped)
    book, idx, one = V.encode(tgt, bool(p['flags'] & 4), a.iters, 6, fmt=p['format'])
    out = V.write_package(shipped, book, idx, one)
    Path(a.out).write_bytes(out)
    rep = dict(out=a.out, sha256=T.sha256(out), bytes=len(out),
               psnr_x2_shipped=round(V.psnr(V.decode(shipped)[..., :3], tgt), 2),
               psnr_x2_new=round(V.psnr(V.decode(out)[..., :3], tgt), 2),
               clipped_pct=round(100 * float((s8 * 2 > 255.5).any(-1).mean()), 2))
    print(json.dumps(rep))


if __name__ == '__main__':
    main()
