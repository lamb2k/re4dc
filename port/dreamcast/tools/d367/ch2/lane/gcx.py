#!/usr/bin/env python3
"""gcx.py OUTDIR file... : extract files from the GC debug disc 1 (GcIso)."""
import sys, pathlib
sys.path.insert(0, '/root/probe/lanes-20261016/ch2/tree/port/dreamcast/tools')
from assetpipe.rooms import GcIso
iso = GcIso('/root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso')
out = pathlib.Path(sys.argv[1])
for f in sys.argv[2:]:
    k = iso.find(f)
    assert k is not None, f
    p = out / f
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(iso.read(k if not isinstance(k, str) else f))
    print(f, p.stat().st_size)
