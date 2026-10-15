#!/usr/bin/env python3
"""fx_ps2_pack.py: the PS2-sourced effect pack (test 12 fx lane, 10-14; runtime knob FX_PS2_PACK=1, TEX_PAL4_ALPHA=1).

  fx_ps2_pack.py lib <ps2lib root> <converter tag> [--rooms r100,...] [--no-common]
  fx_ps2_pack.py pack <in tex.pak> <out tex.pak> <ps2lib root> [--rooms common,r100,...]

lib converts once into the shared PS2 library (re4-assets-private/ps2lib, class effects-tex): common = GameCube
etc/core.das EFF#1 vs PS2 Core.dat EFF#1; each room (default: the 17 disc 1 route rooms) = every top-level EFF of the
decoded GameCube room archive (worldfx-cache rXXX.gc, converted as st1/rXXX.arc) paired with the PS2 rXXX.dat EFF that
shares the most texture ids. Outputs: effects-tex/<room|common>/<crc>-<fnv>.re4tex, one INDEX.tsv row per GameCube
texture id (ps2_source=NONE when the PS2 has no such id), effects-tex/NOTES.tsv. pack builds a tex.pak from the
library (the disc fixture packs from here, never from a lane copy). For each id present in both, every GameCube picture's package (its key is
prepare_native_ui.image_identity of the source TPL image, so the game's lookup is unchanged) is replaced by the PS2
picture of the same frame: PSMT4 indices, PS2 CLUT alpha 0..0x80 -> 0..255, a transposed PS2 picture (TEX0 flag 1:
the PS2 renderer swaps U and V) turned back to the GameCube orientation. Each id's frames share ONE 16-colour palette
(the PS2 CLUTs differ per frame; a weighted k-means in premultiplied ARGB picks the 16), so an id costs one PVR palette
bank; the package is PAL4 ARGB4444 twiddled, and its header flags record the covered texels (bit 31 | w | h << 11) so
the runtime samples the smaller picture whole (native_ui.cpp RE4DC_COVER_W/H, FX_PS2_PACK=1).

A GameCube id with more frames than the PS2 one (r101 0xf4: 4 vs 1) maps frame i to PS2 frame i % n (the effect's own
frame count, timing and Rnd are the GameCube data, untouched). GameCube-only ids and unselected ids keep their package.
PS2-only ids are not referenced by the GameCube data and are not packed. Only the texture pack changes: no logic.
"""
import json, struct, sys, zlib
from pathlib import Path
here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent))
sys.path.insert(0, str(here.parent.parent))
import texpack  # noqa: E402
import convert_tpl as C  # noqa: E402
import le_mirror as mirror  # noqa: E402
from prepare_native_ui import image_identity  # noqa: E402
from fx_pal4_pack import read_pak  # noqa: E402
import ps2_tpl_decode as GS  # noqa: E402  (the world agent's PS2 TPL decoder: GS memory model unswizzle, CSM1 CLUT)


def dat_entries(blob):
    n = struct.unpack_from('<I', blob, 0)[0]
    offs = struct.unpack_from('<%dI' % n, blob, 0x10)
    types = [blob[0x10 + 4 * n + 4 * i:0x10 + 4 * n + 4 * i + 4].rstrip(b'\0').decode('latin1') for i in range(n)]
    ends = list(offs[1:]) + [len(blob)]
    return [(types[i], offs[i], ends[i]) for i in range(n)]


def ps2_eff_textures(e):
    """{id: [picture]}, picture = (w, h, rgba list) in GameCube orientation, or None when the PS2 picture is neither
    PSMT4 (bitdepth 8, 16-colour CLUT) nor PSMT8 (bitdepth 9, 256-colour CSM1 CLUT). Interlace bit 1 = GS swizzle
    (indices uploaded as PSMCT32; unswizzled with ps2_tpl_decode.unswizzle_gs, lane vram12 2026-10-15), bit 0 = the
    PS2 renderer swaps U and V."""
    hdr = struct.unpack_from('<12I', e, 0)
    if hdr[0] != 0xB:
        raise ValueError('PS2 EFF version %#x' % hdr[0])
    o = hdr[1]
    n = struct.unpack_from('<I', e, o)[0]
    ids = [struct.unpack_from('<H', e, o + 4 + 8 * i)[0] for i in range(n)]
    o = hdr[6]
    if n == 0 or o == 0:
        return {}
    if struct.unpack_from('<I', e, o)[0] != n:
        raise ValueError('PS2 EFF id / TPL table sizes differ')
    out = {}
    for i, tid in enumerate(ids):
        t = o + struct.unpack_from('<I', e, o + 4 + 4 * i)[0]
        magic, count, start = struct.unpack_from('<III', e, t)
        if magic != 0x1000:
            raise ValueError('PS2 TPL magic %#x' % magic)
        pics = []
        for k in range(count):
            d = t + start + 0x30 * k
            w, h, depth, inter = struct.unpack_from('<HHHH', e, d)
            io, po = struct.unpack_from('<II', e, d + 0x20)
            if depth not in (8, 9) or inter & ~3:
                pics.append(None)
                continue
            bits = 4 if depth == 8 else 8
            raw = e[t + io:t + io + w * h * bits // 8]
            if inter & 2:
                idx = list(GS.unswizzle_gs(raw, w, h, bits))
            elif bits == 8:
                idx = list(raw)
            else:
                idx = []
                for b in raw:
                    idx += (b & 15, b >> 4)
            if bits == 4:
                clut = []
                for c in range(16):   # 8x2 CLUT in a 16-wide buffer: 0-7 at +0, 8-15 at +0x40
                    q = t + po + (c if c < 8 else 16 + c - 8) * 4
                    r, g, b, a = e[q:q + 4]
                    clut.append((r, g, b, 255 if a >= 128 else a * 255 // 128))
            else:                     # 256 colours, CSM1 order (entries 8-15 <-> 16-23 of every 32)
                clut = [c[:4] for c in GS.clut(e, t + po, 256)]
            px = [clut[v] for v in idx]
            if inter & 1:   # transposed on the PS2: picture (x, y) is stored at (y, x)
                px = [px[x * w + y] for y in range(w) for x in range(h)]
                w, h = h, w
            pics.append((w, h, px))
        out[tid] = pics
    return out


def gc_eff_tables(src, files, rel=None):
    """{ctx: [id]} and {ctx/tplN: [(key, w, h)]} for the GameCube EFF blocks in files (le_mirror's own traversal)."""
    ids, tpls = {}, {}
    orig = mirror.fmt_eff

    def wrap(sw, off, size, ctx):
        d = sw.data
        if struct.unpack_from('>I', d, off)[0] == 0xB:   # peek (big-endian source) before the block is converted
            o = off + struct.unpack_from('>I', d, off + 4)[0]
            n = struct.unpack_from('>I', d, o)[0]
            ids[ctx] = [struct.unpack_from('>H', d, o + 4 + 8 * i)[0] for i in range(n)]
        return orig(sw, off, size, ctx)

    def obs(file, offset, data, context):
        if len(data) >= 12 and struct.unpack_from('>II', data) == (C.TPL_MAGIC, 0):
            return
        try:
            imgs = C.parse_tpl(data)
        except (ValueError, IndexError, struct.error):
            return
        tpls[context] = [(image_identity(im)[0], im.width, im.height) for im in imgs]

    patched = [(tbl, k) for tbl in vars(mirror).values() if isinstance(tbl, dict) for k, v in tbl.items() if v is orig]
    prev = mirror.TPL_OBSERVER
    mirror.fmt_eff, mirror.TPL_OBSERVER = wrap, obs
    for tbl, k in patched:
        tbl[k] = wrap
    try:
        for f in files:
            data = (Path(src) / f).read_bytes()
            name = rel or f
            if name.endswith('.das') and name.startswith('st'):
                mirror.prepare_room_archive(name, data)
            else:
                mirror.convert_file(name, bytearray(data))
    finally:
        mirror.fmt_eff, mirror.TPL_OBSERVER = orig, prev
        for tbl, k in patched:
            tbl[k] = orig
    return ids, tpls


def gc_eff_tables_files(files):
    """gc_eff_tables over (le_mirror rel, path) pairs: a decoded room archive (.gc) is converted as its .arc."""
    ids, tpls = {}, {}
    for rel, path in files:
        i, t = gc_eff_tables(path.parent, [path.name], rel)
        ids.update(i); tpls.update(t)
    return ids, tpls


def premul(c):
    r, g, b, a = c
    return (r * a / 255.0, g * a / 255.0, b * a / 255.0, float(a))


def palette16(weights):
    """16 ARGB colours for {rgba: pixel count}: weighted k-means in premultiplied space (exact when <= 16 colours)."""
    cols = sorted(weights)
    if len(cols) <= 16:
        return cols
    pts = [premul(c) for c in cols]
    wts = [weights[c] for c in cols]

    def d2(p, q):
        return sum((x - y) ** 2 for x, y in zip(p, q))
    centres = [pts[max(range(len(pts)), key=lambda i: wts[i])]]   # deterministic farthest-point start
    while len(centres) < 16:
        centres.append(pts[max(range(len(pts)), key=lambda i: wts[i] * min(d2(pts[i], c) for c in centres))])
    for _ in range(30):
        acc = [[0.0] * 5 for _ in centres]
        for p, w in zip(pts, wts):
            j = min(range(len(centres)), key=lambda k: d2(p, centres[k]))
            a = acc[j]
            for t in range(4):
                a[t] += p[t] * w
            a[4] += w
        new = [tuple(a[t] / a[4] for t in range(4)) if a[4] else c for a, c in zip(acc, centres)]
        if new == centres:
            break
        centres = new
    out = []
    for r, g, b, a in centres:   # back to straight alpha
        if a < 0.5:
            out.append((0, 0, 0, 0))
        else:
            out.append(tuple(min(255, int(round(v * 255.0 / a))) for v in (r, g, b)) + (min(255, int(round(a))),))
    return out


def package(w, h, px, palette, cover):
    """A PAL4 ARGB4444 twiddled package of px (rgba) with the given palette; header flags = cover marker."""
    words = [C._pack_4444(c) for c in palette] + [0] * (16 - len(palette))
    pp = [premul(c) for c in palette]
    cache = {}

    def nearest(c):
        if c not in cache:
            p = premul(c)
            cache[c] = min(range(len(pp)), key=lambda k: sum((x - y) ** 2 for x, y in zip(p, pp[k])))
        return cache[c]
    idx = C.twiddle_16bpp([nearest(c) for c in px], w, h)
    payload = bytes(idx[i] | idx[i + 1] << 4 for i in range(0, len(idx), 2)) + struct.pack('<16H', *words)
    alphas = [palette[i][3] for i in set(idx)]
    flags = C.FLAG_ALPHA if any(a < 255 for a in alphas) else 0
    if flags and all(a in (0, 255) for a in alphas):
        flags |= C.FLAG_BINARY_ALPHA
    tex_off = C.HEADER.size
    data_off = tex_off + C.TEXTURE.size
    rec = C.TEXTURE.pack(b'ps2-source'.ljust(64, b'\0'), w, h, C.FORMAT_PAL4_ARGB4444, data_off, len(payload),
                         flags, C.PAYLOAD_TWIDDLED, 0)
    body = rec + payload
    hdr = C.HEADER.pack(C.MAGIC, C.VERSION, C.HEADER.size, C.TEXTURE.size, 1, tex_off, data_off, len(payload),
                        zlib.crc32(body) & 0xffffffff, 1, 1 << 31 | cover[0] | cover[1] << 11)
    err = 0.0
    for c in px:
        p, q = premul(c), pp[nearest(c)]
        err += max(abs(x - y) for x, y in zip(p, q))
    return hdr + body, err / len(px)


ROUTE = 'r100 r101 r102 r103 r104 r105 r106 r107 r108 r109 r10a r10b r11a r11b r117 r118 r119'.split()
INDEX_HEAD = 'class\troom\tgc_id\tps2_source\tdc_format\tconverter\tsha256\tbytes\tgate\towner_lane'


def convert_set(gc_ctx, gids, gc_tpls, ps2, ps2_name, outdir, keys_seen):
    """Rows (one per GameCube texture id of gc_ctx) and the packages written under outdir."""
    import hashlib
    rows = []
    for n, tid in enumerate(gids):
        gpics = gc_tpls.get('%s/tpl%d' % (gc_ctx, n), [])
        gid = '%s:0x%02x' % (gc_ctx, tid)
        row = dict(gc_id=gid, ps2_source='NONE', dc_format='', sha256='', bytes=0, note='')
        if tid not in ps2:
            row['note'] = 'no PS2 counterpart in %s (%d GC pictures keep their package)' % (ps2_name if ps2_name != 'NONE' else 'any top-level PS2 EFF; nested ETS .eff files are not paired', len(gpics))
            rows.append(row)
            continue
        row['ps2_source'] = ps2_name
        ppics = ps2[tid]
        if not gpics or any(p is None for p in ppics):
            row['dc_format'] = 'NOT_CONVERTED'
            row['note'] = 'PS2 picture is neither PSMT4 nor PSMT8' if gpics else 'no GC pictures'
            rows.append(row)
            continue
        weights = {}
        for w, h, px in ppics:
            for c in px:
                weights[c] = weights.get(c, 0) + 1
        pal = palette16(weights)
        h_all = hashlib.sha256()
        total, errs, shared = 0, [], set()
        for f, (key, gw, gh) in enumerate(gpics):
            w, h, px = ppics[f % len(ppics)]
            blob, err = package(w, h, px, pal, (w, h))
            path = outdir / (key + '.re4tex')
            if key in keys_seen:   # one package per key on the disc: the first conversion (common, then route order) wins
                if keys_seen[key][0] != blob:
                    shared.add(keys_seen[key][1])
                continue
            keys_seen[key] = (blob, gid)
            outdir.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)
            h_all.update(key.encode() + blob)
            total += len(blob)
            errs.append(err)
        row.update(dc_format='PAL4_ARGB4444 %dx%d x%d (GC %dx%d x%d)' % (ppics[0][0], ppics[0][1], len(gpics),
                   gpics[0][1], gpics[0][2], len(ppics)), sha256=h_all.hexdigest(), bytes=total,
                   note='err %.2f, %d PS2 colours -> 16' % (sum(errs) / max(1, len(errs)), len(weights)) +
                   ('; pictures shared with %s keep that conversion' % ','.join(sorted(shared)) if shared else ''))
        rows.append(row)
    return rows


def pair_effs(gc_ids, ps2_effs):
    """[(gc ctx, ps2 entry)] for top-level EFFs: each GameCube table with the PS2 one sharing the most ids."""
    out = []
    for ctx, ids in gc_ids.items():
        best, score = None, 0
        for ent, t in ps2_effs.items():
            s = len(set(ids) & set(t))
            if s > score:
                best, score = ent, s
        out.append((ctx, best))
    return out


# Enemy effect tables (lane vram12, 2026-10-15): each enemy's own EFF in its GameCube em/emXX.drs, paired with the PS2
# emXX.dat EFF (inputs of the ps2cast lane). Library folder effects-tex/<emXX>.
ENEMY_INPUTS = Path('/root/probe/lanes/ps2cast/inputs')


def enemies_available():
    return sorted(p.stem for p in ENEMY_INPUTS.glob('em*.drs') if (ENEMY_INPUTS / (p.stem + '.dat')).exists())


def lib_jobs(rooms, common=True, enemies=()):
    """(library folder, [(le_mirror rel, GameCube path)], PS2 .dat path, PS2 label, only these EFF contexts or None)."""
    cache = Path('/root/probe/worldfx-cache')
    gc_tree = Path('/root/re4data')
    ps2_core = Path('/root/probe/lanes-20261014/fx12/ps2/Core.dat')
    jobs = []
    if common:
        jobs.append(('common', [('etc/core.das', gc_tree / 'etc/core.das')], ps2_core, 'Core.dat',
                     {'etc/core.das:0#1'}))
    for r in rooms:
        jobs.append((r, [('st1/%s.arc' % r, cache / ('%s.gc' % r))], cache / ('%s.ps2' % r), '%s.dat' % r, None))
    for em in enemies:
        jobs.append((em, [('em/%s.drs' % em, ENEMY_INPUTS / ('%s.drs' % em))], ENEMY_INPUTS / ('%s.dat' % em), '%s.dat' % em, None))
    return jobs


def lib_args(a):
    rooms = ROUTE
    if '--rooms' in a:
        rooms = a[a.index('--rooms') + 1].split(',')
    enemies = enemies_available()
    if '--enemies' in a:
        enemies = [x for x in a[a.index('--enemies') + 1].split(',') if x]
    return rooms, '--no-common' not in a, enemies


def lib_main(a):
    """lib <libroot> <converter tag> [--rooms r100,...] [--no-common] [--enemies em13,...|'']: convert into
    ps2lib/effects-tex + INDEX.tsv rows (enemies default: every emXX with both inputs in ENEMY_INPUTS). A row whose
    package bytes (sha256) did not change keeps its converter tag and gate."""
    libroot, tag = Path(a[0]), a[1]
    rooms, common, enemies = lib_args(a)
    out_root = libroot / 'effects-tex'
    rows_all, keys_seen, summary = [], {}, []
    jobs = lib_jobs(rooms, common, enemies)
    for room, files, ps2_path, ps2_label, only in jobs:
        gc_ids, gc_tpls = gc_eff_tables_files(files)
        if only:
            gc_ids = {k: v for k, v in gc_ids.items() if k in only}
        blob = ps2_path.read_bytes()
        ps2_effs = {}
        for k, (ty, s0, s1) in enumerate(dat_entries(blob)):
            if ty == 'EFF':
                try:
                    ps2_effs[k] = ps2_eff_textures(blob[s0:s1])
                except (ValueError, IndexError, struct.error) as ex:   # an EFF without a picture table
                    print('%s: PS2 %s entry %d skipped (%s)' % (room, ps2_label, k, ex))
        outdir = out_root / room
        nconv = nnone = nskip = 0
        for ctx, ent in pair_effs(gc_ids, ps2_effs):
            ps2 = ps2_effs.get(ent, {}) if ent is not None else {}
            name = '%s:%d' % (ps2_label, ent) if ent is not None else 'NONE'
            for row in convert_set(ctx, gc_ids[ctx], gc_tpls, ps2, name, outdir, keys_seen):
                row['room'] = room
                rows_all.append(row)
                if row['ps2_source'] == 'NONE':
                    nnone += 1
                elif row['dc_format'] == 'NOT_CONVERTED':
                    nskip += 1
                else:
                    nconv += 1
        summary.append('%s: %d ids converted, %d no PS2 counterpart, %d not converted' % (room, nconv, nnone, nskip))
    # INDEX.tsv: replace this class's rows, keep every other class's rows
    idx = libroot / 'INDEX.tsv'
    old = idx.read_text().splitlines() if idx.exists() else [INDEX_HEAD]
    keep = [l for l in old[1:] if l and not l.startswith('effects-tex\t')]
    prev = {}
    for l in old[1:]:
        f = l.split('\t')
        if len(f) >= 10 and f[0] == 'effects-tex':
            prev[(f[1], f[2])] = f
    new = []
    for r in rows_all:
        dc = r['dc_format'] or ('-' if r['ps2_source'] == 'NONE' else '')
        row = ['effects-tex', r['room'], r['gc_id'], r['ps2_source'], dc, tag, r['sha256'] or '-', str(r['bytes']), 'UNGATED', 'fx12']
        o = prev.get((r['room'], r['gc_id']))
        if o and o[6] == row[6] and o[3] == row[3] and o[4] == row[4]:
            row = o[:10]   # unchanged package: keep its converter tag, gate and owner
        new.append('\t'.join(row))
    idx.write_text('\n'.join([INDEX_HEAD] + keep + new) + '\n')
    notes = out_root / 'NOTES.tsv'
    notes.write_text('room\tgc_id\tps2_source\tnote\n' + ''.join('%s\t%s\t%s\t%s\n' % (r['room'], r['gc_id'], r['ps2_source'], r['note']) for r in rows_all))
    print('\n'.join(summary))
    print('fx_ps2_pack lib: %d rows, %d packages' % (len(rows_all), len(keys_seen)))


def pack_main(a):
    """pack <in tex.pak> <out tex.pak> <libroot> [--rooms common,r100,...]: replace the library's keys in a tex.pak."""
    src, dst, libroot = a[0], a[1], Path(a[2])
    dirs = sorted(p for p in (libroot / 'effects-tex').iterdir() if p.is_dir())
    if '--rooms' in a:
        sel = set(a[a.index('--rooms') + 1].split(','))
        dirs = [d for d in dirs if d.name in sel]
    pkgs = read_pak(Path(src).read_bytes())
    n = absent = 0
    for d in dirs:
        for f in sorted(d.glob('*.re4tex')):
            k = tuple(int(v, 16) for v in f.stem.split('-'))
            if k not in pkgs:
                absent += 1   # the source disc has no package for it either: added (the runtime reads it from the pack)
            pkgs[k] = f.read_bytes()
            n += 1
    out, _ = texpack.build(pkgs)
    texpack.verify(out)
    Path(dst).write_bytes(out)
    print('fx_ps2_pack pack: %d library packages from %s (%d not in the input pack)' % (n, ','.join(d.name for d in dirs), absent))


def main():
    a = sys.argv[1:]
    if a and a[0] == 'lib':
        return lib_main(a[1:])
    if a and a[0] == 'pack':
        return pack_main(a[1:])
    raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
