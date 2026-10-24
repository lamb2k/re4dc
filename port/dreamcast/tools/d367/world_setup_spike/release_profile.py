#!/usr/bin/env python3
"""Derive world compile flags from the public release recipe without a build.

Make expands the actual native_static.o recipe. Generated configuration headers
are reconstructed from Make's literal printf commands, without executing shell
recipes or claiming the unbuilt KOS library passed its link-time patch guards.
"""
import hashlib
import json
import shlex
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]


def derive(output, compiler, kos, sdk):
    output.mkdir()
    assets = DC / "game/public-assets"
    script = DC / "tools/d367/build-r21.sh"
    release = DC / "tools/d367/test22/release-knobs.txt"
    public = DC / "build-public.sh"
    body = script.read_text().split("R21=(\n", 1)[1].split("\n)", 1)[0]
    for before, after in {"$ASSETS": assets, "$ROOT": ROOT,
                          "$OBJDIR": output / "obj", "$OUT": output}.items():
        body = body.replace(before, str(after))
    base = shlex.split(body, comments=True)
    assert not any("$" in word for word in base)
    knobs = [line.replace("@ASSETS@", str(assets)) for line in release.read_text().splitlines()
             if line and not line.startswith("#")]
    removed = ("PS2_LEON_DIR=", "PS2_GANADO_DIR=", "GANADO_LOD_PACK=", "LEON_HEADLESS_DIR=",
               "PS2_ENEMY_CH22_DIR=", "PS2_ENEMY_CH23_DIR=", "ACTOR_GANADO_PS2_STUMP_DIR=")
    knobs = [word for word in knobs if not word.startswith(removed)]
    private_off = ("PS2_LEON=0 LEON_HAND_PACK=0 PS2_GANADO=0 PS2_GANADO_LIT=0 GANADO_LOD=0 "
                   "GANADO_EVENT_KEEP_LOD=0 ACTOR_PROBE_LIGHT=1 GANADO_LIT=0 NATIVE_MODEL_REGISTRY_DYING=0 "
                   "LEON_HEADLESS=0 PS2_CH2_ENEMY=0 ACTOR_GANADO_PS2_STUMP=0").split()
    public_text = public.read_text()
    assert all(word in public_text for word in private_off)
    # Match kos-env.sh + pinned KOS environ_dreamcast/environ_base target ABI.
    # Debug records are omitted so OFF object identity is not contaminated by
    # source line-number changes; all executable optimization flags remain.
    target_flags = ["-O2", "-fno-PIC", "-fno-PIE", "-fomit-frame-pointer", "-m4-single", "-ml",
                    "-mfsrra", "-mfsca", "-ffunction-sections", "-fdata-sections",
                    "-matomic-model=soft-gusa", "-ftls-model=local-exec", "-D__DREAMCAST__"]
    for path in (kos / "include", kos / "kernel/arch/dreamcast/include", kos / "addons/include"):
        target_flags += ["-isystem", str(path)]
    target_flags += ["-D_arch_dreamcast=1", "-D_arch_sub_pristine=1", "-Wall"]
    target = output / "obj/platform/native_static.o"
    command = ["make", "--no-print-directory", "-n", str(target), *base, *knobs, *private_off,
               "KOS_CFLAGS=" + shlex.join(target_flags), "KOS_BASE=" + str(kos),
               "KOS_LDFLAGS=-T" + str(kos / "utils/ldscripts/shlelf.xc"),
               "SH4ZAM_DIR=" + str(sdk), "--assume-old=" + str(output / "obj/modules.mk")]
    result = subprocess.run(command, cwd=DC / "game", text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (output / "make-dry-run.log").write_text(result.stdout)
    assert result.returncode == 0, result.stdout
    logical = result.stdout.replace("\\\n", " ").splitlines()
    headers = {}
    for line in logical:
        if not line.startswith("printf "):
            continue
        words = shlex.split(line)
        at = next(i for i, word in enumerate(words) if word in (">", ">>"))
        destination = Path(words[at + 1])
        if not str(destination).endswith(".h.tmp"):
            continue
        assert destination.is_relative_to(output / "obj")
        destination = destination.with_suffix("")
        fmt = bytes(words[1], "utf8").decode("unicode_escape")
        text = fmt % tuple(words[2:at])
        previous = headers.get(destination, "") if words[at] == ">>" else ""
        headers[destination] = previous + text
    for destination, text in headers.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text)
    commands = [shlex.split(line) for line in logical if line.startswith("kos-c++ ")]
    assert len(commands) == 1
    compile_command = commands[0]
    assert compile_command[-4:] == ["-c", "platform/native_static.cpp", "-o", str(target)]
    flags = compile_command[1:-4]
    flags = [word for word in flags if word not in ("-MMD", "-MP")]
    for i, word in enumerate(flags):
        if word.startswith("-I") and not Path(word[2:]).is_absolute():
            flags[i] = "-I" + str((DC / "game" / word[2:]).resolve())
        elif i and flags[i - 1] in ("-include", "-isystem") and not Path(word).is_absolute():
            flags[i] = str((DC / "game" / word).resolve())
    # Headers from the patched pinned SDK are necessary for optional CPU2/cone
    # coexistence arms; an unused search directory changes no main-profile code.
    flags += ["-I" + str(sdk / "include")]
    sources = [script, release, public, DC / "kos-env.sh", DC / "game/Makefile",
               *sorted((DC / "game").glob("*.mk"))]
    receipt = dict(scope="Make-expanded Test22 public world configuration; complete TU compile only, no linked release image",
                   command=command, compile_command=compile_command,
                   flags=flags, missing_asset_overrides=private_off,
                   removed_asset_path_knobs=list(removed), debug_records=False,
                   modules_manifest_not_built=True, kos_library_patch_checks_not_executed=True,
                   generated_headers={str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in headers},
                   source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources})
    (output / "recipe.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return [str(compiler), *flags], receipt
