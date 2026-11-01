#!/usr/bin/env python3
"""Exercise actual root-pose/admission/draw/lifetime code with synthetic data."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
import extract


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--cxx", default="g++")
    args = p.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = output / "production-fixture.cpp"
    source.write_text(extract.host_source())
    rows = []
    for cap, preflight, diag in itertools.product((0, 1), repeat=3):
        label = f"c{cap}-p{preflight}-d{diag}"
        exe = output / label
        command = [args.cxx, "-std=c++20", "-O1", "-g", "-Wall", "-Wextra",
                   "-Wno-misleading-indentation", "-Wno-unused-variable", "-Wno-unused-but-set-variable",
                   "-fsanitize=address,undefined", "-fno-sanitize-recover=all", "-fno-pie", "-no-pie",
                   "-DRE4DC_ROOT_POSE_CAP_FALLBACK=" + str(cap),
                   "-DRE4DC_ROOT_POSE_WITNESS_PREFLIGHT=" + str(preflight),
                   "-DRE4DC_ROOT_POSE_REFUSAL_DIAG=" + str(diag),
                   "-I" + str(extract.DC / "game/platform/include"), str(source), "-o", str(exe)]
        build = subprocess.run(command, text=True, capture_output=True)
        (output / (label + "-build.log")).write_text(build.stdout + build.stderr)
        if build.returncode:
            raise RuntimeError(label + " build: " + build.stderr)
        # LeakSanitizer's /proc thread scan is unavailable in the cloud runner;
        # the fixture's exact cell ledger checks every allocation/free itself.
        env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0")
        run = subprocess.run([str(exe)], text=True, capture_output=True, env=env)
        (output / (label + ".log")).write_text(run.stdout + run.stderr)
        if run.returncode:
            raise RuntimeError(label + " run: " + run.stdout + run.stderr)
        rows.append(dict(cap=cap, preflight=preflight, diag=diag, command=command,
                         stdout=run.stdout, stderr=run.stderr))
        print(label + ": PASS", flush=True)
    result = dict(status="PASS", arms=rows,
                  source_sha256=hashlib.sha256(extract.SOURCE.read_bytes()).hexdigest(),
                  fixture_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  limits="Host ASan/UBSan source-extracted control/data-flow tests; synthetic heap/filesystem/owner records. LeakSanitizer disabled because the cloud /proc scan is unavailable; fixture allocation ledger must be empty. No game assets, GPU, target execution or physical console.")
    (output / "host-receipt.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
