#!/usr/bin/env python3
"""Make-derived public Test22 effect profiles, including the current rr recipe.

FX_LEVEL=3 means room level zero plus the Essential runtime boot flag. Derive
both this profile and FX_LEVEL=0 with FX_TRIM=1 in separate output directories
so their generated effects headers cannot be accidentally shared.
"""
import argparse
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import re
import shlex
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
_spec = importlib.util.spec_from_file_location(
    "esp_public_profile_helpers", HERE.parent / "world_submit_spike/build_profile.py")
helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(helpers)
Build, sections, sha, stack_usage = helpers.Build, helpers.sections, helpers.sha, helpers.stack_usage

PRIVATE_PATHS = ("PS2_LEON_DIR=", "PS2_GANADO_DIR=", "GANADO_LOD_PACK=", "LEON_HEADLESS_DIR=",
                 "PS2_ENEMY_CH22_DIR=", "PS2_ENEMY_CH23_DIR=", "ACTOR_GANADO_PS2_STUMP_DIR=")
PUBLIC_OFF = ("PS2_LEON=0 LEON_HAND_PACK=0 PS2_GANADO=0 PS2_GANADO_LIT=0 GANADO_LOD=0 "
              "GANADO_EVENT_KEEP_LOD=0 ACTOR_PROBE_LIGHT=1 GANADO_LIT=0 NATIVE_MODEL_REGISTRY_DYING=0 "
              "LEON_HEADLESS=0 PS2_CH2_ENEMY=0 ACTOR_GANADO_PS2_STUMP=0").split()
SPECIFICATIONS = (
    ("esp", "src/game/esp.o", "../../../src/game/esp.cpp", "src/game/esp.cpp"),
    ("esp_sub", "src/game/esp_sub.o", "../../../src/game/esp_sub.cpp", "src/game/esp_sub.cpp"),
    ("esp_app", "src/game/esp_app.o", "../../../src/game/esp_app.cpp", "src/game/esp_app.cpp"),
    ("native_ui", "platform/native_ui.o", "platform/native_ui.cpp", "port/dreamcast/game/platform/native_ui.cpp"),
)


@contextmanager
def source_tree(tree):
    """Point the existing Make expanders at an independent archived source."""
    modules = (sys.modules[__name__], helpers, helpers.release_profile)
    saved = [(module, module.ROOT, module.DC) for module in modules]
    try:
        for module in modules:
            module.ROOT, module.DC = tree, tree / "port/dreamcast"
        yield
    finally:
        for module, root, dc in saved:
            module.ROOT, module.DC = root, dc


def recipe_inputs(output):
    assets = DC / "game/public-assets"
    script = DC / "tools/d367/build-r21.sh"
    release = DC / "tools/d367/test22/release-knobs.txt"
    recipe = DC / "tools/d367/rr/recipe.conf"
    public = DC / "build-public.sh"
    body = script.read_text().split("R21=(\n", 1)[1].split("\n)", 1)[0]
    for before, after in {"$ASSETS": assets, "$ROOT": ROOT,
                          "$OBJDIR": output / "obj", "$OUT": output}.items():
        body = body.replace(before, str(after))
    base = shlex.split(body, comments=True)
    assert not any("$" in word for word in base), "unresolved R21 expansion"
    knobs = [line.replace("@ASSETS@", str(assets)) for line in release.read_text().splitlines()
             if line and not line.startswith("#")]
    ch2_lines = re.findall(r'^CH2="([^"\n]*)"$', recipe.read_text(), re.MULTILINE)
    assert len(ch2_lines) == 1, "expected a literal CH2 assignment"
    ch2 = shlex.split(ch2_lines[0])
    assert all(re.fullmatch(r"[A-Z0-9_]+=[^\s$`]+", word) for word in ch2), "nonliteral CH2 value"
    removed = [word for word in [*knobs, *ch2] if word.startswith(PRIVATE_PATHS)]
    knobs = [word for word in knobs if not word.startswith(PRIVATE_PATHS)]
    ch2_public = [word for word in ch2 if not word.startswith(PRIVATE_PATHS)]
    assert all(word in public.read_text() for word in PUBLIC_OFF), "public fallback changed"
    inputs = [script, release, recipe, public, DC / "kos-env.sh", DC / "game/Makefile",
              *sorted((DC / "game").glob("*.mk"))]
    metadata = dict(recipe=str(recipe.relative_to(ROOT)), recipe_sha256=sha(recipe),
        current_ch2=ch2, public_ch2=ch2_public, removed_asset_path_assignments=removed,
        missing_asset_overrides=PUBLIC_OFF,
        source_sha256={str(path.relative_to(ROOT)): sha(path) for path in inputs})
    return [*base, *knobs, *ch2_public, *PUBLIC_OFF], metadata


def target_flags(kos):
    values = ["-O2", "-fno-PIC", "-fno-PIE", "-fomit-frame-pointer", "-m4-single", "-ml",
              "-mfsrra", "-mfsca", "-ffunction-sections", "-fdata-sections",
              "-matomic-model=soft-gusa", "-ftls-model=local-exec", "-D__DREAMCAST__"]
    for path in (kos / "include", kos / "kernel/arch/dreamcast/include", kos / "addons/include"):
        values += ["-isystem", str(path)]
    return [*values, "-D_arch_dreamcast=1", "-D_arch_sub_pristine=1", "-Wall"]


def expand_existing(output, compiler, sdk, receipt, overrides=(), *, prefix="esp", specs=SPECIFICATIONS):
    source = dict(receipt["seed"])
    source["command"] = [*source["command"], *overrides]
    flags, profiles = {}, {}
    for name, target, relative, _ in specs:
        flags[name], profiles[name] = helpers.expand(output, compiler, sdk, output / "kos-overlay",
            source, prefix + "-" + name, target, relative)
    return flags, profiles


def derive(output, compiler, kos, sdk, *, fx_level, overrides=(), specs=SPECIFICATIONS):
    assert fx_level in (0, 3)
    output.mkdir(parents=True, exist_ok=False)
    assignments, metadata = recipe_inputs(output)
    target = output / "obj/platform/native_static.o"
    command = ["make", "--no-print-directory", "-n", str(target), *assignments,
               "FX_TRIM=1", f"FX_LEVEL={fx_level}", *overrides,
               "KOS_CFLAGS=" + shlex.join(target_flags(kos)), "KOS_BASE=" + str(kos),
               "KOS_LDFLAGS=-T" + str(kos / "utils/ldscripts/shlelf.xc"),
               "SH4ZAM_DIR=" + str(sdk), "--assume-old=" + str(output / "obj/modules.mk")]
    _, patch_receipt = helpers.pvr_overlay(output, kos)
    seed = dict(seed=dict(command=command))
    flags, profiles = expand_existing(output, compiler, sdk, seed, specs=specs)
    receipt = dict(scope=__doc__, fx_level=fx_level, fx_trim=1,
        essential_boot=int(fx_level == 3), debug_records=False, modules_manifest_not_built=True,
        kos_library_patch_checks_not_executed=True, pvr_header_overlay=patch_receipt,
        recipe_inputs=metadata, seed=seed["seed"], **profiles)
    (output / "esp-profile.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return flags, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sh4-cxx", type=Path, required=True)
    parser.add_argument("--kos-root", type=Path, required=True)
    parser.add_argument("--sdk-root", type=Path, required=True)
    parser.add_argument("--fx-level", type=int, choices=(0, 3), required=True)
    parser.add_argument("--override", action="append", default=[])
    args = parser.parse_args()
    flags, receipt = derive(args.output.resolve(), args.sh4_cxx.resolve(), args.kos_root.resolve(),
                            args.sdk_root.resolve(), fx_level=args.fx_level, overrides=args.override)
    print(json.dumps(dict(status="PASS", translation_units=list(flags), fx_level=args.fx_level,
        profile=str(args.output.resolve() / "esp-profile.json"),
        recipe_sha256=receipt["recipe_inputs"]["recipe_sha256"])))


if __name__ == "__main__":
    main()
