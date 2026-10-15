#!/usr/bin/env python3
"""OCCLUDER_CULL offline (lane t2exact, 2026-10-15): conservative occluder quads for a PS2 world package, the runtime
selection / test simulated on logged cameras, and the per-pixel proof.

usage (Windows Python with numpy):
  occ_build.py build <package dir> <room hex> <work dir> <out .occ> [--cell 50] [--min-area 1.5] [--per-plane 6]
  occ_build.py sim <work dir> <out .occ> <cams file> [--n 16]        (needs <work>/ceil.bin + ceilpx.bin from
                                                                     pvs_cast <work> 1 1 ceil <cams> W H)

Occluders: rectangles, each lying in a plane of the package's static opaque triangles (pass 0, a placement that never
moves or hides: pvs_prep.py's rules), wholly covered by those triangles as seen from its occluding side (the side a
one-sided triangle is drawn from; both sides for two-sided parts). Conservative by construction:
  - coverage on a 50 mm grid of cell centres, eroded by one cell, then the rectangle shrunk by the cell size + the
    largest LOD level error of the clusters involved + 30 mm (a coarser level can move an edge by its error);
  - the rectangle's plane is pushed back behind the farthest of its triangles' points (+ the LOD error + 10 mm), so
    anything behind it is behind every covering triangle.
Runtime (native_static.cpp namespace occ, mirrored by sim()): per frame, every occluder whose occluding side faces the
eye, with all four corners deeper than near + 200 mm and nearer than the cull depth, is scored by its projected area;
the N largest each give 5 view-space planes (4 through the eye and the rectangle's edges, plus the rectangle's plane).
A cluster (or a whole placement) whose view-space box lies inside all 5 planes of one occluder is not drawn.

File (little endian): 32-byte header {char magic[4] "R4OC"; u32 version 1, mesh_crc, mesh_bytes, sidecar_crc, count;
u32 pad[2]}, then count x {f32 corner[4][3]; f32 plane[4] (unit normal towards the occluding side, offset: n.x + d = 0)}
= 64 bytes each.
"""
import json, struct, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'interior'))
from r4im import Pkg  # noqa: E402


def opt(a, name, dflt, f=float):
    return f(a[a.index(name) + 1]) if name in a else dflt


def static_tris(pkg_dir, room):
    """-> (tris (n,3,3) world mm, occluding sides (n, 2) bool [+n side, -n side], maxerr per tri), package"""
    p = Pkg(Path(pkg_dir) / 'ps2-world.re4mesh', Path(pkg_dir) / 'ps2-world.r4pw')
    ids = Path(pkg_dir) / 'ps2-world.ids'
    dyn_field = set()
    if ids.exists():
        b = ids.read_bytes(); count = struct.unpack_from('<I', b, 8)[0]; idv = b[16:16 + count]
        seen = {}
        for v in idv:
            seen[v] = seen.get(v, 0) + 1
        dyn_field = {f for f, v in enumerate(idv) if v < 250 and seen[v] == 1}
    app = Path(pkg_dir) / 'append.json'
    base_places = json.loads(app.read_text())['base_placements'] if app.exists() else None
    sky = {0x100: {2, 3, 75, 33, 34, 35, 36, 37}, 0x101: {0, 1, 2}}.get(room, set())
    T, S, E = [], [], []
    for pi, part, c, ps, cull, lo, hi in p.iter_clusters():
        pl = p.placements[pi]
        if ps != 0 or pl['placement'] in dyn_field or pl['placement'] in sky or (base_places is not None and pi >= base_places):
            continue
        cl = p.clusters[c]
        maxerr = max(p.levels[cl['first_level'] + l][2] for l in range(cl['level_count']))
        t = p.cluster_tris_world(pi, c, 0)
        if not len(t):
            continue
        T.append(t); E.append(np.full(len(t), maxerr))
        S.append(np.tile([True, cull == 0] if cull != 1 else [False, True], (len(t), 1)))
    return np.concatenate(T), np.concatenate(S), np.concatenate(E), p


def max_rect(mask):
    """largest all-True axis-aligned rectangle: (area cells, r0, c0, r1, c1) inclusive-exclusive"""
    h, w = mask.shape
    heights = np.zeros(w, int); best = (0, 0, 0, 0, 0)
    for r in range(h):
        heights = np.where(mask[r], heights + 1, 0)
        stack = []
        for c in range(w + 1):
            hh = heights[c] if c < w else 0
            start = c
            while stack and stack[-1][1] >= hh:
                s0, sh = stack.pop()
                area = sh * (c - s0)
                if area > best[0]:
                    best = (area, r - sh + 1, s0, r + 1, c)
                start = s0
            stack.append((start, hh))
    return best


def build(a):
    pkg_dir, room, work, out = a[1], int(a[2], 16), Path(a[3]), a[4]
    cell = opt(a, '--cell', 50.0); min_area = opt(a, '--min-area', 1.5) * 1e6; per_plane = int(opt(a, '--per-plane', 6))
    max_err = opt(a, '--max-err', 120.0)
    work.mkdir(parents=True, exist_ok=True)
    T, S, E, p = static_tris(pkg_dir, room)
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); area = np.linalg.norm(n, axis=1) / 2
    ok = area > 1.0
    T, S, E, n, area = T[ok], S[ok], E[ok], n[ok] / (2 * area[ok, None]), area[ok]
    # one entry per (triangle, occluding side): occluding normal = the side the viewer must be on
    ent_t, ent_n = [], []
    for side, sgn in ((0, 1.0), (1, -1.0)):
        k = np.nonzero(S[:, side])[0]
        ent_t.append(k); ent_n.append(sgn * n[k])
    et = np.concatenate(ent_t); en = np.concatenate(ent_n)
    ed = -(en * T[et].mean(1)).sum(1)  # plane offset at the centroid
    key = np.stack([np.round(en[:, 0] * 40), np.round(en[:, 1] * 40), np.round(en[:, 2] * 40), np.round(ed / 60)], 1).astype(int)
    groups = {}
    for i, k in enumerate(map(tuple, key)):
        groups.setdefault(k, []).append(i)
    occ = []
    for k, idx in groups.items():
        idx = np.array(idx)
        if area[et[idx]].sum() < min_area:
            continue
        sn = (en[idx] * area[et[idx], None]).sum(0); sn /= np.linalg.norm(sn)
        tri = T[et[idx]]
        dist = (tri * sn).sum(2)  # s.p per corner
        d0 = -np.median(dist)
        flat = np.abs(dist + d0).max(1) <= 25.0
        idx, tri, dist = idx[flat], tri[flat], dist[flat]
        if area[et[idx]].sum() < min_area or not len(idx):
            continue
        err = E[et[idx]].max()
        if err > max_err:
            continue
        # basis in the plane
        up = np.array([0.0, 1.0, 0.0]) if abs(sn[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
        u = np.cross(up, sn); u /= np.linalg.norm(u); v = np.cross(sn, u)
        P = tri.reshape(-1, 3); pu, pv = P @ u, P @ v
        u0, v0 = pu.min() - cell, pv.min() - cell
        W, H = int((pu.max() - u0) / cell) + 2, int((pv.max() - v0) / cell) + 2
        if W * H > 4_000_000:
            continue
        mask = np.zeros((H, W), bool)
        tu, tv = (tri @ u - u0) / cell, (tri @ v - v0) / cell  # (m,3) in cell units
        for j in range(len(tri)):
            x, y = tu[j], tv[j]
            c0, c1 = int(np.floor(x.min())), int(np.ceil(x.max())); r0, r1 = int(np.floor(y.min())), int(np.ceil(y.max()))
            cx, cy = np.meshgrid(np.arange(c0, c1 + 1) + 0.5, np.arange(r0, r1 + 1) + 0.5)
            def edge(a_, b_):
                return (x[b_] - x[a_]) * (cy - y[a_]) - (y[b_] - y[a_]) * (cx - x[a_])
            e0, e1, e2 = edge(0, 1), edge(1, 2), edge(2, 0)
            inside = ((e0 >= 0) & (e1 >= 0) & (e2 >= 0)) | ((e0 <= 0) & (e1 <= 0) & (e2 <= 0))
            rr, cc = np.nonzero(inside)
            mask[rr + r0, cc + c0] = True
        # erode one cell (4-neighbourhood)
        er = mask.copy()
        er[1:, :] &= mask[:-1, :]; er[:-1, :] &= mask[1:, :]; er[:, 1:] &= mask[:, :-1]; er[:, :-1] &= mask[:, 1:]
        er[0, :] = er[-1, :] = False; er[:, 0] = er[:, -1] = False
        shrink = cell + err + 30.0
        push = -(dist.min() + 0) + 0  # unused name kept simple below
        dback = -dist.min() + err + 10.0  # plane offset: n.x + dback = 0 lies behind every covering point
        for _ in range(per_plane):
            ar, r0, c0, r1, c1 = max_rect(er)
            if not ar:
                break
            a0, a1 = u0 + c0 * cell + shrink, u0 + c1 * cell - shrink
            b0, b1 = v0 + r0 * cell + shrink, v0 + r1 * cell - shrink
            er[r0:r1, c0:c1] = False
            if a1 - a0 < 600 or b1 - b0 < 600 or (a1 - a0) * (b1 - b0) < min_area:
                continue
            # corners on the pushed-back plane: x = a u + b v + t sn with sn.x + dback = 0 -> t = -dback
            cs = [a0 * u + b0 * v - dback * sn, a1 * u + b0 * v - dback * sn, a1 * u + b1 * v - dback * sn, a0 * u + b1 * v - dback * sn]
            occ.append((np.array(cs), sn, dback, (a1 - a0) * (b1 - b0) / 1e6, err))
    occ.sort(key=lambda o: -o[3])
    blob = struct.pack('<4s5I2I', b'R4OC', 1, p.mesh_crc, p.mesh_bytes, p.sidecar_crc, len(occ), 0, 0)
    for cs, sn, d, ar, err in occ:
        blob += struct.pack('<12f', *cs.reshape(-1)) + struct.pack('<4f', *sn, d)
    Path(out).write_bytes(blob)
    (work / 'occ.json').write_text(json.dumps([dict(area_m2=round(o[3], 2), err=o[4], n=[round(x, 3) for x in o[1]],
                                                     c=o[0].round(0).tolist()) for o in occ], indent=0))
    print('occluders: %d (%d bytes), area m2 total %.0f, largest %s' % (len(occ), len(blob), sum(o[3] for o in occ),
                                                                    [round(o[3], 1) for o in occ[:8]]))


def load_occ(path):
    b = Path(path).read_bytes()
    n = struct.unpack_from('<I', b, 20)[0]
    rec = np.frombuffer(b, '<f4', n * 16, 32).reshape(n, 16).astype(np.float64)
    return rec[:, :12].reshape(n, 4, 3), rec[:, 12:15], rec[:, 15]


def sim(a):
    work, occ_path, cams_path = Path(a[1]), a[2], a[3]
    N = int(opt(a, '--n', 16))
    C, Nn, D = load_occ(occ_path)
    rows = [l.rstrip('\n').split('\t') for l in open(work / 'inst.tsv')][1:]
    ninst = len(rows)
    verts = np.array([int(r[14]) for r in rows]); M = np.array([[float(x) for x in r[17:29]] for r in rows]).reshape(-1, 3, 4)
    g0 = np.array([[float(x) for x in r[29:32]] for r in rows]); g1 = np.array([[float(x) for x in r[32:35]] for r in rows])
    cams = [list(map(float, l.split())) for l in open(cams_path)]
    b = (work / 'ceil.bin').read_bytes(); m, n2 = struct.unpack_from('<2I', b, 0); nb = (n2 + 7) // 8
    px = np.frombuffer((work / 'ceilpx.bin').read_bytes(), '<u4').reshape(m, ninst)
    tot = dict(fr=0, cut=0, cutpx=0, used=0, tests=0, cut_inst=0, cams=0)
    worst = 0
    for ci, cam in enumerate(cams[:m]):
        V = np.array(cam[:12]).reshape(3, 4); P = cam[12:19]; cfar = cam[19]
        near = P[6] / (P[5] - 1)
        fr = np.unpackbits(np.frombuffer(b, np.uint8, nb, 8 + ci * 2 * nb + nb), bitorder='little')[:ninst].astype(bool)
        eye = -np.linalg.solve(V[:, :3], V[:, 3])
        facing = (Nn @ eye + D) > 10.0
        cv = np.einsum('ij,okj->oki', V[:, :3], C) + V[:, 3]  # (n,4,3) view space
        dep = -cv[:, :, 2]
        ok = facing & (dep.min(1) > near + 200) & (dep.max(1) < cfar)
        # projected area (NDC) as score
        sx = (P[1] * cv[:, :, 0] + P[2] * cv[:, :, 2]) / np.maximum(dep, 1); sy = (P[3] * cv[:, :, 1] + P[4] * cv[:, :, 2]) / np.maximum(dep, 1)
        score = 0.5 * np.abs((sx * np.roll(sy, -1, 1) - np.roll(sx, -1, 1) * sy).sum(1))
        cand = np.nonzero(ok)[0]
        sel = cand[np.argsort(-score[cand])][:N]
        planes = []
        for k in sel:
            q = cv[k]; cen = q.mean(0); pl = []
            for i in range(4):
                nn = np.cross(q[i], q[(i + 1) % 4])
                if nn @ cen > 0:
                    nn = -nn
                pl.append((nn / np.linalg.norm(nn), 0.0))
            mview = V[:, :3] @ Nn[k]  # occluding-side normal in view space (towards the eye side)
            dview = D[k] - mview @ V[:, 3]  # m.x + d' = 0 in view space: Nn.w + D = 0, w = R^-1 (x - t)
            # with a pure rotation R^-1 = R^T: Nn.(R^T (x - t)) = (R Nn).x - (R Nn).t
            pl.append((mview, dview))
            planes.append(pl)
        # each instance box in view space
        Mv = np.einsum('ij,njk->nik', V[:, :3], M[:, :, :3]); tv = np.einsum('ij,nj->ni', V[:, :3], M[:, :, 3]) + V[:, 3]
        cg, eg = (g0 + g1) / 2, (g1 - g0) / 2
        cvb = np.einsum('nij,nj->ni', Mv, cg) + tv; evb = np.einsum('nij,nj->ni', np.abs(Mv), eg)
        cut = np.zeros(ninst, bool)
        for pl in planes:
            inside = np.ones(ninst, bool)
            for nn, dd in pl:
                inside &= (cvb @ nn + evb @ np.abs(nn) + dd) <= -1.0
            cut |= inside
        cut &= fr
        tot['cams'] += 1; tot['fr'] += verts[fr].sum(); tot['cut'] += verts[cut].sum(); tot['cut_inst'] += cut.sum()
        tot['cutpx'] += px[ci][cut].sum(); tot['used'] += len(sel); tot['tests'] += fr.sum() * max(1, len(sel))
        worst = max(worst, px[ci][cut].sum())
    k = tot['cams']
    print('sim N=%d: %d cameras; in frustum %.0f verts/frame, culled %.0f (%.1f%%), %.1f instances; occluders used %.1f; '
          'pixels of culled instances %d total (worst camera %d)' % (N, k, tot['fr'] / k, tot['cut'] / k, 100 * tot['cut'] / tot['fr'],
                                                                    tot['cut_inst'] / k, tot['used'] / k, tot['cutpx'], worst))


def sim_hiz(a):
    """Occluder fusion ceiling: the occluder rectangles rasterised into a W x H depth buffer (nearest occluder depth per
    pixel centre); an instance is hidden when every pixel of its projected box rectangle has an occluder nearer than the
    box's nearest corner. Reports culled vertices and the pixels of culled instances (ceilpx.bin, must be 0)."""
    work, occ_path, cams_path = Path(a[1]), a[2], a[3]
    W, H = int(opt(a, '--w', 160)), int(opt(a, '--h', 120))
    C, Nn, D = load_occ(occ_path)
    rows = [l.rstrip('\n').split('\t') for l in open(work / 'inst.tsv')][1:]
    ninst = len(rows)
    verts = np.array([int(r[14]) for r in rows]); M = np.array([[float(x) for x in r[17:29]] for r in rows]).reshape(-1, 3, 4)
    g0 = np.array([[float(x) for x in r[29:32]] for r in rows]); g1 = np.array([[float(x) for x in r[32:35]] for r in rows])
    cams = [list(map(float, l.split())) for l in open(cams_path)]
    b = (work / 'ceil.bin').read_bytes(); m, n2 = struct.unpack_from('<2I', b, 0); nb = (n2 + 7) // 8
    px = np.frombuffer((work / 'ceilpx.bin').read_bytes(), '<u4').reshape(m, ninst)
    corners = np.array([[(q >> 0) & 1, (q >> 1) & 1, (q >> 2) & 1] for q in range(8)], float)
    tf = tc = tp = 0; used = 0
    for ci, cam in enumerate(cams[:m]):
        V = np.array(cam[:12]).reshape(3, 4); P = cam[12:19]; cfar = cam[19]; near = P[6] / (P[5] - 1)
        fr = np.unpackbits(np.frombuffer(b, np.uint8, nb, 8 + ci * 2 * nb + nb), bitorder='little')[:ninst].astype(bool)
        eye = -np.linalg.solve(V[:, :3], V[:, 3])
        cv = np.einsum('ij,okj->oki', V[:, :3], C) + V[:, 3]; dep = -cv[:, :, 2]
        ok = ((Nn @ eye + D) > 10.0) & (dep.min(1) > near + 200) & (dep.max(1) < cfar)
        zb = np.full((H, W), np.inf)
        xs = (np.arange(W) + 0.5) / W * 2 - 1; ys = (np.arange(H) + 0.5) / H * 2 - 1
        X, Y = np.meshgrid(xs, ys)
        dv = np.stack([(X + P[2]) / P[1], (Y + P[4]) / P[3], -np.ones_like(X)], -1)  # view ray at depth 1
        for k in np.nonzero(ok)[0]:
            q = cv[k]; nrm = np.cross(q[1] - q[0], q[3] - q[0])
            den = dv @ nrm
            with np.errstate(divide='ignore', invalid='ignore'):
                t = (q[0] @ nrm) / den  # depth along the ray (dv has z = -1: t is the view depth)
            hit = np.isfinite(t) & (t > 0)
            pnt = dv * t[..., None]
            for i in range(4):
                e = np.cross(q[(i + 1) % 4] - q[i], pnt - q[i]) @ nrm
                hit &= e >= 0
            zb = np.where(hit & (t < zb), t, zb)
            used += 1
        Mv = np.einsum('ij,njk->nik', V[:, :3], M[:, :, :3]); tv = np.einsum('ij,nj->ni', V[:, :3], M[:, :, 3]) + V[:, 3]
        cut = np.zeros(ninst, bool)
        for i in np.nonzero(fr)[0]:
            pts = g0[i] + corners * (g1[i] - g0[i]); vv = pts @ Mv[i].T + tv[i]; dd = -vv[:, 2]
            if dd.min() <= near:
                continue
            sx = (P[1] * vv[:, 0] + P[2] * vv[:, 2]) / dd; sy = (P[3] * vv[:, 1] + P[4] * vv[:, 2]) / dd
            c0 = int(np.clip(np.floor((sx.min() + 1) / 2 * W), 0, W - 1)); c1 = int(np.clip(np.ceil((sx.max() + 1) / 2 * W), 1, W))
            r0 = int(np.clip(np.floor((sy.min() + 1) / 2 * H), 0, H - 1)); r1 = int(np.clip(np.ceil((sy.max() + 1) / 2 * H), 1, H))
            if (zb[r0:r1, c0:c1] < dd.min()).all():
                cut[i] = True
        tf += verts[fr].sum(); tc += verts[cut].sum(); tp += px[ci][cut].sum()
    print('hiz %dx%d: %d cameras; in frustum %.0f verts/frame, culled %.0f (%.1f%%); occluders rasterised %.1f/frame; '
          'pixels of culled instances %d' % (W, H, m, tf / m, tc / m, 100 * tc / tf, used / m, tp))


if __name__ == '__main__':
    a = sys.argv[1:]
    {'build': build, 'sim': sim, 'hiz': sim_hiz}[a[0]](a)
