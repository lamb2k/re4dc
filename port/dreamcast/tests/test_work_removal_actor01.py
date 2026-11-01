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
TRANS = ROOT / "src/game/trans.cpp"
PROP_FIXTURE = ROOT / "port/dreamcast/tests/work_removal_actor01_prop.cpp.in"
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



def prop_fragment(source):
    start = source.index("static int propGate(cModel* m, Mtx viewMat)")
    end = source.index("#endif\n// PROP_GATE_EARLY01 parent restore:", start)
    return source[start:end]


def weights_fragment(source):
    start = source.index("static int propGateWeights(const Weight* w, u32 n, u32 parts)")
    end = source.index("static int propGate(cModel* m, Mtx viewMat)", start)
    return source[start:end].replace("static int propGateWeights(", "static int propGateWeights_body(", 1)


def remove_prop_spike(source):
    pattern = r"(?ms)^#if defined\(RE4DC_PROP_GATE_EARLY01\).*?\n.*?^#endif\n#line 2711\n"
    restored, n = re.subn(pattern, "", source)
    assert n == 1, "missing or ambiguous production prop spike"
    for marker in ("parent", "outer"):
        pattern = rf"(?ms)^// PROP_GATE_EARLY01 {marker} restore:.*?^#endif\n"
        restored, n = re.subn(pattern, "", restored)
        assert n == 1, f"missing {marker} prop line restoration"
    return restored


def prop_tokens(source):
    baseline = remove_prop_spike(source)
    native = ["__sh__=1", "RE4DC_FRONT_NATIVE=1", "RE4DC_FRONT_LEAN=1",
              "RE4DC_SCENERY_GATE=1", "RE4DC_SKIN_PALETTE_LAZY=1",
              "RE4DC_NATIVE_ACTOR_SKIN_LAZY=1"]
    parents = [("minimal", []),
               ("front-zero", ["__sh__=1", "RE4DC_FRONT_NATIVE=0"]),
               ("front-no-sh", ["RE4DC_FRONT_NATIVE=1"])]
    for scenery, lean in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        parents.append((f"prop-zero-scenery{scenery}-lean{lean}",
                        ["__sh__=1", "RE4DC_FRONT_NATIVE=1", "RE4DC_PROP_GATE=0",
                         f"RE4DC_SCENERY_GATE={scenery}", f"RE4DC_FRONT_LEAN={lean}"]))
    for mode in [1, 2]:
        parents.append((f"native-prop{mode}", native + [f"RE4DC_PROP_GATE={mode}"]))
        parents.append((f"front2-prop{mode}",
                        [x for x in native if x != "RE4DC_FRONT_NATIVE=1"] +
                        ["RE4DC_FRONT_NATIVE=2", f"RE4DC_PROP_GATE={mode}"]))
    profiles = [(f"{label}-{mode}", definitions + extra)
                for label, definitions in parents
                for mode, extra in [("undefined", []),
                                    ("zero", ["RE4DC_PROP_GATE_EARLY01=0"])]]
    # PPC profiles must not claim the SH architecture or enable a palette
    # feature whose existing source guard explicitly disallows PPC.
    profiles += [(f"{label}-PPC-one-inert", [x for x in definitions
                  if not x.startswith(("__sh__=", "RE4DC_SKIN_PALETTE_LAZY=",
                                       "RE4DC_NATIVE_ACTOR_SKIN_LAZY="))] +
                  ["__PPC__=1", "RE4DC_PROP_GATE_EARLY01=1"])
                 for label, definitions in parents]
    for label, definitions in profiles:
        a = preprocess(source, definitions, "trans.cpp")
        b = preprocess(baseline, definitions, "trans.cpp")
        assert a == b, label
        assert preprocess_locations(source, definitions, "trans.cpp") == preprocess_locations(baseline, definitions, "trans.cpp"), label
        print(f"prop full-TU tokens/locations/__LINE__ (include bodies elided): {label} PASS")
    definitions = native + ["RE4DC_PROP_GATE=1", "RE4DC_PROP_GATE_EARLY01=1"]
    assert preprocess(source, definitions, "trans.cpp") != preprocess(baseline, definitions, "trans.cpp")
    print("prop ON preprocessed production body differs: PASS")


def prop_make_profiles(directory):
    harness = directory / "prop-profiles.mk"
    harness.write_text(
        "OBJDIR := obj\ninclude " + str(MAKE) + "\n"
        "obj/src/game/trans.o:\n"
        "\t@echo GAME_CPPFLAGS=$(GAME_CPPFLAGS)\n"
    )
    defaults = {"PROP_GATE_EARLY01": "1", "PROP_GATE": "1", "FRONT_NATIVE": "1",
                "SCENERY_GATE": "1", "FRONT_LEAN": "1", "SKIN_PALETTE_LAZY": "1",
                "NATIVE_ACTOR_SKIN_LAZY": "1"}
    def profile(assignments, ok, flag):
        run = subprocess.run(["make", "-s", "-f", str(harness), "obj/src/game/trans.o",
                              *[f"{k}={v}" for k, v in assignments.items()]],
                             text=True, capture_output=True)
        assert (run.returncode == 0) == ok, (assignments, run.stdout, run.stderr)
        if ok:
            assert ("-DRE4DC_PROP_GATE_EARLY01=1" in run.stdout) == flag
    profile({}, True, False)
    profile({"PROP_GATE_EARLY01": "0"}, True, False)
    profile(defaults, True, True)
    for value in ["2", "-1", "yes", "", "0 1", "1 0"]:
        profile({**defaults, "PROP_GATE_EARLY01": value}, False, False)
    for name in defaults:
        if name == "PROP_GATE_EARLY01":
            continue
        for bad in ["0", "", "1 0", "3"]:
            profile({**defaults, name: bad}, False, False)
    for name in ["PROP_GATE", "FRONT_NATIVE", "SKIN_PALETTE_LAZY"]:
        profile({**defaults, name: "2"}, True, True)
    profile({**defaults, "PROP_GATE": "2", "FRONT_NATIVE": "2", "SKIN_PALETTE_LAZY": "2"}, True, True)
    print("prop make default/0/1/invalid/prerequisite/check profiles: PASS")


def prop_checks(directory):
    source = TRANS.read_text()
    prop_tokens(source)
    prop_make_profiles(directory)
    body = prop_fragment(source)
    cpp = (PROP_FIXTURE.read_text()
           .replace("@ACTUAL_WEIGHTS@", weights_fragment(source))
           .replace("@ACTUAL_CONTROL@", body.replace("static int propGate(", "static int propGate_control(", 1))
           .replace("@ACTUAL_SPIKE@", body.replace("static int propGate(", "static int propGate_spike(", 1)))
    assert "@ACTUAL_" not in cpp
    path = directory / "prop.cpp"
    path.write_text(cpp)
    for mode in [1, 2]:
        executable = directory / f"prop{mode}"
        command([CXX, "-std=c++17", "-O2", "-ffp-contract=off", "-Wall", "-Wextra",
                 f"-DPROP_MODE={mode}", str(path), "-o", str(executable)])
        print(command([str(executable)]), end="")



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
        prop_checks(directory)
    print("work_removal_actor01 host checks: PASS (no target/performance claim)")


if __name__ == "__main__":
    main()
