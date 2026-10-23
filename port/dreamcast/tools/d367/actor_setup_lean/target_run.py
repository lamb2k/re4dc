#!/usr/bin/env python3
"""Price compiled actor setup and observe target data loads/stores.

The real setup code calls observed AVK return edges. Geometry math, kernel
argument reads, TA submission and real model-ID lookup are excluded. Model
cycles assume perfect D-cache; cold-I means one initially cold 8 KiB I-cache
per complete sequence in this synthetic layout. Line counts are touches and
working sets, never inferred Dreamcast misses or hardware timings.
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
REPLAY = HERE.parent / "world_replay_lean"
sys.path.insert(0, str(REPLAY))
import target_machine
import pipeline_cost
from memory_trace import summarize
spec = importlib.util.spec_from_file_location("actor_existing_trace_price", REPLAY / "target_run.py")
price_helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(price_helpers)

LAYOUT = ("version", "part_size", "frame_size", "lights_size", "pos_size", "light_size",
    "part", "frame", "lights", "vertices", "outcodes", "positions", "normals", "uv", "records",
    "matrices", "directions", "position_ready", "direction_ready", "vertices_count", "signed_uv", "call_mask",
    "frame_screen", "lights_dir", "lights_color", "used", "input", "output", "primed", "streaming",
    "committed", "cache", "clip", "projection", "modelpart_size", "lights_fast", "lights_constant",
    "lights_count", "lights_rgb", "lights_source", "lights_viewdot")


class Machine(target_machine.Machine):
    def word(self, at, size=4):
        return int.from_bytes(self.bytes_at(at, size), "little")

    def putword(self, at, value, size=4):
        self.map(at, value.to_bytes(size, "little"))

    def attach(self, symbols, kernels):
        self.symbols = symbols
        self.layout = dict(zip(LAYOUT, (self.word(symbols["_fixture_layout"][0] + 4*i) for i in range(len(LAYOUT)))))
        assert self.layout["version"] == 1 and self.layout["pos_size"] == 72 and self.layout["light_size"] == 40
        self.hooks = {symbols["_" + name][0]: name for name in (*kernels, "fixture_part_edge", "fixture_lights_edge") if "_" + name in symbols}
        self.kernel_records, self.part_records, self.light_records, self.boundaries = [], [], [], []
        self.meshlet_boundaries = []

    def pointer(self, value):
        if not value:
            return None
        l = self.layout
        for name, size in (("part", l["modelpart_size"]), ("frame", l["frame_size"]), ("lights", l["lights_size"]),
            ("vertices", 128*32), ("outcodes", 128), ("positions", 128*8), ("normals", 128*8),
            ("uv", 128*4), ("records", 64*8), ("matrices", 4*16*4), ("directions", 4*12*4),
            ("position_ready", 4), ("direction_ready", 4)):
            if l[name] <= value < l[name] + size:
                return [name, value-l[name]]
        raise AssertionError(("unknown kernel pointer", hex(value)))

    def step(self, pc, delay=False):
        hook = self.hooks.get(pc) if hasattr(self, "hooks") else None
        if hook and hook.startswith("re4dc_avk_"):
            position = "_pos_" in hook
            count = 18 if position else 10
            args = [self.word(self.reg[4]+4*i) for i in range(count)]
            pointers = (0, 2, 3, 4, 5, 7, 8) if position else (0, 2, 3, 5, 6, 7)
            for index in pointers:
                args[index] = self.pointer(args[index])
            self.kernel_records.append(dict(kernel=hook, arguments=args))
            self.boundaries.append(len(self.instruction_pcs))
            if not position or self.word(self.layout["call_mask"]) == 1:
                self.meshlet_boundaries.append(len(self.instruction_pcs))
            self.reg[0] = 0  # an unchanged AVK kernel successfully consumed every record
        elif hook == "fixture_part_edge":
            at, l = self.reg[4], self.layout
            row = {name: self.word(at+l[name], 1 if name in ("streaming", "committed") else 4)
                   for name in ("used", "input", "output", "primed", "streaming", "committed")}
            assert all(row[name] == 0 for name in ("used", "input", "output", "committed")), row
            self.part_records.append(row)
        elif hook == "fixture_lights_edge":
            at, l = self.reg[4], self.layout
            row = {name: self.word(at+l[name], 1 if name in ("lights_fast", "lights_constant") else 4)
                   for name in ("lights_fast", "lights_constant", "lights_count", "lights_rgb")}
            row["dirs"] = self.bytes_at(at+l["lights_dir"], 48).hex()
            row["color"] = self.bytes_at(at+l["lights_color"], 64).hex()
            row["viewdot"] = self.bytes_at(at+l["lights_viewdot"], 12).hex()
            self.light_records.append(row)
        return super().step(pc, delay)


def load(path, kernels):
    program, symbols = target_machine.scalar.load_elf(path)
    machine = Machine()
    for address, data, _ in program:
        machine.map(address, data)
    machine.attach(symbols, kernels)
    return machine, symbols


def timed(machine, symbols, entry, argument=0):
    machine.kernel_records, machine.part_records, machine.light_records, machine.boundaries = [], [], [], []
    machine.meshlet_boundaries = []
    machine.minimum_sp = 0x500000
    machine.observe_start()
    machine.execute(symbols["_"+entry][0], argument)
    traffic = machine.observe_stop()
    pcs = list(machine.instruction_pcs)
    trace = SimpleNamespace(instruction_pcs=pcs, steps=len(pcs), read=machine.read)
    boundaries = [0, *machine.boundaries, len(pcs)]
    segments = [summarize([event for event in machine.memory_events if start <= event[0] < end])
                for start, end in zip(boundaries, boundaries[1:])]
    meshlet_boundaries = [0, *machine.meshlet_boundaries, len(pcs)]
    meshlet_lines = [summarize([event for event in machine.memory_events if start <= event[0] < end])["cached"]["unique_data_lines"]
                    for start, end in zip(meshlet_boundaries, meshlet_boundaries[1:])]
    row = dict(instructions=len(pcs), return_value=machine.reg[0], traffic=traffic,
        peak_stack_bytes=machine.initial_regs[15]-machine.minimum_sp,
        segment_data_line_touches=sum(x["cached"]["unique_data_lines"] for x in segments),
        segment_definition="Before first kernel, between kernel edges, trailing return; union reported separately",
        meshlet_interval_line_touches=sum(meshlet_lines), meshlet_interval_cached_lines=meshlet_lines,
        meshlet_interval_definition="Entry to first lighting edge, successive lighting edges, trailing exit; position-only uses position edges. Middle intervals each contain one complete meshlet's setup; entry/exit remain separately listed.",
        kernel_records=machine.kernel_records, part_records=machine.part_records, light_records=machine.light_records,
        symbol_instructions=pipeline_cost.symbol_costs(trace, symbols))
    return row, trace


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    build = json.loads(args.build.read_text())
    paths = {name: Path(row["elf"]) for name, row in build["arms"].items()}
    models = {}
    for name, path in paths.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == build["arms"][name]["sha256"]
        if not args.no_model:
            models[name] = pipeline_cost.Model(output/("model-"+name), path, args.host_cc)
    rows = []
    cases = [("run", kind, count, mask) for kind in range(4) for count in (0, 1, 2, 8, 32) for mask in (1, 2, 3)]
    cases += [("reset_lights", 0, 0, 0), ("constant_lights", 0, 0, 0), ("constant_lights", 1, 0, 0), ("palette_hit", 0, 1, 0),
              ("prime", 0, 0, 0), ("prime", 0, 32, 0), ("prime", 0, 128, 0)]
    if args.quick:
        cases = [case for case in cases if case[0] != "run" or (case[1] == 0 and case[2] in (0, 1, 8, 32) and case[3] == 3)]
    for entry, kind, count, mask in cases:
        name = f"{entry}-k{kind}-n{count}-m{mask}"
        results, semantics = {}, []
        for arm, path in paths.items():
            machine, symbols = load(path, build["observed_kernel_edges"])
            machine.execute(symbols["_fixture_prepare"][0], kind)
            if entry == "constant_lights":
                machine.execute(symbols["_fixture_prepare_lights"][0], kind)
            machine.putword(machine.layout["call_mask"], mask)
            row, trace = timed(machine, symbols, "fixture_"+entry, count)
            if entry == "run":
                expected = count * ((mask & 1 != 0) + (mask & 2 != 0))
                assert len(row["kernel_records"]) == expected, (name, expected, len(row["kernel_records"]))
                assert row["return_value"] == 32 * expected
                semantic = [row["return_value"], row["kernel_records"], row["part_records"]]
            elif entry == "palette_hit":
                semantic = machine.pointer(row["return_value"])
            else:
                semantic = [row["return_value"], row["part_records"], row["light_records"]] if entry in ("prime", "constant_lights") else None
            if arm in models:
                row.update(price_helpers.price(models[arm], name, trace))
            results[arm] = row
            semantics.append(semantic)
        assert all(value == semantics[0] for value in semantics), (name, "setup argument/state mismatch")
        rows.append(dict(name=name, entry=entry, kind=kind, meshlets=count, mask=mask, arms=results))
        (output/"progress.json").write_text(json.dumps(rows, indent=2)+"\n")
        print("PASS", name, flush=True)
    report = dict(status="PASS", scope=__doc__, cases=rows,
        target_build_sha256=hashlib.sha256(args.build.read_bytes()).hexdigest(),
        memory_controls=target_machine.memory_controls(),
        model={name: model.metadata() for name, model in models.items()},
        source_sha256={str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in (
            Path(__file__), Path(target_machine.__file__), Path(target_machine.scalar.__file__),
            REPLAY/"memory_trace.py", Path(pipeline_cost.__file__), REPLAY/"target_run.py")})
    (output/"target-controls.json").write_text(json.dumps(report, indent=2)+"\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--host-cc", default="gcc")
    parser.add_argument("--no-model", action="store_true")
    parser.add_argument("--quick", action="store_true")
    result = run(parser.parse_args())
    print(json.dumps(dict(status=result["status"], cases=len(result["cases"]))))


if __name__ == "__main__":
    main()
