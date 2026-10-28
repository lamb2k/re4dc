#ifndef RE4DC_SCENERY_CLIP_INDEXED26_HPP
#define RE4DC_SCENERY_CLIP_INDEXED26_HPP

#include <cstdint>

// The package validator already authenticates every local index and pool
// offset. Borrow the same immutable pool until this synchronous clip call
// returns; do not stage its 12-byte records in a second array. Keeping this an
// accessor lets Emitter's exact corner decode/transform/clip order stay shared.
namespace re4dc { namespace scenery_clip26 {
template<class Vertex>
struct Indexed {
    const Vertex* pool;
    const std::uint16_t* offsets;
    const Vertex& operator[](unsigned local) const { return pool[offsets[local]]; }
};
} }

#endif
