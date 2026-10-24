#!/usr/bin/env python3
"""Make-derived public Test22 UI/HUD/text profiles, including the current rr recipe.

The real R21 and Test22 assignments, current CH2 literal recipe and public
asset fallbacks feed Make for UI, bridge, ID and message objects. Debug records are omitted
consistently. No linked game, asset package or KOS library patch is built.
"""
import argparse
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
_spec = importlib.util.spec_from_file_location(
    "ui_public_profile_helpers", HERE.parent / "world_submit_spike/build_profile.py")
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
    "public": [],
    "quad_reference": ["UI_QUAD_LEAN=0"],
    "quad_check": ["UI_QUAD_LEAN=2"],
    "headers_off": ["UI_HEADERS=0"],
    "no_order": ["SS_UI_ORDER=0","WORLD_AUTOSORT=0","ITEM_UI_ORDER=0","UI_POLY_ORDER=0"],
    "no_messages": ["NATIVE_MES=0","RENDER_OPTION=0","RENDER_FSAA=0","VIEW_DIST_OPTION=0",
        "BENCHMARK=0","SPEED_VMU_OFF=0","MCHECK_SAFE=0"],
    "no_jitter": ["RENDER_FSAA=0","RENDER_DOUBLE=1"],
    "accepted_world": ["SCENERY_SELECT_LEAN2=1","SCENERY_UV_SNAPSHOT=1","ACTOR_SETUP_LEAN=1","SCENERY_EMIT_PREFETCH=1"],
    "world_stack_off": ["SCENERY_SELECT_ONLY=0","SCENERY_REPLAY_LEAN=0","SCENERY_SUBMIT_BATCH=0"],
}
SPECIFICATIONS = {
    "native_ui": ("platform/native_ui.o", "platform/native_ui.cpp"),
    "ui_bridge": ("ui_bridge.o", "ui_bridge.cpp"),
    "id_sys": ("src/game/id_sys.o", "../../../src/game/id_sys.cpp"),
    "mes": ("src/game/mes.o", "../../../src/game/mes.cpp"),
    "gx_stub": ("platform/gx_stub.o", "platform/gx_stub.cpp"),
    "pvr_geometry": ("native-reuse/pvr_geometry.o", "../room/pvr_geometry.cpp"),
}
PRIMARY_UNITS=("native_ui","ui_bridge","id_sys","mes","gx_stub")


def derive_math(output, compiler, kos, sdk):
    """Expand the real C SDK recipe and existing SH4 identity assembly recipe."""
    output.mkdir(parents=True,exist_ok=False)
    assignments,metadata=recipe_inputs(output)
    profiles,rows={},{}
    for name,target,source in (("mtx44","sdk/mtx44.o","platform/sdk/gen/mtx44.c"),
                               ("mtx_sh4","platform/mtx_sh4.o","platform/mtx_sh4.S")):
        destination=output/name;destination.mkdir()
        obj=destination/'obj'/target
        command=["make","--no-print-directory","-n",str(obj),
            *[word.replace(str(output),str(destination)) for word in assignments],
            "KOS_CFLAGS="+shlex.join(target_flags(kos)),"KOS_BASE="+str(kos),
            "KOS_LDFLAGS=-T"+str(kos/'utils/ldscripts/shlelf.xc'),
            "SH4ZAM_DIR="+str(sdk),"--assume-old="+str(destination/'obj/modules.mk')]
        result=subprocess.run(command,cwd=DC/'game',text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (destination/'make-dry-run.log').write_text(result.stdout)
        assert result.returncode==0,result.stdout
        commands=[shlex.split(line) for line in result.stdout.replace('\\\n',' ').splitlines() if line.startswith('kos-cc ')]
        assert len(commands)==1,commands
        compile_command=commands[0]
        assert compile_command[-4:]==['-c',source,'-o',str(obj)]
        flags=[word for word in compile_command[1:-4] if word not in ('-MMD','-MP')]
        for i,word in enumerate(flags):
            if word.startswith('-I') and not Path(word[2:]).is_absolute():
                flags[i]='-I'+str((DC/'game'/word[2:]).resolve())
            elif i and flags[i-1] in ('-include','-isystem') and not Path(word).is_absolute():
                flags[i]=str((DC/'game'/word).resolve())
        profiles[name]=[str(compiler),*flags]
        rows[name]=dict(command=command,compile_command=compile_command,flags=flags)
    receipt=dict(profiles=rows,recipe_inputs=metadata)
    (output/'math-profile.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return profiles,receipt


def derive(output, compiler, kos, sdk, *, variants=None, lean=None, units=None):
    output.mkdir(parents=True, exist_ok=False)
    assignments, metadata = recipe_inputs(output)
    _, overlay_receipt = helpers.pvr_overlay(output, kos)
    profiles, rows = {}, {}
    for variant in variants or PROFILES:
        profiles[variant], rows[variant] = {}, {}
        changes = list(PROFILES[variant])
        if lean is not None:
            changes.append(f"UI_DRAW_LEAN={lean}")
        for name in units or PRIMARY_UNITS:
            target, source = SPECIFICATIONS[name]
            destination = output / variant / name
            destination.mkdir(parents=True)
            command = ["make", "--no-print-directory", "-n", str(destination / "obj" / target),
                *[word.replace(str(output), str(destination)) for word in assignments], *changes,
                "KOS_CFLAGS=" + shlex.join(target_flags(kos)), "KOS_BASE=" + str(kos),
                "KOS_LDFLAGS=-T" + str(kos / "utils/ldscripts/shlelf.xc"),
                "SH4ZAM_DIR=" + str(sdk), "--assume-old=" + str(destination / "obj/modules.mk")]
            profiles[variant][name], row = helpers.expand(destination, compiler, sdk, output / "kos-overlay",
                dict(command=command), name, target, source)
            row.update(variant_overrides=changes, seed_command=command)
            rows[variant][name] = row
    receipt = dict(scope=__doc__, profiles=rows, recipe_inputs=metadata,
        pvr_header_overlay=overlay_receipt, debug_records=False, modules_manifest_not_built=True,
        kos_library_patch_checks_not_executed=True)
    (output / "ui-profile.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return profiles, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--variant", action="append", choices=list(PROFILES))
    parser.add_argument("--unit", action="append", choices=list(SPECIFICATIONS))
    parser.add_argument("--lean", type=int, choices=(0, 1))
    args = parser.parse_args()
    flags, receipt = derive(args.output.resolve(), args.sh4_cxx.resolve(), args.kos_root.resolve(),
        args.sdk_root.resolve(), variants=args.variant, lean=args.lean, units=args.unit)
    print(json.dumps(dict(status="PASS", profiles=list(flags),
        profile=str(args.output.resolve() / "ui-profile.json"),
        recipe_sha256=receipt["recipe_inputs"]["recipe_sha256"])))


if __name__ == "__main__":
    main()
