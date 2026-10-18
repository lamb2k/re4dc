#!/usr/bin/env python3
"""World18 back-face ceiling on existing meshlets/strip groups and logged cameras.

Host analysis only. Uses the production sgprice package/frustum/LOD model. The
result is an optimistic geometry ceiling, not an implemented runtime speedup.
Dynamic/sky placement counts are separately excluded from the static candidate.
"""
import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "worldlean"))
import sgprice as sg


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cameras(path, first, last, stride):
    text = Path(path).read_text(errors="replace")
    pattern = r"PS2CAM f=(\d+) cf=([0-9a-f]{8}) c=([0-9a-f ]+) p=([0-9a-f ]+) vp="
    rows = {}
    for m in re.finditer(pattern, text):
        frame = int(m[1])
        words = m[3].split() + m[4].split() + [m[2]]
        if len(words) != 20 or not first <= frame <= last:
            continue
        floats = struct.unpack("<20f", struct.pack("<20I", *[int(x, 16) for x in words]))
        if np.isfinite(floats).all():
            rows[frame] = floats
    selected = []
    next_frame = first
    for frame, row in sorted(rows.items()):
        if frame >= next_frame:
            selected.append((frame, row))
            next_frame = frame + stride
    if len(selected) < 2:
        raise ValueError("A real multi-frame camera window is required")
    return selected


def selected_meshlets(D, V, P, near, far, lod_px):
    a, c = sg.side_coefs(P)
    WQ, AF = D["WQ"], D["AF"]
    Mv = np.einsum("ij,njk->nik", V[:, :3], WQ[:, :, :3])
    tv = np.einsum("ij,nj->ni", V[:, :3], WQ[:, :, 3]) + V[:, 3]
    mvA = np.einsum("ij,njk->nik", V[:, :3], AF[:, :, :3])
    px = max(320 * abs(P[1]), 240 * abs(P[3]))
    ls = np.sqrt((mvA ** 2).sum(2).max(1)) * px / lod_px
    pl = D["ci_pl"]
    v, r = sg.boxes_view(Mv[pl], tv[pl], D["cbox"])
    out, _, inside = sg.classify(v, r, a, c, near, far, True)
    vis = np.nonzero(~out)[0]
    depth = np.maximum(-v[vis, 2] - r[vis, 2], near)
    level = D["nlv"][vis] - 1
    for _ in range(int(D["nlv"].max())):
        idx = D["flv"][vis] + level
        level -= (level > 0) & (D["LV"][idx, 2] * ls[pl[vis]] > depth)
    lv = D["flv"][vis] + level
    for i, lvi in zip(vis, lv):
        pi = int(pl[i]); part = int(D["ci_part"][i])
        fm, mc = D["LV"][lvi, :2].astype(int)
        for li in range(fm, fm + mc):
            if inside[i]:
                mask = 0
            else:
                vb, rb = sg.boxes_view(Mv[pi:pi+1], tv[pi:pi+1], D["lbox"][li:li+1])
                outside, masks, _ = sg.classify(vb, rb, a, c, near, far, False)
                if outside[0]:
                    continue
                mask = int(masks[0])
            rec = D["SG"][li]
            ends = rec[:, 6]
            on = ends != np.r_[0, ends[:-1]]
            if mask and D["real_groups"]:
                lo, hi = rec[:, :3], rec[:, 3:6]
                for k in range(5):
                    if not (mask & (1 << k)):
                        continue
                    if k < 4:
                        row = 0 if k < 2 else 1
                        n = a[k] * Mv[pi, row] + c[k] * Mv[pi, 2]
                        d = a[k] * tv[pi, row] + c[k] * tv[pi, 2]
                    else:
                        n, d = -Mv[pi, 2], -tv[pi, 2] - near
                    on &= np.maximum(n * lo, n * hi).sum(1) + d >= -1.0
            yield pi, part, li, on


def corner_count(on, rec, vc, baseline=False):
    nonempty = rec[:, 6] != np.r_[0, rec[:-1, 6]]
    if not on.any():
        return 0
    if baseline and np.array_equal(on, nonempty):
        return vc
    return int((rec[on, 7] >> 8).max() - (rec[on, 7] & 255).min() + 1)


def cone(points, normals):
    # A zero-area triangle imposes no face constraint; an entirely degenerate
    # group is left alone rather than credited as a useful back-face saving.
    lengths = np.linalg.norm(normals, axis=1)
    valid = lengths > 1e-9
    if not valid.any():
        return None
    nn = normals[valid] / lengths[valid, None]
    axis = nn.sum(0)
    length = np.linalg.norm(axis)
    if length < 1e-9:
        return None
    axis /= length
    ca = float((nn @ axis).min())
    if ca <= 0:
        return None
    center = (points.min(0) + points.max(0)) * 0.5
    radius = float(np.linalg.norm(points - center, axis=1).max())
    return axis, ca, float(np.sqrt(max(0, 1-ca*ca))), center, radius


def cone_back(con, eye):
    if con is None:
        return False
    axis, ca, sa, center, radius = con
    v = center - eye
    along = float(v @ axis)
    # Avoid acos and normalization: support bound of all normals in the cone.
    across = np.sqrt(max(0, float(v @ v) - along*along))
    return along > 0 and along*ca - across*sa > radius + 0.01


def dynamic_fields(pkg_dir, p, room):
    path = pkg_dir / "ps2-world.ids"
    result = set({0x100: [2, 3, 75, 33, 34, 35, 36, 37], 0x101: [0, 1, 2]}.get(room, []))
    if path.exists():
        b = path.read_bytes()
        magic, version, count, crc = struct.unpack_from("<4sIII", b)
        assert magic == b"R4ID" and version == 1 and crc == p.sidecar_crc
        values = list(b[16:16+count])
        result.update(i for i, x in enumerate(values) if x < 250 and values.count(x) == 1)
    return result


def run(args):
    pkg = args.package
    mesh, side, groups = [pkg / ("ps2-world." + ext) for ext in ("re4mesh", "r4pw", "r4sg")]
    has_groups = groups.exists()
    D = sg.load(mesh, side, groups if has_groups else None)
    D["real_groups"] = has_groups
    p = D["p"]
    if not has_groups:
        # Rooms without .r4sg have whole-meshlet transform/submit units today.
        D["G"] = 1
        D["SG"] = np.zeros((p.nlet, 1, 8), dtype=np.int64)
        for li, let in enumerate(p.lets):
            D["SG"][li, 0] = (*let["bmin"], *let["bmax"], let["strip_bytes"], (let["vc"]-1)<<8)
    dyn = dynamic_fields(pkg, p, int(args.room.removeprefix("r"), 16))
    cams = cameras(args.log, args.first, args.last, args.stride)
    cache = {}
    rows = []
    for frame, cam in cams:
        V = np.array(cam[:12]).reshape(3, 4); P = cam[12:19]
        near, far = P[6] / (P[5]-1), cam[19]
        eye = -np.linalg.solve(V[:, :3], V[:, 3])
        row = dict(frame=frame, transformed=0, meshlets=0, groups_tested=0,
                   exact_meshlet_skip=0, exact_group_skip=0, cone_meshlet_skip=0,
                   cone_group_skip=0, static_exact_skip=0, static_cone_skip=0,
                   static_groups_tested=0, static_strips_skipped=0)
        for pi, part, li, on in selected_meshlets(D, V, P, near, far, args.lodpx):
            rec = D["SG"][li]; vc = int(D["vc"][li])
            baseline = corner_count(on, rec, vc, baseline=True)
            if not baseline:
                continue
            row["transformed"] += baseline; row["meshlets"] += 1
            cull = p.pmeta[part]["cull"]
            if cull not in (1, 2):
                continue
            key = (pi, li, cull)
            if key not in cache:
                cn, triangles = p.let_tris(li)
                tri = np.asarray(triangles, dtype=int).reshape(-1, 3)
                world = cn[:, :3] @ D["WQ"][pi, :, :3].T + D["WQ"][pi, :, 3]
                tw = world[tri]
                normal = np.cross(tw[:, 1]-tw[:, 0], tw[:, 2]-tw[:, 0]) * (1 if cull == 2 else -1)
                # sgprice already recovered each strip's group and length.
                sa, sz = D["let_s0"][li:li+2]
                tg = np.repeat(D["s_grp"][sa:sz], D["s_n"][sa:sz]-2)
                assert len(tg) == len(tri)
                cons = [cone(tw[tg == gi].reshape(-1, 3), normal[tg == gi]) if (tg == gi).any() else None
                        for gi in range(D["G"])]
                whole = cone(tw.reshape(-1, 3), normal)
                cache[key] = (tw, normal, tg, cons, whole)
            tw, normal, tg, cons, whole = cache[key]
            back = ((eye-tw[:, 0]) * normal).sum(1) <= -0.01
            exact = np.array([bool(back[tg == gi].all()) if (tg == gi).any() else False for gi in range(D["G"])])
            kb = np.array([cone_back(con, eye) for con in cons])
            # This assertion makes a nonconservative cone a hard analysis error.
            if (kb & ~exact).any():
                raise AssertionError((frame, pi, li, "cone admitted a front face"))
            ntests = sum(on[gi] and cons[gi] is not None for gi in range(D["G"]))
            row["groups_tested"] += int(ntests)
            exsave = baseline - min(baseline, corner_count(on & ~exact, rec, vc))
            cosave = baseline - min(baseline, corner_count(on & ~kb, rec, vc))
            row["exact_group_skip"] += exsave
            row["cone_group_skip"] += cosave
            row["exact_meshlet_skip"] += baseline if back.all() else 0
            row["cone_meshlet_skip"] += baseline if cone_back(whole, eye) else 0
            if p.placements[pi]["placement"] not in dyn:
                row["static_exact_skip"] += exsave
                row["static_cone_skip"] += cosave
                row["static_groups_tested"] += int(ntests)
                sa, sz = D["let_s0"][li:li+2]
                row["static_strips_skipped"] += int((on[D["s_grp"][sa:sz]] & kb[D["s_grp"][sa:sz]]).sum())
        ref = sg.view_counts(D, V, P, near, far, args.lodpx)
        assert row["transformed"] == ref["T1" if has_groups else "T0"], (row, ref)
        rows.append(row)
    means = {key: float(np.mean([row[key] for row in rows])) for key in rows[0] if key != "frame"}
    # 100/200 cycles are explicit sensitivity assumptions, not measured costs.
    pricing = dict(console_slope_ms_per_1000_vertices=1.0,
                   gross_console_slope_ms=means["static_cone_skip"] / 1000,
                   optimistic_exact_console_slope_ms=means["static_exact_skip"] / 1000,
                   prior_hwproject_transform_us_per_corner=0.22,
                   prior_hwproject_walk_us_per_strip=0.31,
                   hwproject_unit_cost_source="docs/lanes/t2exact.md, k0 frames500..799; extrapolation, not a new target run",
                   hwproject_transform_walk_gross_ms=means["static_cone_skip"]*0.00022 + means["static_strips_skipped"]*0.00031,
                   assumed_test_cycles=[100, 200], sh4_clock_mhz=200,
                   net_sensitivity_ms=[means["static_cone_skip"]/1000 - means["static_groups_tested"]*cycles/200000
                                       for cycles in (100, 200)])
    report = dict(room=args.room, kind="MODELLED GEOMETRY CEILING; no runtime speedup measured",
                  package=str(pkg), group_unit="strip_group" if has_groups else "meshlet",
                  files={x.name: sha(x) for x in (mesh, side, groups) if x.exists()},
                  camera_log=str(args.log), camera_log_sha256=sha(args.log),
                  first=rows[0]["frame"], last=rows[-1]["frame"], samples=len(rows), lod_px=args.lodpx,
                  mean=means, pricing=pricing, rows=rows,
                  constraints=["Existing meshlet and strip-group units, original corner range rule",
                               "Per-frame transform total agrees with sgprice",
                               "No GPU back-face gain claimed", "Dynamic/sky excluded from static proposal",
                               "Occluded, hidden, and state-gated geometry can make this ceiling optimistic"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
    args.output.with_suffix(".cams").write_text("".join(" ".join(format(x, ".9g") for x in cam)+"\n" for _, cam in cams))
    print(json.dumps({key: value for key, value in report.items() if key not in ("rows", "constraints")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("log", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--room", required=True)
    parser.add_argument("--first", type=int, default=300)
    parser.add_argument("--last", type=int, default=419)
    parser.add_argument("--stride", type=int, default=7)
    parser.add_argument("--lodpx", type=float, default=5)
    run(parser.parse_args())
