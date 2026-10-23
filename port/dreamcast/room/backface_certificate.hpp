#pragma once

#include <cstdint>
#include <cstring>

// BACKFACE_CONE_FRONT: a geometric candidate is never permission to bypass the
// target classifier. Only projected_front(), using this draw's actual cache,
// completes the certificate. The implementation must be compiled without fast
// math or contraction; callers may retain their ordinary rendering flags.
namespace re4dc { namespace bf { namespace certificate {

struct Interval { float lo, hi; };
struct Context {
    float matrix[12];                 // X, Y, W rows, four coefficients each
    Interval translation[3], determinant; // adj(A)*t, invariant for this matrix
    float near_distance;
    bool valid;
};

struct Cone {
    float center[3], radius;
    float extent[3];                  // tight raw AABB half extents, same center
    // A positive-length axis scaled to length <= 1, preferably by an exact
    // power of two. The producer bounds normals around its UNIT direction.
    float axis[3], cos_lower, sin_upper, min_normal;
};

struct DepthBounds { float lo, hi, transform_error; };
struct Proof {
    float wlo, whi, x_bound, y_bound, x_error, y_error, w_error, area_lower;
    float x_span, y_span;             // ideal projected coordinate ranges
    bool valid;
};

// XYZ are exact signed or unsigned 16-bit coordinates at byte offsets 0,2,4.
// Optional indices select raw records in cache-vertex order; both strides are
// bytes. The caller supplies valid records from the same geometry and matrix
// that produced this draw's cache. Extra scanned vertices are conservative.
struct RawPositions {
    const void* data;
    unsigned stride;
    const std::uint16_t* indices;
    unsigned index_stride;
    bool unsigned_values;
};

enum Outcome { Uncertain, Back, FrontCandidate };

// Empirical cold-cost admission, not a facing proof or a speedup guarantee.
// Counts come from validated byte-indexed groups; reject unsupported ranges
// before the bounded integer scores below. Count ALL scanned cache vertices.
inline bool cost_counts(unsigned vertices, unsigned indices, unsigned strips) {
    return vertices >= 3U && vertices <= 256U && indices <= 65535U &&
           strips != 0U && strips <= indices / 3U;
}
// Actor model: potential saved work 16*I+128*S must exceed 4608+80*V.
// Dividing both sides by 16 makes this a few integer shifts/adds. This admits
// profitable smaller groups without a fixed 256-index/64-strip/4x-reuse rule.
inline bool worth_front(unsigned vertices, unsigned indices, unsigned strips) {
    return cost_counts(vertices, indices, strips) &&
           indices + 8U * strips > 288U + 5U * vertices;
}
// World's count-prefixed walker has different per-strip overhead. These
// coefficients are qualified separately in world_target_test.py.
inline bool worth_front_world(unsigned vertices, unsigned indices, unsigned strips) {
    return cost_counts(vertices, indices, strips) &&
           10U * indices + 168U * strips > 4800U + 65U * vertices;
}

// matrix is exactly the column-major 4x4 loaded into XMTRX. Rows 0,1,3
// produce X,Y,W. No recomposition or inversion is performed here.
// SH4 entry points require single precision, DN=1, RN or RZ, and masked
// arithmetic exceptions. Unsupported FPSCR modes decline without changing it.
bool prepare(Context&, const float matrix[16], float near_distance);
bool positive_depth(const Context&, const Cone&, DepthBounds* = nullptr);

// Back describes the real-arithmetic cone side only; it MUST NOT authorize a
// new target-FMAC rejection. Existing back rejection may use positive_depth()
// as an additional guard. FrontCandidate needs projected_front() below.
Outcome classify(const Context&, const Cone&, unsigned cull, Proof&);

// PVR entries have x,y,reciprocal at byte offsets 4,8,12. Pair each cached
// reciprocal with its own raw-position W dot product, so depth variation does
// not masquerade as reciprocal error. No FSRRA accuracy assumption is used.
// context/proof/raw/cache must describe this same draw and vertex ordering.
bool projected_front(const Context&, const Proof&, const void* cache, unsigned vertices,
                     const RawPositions&, unsigned cache_stride = 32);

// Producer/check-build utilities. Zero means degenerate, outside the supplied
// cone, or unsupported. A positive return is a power-of-two lower bound on
// |normal|. All three signed cross components must have been computed exactly.
float normal_lower_bound(const float axis[3], float cos_lower, const std::int64_t normal[3]);
float sine_upper(float cos_lower);

// Exact target determinant DAG, for check builds only. actor_eol resets strip
// parity at each bit7 terminator. Every drawn triangle must be strictly front.
bool strict_front(const void* cache, const std::uint8_t* index, unsigned count,
                  unsigned mask, unsigned cull, bool actor_eol = false, unsigned stride = 32);

}}} // namespace re4dc::bf::certificate
