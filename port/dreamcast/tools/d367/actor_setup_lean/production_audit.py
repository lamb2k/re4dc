#!/usr/bin/env python3
"""Emit reviewable production assembly and verify it reproduces the gated objects.

The verbose assembly is useful for checking constructor stores and first-use
branches without mistaking a controlled fixture's register allocation for the
production call site's. Reassembly must reproduce the complete qualified TU
object byte for byte. This also checks the Make knob's invalid-value guard and
that the runtime sources have not changed since the production gate.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
import build_profile


def run(args):
    build_path, output = args.build.resolve(), args.output.resolve()
    build = json.loads(build_path.read_text())
    assert build["status"] == "PASS"
    output.mkdir(parents=True, exist_ok=False)
    source_checks = {}
    for path, digest in build["source_sha256"].items():
        assert build_profile.sha(ROOT / path) == digest, (path, "runtime changed since production gate")
        source_checks[path] = digest
    variant = "d1-c0"
    profile = build["profile"]["profiles"][variant]
    # The Make recipe names kos-c++; use the same qualified SH compiler with
    # its expanded flags, as the production gate does.
    compiler = args.sh4_cxx.resolve()
    flags = [str(compiler), *profile["flags"]]
    source_relative = Path("port/dreamcast/game/platform/native_actor_fast.cpp")
    source = ROOT / source_relative
    old = build_path.parent / "baseline-tree" / source_relative
    builder = build_profile.Build(output)
    arms = {}
    for arm, content, extra in (("baseline", old.read_bytes(), []),
                                ("on", source.read_bytes(), ["-DRE4DC_ACTOR_SETUP_LEAN=1"])):
        assembly = output / (arm + ".s")
        builder.run([*flags, *extra, "-x", "c++", "-", "-S", "-fverbose-asm", "-o", assembly],
                    cwd=source.parent, source=content, label=arm)
        obj = output / (arm + ".o")
        builder.run([compiler, "-m4-single", "-ml", "-x", "assembler", "-c", assembly, "-o", obj],
                    label=arm + "-assemble")
        qualified = build_path.parent / (variant + "-" + arm + ".o")
        assert obj.read_bytes() == qualified.read_bytes(), (arm, "verbose assembly changed production object")
        arms[arm] = dict(assembly=str(assembly), assembly_sha256=build_profile.sha(assembly),
                         reassembled_object_sha256=build_profile.sha(obj),
                         qualified_object=str(qualified), object_identical=True)
    invalid = subprocess.run([*profile["command"], "ACTOR_SETUP_LEAN=2"], cwd=DC / "game",
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert invalid.returncode and "ACTOR_SETUP_LEAN must be 0 or 1" in invalid.stdout, invalid.stdout
    result = dict(status="PASS", scope=__doc__, production_controls_sha256=build_profile.sha(build_path),
                  source_sha256=source_checks, arms=arms,
                  invalid_make_value=dict(value=2, returncode=invalid.returncode, output=invalid.stdout))
    (output / "production-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sh4-cxx", required=True, type=Path)
    result = run(parser.parse_args())
    print(json.dumps(dict(status=result["status"], production_objects=2, invalid_value_rejected=True)))


if __name__ == "__main__":
    main()
