#!/usr/bin/env python3
"""lookdump.py <lib> <out dir> <room:name>...: GC and converted triangles (+ UVs, texture index) and the GC / PS2
pictures of lane items assets, for look.py (an offline textured render: ours vs GC)."""
import json
import sys
from pathlib import Path

T = Path('/root/probe/lanes-20261014/items/tree/port/dreamcast/tools')
sys.path[:0] = [str(T), str(T.parents[2] / 'tools')]
import ps2_items as pi  # noqa
import convert_tpl as ct  # noqa

po = pi.po


def tris(b):
    m = po.GcModel(b)
    out = []
    for p in m.parts:
        for t in p['tris']:
            out.append(dict(tex=p['hdr'][0x0C], mask=p['hdr'][0x0E] if p['hdr'][0x0B] & 4 else None, p=[m.p(r[0]) for r in t], uv=[m.uv(r[-1]) for r in t]))
    return out


def main():
    lib, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    src = pi.Sources()
    want = [x.split(':') for x in sys.argv[3:]]
    cache = {}
    for room, name in want:
        if room not in cache:
            cache[room] = pi.room_assets(src, room) if room != 'common' else pi.core_assets(src) + pi.ss_assets(src)
        a = next(x for x in cache[room] if x[1] == name)
        cls, nm, loc, gb, gt, pbn, ptp = a
        man = json.loads((lib / cls / room / (name + '.json')).read_text())
        new, st = pi.convert_geometry(gb, pbn)
        if man.get('geometry') == 'gc-identical':
            new = gb
        gimgs = ct.parse_tpl(gt)
        pics = {}
        for j, im in enumerate(gimgs):
            px = ct.decode_image(im)
            rgba = bytearray(b''.join(bytes(p) for p in px))
            f = out / ('%s_%s.gc%d.png' % (room, name, j))
            pi.write_png(f, im.width, im.height, rgba)
            pics['gc%d' % j] = f.name
        for s in man.get('swaps', []):
            pics['ps2_%d' % s['j']] = str(lib / cls / room / s['png'])
        pm = pi.pb.parse_bin(pbn)
        ptex = [x['diffuse'] for x in pm.materials]
        pmask = [x['opacity'] if (x['flag'] & 4 and x['opacity'] != 255) else None for x in pm.materials]
        ps2 = [dict(tex=ptex[t], mask=pmask[t], p=[c['p'] for c in cs], uv=[c['uv'] for c in cs]) for t, cs in pi.pb.triangles(pm)]
        (out / ('%s_%s.json' % (room, name))).write_text(json.dumps(dict(room=room, name=name, gc=tris(gb), ours=tris(new), ps2=ps2,
                                                                        pics=pics, swaps=man.get('swaps', [])), indent=0))
        print(room, name, len(tris(gb)), len(tris(new)))


if __name__ == '__main__':
    main()
