#!/usr/bin/env python3
"""Observe unchanged, Make-built AVK kernels on constrained address fixtures.

This is a byte/line audit, not general SH4 floating-point emulation. FTRV accepts
only diagonal zero/one matrices and FIPR only bounded integer products/sums
representable exactly in float. FSRRA accepts only input 1.0 and pins its result
to 1.0; hardware reciprocal accuracy is not being validated. Other inputs fail
closed. All position coordinates are far inside the clip boundaries, so this
pin cannot change the address/palette branch path for the audited inputs.
All executed instructions, palette switches and memory accesses are real SH4
opcodes. Model cycles assume perfect D-cache; cold-I uses an isolated synthetic
ELF. Neither traffic nor timing constitutes a captured game frame or console
measurement. Synthetic output sanity checks do not validate target TA words.
"""
import argparse
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
REPLAY = HERE.parent / "world_replay_lean"
sys.path.insert(0, str(REPLAY))
import target_machine
import pipeline_cost
from memory_trace import Observer, summarize
spec = importlib.util.spec_from_file_location("actor_bytes_kernel_price", REPLAY / "target_run.py")
price_helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(price_helpers)
sys.path.insert(0, str(HERE))
import build_profile

REGIONS = dict(arguments=(0x9000, 0x200), records=(0x20000, 0x1000),
    positions=(0x22000, 0x1000), normals=(0x24000, 0x1000), uv=(0x26000, 0x1000),
    vertex_cache=(0x28000, 0x1000), outcodes=(0x2a000, 0x1000),
    position_palette=(0x2c000, 0x1000), direction_palette=(0x2d000, 0x1000),
    ready_bytes=(0x2e000, 0x1000), light_color=(0x2f000, 0x1000),
    stack=(0x4f0000, 0x10000))


class KernelArithmetic(target_machine.ArithmeticMachine):
    def step(self, pc, delay=False):
        opcode = self.fetch(pc)
        n, m = (opcode >> 8) & 15, (opcode >> 4) & 15
        active = (self.fpscr >> 21) & 1
        if opcode & 0xf3ff == 0xf1fd:  # FTRV XMTRX,FVn
            matrix = self.fp[active ^ 1]
            assert all(word == 0 for i, word in enumerate(matrix) if i not in (0, 5, 10, 15)), "non-diagonal FTRV"
            assert all(matrix[i] in (0, 0x3f800000) for i in (0, 5, 10, 15)), "unqualified diagonal FTRV"
            first = n & 12
            for i in range(4):
                # Values in this audit are finite; multiplication by +1 is
                # exact. Zero output is restricted to nonnegative inputs.
                value = self.fp_value(first + i)
                assert 0 <= value <= 1024
                if matrix[5 * i] == 0:
                    self.sf(first + i, 0)
        elif opcode & 0xf0ff == 0xf07d:  # FSRRA FRn
            assert self.f(n) == 0x3f800000, "FSRRA fixture only admits exactly 1.0"
        elif opcode & 0xf0ff == 0xf0ed:  # FIPR FVm,FVn
            first, second = n & 12, (n & 3) * 4
            a = [self.fp_value(first + i) for i in range(4)]
            b = [self.fp_value(second + i) for i in range(4)]
            assert all(value.is_integer() and abs(value) <= 32 for value in a + b), "unqualified FIPR values"
            value = sum(int(x) * int(y) for x, y in zip(a, b))
            assert abs(value) <= 4096
            self.sf(first + 3, target_machine.scalar.base.fbits(float(value)))
        elif opcode & 0xf00f in (0xf008, 0xf009) and self.fpscr & (1 << 20) and n & 1:
            # SH4 little-endian FMOV transfers each single word in matrix
            # order. KOS matrix.s documents this pair ordering explicitly.
            address = self.reg[m]
            value = self.read(address, 8)
            self.fp[active ^ 1][n & 14] = value & 0xffffffff
            self.fp[active ^ 1][(n & 14) + 1] = value >> 32
            if opcode & 15 == 9:
                self.reg[m] = (address + 8) & 0xffffffff
        elif opcode & 0xf0ff == 0xf03d:  # FTRC FRn,FPUL
            value = self.fp_value(n)
            assert 0 <= value <= 1024
            self.fpul = int(value)
        else:
            return super().step(pc, delay)
        self.instruction_pcs.append(pc)
        self.steps += 1
        return pc + 2

    def execute_kernel(self, entry, argument):
        self.pc, self.pr, self.reg[4] = entry, 0xfffffff0, argument
        self.steps, self.instruction_pcs = 0, []
        while self.pc != 0xfffffff0:
            self.pc = self.step(self.pc)
            assert self.steps < 200000
        assert self.steps == len(self.instruction_pcs)
        assert self.reg[15] == self.initial_regs[15]
        assert self.reg[8:15] == self.initial_regs[8:15]
        assert self.fpscr == self.initial_fpscr
        assert self.fp[0][12:16] == self.initial_fp[0][12:16]
        # AVK's documented ABI intentionally clobbers XMTRX.


class Machine(Observer, KernelArithmetic):
    pass


def kernel_controls():
    controls = []
    machine = Machine()
    machine.map(0x100000, struct.pack("<H", 0xf319))  # FMOV @R1+,XD2
    machine.map(0x2000, struct.pack("<2I", 0x3f800000, 0x40000000))
    machine.reg[1], machine.fpscr = 0x2000, machine.fpscr | (1 << 20)
    machine.observe_start(); machine.step(0x100000); result = machine.observe_stop()
    assert machine.fp[1][2:4] == [0x3f800000, 0x40000000] and machine.reg[1] == 0x2008
    assert result["cached"]["load_instructions"] == 1 and result["cached"]["load_bytes"] == 8
    controls.append("FMOV XD selects the opposite bank, preserves single-word order and records one8-byteload")

    machine = Machine(); machine.map(0x100000, struct.pack("<H", 0xf5fd))
    machine.fp[1] = [0x3f800000 if i in (0, 5, 10) else 0 for i in range(16)]
    for i, value in enumerate((1., 2., 3., 1.)): machine.sf(4 + i, target_machine.scalar.base.fbits(value))
    machine.step(0x100000)
    assert [machine.fp_value(i) for i in range(4, 8)] == [1., 2., 3., 0.]
    controls.append("FTRV decodes FV4 and accepts the zero homogeneous row used by lights")
    machine.fp[1][1] = 0x3f800000
    try: machine.step(0x100000)
    except AssertionError: pass
    else: raise AssertionError("unqualified FTRV was accepted")

    machine = Machine(); machine.map(0x100000, struct.pack("<H", 0xf9ed))
    for start, values in ((4, (1., 2., 3., 0.)), (8, (0., 1., 0., 9.))):
        for i, value in enumerate(values): machine.sf(start + i, target_machine.scalar.base.fbits(value))
    machine.step(0x100000)
    assert machine.fp_value(11) == 2. and machine.fp_value(7) == 0.
    controls.append("FIPR source/destination vector decoding and bounded exact integer sum")
    machine.sf(4, target_machine.scalar.base.fbits(0.5))
    try: machine.step(0x100000)
    except AssertionError: pass
    else: raise AssertionError("fractional FIPR was accepted")

    machine = Machine(); machine.map(0x100000, struct.pack("<H", 0xf07d))
    machine.sf(0, 0x3f800000); machine.step(0x100000)
    assert machine.f(0) == 0x3f800000
    machine.sf(0, 0x40000000)
    try: machine.step(0x100000)
    except AssertionError: pass
    else: raise AssertionError("general FSRRA was accepted")
    controls.append("FSRRA pins only input1 to result1; general reciprocal inputs fail closed")
    return dict(status="PASS", controls=controls, scope="Bounded address-fixture controls, not general SH4 FP qualification")


def traffic_details(events, prefetches=()):
    result = summarize(events, prefetches)
    visits = sum(len({address >> 5 for address in range(event[3], event[3] + event[4])}) for event in events)
    result["demand_line_visits"] = visits
    result["repeated_demand_line_visits"] = visits - result["cached"]["unique_data_lines"]
    groups = {}
    for event in events:
        name = next((name for name, (start, size) in REGIONS.items() if start <= event[3] < start + size), "literal_or_table")
        groups.setdefault(name, []).append(event)
    result["regions"] = {name: summarize(rows)["cached"] for name, rows in groups.items()}
    return result


def build(output, profile_path, compiler):
    profile = json.loads(profile_path.read_text())
    row = profile["profiles"]["s0-d1-c0"]
    command = list(row["seed_command"])
    # The rule is keyed under OBJDIR; keep the original object root for dry
    # expansion, then replace only the compiler's output when actually run.
    command[3] = row["seed_command"][3].replace("native_actor_fast.o", "avk_sh4.o")
    result = subprocess.run(command, cwd=DC / "game", capture_output=True, text=True)
    (output / "make-avk.log").write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    commands = [shlex.split(line) for line in result.stdout.replace("\\\n", " ").splitlines() if line.startswith("kos-cc ")]
    assert len(commands) == 1, commands
    actual = commands[0]
    assert actual[-4] == "-c" and actual[-3] == "platform/avk_sh4.S"
    flags = actual[1:-4]
    prefix = str(compiler).removesuffix("g++")
    obj, elf = output / "avk_sh4.o", output / "avk_sh4.elf"
    source = DC / "game/platform/avk_sh4.S"
    builder = build_profile.Build(output)
    builder.run([prefix + "gcc", *flags, "-c", source, "-o", obj], cwd=DC / "game", label="avk")
    script = output / "avk.ld"
    script.write_text("SECTIONS { . = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } }\n")
    builder.run([prefix + "gcc", "-m4-single", "-ml", "-nostdlib", "-Wl,-T," + str(script),
        "-Wl,-e,_re4dc_avk_pos_skin_s16", obj, "-o", elf], label="avk-link")
    (output / "avk-disassembly.txt").write_bytes(builder.run([prefix + "objdump", "-d", elf], label="avk-disassembly"))
    return elf, dict(make_command=command, expanded_compile_command=actual, applied_flags=flags,
        profile_sha256=build_profile.sha(profile_path), source_sha256=build_profile.sha(source),
        object_sha256=build_profile.sha(obj), elf_sha256=build_profile.sha(elf), sections=build_profile.sections(obj))


def prepare(elf, n, run_length, normal_stride, scattered, record_stride):
    program, symbols = target_machine.scalar.load_elf(elf)
    machine = Machine()
    for address, data, _ in program:
        machine.map(address, data)
    for start, size in REGIONS.values():
        machine.map(start, bytes(size))
    def address(name): return REGIONS[name][0]
    for i in range(n + 4):
        index = (i * 37) % 251 if scattered else i
        palette = (i // run_length) % 4
        machine.map(address("records") + i * record_stride, struct.pack("<3H", index, index, index))
        machine.map(address("positions") + index * 8, struct.pack("<4h", i % 16, i % 8, 1, palette))
        normal = struct.pack("<4h", 1, 2, 3, palette) if normal_stride == 8 else struct.pack("<4b", 1, 2, 3, palette)
        machine.map(address("normals") + index * normal_stride, normal)
        machine.map(address("uv") + index * 4, struct.pack("<2h", i % 16, i % 8))
    identity = [1.0 if i in (0, 5, 10, 15) else 0.0 for i in range(16)]
    direction = [1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0.]
    for i in range(4):
        machine.map(address("position_palette") + 64 * i, struct.pack("<16f", *identity))
        machine.map(address("direction_palette") + 48 * i, struct.pack("<12f", *direction))
    machine.map(address("ready_bytes"), bytes([1] * 4))
    identity[-1] = 0
    machine.map(address("light_color"), struct.pack("<16f", *identity))
    machine.map(0x9000, struct.pack("<10I8f", address("records"), n, address("positions"), address("uv"),
        address("vertex_cache"), address("outcodes"), record_stride, address("position_palette"),
        address("ready_bytes"), 4, 640., 480., 0.125, 1000., 1., 0., 1., 0.))
    machine.map(0x9100, struct.pack("<10I", address("records"), n, address("normals"),
        address("vertex_cache") + 24, record_stride, address("light_color"), address("direction_palette"),
        address("ready_bytes"), 4, 0xff000000))
    return machine, symbols


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    elf, build_receipt = build(output, args.profile.resolve(), args.sh4_cxx.resolve())
    model = pipeline_cost.Model(output / "model", elf, args.host_cc) if not args.no_model else None
    cases = [(n, run, normal, scattered, stride) for n in (8, 32, 128) for run in (1, 8, 128)
             for normal in (4, 8) for scattered in (False, True) for stride in (6, 8)]
    if args.quick:
        cases = [(32, 128, 8, False, 6), (32, 8, 8, False, 6), (32, 128, 4, False, 6),
                 (32, 128, 8, True, 6)]
    rows = []
    for n, run_length, normal, scattered, stride in cases:
        machine, symbols = prepare(elf, n, run_length, normal, scattered, stride)
        name = f"n{n}-run{run_length}-normal{normal}-scatter{int(scattered)}-rec{stride}"
        result = {}
        joined = []
        for kind, entry, argument in (("position", "pos_skin_s16", 0x9000),
            ("light", "light_skin_n16" if normal == 8 else "light_skin", 0x9100)):
            machine.minimum_sp = machine.reg[15]
            machine.observe_start()
            machine.execute_kernel(symbols["_re4dc_avk_" + entry][0], argument)
            machine.observe_stop()
            assert machine.reg[0] == 0, (name, kind, "kernel stopped early")
            row = dict(instructions=machine.steps, traffic=traffic_details(machine.memory_events, machine.prefetch_events),
                peak_stack_bytes=machine.initial_regs[15] - machine.minimum_sp)
            if model:
                trace = SimpleNamespace(instruction_pcs=list(machine.instruction_pcs), steps=machine.steps, read=machine.read)
                row.update(price_helpers.price(model, name + "-" + kind, trace))
            result[kind] = row
            offset = max((event[0] for event in joined), default=-1) + 1
            joined.extend((event[0] + offset, *event[1:]) for event in machine.memory_events)
        for i in range(n):
            words = struct.unpack("<8I", machine.bytes_at(REGIONS["vertex_cache"][0] + i * 32, 32))
            expected = [0, *struct.unpack("<5I", struct.pack("<5f", i % 16, i % 8, 1., i % 16, i % 8)), 0xff020406, 0]
            assert list(words) == expected, (name, i, words, expected)
        assert machine.bytes_at(REGIONS["outcodes"][0], n) == bytes(n)
        rows.append(dict(name=name, vertices=n, palette_run_length=run_length, normal_stride=normal,
            scattered=scattered, record_stride=stride, kernels=result, combined_traffic=traffic_details(joined)))
        print("PASS", name, flush=True)
    report = dict(status="PASS", scope=__doc__, build=build_receipt, cases=rows,
        memory_controls=target_machine.memory_controls(), kernel_controls=kernel_controls(), model=model.metadata() if model else None,
        source_sha256={str(path.relative_to(ROOT)): build_profile.sha(path) for path in
            (Path(__file__), REPLAY / "target_machine.py", REPLAY / "sh4_machine.py", REPLAY / "memory_trace.py")})
    (output / "kernel-audit.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "profile", "sh4-cxx"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--host-cc", default="gcc")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--no-model", action="store_true")
    result = run(parser.parse_args())
    print(json.dumps(dict(status=result["status"], cases=len(result["cases"]))))


if __name__ == "__main__":
    main()
