#!/usr/bin/env python3
"""Make-derived Build18 public profiles, independent of Build17 branch files.

The restricted current-recipe reader is retained from Build17; shared public
Make/header expansion helpers are reused from integration. No shell recipe
text is evaluated, no game assets are needed, and debug records are omitted
consistently from every target arm.
"""
from pathlib import Path
import importlib.util
import json
import re
import shlex
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
spec = importlib.util.spec_from_file_location("fx18_profile_helpers", DC / "tools/d367/ui_draw_lean/build_profile.py")
profile = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = profile
spec.loader.exec_module(profile)
Build, sha, sections, stack_usage = profile.Build, profile.sha, profile.sections, profile.stack_usage
UNITS = {"native_ui": ("platform/native_ui.o", "platform/native_ui.cpp"),
         "ui_bridge": ("ui_bridge.o", "ui_bridge.cpp")}
PROFILES = {"recipe24": [], "diagnostic": ["FRAME_QUEUE_DIAG=1", "FX_QUEUE_LOG=1"],
            "slab-alias": ["FX_ROOM_SPILL_KB=0"]}


def recipe_inputs(destination, tree):
    """Read the current public release plus ordered literal CH2 appends.

    Only assignment words and the documented leading $CH2 append are accepted;
    no shell code from recipe.conf or build-public.sh is executed.
    """
    dc = tree / "port/dreamcast"
    assets = dc / "game/public-assets"
    script, public, recipe = (dc / "tools/d367/build-r21.sh", dc / "build-public.sh",
                               dc / "tools/d367/rr/recipe.conf")
    public_text = public.read_text()
    selected = re.findall(r'^RELEASE_KNOBS=\$\{RELEASE_KNOBS:-\$PORT/([^}]+)\}$', public_text, re.MULTILINE)
    assert len(selected) == 1, "public release selection changed"
    release = dc / selected[0]
    body = script.read_text().split("R21=(\n", 1)[1].split("\n)", 1)[0]
    for before, after in {"$ASSETS": assets, "$ROOT": tree,
                          "$OBJDIR": destination / "obj", "$OUT": destination}.items():
        body = body.replace(before, str(after))
    base = shlex.split(body, comments=True)
    assert not any("$" in word or "`" in word for word in base)
    knobs = [line.replace("@ASSETS@", str(assets)) for line in release.read_text().splitlines()
             if line and not line.startswith("#")]
    ch2 = None
    assignments = []
    for line in recipe.read_text().splitlines():
        if not line.startswith("CH2="):
            continue
        match = re.fullmatch(r'CH2="([^"\n]*)"\s*(?:#.*)?', line)
        assert match, ("nonliteral CH2 assignment", line)
        value = match[1]
        if value.startswith("$CH2 "):
            assert ch2 is not None, "append before CH2 definition"
            words = shlex.split(value[len("$CH2 "):])
            ch2.extend(words)
        else:
            assert ch2 is None, "unexpected CH2 reset"
            words = shlex.split(value)
            ch2 = list(words)
        assert all(re.fullmatch(r"[A-Z0-9_]+=[^\s$`]+", word) for word in words), words
        assignments.append(line)
    assert ch2 is not None
    public_off = []
    for line in public_text.splitlines():
        match = re.fullmatch(r'\s*PRIVATE_OFF="([^"\n]*)"', line)
        if not match:
            continue
        value = match[1].removeprefix("${PRIVATE_OFF:+$PRIVATE_OFF }")
        words = shlex.split(value)
        assert all(re.fullmatch(r"[A-Z0-9_]+=[^\s$`]+", word) for word in words), words
        public_off.extend(word for word in words if word not in public_off)
    assert public_off, "missing public fallback assignments"
    private = profile.PRIVATE_PATHS
    removed = [word for word in [*knobs, *ch2] if word.startswith(private)]
    knobs = [word for word in knobs if not word.startswith(private)]
    ch2_public = [word for word in ch2 if not word.startswith(private)]
    inputs = [script, release, recipe, public, dc / "kos-env.sh", dc / "game/Makefile",
              *sorted((dc / "game").glob("*.mk"))]
    receipt = dict(release=str(release.relative_to(tree)), ordered_ch2_assignments=assignments,
                   public_ch2=ch2_public, removed_asset_path_assignments=removed,
                   missing_asset_overrides=public_off,
                   source_sha256={str(path.relative_to(tree)): profile.sha(path) for path in inputs})
    return [*base, *knobs, *ch2_public, *public_off], receipt



def make_command(output, tree, kos, sdk, options, target):
    assignments, recipe = recipe_inputs(output, tree)
    return ["make", "--no-print-directory", "-n", str(target), *assignments, *options,
        "KOS_CFLAGS=" + shlex.join(profile.target_flags(kos)), "KOS_BASE=" + str(kos),
        "KOS_LDFLAGS=-T" + str(kos / "utils/ldscripts/shlelf.xc"), "SH4ZAM_DIR=" + str(sdk),
        "--assume-old=" + str(output / "obj/modules.mk")], recipe


def derive(out, cxx, kos, sdk, options, *, tree=ROOT, units=tuple(UNITS)):
    out.mkdir(parents=True, exist_ok=False)
    flags, rows, sources = {}, {}, {}
    for unit in units:
        target, source = UNITS[unit]
        destination = out / unit
        destination.mkdir()
        command, recipe = make_command(destination, tree, kos, sdk, options,
                                       destination / "obj" / target)
        with profile.source_tree(tree):
            # KOS already has the pinned repository PVR declarations. The
            # existing expander appends SDK/include and this include overlay.
            flags[unit], row = profile.helpers.expand(destination, cxx, sdk,
                kos / "kernel/arch/dreamcast/include", dict(command=command), unit, target, source)
        rows[unit] = dict(row, recipe_inputs=recipe, overrides=options)
        sources[unit] = tree / "port/dreamcast/game" / source
    receipt = dict(profiles=rows, debug_records=False, kos_library_not_built=True,
                   modules_manifest_not_built=True, private_assets_not_used=True)
    (out / "profile.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return flags, receipt, sources


def probe(out, tree, kos, sdk, options):
    out.mkdir(parents=True, exist_ok=False)
    names = ("FX_R200_ENTRY_CAP", "FX_ROOM_SPILL_KB", "FRAME_QUEUE_DIAG", "FX_QUEUE_LOG",
             "PLATFORM_OBJS", "GAME_LDFLAGS")
    query = out / "query.mk"
    query.write_text(".PHONY: fx18-state\nfx18-state:\n\t@:\n" + "\n".join(
        f"$(info FX18_STATE {name}=$({name}))" for name in names) + "\n")
    command, _ = make_command(out, tree, kos, sdk, options, "fx18-state")
    command[3:3] = ["-f", "Makefile", "-f", str(query)]
    run = subprocess.run(command, cwd=tree / "port/dreamcast/game", capture_output=True, text=True)
    output = run.stdout + run.stderr
    (out / "make.log").write_text(output)
    state = dict(line[len("FX18_STATE "):].split("=", 1) for line in output.splitlines()
                 if line.startswith("FX18_STATE "))
    return dict(command=command, returncode=run.returncode, state=state,
                error=output[-2000:] if run.returncode else None)
