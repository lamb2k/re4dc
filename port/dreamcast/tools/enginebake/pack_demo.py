#!/usr/bin/env python3
"""edemo18: pack the standalone KOS stress demo's data file (EDEMO.PAK). Private output, never git.

Inputs
  --edcl     baked clips of em12 (bake_clips.py output, EDCL v1)
  --grid     r101 grid.bin (build_grid.py output, EDGR v1)
  --mesh     mesh.json of a PS2 Ganado LOD rung (repeat: g70, g50, g33 in that order); every rung shares
             the em12:440 skeleton (34 bones) and the atlas
  --atlas    the appearance's atlas.dt (DcTx 32-byte header + PVR VQ RGB565 512x512 payload)

Sections ('EDPK', u32 count, count x {tag[4], u32 offset, u32 size}; every section 32-byte aligned):
  SKEL  u32 n; n x {s32 parent, f32 rest[3], f32 inv_bind[16] (column-major)}
  MSHk  u32 nv, nidx, nstrip, nrun, nchunk; f32 pos[nv][3] (bind, model space, mm); f32 uv[nv][2];
        u8 b0[nv], b1[nv], w0[nv] (w0/255 on b0, the rest on b1; b0 = dominant bone);
        pad4; u16 strip_len[nstrip]; u16 idx[nidx]; pad4; run {u16 count, u8 b0, u8 b1}[nrun];
        chunk {u16 vertex_end, strip_end, run_end, pad}[nchunk]
        (chunks of <= CHUNK_NEW new vertices in strip order; inside a chunk vertices are sorted by (b0, b1) and a
        run is a maximal (b0, b1) span)
  CLIP  u32 n; n x {u32 offset (from the section start), u16 frames, u16 role}; then the EDCL clips
        role 0 walk, 1 attack, 2 idle, 3 run
  GRID  EDGR v1 as written by build_grid.py
  TEXR  u16 w, h, u32 pvr format word; PVR VQ payload (codebook 2048 B + twiddled indices)
  MISC  f32 arena centre x, z (mm), f32 arena radius (mm)
"""
import argparse
import json
import math
import struct
import sys

# ------------------------------------------------------------- EDCL decode (mirrors the runtime)


def dq48(b):
    word = int.from_bytes(b, 'little')
    i = word >> 45
    lim = 1 / math.sqrt(2)
    enc = [(word >> 30) & 0x7FFF, (word >> 15) & 0x7FFF, word & 0x7FFF]
    vals = [e / 32767 * 2 * lim - lim for e in enc]
    big = math.sqrt(max(0.0, 1 - sum(v * v for v in vals)))
    it = iter(vals)
    return tuple(big if k == i else next(it) for k in range(4))


def parse_clip(d, ofs, rest):
    nf, n, _ = struct.unpack_from('<HBB', d, ofs)
    p = ofs + 4
    parts = []
    scaled = [False]
    for i in range(n):
        fl = d[p]; p += 1
        rs = not (fl & 1)
        rshift = (fl >> 3) & 3
        tshift = (fl >> 5) & 3
        nk_r = 1 if rs else ((nf - 1) + (1 << rshift) - 1 >> rshift) + 1
        rq = [dq48(d[p + 6 * k:p + 6 * k + 6]) for k in range(nk_r)]
        p += 6 * nk_r
        tmode = fl & 6
        if tmode == 0:
            tk = [rest[i]]
        else:
            sc, = struct.unpack_from('<f', d, p); p += 4
            nk_t = 1 if tmode == 2 else ((nf - 1) + (1 << tshift) - 1 >> tshift) + 1
            tk = [tuple(v * sc for v in struct.unpack_from('<3h', d, p + 6 * k)) for k in range(nk_t)]
            p += 6 * nk_t
        if fl & 0x80:
            p += 6 * nf
            scaled[0] = True
        parts.append((rshift, rq, tshift, tk))
    p = (p + 3) & ~3
    rsc, = struct.unpack_from('<f', d, p); p += 4
    root = []
    for f in range(nf):
        v = struct.unpack_from('<3h3h', d, p); p += 12
        root.append((v[0] * rsc, v[1] * rsc, v[2] * rsc))
    return nf, parts, root, p - ofs, scaled[0]


def track_at(shift, keys, f, nf, lerp):
    if len(keys) == 1:
        return keys[0]
    k = min(f >> shift, len(keys) - 2)
    a, b = min(k << shift, nf - 1), min((k + 1) << shift, nf - 1)
    t = 0.0 if a == b else (f - a) / (b - a)
    return lerp(keys[k], keys[k + 1], t)


def qlerp(a, b, t):
    if sum(x * y for x, y in zip(a, b)) < 0:
        b = tuple(-v for v in b)
    q = tuple(x + (y - x) * t for x, y in zip(a, b))
    n = math.sqrt(sum(v * v for v in q))
    return tuple(v / n for v in q)


def vlerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def qmat(q, t):
    x, y, z, w = q
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), t[0]],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), t[1]],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), t[2]]]


def mmul(a, b):
    return [[a[r][0] * b[0][c] + a[r][1] * b[1][c] + a[r][2] * b[2][c] + (a[r][3] if c == 3 else 0) for c in range(4)] for r in range(3)]


def fk(parents, parts, f, nf):
    out = []
    for i, (rs, rq, ts, tk) in enumerate(parts):
        l = qmat(track_at(rs, rq, f, nf, qlerp), track_at(ts, tk, f, nf, vlerp))
        out.append(l if parents[i] < 0 else mmul(out[parents[i]], l))
    return out


# ------------------------------------------------------------- mesh


def stripify(tris):
    """Greedy strips over (a, b, c) index triples (culling off: winding is free)."""
    from collections import defaultdict
    edge = defaultdict(list)
    for t, (a, b, c) in enumerate(tris):
        for e in ((a, b), (b, c), (c, a)):
            edge[frozenset(e)].append(t)
    used = [False] * len(tris)
    deg = [sum(len(edge[frozenset(e)]) - 1 for e in ((a, b), (b, c), (c, a))) for (a, b, c) in tris]
    order = sorted(range(len(tris)), key=lambda t: deg[t])
    strips = []
    for t0 in order:
        if used[t0]:
            continue
        used[t0] = True
        a, b, c = tris[t0]
        best = None
        for s in ((a, b, c), (b, c, a), (c, a, b)):
            strip = list(s)
            while True:
                nxt = None
                for t in edge[frozenset((strip[-2], strip[-1]))]:
                    if not used[t]:
                        nxt = t
                        break
                if nxt is None:
                    break
                third = [v for v in tris[nxt] if v not in (strip[-2], strip[-1])]
                if len(third) != 1:
                    break
                used[nxt] = True
                strip.append(third[0])
            best = strip
            break
        strips.append(best)
    return strips


CHUNK_NEW = 160


def pack_mesh(mesh, nbones):
    pos = mesh['positions_mm']
    weights = mesh['weights']
    corners = {}
    verts = []
    tris = []
    for t in mesh['triangles']:
        idx = []
        for c in t['corners']:
            key = (c['vertex'], round(c['uv'][0], 6), round(c['uv'][1], 6))
            if key not in corners:
                corners[key] = len(verts)
                w = sorted(weights[c['vertex']], key=lambda bw: -bw[1])
                b0, w0 = w[0]
                b1, w1 = (w[1] if len(w) > 1 else (b0, 0.0))
                tot = w0 + w1
                verts.append((pos[c['vertex']], c['uv'], b0, b1 if w1 > 0 else b0, w0 / tot if tot else 1.0))
            idx.append(corners[key])
        if len(set(idx)) == 3:
            tris.append(tuple(idx))
    # chunks ("meshlets" for the D-cache): strips in strip order, closed when the chunk would add more than
    # CHUNK_NEW vertices not used by an earlier chunk; each chunk's new vertices are numbered consecutively,
    # sorted by (b0, b1) inside the chunk, so a chunk is skinned (bone runs) then submitted while its vertex
    # images (32 B each) are still in the operand cache
    strips0 = stripify(tris)
    chunks = []          # (strip list, new vertex list)
    seen = set()
    cur, cur_new = [], []
    for st in strips0:
        new = [v for v in dict.fromkeys(st) if v not in seen and v not in cur_new]
        if cur and len(cur_new) + len(new) > CHUNK_NEW:
            chunks.append((cur, cur_new)); cur, cur_new = [], []
            new = [v for v in dict.fromkeys(st) if v not in seen]
        cur.append(st); cur_new += new; seen.update(new)
    if cur:
        chunks.append((cur, cur_new))
    remap = {}
    order = []
    for _, nv in chunks:
        for v in sorted(nv, key=lambda v: (verts[v][2], verts[v][3])):
            remap[v] = len(order); order.append(v)
    verts = [verts[o] for o in order]
    strips = []
    runs = []
    ctab = []
    vbase = 0
    for cs, nv in chunks:
        for st in cs:
            strips.append([remap[v] for v in st])
        for v in verts[vbase:vbase + len(nv)]:
            k = (v[2], v[3])
            if runs and runs[-1][1] == k and len(ctab) == runs[-1][2]:
                runs[-1][0] += 1
            else:
                runs.append([1, k, len(ctab)])
        vbase += len(nv)
        ctab.append((vbase, len(strips), len(runs)))
    nidx = sum(len(s) for s in strips)
    out = bytearray(struct.pack('<5I', len(verts), nidx, len(strips), len(runs), len(ctab)))
    for v in verts:
        out += struct.pack('<3f', *v[0])
    for v in verts:
        out += struct.pack('<2f', *v[1])
    out += bytes(v[2] for v in verts) + bytes(v[3] for v in verts) + bytes(max(0, min(255, int(round(v[4] * 255)))) for v in verts)
    while len(out) % 4:
        out.append(0)
    out += struct.pack(f'<{len(strips)}H', *[len(s) for s in strips])
    out += struct.pack(f'<{nidx}H', *[i for s in strips for i in s])
    while len(out) % 4:
        out.append(0)
    for c, (b0, b1), _ in runs:
        out += struct.pack('<HBB', c, b0, b1)
    for vend, send, rend in ctab:
        out += struct.pack('<HHHH', vend, send, rend, 0)
    info = dict(vertices=len(verts), positions=len(pos), triangles=len(tris), strips=len(strips), strip_vertices=nidx,
                runs=len(runs), chunks=len(ctab), two_bone_vertices=sum(1 for v in verts if v[2] != v[3]))
    return bytes(out), info


def inv_affine(m):
    """4x4 row-major affine inverse -> row-major."""
    r = [[m[j][i] for j in range(3)] for i in range(3)]   # transpose of rotation (assumes orthonormal * uniform)
    # general 3x3 inverse for safety
    a = [row[:3] for row in m[:3]]
    det = (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
           + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    inv = [[(a[(c + 1) % 3][(r_ + 1) % 3] * a[(c + 2) % 3][(r_ + 2) % 3] - a[(c + 1) % 3][(r_ + 2) % 3] * a[(c + 2) % 3][(r_ + 1) % 3]) / det
            for c in range(3)] for r_ in range(3)]
    t = [m[0][3], m[1][3], m[2][3]]
    it = [-(inv[i][0] * t[0] + inv[i][1] * t[1] + inv[i][2] * t[2]) for i in range(3)]
    del r
    return [inv[0] + [it[0]], inv[1] + [it[1]], inv[2] + [it[2]], [0, 0, 0, 1]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--edcl', required=True)
    ap.add_argument('--grid', required=True)
    ap.add_argument('--mesh', action='append', required=True)
    ap.add_argument('--atlas', required=True)
    ap.add_argument('--skeleton-drs', required=True)
    ap.add_argument('--motion-root', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--report', required=True)
    a = ap.parse_args()
    sys.path.insert(0, a.motion_root + '/tools')
    from motion import archive, modelbin
    model = modelbin.parse(archive.Archive(a.skeleton_drs).entry(440).data)
    parents = [p.parent for p in model.parts]
    rest = [p.pos for p in model.parts]
    nb = len(parents)
    meshes = [json.load(open(m)) for m in a.mesh]
    # inverse bind from the mesh's bone rest matrices (model space, row-major 4x4)
    bones = meshes[0]['bones']
    assert len(bones) == nb, (len(bones), nb)
    skel = bytearray(struct.pack('<I', nb))
    for i, b in enumerate(bones):
        inv = inv_affine(b['rest'])
        col = [inv[r][c] for c in range(4) for r in range(4)]
        skel += struct.pack('<i3f16f', parents[i], *rest[i], *col)
    # clips: classify by root speed and right-hand motion
    d = open(a.edcl, 'rb').read()
    magic, ver, count = struct.unpack_from('<4sHH', d, 0)
    assert magic == b'EDCL'
    table = [struct.unpack_from('<HHI', d, 8 + 8 * k) for k in range(count)]
    ends = [t[2] for t in table[1:]] + [len(d)]
    cands = []
    for (ent, nf, ofs), end in zip(table, ends):
        nfr, parts, root, size, scaled = parse_clip(d, ofs, rest)
        assert nfr == nf
        if nf < 20 or scaled:
            continue
        sp = [math.hypot(root[f + 1][0] - root[f][0], root[f + 1][2] - root[f][2]) for f in range(nf - 1)]
        mean = sum(sp) / len(sp)
        var = sum((s - mean) ** 2 for s in sp) / len(sp)
        hands = [fk(parents, parts, f, nf)[16] for f in range(0, nf)]
        hv = max(math.dist((hands[f + 1][0][3], hands[f + 1][1][3], hands[f + 1][2][3]), (hands[f][0][3], hands[f][1][3], hands[f][2][3])) for f in range(nf - 1))
        cands.append(dict(entry=ent, frames=nf, speed=mean, speed_sd=math.sqrt(var), hand_peak=hv, ofs=ofs, size=end - ofs))
    walk = min((c for c in cands if 12 <= c['speed'] <= 40 and c['frames'] <= 120), key=lambda c: c['speed_sd'] / c['speed'])
    run = min((c for c in cands if 45 <= c['speed'] <= 120 and c['frames'] <= 90), key=lambda c: c['speed_sd'] / c['speed'], default=walk)
    attack = max((c for c in cands if c['speed'] < 8 and 30 <= c['frames'] <= 100), key=lambda c: c['hand_peak'] if c['hand_peak'] <= 150 else 0)
    idle = min((c for c in cands if c['frames'] >= 40), key=lambda c: c['hand_peak'] + c['speed'] * 10)
    roles = [(walk, 0), (attack, 1), (idle, 2), (run, 3)]
    clip = bytearray(struct.pack('<I', len(roles)))
    hdr = 4 + 8 * len(roles)
    body = bytearray()
    for c, role in roles:
        clip += struct.pack('<IHH', hdr + len(body), c['frames'], role)
        body += d[c['ofs']:c['ofs'] + c['size']]
    clip += body
    # meshes
    mesh_secs = []
    infos = []
    for m in meshes:
        b, info = pack_mesh(m, nb)
        mesh_secs.append(b)
        infos.append(info)
    grid = open(a.grid, 'rb').read()
    # arena: the walkable cell with the most walkable cells (and no walls) within 7 m
    W, H = struct.unpack_from('<HH', grid, 4)
    gx0, gz0 = struct.unpack_from('<ff', grid, 8)
    C, = struct.unpack_from('<H', grid, 16)
    cells = [struct.unpack_from('<BBBBH', grid, 24 + 6 * i) for i in range(W * H)]
    R = 7
    best = None
    for cz in range(R, H - R):
        for cx in range(R, W - R):
            ok = 0
            for dz in range(-R, R + 1):
                for dx in range(-R, R + 1):
                    if dx * dx + dz * dz <= R * R:
                        c = cells[(cx + dx) + (cz + dz) * W]
                        ok += (c[0] != 0xFF) and c[1] == 0
            if best is None or ok > best[0]:
                best = (ok, cx, cz)
    arena = (gx0 + (best[1] + 0.5) * C, gz0 + (best[2] + 0.5) * C, R * C)
    misc = struct.pack('<3f', *arena)
    atlas = open(a.atlas, 'rb').read()
    assert atlas[:4] == b'DcTx'
    tex = struct.pack('<HHI', 512, 512, 0) + atlas[32:]
    secs = [(b'SKEL', bytes(skel)), (b'CLIP', bytes(clip)), (b'GRID', grid), (b'TEXR', tex), (b'MISC', misc)]
    secs += [(b'MSH' + bytes([48 + k]), s) for k, s in enumerate(mesh_secs)]
    head = 8 + 12 * len(secs)
    ofs = (head + 31) & ~31
    table = b''
    blob = b''
    for tag, s in secs:
        table += struct.pack('<4sII', tag, ofs + len(blob), len(s))
        blob += s
        while (ofs + len(blob)) % 32:
            blob += b'\0'
    out = struct.pack('<4sI', b'EDPK', len(secs)) + table
    out += b'\0' * (ofs - len(out)) + blob
    open(a.out, 'wb').write(out)
    rep = dict(bytes=len(out), sections={t.decode(): len(s) for t, s in secs}, meshes=dict(zip(a.mesh, infos)),
               clips={r: {k: v for k, v in c.items() if k not in ('ofs',)} for c, r in roles}, arena_mm=arena, arena_free_cells=best[0])
    json.dump(rep, open(a.report, 'w'), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == '__main__':
    main()
