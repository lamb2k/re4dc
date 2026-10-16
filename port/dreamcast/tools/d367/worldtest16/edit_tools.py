"""edit_tools.py <tools dir>: worldtest16 B tool fixes (mesh_lod.KEEP_PIECES; ladder --mode terrain, --keep-walk-mm,
--keep-pieces, --class-report)."""
import sys, os
D = sys.argv[1]


def edit(path, pairs):
    s = open(path).read()
    for a, b in pairs:
        assert s.count(a) == 1, (path, a[:60], s.count(a))
        s = s.replace(a, b)
    open(path, 'w').write(s)


edit(os.path.join(D, 'mesh_lod.py'), [
    ("""VERTEX_EPS = None
""", """VERTEX_EPS = None
# KEEP_PIECES (False = the historical behaviour; ps2_world_vert_ladder.py --keep-pieces, lane worldtest16 2026-10-16): no
# connected piece is ever deleted. _drop_small drops nothing, and a collapse that would remove the last live triangles
# of a piece (a plank, post, chair leg, branch or grass card folding away) is refused. In game the reduction deleted
# whole planks, chair legs, tree trunks and fence rails next to the camera (worldtest16 sheets).
KEEP_PIECES = False
"""),
    ("""        self.heap = []
        for a, b in edges:
            self._push(a, b)
            self._push(b, a)
""", """        self.heap = []
        for a, b in edges:
            self._push(a, b)
            self._push(b, a)
        if KEEP_PIECES:
            par = {}

            def find(a):
                while par.setdefault(a, a) != a:
                    par[a] = par[par[a]]
                    a = par[a]
                return a
            for t in self.tv:
                r0 = find(t[0])
                for x in t[1:]:
                    r1 = find(x)
                    if r0 != r1:
                        par[r1] = r0
            self.comp = {v: find(v) for v in self.vt}
            self.comp_live = {}
            for t in self.tv:
                c = self.comp[t[0]]
                self.comp_live[c] = self.comp_live.get(c, 0) + 1
"""),
    ("""    def _valid(self, u, v):
        if not any(v in self.tv[t] for t in self.vt[u]):
            return False  # the edge disappeared since this candidate was queued
""", """    def _valid(self, u, v):
        if not any(v in self.tv[t] for t in self.vt[u]):
            return False  # the edge disappeared since this candidate was queued
        if KEEP_PIECES:
            gone = sum(1 for t in self.vt[u] if v in self.tv[t])
            if self.comp_live[self.comp[u]] - gone < 2:
                return False  # the piece would fold away: keep it
"""),
    ("""        for t in removed:
            self.alive[t] = False
            for x in self.tv[t]:
""", """        for t in removed:
            self.alive[t] = False
            if KEEP_PIECES:
                self.comp_live[self.comp[u]] -= 1
            for x in self.tv[t]:
"""),
    ("""    def _kill(self, t):
        if not self.alive[t]:
            return
        self.alive[t] = False
""", """    def _kill(self, t):
        if not self.alive[t]:
            return
        self.alive[t] = False
        if KEEP_PIECES:
            self.comp_live[self.comp[self.tv[t][0]]] -= 1
"""),
    ("""    def _drop_small(self, eps):
        live = [t for t in range(len(self.tv)) if self.alive[t]]
""", """    def _drop_small(self, eps):
        if KEEP_PIECES:
            return
        live = [t for t in range(len(self.tv)) if self.alive[t]]
"""),
])

L = os.path.join(D, 'ps2_world_vert_ladder.py')
edit(L, [
    ("""        self.cache = {}

    def l0(self, row):""", """        self.cache = {}
        self.part_class = classify_parts(self, a) if getattr(a, 'mode', 'all') == 'terrain' else {}

    def l0(self, row):"""),
    ("""                if (inf['bin'] in self.protect and inf['mesh'] not in self.baked) or inf['mesh'] in self.protect_meshes \\
                        or px <= 0:""", """                if (inf['bin'] in self.protect and inf['mesh'] not in self.baked) or inf['mesh'] in self.protect_meshes \\
                        or px <= 0 or (getattr(a, 'mode', 'all') == 'terrain' and self.part_class.get(pi, {}).get('cls') != 'terrain'):"""),
    ("""            q = a.near_px if (a.near_px is not None and d < a.near_mm) else px
            return min(q * max(d, a.min_eye_mm) / a.focal_px, a.max_error_mm) / scale""", """            if d < getattr(a, 'keep_walk_mm', 0.0):
                return 0.0   # --keep-walk-mm: along the walk path nothing moves
            q = a.near_px if (a.near_px is not None and d < a.near_mm) else px
            return min(q * max(d, a.min_eye_mm) / a.focal_px, a.max_error_mm) / scale"""),
    ("""    ap.add_argument('--list-near', help='X,Z,R: list mesh bins with a cluster within R mm of (X, Z) and stop')""",
     """    ap.add_argument('--list-near', help='X,Z,R: list mesh bins with a cluster within R mm of (X, Z) and stop')
    ap.add_argument('--mode', choices=('all', 'terrain'), default='all',
                    help='terrain: reduce only the parts classified as terrain / rock / cliff (classify_parts); every '
                         'structure part (walls, roofs, beams, planks, posts, furniture, trunks, cut-out cards) keeps level 0')
    ap.add_argument('--keep-walk-mm', type=float, default=0.0,
                    help='per-vertex mode: vertices closer than this to the walkable area (walk field distance) never move')
    ap.add_argument('--keep-pieces', action='store_true', help='mesh_lod.KEEP_PIECES: never delete a connected piece')
    ap.add_argument('--class-report', help='write the per-part terrain / structure classification (JSON)')"""),
    ("""    mesh_lod.COLOUR_GUARD = a.colour_guard if a.colour_guard >= 0 else None
    L = Ladder(a)""", """    mesh_lod.COLOUR_GUARD = a.colour_guard if a.colour_guard >= 0 else None
    mesh_lod.KEEP_PIECES = a.keep_pieces
    L = Ladder(a)
    if a.class_report:
        json.dump(dict(rule=CLASS_RULE, parts=L.part_class), open(a.class_report, 'w'), indent=0)"""),
    ("""class Ladder:""", '''CLASS_RULE = ('terrain = opaque pass AND planarity < 0.55 (area share within 10 deg of the part\\'s 6 strongest normal '
              'directions) AND >= 70% of the area in connected pieces at least 4 m wide in both horizontal axes; '
              'everything else (planar walls/roofs, beams, planks, posts, trunks, furniture, cut-out cards) is structure')


def classify_parts(L, a):
    """{part: {cls, planarity, big_share, area_m2, pass}}: terrain / rock / cliff vs structure, from level-0 geometry in
    world space (the mesh's first placement). Structure is the default; terrain must be irregular (low planarity: rock,
    cliff, uneven ground) and made of large pieces (no posts, planks, trunks or furniture)."""
    src = L.src
    passes, _ = F.read_sidecar(a.sidecar, len(src['parts']))
    out = {}
    for pi, part in enumerate(src['parts']):
        mi = L.part_mesh[pi]
        mesh = src['meshes'][mi]
        pls = L.mesh_pls.get(mi) or [((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0))]
        aff = pls[0]
        lets = [li for row in L.plan[pi] for li in L.l0(row)]
        pos, ids, tris = F.triangles_of(src, lets, part, mesh)
        W = {k: tuple(aff[r][0] * p[0] + aff[r][1] * p[1] + aff[r][2] * p[2] + aff[r][3] for r in range(3)) for k, p in pos.items()}
        par = {}

        def find(x):
            while par.setdefault(x, x) != x:
                par[x] = par[par[x]]
                x = par[x]
            return x
        normals, area = [], 0.0
        for t, _ in tris:
            p0, p1, p2 = W[t[0]], W[t[1]], W[t[2]]
            e1 = [p1[k] - p0[k] for k in range(3)]; e2 = [p2[k] - p0[k] for k in range(3)]
            n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
            ln = math.sqrt(sum(x * x for x in n))
            if ln > 0:
                normals.append(((n[0] / ln, n[1] / ln, n[2] / ln), ln * 0.5))
                area += ln * 0.5
            r0 = find(t[0])
            for x in t[1:]:
                r1 = find(x)
                if r0 != r1:
                    par[r1] = r0
        # planarity: greedy 6 dominant directions (sign-free), area share within 10 degrees
        cos10 = math.cos(math.radians(10)); left = list(normals); covered = 0.0
        for _ in range(6):
            if not left:
                break
            best, bw = None, -1.0
            for n, w in left[:: max(1, len(left) // 200)]:
                s = sum(ww for m, ww in left if abs(n[0] * m[0] + n[1] * m[1] + n[2] * m[2]) >= cos10)
                if s > bw:
                    best, bw = n, s
            covered += bw
            left = [(m, ww) for m, ww in left if abs(best[0] * m[0] + best[1] * m[1] + best[2] * m[2]) < cos10]
        planar = covered / area if area > 0 else 1.0
        # piece sizes
        box, parea = {}, {}
        for t, _ in tris:
            c = find(t[0])
            b = box.setdefault(c, [1e18, 1e18, -1e18, -1e18])
            for k in t:
                x, z = W[k][0], W[k][2]
                b[0] = min(b[0], x); b[1] = min(b[1], z); b[2] = max(b[2], x); b[3] = max(b[3], z)
        for t, _ in tris:
            p0, p1, p2 = W[t[0]], W[t[1]], W[t[2]]
            e1 = [p1[k] - p0[k] for k in range(3)]; e2 = [p2[k] - p0[k] for k in range(3)]
            n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
            c = find(t[0]); parea[c] = parea.get(c, 0.0) + 0.5 * math.sqrt(sum(x * x for x in n))
        big = sum(parea[c] for c, b in box.items() if min(b[2] - b[0], b[3] - b[1]) >= 4000.0)
        big_share = big / area if area > 0 else 0.0
        terrain = passes[pi] == 0 and planar < 0.55 and big_share >= 0.70
        out[pi] = dict(cls='terrain' if terrain else 'structure', planarity=round(planar, 3), big_share=round(big_share, 3),
                       area_m2=round(area / 1e6, 1), pass_=passes[pi], bin=mesh[0], pieces=len(box))
    return out


class Ladder:'''),
])
print('edited')
