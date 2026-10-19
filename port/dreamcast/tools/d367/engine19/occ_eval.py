"""occ_eval.py <room.r4rc> <pkg dir> <run-output> [stride]: replica of the runtime OCCL rule (room_vis.c) over logged
in-view enemy ticks, checked against the dense exact-eye oracle (dense.py). A cull the oracle calls visible = BUG."""
import math, struct, sys
import numpy as np
import vis_enemy as ve

R, H, M = 450.0, 1800.0, 50.0
WINDING = {1: -1, 2: 1}


def load_tris_cull(pkgdir):
    """pass 0, level 0: triangles (n,3,3) and drawn-face sign per triangle (0 two-sided, +-1, None-> 9 unknown)."""
    from pathlib import Path
    from r4im_pkg import Pkg
    p = Pkg(Path(pkgdir) / 'ps2-world.re4mesh', Path(pkgdir) / 'ps2-world.r4pw')
    out, fs = [], []
    for pi, part, c, ps, cull, lo, hi in p.iter_clusters():
        if ps != 0:
            continue
        t = p.cluster_tris_world(pi, c, 0)
        if not len(t):
            continue
        det = np.linalg.det(p.wq(p.placements[pi])[:, :3])
        f = 0 if not cull else (WINDING[cull] if det > 0 else 9)
        out.append(t); fs.append(np.full(len(t), f))
    return np.concatenate(out).astype(np.float64), np.concatenate(fs)


def blocked_cull(eye, pts, T, F):
    """per sample point: does eye->pt hit a triangle drawn toward the eye (unknown facing: never blocks)?"""
    lo = np.minimum(eye, pts.min(0)) - 1; hi = np.maximum(eye, pts.max(0)) + 1
    sel = np.all((T.max(1) >= lo) & (T.min(1) <= hi), 1) & (F != 9)
    S, SF = T[sel], F[sel]
    res = np.zeros(len(pts), bool)
    if not len(S):
        return res
    v0 = S[:, 0]; e1 = S[:, 1] - v0; e2 = S[:, 2] - v0
    nrm = np.cross(e1, e2)
    toward = (SF == 0) | (SF * np.einsum('ij,ij->i', nrm, eye - v0) > 0)
    for i, pt in enumerate(pts):
        d = pt - eye
        h = np.cross(d, e2); a = np.einsum('ij,ij->i', e1, h)
        ok = np.abs(a) > 1e-9
        f = np.where(ok, 1.0 / np.where(ok, a, 1), 0)
        s = eye - v0
        u = f * np.einsum('ij,ij->i', s, h)
        q = np.cross(s, e1)
        v = f * (q @ d)
        t = f * np.einsum('ij,ij->i', e2, q)
        hit = ok & toward & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-4) & (t < 0.999)
        res[i] = hit.any()
    return res


def load(path):
    b = open(path, 'rb').read()
    n = struct.unpack_from('<I', b, 12)[0]
    x0, z0 = struct.unpack_from('<ii', b, 32)
    cell = struct.unpack_from('<I', b, 28)[0]
    for i in range(n):
        tag, ver, fl, off, by = struct.unpack_from('<4sHHII', b, 64 + 32 * i)
        if tag == b'OCCL':
            s = b[off:off + by]
            vw, vh, div, nocc, nlist, rng = struct.unpack_from('<6H', s, 0)
            occ = []
            for k in range(nocc):
                v = struct.unpack_from('<13fb', s, 32 + 56 * k)
                occ.append((np.array(v[:12]).reshape(4, 3), v[12], v[13]))
            co = 32 + 56 * nocc
            cells = [struct.unpack_from('<HBB', s, co + 4 * c) for c in range(vw * vh)]
            lo = co + 4 * vw * vh
            lists = struct.unpack_from('<%dH' % nlist, s, lo)
            return dict(x0=x0, z0=z0, cs=cell * div, vw=vw, vh=vh, occ=occ, cells=cells, lists=lists, rng=rng * 10.0)


def quad_shadow(E, C, corners):
    ctr = C.mean(0)
    for i in range(4):
        m = np.cross(C[i] - E, C[(i + 1) % 4] - E)
        if m @ (ctr - E) < 0:
            m = -m
        if np.any((corners - E) @ m < 0):
            return False
    return True


def shadowed(E, C, half, side, lo, hi, Vm, near, far, rng):
    n = np.cross(C[1] - C[0], C[3] - C[0]); n /= np.linalg.norm(n)
    n = n * side                    # front normal: the eye side
    d = n @ C[0]
    if n @ E - d < half + 50.0:     # eye in front of the slab's front face
        return False
    F, B = C + n * half, C - n * half
    for p in np.vstack([F, B]):
        z = -(Vm[2, :3] @ p + Vm[2, 3])
        if z < near + 10.0 or z > far - 100.0 or np.linalg.norm(p - E) > rng:
            return False
    corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    if np.any(corners @ n - d > -half - 1.0):   # every corner behind the back face
        return False
    return quad_shadow(E, F, corners) and quad_shadow(E, B, corners)


def main():
    V = load(sys.argv[1])
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent / 'vis'))
    T, F = load_tris_cull(sys.argv[2])
    cams, ems = ve.logs(sys.argv[3], 0, 10 ** 9)
    stride = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    fs = sorted(set(cams) & set(ems))[::stride]
    inv = cul = bugs = oracle = 0
    g = np.linspace(-1, 1, 5)
    for f in fs:
        x = cams[f]
        Vm = np.array(x[:12]).reshape(3, 4); P = x[12:19]; far = x[19]; near = P[6] / (P[5] - 1)
        E = -Vm[:, :3].T @ Vm[:, 3]
        cx, cz = int((E[0] - V['x0']) // V['cs']), int((E[2] - V['z0']) // V['cs'])
        lst = ()
        if 0 <= cx < V['vw'] and 0 <= cz < V['vh']:
            first, cnt, _ = V['cells'][cx + cz * V['vw']]
            lst = V['lists'][first:first + cnt]
        for e, (ex, ey, ez, hp, d) in ems[f].items():
            if hp <= 0 or not ve.in_view(Vm, P, near, far, np.array([ex, ey + H / 2, ez]), math.hypot(R, H / 2)):
                continue
            inv += 1
            lo = (ex - R - M, ey - 100 - M, ez - R - M); hi = (ex + R + M, ey + H + M, ez + R + M)
            c = any(shadowed(E, *V['occ'][k], lo, hi, Vm, near, far, V['rng']) for k in lst)
            pts = np.array([[ex + a * R, ey - 100 + (b + 1) / 2 * (H + 100), ez + cc * R] for a in g for b in g for cc in g])
            hid = blocked_cull(E, pts, T, F).all()
            oracle += hid
            if c:
                cul += 1
                if not hid:
                    bugs += 1
                    print('BUG f=%d e=%s' % (f, e))
    print(dict(pictures=len(fs), in_view=inv, oracle_hidden=int(oracle), culled=cul, bugs=bugs,
               culled_per_picture=round(cul / max(1, len(fs)), 3), oracle_per_picture=round(oracle / max(1, len(fs)), 3)))


if __name__ == '__main__':
    main()
