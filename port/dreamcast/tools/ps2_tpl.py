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
            for i in range(w * hh // 2):
                v = b[d + i]
                px.append(pal[v & 15])
                px.append(pal[v >> 4])
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
