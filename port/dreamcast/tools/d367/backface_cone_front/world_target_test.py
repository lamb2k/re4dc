#!/usr/bin/env python3
"""Actual world SH4 walkers, complete packet comparisons and synthetic costs.

Triangle, quad and row strips reuse the same rotated nonplanar grids. Baseline
walk_lean_sq, an ungated certificate plus walk_lean, and walk_lean without proof
execute their compiled production opcodes. Context preparation occurs once for
one or six group draws. No transformation, cache/bus/SQ/PVR timing or game frame
is modeled. The lean-without-proof arm is a cost floor, not a safe production
policy. All inputs in the cost corpus are independently confirmed strictly front.
An additional production-admission arm checks the actual world cost predicate
and verifies that declined groups execute no certificate arithmetic.
"""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import math
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import helper_test as host
import pipeline_cost
import sh4_machine as target
from target_test import object_text_size

HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
MODES = {0: "cpu2", 1: "ungated-certificate", 2: "lean-without-proof", 3: "production-admission"}
PRODUCTION = ("game/platform/backface_certificate.cpp", "room/backface_certificate.hpp",
              "room/backface_sh4.hpp", "room/mesh_strip_lean.hpp", "room/mesh_fastpath.hpp",
              "game/platform/include/re4dc_screen.h")


def build(args, output):
    commands, identities = [], {}

    def command(words):
        commands.append(words)
        result = subprocess.run(words, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        with (output / "build.log").open("ab") as log:
            log.write(("$ " + " ".join(words) + "\n").encode() + result.stdout)
        assert result.returncode == 0, result.stdout.decode()

    # These snapshots, including the actual SDK assembler sources, make a
    # measurement independent of later edits in the shared worktree.
    source_root = (args.production_root or DC).resolve()
    for name in PRODUCTION:
        data = (source_root / name).read_bytes()
        destination = output / "production" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        identities[name] = hashlib.sha256(data).hexdigest()
    if args.sdk_root:
        sdk = output / "sdk"
        for name in ("include/sh4zam/shz_strip.h", "source/shz_strip.S",
                     "source/shz_strip_area.inc", "source/shz_strip_fused.inc"):
            destination = sdk / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            data = (args.sdk_root / name).read_bytes()
            destination.write_bytes(data)
            identities["sdk/" + name] = hashlib.sha256(data).hexdigest()
        for name in ("strip-patch-receipt.json",):
            if (args.sdk_root / name).exists():
                shutil.copy2(args.sdk_root / name, sdk / name)
    else:
        sdk = output / "sdk"
        command([sys.executable, str(HERE.parent / "backface_sh4zam_fused/materialize.py"),
                 "--output", str(sdk), "--receipt", str(output / "sdk-receipt.json")])
        for name in ("include/sh4zam/shz_strip.h", "source/shz_strip.S",
                     "source/shz_strip_area.inc", "source/shz_strip_fused.inc"):
            identities["sdk/" + name] = hashlib.sha256((sdk / name).read_bytes()).hexdigest()
    (output / "source-sha256.json").write_text(json.dumps(identities, indent=2) + "\n")
    fixture = output / "world_target_fixture.cpp"
    fixture.write_bytes((HERE / "world_target_fixture.cpp.in").read_bytes())
    flags = ["-m4-single", "-ml", "-std=c++17", args.optimization, "-fno-fast-math", "-ffp-contract=off",
             "-ffunction-sections", "-fdata-sections", "-fno-rtti", "-fno-exceptions"]
    includes = ["-I" + str(output / "production/room"), "-I" + str(sdk / "include"),
                "-I" + str(HERE.parent / "backface_sh4_kernel/include"),
                "-I" + str(output / "production/game/platform/include")]
    kos = args.kos_root.resolve()
    for directory in (kos / "include", kos / "kernel/arch/dreamcast/include", kos / "addons/include"):
        includes += ["-isystem", str(directory)]
    command([args.sh4_cxx, *flags, args.helper_optimization, "-c",
             str(output / "production/game/platform/backface_certificate.cpp"), "-o", str(output / "certificate.o")])
    command([args.sh4_cxx, *flags, *includes, "-D__DREAMCAST__", "-D_arch_dreamcast=1", "-D_arch_sub_pristine=1",
             "-c", str(fixture), "-o", str(output / "caller.o")])
    command([args.sh4_cxx.removesuffix("g++") + "gcc", "-m4-single", "-ml", "-O2", "-DSHZ_STRIP_EARLY_CLIP=1",
             "-c", str(sdk / "source/shz_strip.S"), "-o", str(output / "kernel.o")])
    command([args.sh4_cxx, "-m4-single", "-ml", "-nostartfiles", "-Wl,--gc-sections",
             "-Wl,-Ttext=0x100000,-e,_measure_caller", "-Wl,-u,_measure_prepare,-u,_measure_classify,-u,_measure_scan,-u,_measure_gated_caller",
             "-Wl,-u,_fixture_layout", str(output / "caller.o"), str(output / "certificate.o"),
             str(output / "kernel.o"), "-lm", "-o", str(output / "caller.elf")])
    command([sys.executable, str(HERE.parent / "backface_sh4_kernel/build_oracle.py"), "--output", str(output)])
    (output / "build-commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    return commands, identities


def producer_module():
    path = HERE.parent / "scenery21/scn21_build.py"
    spec = importlib.util.spec_from_file_location("world_cost_producer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cone_for(producer, points, strips):
    lo = [min(p[a] for p in points) for a in range(3)]
    hi = [max(p[a] for p in points) for a in range(3)]
    record, _ = producer.cone(strips, points, lo, hi)
    ax, ay, az, k, _ = struct.unpack("<3bBf", record)
    minimum = producer.front_normal_lower(strips, points, record)
    assert minimum > 0 and k, "synthetic front metadata must be certified by the actual producer"
    extent = [(hi[a] - lo[a]) / 2 for a in range(3)]
    center = [(hi[a] + lo[a]) / 2 for a in range(3)]
    cos, sin = producer.FRONT_ANGLES[k]
    return host.Cone((ctypes.c_float*3)(*center), sum(extent), (ctypes.c_float*3)(*extent),
                     (ctypes.c_float*3)(ax/128, ay/128, az/128), cos, sin, minimum)


def fixtures():
    producer = producer_module()
    cy, sy, cp, sp = math.cos(0.27), math.sin(0.27), math.cos(0.18), math.sin(0.18)
    view_x, view_y = (cy, 0, sy), (sp*sy, cp, -sp*cy)
    view_w = (cp*sy, -sp, -cp*cy)
    matrix = host.column_matrix(tuple(320*(view_x[i]+view_w[i]) for i in range(3)) + (320*8192,),
                                tuple(240*(view_y[i]+view_w[i]) for i in range(3)) + (240*8192,),
                                view_w + (8192,))
    matrix = host.shifted_matrix(matrix, (4096, 4096, 256))
    for n in range(3, 9):
        points = [(4096+128*x-64*(n-1), 4096+128*y-64*(n-1), 256+4*((x*x+y*y) % 5)-8)
                  for y in range(n) for x in range(n)]
        triangles = [strip for y in range(n-1) for x in range(n-1)
                     for strip in ((y*n+x, y*n+x+1, y*n+x+n),
                                   (y*n+x+1, y*n+x+n+1, y*n+x+n))]
        quads = [(y*n+x, y*n+x+1, y*n+x+n, y*n+x+n+1) for y in range(n-1) for x in range(n-1)]
        rows = [tuple(value for x in range(n) for value in (y*n+x, (y+1)*n+x)) for y in range(n-1)]
        for layout, strips, cull in (("triangles", triangles, 1), ("quads", quads, 1), ("rows", rows, 2)):
            yield make_case(producer, "%dx%d-%s" % (n, n, layout), n, layout, matrix, points, strips, cull)
        if n == 8:
            # A distinct packet control proves that bit7 remains an index bit.
            high_points = [points[0]] * 192 + points
            high_strips = [tuple(i+192 for i in strip) for strip in triangles]
            yield make_case(producer, "8x8-indices192-through255", n, "high-index-control",
                            matrix, high_points, high_strips, 1)


def make_case(producer, name, side, layout, matrix, points, strips, cull):
    cache = bytearray(host.projected_cache(matrix, points))
    for i in range(len(points)):
        struct.pack_into("<I", cache, 32*i, 0xe0000000)
    depth = [math.fsum(matrix[4*a+3]*(*p, 1)[a] for a in range(4)) for p in points]
    cone = cone_for(producer, points, strips)
    assert min(depth) > 1 and max(depth) > min(depth) and all(e > 0 for e in cone.extent)
    return dict(name=name, side=side, layout=layout, matrix=matrix, points=points, strips=strips,
                cull=cull, cache=bytes(cache), cone=cone, depth_range=[min(depth), max(depth)])


def scenario(program, symbols, case, batch=1, mode=1):
    stream = bytes(value for strip in case["strips"] for value in (len(strip), *strip))
    n = len(case["points"])
    machine = target.Machine(b"", case["cache"], stream+bytes(8), 255, case["cull"], fpscr=0x40000)
    for address, data, _ in program:
        machine.map(address, data)
    machine.map(0xA000, struct.pack("<16f", *case["matrix"]))
    machine.map(0xA100, bytes(case["cone"]))
    machine.map(0xA400, bytes(n))
    machine.map(0xB000, b"".join(struct.pack("<6H", *point, 11+i, 21+i, 0x8000+i)
                                for i, point in enumerate(case["points"])))
    size, context_size, proof_size, context_offset, proof_offset = [machine.read(symbols["_fixture_layout"][0]+4*i, 4)
                                                                 for i in range(5)]
    assert context_offset == 108 and proof_offset == context_offset+context_size and size == proof_offset+proof_size
    words = [0xA000, 0xA100, 0x2000, 0x8000, 0xA400, n, len(stream), sum(map(len, case["strips"])),
             len(case["strips"]), case["cull"], batch, mode, host.original.fbits(1), 0xe0000000,
             0, 0, 0, 0, 0, 0, 0, 119, 0xB000, 12, 0, 0, 1]
    machine.map(0x9000, struct.pack("<27I", *words)+bytes(size-108))
    return machine


def plain_packet(cache, strips):
    output = bytearray()
    for strip in strips:
        for j, index in enumerate(strip):
            vertex = bytearray(cache[32*index:32*(index+1)])
            if j+1 == len(strip):
                struct.pack_into("<I", vertex, 0, 0xf0000000)
            output += vertex
    return bytes(output)


def assert_strict_front(cache, strips, cull):
    # Complete packet equality alone is insufficient: the fine classifier can
    # retain short internal back runs. Check each determinant independently in
    # the exact FSUB/FMUL/FMAC order before using the no-proof cost floor.
    f32, fmaf = host.original.f32, host.original._fmaf
    for strip in strips:
        for j in range(len(strip)-2):
            a, b, c = (struct.unpack_from("<2f", cache, 32*strip[k]+4) for k in (j, j+1, j+2))
            dx, dy = f32(b[0]-a[0]), f32(c[1]-a[1])
            second = f32(f32(b[1]-a[1])*f32(c[0]-a[0]))
            area = float(fmaf(dx, dy, -second))
            if j & 1:
                area = -area
            assert area > 0 if cull == 1 else area < 0, (strip, j, area, cull)


def summaries(records):
    grouped = {}
    for row in records:
        if row["layout"] == "high-index-control":
            continue
        grouped.setdefault((row["case"], row["batch"]), {})[row["mode"]] = row
    comparisons = []
    for (name, batch), modes in grouped.items():
        metric = "model_cycles" if "pipeline" in modes[0] else "instructions"
        def cost(row):
            return row["pipeline"][metric] if metric == "model_cycles" else row[metric]
        base, certificate, floor = (cost(modes[i]) for i in (0, 1, 2))
        comparisons.append(dict(case=name, layout=modes[0]["layout"], side=modes[0]["side"], batch=batch,
                                metric=metric, baseline=base, certificate=certificate, lean_floor=floor,
                                proof_overhead=certificate-floor, maximum_facing_saving=base-floor,
                                net_saving=base-certificate, baseline_over_certificate=base/certificate,
                                cost_reduction_fraction=(base-certificate)/base,
                                accepted=modes[1]["accepted"]))
    return comparisons


def linear_fit(features, values, labels):
    # Small full-rank least squares, using only the Python standard library.
    # These descriptive fits are deliberately not used as admission policy.
    n = len(labels)
    system = [[sum(row[i]*row[j] for row in features) for j in range(n)] +
              [sum(row[i]*value for row, value in zip(features, values))] for i in range(n)]
    for column in range(n):
        pivot = max(range(column, n), key=lambda row: abs(system[row][column]))
        system[column], system[pivot] = system[pivot], system[column]
        scale = system[column][column]
        assert abs(scale) > 1e-9, "rank-deficient descriptive cost model"
        system[column] = [value/scale for value in system[column]]
        for row in range(n):
            if row == column:
                continue
            scale = system[row][column]
            system[row] = [a-scale*b for a, b in zip(system[row], system[column])]
    coefficients = [system[i][-1] for i in range(n)]
    errors = [value-sum(a*b for a, b in zip(row, coefficients)) for row, value in zip(features, values)]
    return dict(coefficients=dict(zip(labels, coefficients)), samples=len(values),
                max_absolute_error=max(map(abs, errors)), rms_error=math.sqrt(sum(e*e for e in errors)/len(errors)))


def validated_fit(features, values, labels, sides):
    result = linear_fit(features, values, labels)
    errors, folds = [], []
    for side in sorted(set(sides)):
        train = [i for i, value in enumerate(sides) if value != side]
        test = [i for i, value in enumerate(sides) if value == side]
        fit = linear_fit([features[i] for i in train], [values[i] for i in train], labels)
        coefficients = [fit["coefficients"][label] for label in labels]
        residuals = [values[i]-sum(a*b for a, b in zip(features[i], coefficients)) for i in test]
        errors.extend(residuals)
        folds.append(dict(held_out_grid_side=side, test_cases=len(test), max_absolute_error=max(map(abs, residuals))))
    result["leave_one_grid_size_out"] = dict(folds=folds, max_absolute_error=max(map(abs, errors)),
                                              rms_error=math.sqrt(sum(e*e for e in errors)/len(errors)))
    return result


def cost_models(records):
    models = []
    for batch in (1, 6):
        corpus = [row for row in records if row["batch"] == batch and row["layout"] != "high-index-control"]
        metric = "model_cycles" if "pipeline" in corpus[0] else "instructions"
        def cost(row):
            return (row["pipeline"][metric] if metric == "model_cycles" else row[metric])/batch
        # Preserve the original accepted-only diagnostic fits. Production
        # admission is a piecewise selection policy, not another linear arm.
        for mode in (0, 1, 2):
            rows = [row for row in corpus if row["mode"] == mode]
            fit = validated_fit([[1, row["vertices"], row["indices"], row["strips"]] for row in rows],
                                [cost(row) for row in rows], ["constant", "vertices", "indices", "strips"],
                                [row["side"] for row in rows])
            models.append(dict(batch=batch, policy=MODES[mode], metric=metric+" per group", **fit))
        floors = {row["case"]: row for row in corpus if row["mode"] == 2}
        for mode, label in ((0, "cpu2 minus lean floor"), (1, "certificate minus lean floor")):
            rows = [row for row in corpus if row["mode"] == mode]
            values = [cost(row)-cost(floors[row["case"]]) for row in rows]
            fit = validated_fit([[1, row["vertices"], row["indices"], row["strips"]] for row in rows], values,
                                ["constant", "vertices", "indices", "strips"], [row["side"] for row in rows])
            models.append(dict(batch=batch, policy=label, metric=metric+" per group", **fit))
            if mode == 1:
                fit = validated_fit([[1, row["vertices"]] for row in rows], values,
                                    ["constant", "vertices"], [row["side"] for row in rows])
                models.append(dict(batch=batch, policy=label+" (vertex-only fit)", metric=metric+" per group", **fit))
    return dict(fits=models, domain="9 to 64 vertices; 3x3 through 8x8 nonplanar grids; triangle, quad and row strips; all proofs accepted. High-index compatibility control excluded.",
                interpretation="Descriptive least-squares models with observed residuals, not guarantees or production thresholds. Rejected proofs still pay proof work and then the baseline classifier; this accepted-only cost corpus does not model their frequency.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sh4-cxx", default=os.getenv("SH4_CXX", "/opt/toolchains/dc/sh-elf/bin/sh-elf-g++"))
    parser.add_argument("--kos-root", type=Path, required=True)
    parser.add_argument("--sdk-root", type=Path, help="Existing materialized SDK; copy its exact strip sources")
    parser.add_argument("--production-root", type=Path, help="Frozen production snapshot (otherwise snapshot the current Dreamcast tree)")
    parser.add_argument("--optimization", choices=("-O1", "-O2"), default="-O2")
    parser.add_argument("--helper-optimization", choices=("-O1", "-O2"), default="-O2")
    parser.add_argument("--no-pipeline-model", action="store_true")
    parser.add_argument("--host-cc", default="gcc")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output.resolve()
    commands, identities = build(args, output)
    program, symbols = target.load_elf(output / "caller.elf")
    oracle = host.original.oracle_load(output / "oracle.so")
    model = None if args.no_pipeline_model else pipeline_cost.Model(output / "pipeline", output / "caller.elf", args.host_cc)
    records, phases = [], []
    for case in fixtures():
        assert_strict_front(case["cache"], case["strips"], case["cull"])
        want = b"".join(oracle(case["cache"], bytes(strip), 255, case["cull"])[0] for strip in case["strips"])
        assert want == plain_packet(case["cache"], case["strips"]), (case["name"], "not strictly front")
        part = scenario(program, symbols, case)
        phase_row = dict(case=case["name"], vertices=len(case["points"]), phases={})
        for phase in ("prepare", "classify", "scan"):
            part.execute(symbols["_measure_"+phase][0])
            detail = dict(instructions=part.steps, symbols=pipeline_cost.symbol_costs(part, symbols))
            if model:
                detail["pipeline"] = model.price(case["name"]+"-"+phase, part)
            phase_row["phases"][phase] = detail
        assert part.read(0x9000+20*4, 4) == 1 and part.read(0x9000+19*4, 4) == 2
        assert part.read(0x9000+18*4, 4) == 1, (case["name"], "fixture certificate declined")
        phases.append(phase_row)
        for batch in (1, 6):
            assert len(want)*batch <= 65536
            for mode in MODES:
                machine = scenario(program, symbols, case, batch, mode)
                entry = "_measure_gated_caller" if mode == 3 else "_measure_caller"
                got = machine.execute(symbols[entry][0])
                assert got == want*batch, (case["name"], batch, mode, len(got), len(want))
                assert machine.read(0x9000+13*4, 4) == 0xe0000000+len(got) and machine.written == [0, 0]
                cursor, culled, emitted, triangles, accepted = (machine.read(0x9000+4*i, 4) for i in range(14, 19))
                assert cursor == 0x8000+sum(len(s)+1 for s in case["strips"])
                assert not culled and emitted == len(case["strips"])*batch
                assert triangles == sum(len(s)-2 for s in case["strips"])*batch
                # Independent expected selections for the qualified grids;
                # do not duplicate the production score formula as the oracle.
                admitted = ((case["layout"] == "triangles" and case["side"] >= 6) or
                            (case["layout"] == "quads" and case["side"] == 8))
                expected = mode in (1, 2) or (mode == 3 and admitted)
                assert accepted == (batch if expected else 0), (case["name"], mode, accepted, expected)
                row = dict(case=case["name"], side=case["side"], layout=case["layout"],
                           vertices=len(case["points"]), indices=sum(map(len, case["strips"])),
                           strips=len(case["strips"]), triangles=sum(len(s)-2 for s in case["strips"]),
                           depth_range=case["depth_range"], batch=batch, mode=mode, policy=MODES[mode],
                           accepted=accepted, instructions=machine.steps, packet_sha256=hashlib.sha256(got).hexdigest())
                if mode == 3:
                    symbol_costs = pipeline_cost.symbol_costs(machine, symbols)
                    proof_work = {phase: sum(count for name, count in symbol_costs.items() if pattern in name)
                                  for phase, pattern in (("prepare", "11certificate7prepare"),
                                                         ("classify", "11certificate8classify"),
                                                         ("scan", "11certificate15projected_front"))}
                    assert all(bool(count) == admitted for count in proof_work.values()), (case["name"], proof_work)
                    assert machine.read(0x9000+20*4, 4) == int(admitted)
                    assert machine.read(0x9000+19*4, 4) == (2 if admitted else 0)
                    row.update(admitted=admitted, proof_instructions=proof_work)
                if model:
                    row["pipeline"] = model.price("%s-b%d-m%d" % (case["name"], batch, mode), machine)
                records.append(row)
                print("WORLD_COST", json.dumps({k: v for k, v in row.items() if k != "pipeline"} |
                      ({"model_cycles": row["pipeline"]["model_cycles"]} if model else {})), flush=True)
    report = dict(scope=__doc__, cases=records, phases=phases, comparisons=summaries(records), cost_models=cost_models(records), commands=commands,
                  source_sha256=identities, elf_sha256=hashlib.sha256((output / "caller.elf").read_bytes()).hexdigest(),
                  certificate_object_text_bytes=object_text_size(output / "certificate.o"),
                  linked_fixture_text_bytes=object_text_size(output / "caller.elf"),
                  test_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (Path(__file__), HERE / "world_target_fixture.cpp.in", HERE / "helper_test.py",
                                         HERE / "sh4_machine.py", HERE / "pipeline_cost.py",
                                         HERE.parent / "scenery21/scn21_build.py")},
                  pipeline_model=model.metadata() if model else None,
                  limits="Actual SH4 scalar/copy/classifier opcodes on synthetic projected caches, RN/DN=1. No FTRV/FSRRA execution, metadata/caller setup, cache/memory/PVR timing, hardware, wall time or frame speedup. Batch6 amortizes preparation across six repeated groups; classification and scan remain per group. All packet words are compared. Mode1 deliberately ignores the production cost gate; mode2 omits the proof and is only a lower bound; mode3 executes the world cost gate, with zero proof instructions required for every declined group. Descriptive fits use modes0/1/2 only.")
    (output / "world-target-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS world SH4 walkers and certificates: %d complete packet comparisons" % len(records))


if __name__ == "__main__":
    main()
