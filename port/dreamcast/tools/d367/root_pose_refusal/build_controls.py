#!/usr/bin/env python3
"""Complete current-public native_static TU builds and OFF identity.

Reuses the established Make-expansion/header-overlay/compiler receipt helpers.
The selected release plus every ordered rr CH2 assignment feeds Make; private
asset path overrides match the current public build. This is not a linked release or a run of the game.
"""
import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
import extract

spec = importlib.util.spec_from_file_location("root_pose_build_profile", extract.HERE.parent / "world_submit_spike/build_profile.py")
profile_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile_tools)
Build, sections, sha, stack_usage = profile_tools.Build, profile_tools.sections, profile_tools.sha, profile_tools.stack_usage
BASELINE = "db222fc618045fc1da2bb3c7222743f83612ed1b"
KNOBS = ("ROOT_POSE_CAP_FALLBACK", "ROOT_POSE_WITNESS_PREFLIGHT", "ROOT_POSE_REFUSAL_DIAG")


def derive(output, compiler, kos, sdk):
    spec = importlib.util.spec_from_file_location("root_pose_current_recipe", extract.DC / "tools/cloud/build18/build_profile.py")
    current = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = current
    spec.loader.exec_module(current)
    current.UNITS["native_static"] = ("platform/native_static.o", "platform/native_static.cpp")
    flags, bundle, _ = current.derive(output, compiler, kos, sdk, [], tree=extract.ROOT, units=("native_static",))
    # The supplied SDK is immutable; apply only the pinned header declarations
    # in our output directory, before the SDK's -I search path.
    overlay, patch_receipt = profile_tools.pvr_overlay(output, kos)
    values = [flags["native_static"][0], "-I" + str(overlay), *flags["native_static"][1:]]
    receipt = dict(bundle["profiles"]["native_static"], flags=values[1:],
                   pvr_header_overlay=patch_receipt, debug_records=False,
                   scope="Current selected public release + ordered rr CH2 assignments; complete native_static TU only")
    assert "-DRE4DC_PS2_WORLD_ROOT_POSE=1" in values
    assert "SCENERY_STREAM=1" in receipt["command"], "current rr CH2 overlay missing"
    (output / "root-pose-profile.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return values, receipt


def guards(output, profile):
    rows = []
    for knob in KNOBS:
        for value in ("", "0 1", "1 1", "2", "yes", "01"):
            command = profile["command"] + [knob + "=" + value]
            result = subprocess.run(command, cwd=extract.DC / "game", text=True, capture_output=True)
            assert result.returncode and "must be" in result.stderr, (knob, value, result.stdout, result.stderr)
            rows.append(dict(knob=knob, value=value, status="rejected", stderr=result.stderr))
        command = profile["command"] + [knob + "=1", "PS2_WORLD_ROOT_POSE=0"]
        result = subprocess.run(command, cwd=extract.DC / "game", text=True, capture_output=True)
        assert result.returncode and "Root-pose refusal controls need" in result.stderr
        rows.append(dict(knob=knob, missing="PS2_WORLD_ROOT_POSE", status="rejected", stderr=result.stderr))
    (output / "make-guards.json").write_text(json.dumps(rows, indent=2) + "\n")
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--sh4-cxx", type=Path, required=True)
    p.add_argument("--kos-root", type=Path, required=True)
    p.add_argument("--sdk-root", type=Path, required=True)
    p.add_argument("--baseline", default=BASELINE)
    args = p.parse_args()
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=False)
    flags, profile = derive(output / "release-profile", args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve())
    guard_rows = guards(output, profile)
    common = [*flags, "-iquote", str(extract.SOURCE.parent)]
    old = subprocess.check_output(["git", "show", args.baseline + ":" + str(extract.SOURCE.relative_to(extract.ROOT))], cwd=extract.ROOT)
    current = extract.SOURCE.read_bytes()
    builder = Build(output)
    rows = {}
    arms = [("baseline", old, []), ("absent", current, []),
            ("zero", current, ["-DRE4DC_" + name + "=0" for name in KNOBS])]
    for cap, preflight, diag in itertools.product((0, 1), repeat=3):
        if cap or preflight or diag:
            arms.append((f"c{cap}-p{preflight}-d{diag}", current,
                         [f"-DRE4DC_{name}={value}" for name, value in zip(KNOBS, (cap, preflight, diag))]))
    for label, source, extra in arms:
        rows[label] = {}
        for suffix, phase in (("ii", ["-E", "-P"]), ("o", ["-c", "-fstack-usage"])):
            destination = output / (label + "." + suffix)
            builder.run([*common, *extra, "-x", "c++", "-", *phase, "-o", destination], cwd=extract.SOURCE.parent, source=source, label=label)
            row = dict(bytes=destination.stat().st_size, sha256=sha(destination))
            if suffix == "o":
                row.update(sections(destination));row["stack_usage"] = stack_usage(destination.with_suffix(".su"))
            rows[label][suffix] = row
            if label in ("absent", "zero"):
                assert destination.read_bytes() == (output / ("baseline." + suffix)).read_bytes(), (label, suffix, "OFF identity")
        print(label + ": PASS", flush=True)
    report = dict(status="PASS", baseline=args.baseline, source_sha256=hashlib.sha256(current).hexdigest(),
                  compiler=builder.run([args.sh4_cxx, "--version"], label="compiler").decode().splitlines()[0],
                  profile=profile, make_guards=len(guard_rows), production=rows,
                  limits="Complete native_static TU objects, absent/zero vs baseline byte identity; no linked game, private assets, emulator or physical console.")
    (output / "build-controls.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
