#!/usr/bin/env python3
"""Summarize Build28 complete selected-TU sections and compiler local frames.

Each enabled profile uses its exact matching integration profile as reference.
All figures precede final linking and garbage collection. Local stack frames
are not a complete call chain, IRQ watermark or console heap measurement.
"""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("off", "on", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    off, on = (json.loads(path.read_text()) for path in (args.off, args.on))
    assert off["status"] == on["status"] and off["status"] in ("PASS", "CONTROLLED_SYNTAX_PASS")
    assert off["baseline"] == on["baseline"]
    assert off["off_identity_comparisons"] == 56 and len(on["enabled_compiles"]) == 9
    assert len(on["link_off_on_identity"]) == 8
    assert all(off["source_sha256"].get(name, digest) == digest for name, digest in on["source_sha256"].items())
    fields = ("executable_bytes", "allocated_bytes", "zero_fill_bytes")
    profiles = {}
    for name, units in on["artifacts"].items():
        if not name.endswith("-on"):
            continue
        baseline = name.removesuffix("-on") + "-baseline"
        totals = {key: dict(before=0, after=0, delta=0) for key in fields}
        comparisons = {}
        for unit, artifacts in units.items():
            before, after = off["artifacts"][baseline][unit]["o"], artifacts["o"]
            sections = {key: dict(before=before[key], after=after[key], delta=after[key] - before[key]) for key in fields}
            for key in fields:
                for arm in ("before", "after", "delta"):
                    totals[key][arm] += sections[key][arm]
            frames = {arm: dict(max_local_frame=max((row["bytes"] for row in obj["stack_usage"]), default=0),
                               frames=obj["stack_usage"])
                      for arm, obj in (("before", before), ("after", after))}
            comparisons[unit] = dict(sections=sections, stack=frames,
                                     before_sha256=before["sha256"], after_sha256=after["sha256"])
        profiles[name] = dict(baseline=baseline, units=comparisons, totals=totals)
    result = dict(status=off["status"], baseline=off["baseline"], scope=__doc__, profiles=profiles,
                  syntax_control=off["syntax_control"]["enabled"],
                  source_receipts_sha256=dict(off=sha(args.off), on=sha(args.on)),
                  script_sha256=sha(Path(__file__)),
                  limitations="Relocatable code/data/BSS before final game link; allocated includes zero-fill. All source-controlled static buffers are counted, but no socket/PPP heap or complete game stack measurement is claimed.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as destination:
        json.dump(result, destination, indent=2)
        destination.write("\n")
    print(json.dumps(dict(status=result["status"], profiles=len(profiles), receipt=str(args.output))))


if __name__ == "__main__":
    main()
