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
import hashlib, json, os, struct, sys, zlib
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
    assert p.magic==b'R4IM' and p.version==3 and len(p.m)==p.mesh_bytes
    assert zlib.crc32(p.m[80:]) == p.mesh_crc, 'mesh payload CRC mismatch'
    effective_policy = (pkg_dir / 'ps2-world.r4pw').read_bytes()
    assert zlib.crc32(effective_policy[32:]) == p.sidecar_crc, 'policy payload CRC mismatch'
    state_policy_sha=hashlib.sha256(effective_policy).hexdigest()
    ids_path = pkg_dir / 'ps2-world.ids'
    dyn_field = set()
    if ids_path.exists():
        b = ids_path.read_bytes()
        magic, ver, count, crc = struct.unpack_from('<4sIII', b, 0)
        assert magic == b'R4ID' and ver == 1, 'invalid ids file'
        if crc != p.sidecar_crc:
            # Scoped texture keys change R4PW identity, but cannot change source
            # placement/state classification. Require the original authenticated
            # policy rather than silently trusting an unrelated ids file.
            assert '--original-policy' in sys.argv, 'ids mismatch: supply --original-policy'
            original = Path(sys.argv[sys.argv.index('--original-policy') + 1])
            op = Pkg(pkg_dir / 'ps2-world.re4mesh', original)
            assert op.sidecar_crc == crc, 'ids does not bind original policy'
            original_policy = original.read_bytes()
            state_policy_sha=hashlib.sha256(original_policy).hexdigest()
            assert zlib.crc32(original_policy[32:]) == op.sidecar_crc, 'original payload CRC mismatch'
            def normalized_policy(data):
                data=bytearray(data);data[20:24]=bytes(4)
                for part in range(len(p.pmeta)):data[32+16*part:40+16*part]=bytes(8)
                return bytes(data)
            assert normalized_policy(original_policy)==normalized_policy(effective_policy), 'policy bytes changed outside texture keys and payload CRC'
            assert len(op.placements) == len(p.placements) and len(op.pmeta) == len(p.pmeta)
            assert all(a['mesh'] == b['mesh'] and a['placement'] == b['placement'] and
                       np.array_equal(a['affine'], b['affine']) for a, b in zip(op.placements, p.placements)), 'placement change'
            assert all(all(a[k] == b[k] for k in ('w', 'h', 'pass_', 'cull'))
                       for a, b in zip(op.pmeta, p.pmeta)), 'non-key material change'
        assert count == len(p.placements) and 16 + count <= len(b), 'ids count mismatch'
        idv = b[16:16 + count]
        seen = {}
        for v in idv:
            seen[v] = seen.get(v, 0) + 1
        dyn_field = {f for f, v in enumerate(idv) if v < 250 and seen[v] == 1}
    # sky / backdrop rows (native_static.cpp ps2_sky_row: drawn to the projection far with SKY_FAR): always visible,
    # never occluders
    sky_rows = {0x100: {2, 3, 75, 33, 34, 35, 36, 37}, 0x101: {0, 1, 2}}.get(room, set())
    # Absence of append metadata is not proof that no objects were appended.
    # A conversion report for this exact original package can establish that
    # the entire input is a base package; otherwise no placement may occlude.
    base_places = 0
    static_provenance = None
    app = pkg_dir / 'append.json'
    if app.exists():
        report=json.loads(app.read_text());base_places=report['base_placements']
        assert type(base_places) is int and 0<=base_places<=len(p.placements), 'invalid base placements'
        assert report['r4pw_sha256']==state_policy_sha and report['r4pw_bytes']==len(effective_policy), 'append report policy mismatch'
        static_provenance=dict(kind='append-report',name='append.json',base_placements=base_places)
    else:
        base_report=pkg_dir/'base-report.json'
        if base_report.exists():
            report=json.loads(base_report.read_text())
            assert report['re4mesh_sha256']==hashlib.sha256(p.m).hexdigest() and report['r4pw_sha256']==state_policy_sha, 'base report package mismatch'
            assert report['placements']==len(p.placements) and report['groups']==len(p.placements), 'base report count mismatch'
            base_places=len(p.placements)
            static_provenance=dict(kind='base-conversion-report',name='base-report.json',base_placements=base_places)
    static_qualified=ids_path.exists() and static_provenance is not None
    rows, tris, inst = [], [], 0
    lo_all, hi_all = np.full(3, 1e30), np.full(3, -1e30)
    for pi, pl in enumerate(p.placements):
        mesh = p.meshes[pl['mesh']]
        M = p.wq(pl)
        dyn = not static_qualified or pl['placement'] in dyn_field or pi >= base_places or pl['placement'] in sky_rows
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
    meta['input_hashes']={name:hashlib.sha256((pkg_dir/name).read_bytes()).hexdigest()
                          for name in ('ps2-world.re4mesh','ps2-world.r4pw','ps2-world.ids','append.json','base-report.json')
                          if (pkg_dir/name).exists()}
    meta['static_qualified']=static_qualified
    meta['static_provenance']=static_provenance
    meta['prepared_hashes']={name:hashlib.sha256((work/name).read_bytes()).hexdigest() for name in ('inst.tsv','tris.bin')}
    if '--original-policy' in sys.argv:
        meta['original_policy_sha256']=hashlib.sha256(Path(sys.argv[sys.argv.index('--original-policy')+1]).read_bytes()).hexdigest()
    (work / 'meta.json').write_text(json.dumps(meta, indent=1))
    print('room %03x: %d placements, %d instances, %d triangles (%d occluders), %d dynamic placements, box %s .. %s' % (
        room, len(p.placements), inst, n, meta['occluder_triangles'], len(meta['dynamic_placements']),
        [int(x) for x in lo_all], [int(x) for x in hi_all]))


if __name__ == '__main__':
    main()
