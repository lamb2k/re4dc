#!/usr/bin/env python3
"""Compare actual compiled SH4 setup/selection entries and synthetic CPU cost.

The executable includes production native_static.cpp and group_visible. No
transform, lighting, texture bind, queue replay, PVR or real game frame is run.
Pipeline figures use the repository model, with perfect D-cache and no memory
events. Cold and repeated-call I-cache sensitivity uses the synthetic ELF layout.
"""
import argparse
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backface_cone_front"))
import pipeline_cost
import sh4_machine as target


class Machine(target.Machine):
    """Keep SH4 effective addresses at 32 bits; observe, never price, writes."""
    def __init__(self):
        self.undo = None
        self.tracking = False
        self.write_bytes = 0
        self.minimum_sp = 0x500000
        super().__init__(b"", b"", b"", 255, 0, fpscr=0x40000)

    def read(self, address, size):
        return super().read(address & 0xFFFFFFFF, size)

    def write(self, address, value, size):
        address &= 0xFFFFFFFF
        if self.undo is not None:
            for at in range(address, address + size):
                if at not in self.undo:
                    self.undo[at] = self.mem[at]
        if self.tracking:
            self.write_bytes += size
        return super().write(address, value, size)

    def step(self, pc, delay=False):
        self.minimum_sp = min(self.minimum_sp, self.reg[15])
        opcode = self.read(pc, 2)
        if opcode & 0xF00F in (0x000C, 0x000D):  # indexed MOV.B/MOV.W, sign-extended
            n, m = (opcode >> 8) & 15, (opcode >> 4) & 15
            size = 1 if opcode & 15 == 12 else 2
            value = self.read(self.reg[0] + self.reg[m], size)
            self.instruction_pcs.append(pc)
            self.reg[n] = target.base.signed(value, size*8) & 0xFFFFFFFF
            self.steps += 1
            result = pc + 2
        elif opcode & 0xF00F == 0x200E:  # MULU.W Rm,Rn -> low unsigned16 product in MACL
            n, m = (opcode >> 8) & 15, (opcode >> 4) & 15
            self.instruction_pcs.append(pc)
            self.macl = (self.reg[n] & 65535) * (self.reg[m] & 65535)
            self.steps += 1
            result = pc + 2
        elif opcode & 0xF00F == 0x300A:  # SUBC Rm,Rn, incoming/outgoing borrow in T
            n, m = (opcode >> 8) & 15, (opcode >> 4) & 15
            a, b, borrow = self.reg[n], self.reg[m], self.t
            self.instruction_pcs.append(pc)
            self.reg[n] = (a - b - borrow) & 0xFFFFFFFF
            self.t = int(a < b + borrow)
            self.steps += 1
            result = pc + 2
        else:
            result = super().step(pc, delay)
        self.minimum_sp = min(self.minimum_sp, self.reg[15])
        return result

    def rollback(self):
        if self.undo is not None:
            self.mem.update(self.undo)
        self.undo = None

    def bytes_at(self, address, size):
        return bytes(self.mem[address + i] for i in range(size))


def address_controls():
    # mov.l r2,@(r0,r1); mov.l @(r0,r1),r3. The newlib memset
    # implementation uses a wrapped negative displacement in r0.
    machine = Machine()
    machine.map(0x100000, struct.pack("<2H", 0x0126, 0x031E))
    machine.map(0x2000, bytes(4))
    machine.reg[0], machine.reg[1], machine.reg[2] = 0xFFFFFFFC, 0x2004, 0x81234567
    machine.pc = machine.step(0x100000)
    machine.pc = machine.step(machine.pc)
    assert machine.reg[3] == machine.read(0x2000, 4) == 0x81234567
    assert machine.steps == len(machine.instruction_pcs) == 2
    indexed_signed = 0
    for size, opcode in ((1, 0x031C), (2, 0x031D)):
        for value in (0, 1, (1 << (size*8 - 1)) - 1, 1 << (size*8 - 1), (1 << (size*8)) - 1):
            machine.map(0x10000C, struct.pack("<H", opcode))
            machine.map(0x2000, value.to_bytes(size, "little"))
            machine.reg[0], machine.reg[1], machine.t = 0xFFFFFFFC, 0x2004, 1
            assert machine.step(0x10000C) == 0x10000E
            expected = value - (1 << (8*size)) if value & (1 << (8*size - 1)) else value
            assert machine.reg[3] == expected & 0xFFFFFFFF and machine.t == 1
            indexed_signed += 1
    values = (0, 1, 0x7FFF, 0x8000, 0xFFFF, 0x10000, 0x80000001, 0xFFFFFFFF)
    checked = 0
    for a in values:
        for b in values:
            machine.map(0x100010, struct.pack("<H", 0x264E))
            machine.reg[6], machine.reg[4], machine.t = a, b, 1
            machine.mach = 0x12345678
            before = len(machine.instruction_pcs)
            assert machine.step(0x100010) == 0x100012
            assert machine.macl == (a & 65535) * (b & 65535)
            assert machine.mach == 0x12345678 and machine.t == 1
            assert machine.reg[6] == a and machine.reg[4] == b
            assert len(machine.instruction_pcs) == before + 1
            checked += 1
    subtract_checked = 0
    for a in values:
        for b in values:
            for borrow in (0, 1):
                machine.map(0x100014, struct.pack("<H", 0x301A))
                machine.reg[0], machine.reg[1], machine.t = a, b, borrow
                assert machine.step(0x100014) == 0x100016
                assert machine.reg[0] == (a - b - borrow) & 0xFFFFFFFF
                assert machine.reg[1] == b and machine.t == int(a < b + borrow)
                subtract_checked += 1
    return dict(status="PASS", indexed_address_opcodes=2, indexed_signed_load_controls=indexed_signed,
                unsigned_word_multiply_controls=checked,
                subtract_borrow_controls=subtract_checked,
                scope="32-bit indexed effective-address wrap, MULU.W and SUBC for actual compiler/newlib operations",
                manual="https://www.renesas.com/en/document/mas/sh-4-software-manual")


def load(elf):
    program, symbols = target.load_elf(elf)
    machine = Machine()
    for address, data, _ in program:
        machine.map(address, data)
    at = symbols["_fixture_layout"][0]
    layout = [machine.read(at + 4*i, 4) for i in range(22)]
    assert layout[:4] == [1, 164, 252, 8], layout[:4]
    material = [(value[0], value[1]) for name, value in symbols.items()
                if name.endswith("fixture_part") and value[1]]
    assert len(material) == 1, material
    machine.material_address, machine.material_bytes = material[0]
    return machine, symbols, layout


def prepare(machine, symbols, layout, data):
    magic, input_size, package_size, group_size, cone_size = struct.unpack_from("<5I", data)
    assert magic == 0x31505357 and input_size == layout[1]
    assert package_size <= layout[8] and group_size <= layout[10] and cone_size <= layout[12]
    offset = 20
    for address, size in ((layout[6], input_size), (layout[7], package_size),
                          (layout[9], group_size), (layout[11], cone_size)):
        assert offset + size <= len(data)
        machine.map(address, data[offset:offset + size])
        offset += size
    assert offset == len(data)
    machine.execute(symbols["_fixture_adopt"][0], package_size)
    assert machine.reg[0] == 1, "real MeshPackage::adopt rejected fixture"
    machine.execute(symbols["_fixture_configure"][0])
    machine.execute(symbols["_fixture_reset"][0])


def select(machine, symbols, layout, kind, repeats=1):
    material = machine.bytes_at(machine.material_address, machine.material_bytes)
    machine.undo = {}
    pcs, per_call = [], []
    machine.tracking = True
    machine.write_bytes = 0
    machine.minimum_sp = machine.reg[15]
    try:
        for _ in range(repeats):
            machine.execute(symbols["_fixture_select_" + kind][0])
            per_call.append(machine.steps)
            pcs += machine.instruction_pcs
        machine.tracking = False
        assert machine.bytes_at(machine.material_address, machine.material_bytes) == material, "shared material changed"
        count = machine.reg[0]
        eligible = machine.read(layout[15] + 4, 4)
        assert count <= layout[14] // layout[3]
        evidence = dict(instructions=len(pcs), per_call_instructions=per_call,
                        peak_stack_bytes=machine.initial_regs[15] - machine.minimum_sp,
                        observed_store_bytes=machine.write_bytes)
        machine.reg[5] = eligible
        machine.execute(symbols["_fixture_snapshot"][0], count)
        result = machine.bytes_at(layout[15], layout[2])
        picks = machine.bytes_at(layout[13], layout[14])
        semantic = []
        for i in range(count):
            let, nr, mask, lo, hi = struct.unpack_from("<H4B", picks, i*layout[3])
            semantic.append([let, nr, 0 if nr == 255 else mask,
                             0 if nr == 255 else lo, 0 if nr == 255 else hi])
        evidence.update(count=count, eligible=eligible, picks=semantic,
                        statistics=list(struct.unpack("<%dI" % (len(result)//4), result)),
                        result_sha256=hashlib.sha256(result).hexdigest())
        trace = SimpleNamespace(instruction_pcs=pcs, steps=len(pcs), read=machine.read)
        assert sum(per_call) == trace.steps
        return evidence, result, picks, trace
    finally:
        machine.tracking = False
        machine.rollback()


def same(before, after, layout, name):
    a, result_a, picks_a, _ = before
    b, result_b, picks_b, _ = after
    assert result_a == result_b, (name, "statistics", a["statistics"], b["statistics"])
    assert a["picks"] == b["picks"], (name, "picks", a["picks"], b["picks"])
    count = a["count"]
    assert picks_a[count*layout[3]:] == picks_b[count*layout[3]:], (name, "out-of-count writes")


def cached_price(model, name, trace, perfect):
    row = model.price(name, trace)
    if perfect:
        return row
    # Reuse the exactly checked trace and ELF address view; only the I-cache
    # model changes. There are no data-address events to price a D-cache.
    output = model.output / (name + "-icache")
    command = [str(model.binary), "--elf", str(model.view), "--out", str(output),
               "--perfect-dc", "--no-dma", "--sq-cost", "0", str(model.output / (name + ".bin"))]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    output.with_suffix(".log").write_text(result.stdout)
    assert result.returncode == 0, result.stdout
    totals = dict(line.split() for line in output.with_suffix(".sum.txt").read_text().splitlines())
    assert int(totals["insns"]) == trace.steps
    for key in ("dfills_per_frame", "writebacks_per_frame", "dma_bytes_per_frame", "dma_starts_per_frame"):
        assert float(totals[key]) == 0, (name, key, totals[key])
    row["icache"] = dict(model_cycles=int(totals["cycles"]),
                         instruction_fills=float(totals["ifills_per_frame"]), command=command,
                         scope="Default instruction cache, initially cold once for this complete trace; synthetic link layout")
    return row


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    elf = args.elf.resolve()
    machine, symbols, layout = load(elf)
    manifest_path = args.cases.resolve()
    cases = json.loads(manifest_path.read_text())
    if args.case:
        names = set(args.case)
        cases = [case for case in cases if case["name"] in names]
        assert {case["name"] for case in cases} == names
    model = None if args.no_model else pipeline_cost.Model(output / "pipeline", elf, args.host_cc)
    default_cost = {"empty-part", "whole-inside", "whole-tested", "partial-groups",
                    "many-meshlets", "scalar-box-fallback", "marked-uv-cull-1"}
    cost_names = set(args.cost_case) if args.cost_case else default_cost
    results, costs = [], []
    for case in cases:
        path = manifest_path.parent / case["file"]
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == case["sha256"]
        prepare(machine, symbols, layout, data)
        before = select(machine, symbols, layout, "full")
        after = select(machine, symbols, layout, "light")
        same(before, after, layout, case["name"])
        if case["expected"] is not None:
            assert before[0]["picks"] == case["expected"], (case["name"], "independent expected picks")
        results.append(dict(name=case["name"], input_sha256=case["sha256"], full=before[0], light=after[0]))
        print("PASS", case["name"], before[0]["instructions"], after[0]["instructions"], flush=True)
        if model and case["name"] in cost_names:
            for repeats in (1, args.warm_calls):
                arms = {}
                pairs = []
                for kind in ("full", "light"):
                    selected = (before if kind == "full" else after) if repeats == 1 else select(machine, symbols, layout, kind, repeats)
                    pairs.append(selected)
                    name = "%s-%s-%d" % (case["name"], kind, repeats)
                    priced = cached_price(model, name, selected[3], not args.icache)
                    arms[kind] = dict(instructions=selected[0]["instructions"], **priced)
                    arms[kind]["symbol_instructions"] = pipeline_cost.symbol_costs(selected[3], symbols)
                same(pairs[0], pairs[1], layout, case["name"] + " repeated")
                costs.append(dict(name=case["name"], calls=repeats, **arms))
        (output / "progress.json").write_text(json.dumps(dict(passed=len(results), cases=results, costs=costs), indent=2) + "\n")
    report = dict(status="PASS", scope=__doc__, elf=str(elf), elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest(),
                  input_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                  fpscr=0x40000, arithmetic="RN, DN=1; RZ not executed", address_controls=address_controls(),
                  layout=dict(input_bytes=layout[1], result_bytes=layout[2], pick_bytes=layout[3],
                              full_draw_bytes=layout[4], selector_bytes=layout[5]),
                  cases=results, cost_cases=costs, checks=len(results),
                  model=model.metadata() if model else None,
                  source_sha256={str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in (Path(__file__), Path(target.__file__), Path(pipeline_cost.__file__))},
                  no_real_scene_or_frame_time_claim=True)
    (output / "target-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case", action="append")
    parser.add_argument("--cost-case", action="append")
    parser.add_argument("--warm-calls", type=int, default=32)
    parser.add_argument("--no-model", action="store_true")
    parser.add_argument("--icache", action="store_true")
    parser.add_argument("--host-cc", default="gcc")
    args = parser.parse_args()
    assert 2 <= args.warm_calls <= 64
    report = run(args)
    print("PASS target setup/selection: %d cases" % report["checks"])


if __name__ == "__main__":
    main()
