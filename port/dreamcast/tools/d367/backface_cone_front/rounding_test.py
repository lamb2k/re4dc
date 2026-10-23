#!/usr/bin/env python3
"""Exact-rational RN/RZ+DN checks for the certificate's scalar envelopes.

This is an arithmetic-bound experiment, not a hardware or whole-renderer test.
The production C++ tests separately check actual compiled code and packets.
"""
import argparse
import functools
import json
import random
from fractions import Fraction as Q
from pathlib import Path


@functools.lru_cache(maxsize=200000)
def value(bits):
    sign = -1 if bits >> 31 else 1
    exponent = (bits >> 23) & 255
    mantissa = bits & 0x7fffff
    if exponent == 255:
        raise OverflowError("nonfinite single")
    if not exponent:
        return sign * Q(mantissa, 1 << 149)
    return sign * Q((1 << 23) + mantissa) * power(exponent - 150)


def power(exponent):
    return Q(1 << exponent) if exponent >= 0 else Q(1, 1 << -exponent)


def rounded(q, mode):
    if not q:
        return 0
    sign = 0x80000000 if q < 0 else 0
    q = abs(q)
    n, d = q.numerator, q.denominator
    exponent = n.bit_length() - d.bit_length()
    if q < power(exponent):
        exponent -= 1
    scale = 23 - max(exponent, -126)
    n, d = (n << scale, d) if scale >= 0 else (n, d << -scale)
    mantissa, remainder = divmod(n, d)
    if mode == "RN" and (2 * remainder > d or (2 * remainder == d and mantissa & 1)):
        mantissa += 1
    if exponent < -126:
        # DN=1 flushes the rounded subnormal result. Rounding up to the
        # minimum normal is retained, which is the more demanding enclosure.
        return sign | (0x00800000 if mantissa >= 1 << 23 else 0)
    if mantissa >= 1 << 24:
        mantissa >>= 1
        exponent += 1
    if exponent > 127:
        return sign | (0x7f800000 if mode == "RN" else 0x7f7fffff)
    return sign | ((exponent + 127) << 23) | (mantissa - (1 << 23))


def upward(bits):
    magnitude = bits & 0x7fffffff
    if magnitude >= 0x7f800000:
        return bits
    if magnitude < 0x00800000:
        return 0x00800000
    if bits == 0x80800000:
        return 0
    return bits - 1 if bits >> 31 else bits + 1


def downward(bits):
    return upward(bits ^ 0x80000000) ^ 0x80000000


class Single:
    def __init__(self, mode):
        self.mode = mode

    def number(self, q):
        return rounded(Q(q), self.mode)

    def add(self, a, b):
        return rounded(value(a) + value(b), self.mode)

    def sub(self, a, b):
        return rounded(value(a) - value(b), self.mode)

    def mul(self, a, b):
        return rounded(value(a) * value(b), self.mode)

    def add_up(self, a, b):
        return upward(self.add(a, b))

    def mul_up(self, a, b):
        return upward(self.mul(a, b))


def prepare_bounds(fp, a):
    def cross(p, q, r, s):
        left, right = fp.mul(a[p], a[q]), fp.mul(a[r], a[s])
        return fp.sub(left, right), fp.add(left & 0x7fffffff, right & 0x7fffffff)
    terms = ((5, 10, 6, 9), (2, 9, 1, 10), (1, 6, 2, 5),
             (6, 8, 4, 10), (0, 10, 2, 8), (2, 4, 0, 6),
             (4, 9, 5, 8), (1, 8, 0, 9), (0, 5, 1, 4))
    cofactor = [cross(*indices) for indices in terms]
    exact = [value(a[p]) * value(a[q]) - value(a[r]) * value(a[s]) for p, q, r, s in terms]
    def enclosure(indices, coefficients):
        products = [fp.mul(cofactor[i][0], a[j]) for i, j in zip(indices, coefficients)]
        estimate = fp.add(fp.add(products[0], products[1]), products[2])
        absolute = [fp.mul(cofactor[i][1], a[j] & 0x7fffffff) for i, j in zip(indices, coefficients)]
        magnitude = fp.add(fp.add(absolute[0], absolute[1]), absolute[2])
        error = fp.add(fp.mul(fp.number(power(-17)), magnitude), fp.number(power(-120)))
        lower = downward(fp.sub(estimate, error))
        upper = upward(fp.add(estimate, error))
        truth = sum((exact[i] * value(a[j]) for i, j in zip(indices, coefficients)), Q())
        assert value(lower) <= truth <= value(upper), (fp.mode, "prepare", a, indices, lower, truth, upper)
    enclosure((0, 3, 6), (0, 1, 2))
    for row in range(3):
        enclosure(tuple(range(3 * row, 3 * row + 3)), (3, 7, 11))


def residual_bound(fp, w, point, inverse):
    xyz = [fp.number(p) for p in point]
    products = [fp.mul(w[i], xyz[i]) for i in range(3)]
    depth = fp.add(fp.add(fp.add(products[0], products[1]), products[2]), w[3])
    exact = sum((value(w[i]) * point[i] for i in range(3)), value(w[3]))
    total = w[3] & 0x7fffffff
    for i in range(3):
        total = fp.add(total, fp.mul(w[i] & 0x7fffffff, xyz[i] & 0x7fffffff))
    total = upward(fp.add(fp.mul(total, fp.number(1 + power(-16))), fp.number(power(-120))))
    error = fp.add_up(fp.mul_up(fp.number(power(-20)), total), fp.number(power(-120)))
    assert abs(exact - value(depth)) <= value(error), (fp.mode, "W dot", w, point)
    observed = fp.sub(fp.mul(depth, inverse), fp.number(1))
    residual = observed & 0x7fffffff
    relative = fp.add_up(fp.add_up(fp.add_up(
        fp.mul_up(residual, fp.number(1 + power(-21))), fp.mul_up(error, inverse)),
        fp.number(power(-21))), fp.number(power(-120)))
    assert abs(exact * value(inverse) - 1) <= value(relative), (fp.mode, "residual", w, point, inverse)


def dot_bounds(fp, intervals, axis):
    lo = hi = norm = fp.number(0)
    exact_lo = exact_hi = Q()
    for (ql, qh), direction in zip(intervals, axis):
        left, right = (qh, ql) if value(direction) < 0 else (ql, qh)
        lo = fp.add(lo, fp.mul(left, direction))
        hi = fp.add(hi, fp.mul(right, direction))
        norm = fp.add_up(norm, max((ql & 0x7fffffff), (qh & 0x7fffffff)))
        exact_lo += value(left) * value(direction)
        exact_hi += value(right) * value(direction)
    error = fp.add(fp.mul(fp.number(power(-20)), norm), fp.number(power(-120)))
    lower, upper = downward(fp.sub(lo, error)), upward(fp.add(hi, error))
    assert value(lower) <= exact_lo <= exact_hi <= value(upper), (fp.mode, "cone dot", intervals, axis)
    axis2 = sum((value(a) ** 2 for a in axis), Q())
    d = lower if value(lower) > 0 else upper ^ 0x80000000
    if not 0 < axis2 <= 1 or value(d) <= 0:
        return False
    norm2 = fp.number(0)
    for ql, qh in intervals:
        component = max((ql & 0x7fffffff), (qh & 0x7fffffff))
        norm2 = fp.add_up(norm2, fp.mul_up(component, component))
    perpendicular2 = upward(fp.sub(norm2, downward(fp.mul(d, d))))
    point = [(value(ql) + value(qh)) / 2 for ql, qh in intervals]
    projection = sum((p * value(a) for p, a in zip(point, axis)), Q())
    exact_perpendicular2 = sum((p * p for p in point), Q()) - projection * projection / axis2
    assert 0 <= exact_perpendicular2 <= value(perpendicular2), (fp.mode, "perpendicular square", intervals, axis)
    return True


def coefficient(rng):
    if rng.randrange(8) == 0:
        return 0
    exponent = rng.randint(-40, 39)
    return (rng.randrange(2) << 31) | ((exponent + 127) << 23) | rng.randrange(1 << 23)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rng = random.Random(0x7091C0DE)
    matrices = [[coefficient(rng) for _ in range(12)] for _ in range(1200)]
    # Singular/cancellation cases, exact coefficient guard extremes, and
    # outer products that reach the DN-flush range after a tiny cofactor.
    for exponent in (-40, -30, -10, 0, 10, 30, 39):
        one = rounded(power(exponent), "RN")
        for offset in (-1, 0, 1):
            near = max(rounded(power(-40), "RN"), one + offset)
            matrices.append([one, near, one, one, one, one, near, one, near, one, one, one])
    points = []
    for _ in range(1600):
        unsigned = bool(rng.randrange(2))
        point = [rng.randint(0, 65535) if unsigned else rng.randint(-32768, 32767) for _ in range(3)]
        w = [coefficient(rng) for _ in range(4)]
        exact = sum((value(w[i]) * point[i] for i in range(3)), value(w[3]))
        inverse = rounded(1 / abs(exact), "RN") if exact else 0x3f800000
        inverse = max(0x00800000, min(0x7f7fffff, inverse + rng.randint(-32, 32)))
        points.append((w, point, inverse))
    for _ in range(300):
        point = [rng.randint(-32768, 32767) for _ in range(3)]
        w = [rounded(Q(rng.randint(-8192, 8192), 1024), "RN") for _ in range(3)]
        exact = sum((value(w[i]) * point[i] for i in range(3)), Q())
        w.append(rounded(-exact, "RN") + rng.randint(-2, 2))
        remainder = sum((value(w[i]) * point[i] for i in range(3)), value(w[3]))
        inverse = rounded(1 / abs(remainder), "RN") if remainder else 0x4a800000
        points.append((w, point, inverse))
    for exponent in (-126, -100, -40, 0, 40, 100, 127):
        points.append(([0x3f800000, 0xbf800000, 0x3f800000, 0x3f800001], [65535, 65535, 0],
                       rounded(power(exponent), "RN")))
    dots = []
    for _ in range(2000):
        interval, axis = [], []
        for _ in range(3):
            ends = [(rng.randrange(2) << 31) | ((rng.randint(-126, 57) + 127) << 23) |
                    rng.randrange(1 << 23) for _ in range(2)]
            interval.append(tuple(sorted(ends, key=value)))
            direction = ((rng.randrange(2) << 31) | ((rng.randint(-126, -1) + 127) << 23) |
                         rng.randrange(1 << 23))
            axis.append(direction if rng.randrange(4) else 0)
        dots.append((interval, axis))
    for exponent in (-126, -125, -120, -40, 0, 57):
        q = rounded(power(exponent), "RN")
        for axis in ((0, 0, 0), (0x3f800000, 0xbf800000, 0), (0x00800000,) * 3):
            dots.append(([(q ^ 0x80000000, q)] * 3, axis))
    for _ in range(600):
        interval, axis = [], []
        for _ in range(3):
            q = ((rng.randrange(2) << 31) | ((rng.randint(-126, 57) + 127) << 23) |
                 rng.randrange(1 << 23))
            interval.append((downward(q), upward(q)))
            axis.append(rounded(Q(rng.randint(-32767, 32767), 65536), "RN"))
        dots.append((interval, axis))
    counts = {}
    for mode in ("RN", "RZ"):
        fp = Single(mode)
        for matrix in matrices:
            prepare_bounds(fp, matrix)
        checked, declined = 0, 0
        for w, point, inverse in points:
            try:
                residual_bound(fp, w, point, inverse)
                checked += 1
            except OverflowError:
                declined += 1
        perpendicular = sum(dot_bounds(fp, interval, axis) for interval, axis in dots)
        counts[mode] = dict(prepare_matrices=len(matrices), prepare_intervals=4 * len(matrices),
                            scalar_residual_bounds=checked, nonfinite_declines=declined,
                            cone_dot_enclosures=len(dots), perpendicular_square_enclosures=perpendicular)
    report = dict(scope=__doc__, counts=counts, result="PASS", seed="0x7091C0DE",
                  limitations="Exact rational simulation of arithmetic envelopes; not target hardware, compiled instruction execution, or a proof over every input.")
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
