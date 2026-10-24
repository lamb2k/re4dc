#!/usr/bin/env python3
"""Make-derived Test22 public SH4 TU builds and absent/zero identity controls.

No assets, release link, console execution or emulator timing are needed. KOS
headers and the established public-header profile are compiler inputs only.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
DC = ROOT / "port/dreamcast"
BASELINE = "ea969bb241f77291d2ca43d706c9dc2d1226ee76"
spec = importlib.util.spec_from_file_location("effect_public_profile", HERE.parent / "world_submit_spike/build_profile.py")
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    _, receipt = profile.derive(output / "profile", args.sh4_cxx.resolve(),
                                args.kos_root.resolve(), args.sdk_root.resolve())
    work = output / "profile"
    # Generate the actual public module recipe for this room, without building
    # any module or data. Its overlay-specific CPP flags come from gen_modules.
    module_command = [sys.executable, str(DC / "game/tools/gen_modules.py"),
                      str(ROOT / "config/G4BE08/modules"), str(ROOT), str(work / "obj"),
                      str(work / "obj/modules.mk"), "st1_3:ovl"]
    subprocess.run(module_command, check=True, cwd=DC / "game", capture_output=True)
    builder = profile.Build(output)
    specs = (("esp", "src/game/esp.o", "../../../src/game/esp.cpp", "src/game/esp.cpp"),
             ("r117", "mod/st1_3/src/st1/r117.o", "../../../src/st1/r117.cpp", "src/st1/r117.cpp"))
    profiles, results = {}, {}
    for name, target, source_relative, path in specs:
        flags, expanded = profile.expand(work, args.sh4_cxx.resolve(), args.sdk_root.resolve(),
                                         work / "kos-overlay", receipt["native_static"],
                                         name, target, source_relative)
        profiles[name] = expanded
        # Derive each knob's command through Make, not just command-line defines.
        generated_knob_flags = {}
        for recycle, puzzle in ((0, 0), (1, 0), (0, 1), (1, 1)):
            selected = dict(receipt["native_static"])
            selected["command"] = [*selected["command"], f"ESP_POOL_RECYCLE={recycle}",
                                   f"R117_EFFECT_FAILURE_SAFE={puzzle}"]
            chosen, chosen_receipt = profile.expand(work, args.sh4_cxx.resolve(), args.sdk_root.resolve(),
                                                    work / "kos-overlay", selected,
                                                    f"{name}-make-r{recycle}-p{puzzle}", target, source_relative)
            additions = [word for word in chosen if word not in flags]
            expected = (["-DRE4DC_ESP_POOL_RECYCLE=1"] if recycle else []) + (
                        ["-DRE4DC_R117_EFFECT_FAILURE_SAFE=1"] if puzzle else [])
            assert additions == expected, (name, recycle, puzzle, additions)
            assert [word for word in chosen if word not in expected] == flags
            generated_knob_flags[f"r{recycle}-p{puzzle}"] = chosen_receipt
        profiles[name]["knob_recipes"] = generated_knob_flags
        current = (ROOT / path).read_bytes()
        baseline = subprocess.check_output(["git", "show", args.baseline + ":" + path], cwd=ROOT)
        results[name] = {}
        cases = (("baseline", baseline, []), ("absent", current, []),
                 ("zero", current, ["-DRE4DC_ESP_POOL_RECYCLE=0", "-DRE4DC_R117_EFFECT_FAILURE_SAFE=0"]))
        cases += tuple((f"r{recycle}-p{puzzle}", current,
                        [f"-DRE4DC_ESP_POOL_RECYCLE={recycle}", f"-DRE4DC_R117_EFFECT_FAILURE_SAFE={puzzle}"])
                       for recycle, puzzle in ((1, 0), (0, 1), (1, 1)))
        for arm, body, extras in cases:
            key = name + "-" + arm
            values = {}
            for suffix, phase in (("ii", ["-E", "-P"]), ("o", ["-c", "-fstack-usage"])):
                destination = output / (key + "." + suffix)
                builder.run([*flags, *extras, "-x", "c++", "-", *phase, "-o", destination],
                            cwd=ROOT / path.rsplit("/", 1)[0], source=body, label=key)
                values[suffix] = dict(bytes=destination.stat().st_size, sha256=profile.sha(destination))
                if suffix == "o":
                    values[suffix].update(profile.sections(destination))
                    values[suffix]["stack_usage"] = profile.stack_usage(destination.with_suffix(".su"))
            results[name][arm] = values
        for suffix in ("ii", "o"):
            original = (output / f"{name}-baseline.{suffix}").read_bytes()
            for arm in ("absent", "zero"):
                assert (output / f"{name}-{arm}.{suffix}").read_bytes() == original, (name, arm, suffix)
        # The unrelated fix's knob must not alter this translation unit.
        unrelated = "r0-p1" if name == "esp" else "r1-p0"
        assert (output / f"{name}-{unrelated}.o").read_bytes() == (output / f"{name}-baseline.o").read_bytes()
        own = "r1-p0" if name == "esp" else "r0-p1"
        assert (output / f"{name}-r1-p1.o").read_bytes() == (output / f"{name}-{own}.o").read_bytes()
    # Check Make's real validation/default/explicit-zero behavior too.
    validation = []
    for name in ("ESP_POOL_RECYCLE", "R117_EFFECT_FAILURE_SAFE"):
        for value in ("-1", "2", "bad"):
            command = [*receipt["native_static"]["command"], f"{name}={value}"]
            checked = subprocess.run(command, cwd=DC / "game", capture_output=True, text=True)
            assert checked.returncode != 0 and f"{name} must be 0 or 1" in checked.stderr
            validation.append(dict(knob=name, value=value, rejected=True))
    report = dict(status="PASS", scope=__doc__, baseline=args.baseline,
                  compiler=builder.run([args.sh4_cxx.resolve(), "--version"], label="compiler").decode().splitlines()[0],
                  source_sha256={path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                                 for path in ("src/game/esp.cpp", "src/st1/r117.cpp", "port/dreamcast/game/esppool.mk")},
                  module_recipe_command=module_command, profiles=profiles, results=results,
                  absent_zero_preprocessed_and_objects_identical=True, independent_knobs_compose=True,
                  make_validation=validation)
    (output / "build-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", translation_units=len(results), arms_per_tu=6,
                          absent_zero_identity=True, combination_identity=True)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sh4-cxx", type=Path, required=True)
    parser.add_argument("--kos-root", type=Path, required=True)
    parser.add_argument("--sdk-root", type=Path, required=True)
    parser.add_argument("--baseline", default=BASELINE)
    run(parser.parse_args())
