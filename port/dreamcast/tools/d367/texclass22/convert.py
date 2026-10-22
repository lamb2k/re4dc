#!/usr/bin/env python3
"""convert.py (lane texclass22): add mip chains to the "convert" keys on top of a base pack.

    convert.py --pack v4/tex.pak --keys convert.txt [--recover KEY ...] --out out/tex.pak --report out/convert.json

Generators: square 16-bit VQ = tools/mipmap_vq.py; square 16-bit twiddled = mipmap_twiddled.py; PAL4 = mipmap_pal4.py.
--recover keys (VQ that failed the mipfix22 colour gate) use the miprecover22 spare-slot method
(mipmap_compact_vq.add_mipmaps_original). Every other member stays byte-identical; the full-resolution base of each
converted key is checked exact. Gate the output with mipfix22 mip_quality.py (holds failures at the original).
"""
import argparse, hashlib, json, sys
from pathlib import Path

TOOLS = Path('/root/work/lanes/miprecover22/tree/port/dreamcast/tools')
sys.path.insert(0, str(TOOLS)); sys.path.insert(0, str(TOOLS / 'd367'))
import convert_tpl as tpl
import mipmap_vq as vq
import mipmap_twiddled as tw
import mipmap_pal4 as pal4
import mipmap_compact_vq as cvq
import texpack
from vram.vq_pak import read_pak


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pack', required=True, type=Path); ap.add_argument('--keys', required=True, type=Path)
    ap.add_argument('--recover', nargs='*', default=[]); ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--report', required=True, type=Path)
    a = ap.parse_args()
    src = a.pack.read_bytes()
    packages = read_pak(src)
    new = dict(packages)
    rows = []
    rec = set(a.recover)
    for name in [l.split()[0] for l in a.keys.read_text().splitlines() if l.strip() and not l.startswith('#')]:
        key = tuple(int(x, 16) for x in name.split('-'))
        blob = packages[key]
        t = tpl.TEXTURE.unpack_from(blob, 48)
        fmt, layout = t[3], t[7]
        if name in rec:
            out, ev = cvq.add_mipmaps_original(blob, enabled=True)
            gen = 'compact_vq-original'
        elif fmt == tpl.FORMAT_PAL4_ARGB4444:
            out, ev = pal4.add_mipmaps(blob, enabled=True); gen = 'pal4'
        elif layout == tpl.PAYLOAD_VQ:
            out, ev = vq.add_mipmaps(blob, enabled=True); gen = 'vq'
        else:
            out, ev = tw.add_mipmaps(blob, enabled=True); gen = 'twiddled'
        new[key] = out
        rows.append(dict(key=name, generator=gen, before_bytes=len(blob), after_bytes=len(out),
                         extra_bytes=len(out) - len(blob), extra_alloc32=((len(out) - 144 + 31) // 32 - (len(blob) - 144 + 31) // 32) * 32,
                         after_sha256=hashlib.sha256(out).hexdigest()))
    cand, count = texpack.build(new)
    texpack.verify(cand)
    changed = sorted('%08x-%08x' % k for k in packages if packages[k] != new[k])
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_bytes(cand)
    rep = dict(schema='re4dc-texclass22-addon-1', base_pack_sha256=hashlib.sha256(src).hexdigest(),
               out_pack_sha256=hashlib.sha256(cand).hexdigest(), members=count, converted=len(rows), changed=len(changed),
               extra_bytes=sum(r['extra_bytes'] for r in rows), rows=rows)
    a.report.write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps({k: v for k, v in rep.items() if k != 'rows'}))


if __name__ == '__main__':
    main()
