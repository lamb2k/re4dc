#!/usr/bin/env python3
"""fx_ps2_sheet.py <ps2lib root> <out.png> <folder>:<gc_id> ... [--frames N]: look sheet for PS2-sourced effect pictures.

One row per GameCube effect texture id (ps2lib/INDEX.tsv effects-tex row): the GameCube picture | the decoded PS2
picture | the Dreamcast package the runtime samples (PAL4 ARGB4444, decoded from effects-tex/<folder>/<key>.re4tex),
over a checkerboard, first N frames (default 1), labelled with the INDEX row. Folder = INDEX room column (common,
r101, em13, ...). Lane vram12 (2026-10-15); private inputs, the PNG is evidence, not Git.
"""
import struct, sys
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'test12fx'))
import fx_ps2_pack as F  # noqa: E402
C = F.C
mirror = F.mirror


def gc_pictures(files):
    """{ctx/tplN: [(key, w, h, rgba)]} for the GameCube EFF TPLs in files (fx_ps2_pack.gc_eff_tables' traversal; the
    images are caught through its image_identity call)."""
    seen = {}
    orig = F.image_identity

    def ident(im):
        r = orig(im)
        seen[r[0]] = im
        return r
    F.image_identity = ident
    try:
        _ids, tpls = F.gc_eff_tables_files(files)
    finally:
        F.image_identity = orig
    return {ctx: [(k, w, h, C.decode_image(seen[k])) for k, w, h in pics] for ctx, pics in tpls.items()}


def dc_package(path):
    """(w, h, rgba) of a PAL4 ARGB4444 twiddled package (fx_ps2_pack.package)."""
    b = path.read_bytes()
    h = C.HEADER.unpack_from(b, 0)
    t = C.TEXTURE.unpack_from(b, h[5])
    w, ht, fmt, off, size = t[1], t[2], t[3], t[4], t[5]
    if fmt != C.FORMAT_PAL4_ARGB4444:
        raise ValueError('not PAL4')
    pay = b[off:off + size]
    words = struct.unpack_from('<16H', pay, w * ht // 2)
    pal = [(((v >> 8) & 15) * 17, ((v >> 4) & 15) * 17, (v & 15) * 17, (v >> 12) * 17) for v in words]
    tw = []
    for byte in pay[:w * ht // 2]:
        tw += (byte & 15, byte >> 4)
    order = C.twiddle_16bpp(list(range(w * ht)), w, ht)
    lin = [0] * (w * ht)
    for i, idx in enumerate(order):
        lin[idx] = tw[i]
    return w, ht, [pal[v] for v in lin]


def checker(w, h, c=8):
    im = Image.new('RGBA', (w, h), (200, 200, 200, 255)); d = ImageDraw.Draw(im)
    for y in range(0, h, c):
        for x in range(0, w, c):
            if (x // c + y // c) % 2:
                d.rectangle([x, y, x + c - 1, y + c - 1], fill=(150, 150, 150, 255))
    return im


def tile(w, h, rgba, box=128):
    im = Image.new('RGBA', (w, h)); im.putdata([tuple(p) for p in rgba])
    s = max(1, box // max(w, h))
    im = im.resize((w * s, h * s), Image.NEAREST)
    bg = checker(box, box); bg.alpha_composite(im.crop((0, 0, min(box, im.size[0]), min(box, im.size[1]))))
    return bg


def main(a):
    lib, out = Path(a[0]), a[1]
    nf = int(a[a.index('--frames') + 1]) if '--frames' in a else 1
    sel = [x for x in a[2:] if ':' in x and not x.startswith('--')]
    index = {}
    for ln in (lib / 'INDEX.tsv').read_text().splitlines()[1:]:
        f = ln.split('\t')
        if f[0] == 'effects-tex':
            index[(f[1], f[2])] = f
    jobs = {j[0]: j for j in F.lib_jobs(F.ROUTE, True, F.enemies_available())}
    gc_cache, ps2_cache, ids_cache = {}, {}, {}
    rows = []
    for item in sel:
        folder, gid = item.split(':', 1)
        row = index.get((folder, gid))
        job = jobs[folder]
        if folder not in gc_cache:
            gc_cache[folder] = gc_pictures(job[1])
            ids_cache[folder] = F.gc_eff_tables_files(job[1])[0]
            blob = job[2].read_bytes()
            effs = {}
            for k, (ty, s0, s1) in enumerate(F.dat_entries(blob)):
                if ty == 'EFF':
                    try:
                        effs[k] = F.ps2_eff_textures(blob[s0:s1])
                    except (ValueError, IndexError, struct.error):
                        pass
            ps2_cache[folder] = effs
        ctx, tid = gid.rsplit(':', 1)
        tid = int(tid, 16)
        # tpl index n of this id inside ctx: the id's position in the GameCube EFF id list
        n = ids_cache[folder][ctx].index(tid)
        gpics = gc_cache[folder].get('%s/tpl%d' % (ctx, n), [])
        ent = int(row[3].split(':')[1]) if row and ':' in row[3] else None
        ppics = ps2_cache[folder].get(ent, {}).get(tid, []) if ent is not None else []
        for f in range(min(nf, max(1, len(gpics)))):
            tiles = []
            label = '%s %s  %s %s  %s' % (folder, gid, row[3] if row else '?', row[4] if row else '?', row[8] if row else '')
            if f < len(gpics):
                key, w, h, rgba = gpics[f]
                tiles.append(tile(w, h, rgba))
                label = '%s  key %s GC %dx%d' % (label, key, w, h)
                p = lib / 'effects-tex' / folder / (key + '.re4tex')
                if not p.exists():
                    p = next(iter(lib.glob('effects-tex/*/%s.re4tex' % key)), p)
            else:
                tiles.append(checker(128, 128)); p = None
            pp = ppics[f % len(ppics)] if ppics else None
            tiles.append(tile(pp[0], pp[1], pp[2]) if pp else checker(128, 128))
            if p is not None and p.exists():
                w, h, rgba = dc_package(p)
                tiles.append(tile(w, h, rgba))
            else:
                tiles.append(checker(128, 128))
            r = Image.new('RGBA', (3 * 138, 146), (255, 255, 255, 255))
            ImageDraw.Draw(r).text((2, 2), label[:110], fill=(0, 0, 0, 255))
            for i, t in enumerate(tiles):
                r.paste(t, (i * 138, 16))
            rows.append(r)
    cols = 2
    W = cols * (3 * 138 + 20)
    H = ((len(rows) + cols - 1) // cols) * 150
    sheet = Image.new('RGBA', (W, H + 18), (255, 255, 255, 255))
    ImageDraw.Draw(sheet).text((2, 2), 'GameCube | PS2 decode | Dreamcast package (PAL4 ARGB4444)', fill=(0, 0, 0, 255))
    for i, r in enumerate(rows):
        sheet.paste(r, ((i % cols) * (3 * 138 + 20), 18 + (i // cols) * 150))
    sheet.convert('RGB').save(out)
    print(out, sheet.size, len(rows), 'rows')


if __name__ == '__main__':
    main(sys.argv[1:])
