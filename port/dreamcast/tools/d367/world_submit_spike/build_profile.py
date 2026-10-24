#!/usr/bin/env python3
"""Derive each world-submit TU's real public Test22 compiler command.

The established setup-spike helper reconstructs the shared generated headers.
This extension also expands native_ui's own Make recipe rather than assuming
its per-object options are the same as native_static's.
"""
import hashlib
import importlib.util
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "world_setup_spike"))
import release_profile

# Load the established helpers by an unambiguous name: this directory also
# contains a CLI named build_target.py.
_spec=importlib.util.spec_from_file_location("world_setup_build_helpers",HERE.parent/"world_setup_spike/build_target.py")
_helpers=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_helpers)
Build,sections,sha,stack_usage=(_helpers.Build,_helpers.sections,_helpers.sha,_helpers.stack_usage)

DC = HERE.parents[2]
ROOT = DC.parents[1]


def pvr_overlay(output, kos):
    """Apply the pinned repository's header hunks without modifying the SDK."""
    source = kos / "kernel/arch/dreamcast/include/dc/pvr.h"
    target = output / "kos-overlay/dc/pvr.h"
    target.parent.mkdir(parents=True)
    target.write_bytes(source.read_bytes())
    (target.parent / "pvr").symlink_to(source.parent / "pvr", target_is_directory=True)
    patches = []
    for name in ("manual-flip", "async-present", "vbuf-switch"):
        patch = DC / ("patches/kos-804b319-" + name + ".patch")
        text = patch.read_text()
        start = text.index("--- a/kernel/arch/dreamcast/include/dc/pvr.h")
        remaining = text[start:]
        end = re.search(r"\n(?:diff --git |--- (?:a/|/dev/null))", remaining[1:])
        body = remaining if end is None else remaining[:end.start() + 1]
        command = ["patch", "--batch", "--forward", str(target)]
        result = subprocess.run(command, input=body, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert result.returncode == 0, result.stdout
        patches.append(dict(path=str(patch.relative_to(ROOT)),
                            sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),
                            applied_header_hunk_sha256=hashlib.sha256(body.encode()).hexdigest(),
                            output=result.stdout))
    return target.parent.parent, dict(source=str(source),
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        patched_sha256=hashlib.sha256(target.read_bytes()).hexdigest(), patches=patches,
        scope="Only declarations patched; KOS source/library unchanged and link guards not run")


def expand(output, compiler, sdk, overlay, static_receipt, name, target_relative, source_relative):
    old_target = output / "obj/platform/native_static.o"
    target = output / "obj" / target_relative
    command = [str(target) if word == str(old_target) else word
               for word in static_receipt["command"]]
    result = subprocess.run(command, cwd=DC / "game", text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (output / ("make-" + name + "-dry-run.log")).write_text(result.stdout)
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
        previous = headers.get(destination, "") if words[at] == ">>" else ""
        headers[destination] = previous + fmt % tuple(words[2:at])
    for destination, text in headers.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            assert destination.read_text() == text, destination
        else:
            destination.write_text(text)
    commands = [shlex.split(line) for line in logical if line.startswith("kos-c++ ")]
    assert len(commands) == 1
    compile_command = commands[0]
    assert compile_command[-4:] == ["-c", source_relative, "-o", str(target)]
    flags = [word for word in compile_command[1:-4] if word not in ("-MMD", "-MP")]
    for i, word in enumerate(flags):
        if word.startswith("-I") and not Path(word[2:]).is_absolute():
            flags[i] = "-I" + str((DC / "game" / word[2:]).resolve())
        elif i and flags[i - 1] in ("-include", "-isystem") and not Path(word).is_absolute():
            flags[i] = str((DC / "game" / word).resolve())
    flags += ["-I" + str(sdk / "include"), "-I" + str(overlay)]
    receipt = dict(static_receipt, command=command, compile_command=compile_command,
                   flags=flags,
                   generated_headers={str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                                      for path in headers})
    return [str(compiler), *flags], receipt


def derive(output, compiler, kos, sdk, *, cost_dependencies=False):
    static_flags, static_receipt = release_profile.derive(output, compiler, kos, sdk)
    overlay, patch_receipt = pvr_overlay(output, kos)
    static_flags += ["-I" + str(overlay)]
    static_receipt["flags"] = static_flags[1:]
    profiles = dict(native_static=static_flags)
    receipt = dict(native_static=static_receipt, pvr_header_overlay=patch_receipt)
    specifications = [("native_ui", "platform/native_ui.o", "platform/native_ui.cpp")]
    if cost_dependencies:
        specifications += [("texture_package", "native-reuse/texture_package.o", "../room/texture_package.cpp"),
                           ("pvr_geometry", "native-reuse/pvr_geometry.o", "../room/pvr_geometry.cpp")]
    for name, target, source in specifications:
        profiles[name], receipt[name] = expand(output, compiler, sdk, overlay, static_receipt, name, target, source)
    (output / "submit-profile.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return profiles, receipt
