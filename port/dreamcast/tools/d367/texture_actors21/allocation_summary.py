#!/usr/bin/env python3
"""Summarize unique actor requests by proven native consumer and room.

The sums describe source-referenced texture requests, not simultaneous VRAM
residency, available blocks or measured peaks. No source geometry/data changes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


def summarize(candidates):
    source, textures, consumers, rooms = None, {}, {}, {}
    for directory in candidates:
        contract = json.loads((directory / "contract.json").read_text())
        report = json.loads((directory / "report.json").read_text())
        if contract["source_pack_sha256"] != report["source_pack_sha256"]:
            raise ValueError("candidate and contract refer to different source packs")
        if source is not None and report["source_pack_sha256"] != source:
            raise ValueError("cannot combine requests from different source packs")
        source = report["source_pack_sha256"]
        proofs = {p["id"]: p for p in contract["proofs"]}
        for row in report["textures"]:
            key = row["key"]
            if key in textures:
                raise ValueError("candidate texture key overlaps: " + key)
            textures[key] = dict(key=key, material=row["material"],
                                 source_package_sha256=row["source_package_sha256"],
                                 candidate_package_sha256=row["package_sha256"],
                                 before_request=row["before_allocation_request"],
                                 after_request=row["after_allocation_request"],
                                 before_alloc32=row["before_alloc32"], after_alloc32=row["after_alloc32"])
            for binding in row["owner"].get("proven_consumers", []):
                proof = proofs[binding["proof"]]
                disc_path = proof["disc_path"]
                consumers.setdefault(disc_path, set()).add(key)
                match = re.fullmatch(r"dc/native/(r[0-9a-f]+)/[^/]+\.re4nmr", disc_path)
                if not match:
                    raise ValueError("native consumer has an unexpected disc namespace")
                rooms.setdefault(match[1], set()).add(key)

    def total(keys):
        keys = sorted(keys)
        rows = [textures[k] for k in keys]
        sums = {name: sum(r[name] for r in rows) for name in
                ("before_request", "after_request", "before_alloc32", "after_alloc32")}
        return dict(keys=keys, **sums,
                    extra_request=sums["after_request"] - sums["before_request"],
                    extra_alloc32=sums["after_alloc32"] - sums["before_alloc32"])

    assigned = set().union(*rooms.values()) if rooms else set()
    return dict(schema="re4dc-actor-allocation-request-summary-1", source_pack_sha256=source,
                textures=list(textures.values()), overall=total(textures),
                per_native_consumer={name: total(keys) for name, keys in sorted(consumers.items())},
                per_room={name: total(keys) for name, keys in sorted(rooms.items())},
                no_room_assignment=total(set(textures) - assigned),
                limitations=["Unique source-referenced requests only; duplicate descriptor/LOD/consumer references are not added twice.",
                             "A consumer reference does not prove that texture draws or remains resident simultaneously.",
                             "Standard Leon has no automatic room assignment; pl00/pl08 and current draw selection need their source/runtime proof.",
                             "World, framebuffers, TA buffers, pinned/resident assets, allocator overhead beyond 32-byte rounding and reserves are not included.",
                             "No measured VRAM, residency, look, gameplay or hardware timing acceptance."])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate", action="append", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit("allocation summary exists; use a new output file")
    result = summarize(a.candidate)
    a.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(textures=len(result["textures"]), rooms=len(result["per_room"]),
                          extra_request=result["overall"]["extra_request"],
                          extra_alloc32=result["overall"]["extra_alloc32"])))


if __name__ == "__main__":
    main()
