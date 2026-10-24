#!/usr/bin/env python3
"""Build 10 observation controls over Build 5's 78 actual-emitter cases.

Reuse the existing validated synthetic packages and controlled texture/TA/SQ
sink. Extract the current production emitter, gather, clipping, replay and
submission bodies; compare every TA/accounting word and SQ ownership trace
with WORLD_CENSUS24=0/1. The enabled arm links the real world_census24.cpp,
with host clock/thread/log adapters and an active world/tick scope. Packet
types in the independent sink validate the header/corner census totals.

The original fixture controls picks rather than running world selection. It
does not execute far_shell, SH4 FTRV/FSRRA, or a complete game frame. Host
clock increments exercise accounting only; they are not timing evidence.
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
BUILD5 = HERE.parent / "build5"
CORE = DC / "game/world_census24.cpp"
HEADER = DC / "game/platform/include/world_census24.h"
spec = importlib.util.spec_from_file_location("wc24_geometry_build5", BUILD5 / "check_geometry.py")
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
CASES = list(range(100, 178))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    text, values = prior.sources()
    raw = prior.original.STATIC.read_text()
    helpers = "\n".join(prior.function(raw, name) + ";" for name in
                        ("struct Wc24Count {", "struct Wc24PassResult {"))
    text = ("#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24\n"
            '#include "world_census24.h"\n' + helpers + "\n#endif\n" + text)
    seam = "int main(int argc,char** argv){"
    assert text.count(seam) == 1
    census_fixture = (HERE / "fixture_census.cpp.in").read_text()
    text = text.replace(seam, census_fixture + "\n" + seam)
    seam = "if(id>=100){queue_case(id);report(id);return 0;}"
    assert text.count(seam) == 1
    text = text.replace(seam, """if(id>=100){
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        wc24_begin_case();
        {
            re4dc::wc24::Scope world(re4dc::wc24::NearOP,re4dc::wc24::Selection);
            Wc24PassResult result;
            queue_case(id);
            // Controlled caller status: the actual source-extracted failure
            // guard observes the unchanged queue's return/accounting result.
            result.complete=!queue_fallback && !queue_aborts;
        }
        wc24_finish_case(id);
#else
        queue_case(id);
#endif
        report(id);return 0;
    }""")
    values["CENSUS_HELPERS"] = helpers
    values["CENSUS_FIXTURE"] = census_fixture
    return text, values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sanitize", action="store_true")
    parser.add_argument("--quick", action="store_true",
                        help="Only submission/replay enabled, prefetch disabled (78 paired cases)")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    watched = [prior.original.STATIC, prior.original.SOURCE, CORE, HEADER, Path(__file__),
               HERE / "fixture_census.cpp.in", BUILD5 / "check_geometry.py",
               BUILD5 / "fixture_geometry.cpp.in", prior.PRIOR / "fixture_boundary.cpp.in",
               prior.PRIOR / "check_geometry.py", prior.PRIOR / "check_runtime.py",
               DC / "tools/d367/world_submit_spike/check_runtime.py",
               *[DC / "room" / name for name in ("mesh_fastpath.hpp", "mesh_fastpath_sched.hpp",
                   "mesh_strip_lean.hpp", "pvr_geometry.cpp", "pvr_geometry.hpp",
                   "static_room_prepare.hpp", "instanced_mesh.hpp", "room_package.hpp")]]
    hashes = {str(path.relative_to(ROOT)): sha(path) for path in watched}
    (output / "shim/dc").mkdir(parents=True)
    (output / "shim/kos").mkdir()
    (output / "shim/dc/pvr.h").write_text("#pragma once\n// Types are supplied by the unchanged controlled sink.\n")
    (output / "shim/kos/fs.h").write_text("#pragma once\nusing file_t=int;\n#define FILEHND_INVALID (-1)\n")
    (output / "shim/dc/matrix.h").write_text("""#pragma once
using matrix_t=float[4][4];
static void mat_load(const matrix_t* m){std::memcpy(vp_host_xmtrx,*m,sizeof(matrix_t));}
static void mat_trans_nodiv(float& x,float& y,float& z,float& w){VP_FTRV(x,y,z,w);}
""")
    source, values = sources()
    fixture = output / "geometry.cpp"
    fixture.write_text(source)
    combinations = [(1, 1, 0)] if args.quick else list(itertools.product((0, 1), repeat=3))
    rows, output_hashes, observations = [], {}, {}
    for batch, replay, prefetch in combinations:
        pair = f"b{batch}-r{replay}-e{prefetch}"
        baseline, baseline_locks = None, None
        knobs = dict(SCENERY_SELECT_ONLY=1, SCENERY_SUBMIT_BATCH=batch,
                     SCENERY_REPLAY_LEAN=replay, SCENERY_UV_SNAPSHOT=1,
                     SCENERY_SELECT_LEAN2=0, SCENERY_EMIT_PREFETCH=prefetch)
        for enabled in (0, 1):
            label = pair + f"-wc{enabled}"
            binary = output / label
            command = ["g++", "-std=c++20", "-O2", "-ffp-contract=off", "-Wall", "-Wextra",
                       *(f"-DRE4DC_{name}={value}" for name, value in knobs.items()),
                       f"-DRE4DC_WORLD_CENSUS24={enabled}", "-DRE4DC_WORLD_CENSUS24_HOST=1",
                       "-DCHECK_DIAGNOSTICS=0", "-I" + str(output / "shim"),
                       "-I" + str(HEADER.parent), str(fixture)]
            if enabled:
                command.append(str(CORE))
            command += ["-o", str(binary)]
            if args.sanitize:
                command[3:3] = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-fno-pie", "-no-pie"]
            run = subprocess.run(command, cwd=ROOT, capture_output=True)
            (output / (label + ".compile.log")).write_bytes(run.stdout + run.stderr)
            assert run.returncode == 0, (label, run.stderr.decode())
            reports, errors, census = [], [], []
            for case in CASES:
                run = subprocess.run([str(binary), str(case)], cwd=ROOT, capture_output=True)
                if run.returncode:
                    (output / (label + f"-case{case}.failed.txt")).write_bytes(run.stdout + run.stderr)
                    raise AssertionError((label, case, run.stderr.decode()))
                assert len(run.stdout.splitlines()) == 3, (label, case, "incomplete TA/state report")
                reports.append(run.stdout)
                errors.append(run.stderr)
                matches = re.findall(rb"^WC24 (\{[^\n]+\})$", run.stderr, re.MULTILINE)
                assert len(matches) == enabled, (label, case, "active census receipt missing/unexpected")
                if enabled:
                    receipt = json.loads(matches[0])
                    assert receipt["case"] == case
                    census.append(receipt)
            data, stderr = b"".join(reports), b"".join(errors)
            (output / (label + ".stdout")).write_bytes(data)
            (output / (label + ".stderr")).write_bytes(stderr)
            output_hashes[label] = hashlib.sha256(data).hexdigest()
            locks = re.findall(rb"^(\d+) lock=(\d+) unlock=(\d+)$", stderr, re.MULTILINE)
            assert [int(x[0]) for x in locks] == CASES
            assert all(x[1] == x[2] for x in locks)
            if not enabled:
                baseline, baseline_locks = reports, locks
            else:
                different = [case for case, before, after in zip(CASES, baseline, reports) if before != after]
                assert not different, (label, "TA/accounting words differ", different)
                assert locks == baseline_locks, (label, "SQ ownership changed")
                observations[pair] = census
        rows.append(dict(knobs=knobs, comparisons=len(CASES), exact_words_equal=True,
                         exact_sq_ownership_equal=True, active_census_packet_counts_verified=True))
        print("PASS", pair, flush=True)
    for name, digest in hashes.items():
        assert sha(ROOT / name) == digest, (name, "source changed during control run")
    report = dict(status="PASS", comparisons=len(CASES) * len(rows), sanitized=args.sanitize,
                  source_sha256=hashes, extracted_sha256={key: hashlib.sha256(value.encode()).hexdigest()
                                                        for key, value in values.items()},
                  combinations=rows, output_sha256=output_hashes, census=observations, scope=__doc__)
    (output / "geometry-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", comparisons=report["comparisons"], configurations=len(rows) * 2)))


if __name__ == "__main__":
    main()
