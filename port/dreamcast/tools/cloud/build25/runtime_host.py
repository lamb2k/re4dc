#!/usr/bin/env python3
"""Actual production-TU Build 25 cases; no copy of the light arithmetic."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
ACTOR = ROOT / "port/dreamcast/game/platform/native_actor_fast.cpp"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--sanitize", action="store_true")
    args = parser.parse_args()
    receipts = []
    with tempfile.TemporaryDirectory(prefix="re4dc-build25-") as name:
        temp = Path(name)
        (temp / "dc").mkdir()
        (temp / "dc/pvr.h").write_text(
            "#pragma once\n#include <cstddef>\n#include <cstdint>\n"
            "struct pvr_vertex_t{std::uint32_t flags;float x,y,z,u,v;std::uint32_t argb,oargb;};\n"
            "struct pvr_poly_hdr_t{std::uint32_t words[8];};\n"
            "#define PVR_CMD_VERTEX 0xe0000000U\n#define PVR_CMD_VERTEX_EOL 0xf0000000U\n"
            "int pvr_prim(const void*,std::size_t);\n")
        fixture = temp / "runtime.cpp"
        fixture.write_text((HERE / "runtime_cases.cpp.in").read_text().replace("ACTOR_IMPLEMENTATION", str(ACTOR)))
        profiles = [[], ["RE4DC_ACTOR_PROBE_LIGHT=1", "RE4DC_LEON_SOURCE_LIGHT=1"],
                    ["RE4DC_ACTOR_PROBE_LIGHT=2", "RE4DC_LEON_SOURCE_LIGHT=1", "RE4DC_GIGANTE_LIGHTS=1",
                     "RE4DC_LEON_LIGHT_HEADROOM=1", "RE4DC_LEON_LIGHT_FILL=45", "RE4DC_ACTOR_BYTES_LEAN=1",
                     "RE4DC_ACTOR_NO_CLEAR=1", "RE4DC_ACTOR_SETUP_LEAN=1", "RE4DC_ACTOR_EXACT_FAST=1",
                     "RE4DC_STATUE_LIGHTS=2", "RE4DC_GANADO_LIT=1", "RE4DC_GANADO_LIT_TOGGLE=1",
                     "RE4DC_GANADO_LIT_FILL=40"],
                    ["RE4DC_ACTOR_LIGHT_CAP=1", "RE4DC_BARN28_DIAG=1"]]
        for n, profile in enumerate(profiles):
            exe = temp / ("runtime-" + str(n))
            command = ["g++", "-std=c++20", "-O2", "-ffunction-sections", "-fdata-sections", "-Wl,--gc-sections",
                       "-DRE4DC_ACTOR_LIGHT_FAST_ONLY=1", *["-D" + d for d in profile],
                       "-I" + str(temp), "-I" + str(ROOT / "port/dreamcast/game/platform/include"),
                       str(fixture), "-o", str(exe)]
            if args.sanitize:
                command[1:1] = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
            built = subprocess.run(command, capture_output=True, text=True)
            if built.returncode:
                raise RuntimeError(built.stdout + built.stderr)
            environment = dict(os.environ)
            if args.sanitize:
                # LeakSanitizer cannot inspect /proc task lists in the tool sandbox.
                environment["ASAN_OPTIONS"] = "detect_leaks=0"
            result = subprocess.run([str(exe)], capture_output=True, text=True, env=environment)
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            symbols = subprocess.run(["nm", "-C", str(exe)], check=True, capture_output=True, text=True).stdout
            for forbidden in ("pass_lights(", "pass_lights_exact(", "evaluate_prepared_source_lighting("):
                assert forbidden not in symbols, forbidden
            receipts.append(dict(profile=profile, result=result.stdout.strip(), evaluator_symbols="absent"))
            print(result.stdout.strip())
    sources = [ACTOR, ACTOR.parent / "include/actor_light_fast_only.h",
               ACTOR.parent / "include/actor_light_fast_only.inc", HERE / "runtime_cases.cpp.in", Path(__file__)]
    receipt = dict(status="PASS", scope=__doc__, sanitizer=args.sanitize,
                   leak_detection=False if args.sanitize else None, profiles=receipts,
                   source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                  for path in sources})
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
