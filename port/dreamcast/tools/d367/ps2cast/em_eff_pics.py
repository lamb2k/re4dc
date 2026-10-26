#!/usr/bin/env python3
"""em_eff_pics.py: the Ganado archives' GameCube EFF pictures -> their PS2 pictures under the same tex.pak keys
(lane gcleft26 2026-10-26, no-GameCube-assets rule).

  em_eff_pics.py <base tex.pak> <GC emNN.drs> <PS2 emNN.dat> <out dir>

Every emNN archive (em11..em17) carries the same three EFF pictures, still GameCube texels in the release pack:
  03d1e9a5-755b258f  EFF TPL image 5 (GC 48x48, base package 32x32)
  195b4634-d9ddabb6  EFF TPL image 6 (GC 48x48, base package 32x32)
  41e0ece4-322c9fcc  EFF TPL image 23 (GC 64x64, base package PAL4 64x64)
Their PS2 twins (purgeui24/ps2_tpl_pak.py match: NCC 0.990 / 0.995 / 0.998, unique) are the PS2 emNN.dat TPL pictures 5,
6 and 32 (the PS2 32x32 pictures are the base package's own size, so no resampling). The 16-bit / VQ packages are encoded
like the base package (ps2_tpl_pak.encode_like on a TPL image of the base size); the PAL4 one with the effect pack's
encoder (test12fx/fx_ps2_pack.py palette16 + package: one 16-colour premultiplied palette, PAL4 ARGB4444 twiddled, the
cover marker of the whole picture). Keys, sizes and formats stay; no package grows. Outputs dc/tex.pak, pak-derived.json,
report.json (the purge sets' layout)."""
import hashlib, json, os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / 'purgeui24'), str(HERE.parent / 'test12fx')]
import ps2_tpl_pak as P  # noqa: E402
import fx_ps2_pack as F  # noqa: E402

JOBS = [('03d1e9a5-755b258f', 5), ('195b4634-d9ddabb6', 6), ('41e0ece4-322c9fcc', 32)]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    pak, gcf, ps2f, out = sys.argv[1:5]
    os.makedirs(out + '/dc', exist_ok=True)
    base = open(pak, 'rb').read()
    pkgs = P.read_pak(base)
    gims = {P.hp.identity(im): im for _o, _n, im in P.gc_images(open(gcf, 'rb').read())}
    pims = [im for _o, ims in P.ps2_tpl.find_all(open(ps2f, 'rb').read()) for im in ims]
    rows, done = [], []
    for key, pi in JOBS:
        kt = tuple(int(x, 16) for x in key.split('-'))
        old = pkgs[kt]
        ot = P.tpl.TEXTURE.unpack_from(old, P.tpl.HEADER.unpack_from(old)[5])
        w, h, fmt = ot[1], ot[2], ot[3]
        q = pims[pi]
        img = P.hp.premul_resize(P.rgba(q['width'], q['height'], q['rgba']), (w, h))
        px = list(img.getdata())
        gim = gims[key]
        sig = P.ncc(P.signature(P.rgba(gim.width, gim.height, P.tpl.decode_image(gim))), P.signature(img))
        if fmt in (P.tpl.FORMAT_PAL4_ARGB4444,):
            weights = {}
            for c in px:
                weights[c] = weights.get(c, 0) + 1
            final, err = F.package(w, h, px, F.palette16(weights), (w, h))
            why = None if len(final) <= len(old) else 'PAL4 package grew'
        else:
            small = P.tpl.TplImage(w, h, P.tpl.GX_TF_RGBA8, bytes(w * h * 4))
            final, why = P.encode_like(old, small, px, P.vq.PVRTEX, key)
        if why or final is None:
            raise SystemExit('%s: %s' % (key, why))
        pkgs[kt] = final
        done.append(key)
        rows.append(dict(key=key, ps2_image=pi, ps2_size=[q['width'], q['height']], package=[w, h, fmt],
                         ncc_vs_gc=round(sig, 3), bytes=len(final), base_bytes=len(old), sha256=sha(final)))
        print(key, 'PS2 image', pi, '%dx%d' % (q['width'], q['height']), '-> %dx%d fmt %d' % (w, h, fmt), len(final))
    blob, _ = P.texpack.build(pkgs)
    P.texpack.verify(blob)
    open(out + '/dc/tex.pak', 'wb').write(blob)
    json.dump(dict(base=sha(base), out=sha(blob), count=len(pkgs), added=[], changed=sorted(done), removed=[]),
              open(out + '/pak-derived.json', 'w'), indent=1)
    json.dump(dict(base_pak=pak, gc=gcf, ps2=ps2f, rows=rows, tool_sha256=sha(open(__file__, 'rb').read())),
              open(out + '/report.json', 'w'), indent=1)
    print('changed', len(done), sha(blob))


if __name__ == '__main__':
    main()
