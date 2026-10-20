#!/usr/bin/env python3
"""DC world v1 (lane scenery19, DC_WORLD): a room's PS2 world package re-cut into a few large world-space chunks.

Input: a room's dc/native/<room>/ps2-world.{re4mesh,r4pw,ids} (R4IM v3 + R4PW v1 + R4ID v1).
Output: the same three files (same formats, so today's loader and draw path read them), where
  - every static placement's geometry is pre-transformed into world space (millimetres) and merged across placements
    and parts into one mesh per XZ cell (--cell mm): one part per material run (texture key, pass, cull, vertex-alpha
    flag) in the cell, drawn by one identity placement per cell;
  - each source cluster is carried over with all its LOD levels (level error times the placement's scale), its meshlets
    re-encoded on the cell's grid (positions), the part's UV range (UV) and the source colour word (unchanged);
  - placements that can move (an id used once in ps2-world.ids, id < 250: PS2_WORLD_DYNAMIC) keep their source mesh,
    affine, placement field and id, so the dynamic path still drives them.
The R4TC translucency classes are carried over per part (--r4tc). Strip groups (r4sg) and the room file (OCCL) are rebuilt by
dcw_room.sh (ps2_strip_groups.py, room_compile.py). Approximation: UV and positions are re-quantised (16 bit).

Usage: dcworld_build.py <in room dir> <out dir> [--cell 20000]
"""
import argparse, collections, json, math, struct, zlib
from pathlib import Path

HEADER = struct.Struct('<4s19I')
LOD_HEADER = struct.Struct('<8I')
MESH = struct.Struct('<HBBHHIII12f')
PART = struct.Struct('<IIBBBBII4f')
MESHLET = struct.Struct('<IIIHH6H')
VERTEX = struct.Struct('<6H')
PART_LOD = struct.Struct('<II')
CLUSTER = struct.Struct('<6HII')
LEVEL = struct.Struct('<IIf')
PS2PART = struct.Struct('<IIHHBBBB')
PLACE = struct.Struct('<HH12f')
K_IDS = 250


def align32(n):
    return (n + 31) & ~31


class Src:
    def __init__(self, d, r4tc=None):
        d = Path(d)
        m = (d / 'ps2-world.re4mesh').read_bytes()
        p = (d / 'ps2-world.r4pw').read_bytes()
        self.m = m
        h = HEADER.unpack_from(m, 0)
        self.h = h
        (_, self.version, _, _, nmesh, npart, nlet, nvert, nidx, npal, o_mesh, o_part, o_let, o_vert, o_idx, o_pal,
         self.color_mode) = h[:17]
        self.o_vert, self.o_idx, self.o_pal, self.npal = o_vert, o_idx, o_pal, npal
        ncl, nlv, o_plod, o_cl, o_lv = LOD_HEADER.unpack_from(m, 80)[:5]
        self.meshes = [MESH.unpack_from(m, o_mesh + 68 * i) for i in range(nmesh)]
        self.parts = [PART.unpack_from(m, o_part + 36 * i) for i in range(npart)]
        self.lets = [MESHLET.unpack_from(m, o_let + 28 * i) for i in range(nlet)]
        self.plod = [PART_LOD.unpack_from(m, o_plod + 8 * i) for i in range(npart)]
        self.clusters = [CLUSTER.unpack_from(m, o_cl + 20 * i) for i in range(ncl)]
        self.levels = [LEVEL.unpack_from(m, o_lv + 12 * i) for i in range(nlv)]
        hp = struct.unpack_from('<4s7I', p, 0)
        assert hp[0] == b'R4PW' and hp[1] == 1
        nplace, nparts = hp[2], hp[3]
        self.pmeta = [PS2PART.unpack_from(p, 32 + 16 * i) for i in range(nparts)]
        base = 32 + 16 * nparts
        self.placements = [PLACE.unpack_from(p, base + 52 * i) for i in range(nplace)]
        self.ids = None
        q = d / 'ps2-world.ids'
        if q.exists():
            b = q.read_bytes()
            mg, ver, count, crc = struct.unpack_from('<4sIII', b, 0)
            if mg == b'R4ID' and ver == 1 and count == nplace and crc == hp[5]:
                self.ids = b[16:16 + count]
        self.tc = None
        q = Path(r4tc) if r4tc else d / 'ps2-world.r4tc'
        if q.exists():
            b = q.read_bytes()
            mg, ver, clsf, parts, pwcrc, bcrc = struct.unpack_from('<4s5I', b, 0)
            if mg == b'R4TC' and ver == 1 and parts == nparts and pwcrc == hp[5]:
                self.tc, self.tc_classifier = b[24:24 + parts], clsf

    def let_corners(self, li):
        """(corners as raw 6-tuples in strip-index order, strip bytes, strip count)."""
        fv, fs, sb, vc, sc = self.lets[li][:5]
        s = self.o_idx + fs
        if sc & 0x8000:
            off = struct.unpack_from('<%dH' % vc, self.m, s)
            s += 2 * vc
        else:
            off = range(vc)
        corners = [VERTEX.unpack_from(self.m, self.o_vert + 12 * (fv + o)) for o in off]
        return corners, self.m[s:s + sb], sc & 0x7FFF


def mat_mul(A, G):
    return [[sum(A[r][k] * G[k][c] for k in range(3)) + (A[r][3] if c == 3 else 0.0) for c in range(4)] for r in range(3)]


def build(src, cell, keep=()):
    nplace = len(src.placements)
    dynamic = set()
    if src.ids is not None:
        cnt = collections.Counter(src.ids)
        dynamic = {i for i, v in enumerate(src.ids) if v < K_IDS and cnt[v] == 1}
    dynamic |= {i for i in keep if i < nplace}
    assert all(src.placements[i][1] == i for i in range(nplace)), 'placement field != index'
    # ---- gather static clusters into (cell, material) runs ----
    runs = collections.OrderedDict()      # (cell, material) -> list of (M, scale, part, cluster)
    for pi, pl in enumerate(src.placements):
        if pi in dynamic:
            continue
        mi = pl[0]
        A = [list(pl[2 + 4 * r:6 + 4 * r]) for r in range(3)]
        mesh = src.meshes[mi]
        org, step = mesh[8:11], mesh[11:14]
        G = [[step[0], 0, 0, org[0]], [0, step[1], 0, org[1]], [0, 0, step[2], org[2]]]
        M = mat_mul(A, G)
        scale = max(math.sqrt(sum(A[r][c] ** 2 for r in range(3))) for c in range(3))
        det = (A[0][0] * (A[1][1] * A[2][2] - A[1][2] * A[2][1]) - A[0][1] * (A[1][0] * A[2][2] - A[1][2] * A[2][0])
               + A[0][2] * (A[1][0] * A[2][1] - A[1][1] * A[2][0]))
        for k in range(mesh[7]):
            part = mesh[6] + k
            pm = list(src.pmeta[part])
            if det < 0 and pm[5]:
                pm[5] = 3 - pm[5]          # mirrored: the front face swaps
            rp = src.parts[part]
            material = tuple(pm) + (rp[2], rp[3], rp[4])
            fc, cc = src.plod[part]
            for c in range(fc, fc + cc):
                cl = src.clusters[c]
                ctr = [(cl[a] + cl[3 + a]) * 0.5 for a in range(3)]
                w = [sum(M[r][a] * ctr[a] for a in range(3)) + M[r][3] for r in range(3)]
                key = (int(w[0] // cell), int(w[2] // cell))
                runs.setdefault((key, material), []).append((M, scale, part, c))
    cells = sorted({k[0] for k in runs})
    # ---- output tables ----
    meshes, parts, plods, clusters, levels, lets, verts, idx, pmeta, places, ids_out, part_src, cell_meshes = ([] for _ in range(13))

    def transform(M, q):
        return [M[r][0] * q[0] + M[r][1] * q[1] + M[r][2] * q[2] + M[r][3] for r in range(3)]

    for ck in cells:
        mats = [(k[1], v) for k, v in runs.items() if k[0] == ck]
        # pass 1: world bounds of the cell (every level's corners)
        lo, hi = [math.inf] * 3, [-math.inf] * 3
        cache = {}
        for material, items in mats:
            for M, scale, part, c in items:
                cl = src.clusters[c]
                for lv in range(cl[6], cl[6] + cl[7]):
                    fm, mc, _ = src.levels[lv]
                    for li in range(fm, fm + mc):
                        corners, sb, sc = src.let_corners(li)
                        wc = [transform(M, q) for q in corners]
                        cache[(id(M), li)] = (corners, sb, sc, wc)
                        for w in wc:
                            for a in range(3):
                                lo[a] = min(lo[a], w[a]); hi[a] = max(hi[a], w[a])
        lo = [struct.unpack('<f', struct.pack('<f', x))[0] for x in lo]
        step = [max((hi[a] - lo[a]) / 65535.0, 1e-6) for a in range(3)]
        step = [struct.unpack('<f', struct.pack('<f', x))[0] for x in step]

        def grid(w):
            return [min(65535, max(0, round((w[a] - lo[a]) / step[a]))) for a in range(3)]
        first_part = len(parts)
        for material, items in mats:
            # the run's UV range (float UV of every corner)
            ulo, uhi = [math.inf] * 2, [-math.inf] * 2
            for M, scale, part, c in items:
                rp = src.parts[part]
                cl = src.clusters[c]
                for lv in range(cl[6], cl[6] + cl[7]):
                    fm, mc, _ = src.levels[lv]
                    for li in range(fm, fm + mc):
                        for q in cache[(id(M), li)][0]:
                            for a in range(2):
                                u = rp[8 + a] + q[3 + a] * rp[10 + a]
                                ulo[a] = min(ulo[a], u); uhi[a] = max(uhi[a], u)
            ulo = [struct.unpack('<f', struct.pack('<f', x))[0] for x in ulo]
            us = [struct.unpack('<f', struct.pack('<f', max((uhi[a] - ulo[a]) / 65535.0, 1e-9)))[0] for a in range(2)]
            first_cluster = len(clusters)
            first_let_part = len(lets)
            for M, scale, part, c in items:
                rp = src.parts[part]
                cl = src.clusters[c]
                first_level = len(levels)
                cmin, cmax = [65535] * 3, [0] * 3
                for lv in range(cl[6], cl[6] + cl[7]):
                    fm, mc, err = src.levels[lv]
                    first_let = len(lets)
                    for li in range(fm, fm + mc):
                        corners, sb, sc, wc = cache[(id(M), li)]
                        fv = len(verts)
                        g = [grid(w) for w in wc]
                        for q, gg in zip(corners, g):
                            uv = []
                            for a in range(2):
                                u = rp[8 + a] + q[3 + a] * rp[10 + a]
                                uv.append(min(65535, max(0, round((u - ulo[a]) / us[a]))))
                            verts.append((gg[0], gg[1], gg[2], uv[0], uv[1], q[5]))
                        bmin = [min(x[a] for x in g) for a in range(3)]
                        bmax = [max(x[a] for x in g) for a in range(3)]
                        for a in range(3):
                            cmin[a] = min(cmin[a], bmin[a]); cmax[a] = max(cmax[a], bmax[a])
                        lets.append((fv, len(idx), len(sb), len(corners), sc, *bmin, *bmax))
                        idx.extend(sb)
                    levels.append((first_let, len(lets) - first_let, float(err) * scale))
                clusters.append((*cmin, *cmax, first_level, len(levels) - first_level))
            pm = material[:8]
            rp0 = src.parts[items[0][2]]
            parts.append((rp0[0], rp0[1], material[8], material[9], material[10], 0, first_let_part,
                          len(lets) - first_let_part, ulo[0], ulo[1], us[0], us[1]))
            plods.append((first_cluster, len(clusters) - first_cluster))
            pmeta.append(pm)
            part_src.append(items[0][2])
        hi_q = [lo[a] + 65535 * step[a] for a in range(3)]
        meshes.append((len(meshes), 0, 0x50, 0, len(parts) - first_part, 0, first_part, len(parts) - first_part,
                       *lo, *step, *lo, *hi_q))
        cell_meshes.append(len(meshes) - 1)
    # ---- dynamic placements: their source mesh copied whole ----
    copied, kept = {}, {}
    for pi in sorted(dynamic):
        pl = src.placements[pi]
        mi = pl[0]
        if mi not in copied:
            mesh = src.meshes[mi]
            first_part = len(parts)
            for k in range(mesh[7]):
                part = mesh[6] + k
                rp = src.parts[part]
                first_cluster = len(clusters)
                first_let_part = len(lets)
                fc, cc = src.plod[part]
                for c in range(fc, fc + cc):
                    cl = src.clusters[c]
                    first_level = len(levels)
                    for lv in range(cl[6], cl[6] + cl[7]):
                        fm, mc, err = src.levels[lv]
                        first_let = len(lets)
                        for li in range(fm, fm + mc):
                            corners, sb, sc = src.let_corners(li)
                            l = src.lets[li]
                            fv = len(verts)
                            verts.extend(corners)
                            lets.append((fv, len(idx), len(sb), len(corners), sc, *l[5:11]))
                            idx.extend(sb)
                        levels.append((first_let, len(lets) - first_let, err))
                    clusters.append((*cl[:6], first_level, len(levels) - first_level))
                parts.append(tuple(rp[:6]) + (first_let_part, len(lets) - first_let_part) + tuple(rp[8:12]))
                plods.append((first_cluster, len(clusters) - first_cluster))
                pmeta.append(src.pmeta[part])
                part_src.append(part)
            m = src.meshes[mi]
            meshes.append((len(meshes),) + tuple(m[1:6]) + (first_part, len(parts) - first_part) + tuple(m[8:]))
            copied[mi] = len(meshes) - 1
        kept[pi] = (copied[mi], pl[1]) + tuple(pl[2:])
    # ---- placements: every source field keeps its index (dyn ids, sky rows, gates and owners address placements by
    # field); kept placements at their own field, cell meshes in the first free fields, the rest an empty mesh ----
    empty = len(meshes)
    meshes.append((empty, 0, 0x50, 0, 0, 0, len(parts), 0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    free = [i for i in range(nplace) if i not in kept]
    if len(free) < len(cell_meshes):
        raise SystemExit('more cells than free placement fields')
    ident = (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    slot = {f: m for f, m in zip(free, cell_meshes)}
    for i in range(nplace):
        if i in kept:
            places.append(kept[i]); ids_out.append(src.ids[i] if src.ids is not None else 0xFF)
        else:
            places.append((slot.get(i, empty), i) + ident); ids_out.append(0xFF)
    # ---- write R4IM ----
    head = HEADER.size + LOD_HEADER.size
    body = bytearray()
    offs = {}
    pal = src.m[src.o_pal:src.o_pal + 4 * src.npal]
    for name, blob in (('mesh', b''.join(MESH.pack(*x) for x in meshes)),
                       ('part', b''.join(PART.pack(*x) for x in parts)),
                       ('meshlet', b''.join(MESHLET.pack(*x) for x in lets)),
                       ('vertex', b''.join(VERTEX.pack(*x) for x in verts)),
                       ('index', bytes(idx)),
                       ('palette', pal),
                       ('part_lod', b''.join(PART_LOD.pack(*x) for x in plods)),
                       ('cluster', b''.join(CLUSTER.pack(*x) for x in clusters)),
                       ('level', b''.join(LEVEL.pack(*x) for x in levels))):
        start = align32(head + len(body)) - head
        body.extend(b'\0' * (start - len(body)))
        offs[name] = head + len(body)
        body.extend(blob)
    body.extend(b'\0' * (align32(head + len(body)) - head - len(body)))
    lod = LOD_HEADER.pack(len(clusters), len(levels), offs['part_lod'], offs['cluster'], offs['level'], 0, 0, 0)
    body = lod + bytes(body)
    total = HEADER.size + len(body)
    header = HEADER.pack(b'R4IM', src.version, total, zlib.crc32(body), len(meshes), len(parts), len(lets), len(verts),
                         len(idx), src.npal, offs['mesh'], offs['part'], offs['meshlet'], offs['vertex'], offs['index'],
                         offs['palette'], src.color_mode, 0, 0, 0)
    mesh_blob = header + body
    pbody = b''.join(PS2PART.pack(*x) for x in pmeta) + b''.join(PLACE.pack(*x) for x in places)
    pcrc = zlib.crc32(pbody) & 0xFFFFFFFF
    side = struct.pack('<4s7I', b'R4PW', 1, len(places), len(pmeta), len(meshes), pcrc, 0, 0) + pbody
    ids = struct.pack('<4sIII', b'R4ID', 1, len(places), pcrc) + bytes(ids_out)
    ids += b'\xff' * (align32(len(ids)) - len(ids))
    tc = None
    if src.tc is not None:
        cls = bytes(src.tc[i] for i in part_src)
        tc = struct.pack('<4s5I', b'R4TC', 1, src.tc_classifier, len(cls), pcrc, zlib.crc32(cls) & 0xFFFFFFFF) + cls
        tc += bytes(-len(tc) % 4)
    stats = dict(cells=len(cells), static_runs=len(runs), dynamic_placements=len(dynamic), placements=len(places),
                 meshes=len(meshes), parts=len(parts), clusters=len(clusters), meshlets=len(lets), vertices=len(verts),
                 re4mesh_bytes=len(mesh_blob), src_placements=nplace, src_parts=len(src.parts),
                 src_re4mesh_bytes=len(src.m))
    return mesh_blob, side, ids, tc, stats


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--cell', type=float, default=20000.0)
    ap.add_argument('--keep', default='', help='placement fields kept on their source mesh (sky rows, baked objects), '
                    'besides the dynamic ids: comma list, e.g. 0,1,2,209,210')
    ap.add_argument('--r4tc', type=Path, help='source package R4TC sidecar (default <src>/ps2-world.r4tc)')
    a = ap.parse_args()
    src = Src(a.src, a.r4tc)
    keep = [int(x, 0) for x in a.keep.split(',') if x] if a.keep else []
    mesh_blob, side, ids, tc, stats = build(src, a.cell, keep)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'ps2-world.re4mesh').write_bytes(mesh_blob)
    (a.out / 'ps2-world.r4pw').write_bytes(side)
    (a.out / 'ps2-world.ids').write_bytes(ids)
    if tc is not None:
        (a.out / 'ps2-world.r4tc').write_bytes(tc)
    stats['r4tc'] = tc is not None
    stats['cell'] = a.cell
    (a.out / 'dcworld.json').write_text(json.dumps(stats, indent=1))
    print(json.dumps(stats))


if __name__ == '__main__':
    main()
