"""PS2 scenario TPL decoder, retained from the September 2026 world converter.

Uses the existing JADERLINK interlace decoder (MIT, copyright 2023 JADERLINK).
See LICENSE-JADERLINK.txt and README.md. No game data or private paths required.
Output convention: top row first, alpha = min(255, alpha * 255 // 128).
"""
import json
import struct
import zlib
from pathlib import Path

def write_png(path, w, h, rgba):
    """rgba: bytes/bytearray of w*h*4 (top row first)."""
    raw = bytearray()
    stride = w * 4
    for y in range(h):
        raw.append(0)
        raw += rgba[y * stride:(y + 1) * stride]

    def chunk(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    data = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) + \
        chunk(b'IDAT', zlib.compress(bytes(raw), 9)) + chunk(b'IEND', b'')
    Path(path).write_bytes(data)
    return data

HDR = struct.Struct('<HHHHHHHHIIQIIQ')

def parse_header(d, off):
    f = HDR.unpack_from(d, off)
    keys = ('width', 'height', 'bitdepth', 'interlace', 'next', 'mipmap_status', 'qwc', 'ref',
            'mip1_off', 'mip2_off', 'gs_miptbp', 'index_off', 'palette_off', 'gs_tex0')
    h = dict(zip(keys, f))
    h['header_off'] = off
    return h

def parse_tpl(d):
    magic, count, start, unk = struct.unpack_from('<IIII', d, 0)
    if magic != 0x1000:
        raise ValueError('not an RE4 PS2 TPL (magic 0x%x)' % magic)
    entries = []
    for i in range(count):
        h = parse_header(d, start + 0x30 * i)
        h['mips'] = []
        if h['mipmap_status'] == 2:
            for k in ('mip1_off', 'mip2_off'):
                if h[k]:
                    m = parse_header(d, h[k])
                    m['palette_off'] = h['palette_off']       # mips share the base CLUT (JADERLINK)
                    h['mips'].append(m)
        entries.append(h)
    return dict(magic=magic, count=count, start=start, unk=unk, entries=entries)

def tex0_fields(v):
    return dict(TBP0=v & 0x3fff, TBW=(v >> 14) & 0x3f, PSM=(v >> 20) & 0x3f, TW=(v >> 26) & 0xf,
                TH=(v >> 30) & 0xf, TCC=(v >> 34) & 1, TFX=(v >> 35) & 3, CBP=(v >> 37) & 0x3fff,
                CPSM=(v >> 51) & 0xf, CSM=(v >> 55) & 1, CSA=(v >> 56) & 0x1f, CLD=(v >> 61) & 7)

def alpha8(a):
    return 255 if a >= 128 else (a * 255) // 128

def clut(d, off, n, raw_alpha=False):
    """-> list of (r, g, b, a_out, a_raw)."""
    out = []
    if n == 16:
        for i in range(16):
            p = off + (i * 4 if i < 8 else 0x40 + (i - 8) * 4)
            r, g, b, a = d[p:p + 4]
            out.append((r, g, b, a if raw_alpha else alpha8(a), a))
    else:
        for i in range(256):
            j = i
            if (i & 0x18) == 0x08:
                j = i + 8
            elif (i & 0x18) == 0x10:
                j = i - 8
            p = off + j * 4
            r, g, b, a = d[p:p + 4]
            out.append((r, g, b, a if raw_alpha else alpha8(a), a))
    return out

_P8 = [  # preenche8 (flipInX False): byte index i -> ((dx_hi, dy_hi), (dx_lo, dy_lo)); hi = b >> 4, lo = b & 15
    ((0x4, 2), (0x0, 0)), ((0xC, 2), (0x8, 0)), ((0x14, 2), (0x10, 0)), ((0x1C, 2), (0x18, 0)),
    ((0x5, 2), (0x1, 0)), ((0xD, 2), (0x9, 0)), ((0x15, 2), (0x11, 0)), ((0x1D, 2), (0x19, 0)),
    ((0x6, 2), (0x2, 0)), ((0xE, 2), (0xA, 0)), ((0x16, 2), (0x12, 0)), ((0x1E, 2), (0x1A, 0)),
    ((0x7, 2), (0x3, 0)), ((0xF, 2), (0xB, 0)), ((0x17, 2), (0x13, 0)), ((0x1F, 2), (0x1B, 0)),
    ((0x0, 2), (0x4, 0)), ((0x8, 2), (0xC, 0)), ((0x10, 2), (0x14, 0)), ((0x18, 2), (0x1C, 0)),
    ((0x1, 2), (0x5, 0)), ((0x9, 2), (0xD, 0)), ((0x11, 2), (0x15, 0)), ((0x19, 2), (0x1D, 0)),
    ((0x2, 2), (0x6, 0)), ((0xA, 2), (0xE, 0)), ((0x12, 2), (0x16, 0)), ((0x1A, 2), (0x1E, 0)),
    ((0x3, 2), (0x7, 0)), ((0xB, 2), (0xF, 0)), ((0x13, 2), (0x17, 0)), ((0x1B, 2), (0x1F, 0))]

_P8F = [  # preenche8 flipInX True
    ((0x0, 2), (0x4, 0)), ((0x8, 2), (0xC, 0)), ((0x10, 2), (0x14, 0)), ((0x18, 2), (0x1C, 0)),
    ((0x1, 2), (0x5, 0)), ((0x9, 2), (0xD, 0)), ((0x11, 2), (0x15, 0)), ((0x19, 2), (0x1D, 0)),
    ((0x2, 2), (0x6, 0)), ((0xA, 2), (0xE, 0)), ((0x12, 2), (0x16, 0)), ((0x1A, 2), (0x1E, 0)),
    ((0x3, 2), (0x7, 0)), ((0xB, 2), (0xF, 0)), ((0x13, 2), (0x17, 0)), ((0x1B, 2), (0x1F, 0)),
    ((0x4, 2), (0x0, 0)), ((0xC, 2), (0x8, 0)), ((0x14, 2), (0x10, 0)), ((0x1C, 2), (0x18, 0)),
    ((0x5, 2), (0x1, 0)), ((0xD, 2), (0x9, 0)), ((0x15, 2), (0x11, 0)), ((0x1D, 2), (0x19, 0)),
    ((0x6, 2), (0x2, 0)), ((0xE, 2), (0xA, 0)), ((0x16, 2), (0x12, 0)), ((0x1E, 2), (0x1A, 0)),
    ((0x7, 2), (0x3, 0)), ((0xF, 2), (0xB, 0)), ((0x17, 2), (0x13, 0)), ((0x1F, 2), (0x1B, 0))]

_P9 = [(0x0, 0), (0x4, 2), (0x8, 0), (0xC, 2), (0x1, 0), (0x5, 2), (0x9, 0), (0xD, 2),
       (0x2, 0), (0x6, 2), (0xA, 0), (0xE, 2), (0x3, 0), (0x7, 2), (0xB, 0), (0xF, 2),
       (0x4, 0), (0x0, 2), (0xC, 0), (0x8, 2), (0x5, 0), (0x1, 2), (0xD, 0), (0x9, 2),
       (0x6, 0), (0x2, 2), (0xE, 0), (0xA, 2), (0x7, 0), (0x3, 2), (0xF, 0), (0xB, 2)]

_P9F = [(0x4, 0), (0x0, 2), (0xC, 0), (0x8, 2), (0x5, 0), (0x1, 2), (0xD, 0), (0x9, 2),
        (0x6, 0), (0x2, 2), (0xE, 0), (0xA, 2), (0x7, 0), (0x3, 2), (0xF, 0), (0xB, 2),
        (0x0, 0), (0x4, 2), (0x8, 0), (0xC, 2), (0x1, 0), (0x5, 2), (0x9, 0), (0xD, 2),
        (0x2, 0), (0x6, 2), (0xA, 0), (0xE, 2), (0x3, 0), (0x7, 2), (0xB, 0), (0xF, 2)]

def unswizzle_jl(data, w, h, bits):
    """Port of JADERLINK TplImage.bitDepth8interlace2and3 / bitDepth9interlace2and3 (index output)."""
    if bits == 8:
        out = bytearray(w * h)
        xc = yc = 0
        flip = False
        for i in range(0, w * h, 32):
            tab = _P9F if flip else _P9
            for k in range(32):
                dx, dy = tab[k]
                x, y = xc + dx, yc + dy
                if x < w and y < h:
                    out[y * w + x] = data[i + k]
            xc += 16
            if xc >= w:
                xc = 0
                yc += 1
                if yc % 2 == 0:
                    yc += 2
                    flip = not flip
        return out
    # 4-bit: SimpleBitmap(height, width) -> internal width sw = h, height sh = w
    sw, sh = h, w
    tmp = bytearray(sw * sh)
    tmpset = bytearray(sw * sh)
    xc = yc = alt = lev = 0
    levmax = w // 16
    flip = False
    for i in range(0, w * h // 2, 32):
        tab = _P8F if flip else _P8
        for k in range(32):
            b = data[i + k]
            (hx, hy), (lx, ly) = tab[k]
            for (dx, dy), v in (((hx, hy), b >> 4), ((lx, ly), b & 15)):
                x, y = xc + dx, yc + dy
                j = y * sw + x                         # C# SimpleBitmap index (no per-axis bounds check)
                if 0 <= j < sw * sh:
                    tmp[j] = v; tmpset[j] = 1
                else:
                    raise IndexError('jl 4-bit write outside %dx%d at %d,%d' % (sw, sh, x, y))
        yc += 16
        lev += 1
        if lev == levmax:
            lev = 0
            alt += 1
            if alt % 2 == 0:
                alt += 2
                flip = not flip
            yc = alt
            if alt == 16:
                flip = False
                yc = alt = lev = 0
                xc += 32
    if w > 128 or h > 128:
        fix = bytearray(w * h)
        blocks = (w // 128) * (h // 128)
        cx = cy = sx = sy = 0
        for _ in range(blocks):
            for y in range(128):
                for x in range(128):
                    fix[(y + sy) * w + x + sx] = tmp[(y + cy) * sw + x + cx]
            sx += 128
            if sx >= w:
                sx = 0; sy += 128
            cy += 128
            if cy >= w:
                cy = 0; cx += 128
        return fix
    return tmp

def indices(d, h, swizzle='jl'):
    w, ht, bd, il = h['width'], h['height'], h['bitdepth'], h['interlace']
    if bd == 6:
        return None
    bits = 4 if bd == 8 else 8
    n = w * ht * bits // 8
    raw = d[h['index_off']:h['index_off'] + n]
    if len(raw) != n:
        raise ValueError('truncated index data')
    if il & 2:
        if swizzle != 'jl':
            raise ValueError('this repository helper supports the JADERLINK swizzle decoder only')
        return unswizzle_jl(raw, w, ht, 8 if bits == 8 else 4)
    if bits == 8:
        return bytearray(raw)
    out = bytearray(w * ht)
    for i, b in enumerate(raw):
        out[2 * i] = b & 15
        out[2 * i + 1] = b >> 4
    return out

def decode(d, h, swizzle='jl', raw_alpha=False):
    """-> (w, h, rgba bytearray, stats)"""
    w, ht, bd = h['width'], h['height'], h['bitdepth']
    if bd == 6:
        n = w * ht * 4
        raw = d[h['index_off']:h['index_off'] + n]
        rgba = bytearray(n)
        hist = {}
        for i in range(w * ht):
            r, g, b, a = raw[i * 4:i * 4 + 4]
            rgba[i * 4:i * 4 + 4] = bytes((r, g, b, a if raw_alpha else alpha8(a)))
            hist[a] = hist.get(a, 0) + 1
        return w, ht, rgba, dict(alpha_raw_hist=hist, colours=None)
    pal = clut(d, h['palette_off'], 16 if bd == 8 else 256, raw_alpha)
    idx = indices(d, h, swizzle)
    rgba = bytearray(w * ht * 4)
    hist = {}
    used = set()
    for i, k in enumerate(idx):
        r, g, b, a, ar = pal[k]
        rgba[i * 4:i * 4 + 4] = bytes((r, g, b, a))
        hist[ar] = hist.get(ar, 0) + 1
        used.add(k)
    return w, ht, rgba, dict(alpha_raw_hist=hist, clut_used=len(used), clut_size=len(pal),
                             clut=[list(p) for p in pal])

def describe(h):
    t = tex0_fields(h['gs_tex0'])
    return dict(width=h['width'], height=h['height'],
                format={8: 'PSMT4 4-bit, 16-colour CLUT', 9: 'PSMT8 8-bit, 256-colour CLUT',
                        6: 'PSMCT32'}.get(h['bitdepth'], '?%d' % h['bitdepth']),
                bitdepth_field=h['bitdepth'], interlace_field=h['interlace'],
                swizzled=bool(h['interlace'] & 2), rotate_flag=bool(h['interlace'] & 1),
                mipmap_status=h['mipmap_status'], index_off=h['index_off'], palette_off=h['palette_off'],
                qwc=h['qwc'], gs_tex0='0x%016X' % h['gs_tex0'], tex0=t)

def alpha_summary(hist):
    tot = sum(hist.values())
    zero = hist.get(0, 0)
    full = sum(v for a, v in hist.items() if a >= 0x80)
    over = sum(v for a, v in hist.items() if a > 0x80)
    part = tot - zero - full
    nonzero = sorted(a for a in hist if a != 0)
    if zero == 0 and part == 0:
        cls = 'opaque'
    elif len(nonzero) == 1:
        cls = 'binary cutout (raw 0x00 / 0x%02x only)' % nonzero[0]
    else:
        cls = 'graded (%d texels with 0 < a < 0x80; %d distinct raw values)' % (part, len(hist))
    return dict(texels=tot, a00=zero, a80_or_more=full, partial=part, above_0x80=over, class_=cls,
                raw_values=sorted(hist.items()))

def cmd_decode(tpl, out, entries=None, mips=False, raw_alpha=False, swizzle='jl'):
    d = Path(tpl).read_bytes()
    t = parse_tpl(d)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rep = dict(source=str(tpl), source_bytes=len(d), count=t['count'], swizzle=swizzle,
               alpha='raw GS (0x80 = 1.0)' if raw_alpha else 'rescaled: min(255, a*255//128)', textures=[])
    import hashlib
    rep['source_sha256'] = hashlib.sha256(d).hexdigest()
    for i, h in enumerate(t['entries']):
        if entries is not None and i not in entries:
            continue
        levels = [('', h)] + ([('_mip%d' % (k + 1), m) for k, m in enumerate(h['mips'])] if mips else [])
        for suf, hh in levels:
            w, ht, rgba, st = decode(d, hh, swizzle, raw_alpha)
            name = '%04d%s.png' % (i, suf)
            blob = write_png(out / name, w, ht, rgba)
            e = dict(entry=i, level=suf or 'base', file=name, png_bytes=len(blob),
                     rgba_sha256=hashlib.sha256(bytes(rgba)).hexdigest(), **describe(hh),
                     alpha=alpha_summary(st['alpha_raw_hist']))
            if 'clut_used' in st:
                e['clut_used'] = st['clut_used']; e['clut_size'] = st['clut_size']
                if suf == '':
                    e['clut_rgba_raw'] = [p[:3] + [p[4]] for p in st['clut']]
            rep['textures'].append(e)
    (out / 'decode-report.json').write_text(json.dumps(rep, indent=1))
    print('decoded %d images into %s' % (len(rep['textures']), out))
    return rep
