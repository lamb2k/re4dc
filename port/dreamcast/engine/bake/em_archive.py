"""Whole enemy archive for the engine's room pack (eng-boss, E2): the DRS body of em/<name>.drs with every motion clip
(FCV) the old port keeps out of the archive put back in place.

The old port stores an enemy archive's FCV clips as proxies (the clip header only) plus an R4MOTBL table (section MTC)
and loads each clip's keys on use from dc/mot/<crc>-<fnv>.fcv (platform/native_motion.cpp). The engine reads no disc
in play, so the clips are restored at bake time: each proxy section is replaced by its full clip (identity checked:
CRC32 and FNV-1a of the file, header bytes equal to the proxy's), the section offsets are rewritten, the MTC table
is dropped (its tag kept, offset to an empty section). The hosted motion code relocates a clip's key table on first
use, as on the GameCube.
usage: em_archive.py <disc dir> <em name> <out>
"""
import struct, sys, zlib
from pathlib import Path


def drs_body(path):
    d = path.read_bytes()
    for i in range(8, 64, 8):
        t, size, _, off = struct.unpack_from('<4I', d, 4 * i)
        if t == 0xFFFFFFFF: break
        if t == 0 and size: return d[off:off + size]
    raise ValueError('no body record')


def fnv(b):
    h = 2166136261
    for x in b: h = ((h ^ x) * 16777619) & 0xFFFFFFFF
    return h


def prefix(p):
    n = p[2]
    return ((3 + 3 * n + 3) & ~3) + 4 + 4 * n


def expand(disc, name):
    a = drs_body(disc / 'em' / f'{name}.drs')
    n, rel = struct.unpack_from('<2I', a, 0)
    offs = list(struct.unpack_from(f'<{n}I', a, 16))
    tags = [a[16 + 4 * n + 4 * i:16 + 4 * n + 4 * i + 3] for i in range(n)]
    mtc = next((i for i in range(n) if tags[i] == b'MTC'), None)
    clips = {}
    if mtc is not None:
        m = a[offs[mtc]:]
        if m[:8] != b'R4MOTBL\0': raise ValueError('MTC table')
        count = struct.unpack_from('<I', m, 12)[0]
        for k in range(count):
            off, size, crc, fv, flags = struct.unpack_from('<5I', m, 32 + 20 * k)
            clip = (disc / 'dc' / 'mot' / f'{crc:08x}-{fv:08x}.fcv').read_bytes()
            if len(clip) != size or (zlib.crc32(clip) & 0xFFFFFFFF) != crc or fnv(clip) != fv:
                raise ValueError(f'clip identity {crc:08x}-{fv:08x}')
            head = prefix(a[off:])
            if clip[:head] != a[off:off + head]: raise ValueError('clip header differs from its proxy')
            clips[off] = clip
    order = sorted(range(n), key=lambda i: offs[i])
    head_end = min(offs)
    out = bytearray(a[:head_end])
    new_offs = list(offs)
    for idx, i in enumerate(order):
        end = offs[order[idx + 1]] if idx + 1 < n else rel
        data = clips.get(offs[i], a[offs[i]:end]) if i != mtc else b''
        while len(out) % 32: out.append(0)
        new_offs[i] = len(out)
        out += data
    while len(out) % 32: out.append(0)
    new_rel = len(out)
    out += a[rel:]
    struct.pack_into('<2I', out, 0, n, new_rel)
    struct.pack_into(f'<{n}I', out, 16, *new_offs)
    return bytes(out), dict(sections=n, clips=len(clips), body=len(a), whole=len(out))


if __name__ == '__main__':
    data, st = expand(Path(sys.argv[1]), sys.argv[2])
    Path(sys.argv[3]).write_bytes(data)
    print(st)
