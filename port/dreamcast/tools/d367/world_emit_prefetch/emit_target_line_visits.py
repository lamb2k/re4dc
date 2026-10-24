#!/usr/bin/env python3
"""Qualify repeated demand-line visits for the three reported gather rows.

Re-execute the frozen target ELF, retain every actual data-access address and
width, and prove each access stays in one 32-byte line. Only then is the sum of
load/store accesses reported as line visits. PREF and cache misses are separate.
"""
import argparse
import json
from pathlib import Path

import measure_target as target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build, run = json.loads(args.build.read_text()), json.loads(args.run.read_text())
    names = ("gather-v16-n4-a0", "gather-v64-n32-a0", "gather-v128-n64-a0")
    rows = []
    for case in run["cases"]:
        if case["name"] not in names:
            continue
        config, meta = case["config"], case["package"]
        blob, meta, _, _ = target.package(meta["vertices"], meta["indexed"],
                                        meta["meshlets"], meta["alignment_padding"])
        for arm in ("e0-p0", "e1-p0"):
            machine, symbols, layout = target.load(build["arms"][arm])
            fields = ("count", "nr", "lo", "hi", "gmask", "primed", "next_nr", "header_hint")
            target.prepare(machine, symbols, layout, blob, tuple(config[k] for k in fields))
            row, _ = target.timed(machine, symbols, "fixture_gather_phase", 0, layout, meta)
            assert row["traffic"] == case["arms"][arm]["traffic"]
            assert all((e[3] >> 5) == ((e[3] + e[4] - 1) >> 5) for e in machine.memory_events)
            traffic = row["traffic"]["cached"]
            visits = traffic["load_accesses"] + traffic["store_accesses"]
            rows.append(dict(case=case["name"], arm=arm, demand_line_visits=visits,
                distinct_lines=traffic["unique_data_lines"],
                repeat_visits=visits - traffic["unique_data_lines"],
                all_accesses_within_single_line=True,
                access_widths=sorted({e[4] for e in machine.memory_events})))
    assert len(rows) == len(names) * 2
    result = dict(status="PASS", scope=__doc__, rows=rows,
        build_sha256=target.build_profile.sha(args.build), run_sha256=target.build_profile.sha(args.run),
        script_sha256=target.build_profile.sha(Path(__file__)))
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(status=result["status"], checked_rows=len(rows))))


if __name__ == "__main__":
    main()
