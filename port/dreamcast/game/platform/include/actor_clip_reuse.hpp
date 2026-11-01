#pragma once

// Build 24: reuse the two shared corners of a near-clipped triangle strip.
// Prepare is pure with respect to the strip inputs. Emit consumes its three
// corners synchronously, in the same winding and triangle order as the old
// per-triangle builder, and returns false on the first capacity refusal.
#include "../../../room/pvr_geometry.hpp"

namespace re4dc::actor_clip {
template<class Prepare, class Emit>
bool reuse_strip(unsigned n, Prepare&& prepare, Emit&& emit) {
    if (n < 3) return true;
    render::RenderVertex in[3];
    float opacity[3];
    for (unsigned k = 0; k < 3; ++k) prepare(k, in[k], opacity[k]);
    for (unsigned t = 0; t < n - 2; ++t) {
        if (!emit(in, opacity)) return false;
        if (t + 3 < n) {
            // 0,1,2 -> 2,1,3 -> 2,3,4: one copy preserves strip parity.
            in[t & 1U] = in[2];
            opacity[t & 1U] = opacity[2];
            prepare(t + 3, in[2], opacity[2]);
        }
    }
    return true;
}
}  // namespace re4dc::actor_clip
