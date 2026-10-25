#!/usr/bin/env python3
"""ps2_tpl_pak.py --gc-root DIR --ps2-dir DIR --pak base/tex.pak --out DIR [--glob 'ss/*/*.tpl' ...] [--min-ncc 0.97] [--max-mae 30] [--margin 0.03] [--dry]
(lane purge-ui24, 2026-10-24; GC asset purge: sub screen ss/*, etc/*.tpl, op/*.das, etc/memcard.das)

Pictures of GameCube UI files become their PS2 twins' pictures, "PS2 pixels under the GC key" (no runtime change; same
as ps2_hud_pak.py). File pairs by name: the PS2 BIO4DAT.AFS member with the GC file's base name (lower case; .das ->
.dat: op01.das -> op01.dat, memcard.das -> memcard.dat). Every GC TPL image in the file whose identity key is in the base
pack is matched to the most similar PS2 TPL picture of the twin: normalised cross-correlation of 24x24 premultiplied
luma + alpha signatures, aspect ratios within 2x; it is replaced when the best NCC is >= --min-ncc and either beats the
runner-up by --margin or is the picture at the same index (equal-order files), and the mean absolute RGBA difference
is <= --max-mae (low-contrast dark pictures correlate on noise). The replacement is
the PS2 picture resampled to the GC picture's size (model and screen UVs address the whole picture), packaged by the
texture prep and encoded like the base package (VQ when the base is VQ; a palettised base package is reported and left,
since a 16-bit replacement would grow VRAM). Outputs as ps2_hud_pak.py: dc/tex.pak, pak-derived.json, report.json.
"""
import argparse, glob, hashlib, json, os, struct, sys, tempfile
from pathlib import Path
from PIL import Image
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ps2_hud_pak as hp     # noqa: E402  (sets the tool paths)
tpl, ps2_tpl, vq, texpack = hp.tpl, hp.ps2_tpl, hp.vq, hp.texpack
from vq_pak import read_pak, restamp  # noqa: E402

DEFAULT_GLOBS = ['ss/*/*.tpl', 'ss/*/*.dat', 'etc/*.tpl', 'etc/memcard.das', 'op/*.das']


def gc_images(b):
    mag = struct.pack('>I', tpl.TPL_MAGIC)
    out, i = [], b.find(mag)
    while i >= 0:
        try:
            for n, im in enumerate(tpl.parse_tpl(b[i:])):
                out.append((i, n, im))
        except (ValueError, struct.error, IndexError):
            pass
        i = b.find(mag, i + 4)
    return out


def rgba(w, h, px):
    im = Image.new('RGBA', (w, h)); im.putdata(px); return im


def mae(a, b):
    pa, pb = list(a.getdata()), list(b.getdata())
    return sum(abs(x - y) for p, q in zip(pa, pb) for x, y in zip(p, q)) / (4.0 * len(pa))


SIG = 24


def signature(img):
    """Zero-mean, unit-norm luma + alpha vector of the picture at SIG x SIG (premultiplied)."""
    s = hp.premul_resize(img, (SIG, SIG))
    v = []
    for r, g, b, a in s.getdata():
        v.append((0.3 * r + 0.59 * g + 0.11 * b) * a / 255.0)
    v += [a for _r, _g, _b, a in s.getdata()]
    m = sum(v) / len(v)
    v = [x - m for x in v]
    n = sum(x * x for x in v) ** 0.5
    return [x / n for x in v] if n > 1e-6 else None


def ncc(a, b):
    return sum(x * y for x, y in zip(a, b)) if a and b else -1.0


def encode_like(old, gim, pixels, pvrtex, key):
    pkg16, _ = tpl.build_package([gim], [tpl.MaterialBinding('source', 0, None)], twiddle=True,
                                 pad_to_power_of_two=True, source_intensity_alpha=True, source_pixels={0: pixels})
    ot = tpl.TEXTURE.unpack_from(old, tpl.HEADER.unpack_from(old)[5])
    nt = tpl.TEXTURE.unpack_from(pkg16, tpl.HEADER.unpack_from(pkg16)[5])
    if (nt[1], nt[2]) != (ot[1], ot[2]):
        return None, 'native size %s != base %s' % (nt[1:3], ot[1:3])
    if ot[7] == tpl.PAYLOAD_VQ:
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); (td / 'in').mkdir(); (td / 'out').mkdir()
            (td / 'in' / (key + '.re4tex')).write_bytes(pkg16)
            vq.encode(key, td / 'in', td / 'out', pvrtex, (gim.width, gim.height), td)
            enc = (td / 'out' / (key + '.re4tex')).read_bytes()
    elif ot[3] in (tpl.FORMAT_PAL4_ARGB4444, tpl.FORMAT_PAL8_ARGB4444):
        return None, 'palettised base (format %d): left' % ot[3]
    else:
        enc = pkg16
    final, _ = restamp(old, enc)
    if len(final) > len(old):
        return None, 'replacement larger than the base (%d > %d): left' % (len(final), len(old))
    return final, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gc-root', required=True)
    ap.add_argument('--ps2-dir', required=True)
    ap.add_argument('--pak', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--glob', action='append')
    ap.add_argument('--min-ncc', type=float, default=0.97)
    ap.add_argument('--margin', type=float, default=0.03)
    ap.add_argument('--max-mae', type=float, default=30.0, help='also bound the whole-picture RGBA difference (dark pictures)')
    ap.add_argument('--skip-keys', help='file of keys owned elsewhere (e.g. the HUD set)')
    ap.add_argument('--pvrtex', default=vq.PVRTEX)
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    G, P, O = Path(a.gc_root), Path(a.ps2_dir), Path(a.out)
    (O / 'dc').mkdir(parents=True, exist_ok=True)
    base = Path(a.pak).read_bytes()
    pkgs = read_pak(base)
    skip = set(l.split()[0] for l in open(a.skip_keys)) if a.skip_keys else set()
    rows, files, done = [], [], set()
    for g in a.glob or DEFAULT_GLOBS:
        for f in sorted(glob.glob(str(G / g), recursive=True)):
            rel = os.path.relpath(f, G).replace(os.sep, '/')
            pn = os.path.basename(rel).lower()
            pn = pn[:-4] + '.dat' if pn.endswith('.das') else pn
            gb = Path(f).read_bytes()
            gims = gc_images(gb)
            frow = dict(file=rel, ps2=pn, gc_images=len(gims), in_pak=0, replaced=0)
            files.append(frow)
            if not gims:
                continue
            pp = P / pn
            if not pp.exists():
                frow['note'] = 'no PS2 twin'
                continue
            pimgs = [im for _o, ims in ps2_tpl.find_all(pp.read_bytes()) for im in ims]
            frow['ps2_images'] = len(pimgs)
            psig = [signature(rgba(q['width'], q['height'], q['rgba'])) for q in pimgs]
            for k_i, (off, n, gim) in enumerate(gims):
                key = hp.identity(gim)
                kt = tuple(int(x, 16) for x in key.split('-'))
                if kt not in pkgs or key in skip or key in done:
                    continue
                frow['in_pak'] += 1
                gimg = rgba(gim.width, gim.height, tpl.decode_image(gim))
                gs = signature(gimg)
                ga = gim.width / gim.height
                cand = []
                for j, q in enumerate(pimgs):
                    pa = q['width'] / q['height']
                    if max(ga, pa) / min(ga, pa) > 2.01:   # PS2 halves/doubles a side at most
                        continue
                    cand.append((ncc(gs, psig[j]), j))
                cand.sort(reverse=True)
                row = dict(key=key, file=rel, tpl_offset=off, image=n, gc_size=[gim.width, gim.height])
                if not cand or gs is None:
                    row['note'] = 'no PS2 picture' if gs is not None else 'flat GC picture'; rows.append(row); continue
                score, j = cand[0]
                second = cand[1][0] if len(cand) > 1 else -1.0
                pim = pimgs[j]
                r = hp.premul_resize(rgba(pim['width'], pim['height'], pim['rgba']), (gim.width, gim.height))
                row.update(ps2_index=j, ps2_size=[pim['width'], pim['height']], ncc=round(score, 3),
                           second=round(second, 3), mae=round(mae(r, gimg), 2))
                # a runner-up that is the same picture (PS2 files repeat pictures) is no ambiguity
                twin = len(cand) > 1 and ncc(psig[j], psig[cand[1][1]]) >= 0.995
                if score < a.min_ncc or row['mae'] > a.max_mae or (score - second < a.margin and j != k_i and not twin):
                    row['note'] = 'no unique PS2 picture (ncc %.2f, second %.2f)' % (score, second); rows.append(row); continue
                if a.dry:
                    row['note'] = 'dry'; rows.append(row); continue
                final, why = encode_like(pkgs[kt], gim, list(r.getdata()), a.pvrtex, key)
                if final is None:
                    row['note'] = why; rows.append(row); continue
                pkgs[kt] = final; done.add(key); frow['replaced'] += 1
                row.update(bytes=len(final), sha256=hashlib.sha256(final).hexdigest())
                rows.append(row)
            print('%-24s gc %3d in-pak %3d replaced %3d %s' % (rel, frow['gc_images'], frow['in_pak'], frow['replaced'],
                                                          frow.get('note', '')))
    sha = lambda b: hashlib.sha256(b).hexdigest()
    if not a.dry:
        blob, _ = texpack.build(pkgs)
        texpack.verify(blob)
        (O / 'dc' / 'tex.pak').write_bytes(blob)
        (O / 'pak-derived.json').write_text(json.dumps(dict(base=sha(base), out=sha(blob), count=len(pkgs), added=[],
                                                              changed=sorted(done)), indent=1) + '\n')
    (O / 'report.json').write_text(json.dumps(dict(base_pak=a.pak, min_ncc=a.min_ncc, margin=a.margin, files=files, rows=rows), indent=1) + '\n')
    print('replaced', len(done), 'of', sum(f['in_pak'] for f in files), 'in-pack pictures')


if __name__ == '__main__':
    main()
