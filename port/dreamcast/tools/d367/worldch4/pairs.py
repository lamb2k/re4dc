#!/usr/bin/env python3
"""pairs.py ROOM...   (WSL; lane world-ch4, 2026-11-02)
Lists each room's loose BIN entries in the GameCube room archive (debug disc) and the PS2 rNNN.dat (BIO4DAT.AFS), by
the archive index the game uses (ps2_objects.py --pairs numbering), and prints the castle-gca-26 style spec
'room|all|<gc>:<ps2>,...|-' pairing entries at the same index where both sides are BIN. Unpaired indices are listed
for review (a room-code object the PS2 moved or dropped)."""
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[2]), str(Path(__file__).resolve().parents[5] / 'tools')]
import ps2_objects as po  # noqa: E402
from assetpipe.rooms import GcIso  # noqa: E402

g = GcIso(po.GC_ISO)
keys = dict(g.rooms())
idx = po.pb.afs_index(po.PS2_ISO)
for room in sys.argv[1:]:
    gd = g.read(keys[room])
    if gd[:32] == po.rs.CONTAINER_MAGIC:
        gd = po.rs.decode_das(gd)
    gb = {i + 4 for i, (t, s, e) in enumerate(po.rs.tagged_entries(gd, '>')) if t.rstrip(b'\0') == b'BIN'}
    try:
        pe = {i + 4 for i, t, b in po.pb.dat_entries(po.pb.afs_read(po.PS2_ISO, room + '.dat', idx)) if t == 'BIN'}
    except Exception as ex:  # noqa: BLE001
        print('%s|NO-PS2-DAT %s' % (room, ex)); continue
    both = sorted(gb & pe)
    print('%s|all|%s|-   gc_only=%s ps2_only=%s' % (room, ','.join('%x:%x' % (i, i) for i in both) or '-',
          ','.join('%x' % i for i in sorted(gb - pe)) or '-', ','.join('%x' % i for i in sorted(pe - gb)) or '-'))
