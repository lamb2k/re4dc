#!/usr/bin/env python3
"""Compare UV snapshots against immediate per-row production replay.

Reuses the qualified replay fixture's actual production material, emitter,
borrow/gather, portable transform, strip caller and clipper bodies. The SH4 SQ
walk has its documented C adapter. Compares literal TA and semantic state words,
not only hashes. These are synthetic host controls, not a game or console trace.
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
BASELINE = "28da09802ed9ff6756529bab02978230983453be"
spec = importlib.util.spec_from_file_location("uv_geometry_reference", HERE.parent / "world_replay_lean/check_geometry.py")
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)
reference.BASELINE = BASELINE


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def sources():
    source, values, identity = reference.sources()
    source = replace_once(source, "static void queue_case(unsigned id){", "static unsigned snapshot_mode;\nstatic void queue_case(unsigned id){")
    source = replace_once(source,
        "part.uv_offset[0]=float(variant%3)*.125f;part.uv_offset[1]=-float(variant%5)*.0625f;",
        """part.uv_offset[0]=snapshot_mode==0?0.0f:float(variant%3)*.125f;
    part.uv_offset[1]=snapshot_mode==0?0.0f:-float(variant%5)*.0625f;
    if(snapshot_mode>=2){part.uv_offset[0]=(variant&2)?0.0f:.9375f;part.uv_offset[1]=(variant&2)?-0.0f:-.8125f;}
    std::uint32_t pending_uv[2];std::memcpy(pending_uv,part.uv_offset,sizeof(pending_uv));
    float expected_uv[48][2]{};""")
    source = replace_once(source,
        "key_for(x.index,0,x.cull,x.key);x.first=npk;x.count=2;x.cull_far=1000;x.lod_scale=2;",
        """key_for(x.index,0,x.cull,x.key);x.first=npk;x.count=2;x.cull_far=1000;x.lod_scale=2;
        if(snapshot_mode>=2){expected_uv[j][0]=j%7?float(int(j%7)-3)*.125f:-0.0f;
            expected_uv[j][1]=float(int(j%5)-2)*.0625f;}
        else std::memcpy(expected_uv[j],part.uv_offset,sizeof(expected_uv[j]));
#if RE4DC_SCENERY_UV_SNAPSHOT
        std::memcpy(x.uv_offset,expected_uv[j],sizeof(x.uv_offset));
#endif""")
    source = replace_once(source,
        "const int result=chunk_flush();assert(!locked&&!direct_open);",
        """int result=1;
    if(snapshot_mode==3){
        // Independent oracle: the old queue emitter sees each intended owner
        // value immediately. No snapshot field or snapshot restore is used.
        ChunkPart saved[kChunkParts];std::memcpy(saved,cctx,sizeof(saved));
        const unsigned picks=npk;
        for(unsigned j=0;j<count;++j){cctx[0]=saved[j];nctx=1;npk=picks;
            std::memcpy(part.uv_offset,expected_uv[j],sizeof(expected_uv[j]));
            result=chunk_flush();if(result<0)break;}
        std::memcpy(part.uv_offset,pending_uv,sizeof(pending_uv));
    }else result=chunk_flush();
    assert(std::memcmp(part.uv_offset,pending_uv,sizeof(pending_uv))==0);
    queue_events.insert(queue_events.end(),{pending_uv[0],pending_uv[1]});
    assert(!locked&&!direct_open);""")
    source = replace_once(source,
        "const unsigned id=argc>1?unsigned(std::strtoul(argv[1],nullptr,10)):0;",
        "const unsigned id=argc>1?unsigned(std::strtoul(argv[1],nullptr,10)):0;\n    snapshot_mode=argc>2?unsigned(std::strtoul(argv[2],nullptr,10)):0;")
    return source, values, identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / "shim/dc").mkdir(parents=True)
    (output / "shim/kos").mkdir()
    (output / "shim/dc/pvr.h").write_text("#pragma once\n// Controlled TA sink supplies types.\n")
    (output / "shim/kos/fs.h").write_text("#pragma once\nusing file_t=int;\n#define FILEHND_INVALID (-1)\n")
    (output / "shim/dc/matrix.h").write_text("""#pragma once
using matrix_t=float[4][4];
static void mat_load(const matrix_t* m){std::memcpy(vp_host_xmtrx,*m,sizeof(matrix_t));}
static void mat_trans_nodiv(float& x,float& y,float& z,float& w){VP_FTRV(x,y,z,w);}
""")
    source, values, identity = sources()
    fixture = output / "geometry.cpp"
    fixture.write_text(source)
    cases = list(range(100, 166))
    rows, hashes = [], {}
    for select, batch, replay in itertools.product((0, 1), repeat=3):
        combo = f"s{select}-b{batch}-r{replay}"
        results = {}
        for snapshot in (0, 1):
            label = combo + f"-u{snapshot}"
            binary = output / label
            command = ["g++", "-std=c++20", "-O2", "-ffp-contract=off", "-Wall", "-Wextra",
                f"-DRE4DC_SCENERY_SELECT_ONLY={select}", f"-DRE4DC_SCENERY_SUBMIT_BATCH={batch}",
                f"-DRE4DC_SCENERY_REPLAY_LEAN={replay}", f"-DRE4DC_SCENERY_UV_SNAPSHOT={snapshot}",
                "-DCHECK_DIAGNOSTICS=0", "-I" + str(output / "shim"),
                "-I" + str(DC / "game/platform/include"), str(fixture), "-o", str(binary)]
            run = subprocess.run(command, cwd=ROOT, capture_output=True)
            (output / (label + ".compile.log")).write_bytes(run.stdout + run.stderr)
            assert run.returncode == 0, (label, run.stderr.decode())
            for mode in ((0, 1, 2, 3) if snapshot == 0 else (0, 1, 2)):
                reports, errors = [], []
                for case in cases:
                    run = subprocess.run([str(binary), str(case), str(mode)], cwd=ROOT, capture_output=True)
                    if run.returncode:
                        (output / (label + f"-m{mode}-c{case}.failed.txt")).write_bytes(run.stdout + run.stderr)
                        raise AssertionError((label, mode, case, run.stderr.decode()))
                    assert len(run.stdout.splitlines()) == 3, (label, mode, case, "incomplete report")
                    reports.append(run.stdout)
                    errors.append(run.stderr)
                data, stderr = b"".join(reports), b"".join(errors)
                key = label + f"-m{mode}"
                (output / (key + ".stdout")).write_bytes(data)
                (output / (key + ".stderr")).write_bytes(stderr)
                hashes[key] = hashlib.sha256(data).hexdigest()
                locks = re.findall(rb"(\d+) lock=(\d+) unlock=(\d+)", stderr)
                assert [int(x[0]) for x in locks] == cases and all(x[1] == x[2] for x in locks)
                results[snapshot, mode] = reports
        for mode in (0, 1):
            differences = [c for c, old, new in zip(cases, results[0, mode], results[1, mode]) if old != new]
            assert not differences, (combo, mode, "static-offset TA/state changed", differences)
        differences = [c for c, old, new in zip(cases, results[0, 3], results[1, 2]) if old != new]
        assert not differences, (combo, "dynamic TA/state differs from immediate owner oracle", differences)
        exposed = [c for c, old, new in zip(cases, results[0, 2], results[0, 3])
                   if old.splitlines()[1] != new.splitlines()[1]]
        assert 100 in exposed, (combo, "negative control did not expose stale queued UV")
        rows.append(dict(select=select, submit_batch=batch, replay_lean=replay,
            static_comparisons=len(cases)*2, dynamic_oracle_comparisons=len(cases),
            negative_control_ta_differences=exposed, exact_ta_and_state=True))
    files = [reference.original.STATIC, reference.original.SOURCE,
             reference.HERE / "fixture_boundary.cpp.in", reference.HERE / "fixture_geometry.cpp.in"]
    report = dict(status="PASS", baseline=BASELINE, configurations=16,
        static_comparisons=66*2*8, dynamic_oracle_comparisons=66*8, process_cases=66*7*8,
        source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
        fixture_sha256=hashlib.sha256(source.encode()).hexdigest(),
        unchanged_geometry_body_sha256=identity,
        extracted_sha256={name: hashlib.sha256(value.encode()).hexdigest() for name, value in values.items()},
        combinations=rows, output_sha256=hashes, scope=__doc__)
    (output / "geometry-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "configurations", "static_comparisons", "dynamic_oracle_comparisons", "process_cases")}))


if __name__ == "__main__":
    main()
