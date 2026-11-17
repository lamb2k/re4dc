#!/usr/bin/env python3
"""island_enemy_audit.py GC_ESL_DIR PS2_ESL_DIR  (lane island-gca, 2026-11-17)
Chapter 5 (island, rooms r300..r334) enemy-list audit, GameCube emleon06 / emleon07 (big endian, etc/ on the GC disc) against the PS2 USA
lists (little endian, BIO4DAT emleon06/07, as extracted for ps2enemy-ch34): per room rows, rows that differ, fields that differ and
rows the PS2 starts dead ("held": be_flag bit 0 cleared; the ported room code has to send them). Same record layout as
castle/ps2_enemy_ch4.py (32-byte rows). Prints a table; no game data is written."""
import collections, os, struct, sys
FORMAT = 'BBBBIHBB3h3hHh4s'
NAMES = ('be_flag', 'id', 'type', 'set', 'flag', 'hp', 'emset_no', 'Character', 'pos_x', 'pos_y', 'pos_z', 'rot_x', 'rot_y', 'rot_z', 'room', 'Guard_r', 'reserved')
gcd, ps2d = sys.argv[1:3]
for no in (6, 7):
    g = list(struct.iter_unpack('>' + FORMAT, open(os.path.join(gcd, 'emleon%02d.esl' % no), 'rb').read()))
    p = list(struct.iter_unpack('<' + FORMAT, open(os.path.join(ps2d, 'ps2_emleon%02d.esl' % no), 'rb').read()))
    rooms = collections.defaultdict(lambda: [0, 0, set(), 0])
    for a, b in zip(g, p):
        room = b[14] if b[1] else a[14]
        if not (0x300 <= room <= 0x33f or 0x300 <= a[14] <= 0x33f):
            continue
        r = rooms[room]; r[0] += 1
        ch = [n for n, x, y in zip(NAMES, a, b) if x != y]
        if ch:
            r[1] += 1; r[2].update(ch)
        if a[1] and (a[0] & 1) and not (b[0] & 1):
            r[3] += 1
    print('list', no)
    for room in sorted(rooms):
        r = rooms[room]
        print('  r%03x rows %d changed %d held %d fields %s' % (room, r[0], r[1], r[3], sorted(r[2])))
