#!/usr/bin/env python3
"""ps2_font_exact.py --ps2-common common_p.fnt --gc-common common_p.fnt --out DIR  (lane gc-audit25, 2026-10-25)

pui24f put the PS2 glyph cells into the GC common_p.fnt by re-encoding each PS2 colour to the nearest entry of the GC
file's own C4 palette (16 PS2 colours -> 11 GC entries; 41/57 grey both -> 9), so the glyph indices were PS2-derived but
approximated and the palette (TLUT) stayed GameCube data. This writes the PS2 sheet exactly instead: the C4 indices are
the PS2 sheet's own 4-bit indices (first 192 cells; the PS2 pad-glyph rows 192-255 are not in the GC container), and the
TLUT is the PS2 CLUT (each PS2 index's colour, RGB5A3: opaque -> 1RRRRRGGGGGBBBBB, else 0AAARRRRGGGGBBBB). Width bytes
are the PS2 ones (cells 0-191). Container, header offsets, sizes and the TPL layout are the GC file's; disc form is
le_mirror (font handler). Private data stays out of Git.
"""
import argparse, hashlib, json, struct, sys
from pathlib import Path
T = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(T), str(Path(__file__).resolve().parent)]
import ps2_tpl              # noqa: E402
import ps2_font as pf       # noqa: E402

CELLS = 192


def rgb5a3(c):
    r, g, b, a = c
    if a >= 255:
        return 0x8000 | ((r >> 3) << 10) | ((g >> 3) << 5) | (b >> 3)
    return ((a >> 5) << 12) | ((r >> 4) << 8) | ((g >> 4) << 4) | (b >> 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ps2-common', required=True)
    ap.add_argument('--gc-common', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    pb = Path(a.ps2_common).read_bytes()
    ptofs, pwofs = struct.unpack_from('<2I', pb, 0)
    pim = ps2_tpl.parse(pb, ptofs)[0]
    pw = pim['width']
    # raw PS2 4-bit indices and CLUT, as ps2_tpl.parse reads them (image 0)
    hdr = ptofs + 16
    doff_p, coff_p = struct.unpack_from('<2I', pb, hdr + 0x20)
    assert pim['bpp'] == 4
    clut = ps2_tpl._clut(pb, ptofs + coff_p, 16)
    praw = bytearray(pw * pim['height'])
    d = ptofs + doff_p
    if pim['layout'] == 'linear':
        for i in range(pw * pim['height'] // 2):
            v = pb[d + i]; praw[2 * i] = v & 15; praw[2 * i + 1] = v >> 4
    else:
        praw = ps2_tpl.unswizzle4(pb[d:d + pw * pim['height'] // 2], pw, pim['height'])
    pim = dict(pim, index=praw)
    assert all(clut[praw[i]] == pim['rgba'][i] for i in range(0, len(praw), 97))
    gb = bytearray(Path(a.gc_common).read_bytes())
    tofs, wofs, img, doff = pf.gc_font(bytes(gb))
    w, h = img.width, img.height
    assert w == pw and h == CELLS // (w // 32) * 32, (w, h, pw)
    # PS2 index -> colour (one colour per index, checked)
    pal = {}
    idx = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            i = pim['index'][y * pw + x]
            c = pim['rgba'][y * pw + x]
            assert pal.setdefault(i, c) == c, ('index with two colours', i)
            idx[y * w + x] = i
    assert max(pal) < 16
    enc = pf.c4_encode(idx, w, h)
    gb[doff:doff + len(enc)] = enc
    # TLUT: the GC image header's palette header -> data offset (BE TPL)
    desc = tofs + struct.unpack_from('>I', gb, tofs + 8)[0]
    ph = tofs + struct.unpack_from('>I', gb, desc + 4)[0]
    n, _pad, pfmt, pdat = struct.unpack_from('>HHII', gb, ph)
    assert pfmt == 2 and n >= 16, (n, pfmt)   # RGB5A3
    for i in range(16):
        struct.pack_into('>H', gb, tofs + pdat + 2 * i, rgb5a3(pal.get(i, (0, 0, 0, 0))))
    gb[wofs:wofs + 2 * CELLS] = pb[pwofs:pwofs + 2 * CELLS]
    be = bytes(gb)
    disc = pf.mirror('common_p.fnt', be)
    out = Path(a.out); (out / 'font').mkdir(parents=True, exist_ok=True)
    (out / 'font' / 'common_p.fnt').write_bytes(disc)
    rep = dict(ps2_common_sha256=hashlib.sha256(pb).hexdigest(), gc_common_sha256=hashlib.sha256(Path(a.gc_common).read_bytes()).hexdigest(),
               palette={str(k): list(v) for k, v in sorted(pal.items())}, tlut=['%04x' % rgb5a3(pal.get(i, (0, 0, 0, 0))) for i in range(16)],
               be_sha256=hashlib.sha256(be).hexdigest(), disc_sha256=hashlib.sha256(disc).hexdigest())
    (out / 'report.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps(rep))


if __name__ == '__main__':
    main()
