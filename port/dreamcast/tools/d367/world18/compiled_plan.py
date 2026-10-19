#!/usr/bin/env python3
"""Inspect/compile immutable world traversal metadata; game geometry stays private."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import zlib


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
    args = ap.parse_args()
    report = inspect_room(args.room)
    text = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
