#!/usr/bin/env python3
"""tr_classify.py: offline transparency class of every PS2 world part (lane trans17, 2026-10-17).

TRANSPARENCY-PLAN-20261017.md section 4.1. For each room directory holding ps2-world.re4mesh + ps2-world.r4pw it
decodes the SHIPPED texture of every part (level 0, the alpha the console samples: RGB565, ARGB1555, ARGB4444, PAL4,
twiddled or VQ) and writes:

  <out>/<room>/ps2-world.r4tc   the runtime sidecar read by native_static.cpp trans:: (TRANS_POLICY), bound to the
                                R4PW body crc; the R4PW, the mesh and every existing CRC pin stay unchanged;
  <out>/TRCLASS.tsv             one row per part (room, part, key, pass, class, tier, alpha statistics, strip bytes).

Sidecar layout (little endian): "R4TC", u32 version=1, u32 classifier=CLASSIFIER, u32 parts, u32 r4pw_crc (R4PW
header crc = zlib.crc32 of its body), u32 body_crc (zlib.crc32 of the class bytes), then one class byte per R4PW part,
zero padded to a multiple of 4.

Class bytes (must match native_static.cpp trans::):
  0 UNKNOWN (no texture found: drawn as today)  1 OP  2 PT_BIN  3 OPAQUE_IN_TR  4 FLAT (uniform 14/15)
  5 FLATMID (uniform mid alpha, glass)  6 CARD_NEAR  7 CARD_SOFTA  8 SOFT (B/C, BINLOW)  9 VA (vertex alpha)
  10 DROP (alpha 0 in every texel)

Deterministic: same inputs, byte-identical outputs (sorted rooms, no timestamps). --check compares instead of writing.
Texture lookup: --tex DIR (any *.re4tex below it, named <crc>-<fnv>.re4tex; repeatable) and --pak FILE|DIR
(RE4PAK1 packs; repeatable). The first source that has a key wins, in argument order.

--mip-aware-alpha opts into bounded base-level reading for native 16-bit VQ,
twiddled and nonmip linear packages. It rejects unsupported layouts/formats
(including PAL), bad extents and unknown CRC conventions as UNKNOWN. Default
behavior is unchanged; this option does not change tex_class/part_class rules
or establish compatibility with previously generated R4TC class bytes.
"""
import argparse
import collections
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ps2world'))
import packages as F  # noqa: E402

CLASSIFIER = 1
NAMES = ['UNKNOWN', 'OP', 'PT_BIN', 'OPAQUE_IN_TR', 'FLAT', 'FLATMID', 'CARD_NEAR', 'CARD_SOFTA', 'SOFT', 'VA', 'DROP']
CODE = {n: i for i, n in enumerate(NAMES)}
# Tier of the policy action on the class (plan section 5); '-' = no policy action.
TIER = {'UNKNOWN': 'unclassified', 'OP': '-', 'PT_BIN': '-', 'OPAQUE_IN_TR': '1', 'FLAT': '2', 'FLATMID': '-',
        'CARD_NEAR': '2', 'CARD_SOFTA': '2/3', 'SOFT': 'far-only', 'VA': '2', 'DROP': '1'}
TEX_TO_CLASS = {'OPAQUE': 'OPAQUE_IN_TR', 'FLAT': 'FLAT', 'FLATMID': 'FLATMID', 'BIN': 'CARD_NEAR',
                'NEARBIN': 'CARD_NEAR', 'SOFTA': 'CARD_SOFTA', 'SOFTB': 'SOFT', 'SOFTC': 'SOFT', 'BINLOW': 'SOFT',
                'ALL0': 'DROP', 'NOTEX': 'UNKNOWN'}


def native_base_alpha(blob):
    """Opt-in native16 base histogram; unsupported/invalid input returns None.

    Layouts match texture_package.cpp and mipmap_{vq,twiddled}.py: full VQ
    codebook followed by levels 1x1..base; twiddled16 has six prefix bytes
    followed by levels 1x1..base. Histograms need no Morton permutation.
    Legacy payload-only CRC input is accepted, as in the existing offline
    mip readers; this function is not a strict runtime Package admission gate.
    """
    if not blob or len(blob) < 144:
        return None
    head = struct.unpack_from('<8s10I', blob)
    if (head[:6] != (b'RE4DCTX\0', 2, 48, 96, 1, 48) or
            head[6] != 144 or head[6] + head[7] != len(blob)):
        return None
    _, w, h, fmt, off, size, flags, pay, reserved = struct.unpack_from('<64s8I', blob, 48)
    if (not (8 <= w <= 1024 and 8 <= h <= 1024) or
            w & (w - 1) or h & (h - 1) or fmt not in (0, 1, 2) or
            pay not in (0, 1, 2) or flags & ~7 or reserved or
            off != 144 or size != head[7]):
        return None
    mip = bool(flags & 4)
    if mip and (w != h or pay == 0):
        return None
    pixels = w * h
    if pay == 2:
        indices = pixels // 4
        if mip:
            indices, side = 1, 2
            while side <= w:
                indices += side * side // 4
                side *= 2
        expected = 2048 + indices
        start = expected - pixels // 4
    else:
        expected = (pixels * 4 // 3 + 3) * 2 if mip else pixels * 2
        start = expected - pixels * 2
    if size != expected:
        return None
    payload = blob[off:]
    if head[8] not in (zlib.crc32(blob[48:]) & 0xffffffff,
                       zlib.crc32(payload) & 0xffffffff):
        return None
    if fmt == 0:
        return ({15: pixels}, 15)
    shift, mask = (15, 1) if fmt == 1 else (12, 15)
    levels = collections.Counter()
    if pay == 2:
        book = struct.unpack_from('<1024H', payload)
        for index, count in collections.Counter(payload[start:]).items():
            for corner in range(4):
                levels[(book[index * 4 + corner] >> shift) & mask] += count
    else:
        for word, in struct.iter_unpack('<H', payload[start:]):
            levels[(word >> shift) & mask] += 1
    return (dict(levels), 1 if fmt == 1 else 15)


class Textures:
    def __init__(self, tex_dirs, paks, *, mip_aware_alpha=False):
        self.mip_aware_alpha = mip_aware_alpha
        self.sources = []
        for d in tex_dirs:
            idx = {}
            for root, dirs, files in os.walk(d):
                dirs.sort()
                for f in sorted(files):
                    if f.endswith('.re4tex'):
                        idx.setdefault(f[:-7], os.path.join(root, f))
            self.sources.append(('dir', idx))
        for p in paks:
            files = [p] if os.path.isfile(p) else sorted(
                os.path.join(r, f) for r, ds, fs in os.walk(p) for f in fs if f.endswith('.pak'))
            for f in files:
                with open(f, 'rb') as fh:
                    head = fh.read(28)
                    if head[:8] != b'RE4PAK1\0':
                        continue
                    ver, n, ix, data, crc = struct.unpack_from('<5I', head, 8)
                    fh.seek(ix)
                    tab = fh.read(16 * n)
                idx = {}
                for i in range(n):
                    a, b, o, s = struct.unpack_from('<4I', tab, 16 * i)
                    idx.setdefault('%08x-%08x' % (a, b), (o, s))
                self.sources.append(('pak', (f, idx)))
        self.cache = {}

    def blob(self, key):
        for kind, src in self.sources:
            if kind == 'dir' and key in src:
                with open(src[key], 'rb') as fh:
                    return fh.read()
            if kind == 'pak' and key in src[1]:
                o, s = src[1][key]
                with open(src[0], 'rb') as fh:
                    fh.seek(o)
                    return fh.read(s)
        return None

    def alpha(self, key):
        """Level-0 texel alpha histogram {level: texels}, mx (top level), or None."""
        if key in self.cache:
            return self.cache[key]
        b = self.blob(key)
        if self.mip_aware_alpha:
            r = native_base_alpha(b)
            self.cache[key] = r
            return r
        r = None
        if b and b[:8] == b'RE4DCTX\0':
            head = struct.unpack_from('<8s10I', b)
            w, h, fmt, off, size, flags, pay, res = struct.unpack_from('<64s8I', b, head[5])[1:9]
            p = b[off:off + size]
            lv = collections.Counter()
            try:
                if fmt == 0:
                    lv[15] = w * h
                elif fmt in (1, 2):
                    shift, mask = (15, 1) if fmt == 1 else (12, 15)
                    if pay == 2:  # VQ: 256 x 4 texel codebook, then one index per 2x2
                        cb = struct.unpack_from('<1024H', p, 0)
                        for e, c in collections.Counter(p[2048:2048 + (w // 2) * (h // 2)]).items():
                            for k in range(4):
                                lv[(cb[e * 4 + k] >> shift) & mask] += c
                    else:
                        for v in struct.unpack_from('<%dH' % (w * h), p, 0):
                            lv[(v >> shift) & mask] += 1
                elif fmt in (3, 4):
                    pal = struct.unpack_from('<16H', p, len(p) - 32)
                    shift, mask = (12, 15) if fmt == 4 else (15, 1)
                    cnt = collections.Counter()
                    for byte in p[:(w * h) // 2]:
                        cnt[byte & 15] += 1
                        cnt[byte >> 4] += 1
                    for ix, c in cnt.items():
                        lv[(pal[ix] >> shift) & mask] += c
                else:
                    lv = None
            except struct.error:
                lv = None
            if lv is not None:
                r = (dict(lv), 15 if fmt in (0, 2, 4) else 1)
        self.cache[key] = r
        return r


def stats(lv, mx):
    n = sum(lv.values())
    nzn = sum(v for k, v in lv.items() if k > 0)
    err = sum(v * abs(k / mx - (1.0 if k / mx >= 0.5 else 0.0)) for k, v in lv.items() if k > 0)
    mid = sum(v for k, v in lv.items() if 0.2 <= k / mx <= 0.8)
    return dict(zero=1 - nzn / n if n else 0.0, err=(err / nzn) if nzn else 0.0, mid=(mid / nzn) if nzn else 0.0)


def tex_class(a):
    """Same rules as the plan's census (trcensus.py classify_tex)."""
    if a is None:
        return 'NOTEX'
    lv, mx = a
    nz = sorted(k for k, v in lv.items() if k > 0 and v)
    zeros = lv.get(0, 0)
    if not nz:
        return 'ALL0'
    top = mx - 1 if mx > 1 else 1
    if zeros == 0 and nz == [mx]:
        return 'OPAQUE'
    if zeros == 0 and len(nz) == 1:
        return 'FLAT' if nz[0] >= top else 'FLATMID'
    if all(k >= top for k in nz):
        return 'BIN' if zeros else 'OPAQUE'
    if zeros and len(nz) == 1:
        return 'BINLOW'
    e = stats(lv, mx)['err']
    return 'NEARBIN' if e <= 0.08 else 'SOFTA' if e <= 0.15 else 'SOFTB' if e <= 0.25 else 'SOFTC'


def part_class(pas, va, tcls):
    if pas == 0:
        return 'OP'
    if pas == 1:
        return 'PT_BIN'
    if va:
        return 'VA'
    return TEX_TO_CLASS[tcls]


def classify_room(room, rdir, tex):
    mesh_path = os.path.join(rdir, 'ps2-world.re4mesh')
    with open(mesh_path, 'rb') as fh:
        mesh = F.read(fh.read())
    h, meta, places = F.side_read(os.path.join(rdir, 'ps2-world.r4pw'), mesh)
    npl = collections.Counter(p[0] for p in places)
    part_mesh = {}
    for mi, m in enumerate(mesh['meshes']):
        for pi in range(m[6], m[6] + m[7]):
            part_mesh[pi] = mi
    classes = bytearray()
    rows = []
    for pi, md in enumerate(meta):
        crc, fnv, w, hh, pas, cull, texi, resv = md
        key = '%08x-%08x' % (crc, fnv)
        va = bool(resv & 1)
        a = tex.alpha(key) if pas == 2 else None
        tcls = tex_class(a) if pas == 2 else '-'
        cls = part_class(pas, va, tcls)
        classes.append(CODE[cls])
        part = mesh['parts'][pi]
        sv = 0
        for li in range(part[6], part[6] + part[7]):
            for s in F.let_corners(mesh, mesh['lets'][li])[1]:
                sv += len(s)
        st = stats(*a) if a else None
        bound = ''
        if cls == 'FLAT' and a:
            lvl = max(k for k in a[0] if k > 0)
            bound = '%d' % round((1 - lvl / a[1]) * 255)  # max per-channel change in /255 (plan section 5 Tier 2)
        rows.append([room, str(pi), key, str(pas), '1' if va else '0', tcls, cls, TIER[cls],
                     '%.3f' % st['zero'] if st else '', '%.3f' % st['err'] if st else '',
                     '%.3f' % st['mid'] if st else '', bound, str(sv * 32 * npl.get(part_mesh.get(pi, -1), 0))])
    body = bytes(classes) + b'\0' * ((-len(classes)) % 4)
    head = struct.pack('<4s5I', b'R4TC', 1, CLASSIFIER, len(meta), h[5], zlib.crc32(bytes(classes)) & 0xffffffff)
    # runtime checks crc32 over exactly `parts` bytes (not the padding)
    return head + body, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('rooms', nargs='+', help='room directories (named rXXX) holding ps2-world.re4mesh + ps2-world.r4pw')
    ap.add_argument('--tex', action='append', default=[], help='directory of <key>.re4tex files (repeatable)')
    ap.add_argument('--pak', action='append', default=[], help='RE4PAK1 pack file or directory of .pak (repeatable)')
    ap.add_argument('--out', required=True, help='output root: <out>/<room>/ps2-world.r4tc and <out>/TRCLASS.tsv')
    ap.add_argument('--check', action='store_true', help='compare with existing outputs, write nothing')
    ap.add_argument('--strict', action='store_true', help='exit 1 if any TR part is UNKNOWN (coverage gate)')
    ap.add_argument('--mip-aware-alpha', action='store_true',
                    help='opt-in bounded native16 base histogram; unsupported input is UNKNOWN')
    a = ap.parse_args()
    tex = Textures(a.tex, a.pak, mip_aware_alpha=a.mip_aware_alpha)
    allrows = []
    unknown = 0
    status = 0
    for rdir in sorted(a.rooms, key=lambda d: os.path.basename(os.path.normpath(d))):
        room = os.path.basename(os.path.normpath(rdir))
        side, rows = classify_room(room, rdir, tex)
        allrows += rows
        cnt = collections.Counter(r[6] for r in rows if r[3] == '2')
        unknown += cnt.get('UNKNOWN', 0)
        dst = os.path.join(a.out, room, 'ps2-world.r4tc')
        if a.check:
            same = os.path.exists(dst) and open(dst, 'rb').read() == side
            status |= 0 if same else 1
            print('%s %s' % (room, 'same' if same else 'DIFFERS'))
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as fh:
                fh.write(side)
        print('%s parts=%d tr=%s sha=%08x' % (room, len(rows), ' '.join('%s:%d' % kv for kv in sorted(cnt.items())),
                                             zlib.crc32(side) & 0xffffffff))
    # the disc index (dc/native/trclass.idx): rooms that carry a sidecar, so the runtime opens no file elsewhere
    rooms_hex = sorted({int(r[0][1:], 16) for r in allrows})
    idx = struct.pack('<4sI', b'R4TI', len(rooms_hex)) + b''.join(struct.pack('<H', r) for r in rooms_hex)
    ip = os.path.join(a.out, 'trclass.idx')
    if a.check:
        same = os.path.exists(ip) and open(ip, 'rb').read() == idx
        status |= 0 if same else 1
        print('trclass.idx %s' % ('same' if same else 'DIFFERS'))
    else:
        with open(ip, 'wb') as fh:
            fh.write(idx)
    tsv = 'room\tpart\tkey\tpass\tva\ttex_class\tclass\ttier\tzero\terr\tmid\tbound255\tstrip_bytes_placed\n'
    tsv += ''.join('\t'.join(r) + '\n' for r in allrows)
    tp = os.path.join(a.out, 'TRCLASS.tsv')
    if a.check:
        same = os.path.exists(tp) and open(tp, encoding='ascii').read() == tsv
        status |= 0 if same else 1
        print('TRCLASS.tsv %s' % ('same' if same else 'DIFFERS'))
    else:
        with open(tp, 'w', encoding='ascii', newline='\n') as fh:
            fh.write(tsv)
    if unknown:
        print('UNKNOWN TR parts: %d (no shipped texture found; drawn as today)' % unknown)
        if a.strict:
            status |= 1
    return status


if __name__ == '__main__':
    sys.exit(main())
