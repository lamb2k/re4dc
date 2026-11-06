#!/usr/bin/env python3
"""res34.py <base resident.bin> <out resident.bin> <list.tsv>...: the base Disc 2 resident.bin with each listed room's
records replaced by its list (resident_keys.py record layout: u16 room, width, height, format; u32 crc, fnv; sorted by
room then key; padded with room-0 records to whole 512-byte pieces)."""
import os, struct, sys
base, out, lists = sys.argv[1], sys.argv[2], sys.argv[3:]
R = '<4H2I'
d = open(base, 'rb').read()
recs = [r for r in struct.iter_unpack(R, d) if r[0]]
rooms = {}
for p in lists:
    room = int(os.path.basename(p)[1:4], 16); rows = []
    for ln in open(p):
        f = ln.rstrip('\n').split('\t')
        if not f[0] or f[0].startswith('#') or f[0] == 'key': continue
        c, n = (int(x, 16) for x in f[0].split('-'))
        rows.append((room, int(f[1]), int(f[2]), int(f[3], 0) if f[3].startswith('0x') else int(f[3]), c, n))
    rooms[room] = rows
old = {r: sum(1 for x in recs if x[0] == r) for r in rooms}
recs = [x for x in recs if x[0] not in rooms] + [x for v in rooms.values() for x in v]
recs = sorted(set(recs), key=lambda x: (x[0], x[4], x[5]))
b = b''.join(struct.pack(R, *x) for x in recs)
b += b'\0' * (-len(b) % 512)
open(out, 'wb').write(b)
print('records', len(recs), 'bytes', len(b), {'%03x' % r: (old[r], len(rooms[r])) for r in rooms})
