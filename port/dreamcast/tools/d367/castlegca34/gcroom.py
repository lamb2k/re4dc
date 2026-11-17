#!/usr/bin/env python3
"""gcroom.py OUTDIR ROOM...   (WSL; lane castle-gca-26): the decoded GameCube room archive (debug disc, .das decoded)
of each room as OUTDIR/ROOM.arc, the --gc-room input of ps2_objects_tex.py (Windows python cannot run the decoder)."""
import sys
from pathlib import Path
sys.path[:0] = [str(Path(__file__).resolve().parents[2]), str(Path(__file__).resolve().parents[5] / "tools")]
import ps2_objects as po  # noqa: E402
from assetpipe.rooms import GcIso  # noqa: E402

g = GcIso(po.GC_ISO)
for room in sys.argv[2:]:
    gd = g.read(next(k for rr, k in g.rooms() if rr == room))
    if gd[:32] == po.rs.CONTAINER_MAGIC:
        gd = po.rs.decode_das(gd)
    Path(sys.argv[1], room + '.arc').write_bytes(gd)
    print(room, len(gd))
