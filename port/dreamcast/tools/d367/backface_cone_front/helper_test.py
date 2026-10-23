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
        "wlo", "whi", "x_bound", "y_bound", "x_error", "y_error", "w_error", "area_lower", "x_span", "y_span")]
    _fields_.append(("valid", ctypes.c_bool))


class RawPositions(ctypes.Structure):
    _fields_ = [("data", ctypes.c_void_p), ("stride", ctypes.c_uint),
                ("indices", ctypes.c_void_p), ("index_stride", ctypes.c_uint),
                ("unsigned_values", ctypes.c_bool)]


class RawBuffer:
    """Own a raw XYZ pool and optional reordered index records for the API."""
    def __init__(self, points, unsigned=False, indexed=False, stride=8,
                 index_stride=2, data_offset=0, index_offset=0):
        n = len(points)
        self.data = ctypes.create_string_buffer(max(8, stride) * n + data_offset + 16)
        self.indices = ctypes.create_string_buffer(max(2, index_stride) * n + index_offset + 4) if indexed else None
        data_address = ctypes.addressof(self.data) + data_offset
        index_address = ctypes.addressof(self.indices) + index_offset if indexed else None
        for i, point in enumerate(points):
            assert all(int(x) == x for x in point), point
            slot = n - 1 - i if indexed else i
            ctypes.memmove(data_address + slot * stride,
                           struct.pack("<3H" if unsigned else "<3h", *map(int, point)), 6)
            if indexed:
                ctypes.memmove(index_address + i * index_stride, struct.pack("<H", slot), 2)
        self.layout = RawPositions(data_address, stride, index_address, index_stride, unsigned)


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


def cone_for(points, indices, cosine=0.9995, axis_length=0.5):
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
        axis = [axis_length * a / length for a in axis]
    else:
        axis = [0.0, 0.0, 0.0]
    if valid and length:
        # Curved fixtures use a cone that includes every exact integer normal;
        # the small downward margin covers construction rounding here.
        cosine = min(cosine, min(sum(axis[a] * n[a] for a in range(3)) /
                                (math.sqrt(sum(q*q for q in axis)) * math.sqrt(sum(q*q for q in n)))
                                for n in normals) - 1e-5)
    cosine = adjacent(cosine, False)
    sine = adjacent(math.sqrt(1 - cosine * cosine) + 1e-5, True)
    minimum = min((max(map(abs, n)) for n in normals), default=0)
    lower = float(2 ** math.floor(math.log2(minimum))) if valid and minimum else 0.0
    return Cone((ctypes.c_float * 3)(*center), adjacent(math.sqrt(sum(a * a for a in extent)), True),
                (ctypes.c_float * 3)(*extent), (ctypes.c_float * 3)(*axis), cosine, sine, lower)


def projected_cache(matrix, points, inverse_bias=0.0, ftrv_signs=(0, 0, 0), rng=None,
                    inverse_values=None):
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
        inv = (f32(inverse_values[i]) if inverse_values is not None else
               f32((1.0 / abs(h[2])) * multiplier) if h[2] else math.inf)
        x, y = f32(h[0] * inv), f32(h[1] * inv)
        words = [0xDEADBEEF, original.fbits(x), original.fbits(y), original.fbits(inv),
                 0x3F000000 + i * 13, 0x3E800000 + i * 29, 0xFF123400 + i, 0x3D800000 + i * 19]
        output += struct.pack("<8I", *words)
    return bytes(output)


def camera_matrix(yaw=0, pitch=0, skew=0, distance=2048, reflect=False):
    """Rotated pinhole camera; stored coefficients are the actual float matrix."""
    yaw, pitch = math.radians(yaw), math.radians(pitch)
    right = (math.cos(yaw), 0, -math.sin(yaw))
    up = (math.sin(yaw)*math.sin(pitch), math.cos(pitch), math.cos(yaw)*math.sin(pitch))
    depth = (-math.sin(yaw)*math.cos(pitch), math.sin(pitch), -math.cos(yaw)*math.cos(pitch))
    horizontal = -512 if reflect else 512
    return column_matrix(tuple(320*depth[a] + horizontal*right[a] + skew*512*up[a] for a in range(3)) + (320*distance,),
                         tuple(240*depth[a] - 384*up[a] for a in range(3)) + (240*distance,),
                         depth + (distance,))


def shifted_matrix(matrix, shift):
    """Keep geometry in view after translating its raw integer coordinate space."""
    result = list(matrix)
    for row in range(4):
        result[12+row] = f32(matrix[12+row] - math.fsum(matrix[4*a+row]*shift[a] for a in range(3)))
    return result


def curved_grid():
    points = [((2*x-7)*32, (2*y-7)*32, 2*(x-3)*(y-3)+6*x-4*y)
              for y in range(8) for x in range(8)]
    indices = []
    for y in range(7):
        for x in range(7):
            a = 8*y+x
            indices.extend((a, a+1, (a+8)|128, a+1, a+9, (a+8)|128))
    return points, bytes(indices)


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
    for point, h in zip(points, homogeneous):
        products = [Fraction(matrix[4*c+3]) * Fraction((*point, 1)[c]) for c in range(4)]
        ftrv_error = max(map(abs, products)) / 2**23 + max(abs(h[2]) / 2**23, Fraction(1, 2**149))
        assert Fraction(proof.w_error) >= ftrv_error, (name, "homogeneous W error bound")
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
                              ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint,
                              ctypes.POINTER(RawPositions), ctypes.POINTER(Proof)]
    lib.cone_probe.restype = ctypes.c_uint
    lib.cone_strict.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]
    lib.cone_strict.restype = ctypes.c_uint
    lib.cone_normal.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.c_float, ctypes.POINTER(ctypes.c_int64)]
    lib.cone_normal.restype = ctypes.c_float
    lib.cone_projected.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.c_float,
                                  ctypes.POINTER(Proof), ctypes.c_void_p, ctypes.c_uint,
                                  ctypes.POINTER(RawPositions), ctypes.c_uint]
    lib.cone_projected.restype = ctypes.c_uint
    lib.cone_strict_layout.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
    lib.cone_strict_layout.restype = ctypes.c_uint
    lib.cone_worth.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]
    lib.cone_worth.restype = ctypes.c_uint
    lib.cone_worth_world.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]
    lib.cone_worth_world.restype = ctypes.c_uint
    return lib


def probe(lib, matrix, cone, cache, cull=1, near=1, points=None, raw=None):
    proof = Proof()
    assert points is not None or raw is not None, "Correlated projection requires matching raw positions"
    storage = RawBuffer(points) if raw is None else None
    raw = storage.layout if storage is not None else raw
    result = lib.cone_probe((ctypes.c_float * 16)(*matrix), near, ctypes.byref(cone),
                           cull, cache, len(cache) // 32, ctypes.byref(raw), ctypes.byref(proof))
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
    assert lib.cone_sizes(2) == ctypes.sizeof(Proof) == 44
    assert lib.cone_sizes(3) == ctypes.sizeof(RawPositions)
    admission_controls = []
    # Independent count contracts and measured crossover fixtures. Equality
    # declines; actor and world deliberately have different cost boundaries.
    # Explicit upper-range controls ensure bad counts cannot wrap either score.
    for vertices, indices, strips, actor_expected, world_expected in (
            (0, 65535, 21845, 0, 0), (2, 65535, 21845, 0, 0),
            (3, 0, 1, 0, 0), (3, 1, 1, 0, 0), (3, 2, 1, 0, 0), (3, 3, 1, 0, 0),
            (25, 96, 32, 0, 0), (36, 150, 50, 1, 1),
            (64, 294, 98, 1, 1), (64, 196, 49, 0, 1),
            (64, 112, 7, 0, 0), (128, 128, 1, 0, 0), (128, 294, 98, 1, 1),
            (125, 276, 59, 0, 0), (89, 159, 38, 0, 0),
            (33, 68, 14, 0, 0), (41, 60, 14, 0, 0),
            (64, 287, 40, 0, 1), (64, 288, 40, 0, 1), (64, 289, 40, 1, 1),
            (64, 296, 38, 0, 1), (64, 296, 39, 0, 1), (64, 296, 40, 1, 1),
            (64, 223, 40, 0, 0), (64, 224, 40, 0, 0), (64, 225, 40, 0, 1),
            (3, 300, 5, 1, 0),
            (3, 303, 101, 1, 1), (3, 303, 102, 0, 0), (3, 302, 101, 0, 0),
            (3, 65535, 1, 1, 1), (3, 65535, 0, 0, 0),
            (256, 65535, 21845, 1, 1), (257, 65535, 21845, 0, 0),
            (256, 65536, 21845, 0, 0), (256, 65535, 21846, 0, 0),
            (256, 65535, 0xFFFFFFFF, 0, 0), (3, 0xFFFFFFFF, 1, 0, 0),
            (0x3FFFFFFF, 0xFFFFFFFF, 64, 0, 0), (0x40000000, 0xFFFFFFFF, 64, 0, 0),
            (0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0, 0)):
        assert lib.cone_worth(vertices, indices, strips) == actor_expected, (vertices, indices, strips, "actor")
        assert lib.cone_worth_world(vertices, indices, strips) == world_expected, (vertices, indices, strips, "world")
        admission_controls.append(dict(vertices=vertices, indices=indices, strips=strips,
                                       admitted=bool(actor_expected), world_admitted=bool(world_expected)))
    rng = random.Random(0xC023F012)
    counts = dict(cases=0, prepared=0, front_candidate=0, front_accepted=0,
                  back_suggestion=0, complete_packet_comparisons=0, ideal_bound_checks=0)
    fixtures = []

    def check(name, points, indices, matrix, cone=None, cache=None, cull=1, near=1,
              require=None, record=False, raw=None):
        cone = cone or cone_for(points, indices)
        cache = cache if cache is not None else projected_cache(matrix, points)
        flags, proof = probe(lib, matrix, cone, cache, cull, near, points=points, raw=raw)
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
    ordinary_raw = RawBuffer(points)
    ordinary_matrix = (ctypes.c_float * 16)(*matrix)

    def projected(proof, cache, vertices, stride=32, raw=ordinary_raw.layout, transform=ordinary_matrix):
        return lib.cone_projected(transform, 1, ctypes.byref(proof), cache, vertices, ctypes.byref(raw), stride)

    for stride in (12, 16, 17, 20, 32, 33, 36):
        for misalignment in range(4):
            backing = ctypes.create_string_buffer(stride*3 + 16)
            pointer = ctypes.addressof(backing) + misalignment
            assert ctypes.addressof(backing) % 4 == 0
            for i in range(3):
                ctypes.memmove(pointer+i*stride, ordinary_cache[i*32:i*32+16], 16)
            expected = int(stride >= 16 and stride % 4 == 0 and misalignment == 0)
            projected_result = projected(ordinary_proof, pointer, 3, stride)
            strict = lib.cone_strict_layout(pointer, indices, 3, stride)
            assert projected_result == strict == expected, (stride, misalignment, projected_result, strict)
            alignment_controls.append(dict(stride=stride, misalignment=misalignment, accepted=bool(expected)))
    for vertices in (0, 1, 2):
        assert not projected(ordinary_proof, ordinary_cache, vertices)
    assert not projected(ordinary_proof, None, 3)
    null_raw = RawPositions(None, 8, None, 2, False)
    assert not projected(ordinary_proof, ordinary_cache, 3, raw=null_raw)
    raw_layout_controls = []
    for unsigned, indexed in itertools.product((False, True), repeat=2):
        raw_points = [tuple(v+256 for v in point) for point in points] if unsigned else points
        raw_matrix = shifted_matrix(matrix, (256, 256, 256)) if unsigned else matrix
        for raw_stride, data_offset, index_stride, index_offset in (
                (4, 0, 2, 0), (5, 0, 2, 0), (6, 0, 2, 0),
                (7, 0, 2, 0), (8, 0, 2, 0), (12, 0, 4, 0),
                (14, 0, 6, 0), (8, 1, 2, 0), (8, 2, 2, 0),
                (8, 0, 1, 0), (8, 0, 3, 0), (8, 0, 2, 1),
                (8, 0, 4, 2)):
            raw = RawBuffer(raw_points, unsigned, indexed, raw_stride, index_stride,
                            data_offset, index_offset)
            expected = raw_stride >= 6 and raw_stride % 2 == 0 and data_offset % 2 == 0
            expected &= not indexed or (index_stride >= 2 and index_stride % 2 == 0 and index_offset % 2 == 0)
            flags, _ = check("raw-layout", raw_points, indices, raw_matrix,
                             raw=raw.layout, require="front" if expected else "uncertain")
            raw_layout_controls.append(dict(unsigned=unsigned, indexed=indexed, raw_stride=raw_stride,
                                            data_offset=data_offset, index_stride=index_stride,
                                            index_offset=index_offset, accepted=bool(flags & 16)))
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
        invalids = (math.nan, math.inf, 2**-149) + ((0.0, -1.0, 2**-126, f32(0xFFFFFF*2**104)) if offset == 12 else ())
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

    # Actual three-dimensional raw bounds, not an axis-aligned zero-thickness
    # wall. Camera rotation and shear vary W across a dense, reused curved grid.
    # Every accepted arm is checked against the complete original packet stream.
    grid, grid_indices = curved_grid()
    assert all(x > 0 for x in cone_for(grid, grid_indices).extent)
    perspective_controls = []
    for yaw, pitch, skew, reflect in ((0, 0, 0, False), (10, 5, 0, False),
                                      (25, 10, 0, False), (-20, 12, .2, False),
                                      (10, 5, -.15, True), (-15, -8, .1, True)):
        transform = camera_matrix(yaw, pitch, skew, reflect=reflect)
        flags, proof = check("curved-grid-camera", grid, grid_indices, transform,
                             cull=1 if reflect else 2, require="front", record=True)
        perspective_controls.append(dict(yaw=yaw, pitch=pitch, skew=skew, reflect=reflect,
                                         vertices=len(grid), indices=len(grid_indices), strips=98,
                                         extent=list(cone_for(grid, grid_indices).extent),
                                         wlo=proof.wlo, whi=proof.whi, accepted=bool(flags & 16)))
    for animation in range(3):
        source = camera_matrix(8+animation*5, 4-animation*3, .05)
        model = ((1+.04*animation, .025*animation, .01),
                 (-.02, .95+.02*animation, .015*animation),
                 (.01*animation, -.01, 1.0))
        translation = (5*animation, -3*animation, 10+animation*2)
        transform = [f32(math.fsum(source[4*k+r]*model[k][c] for k in range(3)))
                     for c in range(3) for r in range(4)]
        transform += [f32(source[12+r]+math.fsum(source[4*k+r]*translation[k] for k in range(3)))
                      for r in range(4)]
        flags, proof = check("curved-grid-current-affine-animation", grid, grid_indices, transform,
                             cull=2, require="front", record=True)
        perspective_controls.append(dict(animation=animation, vertices=len(grid), indices=len(grid_indices),
                                         strips=98, wlo=proof.wlo, whi=proof.whi, accepted=bool(flags & 16)))

    # All four template arms must accept real perspective, including gathered
    # indices with padded records. Unsigned coordinates above 32767 are separately
    # tested so an accidental signed load cannot be hidden by small fixtures.
    for unsigned, indexed in itertools.product((False, True), repeat=2):
        offset = (256, 256, 256) if unsigned else (0, 0, 0)
        raw_points = [tuple(point[a]+offset[a] for a in range(3)) for point in grid]
        transform = shifted_matrix(camera_matrix(10, 5), offset)
        raw = RawBuffer(raw_points, unsigned, indexed, stride=12, index_stride=6)
        check("curved-grid-raw-format", raw_points, grid_indices, transform, cull=2,
              raw=raw.layout, require="front", record=True)
    high_points = [tuple(point[a]+(40000, 42000, 36000)[a] for a in range(3)) for point in grid]
    high_matrix = shifted_matrix(camera_matrix(10, 5), (40000, 42000, 36000))
    for indexed in (False, True):
        raw = RawBuffer(high_points, unsigned=True, indexed=indexed, stride=12, index_stride=4)
        check("unsigned-coordinates-above-signed-range", high_points, grid_indices, high_matrix,
              cull=2, raw=raw.layout, record=True)

    transform = camera_matrix(25, 10)
    correct = projected_cache(transform, grid)
    reciprocal = [struct.unpack_from("<f", correct, i*32+12)[0] for i in range(len(grid))]
    wrong = projected_cache(transform, grid, inverse_values=list(reversed(reciprocal)))
    check("reciprocals-paired-to-wrong-vertices", grid, grid_indices, transform,
          cache=wrong, cull=2, require="uncertain", record=True)
    for bias in (.001, .01, .1):
        observed = projected_cache(transform, grid, inverse_bias=bias, rng=rng)
        check("depth-varying-reciprocal-perturbations", grid, grid_indices, transform,
              cache=observed, cull=2, require="uncertain", record=True)
    cancellation_points = [(30000, 30000, 0), (30200, 30000, 16), (30000, 30200, -16)]
    cancellation_matrix = column_matrix((832, -320, -320, -15040000),
                                        (240, -624, -240, 11760000),
                                        (1, -1, -1, 1000))
    for signs in itertools.product((-1, 1), repeat=3):
        check("cancellation-heavy-homogeneous-depth", cancellation_points, indices, cancellation_matrix,
              cache=projected_cache(cancellation_matrix, cancellation_points, ftrv_signs=signs), cull=2)

    # A pyramid fan supplies four different actual triangle-normal directions
    # at the stated half-angle. A nearly unit axis matches the production
    # quantized axes. These wide cones require the perpendicular-eye bound;
    # subtracting sin(theta)*|q| would categorically miss their along-axis views.
    wide_cone_controls = []
    fan_indices = bytes((0, 1, 132, 1, 2, 132, 2, 3, 132, 3, 0, 132))
    for height in (64, 96, 128, 192, 320, 363):
        fan = [(-64, -64, 0), (64, -64, 0), (64, 64, 0), (-64, 64, 0), (0, 0, height)]
        half_angle = math.degrees(math.atan(height/64))
        fan_cone = cone_for(fan, fan_indices, axis_length=32767/32768)
        tilted = (10, 5) if height <= 128 else (5, 3) if height <= 192 else (2, 1)
        for yaw, pitch in ((0, 0), tilted):
            transform = camera_matrix(yaw, pitch)
            flags, proof = check("wide-cone-axis-and-tilted-view", fan, fan_indices, transform,
                                 cone=fan_cone, cull=2, require="front", record=True)
            wide_cone_controls.append(dict(half_angle_degrees=half_angle, yaw=yaw, pitch=pitch,
                                           accepted=bool(flags & 16), area_lower=proof.area_lower))
        yaw = math.ceil(95-half_angle)
        flags, _ = check("wide-cone-crosses-facing-boundary", fan, fan_indices, camera_matrix(yaw),
                         cone=fan_cone, cull=2, require="uncertain", record=True)
        wide_cone_controls.append(dict(half_angle_degrees=half_angle, yaw=yaw, pitch=0,
                                       accepted=bool(flags & 16), boundary_decline=True))
    for invalid_kind in ("zero-cosine", "unit-cosine", "insufficient-sine", "oversized-axis"):
        invalid = Cone.from_buffer_copy(bytes(fan_cone))
        if invalid_kind == "zero-cosine":
            invalid.cos_lower = 0
        elif invalid_kind == "unit-cosine":
            invalid.cos_lower = 1
        elif invalid_kind == "insufficient-sine":
            invalid.sin_upper = .5
        else:
            invalid.axis[2] = 1.01
        check("wide-cone-invalid-bound-"+invalid_kind, fan, fan_indices, camera_matrix(),
              cone=invalid, cull=2, require="uncertain")

    # Same real geometry, changing animation/model matrices, reflections,
    # shears, perspective slopes and deliberately nonuniform reciprocal error.
    for case in range(800):
        size = rng.choice((16, 64, 128, 256, 512))
        pts = [(-size, -size, rng.randrange(-size//8, size//8+1)),
               (size, -size, rng.randrange(-size//8, size//8+1)),
               (-size, size, rng.randrange(-size//8, size//8+1))]
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
                  raw_layout_controls=raw_layout_controls,
                  perspective_controls=perspective_controls,
                  wide_cone_controls=wide_cone_controls,
                  admission_controls=admission_controls,
                  source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in (SOURCE, HEADER, HERE / "helper_fixture.cpp", Path(__file__))},
                  limitations="Synthetic bounded-transform caches and host execution; no exact FTRV/FSRRA emulation, scene, or hardware claim. Back is a geometric suggestion only.")
    (output / "helper-controls.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print("PASS production helper:", json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    main()
