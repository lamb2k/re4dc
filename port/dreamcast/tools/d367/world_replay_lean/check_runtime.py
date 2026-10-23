#!/usr/bin/env python3
"""Compare every controlled TA/state word across all S/B/replay combinations.

Production UI begin/end, emitter bind/end, chunk_emit and chunk_flush bodies
are executed with controlled package, texture, stream, SQ and geometry edges.
This checks replay state and ownership, not complete renderer geometry or FPS.
"""
import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
spec = importlib.util.spec_from_file_location(
    "submission_source_controls", HERE.parent / "world_submit_spike/check_runtime.py")
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)


def fixture_source():
    values = original.extract()
    values["REPLAY_RESTART"] = ("#if RE4DC_SCENERY_REPLAY_LEAN\n" + original.function(
        original.STATIC.read_text(), "[[gnu::always_inline]] void chunk_restart()") + "\n#endif")
    text = (HERE / "fixture_boundary.cpp.in").read_text()
    text = text.replace("@QUEUE_FIXTURE@", (HERE / "fixture_queue.cpp.in").read_text())
    for name, value in values.items():
        text = text.replace("@" + name + "@", value)
    assert not re.search(r"@[A-Z_]+@", text), "Unfilled extraction seam"
    return text, values


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    text, values = fixture_source()
    fixture = output / "boundary.cpp"
    fixture.write_text(text)
    cases = list(range(41)) + list(range(100, 345))
    locks, hashes, rows = {}, {}, []
    for diagnostics, select, batch in itertools.product((0, 1), repeat=3):
        pair = f"d{diagnostics}-s{select}-b{batch}"
        baseline = None
        for replay in (0, 1):
            label = pair + f"-r{replay}"
            binary = output / label
            command = ["g++", "-std=c++20", "-O2", "-Wall", "-Wextra",
                       f"-DRE4DC_SCENERY_SELECT_ONLY={select}",
                       f"-DRE4DC_SCENERY_SUBMIT_BATCH={batch}",
                       f"-DRE4DC_SCENERY_REPLAY_LEAN={replay}",
                       f"-DCHECK_DIAGNOSTICS={diagnostics}", str(fixture), "-o", str(binary)]
            run = subprocess.run(command, cwd=ROOT, capture_output=True)
            (output / (label + ".compile.log")).write_bytes(run.stdout + run.stderr)
            assert run.returncode == 0, (label, run.stderr.decode())
            reports, errors = [], []
            for case in cases:
                run = subprocess.run([str(binary), str(case)], cwd=ROOT, capture_output=True)
                if run.returncode:
                    (output / (label + f"-case{case}.failed.txt")).write_bytes(run.stdout + run.stderr)
                    raise AssertionError((label, case, run.stderr.decode()))
                assert len(run.stdout.splitlines()) == 3, (label, case, "incomplete report")
                assert run.stdout.startswith((str(case) + " words=").encode())
                reports.append(run.stdout)
                errors.append(run.stderr)
            words, stderr = b"".join(reports), b"".join(errors)
            (output / (label + ".stdout")).write_bytes(words)
            (output / (label + ".stderr")).write_bytes(stderr)
            hashes[label] = hashlib.sha256(words).hexdigest()
            locks[label] = [dict(case=int(c), locks=int(l), unlocks=int(u))
                           for c, l, u in re.findall(rb"(\d+) lock=(\d+) unlock=(\d+)", stderr)]
            assert [x["case"] for x in locks[label]] == cases, (label, "missing lock report")
            assert all(x["locks"] == x["unlocks"] for x in locks[label]), label
            if replay == 0:
                baseline = reports
            else:
                differences = [case for case, old, new in zip(cases, baseline, reports) if old != new]
                assert not differences, (label, "TA/state words differ", differences)
                assert locks[label] == locks[pair + "-r0"], (label, "replay changed ownership boundaries")
        rows.append(dict(diagnostics=diagnostics, select=select, submit_batch=batch,
                         comparisons=len(cases), exact_words_equal=True))
    report = dict(status="PASS", comparisons=len(cases) * 8,
                  source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in (original.SOURCE, original.STATIC)},
                  extracted_sha256={name: hashlib.sha256(value.encode()).hexdigest()
                                    for name, value in values.items()},
                  combinations=rows, output_sha256=hashes, locks=locks,
                  scope=__doc__)
    (output / "check-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", comparisons=report["comparisons"], configurations=16)))


if __name__ == "__main__":
    main()
