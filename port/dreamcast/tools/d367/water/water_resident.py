#!/usr/bin/env python3
"""water_resident.py: the WATER_PS2 pictures of each water room as ROOM_RESIDENT=1 lists (lane water16, 2026-10-16).

  water_resident.py list <out.tsv> <room hex> <control run-output.txt> <water run-output.txt>
      The first-sight loads (resident_keys.py rules) that the WATER_PS2=1 run made in that room and the WATER_PS2=0
      run of the same warp did not: the water layers' pictures (the 0xfe / 0xef animation frames that the layer
      shows, every RE4DC_WATER_PS2_FLIP-th one, and the room's 0xf2 / core 0xfc pictures). Written as a
      resident_keys.py list (key, width, height, fmt, runs); merged into <out.tsv> if it exists.
  water_resident.py pack <base resident.bin> <out.bin> <list.tsv>...
      dc/resident.bin = the base's records (e.g. data set res16) plus the lists' records, deduplicated, sorted and
      padded the way resident_keys.py pack writes them. The room is the list's file name (r10a.tsv -> 0x10a).

The lists are data (tools/d367/water/resident/r<room>.tsv). When a room gets its full resident list from the
benchmark / play logs (lane resident), merge these keys into it: `resident_keys.py list` keeps existing rows and
adds new keys, or concatenate the rows.
"""
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'vram'))
import resident_keys as RK  # noqa: E402

HEAD = 'key\twidth\theight\tfmt\truns\n'


def read_tsv(p):
    rows = {}
    if Path(p).exists():
        for ln in Path(p).read_text().splitlines()[1:]:
            k, w, h, f, n = ln.split('\t')
            rows[k] = [int(w), int(h), int(f), int(n)]
    return rows


def cmd_list(a):
    out, room, ctl, new = Path(a[0]), int(a[1], 16), a[2], a[3]
    base = {k for k, *_ in RK.first_sight(ctl, room)}
    rows = read_tsv(out)
    added = 0
    for k, w, h, f in RK.first_sight(new, room):
        if k in base:
            continue
        if k in rows:
            continue
        rows[k] = [w, h, f, 1]
        added += 1
    out.write_text(HEAD + ''.join('%s\t%d\t%d\t%d\t%d\n' % (k, *v) for k, v in sorted(rows.items())))
    print('%s: room %03x, %d water keys (%d new)' % (out, room, len(rows), added))


def cmd_pack(a):
    base, out = Path(a[0]), Path(a[1])
    recs = set()
    b = base.read_bytes()
    for o in range(0, len(b), 16):
        r, w, h, f, c, v = struct.unpack_from('<4H2I', b, o)
        if r or c or v:
            recs.add((r, c, v, w, h, f))
    n0 = len(recs)
    for t in a[2:]:
        room = int(re.match(r'r([0-9a-f]+)', Path(t).stem).group(1), 16)
        for k, (w, h, f, _n) in read_tsv(t).items():
            crc, fnv = (int(x, 16) for x in k.split('-'))
            recs.add((room, crc, fnv, w, h, f))
    data = b''.join(struct.pack('<4H2I', r, w, h, f, c, v) for r, c, v, w, h, f in sorted(recs))
    data += b'\0' * (-len(data) % 512)
    out.write_bytes(data)
    print('%s: %d base records + %d water records, %d bytes' % (out, n0, len(recs) - n0, len(data)))


if __name__ == '__main__':
    {'list': cmd_list, 'pack': cmd_pack}[sys.argv[1]](sys.argv[2:])
