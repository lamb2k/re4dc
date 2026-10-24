#!/usr/bin/env python3
"""Verify unchanged inside selection and compare the screen memo off/on.

Selection executes source-extracted numeric helpers and the unchanged package
validator over deterministic public fixtures. Entry counters confirm that the
existing fully-inside path calls neither meshlet box nor strip-group tests.
Screen tests prove bitwise memo keys and a hardware reload on every call.
No new selection-culling saving, target cost, or full-game claim is made.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
DC = ROOT / "port/dreamcast"
STATIC = DC / "game/platform/native_static.cpp"
SELECTOR = STATIC.parent / "include/scenery_chunk_select.inc"
BASELINE = "451bed6faa2c37f7f9aa05d6fb1116ec64219ebc"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


extractor = module("world_submit_extract", HERE.parent / "world_submit_spike/check_runtime.py")
cases_module = module("world_selection_cases", HERE.parent / "world_setup_spike/selection_cases.py")


def generate(output):
    # room_package.hpp declares a separate file-backed Package, which is never
    # constructed here. MeshPackage::adopt is an in-memory production validator.
    headers = output / "headers/kos"
    headers.mkdir(parents=True)
    (headers / "fs.h").write_text("#pragma once\nusing file_t=int;\n#define FILEHND_INVALID (-1)\n")
    raw = STATIC.read_text()
    baseline_selector = subprocess.check_output(
        ["git", "show", BASELINE + ":" + str(SELECTOR.relative_to(ROOT))], cwd=ROOT)
    assert SELECTOR.read_bytes() == baseline_selector, "selection body changed from integration base"
    function = extractor.function
    source = (HERE / "selection_control.cpp.in").read_text()
    geometry = (DC / "room/pvr_geometry.cpp").read_text()
    values = {
        "ROOM": str(DC / "room"), "PICK": function(raw, "struct Pick {"),
        "GROUP_VISIBLE": function(geometry, "bool group_visible("),
        "SELECTOR": function(raw, "struct ScenerySelector {").replace(
            '#include "include/scenery_chunk_select.inc"', SELECTOR.read_text()),
        "LEAN_STATS": function(raw, "struct Stats { unsigned pre_culled"),
        "SG_STATS": function(raw, "struct LeanSgStats {"),
        "SIDE": function(raw, "struct Side {"),
        "SG_PLANE": function(raw, "struct SgPlane {"),
    }
    for key, signature in {
        "SIDE_SETUP": "inline void side_setup(", "ABS9": "inline void abs9(",
        "BOX_CLASS": "inline unsigned box_class(", "BOX_MASK": "inline int box_mask(",
        "SG_COEF": "inline void sg_coef(",
        "SG_SELECT": "__attribute__((noinline)) unsigned sg_select(",
        "SG_COEF_LEAN": "inline void sg_coef_lean(",
        "SG_SELECT_LEAN": "__attribute__((noinline)) unsigned sg_select_lean(",
        "BOX_MASK_LEAN": "inline int box_mask_lean(",
    }.items():
        values[key] = function(raw, signature)
    for key, value in values.items():
        # Count entries only; the actual numeric body and return value remain
        # unchanged. The source hashes below describe the uninstrumented body.
        if key in ("BOX_MASK", "BOX_MASK_LEAN"):
            value = value.replace("{", "{++fixture_box_mask_calls;", 1)
        elif key in ("SG_SELECT", "SG_SELECT_LEAN"):
            value = value.replace("{", "{++fixture_sg_select_calls;", 1)
        source = source.replace("@" + key + "@", value)
    assert not re.search(r"@[A-Z_]+@", source)
    (output / "selection.cpp").write_text(source)
    screen = function(raw, "void load_screen(")
    # Observe memory-key operations without replacing their comparison/copy.
    observed = screen.replace("std::memcmp", "fixture_memcmp").replace("std::memcpy", "fixture_memcpy")
    source = (HERE / "screen_control.cpp.in").read_text().replace("@LOAD_SCREEN@", observed)
    (output / "screen.cpp").write_text(source)
    return {key: hashlib.sha256(value.encode()).hexdigest() for key, value in values.items()
            if key != "ROOM"} | {"LOAD_SCREEN": hashlib.sha256(screen.encode()).hexdigest()}


def compile_run(output, label, source, flags, arguments):
    binary = output / label
    command = ["g++", "-std=c++20", "-O2", "-Wall", "-Wextra", "-Wno-unused-variable",
               "-I" + str(output / "headers"), *flags, str(output / source), "-o", str(binary)]
    result = subprocess.run(command, capture_output=True)
    (output / (label + ".compile.log")).write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr.decode()
    rows = []
    for args in arguments:
        result = subprocess.run([str(binary), *map(str, args)], capture_output=True)
        assert result.returncode == 0, (label, args, result.stderr.decode())
        rows.append((result.stdout, result.stderr.decode()))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output.resolve()
    hashes = generate(output)
    records = cases_module.write_cases(output / "cases")
    arguments = [(output / "cases" / row["file"], sg_on, skipped)
                 for row in records for sg_on in (0, 1) for skipped in (0, 0xfffffffe)]
    selection = []
    for cone in (0, 1):
        for sg in (0, 1):
            arms = []
            for replay in (0, 1):
                label = f"select-c{cone}-s{sg}-r{replay}"
                flags = [f"-DRE4DC_SCENERY_REPLAY_LEAN={replay}", f"-DRE4DC_SCENERY_CONE={cone}",
                         f"-DRE4DC_SG_SELECT_LEAN={sg}"]
                arms.append(compile_run(output, label, "selection.cpp", flags, arguments))
            assert len(arms[0]) == len(arms[1]) == len(arguments)
            inside_cases = {"placement": 0, "classified_cluster": 0}
            for index, ((before, be), (after, ae)) in enumerate(zip(*arms)):
                assert before == after, (cone, sg, arguments[index], "selector output differs")
                assert len(before) == 8 + 28 + 52 + 20 + 16 + 320 * 8
                count, eligible = struct.unpack_from("<2I", before)
                expected = records[index // 4]["expected"]
                if expected is not None:
                    assert count == len(expected) and eligible == 1
                    picks = before[-320 * 8:]
                    for i, item in enumerate(expected):
                        let, nr, mask, lo, hi = struct.unpack_from("<H4B", picks, i * 8)
                        assert (let, nr) == tuple(item[:2])
                        if nr != 255:
                            assert (mask, lo, hi) == tuple(item[2:])
                assert be == ae, "selector helper/prefetch calls changed"
                calls = {key: int(value) for key, value in re.findall(r"(\w+)=(\d+)", be)}
                if calls["inside"]:
                    assert calls["box_masks"] == calls["sg_selects"] == 0
                    kind = "placement" if calls["inside"] == 1 else "classified_cluster"
                    inside_cases[kind] += 1
            assert all(inside_cases.values()), "both existing inside routes must be exercised"
            selection.append(dict(cone=cone, sg=sg, comparisons=len(arguments),
                                  inside_cases=inside_cases, prefetch_requests_unchanged=True))
    screen = [compile_run(output, "screen-r%d" % replay, "screen.cpp",
                          ["-DRE4DC_SCENERY_REPLAY_LEAN=%d" % replay], [()])[0]
              for replay in (0, 1)]
    assert screen[0][0] == screen[1][0] and screen[0][1] == screen[1][1]
    screen_counts = {key: int(value) for key, value in re.findall(r"(\w+)=(\d+)", screen[0][1])}
    assert screen_counts["cases"] == len(screen[0][0]) // 64
    report = dict(status="PASS", scope=__doc__, baseline=BASELINE,
                  selector_identical_to_base=True, selection=selection, screen=screen_counts,
                  extracted_sha256=hashes,
                  source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in (STATIC, SELECTOR, Path(__file__), HERE / "selection_control.cpp.in",
                                              HERE / "screen_control.cpp.in")})
    (output / "selection-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", selection_comparisons=sum(x["comparisons"] for x in selection),
                          screen=screen_counts)))


if __name__ == "__main__":
    main()
