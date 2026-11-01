#pragma once
#include <type_traits>

namespace re4dc::cloth_material11 {
// The Dreamcast GX object uses words 0..4 for image/shape/format/wrap/TLUT.
// Only actual GXInitTexObj calls establish this capture; full object copies
// preserve it, while the frontend's synthesized four-word objects clear it.
constexpr unsigned sampler_capture = 0x434d3101U;
constexpr unsigned linear_filters = 0x00000101U;

// GX's native uint32_t/u32 can be unsigned long on SH-4. Write through the
// object's actual unsigned 32-bit type; copied reader words remain unsigned.
template<class Word>
inline void init_sampler(Word* words, unsigned mip) {
    static_assert(sizeof(Word)==4 && std::is_integral_v<Word> && std::is_unsigned_v<Word>,
                  "GX sampler needs unsigned 32-bit words");
    words[5] = sampler_capture;
    // Source GXInitTexObj defaults: linear mag, linear min without mipmaps,
    // zero LOD/bias and enabled edge LOD. Mipmapped defaults remain unqualified.
    words[6] = mip ? 0U : linear_filters;
    words[7] = 2U;
}

template<class Word>
inline void lod_sampler(Word* words, int minf, int magf, float minl,
                        float maxl, float bias, unsigned bc, unsigned edge, int aniso) {
    static_assert(sizeof(Word)==4 && std::is_integral_v<Word> && std::is_unsigned_v<Word>,
                  "GX sampler needs unsigned 32-bit words");
    if (words[5] != sampler_capture) {
        words[5] = words[6] = words[7] = 0;
        return;
    }
    // Every changed LOD call revokes the previous qualified state first.
    words[6] = words[7] = 0;
    if (minf == 1 && magf == 1 && minl == 0.0f && maxl == 0.0f &&
        bias == 0.0f && bc <= 1 && edge <= 1 && aniso == 0) {
        words[6] = linear_filters;
        words[7] = bc | (edge << 1);
    }
}

inline bool linear_clamp(const unsigned* words) {
    return words[5] == sampler_capture && words[6] == linear_filters &&
           !(words[7] & ~3U) && words[3] == 0;
}
}
