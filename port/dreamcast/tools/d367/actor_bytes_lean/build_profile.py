#!/usr/bin/env python3
"""Make-derived Test22 public actor profiles, including current rr CH2 settings.

Direct-off is an explicit compatibility profile because the release's grouped
submit/transaction options require direct submission. The data-byte candidate
is independently combined with ACTOR_SETUP_LEAN and the backface-cone option.
No private asset directory, source mirror or unmerged-branch module is used.
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


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


helpers = module("actor_bytes_public_helpers", HERE.parent / "world_submit_spike/build_profile.py")
old_actor = module("actor_bytes_compatibility", HERE.parent / "actor_setup_lean/build_profile.py")
Build, sections, sha, stack_usage = helpers.Build, helpers.sections, helpers.sha, helpers.stack_usage
DIRECT_OFF = old_actor.DIRECT_OFF
PRIVATE_PATHS = ("PS2_LEON_DIR=", "PS2_GANADO_DIR=", "GANADO_LOD_PACK=", "LEON_HEADLESS_DIR=",
                 "PS2_ENEMY_CH22_DIR=", "PS2_ENEMY_CH23_DIR=", "ACTOR_GANADO_PS2_STUMP_DIR=")
PUBLIC_OFF = ("PS2_LEON=0 LEON_HAND_PACK=0 PS2_GANADO=0 PS2_GANADO_LIT=0 GANADO_LOD=0 "
              "GANADO_EVENT_KEEP_LOD=0 ACTOR_PROBE_LIGHT=1 GANADO_LIT=0 NATIVE_MODEL_REGISTRY_DYING=0 "
              "LEON_HEADLESS=0 PS2_CH2_ENEMY=0 ACTOR_GANADO_PS2_STUMP=0").split()


@contextmanager
def source_tree(tree):
    modules = (sys.modules[__name__], helpers, helpers.release_profile)
    saved = [(m, m.ROOT, m.DC) for m in modules]
    try:
        for m in modules:
            m.ROOT, m.DC = tree, tree / "port/dreamcast"
        yield
    finally:
        for m, root, dc in saved:
            m.ROOT, m.DC = root, dc


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
    assert len(ch2_lines) == 1, "expected literal CH2 assignment"
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


def derive(output, compiler, kos, sdk, *, setup_values=(0, 1), direct_values=(0, 1),
           cone_values=(0, 1), lean=None, overrides=()):
    output.mkdir(parents=True, exist_ok=False)
    overlay, patch_receipt = helpers.pvr_overlay(output, kos)
    profiles, records, recipe = {}, {}, None
    for setup in setup_values:
        for direct in direct_values:
            for cone in cone_values:
                name = f"s{setup}-d{direct}-c{cone}"
                destination = output / name
                destination.mkdir()
                assignments, recipe = recipe_inputs(destination)
                changes = [f"ACTOR_SETUP_LEAN={setup}", f"NATIVE_ACTOR_DIRECT={direct}",
                           f"ACTOR_BACKFACE_CONE={cone}", "ACTOR_BACKFACE=0"]
                if not direct:
                    changes += [knob + "=0" for knob in DIRECT_OFF]
                if lean is not None:
                    changes.append(f"ACTOR_BYTES_LEAN={lean}")
                changes += list(overrides)
                command = ["make", "--no-print-directory", "-n", str(destination / "obj/platform/native_actor_fast.o"),
                    *assignments, *changes, "KOS_CFLAGS=" + shlex.join(target_flags(kos)), "KOS_BASE=" + str(kos),
                    "KOS_LDFLAGS=-T" + str(kos / "utils/ldscripts/shlelf.xc"), "SH4ZAM_DIR=" + str(sdk),
                    "--assume-old=" + str(destination / "obj/modules.mk")]
                profiles[name], row = helpers.expand(destination, compiler, sdk, overlay, dict(command=command),
                    "actor", "platform/native_actor_fast.o", "platform/native_actor_fast.cpp")
                row.update(setup=setup, direct=direct, cone=cone,
                    compatibility_profile=not bool(direct), variant_overrides=changes, seed_command=command)
                records[name] = row
    receipt = dict(scope=__doc__, profiles=records, recipe_inputs=recipe, pvr_header_overlay=patch_receipt,
        debug_records=False, modules_manifest_not_built=True, kos_library_patch_checks_not_executed=True)
    (output / "actor-profile.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return profiles, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--setup", nargs="+", type=int, choices=(0, 1), default=[0, 1])
    parser.add_argument("--direct", nargs="+", type=int, choices=(0, 1), default=[0, 1])
    parser.add_argument("--cone", nargs="+", type=int, choices=(0, 1, 2), default=[0, 1])
    parser.add_argument("--lean", type=int, choices=(0, 1))
    args = parser.parse_args()
    flags, receipt = derive(args.output.resolve(), args.sh4_cxx.resolve(), args.kos_root.resolve(),
        args.sdk_root.resolve(), setup_values=args.setup, direct_values=args.direct,
        cone_values=args.cone, lean=args.lean)
    print(json.dumps(dict(status="PASS", profiles=list(flags), profile=str(args.output.resolve() / "actor-profile.json"),
        recipe_sha256=receipt["recipe_inputs"]["recipe_sha256"])))


if __name__ == "__main__":
    main()
