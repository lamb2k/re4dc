#!/usr/bin/env python3
"""leonlod: reduce the PS2 Leon render mesh (arm A mesh.json, re4dc-approved-render-mesh-1) by half-edge collapse.

  lod_mesh.py <in mesh.json> <out mesh.json> --spec <spec.json> [--report <report.json>]

Why our own collapse instead of Blender's decimate: a half-edge collapse moves a vertex onto one of its neighbours,
so every surviving vertex is an original PS2 vertex with its own position, bone weights, normal and UV. No weight is
interpolated, so no new bone combination appears (palette count <= arm A's), and the UV / normal of each corner is an
original one (no UV drift on the atlas tiles).

Rules (per role; roles share no vertices):
  wedge  = a corner's (position, uv, normal, src_uv, hair material). A UV seam, a hard normal edge and a material
           border are all wedge changes.
  kinds  = MANIFOLD (one wedge, no open edge), SEAM (two wedges, exactly two seam edges), BORDER (on an open edge,
           exactly two open edges, one wedge), LOCKED (anything else: seam corners, non-manifold, role junctions).
  MANIFOLD u -> any neighbour v (v's wedge on that side replaces u's); SEAM u -> v only along a seam edge (each side
  keeps its own wedge); BORDER u -> v only along an open edge, and only where the border is not a junction with
  another role (positions within 0.5 mm of another role's vertex: neck, wrists, jacket edge stay watertight).
  Cost: quadric error (area weighted, with edge-preserving planes on seams and borders) + a bone-weight term
  (|w_u - w_v|_1 x edge length)^2 x area. Rejected: flips (normal turns > ~70 deg), link-condition breaks, slivers.

spec.json: {"targets": {"<role>": {"<region>|*": triangles}}, "keep_roles": [5, 6], "allow_border": [7],
            "max_error_mm": null | {"<role>": {"<region>|*": mm}}, "w_bone": 1.0, "locked_vertices": []}
locked_vertices lists immutable source vertex indices (for example, all corners of a boss hand or weak point).
A region target counts the triangles whose part (largest summed bone weight over the corners, leon_sources
bone_regions) is that region; u may collapse while its own part's target is not yet met.
"""
import argparse, heapq, json, math, sys
from collections import defaultdict
from pathlib import Path
import numpy as np

MANIFOLD, SEAM, BORDER, LOCKED = 0, 1, 2, 3
KIND = ['manifold', 'seam', 'border', 'locked']
REGIONS = ['head', 'torso', 'arms', 'legs']


def bone_regions(parents):
    """leon_sources.bone_regions (GC pl00 skeleton structure), from mesh.json's bone parents."""
    n = len(parents)

    def subtree(r):
        out = {r}
        for i in range(n):
            j = i
            while j >= 0:
                if j == r:
                    out.add(i)
                    break
                j = parents[j]
        return out
    reg = ['torso'] * n
    for b in subtree(3):
        reg[b] = 'head'
    for b in subtree(17):
        reg[b] = 'legs'
    for s in (5, 11):
        for b in subtree(s):
            if b not in (5, 11, 113, 114):
                reg[b] = 'arms'
    return reg


def tri_region(ws, reg):
    acc = defaultdict(float)
    for w in ws:
        for b, x in w:
            acc[reg[b]] += x
    return max(REGIONS, key=lambda r: (acc[r], -REGIONS.index(r)))


def vert_region(w, reg):
    return tri_region([w], reg)


def plane_quadric(p0, n, w):
    d = -float(np.dot(n, p0))
    q = np.array([n[0], n[1], n[2], d])
    return w * np.outer(q, q)


def qerr(Q, p):
    h = np.array([p[0], p[1], p[2], 1.0])
    return float(h @ Q @ h)


class Role:
    def __init__(self, role, tris, P, W, reg, junction, allow_border, locked=frozenset()):
        self.locked = locked
        self.seam_w = 2.0
        self.role = role
        self.P, self.W, self.reg = P, W, reg
        # tris: list of [global index, [pos a,b,c], [wedge a,b,c], region]
        self.wkey, self.wid = [], {}
        self.T = []
        for gi, t in tris:
            ps, ws = [], []
            for c in t['corners']:
                key = (c['vertex'], tuple(round(x, 6) for x in c['uv']), tuple(round(x, 4) for x in c['normal']),
                       tuple(round(x, 6) for x in c.get('src_uv', ())), t.get('material', -1))
                if key not in self.wid:
                    self.wid[key] = len(self.wkey); self.wkey.append((key, c))
                ps.append(c['vertex']); ws.append(self.wid[key])
            n0 = np.cross(P[ps[1]] - P[ps[0]], P[ps[2]] - P[ps[0]])
            n0 = n0 / max(np.linalg.norm(n0), 1e-12)
            self.T.append([gi, ps, ws, tri_region([W[p] for p in ps], reg), True, n0])
        self.vt = defaultdict(set)
        for k, t in enumerate(self.T):
            for p in t[1]:
                self.vt[p].add(k)
        self.junction = junction
        self.allow_border = allow_border
        self.Q = {}
        for p in self.vt:
            self.Q[p] = np.zeros((4, 4))
        for t in self.T:
            a, b, c = (P[p] for p in t[1])
            n = np.cross(b - a, c - a); ar = np.linalg.norm(n) / 2
            if ar < 1e-9:
                continue
            n = n / (2 * ar)
            q = plane_quadric(a, n, ar)
            for p in t[1]:
                self.Q[p] += q
        self.classify()
        # edge-preserving planes on seam / border edges (perpendicular to the face, through the edge)
        for (a, b), ts in self.edges().items():
            if len(ts) == 1 or self.is_seam(a, b, ts):
                for k in ts:
                    t = self.T[k]
                    pa, pb = P[a], P[b]
                    i = t[1]; c = [p for p in i if p not in (a, b)][0]
                    fn = np.cross(P[i[1]] - P[i[0]], P[i[2]] - P[i[0]])
                    e = pb - pa; el = np.linalg.norm(e)
                    if el < 1e-9 or np.linalg.norm(fn) < 1e-12:
                        continue
                    pn = np.cross(e, fn); pn /= np.linalg.norm(pn)
                    q = plane_quadric(pa, pn, self.seam_w * el * el)
                    self.Q[a] += q; self.Q[b] += q

    def live(self):
        return [k for k, t in enumerate(self.T) if t[4]]

    def edges(self):
        E = defaultdict(list)
        for k, t in enumerate(self.T):
            if not t[4]:
                continue
            i = t[1]
            for j in range(3):
                a, b = i[j], i[(j + 1) % 3]
                E[(min(a, b), max(a, b))].append(k)
        return E

    def wedge_at(self, k, p):
        t = self.T[k]
        return t[2][t[1].index(p)]

    def is_seam(self, a, b, ts):
        if len(ts) != 2:
            return False
        return self.wedge_at(ts[0], a) != self.wedge_at(ts[1], a) or self.wedge_at(ts[0], b) != self.wedge_at(ts[1], b)

    def classify(self):
        E = self.edges()
        self.E = E
        nb_open, nb_seam, bad = defaultdict(int), defaultdict(int), set()
        for (a, b), ts in E.items():
            if len(ts) > 2:
                bad.update((a, b))
            elif len(ts) == 1:
                nb_open[a] += 1; nb_open[b] += 1
            elif self.is_seam(a, b, ts):
                nb_seam[a] += 1; nb_seam[b] += 1
        self.kind = {}
        for p, ks in self.vt.items():
            ks = [k for k in ks if self.T[k][4]]
            if not ks:
                continue
            wed = {self.wedge_at(k, p) for k in ks}
            if p in bad or p in self.locked:
                kd = LOCKED
            elif nb_open[p]:
                kd = BORDER if (self.allow_border and nb_open[p] == 2 and len(wed) == 1 and nb_seam[p] == 0
                                and p not in self.junction) else LOCKED
            elif len(wed) == 1:
                kd = MANIFOLD
            elif len(wed) == 2 and nb_seam[p] == 2:
                kd = SEAM
            else:
                kd = LOCKED
            self.kind[p] = kd

    def neighbours(self, p):
        out = set()
        for k in self.vt[p]:
            if self.T[k][4]:
                out.update(self.T[k][1])
        out.discard(p)
        return out

    def plan(self, u, v):
        """wedge map for u -> v, or None when the collapse is not allowed."""
        ku = self.kind.get(u, LOCKED)
        if ku == LOCKED:
            return None
        ts = [k for k in self.vt[u] if self.T[k][4] and v in self.T[k][1]]
        if not ts:
            return None
        if ku == MANIFOLD:
            if len(ts) != 2:
                return None
            wv = {self.wedge_at(k, v) for k in ts}
            if len(wv) != 1:
                return None
            return {self.wedge_at(ts[0], u): wv.pop()}
        if ku == SEAM:
            if len(ts) != 2 or not self.is_seam(min(u, v), max(u, v), ts):
                return None
            m = {}
            for k in ts:
                wu, wv = self.wedge_at(k, u), self.wedge_at(k, v)
                if m.get(wu, wv) != wv:
                    return None
                m[wu] = wv
            return m if len(m) == 2 else None
        if ku == BORDER:
            if len(ts) != 1:
                return None
            return {self.wedge_at(ts[0], u): self.wedge_at(ts[0], v)}
        return None

    def valid(self, u, v):
        P = self.P
        ts_uv = [k for k in self.vt[u] if self.T[k][4] and v in self.T[k][1]]
        opp = set()
        for k in ts_uv:
            opp.update(p for p in self.T[k][1] if p not in (u, v))
        if (self.neighbours(u) & self.neighbours(v)) != opp:
            return False
        for k in self.vt[u]:
            t = self.T[k]
            if not t[4] or v in t[1]:
                continue
            a, b, c = (P[p] for p in t[1])
            n0 = np.cross(b - a, c - a)
            q = [P[v] if p == u else P[p] for p in t[1]]
            n1 = np.cross(q[1] - q[0], q[2] - q[0])
            l0, l1 = np.linalg.norm(n0), np.linalg.norm(n1)
            if l1 < 1e-6 or l0 < 1e-12:
                return False
            if np.dot(n0, n1) / (l0 * l1) < 0.35 or np.dot(t[5], n1) / l1 < 0.2:
                return False
            # sliver: longest edge^2 / area
            e = max(np.linalg.norm(q[1] - q[0]), np.linalg.norm(q[2] - q[1]), np.linalg.norm(q[0] - q[2]))
            if e * e / (l1 / 2) > self.sliver:
                return False
        return True

    def cost(self, u, v, w_bone):
        P = self.P
        e = qerr(self.Q[u], P[v])
        wu, wv = dict(self.W[u]), dict(self.W[v])
        wd = sum(abs(wu.get(b, 0) - wv.get(b, 0)) for b in set(wu) | set(wv))
        L = np.linalg.norm(P[u] - P[v])
        area = sum(np.linalg.norm(np.cross(P[self.T[k][1][1]] - P[self.T[k][1][0]], P[self.T[k][1][2]] - P[self.T[k][1][0]])) / 2
                   for k in self.vt[u] if self.T[k][4])
        return e + w_bone * (wd * L) ** 2 * area, math.sqrt(max(e, 0) / max(area, 1e-9))

    def collapse(self, u, v, wmap):
        removed = []
        for k in list(self.vt[u]):
            t = self.T[k]
            if not t[4]:
                continue
            if v in t[1]:
                t[4] = False; removed.append(k)
                continue
            j = t[1].index(u)
            t[1][j] = v; t[2][j] = wmap[t[2][j]]
            self.vt[v].add(k)
        self.vt[u] = set()
        self.Q[v] = self.Q[v] + self.Q[u]
        return removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('dst')
    ap.add_argument('--spec', required=True); ap.add_argument('--report')
    a = ap.parse_args()
    mesh = json.loads(Path(a.src).read_text())
    spec = json.loads(Path(a.spec).read_text())
    P = np.array(mesh['positions_mm'], dtype=float)
    W = [[(int(b), float(x)) for b, x in w] for w in mesh['weights']]
    parents = [b['parent'] for b in sorted(mesh['bones'], key=lambda b: b['id'])]
    reg = bone_regions(parents)
    keep = set(spec.get('keep_roles', []))
    w_bone = float(spec.get('w_bone', 1.0))
    hard_cap = float(spec.get('hard_cap_mm', 8.0))
    # open borders may slide only in the listed roles (default: the hair cards, role 7). A body border (pant hems,
    # sleeve cuffs, collar) that slides lets a whole open tube unzip from its rim (2026-10-15: the legs vanished).
    ab = spec.get('allow_border', [7])
    allow_roles = set(range(16)) if ab is True else set() if ab is False else {int(x) for x in ab}
    maxerr = spec.get('max_error_mm') or {}
    by_role = defaultdict(list)
    for gi, t in enumerate(mesh['triangles']):
        by_role[t['source_info']].append((gi, t))
    role_of = {}
    for r, ts in by_role.items():
        for _, t in ts:
            for c in t['corners']:
                role_of[c['vertex']] = r
    # junctions: a vertex within 0.5 mm of another role's vertex
    junction = defaultdict(set)
    grid = defaultdict(list)
    for i, p in enumerate(P):
        grid[tuple((p // 2).astype(int))].append(i)
    for i, p in enumerate(P):
        g = (p // 2).astype(int)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in grid.get((g[0] + dx, g[1] + dy, g[2] + dz), ()):
                        if role_of.get(j) is not None and role_of.get(i) is not None and role_of[j] != role_of[i] \
                                and np.linalg.norm(P[j] - p) < 0.5:
                            junction[role_of[i]].add(i)
    hidden_t, hidden_v = set(), set()
    if spec.get('vis'):
        seen = json.loads(Path(spec['vis']).read_text())['seen']
        hidden_t = {k for k, s in enumerate(seen) if s <= spec.get('vis_max_seen', 0)}
        vt_all = defaultdict(set)
        for k, t in enumerate(mesh['triangles']):
            for c in t['corners']:
                vt_all[c['vertex']].add(k)
        hidden_v = {p for p, ks in vt_all.items() if ks <= hidden_t}
    # small shells (holster, buckles, straps, pockets): every vertex of a connected piece below the role's threshold
    # stays (spec lock_components_below: {"<role>": triangles} or one number for every role)
    par = list(range(len(P)))

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for t in mesh['triangles']:
        v = [c['vertex'] for c in t['corners']]
        for q in v[1:]:
            par[find(q)] = find(v[0])
    csize = defaultdict(int)
    for t in mesh['triangles']:
        csize[find(t['corners'][0]['vertex'])] += 1
    lcb = spec.get('lock_components_below', 0)
    explicit_locks = spec.get('locked_vertices', [])
    if not isinstance(explicit_locks, list) or any(type(v) is not int or not 0 <= v < len(P) for v in explicit_locks):
        raise ValueError('locked_vertices must be a list of source vertex indices within the mesh')
    locked_v = set(explicit_locks)
    for t in mesh['triangles']:
        lim = lcb.get(str(t['source_info']), 0) if isinstance(lcb, dict) else lcb
        for c in t['corners']:
            if csize[find(c['vertex'])] < lim:
                locked_v.add(c['vertex'])
    before = {}
    out_tris = {}
    report = dict(roles={}, spec=spec)
    if explicit_locks:
        report['explicit_locked_vertices'] = len(set(explicit_locks))
    for r in sorted(by_role):
        R = Role(r, by_role[r], P, W, reg, junction[r], r in allow_roles, locked_v)
        R.sliver = float(spec.get('sliver', 25.0))
        cnt = defaultdict(int)
        for t in R.T:
            cnt[t[3]] += 1
        before[r] = dict(cnt)
        tg = spec['targets'].get(str(r))
        kinds = defaultdict(int)
        for p, kd in R.kind.items():
            kinds[KIND[kd]] += 1
        rep = dict(before=dict(cnt), kinds=dict(kinds), junction=len(junction[r]))
        if r in keep or not tg:
            out_tris[r] = R; rep['after'] = dict(cnt); report['roles'][str(r)] = rep
            continue
        # target per group: '*' = whole role, 'hidden' = a vertex whose every original triangle is unseen (vis.py),
        # else the vertex's region
        def group(p):
            if '*' in tg:
                return '*'
            if 'hidden' in tg and p in hidden_v:
                return 'hidden'
            return vert_region(W[p], reg)
        def met(gname):
            if gname not in tg:
                return True
            if gname == '*':
                have = sum(cnt.values())
            elif gname == 'hidden':
                have = sum(1 for t in R.T if t[4] and t[0] in hidden_t)
            else:
                have = sum(1 for t in R.T if t[4] and t[3] == gname and t[0] not in hidden_t)
            return have <= tg[gname]
        me = maxerr.get(str(r), {}) if isinstance(maxerr, dict) else {}
        heap, ver = [], defaultdict(int)

        def push(u):
            ver[u] += 1
            if R.kind.get(u, LOCKED) == LOCKED or not R.vt[u]:
                return
            cands = []
            for v in R.neighbours(u):
                if R.plan(u, v) is None:
                    continue
                c, mm = R.cost(u, v, w_bone)
                cands.append((c, v, mm))
            for c, v, mm in sorted(cands):
                if R.valid(u, v):
                    heapq.heappush(heap, (c, ver[u], u, v, mm))
                    break
        for u in list(R.vt):
            push(u)
        done = 0
        while heap:
            c, vv, u, v, mm = heapq.heappop(heap)
            if vv != ver[u] or not R.vt[u]:
                continue
            g = group(u)
            if met(g):
                continue
            lim = me.get(g, me.get('*')) if me else None
            # hard cap for every group (spec hard_cap_mm, default 8): with no cap a tube telescopes into its
            # neighbour ring by ring once the cheap collapses run out (2026-10-15: the lower legs vanished)
            if mm > min(lim if lim is not None else 1e9, hard_cap):
                continue
            wm = R.plan(u, v)
            if wm is None or not R.valid(u, v):
                push(u)
                continue
            removed = R.collapse(u, v, wm)
            for k in removed:
                cnt[R.T[k][3]] -= 1
            done += 1
            R.classify()  # kinds can change near the collapse (cheap enough at this size)
            touched = R.neighbours(v) | {v}
            for p in touched:
                push(p)
            if all(met(gn) for gn in tg):
                break
        rep['after'] = dict(cnt); rep['collapses'] = done
        report['roles'][str(r)] = rep
        out_tris[r] = R
    # write: surviving triangles in their original order, vertices compacted in first-use order
    keep_t = []
    for r, R in out_tris.items():
        for t in R.T:
            if t[4]:
                keep_t.append((t[0], r, t))
    keep_t.sort()
    remap, pos, wts, tris = {}, [], [], []
    for gi, r, t in keep_t:
        src = mesh['triangles'][gi]
        cs = []
        for p, w in zip(t[1], t[2]):
            if p not in remap:
                remap[p] = len(pos); pos.append(mesh['positions_mm'][p]); wts.append(mesh['weights'][p])
            cs.append(dict(vertex=remap[p], **R_corner(out_tris[r], w)))
        nt = {k: v for k, v in src.items() if k != 'corners'}
        nt['corners'] = cs
        tris.append(nt)
    out = dict(mesh)
    out['positions_mm'] = pos; out['weights'] = wts; out['triangles'] = tris
    out['source_info_counts'] = {str(r): sum(1 for t in tris if t['source_info'] == r) for r in sorted(by_role)}
    out['mesh'] = mesh['mesh'] + '_LOD'
    out['policy'] = mesh.get('policy', '') + ' | leonlod: half-edge collapse, vertex subset of arm A (spec %s)' % Path(a.spec).name
    Path(a.dst).write_text(json.dumps(out))
    report['triangles'] = [len(mesh['triangles']), len(tris)]
    report['positions'] = [len(mesh['positions_mm']), len(pos)]
    print(json.dumps(dict(triangles=report['triangles'], positions=report['positions'],
                          roles={r: (v['before'], v['after']) for r, v in report['roles'].items()})))
    if a.report:
        Path(a.report).write_text(json.dumps(report, indent=1))


def R_corner(R, w):
    key, c = R.wkey[w]
    out = {'normal': c['normal'], 'uv': c['uv']}
    if 'src_uv' in c:
        out['src_uv'] = c['src_uv']
    return out


if __name__ == '__main__':
    main()
