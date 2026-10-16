#!/usr/bin/env python3
"""steps.py <room dir>: meshes whose grid step has an odd number of negative axes (mirrored in model space)."""
import sys, os, importlib.util
T = '/root/probe/codex-cpu-t15-20261016/tree/port/dreamcast/tools'
sys.path.insert(0, T)
spec = importlib.util.spec_from_file_location('F', T + '/ps2_world_far_lod.py')
F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
src = F.read(open(os.path.join(sys.argv[1], 'flatg.re4mesh'), 'rb').read())
odd = [(mi, m[0], m[11:14]) for mi, m in enumerate(src['meshes']) if sum(1 for s in m[11:14] if s < 0) % 2]
for x in odd: print('mesh %3d bin 0x%02x step %s' % (x[0], x[1], ['%.4g' % s for s in x[2]]))
print('odd-mirrored meshes %d of %d; bins 0x7e/0x94 steps: %s' % (len(odd), len(src['meshes']),
      [(hex(m[0]), ['%.3g' % s for s in m[11:14]], m[1], m[2], hex(m[3])) for m in src['meshes'] if m[0] in (0x7e, 0x94, 0x7f, 0x80, 0x95)]))
