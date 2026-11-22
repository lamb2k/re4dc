#!/usr/bin/env python3
"""engine_pack.py <full pack> <engine pack> [--receipt <file>] [--stream-end]: the engine images' pack (NAT3 version 5) from a whole
room pack (NAT3 version 4). Lane eng-load2, 2026-11-22 (plan 3.3 section 8, B1).

A version 4 pack carries the old game's recording: sections 4 to 12 are delta tables with a row for each of 300
frames. The bench plays the recording; the engine images (game/: E1, FIGHT, BOSS, SENDABLE) apply frame 0 once at
open and never read the rest (lane eng-mem1, H-031), yet read the whole file for its CRC: 5 to 6 MB a room they drop.
A version 5 pack holds, after the unchanged texture section, the resident part exactly as the engine's frame-0 load
builds it in memory today (render/native_scene.inc keep_layout, keep_pad, read_rest_keep): sections 1 to 3 as they
are, frame 0's references made row 0, each delta table one row (frame 0's), the camera row's pad entries that keep
the models' offset modulo 32, sections 13 and 14 as they are. The loader reads it front to back in one pass straight
into its resident buffer, with the whole-file CRC (every byte after the 20-byte header) checked as before. The bench
refuses a version 5 pack (it needs the recording).

Every check the loader's frame-0 path makes on the way is made here too (a refusal is an error, no pack written).
The receipt line: input sha256, this script's sha256, output sha256, sizes.
"""
import hashlib, struct, sys, zlib
from pathlib import Path


def words(b, at, n):
    return list(struct.unpack_from('<%dI' % n, b, at))


def w1(b, at):
    return struct.unpack_from('<I', b, at)[0]


def popcount(x):
    return bin(x).count('1')


def lowest_bits(m, c):
    out = 0
    for _ in range(c):
        low = m & -m
        out |= low
        m &= m - 1
    return out


def keep_pad(row, g):
    """render/native_scene.inc keep_pad: the pad entries appended to the camera row (a list of words), or None."""
    if not g:
        return []
    sizes = [g] if g <= 28 else [g - 24, 24]
    nw = len(row)
    if nw < 3:
        return None
    s0, b0 = row[1], row[2]
    cmax = max((sz - 8) // 4 for sz in sizes)
    if popcount(b0) < cmax or nw < 3 + cmax:
        return None
    sub = lowest_bits(b0, cmax)
    i = 3 + popcount(b0)
    while i + 1 < nw:   # the later entries: none may touch the repeated words
        st, bi = row[i], row[i + 1]
        for b in range(32):
            if bi >> b & 1:
                wd = st + b
                if s0 <= wd < s0 + 32 and sub >> (wd - s0) & 1:
                    return None
        i += 2 + popcount(bi)
    out = []
    for sz in sizes:
        c = (sz - 8) // 4
        out += [s0, lowest_bits(b0, c)] + row[3:3 + c]
    return out


def convert(p, stream_end=False):
    size = len(p)
    head = words(p, 0, 5)
    if p[:4] != b'NAT3' or head[1] != 4 or head[3] != size - 20:
        raise SystemExit('engine_pack: not a version 4 NAT3 pack (header)')
    root = words(p, 20, 17)
    if root[0] != 15 or root[1] != 0 or root[16] != size - 88 or any(root[k + 1] < root[k] or root[k + 1] % 4 for k in range(1, 16)):
        raise SystemExit('engine_pack: bad root table')
    if zlib.crc32(p[20:]) & 0xffffffff != head[4]:
        raise SystemExit('engine_pack: the input pack fails its own CRC')
    tex = root[2]
    sec = [88 + root[s + 1] for s in range(16)]
    # pack_keep: frame 0's row of each delta table
    n = w1(p, sec[3])
    if n != 300 or words(p, sec[3] + 4, 2) != [0, 40]:
        raise SystemExit('engine_pack: the frame table is not 300 rows of 40 bytes')
    refs = words(p, sec[3] + 8 + 4 * n, 10)
    row_at, row_len = [], []
    for d in range(9):
        at = sec[4 + d]
        m = w1(p, at)
        if refs[d + 1] >= m:
            raise SystemExit('engine_pack: delta %d: frame 0 row out of the table' % d)
        o = words(p, at + 4 + 4 * refs[d + 1], 2)
        if o[1] < o[0] or (o[1] - o[0]) % 4:
            raise SystemExit('engine_pack: delta %d: bad row offsets' % d)
        ra = at + 8 + 4 * m + o[0]
        if ra + o[1] - o[0] > sec[5 + d]:
            raise SystemExit('engine_pack: delta %d: row past its section' % d)
        row_at.append(ra)
        row_len.append(o[1] - o[0])
    # keep_layout
    at = [0] * 16
    c = root[5] - tex
    for s in range(1, 4):
        at[s] = root[s + 1] - tex
    total = sum(12 + L for L in row_len)
    want = (root[14] - tex) % 32
    g = (want + 32 - (c + total) % 32) % 32
    if g and g < 12:
        g += 32
    # --stream-end (a control input, lane eng-load2): 96-byte groups of 12-byte pad entries more on the camera row (each
    # repeats the row's first word with its value: frame 0's state is unchanged; 96 keeps the models' offset modulo 32),
    # as many as bring the file's size to 2,017..2,047 bytes modulo 2,048: its last bytes then end fs_iso9660's DMA
    # stream through the 32-byte request (core/disc_safe.c)
    k = 0
    if stream_end:
        base = 88 + tex + c + sum(12 + L for L in row_len) + g + (root[16] - root[14])
        if base % 32 == 0:
            raise SystemExit('engine_pack: --stream-end: the pack is a multiple of 32 bytes (no 32-byte request)')
        while not 2017 <= (base + 96 * k) % 2048 <= 2047:
            k += 1
            if k > 64:
                raise SystemExit('engine_pack: --stream-end: no size in range')
    for s in range(4, 13):
        at[s] = c
        c += 12 + row_len[s - 4] + (g + 96 * k if s == 4 else 0)
    for s in (13, 14):
        at[s] = c
        c += root[s + 2] - root[s + 1]
    at[15] = c
    rest = bytearray(c)
    # read_rest_keep
    for s in range(1, 15):
        src, end = sec[s], sec[s + 1]
        if s < 4 or s > 12:
            rest[at[s]:at[s] + end - src] = p[src:end]
            if s == 3:
                f0 = at[3] + 8 + 4 * 300
                for d in range(1, 10):
                    struct.pack_into('<I', rest, f0 + 4 * d, 0)
            continue
        d = s - 4
        row = words(p, row_at[d], row_len[d] // 4)
        extra = g if d == 0 else 0
        pad = keep_pad(row, extra)
        if pad is None:
            raise SystemExit("engine_pack: frame 0's camera row cannot carry the %u-byte pad" % extra)
        if d == 0 and k:
            if keep_pad(row, 12) is None:   # the same test: no later entry writes the repeated word
                raise SystemExit("engine_pack: --stream-end: the camera row's first word is written again")
            pad +=[row[1], lowest_bits(row[2], 1), row[3]] * (8 * k)
            extra += 96 * k
        sec_words = [1, 0, row_len[d] + extra] + row + pad
        if 4 * len(sec_words) != 12 + row_len[d] + extra:
            raise SystemExit('engine_pack: delta %d: kept section size' % d)
        struct.pack_into('<%dI' % len(sec_words), rest, at[s], *sec_words)
    # the version 5 file
    new_root = [15, 0, tex] + [tex + at[s] for s in range(2, 16)]
    out = bytearray(88 + tex + len(rest))
    out[88:88 + tex] = p[88:88 + tex]
    out[88 + tex:] = rest
    struct.pack_into('<17I', out, 20, *new_root)
    out[0:4] = b'NAT3'
    struct.pack_into('<4I', out, 4, 5, head[2], len(out) - 20, 0)
    struct.pack_into('<I', out, 16, zlib.crc32(out[20:]) & 0xffffffff)
    return bytes(out), dict(tex=tex, rest_in=size - 88 - tex, rest_out=len(rest), pad=g + 96 * k)


def main():
    a = sys.argv[1:]
    rec = None
    se = '--stream-end' in a
    if se:
        a.remove('--stream-end')
    if '--receipt' in a:
        i = a.index('--receipt'); rec = a[i + 1]; del a[i:i + 2]
    if len(a) != 2:
        raise SystemExit(__doc__ + '\n--stream-end: a control input (see convert)')
    src, dst = Path(a[0]), Path(a[1])
    p = src.read_bytes()
    out, info = convert(p, se)
    dst.write_bytes(out)
    h = lambda b: hashlib.sha256(b).hexdigest()
    line = ('engine_pack %s (%d B, sha256 %s) -> %s (%d B, sha256 %s); script sha256 %s; textures %d B, resident %d -> %d B, '
            'camera-row pad %d B\n' % (src.name, len(p), h(p), dst.name, len(out), h(out), h(Path(__file__).read_bytes()),
                                       info['tex'], info['rest_in'], info['rest_out'], info['pad']))
    sys.stdout.write(line)
    if rec:
        with open(rec, 'a') as f:
            f.write(line)


if __name__ == '__main__':
    main()
