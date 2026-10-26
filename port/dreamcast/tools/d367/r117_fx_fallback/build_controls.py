#!/usr/bin/env python3
"""Make-derived SH4 complete-TU identity and composition for the r117 fallback.

Uses the established effect profile expander with the release selected by
build-public.sh and every ordered literal CH2 append in the current rr recipe.
No private assets, SDK mutation, link, emulator run, or hardware timing claim.
All generated files go under --output.
"""
import argparse
import importlib.util
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
BASELINE = "db222fc618045fc1da2bb3c7222743f83612ed1b"
KNOB = "R117_FX_QUALIFIED_FALLBACK"
DEFINE = "RE4DC_" + KNOB
spec = importlib.util.spec_from_file_location("r117_effect_profile", HERE.parent / "esp_setup_lean/build_profile.py")
profile = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = profile
spec.loader.exec_module(profile)
ESP = ("esp_sub", "src/game/esp_sub.o", "../../../src/game/esp_sub.cpp", "src/game/esp_sub.cpp")
UI = ("native_ui", "platform/native_ui.o", "platform/native_ui.cpp", "port/dreamcast/game/platform/native_ui.cpp")


def recipe_inputs(output):
    """Read the selected public release and today's ordered literal CH2 appends."""
    tree, dc = profile.ROOT, profile.DC
    assets = dc / "game/public-assets"
    script = dc / "tools/d367/build-r21.sh"
    recipe = dc / "tools/d367/rr/recipe.conf"
    public_file = dc / "build-public.sh"
    public = public_file.read_text()
    selected = re.findall(r'^RELEASE_KNOBS=\$\{RELEASE_KNOBS:-\$PORT/([^}]+)\}$', public, re.MULTILINE)
    assert len(selected) == 1, "public release selection changed"
    release = dc / selected[0]
    body = script.read_text().split("R21=(\n", 1)[1].split("\n)", 1)[0]
    for before, after in {"$ASSETS": assets, "$ROOT": tree,
                          "$OBJDIR": output / "obj", "$OUT": output}.items():
        body = body.replace(before, str(after))
    base = shlex.split(body, comments=True)
    assert not any("$" in word for word in base)
    knobs = [line.replace("@ASSETS@", str(assets)) for line in release.read_text().splitlines()
             if line and not line.startswith("#")]
    body, ch2, assignments = recipe.read_text(), [], []
    for line in body.splitlines():
        if not line.startswith("CH2="):
            continue
        match = re.fullmatch(r'CH2="([^"\n]*)"(?:\s*#.*)?', line)
        assert match, "nonliteral CH2 assignment"
        words = shlex.split(match.group(1))
        if words and words[0] == "$CH2":
            assert ch2, "CH2 append before initialization"
            words = words[1:]
        else:
            assert not ch2, "multiple CH2 initializers"
        assert all(re.fullmatch(r"[A-Z0-9_]+=[^\s$`]+", word) for word in words)
        ch2 += words
        assignments.append(line)
    assert ch2
    # The existing helper predates these public no-private-assets overrides.
    extra_off = ["LEON_PS2_RIG=0", "LEON_PS2_PORTRAIT_HAIR=0", "ACTOR_GANADO_PS2_GRIP=0"]
    assert all(word in public for word in [*profile.PUBLIC_OFF, *extra_off])
    removed = [word for word in [*knobs, *ch2] if word.startswith(profile.PRIVATE_PATHS)]
    knobs = [word for word in knobs if not word.startswith(profile.PRIVATE_PATHS)]
    public_ch2 = [word for word in ch2 if not word.startswith(profile.PRIVATE_PATHS)]
    inputs = [script, release, recipe, public_file, dc / "kos-env.sh", dc / "game/Makefile",
              *sorted((dc / "game").glob("*.mk"))]
    metadata = dict(release=str(release.relative_to(tree)), release_sha256=profile.sha(release),
        recipe=str(recipe.relative_to(tree)), recipe_sha256=profile.sha(recipe),
        ordered_ch2_assignments=assignments, current_ch2=ch2, public_ch2=public_ch2, removed_asset_path_assignments=removed,
        missing_asset_overrides=[*profile.PUBLIC_OFF, *extra_off],
        source_sha256={str(path.relative_to(tree)): profile.sha(path) for path in inputs})
    return [*base, *knobs, *public_ch2, *profile.PUBLIC_OFF, *extra_off], metadata


profile.recipe_inputs = recipe_inputs
profile.__doc__ = ("Make-derived currently selected public release plus ordered current rr CH2 assignments. "
                   "The r117 controls override only the named FX level, early-filter and feature arms; "
                   "private generated assets use the documented public fallbacks.")


def normalize(flags, directory, tree):
    return [word.replace(str(directory), "<PROFILE>").replace(str(tree), "<SOURCE>") for word in flags]


def headers(receipt, directory):
    return {str(Path(path).relative_to(directory)): digest
            for path, digest in receipt["generated_headers"].items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sh4-cxx", required=True, type=Path)
    parser.add_argument("--kos-root", required=True, type=Path)
    parser.add_argument("--sdk-root", required=True, type=Path)
    parser.add_argument("--baseline", default=BASELINE)
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    tree = out / "baseline-tree"; tree.mkdir()
    archive = subprocess.check_output(["git", "archive", args.baseline], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        stream.extractall(tree, filter="data")
    compiler, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    builder = profile.Build(out)
    paths = [ESP[3], UI[3], "port/dreamcast/game/effects30.mk",
             "src/game/ps2_fx_population.h", "port/dreamcast/tools/d367/rr/recipe.conf",
             "port/dreamcast/build-public.sh", str(Path(__file__).resolve().relative_to(ROOT))]
    hashes = {path: profile.sha(ROOT / path) for path in paths}
    results, profiles, comparisons = {}, {}, 0
    for level, lean in ((3, 0), (3, 1), (0, 1)):
        name = f"fx{level}-lean{lean}"
        old_dir, new_dir = out / (name + "-base-profile"), out / (name + "-profile")
        extra = [f"FX_LEVEL={level}", f"ESP_SETUP_LEAN={lean}"]
        with profile.source_tree(tree):
            old_flags, old_profile = profile.derive(old_dir, compiler, kos, sdk,
                fx_level=level, overrides=extra, specs=(ESP, UI))
        _, new_profile = profile.derive(new_dir, compiler, kos, sdk,
            fx_level=level, overrides=extra, specs=(ESP, UI))
        for field in ("release", "release_sha256", "ordered_ch2_assignments"):
            assert old_profile["recipe_inputs"][field] == new_profile["recipe_inputs"][field], field
        profiles[name] = dict(baseline=old_profile, current=new_profile, overrides=extra)
        arms, metadata = {}, {}
        for arm, values in (("absent", []), ("zero", [KNOB + "=0"]), ("on", [KNOB + "=1"])):
            arms[arm], metadata[arm] = profile.expand_existing(new_dir, compiler, sdk,
                new_profile, values, prefix=name + "-" + arm, specs=(ESP, UI))
            for target in ("esp_sub", "native_ui"):
                actual = normalize(arms[arm][target], new_dir, ROOT)
                flag = "-D" + DEFINE + "=1"
                assert actual.count(flag) == int(arm == "on" and target == "esp_sub")
                assert [word for word in actual if word != flag] == normalize(old_flags[target], old_dir, tree)
                assert headers(metadata[arm][target], new_dir) == headers(old_profile[target], old_dir)
        # Compile the affected TU in every arm; for the unaffected queue TU the
        # equal complete command + header hashes are retained above.
        results[name] = {}
        for arm in ("baseline", "absent", "zero", "on"):
            root = tree if arm == "baseline" else ROOT
            flags = old_flags["esp_sub"] if arm == "baseline" else arms[arm]["esp_sub"]
            if arm == "zero": flags = [*flags, "-D" + DEFINE + "=0"]
            source = root / ESP[3]
            results[name][arm] = {}
            for suffix, phase in (("ii", ["-E", "-P"]), ("o", ["-c", "-fstack-usage"])):
                dest = out / (name + "-" + arm + "." + suffix)
                builder.run([*flags, "-x", "c++", "-", *phase, "-o", dest],
                            cwd=source.parent, source=source.read_bytes(), label=name + "-" + arm)
                record = dict(bytes=dest.stat().st_size, sha256=profile.sha(dest))
                if suffix == "o":
                    record.update(profile.sections(dest))
                    record["stack_usage"] = profile.stack_usage(dest.with_suffix(".su"))
                results[name][arm][suffix] = record
                if arm in ("absent", "zero"):
                    assert dest.read_bytes() == (out / (name + "-baseline." + suffix)).read_bytes(), (name, arm, suffix)
                    comparisons += 1
        print("PASS complete-TU identity and target compile:", name, flush=True)
    # The new base's optional r200 selector stays in the actual batch/scalar TU.
    # Compile both affected and queue TUs with both knobs enabled.
    variant_dir = out / "r200-profile"
    flags, receipt = profile.derive(variant_dir, compiler, kos, sdk, fx_level=3,
        overrides=["FX_LEVEL=3", KNOB + "=1", "ESP_SETUP_LEAN=1", "FX_R200_ENTRY_CAP=1"],
        specs=(ESP, UI))
    assert "-D" + DEFINE + "=1" in flags["esp_sub"]
    assert "-DRE4DC_FX_R200_ENTRY_CAP=1" in flags["native_ui"]
    composition = dict(profile=receipt, results={})
    for target, _, _, path in (ESP, UI):
        source, obj = ROOT / path, out / ("r200-" + target + ".o")
        builder.run([*flags[target], "-x", "c++", "-", "-c", "-fstack-usage", "-o", obj],
                    cwd=source.parent, source=source.read_bytes(), label="r200-" + target)
        composition["results"][target] = dict(sha256=profile.sha(obj), **profile.sections(obj),
            stack_usage=profile.stack_usage(obj.with_suffix(".su")))
        print("PASS target r200 composition:", target, flush=True)
    assert hashes == {path: profile.sha(ROOT / path) for path in paths}
    report = dict(status="PASS", scope=__doc__, baseline=args.baseline,
        selected_release=profiles["fx3-lean0"]["current"]["recipe_inputs"]["release"],
        selected_release_sha256=profiles["fx3-lean0"]["current"]["recipe_inputs"]["release_sha256"],
        source_sha256=hashes, off_identity_comparisons=comparisons,
        compiler=builder.run([compiler, "--version"], label="compiler").decode().splitlines()[0],
        compiler_sha256=profile.sha(compiler), profiles=profiles, results=results,
        r200_composition=composition)
    (out / "build-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", off_identity_comparisons=comparisons)))


if __name__ == "__main__":
    main()
