#pragma once
// D367 native actor path for the recovered game's non-scenery ModelData parts
// (Leon, enemies, weapons, room SMD objects). The source game stays
// authoritative: it selects, animates, orders and lights every draw. Only the
// render representation changes.
//
// NATIVE_ACTOR=1 (native_actor.cpp): dense per-info tables, GX list walked per
// corner. NATIVE_ACTOR=1 NATIVE_ACTOR_FAST=1 (native_actor_fast.cpp): each
// part's GX display list is converted once, in place, into <=128-vertex
// meshlets (unique corner tuples + u8 strip indices); per frame every meshlet
// vertex is transformed/lit once into a small cache and strips are copied.
// NATIVE_ACTOR_SKIN=1 additionally lets the source skip its render-only
// CalcSk1_x pass: the palette is kept and skinning happens at draw time.
#include "native_model.h"

struct Re4dcActorStats {
    unsigned parts, handled, declined, deferred, culled_infos, culled_parts;
    unsigned info_preparations, position_transforms, light_sets, normals_lit;
    unsigned corners, runs, fallback_runs, fallback_triangles, flushes;
    unsigned workspace_misses, attenuated_lights, near_vertices;
    // NATIVE_ACTOR_FAST
    unsigned conversions, conversion_rejects, meshlets, meshlets_culled, meshlets_clipped;
    unsigned vertices, slow_light_vertices, skinned_parts, materialized_infos, skin_registered;
    unsigned transient_conversions, strips_culled, meshlets_whole;
    unsigned lod_parts, lod_rebuilds, lod_draws[4], triangles, bake_hits, bake_scaled, bake_builds, uv16_parts;
    unsigned skin_dir_sets;
    // NATIVE_ACTOR_CROWD: crowd models seen / parts and triangles drawn per
    // tier (0 full: not a crowd class, 1 near, 2 mid, 3 far).
    unsigned crowd_models, crowd_parts[4], crowd_triangles[4];
};

// Where the source keeps an info's unskinned arrays (model_bridge.cpp fills
// it from ModelData; platform code stays free of source struct layouts).
struct Re4dcActorSource {
    const unsigned char* positions;  // vtxOrig: s16 x,y,z + s16 palette index
    const unsigned char* normals;    // nrmOrig: s8 x,y,z,u8 index / s16 x,y,z,s16 index
    unsigned position_count, normal_count, palette_entries, small_normals;
};

extern "C" {
// Bind this source frame's scratch. The recommended owner is the tail of the
// source primitive buffer (GetPrimBuff during Render(), released by the next
// SetPrimBuffPtr), so no memory stays resident. nullptr/0 disables the path.
void re4dc_actor_frame(void* workspace, unsigned bytes);
// 1: consumed (drawn, culled, or queued for the existing translucent drain).
// 0: declined before any side effect; the caller runs the generic path.
int re4dc_actor_submit(const Re4dcModelPart* p);
// Native fast actor format, including a blob with deferred LOD work.
// Once converted in place, a stream cannot be consumed by a cached GX plan.
int re4dc_actor_stream_encoded(const unsigned char* stream,unsigned bytes);
const Re4dcActorStats* re4dc_actor_stats();
// NATIVE_ACTOR_FAST: LOD selection threshold in pixels of projected error
// (0: always full detail; default RE4DC_ACTOR_LOD_PX = 2) and the per-frame
// LOD build budget in triangles (0: never build; default
// RE4DC_ACTOR_LOD_BUDGET = 128; parts over budget are rebuilt later).
void re4dc_actor_lod(float pixels, unsigned budget_triangles);
// NATIVE_ACTOR_FAST: workspace bytes this frame should get when the source
// primitive buffer has them (a deferred LOD build is waiting), else 0.
unsigned re4dc_actor_workspace_want();
// Bytes needed for one info: 12 per source position + 4 per source normal.
inline unsigned re4dc_actor_workspace_bytes(unsigned positions, unsigned normals) {
    return positions * 12U + normals * 4U;
}

// ---- NATIVE_ACTOR_FAST ------------------------------------------------------
// model_bridge.cpp: the unskinned arrays of a cModelInfo. 0 when unknown.
int re4dc_actor_model_source(const void* info, Re4dcActorSource* out);
// model_bridge.cpp: 1 when the model is currently neither animated (no
// motion playing) nor morphed (no shape table / shape flag): its opaque parts
// are converted with a baked-colour field (static prelit). Only a hint; the
// draw re-validates the light fold and pose every frame.
int re4dc_actor_model_prelit(const void* model, const void* info);
// model_bridge.cpp (NATIVE_ACTOR_CROWD): 1 for a Ganado-family enemy's info,
// 2 for its head info, 0 for everything else (Leon, weapons, objects).
int re4dc_actor_model_class(const void* model, const void* info);
// NATIVE_ACTOR_CROWD tuning: near count and distances (view space, source
// units), mid-tier LOD threshold in pixels.
void re4dc_actor_crowd(unsigned near_count, float near_distance, float mid_distance, float mid_pixels);

// native_ui.cpp (NATIVE_ACTOR_UV16): PCW bits the next re4dc_model_packet_begin
// sets/clears in its slab copy of the polygon header (16-bit UV, strip
// length); that call consumes them whatever its result.
void re4dc_model_next_header_pcw(unsigned set, unsigned clear);

// ---- NATIVE_ACTOR_SKIN ------------------------------------------------------
// Trans() side (trans.cpp commonScreenMatSub): after the source built this
// info's weight palette (MakeWeightPalette, unchanged), a copy of it lives in
// the frame's primitive buffer. Registering it lets the source skip the
// render-only CalcSk1_x writes into pPosBuf/pNrmBuf for this frame. 1 = the
// caller may skip. `frame` is pG->Frame_cnt (constant from Trans to Render).
int re4dc_actor_skin_register(unsigned frame, const void* info, const void* position_buffer,
                              const float* palette, unsigned entries);
#if defined(RE4DC_SKIN_ADMISSION32) && RE4DC_SKIN_ADMISSION32
// One non-yielding source palette allocation at a time. A provisional ticket
// claims capacity without replacing a prior lazy/owner entry or advancing the
// primitive buffer. Cancel only this ticket after an allocation refusal.
struct Re4dcActorSkinAdmission {
    unsigned serial, frame, slot, entries;
    const void* info;
    const void* positions;
    unsigned provisional;
};
int re4dc_actor_skin_admit(unsigned frame, const void* info, const void* position_buffer,
                           unsigned entries, Re4dcActorSkinAdmission* out);
int re4dc_actor_skin_commit(Re4dcActorSkinAdmission* ticket, const float* palette);
void re4dc_actor_skin_cancel(Re4dcActorSkinAdmission* ticket);
#endif
// Registered palette for (info, pPosBuf) or nullptr.
const float* re4dc_actor_skin_palette(const void* info, const void* position_buffer, unsigned* entries);
// trans.cpp: run the source's own CalcSk1_x/_x2 for a registered info into
// its pPosBuf/pNrmBuf from the saved palette (generic-path fallback).
int re4dc_skin_materialize(const void* info, const float* palette);
// native_model.cpp: before the generic path reads pPosBuf, make it valid.
void re4dc_actor_materialize(const Re4dcModelPart* p);
// NATIVE_ACTOR_SKIN_LAZY: a part of an info registered without arrays
// (positions NULL): allocate and skin them, set p->positions/normals; 0 if
// that is impossible (the generic path then rejects the part).
int re4dc_actor_materialize_lazy(Re4dcModelPart* p);
// model_bridge.cpp: p->positions/normals from the info current pPosBuf/pNrmBuf.
int re4dc_actor_model_buffers(Re4dcModelPart* p);
// ACTOR_REPLAY_SKIN: re-register a materialized lazy palette for the part's arrays (native_actor_fast.cpp).
int re4dc_actor_skin_rearm(Re4dcModelPart* p);
}

// COARSE_ONE_SUBMIT (game30.mk; render only; native_actor_fast.cpp): the coarse adapters' chunks of one actor in
// one call. *p carries what the chunks share (model, texture and header inputs, lighting, projection, viewport);
// each chunk's info (also the part), stream, uv, counts and modelview are written into *p in turn. Each chunk is
// handled as re4dc_actor_submit(p) would handle it and bit i of the result is set when that call would have
// returned 1; the chunks share one TA header (one direct TA window). n <= 32.
struct Re4dcActorChunk {
    const void* info; const unsigned char* stream; const unsigned char* uv; const float* modelview;
    unsigned stream_bytes, position_count, normal_count;
#if RE4DC_ACTOR_SOURCE_SPAN
    Re4dcActorSourceSpan source_span{};
#endif
};
extern "C" unsigned re4dc_actor_submit_chunks(Re4dcModelPart* p, const Re4dcActorChunk* chunks, unsigned n);

#if defined(RE4DC_ACTOR_TEST)
// Host test access to the prepared tables of the last prepared info.
struct Re4dcActorScreen { float x, y, w_inverse; };
extern "C" const Re4dcActorScreen* re4dc_actor_test_screen();
extern "C" const unsigned* re4dc_actor_test_shade();
#endif
