#!/usr/bin/env python3
"""Read-only SH-4 instruction-cache trace POC; never writes a linker layout.

Uses the existing RE4 hwtrace run format and hwsim's cache-fetch convention.
The temporal/conflict diagnostic follows the idea in Byterset/MipsFit; the
decoder and replay below target SH-4 halfwords and the existing 8 KiB model.
"""
from __future__ import annotations

import argparse
import bisect
from collections import Counter, OrderedDict
import hashlib
import json
from pathlib import Path
import struct
import subprocess

LINES = 256
LINE_BYTES = 32
INSTRUCTION_BYTES = 2


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def runs(path):
    """Yield verified instruction runs, ignoring the separate data/DMA events."""
    with Path(path).open('rb') as stream:
        while block := stream.read(1024 * 1024):
            if len(block) % 8:
                raise ValueError(f'{path}: truncated hwtrace record')
            for pc, event in struct.iter_unpack('<II', block):
                if event >> 28 != 1:
                    continue
                count = event & 0x0fffffff
                if pc & 1 or not count:
                    raise ValueError(f'{path}: invalid halfword run at {pc:08x}')
                last = pc + INSTRUCTION_BYTES * (count - 1)
                if last > 0xffffffff or pc >> 29 != last >> 29:
                    raise ValueError(f'{path}: instruction run crosses an address segment')
                yield pc, count


class Replay:
    def __init__(self, iix=False):
        self.iix = iix
        self.cache = [None] * LINES
        self.previous_line = None
        self.lru = OrderedDict()
        self.seen = set()
        self.instructions = self.fills = self.uncached_fetches = 0
        self.first = self.conflict = self.capacity = 0
        self.evictions = Counter()
        self.line_fills = Counter()

    def run(self, pc, count):
        self.instructions += count
        first = (pc & 0x1fffffff) >> 5
        last = ((pc + INSTRUCTION_BYTES * (count - 1)) & 0x1fffffff) >> 5
        uncached = pc >> 29 == 5
        for line in range(first, last + 1):
            if line == self.previous_line:
                continue
            self.previous_line = line
            if uncached:
                self.uncached_fetches += 1
                continue
            slot = ((line & 0x7f) | (((line >> 20) & 1) << 7)) if self.iix else line & 255
            old = self.cache[slot]
            if old != line:
                self.fills += 1
                self.line_fills[line] += 1
                if line not in self.seen:
                    self.first += 1
                elif line in self.lru:
                    self.conflict += 1
                    if old is not None:
                        self.evictions[line, old] += 1
                else:
                    self.capacity += 1
                self.cache[slot] = line
            self.seen.add(line)
            self.lru[line] = None
            self.lru.move_to_end(line)
            if len(self.lru) > LINES:
                self.lru.popitem(last=False)


class Symbols:
    def __init__(self, elf, tool_prefix):
        output = subprocess.check_output(
            [tool_prefix + 'nm', '-S', '-n', '-C', '--defined-only', str(elf)], text=True)
        selected = {}
        for row in output.splitlines():
            fields = row.split(None, 3)
            if len(fields) != 4 or fields[2] not in ('t', 'T', 'w', 'W'):
                continue
            address, size = int(fields[0], 16), int(fields[1], 16)
            if size and (address not in selected or size > selected[address][0]):
                selected[address] = (size, fields[3])
        self.starts = sorted(selected)
        self.rows = [selected[address] for address in self.starts]

    def lookup(self, line):
        address = (line << 5) | 0x80000000
        i = bisect.bisect_right(self.starts, address) - 1
        owners = []
        if i >= 0 and address < self.starts[i] + self.rows[i][0]:
            owners.append(self.rows[i][1])
        # Multiple functions can share one cache line. A line label is not a
        # verified, independently movable linker input section.
        i += 1
        while i < len(self.starts) and self.starts[i] < address + LINE_BYTES:
            owners.append(self.rows[i][1])
            i += 1
        return ' / '.join(owners) + (' [shared line]' if len(owners) > 1 else '') if owners else '<unresolved/fixed>'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--elf', required=True, type=Path)
    parser.add_argument('--trace', required=True, nargs='+', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--expect-fills', type=int)
    parser.add_argument('--expect-instructions', type=int)
    parser.add_argument('--expect-elf-sha256')
    parser.add_argument('--tool-prefix', default='/opt/toolchains/dc/sh-elf/bin/sh-elf-')
    parser.add_argument('--iix', action='store_true')
    args = parser.parse_args()
    if args.out.exists():
        parser.error('output already exists; preserve prior receipts with a fresh path')
    with args.elf.open('rb') as stream:
        header = stream.read(52)
    if len(header) != 52 or header[:6] != b'\x7fELF\x01\x01' or struct.unpack_from('<H', header, 18)[0] != 42:
        parser.error('expected an uncompressed little-endian ELF32 SH program')
    elf_sha = sha256(args.elf)
    if args.expect_elf_sha256 is not None and elf_sha != args.expect_elf_sha256.lower():
        parser.error('ELF SHA-256 differs from the pinned baseline')
    replay = Replay(args.iix)
    inputs = []
    for trace in args.trace:
        start_fills, start_insns = replay.fills, replay.instructions
        for pc, count in runs(trace):
            replay.run(pc, count)
        row = dict(path=str(trace), sha256=sha256(trace), bytes=trace.stat().st_size,
                   instructions=replay.instructions - start_insns, fills=replay.fills - start_fills)
        inputs.append(row)
        print(json.dumps({'trace': trace.name, 'instructions': row['instructions'], 'fills': row['fills']}), flush=True)
    symbols = Symbols(args.elf, args.tool_prefix)
    matches = ((args.expect_fills is None or replay.fills == args.expect_fills) and
               (args.expect_instructions is None or replay.instructions == args.expect_instructions))
    report = {
        'scope': 'Instruction-cache POC, matching existing hwsim fetch convention. No layout, game, GPU, I/O or timing change.',
        'cache': dict(bytes=8192, lines=LINES, line_bytes=LINE_BYTES, instruction_bytes=INSTRUCTION_BYTES,
                      iix=args.iix, frame_boundary='Cache and last-line state carry across input files as existing hwsim does.'),
        'elf': dict(path=str(args.elf), sha256=elf_sha, machine=42),
        'replay_tool': dict(path=str(Path(__file__).resolve()), sha256=sha256(__file__)),
        'traces': inputs,
        'instructions': replay.instructions, 'fills': replay.fills,
        'uncached_line_fetches': replay.uncached_fetches,
        'lru_reference_classification': dict(first=replay.first, conflict=replay.conflict, capacity=replay.capacity),
        'classification_limits': 'Same-size fully associative LRU is a diagnostic reference, not a lower bound or predicted saving; initial recency is unknown.',
        'symbol_limits': 'Cache-line labels may cover multiple functions and do not prove independently movable linker-section ownership.',
        'expected_counts_match': matches,
        'baseline_expectations': dict(fills=args.expect_fills, instructions=args.expect_instructions,
                                      elf_sha256=args.expect_elf_sha256),
        'top_conflict_evictions': [dict(incoming=f'{a << 5:08x}', victim=f'{b << 5:08x}', count=n,
            incoming_symbol=symbols.lookup(a), victim_symbol=symbols.lookup(b))
            for (a, b), n in replay.evictions.most_common(40)],
        'top_filled_lines': [dict(physical=f'{line << 5:08x}', fills=n, symbol=symbols.lookup(line))
                             for line, n in replay.line_fills.most_common(30)],
        'provenance': 'Inspired by Byterset/MipsFit33c02662 temporal/cache diagnostics; reuses RE4 hwtrace/hwsim contracts. No upstream source copied.',
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as stream:
        stream.write(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ('instructions', 'fills', 'expected_counts_match')}))
    if not matches:
        raise SystemExit('POC rejected: counts differ from the pinned baseline')


if __name__ == '__main__':
    main()
