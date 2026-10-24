#!/usr/bin/env python3
"""Compile the complete motion TU and prove default-OFF identity to integration.

The base Make recipe and source are independently materialized with git archive.
Its full preprocessed TU and raw object are compared with current absent and
explicit-zero arms. The matrix crosses the supported Hermite sampler and diagnostic variants. No geometry data, target executable or private assets are used.
"""
import argparse
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
SOURCE = ROOT / "src/game/motion.cpp"
BASELINE = "d5c1ceab9e06461462669b3ce1d28a379747a74a"
import build_profile


def normalized_flags(flags, profile_root, source_root):
    return [word.replace(str(profile_root), "<PROFILE>").replace(str(source_root), "<SOURCE>")
            for word in flags]


def header_hashes(row, profile_root):
    return {str(Path(path).relative_to(profile_root)): digest
            for path, digest in row["generated_headers"].items()}


def archive_tree(destination, baseline):
    destination.mkdir()
    archive = subprocess.check_output(["git", "archive", baseline], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        source.extractall(destination, filter="data")


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    compiler, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    tree = output / "baseline-tree"
    archive_tree(tree, args.baseline)
    with build_profile.source_tree(tree):
        old_flags, old_profile = build_profile.derive(output / "baseline-profile", compiler, kos, sdk)
    current = {}
    for arm, lean in (("absent", None), ("zero", 0), ("on", 1)):
        current[arm] = build_profile.derive(output / (arm + "-profile"), compiler, kos, sdk, lean=lean)
    checks = {}
    for name in old_flags:
        reference = normalized_flags(old_flags[name], output / "baseline-profile", tree)
        source_headers = header_hashes(old_profile["profiles"][name], output / "baseline-profile")
        for arm, (flags, profile) in current.items():
            normalized = normalized_flags(flags[name], output / (arm + "-profile"), ROOT)
            if arm == "on":
                assert normalized.count("-DRE4DC_ANIM_SAMPLE_LEAN=1") == 1, (name, "missing Make knob")
                normalized.remove("-DRE4DC_ANIM_SAMPLE_LEAN=1")
            assert normalized == reference, (name, arm, "unexpected Make flags")
            assert header_hashes(profile["profiles"][name], output / (arm + "-profile")) == source_headers, (
                name, arm, "unexpected generated headers")
        checks[name] = dict(flags_identical_off=True, generated_headers_identical=True, on_adds_only_knob=True)

    watched = [SOURCE, DC / "game/game30.mk"]
    hashes = {str(path.relative_to(ROOT)): build_profile.sha(path) for path in watched}
    builder = build_profile.Build(output)
    production = {}
    baseline_source = tree / SOURCE.relative_to(ROOT)
    for name in old_flags:
        rows = {}
        for arm in ("baseline", "absent", "zero", "on"):
            source = baseline_source if arm == "baseline" else SOURCE
            flags = old_flags[name] if arm == "baseline" else current[arm][0][name]
            # Make's zero emits no define; explicitly defining zero also proves
            # that conditional compilation did not accidentally use #ifdef.
            extra = ["-DRE4DC_ANIM_SAMPLE_LEAN=0"] if arm == "zero" else []
            label = name + "-" + arm
            for suffix, phase in (("ii", ["-E", "-P"]), ("o", ["-c", "-fstack-usage"])):
                target = output / (label + "." + suffix)
                builder.run([*flags, *extra, "-x", "c++", "-", *phase, "-o", target],
                            cwd=source.parent, source=source.read_bytes(), label=label + "-" + suffix)
                row = dict(bytes=target.stat().st_size, sha256=build_profile.sha(target))
                if suffix == "o":
                    row.update(build_profile.sections(target))
                    row["stack_usage"] = build_profile.stack_usage(target.with_suffix(".su"))
                rows[arm + "." + suffix] = row
                if arm in ("absent", "zero"):
                    assert target.read_bytes() == (output / (name + "-baseline." + suffix)).read_bytes(), (
                        label, suffix, "OFF identity")
            if arm == "on" and name in ("reg0", "reference", "asm1"):
                for suffix in ("ii", "o"):
                    assert (output / (label + "." + suffix)).read_bytes() == (output / (name + "-baseline." + suffix)).read_bytes(), (name, "inactive ON fallback", suffix)
            if arm in ("baseline", "on"):
                (output / (label + ".disassembly.txt")).write_bytes(builder.run(
                    [str(compiler).removesuffix("g++") + "objdump", "-drC", output / (label + ".o")],
                    label=label + "-objdump"))
        production[name] = rows
        print("PASS", name, flush=True)
    for path, digest in hashes.items():
        assert build_profile.sha(ROOT / path) == digest, (path, "changed during full TU build")
    report = dict(status="PASS", baseline=args.baseline, knob="ANIM_SAMPLE_LEAN", scope=__doc__,
        compiler=builder.run([compiler, "--version"], label="compiler").decode().splitlines()[0],
        make_identity=checks, source_sha256=hashes, production=production, baseline_profile=old_profile,
        profiles={arm: profile for arm, (_, profile) in current.items()},
        off_identity_comparisons=len(production) * 4, inactive_on_identity_comparisons=6)
    (output / "build-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--baseline", default=BASELINE)
    result = run(parser.parse_args())
    print(json.dumps(dict(status=result["status"], variants=len(result["production"]),
                          off_identity_comparisons=result["off_identity_comparisons"])))


if __name__ == "__main__":
    main()
