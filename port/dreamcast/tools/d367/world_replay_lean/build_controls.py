#!/usr/bin/env python3
"""Build complete Test22 world TUs and prove replay-OFF identity for S/B pairs.

S is SCENERY_SELECT_ONLY; B is SCENERY_SUBMIT_BATCH. Every pair compares the
unchanged integration-base source, current absent/zero, and replay enabled.
The baseline selector include is restored into a temporary quote-search root,
so the proof cannot accidentally compile new selector code in both arms.
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
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
BASELINE = "451bed6faa2c37f7f9aa05d6fb1116ec64219ebc"
spec = importlib.util.spec_from_file_location(
    "replay_production_profile", HERE.parent / "world_submit_spike/build_profile.py")
profile_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile_tools)
Build, sections, sha, stack_usage = (profile_tools.Build, profile_tools.sections,
                                    profile_tools.sha, profile_tools.stack_usage)


def read_base(path, baseline):
    return subprocess.check_output(["git", "show", baseline + ":" + str(path.relative_to(ROOT))], cwd=ROOT)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--sh4-cxx", type=Path, required=True)
    p.add_argument("--kos-root", type=Path, required=True)
    p.add_argument("--sdk-root", type=Path, required=True)
    p.add_argument("--baseline", default=BASELINE)
    p.add_argument("--profile-only", action="store_true")
    args = p.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    flags, profile = profile_tools.derive(output / "release-profile", args.sh4_cxx.resolve(),
                                         args.kos_root.resolve(), args.sdk_root.resolve())
    if args.profile_only:
        (output / "profile.json").write_text(json.dumps(dict(flags=flags, profile=profile), indent=2) + "\n")
        print(json.dumps(dict(status="PASS", profile=str(output / "profile.json"))))
        return
    builder = Build(output)
    watched = [DC / "game/platform/native_static.cpp", DC / "game/platform/native_ui.cpp",
               DC / "game/scenery19.mk", *sorted((DC / "game/platform/include").glob("scenery_*"))]
    source_hashes = {str(path.relative_to(ROOT)): sha(path) for path in watched}
    baseline_root = output / "baseline-platform"
    (baseline_root / "include").mkdir(parents=True)
    includes = ["scenery_chunk_select.inc", "scenery_part_far.inc", "scenery_submit_batch.h"]
    baseline_includes = {}
    for name in includes:
        path = DC / "game/platform/include" / name
        content = read_base(path, args.baseline)
        (baseline_root / "include" / name).write_bytes(content)
        baseline_includes[name] = hashlib.sha256(content).hexdigest()
    production = {}
    for select, batch in itertools.product((0, 1), repeat=2):
        pair = f"s{select}-b{batch}"
        production[pair] = {}
        for tu in ("native_static", "native_ui"):
            path = DC / ("game/platform/" + tu + ".cpp")
            current, old = path.read_bytes(), read_base(path, args.baseline)
            (output / (tu + ".cpp")).write_bytes(current)
            (baseline_root / (tu + ".cpp")).write_bytes(old)
            common = [word for word in flags[tu] if not word.startswith((
                "-DRE4DC_SCENERY_SELECT_ONLY=", "-DRE4DC_SCENERY_SUBMIT_BATCH=",
                "-DRE4DC_SCENERY_REPLAY_LEAN="))]
            common += ["-iquote", str(path.parent)]
            if select and tu == "native_static":
                common.append("-DRE4DC_SCENERY_SELECT_ONLY=1")
            if batch:
                common.append("-DRE4DC_SCENERY_SUBMIT_BATCH=1")
            records = {}
            for arm, content, cwd, knob in (("baseline", old, baseline_root, None),
                ("absent", current, path.parent, None), ("zero", current, path.parent, 0),
                ("on", current, path.parent, 1)):
                extra = [] if knob is None else ["-DRE4DC_SCENERY_REPLAY_LEAN=" + str(knob)]
                label = pair + "-" + tu + "-" + arm
                for suffix, phase in (("ii", ["-E", "-P"]), ("o", ["-c", "-fstack-usage"])):
                    destination = output / (label + "." + suffix)
                    builder.run([*common, *extra, "-x", "c++", "-", *phase, "-o", destination],
                                cwd=cwd, source=content, label=label)
                    row = dict(bytes=destination.stat().st_size, sha256=sha(destination))
                    if suffix == "o":
                        row.update(sections(destination))
                        row["stack_usage"] = stack_usage(destination.with_suffix(".su"))
                    records[arm + "." + suffix] = row
                if arm in ("absent", "zero"):
                    for suffix in ("ii", "o"):
                        control = output / (pair + "-" + tu + "-baseline." + suffix)
                        assert (output / (label + "." + suffix)).read_bytes() == control.read_bytes(), (
                            pair, tu, arm, suffix, "replay OFF identity")
            production[pair][tu] = records
    for path, digest in source_hashes.items():
        assert sha(ROOT / path) == digest, (path, "source changed during build")
    report = dict(status="PASS", baseline=args.baseline, knob="SCENERY_REPLAY_LEAN",
                  scope="Complete native_static/native_ui Test22 TU builds, four S/B pairs, baseline/absent/zero/on; no linked image",
                  compiler=builder.run([args.sh4_cxx, "--version"], label="compiler").decode().splitlines()[0],
                  source_sha256=source_hashes, baseline_include_sha256=baseline_includes,
                  profile=profile, production=production)
    (output / "build-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", pairs=4, translation_units=2, off_identity_comparisons=32)))


if __name__ == "__main__":
    main()
