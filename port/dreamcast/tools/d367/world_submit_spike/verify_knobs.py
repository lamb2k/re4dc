#!/usr/bin/env python3
"""Check actual Make wiring and unsupported world-submit combinations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
CASES = [
    ("absent", [], True),
    ("off", ["SCENERY_SUBMIT_BATCH=0"], True),
    ("on", ["SCENERY_SUBMIT_BATCH=1"], True),
    ("invalid", ["SCENERY_SUBMIT_BATCH=2"], False),
    *[(name, ["SCENERY_SUBMIT_BATCH=1", knob], False) for name, knob in (
        ("no_chunk", "SCENERY_CHUNK=0"),
        ("no_direct", "TA_DIRECT=0"),
        ("no_mesh_direct", "MESH_DIRECT=0"),
        ("no_world_mesh", "PS2_WORLD_MESH=0"),
        ("no_hdr_cache", "PS2_WORLD_HDR_CACHE=0"),
        ("hdr_check", "PS2_WORLD_HDR_CACHE=2"),
        ("pvs", "PS2_PVS=1"),
        ("scratch", "WORLD_SCRATCH=1"),
        ("guard", "TA_GUARD=1"),
    )],
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True,
                        help="Complete production build-controls.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    profile = json.loads(args.build.read_text())["profile"]
    args.output.mkdir(parents=True, exist_ok=False)
    rows = []
    for name, extra, accepted in CASES:
        row = dict(name=name, extra=extra, expected_accept=accepted)
        for tu in ("native_static", "native_ui"):
            command = profile[tu]["command"] + extra
            run = subprocess.run(command, cwd=DC / "game", text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            (args.output / (name + "-" + tu + ".log")).write_text(run.stdout)
            assert (run.returncode == 0) == accepted, (name, tu, run.stdout)
            if accepted:
                compiles = [line for line in run.stdout.splitlines()
                            if line.startswith("kos-c++ ")]
                assert len(compiles) == 1, (name, tu, compiles)
                enabled = "-DRE4DC_SCENERY_SUBMIT_BATCH=1" in compiles[0]
                assert enabled == (name == "on"), (name, tu, enabled)
            row[tu] = dict(exit=run.returncode,
                           diagnostic=[line for line in run.stdout.splitlines() if "***" in line])
        rows.append(row)
    report = dict(status="PASS", cases=rows,
                  source_sha256=hashlib.sha256((DC / "game/scenery19.mk").read_bytes()).hexdigest(),
                  scope="Actual Make dry-runs for both affected translation units; no shell recipes executed")
    (args.output / "knob-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS %d Make configurations for both translation units" % len(rows))


if __name__ == "__main__":
    main()
