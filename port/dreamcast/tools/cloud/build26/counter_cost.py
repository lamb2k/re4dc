#!/usr/bin/env python3
"""Execute the actual Build26 counter core on bounded synthetic SH4 states.

Inline hit, begin, seal and snapshot instructions come from production source.
There are no clock, OS, allocation or formatting stubs in these executed paths.
The instruction model has perfect D-cache; warm and cold-I costs are separate.
Operand/32-byte-line counts describe architectural accesses, not cache misses.
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
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


controls = module("b26_counter_controls", HERE / "build_controls.py")
profile = controls.profile
kernel = module("b26_counter_kernel", DC / "tools/d367/actor_bytes_lean/kernel_audit.py")
LAYOUT = ("version", "reason_count", "snapshot_bytes", "active", "live", "overflow", "sealed",
          "tick", "room", "drawn", "sequence", "valid", "paused", "have_room", "output")


class CounterMachine(kernel.Machine):
    def step(self, pc, delay=False):
        opcode = self.fetch(pc)
        if opcode & 0xff00 == 0xca00:  # Same immediate-XOR operation qualified by Build24.
            self.reg[0] ^= opcode & 255
            self.instruction_pcs.append(pc)
            self.steps += 1
            return pc + 2
        return super().step(pc, delay)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    sources = [Path(__file__), HERE / "counter_fixture.cpp.in", HERE / "build_controls.py",
               DC / "game/draw_fallback_audit.cpp", DC / "game/platform/include/draw_fallback_audit.h",
               *[DC / "game/platform/include" / ("draw_fallback_" + name + ".def") for name in ("world", "model", "other")],
               DC / "tools/d367/actor_bytes_lean/kernel_audit.py",
               *[DC / ("tools/d367/world_replay_lean/" + name + ".py") for name in
                 ("target_machine", "sh4_machine", "memory_trace", "pipeline_cost", "target_run")]]
    frozen = {str(path.relative_to(ROOT)): profile.sha(path) for path in sources}
    options = controls.QA + ["DRAW_FALLBACK_AUDIT=1", "QA_LINK=0"]
    flags, receipt, production_sources = profile.derive(out / "profile", cxx, kos, sdk, options,
                                                       units=("draw_fallback_audit",))
    command = flags["draw_fallback_audit"]
    assert "-DRE4DC_DRAW_FALLBACK_AUDIT=1" in command, "Make lost enabled audit control"
    builder = profile.Build(out)
    fixture, obj, elf = out / "fixture.cpp", out / "fixture.o", out / "fixture.elf"
    fixture.write_text((HERE / "counter_fixture.cpp.in").read_text().replace("@DC@", str(DC)))
    builder.run([*command, "-fstack-usage", "-c", fixture, "-o", obj], label="fixture")
    production = out / "production.o"
    builder.run([*command, "-fstack-usage", "-c", production_sources["draw_fallback_audit"], "-o", production], label="production")
    script = out / "fixture.ld"
    script.write_text("SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }\n"
                      ". = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n")
    roots = ("fixture_hit_one", "fixture_hit_amount", "fixture_hit_last", "fixture_begin", "fixture_end",
             "fixture_snapshot", "fixture_layout")
    builder.run([cxx, "-m4-single", "-ml", "-nostartfiles", "-Wl,--gc-sections", "-Wl,-T," + str(script),
                 "-Wl,-e,_fixture_hit_one", *["-Wl,-u,_" + root for root in roots], obj, "-o", elf], label="link")
    prefix = str(cxx).removesuffix("g++")
    (out / "disassembly.txt").write_bytes(builder.run([prefix + "objdump", "-d", "-C", elf], label="disassembly"))
    program, symbols = kernel.target_machine.scalar.load_elf(elf)
    model = kernel.pipeline_cost.Model(out / "model", elf)

    def machine():
        result = CounterMachine()
        for address, data, _ in program:
            result.map(address, data)
        return result

    seed = machine()
    layout = dict(zip(LAYOUT, struct.unpack("<" + "I" * len(LAYOUT),
                       seed.bytes_at(symbols["_fixture_layout"][0], 4 * len(LAYOUT)))))
    assert layout["version"] == 1 and layout["snapshot_bytes"] == 20 + 4 * layout["reason_count"]
    cases = (
        dict(case="hit-one", entry="fixture_hit_one", amount=1),
        dict(case="hit-24-items", entry="fixture_hit_amount", amount=24),
        dict(case="hit-last-reason", entry="fixture_hit_last", amount=1, index=layout["reason_count"] - 1),
        dict(case="hit-saturation", entry="fixture_hit_amount", amount=9, old=0xfffffffd),
        dict(case="hit-inactive", entry="fixture_hit_one", amount=1, active=0),
        dict(case="begin-same-room", entry="fixture_begin", argument=18),
        dict(case="begin-new-room", entry="fixture_begin", argument=18, room=0x100),
        dict(case="begin-paused", entry="fixture_begin", argument=18, paused=1),
        dict(case="seal-drawn-tick", entry="fixture_end"),
        dict(case="seal-skipped-tick", entry="fixture_end", drawn=0),
        dict(case="seal-inactive", entry="fixture_end", active=0),
        dict(case="snapshot", entry="fixture_snapshot", argument=1),
        dict(case="snapshot-not-ready", entry="fixture_snapshot", argument=1, valid=0),
        dict(case="snapshot-null", entry="fixture_snapshot", argument=0),
    )
    rows = []
    for case in cases:
        m = machine()
        put = lambda name, value, size=4: m.map(layout[name], int(value).to_bytes(size, "little"))
        get = lambda name, size=4: int.from_bytes(m.bytes_at(layout[name], size), "little")
        items = [100 + i for i in range(layout["reason_count"])]
        index = case.get("index", 0)
        items[index] = case.get("old", items[index])
        m.map(layout["live"], struct.pack("<" + "I" * len(items), *items))
        sealed = [6, 16, 0x103, 1, 0] + [50 + i for i in range(layout["reason_count"])]
        sealed_bytes = struct.pack("<" + "I" * len(sealed), *sealed)
        m.map(layout["sealed"], sealed_bytes)
        m.map(layout["output"], bytes([0xa5]) * layout["snapshot_bytes"])
        for name, value in (("active", case.get("active", 1)), ("valid", case.get("valid", 1)),
                            ("paused", case.get("paused", 0)), ("have_room", 1)):
            put(name, value, 1)
        for name, value in (("tick", 17), ("room", case.get("room", 0x103)), ("drawn", case.get("drawn", 1)),
                            ("sequence", 7), ("overflow", 0)):
            put(name, value)
        m.minimum_sp = m.reg[15]
        m.observe_start()
        m.execute(symbols["_" + case["entry"]][0], case.get("argument", case.get("amount", 0)))
        m.observe_stop()
        after = list(struct.unpack("<" + "I" * len(items), m.bytes_at(layout["live"], 4 * len(items))))
        if case["entry"].startswith("fixture_hit"):
            expected = list(items)
            total = items[index] + case["amount"]
            if case.get("active", 1):
                expected[index] = min(total, 0xffffffff)
            assert after == expected and get("overflow") == int(case.get("active", 1) and total > 0xffffffff), case
        elif case["entry"] == "fixture_begin":
            if case.get("paused", 0):
                assert get("active", 1) == 0 and after == items and get("tick") == 17, case
            else:
                assert get("active", 1) == 1 and after == [0] * len(items) and get("tick") == 18 and get("room") == 0x103, case
                assert get("valid", 1) == int(case.get("room", 0x103) == 0x103), case
        elif case["entry"] == "fixture_end":
            if case.get("active", 1):
                expected = [8, 17, case.get("room", 0x103), case.get("drawn", 1), 0] + items
                assert m.bytes_at(layout["sealed"], layout["snapshot_bytes"]) == struct.pack("<" + "I" * len(expected), *expected), case
                assert get("active", 1) == 0 and get("valid", 1) == 1 and get("sequence") == 8, case
            else:
                assert m.bytes_at(layout["sealed"], layout["snapshot_bytes"]) == sealed_bytes and get("sequence") == 7, case
        else:
            copied = case.get("valid", 1) and case["argument"]
            assert m.reg[0] == int(bool(copied)), case
            expected = sealed_bytes if copied else bytes([0xa5]) * layout["snapshot_bytes"]
            assert m.bytes_at(layout["output"], layout["snapshot_bytes"]) == expected, case
        traffic = kernel.traffic_details(m.memory_events, m.prefetch_events)
        traffic["regions"] = {}
        for name, size in (("live", 4 * len(items)), ("sealed", layout["snapshot_bytes"]), ("output", layout["snapshot_bytes"])):
            traffic["regions"][name] = kernel.summarize([event for event in m.memory_events
                if layout[name] <= event[3] < layout[name] + size])
        trace = SimpleNamespace(instruction_pcs=list(m.instruction_pcs), steps=m.steps, read=m.read)
        rows.append(dict(case=case["case"], entry=case["entry"], instructions=m.steps,
                         peak_stack_bytes=m.initial_regs[15] - m.minimum_sp, traffic=traffic,
                         **kernel.price_helpers.price(model, case["case"], trace)))
        print("PASS", case["case"], flush=True)
    by = {row["case"]: row for row in rows}
    scenarios = []
    for hits in (1000, 10000):
        frequencies = {"hit-one": hits, "begin-same-room": 1, "seal-drawn-tick": 1}
        cycles = sum(by[name]["model_cycles"] * count for name, count in frequencies.items())
        scenarios.append(dict(label="MODELLED", assumed_calls_per_drawn_frame=frequencies, cpu_mhz=200,
                              modelled_counter_ms=cycles / 200000.0, assumed_other_work_ms=30.0,
                              modelled_whole_frame_ms=30.0 + cycles / 200000.0,
                              scope="Synthetic sensitivity: ASSUMED30ms other work plus these actual counter operations. Disabled observer adds0. Formatting/transmission, real counter frequencies and cache misses are not estimated."))
    assert frozen == {str(path.relative_to(ROOT)): profile.sha(path) for path in sources}, "source changed; rerun"
    report = dict(status="PASS", baseline=controls.BASELINE, scope=__doc__, source_sha256=frozen,
                  profile_receipt=receipt, flags=command, target_layout=layout,
                  fixture_elf_sha256=profile.sha(elf), fixture_sections=profile.sections(elf),
                  production_object=dict(sha256=profile.sha(production), **profile.sections(production),
                                         stack_usage=profile.stack_usage(production.with_suffix(".su"))),
                  fixture_stack_usage=profile.stack_usage(obj.with_suffix(".su")), model=model.metadata(),
                  cases=rows, modelled_frame_scenarios=scenarios, memory_controls=kernel.target_machine.memory_controls(),
                  limitations="Actual production counter code on synthetic states. Formatting, telemetry transport, real counter frequencies, interrupts, device waits and D-cache misses are excluded. Per-function cold-I costs are not a combined cold frame. No full game/image, console or private asset gate.")
    (out / "counter-cost.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", cases=len(rows), receipt=str(out / "counter-cost.json"))))


if __name__ == "__main__":
    main()
