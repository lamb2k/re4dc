#!/usr/bin/env python3
"""ps2_ui_map_pak.py --gc-root DIR --ps2-dir DIR --pak base/tex.pak --out DIR [--map ps2_ui_map.tsv] [--dry]
(lane castle-ps2-26, 2026-10-26; GC asset purge: the title and save-screen pictures purge-ui24's automatic matcher left)

ps2_tpl_pak.py pairs GC and PS2 UI pictures automatically and leaves a picture when the match is not unique or the
pixels differ too much. The title screen (ss/Eng/title.dat) and save screen (ss/Cmn/save_*.dat) pictures it left are
paired here by hand in ps2_ui_map.tsv (GC key, GC file, PS2 BIO4DAT member, PS2 picture index, turn, what). PS2
stores some tall pictures squashed (the "4" logos: plain resample) and some turned (save-screen bar: 90; handle:
transpose), so the row names the turn (0/90/270/transpose; "auto" picks 0/90/270 by signature correlation), optionally
followed by +crop:x0,y0,x1,y1 and +ink (the crisp Sofdec logo exists on PS2 only inside the black-on-white splash
picture: cropped, darkness -> alpha) or +onblack. The GC image must hash to the key
(refuses a wrong source); the PS2 picture is rotated, resampled to the GC picture's size and packaged/encoded like the
base package (ps2_tpl_pak.encode_like: same size, format and payload kind; never larger). Same outputs as
ps2_tpl_pak.py: dc/tex.pak, pak-derived.json (changed keys), report.json, previews/<key>-{gc,ps2}.png.
"""
import argparse, hashlib, json, sys
from pathlib import Path
from PIL import Image
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ps2_tpl_pak as tp  # noqa: E402
hp, tpl, ps2_tpl, vq, texpack = tp.hp, tp.tpl, tp.ps2_tpl, tp.vq, tp.texpack
from vq_pak import read_pak  # noqa: E402

ROT = {'0': None, '90': Image.Transpose.ROTATE_90, '270': Image.Transpose.ROTATE_270, 'transpose': Image.Transpose.TRANSPOSE}


def prep(img, ops):
    """Row operations before the turn: crop:x0,y0,x1,y1 (then trimmed to the ink), ink (a dark-on-white splash picture
    becomes a white picture whose alpha is the darkness, the GC logo's form), onblack (composited on opaque black, for a GC
picture that is opaque black-backed: the blurred title "resident evil")."""
    for op in ops:
        if op.startswith('crop:'):
            img = img.crop(tuple(int(v) for v in op[5:].split(',')))
        elif op == 'ink':
            px = [(255, 255, 255, 255 - int(0.3 * r + 0.59 * g + 0.11 * b)) for r, g, b, _a in img.getdata()]
            img = Image.new('RGBA', img.size); img.putdata(px)
            img = img.crop(img.getchannel('A').point(lambda a: 255 if a > 8 else 0).getbbox())
        elif op == 'onblack':
            bg = Image.new('RGBA', img.size, (0, 0, 0, 255)); bg.alpha_composite(img); img = bg
        else:
            raise ValueError('unknown op ' + op)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gc-root', required=True)
    ap.add_argument('--ps2-dir', required=True)
    ap.add_argument('--pak', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--map', default=str(HERE / 'ps2_ui_map.tsv'))
    ap.add_argument('--pvrtex', default=vq.PVRTEX)
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    G, P, O = Path(a.gc_root), Path(a.ps2_dir), Path(a.out)
    (O / 'dc').mkdir(parents=True, exist_ok=True)
    (O / 'previews').mkdir(exist_ok=True)
    base = Path(a.pak).read_bytes()
    pkgs = read_pak(base)
    rows, done, cache = [], [], {}
    for line in open(a.map):
        if not line.strip() or line.startswith(('#', 'key\t')):
            continue
        key, gfile, pfile, pidx, rot, what = line.rstrip('\n').split('\t')
        kt = tuple(int(x, 16) for x in key.split('-'))
        gim = next((im for _o, _n, im in tp.gc_images((G / gfile).read_bytes()) if hp.identity(im) == key), None)
        assert gim is not None, ('GC key not in file', key, gfile)
        if pfile not in cache:
            cache[pfile] = [im for _o, ims in ps2_tpl.find_all((P / pfile).read_bytes()) for im in ims]
        q = cache[pfile][int(pidx)]
        gimg = tp.rgba(gim.width, gim.height, tpl.decode_image(gim))
        rot, *ops = rot.split('+')
        pimg = prep(tp.rgba(q['width'], q['height'], q['rgba']), ops)
        gs = tp.signature(gimg)
        tries = ROT if rot == 'auto' else {rot: ROT[rot]}
        best = max(((tp.ncc(gs, tp.signature(pimg.transpose(t) if t else pimg)), r) for r, t in tries.items()))
        src = pimg.transpose(ROT[best[1]]) if ROT[best[1]] else pimg
        r = hp.premul_resize(src, (gim.width, gim.height))
        gimg.save(O / 'previews' / ('%s-gc.png' % key)); r.save(O / 'previews' / ('%s-ps2.png' % key))
        row = dict(key=key, file=gfile, ps2=pfile, ps2_index=int(pidx), rotate=best[1], ops=ops, ncc=round(best[0], 3),
                   gc_size=[gim.width, gim.height], ps2_size=[q['width'], q['height']], what=what)
        if kt not in pkgs:
            row['note'] = 'key not in base pack'
        elif not a.dry:
            final, why = tp.encode_like(pkgs[kt], gim, list(r.getdata()), a.pvrtex, key)
            if final is None:
                row['note'] = why
            else:
                pkgs[kt] = final; done.append(key)
                row.update(bytes=len(final), sha256=hashlib.sha256(final).hexdigest())
        rows.append(row)
        print('%s %-18s P%-3s rot %-3s ncc %.3f %s' % (key, gfile, pidx, best[1], best[0], row.get('note', 'ok' if not a.dry else 'dry')))
    sha = lambda b: hashlib.sha256(b).hexdigest()
    if not a.dry:
        blob, _ = texpack.build(pkgs)
        texpack.verify(blob)
        (O / 'dc' / 'tex.pak').write_bytes(blob)
        (O / 'pak-derived.json').write_text(json.dumps(dict(base=sha(base), out=sha(blob), count=len(pkgs), added=[],
                                                              changed=sorted(done)), indent=1) + '\n')
    (O / 'report.json').write_text(json.dumps(dict(base_pak=a.pak, map=a.map, rows=rows), indent=1) + '\n')
    print('replaced', len(done), 'of', len(rows))


if __name__ == '__main__':
    main()
