#include "../../room/backface_certificate.hpp"

#include <cmath>
#include <cstring>

#ifdef __FAST_MATH__
#error "backface_certificate.cpp requires -fno-fast-math"
#endif

namespace re4dc { namespace bf { namespace certificate {
namespace {
constexpr float kEpsilon = 0x1p-23f;   // covers both SH4 rounding modes
constexpr float kFloor = 0x1p-120f;    // covers flushed single-precision results
constexpr float kLimit = 0x1p60f;

bool arithmetic_supported() {
#if defined(__sh__)
    std::uint32_t fpscr;
    asm volatile("sts fpscr,%0" : "=r"(fpscr));
    // KOS starts with DN=1. DN=0 can trap on intermediate denormal operands,
    // even when the mathematical error enclosure includes their magnitude.
    // Do not change the caller's mode; retain the existing facing path.
    constexpr std::uint32_t mask = (1U << 18) | (1U << 19) | (1U << 20) | (31U << 7) | 2U;
    return (fpscr & mask) == (1U << 18);
#else
    return true;  // host fixtures use ordinary IEEE arithmetic, not SH4 modes
#endif
}

std::uint32_t bits(float x) { std::uint32_t v; std::memcpy(&v, &x, 4); return v; }
float from_bits(std::uint32_t v) { float x; std::memcpy(&x, &v, 4); return x; }
float absolute(float x) { return from_bits(bits(x) & 0x7fffffffU); }
bool finite(float x) { return (bits(x) & 0x7f800000U) != 0x7f800000U; }
bool ordinary(float x) {
    const std::uint32_t v = bits(x) & 0x7fffffffU;
    return !v || (v >= 0x00800000U && v < 0x7f800000U);
}
float minimum(float a, float b) { return a < b ? a : b; }
float maximum(float a, float b) { return a > b ? a : b; }

// One adjacent NORMAL float outwards is sufficient for RN or RZ. At zero and
// subnormal results use the minimum normal instead: DN may have flushed the
// mathematical result, and denormal operands may trap when DN is clear.
float up(float x) {
    const std::uint32_t v = bits(x), a = v & 0x7fffffffU;
    if (a >= 0x7f800000U) return x;
    if (a < 0x00800000U) return from_bits(0x00800000U);
    if (v == 0x80800000U) return 0.0f; // do not manufacture a denormal operand
    return from_bits(v + ((v >> 31) ? std::uint32_t(-1) : 1U));
}
float down(float x) { return -up(-x); }
float add_up(float a, float b) { return up(a + b); }
float mul_up(float a, float b) { return up(a * b); }
float div_up(float a, float b) { return up(a / b); }
Interval point(float x) { return {x, x}; }
Interval add(Interval a, Interval b) { return {down(a.lo + b.lo), up(a.hi + b.hi)}; }
Interval sub(Interval a, Interval b) { return {down(a.lo - b.hi), up(a.hi - b.lo)}; }
Interval mul(Interval a, Interval b) {
    const float p0 = a.lo * b.lo, p1 = a.lo * b.hi, p2 = a.hi * b.lo, p3 = a.hi * b.hi;
    return {down(minimum(minimum(p0, p1), minimum(p2, p3))),
            up(maximum(maximum(p0, p1), maximum(p2, p3)))};
}
// Exact scalar operands need no four-corner interval product. These helpers
// retain the same outward endpoints while avoiding generic aggregate calls.
inline Interval product(float a, float b) {
    const float p = a * b;
    return {down(p), up(p)};
}
inline Interval scale(Interval a, float b) {
    if (b >= 0.0f) return {down(a.lo * b), up(a.hi * b)};
    return {down(a.hi * b), up(a.lo * b)};
}
float magnitude(Interval a) { return maximum(absolute(a.lo), absolute(a.hi)); }
bool bounded(Interval a) { return ordinary(a.lo) && ordinary(a.hi) && a.lo <= a.hi; }
bool bounded(float x) { return finite(x) && x >= 0.0f && x < kLimit; }
Interval square(float x) { return product(x, x); }
float sqrt_up(float x) { return up(std::sqrt(x)); }

bool sphere_ok(const Cone& c) {
    if (!ordinary(c.radius) || c.radius < 0.0f || c.radius > 0x1p23f) return false;
    for (unsigned i = 0; i < 3; ++i)
        if (!ordinary(c.center[i]) || absolute(c.center[i]) > 0x1p23f ||
            !ordinary(c.extent[i]) || c.extent[i] < 0.0f || c.extent[i] > c.radius) return false;
    return true;
}
bool axis_ok(const float axis[3], Interval* norm2 = nullptr) {
    Interval s = point(0.0f);
    for (unsigned i = 0; i < 3; ++i) {
        if (!ordinary(axis[i]) || absolute(axis[i]) > 1.0f) return false;
        s = add(s, square(axis[i]));
    }
    if (!bounded(s) || !(s.lo > 0.0f) || !(s.hi <= 1.0f)) return false;
    if (norm2) *norm2 = s;
    return true;
}
bool axis_within_unit(const float axis[3]) {
    for (unsigned i = 0; i < 3; ++i)
        if (!ordinary(axis[i]) || absolute(axis[i]) > 1.0f) return false;
    const float sum = (axis[0] * axis[0] + axis[1] * axis[1]) + axis[2] * axis[2];
    // Five separate operations, with a generous RN/RZ/flush envelope.
    const float upper = up(sum * (1.0f + 16.0f * kEpsilon) + kFloor);
    return sum > kFloor && upper <= 1.0f;
}

// SH4 Software Manual 6.6.1: maximum product*2^-23 plus maximum
// (result*2^-23,2^-149). Eight epsilons times the absolute sum comfortably
// covers that contract, including evaluation of the bound and DN's flush.
float transform_error(float sum) { return add_up(mul_up(8.0f * kEpsilon, sum), kFloor); }
float row_sum(const Context& x, const Cone& c, unsigned r) {
    const float* m = x.matrix + 4U * r;
    float s = absolute(m[3]);
    for (unsigned i = 0; i < 3; ++i)
        s += absolute(m[i]) * (absolute(c.center[i]) + c.extent[i]);
    // Every nonnegative contribution traverses at most five roundings. With
    // eps covering RN and RZ, H <= (s+3*FLT_MIN)/(1-eps)^5. The two roundings
    // below retain ample slack in 128 eps and kFloor=64*FLT_MIN, also with DN.
    return up(s * (1.0f + 128.0f * kEpsilon) + kFloor);
}
float row_spread(const Context& x, const Cone& c, unsigned r) {
    const float* m = x.matrix + 4U * r;
    const float s = (absolute(m[0]) * c.extent[0] + absolute(m[1]) * c.extent[1]) +
                    absolute(m[2]) * c.extent[2];
    return up(s * (1.0f + 16.0f * kEpsilon) + kFloor);
}
float read_float(const void* p, unsigned offset) {
    // Both public cache entry points reject non-word-aligned inputs. Retain
    // alias-safe loads while giving SH4 GCC the alignment needed for FMOV
    // instead of a libc memcpy for every four-byte field.
    const void* source = __builtin_assume_aligned(static_cast<const std::uint8_t*>(p) + offset, 4);
    float f; std::memcpy(&f, source, 4); return f;
}
inline std::uint32_t read_word(const void* p, unsigned offset) {
    const void* source = __builtin_assume_aligned(static_cast<const std::uint8_t*>(p) + offset, 4);
    std::uint32_t word; std::memcpy(&word, source, 4); return word;
}

float target_area(float ax, float ay, float bx, float by, float cx, float cy) {
#if defined(__sh__)
    float result;
    asm volatile(
        "fmov %[by],fr2\n\t"
        "fmov %[cx],fr3\n\t"
        "fmov %[bx],fr0\n\t"
        "fmov %[cy],fr1\n\t"
        "fsub %[ay],fr2\n\t"
        "fsub %[ax],fr3\n\t"
        "fsub %[ax],fr0\n\t"
        "fsub %[ay],fr1\n\t"
        "fmul fr3,fr2\n\t"
        "fneg fr2\n\t"
        "fmac fr0,fr1,fr2\n\t"
        "fmov fr2,%[out]"
        : [out] "=f"(result)
        : [ax] "f"(ax), [ay] "f"(ay), [bx] "f"(bx), [by] "f"(by), [cx] "f"(cx), [cy] "f"(cy)
        : "fr0", "fr1", "fr2", "fr3");
    return result;
#else
    const float dx1 = bx - ax, dy1 = by - ay, dx2 = cx - ax, dy2 = cy - ay;
    const float second = dy1 * dx2;
    return std::fma(dx1, dy2, -second);
#endif
}
} // namespace

bool prepare(Context& out, const float matrix[16], float near_distance) {
    out.valid = false;
    if (!arithmetic_supported() || !matrix || !ordinary(near_distance) || !(near_distance > 0.0f)) return false;
    out.near_distance = near_distance;
    for (unsigned r = 0; r < 3; ++r) for (unsigned c = 0; c < 4; ++c) {
        const float a = matrix[4U * c + (r == 2 ? 3U : r)];
        if (!ordinary(a) || absolute(a) > 0x1p40f || (a != 0.0f && absolute(a) < 0x1p-40f)) return false;
        out.matrix[4U * r + c] = a;
    }
    const float* a = out.matrix;
    const auto cross = [&](unsigned p, unsigned q, unsigned r, unsigned s) {
        return sub(product(a[p], a[q]), product(a[r], a[s]));
    };
    Interval c[9];
    c[0] = cross(5,10,6,9); c[1] = cross(2,9,1,10); c[2] = cross(1,6,2,5);
    c[3] = cross(6,8,4,10); c[4] = cross(0,10,2,8); c[5] = cross(2,4,0,6);
    c[6] = cross(4,9,5,8); c[7] = cross(1,8,0,9); c[8] = cross(0,5,1,4);
    out.determinant = add(add(scale(c[0], a[0]), scale(c[3], a[1])), scale(c[6], a[2]));
    for (unsigned i = 0; i < 9; ++i) if (!bounded(c[i])) return false;
    if (!bounded(out.determinant) || (out.determinant.lo <= 0.0f && out.determinant.hi >= 0.0f)) return false;
    for (unsigned r = 0; r < 3; ++r) {
        out.translation[r] = add(add(scale(c[3U*r], a[3]), scale(c[3U*r+1U], a[7])), scale(c[3U*r+2U], a[11]));
        if (!bounded(out.translation[r])) return false;
    }
    out.valid = true;
    return true;
}

namespace {
bool depth_bounds(const Context& x, const Cone& c, DepthBounds* out) {
    const float* w = x.matrix + 8;
    const float center = ((w[0] * c.center[0] + w[1] * c.center[1]) + w[2] * c.center[2]) + w[3];
    const float extent = (absolute(w[0]) * c.extent[0] + absolute(w[1]) * c.extent[1]) +
                         absolute(w[2]) * c.extent[2];
    const float sum = row_sum(x, c, 2);
    if (!finite(center) || !bounded(sum) || !bounded(extent)) return false;
    // Signed center, nonnegative spread and their final sum/difference use
    // fewer than ten eps*H + fourteen flushed minimum-normal units of error.
    // Inflate once with 32 eps*H + 64 minimum-normal units instead of paying
    // for an interval adjustment after every scalar operation.
    const float enclosure = 32.0f * kEpsilon * sum + kFloor;
    const float lo = down((center - extent) - enclosure), hi = up((center + extent) + enclosure);
    const float error = transform_error(sum);
    if (!(down(lo - error) > x.near_distance) || !bounded(hi) || !(lo > 0.0f)) return false;
    if (out) *out = {lo, hi, error};
    return true;
}
} // namespace

bool positive_depth(const Context& x, const Cone& c, DepthBounds* out) {
    return arithmetic_supported() && x.valid && sphere_ok(c) && depth_bounds(x, c, out);
}

float sine_upper(float cos_lower) {
    if (!arithmetic_supported() || !ordinary(cos_lower) || !(cos_lower > 0.0f) || !(cos_lower < 1.0f)) return 1.0f;
    return sqrt_up(up(1.0f - down(cos_lower * cos_lower)));
}

Outcome classify(const Context& x, const Cone& c, unsigned cull, Proof& proof) {
    proof.valid = false;
    if (!arithmetic_supported() || !x.valid || (cull != 1 && cull != 2) || !sphere_ok(c) || !axis_within_unit(c.axis) ||
        !ordinary(c.cos_lower) || !(c.cos_lower > 0.0f) || !(c.cos_lower < 1.0f) ||
        !ordinary(c.sin_upper) || !(c.sin_upper >= sine_upper(c.cos_lower)) ||
        !ordinary(c.min_normal) || !(c.min_normal > 0.0f)) return Uncertain;
    Interval q[3];
    Interval dot = point(0.0f);
    float qnorm = 0.0f;
    for (unsigned r = 0; r < 3; ++r) {
        q[r] = add(scale(x.determinant, c.center[r]), x.translation[r]);
        if (!bounded(q[r])) return Uncertain;
        dot = add(dot, scale(q[r], c.axis[r]));
        qnorm = add_up(qnorm, magnitude(q[r]));
    }
    if (!bounded(dot) || !bounded(qnorm)) return Uncertain;
    const bool positive = dot.lo > 0.0f;
    const float d = positive ? dot.lo : -dot.hi;
    if (!(d > 0.0f)) return Uncertain;
    const float margin = down(down(c.cos_lower * d) -
        add_up(mul_up(c.sin_upper, qnorm), mul_up(magnitude(x.determinant), c.radius)));
    if (!(margin > 0.0f) || !finite(margin)) return Uncertain;
    DepthBounds depth;
    if (!depth_bounds(x, c, &depth)) return Uncertain;
    if (positive == (cull == 2U)) return Back;
    const float h_x = row_sum(x, c, 0), h_y = row_sum(x, c, 1);
    const float cube = mul_up(mul_up(depth.hi, depth.hi), depth.hi);
    const float area = down(down(c.min_normal * margin) / cube);
    if (!bounded(h_x) || !bounded(h_y) || !bounded(cube) || !finite(area) || !(area > kFloor)) return Uncertain;
    proof.wlo = depth.lo; proof.whi = depth.hi;
    proof.x_bound = div_up(h_x, depth.lo); proof.y_bound = div_up(h_y, depth.lo);
    proof.x_error = transform_error(h_x); proof.y_error = transform_error(h_y);
    proof.area_lower = area;
    const float wrange = up(depth.hi - depth.lo);
    // |Xa/Wa-Xb/Wb| <= |Xa-Xb|/Wlo + (H_X/Wlo)*|Wa-Wb|/Wlo.
    // These tight ideal spans let the cache pass skip per-vertex XY extrema.
    proof.x_span = div_up(add_up(mul_up(2.0f, row_spread(x, c, 0)), mul_up(proof.x_bound, wrange)), depth.lo);
    proof.y_span = div_up(add_up(mul_up(2.0f, row_spread(x, c, 1)), mul_up(proof.y_bound, wrange)), depth.lo);
    proof.valid = bounded(proof.x_bound) && bounded(proof.y_bound) && bounded(proof.x_span) && bounded(proof.y_span);
    if (!proof.valid) return Uncertain;
    return FrontCandidate;
}

bool projected_front(const Proof& p, const void* cache, unsigned vertices, unsigned stride) {
    if (!arithmetic_supported() || !p.valid || !cache || vertices < 3 || stride < 16 ||
        ((reinterpret_cast<std::uintptr_t>(cache) | stride) & 3U)) return false;
    std::uint32_t imin_bits = ~0U, imax_bits = 0, xy_bits = 0, subnormal = 0;
    const auto* v = static_cast<const std::uint8_t*>(cache);
    for (unsigned i = 0; i < vertices; ++i, v += stride) {
        const std::uint32_t xb = read_word(v, 4) & 0x7fffffffU;
        const std::uint32_t yb = read_word(v, 8) & 0x7fffffffU;
        const std::uint32_t ib = read_word(v, 12);
        // Positive finite float words have the same ordering as unsigned
        // integers. Validate the extrema once after scanning. For XY, the
        // combined word is >= either magnitude: its upper-bound check may
        // conservatively decline a group but cannot admit an invalid value.
        imin_bits = ib < imin_bits ? ib : imin_bits;
        imax_bits = ib > imax_bits ? ib : imax_bits;
        xy_bits |= xb | yb;
        subnormal |= (xb - 1U < 0x007fffffU) | (yb - 1U < 0x007fffffU);
    }
    if (imin_bits < 0x00800000U || imax_bits >= 0x7f800000U ||
        subnormal || xy_bits > 0x4e800000U) return false;
    const float imin = from_bits(imin_bits), imax = from_bits(imax_bits);
    // Stage one guarantees positive W; the scan guarantees positive I.
    // Only the lower/lower and upper/upper products can be extrema.
    const Interval wi = {down(p.wlo * imin), up(p.whi * imax)};
    if (!bounded(wi)) return false;
    const float relative = magnitude(sub(wi, point(1.0f)));
    // Reconstruct an upper bound on the actual projected magnitude from the
    // ideal |X/W| bound and the actual reciprocal. The two-epsilon inflation
    // covers target FMUL rounding; kFloor covers a flushed tiny result. The
    // integer scan independently establishes the 2^30 cap.
    const float xabs = minimum(0x1p30f, add_up(mul_up(mul_up(
        add_up(mul_up(p.x_bound, p.whi), p.x_error), imax), 1.0f + 2.0f * kEpsilon), kFloor));
    const float yabs = minimum(0x1p30f, add_up(mul_up(mul_up(
        add_up(mul_up(p.y_bound, p.whi), p.y_error), imax), 1.0f + 2.0f * kEpsilon), kFloor));
    const float ex = add_up(add_up(mul_up(p.x_bound, relative), mul_up(p.x_error, imax)),
                            add_up(mul_up(2.0f * kEpsilon, xabs), kFloor));
    const float ey = add_up(add_up(mul_up(p.y_bound, relative), mul_up(p.y_error, imax)),
                            add_up(mul_up(2.0f * kEpsilon, yabs), kFloor));
    // classify() bounds ideal projected spans from the raw AABB. Each of
    // the two endpoints may move by ex/ey, so no XY extrema scan is needed.
    const float dx = add_up(p.x_span, mul_up(2.0f, ex)), dy = add_up(p.y_span, mul_up(2.0f, ey));
    // Compare the ideal area to the exact determinant of the observed cache:
    // four cross terms of edge*coordinate-error plus two error products.
    float error = add_up(mul_up(4.0f, add_up(mul_up(dx, ey), mul_up(dy, ex))), mul_up(8.0f, mul_up(ex, ey)));
    // Four FSUBs, a rounded second FMUL and the pinned first-product FMAC.
    error = add_up(error, add_up(mul_up(64.0f * kEpsilon, mul_up(dx, dy)), kFloor));
    return finite(error) && p.area_lower > error;
}

float normal_lower_bound(const float axis[3], float cos_lower, const std::int64_t normal[3]) {
    Interval axis2;
    if (!arithmetic_supported() || !normal || !axis_ok(axis, &axis2) || !ordinary(cos_lower) || !(cos_lower > 0.0f) || !(cos_lower < 1.0f)) return 0.0f;
    Interval dot = point(0.0f), norm2 = point(0.0f);
    std::uint64_t largest = 0;
    for (unsigned i = 0; i < 3; ++i) {
        // Raw s16 cross components are strictly below 2^33 in magnitude.
        if (normal[i] <= -std::int64_t(0x200000000ULL) || normal[i] >= std::int64_t(0x200000000ULL)) return 0.0f;
        const std::uint64_t mag = normal[i] < 0 ? std::uint64_t(-normal[i]) : std::uint64_t(normal[i]);
        if (mag > largest) largest = mag;
        const float f = float(normal[i]);
        const Interval n = {down(f), up(f)};
        dot = add(dot, scale(n, axis[i]));
        norm2 = add(norm2, mul(n, n));
    }
    if (!largest || !bounded(dot) || !bounded(norm2) || !(dot.lo > 0.0f)) return 0.0f;
    const float norm = sqrt_up(mul_up(norm2.hi, axis2.hi));
    if (!(dot.lo > mul_up(cos_lower, norm))) return 0.0f;
    unsigned exponent = 0;
    while (largest >>= 1) ++exponent;
    return from_bits((127U + exponent) << 23);
}

bool strict_front(const void* cache, const std::uint8_t* index, unsigned count,
                  unsigned mask, unsigned cull, bool actor_eol, unsigned stride) {
    if (!arithmetic_supported() || !cache || !index || (cull != 1 && cull != 2) || stride < 16 ||
        ((reinterpret_cast<std::uintptr_t>(cache) | stride) & 3U)) return false;
    unsigned first = 0;
    while (first < count) {
        unsigned end = count;
        if (actor_eol) {
            end = first;
            while (end < count && !(index[end] & 128U)) ++end;
            if (end < count) ++end;
        }
        if (end - first < 3) return false;
        for (unsigned i = first; i + 2 < end; ++i) {
            const auto* a = static_cast<const std::uint8_t*>(cache) + (index[i] & mask) * stride;
            const auto* b = static_cast<const std::uint8_t*>(cache) + (index[i + 1] & mask) * stride;
            const auto* c = static_cast<const std::uint8_t*>(cache) + (index[i + 2] & mask) * stride;
            float area = target_area(read_float(a,4), read_float(a,8), read_float(b,4), read_float(b,8), read_float(c,4), read_float(c,8));
            if ((i - first) & 1U) area = -area;
            if (!finite(area) || !(cull == 1 ? area > 0.0f : area < 0.0f)) return false;
        }
        first = end;
    }
    return count >= 3;
}

}}} // namespace re4dc::bf::certificate
