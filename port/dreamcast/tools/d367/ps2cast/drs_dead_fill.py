#!/usr/bin/env python3
"""drs_dead_fill.py: zero the bytes of a DVD container (.drs / .arc / .dar) that no top-level header entry reads
(lane gcleft26 2026-10-26, no-GameCube-assets rule).

The game reads a container through its 0x400-byte header (src/game/dvd.cpp cDvdQueue: case 1 reads the header at the
file's base offset, readMain then reads every entry at its ofs/size; a nested entry (type 4) is read the same way, its
own 0x400 header at the entry's ofs). Bytes outside [0, 0x400) and every top-level entry's [ofs, ofs + size) are never
read. The prepared em archives keep the original GameCube body there (em11: 0x400..0x3962c0, before the nested sound
entry), which the GC-ASSET (bytes) catalog counts as GameCube models. This tool zero-fills those gaps; offsets, sizes
and every read byte stay the same.

  drs_dead_fill.py <in> <out> [--json report]      (--check: report only, no output file)
"""
import hashlib, json, struct, sys

HEADER = 0x400
END = 0xFFFFFFFF
NESTED = 4


def entries(b, base=0):
    """(kind, size, dest, ofs) of the 32-byte DvdHeader rows after the 32-byte magic (le_mirror ENTRY_SIZE)."""
    out = []
    for pos in range(base + 32, base + HEADER, 32):
        kind, size, dest, ofs = struct.unpack_from('<4I', b, pos)
        if kind == END:
            return out
        out.append((kind, size, dest, ofs))
    raise ValueError('no end-of-table entry')


def gaps(b):
    for kind, size, _d, ofs in entries(b):
        if kind == NESTED:   # a nested header's rows are relative to its own ofs (dvd.cpp m_BaseOffset): they must stay inside it
            for _k, s2, _d2, o2 in entries(b, ofs):
                if s2 and not (HEADER <= o2 and o2 + s2 <= size):
                    raise ValueError('nested entry %#x+%#x reads outside its container at %#x' % (o2, s2, ofs))
    read = sorted([(0, HEADER)] + [(ofs, ofs + size) for kind, size, _d, ofs in entries(b) if size])
    out, at = [], 0
    for s, e in read:
        if s > at:
            out.append((at, s))
        at = max(at, e)
    if at < len(b):
        out.append((at, len(b)))
    return out, entries(b)


def main():
    a = sys.argv[1:]
    src = a[0]
    b = bytearray(open(src, 'rb').read())
    g, ents = gaps(b)
    nonzero = sum(1 for s, e in g for x in b[s:e] if x)
    rep = dict(file=src, size=len(b), sha256=hashlib.sha256(b).hexdigest(),
               entries=[dict(kind=k, size=hex(s), dest=hex(d), ofs=hex(o)) for k, s, d, o in ents],
               gaps=[[hex(s), hex(e)] for s, e in g], gap_bytes=sum(e - s for s, e in g), nonzero_gap_bytes=nonzero)
    if '--check' not in a:
        for s, e in g:
            b[s:e] = bytes(e - s)
        open(a[1], 'wb').write(b)
        rep['out_sha256'] = hashlib.sha256(b).hexdigest()
    if '--json' in a:
        json.dump(rep, open(a[a.index('--json') + 1], 'w'), indent=1)
    print(src, 'entries', len(ents), 'gaps', rep['gaps'], 'nonzero', nonzero)


if __name__ == '__main__':
    main()
