#!/usr/bin/env python3
"""Build 5 host TA-word equivalence through the actual emitter bodies.

Reuses the earlier replay controls' synthetic package, texture/SQ sink and
portable geometry adapter. Production emit/replay/borrow/clip bodies are
extracted from the current source. Every TA and accounting word is compared
with SCENERY_EMIT_PREFETCH off/on across the required preceding switches.
Picks are controlled inputs; selection itself is not executed. This is host
geometry evidence, not target FTRV/FSRRA or a game frame.
"""
import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
PRIOR = DC / "tools/d367/world_replay_lean"
KNOBS = ("SCENERY_SELECT_ONLY", "SCENERY_SUBMIT_BATCH", "SCENERY_REPLAY_LEAN",
         "SCENERY_UV_SNAPSHOT", "SCENERY_SELECT_LEAN2")
spec = importlib.util.spec_from_file_location("emit_geometry_prior", PRIOR / "check_geometry.py")
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
original, function = prior.original, prior.function


def sources():
    values = original.extract()
    raw = original.STATIC.read_text()
    # Both mutually exclusive signatures open the same source body. Parse
    # its braces from the second signature, retaining both guarded headers.
    old_signature = "__attribute__((noinline)) int chunk_emit(const Pick* pk,unsigned n){"
    first = raw.index("__attribute__((noinline)) int chunk_emit(")
    second = raw.index(old_signature, first)
    if first != second:
        begin = raw.rfind("#if RE4DC_SCENERY_EMIT_PREFETCH", 0, first)
        assert begin >= 0 and "#else" in raw[first:second]
        values["CHUNK_EMIT"] = raw[begin:second + len(function(raw, old_signature))]
    names = {
        "EMITTER": "struct Emitter {", "BORROW_GATHER": "bool borrow_gather(){",
        "CORNERS": "const re4dc::room::CompactVertex12* corners(",
        "BORROW": "bool borrow(){", "LEAN_FLUSH": "void lean_flush(",
        "STRIPS_LEAN": "const std::uint8_t* strips_lean(", "EMIT_PICK": "int emit_pick(",
        "ALPHA_LUT": "const std::uint32_t* ps2_vertex_alpha_lut(){",
    }
    for name, signature in names.items():
        values[name] = function(raw, signature)
    begin, end = "// SCENERY_EMIT_PREFETCH_MEMBERS_BEGIN", "// SCENERY_EMIT_PREFETCH_MEMBERS_END"
    if begin in raw:
        assert raw.count(begin) == raw.count(end) == 1
        members = raw.split(begin, 1)[1].split(end, 1)[0]
        values["EMIT_MEMBERS"] = "#if RE4DC_SCENERY_EMIT_PREFETCH\n" + members + "\n#endif"
    else:
        values["EMIT_MEMBERS"] = ""
    values["LOAD_SCREEN"] = function(raw, "void load_screen(")
    values["REPLAY_RESTART"] = "#if RE4DC_SCENERY_REPLAY_LEAN\n" + function(
        raw, "[[gnu::always_inline]] void chunk_restart()") + "\n#endif"
    geometry = (DC / "room/pvr_geometry.cpp").read_text()
    for name, signature in (("SHADE_COLOR", "std::uint32_t shade_color("),
        ("INTERPOLATE_VERTEX", "RenderVertex interpolate_vertex("),
        ("CLIP_PROJECTED_TRIANGLE", "std::uint32_t clip_projected_triangle(")):
        values[name] = function(geometry, signature)
    active = "\n".join(values[name] for name in (*names, "EMIT_MEMBERS"))
    stats = sorted(set(re.findall(r"\bstats\.(\w+)", active)))
    values["STATIC_STATS"] = "static struct {unsigned " + ",".join(name + "=0" for name in stats) + ";}stats;"
    values["REPORT_STATS"] = "queue_events.insert(queue_events.end(),{" + ",".join("stats." + name for name in stats) + "});"
    values["ROOT"] = str(ROOT)
    template = (PRIOR / "fixture_boundary.cpp.in").read_text()
    template = template.replace("struct Packet { std::uint32_t word[8]; };", """struct Packet {
    std::uint32_t flags;float x,y,z,u,v;std::uint32_t argb,oargb;
};
using pvr_vertex_t=Packet;
constexpr std::uint32_t PVR_CMD_VERTEX=0xe0000000U,PVR_CMD_VERTEX_EOL=0xf0000000U;
float vp_host_xmtrx[4][4];
static unsigned geometry_low_at;""")
    template = template.replace("static void sourceWorldTextureAcquired(Key){++acquired;", """static void sourceWorldTextureAcquired(Key){
std::fill(&vp_host_xmtrx[0][0],&vp_host_xmtrx[0][0]+16,-9999.0f);
++acquired;
if(geometry_low_at&&acquired==geometry_low_at)model_pending=kModelPacketBytes/32-300;
""")
    template = template.replace("@QUEUE_FIXTURE@", (HERE / "fixture_geometry.cpp.in").read_text())
    for name, value in values.items():
        template = template.replace("@" + name + "@", value)
    assert not re.search(r"@[A-Z_]+@", template)
    return template, values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sanitize", action="store_true")
    parser.add_argument("--quick", action="store_true", help="One enabled prior-switch combination")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    files = [original.STATIC, original.SOURCE, Path(__file__), HERE / "fixture_geometry.cpp.in",
             PRIOR / "fixture_boundary.cpp.in", PRIOR / "check_geometry.py",
             *[DC / "room" / name for name in ("mesh_fastpath.hpp", "mesh_fastpath_sched.hpp", "mesh_strip_lean.hpp",
                "pvr_geometry.cpp", "pvr_geometry.hpp", "static_room_prepare.hpp", "instanced_mesh.hpp", "room_package.hpp")]]
    input_hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    (output / "shim/dc").mkdir(parents=True)
    (output / "shim/kos").mkdir()
    (output / "shim/dc/pvr.h").write_text("#pragma once\n// Types supplied by the controlled TA sink.\n")
    (output / "shim/kos/fs.h").write_text("#pragma once\nusing file_t=int;\n#define FILEHND_INVALID (-1)\n")
    (output / "shim/dc/matrix.h").write_text("""#pragma once
using matrix_t=float[4][4];
static void mat_load(const matrix_t* m){std::memcpy(vp_host_xmtrx,*m,sizeof(matrix_t));}
static void mat_trans_nodiv(float& x,float& y,float& z,float& w){VP_FTRV(x,y,z,w);}
""")
    text, values = sources()
    fixture = output / "geometry.cpp"
    fixture.write_text(text)
    cases = list(range(100, 178))
    combinations = [(1, 1, 1, 1, 1)] if args.quick or args.sanitize else itertools.product((0, 1), repeat=5)
    rows, hashes = [], {}
    for bits in combinations:
        pair = "s%d-b%d-r%d-u%d-q%d" % bits
        baseline, old_locks = None, None
        for enabled in (0, 1):
            label = pair + f"-e{enabled}"
            binary = output / label
            command = ["g++", "-std=c++20", "-O2", "-ffp-contract=off", "-Wall", "-Wextra",
                       *(f"-DRE4DC_{name}={value}" for name, value in zip(KNOBS, bits)),
                       f"-DRE4DC_SCENERY_EMIT_PREFETCH={enabled}", "-DCHECK_DIAGNOSTICS=0",
                       "-I" + str(output / "shim"), "-I" + str(DC / "game/platform/include"),
                       str(fixture), "-o", str(binary)]
            if args.sanitize:
                command[3:3] = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-fno-pie", "-no-pie"]
            run = subprocess.run(command, cwd=ROOT, capture_output=True)
            (output / (label + ".compile.log")).write_bytes(run.stdout + run.stderr)
            assert run.returncode == 0, (label, run.stderr.decode())
            reports, errors = [], []
            for case in cases:
                run = subprocess.run([str(binary), str(case)], cwd=ROOT, capture_output=True)
                if run.returncode:
                    (output / (label + f"-case{case}.failed.txt")).write_bytes(run.stdout + run.stderr)
                    raise AssertionError((label, case, run.stderr.decode()))
                assert len(run.stdout.splitlines()) == 3, (label, case, "incomplete report")
                reports.append(run.stdout)
                errors.append(run.stderr)
            data, stderr = b"".join(reports), b"".join(errors)
            (output / (label + ".stdout")).write_bytes(data)
            (output / (label + ".stderr")).write_bytes(stderr)
            hashes[label] = hashlib.sha256(data).hexdigest()
            locks = re.findall(rb"(\d+) lock=(\d+) unlock=(\d+)", stderr)
            assert [int(x[0]) for x in locks] == cases
            assert all(x[1] == x[2] for x in locks)
            if not enabled:
                baseline, old_locks = reports, locks
            else:
                differences = [case for case, old, new in zip(cases, baseline, reports) if old != new]
                assert not differences, (label, "TA/accounting words differ", differences)
                assert locks == old_locks, (label, "SQ ownership changed")
        rows.append(dict(knobs=dict(zip(KNOBS, bits)), comparisons=len(cases), exact_words_equal=True))
        print("PASS", pair, flush=True)
    for name, digest in input_hashes.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, (name, "changed during control run")
    report = dict(status="PASS", comparisons=len(cases) * len(rows), sanitized=args.sanitize,
                  source_sha256=input_hashes,
                  extracted_sha256={name: hashlib.sha256(value.encode()).hexdigest() for name, value in values.items()},
                  combinations=rows, output_sha256=hashes, scope=__doc__)
    (output / "geometry-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", comparisons=report["comparisons"], configurations=len(rows)*2)))


if __name__ == "__main__":
    main()
