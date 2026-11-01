#ifndef RE4DC_SCENERY_CLIP_GATHER_HPP
#define RE4DC_SCENERY_CLIP_GATHER_HPP

#include <cstdint>

// Build 24: an indexed streamed meshlet already transformed its pool directly.
// Only the scalar clipper needs the legacy local-corner array. Keep that array's
// indices, but populate exactly the corners referenced by its clipped strips.
// Package adoption validates the 0..255 indices, even u16 offset table, and
// 4-byte-aligned 12-byte vertices. No allocation, source mutation or new owner.
namespace re4dc { namespace scenery_clip24 {
struct Gather {
    std::uint32_t seen[8];
    bool started = false;

    // Most picks do not clip: do not clear 32 bytes until the first consumer.
    void begin() { started = false; }

    template<class Vertex>
    unsigned fill(const Vertex* pool, const std::uint16_t* offsets, Vertex* local,
                  const std::uint8_t* indices, unsigned count) {
        static_assert(sizeof(Vertex) == 12, "scenery clip gather requires AoS12");
        if (!started) {
            for (unsigned i = 0; i < 8; ++i) seen[i] = 0;
            started = true;
        }
        typedef std::uint32_t __attribute__((may_alias)) Word;
        unsigned copied = 0;
        for (unsigned i = 0; i < count; ++i) {
            const unsigned index = indices[i], word = index >> 5;
            const std::uint32_t bit = std::uint32_t(1) << (index & 31U);
            if (seen[word] & bit) continue;
            const Word* from = reinterpret_cast<const Word*>(pool + offsets[index]);
            Word* to = reinterpret_cast<Word*>(local + index);
            to[0] = from[0]; to[1] = from[1]; to[2] = from[2];
            seen[word] |= bit;
            ++copied;
        }
        return copied;
    }
};
} }
#endif
