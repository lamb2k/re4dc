#!/usr/bin/env python3
"""Make-derived public Test22 motion profiles, including the current rr recipe.

The real R21 and Test22 assignments, current CH2 literal recipe and public
asset fallbacks feed Make for src/game/motion.o. Debug records are omitted
consistently. No linked game, asset package or KOS library patch is built.
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
    "anim_public_profile_helpers", HERE.parent / "world_submit_spike/build_profile.py")
helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(helpers)
Build, sections, sha, stack_usage = helpers.Build, helpers.sections, helpers.sha, helpers.stack_usage

PRIVATE_PATHS = ("PS2_LEON_DIR=", "PS2_GANADO_DIR=", "GANADO_LOD_PACK=", "LEON_HEADLESS_DIR=",
                 "PS2_ENEMY_CH22_DIR=", "PS2_ENEMY_CH23_DIR=", "ACTOR_GANADO_PS2_STUMP_DIR=")
PUBLIC_OFF = ("PS2_LEON=0 LEON_HAND_PACK=0 PS2_GANADO=0 PS2_GANADO_LIT=0 GANADO_LOD=0 "
              "GANADO_EVENT_KEEP_LOD=0 ACTOR_PROBE_LIGHT=1 GANADO_LIT=0 NATIVE_MODEL_REGISTRY_DYING=0 "
              "LEON_HEADLESS=0 PS2_CH2_ENEMY=0 ACTOR_GANADO_PS2_STUMP=0").split()
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


PROFILES = {
    "reg1": [],
    "reg0": ["GAME_HF_REG=0"],
    "reg2": ["GAME_HF_REG=2"],
    "fast2": ["GAME_HERMITE_FAST=2"],
    "no_prefetch": ["GAME_HF_PF=0"],
    "reference": ["GAME_HERMITE_FAST=0", "GAME_HF_REG=0", "GAME_HF_INLINE=0", "GAME_HF_PF=0", "GAME_HF_ASM=0"],
    "asm1": ["GAME_HF_REG=0", "GAME_HF_ASM=1"],
}


def derive(output, compiler, kos, sdk, *, variants=None, lean=None):
    output.mkdir(parents=True, exist_ok=False)
    assignments, metadata = recipe_inputs(output)
    _, overlay_receipt = helpers.pvr_overlay(output, kos)
    profiles, rows = {}, {}
    for name in variants or PROFILES:
        destination = output / name
        destination.mkdir()
        changes = list(PROFILES[name])
        if lean is not None:
            changes.append(f"ANIM_SAMPLE_LEAN={lean}")
        # Every variant owns generated header paths. Changing only its actual
        # sampler switches leaves the rest of the public recipe unchanged.
        command = ["make", "--no-print-directory", "-n", str(destination / "obj/src/game/motion.o"),
            *[word.replace(str(output), str(destination)) for word in assignments], *changes,
            "KOS_CFLAGS=" + shlex.join(target_flags(kos)), "KOS_BASE=" + str(kos),
            "KOS_LDFLAGS=-T" + str(kos / "utils/ldscripts/shlelf.xc"),
            "SH4ZAM_DIR=" + str(sdk), "--assume-old=" + str(destination / "obj/modules.mk")]
        profiles[name], row = helpers.expand(destination, compiler, sdk, output / "kos-overlay",
            dict(command=command), "motion", "src/game/motion.o", "../../../src/game/motion.cpp")
        row.update(variant_overrides=changes, seed_command=command)
        rows[name] = row
    receipt = dict(scope=__doc__, profiles=rows, recipe_inputs=metadata,
        pvr_header_overlay=overlay_receipt, debug_records=False, modules_manifest_not_built=True,
        kos_library_patch_checks_not_executed=True)
    (output / "motion-profile.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return profiles, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--variant", action="append", choices=list(PROFILES))
    parser.add_argument("--lean", type=int, choices=(0, 1))
    args = parser.parse_args()
    flags, receipt = derive(args.output.resolve(), args.sh4_cxx.resolve(), args.kos_root.resolve(),
        args.sdk_root.resolve(), variants=args.variant, lean=args.lean)
    print(json.dumps(dict(status="PASS", profiles=list(flags),
        profile=str(args.output.resolve() / "motion-profile.json"),
        recipe_sha256=receipt["recipe_inputs"]["recipe_sha256"])))


if __name__ == "__main__":
    main()
