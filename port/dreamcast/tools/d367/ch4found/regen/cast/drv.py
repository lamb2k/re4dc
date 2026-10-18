#!/usr/bin/env python3
"""ch4regen copy of /c/tmp/c4drv.py (cast16 10-17) for Linux python: same drop-on-assert loop; ISO paths via /mnt/c.
usage: c4r-drv.py <ps2_cast.py> <outdir> [--plain] [--em1b0ag] <preset>...
--plain: a single pc.convert (the recorded 'ps2_cast.py convert <p> <out> --bone-tol 0.05' commands)."""
import sys, importlib.util, pathlib, shutil
args = [a for a in sys.argv[1:] if not a.startswith('--')]
flags = [a for a in sys.argv[1:] if a.startswith('--')]
s = importlib.util.spec_from_file_location('pc', args[0]); pc = importlib.util.module_from_spec(s); s.loader.exec_module(pc)
PS2, GC = pc.PS2_ISO, pc.GC_ISO  # Windows python, as recorded
W = args[1]
if '--em1b0ag' in flags:
    pc.PRESETS['zealot-em1b-0ag'] = pc._set_pool('em1b', 10, ['r201', 'r20c'])
for n in args[2:]:
    spec = pc.PRESETS[n]; dropped = []
    for _ in range(25):
        out = pathlib.Path(W) / n; shutil.rmtree(out, ignore_errors=True)
        try:
            tol = [float(f[6:]) for f in flags if f.startswith('--tol=')]
            pc.convert(n, out, ps2_iso=PS2, gc_iso=GC, bone_tol=tol[0] if tol else 0.05)
            print(n, 'OK sections', [hex(x[0]) for x in spec['sections']], 'drops', [hex(b) for b in dropped], flush=True); break
        except AssertionError as e:
            if '--plain' in flags: print(n, 'FAIL', repr(e)[:200]); break
            role = e.args[0][0] if e.args and isinstance(e.args[0], tuple) else None
            hit = [x for x in spec['sections'] if x[1] == role]
            if not hit or hit[0][1] == 'body': print(n, 'FAIL', repr(e)[:150]); break
            spec['sections'] = [x for x in spec['sections'] if x[1] != role]; dropped.append(hit[0][0])
