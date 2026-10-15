#!/usr/bin/env python3
"""ps2_world_far_lod.py IN.re4mesh OUT.re4mesh --sidecar R4PW [--table worldlod-rooms.json --room r119]
                        [--max-error-px 1] [--walk WALK.json] [--report R.json]

Offline world distance LOD for a PS2 world package (R4IM v3, prelit; lane worldlod 2026-10-15, backlog C1).

Rules (user 10-15, the same in every room):
- One look floor for the whole game: a screen-space error ceiling, --max-error-px pixels at 640x480 (focal --focal-px,
  fovy 50) at the switch distance minus the hysteresis band (WORLD_LOD_MM - WORLD_LOD_HYST_MM, 11.5 m). It becomes a
  geometric ceiling in model units per mesh (placement scale included). A room that cannot reach its target stops at
  the floor and never goes below it. The table's floor_px is the game-wide value; --max-error-px overrides it for tests.
- Near field untouched: full detail inside the switch distance (the runtime, WORLD_LOD=1).
- Landmarks protected: meshes on the table's per-area protected list (by room and mesh bin) get no far level.
- Textures unchanged: only geometry is reduced; UV guard (--uv-guard) and vertex-colour guard (--colour-guard, baked
  lighting gradients) refuse collapses that would shear a texture or flatten a lighting gradient.
- No popping: one fixed switch distance with a hysteresis band (runtime); no fades.
- No streaming and no load-time growth (replace, don't add): with --walk (walkable points of the room's collision,
  tools/d367/worldlod/walk.py), a cluster whose every placement stays beyond --far-only-mm of every walkable point is
  never seen inside the switch distance, so its level 0 is REPLACED by the reduced mesh (a net saving). Clusters seen
  near and far get an ADDITIVE far level only while the package stays within --max-growth bytes of its input (default
  0), best triangles saved per byte first. Unreferenced meshlets and vertex records are dropped (pools compacted).
- Rooms the table marks untouched (no Ganados, or already under target) are copied unchanged (exit before writing
  anything else when --table says so: the caller ships the source package).

The far level (additive) is written as indexed meshlets into its part's vertex pool and carries the marker error
FAR_ERROR (1e30): the runtime's screen-space selection never reaches it, so a build without the game knob WORLD_LOD
draws additive clusters exactly as before; replaced clusters draw their reduced level 0 in every build (data change).
With WORLD_LOD=1 (native_static.cpp) a cluster farther than 12 m (+- 0.5 m hysteresis) whose screen-space choice is
level 0 draws its far level. The far plane is unchanged. Run tools/ps2_strip_groups.py on the output afterwards when
the room ships strip groups. The report lists every output cluster with its source cluster (for per-cluster tables
such as an occlusion PVS: build those on the final package or map them through `src_cluster`).
"""
import argparse, json, math, struct, sys, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mesh_lod  # noqa: E402
import convert_room_bins as crb  # noqa: E402

HEADER = struct.Struct('<4s19I')
LOD_HEADER = struct.Struct('<8I')
MESH = struct.Struct('<HBBHHIII12f')
PART = struct.Struct('<IIBBBBII4f')
MESHLET = struct.Struct('<IIIHH6H')
VERTEX = struct.Struct('<6H')
PART_LOD = struct.Struct('<II')
CLUSTER = struct.Struct('<6HII')
LEVEL = struct.Struct('<IIf')
INDEXED = 0x8000
FAR_ERROR = 1.0e30
MAX_LET_VERTICES = 256


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def read(blob):
    h = HEADER.unpack_from(blob, 0)
    magic, version, nbytes, crc, nmesh, npart, nlet, nvert, nstrip, npal, o_mesh, o_part, o_let, o_vert, o_strip, \
        o_pal = h[:16]
    reserved = h[16:20]
    assert magic == b'R4IM' and version == 3 and nbytes == len(blob), (magic, version, nbytes, len(blob))
    assert reserved[0] == 2 and reserved[1:] == (0, 0, 0), ('prelit packages only', reserved)
    lod = LOD_HEADER.unpack_from(blob, 80)
    ncl, nlv, o_plod, o_cl, o_lv, o_class, o_rule, o_res = lod
    assert o_class == 0 and o_rule == 0 and o_res == 0, ('class / rule / impostor tables are not carried', lod)
    assert zlib.crc32(blob[80:]) == crc, 'header crc'
    p = dict(
        meshes=[list(MESH.unpack_from(blob, o_mesh + MESH.size * i)) for i in range(nmesh)],
        parts=[list(PART.unpack_from(blob, o_part + PART.size * i)) for i in range(npart)],
        lets=[list(MESHLET.unpack_from(blob, o_let + MESHLET.size * i)) for i in range(nlet)],
        verts=[VERTEX.unpack_from(blob, o_vert + VERTEX.size * i) for i in range(nvert)],
        strip=bytes(blob[o_strip:o_strip + nstrip]),
        pal=[struct.unpack_from('<I', blob, o_pal + 4 * i)[0] for i in range(npal)],
        plods=[list(PART_LOD.unpack_from(blob, o_plod + PART_LOD.size * i)) for i in range(npart)],
        clusters=[list(CLUSTER.unpack_from(blob, o_cl + CLUSTER.size * i)) for i in range(ncl)],
        levels=[list(LEVEL.unpack_from(blob, o_lv + LEVEL.size * i)) for i in range(nlv)])
    return p


def write(p):
    head = HEADER.size + LOD_HEADER.size
    body = bytearray()
    offsets = {}
    for name, blob in (('mesh', b''.join(MESH.pack(*m) for m in p['meshes'])),
                       ('part', b''.join(PART.pack(*x) for x in p['parts'])),
                       ('meshlet', b''.join(MESHLET.pack(*m) for m in p['lets'])),
                       ('vertex', b''.join(VERTEX.pack(*v) for v in p['verts'])),
                       ('index', bytes(p['strip'])),
                       ('palette', b''.join(struct.pack('<I', c) for c in p['pal'])),
                       ('part_lod', b''.join(PART_LOD.pack(*x) for x in p['plods'])),
                       ('cluster', b''.join(CLUSTER.pack(*c) for c in p['clusters'])),
                       ('level', b''.join(LEVEL.pack(*l) for l in p['levels']))):
        start = crb.align(head + len(body)) - head
        body.extend(b'\0' * (start - len(body)))
        offsets[name] = head + len(body)
        body.extend(blob)
    body.extend(b'\0' * (crb.align(head + len(body)) - head - len(body)))
    lod = LOD_HEADER.pack(len(p['clusters']), len(p['levels']), offsets['part_lod'], offsets['cluster'],
                          offsets['level'], 0, 0, 0)
    body = lod + bytes(body)
    total = HEADER.size + len(body)
    header = HEADER.pack(b'R4IM', 3, total, zlib.crc32(body), len(p['meshes']), len(p['parts']), len(p['lets']),
                         len(p['verts']), len(p['strip']), len(p['pal']), offsets['mesh'], offsets['part'],
                         offsets['meshlet'], offsets['vertex'], offsets['index'], offsets['palette'], 2, 0, 0, 0)
    return header + body


def let_corners(p, m):
    """-> (pool vertex index per local corner, [strip corner lists]) of meshlet record m."""
    first_vertex, first_strip, strip_bytes, nv, sc = m[0], m[1], m[2], m[3], m[4]
    s = p['strip']
    if sc & INDEXED:
        table = struct.unpack_from('<%dH' % nv, s, first_strip)
        corners = [first_vertex + o for o in table]
        at = first_strip + 2 * nv
    else:
        corners = [first_vertex + k for k in range(nv)]
        at = first_strip
    end = at + strip_bytes
    strips = []
    while at < end:
        n = s[at]
        strips.append(list(s[at + 1:at + 1 + n]))
        at += 1 + n
    assert len(strips) == (sc & (INDEXED - 1))
    return corners, strips


def part_pool(p, pi):
    """[lo, hi) of the vertex records part pi's meshlets read."""
    part = p['parts'][pi]
    lo, hi = None, None
    for li in range(part[6], part[6] + part[7]):
        corners, _ = let_corners(p, p['lets'][li])
        a, b = min(corners), max(corners) + 1
        lo = a if lo is None else min(lo, a)
        hi = b if hi is None else max(hi, b)
    return lo, hi


def let_box(m):
    return m[5:8], m[8:11]


def split_groups(p, lets, step, limit):
    """Level-0 meshlets of one cluster -> groups (lists, source order kept) whose box extent (model units) is <= limit,
    by halving the widest axis at the median meshlet centre (a single meshlet is never split)."""
    def extent(g):
        lo = [min(p['lets'][i][5 + a] for i in g) for a in range(3)]
        hi = [max(p['lets'][i][8 + a] for i in g) for a in range(3)]
        return [(hi[a] - lo[a]) * abs(step[a]) for a in range(3)]
    out, todo = [], [list(lets)]
    while todo:
        g = todo.pop()
        e = extent(g)
        if len(g) < 2 or max(e) <= limit:
            out.append(sorted(g))
            continue
        ax = e.index(max(e))
        g2 = sorted(g, key=lambda i: p['lets'][i][5 + ax] + p['lets'][i][8 + ax])
        h = len(g2) // 2
        todo += [g2[:h], g2[h:]]
    return sorted(out, key=lambda g: g[0])


def triangles_of(p, lets, part, mesh):
    """Welded triangles of a meshlet list: (pos {id: xyz model units}, ids {grid: id}, [(ids, attrs)])."""
    step, origin = mesh[11:14], mesh[8:11]
    uvb, uvs = part[8:10], part[10:12]
    pos, ids, tris = {}, {}, []
    for li in lets:
        corners, strips = let_corners(p, p['lets'][li])
        for s in strips:
            for t in crb.strip_triangles(s):
                vs = [p['verts'][corners[k]] for k in t]
                g = [tuple(v[:3]) for v in vs]
                if len(set(g)) < 3:
                    continue
                for x in g:
                    if x not in ids:
                        ids[x] = len(ids)
                        pos[ids[x]] = tuple(origin[k] + step[k] * x[k] for k in range(3))
                attrs = tuple(((uvb[0] + uvs[0] * v[3], uvb[1] + uvs[1] * v[4]), None, v[5]) for v in vs)
                tris.append((tuple(ids[x] for x in g), attrs))
    return pos, ids, tris


def far_level(p, lets, part, mesh, locked_pos, a, max_error):
    """-> (kept, source tris, error, keyed triangles) for the level-0 meshlets `lets`, or None (no worthwhile level).
    Collapses run with growing tolerance up to max_error (model units; the look floor), stopping early only when a
    --target share is reached (0 = reduce to the floor)."""
    uvb, uvs = part[8:10], part[10:12]
    pos, ids, tris = triangles_of(p, lets, part, mesh)
    if not tris:
        return None
    locked = {ids[x] for x in ids if x in locked_pos}
    s = mesh_lod.Simplifier(pos, tris, locked)
    goal = a.target * len(tris)
    eps, error, cur = min(a.start_error, max_error), 0.0, tris
    while True:
        s.run_to(eps)
        cur, error = s.triangles(), s.error
        if len(cur) <= goal or eps >= max_error:
            break
        eps = min(max_error, eps * 1.25)
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


def external_level(res, lets, part, mesh, p, a):
    """A far level from an external reducer's triangles (model units, float UV, colour): positions go back to the mesh
    grid, UVs to the part's 16-bit UV. -> as far_level(), or None."""
    if not res or not res.get('tris'):
        return None
    step, origin = mesh[11:14], mesh[8:11]
    uvb, uvs = part[8:10], part[10:12]
    n0 = sum(len(s) - 2 for li in lets for s in let_corners(p, p['lets'][li])[1])
    keyed = []
    for t in res['tris']:
        k3 = []
        for x, y, z, u, v, colour in t:
            g = tuple(min(65535, max(0, round((c - origin[k]) / step[k]))) for k, c in enumerate((x, y, z)))
            k3.append((*g, min(65535, max(0, round((u - uvb[0]) / uvs[0]))),
                       min(65535, max(0, round((v - uvb[1]) / uvs[1]))), int(colour)))
        if len({c[:3] for c in k3}) == 3:
            keyed.append(tuple(k3))
    if not keyed or len(keyed) > (1.0 - a.min_saving) * n0:
        return None
    return len(keyed), n0, float(res.get('error', 0.0)), keyed


def read_sidecar(path, npart):
    """-> (part passes, placements [(mesh, 3x4 affine rows)])."""
    side = open(path, 'rb').read()
    hp = struct.unpack_from('<4s7I', side, 0)
    assert hp[0] == b'R4PW' and hp[3] == npart, ('R4PW sidecar does not match', hp[:4], npart)
    passes = [side[32 + 16 * i + 12] for i in range(npart)]
    base = 32 + 16 * npart
    pls = []
    for i in range(hp[2]):
        r = struct.unpack_from('<HH12f', side, base + 52 * i)
        pls.append((r[0], [r[2:6], r[6:10], r[10:14]]))
    return passes, pls


def world_box(mesh, aff, lo, hi):
    """World AABB of a grid box under a placement (8 corners)."""
    step, origin = mesh[11:14], mesh[8:11]
    wl, wh = [1e30] * 3, [-1e30] * 3
    for cx in (lo[0], hi[0]):
        for cy in (lo[1], hi[1]):
            for cz in (lo[2], hi[2]):
                m = (origin[0] + step[0] * cx, origin[1] + step[1] * cy, origin[2] + step[2] * cz)
                for r in range(3):
                    w = aff[r][0] * m[0] + aff[r][1] * m[1] + aff[r][2] * m[2] + aff[r][3]
                    wl[r] = min(wl[r], w)
                    wh[r] = max(wh[r], w)
    return wl, wh


class WalkGrid:
    """Walkable sample points bucketed on a CELL mm X/Z grid: nearest distance from a world box."""
    CELL = 4000.0

    def __init__(self, points):
        self.cells = {}
        for p in points:
            self.cells.setdefault((int(p[0] // self.CELL), int(p[2] // self.CELL)), []).append(p)

    def nearest(self, wl, wh, limit):
        """Distance from the box to the nearest point, or limit when none is closer than limit."""
        best = limit
        x0, x1 = int((wl[0] - limit) // self.CELL), int((wh[0] + limit) // self.CELL)
        z0, z1 = int((wl[2] - limit) // self.CELL), int((wh[2] + limit) // self.CELL)
        for gx in range(x0, x1 + 1):
            for gz in range(z0, z1 + 1):
                for p in self.cells.get((gx, gz), ()):
                    d2 = 0.0
                    for r in range(3):
                        e = wl[r] - p[r] if p[r] < wl[r] else (p[r] - wh[r] if p[r] > wh[r] else 0.0)
                        d2 += e * e
                    if d2 < best * best:
                        best = math.sqrt(d2)
        return best


def placement_scale(aff):
    return max(math.sqrt(aff[0][k] ** 2 + aff[1][k] ** 2 + aff[2][k] ** 2) for k in range(3))


def level_triangles(p, lv):
    out = []
    for li in range(lv[0], lv[0] + lv[1]):
        corners, strips = let_corners(p, p['lets'][li])
        for s in strips:
            out.append(tuple(tuple(p['verts'][corners[k]]) for k in s))
    return out


def verify(src_path, out_path, report_path=None):
    """What a build without WORLD_LOD draws from OUT is what it drew from IN, except the clusters the report lists as
    replaced (far-only: level 0 is the reduced mesh in every build; checked for their triangle count).
    Unsplit clusters: every source level draws the same strips (vertex records in order). Clusters split by --split-mm
    (level-0-only clusters of non-translucent parts): their meshlets, as strips of vertex records, are the same multiset
    in each part. Far levels are last in their cluster with the marker error. Strip-grouped outputs compare like for like
    (ps2_strip_groups.py works per meshlet)."""
    a, b = read(open(src_path, 'rb').read()), read(open(out_path, 'rb').read())
    rep = {}
    if report_path:
        rep = {r['cluster']: r for r in json.load(open(report_path))['clusters']}
    assert [m[:6] + m[8:] for m in a['meshes']] == [m[:6] + m[8:] for m in b['meshes']]
    assert [x[:6] + x[8:] for x in a['parts']] == [x[:6] + x[8:] for x in b['parts']]
    assert a['pal'] == b['pal']
    same = far = split_parts = replaced = 0
    tri_count = lambda p, lv: sum(len(s) - 2 for s in level_triangles(p, lv))
    for pi in range(len(a['parts'])):
        fa, ca = a['plods'][pi]
        fb, cb = b['plods'][pi]
        if ca == cb:   # unsplit: cluster by cluster
            for k in range(ca):
                x, y = a['clusters'][fa + k], b['clusters'][fb + k]
                assert x[:6] == y[:6] and y[7] in (x[7], x[7] + 1)
                r = rep.get(fb + k, {})
                for j in range(x[7]):
                    la, lb = a['levels'][x[6] + j], b['levels'][y[6] + j]
                    if j == 0 and r.get('decision') == 'replace':
                        assert tri_count(b, lb) <= r['far'] and la[2] == lb[2], ('replaced level', pi, k)
                        replaced += 1
                        continue
                    assert la[1:] == lb[1:] and level_triangles(a, la) == level_triangles(b, lb), ('level differs', pi, k, j)
                    same += 1
                if y[7] == x[7] + 1:
                    assert b['levels'][y[6] + x[7]][2] >= 1e29
                    far += 1
            continue
        split_parts += 1
        src, dst = [], []
        skip = {li for k in range(cb) for li in rep.get(fb + k, {}).get('src_lets', ())
                if rep.get(fb + k, {}).get('decision') == 'replace'}
        for k in range(ca):
            x = a['clusters'][fa + k]
            for j in range(x[7]):
                lv = a['levels'][x[6] + j]
                src.append((j, lv[2], sorted(level_triangles(a, [li, 1, 0]) for li in range(lv[0], lv[0] + lv[1])
                                             if not (j == 0 and li in skip))))
        for k in range(cb):
            y = b['clusters'][fb + k]
            r = rep.get(fb + k, {})
            for j in range(y[7]):
                lv = b['levels'][y[6] + j]
                if lv[2] >= 1e29:
                    assert j == y[7] - 1
                    far += 1
                    continue
                if j == 0 and r.get('decision') == 'replace':
                    replaced += 1
                    continue
                dst.append((j, lv[2], sorted(level_triangles(b, [li, 1, 0]) for li in range(lv[0], lv[0] + lv[1]))))
        flat = lambda rows: sorted(m for j, e, ms in rows for m in ms)
        assert flat(src) == flat(dst), ('split part meshlets differ', pi)
        same += len(src)
    print('VERIFY OK clusters %d -> %d, source levels identical %d (split parts %d), far levels %d, replaced %d' % (
        len(a['clusters']), len(b['clusters']), same, split_parts, far, replaced))


_CHUNKS = {}
FAR_LET_VERTICES = 64   # --far-let-verts: the source meshlets' size, so culling stays as fine


def emit(src, plan, part_mesh, far, decision):
    """Write the output package dict. decision[(pi, n)] in {'replace', 'add', None}; far[(pi, n)] = far_level() result.
    Each part keeps the source meshlets some kept level names (source order), then its far meshlets; its vertex pool
    keeps the records those source meshlets read (source order, so non-indexed runs stay contiguous), then far corners
    not already present. Returns (out, per-cluster rows)."""
    out = dict(meshes=[list(m) for m in src['meshes']], parts=[], lets=[], verts=[], strip=bytearray(),
               pal=list(src['pal']), plods=[], clusters=[], levels=[])
    rows_out = []
    for pi, part in enumerate(src['parts']):
        new_lo = len(out['verts'])
        first_let = len(out['lets'])
        # levels per cluster: [(error, ('src', [lets]) | ('far', n))]
        levels = []
        for n, row in enumerate(plan[pi]):
            d = decision.get((pi, n))
            if row[0] == 'keep':
                c = src['clusters'][row[1]]
                lv = [(src['levels'][k][2], ('src', list(range(src['levels'][k][0], src['levels'][k][0] + src['levels'][k][1]))))
                      for k in range(c[6], c[6] + c[7])]
            else:
                lv = [(0.0, ('src', list(row[1])))]
            if d == 'replace':
                lv[0] = (lv[0][0], ('far', n))
            elif d == 'add':
                lv.append((FAR_ERROR, ('far', n)))
            levels.append(lv)
        # source meshlets in source order of first use
        let_map, src_lets = {}, []
        for lv in levels:
            for e, (kind, x) in lv:
                if kind == 'src':
                    for li in x:
                        if li not in let_map:
                            let_map[li] = len(src_lets)
                            src_lets.append(li)
        named_by_source = set()
        for row in plan[pi]:
            if row[0] == 'keep':
                c = src['clusters'][row[1]]
                for k in range(c[6], c[6] + c[7]):
                    named_by_source.update(range(src['levels'][k][0], src['levels'][k][0] + src['levels'][k][1]))
            else:
                named_by_source.update(row[1])
        for li in range(part[6], part[6] + part[7]):   # meshlets no source level names (none expected): kept
            if li not in named_by_source and li not in let_map:
                let_map[li] = len(src_lets)
                src_lets.append(li)
        # vertex pool: source records the kept meshlets read, in source order
        used = set()
        for li in src_lets:
            used.update(let_corners(src, src['lets'][li])[0])
        used = sorted(used)
        newidx = {v: new_lo + k for k, v in enumerate(used)}
        out['verts'].extend(src['verts'][v] for v in used)
        pool = {}
        for v in used:
            pool.setdefault(tuple(src['verts'][v]), newidx[v])
        for li in src_lets:
            m = src['lets'][li]
            corners, strips = let_corners(src, m)
            if len(out['strip']) & 1:
                out['strip'].append(0)
            start = len(out['strip'])
            if m[4] & INDEXED:
                out['strip'].extend(struct.pack('<%dH' % m[3], *[newidx[c] - new_lo for c in corners]))
                out['strip'].extend(src['strip'][m[1] + 2 * m[3]:m[1] + 2 * m[3] + m[2]])
                fv = new_lo
            else:
                fv = newidx[corners[0]]
                assert newidx[corners[-1]] - fv == len(corners) - 1
                out['strip'].extend(src['strip'][m[1]:m[1] + m[2]])
            out['lets'].append([fv, start] + list(m[2:]))
        # far meshlets
        far_first = {}
        fresh = 0
        for n in range(len(plan[pi])):
            if decision.get((pi, n)) not in ('replace', 'add'):
                continue
            if (pi, n) not in _CHUNKS:
                keyed = far[(pi, n)][3]
                strips = [c for s in mesh_lod.stripify(keyed) for c in crb.split_strip(s) if len(c) >= 3]
                _CHUNKS[(pi, n)] = list(mesh_lod.pack_meshlets(strips, FAR_LET_VERTICES, lambda k: k[:3]))
            far_first[n] = (len(out['lets']), 0)
            count = 0
            for chunk in _CHUNKS[(pi, n)]:
                keys = list(dict.fromkeys(c for s in chunk for c in s))
                local = {c: i for i, c in enumerate(keys)}
                offs = []
                for c in keys:
                    if c not in pool:
                        pool[c] = len(out['verts'])
                        out['verts'].append(c)
                        fresh += 1
                    offs.append(pool[c] - new_lo)
                if len(out['strip']) & 1:
                    out['strip'].append(0)
                first_index = len(out['strip'])
                out['strip'].extend(struct.pack('<%dH' % len(keys), *offs))
                strip_start = len(out['strip'])
                for s in chunk:
                    out['strip'].append(len(s))
                    out['strip'].extend(local[c] for c in s)
                g = [c[:3] for c in keys]
                out['lets'].append([new_lo, first_index, len(out['strip']) - strip_start, len(keys), len(chunk) | INDEXED,
                                    *[min(q[x] for q in g) for x in range(3)], *[max(q[x] for q in g) for x in range(3)]])
                count += 1
            far_first[n] = (far_first[n][0], count)
        assert len(out['verts']) - new_lo <= 65536, 'part pool over 65536 vertices'
        out['parts'].append([part[0], part[1], part[2], part[3], part[4], part[5], first_let,
                             len(out['lets']) - first_let] + list(part[8:12]))
        out['plods'].append([len(out['clusters']), len(plan[pi])])
        for n, row in enumerate(plan[pi]):
            first_level = len(out['levels'])
            for e, (kind, x) in levels[n]:
                if kind == 'src':
                    nl = [first_let + let_map[li] for li in x]
                    assert nl == list(range(nl[0], nl[0] + len(nl))) if nl else True, ('level not contiguous', pi, n)
                    out['levels'].append([nl[0] if nl else first_let, len(nl), e])
                else:
                    out['levels'].append([far_first[x][0], far_first[x][1], f32(e)])
            if row[0] == 'keep':
                box = list(src['clusters'][row[1]][:6])
            else:
                box = [min(src['lets'][li][5 + k] for li in row[1]) for k in range(3)] + \
                      [max(src['lets'][li][8 + k] for li in row[1]) for k in range(3)]
            out['clusters'].append(box + [first_level, len(out['levels']) - first_level])
            rows_out.append(dict(part=pi, cluster=len(out['clusters']) - 1, kind=row[0],
                                 src_cluster=row[1] if row[0] == 'keep' else row[2],
                                 decision=decision.get((pi, n))))
            if row[0] == 'split' and decision.get((pi, n)) == 'replace':
                rows_out[-1]['src_lets'] = list(row[1])
    return out, rows_out


def load_table(path, room):
    t = json.load(open(path))
    r = t['rooms'].get(room)
    assert r is not None, ('room not in the table', room)
    area = t['areas'][r['area']]
    return t, r, area


def main():
    if len(sys.argv) in (4, 5) and sys.argv[1] == '--verify':
        verify(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) == 5 else None)
        return
    ap = argparse.ArgumentParser()
    ap.add_argument('mesh'); ap.add_argument('out')
    ap.add_argument('--table', help='per-room table (tools/d367/worldlod/worldlod-rooms.json): floor, targets, '
                    'untouched rooms, per-area protected meshes')
    ap.add_argument('--room', help='room id in the table (r119)')
    ap.add_argument('--max-error-px', dest='max_error_px', type=float,
                    help='look floor: pixels at 640x480 at the switch distance minus hysteresis (default: the table)')
    ap.add_argument('--switch-mm', type=float, default=12000.0)
    ap.add_argument('--hyst-mm', type=float, default=500.0)
    ap.add_argument('--focal-px', type=float, default=514.7, help='240 / tan(fovy / 2), fovy 50 (roomproj.py)')
    ap.add_argument('--max-error-mm', dest='max_error', type=float,
                    help='geometric ceiling in world mm instead of --max-error-px (tests)')
    ap.add_argument('--target', type=float, default=0.0,
                    help='stop a cluster early at this share of its triangles (0 = reduce to the floor)')
    ap.add_argument('--start-error-mm', dest='start_error', type=float, default=2.0)
    ap.add_argument('--min-saving', type=float, default=0.1)
    ap.add_argument('--uv-guard', type=float, default=0.02)
    ap.add_argument('--colour-guard', type=int, default=2, help='5-bit steps a corner colour may change (-1 = off)')
    ap.add_argument('--split-mm', type=float, default=0.0,
                    help='split level-0-only clusters of opaque / punch-through parts wider than this (model units) '
                         'into sub-clusters first, so the 12 m switch acts per region (0 = off)')
    ap.add_argument('--sidecar', required=True, help='the package\'s R4PW (placements; part passes)')
    ap.add_argument('--walk', help='walkable points JSON (walk.py): enables far-only replacement')
    ap.add_argument('--far-only-mm', type=float, default=15000.0,
                    help='a cluster this far from every walkable point is far-only (switch 12 m + camera offset)')
    ap.add_argument('--max-growth', type=int, default=0, help='bytes the package may grow (additive far levels)')
    ap.add_argument('--no-add', action='store_true', help='replacement only (no additive far levels)')
    ap.add_argument('--far-let-verts', type=int, default=64,
                    help='vertex limit of a far meshlet (the PS2 source meshlets hold ~64: as fine a cull)')
    ap.add_argument('--protect-bins', default='', help='comma list of mesh bins with no far level (adds to the table)')
    ap.add_argument('--report')
    ap.add_argument('--export-clusters', help='write the far-level candidates\' level-0 triangles (model-unit positions, '
                    'UV, colour, locked vertices, triangle target) as JSON for an external reducer (tools/d367/worldlod/'
                    'blender_decimate.py) and stop; --targets-from REPORT takes each cluster\'s target from a report '
                    'of this tool (the same far triangle count)')
    ap.add_argument('--targets-from')
    ap.add_argument('--external', help='far levels from an external reducer\'s JSON ({cluster: {"tris": [[x, y, z, u, v, '
                    'colour] x3, ...]}}) instead of the built-in simplifier')
    a = ap.parse_args()
    room_row, area, protect = None, None, set()
    floor_px = a.max_error_px
    if a.table:
        assert a.room, '--table needs --room'
        table, room_row, area = load_table(a.table, a.room)
        if floor_px is None:
            floor_px = table['floor_px']
        if room_row.get('plan') == 'untouched':
            print('ROOM %s UNTOUCHED (%s): ship the source package' % (a.room, room_row.get('why', '')))
            return
        protect |= set(area.get('protect', {}).get(a.room, []))
    protect |= {int(x, 0) for x in a.protect_bins.split(',') if x}
    if a.max_error is None:
        assert floor_px is not None, 'give --max-error-px, --max-error-mm or --table'
        a.max_error = floor_px * (a.switch_mm - a.hyst_mm) / a.focal_px
    global FAR_LET_VERTICES
    FAR_LET_VERTICES = a.far_let_verts
    mesh_lod.UV_GUARD = a.uv_guard if a.uv_guard > 0 else None
    mesh_lod.COLOUR_GUARD = a.colour_guard if a.colour_guard >= 0 else None
    export = {} if a.export_clusters else None
    targets = None
    if a.targets_from:
        targets = {r['cluster']: r['far'] for r in json.load(open(a.targets_from))['clusters'] if r.get('far')}
    external = json.load(open(a.external))['clusters'] if a.external else None
    src = read(open(a.mesh, 'rb').read())
    passes, placements = read_sidecar(a.sidecar, len(src['parts']))
    part_mesh = {}
    for mi, m in enumerate(src['meshes']):
        for pi in range(m[6], m[6] + m[7]):
            part_mesh[pi] = mi
    mesh_pls = {}
    for mi, aff in placements:
        mesh_pls.setdefault(mi, []).append(aff)
    # per mesh: the geometric ceiling in model units (the largest placement scale magnifies the error)
    mesh_err = {mi: a.max_error / max([placement_scale(x) for x in mesh_pls.get(mi, [])] + [1e-9])
                if mesh_pls.get(mi) else a.max_error for mi in range(len(src['meshes']))}
    # plan: per part, ('keep', ci) keeps a source cluster (all levels); ('split', [meshlets], ci) is a level-0-only
    # sub-cluster of a split source cluster
    plan = []
    nsplit = 0
    for pi, part in enumerate(src['parts']):
        mesh = src['meshes'][part_mesh[pi]]
        fc, cc = src['plods'][pi]
        rows = []
        for ci in range(fc, fc + cc):
            c = src['clusters'][ci]
            lv0 = src['levels'][c[6]]
            if a.split_mm > 0 and c[7] == 1 and passes[pi] != 2 and lv0[1] > 1:
                ext = max((c[3 + x] - c[x]) * abs(mesh[11 + x]) for x in range(3))
                if ext > a.split_mm:
                    gs = split_groups(src, range(lv0[0], lv0[0] + lv0[1]), mesh[11:14], a.split_mm)
                    if len(gs) > 1:
                        nsplit += 1
                        rows += [('split', g, ci) for g in gs]
                        continue
            rows.append(('keep', ci))
        plan.append(rows)

    def l0_lets(row):
        if row[0] == 'split':
            return list(row[1])
        lv0 = src['levels'][src['clusters'][row[1]][6]]
        return list(range(lv0[0], lv0[0] + lv0[1]))
    owners = {}
    for pi, rows in enumerate(plan):
        mi = part_mesh[pi]
        for n, row in enumerate(rows):
            for li in l0_lets(row):
                for c in let_corners(src, src['lets'][li])[0]:
                    owners.setdefault((mi, src['verts'][c][:3]), set()).add((pi, n))
    locked_by_mesh = {}
    for (mi, g), cs in owners.items():
        if len(cs) > 1:
            locked_by_mesh.setdefault(mi, set()).add(g)
    walk = None
    if a.walk:
        walk = WalkGrid(json.load(open(a.walk))['points'])
    # phase A: far meshes and the far-only test
    far, info = {}, {}
    cid = 0
    for pi, part in enumerate(src['parts']):
        mi = part_mesh[pi]
        mesh = src['meshes'][mi]
        for n, row in enumerate(plan[pi]):
            lets0 = l0_lets(row)
            l0_tris = sum(len(s) - 2 for li in lets0 for s in let_corners(src, src['lets'][li])[1])
            if row[0] == 'keep':
                lo, hi = src['clusters'][row[1]][0:3], src['clusters'][row[1]][3:6]
            else:
                lo = [min(src['lets'][li][5 + k] for li in lets0) for k in range(3)]
                hi = [max(src['lets'][li][8 + k] for li in lets0) for k in range(3)]
            near = None
            if walk is not None and mesh_pls.get(mi):
                near = min(walk.nearest(*world_box(mesh, aff, lo, hi), a.far_only_mm) for aff in mesh_pls[mi])
            info[(pi, n)] = dict(cid=cid, l0=l0_tris, near_mm=None if near is None else round(near),
                                 protected=mesh[0] in protect, mesh_bin=mesh[0])
            cid += 1
            if mesh[0] in protect or not l0_tris:
                continue
            if export is not None:
                pos, ids, tris = triangles_of(src, lets0, part, mesh)
                lk = sorted(i for x, i in ids.items() if x in locked_by_mesh.get(mi, set()))
                want = targets.get(info[(pi, n)]['cid']) if targets is not None else None
                if tris and (targets is None or want):
                    export[str(info[(pi, n)]['cid'])] = dict(
                        part=pi, pos=[pos[i] for i in range(len(pos))], locked=lk,
                        tris=[[list(t[0]), [[c[0][0], c[0][1], c[2]] for c in t[1]]] for t in tris],
                        target=want or max(1, int(0.5 * len(tris))))
                continue
            if external is not None:
                r = external_level(external.get(str(info[(pi, n)]['cid'])), lets0, part, mesh, src, a)
            else:
                r = far_level(src, lets0, part, mesh, locked_by_mesh.get(mi, set()), a, mesh_err[mi])
            if r is not None:
                far[(pi, n)] = r
    if export is not None:
        json.dump(dict(source=a.mesh, split_mm=a.split_mm, clusters=export), open(a.export_clusters, 'w'))
        print('exported %d clusters to %s' % (len(export), a.export_clusters))
        return
    # phase B: decisions. Far-only clusters replace their level 0; the others are additive candidates, best saving per
    # byte first, while the package stays within --max-growth of its input
    in_bytes = len(open(a.mesh, 'rb').read())
    decision = {}
    cands = []
    for key, r in far.items():
        nm = info[key]['near_mm']
        if nm is not None and nm >= a.far_only_mm:
            decision[key] = 'replace'
        elif not a.no_add:
            kept, n0, err, keyed = r
            est = 28 * (1 + len(keyed) // 120) + 2 * 3 * len(keyed) // 2 + len(keyed) + 8
            cands.append(((n0 - kept) / est, key))
    cands.sort(reverse=True)
    out, rows = emit(src, plan, part_mesh, far, decision)
    base_bytes = len(write(out))
    budget = in_bytes + a.max_growth - base_bytes
    # add candidates in value order; re-measure exactly, drop from the tail until within budget
    added = []
    lo_k, hi_k = 0, len(cands)
    best = None
    while lo_k <= hi_k:   # binary search on the number of candidates added (exact sizes)
        mid = (lo_k + hi_k) // 2
        dec = dict(decision)
        for _, key in cands[:mid]:
            dec[key] = 'add'
        o, rw = emit(src, plan, part_mesh, far, dec)
        size = len(write(o))
        if size <= in_bytes + a.max_growth:
            best = (mid, dec, o, rw, size)
            lo_k = mid + 1
        else:
            hi_k = mid - 1
    ship_source = False
    if best is None:   # even the replacements (with split cluster records) grow the package: ship the source
        best = (0, decision, out, rows, base_bytes)
        ship_source = True
    nadd, decision, out, rows, size = best
    blob = write(out)
    open(a.out, 'wb').write(blob)
    report = []
    tot = dict(clusters_in=len(src['clusters']), split_clusters=nsplit, clusters=len(out['clusters']), l0_tris=0,
               replaced=0, added=0, candidates=len(far), protected=0, far_only=0, tris_replaced_saved=0,
               tris_added_saved=0)
    for row in rows:
        key = (row['part'], [n for n in range(len(plan[row['part']]))][row['cluster'] - out['plods'][row['part']][0]])
        inf = info[key]
        r = far.get(key)
        tot['l0_tris'] += inf['l0']
        tot['protected'] += inf['protected']
        tot['far_only'] += bool(inf['near_mm'] is not None and inf['near_mm'] >= a.far_only_mm)
        rr = dict(row, l0=inf['l0'], near_mm=inf['near_mm'], mesh_bin=inf['mesh_bin'], protected=inf['protected'])
        if r is not None:
            kept, n0, err, _ = r
            rr.update(far=kept, error_mm=round(err, 2),
                      error_px=round(err * placement_scale_max(mesh_pls, part_mesh[row['part']]) * a.focal_px /
                                     (a.switch_mm - a.hyst_mm), 3))
            if row['decision'] == 'replace':
                tot['replaced'] += 1
                tot['tris_replaced_saved'] += n0 - kept
            elif row['decision'] == 'add':
                tot['added'] += 1
                tot['tris_added_saved'] += n0 - kept
        report.append(rr)
    summary = dict(input=a.mesh, output=a.out, room=a.room, bytes_in=in_bytes, bytes_out=len(blob),
                   growth=len(blob) - in_bytes, floor_px=floor_px, max_error_mm=round(a.max_error, 2),
                   switch_mm=a.switch_mm, hyst_mm=a.hyst_mm, focal_px=a.focal_px, target=a.target,
                   uv_guard=a.uv_guard, colour_guard=a.colour_guard, min_saving=a.min_saving, split_mm=a.split_mm,
                   far_only_mm=a.far_only_mm if walk else None, max_growth=a.max_growth, far_let_verts=a.far_let_verts,
                   protect_bins=sorted(protect), external=bool(external), ship_source=ship_source, **tot)
    print(json.dumps(summary, indent=1))
    if ship_source:
        print('NOTHING FITS within --max-growth %d: ship the source package unchanged' % a.max_growth)
    if a.report:
        json.dump(dict(summary=summary, clusters=report), open(a.report, 'w'), indent=1)


def placement_scale_max(mesh_pls, mi):
    return max([placement_scale(x) for x in mesh_pls.get(mi, [])] + [1.0]) if mesh_pls.get(mi) else 1.0


if __name__ == '__main__':
    main()
