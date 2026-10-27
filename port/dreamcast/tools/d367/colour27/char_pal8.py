#!/usr/bin/env python3
"""char_pal8.py (colour27, 2026-10-27): exact PAL8 character atlases with ARGB8888 palettes, for TEX_PAL32=1.

The PS2 character pictures are 4-bit / 8-bit CLUT images: a converted Ganado atlas (ps2_cast.py atlas.png) holds only
16 to 112 distinct colours (em12 / em15 / em17: 49). The shipped atlas is RGB565 VQ (2048-byte codebook + one index
per 2x2 block), which adds codebook noise (PSNR 30 to 38 dB against the atlas, dark mean -1 to -2.4 levels) to a
picture that a 256-entry palette holds exactly. This tool writes the atlas as a square twiddled PAL8 package
(texture_package.hpp kPal8Argb4444 + kPalette8888: 256 ARGB8888 palette words), byte-exact to the PS2 colours:

  * <= 256 distinct RGBA colours and a square power-of-two side (the runtime PAL8 path is square only), else refused;
  * --mip (TEX_PAL8_MIPMAP chains): the PVR order (3 prefix bytes, 1x1 up to the base); each smaller level is the 2x2
    box average of the level above mapped to the nearest palette colour (the base level stays exact);
  * the package keeps the shipped package's material name and is written under the shipped key (<key>.re4tex), so
    the character binds it unchanged. VRAM: side^2 (x4/3 with mips) + 1024 bytes, against the VQ package's
    2048 + side^2/4 (x4/3).
usage: char_pal8.py <atlas.png> <shipped .re4tex> <out .re4tex> [--mip]
"""
import argparse, struct, sys, zlib
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent.parent)]
import convert_tpl as C  # noqa: E402

PAL8, PAL32, MIP = C.FORMAT_PAL8_ARGB4444, 1 << 3, C.FLAG_MIPMAP


def twiddled(level):
    side = level.shape[0]
    return bytes(C.twiddle_16bpp([int(v) for v in level.reshape(-1)], side, side))


def build(atlas, shipped, mip):
    img = np.asarray(Image.open(atlas).convert('RGBA'))
    side = img.shape[0]
    if img.shape[1] != side or side & (side - 1) or not 8 <= side <= 1024:
        raise SystemExit('char_pal8: %s is %dx%d; the PAL8 path takes square power-of-two pictures only'
                         % (atlas, img.shape[1], img.shape[0]))
    flat = img.reshape(-1, 4)
    pal, inv = np.unique(flat, axis=0, return_inverse=True)
    if len(pal) > 256:
        raise SystemExit('char_pal8: %s has %d colours (> 256): not exact in PAL8' % (atlas, len(pal)))
    base = inv.reshape(side, side).astype(np.uint8)
    levels = [base]
    if mip:
        cur = img.astype(np.float64)
        palf = pal.astype(np.float64)
        while cur.shape[0] > 1:
            cur = cur.reshape(cur.shape[0] // 2, 2, cur.shape[1] // 2, 2, 4).mean((1, 3))
            d = ((cur.reshape(-1, 1, 4) - palf[None]) ** 2).sum(-1)
            levels.append(d.argmin(1).reshape(cur.shape[:2]).astype(np.uint8))
        levels = levels[::-1]                     # 1x1 first (PVR order)
        idx = bytes(3) + b''.join(twiddled(l) for l in levels)
    else:
        idx = twiddled(base)
    words = [(int(a) << 24) | (int(r) << 16) | (int(g) << 8) | int(b) for r, g, b, a in pal]
    payload = idx + struct.pack('<256I', *(words + [0] * (256 - len(words))))
    h = C.HEADER.unpack_from(shipped)
    t = C.TEXTURE.unpack_from(shipped, h[5])
    alpha = int(flat[:, 3].min()) < 255
    flags = PAL32 | (MIP if mip else 0) | ((C.FLAG_ALPHA | (C.FLAG_BINARY_ALPHA if set(np.unique(flat[:, 3])) <= {0, 255} else 0)) if alpha else 0)
    start = C.HEADER.size + C.TEXTURE.size
    desc = C.TEXTURE.pack(t[0], side, side, PAL8, start, len(payload), flags, C.PAYLOAD_TWIDDLED, 0)
    body = desc + payload
    head = C.HEADER.pack(C.MAGIC, C.VERSION, C.HEADER.size, C.TEXTURE.size, 1, C.HEADER.size, start, len(payload),
                         zlib.crc32(body) & 0xffffffff, h[9], h[10])
    return head + body, len(pal)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('atlas'); ap.add_argument('shipped'); ap.add_argument('out'); ap.add_argument('--mip', action='store_true')
    a = ap.parse_args()
    out, n = build(a.atlas, Path(a.shipped).read_bytes(), a.mip)
    Path(a.out).write_bytes(out)
    print('char_pal8: %s %d colours -> %d bytes (shipped %d)' % (Path(a.out).name, n, len(out), len(Path(a.shipped).read_bytes())))


if __name__ == '__main__':
    main()
