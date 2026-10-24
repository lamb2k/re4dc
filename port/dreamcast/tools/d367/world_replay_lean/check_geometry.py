#!/usr/bin/env python3
"""Host replay equivalence with validated meshes and actual portable geometry.

Runs production Emitter/borrow/gather/emit_pick/strips_lean/clipper/replay bodies,
the existing portable vertex transform, and a documented C SQ-walk adapter.
It compares every TA word and accounting word. This is host arithmetic, not
SH4 FTRV/FSRRA execution, a full game frame, or a performance measurement.
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
BASELINE = "451bed6faa2c37f7f9aa05d6fb1116ec64219ebc"
spec = importlib.util.spec_from_file_location("boundary_source", HERE / "check_runtime.py")
boundary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boundary)
original = boundary.original
function = original.function


def sources():
    values = original.extract()
    raw = original.STATIC.read_text()
    old = subprocess.check_output(["git", "show", BASELINE + ":" + str(original.STATIC.relative_to(ROOT))], cwd=ROOT).decode()
    names = {
        "EMITTER": "struct Emitter {", "BORROW_GATHER": "bool borrow_gather(){",
        "CORNERS": "const re4dc::room::CompactVertex12* corners(",
        "BORROW": "bool borrow(){", "LEAN_FLUSH": "void lean_flush(",
        "STRIPS_LEAN": "const std::uint8_t* strips_lean(", "EMIT_PICK": "int emit_pick(",
        "ALPHA_LUT": "const std::uint32_t* ps2_vertex_alpha_lut(){",
    }
    identity = {}
    for name, signature in names.items():
        current, baseline = function(raw, signature), function(old, signature)
        assert current == baseline, (name, "reachable geometry body changed")
        values[name] = current
        identity[name] = hashlib.sha256(current.encode()).hexdigest()
    values["LOAD_SCREEN"] = function(raw, "void load_screen(")
    values["REPLAY_RESTART"] = "#if RE4DC_SCENERY_REPLAY_LEAN\n" + function(
        raw, "[[gnu::always_inline]] void chunk_restart()") + "\n#endif"
    geometry = (DC / "room/pvr_geometry.cpp").read_text()
    for name, signature in (("SHADE_COLOR", "std::uint32_t shade_color("),
        ("INTERPOLATE_VERTEX", "RenderVertex interpolate_vertex("),
        ("CLIP_PROJECTED_TRIANGLE", "std::uint32_t clip_projected_triangle(")):
        values[name] = function(geometry, signature)
    active = "\n".join(values[name] for name in names)
    stats = sorted(set(re.findall(r"\bstats\.(\w+)", active)))
    values["STATIC_STATS"] = "static struct {unsigned " + ",".join(name + "=0" for name in stats) + ";}stats;"
    values["REPORT_STATS"] = "queue_events.insert(queue_events.end(),{" + ",".join("stats." + name for name in stats) + "});"
    values["ROOT"] = str(ROOT)
    template = (HERE / "fixture_boundary.cpp.in").read_text()
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
// Simulated packet pressure at the texture-acquired edge, before begin fills
// scratch_capacity. The first part succeeds; the second must revalidate borrow.
if(geometry_low_at&&acquired==geometry_low_at)model_pending=kModelPacketBytes/32-300;
""")
    template = template.replace("@QUEUE_FIXTURE@", (HERE / "fixture_geometry.cpp.in").read_text())
    for name, value in values.items():
        template = template.replace("@" + name + "@", value)
    assert not re.search(r"@[A-Z_]+@", template)
    return template, values, identity


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--compile-only", action="store_true")
    args = p.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / "shim/dc").mkdir(parents=True)
    (output / "shim/kos").mkdir()
    (output / "shim/dc/pvr.h").write_text("#pragma once\n// Types are supplied by the controlled TA sink before production headers.\n")
    (output / "shim/kos/fs.h").write_text("#pragma once\nusing file_t=int;\n#define FILEHND_INVALID (-1)\n")
    (output / "shim/dc/matrix.h").write_text("""#pragma once
using matrix_t=float[4][4];
static void mat_load(const matrix_t* m){std::memcpy(vp_host_xmtrx,*m,sizeof(matrix_t));}
static void mat_trans_nodiv(float& x,float& y,float& z,float& w){VP_FTRV(x,y,z,w);}
""")
    text, values, identity = sources()
    fixture = output / "geometry.cpp"
    fixture.write_text(text)
    cases = list(range(100, 166))
    rows, hashes = [], {}
    for select, batch in itertools.product((0, 1), repeat=2):
        pair = f"s{select}-b{batch}"
        baseline = None
        for replay in (0, 1):
            label = pair + f"-r{replay}"
            binary = output / label
            command = ["g++", "-std=c++20", "-O2", "-ffp-contract=off", "-Wall", "-Wextra",
                       f"-DRE4DC_SCENERY_SELECT_ONLY={select}", f"-DRE4DC_SCENERY_SUBMIT_BATCH={batch}",
                       f"-DRE4DC_SCENERY_REPLAY_LEAN={replay}", "-DCHECK_DIAGNOSTICS=0",
                       "-I" + str(output / "shim"), "-I" + str(DC / "game/platform/include"),
                       str(fixture), "-o", str(binary)]
            run = subprocess.run(command, cwd=ROOT, capture_output=True)
            (output / (label + ".compile.log")).write_bytes(run.stdout + run.stderr)
            assert run.returncode == 0, (label, run.stderr.decode())
            if args.compile_only:
                print(json.dumps(dict(status="COMPILED", binary=str(binary))))
                return
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
            if not replay:
                baseline = reports
            else:
                differences = [case for case, old, new in zip(cases, baseline, reports) if old != new]
                assert not differences, (label, "TA/accounting words differ", differences)
        rows.append(dict(select=select, submit_batch=batch, comparisons=len(cases), exact_words_equal=True))
    files = [original.STATIC, original.SOURCE,
             *[DC / "room" / name for name in ("mesh_fastpath.hpp", "mesh_fastpath_sched.hpp", "mesh_strip_lean.hpp",
                "pvr_geometry.cpp", "pvr_geometry.hpp", "static_room_prepare.hpp", "instanced_mesh.hpp", "room_package.hpp")]]
    report = dict(status="PASS", comparisons=len(cases) * 4, baseline=BASELINE,
                  source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
                  unchanged_production_body_sha256=identity,
                  extracted_sha256={name: hashlib.sha256(value.encode()).hexdigest() for name, value in values.items()},
                  combinations=rows, output_sha256=hashes, scope=__doc__)
    (output / "geometry-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", comparisons=report["comparisons"], configurations=8)))


if __name__ == "__main__":
    main()
