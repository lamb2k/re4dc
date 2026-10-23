#!/usr/bin/env python3
"""Asset-free tests of the actual scenery converter's optional front certificate."""
import argparse
import hashlib
import importlib.util
import json
import math
import struct
import subprocess
import sys
import types
import zlib
from pathlib import Path


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
SOURCE = DC / "tools/d367/scenery21/scn21_build.py"


def align(n):
    return (n + 15) & ~15


def fixture(path, levels):
    """One synthetic part, one cluster, one meshlet at each LOD; no source assets."""
    nlet = len(levels)
    omesh = 112
    opart = align(omesh + 68)
    oplod = align(opart + 36)
    ocluster = align(oplod + 8)
    olevel = align(ocluster + 20)
    olet = align(olevel + 12 * nlet)
    overt = align(olet + 28 * nlet)
    nvert = sum(len(positions) for positions, _ in levels)
    ostrips = align(overt + 12 * nvert)
    streams = [b"".join(bytes([len(ix)]) + bytes(ix) for ix in strips)
               for _, strips in levels]
    mesh = bytearray(align(ostrips + sum(map(len, streams))))
    struct.pack_into("<4s19I", mesh, 0, b"R4IM", 3, len(mesh), 0, 1, 1,
                     nlet, nvert, sum(map(len, streams)), 0,
                     omesh, opart, olet, overt, ostrips, len(mesh), 0, 0, 0, 0)
    struct.pack_into("<5I", mesh, 80, 1, nlet, oplod, ocluster, olevel)
    struct.pack_into("<HBBHHIII12f", mesh, omesh, 0, 0, 0, 0, 0, 0, 0, 1,
                     0, 0, 0, 1, 1, 1, 0, 0, 0, 65535, 65535, 65535)
    struct.pack_into("<II", mesh, opart + 12, 0, nlet)
    struct.pack_into("<II", mesh, oplod, 0, 1)
    struct.pack_into("<6HII", mesh, ocluster, 0, 0, 0, 65535, 65535, 65535, 0, nlet)
    first = start = 0
    for number, ((positions, strips), stream) in enumerate(zip(levels, streams)):
        struct.pack_into("<IIf", mesh, olevel + 12 * number, number, 1, float(number))
        lo = [min(p[a] for p in positions) for a in range(3)]
        hi = [max(p[a] for p in positions) for a in range(3)]
        struct.pack_into("<IIIHH6H", mesh, olet + 28 * number, first, start,
                         len(stream), len(positions), len(strips), *lo, *hi)
        for index, position in enumerate(positions):
            struct.pack_into("<6H", mesh, overt + 12 * (first + index), *position,
                             index * 31, index * 47, 0x7FFF)
        mesh[ostrips + start:ostrips + start + len(stream)] = stream
        first += len(positions)
        start += len(stream)
    struct.pack_into("<I", mesh, 12, zlib.crc32(mesh[80:]) & 0xFFFFFFFF)
    side = bytearray(48)
    struct.pack_into("<4s7I", side, 0, b"R4PW", 1, 0, 1, 0, 0x12345678, 0, 0)
    mesh_path, side_path = path / "synthetic.re4mesh", path / "synthetic.r4pw"
    mesh_path.write_bytes(mesh)
    side_path.write_bytes(side)
    return mesh_path, side_path


def load_source(name, text):
    module = types.ModuleType(name)
    module.__file__ = str(SOURCE)
    exec(compile(text, str(SOURCE), "exec"), module.__dict__)
    return module


def minimum_cross(positions, strips):
    bound = None
    for indices in strips:
        if len(indices) < 3:
            return 0.0
        for i in range(len(indices) - 2):
            a, b, c = (positions[j] for j in indices[i:i + 3])
            u = [b[j] - a[j] for j in range(3)]
            v = [c[j] - a[j] for j in range(3)]
            n = (u[1] * v[2] - u[2] * v[1],
                 u[2] * v[0] - u[0] * v[2],
                 u[0] * v[1] - u[1] * v[0])
            value = max(map(abs, n))
            if not value:
                return 0.0
            lower = float(1 << (value.bit_length() - 1))
            bound = lower if bound is None else min(bound, lower)
    return bound or 0.0


def parse_front(data, groups):
    mesh_crc, mesh_bytes, nlet, recorded_groups = struct.unpack_from("<4I", data)
    assert recorded_groups == groups
    start = align(272 + 8 * nlet * groups)
    header = struct.unpack_from("<4s7I", data, start)
    tag, version, total, sg_crc, crc, size, lets, ng = header
    assert (tag, version, crc, size, lets, ng) == (b"SCCF", 1, mesh_crc, mesh_bytes, nlet, groups), header
    count = nlet * groups
    assert total == align(544 + 8 * count) == len(data) - start, (total, len(data), start)
    angles = [struct.unpack_from("<2f", data, start + 32 + 8 * k) for k in range(64)]
    minima = struct.unpack_from("<%df" % (nlet * groups), data, start + 32 + 512)
    counts = [struct.unpack_from("<HH", data, start + 544 + 4 * count + 4 * k)
              for k in range(count)]
    assert all(math.isfinite(x) and x >= 0 for x in minima)
    assert not any(data[start + 544 + 8 * count:]), "nonzero trailer padding"
    return start, sg_crc, angles, minima, counts


def check_group_spans(r4sg, counts, groups):
    """Serialized cardinalities must cover the existing byte-counted strips."""
    previous = 0
    for k, (indices, strips) in enumerate(counts):
        if not k % groups:
            previous = 0
        end = struct.unpack_from("<H", r4sg, 32 + 16 * k + 12)[0]
        assert indices + strips == end - previous, (k, indices, strips, end, previous)
        previous = end


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", default="d1bc83cff32217a659f93acd5837a1ecc96ff6c3")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output.resolve()
    current = load_source("cone_current", SOURCE.read_text())
    original = load_source("cone_original", subprocess.check_output(
        ["git", "show", args.baseline + ":" + str(SOURCE.relative_to(ROOT))], cwd=ROOT, text=True))
    cases = [
        ("ordinary", [(100, 100, 100), (140, 100, 100), (100, 140, 100)], [[0, 1, 2]]),
        ("raw-unit-area", [(0, 0, 0), (5363, 5362, 0), (5362, 5361, 0)], [[0, 1, 2]]),
        ("degenerate", [(0, 0, 0), (10, 0, 0), (20, 0, 0)], [[0, 1, 2]]),
        ("mixed-degenerate", [(0, 0, 0), (10, 0, 0), (0, 10, 0), (20, 0, 0)], [[0, 1, 2], [0, 1, 3]]),
        ("connector-degenerate", [(0, 0, 0), (10, 0, 0), (0, 10, 0)], [[0, 1, 2, 2, 1, 0]]),
        ("max-coordinate", [(0, 0, 0), (65535, 0, 0), (0, 65535, 0)], [[0, 1, 2]]),
        ("short-strip", [(0, 0, 0), (1, 0, 0)], [[0, 1]]),
    ]
    records = []
    for name, positions, strips in cases:
        directory = output / name
        directory.mkdir()
        files = fixture(directory, [(positions, strips)])
        old = original.build_room(*files, 1, False)
        default = current.build_room(*files, 1, False)
        assert old == default, (name, "default converter changed")
        enhanced = current.build_room(*files, 1, False, front_proof=True)
        assert enhanced[:2] == default[:2] and enhanced[3] == default[3], name
        assert enhanced[2].startswith(default[2]), name
        start, sg_crc, angles, minima, counts = parse_front(enhanced[2], 1)
        assert sg_crc == zlib.crc32(enhanced[1][32:]) & 0xFFFFFFFF
        assert counts == [(sum(map(len, strips)), len(strips))], (name, counts)
        check_group_spans(enhanced[1], counts, 1)
        expected = minimum_cross(positions, strips)
        # No valid geometric cone => no front proof, even with a nonzero area.
        if not enhanced[2][272 + 3]:
            expected = 0
        assert minima == (expected,), (name, minima, expected)
        for k, (cos_lower, sin_upper) in enumerate(angles):
            if not k:
                continue
            theta = k * current.KSTEP
            assert cos_lower <= math.cos(theta), (k, cos_lower)
            assert sin_upper >= math.sin(theta), (k, sin_upper)
        repeat = current.build_room(*files, 1, False, front_proof=True)
        assert enhanced == repeat, (name, "nondeterministic converter")
        (directory / "legacy.sccn").write_bytes(default[2])
        (directory / "front.sccn").write_bytes(enhanced[2])
        records.append(dict(case=name, minimum=expected, default_bytes=len(default[2]),
                            proof_bytes=len(enhanced[2]) - start, counts=counts,
                            sccn_sha256=hashlib.sha256(enhanced[2]).hexdigest()))
    # Every LOD gets its own proof record: the second level must not inherit
    # the valid area floor from level zero.
    directory = output / "lod-degenerate"
    directory.mkdir()
    files = fixture(directory, [(cases[0][1], cases[0][2]), (cases[2][1], cases[2][2])])
    result = current.build_room(*files, 1, False, front_proof=True)
    _, _, _, minima, counts = parse_front(result[2], 1)
    assert minima == (minimum_cross(cases[0][1], cases[0][2]), 0), minima
    assert counts == [(3, 1), (3, 1)], counts
    check_group_spans(result[1], counts, 1)
    records.append(dict(case="lod-degenerate", minima=minima, counts=counts))
    # Spare group slots must carry zero cardinalities, not inherited counts.
    directory = output / "spare-groups"
    directory.mkdir()
    files = fixture(directory, [(cases[0][1], cases[0][2])])
    result = current.build_room(*files, 4, False, front_proof=True)
    _, _, _, minima, counts = parse_front(result[2], 4)
    assert counts == [(3, 1), (0, 0), (0, 0), (0, 0)], counts
    assert minima == (minimum_cross(cases[0][1], cases[0][2]), 0, 0, 0), minima
    check_group_spans(result[1], counts, 4)
    records.append(dict(case="spare-groups", minima=minima, counts=counts))
    report = dict(scope=__doc__, baseline=args.baseline, cases=records,
                  source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  limits="Synthetic converter output only; runtime trailer rejection and actual target emission are separate gates.")
    (output / "world-producer-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS world producer: %d synthetic cases, exact legacy default output" % len(records))


if __name__ == "__main__":
    main()
