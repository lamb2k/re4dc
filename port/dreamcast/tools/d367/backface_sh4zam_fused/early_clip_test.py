#!/usr/bin/env python3
"""Check early clipping against the C oracle and count executed SH4 instructions.

The counts come from the real linked opcodes, including the complete public
caller. They are NOT cycles, elapsed Dreamcast time, or game-frame speedups.
Both input directories must contain trace0/trace1 objects and linked callers;
the baseline directory also supplies the unchanged target-lowered C oracle.
"""
import argparse
import itertools
import json
import random
import struct
from pathlib import Path


HERE = Path(__file__).resolve().parent
# Reuse exactly the established world caller interpreter and oracle adapter.
# caller_test.py has a command-line body; sq_guard_test.py uses this same split.
CALLER = (HERE / "caller_test.py").read_text()
DEFINITIONS = CALLER.split("p=argparse.ArgumentParser(description=__doc__)", 1)[0]
NAMESPACE = {"__file__": str(HERE / "caller_test.py"), "__doc__": __doc__}
exec(compile(DEFINITIONS, str(HERE / "caller_test.py"), "exec"), NAMESPACE)
BASE = NAMESPACE["base"]
EXPECTED = NAMESPACE["expected"]


class CountedWorld(NAMESPACE["WalkMachine"]):
    def __init__(self, *args, **kwargs):
        self.sq_stores = 0
        self.outcode_reads = 0
        super().__init__(*args, **kwargs)

    def write(self, address, value, length):
        if 0xE0000000 <= address < 0xE0010000:
            self.sq_stores += 1
        super().write(address, value, length)

    def read(self, address, length):
        if 0xA000 <= address < 0xA100:
            self.outcode_reads += 1
        return super().read(address, length)


def programs(directory):
    result = []
    for trace in (0, 1):
        path = directory / ("walk-trace%d.elf" % trace)
        result.append((BASE.text_section(path),
                       struct.unpack_from("<I", path.read_bytes(), 24)[0]))
    return result


def execute(program, cache, stream, outcodes, limit, cull, trace=0, fpscr=0):
    text, entry = program
    machine = CountedWorld(text, cache, stream, outcodes, limit, cull,
                           fpscr=fpscr, trace=bool(trace))
    machine.pc = entry
    result = machine.run()
    assert machine.written == [0, 0], "partial uncommitted SQ burst"
    return result, machine


def patterned_cache(triangles, front_mask):
    ys = [0.0, 1.0]
    for i in range(triangles):
        step = (-1.0 if (front_mask >> i) & 1 else 1.0)
        ys.append(2 * ys[-1] - ys[-2] + step * (-1.0 if i & 1 else 1.0))
    return BASE.generated_cache(list(enumerate(ys)))


def benchmark(baseline, candidate, oracle):
    rows = []
    n = 64
    strip = bytes([n]) + bytes(range(n))
    valid = (1 << (n - 2)) - 1
    cases = []
    for kind, mask in (("all-front", valid), ("all-back", 0),
                       ("mixed", int("001111000111" * 6, 2) & valid)):
        cache = patterned_cache(n - 2, mask)
        for batch in (1, 32):
            cases.append((kind, cache, strip * batch, bytes(n), 255, batch))
    cache = patterned_cache(n - 2, valid)
    for position in (1, 2, 3, 7, 31, 32, 62, 63):
        outcodes = bytearray(n)
        outcodes[position] = 1
        cases.append(("depth-cross-at-%d" % position, cache, strip,
                      bytes(outcodes), 255, 1))
    for kind, code, limit in (("depth-all", 1, 255),
                               ("screen-all", 4, 255),
                               ("oversize", 0, 63)):
        cases.append((kind, cache, strip, bytes([code]) * n, limit, 1))
    codes = bytearray(n)
    codes[0] = 4
    cases.append(("first-screen-eligible", cache, strip, bytes(codes), 255, 1))
    for name, cache, stream, outcodes, limit, batch in cases:
        before, old = execute(baseline[0], cache, stream, outcodes, limit, 2)
        after, new = execute(candidate[0], cache, stream, outcodes, limit, 2)
        want = EXPECTED(oracle, cache, stream, outcodes, limit, 2)
        assert before == after == want, (name, batch, "output mismatch")
        rows.append(dict(
            pattern=name, indices_per_strip=n, batch=batch,
            baseline_instructions=old.steps, candidate_instructions=new.steps,
            instructions_removed=old.steps - new.steps,
            instruction_reduction_percent=100.0 * (old.steps - new.steps) / old.steps,
            instruction_count_ratio=old.steps / new.steps,
            baseline_area_operations=old.area_ops,
            candidate_area_operations=new.area_ops,
            baseline_outcode_reads=old.outcode_reads,
            candidate_outcode_reads=new.outcode_reads,
            emitted_bytes=len(after[0]),
        ))
    return rows


def controls(candidate, oracle):
    rng = random.Random(0xEC11F23)
    cache = BASE.generated_cache([(rng.uniform(-640, 640), rng.uniform(-480, 480))
                                  for _ in range(256)])
    passed = 0
    cases = []
    sizes = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 31, 32, 33, 34,
             63, 64, 65, 119, 255)
    for n in sizes:
        positions = range(1, n) if n == 64 else sorted({1, n // 2, n - 1})
        for position, first, depth in itertools.product(positions, (0, 64, 128, 192), (1, 2)):
            oc = bytearray(256)
            oc[0] = first
            oc[position] = depth
            cases.append((bytes([n]) + bytes(range(n)), bytes(oc), 255,
                          n, position, "crossing"))
    # An emitted prefix and an unread suffix verify additive counters and the
    # original stop pointer; the crossing strip must not write even partial SQ.
    prefix = bytes([3, 220, 221, 222])
    suffix = bytes([3, 230, 231, 232])
    for position in range(1, 64):
        oc = bytearray(256)
        oc[position] = 3
        cases.append((prefix + bytes([64]) + bytes(range(64)) + suffix,
                      bytes(oc), 255, 64, position, "prefix"))
    # The first-zero specialization must not change all-depth-before-limit,
    # screen rejection, screen/depth priority, or long-strip fallback.
    for n, code, limit in itertools.product((1, 2, 3, 64, 65, 255),
                                           (1, 2, 3, 4, 8, 16, 32, 60, 255),
                                           (0, 63, 255)):
        cases.append((bytes([n]) + bytes(range(n)), bytes([code]) * 256,
                      limit, n, 0, "ordering"))
    for stream, oc, limit, n, position, kind in cases:
        for cull, trace in itertools.product((1, 2), (0, 1)):
            want = EXPECTED(oracle, cache, stream, oc, limit, cull)
            got, machine = execute(candidate[trace], cache, stream, oc, limit,
                                   cull, trace)
            assert got == want, (kind, n, position, cull, trace, got[1:], want[1:])
            if kind == "crossing":
                assert machine.sq_stores == 0, (n, position, "SQ write before clip")
                if n <= 64 and position <= 2:
                    assert machine.area_ops == 0, (n, position, machine.area_ops)
                if n <= 64 and position > 2:
                    assert machine.area_ops < max(0, n - 2) * 7, (n, position, machine.area_ops)
            if kind == "prefix":
                _, prefix_only = execute(candidate[trace], cache, prefix, oc,
                                         limit, cull, trace)
                assert machine.sq_stores == prefix_only.sq_stores
            passed += 1
    # Exercise restoration after early exits, not just the accepted mode path
    # already covered by caller_test.py.
    for bits, trace, position in itertools.product(range(16), (0, 1), (1, 31, 63)):
        fpscr = ((bits & 1) << 21) | ((bits & 2) << 19) | ((bits & 4) << 17) | ((bits & 8) << 15)
        oc = bytearray(256)
        oc[position] = 1
        stream = bytes([64]) + bytes(range(64))
        got, machine = execute(candidate[trace], cache, stream, bytes(oc), 255,
                               2, trace, fpscr)
        assert got == EXPECTED(oracle, cache, stream, oc, 255, 2)
        assert machine.sq_stores == 0
        passed += 1
    return dict(comparisons=passed, cases=len(cases), fpscr_early_exit_controls=96,
                every_64_index_crossing_position=True, high_outcode_bits=True,
                no_sq_store_before_clip=True, exact_stop_pointer_and_counts=True,
                ordering_and_long_fallback=True, sizes=list(sizes))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--benchmark-only", action="store_true")
    args = parser.parse_args()
    assert not args.report.exists(), "report path must be new"
    baseline, candidate = programs(args.baseline), programs(args.candidate)
    oracle = BASE.oracle_load(args.baseline / "oracle.so")
    report = dict(
        scope="Actual SH4 opcodes, host interpretation, synthetic geometry",
        metric="Executed instructions, not cycles or wall time",
        hardware_or_frame_speedup_claim=False,
        benchmark=benchmark(baseline, candidate, oracle),
        controls=None if args.benchmark_only else controls(candidate, oracle),
        files={arm: {p.name: BASE.sha(p.read_bytes()) for p in directory.glob("walk-trace*.elf")}
               for arm, directory in (("baseline", args.baseline), ("candidate", args.candidate))},
        source_sha256=BASE.sha(Path(__file__).read_bytes()),
    )
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
