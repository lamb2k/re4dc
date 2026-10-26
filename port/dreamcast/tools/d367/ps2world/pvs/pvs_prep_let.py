#!/usr/bin/env python3
"""Meshlet-level PVS census, step 1 (lane vis-census26, 2026-10-26): pvs_prep.py with one row per level-0 meshlet.

usage (Windows Python with numpy): pvs_prep_let.py <package dir> <room hex> <work dir>

Same inputs, flags and dynamic / sky / appended-placement rules as pvs_prep.py, but an instance is one level-0 meshlet
of a (placement, part, cluster), numbered in that walk order. pvs_cast (build / ceil) and pvs_emit work on it unchanged.
inst.tsv columns: inst placement field part cluster pass cull dyn lo_x lo_y lo_z hi_x hi_y hi_z verts0 tris0 let
(the meshlet's world box; verts0 = its corner count). clusters.tsv: per cluster instance (placement, cluster, first
meshlet inst, meshlet count, per level corner totals) for the LOD model in census.py.
"""
import json, os, struct, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'interior'))
from r4im import Pkg  # noqa: E402

DYN_OCC = os.environ.get('PVS_DYN_OCCLUDE') == '1'


def main():
    pkg_dir, room, work = Path(sys.argv[1]), int(sys.argv[2], 16), Path(sys.argv[3])
    work.mkdir(parents=True, exist_ok=True)
    p = Pkg(pkg_dir / 'ps2-world.re4mesh', pkg_dir / 'ps2-world.r4pw')
    ids_path = pkg_dir / 'ps2-world.ids'
    dyn_field = set()
    if ids_path.exists():
        b = ids_path.read_bytes()
        magic, ver, count, crc = struct.unpack_from('<4sIII', b, 0)
        if magic == b'R4ID' and count == len(p.placements):  # runtime checks a policy-source crc; count is enough here
            idv = b[16:16 + count]
            seen = {}
            for v in idv:
                seen[v] = seen.get(v, 0) + 1
            dyn_field = {f for f, v in enumerate(idv) if v < 250 and seen[v] == 1}
        else:
            print('warning: ids file does not match the sidecar; no dynamic placements')
    sky_rows = {0x100: {2, 3, 75, 33, 34, 35, 36, 37}, 0x101: {0, 1, 2}}.get(room, set())
    base_places = None
    app = pkg_dir / 'append.json'
    if app.exists():
        base_places = json.loads(app.read_text())['base_placements']
    rows, crow, tris, inst = [], [], [], 0
    for pi, pl in enumerate(p.placements):
        mesh = p.meshes[pl['mesh']]
        M = p.wq(pl)
        dyn = pl['placement'] in dyn_field or (base_places is not None and pi >= base_places) or pl['placement'] in sky_rows
        scale = float(np.sqrt((pl['affine'][:, :3] ** 2).sum(0).max()))
        for k in range(mesh['part_count']):
            part = mesh['first_part'] + k
            fc, cc = p.plod[part]
            meta = p.pmeta[part]
            occ = meta['pass_'] == 0 and (not dyn or (DYN_OCC and pl['placement'] not in sky_rows))
            flags = (1 if occ else 0) | (2 if meta['cull'] == 0 else 0) | (4 if meta['pass_'] == 0 else 0)  # 4: opaque (ground / indoor tests)
            for c in range(fc, fc + cc):
                cl = p.clusters[c]
                fm, mc, _ = p.levels[cl['first_level']]
                first = inst
                lv = []
                for l in range(cl['level_count']):
                    a, n, err = p.levels[cl['first_level'] + l]
                    lv.append((sum(p.lets[li]['vc'] for li in range(a, a + n)), float(err)))
                for li in range(fm, fm + mc):
                    L = p.lets[li]
                    corners, tl = p.let_tris(li)
                    w = corners[:, :3].astype(np.float64) @ M[:, :3].T + M[:, 3]
                    lo, hi = p.world_aabb(M, L['bmin'], L['bmax'])
                    if tl:
                        t = w[np.array(tl, dtype=np.int64)]
                        tris.append((t.astype(np.float32), inst, flags))
                    rows.append([inst, pi, pl['placement'], part, c, meta['pass_'], meta['cull'], int(dyn)] +
                                [round(float(x), 1) for x in lo] + [round(float(x), 1) for x in hi] +
                                [L['vc'], len(tl), li])
                    inst += 1
                g0, g1 = p.world_aabb(M, cl['bmin'], cl['bmax'])
                crow.append([pi, c, first, inst - first, round(scale, 5)] + [round(float(x), 1) for x in g0] +
                            [round(float(x), 1) for x in g1] + ['%d:%g' % v for v in lv])
    n = sum(len(t) for t, _, _ in tris)
    rec = np.zeros(n, dtype=[('v', '<f4', (9,)), ('inst', '<u4'), ('flags', '<u4')])
    at = 0
    for t, i, f in tris:
        rec['v'][at:at + len(t)] = t.reshape(-1, 9); rec['inst'][at:at + len(t)] = i; rec['flags'][at:at + len(t)] = f
        at += len(t)
    with open(work / 'tris.bin', 'wb') as f:
        f.write(struct.pack('<I', n)); f.write(rec.tobytes())
    with open(work / 'inst.tsv', 'w') as f:
        f.write('inst\tplacement\tfield\tpart\tcluster\tpass\tcull\tdyn\tlo_x\tlo_y\tlo_z\thi_x\thi_y\thi_z\tverts0\ttris0\tlet\n')
        for r in rows:
            f.write('\t'.join(str(x) for x in r) + '\n')
    with open(work / 'clusters.tsv', 'w') as f:
        f.write('placement\tcluster\tfirst\tcount\tscale\tlo_x\tlo_y\tlo_z\thi_x\thi_y\thi_z\tlevels(corners:err)\n')
        for r in crow:
            f.write('\t'.join(str(x) for x in r) + '\n')
    meta = dict(room=room, mesh_crc=p.mesh_crc, mesh_bytes=p.mesh_bytes, sidecar_crc=p.sidecar_crc,
                placements=len(p.placements), instances=inst, clusters=len(crow), triangles=n,
                occluder_triangles=int((rec['flags'] & 1).sum()),
                dynamic_placements=sorted({r[1] for r in rows if r[7]}), dyn_occlude=DYN_OCC)
    (work / 'meta.json').write_text(json.dumps(meta, indent=1))
    print('room %03x: %d placements, %d clusters, %d meshlets, %d triangles (%d occluders), %d dynamic placements' % (
        room, len(p.placements), len(crow), inst, n, meta['occluder_triangles'], len(meta['dynamic_placements'])))


if __name__ == '__main__':
    main()
