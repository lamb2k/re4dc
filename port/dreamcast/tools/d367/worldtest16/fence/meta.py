#!/usr/bin/env python3
"""meta.py <room dir>: R4PW part metadata (<IIHH4B) for the fence meshes (src) and the batch parts (sp) holding them."""
import sys, os, struct, importlib.util
T = '/root/probe/codex-cpu-t15-20261016/tree/port/dreamcast/tools'
sys.path.insert(0, T)
spec = importlib.util.spec_from_file_location('F', T + '/ps2_world_far_lod.py')
F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
D = sys.argv[1]
def side(path, n):
    b = open(path, 'rb').read(); h = struct.unpack_from('<4s7I', b)
    meta = [struct.unpack_from('<IIHH4B', b, 32 + 16 * i) for i in range(h[3])]
    places = [struct.unpack_from('<HH12f', b, 32 + 16 * h[3] + 52 * i) for i in range(h[2])]
    return meta, places
for name, f, s in (('flatg', 'flatg.re4mesh', 'src.r4pw'), ('sp', 'sp/ps2-wv5.re4mesh', 'sp/ps2-world.r4pw')):
    p = F.read(open(os.path.join(D, f), 'rb').read()); meta, places = side(os.path.join(D, s), len(p['parts']))
    print('==', name)
    for mi, m in enumerate(p['meshes']):
        if m[0] in (0x7e, 0x94, 0x59) or m[0] >= 60206 and m[0] <= 60209:
            for pi in range(m[6], m[6] + m[7]):
                pr = p['parts'][pi]
                print(' mesh bin 0x%x part %3d meta %s part0-5 %s uv %s' % (m[0], pi, ['0x%x' % x for x in meta[pi]], pr[:6], ['%.4g' % x for x in pr[8:12]]))
    pl = [(i, x[0], x[1]) for i, x in enumerate(places) if p['meshes'][x[0]][0] in (0x7e, 0x7f, 0x80, 0x94, 0x95, 0xd)]
    print(' placements of fence meshes (row, mesh, id):', pl)
