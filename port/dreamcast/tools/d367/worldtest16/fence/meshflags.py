#!/usr/bin/env python3
"""meshflags.py <room dir> [bin ...]: MeshRecord source_flags / part flags of chosen bins (src) vs the spatial batch."""
import sys, os, importlib.util, collections
T = '/root/probe/codex-cpu-t15-20261016/tree/port/dreamcast/tools'
sys.path.insert(0, T)
spec = importlib.util.spec_from_file_location('F', T + '/ps2_world_far_lod.py')
F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
D = sys.argv[1]; bins = [int(b, 16) for b in sys.argv[2:]] or [0x7e, 0x94, 0x7f, 0x80, 0x95, 0x59, 0x63]
for name, f in (('flatg', 'flatg.re4mesh'), ('sp', 'sp/ps2-wv5.re4mesh')):
    p = F.read(open(os.path.join(D, f), 'rb').read())
    print('==', name)
    for mi, m in enumerate(p['meshes']):
        if m[0] in bins or m[0] >= 60000:
            parts = [p['parts'][pi][2:6] for pi in range(m[6], m[6] + m[7])]
            print('mesh %3d bin %5d (0x%x) common %d owner %d srcv %d srcp %d source_flags 0x%08x parts %d part tex/alpha/flags %s' % (
                mi, m[0], m[0], m[1], m[2], m[3], m[4], m[5], m[7], sorted(set(tuple(x) for x in parts))))
    fl = collections.Counter(m[5] for m in p['meshes'])
    print('source_flags histogram', {hex(k): v for k, v in fl.items()})
