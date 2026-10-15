#!/usr/bin/env python3
"""resident_keys.py: the per-room texture lists of ROOM_RESIDENT=1 (lane vram12 D5, 2026-10-15).

  resident_keys.py list <room hex> <out.tsv> <run-output.txt>...
      The textures the runs loaded in that room outside its room-entry preload passes (first-sight loads), from
      VRAM_ROOM_LOG=1 logs: a load belongs to the room of the next "vram room: r=..." line; the last <loads> loads
      before each "native texture preload: frame=... loads=<loads>" line are that pass's own and are left out.
      Merged into <out.tsv> if it exists (rows kept, new keys added): key, width, height, fmt, runs.
  resident_keys.py pack <out.bin> <list.tsv>...
      dc/resident.bin: 16-byte records (u16 room, width, height, format; u32 crc, fnv), little endian, sorted by
      room then key, padded with room-0 records to whole 512-byte pieces (native_ui.cpp preload_resident reads
      32 records at a time). The room is the list's file name: r101.tsv -> 0x101.

The lists are data: tools/d367/vram/resident/r<room>.tsv, checked in, regenerated from the benchmark and play
logs of a room when its texture set changes. The runtime loads a listed key only while the preload's slot and byte
limits allow, so a list never forces an eviction at room entry.
"""
import re
import struct
import sys
from pathlib import Path

LOAD = re.compile(r'^native UI: load /cd/dc/tex/./([0-9a-f]{8}-[0-9a-f]{8})\.re4tex (\d+)x(\d+) fmt=(\d+)')
ROOM = re.compile(r'^vram room: r=([0-9a-f]+) ')
PRE = re.compile(r'^native texture preload: frame=\d+ picked=\d+ resident=\d+ loads=(\d+)')


def first_sight(log, room):
    out, pending = [], []
    for ln in Path(log).read_text(errors='replace').splitlines():
        m = LOAD.match(ln)
        if m:
            pending.append((m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))))
            continue
        m = PRE.match(ln)
        if m:
            k = int(m.group(1))
            if k:
                del pending[-k:]
            continue
        m = ROOM.match(ln)
        if m:
            if int(m.group(1), 16) == room:
                out += pending
            pending = []
    return out   # loads after the last room line: room unknown, left out


def cmd_list(a):
    room, out = int(a[0], 16), Path(a[1])
    rows = {}
    if out.exists():
        for ln in out.read_text().splitlines()[1:]:
            k, w, h, f, n = ln.split('\t')
            rows[k] = [int(w), int(h), int(f), int(n)]
    for log in a[2:]:
        seen = set()
        for k, w, h, f in first_sight(log, room):
            if k in seen:
                continue
            seen.add(k)
            if k in rows:
                rows[k][3] += 1
            else:
                rows[k] = [w, h, f, 1]
        print('%s: %d first-sight keys in room %03x' % (log, len(seen), room))
    out.write_text('key\twidth\theight\tfmt\truns\n' + ''.join('%s\t%d\t%d\t%d\t%d\n' % (k, *v) for k, v in sorted(rows.items())))
    print('%s: %d keys' % (out, len(rows)))


def cmd_pack(a):
    out = Path(a[0])
    recs = []
    for t in a[1:]:
        room = int(re.match(r'r([0-9a-f]+)', Path(t).stem).group(1), 16)
        for ln in Path(t).read_text().splitlines()[1:]:
            k, w, h, f, _n = ln.split('\t')
            crc, fnv = (int(x, 16) for x in k.split('-'))
            recs.append((room, crc, fnv, int(w), int(h), int(f)))
    recs.sort()
    b = b''.join(struct.pack('<4H2I', r, w, h, f, c, v) for r, c, v, w, h, f in recs)
    b += b'\0' * (-len(b) % 512)
    out.write_bytes(b)
    print('%s: %d records, %d bytes' % (out, len(recs), len(b)))


if __name__ == '__main__':
    {'list': cmd_list, 'pack': cmd_pack}[sys.argv[1]](sys.argv[2:])
