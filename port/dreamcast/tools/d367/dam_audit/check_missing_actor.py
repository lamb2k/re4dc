#!/usr/bin/env python3
"""Code-only dam event controls; no assets, disc I/O, guest or console.

Execute extracted production EmSetFromList2 and the complete r10c event/exit.
The initial-move control executes the exact failure prefix of em10_R0_Init
and its exact destruction branch in cEm10::move, plus cManager::destroy.
Model construction, the rest of movement, camera/sound/effects and scheduling
are controlled boundaries. Those boundaries do not establish real read or
hardware failure rates. A separate target gate compiles the complete room TU.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
BASE = "ea969bb241f77291d2ca43d706c9dc2d1226ee76"


def function(source, signature):
    match = re.search(r"(?m)^" + re.escape(signature) + r"[^;\n]*\n?\s*\{", source)
    assert match, signature
    start = source.index("{", match.start())
    depth = 0
    for end in range(start, len(source)):
        depth += (source[end] == "{") - (source[end] == "}")
        if depth == 0:
            return source[match.start():end + 1] + "\n"
    raise AssertionError(signature)


def sha(content):
    return hashlib.sha256(content).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", default=BASE)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    paths = ("src/st1/r10c.cpp", "src/game/em_set.cpp", "src/em10/em10.cpp", "include/cManager.h")
    source = {p: (ROOT / p).read_text() for p in paths}
    baseline = subprocess.check_output(["git", "show", args.baseline + ":src/st1/r10c.cpp"], cwd=ROOT).decode()
    spawn = function(source[paths[1]], "cEm* EmSetFromList2(")
    init = function(source[paths[2]], "static void em10_R0_Init(")
    init_prefix = init[:init.index("    switch (em->emset_no & 0xF)")]
    init_prefix += "    em->r_no_0 = 1; // controlled successful initialization boundary\n}\n"
    move = function(source[paths[2]], "void cEm10::move(")
    move_begin = move.index("    Em10_R0_move_tbl[r_no_0](this);")
    move_end = move.index("\n#if", move_begin)
    move_branch = move[move_begin:move_end]
    destroy = "template<class T>\n" + function(source[paths[3]], "inline void cManager<T>::destroy(")
    template = (HERE / "missing_actor_fixture.cpp.in").read_text()
    inputs = dict(spawn_sha256=sha(spawn.encode()), init_failure_prefix_sha256=sha(init_prefix.encode()),
                  move_destroy_branch_sha256=sha(move_branch.encode()), destroy_sha256=sha(destroy.encode()))
    reports = {}
    for arm, room, knob in (("baseline", baseline, None), ("absent", source[paths[0]], None),
                             ("zero", source[paths[0]], 0), ("on", source[paths[0]], 1)):
        bodies = dict(SPAWN=spawn, INIT_FAILURE_PREFIX=init_prefix, MOVE_DESTROY_BRANCH=move_branch,
                      DESTROY=destroy, EVENT=function(room, "static void r10c_EmEvent("),
                      EXIT=function(room, "static void r10c_EmEvent_exit("))
        text = template
        for name, body in bodies.items():
            text = text.replace("@" + name + "@", body)
        path = out / (arm + ".cpp")
        path.write_text(text)
        exe = out / arm
        command = ["g++", "-std=c++20", "-O2", "-fpermissive",
                   "-fsanitize=undefined", "-fno-sanitize-recover=all", "-DRE4DC_EM_READ_RETRY=1",
                   "-DRE4DC_ALIVE_CAP=1"]
        if knob is not None:
            command += ["-DRE4DC_R10C_SPAWN_LIVE_GUARD=" + str(knob)]
        result = subprocess.run([*command, str(path), "-o", str(exe)], text=True, capture_output=True)
        (out / (arm + "-build.log")).write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stderr
        result = subprocess.run([str(exe)], text=True, capture_output=True)
        (out / (arm + "-run.log")).write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        reports[arm] = json.loads(result.stdout)
    assert reports["baseline"] == reports["absent"] == reports["zero"]
    for scenario in ("success", "one_missing_then_success", "two_missing_then_success",
                     "all_missing", "already_seen", "live_other_flags"):
        assert reports["on"][scenario] == reports["baseline"][scenario], scenario
    for scenario in ("first_move_failure", "retry_move_failure", "last_retry_move_failure", "missing_initializer"):
        old, new = reports["baseline"][scenario], reports["on"][scenario]
        assert old["retired_uses"] > 0 and new["retired_uses"] == 0, (scenario, old, new)
        assert new["event_starts"] == new["motion_sets"] == new["effect_sets"] == 0
        assert new["bank_3"] == new["bank_4"] == 1
        assert new["attempts"] == 3 and new["sleep_frames"] == 60
        assert new["initial_moves"] == 1 and new["list2_flags"] & 2
        assert new["list2_set"] == 0
    receipt = dict(status="PASS", baseline=args.baseline, scope=__doc__,
                   source_sha256={p: sha(v.encode()) for p, v in source.items()},
                   extracted=inputs, reports=reports, controls_per_arm=len(reports["on"]),
                   off_behavior_identical=True, successful_and_existing_missing_actions_identical=True,
                   sanitizers="UBSan; passing host controls only")
    (out / "host-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: receipt[k] for k in ("status", "controls_per_arm", "off_behavior_identical",
                                             "successful_and_existing_missing_actions_identical")}))


if __name__ == "__main__":
    main()
