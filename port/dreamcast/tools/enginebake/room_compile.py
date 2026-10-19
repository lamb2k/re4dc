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
                floors_total=len(floors), walls_total=len(walls))


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--out', required=True)
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
        rid = int(room[1:], 16)
        blob = container(rid, g, [(b'SRCB', 1, 0, srcb, len(sats), 40),
                                  (b'GRID', 1, 1 | (2 if static else 0), grid, g['W'] * g['H'], 0)], 0)
        od = os.path.join(a.out, room)
        os.makedirs(od, exist_ok=True)
        with open(os.path.join(od, 'room.r4rc'), 'wb') as f:
            f.write(blob)
        sha = hashlib.sha256(blob).hexdigest()
        rep = dict(room=room, das=das, compiler=COMPILER, file_bytes=len(blob), sha256=sha, grid_bytes=len(grid),
                   grid=gb, w=g['W'], h=g['H'], origin_mm=[g['x0'], g['z0']], cell_mm=CELL, static=static,
                   sat_members=[[i, len(s), hashlib.sha256(s).hexdigest()] for i, s in sats],
                   multi_level_cells=g['multi'], floor_planes_used=len(g['planes']), floors_total=g['floors_total'],
                   walls_used=len(g['segs']), walls_total=g['walls_total'])
        with open(os.path.join(od, 'report.json'), 'w') as f:
            json.dump(rep, f, indent=1)
        rows.append((room, len(blob), sha, len(grid), int(static)))
        print('%s %6d B grid %6d (cells %d combos %d planes %d segs %d wl %d) static=%d multi=%d' % (
            room, len(blob), len(grid), gb['cells'], gb['combos'], gb['planes'], gb['segments'], gb['wall_list'],
            static, g['multi']), flush=True)
    with open(os.path.join(a.out, 'MANIFEST.tsv'), 'w') as f:
        f.write('room\tbytes\tsha256\tgrid_bytes\tstatic\tcompiler\n')
        for r in rows:
            f.write('%s\t%d\t%s\t%d\t%d\t%s\n' % (r + (COMPILER,)))


if __name__ == '__main__':
    main()
