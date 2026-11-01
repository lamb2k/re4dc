#!/usr/bin/env python3
"""Public host checks for default-OFF actor work-removal spikes.

Compiles actual production fragments, replacing only the surrounding engine
dependencies. Counting Stream is a test proxy for ordinary RAM reads, not a
production type. Full-TU preprocessor checks elide #include bodies because the
Dreamcast SDK is not needed here; they compare OFF tokens and __LINE__ values,
not target code, ELF/image identity, FPSCR, or performance.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
ACTOR = ROOT / "port/dreamcast/game/platform/native_actor_fast.cpp"
MAKE = ROOT / "port/dreamcast/game/work_removal_actor01.mk"
FIXTURE = ROOT / "port/dreamcast/tests/work_removal_actor01_padding.cpp.in"
CXX = os.environ.get("CXX", "g++")


def command(args, **kwargs):
    result = subprocess.run(args, text=True, capture_output=True, **kwargs)
    if result.returncode:
        raise AssertionError(f"command failed: {args}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def padding_fragment(source):
    comment = source.index("// ACTOR_REPLAY_SKIN: a GX list of padding only")
    start = source.rfind("#if defined(RE4DC_ACTOR_REPLAY_SKIN)", 0, comment)
    end = source.index("    if (!part || !qualifies(*part", comment)
    assert start >= 0
    return source[start:end]


def remove_padding_spike(source):
    pattern = (
        r"(?ms)^#if defined\(RE4DC_ACTOR_PADDING_FIRST01\).*?\n"
        r".*?^#else\n#line 6630\n(.*?)^#endif\n#line 6633\n"
    )
    restored, n = re.subn(pattern, lambda m: m.group(1), source)
    assert n == 1, "missing or ambiguous production spike block"
    restored, n = re.subn(r"(?m)^#line 6635\n", "", restored)
    assert n == 1, "missing outer replay line restoration"
    return restored


def preprocess(source, definitions, filename="native_actor_fast.cpp", sentinel=True):
    # Preserve physical line counts and use one filename for both comparison arms.
    source = re.sub(r"(?m)^[ \t]*#include[^\n]*", "", source)
    source = f'#line 1 "{filename}"\n' + source
    if sentinel:
        source += "\nconst unsigned work_removal_line_sentinel = __LINE__;\n"
    return command([CXX, "-E", "-P", "-x", "c++",
                    *[f"-D{x}" for x in definitions], "-"], input=source)


def preprocess_locations(source, definitions, filename="native_actor_fast.cpp"):
    # Compare every active token line's source location, including code after
    # inactive parent blocks. A sentinel alone could miss a later #line reset.
    source = re.sub(r"(?m)^[ \t]*#include[^\n]*", "", source)
    source = f'#line 1 "{filename}"\n' + source
    source += "\nconst unsigned work_removal_line_sentinel = __LINE__;\n"
    output = command([CXX, "-E", "-x", "c++",
                      *[f"-D{x}" for x in definitions], "-"], input=source)
    result = []
    logical_file, logical_line = "", 0
    for line in output.splitlines():
        marker = re.match(r'^#\s+(\d+)\s+"([^"]+)"', line)
        if marker:
            logical_line, logical_file = int(marker.group(1)), marker.group(2)
        else:
            if line.strip():
                result.append((logical_file, logical_line, line))
            logical_line += 1
    return result


def token_identity(source):
    baseline = remove_padding_spike(source)
    common = ["RE4DC_NATIVE_ACTOR_FAST=1", "RE4DC_ACTOR_REPLAY_SKIN=1",
              "RE4DC_ACTOR_TEST=1", "RE4DC_DRAW_FALLBACK_AUDIT=1",
              "RE4DC_K45DIAG31=1"]
    parents = [("minimal", []), ("native-replay", common)]
    for fast, replay in [(0, 0), (1, 0), (0, 1)]:
        parents.append((f"native{fast}-replay{replay}",
                        [f"RE4DC_NATIVE_ACTOR_FAST={fast}",
                         f"RE4DC_ACTOR_REPLAY_SKIN={replay}"]))
    profiles = [(f"{label}-{mode}", definitions + extra)
                for label, definitions in parents
                for mode, extra in [("undefined", []),
                                    ("zero", ["RE4DC_ACTOR_PADDING_FIRST01=0"])]]
    profiles += [(f"{label}-PPC-one-inert", definitions +
                  ["__PPC__=1", "RE4DC_ACTOR_PADDING_FIRST01=1"])
                 for label, definitions in parents]
    for label, definitions in profiles:
        assert preprocess(source, definitions) == preprocess(baseline, definitions), label
        assert preprocess_locations(source, definitions) == preprocess_locations(baseline, definitions), label
        print(f"padding full-TU tokens/locations/__LINE__ (include bodies elided): {label} PASS")
    assert preprocess(source, common + ["RE4DC_ACTOR_PADDING_FIRST01=1"]) != preprocess(baseline, common)
    print("padding ON preprocessed production body differs: PASS")


def make_profiles(directory):
    harness = directory / "profiles.mk"
    harness.write_text(
        "OBJDIR := obj\ninclude " + str(MAKE) + "\n"
        "obj/platform/native_actor_fast.o:\n"
        "\t@echo PLATFORM_CPPFLAGS=$(PLATFORM_CPPFLAGS)\n"
    )
    target = "obj/platform/native_actor_fast.o"
    def profile(assignments, ok, flag):
        run = subprocess.run(["make", "-s", "-f", str(harness), target, *assignments],
                             text=True, capture_output=True)
        assert (run.returncode == 0) == ok, (assignments, run.stdout, run.stderr)
        if ok:
            assert ("-DRE4DC_ACTOR_PADDING_FIRST01=1" in run.stdout) == flag
        return run
    profile([], True, False)
    profile(["ACTOR_PADDING_FIRST01=0"], True, False)
    profile(["ACTOR_PADDING_FIRST01=1", "NATIVE_ACTOR_FAST=1", "ACTOR_REPLAY_SKIN=1"], True, True)
    for value in ["2", "-1", "yes", "", "0 1", "1 0"]:
        profile([f"ACTOR_PADDING_FIRST01={value}"], False, False)
    for fast, replay in [("0","1"), ("1","0"), ("0","0"), ("2","1"), ("11", "")]:
        profile(["ACTOR_PADDING_FIRST01=1", f"NATIVE_ACTOR_FAST={fast}",
                 f"ACTOR_REPLAY_SKIN={replay}"], False, False)
    print("padding make default/0/1/invalid/prerequisite profiles: PASS")


def main():
    source = ACTOR.read_text()
    token_identity(source)
    with tempfile.TemporaryDirectory(prefix="work-removal-actor01-") as tmp:
        directory = Path(tmp)
        make_profiles(directory)
        cpp = FIXTURE.read_text().replace("@ACTUAL_PADDING@", padding_fragment(source))
        assert "@ACTUAL_PADDING@" not in cpp
        path = directory / "padding.cpp"
        executable = directory / "padding"
        path.write_text(cpp)
        command([CXX, "-std=c++17", "-O2", "-Wall", "-Wextra", "-pedantic",
                 str(path), "-o", str(executable)])
        print(command([str(executable)]), end="")
    print("work_removal_actor01 host checks: PASS (no target/performance claim)")


if __name__ == "__main__":
    main()
