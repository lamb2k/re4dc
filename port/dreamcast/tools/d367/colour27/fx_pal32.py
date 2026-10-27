#!/usr/bin/env python3
"""fx_pal32.py (colour27, 2026-10-27): PS2 effect packages with ARGB8888 palettes, for game TEX_PAL32=1.

The effect packages of ps2lib/effects-tex (fx_ps2_pack.py) store their 16 palette colours as ARGB4444 words made by
truncation (convert_tpl._pack_4444): every PS2 CLUT channel loses its low 4 bits and values below 16 become 0, so
faint smoke / glow texels ship fully transparent (colour27 audit: 11 % of the visible texels of the PS2 effects).
This tool rebuilds such a package with the same indices and the same 16 colours at full 8 bits:

  * it re-derives each package's 8-bit palette from the PS2 EFF it came from (fx_ps2_pack.ps2_eff_textures +
    palette16, the converter's own code) and proves the match: the converter's ARGB4444 words of that palette must
    equal the package's palette words, and its nearest-colour indices of one of the id's frames must equal the
    package's indices exactly (a package that matches no PS2 picture is left out and listed);
  * it writes the package with the texture flag kPalette8888 (bit 3) and a 64-byte ARGB8888 tail (room/
    texture_package.hpp); name, key, size, indices and every other field stay the same, so the key binds as before.

Mipmapped packages (TEX_PAL4_MIPMAP chains) keep their chain: only the palette tail changes.
usage: fx_pal32.py <PS2 .dat>... --lib <effects-tex dir with .re4tex> --out <dir> [--report out.json]
Private inputs and outputs (game assets): never commit them.
"""
import argparse, collections, json, struct, sys, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / 'test12fx'), str(HERE.parent), str(HERE.parent.parent)]
import convert_tpl as C  # noqa: E402
import fx_ps2_pack as F  # noqa: E402

PAL32 = 1 << 3


def ps2_candidates(dat_paths):
    """{palette words (16-tuple): [(source, id, palette, [frames px])]} for every PSMT4/8 effect id."""
    out = collections.defaultdict(list)
    for path in dat_paths:
        blob = Path(path).read_bytes()
        try:
            entries = F.dat_entries(blob)
        except (struct.error, IndexError, UnicodeDecodeError):
            continue                       # not a .dat container (empty or another layout)
        for k, (ty, s0, s1) in enumerate(entries):
            if ty != 'EFF':
                continue
            try:
                effs = F.ps2_eff_textures(blob[s0:s1])
            except (ValueError, IndexError, struct.error):
                continue
            for tid, pics in effs.items():
                if not pics or any(p is None for p in pics):
                    continue
                weights = collections.Counter(c for _, _, px in pics for c in px)
                pal = F.palette16(dict(weights))
                words = tuple([C._pack_4444(c) for c in pal] + [0] * (16 - len(pal)))
                out[words].append(('%s:%d' % (Path(path).name, k), tid, pal, pics))
    return out


def indices_for(pal, w, h, px):
    pp = [F.premul(c) for c in pal]
    cache = {}

    def nearest(c):
        if c not in cache:
            p = F.premul(c)
            cache[c] = min(range(len(pp)), key=lambda k: sum((x - y) ** 2 for x, y in zip(p, pp[k])))
        return cache[c]
    idx = C.twiddle_16bpp([nearest(c) for c in px], w, h)
    return bytes(idx[i] | idx[i + 1] << 4 for i in range(0, len(idx), 2))


def rebuild(blob, pal):
    h = list(C.HEADER.unpack_from(blob))
    t = list(C.TEXTURE.unpack_from(blob, h[5]))
    off, size = t[4], t[5]
    payload = blob[off:off + size - 32]
    words = [(a << 24) | (r << 16) | (g << 8) | b for r, g, b, a in pal] + [0] * (16 - len(pal))
    payload += struct.pack('<16I', *words)
    t[5], t[6] = len(payload), t[6] | PAL32
    desc = C.TEXTURE.pack(*t)
    body = desc + payload
    h[7], h[8] = len(payload), zlib.crc32(body) & 0xffffffff
    return C.HEADER.pack(*h) + body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dats', nargs='+')
    ap.add_argument('--lib', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--report', type=Path)
    a = ap.parse_args()
    cands = ps2_candidates(a.dats)
    a.out.mkdir(parents=True, exist_ok=True)
    done, skipped = [], []
    for p in sorted(a.lib.rglob('*.re4tex')):
        blob = p.read_bytes()
        h = C.HEADER.unpack_from(blob)
        t = C.TEXTURE.unpack_from(blob, h[5])
        if h[4] != 1 or t[3] != C.FORMAT_PAL4_ARGB4444 or t[6] & PAL32:
            skipped.append((p.name, 'not a single PAL4 ARGB4444 package')); continue
        w, hh, off, size, flags = t[1], t[2], t[4], t[5], t[6]
        words = struct.unpack_from('<16H', blob, off + size - 32)
        base = blob[off + size - 32 - w * hh // 2:off + size - 32]   # base level indices (last before the palette)
        match = None
        for src, tid, pal, pics in cands.get(tuple(words), []):
            for fw, fh, px in pics:
                if (fw, fh) == (w, hh) and indices_for(pal, w, hh, px) == base:
                    match = (src, tid, pal); break
            if match:
                break
        if not match:
            skipped.append((p.name, 'no PS2 picture reproduces it')); continue
        out = rebuild(blob, match[2])
        (a.out / p.name).write_bytes(out)
        done.append(dict(key=p.stem, source=match[0], id=match[1], width=w, height=hh, mip=bool(flags & 4),
                         bytes_before=len(blob), bytes_after=len(out)))
    rep = dict(converted=len(done), skipped=len(skipped), packages=done, skipped_list=skipped,
               extra_vram_bytes=32 * len(done))
    if a.report:
        a.report.write_text(json.dumps(rep, indent=1))
    print('fx_pal32: %d packages rebuilt with ARGB8888 palettes, %d left as they are' % (len(done), len(skipped)))


if __name__ == '__main__':
    main()
