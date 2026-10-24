# Test-only helper retained from commit 8c7226467dba68ac8ee16652accc10f683562685.
# This copies no renderer runtime or PR56 ancestry into the integration branch.
"""Price actual dynamic instruction traces with the repository's hwsim model.

Perfect caches, no memory/bus/SQ/DMA events and no final completion drain.
This is a synthetic CPU scheduling comparison, never hardware time or FPS.
"""
import bisect
import collections
import csv
import hashlib
import struct
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1] / "hwmodel/hwsim.c"
RAM_ALIAS = 0x8C000000
FLAGS = ["--perfect-ic", "--perfect-dc", "--no-dma", "--sq-cost", "0"]


def symbol_costs(machine, symbols):
    # The SDK and libc assembler routines can be STT_NOTYPE rather than
    # STT_FUNC. Include their named entry points, but not local L_* labels.
    entries = sorted((address, name) for name, (address, _, info) in symbols.items()
                     if name.startswith("_") and 0x100000 <= address < 0x110000
                     and (info & 15) in (0, 2))
    starts = [address for address, _ in entries]
    counts = collections.Counter()
    for pc in machine.instruction_pcs:
        position = bisect.bisect_right(starts, pc) - 1
        assert position >= 0, hex(pc)
        counts[entries[position][1]] += 1
    assert sum(counts.values()) == machine.steps
    return dict(counts.most_common())


class Model:
    def __init__(self, output, source_elf, host_cc="gcc"):
        self.output = output
        self.output.mkdir(exist_ok=False)
        self.binary = output / "hwsim"
        self.compile_command = [host_cc, "-O2", "-o", str(self.binary), str(MODEL), "-lm"]
        subprocess.run(self.compile_command, check=True)
        original = source_elf.read_bytes()
        image = bytearray(original)
        assert image[:6] == b"\x7fELF\x01\x01"
        entry, phoff = struct.unpack_from("<II", image, 24)
        phsize, phnum = struct.unpack_from("<HH", image, 42)
        assert entry < 1 << 24
        struct.pack_into("<I", image, 24, entry | RAM_ALIAS)
        self.segments = []
        for index in range(phnum):
            at = phoff + index * phsize
            kind, offset, vaddr, paddr, size, _, flags = struct.unpack_from("<7I", image, at)
            if kind != 1 or not flags & 1:
                continue
            assert vaddr + size <= 1 << 24 and paddr < 1 << 24
            struct.pack_into("<II", image, at + 8, vaddr | RAM_ALIAS, paddr | RAM_ALIAS)
            self.segments.append((vaddr, offset, size))
        assert self.segments
        for _, offset, size in self.segments:
            assert original[offset:offset + size] == image[offset:offset + size]
        self.image = image
        self.view = output / "model-address-view.elf"
        self.view.write_bytes(image)

    def price(self, name, machine):
        pcs = machine.instruction_pcs
        assert pcs and len(pcs) == machine.steps
        for pc in set(pcs):
            segments = [(start, offset, size) for start, offset, size in self.segments
                        if start <= pc and pc + 2 <= start + size]
            assert len(segments) == 1, (hex(pc), segments)
            start, offset, _ = segments[0]
            expected = struct.unpack_from("<H", self.image, offset + pc - start)[0]
            assert machine.read(pc, 2) == expected
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
        trace = self.output / (name + ".bin")
        trace.write_bytes(b"".join(struct.pack("<II", *run) for run in runs))
        prefix = self.output / name
        command = [str(self.binary), "--elf", str(self.view), "--out", str(prefix), *FLAGS, str(trace)]
        result = subprocess.run(command, capture_output=True, text=True)
        prefix.with_suffix(".log").write_text(result.stdout + result.stderr)
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
                      for key in ("base", "dep_load", "dep_fpu", "dep_fdiv", "dep_other",
                                  "flock", "branch", "imiss", "dmiss", "pfwait", "sq", "uncached")}
        assert all(categories[key] == 0 for key in ("imiss", "dmiss", "pfwait", "sq", "uncached"))
        return dict(model_cycles=int(totals["cycles"]), instruction_runs=len(runs),
                    categories=categories, trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),
                    command=command)

    def metadata(self):
        return dict(scope=__doc__, source=str(MODEL), source_sha256=hashlib.sha256(MODEL.read_bytes()).hexdigest(),
                    compile_command=self.compile_command, flags=FLAGS,
                    exact_dynamic_instruction_and_delay_slot_counts=True,
                    no_hardware_time_or_frame_speedup_claim=True)
