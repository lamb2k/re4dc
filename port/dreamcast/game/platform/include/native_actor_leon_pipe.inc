// Included once by native_actor_fast.cpp after native_actor_owner_submit.inc, under LEON_NATIVE_PIPE
// (native_model_registry.mk; default 0; render only, exact). Leon's lean owner passes (coarse_actor_leon_pipe.inc)
// submit through re4dc_actor_submit_owned_runs' kernels, with what that call repeats proved once:
//  - re4dc_leon_pipe_preflight: re4dc_actor_preflight_owned_runs for runs whose fixed per-run terms (the run spans and
//    material index, one_qualifies' part / run field terms, blob_of) the caller proved with that full preflight for
//    the same plan. It evaluates the global terms as there; one_qualifies' per-frame terms (projection / viewport words,
//    the skin frame, each info's registry entry and owned source: find_skin's entry is the lease's, intact by
//    re4dc_actor_skin_validate); and per material the texture-material and packet-reserve terms (functions of the
//    material and of frame state no run changes). The caller runs the full preflight when it returns 0.
//  - re4dc_leon_pipe_submit: re4dc_actor_submit_owned_runs with each info's registry entry and source handed to
//    one_chunk (one_qualifies' result, proved by the preflight), and, at a change back to a material whose own first
//    window this call opened, a header change inside the open window (re4dc_leon_direct_switch: the header words and
//    counters of closing and reopening it) when the PS2 world barrier would be a no-op there. The same kernels run on
//    the same inputs in the same order: the TA receives the same words.
#include "leon_native_pipe.h"
namespace {
// The lease's registry entry and owned source of info (what one_qualifies finds for a lease-registered info).
bool leon_skin_of(const Re4dcActorSkinLease* lease, const void* info, const SkinEntry*& se, Re4dcActorSource& src) {
#if RE4DC_ACTOR_SKIN_OWNER_POOL
    return owned_skin_from_lease(lease, info, se, src);
#else
    for (unsigned k = 0; k < lease->count; ++k) {
        const unsigned i = lease->old[k].index;
        if (i < skin_count && skins[i].info == info && owned_skins[i].serial == lease->serial) {
            se = &skins[i];
            src = owned_skins[i].source;
            return true;
        }
    }
    return false;
#endif
}
// one_chunk's store-queue bound of the loaded part (6 slots per triangle of its meshlets; 0 without a blob).
unsigned leon_bound(const Re4dcModelPart& p) {
    const BlobHeader* blob = blob_of(p);
    if (!blob) return 0;
    const auto* table = reinterpret_cast<const MeshletInfo*>(reinterpret_cast<const u8*>(blob) + sizeof(BlobHeader));
    unsigned bound = 0;
    for (unsigned mi = 0; mi < blob->meshlets; ++mi) bound += table[mi].n.triangles();
    return 6U * bound;
}
#if defined(RE4DC_PS2_WORLD_DRAW) && RE4DC_PS2_WORLD_DRAW
bool leon_tr_idle(const Re4dcModelPart* p) { return re4dc_leon_owned_tr_idle(p) != 0; }
#else
bool leon_tr_idle(const Re4dcModelPart*) { return true; }  // no barrier between owned runs
#endif
}  // namespace

extern "C" int re4dc_leon_pipe_preflight(Re4dcModelPart* part, const Re4dcActorDrawRun* runs, unsigned n,
                                         const Re4dcActorOwnedMaterial* materials, unsigned nm,
                                         const Re4dcActorWorkspaceLease* workspace_lease,
                                         const Re4dcActorSkinLease* skin_lease, const Re4dcActorTextureLease* textures,
                                         unsigned source_frame) {
    if (!part || !runs || !materials || !n || n > kRe4dcActorRuns || owned_submission ||
        !re4dc_actor_workspace_validate(workspace_lease) || !re4dc_actor_skin_validate(skin_lease) ||
        !owned_all_textures(textures, nm))
        return 0;
    Re4dcActorStreamState before{};
    if (!re4dc_actor_stream_state(&before)) return 0;
    for (float f : part->projection) if (!re4dc::render::is_finite(f)) return 0;
    for (float f : part->viewport) if (!re4dc::render::is_finite(f)) return 0;
    const float near = part->projection[6] / (part->projection[5] - 1.0f), far = part->projection[6] / part->projection[5];
    if (!re4dc::render::is_finite(near) || !re4dc::render::is_finite(far) || !(near > 0) || !(far > near)) return 0;
    if (!(part->projection[0] == 0 && part->viewport[2] > 0 && part->viewport[3] > 0) || skin_frame != source_frame) return 0;
    unsigned done = 0;
    const void* info = nullptr;
    for (unsigned i = 0; i < n; ++i) {
        const Re4dcActorDrawRun& r = runs[i];
        if (r.material >= nm) return 0;
        if (r.chunk.info != info) {
            const SkinEntry* se = nullptr;
            Re4dcActorSource src{};
            if (!leon_skin_of(skin_lease, r.chunk.info, se, src) || find_skin(r.chunk.info, nullptr) != se ||
                se->materialized || !se->palette || !se->entries || !src.positions || !src.normals ||
                src.position_count != r.chunk.position_count || src.normal_count != r.chunk.normal_count)
                return 0;
            for (unsigned k = 0; k < 12; ++k) if (!re4dc::render::is_finite(r.chunk.modelview[k])) return 0;
            info = r.chunk.info;
        }
        if (done & (1U << r.material)) continue;
        owned_run_load(*part, r, materials[r.material]);
        if (!re4dc_actor_texture_material_validate(part, &textures[r.material])) return 0;
        Re4dcModelPacket packet{};
        if (!re4dc_model_packet_reserve(part, &packet) || packet.capacity < kCacheSlots + 64U) return 0;
        done |= 1U << r.material;
    }
    return 1;
}

// preflight: 0 = the caller preflighted these runs in this call with nothing run since (the pass that acquired the
// actor); otherwise the lite preflight, and the full one when that returns 0.
extern "C" int re4dc_leon_pipe_submit(Re4dcModelPart* part, const Re4dcActorDrawRun* runs, unsigned n,
                                      const Re4dcActorOwnedMaterial* materials, unsigned nm,
                                      const Re4dcActorWorkspaceLease* workspace_lease,
                                      const Re4dcActorSkinLease* skin_lease, const Re4dcActorTextureLease* textures,
                                      unsigned source_frame, int preflight) {
    if (preflight &&
        !re4dc_leon_pipe_preflight(part, runs, n, materials, nm, workspace_lease, skin_lease, textures, source_frame) &&
        !re4dc_actor_preflight_owned_runs(part, runs, n, materials, nm, workspace_lease, skin_lease, textures))
        return 0;
    Re4dcActorStreamState before{};
    if (!re4dc_actor_stream_state(&before)) return 0;
    for (unsigned i = 0; i < nm; ++i) if (!re4dc_actor_texture_commit(&textures[i])) return 0;
    OneWindow window;
    owned_submission = true;
    bool okay = true;
    unsigned previous = ~0U;
    Re4dcLeonHeader header[kRe4dcActorMaterials];
    for (auto& h : header) h.valid = 0;
    float scale[kRe4dcActorMaterials][2] = {};
    unsigned base = 0;  // store-queue slots this window sent before its current part's header (headers and parts)
    const void* info = nullptr;
    const SkinEntry* se = nullptr;
    Re4dcActorSource src{};
    for (unsigned i = 0; i < n && okay; ++i) {
        const unsigned material = runs[i].material;
        const bool changed = material != previous;
        owned_run_load(*part, runs[i], materials[material]);
        previous = material;
        if (runs[i].chunk.info != info) {
            // (the preflight proved an entry for every info; none can go before one_chunk would have declined)
            if (!leon_skin_of(skin_lease, runs[i].chunk.info, se, src)) { okay = false; break; }
            info = runs[i].chunk.info;
        }
        const unsigned bound = leon_bound(*part);
        bool switched = false;
        if (changed && window.open && header[material].valid && leon_tr_idle(part) &&
            base + window.slots + 1U + bound <= 32767U) {
#if RE4DC_GC_ASSET_MOTION_UNKNOWN
            if(window.motion_accounted)re4dc_gcasset::motion_pending_accounted();
#endif
            if (std::uint32_t* sq = re4dc_leon_direct_switch(part, &header[material], window.slots, window.sq)) {
#if RE4DC_GC_ASSET_MOTION_UNKNOWN
                window.motion_accounted=0;
#endif
                base += window.slots + 1U;
                window.sq = sq;
                window.slots = 0;
                window.direct.u_scale = scale[material][0];
                window.direct.v_scale = scale[material][1];
                switched = true;
            }
        }
        if (changed && !switched) {
            one_close(window);
            base = 0;
#if defined(RE4DC_PS2_WORLD_DRAW) && RE4DC_PS2_WORLD_DRAW
            if (!re4dc_ps2_world_before_owned_tr(part)) { okay = false; break; }
#endif
        }
        const bool was_open = window.open;
        const bool reopen = was_open && window.slots + bound > 32767U;  // one_chunk closes and opens it again
        okay = one_chunk_core(*part, window, se, &src) == 1;
        if (window.open && (!was_open || reopen)) {
            base = 0;
            if (re4dc_leon_direct_capture(part, &header[material])) {
                scale[material][0] = window.direct.u_scale;
                scale[material][1] = window.direct.v_scale;
            }
        }
        Re4dcActorStreamState after{};
        okay = okay && re4dc_actor_stream_state(&after) && after.frame == before.frame && after.invalid == before.invalid &&
               after.resource == before.resource && after.overflow == before.overflow;
    }
    one_close(window);
    owned_submission = false;
    Re4dcActorStreamState closed{};
    if (!okay || !re4dc_actor_stream_state(&closed) || closed.frame != before.frame || closed.invalid != before.invalid ||
        closed.resource != before.resource || closed.overflow != before.overflow ||
        !re4dc_actor_workspace_validate(workspace_lease) || !re4dc_actor_skin_validate(skin_lease) ||
        !owned_all_textures(textures, nm)) {
        re4dc_model_packet_abort();
        return -1;
    }
    return 1;
}
