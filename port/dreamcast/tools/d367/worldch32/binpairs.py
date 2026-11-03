#!/usr/bin/env python3
"""binpairs.py <room>... (lane world-ch32): list GC room-archive BIN entries and PS2 rNNN.dat BIN entries side by side,
to pick the --pairs argument of ps2_objects.py room (GC arc index : PS2 arc index, as the game numbers them)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import ps2_bin as pb  # noqa: E402
import room_smd as rs  # noqa: E402
from assetpipe.rooms import GcIso  # noqa: E402

GI = '/mnt/c/Game Dev/Emulators/Resident Evil 4 Debug (Disc 1)/Resident Evil 4 Debug (Disc 1).iso'
PI = '/mnt/c/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso'
g = GcIso(GI)
idx = pb.afs_index(PI)
for room in sys.argv[1:]:
    key = next((k for rr, k in g.rooms() if rr == room), None)
    gd = g.read(key)
    if gd[:32] == rs.CONTAINER_MAGIC:
        gd = rs.decode_das(gd)
    ge = rs.tagged_entries(gd, '>')
    gb = [(i + 4, e - s) for i, (t, s, e) in enumerate(ge) if t.rstrip(b'\0') == b'BIN']
    pe = [(i + 4, len(b)) for i, t, b in pb.dat_entries(pb.afs_read(PI, room + '.dat', idx)) if t == 'BIN']
    print(room, 'GC', ' '.join('%x:%d' % x for x in gb))
    print(room, 'PS2', ' '.join('%x:%d' % x for x in pe))
