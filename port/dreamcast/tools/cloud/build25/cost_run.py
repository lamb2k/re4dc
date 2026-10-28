#!/usr/bin/env python3
"""Observe real compiled Build25 light instructions on bounded synthetic data.

Warm/cold-I cycles are the existing hwsim scheduling model with perfect D-cache.
Loads/stores and 32-byte demand lines are real executed operand addresses, not
cache misses or bus traffic. Every reference light is at unit distance; the
existing qualified FSRRA(1) implementation suffices for ACTOR_EXACT_FAST=1.
This does not emulate general SH4 approximate reciprocal values or a game scene.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
spec = importlib.util.spec_from_file_location("b25_kernel", DC / "tools/d367/actor_bytes_lean/kernel_audit.py")
kernel = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = kernel
spec.loader.exec_module(kernel)
LAYOUT = ("version", "part_bytes", "frame_bytes", "lights_bytes", "source_bytes",
          "source_part_bytes",
          "part", "frame", "source", "lights", "positions", "normals", "records", "cache", "colors",
          "argb_offset", "constant_rgb_offset")
KINDS = ("vertex-colour", "material-scale", "eight-lights", "diffuse-unclamped", "leon-low-material")


class Machine(kernel.Machine):
    def step(self, pc, delay=False):
        opcode = self.fetch(pc)
        if opcode & 0xf0ff == 0xf03d:  # FTRC FRn,FPUL, positive finite Q16 gains.
            value = self.fp_value((opcode >> 8) & 15)
            # Same toward-zero scalar operation as the existing qualified
            # kernel interpreter, widening only its fixture input range.
            # NaNs, infinities, negatives and signed overflow fail closed.
            assert math.isfinite(value) and 0 <= value < 0x80000000
            self.fpul = int(value)
            self.instruction_pcs.append(pc)
            self.steps += 1
            return pc + 2
        if opcode & 0xff00 == 0xca00:  # XOR #imm,R0; unchanged T.
            self.reg[0] ^= opcode & 255
            self.instruction_pcs.append(pc)
            self.steps += 1
            return pc + 2
        return super().step(pc, delay)


def conversion_controls():
    cases = (0.0, 0.5, 1.0, 255.75, 65535.5, 65536.5, 16776960.0, 2147483520.0)
    for value in cases:
        m = Machine()
        m.map(0x100000, struct.pack("<H", 0xf53d))
        m.sf(5, kernel.target_machine.scalar.base.fbits(value))
        m.t = 1
        before = m.f(5)
        m.observe_start(); m.step(0x100000); m.observe_stop()
        assert m.fpul == int(value) and m.f(5) == before and m.t == 1
        assert m.steps == 1 and m.instruction_pcs == [0x100000] and not m.memory_events
    for value in (-1.0, float("nan"), float("inf"), 2147483648.0):
        m = Machine()
        m.map(0x100000, struct.pack("<H", 0xf53d))
        m.sf(5, kernel.target_machine.scalar.base.fbits(value))
        try:
            m.step(0x100000)
        except AssertionError:
            continue
        raise AssertionError("unqualified FTRC input admitted")
    return dict(status="PASS", accepted_cases=len(cases), refused_cases=4,
                scope="Existing FTRC toward-zero operation over finite nonnegative values below signed32 overflow; preserves FR/T and has no memory effect. General exceptional FPU behavior untested.")


def read_u32(machine, address):
    return int.from_bytes(machine.bytes_at(address, 4), "little")


def load(path):
    program, symbols = kernel.target_machine.scalar.load_elf(path)
    machine = Machine()
    for address, data, _ in program:
        machine.map(address, data)
    at = symbols["_fixture_layout"][0]
    layout = dict(zip(LAYOUT, struct.unpack("<" + "I" * len(LAYOUT), machine.bytes_at(at, 4 * len(LAYOUT)))))
    assert layout["version"] == 2 and layout["argb_offset"] == 24
    return machine, symbols, layout


def traffic(events, layout):
    result = kernel.summarize(events)
    visits = sum(len({address >> 5 for address in range(row[3], row[3] + row[4])}) for row in events)
    result["demand_line_visits"] = visits
    result["repeated_demand_line_visits"] = visits - result["cached"]["unique_data_lines"]
    sizes = {"part": layout["source_part_bytes"], "frame": layout["frame_bytes"],
             "source": layout["source_bytes"], "lights": layout["lights_bytes"],
             "positions": 128 * 8, "normals": 128 * 4, "records": 128 * 8,
             "cache": 128 * 32, "colors": 128 * 4}
    result["regions"] = {}
    for key, size in sizes.items():
        selected = [row for row in events if layout[key] <= row[3] < layout[key] + size]
        result["regions"][key] = kernel.summarize(selected)["cached"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--no-model", action="store_true")
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    build = json.loads(args.build.read_text())
    paths = {name: Path(row["elf"]) for name, row in build["arms"].items()}
    models = {}
    for arm, path in paths.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == build["arms"][arm]["sha256"]
        if not args.no_model:
            models[arm] = kernel.pipeline_cost.Model(out / ("model-" + arm), path)
    rows = []
    for kind, description in enumerate(KINDS):
        lengths = (16,) if args.quick else (16, 64, 128)
        for n in lengths:
            phases = {}
            for arm, path in paths.items():
                m, symbols, layout = load(path)
                m.execute(symbols["_fixture_prepare"][0], kind)
                # Fold/prepare and pass are priced separately. Preparation is
                # included in the old declining fold's cost.
                for phase, argument in (("fold", 0), ("pass", n)):
                    m.minimum_sp = m.reg[15]
                    m.observe_start()
                    m.execute(symbols["_fixture_" + phase][0], argument)
                    m.observe_stop()
                    observed = traffic(m.memory_events, layout)
                    if phase == "fold":
                        assert m.reg[0] == int(arm == "fast"), (description, arm, "unexpected old/new fold decision", m.reg[0])
                    else:
                        words = [read_u32(m, layout["cache"] + 32 * i + layout["argb_offset"]) for i in range(n)]
                        assert all(word >> 24 == 80 + i for i, word in enumerate(words)), (description, arm, "alpha changed")
                        if arm == "fast":
                            for field in ("positions", "normals"):
                                assert observed["regions"][field]["load_instructions"] == 0, (description, field, "per-vertex geometry read by flat pass")
                            if kind != 0:
                                assert len({word & 0xffffff for word in words}) == 1, (description, "flat part RGB varies")
                            else:
                                assert len({word & 0xffffff for word in words}) > 1 and (words[0] & 255) == 0
                    trace = SimpleNamespace(instruction_pcs=list(m.instruction_pcs), steps=m.steps, read=m.read)
                    row = dict(arm=arm, phase=phase, instructions=m.steps,
                               peak_stack_bytes=m.initial_regs[15] - m.minimum_sp, traffic=observed,
                               lights_bytes=layout["lights_bytes"], part_bytes=layout["part_bytes"])
                    row["synthetic_identity_hook_calls"] = {name: m.instruction_pcs.count(symbols[name][0])
                        for name in ("_re4dc_actor_model_id", "_re4dc_actor_obj_id") if name in symbols}
                    if phase == "pass":
                        row["output_sha256"] = hashlib.sha256(struct.pack("<" + "I" * n, *words)).hexdigest()
                        row["first_argb"] = f"{words[0]:08x}"
                    if arm in models:
                        row.update(kernel.price_helpers.price(models[arm], f"{description}-n{n}-{phase}", trace))
                    if phase == "pass" and arm == "fast":
                        m.execute(symbols["_fixture_read_stats"][0], 0)
                        stats = struct.unpack("<9I", m.bytes_at(symbols["_fixture_stats"][0], 36))
                        assert stats[0] == 1 and stats[1] == 0, (description, "fallback invariant", stats)
                        expected_reason = (0, 1, 2, 1, 1)[kind]
                        assert stats[2 + expected_reason] == 1, (description, "former decline reason absent", stats)
                        assert stats[7:9] == ((0, n) if kind == 0 else (n, 0)), (description, "vertex census", stats)
                        row["stats"] = dict(parts=stats[0], fallback_parts=stats[1], avoided=list(stats[2:7]),
                                             flat_vertices=stats[7], multiply_vertices=stats[8])
                    phases[arm + "-" + phase] = row
            rows.append(dict(case=description, input_vertices=n, phases=phases))
            print("PASS", description, n, flush=True)
    scenarios = []
    if not args.no_model:
        for row in rows:
            if row["input_vertices"] != (16 if args.quick else 128):
                continue
            parts = 42
            totals = {}
            for arm in paths:
                per_part = row["phases"][arm + "-fold"]["model_cycles"] + row["phases"][arm + "-pass"]["model_cycles"]
                totals[arm] = dict(cycles=parts * per_part, modelled_lighting_ms=parts * per_part / 200000.0)
            delta = totals["fast"]["modelled_lighting_ms"] - totals["exact"]["modelled_lighting_ms"]
            scenarios.append(dict(label="MODELLED", case=row["case"], parts=parts,
                                  input_vertices_per_part=row["input_vertices"], cpu_mhz=200, lighting=totals,
                                  lighting_delta_ms=delta,
                                  assumed_other_frame_work_ms=30.0,
                                  modelled_exact_whole_frame_ms=30.0 + totals["exact"]["modelled_lighting_ms"],
                                  modelled_fast_whole_frame_ms=30.0 + totals["fast"]["modelled_lighting_ms"],
                                  assumptions="Synthetic sensitivity only: T_frame = ASSUMED 30 ms other work + 42 copies of this 128-input-vertex lighting fixture (16 in --quick). The same other work is held constant in both arms. No measured room total or character budget is used; real parts, vertices, materials, drawing cadence and overlap are unknown."))
    sources = [Path(__file__), HERE / "cost_build.py", HERE / "cost_fixture.cpp.in", HERE / "cost_identity.cpp.in",
               DC / "tools/d367/actor_bytes_lean/kernel_audit.py", *[DC / "tools/d367/world_replay_lean" / (name + ".py")
                 for name in ("target_machine", "sh4_machine", "memory_trace", "pipeline_cost", "target_run")]]
    report = dict(status="PASS", scope=__doc__, cases=rows, modelled_frame_scenarios=scenarios,
                  target_build_sha256=hashlib.sha256(args.build.read_bytes()).hexdigest(),
                  model={name: model.metadata() for name, model in models.items()},
                  memory_controls=kernel.target_machine.memory_controls(), arithmetic_controls=kernel.kernel_controls(),
                  conversion_controls=conversion_controls(),
                  source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
                  limitations="Synthetic rigid inputs and actual production light routines only. Separately compiled identity hook instructions are included and calls counted; actual model_bridge lookup cost is unpriced. Draw-list traversal, deformation, transforms, clipping, TA output, DMA, scheduling interruptions, device stalls and real D-cache misses are excluded. Cold-I costs depend on the fixture's code layout. No full-frame or private visual/gameplay acceptance.")
    (out / "target-cost.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", cases=len(rows), receipt=str(out / "target-cost.json"))))


if __name__ == "__main__":
    main()
