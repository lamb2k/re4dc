#!/usr/bin/env python3
"""RE4 PS2 TPL (scenario / SMD texture pack) -> RGBA PNG decoder. Python 3 standard library only.

Written 2026-09-26 for the D367 world agent (request 18, PS2 tree materials). Re-runnable:

  python3 ps2_tpl_decode.py info    <file.TPL>
  python3 ps2_tpl_decode.py decode  <file.TPL> <out_dir> [--entries 83,69,97] [--mips] [--raw-alpha]
                                     [--swizzle gs|jl]
  python3 ps2_tpl_decode.py compare <out_dir> <jaderlink_png_dir>      (pixel compare vs RE4_PS2_TPL_EXTRACT PNGs)
  python3 ps2_tpl_decode.py selftest <file.TPL>                         (GS-model vs JADERLINK-port swizzle, all entries)

Format (little endian), established from the TPL bytes plus JADERLINK RE4-PS2-TPL-TOOL B.1.1.1 (MIT) source:
  file header 16 B : u32 magic 0x00001000, u32 count, u32 first_entry_offset (0x10), u32 0
  entry header 48 B: u16 width, u16 height, u16 bitdepth, u16 interlace, u16 next, u16 mipmap_status,
                     u16 qwc, u16 ref, u32 mip1_hdr_off, u32 mip2_hdr_off, u64 gs_miptbp,
                     u32 index_off, u32 palette_off, u64 gs_tex0
  bitdepth 8 = 4-bit indices, 16-colour CLUT (GS PSMT4);  9 = 8-bit indices, 256-colour CLUT (PSMT8);
           6 = 32-bit direct colour (PSMCT32, unused in r101).
  interlace bit 0 = "rotate" flag (the TPL tool rotates on request; scenario TPLs are always used as stored,
           i.e. NOT rotated - JADERLINK README: the game does not honour it for scenario TPLs);
           bit 1 = GS swizzle (indices stored in PSMCT32 upload order; read back as PSMT4 / PSMT8).
  CLUT: RGBA8888 (PSMCT32).  16 colours: entries 0-7 at palette_off+0x00, 8-15 at +0x40 (8x2 CLUT in a
        16-wide buffer).  256 colours: CSM1 layout, blocks of 8 entries 8-15 <-> 16-23 swapped in each 32.
  Alpha: GS alpha, 0x80 = 1.0.  Output alpha = min(255, a * 255 // 128) (JADERLINK uses a*255/128 truncated,
        identical for a <= 0x80; values above 0x80 are clamped here and counted in the report).
  Pixels: row 0 = top of the image as stored in GS memory. The scenario OBJ written by
        RE4_PS2_SCENARIO_SMD_TOOL 1.3.0 uses vt = raw/255 with NO V flip, i.e. v = 0 is PNG row 0 (DirectX / GS /
        PVR convention). The texture coordinate itself is raw/256 (raw 256 = one full texture; it occurs), so
        sample at (vt_u*255/256, vt_v*255/256) with v measured from row 0 (vt/1 is 0.4 % too large).
        OpenGL-convention consumers must use v' = 1 - v (or flip the image).
Mipmaps: mip headers share the base palette; mip1/mip2 decode with the same rules.

Two independent swizzle decoders are provided (they must agree; `selftest` checks it):
  gs : a GS local-memory model (write the index bytes as a PSMCT32 rectangle, read back as PSMT4 / PSMT8,
       PCSX2 GSdx block / column tables);
  jl : a line-by-line port of JADERLINK's bitDepth8/9 interlace2 readers (the pipeline's existing decode,
       /root/probe/ps2-asset-experiment/r101/r101_004/*.PNG, came from that tool).
"""
import json
import struct
import sys
import zlib
from pathlib import Path

# ----------------------------------------------------------------------------------------------- PNG I/O


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


def read_png(path):
    """Minimal PNG reader: 8-bit greyscale(+A) / RGB(A) / palette, non-interlaced. -> (w, h, bytearray RGBA)."""
    d = Path(path).read_bytes()
    assert d[:8] == b'\x89PNG\r\n\x1a\n', path
    o = 8
    idat = bytearray()
    plte = trns = None
    while o < len(d):
        n, t = struct.unpack_from('>I4s', d, o)
        body = d[o + 8:o + 8 + n]
        if t == b'IHDR':
            w, h, bd, ct, _, _, il = struct.unpack('>IIBBBBB', body)
        elif t == b'PLTE':
            plte = body
        elif t == b'tRNS':
            trns = body
        elif t == b'IDAT':
            idat += body
        o += 12 + n
    assert bd == 8 and il == 0, (path, bd, il)
    ch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ct]
    raw = zlib.decompress(bytes(idat))
    stride = w * ch
    out = bytearray(w * h * ch)
    prev = bytearray(stride)
    p = 0
    for y in range(h):
        f = raw[p]; p += 1
        line = bytearray(raw[p:p + stride]); p += stride
        for i in range(stride):
            a = line[i - ch] if i >= ch else 0
            b = prev[i]
            c = prev[i - ch] if i >= ch else 0
            if f == 1:
                line[i] = (line[i] + a) & 255
            elif f == 2:
                line[i] = (line[i] + b) & 255
            elif f == 3:
                line[i] = (line[i] + ((a + b) >> 1)) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else (b if pb <= pc else c))) & 255
        out[y * stride:(y + 1) * stride] = line
        prev = line
    rgba = bytearray(w * h * 4)
    for i in range(w * h):
        if ct == 6:
            rgba[i * 4:i * 4 + 4] = out[i * 4:i * 4 + 4]
        elif ct == 2:
            rgba[i * 4:i * 4 + 3] = out[i * 3:i * 3 + 3]; rgba[i * 4 + 3] = 255
        elif ct == 0:
            rgba[i * 4:i * 4 + 3] = bytes([out[i]]) * 3; rgba[i * 4 + 3] = 255
        elif ct == 4:
            rgba[i * 4:i * 4 + 3] = bytes([out[i * 2]]) * 3; rgba[i * 4 + 3] = out[i * 2 + 1]
        else:
            k = out[i]
            rgba[i * 4:i * 4 + 3] = plte[k * 3:k * 3 + 3]
            rgba[i * 4 + 3] = trns[k] if trns and k < len(trns) else 255
    return w, h, rgba

# ----------------------------------------------------------------------------------------------- TPL parse


HDR = struct.Struct('<HHHHHHHHIIQIIQ')   # 48 bytes


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

# ----------------------------------------------------------------------------------------------- CLUT


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

# ----------------------------------------------------------------------------------------------- GS model

BT32 = [[0, 1, 4, 5, 16, 17, 20, 21], [2, 3, 6, 7, 18, 19, 22, 23],
        [8, 9, 12, 13, 24, 25, 28, 29], [10, 11, 14, 15, 26, 27, 30, 31]]
BT8 = BT32
BT4 = [[0, 2, 8, 10], [1, 3, 9, 11], [4, 6, 12, 14], [5, 7, 13, 15],
       [16, 18, 24, 26], [17, 19, 25, 27], [20, 22, 28, 30], [21, 23, 29, 31]]
CT32 = [[0, 1, 4, 5, 8, 9, 12, 13], [2, 3, 6, 7, 10, 11, 14, 15]]          # word in a 2x8 column
_C8 = [[0, 4, 16, 20, 32, 36, 48, 52, 2, 6, 18, 22, 34, 38, 50, 54],
       [8, 12, 24, 28, 40, 44, 56, 60, 10, 14, 26, 30, 42, 46, 58, 62],
       [33, 37, 49, 53, 1, 5, 17, 21, 35, 39, 51, 55, 3, 7, 19, 23],
       [41, 45, 57, 61, 9, 13, 25, 29, 43, 47, 59, 63, 11, 15, 27, 31]]
_C4 = [[0, 8, 32, 40, 64, 72, 96, 104, 2, 10, 34, 42, 66, 74, 98, 106,
        4, 12, 36, 44, 68, 76, 100, 108, 6, 14, 38, 46, 70, 78, 102, 110],
       [16, 24, 48, 56, 80, 88, 112, 120, 18, 26, 50, 58, 82, 90, 114, 122,
        20, 28, 52, 60, 84, 92, 116, 124, 22, 30, 54, 62, 86, 94, 118, 126],
       [65, 73, 97, 105, 1, 9, 33, 41, 67, 75, 99, 107, 3, 11, 35, 43,
        69, 77, 101, 109, 5, 13, 37, 45, 71, 79, 103, 111, 7, 15, 39, 47],
       [81, 89, 113, 121, 17, 25, 49, 57, 83, 91, 115, 123, 19, 27, 51, 59,
        85, 93, 117, 125, 21, 29, 53, 61, 87, 95, 119, 127, 23, 31, 55, 63]]


def _col_even_odd(base):
    """Even columns use `base`; odd columns swap the two 4-texel groups of every 8 (GS column layout)."""
    even = [list(r) for r in base]
    odd = [[r[j ^ 4] for j in range(len(r))] for r in base]
    return even, odd


def column_table8():
    even, odd = _col_even_odd(_C8)
    t = []
    for col in range(4):
        src = even if col % 2 == 0 else odd
        for r in range(4):
            t.append([v + 64 * col for v in src[r]])
    return t                                          # 16 x 16 byte offsets inside a 256 B block


def column_table4():
    even, odd = _col_even_odd(_C4)
    t = []
    for col in range(4):
        src = even if col % 2 == 0 else odd
        for r in range(4):
            t.append([v + 128 * col for v in src[r]])
    return t                                          # 16 x 32 nibble offsets inside a 256 B block


CT8 = column_table8()
CT4 = column_table4()


def gs_write32(mem, dbw, rw, rh, data):
    """PSMCT32 host->local transfer of an rw x rh rectangle at (0,0), buffer width dbw (x64 px)."""
    i = 0
    for y in range(rh):
        for x in range(rw):
            page = (x >> 6) + (y >> 5) * dbw
            block = BT32[(y & 31) >> 3][(x & 63) >> 3]
            word = page * 2048 + block * 64 + ((y & 7) >> 1) * 16 + CT32[y & 1][x & 7]
            mem[word * 4:word * 4 + 4] = data[i:i + 4]
            i += 4


def gs_read8(mem, tbw, w, h):
    ppr = max(1, tbw >> 1)
    out = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            page = (x >> 7) + (y >> 6) * ppr
            block = BT8[(y & 63) >> 4][(x & 127) >> 4]
            out[y * w + x] = mem[page * 8192 + block * 256 + CT8[y & 15][x & 15]]
    return out


def gs_read4(mem, tbw, w, h):
    ppr = max(1, tbw >> 1)
    out = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            page = (x >> 7) + (y >> 7) * ppr
            block = BT4[(y & 127) >> 4][(x & 127) >> 5]
            nib = CT4[y & 15][x & 31]
            b = mem[page * 8192 + block * 256 + (nib >> 1)]
            out[y * w + x] = (b >> 4) if nib & 1 else (b & 15)
    return out


def unswizzle_gs(data, w, h, bits):
    """Indices uploaded as PSMCT32 then read as PSMT4/PSMT8. Page grids of the two views coincide:
    PSMT8 w x h <- PSMCT32 (w/2) x (h/2); PSMT4 w x h <- PSMCT32 (w/2) x (h/4); sub-page textures use the
    PSMCT32 rectangle that covers the same GS blocks (32 x 32 for a 64 x 64 PSMT8 / 128 x 128 PSMT4 quarter)."""
    nbytes = w * h * bits // 8
    pages = max(1, nbytes // 8192) + 4
    mem = bytearray(pages * 8192 + 8192)
    if bits == 8:
        rw, rh = w // 2, h // 2
        dbw = max(1, w // 128)
        gs_write32(mem, dbw, rw, rh, data)
        return gs_read8(mem, max(2, w // 64), w, h)
    rw, rh = w // 2, h // 4
    dbw = max(1, w // 128)
    gs_write32(mem, dbw, rw, rh, data)
    return gs_read4(mem, max(2, w // 64), w, h)

# ----------------------------------------------------------------------------------------------- JADERLINK port


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
    return tmp        # raw buffer reinterpreted as w x h (as the C# Bitmap constructor does)

# ----------------------------------------------------------------------------------------------- decode


def indices(d, h, swizzle='gs'):
    w, ht, bd, il = h['width'], h['height'], h['bitdepth'], h['interlace']
    if bd == 6:
        return None
    bits = 4 if bd == 8 else 8
    n = w * ht * bits // 8
    raw = d[h['index_off']:h['index_off'] + n]
    if len(raw) != n:
        raise ValueError('truncated index data')
    if il & 2:
        return (unswizzle_gs if swizzle == 'gs' else unswizzle_jl)(raw, w, ht, 8 if bits == 8 else 4)
    if bits == 8:
        return bytearray(raw)
    out = bytearray(w * ht)
    for i, b in enumerate(raw):
        out[2 * i] = b & 15
        out[2 * i + 1] = b >> 4
    return out


def decode(d, h, swizzle='gs', raw_alpha=False):
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


def cmd_info(tpl):
    d = Path(tpl).read_bytes()
    t = parse_tpl(d)
    print('magic 0x%x count %d start 0x%x' % (t['magic'], t['count'], t['start']))
    for i, h in enumerate(t['entries']):
        s = describe(h)
        print('%04d %4dx%-4d %-28s il=%d mips=%d tex0=%s' % (i, s['width'], s['height'], s['format'],
                                                            h['interlace'], len(h['mips']), s['gs_tex0']))


def cmd_decode(tpl, out, entries=None, mips=False, raw_alpha=False, swizzle='gs'):
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


def cmd_compare(out, jl_dir):
    """Pixel compare our PNGs against RE4_PS2_TPL_EXTRACT PNGs (NNNN.PNG, NNNN_Mipmap1.PNG ...)."""
    out, jl = Path(out), Path(jl_dir)
    rows = []
    for p in sorted(out.glob('[0-9][0-9][0-9][0-9]*.png')):
        stem = p.stem
        jn = stem.replace('_mip', '_Mipmap') + '.PNG'
        q = jl / jn
        if not q.exists():
            rows.append(dict(file=p.name, jaderlink=None, status='no reference'))
            continue
        w, h, a = read_png(p)
        w2, h2, b = read_png(q)
        if (w, h) != (w2, h2):
            rows.append(dict(file=p.name, jaderlink=jn, status='size %dx%d vs %dx%d' % (w, h, w2, h2)))
            continue
        diff_rgb = diff_a = diff_rgb_where_a = 0
        maxd = 0
        for i in range(w * h):
            pa, pb = a[i * 4:i * 4 + 4], b[i * 4:i * 4 + 4]
            if pa[3] != pb[3]:
                diff_a += 1
            if pa[:3] != pb[:3]:
                diff_rgb += 1
                if pa[3] or pb[3]:
                    diff_rgb_where_a += 1
                maxd = max(maxd, max(abs(pa[k] - pb[k]) for k in range(3)))
        rows.append(dict(file=p.name, jaderlink=jn, size='%dx%d' % (w, h), texels=w * h,
                         rgb_diff_texels=diff_rgb, rgb_diff_visible=diff_rgb_where_a, alpha_diff_texels=diff_a,
                         max_channel_diff=maxd,
                         status='identical' if diff_rgb == 0 and diff_a == 0 else
                         ('identical where visible' if diff_rgb_where_a == 0 and diff_a == 0 else 'DIFFERENT')))
    return rows


def cmd_selftest(tpl):
    d = Path(tpl).read_bytes()
    t = parse_tpl(d)
    res = []
    for i, h in enumerate(t['entries']):
        for suf, hh in [('', h)] + [('_mip%d' % (k + 1), m) for k, m in enumerate(h['mips'])]:
            if not hh['interlace'] & 2:
                continue
            a = indices(d, hh, 'gs')
            try:
                b = indices(d, hh, 'jl')
                same = sum(1 for x, y in zip(a, b) if x == y)
                res.append(dict(entry='%04d%s' % (i, suf), size='%dx%d' % (hh['width'], hh['height']),
                                bits=4 if hh['bitdepth'] == 8 else 8, equal_texels=same, texels=len(a)))
            except Exception as ex:  # noqa: BLE001
                res.append(dict(entry='%04d%s' % (i, suf), error=str(ex)))
    return res


def main(argv):
    if len(argv) < 3:
        print(__doc__); return 2
    cmd = argv[1]
    if cmd == 'info':
        cmd_info(argv[2])
    elif cmd == 'decode':
        ents = mips = None
        opts = argv[4:]
        entries = None
        if '--entries' in opts:
            entries = {int(x) for x in opts[opts.index('--entries') + 1].split(',')}
        sw = opts[opts.index('--swizzle') + 1] if '--swizzle' in opts else 'gs'
        cmd_decode(argv[2], argv[3], entries, '--mips' in opts, '--raw-alpha' in opts, sw)
    elif cmd == 'compare':
        rows = cmd_compare(argv[2], argv[3])
        print(json.dumps(rows, indent=1))
    elif cmd == 'selftest':
        print(json.dumps(cmd_selftest(argv[2]), indent=1))
    else:
        print(__doc__); return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
