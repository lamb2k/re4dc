#!/usr/bin/env python3
"""Exact Build 3 picks, masks, ranges and accounting over synthetic R4IM data.

The actual selector and numeric helper bodies are extracted from production;
MeshPackage::adopt validates every package. Host floating point is compared
locally in each mode. This is not a target timing or gameplay/TA capture.
"""
import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import random
import re
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
STATIC = DC / "game/platform/native_static.cpp"
SELECTOR = STATIC.parent / "include/scenery_chunk_select.inc"
BASELINE = "75229c8fa54d4a939095666036c8ee1c8f52e2fe"
KNOBS = ("SCENERY_SELECT_ONLY", "SCENERY_SUBMIT_BATCH", "SCENERY_REPLAY_LEAN",
         "ACTOR_SETUP_LEAN", "SCENERY_UV_SNAPSHOT")


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


extractor = module("select2_extract", HERE.parent / "world_submit_spike/check_runtime.py")
cases_module = module("select2_cases", HERE.parent / "world_setup_spike/selection_cases.py")


def generate(output):
    (output / "headers/kos").mkdir(parents=True)
    (output / "headers/kos/fs.h").write_text("#pragma once\nusing file_t=int;\n#define FILEHND_INVALID (-1)\n")
    raw = STATIC.read_text()
    f = extractor.function
    new_helpers=(STATIC.parent / "include/scenery_select_lean2.inc").read_text()
    values = dict(ROOM=str(DC / "room"), PICK=f(raw, "struct Pick {"),
        GROUP_VISIBLE=f((DC / "room/pvr_geometry.cpp").read_text(), "bool group_visible("),
        LEAN_NAMESPACE=f(raw, "namespace lean {").replace(
            '#include "include/scenery_select_lean2.inc"',
            new_helpers),
        SELECTOR=f(raw, "struct ScenerySelector {").replace(
            '#include "include/scenery_chunk_select.inc"', SELECTOR.read_text()))
    source = (HERE / "selection_fixture.cpp.in").read_text()
    if "box_mask_grid(" in new_helpers and "RE4DC_SCENERY_SELECT_LEAN2_BOX_TRIAL" not in new_helpers:
        source="#define FIXTURE_BOX_GRID_FINAL 1\n"+source
    for name, value in values.items():
        source = source.replace("@" + name + "@", value)
    assert not re.search(r"@[A-Z_]+@", source)
    (output / "selection.cpp").write_text(source)
    # Selection feeds these unchanged consumers. Equal ordered Pick bytes
    # therefore preserve the existing group walk and vertex-range inputs.
    baseline = subprocess.check_output(["git", "show", BASELINE + ":" + str(STATIC.relative_to(ROOT))], cwd=ROOT).decode()
    downstream = {}
    for signature in ("int emit_pick(", "const std::uint8_t* strips_lean(",
                      "int chunk_emit(", "bool borrow_gather(){", "const re4dc::room::CompactVertex12* corners("):
        before, after = f(baseline, signature), f(raw, signature)
        assert before == after, (signature, "selection consumer changed")
        downstream[signature] = hashlib.sha256(after.encode()).hexdigest()
    return values, downstream


def extended_cases():
    cases = cases_module.cases()
    rng = random.Random(0x36720261023)

    def add(name, parts, *, records=None, indexed=False, **changes):
        cfg = cases_module.defaults()
        cfg.update(changes)
        package, groups, cones = cases_module.package(parts, cfg["groups"], indexed)
        if records is not None:
            data = bytearray(groups)
            for i, value in records.items():
                struct.pack_into("<H", data, 2 * i, value)
            groups = bytes(data)
        cases.append(dict(name=name, config=cfg, package=package, groups=groups, cones=cones, expected=None))

    # A complete cluster covers both screen edges, with varied individual boxes.
    for number in (1, 2, 4, 8, 16, 32):
        for groups in (1, 2, 4, 8):
            lets = []
            for i in range(number):
                xyz = [cases_module.triangle((i*37+j*79)%601, (i*53+j*13)%401, 100)
                       for j in range(groups)]
                lets.append(cases_module.meshlet(xyz))
            add(f"partial-n{number}-g{groups}", [[[(0., lets)]]], groups=groups,
                mvq=[.1, 0, 0, -30, 0, .1, 0, -20, 0, 0, -.1, -10])
    # Duplicate records, internal empty slots, and decreasing strip ends are
    # permitted external group data even though the normal producer is ordered.
    lets = [cases_module.meshlet([cases_module.triangle(x, 50, 0)
                                 for x in (0, 100, 300, 450, 0, 100, 300, 450)])]
    for pattern in ((4,8,4,8,12,16,20,24), (0,0,4,4,8,8,12,12),
                    (4,8,12,16,12,16,20,24), (4,8,12,16,20,24,0,4),
                    (0,0,0,0,0,0,0,0), (4,4,4,4,4,4,4,4)):
        for cull in (0, 1, 2):
            add("ends-"+"-".join(map(str,pattern))+f"-c{cull}", [[[(0., lets)]]], groups=8,
                records={8*i+6: value for i,value in enumerate(pattern)}, cull=cull, cone_on=1)
    # Adjacent float32 translations at the five decision planes, including
    # signed zero, exact integer coordinates and the largest u16 bounds.
    def adjacent(value, steps):
        bits = struct.unpack("<I", struct.pack("<f", value))[0]
        return struct.unpack("<f", struct.pack("<I", bits+steps))[0]
    for axis, value in ((3,10.), (3,-30.), (7,10.), (7,-30.), (11,1.), (11,-1000.)):
        for delta in range(-8, 9):
            matrix = cases_module.defaults()["mvq"]
            matrix[axis] = adjacent(value, delta)
            add(f"ulp-a{axis}-v{value}-d{delta}", [[[(0., [cases_module.meshlet()])]]], mvq=matrix)
    for i in range(256):
        ng = (1,2,4,8)[i%4]
        nm = (1,2,4,8,16)[(i//4)%5]
        lets = []
        for _ in range(nm):
            groups = [cases_module.triangle(rng.randrange(0,700), rng.randrange(0,500), rng.randrange(0,200))
                      for _ in range(ng)]
            lets.append(cases_module.meshlet(groups))
        matrix = [rng.uniform(-.15,.15),rng.uniform(-.03,.03),rng.uniform(-.03,.03),rng.uniform(-50,30),
                  rng.uniform(-.03,.03),rng.uniform(-.15,.15),rng.uniform(-.03,.03),rng.uniform(-30,30),
                  rng.uniform(-.03,.03),rng.uniform(-.03,.03),rng.uniform(-.15,-.01),rng.uniform(-30,5)]
        if i%16==0:
            matrix[0]=matrix[5]=0.;matrix[1]=-0.;matrix[4]=0.
        add(f"seeded-{i:03d}", [[[(0., lets), (4., lets[:max(1,nm//2)])]]],
            groups=ng, mvq=matrix, cull=i%3, cone_on=i%2, indexed=bool(i%2),
            near=(.01,1.,3.,8.)[i%4], cull_far=(30.,60.,1000.)[i%3],
            lod_scale=(0.,1.,10.,100.)[i%4])
    edge = cases_module.meshlet([cases_module.triangle(0,0,0), cases_module.triangle(65527,65527,65535)])
    for sign in (-1,1):
        add(f"u16-extents-{sign}", [[[(0., [edge,edge])]]], groups=2,
            mvq=[.001*sign,0,0,-20,0,.001,0,-20,0,0,-.001,-10])
    return cases


def matrix():
    rows = []
    for bits in itertools.product((0,1), repeat=5):
        rows.append(dict(name="s%d-b%d-r%d-a%d-u%d" % bits, bits=bits,
            cone=0, sg=1, pvs=0, interior=1, quality=1, guards=(0,), helpers=not any(bits)))
    extras = [("cone",dict(cone=1)), ("sg0",dict(sg=0,helpers=True)),
              ("sg2",dict(sg=2)), ("pvs",dict(pvs=1,guards=(0,1))),
              ("interior0",dict(interior=0)), ("interior2",dict(interior=2,guards=(0,2))),
              ("interior3",dict(interior=3,guards=(0,2))),
              ("quality0",dict(quality=0)), ("quality-active",dict(guards=(4,))),
              ("all-eligibility",dict(pvs=1,guards=(1,2,4,7)))]
    for name, changes in extras:
        row=dict(name=name,bits=(1,0,1,1,1),cone=1,sg=1,pvs=0,interior=1,quality=1,guards=(0,),helpers=False)
        row.update(changes);rows.append(row)
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--quick",action="store_true",help="one public pair, all cases; exploratory only")
    parser.add_argument("--sanitize",action="store_true",help="one bounded ASan/UBSan pair")
    parser.add_argument("--define",action="append",default=[],help="additional diagnostic macro NAME=VALUE")
    args=parser.parse_args();output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    watched=[STATIC,SELECTOR,STATIC.parent/"include/scenery_select_lean2.inc",Path(__file__),HERE/"selection_fixture.cpp.in",
        HERE.parent/"world_setup_spike/selection_cases.py",HERE.parent/"world_submit_spike/check_runtime.py",
        DC/"room/instanced_mesh.hpp",DC/"room/nonempty_lod.hpp",DC/"room/pvr_geometry.cpp"]
    source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
    values,downstream=generate(output)
    (output/"cases").mkdir()
    cases=extended_cases()
    if args.sanitize:cases=cases[:160]
    records=[cases_module.write_case(c,output/"cases"/(c["name"]+".bin")) for c in cases]
    (output/"cases.json").write_text(json.dumps(records,indent=2)+"\n")
    (output/"cases.list").write_text("".join(str(output/"cases"/r["file"])+"\n" for r in records))
    rows=matrix()[:1] if args.quick or args.sanitize else matrix()
    reports=[]
    for row in rows:
        arms=[]
        for enabled in (0,1):
            label=row["name"]+f"-l{enabled}";binary=output/label
            flags=["-DRE4DC_%s=%d" % (k,v) for k,v in zip(KNOBS,row["bits"])]
            flags += [f"-DRE4DC_SCENERY_SELECT_LEAN2={enabled}",f"-DRE4DC_SCENERY_CONE={row['cone']}",
                      f"-DRE4DC_SG_SELECT_LEAN={row['sg']}",f"-DRE4DC_PS2_PVS={row['pvs']}",
                      f"-DRE4DC_PS2_INTERIOR_CULL={row['interior']}",f"-DRE4DC_QUALITY_ASSETS={row['quality']}"]
            flags += ["-D"+value for value in args.define]
            command=["g++","-std=c++20","-O2","-ffp-contract=off","-Wall","-Wextra","-Wno-unused-variable",
                "-I"+str(output/"headers"),"-iquote",str(STATIC.parent),*flags,str(output/"selection.cpp"),"-o",str(binary)]
            if args.sanitize:command[3:3]=["-fsanitize=address,undefined","-fno-omit-frame-pointer","-fno-pie","-no-pie"]
            run=subprocess.run(command,capture_output=True)
            (output/(label+".compile.log")).write_bytes(run.stdout+run.stderr)
            assert run.returncode==0,(label,run.stderr.decode())
            results={}
            tasks=[(str(output/"cases.list"),str(g)) for g in row["guards"]]
            if row["helpers"] and not args.sanitize:tasks.append(("helpers","0"))
            for task in tasks:
                env=None
                if args.sanitize:
                    import os
                    env=dict(os.environ,ASAN_OPTIONS="detect_leaks=0")
                run=subprocess.run([str(binary),*task],capture_output=True,env=env)
                if run.returncode:
                    (output/(label+".failed.stderr")).write_bytes(run.stderr)
                    raise AssertionError((label,task,run.returncode,run.stderr.decode()))
                counts={k:int(v) for k,v in re.findall(r"(\w+)=(\d+)",run.stderr.decode())}
                results[task]=(run.stdout,counts)
            arms.append(results)
        pairs=[]
        for key,(before,bc) in arms[0].items():
            after,ac=arms[1][key]
            if before!=after:
                (output/(row["name"]+".before.bin")).write_bytes(before)
                (output/(row["name"]+".after.bin")).write_bytes(after)
                raise AssertionError((row["name"],key,"selection words differ"))
            assert bc==ac,(row["name"],"accounting differs",bc,ac)
            pairs.append(dict(input="helpers" if key[0]=="helpers" else "packages",guard=int(key[1]),
                counts=bc,bytes_compared=len(before),sha256=hashlib.sha256(before).hexdigest()))
        reports.append(dict(configuration=row,comparisons=pairs))
        print("PASS",row["name"],flush=True)
    snapshot_still_current=all(hashlib.sha256(p.read_bytes()).hexdigest()==source_hashes[str(p.relative_to(ROOT))] for p in watched)
    assert snapshot_still_current,"source changed during the frozen comparison; rerun in a fresh output directory"
    report=dict(status="PASS",baseline=BASELINE,scope=__doc__,quick=args.quick,sanitized=args.sanitize,additional_defines=args.define,
        configurations=len(rows)*2,packages=len(records),combinations=reports,
        source_sha256=source_hashes,
        source_snapshot_still_current=snapshot_still_current,
        extracted_sha256={k:hashlib.sha256(v.encode()).hexdigest() for k,v in values.items() if k!="ROOM"},
        unchanged_selection_consumer_sha256=downstream,
        selection_comparisons=sum(p["counts"]["semantic"] for r in reports for p in r["comparisons"]),
        eligible_selector_comparisons=sum(p["counts"]["semantic"]-p["counts"]["guards"] for r in reports for p in r["comparisons"]),
        guard_rejection_comparisons=sum(p["counts"]["guards"] for r in reports for p in r["comparisons"]),
        helper_comparisons=sum(p["counts"]["helpers"] for r in reports for p in r["comparisons"]),
        box_comparisons=sum(p["counts"]["boxes"] for r in reports for p in r["comparisons"]))
    (output/"selection-controls.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ("status","configurations","packages","selection_comparisons","helper_comparisons","box_comparisons")}))


if __name__=="__main__":main()
