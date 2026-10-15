#!/usr/bin/env python3
"""ps2_items_tex.py <ps2lib> [--classes items,breakables]: the .re4tex packages of lane items' PS2 pictures
(Windows Python: numpy + PIL; the encoders are ps2_room_r4im.py's, i.e. the PS2 world packs' rules).

For every picture swap in <lib>/<class>/manifest.json (written by ps2_items.py convert; mask swaps excepted) and every
material pair (colour RGB + mask intensity as alpha, keyed material_pair_identity): the PS2 RGBA (<name>.t<j>.png,
already turned to the GC orientation; alpha forced opaque where the GC picture is opaque) -> opaque: VQ RGB565 when smaller than 16-bit, else twiddled RGB565;
cutout (alpha 0 / 255 only): twiddled ARGB1555; graded: twiddled ARGB4444. The package is written as
<lib>/<class>/tex/<key>.re4tex where <key> is the picture's GC identity (ps2_items.py identity_key), the key the
runtime asks dc/tex.pak for. A key seen twice must give the same bytes. Writes <lib>/<class>/tex/tex.json.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ps2_room_r4im as w  # noqa: E402  (loads the world agent's codec / VQ helpers)


def build(png, opaque=False, mask=None):
    """opaque: alpha forced to 255 (the GC picture is opaque); mask: a grey PNG whose intensity becomes the alpha
    (a material pair: colour + mask in one package, prepare_native_ui.prepare_model_pairs' contract)"""
    image = np.array(Image.open(png).convert('RGBA'))
    if opaque:
        image[..., 3] = 255
    if mask is not None:
        m = np.asarray(Image.open(mask).convert('RGBA'))
        if m.shape != image.shape:
            raise SystemExit('pair %s + %s: sizes differ' % (png, mask))
        image[..., 3] = m[..., 0]
    h, wd = image.shape[:2]
    alpha = np.unique(image[..., 3])
    mode = 'opaque' if alpha.min() == 255 else ('cutout' if np.all(np.isin(alpha, [0, 255])) else 'graded')
    fmt = {'opaque': 0, 'cutout': 1, 'graded': 2}[mode]
    target = image.astype(np.float64)
    use_vq = fmt == 0 and 2048 + wd * h // 4 < wd * h * 2
    if use_vq:
        payload, ptype = w.vq_encode(target, fmt), 2
    else:
        q = w.pack16(target, fmt)
        raw = np.empty(wd * h, dtype='<u2'); raw[w.codec.untwiddle_index(wd, h).ravel()] = q.ravel()
        payload, ptype = raw.tobytes(), 1
    return wd, h, fmt, ptype, payload, mode, use_vq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('lib')
    ap.add_argument('--classes', default='items,breakables')
    a = ap.parse_args()
    lib = Path(a.lib)
    for cls in a.classes.split(','):
        man = json.loads((lib / cls / 'manifest.json').read_text())
        out = lib / cls / 'tex'
        out.mkdir(exist_ok=True)
        rows, done = {}, {}
        for asset in man['assets']:
            jobs = [(s['key'], s['png'], None, s.get('gc_alpha') == 'opaque', s) for s in asset.get('swaps', [])
                    if s.get('role') != 'mask']
            jobs += [(p['key'], p['color_png'], p['mask_png'], False, p) for p in asset.get('pairs', [])]
            for key, pngname, maskname, opaque, s in jobs:
                png = lib / cls / asset['room'] / pngname
                src = png.read_bytes() + (b'|' + (lib / cls / asset['room'] / maskname).read_bytes() if maskname else b'') + (b'|opaque' if opaque else b'')
                if key in done and done[key][1] == src:
                    rows[key]['uses'].append('%s/%s' % (asset['room'], asset['name']))
                    continue
                wd, h, fmt, ptype, payload, mode, vq = build(png, opaque, lib / cls / asset['room'] / maskname if maskname else None)
                if (wd, h) != (s['w'], s['h']):
                    raise SystemExit('%s: png %dx%d != swap %dx%d' % (png, wd, h, s['w'], s['h']))
                data, _ = w.re4dctx_bytes('PS2 %s %s' % (cls, key), wd, h, fmt, ptype, payload)
                if key in done:
                    # same identity from two rooms must be the same picture
                    raise SystemExit('key %s: two different pictures' % key)
                (out / (key + '.re4tex')).write_bytes(data)
                done[key] = (data, src)
                rows[key] = dict(key=key, width=wd, height=h, format=fmt, payload='vq' if vq else 'native16', alpha=mode,
                                 kind='pair' if maskname else 'picture',
                                 vram_bytes=len(payload), bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                                 uses=['%s/%s' % (asset['room'], asset['name'])])
        (out / 'tex.json').write_text(json.dumps(sorted(rows.values(), key=lambda r: r['key']), indent=1))
        print(cls, 'packages', len(rows), 'vram bytes', sum(r['vram_bytes'] for r in rows.values()))


if __name__ == '__main__':
    main()
