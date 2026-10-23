#!/usr/bin/env python3
"""r4pw_rekey.py: carry a data line's texture rekey (e.g. mip22b) over to a re-converted package of the same room.

    python3 r4pw_rekey.py <new.r4pw> <source.r4pw> <rekeyed.r4pw> <out.r4pw> [--obj <room>_004.scenario.obj --ids <out.ids>]

<source.r4pw> is the converter's own sidecar the data line started from (e.g. ch21l), <rekeyed.r4pw> the data line's
copy of it (same part table, texture key / size fields replaced). Every part record of <new.r4pw> (e.g. a
--bake-static or LOD rebuild from the same inputs) whose (crc, fnv, w, h) appears in <source.r4pw> gets the rekeyed
record's (crc, fnv, w, h); pass, cull, texture index and flags stay. The header crc is recomputed, and with --obj the
scroll object id sidecar is rewritten for the new crc (ps2_room_ids.write). Lane fix-r10d-speed23, 2026-10-23.
"""
import os, struct, sys, zlib
from pathlib import Path


def parts(d):
    magic, ver, npl, nparts, nmesh, crc = struct.unpack_from('<4s5I', d, 0)
    assert magic == b'R4PW' and ver == 1, 'not an R4PW v1 sidecar'
    return npl, nparts, [struct.unpack_from('<IIHHBBBB', d, 32 + 16 * i) for i in range(nparts)]


def main():
    a = sys.argv[1:]
    obj = ids = None
    if '--obj' in a:
        i = a.index('--obj'); obj = a[i + 1]; del a[i:i + 2]
    if '--ids' in a:
        i = a.index('--ids'); ids = a[i + 1]; del a[i:i + 2]
    if len(a) != 4:
        raise SystemExit(__doc__)
    new, src, rek = (bytearray(Path(p).read_bytes()) for p in a[:3])
    _, ns, ps = parts(src)
    _, nr, pr = parts(rek)
    assert ns == nr, 'source and rekeyed part tables differ in length'
    m = {}
    for s, r in zip(ps, pr):
        assert s[4:] == r[4:], 'source and rekeyed records differ beyond the texture fields'
        k = s[:4]
        assert m.get(k, r[:4]) == r[:4], 'one source key rekeyed two ways'
        m[k] = r[:4]
    npl, nn, pn = parts(new)
    miss = 0
    for i, p in enumerate(pn):
        q = m.get(p[:4])
        if q is None:
            miss += 1
            continue
        struct.pack_into('<IIHHBBBB', new, 32 + 16 * i, *(q + p[4:]))
    if miss:
        raise SystemExit('%d part records have no source key' % miss)
    struct.pack_into('<I', new, 20, zlib.crc32(bytes(new[32:])))
    Path(a[3]).write_bytes(bytes(new))
    print('r4pw_rekey: %d parts rekeyed, %d placements, crc %08x' % (nn, npl, struct.unpack_from('<I', new, 20)[0]))
    if obj:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        import ps2_room_ids
        ps2_room_ids.write(obj, a[3], ids)
        print('r4pw_rekey: ids', ids)


if __name__ == '__main__':
    main()
