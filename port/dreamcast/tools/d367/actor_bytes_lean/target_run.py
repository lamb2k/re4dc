#!/usr/bin/env python3
"""Price actual compiled Part/color phases and count their memory traffic.

The changed production fragments, full Part layout and scalar loops execute as
SH4 instructions. Observed color edges check every live ARGB word. The unchanged
directional/exact light calculation supplies synthetic ARGB words outside the
timed instruction trace. Position writes, cache priming and TA submission are
excluded; therefore removed color visits do not imply fewer total vertex-cache
lines in the renderer. Warm/cold-I cycle estimates use perfect D-cache and a
synthetic code layout, not hardware time or a captured character workload.
The Part observer keeps full construction live, including stores a production
caller may omit. Per-Part and per-meshlet deltas are isolated phase estimates.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
REPLAY = HERE.parent / "world_replay_lean"
sys.path.insert(0, str(REPLAY))
import target_machine
import pipeline_cost
from memory_trace import summarize
spec = importlib.util.spec_from_file_location("actor_bytes_color_price", REPLAY / "target_run.py")
price_helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(price_helpers)

LAYOUT = ("version", "part_size", "frame_size", "lights_size", "part", "frame", "lights", "vertices", "counts",
          "cache", "primed", "flat_primed")


def details(events, vertices):
    result = summarize(events)
    visits = sum(len({address >> 5 for address in range(row[3], row[3] + row[4])}) for row in events)
    result["demand_line_visits"] = visits
    result["repeated_demand_line_visits"] = visits - result["cached"]["unique_data_lines"]
    cache = [row for row in events if vertices <= row[3] < vertices + 128 * 32]
    result["vertex_cache"] = summarize(cache)["cached"]
    argb = [row for row in cache if (row[3] - vertices) % 32 == 24]
    assert all(row[4] == 4 for row in argb)
    result["argb"] = summarize(argb)["cached"]
    return result


class Machine(target_machine.Machine):
    def word(self, at): return int.from_bytes(self.bytes_at(at, 4), "little")

    def putword(self, at, value): self.map(at, int(value).to_bytes(4, "little"))

    def attach(self, symbols):
        self.layout = dict(zip(LAYOUT, (self.word(symbols["_fixture_layout"][0] + 4 * i) for i in range(len(LAYOUT)))))
        assert self.layout["version"] == 1
        self.hooks = {symbols["_" + name][0]: name for name in
                      ("fixture_part_edge", "fixture_color_edge", "fixture_light_edge")}
        self.colors, self.boundaries, self.light_calls, self.part_states = [], [], 0, []

    def step(self, pc, delay=False):
        opcode = self.fetch(pc)
        if opcode & 0xff00 == 0xca00:  # XOR #imm,R0; T is unchanged
            self.reg[0] ^= opcode & 255
            self.instruction_pcs.append(pc)
            self.steps += 1
            return pc + 2
        hook = self.hooks.get(pc) if hasattr(self, "hooks") else None
        if hook == "fixture_part_edge":
            pointer = self.reg[4]
            self.part_states.append(dict(primed=self.word(pointer + self.layout["primed"]),
                flat_primed=self.word(pointer + self.layout["flat_primed"]) if self.layout["flat_primed"] != 0xffffffff else None))
        elif hook == "fixture_light_edge":
            pointer, _, _, n = self.reg[4:8]
            vertices = self.word(pointer + self.layout["cache"])
            assert vertices == self.layout["vertices"]
            for i in range(n): self.putword(vertices + 32 * i + 24, 0xff2468ac)
            self.light_calls += 1
        elif hook == "fixture_color_edge":
            pointer, n = self.reg[4:6]
            vertices = self.word(pointer + self.layout["cache"])
            assert vertices == self.layout["vertices"]
            self.colors.append([self.word(vertices + 32 * i + 24) for i in range(n)])
            self.boundaries.append(len(self.instruction_pcs))
        return super().step(pc, delay)


def opcode_controls():
    for original in (0, 1, 255, 0x12345678, 0xffffffff):
        for immediate in (0, 1, 127, 255):
            machine = Machine()
            machine.map(0x100000, struct.pack("<H", 0xca00 | immediate))
            machine.reg[0], machine.t = original, 1
            machine.observe_start(); machine.step(0x100000); traffic = machine.observe_stop()
            assert machine.reg[0] == original ^ immediate and machine.t == 1
            assert machine.steps == len(machine.instruction_pcs) == 1 and not machine.memory_events
    return dict(status="PASS", cases=20, scope="XOR immediate decodes unsigned8-bit operand and preserves T; no memory access")


def load(path):
    program, symbols = target_machine.scalar.load_elf(path)
    machine = Machine()
    for address, data, _ in program: machine.map(address, data)
    machine.attach(symbols)
    return machine, symbols


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    build = json.loads(args.build.read_text())
    paths = {name: Path(row["elf"]) for name, row in build["arms"].items()}
    models = {}
    for name, path in paths.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == build["arms"][name]["sha256"]
        if not args.no_model: models[name] = pipeline_cost.Model(output / ("model-" + name), path, args.host_cc)
    cases = [(kind, meshlets, shape) for kind in range(6)
             for meshlets, shape in ((0, "repeat"), (1, "repeat"), (2, "repeat"), (4, "repeat"),
                                    (1, "wide"), (6, "wide"), (8, "growth"))]
    if args.quick: cases = [case for case in cases if case[0] in (0, 1, 2, 4) and case[1] in (0, 1, 4, 6) and case[2] != "growth"]
    rows = []
    for kind, meshlets, shape in cases:
        counts = ([8, 32, 16, 64, 24, 128, 64, 128] * 4 if shape == "growth" else [64 if shape == "wide" else 32] * 32)[:meshlets]
        for entry in ("submit", "chunk"):
            name = f"{entry}-k{kind}-n{meshlets}-{shape}"
            arms, semantics = {}, []
            for arm, path in paths.items():
                machine, symbols = load(path)
                machine.execute(symbols["_fixture_prepare"][0], kind)
                for i, n in enumerate(counts): machine.putword(machine.layout["counts"] + 4 * i, n)
                machine.colors, machine.boundaries, machine.light_calls, machine.part_states = [], [], 0, []
                machine.minimum_sp = machine.reg[15]
                machine.observe_start()
                machine.execute(symbols["_fixture_run_" + entry][0], meshlets)
                machine.observe_stop()
                assert len(machine.colors) == meshlets
                expected = [[((i * 7 & 255) << 24 if kind in (2, 3) else 0xff000000) |
                              (0x00123456 if kind & 1 else 0x002468ac) for i in range(n)] for n in counts]
                assert machine.colors == expected, (name, arm, "ARGB output mismatch")
                assert machine.light_calls == (meshlets if kind >= 4 else 0)
                assert machine.reg[0] == 0xff000000
                trace = SimpleNamespace(instruction_pcs=list(machine.instruction_pcs), steps=machine.steps, read=machine.read)
                boundaries = [0, *machine.boundaries, machine.steps]
                intervals = [details([event for event in machine.memory_events if start <= event[0] < end], machine.layout["vertices"])
                             for start, end in zip(boundaries, boundaries[1:])]
                row = dict(instructions=machine.steps, traffic=details(machine.memory_events, machine.layout["vertices"]),
                    peak_stack_bytes=machine.initial_regs[15] - machine.minimum_sp, part_size=machine.layout["part_size"],
                    argb_sha256=hashlib.sha256(b"".join(struct.pack("<I", word) for mesh in machine.colors for word in mesh)).hexdigest(),
                    observed_light_calls=machine.light_calls, intervals=intervals,
                    interval_line_touches=sum(interval["cached"]["unique_data_lines"] for interval in intervals),
                    interval_definition="Entry to first color edge; successive color edges; trailing return. Entry includes complete Part construction and retained-color setup.",
                    part_states=machine.part_states)
                if arm in models: row.update(price_helpers.price(models[arm], name, trace))
                arms[arm] = row
                semantics.append([machine.reg[0], machine.colors, machine.light_calls])
            assert all(value == semantics[0] for value in semantics)
            rows.append(dict(name=name, entry=entry, kind=kind, meshlets=meshlets, shape=shape, counts=counts, arms=arms))
            print("PASS", name, flush=True)
    report = dict(status="PASS", scope=__doc__, cases=rows,
        target_build_sha256=hashlib.sha256(args.build.read_bytes()).hexdigest(),
        memory_controls=target_machine.memory_controls(), opcode_controls=opcode_controls(),
        model={name: model.metadata() for name, model in models.items()},
        source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in
            (Path(__file__), REPLAY / "target_machine.py", REPLAY / "memory_trace.py", REPLAY / "pipeline_cost.py")})
    (output / "target-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("build", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--host-cc", default="gcc")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--no-model", action="store_true")
    result = run(parser.parse_args())
    print(json.dumps(dict(status=result["status"], cases=len(result["cases"]))))


if __name__ == "__main__":
    main()
