#!/usr/bin/env python3
"""charbake: read the native actor runtime headers (leon4k_runtime.h, leon_hair_runs.h, ganado_cast_runtime.h) and
the FE/v3 meshlet blobs they hold (platform/native_actor_fast.cpp BlobHeader / MeshletInfo / Records).

Stdlib only. Inputs are private generated headers (game-derived data): read them, never copy them into Git.
"""
from __future__ import annotations

import re
import struct
from pathlib import Path

ARRAY = re.compile(r'alignas\(32\)\s+static\s+(?:const\s+)?unsigned\s+char\s+(\w+)\[\]\s*=\s*\{([^}]*)\};', re.S)


def c_arrays(path) -> dict:
    """name -> bytes for every `alignas(32) static [const] unsigned char name[] = {...};` in a header."""
    text = Path(path).read_text()
    out = {}
    for m in ARRAY.finditer(text):
        vals = [int(v, 0) for v in m.group(2).replace('\n', '').split(',') if v.strip()]
        out[m.group(1)] = bytes(vals)
    return out


class Blob:
    """One FE/v3 blob: header, level-0 meshlets (records, index bytes)."""

    def __init__(self, data: bytes):
        self.data = data
        (self.magic, self.version, self.flags, self.levels, self.meshlets, self.color_index, self.rec4, self.idx4,
         self.lod4, self.bake4) = struct.unpack_from('<4B6H', data, 0)
        self.center = struct.unpack_from('<3f', data, 16)
        self.radius = struct.unpack_from('<f', data, 28)[0]
        if self.magic != 0xFE or self.version != 3:
            raise ValueError('not an FE/v3 blob')
        self.rs = 3 + (1 if self.flags & 1 else 0) + (1 if self.flags & 2 else 0)
        self.table = []
        for i in range(self.meshlets):
            w, first, index = struct.unpack_from('<IHH', data, 32 + 8 * i)
            nv, ni, nt = w & 0xFF, (w >> 8) & 0xFFF, w >> 20
            recs = [struct.unpack_from('<%dH' % self.rs, data, self.rec4 * 4 + (first + k) * self.rs * 2)
                    for k in range(nv)]
            idx = data[self.idx4 * 4 + index: self.idx4 * 4 + index + ni]
            self.table.append(dict(vertices=nv, indices=ni, triangles=nt, first=first, index=index, records=recs,
                                   idx=bytes(idx)))

    def strips(self):
        """Yield (meshlet, [local record index...]) per strip."""
        for m in self.table:
            cur = []
            for b in m['idx']:
                cur.append(b & 127)
                if b & 128:
                    yield m, cur
                    cur = []
            if cur:
                raise ValueError('unterminated strip')

    def triangles(self):
        """Oriented triangles as (record tuple a, b, c), strip parity applied (native_actor_fast.cpp clip_strip)."""
        out = []
        for m, s in self.strips():
            for t in range(len(s) - 2):
                tri = [s[t], s[t + 1], s[t + 2]]
                if t & 1:
                    tri[0], tri[1] = tri[1], tri[0]
                if len({tri[0], tri[1], tri[2]}) < 3:
                    out.append(None)  # degenerate (a strip joint); counted, not drawn as area
                    continue
                out.append(tuple(m['records'][k] for k in tri))
        return out

    def stats(self):
        nrec = sum(m['vertices'] for m in self.table)
        nidx = sum(m['indices'] for m in self.table)
        ntri = sum(m['triangles'] for m in self.table)
        nstrips = sum(1 for _ in self.strips())
        return dict(meshlets=self.meshlets, records=nrec, indices=nidx, triangles=ntri, strips=nstrips,
                    bytes=len(self.data), flags=self.flags, levels=self.levels, rs=self.rs)


def canon(tri):
    """Rotation-invariant key of an oriented triangle (winding kept)."""
    a, b, c = tri
    return min((a, b, c), (b, c, a), (c, a, b))


if __name__ == '__main__':
    import json
    import sys
    arrays = c_arrays(sys.argv[1])
    rows = {}
    for name, data in arrays.items():
        if data[:2] == b'\xfe\x03':
            b = Blob(data)
            st = b.stats()
            tris = b.triangles()
            st['degenerate_in_strips'] = sum(1 for t in tris if t is None)
            st['drawn'] = sum(1 for t in tris if t is not None)
            st['unique_oriented'] = len({canon(t) for t in tris if t is not None})
            st['idx_per_tri'] = round(st['indices'] / max(1, st['drawn']), 3)
            rows[name] = st
    print(json.dumps(rows, indent=1))
