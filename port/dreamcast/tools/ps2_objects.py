#!/usr/bin/env python3
"""ps2_objects.py: PS2 geometry for the room objects the source model path draws (Phase 2 lane B item B1).

Room-code set pieces (loose room-archive BINs: SetObjSmd / ModInfoMgr / EvtMgr.SetBin) and etc models (ETM BINs) are
GameCube ModelData drawn by the recovered game through the generic model path. This tool keeps that path and every
source identity and only swaps the geometry: it writes a GameCube-format ModelData whose positions, normals, UVs and
GX primitive streams come from the PS2 BIN of the same object, with the GC header, joints, weight palette layout,
part (material) headers, colour table, nTex and the blend / flip joint tables unchanged. The GC TPL stays the texture
(the PS2 UVs index the same texture space; the PS2 TPL images are reduced copies), so dc/tex.pak keys do not change.
The result is disc data only: the executable is byte-identical; the knob is the staging (PS2_OBJECTS=1 fixtures).

What the game can observe besides drawing: part count and order (kept: a part with no PS2 triangle keeps its header
and gets an empty 32-byte stream), joint table (kept), material headers (kept), nVtx / nNrm and array sizes (smaller:
less memory, the purpose). Collision never comes from ModelData (SAT/EAT/ETS stay GC).

PS2 triangle -> GC part: among the GC parts that sample the same TPL image as the PS2 material, the part of the
nearest GC triangle (centroid distance). Corner colour index: the nearest GC draw vertex of that part. Weights:
the PS2 corner's bone weights as a GC palette entry (reused when equal, appended otherwise). Winding: each PS2
triangle is oriented so its face normal agrees with its corner normals in the same sense as the GC source's.

  ps2_objects.py bin <gc.bin> <ps2.bin> <out.bin> [--json out.json]        (big-endian GC BIN -> big-endian GC BIN)
  ps2_objects.py room --dar <native .dar> --room rNNN --pairs 1d:1b,1f:1d [--etm all|name,...] --out <new .dar>
                 [--json report.json] [--gc-iso ISO] [--ps2-iso ISO]
     replaces the payload's BIN entries (GC arc : PS2 arc, archive indices as the game numbers them) and/or ETM
     BINs (paired by name) with le_mirror-converted rebuilt BINs; every other byte of the payload is kept.
     Since 2026-10-26 (lane props-ps2-26) every PS2 object is reduced in the convert step (mesh_lod, UV guard; see
     LOD) and self-checked (self_check: fewer triangles than the GC model and no more bytes, reduction step run); an
     object that fails is skipped and listed. The report's 'graft' block is the deliverable (--graft-json): a member
     set for t11-fix.py {'graft': ...}, never a whole-.dar replacement.
     --keep-larger --keep-larger-reason "..."   (refused without a reason) ship an object that fails the self-check.
     History of --keep-larger: also convert an object whose PS2 mesh is not smaller (PS2 assets are the target; lane objs,
                       2026-10-14). Without it such an object keeps its GC geometry (the 10-11 dars).
     --world-owned 20,...  GC room BINs the PS2 version draws as part of its scenario SMD (so the PS2 world package
                       already draws it): the GC copy keeps its header, joints and part headers with no triangles
                       (empty parts; one unused vertex so no array is empty). r101 BIN 0x20 = the burning stake
                       (SetObj00), PS2 SMD_016 / SMD_120.
     --etm-empty et0000.bin,...  etc models whose PS2 model is a placeholder (window panes et0000 / et2500: one
                       degenerate triangle): emptied like --world-owned (the PS2 draws nothing there; lane purge-props24).
     --etm-restore-gc et0000.bin,...  the reverse for an already emptied payload: the model goes back to le_mirror(GC)
                       (needs --etm). Window panes: PS2 draws no intact pane, the user requires glass and bars
                       (2026-10-26, lane windows26; GC-ASSET allowlist).
     --etm-member-from et0000.tpl=<dar>,...  an ETM sub-file copied byte for byte from another native dar (same size
                       only; needs --etm): the pane's colour record back to the GC package key where a PS2 picture
                       replaced it (r105 / r107 / r111 / r11c / r11f; r100's record is the source).
     --etm-from et1000.bin=r109,...  an etc model absent from this room's PS2 ETM, taken from that room's PS2 ETM;
                       refused unless this room's GC model is byte-identical to that room's (the same object). r11a
                       et1000 (torch type 4) = r109's.
  ps2_objects.py selftest <gc.bin>   (rebuild with the GC geometry itself as the "PS2" input; layout check)
"""
import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[2] / 'tools')]
import convert_character as cc  # noqa: E402
import convert_room_bins as crb  # noqa: E402
import le_mirror as lm  # noqa: E402
import ps2_bin as pb  # noqa: E402
import room_smd as rs  # noqa: E402

PS2_ISO = '/mnt/c/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso'
GC_ISO = '/mnt/c/Game Dev/Emulators/Resident Evil 4 Debug (Disc 1)/Resident Evil 4 Debug (Disc 1).iso'
VERSIONS = (0x20010801, 0x20030818)
# --uv-fold (converter v3, lane objs 2026-10-15): the PS2 BINs address their textures with wrapping UVs (the r119 /
# village wood box et1100: u -0.961..-0.024), the GameCube models with UVs inside [0, 1] and the game sets clamp for
# many of them (GX wrap state), so a PS2 triangle outside [0, 1] drew one edge texel (the "dark block"); unsigned UV
# models also clamped negative UVs to 0 here. Each PS2 triangle is shifted by whole texture repeats (u, v separately)
# into [0, 1] when it fits (tolerance UV_FOLD_TOL); identical under wrap, correct under clamp. A triangle that spans
# more than one repeat keeps its UVs (stats uv_outside).
UV_FOLD = False
UV_FOLD_TOL = 0.02


def fold_uv(cs):
    """-> (corners with the triangle's UVs shifted by whole repeats into [0, 1], folded?, still outside?)"""
    uvs = [c[2] for c in cs]
    shift, outside = [0, 0], False
    for a in (0, 1):
        xs = [uv[a] for uv in uvs]
        if min(xs) >= -UV_FOLD_TOL and max(xs) <= 1 + UV_FOLD_TOL:
            continue
        k = math.floor(min(xs) + UV_FOLD_TOL)
        if max(xs) - k <= 1 + UV_FOLD_TOL:
            shift[a] = k
        else:
            outside = True
    if not shift[0] and not shift[1]:
        return cs, False, outside
    return [(p, n, (uv[0] - shift[0], uv[1] - shift[1]), w) for p, n, uv, w in cs], True, outside


# Dreamcast reduction inside the convert step (lane props-ps2-26 2026-10-26, coordinator scope: "fix the converter
# itself"). On by default (--no-lod is test-only): the PS2 triangles go through mesh_lod's quadric simplifier with the
# UV guard (LOD_UV_GUARD, as the world packages' --lod-uv-guard) before part assignment and strip building. Target:
# fewer triangles than the GC model it replaces; the geometric error is capped at LOD_MAX_ERR of the model's bounds
# diagonal, so a reduction that would need more stops there (and the self-check refuses the object: it stays listed for
# review, never shipped larger). Vertices on a material / bone-weight seam are locked (no texture or skin tear).
LOD = True
LOD_UV_GUARD = 0.02
LOD_MAX_ERR = 0.04
LOD_STEPS = 24


def lod_reduce(ps2, gc_tris):
    """[(tex, [(p, n, uv, w)] * 3)] -> (reduced list, report). Always reports (the self-check needs the step recorded)."""
    import mesh_lod as ml
    rep = dict(step='mesh_lod', uv_guard=LOD_UV_GUARD, target=gc_tris - 1, tris_in=len(ps2), tris_out=len(ps2), error=0.0)
    if len(ps2) < gc_tris:
        rep['note'] = 'already below the GC count'
        return ps2, rep
    pts = [c[0] for t, cs in ps2 for c in cs]
    lo = [min(p[a] for p in pts) for a in range(3)]
    hi = [max(p[a] for p in pts) for a in range(3)]
    diag = math.sqrt(sum((hi[a] - lo[a]) ** 2 for a in range(3))) or 1.0
    ids, where, seam, tris = {}, {}, {}, []
    for tex, cs in ps2:
        vs = []
        for p, n, uv, w in cs:
            v = where.setdefault(p, len(where))
            ids[v] = p
            seam.setdefault(v, set()).add((tex, w))
            vs.append(v)
        if len(set(vs)) < 3:
            continue
        tris.append((tuple(vs), tuple((uv, n, (tex, w)) for p, n, uv, w in cs)))
    locked = [v for v, s in seam.items() if len(s) > 1]
    old = ml.UV_GUARD
    ml.UV_GUARD = LOD_UV_GUARD
    try:
        s = ml.Simplifier(ids, tris, locked)
        cur = tris
        for k in range(1, LOD_STEPS + 1):
            s.run_to(diag * LOD_MAX_ERR * k / LOD_STEPS)
            cur = s.triangles()
            rep['error'] = round(s.error / diag, 5)
            if len(cur) < gc_tris:
                break
    finally:
        ml.UV_GUARD = old
    out = [(a[0][2][0], [(ids[v], a[j][1], a[j][0], a[j][2][1]) for j, v in enumerate(vs)]) for vs, a in cur]
    rep['tris_out'] = len(out)
    return out, rep


class SizeCheckError(ValueError):
    pass


def self_check(st, before_bytes=None, after_bytes=None):
    """(d) of the 10-26 scope: a converted object may not be larger than what it replaces (triangles; bytes when known)
    and must have run the reduction step. Raises SizeCheckError."""
    if 'lod' not in st:
        raise SizeCheckError('reduction step skipped')
    if st['gc_tris'] and st['out_tris'] >= st['gc_tris']:
        raise SizeCheckError('PS2 %d triangles >= GC %d after reduction' % (st['out_tris'], st['gc_tris']))
    if before_bytes is not None and after_bytes is not None and after_bytes > before_bytes:
        raise SizeCheckError('output %d bytes > source %d' % (after_bytes, before_bytes))


def al(n, a=32):
    return (n + a - 1) & ~(a - 1)


def sha(b):
    return hashlib.sha256(b).hexdigest()


# ------------------------------------------------------------------------------------------ GC side


class GcModel:
    def __init__(self, d):
        self.d = d
        u32 = lambda o: struct.unpack_from('>I', d, o)[0]
        u16 = lambda o: struct.unpack_from('>H', d, o)[0]
        self.version = u32(0x3C)
        if self.version not in VERSIONS:
            raise ValueError('unsupported ModelData version %#x' % self.version)
        self.head, self.clr, self.tex, self.wgt = u32(0), u32(0x0C), u32(0x10), u32(0x14)
        self.nw, self.nj, self.nd = d[0x18], d[0x19], u16(0x1A)
        self.parts_off, self.flags, self.ntex = u32(0x1C), u32(0x20), u32(0x24)
        self.shift, self.ext, self.shape = d[0x28], u16(0x2A), u32(0x2C)
        self.vtx, self.nrm, self.nv, self.nn = u32(0x30), u32(0x34), u16(0x38), u16(0x3A)
        self.blend, self.flip = (u32(0x40), u32(0x44)) if self.version == 0x20030818 else (0, 0)
        if self.shape:
            raise ValueError('shape (morph) model: not converted')
        # extended weights (r10c BIN 0x1f, 10-24): a palette of more than 255 entries. +0x2A holds the full count
        # (+0x18 its low byte) and each record is 12 bytes: 3 u16 joint ids, u16 count, 4 u8 weights.
        self.xw = self.ext > 0xFF
        if self.xw:
            self.nw = self.ext
        self.stride = 8 if self.flags & 0x80000000 else 6
        self.nstride = 4 if self.flags & 0x20000000 else 8
        self.scale = 1.0 / (1 << self.shift)
        self.pos = [struct.unpack_from('>4h', d, self.vtx + 8 * i) for i in range(self.nv)]
        if self.nstride == 4:
            self.nrms = [struct.unpack_from('>3bB', d, self.nrm + 4 * i) for i in range(self.nn)]
        else:
            self.nrms = [struct.unpack_from('>3hH', d, self.nrm + 8 * i) for i in range(self.nn)]
        self.weights = []
        for i in range(self.nw):
            if self.xw:
                o = self.wgt + 12 * i
                r = struct.unpack_from('>4H4B', d, o)
                n = r[3]
                self.weights.append((tuple(r[:n]), tuple(r[4:4 + n])))
                continue
            o = self.wgt + 8 * i
            n = d[o + 3]
            self.weights.append((tuple(d[o:o + n]), tuple(d[o + 4:o + 4 + n])))
        # parts
        self.parts = []
        cur = self.parts_off
        for k in range(self.nd):
            hdr = d[cur:cur + 0x20]
            size = struct.unpack_from('>I', hdr, 0x18)[0]
            tris, s, end = [], cur + 0x20, cur + 0x20 + size
            while s < end:
                op = d[s]; s += 1
                if op == 0:
                    continue
                if op not in (0x80, 0x90, 0x98):
                    raise ValueError('part %d opcode %#x' % (k, op))
                n = struct.unpack_from('>H', d, s)[0]; s += 2
                recs = [struct.unpack_from('>%dH' % (self.stride // 2), d, s + self.stride * j) for j in range(n)]
                s += n * self.stride
                tris += list(cc.triangulate(op, recs))
            self.parts.append(dict(hdr=bytes(hdr), tris=tris, stat=struct.unpack_from('>I', hdr, 0x1C)[0]))
            cur = end
        self.parts_end = cur
        self.uvs_count = 1 + max((r[-1] for p in self.parts for t in p['tris'] for r in t), default=-1)
        # sections must be in the source order this writer reproduces
        order = [self.vtx, self.nrm] + ([self.clr] if self.clr else []) + [self.tex, self.wgt, self.parts_off]
        if order != sorted(order) or self.head >= self.vtx:
            raise ValueError('unexpected section order %s' % [hex(x) for x in order])
        for t in (self.blend, self.flip):
            if t and t < self.parts_end:
                raise ValueError('joint table before the parts')

    def uv(self, i):
        if self.flags & 0x80000000:
            u, v = struct.unpack_from('>2h', self.d, self.tex + 4 * i)
            return u / 256.0, v / 256.0
        u, v = struct.unpack_from('>2H', self.d, self.tex + 4 * i)
        return u / 32768.0, v / 32768.0

    def p(self, i):
        x, y, z, _ = self.pos[i]
        return x * self.scale, y * self.scale, z * self.scale

    def normal_unit(self):
        """Length of a unit normal in this model's normal format (median of the source normals)."""
        ls = sorted(math.sqrt(a * a + b * b + c * c) for a, b, c, _ in self.nrms)
        return ls[len(ls) // 2] if ls else (64.0 if self.nstride == 4 else 16384.0)

    def table(self, off):
        """bytes of a blend / flip joint table (u32 count + payload)."""
        n = struct.unpack_from('>I', self.d, off)[0]
        size = 4 + n * (8 if off == self.blend else 2)
        return self.d[off:off + size]


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


class Grid:
    """Nearest point over a uniform hash grid (pure Python)."""
    def __init__(self, pts, cell=200.0):
        self.pts, self.cell, self.g = pts, cell, {}
        for i, p in enumerate(pts):
            self.g.setdefault(self.key(p), []).append(i)

    def key(self, p):
        c = self.cell
        return (int(math.floor(p[0] / c)), int(math.floor(p[1] / c)), int(math.floor(p[2] / c)))

    def nearest(self, p, ok=None):
        kx, ky, kz = self.key(p)
        best, bi = None, -1
        for r in range(0, 64):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    for dz in range(-r, r + 1):
                        if max(abs(dx), abs(dy), abs(dz)) != r:
                            continue
                        for i in self.g.get((kx + dx, ky + dy, kz + dz), ()):
                            if ok is not None and not ok(i):
                                continue
                            q = self.pts[i]
                            d = (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 + (q[2] - p[2]) ** 2
                            if best is None or d < best:
                                best, bi = d, i
            if best is not None and math.sqrt(best) < r * self.cell:
                return bi, math.sqrt(best)
        if best is None:
            return -1, float('inf')
        return bi, math.sqrt(best)


# ------------------------------------------------------------------------------------------ rebuild


def gc_winding_sense(m):
    """+1 when GC face normals (cross(b-a, c-a)) agree with the corner normals, -1 when opposed."""
    agree = 0
    for part in m.parts:
        for t in part['tris']:
            a, b, c = (m.p(r[0]) for r in t)
            f = cross(sub(b, a), sub(c, a))
            n = [m.nrms[r[1]][:3] for r in t]
            s = dot(f, (n[0][0] + n[1][0] + n[2][0], n[0][1] + n[1][1] + n[2][1], n[0][2] + n[1][2] + n[2][2]))
            agree += 1 if s > 0 else -1 if s < 0 else 0
    return 1 if agree >= 0 else -1


# PS2 material image -> GC TPL image, for models whose PS2 TPL lists the images in another order than the GC TPL
# (checked by image size: r104 et1700 gate, GC img0 128x256 panels / img1 64x64 frame, PS2 img0 64x64 / img1 128x256;
# without it the panels' PS2 triangles land in the 64x64 frame part and the PS2 pictures' sizes disagree with the GC
# record, which hid the gate in the objs13 look check 10-15). Keyed by the etc model name.
TEX_MAPS = {'et1700.bin': {0: 1, 1: 0}}
# PS2 atlas (lane purge-props24 2026-10-24, coordinator-approved tool extension): objects whose one GC picture the PS2
# split into several pictures (r117 BIN 0x1f: GC image 0 256x256 <- PS2 images 0 128x128, 1 128x16, 3 64x64). The PS2
# pictures the model uses are packed into one atlas (atlas_for: deterministic grid fill inside the GC image size,
# largest first), each PS2 triangle's UVs are mapped into its picture's rectangle, and ps2_objects_tex.py composes the
# atlas picture from the same layout. (room, room-archive BIN index) -> the GC image size the atlas fills (checked
# against the GC TPL header by ps2_objects_tex.py).
ATLAS_OBJECTS = {('r117', 0x1f): (256, 256)}


def atlas_for(ps2_tpl, off, used, gc_wh):
    """-> {ps2 image: (x, y, w, h)}, (W, H): the atlas layout of PS2 TPL images `used` (sizes as the geometry samples
    them: transposed when the entry's rotate flag is set) inside the GC image size gc_wh (step 8 texels)."""
    sys.path.insert(0, str(HERE / 'd367' / 'test12fx'))
    import ps2_tpl_decode as ptd  # noqa: E402
    ents = ptd.parse_tpl(ps2_tpl[off:])['entries']
    sizes = {}
    for i in used:
        h = ents[i]
        w_, h_ = h['width'], h['height']
        sizes[i] = (h_, w_) if h['interlace'] & 1 else (w_, h_)
    gw, gh = gc_wh
    occ = []
    lay = {}
    for i in sorted(sizes, key=lambda k: (-sizes[k][0] * sizes[k][1], k)):
        w_, h_ = sizes[i]
        spot = None
        for y in range(0, gh - h_ + 1, 8):
            for x in range(0, gw - w_ + 1, 8):
                if all(x + w_ <= ox or ox + ow <= x or y + h_ <= oy or oy + oh <= y for ox, oy, ow, oh in occ):
                    spot = (x, y); break
            if spot:
                break
        if spot is None:
            raise ValueError('atlas: PS2 images %s do not fit in %dx%d' % (sorted(sizes), gw, gh))
        lay[i] = (spot[0], spot[1], w_, h_); occ.append(lay[i])
    p2 = lambda n: 1 << max(3, (n - 1).bit_length())  # noqa: E731
    W = p2(max(x + w_ for x, y, w_, h_ in lay.values())); H = p2(max(y + h_ for x, y, w_, h_ in lay.values()))
    return lay, (W, H)


def atlas_uv_map(lay, wh, gc_image):
    """rebuild()'s atlas argument: {ps2 image: (gc image, u0, v0, su, sv)}."""
    W, H = wh
    return {i: (gc_image, x / W, y / H, w_ / W, h_ / H) for i, (x, y, w_, h_) in lay.items()}



def rebuild(gc_bytes, ps2_bytes, gc_tris_from=None, allow_empty=False, tex_map=None, atlas=None, pos_offset=None):
    """-> (new big-endian GC BIN, stats). gc_tris_from: selftest geometry list instead of the PS2 BIN.
    allow_empty: a model with no triangle is written (world-owned objects); otherwise it is refused (a PS2 placeholder
    such as the window panes et0000 / et2500, one degenerate triangle, is never converted silently)."""
    m = GcModel(gc_bytes)
    sense = gc_winding_sense(m)
    unit = m.normal_unit()
    # GC triangles for part assignment: centroid + part + texture image
    cent, cpart = [], []
    for k, part in enumerate(m.parts):
        for t in part['tris']:
            a, b, c = (m.p(r[0]) for r in t)
            cent.append(((a[0] + b[0] + c[0]) / 3, (a[1] + b[1] + c[1]) / 3, (a[2] + b[2] + c[2]) / 3))
            cpart.append(k)
    grid = Grid(cent)
    part_tex = [p['hdr'][0x0C] for p in m.parts]
    # corner colour: nearest GC draw vertex of the chosen part
    vgrid_pts, vgrid_rec, vgrid_part = [], [], []
    for k, part in enumerate(m.parts):
        for t in part['tris']:
            for r in t:
                vgrid_pts.append(m.p(r[0])); vgrid_rec.append(r); vgrid_part.append(k)
    vgrid = Grid(vgrid_pts)

    if gc_tris_from is None:
        pm = pb.parse_bin(ps2_bytes)
        ptex = [x['diffuse'] for x in pm.materials]
        ps2 = []
        for t, cs in pb.triangles(pm):
            if pos_offset:   # gc-audit25: model-space shift fitting a PS2 mesh to the GC skeleton (ps2_weapons fit)
                cs = [dict(c, p=tuple(a + b for a, b in zip(c['p'], pos_offset))) for c in cs]
            ps2.append((ptex[t], [(c['p'], c['n'], c['uv'], tuple(c['w'])) for c in cs]))
    else:
        ps2 = gc_tris_from(m)
    stats = dict(gc_tris=sum(len(p['tris']) for p in m.parts), ps2_tris=len(ps2), gc_parts=m.nd,
                 gc_vertices=m.nv, gc_normals=m.nn, gc_bytes=len(gc_bytes), no_tex_part=0, flipped=0,
                 weight_mismatch=0, degenerate=0, appended_weights=0, uv_folded=0, uv_outside=0)
    if LOD and gc_tris_from is None and ps2:
        ps2, stats['lod'] = lod_reduce(ps2, stats['gc_tris'])

    pal = list(m.weights)
    pal_index = {w: i for i, w in reversed(list(enumerate(pal)))}

    def palette(w):
        if not w:
            w = ((0, 1.0),)
        w = sorted(((int(b), float(f)) for b, f in w if f > 0.0005), key=lambda x: -x[1])[:3]
        tot = sum(f for b, f in w) or 1.0
        vals = [int(round(100 * f / tot)) for b, f in w]
        vals[0] += 100 - sum(vals)
        key = (tuple(b for b, f in w), tuple(vals))
        if key not in pal_index:
            pal_index[key] = len(pal); pal.append(key); stats['appended_weights'] += 1
        return pal_index[key]

    verts, vmap, nrms, nmap, uvs, umap = [], {}, [], {}, [], {}
    part_tris = [[] for _ in m.parts]
    part_ps2_tex = {}  # GC part -> the PS2 material images its triangles came from (ps2_objects_tex.py)
    lim = 32767
    for tex, cs in ps2:
        P = [c[0] for c in cs]
        if len(set(P)) < 3:
            stats['degenerate'] += 1
            continue
        cen = tuple(sum(p[i] for p in P) / 3 for i in range(3))
        gtex = (tex_map or {}).get(tex, tex)
        if atlas and tex in atlas:
            g_, u0, v0, su, sv = atlas[tex]
            gtex = g_
            cs = [(p, n, (u0 + uv[0] * su, v0 + uv[1] * sv), w) for p, n, uv, w in cs]
            stats['atlas_tris'] = stats.get('atlas_tris', 0) + 1
        ti, _ = grid.nearest(cen, lambda i: part_tex[cpart[i]] == gtex)
        if ti < 0:
            stats['no_tex_part'] += 1
            ti, _ = grid.nearest(cen)
        k = cpart[ti]
        f = cross(sub(P[1], P[0]), sub(P[2], P[0]))
        ns = [c[1] for c in cs]
        s = dot(f, (ns[0][0] + ns[1][0] + ns[2][0], ns[0][1] + ns[1][1] + ns[2][1], ns[0][2] + ns[1][2] + ns[2][2]))
        if (s > 0 and sense < 0) or (s < 0 and sense > 0):
            cs = [cs[0], cs[2], cs[1]]; stats['flipped'] += 1
        if UV_FOLD:
            cs, folded, outside = fold_uv(cs)
            stats['uv_folded'] += folded; stats['uv_outside'] += outside
        tri = []
        for p, n, uv, w in cs:
            wi = palette(w)
            vi_near, _ = vgrid.nearest(p, lambda i: vgrid_part[i] == k)
            rec = vgrid_rec[vi_near]
            if pal[wi][0] != m.weights[m.pos[rec[0]][3]][0]:
                stats['weight_mismatch'] += 1
            q = [int(round(x / m.scale)) for x in p]
            if max(abs(x) for x in q) > lim:
                raise ValueError('position outside the s16 range at shift %d' % m.shift)
            vk = (q[0], q[1], q[2], wi)
            if vk not in vmap:
                vmap[vk] = len(verts); verts.append(vk)
            ln = math.sqrt(dot(n, n)) or 1.0
            if m.nstride == 4:
                nq = tuple(max(-127, min(127, int(round(x / ln * unit)))) for x in n)
            else:
                nq = tuple(max(-32767, min(32767, int(round(x / ln * unit)))) for x in n)
            nk = nq + (wi,)
            if nk not in nmap:
                nmap[nk] = len(nrms); nrms.append(nk)
            if m.flags & 0x80000000:
                uq = (max(-32768, min(32767, int(round(uv[0] * 256)))), max(-32768, min(32767, int(round(uv[1] * 256)))))
            else:
                uq = (max(0, min(65535, int(round(uv[0] * 32768)))), max(0, min(65535, int(round(uv[1] * 32768)))))
            if uq not in umap:
                umap[uq] = len(uvs); uvs.append(uq)
            corner = (vmap[vk], nmap[nk]) + ((rec[2],) if m.stride == 8 else ()) + (umap[uq],)
            tri.append(corner)
        part_tris[k].append(tuple(tri))
        part_ps2_tex.setdefault(k, set()).add(tex)
    if not verts:
        if not allow_empty:
            raise ValueError('no PS2 triangle (placeholder model)')
        # world-owned / empty geometry: keep one unused vertex, normal and UV so no array is empty
        verts.append((0, 0, 0, 0)); nrms.append((0, 0, 0, 0)); uvs.append((0, 0))
    if len(verts) > 0xFFFF or len(nrms) > 0xFFFF:
        raise ValueError('array too large')
    xw = len(pal) > 0xFF   # extended weights form (12-byte records, full count at +0x2A)
    if len(pal) > 0xFFFF or (xw and not m.xw):
        raise ValueError('weight palette exceeds 255 entries')

    # ---- write (source section order)
    d = gc_bytes
    out = bytearray(d[:m.vtx])
    vtx = len(out)
    for x, y, z, wi in verts:
        out += struct.pack('>4h', x, y, z, wi)
    out += bytes(al(len(out)) - len(out))
    nrm = len(out)
    for nk in nrms:
        if m.nstride == 4:   # the byte normal's 4th field is the weight index's low byte (extended weights: index & 0xFF)
            out += struct.pack('>3bB', nk[0], nk[1], nk[2], nk[3] & 0xFF)
        else:
            out += struct.pack('>3hH', *nk)
    out += bytes(al(len(out)) - len(out))
    clr = 0
    if m.clr:
        clr = len(out)
        out += d[m.clr:m.tex]
        out += bytes(al(len(out)) - len(out))
    tex = len(out)
    for uq in uvs:
        out += struct.pack('>2h' if m.flags & 0x80000000 else '>2H', *uq)
    out += bytes(al(len(out)) - len(out))
    wgt = len(out)
    for ids, vals in pal:
        n = len(ids)
        if xw:
            out += struct.pack('>4H4B', *(list(ids) + [0] * (3 - n) + [n] + list(vals) + [0] * (4 - n)))
            continue
        out += bytes(list(ids) + [0] * (3 - n) + [n] + list(vals) + [0] * (4 - n))
    out += bytes(al(len(out)) - len(out))
    parts_off = len(out)
    stream_stats = dict(strips=0, triangles=0)
    for k, part in enumerate(m.parts):
        body = bytearray()
        tris = part_tris[k]
        if tris:
            # stripify over corner tuples (vertex identity = the whole record), GX strip order
            ids, back = {}, []
            for t in tris:
                for c in t:
                    if c not in ids:
                        ids[c] = len(back); back.append(c)
            for strip in crb.stripify([tuple(ids[c] for c in t) for t in tris]):
                for chunk in crb.split_strip(strip) if len(strip) > 0xFFFF else [strip]:
                    if len(chunk) == 3:
                        continue  # emitted below as one triangle list
                    body += struct.pack('>BH', 0x98, len(chunk))
                    for i in chunk:
                        body += struct.pack('>%dH' % (m.stride // 2), *back[i])
                    stream_stats['strips'] += 1
            singles = [s for s in crb.stripify([tuple(ids[c] for c in t) for t in tris]) if len(s) == 3]
            if singles:
                body += struct.pack('>BH', 0x90, 3 * len(singles))
                for s in singles:
                    for i in s:
                        body += struct.pack('>%dH' % (m.stride // 2), *back[i])
                stream_stats['triangles'] += len(singles)
        body += bytes(max(32, al(len(body))) - len(body))
        hdr = bytearray(part['hdr'])
        struct.pack_into('>I', hdr, 0x18, len(body))
        struct.pack_into('>I', hdr, 0x1C, len(tris) if part['stat'] == len(part['tris']) else part['stat'])
        out += hdr + body
    tables = {}
    for name, off in (('blend', m.blend), ('flip', m.flip)):
        if off:
            out += bytes(al(len(out)) - len(out))
            tables[name] = len(out)
            out += m.table(off)
    out += bytes(al(len(out)) - len(out))
    # file tail beyond the last section in the source (kept as padding size)
    hdr_put = lambda o, fmt, v: struct.pack_into(fmt, out, o, v)
    hdr_put(0x0C, '>I', clr); hdr_put(0x10, '>I', tex); hdr_put(0x14, '>I', wgt)
    out[0x18] = len(pal) & 0xFF
    hdr_put(0x1C, '>I', parts_off)
    if m.ext == m.nw or m.xw:
        hdr_put(0x2A, '>H', len(pal))
    hdr_put(0x30, '>I', vtx); hdr_put(0x34, '>I', nrm)
    hdr_put(0x38, '>H', len(verts)); hdr_put(0x3A, '>H', len(nrms))
    if m.version == 0x20030818:
        hdr_put(0x40, '>I', tables.get('blend', 0)); hdr_put(0x44, '>I', tables.get('flip', 0))
    new = bytes(out)
    # parse back with the converter's reader (exactness of the written layout)
    if xw or m.xw:   # the lean converter has no extended-weights reader: parse back with GcModel (le_mirror's layout)
        out_tris = sum(len(pt['tris']) for pt in GcModel(new).parts)
    else:
        out_tris = len(cc.parse_geometry(new)[9]) // 3
    stats['part_images'] = {str(k): [part_tex[k], sorted(v)] for k, v in sorted(part_ps2_tex.items())}
    stats.update(out_tris=out_tris, out_vertices=len(verts), out_normals=len(nrms), out_uvs=len(uvs),
                 out_weights=len(pal), out_bytes=len(new), **stream_stats,
                 empty_parts=sum(1 for t in part_tris if not t))
    if stats['out_tris'] != sum(len(t) for t in part_tris):
        raise ValueError('triangle count changed in the round trip')
    return new, stats


def to_le(be_bin, label='bin'):
    """le_mirror's ModelData conversion of one BIN (the native room payload form)."""
    sw = lm.Swapper(bytearray(be_bin), label)
    with sw.bounded(0, len(be_bin)):
        lm.fmt_bin(sw, 0, len(be_bin), {})
    return bytes(sw.data)


def selftest_geometry(m):
    out = []
    for part in m.parts:
        for t in part['tris']:
            cs = []
            for r in t:
                n = m.nrms[r[1]][:3]
                ids, vals = m.weights[m.pos[r[0]][3]]
                cs.append((m.p(r[0]), n, m.uv(r[-1]), tuple((b, v / 100.0) for b, v in zip(ids, vals))))
            out.append((part['hdr'][0x0C], cs))
    return out


# ------------------------------------------------------------------------------------------ archives


def etm_entries(b, en):
    """ETM: u32 count, 0x20 header, entries {u32 size, ... name @0x20, data @0x40} -> [(name, data off, data end)]"""
    n = struct.unpack_from(en + 'I', b, 0)[0]
    o, out = 0x20, []
    for _ in range(n):
        sz = struct.unpack_from(en + 'I', b, o)[0]
        nm = b[o + 0x20:o + 0x40].split(b'\0')[0].decode('latin-1')
        out.append((nm, o, o + sz if sz else len(b)))
        if not sz:
            break
        o += sz
    return out


def rebuild_tagged(data, en, replace):
    """Tagged archive with entries replaced ({index: bytes}); offsets recomputed in the source entry order,
    32-byte aligned; every other entry byte-identical."""
    n = struct.unpack_from(en + 'I', data, 0)[0]
    ents = rs.tagged_entries(data, en)
    offs = struct.unpack_from(en + '%dI' % n, data, 0x10)
    order = sorted((o, i) for i, o in enumerate(offs) if o)
    out = bytearray(data[:order[0][0]])
    new_offs = list(offs)
    for o, i in order:
        tag, s, e = ents[i]
        body = replace.get(i, data[s:e])
        out += bytes(al(len(out)) - len(out))
        new_offs[i] = len(out)
        out += body
    out += bytes(al(len(out)) - len(out))
    struct.pack_into(en + '%dI' % n, out, 0x10, *new_offs)
    return bytes(out)


NATIVE_TABLES = {b'ESQ\0': b'R4ESQTBL', b'NTR\0': None}


def remap_native_tables(old, new, inner=None):
    """The native room payload's prepared tables (ESQ effect sequences, NTR texture identities: header
    magic, version, count, 12, crc32(table), word24, word28 + count 12-byte rows of payload offsets) name
    absolute payload offsets and the payload size (native_effect.cpp bind_archive, native_ui.cpp adopt).
    Rebase every offset by its owning entry's move and the size words to the new payload bytes.
    inner {entry index: [(old rel start, old rel end, new rel start, replaced)]}: a rebuilt entry's
    sub-file moves (ETM); an offset inside a replaced sub-file body (past its 0x40 header) is refused."""
    import zlib
    oe, ne = rs.tagged_entries(old, '<'), rs.tagged_entries(new, '<')
    spans = sorted((s, e, ne[i][1], i) for i, (t, s, e) in enumerate(oe))

    def mapped(x):
        for s, e, s2, i in spans:
            if s <= x < e:
                if inner and i in inner:
                    for a, b, a2, repl in inner[i]:
                        if a <= x - s < b:
                            if repl and x - s >= a + 0x40:
                                raise ValueError('table offset %#x inside a replaced sub-file' % x)
                            return x - s - a + a2 + s2
                    raise ValueError('table offset %#x outside the sub-files of entry %d' % (x, i))
                return x - s + s2
        raise ValueError('table offset %#x outside every entry' % x)
    out = bytearray(new)
    report = {}
    for i, (tag, s, e) in enumerate(ne):
        if tag not in NATIVE_TABLES:
            continue
        magic, ver, cnt, row, crc, w24, w28 = struct.unpack_from('<8s6I', out, s)
        if row != 12 or ver != 1 or zlib.crc32(out[s + 32:s + 32 + 12 * cnt]) & 0xffffffff != crc:
            raise ValueError('%s table header not understood' % tag)
        for r in range(cnt):
            o = s + 32 + 12 * r
            a, b, c = struct.unpack_from('<3I', out, o)
            if tag == b'ESQ\0':
                checks = [(a, b)]
                struct.pack_into('<I', out, o, mapped(a))
            else:
                checks = [(a, 32), (b, 36), (c, 12)]
                struct.pack_into('<3I', out, o, mapped(a), mapped(b), mapped(c))
            for x, ln in checks:
                if old[x:x + ln] != new[mapped(x):mapped(x) + ln]:
                    raise ValueError('%s row %d: data at %#x did not move intact' % (tag, r, x))
        if tag == b'ESQ\0':
            if w24 != len(old) or w28:
                raise ValueError('ESQ size word')
            w24 = len(new)
        else:
            if w28 != len(old):
                raise ValueError('NTR size word')
            w28 = len(new)
        crc = zlib.crc32(out[s + 32:s + 32 + 12 * cnt]) & 0xffffffff
        struct.pack_into('<8s6I', out, s, magic, ver, cnt, row, crc, w24, w28)
        report[tag.rstrip(b'\0').decode()] = cnt
    return bytes(out), report


def room_atlas(gbin, ps2bin, ps2_tpl_entry, gc_wh):
    """-> (rebuild atlas map, layout report) for an ATLAS_OBJECTS room BIN: its PS2 TPL is the entry after the BIN."""
    if not ps2_tpl_entry or ps2_tpl_entry[0] != 'TPL':
        raise ValueError('atlas: the PS2 entry after the BIN is not a TPL')
    m = GcModel(gbin)
    gimgs = sorted({p['hdr'][0x0C] for p in m.parts if p['tris']})
    if len(gimgs) != 1:
        raise ValueError('atlas: the GC model samples images %s (one expected)' % gimgs)
    pm = pb.parse_bin(ps2bin)
    used = sorted({pm.materials[t]['diffuse'] for t, cs in pb.triangles(pm)})
    lay, wh = atlas_for(ps2_tpl_entry[1], 0, used, gc_wh)
    return atlas_uv_map(lay, wh, gimgs[0]), dict(gc_image=gimgs[0], size=list(wh), rects={str(k): list(v) for k, v in lay.items()})


def size_gate(args, st, before, after):
    """-> None (ship it) or the skip reason. --keep-larger needs --keep-larger-reason (scope (a), 10-26) and still
    records the self-check failure in the report."""
    try:
        self_check(st, before, after)
    except SizeCheckError as ex:
        if args.keep_larger:
            st['keep_larger'] = dict(reason=args.keep_larger_reason, check=str(ex))
            return None
        return 'self-check: %s' % ex
    return None


def room(args):
    if args.keep_larger and not (args.keep_larger_reason or '').strip():
        raise SystemExit('--keep-larger is refused without --keep-larger-reason "<why this object may ship larger>"')
    reconvert_etm = set(x for x in (args.reconvert_etm or '').split(',') if x)
    from assetpipe.rooms import GcIso
    dar = Path(args.dar).read_bytes()
    kind, size, dest, off = struct.unpack_from('<4I', dar, 0x20)
    if kind != 0 or off + size > len(dar):
        raise ValueError('dar: first entry is not the room payload')
    for pos in range(0x40, 0x400, 0x20):
        k2, s2, d2, o2 = struct.unpack_from('<4I', dar, pos)
        if k2 == 0xFFFFFFFF:
            break
        if o2 + s2 > off:
            raise ValueError('dar: an entry lies after the payload; not rewritten in place')
    pay = dar[off:off + size]
    g = GcIso(args.gc_iso)
    key = next((k for rr, k in g.rooms() if rr == args.room), None)
    gd = g.read(key)
    if gd[:32] == rs.CONTAINER_MAGIC:
        gd = rs.decode_das(gd)
    ge = rs.tagged_entries(gd, '>')
    pe = {i + 4: (t, b) for i, t, b in pb.dat_entries(pb.afs_read(args.ps2_iso, args.room + '.dat', pb.afs_index(args.ps2_iso)))}
    le = rs.tagged_entries(pay, '<')
    rep, report = {}, dict(room=args.room, dar_in=args.dar, dar_in_sha256=sha(dar), payload_in_bytes=len(pay), objects=[])
    reconvert = {int(x, 16) for x in (args.reconvert or '').split(',') if x}
    for pair in [x for x in (args.pairs or '').split(',') if x]:
        ga, pa = (int(x, 16) for x in pair.split(':'))
        i = ga - 4
        tag, s, e = ge[i]
        if tag.rstrip(b'\0') != b'BIN' or le[i][0].rstrip(b'\0') != b'BIN' or pe[pa][0] != 'BIN':
            raise ValueError('pair %s: not BIN entries' % pair)
        gbin = gd[s:e]
        cur = pay[le[i][1]:le[i][2]]
        src_le = to_le(gbin, pair)
        if cur.rstrip(b'\0') != src_le.rstrip(b'\0') and ga not in reconvert:
            raise ValueError('pair %s: the payload BIN is not le_mirror(GC BIN); refusing to replace modified data' % pair)
        atl = None
        if (args.room, ga) in ATLAS_OBJECTS:
            atl, lay = room_atlas(gbin, pe[pa][1], pe.get(pa + 1), ATLAS_OBJECTS[(args.room, ga)])
        new, st = rebuild(gbin, pe[pa][1], atlas=atl)
        if atl:
            st['atlas'] = lay
        why = size_gate(args, st, len(cur), len(to_le(new, pair)))
        if why:
            st.update(kind='room BIN', gc_arc=hex(ga), ps2_arc=hex(pa), skipped=why)
            report['objects'].append(st)
            continue
        rep[i] = to_le(new, pair)
        report.setdefault('graft_members', []).append('%#04x BIN' % ga)
        st.update(kind='room BIN', gc_arc=hex(ga), ps2_arc=hex(pa), le_bytes_before=len(cur), le_bytes_after=len(rep[i]))
        report['objects'].append(st)
    for x in [x for x in (args.world_owned or '').split(',') if x]:
        ga = int(x, 16)
        i = ga - 4
        tag, s, e = ge[i]
        if tag.rstrip(b'\0') != b'BIN' or le[i][0].rstrip(b'\0') != b'BIN' or i in rep:
            raise ValueError('world-owned %s: not a free BIN entry' % x)
        gbin = gd[s:e]
        cur = pay[le[i][1]:le[i][2]]
        if cur.rstrip(b'\0') != to_le(gbin, x).rstrip(b'\0'):
            raise ValueError('world-owned %s: the payload BIN is not le_mirror(GC BIN)' % x)
        new, st = rebuild(gbin, None, lambda m: [], allow_empty=True)
        rep[i] = to_le(new, x)
        st.update(kind='room BIN', gc_arc=hex(ga), ps2_arc='world', le_bytes_before=len(cur), le_bytes_after=len(rep[i]))
        report['objects'].append(st)
    inner = {}
    if args.etm:
        ei = next(i for i, (t, s, e) in enumerate(ge) if t.rstrip(b'\0') == b'ETM')
        gb = gd[ge[ei][1]:ge[ei][2]]
        lb = bytearray(pay[le[ei][1]:le[ei][2]])
        pbm = next(b for t, b in pe.values() if t == 'ETM')
        gents = etm_entries(gb, '>'); lents = etm_entries(bytes(lb), '<')
        pents = {nm: pbm[s + 0x40:e] for nm, s, e in etm_entries(pbm, '<')}
        ps2_from = {}
        for spec in [x for x in (args.etm_from or '').split(',') if x]:
            # --etm-from et1000.bin=r109: an etc model absent from this room's PS2 ETM taken from another PS2 room's
            # ETM, only when this room's GC model is byte-identical to that room's GC model (the same object).
            nm, src_room = spec.split('=')
            sk = next((k for rr, k in g.rooms() if rr == src_room), None)
            sgd = g.read(sk)
            if sgd[:32] == rs.CONTAINER_MAGIC:
                sgd = rs.decode_das(sgd)
            sge = rs.tagged_entries(sgd, '>')
            sgb = next(sgd[s:e] for t, s, e in sge if t.rstrip(b'\0') == b'ETM')
            sg = {n: sgb[s + 0x40:e] for n, s, e in etm_entries(sgb, '>')}
            mine = {n: gb[s + 0x40:e] for n, s, e in etm_entries(gb, '>')}
            if nm not in mine or nm not in sg or mine[nm] != sg[nm]:
                raise ValueError('--etm-from %s: GC %s differs from (or is absent in) %s' % (spec, nm, src_room))
            spe = {i + 4: (t, b) for i, t, b in pb.dat_entries(pb.afs_read(args.ps2_iso, src_room + '.dat', pb.afs_index(args.ps2_iso)))}
            spbm = next(b for t, b in spe.values() if t == 'ETM')
            sp = {n: spbm[s + 0x40:e] for n, s, e in etm_entries(spbm, '<')}
            if nm in pents or nm not in sp:
                raise ValueError('--etm-from %s: %s is in this room\'s PS2 ETM or absent in %s' % (spec, nm, src_room))
            pents[nm] = sp[nm]; ps2_from[nm] = src_room
        want = None if args.etm == 'all' else set(args.etm.split(','))
        etm_empty = set(x for x in (args.etm_empty or '').split(',') if x)
        etm_restore = set(x for x in (args.etm_restore_gc or '').split(',') if x)
        etm_member_from = {}
        for spec in [x for x in (args.etm_member_from or '').split(',') if x]:
            mnm, mdar = spec.split('=', 1)
            md = Path(mdar).read_bytes()
            mk, msz, _, moff = struct.unpack_from('<4I', md, 0x20)
            mpay = md[moff:moff + msz]
            mle = rs.tagged_entries(mpay, '<')
            mb = next(mpay[a:z] for t, a, z in mle if t.rstrip(b'\0') == b'ETM')
            hit = [mb[a:z] for n2, a, z in etm_entries(mb, '<') if n2 == mnm]
            if len(hit) != 1:
                raise ValueError('--etm-member-from %s: not one %s in that ETM' % (spec, mnm))
            etm_member_from[mnm] = hit[0]
        if etm_empty & etm_restore:
            raise ValueError('--etm-empty and --etm-restore-gc name the same model')
        if want is not None:
            want |= etm_empty
        pieces = []
        if lents[-1][2] != len(lb) or lents[0][1] != 0x20:
            raise ValueError('ETM sub-files do not tile the entry')
        for (nm, s, e), (lnm, ls, le_) in zip(gents, lents):
            if nm != lnm:
                raise ValueError('ETM order differs')
            body = bytes(lb[ls:le_])
            if nm in etm_member_from:
                # --etm-member-from et0000.tpl=<dar>: this ETM sub-file taken byte for byte from another native dar's
                # ETM (the same object's packaged record); refused unless the sizes match (no payload offset moves).
                src_body = etm_member_from[nm]
                if len(src_body) != len(body):
                    raise ValueError('--etm-member-from %s: %d bytes here, %d in the source' % (nm, len(body), len(src_body)))
                report['objects'].append(dict(kind='etc', name=nm, member_from=args.etm_member_from, le_bytes_before=len(body),
                                              le_bytes_after=len(src_body), same=src_body == body))
                body = src_body
            elif nm in etm_restore:
                # --etm-restore-gc (lane windows26 2026-10-26): put the GC model back where an earlier pass emptied it.
                # PS2 draws no intact window pane (et0000 / et2500: one degenerate triangle; the PS2 Et00_init loads
                # it exactly as GC does), but the user requires glass and bars (10-26), so the GC pane returns
                # (GC-ASSET allowlist row). Accepted inputs: the emptied model (--etm-empty output) or the GC model.
                gbin = gb[s + 0x40:e]
                src_le = to_le(gbin, nm)
                emptied = to_le(rebuild(gbin, None, lambda m: [], allow_empty=True)[0], nm)
                cur = body[0x40:].rstrip(b'\0')
                if cur not in (src_le.rstrip(b'\0'), emptied.rstrip(b'\0')):
                    raise ValueError('--etm-restore-gc %s: the payload model is neither le_mirror(GC) nor its emptied form' % nm)
                h = bytearray(body[:0x40])
                size = al(0x40 + len(src_le))
                struct.pack_into('<I', h, 0, size if struct.unpack_from('<I', h, 0)[0] else 0)
                nb = bytes(h) + src_le + bytes(size - 0x40 - len(src_le))
                report['objects'].append(dict(kind='etc', name=nm, restored='GC', le_bytes_before=len(body),
                                              le_bytes_after=len(nb),
                                              was='emptied' if cur == emptied.rstrip(b'\0') else 'GC'))
                body = nb
            elif nm.lower().endswith('.bin') and nm in pents and (want is None or nm in want):
                gbin = gb[s + 0x40:e]
                try:
                    src_le = to_le(gbin, nm)
                    if body[0x40:].rstrip(b'\0') != src_le.rstrip(b'\0') and nm not in reconvert_etm:
                        raise ValueError('ETM %s is not le_mirror(GC)' % nm)
                    if nm in etm_empty:
                        # --etm-empty: the PS2 model is a placeholder (no triangle): the GC copy keeps its header,
                        # joints and part headers with no triangles, as --world-owned
                        new, st = rebuild(gbin, None, lambda m: [], allow_empty=True)
                        st['ps2'] = 'placeholder (emptied)'
                    else:
                        new, st = rebuild(gbin, pents[nm], tex_map=TEX_MAPS.get(nm.lower()))
                    nl = to_le(new, nm)
                    h = bytearray(body[:0x40])
                    size = al(0x40 + len(nl))
                    struct.pack_into('<I', h, 0, size if struct.unpack_from('<I', h, 0)[0] else 0)
                    nb = bytes(h) + nl + bytes(size - 0x40 - len(nl))
                    why = None if nm in etm_empty else size_gate(args, st, al(0x40 + len(src_le)), len(nb))
                    if why:
                        st.update(kind='etc', name=nm, skipped=why)
                        report['objects'].append(st)
                    else:
                        report.setdefault('graft_members', []).append(nm)
                        st.update(kind='etc', name=nm, le_bytes_before=len(body), le_bytes_after=len(nb))
                        if nm in ps2_from:
                            st['ps2_from'] = ps2_from[nm] + '.dat:ETM/' + nm
                        report['objects'].append(st)
                        body = nb
                except ValueError as ex:
                    report['objects'].append(dict(kind='etc', name=nm, skipped=str(ex)))
            pieces.append((ls, le_, body, body != bytes(lb[ls:le_])))
        newetm = bytearray(lb[:0x20])
        moves = [(0, 0x20, 0, False)]
        for ls, le_, b, repl in pieces:
            moves.append((ls, le_, len(newetm), repl))
            newetm += b
        inner[ei] = moves
        newetm += bytes(al(len(newetm)) - len(newetm))
        rep[ei] = bytes(newetm)
    newpay = rebuild_tagged(pay, '<', rep)
    if args.pad_to:
        # Equalised gate arm: zero-pad the payload to the control's bytes so heap 4 keeps the control layout
        # (the H2 frame 660 em10 parts allocation is heap-4-layout dependent until D0).
        pad = len(pay) if args.pad_to == 'source' else int(args.pad_to, 0)
        if pad < len(newpay) or pad % 32:
            raise ValueError('--pad-to %d is below the payload or unaligned' % pad)
        newpay += bytes(pad - len(newpay))
    newpay, report['native_tables'] = remap_native_tables(pay, newpay, inner)
    out = bytearray(dar[:off]) + newpay
    out += bytes(al(len(out), 2048) - len(out))
    struct.pack_into('<4I', out, 0x20, 0, len(newpay), 0, off)
    Path(args.out).write_bytes(bytes(out))
    report.update(payload_out_bytes=len(newpay), payload_saved=len(pay) - len(newpay), dar_out=args.out,
                  dar_out_sha256=sha(bytes(out)), tool_sha256=sha(Path(__file__).read_bytes()))
    report['graft'] = {'dest': 'st1/%s.dar' % args.room if args.room != 'r200' else 'st2/r200.dar',
                       'source': args.out, 'members': report.get('graft_members', [])}
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=1))
    if args.graft_json:
        # scope (c): the deliverable is a graft member set (t11-fix.py {'graft': {dest: (source, members)}}); the
        # written .dar is only the member source, never staged whole.
        Path(args.graft_json).write_text(json.dumps(report['graft'], indent=1))
    for o in report['objects']:
        print('%-10s %-14s tris %s -> %s  bytes %s -> %s %s' % (o.get('kind'), o.get('name', o.get('gc_arc', '')), o.get('gc_tris'),
              o.get('out_tris'), o.get('le_bytes_before'), o.get('le_bytes_after'), o.get('skipped', '')))
    print('payload %d -> %d (saved %d)' % (len(pay), len(newpay), len(pay) - len(newpay)))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    a = sp.add_parser('bin'); a.add_argument('gc'); a.add_argument('ps2'); a.add_argument('out'); a.add_argument('--json')
    a = sp.add_parser('selftest'); a.add_argument('gc')
    a = sp.add_parser('room')
    a.add_argument('--dar', required=True); a.add_argument('--room', required=True); a.add_argument('--pairs')
    a.add_argument('--etm'); a.add_argument('--pad-to'); a.add_argument('--out', required=True); a.add_argument('--json')
    a.add_argument('--keep-larger', action='store_true', help='refused without --keep-larger-reason (10-26)')
    a.add_argument('--keep-larger-reason'); a.add_argument('--graft-json', help='write the graft member set here')
    a.add_argument('--reconvert-etm', help='ETM models (name,...) already converted in the input: rebuilt from GC + PS2 again')
    a.add_argument('--no-lod', action='store_true', help='test only: skip the mesh_lod step (the self-check then refuses)')
    a.add_argument('--world-owned'); a.add_argument('--etm-from')
    a.add_argument('--reconvert', help='room BINs (hex,...) already converted in the input dar: rebuilt from the GC source again')
    a.add_argument('--etm-member-from', help='ETM sub-files (name=<native dar>,...) copied byte for byte from that dar (same size only)')
    a.add_argument('--etm-restore-gc', help='etc models (name,...) put back as le_mirror(GC) where emptied (window panes, lane windows26)')
    a.add_argument('--etm-empty', help='etc models (name,...) whose PS2 model is a placeholder: emptied (lane purge-props24)')
    a.add_argument('--uv-fold', action='store_true', help='converter v3: fold PS2 triangle UVs into [0, 1] (UV_FOLD)')
    a.add_argument('--gc-iso', default=GC_ISO); a.add_argument('--ps2-iso', default=PS2_ISO)
    args = ap.parse_args()
    if args.cmd == 'bin':
        new, st = rebuild(Path(args.gc).read_bytes(), Path(args.ps2).read_bytes())
        Path(args.out).write_bytes(new)
        if args.json:
            Path(args.json).write_text(json.dumps(st, indent=1))
        print(json.dumps(st))
    elif args.cmd == 'selftest':
        g = Path(args.gc).read_bytes()
        new, st = rebuild(g, None, selftest_geometry)
        to_le(new)
        print(json.dumps(st))
    else:
        global UV_FOLD, LOD
        UV_FOLD = args.uv_fold
        LOD = not args.no_lod
        room(args)


if __name__ == '__main__':
    main()
