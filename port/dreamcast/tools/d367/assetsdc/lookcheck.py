#!/usr/bin/env python3
"""lookcheck.py <base tex.pak> <set dir> <out dir> [--sheet N]   (lane assets-dc, 2026-11-02; tier 2 look check, offline)

Per changed key of a dcform_pak.py set: base-level pixel diff of the new package against the old one.
  - '+mip' only (vq+mip, tw16+mip, pal4+mip): the base level is byte-identical by construction (mipmap_* keep the base
    codebook / indices / texels); checked here by comparing the base payload bytes.
  - raw16->vq(+mip): the old 16-bit texels against the decoded VQ base (square: mipmap_vq.decode_level; non-square:
    the pvrtex preview PSNR the set recorded). PSNR over RGBA, and the max per-channel error.
Writes <out>/look.tsv and, for the N lowest-PSNR square conversions, <out>/pairs/<key>.png (old | new, 2x, side by side)
as the still pairs for the user's look batch.
"""
import json, sys, pathlib, math
HERE = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent), str(HERE.parent / 'vram')]
import convert_tpl as tpl      # noqa: E402
import vq_native_ui as vqn     # noqa: E402
import mipmap_vq               # noqa: E402
from vq_pak import read_pak    # noqa: E402


def psnr(a, b):
    se = sum((x - y) ** 2 for p, q in zip(a, b) for x, y in zip(p, q))
    return 99.0 if se == 0 else 10 * math.log10(255 * 255 * 4 * len(a) / se)


def main():
    base, setd, out = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
    nsheet = int(sys.argv[sys.argv.index('--sheet') + 1]) if '--sheet' in sys.argv else 12
    out.mkdir(parents=True, exist_ok=True)
    old = read_pak(open(base, 'rb').read())
    new = read_pak(open(setd / 'dc' / 'tex.pak', 'rb').read())
    rep = {r['key']: r for r in json.load(open(setd / 'report.json'))['rows'] if 'how' in r}
    rows = []
    for k, r in sorted(rep.items()):
        kt = tuple(int(x, 16) for x in k.split('-'))
        o, n = old[kt], new[kt]
        ot = tpl.TEXTURE.unpack_from(o, tpl.HEADER.unpack_from(o)[5])
        nt = tpl.TEXTURE.unpack_from(n, tpl.HEADER.unpack_from(n)[5])
        if not r['how'].startswith('raw16'):
            # base level: the old payload must sit unchanged at the end of the new chain (mips are stored smallest first)
            same = n[nt[4]:nt[4] + nt[5]].endswith(o[ot[4]:ot[4] + ot[5]]) or \
                   (r['how'] == 'vq+mip' and n[nt[4]:nt[4] + 2048] == o[ot[4]:ot[4] + 2048])
            rows.append((k, r['how'], r['w'], r['h'], 99.0 if same else -1.0, 0, 'base kept' if same else 'BASE CHANGED'))
            continue
        w, h, fmt = ot[1], ot[2], ot[3]
        _, _, _, _, tex = vqn.read_package(o)
        px = [vqn.expand(v, fmt) for v in vqn.detwiddle(tex, w, h)]
        if w == h:
            dec = mipmap_vq.decode_level(mipmap_vq.read_native_vq(n), w)
            q = psnr(px, dec); mx = max(abs(x - y) for p, s in zip(px, dec) for x, y in zip(p, s))
            rows.append((k, r['how'], w, h, round(q, 2), mx, ''))
            if nsheet:
                rows[-1] = rows[-1][:6] + ((px, dec),)
        else:
            rows.append((k, r['how'], w, h, r.get('psnr') or -1, -1, 'pvrtex preview'))
    sq = sorted([x for x in rows if isinstance(x[6], tuple)], key=lambda x: x[4])[:nsheet]
    if sq:
        from PIL import Image
        (out / 'pairs').mkdir(exist_ok=True)
        for k, how, w, h, q, mx, (a, b) in sq:
            im = Image.new('RGBA', (w * 4 + 8, h * 2), (255, 0, 255, 255))
            for i, src in enumerate((a, b)):
                t = Image.new('RGBA', (w, h)); t.putdata(src)
                im.paste(t.resize((w * 2, h * 2), Image.NEAREST), (i * (w * 2 + 8), 0))
            im.save(out / 'pairs' / ('%s_psnr%.1f.png' % (k, q)))
    with open(out / 'look.tsv', 'w') as f:
        f.write('key\thow\tw\th\tpsnr_db\tmax_err\tnote\n')
        for x in rows:
            f.write('\t'.join(str(v) for v in x[:6]) + '\t' + (x[6] if isinstance(x[6], str) else '') + '\n')
    conv = [x for x in rows if x[1].startswith('raw16') and x[4] > 0]
    kept = sum(1 for x in rows if x[6] == 'base kept'); changed = sum(1 for x in rows if x[6] == 'BASE CHANGED')
    print('keys %d: base kept %d, BASE CHANGED %d; raw16->vq %d, PSNR min %.1f median %.1f dB; pairs %d' % (
        len(rows), kept, changed, len(conv), min((x[4] for x in conv), default=0),
        sorted(x[4] for x in conv)[len(conv) // 2] if conv else 0, len(sq)))


if __name__ == '__main__':
    main()
