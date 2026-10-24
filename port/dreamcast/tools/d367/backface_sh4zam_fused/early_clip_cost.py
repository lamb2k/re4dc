#!/usr/bin/env python3
"""Price synthetic dynamic caller traces with the existing SH4 pipeline model.

This is a perfect-cache, no-memory-event CPU scheduling comparison. It is not
a hardware, emulator, scene, wall-time or frame-rate measurement. The unchanged
hwsim.c supplies all scheduling/dependency/branch costs. Its final-instruction
issue convention omits completion drain after the common return sequence.
"""
import argparse
import csv
import json
import struct
import subprocess
from pathlib import Path

import early_clip_test as checks


HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1] / "hwmodel/hwsim.c"
RAM_ALIAS = 0x8C000000
FLAGS = ["--perfect-ic", "--perfect-dc", "--no-dma", "--sq-cost", "0"]


class TracedWorld(checks.CountedWorld):
    def __init__(self, *args, **kwargs):
        self.instruction_pcs = []
        super().__init__(*args, **kwargs)

    def step(self, pc, delay=False):
        # The interpreter recursively calls self.step for delay slots, so this
        # records every executed instruction exactly once, in execution order.
        self.instruction_pcs.append(pc)
        return super().step(pc, delay)


def model_elf(source, destination):
    """Give hwsim a RAM-addressed header view without changing any code bytes."""
    original = source.read_bytes()
    image = bytearray(original)
    assert image[:6] == b"\x7fELF\x01\x01"
    entry, phoff = struct.unpack_from("<II", image, 24)
    entsize, count = struct.unpack_from("<HH", image, 42)
    assert entry < (1 << 24)
    struct.pack_into("<I", image, 24, entry | RAM_ALIAS)
    segments = []
    for index in range(count):
        offset = phoff + index * entsize
        kind, file_offset, vaddr, paddr, size, _, flags = struct.unpack_from("<7I", image, offset)
        # The bare-metal linker also emits an unused .stack segment at
        # 0x3fffff00. Only executable segments belong in the model's RAM view.
        if kind != 1 or not flags & 1:
            continue
        assert vaddr + size <= (1 << 24) and paddr < (1 << 24)
        struct.pack_into("<II", image, offset + 8, vaddr | RAM_ALIAS, paddr | RAM_ALIAS)
        segments.append((vaddr, file_offset, size))
    assert segments
    destination.write_bytes(image)
    assert checks.BASE.text_section(source) == checks.BASE.text_section(destination)
    return image, segments


def write_trace(path, machine, program, model_image, segments):
    pcs = machine.instruction_pcs
    assert len(pcs) == machine.steps, (len(pcs), machine.steps)
    assert pcs
    # Confirm hwsim will decode exactly the bytes that the host interpreter
    # executed, despite the metadata-only RAM alias used by the model.
    for pc in set(pcs):
        matches = [(start, offset, size) for start, offset, size in segments
                   if start <= pc and pc + 2 <= start + size]
        assert len(matches) == 1, (hex(pc), matches)
        start, offset, _ = matches[0]
        assert model_image[offset + pc - start:offset + pc - start + 2] == program[pc - 0x100000:pc - 0x100000 + 2]
    runs = []
    start = previous = pcs[0]
    count = 1
    for pc in pcs[1:]:
        if pc == previous + 2:
            count += 1
        else:
            runs.append((start | RAM_ALIAS, 0x10000000 | count))
            start, count = pc, 1
        previous = pc
    runs.append((start | RAM_ALIAS, 0x10000000 | count))
    assert sum(word & 0x0FFFFFFF for _, word in runs) == machine.steps
    with path.open("wb") as output:
        for run in runs:
            output.write(struct.pack("<II", *run))
    return len(runs)


def fixtures():
    n = 64
    valid = (1 << (n - 2)) - 1
    strip = bytes([n]) + bytes(range(n))
    for pattern, front in (("all-front", valid), ("all-back", 0),
                           ("mixed", int("001111000111" * 6, 2) & valid)):
        cache = checks.patterned_cache(n - 2, front)
        for batch in (1, 32):
            yield pattern, batch, cache, strip * batch, bytes(n)
    cache = checks.patterned_cache(n - 2, valid)
    for position in (1, 31, 63):
        outcodes = bytearray(n)
        outcodes[position] = 1
        yield "depth-cross-at-%d" % position, 1, cache, strip, bytes(outcodes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--host-cc", default="gcc")
    args = parser.parse_args()
    assert not args.output.exists(), "output directory must be new"
    args.output.mkdir(parents=True)
    output = args.output.resolve()
    model = output / "hwsim"
    command = [args.host_cc, "-O2", "-o", str(model), str(MODEL), "-lm"]
    subprocess.run(command, check=True)
    directories = {"baseline": args.baseline.resolve(), "candidate": args.candidate.resolve()}
    oracle = checks.BASE.oracle_load(directories["baseline"] / "oracle.so")
    programs = {}
    for arm, directory in directories.items():
        source = directory / "walk-trace0.elf"
        view = output / (arm + "-model-address-view.elf")
        image, segments = model_elf(source, view)
        programs[arm] = (checks.BASE.text_section(source),
                         struct.unpack_from("<I", source.read_bytes(), 24)[0],
                         view, image, segments)
    rows = []
    for pattern, batch, cache, stream, outcodes in fixtures():
        row = dict(pattern=pattern, batch=batch, indices_per_strip=64)
        want = checks.EXPECTED(oracle, cache, stream, outcodes, 255, 2)
        for arm, program in programs.items():
            text, entry, view, image, segments = program
            machine = TracedWorld(text, cache, stream, outcodes, 255, 2)
            machine.pc = entry
            assert machine.run() == want, (arm, pattern, batch, "oracle mismatch")
            assert machine.written == [0, 0]
            name = "%s-%s-%d" % (arm, pattern, batch)
            trace = output / (name + ".bin")
            runs = write_trace(trace, machine, text, image, segments)
            prefix = output / name
            cmd = [str(model), "--elf", str(view), "--out", str(prefix), *FLAGS, str(trace)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            (output / (name + ".log")).write_text(result.stdout + result.stderr)
            assert result.returncode == 0, result.stderr
            totals = dict(line.split() for line in prefix.with_suffix(".sum.txt").read_text().splitlines())
            assert int(totals["insns"]) == machine.steps
            for key in ("dfills_per_frame", "ifills_per_frame", "writebacks_per_frame",
                        "dma_bytes_per_frame", "dma_starts_per_frame", "dma_bus_cycles_per_frame"):
                assert float(totals[key]) == 0, (name, key, totals[key])
            with prefix.with_suffix(".pcs.tsv").open() as source:
                stats = list(csv.DictReader(source, delimiter="\t"))
            assert sum(int(item["exec"]) for item in stats) == machine.steps
            categories = {key: sum(float(item[key]) for item in stats)
                          for key in ("base", "dep_load", "dep_fpu", "dep_fdiv",
                                      "dep_other", "flock", "branch", "imiss", "dmiss",
                                      "pfwait", "sq", "uncached")}
            assert all(categories[key] == 0 for key in ("imiss", "dmiss", "pfwait", "sq", "uncached"))
            row[arm] = dict(instructions=machine.steps, instruction_runs=runs,
                            model_cycles=int(totals["cycles"]), model_categories=categories,
                            trace_sha256=checks.BASE.sha(trace.read_bytes()), command=cmd)
        before, after = row["baseline"]["model_cycles"], row["candidate"]["model_cycles"]
        row.update(cycles_removed=before - after,
                   reduction_percent=100.0 * (before - after) / before)
        rows.append(row)
    report = dict(
        scope="Synthetic complete public caller, dynamic SH4 opcodes, existing hwsim pipeline model",
        exclusions="No cache misses, memory/bus/SQ events, DMA, interrupts, scene distribution, emulator or hardware run",
        convention="Issue through the final actual instruction; common final return completion drain is not priced",
        no_hardware_time_or_frame_speedup_claim=True,
        exact_dynamic_instruction_and_delay_slot_counts=True,
        model_source=str(MODEL), model_source_sha256=checks.BASE.sha(MODEL.read_bytes()),
        helper_source_sha256=checks.BASE.sha(Path(__file__).read_bytes()),
        compiler_command=command, model_flags=FLAGS,
        source_elfs={arm: checks.BASE.sha((directory / "walk-trace0.elf").read_bytes())
                     for arm, directory in directories.items()},
        rows=rows,
    )
    (output / "pipeline-cost.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(scope=report["scope"],
                          rows=[dict(pattern=row["pattern"], batch=row["batch"],
                                     baseline_cycles=row["baseline"]["model_cycles"],
                                     candidate_cycles=row["candidate"]["model_cycles"],
                                     cycles_removed=row["cycles_removed"])
                                for row in rows]), indent=2))


if __name__ == "__main__":
    main()
