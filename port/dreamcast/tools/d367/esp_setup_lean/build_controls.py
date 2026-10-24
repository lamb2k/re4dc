#!/usr/bin/env python3
"""Complete-TU absent/zero identity and FX0/FX3 composition for ESP_SETUP_LEAN.

The baseline source and Make tree are archived independently. Debug records
and preprocessor line markers are consistently omitted; executable options
come from actual public-recipe Make expansions, including current CH2.
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
BASELINE = "a5e972e44096410253ad93164b84d92e3c22655a"
KNOB = "ESP_SETUP_LEAN"
DEFINE = "RE4DC_ESP_SETUP_LEAN"
import build_profile as profile


def normalize(flags, directory, tree):
    return [word.replace(str(directory), "<PROFILE>").replace(str(tree), "<SOURCE>") for word in flags]


def generated_headers(receipt, directory):
    return {str(Path(path).relative_to(directory)): digest
            for path, digest in receipt["generated_headers"].items()}


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    tree = output / "baseline-tree"
    tree.mkdir()
    archive = subprocess.check_output(["git", "archive", args.baseline], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        stream.extractall(tree, filter="data")
    compiler, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    builder = profile.Build(output)
    watched = [ROOT / spec[3] for spec in profile.SPECIFICATIONS]
    watched += [DC / "game/effects30.mk", DC / "game/platform/include/native_ui_fx_core_prep.inc",
                DC / "tools/d367/rr/recipe.conf", HERE / "build_profile.py", Path(__file__)]
    watched += [Path(path) for path in subprocess.check_output(
        ["git", "diff", "--name-only", args.baseline, "--", "src", "port/dreamcast/game"], cwd=ROOT,
        text=True).splitlines() if path]
    watched = [p if p.is_absolute() else ROOT / p for p in watched]
    hashes = {str(path.relative_to(ROOT)): profile.sha(path) for path in watched if path.is_file()}
    result, make_checks, profiles = {}, {}, {}
    comparisons, unaffected, on_targets = 0, 0, set()
    for level in (0, 3):
        key = f"fx{level}"
        old_dir, current_dir = output / (key + "-baseline-profile"), output / (key + "-profile")
        with profile.source_tree(tree):
            baseline_flags, baseline_profile = profile.derive(old_dir, compiler, kos, sdk, fx_level=level)
        _, current_profile = profile.derive(current_dir, compiler, kos, sdk, fx_level=level)
        profiles[key] = dict(baseline=baseline_profile, current=current_profile)
        arms, arm_profiles = {}, {}
        for arm, extras in (("absent", []), ("zero", [KNOB + "=0"]), ("on", [KNOB + "=1"])):
            arms[arm], arm_profiles[arm] = profile.expand_existing(current_dir, compiler, sdk,
                current_profile, extras, prefix=key + "-" + arm)
        result[key], make_checks[key] = {}, {}
        for name, _, _, path in profile.SPECIFICATIONS:
            before = normalize(baseline_flags[name], old_dir, tree)
            defined_on = False
            for arm in ("absent", "zero", "on"):
                after = normalize(arms[arm][name], current_dir, ROOT)
                if arm == "on":
                    flag = "-D" + DEFINE + "=1"
                    assert after.count(flag) <= 1
                    defined_on = flag in after
                    after = [word for word in after if word != flag]
                    if defined_on: on_targets.add(name)
                assert after == before, (key, name, arm, "unexpected Make flags")
                assert generated_headers(arm_profiles[arm][name], current_dir) == generated_headers(
                    baseline_profile[name], old_dir), (key, name, arm, "unexpected generated headers")
            make_checks[key][name] = dict(off_flags_and_headers_identical=True,
                on_adds_only_knob_define=defined_on)
            result[key][name] = {}
            for arm in ("baseline", "absent", "zero", "on"):
                source_root = tree if arm == "baseline" else ROOT
                flags = baseline_flags[name] if arm == "baseline" else arms[arm][name]
                if arm == "zero": flags = [*flags, "-D" + DEFINE + "=0"]
                body = (source_root / path).read_bytes()
                record = {}
                label = key + "-" + name + "-" + arm
                for suffix, phase in (("ii", ["-E", "-P"]), ("o", ["-c", "-fstack-usage"])):
                    dest = output / (label + "." + suffix)
                    builder.run([*flags, "-x", "c++", "-", *phase, "-o", dest],
                                cwd=(source_root / path).parent, source=body, label=label)
                    values = dict(bytes=dest.stat().st_size, sha256=profile.sha(dest))
                    if suffix == "o":
                        values.update(profile.sections(dest))
                        values["stack_usage"] = profile.stack_usage(dest.with_suffix(".su"))
                    record[suffix] = values
                    if arm in ("absent", "zero") or (arm == "on" and not defined_on):
                        base_path = output / (key + "-" + name + "-baseline." + suffix)
                        assert dest.read_bytes() == base_path.read_bytes(), (label, suffix, "identity")
                        if arm == "on": unaffected += 1
                        else: comparisons += 1
                result[key][name][arm] = record
            print("PASS", key, name, flush=True)
    assert on_targets, "The new Make knob did not enable any selected TU"
    variants = {}
    selected = tuple(spec for spec in profile.SPECIFICATIONS if spec[0] in ("esp_sub", "native_ui"))
    specifications = (
        # TA_GUARD and BIN/MATERIAL diagnostics conflict with this recipe's
        # headroom and runtime resolution contracts. TA_HASH alone exercises
        # the same full-packet fallback without changing release dependencies.
        ("diagnostics", ["TA_HASH=1", "FX_TRIM_LOG=1", "ESP_CENSUS=1"]),
        ("extra-batch-rtt", ["PS2_FX_COMMON_HAZE=1", "PVR_RTT=1"]),
    )
    for name, changes in specifications:
        directory = output / (name + "-profile")
        flags, receipt = profile.derive(directory, compiler, kos, sdk, fx_level=3,
            overrides=[KNOB + "=1", *changes], specs=selected)
        variants[name] = dict(overrides=changes, profile=receipt, results={})
        for target, _, _, path in selected:
            source = ROOT / path
            obj = output / (name + "-" + target + ".o")
            builder.run([*flags[target], "-x", "c++", "-", "-c", "-fstack-usage", "-o", obj],
                cwd=source.parent, source=source.read_bytes(), label=name + "-" + target)
            macros = builder.run([*flags[target], "-x", "c++", "-", "-E", "-dM"],
                cwd=source.parent, source=source.read_bytes(), label=name + "-" + target + "-macros").decode()
            active = {flag: ("#define " + flag + " 1") in macros
                for flag in ("RE4DC_ESP_SETUP_LEAN", "RE4DC_ESP_SETUP_BATCH", "RE4DC_ESP_ESSENTIAL_EARLY",
                             "RE4DC_PS2_FX_COMMON_HAZE", "RE4DC_PS2_FX_ADDITIONS", "RE4DC_PVR_RTT")}
            assert active["RE4DC_ESP_SETUP_LEAN"]
            if name == "diagnostics":
                assert not active["RE4DC_ESP_SETUP_BATCH"] and not active["RE4DC_ESP_ESSENTIAL_EARLY"]
            elif target == "native_ui":
                assert active["RE4DC_ESP_SETUP_BATCH"] and active["RE4DC_PS2_FX_COMMON_HAZE"] and active["RE4DC_PVR_RTT"]
            variants[name]["results"][target] = dict(sha256=profile.sha(obj), **profile.sections(obj),
                stack_usage=profile.stack_usage(obj.with_suffix(".su")), active_macros=active)
            print("PASS variant", name, target, flush=True)
    for path, digest in hashes.items():
        assert profile.sha(ROOT / path) == digest, (path, "source changed during build")
    report = dict(status="PASS", scope=__doc__, baseline=args.baseline,
        fx_levels=[0, 3], fx_trim=1, translation_units=len(profile.SPECIFICATIONS),
        off_identity_comparisons=comparisons, enabled_unaffected_tu_identities=unaffected,
        on_targets=sorted(on_targets), source_sha256=hashes, make_checks=make_checks, variants=variants,
        toolchain=dict(compiler=builder.run([compiler, "--version"], label="compiler").decode().splitlines()[0],
                       compiler_sha256=profile.sha(compiler)), profiles=profiles, results=result)
    (output / "build-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "fx_levels", "translation_units",
        "off_identity_comparisons", "enabled_unaffected_tu_identities", "on_targets")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sh4-cxx", type=Path, required=True)
    parser.add_argument("--kos-root", type=Path, required=True)
    parser.add_argument("--sdk-root", type=Path, required=True)
    parser.add_argument("--baseline", default=BASELINE)
    run(parser.parse_args())
