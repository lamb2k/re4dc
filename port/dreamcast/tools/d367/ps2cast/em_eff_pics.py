#!/usr/bin/env python3
"""em_eff_pics.py: named GameCube tex.pak pictures -> their PS2 twins' pixels under the same keys (lane gcleft26
2026-10-26, no-GameCube-assets rule). "PS2 pixels under the GC key", like purgeui24/ps2_tpl_pak.py, for a hand-picked
key list and with the base package's own size (no resampling when the PS2 picture already has it) and format, PAL4
included.

  em_eff_pics.py <base tex.pak> <out dir> --pair <GC file> <PS2 file> <key>[:<ps2 image>] ... [--pair ...]

GC file: a GameCube disc file (a .das is decoded with room_smd.decode_das), or '-' (the key has no GC disc picture:
the base package's own pixels are the reference); PS2 file: its BIO4DAT.AFS twin. Each key is
a GC TPL picture of the GC file; its PS2 picture is the given PS2 TPL image index, or else the unique best match
(normalised cross-correlation of the 24x24 signatures at the GC size, as stored or transposed for the PS2 rotate flag,
>= 0.97 and 0.03 ahead of the next picture, as ps2_tpl_pak.py); '<index>t' names a transposed one.
The 16-bit / VQ packages are encoded like the base package (ps2_tpl_pak.encode_like, at the base size); PAL4 ones with
the effect pack's encoder (test12fx/fx_ps2_pack.py palette16 + package: one 16-colour premultiplied palette, PAL4
ARGB4444 twiddled, cover marker of the whole picture). Keys, sizes and formats stay; a package may not grow.
Outputs dc/tex.pak, pak-derived.json, report.json (the purge sets' layout).

Used for: the Ganado archives' EFF pictures (every emNN: 03d1e9a5 <- PS2 TPL image 5, 195b4634 <- 6, 41e0ece4 <- 32;
NCC 0.990 / 0.995 / 0.998) and the core.das entry-25 pictures (89f1808c <- PS2 core.dat image 288, c703f665 <- image 306 transposed) and 2ea4d2ec (r101 grenade-time
picture with no GC disc twin: the package itself matches PS2 core.dat TPL 0xd2140 image 0, NCC 1.000)."""
import hashlib, json, os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / 'purgeui24'), str(HERE.parent / 'test12fx'), str(HERE.parents[1])]
import ps2_tpl_pak as P  # noqa: E402
import fx_ps2_pack as F  # noqa: E402
from PIL import Image  # noqa: E402


def sha(b):
    return hashlib.sha256(b).hexdigest()


def gc_pictures(path):
    b = open(path, 'rb').read()
    out = {P.hp.identity(im): im for _o, _n, im in P.gc_images(b)}
    if path.lower().endswith('.das'):   # YZ2-packed .das: its decoded body too
        import room_smd
        try:
            out.update({P.hp.identity(im): im for _o, _n, im in P.gc_images(room_smd.decode_das(b))})
        except ValueError:
            pass
    return out


def ps2_image(q, transpose):
    im = P.rgba(q['width'], q['height'], q['rgba'])
    return im.transpose(Image.TRANSPOSE) if transpose else im


def package_image(blob):
    """RGBA picture of a single-texture native package (VQ or twiddled 16-bit), padded size."""
    import struct
    import vq_native_ui as V
    tpl = P.tpl
    _, w, h, fmt, do, ds, _flags, payload, _ = tpl.TEXTURE.unpack_from(blob, tpl.HEADER.unpack_from(blob)[5])
    if payload == tpl.PAYLOAD_VQ:
        cb = struct.unpack_from('<1024H', blob, do)
        idx = blob[do + 2048:do + ds]
        order = tpl.twiddle_16bpp(list(range((w // 2) * (h // 2))), w // 2, h // 2)
        lin = [0] * len(order)
        for t, i in enumerate(order):
            lin[i] = idx[t]
        px = [None] * (w * h)
        for by in range(h // 2):
            for bx in range(w // 2):
                c = lin[by * (w // 2) + bx]
                for k, (dx, dy) in enumerate(((0, 0), (0, 1), (1, 0), (1, 1))):
                    px[(2 * by + dy) * w + 2 * bx + dx] = V.expand(cb[4 * c + k], fmt)
    else:
        px = [V.expand(v, fmt) for v in V.detwiddle(struct.unpack_from('<%dH' % (w * h), blob, do), w, h)]
    img = Image.new('RGBA', (w, h))
    img.putdata(px)
    return img


class Ref:
    """The GC reference picture: a GC TPL image, or (GC file '-') the base package's own pixels (a key with no GC disc
    picture, e.g. 2ea4d2ec)."""
    def __init__(self, gim=None, img=None):
        self.img = img if img is not None else P.rgba(gim.width, gim.height, P.tpl.decode_image(gim))
        self.width, self.height = self.img.size


def match(gim, pims):
    """(PS2 image index, transposed, NCC): the unique best PS2 picture as stored or transposed (the PS2 rotate flag:
    the renderer swaps U and V), compared at the GC picture's size."""
    gs = P.signature(gim.img)
    cand = sorted(((P.ncc(gs, P.signature(P.hp.premul_resize(ps2_image(q, t), (gim.width, gim.height)))), j, t)
                   for j, q in enumerate(pims) for t in (False, True)), reverse=True)
    best = cand[0]
    second = next((c for c in cand[1:] if c[1] != best[1]), (-1.0, -1, False))
    if best[0] < 0.97 or best[0] - second[0] < 0.03:
        raise SystemExit('no unique PS2 picture: %s' % cand[:3])
    return best[1], best[2], best[0]


def main():
    a = sys.argv[1:]
    pak, out = a[0], a[1]
    pairs, i = [], 2
    while i < len(a):
        assert a[i] == '--pair', a[i]
        j = i + 3
        while j < len(a) and a[j] != '--pair':
            j += 1
        pairs.append((a[i + 1], a[i + 2], a[i + 3:j]))
        i = j
    os.makedirs(out + '/dc', exist_ok=True)
    base = open(pak, 'rb').read()
    pkgs = P.read_pak(base)
    rows, done = [], []
    for gcf, ps2f, keys in pairs:
        gims = gc_pictures(gcf) if gcf != '-' else {}
        pims = [im for _o, ims in P.ps2_tpl.find_all(open(ps2f, 'rb').read()) for im in ims]
        for spec in keys:
            key, _, pi = spec.partition(':')
            kt = tuple(int(x, 16) for x in key.split('-'))
            gim = Ref(gims[key]) if gcf != '-' else Ref(img=package_image(pkgs[kt]))
            if pi:
                tr, pi, score = pi.endswith('t'), int(pi.rstrip('t')), None
            else:
                pi, tr, score = match(gim, pims)
            kt = tuple(int(x, 16) for x in key.split('-'))
            old = pkgs[kt]
            ot = P.tpl.TEXTURE.unpack_from(old, P.tpl.HEADER.unpack_from(old)[5])
            w, h, fmt = ot[1], ot[2], ot[3]
            q = pims[pi]
            p2 = lambda n: 1 << (n - 1).bit_length()
            # the picture's own size when the base package is it padded to powers of two (c703f665: 64x80 in 64x128,
            # sampled through the UV scale), else the package size (the EFF pictures: GC 48x48, package 32x32)
            tw, th = (gim.width, gim.height) if (p2(gim.width), p2(gim.height)) == (w, h) and fmt != P.tpl.FORMAT_PAL4_ARGB4444 else (w, h)
            img = P.hp.premul_resize(ps2_image(q, tr), (tw, th))
            px = list(img.getdata())
            if score is None:
                score = P.ncc(P.signature(gim.img), P.signature(img))
            if fmt == P.tpl.FORMAT_PAL4_ARGB4444:
                weights = {}
                for c in px:
                    weights[c] = weights.get(c, 0) + 1
                final, _err = F.package(w, h, px, F.palette16(weights), (w, h))
                why = None if len(final) <= len(old) else 'PAL4 package grew'
            else:
                small = P.tpl.TplImage(tw, th, P.tpl.GX_TF_RGBA8, bytes(tw * th * 4))
                final, why = P.encode_like(old, small, px, P.vq.PVRTEX, key)
            if why or final is None:
                raise SystemExit('%s: %s' % (key, why))
            pkgs[kt] = final
            done.append(key)
            rows.append(dict(key=key, gc=gcf, ps2=ps2f, ps2_image=pi, transposed=tr, ps2_size=[q['width'], q['height']],
                             package=[w, h, fmt], ncc_vs_gc=round(score, 3), bytes=len(final), base_bytes=len(old),
                             sha256=sha(final)))
            print(key, 'PS2 image', pi, '%dx%d' % (q['width'], q['height']), '-> %dx%d in %dx%d fmt %d' % (tw, th, w, h, fmt),
                  'ncc %.3f' % score, len(final))
    blob, _ = P.texpack.build(pkgs)
    P.texpack.verify(blob)
    open(out + '/dc/tex.pak', 'wb').write(blob)
    json.dump(dict(base=sha(base), out=sha(blob), count=len(pkgs), added=[], changed=sorted(done), removed=[]),
              open(out + '/pak-derived.json', 'w'), indent=1)
    json.dump(dict(base_pak=pak, rows=rows, tool_sha256=sha(open(__file__, 'rb').read())),
              open(out + '/report.json', 'w'), indent=1)
    print('changed', len(done), sha(blob))


if __name__ == '__main__':
    main()
