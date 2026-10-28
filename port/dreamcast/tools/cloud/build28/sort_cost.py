#!/usr/bin/env python3
"""Price exact old/new RECORD sorting code on bounded synthetic SH4 inputs.

The old insertion loop is extracted verbatim from record_tick and checked
against the integration source. The new arm calls the real header helper.
Formatting, recording, transport, game callbacks and diagnostics are excluded.
The large reverse input uses aggregated access records to bound host memory;
the aggregator is checked against the existing traffic summarizer.
"""
import argparse
from array import array
import collections
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
REPLAY = DC / "tools/d367/world_replay_lean"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


controls = module("b28_sort_controls", HERE / "build_controls.py")
profile = controls.profile
kernel = module("b28_sort_kernel", DC / "tools/d367/actor_bytes_lean/kernel_audit.py")


def insertion(text):
    start = text.index("    for (unsigned i = 1; i < n; ++i) {   // insertion sort")
    depth = 0
    for end in range(text.index("{", start), len(text)):
        depth += (text[end] == "{") - (text[end] == "}")
        if depth == 0:
            return text[start:end + 1]
    raise AssertionError("unterminated insertion loop")


class AccessTotals:
    """Aggregate the existing observer's actual opcode events, without a log."""
    def __init__(self):
        self.last = -1
        self.last_kind = {"read": -1, "write": -1}
        self.instructions = collections.Counter()
        self.accesses = collections.Counter()
        self.bytes = collections.Counter()
        self.lines = {"read": set(), "write": set()}
        self.visits = 0

    def append(self, event):
        ordinal, pc, kind, address, size = event
        assert ordinal >= self.last and 0 <= address < 0x20000000 and size in (1, 2, 4, 8), event
        self.last = ordinal
        if self.last_kind[kind] != ordinal:
            self.instructions[kind] += 1
            self.last_kind[kind] = ordinal
        self.accesses[kind] += 1
        self.bytes[kind] += size
        lines = set(range(address >> 5, ((address + size - 1) >> 5) + 1))
        self.lines[kind].update(lines)
        self.visits += len(lines)

    def report(self):
        reads, writes = self.lines["read"], self.lines["write"]
        cached = dict(load_instructions=self.instructions["read"], store_instructions=self.instructions["write"],
            load_accesses=self.accesses["read"], store_accesses=self.accesses["write"],
            load_bytes=self.bytes["read"], store_bytes=self.bytes["write"],
            unique_read_lines=len(reads), unique_write_lines=len(writes),
            unique_data_lines=len(reads | writes), unique_line_bytes=32 * len(reads | writes))
        return dict(cached=cached, demand_line_visits=self.visits,
                    repeated_demand_line_visits=self.visits-len(reads | writes),
                    scope="Actual cached-RAM opcode accesses including literal pools; opcode fetches excluded. Unique 32-byte lines are touches, not cache misses or bus traffic. No uncached, SQ or PREF access is permitted in this fixture.")


class SortMachine(kernel.Machine):
    def execute_sort(self, entry):
        self.pc, self.pr, self.reg[4] = entry, 0xfffffff0, 0x9000
        self.steps, self.instruction_pcs = 0, array("I")
        while self.pc != 0xfffffff0:
            self.pc = self.step(self.pc)
            assert self.steps < 30000000, ("explicit sort fixture instruction cap", hex(self.pc))
        assert self.steps == len(self.instruction_pcs)
        assert self.reg[15] == self.initial_regs[15]
        assert self.reg[8:15] == self.initial_regs[8:15]
        assert self.fpscr == self.initial_fpscr and self.fp[0][12:16] == self.initial_fp[0][12:16]
        assert self.fp[1] == self.initial_fp[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--baseline", default=controls.BASELINE)
    reuse_group = parser.add_mutually_exclusive_group()
    reuse_group.add_argument("--reuse-old", type=Path,
        help="Reuse completed old-arm rows only after exact fresh object/ELF identity and source-loop checks")
    reuse_group.add_argument("--reuse", type=Path,
        help="Reuse completed rows in both arms only after exact fresh object/ELF identity and source-loop checks")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    baseline = subprocess.check_output(["git", "rev-parse", args.baseline], cwd=ROOT, text=True).strip()
    reuse_path = args.reuse or args.reuse_old
    previous = json.loads(reuse_path.read_text()) if reuse_path else None
    if previous:
        assert previous["status"] == "PASS"
        # A required integration rebase may change unrelated source. Retain
        # rows only from an ancestor, with the fragment and freshly rebuilt
        # object/ELF byte identities checked below for each reused arm.
        subprocess.run(["git", "merge-base", "--is-ancestor", previous["baseline"], baseline],
                       cwd=ROOT, check=True)
    menu_path = DC / "game/qa_menu.cpp"
    menu_sha256_before = profile.sha(menu_path)
    old = insertion(menu_path.read_text())
    baseline_text = subprocess.check_output(["git", "show", baseline + ":port/dreamcast/game/qa_menu.cpp"],
                                          cwd=ROOT, text=True)
    assert old == insertion(baseline_text), "old sorting source differs from integration"
    if previous:
        assert previous["extracted_source"]["insertion_sha256"] == hashlib.sha256(old.encode()).hexdigest()
    header = DC / "game/platform/include/qa_link_review28.hpp"
    sources = [Path(__file__), HERE / "build_controls.py", header,
               DC / "tools/d367/actor_bytes_lean/kernel_audit.py", *[REPLAY / (name + ".py") for name in
                 ("target_machine", "sh4_machine", "memory_trace", "pipeline_cost", "target_run")]]
    frozen = {str(path.relative_to(ROOT)): profile.sha(path) for path in sources}
    builder = profile.Build(out)
    prefix = str(cxx).removesuffix("g++")
    fixture = out / "fixture.cpp"
    fixture.write_text('#include <stdint.h>\n#if defined(RE4DC_QA_LINK_REVIEW28) && RE4DC_QA_LINK_REVIEW28\n'
        '#include "' + str(header) + '"\n#endif\n'
        'struct SortArgs { unsigned* values; unsigned count; };\n'
        'extern "C" void fixture_sort(const SortArgs* args) {\n'
        '    unsigned* v=args->values; const unsigned n=args->count;\n'
        '#if defined(RE4DC_QA_LINK_REVIEW28) && RE4DC_QA_LINK_REVIEW28\n'
        '    re4dc::ql28::sort_ticks(v,n);\n#else\n' + old + '\n#endif\n}\n')
    script = out / "fixture.ld"
    script.write_text('SECTIONS { . = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } '
                      '.data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n')
    cases = ((128, "ascending"), (128, "reverse"), (1800, "ascending"),
             (1800, "nearly-sorted"), (1800, "reverse"))
    rows, configurations = [], {}
    aggregator_checked = False
    aggregation_case = None
    for arm, value in (("old", 0), ("new", 1)):
        options = controls.QA + ["QA_LINK=1", controls.KNOB + "=" + str(value)]
        flags, receipt, _ = profile.derive(out / (arm + "-profile"), cxx, kos, sdk, options, units=("qa_menu",))
        command = flags["qa_menu"]
        assert ("-D" + controls.MACRO + "=1" in command) == bool(value)
        obj, elf = out / (arm + ".o"), out / (arm + ".elf")
        builder.run([*command, "-fstack-usage", "-c", fixture, "-o", obj], label=arm + "-compile")
        builder.run([cxx, "-m4-single", "-ml", "-nostartfiles", "-Wl,--gc-sections", "-Wl,-T," + str(script),
                     "-Wl,-e,_fixture_sort", obj, "-o", elf], label=arm + "-link")
        undefined = builder.run([prefix + "nm", "-u", elf], label=arm + "-undefined").decode()
        assert not undefined.strip(), (arm, undefined)
        (out / (arm + ".disassembly.txt")).write_bytes(builder.run([prefix + "objdump", "-d", "-C", elf], label=arm + "-disassembly"))
        program, symbols = kernel.target_machine.scalar.load_elf(elf)
        model = kernel.pipeline_cost.Model(out / (arm + "-model"), elf)
        configurations[arm] = dict(profile=receipt, object_sha256=profile.sha(obj), elf_sha256=profile.sha(elf),
            sections=profile.sections(obj), linked_sections=profile.sections(elf),
            stack_usage=profile.stack_usage(obj.with_suffix(".su")), model=model.metadata())
        reuse_arm = previous and (arm == "old" or args.reuse)
        if reuse_arm:
            for key in ("object_sha256", "elf_sha256"):
                assert configurations[arm][key] == previous["configurations"][arm][key], (key, "old code changed")
        for count, order in cases:
            prior = next((row for row in previous["cases"] if row["arm"] == arm
                          and (row["count"], row["order"]) == (count, order)), None) if reuse_arm else None
            if prior:
                rows.append(dict(copy.deepcopy(prior), reused_from_raw_sha256=profile.sha(reuse_path)))
                print("REUSED identical target code", arm, count, order, prior["model_cycles"], flush=True)
                continue
            m = SortMachine()
            for address, data, _ in program:
                m.map(address, data)
            values = list(range(count, 0, -1)) if order == "reverse" else list(range(count))
            if order == "nearly-sorted":
                values[count//2], values[count//2+1] = values[count//2+1], values[count//2]
            m.map(0x9000, struct.pack("<II", 0x20000, count))
            m.map(0x1ffe0, bytes([0xa5]) * 32)
            m.map(0x20000, struct.pack("<" + "I" * count, *values))
            m.map(0x20000 + count * 4, bytes([0x5a]) * 32)
            m.minimum_sp = m.reg[15]
            m.observe_start()
            aggregate = AccessTotals()
            if aggregator_checked:
                m.memory_events = aggregate
            m.execute_sort(symbols["_fixture_sort"][0])
            m.memory_tracking = False
            assert not m.prefetch_events
            if not aggregator_checked:
                for event in m.memory_events:
                    aggregate.append(event)
                reference = kernel.traffic_details(m.memory_events, m.prefetch_events)
                assert aggregate.report()["cached"] == reference["cached"]
                for field in ("demand_line_visits", "repeated_demand_line_visits"):
                    assert aggregate.report()[field] == reference[field]
                aggregator_checked = True
                aggregation_case = dict(arm=arm, count=count, order=order,
                                        checked_against_existing_full_event_summarizer=True)
            result = list(struct.unpack("<" + "I" * count, m.bytes_at(0x20000, count * 4)))
            assert result == sorted(values)
            assert m.bytes_at(0x1ffe0, 32) == bytes([0xa5]) * 32
            assert m.bytes_at(0x20000 + count * 4, 32) == bytes([0x5a]) * 32
            trace = SimpleNamespace(instruction_pcs=m.instruction_pcs, steps=m.steps, read=m.read)
            priced = kernel.price_helpers.price(model, f"{arm}-{count}-{order}", trace)
            rows.append(dict(arm=arm, count=count, order=order, instructions=m.steps,
                peak_stack_bytes=m.initial_regs[15] - m.minimum_sp, traffic=aggregate.report(), **priced))
            (out / "progress.json").write_text(json.dumps(dict(status="IN_PROGRESS", source_sha256=frozen,
                configurations=configurations, cases=rows), indent=2) + "\n")
            print("PASS", arm, count, order, priced["model_cycles"], flush=True)
    assert frozen == {path: profile.sha(ROOT / path) for path in frozen}, "sort source changed during run"
    assert insertion(menu_path.read_text()) == old, "extracted old loop changed during run"
    frames = []
    for count, order in cases:
        pair = {row["arm"]: row for row in rows if (row["count"], row["order"]) == (count, order)}
        frames.append(dict(count=count, order=order, assumed_other_work_ms=30, cpu_mhz=200,
            old_total_ms=30 + pair["old"]["model_cycles"] / 200000,
            new_total_ms=30 + pair["new"]["model_cycles"] / 200000,
            delta_ms=(pair["new"]["model_cycles"]-pair["old"]["model_cycles"]) / 200000))
    result = dict(status="PASS", baseline=baseline, scope=__doc__, source_sha256=frozen,
        extracted_source=dict(path=str(menu_path.relative_to(ROOT)), file_sha256_before=menu_sha256_before,
            file_sha256_after=profile.sha(menu_path), insertion_sha256=hashlib.sha256(old.encode()).hexdigest(),
            scope="Only the unchanged insertion loop is compiled from this file. Unrelated menu edits do not enter this fixture."),
        configurations=configurations, cases=rows, memory_controls=kernel.target_machine.memory_controls(),
        reused_receipt_sha256=profile.sha(reuse_path) if previous else None,
        reused_receipt_baseline=previous["baseline"] if previous else None,
        aggregated_access_control=dict(current_execution=aggregation_case,
            inherited_control=previous["aggregated_access_control"] if previous else None,
            scope="Freshly executed aggregate traffic is compared with the existing full-event summarizer. Reused rows retain their earlier checks and require exact fresh object/ELF identity."),
        whole_frame_modelled=dict(label="MODELLED", cases=frames,
            scope="One synthetic RECORD completion sort plus an assumed unchanged 30 ms remainder. No regular-frame FPS, actual recorded timing distribution or modem wait is predicted."),
        limitations="Synthetic integer input; actual target sorting code only. Perfect D-cache, warm/cold-I separated. Source extraction does not establish whole-qa_menu compilation or disabled identity; those are separate target gates.")
    (out / "sort-cost.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", cases=len(rows), receipt=str(out / "sort-cost.json"))))


if __name__ == "__main__":
    main()
