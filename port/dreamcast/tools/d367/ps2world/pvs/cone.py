#!/usr/bin/env python3
"""Back-face (normal cone) ceiling for the PS2 world path, on logged cameras (lane t2exact, 2026-10-15).

usage: cone.py <package dir> <work dir (pvs_prep + pvs_cast ceil: inst.tsv, ceil.bin)> <cams> [--sg FILE.r4sg] [--lodpx 3]

Runtime model (native_static.cpp MeshDraw): a cluster in the frustum (ceil.bin frustum bit) draws one LOD level (the
coarsest whose error * lod_scale <= box depth); each meshlet of that level whose grid box is outside a frustum plane
is skipped, else its corners are transformed (vertex_count; a straddling meshlet with strip groups transforms only the
corner range lo..hi of the groups not outside a crossed plane). Back faces: one-sided parts (cull != 0), a triangle is
back-facing when the eye is not on the side of cross(b - a, c - a) (strip parity as r4im.let_tris).
Counts per frame (corners transformed):
  T        today's transformed corners
  A        meshlets whose every triangle is back-facing (skipped whole: exact, today's unit)
  B        today's strip groups: range lo..hi of groups that are on screen AND not all back-facing (range rule)
  C<G>     orientation groups: each meshlet's triangles k-means'd by normal into G groups, corners renumbered by first
           use in group order, range rule; exact per-view condition (all triangles of the group back-facing)
  K<G>     the same groups with the runtime cone test (axis, half angle, bounding sphere; conservative)
  D<G>     orientation groups owning their corners (shared corners duplicated: more corners, no range rule)
  extra strip vertices: 2 per strip break the regrouping adds (consecutive triangles of a strip in different groups)
"""
import struct, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'interior'))
from r4im import Pkg  # noqa: E402

a = sys.argv[1:]
pkg_dir, work, cams_path = a[0], a[1], a[2]
sg_path = a[a.index('--sg') + 1] if '--sg' in a else None
lod_px = float(a[a.index('--lodpx') + 1]) if '--lodpx' in a else 3.0
GS = (4, 8)
p = Pkg(pkg_dir + '/ps2-world.re4mesh', pkg_dir + '/ps2-world.r4pw')
rows = [l.rstrip('\n').split('\t') for l in open(work + '/inst.tsv')][1:]
n = len(rows)
cams = [list(map(float, l.split())) for l in open(cams_path)]
b = open(work + '/ceil.bin', 'rb').read(); m, _ = struct.unpack_from('<2I', b, 0); nb = (n + 7) // 8
SG = None
if sg_path:
    sb = open(sg_path, 'rb').read(); G0 = struct.unpack_from('<I', sb, 12)[0]
    SG = np.frombuffer(sb, '<u2', offset=32).reshape(-1, G0, 8)
corners8 = np.array([[(q >> 0) & 1, (q >> 1) & 1, (q >> 2) & 1] for q in range(8)], float)
rng = np.random.default_rng(1)


def kmeans_normals(N, k):
    if len(N) <= k:
        return np.arange(len(N))
    c = N[rng.choice(len(N), k, replace=False)]
    for _ in range(12):
        lab = np.argmax(N @ c.T, 1)
        for j in range(k):
            s = N[lab == j].sum(0)
            if np.linalg.norm(s) > 1e-9:
                c[j] = s / np.linalg.norm(s)
    return np.argmax(N @ c.T, 1)


# per meshlet precompute (by meshlet index; world data per instance later)
let_cache = {}


def let_info(li):
    if li in let_cache:
        return let_cache[li]
    corners, tris = p.let_tris(li)
    t = np.array(tris, np.int64).reshape(-1, 3)
    # strip membership for break counting: let_tris emits strips in order; recover consecutive pairs
    L = p.lets[li]
    fs = p.o_strip + L['first_strip'] + (2 * L['vc'] if L['sc'] & 0x8000 else 0)
    end = fs + L['strip_bytes']; s = fs; pairs = []; ti = 0; nstrip = 0; sent = 0
    gend = []
    while s < end:
        k = p.m[s]; s += 1 + k; nstrip += 1; sent += k
        for j in range(k - 2):
            if j:
                pairs.append((ti - 1, ti))
            ti += 1
        gend.append(s - fs)
    info = dict(c=corners[:, :3].astype(np.float64), t=t, pairs=np.array(pairs, np.int64).reshape(-1, 2), nstrip=nstrip,
                sent=sent, tri_strip_end=None)
    # triangle -> strip byte end (to map today's groups: a group = strips up to its byte end)
    ends = []; s = fs
    while s < end:
        k = p.m[s]; s += 1 + k
        ends += [s - fs] * (k - 2)
    info['tend'] = np.array(ends, np.int64)
    let_cache[li] = info
    return info


def range_count(groups_on, glo, ghi):
    if not groups_on.any():
        return 0
    return int(ghi[groups_on].max() - glo[groups_on].min() + 1)


tot = dict(T=0, A=0, B=0)
for G in GS:
    for kname in ('C', 'K', 'D', 'Dall', 'DK', 'U', 'UK'):
        tot['%s%d' % (kname, G)] = 0
    tot['xs%d' % G] = 0
tot['sent'] = 0; tot['nlet'] = 0; tot['E'] = 0; tot['lv'] = np.zeros(4)
group_cache = {}
for ci in range(m):
    cam = cams[ci]; V = np.array(cam[:12]).reshape(3, 4); P = cam[12:19]; near = P[6] / (P[5] - 1); cfar = cam[19]
    eye = -np.linalg.solve(V[:, :3], V[:, 3])
    px = max(320 * abs(P[1]), 240 * abs(P[3]))
    fr = np.unpackbits(np.frombuffer(b, np.uint8, nb, 8 + ci * 2 * nb + nb), bitorder='little')[:n].astype(bool)

    def box_state(Mw, lo, hi):
        """-1 outside one plane, 0 inside all, 1 straddles (box corners in view space)."""
        pts = lo + corners8 * (hi - lo); w = pts @ Mw[:, :3].T + Mw[:, 3]; v = w @ V[:, :3].T + V[:, 3]; d = -v[:, 2]
        cx = P[1] * v[:, 0] + P[2] * v[:, 2]; cy = P[3] * v[:, 1] + P[4] * v[:, 2]
        tests = [cx < -d, cx > d, cy < -d, cy > d, d < near, d > cfar]
        if any(t.all() for t in tests):
            return -1
        return 1 if any(t.any() for t in tests) else 0

    for i in np.nonzero(fr)[0]:
        r = rows[i]; pi = int(r[1]); part = int(r[3]); c = int(r[4]); cull = int(r[6])
        M = np.array([float(x) for x in r[17:29]]).reshape(3, 4)
        g0 = np.array([float(x) for x in r[29:32]]); g1 = np.array([float(x) for x in r[32:35]])
        cl = p.clusters[c]
        mvq = V[:, :3] @ M[:, :3]; tq = V[:, :3] @ M[:, 3] + V[:, 3]
        cen = (g0 + g1) / 2; ext = (g1 - g0) / 2
        depth = -(mvq[2] @ cen + tq[2]) - np.abs(mvq[2]) @ ext
        depth = max(depth, near)
        A = p.placements[pi]['affine']; mv = V[:, :3] @ A[:, :3]
        lod_scale = np.sqrt((mv ** 2).sum(1).max()) * px / lod_px
        level = cl['level_count'] - 1
        while level and p.levels[cl['first_level'] + level][2] * lod_scale > depth:
            level -= 1
        tot['lv'][min(level, 3)] += 1
        fm, mc, _ = p.levels[cl['first_level'] + level]
        for li in range(fm, fm + mc):
            L = p.lets[li]
            st = box_state(M, np.array(L['bmin'], float), np.array(L['bmax'], float))
            if st < 0:
                continue
            info = let_info(li); vc = L['vc']; t = info['t']
            Wc = info['c'] @ M[:, :3].T + M[:, 3]
            Tw = Wc[t]
            nrm = np.cross(Tw[:, 1] - Tw[:, 0], Tw[:, 2] - Tw[:, 0])
            back = ((eye - Tw[:, 0]) * nrm).sum(1) <= 0 if cull != 0 else np.zeros(len(t), bool)
            # today's groups (strip groups) on screen
            if SG is not None:
                rec = SG[li]; ge = rec[:, 6].astype(np.int64); glo = (rec[:, 7] & 255).astype(np.int64); ghi = (rec[:, 7] >> 8).astype(np.int64)
                prev = np.concatenate([[0], ge[:-1]]); nonempty = ge != prev
                on = nonempty.copy()
                if st == 1:
                    for gi in range(len(ge)):
                        if nonempty[gi] and box_state(M, rec[gi, 0:3].astype(float), rec[gi, 3:6].astype(float)) < 0:
                            on[gi] = False
                tg = np.searchsorted(ge, info['tend'], side='left')  # triangle -> today's group
                Tn = range_count(on, glo, ghi) if (st == 1 and not on[nonempty].all()) else vc
                allback = np.array([nonempty[gi] and back[tg == gi].all() if (tg == gi).any() else False for gi in range(len(ge))])
                onb = on & ~allback
                Bn = range_count(onb, glo, ghi) if onb.any() else 0
                Bn = min(Bn, Tn)
            else:
                Tn = vc; Bn = 0 if back.all() else vc
            tot['T'] += Tn; tot['A'] += Tn if back.all() else 0; tot['B'] += Tn - Bn
            tot['sent'] += info['sent']; tot['nlet'] += 1
            used = np.zeros(vc, bool); used[t[~back].reshape(-1)] = True; tot['E'] += vc - int(used.sum())
            # orientation groups (computed once per meshlet; normals in model space = world up to the placement's
            # rotation: k-means in world space of this instance)
            nn = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
            for G in GS:
                key = (li, i, G)
                if key not in group_cache:
                    lab = kmeans_normals(nn, G)
                    order = np.argsort(lab, kind='stable')
                    first = {}
                    for ti_ in order:
                        for k in t[ti_]:
                            if k not in first:
                                first[k] = len(first)
                    glo2 = np.full(G, 10 ** 9); ghi2 = np.full(G, -1); own = np.zeros(G, np.int64)
                    for gi in range(G):
                        sel = lab == gi
                        if sel.any():
                            ks = np.unique(t[sel]); nk = np.array([first[k] for k in ks])
                            glo2[gi] = nk.min(); ghi2[gi] = nk.max(); own[gi] = len(ks)
                    # cone per group (world): axis, cos/sin of half angle, sphere
                    cone = []
                    for gi in range(G):
                        sel = lab == gi
                        if not sel.any() or cull == 0:
                            cone.append(None); continue
                        ax = nn[sel].sum(0); ax /= max(np.linalg.norm(ax), 1e-12)
                        ca = (nn[sel] @ ax).min()
                        pts = Tw[sel].reshape(-1, 3); cc = (pts.min(0) + pts.max(0)) / 2; rr = np.linalg.norm(pts - cc, axis=1).max()
                        cone.append((ax, ca, cc, rr))
                    br = len(info['pairs']) and int((lab[info['pairs'][:, 0]] != lab[info['pairs'][:, 1]]).sum())
                    group_cache[key] = (lab, glo2, ghi2, own, cone, br)
                lab, glo2, ghi2, own, cone, br = group_cache[key]
                present = ghi2 >= 0
                gback = np.array([present[gi] and back[lab == gi].all() for gi in range(G)])
                keep = present & ~gback
                Cn = range_count(keep, glo2, ghi2)
                tot['C%d' % G] += Tn - min(Cn, Tn) if keep.any() else Tn
                # cone test: back for every normal in the cone and every point in the sphere
                kb = np.zeros(G, bool)
                for gi in range(G):
                    if cone[gi] is None:
                        continue
                    ax, ca, cc, rr = cone[gi]
                    v = cc - eye; dv = np.linalg.norm(v)
                    if dv <= rr:
                        continue
                    cb = np.clip(v @ ax / dv, -1, 1); beta = np.arccos(cb); alpha = np.arccos(np.clip(ca, -1, 1))
                    if beta + alpha < np.pi / 2 and dv * np.cos(beta + alpha) > rr:
                        kb[gi] = True
                keepk = present & ~kb
                Kn = range_count(keepk, glo2, ghi2)
                tot['K%d' % G] += Tn - min(Kn, Tn) if keepk.any() else Tn
                def union(sel):
                    cov = np.zeros(vc + 1, bool)
                    for gi in np.nonzero(sel)[0]:
                        cov[glo2[gi]:ghi2[gi] + 1] = True
                    return int(cov.sum())
                tot['U%d' % G] += Tn - min(union(keep), Tn); tot['UK%d' % G] += Tn - min(union(keepk), Tn)
                tot['D%d' % G] += int(own[keep].sum()); tot['Dall%d' % G] += int(own[present].sum()); tot['DK%d' % G] += int(own[keepk].sum())
                tot['xs%d' % G] += 2 * br
print('%s: %d cams, lod_px %.0f, LOD levels/frame %s' % (work, m, lod_px, np.round(tot['lv'] / m, 1)))
T = tot['T'] / m
print('transformed corners/frame T %.0f in %.0f meshlets; strip vertices sent (whole meshlets) %.0f' % (T, tot['nlet'] / m, tot['sent'] / m))
print('E corners used only by back faces (per-triangle ideal, no grouping): %.0f (%.1f%%)' % (tot['E'] / m, 100 * tot['E'] / m / T))
print('A whole meshlets all back-facing: skip %.0f (%.1f%%)' % (tot['A'] / m, 100 * tot['A'] / m / T))
print('B today\'s strip groups all back-facing (range rule): skip %.0f (%.1f%%)' % (tot['B'] / m, 100 * tot['B'] / m / T))
for G in GS:
    print('G=%d per-group corner ranges (transform each kept group range, union): exact skip %.0f (%.1f%%), cone test skip %.0f (%.1f%%)' % (
        G, tot['U%d' % G] / m, 100 * tot['U%d' % G] / m / T, tot['UK%d' % G] / m, 100 * tot['UK%d' % G] / m / T))
    print('G=%d orientation groups: exact skip %.0f (%.1f%%); cone test skip %.0f (%.1f%%); owned corners: transform %.0f '
          '(all groups %.0f, +%.0f duplicated) -> net %.0f (%.1f%%), with the cone test net %.0f; extra strip vertices sent %.0f/frame' % (
              G, tot['C%d' % G] / m, 100 * tot['C%d' % G] / m / T, tot['K%d' % G] / m, 100 * tot['K%d' % G] / m / T,
              tot['D%d' % G] / m, tot['Dall%d' % G] / m, (tot['Dall%d' % G] / m) - T, T - tot['D%d' % G] / m,
              100 * (T - tot['D%d' % G] / m) / T, T - tot['DK%d' % G] / m, tot['xs%d' % G] / m))
