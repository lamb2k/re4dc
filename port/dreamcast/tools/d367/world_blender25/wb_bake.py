# world-blender25 arm (a): compact static pieces by 3D cell (r101 legacy-chain converter input). Like r10dbake23
# (ps2_room_r4im --bake-static) but cell-bucketed: every STATIC placement (scroll id >= 250) is transformed to world
# space and its triangles go to the cell (WB_CELL mm, x/z grid, by triangle centroid) they fall in; each non-empty cell is
# one world-space mesh (identity placement, placement field = the first static group in it, so ps2-world.ids gives it a
# static id), one part per material. Placements with an id < 250 (doors, dynamic objects) keep their own mesh,
# placement and part order. Positions stay float (the converter quantises per mesh).
import collections, os, sys


def bake(meshes, placements, sources, parts_meta, ids, cell):
    stat = [(mi, p) for mi, p in placements if ids[p['placement']] >= 250]
    keep = [(mi, p) for mi, p in placements if ids[p['placement']] < 250]
    if len(stat) < 2:
        return meshes, placements, sources, parts_meta
    first = {}
    o = 0
    for mi in range(len(meshes)):
        first[mi] = o; o += len(sources[mi]['parts'])
    # cell -> material key -> triangles of world corners (pos, uv, colour)
    cells = collections.OrderedDict(); cell_field = {}
    for mi, p in stat:
        s = sources[mi]; A = p['affine']
        W = [tuple(A[r][0]*v[0] + A[r][1]*v[1] + A[r][2]*v[2] + A[r][3] for r in range(3)) for v in s['positions']]
        det = (A[0][0]*(A[1][1]*A[2][2]-A[1][2]*A[2][1]) - A[0][1]*(A[1][0]*A[2][2]-A[1][2]*A[2][0])
               + A[0][2]*(A[1][0]*A[2][1]-A[1][1]*A[2][0]))
        for k, part in enumerate(s['parts']):
            key = tuple(parts_meta[first[mi] + k])
            for tri in part['loose']:
                cs = [(W[c[0]], s['uv'](c[2]), s['color'](c[1])) for c in tri]
                if det < 0:
                    cs = [cs[1], cs[0], cs[2]]  # mirrored placement: keep the drawn winding
                cx = sum(c[0][0] for c in cs) / 3; cz = sum(c[0][2] for c in cs) / 3
                ck = (int(cx // cell), int(cz // cell)) if cell > 0 else (0, 0)
                cells.setdefault(ck, collections.OrderedDict()).setdefault(key, []).append(cs)
                cell_field.setdefault(ck, p['placement'])
    # rebuild: kept meshes first (renumbered), then one mesh per cell
    used = sorted({mi for mi, _ in keep})
    remap = {mi: n for n, mi in enumerate(used)}
    nm, ns, npm, npl = [], {}, [], []
    for mi in used:
        nm.append(meshes[mi]); ns[remap[mi]] = sources[mi]
        npm.extend(parts_meta[first[mi]:first[mi] + len(sources[mi]['parts'])])
    for mi, p in keep:
        npl.append((remap[mi], p))
    ident = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]]
    for ck, mats in cells.items():
        positions, pidx, uvs, uidx, cols, cidx = [], {}, [], {}, [], {}
        def ix(v, lst, d):
            if v not in d:
                d[v] = len(lst); lst.append(v)
            return d[v]
        parts = []
        for k, (key, tris) in enumerate(mats.items()):
            loose = [tuple((ix(c[0], positions, pidx), ix(c[2], cols, cidx), ix(c[1], uvs, uidx), 0) for c in t) for t in tris]
            parts.append(dict(offset=32 * k, size=0, flags=0, texture=k & 255, alpha=255, strips=[], loose=loose))
            npm.append(key)
        n = len(nm)
        nm.append(dict(template=None, lit=None, placement=None, ranges=[], cell=ck))
        ns[n] = dict(flags=0, nvtx=min(65535, len(positions)), nparts=len(parts), positions=positions, parts=parts,
                     uv=uvs.__getitem__, color=cols.__getitem__, normal=lambda q: (0.0, 1.0, 0.0), bytes=0)
        npl.append((n, dict(placement=cell_field[ck], affine=ident)))
    print('WB_BAKE cell_mm=%d static placements %d -> %d cell meshes; kept %d; meshes %d -> %d; parts %d -> %d' % (
        cell, len(stat), len(cells), len(keep), len(meshes), len(nm), len(parts_meta), len(npm)), file=sys.stderr)
    return nm, npl, ns, npm
