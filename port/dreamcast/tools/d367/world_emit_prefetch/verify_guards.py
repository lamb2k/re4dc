#!/usr/bin/env python3
"""Negative controls for Build 5's indexed-range and lookahead boundaries.

Mutations apply only to generated host fixtures, never to game sources. Each
control must expose a TA mismatch or reject an out-of-range prefetch request.
These prove that the corresponding fixture can observe a missing guard; they
do not substitute for target arithmetic, whole-game or console qualification.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("emit_geometry", HERE / "check_geometry.py")
geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    geometry.write_shims(output)
    source, values, _ = geometry.sources()
    # The last valid pick is followed by an allocated but deliberately invalid
    # descriptor. Correct run_end handling never evaluates its meshlet index.
    sentinel = geometry.replace_once(source,
        "ChunkPart cctx[kChunkParts]{};MeshDraw::Pick cpk[kChunkPicks]{};",
        "ChunkPart cctx[kChunkParts]{};MeshDraw::Pick cpk[kChunkPicks]{};\n"
        "    for(auto& unused:cpk)unused={0xffffU,255U,255U,0U,255U,{0,0}};")
    variants = {
        "positive": sentinel,
        "missing_dedup_fallback": geometry.replace_once(sentinel,
            "if(dd_word(l)>>24)return corners(l);", "if(false)return corners(l);"),
        "compacted_partial_gather": geometry.replace_once(sentinel,
            "Word* out=reinterpret_cast<Word*>(gathered+pk.lo);",
            "Word* out=reinterpret_cast<Word*>(gathered);"),
        "missing_run_end": geometry.replace_once(sentinel,
            "if(next>=run_end)next=nullptr;", "if(false)next=nullptr;"),
    }
    cases = {
        # Visible repeats expose wrong bytes; clipped-away controls remain in
        # the positive matrix but need not expose a TA mismatch when mutated.
        "missing_dedup_fallback": [305, 309, 313],
        "compacted_partial_gather": [211, 213, 215],
        "missing_run_end": [200, 201, 202, 203],
    }
    binaries = {}
    for name, text in variants.items():
        source_path, binary = output / (name + ".cpp"), output / name
        source_path.write_text(text)
        command = ["g++", "-std=c++20", "-O2", "-ffp-contract=off",
            "-DRE4DC_SCENERY_EMIT_PREFETCH=1", "-DRE4DC_SCENERY_SELECT_ONLY=1",
            "-DRE4DC_SCENERY_SUBMIT_BATCH=1", "-DRE4DC_SCENERY_REPLAY_LEAN=1",
            "-DRE4DC_SCENERY_UV_SNAPSHOT=1", "-DRE4DC_SCENERY_SELECT_LEAN2=1",
            "-DRE4DC_PREF_WALK=1", "-DRE4DC_SCN_CENSUS=1", "-DCHECK_DIAGNOSTICS=0",
            "-I" + str(output / "shim"), "-I" + str(geometry.DC / "game/platform/include"),
            "-I" + str(geometry.DC / "game/platform"), str(source_path), "-o", str(binary)]
        run = subprocess.run(command, cwd=geometry.ROOT, capture_output=True)
        (output / (name + ".compile.log")).write_bytes(run.stdout + run.stderr)
        assert run.returncode == 0, (name, run.stderr.decode())
        binary.chmod(binary.stat().st_mode | 0o111)
        binaries[name] = binary
    rows = []
    for name, controls in cases.items():
        for case in controls:
            positive = subprocess.run([str(binaries["positive"]), str(case), "2", "4"], capture_output=True)
            assert positive.returncode == 0, (case, "positive control failed", positive.stderr.decode())
            mutated = subprocess.run([str(binaries[name]), str(case), "2", "4"], capture_output=True)
            if name == "missing_run_end":
                observed = mutated.returncode != 0 and b"prefetch outside registered live data" in mutated.stderr
            else:
                observed = mutated.returncode == 0 and positive.stdout.splitlines()[1] != mutated.stdout.splitlines()[1]
            assert observed, (name, case, "negative control was not exposed", mutated.stderr.decode())
            (output / f"{name}-{case}.positive.stdout").write_bytes(positive.stdout)
            (output / f"{name}-{case}.mutated.stdout").write_bytes(mutated.stdout)
            (output / f"{name}-{case}.mutated.stderr").write_bytes(mutated.stderr)
            rows.append(dict(mutation=name, case=case, positive_exit=positive.returncode,
                             mutated_exit=mutated.returncode, guard_failure_observed=True))
    report = dict(status="PASS", negative_controls=len(rows), scope=__doc__,
        source_sha256=hashlib.sha256(geometry.original.STATIC.read_bytes()).hexdigest(),
        original_fixture_sha256=geometry.sha(source),
        fixture_sha256={name: geometry.sha(text) for name, text in variants.items()}, controls=rows)
    (output / "negative-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "negative_controls": len(rows)}))


if __name__ == "__main__":
    main()
