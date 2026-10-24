#!/usr/bin/env python3
"""ps2_hud_pak.py --gc-core core.das --ps2-core Core.dat --pak base/tex.pak --out DIR [--map map.tsv]
(lane purge-ui24, 2026-10-24; GC asset purge, user 10-23 "this game shouldn't have any game cube assets")

The HUD pictures the game reads from the GameCube etc/core.das become the PS2 Core.dat pictures, shipped as "PS2 pixels
under the GC key": the runtime still hashes the GC TPL image it loads (crc32-FNV source identity) and binds the tex.pak
package of that key, so only the package payload changes. No runtime change, no knob; a data set (t11-fix.py) after the
last pack set.

Per map row (GC key, GC core.das TPL offset, PS2 Core.dat TPL offset, PS2 image index):
  1. the GC image at that offset must hash to the key (refuses a wrong source);
  2. the PS2 picture (tools/ps2_tpl.py) is fitted to the GC framing: its alpha bounding box is resampled (bilinear,
     premultiplied) onto the GC picture's alpha bounding box, transparent elsewhere (the GC UVs stay valid);
  3. packaged by the existing texture prep (convert_tpl.build_package with source_pixels, the ui_overrides.py path:
     twiddled 16-bit, power-of-two padding), then encoded like the base pack's package of that key (full-codebook VQ via
     vq_native_ui.encode when the base package is VQ) and restamped with its material name (vq_pak.restamp).
Outputs: DIR/dc/tex.pak (texpack build + verify), pak-derived.json (base/out sha256, changed keys: t11-fix.py
PAK_DERIVED), report.json, previews/<key>-{gc,ps2}.png. Private data: nothing produced here belongs in Git.
"""
import argparse, hashlib, json, struct, sys, tempfile, zlib
from pathlib import Path
from PIL import Image

T = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(T), str(T / 'd367'), str(T / 'd367' / 'vram')]
import convert_tpl as tpl      # noqa: E402
import ps2_tpl                 # noqa: E402
import vq_native_ui as vq      # noqa: E402
import texpack                 # noqa: E402
from vq_pak import read_pak, restamp  # noqa: E402

# GC key, GC core.das TPL offset, PS2 Core.dat TPL offset, image index, what it is (debug Disc 1 G4BE08 / PS2 USA)
MAP = [
    ('4453f667-45bfa53f', 0x1c9760, 0x128670, 0, 'ammo lens EMPTY (64x64 C4) <- PS2 32x32'),
    ('8f6b4eb2-8081114f', 0x1c6400, 0x1265a0, 0, 'life gauge sphere (64x64 C8) <- PS2 64x64'),
    ('5876c879-66dc7739', 0x1e75a0, 0x139c90, 0, 'name label Leon (48x24) <- PS2 32x16'),
    ('9d10cae4-346ca7ad', 0x1e4fe0, 0x138050, 0, 'ammo bullet icon (48x32) <- PS2 32x16'),
    ('afa4bc82-306be3e3', 0x1e0360, 0x134d30, 0, 'gauge arc (44x44) <- PS2 64x64'),
    ('008c81f7-a82ce898', 0x1f4fc0, 0x1409d0, 0, 'partner icon ! (32x32) <- PS2 32x32'),
    ('0bdce3ef-43f4fcb5', 0x1f5240, 0x140c90, 0, 'partner icon together (64x64) <- PS2 64x64'),
    ('4ae2bfaf-4e307ec2', 0x1f4240, 0x13fb90, 0, 'partner icon wait (64x64) <- PS2 64x64'),
    ('711dd021-24d61c99', 0x1e62a0, 0x138fb0, 0, 'dark gauge dome (48x48) <- PS2 32x32'),
    ('7295834a-e6158750', 0x1e1080, 0x135b70, 0, 'gauge quarter disc (48x48) <- PS2 64x64'),
    ('862bd374-a98ce31f', 0x1dd860, 0x1338f0, 0, 'Ashley gauge (103x99) <- PS2 64x64'),
    ('e42a7628-c166970d', 0x1b2c60, 0x11eaf0, 0, 'd-pad cross (26x26) <- PS2 16x16'),
]
# Held for a decision (coordinator): controller button glyphs. The PS2 pictures say L1 / R1 (PS2 pad), the GC ones L / R,
# which is what a Dreamcast pad has. --buttons adds them: 755e1575 (L, 59x51) <- PS2 L1 0x1280b0, 803499f2 (R, 59x48)
# <- PS2 R1 0x127bf0. The GC B button (3acc7fea, 36x36) has no PS2 counterpart chosen.
BUTTONS = [
    ('755e1575-fea9d26b', 0x1c8e60, 0x1280b0, 0, 'shoulder button L (59x51) <- PS2 L1 64x32'),
    ('803499f2-4b0a27a8', 0x1c87e0, 0x127bf0, 0, 'shoulder button R (59x48) <- PS2 R1 64x32'),
]
COLOR_PS2 = (0x120590, 0)   # PS2 picture of the HUD colour key 0565aab7 (decodes identical to the GC one)
COMPOSITE = [('84d450d5-ede2f8a1', '8f6b4eb2-8081114f'), ('acfcae72-ccf1609c', '4453f667-45bfa53f')]


def identity(im):
    pal = im.palette_data or b''
    md = struct.pack('<5I', im.width, im.height, im.format,
                     im.palette_format if im.palette_format is not None else 0xffffffff, len(pal))
    p = md + im.data + pal
    f = 2166136261
    for b in p:
        f = ((f ^ b) * 16777619) & 0xffffffff
    return '%08x-%08x' % (zlib.crc32(p) & 0xffffffff, f)


def bbox(img):
    return img.getchannel('A').point(lambda a: 255 if a > 8 else 0).getbbox() or (0, 0, img.width, img.height)


def premul_resize(img, size):
    r, g, b, a = [list(c.getdata()) for c in img.split()]
    pm = Image.new('RGBA', img.size)
    pm.putdata([(r[i] * a[i] // 255, g[i] * a[i] // 255, b[i] * a[i] // 255, a[i]) for i in range(len(a))])
    pm = pm.resize(size, Image.BILINEAR)
    out = []
    for (R, G, B, A) in pm.getdata():
        out.append((min(255, R * 255 // A), min(255, G * 255 // A), min(255, B * 255 // A), A) if A else (0, 0, 0, 0))
    res = Image.new('RGBA', size)
    res.putdata(out)
    return res


def fit(gc_img, ps2_img):
    gb, pb = bbox(gc_img), bbox(ps2_img)
    crop = ps2_img.crop(pb)
    size = (gb[2] - gb[0], gb[3] - gb[1])
    canvas = Image.new('RGBA', gc_img.size, (0, 0, 0, 0))
    canvas.paste(crop if crop.size == size else premul_resize(crop, size), gb[:2])
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gc-core', required=True)
    ap.add_argument('--ps2-core', required=True)
    ap.add_argument('--pak', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--pvrtex', default=vq.PVRTEX)
    ap.add_argument('--buttons', action='store_true', help='also the L1/R1 button glyphs (held for a decision)')
    a = ap.parse_args()
    if a.buttons:
        MAP.extend(BUTTONS)
    out = Path(a.out)
    (out / 'dc').mkdir(parents=True, exist_ok=True)
    prev = out / 'previews'
    prev.mkdir(exist_ok=True)
    gc = Path(a.gc_core).read_bytes()
    ps = Path(a.ps2_core).read_bytes()
    base = Path(a.pak).read_bytes()
    pkgs = read_pak(base)
    rep = []
    for key, goff, poff, pidx, what in MAP:
        k = tuple(int(x, 16) for x in key.split('-'))
        gim = tpl.parse_tpl(gc[goff:])[0]
        assert identity(gim) == key, (key, identity(gim))
        gimg = Image.new('RGBA', (gim.width, gim.height))
        gimg.putdata(tpl.decode_image(gim))
        pim = ps2_tpl.parse(ps, poff)[pidx]
        pimg = Image.new('RGBA', (pim['width'], pim['height']))
        pimg.putdata(pim['rgba'])
        new = fit(gimg, pimg)
        gimg.save(prev / (key + '-gc.png'))
        new.save(prev / (key + '-ps2.png'))
        pkg16, meta = tpl.build_package([gim], [tpl.MaterialBinding('source', 0, None)], twiddle=True,
                                        pad_to_power_of_two=True, source_intensity_alpha=True,
                                        source_pixels={0: list(new.getdata())})
        old = pkgs[k]
        oh = tpl.HEADER.unpack_from(old)
        ot = tpl.TEXTURE.unpack_from(old, oh[5])
        nt = tpl.TEXTURE.unpack_from(pkg16, tpl.HEADER.unpack_from(pkg16)[5])
        assert (nt[1], nt[2]) == (ot[1], ot[2]), (key, 'native size', nt[1:3], ot[1:3])
        row = dict(key=key, what=what, gc_offset=goff, ps2_offset=poff, ps2_index=pidx,
                   ps2_size=[pim['width'], pim['height']], gc_size=[gim.width, gim.height],
                   base_payload=ot[7], base_format=ot[3], new_format=nt[3], base_bytes=len(old))
        if ot[7] == tpl.PAYLOAD_VQ:
            with tempfile.TemporaryDirectory() as td:
                td = Path(td)
                (td / 'in').mkdir(); (td / 'out').mkdir()
                (td / 'in' / (key + '.re4tex')).write_bytes(pkg16)
                e = vq.encode(key, td / 'in', td / 'out', a.pvrtex, (gim.width, gim.height), td)
                enc = (td / 'out' / (key + '.re4tex')).read_bytes()
            row['psnr_db'] = e['psnr_db']
        else:
            enc = pkg16
        final, rule = restamp(old, enc)
        pkgs[k] = final
        row.update(new_bytes=len(final), sha256=hashlib.sha256(final).hexdigest())
        rep.append(row)
        print('%s %-44s base fmt%d payload%d %5d B -> fmt%d %5d B' % (key, what, ot[3], ot[7], len(old), nt[3], len(final)))
    # HUD mask composites (UI_HUD_MASK, hud_source_mask_keys.inc; built by the 09-27 hud-source-mask-r1 bundle): the core
    # colour picture 0565aab7 (constant RGB, already PS2 in the pack) with the alpha of mask 8f6b4eb2 / 4453f667. Rebuilt
    # from the PS2 masks fitted above, so the composite matches the swapped masks.
    cim = ps2_tpl.parse(ps, COLOR_PS2[0])[COLOR_PS2[1]]
    rgb = cim['rgba'][0][:3]
    for key, mkey in COMPOSITE:
        k = tuple(int(x, 16) for x in key.split('-'))
        if k not in pkgs:
            print(key, 'not in the base pack: skipped'); continue
        mrow = next(r for r in MAP if r[0] == mkey)
        gim = tpl.parse_tpl(gc[mrow[1]:])[0]
        mask = Image.open(prev / (mkey + '-ps2.png')).convert('RGBA')
        pix = [rgb + (a,) for a in mask.getchannel('A').getdata()]
        comp = Image.new('RGBA', mask.size); comp.putdata(pix); comp.save(prev / (key + '-ps2.png'))
        pkg16, _ = tpl.build_package([gim], [tpl.MaterialBinding('source', 0, None)], twiddle=True,
                                     pad_to_power_of_two=True, source_intensity_alpha=True, source_pixels={0: pix})
        old = pkgs[k]
        ot = tpl.TEXTURE.unpack_from(old, tpl.HEADER.unpack_from(old)[5])
        row = dict(key=key, what='HUD mask composite: colour 0565aab7 rgb %s x alpha of PS2 %s' % (rgb, mkey),
                   base_payload=ot[7], base_format=ot[3], base_bytes=len(old))
        if ot[7] == tpl.PAYLOAD_VQ:
            with tempfile.TemporaryDirectory() as td:
                td = Path(td); (td / 'in').mkdir(); (td / 'out').mkdir()
                (td / 'in' / (key + '.re4tex')).write_bytes(pkg16)
                e = vq.encode(key, td / 'in', td / 'out', a.pvrtex, (gim.width, gim.height), td)
                enc = (td / 'out' / (key + '.re4tex')).read_bytes()
            row['psnr_db'] = e['psnr_db']
        else:
            enc = pkg16
        final, _ = restamp(old, enc)
        pkgs[k] = final
        row.update(new_bytes=len(final), sha256=hashlib.sha256(final).hexdigest())
        rep.append(row)
        print('%s composite of %s: %d B -> %d B' % (key, mkey, len(old), len(final)))
    blob, _ = texpack.build(pkgs)
    texpack.verify(blob)
    (out / 'dc' / 'tex.pak').write_bytes(blob)
    sha = lambda b: hashlib.sha256(b).hexdigest()
    (out / 'pak-derived.json').write_text(json.dumps(dict(base=sha(base), out=sha(blob), count=len(pkgs), added=[],
                                                          changed=sorted(r['key'] for r in rep)), indent=1) + '\n')
    (out / 'report.json').write_text(json.dumps(dict(gc_core=sha(gc), ps2_core=sha(ps), base_pak=a.pak, rows=rep),
                                                indent=1) + '\n')
    print('tex.pak', sha(blob), len(pkgs), 'packages')


if __name__ == '__main__':
    main()
