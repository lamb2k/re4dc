#!/usr/bin/env python3
"""Summarize Build27 guarded-TU sections plus newly selected module storage."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("off", "on", "modules", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    off, on, modules = (json.loads(path.read_text()) for path in (args.off, args.on, args.modules))
    assert all(value["status"] == "PASS" for value in (off, on, modules))
    assert off["baseline"] == on["baseline"] == modules["baseline"]
    assert off["off_identity_comparisons"] == 192 and on["enabled_compositions"] == 8
    for name, digest in on["source_sha256"].items():
        assert off["source_sha256"].get(name, digest) == digest, (name, "different source freezes")
    fields = ("executable_bytes", "allocated_bytes", "zero_fill_bytes")
    profiles = {}
    for name, units in on["artifacts"].items():
        baseline = name.removesuffix("-on") + "-baseline"
        totals = {key: dict(before=0, after=0, delta=0) for key in fields}
        comparisons = {}
        for unit, artifacts in units.items():
            before, after = off["artifacts"][baseline][unit]["o"], artifacts["o"]
            sections = {key: dict(before=before[key], after=after[key], delta=after[key] - before[key]) for key in fields}
            for key in fields:
                for arm in ("before", "after", "delta"):
                    totals[key][arm] += sections[key][arm]
            frames = {}
            for arm, obj in (("before", before), ("after", after)):
                frames[arm] = dict(max_local_frame=max((row["bytes"] for row in obj["stack_usage"]), default=0),
                    selected=[row for row in obj["stack_usage"] if any(token in row["function"] for token in
                        ("weapon27", "weaponLoad", "ReadWepData", "debugWeapon", "cItemMgr::arm", "loadRelData", "revert", "linkRelData"))])
            comparisons[unit] = dict(sections=sections, stack=frames, before_sha256=before["sha256"], after_sha256=after["sha256"])
        added = ("wep06", "wep12") if name.startswith("w1-") else ("wep05", "wep06", "wep12")
        module_delta = {key: sum(modules["modules"][mod]["allocated"][key] for mod in added) for key in fields}
        profiles[name] = dict(baseline=baseline, guarded_units=comparisons, guarded_unit_totals=totals,
                             new_modules=list(added), new_module_sections=module_delta,
                             combined_added_sections={key: totals[key]["delta"] + module_delta[key] for key in fields})
    result = dict(status="PASS", baseline=off["baseline"], scope=__doc__, profiles=profiles,
                  source_receipts_sha256=dict(off=sha(args.off), on=sha(args.on), modules=sha(args.modules)),
                  script_sha256=sha(Path(__file__)),
                  limitations="Whole relocatable sections before final link and garbage collection, not final game image growth. With old WEAPON_WEP05=1 its module already exists and is not added twice. Compiler local stack frames are not complete call-chain or console watermarks.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as destination:
        json.dump(result, destination, indent=2)
        destination.write("\n")
    print(json.dumps(dict(status="PASS", profiles=len(profiles), receipt=str(args.output))))


if __name__ == "__main__":
    main()
