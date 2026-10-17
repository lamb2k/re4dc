#!/usr/bin/env python3
"""resident_keys.py: the per-room texture lists of ROOM_RESIDENT=1 (lane vram12 D5, 2026-10-15).

  resident_keys.py list <room hex> <out.tsv> <run-output.txt>...
      The textures the runs loaded in that room outside its room-entry preload passes (first-sight loads), from
      VRAM_ROOM_LOG=1 logs: a load belongs to the room of the next "vram room: r=..." line; the last <loads> loads
      before each "native texture preload: frame=... loads=<loads>" line are that pass's own and are left out.
      Loads after the log's last "vram room:" line count for the room entered last ("room lifecycle: phase=enter").
      Merged into <out.tsv> if it exists (rows kept, new keys added): key, width, height, fmt, runs.
      Loads while the sub screen is open ("subscreen backing: open" .. "close": radio calls, the attache case, the
      map; the game is paused) are left out (test 14 #1): they are the sub screen's own pictures, 430 KB for the
      post-bell call in r101, which no room list can hold beside the room's set.
  resident_keys.py pack <out.bin> <list.tsv>...
      dc/resident.bin: 16-byte records (u16 room, width, height, format; u32 crc, fnv), little endian, sorted by
      room then key, padded with room-0 records to whole 512-byte pieces (native_ui.cpp preload_resident reads
      32 records at a time). The room is the list's file name: r101.tsv -> 0x101.
  resident_keys.py check <resident.bin> <list.tsv>...
      Which listed rooms the packed file does not fully cover (lane r200-17, 10-16): a data set built from an older
      tree or a partial list set (the ch4 lane's resident-ch3.bin listed 6 of r10f's 153 keys and missed r112's set,
      so their r10f / r112 runs re-read 49 / 65 pictures from disc). Prints one line per short room; exit 1 if any.

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
SS_OPEN = re.compile(r'^subscreen backing: open ')
SS_CLOSE = re.compile(r'^subscreen backing: close ')
ENTER = re.compile(r'^room lifecycle: phase=enter room=([0-9a-f]+) ')


def first_sight(log, room):
    out, pending, subscreen, cur = [], [], False, None
    ss_heap = False
    for ln in Path(log).read_text(errors='replace').splitlines():
        m = ENTER.match(ln)
        if m:
            cur = int(m.group(1), 16)
            continue
        if SS_OPEN.match(ln):
            subscreen = True
            continue
        if SS_CLOSE.match(ln):
            subscreen = False
            continue
        # The chapter title card and the chapter-end results / save screens (SS heap 11 alive; lane resident16 10-16):
        # menu pictures (~1 MB with the results screen) that no room list should pin, as vram_gate.py counts them.
        if ln.startswith('-- MemCreateHeap 11 '):
            ss_heap = True
            continue
        if ln.startswith('-- MemDestroyHeap 11 '):
            ss_heap = False
            continue
        m = LOAD.match(ln)
        if m and (subscreen or ss_heap):
            continue
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
    # Loads after the last room line belong to the room the log is still in (a run that ends inside the room,
    # test 14 r103: 60 s runs); a log without room lifecycle lines leaves them out.
    if cur == room:
        out += pending
    return out


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


def coverage(bin_path, tsvs):
    """[(room, listed, packed_of_listed)] for every list whose keys the packed file does not all carry."""
    b = Path(bin_path).read_bytes()
    have = set()
    for o in range(0, len(b) - 15, 16):
        r, w, h, f, c, v = struct.unpack_from('<4H2I', b, o)
        if r or w:   # room 0 with a size = a core key (CORE_PIN); room 0 without = padding
            have.add((r, c, v))
    short = []
    for t in tsvs:
        room = int(re.match(r'r([0-9a-f]+)', Path(t).stem).group(1), 16)
        keys = [ln.split('\t')[0] for ln in Path(t).read_text().splitlines()[1:] if ln.strip()]
        got = sum(1 for k in keys if (room, *(int(x, 16) for x in k.split('-'))) in have)
        if got < len(keys):
            short.append((room, len(keys), got))
    return short


def cmd_check(a):
    short = coverage(a[0], a[1:])
    for room, n, got in short:
        print('resident check: r%03x lists %d keys, %s carries %d' % (room, n, a[0], got))
    print('resident check: %d of %d lists short' % (len(short), len(a) - 1))
    sys.exit(1 if short else 0)


if __name__ == '__main__':
    {'list': cmd_list, 'pack': cmd_pack, 'check': cmd_check}[sys.argv[1]](sys.argv[2:])
