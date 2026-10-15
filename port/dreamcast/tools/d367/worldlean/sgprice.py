#!/usr/bin/env python3
"""sgprice.py: price PS2_STRIP_GROUPS (.r4sg) for a room before building it (lane t2exact, 2026-10-15).

usage: sgprice.py MESH R4PW R4SG [--cams FILE | --synth ROOM --samples JSON] [--lodpx 5] [--json OUT]

MESH / R4SG are the re-ordered package and its group records from tools/ps2_strip_groups.py (the runtime reads both;
"today" is the same package without the records, which draws the same strips: only corner numbering differs).
Cameras: --cams FILE = logged game cameras (PS2_PVS "pvs 2" PS2CAM lines, as pvs/cone.py reads them: 12 view floats,
7 projection floats, cull far), or --views FILE.json = synthetic views (a list of {"eye": [x,y,z], "yaw": rad,
"pitch": rad}; 50 degree vertical FOV, 4:3, near 100, far 25 m, as roomproj.py / stripcull.py).

Runtime model, native_static.cpp (PS2_WORLD_LEAN=23 + MESH_STRIP_LEAN + MESH_DEPTH_CULL, direct path):
  cluster: lean::box_class on its grid box (0 out, 1 straddle, 2 inside every plane with a unit of margin);
           LOD level = the coarsest whose error * lod_scale <= the box's nearest depth (lod_px, Standard 5);
  meshlet (level's meshlets): cluster inside -> known (no test, no groups); else one box test
           (today group_visible, with records lean::box_mask: -1 out, else the mask of crossed planes);
  today:   every corner transformed (transform_sched), every strip walked (walk_lean): culled when all corners are
           outside one screen edge or all nearer than near / past far;
  groups:  a meshlet with a crossed plane calls lean::sg_select: each non-empty group's grid box against the crossed
           planes (screen edges, near; max of n.g + d < -1 = out); if any group is out, only the corner range lo..hi
           of the groups left is transformed and only their strips are walked.
Placement-level culls (world_out, placement inside) are not modelled: they change test counts, not corners.
Prints per-view means: T corners transformed, S strips walked, C strips culled after the transform, W corners that
feed only culled strips, calls (sg_select), tests (meshlet box tests), and the same with groups."""
import json, math, struct, sys, os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r4im_pkg import Pkg  # noqa: E402

NEAR, FAR = 100.0, 25000.0
# Strip outcodes: the screen edges and near, and the PROJECTION far (PS2MESH far=1000000), not the 25 m cull far that
# the cluster / meshlet box tests use: a strip past 25 m in a straddling meshlet is drawn (fogged), not culled.
PROJ_FAR = float(os.environ.get('SGP_PROJ_FAR', 1e6))
OC_SCALE = tuple(float(x) for x in os.environ.get('SGP_OC', '1,1').split(','))  # what-if only


def load(mesh, side, sg):
    p = Pkg(mesh, side)
    b = open(sg, 'rb').read() if sg else None
    G = struct.unpack_from('<I', b, 12)[0] if b else 0
    if b:
        assert b[:4] == b'R4SG'
        assert struct.unpack_from('<I', b, 8)[0] == p.nlet
        assert struct.unpack_from('<I', b, 16)[0] == p.mesh_crc, 'r4sg is not for this mesh'
    SG = np.frombuffer(b, '<u2', offset=32).reshape(p.nlet, G, 8).astype(np.int64) if b else None
    nlet = p.nlet
    vc = np.array([L['vc'] for L in p.lets], np.int64)
    # corners (grid u16) per meshlet, strips and entries
    c0 = np.zeros(nlet + 1, np.int64); c0[1:] = np.cumsum(vc)
    CG = np.zeros((int(c0[-1]), 3), np.float64)
    s_let = []; s_n = []; s_end = []; e_idx = []; let_s0 = np.zeros(nlet + 1, np.int64)
    for li, L in enumerate(p.lets):
        fs = p.o_strip + L['first_strip']
        if L['sc'] & 0x8000:
            off = np.frombuffer(p.m, dtype='<u2', count=L['vc'], offset=fs).astype(np.int64)
            cn = p.verts[L['first_vertex'] + off]; sb = fs + 2 * L['vc']
        else:
            cn = p.verts[L['first_vertex']:L['first_vertex'] + L['vc']]; sb = fs
        CG[c0[li]:c0[li + 1]] = cn[:, :3]
        s = sb; end = sb + L['strip_bytes']; k = 0
        while s < end:
            n = p.m[s]; e_idx.append(np.frombuffer(p.m, np.uint8, n, s + 1).astype(np.int64)); s += 1 + n
            s_let.append(li); s_n.append(n); s_end.append(s - sb); k += 1
        let_s0[li + 1] = let_s0[li] + k
    s_let = np.array(s_let, np.int64); s_n = np.array(s_n, np.int64); s_end = np.array(s_end, np.int64)
    e_idx = np.concatenate(e_idx); e0 = np.zeros(len(s_n) + 1, np.int64); e0[1:] = np.cumsum(s_n)
    s_grp = np.zeros(len(s_n), np.int64)
    if SG is not None:
        for li in range(nlet):
            a, z = let_s0[li], let_s0[li + 1]
            s_grp[a:z] = np.searchsorted(SG[li, :, 6], s_end[a:z], side='left')
        assert (s_grp < G).all()
    lbox = np.array([L['bmin'] + L['bmax'] for L in p.lets], np.float64)
    # cluster instances
    cl_part = {}
    for pi_ in range(p.npart):
        fc, cc = p.plod[pi_]
        for c in range(fc, fc + cc):
            cl_part[c] = pi_
    ci_pl = []; ci_cl = []
    for pi, pl in enumerate(p.placements):
        mesh = p.meshes[pl['mesh']]
        for k in range(mesh['part_count']):
            fc, cc = p.plod[mesh['first_part'] + k]
            for c in range(fc, fc + cc):
                ci_pl.append(pi); ci_cl.append(c)
    ci_pl = np.array(ci_pl, np.int64); ci_cl = np.array(ci_cl, np.int64)
    ci_part = np.zeros(len(ci_cl), np.int64)
    for i, c in enumerate(ci_cl):
        ci_part[i] = cl_part[c]
    cbox = np.array([p.clusters[c]['bmin'] + p.clusters[c]['bmax'] for c in ci_cl], np.float64)
    nlv = np.array([p.clusters[c]['level_count'] for c in ci_cl], np.int64)
    flv = np.array([p.clusters[c]['first_level'] for c in ci_cl], np.int64)
    LV = np.array(p.levels, np.float64)  # first_meshlet, meshlet_count, error
    WQ = np.array([p.wq(pl) for pl in p.placements]); AF = np.array([pl['affine'] for pl in p.placements])
    return dict(p=p, G=G, SG=SG, vc=vc, c0=c0, CG=CG, s_let=s_let, s_n=s_n, s_grp=s_grp, e_idx=e_idx, e0=e0,
                let_s0=let_s0, lbox=lbox, ci_part=ci_part, ci_pl=ci_pl, ci_cl=ci_cl, cbox=cbox, nlv=nlv, flv=flv, LV=LV, WQ=WQ, AF=AF)


def side_coefs(P):
    a = np.array([P[1], -P[1], -P[3], P[3]]); c = np.array([P[2] - 1, -P[2] - 1, -P[4] - 1, P[4] - 1])
    return a, c


def boxes_view(Mv, tv, box):
    """Mv (n,3,3), tv (n,3), box (n,6) grid lo/hi -> centre view coords (n,3), radius (n,3)."""
    cen = (box[:, :3] + box[:, 3:]) * 0.5; ext = (box[:, 3:] - box[:, :3]) * 0.5
    v = np.einsum('nij,nj->ni', Mv, cen) + tv
    r = np.einsum('nij,nj->ni', np.abs(Mv), ext)
    return v, r


def classify(v, r, a, c, near, far, margin):
    """box_class / box_mask: returns out (bool), crossed mask (int), inside-with-margin (bool)."""
    vx, vy, vz = v[:, 0], v[:, 1], v[:, 2]; rx, ry, rz = r[:, 0], r[:, 1], r[:, 2]
    out = (-vz + rz < near) | (-vz - rz > far)
    mask = np.zeros(len(v), np.int64); ins = (-vz - rz >= near + 1.0) & (-vz + rz <= far - 1.0)
    for k in range(4):
        vv = vx if k < 2 else vy; rr = rx if k < 2 else ry
        s = a[k] * vv + c[k] * vz; t = abs(a[k]) * rr + abs(c[k]) * rz
        out |= s + t < -0.0001
        mask |= np.where(~(s - t > 0.0), 1 << k, 0)
        ins &= s - t > 1.0
    mask |= np.where(~(-vz - rz > near), 16, 0)
    return out, mask, ins


def view_counts(D, V, P, near, far, lod_px):
    a, c = side_coefs(P)
    V3 = V[:, :3]; Vt = V[:, 3]
    WQ, AF = D['WQ'], D['AF']
    Mv_pl = np.einsum('ij,njk->nik', V3, WQ[:, :, :3]); tv_pl = np.einsum('ij,nj->ni', V3, WQ[:, :, 3]) + Vt
    mvA = np.einsum('ij,njk->nik', V3, AF[:, :, :3])
    px = max(320 * abs(P[1]), 240 * abs(P[3]))
    lod_scale = np.sqrt((mvA ** 2).sum(2).max(1)) * px / lod_px
    pl = D['ci_pl']
    v, r = boxes_view(Mv_pl[pl], tv_pl[pl], D['cbox'])
    out, _, ins = classify(v, r, a, c, near, far, True)
    vis = np.nonzero(~out)[0]
    depth = np.maximum(-v[vis, 2] - r[vis, 2], near)
    level = D['nlv'][vis] - 1
    ls = lod_scale[pl[vis]]
    for _ in range(4):
        idx = D['flv'][vis] + level
        dec = (level > 0) & (D['LV'][idx, 2] * ls > depth)
        level = level - dec
    lvi = D['flv'][vis] + level
    fm = D['LV'][lvi, 0].astype(np.int64); mc = D['LV'][lvi, 1].astype(np.int64)
    # pairs (instance, meshlet)
    rep = np.repeat(np.arange(len(vis)), mc)
    off = np.arange(mc.sum()) - np.repeat(np.cumsum(mc) - mc, mc)
    p_let = fm[rep] + off; p_inst = vis[rep]; p_known = ins[p_inst]
    p_pl = pl[p_inst]; p_part = D['ci_part'][p_inst]
    Mv = Mv_pl[p_pl]; tv = tv_pl[p_pl]
    lv_, lr_ = boxes_view(Mv, tv, D['lbox'][p_let])
    lout, lmask, _ = classify(lv_, lr_, a, c, near, far, False)
    lout &= ~p_known; lmask = np.where(p_known, 0, lmask)
    tests = int((~p_known).sum())
    keep = np.nonzero(~lout)[0]
    k_let = p_let[keep]; k_pl = p_pl[keep]; k_mask = lmask[keep]; k_part = p_part[keep]
    vc = D['vc'][k_let]
    T0 = int(vc.sum())
    # corners -> view -> outcodes
    crep = np.repeat(np.arange(len(keep)), vc)
    coff = np.arange(vc.sum()) - np.repeat(np.cumsum(vc) - vc, vc)
    cg = D['CG'][D['c0'][k_let][crep] + coff]
    cv = np.einsum('nij,nj->ni', Mv_pl[k_pl][crep], cg) + tv_pl[k_pl][crep]
    vx, vy, vz = cv[:, 0], cv[:, 1], cv[:, 2]
    oc = np.zeros(len(cv), np.int64)
    gx, gy = OC_SCALE
    for k in range(4):
        vv = vx if k < 2 else vy
        oc |= np.where(a[k] * vv + c[k] * vz * (gx if k < 2 else gy) < 0, 1 << k, 0)
    oc |= np.where(-vz < near, 16, 0) | np.where(-vz > PROJ_FAR, 32, 0)
    pc0 = np.zeros(len(keep) + 1, np.int64); pc0[1:] = np.cumsum(vc)
    # strips of kept pairs
    ns = D['let_s0'][k_let + 1] - D['let_s0'][k_let]
    srep = np.repeat(np.arange(len(keep)), ns)
    sid = np.repeat(D['let_s0'][k_let], ns) + np.arange(ns.sum()) - np.repeat(np.cumsum(ns) - ns, ns)
    sn = D['s_n'][sid]
    erep = np.repeat(np.arange(len(sid)), sn)
    eid = np.repeat(D['e0'][sid], sn) + np.arange(sn.sum()) - np.repeat(np.cumsum(sn) - sn, sn)
    ecorner = pc0[srep][erep] + D['e_idx'][eid]
    eoc = oc[ecorner]
    starts = np.r_[0, np.cumsum(sn)[:-1]]
    andc = np.bitwise_and.reduceat(eoc, starts)
    culled = (andc & 0x3f) != 0  # screen edge, all near, all far
    S0 = len(sid); C0 = int(culled.sum())
    used = np.zeros(len(cv), bool); used[ecorner[~culled[erep]]] = True
    W0 = T0 - int(used.sum())
    res = dict(T0=T0, S0=S0, C0=C0, W0=W0, tests=tests, pairs=len(keep), known=int(p_known[keep].sum()))
    if D['SG'] is None:
        return res
    # groups: pairs with a crossed plane and not known call sg_select
    call = np.nonzero(k_mask != 0)[0]
    G = D['G']; rec = D['SG'][k_let[call]]  # (n,G,8)
    gend = rec[:, :, 6]; prev = np.concatenate([np.zeros((len(call), 1), np.int64), gend[:, :-1]], 1)
    nonempty = gend != prev
    glo = rec[:, :, 0:3].astype(np.float64); ghi = rec[:, :, 3:6].astype(np.float64)
    Mc = Mv_pl[k_pl[call]]; tc = tv_pl[k_pl[call]]
    gout = np.zeros((len(call), G), bool)
    for k in range(5):
        if k < 4:
            row = 0 if k < 2 else 1
            n = a[k] * Mc[:, row, :] + c[k] * Mc[:, 2, :]; d = a[k] * tc[:, row] + c[k] * tc[:, 2]
        else:
            n = -Mc[:, 2, :]; d = -tc[:, 2] - near
        mx = (np.maximum(n[:, None, :] * glo, n[:, None, :] * ghi)).sum(2) + d[:, None]
        crossed = ((k_mask[call] >> k) & 1).astype(bool)
        gout |= crossed[:, None] & (mx < -1.0)
    gout &= nonempty
    anycut = gout.any(1)
    on = nonempty & ~gout
    lo = np.where(on, rec[:, :, 7] & 255, 10 ** 6).min(1); hi = np.where(on, rec[:, :, 7] >> 8, -1).max(1)
    rng = np.where(on.any(1), hi - lo + 1, 0)
    T1 = T0 - int((vc[call][anycut] - rng[anycut]).sum())
    # strips walked: drop strips of cut groups in cut pairs
    pair_cut = np.zeros(len(keep), bool); pair_cut[call[anycut]] = True
    gout_full = np.zeros((len(keep), G), bool); gout_full[call] = gout
    s_out = pair_cut[srep] & gout_full[srep, D['s_grp'][sid]]
    S1 = S0 - int(s_out.sum()); C1 = C0 - int((s_out & culled).sum())
    lost = int((s_out & ~culled).sum())  # must be 0: a cut group never holds a drawn strip
    coef = len(set(zip(k_pl[call].tolist(), k_part[call].tolist())))
    res.update(coef=coef, T1=T1, S1=S1, C1=C1, calls=len(call), cut_meshlets=int(anycut.sum()), groups_cut=int(gout.sum()),
               lost=lost)
    return res


def cams_logged(path):
    out = []
    for l in open(path):
        x = list(map(float, l.split()))
        if len(x) < 20:
            continue
        V = np.array(x[:12]).reshape(3, 4); P = x[12:19]
        out.append((V, P, P[6] / (P[5] - 1), x[19]))
    return out


def cams_synth(path):
    out = []
    f = 1 / math.tan(math.radians(50) / 2)
    P = [0, f / (4 / 3), 0, f, 0, 0, 0]
    for v in json.load(open(path)):
        eye = np.array(v['eye'], float); yaw = v['yaw']; pitch = v['pitch']
        fwd = np.array([math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch)])
        right = np.cross(fwd, [0, 1, 0]); right /= np.linalg.norm(right); up = np.cross(right, fwd)
        R = np.stack([right, up, -fwd]); V = np.zeros((3, 4)); V[:, :3] = R; V[:, 3] = -R @ eye
        out.append((V, P, NEAR, FAR))
    return out


def main():
    a = sys.argv[1:]
    mesh, side, sg = a[0], a[1], (a[2] if a[2] != '-' else None)
    lod_px = float(a[a.index('--lodpx') + 1]) if '--lodpx' in a else 5.0
    cams = cams_logged(a[a.index('--cams') + 1]) if '--cams' in a else cams_synth(a[a.index('--views') + 1])
    D = load(mesh, side, sg)
    rows = [view_counts(D, V, P, near, far, lod_px) for V, P, near, far in cams]
    keys = list(rows[0].keys())
    mean = {k: float(np.mean([r[k] for r in rows])) for k in keys}
    out = dict(mesh=mesh, sg=sg, G=D['G'], nlet=D['p'].nlet, views=len(rows), lod_px=lod_px, mean=mean, rows=rows)
    if '--json' in a:
        json.dump(out, open(a[a.index('--json') + 1], 'w'))
    print(json.dumps(dict((k, v) for k, v in out.items() if k != 'rows')))


if __name__ == '__main__':
    main()
