#pragma once
// Build 29 uses the existing FE/v3 RGB565 record and 120-byte BakeBlock.
// Ordinary bake states are zero or palette_hash() | 1 (odd). An even nonzero
// state plus a non-boolean clamped word cannot collide with an ordinary bake.
#include <cstdint>
#include <cstring>
#include <cmath>
#include "../../../room/source_lighting.hpp"

namespace re4dc { namespace fallback29 {
constexpr std::uint32_t kState = 0x46423290U;
constexpr std::uint32_t kFlags = 0xf0290000U;
constexpr unsigned kFoldScale = 1U, kBakeProbe = 2U;
struct Bake {
    std::uint32_t state, flags;
    float reference[12];
    float reserved[16];
};
static_assert(sizeof(Bake) == 120, "existing FE/v3 BakeBlock size");

inline unsigned half(const unsigned char* p) {
    unsigned short v; std::memcpy(&v, p, 2); return v;
}
inline bool finite(float v) { return v == v && v <= 3.402823466e38f && v >= -3.402823466e38f; }

// This is admission to the extra bake policy, not a replacement for the actor
// blob/source qualification. No pointers or persistent bindings are cached.
inline const Bake* tagged(const unsigned char* p, unsigned bytes) {
    if (!p || (reinterpret_cast<std::uintptr_t>(p) & 3U) || bytes < 160 || p[0] != 0xfe || p[1] != 3 || !(p[2] & 2U) ||
        (p[2] & 0x80U) || p[3] || half(p + 12)) return nullptr;
    const unsigned count = half(p + 4), records = half(p + 8) * 4U,
        indices = half(p + 10) * 4U, at = half(p + 14) * 4U;
    if (!count || count > (bytes - 32U) / 8U || records < 32U + count * 8U ||
        indices < records || at < indices || at > bytes || sizeof(Bake) > bytes - at)
        return nullptr;
    const Bake* b = reinterpret_cast<const Bake*>(p + at);
    if (b->state != kState || (b->flags & ~3U) != kFlags || !(b->flags & 3U) ||
        b->reserved[15] != 291.0f) return nullptr;
    for (unsigned i = 0; i < 12; ++i) if (!finite(b->reference[i])) return nullptr;
    for (unsigned c = 0; c < 3; ++c) {
        if (!(b->reference[c] > 0.0f) || b->reference[c] > 16384.0f ||
            b->reference[3U+c] < 0 || b->reference[3U+c] > 255 ||
            b->reference[6U+c] < 0 || b->reference[6U+c] > 255) return nullptr;
    }
    if (!(b->reference[9] > 0) || b->reference[9] > 4 || b->reference[10] != 1.0f ||
        b->reference[11] < 0 || b->reference[11] > 11 ||
        float(int(b->reference[11])) != b->reference[11]) return nullptr;
    return b;
}

// Preserve live colour/flash response using the quarter-Lambert energy of the
// current selected lights. Direction, attenuation and animated normal changes
// are intentionally approximated by this per-part RGB gain. Source alpha and
// texture/material animation are not read or changed. Vertex RGB must be the
// static source palette that the offline converter required explicitly.
inline bool gains(const render::SourceLighting& s, const Bake& b, unsigned out[3]) {
    const unsigned mode = unsigned(b.reference[11]);
    if (!s.enable || s.enable != 1U || s.mask > 255U ||
        s.normal_matrix[3] == 1.0e30f || s.normal_matrix[7] == 1.0e30f ||
        s.ambient_vertex != (mode & 1U) || s.material_vertex != ((mode >> 1) & 1U) ||
        s.diffuse != (mode >> 2) || !finite(s.tev_scale) ||
        s.tev_scale <= 0 || s.tev_scale > 4) return false;
    const float mean = s.diffuse == 0 ? 1.0f : s.diffuse == 2 ? 0.25f : 0.0f;
    for (unsigned c = 0; c < 3; ++c) {
        float energy = s.ambient_vertex ? b.reference[3U+c] : float(s.ambient[c]);
        for (unsigned i = 0; i < 8; ++i)
            if (s.mask & (1U << i)) energy += mean * s.lights[i].color[c];
        const float material = s.material_vertex ? b.reference[6U+c] : float(s.material[c]);
        const float gain = energy * (material * s.tev_scale) / (255.0f * b.reference[c]);
        if (!finite(gain) || gain < 0 || gain > 16.0f) return false;
        out[c] = unsigned(gain * 256.0f + 0.5f);
    }
    return true;
}
} }
