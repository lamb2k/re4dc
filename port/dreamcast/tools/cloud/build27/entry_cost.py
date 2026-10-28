#!/usr/bin/env python3
"""Execute real weapon-module registration prefixes and complete epilogs.

Each module is the unmodified generated/partially linked target object. A
fixture-only link assigns synthetic addresses to its external imports. Only
the three registration cells are mapped; execution stops before OSReport and
rejects every other imported-service entry. No missing provider is executed as
a success stub. Prolog timing ends at the logging call boundary, before its
body and the caller return tail. Epilog timing includes its complete return.
Module-state reset, disk/assets, weapon creation, fire/reload, sound and frame
work are not executed or priced. This is not a final game link.
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
spec = importlib.util.spec_from_file_location("wep27_price", REPLAY / "target_run.py")
prices = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prices)
spec = importlib.util.spec_from_file_location("wep27_module_build", HERE / "module_build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
profile = build.profile
SPECS = {"wep05": (67, 0x29, 0x2e, "Wep05_init", "PlHandgunMove", "ObjCivilian_init"),
         "wep06": (50, 0x2a, 0x31, "Wep06_init", "PlHandgunMove", "ObjGovernment_init"),
         "wep12": (56, 0x34, 0x25, "Wep12_init", "PlMachineMove", "ObjTompson_init")}
BINDINGS = {"_WeaponInitFunc": 0x20000, "_WeaponMoveFunc": 0x20004, "_ObjInitFunc": 0x20040,
            "_OSReport": 0x700000}


class Machine(target_machine.Machine):
    def prefix(self, entry, edge, imported):
        self.pc, self.pr = entry, 0xfffffff0
        self.steps, self.instruction_pcs = 0, []
        while self.pc != edge:
            assert self.pc not in imported, (hex(self.pc), "unpriced imported service executed")
            assert self.pc != 0xfffffff0, "registration returned before the logging boundary"
            self.pc = self.step(self.pc)
            assert self.steps < 1000
        assert self.steps == len(self.instruction_pcs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "module-build"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx = args.sh4_cxx.resolve()
    prefix = str(cxx).removesuffix("g++")
    builder = profile.Build(out)
    receipt = json.loads(args.module_build.read_text())
    assert receipt["status"] == "PASS"
    source_files = [Path(__file__), HERE / "module_build.py", *[REPLAY / (name + ".py") for name in
                    ("target_machine", "sh4_machine", "memory_trace", "pipeline_cost", "target_run")]]
    frozen = {str(path.relative_to(ROOT)): profile.sha(path) for path in source_files}
    script = out / "fixture.ld"
    script.write_text("SECTIONS { . = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } "
                      ".data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n")
    rows, models = [], {}
    for mod, (module_id, item_id, object_id, init_name, move_name, object_name) in SPECS.items():
        source = receipt["modules"][mod]
        obj = Path(source["object"])
        assert profile.sha(obj) == source["sha256"]
        bindings = {name: BINDINGS.get(name, 0x710000 + 64 * i) for i, name in enumerate(source["imports"])}
        assert all(name in bindings for name in BINDINGS)
        aliases = out / (mod + "-bindings.ld")
        aliases.write_text("/* Test-only bindings: unexecuted game imports stay explicit. */\n" +
                           "".join(name + " = " + hex(address) + ";\n" for name, address in bindings.items()))
        elf = out / (mod + ".elf")
        builder.run([prefix + "ld", "-EL", "-e", "_" + mod + "_prolog", "-T", script, "-T", aliases,
                     obj, "-o", elf], label=mod + "-fixture-link")
        program, symbols = target_machine.scalar.load_elf(elf)
        models[mod] = pipeline_cost.Model(out / (mod + "-model"), elf)

        def find(name):
            candidates = [value[0] for symbol, value in symbols.items() if name in symbol and value[2] & 15 == 2]
            assert len(candidates) == 1, (name, candidates)
            return candidates[0]

        expected = (find(init_name), find(move_name), find(object_name))
        constructor = BINDINGS["_ObjInitFunc"] + 4 * object_id
        for phase in ("registration-prefix", "epilog"):
            m = Machine()
            for address, data, _ in program:
                m.map(address, data)
            m.map(0x20000, bytes([0xa5]) * 0x140)
            m.map(BINDINGS["_WeaponInitFunc"], struct.pack("<I", expected[0] if phase == "epilog" else 0xaaaaaaaa))
            m.map(BINDINGS["_WeaponMoveFunc"], struct.pack("<I", expected[1] if phase == "epilog" else 0xbbbbbbbb))
            m.map(constructor, struct.pack("<I", expected[2] if phase == "epilog" else 0xcccccccc))
            before = m.bytes_at(0x20000, 0x140)
            m.minimum_sp = m.reg[15]
            m.observe_start()
            if phase == "registration-prefix":
                m.prefix(symbols["_" + mod + "_prolog"][0], bindings["_OSReport"], set(bindings.values()))
                assert m.reg[15] == m.initial_regs[15] - 4
            else:
                m.execute(symbols["_" + mod + "_epilog"][0], 0)
            m.observe_stop()
            after = bytearray(before)
            if phase == "registration-prefix":
                for address, value in zip((BINDINGS["_WeaponInitFunc"], BINDINGS["_WeaponMoveFunc"], constructor), expected):
                    struct.pack_into("<I", after, address - 0x20000, value)
                message = bytearray()
                cursor = m.reg[4]
                while m.mem[cursor]:
                    message.append(m.mem[cursor]); cursor += 1
                assert mod.lower().encode() in bytes(message).lower()
            else:
                struct.pack_into("<I", after, constructor - 0x20000, 0)
                message = b""
            assert m.bytes_at(0x20000, 0x140) == bytes(after), (mod, phase, "registration cells or adjacent state changed")
            trace = SimpleNamespace(instruction_pcs=list(m.instruction_pcs), steps=m.steps, read=m.read)
            traffic = summarize(m.memory_events)
            visits = sum(len({at >> 5 for at in range(event[3], event[3] + event[4])}) for event in m.memory_events)
            traffic.update(demand_line_visits=visits, repeated_demand_line_visits=visits - traffic["cached"]["unique_data_lines"])
            rows.append(dict(module=mod, module_id=module_id, item_id=item_id, object_id=object_id, phase=phase,
                             instructions=m.steps, peak_stack_bytes=m.initial_regs[15] - m.minimum_sp,
                             traffic=traffic, expected_callback_addresses=expected, log_message=bytes(message).decode(),
                             module_object_sha256=source["sha256"], fixture_elf_sha256=profile.sha(elf),
                             fixture_bindings_sha256=profile.sha(aliases),
                             **prices.price(models[mod], phase, trace)))
            print("PASS", mod, phase, flush=True)
    assert frozen == {str(path.relative_to(ROOT)): profile.sha(path) for path in source_files}
    registration = max(row["model_cycles"] for row in rows if row["phase"] == "registration-prefix")
    epilog = max(row["model_cycles"] for row in rows if row["phase"] == "epilog")
    frame = dict(label="MODELLED", assumed_other_work_ms=30.0, assumed_cpu_mhz=200,
                 assumed_calls=dict(registration_prefix=1, epilog=1),
                 priced_cycles=registration + epilog,
                 priced_ms=(registration + epilog) / 200000.0,
                 total_ms=30.0 + (registration + epilog) / 200000.0,
                 scope="Synthetic switch-tick sensitivity with a fixed unpriced remainder; logging/return tail, reset/load/assets and actual weapon work remain in that assumed remainder. No gain relative to failed/missing-module behavior is claimed.")
    result = dict(status="PASS", baseline=receipt["baseline"], scope=__doc__, cases=rows,
                  source_sha256=frozen, module_build_sha256=profile.sha(args.module_build),
                  bindings=BINDINGS, model={name: model.metadata() for name, model in models.items()},
                  whole_frame_modelled=frame,
                  memory_controls=target_machine.memory_controls(),
                  limitations="Fixed synthetic global layout; perfect D-cache. Registration prefix stops before OSReport and excludes the caller return tail. Only the complete epilog returns. Imported callbacks are registered but never called. No gameplay/fire/reload/asset service cost, whole-game link or console timing is claimed.")
    (out / "entry-cost.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", cases=len(rows), receipt=str(out / "entry-cost.json"))))


if __name__ == "__main__":
    main()
