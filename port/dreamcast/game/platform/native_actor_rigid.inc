// platform/native_actor_rigid.inc -- RIGID_CHUNK (rigid20.mk; lane props-new-path, RIGID20-STATUS.md).
// Included by native_actor_fast.cpp inside its anonymous namespace after Part, only when RE4DC_RIGID_CHUNK is set
// (knob 0 compiles nothing). Rigid models = unskinned native actor parts (Frame mode kRigid): trucks, carts, doors,
// boats, breakables, weapons, cObj room props.
//
// Render only, an approximation (CLAUDE.md approximation rule; gate = gameplay equivalence + look check):
//   * one object matrix per part (Frame::screen, built once per (info, matrices) per frame, as today);
//   * size rule from the part's bind sphere in screen pixels (the scenery path's per-placement culling):
//       r <  RIGID_CULL_PX     not drawn (sub-pixel props);
//       r <  RIGID_FLAT_PX     one light colour per part (no per-vertex lighting) and the coarsest LOD level;
//   * strips through the shared chunk-submit back end (chunk_submit.h v1.1, direct vertices), the same back end as the
//     PS2 world scenery. Falls back to the store-queue window when the part is not on the direct path.
#if !RE4DC_ACTOR_DIRECT
#error RIGID_CHUNK needs NATIVE_ACTOR_DIRECT=1
#endif
}  // namespace
#include "chunk_submit.h"
namespace {
#ifndef RE4DC_RIGID_CULL_PX
#define RE4DC_RIGID_CULL_PX 0.75f
#endif
#ifndef RE4DC_RIGID_FLAT_PX
#define RE4DC_RIGID_FLAT_PX 12.0f
#endif
struct RigidStats { unsigned parts, culled, flat, meshlets, fallback; } rigid_stats;
unsigned rigid_stats_log = 0;

// Bind-sphere radius in screen pixels (0 when the sphere reaches the near plane: draw it in full).
inline float rigid_pixels(const Re4dcModelPart& p, const BlobHeader& b, float near_distance) {
    if (!(b.radius > 0.0f)) return 1.0e9f;
    const float* m = p.modelview; const float* c = b.center;
    const float depth = -(m[8] * c[0] + m[9] * c[1] + m[10] * c[2] + m[11]);
    const float scale = std::sqrt(m[0] * m[0] + m[4] * m[4] + m[8] * m[8]);
    if (!(depth - b.radius * scale > near_distance)) return 1.0e9f;
    return 0.5f * p.viewport[2] * std::fabs(p.projection[1]) * scale * b.radius / depth;
}

inline u8 rigid_code(unsigned oc) {
    return u8(((oc & kOcLeft) ? 32U : 0U) | ((oc & kOcRight) ? 16U : 0U) | ((oc & kOcTop) ? 8U : 0U) |
              ((oc & kOcBottom) ? 4U : 0U) | ((oc & kOcNear) ? 2U : 0U) | ((oc & kOcFar) ? 1U : 0U));
}
// Strips with a corner past near or far come back here: culled when every corner shares a screen edge or far, sent
// as is when no corner is past near (the PVR scissors the rest), else the actor clipper.
struct RigidClip { Part* e; const Records* r; re4dc_chunk_sink* s; };
int rigid_clip(void* ctx, const uint8_t* idx, unsigned n, unsigned form) {
    (void)form;
    RigidClip& c = *static_cast<RigidClip*>(ctx);
    Part& e = *c.e;
    unsigned all = ~0U, any = 0;
    for (unsigned k = 0; k < n; ++k) { const unsigned oc = e.cache.oc[idx[k] & 127U]; all &= oc; any |= oc; }
    if (all & kOcCull) { ++stats.strips_culled; return 1; }
    e.sq = *re4dc_chunk_sq(c.s);
    bool ok = true;
    if (!(any & kOcNear)) { e.strip(idx, n); e.output += n - 2U; }
    else ok = e.clip_strip(*c.r, idx, n);
    *re4dc_chunk_sq(c.s) = e.sq;
    return ok ? 1 : -1;
}
// One meshlet's strips: the back end when the part is on the direct path, else today's window sends.
bool rigid_strips(Part& e, const Records& r, const u8* index, unsigned nv, unsigned ni, unsigned nt, unsigned any) {
    ++rigid_stats.meshlets;
    if (e.direct && nv <= RE4DC_CHUNK_MAX_CORNERS && e.slots + 6U * nt <= 32767U) {
        u8 codes[RE4DC_CHUNK_MAX_CORNERS];
        for (unsigned i = 0; i < nv; ++i) codes[i] = rigid_code(e.cache.oc[i]);
        re4dc_chunk_sink s;
        RigidClip cc{&e, &r, &s};
        re4dc_chunk_window_begin(&s, e.sq, nullptr, 255U, rigid_clip, &cc);
        re4dc_chunk_vertices_direct(&s, e.cache.v, codes, nv);
        const int res = re4dc_chunk_strips(&s, index, ni, RE4DC_CHUNK_STRIPS_ACTOR);
        e.sq = re4dc_chunk_window_end(&s);
        e.slots += s.slots; e.output += s.slots - 2U * s.strips;
        e.input += nt;
        return res > 0;
    }
    ++rigid_stats.fallback;
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    re4dc::dfa26::hit(re4dc::dfa26::ActorRigidBackend);
#endif
    if (!(any & (kOcCull | kOcNear)) && e.fits(ni)) { ++stats.meshlets_whole; return e.whole(index, ni, nt); }
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    re4dc::dfa26::hit(re4dc::dfa26::ActorStripScan);
#endif
    return e.strips(r, index, ni);
}
void rigid_log() {
    if (frame_serial - rigid_stats_log < 600U) return;
    rigid_stats_log = frame_serial;
    re4dc_log("RIGIDCHUNK frame=%u parts=%u culled=%u flat=%u meshlets=%u fallback=%u\n", frame_serial,
              rigid_stats.parts, rigid_stats.culled, rigid_stats.flat, rigid_stats.meshlets, rigid_stats.fallback);
    rigid_stats = RigidStats{};
}
