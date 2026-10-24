#!/usr/bin/env python3
"""Prove complete actor TU OFF identity and compile the direct/cone matrix.

The integration-base tree is materialized from git archive solely to expand
its unmodified Make recipe. Base/current absent/current zero must produce the
same flags and generated header contents after path normalization. Full TUs
then compare executable objects and line-marker-free preprocessing, retaining
the release optimization/ABI settings and omitting only debug line records.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
SOURCE = DC / "game/platform/native_actor_fast.cpp"
BASELINE = "28da09802ed9ff6756529bab02978230983453be"
import build_profile


def normalized_flags(flags, profile_root, source_root):
    return [word.replace(str(profile_root), "<PROFILE>").replace(str(source_root), "<SOURCE>") for word in flags]


def headers(row, profile_root):
    return {str(Path(path).relative_to(profile_root)): digest for path, digest in row["generated_headers"].items()}


def baseline_profiles(output, compiler, kos, sdk, baseline):
    tree = output / "baseline-tree"
    tree.mkdir()
    archive = subprocess.check_output(["git", "archive", baseline], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        source.extractall(tree, filter="data")
    modules = (build_profile, build_profile.helpers, build_profile.helpers.release_profile)
    saved = [(module, module.ROOT, module.DC) for module in modules]
    try:
        for module in modules:
            module.ROOT, module.DC = tree, tree / "port/dreamcast"
        profiles, receipt = build_profile.derive(output / "baseline-profile", compiler, kos, sdk)
    finally:
        for module, root, dc in saved:
            module.ROOT, module.DC = root, dc
    return tree, profiles, receipt


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    compiler, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    tree, old_flags, old_profile = baseline_profiles(output, compiler, kos, sdk, args.baseline)
    flags, profile = build_profile.derive(output / "release-profile", compiler, kos, sdk)
    zero_flags, zero_profile = build_profile.derive(output / "zero-profile", compiler, kos, sdk, lean=0)
    on_flags, on_profile = build_profile.derive(output / "on-profile", compiler, kos, sdk, lean=1)
    make_checks = {}
    for name in flags:
        reference = normalized_flags(old_flags[name], output/"baseline-profile", tree)
        absent = normalized_flags(flags[name], output/"release-profile", ROOT)
        zero = normalized_flags(zero_flags[name], output/"zero-profile", ROOT)
        on = normalized_flags(on_flags[name], output/"on-profile", ROOT)
        assert absent == zero == reference, (name, "Make flags OFF identity")
        assert [x for x in on if x != "-DRE4DC_ACTOR_SETUP_LEAN=1"] == reference, (name, "Make ON adds only knob")
        assert on.count("-DRE4DC_ACTOR_SETUP_LEAN=1") == 1, (name, "Make knob wiring missing")
        source_headers = headers(old_profile["profiles"][name], output/"baseline-profile")
        for other, root in ((profile, "release-profile"), (zero_profile, "zero-profile"), (on_profile, "on-profile")):
            assert headers(other["profiles"][name], output/root) == source_headers, (name, root, "generated headers")
        make_checks[name] = dict(flags_identical_off=True, generated_headers_identical=True, on_adds_only_knob=True)
    watched = [SOURCE, DC/"game/game30.mk", *(SOURCE.parent/"include").glob("native_actor*.inc")]
    source_hashes = {str(path.relative_to(ROOT)): build_profile.sha(path) for path in watched}
    # The runtime change is in this TU. Current existing native-actor includes
    # must remain the baseline bytes; a new disabled include can be absent there.
    include_checks = {}
    for path in watched[2:]:
        baseline_path = tree/path.relative_to(ROOT)
        if baseline_path.exists():
            assert baseline_path.read_bytes() == path.read_bytes(), (path, "baseline runtime include changed")
            include_checks[str(path.relative_to(ROOT))] = build_profile.sha(path)
    current, old = SOURCE.read_bytes(), (tree/SOURCE.relative_to(ROOT)).read_bytes()
    builder = build_profile.Build(output)
    production = {}
    for name, common in flags.items():
        records = {}
        for arm, content, knob in (("baseline", old, None), ("absent", current, None),
                                   ("zero", current, 0), ("on", current, 1)):
            extra = [] if knob is None else [f"-DRE4DC_ACTOR_SETUP_LEAN={knob}"]
            label = name + "-" + arm
            for suffix, phase in (("ii", ["-E", "-P"]), ("o", ["-c", "-fstack-usage"])):
                target = output/(label+"."+suffix)
                builder.run([*common, *extra, "-x", "c++", "-", *phase, "-o", target],
                            cwd=SOURCE.parent, source=content, label=label)
                row = dict(bytes=target.stat().st_size, sha256=build_profile.sha(target))
                if suffix == "o":
                    row.update(build_profile.sections(target))
                    row["stack_usage"] = build_profile.stack_usage(target.with_suffix(".su"))
                records[arm+"."+suffix] = row
                if arm in ("absent", "zero"):
                    assert target.read_bytes() == (output/(name+"-baseline."+suffix)).read_bytes(), (label, suffix, "OFF identity")
            if arm in ("baseline", "on"):
                (output/(label+".disassembly.txt")).write_bytes(builder.run(
                    [str(compiler).removesuffix("g++")+"objdump", "-drC", output/(label+".o")], label=label+"-objdump"))
        production[name] = records
        print("PASS", name, flush=True)
    for path, digest in source_hashes.items():
        assert build_profile.sha(ROOT/path) == digest, (path, "changed during complete TU build")
    report = dict(status="PASS", baseline=args.baseline, knob="ACTOR_SETUP_LEAN", scope=__doc__,
        compiler=builder.run([compiler, "--version"], label="compiler").decode().splitlines()[0],
        make_identity=make_checks, unchanged_runtime_includes=include_checks, source_sha256=source_hashes,
        profile=profile, baseline_profile=old_profile, zero_profile=zero_profile, on_profile=on_profile,
        production=production)
    (output/"build-controls.json").write_text(json.dumps(report, indent=2)+"\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sh4-cxx", required=True, type=Path)
    parser.add_argument("--kos-root", required=True, type=Path)
    parser.add_argument("--sdk-root", required=True, type=Path)
    parser.add_argument("--baseline", default=BASELINE)
    result = run(parser.parse_args())
    print(json.dumps(dict(status=result["status"], variants=6, off_identity_comparisons=24)))


if __name__ == "__main__":
    main()
