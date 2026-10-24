#!/usr/bin/env python3
"""Bounded source-extracted renderer error annotations, actual WC24 core.

Only admission/refusal blocks run. Package/binding/camera edges and shell
groups are controlled fixtures. No geometry, actual selection, PVR, KOS,
hardware timing, private assets or full-renderer qualification is claimed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def between(text, start, stop):
    assert text.count(start) == 1, start
    first = text.index(start)
    last = text.index(stop, first)
    return text[first:last]


def function(text, signature):
    """Keep a complete source function, ignoring braces inside comments/strings."""
    assert text.count(signature) == 1, signature
    start = text.index(signature)
    first = text.index("{", start)
    token = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]')
    depth = 0
    for found in token.finditer(text, first):
        word = found.group()
        if word == "{":
            depth += 1
        elif word == "}":
            depth -= 1
            if not depth:
                return text[start:found.end()]
    raise AssertionError("unterminated function: " + signature)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, required=True)
    args = ap.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    paths = {
        "static": DC / "game/platform/native_static.cpp",
        "world": DC / "game/platform/native_ps2_world.cpp",
        "owner": DC / "game/platform/include/native_source_world.inc",
        "shell": DC / "game/platform/far_shell.inc",
        "core": DC / "game/world_census24.cpp",
        "header": DC / "game/platform/include/world_census24.h",
        "errors": DC / "game/platform/include/world_census24_errors.inc",
        "template": HERE / "census_errors_hooks.cpp.in",
        "script": Path(__file__),
    }
    raw = {name: path.read_bytes() for name, path in paths.items()}
    text = {name: value.decode() for name, value in raw.items()}
    static, world, owner, shell = (text[name] for name in ("static", "world", "owner", "shell"))
    pass_full = function(static, "int ps2_pass(unsigned pass,float zfar){")
    pass_tail = "#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24\n    wc_result.complete=!c.fallback;"
    source_full = function(owner, 'extern "C" int re4dc_ps2_source_draw(unsigned generation) {')
    flush_full = function(world, 'extern "C" void re4dc_ps2_world_flush(){')
    shell_full = function(shell, 'extern "C" int re4dc_far_shell_draw(float cut, float full) {')
    selections = {
        "PASS_HELPER": between(static, "struct Wc24PassResult {", "\n#endif\nstruct Emitter"),
        "WORLD_HELPER": between(world, "struct Wc24WorldResult {", '\n#endif\n#include "include/ps2_world_data.inc"'),
        "PS2_PASS_PREFIX": pass_full[:pass_full.index("    float cull_far=far;")],
        "PS2_PASS_TAIL": pass_full[pass_full.index(pass_tail):],
        "MESH_CAMERA": function(static, 'extern "C" void re4dc_ps2_mesh_camera(const float* view,const float* projection,const float* viewport){'),
        "MESH_DRAW": function(static, 'extern "C" int re4dc_ps2_mesh_draw(unsigned pass,float zfar){'),
        "SOURCE_PREFIX": source_full[:source_full.index("    sourceWorldImageFrame=frame;sourceWorldImageGeneration=generation;")],
        "FLUSH_PREFIX": flush_full[:flush_full.index("    state.flushed=state.frame;state.pending=false;")],
        "SHELL_PREFIX": shell_full[:shell_full.index("    const float near_w = near * 1.01f;")],
        "SHELL_SELECTION": between(shell_full, "#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24\n        wc_phase.phase(re4dc::wc24::Selection);", "        const Group& g"),
        "SHELL_BIND_SCRATCH": between(shell_full, "        const unsigned mat = g.material & 0x3fffU;", "        ++drawn;"),
        "SHELL_TAIL": shell_full[shell_full.index("#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24\n    wc_phase.phase(re4dc::wc24::Submit);"):],
    }
    generated = text["template"].replace("@DC@", str(DC))
    for name, block in selections.items():
        assert generated.count("@"+name+"@") == 1, name
        generated = generated.replace("@"+name+"@", block)
    assert not re.search(r"@[A-Z_]+@", generated)
    source = out / "hooks.cpp"; source.write_text(generated)
    commands, outputs = {}, {}
    for sanitizers in (False, True):
        kind = "asan-ubsan" if sanitizers else "normal"
        for enabled in (0, 1):
            name = f"{kind}-errors{enabled}"
            exe = out / name
            command = ["g++", "-std=c++17", "-O1" if sanitizers else "-O2", "-g", "-Wall", "-Wextra", "-Werror",
                       "-Wno-misleading-indentation", "-DRE4DC_WORLD_CENSUS24_ERRORS="+str(enabled),
                       "-DRE4DC_WORLD_CENSUS24_HOST=1", "-DRE4DC_WORLD_CENSUS24=1", "-DRE4DC_WORLD_CENSUS24_WINDOW=300",
                       str(source), str(paths["core"]), "-o", str(exe)]
            if sanitizers:
                command += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-fno-sanitize-recover=all"]
            result = subprocess.run(command, capture_output=True, text=True)
            (out / (name+".compile.log")).write_text(result.stdout+result.stderr)
            assert result.returncode == 0, (name, result.stderr)
            # LeakSanitizer cannot enumerate /proc tasks in this executor.
            # Address/undefined-behavior instrumentation remains enabled.
            env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:halt_on_error=1", UBSAN_OPTIONS="halt_on_error=1")
            run = subprocess.run([str(exe)], capture_output=True, text=True, env=env)
            (out / (name+".run.log")).write_text(run.stdout+run.stderr)
            assert run.returncode == 0, (name, run.stderr)
            outputs[name] = json.loads(run.stdout)
            commands[name] = command
        assert outputs[kind+"-errors0"] == outputs[kind+"-errors1"], kind+" aggregate/return/edge mismatch"
    assert outputs["normal-errors0"] == outputs["asan-ubsan-errors0"], "sanitizer changed observed result"
    for name, path in paths.items():
        assert path.read_bytes() == raw[name], "source changed during gate: "+str(path)
    rows = outputs["normal-errors0"]
    result = dict(status="PASS_BOUNDED_PUBLIC_HOST_HOOKS", base=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  cases=len(rows), drawn_ticks_per_case=300, arms=list(outputs),
                  original_snapshot_all_fields_equal=True, returns_and_controlled_edge_counts_equal=True,
                  enabled_reason_site_path_phase_first_details_asserted=True,
                  cpp_compiler=subprocess.check_output(["g++", "--version"], text=True).splitlines()[0],
                  commands=commands, results=rows,
                  extracted_blocks_sha256={name: sha(block.encode()) for name, block in selections.items()},
                  generated_fixture_sha256=sha(generated.encode()),
                  sources_sha256={str(paths[name].relative_to(ROOT)): sha(value) for name, value in raw.items()},
                  edges=["movie","binding","binding-failed","open","r11f-claim","r11f-pass","read-begin","read-end",
                         "pass-tail","group-claim","ui-frame","source-package","transition","coarse-camera","source-tail",
                         "flush-tail","direct-begin","direct-end","shell-group"],
                  limits=["Actual source guard/helper text plus actual WC24 core; controlled external edges and success tails.",
                          "No complete renderer, actual selection, source ownership, geometry, TA/PVR, KOS or hardware timing qualification.",
                          "First-failure scope is asserted for first() branches; generic fallback reports its current Selection scope.",
                          "Shell groups and material/scratch outcomes are synthetic; geometry body is excluded.",
                          "Diagnostic seal logging is allowed to add lines; fixed timer avoids attributing fake serial cost.",
                          "ASan/UBSan enabled; LeakSanitizer disabled because executor /proc task enumeration is unavailable.",
                          "No private game asset or disc inputs."])
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    print(json.dumps({"status": result["status"], "cases": len(rows), "arms": len(outputs), "receipt": str(args.receipt)}))


if __name__ == "__main__":
    main()
