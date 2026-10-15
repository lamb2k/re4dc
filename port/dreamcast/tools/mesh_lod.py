#!/usr/bin/env python3
"""Offline level-of-detail builder for native scenery meshes (R4IM v2).

Pure Python, no dependencies. Used by convert_room_bins.py --lod.

Two reducers, both judged by geometric error in model units:

* Opaque connected geometry: quadric error metric (Garland/Heckbert) half-edge
  collapse. A surviving vertex keeps its original position, so every level's
  vertices lie on the source surface and inside the source bounds. A collapse
  costs the summed squared distance of the kept position to every source plane
  (and open-border plane) merged into both ends, so sqrt(cost) bounds the
  distance to each of those planes. Open borders only collapse along
  themselves; locked vertices (cluster borders) never move, so neighbouring
  clusters at any mix of levels share the same border and cannot crack.
  Components whose bounding radius is below the level error are dropped.
* Card fields (alpha-textured parts made of many tiny components, i.e. grass
  and leaf cards): whole cards are thinned with a stratified order, so a level
  keeps an even subset. Their "error" is the distance-equivalent error chosen
  by the caller.

Corner attributes follow their triangle: a corner that moves from u to v takes
v's attributes from a removed triangle with the same UV at u when one exists
(same chart), otherwise its UV is extrapolated through the triangle's own
affine UV mapping, clamped to that triangle's UV range.

UV_GUARD (None = off, the historical behaviour): a tolerance in UV units. A
collapse is then refused when any surviving corner's new UV differs by more
than the tolerance from the triangle's own UV mapping evaluated at the kept
position, i.e. when the collapse would shear or squeeze the texture (flat walls
cost nothing geometrically, so without it a collapse across a UV seam or a
tiling restart draws the texture skewed: the r100 house wainscot, 2026-10-03).
"""
import heapq
import math


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _plane_quadric(n, p, w=1.0):
    a, b, c = n
    d = -(a * p[0] + b * p[1] + c * p[2])
    return [w * a * a, w * a * b, w * a * c, w * a * d, w * b * b, w * b * c, w * b * d,
            w * c * c, w * c * d, w * d * d]


def _qadd(q, r):
    for i in range(10):
        q[i] += r[i]


def _qeval(q, p):
    x, y, z = p
    return max(0.0, q[0] * x * x + 2 * q[1] * x * y + 2 * q[2] * x * z + 2 * q[3] * x + q[4] * y * y +
               2 * q[5] * y * z + 2 * q[6] * y + q[7] * z * z + 2 * q[8] * z + q[9])


# Converter option (ps2_room_r4im.py --lod-uv-guard): see the module docstring.
UV_GUARD = None
# COLOUR_GUARD (None = off, the historical behaviour; ps2_world_far_lod.py --colour-guard): the largest change, in 5-bit
# steps of any ARGB1555 colour channel, a surviving corner's vertex colour may take in a collapse. PS2 world meshes carry
# baked lighting in vertex colours and some tessellation exists only to carry a lighting gradient: a collapse that
# would move a corner onto a vertex of a visibly different colour is refused (lane worldlod 2026-10-15).
COLOUR_GUARD = None


def _c1555(c):
    return ((c >> 10) & 31, (c >> 5) & 31, c & 31)


def _uv_affine(p0, p1, p2, t0, t1, t2, x):
    """The triangle's UV mapping at x (barycentric in the triangle's plane, unclamped); None if degenerate."""
    e1, e2, d = _sub(p1, p0), _sub(p2, p0), _sub(x, p0)
    d00, d01, d11 = _dot(e1, e1), _dot(e1, e2), _dot(e2, e2)
    d20, d21 = _dot(d, e1), _dot(d, e2)
    den = d00 * d11 - d01 * d01
    if den <= 1e-12 * max(d00 * d11, 1e-30):
        return None
    b1 = (d11 * d20 - d01 * d21) / den
    b2 = (d00 * d21 - d01 * d20) / den
    b0 = 1.0 - b1 - b2
    return tuple(b0 * t0[a] + b1 * t1[a] + b2 * t2[a] for a in range(2))


def _uv_extrapolate(p0, p1, p2, t0, t1, t2, x):
    e1, e2, d = _sub(p1, p0), _sub(p2, p0), _sub(x, p0)
    d00, d01, d11 = _dot(e1, e1), _dot(e1, e2), _dot(e2, e2)
    d20, d21 = _dot(d, e1), _dot(d, e2)
    den = d00 * d11 - d01 * d01
    if den <= 1e-12 * max(d00 * d11, 1e-30):
        return t0
    b1 = (d11 * d20 - d01 * d21) / den
    b2 = (d00 * d21 - d01 * d20) / den
    b0 = 1.0 - b1 - b2
    out = []
    for a in range(2):
        v = b0 * t0[a] + b1 * t1[a] + b2 * t2[a]
        lo, hi = min(t0[a], t1[a], t2[a]), max(t0[a], t1[a], t2[a])
        out.append(min(hi, max(lo, v)))
    return tuple(out)


class Simplifier:
    """tris: [((v0, v1, v2), (a0, a1, a2))] with welded vertex ids and corner
    attributes (uv, normal, colour) where uv is a 2-tuple. positions: {id: xyz}."""

    def __init__(self, positions, tris, locked=()):
        self.pos = positions
        self.tv = [list(t[0]) for t in tris]
        self.ta = [list(t[1]) for t in tris]
        self.alive = [True] * len(tris)
        self.vt = {}
        for i, t in enumerate(self.tv):
            for v in t:
                self.vt.setdefault(v, set()).add(i)
        self.locked = set(locked)
        self.stamp = {v: 0 for v in self.vt}
        self.q = {v: [0.0] * 10 for v in self.vt}
        self.error = 0.0
        edges = {}
        for i, t in enumerate(self.tv):
            p = [positions[v] for v in t]
            n = _cross(_sub(p[1], p[0]), _sub(p[2], p[0]))
            ln = math.sqrt(_dot(n, n))
            if ln <= 0:
                continue
            n = (n[0] / ln, n[1] / ln, n[2] / ln)
            pq = _plane_quadric(n, p[0])
            for v in t:
                _qadd(self.q[v], pq)
            for k in range(3):
                a, b = t[k], t[(k + 1) % 3]
                edges.setdefault((min(a, b), max(a, b)), []).append((i, n, a, b))
        self.border = set()
        self.border_edges = set()
        for (a, b), users in edges.items():
            if len(users) == 1:
                _, n, x, y = users[0]
                self.border.update((a, b))
                self.border_edges.add((a, b))
                e = _sub(positions[y], positions[x])
                m = _cross(e, n)
                lm = math.sqrt(_dot(m, m))
                if lm > 0:
                    bq = _plane_quadric((m[0] / lm, m[1] / lm, m[2] / lm), positions[x])
                    _qadd(self.q[a], bq)
                    _qadd(self.q[b], bq)
        self.heap = []
        for a, b in edges:
            self._push(a, b)
            self._push(b, a)

    # ---- candidates
    def _cost(self, u, v):
        q = list(self.q[u])
        _qadd(q, self.q[v])
        return _qeval(q, self.pos[v])

    def _push(self, u, v):
        if u in self.locked:
            return
        if u in self.border and (min(u, v), max(u, v)) not in self.border_edges:
            return
        heapq.heappush(self.heap, (self._cost(u, v), u, v, self.stamp[u], self.stamp[v]))

    def _neighbours(self, v):
        out = set()
        for t in self.vt.get(v, ()):
            out.update(self.tv[t])
        out.discard(v)
        return out

    def _valid(self, u, v):
        if not any(v in self.tv[t] for t in self.vt[u]):
            return False  # the edge disappeared since this candidate was queued
        pv = self.pos[v]
        for t in self.vt[u]:
            tv = self.tv[t]
            if v in tv:
                continue
            p = [self.pos[x] for x in tv]
            n0 = _cross(_sub(p[1], p[0]), _sub(p[2], p[0]))
            p = [pv if x == u else self.pos[x] for x in tv]
            n1 = _cross(_sub(p[1], p[0]), _sub(p[2], p[0]))
            if _dot(n0, n1) < 0:
                return False
        if UV_GUARD is not None and not self._uv_kept(u, v):
            return False
        if COLOUR_GUARD is not None and not self._colour_kept(u, v):
            return False
        return True

    def _colour_kept(self, u, v):
        """Every surviving corner at u keeps its vertex colour within COLOUR_GUARD steps when moved to v."""
        wedge = {}
        v_col = None
        for t in self.vt[u]:
            tv = self.tv[t]
            if v in tv:
                ta = self.ta[t]
                wedge.setdefault(ta[tv.index(u)][0], ta[tv.index(v)][2])
                if v_col is None:
                    v_col = ta[tv.index(v)][2]
        if v_col is None:
            for t in self.vt[v]:
                v_col = self.ta[t][self.tv[t].index(v)][2]
                break
        for t in self.vt[u]:
            tv = self.tv[t]
            if v in tv:
                continue
            uv_u, _, c_u = self.ta[t][tv.index(u)]
            c_new = wedge.get(uv_u, v_col)
            if c_u is None or c_new is None or not isinstance(c_u, int):
                continue
            a, b = _c1555(c_u), _c1555(c_new)
            if max(abs(a[i] - b[i]) for i in range(3)) > COLOUR_GUARD:
                return False
        # the removed triangles' own corners at u vanish: their colour must also be representable by v's
        for t in self.vt[u]:
            tv = self.tv[t]
            if v in tv:
                ta = self.ta[t]
                c_u, c_v = ta[tv.index(u)][2], ta[tv.index(v)][2]
                if isinstance(c_u, int) and isinstance(c_v, int):
                    a, b = _c1555(c_u), _c1555(c_v)
                    if max(abs(a[i] - b[i]) for i in range(3)) > COLOUR_GUARD:
                        return False
        return True

    def _uv_kept(self, u, v):
        """Every surviving corner at u keeps its triangle's UV mapping when moved to v (see UV_GUARD)."""
        wedge = {}
        for t in self.vt[u]:
            tv = self.tv[t]
            if v in tv:
                ta = self.ta[t]
                wedge.setdefault(ta[tv.index(u)][0], ta[tv.index(v)][0])
        pv = self.pos[v]
        for t in self.vt[u]:
            tv = self.tv[t]
            if v in tv:
                continue
            ta = self.ta[t]
            k = tv.index(u)
            o1, o2 = tv[(k + 1) % 3], tv[(k + 2) % 3]
            uv_u = ta[k][0]
            want = _uv_affine(self.pos[u], self.pos[o1], self.pos[o2], uv_u, ta[(k + 1) % 3][0], ta[(k + 2) % 3][0], pv)
            if want is None:
                return False
            got = wedge[uv_u] if uv_u in wedge else _uv_extrapolate(
                self.pos[u], self.pos[o1], self.pos[o2], uv_u, ta[(k + 1) % 3][0], ta[(k + 2) % 3][0], pv)
            if abs(got[0] - want[0]) > UV_GUARD or abs(got[1] - want[1]) > UV_GUARD:
                return False
        return True

    def _collapse(self, u, v):
        removed = [t for t in self.vt[u] if v in self.tv[t]]
        wedge = {}
        for t in removed:
            tv, ta = self.tv[t], self.ta[t]
            wedge.setdefault(ta[tv.index(u)][0], ta[tv.index(v)])
        v_attr = self.ta[removed[0]][self.tv[removed[0]].index(v)] if removed else None
        if v_attr is None:
            for t in self.vt[v]:
                v_attr = self.ta[t][self.tv[t].index(v)]
                break
        for t in removed:
            self.alive[t] = False
            for x in self.tv[t]:
                if x != u:
                    self.vt[x].discard(t)
        pv = self.pos[v]
        for t in list(self.vt[u]):
            if not self.alive[t]:
                continue
            tv, ta = self.tv[t], self.ta[t]
            k = tv.index(u)
            uv_u, n_u, c_u = ta[k]
            if uv_u in wedge:
                ta[k] = wedge[uv_u]
            else:
                o1, o2 = tv[(k + 1) % 3], tv[(k + 2) % 3]
                uv = _uv_extrapolate(self.pos[u], self.pos[o1], self.pos[o2], uv_u, ta[(k + 1) % 3][0],
                                     ta[(k + 2) % 3][0], pv)
                ta[k] = (uv, v_attr[1], v_attr[2])
            tv[k] = v
            self.vt[v].add(t)
        del self.vt[u]
        _qadd(self.q[v], self.q[u])
        if u in self.border:
            self.border.discard(u)
            self.border_edges = {e for e in self.border_edges if u not in e} | \
                {(min(v, w), max(v, w)) for (a, b) in self.border_edges if u in (a, b)
                 for w in (a, b) if w != u and w != v}
        self.stamp[u] += 1
        self.stamp[v] += 1
        self._dedupe(v)
        for w in self._neighbours(v):
            self._push(v, w)
            self._push(w, v)

    def _dedupe(self, v):
        """Drop degenerate triangles and folded/duplicated pairs around v."""
        seen = {}
        for t in list(self.vt.get(v, ())):
            tv = self.tv[t]
            if len(set(tv)) < 3:
                self._kill(t)
                continue
            key = frozenset(tv)
            if key in seen:
                o = seen.pop(key)
                ov = self.tv[o]
                # same cyclic order: duplicate; opposite: zero-thickness fold
                i = ov.index(tv[0])
                same = ov[(i + 1) % 3] == tv[1]
                self._kill(t)
                if not same:
                    self._kill(o)
            else:
                seen[key] = t

    def _kill(self, t):
        if not self.alive[t]:
            return
        self.alive[t] = False
        for x in set(self.tv[t]):
            if x in self.vt:
                self.vt[x].discard(t)

    def run_to(self, eps):
        limit = eps * eps
        h = self.heap
        while h and h[0][0] <= limit:
            cost, u, v, su, sv = heapq.heappop(h)
            if u not in self.vt or v not in self.vt or self.stamp[u] != su or self.stamp[v] != sv:
                continue
            if not self.vt[u] or not self._valid(u, v):
                continue
            self.error = max(self.error, math.sqrt(cost))
            self._collapse(u, v)
        self._drop_small(eps)

    def _drop_small(self, eps):
        live = [t for t in range(len(self.tv)) if self.alive[t]]
        parent = {}

        def find(a):
            while parent.setdefault(a, a) != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        for t in live:
            a = find(self.tv[t][0])
            for x in self.tv[t][1:]:
                b = find(x)
                if a != b:
                    parent[b] = a
        comps = {}
        for t in live:
            comps.setdefault(find(self.tv[t][0]), []).append(t)
        for ts in comps.values():
            vs = {x for t in ts for x in self.tv[t]}
            if vs & self.locked:
                continue
            ps = [self.pos[x] for x in vs]
            c = [(min(p[a] for p in ps) + max(p[a] for p in ps)) * 0.5 for a in range(3)]
            r = max(math.sqrt(_dot(_sub(p, c), _sub(p, c))) for p in ps)
            if r <= eps:
                self.error = max(self.error, r)
                for t in ts:
                    self._kill(t)

    def triangles(self):
        return [(tuple(self.tv[t]), tuple(self.ta[t])) for t in range(len(self.tv)) if self.alive[t]]


def weld(points):
    """Exact-coordinate welding: returns (id per input index, {id: xyz})."""
    ids, out, where = [], {}, {}
    for p in points:
        k = where.get(p)
        if k is None:
            k = where[p] = len(out)
            out[k] = p
        ids.append(k)
    return ids, out


def components(tris):
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for t in tris:
        a = find(t[0][0])
        for x in t[0][1:]:
            b = find(x)
            if a != b:
                parent[b] = a
    comps = {}
    for i, t in enumerate(tris):
        comps.setdefault(find(t[0][0]), []).append(i)
    return list(comps.values())


def tree_groups(tris, positions, trunk_height):
    """Split a grove BIN into its trees: connected components (shared welded
    vertices), each joined to the trunk nearest in x/z, a trunk being a
    component taller than trunk_height (model units). -> [[triangle index]]
    per tree, ordered by first triangle, or None with fewer than two trunks
    (a single tree or not a tree: the caller clusters it as before)."""
    comps = components(tris)
    info = []
    for c in comps:
        vs = sorted({v for i in c for v in tris[i][0]})
        ys = [positions[v][1] for v in vs]
        info.append((max(ys) - min(ys), sum(positions[v][0] for v in vs) / len(vs),
                     sum(positions[v][2] for v in vs) / len(vs)))
    trunks = [k for k, (h, _, _) in enumerate(info) if h > trunk_height]
    if len(trunks) < 2:
        return None
    groups = {t: [] for t in trunks}
    for k, (_, x, z) in enumerate(info):
        t = min(trunks, key=lambda t: ((x - info[t][1]) ** 2 + (z - info[t][2]) ** 2, t))
        groups[t].extend(comps[k])
    return sorted((sorted(g) for g in groups.values()), key=lambda g: g[0])


def is_card_field(tris, alpha):
    """Alpha parts made of many tiny components (grass, leaf and litter cards)."""
    if not alpha:
        return False
    comps = components(tris)
    if len(comps) < 24:
        return False
    sizes = sorted(len({x for i in c for x in tris[i][0]}) for c in comps)
    return sizes[len(sizes) // 2] <= 8


def _radical_inverse(i):
    r, f = 0.0, 0.5
    while i:
        if i & 1:
            r += f
        i >>= 1
        f *= 0.5
    return r


def card_levels(tris, positions, keeps):
    """Stratified thinning: cards ordered along a Morton curve get van der
    Corput ranks, so every level keeps an even spatial subset."""
    comps = components(tris)
    cents = []
    for c in comps:
        ps = [positions[x] for i in c for x in tris[i][0]]
        cents.append(tuple(sum(p[a] for p in ps) / len(ps) for a in range(3)))
    lo = [min(c[a] for c in cents) for a in range(3)]
    hi = [max(c[a] for c in cents) for a in range(3)]

    def morton(c):
        q = [min(1023, int((c[a] - lo[a]) / max(hi[a] - lo[a], 1e-9) * 1023)) for a in range(3)]
        m = 0
        for bit in range(10):
            for a in (0, 2, 1):
                m = (m << 1) | ((q[a] >> (9 - bit)) & 1)
        return m
    order = sorted(range(len(comps)), key=lambda i: morton(cents[i]))
    rank = {c: _radical_inverse(n) for n, c in enumerate(order)}
    out = []
    for keep in keeps:
        out.append([tris[i] for ci, c in enumerate(comps) if rank[ci] < keep for i in c])
    return out


def simplify_levels(positions, tris, eps_list, locked=(), min_gain=0.8):
    """-> [(error, tris)] starting with (0, tris). A level is kept only when it
    has at most min_gain of the previous kept level's triangles."""
    s = Simplifier(positions, tris, locked)
    levels = [(0.0, tris)]
    for eps in eps_list:
        s.run_to(eps)
        cur = s.triangles()
        if len(cur) <= min_gain * len(levels[-1][1]):
            levels.append((max(s.error, 1e-6), cur))
        if not cur:
            break
    return levels


# stripify() uses stripify_swaps() when this is set (converter --strip-swaps).
STRIP_SWAPS = False


def strip_triangles_of(s):
    """Triangles a strip draws in GX/PVR order (odd triangles swap their first
    two corners), skipping degenerate ones (a repeated corner draws nothing)."""
    out = []
    for i in range(len(s) - 2):
        a, b, c = s[i], s[i + 1], s[i + 2]
        if i % 2:
            a, b = b, a
        if a != b and b != c and a != c:
            out.append((a, b, c))
    return out


def _canon(t):
    """Rotation-invariant, winding-preserving key of a triangle."""
    a, b, c = t
    return min((a, b, c), (b, c, a), (c, a, b))


def stripify_swaps(tris):
    """Winding-preserving stripifier that turns with swaps. A plain strip must
    alternate left/right turns; when the next triangle is across the other edge
    of the last one, the strip repeats a corner (s[-3] inserted before s[-1]:
    one zero-area triangle, which draws nothing) instead of ending, so a swap
    costs one corner where a restart costs two plus a strip. Seeds are the
    unused triangles with the fewest unused neighbours (best of three seed
    rotations). The drawn triangle set equals the input exactly (checked)."""
    tris = [tuple(t) for t in tris if len(set(t)) == 3]
    by_pair = {}
    for n, t in enumerate(tris):
        for i in range(3):
            by_pair.setdefault(frozenset((t[i], t[(i + 1) % 3])), []).append(n)
    used = [False] * len(tris)
    canon = [_canon(t) for t in tris]

    def degree(n):
        t = tris[n]
        return sum(1 for i in range(3) for m in by_pair[frozenset((t[i], t[(i + 1) % 3]))]
                   if m != n and not used[m])

    def extend(s, taken):
        """Best unused triangle continuing strip s (no swap); returns (degree, n, x) or None."""
        best = None
        for m in by_pair.get(frozenset((s[-2], s[-1])), ()):
            if used[m] or m in taken:
                continue
            t = tris[m]
            x = next((v for v in t if v != s[-2] and v != s[-1]), None)
            if x is None:
                continue
            i = len(s) - 2
            a, b, c = s[-2], s[-1], x
            if i % 2:
                a, b = b, a
            if _canon((a, b, c)) != canon[m]:
                continue
            d = degree(m)
            if best is None or d < best[0]:
                best = (d, m, x)
        return best

    def grow(seed_n, rot):
        t = tris[seed_n]
        s, taken = list(t[rot:] + t[:rot]), {seed_n}
        while True:
            nxt = extend(s, taken)
            if nxt is not None:
                taken.add(nxt[1]); s.append(nxt[2]); continue
            if len(s) < 3:
                break
            s2 = s[:-1] + [s[-3], s[-1]]
            nxt = extend(s2, taken)
            if nxt is None:
                break
            taken.add(nxt[1]); s = s2 + [nxt[2]]
        return s, taken

    heap = [(degree(n), n) for n in range(len(tris))]
    heapq.heapify(heap)
    strips = []
    while heap:
        d, n = heapq.heappop(heap)
        if used[n]:
            continue
        now = degree(n)
        if now != d:
            heapq.heappush(heap, (now, n))
            continue
        best = None
        for r in range(3):
            s, taken = grow(n, r)
            if best is None or len(taken) > len(best[1]) or (len(taken) == len(best[1]) and len(s) < len(best[0])):
                best = (s, taken)
        for m in best[1]:
            used[m] = True
        strips.append(best[0])
    # Exactness: the strips draw the input triangles, each once, same winding.
    drawn = sorted(_canon(t) for s in strips for t in strip_triangles_of(s))
    if drawn != sorted(canon):
        raise AssertionError('stripify_swaps: drawn triangles differ from the input')
    return strips


def stripify(tris):
    """Winding-preserving stripifier (GX/PVR order: odd triangles swap their
    first two corners). Seeds are the unused triangles with the fewest unused
    neighbours; each strip grows forward (best of three seed rotations, next
    triangle chosen by fewest unused neighbours) and then backward two
    triangles at a time, which keeps the first triangle's parity."""
    if STRIP_SWAPS:
        return stripify_swaps(tris)
    tris = [tuple(t) for t in tris if len(set(t)) == 3]
    edge = {}
    for n, (a, b, c) in enumerate(tris):
        for e, x in (((a, b), c), ((b, c), a), ((c, a), b)):
            edge.setdefault(e, []).append((n, x))
    used = [False] * len(tris)

    def degree(n):
        a, b, c = tris[n]
        return sum(1 for e in ((b, a), (c, b), (a, c)) for m, _ in edge.get(e, ()) if not used[m] and m != n)

    def pick(key, taken):
        best = None
        for n, x in edge.get(key, ()):
            if not used[n] and n not in taken:
                d = degree(n)
                if best is None or d < best[0]:
                    best = (d, n, x)
        return best

    def grow(seed):
        s, taken = list(seed[1]), [seed[0]]
        while True:
            k = len(s) - 2
            key = (s[k], s[k + 1]) if k % 2 == 0 else (s[k + 1], s[k])
            nxt = pick(key, taken)
            if nxt is None:
                break
            taken.append(nxt[1])
            s.append(nxt[2])
        # Backward, in pairs: (y2, y1, s0, s1, ...) needs (s0, y1, s1) then (y2, y1, s0).
        while True:
            t1 = pick((s[1], s[0]), taken)
            if t1 is None:
                break
            y1 = t1[2]
            taken.append(t1[1])
            t0 = pick((y1, s[0]), taken)
            if t0 is None:
                taken.pop()
                break
            taken.append(t0[1])
            s = [t0[2], y1] + s
        return s, taken

    heap = [(degree(n), n) for n in range(len(tris))]
    heapq.heapify(heap)
    strips = []
    while heap:
        d, n = heapq.heappop(heap)
        if used[n]:
            continue
        now = degree(n)
        if now != d:
            heapq.heappush(heap, (now, n))
            continue
        t = tris[n]
        best = None
        for r in range(3):
            s, taken = grow((n, t[r:] + t[:r]))
            if best is None or len(taken) > len(best[1]):
                best = (s, taken)
        for m in best[1]:
            used[m] = True
        strips.append(best[0])
    return strips


def split_to_limit(s, limit):
    """Pieces of strip s with at most `limit` distinct corners each; each piece after the first restarts two corners
    back at an even triangle (convert_room_bins split_strip's rule), so the triangles and their winding are kept."""
    out, start = [], 0
    while start < len(s) - 2:
        end, seen = start, set()
        while end < len(s) and len(seen | {s[end]}) <= limit:
            seen.add(s[end])
            end += 1
        if end < len(s) and (end - 2 - start) % 2:
            end -= 1
        assert end - start >= 3, 'meshlet limit too small (needs >= 4 corners)'
        out.append(s[start:end])
        if end >= len(s):
            break
        start = end - 2
    return out


def pack_meshlets(strips, limit=256, point=None):
    """Greedy vertex-reuse packing (after dca3-game's processGeom): a meshlet
    repeatedly takes the strip adding the fewest new vertices until full; ties
    go to the strip nearest the meshlet's seed (point(key) -> xyz), then to the
    longest, so meshlets stay spatially compact for culling."""
    def centre(s):
        if point is None:
            return (0.0, 0.0, 0.0)
        ps = [point(k) for k in s]
        return tuple(sum(p[a] for p in ps) / len(ps) for a in range(3))
    pending = [(s, centre(s)) for s in sorted(strips, key=len, reverse=True)]
    out = []
    while pending:
        cur, keys = [], set()
        seed = None
        while pending:
            best = None
            for i, (s, c) in enumerate(pending):
                new = len(set(s) - keys)
                if len(keys) + new > limit:
                    continue
                d = 0.0 if seed is None else (c[0] - seed[0]) ** 2 + (c[1] - seed[1]) ** 2 + (c[2] - seed[2]) ** 2
                score = (new, d, -len(s))
                if best is None or score < best[0]:
                    best = (score, i)
            if best is None:
                if not cur:
                    # No strip fits an empty meshlet: a strip alone has more than `limit` distinct corners (a long
                    # strip under a small limit, e.g. 64). Split it into pieces that fit. Only reached where this
                    # loop used to append empty meshlets forever, so every input that converted before is unchanged.
                    s, c = pending.pop(0)
                    pending[0:0] = [(p, centre(p)) for p in split_to_limit(s, limit)]
                    continue
                break
            s, c = pending.pop(best[1])
            if seed is None:
                seed = c
            cur.append(s)
            keys.update(s)
        out.append(cur)
    return out


def kd_clusters(tris, positions, max_tris, max_extent, min_extent, min_tris=64):
    """Median splits along the longest axis while a cluster spans more than
    max_extent, or holds more than max_tris triangles and spans more than
    min_extent (model units). Compact objects (trees) stay whole: every split
    locks its shared border in all levels."""
    def cent(t):
        return [sum(positions[v][a] for v in t[0]) / 3.0 for a in range(3)]
    out, work = [], [tris]
    while work:
        ts = work.pop()
        cs = [cent(t) for t in ts]
        lo = [min(c[a] for c in cs) for a in range(3)]
        hi = [max(c[a] for c in cs) for a in range(3)]
        ext = [hi[a] - lo[a] for a in range(3)]
        axis = ext.index(max(ext))
        if len(ts) < 2 * min_tris or not (ext[axis] > max_extent or (len(ts) > max_tris and ext[axis] > min_extent)):
            out.append(ts)
            continue
        order = sorted(range(len(ts)), key=lambda i: cs[i][axis])
        half = len(order) // 2
        work.append([ts[i] for i in order[:half]])
        work.append([ts[i] for i in order[half:]])
    return out
