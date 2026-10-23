#!/usr/bin/env python3
"""Production certificate vs complete target-FMAC strip output on synthetic caches.

Transforms use exact sums of float matrix coefficients plus bounded FTRV error
perturbations. Reciprocals are deliberately perturbed; no FSRRA accuracy or
hardware execution is assumed. The unchanged C strip oracle supplies every
32-byte emitted vertex, including strip restart/EOL words.
"""
import argparse
import ctypes
import hashlib
import itertools
import json
import math
import random
import struct
import subprocess
import sys
from fractions import Fraction
from pathlib import Path


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
SOURCE = DC / "game/platform/backface_certificate.cpp"
HEADER = DC / "room/backface_certificate.hpp"
sys.path.insert(0, str(HERE.parent / "backface_sh4_kernel"))
import object_test as original  # noqa: E402


class Cone(ctypes.Structure):
    _fields_ = [("center", ctypes.c_float * 3), ("radius", ctypes.c_float),
                ("extent", ctypes.c_float * 3), ("axis", ctypes.c_float * 3),
                ("cos_lower", ctypes.c_float), ("sin_upper", ctypes.c_float),
                ("min_normal", ctypes.c_float)]


class Proof(ctypes.Structure):
    _fields_ = [(name, ctypes.c_float) for name in (
        "wlo", "whi", "x_bound", "y_bound", "x_error", "y_error", "area_lower", "x_span", "y_span")]
    _fields_.append(("valid", ctypes.c_bool))


def f32(value):
    try:
        return struct.unpack("<f", struct.pack("<f", value))[0]
    except OverflowError:
        return math.copysign(math.inf, value)


def adjacent(value, up):
    bits = struct.unpack("<I", struct.pack("<f", f32(value)))[0]
    bits += 1 if (value >= 0) == up else -1
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def column_matrix(x, y, w):
    rows = (x, y, w, w)
    return [f32(rows[r][c]) for c in range(4) for r in range(4)]


def cross(a, b, c):
    u = [b[j] - a[j] for j in range(3)]
    v = [c[j] - a[j] for j in range(3)]
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0])


def cone_for(points, indices, cosine=0.9995):
    lo = [min(p[a] for p in points) for a in range(3)]
    hi = [max(p[a] for p in points) for a in range(3)]
    center = [(a + b) / 2 for a, b in zip(lo, hi)]
    extent = [(b - a) / 2 for a, b in zip(lo, hi)]
    normals = []
    first = 0
    for end in range(len(indices)):
        if not indices[end] & 128 and end != len(indices) - 1:
            continue
        for j in range(first, end - 1):
            n = cross(*(points[indices[k] & 127] for k in (j, j + 1, j + 2)))
            if (j - first) & 1:
                n = tuple(-q for q in n)
            normals.append(n)
        first = end + 1
    valid = bool(normals) and all(any(n) for n in normals)
    axis = [sum(n[a] for n in normals) for a in range(3)]
    length = math.sqrt(sum(a * a for a in axis))
    if length:
        axis = [a / (2 * length) for a in axis]
    else:
        axis = [0.0, 0.0, 0.0]
    cosine = adjacent(cosine, False)
    sine = adjacent(math.sqrt(1 - cosine * cosine) + 1e-5, True)
    minimum = min((max(map(abs, n)) for n in normals), default=0)
    lower = float(2 ** math.floor(math.log2(minimum))) if valid and minimum else 0.0
    return Cone((ctypes.c_float * 3)(*center), adjacent(math.sqrt(sum(a * a for a in extent)), True),
                (ctypes.c_float * 3)(*extent), (ctypes.c_float * 3)(*axis), cosine, sine, lower)


def projected_cache(matrix, points, inverse_bias=0.0, ftrv_signs=(0, 0, 0), rng=None):
    output = bytearray()
    for i, point in enumerate(points):
        h = []
        for row, sign in zip((0, 1, 3), ftrv_signs):
            products = [float(matrix[4 * c + row]) * float((*point, 1)[c]) for c in range(4)]
            exact = math.fsum(products)
            # Use only half of the published FTRV envelope. The final float
            # rounding remains within the full envelope for these normal data.
            bound = max(map(abs, products)) * 2**-23 + max(abs(exact) * 2**-23, 2**-149)
            error = sign * bound * 0.45
            value = f32(exact + error)
            assert abs(value - exact) <= bound + 2**-149, (value, exact, bound)
            h.append(value)
        multiplier = 1.0 + inverse_bias * (rng.uniform(-1, 1) if rng else 1)
        inv = f32((1.0 / abs(h[2])) * multiplier) if h[2] else math.inf
        x, y = f32(h[0] * inv), f32(h[1] * inv)
        words = [0xDEADBEEF, original.fbits(x), original.fbits(y), original.fbits(inv),
                 0x3F000000 + i * 13, 0x3E800000 + i * 29, 0xFF123400 + i, 0x3D800000 + i * 19]
        output += struct.pack("<8I", *words)
    return bytes(output)


def plain_output(cache, indices):
    output = bytearray()
    for i, value in enumerate(indices):
        vertex = bytearray(cache[(value & 127) * 32:(value & 127) * 32 + 32])
        flag = 0xF0000000 if value & 128 or i + 1 == len(indices) else 0xE0000000
        struct.pack_into("<I", vertex, 0, flag)
        output += vertex
    return bytes(output)


def check_ideal_bounds(name, proof, matrix, points, indices):
    """Evaluate actual vertices with exact rationals, independently of the proof.

    These are checks of the conservative certificate's contract, not a second
    implementation of its interval algebra or cone margin.
    """
    homogeneous = []
    for point in points:
        p = (*point, 1)
        homogeneous.append([sum((Fraction(matrix[4*c+r]) * Fraction(p[c]) for c in range(4)), Fraction())
                            for r in (0, 1, 3)])
    assert all(Fraction(proof.wlo) <= p[2] <= Fraction(proof.whi) for p in homogeneous), (name, "W bounds")
    assert min(p[2] for p in homogeneous) > 0
    screen = [(p[0]/p[2], p[1]/p[2]) for p in homogeneous]
    for axis, absolute, span in ((0, proof.x_bound, proof.x_span), (1, proof.y_bound, proof.y_span)):
        coordinates = [p[axis] for p in screen]
        assert max(map(abs, coordinates)) <= Fraction(absolute), (name, "absolute projected bound", axis)
        assert max(coordinates)-min(coordinates) <= Fraction(span), (name, "projected span", axis)
    start = 0
    for end, value in enumerate(indices):
        if not value & 128 and end != len(indices)-1:
            continue
        for i in range(start, end-1):
            a, b, c = (screen[indices[j] & 127] for j in (i, i+1, i+2))
            area = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
            assert abs(area) >= Fraction(proof.area_lower), (name, "ideal area lower bound", i)
        start = end+1


def load_library(path):
    lib = ctypes.CDLL(str(path))
    lib.cone_probe.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.c_float, ctypes.POINTER(Cone),
                              ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(Proof)]
    lib.cone_probe.restype = ctypes.c_uint
    lib.cone_strict.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]
    lib.cone_strict.restype = ctypes.c_uint
    lib.cone_normal.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.c_float, ctypes.POINTER(ctypes.c_int64)]
    lib.cone_normal.restype = ctypes.c_float
    lib.cone_projected.argtypes = [ctypes.POINTER(Proof), ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
    lib.cone_projected.restype = ctypes.c_uint
    lib.cone_strict_layout.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
    lib.cone_strict_layout.restype = ctypes.c_uint
    lib.cone_worth.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]
    lib.cone_worth.restype = ctypes.c_uint
    lib.cone_flat.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)]
    lib.cone_flat.restype = ctypes.c_uint
    return lib


def probe(lib, matrix, cone, cache, cull=1, near=1):
    proof = Proof()
    result = lib.cone_probe((ctypes.c_float * 16)(*matrix), near, ctypes.byref(cone),
                           cull, cache, len(cache) // 32, ctypes.byref(proof))
    return result, proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--host-cxx", default="g++")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output.resolve()
    commands = []
    command = [args.host_cxx, "-std=c++17", "-O2", "-fno-fast-math", "-ffp-contract=off",
               "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", "-I" + str(DC / "room"),
               str(SOURCE), str(HERE / "helper_fixture.cpp"), "-o", str(output / "helper.so")]
    subprocess.run(command, check=True)
    commands.append(command)
    oracle_directory = output / "oracle"
    oracle_directory.mkdir()
    command = [sys.executable, str(HERE.parent / "backface_sh4_kernel/build_oracle.py"),
               "--output", str(oracle_directory)]
    subprocess.run(command, check=True)
    commands.append(command)
    oracle = original.oracle_load(oracle_directory / "oracle.so")
    lib = load_library(output / "helper.so")
    assert lib.cone_sizes(1) == ctypes.sizeof(Cone) == 52
    assert lib.cone_sizes(2) == ctypes.sizeof(Proof) == 40
    admission_controls = []
    for vertices, indices, strips, expected in (
            (0, 256, 64, 0), (2, 256, 64, 0), (3, 255, 64, 0),
            (3, 256, 63, 0), (3, 256, 64, 1), (64, 256, 64, 1),
            (65, 256, 64, 0), (65, 260, 64, 1), (64, 294, 98, 1),
            (64, 196, 49, 0), (64, 112, 7, 0), (128, 128, 1, 0),
            (3, 256, 0, 0), (3, 256, 0xFFFFFFFF, 1),
            (0x3FFFFFFF, 0xFFFFFFFF, 64, 1), (0x40000000, 0xFFFFFFFF, 64, 0),
            (0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0)):
        assert lib.cone_worth(vertices, indices, strips) == expected
        admission_controls.append(dict(vertices=vertices, indices=indices, strips=strips, admitted=bool(expected)))
    for wrow, extent, expected in (((0, 0, -1, 8192), (1, 1, 0), 1),
                                   ((0, 0, -1, 8192), (1, 1, 1), 0),
                                   ((0.25, 0, -1, 8192), (1, 1, 0), 0),
                                   ((0.25, 0, -1, 8192), (0, 1, 0), 1),
                                   ((0, -0.0, -1, 8192), (1, 1, 0), 1)):
        m = column_matrix((1, 0, 0, 0), (0, 1, 0, 0), wrow)
        assert lib.cone_flat((ctypes.c_float * 16)(*m), (ctypes.c_float * 3)(*extent)) == expected
        admission_controls.append(dict(wrow=wrow, extent=extent, flat=bool(expected)))
    rng = random.Random(0xC023F012)
    counts = dict(cases=0, prepared=0, front_candidate=0, front_accepted=0,
                  back_suggestion=0, complete_packet_comparisons=0, ideal_bound_checks=0)
    fixtures = []

    def check(name, points, indices, matrix, cone=None, cache=None, cull=1, near=1,
              require=None, record=False):
        cone = cone or cone_for(points, indices)
        cache = cache if cache is not None else projected_cache(matrix, points)
        flags, proof = probe(lib, matrix, cone, cache, cull, near)
        candidate = bool(flags & 4)
        accepted = bool(flags & 16)
        counts["cases"] += 1
        counts["prepared"] += bool(flags & 1)
        counts["front_candidate"] += candidate
        counts["front_accepted"] += accepted
        counts["back_suggestion"] += (flags >> 1 & 3) == 1
        if proof.valid:
            check_ideal_bounds(name, proof, matrix, points, indices)
            counts["ideal_bound_checks"] += 1
        strict = bool(lib.cone_strict(cache, bytes(indices), len(indices), cull, 1))
        expected, pieces = oracle(cache, bytes(indices), 0x17F, cull)
        direct = plain_output(cache, indices)
        # Validate the production check-mode oracle against the independent
        # original strip output on cases with no retained inner back run.
        if strict:
            assert expected == direct, (name, "strict oracle disagrees")
        if accepted:
            assert candidate and strict and expected == direct, (name, flags, vars(proof), len(expected), len(direct))
            counts["complete_packet_comparisons"] += 1
        if require == "front":
            assert accepted, (name, flags, [(n, getattr(proof, n)) for n, _ in Proof._fields_])
        elif require == "uncertain":
            assert not accepted, (name, flags)
        elif require == "back":
            assert (flags >> 1 & 3) == 1 and not accepted, (name, flags)
        if record:
            fixtures.append(dict(case=name, flags=flags, strict_front=strict,
                                 original_vertices=len(expected) // 32, plain_vertices=len(direct) // 32,
                                 pieces=pieces, matrix=matrix, points=points, indices=list(indices),
                                 cone=list(struct.unpack("<13f", bytes(cone))),
                                 cache_hex=cache.hex(), proof={n: getattr(proof, n) for n, _ in Proof._fields_}))
        return flags, proof

    points = [(-100, -100, 0), (100, -100, 0), (-100, 100, 0)]
    indices = bytes([0, 1, 130])
    matrix = column_matrix((1, 0, -320, 320000), (0, 1, -240, 240000), (0, 0, -1, 1000))
    _, ordinary_proof = check("ordinary-front", points, indices, matrix, require="front", record=True)
    alignment_controls = []
    ordinary_cache = projected_cache(matrix, points)
    for stride in (12, 16, 17, 20, 32, 33, 36):
        for misalignment in range(4):
            backing = ctypes.create_string_buffer(stride*3 + 16)
            pointer = ctypes.addressof(backing) + misalignment
            assert ctypes.addressof(backing) % 4 == 0
            for i in range(3):
                ctypes.memmove(pointer+i*stride, ordinary_cache[i*32:i*32+16], 16)
            expected = int(stride >= 16 and stride % 4 == 0 and misalignment == 0)
            projected = lib.cone_projected(ctypes.byref(ordinary_proof), pointer, 3, stride)
            strict = lib.cone_strict_layout(pointer, indices, 3, stride)
            assert projected == strict == expected, (stride, misalignment, projected, strict)
            alignment_controls.append(dict(stride=stride, misalignment=misalignment, accepted=bool(expected)))
    for vertices in (0, 1, 2):
        assert not lib.cone_projected(ctypes.byref(ordinary_proof), ordinary_cache, vertices, 32)
    assert not lib.cone_projected(ctypes.byref(ordinary_proof), None, 3, 32)
    check("opposite-cull", points, indices, matrix, cull=2, require="back", record=True)
    for field in (0, 1, 3, 4, 7, 11, 12, 13, 15):
        for invalid in (math.nan, math.inf, -math.inf, 2**-149, 2**50):
            m = list(matrix)
            m[field] = invalid
            check("invalid-matrix", points, indices, m, cache=projected_cache(matrix, points), require="uncertain")
    for cull in (0, 3, 255):
        check("invalid-cull", points, indices, matrix, cull=cull, require="uncertain")
    for near in (0, -1, math.nan, math.inf, 1000, 1001):
        check("near-boundary", points, indices, matrix, near=near, require="uncertain")
    for label, wrow in (("all-behind-eye", (0, 0, -1, -1000)),
                        ("crosses-eye-plane", (8, 0, -1, 0)),
                        ("crosses-near-plane", (0.005, 0, -1, 1))):
        altered = column_matrix((1, 0, -320, 320000), (0, 1, -240, 240000), wrow)
        check(label, points, indices, altered, require="uncertain", record=True)
    for cull in (1, 2):
        degenerate = [(0, 0, 0), (100, 0, 0), (200, 0, 0)]
        check("degenerate", degenerate, indices, matrix, cull=cull, require="uncertain", record=True)
        short = bytes([0, 129])
        check("short-strip", points[:2], short, matrix, cull=cull, require="uncertain")
    for offset in (4, 8, 12):
        invalids = (math.nan, math.inf, 2**-149) + ((0.0, -1.0) if offset == 12 else ())
        for invalid in invalids:
            cache = bytearray(projected_cache(matrix, points))
            struct.pack_into("<f", cache, offset, invalid)
            check("nonfinite-or-invalid-cache", points, indices, matrix, cache=bytes(cache), require="uncertain")

    sliver = [(0, 0, 0), (5363, 5362, 0), (5362, 5361, 0)]
    witness = column_matrix((2.5, 0, 0, 327680), (0, -1.875, 0, 245760), (0, 0, -1/128, 1024))
    cache = projected_cache(witness, sliver)
    expected_screen = [(320.0, 240.0), (333.09326171875, 230.181884765625),
                       (333.0908203125, 230.1837158203125)]
    assert [struct.unpack_from("<2f", cache, 32*i+4) for i in range(3)] == expected_screen
    check("nondegenerate-target-fmac-sign-flip", sliver, indices, witness,
          cache=cache, require="uncertain", record=True)
    check("back-is-not-target-rejection", sliver, indices, witness,
          cache=cache, cull=2, require="back", record=True)
    assert oracle(cache, indices, 0x17F, 1)[0] == b""
    assert oracle(cache, indices, 0x17F, 2)[0] == plain_output(cache, indices)

    # Same real geometry, changing animation/model matrices, reflections,
    # shears, perspective slopes and deliberately nonuniform reciprocal error.
    for case in range(800):
        size = rng.choice((16, 64, 128, 256, 512))
        pts = [(-size, -size, 0), (size, -size, 0), (-size, size, 0)]
        reflect = rng.choice((-1, 1))
        scale = rng.choice((0.125, 0.5, 1, 2, 4))
        shear = rng.choice((0, -0.25, 0.25, 1))
        w = rng.choice((256, 512, 1024, 2048))
        depth_x, depth_y = (rng.choice((0, 0, 0, -0.03125, 0.03125)) for _ in range(2))
        m = column_matrix((reflect*scale+320*depth_x, shear+320*depth_y, -320, 320*w),
                          (240*depth_x, scale+240*depth_y, -240, 240*w),
                          (depth_x, depth_y, -1, w))
        bias = rng.choice((0, 0, 1e-5, 1e-3, 0.1, 0.5))
        signs = tuple(rng.choice((-1, 0, 1)) for _ in range(3))
        observed = projected_cache(m, pts, bias, signs, rng)
        check("randomized-affine-and-observed-reciprocal", pts, indices, m,
              cache=observed, cull=1 if reflect > 0 else 2)

    # Multiple actor EOL boundaries and strip parity, with all vertex words
    # deliberately distinct. Coordinate-only comparisons could miss corruption.
    repeated = points * 8
    stream = bytes(j | (128 if i % 3 == 2 else 0) for i, j in enumerate(range(len(repeated))))
    check("eight-strips-all-words", repeated, stream, matrix, require="front", record=True)
    for signs in itertools.product((-1, 1), repeat=3):
        check("ftrv-envelope-corners", points, indices, matrix,
              cache=projected_cache(matrix, points, ftrv_signs=signs), require="front")

    # Exact integer normal components, including products beyond 32 bits.
    axis = (ctypes.c_float * 3)(0, 0, 0.5)
    for normal, expected in (((0, 0, 0), 0), ((0, 0, 1), 1),
                             ((0, 0, 1600), 1024), ((0, 0, 65535**2), 2**31),
                             ((0, 0, -1600), 0), ((2**33, 0, 1), 0)):
        got = lib.cone_normal(axis, ctypes.c_float(0.999), (ctypes.c_int64 * 3)(*normal))
        assert got == expected, (normal, got, expected)
    assert counts["front_accepted"] >= 20, counts
    assert counts["front_accepted"] < counts["front_candidate"], counts
    report = dict(scope=__doc__, counts=counts, fixtures=fixtures, commands=commands,
                  alignment_controls=alignment_controls,
                  admission_controls=admission_controls,
                  source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in (SOURCE, HEADER, HERE / "helper_fixture.cpp", Path(__file__))},
                  limitations="Synthetic bounded-transform caches and host execution; no exact FTRV/FSRRA emulation, scene, or hardware claim. Back is a geometric suggestion only.")
    (output / "helper-controls.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print("PASS production helper:", json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    main()
