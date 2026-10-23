#!/usr/bin/env python3
"""facing23.py: OFFLINE estimate (lane facing-groups23, step 1) of re-sorting PS2 world strip groups by facing.

Usage: facing23.py <room dir> --pose x,y,z,ang [--pose ...] [--frames 30] [--far 25000] [--split-deg 60] [--json out]

<room dir> holds the CURRENT data set (sc21: ps2-world.re4mesh + ps2-world.r4sg) and the room's ps2-world.r4pw.
Nothing is written to the game data; no game code changes. Every number this prints is MODELLED / offline.

Groupings compared, same meshlets and vertex sets (per meshlet, at most G groups, G from the r4sg):
  cur   the shipped sc21 groups (r4sg records, cones recomputed with scn21_build.cone = the SCCN records).
  km    strips clustered by grid-space normal (spherical k-means, k = G, deterministic farthest-point init), groups
        ordered along the principal axis of their mean normals, corners renumbered by first use in group order.
  kms   km after splitting strips at even triangle indices where the normal turns more than --split-deg from the
        strip's running normal (parity kept; strip count and strip bytes may rise).
  best  per meshlet the lowest expected-transform of {cur, km, kms} (expected cost over a uniform view sphere:
        vertex range kept, with a cone of half angle t rejecting a far viewer with probability (1 - sin t) / 2).
Only opaque / punch-through parts (pass 0/1) with ≥ 2 strips are regrouped (as scn21_build); others keep cur.

Runtime rule replayed (native_static.cpp chunk_select, SCENERY_CONE): for a part with cull 1/2, eye e in grid space,
csgn = S * (cull==1 ? 1 : -1) * sign(det); group q rejected when d = csgn dot(axis, c - e) > R and
(d - R)^2 > TAB2[k] |c - e|^2. Transformed corners of a meshlet = vhi - vlo + 1 over its kept groups (0 if none):
only the ENDS of the vertex range are skipped, as at runtime. S (the projection handedness) is calibrated as the
sign giving the smaller per-triangle back-face share (terrain seen from above is front-facing), reported both ways.
View model: level-0 meshlets (no LOD), a meshlet is in view when its bounding sphere meets a symmetric frustum
(half angles 40 x 30 deg) within --far of the eye. The camera sits behind Leon (2.2 m back, 1.7 m up, 0.35 m right),
looking along ang (+/- --sweep deg over the frames), as the benchmark warp poses (pos, ang).
"""
import argparse, json, math, struct, sys, zlib
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scenery21'))
import scn21_build as S21  # noqa: E402


def load(room):
    room = Path(room)
    m = (room / 'ps2-world.re4mesh').read_bytes()
    sg = (room / 'ps2-world.r4sg').read_bytes()
    side = (room / 'ps2-world.r4pw').read_bytes()
    h = struct.unpack_from('<4s15I4I', m, 0)
    magic, version, nbytes, crc, nmesh, npart, nlet, nvert, nstrip, npal, o_mesh, o_part, o_let, o_vert, o_strip, o_pal = h[:16]
    assert magic == b'R4IM' and version == 3
    ncl, nlv, o_plod, o_cl, o_lv = struct.unpack_from('<5I', m, 80)
    sgh = struct.unpack_from('<4s7I', sg, 0)
    assert sgh[0] == b'R4SG' and sgh[2] == nlet and sgh[4] == crc, 'r4sg does not match the mesh'
    G = sgh[3]
    sp = struct.unpack_from('<4s7I', side, 0)
    assert sp[0] == b'R4PW' and sp[3] == npart
    side_ok = (struct.unpack_from('<I', side, 20)[0] == sgh[6])
    pmeta = [struct.unpack_from('<IIHHBBBB', side, 32 + 16 * i) for i in range(npart)]
    nplace = sp[2]
    placements = [struct.unpack_from('<HH12f', side, 32 + 16 * npart + 52 * i) for i in range(nplace)]
    meshes = [struct.unpack_from('<HBBHHIII12f', m, o_mesh + 68 * i) for i in range(nmesh)]
    lets = [struct.unpack_from('<IIIHH6H', m, o_let + 28 * li) for li in range(nlet)]
    # level-0 meshlets per part
    part_l0 = {}
    for pi in range(npart):
        fc, cc = struct.unpack_from('<II', m, o_plod + 8 * pi)
        ls = []
        for c in range(fc, fc + cc):
            fl = struct.unpack_from('<I', m, o_cl + 20 * c + 12)[0]
            fm, mc = struct.unpack_from('<II', m, o_lv + 12 * fl)
            ls.extend(range(fm, fm + mc))
        if not cc:
            first_let, let_count = struct.unpack_from('<II', m, o_part + 36 * pi + 12)
            ls = list(range(first_let, first_let + let_count))
        part_l0[pi] = ls
    lets_d = {}
    for li, r in enumerate(lets):
        fv, fs, sb, vc, sc = r[:5]
        indexed = bool(sc & 0x8000)
        s0 = o_strip + fs
        if indexed:
            offs = struct.unpack_from('<%dH' % vc, m, s0)
            s0 += 2 * vc
        else:
            offs = range(vc)
        strips, ends, s = [], [], s0
        while s < s0 + sb:
            n = m[s]; strips.append(list(m[s + 1:s + 1 + n])); s += 1 + n; ends.append(s - s0)
        pos = [struct.unpack_from('<3H', m, o_vert + 12 * (fv + offs[k])) for k in range(vc)]
        recs = [struct.unpack_from('<6HHBB', sg, 32 + 16 * (G * li + q)) for q in range(G)]
        cur, prev, j = [], 0, 0
        for rq in recs:
            end = rq[6]
            if end == prev:
                continue
            g = []
            while j < len(strips) and ends[j] <= end:
                g.append(strips[j]); j += 1
            cur.append(g); prev = end
        assert j == len(strips)
        lets_d[li] = dict(strips=strips, pos=pos, vc=vc, cur=cur, sb=sb)
    return dict(G=G, nlet=nlet, npart=npart, pmeta=pmeta, placements=placements, meshes=meshes, part_l0=part_l0,
                lets=lets_d, side_ok=side_ok, sg_bytes=len(sg), mesh_bytes=len(m))


def tri_list(strips, pos):
    out = []
    for st in strips:
        for a, b, c in S21.strip_tris(st):
            n = S21.cross(S21.sub(pos[b], pos[a]), S21.sub(pos[c], pos[a]))
            if S21.dot(n, n) > 0:
                out.append((a, b, c, n))
    return out


def strip_normal(st, pos):
    s = [0.0, 0.0, 0.0]
    for a, b, c in S21.strip_tris(st):
        n = S21.cross(S21.sub(pos[b], pos[a]), S21.sub(pos[c], pos[a]))
        s[0] += n[0]; s[1] += n[1]; s[2] += n[2]
    return S21.unit(s), math.sqrt(S21.dot(s, s))


def split_strips(strips, pos, deg):
    """Split at even triangle indices where the triangle normal leaves the running strip normal by > deg."""
    cmax = math.cos(math.radians(deg))
    out = []
    for st in strips:
        cur0, run = 0, [0.0, 0.0, 0.0]
        for k, (a, b, c) in enumerate(S21.strip_tris(st)):
            n = S21.unit(S21.cross(S21.sub(pos[b], pos[a]), S21.sub(pos[c], pos[a])))
            if n is None:
                continue
            ru = S21.unit(run)
            if ru is not None and k % 2 == 0 and k > cur0 and S21.dot(ru, n) < cmax:
                out.append(st[cur0:k + 2]); cur0 = k; run = [0.0, 0.0, 0.0]
            run[0] += n[0]; run[1] += n[1]; run[2] += n[2]
        out.append(st[cur0:])
    return out


def kmeans_groups(strips, pos, G):
    ns = [strip_normal(s, pos) for s in strips]
    nv = [(n if n is not None else (0.0, 0.0, 1.0), w) for n, w in ns]
    k = min(G, len(strips))
    # deterministic farthest-point init from the heaviest strip
    cen = [max(range(len(nv)), key=lambda i: (nv[i][1], -i))]
    while len(cen) < k:
        cen.append(min(range(len(nv)), key=lambda i: (max(S21.dot(nv[i][0], nv[c][0]) for c in cen), i)))
    C = [nv[c][0] for c in cen]
    asg = None
    for _ in range(12):
        new = [max(range(k), key=lambda q: (S21.dot(nv[i][0], C[q]), -q)) for i in range(len(nv))]
        if new == asg:
            break
        asg = new
        for q in range(k):
            s = [0.0, 0.0, 0.0]
            for i in range(len(nv)):
                if asg[i] == q:
                    s[0] += nv[i][0][0] * nv[i][1]; s[1] += nv[i][0][1] * nv[i][1]; s[2] += nv[i][0][2] * nv[i][1]
            u = S21.unit(s)
            if u is not None:
                C[q] = u
    groups = [[strips[i] for i in range(len(strips)) if asg[i] == q] for q in range(k)]
    groups = [g for g in groups if g]
    # order along the principal axis of the group mean normals: opposite facings land at opposite ends
    means = []
    for g in groups:
        s = [0.0, 0.0, 0.0]
        for t in g:
            n, w = strip_normal(t, pos)
            if n:
                s[0] += n[0] * w; s[1] += n[1] * w; s[2] += n[2] * w
        means.append(S21.unit(s) or (0.0, 0.0, 1.0))
    A = np.array(means)
    if len(A) > 1:
        _, _, vt = np.linalg.svd(A - A.mean(0) if len(A) > 2 else A)
        ax = vt[0]
        order = sorted(range(len(groups)), key=lambda q: (float(A[q] @ ax), q))
        groups = [groups[q] for q in order]
    return groups


def finish(groups, pos, vc):
    """Renumber corners by first use in group order; -> per group dict(cone info, vlo, vhi, ntri, tris)."""
    new_of = {}
    for g in groups:
        for s in g:
            for k in s:
                if k not in new_of:
                    new_of[k] = len(new_of)
    out = []
    for g in groups:
        ks = [k for s in g for k in s]
        lo = [min(pos[k][a] for k in ks) for a in range(3)]
        hi = [max(pos[k][a] for k in ks) for a in range(3)]
        _, info = S21.cone(g, pos, lo, hi)
        nk = [new_of[k] for k in ks]
        tris = tri_list(g, pos)
        out.append(dict(info=info, vlo=min(nk), vhi=max(nk), ntri=sum(max(0, len(s) - 2) for s in g), lo=lo, hi=hi,
                        nstrip=len(g), sbytes=sum(1 + len(s) for s in g), tris=tris))
    return out


def expected(gs, vc):
    """Expected transformed corners over a uniform view sphere (independence approximation)."""
    p = [((1 - math.sin(math.atan(i[1] / 128.0))) / 2.0 if i else 0.0) for i in (g['info'] for g in gs)]
    # probability each group kept; expected range ~ sum over corners of P(some kept group spans it), approximate by
    # expected (hi - lo + 1) with ends trimmed independently
    keep = [1 - x for x in p]
    e, n = 0.0, len(gs)
    for i in range(n):
        for j in range(i, n):
            pr = keep[i] * keep[j]
            for q in range(i): pr *= p[q]
            for q in range(j + 1, n): pr *= p[q]
            if i == j:
                pr = keep[i]
                for q in range(n):
                    if q != i: pr *= p[q]
            e += pr * (max(gs[j]['vhi'], gs[i]['vhi']) - min(gs[i]['vlo'], gs[j]['vlo']) + 1)
    return e


def build(D, split_deg):
    G = D['G']
    regroup_parts = {pi for pi in range(D['npart']) if D['pmeta'][pi][4] in (0, 1)}
    let_part = {}
    for pi, ls in D['part_l0'].items():
        for li in ls:
            let_part[li] = pi
    out = {'cur': {}, 'km': {}, 'kms': {}, 'best': {}}
    for li, L in D['lets'].items():
        pos, vc = L['pos'], L['vc']
        cur = finish(L['cur'], pos, vc)
        out['cur'][li] = cur
        if let_part.get(li) in regroup_parts and len(L['strips']) > 1:
            km = finish(kmeans_groups(L['strips'], pos, G), pos, vc)
            ss = split_strips(L['strips'], pos, split_deg)
            kms = finish(kmeans_groups(ss, pos, G), pos, vc) if len(ss) != len(L['strips']) else km
        else:
            km = kms = cur
        out['km'][li] = km; out['kms'][li] = kms
        cand = [(expected(cur, vc), 0, cur), (expected(km, vc), 1, km), (expected(kms, vc), 2, kms)]
        out['best'][li] = min(cand, key=lambda t: (t[0], t[1]))[2]
    return out


def arrays(gs_by_let):
    """Per meshlet numpy arrays of group cone data and triangles."""
    A = {}
    for li, gs in gs_by_let.items():
        rows = []
        for g in gs:
            i = g['info']
            c = [(g['lo'][a] + g['hi'][a]) * 0.5 for a in range(3)]
            if i:
                rows.append((*c, *i[0], i[1], i[2], 1.0, g['vlo'], g['vhi'], g['ntri']))
            else:
                rows.append((*c, 0, 0, 0, 0, 0, 0.0, g['vlo'], g['vhi'], g['ntri']))
        A[li] = np.array(rows, np.float64)
    return A


def tri_arrays(D):
    T = {}
    for li, L in D['lets'].items():
        tl = tri_list(L['strips'], L['pos'])
        if tl:
            p = np.array([L['pos'][a] for a, b, c, n in tl], np.float64)
            n = np.array([t[3] for t in tl], np.float64)
            T[li] = (p, n)
    return T


def poses(spec, frames, sweep):
    x, y, z, ang = spec
    out = []
    for f in range(frames):
        a = ang + math.radians(sweep) * (2.0 * f / max(frames - 1, 1) - 1.0)
        fw = np.array([math.sin(a), 0.0, math.cos(a)])
        rt = np.array([math.cos(a), 0.0, -math.sin(a)])
        eye = np.array([x, y, z]) - fw * 2200 + np.array([0, 1700.0, 0]) + rt * 350
        look = np.array([x, y, z]) + fw * 3000 + np.array([0, 1200.0, 0])
        d = look - eye; d /= np.linalg.norm(d)
        out.append((eye, d))
    return out


def simulate(D, groupings, T, eye, fwd, far, sgn):
    up = np.array([0.0, 1.0, 0.0])
    rt = np.cross(fwd, up); rt /= np.linalg.norm(rt)
    upv = np.cross(rt, fwd)
    th, tv = math.radians(40), math.radians(30)
    res = {k: dict(base=0, xf=0, tris=0, rejtri=0, groups_tested=0, groups_rej=0) for k in groupings}
    bf = dict(tris=0, back=0)
    for (mi, gi, *aff) in D['placements']:
        M = np.array(aff, np.float64).reshape(3, 4)
        mr = D['meshes'][mi]
        step, org = np.array(mr[11:14]), np.array(mr[8:11])
        M3 = M[:, :3] * step[None, :]
        t = M[:, :3] @ org + M[:, 3]
        det = np.linalg.det(M3)
        if abs(det) < 1e-12:
            continue
        e = np.linalg.solve(M3, eye - t)
        sc = abs(det) ** (1 / 3)
        for pi in range(mr[6], mr[6] + mr[7]):
            cull = D['pmeta'][pi][5]
            for li in D['part_l0'][pi]:
                L = D['lets'][li]
                pos = L['pos']
                if not pos:
                    continue
                lo = np.min(pos, 0); hi = np.max(pos, 0)
                cw = M3 @ ((lo + hi) * 0.5) + t
                r = 0.5 * np.linalg.norm((hi - lo) * step) * np.linalg.norm(M[:, :3], 2)
                v = cw - eye
                dist = np.linalg.norm(v)
                if dist - r > far:
                    continue
                if dist > r:
                    zf = v @ fwd
                    if zf < -r:
                        continue
                    xa = abs(v @ rt); ya = abs(v @ upv)
                    if xa - r > max(zf, 0) * math.tan(th) + r * 0.5 or ya - r > max(zf, 0) * math.tan(tv) + r * 0.5:
                        continue
                vc = L['vc']
                cs = sgn * (1.0 if cull == 1 else -1.0) * (1.0 if det > 0 else -1.0)
                if li in T:
                    p, n = T[li]
                    bf['tris'] += len(p)
                    if cull in (1, 2):
                        bf['back'] += int(np.count_nonzero(cs * np.einsum('ij,ij->i', n, p - e) > 0))
                for k, A in groupings.items():
                    a = A[li]
                    R_ = res[k]
                    R_['base'] += vc
                    R_['tris'] += int(a[:, 11].sum())
                    if cull in (1, 2):
                        vv = a[:, 0:3] - e
                        d = cs * np.einsum('ij,ij->i', a[:, 3:6], vv)
                        rej = (a[:, 8] > 0) & (d > a[:, 7]) & ((d - a[:, 7]) * np.abs(d - a[:, 7]) > (a[:, 6] ** 2) * np.einsum('ij,ij->i', vv, vv))
                        R_['groups_tested'] += int(np.count_nonzero(a[:, 8] > 0))
                        R_['groups_rej'] += int(np.count_nonzero(rej))
                        R_['rejtri'] += int(a[rej, 11].sum())
                        kept = a[~rej]
                        R_['xf'] += 0 if len(kept) == 0 else int(kept[:, 10].max() - kept[:, 9].min() + 1)
                    else:
                        R_['xf'] += vc
    return res, bf


def stats(D, gby):
    groups = strips = sbytes = cones = 0
    for li, gs in gby.items():
        groups += len(gs)
        strips += sum(g['nstrip'] for g in gs)
        sbytes += sum(g['sbytes'] for g in gs)
        cones += sum(1 for g in gs if g['info'])
    return dict(meshlets=len(gby), groups=groups, strips=strips, strip_bytes=sbytes, cones=cones)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('room')
    ap.add_argument('--pose', action='append', required=True)
    ap.add_argument('--frames', type=int, default=30)
    ap.add_argument('--sweep', type=float, default=20.0)
    ap.add_argument('--far', type=float, default=25000.0)
    ap.add_argument('--split-deg', type=float, default=60.0)
    ap.add_argument('--groups', type=int, default=0, help='override G for km/kms (cur keeps the r4sg)')
    ap.add_argument('--json')
    a = ap.parse_args()
    D = load(a.room)
    if a.groups:
        D['G'] = a.groups
    B = build(D, a.split_deg)
    gs = {k: arrays(v) for k, v in B.items()}
    T = tri_arrays(D)
    st = {k: stats(D, v) for k, v in B.items()}
    G = D['G']
    rep = dict(room=a.room, G=G, side_crc_matches_r4sg=D['side_ok'], r4sg_bytes=D['sg_bytes'],
               sccn_bytes=16 + 256 + 8 * G * D['nlet'] + (-(16 + 256 + 8 * G * D['nlet']) % 16), structure=st, scenes=[])
    for spec in a.pose:
        x, y, z, ang = (float(v) for v in spec.split(','))
        per = {}
        for s in (1.0, -1.0):
            tot = {k: dict(base=0, xf=0, tris=0, rejtri=0, groups_tested=0, groups_rej=0) for k in gs}
            bft = dict(tris=0, back=0)
            for eye, fwd in poses((x, y, z, ang), a.frames, a.sweep):
                r, bf = simulate(D, gs, T, eye, fwd, a.far, s)
                for k in r:
                    for f in r[k]:
                        tot[k][f] += r[k][f]
                bft['tris'] += bf['tris']; bft['back'] += bf['back']
            per[s] = (tot, bft)
        S = min(per, key=lambda s: per[s][1]['back'] / max(per[s][1]['tris'], 1))
        tot, bft = per[S]
        row = dict(pose=spec, frames=a.frames, sign=S,
                   backface_tri_share=bft['back'] / max(bft['tris'], 1),
                   backface_tri_share_other_sign=per[-S][1]['back'] / max(per[-S][1]['tris'], 1),
                   per_frame_base_corners=tot['cur']['base'] / a.frames)
        for k, v in tot.items():
            row[k] = dict(skip_share=1 - v['xf'] / max(v['base'], 1), rejtri_share=v['rejtri'] / max(v['tris'], 1),
                          group_rej_share=v['groups_rej'] / max(v['groups_tested'], 1))
        rep['scenes'].append(row)
    print(json.dumps(rep, indent=1))
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1))


if __name__ == '__main__':
    main()
