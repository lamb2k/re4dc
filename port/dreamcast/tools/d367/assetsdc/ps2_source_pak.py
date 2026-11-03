#!/usr/bin/env python3
"""ps2_source_pak.py --gc-root DIR --ps2-dir DIR --pak base/tex.pak --out DIR [--glob ...] [--dry] [--format-only]
(lane assets-dc, 2026-11-02: no GameCube asset, retroactively; every picture in Dreamcast form)

Batch 1 of the retroactive asset pass. For every dc/tex.pak package whose material is "source" (a picture keyed by a
GameCube TPL image identity), find the GC image in the shipped GC container (em/*.drs, st1/*.arc, ss, etc, op), match it
to the PS2 twin file's picture (ps2_tpl_pak.py matcher: NCC of premultiplied luma+alpha signatures, unique-best, MAE
bound) and ship "PS2 pixels under the GC key" in Dreamcast form:
  - >= 64x64: full-codebook VQ, with mips when square (PVR mips need square);
  - smaller: 16-bit twiddled, with mips when square (mipmap_twiddled);
  - the pixel format follows the base package (RGB565 / ARGB1555 / ARGB4444); dimensions are the base package's.
--format-only re-encodes the existing (GC-derived) pixels in Dreamcast form without a PS2 match (used only to measure).
Outputs: <out>/dc/tex.pak, pak-derived.json (changed keys), report.json (one row per source key, matched or why not).
Runtime knobs the output needs: CAST_MIPMAP=1 TEX_TWIDDLED_MIPMAP=1 (both already in the release recipe).
"""
import argparse, glob, hashlib, json, os, struct, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'purgeui24'))
import ps2_tpl_pak as tp      # noqa: E402  (sets the tool paths)
hp, tpl, ps2_tpl, texpack = tp.hp, tp.tpl, tp.ps2_tpl, tp.texpack
from vq_pak import read_pak, restamp  # noqa: E402
import mipmap_twiddled        # noqa: E402
sys.path.insert(0, str(HERE.parents[1]))
import room_smd               # noqa: E402


def read_gc(path):
    d = Path(path).read_bytes()
    if d[:32] == room_smd.CONTAINER_MAGIC:
        try:
            d = room_smd.decode_das(d)
        except ValueError as e:
            print('decode failed', path, e, flush=True)
    return d

PVRTEX = '/root/work/kos-re4dc-d336/utils/pvrtex/pvrtex'
DEFAULT_GLOBS = ['em/*', 'st1/*', 'st2/*', 'ss/*/*', 'etc/*', 'etc/*/*', 'op/*', 'evd/*', 'font/*']
FMT_NAME = {0: 'RGB565', 1: 'ARGB1555', 2: 'ARGB4444'}


def restamp_mip(old, new):
    import zlib
    sh, nh = list(tpl.HEADER.unpack_from(old)), list(tpl.HEADER.unpack_from(new))
    st, nt = list(tpl.TEXTURE.unpack_from(old, sh[5])), list(tpl.TEXTURE.unpack_from(new, nh[5]))
    nt[0], nt[6] = st[0], (st[6] & ~tpl.FLAG_MIPMAP) | (nt[6] & tpl.FLAG_MIPMAP)
    body = tpl.TEXTURE.pack(*nt) + new[nh[6]:]
    nh[8] = zlib.crc32(body) & 0xffffffff
    return tpl.HEADER.pack(*nh) + body


def twin(rel):
    b = os.path.basename(rel).lower()
    stem = b.rsplit('.', 1)[0]
    if rel.startswith('etc/') and b.endswith('.tpl'):
        return [b]
    return [stem + '.dat', stem + 'low.dat']


def base_info(pkg):
    h = tpl.HEADER.unpack_from(pkg)
    t = tpl.TEXTURE.unpack_from(pkg, h[5])
    name = t[0].split(b'\0')[0].decode('latin1')
    return name, t[1], t[2], t[3], t[6], t[7]   # material, w, h, format, flags, payload


def encode_dc(pixels, w, h, fmt, work, gim):
    """RGBA pixels (w*h, the GC picture's size = the base package's) -> native package in Dreamcast form."""
    square = w == h
    if w * h >= 64 * 64:
        png = work / 'in.png'
        im = Image.new('RGBA', (w, h)); im.putdata(pixels); im.save(png)
        dt = work / 'out.dt'
        if dt.exists():
            dt.unlink()
        cmd = [PVRTEX, '-i', str(png), '-o', str(dt), '-f', FMT_NAME[fmt], '-c'] + (['-m'] if square else [])
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        pkg, _ = tpl.package_existing_vq(dt.read_bytes(), allow_mipmaps=square)
        return pkg, 'vq' + ('+mip' if square else '')
    # small: 16-bit twiddled like the stager builds it (texture prep), + mips when square
    pkg16, _ = tpl.build_package([gim], [tpl.MaterialBinding('source', 0, None)], twiddle=True, pad_to_power_of_two=True,
                                 source_intensity_alpha=True, source_pixels={0: pixels})
    t = tpl.TEXTURE.unpack_from(pkg16, tpl.HEADER.unpack_from(pkg16)[5])
    if t[3] != fmt:
        raise RuntimeError('prep format %d != base %d' % (t[3], fmt))
    if square:
        pkg16, _ = mipmap_twiddled.add_mipmaps(pkg16, enabled=True)
        return pkg16, 'tw16+mip'
    return pkg16, 'tw16'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gc-root', required=True)
    ap.add_argument('--ps2-dir', required=True)
    ap.add_argument('--pak', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--glob', action='append')
    ap.add_argument('--min-ncc', type=float, default=0.97)
    ap.add_argument('--margin', type=float, default=0.03)
    ap.add_argument('--max-mae', type=float, default=30.0)
    ap.add_argument('--min-side', type=int, default=8, help='only convert pictures with both sides >= this (raw16 small UI-ish pictures stay)')
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--align-mae', type=float, default=5.0)
    ap.add_argument('--only-keys', help='convert only these keys (one per line)')
    ap.add_argument('--ps2-size', action='store_true', help='keep the PS2 picture at its own size (power of two, >= 64x64 '
                    'pictures, VQ) and set header flags bit 29 (runtime PKG_PS2_SIZE=1: whole picture, scaled)')
    ap.add_argument('--skip-keys', help='keys never touched (one per line): already PS2-proven pictures (HUD, fonts, pics sets)')
    a = ap.parse_args()
    G, P, O = Path(a.gc_root), Path(a.ps2_dir), Path(a.out)
    (O / 'dc').mkdir(parents=True, exist_ok=True)
    base = Path(a.pak).read_bytes()
    pkgs = read_pak(base)
    skip = set(l.split()[0] for l in open(a.skip_keys) if l.strip()) if a.skip_keys else set()
    only = set(l.split()[0] for l in open(a.only_keys) if l.strip()) if a.only_keys else None
    src = {k for k, v in pkgs.items() if base_info(v)[0] == 'source' and '%08x-%08x' % k not in skip
           and (only is None or '%08x-%08x' % k in only)}
    rows, files, done, seen = [], [], set(), set()
    work = Path(tempfile.mkdtemp(prefix='psp-', dir=str(O)))
    for g in a.glob or DEFAULT_GLOBS:
        for f in sorted(glob.glob(str(G / g))):
            if not os.path.isfile(f):
                continue
            if not os.path.isfile(f):
                continue
            rel = os.path.relpath(f, G).replace(os.sep, '/')
            gims = tp.gc_images(read_gc(f))
            mine = []
            for off, n, gim in gims:
                key = hp.identity(gim)
                kt = tuple(int(x, 16) for x in key.split('-'))
                if kt in src and key not in seen:
                    seen.add(key); mine.append((off, n, gim, key, kt))
            frow = dict(file=rel, gc_images=len(gims), source_keys=len(mine), replaced=0)
            files.append(frow)
            if not mine:
                continue
            pimgs = []
            twins = []
            for pn in twin(rel):
                if (P / pn).exists() and (P / pn).stat().st_size:
                    twins.append((pn, hashlib.sha256((P / pn).read_bytes()).hexdigest()))
                    for t_i, (_o, ims) in enumerate(ps2_tpl.find_all((P / pn).read_bytes())):
                        for i_i, im in enumerate(ims):
                            pimgs.append(dict(im, tpl=(pn, t_i), idx=i_i))
            # the PS2 often stores a tall picture transposed (64x128 -> 128x64): offer each non-square PS2 picture
            # transposed too (the same texels, 11-03 r203/r207 rows)
            from PIL import Image as _I
            for q in list(pimgs):
                if q['width'] != q['height']:
                    t = tp.rgba(q['width'], q['height'], q['rgba']).transpose(_I.TRANSPOSE)
                    pimgs.append(dict(q, width=q['height'], height=q['width'], rgba=list(t.getdata()),
                                      transposed=True))
            gc_tpls = sorted({o for o, _n, _g in gims})
            frow['ps2_images'] = len(pimgs)
            psig = [tp.signature(tp.rgba(q['width'], q['height'], q['rgba'])) for q in pimgs]
            for k_i, (off, n, gim, key, kt) in enumerate(mine):
                mat, bw, bh, bfmt, bfl, bpay = base_info(pkgs[kt])
                row = dict(key=key, file=rel, tpl_offset=off, image=n, gc_size=[gim.width, gim.height],
                           base=[bw, bh, bfmt, bpay, bfl & 4])
                if min(bw, bh) < a.min_side:
                    row['note'] = 'below min side'; rows.append(row); continue
                if (bw, bh) != (gim.width, gim.height) or bfmt > 2:
                    row['note'] = 'base layout differs (padded or palettised): left'; rows.append(row); continue
                gimg = tp.rgba(gim.width, gim.height, tpl.decode_image(gim))
                gs = tp.signature(gimg)
                ga = gim.width / gim.height
                import operator
                sc = [sum(map(operator.mul, gs, v)) if (gs and v) else -1.0 for v in psig]
                cand = sorted(((float(sc[j]), j) for j, q in enumerate(pimgs)
                               if max(ga, q['width'] / q['height']) / min(ga, q['width'] / q['height']) <= 2.01), reverse=True)
                if not cand or gs is None:
                    row['note'] = 'no PS2 picture' if gs is not None else 'flat GC picture'; rows.append(row); continue
                score, j = cand[0]
                second = cand[1][0] if len(cand) > 1 else -1.0
                pim = pimgs[j]
                r = hp.premul_resize(tp.rgba(pim['width'], pim['height'], pim['rgba']), (gim.width, gim.height))
                row.update(ps2_index=j, ps2_size=[pim['width'], pim['height']], ncc=round(score, 3),
                           second=round(second, 3), mae=round(tp.mae(r, gimg), 2))
                twin_dup = len(cand) > 1 and tp.ncc(psig[j], psig[cand[1][1]]) >= 0.995
                if score < a.min_ncc or row['mae'] > a.max_mae or (score - second < a.margin and not twin_dup):
                    # flat pictures tie on NCC: accept the PS2 picture at the same TPL / image index when it is near
                    # identical (MAE <= --align-mae), as stored or transposed
                    al = [jj for jj, q in enumerate(pimgs) if q.get('tpl', (None, -1))[1] == gc_tpls.index(off)
                          and q.get('idx') == n and (q['width'], q['height']) == (gim.width, gim.height)]
                    al = [(tp.mae(tp.rgba(pimgs[jj]['width'], pimgs[jj]['height'], pimgs[jj]['rgba']), gimg), jj) for jj in al]
                    al = sorted(x for x in al if x[0] <= a.align_mae)
                    if not al:
                        row['note'] = 'no unique PS2 picture'; rows.append(row); continue
                    j = al[0][1]; pim = pimgs[j]
                    r = tp.rgba(pim['width'], pim['height'], pim['rgba'])
                    row.update(ps2_index=j, ps2_size=[pim['width'], pim['height']], mae=round(al[0][0], 2), aligned=True)
                row['transposed'] = bool(pim.get('transposed'))
                if a.dry:
                    row['note'] = 'dry-match'; rows.append(row); continue
                pw, ph = pim['width'], pim['height']
                native = (a.ps2_size and (pw, ph) != (bw, bh) and pw * ph >= 64 * 64 and max(pw, ph) <= 1024
                          and not (pw & (pw - 1)) and not (ph & (ph - 1)))
                try:
                    if native:
                        enc, how = encode_dc(list(tp.rgba(pw, ph, pim['rgba']).getdata()), pw, ph, bfmt, work, gim)
                        how += ' ps2size'
                    else:
                        enc, how = encode_dc(list(r.getdata()), bw, bh, bfmt, work, gim)
                except Exception as e:  # noqa: BLE001
                    row['note'] = 'encode failed: %s' % e; rows.append(row); continue
                final = restamp_mip(pkgs[kt], enc)
                if native:
                    hh = list(tpl.HEADER.unpack_from(final)); hh[10] |= 1 << 29   # Header.flags: whole picture, scaled
                    final = tpl.HEADER.pack(*hh) + final[tpl.HEADER.size:]
                row.update(how=how, before=len(pkgs[kt]), after=len(final), sha256=hashlib.sha256(final).hexdigest(),
                           ps2_file=pim['tpl'][0], ps2_file_sha256=dict(twins)[pim['tpl'][0]], ps2_tpl=pim['tpl'][1], ps2_image=pim['idx'])
                pkgs[kt] = final; done.add(key); frow['replaced'] += 1
                rows.append(row)
            print('%-24s gc %4d source %4d ps2 %4d replaced %4d' % (rel, frow['gc_images'], frow['source_keys'],
                                                                     frow.get('ps2_images', 0), frow['replaced']), flush=True)
    notfound = sorted('%08x-%08x' % k for k in src if '%08x-%08x' % k not in seen)
    if not a.dry:
        blob, _ = texpack.build(pkgs)
        texpack.verify(blob)
        (O / 'dc' / 'tex.pak').write_bytes(blob)
        sha = lambda b: hashlib.sha256(b).hexdigest()
        (O / 'pak-derived.json').write_text(json.dumps(dict(base=sha(base), out=sha(blob), count=len(pkgs), added=[],
                                                              changed=sorted(done)), indent=1) + '\n')
    (O / 'report.json').write_text(json.dumps(dict(base_pak=a.pak, source_keys=len(src), located=len(seen),
                                                    not_located=notfound, files=files, rows=rows), indent=1) + '\n')
    import collections
    print('source keys', len(src), 'located', len(seen), 'replaced', len(done))
    print(collections.Counter(r.get('note', r.get('how')) for r in rows).most_common())


if __name__ == '__main__':
    main()
