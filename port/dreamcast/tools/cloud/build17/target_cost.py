#!/usr/bin/env python3
"""Compiled Build17 controller/state/validator traces, with synthetic devices.

Actual production header instructions are executed by the repository's SH4
trace interpreter and priced by hwsim. Controller traces also include fake
callback bookkeeping. No BIOS, device transfer, hardware waiting, real cache
maintenance or semaphore/timer implementation is priced. These results cannot
establish PIO read rate, door-load time, movie bandwidth or game FPS.
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


build = module("disc17_build", HERE / "build_controls.py")
kernel = module("disc17_kernel", DC / "tools/d367/actor_bytes_lean/kernel_audit.py")
profile = build.profile
IO_FIELDS = ("clock", "fault", "dma", "retiring", "reset_done", "acquired", "released",
             "submissions", "pio_submissions", "first_sector", "first_count", "last_sector",
             "last_count", "switches", "session_switches", "disables", "enables", "aborts",
             "resets", "inits", "clears", "pauses")
STATE_FIELDS = ("failures", "session_pio", "retry_pio", "poisoned", "validating",
                "validation_dma", "validation_fault", "validation_rejected")


class DiscArithmetic(kernel.KernelArithmetic):
    def step(self, pc, delay=False):
        opcode = self.fetch(pc)
        if opcode & 0xff00 != 0xca00:  # XOR #imm,R0
            return super().step(pc, delay)
        self.minimum_sp = min(self.minimum_sp, self.reg[15])
        self.reg[0] ^= opcode & 255
        self.instruction_pcs.append(pc)
        self.steps += 1
        return pc + 2


class Machine(kernel.Observer, DiscArithmetic):
    pass


def opcode_controls():
    m = Machine()
    m.map(0x100000, bytes(6))
    for immediate in range(256):
        for value in (0, 0xffffffff, 0x12345678):
            for t in (0, 1):
                m.map(0x100000, struct.pack("<H", 0xca00 | immediate))
                m.reg[0], m.t, m.steps, m.instruction_pcs = value, t, 0, []
                m.observe_start()
                assert m.step(0x100000) == 0x100002
                m.observe_stop()
                assert m.reg[0] == (value ^ immediate) and m.t == t
                assert m.steps == 1 and m.instruction_pcs == [0x100000] and not m.memory_events
    m.map(0x100000, struct.pack("<3H", 0xa000, 0xca01, 0x0009))
    m.reg[0], m.steps, m.instruction_pcs = 0xffffffff, 0, []
    m.observe_start()
    assert m.step(0x100000) == 0x100004
    m.observe_stop()
    assert m.reg[0] == 0xfffffffe and m.steps == 2 and not m.memory_events
    return dict(status="PASS", added_opcode="XOR #imm,R0", immediate_values=256,
                register_controls=[0, 0xffffffff, 0x12345678], t_values=[0, 1],
                delay_slot=True, scope="Exact unsigned register XOR; preserves T and performs no data access")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    paths = [ROOT / name for name in build.SOURCES] + [HERE / "controller_cost.cpp.in", HERE / "validator_cost.cpp.in",
        Path(__file__), DC / "tools/d367/actor_bytes_lean/kernel_audit.py",
        DC / "tools/d367/world_replay_lean/target_machine.py", DC / "tools/d367/world_replay_lean/sh4_machine.py",
        DC / "tools/d367/world_replay_lean/memory_trace.py", DC / "tools/d367/world_replay_lean/pipeline_cost.py",
        DC / "tools/d367/world_replay_lean/target_run.py"]
    frozen = {str(p.relative_to(ROOT)): profile.sha(p) for p in paths}
    flags, receipt, _ = build.derive(out / "profile", cxx, kos, sdk,
        build.PROFILES["fallback2"] + ["DISC_PIO_FALLBACK=1"], units=("dvd", "snd"))
    builder = profile.Build(out)
    objects = []
    for name, unit in (("controller", "dvd"), ("validator", "snd")):
        source, obj = out / (name + ".cpp"), out / (name + ".o")
        source.write_text((HERE / (name + "_cost.cpp.in")).read_text().replace("@DC@", str(DC)))
        builder.run([*flags[unit], "-c", "-fstack-usage", source, "-o", obj], label=name)
        objects.append(obj)
    roots = ("fixture_read", "fixture_begin", "fixture_dma_ok", "fixture_reject", "fixture_end",
             "fixture_validate", "fixture_controller_layout", "fixture_validator_layout")
    linker, elf = out / "fixture.ld", out / "fixture.elf"
    linker.write_text("SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }\n"
                     ". = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n")
    builder.run([cxx, "-m4-single", "-ml", "-nostartfiles", "-Wl,--gc-sections", "-Wl,-T," + str(linker),
                 "-Wl,-e,_fixture_read", *["-Wl,-u,_" + x for x in roots], *objects, "-o", elf], label="link")
    prefix = str(cxx).removesuffix("g++")
    (out / "disassembly.txt").write_bytes(builder.run([prefix + "objdump", "-d", "-C", elf], label="disassembly"))
    program, symbols = kernel.target_machine.scalar.load_elf(elf)
    model = kernel.pipeline_cost.Model(out / "model", elf)

    def machine():
        m = Machine()
        for address, data, _ in program:
            m.map(address, data)
        return m

    seed = machine()
    layout = struct.unpack("<37I", seed.bytes_at(symbols["_fixture_controller_layout"][0], 148))
    arg_size, state_off, request_off, dma_off, io_off, state_size, io_size = layout[:7]
    io_offsets = dict(zip(IO_FIELDS, layout[7:29]))
    state_offsets = dict(zip(STATE_FIELDS, layout[29:]))
    vl = struct.unpack("<4I", seed.bytes_at(symbols["_fixture_validator_layout"][0], 16))
    rows = []

    def observe(m, name, entry, *, controller=False):
        m.minimum_sp = m.reg[15]
        m.observe_start()
        m.execute_kernel(symbols["_" + entry][0], 0x9000)
        m.observe_stop()
        traffic = kernel.traffic_details(m.memory_events, m.prefetch_events)
        regions = {}
        for event in m.memory_events:
            address = event[3]
            region = ("stack" if address >= 0x4f0000 else
                      "table-input" if 0x20000 <= address < 0x30000 else
                      "synthetic-driver" if controller and 0x9000 + io_off <= address < 0x9000 + io_off + io_size else
                      "state-and-arguments" if 0x9000 <= address < 0xa000 else "code-literals")
            regions.setdefault(region, []).append(event)
        traffic["regions"] = {region: kernel.summarize(events) for region, events in regions.items()}
        trace = SimpleNamespace(instruction_pcs=list(m.instruction_pcs), steps=m.steps, read=m.read)
        priced = kernel.price_helpers.price(model, name, trace)
        row = dict(case=name, entry=entry, result=m.reg[0], instructions=m.steps,
                   peak_stack_bytes=m.initial_regs[15] - m.minimum_sp, traffic=traffic, **priced)
        rows.append(row)
        return row

    def arguments(fault=0, **state):
        raw = bytearray(arg_size)
        for name, value in state.items():
            raw[state_off + state_offsets[name]] = value
        struct.pack_into("<III", raw, request_off, 0x20000, 83433, 21)
        struct.pack_into("<I", raw, dma_off, 1)
        struct.pack_into("<I", raw, io_off + io_offsets["fault"], fault)
        m = machine()
        m.map(0x9000, raw)
        return m

    def read_io(m):
        return {name: int.from_bytes(m.bytes_at(0x9000 + io_off + offset, 8 if name == "clock" else 4), "little")
                for name, offset in io_offsets.items()}

    def read_state(m):
        return {name: m.bytes_at(0x9000 + state_off + offset, 1)[0] for name, offset in state_offsets.items()}

    for name, fault, state in (
        ("dma-ok", 0, {}), ("pio-session-ok", 0, {"session_pio": 1, "failures": 2}),
        ("dma-drop-completion-pio", 1, {}), ("dma-marker-missing-pio", 2, {}),
        ("dma-error-pio", 3, {}), ("dma-abort-timeout-reset-pio", 4, {}),
        ("second-failure-latches-session", 1, {"failures": 1}),
    ):
        m = arguments(fault, **state)
        row = observe(m, name, "fixture_read", controller=True)
        io, result_state = read_io(m), read_state(m)
        assert row["result"] == 0, (name, row["result"])
        assert io["acquired"] == io["released"] == 1
        assert io["first_sector"] == io["last_sector"] == 83433
        assert io["first_count"] == io["last_count"] == 21
        assert io["submissions"] == (2 if fault else 1)
        assert io["pio_submissions"] == int(bool(fault or state.get("session_pio")))
        assert io["switches"] == int(bool(fault))
        assert io["disables"] == io["enables"] == io["aborts"] == int(bool(fault))
        assert io["resets"] == io["inits"] == int(fault == 4)
        assert result_state["poisoned"] == 0
        assert result_state["session_pio"] == int(name in ("pio-session-ok", "second-failure-latches-session"))
        row.update(state=result_state, synthetic_driver=io,
                   requested_payload_bytes_all_submissions_unpriced=21 * 2048 * io["submissions"],
                   scope="Production controller plus synthetic callback instructions; no actual payload copy or BIOS calls")
        print("PASS", name, flush=True)

    for name, entry, values, expected in (
        ("state-validation-begin", "fixture_begin", {}, {"validating": 1}),
        ("state-dma-success-pending-validation", "fixture_dma_ok", {"validating": 1, "failures": 1}, {"validation_dma": 1, "failures": 1}),
        ("state-first-semantic-reject", "fixture_reject", {"validating": 1, "validation_dma": 1}, {"failures": 1, "retry_pio": 1, "validation_rejected": 1}),
        ("state-second-semantic-reject", "fixture_reject", {"validating": 1, "validation_dma": 1, "failures": 1}, {"failures": 2, "retry_pio": 1, "session_pio": 1}),
        ("state-duplicate-reject", "fixture_reject", {"validating": 1, "validation_dma": 1, "validation_rejected": 1, "failures": 1, "retry_pio": 1}, {"failures": 1, "retry_pio": 1}),
        ("state-accepted-end", "fixture_end", {"validating": 1, "validation_dma": 1, "failures": 1}, {"failures": 0, "validating": 0, "retry_pio": 0}),
        ("state-session-end-stays-pio", "fixture_end", {"validating": 1, "validation_dma": 1, "validation_rejected": 1, "failures": 2, "session_pio": 1, "retry_pio": 1}, {"failures": 2, "validating": 0, "session_pio": 1, "retry_pio": 0}),
    ):
        m = arguments(**values)
        row = observe(m, name, entry, controller=True)
        result_state = read_state(m)
        assert all(result_state[key] == value for key, value in expected.items()), (name, result_state)
        row.update(state=result_state, scope="Production State method plus fixture entry wrapper")
        print("PASS", name, flush=True)

    for name, length, bad_offset, expected in (
        ("validator-valid-44384", 44384, None, 1),
        ("validator-short", 7, None, 0),
        ("validator-overflow-offset", 44384, 0xfffffffc, 0),
        ("validator-misaligned-offset", 44384, 9, 0),
        ("validator-misaligned-rit", 44384, None, 0),
    ):
        m = machine()
        raw = bytearray(vl[0])
        struct.pack_into("<I", raw, vl[1], 0x20000)
        struct.pack_into("<i", raw, vl[2], length)
        m.map(0x9000, raw)
        table = bytearray(44384)
        struct.pack_into("<II", table, 0, 8, 32)
        for offset in (8, 32):
            struct.pack_into("<III", table, offset, 3, 12, 24)
        if name == "validator-misaligned-rit":
            struct.pack_into("<I", table, 16, 25)
        if bad_offset is not None:
            struct.pack_into("<I", table, 0, bad_offset)
        m.map(0x20000, table)
        row = observe(m, name, "fixture_validate")
        assert row["result"] == expected, (name, row["result"])
        table_accesses = [e for e in m.memory_events if 0x20000 <= e[3] < 0x30000]
        assert all(e[2] == "read" and e[3] + e[4] <= 0x20000 + max(0, length) for e in table_accesses)
        row.update(table_length=length, scope="Production stream-table validator, with actual compiler/libc instructions")
        print("PASS", name, flush=True)
    assert frozen == {str(p.relative_to(ROOT)): profile.sha(p) for p in paths}, "source changed; rerun"
    report = dict(status="PASS", scope=__doc__, source_sha256=frozen, profile_receipt=receipt,
        compiler_sha256=profile.sha(cxx), elf_sha256=profile.sha(elf), sections=profile.sections(elf),
        objects={obj.name: dict(sha256=profile.sha(obj), **profile.sections(obj),
                               stack_usage=profile.stack_usage(obj.with_suffix(".su"))) for obj in objects},
        controller_layout=dict(argument_bytes=arg_size, state_bytes=state_size, synthetic_io_bytes=io_size,
                               actual_snd_rit_alignment=vl[3]),
        cases=rows, model=model.metadata(), memory_controls=kernel.target_machine.memory_controls(),
        opcode_controls=opcode_controls(),
        limits="Architectural bytes and 32-byte demand lines are not measured cache misses or bus traffic. Warm/perfect-cache and isolated cold-I cycles are synthetic CPU scheduling models. Driver bookkeeping is included; BIOS, drive/PIO waits, real IRQ/cache/semaphore work and payload bytes are unpriced. No read-rate/FPS inference is justified.")
    (out / "target-cost.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", cases=len(rows), receipt=str(out / "target-cost.json"))))


if __name__ == "__main__":
    main()
