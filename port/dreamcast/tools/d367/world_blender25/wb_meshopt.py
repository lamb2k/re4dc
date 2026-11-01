# world-blender25 "modern standards" arm: meshoptimizer (python binding 0.2.30a0, vendored in ./pylib) on converter-input
# parts of the hot-spot meshes. Per part (one texture/pass/cull), in-box vertices only (others locked):
#  1 exact weld (meshopt generate_vertex_remap on position+UV+colour; the source has no normals: prelit)
#  2 drop degenerate / zero-area / duplicate triangles
#  3 interior: drop coincident back-to-back pairs (same 3 positions, opposite winding) inside the box
#  4 simplify_with_attributes, absolute error budget (mm), UV weight + colour weight, LOCK_BORDER, out-of-box verts locked
#  7 optimize_overdraw for translucent parts only (pass 2)
# Steps 5 (distance LOD: screen-error cluster LOD) and 6 (stripify + meshlets with bounds at <=256) are our converter's
# own convert_lod / mesh_lod, which runs after this filter on every arm (counts come from its output).
import os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'pylib'))
import numpy as np
import meshoptimizer as mo

LOG = collections.Counter()


def part(tris, ptype, err):
    if len(tris) < 4 or not any(c[9] for t in tris for c in t):
        return [[c[:9] for c in t] for t in tris]
    corners = np.array([c[:10] for t in tris for c in t], dtype=np.float64)
    LOG['tri_in'] += len(tris); LOG['corner_in'] += len(corners)
    key = np.ascontiguousarray(corners[:, :9].astype(np.float32))
    remap = np.zeros(len(key), dtype=np.uint32)
    nv = mo.generate_vertex_remap(remap, np.arange(len(key), dtype=np.uint32), len(key), key, len(key), key.itemsize * 9)  # binding: unindexed input needs explicit indices
    verts = np.zeros((nv, 10)); verts[remap] = corners
    idx = remap.reshape(-1, 3)
    LOG['v_weld'] += nv
    # 2 degenerate / zero area / duplicate
    P = verts[:, :3]
    keep, seen = [], set()
    for t in idx:
        a, b, c = P[t[0]], P[t[1]], P[t[2]]
        if len({tuple(a), tuple(b), tuple(c)}) < 3 or np.linalg.norm(np.cross(b - a, c - a)) < 1e-6:
            LOG['degenerate'] += 1; continue
        k = tuple(t[np.argmin(t):]) + tuple(t[:np.argmin(t)])
        if k in seen:
            LOG['duplicate'] += 1; continue
        seen.add(k); keep.append(t)
    # 3 coincident back-to-back pairs inside the box
    pos = collections.defaultdict(list)
    for i, t in enumerate(keep):
        pos[frozenset(tuple(P[v]) for v in t)].append(i)
    drop = set()
    if ptype != 2:
        for k, ii in pos.items():
            if len(ii) >= 2 and all(verts[v][9] for v in keep[ii[0]]):
                drop.update(ii); LOG['interior'] += len(ii)
    keep = [t for i, t in enumerate(keep) if i not in drop]
    if not keep:
        return [[c[:9] for c in t] for t in tris]
    ind = np.ascontiguousarray(np.array(keep, dtype=np.uint32).reshape(-1))
    # 4 attribute-aware simplification; out-of-box vertices locked; borders locked
    if err > 0:
        vp = np.ascontiguousarray(verts[:, :3].astype(np.float32))
        at = np.ascontiguousarray(np.concatenate([verts[:, 3:5], verts[:, 5:8] / 255.0], 1).astype(np.float32))
        # weights in mm: a full UV repeat ~ 1 m of error, a full colour swing ~ 0.2 m
        w = np.array([1000.0, 1000.0, 200.0, 200.0, 200.0], dtype=np.float32)
        lock = np.ascontiguousarray((verts[:, 9] == 0).astype(np.uint8))
        dst = np.zeros(len(ind), dtype=np.uint32)
        n = mo.simplify_with_attributes(dst, ind, vp, at, w, len(ind), len(vp), 12, 20, 5, lock, 0, __import__("ctypes").c_float(err),  # binding passes target_error raw to ctypes
                                        mo.SIMPLIFY_LOCK_BORDER | mo.SIMPLIFY_ERROR_ABSOLUTE)
        if n >= 3:
            ind = dst[:n].copy()
    if ptype == 2:
        vp = np.ascontiguousarray(verts[:, :3].astype(np.float32))
        dst = np.zeros(len(ind), dtype=np.uint32)
        mo.optimize_overdraw(dst, ind, vp, len(ind), len(vp), 12, 1.05); ind = dst; LOG['overdraw_parts'] += 1
    t = ind.reshape(-1, 3)
    LOG['tri_out'] += len(t); LOG['v_out'] += len(set(ind.tolist()))
    return [[[*verts[v][:9]] for v in tri] for tri in t]


def run(job, passes, err):
    out = []
    for m in job:
        out.append(dict(mesh=m['mesh'], parts=[part(t, passes[m['mesh']][k], err) for k, t in enumerate(m['parts'])]))
    print('WB_MESHOPT err_mm=%g %s' % (err, dict(LOG)), file=sys.stderr)
    return dict(meshes=out)
