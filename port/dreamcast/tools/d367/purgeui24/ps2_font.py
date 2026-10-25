#!/usr/bin/env python3
"""ps2_font.py --gc-font DIR --ps2-common common_p.fnt --out DIR [--disc-ref DIR]
(lane purge-ui24, 2026-10-24; GC asset purge: fonts)

What the PS2 USA build loads for English: BIO4DAT.AFS carries only one Latin font, common_p.fnt (the stage / event /
sub screen fonts are the Japanese *_j set). Its glyph sheet is the GameCube common_p.fnt layout cell for cell (32x32
cells, 32 per row, 2 width bytes per cell) plus two rows of PS2 pad glyphs (cells 192-255: X, square, circle, triangle,
L1/R1/R2), which the Dreamcast does not use. The GC English build reads common_p plus per-stage *_p sheets (stage1_p,
stage2_p, event1-3_p, sscrn_p), which hold the same Latin cells (a few extra ones, e.g. "cm").

So the swap needs no runtime change:
  - common_p.fnt: the PS2 sheet's first 192 cells and their width bytes, in the GC container (same size and layout);
  - each *_p.fnt: the sheets are re-rasterised copies of the common_p layout (slightly different palette and texels),
    so a non-empty cell whose glyph mask overlaps the GC common_p cell at the same index (IoU >= MIN_IOU) becomes that
    cell's PS2 glyph and width bytes; other cells (e.g. "cm" where common_p has a star) stay GC and are counted
    (report.json "kept_gc", "kept_cells").
Pixels are re-encoded into the GC file's own C4 palette (nearest entry), so the TPL header, palette and file size are
unchanged; the disc form is le_mirror.convert_file of the result (font/*.fnt: header swap only). --disc-ref checks that
the unmodified GC files mirror to the release disc's bytes (pipeline identity). Private data stays out of Git.
"""
import argparse, hashlib, json, struct, sys
from pathlib import Path
T = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(T)]
import convert_tpl as tpl   # noqa: E402
import ps2_tpl              # noqa: E402
import le_mirror            # noqa: E402

CELL = 32
P_FONTS = ['stage1_p.fnt', 'stage2_p.fnt', 'event1_p.fnt', 'event2_p.fnt', 'event3_p.fnt', 'sscrn_p.fnt']


def gc_font(b):
    tofs, wofs = struct.unpack_from('>2I', b, 0)
    img = tpl.parse_tpl(b[tofs:])[0]
    assert img.format == tpl.GX_TF_C4, 'expected a C4 glyph sheet'
    # image data offset inside the file
    desc = tofs + struct.unpack_from('>I', b, tofs + 8)[0]
    th = tofs + struct.unpack_from('>I', b, desc)[0]
    data_off = tofs + struct.unpack_from('>I', b, th + 8)[0]
    return tofs, wofs, img, data_off


def c4_indices(img):
    """Linear palette indices of a GC C4 image (8x8 tiles, high nibble first)."""
    w, h = img.width, img.height
    out = bytearray(w * h)
    o = 0
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            for r in range(8):
                for p in range(4):
                    v = img.data[o]; o += 1
                    x = tx + p * 2; y = ty + r
                    out[y * w + x] = v >> 4
                    out[y * w + x + 1] = v & 15
    return out


def c4_encode(idx, w, h):
    out = bytearray(w * h // 2)
    o = 0
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            for r in range(8):
                for p in range(4):
                    x = tx + p * 2; y = ty + r
                    out[o] = (idx[y * w + x] << 4) | idx[y * w + x + 1]; o += 1
    return bytes(out)


def cells(idx, w, h):
    n = (w // CELL) * (h // CELL)
    res = []
    for c in range(n):
        cx, cy = (c % (w // CELL)) * CELL, (c // (w // CELL)) * CELL
        res.append(bytes(idx[(cy + y) * w + cx + x] for y in range(CELL) for x in range(CELL)))
    return res


MIN_IOU = 0.6


def mask(cell, pal):
    return {i for i, v in enumerate(cell) if pal[v][3] >= 96}


def iou(a, b):
    return len(a & b) / len(a | b) if (a and b) else 0.0


def mirror(name, be):
    """The disc form: le_mirror's font handler, in place on a copy."""
    ba = bytearray(be)
    le_mirror.convert_file('font/' + name, ba)
    return bytes(ba)


def nearest(pal, rgba):
    best, bi = None, 0
    for i, q in enumerate(pal):
        d = sum((a - b) ** 2 for a, b in zip(q, rgba)) + 3 * (q[3] - rgba[3]) ** 2
        if best is None or d < best:
            best, bi = d, i
    return bi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gc-font', required=True)
    ap.add_argument('--ps2-common', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--disc-ref')
    a = ap.parse_args()
    G, O = Path(a.gc_font), Path(a.out)
    (O / 'font').mkdir(parents=True, exist_ok=True)
    pb = Path(a.ps2_common).read_bytes()
    ptofs, pwofs = struct.unpack_from('<2I', pb, 0)
    pim = ps2_tpl.parse(pb, ptofs)[0]
    pw = pim['width']
    ptab = pb[pwofs:]
    gcp = (G / 'common_p.fnt').read_bytes()
    _, gwofs, gimg, _ = gc_font(gcp)
    gcells = cells(c4_indices(gimg), gimg.width, gimg.height)
    gpal = [tpl._decode_palette_entry(v, gimg.palette_format) for v, in struct.iter_unpack('>H', gimg.palette_data)]
    gmasks = [mask(c, gpal) for c in gcells]
    rep = {'ps2_common_sha256': hashlib.sha256(pb).hexdigest(), 'files': []}
    for name in ['common_p.fnt'] + P_FONTS:
        src = G / name
        if not src.exists():
            continue
        b = bytearray(src.read_bytes())
        tofs, wofs, img, doff = gc_font(bytes(b))
        pal = [tpl._decode_palette_entry(v, img.palette_format) for v, in struct.iter_unpack('>H', img.palette_data)]
        idx = bytearray(c4_indices(img))
        mine = cells(idx, img.width, img.height)
        per_row = img.width // CELL
        cmap = {}   # PS2 rgba -> GC index (per file palette)
        swapped = kept = 0
        kept_cells = []
        for c, cell in enumerate(mine):
            if not any(cell):
                continue
            j = c if name == 'common_p.fnt' else (c if c < len(gcells) and iou(mask(cell, pal), gmasks[c]) >= MIN_IOU else None)
            if j is None or j >= 192:
                kept += 1; kept_cells.append(c); continue
            jx, jy = (j % (pw // CELL)) * CELL, (j // (pw // CELL)) * CELL
            cx, cy = (c % per_row) * CELL, (c // per_row) * CELL
            for y in range(CELL):
                for x in range(CELL):
                    px = pim['rgba'][(jy + y) * pw + jx + x]
                    if px not in cmap:
                        cmap[px] = nearest(pal, px)
                    idx[(cy + y) * img.width + cx + x] = cmap[px]
            b[wofs + 2 * c: wofs + 2 * c + 2] = ptab[2 * j: 2 * j + 2]
            swapped += 1
        enc = c4_encode(idx, img.width, img.height)
        assert len(enc) == img.width * img.height // 2
        b[doff:doff + len(enc)] = enc
        be = bytes(b)
        try:
            from PIL import Image
            (O / 'previews').mkdir(exist_ok=True)
            for tag, data in (('gc', src.read_bytes()), ('ps2', be)):
                im2 = gc_font(data)[2]
                pv = Image.new('RGBA', (im2.width, min(im2.height, 256)))
                pv.putdata(tpl.decode_image(im2)[:im2.width * pv.height])
                bg = Image.new('RGBA', pv.size, (0, 0, 80, 255)); bg.alpha_composite(pv)
                bg.convert('RGB').save(O / 'previews' / ('%s-%s.png' % (name, tag)))
        except ImportError:
            pass
        disc = mirror(name, be)
        row = dict(file=name, swapped=swapped, kept_gc=kept, kept_cells=kept_cells, colours=len(cmap),
                   be_sha256=hashlib.sha256(be).hexdigest(), disc_sha256=hashlib.sha256(disc).hexdigest())
        (O / 'font' / name).write_bytes(disc)
        if a.disc_ref:
            ref = Path(a.disc_ref) / name
            row['pipeline_identity'] = ref.exists() and mirror(name, src.read_bytes()) == ref.read_bytes()
        rep['files'].append(row)
        print(row['file'], 'swapped', swapped, 'kept_gc', kept, 'identity', row.get('pipeline_identity'))
    (O / 'report.json').write_text(json.dumps(rep, indent=1) + '\n')


if __name__ == '__main__':
    main()
