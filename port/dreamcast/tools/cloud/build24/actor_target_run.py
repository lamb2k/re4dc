#!/usr/bin/env python3
"""Execute and price actual compiled actor clip reconstruction OFF/ON.

The timed entry includes full Part construction and Part::clip_strip. The
unchanged shared clipper exposes every prepared vertex/opacity byte then returns
zero, so clipping arithmetic, nonempty TA output and devices are excluded. The
same observed edge is used for both arms. Synthetic rigid, skinned and stride-6
source inputs cover near-crossing and far-depth strips, without game assets.
Warm/cold-I scheduling estimates assume perfect D-cache and a synthetic code
layout. Data load/store and 32-byte line visits are observed addresses, not
cache misses, bus traffic, console time or a whole-frame speedup estimate.
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
DC = HERE.parents[2]
ROOT = DC.parents[1]
REPLAY = DC / "tools/d367/world_replay_lean"
sys.path.insert(0, str(REPLAY))
import target_machine
import pipeline_cost
from memory_trace import summarize
spec = importlib.util.spec_from_file_location("b24_actor_price", REPLAY / "target_run.py")
price_helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(price_helpers)

LAYOUT = ("version", "part_size", "frame_size", "render_vertex_size", "positions",
          "normals", "palette", "records", "cache", "indices", "colors")
KINDS = ("rigid-near", "skin-near", "rigid-far", "skin-far", "source6-near")


class Machine(target_machine.Machine):
    def word(self, at):
        return int.from_bytes(self.bytes_at(at, 4), "little")

    def attach(self, symbols):
        at = symbols["_fixture_layout"][0]
        self.layout = dict(zip(LAYOUT, (self.word(at + 4 * i) for i in range(len(LAYOUT)))))
        assert self.layout["version"] == 1 and self.layout["render_vertex_size"] == 52
        self.edge = symbols["_fixture_clip_edge"][0]
        self.forbidden = {symbols[name][0] for name in ("_sq_fast_cpy", "_re4dc_model_packet_commit")
                          if name in symbols}
        self.prepared, self.boundaries = [], []

    def step(self, pc, delay=False):
        assert pc not in self.forbidden, "excluded nonempty TA/device edge executed"
        opcode = self.fetch(pc)
        if opcode & 0xff00 == 0xca00:  # XOR #imm,R0; T is unchanged.
            self.reg[0] ^= opcode & 255
            self.instruction_pcs.append(pc)
            self.steps += 1
            return pc + 2
        if pc == self.edge:
            self.prepared.append(self.bytes_at(self.reg[4], 3 * self.layout["render_vertex_size"])
                                 + self.bytes_at(self.reg[5], 12))
            self.boundaries.append(len(self.instruction_pcs))
        return super().step(pc, delay)


def opcode_controls():
    for original in (0, 1, 255, 0x12345678, 0xffffffff):
        for immediate in (0, 1, 127, 255):
            machine = Machine()
            machine.edge, machine.forbidden = -1, set()
            machine.map(0x100000, struct.pack("<H", 0xca00 | immediate))
            machine.reg[0], machine.t = original, 1
            machine.observe_start(); machine.step(0x100000); machine.observe_stop()
            assert machine.reg[0] == original ^ immediate and machine.t == 1
            assert machine.steps == len(machine.instruction_pcs) == 1 and not machine.memory_events
    return dict(status="PASS", cases=20, scope="XOR unsigned8-bit immediate preserves T and performs no memory access")


def load(path):
    program, symbols = target_machine.scalar.load_elf(path)
    machine = Machine()
    for address, data, _ in program:
        machine.map(address, data)
    machine.attach(symbols)
    return machine, symbols


def traffic(events, layout, kind):
    result = summarize(events)
    visits = sum(len({address >> 5 for address in range(row[3], row[3] + row[4])}) for row in events)
    result["demand_line_visits"] = visits
    result["repeated_demand_line_visits"] = visits - result["cached"]["unique_data_lines"]
    result["input_regions"] = {}
    sizes = {"positions": (6 if kind == 4 else 8) * 128, "normals": 4 * 128,
             "palette": 36 * 4, "records": 128 * 4 * 2, "cache": 132 * 32,
             "indices": 128, "colors": 128 * 4}
    for key, size in sizes.items():
        selected = [event for event in events if layout[key] <= event[3] < layout[key] + size]
        result["input_regions"][key] = summarize(selected)["cached"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("build", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--host-cc", default="gcc")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--no-model", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    build = json.loads(args.build.read_text())
    paths = {name: Path(row["elf"]) for name, row in build["arms"].items()}
    models = {}
    for name, path in paths.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == build["arms"][name]["sha256"]
        if not args.no_model:
            models[name] = pipeline_cost.Model(output / ("model-" + name), path, args.host_cc)
    rows = []
    lengths = (3, 16) if args.quick else (3, 4, 16, 64, 128)
    for kind, description in enumerate(KINDS):
        for length in lengths:
            name = f"{description}-n{length}"
            arms, semantics = {}, []
            for arm, path in paths.items():
                machine, symbols = load(path)
                machine.execute(symbols["_fixture_prepare"][0], kind)
                machine.minimum_sp = machine.reg[15]
                machine.observe_start()
                machine.execute(symbols["_fixture_run"][0], length)
                machine.observe_stop()
                assert machine.reg[0] == 1 and len(machine.prepared) == length - 2
                # Observe all bytes, including retained strip parity and alpha.
                # No host observer reads are included in the memory trace.
                prepared = b"".join(machine.prepared)
                digest = hashlib.sha256(prepared).hexdigest()
                trace = SimpleNamespace(instruction_pcs=list(machine.instruction_pcs),
                                        steps=machine.steps, read=machine.read)
                row = dict(instructions=machine.steps,
                    traffic=traffic(machine.memory_events, machine.layout, kind),
                    peak_stack_bytes=machine.initial_regs[15] - machine.minimum_sp,
                    prepared_triangles=len(machine.prepared), prepared_bytes=len(prepared),
                    prepared_sha256=digest, first_prepared_triangle_hex=machine.prepared[0].hex(),
                    part_size=machine.layout["part_size"], frame_size=machine.layout["frame_size"])
                if arm in models:
                    row.update(price_helpers.price(models[arm], name, trace))
                arms[arm] = row
                semantics.append(prepared)
            assert semantics[0] == semantics[1], (name, "actual prepared vertex/opacity bytes differ")
            rows.append(dict(name=name, kind=description, vertices=length,
                triangles=length - 2, rebuilds_off=3 * (length - 2), rebuilds_on=length, arms=arms))
            print("PASS", name, flush=True)
    sources = (Path(__file__), REPLAY / "target_machine.py", REPLAY / "sh4_machine.py",
               REPLAY / "memory_trace.py", REPLAY / "pipeline_cost.py", REPLAY / "target_run.py")
    report = dict(status="PASS", scope=__doc__, cases=rows,
        target_build_sha256=hashlib.sha256(args.build.read_bytes()).hexdigest(),
        memory_controls=target_machine.memory_controls(), opcode_controls=opcode_controls(),
        model={name: model.metadata() for name, model in models.items()},
        source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources})
    destination = output / "actor-target-run.json"
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", cases=len(rows), receipt=str(destination))))


if __name__ == "__main__":
    main()
