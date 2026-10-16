#!/usr/bin/env python3
"""rows.py <mesh> <sidecar> BINS_CSV: placement rows (R4PW) of the meshes with these bins, as a csv."""
import sys, importlib.util
T = '/root/probe/codex-cpu-t15-20261016/tree/port/dreamcast/tools'
sys.path.insert(0, T)
spec = importlib.util.spec_from_file_location('F', T + '/ps2_world_far_lod.py')
F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
p = F.read(open(sys.argv[1], 'rb').read())
_, pls = F.read_sidecar(sys.argv[2], len(p['parts']))
bins = {int(b, 16) for b in sys.argv[3].split(',')}
print(','.join(str(i) for i, (mi, a) in enumerate(pls) if p['meshes'][mi][0] in bins))
