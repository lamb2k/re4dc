#!/usr/bin/env python3
"""Actual SH4 certificate/caller/copy opcodes and complete target-FMAC output.

Synthetic projected inputs exclude transformation, lighting, cache/bus/PVR and
game scheduling. Context preparation, certificate, observed-cache scan, branch
dispatch and the actual actor SQ copy/fallback opcodes are all executed.
"""
import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import helper_test as host
import pipeline_cost
import sh4_machine as target

HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]


def function(source, signature):
    start = source.index(signature)
    at = source.index("{", start) + 1
    depth = 1
    while depth:
        depth += (source[at] == "{") - (source[at] == "}")
        at += 1
    return source[start:at]


def build(output, compiler, optimization, helper_optimization, avk):
    sdk = output / "sdk"
    commands = []

    def command(args):
        commands.append(args)
        p = subprocess.run(args, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (output / "build.log").open("a").write("$ " + " ".join(args) + "\n" + p.stdout)
        assert p.returncode == 0, p.stdout

    command([sys.executable, str(HERE.parent / "backface_sh4zam_fused/materialize.py"),
             "--output", str(sdk), "--receipt", str(output / "sdk-receipt.json")])
    actor = DC / "game/platform/native_actor_fast.cpp"
    copy = function(actor.read_text(), "template <bool SQ>\ninline void* emit_meshlet(")
    source_hashes = {}
    for relative in ("game/platform/backface_certificate.cpp", "room/backface_certificate.hpp", "room/backface_sh4.hpp"):
        original = DC / relative
        snapshot = output / "production" / relative
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        data = original.read_bytes()
        snapshot.write_bytes(data)
        source_hashes[str(original.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
    (output / "source-sha256.json").write_text(json.dumps(source_hashes, indent=2) + "\n")
    fixture = output / "target_fixture.cpp"
    fixture.write_text((HERE / "target_fixture.cpp.in").read_text().replace("@ACTUAL_EMIT_MESHLET@", copy))
    flags = ["-m4-single", "-ml", "-std=c++17", optimization, "-fno-fast-math", "-ffp-contract=off",
             "-ffunction-sections", "-fdata-sections", "-fno-rtti", "-fno-exceptions"]
    source = output / "production/game/platform/backface_certificate.cpp"
    command([compiler, *flags, helper_optimization, "-c", str(source), "-o", str(output / "certificate.o")])
    command([compiler, *flags, "-I" + str(output / "production/room"), "-I" + str(sdk / "include"),
             "-I" + str(HERE.parent / "backface_sh4_kernel/include"), "-DRE4DC_AVK=" + str(avk),
             "-c", str(fixture), "-o", str(output / "caller.o")])
    cc = compiler.removesuffix("g++") + "gcc"
    command([cc, "-m4-single", "-ml", "-O2", "-DSHZ_STRIP_EARLY_CLIP=1", "-c", str(sdk / "source/shz_strip.S"),
             "-o", str(output / "kernel.o")])
    command([compiler, "-m4-single", "-ml", "-nostartfiles", "-Wl,--gc-sections",
             "-Wl,-Ttext=0x100000,-e,_measure_caller", "-Wl,-u,_measure_prepare,-u,_measure_classify,-u,_measure_scan",
             "-Wl,-u,_fixture_layout,-u,_measure_eligibility,-u,_measure_strict",
             str(output / "caller.o"), str(output / "certificate.o"), str(output / "kernel.o"),
             "-lm", "-o", str(output / "caller.elf")])
    # Include the production implementation in a separate probe TU so its
    # actual private mode predicate can be executed without an unsafe C/FPU
    # ABI entry when PR/SZ are deliberately invalid. All unused math is GC'd.
    guard = output / "fpscr_guard.cpp"
    guard.write_text('#include "production/game/platform/backface_certificate.cpp"\n'
                     'extern "C" unsigned measure_mode_guard() {\n'
                     '    return re4dc::bf::certificate::arithmetic_supported();\n}\n')
    command([compiler, *flags, helper_optimization, "-nostartfiles", "-Wl,--gc-sections",
             "-Wl,-Ttext=0x100000,-e,_measure_mode_guard", str(guard), "-lm", "-o", str(output / "fpscr-guard.elf")])
    command([sys.executable, str(HERE.parent / "backface_sh4_kernel/build_oracle.py"), "--output", str(output)])
    command([compiler.removesuffix("g++") + "size", "-A", str(output / "caller.elf")])
    command([compiler.removesuffix("g++") + "size", "-A", str(output / "certificate.o")])
    (output / "build-commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    return commands, hashlib.sha256(copy.encode()).hexdigest()


def object_text_size(path):
    image = path.read_bytes()
    offset = struct.unpack_from("<I", image, 32)[0]
    size, count = struct.unpack_from("<HH", image, 46)
    sections = [struct.unpack_from("<10I", image, offset + i*size) for i in range(count)]
    return sum(section[5] for section in sections if section[2] & 4)


def mode_controls(output, program, symbols):
    guard_program, guard_symbols = target.load_elf(output / "fpscr-guard.elf")
    rows = []
    # RN/RZ are admitted by the exact predicate. This only tests the integer
    # guard for RZ; all interpreted arithmetic and cost workloads remain RN.
    values = [0, 1, 0x40000, 0x40001, 0x40002, 0x40003,
              0x40000 | 1 << 19, 0x40000 | 1 << 20,
              0x40000 | 1 << 21, 0x4007C]
    values.extend(0x40000 | 1 << bit for bit in range(7, 12))
    for fpscr in values:
        m = target.Machine(b"", bytes(96), bytes(8), 127, 1, fpscr=fpscr)
        for address, data, _ in guard_program:
            m.map(address, data)
        m.execute(guard_symbols["_measure_mode_guard"][0])
        expected = fpscr in (0x40000, 0x40001, 0x240000, 0x4007C)
        assert m.reg[0] == int(expected), hex(fpscr)
        assert not any(m.read(pc, 2) & 0xF000 == 0xF000 for pc in m.instruction_pcs)
        rows.append(dict(fpscr=fpscr, scope="production integer mode predicate only", admitted=expected, instructions=m.steps))
    fixture = next(case for case in fixtures() if case[0] == "front-grid64-294indices")
    _, matrix, cone, cache, indices, cull = fixture
    for fpscr in (0, 0x40002, 0x40080):
        for phase in ("prepare", "classify", "scan", "strict"):
            m = scenario(program, symbols, matrix, cone, cache, indices, cull)
            if phase in ("classify", "scan"):
                m.execute(symbols["_measure_prepare"][0])
            if phase == "scan":
                m.execute(symbols["_measure_classify"][0])
            m.fpscr = m.initial_fpscr = fpscr
            m.execute(symbols["_measure_" + phase][0])
            field = {"prepare": 56, "classify": 52, "scan": 48, "strict": 48}[phase]
            assert m.read(0x9000 + field, 4) == 0, (fpscr, phase)
            rows.append(dict(fpscr=fpscr, scope="actual public helper entry", phase=phase, admitted=False, instructions=m.steps))
    altered = list(matrix)
    altered[3] = 2**-149
    m = scenario(program, symbols, altered, cone, cache, indices, cull, fpscr=0)
    m.execute(symbols["_measure_eligibility"][0])
    assert not m.read(0x9034, 4)
    assert not any(m.read(pc, 2) & 0xF00F in (0xF004, 0xF005) for pc in m.instruction_pcs)
    rows.append(dict(fpscr=0, scope="actual cost admission with subnormal W coefficient", admitted=False,
                     no_floating_comparison=True, instructions=m.steps))
    return rows


def scenario(program, symbols, matrix, cone, cache, indices, cull=1, batch=1, mode=1, fpscr=0x40000):
    m = target.Machine(b"", cache, bytes(indices) + bytes(8), 127, cull, fpscr=fpscr)
    for address, data, flags in program:
        m.map(address, data)
    m.map(0xA000, struct.pack("<16f", *matrix))
    m.map(0xA100, bytes(cone))
    words = [0xA000, 0xA100, 0x2000, 0x8000, len(cache) // 32, len(indices), cull,
             batch, mode, host.original.fbits(1.0), 0xE0000000, 0, 0, 0, 0,
             sum(bool(value & 128) for value in indices)]
    layout = [m.read(symbols["_fixture_layout"][0] + 4*i, 4) for i in range(5)]
    size, context_size, proof_size, context_offset, proof_offset = layout
    assert context_offset == 64 and proof_offset == context_offset + context_size
    assert size == proof_offset + proof_size
    m.map(0x9000, struct.pack("<16I", *words) + bytes(size - 64))
    return m


def fixtures():
    for n in (3, 16, 64, 128):
        if n == 3:
            points = [(-100, -100, 0), (100, -100, 0), (-100, 100, 0)]
            cull = 1
        else:
            points = [(i // 2 * 32, -100 if i % 2 == 0 else 100, 0) for i in range(n)]
            cull = 2
        center = (max(p[0] for p in points) + min(p[0] for p in points)) / 2
        w = 8192
        matrix = host.column_matrix((320, 0, -320, 320*w-320*center),
                                    (0, 240, -240, 240*w), (0, 0, -1, w))
        indices = bytes(list(range(n - 1)) + [n - 1 | 128])
        cone = host.cone_for(points, indices)
        cache = host.projected_cache(matrix, points)
        yield "front-%d" % n, matrix, cone, cache, indices, cull
        yield "back-suggestion-%d" % n, matrix, cone, cache, indices, 3-cull
        # Actual varying reciprocals, without assuming an approximation law.
        unstable = host.projected_cache(matrix, points, inverse_bias=0.1,
                                        rng=__import__("random").Random(117))
        yield "uncertain-reciprocal-%d" % n, matrix, cone, unstable, indices, cull
    # A tessellated 8x8 grid has 98 nonoverlapping triangles reusing 64 cached
    # vertices. Separate material-compatible short strips make reuse and
    # per-strip classifier setup visible without duplicating geometry.
    points = [(32*x - 112, 32*y - 112, 0) for y in range(8) for x in range(8)]
    indices = bytearray()
    for y in range(7):
        for x in range(7):
            a = y*8+x
            indices.extend((a, a+1, (a+8) | 128, a+1, a+9, (a+8) | 128))
    indices = bytes(indices)
    matrix = host.column_matrix((320, 0, -320, 320*8192),
                                (0, 240, -240, 240*8192), (0, 0, -1, 8192))
    cone = host.cone_for(points, indices)
    yield "front-grid64-294indices", matrix, cone, host.projected_cache(matrix, points), indices, 1
    quads = bytes(value for y in range(7) for x in range(7)
                  for value in (y*8+x, y*8+x+1, y*8+x+8, (y*8+x+9) | 128))
    yield "front-grid64-196indices", matrix, host.cone_for(points, quads), host.projected_cache(matrix, points), quads, 1
    rows = bytes(value for y in range(7) for x in range(8)
                 for value in (y*8+x, ((y+1)*8+x) | (128 if x == 7 else 0)))
    # Row strips have the opposite strip winding, so retain their actual cull.
    yield "front-grid64-112indices", matrix, host.cone_for(points, rows), host.projected_cache(matrix, points), rows, 2
    # Affine/shear and perspective depth variation use the same exact geometry.
    # Acceptance is measured rather than assumed for these conservative bounds.
    off_axis = host.column_matrix((320, 40, -320, 320*8192+400000),
                                  (-32, 240, -240, 240*8192), (0, 0, -1, 8192))
    yield "off-axis-grid64", off_axis, cone, host.projected_cache(off_axis, points), indices, 1
    depth = host.column_matrix((320, 0, -320, 320*8192),
                               (0, 240, -240, 240*8192), (0.25, 0, -1, 8192))
    yield "depth-varying-grid64", depth, cone, host.projected_cache(depth, points), indices, 1
    unstable = host.projected_cache(matrix, points, inverse_bias=0.01,
                                    rng=__import__("random").Random(118))
    yield "uncertain-grid64", matrix, cone, unstable, indices, 1
    points = [(0, 0, 0), (5363, 5362, 0), (5362, 5361, 0)]
    matrix = host.column_matrix((2.5, 0, 0, 327680), (0, -1.875, 0, 245760), (0, 0, -1/128, 1024))
    indices = bytes([0, 1, 130])
    yield "fmac-sign-flip", matrix, host.cone_for(points, indices), host.projected_cache(matrix, points), indices, 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sh4-cxx", default=os.getenv("SH4_CXX", "/opt/toolchains/dc/sh-elf/bin/sh-elf-g++"))
    parser.add_argument("--optimization", choices=("-O1", "-O2"), default="-O2")
    parser.add_argument("--helper-optimization", choices=("-O1", "-O2"), default="-O2")
    parser.add_argument("--avk", type=int, choices=(0, 1), default=1)
    parser.add_argument("--no-pipeline-model", action="store_true", help="Development only: instruction counts without hwsim")
    parser.add_argument("--host-cc", default="gcc")
    parser.add_argument("--reuse-build", action="store_true", help="Development only: keep already compiled owned output")
    args = parser.parse_args()
    if args.reuse_build:
        assert args.output.is_dir()
    else:
        args.output.mkdir(parents=True, exist_ok=False)
    output = args.output.resolve()
    test_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in (HERE / "target_fixture.cpp.in", HERE / "sh4_machine.py", HERE / "pipeline_cost.py",
                             HERE / "helper_test.py", Path(__file__))}
    if args.reuse_build:
        commands = json.loads((output / "build-commands.json").read_text())
        copy_hash = "development-reuse"
    else:
        commands, copy_hash = build(output, args.sh4_cxx, args.optimization, args.helper_optimization, args.avk)
    program, symbols = target.load_elf(output / "caller.elf")
    model = None if args.no_pipeline_model else pipeline_cost.Model(output / "pipeline", output / "caller.elf", args.host_cc)
    oracle = host.original.oracle_load(output / "oracle.so")
    controls = mode_controls(output, program, symbols)
    records = []
    math_entries = {address for name, (address, _, _) in symbols.items()
                    if any(part in name for part in ("certificate7prepareE", "certificate8classifyE", "certificate15projected_frontE"))}
    assert len(math_entries) >= 3  # GCC can retain prepare's local lambda clone.
    for name, matrix, cone, cache, indices, cull in fixtures():
        admission = scenario(program, symbols, matrix, cone, cache, indices, cull)
        admission.execute(symbols["_measure_eligibility"][0])
        eligible = bool(admission.read(0x9034, 4))
        assert eligible == (name in ("front-grid64-294indices", "off-axis-grid64", "uncertain-grid64")), (name, eligible)
        if name in ("front-3", "front-64"):
            parts = scenario(program, symbols, matrix, cone, cache, indices, cull)
            phases = {}
            phase_costs = {}
            for phase in ("prepare", "classify", "scan"):
                parts.execute(symbols["_measure_" + phase][0])
                phases[phase] = parts.steps
                phase_costs[phase] = dict(instructions=parts.steps, symbols=pipeline_cost.symbol_costs(parts, symbols))
                if model:
                    phase_costs[phase]["pipeline"] = model.price(name + "-" + phase, parts)
            print("PHASE_COUNTS", json.dumps(phases), flush=True)
            records.append(dict(case=name + "-isolated-phases", instructions=phases, details=phase_costs))
        want = oracle(cache, indices, 0x17F, cull)[0]
        batches = sorted({1, min(16, 65536 // max(1, len(want)))})
        for batch in batches:
            for mode in ((0, 1, 2, 4) if batch == 1 else (0, 1, 2)):
                m = scenario(program, symbols, matrix, cone, cache, indices, cull, batch, mode)
                try:
                    got = m.execute(symbols["_measure_caller"][0])
                except AssertionError as exc:
                    raise AssertionError((name, batch, mode, str(exc), list(m.ring))) from exc
                assert got == want * batch, (name, batch, mode, len(got), len(want)*batch)
                sent, accepted, outcome, ready = (m.read(0x9000 + i*4, 4) for i in (11, 12, 13, 14))
                assert sent * 32 == len(got)
                assert m.read(0x9000 + 40, 4) == 0xE0000000 + len(got)
                assert m.written == [0, 0]
                if name.startswith("front-") and mode:
                    assert accepted == (batch if eligible or mode == 4 else 0), (name, mode, accepted, outcome)
                if mode in (1, 2) and not eligible:
                    assert not ready and not accepted
                    assert math_entries.isdisjoint(m.instruction_pcs), (name, "cost gate executed proof work")
                if name == "fmac-sign-flip" and mode:
                    assert not accepted
                row = dict(case=name, batch=batch, mode=mode, instructions=m.steps,
                           admitted=eligible, policy="ungated-diagnostic" if mode == 4 else "production",
                           accepted=accepted, outcome=outcome, sent=sent,
                           output_sha256=hashlib.sha256(got).hexdigest())
                if model:
                    row["pipeline"] = model.price("%s-batch%d-mode%d" % (name, batch, mode), m)
                records.append(row)
                print("COST", json.dumps({k: v for k, v in row.items() if k != "pipeline"} |
                                         ({"model_cycles": row["pipeline"]["model_cycles"]} if model else {}), sort_keys=True), flush=True)
    report = dict(scope=__doc__, compiler=args.sh4_cxx, optimization=args.optimization,
                  helper_optimization=args.helper_optimization, avk=args.avk, shz_strip_early_clip=1,
                  comparisons=sum("mode" in row for row in records), cases=records, commands=commands,
                  pipeline_model=model.metadata() if model else None,
                  mode_controls=controls,
                  certificate_object_text_bytes=object_text_size(output / "certificate.o"),
                  linked_fixture_text_bytes=object_text_size(output / "caller.elf"),
                  actual_copy_source_sha256=copy_hash,
                  source_sha256=json.loads((output / "source-sha256.json").read_text()) if (output / "source-sha256.json").exists() else {},
                  test_sha256=test_hashes,
                  elf_sha256=hashlib.sha256((output / "caller.elf").read_bytes()).hexdigest(),
                  fpscr=0x40000,
                  limits="Actual scalar SH4 opcodes with RN and DN=1 synthetic projected inputs; RZ arithmetic and FPU exception-status/traps are not modeled. No FTRV/FSRRA emulation, metadata decoding, matrix construction, cache/memory/PVR events, scene, hardware, wall-time or FPS claim. Mode0 is exact CPU2 fallback; modes1/2 execute production admission and certificate; mode2 adds strict check. Mode4 is explicitly ungated diagnostic.")
    (output / "target-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS target certificate, actual actor copy and exact fallback output")


if __name__ == "__main__":
    main()
