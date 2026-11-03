#!/usr/bin/env python3
"""roomscan (lane roomscan, 2026-11-03; user: "detail where it's warranted to maintain target fps"): a standing per-room
world-draw scan and planner. PREDICTED numbers only (a calibrated cost model, not hw-model or console ms).

  roomscan.py scan  <room> <world dir> [--warp warp.txt] [--bound run-output.txt] [--other-ms N] [--out plan.json]
  roomscan.py apply <plan.json> <world dir> <out dir>        (writes the planned ps2-world.re4mesh; r4pw/ids copied)

<world dir> holds ps2-world.re4mesh / .r4pw / .ids (a converter output or a shipped package).

Model (bakepredict calibration on the bakeall pilot, hw-model function tables; about +-1 ms per room):
  world ms = 0.0045 x placements + 0.005 x bound placements + 0.367 x package kvtx + 0.638 x bound-source kvtx
  The view replay mirrors native_static.cpp: cluster box frustum + far cull, LOD level = coarsest with error*K <= depth-r.
Budget: 33.3 ms per drawn frame (30 fps) minus the room's non-world cost (--other-ms: hw-model total minus the scenery
area, default 30.0) = the world budget per view.
Planner, per 8 m cell, look-preserving first:
  lod   the room's converter recipe with --lod-cluster 3000 --lod-min-gain 0.8 --lod-floor 60 (the lod27 set; chosen
        per room outside this tool when its scan predicts a gain and the heap fits)
  dec1  the cell's clusters switch to LOD level 1 (about half the triangles or fewer) from 8 m: the level error is
        capped at 8 m / K, so full detail stays inside 8 m of the camera wherever it is
  dec2  dec1 + level 2 (about a quarter) from 12 m and level 3 from 16 m
  Decimation only where a view is over budget, the costliest far cells first, never on a placement bound to a live
  scroll object (ids < 250 bound in the census log), visual mesh only (collision is not here). Only clusters that have
  coarser levels can change: build the room with the lod27 LOD settings first for more of them.
apply rewrites only the level records' error values and the body CRC: same file size, so the world
arena layout is unchanged; every bound sidecar must then be regenerated (bakeall/post_room.sh) for the new mesh crc."""
import argparse, json, math, os, re, struct, sys, zlib
import numpy as np

CELL = 8000.0
LODK = 150.0
FAR = 40000.0
NEAR = 100.0
HFOV, VFOV = math.radians(72) / 2, math.radians(56) / 2
A_PL, A_DYN, C_PKG, C_SRC = 0.0045, 0.005, 0.367, 0.638
FRAME_MS = 33.3
CAPS = {1: (8000.0,), 2: (8000.0, 12000.0, 16000.0)}   # dec option -> switch distance of levels 1, 2, 3
LIVE = set()          # scroll ids bound to a live object in this room (census PS2PART bind): never decimated
CLUSTER = np.dtype([('b', '<u2', 6), ('fl', '<u4'), ('lc', '<u4')])


def read_world(d):
    m = bytearray(open(os.path.join(d, 'ps2-world.re4mesh'), 'rb').read())
    h = struct.unpack_from('<4s19I', m)
    ncl, nlv, oplod, ocl, olv = struct.unpack_from('<5I', m, 80)
    meshes = [struct.unpack_from('<HBBHHIII12f', m, h[10] + 68 * i) for i in range(h[4])]
    plod = [struct.unpack_from('<II', m, oplod + 8 * i) for i in range(h[5])]
    cl = np.frombuffer(bytes(m), dtype=CLUSTER, count=ncl, offset=ocl)
    lv = np.frombuffer(bytes(m), dtype=np.dtype([('fm', '<u4'), ('mc', '<u4'), ('err', '<f4')]), count=nlv, offset=olv)
    ml = np.frombuffer(bytes(m), dtype=np.dtype([('fv', '<u4'), ('fs', '<u4'), ('sb', '<u4'), ('vc', '<u2'), ('sc', '<u2'),
                                                 ('b', '<u2', 6)]), count=h[6], offset=h[12])
    w = open(os.path.join(d, 'ps2-world.r4pw'), 'rb').read()
    _, _, npl, nparts, _, _, _, _ = struct.unpack_from('<4s7I', w)
    pl = [struct.unpack_from('<HH12f', w, 32 + 16 * nparts + 52 * i) for i in range(npl)]
    ip = os.path.join(d, 'ps2-world.ids')
    ids = open(ip, 'rb').read() if os.path.exists(ip) else b''
    rows, cache = [], {}
    for pi, (mi, gi, *aff) in enumerate(pl):
        A = np.array(aff, dtype=np.float64).reshape(3, 4)
        me = meshes[mi]
        lo, st = np.array(me[8:11]), np.array(me[11:14])
        rid = ids[16 + gi] if 16 + gi < len(ids) else 255
        for p in range(me[6], me[6] + me[7]):
            fc, cc = plod[p]
            for c in range(fc, fc + cc):
                b = cl[c]['b'].astype(np.float64)
                bl, bh = lo + st * b[:3], lo + st * b[3:]
                ctr = A[:, :3] @ ((bl + bh) / 2) + A[:, 3]
                half = np.abs(A[:, :3]) @ ((bh - bl) / 2)
                if c not in cache:
                    levels = []
                    for k in range(int(cl[c]['lc'])):
                        L = lv[cl[c]['fl'] + k]
                        lets = ml[L['fm']:L['fm'] + L['mc']]
                        levels.append((float(L['err']), int(lets['vc'].sum())))
                    cache[c] = levels
                rows.append(dict(c=c, pl=pi, ctr=ctr, half=half, rad=float(np.linalg.norm(half)), levels=cache[c], rid=rid,
                                 cell='%d,%d' % (math.floor(ctr[0] / CELL), math.floor(ctr[2] / CELL))))
    return dict(mesh=m, h=h, ocl=ocl, cl=cl, rows=rows, npl=len(pl), ids=ids, pl=pl)


def cameras(rows, warp=None, n=8):
    cams = []
    if warp:
        pos = ang = None
        for line in open(warp):
            t = line.split()
            if t and t[0] == 'pos':
                pos = np.array([float(x) for x in t[1:4]])
            if t and t[0] == 'ang':
                ang = float(t[1])
        if pos is not None:
            cams.append(('warp', pos, ang))
    # sampled positions: floor proxies of the densest cells, spread by farthest-point sampling
    ctr = np.array([r['ctr'] for r in rows]); lo = ctr - np.array([r['half'] for r in rows])
    keys = np.floor(ctr[:, [0, 2]] / CELL).astype(int)
    uniq, cnt = np.unique(keys, axis=0, return_counts=True)
    cand = []
    for k in uniq[cnt >= 2]:
        sel = (keys == k).all(1)
        cand.append(np.array([(k[0] + .5) * CELL, lo[sel, 1].min(), (k[1] + .5) * CELL]))
    chosen = [c[1] for c in cams] or ([cand[int(np.argmax([cnt[i] for i in range(len(cand))]))]] if cand else [])
    while cand and len(chosen) < n + len(cams):
        d = [min(np.linalg.norm((c - x)[[0, 2]]) for x in chosen) for c in cand]
        chosen.append(cand[int(np.argmax(d))])
    for p in chosen[len(cams):]:
        cams.append(('sample', p, None))
    return cams


def view(rows, eye, yaw, shift=None):
    """per-cell [package vtx, bound-source vtx], placements seen, and the world ms of one view."""
    f = np.array([math.sin(yaw), 0.0, math.cos(yaw)]); r_ = np.array([math.cos(yaw), 0.0, -math.sin(yaw)])
    t, tv = math.tan(HFOV), math.tan(VFOV)
    cells = {}
    for r in rows:
        d = r['ctr'] - eye
        z = d @ f; rad = r['rad']
        if z + rad < NEAR or z - rad > FAR or abs(d @ r_) - rad > max(z, 0) * t or abs(d[1]) - rad > max(z, 0) * tv:
            continue
        levels = r['levels']
        s = shift.get(r['cell'], 0) if shift else 0
        if s and r['rid'] not in LIVE:
            levels = capped(levels, s)
        depth = max(z - rad, NEAR)
        k = len(levels) - 1
        while k and levels[k][0] * LODK > depth:
            k -= 1
        while k and levels[k][1] == 0:
            k -= 1
        cv = cells.setdefault(r['cell'], [0, 0])
        cv[1 if r.get('src') else 0] += levels[k][1]
    return cells


def capped(levels, s):
    out = list(levels)
    for i, d in enumerate(CAPS[s], 1):
        if i < len(out):
            out[i] = (min(out[i][0], d / LODK), out[i][1])
    for i in range(len(out) - 2, 0, -1):          # keep errors non-decreasing
        out[i] = (min(out[i][0], out[i + 1][0]), out[i][1])
    return out


def cell_ms(cv):
    return (C_PKG * cv[0] + C_SRC * cv[1]) / 1000.0


def scan(a):
    W = read_world(a.world)
    rows = W['rows']
    bound = set()
    if a.bound and os.path.exists(a.bound):
        bound = set(int(x, 16) for x in re.findall(r'PS2PART bind id=([0-9a-f]+)', open(a.bound, errors='replace').read()))
    LIVE.clear(); LIVE.update(i for i in bound if i < 250)
    live = sorted(set(r['cell'] for r in rows if r['rid'] in LIVE))   # cells holding a live object (their other rows may change)
    ndyn = sum(1 for mi, gi, *_ in W['pl'] if 16 + gi < len(W['ids']) and W['ids'][16 + gi] < 250)
    fee = A_PL * W['npl'] + A_DYN * ndyn
    cams = cameras(rows, a.warp)
    views = []
    for kind, pos, ang in cams:
        eye0 = pos + np.array([0, 1600.0, 0])
        for yw in ([ang] if ang is not None else [0, math.pi / 2, math.pi, -math.pi / 2]):
            views.append(dict(kind=kind, eye=(eye0 - 2000.0 * np.array([math.sin(yw), 0, math.cos(yw)])).tolist(), yaw=yw))
    budget = max(FRAME_MS - a.other_ms, 0.0)
    eyes = np.array([v['eye'] for v in views])
    centre = {}
    for r in rows:
        centre.setdefault(r['cell'], []).append(r['ctr'])
    dist = {k: float(min(np.linalg.norm((eyes - np.mean(v, 0))[:, [0, 2]], axis=1))) for k, v in centre.items()}
    shift = {}

    def evaluate(sh):
        out = []
        for v in views:
            cells = view(rows, np.array(v['eye']), v['yaw'], sh)
            out.append((fee + sum(cell_ms(c) for c in cells.values()), cells))
        return out
    before = evaluate({})
    # far cells first, only cells some view draws, never near a camera or holding a live object
    base_cell = {}
    for ms, cells in before:
        for k, cv in cells.items():
            base_cell[k] = base_cell.get(k, 0.0) + cell_ms(cv)
    order = sorted(base_cell, key=lambda k: -base_cell[k])
    for level in (1, 2):
        for k in order:
            cur = evaluate(shift)
            if all(ms <= budget for ms, _ in cur):
                break
            trial = dict(shift); trial[k] = level
            new = evaluate(trial)
            if sum(ms for ms, _ in new) < sum(ms for ms, _ in cur) - 1e-6:
                shift = trial
    after = evaluate(shift)
    per_cell = {}
    for (ms0, c0), (ms1, c1) in zip(before, after):
        for k in set(c0) | set(c1):
            e = per_cell.setdefault(k, [0.0, 0.0])
            e[0] += cell_ms(c0.get(k, [0, 0])) / len(views); e[1] += cell_ms(c1.get(k, [0, 0])) / len(views)
    plan = dict(room=a.room, world=a.world, budget_world_ms=round(budget, 2), other_ms=a.other_ms, switch_m={k: [d / 1000 for d in v] for k, v in CAPS.items()},
                fee_ms=round(fee, 2), cells=len(centre), live_cells=live, live_ids=sorted(LIVE),
                plan={k: ('dec%d' % v) for k, v in sorted(shift.items())},
                views=[dict(kind=v['kind'], eye=[round(x) for x in v['eye']], yaw=round(v['yaw'], 3),
                            before_ms=round(b[0], 2), after_ms=round(f[0], 2)) for v, b, f in zip(views, before, after)],
                hot_cells=sorted(({'cell': k, 'before_ms': round(e[0], 3), 'after_ms': round(e[1], 3), 'dist_m': round(dist.get(k, 0) / 1000, 1),
                                   'option': ('dec%d' % shift[k]) if k in shift else 'keep'} for k, e in per_cell.items()),
                                 key=lambda x: -x['before_ms'])[:20])
    b = [v['before_ms'] for v in plan['views']]; f = [v['after_ms'] for v in plan['views']]
    plan['summary'] = dict(mean_before=round(float(np.mean(b)), 2), mean_after=round(float(np.mean(f)), 2),
                           worst_before=round(max(b), 2), worst_after=round(max(f), 2), cells_decimated=len(shift),
                           mesh_bytes_delta=0)
    out = a.out or '%s-plan.json' % a.room
    json.dump(plan, open(out, 'w'), indent=1)
    print(json.dumps(dict(room=a.room, **plan['summary'], budget=plan['budget_world_ms'], cells=plan['cells'])))


def apply(a):
    plan = json.load(open(a.plan))
    W = read_world(a.world)
    m = W['mesh']
    shift = {k: int(v[3:]) for k, v in plan['plan'].items()}
    LIVE.clear(); LIVE.update(plan.get('live_ids', []))
    done = set()
    olv = struct.unpack_from('<5I', m, 80)[4]
    for r in W['rows']:
        s = shift.get(r['cell'], 0)
        if not s or r['rid'] in LIVE or r['c'] in done:
            continue
        done.add(r['c'])
        fl, lc = struct.unpack_from('<II', m, W['ocl'] + 20 * r['c'] + 12)
        new = capped(r['levels'], s)
        for i in range(1, lc):
            struct.pack_into('<f', m, olv + 12 * (fl + i) + 8, new[i][0])
    struct.pack_into('<I', m, 12, zlib.crc32(bytes(m[80:])) & 0xffffffff)
    os.makedirs(a.out, exist_ok=True)
    open(os.path.join(a.out, 'ps2-world.re4mesh'), 'wb').write(bytes(m))
    for f in ('ps2-world.r4pw', 'ps2-world.ids'):
        if os.path.exists(os.path.join(a.world, f)):
            open(os.path.join(a.out, f), 'wb').write(open(os.path.join(a.world, f), 'rb').read())
    print('applied %s: %d clusters capped, mesh %d bytes (unchanged size)' % (plan['room'], len(done), len(m)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('scan'); s.add_argument('room'); s.add_argument('world'); s.add_argument('--warp')
    s.add_argument('--bound'); s.add_argument('--other-ms', type=float, default=30.0); s.add_argument('--out')
    p = sub.add_parser('apply'); p.add_argument('plan'); p.add_argument('world'); p.add_argument('out')
    a = ap.parse_args()
    scan(a) if a.cmd == 'scan' else apply(a)
