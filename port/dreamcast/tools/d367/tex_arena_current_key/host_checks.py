#!/usr/bin/env python3
"""Source-based texture arena and terminal-refusal host checks.

The classifier, complete load(), logging helper/macros, and allocator are read
from the checkout. Filesystem/package operations are controlled substitutes;
no game assets, full renderer, SH-4 cache behavior, or console result is implied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extracts(source: str) -> dict[str, str]:
    key = next(line for line in source.splitlines() if line.startswith("struct Key {"))
    start = source.index("    struct ArenaClass { explicit ArenaClass(unsigned c)")
    last = "    const ArenaClass arena_class(arena_core?2U:1U);"
    classifier = source[start:source.index(last, start) + len(last)]
    function = source.index("void tex_final_refusal(")
    guard = source.rfind("#if defined(RE4DC_TEX_FINAL_REFUSAL_LOG)", 0, function)
    logging_end = source.index("#endif", function) + len("#endif")
    logging = source[guard:logging_end]
    assert "#define RE4DC_TEX_REFUSE_RETURN" in logging
    start = source.index("Entry* load(const Re4dcUiImage&")
    end = source.index("#undef RE4DC_OPEN_PACKAGE\n", start)
    load = source[start:end]
    assert "RE4DC_TEX_ARENA_CURRENT_KEY" in classifier
    return dict(KEY=key, CLASSIFIER=classifier, LOGGING=logging, LOAD=load)


def run(output: Path, repo: Path = ROOT, compiler: str = "g++") -> dict:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    compiler_path = shutil.which(compiler)
    if not compiler_path:
        raise RuntimeError("A host C++ compiler is required.")
    source = repo / "port/dreamcast/game/platform/native_ui.cpp"
    allocator = repo / "port/dreamcast/game/platform/vram_pages.cpp"
    blocks = extracts(source.read_text())
    frozen = {str(path.relative_to(repo)): sha(path) for path in (source, allocator)}
    rows = []
    with tempfile.TemporaryDirectory(prefix="tex-arena-host-") as temporary:
        work = Path(temporary)
        (work / "stubs/dc").mkdir(parents=True)
        (work / "stubs/kos.h").write_text("#pragma once\n#include <cstddef>\n#define irq_disable_scoped() ((void)0)\n")
        (work / "stubs/dc/pvr.h").write_text("#pragma once\nusing pvr_ptr_t=void*;\n")
        (work / "stubs/re4dc_platform.h").write_text('#pragma once\nextern "C" void re4dc_log(const char*,...);\n')
        (work / "actual_allocator.inc").write_bytes(allocator.read_bytes())
        fixtures = {}
        for kind in ("arena", "load"):
            text = (HERE / f"{kind}_fixture.cpp.in").read_text()
            for key, value in blocks.items():
                text = text.replace("@" + key + "@", value)
            path = work / f"{kind}_fixture.cpp"
            path.write_text(text)
            fixtures[kind] = path
        variants = []
        for fix in (0, 1):
            for core, no_top in ((2, 0), (0, 0), (2, 1)):
                variants.append(("arena", f"arena-f{fix}-c{core}-t{no_top}", fix, 0, core, no_top))
            for log in (0, 1):
                variants.append(("load", f"load-f{fix}-l{log}", fix, log, 2, 0))
        for kind, name, fix, log, core, no_top in variants:
            target = work / name
            command = [compiler_path, "-std=c++17", "-O1", "-g", "-fsanitize=undefined", "-fno-sanitize-recover=all",
                       "-DRE4DC_VRAM_PAGES=1", "-DRE4DC_VRAM_PAGES_VQ_ONLY=1", "-DRE4DC_VRAM_ROOM_ARENA=1",
                       f"-DRE4DC_CORE_PIN={core}", f"-DRE4DC_VRAM_ROOM_ARENA_NO_TOP={no_top}",
                       f"-DRE4DC_TEX_ARENA_CURRENT_KEY={fix}", f"-DRE4DC_TEX_FINAL_REFUSAL_LOG={log}",
                       f"-DRE4DC_ARENA_RING={1 if kind == 'load' else 0}", "-I", str(work / "stubs"),
                       "-I", str(repo / "port/dreamcast/game/platform/include"), str(fixtures[kind]), "-o", str(target)]
            built = subprocess.run(command, capture_output=True, text=True)
            (output / f"{name}-compile.log").write_text(built.stdout + built.stderr)
            if built.returncode:
                raise RuntimeError(f"Compilation failed: {output / (name + '-compile.log')}")
            result = subprocess.run([str(target)], capture_output=True, text=True)
            (output / f"{name}.txt").write_text(result.stdout + result.stderr)
            if result.returncode:
                raise RuntimeError(f"Fixture failed: {output / (name + '.txt')}")
            cases = [line for line in result.stdout.splitlines() if line.startswith("PASS ")]
            rows.append(dict(name=name, kind=kind, fix=fix, log=log, core_pin=core, no_top=no_top,
                             command=command, cases=cases, stdout=result.stdout, stderr=result.stderr))
            print("PASS", name, len(cases), "cases", flush=True)
    if frozen != {str(path.relative_to(repo)): sha(path) for path in (source, allocator)}:
        raise RuntimeError("Runtime source changed during the host controls; rerun on frozen input.")
    report = dict(status="PASS", scope=__doc__, source_sha256=frozen,
                  gate_sha256={path.name: sha(path) for path in (Path(__file__), HERE / "arena_fixture.cpp.in", HERE / "load_fixture.cpp.in")},
                  extracted_sha256={name: hashlib.sha256(value.encode()).hexdigest() for name, value in blocks.items()},
                  compiler=subprocess.check_output([compiler_path, "--version"], text=True).splitlines()[0],
                  variants=rows, case_executions=sum(len(row["cases"]) for row in rows))
    (output / "host-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--compiler", default="g++")
    args = parser.parse_args()
    result = run(args.output, args.repo.resolve(), args.compiler)
    print(json.dumps(dict(status=result["status"], variants=len(result["variants"]),
                          case_executions=result["case_executions"], receipt=str(args.output / "host-controls.json"))))


if __name__ == "__main__":
    main()
