#!/usr/bin/env python3
"""ps2leon arm A (PS2_LEON=1): the full PS2 Leon as an approved render mesh (re4dc-approved-render-mesh-1), the input
of pack_coarse_actor.py and the cl lane's fastpath, like today's leon-hair-v2 mesh.json.

  build_arm_a.py <out dir>      writes <out>/mesh.json and <out>/report-a.json

Geometry: the eight PS2 pl00 / wep02 sections at the GC roles' arcs (leon_sources.ROLES), every triangle of the PS2
strips except zero-area strip joints; positions in the GC model space (the PS2 vertices coincide with the GC ones).
Normals: the PS2 corner normals. UVs: PS2 raw / 256 (the GC UV layout: equal at every coincident corner; ps2_bin's
/255 is JADERLINK's approximation) mapped into today's 512 atlas tiles (build_leon_4k.py: the GC images; the PS2
images are the same pictures, the face at half width), so the atlas, its texture key, VRAM and the charbake
variants stay as they are. Hair: PS2 draws all 691 hair triangles with one colour image (GC image 0 = runtime hair
material 1, ac381b1a) and its alpha (the same mask); each corner also carries src_uv, its UV in the hair image.
Weights: the PS2 weights where the PS2 bone is the GC bone (same id, parent and rest: body, role 2, face, head,
hands). The jacket's cloth bones (PS2 69-75) and the hair bones (PS2 64, 66-68) are not the GC skeleton's (the
game animates GC bones 86-110 for the jacket, 65-83 for the hair), so those two sections take the weights of the
nearest GC vertex of the same section (82 % of the PS2 hair vertices and most jacket vertices sit on a GC vertex).
Skeleton, bones, bind matrices, source signatures: today's (mesh.json bones, leon-source.json).
"""
import hashlib, json, sys
from collections import Counter
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import leon_sources as ls  # noqa: E402

TILES = json.loads((ls.PROTO / 'deliverables/leon-4k/asset-report.json').read_text())['source_uv_tiles']
TILE = {k.replace('SourceTex_', ''): t for k, t in TILES.items()}
# PS2 material (texture index of the section's TPL) -> GC image key (today's atlas tile). PS2 texture k of TPL 0x005
# is GC image k; the face / head TPL 0x007 image 2 is the GC face (image 4); hair image 0 is GC hair colour 0.
PS2_KEY = {
    0: {0: '1f625c95-7aed4809', 2: '23f6b950-9ea131c1', 3: '15f7e18c-11dc93e0', 7: '2a8a368f-76c02b02'},
    1: {3: '15f7e18c-11dc93e0', 5: '878b23c0-e7038833'},
    2: {0: '1f625c95-7aed4809'},
    3: {2: 'dde6f32a-0b7cfdcf'},
    4: {2: 'dde6f32a-0b7cfdcf'},
    5: {0: 'cd026c6d-3a54bfa9'},
    6: {0: 'cd026c6d-3a54bfa9'},
    7: {0: 'ac381b1a-3ade84b1'},
}
HAIR_MATERIAL = {'ac381b1a-3ade84b1': 1, '7a9de1fd-0e415f15': 2}   # runtime materials 1 / 2 (owner_leon hair_colours)
TRANSFER = {1, 7}   # sections whose PS2 bones are not the GC skeleton's


def atlas_uv(key, u, v):
    """GC-convention UV (v down) in image `key` -> mesh.json atlas UV (export_coarse_actor: (u, 1 - v_blender))."""
    t = TILE[key]
    return [(t['x'] + 2 + u * t['inner_width']) / 512.0, 1.0 - (t['y'] + 2 + (1.0 - v) * t['inner_height']) / 512.0]


def nearest_index(a, b):
    out = np.empty(len(a), int); dist = np.empty(len(a))
    for i in range(0, len(a), 256):
        d = ((a[i:i + 256, None, :] - b[None, :, :]) ** 2).sum(-1)
        out[i:i + 256] = d.argmin(1); dist[i:i + 256] = np.sqrt(d.min(1))
    return out, dist


def closest_on_triangles(p, A, B, C):
    """distance from each point p to the nearest triangle (A, B, C arrays) - the standard region test, vectorized."""
    best = np.full(len(p), np.inf)
    for i in range(0, len(p), 64):
        q = p[i:i + 64, None, :]
        ab, ac, ap = B - A, C - A, q - A
        d1, d2 = (ab * ap).sum(-1), (ac * ap).sum(-1)
        bp = q - B; d3, d4 = (ab * bp).sum(-1), (ac * bp).sum(-1)
        cp = q - C; d5, d6 = (ab * cp).sum(-1), (ac * cp).sum(-1)
        va = d3 * d6 - d5 * d4; vb = d5 * d2 - d1 * d6; vc = d1 * d4 - d3 * d2
        den = va + vb + vc
        den = np.where(np.abs(den) < 1e-20, 1e-20, den)
        v = vb / den; w = vc / den
        proj = A + ab * v[..., None] + ac * w[..., None]
        # outside the face: fall back to the nearest of the three edges (clamped segments)
        def seg(P0, P1):
            d = P1 - P0; t = np.clip(((q - P0) * d).sum(-1) / np.maximum((d * d).sum(-1), 1e-20), 0, 1)
            return P0 + d * t[..., None]
        inside = (va >= 0) & (vb >= 0) & (vc >= 0)
        cand = [np.where(inside[..., None], proj, seg(A, B)), seg(B, C), seg(C, A)]
        dist = np.min([np.linalg.norm(q - c, axis=-1) for c in cand], axis=0)
        best[i:i + 64] = dist.min(1)
    return best


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    today = ls.leon_mesh()
    parents, _ = ls.gc_skeleton()
    regions = ls.bone_regions(parents)
    positions, weights, triangles = [], [], []
    rep = dict(roles=[])
    for role in range(8):
        p = ls.ps2_role(role)
        g = ls.gc_role(role)
        gpos = g['positions']
        vid = {}
        tris_in = len(p['tris'])
        dropped = 0
        corners_all = []
        for mat, cs in p['tris']:
            P = np.asarray([c['p'] for c in cs], float)
            if np.linalg.norm(np.cross(P[1] - P[0], P[2] - P[0])) < 1e-6:
                dropped += 1
                continue
            corners_all.append((mat, cs))
        # weights: PS2 (shared bones) or the nearest GC vertex of the same section
        uniq = sorted({tuple(np.round(c['p'], 4)) for _, cs in corners_all for c in cs})
        upos = np.asarray(uniq, float)
        transfer = {}
        tstats = None
        if role in TRANSFER:
            idx, dist = nearest_index(upos, gpos)
            surf = closest_on_triangles(upos, gpos[g['tris'][:, 0]], gpos[g['tris'][:, 1]], gpos[g['tris'][:, 2]])
            for k, key in enumerate(uniq):
                transfer[key] = tuple((int(b), float(w)) for b, w in g['weights'][idx[k]])
            tstats = dict(vertices=len(uniq), on_gc_vertex=int((dist < .05).sum()), nearest_vertex_mm_median=float(np.median(dist)),
                          nearest_vertex_mm_p95=float(np.percentile(dist, 95)), nearest_vertex_mm_max=float(dist.max()),
                          gc_surface_mm_median=float(np.median(surf)), gc_surface_mm_p95=float(np.percentile(surf, 95)),
                          gc_surface_mm_max=float(surf.max()))
        else:
            surf = closest_on_triangles(upos, gpos[g['tris'][:, 0]], gpos[g['tris'][:, 1]], gpos[g['tris'][:, 2]])
            tstats = dict(vertices=len(uniq), gc_surface_mm_median=float(np.median(surf)), gc_surface_mm_p95=float(np.percentile(surf, 95)),
                          gc_surface_mm_max=float(surf.max()))
        mats = Counter()
        regs = Counter()
        for node, cs in corners_all:
            key = PS2_KEY[role][p['bin'].materials[node]['diffuse']]   # ps2_bin.triangles: (node, corners); one material per node
            mats[key] += 1
            tc = []
            cw = []
            for c in cs:
                pk = tuple(np.round(c['p'], 4))
                w = transfer[pk] if role in TRANSFER else tuple((int(b), float(x)) for b, x in c['w'])
                w = tuple(sorted(w, key=lambda bw: -bw[1])[:3])
                s = sum(x for _, x in w)
                w = tuple(sorted((b, x / s) for b, x in w))
                vk = (pk, w)
                if vk not in vid:
                    vid[vk] = len(positions)
                    positions.append([float(x) for x in c['p']])
                    weights.append([[b, x] for b, x in w])
                cw.append(w)
                u, v = c['raw']['uv'][0] / 256.0, c['raw']['uv'][1] / 256.0
                corner = dict(vertex=vid[vk], normal=[float(x) for x in c['n']], uv=atlas_uv(key, u, v))
                if role == 7:
                    corner['src_uv'] = [u, v]
                tc.append(corner)
            t = dict(source_info=role, corners=tc)
            if role == 7:
                t['material'] = HAIR_MATERIAL[key]
            triangles.append(t)
            regs[ls.triangle_region(cw, regions)] += 1
        row = dict(role=role, name=ls.ROLES[role][2], ps2_triangles=tris_in, zero_area_dropped=dropped,
                   triangles=tris_in - dropped, vertices=len({v for (pk, w), v in vid.items()}), unique_positions=len(uniq),
                   images=dict(mats), regions=dict(regs), weights='nearest GC vertex' if role in TRANSFER else 'PS2', check=tstats)
        rep['roles'].append(row)
        print(json.dumps(row))
    mesh = {
        'schema': 're4dc-approved-render-mesh-1',
        'blend_sha256': None,
        'source_sha256': today['source_sha256'],
        'mesh': 'Leon_PS2_A_RenderMesh',
        'positions_mm': positions, 'weights': weights, 'bones': today['bones'], 'triangles': triangles,
        'source_info_counts': {str(i): sum(t['source_info'] == i for t in triangles) for i in range(8)},
        'policy': 'ps2leon arm A: PS2 pl00 geometry on the GC skeleton; render only. Source info visibility remains separate.',
    }
    text = json.dumps(mesh, separators=(',', ':'))
    (out / 'mesh.json').write_text(text)
    rep.update(triangles=len(triangles), vertices=len(positions), mesh_sha256=hashlib.sha256(text.encode()).hexdigest(),
               regions=dict(sum((Counter(r['regions']) for r in rep['roles']), Counter())))
    (out / 'report-a.json').write_text(json.dumps(rep, indent=1))
    print('ARM_A', rep['triangles'], 'triangles', rep['vertices'], 'vertices', rep['regions'])


if __name__ == '__main__':
    main()
