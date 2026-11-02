#!/usr/bin/env python3
"""dcform_pak.py --pak base/tex.pak --out DIR [--material-prefix 'PS2 r' ...] [--keys loaded.txt] [--jobs N]
(lane assets-dc, 2026-11-02; batch 2/3 of the retroactive asset pass: every picture in Dreamcast form)

Re-encodes selected dc/tex.pak packages in place (same key, same material name, same dimensions and pixel format):
  - raw 16-bit twiddled, >= 64x64      -> full-codebook VQ (pvrtex -c), with mips when square (pvrtex -m);
  - raw 16-bit twiddled, smaller square -> 16-bit twiddled + mips (mipmap_twiddled, base texels unchanged);
  - VQ square without mips              -> VQ + mips (mipmap_vq, base codebook/indices unchanged);
  - PAL4+alpha square without mips      -> PAL4 + mips (mipmap_pal4).
Non-square pictures cannot carry PVR mips; raw non-square >= 64 px becomes VQ without mips. Everything else is left.
Runtime knobs needed (all already ON in the release recipe): CAST_MIPMAP TEX_TWIDDLED_MIPMAP TEX_PAL4_MIPMAP.
Outputs <out>/dc/tex.pak, <out>/pak-derived.json (changed keys), <out>/report.json (per key: how, bytes before/after,
PSNR of the VQ re-encode against the original 16-bit pixels).
"""
import argparse, hashlib, json, math, os, subprocess, sys, tempfile, zlib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
T = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(T), str(T / 'd367'), str(T / 'd367' / 'vram')]
import convert_tpl as tpl          # noqa: E402
import vq_native_ui as vqn         # noqa: E402
import mipmap_vq, mipmap_twiddled, mipmap_pal4  # noqa: E402
import texpack                     # noqa: E402
from vq_pak import read_pak        # noqa: E402

PVRTEX = vqn.PVRTEX
RAW = (tpl.FORMAT_RGB565, tpl.FORMAT_ARGB1555, tpl.FORMAT_ARGB4444)


def info(pkg):
    h = tpl.HEADER.unpack_from(pkg)
    t = tpl.TEXTURE.unpack_from(pkg, h[5])
    return h, t


def restamp_keep(old, new, add_flags):
    """New payload under the old package's material name and flags (| add_flags); canonical runtime CRC."""
    sh, nh = list(tpl.HEADER.unpack_from(old)), list(tpl.HEADER.unpack_from(new))
    st, nt = list(tpl.TEXTURE.unpack_from(old, sh[5])), list(tpl.TEXTURE.unpack_from(new, nh[5]))
    nt[0], nt[6] = st[0], st[6] | add_flags
    body = tpl.TEXTURE.pack(*nt) + new[nh[6]:]
    nh[8] = zlib.crc32(body) & 0xffffffff
    # the runtime's canonical rule (convert_tpl.canonical_native_crc): CRC over everything after the header, whatever
    # legacy rule the old package used (a data-rule CRC is refused by Package::adopt: "payload CRC mismatch")
    return tpl.HEADER.pack(*nh) + body


def psnr(a, b):
    se = sum((x - y) ** 2 for p, q in zip(a, b) for x, y in zip(p, q))
    return 99.0 if se == 0 else 10 * math.log10(255 * 255 * 4 * len(a) / se)


def convert(args):
    key, old = args
    h, t = info(old)
    _, w, ht, fmt, _, size, flags, pay, _ = t
    mip = bool(flags & tpl.FLAG_MIPMAP)
    sq = w == ht
    try:
        if pay == tpl.PAYLOAD_TWIDDLED and fmt in RAW and size == w * ht * 2 and w * ht >= 64 * 64:
            from PIL import Image
            with tempfile.TemporaryDirectory() as td:
                td = Path(td)
                _, _, _, _, tex = vqn.read_package(old)
                px = [vqn.expand(v, fmt) for v in vqn.detwiddle(tex, w, ht)]
                im = Image.new('RGBA', (w, ht)); im.putdata(px); im.save(td / 'i.png')
                cmd = [PVRTEX, '-i', str(td / 'i.png'), '-o', str(td / 'o.dt'), '-f', vqn.FORMAT_NAMES[fmt], '-c',
                       '-p', str(td / 'p.png')] + (['-m'] if sq else [])
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                new, _ = tpl.package_existing_vq((td / 'o.dt').read_bytes(), allow_mipmaps=sq)
                q = psnr(px, list(Image.open(td / 'p.png').convert('RGBA').getdata())[:w * ht]) if not sq else None
            out = restamp_keep(old, new, tpl.FLAG_MIPMAP if sq else 0)
            how = 'raw16->vq' + ('+mip' if sq else '')
        elif mip or not sq:
            return key, None, dict(key=key, note='left (mipped or non-square)')
        elif pay == tpl.PAYLOAD_TWIDDLED and fmt in RAW:
            out, _ = mipmap_twiddled.add_mipmaps(old, enabled=True); how, q = 'tw16+mip', None
        elif pay == tpl.PAYLOAD_VQ and fmt in RAW:
            out, _ = mipmap_vq.add_mipmaps(old, enabled=True); how, q = 'vq+mip', None
        elif fmt == tpl.FORMAT_PAL4_ARGB4444:
            out, _ = mipmap_pal4.add_mipmaps(old, enabled=True); how, q = 'pal4+mip', None
        else:
            return key, None, dict(key=key, note='left (format %d payload %d)' % (fmt, pay))
    except Exception as e:  # noqa: BLE001
        return key, None, dict(key=key, note='failed: %s' % e)
    return key, out, dict(key=key, how=how, w=w, h=ht, before=len(old), after=len(out), psnr=q,
                          sha256=hashlib.sha256(out).hexdigest())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pak', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--material-prefix', action='append', default=[])
    ap.add_argument('--keys', help='only these keys (one per line)')
    ap.add_argument('--jobs', type=int, default=2)
    ap.add_argument('--skip-key', action='append', default=[], help='never touch this key (e.g. leon28 atlases)')
    a = ap.parse_args()
    O = Path(a.out); (O / 'dc').mkdir(parents=True, exist_ok=False)
    base = Path(a.pak).read_bytes()
    pkgs = read_pak(base)
    only = set(l.split()[0] for l in open(a.keys) if l.strip()) if a.keys else None
    todo = []
    for kt, v in sorted(pkgs.items()):
        key = '%08x-%08x' % kt
        mat = info(v)[1][0].split(b'\0')[0].decode('latin1')
        if a.material_prefix and not any(mat.startswith(p) for p in a.material_prefix):
            continue
        if (only is not None and key not in only) or key in a.skip_key:
            continue
        todo.append((key, v))
    rows, changed = [], []
    with ProcessPoolExecutor(a.jobs) as ex:
        for key, out, row in ex.map(convert, todo, chunksize=8):
            rows.append(row)
            if out is not None:
                pkgs[tuple(int(x, 16) for x in key.split('-'))] = out; changed.append(key)
    blob, _ = texpack.build(pkgs)
    texpack.verify(blob)
    (O / 'dc' / 'tex.pak').write_bytes(blob)
    sha = lambda b: hashlib.sha256(b).hexdigest()
    (O / 'pak-derived.json').write_text(json.dumps(dict(base=sha(base), out=sha(blob), count=len(pkgs), added=[],
                                                          changed=sorted(changed)), indent=1) + '\n')
    (O / 'report.json').write_text(json.dumps(dict(base_pak=a.pak, prefixes=a.material_prefix, rows=rows), indent=1) + '\n')
    import collections
    print('selected', len(todo), 'changed', len(changed), 'pak', len(base), '->', len(blob))
    print(collections.Counter(r.get('how', r.get('note')) for r in rows).most_common())


if __name__ == '__main__':
    main()
