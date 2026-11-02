#!/usr/bin/env python3
"""zpair.py <base tex.pak> <out dir>: the castle Zealot (cast zealot-em11-07p) mask-run pair packages bc1a9802 / ac23b5fe /
ec7b1745 (ps2_mask_runs.py gc-bake of GC em11 TPL colour+mask images) as PS2 pixels under their keys: texels = the cast's
PS2 atlas (ps2_cast.py convert: PS2 em11.dat TPL images) over each run's hair_atlas_bbox (the hair UVs are that box mapped
affinely onto the pair texture), alpha 15 (the PS2 TPL pictures of these sections are opaque: ps2_cast wrote no
atlas-rgba.png). Each base package is kept byte for byte except its texels and body CRC: ARGB4444 twiddled, the
masked-material pair the registry run binds (as ps2_mask_runs.py / cb_tex.package_twiddled16 pack it). Rev 1 re-encoded
them with ps2_tpl_pak.encode_like, which picks opaque RGB565 for an all-opaque picture; the actor texture lease refuses
that, so the Zealot registry declined (acquire) and drew on the GC path."""
import sys, json, hashlib, os, struct, zlib
T = '/root/work/lanes/castle-gca-26/port/dreamcast/tools'
sys.path[:0] = [T, T + '/d367/purgeui24']
import ps2_tpl_pak as P
from PIL import Image
ATLAS = '/root/probe/lanes-20261016/cast16/conv4/zealot-em11-07p/atlas.png'
M = '/root/re4data/private/castle18-cast-rooms-20261018/em11/mask/zealot-em11-07p/%d/mask-runs.json'


def spread(v):
    r = 0
    for b in range(16):
        r |= ((v >> b) & 1) << (2 * b)
    return r


pak, out = sys.argv[1], sys.argv[2]
os.makedirs(out + '/dc', exist_ok=True); os.makedirs(out + '/preview', exist_ok=True)
base = open(pak, 'rb').read(); pkgs = P.read_pak(base)
at = Image.open(ATLAS).convert('RGBA'); aw, ah = at.size
sh = lambda x: hashlib.sha256(x).hexdigest()
rows, done = [], []
for sec in (13, 16, 20):
    m = json.load(open(M % sec)); key = m['keys']['pair']; w, h = m['texture']['width'], m['texture']['height']
    x0, y0, x1, y1 = m['hair_atlas_bbox']
    crop = at.crop((round(x0 * aw), round(y0 * ah), round(x1 * aw), round(y1 * ah))).resize((w, h), Image.BILINEAR)
    kt = tuple(int(x, 16) for x in key.split('-')); old = pkgs[kt]
    magic, ver, hsize, tsize, count, toff, start, plen, crc = struct.unpack_from('<8s8I', old, 0)
    assert count == 1 and plen == w * h * 2, (key, count, plen)
    mm = min(w, h); tw = bytearray(plen)
    for y in range(h):
        for x in range(w):
            r, g, b = crop.getpixel((x, y))[:3]
            t = (15 << 12) | ((r >> 4) << 8) | ((g >> 4) << 4) | (b >> 4)
            o = (spread(y & (mm - 1)) | (spread(x & (mm - 1)) << 1)) + (x // mm) * mm * mm + (y // mm) * mm * mm
            struct.pack_into('<H', tw, 2 * o, t)
    body = bytearray(old[hsize:]); body[start - hsize:start - hsize + plen] = tw
    final = bytearray(old[:hsize]) + body
    struct.pack_into('<I', final, 8 + 4 * 7, zlib.crc32(bytes(body)) & 0xffffffff)
    final = bytes(final)
    pkgs[kt] = final; done.append(key)
    crop.convert('RGB').save('%s/preview/ps2-%s.png' % (out, key))
    rows.append(dict(key=key, section=sec, atlas=ATLAS, atlas_sha256=sh(open(ATLAS, 'rb').read()), bbox=m['hair_atlas_bbox'],
                     size=[w, h], bytes=len(final), base_bytes=len(old), sha256=sh(final)))
    print(key, sec, w, h, len(final))
blob, _ = P.texpack.build(pkgs); P.texpack.verify(blob)
open(out + '/dc/tex.pak', 'wb').write(blob)
json.dump(dict(base=sh(base), out=sh(blob), count=len(pkgs), added=[], changed=sorted(done), removed=[]), open(out + '/pak-derived.json', 'w'), indent=1)
json.dump(dict(base_pak=pak, rows=rows), open(out + '/report.json', 'w'), indent=1)
print('changed', len(done), sh(blob))
