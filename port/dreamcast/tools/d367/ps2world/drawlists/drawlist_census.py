#!/usr/bin/env python3
"""Offline feasibility census for camera-keyed world draw decisions.

Uses existing R4IM readers and historical camera samples with current assets.
Float64 geometric enumeration is a proxy, not the runtime's conservative view-AABB
and crossed-plane implementation, SH-4 bit-exact validation, or a speed test.
No game files are modified. Only immutable opaque placements are candidates.
"""
import argparse
import collections
import hashlib
import json
import math
import struct
import sys
import zlib
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--reader-dir', required=True)
    ap.add_argument('--package', required=True)
    ap.add_argument('--cameras', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--lod-px', type=float, default=3)
    a = ap.parse_args()
    sys.path.insert(0, a.reader_dir)
    from r4im import Pkg

    d = Path(a.package)
    mesh = d / 'ps2-wv5.re4mesh'
    side = d / 'ps2-world.r4pw'
    ids_path = d / 'ps2-world.ids'
    group_path = d / 'ps2-wv5.r4sg'
    p = Pkg(mesh, side)
    idblob = ids_path.read_bytes()
    idmagic, idversion, idcount, idcrc = struct.unpack_from('<4s3I', idblob)
    assert (idmagic, idversion, idcount, idcrc) == (b'R4ID', 1, len(p.placements), p.sidecar_crc)
    assert len(idblob) >= 16 + idcount
    ids = idblob[16:16 + idcount]
    gb = group_path.read_bytes()
    magic, version, nlet, ng, mesh_crc, mesh_bytes, side_crc, payload_crc = struct.unpack_from('<4s7I', gb)
    assert magic == b'R4SG' and version == 1 and nlet == p.nlet and 1 <= ng <= 8
    assert (mesh_crc, mesh_bytes, side_crc) == (p.mesh_crc, p.mesh_bytes, p.sidecar_crc)
    assert len(gb) == 32 + 16 * nlet * ng and zlib.crc32(gb[32:]) == payload_crc
    groups = np.frombuffer(gb, '<u2', offset=32).reshape(-1, ng, 8)
    gates = set(range(209, 223))
    protected = []
    candidates = []
    for pi, pl in enumerate(p.placements):
        source = pl['placement']
        m = p.meshes[pl['mesh']]
        if source <= 2 or source in gates or source >= len(ids) or ids[source] < 250:
            protected.append(pi)
            continue
        for part in range(m['first_part'], m['first_part'] + m['part_count']):
            if p.pmeta[part]['pass_'] != 0:
                continue
            first, count = p.plod[part]
            for ci in range(first, first + count):
                candidates.append((pi, part, ci))
    mats = {pi: p.wq(p.placements[pi]) for pi, _, _ in candidates}
    cameras = np.array([list(map(float, l.split())) for l in Path(a.cameras).read_text().splitlines() if l.strip()])
    assert cameras.shape[1] == 20
    bits8 = np.array([[(b >> j) & 1 for j in range(3)] for b in range(8)], float)

    def enumerate_decisions(cam):
        V = cam[:12].reshape(3, 4)
        P = cam[12:19]
        near = P[6] / (P[5] - 1)
        far = cam[19]
        px = max(320 * abs(P[1]), 240 * abs(P[3]))
        records = []
        visible = 0
        corners = 0
        nmeshlets = 0

        def state(M, lo, hi):
            q = np.asarray(lo) + bits8 * (np.asarray(hi) - lo)
            v = (q @ M[:, :3].T + M[:, 3]) @ V[:, :3].T + V[:, 3]
            z = -v[:, 2]
            x = P[1] * v[:, 0] + P[2] * v[:, 2]
            y = P[3] * v[:, 1] + P[4] * v[:, 2]
            outside = [x < -z, x > z, y < -z, y > z, z < near, z > far]
            if any(t.all() for t in outside):
                return -1
            return 1 if any(t.any() for t in outside) else 0

        for pi, part, ci in candidates:
            cl = p.clusters[ci]
            M = mats[pi]
            lo, hi = np.array(cl['bmin']), np.array(cl['bmax'])
            if state(M, lo, hi) < 0:
                records.append((-1, ()))
                continue
            visible += 1
            A = p.placements[pi]['affine']
            mv = V[:, :3] @ A[:, :3]
            mvq = V[:, :3] @ M[:, :3]
            tq = V[:, :3] @ M[:, 3] + V[:, 3]
            depth = max(near, -(mvq[2] @ ((lo + hi) * .5) + tq[2]) - np.abs(mvq[2]) @ ((hi - lo) * .5))
            lod_scale = np.sqrt((mv * mv).sum(1).max()) * px / a.lod_px
            level = cl['level_count'] - 1
            while level and p.levels[cl['first_level'] + level][2] * lod_scale > depth:
                level -= 1
            first, count, _ = p.levels[cl['first_level'] + level]
            lets = []
            for li in range(first, first + count):
                L = p.lets[li]
                ls = state(M, np.array(L['bmin']), np.array(L['bmax']))
                if ls < 0:
                    lets.append((li, 0, 0, -1))
                    continue
                gs = groups[li]
                ends = gs[:, 6]
                nonempty = ends != np.concatenate(([0], ends[:-1]))
                on = nonempty.copy()
                if ls:
                    for gi in range(ng):
                        if on[gi] and state(M, gs[gi, :3].astype(float), gs[gi, 3:6].astype(float)) < 0:
                            on[gi] = False
                mask = sum((1 << gi) for gi in range(ng) if on[gi])
                if mask:
                    lower = int((gs[:, 7] & 255)[on].min())
                    upper = int((gs[:, 7] >> 8)[on].max())
                    if on[nonempty].all():
                        lower, upper = 0, int(L['vc']) - 1
                    corners += upper - lower + 1
                    nmeshlets += 1
                else:
                    lower, upper = 0, -1
                lets.append((li, mask, lower, upper))
            records.append((level, tuple(lets)))
        return tuple(records), dict(visible_clusters=visible, meshlets=nmeshlets, transformed_corners=corners)

    records = []
    stats = []
    for cam in cameras:
        r, s = enumerate_decisions(cam)
        records.append(r)
        stats.append(s)

    def difference(x, y):
        return dict(cluster_visibility_or_lod=sum(r[0] != s[0] for r, s in zip(x, y)),
                    complete_cluster_draw_decision=sum(r != s for r, s in zip(x, y)))

    first = cameras[0].copy()
    V = first[:12].reshape(3, 4)
    eye = -np.linalg.solve(V[:, :3], V[:, 3])
    # Turn 90 degrees at the same eye. Keep the original pitch and projection.
    R = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float)
    rotated = first.copy()
    RV = V[:, :3] @ R
    rotated[:12] = np.column_stack((RV, -RV @ eye)).ravel()
    rr, rs = enumerate_decisions(rotated)
    zoomed = first.copy()
    zoomed[13] *= 1.2
    zoomed[15] *= 1.2
    zr, zs = enumerate_decisions(zoomed)
    shifted = []
    # Small sample of within-cell perturbations; a counterexample census, not certification.
    for i in range(0, len(cameras), max(1, len(cameras) // 8)):
        for axis, sign in ((0, -1), (0, 1), (2, -1), (2, 1)):
            cam = cameras[i].copy()
            vm = cam[:12].reshape(3, 4)
            e = -np.linalg.solve(vm[:, :3], vm[:, 3])
            e[axis] += sign * 250
            vm[:, 3] = -vm[:, :3] @ e
            r, _ = enumerate_decisions(cam)
            shifted.append(difference(records[i], r))

    levels_max = max(p.clusters[c]['level_count'] for _, _, c in candidates)
    cluster_bits = math.ceil(math.log2(levels_max + 1))
    nlet_instances = sum(sum(p.levels[p.clusters[c]['first_level'] + lv][1] for lv in range(p.clusters[c]['level_count'])) for _, _, c in candidates)
    cluster_bytes = math.ceil(len(candidates) * cluster_bits / 8)
    # This is just decisions; it excludes lookup/index, guards, alignment and the stream itself.
    complete_bytes = cluster_bytes + math.ceil(nlet_instances * ng / 8)
    out = dict(status='OFFLINE_FEASIBILITY_CENSUS_NOT_RUNTIME_PROOF',
        basis='Current spatial32v3 approved-L2 package geometry; historical 2026-10-15 cross camera poses; float64 geometric proxy. Not reconstructed runtime decisions, a matched current trace, or a performance measurement.',
        proxy_differences=['Proxy tests transformed box corners against all six planes; runtime cluster/meshlet tests use conservative view-space AABB supports with different margins.',
                          'Proxy tests group boxes against all six planes; runtime sg_select tests only crossed side/near planes and never far.',
                          'The 20-value camera input omits viewport; zero viewport offset is assumed here and not certified by that input.',
                          'Placement pretests, fully-inside propagation and interior state are not replayed; candidate pool excludes protected live gates.'],
        files={str(x): sha(x) for x in (mesh, side, ids_path, group_path, Path(a.cameras))},
        protected_placement_rows=protected, candidate_cluster_instances=len(candidates),
        candidate_placements=len(mats), candidate_all_level_meshlet_instances=nlet_instances,
        historical_camera_samples=len(cameras), unique_view_projection_samples=len({tuple(x) for x in cameras}),
        unique_cluster_lod_lists=len({tuple(r[0] for r in x) for x in records}),
        unique_complete_draw_lists=len(set(records)),
        historical_counts={k:dict(min=min(s[k] for s in stats), max=max(s[k] for s in stats), mean=sum(s[k] for s in stats)/len(stats)) for k in stats[0]},
        same_eye_yaw_90=dict(eye=eye.tolist(), differences=difference(records[0], rr), before=stats[0], after=rs),
        same_eye_fov_scale_1_2=dict(differences=difference(records[0], zr), before=stats[0], after=zs),
        within_cell_250mm_probe=dict(samples=len(shifted), changed_samples=sum(s['complete_cluster_draw_decision'] > 0 for s in shifted),
                                   max_changed_cluster_decisions=max(s['complete_cluster_draw_decision'] for s in shifted),
                                   mean_changed_cluster_decisions=sum(s['complete_cluster_draw_decision'] for s in shifted)/len(shifted)),
        illustrative_uncompressed_table_cost=dict(cluster_decision_bits=cluster_bits, cluster_only_bytes_per_pose=cluster_bytes,
             clusters_plus_all_level_group_masks_bytes_per_pose=complete_bytes,
             cluster_only_1024_positions_16_yaw_4_pitch_bytes=cluster_bytes*1024*16*4,
             complete_masks_1024_positions_16_yaw_4_pitch_bytes=complete_bytes*1024*16*4,
             example_grid_is_illustrative_not_required_coverage=True,
             compression_not_modeled=True,
             excluded='lookup/index, proof guards, projection variants, dynamic state, padding, vertex transform and submission'))
    Path(a.output).write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ('files', 'protected_placement_rows')}, indent=2))


if __name__ == '__main__':
    main()
