#!/usr/bin/env python3
"""Compare Build 5's literal TA/state words on controlled valid R4IM inputs.

The production emitter, gather, replay, material and clip bodies execute with
the repository's portable transform and the replay fixture's C SQ-walk edge.
DEDUP's two SH-4 FMAC statements have a documented portable arithmetic edge.
Both arms use the same host arithmetic; this is neither target floating-point
qualification nor a game-data/console trace. Selection is supplied as controlled
valid picks: SELECT_ONLY/SELECT_LEAN2 are composition labels, not selection tests.
Ordinary RAM-prefetch addresses and work counters are reported separately from
TA/accounting words. Requests must remain within registered live input ranges.
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
BASELINE = "20df6734578cacc7033bb32a660d4b466a7cfbe9"
spec = importlib.util.spec_from_file_location(
    "emit_submission_source", HERE.parent / "world_submit_spike/check_runtime.py")
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)
function = original.function


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def replace_once(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)


def sources(baseline=BASELINE):
    values = original.extract()
    # The old lexical brace parser counts both arms of conditional function
    # signatures. Keep the whole guarded emit-method region instead.
    del values["CHUNK_EMIT"]
    raw = original.STATIC.read_text()
    old = subprocess.check_output(
        ["git", "show", baseline + ":" + str(original.STATIC.relative_to(ROOT))], cwd=ROOT).decode()
    names = {
        "EMITTER": "struct Emitter {", "BORROW_GATHER": "bool borrow_gather(){",
        "CORNERS": "const re4dc::room::CompactVertex12* corners(",
        "BORROW": "bool borrow(){", "LEAN_FLUSH": "void lean_flush(",
        "STRIPS_LEAN": "const std::uint8_t* strips_lean(",
        "ALPHA_LUT": "const std::uint32_t* ps2_vertex_alpha_lut(){",
        "LOAD_SCREEN": "void load_screen(", "DD_WORD": "std::uint32_t dd_word(",
    }
    unchanged = {}
    for name, signature in names.items():
        current, before = function(raw, signature), function(old, signature)
        assert current == before, (name, "unexpected reachable body change")
        unchanged[name] = sha(current)
        values[name] = current
    selector = '#include "include/scenery_chunk_select.inc"'
    first = raw.index(selector) + len(selector)
    last = raw.index("\n    int run(){", first)
    methods = raw[first:last]
    assert methods.rstrip().endswith("#endif"), "Missing outer SCENERY_CHUNK end"
    values["EMIT_METHODS"] = methods[:methods.rindex("#endif")]
    dedup = function(raw, "namespace dedup {")
    assert dedup == function(old, "namespace dedup {"), "DEDUP source changed"
    unchanged["DEDUP_TARGET_BODY"] = sha(dedup)
    # This is the only arithmetic substitution beyond the existing portable
    # transform/SQ-walk fixture. Inputs use binary-exact UV scales. We compare
    # off/on, not SH-4 FMAC rounding against host multiplication/addition.
    dedup = replace_once(dedup, '__asm__("fmac fr0,%1,%0" : "+f"(ru) : "f"(au),"w"(fu));',
                         "ru=fu*au+ru;")
    dedup = replace_once(dedup, '__asm__("fmac fr0,%1,%0" : "+f"(rv) : "f"(av),"w"(fv));',
                         "rv=fv*av+rv;")
    values["DEDUP"] = dedup
    geometry = (DC / "room/pvr_geometry.cpp").read_text()
    for name, signature in (("SHADE_COLOR", "std::uint32_t shade_color("),
        ("INTERPOLATE_VERTEX", "RenderVertex interpolate_vertex("),
        ("CLIP_PROJECTED_TRIANGLE", "std::uint32_t clip_projected_triangle(")):
        values[name] = function(geometry, signature)
    active = "\n".join(values.values())
    stats = sorted(set(re.findall(r"\bstats\.(\w+)", active)))
    values["STATIC_STATS"] = "static struct {unsigned " + ",".join(name + "=0" for name in stats) + ";}stats;"
    values["REPORT_STATS"] = "queue_events.insert(queue_events.end(),{" + ",".join("stats." + name for name in stats) + "});"
    values["ROOT"] = str(ROOT)
    template = (HERE / "boundary.cpp.in").read_text()
    template = replace_once(template, "struct Packet { std::uint32_t word[8]; };", """struct Packet {
    std::uint32_t flags;float x,y,z,u,v;std::uint32_t argb,oargb;
};
using pvr_vertex_t=Packet;
constexpr std::uint32_t PVR_CMD_VERTEX=0xe0000000U,PVR_CMD_VERTEX_EOL=0xf0000000U;
float vp_host_xmtrx[4][4];
static unsigned geometry_low_at;""")
    template = replace_once(template, "static void sourceWorldTextureAcquired(Key){++acquired;", """static void sourceWorldTextureAcquired(Key){
std::fill(&vp_host_xmtrx[0][0],&vp_host_xmtrx[0][0]+16,-9999.0f);
++acquired;
if(geometry_low_at&&acquired==geometry_low_at)model_pending=kModelPacketBytes/32-300;
""")
    template = template.replace("@QUEUE_FIXTURE@", (HERE / "geometry.cpp.in").read_text())
    for name, value in values.items():
        template = template.replace("@" + name + "@", value)
    assert not re.search(r"@[A-Z_]+@", template), "Unfilled extraction seam"
    return template, values, unchanged


def write_shims(output):
    (output / "shim/dc").mkdir(parents=True)
    (output / "shim/kos").mkdir()
    (output / "shim/dc/pvr.h").write_text("#pragma once\n// Controlled TA sink supplies types.\n")
    (output / "shim/kos/fs.h").write_text("#pragma once\nusing file_t=int;\n#define FILEHND_INVALID (-1)\n")
    (output / "shim/dc/matrix.h").write_text("""#pragma once
using matrix_t=float[4][4];
static void mat_load(const matrix_t* m){std::memcpy(vp_host_xmtrx,*m,sizeof(matrix_t));}
static void mat_trans_nodiv(float& x,float& y,float& z,float& w){VP_FTRV(x,y,z,w);}
""")


def run_cases(binary, cases, mode, mask, output, label):
    reports, errors = [], []
    for case in cases:
        run = subprocess.run([str(binary), str(case), str(mode), str(mask)], cwd=ROOT, capture_output=True)
        if run.returncode:
            failed = output / (label + f"-c{case}.failed.txt")
            failed.write_bytes(run.stdout + run.stderr)
            raise AssertionError((label, case, run.returncode, run.stderr.decode()))
        assert len(run.stdout.splitlines()) == 3, (label, case, "incomplete report")
        reports.append(run.stdout)
        errors.append(run.stderr)
    data, stderr = b"".join(reports), b"".join(errors)
    (output / (label + ".stdout")).write_bytes(data)
    (output / (label + ".stderr")).write_bytes(stderr)
    locks = re.findall(rb"(\d+) lock=(\d+) unlock=(\d+)", stderr)
    assert [int(x[0]) for x in locks] == cases
    assert all(x[1] == x[2] for x in locks), "Unbalanced store-queue ownership"
    work = re.findall(rb"WORK (\d+) prime_reuse=(\d+) prime_bad=(\d+) primed=(\d+)", stderr)
    assert [int(x[0]) for x in work] == cases and all(int(x[2]) == 0 for x in work)
    prefetch = re.findall(rb"PREF (\d+)([^\n]*)", stderr)
    assert [int(x[0]) for x in prefetch] == cases
    requests = {int(case): [int(v) for v in words.split()] for case, words in prefetch}
    assert all(len(words) % 2 == 0 for words in requests.values())
    return dict(reports=reports, sha256=sha(data), locks=locks,
                work=[[int(v) for v in row] for row in work],
                prefetch_requests={case: len(words)//2 for case, words in requests.items()},
                prefetch_sha256=sha(json.dumps(requests, sort_keys=True)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baseline", default=BASELINE)
    parser.add_argument("--smoke", action="store_true", help="One release-knob combination; not the full gate")
    parser.add_argument("--sanitize", action="store_true", help="ASan/UBSan on the requested matrix")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_shims(output)
    source, values, identity = sources(args.baseline)
    fixture = output / "geometry.cpp"
    fixture.write_text(source)
    cases = list(range(100, 166)) + list(range(200, 232)) + list(range(240, 256)) + list(range(300, 316))
    combos = [(1, 1, 1, 1, 1)] if args.smoke else list(itertools.product((0, 1), repeat=5))
    knobs = ("SELECT_ONLY", "SUBMIT_BATCH", "REPLAY_LEAN", "UV_SNAPSHOT", "SELECT_LEAN2")
    pairs = [(0, 0)] if args.smoke else list(itertools.product((0, 1), repeat=2))
    rows, hashes, compilation_cache, run_cache = [], {}, {}, {}
    compile_rows, comparisons, process_cases = [], 0, 0
    for combo in combos:
        for prefwalk, census in pairs:
            label = "-".join(f"{k.lower()}{v}" for k, v in zip(knobs, combo)) + f"-w{prefwalk}-c{census}"
            arms = {}
            for enabled in (0, 1):
                name = label + f"-p{enabled}"
                defines = [f"-DRE4DC_SCENERY_{k}={v}" for k, v in zip(knobs, combo)]
                defines += [f"-DRE4DC_SCENERY_EMIT_PREFETCH={enabled}", f"-DRE4DC_PREF_WALK={prefwalk}",
                            f"-DRE4DC_SCN_CENSUS={census}", "-DCHECK_DIAGNOSTICS=0"]
                command = ["g++", "-std=c++20", "-O2", "-ffp-contract=off", "-Wall", "-Wextra", *defines,
                    "-I" + str(output / "shim"), "-I" + str(DC / "game/platform/include"),
                    "-I" + str(DC / "game/platform")]
                if args.sanitize:
                    command += ["-fsanitize=address,undefined", "-fno-sanitize-recover=all", "-fno-omit-frame-pointer", "-fno-pie", "-no-pie"]
                pp = subprocess.run([*command, "-E", "-P", str(fixture)], cwd=ROOT, capture_output=True)
                assert pp.returncode == 0, (name, pp.stderr.decode())
                key = sha(pp.stdout)
                if key not in compilation_cache:
                    binary = output / ("geometry-" + key[:16])
                    run = subprocess.run([*command, str(fixture), "-o", str(binary)], cwd=ROOT, capture_output=True)
                    (output / (name + ".compile.log")).write_bytes(run.stdout + run.stderr)
                    assert run.returncode == 0, (name, run.stderr.decode())
                    binary.chmod(binary.stat().st_mode | 0o111)
                    compilation_cache[key] = binary
                binary = compilation_cache[key]
                compile_rows.append(dict(configuration=name, preprocessed_sha256=key,
                                         binary=binary.name, command=command))
                arms[enabled] = {}
                for mode in (0, 1, 2):
                    for mask in ((4, 0) if prefwalk else (4,)):
                        run_key = (key, mode, mask)
                        run_label = name + f"-m{mode}-mask{mask}"
                        if run_key not in run_cache:
                            run_cache[run_key] = run_cases(binary, cases, mode, mask, output, run_label)
                            process_cases += len(cases)
                        arms[enabled][mode, mask] = run_cache[run_key]
                        hashes[run_label] = run_cache[run_key]["sha256"]
            for context in arms[0]:
                before, after = arms[0][context], arms[1][context]
                different = [c for c, a, b in zip(cases, before["reports"], after["reports"]) if a != b]
                if different:
                    (output / (label + "-differences.json")).write_text(json.dumps(different) + "\n")
                    raise AssertionError((label, context, "TA/accounting words differ", different))
                assert before["locks"] == after["locks"], (label, context, "ownership boundary changed")
                work_changes = [dict(case=a[0], before=a[1:], after=b[1:])
                                for a, b in zip(before["work"], after["work"]) if a != b]
                comparisons += len(cases)
                rows.append(dict(configuration=label, snapshot_mode=context[0], prefetch_mask=context[1],
                    comparisons=len(cases), exact_ta_and_accounting=True,
                    work_counter_changes=work_changes,
                    prefetch_before=before["prefetch_requests"], prefetch_after=after["prefetch_requests"],
                    prefetch_sha256_before=before["prefetch_sha256"], prefetch_sha256_after=after["prefetch_sha256"]))
    files = [original.STATIC, original.SOURCE, HERE / "geometry.cpp.in", HERE / "boundary.cpp.in", Path(__file__),
             *[DC / "room" / name for name in ("mesh_fastpath.hpp", "mesh_fastpath_sched.hpp", "mesh_strip_lean.hpp",
                "pvr_geometry.cpp", "pvr_geometry.hpp", "static_room_prepare.hpp", "instanced_mesh.hpp", "room_package.hpp")]]
    report = dict(status="PASS", baseline=args.baseline, smoke=args.smoke, sanitized=args.sanitize,
        configurations=len(compile_rows), distinct_compiled_inputs=len(compilation_cache),
        comparisons=comparisons, executed_process_cases=process_cases, cases=cases,
        source_sha256={str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in files},
        fixture_sha256=sha(source), unchanged_production_body_sha256=identity,
        extracted_sha256={name: sha(value) for name, value in values.items()},
        compile_configurations=compile_rows, combinations=rows, output_sha256=hashes, scope=__doc__)
    (output / "geometry-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "smoke", "sanitized", "configurations", "distinct_compiled_inputs", "comparisons", "executed_process_cases")}))


if __name__ == "__main__":
    main()
