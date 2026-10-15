#!/usr/bin/env python3
"""ps2_world_far_lod.py IN.re4mesh OUT.re4mesh [--target 0.5] [--max-error-mm 150] [--uv-guard 0.002] [--report R.json]

Offline world distance LOD for a PS2 world package (R4IM v3, prelit; lane worldlod 2026-10-15, backlog C1).

Every LOD cluster gets one more level, the FAR level: its level-0 triangles simplified (mesh_lod quadric collapse, the
UV guard on, vertices shared with another cluster or part of the same mesh locked so neighbours never crack) until it
keeps at most --target of the triangles or the next collapse would move the surface more than --max-error-mm (model
units are source millimetres times the mesh scale; the error cap is in model units here, the PS2 world is unscaled).
The far level is written as indexed meshlets into its part's vertex pool (a QEM collapse keeps original positions, so
it adds strips and u16 tables, rarely vertices) and carries the marker error FAR_ERROR (1e30): the runtime's
screen-space selection never reaches it, so a build without the game knob WORLD_LOD draws exactly what it drew before.
With WORLD_LOD=1 (native_static.cpp) a cluster whose nearest point is beyond 12 m and whose screen-space choice is
level 0 draws its FAR level instead. The far plane is unchanged.

Everything else is copied: meshes, parts, the existing levels, vertex records (each part's pool keeps its order; a far
level's new corners, if any, follow its pool), palette, bounds. A cluster whose far level would not save at least
--min-saving of its level-0 triangles gets none. Run tools/ps2_strip_groups.py on the output afterwards when the room
ships strip groups (PS2_STRIP_GROUPS=1): it re-groups every meshlet, the far ones included.
"""
import argparse, json, math, struct, sys, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mesh_lod  # noqa: E402
import convert_room_bins as crb  # noqa: E402

HEADER = struct.Struct('<4s19I')
LOD_HEADER = struct.Struct('<8I')
MESH = struct.Struct('<HBBHHIII12f')
PART = struct.Struct('<IIBBBBII4f')
MESHLET = struct.Struct('<IIIHH6H')
VERTEX = struct.Struct('<6H')
PART_LOD = struct.Struct('<II')
CLUSTER = struct.Struct('<6HII')
LEVEL = struct.Struct('<IIf')
INDEXED = 0x8000
FAR_ERROR = 1.0e30
MAX_LET_VERTICES = 256


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def read(blob):
    h = HEADER.unpack_from(blob, 0)
    magic, version, nbytes, crc, nmesh, npart, nlet, nvert, nstrip, npal, o_mesh, o_part, o_let, o_vert, o_strip, \
        o_pal = h[:16]
    reserved = h[16:20]
    assert magic == b'R4IM' and version == 3 and nbytes == len(blob), (magic, version, nbytes, len(blob))
    assert reserved[0] == 2 and reserved[1:] == (0, 0, 0), ('prelit packages only', reserved)
    lod = LOD_HEADER.unpack_from(blob, 80)
    ncl, nlv, o_plod, o_cl, o_lv, o_class, o_rule, o_res = lod
    assert o_class == 0 and o_rule == 0 and o_res == 0, ('class / rule / impostor tables are not carried', lod)
    assert zlib.crc32(blob[80:]) == crc, 'header crc'
    p = dict(
        meshes=[list(MESH.unpack_from(blob, o_mesh + MESH.size * i)) for i in range(nmesh)],
        parts=[list(PART.unpack_from(blob, o_part + PART.size * i)) for i in range(npart)],
        lets=[list(MESHLET.unpack_from(blob, o_let + MESHLET.size * i)) for i in range(nlet)],
        verts=[VERTEX.unpack_from(blob, o_vert + VERTEX.size * i) for i in range(nvert)],
        strip=bytes(blob[o_strip:o_strip + nstrip]),
        pal=[struct.unpack_from('<I', blob, o_pal + 4 * i)[0] for i in range(npal)],
        plods=[list(PART_LOD.unpack_from(blob, o_plod + PART_LOD.size * i)) for i in range(npart)],
        clusters=[list(CLUSTER.unpack_from(blob, o_cl + CLUSTER.size * i)) for i in range(ncl)],
        levels=[list(LEVEL.unpack_from(blob, o_lv + LEVEL.size * i)) for i in range(nlv)])
    return p


def write(p):
    head = HEADER.size + LOD_HEADER.size
    body = bytearray()
    offsets = {}
    for name, blob in (('mesh', b''.join(MESH.pack(*m) for m in p['meshes'])),
                       ('part', b''.join(PART.pack(*x) for x in p['parts'])),
                       ('meshlet', b''.join(MESHLET.pack(*m) for m in p['lets'])),
                       ('vertex', b''.join(VERTEX.pack(*v) for v in p['verts'])),
                       ('index', bytes(p['strip'])),
                       ('palette', b''.join(struct.pack('<I', c) for c in p['pal'])),
                       ('part_lod', b''.join(PART_LOD.pack(*x) for x in p['plods'])),
                       ('cluster', b''.join(CLUSTER.pack(*c) for c in p['clusters'])),
                       ('level', b''.join(LEVEL.pack(*l) for l in p['levels']))):
        start = crb.align(head + len(body)) - head
        body.extend(b'\0' * (start - len(body)))
        offsets[name] = head + len(body)
        body.extend(blob)
    body.extend(b'\0' * (crb.align(head + len(body)) - head - len(body)))
    lod = LOD_HEADER.pack(len(p['clusters']), len(p['levels']), offsets['part_lod'], offsets['cluster'],
                          offsets['level'], 0, 0, 0)
    body = lod + bytes(body)
    total = HEADER.size + len(body)
    header = HEADER.pack(b'R4IM', 3, total, zlib.crc32(body), len(p['meshes']), len(p['parts']), len(p['lets']),
                         len(p['verts']), len(p['strip']), len(p['pal']), offsets['mesh'], offsets['part'],
                         offsets['meshlet'], offsets['vertex'], offsets['index'], offsets['palette'], 2, 0, 0, 0)
    return header + body


def let_corners(p, m):
    """-> (pool vertex index per local corner, [strip corner lists]) of meshlet record m."""
    first_vertex, first_strip, strip_bytes, nv, sc = m[0], m[1], m[2], m[3], m[4]
    s = p['strip']
    if sc & INDEXED:
        table = struct.unpack_from('<%dH' % nv, s, first_strip)
        corners = [first_vertex + o for o in table]
        at = first_strip + 2 * nv
    else:
        corners = [first_vertex + k for k in range(nv)]
        at = first_strip
    end = at + strip_bytes
    strips = []
    while at < end:
        n = s[at]
        strips.append(list(s[at + 1:at + 1 + n]))
        at += 1 + n
    assert len(strips) == (sc & (INDEXED - 1))
    return corners, strips


def part_pool(p, pi):
    """[lo, hi) of the vertex records part pi's meshlets read."""
    part = p['parts'][pi]
    lo, hi = None, None
    for li in range(part[6], part[6] + part[7]):
        corners, _ = let_corners(p, p['lets'][li])
        a, b = min(corners), max(corners) + 1
        lo = a if lo is None else min(lo, a)
        hi = b if hi is None else max(hi, b)
    return lo, hi


def far_level(p, pi, ci, locked_pos, mesh, a):
    """-> (tris kept, level-0 tris, error, [(key corners) triangles]) for cluster ci of part pi, or None."""
    part = p['parts'][pi]
    cl = p['clusters'][ci]
    lv0 = p['levels'][cl[6]]
    step, origin = mesh[11:14], mesh[8:11]
    uvb, uvs = part[8:10], part[10:12]
    pos, ids, tris = {}, {}, []
    for li in range(lv0[0], lv0[0] + lv0[1]):
        corners, strips = let_corners(p, p['lets'][li])
        for s in strips:
            for t in crb.strip_triangles(s):
                vs = [p['verts'][corners[k]] for k in t]
                g = [tuple(v[:3]) for v in vs]
                if len(set(g)) < 3:
                    continue
                for x in g:
                    if x not in ids:
                        ids[x] = len(ids)
                        pos[ids[x]] = tuple(origin[k] + step[k] * x[k] for k in range(3))
                attrs = tuple(((uvb[0] + uvs[0] * v[3], uvb[1] + uvs[1] * v[4]), None, v[5]) for v in vs)
                tris.append((tuple(ids[x] for x in g), attrs))
    if not tris:
        return None
    locked = {ids[x] for x in ids if x in locked_pos}
    s = mesh_lod.Simplifier(pos, tris, locked)
    goal = a.target * len(tris)
    eps, error, cur = a.start_error, 0.0, tris
    while eps <= a.max_error + 1e-6:
        s.run_to(eps)
        cur, error = s.triangles(), s.error
        if len(cur) <= goal:
            break
        eps *= 1.25
    if len(cur) > (1.0 - a.min_saving) * len(tris) or not cur:
        return None
    grid_of = {i: x for x, i in ids.items()}
    keyed = []
    for t in cur:
        k3 = []
        for v, (uv, _, colour) in zip(t[0], t[1]):
            qu = min(65535, max(0, round((uv[0] - uvb[0]) / uvs[0])))
            qv = min(65535, max(0, round((uv[1] - uvb[1]) / uvs[1])))
            k3.append((*grid_of[v], qu, qv, colour))
        keyed.append(tuple(k3))
    return len(cur), len(tris), error, keyed


def level_triangles(p, lv):
    out = []
    for li in range(lv[0], lv[0] + lv[1]):
        corners, strips = let_corners(p, p['lets'][li])
        for s in strips:
            out.append(tuple(tuple(p['verts'][corners[k]]) for k in s))
    return out


def verify(src_path, out_path):
    """Every cluster's source levels draw the same strips (vertex records in order) in OUT, the far level is last with
    the marker error, and nothing else changed: what a build without WORLD_LOD draws from OUT is what it drew from IN.
    Works on strip-grouped outputs too when IN is strip-grouped the same way (ps2_strip_groups.py is per meshlet)."""
    a, b = read(open(src_path, 'rb').read()), read(open(out_path, 'rb').read())
    assert [m[:6] + m[8:] for m in a['meshes']] == [m[:6] + m[8:] for m in b['meshes']]
    assert [x[:6] + x[8:] for x in a['parts']] == [x[:6] + x[8:] for x in b['parts']]
    assert a['pal'] == b['pal'] and len(a['clusters']) == len(b['clusters'])
    far = same = 0
    for ca, cb in zip(a['clusters'], b['clusters']):
        assert ca[:6] == cb[:6] and cb[7] in (ca[7], ca[7] + 1)
        for k in range(ca[7]):
            la, lb = a['levels'][ca[6] + k], b['levels'][cb[6] + k]
            assert la[2] == lb[2] and la[1] == lb[1]
            assert level_triangles(a, la) == level_triangles(b, lb), ('level differs', ca, k)
            same += 1
        if cb[7] == ca[7] + 1:
            assert b['levels'][cb[6] + ca[7]][2] >= 1e29
            far += 1
    print('VERIFY OK clusters=%d source_levels_identical=%d far_levels=%d' % (len(a['clusters']), same, far))


def main():
    if len(sys.argv) == 4 and sys.argv[1] == '--verify':
        verify(sys.argv[2], sys.argv[3])
        return
    ap = argparse.ArgumentParser()
    ap.add_argument('mesh'); ap.add_argument('out')
    ap.add_argument('--target', type=float, default=0.5, help='keep at most this share of a cluster\'s triangles')
    ap.add_argument('--max-error-mm', dest='max_error', type=float, default=150.0)
    ap.add_argument('--start-error-mm', dest='start_error', type=float, default=4.0)
    ap.add_argument('--min-saving', type=float, default=0.2)
    ap.add_argument('--uv-guard', type=float, default=0.002)
    ap.add_argument('--report')
    a = ap.parse_args()
    mesh_lod.UV_GUARD = a.uv_guard if a.uv_guard > 0 else None
    src = read(open(a.mesh, 'rb').read())
    # vertex pools: ascending, disjoint, covering the records in order
    pools = [part_pool(src, pi) for pi in range(len(src['parts']))]
    prev = 0
    for lo, hi in pools:
        assert lo == prev, ('vertex pools are not contiguous', lo, prev)
        prev = hi
    assert prev == len(src['verts'])
    # part -> mesh; grid positions shared by two clusters (any part) of one mesh are locked
    part_mesh = {}
    for mi, m in enumerate(src['meshes']):
        for pi in range(m[6], m[6] + m[7]):
            part_mesh[pi] = mi
    owners = {}
    for pi, (fc, cc) in enumerate(src['plods']):
        mi = part_mesh[pi]
        for ci in range(fc, fc + cc):
            lv0 = src['levels'][src['clusters'][ci][6]]
            for li in range(lv0[0], lv0[0] + lv0[1]):
                corners, _ = let_corners(src, src['lets'][li])
                for c in corners:
                    owners.setdefault((mi, src['verts'][c][:3]), set()).add(ci)
    locked_by_mesh = {}
    for (mi, g), cs in owners.items():
        if len(cs) > 1:
            locked_by_mesh.setdefault(mi, set()).add(g)

    out = dict(meshes=[list(m) for m in src['meshes']], parts=[], lets=[], verts=[], strip=bytearray(),
               pal=list(src['pal']), plods=[], clusters=[], levels=[])
    rows = []
    tot = dict(clusters=0, far_clusters=0, l0_tris=0, far_tris=0, l0_far_tris=0, new_vertices=0, far_meshlets=0)
    for pi, part in enumerate(src['parts']):
        lo, hi = pools[pi]
        mi = part_mesh[pi]
        new_lo = len(out['verts'])
        out['verts'].extend(src['verts'][lo:hi])
        pool = {}
        for k in range(lo, hi):
            pool.setdefault(tuple(src['verts'][k]), k - lo)
        let_map = {}
        first_let = len(out['lets'])
        # the part's own meshlets, copied (re-based on the new pool and strip offsets)
        for li in range(part[6], part[6] + part[7]):
            m = src['lets'][li]
            ix = m[4] & INDEXED
            table = 2 * m[3] if ix else 0
            if len(out['strip']) & 1:
                out['strip'].append(0)
            start = len(out['strip'])
            out['strip'].extend(src['strip'][m[1]:m[1] + table + m[2]])
            fv = new_lo + (m[0] - lo)
            let_map[li] = len(out['lets'])
            out['lets'].append([fv, start] + list(m[2:]))
        fresh = []
        far_lets = {}
        fc, cc = src['plods'][pi]
        for ci in range(fc, fc + cc):
            tot['clusters'] += 1
            r = far_level(src, pi, ci, locked_by_mesh.get(mi, set()), src['meshes'][mi], a)
            l0 = src['levels'][src['clusters'][ci][6]]
            l0_tris = sum(len(s) - 2 for li in range(l0[0], l0[0] + l0[1])
                          for s in let_corners(src, src['lets'][li])[1])
            tot['l0_tris'] += l0_tris
            if r is None:
                tot['far_tris'] += l0_tris
                rows.append(dict(part=pi, cluster=ci, l0=l0_tris, far=None))
                continue
            kept, n0, err, keyed = r
            strips = [c for s in mesh_lod.stripify(keyed) for c in crb.split_strip(s) if len(c) >= 3]
            packed = mesh_lod.pack_meshlets(strips, MAX_LET_VERTICES, lambda k: k[:3])
            recs = []
            for chunk in packed:
                keys = list(dict.fromkeys(c for s in chunk for c in s))
                local = {c: i for i, c in enumerate(keys)}
                offs = []
                for c in keys:
                    if c not in pool:
                        pool[c] = (hi - lo) + len(fresh)
                        fresh.append(c)
                    offs.append(pool[c])
                if len(out['strip']) & 1:
                    out['strip'].append(0)
                first_index = len(out['strip'])
                out['strip'].extend(struct.pack('<%dH' % len(keys), *offs))
                strip_start = len(out['strip'])
                for s in chunk:
                    out['strip'].append(len(s))
                    out['strip'].extend(local[c] for c in s)
                g = [c[:3] for c in keys]
                recs.append([new_lo, first_index, len(out['strip']) - strip_start, len(keys), len(chunk) | INDEXED,
                             *[min(q[x] for q in g) for x in range(3)], *[max(q[x] for q in g) for x in range(3)]])
            far_lets[ci] = recs
            tot['far_clusters'] += 1
            tot['far_tris'] += kept
            tot['l0_far_tris'] += n0
            tot['far_meshlets'] += len(recs)
            rows.append(dict(part=pi, cluster=ci, l0=n0, far=kept, error=round(err, 2), meshlets=len(recs)))
        # far meshlets after the part's own, inside its meshlet range
        far_first = {}
        for ci in range(fc, fc + cc):
            if ci in far_lets:
                far_first[ci] = len(out['lets'])
                out['lets'].extend(far_lets[ci])
        out['verts'].extend(fresh)
        tot['new_vertices'] += len(fresh)
        assert len(out['verts']) - new_lo <= 65536, 'part pool over 65536 vertices'
        out['parts'].append([part[0], part[1], part[2], part[3], part[4], part[5], first_let,
                             len(out['lets']) - first_let] + list(part[8:12]))
        out['plods'].append([len(out['clusters']), cc])
        for ci in range(fc, fc + cc):
            c = src['clusters'][ci]
            first_level = len(out['levels'])
            for k in range(c[6], c[6] + c[7]):
                lv = src['levels'][k]
                # own meshlets are copied in order, so a level (even an empty one at the range end) moves by the same base
                assert part[6] <= lv[0] <= part[6] + part[7] and lv[0] + lv[1] <= part[6] + part[7]
                out['levels'].append([first_let + (lv[0] - part[6]), lv[1], lv[2]])
            if ci in far_lets:
                out['levels'].append([far_first[ci], len(far_lets[ci]), f32(FAR_ERROR)])
            out['clusters'].append(list(c[:6]) + [first_level, len(out['levels']) - first_level])
    blob = write(out)
    open(a.out, 'wb').write(blob)
    in_bytes = len(open(a.mesh, 'rb').read())
    summary = dict(input=a.mesh, output=a.out, bytes_in=in_bytes, bytes_out=len(blob), growth=len(blob) - in_bytes,
                   target=a.target, max_error_mm=a.max_error, uv_guard=a.uv_guard, min_saving=a.min_saving, **tot,
                   far_share=round(tot['far_tris'] / max(1, tot['l0_tris']), 3),
                   far_share_of_reduced=round(tot['far_tris'] - (tot['l0_tris'] - tot['l0_far_tris']), 0) /
                   max(1, tot['l0_far_tris']))
    print(json.dumps(summary, indent=1))
    if a.report:
        json.dump(dict(summary=summary, clusters=rows), open(a.report, 'w'), indent=1)


if __name__ == '__main__':
    main()
