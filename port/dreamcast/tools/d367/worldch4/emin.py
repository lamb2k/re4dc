#!/usr/bin/env python3
"""emin.py OUTDIR EM...   (WSL; lane world-ch4 2026-11-02): enemy inputs for gen-em.sh: emNN.drs = the GameCube debug
disc file, emNN.dat = the PS2 USA BIO4DAT.AFS member (byte-identical to the ps2cast lane's inputs for the enemies it has;
em24 is not among them)."""
import os, sys
from pathlib import Path
sys.path[:0] = [str(Path(__file__).resolve().parents[2])]
import ps2_bin as pb  # noqa: E402
import ps2_objects as po  # noqa: E402
from assetpipe.rooms import GcIso  # noqa: E402

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
g = GcIso(po.GC_ISO); idx = pb.afs_index(po.PS2_ISO)
for e in sys.argv[2:]:
    (out / (e + '.drs')).write_bytes(g.read('em/%s.drs' % e))
    (out / (e + '.dat')).write_bytes(pb.afs_read(po.PS2_ISO, e + '.dat', idx))
    print(e, 'inputs written')
