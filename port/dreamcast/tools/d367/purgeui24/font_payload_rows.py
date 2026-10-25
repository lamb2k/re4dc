#!/usr/bin/env python3
"""font_payload_rows.py DISC_FNT PS2_SHA256 SOURCE  (lane gc-audit25, 2026-10-25)

Prints provenance-reviewed.tsv rows for the runtime font payloads the GC-ASSET gate hashes from one disc-form font file
(native_ui.cpp): glyph_cell's 512-byte twiddled PAL4 32x32 window at (u, v) = (32 * (cell % 32) + width byte 0,
32 * (cell / 32)) for every cell, clamped at the sheet edges, and glyph_bank's 16 ARGB8888 words of the TLUT
(glyph_color format 2, RGB5A3). The (u, v) rule was checked against the 45 glyph payloads of the gc-catalog24b census
(every one is reproduced at that position from pui24f common_p.fnt)."""
import hashlib, struct, sys

TWX, TWY = [], []
for i in range(32):
    x = y = 0
    for k in range(5):
        if i >> k & 1:
            x |= 2 << (2 * k); y |= 1 << (2 * k)
    TWX.append(x); TWY.append(y)


def x5(v):
    return (v << 3) | (v >> 2)


def color5a3(c):
    if c & 0x8000:
        return 0xff000000 | (x5((c >> 10) & 31) << 16) | (x5((c >> 5) & 31) << 8) | x5(c & 31)
    a = (c >> 12) & 7
    return (((a << 5) | (a << 2) | (a >> 1)) << 24) | ((((c >> 8) & 15) * 17) << 16) | ((((c >> 4) & 15) * 17) << 8) | ((c & 15) * 17)


def sheet(b):
    """Disc form (le_mirror font handler): LE header and TPL tables; texel and TLUT bytes as on the GC."""
    tofs, wofs = struct.unpack_from('<2I', b, 0)
    _m, _n, desc = struct.unpack_from('<3I', b, tofs)
    ih, ph = struct.unpack_from('<2I', b, tofs + desc)
    h, w, fmt, doff = struct.unpack_from('<2H2I', b, tofs + ih)
    assert fmt == 8, fmt   # C4
    n, _u, pf, pd = struct.unpack_from('<HBBII', b, tofs + ph)[0], 0, *struct.unpack_from('<II', b, tofs + ph + 4)
    assert pf == 2, pf
    tlut = [v for v, in struct.iter_unpack('>H', b[tofs + pd:tofs + pd + 32])]   # le_mirror leaves the TLUT big-endian
    return w, h, b[tofs + doff:tofs + doff + w * h // 2], tlut, wofs


def index(data, w, x, y):
    byte = data[(y >> 3) * (w >> 3) * 32 + (y & 7) * 4 + (x >> 3) * 32 + ((x & 7) >> 1)]
    return byte & 15 if x & 1 else byte >> 4


def cell(data, w, h, u, v):
    out = bytearray(512)
    for y in range(32):
        sy = min(max(v + y, 0), h - 1)
        for x in range(32):
            sx = min(max(u + x, 0), w - 1)
            t = TWX[x] | TWY[y]
            out[t >> 1] |= index(data, w, sx, sy) << (4 if t & 1 else 0)
    return bytes(out)


def main():
    path, ps2, src = sys.argv[1:4]
    b = open(path, 'rb').read()
    w, h, data, tlut, wofs = sheet(b)
    pal = struct.pack('<16I', *[color5a3(c) for c in tlut])
    ph = hashlib.sha256(pal).hexdigest()
    print('\t'.join(['font-palette', ph[:40], ph, ps2, src + ' TLUT', 'font_payload_rows.py glyph_bank payload of ' + path.split('/')[-1]]))
    seen = set()
    for c in range((w // 32) * (h // 32)):
        u, v = 32 * (c % 32) + b[wofs + 2 * c], 32 * (c // 32)
        p = cell(data, w, h, u, v)
        s = hashlib.sha256(p).hexdigest()
        if s in seen:
            continue
        seen.add(s)
        print('\t'.join(['font-glyph', s[:40], s, ps2, '%s cell %d' % (src, c), 'font_payload_rows.py glyph_cell window u=%d v=%d' % (u, v)]))


if __name__ == '__main__':
    main()
