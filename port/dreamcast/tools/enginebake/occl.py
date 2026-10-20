"""occl.py (lane engine19, offline): the room data file's OCCL section, large opaque occluders of the PS2 world for
the runtime wall check (platform/room_vis.c, ENEMY_VIS_CULL option C).

An occluder is a SLAB: a rectangle (u, v extents) on a reference plane (n, d0), with half thickness T, such that the
room's drawn opaque surface inside the slab |n.x - d0| <= T is a sheet whose projection onto the plane covers the
whole rectangle. A segment that enters the slab through its front face and leaves it through its back face, both
inside the rectangle, therefore crosses that sheet. The runtime culls a box only when it lies in the shadow of BOTH the
front and the back rectangle from the real eye (every eye -> box segment crosses both faces inside the rectangle).
Real walls are rarely flat (stone, timber), so the slab absorbs their relief.
  - pass 0 (opaque) parts only, so no alpha, punch-through, fences or foliage (those are passes 1-2);
  - every placement except those whose scroll object id is unique in the package (the game may hide or move them:
    doors, breakables; PS2_WORLD_DYNAMIC). The runtime also refuses any frame where the world is not as compiled;
  - covered at EVERY LOD level 0..2 (the coverage grids are ANDed);
  - one-sided parts count only for the side they are drawn from, so an occluder carries the side the eye must be on.
    The drawn face's winding is found from the room's own floors (most one-sided horizontal area faces up).
Coverage is sampled on a SPACING lattice in the plane. A lattice cell counts when its 4 corners lie inside the
union of the projected slab triangles. The greedy largest all-covered rectangles are kept (>= MIN_AREA, sides >=
MIN_SIDE) and inset by INSET on every side.
Per 4 m camera cell, the candidate list holds up to CAP occluders whose front can hold an eye of that cell and that
lie within range, best first by area / distance^2. Identical lists are stored once.

OCCL v1 (little-endian):
  header 32 B: u16 vw, vh, div, nocc, nlist, range_cm; u32 R4PW sidecar crc; u16 cap, spacing_mm, inset_mm; 10 B zero
  occluders[nocc] 56 B: f32 corner[4][3] on the reference plane (in order around the rectangle), f32 half thickness,
                 s8 side (+1 / -1: the eye must be in front of the slab along (c1-c0) x (c3-c0) / its opposite), 3 B 0
  cells[vw*vh] 4 B: u16 first (into lists), u8 count, u8 0
  lists u16[nlist] (padded to 4 B)
"""
import math
import struct

SPACING = 150.0     # coverage lattice (mm)
MIN_AREA = 2.0e6    # mm^2
MIN_SIDE = 800.0
INSET = 100.0
MAX_RECTS = 64      # per slab and side
CAP = int(__import__("os").environ.get("RC_OCCL_CAP", 32))
HALF = 250.0        # slab half thickness (mm)
N_BIN = 6.0         # normal bins (about 10 degrees)
N_COS = math.cos(math.radians(35.0))   # a slab triangle's normal within 35 degrees of the reference
STRIDE = 56
EYE_UP = 2000.0       # ranking eye height over a camera cell's lowest floor
SEED_TRI = 0.25e6     # mm^2: a triangle this large proposes a plane
N_SEED = 32.0         # proposed normals quantised to about 2 degrees
SEED_AREA = 1.0e6     # mm^2 of proposing triangles for a plane to be tried
WINDING = {1: -1, 2: 1}   # drawn face along +-(b-a) x (c-a) for R4PW cull 1 (CCW) / 2 (CW); see winding_sign


def _sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def _dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def _cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    l = math.sqrt(_dot(a, a))
    return (a[0] / l, a[1] / l, a[2] / l) if l > 0 else None


def _canon(n):
    for c in n:
        if abs(c) > 1e-6:
            return (n, 1) if c > 0 else ((-n[0], -n[1], -n[2]), -1)
    return n, 1


def winding_sign(tris):
    """per cull mode (1 CCW, 2 CW): +1 when the drawn face is along (b-a) x (c-a), -1 when opposite, None when not
    known for sure (confidence < 0.8, or both modes agree); from the ground of each column."""
    # Only the LOWEST horizontal surface of each 4 m column counts (the ground, seen from above); ceilings, roof
    # undersides and upper floors are left out.
    # The cull modes mean the same in every room (one renderer, one projection): WINDING, calibrated on the r101
    # ground (mode 2: +1 at 0.90 evidence; r103 +1 at 0.72; mode 1 has no ground). A room whose own ground
    # contradicts it with evidence >= 0.5 gets no one-sided occluders.
    res = {}
    out = {}
    for mode in (1, 2):
        res[mode] = _winding(tris, mode)
        w, c = res[mode]
        out[mode] = None if (c >= 0.5 and w != WINDING[mode]) else WINDING[mode]
    return out, res


def _winding(tris, mode):
    col = {}
    for t in tris:
        if t[9] != mode:
            continue
        a, b, c = t[0:3], t[3:6], t[6:9]
        n = _cross(_sub(b, a), _sub(c, a))
        ar = math.sqrt(_dot(n, n))
        if ar <= 0 or abs(n[1]) < 0.9 * ar:
            continue
        cy = (a[1] + b[1] + c[1]) / 3.0
        key = (int((a[0] + b[0] + c[0]) // 12000), int((a[2] + b[2] + c[2]) // 12000))
        col.setdefault(key, []).append((cy, n[1], ar))
    up = tot = 0.0
    for lst in col.values():
        y0 = min(e[0] for e in lst)
        for cy, ny, ar in lst:
            if cy <= y0 + 200.0:
                up += ny
                tot += ar
    return (1 if up > 0 else -1), (abs(up) / tot if tot else 0.0)


def _slabs(tris):
    """reference planes [(n, d0, seed area)]: every triangle of >= SEED_TRI area proposes its own plane, quantised
    (normal to 1/N_SEED, d to HALF/2); planes proposed by >= SEED_AREA of triangles are kept. Slabs overlap, so a wall
    whose relief fits one slab is wholly inside at least one of them."""
    seeds = {}
    for t in tris:
        a, b, c = t[0:3], t[3:6], t[6:9]
        cr = _cross(_sub(b, a), _sub(c, a))
        ar = 0.5 * math.sqrt(_dot(cr, cr))
        if ar < SEED_TRI:
            continue
        cn, _ = _canon(_norm(cr))
        q = _norm((round(cn[0] * N_SEED) / N_SEED, round(cn[1] * N_SEED) / N_SEED, round(cn[2] * N_SEED) / N_SEED))
        if q is None:
            continue
        d = sum(_dot(q, p) for p in (a, b, c)) / 3.0
        key = (q, round(d / (HALF / 2)))
        seeds[key] = seeds.get(key, 0.0) + ar
    return [(q, k * (HALF / 2), ar) for (q, k), ar in seeds.items() if ar >= SEED_AREA]


def _basis(n):
    ref = (0.0, 1.0, 0.0) if abs(n[1]) < 0.9 else (1.0, 0.0, 0.0)
    u = _norm(_cross(ref, n))
    v = _cross(n, u)
    return u, v


def _cover(tris2, x0, y0, nx, ny, side):
    """lattice point coverage (nx+1 x ny+1) by the projected triangles drawn toward `side` (or two-sided)."""
    pts = [bytearray(nx + 1) for _ in range(ny + 1)]
    for (a, b, c, f, _fld) in tris2:
        if f != 0 and f != side:
            continue
        lo_x = max(0, int(math.ceil((min(a[0], b[0], c[0]) - x0) / SPACING - 1e-6)))
        hi_x = min(nx, int(math.floor((max(a[0], b[0], c[0]) - x0) / SPACING + 1e-6)))
        lo_y = max(0, int(math.ceil((min(a[1], b[1], c[1]) - y0) / SPACING - 1e-6)))
        hi_y = min(ny, int(math.floor((max(a[1], b[1], c[1]) - y0) / SPACING + 1e-6)))
        if lo_x > hi_x or lo_y > hi_y:
            continue
        det = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(det) < 1e-3:
            continue
        eps = 1e-4 * abs(det)
        for j in range(lo_y, hi_y + 1):
            py = y0 + j * SPACING
            row = pts[j]
            for i in range(lo_x, hi_x + 1):
                px = x0 + i * SPACING
                w0 = (b[0] - px) * (c[1] - py) - (b[1] - py) * (c[0] - px)
                w1 = (c[0] - px) * (a[1] - py) - (c[1] - py) * (a[0] - px)
                w2 = (a[0] - px) * (b[1] - py) - (a[1] - py) * (b[0] - px)
                if det > 0:
                    if w0 >= -eps and w1 >= -eps and w2 >= -eps:
                        row[i] = 1
                elif w0 <= eps and w1 <= eps and w2 <= eps:
                    row[i] = 1
    return pts


def _cells(pts, nx, ny):
    return [bytearray(1 if (pts[j][i] and pts[j][i + 1] and pts[j + 1][i] and pts[j + 1][i + 1]) else 0
                      for i in range(nx)) for j in range(ny)]


def _largest(cells, nx, ny):
    best = (0, 0, 0, 0, 0)
    h = [0] * nx
    for j in range(ny):
        row = cells[j]
        for i in range(nx):
            h[i] = h[i] + 1 if row[i] else 0
        st = []
        for i in range(nx + 1):
            cur = h[i] if i < nx else 0
            start = i
            while st and st[-1][1] >= cur:
                s, hh = st.pop()
                ar = hh * (i - s)
                if ar > best[0]:
                    best = (ar, s, j - hh + 1, i - s, hh)
                start = s
            st.append((start, cur))
    return best


def extract(levels, ws):
    """levels: [tris of LOD 0, 1, 2] -> (list of (corners[4], half, side), slab count)."""
    slabs = _slabs(levels[0])
    # triangle precompute per level: (verts, unit normal, facing-capable flag)
    pre = []   # per level: {canonical normal bin: [(a, b, c, unit normal, cull, d of the centroid along canon)]}
    for lt in levels:
        pl = {}
        for t in lt:
            a, b, c = t[0:3], t[3:6], t[6:9]
            nn = _norm(_cross(_sub(b, a), _sub(c, a)))
            if nn is None:
                continue
            cn, _ = _canon(nn)
            key = (round(cn[0] * N_BIN), round(cn[1] * N_BIN), round(cn[2] * N_BIN))
            pl.setdefault(key, []).append((a, b, c, nn, t[9], t[10]))
        pre.append(pl)
    span = int(math.ceil(N_BIN * 2 * math.sin(math.acos(N_COS)))) + 1
    out = []
    for n, d0, _ in slabs:
        u, v = _basis(n)
        k0 = (round(n[0] * N_BIN), round(n[1] * N_BIN), round(n[2] * N_BIN))
        keys = set()
        for dx in range(-span, span + 1):
            for dy in range(-span, span + 1):
                for dz in range(-span, span + 1):
                    k = (k0[0] + dx, k0[1] + dy, k0[2] + dz)
                    keys.add(k)
                    keys.add((-k[0], -k[1], -k[2]))
        per_level = []
        for pl in pre:
            sel = []
            for a, b, c, nn, cull, fld in (t for k in keys if k in pl for t in pl[k]):
                dn = _dot(nn, n)
                if abs(dn) < N_COS:
                    continue
                if not all(abs(_dot(n, p) - d0) <= HALF for p in (a, b, c)):
                    continue
                if cull == 0:
                    f = 0
                else:
                    w = ws.get(int(cull))   # None: mirrored placement or the winding of this cull mode unknown
                    if w is None:
                        continue
                    f = (1 if dn > 0 else -1) * w
                sel.append(((_dot(a, u), _dot(a, v)), (_dot(b, u), _dot(b, v)), (_dot(c, u), _dot(c, v)), f, fld))
            per_level.append(sel)
        if not per_level[0]:
            continue
        xs = [p[0] for t in per_level[0] for p in t[:3]]
        ys = [p[1] for t in per_level[0] for p in t[:3]]
        x0, y0 = min(xs), min(ys)
        nx, ny = int((max(xs) - x0) / SPACING) + 1, int((max(ys) - y0) / SPACING) + 1
        if nx * ny > 4_000_000:
            continue
        for side in (1, -1):
            cells = None
            for sel in per_level:
                c = _cells(_cover(sel, x0, y0, nx, ny, side), nx, ny)
                cells = c if cells is None else [bytearray(p & q for p, q in zip(r1, r2)) for r1, r2 in zip(cells, c)]
            for _ in range(MAX_RECTS):
                ar, i, j, w, h = _largest(cells, nx, ny)
                if not ar:
                    break
                wx, hy = w * SPACING - 2 * INSET, h * SPACING - 2 * INSET
                if wx < MIN_SIDE or hy < MIN_SIDE or wx * hy < MIN_AREA:
                    break
                for jj in range(j, j + h):
                    for ii in range(i, i + w):
                        cells[jj][ii] = 0
                ua, ub = x0 + i * SPACING + INSET, x0 + (i + w) * SPACING - INSET
                va, vb = y0 + j * SPACING + INSET, y0 + (j + h) * SPACING - INSET
                corners = [tuple(n[k] * d0 + u[k] * uu + v[k] * vv for k in range(3))
                           for uu, vv in ((ua, va), (ub, va), (ub, vb), (ua, vb))]
                # (c1-c0) x (c3-c0) is along u x v = n
                # the placements whose triangles lie over the rectangle at any level: the runtime draws the
                # occluder only while each of them is drawn at rest
                srcs = set()
                for sl in per_level:
                    for t in sl:
                        if (min(t[0][0], t[1][0], t[2][0]) <= ub and max(t[0][0], t[1][0], t[2][0]) >= ua and
                                min(t[0][1], t[1][1], t[2][1]) <= vb and max(t[0][1], t[1][1], t[2][1]) >= va):
                            srcs.add(t[4])
                out.append((corners, HALF, side, tuple(sorted(srcs))))
    return _dedupe(out), len(slabs)


def _dedupe(occ):
    """overlapping slabs give near copies of one wall: keep the largest of each (same side, normal within 6
    degrees, centres within 1 m along the plane and HALF across it)."""
    info = []
    for c, half, side, _s in occ:
        n = _norm(_cross(_sub(c[1], c[0]), _sub(c[3], c[0])))
        a = _cross(_sub(c[1], c[0]), _sub(c[3], c[0]))
        info.append((n, tuple(sum(p[k] for p in c) / 4 for k in range(3)), math.sqrt(_dot(a, a))))
    order = sorted(range(len(occ)), key=lambda i: -info[i][2])
    grid, keep = {}, []
    for i in order:
        n, q, ar = info[i]
        key = (int(q[0] // 1000), int(q[1] // 1000), int(q[2] // 1000))
        dup = False
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in grid.get((key[0] + dx, key[1] + dy, key[2] + dz), ()):
                        nj, qj, _ = info[j]
                        if occ[j][2] != occ[i][2] or _dot(n, nj) < 0.995:
                            continue
                        dq = _sub(q, qj)
                        across = abs(_dot(dq, nj))
                        if across <= HALF and _dot(dq, dq) - across * across < 1000.0 ** 2:
                            dup = True
                            break
                    if dup:
                        break
                if dup:
                    break
            if dup:
                break
        if not dup:
            grid.setdefault(key, []).append(i)
            keep.append(i)
    return [occ[i] for i in sorted(keep)]


def _box_side_max(n, d, lo, hi, side):
    m = -1e30
    for x in (lo[0], hi[0]):
        for y in (lo[1], hi[1]):
            for z in (lo[2], hi[2]):
                m = max(m, side * (n[0] * x + n[1] * y + n[2] * z - d))
    return m


def _box_dist(lo, hi, p):
    return math.sqrt(sum(max(lo[k] - p[k], 0.0, p[k] - hi[k]) ** 2 for k in range(3)))


def _rank(occ, g, vis_div, cell, rng, cap):
    """per camera cell: up to cap occluder indices, chosen by occl_rank.c (targets shadowed from the cell centre)."""
    import hashlib, os, subprocess, tempfile
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, 'occl_rank.c')
    exe = os.path.join(tempfile.gettempdir(), 'occl_rank-%s' % hashlib.sha256(open(src, 'rb').read()).hexdigest()[:12])
    if not os.path.exists(exe):
        subprocess.check_call(['cc', '-O2', '-pthread', '-o', exe, src, '-lm'])
    W, H = g['W'], g['H']
    vw, vh = (W + vis_div - 1) // vis_div, (H + vis_div - 1) // vis_div
    cs = cell * vis_div
    eyes = []
    for vz in range(vh):
        for vx in range(vw):
            ys = [g['yr'][x + z * W] for z in range(vz * vis_div, min(H, vz * vis_div + vis_div))
                  for x in range(vx * vis_div, min(W, vx * vis_div + vis_div)) if g['yr'][x + z * W]]
            if ys:
                eyes.append((g['x0'] + (vx + 0.5) * cs, min(y[0] for y in ys) + EYE_UP, g['z0'] + (vz + 0.5) * cs, 1))
            else:
                eyes.append((0.0, 0.0, 0.0, 0))
    tg = []
    for z in range(H):
        for x in range(W):
            yr = g['yr'][x + z * W]
            if not yr:
                continue
            cx, cz = g['x0'] + (x + 0.5) * cell, g['z0'] + (z + 0.5) * cell
            for y in sorted({yr[0], yr[1]} if yr[1] - yr[0] > 1000.0 else {yr[0]}):
                tg.append((cx - 450.0, y - 100.0, cz - 450.0, cx + 450.0, y + 1800.0, cz + 450.0))
    with tempfile.TemporaryDirectory() as td:
        fi, fo = os.path.join(td, 'in'), os.path.join(td, 'out')
        with open(fi, 'wb') as f:
            f.write(b'OCRI' + struct.pack('<5If', len(occ), len(eyes), len(tg), cap, os.cpu_count() or 4, rng))
            for c, half, side, _s in occ:
                f.write(struct.pack('<13fi', *[v for p in c for v in p], half, side))
            for e in eyes:
                f.write(struct.pack('<3fI', *e))
            for t in tg:
                f.write(struct.pack('<6f', *t))
        subprocess.check_call([exe, fi, fo])
        raw = open(fo, 'rb').read()
    out = []
    for c in range(len(eyes)):
        v = struct.unpack_from('<%dH' % cap, raw, 2 * cap * c)
        out.append(tuple(i for i in v if i != 0xFFFF))
    return out


def encode(occ, g, vis_div, cell, eye_lo, eye_hi, rng, crc, cap=CAP):
    """occ: [(corners, half, side)]; g: room_compile grid (W, H, x0, z0, yr). -> (section bytes, info)."""
    W, H = g['W'], g['H']
    vw, vh = (W + vis_div - 1) // vis_div, (H + vis_div - 1) // vis_div
    planes = []
    for corners, half, side, _s in occ:
        n = _norm(_cross(_sub(corners[1], corners[0]), _sub(corners[3], corners[0])))
        planes.append((n, _dot(n, corners[0])))
    centres = [tuple(sum(p[k] for p in c) / 4 for k in range(3)) for c, _, _, _ in occ]
    cs = cell * vis_div
    picks = _rank(occ, g, vis_div, cell, rng, cap)
    keep = sorted({i for l in picks for i in l})   # only occluders some list uses are stored
    remap = {o: k for k, o in enumerate(keep)}
    occ = [occ[o] for o in keep]
    picks = [tuple(remap[i] for i in l) for l in picks]
    lists, lidx, cells = [], {}, b''
    used = 0
    for c in range(vw * vh):
        sel = picks[c]
        if not sel:
            cells += struct.pack('<HBB', 0, 0, 0)
            continue
        if sel not in lidx:
            lidx[sel] = sum(len(x) for x in lists)
            lists.append(sel)
        cells += struct.pack('<HBB', lidx[sel], len(sel), 0)
        used += 1
    flat = [i for l in lists for i in l]
    if len(flat) >= 0xFFFF or len(occ) >= 0xFFFF:
        raise SystemExit('OCCL too large')
    data = struct.pack('<6HIHHHH8x', vw, vh, vis_div, len(occ), len(flat), int(rng) // 10, crc, cap, int(SPACING),
                       int(INSET), sum(len(o[3]) for o in occ))
    pool = []
    for corners, half, side, srcs in occ:
        if len(srcs) > 255 or len(pool) + len(srcs) >= 0xFFFF:
            raise SystemExit('OCCL source placements overflow')
        data += struct.pack('<13fbBH', *[c for p in corners for c in p], half, side, len(srcs), len(pool))
        pool += list(srcs)
    data += cells
    lb = struct.pack('<%dH' % len(flat), *flat)
    if len(flat) & 1:
        lb += b'\0\0'
    data += lb
    pb = struct.pack('<%dH' % len(pool), *pool)
    if len(pool) & 1:
        pb += b'\0\0'
    data += pb
    return data, dict(occluders=len(occ), lists=len(lists), list_entries=len(flat), cells_with_list=used,
                      bytes=len(data))
