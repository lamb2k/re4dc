#!/usr/bin/env python3
"""PS2_PVS step 1 (lane t2exact, 2026-10-15): export a PS2 world package for the offline visibility caster.

usage (Windows Python with numpy): pvs_prep.py <package dir> <room hex> <work dir>
  package dir: ps2-world.re4mesh + ps2-world.r4pw (+ ps2-world.ids, optional)

Instances: every (placement, part, cluster) of the package in the runtime's order (placement array order, the mesh's
parts in order, each part's clusters in order: native_static.cpp pvs::open counts the same way), numbered from 0.
This instance numbering is the PVS's (and lane worldlod's) cluster id format: docs/lanes/t2exact.md "PVS format".

Writes into <work dir>:
  inst.tsv   inst placement placement_field part cluster pass cull dyn lo_x lo_y lo_z hi_x hi_y hi_z verts0 tris0 maxerr
             m0..m11 (world-from-grid 3x4) g0x..g1z (the cluster's grid box)
  tris.bin   u32 N, N x {float a[3], b[3], c[3]; u32 inst; u32 flags}  level-0 triangles in world mm;
             flags bit 0 = occluder (opaque pass 0 of a static placement), bit 1 = two-sided (part cull 0)
  meta.json  package crcs / sizes, counts, world box
A sky row (ps2_sky_row), a dynamic placement (a unique id in ps2-world.ids: the runtime may move or hide it) and the placements appended after
the base package (PS2_PLACE_GATE baked objects: an object can stop drawing them) never occlude; the caster marks them
visible from every cell. Translucent (pass 2) and punch-through (pass 1) triangles never occlude either.
"""
import json, os, struct, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'interior'))
from r4im import Pkg  # noqa: E402


# PVS_DYN_OCCLUDE=1 (ceiling measurement only): dynamic placements occlude too, at their baked positions
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
        assert magic == b'R4ID' and ver == 1 and crc == p.sidecar_crc, 'ids file does not match the package'
        idv = b[16:16 + count]
        seen = {}
        for v in idv:
            seen[v] = seen.get(v, 0) + 1
        dyn_field = {f for f, v in enumerate(idv) if v < 250 and seen[v] == 1}
    # sky / backdrop rows (native_static.cpp ps2_sky_row: drawn to the projection far with SKY_FAR): always visible,
    # never occluders
    sky_rows = {0x100: {2, 3, 75, 33, 34, 35, 36, 37}, 0x101: {0, 1, 2}}.get(room, set())
    base_places = None
    app = pkg_dir / 'append.json'
    if app.exists():
        base_places = json.loads(app.read_text())['base_placements']
    rows, tris, inst = [], [], 0
    lo_all, hi_all = np.full(3, 1e30), np.full(3, -1e30)
    for pi, pl in enumerate(p.placements):
        mesh = p.meshes[pl['mesh']]
        M = p.wq(pl)
        dyn = pl['placement'] in dyn_field or (base_places is not None and pi >= base_places) or pl['placement'] in sky_rows
        for k in range(mesh['part_count']):
            part = mesh['first_part'] + k
            fc, cc = p.plod[part]
            meta = p.pmeta[part]
            for c in range(fc, fc + cc):
                cl = p.clusters[c]
                lo, hi = p.world_aabb(M, cl['bmin'], cl['bmax'])
                t = p.cluster_tris_world(pi, c, 0)
                fm, mc, _ = p.levels[cl['first_level']]
                nv = sum(p.lets[li]['vc'] for li in range(fm, fm + mc))
                occ = meta['pass_'] == 0 and (not dyn or (DYN_OCC and pl['placement'] not in sky_rows))
                flags = (1 if occ else 0) | (2 if meta['cull'] == 0 else 0)
                if len(t):
                    tris.append((t.astype(np.float32), inst, flags))
                    lo_all = np.minimum(lo_all, t.reshape(-1, 3).min(0)); hi_all = np.maximum(hi_all, t.reshape(-1, 3).max(0))
                maxerr = max(p.levels[cl['first_level'] + l][2] for l in range(cl['level_count']))
                rows.append([inst, pi, pl['placement'], part, c, meta['pass_'], meta['cull'], int(dyn)] +
                            [round(float(x), 1) for x in lo] + [round(float(x), 1) for x in hi] +
                            [nv, len(t), round(float(maxerr), 2)] + ['%.9g' % x for x in M.reshape(-1)] +
                            list(cl['bmin']) + list(cl['bmax']))
                inst += 1
    n = sum(len(t) for t, _, _ in tris)
    rec = np.zeros(n, dtype=[('v', '<f4', (9,)), ('inst', '<u4'), ('flags', '<u4')])
    at = 0
    for t, i, f in tris:
        rec['v'][at:at + len(t)] = t.reshape(-1, 9); rec['inst'][at:at + len(t)] = i; rec['flags'][at:at + len(t)] = f
        at += len(t)
    with open(work / 'tris.bin', 'wb') as f:
        f.write(struct.pack('<I', n)); f.write(rec.tobytes())
    with open(work / 'inst.tsv', 'w') as f:
        f.write('inst\tplacement\tfield\tpart\tcluster\tpass\tcull\tdyn\tlo_x\tlo_y\tlo_z\thi_x\thi_y\thi_z\tverts0\ttris0\tmaxerr\t' + '\t'.join('m%d' % i for i in range(12)) +
                '\tg0x\tg0y\tg0z\tg1x\tg1y\tg1z\n')
        for r in rows:
            f.write('\t'.join(str(x) for x in r) + '\n')
    meta = dict(room=room, mesh_crc=p.mesh_crc, mesh_bytes=p.mesh_bytes, sidecar_crc=p.sidecar_crc,
                placements=len(p.placements), instances=inst, triangles=n,
                occluder_triangles=int((rec['flags'] & 1).sum()), dynamic_placements=sorted(
                    {r[1] for r in rows if r[7]}), world_lo=lo_all.tolist(), world_hi=hi_all.tolist())
    (work / 'meta.json').write_text(json.dumps(meta, indent=1))
    print('room %03x: %d placements, %d instances, %d triangles (%d occluders), %d dynamic placements, box %s .. %s' % (
        room, len(p.placements), inst, n, meta['occluder_triangles'], len(meta['dynamic_placements']),
        [int(x) for x in lo_all], [int(x) for x in hi_all]))


if __name__ == '__main__':
    main()
