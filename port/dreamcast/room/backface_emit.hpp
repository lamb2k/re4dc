// backface_emit.hpp (lane backface22, 2026-10-22; CPU_BACKFACE, backface.mk): send only the triangles of a strip the PVR
// would draw. The ISP rejects back faces only after the TA has written them into the display list (vertex parameters +
// object pointer blocks in VRAM); dropping them before the store-queue write saves the SH-4 copy, the TA parameter space
// and the ISP setup.
//
// Rule (exact for every triangle that faces the camera):
// - facing: screen area of (v[i], v[i+1], v[i+2]) from the transformed cache entries (x, y at words 1, 2), negated for odd
//   i (the strip's alternating winding, as the TA treats it). cull 2 (PVR_CULLING_CW) rejects area >= 0, cull 1
//   (PVR_CULLING_CCW) rejects area <= 0 (pvr_geometry.hpp's clipper convention; zero area draws nothing either way).
//   cull 0 (none / double-sided) never reaches this code.
// - a back run is dropped when it starts or ends the strip (any length) or is >= 3 triangles long inside it; shorter inner
//   runs stay (a strip restart costs 2 vertices) and the ISP rejects them as before.
// - every kept piece starts on an even triangle of the original strip (one back triangle is kept in front of a piece
//   that would start odd), so each kept triangle keeps its winding parity and its exact vertex words.
#pragma once
#include <cstdint>
#include <dc/pvr.h>

namespace re4dc::bf {

// idx: n (3..255) index bytes into cache, masked with `mask` (actor meshlets carry an EOL flag in bit 7).
// emit(const std::uint8_t* idx, unsigned count): sends one strip of count >= 3 plain indices.
// Returns the vertices sent.
template <class Emit>
inline unsigned strip(const pvr_vertex_t* __restrict cache, const std::uint8_t* __restrict idx, unsigned n, unsigned mask,
                      unsigned cull, Emit&& emit) {
    if (n < 3) return 0;
    std::uint8_t plain[256];
    for (unsigned k = 0; k < n; ++k) plain[k] = std::uint8_t(idx[k] & mask);
    const unsigned t = n - 2;
    std::uint8_t keep[256];
    // Facing.
    const float sign = cull == 2 ? 1.0f : -1.0f;
    {
        const pvr_vertex_t* a = cache + plain[0];
        const pvr_vertex_t* b = cache + plain[1];
        float ax = a->x, ay = a->y, bx = b->x, by = b->y;
        for (unsigned i = 0; i < t; ++i) {
            const pvr_vertex_t* c = cache + plain[i + 2];
            const float cx = c->x, cy = c->y;
            float area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);
            if (i & 1) area = -area;
            keep[i] = (sign * area) < 0.0f;  // front: rejected sign excluded, zero area dropped
            ax = bx; ay = by; bx = cx; by = cy;
        }
    }
    // Back runs that stay: inner runs of 1 or 2 triangles.
    for (unsigned i = 0; i < t;) {
        if (keep[i] == 1) { ++i; continue; }
        unsigned j = i;
        while (j < t && keep[j] != 1) ++j;
        if (i > 0 && j < t && j - i < 3)
            for (unsigned q = i; q < j; ++q) keep[q] = 2;  // kept for the ISP to reject
        i = j;
    }
    unsigned sent = 0;
    for (unsigned i = 0; i < t;) {
        if (!keep[i]) { ++i; continue; }
        unsigned a = i;
        while (i < t && keep[i]) ++i;
        if (a & 1) --a;  // parity: start on an even triangle (a - 1 is a dropped back triangle)
        const unsigned count = i - a + 2;
        emit(plain + a, count);
        sent += count;
    }
    return sent;
}

}  // namespace re4dc::bf
