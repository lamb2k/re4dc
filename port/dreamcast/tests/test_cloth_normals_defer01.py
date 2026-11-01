#!/usr/bin/env python3
"""Host source-boundary checks for the default-OFF cloth normal-work spike.

Executes production Cloth lifecycle/physics/normal bodies, Esp4e::move in both
arms, and the complete clothTrans consumer with host engine/GX stubs. Native
outcomes use the production result type; native rendering itself is simulated.
Include-elided preprocessor checks prove source token/diagnostic-line identity,
not target ELF/image identity, SH-4 numeric/FPSCR behavior, or a performance gain.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
CXX = os.environ.get("CXX", "g++")
CLOTH = ROOT / "src/game/cloth.cpp"
ESP = ROOT / "src/game/esp4e.cpp"
MAKE = ROOT / "port/dreamcast/game/work_removal_cloth01.mk"
FIXTURE = ROOT / "port/dreamcast/tests/cloth_normals_defer01.cpp.in"
INCLUDES = ROOT / "port/dreamcast/game/platform/include"
GUARD = "#if defined(RE4DC_CLOTH_NORMALS_DEFER01) && RE4DC_CLOTH_NORMALS_DEFER01 && !defined(__PPC__)"


def command(args, **kwargs):
    result = subprocess.run(args, text=True, capture_output=True, **kwargs)
    if result.returncode:
        raise AssertionError(f"command failed: {args}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def function(source, signature):
    """Keep the production function, including its conditional bodies."""
    start = source.index(signature)
    if signature == "void clothTrans(":
        # The final function has alternative preprocessor arms that each open
        # the same if statement. Keep both arms rather than counting raw braces.
        assert source.rstrip().endswith("}")
        return source[start:]
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end] + "\n"


def restore_off(source, expected):
    """Remove only this spike's guarded additions and restoring #line markers."""
    lines = source.splitlines(keepends=True)
    result = []
    i = count = 0
    while i < len(lines):
        if lines[i].rstrip() != GUARD:
            result.append(lines[i])
            i += 1
            continue
        count += 1
        depth = 1
        alternate = None
        i += 1
        while depth:
            line = lines[i]
            if re.match(r"\s*#if(?:def|ndef)?\b", line):
                depth += 1
            elif re.match(r"\s*#endif\b", line):
                depth -= 1
            elif depth == 1 and re.match(r"\s*#else\b", line):
                alternate = []
                i += 1
                continue
            if alternate is not None and depth:
                alternate.append(line)
            i += 1
        if alternate:
            assert alternate[0].startswith("#line ")
            result.extend(alternate[1:])
        assert lines[i].startswith("#line "), "missing OFF logical-line restoration"
        i += 1
    assert count == expected, count
    return "".join(result)


def preprocess(source, definitions, filename, locations=False):
    source = re.sub(r"(?m)^[ \t]*#include[^\n]*", "", source)
    preamble = (
        '#define MEM_ALLOC(...) allocation_marker(__FILE__, __LINE__, __VA_ARGS__)\n'
        '#define VECNormalize(...) normalization_marker(__FILE__, __LINE__, __VA_ARGS__)\n'
    )
    source = preamble + f'#line 1 "{filename}"\n' + source
    source += "\nconst unsigned cloth_normals_line_sentinel = __LINE__;\n"
    output = command([CXX, "-E", *([] if locations else ["-P"]), "-x", "c++",
                      *[f"-D{x}" for x in definitions], "-"], input=source)
    if not locations:
        return output
    active = []
    logical_file, logical_line = "", 0
    for line in output.splitlines():
        marker = re.match(r'^# (\d+) "([^"]+)"', line)
        if marker:
            logical_line, logical_file = int(marker[1]), marker[2]
            continue
        if line.strip():
            active.append((logical_file, logical_line, line.strip()))
        logical_line += 1
    return active


def token_identity(cloth, esp, baseline_root):
    sources = [("src/game/cloth.cpp", cloth, restore_off(cloth, 6)),
               ("src/game/esp4e.cpp", esp, restore_off(esp, 2))]
    native = ["RE4DC_CLOTH_NATIVE=1", "RE4DC_NATIVE_DRAW_OUTCOMES=1"]
    material = native + ["RE4DC_CLOTH_SHEET11=1", "RE4DC_CLOTH_PUBLICATION11=1",
                         "RE4DC_CLOTH_MATERIAL11=1", "RE4DC_CLOTH_LIGHT_ABI_FIX=1",
                         "RE4DC_FALLBACK_AUDIT29=1", "RE4DC_FALLBACK_AUDIT35=1"]
    profiles = [("default-undefined", []),
                ("default-zero", ["RE4DC_CLOTH_NORMALS_DEFER01=0"]),
                ("PPC-one-inert", ["__PPC__=1", "RE4DC_CLOTH_NORMALS_DEFER01=1"]),
                ("material-audit-zero", material + ["RE4DC_CLOTH_NORMALS_DEFER01=0"])]
    for native_value in [0, 1]:
        for outcomes in [None, 0, 1]:
            parent = [f"RE4DC_CLOTH_NATIVE={native_value}"]
            if outcomes is not None:
                parent.append(f"RE4DC_NATIVE_DRAW_OUTCOMES={outcomes}")
            for label, extra in [("undefined", []), ("zero", ["RE4DC_CLOTH_NORMALS_DEFER01=0"]),
                                 ("PPC-one", ["__PPC__=1", "RE4DC_CLOTH_NORMALS_DEFER01=1"])]:
                profiles.append((f"native{native_value}/outcomes{outcomes}/{label}", parent + extra))
    for spring in [1, 2]:
        profiles.append((f"spring{spring}-zero", native + [f"RE4DC_CLOTH_SPRING={spring}", "RE4DC_CLOTH_NORMALS_DEFER01=0"]))
    for rel, source, restored in sources:
        if baseline_root:
            assert restored == (baseline_root / rel).read_text(), f"frozen baseline mismatch: {rel}"
        for label, definitions in profiles:
            assert preprocess(source, definitions, rel) == preprocess(restored, definitions, rel), (rel, label)
            assert preprocess(source, definitions, rel, True) == preprocess(restored, definitions, rel, True), (rel, label, "active-token logical locations")
        assert preprocess(source, native + ["RE4DC_CLOTH_NORMALS_DEFER01=1"], rel) != preprocess(restored, native, rel)
        print(f"{rel}: full-TU OFF/PPC tokens, diagnostic expansions and all active-line locations, {len(profiles)} profiles PASS")
    assert function(cloth, "void Cloth::move()") == function(sources[0][2], "void Cloth::move()")
    assert function(cloth, "void Cloth::calcNormal()") == function(sources[0][2], "void Cloth::calcNormal()")
    print("unchanged production Cloth::move/calcNormal and original Esp4e update site: PASS")


def make_profiles(directory):
    harness = directory / "profiles.mk"
    harness.write_text("OBJDIR := obj\ninclude " + str(MAKE) + "\n"
                       "obj/src/game/cloth.o obj/src/game/esp4e.o obj/src/game/unrelated.o:\n"
                       "\t@echo $@ GAME_CPPFLAGS=$(GAME_CPPFLAGS)\n")
    targets = ["obj/src/game/cloth.o", "obj/src/game/esp4e.o", "obj/src/game/unrelated.o"]
    count = 0
    def profile(assignments, ok, flag):
        nonlocal count
        count += 1
        result = subprocess.run(["make", "-s", "-f", str(harness), *targets, *assignments],
                                text=True, capture_output=True)
        assert (result.returncode == 0) == ok, (assignments, result.stdout, result.stderr)
        if ok:
            lines = result.stdout.splitlines()
            assert len(lines) == 3
            for i, line in enumerate(lines):
                assert ("-DRE4DC_CLOTH_NORMALS_DEFER01=1" in line) == (flag and i < 2)
    profile([], True, False)
    profile(["CLOTH_NORMALS_DEFER01=0"], True, False)
    profile(["CLOTH_NORMALS_DEFER01=1", "CLOTH_NATIVE=1", "NATIVE_DRAW_OUTCOMES=1"], True, True)
    for value in ["2", "-1", "yes", "", "0 1", "1 0"]:
        profile([f"CLOTH_NORMALS_DEFER01={value}"], False, False)
    for name in ["CLOTH_NATIVE", "NATIVE_DRAW_OUTCOMES"]:
        for value in [None, "0", "2", "", "1 0"]:
            settings = {"CLOTH_NORMALS_DEFER01":"1", "CLOTH_NATIVE":"1", "NATIVE_DRAW_OUTCOMES":"1"}
            if value is None:
                del settings[name]
            else:
                settings[name] = value
            profile([f"{k}={v}" for k, v in settings.items()], False, False)
    print(f"make default/0/1/invalid/prerequisite/object-isolation profiles: {count} PASS")


def fixture_source(cloth, esp):
    state_start = cloth.index(GUARD, cloth.index("Cloth ClothWk[8];"))
    state_end = cloth.index("#line 26\n", state_start)
    physics_start = cloth.index("// One simulation step of the speeds")
    physics_end = cloth.index("// A free cloth work", physics_start)
    physics = cloth[physics_start:physics_end]
    physics = physics.replace("void Cloth::calcSpeed(f32 damping)\n{", "void Cloth::calcSpeed(f32 damping)\n{\n    event('S');")
    methods = []
    for signature in ["void ClothInit()", "void ClothRoomInit()", "void Cloth::Set(Vec", "void Cloth::SetPosAng(",
                      "void Cloth::Destroy()", "int PullCloth(", "void Cloth::move()", "void Cloth::calcNormal()",
                      "void Cloth::disturbance("]:
        body = function(cloth, signature)
        if signature == "void Cloth::move()":
            body = body.replace("{", "{\n    event('M');", 1)
        elif signature == "void Cloth::calcNormal()":
            body = body.replace("{", "{\n    ++normal_calls; event('N');", 1)
        elif signature == "void Cloth::disturbance(":
            body = body.replace("{", "{\n    event('D');", 1)
        methods.append(body)
    esp_type = esp[esp.index("struct Esp4eWork {"):esp.index('extern "C" {')]
    move = function(esp, "void cEsp4e::move()")
    math_header = (ROOT / "include/math_sub.h").read_text()
    normal_macro = math_header[math_header.index("#define VECNormalize("):math_header.rindex("\n#endif")]
    replacements = {
        "@ACTUAL_CLOTH_TYPE@": re.sub(r"(?m)^#include[^\n]*", "", (ROOT / "include/cloth.h").read_text()),
        "@ACTUAL_NORMAL_MACRO@": normal_macro,
        "@ACTUAL_NORMAL_STATE@": cloth[state_start:state_end],
        "@ACTUAL_PHYSICS@": physics,
        "@ACTUAL_METHODS@": "\n".join(methods),
        "@ACTUAL_ESP_TYPE@": esp_type,
        "@ACTUAL_ESP_MOVE@": move,
        "@ACTUAL_ESP_CONTROL@": move.replace("void cEsp4e::move()", "void cEsp4eControl::move()", 1),
        "@ACTUAL_ESP_DESTRUCT@": function(esp, "void cEsp4e::Destruct()"),
        "@ACTUAL_VISIBLE@": function(cloth, "static int re4dc_cloth_visible("),
        "@ACTUAL_TRANS@": function(cloth, "void clothTrans("),
    }
    result = FIXTURE.read_text()
    for key, value in replacements.items():
        assert result.count(key) == 1, key
        result = result.replace(key, value)
    assert "@ACTUAL_" not in result
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-root", type=Path, help="also verify exact restoration against the independent frozen input")
    parser.add_argument("--keep-output", type=Path, help="save generated production-fragment fixture and executables")
    args = parser.parse_args()
    cloth, esp = CLOTH.read_text(), ESP.read_text()
    token_identity(cloth, esp, args.baseline_root)
    with tempfile.TemporaryDirectory(prefix="cloth-normals-defer01-") as tmp:
        directory = args.keep_output or Path(tmp)
        directory.mkdir(parents=True, exist_ok=True)
        make_profiles(directory)
        source = directory / "cloth.cpp"
        source.write_text(fixture_source(cloth, esp))
        for spring in [0, 1, 2]:
            executable = directory / f"cloth-spring{spring}"
            command([CXX, "-std=c++17", "-O2", "-ffp-contract=off", "-Wall", "-Wextra",
                     "-Wno-unused-variable", "-I", str(INCLUDES), f"-DRE4DC_CLOTH_SPRING={spring}",
                     *shlex.split(os.environ.get("CLOTH_NORMALS_TEST_CXXFLAGS", "")), str(source), "-o", str(executable)])
            print(command([str(executable)]), end="")
    print("cloth_normals_defer01 host checks: PASS (target identity/numeric/performance unmeasured)")


if __name__ == "__main__":
    main()
