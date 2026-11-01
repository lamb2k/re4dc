"""Every PS2 TPL picture in BIO4DAT.AFS -> 16x16 signature (lane fxproof26).

  ps2scan.py <out prefix>   writes <out>.sig (1024 bytes per picture) and <out>.tsv (one location row per picture)

Scans every 16-aligned PS2 TPL header (magic 0x1000) in every non-audio BIO4DAT member (room/Core/em/wep .dat with
every entry incl. EFF and ETM members, standalone .tpl/.eff), decodes PSMT4/PSMT8 (+GS swizzle, transpose) the way
fx_ps2_pack.ps2_eff_textures does, and records member | dat entry[/ETM member] | TPL offset | frame | size | depth.
Also records the EFF id of the picture when the TPL is an EFF texture-table slot (eff-id column).
"""
import struct, sys, bisect
from PIL import Image
sys.path.insert(0, '/root/work/lanes/fxproof26')
sys.path.insert(0, '/root/work/lanes/fxproof26/wt/port/dreamcast/tools/d367/test12fx')
import ps2afs, ps2etm, sigs
import fx_ps2_pack as F
GS = F.GS
SIZES = (8, 16, 32, 64, 128, 256, 512, 1024)
LO = bytes(i & 15 for i in range(256))
HI = bytes(i >> 4 for i in range(256))


def decode_tpl(b, t):
    magic, count, start = struct.unpack_from('<III', b, t)
    if magic != 0x1000 or not (0 < count <= 512) or not (0 < start < 0x4000):
        return None
    out = []
    for k in range(count):
        d = t + start + 0x30 * k
        if d + 0x30 > len(b):
            return out or None
        w, h, depth, inter = struct.unpack_from('<HHHH', b, d)
        io, po = struct.unpack_from('<II', b, d + 0x20)
        if w not in SIZES or h not in SIZES:
            return out or None
        if depth not in (8, 9) or inter & ~3:
            continue
        bits = 4 if depth == 8 else 8
        n = w * h * bits // 8
        if t + io + n > len(b) or t + po + (64 if bits == 4 else 1024) > len(b):
            continue
        raw = bytes(b[t + io:t + io + n])
        if inter & 2:
            idx = bytes(GS.unswizzle_gs(raw, w, h, bits))
        elif bits == 8:
            idx = raw
        else:
            ba = bytearray(2 * n); ba[0::2] = raw.translate(LO); ba[1::2] = raw.translate(HI); idx = bytes(ba)
        if bits == 4:
            pal = []
            for c in range(16):
                q = t + po + (c if c < 8 else 16 + c - 8) * 4
                r_, g_, b_, a_ = b[q:q + 4]
                pal += [r_, g_, b_, 255 if a_ >= 128 else a_ * 255 // 128]
            pal += [0] * (1024 - len(pal))
        else:
            pal = []
            for c in GS.clut(b, t + po, 256):
                pal += list(c[:4])
        im = Image.frombytes('P', (w, h), idx)
        im.putpalette(pal, 'RGBA')
        im = im.convert('RGBA')
        if inter & 1:   # stored transposed: picture (x, y) at (y, x)
            im = im.transpose(Image.TRANSPOSE)
        out.append((k, im.size[0], im.size[1], depth, sigs.sig_image(im)))
    return out


def eff_slots(b, o, e, loc_prefix):
    """{tpl absolute offset: eff id} for an EFF version 0xB block at b[o:e]."""
    res = {}
    try:
        hdr = struct.unpack_from('<12I', b, o)
        if hdr[0] != 0xB:
            return res
        n = struct.unpack_from('<I', b, o + hdr[1])[0]
        ids = [struct.unpack_from('<H', b, o + hdr[1] + 4 + 8 * i)[0] for i in range(n)]
        to = o + hdr[6]
        if n == 0 or hdr[6] == 0 or struct.unpack_from('<I', b, to)[0] != n:
            return res
        for i, tid in enumerate(ids):
            res[to + struct.unpack_from('<I', b, to + 4 + 4 * i)[0]] = tid
    except struct.error:
        pass
    return res


def main(out):
    fs, ft = open(out + '.sig', 'wb'), open(out + '.tsv', 'w')
    n = 0
    ents = ps2afs.entries()
    for k in sorted(ents):
        if not k.startswith('BIO4DAT.AFS:') or k.endswith(('.adx', '.snd', '.rel', '.esl', '.fnt')):
            continue
        b = ps2afs.read(k)
        nm = k.split(':')[1]
        slots, de, starts, etm = {}, None, [], {}
        if nm.endswith('.eff'):
            slots = eff_slots(b, 0, len(b), '')
        if nm.endswith('.dat'):
            try:
                de = F.dat_entries(b)
                if not de or de[0][1] > len(b) or any(o > len(b) for _, o, _ in de):
                    de = None
            except Exception:
                de = None
        if de:
            starts = [o for _, o, _ in de]
            for i, (ty, o, e) in enumerate(de):
                if ty == 'EFF':
                    slots.update(eff_slots(b, o, e, ''))
                if ty == 'ETM':
                    try:
                        for mn, _, a, z in ps2etm.members(b[o:e]):
                            etm.setdefault(i, []).append((o + a, o + z, mn))
                            if mn.endswith('.eff'):
                                slots.update(eff_slots(b, o + a, o + z, ''))
                    except struct.error:
                        pass

        def loc(t):
            if not de:
                return '-'
            i = bisect.bisect_right(starts, t) - 1
            s = '#%d:%s' % (i, de[i][0])
            for a, z, mn in etm.get(i, []):
                if a <= t < z:
                    return s + '/%s+%#x' % (mn, t - a)
            return s + '+%#x' % (t - de[i][1])
        pos = 0
        while True:
            t = b.find(b'\x00\x10\x00\x00', pos)
            if t < 0:
                break
            pos = t + 4
            if t % 16:
                continue
            try:
                r = decode_tpl(b, t)
            except Exception:
                r = None
            for fr, w, h, depth, s in r or ():
                fs.write(s)
                eid = slots.get(t)
                ft.write('%s\t%s\t%#x\t%d\t%dx%d\t%d\t%s\n' % (nm, loc(t), t, fr, w, h, depth,
                                                              '-' if eid is None else '%#x' % eid))
                n += 1
    print('pictures', n)


if __name__ == '__main__':
    main(sys.argv[1])
