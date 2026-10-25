#!/usr/bin/env python3
"""ps2_tpl.py: decode RE4 PS2 TPL pictures to RGBA (lane purge-ui24, 2026-10-24).

The PS2 build's own TPL (not the GameCube 0x0020AF30 one): u32 0x1000, u32 count, u32 table offset (0x10), u32 0, then
one 48-byte record per image: u16 width, u16 height, u32 format (low byte 8 = PSMT4, 9 = PSMT8; bits 16+ = mip levels,
the base level is decoded), u32 pixel offset @+0x20 and u32 CLUT offset @+0x24 (relative to the TPL), GS TEX0 high
word @+0x28. Pixels are stored linear (PSMT4: low nibble = left pixel). CLUTs are RGBA32 with PS2 alpha (0x80 = opaque,
scaled x2 to 0xFF): a 4-bit CLUT is an 8x2 block in a 16-entry-wide buffer (entries 8-15 at +0x40); an 8-bit CLUT is
CSM1-swizzled (entries 8-15 and 16-23 of every 32 swapped). Containers (Core.dat, .fnt, memcard.dat) embed these TPLs;
find_all() locates them. Read only; private inputs and outputs stay out of Git.
"""
import struct

MAGIC = 0x1000


def _alpha(a):
    return min(255, a * 2)


def _clut(b, off, n):
    pal = []
    for i in range(n):
        o = off + 4 * i if (n == 256 or i < 8) else off + 0x40 + 4 * (i - 8)
        r, g, bb, a = b[o:o + 4]
        pal.append((r, g, bb, _alpha(a)))
    if n == 256:
        sw = []
        for i in range(256):
            j = i
            if (i & 0x18) == 0x08:
                j = i + 8
            elif (i & 0x18) == 0x10:
                j = i - 8
            sw.append(pal[j])
        pal = sw
    return pal


def parse(b, base=0):
    magic, n, tab, _z = struct.unpack_from('<4I', b, base)
    if magic != MAGIC or tab != 16:
        raise ValueError('not a PS2 TPL')
    out = []
    for k in range(n):
        h = base + tab + 48 * k
        w, hh, fmt = struct.unpack_from('<HHI', b, h)
        doff, coff = struct.unpack_from('<2I', b, h + 0x20)
        kind = fmt & 0xff
        if kind == 8:
            bpp, ncol = 4, 16
        elif kind == 9:
            bpp, ncol = 8, 256
        else:
            raise ValueError('format %d' % fmt)
        pal = _clut(b, base + coff, ncol)
        d = base + doff
        if d + w * hh * bpp // 8 > len(b):
            raise ValueError('pixels outside the file')
        px = []
        layout = 'linear'
        if bpp == 8:
            raw = b[d:d + w * hh]
            if w % 16 == 0 and hh % 16 == 0:
                sw = unswizzle8(raw, w, hh)
                if roughness(sw, w, hh) < 0.7 * roughness(raw, w, hh):
                    raw, layout = sw, 'psmct32-swizzled'
            for i in range(w * hh):
                px.append(pal[raw[i]])
        else:
            raw = bytearray(w * hh)
            for i in range(w * hh // 2):
                v = b[d + i]
                raw[2 * i] = v & 15
                raw[2 * i + 1] = v >> 4
            if w % 128 == 0 and hh % 128 == 0:
                sw = unswizzle4(b[d:d + w * hh // 2], w, hh)
                if roughness(sw, w, hh) < 0.7 * roughness(raw, w, hh):
                    raw, layout = sw, 'psmct32-swizzled'
            for i in range(w * hh):
                px.append(pal[raw[i]])
        out.append(dict(width=w, height=hh, fmt=fmt, bpp=bpp, rgba=px, index=k, layout=layout))
    return out


def unswizzle8(buf, w, h):
    """PSMT8 texels written to GS memory as PSMCT32 (the fast upload some RE4 PS2 pictures use), back to linear order
    (the standard PS2 8-bit unswizzle)."""
    out = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            block = (y & ~0xF) * w + (x & ~0xF) * 2
            swap = (((y + 2) >> 2) & 1) * 4
            py = (((y & ~3) >> 1) + (y & 1)) & 7
            col = py * w * 2 + ((x + swap) & 7) * 4
            byte = ((y >> 1) & 1) + ((x >> 2) & 2)
            out[y * w + x] = buf[block + col + byte]
    return bytes(out)


# GS local memory layouts (PCSX2 GSLocalMemory tables): PSMCT32 pages 64x32 (blocks 8x8), PSMT4 pages 128x128 (blocks 32x16)
BLOCK32 = [[0, 1, 4, 5, 16, 17, 20, 21], [2, 3, 6, 7, 18, 19, 22, 23],
           [8, 9, 12, 13, 24, 25, 28, 29], [10, 11, 14, 15, 26, 27, 30, 31]]
COLUMN32 = [[0, 1, 4, 5, 8, 9, 12, 13], [2, 3, 6, 7, 10, 11, 14, 15],
            [16, 17, 20, 21, 24, 25, 28, 29], [18, 19, 22, 23, 26, 27, 30, 31],
            [32, 33, 36, 37, 40, 41, 44, 45], [34, 35, 38, 39, 42, 43, 46, 47],
            [48, 49, 52, 53, 56, 57, 60, 61], [50, 51, 54, 55, 58, 59, 62, 63]]
BLOCK4 = [[0, 2, 8, 10], [1, 3, 9, 11], [4, 6, 12, 14], [5, 7, 13, 15],
          [16, 18, 24, 26], [17, 19, 25, 27], [20, 22, 28, 30], [21, 23, 29, 31]]


def _column4():
    # PSMT4 column layout: rows of a 32x16 block, nibble index inside the block (GSLocalMemory columnTable4)
    base = [[0, 8, 32, 40, 64, 72, 96, 104], [16, 24, 48, 56, 80, 88, 112, 120],
            [65, 73, 97, 105, 1, 9, 33, 41], [81, 89, 113, 121, 17, 25, 49, 57]]
    t = []
    for col in range(4):              # 4 columns of 4 rows
        for r in range(4):
            row = []
            off = col * 128
            src = base[r] if col % 2 == 0 else base[r][4:] + base[r][:4]   # odd columns swap the halves
            for g in range(4):        # 4 groups of 8 pixels, +2 per group
                row += [v + off + 2 * g for v in src]
            t.append(row)
    return t


COLUMN4 = _column4()


def unswizzle4(buf, w, h):
    """PSMT4 texels written to GS memory as PSMCT32 (w/2 x h/4 words), read back with PSMT4 addressing."""
    w32 = w // 2
    bw32 = w32 // 64
    mem = {}
    words = struct.unpack_from('<%dI' % (len(buf) // 4), buf)
    h32 = len(words) // w32
    for y in range(h32):
        for x in range(w32):
            page = (y // 32) * bw32 + x // 64
            a = page * 2048 + BLOCK32[(y % 32) // 8][(x % 64) // 8] * 64 + COLUMN32[y % 8][x % 8]
            mem[a] = words[y * w32 + x]
    bw4 = w // 128
    out = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            page = (y // 128) * bw4 + x // 128
            n = page * 16384 + BLOCK4[(y % 128) // 16][(x % 128) // 32] * 512 + COLUMN4[y % 16][x % 32]
            word = mem.get(n >> 3, 0)
            out[y * w + x] = (word >> ((n & 7) * 4)) & 15
    return bytes(out)


def roughness(idx, w, h):
    """Mean absolute horizontal + vertical index step (swizzled data reads as noise)."""
    s = 0
    for y in range(h - 1):
        r = y * w
        for x in range(w - 1):
            v = idx[r + x]
            s += abs(v - idx[r + x + 1]) + abs(v - idx[r + w + x])
    return s / max(1, (w - 1) * (h - 1))


def find_all(b):
    """[(offset, images)] for every PS2 TPL embedded in a container."""
    res = []
    i = 0
    while True:
        i = b.find(b'\x00\x10\x00\x00', i)
        if i < 0:
            break
        if i % 16 == 0 and i + 16 <= len(b):
            m, n, t, z = struct.unpack_from('<4I', b, i)
            if 0 < n < 256 and t == 16 and z == 0:
                try:
                    res.append((i, parse(b, i)))
                except (ValueError, struct.error, IndexError):
                    pass
        i += 4
    return res
