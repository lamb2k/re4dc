#!/usr/bin/env python3
"""edemo18 room grid builder: GC SAT collision -> 2D Dreamcast room grid (EDGR v1).

Input: the room's SAT (cSatMgr collision: floor / slope / wall triangles in that order), parsed by
convert_sat.parse_sat. Output (private dir, never git): grid.bin + report.json + diff.png.

Grid (cell = CELL mm, x/z):
  cell u8 floor   index into the floor-plane table (floor + slope triangles), 0xFF = no floor
  cell u8 nwall   wall segments touching the cell (expanded by the body radius)
  cell u16 wofs   offset into the u16 wall-index list
  plane  f32 a, c, d   y = a*x + c*z + d   (exact triangle plane: foot height is exact, not sampled)
  segment s16 x0, z0, x1, z1, ymin, ymax  (cm): the wall triangle's XZ footprint (longest edge)

Walkable diff: on a 100 mm lattice, the polygon reference (highest floor triangle under the point,
no wall triangle within BODY_R in XZ inside [floor + STEP, floor + HEIGHT]) vs the grid query (the
cell's plane must contain the point's floor, the same wall test against the cell's segments).
"""
import argparse
import json
import math
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import convert_sat  # noqa: E402
import pathlib  # noqa: E402

BODY_R = 300.0
STEP = 300.0
HEIGHT = 1600.0


def tri_xz_contains(a, b, c, x, z):
    def s(p, q):
        return (q[0] - p[0]) * (z - p[2]) - (q[2] - p[2]) * (x - p[0])
    d1, d2, d3 = s(a, b), s(b, c), s(c, a)
    neg = d1 < 0 or d2 < 0 or d3 < 0
    pos = d1 > 0 or d2 > 0 or d3 > 0
    return not (neg and pos)


def plane_of(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    if abs(ny) < 1e-9:
        return None
    pa, pc = -nx / ny, -nz / ny
    return (pa, pc, a[1] - pa * a[0] - pc * a[2])


def seg_dist(px, pz, s):
    x0, z0, x1, z1 = s[:4]
    dx, dz = x1 - x0, z1 - z0
    L = dx * dx + dz * dz
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - x0) * dx + (pz - z0) * dz) / L))
    return math.hypot(px - (x0 + t * dx), pz - (z0 + t * dz))


def png(path, w, h, rows):
    raw = b''.join(b'\0' + bytes(r) for r in rows)
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xFFFFFFFF)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sat')
    ap.add_argument('--out', required=True)
    ap.add_argument('--cell', type=float, default=1000.0)
    ap.add_argument('--lattice', type=float, default=100.0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    d = convert_sat.parse_sat(pathlib.Path(a.sat), source_scale=1.0)   # source units = mm
    V = d['vertices']
    P = d['polygons']
    nfl = d['floor_count'] + d['slope_count']
    floors = []
    for i in range(nfl):
        v0, v1, v2 = (V[k] for k in P[i][:3])
        pl = plane_of(v0, v1, v2)
        if pl:
            floors.append((v0, v1, v2, pl, i))
    walls = []
    for i in range(nfl, len(P)):
        v0, v1, v2 = (V[k] for k in P[i][:3])
        pts = [v0, v1, v2]
        best = max(((p, q) for p in pts for q in pts), key=lambda e: (e[0][0] - e[1][0]) ** 2 + (e[0][2] - e[1][2]) ** 2)
        ys = [p[1] for p in pts]
        walls.append((best[0][0], best[0][2], best[1][0], best[1][2], min(ys), max(ys), i))
    bmin, bmax = d['bounds_min'], d['bounds_max']
    C = a.cell
    x0, z0 = math.floor(bmin[0] / C) * C, math.floor(bmin[2] / C) * C
    W = int(math.ceil((bmax[0] - x0) / C))
    H = int(math.ceil((bmax[2] - z0) / C))

    def floor_at(x, z, cands):
        best = None
        for fi in cands:
            v0, v1, v2, pl, _ = floors[fi]
            if tri_xz_contains(v0, v1, v2, x, z):
                y = pl[0] * x + pl[1] * z + pl[2]
                if best is None or y > best[1]:
                    best = (fi, y)
        return best

    def wall_blocked(x, z, y, cands):
        for wi in cands:
            s = walls[wi]
            if s[5] < y + STEP or s[4] > y + HEIGHT:
                continue
            if seg_dist(x, z, s) < BODY_R:
                return True
        return False

    # per-cell candidates (bbox overlap), floor choice and wall lists
    cell_floor = [0xFF] * (W * H)
    cell_walls = [[] for _ in range(W * H)]
    multi = 0
    allf = list(range(len(floors)))
    fl_bb = [(min(f[0][0], f[1][0], f[2][0]), max(f[0][0], f[1][0], f[2][0]), min(f[0][2], f[1][2], f[2][2]), max(f[0][2], f[1][2], f[2][2])) for f in floors]
    for cz in range(H):
        for cx in range(W):
            xa, za = x0 + cx * C, z0 + cz * C
            fc = [i for i in allf if fl_bb[i][1] >= xa and fl_bb[i][0] <= xa + C and fl_bb[i][3] >= za and fl_bb[i][2] <= za + C]
            hits = {}
            for sx, sz in ((0.5, 0.5), (0.1, 0.1), (0.9, 0.1), (0.1, 0.9), (0.9, 0.9)):
                r = floor_at(xa + sx * C, za + sz * C, fc)
                if r:
                    hits[r[0]] = hits.get(r[0], 0) + (3 if sx == 0.5 else 1)
            if hits:
                cell_floor[cx + cz * W] = max(hits, key=hits.get)
                ys = sorted(set(round(floors[k][3][0] * (xa + C / 2) + floors[k][3][1] * (za + C / 2) + floors[k][3][2]) for k in hits))
                if ys[-1] - ys[0] > 1500:
                    multi += 1
            for wi, s in enumerate(walls):
                if min(s[0], s[2]) - BODY_R <= xa + C and max(s[0], s[2]) + BODY_R >= xa and min(s[1], s[3]) - BODY_R <= za + C and max(s[1], s[3]) + BODY_R >= za:
                    # exact: segment within BODY_R of the cell rectangle
                    cxm, czm = xa + C / 2, za + C / 2
                    if seg_dist(cxm, czm, s) <= BODY_R + C * 0.7072:
                        cell_walls[cx + cz * W].append(wi)
    if len(floors) > 255:
        raise SystemExit('more than 255 floor planes: widen the cell floor field')
    # encode
    wl = []
    cells = bytearray()
    for i in range(W * H):
        if len(cell_walls[i]) > 255:
            raise SystemExit('cell wall list > 255')
        cells += struct.pack('<BBH', cell_floor[i], len(cell_walls[i]), len(wl))
        wl += cell_walls[i]
    if len(wl) > 65535:
        raise SystemExit('wall list > 65535')
    planes = b''.join(struct.pack('<3f', *f[3]) for f in floors)
    segs = b''.join(struct.pack('<6h', *[max(-32768, min(32767, int(round(v / 10)))) for v in s[:6]]) for s in walls)
    wlb = struct.pack(f'<{len(wl)}H', *wl)
    hdr = struct.pack('<4sHHffHHHH', b'EDGR', W, H, x0, z0, int(C), len(floors), len(walls), 0)
    blob = hdr + cells + planes + segs + wlb
    with open(os.path.join(a.out, 'grid.bin'), 'wb') as f:
        f.write(blob)

    # walkable diff on the lattice
    L = a.lattice
    NX, NZ = int((bmax[0] - x0) / L), int((bmax[2] - z0) / L)
    stats = dict(both=0, poly_only=0, grid_only=0, neither=0, height_err_max=0.0, height_err_sum=0.0, hn=0)
    rows = []
    for jz in range(NZ):
        row = []
        z = z0 + (jz + 0.5) * L
        for jx in range(NX):
            x = x0 + (jx + 0.5) * L
            cx, cz = int((x - x0) / C), int((z - z0) / C)
            ci = cx + cz * W
            # polygon reference: all floors, all walls near
            r = floor_at(x, z, [i for i in allf if fl_bb[i][0] <= x <= fl_bb[i][1] and fl_bb[i][2] <= z <= fl_bb[i][3]])
            pw = bool(r) and not wall_blocked(x, z, r[1], [w for w in range(len(walls)) if min(walls[w][0], walls[w][2]) - BODY_R <= x <= max(walls[w][0], walls[w][2]) + BODY_R and min(walls[w][1], walls[w][3]) - BODY_R <= z <= max(walls[w][1], walls[w][3]) + BODY_R])
            gw = False
            if cell_floor[ci] != 0xFF:
                pl = floors[cell_floor[ci]][3]
                gy = pl[0] * x + pl[1] * z + pl[2]
                gw = not wall_blocked(x, z, gy, cell_walls[ci])
                if r and pw and gw:
                    e = abs(gy - r[1])
                    stats['height_err_max'] = max(stats['height_err_max'], e)
                    stats['height_err_sum'] += e
                    stats['hn'] += 1
            k = 'both' if pw and gw else 'poly_only' if pw else 'grid_only' if gw else 'neither'
            stats[k] += 1
            row += {'both': (170, 170, 170), 'poly_only': (220, 30, 30), 'grid_only': (30, 80, 230), 'neither': (20, 20, 20)}[k]
        rows.append(row)
    png(os.path.join(a.out, 'diff.png'), NX, NZ, rows[::-1])
    cellA = L * L / 1e6
    rep = dict(source=os.path.basename(a.sat), cell_mm=C, grid=[W, H], origin_mm=[x0, z0],
               floor_planes=len(floors), wall_segments=len(walls), wall_list_entries=len(wl),
               bytes=dict(total=len(blob), cells=len(cells), planes=len(planes), segments=len(segs), wall_list=len(wlb)),
               multi_level_cells=multi,
               walkable_m2=dict(polygon=(stats['both'] + stats['poly_only']) * cellA, grid=(stats['both'] + stats['grid_only']) * cellA,
                                agree=stats['both'] * cellA, polygon_only=stats['poly_only'] * cellA, grid_only=stats['grid_only'] * cellA),
               height_err_mm=dict(max=stats['height_err_max'], mean=stats['height_err_sum'] / max(1, stats['hn'])),
               body=dict(radius=BODY_R, step=STEP, height=HEIGHT), lattice_mm=L)
    with open(os.path.join(a.out, 'report.json'), 'w') as f:
        json.dump(rep, f, indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == '__main__':
    main()
