#!/usr/bin/env python3
"""Room compile (lane engine19): one versioned per-room data file (R4RC v1) from the room's GC collision (SAT).

The file replaces the grid the ENGINE_PREVIEW build embedded in the program (+83 KB). It is loaded at room entry
into room memory (heap 4, re4dc_static_alloc) by platform/actor_rt.c; with no file the room runs the source path.

Container (little-endian, the world18 I-007 contract; owner: engine19):
  header 64 B: magic 'R4RC', u16 version=1, u16 header_bytes=64, u32 room_id, u32 section_count, u32 file_bytes,
               u32 flags, u16 grid_w, u16 grid_h, u32 cell_mm, s32 x0_mm, s32 z0_mm, f32 world_ymin, f32 world_ymax,
               u32 payload_crc32 (bytes 64..file_bytes), 12 B zero
  directory  : section_count x 32 B: tag4, u16 section_version, u16 flags (bit0 required), u32 offset, u32 bytes,
               u32 count, u32 stride, u32 alignment, u32 reserved
  sections   : 16 B aligned, nonoverlapping, inside file_bytes. Unknown optional sections are ignored by the loader.

Sections in v1:
  SRCB v1  40 B records: source tag4, u32 source bytes, sha256[32] (the SAT member this file was compiled from)
  GRID v1  movement collision + foot floor grid (same semantics as tools/enginebake/build_grid.py EDGR v1, which the
           ENGINE_PREVIEW grid was, minus the flow-field passability bits the preview never used):
           u16 nplane, u16 nseg, u16 ncombo, u16 nwl, u16 bw, u16 bh, u16 nblock, u16 0
           u16 block[bw*bh]       8x8-cell blocks: 0xFFFF = all cells without floor, else a block index (identical
                                  blocks share one)
           (pad to 4)
           u16 bcell[nblock][64]  row-major in the block (z then x): 0xFFFF = no floor (source path), else a combo
           combo[ncombo] 6 B      u16 floor plane, u16 first index in wl, u8 nwall, u8 pad
           (pad to 4)
           f32 plane[nplane][3]   y = a x + c z + d (exact triangle planes)
           s16 seg[nseg][6]       x0 z0 x1 z1 ymin ymax, cm (the wall triangle's longest XZ edge)
           u16 wl[nwl]            wall lists; identical lists are stored once
  (later: VIS, LAYR, SCEN; a VIS section is only added when the Task 2 measurement clears its stop rule)

Rooms with extra SAT members (object collision: r109, r119, r11e, r224, ...) still get a grid from the room SAT
(member 1); the runtime only owns movement in rooms whose file sets GRID flag bit1 'static' (no extra SAT members).

Usage: room_compile.py --iso <GC disc1 iso> --out <dir> r101 r103 ...   (writes <dir>/<room>/room.r4rc, a JSON report
       and <dir>/MANIFEST.tsv). Deterministic: same SAT, same bytes (no timestamps).
"""
import argparse
import hashlib
import json
import math
import os
import struct
import sys
import subprocess
import tempfile
import zlib
import pathlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import convert_sat  # noqa: E402
import room_smd  # noqa: E402
from build_grid import tri_xz_contains, plane_of, seg_dist, BODY_R  # noqa: E402

COMPILER = 'room_compile/1'
CELL = 1000.0


def sat_members(iso, room):
    from assetpipe.rooms import GcIso
    g = GcIso(iso)
    k = next((k for r, k in g.rooms() if r == room), None)
    if not k:
        raise SystemExit('%s: no .das on the disc' % room)
    d = g.read(k)
    if d[:32] == room_smd.CONTAINER_MAGIC:
        d = room_smd.decode_das(d)
    e = room_smd.archive_endian(d)
    return [(i, d[s:t]) for i, (tag, s, t) in enumerate(room_smd.tagged_entries(d, e)) if tag == b'SAT\0'], k


def build_cells(sat_bytes):
    with tempfile.NamedTemporaryFile(suffix='.SAT', delete=False) as f:
        f.write(sat_bytes)
        tmp = f.name
    try:
        d = convert_sat.parse_sat(pathlib.Path(tmp), source_scale=1.0)
    finally:
        os.unlink(tmp)
    V, P = d['vertices'], d['polygons']
    nfl = d['floor_count'] + d['slope_count']
    floors = []
    for i in range(nfl):
        v0, v1, v2 = (V[k] for k in P[i][:3])
        pl = plane_of(v0, v1, v2)
        if pl:
            floors.append((v0, v1, v2, pl))
    walls = []
    for i in range(nfl, len(P)):
        pts = [V[k] for k in P[i][:3]]
        best = max(((p, q) for p in pts for q in pts), key=lambda e: (e[0][0] - e[1][0]) ** 2 + (e[0][2] - e[1][2]) ** 2)
        ys = [p[1] for p in pts]
        walls.append((best[0][0], best[0][2], best[1][0], best[1][2], min(ys), max(ys)))
    bmin, bmax = d['bounds_min'], d['bounds_max']
    C = CELL
    x0, z0 = math.floor(bmin[0] / C) * C, math.floor(bmin[2] / C) * C
    W = max(1, int(math.ceil((bmax[0] - x0) / C)))
    H = max(1, int(math.ceil((bmax[2] - z0) / C)))
    # bucket triangles / walls by cell (bbox overlap), then the build_grid rules per cell
    fb = {}
    for fi, f in enumerate(floors):
        xs, zs = [f[k][0] for k in range(3)], [f[k][2] for k in range(3)]
        for cz in range(max(0, int((min(zs) - z0) // C)), min(H - 1, int((max(zs) - z0) // C)) + 1):
            for cx in range(max(0, int((min(xs) - x0) // C)), min(W - 1, int((max(xs) - x0) // C)) + 1):
                fb.setdefault(cx + cz * W, []).append(fi)
    wb = {}
    for wi, s in enumerate(walls):
        lx, hx = min(s[0], s[2]) - BODY_R, max(s[0], s[2]) + BODY_R
        lz, hz = min(s[1], s[3]) - BODY_R, max(s[1], s[3]) + BODY_R
        for cz in range(max(0, int((lz - z0) // C) - 1), min(H - 1, int((hz - z0) // C) + 1) + 1):
            for cx in range(max(0, int((lx - x0) // C) - 1), min(W - 1, int((hx - x0) // C) + 1) + 1):
                wb.setdefault(cx + cz * W, []).append(wi)

    def floor_at(x, z, cands):
        best = None
        for fi in cands:
            v0, v1, v2, pl = floors[fi]
            if tri_xz_contains(v0, v1, v2, x, z):
                y = pl[0] * x + pl[1] * z + pl[2]
                if best is None or y > best[1]:
                    best = (fi, y)
        return best

    cell_floor = [None] * (W * H)   # None = no floor
    cell_walls = [[] for _ in range(W * H)]
    cell_yr = [None] * (W * H)
    multi = 0
    for cz in range(H):
        for cx in range(W):
            ci = cx + cz * W
            xa, za = x0 + cx * C, z0 + cz * C
            fc = fb.get(ci, [])
            hits = {}
            for sx, sz in ((0.5, 0.5), (0.1, 0.1), (0.9, 0.1), (0.1, 0.9), (0.9, 0.9)):
                r = floor_at(xa + sx * C, za + sz * C, fc)
                if r:
                    hits[r[0]] = hits.get(r[0], 0) + (3 if sx == 0.5 else 1)
            # every floor height under the 9 points of the cell (all levels): the VIS section's y ranges
            yall = []
            for sx in (0.0, 0.5, 1.0):
                for sz in (0.0, 0.5, 1.0):
                    px, pz = xa + sx * C, za + sz * C
                    for fi in fc:
                        v0, v1, v2, pl = floors[fi]
                        if tri_xz_contains(v0, v1, v2, px, pz):
                            yall.append(pl[0] * px + pl[1] * pz + pl[2])
            cell_yr[ci] = (min(yall), max(yall)) if yall else None
            if hits:
                cell_floor[ci] = max(hits, key=hits.get)
                ys = sorted(set(round(floors[k][3][0] * (xa + C / 2) + floors[k][3][1] * (za + C / 2) + floors[k][3][2]) for k in hits))
                if ys[-1] - ys[0] > 1500:
                    multi += 1
            cxm, czm = xa + C / 2, za + C / 2
            for wi in sorted(set(wb.get(ci, []))):
                s = walls[wi]
                if min(s[0], s[2]) - BODY_R <= xa + C and max(s[0], s[2]) + BODY_R >= xa and \
                        min(s[1], s[3]) - BODY_R <= za + C and max(s[1], s[3]) + BODY_R >= za and \
                        seg_dist(cxm, czm, s) <= BODY_R + C * 0.7072:
                    cell_walls[ci].append(wi)
    # keep only floor planes that a cell uses (renumbered in first-use order); walls likewise
    used_f = sorted(set(f for f in cell_floor if f is not None))
    if len(used_f) > 0xFFFE:
        raise SystemExit('more than 65534 floor planes in use')
    fmap = {f: i for i, f in enumerate(used_f)}
    used_w = sorted(set(w for l in cell_walls for w in l))
    wmap = {w: i for i, w in enumerate(used_w)}
    return dict(W=W, H=H, x0=x0, z0=z0, ymin=bmin[1], ymax=bmax[1], multi=multi,
                planes=[floors[f][3] for f in used_f], segs=[walls[w] for w in used_w],
                cells=[(None if cell_floor[i] is None else fmap[cell_floor[i]], tuple(wmap[w] for w in cell_walls[i]))
                       for i in range(W * H)],
                floors_total=len(floors), walls_total=len(walls), yr=cell_yr)


def encode_grid(g):
    lists, wl = {}, []
    combos, cidx, cells = [], {}, []
    for f, ws in g['cells']:
        if f is None:
            cells.append(0xFFFF)
            continue
        if len(ws) > 255:
            raise SystemExit('cell wall list > 255')
        if ws not in lists:
            lists[ws] = len(wl)
            wl += ws
        key = (f, len(ws), lists[ws] if ws else 0)
        if key not in cidx:
            cidx[key] = len(combos)
            combos.append(key)
        cells.append(cidx[key])
    if len(combos) >= 0xFFFF or len(wl) > 0xFFFF or len(g['segs']) > 0xFFFF:
        raise SystemExit('grid tables exceed u16')
    W, H = g['W'], g['H']
    bw, bh = (W + 7) // 8, (H + 7) // 8
    btab, bdata, bseen = [], [], {}
    for by in range(bh):
        for bx in range(bw):
            blk = [cells[x + z * W] if x < W and z < H else 0xFFFF
                   for z in range(by * 8, by * 8 + 8) for x in range(bx * 8, bx * 8 + 8)]
            if all(c == 0xFFFF for c in blk):
                btab.append(0xFFFF)
            else:   # identical blocks (open ground, water) are stored once
                t = tuple(blk)
                if t not in bseen:
                    bseen[t] = len(bdata)
                    bdata.append(blk)
                btab.append(bseen[t])
    if len(bdata) >= 0xFFFF:
        raise SystemExit('too many blocks')
    out = struct.pack('<8H', len(g['planes']), len(g['segs']), len(combos), len(wl), bw, bh, len(bdata), 0)
    out += struct.pack('<%dH' % len(btab), *btab)
    out += b'\0' * (-len(out) % 4)
    for blk in bdata:
        out += struct.pack('<64H', *blk)
    out += b''.join(struct.pack('<HHBB', c[0], c[2], c[1], 0) for c in combos)
    out += b'\0' * (-len(out) % 4)
    out += b''.join(struct.pack('<3f', *p) for p in g['planes'])
    out += b''.join(struct.pack('<6h', *[max(-32768, min(32767, int(round(v / 10)))) for v in s[:6]]) for s in g['segs'])
    out += struct.pack('<%dH' % len(wl), *wl)
    return out, dict(cells=2 * len(btab) + 128 * len(bdata), blocks=len(bdata), combos=6 * len(combos), planes=12 * len(g['planes']),
                     segments=12 * len(g['segs']), wall_list=2 * len(wl), ncombo=len(combos), nwl=len(wl))


def container(room_id, g, sections, flags):
    n = len(sections)
    off = 64 + 32 * n
    body, dirs = b'', b''
    for tag, ver, sflags, data, count, stride in sections:
        pad = -(off + len(body)) % 16
        body += b'\0' * pad
        dirs += struct.pack('<4sHHIIIIII', tag, ver, sflags, off + len(body), len(data), count, stride, 16, 0)
        body += data
    body += b'\0' * (-(off + len(body)) % 16)
    payload = dirs + body
    total = 64 + len(payload)
    hdr = struct.pack('<4sHHIIIIHHIiiffI12s', b'R4RC', 1, 64, room_id, n, total, flags, g['W'], g['H'], int(CELL),
                      int(g['x0']), int(g['z0']), g['ymin'], g['ymax'], zlib.crc32(payload) & 0xFFFFFFFF, b'\0' * 12)
    assert len(hdr) == 64
    return hdr + payload


VIS_DIV = int(os.environ.get("RC_VIS_DIV", 4))            # VIS cell = 4 x the 1 m lattice
VIS_RANGE = 24000.0    # pairs farther apart than this (cell Chebyshev distance x cell) are written visible
SHELL_RANGE = {0x100: 18750, 0x101: 18750}   # rooms with a far shell (FAR_SHELL): beyond this the world is the shell
VIS_MARGIN = float(os.environ.get("RC_VIS_MARGIN", 500))     # eye and target sample areas extend this far past their cell
VIS_SAMPLES = int(os.environ.get("RC_VIS_SAMPLES", 5))        # per axis
VIS_EYE_N, VIS_TGT_N = 3, 4
EYE_LO, EYE_HI = 300.0, 4500.0       # eye y range over a cell's floors
EYE_STEP, EYE_SPAN = 1000.0, 1500.0  # eye height bands: start every STEP, SPAN tall (one row each)
TGT_LO, TGT_HI = -500.0, 3000.0      # enemy boxes over a cell's floors
BAND_STEP, BAND_SPAN = 1000.0, float(os.environ.get("RC_BAND_SPAN", 3500))  # target height bands: start every STEP, SPAN tall (a box <= 2.5 m fits one)
LEVELS = 3             # world LOD levels 0..2: a pair is hidden only when hidden at every level


def vis_tool():
    src = os.path.join(HERE, 'vis_pvs.c')
    exe = os.path.join(tempfile.gettempdir(), 'vis_pvs-%s' % hashlib.sha256(open(src, 'rb').read()).hexdigest()[:12])
    if not os.path.exists(exe):
        subprocess.check_call(['cc', '-O2', '-pthread', '-o', exe, src, '-lm'])
    return exe


def q10(v, up):
    v = math.ceil(v / 10) if up else math.floor(v / 10)
    return max(-32768, min(32767, int(v)))


def build_vis(g, worlddir, threads, room_id):
    """VIS v2 (supersedes the v1 layout described below; eye height bands):
    header 32 B: u16 vw, vh, div, nrow, rowbytes, ntgt, range_cm, span_cm; u32 R4PW sidecar crc the occluders came
                 from; u16 ncam, eye_step_cm, eye_span_cm; 6 B zero
    cells[vw*vh] 12 B: s16 eye0 (cm), u8 neye, u8 nband, s16 band0 (cm), u16 first camera volume (0xFFFF none),
                 u16 first target volume, u16 0; eye band j = [eye0 + j*step, + span] -> camrow[first_cam + j]
    camrow u16[ncam] (padded to 4 B), rows[nrow][rowbytes].
    v1 text: camera cell -> target volume visibility over VIS_DIV x VIS_DIV blocks of the grid lattice (vis_pvs.c).
    header 16 B: u16 vw, u16 vh, u16 div, u16 nrow, u16 rowbytes, u16 ntgt, u16 range_m10 (range, 10 cm... see below),
                 u16 band_step_cm, (range_mm = u16 at 12 x 10 mm; band span = u16 at 14 is BAND_SPAN in cm)
      exact: u16 vw, vh, div, nrow, rowbytes, ntgt, u16 range_cm, u16 span_cm; the band step is 100 cm (BAND_STEP)
    cells[vw*vh] 12 B: s16 eye_lo, s16 eye_hi (cm; lo > hi = no culling from this cell), s16 band0 (cm), u8 nband,
                       u8 0, u16 row (0xFFFF: none), u16 first target volume (band k of the cell = first + k)
    rows[nrow][rowbytes]: bit t set = target volume t possibly visible (deduplicated rows).
    A box is hidden from an eye in cell A when it fits one band (band0 + k*step <= lo, hi <= that + span) of every
    cell it overlaps, all those bits are clear, and its farthest corner is within range."""
    import world_tris
    assert BAND_STEP == 1000.0
    W, H, C = g['W'], g['H'], CELL
    vw, vh = (W + VIS_DIV - 1) // VIS_DIV, (H + VIS_DIV - 1) // VIS_DIV
    rng = min(VIS_RANGE, SHELL_RANGE.get(room_id, VIS_RANGE))
    cams, tg, cinfo = [], [], []
    for vz in range(vh):
        for vx in range(vw):
            c = vx + vz * vw
            ys = [g['yr'][x + z * W] for z in range(vz * VIS_DIV, min(H, vz * VIS_DIV + VIS_DIV))
                  for x in range(vx * VIS_DIV, min(W, vx * VIS_DIV + VIS_DIV)) if g['yr'][x + z * W]]
            if ys:
                lo, hi = min(y[0] for y in ys), max(y[1] for y in ys)
                e0 = q10(lo + EYE_LO, False) * 10
                ne = max(1, int(math.ceil((hi + EYE_HI - EYE_SPAN - e0) / EYE_STEP)) + 1)
                ne = min(ne, 255)
                b0 = q10(lo + TGT_LO, False) * 10
                nb = max(1, int(math.ceil((hi + TGT_HI - BAND_SPAN - b0) / BAND_STEP)) + 1)
                nb = min(nb, 255)
                cinfo.append((e0, ne, b0, nb, len(cams), len(tg)))
                for j in range(ne):
                    cams.append((c, e0 + j * EYE_STEP, e0 + j * EYE_STEP + EYE_SPAN))
                for k in range(nb):
                    tg.append((c, b0 + k * BAND_STEP, b0 + k * BAND_STEP + BAND_SPAN))
            else:
                cinfo.append(None)
    pkg = world_tris.Pkg(worlddir)
    exe = vis_tool()
    rowb = (len(tg) + 7) // 8
    acc = bytearray(rowb * len(cams))
    ntris = []
    with tempfile.TemporaryDirectory() as td:
        for lv in range(LEVELS):
            tris = pkg.occluders(lv)
            ntris.append(len(tris))
            fi, fo = os.path.join(td, 'in%d' % lv), os.path.join(td, 'out%d' % lv)
            with open(fi, 'wb') as f:
                f.write(b'PVSI' + struct.pack('<3I5f5I', len(tris), vw, vh, g['x0'], g['z0'], C * VIS_DIV, VIS_MARGIN,
                                               rng + C * VIS_DIV * 2, VIS_SAMPLES, VIS_EYE_N, VIS_TGT_N, 1, threads))
                f.write(struct.pack('<I', len(cams)) + b''.join(struct.pack('<Iff', *c) for c in cams))
                f.write(struct.pack('<I', len(tg)) + b''.join(struct.pack('<Iff', *t) for t in tg))
                f.write(b''.join(struct.pack('<10f', *t) for t in tris))
            subprocess.check_call([exe, fi, fo])
            out = open(fo, 'rb').read()
            for i in range(len(acc)):
                acc[i] |= out[i]
    rows, ridx, cells, camrow = [], {}, b'', []
    hidden = 0
    for a in range(len(cams)):
        row = bytes(acc[a * rowb:(a + 1) * rowb])
        if row not in ridx:
            ridx[row] = len(rows)
            rows.append(row)
        camrow.append(ridx[row])
        hidden += sum(1 for t in range(len(tg)) if not (row[t >> 3] >> (t & 7)) & 1)
    for c in range(vw * vh):
        ci = cinfo[c]
        if ci is None:
            cells += struct.pack('<hBBhHHH', 0, 0, 0, 0, 0xFFFF, 0, 0)
            continue
        cells += struct.pack('<hBBhHHH', ci[0] // 10, ci[1], ci[3], ci[2] // 10, ci[4], ci[5], 0)
    if len(rows) >= 0xFFFF or len(tg) >= 0xFFFF or len(cams) >= 0xFFFF:
        raise SystemExit('too many VIS rows / targets / cameras')
    camb = struct.pack('<%dH' % len(camrow), *camrow)
    if len(camrow) & 1:
        camb += b'\0\0'
    data = struct.pack('<8HIHHH6x', vw, vh, VIS_DIV, len(rows), rowb, len(tg), int(rng) // 10, int(BAND_SPAN) // 10,
                       pkg.sidecar_crc, len(cams), int(EYE_STEP) // 10, int(EYE_SPAN) // 10)
    data += cells + camb + b''.join(rows)
    return data, dict(vw=vw, vh=vh, rows=len(rows), rowbytes=rowb, targets=len(tg), cameras=len(cams), hidden_pairs=hidden,
                      occluder_tris=ntris, range_mm=rng, bytes=len(data))


def build_occl(g, worlddir, room_id):
    """OCCL v1 (occl.py): large opaque occluders + per-camera-cell candidate lists."""
    import occl
    import world_tris
    pkg = world_tris.Pkg(worlddir)
    levels = [pkg.occluders(lv, exclude_dynamic=False) for lv in range(LEVELS)]   # runtime world_intact guards bound objects
    ws, conf = occl.winding_sign(levels[0])
    occ, ngroups = occl.extract(levels, ws)
    rng = min(VIS_RANGE, SHELL_RANGE.get(room_id, VIS_RANGE))
    data, info = occl.encode(occ, g, VIS_DIV, CELL, EYE_LO, EYE_HI, rng, pkg.sidecar_crc)
    info.update(winding=ws, winding_evidence={m: [w, round(c, 3)] for m, (w, c) in conf.items()}, plane_groups=ngroups, range_mm=rng,
                tris=[len(t) for t in levels], occluder_area_m2=round(sum(
                    math.dist(c[0], c[1]) * math.dist(c[0], c[3]) for c, _, _ in occ) / 1e6, 1))
    return data, info, occ


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--world', help='native package root: <world>/<room>/ps2-world.{re4mesh,r4pw,ids} (adds VIS)')
    ap.add_argument('--no-grid', action='store_true', help='leave the GRID section out')
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--vis', action='store_true', help='VIS v2 (cell-to-cell) instead of OCCL (default) with --world')
    ap.add_argument('rooms', nargs='+')
    a = ap.parse_args()
    rows = []
    for room in a.rooms:
        sats, das = sat_members(a.iso, room)
        if not sats:
            print(room, 'no SAT: skipped')
            continue
        idx, sat = sats[0]
        g = build_cells(sat)
        grid, gb = encode_grid(g)
        static = len(sats) == 1
        srcb = b''.join(struct.pack('<4sI32s', b'SAT\0', len(s), hashlib.sha256(s).digest()) for _, s in sats)
        nsrc = len(sats)
        rid = int(room[1:], 16)
        secs = []
        if not a.no_grid:
            secs.append((b'GRID', 1, 1 | (2 if static else 0), grid, g['W'] * g['H'], 0))
        vb = None
        wd = os.path.join(a.world, room) if a.world else None
        if wd and os.path.exists(os.path.join(wd, 'ps2-world.re4mesh')):
            for fn in ('ps2-world.re4mesh', 'ps2-world.r4pw', 'ps2-world.ids'):
                p = os.path.join(wd, fn)
                if os.path.exists(p):
                    b = open(p, 'rb').read()
                    srcb += struct.pack('<4sI32s', {'ps2-world.re4mesh': b'R4IM', 'ps2-world.r4pw': b'R4PW',
                                                    'ps2-world.ids': b'R4ID'}[fn], len(b), hashlib.sha256(b).digest())
                    nsrc += 1
            if a.vis:
                vis, vb = build_vis(g, wd, a.threads, rid)
                secs.append((b'VIS\0', 2, 0, vis, vb['vw'] * vb['vh'], 12))
            else:
                oc, vb, occ = build_occl(g, wd, rid)
                secs.append((b'OCCL', 1, 0, oc, vb['occluders'], 56))
                os.makedirs(os.path.join(a.out, room), exist_ok=True)
                with open(os.path.join(a.out, room, 'occl.json'), 'w') as f:
                    json.dump([[list(map(list, c)), h, s] for c, h, s in occ], f)
        blob = container(rid, g, [(b'SRCB', 1, 0, srcb, nsrc, 40)] + secs, 0)
        od = os.path.join(a.out, room)
        os.makedirs(od, exist_ok=True)
        with open(os.path.join(od, 'room.r4rc'), 'wb') as f:
            f.write(blob)
        sha = hashlib.sha256(blob).hexdigest()
        rep = dict(room=room, das=das, compiler=COMPILER, file_bytes=len(blob), sha256=sha, grid_bytes=len(grid),
                   grid=gb, w=g['W'], h=g['H'], origin_mm=[g['x0'], g['z0']], cell_mm=CELL, static=static,
                   sat_members=[[i, len(s), hashlib.sha256(s).hexdigest()] for i, s in sats],
                   multi_level_cells=g['multi'], floor_planes_used=len(g['planes']), floors_total=g['floors_total'],
                   walls_used=len(g['segs']), walls_total=g['walls_total'], vis=vb)
        with open(os.path.join(od, 'report.json'), 'w') as f:
            json.dump(rep, f, indent=1)
        rows.append((room, len(blob), sha, len(grid), int(static)))
        print('%s %6d B grid %6d (cells %d combos %d planes %d segs %d wl %d) static=%d multi=%d vis=%s' % (
            room, len(blob), len(grid), gb['cells'], gb['combos'], gb['planes'], gb['segments'], gb['wall_list'],
            static, g['multi'], vb and {k: vb.get(k) for k in ('bytes', 'rows', 'hidden_pairs', 'occluders', 'list_entries')}), flush=True)
    with open(os.path.join(a.out, 'MANIFEST.tsv'), 'w') as f:
        f.write('room\tbytes\tsha256\tgrid_bytes\tstatic\tcompiler\n')
        for r in rows:
            f.write('%s\t%d\t%s\t%d\t%d\t%s\n' % (r + (COMPILER,)))


if __name__ == '__main__':
    main()
