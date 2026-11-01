#!/usr/bin/env python3
"""Execute actual actor clip-strip OFF/ON paths using explicit host adapters.

Reuses the existing Build 2 host AVK/SQ adapters without changing production
control, preparation, clipping or ownership code. Adds long-strip, parity,
skin/source/rigid, alpha, packed-UV, plane and capacity-failure controls.
This is host equivalence evidence, not hardware timing or console acceptance.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
OLD = DC / "tools/d367/actor_setup_lean"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sanitizer", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location("actor_setup_host", OLD / "check_runtime.py")
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    (out / "host/dc").mkdir(parents=True)
    (out / "host/dc/pvr.h").write_text(base.PVR)
    (out / "host/dc/sq.h").write_text(base.SQ)
    actor = DC / "game/platform/native_actor_fast.cpp"
    inputs = [actor, DC / "game/platform/include/actor_clip_reuse.hpp",
              DC / "room/pvr_geometry.cpp", OLD / "check_runtime.py",
              OLD / "fixture_actor.cpp.in", HERE / "actor_clip_cases.cpp.in", Path(__file__)]
    source_sha256 = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    host, adaptations = base.host_source(actor.read_text())
    (out / "native_actor_host.inc").write_text(host)
    fixture = (OLD / "fixture_actor.cpp.in").read_text()
    # A zero-sized vector may have a null data() pointer. The legacy dump helper
    # passed it to fwrite even with nmemb=0; guard the test-only output calls so
    # UBSan can check the production paths without this libc-contract violation.
    for vector in ("ta", "events", "calls"):
        old = f"assert(std::fwrite({vector}.data(),4,{vector}.size(),stdout)=={vector}.size());"
        assert fixture.count(old) == 1
        fixture = fixture.replace(old, f"if (!{vector}.empty()) " + old)
    adaptations["empty_vector_output"] = "Fixture output skips fwrite for empty vectors (no output-byte change)."
    needle = "int main(){"
    assert fixture.count(needle) == 1
    fixture = fixture.replace(needle, (HERE / "actor_clip_cases.cpp.in").read_text()
        + "\n" + needle + "\n    check::clip_cases();", 1)
    (out / "fixture.cpp").write_text(fixture)
    configurations = []
    for direct in (0, 1):
        before = None
        for reuse in (0, 1):
            name = f"direct{direct}-reuse{reuse}"
            defines = {
                "RE4DC_ACTOR_CLIP_REUSE": reuse, "RE4DC_DRAW_SETUP_AUDIT": 0,
                "RE4DC_ACTOR_SETUP_LEAN": 1, "RE4DC_ACTOR_DIRECT": direct,
                "RE4DC_ACTOR_BACKFACE_CONE": 0, "RE4DC_COARSE_ONE_SUBMIT": direct,
                "RE4DC_ACTOR_VTX_KERNEL": 1, "RE4DC_ACTOR_ASM": 0,
                "RE4DC_AVK_RIGID6": 1, "RE4DC_ACTOR_LIGHT_N16": 1,
                "RE4DC_ACTOR_NO_CLEAR": 1, "RE4DC_ACTOR_MOVCA": 0,
                "RE4DC_ACTOR_LOD_BUDGET": 0, "RE4DC_NATIVE_ACTOR_SKIN": 1,
                "RE4DC_NATIVE_ACTOR_SKIN_LAZY": 1,
                "RE4DC_ACTOR_PRELIT": 1, "RE4DC_ACTOR_EXACT_FAST": 1,
                "RE4DC_ACTOR_PROBE_LIGHT": 1, "RE4DC_LEON_SOURCE_LIGHT": 1,
                "RE4DC_LEON_LIGHT_HEADROOM": 1, "RE4DC_LEON_LIGHT_FILL": 45,
            }
            command = ["g++", "-std=c++20", "-O2", "-fno-fast-math", "-ffp-contract=off",
                "-ffunction-sections", "-fdata-sections", "-Wall", "-Wextra",
                *(f"-D{k}={v}" for k, v in defines.items()),
                "-I" + str(out / "host"), "-I" + str(DC / "game/platform"),
                "-I" + str(DC / "game/platform/include"), "-I" + str(DC / "room"),
                str(out / "fixture.cpp"), str(DC / "room/pvr_geometry.cpp"),
                str(DC / "room/source_lighting.cpp"), "-Wl,--gc-sections", "-o", str(out / name)]
            if args.sanitizer:
                command[1:1] = ["-fsanitize=address,undefined", "-fno-sanitize-recover=all"]
                command[command.index("-O2")] = "-O1"
            run = subprocess.run(command, capture_output=True)
            (out / (name + ".compile.log")).write_bytes(run.stdout + run.stderr)
            assert run.returncode == 0, (name, run.stderr.decode())
            env = os.environ.copy()
            env["ASAN_OPTIONS"] = "detect_leaks=0"
            run = subprocess.run([str(out / name)], capture_output=True, env=env)
            (out / (name + ".stdout")).write_bytes(run.stdout)
            (out / (name + ".stderr")).write_bytes(run.stderr)
            assert run.returncode == 0, (name, run.returncode, run.stderr.decode())
            if before is None:
                before = run.stdout
            else:
                assert before == run.stdout, (name, "TA/ownership/topology bytes differ")
            rows = base.decode_output(run.stdout)
            extended = [r for r in rows if r["case"] >= 10000]
            assert len(extended) == 3624
            assert any(r["ta_words"] > 0 for r in extended)
            assert any([90, 0, 0] == x for r in extended for x in r["result_events"])
            configurations.append(dict(name=name, cases=len(rows), added_clip_cases=len(extended),
                output_bytes=len(run.stdout), output_sha256=hashlib.sha256(run.stdout).hexdigest(),
                command=command))
    assert source_sha256 == {str(p.relative_to(ROOT)): sha(p) for p in inputs}, "sources changed during run"
    result = dict(status="PASS", scope=__doc__, host_adaptations=adaptations,
        sanitizer="address,undefined" if args.sanitizer else None,
        source_sha256=source_sha256,
        configurations=configurations)
    (out / "actor-host.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", configurations=len(configurations),
        cases_per_configuration=[r["cases"] for r in configurations], receipt=str(out / "actor-host.json"))))


if __name__ == "__main__":
    main()
