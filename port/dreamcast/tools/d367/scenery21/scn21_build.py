#!/usr/bin/env python3
"""scn21_build.py: the scenery-pieces data set (lane scenery21, P2 second half) for every PS2 world room.

Usage: scn21_build.py <native in dir> <out dir> [--groups 4] [--facing] [--sim room:x,y,z ...] [rooms...]

Per room with dc/native/<room>/ps2-world.re4mesh + ps2-world.r4pw in <native in dir> (a release disc tree):
  1. Strip groups (tools/ps2_strip_groups.py layout, R4SG v1, same runtime reader): up to G groups per meshlet.
     --facing: opaque / punch-through strips are first binned by facing (dominant axis of the strip's model-space
     normal, 6 bins, small bins merged into the nearest by mean normal), then the largest group is halved spatially
     (kd, as ps2_strip_groups.py) until G groups. Without --facing: ps2_strip_groups.py's spatial kd split.
     Translucent parts keep their strip order (G runs). Corners are renumbered by first use in group order (the
     vertex records / pool offsets permuted, as ps2_strip_groups.py); triangles are unchanged.
  2. R4RC section 'SCCN' v1 (SCENERY_CONE=1): per meshlet x group a back-face cone in grid space, 8 B:
     s8 axis[3] (quantised; the bound is computed with the quantised axis), u8 k (0 = no cone), f32 R.
     Every triangle n of the group (n = cross(b - a, c - a) in grid coordinates, strip parity as the PVR walks it)
     satisfies dot(n, p - e) > 0 for every point p of the group's box sphere whenever, with v = c - e,
         d = dot(axis, v) > R  and  (d - R)^2 > TAB2[k] |v|^2       (c = the group box centre, e = the eye)
     TAB2[k] = (128 tan(theta_k))^2, theta_k = k * 87/63 deg >= theta + 0.5 deg (theta: the largest angle between the
     axis and a triangle normal), R = |axis| (r / cos(theta_k) + 1), r the box half diagonal + 0.5. Orientation is
     affine invariant, so the runtime tests the cone or its negation by the part's cull mode and the sign of det(mvq).
     Body: head 16 B (u32 mesh crc, u32 mesh bytes, u32 meshlet count, u32 groups), f32 TAB2[64], records; pad 16.
  3. R4RC section 'SCPS' v1 (SCENERY_PIECE_STATE=1): head 16 B (u32 mesh crc, u32 mesh bytes, u32 part count, 0) +
     u32[part count] zero: one header-slot word per piece, written by the runtime at the first bind in the room
     (the texture's VRAM address is known only after it loads) and checked at every bind.
  4. SCDD (scenery19 scdd_compile.py) recomputed for the new mesh (a stale one would be refused anyway).
Outputs <out>/<room>/{ps2-world.re4mesh, ps2-world.r4sg, room.r4rc}, MANIFEST-SC21.tsv, SHA256SUMS. Deterministic.
--sim room:x,y,z: for that room, the share of level-0 corners whose group the cone rejects for a world-space eye
(every placement, no frustum): a data-only estimate, not timing.
"""
import argparse, hashlib, json, math, struct, sys, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scenery19'))
import scdd_compile  # noqa: E402

PI_HALF_MARGIN = math.radians(0.5)


def strip_tris(st):
    for k in range(len(st) - 2):
        a, b, c = st[k], st[k + 1], st[k + 2]
        yield (a, b, c) if k % 2 == 0 else (c, b, a)


def sub(p, q):
    return (p[0] - q[0], p[1] - q[1], p[2] - q[2])


def cross(u, v):
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])


def dot(u, v):
    return u[0] * v[0] + u[1] * v[1] + u[2] * v[2]


def unit(u):
    n = math.sqrt(dot(u, u))
    return (u[0] / n, u[1] / n, u[2] / n) if n > 0 else None


def tri_normals(strips, pos):
    out = []
    for st in strips:
        for a, b, c in strip_tris(st):
            pa, pb, pc = pos[a], pos[b], pos[c]
            n = unit(cross(sub(pb, pa), sub(pc, pa)))
            if n is not None:
                out.append(n)
    return out


KSTEP = math.radians(87.0 / 63.0)   # cone code k (1..63): theta_k = k * KSTEP
TAB2 = [0.0] + [(128.0 * math.tan(k * KSTEP)) ** 2 for k in range(1, 64)]
NOCONE = struct.pack('<3bBf', 0, 0, 0, 0, 0.0)


def cone(strips, pos, lo, hi):
    """8 B record: s8 axis[3] (quantised; theta measured against it), u8 k, f32 R. Runtime rejects when
    d = dot(axis, c - e) > R and (d - R)^2 > TAB2[k] |c - e|^2, i.e. d > 128 tan(theta_k) |v| + R >= |axis| tan|v| + R."""
    ns = tri_normals(strips, pos)
    if not ns:
        return NOCONE, None
    s = (sum(n[0] for n in ns), sum(n[1] for n in ns), sum(n[2] for n in ns))
    ax = unit(s)
    if ax is None:
        return NOCONE, None
    aq = tuple(max(-127, min(127, int(round(v * 127)))) for v in ax)
    la = math.sqrt(dot(aq, aq))
    if la == 0 or la > 128.0:
        return NOCONE, None
    cmin = min(dot(n, aq) / la for n in ns)
    if cmin <= 0.05:
        return NOCONE, None
    th = math.acos(min(1.0, cmin)) + PI_HALF_MARGIN
    k = int(math.ceil(th / KSTEP))
    if k < 1:
        k = 1
    if k > 63:
        return NOCONE, None
    thk = k * KSTEP
    r = 0.5 * math.sqrt(sum((hi[a] - lo[a]) ** 2 for a in range(3))) + 0.5
    R = la * (r / math.cos(thk) + 1.0)
    return struct.pack('<3bBf', aq[0], aq[1], aq[2], k, R), (aq, 128.0 * math.tan(thk), R, lo, hi)


def build_room(mesh_path, side_path, G, facing):
    m = bytearray(Path(mesh_path).read_bytes())
    side = Path(side_path).read_bytes()
    h = struct.unpack_from('<4s15I4I', m, 0)
    magic, version, nbytes, crc, nmesh, npart, nlet, nvert, nstrip, npal, o_mesh, o_part, o_let, o_vert, o_strip, o_pal = h[:16]
    assert magic == b'R4IM' and version == 3 and nbytes == len(m), (magic, version)
    ncl, nlv, o_plod, o_cl, o_lv = struct.unpack_from('<5I', m, 80)
    hp = struct.unpack_from('<4s7I', side, 0)
    assert hp[0] == b'R4PW'
    nparts_side = hp[3]
    side_crc = struct.unpack_from('<I', side, 20)[0]
    assert nparts_side == npart
    part_pass = [side[32 + 16 * i + 12] for i in range(npart)]
    part_step = [(1.0, 1.0, 1.0)] * npart
    for mi in range(nmesh):
        r = struct.unpack_from('<HBBHHIII12f', m, o_mesh + 68 * mi)
        for pi in range(r[6], r[6] + r[7]):
            part_step[pi] = tuple(r[11:14])
    let_part = [None] * nlet
    for pi in range(npart):
        first_let, let_count = struct.unpack_from('<II', m, o_part + 36 * pi + 12)
        for li in range(first_let, first_let + let_count):
            let_part[li] = pi
        fc, cc = struct.unpack_from('<II', m, o_plod + 8 * pi)
        for c in range(fc, fc + cc):
            fl, lc = struct.unpack_from('<II', m, o_cl + 20 * c + 12)
            for lv in range(fl, fl + lc):
                fm, mc = struct.unpack_from('<II', m, o_lv + 12 * lv)
                for li in range(fm, fm + mc):
                    let_part[li] = pi
    lets = []
    for li in range(nlet):
        r = struct.unpack_from('<IIIHH6H', m, o_let + 28 * li)
        lets.append(dict(fv=r[0], fs=r[1], sb=r[2], vc=r[3], sc=r[4]))
    owner = {}
    for li, L in enumerate(lets):
        if not L['sc'] & 0x8000:
            for v in range(L['fv'], L['fv'] + L['vc']):
                assert v not in owner, 'two non-indexed meshlets share vertex %d' % v
                owner[v] = li
    vmap = {}
    recs, cones, geo = {}, {}, {}
    st = dict(meshlets=nlet, groups=G, facing=bool(facing), cones=0, cone_corners=0, corners=0, nonempty=0)

    def process(li, L):
        indexed = bool(L['sc'] & 0x8000)
        fs = o_strip + L['fs']
        vc = L['vc']
        if indexed:
            offs = list(struct.unpack_from('<%dH' % vc, m, fs))
            for k in range(vc):
                v = L['fv'] + offs[k]
                if v in vmap and vmap[v] != v:
                    offs[k] = vmap[v] - L['fv']
            s0 = fs + 2 * vc
        else:
            s0 = fs
        end = s0 + L['sb']
        strips = []
        s = s0
        while s < end:
            n = m[s]; strips.append(list(m[s + 1:s + 1 + n])); s += 1 + n
        assert s == end

        def grid(k):
            base = L['fv'] + (offs[k] if indexed else k)
            return struct.unpack_from('<3H', m, o_vert + 12 * base)
        pos = [grid(k) for k in range(vc)]
        pi = let_part[li]
        ng = min(G, len(strips))
        if pi is not None and part_pass[pi] in (0, 1) and len(strips) > 1:
            stp = part_step[pi]
            cen = {id(t): [sum(pos[k][a] for k in t) / len(t) * abs(stp[a]) for a in range(3)] for t in strips}
            if facing:
                # model-space strip normal (grid normal scaled by the cofactors of diag(step)); bins by dominant axis
                def snorm(t):
                    s_ = [0.0, 0.0, 0.0]
                    for a_, b_, c_ in strip_tris(t):
                        n_ = cross(sub(pos[b_], pos[a_]), sub(pos[c_], pos[a_]))
                        s_[0] += n_[0]; s_[1] += n_[1]; s_[2] += n_[2]
                    s_ = (s_[0] * stp[1] * stp[2], s_[1] * stp[0] * stp[2], s_[2] * stp[0] * stp[1])
                    return unit(s_) or (0.0, 0.0, 0.0)
                nrm = {id(t): snorm(t) for t in strips}
                bins = {}
                for t in strips:
                    n_ = nrm[id(t)]
                    a_ = max(range(3), key=lambda q: abs(n_[q]))
                    key = (a_, n_[a_] >= 0)
                    bins.setdefault(key, []).append(t)
                groups = [bins[k] for k in sorted(bins)]

                def mean(g):
                    s_ = [0.0, 0.0, 0.0]
                    for t in g:
                        n_ = nrm[id(t)]
                        s_[0] += n_[0]; s_[1] += n_[1]; s_[2] += n_[2]
                    return unit(s_) or (0.0, 0.0, 0.0)
                while len(groups) > ng:
                    i = min(range(len(groups)), key=lambda j: len(groups[j]))
                    g = groups.pop(i)
                    mg = mean(g)
                    j = max(range(len(groups)), key=lambda q: dot(mean(groups[q]), mg))
                    groups[j] = groups[j] + g
            else:
                groups = [strips]
            while len(groups) < ng:
                i = max(range(len(groups)), key=lambda j: len(groups[j]))
                g = groups[i]
                if len(g) < 2:
                    break
                ax = max(range(3), key=lambda a: max(cen[id(t)][a] for t in g) - min(cen[id(t)][a] for t in g))
                g = sorted(g, key=lambda t: cen[id(t)][ax])
                hh = len(g) // 2
                groups[i:i + 1] = [g[:hh], g[hh:]]
        else:
            per = -(-len(strips) // ng)
            groups = [strips[i:i + per] for i in range(0, len(strips), per)]
        new_of = {}
        for g in groups:
            for s_ in g:
                for k in s_:
                    if k not in new_of:
                        new_of[k] = len(new_of)
        for k in range(vc):
            if k not in new_of:
                new_of[k] = len(new_of)
        old_of = [0] * vc
        for k, nk in new_of.items():
            old_of[nk] = k
        if indexed:
            struct.pack_into('<%dH' % vc, m, fs, *[offs[old_of[nk]] for nk in range(vc)])
        else:
            rec = [bytes(m[o_vert + 12 * (L['fv'] + k):o_vert + 12 * (L['fv'] + k) + 12]) for k in range(vc)]
            for nk in range(vc):
                m[o_vert + 12 * (L['fv'] + nk):o_vert + 12 * (L['fv'] + nk) + 12] = rec[old_of[nk]]
            for k in range(vc):
                vmap[L['fv'] + k] = L['fv'] + new_of[k]
        groups = [[[new_of[k] for k in s_] for s_ in g] for g in groups]
        pos = [pos[old_of[nk]] for nk in range(vc)]
        out = bytearray(); rl = bytearray(); cl = bytearray(); gl = []
        for g in groups:
            for s_ in g:
                out.append(len(s_)); out.extend(s_)
            ks = [k for s_ in g for k in s_]
            lo = [min(pos[k][a] for k in ks) for a in range(3)]; hi = [max(pos[k][a] for k in ks) for a in range(3)]
            rl += struct.pack('<6HHBB', *lo, *hi, len(out), min(ks), max(ks))
            rec_c, info = cone(g, pos, lo, hi)
            cl += rec_c
            gl.append((info, max(ks) - min(ks) + 1))
            st['nonempty'] += 1
            if info:
                st['cones'] += 1; st['cone_corners'] += max(ks) - min(ks) + 1
        assert len(out) == L['sb']
        m[s0:end] = out
        for _ in range(G - len(groups)):
            rl += struct.pack('<6HHBB', 0, 0, 0, 0, 0, 0, len(out), 1, 0)
            cl += NOCONE
        recs[li] = bytes(rl); cones[li] = bytes(cl); geo[li] = (gl, vc)
        st['corners'] += vc
    for li, L in enumerate(lets):
        if not L['sc'] & 0x8000:
            process(li, L)
    for li, L in enumerate(lets):
        if L['sc'] & 0x8000:
            process(li, L)
    rb = b''.join(recs[li] for li in range(nlet))
    cb = b''.join(cones[li] for li in range(nlet))
    struct.pack_into('<I', m, 12, zlib.crc32(bytes(m[80:])) & 0xffffffff)
    new_crc = struct.unpack_from('<I', m, 12)[0]
    r4sg = struct.pack('<4s7I', b'R4SG', 1, nlet, G, new_crc, len(m), side_crc, zlib.crc32(bytes(rb)) & 0xffffffff) + rb
    sccn = struct.pack('<4I', new_crc, len(m), nlet, G) + struct.pack('<64f', *TAB2) + cb
    sccn += bytes(-len(sccn) % 16)
    scps = struct.pack('<4I', new_crc, len(m), npart, 0) + bytes(4 * npart)
    scps += bytes(-len(scps) % 16)
    st.update(mesh_crc_in='%08x' % crc, mesh_crc_out='%08x' % new_crc, r4sg_bytes=len(r4sg), sccn_bytes=len(sccn),
              scps_bytes=len(scps), parts=npart)
    return bytes(m), r4sg, sccn, scps, st, geo


def sim(room_dir, mesh_bytes, geo, eye):
    """Share of level-0 corners in cone-rejected groups for a world eye, both orientations counted as 'culled side'
    unknown: reports the corners whose group is wholly one-sided for the eye (the runtime drops the culled side)."""
    m = mesh_bytes
    side = (room_dir / 'ps2-world.r4pw').read_bytes()
    h = struct.unpack_from('<4s15I4I', m, 0)
    nmesh, npart, o_mesh, o_part = h[4], h[5], h[10], h[11]
    ncl, nlv, o_plod, o_cl, o_lv = struct.unpack_from('<5I', m, 80)
    nplace, nparts = struct.unpack_from('<II', side, 8)
    base = 32 + 16 * nparts
    tot = rej = rejn = 0
    for i in range(nplace):
        r = struct.unpack_from('<HH12f', side, base + 52 * i)
        A = [r[2 + 4 * row:6 + 4 * row] for row in range(3)]
        mr = struct.unpack_from('<HBBHHIII12f', m, o_mesh + 68 * r[0])
        step, org = mr[11:14], mr[8:11]
        # world = A3 (step * g + org) + At  ->  M3 = A3 diag(step), t = A3 org + At
        M3 = [[A[row][c] * step[c] for c in range(3)] for row in range(3)]
        t = [sum(A[row][c] * org[c] for c in range(3)) + A[row][3] for row in range(3)]
        b = [eye[row] - t[row] for row in range(3)]
        det = (M3[0][0] * (M3[1][1] * M3[2][2] - M3[1][2] * M3[2][1]) - M3[0][1] * (M3[1][0] * M3[2][2] - M3[1][2] * M3[2][0])
               + M3[0][2] * (M3[1][0] * M3[2][1] - M3[1][1] * M3[2][0]))
        if abs(det) < 1e-12:
            continue
        e = []
        for col in range(3):  # Cramer
            Mc = [[b[row] if c == col else M3[row][c] for c in range(3)] for row in range(3)]
            dc = (Mc[0][0] * (Mc[1][1] * Mc[2][2] - Mc[1][2] * Mc[2][1]) - Mc[0][1] * (Mc[1][0] * Mc[2][2] - Mc[1][2] * Mc[2][0])
                  + Mc[0][2] * (Mc[1][0] * Mc[2][1] - Mc[1][1] * Mc[2][0]))
            e.append(dc / det)
        for pi in range(mr[6], mr[6] + mr[7]):
            fc, cc = struct.unpack_from('<II', m, o_plod + 8 * pi)
            for c in range(fc, fc + cc):
                fl = struct.unpack_from('<I', m, o_cl + 20 * c + 12)[0]
                fm, mc = struct.unpack_from('<II', m, o_lv + 12 * fl)
                for li in range(fm, fm + mc):
                    gl, vc = geo[li]
                    tot += vc
                    for info, rng in gl:
                        if not info:
                            continue
                        aq, T, R, lo, hi = info
                        cc_ = [(lo[a] + hi[a]) * 0.5 for a in range(3)]
                        v = [cc_[a] - e[a] for a in range(3)]
                        lv = math.sqrt(dot(v, v))
                        d = dot(aq, v)
                        if d > T * lv + R:
                            rej += rng
                        elif -d > T * lv + R:
                            rejn += rng
    return tot, rej, rejn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('native'); ap.add_argument('out')
    ap.add_argument('--groups', type=int, default=4); ap.add_argument('--facing', action='store_true')
    ap.add_argument('--sim', action='append', default=[])
    ap.add_argument('--no-write', action='store_true')
    ap.add_argument('rooms', nargs='*')
    a = ap.parse_intermixed_args()
    nat, out = Path(a.native), Path(a.out)
    rooms = a.rooms or sorted(d.name for d in nat.iterdir() if (d / 'ps2-world.re4mesh').is_file())
    sims = {}
    for s in a.sim:
        r, xyz = s.split(':')
        sims.setdefault(r, []).append(tuple(float(v) for v in xyz.split(',')))
    rows, sums = [], []
    for r in rooms:
        d = nat / r
        mesh, r4sg, sccn, scps, st, geo = build_room(d / 'ps2-world.re4mesh', d / 'ps2-world.r4pw', a.groups, a.facing)
        for eye in sims.get(r, []):
            tot, rej, rejn = sim(d, mesh, geo, eye)
            print('SIM %s eye=%s corners=%d one-sided +n %d (%.1f%%) -n %d (%.1f%%)' % (r, eye, tot, rej, 100.0 * rej / max(tot, 1),
                  rejn, 100.0 * rejn / max(tot, 1)))
        print(r, json.dumps(st))
        if a.no_write:
            continue
        o = out / r
        o.mkdir(parents=True, exist_ok=True)
        (o / 'ps2-world.re4mesh').write_bytes(mesh)
        (o / 'ps2-world.r4sg').write_bytes(r4sg)
        b = (d / 'room.r4rc').read_bytes()
        secs = [s for s in scdd_compile.read_rc(b) if s[0] not in (b'SCDD', b'SCCN', b'SCPS')]
        tmp = o / '_scdd'
        tmp.mkdir(exist_ok=True)
        (tmp / 'ps2-world.re4mesh').write_bytes(mesh)
        body, sst = scdd_compile.scdd(tmp)
        (tmp / 'ps2-world.re4mesh').unlink(); tmp.rmdir()
        secs.append([b'SCDD', 1, 0, body, sst['meshlets'], 0, 16])
        secs.append([b'SCCN', 1, 0, sccn, st['meshlets'], 16, 16])
        secs.append([b'SCPS', 1, 0, scps, st['parts'], 4, 16])
        rc = scdd_compile.write_rc(b, secs)
        (o / 'room.r4rc').write_bytes(rc)
        rows.append((r, st['mesh_crc_in'], st['mesh_crc_out'], st['r4sg_bytes'], st['sccn_bytes'], st['scps_bytes'],
                     len(body), st['nonempty'], st['cones'], st['corners'], st['cone_corners']))
        for f in ('ps2-world.re4mesh', 'ps2-world.r4sg', 'room.r4rc'):
            sums.append('%s  %s/%s' % (hashlib.sha256((o / f).read_bytes()).hexdigest(), r, f))
    if not a.no_write:
        with open(out / 'MANIFEST-SC21.tsv', 'w') as f:
            f.write('room\tmesh_in\tmesh_out\tr4sg\tsccn\tscps\tscdd\tgroups\tcones\tcorners\tcone_range_corners\n')
            for x in rows:
                f.write('\t'.join(str(v) for v in x) + '\n')
        (out / 'SHA256SUMS').write_text('\n'.join(sums) + '\n')


if __name__ == '__main__':
    main()
