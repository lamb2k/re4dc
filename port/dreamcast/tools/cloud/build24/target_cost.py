#!/usr/bin/env python3
"""Actual SH4 Build24 observer instructions on bounded synthetic states.

Production accounting is unchanged. Clock, thread, identity and PMU-read hooks
are deterministic fixture functions; real timer/PMU/OS work is unpriced. Model
cycles use perfect D-cache and both warm and initially cold I-cache. Memory
traffic is architectural accesses/32-byte lines, not hardware cache misses.
"""
import argparse
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


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


build = module("dsa24_build", HERE / "build_controls.py")
profile = build.profile
kernel = module("dsa24_kernel", DC / "tools/d367/actor_bytes_lean/kernel_audit.py")
LAYOUT = ("argument_bytes", "snapshot_bytes", "frame_bytes", "current", "window", "state", "epoch",
          "owner", "paused", "have_key", "have_sealed", "key", "clock", "thread", "identity",
          "begin_at", "last_at", "tick_at", "active_at", "complete_at", "attempt_at", "finished_at",
          "phase_us_at", "phase_events_at", "counters_at", "outside_us_at", "wall_us_at", "ticks_at",
          "drawn_at", "errors_at", "pm_samples_at", "pm_gaps_at", "pm_wraps_at")
PM_LAYOUT = ("previous_pm", "have_pm", "sample", "sample_valid")


class ObserverMachine(kernel.Machine):
    def step(self, pc, delay=False):
        opcode = self.fetch(pc)
        if opcode & 0xff00 == 0xca00:  # XOR #imm,R0; emitted for boolean !attempt.
            self.reg[0] ^= opcode & 255
            self.instruction_pcs.append(pc)
            self.steps += 1
            return pc + 2
        return super().step(pc, delay)


def scalar_controls():
    m = ObserverMachine()
    m.map(0x1000, struct.pack("<H", 0xca5a))
    m.reg[0], m.t = 0x87654321, 1
    m.observe_start()
    assert m.step(0x1000) == 0x1002
    m.observe_stop()
    assert m.reg[0] == (0x87654321 ^ 0x5a) and m.t == 1
    assert m.steps == 1 and m.instruction_pcs == [0x1000] and not m.memory_events
    return ["XOR immediate zero-extends eight-bit operand, preserves T, and creates no data access"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    paths = [Path(__file__), HERE / "cost_fixture.cpp.in", HERE / "cost_hooks.cpp.in", HERE / "build_controls.py",
             DC / "game/draw_setup_audit.cpp", DC / "game/platform/include/draw_setup_audit.h",
             DC / "game/platform/include/perf_phase_miss.h", DC / "game/platform/include/perf_phase_accounting.hpp",
             DC / "tools/d367/actor_bytes_lean/kernel_audit.py",
             *[DC / ("tools/d367/world_replay_lean/" + name + ".py") for name in
               ("target_machine", "sh4_machine", "memory_trace", "pipeline_cost", "target_run")]]
    frozen = {str(path.relative_to(ROOT)): profile.sha(path) for path in paths}
    rows, configurations = [], {}
    for pmu in (False, True):
        name = "time-pmu" if pmu else "time"
        destination = out / name
        destination.mkdir()
        options = build.QA + ["DRAW_SETUP_AUDIT=1"]
        if pmu:
            options += ["WORLD_CENSUS24=1", "PERF_PHASE_MISS=1", "PERF_PHASE_MISS_EVENT=15"]
        flags, receipt, sources = profile.derive(destination / "profile", cxx, kos, sdk, options,
                                                  units=("draw_setup_audit",))
        builder = profile.Build(destination)
        fixture, obj, elf = destination / "fixture.cpp", destination / "fixture.o", destination / "fixture.elf"
        fixture.write_text((HERE / "cost_fixture.cpp.in").read_text().replace("@DC@", str(DC)))
        builder.run([*flags["draw_setup_audit"], "-c", "-fstack-usage", fixture, "-o", obj], label="fixture")
        hooks, hooks_obj = destination / "hooks.cpp", destination / "hooks.o"
        hooks.write_text((HERE / "cost_hooks.cpp.in").read_text().replace("@DC@", str(DC)))
        builder.run([*flags["draw_setup_audit"], "-c", "-fstack-usage", hooks, "-o", hooks_obj], label="hooks")
        production = destination / "production.o"
        builder.run([*flags["draw_setup_audit"], "-c", "-fstack-usage", sources["draw_setup_audit"], "-o", production], label="production")
        linker = destination / "fixture.ld"
        linker.write_text("SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }\n"
                          ". = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n")
        roots = ("fixture_enter", "fixture_nested", "fixture_leave", "fixture_phase", "fixture_count",
                 "fixture_next_tick", "fixture_layout", "fixture_layout_count")
        builder.run([cxx, "-m4-single", "-ml", "-nostartfiles", "-Wl,--gc-sections", "-Wl,-T," + str(linker),
                     "-Wl,-e,_fixture_enter", *["-Wl,-u,_" + root for root in roots], obj, hooks_obj, "-o", elf], label="link")
        prefix = str(cxx).removesuffix("g++")
        (destination / "disassembly.txt").write_bytes(builder.run([prefix + "objdump", "-d", "-C", elf], label="disassembly"))
        program, symbols = kernel.target_machine.scalar.load_elf(elf)
        model = kernel.pipeline_cost.Model(destination / "model", elf)

        def machine():
            result = ObserverMachine()
            for address, data, _ in program:
                result.map(address, data)
            return result

        seed = machine()
        count = int.from_bytes(seed.bytes_at(symbols["_fixture_layout_count"][0], 4), "little")
        fields = LAYOUT + (PM_LAYOUT if pmu else ())
        assert count == len(fields), (count, len(fields))
        layout = dict(zip(fields, struct.unpack("<" + "I" * count, seed.bytes_at(symbols["_fixture_layout"][0], 4 * count))))
        assert layout["argument_bytes"] == 28
        cases = (
            dict(case="enter-path", entry="fixture_enter", state=0, after=84, returned=65536, outside=100, sample=True),
            dict(case="enter-nested-clip", entry="fixture_nested", state=65, after=145, returned=65601, phase=100, sample=True),
            dict(case="leave-path", entry="fixture_leave", state=65, after=0, phase=100, sample=True),
            dict(case="same-phase", entry="fixture_phase", state=65, after=65, argument_phase=0),
            dict(case="change-phase", entry="fixture_phase", state=65, after=81, phase=100, sample=True),
            dict(case="count-24-triangles", entry="fixture_count", state=65, after=65, counter=24),
            dict(case="inactive-enter", entry="fixture_enter", state=0, after=0, returned=0xffffffff, active=0),
            dict(case="next-completed-tick", entry="fixture_next_tick", state=0, after=0, finish=True, sample=True),
        )
        for case in cases:
            m = machine()
            put = lambda address, value, size=4: m.map(address, value.to_bytes(size, "little"))
            get = lambda address, size=4: int.from_bytes(m.bytes_at(address, size), "little")
            current = layout["current"]
            m.map(current, bytes(layout["frame_bytes"]))
            m.map(layout["window"], bytes(layout["snapshot_bytes"]))
            for field, value in (("state", case["state"]), ("epoch", 1), ("owner", 1), ("thread", 1)):
                put(layout[field], value)
            put(layout["clock"], 200, 8)
            put(current + layout["begin_at"], 0, 8)
            put(current + layout["last_at"], 100, 8)
            put(current + layout["tick_at"], 17)
            put(current + layout["active_at"], case.get("active", 1), 1)
            put(layout["have_key"], 1, 1)
            identity = struct.pack("<7I", 0x103, 1, 2, 3, 4, 5, 6)
            m.map(layout["key"], identity)
            m.map(layout["identity"], identity)
            if case.get("finish"):
                for field in ("complete_at", "attempt_at", "finished_at"):
                    put(current + layout[field], 1, 1)
                put(current + layout["phase_us_at"], 50, 8)
                put(current + layout["outside_us_at"], 50, 8)
            if pmu:
                m.map(layout["previous_pm"], struct.pack("<QIII", 0, 1, 15, 1))
                m.map(layout["sample"], struct.pack("<QIII", 100, 1, 15, 1))
                put(layout["have_pm"], 1, 1)
                put(layout["sample_valid"], 1, 1)
            m.map(0x9000, struct.pack("<7I", 3, case.get("argument_phase", 1), 2, 24, 65536, 18, 0x103))
            m.minimum_sp = m.reg[15]
            m.observe_start()
            m.execute_kernel(symbols["_" + case["entry"]][0], 0x9000)
            m.observe_stop()
            assert symbols["_snprintf"][0] not in m.instruction_pcs, "unpriced formatting branch executed"
            assert get(layout["state"]) == case["after"], (name, case, get(layout["state"]))
            if "returned" in case:
                assert m.reg[0] == case["returned"], (name, case, m.reg[0])
            if case.get("finish"):
                window = layout["window"]
                assert get(window + layout["ticks_at"]) == get(window + layout["drawn_at"]) == 1
                assert get(window + layout["wall_us_at"], 8) == 200
                assert get(window + layout["phase_us_at"], 8) == 50
                assert get(window + layout["outside_us_at"], 8) == 150
                assert get(current + layout["tick_at"]) == 18 and get(current + layout["last_at"], 8) == 200
            else:
                assert get(current + layout["phase_us_at"], 8) == case.get("phase", 0)
                assert get(current + layout["outside_us_at"], 8) == case.get("outside", 0)
                assert get(current + layout["counters_at"] + 16, 8) == case.get("counter", 0)
            assert get(current + layout["errors_at"]) == 0
            if pmu:
                snapshot = layout["window"] if case.get("finish") else current
                assert get(snapshot + layout["pm_samples_at"]) == int(case.get("sample", False))
                assert get(snapshot + layout["pm_gaps_at"]) == get(snapshot + layout["pm_wraps_at"]) == 0
            traffic = kernel.traffic_details(m.memory_events, m.prefetch_events)
            regions = {}
            for event in m.memory_events:
                address = event[3]
                region = ("stack" if address >= 0x4f0000 else "fixture-arguments" if 0x9000 <= address < 0x9100
                          else "observer-and-literals")
                regions.setdefault(region, []).append(event)
            traffic["regions"] = {region: kernel.summarize(events) for region, events in regions.items()}
            hooks = {hook: m.instruction_pcs.count(symbols["_re4dc_dsa24_test_" + hook][0])
                     for hook in ("clock", "thread", "identity") if "_re4dc_dsa24_test_" + hook in symbols}
            if pmu:
                sample_symbol = next(symbol for symbol in symbols if "read_audit_sample" in symbol)
                hooks["pmu_sample"] = m.instruction_pcs.count(symbols[sample_symbol][0])
            trace = SimpleNamespace(instruction_pcs=list(m.instruction_pcs), steps=m.steps, read=m.read)
            priced = kernel.price_helpers.price(model, case["case"], trace)
            rows.append(dict(configuration=name, case=case["case"], entry=case["entry"], instructions=m.steps,
                             peak_stack_bytes=m.initial_regs[15] - m.minimum_sp, traffic=traffic,
                             synthetic_hook_calls=hooks, **priced))
            print("PASS", name, case["case"], flush=True)
        configurations[name] = dict(profile_receipt=receipt, flags=flags["draw_setup_audit"],
                                    fixture_elf_sha256=profile.sha(elf), fixture_sections=profile.sections(elf),
                                    production_object=dict(sha256=profile.sha(production), **profile.sections(production),
                                                           stack_usage=profile.stack_usage(production.with_suffix(".su"))),
                                    fixture_stack_usage=profile.stack_usage(obj.with_suffix(".su")), target_layout=layout,
                                    model=model.metadata())
    scenarios = []
    for configuration in configurations:
        by = {row["case"]: row for row in rows if row["configuration"] == configuration}
        for scopes, phases, counts in ((1000, 200, 2000), (5000, 1000, 10000)):
            frequencies = {"enter-path": scopes, "leave-path": scopes, "change-phase": phases,
                           "count-24-triangles": counts, "next-completed-tick": 1}
            cycles = sum(by[case]["model_cycles"] * frequency for case, frequency in frequencies.items())
            hooks = {hook: sum(by[case]["synthetic_hook_calls"].get(hook, 0) * frequency for case, frequency in frequencies.items())
                     for hook in ("clock", "thread", "identity", "pmu_sample")}
            scenarios.append(dict(configuration=configuration, assumed_calls_per_drawn_frame=frequencies,
                                  assumed_cpu_mhz=200, modelled_core_ms=cycles / 200000.0, synthetic_hook_calls=hooks,
                                  scope="MODELLED synthetic counts, one completed tick per draw. Includes stub instructions. Add real timer/PMU/identity/thread costs, adapter bookkeeping, window seal/format and cache/bus/interrupt costs; not a complete observer or farm-frame estimate."))
    assert frozen == {str(path.relative_to(ROOT)): profile.sha(path) for path in paths}, "source changed; rerun"
    report = dict(status="PASS", scope=__doc__, source_sha256=frozen, configurations=configurations,
                  cases=rows, modelled_frame_scenarios=scenarios, memory_controls=kernel.target_machine.memory_controls(),
                  scalar_controls=scalar_controls(),
                  limitations="No private assets, scene/emulator/console capture or measured cache/PMU miss counts. Production core is compiled separately for real code/static-stack sizes. Execution uses the documented host hooks and a never-executed snprintf link stub. Window sealing/formatting, timer/PMU/OS hook implementations and surrounding renderer/PM14 overhead remain unpriced.")
    (out / "target-cost.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", cases=len(rows), receipt=str(out / "target-cost.json"))))


if __name__ == "__main__":
    main()
