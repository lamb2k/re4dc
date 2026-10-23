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
    float wlo, whi, x_bound, y_bound, x_error, y_error, area_lower;
    float x_span, y_span;             // ideal projected coordinate ranges
    bool valid;
};

enum Outcome { Uncertain, Back, FrontCandidate };

// Cost admission, not a facing proof. Target measurements show that setup is
// repaid by dense reuse across many short strips; small/long-strip groups keep
// the existing classifier. Integer division avoids an overflowing product.
inline bool worth_front(unsigned vertices, unsigned indices, unsigned strips) {
    return vertices >= 3U && indices >= 256U && indices / 4U >= vertices && strips >= 64U;
}

// The global W/I enclosure is useful when this box has constant ideal W.
// Decline depth-varying boxes before paying for cofactor preparation. This is
// only a cost policy: the full certificate still checks the actual projection.
inline bool exact_zero(float value) {
    std::uint32_t word;
    std::memcpy(&word, &value, sizeof(word));
    return (word & 0x7fffffffU) == 0U;
}
inline bool flat_depth(const float matrix[16], const float extent[3]) {
    // Bit tests also work before the supported-FPSCR guard: comparing a
    // denormal float with zero could itself trap with DN=0.
    return (exact_zero(extent[0]) || exact_zero(matrix[3])) &&
           (exact_zero(extent[1]) || exact_zero(matrix[7])) &&
           (exact_zero(extent[2]) || exact_zero(matrix[11]));
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

// PVR entries have x,y,reciprocal at byte offsets 4,8,12. Actual reciprocal
// extrema bound projection error without an FSRRA accuracy assumption.
bool projected_front(const Proof&, const void* cache, unsigned vertices, unsigned stride = 32);

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
