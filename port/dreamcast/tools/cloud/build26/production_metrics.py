#!/usr/bin/env python3
"""Summarize verified whole-TU sections and compiler stack frames for Build26.

These are relocatable object sections before final linking/garbage collection.
They do not assert a game-image, system-memory or maximum call-chain budget.
Each enabled profile is compared with the same QA_LINK baseline setting.
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
    assert off["status"] == on["status"] == "PASS" and off["baseline"] == on["baseline"]
    assert off["off_identity_comparisons"] == 200 and len(on["enabled_compiles"]) == 7
    assert all(off["source_sha256"].get(name, digest) == digest for name, digest in on["source_sha256"].items())
    fields = ("executable_bytes", "allocated_bytes", "zero_fill_bytes")
    rows = {}
    for name, units in on["artifacts"].items():
        overrides = next(iter(on["profiles"][name]["profiles"].values()))["overrides"]
        baseline = "link-baseline" if "QA_LINK=1" in overrides else "qa-baseline"
        result = {}
        totals = {key: dict(before=0, after=0, delta=0) for key in fields}
        for unit, artifacts in units.items():
            before = off["artifacts"][baseline].get(unit, {}).get("o", {})
            after = artifacts["o"]
            sizes = {key: dict(before=before.get(key, 0), after=after[key],
                               delta=after[key] - before.get(key, 0)) for key in fields}
            for key in fields:
                for arm in ("before", "after", "delta"):
                    totals[key][arm] += sizes[key][arm]
            stack = {}
            for arm, obj in (("before", before), ("after", after)):
                frames = obj.get("stack_usage", [])
                stack[arm] = dict(maximum_local_frame=max((frame["bytes"] for frame in frames), default=0),
                    selected=[frame for frame in frames if any(token in frame["function"] for token in
                        ("dfa26", "actor_clip26", "clip_strip", "clip_stream_strip", "front_triangle",
                         "diag_rows", "snap_diag", "link_telemetry", "link_pump", "Telemetry::step", "qa_poll", "link26"))])
            result[unit] = dict(sections=sizes, local_stack_frames=stack,
                                baseline_object_sha256=before.get("sha256"), candidate_object_sha256=after["sha256"])
        rows[name] = dict(baseline=baseline, overrides=overrides, units=result, totals=totals)
    report = dict(status="PASS", baseline=off["baseline"], scope=__doc__, profiles=rows,
                  source_receipts_sha256=dict(off=sha(args.off), on=sha(args.on)),
                  script_sha256=sha(Path(__file__)),
                  limitations="Section sizes include code/data/literal-pool sections before final link. Allocated includes zero-fill. Compiler local frames are not summed blindly and are not a full game stack watermark; observed fixture call-chain peaks are separately reported in cost receipts.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as destination:
        json.dump(report, destination, indent=2)
        destination.write("\n")
    print(json.dumps(dict(status="PASS", profiles=len(rows), receipt=str(args.output))))


if __name__ == "__main__":
    main()
