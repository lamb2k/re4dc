#!/usr/bin/env python3
"""Execute compiled SH4 root decisions/transforms and model their CPU cost.

Synthetic objects; no geometry submission, GPU, full room, bus contention,
DMA/interrupts or whole-frame measurement. Data line counts are observed
32-byte address sets, not cache misses. Uses the existing qualified interpreter
and hwsim pipeline model; XOR #imm,R0 is checked for all 256 immediates, and
the existing ESP fixture's ROTR interpretation is checked on boundary inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
import extract
from build_controls import Build, sections, sha, stack_usage
sys.path.insert(0, str(extract.HERE.parent / "world_replay_lean"))
import target_machine
import pipeline_cost


class Machine(target_machine.Machine):
    def step(self, pc, delay=False):
        opcode = self.fetch(pc)
        if opcode & 0xff00 == 0xca00:  # XOR #imm,R0: zero-extended imm8, T unchanged
            self.instruction_pcs.append(pc);self.steps += 1
            self.reg[0] ^= opcode & 255
            return pc + 2
        if opcode & 0xf0ff == 0x4005:  # Same ROTR semantics as esp_setup_lean/measure_target.py
            self.instruction_pcs.append(pc);self.steps += 1
            n = (opcode >> 8) & 15;old = self.reg[n]
            self.t = old & 1;self.reg[n] = (old >> 1) | ((old & 1) << 31)
            return pc + 2
        return super().step(pc, delay)


def xor_controls():
    machine = Machine();checks = 0
    for value in (0, 1, 0x80000000, 0x12345678, 0xffffffff):
        for immediate in range(256):
            machine.map(0x100000, struct.pack("<H", 0xca00 | immediate))
            machine.reg[0] = value;machine.t = checks & 1
            before = machine.t;machine.observe_start()
            assert machine.step(0x100000) == 0x100002
            traffic = machine.observe_stop()
            assert machine.reg[0] == value ^ immediate and machine.t == before
            assert not traffic["cached"]["load_bytes"] and not traffic["cached"]["store_bytes"]
            checks += 1
    assert machine.steps == len(machine.instruction_pcs) == checks
    for n in range(16):
        for value in (0, 1, 2, 0x80000000, 0xffffffff):
            machine.map(0x100000, struct.pack("<H", 0x4005 | (n << 8)))
            machine.reg[n] = value;machine.t = 1
            assert machine.step(0x100000) == 0x100002
            assert machine.reg[n] == ((value >> 1) | ((value & 1) << 31)) and machine.t == value & 1
    return dict(xor_immediate_checks=checks, rotr_checks=80, status="PASS")


def cold(model, name, trace):
    row = model.price(name, trace)
    prefix = model.output / (name + "-cold")
    command = [str(model.binary), "--elf", str(model.view), "--out", str(prefix), "--perfect-dc", "--no-dma", "--sq-cost", "0", str(model.output / (name + ".bin"))]
    result = subprocess.run(command, text=True, capture_output=True)
    prefix.with_suffix(".log").write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr
    totals = dict(line.split() for line in prefix.with_suffix(".sum.txt").read_text().splitlines())
    assert int(totals["insns"]) == trace.steps
    row["cold_icache"] = dict(model_cycles=int(totals["cycles"]), instruction_fills=float(totals["ifills_per_frame"]), command=command)
    return row


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--build-controls", type=Path, required=True)
    args = p.parse_args()
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=False)
    production = json.loads(args.build_controls.read_text())
    assert production["source_sha256"] == sha(extract.SOURCE), "production source changed after complete TU build"
    profile = production["profile"]
    compiler = profile["compile_command"][0]
    # The expanded recipe names kos-c++; complete-TU receipts record the actual
    # selected compiler in their execution ledger.
    commands = json.loads((args.build_controls.parent / "build-commands.json").read_text())
    compiler = commands[0]["argv"][0]
    flags = [compiler, *profile["flags"], "-DRE4DC_ROOT_POSE_WITNESS_PREFLIGHT=1", "-DRE4DC_ROOT_POSE_REFUSAL_DIAG=0"]
    parts = extract.pieces()
    text = (extract.HERE / "target_fixture.cpp.in").read_text()
    for key in ("helpers", "state", "binding", "draw"):
        text = text.replace("@" + key.upper() + "@", parts[key])
    source = output / "target-fixture.cpp";source.write_text(text)
    linker = output / "fixture.ld"
    linker.write_text("SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) } . = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n")
    roots = ("fixture_layout", "fixture_setup", "fixture_prepare", "fixture_query", "fixture_draw")
    builder = Build(output);rows = {}
    for cap in (0, 1):
        label = "cap" + str(cap);obj = output / (label + ".o");elf = output / (label + ".elf")
        builder.run([*flags, "-DRE4DC_ROOT_POSE_CAP_FALLBACK=" + str(cap), "-fstack-usage", "-c", source, "-o", obj], label=label)
        builder.run([compiler, "-m4-single", "-ml", "-nostartfiles", "-Wl,--gc-sections", "-Wl,-T," + str(linker),
                     "-Wl,-e,_fixture_setup", *("-Wl,-u,_" + name for name in roots), obj, "-lm", "-o", elf], label=label + "-link")
        (output / (label + ".disassembly.txt")).write_bytes(builder.run([compiler.removesuffix("g++") + "objdump", "-d", "-C", elf], label=label + "-disassembly"))
        model = pipeline_cost.Model(output / (label + "-model"), elf)
        cases = {}
        for kind, name in enumerate(("unchanged", "cached-moved", "overflow", "hidden", "returned-bind", "serial-reused")):
            program, symbols = target_machine.scalar.load_elf(elf)
            machine = Machine()
            for address, data, _ in program:machine.map(address, data)
            layout = [machine.read(symbols["_fixture_layout"][0] + 4 * i, 4) for i in range(10)]
            assert layout[:8] == [1, 76, 40, 136, 136, 53000, 56, 72], layout
            machine.execute(symbols["_fixture_setup"][0]);assert machine.reg[0] == 1
            machine.execute(symbols["_fixture_prepare"][0], kind)
            case = {}
            for entry in ("fixture_query", "fixture_draw"):
                machine.minimum_sp = machine.reg[15];machine.observe_start()
                machine.execute(symbols["_" + entry][0])
                traffic = machine.observe_stop();pcs = list(machine.instruction_pcs)
                trace = SimpleNamespace(instruction_pcs=pcs, steps=len(pcs), read=machine.read)
                cost = cold(model, name + "-" + entry, trace)
                case[entry] = dict(result=machine.reg[0], instructions=machine.steps,
                                   peak_stack_bytes=machine.initial_regs[15] - machine.minimum_sp,
                                   traffic=traffic, cost=cost)
            expected_query = (0, 2, 4 if cap else 1, 1, 4 if cap else 1, 4 if cap else 1)[kind]
            expected_draw = int(kind < 2 or (cap and kind in (2, 4)))
            assert case["fixture_query"]["result"] == expected_query, (cap, name, case)
            assert case["fixture_draw"]["result"] == expected_draw, (cap, name, case)
            if expected_draw:
                actual = struct.unpack("<12f", machine.bytes_at(layout[8], 48))
                expected = (0, 0, -2, 17, 0, 3, 0, -5, -4, 0, 0, 31) if kind in (0, 4) else (2, 0, 0, -30, 0, -5, 0, 40, 0, 0, 3, 50)
                assert all(abs(a-b)<0.002 for a, b in zip(actual, expected)), (name, actual, expected)
            assert machine.read(layout[9], 4) == 1, "no later allocation at bind/query/draw"
            cases[name] = case
        rows[label] = dict(layout=layout[:8], sections=sections(elf), stack_usage=stack_usage(obj.with_suffix(".su")),
                           elf_sha256=sha(elf), model=model.metadata(), cases=cases)
        print(label + ": target execution PASS", flush=True)
    result = dict(status="PASS", scope=__doc__, source_sha256=sha(extract.SOURCE), fixture_sha256=sha(source), arms=rows,
                  model_traffic_controls=target_machine.memory_controls(), xor_controls=xor_controls(),
                  whole_frame="NOT MEASURED. Any transform-only projection uses these synthetic instruction-model cycles at nominal 200 MHz; geometry/GPU work and memory stalls are additional.")
    (output / "target-cost.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
