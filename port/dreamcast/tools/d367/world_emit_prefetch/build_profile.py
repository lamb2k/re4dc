#!/usr/bin/env python3
"""Make-derived public Test22 world profile with the current rr CH2 overrides.

The release-knobs file is the established public Test22 starting point. The
current recipe.conf CH2 values are appended before the public asset overrides,
so release changes made after that file (including the three world switches)
are present in the actual Make expansion. No shell script is sourced.
"""
import argparse
import hashlib
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
    "emit_public_profile_helpers", HERE.parent / "world_submit_spike/build_profile.py")
helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(helpers)
Build, sections, sha, stack_usage = helpers.Build, helpers.sections, helpers.sha, helpers.stack_usage

PRIVATE_PATHS = ("PS2_LEON_DIR=", "PS2_GANADO_DIR=", "GANADO_LOD_PACK=", "LEON_HEADLESS_DIR=",
                 "PS2_ENEMY_CH22_DIR=", "PS2_ENEMY_CH23_DIR=", "ACTOR_GANADO_PS2_STUMP_DIR=")
PUBLIC_OFF = ("PS2_LEON=0 LEON_HAND_PACK=0 PS2_GANADO=0 PS2_GANADO_LIT=0 GANADO_LOD=0 "
              "GANADO_EVENT_KEEP_LOD=0 ACTOR_PROBE_LIGHT=1 GANADO_LIT=0 NATIVE_MODEL_REGISTRY_DYING=0 "
              "LEON_HEADLESS=0 PS2_CH2_ENEMY=0 ACTOR_GANADO_PS2_STUMP=0").split()
SPECIFICATIONS = (("native_static", "platform/native_static.o", "platform/native_static.cpp"),
                  ("native_ui", "platform/native_ui.o", "platform/native_ui.cpp"),
                  ("chunk_submit", "platform/chunk_submit.o", "platform/chunk_submit.cpp"))


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
    assert len(ch2_lines) == 1, "expected one literal CH2 assignment"
    ch2 = shlex.split(ch2_lines[0])
    assert all(re.fullmatch(r"[A-Z0-9_]+=[^\s$`]+", word) for word in ch2), "non-literal CH2 value"
    removed = [word for word in [*knobs, *ch2] if word.startswith(PRIVATE_PATHS)]
    knobs = [word for word in knobs if not word.startswith(PRIVATE_PATHS)]
    ch2_public = [word for word in ch2 if not word.startswith(PRIVATE_PATHS)]
    assert all(word in public.read_text() for word in PUBLIC_OFF), "public asset fallback changed"
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


def expand_existing(output, compiler, sdk, receipt, overrides=(), *, prefix="emit", dependencies=False):
    source = dict(receipt["native_static"])
    source["command"] = [*source["command"], *overrides]
    specs = list(SPECIFICATIONS)
    if dependencies:
        specs += [("texture_package", "native-reuse/texture_package.o", "../room/texture_package.cpp"),
                  ("pvr_geometry", "native-reuse/pvr_geometry.o", "../room/pvr_geometry.cpp")]
    flags, profiles = {}, {}
    for name, target, path in specs:
        flags[name], profiles[name] = helpers.expand(output, compiler, sdk, output / "kos-overlay",
            source, prefix + "-" + name, target, path)
    return flags, profiles


def derive(output, compiler, kos, sdk, *, overrides=(), dependencies=False):
    output.mkdir(parents=True, exist_ok=False)
    assignments, metadata = recipe_inputs(output)
    target = output / "obj/platform/native_static.o"
    command = ["make", "--no-print-directory", "-n", str(target), *assignments, *overrides,
               "KOS_CFLAGS=" + shlex.join(target_flags(kos)), "KOS_BASE=" + str(kos),
               "KOS_LDFLAGS=-T" + str(kos / "utils/ldscripts/shlelf.xc"),
               "SH4ZAM_DIR=" + str(sdk), "--assume-old=" + str(output / "obj/modules.mk")]
    _, patch_receipt = helpers.pvr_overlay(output, kos)
    seed = dict(native_static=dict(command=command))
    flags, profiles = expand_existing(output, compiler, sdk, seed, dependencies=dependencies)
    receipt = dict(scope=__doc__, debug_records=False, modules_manifest_not_built=True,
        kos_library_patch_checks_not_executed=True, pvr_header_overlay=patch_receipt,
        recipe_inputs=metadata, **profiles)
    (output / "emit-profile.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return flags, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sh4-cxx", type=Path, required=True)
    parser.add_argument("--kos-root", type=Path, required=True)
    parser.add_argument("--sdk-root", type=Path, required=True)
    parser.add_argument("--override", action="append", default=[])
    args = parser.parse_args()
    flags, receipt = derive(args.output.resolve(), args.sh4_cxx.resolve(), args.kos_root.resolve(),
                            args.sdk_root.resolve(), overrides=args.override)
    print(json.dumps(dict(status="PASS", translation_units=list(flags),
        profile=str(args.output.resolve() / "emit-profile.json"),
        recipe_sha256=receipt["recipe_inputs"]["recipe_sha256"])))


if __name__ == "__main__":
    main()
