#pragma once
// CPU_BACKFACE=2: shared ABI for the world and actor store-queue emitters.
// Inputs are projected 32-byte PVR vertices and already-unclipped indices.
#include <cstddef>
#include <cstdint>

#include <sh4zam/shz_strip.h>
using BackfaceSq = shz_strip_sq_t;

namespace re4dc { namespace bf {
// Cull is 1 or 2; callers preserve two-sided/material exclusions and SQ lock.
// Low 8 mask bits select the cache index. Bit 8 marks an actor meshlet stream:
// index bit 7 ends a strip, resets parity, and is never part of a cache index.
inline unsigned strip_sq(const void* cache, const uint8_t* indices,
                         unsigned n, unsigned mask, unsigned cull,
                         uint32_t*& q) {
    BackfaceSq context{cache, indices, n, mask, cull, q, 0, 0};
    shz_strip_sq(&context);
    q = context.q;
    return context.sent;
}
inline unsigned stream_sq(const void* cache, const uint8_t* indices,
                          unsigned n, unsigned cull, uint32_t*& q) {
    return strip_sq(cache, indices, n, 0x17f, cull, q);
}
}} // namespace re4dc::bf
