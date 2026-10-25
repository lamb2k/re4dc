# world-blender25: dump the LOD0 world triangles of the hot-spot box (world mm) from an R4IM+R4PW bundle as OBJ (metres,
# Blender Z-up: x, -z, y) with vertex colours; prints vertex (pool) and piece (meshlet) counts. usage: cellobj.py <bundle> <out.obj>
import sys, struct
sys.path.insert(0, '/root/work/lanes/world-blender25/port/dreamcast/tools/d367/world_blender_roundtrip')
import package as p

d, out = sys.argv[1], sys.argv[2]
cx, cz, half = -7914.0, 2000.0, 12500.0
doc = p.decode(open(d + '/ps2-world.re4mesh', 'rb').read(), open(d + '/ps2-world.r4pw', 'rb').read(), preserve_index_layout=True)
own = p.owners(doc)
pal = doc['palette']
V, F, pieces, verts = [], [], 0, 0
for pl in doc['placements']:
    mi = pl[0]; me = doc['meshes'][mi]; A = pl[2:]
    lo, step = me[8:11], me[11:14]
    for ji, o in own.items():
        if o[0] != mi or o[4] != 0:
            continue
        m = doc['meshlets'][ji]
        pool = p.local_vertices(doc, ji)
        W = []
        for vi in pool:
            v = doc['vertices'][vi]
            loc = [lo[a] + v[a] * step[a] for a in range(3)]
            W.append([A[r*4]*loc[0] + A[r*4+1]*loc[1] + A[r*4+2]*loc[2] + A[r*4+3] for r in range(3)] + [v])
        cxm = sum(w[0] for w in W) / len(W); czm = sum(w[2] for w in W) / len(W)
        if abs(cxm - cx) > half or abs(czm - cz) > half:
            continue
        pieces += 1; verts += len(pool)
        base = len(V)
        for w in W:
            V.append(w)
        for t in p.triangles(doc, ji):
            if len(set(t)) == 3:
                F.append([base + i for i in t])
with open(out, 'w') as f:
    for w in V:
        c = w[3][-1] if isinstance(w[3], (list, tuple)) else 0
        r = ((c >> 10) & 31) / 31; g = ((c >> 5) & 31) / 31; b = (c & 31) / 31
        f.write('v %.4f %.4f %.4f %.4f %.4f %.4f\n' % ((w[0]-cx)/1000, -(w[2]-cz)/1000, w[1]/1000, r, g, b))
    for t in F:
        f.write('f %d %d %d\n' % (t[0]+1, t[1]+1, t[2]+1))
print('CELL', d, 'pieces', pieces, 'verts', verts, 'tris', len(F))
