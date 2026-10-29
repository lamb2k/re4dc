#pragma once
#include <cstdint>
#include "actor_source_span.h"
#include "native_ui.h"
#include "../../../room/source_lighting.hpp"
// View of a qualified source ModelData part. The source already selected and
// skinned the model. Candidate nonopaque views are borrowed only until the
// source Render completion barrier, before its primitive buffer can be reused.
struct Re4dcModelPart {
    const void* model; const void* info; const void* part;
    const unsigned char* positions; const unsigned char* normals;
    const unsigned char* uv; const unsigned char* stream;
    unsigned position_count, normal_count, position_stride, stream_bytes;
    unsigned shift, flags, cull, blend, depth_mode, material_flags;
    float modelview[12], projection[7], viewport[6];
    Re4dcUiImage image;
    // Channel zero alpha: low byte material, bit 8 vertex source; other bits reject.
    // Candidate RGB is captured from the source-selected lighting channel.
    const unsigned char* colors=nullptr; unsigned alpha_state=255;
    float uv_offset[2]; unsigned wrap_s,wrap_t;
    unsigned normal_stride=0, normal_shift=0, static_geometry=0;
    const re4dc::render::SourceLighting* lighting=nullptr;
    Re4dcUiImage mask{};unsigned mask_ref=256,mask_same_uv=0;
    // Native static package binding (native_static.h): the owning object's
    // creation serial, current world matrix and the source camera, borrowed
    // like the arrays above; the part's (texId, alphaTex or 0xff) key.
    unsigned serial=0; const float* world=nullptr; const float* view=nullptr;
    unsigned char source_key[4]={0,0xff,0,0};
#if RE4DC_ACTOR_SOURCE_SPAN
    Re4dcActorSourceSpan source_span{};
#endif
};
extern "C" {
int re4dc_model_diagnostic_enabled();
unsigned re4dc_gx_model_alpha();
void re4dc_model_submit(const Re4dcModelPart*);
// Source-only bridge entry points; opaque types keep SDK/KOS headers separate.
void re4dc_model_material(const void* texture_object,float u,float v,unsigned flags);
void re4dc_model_alpha_material(const void* texture_object,unsigned ref,unsigned same_uv);
void re4dc_draw_model_part(const void* model,const void* info,const void* part,
                          const float modelview[3][4],unsigned pass);
}
#if defined(RE4DC_G1_DIAG_INLINE) && RE4DC_G1_DIAG_INLINE
// G1_DIAG_INLINE (g1parts.mk; exact): the per-part callers read the latched flag inline; the first call (-1) still
// opens /cd/dc/model-diagnostic.flag through re4dc_model_diagnostic_enabled(), which sets the latch.
extern "C" int re4dc_model_diag_latch;
static inline int re4dc_model_diag(){const int s=re4dc_model_diag_latch;return s>=0?s:re4dc_model_diagnostic_enabled();}
#define RE4DC_MODEL_DIAG() re4dc_model_diag()
#else
#define RE4DC_MODEL_DIAG() re4dc_model_diagnostic_enabled()
#endif

// Adapter/owner interface. Returned storage belongs to the one native frame,
// reserves header space, and is committed only after a complete part succeeds.
// reserve() performs no texture I/O. begin() binds the validated native texture
// after geometry fits; differing native UV scales require preparation again.
// Default mode rolls back a failed complete part. Streaming mode can reuse this
// scratch after committing chunks; a later failure must abort the whole frame.
// Packet storage contains native values; deferred source views have a separate
// bounded lifetime ending at finish_source_draws().
struct Re4dcModelPacket { void* vertices; unsigned capacity; float u_scale,v_scale; };
extern "C" int re4dc_model_packet_reserve(const Re4dcModelPart*,Re4dcModelPacket*);
extern "C" int re4dc_model_packet_begin(const Re4dcModelPart*,Re4dcModelPacket*);
extern "C" void re4dc_model_packet_commit(unsigned vertices);
extern "C" void re4dc_model_result(unsigned reason,unsigned input_triangles,unsigned output_triangles);

extern "C" int re4dc_model_packet_streaming();
extern "C" void re4dc_model_packet_abort();

// Direct TA submission (frame owner knob TA_DIRECT=1; ta_direct.hpp helpers).
// After re4dc_model_packet_reserve() qualified the part, direct_begin() does
// packet_begin()'s texture bind, pass/list selection (translucent deferral is
// unchanged: deferred parts never reach an emitter before the drain) and
// header build, sends the header straight into the TA and returns with the
// TA store queues locked. The emitter then writes FINAL vertices to 'sq'
// (32 bytes per slot, pref after each; nothing can be rolled back, so only
// qualified strips/clipped output go out) and calls direct_end() with the
// number of vertex slots written. 'scratch' is the part's private packet
// slab range (never sent), e.g. for the transform-once meshlet cache. Between
// begin and end: no texture/file I/O, no yielding, no other TA submission,
// at most 32768 slots (1 MiB store-queue window). A failure after begin
// behaves like a streamed packet failure: re4dc_model_packet_abort() then
// direct_end(). Returns 0 (nothing sent) when disabled or not eligible; the
// caller keeps its packet path.
struct Re4dcModelDirect { std::uint32_t* sq; void* scratch; unsigned scratch_capacity; float u_scale,v_scale; };
extern "C" int re4dc_model_direct_enabled();
// D367 TA_HASH=1 (test builds, tahash.mk): every 32-byte TA store-queue burst of the game
// frame is folded into a per-list hash, logged once per scene ("ta_hash:"). 0 = compiled out.
#ifndef RE4DC_TA_HASH
#define RE4DC_TA_HASH 0
#endif
#if RE4DC_TA_HASH
extern "C" void re4dc_ta_hash(const void* data,unsigned bytes);
#endif
extern "C" int re4dc_model_direct_begin(const Re4dcModelPart*,Re4dcModelDirect*);
extern "C" void re4dc_model_direct_end(unsigned vertices);

// Source cModel 0/1 selects GX_CULL_FRONT/BACK, not the viewer helper's
// screen-area values. GXSetCullMode swaps the two hardware bits; with GX's
// negative viewport Y scale, FRONT rejects positive screen area, BACK negative.
// Preserve the shared helper/accepted viewer convention at this adapter boundary.
inline unsigned re4dc_model_cull(unsigned source_mode,bool force_front){
    return force_front?2U:(source_mode==0?2U:source_mode==1?1U:0U);
}

// Cumulative preparation work; distinct from PVR/internal TA capacity counters.
// Native cache costs 2 KiB of the existing calling stack, no resident allocation.
struct Re4dcModelWorkStats {
    unsigned part_preparations, position_references, position_transforms, position_hits;
    unsigned room_prepared_strips, room_prepared_corners, room_strip_fallbacks;
    unsigned gx_walk_bytes, prepared_parts, unprepared_parts;
    unsigned normal_transforms,light_evaluations,light_hits,lighting_rejects;
    unsigned clipped_triangles,culled_triangles,culled_groups,culled_primitives;
    unsigned static_light_hits,static_light_misses,static_light_invalidations;
    unsigned local_position_references,general_position_references;
    // Matched frame deltas: weight matrices, palette, morph, positions, normals,
    // the two post-skin flushes. Separate from native submission/overlapped GPU.
    unsigned source_prepare_us[6],pose_writeback_bytes_skipped;
};
extern "C" const Re4dcModelWorkStats* re4dc_model_work_stats();

namespace re4dc::render { struct NativeDrawPlan; struct DrawPlanBounds; struct DrawLocalPlan; }
// Qualified archive ranges come from the existing UI/resource owner. A plan
// contains command spans only; its owner retains the live display-list backing.
extern "C" void re4dc_model_bind_draw_owner(const void* owner,void* archive,unsigned bytes,unsigned transient);
extern "C" void re4dc_model_unbind_draw_owner(const void* owner);
extern "C" void re4dc_model_reset_draw_plans();
extern "C" const re4dc::render::NativeDrawPlan* re4dc_model_acquire_draw_plan(const Re4dcModelPart*,int* invalid);
extern "C" const re4dc::render::DrawPlanBounds* re4dc_model_acquired_bounds();
extern "C" const re4dc::render::DrawLocalPlan* re4dc_model_acquired_locals();
extern "C" void re4dc_model_release_draw_plan();
extern "C" void re4dc_model_draw_plan_frame(unsigned frame);
struct Re4dcDrawPlanStats {
    unsigned hits,installs,source_bytes,uncovered,capacity_rejects,invalid,
             used,capacity,peak,resets,owner_misses;
};
extern "C" const Re4dcDrawPlanStats* re4dc_model_draw_plan_stats();

extern "C" void re4dc_model_retire_draw_plans();
// Partition of the existing native packet slab; never allocated from the game heap.
extern "C" void* re4dc_model_metadata_storage(unsigned* bytes);

extern "C" void re4dc_gx_model_lighting(re4dc::render::SourceLighting*);
// Live GX channel-0 lighting state (BRIDGE_LEAN=1): parts borrow it for the
// synchronous submit; the translucent queue snapshots it as before.
extern "C" const re4dc::render::SourceLighting* re4dc_gx_model_lighting_ref();

// Returns one only when this part has been queued/failed; zero submits now.
// The source Render() sync boundary drains every borrowed pose before reuse.
extern "C" int re4dc_model_defer_part(const Re4dcModelPart*);
extern "C" void re4dc_model_finish_source_draws();

extern "C" void re4dc_model_invalidate_pending();

extern "C" void* re4dc_model_static_lighting_storage(unsigned* bytes);
extern "C" void re4dc_model_invalidate_static_lighting();

// Published only after this source frame's presentation decision. Sequence is
// odd during publication so existing readback tooling can reject torn reads.
struct Re4dcNativeFrameStats {
    volatile unsigned sequence;unsigned frame;
    Re4dcModelWorkStats work;
    unsigned pvr_calls,pvr_bytes,header_hits,header_builds;
    unsigned plan_used,plan_capacity,queue_peak,queue_drops;
    unsigned texture_vram,texture_peak,native_slab,source_heap_free;
    unsigned render_wall_us,present_wait_us,present_requested,aborted;
};
extern "C" const Re4dcNativeFrameStats* re4dc_native_frame_stats();

// Asset adapter: source registrations/owner changes request one bounded update
// before drawing. The source manager remains the only active-model registry.
extern "C" void re4dc_model_assets_changed();
extern "C" int re4dc_model_begin_asset_update();
extern "C" void re4dc_model_finish_asset_update();
extern "C" int re4dc_model_owned_source(const void*,unsigned);
extern "C" int re4dc_model_prepare_draw_plan(const Re4dcModelPart*);
extern "C" void re4dc_prepare_model_assets();

extern "C" unsigned re4dc_model_source_stamp();
extern "C" void re4dc_model_source_span(unsigned stage,unsigned start);
extern "C" void re4dc_model_skipped_writeback(unsigned bytes);

extern "C" void* re4dc_model_deferred_storage(unsigned* bytes);

// One bounded preparation partition in the existing native slab. The frame
// owner invalidates it before any source pose storage may be reused.
struct Re4dcPreparationStats {
    unsigned parts,position_states,position_state_hits,normal_states,normal_state_hits;
    unsigned light_builds,light_build_hits,position_batches,normal_batches,shade_batches;
    unsigned normal_hits,color_packs,packet_flushes;
    unsigned normal_dense_references,shade_dense_references;
};
extern "C" void* re4dc_model_preparation_storage(unsigned* bytes);
// Optional room-owned extension, funded by compact source backing. It retains
// prepared values only; source arrays and the bounded topology remain backing.
// Binding does not allocate. Acquisition happens after source room consumers.
extern "C" void re4dc_model_preparation_owner(void* owner);
extern "C" void* re4dc_model_retained_storage(unsigned* bytes);
extern "C" void re4dc_model_detach_retained_storage();
extern "C" void re4dc_model_preparation_frame();
extern "C" const Re4dcPreparationStats* re4dc_model_preparation_stats();
