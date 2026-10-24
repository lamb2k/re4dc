#!/usr/bin/env python3
"""Compile and price real WORLD_CENSUS24 hot code with synthetic callers.

The production census TU is separate and unchanged, uses its Dreamcast path,
and reads the real thd_current global. Clock/identity/log/formatting are explicit
test edges. Edge bodies are excluded from cost and traffic; call-site setup is
retained. Real timer/MMIO, interrupt delivery, IRQ contention, thread switching,
logging/formatting, D-cache misses, SQ, DMA and renderer work are not priced.
Warm/cold-I cycles are model estimates for this synthetic code layout, not
console timing, captured r101 hook counts or a promised frame-rate gain.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import struct
import subprocess
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
SOURCE = DC / "game/world_census24.cpp"
HEADER = DC / "game/platform/include/world_census24.h"
FIXTURE = HERE / "fixtures/target_cost.cpp"
REPLAY = HERE.parent / "world_replay_lean"
sys.path.insert(0, str(REPLAY))
import target_machine
import pipeline_cost
from memory_trace import summarize


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


profiles = module("wc24_cost_profiles", HERE.parent / "actor_bytes_lean/build_profile.py")
pricing = module("wc24_replay_price", REPLAY / "target_run.py")
known_scalar = module("wc24_known_scalar", HERE.parent / "actor_bytes_lean/target_run.py")
sha = profiles.sha
LAYOUT = ("version", "size", "paths", "phases", "counter_count", "ticks", "drawn",
          "errors", "wall_us", "phase_us", "counters", "residual_us", "wait_us")
COUNTERS = ("transformed", "corners", "headers", "material_changes", "picked_indexed",
            "picked_plain", "picked_empty", "strip_inputs")
STUBS = ("__dreamcast_get_ticks", "re4dc_wc24_identity", "re4dc_log", "snprintf")
ROOTS = ("fixture_layout", "fixture_summary_entry", "fixture_prepare", "fixture_open_outer",
         "fixture_close_outer", "fixture_path_pair", "fixture_phase_pair", "fixture_wait_pair",
         "fixture_phase_switch", "fixture_count", "fixture_header", "fixture_normal_tick",
         "fixture_frame", "fixture_capture", "fixture_clock", "fixture_clock_step",
         "fixture_words", "fixture_snapshot")


def derive(output, compiler, kos, sdk):
    output.mkdir()
    assignments, recipe = profiles.recipe_inputs(output)
    overlay, patch = profiles.helpers.pvr_overlay(output, kos)
    overrides = ["WORLD_CENSUS24=1", "WORLD_CENSUS24_WINDOW=300", "QA_MENU=1",
                 "DBG_WARP=1", "WARP_AFTER_RESET=1", "BENCHMARK=0",
                 "PS2_WORLD_DRAW=1", "PS2_WORLD_MESH=1", "PVR_STREAM=1",
                 "MESH_DIRECT=1", "TA_DIRECT=1"]
    command = ["make", "--no-print-directory", "-n", str(output / "obj/world_census24.o"),
               *assignments, *overrides,
               "KOS_CFLAGS=" + shlex.join(profiles.target_flags(kos)),
               "KOS_BASE=" + str(kos),
               "KOS_LDFLAGS=-T" + str(kos / "utils/ldscripts/shlelf.xc"),
               "SH4ZAM_DIR=" + str(sdk),
               "--assume-old=" + str(output / "obj/modules.mk")]
    flags, receipt = profiles.helpers.expand(output, compiler, sdk, overlay,
        dict(command=command), "census", "world_census24.o", "world_census24.cpp")
    receipt.update(recipe_inputs=recipe, pvr_header_overlay=patch, overrides=overrides)
    (output / "census-profile.json").write_text(json.dumps(receipt, indent=2) + "\n")
    assert not any("WORLD_CENSUS24_HOST" in arg for arg in flags)
    return flags, receipt


def build(args, output):
    builder = profiles.Build(output)
    compiler, kos, sdk = (p.resolve() for p in (args.sh4_cxx, args.kos_root, args.sdk_root))
    version = builder.run([compiler, "-v"], label="compiler-version").decode()
    prefix = str(compiler).removesuffix("g++")
    ld_version = builder.run([prefix + "ld", "--version"], label="linker-version").decode()
    kos_sha = builder.run(["git", "-C", kos, "rev-parse", "HEAD"], label="kos-pin").decode().strip()
    pinned = ("gcc version 15.2.0" in version and "Thread model: kos" in version
              and "2.45.1" in ld_version
              and kos_sha == "804b3195ebd1a06a27cc2b3a5eacf7a2429040a3")
    if not args.allow_version_mismatch:
        assert pinned, "Acceptance requires pinned GCC 15.2/KOS-thread/binutils/KOS source"
    flags, profile = derive(output / "profile", compiler, kos, sdk)
    source_bytes, header_bytes, fixture_bytes = SOURCE.read_bytes(), HEADER.read_bytes(), FIXTURE.read_bytes()
    objects = {}
    for name, source in (("production", SOURCE), ("fixture", FIXTURE)):
        obj = output / (name + ".o")
        extra = ["-iquote", str(SOURCE.parent)] if name == "fixture" else []
        builder.run([*flags, *extra, "-fstack-usage", "-c", source, "-o", obj], label=name)
        objects[name] = dict(path=str(obj), sha256=sha(obj), **profiles.sections(obj),
                             stack_usage=profiles.stack_usage(obj.with_suffix(".su")))
    script = output / "fixture.ld"
    # Same synthetic RAM layout as the established setup/replay/actor fixtures.
    script.write_text('''SECTIONS {
 /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }
 . = 0x100000;
 .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) }
}
''')
    elf = output / "census.elf"
    builder.run([compiler, "-m4-single", "-ml", "-nostartfiles", "-Wl,--gc-sections",
        "-Wl,-T," + str(script), "-Wl,-e,_fixture_frame",
        *("-Wl,-u,_" + root for root in ROOTS),
        output / "production.o", output / "fixture.o", "-lm", "-o", elf], label="link")
    (output / "census.disassembly.txt").write_bytes(builder.run(
        [prefix + "objdump", "-d", "-C", elf], label="disassembly"))
    (output / "census.symbols.txt").write_bytes(builder.run(
        [prefix + "nm", "-n", "-C", elf], label="symbols"))
    assert SOURCE.read_bytes() == source_bytes and HEADER.read_bytes() == header_bytes
    assert FIXTURE.read_bytes() == fixture_bytes
    receipt = dict(pinned_toolchain=pinned, compiler_version=version, linker_version=ld_version,
        kos_sha=kos_sha, elf=str(elf), elf_sha256=sha(elf), objects=objects, profile=profile,
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in (SOURCE, HEADER, FIXTURE, Path(__file__))},
        separate_unmodified_production_object=True, host_adapter_macro=False)
    (output / "target-cost-build.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return elf, receipt


class Machine(known_scalar.Machine):
    def __init__(self):
        super().__init__()
        self.measuring = False
        self.format_entries = set()
        self.edge_entries = {}
        self.unpriced = {}

    def word(self, address, size=4):
        return int.from_bytes(self.bytes_at(address, size), "little")

    def put(self, address, value, size=4):
        self.map(address, int(value).to_bytes(size, "little"))

    def attach(self, symbols):
        self.symbols = symbols
        self.measuring = False
        self.edge_calls = {}
        self.unpriced = {name: (symbols["_" + name][0], symbols["_" + name][1])
                         for name in STUBS if "_" + name in symbols}
        assert all(size for _, size in self.unpriced.values())
        self.edge_entries = {address: name for name, (address, _) in self.unpriced.items()}
        # Summary and its possible compiler clones are only skipped during
        # untimed window sealing. The state/counter copies preceding them run.
        self.format_entries = {address for name, (address, _, info) in symbols.items()
            if (info & 15) == 2 and ("summary" in name and "fixture" not in name
                                  or "divdi3" in name)}
        self.format_entries.add(self.word(symbols["_fixture_summary_entry"][0]))
        layout_address = symbols["_fixture_layout"][0]
        self.layout = dict(zip(LAYOUT, (self.word(layout_address + i * 4) for i in range(len(LAYOUT)))))
        assert [self.layout[k] for k in ("version", "paths", "phases", "counter_count")] == [1, 6, 6, 8]

    def step(self, pc, delay=False):
        if pc in self.format_entries:
            assert not self.measuring, "Formatting/window seal entered a priced region"
            self.reg[0] = self.reg[1] = 0
            return self.pr
        if self.measuring and pc in self.edge_entries:
            name = self.edge_entries[pc]
            self.edge_calls[name] = self.edge_calls.get(name, 0) + 1
        opcode = self.fetch(pc)
        if opcode & 0xf00f == 0x300d:  # DMULS.L Rm,Rn; MACH:MACL, T unchanged.
            n, m = (opcode >> 8) & 15, (opcode >> 4) & 15
            product = (target_machine.scalar.base.signed(self.reg[n]) *
                       target_machine.scalar.base.signed(self.reg[m])) & ((1 << 64) - 1)
            self.mach, self.macl = product >> 32, product & 0xffffffff
            self.instruction_pcs.append(pc)
            self.steps += 1
            self.minimum_sp = min(self.minimum_sp, self.reg[15])
            return pc + 2
        if opcode & 0xf00f == 0x400c:  # SHAD Rm,Rn; signed variable right shift.
            n, m = (opcode >> 8) & 15, (opcode >> 4) & 15
            amount, value = self.reg[m], self.reg[n]
            if amount & 0x80000000:
                shift = 32 - (amount & 31)
                value = target_machine.scalar.base.signed(value) >> shift
            else:
                value <<= amount & 31
            self.reg[n] = value & 0xffffffff
            self.instruction_pcs.append(pc)
            self.steps += 1
            self.minimum_sp = min(self.minimum_sp, self.reg[15])
            return pc + 2
        return super().step(pc, delay)

    def priced_pc(self, pc):
        return not any(start <= pc < start + size for start, size in self.unpriced.values())

    def call(self, name, argument=0):
        self.execute(self.symbols["_" + name][0], argument)


def load(path):
    segments, symbols = target_machine.scalar.load_elf(path)
    machine = Machine()
    for address, data, _ in segments:
        machine.map(address, data)
    machine.attach(symbols)
    return machine


def opcode_controls():
    """Qualify the scalar opcodes used by the pinned KOS clock conversion.

    Renesas' common DMULS.L instruction definition specifies signed 32x32->64,
    MACH:MACL and unchanged T; SHAD performs a signed variable right shift.
    hwsim already decodes/prices both; only the architectural interpreter lacked
    them. No timing constants are added.
    """
    values = (0, 1, -1, 2, -2, 0x7fffffff, -0x80000000, 0x12345678)
    cases = 0
    for a in values:
        for b in values:
            for t in (0, 1):
                machine = Machine()
                machine.map(0x100000, struct.pack("<3H", 0x327d, 0x040a, 0x051a))
                machine.reg[2], machine.reg[7], machine.t = a & 0xffffffff, b & 0xffffffff, t
                before = list(machine.reg)
                machine.observe_start()
                pc = 0x100000
                for _ in range(3): pc = machine.step(pc)
                machine.observe_stop()
                expected_product = (a * b) % (1 << 64)
                assert (machine.reg[4] << 32) | machine.reg[5] == expected_product
                assert machine.t == t and machine.reg[2] == before[2] and machine.reg[7] == before[7]
                assert machine.steps == len(machine.instruction_pcs) == 3 and not machine.memory_events
                cases += 1
    for a in values:
        machine = Machine()
        machine.map(0x100000, struct.pack("<H", 0x322d))
        machine.reg[2] = a & 0xffffffff
        machine.step(0x100000)
        assert (machine.mach << 32) | machine.macl == a * a
        cases += 1
    multiply_cases = cases
    shifts = (0, 1, 31, 32, 33, 0x7fffffff, -0x80000000, -1, -2, -31, -32, -33, -63, -64)
    for value in values:
        for amount in shifts:
            for t in (0, 1):
                machine = Machine()
                machine.map(0x100000, struct.pack("<H", 0x427c))
                machine.reg[2], machine.reg[7], machine.t = value & 0xffffffff, amount & 0xffffffff, t
                machine.observe_start(); machine.step(0x100000); machine.observe_stop()
                if amount >= 0:
                    expected_value = (value << (amount % 32)) & 0xffffffff
                else:
                    width = (-amount) % 32 or 32
                    expected_value = (value // (1 << width)) & 0xffffffff
                assert machine.reg[2] == expected_value and machine.reg[7] == amount & 0xffffffff
                assert machine.t == t and machine.steps == 1 and not machine.memory_events
                cases += 1
    for value in values:
        machine = Machine()
        machine.map(0x100000, struct.pack("<H", 0x422c))
        machine.reg[2] = value & 0xffffffff
        machine.step(0x100000)
        shift = value % 32 if value >= 0 else ((-value) % 32 or 32)
        expected_value = value << shift if value >= 0 else value // (1 << shift)
        assert machine.reg[2] == expected_value & 0xffffffff
        cases += 1
    return dict(status="PASS", cases=cases, signed_multiply_cases=multiply_cases,
        arithmetic_shift_cases=cases - multiply_cases,
        scope="DMULS.L and SHAD signed/extreme values, operand alias, T and data-traffic controls; existing hwsim timing unchanged",
        instruction_reference="https://www.renesas.com/en/document/mas/sh-4a-extended-functions-software-manual",
        reference_scope="Common instruction semantics only; SH4A timing is not used")


def snapshot(machine):
    machine.call("fixture_capture")
    assert machine.reg[0] == 1, "Fixture failed to seal a complete window"
    at, layout = machine.symbols["_fixture_snapshot"][0], machine.layout
    raw = machine.bytes_at(at, layout["size"])
    counters = [list(struct.unpack_from("<8Q", raw, layout["counters"] + p * 8 * 8)) for p in range(6)]
    phases = [list(struct.unpack_from("<6Q", raw, layout["phase_us"] + p * 6 * 8)) for p in range(6)]
    waits = list(struct.unpack_from("<3Q", raw, layout["wait_us"]))
    wall = struct.unpack_from("<Q", raw, layout["wall_us"])[0]
    residual = struct.unpack_from("<q", raw, layout["residual_us"])[0]
    assert machine.word(at + layout["ticks"]) == machine.word(at + layout["drawn"]) == 300
    assert machine.word(at + layout["errors"]) == 0
    assert sum(map(sum, phases)) + sum(waits) + residual == wall
    assert all(not any(row) for row in counters[1:])
    return dict(near_op_counters=dict(zip(COUNTERS, counters[0])), phase_us=phases,
                wait_us=waits, wall_us=wall, residual_us=residual,
                snapshot_sha256=hashlib.sha256(raw).hexdigest(), ticks=300, drawn=300, errors=0)


def timed(machine, entry, argument=0):
    machine.put(machine.symbols["_fixture_clock_step"][0], 2, 8)
    machine.edge_calls = {}
    machine.minimum_sp = machine.reg[15]
    machine.observe_start()
    machine.measuring = True
    machine.call(entry, argument)
    machine.measuring = False
    raw_traffic = machine.observe_stop()
    all_pcs = list(machine.instruction_pcs)
    pcs = [pc for pc in all_pcs if machine.priced_pc(pc)]
    events = [e for e in machine.memory_events if machine.priced_pc(e[1])]
    excluded = [e for e in machine.memory_events if not machine.priced_pc(e[1])]
    prefetches = [e for e in machine.prefetch_events if machine.priced_pc(e[1])]
    trace = SimpleNamespace(instruction_pcs=pcs, steps=len(pcs), read=machine.read)
    visits = sum(len({a >> 5 for a in range(e[3], e[3] + e[4])}) for e in events)
    result = dict(instructions=len(pcs), raw_instructions=len(all_pcs),
        excluded_edge_instructions=len(all_pcs) - len(pcs),
        traffic=summarize(events, prefetches), excluded_edge_traffic=summarize(excluded),
        raw_traffic=raw_traffic, architectural_32byte_line_visits=visits,
        unpriced_edge_calls=dict(machine.edge_calls),
        peak_stack_bytes_including_test_edges=machine.initial_regs[15] - machine.minimum_sp,
        symbol_instructions=pipeline_cost.symbol_costs(trace, machine.symbols))
    machine.put(machine.symbols["_fixture_clock_step"][0], 0, 8)
    return result, trace


def expected(case, pieces=0):
    result = dict.fromkeys(COUNTERS, 0)
    if case == "count-active": result["corners"] = 32
    if case.startswith("header-") and case != "header-inactive":
        result["headers"] = 1 if case == "header-first" else 2
        result["material_changes"] = 2 if case == "header-changed" else 1
    if case == "synthetic-frame":
        for key in ("transformed", "corners", "strip_inputs"): result[key] = pieces * 32
        result["picked_indexed"] = result["headers"] = pieces
        result["material_changes"] = int(pieces > 0)
    return result


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    elf, build_receipt = build(args, output)
    model = pipeline_cost.Model(output / "model", elf, args.host_cc)
    baseline = load(elf)
    baseline.call("fixture_prepare", 0)
    rows = []
    specifications = [
        ("path-scope-pair", "fixture_path_pair", False),
        ("phase-scope-pair", "fixture_phase_pair", True),
        ("wait-scope-pair", "fixture_wait_pair", True),
        ("phase-switch", "fixture_phase_switch", True),
        ("count-active", "fixture_count", True),
        ("count-inactive", "fixture_count", False),
        ("header-first", "fixture_header", True),
        ("header-same", "fixture_header", True),
        ("header-changed", "fixture_header", True),
        ("header-inactive", "fixture_header", False),
    ]
    if not args.skip_tick:
        specifications.append(("normal-tick", "fixture_normal_tick", False))
    for name, entry, outer in specifications:
        machine = copy.deepcopy(baseline) if name != "normal-tick" else load(elf)
        if name == "normal-tick": machine.call("fixture_prepare", 1)
        if outer: machine.call("fixture_open_outer")
        if name in ("header-same", "header-changed"):
            machine.call("fixture_header")
        if name == "header-changed":
            word = machine.symbols["_fixture_words"][0]
            machine.put(word, machine.word(word) ^ 1)
        row, trace = timed(machine, entry)
        row.update(pricing.price(model, name, trace))
        semantic = snapshot(machine)
        assert semantic["near_op_counters"] == expected(name), (name, semantic)
        row.update(name=name, kind="hot-hook", semantic=semantic)
        rows.append(row)
        print("PASS model", name, row["model_cycles"], flush=True)
    for pieces in (0, 1, 16, 64):
        name = f"synthetic-frame-{pieces}"
        machine = copy.deepcopy(baseline)
        row, trace = timed(machine, "fixture_frame", pieces)
        row.update(pricing.price(model, name, trace))
        semantic = snapshot(machine)
        assert semantic["near_op_counters"] == expected("synthetic-frame", pieces), (name, semantic)
        row.update(name=name, kind="synthetic-frame", pieces=pieces, semantic=semantic,
            hook_counts=dict(origin="Assumed synthetic fixture schedule; not observed r101",
                outer_scope_pairs=1, nested_scope_pairs=3 * pieces,
                standalone_count_calls=4 * pieces, submitted_header_calls=pieces,
                first_headers=int(pieces > 0), unchanged_headers=max(0, pieces - 1),
                clock_edge_calls=2 + 6 * pieces))
        assert row["unpriced_edge_calls"].get("__dreamcast_get_ticks", 0) == 2 + 6 * pieces
        rows.append(row)
        print("PASS model", name, row["model_cycles"], flush=True)
    by_name = {row["name"]: row for row in rows}
    c = lambda key: by_name[key]["model_cycles"]
    # This arithmetic view is deliberately distinguished from the compiled
    # frame traces above: isolated wrappers/call sites do not schedule additively.
    per_piece = 3 * c("phase-scope-pair") + 4 * c("count-active") + c("header-same")
    formula = dict(scope="MODELLED arithmetic budget; isolated synthetic caller prices; excludes real external edges",
        warm_per_piece_cycles=per_piece,
        per_piece="3 * phase_scope_pair + 4 * active_count + unchanged_header",
        warm_fixed_outer_cycles=c("path-scope-pair"),
        warm_first_header_adjustment=c("header-first") - c("header-same"),
        warm_normal_tick_cycles=c("normal-tick") if "normal-tick" in by_name else None,
        frame="normal_tick + path_scope_pair + P * per_piece + (P > 0 ? first_header - unchanged_header : 0)",
        additional_calls="Add separate active/inactive count, header, phase-switch and wait-scope terms when real hook counts exist",
        counts_origin="P and all hook frequencies are assumptions. No game trace or r101 hook census was provided.",
        cold_icache="Use complete-sequence cold-I rows; do not sum independently cold hook prices.",
        nonadditivity="Compiled frame rows include their loop, argument setup and actual scheduling; the arithmetic sum is not an identity.",
        cycles_to_ms="cycles / 200000 at an assumed 200 MHz; still MODELLED, with listed costs excluded")
    report = dict(status="PASS" if build_receipt["pinned_toolchain"] else "DEVELOPMENT_ONLY",
        scope=__doc__, build=build_receipt, cases=rows, formulas=formula,
        memory_controls=target_machine.memory_controls(), opcode_controls=opcode_controls(),
        inherited_xor_controls=known_scalar.opcode_controls(), model=model.metadata(),
        model_limitations=["Perfect D-cache; architectural line unions are not cache misses or bus traffic",
            "Warm I uses perfect-I; cold I starts an 8 KiB cache once per complete sequence",
            "No real timer/MMIO body, IRQ delivery/contention, scheduler or renderer work",
            "Real thd_current reads and pinned KOS clock conversion are retained; raw timer/identity/log/format edge bodies are excluded",
            "Caller scaffolding is synthetic and its register allocation can differ from actual geometry call sites",
            "Normal-tick path does not seal a window; once-per-window formatting and copying need separate hardware observation"],
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in (
            Path(target_machine.__file__), Path(target_machine.scalar.__file__), REPLAY / "memory_trace.py",
            Path(pipeline_cost.__file__), Path(pricing.__file__), Path(known_scalar.__file__), pipeline_cost.MODEL)})
    (output / "target-cost-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        p.add_argument("--" + name, required=True, type=Path)
    p.add_argument("--host-cc", default="gcc")
    p.add_argument("--allow-version-mismatch", action="store_true",
                   help="Development only; report cannot PASS the pinned-toolchain gate")
    p.add_argument("--skip-tick", action="store_true", help="Omit optional normal-tick cost and state this in the report")
    report = run(p.parse_args())
    print(json.dumps(dict(status=report["status"], cases=len(report["cases"]))))


if __name__ == "__main__":
    main()
