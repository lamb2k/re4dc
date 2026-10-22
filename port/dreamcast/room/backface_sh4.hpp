#pragma once
// CPU_BACKFACE=2: shared ABI for the world and actor store-queue emitters.
// Inputs are projected 32-byte PVR vertices and already-unclipped indices.
#include <cstddef>
#include <cstdint>

struct BackfaceSq {
    const void* cache;
    const uint8_t* indices;
    uint32_t n;
    uint32_t mask;
    uint32_t cull;
    uint32_t* q;
    uint32_t sent;
    uint32_t pieces;
};
#if defined(__sh__)
static_assert(sizeof(BackfaceSq) == 32, "SH-4 backface context ABI");
static_assert(offsetof(BackfaceSq, q) == 20, "SH-4 SQ output offset");
static_assert(offsetof(BackfaceSq, pieces) == 28, "SH-4 piece output offset");
#endif
extern "C" void re4dc_backface_sq(BackfaceSq* context);

namespace re4dc { namespace bf {
// Cull is 1 or 2; callers preserve two-sided/material exclusions and SQ lock.
// Low 8 mask bits select the cache index. Bit 8 marks an actor meshlet stream:
// index bit 7 ends a strip, resets parity, and is never part of a cache index.
inline unsigned strip_sq(const void* cache, const uint8_t* indices,
                         unsigned n, unsigned mask, unsigned cull,
                         uint32_t*& q) {
    BackfaceSq context{cache, indices, n, mask, cull, q, 0, 0};
    re4dc_backface_sq(&context);
    q = context.q;
    return context.sent;
}
inline unsigned stream_sq(const void* cache, const uint8_t* indices,
                          unsigned n, unsigned cull, uint32_t*& q) {
    return strip_sq(cache, indices, n, 0x17f, cull, q);
}
}} // namespace re4dc::bf
