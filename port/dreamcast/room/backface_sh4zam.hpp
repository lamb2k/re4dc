#pragma once
// Runtime primitives from SH4ZAM pin 33fa4850, not a replacement C bf::strip.
// Kept separate from game headers, whose legacy cmath declarations conflict
// with newlib's C math declarations pulled in by the SDK.
#include <sh4zam/shz_vector.h>
#include <sh4zam/shz_scalar.h>

namespace re4dc { namespace bf { namespace sdk {
// CPU_BACKFACE=1's actual SH-4 object rounds the second product, then FMACs
// the first product onto its negation. A mathematically collinear triangle
// can therefore have nonzero area. Preserve that target operation order.
__attribute__((always_inline)) inline float area(shz_vec2_t a,
                                                shz_vec2_t b,
                                                shz_vec2_t c) {
    const shz_vec2_t ba = shz_vec2_sub(b, a);
    const shz_vec2_t ca = shz_vec2_sub(c, a);
    float rounded_second = ba.y * ca.x;
#if defined(__sh__)
    // Prevent reassociation or reverse FMAC fusion; this is a register barrier,
    // not another arithmetic instruction. -ffp-contract=fast is required.
    asm("" : "+f" (rounded_second));
#else
    asm("" : "+x" (rounded_second));
#endif
    return shz_fmaf(ba.x, ca.y, -rounded_second);
}
__attribute__((always_inline)) inline bool front(shz_vec2_t a, shz_vec2_t b,
                                                 shz_vec2_t c,
                                                 unsigned triangle,
                                                 unsigned cull) {
    float determinant = area(a, b, c);
    if (triangle & 1u) determinant = -determinant;
    return cull == 2u ? determinant < 0.0f : determinant > 0.0f;
}
}}}
