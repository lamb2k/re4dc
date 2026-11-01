#pragma once

// Build 26: a near-crossing strip need not reconstruct/clip its wholly-front
// triangles. Those triangles use the same projected cache as ordinary actor
// strips. This is a render approximation: cache FTRV/reciprocal rounding can
// differ from world_of + project at subpixel or cull/near boundaries.
#include "../../../room/pvr_geometry.hpp"

namespace re4dc::actor_clip26 {
enum FrontResult : int { Invalid = -2, Slow = -1, Culled = 0, Front = 1 };

// local[] already has strip parity applied; all bounds are checked before any
// cache/outcode read. No source positions, normals, palettes or lights enter
// this path. Near/far crossings retain the existing source clipper.
template<unsigned DepthMask = 48U>
inline FrontResult front_triangle(const pvr_vertex_t* cache, const unsigned char* outcodes,
                                  unsigned vertex_count, const unsigned local[3],
                                  unsigned cull, float width, float height,
                                  pvr_vertex_t output[3]) {
    if (vertex_count > 128 || local[0] >= vertex_count || local[1] >= vertex_count || local[2] >= vertex_count)
        return Invalid;
    // AVK uses near32/far16; the portable actor path uses near2/far1.
    if ((outcodes[local[0]] | outcodes[local[1]] | outcodes[local[2]]) & DepthMask) return Slow;
    const pvr_vertex_t& a = cache[local[0]];
    const pvr_vertex_t& b = cache[local[1]];
    const pvr_vertex_t& c = cache[local[2]];
    if (!render::is_finite(a.x) || !render::is_finite(a.y) || !render::is_finite(a.z) ||
        !render::is_finite(b.x) || !render::is_finite(b.y) || !render::is_finite(b.z) ||
        !render::is_finite(c.x) || !render::is_finite(c.y) || !render::is_finite(c.z)) return Slow;
    if (!render::triangle_visible_xy(a, b, c, static_cast<unsigned char>(cull), width, height)) return Culled;
    output[0] = a; output[1] = b; output[2] = c;
    output[0].flags = output[1].flags = PVR_CMD_VERTEX;
    output[2].flags = PVR_CMD_VERTEX_EOL;
    // UV16 stores an unpacked-U scratch word here; the clipped packet's offset
    // colour is zero. The packed UV word and untouched V word are already final.
    output[0].oargb = output[1].oargb = output[2].oargb = 0;
    return Front;
}

template<bool Reuse, unsigned DepthMask = 48U, class Prepare, class EmitSlow, class EmitFront>
bool walk_strip(const unsigned char* index, unsigned n, const pvr_vertex_t* cache,
                const unsigned char* outcodes, unsigned vertex_count, unsigned cull,
                float width, float height, Prepare&& prepare, EmitSlow&& slow, EmitFront&& front) {
    if (n < 3) return true;
    render::RenderVertex saved[3];
    float saved_alpha[3];
    unsigned saved_corner[3] = {~0U, ~0U, ~0U};
    for (unsigned t = 0; t < n - 2; ++t) {
        const unsigned corner[3] = {t + (t & 1U), t + ((t & 1U) ^ 1U), t + 2U};
        const unsigned local[3] = {unsigned(index[corner[0]] & 127U), unsigned(index[corner[1]] & 127U),
                                   unsigned(index[corner[2]] & 127U)};
        pvr_vertex_t output[3];
        const FrontResult result = front_triangle<DepthMask>(cache, outcodes, vertex_count, local, cull, width, height, output);
        if (result == Invalid) return false;
        if (result == Culled) continue;
        if (result == Front) {
            if (!front(output)) return false;
            continue;
        }
        render::RenderVertex in[3];
        float alpha[3];
        for (unsigned k = 0; k < 3; ++k) {
            if constexpr (Reuse) {
                const unsigned slot = corner[k] % 3U;
                if (saved_corner[slot] != corner[k]) {
                    prepare(corner[k], saved[slot], saved_alpha[slot]);
                    saved_corner[slot] = corner[k];
                }
                in[k] = saved[slot]; alpha[k] = saved_alpha[slot];
            } else {
                prepare(corner[k], in[k], alpha[k]);
            }
        }
        if (!slow(in, alpha)) return false;
    }
    return true;
}
} // namespace re4dc::actor_clip26
