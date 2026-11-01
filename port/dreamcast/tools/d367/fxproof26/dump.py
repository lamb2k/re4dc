"""dump.py <out.png> [gc:<key> | ps2:<member>:<tpl off hex>:<frame>] ... -> contact sheet (128px tiles, checker bg)."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, '/root/work/lanes/fxproof26')
T = '/root/work/lanes/fxproof26/wt/port/dreamcast/tools'
sys.path[:0] = [T, T + '/d367/vram', T + '/d367/test12fx']
import fx_ps2_sheet as SH  # noqa
import ps2afs, ps2scan  # noqa

_gc = None


def gc_pic(key):
    global _gc
    if _gc is None:
        _gc = {}
        W = Path('/root/work/lanes/fxproof26/gc')
        for p in sorted(W.glob('*.das')):
            st = 'st2' if p.stem.startswith('r2') else 'st1'
            for ctx, l in SH.gc_pictures([('%s/%s' % (st, p.name), p)]).items():
                for k, w, h, px in l:
                    _gc.setdefault(k, (w, h, px))
    w, h, px = _gc[key]
    im = Image.new('RGBA', (w, h)); im.putdata([tuple(p) for p in px])
    return im


def ps2_pic(member, off, frame, full=False):
    b = ps2afs.read('BIO4DAT.AFS:' + member)
    import struct
    t = off
    magic, count, start = struct.unpack_from('<III', b, t)
    d = t + start + 0x30 * frame
    # re-decode to an image (same path as ps2scan.decode_tpl, keep the image)
    orig = ps2scan.sigs.sig_image
    got = {}
    ps2scan.sigs.sig_image = lambda im: got.setdefault(len(got), im) and b''
    try:
        r = ps2scan.decode_tpl(b, t)
    finally:
        ps2scan.sigs.sig_image = orig
    ks = [x[0] for x in r]
    return got[ks.index(frame)]


def main(out, items, box=128):
    tiles = []
    for it in items:
        if it.startswith('gc:'):
            im = gc_pic(it[3:])
        else:
            _, m, o, f = it.split(':')
            im = ps2_pic(m, int(o, 16), int(f))
        s = box / max(im.size)
        im = im.resize((max(1, int(im.size[0] * s)), max(1, int(im.size[1] * s))), Image.NEAREST)
        bg = SH.checker(box, box); bg.alpha_composite(im)
        d = ImageDraw.Draw(bg); d.text((2, 2), it[-24:], fill=(255, 0, 0, 255))
        tiles.append(bg)
    cols = min(8, len(tiles))
    sheet = Image.new('RGBA', (box * cols, box * ((len(tiles) + cols - 1) // cols)), (0, 0, 0, 255))
    for i, t in enumerate(tiles):
        sheet.paste(t, (box * (i % cols), box * (i // cols)))
    sheet.save(out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
