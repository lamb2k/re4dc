#!/usr/bin/env python3
"""Check real Make wiring for all replay/select/submit combinations and guards."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile", type=Path, required=True, help="profile.json or build-controls.json")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    profile = json.loads(args.profile.read_text())["profile"]
    args.output.mkdir(parents=True, exist_ok=False)
    cases = [("absent", [], True, (0, 0, 0))]
    for replay, select, batch in itertools.product((0, 1), repeat=3):
        cases.append((f"r{replay}-s{select}-b{batch}", [f"SCENERY_REPLAY_LEAN={replay}",
            f"SCENERY_SELECT_ONLY={select}", f"SCENERY_SUBMIT_BATCH={batch}"], True, (replay, select, batch)))
    cases += [("invalid", ["SCENERY_REPLAY_LEAN=2"], False, None)]
    cases += [(name, ["SCENERY_REPLAY_LEAN=1", extra], False, None) for name, extra in (
        ("no_chunk", "SCENERY_CHUNK=0"), ("no_ta_direct", "TA_DIRECT=0"),
        ("no_mesh_direct", "MESH_DIRECT=0"), ("no_ps2_mesh", "PS2_WORLD_MESH=0"),
        ("scratch", "WORLD_SCRATCH=1"))]
    cases += [("pvs_without_submit", ["SCENERY_REPLAY_LEAN=1", "PS2_PVS=1"], True, (1, 0, 0)),
              ("no_header_cache_without_submit", ["SCENERY_REPLAY_LEAN=1", "PS2_WORLD_HDR_CACHE=0"], True, (1, 0, 0))]
    rows = []
    for name, extra, accepted, modes in cases:
        row = dict(name=name, options=extra, accepted=accepted)
        for tu in ("native_static", "native_ui"):
            command = profile[tu]["command"] + extra
            run = subprocess.run(command, cwd=DC / "game", text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            (args.output / (name + "-" + tu + ".log")).write_text(run.stdout)
            assert (run.returncode == 0) == accepted, (name, tu, run.stdout)
            if accepted:
                commands = [shlex.split(line) for line in run.stdout.replace("\\\n", " ").splitlines()
                            if line.startswith("kos-c++ ")]
                assert len(commands) == 1, (name, tu)
                replay, select, batch = modes
                expected = dict(SCENERY_REPLAY_LEAN=replay if tu == "native_static" else 0,
                                SCENERY_SELECT_ONLY=select if tu == "native_static" else 0,
                                SCENERY_SUBMIT_BATCH=batch)
                for knob, mode in expected.items():
                    assert ("-DRE4DC_" + knob + "=1" in commands[0]) == bool(mode), (name, tu, knob)
            row[tu] = dict(exit=run.returncode,
                           diagnostics=[line for line in run.stdout.splitlines() if "***" in line])
        rows.append(row)
    report = dict(status="PASS", cases=rows,
                  source_sha256=hashlib.sha256((DC / "game/scenery19.mk").read_bytes()).hexdigest(),
                  scope="Make dry-runs only, no shell recipes, all three switches and new-knob dependency guards")
    (args.output / "knob-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", configurations=len(rows), translation_units=2)))


if __name__ == "__main__":
    main()
