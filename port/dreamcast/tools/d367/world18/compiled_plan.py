#!/usr/bin/env python3
"""Inspect/compile immutable world traversal metadata; game geometry stays private."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct
import zlib

import package_io

PLAN_HEADER = struct.Struct("<4s31I")


def compile_room(root: Path, output: Path) -> dict:
    """Replace R4SG metadata in its existing allocation; never rewrite geometry."""
    report = inspect_room(root)
    mesh = (root / "ps2-world.re4mesh").read_bytes()
    pw = (root / "ps2-world.r4pw").read_bytes()
    sg = (root / "ps2-world.r4sg").read_bytes()
    ids = (root / "ps2-world.ids").read_bytes()  # No static-cache eligibility without the ownership map.
    mh, ph, gh = struct.unpack_from("<4s19I", mesh), struct.unpack_from("<4s7I", pw), struct.unpack_from("<4s7I", sg)
    pk = package_io.read(mesh)
    np, nt, nm = ph[2:5]
    places = [struct.unpack_from("<HH12f", pw, 32 + 16 * nt + 52 * i) for i in range(np)]
    assert sorted(p[1] for p in places) == list(range(np))
    assert len(ids) >= 16 + np and struct.unpack_from("<4sIII", ids) == (b"R4ID", 1, np, ph[5])
    id_counts = Counter(ids[16:16+np])
    room = int(root.name.removeprefix("r"), 16)
    sky = set({0x100: [2, 3, 75, 33, 34, 35, 36, 37], 0x101: [0, 1, 2]}.get(room, []))
    static = [p[1] not in sky and not (ids[16+p[1]] < 250 and id_counts[ids[16+p[1]]] == 1) for p in places]
    uses = Counter(p[0] for p in places)
    parts = [struct.unpack_from("<IIHHBBBB", pw, 32 + 16 * i) for i in range(nt)]
    masks = [7 if p[4] == 2 and not (p[7] & 1) else 1 << p[4] for p in parts]
    tc_path = root / "ps2-world.r4tc"
    tc = tc_path.read_bytes() if tc_path.exists() else b""
    classes = bytes(nt)
    if tc:
        th = struct.unpack_from("<4s5I", tc)
        assert th[0] == b"R4TC" and th[1] == 1 and th[3:5] == (nt, ph[5])
        classes = tc[24:24+nt]
        assert th[5] == zlib.crc32(classes)
    pmasks = []
    affine_keys, affine_index = {}, []
    bounds = []
    for i, p in enumerate(places):
        m = pk["meshes"][p[0]]
        mask = 0
        for k in range(m[6], m[6]+m[7]):
            mask |= masks[k]
        pmasks.append(mask)
        raw = pw[36+16*nt+52*i:84+16*nt+52*i]
        affine_index.append(affine_keys.setdefault(raw, len(affine_keys)) if static[i] else 65535)
        a = p[2:]
        xyz = [[sum(a[4*r+c] * (m[17+c] if bit & (1 << c) else m[14+c]) for c in range(3)) + a[4*r+3]
                for r in range(3)] for bit in range(8)]
        assert all(math.isfinite(v) for pt in xyz for v in pt)
        bounds.append(([min(pt[r] for pt in xyz) for r in range(3)], [max(pt[r] for pt in xyz) for r in range(3)]))
    # Balanced spatial cells retain every immutable placement. They are candidates, never a visibility/PVS assertion.
    cells = [[i for i in range(np) if static[i]]]
    while len(cells) < 16:
        choices = [(len(c), j) for j, c in enumerate(cells) if len(c) > 1]
        if not choices:
            break
        _, j = max(choices)
        c = cells.pop(j)
        axis = max(range(3), key=lambda a: max(bounds[i][1][a]+bounds[i][0][a] for i in c)-min(bounds[i][1][a]+bounds[i][0][a] for i in c))
        c.sort(key=lambda i: (bounds[i][0][axis]+bounds[i][1][axis], i))
        cells.extend((c[:len(c)//2], c[len(c)//2:]))
    cells = [sorted(c) for c in cells if c]
    cell_of = {i: j for j, c in enumerate(cells) for i in c}
    assert sorted(cell_of) == [i for i in range(np) if static[i]]
    pool, keys, packed = bytearray(), {}, []
    reference = []
    for i in range(mh[6]):
        previous, live = 0, bytearray()
        for k in range(gh[3]):
            rec = sg[32+16*(i*gh[3]+k):48+16*(i*gh[3]+k)]
            end = struct.unpack_from("<H", rec, 12)[0]
            assert previous <= end <= pk["lets"][i][2]
            if end != previous:
                live.extend(rec)
            previous = end
        assert previous == pk["lets"][i][2] and live
        live = bytes(live)
        if live not in keys:
            keys[live] = len(pool)//16
            pool.extend(live)
        n = len(live)//16
        assert 1 <= n <= 8 and len(pool)//16 <= 8192
        packed.append(keys[live] | ((n-1) << 13))
        reference.append(live)
    out = bytearray(128)
    h = [b"R4SG", 2, mh[6], gh[3], mh[3], len(mesh), ph[5], 0, np, nt,
         len(pk["clusters"]), len(affine_keys), len(pool)//16, len(cells)] + [0]*18
    def section(slot, blob):
        out.extend(bytes((-len(out)) % 4))
        h[slot] = len(out)
        out.extend(blob)
    section(14, struct.pack("<%dH" % len(packed), *packed))
    section(15, pool)
    section(16, b"".join(struct.pack("<HBB", affine_index[i], pmasks[i],
                        (1 if static[i] else 0) | (2 if static[i] and uses[p[0]] == 1 else 0) | (cell_of.get(i, 31) << 3))
                        for i, p in enumerate(places)))
    section(17, bytes(v for pair in zip(masks, classes) for v in pair))
    candidates = [[i for i in range(np) if pmasks[i] & (1 << p)] for p in range(3)]
    ends = [0]
    for c in candidates:
        ends.append(ends[-1]+len(c))
    section(18, struct.pack("<%dH" % (4+ends[-1]), *(ends+sum(candidates, []))))
    h[19] = ends[-1]
    members, cell_blob = [], bytearray()
    for c in cells:
        # Outward padding dominates float rounding in the source's affine bound test. Runtime still tests all small units.
        lo = [min(bounds[i][0][a] for i in c) for a in range(3)]
        hi = [max(bounds[i][1][a] for i in c) for a in range(3)]
        pad = max(16., max(abs(v) for v in lo+hi)/4096.)
        lo = [package_io.f32(v-pad) for v in lo]
        hi = [package_io.f32(v+pad) for v in hi]
        assert all(lo[a] <= bounds[i][0][a] <= bounds[i][1][a] <= hi[a] for i in c for a in range(3))
        cell_blob.extend(struct.pack("<6fHH", *(lo+hi), len(members), len(c)))
        members.extend(c)
    section(20, cell_blob)
    section(21, struct.pack("<%dH" % len(members), *members))
    h[22] = len(members)
    section(25, bytes(2*mh[6]))
    h[23] = h[25]
    section(26, bytes(len(pk["clusters"])))
    section(27, bytes(48*len(affine_keys)))
    section(28, bytes(len(affine_keys)))
    section(29, bytes(108+len(cells)))  # exact camera key, validity word, conservative cell results
    used = len(out)
    if used > len(sg):
        raise ValueError(f"compiled plan needs {used} bytes, existing allocation only {len(sg)}")
    out.extend(bytes(len(sg)-len(out)))
    h[24] = len(out)-h[23]
    h[30], h[31] = zlib.crc32(ids), zlib.crc32(tc) if tc else 0
    h[7] = zlib.crc32(out[128:])
    PLAN_HEADER.pack_into(out, 0, *h)
    # Byte-exact reconstruction is stronger than triangle counts: group bounds, ranges and corner intervals are identical.
    for i, original in enumerate(reference):
        entry = struct.unpack_from("<H", out, h[14]+2*i)[0]
        first, count = entry & 8191, (entry >> 13)+1
        assert out[h[15]+16*first:h[15]+16*(first+count)] == original
    assert len(out) == len(sg) and not any(out[h[23]:])
    report.update(plan_sha256=sha(out), plan_bytes=len(out), plan_used_bytes=used,
                  allocation_growth=0, unused_bytes=len(out)-used, cells=len(cells),
                  covered_static_placements=len(members), fallback_dynamic_or_sky=np-len(members),
                  scratch_bytes=h[24], offsets=h[14:30], reconstructed_groups="byte-identical",
                  geometry_after_sha256=sha((root / "ps2-world.re4mesh").read_bytes()),
                  sidecar_after_sha256=sha((root / "ps2-world.r4pw").read_bytes()),
                  ids_sha256=sha(ids), classes_sha256=sha(tc) if tc else None,
                  descriptor_contract="placement references R4PW affine and R4IM mesh quantization; part references R4PW material/header key, pass and cull; fog stays source-owned; class bytes copied from R4TC")
    assert report["geometry_after_sha256"] == report["mesh_sha256"]
    assert report["sidecar_after_sha256"] == report["sidecar_sha256"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(out)
    return report


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def inspect_room(root: Path) -> dict:
    mesh = (root / "ps2-world.re4mesh").read_bytes()
    pw = (root / "ps2-world.r4pw").read_bytes()
    mh = struct.unpack_from("<4s19I", mesh)
    ph = struct.unpack_from("<4s7I", pw)
    assert mh[0] == b"R4IM" and mh[1] == 3 and mh[2] == len(mesh)
    assert mh[3] == zlib.crc32(mesh[80:])
    assert ph[0] == b"R4PW" and ph[1] == 1
    nplace, npart, nmesh = ph[2:5]
    assert npart == mh[5] and nmesh == mh[4]
    assert len(pw) == 32 + 16 * npart + 52 * nplace
    assert ph[5] == zlib.crc32(pw[32:])
    placements = [struct.unpack_from("<HH12f", pw, 32 + 16 * npart + 52 * i)
                  for i in range(nplace)]
    matrices = [pw[36 + 16 * npart + 52 * i:84 + 16 * npart + 52 * i]
                for i in range(nplace)]
    identity = struct.pack("<12f", 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0)
    linear_identity = sum(all(v[j] == identity[j] for j in range(48)
                              if j // 4 not in (3, 7, 11)) for v in matrices)
    counts = Counter(matrices)
    mesh_uses = Counter(p[0] for p in placements)
    mesh_rows = [struct.unpack_from("<HBBHHIII12f", mesh, mh[10] + 68 * i)
                 for i in range(nmesh)]
    part_rows = [struct.unpack_from("<IIHHBBBB", pw, 32 + 16 * i) for i in range(npart)]
    part_candidates = [7 if p[4] == 2 and not (p[7] & 1) else 1 << p[4] for p in part_rows]
    place_candidates = []
    for p in placements:
        m = mesh_rows[p[0]]
        mask = 0
        for pi in range(m[6], m[6] + m[7]):
            mask |= part_candidates[pi]
        place_candidates.append(mask)
    room = int(root.name.removeprefix("r"), 16)
    excluded = set({0x100: [2, 3, 75, 33, 34, 35, 36, 37], 0x101: [0, 1, 2]}.get(room, []))
    ids_path = root / "ps2-world.ids"
    if ids_path.exists():
        ids = ids_path.read_bytes()
        ih = struct.unpack_from("<4sIII", ids)
        assert ih == (b"R4ID", 1, nplace, ph[5])
        values = list(ids[16:16+nplace])
        id_counts = Counter(values)
        excluded.update(i for i, value in enumerate(values) if value < 250 and id_counts[value] == 1)
    static_places = [i for i, p in enumerate(placements) if p[1] not in excluded]
    static_unique = [i for i in static_places if mesh_uses[placements[i][0]] == 1]
    out = {"room_path": str(root), "mesh_sha256": sha(mesh), "sidecar_sha256": sha(pw),
           "mesh_bytes": len(mesh), "sidecar_bytes": len(pw), "placements": nplace,
           "parts": npart, "meshes": nmesh, "meshlets": mh[6], "vertices": mh[7],
           "unique_affines": len(counts), "identity_affines": counts[identity],
           "translation_only_affines": linear_identity,
           "affine_dictionary_bytes": 48 * len(counts) + 2 * nplace,
           "current_affine_bytes": 48 * nplace,
           "static_placement_count": len(static_places),
           "static_unique_mesh_placement_count": len(static_unique),
           "static_affine_count": len({matrices[i] for i in static_places}),
           "conservative_pass_candidates": [sum(bool(mask & (1 << p)) for mask in place_candidates) for p in range(3)],
           "shared_meshes": {str(k): v for k, v in sorted(mesh_uses.items()) if v > 1}}
    groups_path = root / "ps2-world.r4sg"
    if groups_path.exists():
        sg = groups_path.read_bytes()
        gh = struct.unpack_from("<4s7I", sg)
        assert gh[:3] == (b"R4SG", 1, mh[6]) and gh[4:7] == (mh[3], len(mesh), ph[5])
        assert gh[7] == zlib.crc32(sg[32:])
        ng = gh[3]
        records = [sg[i:i + 16] for i in range(32, len(sg), 16)]
        live = []
        per_let = []
        for let in range(mh[6]):
            prev = 0
            entries = []
            for g in range(ng):
                rec = records[let * ng + g]
                end = struct.unpack_from("<H", rec, 12)[0]
                if end != prev:
                    live.append(rec)
                    entries.append(rec)
                prev = end
            per_let.append(b"".join(entries))
        unique_lists = set(per_let)
        compact_bytes = 32 + 4 * mh[6] + sum(len(v) for v in per_let)
        dedup_bytes = 32 + 4 * mh[6] + sum(len(v) for v in unique_lists)
        pool_records = sum(len(v) // 16 for v in unique_lists)
        packed_bytes = dedup_bytes - 2 * mh[6] if pool_records <= 8192 and ng <= 8 else None
        out.update(groups_sha256=sha(sg), group_bytes=len(sg), groups_per_meshlet=ng,
                   nonempty_groups=len(live), all_group_records=len(records),
                   compact_group_bytes=compact_bytes, compact_group_saving=len(sg)-compact_bytes,
                   dedup_group_bytes=dedup_bytes, dedup_group_saving=len(sg)-dedup_bytes,
                   packed_dedup_group_bytes=packed_bytes,
                   packed_dedup_group_saving=len(sg)-packed_bytes if packed_bytes is not None else None,
                   unique_group_lists=len(unique_lists),
                   group_count_histogram=dict(sorted(Counter(len(x)//16 for x in per_let).items())))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("room", type=Path)
    ap.add_argument("--report", type=Path)
    ap.add_argument("--output", type=Path, help="write R4SG v2; input files are never modified")
    args = ap.parse_args()
    report = compile_room(args.room, args.output) if args.output else inspect_room(args.room)
    text = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
