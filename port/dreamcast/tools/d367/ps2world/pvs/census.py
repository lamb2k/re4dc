#!/usr/bin/env python3
"""Meshlet-level visibility census (lane vis-census26, 2026-10-26).

usage (Windows Python with numpy):
  census.py cams <work dir> [--n 120] [--seed 1]   synthetic cameras from the caster's grounded cells -> cams.txt, cams.json
  census.py eval <work dir> [--lodpx 5]           after pvs_cast build (cells.bin) and ceil (ceil.bin) -> census.json

Cameras (SYNTHETIC, not PS2CAM logs): up to --n grounded 4 m cells (pvs_cast build, eye heights 1.0/1.7/2.4 m), eye
1.8 m above the cell's local ground at the cell centre, 2 yaws per cell (random), pitch -12 deg, 50 deg vertical FOV
4:3, near 100 mm, cull far 25 m (the game's ps2 world cull depth). Indoor = an opaque static triangle within 12 m
straight up AND at least 6 of 8 horizontal rays hit one within 15 m.
Eval, per camera (corners weighted by the cluster's LOD level, cone.py's rule: coarsest level whose error x scale x
px / lodpx <= the box's nearest depth; meshlet corners x level corners / level-0 corners):
  F   corners of meshlets whose world box meets the frustum (what the box tests keep today)
  B   of F, meshlets entirely back-facing (one-sided parts): back-face work, not visibility
  OFF of F - B, meshlets whose box meets the frustum but no triangle covers a pixel even with nothing occluding
  H   of F - B - OFF, meshlets no pixel ray reaches before a static opaque occluder: the PERFECT per-view cut (upper bound)
  Hs  of H, meshlets of static placements (a static set can cut only these)
  C   of F - B, meshlets outside the camera cell's conservative set (pvs_emit rules: dilate 1, near 3 m, dynamic and
      non-opaque kept): what a realistic cell PVS cuts
  ms = corners x 0.21 us x 1.23 (vp::transform_sched corner cost, corrected), MODELLED.
"""
import json, struct, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pvs_emit  # noqa: E402

US = 0.21 * 1.23e-3   # ms per corner, MODELLED
COTY = 1 / np.tan(np.radians(25)); COTX = COTY * 0.75; NEAR = 100.0; FAR = 25000.0


def load_tris(work):
    b = (Path(work) / 'tris.bin').read_bytes(); n = struct.unpack_from('<I', b, 0)[0]
    rec = np.frombuffer(b, dtype=[('v', '<f4', (9,)), ('inst', '<u4'), ('flags', '<u4')], count=n, offset=4)
    v = rec['v'].astype(np.float64).reshape(-1, 3, 3)
    return v, rec['inst'].astype(np.int64), rec['flags']


def ray_hits(o, d, A, E1, E2, tmax):
    p = np.cross(d, E2); det = (E1 * p).sum(1); ok = np.abs(det) > 1e-9
    inv = np.where(ok, 1 / np.where(ok, det, 1), 0); s = o - A
    u = (s * p).sum(1) * inv; q = np.cross(s, E1); w = (q @ d) * inv; t = (q * E2).sum(1) * inv
    return bool((ok & (u >= 0) & (w >= 0) & (u + w <= 1) & (t > 1) & (t < tmax)).any())


def view_of(eye, yaw, pitch):
    f = np.array([np.cos(pitch) * np.sin(yaw), np.sin(pitch), np.cos(pitch) * np.cos(yaw)])
    r = np.cross(f, [0, 1, 0]); r /= np.linalg.norm(r); u = np.cross(r, f)
    R = np.array([r, u, -f]); t = -R @ eye
    return np.hstack([R, t[:, None]]), f


def cams(work, n, seed):
    C = pvs_emit.load_cells(work)
    v, inst, flags = load_tris(work)
    occ = (flags & 5) != 0  # any opaque triangle, dynamic too (ground, indoor)
    A, E1, E2 = v[occ, 0], v[occ, 1] - v[occ, 0], v[occ, 2] - v[occ, 0]
    rng = np.random.default_rng(seed)
    cells = np.nonzero(C['has'])[0]
    pick = rng.choice(cells, min(n, len(cells)), replace=False)
    lines, info = [], []
    for c in pick:
        ix, iz = c % C['nx'], c // C['nx']
        ground = C['ylo'][c] - 1000
        eye = np.array([C['x0'] + (ix + 0.5) * C['cell'], ground + 1800, C['z0'] + (iz + 0.5) * C['cell']])
        up = ray_hits(eye, np.array([0, 1.0, 0]), A, E1, E2, 12000)
        walls = sum(ray_hits(eye, np.array([np.cos(a), 0, np.sin(a)]), A, E1, E2, 15000) for a in np.arange(8) * np.pi / 4) if up else 0
        indoor = bool(up and walls >= 6)
        for yaw in rng.uniform(0, 2 * np.pi, 2):
            V, _ = view_of(eye, yaw, np.radians(-12))
            P = [0, COTX, 0, COTY, 0, 2.0, NEAR]
            lines.append(' '.join('%.6g' % x for x in list(V.reshape(-1)) + P + [FAR]))
            info.append(dict(cell=int(c), eye=eye.round(0).tolist(), yaw=float(yaw), indoor=indoor))
    (Path(work) / 'cams.txt').write_text('\n'.join(lines) + '\n')
    (Path(work) / 'cams.json').write_text(json.dumps(info))
    print('%s: %d cameras (%d indoor)' % (work, len(info), sum(i['indoor'] for i in info)))


def evaluate(work, lodpx):
    work = Path(work)
    info = json.loads((work / 'cams.json').read_text())
    camv = [list(map(float, l.split())) for l in open(work / 'cams.txt')]
    I = pvs_emit.load_inst(work); ninst = I['n']; nb = (ninst + 7) // 8
    rows = [l.rstrip('\n').split('\t') for l in open(work / 'inst.tsv')][1:]
    cull = np.array([int(r[6]) for r in rows]); cl_of = np.zeros(ninst, np.int64)
    crows = [l.rstrip('\n').split('\t') for l in open(work / 'clusters.tsv')][1:]
    for k, r in enumerate(crows):
        cl_of[int(r[2]):int(r[2]) + int(r[3])] = k
    clo = np.array([[float(x) for x in r[5:8]] for r in crows]); chi = np.array([[float(x) for x in r[8:11]] for r in crows])
    cscale = np.array([float(r[4]) for r in crows])
    clev = [[tuple(map(float, x.split(':'))) for x in r[11:]] for r in crows]
    b = (work / 'ceil.bin').read_bytes(); m, ni = struct.unpack_from('<2I', b, 0); assert ni == ninst and m == len(info)
    raw = np.frombuffer(b, np.uint8, offset=8).reshape(m, 2, nb)
    vis = np.unpackbits(raw[:, 0], axis=1, bitorder='little')[:, :ninst].astype(bool)
    fr = np.unpackbits(raw[:, 1], axis=1, bitorder='little')[:, :ninst].astype(bool)
    v, tinst, tflags = load_tris(work)
    # on screen ignoring occlusion (pvs_cast ceil on the same triangles with no occluders: noocc/ceil.bin)
    nb2 = np.frombuffer((work / 'noocc' / 'ceil.bin').read_bytes(), np.uint8, offset=8).reshape(m, 2, nb)
    onscr = np.unpackbits(nb2[:, 0], axis=1, bitorder='little')[:, :ninst].astype(bool)
    nrm = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]); one = (tflags & 2) == 0
    Cc = pvs_emit.load_cells(str(work)); S = pvs_emit.conservative(Cc, I, 1, 3000)
    out = dict(cams=[], meta=json.loads((work / 'meta.json').read_text()))
    px = 240 * COTY
    for ci in range(m):
        cv = np.array(camv[ci]); V = cv[:12].reshape(3, 4); eye = np.array(info[ci]['eye'], float); fwd = -V[2, :3]
        # LOD ratio per cluster
        corners = np.stack([clo + (chi - clo) * np.array([(q >> a) & 1 for a in range(3)]) for q in range(8)])
        depth = np.maximum(((corners - eye) @ fwd).min(0), NEAR)
        ratio = np.ones(len(crows))
        for k, lv in enumerate(clev):
            s = cscale[k] * px / lodpx; L = len(lv) - 1
            while L and lv[L][1] * s > depth[k]:
                L -= 1
            ratio[k] = lv[L][0] / max(lv[0][0], 1)
        w = I['verts'] * ratio[cl_of]
        facing = ((nrm * (eye - v[:, 0])).sum(1) > 0) | ~one
        nface = np.bincount(tinst, weights=facing, minlength=ninst)
        back = (nface == 0) & (cull != 0) & (np.bincount(tinst, minlength=ninst) > 0)
        F = fr[ci]; B = F & back; H = F & onscr[ci] & ~vis[ci] & ~back; OFF = F & ~onscr[ci] & ~back; Hs = H & ~I['dyn']
        cell = info[ci]['cell']; Cm = F & onscr[ci] & ~back & ~S[cell]
        out['cams'].append(dict(indoor=info[ci]['indoor'], F=float(w[F].sum()), B=float(w[B].sum()), H=float(w[H].sum()),
                                Hs=float(w[Hs].sum()), OFF=float(w[OFF].sum()), C=float(w[Cm].sum()), Fdyn=float(w[F & I['dyn']].sum()),
                                nF=int(F.sum()), nH=int(H.sum()), F0=float(I['verts'][F].sum()), H0=float(I['verts'][H].sum()), C0=float(I['verts'][Cm].sum())))
    pvs_emit.emit(str(work), str(work / 'room.pvs'), 1, 3000)
    out['pvs_bytes'] = (work / 'room.pvs').stat().st_size
    cs = out['cams']
    def agg(sel):
        sel = [c for c in cs if sel(c)]
        if not sel:
            return None
        g = {k: float(np.mean([c[k] for c in sel])) for k in ('F', 'B', 'H', 'Hs', 'C', 'Fdyn', 'F0', 'H0', 'C0', 'OFF')}
        g['n'] = len(sel); g.update({k + '_ms': g[k] * US for k in ('F', 'B', 'H', 'Hs', 'C', 'OFF')})
        g['H95_ms'] = float(np.percentile([c['H'] for c in sel], 90)) * US
        return g
    out['all'] = agg(lambda c: True); out['indoor'] = agg(lambda c: c['indoor']); out['outdoor'] = agg(lambda c: not c['indoor'])
    (work / 'census.json').write_text(json.dumps(out, indent=1))
    a = out['all']
    print('%s: %d cams F %.0f corners %.2f ms | offscreen-box %.1f%% | back %.1f%% | perfect %.1f%% (%.2f ms, static %.2f) | cell %.1f%% (%.2f ms) | pvs %d B | indoor %s' % (
        work.name, a['n'], a['F'], a['F_ms'], 100 * a['OFF'] / a['F'], 100 * a['B'] / a['F'], 100 * a['H'] / a['F'], a['H_ms'], a['Hs_ms'],
        100 * a['C'] / a['F'], a['C_ms'], out['pvs_bytes'], out['indoor'] and '%d cams perfect %.1f%%' % (out['indoor']['n'], 100 * out['indoor']['H'] / out['indoor']['F'])))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'cams':
        cams(a[1], int(a[a.index('--n') + 1]) if '--n' in a else 120, int(a[a.index('--seed') + 1]) if '--seed' in a else 1)
    else:
        evaluate(a[1], float(a[a.index('--lodpx') + 1]) if '--lodpx' in a else 5.0)
