#!/usr/bin/env python3
"""look_rooms.py <tree> <set dir> <out dir> [--threshold dB]   (lane assets-dc, 2026-11-02; tier 2 auto pixel diff per room)

For a dcform_dir.py set over a content tree: per changed picture, base-level PSNR of the new package against the old
16-bit texels (mips-only changes keep the base: checked byte for byte). Pictures are grouped by room through the tree's
dc/resident.bin (16-byte records: u16 room, width, height, format; u32 crc, fnv); keys no room lists go to 'unlisted'.
Writes look-rooms.tsv (room, pictures, raw->VQ, min / median PSNR, below threshold) and sheet-<room>.png (old | new, 2x)
for every picture under the threshold (default 28 dB).
"""
import json, os, struct, sys, math, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent), str(HERE.parent / 'vram'), str(HERE)]
import convert_tpl as tpl, vq_native_ui as vqn, mipmap_vq  # noqa: E402
from lookcheck import psnr  # noqa: E402


def dec_old(b):
    h = tpl.HEADER.unpack_from(b); t = tpl.TEXTURE.unpack_from(b, h[5])
    _, _, _, _, tex = vqn.read_package(b)
    return t[1], t[2], [vqn.expand(v, t[3]) for v in vqn.detwiddle(tex, t[1], t[2])]


def main():
    tree, setd, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    thr = float(sys.argv[sys.argv.index('--threshold') + 1]) if '--threshold' in sys.argv else 28.0
    out.mkdir(parents=True, exist_ok=True)
    rooms = collections.defaultdict(set)
    rb = (tree / 'dc/resident.bin').read_bytes() if (tree / 'dc/resident.bin').exists() else b''
    for i in range(0, len(rb) - 15, 16):
        room, w, h, f, crc, fnv = struct.unpack_from('<4H2I', rb, i)
        if room:
            rooms['%08x-%08x' % (crc, fnv)].add('r%03x' % room)
    # plus a byte search of each key (u32 crc, u32 fnv, little endian, or its text form) in each room's own files:
    # dc/native/rXXX/* and st*/rXXX* (room worlds, registries, archives)
    rep = json.load(open(setd / 'report.json'))['rows']
    keys = [os.path.basename(r['path'])[:-7] for r in rep if 'how' in r]
    blobs = collections.defaultdict(bytearray)
    for d, _, fs in os.walk(tree):
        for f in fs:
            rel = os.path.relpath(os.path.join(d, f), tree)
            parts = rel.split('/')
            room = parts[2] if rel.startswith('dc/native/') and len(parts) > 3 else (f[:4] if parts[0].startswith('st') and f[:1] == 'r' else None)
            if room and room[:1] == 'r':
                blobs[room] += open(os.path.join(d, f), 'rb').read()
    for k in keys:
        c, v = (int(x, 16) for x in k.split('-'))
        pat, txt = struct.pack('<2I', c, v), k.encode()
        for room, b in blobs.items():
            if pat in b or txt in b:
                rooms[k].add(room)
    per = collections.defaultdict(list); low = collections.defaultdict(list)
    for r in rep:
        if 'how' not in r:
            continue
        key = os.path.basename(r['path'])[:-7]
        old = (tree / r['path']).read_bytes(); new = (setd / r['path']).read_bytes()
        if r['how'].startswith('raw16'):
            w, h, a = dec_old(old)
            if w == h:
                b = mipmap_vq.decode_level(mipmap_vq.read_native_vq(new), w); q = psnr(a, b)
            else:
                # non-square VQ: decode through the package's own index layout is not in mipmap_vq; use pvrtex's
                # preview PSNR recorded by dcform_pak (r['psnr'])
                b, q = None, r.get('psnr') or 0.0
        else:
            q, a, b, w, h = 99.0, None, None, r['w'], r['h']
        for room in sorted(rooms.get(key, {'unlisted'})):
            per[room].append((q, r['how']))
            if q < thr and b is not None:
                low[room].append((q, key, w, h, a, b))
    from PIL import Image
    with open(out / 'look-rooms.tsv', 'w') as f:
        f.write('room\tpictures\traw_to_vq\tmin_psnr\tmedian_psnr\tbelow_%.0f_dB\n' % thr)
        for room in sorted(per):
            qs = sorted(q for q, how in per[room] if how.startswith('raw16'))
            f.write('%s\t%d\t%d\t%.1f\t%.1f\t%d\n' % (room, len(per[room]), len(qs), qs[0] if qs else 99, qs[len(qs) // 2] if qs else 99,
                                                  sum(1 for q in qs if q < thr)))
            lo = sorted(low[room], key=lambda x: x[0])[:24]
            if lo:
                cols = 4; tw = 136
                sheet = Image.new('RGBA', (cols * (tw + 8), ((len(lo) + cols - 1) // cols) * 72), (40, 40, 40, 255))
                for i, (q, key, w, h, a, b) in enumerate(lo):
                    for j, px in enumerate((a, b)):
                        t = Image.new('RGBA', (w, h)); t.putdata(px)
                        sheet.paste(t.resize((64, 64)), ((i % cols) * (tw + 8) + j * 72, (i // cols) * 72))
                sheet.save(out / ('sheet-%s.png' % room))
    print(open(out / 'look-rooms.tsv').read())


if __name__ == '__main__':
    main()
