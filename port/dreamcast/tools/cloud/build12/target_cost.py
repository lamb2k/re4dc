#!/usr/bin/env python3
"""Observe real SH4 kernel opcodes/traffic, with explicit synthetic cycle scope.

This prices transform_sched+walk_lean (shared gather or local) against the
actual SDS1 direct helper including its conservative box classify/precheck.
FTRV uses only a qualified identity matrix; FSRRA only input1->result1. The
committed-word sanity check does not establish general target FP equivalence.
Perfect D-cache/no DMA/zero SQ service cost; warm/cold I-cache are reported.
No game frame, cache miss reduction, console time or FPS is measured here.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); sys.modules[name] = value
    spec.loader.exec_module(value); return value


controls = module("layout_target_build", HERE/"build_controls.py")
kernel = module("layout_qualified_fp", DC/"tools/d367/actor_bytes_lean/kernel_audit.py")
profile = controls.profile
REGIONS = {"arguments": (0x9000, 0x1000), "shared_pool": (0x20000, 0x10000),
           "local_or_gather": (0x40000, 0x4000), "sequential_inputs": (0x50000, 0x4000),
           "pool_offsets": (0x60000, 0x1000), "strips": (0x62000, 0x1000),
           "transformed_cache": (0x64000, 0x2100), "outcodes": (0x67000, 0x1000),
           "colour_lut": (0x68000, 0x1000), "constants": (0x6a000, 0x1000),
           "stack": (0x4f0000, 0x10000)}


class Arithmetic(kernel.KernelArithmetic):
    def step(self, pc, delay=False):
        opcode = self.fetch(pc)
        if opcode & 0xff00 == 0xca00:  # XOR #imm,R0; T is unchanged.
            self.reg[0] ^= opcode & 255
            self.instruction_pcs.append(pc); self.steps += 1
            return pc+2
        return super().step(pc, delay)


class Machine(kernel.Observer, Arithmetic):
    pass


def opcode_controls():
    for value, immediate in ((0, 1), (0xffffffff, 255), (0x12345678, 0), (0xabcdef00, 0x5a)):
        machine = Machine(); machine.map(0x100000, struct.pack("<H", 0xca00|immediate))
        machine.reg[0] = value; machine.t = 1
        machine.observe_start(); machine.step(0x100000); machine.observe_stop()
        assert machine.reg[0] == value^immediate and machine.t == 1 and machine.steps == 1
        assert not machine.memory_events
    return dict(status="PASS", xor_immediate_cases=4, scope="Documented integer XOR immediate only; no added FP approximation")


def build(args, out):
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    profile.SPECIFICATIONS.update(controls.UNITS)
    profile.PROFILES["cost"] = [*controls.MATCHED, "SCENERY_DIRECT_STRIPS=1"]
    flags, receipt = profile.derive(out/"profile", cxx, kos, sdk, variants=["cost"], units=["native_static"])
    builder = profile.Build(out)
    fixture = out/"fixture.cpp"
    fixture.write_text((HERE/"cost_fixture.cpp.in").read_text().replace("@DC@", str(DC)))
    obj, elf = out/"fixture.o", out/"fixture.elf"
    builder.run([*flags["cost"]["native_static"], "-c", "-fstack-usage", fixture, "-o", obj], label="fixture")
    script = out/"fixture.ld"
    script.write_text("SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }\n"
        ". = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n")
    builder.run([cxx, "-m4-single", "-ml", "-nostartfiles", "-Wl,--gc-sections", "-Wl,-T,"+str(script),
        "-Wl,-e,_fixture_cached", "-Wl,-u,_fixture_direct", "-Wl,-u,_fixture_layout", obj, "-lm", "-o", elf], label="link")
    prefix = str(cxx).removesuffix("g++")
    (out/"fixture.disassembly.txt").write_bytes(builder.run([prefix+"objdump", "-d", "-C", elf], label="disassembly"))
    return elf, dict(flags=flags["cost"]["native_static"], profile=receipt, object_sha256=profile.sha(obj),
        elf_sha256=profile.sha(elf), sections=profile.sections(elf), stack_usage=profile.stack_usage(obj.with_suffix(".su")),
        compiler_sha256=profile.sha(cxx), compiler=builder.run([cxx, "--version"], label="compiler").decode().splitlines()[0])


def prepare(elf, unique, repeats, scattered, arm, prime):
    program, symbols = kernel.target_machine.scalar.load_elf(elf)
    m = Machine()
    for address, data, _ in program:
        m.map(address, data)
    layout_at = symbols["_fixture_layout"][0]
    layout = struct.unpack("<18I", m.bytes_at(layout_at, 72))
    assert layout[:2] == (172, 88), layout
    fields = dict(zip(("pool", "local", "sequential", "offsets", "strips", "vertex_count", "strip_bytes",
                      "cache", "codes", "constants", "bounds", "matrix", "projection", "viewport", "prime", "limit"), layout[2:]))
    for address, size in REGIONS.values():
        if address != 0x4f0000:
            m.map(address, bytes(size))
    at = lambda name: REGIONS[name][0]
    records = [struct.pack("<6H", 100+i*3, 100+i, i % 3, i % 16, i % 8, 0x8000|i) for i in range(unique)]
    offsets = [(i*73) % 4096 if scattered else i for i in range(unique)]
    # Odd73 is injective modulo4096 for these bounded fixture sizes.
    assert len(set(offsets)) == unique
    for offset, record in zip(offsets, records):
        m.map(at("shared_pool")+12*offset, record)
    m.map(at("pool_offsets"), struct.pack("<%dH" % unique, *offsets))
    m.map(at("local_or_gather"), b"".join(records))
    # One or four ordinary strips; corners keep their exact strip-local order.
    strips = [list(range(unique)) for _ in range(repeats)]
    raw = b"".join(bytes([len(s), *s]) for s in strips)
    m.map(at("strips"), raw)
    m.map(at("sequential_inputs"), b"".join(records[k] for s in strips for k in s))
    lut = []
    for c in ([i << 8 for i in range(256)]+list(range(256))):
        r, g, b = (c >> 10)&31, (c >> 5)&31, c&31
        lut.append((0xff000000 if c&0x8000 else 0)|(((r<<3)|(r>>2))<<16)|(((g<<3)|(g>>2))<<8)|((b<<3)|(b>>2)))
    m.map(at("colour_lut"), struct.pack("<512I", *lut))
    values = (1., 0., 0., 1., 1., 0., 0., 1., .5, 10.)
    const = struct.pack("<10f3I9f", *values, 0xffffffff, 0, at("colour_lut"),
                        0., 1., 0., 1., 0., 640., 480., .5, 10.)
    m.map(at("constants"), const)
    inputs = bytearray(layout[0])
    words = dict(pool=at("shared_pool"), local=at("local_or_gather"), sequential=at("sequential_inputs"),
        offsets=at("pool_offsets") if arm == "shared" else 0, strips=at("strips"), vertex_count=unique,
        strip_bytes=len(raw), cache=at("transformed_cache"), codes=at("outcodes"), constants=at("constants"),
        prime=prime, limit=119)
    for name, value in words.items():
        struct.pack_into("<I", inputs, fields[name], value)
    floats = dict(bounds=(100., 100., 0., 100.+3*(unique-1), 100.+unique-1, 2.),
        matrix=(1., 0., 0., -320., 0., -1., 0., 240., 0., 0., 0., -1.),
        projection=(0., 1./320., 0., 1./240., 0., 0., 0.), viewport=(0., 0., 640., 480., 0., 0.))
    for name, values in floats.items():
        struct.pack_into("<%df" % len(values), inputs, fields[name], *values)
    m.map(0x9000, inputs)
    for i in range(256):
        m.map(at("transformed_cache")+32*i, struct.pack("<8I", 0xe0000000, 0, 0, 0, 0, 0, 0, 0))
    m.fp[1] = [0x3f800000 if i in (0, 5, 10, 15) else 0 for i in range(16)]
    return m, symbols, records, strips


def traffic(machine):
    report = kernel.traffic_details(machine.memory_events, machine.prefetch_events)
    grouped = {}
    for e in machine.memory_events:
        region = next((name for name, (start, size) in REGIONS.items() if start <= e[3] < start+size),
                      "store_queue" if e[3] >= 0xe0000000 else "literal_or_table")
        grouped.setdefault(region, []).append(e)
    report["regions"] = {name: kernel.summarize(events) for name, events in grouped.items()}
    report["interpretation"] = "Architectural loads/stores and unique demanded32B addresses; no external traffic or D-cache misses inferred."
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--host-cc", default="gcc")
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    paths = [Path(__file__), HERE/"cost_fixture.cpp.in", HERE/"build_controls.py",
             DC/"room/scenery_direct_strips.hpp", DC/"room/mesh_fastpath.hpp",
             DC/"room/mesh_fastpath_sched.hpp", DC/"room/mesh_strip_lean.hpp",
             DC/"tools/d367/actor_bytes_lean/kernel_audit.py",
             DC/"tools/d367/world_replay_lean/target_machine.py",
             DC/"tools/d367/world_replay_lean/sh4_machine.py",
             DC/"tools/d367/world_replay_lean/memory_trace.py",
             DC/"tools/d367/world_replay_lean/pipeline_cost.py"]
    frozen = {str(p.relative_to(ROOT)): profile.sha(p) for p in paths}
    elf, build_receipt = build(args, out)
    model = kernel.pipeline_cost.Model(out/"model", elf, args.host_cc)
    rows = []
    # Bounded frequency/reuse controls, not a claim about actual room mix.
    for unique, repeats, scattered, prime in ((8, 1, False, 1), (32, 1, True, 1),
        (64, 1, True, 0), (64, 4, True, 0), (32, 4, True, 1)):
        case = f"u{unique}-r{repeats}-s{int(scattered)}-p{prime}"
        result, golden = {}, None
        for arm in ("shared", "local", "direct"):
            m, symbols, records, strips = prepare(elf, unique, repeats, scattered, arm, prime)
            m.minimum_sp = m.reg[15]; m.observe_start()
            m.execute_kernel(symbols["_fixture_direct" if arm == "direct" else "_fixture_cached"][0], 0x9000)
            m.observe_stop()
            assert m.reg[0] == unique*repeats, (case, arm, "partial/cull path")
            actual = bytes(m.output)
            assert len(actual) == unique*repeats*32, (case, arm, len(actual))
            if golden is None:
                golden = actual
            else:
                assert golden == actual, (case, arm, "bounded actual target words")
            trace = SimpleNamespace(instruction_pcs=list(m.instruction_pcs), steps=m.steps, read=m.read)
            row = dict(instructions=m.steps, transforms=unique*repeats if arm == "direct" else unique,
                submitted_corners=unique*repeats, peak_stack_bytes=m.initial_regs[15]-m.minimum_sp,
                traffic=traffic(m), output_sha256=hashlib.sha256(actual).hexdigest())
            row.update(kernel.price_helpers.price(model, case+"-"+arm, trace))
            result[arm] = row
        rows.append(dict(name=case, unique_vertices=unique, strips=repeats, scatter=scattered,
                         cache_primed_this_call=bool(prime), arms=result))
        print("PASS", case, flush=True)
    # Explicit arithmetic scenarios: all unpriced frame work is assumed30ms.
    # A microkernel delta is not pasted into the observed49.3ms console frame.
    projection = []
    for case in rows:
        for calls in (100, 500):
            projection.append(dict(case=case["name"], assumed_calls_per_drawn_frame=calls,
                assumed_cpu_mhz=200, assumed_all_other_frame_ms=30.0,
                modelled_frame_ms={arm: 30.0+calls*row["model_cycles"]/200000.0 for arm, row in case["arms"].items()},
                modelled_cold_icache_frame_ms={arm: 30.0+calls*row["cold_icache"]["model_cycles"]/200000.0
                    for arm, row in case["arms"].items()},
                cold_policy="Pessimistically re-cold the isolated kernel before every call; no game instruction footprint."))
    assert frozen == {str(p.relative_to(ROOT)): profile.sha(p) for p in paths}, "source changed during kernel gate"
    report = dict(status="PASS", scope=__doc__, build=build_receipt, source_sha256=frozen, cases=rows,
        memory_controls=kernel.target_machine.memory_controls(), fp_controls=kernel.kernel_controls(), opcode_controls=opcode_controls(),
        model=model.metadata(), modelled_whole_frame_scenarios=projection,
        exclusions="No bind/selection/headers/locks/waits/clipping or library-internal waits; no D-cache misses/bus contention. Modelled frame scenarios assume all excluded work30ms; they do not predict49.3ms-console behavior.")
    (out/"target-cost.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(dict(status="PASS", cases=len(rows), report=str(out/"target-cost.json"))))


if __name__ == "__main__":
    main()
