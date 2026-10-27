#!/usr/bin/env python3
"""ps2_items.py: PS2 pickups (ITM item models + SS/cmn pick-up zoom models) and breakable debris (Efm effect models
inside EFF files: room EFF, ETM .eff members, core EFF) for the native rooms (lane items, test 12, 2026-10-14).

The game keeps every GameCube identity and all of its logic: the item id table (cItmSys), the EFF efm id tables
(efmRegist), the ETM names, collision, pick-up and break code. Only two kinds of bytes change, both in place:
  geometry  the GC ModelData is rebuilt with the PS2 BIN's triangles (ps2_objects.rebuild: GC header, joints, part
            headers and order kept; tools/ps2_objects.py) and written over the GC model's slot in the native payload,
            zero padded. Offsets, entry sizes, the payload size and the NTR / ESQ tables do not move, so the heap-4
            layout is the control's. A model whose PS2 positions exceed the GC s16 range at the GC shift is
            re-quantised one shift lower (the GC copy used for part matching is halved the same way).
  pictures  every GC TPL image a converted part samples is replaced by the PS2 TPL entry with the same index (the PS2
            UVs index the PS2 pictures). The PS2 picture's identity is its GC CMPR encoding (format 14, a fixed
            deterministic encoder) hashed like prepare_native_ui.image_identity / native_ui.cpp image_key. In a TPL
            the payload already externalised (NTR R4NREF record) the record and the image header take the new key and
            size; in a resident TPL (EFF efm pictures, the runtime hashes the texels) the CMPR texels are written in
            place of the GC texels. The displayed picture is the <key>.re4tex built from the PS2 RGBA by
            ps2_items_tex.py (Windows Python: VQ RGB565 / ARGB1555 / ARGB4444, the ps2_room_r4im.py rules).

  ps2_items.py convert --lib <ps2lib> [--rooms r100,...] [--classes items,breakables] [--commit C]
      every route room in one pass (+ core EFF and SS/cmn): <lib>/<class>/<room|common>/<name>.bin (LE ModelData),
      <name>.json (source, GC slot identity, picture swaps), <name>.t<j>.png / .cmpr; manifest.json per class;
      INDEX.tsv rows (ps2_source=NONE for a GC model with no PS2 counterpart).
  ps2_items.py pack --dar <in> --room rNNN --lib <ps2lib> --out <dar> [--json report] [--classes ...]
  ps2_items.py pack-core --das <core.das> --lib <ps2lib> --out <core.das>
  ps2_items.py pack-ss --src <dir with DC ss/cmn files> --lib <ps2lib> --out <dir>
  ps2_items.py census --dar <dar> --room rNNN --lib <ps2lib>     (per slot: PS2 / GC / NONE / ?; exit 1 on GC)
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[2] / 'tools')]
import le_mirror as lm  # noqa: E402
import ps2_bin as pb  # noqa: E402
import ps2_objects as po  # noqa: E402
import room_smd as rs  # noqa: E402

ROUTE = 'r100 r101 r102 r103 r104 r105 r106 r107 r108 r109 r10a r10b r11a r11b r117 r118 r119'.split()
WA = Path(os.environ.get('RE4_WORLD_AGENT', '/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926'))
CMPR = 14
TOOL_VERSION = 'ps2_items-v2'
PS2_KEYS = set()   # census --catalog


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_tpl = None


def ps2tpl():
    global _tpl
    if _tpl is None:
        _tpl = load('ps2_tpl_decode', WA / 'from-main/ps2-trees/tools/ps2_tpl_decode.py')
    return _tpl


# ------------------------------------------------------------------------------------------ containers


def itm_tables(b, en):
    """ITM pack -> (ids, bin offsets, tpl offsets) relative to the pack."""
    ver, oi, ob, ot = struct.unpack_from(en + '4I', b, 0)
    if ver != 3:
        raise ValueError('ITM version %d' % ver)
    n = struct.unpack_from(en + 'I', b, oi)[0]
    ids = [struct.unpack_from(en + 'H', b, oi + 4 + 8 * i)[0] for i in range(n)]
    bo = [ob + struct.unpack_from(en + 'I', b, ob + 4 + 4 * i)[0] for i in range(n)]
    to = [ot + struct.unpack_from(en + 'I', b, ot + 4 + 4 * i)[0] for i in range(n)]
    return ids, bo, to, (oi, ob, ot)


def spans(starts, limits):
    """{start: next boundary} over the sorted union of starts and extra limits."""
    lim = sorted(set(starts) | set(limits))
    return {s: next(x for x in lim if x > s) for s in starts}


def itm_assets(b, en):
    ids, bo, to, tabs = itm_tables(b, en)
    end = spans(bo + to, list(tabs) + [len(b)])
    return {i: (b[bo[k]:end[bo[k]]], b[to[k]:end[to[k]]]) for k, i in enumerate(ids)}


def eff_efm(b, en):
    """EFF efm entries -> [(id, model off, tpl off, model end)] relative to the EFF block (model end = tpl off)."""
    h = struct.unpack_from(en + '12I', b, 0)
    if h[0] != 0xB or not h[5]:
        return []
    n = struct.unpack_from(en + 'I', b, h[5])[0]
    out = []
    for i in range(n):
        idv = struct.unpack_from(en + 'H', b, h[5] + 4 + 8 * i)[0]
        e = h[11] + struct.unpack_from(en + 'I', b, h[11] + 4 + 4 * i)[0]
        x0, om, ot, omot, ox = struct.unpack_from(en + '5I', b, e)
        out.append((idv, e + om, e + ot))
    return out


def eff_tpl_end(b, en, tpl):
    """end of a TPL inside an EFF block: the TPL's own extent (images + palettes)."""
    n, desc = struct.unpack_from(en + '2I', b, tpl + 4)
    end = tpl + desc + 8 * n
    for i in range(n):
        h, c = struct.unpack_from(en + '2I', b, tpl + desc + 8 * i)
        hh, ww, fmt, data = struct.unpack_from(en + '2H2I', b, tpl + h)
        end = max(end, tpl + h + 36, tpl + data + image_size(ww, hh, fmt))
        if c:
            cn, cfmt, cdata = struct.unpack_from(en + 'H2xII', b, tpl + c)
            end = max(end, tpl + cdata + 2 * cn)
    return end


def image_size(w, h, fmt):
    bpp = {0: 4, 1: 8, 2: 8, 3: 16, 4: 16, 5: 16, 6: 32, 8: 4, 9: 8, 10: 16, 14: 4}[fmt]
    bw, bh = {4: (8, 8), 8: (8, 4), 16: (4, 4), 32: (4, 4)}[bpp]
    w2, h2 = (w + bw - 1) // bw * bw, (h + bh - 1) // bh * bh
    return w2 * h2 * bpp // 8


def gc_tpl_images(t, en='>'):
    n, desc = struct.unpack_from(en + '2I', t, 4)
    out = []
    for i in range(n):
        h, clut = struct.unpack_from(en + '2I', t, desc + 8 * i)
        hh, ww, fmt, data = struct.unpack_from(en + '2H2I', t, h)
        out.append(dict(j=i, w=ww, h=hh, fmt=fmt, hdr=h, data=data, clut=clut, lod=tuple(t[h + 33:h + 36])))
    return out


# ------------------------------------------------------------------------------------------ sources


class Sources:
    def __init__(self, gc_iso=po.GC_ISO, ps2_iso=po.PS2_ISO):
        from assetpipe.rooms import GcIso
        self.g = GcIso(gc_iso)
        self.ps2_iso = ps2_iso
        self.ix = pb.afs_index(ps2_iso)
        self.rooms = dict((r, k) for r, k in self.g.rooms())

    def gc_room(self, room):
        d = self.g.read(self.rooms[room])
        return rs.decode_das(d) if d[:32] == rs.CONTAINER_MAGIC else d

    def ps2_room(self, room):
        return pb.afs_read(self.ps2_iso, room + '.dat', self.ix)

    def gc_core(self):
        d = self.g.read('etc/core.das')
        kind, size, dest, off = struct.unpack_from('>4I', d, 0x20)
        return d[off:off + size]

    def ps2_core(self):
        return pb.afs_read(self.ps2_iso, 'Core.dat', self.ix)

    def gc_file(self, rel):
        return self.g.read(rel)

    def ps2_file(self, name):
        k = next((k for k in self.ix if k.lower() == name.lower()), None)
        return pb.afs_read(self.ps2_iso, k, self.ix) if k else None


def room_assets(src, room):
    """[(class, name, locator, gc bin, gc tpl, ps2 bin | None, ps2 tpl | None)] of one room."""
    g = src.gc_room(room)
    p = src.ps2_room(room)
    ge = [(t.rstrip(b'\0').decode(), s, e) for t, s, e in rs.tagged_entries(g, '>')]
    pe = [(t, bb) for i, t, bb in pb.dat_entries(p)]
    out = []
    gi = [x for x in ge if x[0] == 'ITM']
    pi = [bb for t, bb in pe if t == 'ITM']
    if gi:
        pm = itm_assets(pi[0], '<') if pi else {}
        for i, (b_, t_) in itm_assets(g[gi[0][1]:gi[0][2]], '>').items():
            pb_, pt_ = pm.get(i, (None, None))
            out.append(('items', 'itm%02x' % i, dict(kind='ITM', id=i), b_, t_, pb_, pt_))
    peff = [bb for t, bb in pe if t == 'EFF']
    for k, eb in enumerate([g[s:e] for t, s, e in ge if t == 'EFF']):
        pmod = {}
        if k < len(peff):
            pmod = {i: (peff[k][mo:to], peff[k][to:]) for i, mo, to in eff_efm(peff[k], '<')}
        for i, mo, to in eff_efm(eb, '>'):
            pb_, pt_ = pmod.get(i, (None, None))
            out.append(('breakables', 'eff%d_efm%02x' % (k, i), dict(kind='EFF', eff=k, id=i), eb[mo:to],
                        eb[to:eff_tpl_end(eb, '>', to)], pb_, pt_))
    pets = {}
    for t, bb in pe:
        if t == 'ETM':
            for nm, s2, e2 in po.etm_entries(bb, '<'):
                if nm.endswith('.eff'):
                    body = bb[s2 + 0x40:e2]
                    pets[nm] = {i: (body[mo:to], body[to:]) for i, mo, to in eff_efm(body, '<')}
    for t, s, e in ge:
        if t != 'ETM':
            continue
        eb = g[s:e]
        for nm, s2, e2 in po.etm_entries(eb, '>'):
            if not nm.endswith('.eff'):
                continue
            body = eb[s2 + 0x40:e2]
            for i, mo, to in eff_efm(body, '>'):
                pb_, pt_ = pets.get(nm, {}).get(i, (None, None))
                out.append(('breakables', '%s_efm%02x' % (nm[:-4], i), dict(kind='ETM', member=nm, id=i), body[mo:to],
                            body[to:eff_tpl_end(body, '>', to)], pb_, pt_))
    return out


def core_assets(src):
    g = src.gc_core()
    p = src.ps2_core()
    ge = rs.tagged_entries(g, '>')
    pe = {i: (t, bb) for i, t, bb in pb.dat_entries(p)}
    out = []
    for k, (t, s, e) in enumerate(ge):
        if t.rstrip(b'\0') != b'EFF':
            continue
        eb = g[s:e]
        pt, pbb = pe.get(k, (None, None))
        pmod = {i: (pbb[mo:to], pbb[to:]) for i, mo, to in eff_efm(pbb, '<')} if pt == 'EFF' else {}
        for i, mo, to in eff_efm(eb, '>'):
            pb_, pt_ = pmod.get(i, (None, None))
            out.append(('breakables', 'core%d_efm%02x' % (k, i), dict(kind='CORE', entry=k, id=i), eb[mo:to],
                        eb[to:eff_tpl_end(eb, '>', to)], pb_, pt_))
    return out


def ss_assets(src):
    out = []
    names = sorted(f for f in src.g.files if f.lower().startswith('ss/cmn/itm') and f.lower().endswith('.bin'))
    for f in names:
        stem = f.split('/')[-1][:-4].lower()
        gb, gt = src.gc_file(f), src.gc_file(f[:-4] + '.tpl')
        pb_, pt_ = src.ps2_file(stem + '.bin'), src.ps2_file(stem + '.tpl')
        out.append(('items', 'ss_' + stem, dict(kind='SS', file='ss/cmn/%s' % stem), gb, gt, pb_, pt_))
    return out


# ------------------------------------------------------------------------------------------ geometry


def halve_shift(gc):
    """the GC BIN one fixed-point shift lower (positions halved): same float geometry, twice the range."""
    d = bytearray(gc)
    if d[0x28] == 0:
        raise ValueError('shift 0: cannot lower')
    d[0x28] -= 1
    vtx, nv = struct.unpack_from('>I', d, 0x30)[0], struct.unpack_from('>H', d, 0x38)[0]
    for i in range(nv):
        x, y, z, w = struct.unpack_from('>4h', d, vtx + 8 * i)
        struct.pack_into('>4h', d, vtx + 8 * i, int(round(x / 2)), int(round(y / 2)), int(round(z / 2)), w)
    return bytes(d)


def convert_geometry(gc, ps2, pos_offset=None):
    shifted = 0
    src = gc
    while True:
        try:
            new, st = po.rebuild(src, ps2, pos_offset=pos_offset)
            break
        except ValueError as ex:
            if 'outside the s16 range' not in str(ex) or shifted >= 2:
                raise
            src = halve_shift(src)
            shifted += 1
    st['shift_lowered'] = shifted
    return new, st


def same_geometry(gc, ps2, q=0.5):
    m = po.GcModel(gc)
    key = lambda t: tuple(sorted(tuple(round(x / q) for x in v) for v in t))
    a = [key(tuple(m.p(r[0]) for r in t)) for p in m.parts for t in p['tris']]
    b = [key(tuple(c['p'] for c in cs)) for t, cs in pb.triangles(pb.parse_bin(ps2))]
    return len(a) == len(b) and len(set(a) & set(b)) >= len(set(a)) - max(1, len(a) // 100)


# ------------------------------------------------------------------------------------------ pictures


def rgb565(c):
    r, g, b = c
    return ((r * 31 + 127) // 255) << 11 | ((g * 63 + 127) // 255) << 5 | ((b * 31 + 127) // 255)


def expand565(v):
    r, g, b = (v >> 11) & 31, (v >> 5) & 63, v & 31
    return (r << 3 | r >> 2, g << 2 | g >> 4, b << 3 | b >> 2)


def cmpr_encode(w, h, rgba):
    """deterministic GX CMPR (DXT1, big-endian colours, 8x8 tiles of four 4x4 blocks): endpoints = the darkest and
    the brightest opaque texels; any texel below alpha 128 selects the 3-colour mode with index 3 transparent."""
    out = bytearray()
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            for by, bx in ((0, 0), (0, 4), (4, 0), (4, 4)):
                px = []
                for y in range(4):
                    for x in range(4):
                        X, Y = min(tx + bx + x, w - 1), min(ty + by + y, h - 1)
                        o = 4 * (Y * w + X)
                        px.append(tuple(rgba[o:o + 4]))
                op = [p for p in px if p[3] >= 128]
                trans = len(op) < 16
                if op:
                    lum = lambda p: 299 * p[0] + 587 * p[1] + 114 * p[2]
                    lo, hi = min(op, key=lum), max(op, key=lum)
                    c0, c1 = rgb565(hi[:3]), rgb565(lo[:3])
                else:
                    c0 = c1 = 0
                if trans:
                    c0, c1 = min(c0, c1), max(c0, c1)
                    e0, e1 = expand565(c0), expand565(c1)
                    pal = [e0, e1, tuple((a + b) // 2 for a, b in zip(e0, e1))]
                else:
                    if c0 == c1:
                        c1 = c1 - 1 if c1 else 0
                        if c0 == c1:
                            c0 = 1
                    if c0 < c1:
                        c0, c1 = c1, c0
                    e0, e1 = expand565(c0), expand565(c1)
                    pal = [e0, e1, tuple((2 * a + b) // 3 for a, b in zip(e0, e1)), tuple((a + 2 * b) // 3 for a, b in zip(e0, e1))]
                bits = 0
                for k, p in enumerate(px):
                    if trans and p[3] < 128:
                        ix = 3
                    else:
                        ix = min(range(len(pal)), key=lambda q: sum((a - b) ** 2 for a, b in zip(pal[q], p[:3])))
                    bits |= ix << (30 - 2 * k)
                out += struct.pack('>HHI', c0, c1, bits)
    return bytes(out)


def identity_key(w, h, fmt, data):
    """prepare_native_ui.image_identity / native_ui.cpp image_key of a non-indexed image."""
    payload = struct.pack('<5I', w, h, fmt, 0xffffffff, 0) + data
    fnv = 2166136261
    for x in payload:
        fnv = ((fnv ^ x) * 16777619) & 0xffffffff
    return '%08x-%08x' % (zlib.crc32(payload) & 0xffffffff, fnv)


def write_png(path, w, h, rgba):
    ps2tpl().write_png(str(path), w, h, rgba)


ORIENT = ('id', 'flipx', 'flipy', 'rot180', 'transpose', 'rot90cw', 'rot90ccw', 'antitranspose')


def orient(w, h, rgba, o):
    """the picture under orientation o -> (w', h', rgba')"""
    swap = o in ('transpose', 'rot90cw', 'rot90ccw', 'antitranspose')
    W, H = (h, w) if swap else (w, h)
    out = bytearray(W * H * 4)
    for y in range(H):
        for x in range(W):
            if o == 'id': sx, sy = x, y
            elif o == 'flipx': sx, sy = w - 1 - x, y
            elif o == 'flipy': sx, sy = x, h - 1 - y
            elif o == 'rot180': sx, sy = w - 1 - x, h - 1 - y
            elif o == 'transpose': sx, sy = y, x
            elif o == 'rot90cw': sx, sy = y, h - 1 - x
            elif o == 'rot90ccw': sx, sy = w - 1 - y, x
            else: sx, sy = w - 1 - y, h - 1 - x
            i, k = 4 * (y * W + x), 4 * (sy * w + sx)
            out[i:i + 4] = rgba[k:k + 4]
    return W, H, out


def picture_error(gw, gh, grgba, w, h, rgba):
    """mean squared RGB error of rgba (w x h) resampled to the GC picture's size (nearest), 16x16 grid samples."""
    n, e = 0, 0
    for gy in range(0, gh, max(1, gh // 16)):
        for gx in range(0, gw, max(1, gw // 16)):
            x, y = gx * w // gw, gy * h // gh
            a, b = grgba[gy * gw + gx], rgba[4 * (y * w + x):4 * (y * w + x) + 3]
            e += sum((int(p) - int(q)) ** 2 for p, q in zip(a[:3], b))
            n += 1
    return e / max(n, 1)


def resample(w, h, rgba, W, H):
    """nearest-neighbour resize of an RGBA picture to W x H"""
    out = bytearray(W * H * 4)
    for y in range(H):
        sy = y * h // H
        for x in range(W):
            k = 4 * (sy * w + x * w // W)
            out[4 * (y * W + x):4 * (y * W + x) + 4] = rgba[k:k + 4]
    return out


def convert_pictures(gc_tpl, ps2_tpl_bytes, used, out_dir, name, pairs=()):
    """-> [swap dicts], [kept GC images with reasons], [pair dicts]. The PS2 TPL's interlace bit 0 marks a picture
    stored rotated: the PS2 UVs are the GC UVs (checked on the route models), so the picture is turned back to the GC
    orientation; the orientation is chosen by the smallest error against the GC picture and must be a rotation
    exactly when the bit is set (else the picture is kept GC and listed).

    pairs = (color image, alpha image) of every drawn part with material flag 4 (ModelPart alphaTex): the runtime
    draws such a part from ONE package keyed material_pair_identity(color key, mask key) and needs the mask at the
    colour's size (native_ui.cpp model_mask_key, reason 16). The mask of a swapped colour is therefore swapped too:
    the PS2 TPL entry of the same index (else the GC mask), as an intensity picture resampled to the colour's PS2
    size. The pair package itself is built by ps2_items_tex.py from the two PNGs. A mask whose colour stays GC
    stays GC (the GC pair package is unchanged)."""
    import convert_tpl as ct
    T = ps2tpl()
    gimg = gc_tpl_images(gc_tpl)
    gdec = ct.parse_tpl(gc_tpl)
    swaps, kept, pair_out = [], [], []
    masks = {}
    for c, m in pairs:
        masks.setdefault(m, set()).add(c)
    mask_px = {}
    try:
        pt = T.parse_tpl(ps2_tpl_bytes)['entries'] if ps2_tpl_bytes else []
    except Exception as ex:
        pt, err = [], str(ex)
    else:
        err = None
    for im in gimg:
        j = im['j']
        if j not in used and j not in masks:
            continue
        if j >= len(pt):
            if j in masks and j not in used:
                gi = gdec[j]
                mask_px[j] = ('gc', gi.width, gi.height, bytearray(b''.join(bytes(p) for p in ct.decode_image(gi))), 0)
                continue
            kept.append(dict(j=j, reason=err or 'no PS2 TPL entry %d' % j))
            continue
        w, h, rgba, stats = T.decode(ps2_tpl_bytes, pt[j])
        gi = gdec[j]
        gpx = ct.decode_image(gi)
        errs = {o: picture_error(gi.width, gi.height, gpx, *orient(w, h, rgba, o)) for o in ORIENT}
        best = min(ORIENT, key=lambda o: (errs[o], ORIENT.index(o)))
        rotated = best in ('transpose', 'rot90cw', 'rot90ccw', 'antitranspose')
        want_rot = bool(pt[j]['interlace'] & 1)
        if rotated != want_rot or (not want_rot and best != 'id'):
            alt = [o for o in ORIENT if (o in ('transpose', 'rot90cw', 'rot90ccw', 'antitranspose')) == want_rot]
            alt = [o for o in alt if want_rot or o == 'id']
            best2 = min(alt, key=lambda o: (errs[o], ORIENT.index(o)))
            if errs[best2] > 1.5 * errs[best] + 200:
                if j in masks and j not in used:
                    mask_px[j] = ('gc', gi.width, gi.height, bytearray(b''.join(bytes(p) for p in gpx)), 0)
                    continue
                kept.append(dict(j=j, reason='PS2 picture orientation unclear (best %s %.0f, interlace %d)' % (best, errs[best], pt[j]['interlace'])))
                continue
            best = best2
        w, h, rgba = orient(w, h, rgba, best)
        if j in masks and j not in used:
            mask_px[j] = ('ps2', w, h, rgba, round(errs[best], 1))
            continue
        if w % 8 or h % 8 or w > 1024 or h > 1024:
            kept.append(dict(j=j, reason='PS2 picture %dx%d not CMPR-encodable' % (w, h)))
            continue
        data = cmpr_encode(w, h, rgba)
        key = identity_key(w, h, CMPR, data)
        png = out_dir / ('%s.t%d.png' % (name, j))
        write_png(png, w, h, rgba)
        (out_dir / ('%s.t%d.cmpr' % (name, j))).write_bytes(data)
        alpha = sorted(set(rgba[3::4]))
        ga = sorted(set(p[3] for p in gpx))
        # gc_alpha: the GC picture's alpha class. The GC material (kept) decides transparency: ps2_items_tex.py
        # makes the package opaque when the GC picture is opaque (itm78 / itm79 / ss_itm78 / ss_itm97 carry PS2
        # colour alpha 0..255 on an unmasked part whose GC picture is opaque: drawn as coverage it would make
        # the box see-through; what the PS2 uses it for is not established)
        swaps.append(dict(j=j, w=w, h=h, fmt=CMPR, key=key, png=png.name, cmpr=('%s.t%d.cmpr' % (name, j)),
                          gc_alpha='opaque' if ga == [255] else ('cutout' if set(ga) <= {0, 255} else 'graded'),
                          cmpr_bytes=len(data), gc=dict(w=im['w'], h=im['h'], fmt=im['fmt'], lod=im['lod']),
                          ps2=dict(bitdepth=pt[j]['bitdepth'], interlace=pt[j]['interlace']), orientation=best,
                          match_error=round(errs[best], 1),
                          alpha='opaque' if alpha == [255] else ('cutout' if set(alpha) <= {0, 255} else 'graded')))
    import prepare_native_ui as pnu
    byj = {s['j']: s for s in swaps}
    for m, cols in sorted(masks.items()):
        if m in used:
            kept.append(dict(j=m, reason='image %d is both a colour and a mask (pair not built)' % m))
            continue
        sw = [byj[c] for c in sorted(cols) if c in byj]
        if not sw:
            continue  # every colour of this mask stayed GC: the GC pair stays
        if len(sw) != len(cols) or len(set((s['w'], s['h']) for s in sw)) != 1:
            raise ValueError('%s: mask %d shared by colours %s of different sizes / sources' % (name, m, sorted(cols)))
        if m not in mask_px:
            raise ValueError('%s: mask %d has no picture' % (name, m))
        src, w, h, rgba, merr = mask_px[m]
        W, H = sw[0]['w'], sw[0]['h']
        rgba = resample(w, h, rgba, W, H) if (w, h) != (W, H) else rgba
        gray = bytearray(len(rgba))
        vals = [(rgba[i] + rgba[i + 1] + rgba[i + 2]) // 3 for i in range(0, len(rgba), 4)]
        # PS2 masks are 4-bit grey levels decoded as n * 16 (0..240): expand to n * 17 (0..255) like a GX I4 mask,
        # so a full mask is fully opaque (checked: itm06 / core efm25 / et04 levels match the GC masks' spread)
        four_bit = src == 'ps2' and all(v % 16 == 0 for v in vals)
        for k, v in enumerate(vals):
            v = (v // 16) * 17 if four_bit else v
            gray[4 * k:4 * k + 4] = bytes((v, v, v, 255))
        data = cmpr_encode(W, H, gray)
        key = identity_key(W, H, CMPR, data)
        png = out_dir / ('%s.t%d.png' % (name, m))
        write_png(png, W, H, gray)
        (out_dir / ('%s.t%d.cmpr' % (name, m))).write_bytes(data)
        gm = next(x for x in gimg if x['j'] == m)
        swaps.append(dict(j=m, w=W, h=H, fmt=CMPR, key=key, png=png.name, cmpr=('%s.t%d.cmpr' % (name, m)),
                          cmpr_bytes=len(data), gc=dict(w=gm['w'], h=gm['h'], fmt=gm['fmt'], lod=gm['lod']),
                          role='mask', mask_source=src, mask_size=[w, h], match_error=merr, alpha='opaque',
                          mask_levels='4bit*17' if four_bit else 'as decoded'))
        for s in sw:
            pair_out.append(dict(color=s['j'], mask=m, color_key=s['key'], mask_key=key,
                                 key=pnu.material_pair_identity(s['key'], key), w=W, h=H,
                                 color_png=s['png'], mask_png=png.name, mask_source=src))
    return swaps, kept, pair_out


# ------------------------------------------------------------------------------------------ convert


def index_row(cls, room, gc_id, ps2_source, dc_format, conv, digest, nbytes, gate='UNGATED'):
    return '\t'.join([cls, room, gc_id, ps2_source, dc_format, conv, digest, str(nbytes), gate, 'items'])


def convert(args):
    lib = Path(args.lib)
    src = Sources()
    rooms = args.rooms.split(',') if args.rooms else ROUTE
    classes = set(args.classes.split(','))
    conv = '%s@%s' % (TOOL_VERSION, args.commit)
    manifests = {c: [] for c in classes}
    rows = []
    jobs = [(r, a) for r in rooms for a in room_assets(src, r)]
    if not args.no_common:
        jobs += [('common', a) for a in core_assets(src)] + [('common', a) for a in ss_assets(src)]
    for room, (cls, name, loc, gb, gt, pbn, ptp) in jobs:
        if cls not in classes:
            continue
        d = lib / cls / room
        d.mkdir(parents=True, exist_ok=True)
        gc_le = po.to_le(gb, name)
        gm = po.GcModel(gb)
        rec = dict(room=room, name=name, cls=cls, locator=loc, gc_bin_sha256=sha(gb), gc_le_sha256=sha(gc_le),
                   gc_le_bytes=len(gc_le), gc_tpl_sha256=sha(gt), gc_sig=[gm.nv, gm.nn, gm.nd])
        psrc = '%s:%s' % ({'common': 'Core.dat' if loc['kind'] == 'CORE' else 'BIO4DAT.AFS'}.get(room, room + '.dat'), name)
        if pbn is None:
            rec.update(status='NONE', reason='no PS2 model with this id (PS2 deleted it)')
            rows.append(index_row(cls, room, name, 'NONE', 'GC kept (render cut: EFM_PS2_CUT)' if cls == 'breakables' else 'GC kept',
                                  conv, sha(gc_le), len(gc_le)))
            manifests[cls].append(rec)
            continue
        try:
            new, st = convert_geometry(gb, pbn)
        except ValueError as ex:
            rec.update(status='GC', reason='geometry: %s' % ex)
            rows.append(index_row(cls, room, name, psrc, 'GC kept (%s)' % ex, conv, sha(gc_le), len(gc_le)))
            manifests[cls].append(rec)
            continue
        le = po.to_le(new, name)
        geom = 'ps2'
        if len(le) > len(gc_le) and same_geometry(gb, pbn) and loc['kind'] != 'SS':
            # the PS2 mesh is the GC mesh (every triangle within 0.5 units, same UVs): the GC bytes are the PS2 geometry
            new, le, geom = gb, gc_le, 'gc-identical'
            st['out_tris'] = st['gc_tris']
        m = po.GcModel(new)
        drawn = [p for p in m.parts if p['tris']]
        used = sorted(set(p['hdr'][0x0C] for p in drawn))
        # ModelPart 0x0B flags: bit 2 = alpha texture at 0x0E (a material pair); bits 0 / 4 (bump 0x0D, specular
        # texture) are not handled: listed so a model that uses them is visible in the manifest
        pairs = sorted(set((p['hdr'][0x0C], p['hdr'][0x0E]) for p in drawn if p['hdr'][0x0B] & 4))
        other_tex = sorted(set(p['hdr'][0x0B] & 0x11 for p in drawn if p['hdr'][0x0B] & 0x11))
        swaps, kept, pair_list = convert_pictures(gt, ptp, used, d, name, pairs)
        (d / (name + '.bin')).write_bytes(le)
        rec.update(status='PS2', geometry=geom, out_sig=[m.nv, m.nn, m.nd], bin=name + '.bin', bin_sha256=sha(le), bin_bytes=len(le), fits=len(le) <= len(gc_le),
                   stats=st, used_images=used, swaps=swaps, kept_gc_images=kept, pairs=pair_list,
                   unhandled_material_flags=other_tex, ps2_bin_sha256=sha(pbn),
                   ps2_tpl_sha256=sha(ptp) if ptp else None)
        fmt = 'ModelData LE (GC layout, %s geometry%s)' % ('PS2' if geom == 'ps2' else 'PS2=GC identical', ', shift-%d' % st['shift_lowered'] if st['shift_lowered'] else '')
        rows.append(index_row(cls, room, name, psrc, fmt, conv, sha(le), len(le)))
        for s in swaps:
            if s.get('role') == 'mask':
                rows.append(index_row(cls, room, '%s/tex%d' % (name, s['j']),
                                      '%s/tpl%d' % (psrc, s['j']) if s['mask_source'] == 'ps2' else 'NONE',
                                      'mask identity (key %s; %dx%d%s)' % (s['key'], s['w'], s['h'],
                                                                           '' if s['mask_source'] == 'ps2' else '; GC mask resampled: no PS2 entry'),
                                      conv, s['key'], s['cmpr_bytes']))
                continue
            rows.append(index_row(cls, room, '%s/tex%d' % (name, s['j']), '%s/tpl%d' % (psrc, s['j']),
                                  're4tex %s (key %s; PS2 %dx%d)' % (s['alpha'], s['key'], s['w'], s['h']), conv, s['key'], s['cmpr_bytes']))
        for pr in pair_list:
            rows.append(index_row(cls, room, '%s/pair%d+%d' % (name, pr['color'], pr['mask']),
                                  '%s/tpl%d+tpl%d' % (psrc, pr['color'], pr['mask']),
                                  're4tex material pair (key %s = color %s + mask %s; %dx%d)' % (pr['key'], pr['color_key'], pr['mask_key'], pr['w'], pr['h']),
                                  conv, pr['key'], 0))
        for k in kept:
            rows.append(index_row(cls, room, '%s/tex%d' % (name, k['j']), 'NONE', 'GC TPL kept (%s)' % k['reason'], conv, '-', 0))
        (d / (name + '.json')).write_text(json.dumps(rec, indent=1))
        manifests[cls].append(rec)
        print('%-10s %-5s %-18s %-4s tris %s->%s bytes %s->%s%s pictures %d kept %d pairs %d%s' % (
            cls, room, name, rec['status'], st['gc_tris'], st['out_tris'], len(gc_le), len(le),
            '' if rec['fits'] else ' NOFIT', len(swaps), len(kept), len(pair_list),
            ' UNHANDLED-FLAGS %s' % other_tex if other_tex else ''))
    for c, lst in manifests.items():
        (lib / c).mkdir(parents=True, exist_ok=True)
        (lib / c / 'manifest.json').write_text(json.dumps(dict(tool=TOOL_VERSION, commit=args.commit, assets=lst), indent=1))
    idx = lib / 'INDEX.tsv'
    old = idx.read_text().splitlines() if idx.exists() else []
    keep = [l for l in old if not (l.split('\t')[-1:] == ['items'] and l.split('\t')[0] in classes)]
    idx.write_text('\n'.join(keep + rows) + '\n')
    print('rows', len(rows))


# ------------------------------------------------------------------------------------------ pack


def payload_of(dar):
    kind, size, dest, off = struct.unpack_from('<4I', dar, 0x20)
    if kind != 0 or off + size > len(dar):
        raise ValueError('first entry is not the payload')
    return bytearray(dar[off:off + size]), off


def ntr_records(pay):
    recs = {}
    for t, s, e in rs.tagged_entries(bytes(pay), '<'):
        if t == b'NTR\0':
            cnt = struct.unpack_from('<I', pay, s + 12)[0]
            for r in range(cnt):
                a, b, c = struct.unpack_from('<3I', pay, s + 32 + 12 * r)
                recs[a] = (b, c)
    return recs


class Packer:
    def __init__(self, pay, lib, report, recs=None):
        self.pay, self.lib, self.rep = pay, Path(lib), report
        self.recs = ntr_records(pay) if recs is None else recs

    def model(self, a, at, slot_end):
        """write the converted model of manifest asset a over the GC model at payload offset at."""
        gc_n = a['gc_le_bytes']
        cur = bytes(self.pay[at:at + gc_n])
        lib_bin = (self.lib / a['cls'] / a['room'] / a['bin']).read_bytes()
        if sha(lib_bin) != a['bin_sha256']:
            raise ValueError('%s: library file changed since the manifest' % a['name'])
        if bytes(self.pay[at:at + len(lib_bin)]) == lib_bin and not any(self.pay[at + len(lib_bin):slot_end]):
            return 'already'
        if sha(cur) != a['gc_le_sha256']:
            raise ValueError('%s: payload slot at %#x is not le_mirror(GC)' % (a['name'], at))
        if len(lib_bin) > slot_end - at:
            return 'nofit'
        self.pay[at:slot_end] = lib_bin + bytes(slot_end - at - len(lib_bin))
        return 'ps2'

    def pictures(self, a, tpl):
        """swap the TPL images of asset a in the LE TPL at payload offset tpl."""
        n, desc = struct.unpack_from('<2I', self.pay, tpl + 4)
        done = []
        for s in a.get('swaps', []):
            j = s['j']
            if j >= n:
                raise ValueError('%s: TPL has no image %d' % (a['name'], j))
            h, clut = struct.unpack_from('<2I', self.pay, tpl + desc + 8 * j)
            hh, ww, fmt, data = struct.unpack_from('<2H2I', self.pay, tpl + h)
            kc, kf = (int(x, 16) for x in s['key'].split('-'))
            at = tpl + data
            tex = (self.lib / a['cls'] / a['room'] / s['cmpr']).read_bytes()
            # an R4NREF record is a record even when no NTR row lists it (a graft or a later externalising set moved
            # the table; lane gcleft26 10-26: CMPR texels written over it would break the record)
            is_rec = at in self.recs or bytes(self.pay[at:at + 8]) == b'R4NREF\0\0'
            # a record already naming a PS2-catalogued key (census --catalog; e.g. r109 / r119 et10 efm 0f -> 4f784887,
            # PS2 r109.dat) is PS2 even when it is not the library's key: kept as it is
            if is_rec and '%08x-%08x' % struct.unpack_from('<2I', self.pay, at + 8) in PS2_KEYS:
                done.append('already')
                continue
            if (ww, hh, fmt) == (s['w'], s['h'], s['fmt']):
                if is_rec and struct.unpack_from('<2I', self.pay, at + 8) == (kc, kf):
                    done.append('already')
                    continue
                if not is_rec and bytes(self.pay[at:at + len(tex)]) == tex:
                    done.append('already')
                    continue
            if (ww, hh, fmt) != (s['gc']['w'], s['gc']['h'], s['gc']['fmt']):
                raise ValueError('%s image %d: payload header %dx%d f%d is not the GC source' % (a['name'], j, ww, hh, fmt))
            if fmt in (8, 9, 10) or clut:
                raise ValueError('%s image %d: indexed GC image (not handled)' % (a['name'], j))
            if is_rec:
                magic = bytes(self.pay[at:at + 8])
                if magic != b'R4NREF\0\0':
                    raise ValueError('%s image %d: record %r' % (a['name'], j, magic))
                chain = struct.unpack_from('<I', self.pay, at + 28)[0]
                struct.pack_into('<8s6I', self.pay, at, b'R4NREF\0\0', kc, kf, s['w'], s['h'], s['fmt'], chain)
                how = 'record'
            else:
                old = image_size(ww, hh, fmt)
                if len(tex) > old:
                    raise ValueError('%s image %d: PS2 CMPR %d B > GC span %d B' % (a['name'], j, len(tex), old))
                self.pay[at:at + old] = tex + bytes(old - len(tex))
                how = 'texels'
            struct.pack_into('<2HI', self.pay, tpl + h, s['h'], s['w'], s['fmt'])
            done.append(how)
        return done

    def asset(self, a, at, slot_end, tpl):
        if a['status'] != 'PS2':
            self.rep.append(dict(name=a['name'], result=a['status']))
            return
        g = self.model(a, at, slot_end)
        if g == 'nofit':
            self.rep.append(dict(name=a['name'], result='nofit', need=a['bin_bytes'], slot=slot_end - at))
            return
        p = self.pictures(a, tpl)
        self.rep.append(dict(name=a['name'], result=g, pictures=p))


def assets_for(lib, cls, room):
    m = Path(lib) / cls / 'manifest.json'
    if not m.exists():
        return []
    return [a for a in json.loads(m.read_text())['assets'] if a['room'] == room]


def pack_payload(pay, room, lib, classes, rep):
    P = Packer(pay, lib, rep)
    want = [a for c in classes for a in assets_for(lib, c, room)]
    by = {}
    for a in want:
        by.setdefault(a['locator']['kind'], []).append(a)
    ents = rs.tagged_entries(bytes(pay), '<')
    effk = 0
    for t, s, e in ents:
        tag = t.rstrip(b'\0').decode()
        if tag == 'ITM' and by.get('ITM'):
            b = bytes(pay[s:e])
            ids, bo, to, tabs = itm_tables(b, '<')
            end = spans(bo + to, list(tabs) + [len(b)])
            pos = {i: k for k, i in enumerate(ids)}
            nofit = []
            for a in by['ITM']:
                k = pos[a['locator']['id']]
                P.asset(a, s + bo[k], s + end[bo[k]], s + to[k])
                if rep[-1].get('result') == 'nofit':
                    nofit.append((a, k))
            if nofit:
                repack_itm(pay, s, e, lib, by['ITM'], rep)
        elif tag == 'EFF':
            mine = [a for a in by.get('EFF', []) if a['locator']['eff'] == effk]
            b = bytes(pay[s:e])
            efm = {i: (mo, to) for i, mo, to in eff_efm(b, '<')}
            for a in mine:
                mo, to = efm[a['locator']['id']]
                P.asset(a, s + mo, s + to, s + to)
            effk += 1
        elif tag == 'ETM' and by.get('ETM'):
            for nm, s2, e2 in po.etm_entries(bytes(pay[s:e]), '<'):
                base = s + s2 + 0x40
                mine = [a for a in by['ETM'] if a['locator']['member'] == nm]
                if not mine:
                    continue
                efm = {i: (mo, to) for i, mo, to in eff_efm(bytes(pay[base:s + e2]), '<')}
                for a in mine:
                    mo, to = efm[a['locator']['id']]
                    P.asset(a, base + mo, base + to, base + to)
    return P


def repack_itm(pay, s, e, lib, assets, rep):
    """an ITM model that does not fit its slot: lay every BIN of the pack out again inside the pack's BIN region
    (the BINs are contiguous; TPLs and tables stay where they are), PS2 bytes for converted ids, the payload's
    current bytes otherwise; then the offset table. The pack's size and every TPL offset are unchanged."""
    b = bytes(pay[s:e])
    ids, bo, to, (oi, ob, ot) = itm_tables(b, '<')
    end = spans(bo + to, [oi, ob, ot, len(b)])
    lo, hi = min(bo), max(end[x] for x in bo)
    if any(lo <= x < hi for x in to + [oi, ob, ot]):
        raise ValueError('ITM BIN region is not contiguous')
    byid = {a['locator']['id']: a for a in assets if a['status'] == 'PS2'}
    order = sorted(range(len(ids)), key=lambda k: bo[k])
    region, new_off = bytearray(), {}
    for k in order:
        a = byid.get(ids[k])
        if a and sha(b[bo[k]:bo[k] + a['gc_le_bytes']]) == a['gc_le_sha256']:
            body = (Path(lib) / a['cls'] / a['room'] / a['bin']).read_bytes()
        else:
            body = b[bo[k]:end[bo[k]]]
        region += bytes(po.al(len(region)) - len(region))
        new_off[k] = lo + len(region)
        region += body
    if len(region) > hi - lo:
        raise ValueError('ITM BIN region overflow: %d > %d' % (len(region), hi - lo))
    pay[s + lo:s + hi] = region + bytes(hi - lo - len(region))
    for k in range(len(ids)):
        struct.pack_into('<I', pay, s + ob + 4 + 4 * k, new_off[k] - ob)
    for r in rep:
        if r.get('result') == 'nofit':
            r['result'] = 'ps2 (ITM repacked)'
    # pictures of the repacked ones
    P = Packer(pay, lib, [])
    for k in range(len(ids)):
        a = byid.get(ids[k])
        if a:
            P.pictures(a, s + to[k])
    rep.append(dict(itm_repack=dict(region=hi - lo, used=len(region))))


def pack(args):
    dar = Path(args.dar).read_bytes()
    pay, off = payload_of(dar)
    before = bytes(pay)
    rep = []
    pack_payload(pay, args.room, args.lib, args.classes.split(','), rep)
    if len(pay) != len(before):
        raise AssertionError('payload size changed')
    out = bytearray(dar)
    out[off:off + len(pay)] = pay
    Path(args.out).write_bytes(bytes(out))
    res = dict(room=args.room, dar_in=args.dar, dar_in_sha256=sha(dar), dar_out=args.out, dar_out_sha256=sha(bytes(out)),
               changed_bytes=sum(1 for x, y in zip(before, pay) if x != y), assets=rep, tool_sha256=sha(Path(__file__).read_bytes()))
    if args.json:
        Path(args.json).write_text(json.dumps(res, indent=1))
    summary = {}
    for r in rep:
        if 'result' in r:
            summary[r['result']] = summary.get(r['result'], 0) + 1
    print(args.room, 'changed', res['changed_bytes'], summary, res['dar_out_sha256'][:16])
    bad = [r for r in rep if r.get('result') == 'nofit']
    return 1 if bad else 0


def pack_core(args):
    dar = Path(args.das).read_bytes()
    pay, off = payload_of(dar)
    before = bytes(pay)
    rep = []
    P = Packer(pay, args.lib, rep)
    want = [a for a in assets_for(args.lib, 'breakables', 'common') if a['locator']['kind'] == 'CORE']
    ents = rs.tagged_entries(bytes(pay), '<')
    for a in want:
        t, s, e = ents[a['locator']['entry']]
        if t.rstrip(b'\0') != b'EFF':
            raise ValueError('core entry %d is %r' % (a['locator']['entry'], t))
        efm = {i: (mo, to) for i, mo, to in eff_efm(bytes(pay[s:e]), '<')}
        mo, to = efm[a['locator']['id']]
        P.asset(a, s + mo, s + to, s + to)
    out = bytearray(dar)
    out[off:off + len(pay)] = pay
    Path(args.out).write_bytes(bytes(out))
    print('core changed', sum(1 for x, y in zip(before, pay) if x != y), rep)


def pack_ss(args):
    """SS/cmn pick-up zoom models are standalone files: the PS2 model replaces the .bin; the .tpl's swapped images
    get the PS2 CMPR texels (resident TPL, runtime-hashed)."""
    src, out = Path(args.src), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for a in assets_for(args.lib, 'items', 'common'):
        if a['locator']['kind'] != 'SS' or a['status'] != 'PS2':
            print(a['name'], a['status'])
            continue
        stem = a['locator']['file'].split('/')[-1]
        cur = (src / (stem + '.bin')).read_bytes()
        if sha(cur) != a['gc_le_sha256']:
            print(a['name'], 'source .bin is not le_mirror(GC): skipped')
            continue
        (out / (stem + '.bin')).write_bytes((Path(args.lib) / 'items' / 'common' / a['bin']).read_bytes())
        tpl = bytearray((src / (stem + '.tpl')).read_bytes())
        P = Packer(tpl, args.lib, [], recs={})
        p = P.pictures(a, 0)
        (out / (stem + '.tpl')).write_bytes(bytes(tpl))
        print(a['name'], 'ps2', p)


def census(args):
    if args.catalog:   # GC-ASSET catalog (gc_port23/make_catalog.sh): texture keys whose provenance is ps2
        PS2_KEYS.update(e['id'] for e in json.loads(Path(args.catalog).read_text())['entries']
                        if e['kind'] == 'texture' and e['provenance'] == 'ps2')
    dar = Path(args.dar).read_bytes()
    pay, off = payload_of(dar)
    rows = []
    for cls in args.classes.split(','):
        for a in assets_for(args.lib, cls, args.room):
            rows.append(a)
    # reuse pack's slot walk on a copy and read the results without writing
    rep = []
    probe = bytearray(pay)
    try:
        pack_payload(probe, args.room, args.lib, args.classes.split(','), rep)
    except ValueError as ex:
        print('census: GC slot check failed: %s' % ex)
        return 1
    res = {'PS2': 0, 'GC': 0, 'NONE': 0}
    for r in rep:
        if 'result' not in r:
            continue
        k = {'already': 'PS2', 'NONE': 'NONE'}.get(r['result'], 'GC')
        if r['result'] == 'already' and any(p != 'already' for p in r.get('pictures', [])):
            k = 'GC'
        res[k] += 1
        if k == 'GC':
            print('census GC', args.room, r)
    print('items census: room=%s ps2=%d gc=%d none=%d' % (args.room, res['PS2'], res['GC'], res['NONE']))
    return 1 if res['GC'] else 0


def ntr_check(pay):
    """room/texture_package.cpp SourceIdentityTable::adopt's checks over every NTR row -> list of problems."""
    bad = []
    n = len(pay)
    for t, s, e in rs.tagged_entries(bytes(pay), '<'):
        if t != b'NTR\0':
            continue
        magic, ver, cnt, row, crc, w24, w28 = struct.unpack_from('<8s6I', pay, s)
        if magic != b'R4NTBL\0\0' or ver != 1 or row != 12 or w28 != n or w24 <= n or \
                zlib.crc32(bytes(pay[s + 32:s + 32 + 12 * cnt])) & 0xffffffff != crc:
            bad.append('NTR header')
        for r in range(cnt):
            rec, hdr, tpl = struct.unpack_from('<3I', pay, s + 32 + 12 * r)
            p_ = bytes(pay[rec:rec + 64])
            w, ht, fmt = struct.unpack_from('<3I', p_, 16)
            indexed = p_[:8] == b'R4PREF\0\0'
            hh, ww = struct.unpack_from('<2H', pay, hdr)
            hfmt, hdata = struct.unpack_from('<2I', pay, hdr + 4)
            ok = (indexed or (p_[:8] == b'R4NREF\0\0' and (fmt <= 6 or fmt == 14))) and w and ht and w <= 1024 and \
                ht <= 1024 and not pay[hdr + 33] and not (pay[hdr + 34] and indexed) and not pay[hdr + 35] and \
                w == ww and ht == hh and fmt == hfmt and tpl + hdata == rec
            if not ok:
                bad.append('row %d rec %#x' % (r, rec))
    return bad


def verify(args):
    pay, off = payload_of(Path(args.dar).read_bytes())
    bad = ntr_check(pay)
    print('ntr', 'OK' if not bad else bad[:10])
    return 1 if bad else 0


def gate(args):
    """Record a gate result in INDEX.tsv's gate column for lane items' rows of the given rooms (metadata only: the
    converted outputs and every other lane's rows are untouched)."""
    idx = Path(args.lib) / 'INDEX.tsv'
    rooms = set(args.rooms.split(','))
    classes = set(args.classes.split(','))
    assert re.match(r'^(PASS|FAIL):\S+$', args.result), args.result
    out, n = [], 0
    for l in idx.read_text().splitlines():
        f = l.split('\t')
        if len(f) == 10 and f[9] == 'items' and f[0] in classes and f[1] in rooms:
            f[8] = args.result
            n += 1
            l = '\t'.join(f)
        out.append(l)
    idx.write_text('\n'.join(out) + '\n')
    print('gate %s: %d rows (%s)' % (args.result, n, ','.join(sorted(rooms))))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    a = sp.add_parser('convert'); a.add_argument('--lib', required=True); a.add_argument('--rooms')
    a.add_argument('--classes', default='items,breakables'); a.add_argument('--commit', default='local')
    a.add_argument('--no-common', action='store_true')
    a = sp.add_parser('pack'); a.add_argument('--dar', required=True); a.add_argument('--room', required=True)
    a.add_argument('--lib', required=True); a.add_argument('--out', required=True); a.add_argument('--json')
    a.add_argument('--classes', default='items,breakables')
    a = sp.add_parser('pack-core'); a.add_argument('--das', required=True); a.add_argument('--lib', required=True)
    a.add_argument('--out', required=True)
    a = sp.add_parser('pack-ss'); a.add_argument('--src', required=True); a.add_argument('--lib', required=True)
    a.add_argument('--out', required=True)
    a = sp.add_parser('verify'); a.add_argument('--dar', required=True)
    a = sp.add_parser('census'); a.add_argument('--dar', required=True); a.add_argument('--room', required=True)
    a.add_argument('--lib', required=True); a.add_argument('--classes', default='items,breakables')
    a.add_argument('--catalog', help='GC-ASSET catalog.json: a picture record naming any PS2-provenance key counts as PS2')
    a = sp.add_parser('gate'); a.add_argument('--lib', required=True); a.add_argument('--rooms', required=True)
    a.add_argument('--result', required=True, help='PASS:<run> or FAIL:<run>'); a.add_argument('--classes', default='items,breakables')
    args = ap.parse_args()
    sys.exit({'convert': convert, 'pack': pack, 'pack-core': pack_core, 'pack-ss': pack_ss, 'census': census, 'verify': verify,
              'gate': gate}[args.cmd](args) or 0)


if __name__ == '__main__':
    main()
