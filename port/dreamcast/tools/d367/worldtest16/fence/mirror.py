#!/usr/bin/env python3
"""mirror.py <room dir>: placements with a negative determinant (mirrored instances) among the meshes the spatial batch
bakes into room space (worldtest16 fence-rail hunt). Lists every mirrored placement, its mesh bin and world centre."""
import sys, os, struct, importlib.util
T = '/root/probe/codex-cpu-t15-20261016/tree/port/dreamcast/tools'
sys.path.insert(0, T)
spec = importlib.util.spec_from_file_location('F', T + '/ps2_world_far_lod.py')
F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
D = sys.argv[1]
src = F.read(open(os.path.join(D, 'flatg.re4mesh'), 'rb').read())
passes, pls = F.read_sidecar(os.path.join(D, 'src.r4pw'), len(src['parts']))
neg = 0
for i, (mi, a) in enumerate(pls):
    det = (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
           + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    if det < 0:
        neg += 1
        m = src['meshes'][mi]
        print('placement %3d mesh %3d bin 0x%02x det %+.3f at x %7.0f y %6.0f z %7.0f parts %d' % (
            i, mi, m[0], det, a[0][3], a[1][3], a[2][3], m[7]))
print('mirrored placements: %d of %d' % (neg, len(pls)))
