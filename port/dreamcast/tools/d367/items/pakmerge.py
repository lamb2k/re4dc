#!/usr/bin/env python3
"""pakmerge.py <base tex.pak> <out tex.pak> <dir with <crc>-<fnv>.re4tex>...: the base pack's packages plus every
package under the dirs (texpack.py layout and checks; a key in both must be byte-identical)."""
import struct
import sys
from pathlib import Path

sys.path.insert(0, '/root/probe/lanes-20261014/items/tree/port/dreamcast/tools/d367')
import texpack as tp  # noqa


def read_pak(blob):
    tp.verify(blob)
    ver, count, index_at, data_at, crc = struct.unpack_from('<5I', blob, 8)
    out = {}
    for i in range(count):
        k0, k1, off, size = struct.unpack_from('<4I', blob, 2048 + 16 * i)
        out[(k0, k1)] = blob[off:off + size]
    return out


def main():
    base, out = Path(sys.argv[1]), Path(sys.argv[2])
    pk = read_pak(base.read_bytes())
    n0 = len(pk)
    added = 0
    for d in sys.argv[3:]:
        for k, v in tp.from_dir(d).items():
            if k not in pk:
                added += 1
            tp.add(pk, k, v, d)
    blob, count = tp.build(pk)
    out.write_bytes(blob)
    tp.verify(blob)
    print('pakmerge: base %d + %d new = %d packages, %d bytes' % (n0, added, count, len(blob)))


if __name__ == '__main__':
    main()
