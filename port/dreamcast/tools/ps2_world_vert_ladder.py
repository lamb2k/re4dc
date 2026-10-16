#!/usr/bin/env python3
"""ps2_world_vert_ladder.py IN.re4mesh OUT.re4mesh --sidecar R4PW --walk WALK.json (--px P | --target-share S)
                           [--protect-bins 0x2d,...] [--eye X,Y,Z] [--report R.json]

Wholesale world vertex reduction for a PS2 world package (R4IM v3, prelit; lane worldvert 2026-10-15). Not a far LOD:
every cluster's level 0 is REPLACED by an error-bounded simplification (tools/mesh_lod.py half-edge collapse: every
surviving vertex is an original PS2 vertex; UVs and textures unchanged, UV guard and vertex-colour guard on, open
borders only collapse along themselves, cluster borders locked so neighbours never crack). Coarser source levels stay.

Error is screen space from the gameplay camera region: a cluster's geometric ceiling is
    P px * max(distance to the nearest walkable point (tools/d367/worldlod/walk.py), --min-eye-mm) / focal
(640x480, fovy 50; placement scale included), so ground and walls the player stands next to keep their shape and the
far village loses the most. One P per level for the whole room (no per-mesh tuning); --target-share bisects P so the
level-0 TA corners of the clusters within --view-mm of --eye (the benchmark camera) fall to that share.
Protected landmarks (--protect-bins by mesh bin, --protect-last for the baked objects) keep level 0. Collision is a separate file (untouched).
The output keeps the mesh / part / placement records, so the source R4PW sidecar and ids file still match; run
tools/ps2_strip_groups.py on it for the strip-group sidecar. The runtime picks a level file with WORLD_VERT_LEVEL.
"""
import argparse, json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mesh_lod  # noqa: E402
import ps2_world_far_lod as F  # noqa: E402


def corners_of(p, lets):
    return sum(sum(len(s) for s in F.let_corners(p, p['lets'][li])[1]) for li in lets)


class WalkField:
    """Horizontal distance (mm) from the nearest walkable point on a CELL mm grid (two-pass chamfer over the room's
    box), plus the camera's height band: a point's camera distance is hypot(xz distance, height outside the band)."""
    CELL = 500.0

    def __init__(self, points, eye_lo=0.0, eye_hi=3500.0):
        xs = [p[0] for p in points]; zs = [p[2] for p in points]
        self.x0, self.z0 = min(xs) - 30000.0, min(zs) - 30000.0
        self.nx = int((max(xs) + 30000.0 - self.x0) / self.CELL) + 1
        self.nz = int((max(zs) + 30000.0 - self.z0) / self.CELL) + 1
        self.lo, self.hi = eye_lo, eye_hi
        ys = {}
        INF = 1e18
        d = [INF] * (self.nx * self.nz)
        for p in points:
            i = self.idx(p[0], p[2])
            d[i] = 0.0
            ys[i] = min(ys.get(i, 1e9), p[1])
        c, dg = self.CELL, self.CELL * math.sqrt(2.0)
        nx, nz = self.nx, self.nz
        for z in range(nz):
            for x in range(nx):
                i = z * nx + x; v = d[i]
                if x: v = min(v, d[i - 1] + c)
                if z: v = min(v, d[i - nx] + c)
                if x and z: v = min(v, d[i - nx - 1] + dg)
                if z and x < nx - 1: v = min(v, d[i - nx + 1] + dg)
                d[i] = v
        for z in range(nz - 1, -1, -1):
            for x in range(nx - 1, -1, -1):
                i = z * nx + x; v = d[i]
                if x < nx - 1: v = min(v, d[i + 1] + c)
                if z < nz - 1: v = min(v, d[i + nx] + c)
                if x < nx - 1 and z < nz - 1: v = min(v, d[i + nx + 1] + dg)
                if z < nz - 1 and x: v = min(v, d[i + nx - 1] + dg)
                d[i] = v
        self.d = d

    def idx(self, x, z):
        ix = min(self.nx - 1, max(0, int((x - self.x0) / self.CELL)))
        iz = min(self.nz - 1, max(0, int((z - self.z0) / self.CELL)))
        return iz * self.nx + ix

    def dist(self, x, y, z):
        h = self.d[self.idx(x, z)]
        dy = max(0.0, y - self.hi, self.lo - y)
        return math.sqrt(h * h + dy * dy)


def level_pv(src, lets, part, mesh, locked_pos, a, eps_of):
    """far_level() with a per-vertex error bound: eps_of(model xyz) -> model units. -> as far_level(), or None."""
    uvb, uvs = part[8:10], part[10:12]
    pos, ids, tris = F.triangles_of(src, lets, part, mesh)
    if not tris:
        return None
    locked = {ids[x] for x in ids if x in locked_pos}
    ve = {i: eps_of(p) for i, p in pos.items()}
    if a.thin_frac > 0:
        # thin-part guard: a connected piece (post, plank, beam, frame) never loses more than thin_frac of its middle
        # extent, so it cannot collapse into a sliver or vanish however coarse the screen bound around it is
        parent = {}
        def find(x):
            while parent.setdefault(x, x) != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for t, _ in tris:
            r0 = find(t[0])
            for x in t[1:]:
                r1 = find(x)
                if r1 != r0:
                    parent[r1] = r0
        box = {}
        for i, p in pos.items():
            r = find(i)
            b = box.setdefault(r, [list(p), list(p)])
            for k in range(3):
                b[0][k] = min(b[0][k], p[k]); b[1][k] = max(b[1][k], p[k])
        cap = {r: sorted(b[1][k] - b[0][k] for k in range(3))[1] * a.thin_frac for r, b in box.items()}
        for i in ve:
            if a.thin_mm <= 0 or eps_of.dist(pos[i]) < a.thin_mm:
                ve[i] = min(ve[i], cap[find(i)])
    mesh_lod.VERTEX_EPS = ve
    try:
        s = mesh_lod.Simplifier(pos, tris, locked)
        top = max(ve.values())
        eps = min(a.start_error, top)
        while True:
            s.run_to(eps)
            if eps >= top:
                break
            eps = min(top, eps * 1.25)
        cur, error = s.triangles(), s.error
    finally:
        mesh_lod.VERTEX_EPS = None
    if len(cur) > (1.0 - a.min_saving) * len(tris) or not cur:
        return None
    grid_of = {i: x for x, i in ids.items()}
    keyed = []
    for t in cur:
        k3 = []
        for v, (uv, _, colour) in zip(t[0], t[1]):
            qu = min(65535, max(0, round((uv[0] - uvb[0]) / uvs[0])))
            qv = min(65535, max(0, round((uv[1] - uvb[1]) / uvs[1])))
            k3.append((*grid_of[v], qu, qv, colour))
        keyed.append(tuple(k3))
    return len(cur), len(tris), error, keyed


def identity_level(src, lets, part, mesh):
    """Level 0 unchanged, as keyed triangles (--repack: the same triangles re-emitted in bigger meshlets)."""
    uvb, uvs = part[8:10], part[10:12]
    pos, ids, tris = F.triangles_of(src, lets, part, mesh)
    if not tris:
        return None
    grid_of = {i: x for x, i in ids.items()}
    keyed = []
    for t in tris:
        k3 = []
        for v, (uv, _, colour) in zip(t[0], t[1]):
            k3.append((*grid_of[v], min(65535, max(0, round((uv[0] - uvb[0]) / uvs[0]))),
                       min(65535, max(0, round((uv[1] - uvb[1]) / uvs[1]))), colour))
        keyed.append(tuple(k3))
    return len(tris), len(tris), 0.0, keyed


class Ladder:
    def __init__(self, a):
        self.a = a
        self.src = F.read(open(a.mesh, 'rb').read())
        src = self.src
        _, placements = F.read_sidecar(a.sidecar, len(src['parts']))
        self.part_mesh = {pi: mi for mi, m in enumerate(src['meshes']) for pi in range(m[6], m[6] + m[7])}
        self.mesh_pls = {}
        for mi, aff in placements:
            self.mesh_pls.setdefault(mi, []).append(aff)
        self.plan = [[('keep', ci) for ci in range(src['plods'][pi][0], src['plods'][pi][0] + src['plods'][pi][1])]
                     for pi in range(len(src['parts']))]
        owners = {}
        for pi, rows in enumerate(self.plan):
            mi = self.part_mesh[pi]
            for n, row in enumerate(rows):
                for li in self.l0(row):
                    for c in F.let_corners(src, src['lets'][li])[0]:
                        owners.setdefault((mi, src['verts'][c][:3]), set()).add((pi, n))
        self.locked = {}
        for (mi, g), cs in owners.items():
            if len(cs) > 1:
                self.locked.setdefault(mi, set()).add(g)
        pts = json.load(open(a.walk))['points']
        walk = F.WalkGrid(pts)
        self.field = WalkField(pts) if a.per_vertex else None
        eye = [float(x) for x in a.eye.split(',')]
        self.protect = {int(x, 0) for x in a.protect_bins.split(',') if x}
        nm = len(src['meshes'])
        self.baked = set(range(nm - a.baked, nm)) if a.baked else set()
        self.protect_meshes = set(range(nm - a.protect_last, nm)) if a.protect_last else set()
        self.info = {}
        for pi in range(len(src['parts'])):
            mi = self.part_mesh[pi]
            mesh = src['meshes'][mi]
            for n, row in enumerate(self.plan[pi]):
                c = src['clusters'][row[1]]
                lo, hi = c[0:3], c[3:6]
                pls = self.mesh_pls.get(mi, [])
                boxes = [F.world_box(mesh, aff, lo, hi) for aff in pls]
                near = min([walk.nearest(wl, wh, 200000.0) for wl, wh in boxes] + [200000.0])
                view = min([math.sqrt(sum((max(wl[k] - eye[k], 0, eye[k] - wh[k])) ** 2 for k in range(3)))
                            for wl, wh in boxes] + [1e9])
                scale = max([F.placement_scale(x) for x in pls] + [1e-9]) if pls else 1.0
                self.info[(pi, n)] = dict(near=near, view=view, scale=scale, bin=mesh[0], mesh=mi,
                                          corners=corners_of(src, self.l0(row)), box=boxes)
        self.cache = {}

    def l0(self, row):
        lv0 = self.src['levels'][self.src['clusters'][row[1]][6]]
        return list(range(lv0[0], lv0[0] + lv0[1]))

    def reduce(self, px):
        """-> {(pi, n): far_level result} for every cluster that reduces at P = px."""
        a, src, out = self.a, self.src, {}
        for pi, part in enumerate(src['parts']):
            mi = self.part_mesh[pi]
            mesh = src['meshes'][mi]
            for n, row in enumerate(self.plan[pi]):
                inf = self.info[(pi, n)]
                if not inf['corners']:
                    continue
                if (inf['bin'] in self.protect and inf['mesh'] not in self.baked) or inf['mesh'] in self.protect_meshes \
                        or px <= 0:
                    if a.repack:
                        out[(pi, n)] = identity_level(src, self.l0(row), part, mesh)
                    continue
                # within --near-mm of the walkable area the camera can come right up to it (posts, planks, door frames):
                # those clusters use --near-px, so thin parts are never collapsed into slivers
                use_px = a.near_px if (a.near_px is not None and inf['near'] < a.near_mm and not a.per_vertex) else px
                err_world = use_px * max(inf['near'], a.min_eye_mm) / a.focal_px
                err = min(err_world, a.max_error_mm) / inf['scale']
                # guards loosen with distance from the walkable area (a far gradient or UV shift is sub-pixel)
                near_m = max(inf['near'], a.min_eye_mm) / 1000.0
                cg = None if a.colour_guard < 0 else int(a.colour_guard + a.colour_per_m * near_m)
                ug = None if a.uv_guard <= 0 else a.uv_guard + a.uv_per_m * near_m
                mesh_lod.COLOUR_GUARD, mesh_lod.UV_GUARD = cg, ug
                be = None if a.border_px is None else a.border_px * max(inf['near'], a.min_eye_mm) / a.focal_px / inf['scale']
                mesh_lod.BORDER_EPS = be
                key = (pi, n, round(err, 3), cg, None if ug is None else round(ug, 4), None if be is None else round(be, 3))
                locked = self.locked.get(mi, set())
                if a.lock_borders:
                    locked = locked | self.borders(pi, n, part, mesh)
                if self.field is not None:
                    key = key + ('pv', px)
                if key not in self.cache:
                    if self.field is not None:
                        self.cache[key] = level_pv(src, self.l0(row), part, mesh, locked, a,
                                                   self.eps_fn(mi, px, inf['scale']))
                    else:
                        self.cache[key] = F.far_level(src, self.l0(row), part, mesh, locked, a, err)
                if self.cache[key] is not None:
                    out[(pi, n)] = self.cache[key]
                elif a.repack:
                    out[(pi, n)] = identity_level(src, self.l0(row), part, mesh)
        return out

    def eps_fn(self, mi, px, scale):
        """model xyz -> the model-unit error bound at that point: P px at its camera distance (the nearest walkable
        point, the camera height band; the closest of the mesh's placements), capped by --max-error-mm."""
        a, pls = self.a, self.mesh_pls.get(mi, [])
        def dist(p):
            d = 1e9
            for aff in pls or [((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0))]:
                w = [aff[r][0] * p[0] + aff[r][1] * p[1] + aff[r][2] * p[2] + aff[r][3] for r in range(3)]
                d = min(d, self.field.dist(*w))
            return d

        def f(p):
            d = 1e9
            for aff in pls or [((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0))]:
                w = [aff[r][0] * p[0] + aff[r][1] * p[1] + aff[r][2] * p[2] + aff[r][3] for r in range(3)]
                d = min(d, self.field.dist(*w))
            q = a.near_px if (a.near_px is not None and d < a.near_mm) else px
            return min(q * max(d, a.min_eye_mm) / a.focal_px, a.max_error_mm) / scale
        f.dist = dist
        return f

    def borders(self, pi, n, part, mesh):
        """Grid positions on the cluster's open borders (edges of one triangle): --lock-borders keeps them, so plank
        and wall edges, silhouettes against other meshes and T-junctions with neighbouring meshes never move."""
        k = ('b', pi, n)
        if k not in self.cache:
            pos, ids, tris = F.triangles_of(self.src, self.l0(self.plan[pi][n]), part, mesh)
            grid = {i: x for x, i in ids.items()}
            use = {}
            for t, _ in tris:
                for e in range(3):
                    a_, b_ = t[e], t[(e + 1) % 3]
                    key = (min(a_, b_), max(a_, b_))
                    use[key] = use.get(key, 0) + 1
            self.cache[k] = {grid[v] for e, c in use.items() if c == 1 for v in e}
        return self.cache[k]

    def view_corners(self, far):
        """Level-0 TA corners of the clusters within --view-mm of the eye: (source, with far)."""
        s = r = 0
        for key, inf in self.info.items():
            if inf['view'] > self.a.view_mm:
                continue
            s += inf['corners']
            f = far.get(key)
            r += sum(len(x) for x in F.mesh_lod.stripify(f[3])) if f else inf['corners']
        return s, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mesh'); ap.add_argument('out')
    ap.add_argument('--sidecar', required=True)
    ap.add_argument('--walk', required=True)
    ap.add_argument('--px', type=float)
    ap.add_argument('--target-share', type=float, help='share of the view\'s level-0 TA corners to keep (bisects --px)')
    ap.add_argument('--eye', default='-7914,1600,2000', help='benchmark-r101 cross camera region (world mm)')
    ap.add_argument('--view-mm', type=float, default=25000.0, help='the r101 fog far plane')
    ap.add_argument('--min-eye-mm', type=float, default=1500.0, help='camera distance floor (the camera trails Leon)')
    ap.add_argument('--max-error-mm', type=float, default=400.0, help='no single collapse beyond this, any distance')
    ap.add_argument('--focal-px', type=float, default=514.7)
    ap.add_argument('--uv-guard', type=float, default=0.02)
    ap.add_argument('--colour-guard', type=int, default=2)
    ap.add_argument('--colour-per-m', type=float, default=0.0, help='colour guard steps added per m from the walkable area')
    ap.add_argument('--uv-per-m', type=float, default=0.0, help='UV guard added per m from the walkable area')
    ap.add_argument('--per-vertex', action='store_true',
                    help='bound each vertex by its own camera distance (walk field) instead of the nearest point of its cluster')
    ap.add_argument('--thin-frac', type=float, default=0.0,
                    help='per-vertex mode: cap the error of a connected piece at this share of its middle extent')
    ap.add_argument('--thin-mm', type=float, default=0.0,
                    help='apply --thin-frac only to vertices closer than this to the camera region (0 = everywhere)')
    ap.add_argument('--near-px', type=float, help='screen error for clusters within --near-mm of the walkable area')
    ap.add_argument('--near-mm', type=float, default=3000.0)
    ap.add_argument('--border-px', type=float, help='screen error ceiling for open-border collapses (default: as --px)')
    ap.add_argument('--lock-borders', action='store_true',
                    help='lock every open-border vertex (no border collapses: no slivers between meshes)')
    ap.add_argument('--repack', action='store_true',
                    help='re-emit every cluster (reduced or not) in --let-verts meshlets; --px 0 keeps every triangle '
                         '(exact: fewer, bigger meshlets, fewer per-meshlet fixed fees)')
    ap.add_argument('--let-verts', type=int, default=64,
                    help='vertex limit of a re-emitted meshlet (max 256): bigger meshlets, fewer fixed per-meshlet fees')
    ap.add_argument('--protect-bins', default='')
    ap.add_argument('--baked', type=int, default=14, help='trailing STATIC_OBJ_BAKE meshes (their bins repeat)')
    ap.add_argument('--protect-last', type=int, default=0,
                    help='keep the last N meshes (STATIC_OBJ_BAKE appends the baked room objects: doors, props)')
    ap.add_argument('--list-near', help='X,Z,R: list mesh bins with a cluster within R mm of (X, Z) and stop')
    ap.add_argument('--report')
    a = ap.parse_args()
    # far_level() knobs
    a.target, a.start_error, a.min_saving = 0.0, 2.0, 0.05
    F.FAR_LET_VERTICES = min(256, a.let_verts)
    mesh_lod.UV_GUARD = a.uv_guard if a.uv_guard > 0 else None
    mesh_lod.COLOUR_GUARD = a.colour_guard if a.colour_guard >= 0 else None
    L = Ladder(a)
    if a.list_near:
        x, z, r = [float(v) for v in a.list_near.split(',')]
        rows = {}
        for key, inf in L.info.items():
            for wl, wh in inf['box']:
                d = math.hypot(max(wl[0] - x, 0, x - wh[0]), max(wl[2] - z, 0, z - wh[2]))
                if d <= r:
                    b = rows.setdefault(inf['bin'], [1e9, -1e9, 1e9, 0])
                    b[0], b[1], b[2] = min(b[0], wl[1]), max(b[1], wh[1]), min(b[2], d)
                    b[3] += inf['corners']
        for b, (y0, y1, d, c) in sorted(rows.items(), key=lambda t: t[1][2]):
            print('bin 0x%x  y %d..%d  dist %d  corners %d' % (b, y0, y1, d, c))
        return
    if a.target_share is not None:
        lo, hi = 0.0, 64.0
        for _ in range(12):
            mid = (lo + hi) / 2
            s, r = L.view_corners(L.reduce(mid))
            print('px %.3f view corners %d -> %d (%.3f)' % (mid, s, r, r / s), flush=True)
            if r / s > a.target_share:
                lo = mid
            else:
                hi = mid
        a.px = hi
    far = L.reduce(a.px)
    decision = {k: 'replace' for k in far}
    out, rows = F.emit(L.src, L.plan, L.part_mesh, far, decision)
    blob = F.write(out)
    open(a.out, 'wb').write(blob)
    s, r = L.view_corners(far)
    tot0 = sum(i['corners'] for i in L.info.values())
    tot1 = tot0 - sum(i['corners'] for k, i in L.info.items() if k in far) + \
        sum(sum(len(x) for x in mesh_lod.stripify(f[3])) for f in far.values())
    summary = dict(input=a.mesh, output=a.out, px=round(a.px, 4), bytes_in=len(open(a.mesh, 'rb').read()),
                   bytes_out=len(blob), view_corners_in=s, view_corners_out=r, view_share=round(r / s, 4),
                   all_corners_in=tot0, all_corners_out=tot1, clusters=len(L.info), replaced=len(far),
                   protect_bins=sorted(L.protect), protect_last=a.protect_last, eye=a.eye, view_mm=a.view_mm, min_eye_mm=a.min_eye_mm,
                   max_error_mm=a.max_error_mm, uv_guard=a.uv_guard, colour_guard=a.colour_guard,
                   colour_per_m=a.colour_per_m, uv_per_m=a.uv_per_m,
                   lock_borders=a.lock_borders, border_px=a.border_px, near_px=a.near_px, near_mm=a.near_mm, per_vertex=a.per_vertex, thin_frac=a.thin_frac, thin_mm=a.thin_mm, let_verts=a.let_verts, repack=a.repack, meshlets=len(out['lets']))
    print(json.dumps(summary, indent=1))
    if a.report:
        json.dump(dict(summary=summary, clusters=[dict(r, near_mm=round(L.info[(r['part'], r['cluster'] - out['plods'][r['part']][0])]['near'])) for r in rows]),
                  open(a.report, 'w'), indent=1)


if __name__ == '__main__':
    main()
