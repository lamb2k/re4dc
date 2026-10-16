#!/usr/bin/env python3
"""lods.py <room dir> [bin ...]: per stage, the LOD chain of the chosen bins' parts: per cluster, each level's triangle
count and error (the runtime picks a level per cluster by distance; worldtest16 fence-rail hunt)."""
import sys, os, importlib.util
T = '/root/probe/codex-cpu-t15-20261016/tree/port/dreamcast/tools'
sys.path.insert(0, T)
spec = importlib.util.spec_from_file_location('F', T + '/ps2_world_far_lod.py')
F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
D = sys.argv[1]; bins = [int(b, 16) for b in sys.argv[2:]] or [0x7e]
for name, f in (('src', 'src.re4mesh'), ('L2', 'L2.re4mesh'), ('flatg', 'flatg.re4mesh'), ('wv5', 'out/ps2-wv5.re4mesh')):
    p = F.read(open(os.path.join(D, f), 'rb').read())
    for mi, m in enumerate(p['meshes']):
        if m[0] not in bins:
            continue
        for pi in range(m[6], m[6] + m[7]):
            c0, cn = p['plods'][pi]
            row = []
            for ci in range(c0, c0 + cn):
                c = p['clusters'][ci]
                lv = []
                for k in range(c[7]):
                    L = p['levels'][c[6] + k]
                    nt = sum(len(list(F.crb.strip_triangles(s))) for li in range(L[0], L[0] + L[1]) for s in F.let_corners(p, p['lets'][li])[1])
                    lv.append('%d@%.3g' % (nt, L[2]))
                row.append('[' + ' '.join(lv) + ']')
            print('%-5s bin 0x%x part %d clusters %d: %s' % (name, m[0], pi, cn, ' '.join(row)))
