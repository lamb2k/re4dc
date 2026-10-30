#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
#include "include/native_draw_result.hpp"
#endif
#if defined(RE4DC_CLOTH_PUBLICATION11) && RE4DC_CLOTH_PUBLICATION11
#include "include/cloth_publication11.inc"
#endif
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
#include "include/static_obj_batch33.hpp"
#endif
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
#include "include/actor_format32_uv.hpp"
#endif
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
#include "include/fallback_audit29.h"
#endif
#line 1
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
#include "include/draw_fallback_audit.h"
#define DFA26_HIT(reason) ::re4dc::dfa26::hit(::re4dc::dfa26::reason);
#define DFA26_FALSE(reason) (::re4dc::dfa26::hit(::re4dc::dfa26::reason), false)
#define DFA26_COUNT(counter,reason) (::re4dc::dfa26::hit(::re4dc::dfa26::reason), ++counter)
#else
#define DFA26_HIT(reason)
#define DFA26_FALSE(reason) false
#define DFA26_COUNT(counter,reason) ++counter
#endif
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
#include "draw_setup_audit.h"
#endif
#include "include/gc_asset_motion_unknown.h"
#include "include/gc_asset_gate.h"
#include "include/gc_asset_packet_cursor.h"
#include "include/gc_asset_members.h"
#include "include/gc_asset_payloads.h"
#include "include/gc_asset_audio.h"
#include "include/gc_asset_movie.h"
#include "include/gc_asset_lifecycle.h"
#include "include/gc_asset_actor.h"
#if defined(RE4DC_PREPARED_BINDING34) && RE4DC_PREPARED_BINDING34
#include "include/model_prepared_binding34.h"
#endif
#if RE4DC_GC_ASSET_GATE
#include "include/native_io.h"
#define RE4DC_GCA_ADOPT(...) ((void)(re4dc_gcasset::ensure_disc_catalog() && re4dc_gcasset::member_adopt(__VA_ARGS__)))
#define RE4DC_GCA_RETIRE(...) re4dc_gcasset::member_retire(__VA_ARGS__)
#else
#define RE4DC_GCA_ADOPT(...) ((void)0)
#define RE4DC_GCA_RETIRE(...) ((void)0)
#endif
#include "../world_scratch.h"
#if defined(RE4DC_FX_R200_ENTRY_CAP) && RE4DC_FX_R200_ENTRY_CAP
#if !RE4DC_NATIVE_STATIC || !RE4DC_EFFECT_SPRITES || !RE4DC_D349_RENDERER_STACK || !RE4DC_PVR_STREAM || !RE4DC_FX_ROOM_SPILL_KB
#error FX_R200_ENTRY_CAP requires native static, effect sprites, the renderer stack, PVR stream and a room spill
#endif
#include "include/fx_r200_entry_cap.h"
extern "C" unsigned re4dc_room_id_now();
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
#include "include/world_census24.h"
namespace {
[[maybe_unused]] int wc24_post_result(int result,bool present){
    if(result==0)re4dc::wc24::decision_posted(present);
    return result;
}
[[maybe_unused]] int wc24_queue_result(int result,bool present){
    if(result)re4dc::wc24::decision_posted(present);
    return result;
}
}
#define WC24_POST_RESULT(result,present) wc24_post_result((result),(present))
#define WC24_QUEUE_RESULT(result,present) wc24_queue_result((result),(present))
#else
#define WC24_POST_RESULT(result,present) result
#define WC24_QUEUE_RESULT(result,present) result
#endif
#if RE4DC_WORLD_SCRATCH
extern "C" unsigned re4dc_ps2_mesh_room();
#endif
#if defined(RE4DC_VRAM_ROOM_ARENA) && RE4DC_VRAM_ROOM_ARENA
extern "C" volatile unsigned re4dc_vram_arena_class;   // vram_pages.cpp (VRAM_ROOM_ARENA)
#endif
#if defined(RE4DC_TEX_ARENA_CURRENT_KEY) && RE4DC_TEX_ARENA_CURRENT_KEY
#if !RE4DC_VRAM_ROOM_ARENA || !RE4DC_VRAM_PAGES || !RE4DC_UI_VRAM
#error TEX_ARENA_CURRENT_KEY requires VRAM_ROOM_ARENA, VRAM_PAGES and UI_VRAM
#endif
#endif
#if defined(RE4DC_TEX_FINAL_REFUSAL_LOG) && RE4DC_TEX_FINAL_REFUSAL_LOG
#if !RE4DC_VRAM_PAGES || !RE4DC_UI_VRAM
#error TEX_FINAL_REFUSAL_LOG requires VRAM_PAGES and UI_VRAM
#endif
extern "C" unsigned re4dc_room_id_now();
extern "C" void re4dc_vram_pages_census(unsigned* out);
#endif
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
extern "C" volatile unsigned re4dc_vram_key_crc,re4dc_vram_key_fnv;   // vram_pages.cpp (WORLD_METER VRAMFAIL lines)
#endif
#if defined(RE4DC_RESIDENT_LIST_CACHE) && RE4DC_RESIDENT_LIST_CACHE
#include "include/resident_list_cache.h"
#endif
#if defined(RE4DC_EM35_DIAG) && RE4DC_EM35_DIAG
#include "include/em35_diag.h"
#endif
#if defined(RE4DC_BACKFACE_CENSUS) && RE4DC_BACKFACE_CENSUS
extern "C" void re4dc_bfc_feed(unsigned list,const void* data,unsigned bytes);
extern "C" void re4dc_bfc_scene(unsigned frame,int present);
#endif
#include "include/movie_world_arena.h"
#include "include/actor_visibility_diag.h"
#if RE4DC_PS2_WORLD_SOURCE_OWNER
#include "include/ps2_source_world.h"
#endif
#ifndef RE4DC_UI_POLY_ORDER
#define RE4DC_UI_POLY_ORDER 0
#endif
#if RE4DC_UI_POLY_ORDER && (!RE4DC_SS_UI_ORDER || !RE4DC_D349_RENDERER_STACK || !RE4DC_PVR_STREAM)
#error UI_POLY_ORDER requires SS_UI_ORDER, D349_RENDERER_STACK and PVR_STREAM
#endif
#include "include/native_cabin.h"
#if RE4DC_PS2_WORLD_SOURCE_OWNER || RE4DC_PS2_WORLD_R11F_OWNER
#include "include/ps2_source_world.h"
#endif
#ifndef RE4DC_PT_BLEND_FIX
#define RE4DC_PT_BLEND_FIX 0
#endif
#if RE4DC_KOS_HEAP_CHECK
extern "C" void re4dc_heap_check(void);
#endif
#if defined(RE4DC_MCHECK_SAFE) && RE4DC_MCHECK_SAFE && defined(RE4DC_LETTERBOX_CLIP) && RE4DC_LETTERBOX_CLIP
extern "C" unsigned re4dc_lbx_rows_last;  // letterbox_clip.cpp (MCHECK_SAFE, mcheck.mk)
#endif
#include <type_traits>
#if defined(RE4DC_MCHECK_PT) && RE4DC_MCHECK_PT
#include "include/ta_pt_audit.h"
#endif
// FX_QUEUE_MARGIN=<bytes> (mendezfx.mk; render only, default 8192 = unchanged; #41 / #55): the frame-queue bytes an
// effect sprite leaves free for the world's translucent parts that come after it (on top of the UI reserve).
#ifndef RE4DC_FX_QUEUE_MARGIN
#define RE4DC_FX_QUEUE_MARGIN 8192U
#endif
#ifndef RE4DC_WORLD_AUTOSORT
#define RE4DC_WORLD_AUTOSORT 0
#endif
#ifndef RE4DC_PS2_WORLD_DRAW
#define RE4DC_PS2_WORLD_DRAW 0
#endif
#ifndef RE4DC_WORLD_RECT21
#define RE4DC_WORLD_RECT21 0
#endif
#if RE4DC_WORLD_RECT21
#if !RE4DC_PS2_WORLD_DRAW || !RE4DC_PS2_WORLD_MESH || !RE4DC_MESH_DIRECT
#error WORLD_RECT21 requires the qualified PS2 world mesh direct consumer
#endif
#include "../../tools/d367/texture_rect21/world_rect_bind.h"
#endif
#if RE4DC_PS2_WORLD_DRAW
#include "re4dc_screen.h"
#include "include/native_ps2_world.h"
#endif
// Narrow ID-quad backend. Reuses the scene Package and owned storage reader.
// Candidate scope: common unmasked UI; unsupported effects are counted/rejected.
#if defined(RE4DC_GAME) && !defined(__PPC__)
#include "actor_lifetime.h"
#endif
#include <kos.h>
#if defined(RE4DC_KOS_WATCH) && RE4DC_KOS_WATCH
extern "C" void re4dc_kos_heap_state(unsigned* free_chunks, unsigned* used, unsigned* break_room);
void re4dc_kos_heap_state_cpp(unsigned* a, unsigned* b, unsigned* c) { re4dc_kos_heap_state(a, b, c); }
#endif
#include <dc/sq.h>
#include <fcntl.h>
#include <cstdio>
#include <cstring>
#include <cmath>
#include <malloc.h>
#include <new>
#if RE4DC_ACTOR_GANADO_DEATH_FADE
// This platform TU has the standard placement-new declaration. The recovered
// source headers use this compatibility guard because their <new> omits it.
#define PLACEMENT_NEW_DEFINED
#include "include/actor_death_fade.h"
#endif
#include <cstddef>
#include <algorithm>
#ifndef RE4DC_ACTOR_TRANSACTION
#define RE4DC_ACTOR_TRANSACTION 0
#endif
#if RE4DC_ACTOR_TRANSACTION
#include "include/actor_resource_lease.h"
#endif
#if RE4DC_ACTOR_TEX_PREP
// This KOS translation unit has the real <new> placement overload above.
#ifndef PLACEMENT_NEW_DEFINED
#define PLACEMENT_NEW_DEFINED
#endif
#include "include/actor_tex_prep.h"
#endif
#include "re4dc_pad_prompts.h"
#include "re4dc_manual_pages.h"
#if RE4DC_PAD_PROMPTS
#include "binocular_art_keys.h"
#endif
#ifndef RE4DC_D349_RENDERER_STACK
#define RE4DC_D349_RENDERER_STACK 0
#endif
// Frame-pipeline knobs (obj/pipeline30.h; all default off = previous image).
#ifndef RE4DC_PVR_FAST_WAKE
#define RE4DC_PVR_FAST_WAKE 0
#endif
#ifndef RE4DC_PVR_PIPELINE
#define RE4DC_PVR_PIPELINE 0   // 1 presenter thread (pinned KOS); 2 KOS async present (patched KOS)
#endif
#ifndef RE4DC_TA_DIRECT
#define RE4DC_TA_DIRECT 0
#endif
#ifndef RE4DC_BRIDGE_LEAN
#define RE4DC_BRIDGE_LEAN 0
#endif
#ifndef RE4DC_TA_GUARD
#define RE4DC_TA_GUARD 0
#endif
#ifndef RE4DC_SCENERY_SUBMIT_BATCH
#define RE4DC_SCENERY_SUBMIT_BATCH 0
#endif
// PVS_BATCH_COMPOSITION_GUARD
#ifndef RE4DC_PS2_PVS_BATCH_COMPOSE
#define RE4DC_PS2_PVS_BATCH_COMPOSE 0
#endif
#if RE4DC_PS2_PVS_BATCH_COMPOSE != 0 && RE4DC_PS2_PVS_BATCH_COMPOSE != 1
#error PS2_PVS_BATCH_COMPOSE must be 0 or 1
#endif
#if RE4DC_PS2_PVS_BATCH_COMPOSE
#if (defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE != 0) || (defined(RE4DC_GC_ASSET_MOTION_UNKNOWN) && RE4DC_GC_ASSET_MOTION_UNKNOWN != 0)
#error PS2_PVS_BATCH_COMPOSE does not yet qualify GC asset diagnostics
#endif
#if RE4DC_PS2_PVS != 1 || RE4DC_SCENERY_SUBMIT_BATCH != 1 || RE4DC_TA_DIRECT != 1 || RE4DC_PS2_WORLD_HDR_CACHE != 1 || RE4DC_PVR_STREAM != 1 || RE4DC_D349_RENDERER_STACK != 1 || RE4DC_PS2_WORLD_SOURCE_OWNER != 1 || RE4DC_PS2_WORLD_SOURCE_TEX_PREP != 1
#error PS2_PVS_BATCH_COMPOSE needs the qualified streaming source/direct path
#endif
#if !defined(RE4DC_PS2_PVS_DEFAULT) || RE4DC_PS2_PVS_DEFAULT != 0
#error PS2_PVS_BATCH_COMPOSE needs explicit PS2_PVS_DEFAULT=0
#endif
#if RE4DC_WORLD_SCRATCH || RE4DC_TA_GUARD || RE4DC_PS2_WORLD_TRANSITION_OWNER || RE4DC_PS2_WORLD_R11F_OWNER || RE4DC_SCENERY_PIECE_STATE || RE4DC_SCENERY_DEDUP || RE4DC_SCENERY_CONE || RE4DC_CPU_BACKFACE || RE4DC_TA_MATERIAL_DIAG || RE4DC_WORLD_HOLE_DIAG || RE4DC_PS2_WORLD_PREFLIGHT_DIAG
#error PS2_PVS_BATCH_COMPOSE has an unqualified owner, scratch or diagnostic path
#endif
#if RE4DC_PS2_INTERIOR_CULL != 0 && RE4DC_PS2_INTERIOR_CULL != 1
#error PS2_PVS_BATCH_COMPOSE does not qualify interior header-check mode
#endif
#endif
// PVS_BATCH_COMPOSITION_GUARD_END
#if RE4DC_SCENERY_SUBMIT_BATCH != 0 && RE4DC_SCENERY_SUBMIT_BATCH != 1
#error SCENERY_SUBMIT_BATCH must be 0 or 1
#endif
#if RE4DC_SCENERY_SUBMIT_BATCH
#if !RE4DC_TA_DIRECT || RE4DC_PS2_WORLD_HDR_CACHE != 1
#error SCENERY_SUBMIT_BATCH needs TA_DIRECT=1 and PS2_WORLD_HDR_CACHE=1
#endif
#if (RE4DC_PS2_PVS && !RE4DC_PS2_PVS_BATCH_COMPOSE) || RE4DC_WORLD_SCRATCH || RE4DC_TA_GUARD
#error SCENERY_SUBMIT_BATCH does not yet qualify PS2_PVS, WORLD_SCRATCH or TA_GUARD
#endif
#include "include/scenery_submit_batch.h"
#endif
#ifndef RE4DC_PERF_HUD
#define RE4DC_PERF_HUD 0
#endif
// D367 frontend30 (obj/frontend30.h; default off = previous image): staging
// without libcall compares/copies or redundant zero-fills, one-pass view
// diffs, indexed texture-key lookups (same keys, same first match).
#ifndef RE4DC_COPY_LEAN
#define RE4DC_COPY_LEAN 0
#endif
// VRAM layout (defaults = the previous image: 1 MiB, one bank used, 16-word bins).
#ifndef RE4DC_TA_VERTBUF_KB
#define RE4DC_TA_VERTBUF_KB 1024
#endif
#ifndef RE4DC_TA_DOUBLEBUF
#define RE4DC_TA_DOUBLEBUF 0
#endif
#ifndef RE4DC_TA_OPB_BINS
#define RE4DC_TA_OPB_BINS 16
#endif
#ifndef RE4DC_TA_OPB_OVERFLOW
#define RE4DC_TA_OPB_OVERFLOW 3
#endif
#ifndef RE4DC_TA_HEADROOM
#define RE4DC_TA_HEADROOM 0
#endif
#ifndef RE4DC_PVR_MID_FENCE
#define RE4DC_PVR_MID_FENCE 0
#endif
#if RE4DC_TA_HEADROOM
static unsigned ta_vertex_bytes=RE4DC_TA_VERTBUF_KB*1024U;   // TA_HEADROOM: the vertex buffer pvr_init got
#define RE4DC_TA_VERTEX_BYTES ta_vertex_bytes
#else
#define RE4DC_TA_VERTEX_BYTES (unsigned(RE4DC_TA_VERTBUF_KB)*1024U)
#endif
// UI_VRAM=1 (default off = previous image): texture cache budget from the
// actual PVR pool after pvr_init() minus RE4DC_UI_VRAM_RESERVE_KB (the pool
// shrinks by 2 MiB per extra MiB of TA_VERTBUF_KB); LRU eviction against the
// real pool, one evict-and-retry on a fragmented pool, and fail-fast (no
// eviction/file I/O) for a texture that cannot fit beside this frame's pins.
#ifndef RE4DC_UI_VRAM
#define RE4DC_UI_VRAM 0
#endif
#ifndef RE4DC_UI_VRAM_RESERVE_KB
#define RE4DC_UI_VRAM_RESERVE_KB 64
#endif
// UI_FRAG_LATCH=1: a load refused for fragmentation is not retried for kFragRetryFrames or until the
// next room preload. Each retry evicted every upload the scene drew last frame, the scene reloaded
// them and the next retry evicted them again: the r101 scope overlay (256x224, 128 KB 16-bit, with
// 928 KB free but no such block) locked the game in that loop (user play, warp-r101-door).
// UI_OVERLAY_SLAB_KB=n: one contiguous n KiB block held from init (beside the glyph atlas, before
// the budget is taken). A load that finds no contiguous block gets it: the slab is freed and the
// upload retried into the hole, before anything is evicted; it is taken back when that entry closes.
#ifndef RE4DC_UI_FRAG_LATCH
#define RE4DC_UI_FRAG_LATCH 0
#endif
#ifndef RE4DC_UI_OVERLAY_SLAB_KB
#define RE4DC_UI_OVERLAY_SLAB_KB 0
#endif
#ifndef RE4DC_UI_FRAG_WINDOW
#define RE4DC_UI_FRAG_WINDOW 0 // Makefile: window release (1) + frame drop (2) for a fragmented upload
#endif
#ifndef RE4DC_TEX_REF_SELFKEY
#define RE4DC_TEX_REF_SELFKEY 0 // Makefile: an unregistered R4NREF record takes its own key
#endif
// UI_HANDLES=1 (default off = previous image): direct texture handles. A
// source image descriptor resolves to its cache entry once; later draws reach
// it by one direct-mapped compare (no source scan, identity lookup, texel
// hash or entry scan). See resolve() below.
#ifndef RE4DC_UI_HANDLES
#define RE4DC_UI_HANDLES 0
#endif
// PS2_UPLOAD_INCARNATION: bind derived PS2 headers to an exact published
// upload, independent of UI_HANDLES. Zero retains the previous ABI/output.
#ifndef RE4DC_PS2_UPLOAD_INCARNATION
#define RE4DC_PS2_UPLOAD_INCARNATION 0
#endif
// UI_HEADERS=1 (default off = previous image): each UI/HUD quad's PVR header
// (texture binding and blend) is compiled once per cache entry and blend mode
// and reused while the entry lives; the per-frame UI path only writes vertices.
#ifndef RE4DC_UI_HEADERS
#define RE4DC_UI_HEADERS 0
#endif
#ifndef RE4DC_UI_DRAW_LEAN
#define RE4DC_UI_DRAW_LEAN 0
#endif
#ifndef RE4DC_NATIVE_MES
#define RE4DC_NATIVE_MES 0 // message glyphs: see re4dc_ui_glyph()
#endif
// TEX_RESIDENT=1 (default off = previous image): no texture load while moving.
// Packages open without the runtime payload CRC (verified at staging); each
// bound room/enemy/player/weapon identity set is preloaded on the first frame
// after the bind (behind the room-entry fade), up to the texture budget minus
// TEX_RESIDENT_RESERVE_KB; the cache holds 128 entries; a package missing from
// the disc is remembered instead of evicting an entry and retrying every frame.
#ifndef RE4DC_TEX_KEEP
#define RE4DC_TEX_KEEP 0
#endif
#ifndef RE4DC_TEX_RESIDENT
#define RE4DC_TEX_RESIDENT 0
#endif
#ifndef RE4DC_TEX_RESIDENT_RESERVE_KB
#define RE4DC_TEX_RESIDENT_RESERVE_KB 256
#endif
#ifndef RE4DC_TEX_RESIDENT_RESERVE_SLOTS
#define RE4DC_TEX_RESIDENT_RESERVE_SLOTS 32 // entries the room-entry preload leaves for first-sight loads
#endif
#ifndef RE4DC_TEX_SLOTS
#define RE4DC_TEX_SLOTS 192 // TEX_RESIDENT cache entries: r101 pins 95 per frame; the r100 room table has ~146
#endif
#if (RE4DC_PVR_PIPELINE || RE4DC_TA_DIRECT) && !RE4DC_PVR_STREAM
#error PVR_PIPELINE and TA_DIRECT extend the PVR_STREAM=1 frame owner
#endif
#if RE4DC_PVR_FAST_WAKE || RE4DC_PVR_PIPELINE || RE4DC_TA_GUARD
#include <dc/asic.h>
#include <dc/vblank.h>
#include <kos/genwait.h>
#include <kos/sem.h>
#endif
#if (defined(RE4DC_PACE_STEADY) && RE4DC_PACE_STEADY) || (defined(RE4DC_PACE_HOLD_LOG) && RE4DC_PACE_HOLD_LOG)
// pace.mk PACE_STEADY / PACE_HOLD_LOG (pace_present.cpp): a present decision may wait for its target field; it counts
// as pending for every fence below.
#if RE4DC_PVR_PIPELINE != 2
#error PACE_STEADY and PACE_HOLD_LOG defer the KOS async present: need PVR_PIPELINE=2
#endif
#define RE4DC_PACE_PRESENT 1
extern "C" int re4dc_steady_present(int present);
extern "C" void re4dc_present_posted(int present);
extern "C" void re4dc_steady_wait(void);
extern "C" int re4dc_steady_pending(void);
extern "C" void re4dc_steady_ta_wait(void);
#define pvr_present_pending() (pvr_present_pending() || re4dc_steady_pending())
#else
#define RE4DC_PACE_PRESENT 0
#endif
#if RE4DC_PVR_LATCH || RE4DC_PVR_READY_STRICT
#if RE4DC_PVR_PIPELINE != 2 || !RE4DC_PVR_STREAM
#error PVR_LATCH and PVR_READY_STRICT read the KOS async-present state: need PVR_PIPELINE=2 and PVR_STREAM=1
#endif
#include <dc/asic.h>
#include <dc/vblank.h>
extern "C" {
#include "pvr_internal.h"   // KOS pvr_state (Makefile: -I$(KOS_BASE)/kernel/arch/dreamcast/hardware/pvr)
}
#endif
#if RE4DC_TA_MATERIAL_DIAG
#if !RE4DC_PVR_STREAM || !RE4DC_TA_BIN_DIAG || RE4DC_TA_HASH!=1
#error TA_MATERIAL_DIAG needs PVR_STREAM=1 TA_BIN_DIAG=1 TA_HASH=1
#endif
#include "ta_material_diag.h"
#endif
#include "native_ui.h"
#if defined(RE4DC_PVR_RTT) && RE4DC_PVR_RTT
extern "C" void re4dc_rtt_render_pending();   // pvr_rtt.inc (pvr_rtt.mk)
extern "C" void* re4dc_rtt_override_texture(unsigned* w,unsigned* h);
#endif
#include "hud_source_mask.h"
#include "native_model.h"
#if RE4DC_NATIVE_FE_CONTINUATION
#include "native_actor_continuation.h"
#if !RE4DC_COPY_LEAN || !RE4DC_D349_RENDERER_STACK || !RE4DC_PVR_STREAM
#error NATIVE_FE_CONTINUATION requires the existing copied deferred-view streaming owner
#endif
#endif
#include "native_static.h"
#include "native_render_profile.hpp"
#include "pc_sampler.h"
#include "re4dc_platform.h"
#include "../../room/texture_package.hpp"
#include "../../room/room_storage.hpp"
#include "../../room/gpu_lifecycle.hpp"
#include "../../room/pvr_geometry.hpp"
#if defined(RE4DC_SHADOW_BLOB) && RE4DC_SHADOW_BLOB
#if !RE4DC_PVR_STREAM || !RE4DC_TA_DIRECT || !RE4DC_D349_RENDERER_STACK || !RE4DC_WORLD_AUTOSORT || !RE4DC_PS2_WORLD_DRAW
#error SHADOW_BLOB needs PVR_STREAM=1, TA_DIRECT=1, D349_RENDERER_STACK=1, WORLD_AUTOSORT=1 and PS2_WORLD_DRAW=1
#endif
#endif
#if RE4DC_MV_SHADOWS
#if !RE4DC_PVR_STREAM || !RE4DC_TA_DIRECT || !RE4DC_D349_RENDERER_STACK || !RE4DC_TA_HEADROOM
#error MV_SHADOWS needs PVR_STREAM=1, TA_DIRECT=1, D349_RENDERER_STACK=1 (stream_select) and TA_HEADROOM>=1
#endif
extern "C" unsigned re4dc_mv_receiver;  // native_static.cpp MeshDraw::bind: the part being bound is a shadow receiver
static unsigned mv_receivers;           // receiver headers this run (MV_SHADOWS stats)
#endif
#if RE4DC_COARSE_WORLD & 64
extern "C" int re4dc_coarse_world_room(void);                        // coarse.cpp: the world data's room (R3)
extern "C" int re4dc_coarse_world_tex(unsigned i,unsigned out[5]);   // coarse_world.cpp: its texture list
#endif

#if RE4DC_COARSE_LEON
extern "C" int re4dc_coarse_actor_texture_key(const Re4dcUiImage*,unsigned*,unsigned*);
#endif
#if RE4DC_PVR_RECOVER
#if !RE4DC_PVR_READY_STRICT
#error PVR_RECOVER runs in the PVR_READY_STRICT wait slices: need PVR_READY_STRICT=1
#endif
extern "C" int re4dc_fixture_read(const char* path,char* buffer,unsigned size);   // os.cpp (dc/crashtest.txt test aid)
#endif
#if defined(RE4DC_LETTERBOX_CLIP) && RE4DC_LETTERBOX_CLIP
extern "C" void re4dc_lbx_open(int list,void (*send)(const void*,unsigned)); // platform/letterbox_clip.cpp
extern "C" void re4dc_lbx_close(void);
#endif
#if defined(RE4DC_MODEL_DROP_LOG) && RE4DC_MODEL_DROP_LOG
extern "C" void re4dc_model_drop_summary();  // MODEL_DROP_LOG, defined above re4dc_model_packet_reserve
#endif
#if RE4DC_TEX_META_EVICT
extern "C" void re4dc_kos_heap_state(unsigned* free_chunks,unsigned* used,unsigned* break_room);   // platform/os.cpp
#endif
namespace {
constexpr unsigned kQuadCount=256, kTextureCount=RE4DC_TEX_RESIDENT?RE4DC_TEX_SLOTS:RE4DC_PVR_STREAM?80:48, kSourceCount=RE4DC_PVR_STREAM?128:256, kVramBudget=4*1024*1024;
#if RE4DC_UI_VRAM
unsigned vram_budget,vram_retries,vram_rejects; // budget: set by re4dc_ui_init() from the actual pool
#if RE4DC_TEX_META_EVICT
unsigned vram_meta_evicts; // TEX_META_EVICT: uploads evicted for KOS heap (refused descriptor prefix or reserve)
constexpr unsigned kKosReserve=8U*1024U;    // KOS heap the texture cache leaves free (pack sector reads, file handles)
unsigned kos_headroom(){unsigned f=0,u=0,b=0;re4dc_kos_heap_state(&f,&u,&b);return f+b;}
#endif
#endif
struct Key { unsigned crc,fnv; bool operator==(const Key& b)const{return crc==b.crc && fnv==b.fnv;} };
#ifndef RE4DC_TEX_PAYLOAD_RETRY
#define RE4DC_TEX_PAYLOAD_RETRY 0
#endif
#if RE4DC_TEX_PAYLOAD_RETRY && (!RE4DC_TEX_PACK || !RE4DC_TEX_RESIDENT)
#error TEX_PAYLOAD_RETRY requires TEX_PACK and TEX_RESIDENT
#endif
#if RE4DC_TEX_PAYLOAD_RETRY
#include "texpack_payload_retry.inc"
#endif
// TEX_PACK (game30.mk; tools/d367/texpack.py): dc/tex.pak index, validation and failure policy.
#if RE4DC_TEX_PACK
#include "texpack_index.inc"
#if RE4DC_TEX_PAYLOAD_RETRY
static_assert(texpack_payload_retry::kMembers==texpack::kMaxCount,"payload retry ordinal cap must match the validated pack cap");
#endif
#endif
struct Entry { re4dc::texture::Package package; Key key{}; unsigned frame=0; bool valid=false;
#if RE4DC_PS2_UPLOAD_INCARNATION
    // Never reset with source tables or room/movie transitions. Exhaustion
    // permanently disables derived-header reuse for this Entry (zero).
    std::uint32_t upload_incarnation=1;
#endif
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::CheckedAsset asset{};
    unsigned asset_consumers=0;
#endif
#if RE4DC_D349_RENDERER_STACK
    pvr_poly_hdr_t model_header{};unsigned model_header_key=~0U;
#endif
#if RE4DC_UI_HEADERS
    pvr_poly_hdr_t ui_header{};unsigned ui_header_key=~0U; // UI quad header for blend ui_header_key
#endif
};
struct Source { Re4dcUiImage image{}; Key key{}; };
// Current source view needs >64 simultaneously pinned native handles. Reuse
// bytes from the optional source-key lookup cache, not the game heap/queue.
// An uncached source descriptor still resolves through its existing owner table.
Entry entries[kTextureCount]; Source sources[kSourceCount]; unsigned nsource;
#if RE4DC_GC_ASSET_GATE
#if defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
struct GcaFpProf {
    static unsigned n,streamed; static unsigned long long us,bytes,bind_us;
    unsigned long long t0=timer_us_gettime64();
    ~GcaFpProf(){
        us+=timer_us_gettime64()-t0;
        if(!(++n&7))re4dc_log("GC-ASSET-PROF fp=%u streamed=%u fp_us=%llu fp_bytes=%llu bind_us=%llu catalog_reads=%u catalog_us=%llu\n",
            n,streamed,us,bytes,bind_us,re4dc_gcasset::prof_disc_reads(),re4dc_gcasset::prof_disc_us());
    }
};
unsigned GcaFpProf::n,GcaFpProf::streamed; unsigned long long GcaFpProf::us,GcaFpProf::bytes,GcaFpProf::bind_us;
#endif
bool gcasset_texture_fingerprint(Entry& entry,const Key& key,const char* path,unsigned offset,unsigned bytes,
                                 const re4dc_gcasset::Digest* streamed=nullptr) {
#if defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
    GcaFpProf prof;if(streamed)++GcaFpProf::streamed;
#endif
    entry.asset={};
    if(!re4dc_gcasset::ensure_disc_catalog())return false;
    // gc-catalog24b: an immutable tex.pak member (key, offset, size) binds to the
    // same token for the whole catalog epoch, so a reload reuses it instead of
    // re-reading and re-hashing the member. Direct-mapped, 64 x 20 B = 1280 B.
    struct FpCache { unsigned crc,fnv,offset,bytes,token; };
    static FpCache fp_cache[64];
    const bool cacheable=bytes!=0;
    FpCache& slot=fp_cache[(key.crc^key.fnv^offset)&63U];
    if(cacheable && slot.token && slot.crc==key.crc && slot.fnv==key.fnv && slot.offset==offset && slot.bytes==bytes &&
       (slot.token>>14)==re4dc_gcasset::catalog_generation()){
        entry.asset.value=slot.token;return true;
    }
    if(streamed){
        char id[24];snprintf(id,sizeof id,"%08x-%08x",key.crc,key.fnv);
        entry.asset=re4dc_gcasset::bind_checked("texture",id,*streamed);
        if(entry.asset.value && cacheable)slot={key.crc,key.fnv,offset,bytes,entry.asset.value};
        return entry.asset.value!=0;
    }
    // Hash through the package's own open handle when it has one (no second
    // open/directory lookup); upload() seeks before each of its reads.
    const file_t own=entry.package.stream_file();
    file_t file=own;
    if(file==FILEHND_INVALID){Re4dcIoScope io;file=fs_open(path,O_RDONLY);}
    if(file==FILEHND_INVALID)return false;
    bool okay=true;
    {Re4dcIoScope io;
        if(!bytes) { const auto length=fs_total(file);okay=length>=0;bytes=okay?unsigned(length):0; }
        if(okay)okay=fs_seek(file,offset,SEEK_SET)==off_t(offset);
    }
    // Read through the shared storage bounce (the same 16 KiB reads upload()
    // uses: one GD command per 16 KiB, no new buffer). Same bytes, same digest.
    re4dc_gcasset::Digest digest{};
    if(okay){
        re4dc_gcasset::DigestStream stream;re4dc_gcasset::digest_begin(stream);
        Re4dcIoScope io;
        okay=re4dc::storage::read_chunks(file,bytes,[](const std::uint8_t* p,std::size_t n,void* ctx){
            re4dc_gcasset::digest_update(*static_cast<re4dc_gcasset::DigestStream*>(ctx),p,unsigned(n));return true;
        },&stream);
        if(okay)digest=re4dc_gcasset::digest_finish(stream);
    }
    if(own==FILEHND_INVALID){Re4dcIoScope io;fs_close(file);}
#if defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
    GcaFpProf::bytes+=bytes;const unsigned long long bind_t0=timer_us_gettime64();
#endif
    if(okay){char id[24];snprintf(id,sizeof id,"%08x-%08x",key.crc,key.fnv);entry.asset=re4dc_gcasset::bind_checked("texture",id,digest);okay=entry.asset.value!=0;}
    if(okay && cacheable)slot={key.crc,key.fnv,offset,bytes,entry.asset.value};
#if defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
    GcaFpProf::bind_us+=timer_us_gettime64()-bind_t0;
#endif
    return okay;
}
// gc-catalog24b: hash the member from the bytes the streamed package already
// reads (open: header + descriptors; upload: payload chunks; gap(): padding and
// tail the upload skips, read here outside read_chunks). One load at a time on
// the main thread; any out-of-order byte falls back to the full re-read above.
struct GcaTexHash {
    const re4dc::texture::Package* package=nullptr;
    unsigned cursor=0;bool bad=false;
    re4dc_gcasset::DigestStream stream;
} gca_tex_hash;
void gca_tex_bytes(void*,const re4dc::texture::Package* package,std::uint32_t offset,const std::uint8_t* data,std::size_t n){
    auto& h=gca_tex_hash;
    if(package!=h.package)return;
    if(!offset){re4dc_gcasset::digest_begin(h.stream);h.cursor=0;h.bad=false;}   // a (re)open restarts the member
    if(h.bad)return;
    if(offset!=h.cursor){h.bad=true;return;}
#if defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
    const unsigned long long hash_t0=timer_us_gettime64();
#endif
    re4dc_gcasset::digest_update(h.stream,data,unsigned(n));h.cursor+=unsigned(n);
#if defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
    GcaFpProf::bytes+=n;GcaFpProf::bind_us+=timer_us_gettime64()-hash_t0;   // streamed: fp_bytes/bind_us = hashed bytes/us
#endif
}
void gca_tex_gap(void*,const re4dc::texture::Package* package,file_t file,std::uint32_t base,std::uint32_t upto){
    auto& h=gca_tex_hash;
    if(package!=h.package || h.bad)return;
    if(upto<h.cursor){h.bad=true;return;}
    if(upto==h.cursor)return;
#if defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
    static unsigned gap_n;static unsigned long long gap_us,gap_total;
    const unsigned long long gap_t0=timer_us_gettime64();gap_total+=upto-h.cursor;
    struct GapDone{unsigned long long t0;~GapDone(){gap_us+=timer_us_gettime64()-t0;
        if(!(++gap_n&15))re4dc_log("GC-ASSET-PROF gaps=%u gap_bytes=%llu gap_us=%llu\n",gap_n,gap_total,gap_us);}} gap_done{gap_t0};
#endif
    Re4dcIoScope io;
    if(file==FILEHND_INVALID || fs_seek(file,off_t(base+h.cursor),SEEK_SET)!=off_t(base+h.cursor) ||
       !re4dc::storage::read_chunks(file,upto-h.cursor,[](const std::uint8_t* p,std::size_t n,void* ctx){
           re4dc_gcasset::digest_update(*static_cast<re4dc_gcasset::DigestStream*>(ctx),p,unsigned(n));return true;
       },&h.stream)){h.bad=true;return;}
    h.cursor=upto;
}
void gca_tex_arm(Entry& entry){
    gca_tex_hash.package=&entry.package;gca_tex_hash.cursor=0;gca_tex_hash.bad=true;   // valid only after an open reports byte 0
    re4dc::texture::upload_observer={gca_tex_bytes,gca_tex_gap,nullptr};
}
void gca_tex_disarm(){re4dc::texture::upload_observer={};gca_tex_hash.package=nullptr;}
// After a successful upload: bind from the streamed digest when the whole member
// [0, bytes) was covered in order; otherwise the full re-read (same digest).
bool gcasset_texture_finish(Entry& entry,const Key& key,const char* path,unsigned offset,unsigned bytes){
    auto& h=gca_tex_hash;
    const bool streamed=h.package==&entry.package && !h.bad && (!bytes || h.cursor==bytes);
    gca_tex_disarm();
    if(!streamed)return gcasset_texture_fingerprint(entry,key,path,offset,bytes);
    const re4dc_gcasset::Digest digest=re4dc_gcasset::digest_finish(h.stream);
    return gcasset_texture_fingerprint(entry,key,path,offset,bytes,&digest);
}
void gcasset_texture_emitted(Entry* entry,re4dc_gcasset::Consumer consumer=re4dc_gcasset::Texture) {
    if(!entry || !entry->valid)return;
    // Some direct world ends retain the SQ lock across parts. Latch only;
    // formatting/hashing/logging happens later, after submission releases it.
    entry->asset_consumers |= (1U<<consumer)|(1U<<re4dc_gcasset::Texture);
}
void gcasset_texture_flush(Entry& entry) {
    const unsigned mask=entry.asset_consumers;entry.asset_consumers=0;
    if(!mask)return;
    for(unsigned i=0;i<re4dc_gcasset::ConsumerCount;++i)if(mask&(1U<<i))
        re4dc_gcasset::emitted_checked(re4dc_gcasset::Consumer(i),entry.asset);
}
using GcAssetPacketState=re4dc_gcasset::PacketCursor;
re4dc_gcasset::Consumer gcasset_packet_consumer=re4dc_gcasset::Texture;
struct GcAssetGeneratedPacket {
    const void* packet;unsigned bytes,address;re4dc_gcasset::Consumer consumer;bool verified,accepted=false;
};
GcAssetGeneratedPacket* gcasset_generated_packet;
struct GcAssetGeneratedScope {
    GcAssetGeneratedPacket* previous;re4dc_gcasset::Consumer old_consumer;
    GcAssetGeneratedScope(GcAssetGeneratedPacket& packet):previous(gcasset_generated_packet),old_consumer(gcasset_packet_consumer){
        if(previous){packet.verified=false;re4dc_gcasset::unresolved(packet.consumer,"nested-generated-packet");}
        gcasset_generated_packet=&packet;gcasset_packet_consumer=packet.consumer;
    }
    ~GcAssetGeneratedScope(){gcasset_generated_packet=previous;gcasset_packet_consumer=old_consumer;}
};
GcAssetPacketState gcasset_packet_states[5];
#if defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
// Probe (diagnostic): first 32 distinct (why, address, caller) per run.
static bool gca_probe_once(const char* why,const void* a,const void* c){
    static const void* seen[24][3];static unsigned n;
    for(unsigned i=0;i<n;++i)if(seen[i][0]==why && seen[i][1]==a && seen[i][2]==c)return false;
    if(n>=24){return false;}
    seen[n][0]=why;seen[n][1]=a;seen[n][2]=c;++n;return true;
}
#define GCA_PROBE(why,a,c,fmt,...) do{if(gca_probe_once(why,a,c))re4dc_log("GC-ASSET-PROBE why=%s addr=%p caller=%p " fmt,why,a,c,##__VA_ARGS__);}while(0)
#else
#define GCA_PROBE(...) do{}while(0)
#endif
const void* gcasset_probe_part;const void* gcasset_probe_caller;const void* gcasset_probe_outer;
extern "C" unsigned re4dc_gcasset_model_identity(const void*,const void*,const void**);
re4dc_gcasset::SourceUse gcasset_model_pending;
__attribute__((noinline)) void gcasset_model_prepare(const Re4dcModelPart* p) {
    gcasset_probe_part=p;gcasset_probe_caller=__builtin_return_address(0);
#if RE4DC_GC_ASSET_MOTION_UNKNOWN
    re4dc_gcasset::motion_prepare();
#endif
    gcasset_model_pending={};const auto& source=re4dc_gcasset::source_use;
    if(source.payload || (p && p->model==source.model && p->info==source.info))gcasset_model_pending=source;
}
void gcasset_model_accept(const void* vertices=nullptr,unsigned count=0) {
#if RE4DC_GC_ASSET_MOTION_UNKNOWN
    re4dc_gcasset::motion_accept_pending(count); // also before quad geometry's early return
#endif
    if(re4dc_gcasset::payload_quads_accept(vertices,count))return;
    const unsigned mask=gcasset_model_pending.mask?gcasset_model_pending.mask:1U<<re4dc_gcasset::SourceGeometry;
    if(gcasset_model_pending.payload)re4dc_gcasset::payload_accept(gcasset_model_pending.payload,gcasset_model_pending.serial,mask);
    else{
#if defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
        if(!gcasset_model_pending.serial){
            const auto* part=static_cast<const Re4dcModelPart*>(gcasset_probe_part);const void* data=nullptr;
            const unsigned identity=part?re4dc_gcasset_model_identity(part->model,part->info,&data):0xffffffffU;
            GCA_PROBE("unbound-model",gcasset_probe_part,gcasset_probe_outer,"model=%p identity=%08x data=%p replay=%08x mask=%x\n",re4dc_gcasset::source_use.model,identity,data,re4dc_gcasset::replay_use.serial,re4dc_gcasset::source_use.mask);
        }
#endif
        re4dc_gcasset::member_accept(gcasset_model_pending.serial,mask);}
}
void gcasset_packet_reset(){for(auto& state:gcasset_packet_states){
    if(state.continuation)re4dc_gcasset::unresolved(re4dc_gcasset::Texture,"incomplete-packet-continuation");
    state={};
}}
void gcasset_packet_emitted(const void* packet,unsigned bytes,unsigned list,re4dc_gcasset::Consumer consumer) {
    if(!bytes)return;
    if(list>=5 || !packet || bytes%32){re4dc_gcasset::unresolved(consumer,"packet-shape");return;}
    // Modifier-volume lists (MV_SHADOWS volumes, re4dc_ui_mv_send) carry no texture: their 0x80000000 triangle words
    // read as polygon headers whose "address" is vertex data (GC-ASSET-PROBE addr=0x0 caller=re4dc_ui_mv_send). Nothing to attribute.
    if(list==PVR_LIST_OP_MOD || list==PVR_LIST_TR_MOD)return;
    auto& state=gcasset_packet_states[list];
    const auto* words=static_cast<const std::uint32_t*>(packet);
    for(unsigned offset=0;offset<bytes;offset+=32) {
        const auto* q=words+offset/4;
        if(!state.feed(q,gcasset_generated_packet!=nullptr))continue;
        unsigned matches=0;
        for(auto& e:entries)if(e.valid && e.package.upload_complete()) {
            const unsigned n=e.package.header().texture_count;
            for(unsigned t=0;t<n;++t)if((unsigned(reinterpret_cast<std::uintptr_t>(e.package.pvr_texture(t)))&0x007fffffU)==state.address) {
                gcasset_texture_emitted(&e,consumer);++matches;break;
            }
        }
        if(matches!=1){
            auto* generated=gcasset_generated_packet;
            if(!matches && generated && generated->verified && generated->packet==packet && generated->bytes==bytes &&
                generated->address==state.address && generated->consumer==consumer)generated->accepted=true;
            else{GCA_PROBE("unmapped-texture",(const void*)(std::uintptr_t)state.address,__builtin_return_address(0),"consumer=%u list=%u gen=%u\n",unsigned(consumer),list,generated?1u:0u);
                re4dc_gcasset::unresolved(consumer,matches?"ambiguous-texture-address":"unmapped-texture-address");}
        }
    }
}
#define RE4DC_GCA_TEXTURE(...) gcasset_texture_emitted(__VA_ARGS__)
#define RE4DC_GCA_PACKET(...) gcasset_packet_emitted(__VA_ARGS__)
#define RE4DC_GCA_MODEL_PREPARE(...) gcasset_model_prepare(__VA_ARGS__)
#define RE4DC_GCA_MODEL_ACCEPT() gcasset_model_accept()
#define RE4DC_GCA_MODEL_PACKET_ACCEPT(vertices,count) gcasset_model_accept(vertices,count)
#define RE4DC_GCA_MODEL_TEXTURE(entry) do { gcasset_texture_emitted(entry);if(gcasset_model_pending.mask&(1U<<re4dc_gcasset::Weapon))gcasset_texture_emitted(entry,re4dc_gcasset::Weapon); } while(0)
#else
#define RE4DC_GCA_TEXTURE(...) ((void)0)
#define RE4DC_GCA_PACKET(...) ((void)0)
#define RE4DC_GCA_MODEL_PREPARE(...) ((void)0)
#define RE4DC_GCA_MODEL_ACCEPT() ((void)0)
#define RE4DC_GCA_MODEL_PACKET_ACCEPT(...) ((void)0)
#define RE4DC_GCA_MODEL_TEXTURE(...) ((void)0)
#endif
#if defined(RE4DC_FX_PS2_PACK) && RE4DC_FX_PS2_PACK
// FX_PS2_PACK=1 (effects30.mk, test 12 fx lane; render only): a package that fx_ps2_pack.py built from the PS2 picture of
// a GameCube effect texture (smaller than the source TPL image) says in its header flags how many of its texels the
// source image's UV 0..1 covers (bit 31 set; width bits 0-10, height bits 11-21). Other packages: the source image size.
#define RE4DC_COVER(pkg) (((pkg).header().flags>>31)!=0U)
#define RE4DC_COVER_W(pkg,iw) (RE4DC_COVER(pkg)?((pkg).header().flags&0x7ffU):(iw))
#define RE4DC_COVER_H(pkg,ih) (RE4DC_COVER(pkg)?(((pkg).header().flags>>11)&0x7ffU):(ih))
#else
#define RE4DC_COVER(pkg) false
#define RE4DC_COVER_W(pkg,iw) (iw)
#define RE4DC_COVER_H(pkg,ih) (ih)
#endif
#if defined(RE4DC_GANADO_ATLAS_DROP) && RE4DC_GANADO_ATLAS_DROP
// GANADO_ATLAS_DROP (game30.mk): a texture whose top mip level was left out at load (kTopDrop) keeps its logical size in
// the descriptor (UV scales and size checks); its TSP size is the uploaded half.
#define RE4DC_TSP_W(t) (((t).flags&re4dc::texture::kTopDrop)?(t).width>>1:(t).width)
#define RE4DC_TSP_H(t) (((t).flags&re4dc::texture::kTopDrop)?(t).height>>1:(t).height)
#else
#define RE4DC_TSP_W(t) ((t).width)
#define RE4DC_TSP_H(t) ((t).height)
#endif
#if defined(RE4DC_FX_TEX_POOL) && RE4DC_FX_TEX_POOL
// FX_TEX_POOL=<KB> (effects30.mk, test 12 fx lane; render only): a resident effect texture pool. An effect sprite's
// texture (re4dc_effect_sprite) is pinned while the pool's bytes stay under the budget, so the room's effect set (the
// r101 pyre fire flipbook) is loaded once and kept out of the UI / world LRU eviction; until the pool is full an effect
// texture may load even while the cache is evicting (the EFFECT_ROOM thrash guard applies once it is full). Pins end
// at room retirement (re4dc_ui_retire_room) or when the entry closes.
bool fx_pool_pin[kTextureCount];unsigned fx_pool_size[kTextureCount],fx_pool_bytes,fx_pool_pins,fx_pool_full;
#define RE4DC_FX_POOL_PINNED(e) fx_pool_pin[unsigned(&(e)-entries)]
#else
#define RE4DC_FX_POOL_PINNED(e) false
#endif
#if defined(RE4DC_PS2_ROOM_PIN) && RE4DC_PS2_ROOM_PIN
// PS2_ROOM_PIN=1 (game30.mk, render only; lane objs 2026-10-15): a large PS2 world texture of a room stays resident for
// the whole visit (no LRU eviction), so it never has to load again late into a fragmented pool. r101: 9fe00ef7-6123f7d5
// (256x256, 128 KB): evicted when out of view and reloaded at frame 1228 into a fragmented pool on the test 11 village
// runs ("PVR texture allocation failed" / frag-latched, TEX_CHECK). Set at each room-entry preload (re4dc_ps2_mesh_room).
extern "C" unsigned re4dc_ps2_mesh_room(); // native_static.cpp: the open PS2 world package's room (0: none)
struct RoomPin { unsigned room; Key key; };
constexpr RoomPin kRoomPins[]={{0x101,{0x9fe00ef7U,0x6123f7d5U}}};
Key room_pin_key{};
#define RE4DC_ROOM_PINNED(e) ((room_pin_key.crc|room_pin_key.fnv) && (e).key==room_pin_key)
#else
#define RE4DC_ROOM_PINNED(e) false
#endif
#if defined(RE4DC_TEX_WRAP_SAFE) && RE4DC_TEX_WRAP_SAFE
// TEX_WRAP_SAFE=1 (game30.mk; render only): a package whose texels are all one colour carries header flags bit 30
// (tools/d367/tex_wrapsafe.py). Sampling it gives that colour whatever the wrap, padding or UV scale, so a wrapping
// part may use it even though the converter padded its image (the r101 window glass, 2x2 padded to 8x8).
#define RE4DC_WRAP_SAFE(pkg) ((((pkg).header().flags>>30)&1U)!=0U)
#else
#define RE4DC_WRAP_SAFE(pkg) false
#endif
#if defined(RE4DC_OVL_WATCH) && RE4DC_OVL_WATCH
extern "C" void re4dc_ovl_watch(const char* where);
#define OVLW(x) re4dc_ovl_watch(x)
#else
#define OVLW(x) ((void)0)
#endif
#if defined(RE4DC_ARENA_RING) && RE4DC_ARENA_RING
extern "C" void re4dc_vram_ring_upload(std::uint32_t crc, std::uint32_t bytes, const void* package);
#endif
#if defined(RE4DC_OVL_GUARD) && RE4DC_OVL_GUARD
extern "C" void re4dc_ovl_guard(const char* where);
#define OVLG(x) re4dc_ovl_guard(x)
#else
#define OVLG(x) ((void)0)
#endif
#if RE4DC_ACTOR_TRANSACTION
re4dc_actor::TextureLeases<kTextureCount> actor_texture_leases;
#define RE4DC_ENTRY_PINNED(e) ((e).frame==frame || actor_texture_leases.pinned(unsigned(&(e)-entries)) || RE4DC_FX_POOL_PINNED(e) || RE4DC_ROOM_PINNED(e))
#else
#define RE4DC_ENTRY_PINNED(e) ((e).frame==frame || RE4DC_FX_POOL_PINNED(e) || RE4DC_ROOM_PINNED(e))
#endif
// EFFECT_SPRITES=1 (effects30.mk; default off = previous image): native effect sprites
// (re4dc_effect_sprite below).
#ifndef RE4DC_EFFECT_SPRITES
#define RE4DC_EFFECT_SPRITES 0
#endif
#if RE4DC_EFFECT_SPRITES
unsigned fx_frame=~0U,fx_count,fx_queued,fx_direct,fx_missing,fx_dropped,fx_capped,fx_culled,fx_peak;
#endif
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
// EFFECT_ROOM thrash guard (render only): an effect sprite never evicts a texture the scene needs. While the
// cache is under pressure (an eviction this frame or the last) an effect sprite draws only from a resident
// texture, and at most kFxNewLoads new effect textures load per frame. Without it a view whose working set
// is over the VRAM budget reloads textures from disc every frame (r101 bell fight, 16-bit effect frames:
// seconds per frame); with it the effects thin out until the cache settles.
constexpr unsigned kFxNewLoads=4;
bool fx_resident_only;unsigned fx_evict_frame=~0U-8,fx_new_loads,fx_resident_skips,load_opens;
#define RE4DC_FX_EVICTED() (fx_evict_frame=frame)
#else
#define RE4DC_FX_EVICTED() ((void)0)
#endif
// MODEL_SLAB_LATCH=1 (scenery30.mk; default off = previous image): a failed native model slab
// allocation is tried once per room (re4dc_ui_retire_room re-arms it), not once per part: each
// retry walked the allocator and logged "Out of memory". The native model path then declines
// quietly, as for any unavailable resource.
#ifndef RE4DC_MODEL_SLAB_LATCH
#define RE4DC_MODEL_SLAB_LATCH 0
#endif
#if RE4DC_MODEL_SLAB_LATCH
bool model_slab_failed=false;
unsigned model_slab_failures=0;
#endif
// TEX_RESIDENT deliberately exceeds this bound: TEX_SLOTS-80 more entries (x sizeof(Entry)).
static_assert(RE4DC_TEX_RESIDENT || sizeof(entries)+sizeof(sources)<=64*sizeof(Entry)+256*sizeof(Source));
// SOB33_STATE_BEGIN
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
re4dc::sob33::Run sob33_run;
re4dc::sob33::Stats sob33_stats;
bool sob33_packet_eligible=false,sob33_direct_candidate=false;
unsigned char sob33_packet_marker=0;
inline void sob33_barrier(re4dc::sob33::Barrier cause){
    sob33_run.barrier();sob33_packet_eligible=false;sob33_direct_candidate=false;
    sob33_packet_marker=0;
    ++sob33_stats.barriers;++sob33_stats.barrier_causes[cause];
}
void sob33_report(unsigned fr){
    // Two cumulative rows fit a capture of at least 300 drawn UI frames.
    if(fr%120)return;
    const auto& s=sob33_stats;
    re4dc_log("SOB33 f=%u first=%u reuse=%u foreign=%u format=%u boundary=%u header=%u direct=%u packet=%u op=%u tr=%u pt=%u single=%u/%u large=%u/%u blended=%u/%u completed=%u incomplete=%u empty=%u barriers=%u saved=%u\n",
        fr,s.decisions[re4dc::sob33::First],s.decisions[re4dc::sob33::Reuse],s.decisions[re4dc::sob33::Foreign],
        s.decisions[re4dc::sob33::Format],s.decisions[re4dc::sob33::Boundary],s.decisions[re4dc::sob33::Header],
        s.direct_reused,s.packet_reused,s.list_reused[0],s.list_reused[2],s.list_reused[4],
        s.category_seen[0],s.category_reused[0],s.category_seen[1],s.category_reused[1],
        s.category_seen[2],s.category_reused[2],
        s.completed,s.incomplete,s.empty,s.barriers,(s.direct_reused+s.packet_reused)*32U);
    // Boundary-call counts (including an already empty receipt), not lost
    // reuse opportunities. Source includes retirement and pending invalidation.
    const auto* b=s.barrier_causes;
    re4dc_log("SOB33B f=%u source=%u deferred=%u frame=%u scene=%u list=%u abort=%u send=%u direct=%u custom=%u empty=%u\n",
        fr,b[re4dc::sob33::SourceReset],b[re4dc::sob33::DeferredReset],b[re4dc::sob33::FrameReset],
        b[re4dc::sob33::SceneBoundary],b[re4dc::sob33::ListBoundary],b[re4dc::sob33::PacketAbort],
        b[re4dc::sob33::StreamSend],b[re4dc::sob33::ForeignDirect],b[re4dc::sob33::CustomPacket],
        b[re4dc::sob33::EmptyPacket]);
}
#endif
// SOB33_STATE_END
#if RE4DC_UI_HANDLES
// One 32-bit clock stamps every event that invalidates a handle: closing an
// entry (entry_closed[]) and every source descriptor boundary (each sources[]
// reset, handle_reset). A handle stamped later than both is still exact.
unsigned entry_closed[kTextureCount]; unsigned handle_clock=1,handle_reset=1,handle_hits,handle_misses,handle_bypass;
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
inline void sources_reset(){sob33_barrier(re4dc::sob33::SourceReset);nsource=0;handle_reset=++handle_clock;}
#else
inline void sources_reset(){nsource=0;handle_reset=++handle_clock;}
#endif
#else
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
inline void sources_reset(){sob33_barrier(re4dc::sob33::SourceReset);nsource=0;}
#else
inline void sources_reset(){nsource=0;}
#endif
#endif
#if RE4DC_TEX_RESIDENT || RE4DC_SUBSCREEN
// (SUBSCREEN: sub screen images without a converted package are drawn every frame.)
Key missing_keys[32]; unsigned nmissing;
#endif
#if RE4DC_UI_VRAM && RE4DC_UI_FRAG_LATCH
constexpr unsigned kFragRetryFrames=120;
Key frag_key{}; unsigned frag_frame,frag_latched;
#if RE4DC_UI_FRAG_RESERVE
// UI_FRAG_RESERVE: the block wanted for frag_key (bytes; taken at the next frame start) and the block held for it.
unsigned frag_want,frag_held_frame,frag_reserves,frag_handoffs,frag_expired;pvr_ptr_t frag_held;
void frag_release(const char* why){
    if(!frag_held)return;
    pvr_mem_free(frag_held);frag_held=nullptr;++frag_expired;
    re4dc_log("native UI: frag reserve dropped (%s) key=%08x-%08x\n",why,frag_key.crc,frag_key.fnv);
}
#endif
#if RE4DC_UI_FRAG_WINDOW
// UI_FRAG_WINDOW (Makefile): windows released for fragmented uploads (ok / none qualified / bytes), frames dropped
// for one (=2) and the uploads that then fitted; the frame of the last drop (one per kFragRetryFrames).
unsigned frag_win_ok,frag_win_none,frag_win_bytes,frag_drops,frag_drop_ok,frag_drop_frame=~0U-1000U;
bool frag_discard; // =2: the open scene closes unrendered (stream_close), the previous picture stays one more frame
// The window may hold only uploads idle for this many frames (movie_window_release reads it while it is set): a
// window of recently drawn uploads reloaded the next frame and failed again (r101 bell fight: 96x96 / 64x64 effect
// textures, ~12,000 window releases and ~13,000 loads in 10,000 frames, vr-bell-v4). The frame discard (=2) runs after
// the LRU retry failed, for uploads of at least kFragDropBytes (the 256 KiB results picture, Leon's 512 KiB body).
constexpr unsigned kFragMinAge=30,kFragDropBytes=128U*1024U;
unsigned frag_min_age;
unsigned movie_window_release(unsigned bytes,bool pinned_ok,unsigned& released_bytes); // MOVIE_WINDOW, below
#endif
#endif
#if RE4DC_UI_VRAM && RE4DC_TEX_RESIDENT && RE4DC_UI_OVERLAY_SLAB_KB
constexpr unsigned kOverlaySlabBytes=RE4DC_UI_OVERLAY_SLAB_KB*1024U;
pvr_ptr_t overlay_slab; const Entry* overlay_owner; unsigned overlay_uses;
#if defined(RE4DC_VRAM_ROOM_ARENA) && RE4DC_VRAM_ROOM_ARENA
void overlay_slab_take(){
    if(overlay_slab || overlay_owner)return;
    re4dc_vram_arena_class=2;   // VRAM_ROOM_ARENA: long-lived, from the top
    overlay_slab=pvr_mem_malloc(kOverlaySlabBytes);
    re4dc_vram_arena_class=0;
}
#else
void overlay_slab_take(){ if(!overlay_slab && !overlay_owner)overlay_slab=pvr_mem_malloc(kOverlaySlabBytes); }
#endif
#endif
#if RE4DC_TEX_RESIDENT
bool preload_pending; unsigned preload_loads,preload_skipped,preload_runs;
#if RE4DC_TEX_PACK
// load() calls that met a pack read error (texpack::kError). A preload pass that met one skipped those picks, since
// texpack spaces its retries over UI frames: the pass runs once more when the pack has settled (preload_after_pack).
unsigned pack_error_skips; bool preload_after_pack;
#endif
// Open VRAM claims (re4dc_ui_vram_claim: route movie texture, sub screen backing):
// the room-entry preload waits while any is open and runs again after the last
// one closes if a claim released uploads.
unsigned vram_claims,claim_released;
#endif
#if defined(RE4DC_CORE_PIN) && RE4DC_CORE_PIN
// CORE_PIN (subscreen.mk): the core keys (dc/resident.bin room 0), collected by preload_resident; load() never evicts
// an entry holding one.
constexpr unsigned kCoreKeys=16;
Key core_keys[kCoreKeys];unsigned core_nkeys;
#if RE4DC_CORE_PIN==2
bool core_room_on; // CORE_PIN=2: pinned only in a room with its own resident list (r101, r103), see preload_resident
inline bool core_pinned(const Entry& e){if(!core_room_on)return false;for(unsigned k=0;k<core_nkeys;++k)if(core_keys[k]==e.key)return true;return false;}
#else
inline bool core_pinned(const Entry& e){for(unsigned k=0;k<core_nkeys;++k)if(core_keys[k]==e.key)return true;return false;}
#endif
#if RE4DC_CORE_PIN==2
// CORE_PIN=2 (t15/int, the test 14 open item): the core keys yield to the fragmented-upload retry of a large picture
// (>= kCoreYieldBytes: the r105 chapter 1-2 results screen, 631x169 / 495x150). With =1 they stayed pinned there, and the
// 512 KiB picture found no contiguous block (texchk FAIL, 63-102 effect sprites refused). Everywhere else (the radio
// call's menu pictures, room loads) they stay pinned as with =1. A yielded HUD key reloads on first sight, as without
// CORE_PIN.
constexpr unsigned kCoreYieldBytes=128U*1024U;
bool core_yield;unsigned core_yields;
#define RE4DC_CORE_PINNED(e) (!core_yield && core_pinned(e))
#else
#define RE4DC_CORE_PINNED(e) core_pinned(e)
#endif
#else
#define RE4DC_CORE_PINNED(e) false
#endif
#if defined(RE4DC_SS_HOLD_RESTORE) && RE4DC_SS_HOLD_RESTORE && RE4DC_TEX_RESIDENT
// SS_HOLD_RESTORE (subscreen.mk): the uploads load() evicts while the sub screen hold is open and that the room drew in
// the kHoldWindow frames before the hold (the HUD, the view behind the call) are remembered; after the last unclaim a
// preload pass restricted to them brings them back before play resumes. Others load on first sight, as before (a full
// room pass after a call reloaded 95 r101 keys, 1.6 s in Flycast, most of them not in view).
constexpr unsigned kHoldWindow=60,kHoldKeys=64;
Key hold_keys[kHoldKeys];unsigned hold_nkeys,hold_frame,hold_dropped;bool hold_restore;
#define RE4DC_HOLD_EVICTED(e) do{if(vram_claims && (e).frame+kHoldWindow>=hold_frame){ \
    if(hold_nkeys<kHoldKeys)hold_keys[hold_nkeys++]=(e).key;else ++hold_dropped;}}while(0)
#else
#define RE4DC_HOLD_EVICTED(e) ((void)0)
#endif
re4dc::texture::SourceIdentityTable room_identities,core_identities,option_identities,player_identities,weapon_identities;unsigned identity_hits;
// Match the recovered loader's four module owners; texture uploads still share
// the existing cache and VRAM budget. These views own no texels or allocations.
struct EnemyIdentity { void* archive=nullptr; re4dc::texture::SourceIdentityTable table; };
EnemyIdentity enemy_identities[4];
// UI grows upward, deferred source draw snapshots downward in the EXISTING
// quad allocation. No full PVR packet copy or additional source heap budget.
alignas(32) unsigned char frame_storage[kQuadCount*sizeof(Re4dcUiQuad)];
Re4dcUiQuad* const quads=reinterpret_cast<Re4dcUiQuad*>(frame_storage);
Entry* handles[kQuadCount]; unsigned nquad,frame,used,peak,staging_peak;
#ifndef RE4DC_SS_UI_ORDER
#define RE4DC_SS_UI_ORDER 0
#endif
#if RE4DC_SS_UI_ORDER
#if !RE4DC_D349_RENDERER_STACK || !RE4DC_PVR_STREAM
#error SS_UI_ORDER requires the existing streamed source renderer
#endif
bool ui_order;unsigned quads_flushed;
extern "C" int re4dc_ss_ui_order(); // actual swapped-area owner, not a UI guess
#if RE4DC_ITEM_UI_ORDER
extern "C" int re4dc_item_ui_order(); // source pickup presentation; no heap swap
#endif
#endif
#if RE4DC_D349_RENDERER_STACK
// Only selected lights and current channel/matrix parameters are snapshotted.
// Identical state is shared within this frame; no unselected eight-light copy
// per part, extra allocation, or persistent source pose representation.
using SourceLighting=re4dc::render::SourceLighting;
using SourceLight=re4dc::render::SourceLight;
constexpr unsigned light_parameters=offsetof(SourceLighting,normal_matrix);
constexpr unsigned light_parameter_bytes=sizeof(SourceLighting)-light_parameters;
struct DeferredLightSet { DeferredLightSet* next;unsigned mask; };
DeferredLightSet* deferred_light_sets=nullptr;
struct DeferredLighting { DeferredLighting* next;const DeferredLightSet* lights; };
// Lossless source-state snapshots in the same bounded queue. Camera/projection,
// common array bindings and material defaults are repeated across parts; retain
// one frame basis and only differing 32-bit words. No geometry/pose is copied,
// no quantization, persistent cache, source-heap cut or extra queue allocation.
constexpr unsigned kViewWords=sizeof(Re4dcModelPart)/sizeof(unsigned);
constexpr unsigned kViewMasks=(kViewWords+31)/32;
static_assert(sizeof(Re4dcModelPart)%sizeof(unsigned)==0);
struct DeferredPart { DeferredPart* next;DeferredLighting* lighting;unsigned changed[kViewMasks];
#if RE4DC_GC_ASSET_GATE
    unsigned asset_serial=0,asset_mask=0;
    re4dc_gcasset::PayloadProof* asset_payload=nullptr;
#endif
};
#if defined(RE4DC_ESP_SETUP_LEAN) && RE4DC_ESP_SETUP_LEAN && RE4DC_EFFECT_SPRITES && \
    !RE4DC_TA_GUARD && !RE4DC_TA_HASH && !RE4DC_TA_BIN_DIAG && !RE4DC_TA_MATERIAL_DIAG
#define RE4DC_ESP_SETUP_BATCH 1
void fx_setup_forget();
#endif
Re4dcModelPart* deferred_basis=nullptr;
#if RE4DC_BRIDGE_LEAN
// Same word-difference encoding. The 4-byte memcpy()s above were libcalls on
// SH4 (strict alignment through char*): D367 T spent 4.4 ms/frame of memcpy/
// memset in view_words plus 1.4 ms in its own loop. Re4dcModelPart is 4-byte
// aligned (pointers/floats/unsigned only), so read it as may_alias words.
typedef unsigned __attribute__((may_alias)) AliasWord;
static_assert(alignof(Re4dcModelPart)>=alignof(unsigned));
unsigned view_words(const Re4dcModelPart& p,const Re4dcModelPart& base,unsigned* masks,unsigned* values){
    const auto* a=reinterpret_cast<const AliasWord*>(&p);
    const auto* b=reinterpret_cast<const AliasWord*>(&base);
    unsigned count=0;
    for(unsigned m=0;m<kViewMasks;++m){
        unsigned bits=0;const unsigned first=m*32,last=std::min(kViewWords,first+32);
        for(unsigned i=first;i<last;++i){
            const unsigned word=a[i];
            if(word!=b[i]){bits|=1U<<(i-first);if(values)values[count]=word;++count;}
        }
        if(masks)masks[m]=bits;
    }
    return count;
}
Re4dcModelPart restore_view(const DeferredPart* node){
    Re4dcModelPart out=*deferred_basis;const auto* values=reinterpret_cast<const unsigned*>(node+1);
    auto* words=reinterpret_cast<AliasWord*>(&out);
    for(unsigned m=0;m<kViewMasks;++m)
        for(unsigned bits=node->changed[m];bits;bits&=bits-1)words[m*32+__builtin_ctz(bits)]=*values++;
    return out;
}
#else
unsigned view_words(const Re4dcModelPart& p,const Re4dcModelPart& base,unsigned* masks,unsigned* values){
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    re4dc::dfa26::hit(re4dc::dfa26::DeferredWordCopy,kViewWords);
#endif
    unsigned count=0;if(masks)std::memset(masks,0,kViewMasks*sizeof(unsigned));
    for(unsigned i=0;i<kViewWords;++i){
        unsigned a,b;std::memcpy(&a,reinterpret_cast<const char*>(&p)+i*4,4);
        std::memcpy(&b,reinterpret_cast<const char*>(&base)+i*4,4);
        if(a!=b){if(masks)masks[i/32]|=1U<<(i%32);if(values)values[count]=a;++count;}
    }
    return count;
}
Re4dcModelPart restore_view(const DeferredPart* node){
    Re4dcModelPart out=*deferred_basis;const auto* values=reinterpret_cast<const unsigned*>(node+1);
    for(unsigned i=0;i<kViewWords;++i)if(node->changed[i/32]&(1U<<(i%32))){
        std::memcpy(reinterpret_cast<char*>(&out)+i*4,values++,4);
    }
    return out;
}
#endif
DeferredLighting* deferred_lights=nullptr;
unsigned selected_mask(const SourceLighting& s){return s.enable?s.mask&255U:0U;}
unsigned deferred_light_bytes(const SourceLighting&){return sizeof(DeferredLighting)+light_parameter_bytes;}
unsigned deferred_set_bytes(const SourceLighting& s){
    return sizeof(DeferredLightSet)+__builtin_popcount(selected_mask(s))*sizeof(SourceLight);
}
#if RE4DC_COPY_LEAN
// Same equality, stores and restores as below, as aligned word loops: the
// memcmp()/memcpy() calls were libcalls (D367 LD: memcmp 1.1 ms/frame from
// these compares). Records are 4-byte aligned and word-sized (static_asserts).
typedef unsigned __attribute__((may_alias)) LightWord;
static_assert(sizeof(SourceLight)%4==0 && light_parameter_bytes%4==0 && light_parameters%4==0);
static_assert(sizeof(DeferredLightSet)%4==0 && sizeof(DeferredLighting)%4==0);
inline bool same_words(const void* a,const void* b,unsigned bytes){
    const auto* x=static_cast<const LightWord*>(a);const auto* y=static_cast<const LightWord*>(b);
    for(unsigned i=0;i<bytes/4;++i)if(x[i]!=y[i])return false;
    return true;
}
inline void copy_words(void* to,const void* from,unsigned bytes){
    auto* x=static_cast<LightWord*>(to);const auto* y=static_cast<const LightWord*>(from);
    for(unsigned i=0;i<bytes/4;++i)x[i]=y[i];
}
bool same_light_set(const DeferredLightSet* stored,const SourceLighting& source){
    if(stored->mask!=selected_mask(source))return false;
    auto* data=reinterpret_cast<const unsigned char*>(stored+1);
    for(unsigned i=0;i<8;++i)if(stored->mask&(1U<<i)){
        if(!same_words(data,&source.lights[i],sizeof(SourceLight)))return false;
        data+=sizeof(SourceLight);
    }
    return true;
}
bool same_lighting(const DeferredLighting* stored,const SourceLighting& source){
    return same_words(stored+1,reinterpret_cast<const unsigned char*>(&source)+light_parameters,light_parameter_bytes)
        && same_light_set(stored->lights,source);
}
void store_light_set(DeferredLightSet* stored,const SourceLighting& source){
    stored->mask=selected_mask(source);
    auto* data=reinterpret_cast<unsigned char*>(stored+1);
    for(unsigned i=0;i<8;++i)if(stored->mask&(1U<<i)){
        copy_words(data,&source.lights[i],sizeof(SourceLight));data+=sizeof(SourceLight);
    }
}
void store_lighting(DeferredLighting* stored,const SourceLighting& source){
    copy_words(stored+1,reinterpret_cast<const unsigned char*>(&source)+light_parameters,light_parameter_bytes);
}
// Into a default-constructed SourceLighting (unselected lights stay zero, as
// restore_lighting()): no second 0.5 KiB zero-fill and whole-struct copy.
void restore_lighting_into(const DeferredLighting* stored,SourceLighting& source){
    copy_words(reinterpret_cast<unsigned char*>(&source)+light_parameters,stored+1,light_parameter_bytes);
    auto* data=reinterpret_cast<const unsigned char*>(stored->lights+1);
    for(unsigned i=0;i<8;++i)if(stored->lights->mask&(1U<<i)){
        copy_words(&source.lights[i],data,sizeof(SourceLight));data+=sizeof(SourceLight);
    }
}
#else
bool same_light_set(const DeferredLightSet* stored,const SourceLighting& source){
    if(stored->mask!=selected_mask(source))return false;
    auto* data=reinterpret_cast<const unsigned char*>(stored+1);
    for(unsigned i=0;i<8;++i)if(stored->mask&(1U<<i)){
        if(std::memcmp(data,&source.lights[i],sizeof(SourceLight)))return false;
        data+=sizeof(SourceLight);
    }
    return true;
}
bool same_lighting(const DeferredLighting* stored,const SourceLighting& source){
    return !std::memcmp(stored+1,reinterpret_cast<const unsigned char*>(&source)+light_parameters,light_parameter_bytes)
        && same_light_set(stored->lights,source);
}
void store_light_set(DeferredLightSet* stored,const SourceLighting& source){
    stored->mask=selected_mask(source);
    auto* data=reinterpret_cast<unsigned char*>(stored+1);
    for(unsigned i=0;i<8;++i)if(stored->mask&(1U<<i)){
        std::memcpy(data,&source.lights[i],sizeof(SourceLight));data+=sizeof(SourceLight);
    }
}
void store_lighting(DeferredLighting* stored,const SourceLighting& source){
    std::memcpy(stored+1,reinterpret_cast<const unsigned char*>(&source)+light_parameters,light_parameter_bytes);
}
SourceLighting restore_lighting(const DeferredLighting* stored){
    SourceLighting source{};
    std::memcpy(reinterpret_cast<unsigned char*>(&source)+light_parameters,stored+1,light_parameter_bytes);
    auto* data=reinterpret_cast<const unsigned char*>(stored->lights+1);
    for(unsigned i=0;i<8;++i)if(stored->lights->mask&(1U<<i)){
        std::memcpy(&source.lights[i],data,sizeof(SourceLight));data+=sizeof(SourceLight);
    }
    return source;
}
#endif
DeferredPart* deferred_first=nullptr;DeferredPart* deferred_last=nullptr;
unsigned deferred_top=sizeof(frame_storage),deferred_peak=0,deferred_count=0,deferred_drops=0;
unsigned char* deferred_spill=nullptr;unsigned deferred_spill_top=0,deferred_spill_capacity=0;
#if defined(RE4DC_FX_R200_ENTRY_CAP) && RE4DC_FX_R200_ENTRY_CAP
// FX_R200_TAIL_STATE_BEGIN (one cursor per existing deferred-queue lifetime).
re4dc::fx_r200::Tail fx_r200_tail;
bool fx_r200_tail_select(unsigned required,unsigned char*& storage,unsigned*& top);
void fx_r200_tail_reset();
// FX_R200_TAIL_STATE_END
#endif
bool draining_parts=false,source_draws_finished=false;
pvr_list_t draining_list=PVR_LIST_TR_POLY;
#if RE4DC_ACTOR_TRANSACTION_DIAG
unsigned avd_queue_epoch;
#endif
#if RE4DC_ACTOR_GANADO_DEATH_FADE
void actor_fade_queue_reset();
#endif
#if defined(RE4DC_CLOTH_PUBLICATION11) && RE4DC_CLOTH_PUBLICATION11
extern bool stream_aborted;
#endif
void reset_deferred(){
#if defined(RE4DC_CLOTH_PUBLICATION11) && RE4DC_CLOTH_PUBLICATION11
    re4dc_cloth_publication11.reset(frame,stream_aborted);
#endif
#if RE4DC_NATIVE_FE_CONTINUATION
    re4dc_actor_native_pose_retire();
#endif
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    sob33_barrier(re4dc::sob33::DeferredReset);
#endif
#if defined(RE4DC_ESP_SETUP_BATCH)
    fx_setup_forget(); // queue addresses can be reused after any reset, even within a frame
#endif
    AVD_EVENT(Reset,nullptr,nullptr,0); // Caller reason intentionally unknown.
#if RE4DC_ACTOR_TRANSACTION_DIAG
    ++avd_queue_epoch;
#endif
#if RE4DC_ACTOR_GANADO_DEATH_FADE
    actor_fade_queue_reset();
#endif
#if defined(RE4DC_FX_R200_ENTRY_CAP) && RE4DC_FX_R200_ENTRY_CAP
    fx_r200_tail_reset();
#endif
    deferred_spill=nullptr;deferred_spill_top=deferred_spill_capacity=0;deferred_light_sets=nullptr;deferred_basis=nullptr;deferred_lights=nullptr;deferred_first=deferred_last=nullptr;deferred_top=sizeof(frame_storage);deferred_count=0;}
pvr_list_t select_model_pass(const Re4dcModelPart* p){
    // Alpha is from source material/vertex channels, not texture file format.
    // The separately masked path is classified after its native binding qualifies.
    if(!source_draws_finished && !(p->material_flags&4) && p->depth_mode==0 &&
       (p->blend==4 || (p->blend==0 && p->alpha_state==255)))return PVR_LIST_OP_POLY;
    return PVR_LIST_TR_POLY;
}
#endif
unsigned dropped,unsupported,missing,drawn,culled,loads,reclaimed; bool ready,frame_ready;
#if RE4DC_PACE_CATCHUP
bool pace_skip_frame;   // re4dc_ui_begin_skip .. next re4dc_ui_begin: nothing may reach the TA
#endif
extern "C" int re4dc_vi_black();
#if RE4DC_ROUTE_MOVIES
// Route cutscenes (native_movie.cpp): one 512x256 UYVY texture owned here, so
// all display submission stays with this frame owner. While a picture exists
// it replaces the UI quads and is presented even when the source holds its
// picture (System_flg 0x400) or requests VI black.
pvr_ptr_t movie_texture; bool movie_picture; unsigned movie_width,movie_height;
#if RE4DC_GC_ASSET_GATE
struct GcAssetMovieProof {
    const void* texture=nullptr;unsigned width=0,height=0,owner=0,upload=0,uploading=0;re4dc_gcasset::CheckedAsset asset{};
    bool pending=false;unsigned pending_uses=0;   // token bound at the movie's natural end
} gcasset_movie;
unsigned gcasset_movie_serial;
void gcasset_movie_forget(){gcasset_movie={};}
#endif
bool movie_background;  // re4dc_ui_movie_background: the frame draws the picture behind its UI
unsigned movie_upload_serial,movie_shown_serial,movie_presentations;
#if RE4DC_CABIN_SOURCE
// CABIN_UI_STATE_BEGIN
unsigned movie_cabin_ui_epoch;
bool movie_cabin_ui_busy;
#if RE4DC_CABIN_COMPLETE_HANDOFF
// A fatal scene-close diagnostic must not become a successful close if it
// returns. Epochs never repeat; the fault belongs only to this texture owner.
unsigned movie_cabin_ui_close_fault;
#endif
// Reserve the owner across the existing allocation/free/claim paths, which can
// yield. Interrupts are masked only for this flag, never for a fence or free.
struct MovieCabinUiScope {
    bool held;
    MovieCabinUiScope(){unsigned old=irq_disable();held=!movie_cabin_ui_busy;
        if(held)movie_cabin_ui_busy=true;irq_restore(old);}
    ~MovieCabinUiScope(){if(held){unsigned old=irq_disable();movie_cabin_ui_busy=false;irq_restore(old);}}
};
// CABIN_UI_STATE_END
#endif
uint64_t movie_first_picture_us;
void movie_draw();
#endif
// Diagnostic only: 64 KiB of copied native packets, allocated on first model.
// Roll back an entire part on overflow. No deferred source/primitive pointers.
#if defined(RE4DC_FRAME_QUEUE_SPILL_KB) && RE4DC_FRAME_QUEUE_SPILL_KB
// FRAME_QUEUE_SPILL_KB=<n> (Makefile; render only; lane fix18 #39): the frame queue's deferred spill is <n> KiB instead
// of 8 KiB; the model slab grows by the difference (packet / preparation / metadata areas unchanged).
static_assert(RE4DC_FRAME_QUEUE_SPILL_KB>=8,"FRAME_QUEUE_SPILL_KB is at least the 8 KiB it replaces");
constexpr unsigned kModelSlabBytes=64*1024+(RE4DC_FRAME_QUEUE_SPILL_KB-8)*1024;
constexpr unsigned kModelDeferredSpillBytes=RE4DC_D349_RENDERER_STACK?RE4DC_FRAME_QUEUE_SPILL_KB*1024:0;
#else
constexpr unsigned kModelSlabBytes=64*1024;
constexpr unsigned kModelDeferredSpillBytes=RE4DC_D349_RENDERER_STACK?8192:0;
#endif
constexpr unsigned kModelMetadataBytes=RE4DC_MODEL_DRAW_PLANS?32*1024:0;
// Whole-stack bisection: two static-cache contexts yielded ~1 hit/frame while
// late UI collided with source snapshots. Reassign those same 8 KiB to bounded
// frame ownership; evaluate unchanged source lighting without that tiny cache.
constexpr unsigned kModelStaticLightBytes=0;
constexpr unsigned kModelPreparationBytes=RE4DC_D349_RENDERER_STACK?12288:0;
constexpr unsigned kModelPacketBytes=kModelSlabBytes-kModelMetadataBytes-kModelStaticLightBytes-kModelDeferredSpillBytes-kModelPreparationBytes;
pvr_vertex_t* model_packets; unsigned model_used,model_pending; Entry* model_handle;
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
re4dc::format32::UvRequest actor_uv32_request;
struct ActorUv32Binding {
    Entry* handle=nullptr;
    unsigned width=0,height=0;
    float u_scale=0,v_scale=0;
    bool valid=false;
} actor_uv32_binding;
#endif
#if RE4DC_ACTOR_UV16
unsigned next_pcw_set,next_pcw_clear; // actors30: re4dc_model_next_header_pcw, one packet_begin
#endif
int model_diagnostic=-1;
unsigned model_parts,model_invalid,model_resource,model_overflow,model_input,model_output,model_peak,model_presented;
#if defined(RE4DC_MODEL_PART_DUMP)
unsigned model_dump_crc,model_dump_fnv;
#define RE4DC_PART_DUMP_KEY(k) (model_dump_crc=(k).crc,model_dump_fnv=(k).fnv)
#else
#define RE4DC_PART_DUMP_KEY(k) ((void)0)
#endif
unsigned model_capacity_rejects,model_state_rejects,model_texture_rejects,model_wrap_rejects,model_empty_parts,model_scale_rebuilds;
unsigned model_state_bits[8];
unsigned model_alpha_material,model_alpha_vertex,model_alpha_faded;
unsigned model_header_hits,model_header_builds;
Re4dcNativeFrameStats completed_frame{};
re4dc::profile::Snapshot completed_render_profile{};
re4dc::profile::Source render_source_begin{};
Re4dcModelWorkStats frame_work_start{};
Re4dcPreparationStats preparation_start{};
struct PreparationFrame {volatile unsigned sequence;unsigned frame;Re4dcPreparationStats work;unsigned scratch_bytes,packet_bytes;};
PreparationFrame completed_preparation{};
unsigned frame_header_hits,frame_header_builds,frame_pvr_calls,frame_pvr_bytes;
unsigned frame_queue_peak,frame_queue_drops;
std::uint64_t frame_render_start;

#if RE4DC_PVR_FAST_WAKE || RE4DC_PVR_PIPELINE
// KOS wakes a thread blocked in pvr_wait_render_done()/pvr_resolve_frame()
// from the render-done and vblank interrupts without rescheduling (only the
// TA-done path calls thd_schedule(true)). With THD_SCHED_HZ=100 the waiter
// then sleeps until the next 10 ms tick: D367 T idled 29 ms/frame as ONE run
// per frame of ~25 or ~35 ms (render 7.5 + vblank + up to 2 x 10 ms ticks).
// Chain both interrupts and reschedule, as KOS's TA-done path does, only
// while a native PVR waiter is registered. No game thread is woken or
// reordered here: thd_schedule(true) keeps the interrupted thread at the
// front of its priority group.
volatile unsigned pvr_waiters;
asic_evt_handler_entry_t kos_render_done{};
unsigned wake_renders,wake_vblanks;
void render_done_chain(uint32_t code,void* data){
    (void)data;
    if(kos_render_done.hdl)kos_render_done.hdl(code,kos_render_done.data);
    if(pvr_waiters){++wake_renders;thd_schedule(true);}
}
void vblank_wake(uint32_t,void*){
    if(pvr_waiters){++wake_vblanks;thd_schedule(true);}
}
struct PvrWaiter {
    PvrWaiter(){const int o=irq_disable();pvr_waiters=pvr_waiters+1;irq_restore(o);}
    ~PvrWaiter(){const int o=irq_disable();pvr_waiters=pvr_waiters-1;irq_restore(o);}
};
void install_fast_wake(){
    kos_render_done=asic_evt_set_handler(ASIC_EVT_PVR_RENDERDONE_TSP,render_done_chain,nullptr);
    // Registered after pvr_init(): runs after KOS's flip handler.
    const int handle=vblank_handler_add(vblank_wake,nullptr);
    re4dc_log("native pvr wake: render-done chained=%d vblank handler=%d\n",kos_render_done.hdl!=nullptr,handle);
}
#endif
#if RE4DC_TA_GUARD
// Real-hardware TA capacity guard. Flycast neither enforces nor reports TA
// capacity (KOS ta_used stays 0 there); a console does: the TA writes every
// strip into the current bank's vertex (parameter) buffer (~12 B per strip
// header + 24 B per float-UV vertex without offset colour) and one 4-byte
// object pointer per touched tile into the OPBs. Overflow drops or corrupts
// geometry, or halts the render. As dca3 does (rwdc.cpp vertexBufferFree /
// freeVertexTarget / vertexOverflown), skip whole parts once free space falls
// below an adaptive reserve and detect overflow per scene. TA_GUARD=2 also
// declines to present an overflowed scene (the previous image stays shown;
// game state, logic and inputs are untouched either way).
constexpr unsigned kGuardVertbuf=RE4DC_TA_VERTBUF_KB*1024U;
constexpr unsigned kGuardMin=64*1024,kGuardMax=kGuardVertbuf/2,kParamPerHeader=12,kParamPerVertex=24;
unsigned guard_reserve=kGuardMin,guard_scale=256;   // adaptive reserve; hw/estimate x256
unsigned guard_sw;                                  // estimated parameter bytes, this scene
volatile unsigned guard_ta_faults,guard_render_faults; // ASIC error events (interrupt)
unsigned guard_skips,guard_fault_frames,guard_render_fault_frames,guard_discards;
unsigned guard_hw_last,guard_hw_peak,guard_sw_last,guard_sw_peak,guard_opb_last;
asic_evt_handler_entry_t guard_kos[5];
constexpr std::uint16_t kGuardEvents[5]={ASIC_EVT_PVR_OPB_OUTOFMEM,ASIC_EVT_PVR_TA_INPUT_OVERFLOW,
    ASIC_EVT_PVR_TA_INPUT_ERR,ASIC_EVT_PVR_ISP_OUTOFMEM,ASIC_EVT_PVR_STRIP_HALT};
void guard_event(uint32_t code,void* data){
    const unsigned i=unsigned(reinterpret_cast<std::uintptr_t>(data));
    if(i<5 && guard_kos[i].hdl)guard_kos[i].hdl(code,guard_kos[i].data); // KOS PVR_RENDER_DBG builds only
    if(i<3)guard_ta_faults=guard_ta_faults|(1U<<i);else guard_render_faults=guard_render_faults|(1U<<i);
}
void install_guard(){
    // Release KOS leaves these events unhooked and disabled; enable them.
    for(unsigned i=0;i<5;++i){
        guard_kos[i]=asic_evt_set_handler(kGuardEvents[i],guard_event,reinterpret_cast<void*>(std::uintptr_t(i)));
        asic_evt_enable(kGuardEvents[i],ASIC_IRQ_DEFAULT);
    }
    re4dc_log("native TA guard: vertbuf=%u reserve=%u..%u discard=%d estimate=%u+%u/vertex\n",
        kGuardVertbuf,kGuardMin,kGuardMax,RE4DC_TA_GUARD>=2,kParamPerHeader,kParamPerVertex);
}
unsigned guard_estimate(){return unsigned((std::uint64_t(guard_sw)*guard_scale)>>8);}
unsigned guard_hw_free(){
    const unsigned start=PVR_GET(PVR_TA_VERTBUF_START),pos=PVR_GET(PVR_TA_VERTBUF_POS),end=PVR_GET(PVR_TA_VERTBUF_END);
    if(end<=start || pos<start)return ~0U; // registers not live (emulator): estimate only
    return pos<end?end-pos:0;
}
// Part admission (reserve): translucent drain parts keep a quarter reserve so
// the opaque list is what yields first; UI quads are never refused.
bool guard_admit(bool draining){
    const unsigned need=draining?guard_reserve/4:guard_reserve;
    const unsigned est=guard_estimate();
    const unsigned sw_free=est<kGuardVertbuf?kGuardVertbuf-est:0;
    if(std::min(sw_free,guard_hw_free())>=need)return true;
    ++guard_skips;return false;
}
void guard_account(unsigned header_slots,unsigned vertex_slots){
    guard_sw+=header_slots*kParamPerHeader+vertex_slots*kParamPerVertex;
}
void guard_scene_begin(){guard_sw=0;guard_ta_faults=0;}
// Before the last list closes (afterwards KOS may already retarget the TA
// registers to the next bank). Returns the TA-time fault bits of the scene.
unsigned guard_scene_end(){
    const unsigned start=PVR_GET(PVR_TA_VERTBUF_START),pos=PVR_GET(PVR_TA_VERTBUF_POS),end=PVR_GET(PVR_TA_VERTBUF_END);
    const unsigned opb=PVR_GET(PVR_TA_OPB_POS),opb_end=PVR_GET(PVR_TA_OPB_END),opb_init=PVR_GET(PVR_TA_OPB_INIT);
    unsigned faults=guard_ta_faults;
    if(pos>=end)faults|=8;
    if(opb*4>=opb_end && opb!=opb_init)faults|=16; // dca3 vertexOverflown(); Flycast's OPB_POS differs
    guard_hw_last=pos>start?pos-start:0;guard_sw_last=guard_sw;guard_opb_last=opb;
    guard_hw_peak=std::max(guard_hw_peak,guard_hw_last);guard_sw_peak=std::max(guard_sw_peak,guard_sw_last);
    // Calibrate the estimate on hardware (Flycast reports 0: keep 1.0).
    if(guard_hw_last && guard_sw && !(faults&8))
        guard_scale=std::clamp(unsigned((std::uint64_t(guard_hw_last)<<8)/guard_sw),128U,384U);
    if(faults){++guard_fault_frames;guard_reserve=std::min(guard_reserve+32*1024,kGuardMax);}
    else if(guard_reserve>kGuardMin+4*1024)guard_reserve-=4*1024;else guard_reserve=kGuardMin;
    guard_ta_faults=0;
    return faults;
}
// After the render fence: render-time faults of the scene being resolved.
bool guard_present(bool present,unsigned ta_faults){
    const int o=irq_disable();const unsigned render=guard_render_faults;guard_render_faults=0;irq_restore(o);
    if(render)++guard_render_fault_frames;
    if((ta_faults|render) && present && RE4DC_TA_GUARD>=2){++guard_discards;return false;}
    return present;
}
#endif
#if RE4DC_PVR_LATCH
// PVR_LATCH=1 (issue 9, hardware diagnosis; needs CRASH_SCREEN=1): a ring of the last PVR events with their UI
// frame, event totals and the KOS PVR state, printed on the stop screen. The raw ASIC_ACK_A/B/C words read at the
// failure cannot show an error event: KOS's ASIC dispatcher (asic.c handler_irq) acknowledges every pending bit
// of all three registers on each ASIC interrupt, vblank included, whether or not the event is enabled. Here every
// PVR event gets a chained handler (the previous handler, KOS's or the fast-wake chain, still runs first). Nothing
// new is enabled: an event without its own interrupt (ISP render done, the five error events in a release KOS) is
// still seen at the next dispatch, which reads all pending bits. Thread-side marks: scene open / close, fence,
// TA bank wait over 95 ms (KOS ignores pvr_wait_ready's 100 ms timeout and writes the next scene anyway), bank
// switches. Render-only: no frame, timing or logic decision reads any of it.
namespace latch {
constexpr unsigned kRing=64;
volatile unsigned char ring_code[kRing];
volatile unsigned short ring_frame[kRing];
volatile unsigned head;
// totals: S scene opened, c/d closed presented/discarded, o m t n p list done, R I render done TSP/ISP, F flip,
// e error events (any), W TA bank waits over 95 ms, X fence failures
enum {kS,kC,kO,kT,kP,kR,kI,kF,kE,kW,kX,kCounts};
volatile unsigned counts[kCounts];
volatile unsigned last_flips;
#if RE4DC_PVR_LATCH>=2
// PVR_LATCH=2 (latch v2, issue 9 after the d74b8ec8 photos): v1's ring lost every pre-hang event to 100 identical
// Y slices and v1 watched only five of the six SB_ISTERR bits (KOS ASIC_EVT_PVR_PARAM_OUTOFMEM, bit 2, was missing,
// and its "er" legend called bit 3 "OPB out of memory" bit 2). v2: a run of one code is one ring entry with a
// count; "er" is the SB_ISTERR bit set itself (bit 0 render ISP out of cache, 1 render strip buffer hazard, 2 TA
// ISP/TSP parameter overflow, 3 TA object list pointer overflow, 4 TA illegal parameter, 5 TA FIFO overflow), each
// with the UI frame it first appeared and its count; every scene's TA vertex / OPB use at its close (the positions
// the render of that scene reads) is kept for the last two scenes and as a maximum since boot.
volatile unsigned short ring_rep[kRing];
volatile unsigned errors;          // SB_ISTERR bits seen since boot (bit n = ASIC event 0x0200+n)
volatile unsigned err_first[6],err_count[6];
struct SceneUse { unsigned frame,vtx,opb; };
volatile SceneUse scene_use[2];    // [0] newest closed scene
volatile unsigned max_vtx,max_vtx_frame,max_opb,max_opb_frame;
constexpr unsigned kNEvents=13;
asic_evt_handler_entry_t prev[kNEvents];
constexpr std::uint16_t kEvents[kNEvents]={ASIC_EVT_PVR_OPAQUEDONE,ASIC_EVT_PVR_OPAQUEMODDONE,ASIC_EVT_PVR_TRANSDONE,
    ASIC_EVT_PVR_TRANSMODDONE,ASIC_EVT_PVR_PTDONE,ASIC_EVT_PVR_RENDERDONE_TSP,ASIC_EVT_PVR_RENDERDONE_ISP,
    ASIC_EVT_PVR_ISP_OUTOFMEM,ASIC_EVT_PVR_STRIP_HALT,ASIC_EVT_PVR_PARAM_OUTOFMEM,ASIC_EVT_PVR_OPB_OUTOFMEM,
    ASIC_EVT_PVR_TA_INPUT_ERR,ASIC_EVT_PVR_TA_INPUT_OVERFLOW};
constexpr char kCodes[kNEvents]={'o','m','t','n','p','R','I','0','1','2','3','4','5'};
constexpr unsigned char kCount[kNEvents]={kO,kO,kT,kT,kP,kR,kI,kE,kE,kE,kE,kE,kE};
#else
volatile unsigned errors;          // error event bits: 1 ISP out of memory, 2 strip halt, 4 OPB out of memory, 8 TA input error, 16 TA input overflow
constexpr unsigned kNEvents=12;
asic_evt_handler_entry_t prev[12];
constexpr std::uint16_t kEvents[12]={ASIC_EVT_PVR_OPAQUEDONE,ASIC_EVT_PVR_OPAQUEMODDONE,ASIC_EVT_PVR_TRANSDONE,
    ASIC_EVT_PVR_TRANSMODDONE,ASIC_EVT_PVR_PTDONE,ASIC_EVT_PVR_RENDERDONE_TSP,ASIC_EVT_PVR_RENDERDONE_ISP,
    ASIC_EVT_PVR_ISP_OUTOFMEM,ASIC_EVT_PVR_STRIP_HALT,ASIC_EVT_PVR_OPB_OUTOFMEM,ASIC_EVT_PVR_TA_INPUT_ERR,
    ASIC_EVT_PVR_TA_INPUT_OVERFLOW};
constexpr char kCodes[12]={'o','m','t','n','p','R','I','1','2','3','4','5'};
constexpr unsigned char kCount[12]={kO,kO,kT,kT,kP,kR,kI,kE,kE,kE,kE,kE};
#endif
void put(char c){
    const int o=irq_disable();
    const unsigned h=head;
#if RE4DC_PVR_LATCH>=2
    if(h && ring_code[(h-1)%kRing]==static_cast<unsigned char>(c)){
        if(ring_rep[(h-1)%kRing]<65535)ring_rep[(h-1)%kRing]=static_cast<unsigned short>(ring_rep[(h-1)%kRing]+1);
        irq_restore(o);return;
    }
    ring_rep[h%kRing]=1;
#endif
    ring_code[h%kRing]=static_cast<unsigned char>(c);ring_frame[h%kRing]=static_cast<unsigned short>(frame);head=h+1;
    irq_restore(o);
}
void bump(unsigned k){const int o=irq_disable();counts[k]=counts[k]+1;irq_restore(o);}
void event(uint32_t code,void* data){
    const unsigned i=unsigned(reinterpret_cast<std::uintptr_t>(data));
    if(i>=kNEvents)return;
    if(prev[i].hdl)prev[i].hdl(code,prev[i].data);
    put(kCodes[i]);counts[kCount[i]]=counts[kCount[i]]+1;
#if RE4DC_PVR_LATCH>=2
    if(i>=7){
        const unsigned b=code&0xff;
        if(b<6){
            if(!(errors&(1U<<b)))err_first[b]=frame;
            err_count[b]=err_count[b]+1;errors=errors|(1U<<b);
        }
    }
#else
    if(i>=7)errors=errors|(1U<<(i-7));
#endif
}
#if RE4DC_PVR_LATCH>=2
// stream_close, before the scene's lists finish: the TA registers still describe this scene's bank.
void scene_close(){
    const unsigned vs=PVR_GET(PVR_TA_VERTBUF_START),vp=PVR_GET(PVR_TA_VERTBUF_POS);
    const unsigned oi=PVR_GET(PVR_TA_OPB_INIT),op=PVR_GET(PVR_TA_OPB_POS)*4U;   // OPB_POS: word units on hardware
    const unsigned v=vp>=vs?vp-vs:0,b=op>=oi?op-oi:0;
    const int o=irq_disable();
    scene_use[1].frame=scene_use[0].frame;scene_use[1].vtx=scene_use[0].vtx;scene_use[1].opb=scene_use[0].opb;
    scene_use[0].frame=frame;scene_use[0].vtx=v;scene_use[0].opb=b;
    if(v>max_vtx){max_vtx=v;max_vtx_frame=frame;}
    if(b>max_opb){max_opb=b;max_opb_frame=frame;}
    irq_restore(o);
}
#endif
void vblank(uint32_t,void*){
    const unsigned f=unsigned(pvr_state.frame_count);
    if(f!=last_flips){last_flips=f;put('F');counts[kF]=counts[kF]+1;}
}
void install(){
    last_flips=unsigned(pvr_state.frame_count);
    for(unsigned i=0;i<kNEvents;++i)prev[i]=asic_evt_set_handler(kEvents[i],event,reinterpret_cast<void*>(std::uintptr_t(i)));
    const int handle=vblank_handler_add(vblank,nullptr);
    re4dc_log("native PVR latch: %u events chained (kos handlers %d/%d/%d) vblank=%d\n",kNEvents,prev[0].hdl!=nullptr,
              prev[5].hdl!=nullptr,prev[9].hdl!=nullptr,handle);
}
// Thread side: the scene's first list (KOS pvr_start_ta_rendering waits up to 100 ms for the TA bank, then
// proceeds even on a timeout).
void list_begin_timed(pvr_list_t list,bool& failed){
    const bool busy=pvr_check_ready()<0;
    const auto t=busy?timer_us_gettime64():0;
    failed=pvr_list_begin(list)<0;
    if(busy && timer_us_gettime64()-t>95000){put('W');bump(kW);}
}
}
#endif
#if RE4DC_PVR_READY_STRICT
// PVR_READY_STRICT=1 (issue 9): never write a scene into a TA bank, a tile matrix or a VRAM page the PVR may still
// read after a timed-out wait. KOS (pinned toolchain, kernel/arch/dreamcast/hardware/pvr) waits 100 ms and then
// carries on regardless in three places this build reaches:
// - pvr_scene.c pvr_start_ta_rendering() (static, inlined into pvr_list_begin at a scene's first list):
//   pvr_wait_ready()'s timeout is ignored, so the next scene's TA input goes into the bank whose previous scene was
//   never handed to a render (no TA list init: it is appended to it). When that render finally starts,
//   pvr_begin_queued_render() puts the background plane at the TA's current vertex position, in the middle of the
//   new scene, and pvr_sync_reg_buffer() re-inits the TA under a half-written scene: a corrupted render (an ISP
//   lockup on real hardware) or a scene whose list-done events never all arrive (never rendered).
//   With one bank (TA_DOUBLEBUF off, the sub-screen backing) pvr_wait_render_done()'s timeout is ignored there too:
//   TA input into the bank the render reads.
// - pvr_buffers.c pvr_set_presort_mode() (WORLD_AUTOSORT, stream_open / world_sort_begin): writes the TA target
//   bank's tile matrix; with one bank after an ignored pvr_wait_render_done() timeout, the matrix being rendered.
// - pvr_irq.c pvr_present_wait() (present_fence: every scene open in single-bank mode and every VRAM upload / free)
//   returns -1 after ONE 100 ms wait; the build halts there ("completion fence failed"), so a render that is only
//   slow (a GPU-bound frame queued behind the previous one) stops the game.
// Here (link wraps, the toolchain stays as pinned) each wait goes on in 100 ms slices up to kSlices (10 s, inside
// the 30 s hang watchdog); every expired slice is counted and, with PVR_LATCH, put in the event ring with its UI
// frame: K TA bank (previous scene not yet handed to a render), Q render done (one bank / tile matrix),
// Y present fence. Past the bound the failure is reported as before (the stop screen names it). No TA or ISP reset
// (rejected: it would hide the failure). Render-only: no frame, timing or logic decision reads any of it; in
// Flycast no wait ever expires (renders complete at once), so the image behaves exactly as without the knob.
// Checked and left alone (they do not proceed into a busy bank): pvr_render_lists() (starts a render only with
// render_busy and render_completed clear, all lists in), pvr_apply_decision()/pvr_present_async() (a decision
// applies only after render-done), the fast-wake and latch chains (KOS's handler runs first), pvr_scene_finish()
// (its blank lists follow a list_begin of the same scene), pvr_set_vbuf_doublebuf() (refuses while busy),
// re4dc_ui_ta_single_bank() and stream_open()'s single-bank path (present_fence first, which halts on failure), the
// gpu::quiesce() callers (after present_fence; a timeout halts or skips the VRAM change).
#if RE4DC_PVR_RECOVER
// PVR_RECOVER=1 (issue 9, default 0; needs PVR_READY_STRICT=1): a render the console never finishes (d74b8ec8 photos:
// the last closed scene got all three list-done events, its render started and render-done never came; SB_ISTERR
// bit 0 "ISP out of cache" and bit 3 "object list pointer overflow" were raised) stopped the game for good. Here a
// render still busy after a bounded time is reset the way the hardware allows and its frame is dropped:
// - Detection, in PVR_READY_STRICT's 100 ms wait slices (K TA bank, Q render done, Y present fence): the render
//   has been busy for kStuckMs (1 s), or kStuckErrMs (100 ms) once a render error (SB_ISTERR bit 0 or 1) was
//   raised during it. P2, the TA side: a closed scene whose list-done events have not all arrived after kStuckMs
//   while no render runs.
// - Action, in the next vblank interrupt (the thread only asks; the ISR context is what KOS's handlers expect):
//   P1: PVR soft reset of the ISP/TSP core (SOFTRESET 0x005F8008 bit 1, then 0), then the render-done handler chain
//   below this one (KOS pvr_int_handler: render_busy 0, render_completed 1, the pending present/discard decision
//   applied, waiters woken; the fast-wake chain) runs as if the interrupt had come. The dropped frame's buffer is
//   flipped as it is (partly drawn); the next scene renders normally. P2: a TA soft reset (bit 0) only when a TA
//   error (SB_ISTERR bit 4 or 5) was raised, then the missing list-done events through their handler chains, so
//   KOS starts the render (pvr_render_lists re-inits the TA registers for the other bank).
// - Last resort: kGiveUp recoveries in a row without one render finishing on its own stop the game with the stop
//   screen ("PVR render recovery gave up").
// Render-only: nothing runs until a wait has expired, which never happens in Flycast (renders finish at once) and
// so never in a gate run; every recovery logs "pvr recover:" and counts in the stop screen's rdy row.
// Test aid (never on a play disc): dc/crashtest.txt "pvrhang <ui frame> <n>" swallows n render-done interrupts
// from that frame on (render_busy stays set as on the console), "pvrlist <ui frame>" one translucent list-done.
namespace pvr_recover {
constexpr unsigned kStuckMs=1000,kStuckErrMs=100,kGiveUp=8;
#if RE4DC_MV_SHADOWS
// MV_SHADOWS: the opaque modifier volume list is enabled too (its OPB is allocated), so KOS waits for its list-done.
constexpr unsigned kNLists=4;
asic_evt_handler_entry_t done_prev{},list_prev[kNLists]{};
constexpr std::uint16_t kListEvents[kNLists]={ASIC_EVT_PVR_OPAQUEDONE,ASIC_EVT_PVR_TRANSDONE,ASIC_EVT_PVR_PTDONE,ASIC_EVT_PVR_OPAQUEMODDONE};
constexpr unsigned kListBits[kNLists]={1U<<PVR_LIST_OP_POLY,1U<<PVR_LIST_TR_POLY,1U<<PVR_LIST_PT_POLY,1U<<PVR_LIST_OP_MOD};
#else
constexpr unsigned kNLists=3;
asic_evt_handler_entry_t done_prev{},list_prev[3]{};
constexpr std::uint16_t kListEvents[3]={ASIC_EVT_PVR_OPAQUEDONE,ASIC_EVT_PVR_TRANSDONE,ASIC_EVT_PVR_PTDONE};
constexpr unsigned kListBits[3]={1U<<PVR_LIST_OP_POLY,1U<<PVR_LIST_TR_POLY,1U<<PVR_LIST_PT_POLY};
#endif
asic_evt_handler_entry_t err_prev[6]{};
volatile unsigned req;            // 1 P1 render, 2 P2 TA lists; cleared by the vblank handler
volatile unsigned err_bits;       // SB_ISTERR bits since the current render started
volatile bool busy_seen;
volatile std::uint64_t busy_since;
volatile unsigned p1,p2,in_row,last_frame,natural;
volatile bool synth;
volatile int inject_hang_frame=-1,inject_hang_left,inject_list_frame=-1;
void note_render_state(){   // IRQ context
    if(pvr_state.render_busy){
        if(!busy_seen){busy_seen=true;busy_since=timer_us_gettime64();err_bits=0;}
    } else busy_seen=false;
}
void done_chain(uint32_t code,void* data){
    (void)data;
    if(!synth && inject_hang_frame>=0 && int(frame)>=inject_hang_frame && inject_hang_left>0){
        inject_hang_left=inject_hang_left-1;   // test: the render-done interrupt never arrives
        return;
    }
    if(done_prev.hdl)done_prev.hdl(code,done_prev.data);
    if(!synth){in_row=0;natural=natural+1;}
    note_render_state();
}
void list_chain(uint32_t code,void* data){
    const unsigned i=unsigned(reinterpret_cast<std::uintptr_t>(data));
    if(i>=kNLists)return;
    if(!synth && i==1 && inject_list_frame>=0 && int(frame)>=inject_list_frame){inject_list_frame=-1;return;}
    if(list_prev[i].hdl)list_prev[i].hdl(code,list_prev[i].data);
    note_render_state();
}
void err_chain(uint32_t code,void* data){
    const unsigned b=unsigned(reinterpret_cast<std::uintptr_t>(data));
    if(b<6 && err_prev[b].hdl)err_prev[b].hdl(code,err_prev[b].data);
    if(b<6)err_bits=err_bits|(1U<<b);
}
void vblank(uint32_t,void*){
    note_render_state();
    const unsigned r=req;
    if(!r)return;
    synth=true;
    if(r==1 && pvr_state.render_busy){
        PVR_SET(PVR_RESET,PVR_RESET_ISPTSP);PVR_SET(PVR_RESET,PVR_RESET_NONE);
        if(done_prev.hdl)done_prev.hdl(ASIC_EVT_PVR_RENDERDONE_TSP,done_prev.data);
    } else if(r==2 && !pvr_state.render_busy && pvr_state.ta_busy){
        if(err_bits&0x30){PVR_SET(PVR_RESET,PVR_RESET_TA);PVR_SET(PVR_RESET,PVR_RESET_NONE);}
        for(unsigned i=0;i<kNLists;++i)
            if((pvr_state.lists_enabled&kListBits[i]) && !(pvr_state.lists_transferred&kListBits[i]) && list_prev[i].hdl)
                list_prev[i].hdl(kListEvents[i],list_prev[i].data);
    }
    synth=false;
    note_render_state();
    req=0;
    genwait_wake_all((void*)&req);
}
void install(){
    char t[48]={0};
    if(re4dc_fixture_read("/cd/dc/crashtest.txt",t,sizeof(t)-1)>0){
        unsigned a=0,b=0;
        if(!std::strncmp(t,"pvrhang",7) && std::sscanf(t+7,"%u %u",&a,&b)==2){inject_hang_frame=int(a);inject_hang_left=int(b);}
        else if(!std::strncmp(t,"pvrlist",7) && std::sscanf(t+7,"%u",&a)==1)inject_list_frame=int(a);
    }
    done_prev=asic_evt_set_handler(ASIC_EVT_PVR_RENDERDONE_TSP,done_chain,nullptr);
    for(unsigned i=0;i<kNLists;++i)list_prev[i]=asic_evt_set_handler(kListEvents[i],list_chain,reinterpret_cast<void*>(std::uintptr_t(i)));
    for(unsigned b=0;b<6;++b)err_prev[b]=asic_evt_set_handler(std::uint16_t(ASIC_EVT_PVR_ISP_OUTOFMEM+b),err_chain,reinterpret_cast<void*>(std::uintptr_t(b)));
    const int handle=vblank_handler_add(vblank,nullptr);
    re4dc_log("pvr recover: armed (stuck %u ms, %u ms after a render error, give up after %u) vblank=%d test hang=%d/%d list=%d\n",
              kStuckMs,kStuckErrMs,kGiveUp,handle,int(inject_hang_frame),int(inject_hang_left),int(inject_list_frame));
}
// Called by the wait loops once per expired 100 ms slice (IRQs disabled). code: K / Q / Y.
volatile bool gave_up;
bool on_slice(char code){
    if(gave_up)return true;
    unsigned kind=0;
    const std::uint64_t now=timer_us_gettime64();
    if(pvr_state.render_busy && busy_seen){
        const std::uint64_t ms=(now-busy_since)/1000;
        if(ms>=((err_bits&3)?kStuckErrMs:kStuckMs))kind=1;
    } else if(code=='K' && !pvr_state.render_busy && pvr_state.ta_busy &&
              pvr_state.lists_transferred!=pvr_state.lists_enabled){
        // The previous scene is closed (this wait is the next scene's first list) and its lists never all arrived.
        static unsigned k_slices;static unsigned k_frame=~0U;
        if(k_frame!=frame){k_frame=frame;k_slices=0;}
        if(++k_slices>=kStuckMs/100)kind=2;
    }
    if(!kind)return false;
    if(in_row>=kGiveUp){gave_up=true;return true;}
    in_row=in_row+1;last_frame=frame;
    if(kind==1)p1=p1+1;else p2=p2+1;
#if RE4DC_PVR_LATCH
    latch::put(kind==1?'V':'U');
#endif
    re4dc_log("pvr recover: P%u at ui frame %u (wait %c, render busy %ums, isterr %02x, lists %02x/%02x, in a row %u)\n",kind,frame,
              code,busy_seen?unsigned((now-busy_since)/1000):0U,err_bits,unsigned(pvr_state.lists_transferred),
              unsigned(pvr_state.lists_enabled),in_row);
    req=kind;
    for(unsigned tries=0;req && tries<4;++tries)genwait_wait((void*)&req,"re4dc recover",50);
    return false;
}
}
#endif
namespace pvr_ready {
constexpr unsigned kSliceMs=100,kSlices=100;
volatile int test_slices;   // crash_screen.cpp "pvrwait" test (re4dc_pvr_ready_test_arm): slices to expire
volatile unsigned ta_timeouts,render_timeouts,present_timeouts,first_frame=~0U,last_frame;
void note(char code,volatile unsigned& n){
    n=n+1;if(first_frame==~0U)first_frame=frame;last_frame=frame;
#if RE4DC_PVR_LATCH
    latch::put(code);
#else
    (void)code;
#endif
}
// Wait until a KOS PVR flag clears (KOS wakes the flag's genwait queue: ta_busy at render start, render_busy at
// render done). Returns false only past the bound.
bool wait_clear(volatile int& flag,const char* what,char code,volatile unsigned& n){
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    re4dc::wc24::WaitScope wc24_wait(re4dc::wc24::PvrWait);
#endif
    const int o=irq_disable();
    unsigned slices=0;
    while(flag && slices<kSlices)
        if(genwait_wait((void*)&flag,what,kSliceMs)<0 && flag){
            note(code,n);++slices;
#if RE4DC_PVR_RECOVER
            if(pvr_recover::on_slice(code))break;
#endif
        }
    const bool ok=!flag;
    irq_restore(o);
#if RE4DC_PVR_RECOVER
    if(pvr_recover::gave_up)re4dc_missing("PVR render recovery gave up");
#endif
    return ok;
}
// Before KOS's own 100 ms waits run (they then return at once).
void acquire_bank(){
    if(pvr_state.ta_checked_ready)return;   // this scene already owns its TA bank
    // Crash test (dc/crashtest.txt "pvrwait", never on a play disc): one expired 100 ms slice per scene, counted as
    // a TA bank timeout, so the stop screen's rdy row can be checked in Flycast (renders never stall there).
    if(test_slices>0){
        test_slices=test_slices-1;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        re4dc::wc24::WaitScope wc24_wait(re4dc::wc24::PvrWait);
#endif
        const int o=irq_disable();genwait_wait((void*)&test_slices,"re4dc ready test",kSliceMs);irq_restore(o);
        note('K',ta_timeouts);
    }
    if(!wait_clear(pvr_state.ta_busy,"re4dc TA bank",'K',ta_timeouts))re4dc_missing("PVR TA bank wait timed out (strict)");
    if(!pvr_state.vbuf_doublebuf && !wait_clear(pvr_state.render_busy,"re4dc render done",'Q',render_timeouts))
        re4dc_missing("PVR render wait timed out (strict)");
}
int present_wait(){
    for(unsigned slices=0;;){
        if(pvr_present_wait()==0 || !pvr_present_pending())return 0;
        note('Y',present_timeouts);
#if RE4DC_PVR_RECOVER
        {const int o=irq_disable();const bool give_up=pvr_recover::on_slice('Y');irq_restore(o);
         if(give_up)re4dc_missing("PVR render recovery gave up");}
#endif
        if(++slices>=kSlices)return -1;
    }
}
}
extern "C" void re4dc_pvr_ready_test_arm(int slices){pvr_ready::test_slices=slices;}
extern "C" int __real_pvr_list_begin(pvr_list_t list);
extern "C" int __wrap_pvr_list_begin(pvr_list_t list){
    // DMA lists (unused here) do not touch the TA at list_begin, as in KOS.
    if(!(pvr_state.dma_mode && pvr_state.dma_buffers[pvr_state.ram_target].base[list]))pvr_ready::acquire_bank();
    return __real_pvr_list_begin(list);
}
extern "C" void __real_pvr_set_presort_mode(bool presort);
#if defined(RE4DC_G1_PRESORT_LAZY) && RE4DC_G1_PRESORT_LAZY
// G1_PRESORT_LAZY (g1parts.mk; exact): the ISP reads a tile's presort bit (control word bit 29) only when the scene
// renders, so a scene's requests are kept and its last one is written at pvr_scene_finish, into the bank and layout
// they were made for, and only when that bank's tiles hold the other mode. Every writer (KOS init / set, res_mode.cpp
// apply, this flush) writes all tiles alike, so the first tile tells the bank's mode. Play draws presort at the
// stream open, then autosort for the world (world_sort_begin): both writes of ~600 tiles (uncached VRAM) every frame
// become none. Single-bank mode (no TA double buffer) keeps KOS's immediate write.
namespace presort_lazy {
bool pending,want; uint32_t tm; int tw,th;
unsigned requests,writes,skips,log_frame;
void flush(){
    if(!pending)return;
    pending=false;
    uint32_t* vr=reinterpret_cast<uint32_t*>(PVR_RAM_BASE)+tm/4U+6U;
    if(((vr[0]>>29)&1U)==(want?1U:0U)){++skips;return;}
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    DFA26_HIT(PresortChanged)
#endif
    ++writes;
    for(int x=0;x<tw;++x)
        for(int y=0;y<th;++y){vr[0]=(uint32_t(y)<<8)|(uint32_t(x)<<2)|(uint32_t(want)<<29);vr+=6;}
    vr[-6]|=BIT(31);
}
}
extern "C" int __real_pvr_scene_finish();
extern "C" int __wrap_pvr_scene_finish(){
    presort_lazy::flush();
    if(frame-presort_lazy::log_frame>=1800U){presort_lazy::log_frame=frame;
        re4dc_log("G1 presort lazy: frame=%u requests=%u writes=%u skips=%u\n",frame,presort_lazy::requests,presort_lazy::writes,presort_lazy::skips);}
    return __real_pvr_scene_finish();
}
extern "C" void __wrap_pvr_set_presort_mode(bool presort){
    pvr_ready::acquire_bank();   // the target bank's tile matrix is free only once the bank is acquired
    if(!pvr_state.vbuf_doublebuf){presort_lazy::flush();DFA26_HIT(PresortRewrite)__real_pvr_set_presort_mode(presort);return;}
    const uint32_t tm=pvr_state.ta_buffers[pvr_state.ta_target].tile_matrix;
    if(presort_lazy::pending && presort_lazy::tm!=tm)presort_lazy::flush();   // another bank's request (not in play)
    presort_lazy::pending=true;presort_lazy::want=presort;presort_lazy::tm=tm;
    presort_lazy::tw=pvr_state.tw;presort_lazy::th=pvr_state.th;++presort_lazy::requests;
}
#else
extern "C" void __wrap_pvr_set_presort_mode(bool presort){
    pvr_ready::acquire_bank();   // the target bank's tile matrix is free only once the bank is acquired
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    DFA26_HIT(PresortRewrite)
#endif
    __real_pvr_set_presort_mode(presort);
}
#endif
#endif
#if RE4DC_PVR_LATCH
// The stop screen's lines (crash_screen.cpp, which = 0..3), formatted at the failure; 0 past the last line.
extern "C" int re4dc_pvr_latch_line(unsigned which,char* out,unsigned size){
    using namespace latch;
    if(which==0){
        snprintf(out,size,"st ta%d rb%d rc%d le%02x lt%02x tt%d vt%d db%d pd%d er%02x",int(pvr_state.ta_busy),
            int(pvr_state.render_busy),int(pvr_state.render_completed),unsigned(pvr_state.lists_enabled),
            unsigned(pvr_state.lists_transferred),int(pvr_state.ta_target),int(pvr_state.view_target),
            int(pvr_state.vbuf_doublebuf),pvr_present_pending(),errors);
        return 1;
    }
    if(which==1){
        snprintf(out,size,"n S%u c%u o%u t%u p%u R%u I%u F%u W%u X%u",counts[kS]%1000,counts[kC]%1000,
            counts[kO]%1000,counts[kT]%1000,counts[kP]%1000,counts[kR]%1000,counts[kI]%1000,counts[kF]%1000,
            counts[kW]%1000,counts[kX]%1000);
        return 1;
    }
    if(which==2){
        // Newest events last; a frame's events follow its last two digits and ':'.
        const unsigned h=head,n=h<kRing?h:kRing;
#if RE4DC_PVR_LATCH>=2
        char tmp[kRing*10+8];unsigned len=0,last=~0U;   // v2: a run of one code reads "Y*100"
#else
        char tmp[kRing*4+8];unsigned len=0,last=~0U;
#endif
        for(unsigned k=h-n;k!=h;++k){
            const unsigned f=ring_frame[k%kRing];
            if(f!=last){tmp[len++]=' ';tmp[len++]=char('0'+f/10%10);tmp[len++]=char('0'+f%10);tmp[len++]=':';last=f;}
            tmp[len++]=char(ring_code[k%kRing]);
#if RE4DC_PVR_LATCH>=2
            if(ring_rep[k%kRing]>1)len+=unsigned(snprintf(tmp+len,8,"*%u",unsigned(ring_rep[k%kRing])));
#endif
        }
        tmp[len]=0;
        // Keep the newest end that fits.
        const unsigned room=size>4?size-4:0;
        snprintf(out,size,"ev%s",len>room?tmp+(len-room):tmp);
        return 1;
    }
#if RE4DC_PVR_READY_STRICT
    if(which==3){
        // PVR_READY_STRICT: expired 100 ms slices (K TA bank, Q render done, Y present fence) and the UI frames of
        // the first and the last one; "rdy K0 Q0 Y0" = the path never fired.
#if RE4DC_PVR_RECOVER
        // PVR_RECOVER: "rv <P1>/<P2> <last frame>" recoveries (render reset / TA lists) and the UI frame of the last.
        char rv[24]="";
        if(pvr_recover::p1 || pvr_recover::p2)snprintf(rv,sizeof(rv)," rv%u/%u@%u",pvr_recover::p1,pvr_recover::p2,pvr_recover::last_frame);
#else
        const char* rv="";
#endif
        if(pvr_ready::first_frame==~0U)snprintf(out,size,"rdy K0 Q0 Y0%s",rv);
        else snprintf(out,size,"rdy K%u Q%u Y%u first %u last %u%s",pvr_ready::ta_timeouts,pvr_ready::render_timeouts,
                      pvr_ready::present_timeouts,pvr_ready::first_frame,pvr_ready::last_frame,rv);
        return 1;
    }
#endif
#if RE4DC_PVR_LATCH>=2
    if(which==4){
        // SB_ISTERR bits seen since boot: e<bit>@<first UI frame>x<count>; then the largest scene since boot
        // (TA vertex bytes, OPB overflow-pool bytes) with its UI frame.
        int n=snprintf(out,size,"er");
        for(unsigned b=0;b<6 && n<int(size);++b)
            if(errors&(1U<<b))n+=snprintf(out+n,size-n," e%u@%ux%u",b,err_first[b],err_count[b]);
        if(n<int(size))snprintf(out+n,size-n," mx v%x o%x",max_vtx,max_opb);
        return 1;
    }
    if(which==5){
        // The last two closed scenes (newest first): UI frame, TA vertex bytes, OPB overflow-pool bytes at their
        // close; the render that hangs reads one of these.
        snprintf(out,size,"sc %u v%x o%x | %u v%x o%x",scene_use[0].frame,scene_use[0].vtx,scene_use[0].opb,
                 scene_use[1].frame,scene_use[1].vtx,scene_use[1].opb);
        return 1;
    }
#endif
    return 0;
}
#endif
#if RE4DC_PVR_PIPELINE
// Frame N's render and flip overlap frame N+1's CPU work. The late present/
// discard decision is unchanged (Render_swap still makes it); a presenter
// thread performs the same fence + pvr_resolve_frame() the frame owner used
// to block in. Every later PVR owner step waits for that resolution first:
// the next scene begin (single TA bank, render_completed must be clear) and,
// through re4dc_pvr_vram_fence(), any VRAM free or upload. Game threads and
// the tick order are untouched; the presenter never calls source code.
volatile unsigned present_submitted,present_resolved,present_failures;
unsigned present_reported,fence_blocked,fence_timeouts;
std::uint64_t fence_wait_us;
void present_report(){
    const unsigned failures=present_failures;
    if(failures!=present_reported){
        present_reported=failures;
        if(failures&1)re4dc_missing("native stream completion fence failed");
        if(failures&2)re4dc_missing("native source presentation resolve failed");
    }
}
#if RE4DC_PVR_PIPELINE==2
// PIPELINE=2: no presenter thread. Needs the KOS async-present patch
// (pvr_present_async/pvr_present_wait): the decision is recorded at scene
// finish and applied by the render-done IRQ; the flip happens in the vblank
// IRQ. With TA_DOUBLEBUF=1 frame N+1's TA input also overlaps frame N's render.
// Render faults are only known after the decision, so TA_GUARD>=2 discards on
// TA faults of this scene and render faults of earlier scenes.
void start_presenter(){
    re4dc_log("native frame pipeline: KOS async present (IRQ-applied decision, vblank flip) ta=%s\n",RE4DC_TA_DOUBLEBUF?"double-buffered":"single-bank");
}
void present_fence(){
#if RE4DC_PACE_PRESENT
    re4dc_steady_wait(); // a deferred picture is handed to KOS first (pace_present.cpp)
#endif
    if(!pvr_present_pending())return;
#if RE4DC_PVR_LATCH
    latch::put('f');
#endif
    const auto start=timer_us_gettime64();
    // The timed waiter can become runnable before the render/vblank IRQ
    // completes, then resume with its old error after presentation finished.
    // Recheck ownership before treating that timeout as an unfinished frame.
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    {
    re4dc::wc24::WaitScope wc24_wait(re4dc::wc24::PvrWait);
#endif
#if RE4DC_PVR_READY_STRICT
    if(pvr_ready::present_wait()<0 && pvr_present_pending()){   // keeps waiting past 100 ms (bounded)
#else
    if(pvr_present_wait()<0 && pvr_present_pending()){
#endif
        ++fence_timeouts;present_failures=present_failures|1;
#if RE4DC_PVR_LATCH
        latch::put('X');latch::bump(latch::kX);
#endif
    }
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    }
#endif
    ++fence_blocked;fence_wait_us+=timer_us_gettime64()-start;
    present_resolved=present_submitted;
    present_report();
}
void present_submit(bool present,unsigned ta_faults){
#if RE4DC_TA_GUARD
    present=guard_present(present,ta_faults);
#else
    (void)ta_faults;
#endif
    present_submitted=present_submitted+1;
#if RE4DC_PACE_PRESENT
    if(WC24_QUEUE_RESULT(re4dc_steady_present(present),present))return; // Steady: released at its target field by pace_present.cpp
    auto post=[](bool p){const int irq=irq_disable();const int r=WC24_POST_RESULT(pvr_present_async(p),p);if(r==0)re4dc_present_posted(p);irq_restore(irq);return r;};
    if(post(present)<0){
        present_fence();
        if(post(present)<0){present_failures=present_failures|2;present_report();}
    }
#else
    // One decision is outstanding at a time: frame N's flip normally happened
    // long before frame N+1 finishes, so this rarely blocks.
    if(WC24_POST_RESULT(pvr_present_async(present),present)<0){
        present_fence();
        if(WC24_POST_RESULT(pvr_present_async(present),present)<0){present_failures=present_failures|2;present_report();}
    }
#endif
}
#else
semaphore_t present_request;
volatile bool present_decision;
volatile unsigned present_ta_faults;
alignas(32) unsigned char presenter_stack[4096];
void* presenter_main(void*){
    for(;;){
        sem_wait(&present_request);
        bool present=present_decision;
        unsigned failure=0;
        {
            PvrWaiter waiter;
            if(re4dc::gpu::quiesce()!=re4dc::gpu::FenceResult::ready)failure=1;
            else {
#if RE4DC_TA_GUARD
                present=guard_present(present,present_ta_faults);
#endif
                if(pvr_resolve_frame(present)<0)failure=2;
            }
        }
        const int o=irq_disable();
        present_failures=present_failures|failure;present_resolved=present_resolved+1;
        genwait_wake_all((void*)&present_resolved);
        irq_restore(o);
    }
    return nullptr;
}
void start_presenter(){
    sem_init(&present_request,0);
    kthread_attr_t a{};
    a.stack_size=sizeof(presenter_stack);a.stack_ptr=presenter_stack;
    a.prio=2;a.label="re4dc-present";a.create_detached=true;
    kthread_t* t=thd_create_ex(&a,presenter_main,nullptr);
    if(!t)re4dc_missing("native presenter thread create failed");
    re4dc_log("native frame pipeline: presenter tid=%d prio=2 stack=static:%u\n",t?int(t->tid):-1,unsigned(sizeof(presenter_stack)));
}
void present_fence(){
    if(present_resolved==present_submitted)return;
    const auto start=timer_us_gettime64();
    {
        PvrWaiter waiter;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        re4dc::wc24::WaitScope wc24_wait(re4dc::wc24::PvrWait);
#endif
        const int o=irq_disable();
        while(present_resolved!=present_submitted)
            if(genwait_wait((void*)&present_resolved,"re4dc present fence",250)<0)++fence_timeouts;
        irq_restore(o);
    }
    ++fence_blocked;fence_wait_us+=timer_us_gettime64()-start;
    present_report();
}
void present_submit(bool present,unsigned ta_faults){
    present_decision=present;present_ta_faults=ta_faults;present_submitted=present_submitted+1;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    // Queued decision; the presenter may still reject it. PAGEFLIP is separate.
    re4dc::wc24::decision_posted(present);
#endif
    sem_signal(&present_request);
    // Let the higher-priority presenter reach its render-done wait now, as
    // OSResumeThread yields to a resumed higher-priority thread.
    thd_pass();
}
#endif
#endif

#if !RE4DC_WORLD_AUTOSORT
constexpr float overlay_depth(){return 1.0f;}
#endif

#if RE4DC_PVR_STREAM
// One serial PVR owner, no extra framebuffer or whole-scene packet copy.
// KOS's opt-in manual flip preserves the source's late presentation decision.
bool stream_scene,stream_aborted,stream_retire;
#if RE4DC_WORLD_AUTOSORT
bool world_autosort;
unsigned overlay_layer;
// Ordinary world 1/w is below one. Screen-space strips use increasing constant
// depths so hardware sorting retains their emission order without changing UVs.
float overlay_depth(){return world_autosort?float(2U+overlay_layer++):1.0f;}
#endif
unsigned stream_model_bytes,stream_peak_bytes,stream_discards,stream_black_frames;
#if RE4DC_TA_DIRECT
bool direct_open;               // re4dc_model_direct_begin/end: SQ held
unsigned direct_parts,direct_slots;
#endif
pvr_list_t stream_list=PVR_LIST_TR_POLY;
#if RE4DC_PS2_WORLD_DRAW
unsigned stream_closed_lists,stream_pass_logs,world_barrier_logs;
#endif
#if RE4DC_D349_RENDERER_STACK
pvr_list_t desired_list=PVR_LIST_OP_POLY;
#endif
#if RE4DC_TA_HASH
// TA_HASH: FNV-1a over 32-bit words per list (OP, OP mod, TR, TR mod, PT) of one scene; a list
// switch folds a marker into the list being opened, so order and list membership both count.
std::uint32_t ta_hash_h[5];
unsigned ta_hash_words[5];
#if RE4DC_TA_HASH == 4
// TA_HASH=4 (lane cap16 2026-10-16, the CAP_COMPARE benchmark's translucency page; count only: no hashing, no per-frame
// log, the per-vertex hash copies in native_static.cpp / native_actor_fast.cpp are left out): the ISP/TSP parameter bytes
// each display list wrote, from the TA's own write pointer (TA_ITP_CURRENT, 0x005F8138) read at every list open and at
// the scene close. Presented scenes add their words per list to re4dc_ta_count[0..4] (0 op, 1 op mod, 2 tr, 3 tr mod,
// 4 pt) and 1 to [5]; bench.cpp reads them per one-second window. Flycast does not move this register (its KOS stats
// read 0 there): a console number.
} // namespace (re4dc_ta_count at file scope: bench.cpp reads it through re4dc_ta_count_ptr)
extern "C" { unsigned re4dc_ta_count[6]; unsigned* re4dc_ta_count_ptr(void){return re4dc_ta_count;} }
namespace {
unsigned ta4_list=5,ta4_pos,ta4_words[5];
inline unsigned ta4_itp(){return *(volatile std::uint32_t*)0xA05F8138;}
void ta4_mark(unsigned list){const unsigned p=ta4_itp();if(ta4_list<5 && p>=ta4_pos)ta4_words[ta4_list]+=(p-ta4_pos)/4;ta4_list=list;ta4_pos=p;}
#endif
#if RE4DC_TA_HASH == 3
std::uint32_t ta_hash_pend[5][4];  // TA_HASH=3: a header's words 0..3, hashed once a vertex follows it
bool ta_hash_pending[5];
void ta_hash_reset(){for(unsigned i=0;i<5;++i){ta_hash_h[i]=2166136261u;ta_hash_words[i]=0;ta_hash_pending[i]=false;}}
#elif RE4DC_TA_HASH == 4
void ta_hash_reset(){for(unsigned i=0;i<5;++i){ta_hash_h[i]=2166136261u;ta_hash_words[i]=0;ta4_words[i]=0;}ta4_list=5;}
#else
void ta_hash_reset(){for(unsigned i=0;i<5;++i){ta_hash_h[i]=2166136261u;ta_hash_words[i]=0;}}
#endif
void ta_hash_marker(pvr_list_t list){const std::uint32_t w=0xF00D0000u|(unsigned)list;re4dc_ta_hash(&w,4);}
#if defined(RE4DC_MCHECK_PT) && RE4DC_MCHECK_PT
// MCHECK_PT=1: observe packet boundaries per list before checking actual PT
// headers. v2 rejects malformed/truncated packets; a 64-byte payload tail is
// never interpreted as a fresh PCW. No emitted data or TA_HASH input is changed.
re4dc_pt_audit::Decoder pt_audit;
void pt_audit_feed(unsigned list,const void* data,unsigned bytes,void* ra){
    pt_audit.feed(list,data,bytes,reinterpret_cast<std::uintptr_t>(ra));
}
void pt_audit_scene(unsigned fr,bool present){
    const auto s=pt_audit.finish_scene();
    if(s.bad || s.invalid || s.incomplete || (s.headers && !(fr%30))){
        re4dc_log("pt_audit: v=2 frame=%u present=%u pt_hdr=%u bad=%u invalid=%u incomplete=%u why=%u w0=%08x w2=%08x ra=%p\n",
            fr,present?1u:0u,s.headers,s.bad,s.invalid,s.incomplete,s.reason,s.w0,s.w2,
            reinterpret_cast<void*>(s.caller));
    }
}
#endif
#if RE4DC_TA_BIN_DIAG
// TA_BIN_DIAG=1 (issue 9, test builds only; needs TA_HASH): replays every 32-byte TA burst the TA_HASH hooks see
// through a model of the hardware tiler (20x15 tiles of 32x32): one object pointer per strip object of up to six
// triangles (bounding box per triangle) or per sprite, in every tile it touches; object pointer blocks of the
// list's size (OP/TR TA_OPB_BINS words, PT 8 with TREE_IMPOSTOR), the last word of a block reserved for the link,
// one word for the end-of-list. Logs per scene the overflow-pool bytes it needs against the pool KOS reserves
// (opb_overflow_count x the initial blocks), the deepest tile per list, the translucent triangles in the
// busiest tile (the ISP autosort load) and an ISP/TSP parameter estimate against the TA vertex bank.
#if RE4DC_TA_MATERIAL_DIAG
namespace tamat {
re4dc_tamat::Census census;
// 0 unclassified, 1 PS2 world, 2 source models, 3 UI, 4 effects.
// These are submission paths; offline source manifests classify actual assets.
unsigned source,packet_source,scene;
struct Scope { unsigned saved; explicit Scope(unsigned s):saved(source){source=s;} ~Scope(){source=saved;} };
void header(unsigned list,const std::uint32_t* q){
    const unsigned old=census.count;
    const unsigned i=census.select(list,source,q[2],q[3],(q[0]&8)!=0);
    if(i==re4dc_tamat::None || i<old)return;
    auto& row=census.rows[i];
    if(!row.textured){row.resolved=1;return;}
    const unsigned address=(q[3]&0x001fffffU)<<3;
    for(const auto& e:entries){
        if(!e.valid || !e.package.upload_complete())continue;
        const unsigned n=e.package.header().texture_count;
        for(unsigned t=0;t<n;++t){
            if((unsigned(reinterpret_cast<std::uintptr_t>(e.package.pvr_texture(t)))&0x007fffffU)==address){
                row.crc=e.key.crc;row.fnv=e.key.fnv;row.resolved=1;return;
            }
        }
    }
}
void report(unsigned frame,bool present){
    // Read the snapshot already taken at this render's begin. Native frame
    // numbers can skip source ticks under PACE_FAST, so they cannot align views.
    const auto& v=render_source_begin;
    unsigned camera[8],player[6],motion;
    static_assert(sizeof(unsigned)==sizeof(float), "source bit readback");
    std::memcpy(camera,v.camera,sizeof(camera));
    std::memcpy(player,v.player,sizeof(player));
    std::memcpy(&motion,&v.motion_frame,sizeof(motion));
    // re4dc_log has a 256-byte formatter. Each versioned record is bounded
    // below that even with full-width counters; offline tools require both.
    re4dc_log("taview: v=2 f=%u scene=%u p=%u tick=%u room=%03x system=%08x stop=%08x rf=%08x/%08x/%08x/%08x sf=%08x/%08x/%08x/%08x\n",
        frame,scene,present?1u:0u,v.tick,v.room,v.system,v.stop,
        v.room_flags[0],v.room_flags[1],v.room_flags[2],v.room_flags[3],
        v.status[0],v.status[1],v.status[2],v.status[3]);
    re4dc_log("taview pose: v=2 f=%u scene=%u p=%u cam=%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x pl=%08x/%08x/%08x/%08x/%08x/%08x motion=%08x/%08x\n",
        frame,scene,present?1u:0u,
        camera[0],camera[1],camera[2],camera[3],camera[4],camera[5],camera[6],camera[7],
        player[0],player[1],player[2],player[3],player[4],player[5],motion,v.motion_state);
    unsigned areas[5]{};const bool valid_area=census.integer_fill(areas);if(!valid_area)++census.invalid;
    for(unsigned i=0;i<census.count;++i){const auto& r=census.rows[i];if(!r.tris)continue;
        re4dc_log("tamat: f=%u scene=%u p=%u l=%u source=%u key=%08x-%08x tcw=%08x tsp=%08x tris=%u fill=%u resolved=%u textured=%u\n",
            frame,scene,present?1u:0u,r.list,r.source,r.crc,r.fnv,r.tcw,r.tsp,r.tris,valid_area?unsigned(r.fill):0u,r.resolved,r.textured);
    }
    re4dc_log("tamat total: f=%u scene=%u p=%u rows=%u overflow=%u invalid=%u orphan=%u tris=%u/%u/%u fill=%u/%u/%u\n",
        frame,scene,present?1u:0u,census.count,census.overflow,census.invalid,census.orphans,
        census.tris[0],census.tris[2],census.tris[4],areas[0],areas[2],areas[4]);
    ++scene;census.clear();
}
}
#endif
namespace tabin {
constexpr unsigned kTw=20,kTh=15,kTiles=kTw*kTh;
unsigned short ent[5][kTiles];
unsigned short trtri[kTiles];
unsigned stamp[kTiles],objid;
struct L{ unsigned hdr_words,vtx_words,param_words; bool sprite,vtx64,half,hdr64_pending,tex,uv16,offset,vol; unsigned nv,tri_in_obj;
          float x[2],y[2]; unsigned objs,tris,verts,short_strips,orphans; };
L ls[5];
unsigned scene_param,scene_wild,scene_mismatch,scene_lists_seen;
unsigned max_pool,max_param,max_trtile,scenes;
// Translucent fill (Phase 2 B6): the screen area (pixels, clipped to 640x480) of every translucent triangle / sprite
// the tiler model sees, and of the effect sprites by kind (re4dc_effect_sprite: pad bit 2 PS2 haze, bit 4 GameCube
// mist sheet, else other effects; an M2 octagon counts 0.671 of its square). Logged per scene as "tabin fill:".
// fill_tr counts translucent polygons only: PVR sprites (the effect sprites) and the M2 octagon strips (skip_fill)
// are counted at re4dc_effect_sprite, so the scene total is tr + haze + mist + fx.
float fill_tr,fill_haze,fill_mist,fill_fx;bool skip_fill;
float clip_area(const float* xs,const float* ys,unsigned n){
    float ax[12],ay[12],bx[12],by[12];unsigned m=n;
    for(unsigned i=0;i<n;++i){ax[i]=xs[i];ay[i]=ys[i];}
    for(unsigned e=0;e<4 && m;++e){
        unsigned k=0;
        for(unsigned i=0;i<m;++i){
            const unsigned j=(i+1)%m;
            const float pi=e==0?ax[i]:e==1?640.0f-ax[i]:e==2?ay[i]:480.0f-ay[i];
            const float pj=e==0?ax[j]:e==1?640.0f-ax[j]:e==2?ay[j]:480.0f-ay[j];
            if(pi>=0 && k<12){bx[k]=ax[i];by[k]=ay[i];++k;}
            if((pi>=0)!=(pj>=0) && k<12){const float t=pi/(pi-pj);bx[k]=ax[i]+t*(ax[j]-ax[i]);by[k]=ay[i]+t*(ay[j]-ay[i]);++k;}
        }
        m=k;for(unsigned i=0;i<m;++i){ax[i]=bx[i];ay[i]=by[i];}
    }
    float a=0;for(unsigned i=0;i<m;++i){const unsigned j=(i+1)%m;a+=ax[i]*ay[j]-ax[j]*ay[i];}
    return a<0?-a*0.5f:a*0.5f;
}
// The previous scene's busiest translucent tile: which callers of re4dc_ta_hash (return address) put triangles
// there, and the header words (TSP, TCW) of the biggest contributor.
void* cur_ra;
unsigned hot_tile=~0U,hot_op_tile=~0U;
struct Contrib{ void* ra; unsigned tris,tsp,tcw; };
Contrib hot[8],hot_op[8];
unsigned cur_tsp[5],cur_tcw[5];
void contrib(Contrib* c,unsigned add,unsigned list){
    for(unsigned i=0;i<8;++i){
        if(c[i].ra==cur_ra){c[i].tris+=add;return;}
        if(!c[i].ra){c[i].ra=cur_ra;c[i].tris=add;c[i].tsp=cur_tsp[list];c[i].tcw=cur_tcw[list];return;}
    }
}
unsigned blocks_words(unsigned list){
#if RE4DC_TREE_IMPOSTOR
    if(list==4)return 8;
#endif
#if RE4DC_MV_SHADOWS
    if(list==1)return unsigned(RE4DC_MV_OPB_BINS);
#endif
    return list==0||list==2?unsigned(RE4DC_TA_OPB_BINS):(list==4?16U:0U);
}
inline int clampt(float v,int hi){ if(!(v==v))return -1; if(v<0)return 0; const int t=int(v)>>5; return t>hi?hi:t; }
void add_box(unsigned list,float x0,float x1,float y0,float y1,unsigned tris){
    if(!(x0==x0&&x1==x1&&y0==y0&&y1==y1)){++scene_wild;return;}
    if(x0<-8192||x1>8192||y0<-8192||y1>8192)++scene_wild;
    if(x1<0||y1<0||x0>=640||y0>=480)return;   // outside the global tile clip
    const int tx0=clampt(x0,kTw-1),tx1=clampt(x1,kTw-1),ty0=clampt(y0,kTh-1),ty1=clampt(y1,kTh-1);
    for(int ty=ty0;ty<=ty1;++ty)for(int tx=tx0;tx<=tx1;++tx){
        const unsigned t=unsigned(ty)*kTw+unsigned(tx);
        if(stamp[t]!=objid){stamp[t]=objid;if(ent[list][t]<65535)++ent[list][t];if(list==0 && t==hot_op_tile)contrib(hot_op,1,0);}
        if(list==2){trtri[t]=static_cast<unsigned short>(std::min(65535U,unsigned(trtri[t])+tris));if(t==hot_tile)contrib(hot,tris,2);}
    }
}
void obj_begin(L& s){ ++objid; ++s.objs; s.tri_in_obj=0; scene_param+=s.hdr_words; }
#if RE4DC_MV_SHADOWS
// MV_SHADOWS: the opaque modifier volume list. A header (type 4) then 64-byte triangles (type 7): counted as one
// object per triangle in every tile its box touches (an upper bound for the TA's grouping), 3 + 9 parameter words.
float mv_tri[5];bool mv_second;
void feed_mod(const std::uint32_t* q){
    L& s=ls[1];
    const float* f=reinterpret_cast<const float*>(q);
    if(mv_second){
        mv_second=false;const float cy=f[0];
        obj_begin(s);++s.tris;++s.verts;scene_param+=9;
        add_box(1,std::min({mv_tri[0],mv_tri[2],mv_tri[4]}),std::max({mv_tri[0],mv_tri[2],mv_tri[4]}),
                std::min({mv_tri[1],mv_tri[3],cy}),std::max({mv_tri[1],mv_tri[3],cy}),1);
        return;
    }
    const unsigned t=q[0]>>29;
    if(t==4u){if(((q[0]>>24)&7)!=1)++scene_mismatch;s.hdr_words=3;return;}
    if(t!=7u)return;
    if(!s.hdr_words){++s.orphans;}
    mv_tri[0]=f[1];mv_tri[1]=f[2];mv_tri[2]=f[4];mv_tri[3]=f[5];mv_tri[4]=f[7];mv_second=true;
}
#endif
void feed_block(unsigned list,const std::uint32_t* q){
#if RE4DC_MV_SHADOWS
    if(list==1){feed_mod(q);return;}
#endif
    L& s=ls[list];
    if(s.half){
#if RE4DC_TA_MATERIAL_DIAG
        if(s.sprite)tamat::census.sprite_second(list,reinterpret_cast<const float*>(q));
#endif
        s.half=false; return; }                 // second half of a 64-byte vertex / header
    if(s.hdr64_pending){ s.hdr64_pending=false; return; }
    const std::uint32_t pcw=q[0];const unsigned t=pcw>>29;
    if(t==4u||t==5u){
        if(((pcw>>24)&7)!=list)++scene_mismatch;
        cur_tsp[list]=q[2];cur_tcw[list]=q[3];
#if RE4DC_TA_MATERIAL_DIAG
        tamat::header(list,q);
#endif
        s.sprite=t==5u; s.tex=pcw&8; s.uv16=pcw&1; s.offset=pcw&4; s.vol=pcw&64; const unsigned col=(pcw>>4)&3;
        if(s.nv>0 && s.nv<3)++s.short_strips;
        s.nv=0;
        s.hdr64_pending=!s.sprite && ((!s.vol && col==2 && s.tex && s.offset) || (s.vol && col==2));
        s.vtx64=s.sprite || (s.tex && col==1) || (s.vol && s.tex);
        s.hdr_words=3+(s.vol?2:0);
        s.vtx_words=3+(s.tex?(s.uv16?1:2):0)+1+(s.offset?1:0);
        if(s.vol)s.vtx_words+=(s.tex?(s.uv16?1:2):0)+1+(s.offset?1:0);
        return;
    }
    if(t!=7u)return;                                      // EOL, user clip, object list set
    if(!s.hdr_words){++s.orphans;return;}
    const float* f=reinterpret_cast<const float*>(q);
    if(s.sprite){
        // A, B, C xyz in words 1..9, D xy in 10..11: words 8.. are in the second half (not kept), so use A and B
        // and C's x (word 7); D is C's mirror in practice: take the box of A, B and C.x with y of A/B.
        s.half=true;
#if RE4DC_TA_MATERIAL_DIAG
        tamat::census.sprite_first(list,f);
#endif
        const float xs[3]={f[1],f[4],f[7]},ys[2]={f[2],f[5]};
        obj_begin(s); ++s.tris;
        add_box(list,std::min({xs[0],xs[1],xs[2]}),std::max({xs[0],xs[1],xs[2]}),std::min(ys[0],ys[1]),std::max(ys[0],ys[1]),2);
        scene_param+=4*4; ++s.verts;
        return;
    }
    if(s.vtx64)s.half=true;
    ++s.verts;
    const float x=f[1],y=f[2];
    if(s.nv>=2){
        if(s.tri_in_obj==0||s.tri_in_obj==6){ obj_begin(s); scene_param+=2*s.vtx_words; }
        ++s.tri_in_obj; ++s.tris; scene_param+=s.vtx_words;
        add_box(list,std::min({x,s.x[0],s.x[1]}),std::max({x,s.x[0],s.x[1]}),std::min({y,s.y[0],s.y[1]}),std::max({y,s.y[0],s.y[1]}),1);
        #if RE4DC_TA_MATERIAL_DIAG
        {const float tx[3]={s.x[0],s.x[1],x},ty[3]={s.y[0],s.y[1],y};tamat::census.add(list,tx,ty,3,1);}
#endif
        if(list==2 && !skip_fill){const float tx[3]={s.x[0],s.x[1],x},ty[3]={s.y[0],s.y[1],y};
                     if(x==x&&y==y&&s.x[0]==s.x[0]&&s.x[1]==s.x[1])fill_tr+=clip_area(tx,ty,3);}
    }
    s.x[0]=s.x[1];s.y[0]=s.y[1];s.x[1]=x;s.y[1]=y;++s.nv;
    if(pcw&(1u<<28)){ if(s.nv<3)++s.short_strips; s.nv=0; s.tri_in_obj=0; }
}
void feed(unsigned list,const void* data,unsigned bytes){
    if(bytes<32||list>4)return;
    const auto* w=static_cast<const std::uint32_t*>(data);
    scene_lists_seen|=1u<<list;
    for(unsigned b=0;b<bytes/32;++b)feed_block(list,w+b*8);
}
unsigned pool_now(){
    unsigned pool=0;
    for(unsigned l=0;l<5;++l){
        const unsigned n=blocks_words(l);if(!n)continue;
        for(unsigned t=0;t<kTiles;++t){const unsigned e=ent[l][t];if(e+1>n)pool+=((e+1-(n-1)+(n-2))/(n-1))*n*4;}
    }
    return pool;
}
// A VRAM fence inside an open scene (a texture upload): how much of the scene the TA holds at this point, to set
// a console photo's TA registers (read at such a fence) against the scene's final numbers.
void partial(unsigned fr){
    re4dc_log("tabin fence: f=%u param=%u pool=%u tris=%u\n",fr,scene_param*4,pool_now(),ls[0].tris+ls[2].tris+ls[4].tris);
}
void scene_end(unsigned fr,bool present){
    unsigned pool=0,maxent[5]={0,0,0,0,0},total[5]={0,0,0,0,0},maxtr=0,objs[5],tris=0,shorts=0,orph=0;
    for(unsigned l=0;l<5;++l){
        const unsigned n=blocks_words(l);objs[l]=ls[l].objs;tris+=ls[l].tris;shorts+=ls[l].short_strips;orph+=ls[l].orphans;
        for(unsigned t=0;t<kTiles;++t){
            const unsigned e=ent[l][t];total[l]+=e;maxent[l]=std::max(maxent[l],e);
            if(n && e+1>n){ const unsigned slots=e+1,first=n-1; pool+=((slots-first+(n-2))/(n-1))*n*4; }
        }
    }
    unsigned trt=0,opt=0;
    for(unsigned t=0;t<kTiles;++t){
        if(trtri[t]>maxtr){maxtr=trtri[t];trt=t;}
        if(ent[0][t]>ent[0][opt])opt=t;
    }
#if RE4DC_MV_SHADOWS
    const unsigned limit=(2*unsigned(RE4DC_TA_OPB_BINS)+blocks_words(4)+blocks_words(1))*4*kTiles*unsigned(RE4DC_TA_OPB_OVERFLOW+RE4DC_TA_HEADROOM);
    re4dc_log("tabin mod: f=%u obj=%u ent=%u deep=%u\n",fr,objs[1],total[1],maxent[1]);
#else
    const unsigned limit=(2*unsigned(RE4DC_TA_OPB_BINS)+blocks_words(4))*4*kTiles*unsigned(RE4DC_TA_OPB_OVERFLOW+RE4DC_TA_HEADROOM);
#endif
    const unsigned param=scene_param*4;
    const bool peak=pool>max_pool||param>max_param||maxtr>max_trtile;
    if(peak){
        // i9d: the overflow pool this scene needs with other OP / TR block sizes (8, 16, 32 words; PT as built), to
        // price OPB layouts: a layout fits when op+tr+pt <= (op_n+tr_n+pt_n words) x 4 x 300 x overflow count.
        unsigned need[2][3]={{0,0,0},{0,0,0}},pt=0;
        for(unsigned t=0;t<kTiles;++t){
            for(unsigned k=0;k<3;++k){
                const unsigned n=8U<<k;
                for(unsigned j=0;j<2;++j){const unsigned e=ent[j*2][t];if(e+1>n)need[j][k]+=((e+1-(n-1)+(n-2))/(n-1))*n*4;}
            }
            const unsigned n4=blocks_words(4),e4=ent[4][t];
            if(n4 && e4+1>n4)pt+=((e4+1-(n4-1)+(n4-2))/(n4-1))*n4*4;
        }
        re4dc_log("tabin alt: f=%u op8=%u op16=%u op32=%u tr8=%u tr16=%u tr32=%u pt%u=%u\n",fr,need[0][0],need[0][1],need[0][2],
                  need[1][0],need[1][1],need[1][2],blocks_words(4),pt);
    }
    // Every 30th scene (or a new peak): the attribution of the previous scene's busiest tiles.
    if((!(scenes%30) || peak) && hot_tile!=~0U){
        char b[220];int n=snprintf(b,sizeof(b),"tabin hot: tr tile %u,%u",hot_tile%kTw,hot_tile/kTw);
        for(unsigned i=0;i<8 && hot[i].ra && n<int(sizeof(b));++i)
            n+=snprintf(b+n,sizeof(b)-n," %08x:%u/%08x/%08x",unsigned(reinterpret_cast<std::uintptr_t>(hot[i].ra)),hot[i].tris,hot[i].tsp,hot[i].tcw);
        re4dc_log("%s\n",b);
        n=snprintf(b,sizeof(b),"tabin hot: op tile %u,%u",hot_op_tile%kTw,hot_op_tile/kTw);
        for(unsigned i=0;i<8 && hot_op[i].ra && n<int(sizeof(b));++i)
            n+=snprintf(b+n,sizeof(b)-n," %08x:%u/%08x/%08x",unsigned(reinterpret_cast<std::uintptr_t>(hot_op[i].ra)),hot_op[i].tris,hot_op[i].tsp,hot_op[i].tcw);
        re4dc_log("%s\n",b);
    }
    hot_tile=maxtr?trt:~0U;hot_op_tile=ent[0][opt]?opt:~0U;
    std::memset(hot,0,sizeof(hot));std::memset(hot_op,0,sizeof(hot_op));
    ++scenes;
    max_pool=std::max(max_pool,pool);max_param=std::max(max_param,param);max_trtile=std::max(max_trtile,maxtr);
    re4dc_log("tabin: f=%u p=%d obj=%u/%u/%u ent=%u/%u/%u deep=%u/%u/%u pool=%u/%u param=%u/%u trtile=%u tris=%u short=%u orphan=%u wild=%u mism=%u%s\n",
        fr,present?1:0,objs[0],objs[2],objs[4],total[0],total[2],total[4],maxent[0],maxent[2],maxent[4],pool,limit,param,
        unsigned(RE4DC_TA_VERTEX_BYTES),maxtr,tris,shorts,orph,scene_wild,scene_mismatch,peak?" PEAK":"");
    re4dc_log("tabin fill: f=%u poly=%u haze=%u mist=%u fx=%u\n",fr,unsigned(fill_tr),unsigned(fill_haze),unsigned(fill_mist),unsigned(fill_fx));
    fill_tr=fill_haze=fill_mist=fill_fx=0;
#if RE4DC_TA_MATERIAL_DIAG
    for(const auto& state:ls)tamat::census.incomplete(state.half || state.hdr64_pending);
    tamat::report(fr,present);
#endif
    std::memset(ent,0,sizeof(ent));std::memset(trtri,0,sizeof(trtri));
    for(auto& s:ls)s=L{};
#if RE4DC_MV_SHADOWS
    mv_second=false;
#endif
    scene_param=scene_wild=scene_mismatch=scene_lists_seen=0;
}
}
#endif
#endif
#if RE4DC_TA_DOUBLEBUF
// TA double buffering at run time (design-doublebuf, KOS pvr_set_vbuf_doublebuf): on in play, off
// while the sub-screen backing holds bank 1's vertex buffer (re4dc_ui_ta_single_bank at backing
// open), back on at the first scene after the backing closed (no extra fence: the single-bank
// stream_open fenced already).
bool ta_double=true,ta_double_wanted=false;
#endif
#if defined(RE4DC_LETTERBOX_CLIP) && RE4DC_LETTERBOX_CLIP
void stream_send(const void* data,unsigned bytes);
#endif
#if defined(RE4DC_PS2_PVS) && RE4DC_PS2_PVS
unsigned pvs23_scene_epoch=0; // observation identity only; no renderer ownership
#endif
#if defined(RE4DC_BACKFACE_ROOMS) && RE4DC_BACKFACE_ROOMS
extern "C" void re4dc_bf_room_update();   // native_static.cpp (BACKFACE_ROOMS, lane fix-hideout23)
#endif
void stream_open() { RE4DC_TAIL_GPU_SCOPE(open);
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    sob33_barrier(re4dc::sob33::SceneBoundary);
#endif
#if RE4DC_GC_ASSET_GATE
    gcasset_packet_reset();
#endif
#if defined(RE4DC_BACKFACE_ROOMS) && RE4DC_BACKFACE_ROOMS
    re4dc_bf_room_update();
#endif
#if RE4DC_PACE_CATCHUP
    // A movie presents its own picture (re4dc_ui_movie_present_now) even inside a skipped tick.
#if RE4DC_ROUTE_MOVIES
    if(pace_skip_frame && !movie_texture)re4dc_missing("pace: emission on a skipped tick");
#else
    if(pace_skip_frame)re4dc_missing("pace: emission on a skipped tick");
#endif
#endif
#if RE4DC_PVR_PIPELINE
#if RE4DC_TA_DOUBLEBUF
    if(!ta_double){
        present_fence(); // single bank: previous scene flipped/discarded, TA bank and back buffer free
        if(ta_double_wanted){
            if(pvr_set_vbuf_doublebuf(true)<0)re4dc_missing("TA double buffer switch refused");
            ta_double=true;ta_double_wanted=false;
#if RE4DC_PVR_LATCH
            latch::put('D');
#endif
            re4dc_log("ta bank: double at frame %u" "\n",frame);
        }
    }
#if RE4DC_NATIVE_FOG
    else if(re4dc_fog_frame_pending())present_fence(); // the render in flight reads the fog registers
    re4dc_fog_frame();
#endif
#else
    present_fence(); // previous scene flipped/discarded: TA bank and back buffer free
#if RE4DC_NATIVE_FOG
    re4dc_fog_frame(); // fog registers: the previous scene no longer renders
#endif
#endif
#endif
#if defined(RE4DC_PVR_RTT) && RE4DC_PVR_RTT
    re4dc_rtt_render_pending();   // PVR_RTT: last frame's wanted render targets, before this scene
#endif
    pvr_scene_begin();
#if RE4DC_PACE_PRESENT
    re4dc_steady_ta_wait(); // Steady: the TA bank wait for a held picture's flip, timed as a wait (pace_present.cpp)
#endif
#if RE4DC_PS2_WORLD_DRAW
    stream_closed_lists=0;
#endif
#if RE4DC_TA_GUARD
    guard_scene_begin();
#endif
#if RE4DC_D349_RENDERER_STACK
    stream_list=desired_list;
#else
    stream_list=PVR_LIST_TR_POLY;
#endif
#if RE4DC_PVR_LATCH
    {bool failed;latch::list_begin_timed(stream_list,failed);if(failed)re4dc_missing("native stream list begin failed");}
    latch::put('S');latch::bump(latch::kS);
#else
    if(pvr_list_begin(stream_list)<0)re4dc_missing("native stream list begin failed");
#endif
#if RE4DC_TA_HASH
    ta_hash_reset();ta_hash_marker(stream_list);
#endif
    // Do not retain the main thread's SQ mutex across source task dispatch or
    // file/audio services. Each synchronous packet transfer reacquires it.
    sq_unlock();stream_scene=true;
#if defined(RE4DC_PS2_PVS) && RE4DC_PS2_PVS
    if(!++pvs23_scene_epoch)++pvs23_scene_epoch;
#endif
#if defined(RE4DC_LETTERBOX_CLIP) && RE4DC_LETTERBOX_CLIP
#if RE4DC_TA_MATERIAL_DIAG
    { tamat::Scope source_scope(3); re4dc_lbx_open(int(stream_list),stream_send); }
#else
    re4dc_lbx_open(int(stream_list),stream_send); // platform/letterbox_clip.cpp: the opaque bars
#endif
#endif
#if RE4DC_WORLD_AUTOSORT
    // list_begin, not scene_begin, waits for and acquires this TA bank.
    // Set its tiles only after that wait, never while the old bank renders.
    world_autosort=false;overlay_layer=0;pvr_set_presort_mode(true);
#endif
}
#if RE4DC_D349_RENDERER_STACK
#if RE4DC_UI_POLY_ORDER
// UI models interleave with source quads. All polygons share the presorted TR
// list in that frame; modifier volumes retain their separate list ownership.
static pvr_list_t ui_order_polygon_list(pvr_list_t list){
    if(ui_order && (list==PVR_LIST_OP_POLY || list==PVR_LIST_PT_POLY || list==PVR_LIST_TR_POLY))
        return PVR_LIST_TR_POLY;
    return list;
}
static void ui_order_polygon_header(pvr_poly_hdr_t& header){
    // Change only the local command's list bits. In particular, keep KOS's
    // source-list alpha default, depth, blend and texture-alpha unchanged.
    const auto list=static_cast<pvr_list_t>((header.cmd>>24)&7U);
    header.cmd=(header.cmd&~(7U<<24))|(unsigned(ui_order_polygon_list(list))<<24);
}
#endif
void stream_select(pvr_list_t list){
#if RE4DC_UI_POLY_ORDER
    list=ui_order_polygon_list(list);
#endif
#if RE4DC_ACTOR_TRANSACTION_DIAG
    const bool avd_note=list!=stream_list || !stream_scene;
#endif
    AVD_IF_EVENT(avd_note,ListRequest,nullptr,nullptr,unsigned(list));
    desired_list=list;
    if(!stream_scene){stream_open();AVD_IF_EVENT(avd_note,ListResult,nullptr,nullptr,unsigned(list));return;}
    if(stream_list==list){AVD_IF_EVENT(avd_note,ListResult,nullptr,nullptr,unsigned(list));return;}
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    sob33_barrier(re4dc::sob33::ListBoundary);
#endif
    // End the old list once. Never reopen it or replay source ModelRender.
#if RE4DC_PS2_WORLD_DRAW
    if(stream_closed_lists&(1u<<unsigned(list))){
#if RE4DC_CLOSED_PASS_KEEP
        // CLOSED_PASS_KEEP (game30.mk): stay in the open list; the TA keeps the list type latched at its first header.
        static unsigned kept;
        if(kept<16 || !(kept&255))
            re4dc_log("PS2PASS kept frame=%u from=%u to=%u mask=%x finished=%u ra=%p count=%u\n",frame,unsigned(stream_list),
                unsigned(list),stream_closed_lists,unsigned(source_draws_finished),__builtin_return_address(0),kept+1);
        ++kept;
        AVD_IF_EVENT(avd_note,ListResult,nullptr,nullptr,unsigned(list));
        return;
#else
        re4dc_log("PS2PASS closed frame=%u from=%u to=%u mask=%x finished=%u\n",
            frame,unsigned(stream_list),unsigned(list),stream_closed_lists,unsigned(source_draws_finished));
        re4dc_missing("native closed pass requested");
#endif
    }
    if(stream_pass_logs<12 || !(frame%120)){
        ++stream_pass_logs;
        re4dc_log("PS2PASS switch frame=%u from=%u to=%u mask=%x\n",
            frame,unsigned(stream_list),unsigned(list),stream_closed_lists);
    }
#endif
    sq_lock((void*)PVR_TA_INPUT);
#if RE4DC_PS2_WORLD_DRAW
    if(pvr_list_finish()<0)re4dc_missing("native pass transition failed");
    stream_closed_lists|=1u<<unsigned(stream_list);
    if(pvr_list_begin(list)<0)re4dc_missing("native pass transition failed");
#else
    if(pvr_list_finish()<0 || pvr_list_begin(list)<0)re4dc_missing("native pass transition failed");
#endif
    sq_unlock();stream_list=list;
    AVD_IF_EVENT(avd_note,ListResult,nullptr,nullptr,unsigned(list));
#if RE4DC_TA_HASH
    ta_hash_marker(list);
#endif
#if defined(RE4DC_LETTERBOX_CLIP) && RE4DC_LETTERBOX_CLIP
    re4dc_lbx_open(int(list),stream_send); // a frame whose first list was not the opaque one
#endif
}
#endif
#if RE4DC_WORLD_AUTOSORT
void world_sort_begin(){
    // Subscreen and pickup models deliberately interleave with their 2D art.
    if(world_autosort || ui_order)return;
#if RE4DC_ROUTE_MOVIES
    if(movie_texture && movie_picture)return;
#endif
    pvr_set_presort_mode(false);world_autosort=true;
}
#endif
#if RE4DC_POST_F00_DIAG
// POST_F00_DIAG (test builds): the frame of the last queued post, opaque packets sent after it in that frame
// (drawn below it on the PVR, above it on the GameCube) and UI quads queued before it (drawn above it here).
unsigned post_diag_frame_no=~0U,post_diag_op_after,post_diag_ui_before,post_diag_ui_frames,post_diag_ui_max,post_diag_frames;
void post_diag_frame(){
    post_diag_frame_no=frame;++post_diag_frames;post_diag_ui_before+=nquad;
    if(nquad){++post_diag_ui_frames;post_diag_ui_max=std::max(post_diag_ui_max,nquad);}
    if(post_diag_frames%600==0)
        re4dc_log("post f00 diag: frames=%u ui_before=%u (frames %u, max %u) op_after=%u frame=%u\n",post_diag_frames,
                  post_diag_ui_before,post_diag_ui_frames,post_diag_ui_max,post_diag_op_after,frame);
}
#endif
// SOB33_STREAM_SEND_BEGIN
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
void stream_send33(const void* data,unsigned bytes,unsigned skip_header) {
    // Asset auditing consumes the complete logical model packet. Only the
    // physical TA stream and its byte/hash counters omit the repeated header.
    const void* const logical_data=data;const unsigned logical_bytes=bytes;
    data=static_cast<const unsigned char*>(data)+skip_header;bytes-=skip_header;
#else
void stream_send(const void* data,unsigned bytes) {
#endif
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    const re4dc::dsa24::Scope dsa_submit(re4dc::dsa24::Submit);
#endif
    re4dc::profile::Scope profile_scope(stream_list==PVR_LIST_OP_POLY?re4dc::profile::SubmitOP:
        stream_list==PVR_LIST_PT_POLY?re4dc::profile::SubmitPT:re4dc::profile::SubmitTR);
    ++frame_pvr_calls;frame_pvr_bytes+=bytes;
#if RE4DC_POST_F00_DIAG
    if(post_diag_frame_no==frame && stream_list==PVR_LIST_OP_POLY)++post_diag_op_after;
#endif
    if(!stream_scene)stream_open();
    sq_lock((void*)PVR_TA_INPUT);
#if RE4DC_TA_HASH
    re4dc_ta_hash(data,bytes);
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    DFA26_HIT(SubmitCopy)
#endif
    re4dc::render::submit_pvr(data,bytes);
    sq_unlock();
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    RE4DC_GCA_PACKET(logical_data,logical_bytes,unsigned(stream_list),gcasset_packet_consumer);
#else
    RE4DC_GCA_PACKET(data,bytes,unsigned(stream_list),gcasset_packet_consumer);
#endif
#if RE4DC_TA_GUARD
    guard_account(1,bytes/32-1); // every call is one header + its vertices
#endif
}
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
void stream_send(const void* data,unsigned bytes) {
    sob33_barrier(re4dc::sob33::StreamSend);stream_send33(data,bytes,0);
}
#endif
// SOB33_STREAM_SEND_END
#if RE4DC_MV_SHADOWS
// MV_SHADOWS (game30.mk; mv_shadow.cpp): the frame's shadow volumes go into the opaque modifier volume list, opened
// once after every other list of a presented scene (a closed list is never reopened). re4dc_mv_emit calls
// re4dc_ui_mv_send once per caster (a header pair and its 64-byte triangles).
extern "C" void re4dc_mv_emit(unsigned frame);
unsigned mv_sends,mv_bytes,mv_scenes;
bool mv_open;
#endif
#if defined(RE4DC_SHADOW_BLOB) && RE4DC_SHADOW_BLOB
// SHADOW_BLOB (game30.mk; blob_shadow.cpp): the ground blobs go into the TR list at the end of a presented scene whose
// world sorts per pixel (WORLD_AUTOSORT), before the MV_SHADOWS volume list closes it. re4dc_blob_emit calls
// re4dc_ui_blob_send once per caster (a header and its strips).
extern "C" void re4dc_blob_emit(unsigned frame);
unsigned blob_sends,blob_bytes;
#endif
#if defined(RE4DC_MCHECK_SAFE) && RE4DC_MCHECK_SAFE
void safe_audit_scene(bool present);
#endif
void stream_close(bool present) {
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    sob33_barrier(re4dc::sob33::SceneBoundary);
#endif
    RE4DC_PROFILE_SCOPE(PresentFence);
#if RE4DC_UI_FRAG_WINDOW==2
    if(frag_discard){present=false;frag_discard=false;} // UI_FRAG_WINDOW: this frame released textures its scene used
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
    if(present && !re4dc_r11f_present(frame,source_draws_finished,stream_aborted))present=false;
#endif
    if(!stream_scene)stream_open();
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();present=false;}
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
    if(present && !re4dc_r11f_present(frame,source_draws_finished,stream_aborted))present=false;
#endif
#if defined(RE4DC_SHADOW_BLOB) && RE4DC_SHADOW_BLOB
    if(present && !stream_aborted && !direct_open && world_autosort)re4dc_blob_emit(frame);
#endif
#if RE4DC_MV_SHADOWS
    if(present && !stream_aborted && !direct_open){mv_open=false;re4dc_mv_emit(frame);if(mv_open)++mv_scenes;}
#endif
#if RE4DC_TA_GUARD
    const unsigned ta_faults=guard_scene_end();
#else
    const unsigned ta_faults=0;
#endif
    (void)ta_faults;
#if RE4DC_TA_BIN_DIAG
    tabin::scene_end(frame,present);
#elif RE4DC_TA_HASH == 4
    ta4_mark(5);if(present){for(unsigned i=0;i<5;++i)re4dc_ta_count[i]+=ta4_words[i];++re4dc_ta_count[5];}
#elif RE4DC_TA_HASH
    re4dc_log("ta_hash: frame=%u present=%u op=%08x/%u tr=%08x/%u pt=%08x/%u mod=%08x/%u,%08x/%u\n",frame,present?1u:0u,
              ta_hash_h[0],ta_hash_words[0],ta_hash_h[2],ta_hash_words[2],ta_hash_h[4],ta_hash_words[4],
              ta_hash_h[1],ta_hash_words[1],ta_hash_h[3],ta_hash_words[3]);
#endif
#if RE4DC_PVR_LATCH>=2
    latch::scene_close();
#endif
#if defined(RE4DC_LETTERBOX_CLIP) && RE4DC_LETTERBOX_CLIP
    re4dc_lbx_close(); // platform/letterbox_clip.cpp: tile row clip in the region array of the bank being filled
#endif
#if defined(RE4DC_MCHECK_PT) && RE4DC_MCHECK_PT
    pt_audit_scene(frame,present);
#endif
#if defined(RE4DC_BACKFACE_CENSUS) && RE4DC_BACKFACE_CENSUS
    re4dc_bfc_scene(frame,present?1:0);
#endif
#if defined(RE4DC_MCHECK_SAFE) && RE4DC_MCHECK_SAFE
    safe_audit_scene(present);
#endif
    sq_lock((void*)PVR_TA_INPUT); RE4DC_TAIL_GPU_SCOPE(close);
#if RE4DC_CABIN_COMPLETE_HANDOFF
    if(pvr_list_finish()<0 || pvr_scene_finish()<0){
        if(movie_cabin_ui_busy && movie_texture)movie_cabin_ui_close_fault=movie_cabin_ui_epoch;
        re4dc_missing("native stream finish failed");
    }
#else
    if(pvr_list_finish()<0 || pvr_scene_finish()<0)re4dc_missing("native stream finish failed");
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    re4dc::wc24::scene_finished(); // finished game scene, including a later discard
#endif
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    re4dc::dsa24::scene_finished();
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
    // pvr_scene_finish can wait. Revalidate immediately before presentation.
    if(present && !re4dc_r11f_present(frame,source_draws_finished,stream_aborted))present=false;
#endif
    stream_scene=false;
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    // Last decision, after source/UI/shadow drains, after the final yielding scene finish.
    // The receipt is revalidated even if a prior barrier already flushed PT/TR.
    if(!re4dc_source_world_present(frame,source_draws_finished,stream_aborted || !present))present=false;
#endif

#if RE4DC_PVR_LATCH
    latch::put(present?'c':'d');latch::bump(latch::kC);
#endif
#if RE4DC_PVR_PIPELINE
    present_submit(present,ta_faults); // resolved by the presenter; fenced before reuse
#else
    {
#if RE4DC_PVR_FAST_WAKE
    PvrWaiter waiter;
#endif
    if(re4dc::gpu::quiesce()!=re4dc::gpu::FenceResult::ready)
        re4dc_missing("native stream completion fence failed");
#if RE4DC_TA_GUARD
    const bool shown=guard_present(present,ta_faults);
#else
    const bool shown=present;
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    {
    re4dc::wc24::WaitScope wc24_wait(re4dc::wc24::PvrWait);
#endif
    if(WC24_POST_RESULT(pvr_resolve_frame(shown),shown)<0)re4dc_missing("native source presentation resolve failed");
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    }
#endif
    }
#endif
    if(!present)++stream_discards;
}
#endif
#if RE4DC_PERF_HUD || (defined(RE4DC_RENDER_OPTION) && RE4DC_RENDER_OPTION)
// On-screen timing for real consoles (a GDEMU/ODE setup has no serial or BBA
// console, and the RAM log is unreadable there). Untextured TR quads at the
// end of each presented frame; photograph or film the screen. Bars at 4 px/ms
// with ticks at 16.7 / 33.3 / 50 ms, value left of each bar (7-segment, in
// 0.1 ms; TA row in KiB, bar = share of the vertex buffer). Rows, top down:
//   white   flip-to-flip interval (KOS stats: the displayed frame time)
//   green   CPU frame period (re4dc_ui_begin to re4dc_ui_begin)
//   yellow  CPU busy from frame begin to this present
//   cyan    PVR render time of the last scene (real fill/sort cost on HW)
//   magenta present wait of the last frame (fence or blocking resolve)
//   orange  TA parameter bytes of the last scene (red: overflow/fault)
std::uint64_t hud_begin,hud_begin_prev;
struct HudBatch { alignas(32) pvr_vertex_t v[128]; unsigned n=1; };
#if defined(RE4DC_MCHECK_SAFE) && RE4DC_MCHECK_SAFE
void safe_audit_note(const HudBatch& b);
#endif
void hud_flush(HudBatch& b){
#if RE4DC_TA_MATERIAL_DIAG
    tamat::Scope source_scope(3);
#endif
#if defined(RE4DC_MCHECK_SAFE) && RE4DC_MCHECK_SAFE
    safe_audit_note(b);
#endif
    if(b.n>1)stream_send(b.v,b.n*32);b.n=1;}
void hud_rect(HudBatch& b,float x,float y,float w,float h,std::uint32_t argb){
    if(b.n+4>128)hud_flush(b);
    const float xs[4]={x,x,x+w,x+w},ys[4]={y+h,y,y+h,y};
    const float layer=overlay_depth();
    for(unsigned k=0;k<4;++k){
        auto& v=b.v[b.n++];
        v.flags=k==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;
        v.x=RE4DC_UI_X(xs[k]);v.y=RE4DC_UI_Y(ys[k]);v.z=layer;v.u=v.v=0;v.argb=argb;v.oargb=0;
    }
}
void hud_number(HudBatch& b,float x,float y,unsigned value,bool tenths,std::uint32_t argb){
    static const unsigned char seg[10]={0x3f,0x06,0x5b,0x4f,0x66,0x6d,0x7d,0x07,0x7f,0x6f};
    constexpr float W=7,H=12,T=2,P=10;
    value=std::min(value,99999U);
    for(int d=0;d<5;++d){
        const unsigned digit=value%10;
        const float dx=x+(4-d)*P;
        if(d>(tenths?1:0) && value==0)break;           // "0.0" / "0" minimum
        value/=10;
        const unsigned m=seg[digit];
        if(m&1)hud_rect(b,dx,y,W,T,argb);
        if(m&2)hud_rect(b,dx+W-T,y,T,H/2,argb);
        if(m&4)hud_rect(b,dx+W-T,y+H/2,T,H/2,argb);
        if(m&8)hud_rect(b,dx,y+H-T,W,T,argb);
        if(m&16)hud_rect(b,dx,y+H/2,T,H/2,argb);
        if(m&32)hud_rect(b,dx,y,T,H/2,argb);
        if(m&64)hud_rect(b,dx,y+H/2-T/2,W,T,argb);
        if(d==0 && tenths)hud_rect(b,dx-3,y+H-T,2,T,argb);
    }
}
#if defined(RE4DC_RENDER_OPTION) && RE4DC_RENDER_OPTION
// RENDER_OPTION speed display (pace.cpp): the counter at the top right (fps, game speed %, test builds CPU %) and the
// 2 s note after R + START (four boxes: Off, VMU, Screen, Both), 7-segment quads of the PERF_HUD path.
extern "C" int re4dc_speed_screen(unsigned v[3]);
extern "C" int re4dc_speed_note(int* speed);
HudBatch speed_batch;
#if defined(RE4DC_PHASE_METER) && RE4DC_PHASE_METER
// PHASE_METER=1 (T12 Phases disc, 2026-10-15; display / log only): a second column left of the speed counter, in
// 0.1 ms (mean over the GAME_TICK_LOG window, the game's own ProcessTickGet stamps, tick_log.cpp), top to bottom:
//   GPU render (PACE_VMU_GPU), render mode (0 Standard, 1 FSAA),
//   logic (setup .. TaskScheduler without EspMove), effects move (EspMove), effects trans (EspTrans),
//   objects / actors trans (objTrans + ShadowTrans + MirrorTrans + ClothTrans), other trans (IdSys, Trans rest, Dvd,
//   sound), post (messages, fades, OT draw), draw remain (iTask + Render_done: TA end / PVR wait), vblank wait + swap,
//   frame total. One "PHASES:" log line per window carries the same values by name.
extern "C" int re4dc_tick_log_snapshot(const char** name, unsigned* avg_us, unsigned* max_us, int max, unsigned* seq);
extern "C" unsigned re4dc_speed_gpu10(void);
extern "C" int re4dc_quality_render(void);
#if defined(RE4DC_PMC_ROW) && RE4DC_PMC_ROW
extern "C" int re4dc_pmc_row(unsigned* code, unsigned* val10);  // pace.cpp
#endif
#if defined(RE4DC_DISC_READ_METER) && RE4DC_DISC_READ_METER
extern "C" int re4dc_disc_meter_hud(unsigned* lit, unsigned* music, unsigned* rate, unsigned* load_ms);  // dvd_read_safe.cpp
extern "C" int re4dc_disc_meter_loading(void);
#endif
constexpr int kPhaseRows=11;
unsigned phase_v[kPhaseRows];unsigned phase_seq=~0U;
void phase_refresh(){
    const char* nm[32];unsigned avg[32];unsigned seq=0;
    const int n=re4dc_tick_log_snapshot(nm,avg,nullptr,32,&seq);
    if(seq==phase_seq || n<=0)return;
    phase_seq=seq;
    auto get=[&](const char* k)->unsigned{for(int i=0;i<n;++i)if(nm[i] && !std::strcmp(nm[i],k))return avg[i];return 0U;};
    const unsigned logic=get("logic"),esp_move=get("EspMove"),esp_trans=get("EspTrans");
    const unsigned objs=get("objTrans")+get("ShadowTrans")+get("MirrorTrans")+get("ClothTrans");
    const unsigned trans=get("trans"),post=get("post"),cpu=get("cpu"),remain=get("remain"),total=get("total");
    const unsigned other=trans>esp_trans+objs?trans-esp_trans-objs:0;
    const unsigned draw=remain>cpu?remain-cpu:0,vbl=total>remain?total-remain:0;
    auto ms10=[](unsigned us)->unsigned{return (us+50)/100;};
    phase_v[0]=re4dc_speed_gpu10();
    phase_v[1]=unsigned(re4dc_quality_render()==1);
    phase_v[2]=ms10(logic>esp_move?logic-esp_move:0);phase_v[3]=ms10(esp_move);phase_v[4]=ms10(esp_trans);
    phase_v[5]=ms10(objs);phase_v[6]=ms10(other);phase_v[7]=ms10(post);phase_v[8]=ms10(draw);phase_v[9]=ms10(vbl);
    phase_v[10]=ms10(total);
    re4dc_log("PHASES: gpu=%u render=%u logic=%u fxmove=%u fxtrans=%u objs=%u other=%u post=%u draw=%u vblank=%u total=%u (0.1 ms)\n",
        phase_v[0],phase_v[1],phase_v[2],phase_v[3],phase_v[4],phase_v[5],phase_v[6],phase_v[7],phase_v[8],phase_v[9],phase_v[10]);
}
#endif
void speed_draw(){
    unsigned v[3];
    int s;
#if defined(RE4DC_PHASE_METER) && RE4DC_PHASE_METER
    phase_refresh();   // the PHASES: log line each window, also while the counter is off
#endif
    const bool counter=re4dc_speed_screen(v)!=0,note=re4dc_speed_note(&s)!=0;
#if defined(RE4DC_DISC_READ_METER) && RE4DC_DISC_READ_METER
    const bool meter_load=re4dc_disc_meter_loading()!=0;
    if(!counter && !note && !meter_load)return;
#else
    if(!counter && !note)return;
#endif
    HudBatch& b=speed_batch;b.n=1;
    pvr_poly_cxt_t c;pvr_poly_cxt_col(&c,PVR_LIST_TR_POLY);
    c.gen.culling=PVR_CULLING_NONE;c.depth.comparison=PVR_DEPTHCMP_ALWAYS;c.depth.write=PVR_DEPTHWRITE_DISABLE;
    pvr_poly_hdr_t header;pvr_poly_compile(&header,&c);
    std::memcpy(&b.v[0],&header,sizeof(header));
#if defined(RE4DC_LETTERBOX_CLIP) && RE4DC_LETTERBOX_CLIP
    // letterbox_clip.cpp (b): at 640x480 tile row 0 (y 0..31) renders no translucent list under the top bar, which
    // cut the counter's first row on consoles (issue #26); start below it.
    constexpr float SY=34;
#else
    constexpr float SY=24;
#endif
    if(counter){
        hud_number(b,566,SY,v[0],true,0xe0ffffffU);
        hud_number(b,566,SY+18,v[1],false,0xe0ffd0a0U);
#if RE4DC_PACE_DEBUG
        hud_number(b,566,SY+36,v[2],false,0xe0a0d0ffU);
#endif
#if defined(RE4DC_PHASE_METER) && RE4DC_PHASE_METER
        phase_refresh();
        static const std::uint32_t kPhaseColour[kPhaseRows]={0xe080ff80U,0xe0ffff60U,0xe0ffffffU,0xe0ff9060U,0xe0ffb090U,
            0xe0a0d0ffU,0xe0c0c0c0U,0xe0e0a0ffU,0xe080ffffU,0xe0909090U,0xe0ffffffU};
        for(int k=0;k<kPhaseRows;++k)hud_number(b,500,SY+k*18,phase_v[k],k!=1,kPhaseColour[k]);
#endif
#if defined(RE4DC_EM35_DIAG) && RE4DC_EM35_DIAG
        // EM35_DIAG=1 (em35_diag.h; diagnostic): one row per live Mendez half (top orange: whole body, below pink: upper
        // body), left to right: r_no_0 x100 + r_no_1, r_no_2, motion index, motion frame, seconds on this step with a
        // still motion frame, game frames since his last move() (0 or 1 = he is being moved).
        for(unsigned t=0;t<2;++t){
            const Re4dcEm35Diag& d=re4dc_em35_diag[t];
            if(!d.live)continue;
            const float y=SY+120+t*18;
            const std::uint32_t col=t?0xe0ff80ffU:0xe0ffa040U;
            hud_number(b,40,y,(d.r>>24)*100+((d.r>>16)&0xFF),false,col);
            hud_number(b,100,y,(d.r>>8)&0xFF,false,col);
            hud_number(b,160,y,d.mot,false,col);
            hud_number(b,220,y,unsigned(d.frame10>0?d.frame10:0),true,col);
            hud_number(b,280,y,d.same/3,true,col);
            hud_number(b,340,y,re4dc_em35_diag_polls-d.last_poll,false,col);
        }
#endif
#if defined(RE4DC_PMC_ROW) && RE4DC_PMC_ROW
        {   // PMC_ROW: event code (25 D-miss freeze, 24 I-miss freeze, 4 / 5 OC read / write misses, 8 IC misses), value
            unsigned code=0,val=0;
            if(re4dc_pmc_row(&code,&val)){
                hud_number(b,440,SY+kPhaseRows*18,code,false,0xe0ff6060U);
                hud_number(b,500,SY+kPhaseRows*18,val,true,0xe0ff6060U);
            }
        }
#endif
    }
#if defined(RE4DC_DISC_READ_METER) && RE4DC_DISC_READ_METER
    if(counter || meter_load){   // DISC_READ_METER: also during room loads, where the speed counter hides
        // the read marker (green: a GD-ROM read in flight, orange: one ran since the last drawn frame, dim: none) with
        // the music stream's reads as a blue bar under it, then reads/s, KB/s and game blocked ms/s (without the music
        // stream), then the room-entry load time in ms (5 s); during a load: reads, KB, blocked ms and ms so far
        unsigned lit=0,music=0,rate[3]={},load=0;
        const int room=re4dc_disc_meter_hud(&lit,&music,rate,&load);
        hud_rect(b,40,64,20,20,lit==2?0xf040ff40U:lit==1?0xf0ffa020U:0x40ffffffU);
        if(music)hud_rect(b,40,86,20,4,0xf04080ffU);
        constexpr float RY=SY+(kPhaseRows+1)*18;
        hud_number(b,380,RY,rate[0],false,0xe060ff60U);
        hud_number(b,440,RY,rate[1],false,0xe060ff60U);
        hud_number(b,500,RY,rate[2],false,0xe060ff60U);
        if(room)hud_number(b,500,RY+18,load,false,0xe0ffff60U);
    }
#endif
#if defined(RE4DC_SPEED_VMU_OFF) && RE4DC_SPEED_VMU_OFF
    const int boxes=2;   // SPEED_VMU_OFF (pace.mk, issue #29): Off, Screen
#elif defined(RE4DC_VMU_CONTEXT) && RE4DC_VMU_CONTEXT
    const int boxes=3;   // VMU_CONTEXT: Off, VMU, Screen (no Both)
#else
    const int boxes=4;
#endif
    if(note)for(int k=0;k<boxes;++k)hud_rect(b,40.0f+k*36,40.0f,28.0f,16.0f,k==s?0xf0ffff40U:0x60ffffffU);
    hud_flush(b);
}
#if (defined(RE4DC_BENCHMARK) && RE4DC_BENCHMARK) || (defined(RE4DC_QA_BANNER) && RE4DC_QA_BANNER)
// QA_MENU=1 (qamenu.mk, RE4DC_QA_BANNER): the same banner with the QA disc name, on the title screens only.
// BENCHMARK=1 (bench.mk; benchmark disc only): the banner "BENCHMARK DISC - NOT THE GAME" on every presented frame,
// white BIOS font (bfont 12x24) on red in a 512x32 RGB565 texture (32 KiB of VRAM, written once at the first frame
// straight into texture memory with 16-bit stores, as KOS's pvr_txr_load_ex does: no RAM copy, the image does not
// grow; no banner if the allocation fails), one quad at the top centre, inside the top letterbox bar and below tile
// row 0 (y 32..60: LETTERBOX_CLIP renders no translucent list in row 0).
extern "C" const char* re4dc_bench_banner(void);   // bench.cpp (qa_menu.cpp with QA_MENU)
extern "C" int re4dc_qa_banner_on(void);           // qa_menu.cpp (QA_MENU only)
pvr_ptr_t bench_vram;bool bench_failed;unsigned bench_w;
void bench_banner_draw(){
    constexpr unsigned W=512,H=32;
    if(bench_failed)return;
    if(!bench_vram){
        bench_vram=pvr_mem_malloc(W*H*2);
        if(!bench_vram){bench_failed=true;re4dc_log("bench banner: no VRAM\n");return;}
        volatile unsigned short* t=reinterpret_cast<volatile unsigned short*>(bench_vram);
        for(unsigned i=0;i<W*H;++i)t[i]=0x9000U;
        const char* text=re4dc_bench_banner();
        bfont_draw_str_ex(reinterpret_cast<unsigned short*>(bench_vram)+4*W+8,W,0xFFFFU,0x9000U,16,1,text);
        bench_w=std::min(W,unsigned(strlen(text))*12U+16U);
        re4dc_log("bench banner: '%s' vram=%p w=%u frame=%u\n",text,(void*)bench_vram,bench_w,frame);
    }
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,PVR_LIST_TR_POLY,PVR_TXRFMT_RGB565|PVR_TXRFMT_NONTWIDDLED,W,H,bench_vram,PVR_FILTER_NONE);
    c.gen.culling=PVR_CULLING_NONE;c.depth.comparison=PVR_DEPTHCMP_ALWAYS;c.depth.write=PVR_DEPTHWRITE_DISABLE;
    c.blend.src=PVR_BLEND_ONE;c.blend.dst=PVR_BLEND_ZERO;c.gen.fog_type=PVR_FOG_DISABLE;
    alignas(32) unsigned char packet[sizeof(pvr_poly_hdr_t)+4*sizeof(pvr_vertex_t)];
    pvr_poly_compile(reinterpret_cast<pvr_poly_hdr_t*>(packet),&c);
    auto* v=reinterpret_cast<pvr_vertex_t*>(packet+sizeof(pvr_poly_hdr_t));
    const float w=float(bench_w),x0=(640.0f-w)*0.5f,y0=32,h=28,u1=w/float(W),v0=2.0f/H,v1=30.0f/H;
    const float xs[4]={x0,x0,x0+w,x0+w},ys[4]={y0+h,y0,y0+h,y0},us[4]={0,0,u1,u1},vs[4]={v1,v0,v1,v0};
    const float layer=overlay_depth();
    for(unsigned k=0;k<4;++k){
        v[k].flags=k==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;v[k].x=RE4DC_UI_X(xs[k]);v[k].y=RE4DC_UI_Y(ys[k]);v[k].z=layer;
        v[k].u=us[k];v[k].v=vs[k];v[k].argb=0xffffffffU;v[k].oargb=0;
    }
    stream_send(packet,sizeof(packet));
}
#endif
#if defined(RE4DC_MCHECK_SAFE) && RE4DC_MCHECK_SAFE
// MCHECK_SAFE=1 (mcheck.mk, test builds only): the bounding box (screen pixels) of every quad the speed display
// flushes in a scene, logged at scene close with the render size, the tile grid and the tile rows LETTERBOX_CLIP
// took the translucent lists from in that scene (letterbox_clip.cpp; bit 0 row 0, bit 1 the last row; declared at
// file scope at the top: an extern "C" object declared in this unnamed namespace links to a mangled stub).
float safe_x0,safe_y0,safe_x1,safe_y1;bool safe_seen;unsigned safe_logs,safe_last_key;
void safe_audit_note(const HudBatch& b){
    if(&b!=&speed_batch)return;
    for(unsigned i=1;i<b.n;++i){
        const float x=b.v[i].x,y=b.v[i].y;
        if(!safe_seen){safe_x0=safe_x1=x;safe_y0=safe_y1=y;safe_seen=true;continue;}
        safe_x0=std::min(safe_x0,x);safe_x1=std::max(safe_x1,x);safe_y0=std::min(safe_y0,y);safe_y1=std::max(safe_y1,y);
    }
}
void safe_audit_scene(bool present){
    if(!safe_seen)return;
    safe_seen=false;
#if defined(RE4DC_LETTERBOX_CLIP) && RE4DC_LETTERBOX_CLIP
    const unsigned rows=re4dc_lbx_rows_last;
#else
    const unsigned rows=0;
#endif
    const unsigned key=rows|(unsigned(pvr_state.th)<<4)|(unsigned(safe_y0)<<12);
    if(key==safe_last_key && (frame%30) && safe_logs>8)return;
    safe_last_key=key;++safe_logs;
    re4dc_log("safe_area: frame=%u present=%u speed=%d,%d,%d,%d screen=%dx%d tiles=%ux%u lbx_rows=%u\n",frame,
              present?1u:0u,int(safe_x0),int(safe_y0),int(safe_x1+0.999f),int(safe_y1+0.999f),int(RE4DC_SCREEN_W),
              int(RE4DC_SCREEN_H),unsigned(pvr_state.tw),unsigned(pvr_state.th),rows);
}
#endif
#endif
#endif
#if RE4DC_PERF_HUD
HudBatch hud_batch; // 4 KiB .bss (PERF_HUD only), not the caller's stack
#ifndef RE4DC_IO_PROBE
#define RE4DC_IO_PROBE 0
#endif
#if RE4DC_IO_PROBE
extern "C" int re4dc_ioprobe_hud(unsigned v[4]);
extern "C" int re4dc_iocount_hud(unsigned v[4]);   // io_wrap.cpp: last door
#endif
#if RE4DC_QUALITY
extern "C" int re4dc_quality_hud(unsigned v[2]);   // platform/quality.cpp
#endif
#ifndef RE4DC_VMU_DEBUG_SLOT
#define RE4DC_VMU_DEBUG_SLOT 0
#endif
#if RE4DC_VMU_DEBUG_SLOT
extern "C" int re4dc_dbgslot_hud(unsigned v[2]);   // dbgslot_bridge.cpp
#endif
#if RE4DC_PACE_CATCHUP
extern "C" int re4dc_pace_hud(unsigned v[2]);      // pace.cpp: game speed %, drawn fps x10
#define RE4DC_PACE_HUD_ROW 1
#else
#define RE4DC_PACE_HUD_ROW 0
#endif
void hud_draw(unsigned flip_us,unsigned render_us,unsigned wait_us,unsigned ta_bytes,unsigned ta_capacity,bool ta_fault){
    HudBatch& b=hud_batch;b.n=1;
    pvr_poly_cxt_t c;pvr_poly_cxt_col(&c,PVR_LIST_TR_POLY);
    c.gen.culling=PVR_CULLING_NONE;c.depth.comparison=PVR_DEPTHCMP_ALWAYS;c.depth.write=PVR_DEPTHWRITE_DISABLE;
    pvr_poly_hdr_t header;pvr_poly_compile(&header,&c);
    std::memcpy(&b.v[0],&header,sizeof(header));
    const std::uint64_t now=timer_us_gettime64();
    const unsigned period=hud_begin_prev?unsigned(hud_begin-hud_begin_prev):0,busy=unsigned(now-hud_begin);
    constexpr float X=40,BX=100,Y=324,R=18,PX=4.0f/1000.0f,MAXW=480;
    const unsigned us[5]={flip_us,period,busy,render_us,wait_us};
    const std::uint32_t colors[6]={0xe0ffffffU,0xe040ff40U,0xe0ffff40U,0xe040ffffU,0xe0ff40ffU,ta_fault?0xf0ff2020U:0xe0ffa040U};
    hud_rect(b,X-4,Y-4,BX-X+MAXW+8,(6+RE4DC_IO_PROBE+RE4DC_QUALITY+RE4DC_VMU_DEBUG_SLOT+RE4DC_PACE_HUD_ROW)*R+6,0x90000000U);   // backdrop
    for(unsigned r=0;r<5;++r){
        hud_number(b,X,Y+r*R,(us[r]+50)/100,true,colors[r]);
        hud_rect(b,BX,Y+r*R+2,std::min(MAXW,float(us[r])*PX),8,colors[r]);
    }
    const float ta=ta_capacity?std::min(1.0f,float(ta_bytes)/float(ta_capacity)):0.0f;
    hud_number(b,X,Y+5*R,ta_bytes/1024,false,colors[5]);
    hud_rect(b,BX,Y+5*R+2,ta*MAXW,8,colors[5]);
    hud_rect(b,BX+MAXW,Y+5*R,1,12,0xffffffffU);          // 100% of the vertex buffer
    for(float ms:{16.683f,33.367f,50.05f})hud_rect(b,BX+ms*1000*PX,Y-2,1,5*R,0xffffffffU);
#if RE4DC_IO_PROBE
    // IO probe row (lilac): sequential KB/s, cold 32 KiB p95 (0.1 ms), stream underruns
    // under load, worst underrun deficit (0.1 ms). Blank until the probe has run.
    unsigned io[4];
    if(re4dc_ioprobe_hud(io))for(unsigned k=0;k<4;++k)hud_number(b,X+k*60,Y+6*R,io[k],k==1||k==3,0xe0c0a0ffU);
    // Last door (orange): wall s, MB read (both 0.1), GD commands, seeks of 16 MB or more.
    if(re4dc_iocount_hud(io))for(unsigned k=0;k<4;++k)hud_number(b,X+240+k*60,Y+6*R,io[k],k<2,0xe0ffb060U);
#endif
#if RE4DC_QUALITY
    // Quality row (green): mode (1 Standard, 0 Original) and the feature word.
    unsigned qv[2];
    re4dc_quality_hud(qv);
    hud_number(b,X,Y+(6+RE4DC_IO_PROBE)*R,qv[0],false,0xe080ff80U);
    hud_number(b,X+60,Y+(6+RE4DC_IO_PROBE)*R,qv[1],false,0xe080ff80U);
#endif
#if RE4DC_VMU_DEBUG_SLOT
    // Debug slot row (orange): status (1 OK, 2 ERR, 3 BUSY, 4 NOMEM) and the debug save count.
    unsigned dv[2];
    re4dc_dbgslot_hud(dv);
    hud_number(b,X,Y+(6+RE4DC_IO_PROBE+RE4DC_QUALITY)*R,dv[0],false,0xe0ffb060U);
    hud_number(b,X+60,Y+(6+RE4DC_IO_PROBE+RE4DC_QUALITY)*R,dv[1],false,0xe0ffb060U);
#endif
#if RE4DC_PACE_CATCHUP
    // Pacing row (orange-white): game speed % and drawn fps of the last PACE window.
    unsigned pv[2];
    re4dc_pace_hud(pv);
    hud_number(b,X,Y+(6+RE4DC_IO_PROBE+RE4DC_QUALITY+RE4DC_VMU_DEBUG_SLOT)*R,pv[0],false,0xe0ffd0a0U);
    hud_number(b,X+60,Y+(6+RE4DC_IO_PROBE+RE4DC_QUALITY+RE4DC_VMU_DEBUG_SLOT)*R,pv[1],true,0xe0ffd0a0U);
#endif
    hud_flush(b);
}
#endif



unsigned image_size(const Re4dcUiImage& i) {
    unsigned bw,bh,bytes;
    switch(i.format) {
    case 0:case 8:case 14:bw=8;bh=8;bytes=32;break;
    case 1:case 2:case 9:bw=8;bh=4;bytes=32;break;
    case 3:case 4:case 5:bw=4;bh=4;bytes=32;break;
    case 6:bw=4;bh=4;bytes=64;break;
    default:return 0;
    }
    return ((i.width+bw-1)/bw)*((i.height+bh-1)/bh)*bytes;
}
#if RE4DC_COPY_LEAN
// The same reflected CRC-32 (0xEDB88320), four bits per table step instead of
// one per loop pass: identical keys (package file names) at ~1/4 the work.
constexpr unsigned kCrcNibble[16]={0x00000000U,0x1db71064U,0x3b6e20c8U,0x26d930acU,0x76dc4190U,0x6b6b51f4U,
    0x4db26158U,0x5005713cU,0xedb88320U,0xf00f9344U,0xd6d6a3e8U,0xcb61b38cU,0x9b64c2b0U,0x86d3d2d4U,0xa00ae278U,0xbdbdf21cU};
void hash_bytes(Key& k,const void* ptr,unsigned size) {
    const auto* p=(const unsigned char*)ptr;
    unsigned crc=k.crc,fnv=k.fnv;
    for(unsigned i=0;i<size;++i) {
        fnv=(fnv^p[i])*16777619U;crc^=p[i];
        crc=(crc>>4)^kCrcNibble[crc&15U];crc=(crc>>4)^kCrcNibble[crc&15U];
    }
    k.crc=crc;k.fnv=fnv;
}
#else
void hash_bytes(Key& k,const void* ptr,unsigned size) {
    const auto* p=(const unsigned char*)ptr;
    for(unsigned i=0;i<size;++i) {
        k.fnv=(k.fnv^p[i])*16777619U;k.crc^=p[i];
        for(unsigned b=0;b<8;++b) k.crc=(k.crc>>1)^(0xedb88320U & (0U-(k.crc&1)));
    }
}
#endif
bool same_image(const Re4dcUiImage& a,const Re4dcUiImage& b) {
    return a.pixels==b.pixels && a.palette==b.palette && a.width==b.width && a.height==b.height &&
           a.format==b.format && a.palette_format==b.palette_format && a.palette_bytes==b.palette_bytes;
}
#if RE4DC_COPY_LEAN
// Direct-mapped hints into sources[] / entries[] (index+1, 0 empty). A hint is
// used only after the full equality test; a miss falls back to the original
// scan. sources[] and valid entries[] never hold duplicates (both are appended
// only after a failed scan), so the hinted match is the scan's first match.
// One byte per hint while both tables fit (the default image); TEX_SLOTS above 254 widens the entry hints.
using EntryHint=std::conditional_t<(kTextureCount<255),unsigned char,unsigned short>;
unsigned char source_hint[128];EntryHint entry_hint[128];
inline unsigned source_slot(const Re4dcUiImage& i){
    const unsigned a=unsigned(reinterpret_cast<std::uintptr_t>(i.pixels))^unsigned(reinterpret_cast<std::uintptr_t>(i.palette));
    return ((a>>5)^(a>>12)^i.format)&127U;
}
static_assert(kSourceCount<255 && kTextureCount<65535);
#endif
#if RE4DC_PAD_PROMPTS
// Private immutable addresses are presentation identities, never source pixels.
// A malformed descriptor using one of these addresses is rejected, not hashed.
static Re4dcUiImage prompt_image(unsigned i) {
    return {&re4dc_binocular_art[i],nullptr,36,36,5,0xffffffffU,0};
}
static int prompt_image_key(const Re4dcUiImage& image,Key& key) {
    for(unsigned i=0;i<2;++i)if(image.pixels==&re4dc_binocular_art[i]) {
        if(!same_image(image,prompt_image(i)))return -1;
        key={re4dc_binocular_art[i].crc,re4dc_binocular_art[i].fnv};
        return 1;
    }
    return 0;
}
#endif
#if RE4DC_PAD_PROMPT_MANUAL_ART
#include "manual_pages_keys.inc"
#endif
#if RE4DC_UI_HUD_MASK
#include "include/hud_source_mask_keys.inc"
#endif
int external_image_key(const Re4dcUiImage& image,Key& external) {
#if RE4DC_UI_HUD_MASK
    const int hud=hud_mask_image_key(image,external);if(hud)return hud;
#endif
#if RE4DC_PAD_PROMPT_MANUAL_ART
    const int manual=manual_page_key(image,external);if(manual)return manual;
#endif
#if RE4DC_PAD_PROMPTS
    const int prompt=prompt_image_key(image,external);
    if(prompt)return prompt;
#endif
#if RE4DC_COARSE_LEON
    if(re4dc_coarse_actor_texture_key(&image,&external.crc,&external.fnv))return 1;
#endif
    int native=room_identities.lookup(image.pixels,image.width,image.height,image.format,external.crc,external.fnv,image.palette,image.palette_format,image.palette_bytes);
    if(!native)native=core_identities.lookup(image.pixels,image.width,image.height,image.format,external.crc,external.fnv,image.palette,image.palette_format,image.palette_bytes);
    if(!native)native=option_identities.lookup(image.pixels,image.width,image.height,image.format,external.crc,external.fnv,image.palette,image.palette_format,image.palette_bytes);
    if(!native)native=player_identities.lookup(image.pixels,image.width,image.height,image.format,external.crc,external.fnv,image.palette,image.palette_format,image.palette_bytes);
    if(!native)native=weapon_identities.lookup(image.pixels,image.width,image.height,image.format,external.crc,external.fnv,image.palette,image.palette_format,image.palette_bytes);
    for(auto& e:enemy_identities)if(!native && e.archive)
        native=e.table.lookup(image.pixels,image.width,image.height,image.format,external.crc,external.fnv,image.palette,image.palette_format,image.palette_bytes);
    return native;
}
#if defined(RE4DC_UI_HASH_DIAG) && RE4DC_UI_HASH_DIAG
// UI_HASH_DIAG (crowd.mk, test only): which images image_key() hashes texel by texel (no source-table hit, no external
// identity), per 60 UI frames: calls, bytes, nsource, and the 12 heaviest images (load()'s caller, pixels, size, format).
namespace hashdiag {
struct Rec { const void* px; const void* site; unsigned w, h, fmt, bytes, n; };
Rec rec[12]; unsigned nrec, calls, bytes, frames, full;
const void* site;
void note(const Re4dcUiImage& i, unsigned b) {
    ++calls; bytes += b;
    for (unsigned k = 0; k < nrec; ++k) if (rec[k].px == i.pixels) { ++rec[k].n; return; }
    if (nrec < 12) { rec[nrec++] = Rec{i.pixels, site, i.width, i.height, i.format, b, 1}; return; }
    unsigned lo = 0; for (unsigned k = 1; k < 12; ++k) if (rec[k].n * rec[k].bytes < rec[lo].n * rec[lo].bytes) lo = k;
    if (rec[lo].n <= 1) rec[lo] = Rec{i.pixels, site, i.width, i.height, i.format, b, 1};
}
}
#endif
#if defined(RE4DC_UI_SOURCE_LRU) && RE4DC_UI_SOURCE_LRU
// UI_SOURCE_LRU (crowd.mk; exact, render only): once sources[] is full, a new descriptor replaces the least recently
// used entry instead of being re-hashed on every lookup. A replaced entry is a later descriptor, never a key change:
// the key of a descriptor is still the hash of its texels (or its external identity) when first seen. An indexed
// image cached this way also records an FNV of its palette bytes; a hit with a changed palette is hashed again
// (exactly what the full path did). =2 (check build): every hit on a late entry hashes again and compares
// ("UISRC" lines: bad must stay 0).
unsigned source_used[kSourceCount],source_clock,source_evict,source_late_hits,source_bad;
unsigned char source_late[kSourceCount];unsigned source_pal[kSourceCount];
inline unsigned palette_fnv(const Re4dcUiImage& i){
    unsigned h=2166136261U;const unsigned char* p=(const unsigned char*)i.palette;
    for(unsigned n=0;n<i.palette_bytes;++n)h=(h^p[n])*16777619U;
    return h;
}
void hash_bytes(Key& k,const void* ptr,unsigned size);
inline Key full_hash(const Re4dcUiImage& image){
    const unsigned metadata[]={image.width,image.height,image.format,image.palette_format,image.palette_bytes};
    Key key={0xffffffffU,2166136261U};hash_bytes(key,metadata,sizeof(metadata));
    hash_bytes(key,image.pixels,image_size(image));
    if(image.palette_bytes) hash_bytes(key,image.palette,image.palette_bytes);
    key.crc=~key.crc;return key;
}
// A hit on sources[n]: 0 = use it, 1 = an indexed late entry whose palette changed (take the full path).
inline int source_hit(unsigned n,const Re4dcUiImage& image){
    if(source_late[n]){
        ++source_late_hits;
        if(source_late[n]==2 && palette_fnv(image)!=source_pal[n])return 1;
#if RE4DC_UI_SOURCE_LRU==2
        if(source_late[n]!=3 && !(full_hash(image)==sources[n].key) && source_bad++<16)
            re4dc_log("UISRC bad n=%u px=%08x %ux%u fmt=%u%s",n,(unsigned)reinterpret_cast<std::uintptr_t>(image.pixels),image.width,image.height,image.format,"\n");
        if(!(source_late_hits&4095U))re4dc_log("UISRC check late_hits=%u evict=%u bad=%u%s",source_late_hits,source_evict,source_bad,"\n");
#endif
    }
    source_used[n]=++source_clock;return 0;
}
// Insert (image, key): append while there is room (late = 0, as without the knob), else replace the LRU entry.
// kind: 1 hashed texels, 2 hashed indexed texels (palette FNV kept), 3 external / self key (not re-hashable).
inline void source_put(const Re4dcUiImage& image,const Key& key,unsigned hint,unsigned char kind){
    unsigned n;
    if(nsource<kSourceCount){n=nsource++;source_late[n]=0;}
    else{
        n=0;for(unsigned k=1;k<kSourceCount;++k)if(source_used[k]<source_used[n])n=k;
        ++source_evict;source_late[n]=kind;if(kind==2)source_pal[n]=palette_fnv(image);
    }
    sources[n]={image,key};source_used[n]=++source_clock;source_hint[hint]=(unsigned char)(n+1);
}
#endif
bool image_key(const Re4dcUiImage& image,Key& key) {
    Key external{};int native=0;
    const bool indexed=image.format==8 || image.format==9;
    // Indexed external records must qualify the CURRENT retained palette before
    // a pointer-key cache hit. A changed palette cannot reuse an old upload or
    // hash the discarded source indices. Ordinary resident images retain their
    // existing fast path. No cache entries or extra allocation are introduced.
    if(indexed)native=external_image_key(image,external);
    if(native<0){re4dc_log("native source identity: incompatible palette rejected\n");return false;}
#if RE4DC_COPY_LEAN
    const unsigned hint=source_slot(image);
    if(!native){
        const unsigned h=source_hint[hint];
#if defined(RE4DC_UI_SOURCE_LRU) && RE4DC_UI_SOURCE_LRU
        int stale=-1;
        if(h && h<=nsource && same_image(sources[h-1].image,image)){if(!source_hit(h-1,image)){key=sources[h-1].key;return true;}stale=int(h-1);}
        if(stale<0)for(unsigned n=0;n<nsource;++n) if(same_image(sources[n].image,image)) {
            if(source_hit(n,image)){stale=int(n);break;}
            source_hint[hint]=(unsigned char)(n+1);key=sources[n].key;return true;}
        if(stale>=0){   // indexed late entry, palette changed: hash as the full path does and refresh this entry
            key=full_hash(image);sources[stale].key=key;source_pal[stale]=palette_fnv(image);source_used[stale]=++source_clock;return true;}
#else
        if(h && h<=nsource && same_image(sources[h-1].image,image)){key=sources[h-1].key;return true;}
        for(unsigned n=0;n<nsource;++n) if(same_image(sources[n].image,image)) {source_hint[hint]=(unsigned char)(n+1);key=sources[n].key;return true;}
#endif
    }
#else
    if(!native)for(unsigned n=0;n<nsource;++n) if(same_image(sources[n].image,image)) {key=sources[n].key;return true;}
#endif
    if(!indexed)native=external_image_key(image,external);
    if(native<0){re4dc_log("native source identity: incompatible descriptor rejected\n");return false;}
    if(native) {
        if(identity_hits++<3)re4dc_log("native source identity: %08x-%08x (no source-texel hash)\n",external.crc,external.fnv);
#if defined(RE4DC_UI_SOURCE_LRU) && RE4DC_UI_SOURCE_LRU
        if(!indexed)source_put(image,external,hint,3);
#elif RE4DC_COPY_LEAN
        if(!indexed && nsource<kSourceCount){source_hint[hint]=(unsigned char)(nsource+1);sources[nsource++]={image,external};}
#else
        if(!indexed && nsource<kSourceCount)sources[nsource++]={image,external};
#endif
        key=external;return true;
    }
#if RE4DC_TEX_REF_SELFKEY
    // TEX_REF_SELFKEY (Makefile): an R4NREF record no registered table covers names its own package; hashing its 32
    // bytes as texels gives a key that is on no disc.
    if(!indexed && !(reinterpret_cast<std::uintptr_t>(image.pixels)&3U)){
        const unsigned* r=(const unsigned*)image.pixels;
        if(r[0]==0x524e3452U && r[1]==0x00004645U && r[4]==image.width && r[5]==image.height && r[6]==image.format){
            static unsigned selfkeys;
            key={r[2],r[3]};
            if(selfkeys++<16 || !(selfkeys&1023U))re4dc_log("native UI: ref self-key %08x-%08x %ux%u fmt=%u pix=%08x n=%u\n",key.crc,key.fnv,
                image.width,image.height,image.format,(unsigned)reinterpret_cast<std::uintptr_t>(image.pixels),selfkeys);
#if defined(RE4DC_UI_SOURCE_LRU) && RE4DC_UI_SOURCE_LRU
            source_put(image,key,hint,3);
#elif RE4DC_COPY_LEAN
            if(nsource<kSourceCount){source_hint[hint]=(unsigned char)(nsource+1);sources[nsource++]={image,key};}
#else
            if(nsource<kSourceCount)sources[nsource++]={image,key};
#endif
            return true;
        }
    }
#endif
    const unsigned metadata[]={image.width,image.height,image.format,image.palette_format,image.palette_bytes};
#if defined(RE4DC_UI_HASH_DIAG) && RE4DC_UI_HASH_DIAG
    hashdiag::note(image,image_size(image)+image.palette_bytes);if(nsource>=kSourceCount)++hashdiag::full;
#endif
    key={0xffffffffU,2166136261U};hash_bytes(key,metadata,sizeof(metadata));
    hash_bytes(key,image.pixels,image_size(image));
    if(image.palette_bytes) hash_bytes(key,image.palette,image.palette_bytes);
    key.crc=~key.crc;
#if defined(RE4DC_UI_SOURCE_LRU) && RE4DC_UI_SOURCE_LRU
    source_put(image,key,hint,indexed?2:1);
#elif RE4DC_COPY_LEAN
    if(nsource<kSourceCount){source_hint[hint]=(unsigned char)(nsource+1);sources[nsource++]={image,key};}
#else
    if(nsource<kSourceCount) sources[nsource++]={image,key};
#endif
    return true;
}
#if RE4DC_D349_RENDERER_STACK
bool model_mask_key(const Re4dcModelPart* p,Key& key){
    Key color{},mask{};
    if(!image_key(p->image,color) || !image_key(p->mask,mask))return false;
    const unsigned words[]={color.crc,color.fnv,mask.crc,mask.fnv};
    key={0xffffffffU,2166136261U};
    hash_bytes(key,"R4MPv001",8);hash_bytes(key,words,sizeof(words));key.crc=~key.crc;
    return true;
}
// A material pair whose package failed to load: its color and mask identities, once per pair, so
// the missing package can be built from the log (tools/d367/pairs_from_log.py, prepare_model_pairs).
void log_pair_miss(const Re4dcModelPart* p,const Key& key){
    static Key seen[32];static unsigned nseen=0;
    for(unsigned i=0;i<nseen && i<32;++i)if(seen[i].crc==key.crc && seen[i].fnv==key.fnv)return;
    seen[nseen++%32]=key;
    Key color{},mask{};
    if(!image_key(p->image,color) || !image_key(p->mask,mask))return;
    re4dc_log("native UI: pair missing %08x-%08x color=%08x-%08x mask=%08x-%08x %ux%u\n",key.crc,key.fnv,
              color.crc,color.fnv,mask.crc,mask.fnv,p->image.width,p->image.height);
}
#endif
#if RE4DC_TEX_RESIDENT
// Least-recently-REQUESTED eviction. A model part's lookup does not pin its
// entry (the part pins it only once committed to the scene) and a new
// unpinned upload used to get frame 0: under a full pool (room preload) it was
// the first victim of the next load in the same frame, so parts that ask for a
// texture every frame reloaded it every frame (4-5 disc reads per frame).
// A lookup now marks the entry as requested last frame: still evictable this
// frame, but after every texture nothing asked for since.
#define RE4DC_TOUCH(e) do{if(pin)(e).frame=frame;else if(frame && (e).frame+1<frame)(e).frame=frame-1;}while(0)
#else
#define RE4DC_TOUCH(e) if(pin)(e).frame=frame
#endif
#if RE4DC_TEX_RESIDENT
// TEX_RESIDENT discs fan the packages out by the first hex digit (stage.sh):
// the flat /cd/dc/tex directory (~550 packages, 17+ sectors) overflowed the
// iso9660 16-sector inode cache, so every open re-read the directory from the
// disc (~0.2 s per first-sight texture in Flycast at r100, ~0.3 s at r101).
#if RE4DC_QUALITY_ASSETS
// Standard (s16.2): the keys the room's index adds live in texlow/ (never in tex/).
extern "C" int re4dc_std_texlow(unsigned crc,unsigned fnv);
extern "C" int re4dc_std_dropped(unsigned crc,unsigned fnv);
extern "C" int re4dc_std_texture(unsigned i,unsigned out[5]);
#if RE4DC_PS2_PRELOAD_LEAN
extern "C" int re4dc_ps2_mesh_texture(unsigned i,unsigned out[4]);   // native_static.cpp
unsigned preload_ps2_lean_runs;
#endif
#define RE4DC_TEX_PATH(buf,key) std::sprintf(buf,re4dc_std_texlow((key).crc,(key).fnv)?"/cd/dc/texlow/%x/%08x-%08x.re4tex":"/cd/dc/tex/%x/%08x-%08x.re4tex",(key).crc>>28,(key).crc,(key).fnv)
#else
#define RE4DC_TEX_PATH(buf,key) std::sprintf(buf,"/cd/dc/tex/%x/%08x-%08x.re4tex",(key).crc>>28,(key).crc,(key).fnv)
#endif
#else
#define RE4DC_TEX_PATH(buf,key) std::sprintf(buf,"/cd/dc/tex/%08x-%08x.re4tex",(key).crc,(key).fnv)
#endif
#ifndef RE4DC_TEX_CHECK
#define RE4DC_TEX_CHECK 0
#endif
#if RE4DC_TEX_CHECK
// TEX_CHECK=1|2 (test only; Makefile; default 0 = this block compiles to nothing): texture presence check
// (lane texchk, issue #26). Every texture lookup that fails or is refused logs "texchk: FAIL <reason>"
// (first per key and reason); every upload records a checksum of the package metadata (header, descriptor,
// VRAM pointer, owned bytes: heap memory that a stray writer can overwrite) and a sparse VRAM sample.
// Each frame start re-verifies the metadata of every resident entry, every 30 frames its VRAM sample, and
// every lookup hit re-verifies its entry ("bind"). A change logs "texchk: META CHANGED" / "VRAM CHANGED".
// "texchk: frame=" summaries every 120 frames and "texchk: room" at each room retirement feed
// tools/d367/texchk/texchk.sh (the PASS/FAIL gate). TEX_CHECK=2 also fills free texture RAM with
// magenta (vram_pages.cpp, VRAM_PAGES=1) so a draw from never-written or freed VRAM shows on Flycast,
// which zeroes VRAM where a console holds noise.
namespace texchk {
unsigned meta_sum[kTextureCount],head_sum[kTextureCount],vram_sum[kTextureCount];bool armed[kTextureCount];
unsigned fails,policy_skips,meta_changes,vram_changes,binds,arms,room_fails,room_changes,room_binds;
struct Seen { Key key; const char* why; };
Seen seen[64]; unsigned nseen;
// The caller of the current load() (load is not inlined in TEX_CHECK builds): a refused key's owner, symbolized offline.
const void* site;
inline unsigned fnv(unsigned h,const void* p,unsigned n){const unsigned char* b=(const unsigned char*)p;for(unsigned i=0;i<n;++i)h=(h^b[i])*16777619U;return h;}
inline unsigned head_hash(const Entry& e){
    const auto& h=e.package.header();
    unsigned s=fnv(2166136261U,&h,sizeof(h));const void* hp=&h;return fnv(s,&hp,sizeof(hp));
}
inline unsigned meta_hash(const Entry& e){
    // Only called while the header hash is unchanged (its texture_offset and count are then sane).
    const auto& h=e.package.header();unsigned s=2166136261U;
    for(unsigned i=0;i<h.texture_count && i<4;++i){s=fnv(s,&e.package.textures()[i],sizeof(re4dc::texture::Texture));const pvr_ptr_t p=e.package.pvr_texture(i);s=fnv(s,&p,sizeof(p));}
    const unsigned extra[]={(unsigned)e.package.vram_bytes(),(unsigned)e.package.upload_complete()};return fnv(s,extra,sizeof(extra));
}
inline unsigned vram_hash(const Entry& e){
    const auto& t=e.package.textures()[0];const volatile unsigned* v=(const volatile unsigned*)e.package.pvr_texture(0);
    if(!v)return 0;const unsigned words=t.data_size/4;if(!words)return 0;
    unsigned s=2166136261U;const unsigned step=words>64?words/64:1;
    for(unsigned i=0;i<words;i+=step){const unsigned w=v[i];s=fnv(s,&w,4);}
    return s;
}
inline void log_entry(const char* what,const Entry& e,const char* where){
    re4dc_log("texchk: %s %08x-%08x where=%s frame=%u ptr=%08x\n",what,e.key.crc,e.key.fnv,where,frame,(unsigned)(std::uintptr_t)e.package.pvr_texture(0));
}
void arm(Entry& e){
    const unsigned i=unsigned(&e-entries);armed[i]=true;++arms;
    head_sum[i]=head_hash(e);meta_sum[i]=meta_hash(e);vram_sum[i]=vram_hash(e);
}
void verify(Entry& e,const char* where,bool vram){
    const unsigned i=unsigned(&e-entries);if(!armed[i] || !e.valid)return;
    const unsigned h=head_hash(e);
    if(h!=head_sum[i]){++meta_changes;++room_changes;log_entry("META CHANGED header",e,where);head_sum[i]=h;armed[i]=false;return;}
    const unsigned m=meta_hash(e);
    if(m!=meta_sum[i]){++meta_changes;++room_changes;log_entry("META CHANGED descriptor",e,where);meta_sum[i]=m;}
    if(vram){const unsigned v=vram_hash(e);if(v!=vram_sum[i]){++vram_changes;++room_changes;log_entry("VRAM CHANGED",e,where);vram_sum[i]=v;}}
}
void bind(Entry& e){++binds;++room_binds;verify(e,"bind",false);}
void fail(const Key& k,const char* why,const Re4dcUiImage& image,bool policy=false){
    if(policy)++policy_skips;else{++fails;++room_fails;}
    for(unsigned i=0;i<nseen && i<64;++i)if(seen[i].key==k && seen[i].why==why)return;
    seen[nseen++%64]={k,why};
    re4dc_log("texchk: %s %s %08x-%08x %ux%u fmt=%u frame=%u\n",policy?"SKIP":"FAIL",why,k.crc,k.fnv,image.width,image.height,image.format,frame);
    // A package that is not on the disc: where the image came from (t11 lane vr). The key of an image without an
    // identity is a hash of its pixel bytes; a key that changes per build means the pixels are not asset data.
    // pix / pal: the descriptor's pointers; region: vram (0xa4/0xa5 texture or framebuffer memory), p1 (P1 RAM),
    // p2 (uncached RAM); w: the first 4 pixel words; site: load()'s caller (sh-elf-addr2line on the build's ELF).
    if(!policy && (!std::strcmp(why,"open failed") || !std::strcmp(why,"absent"))){
        const unsigned px=(unsigned)image.pixels,top=px>>24;
        const char* region=top==0xa4||top==0xa5?"vram":top==0x8c?"p1":top==0xac?"p2":"other";
        unsigned w[4]={0,0,0,0};
        if(px && (top==0x8c || top==0xac || top==0xa5 || top==0xa4) && !(px&3))for(unsigned i=0;i<4;++i)w[i]=((const volatile unsigned*)px)[i];
        re4dc_log("texchk: SRC %08x-%08x pix=%08x region=%s pal=%08x palfmt=%u palbytes=%u site=%08x w=%08x,%08x,%08x,%08x frame=%u\n",
                  k.crc,k.fnv,px,region,(unsigned)image.palette,(unsigned)image.palette_format,(unsigned)image.palette_bytes,
                  (unsigned)site,w[0],w[1],w[2],w[3],frame);
    }
}
void frame_sweep(){
    const bool vram=frame%30==0;
    for(auto& e:entries)if(e.valid)verify(e,"frame",vram);
    if(frame%120==0)re4dc_log("texchk: frame=%u fails=%u skips=%u meta_changes=%u vram_changes=%u binds=%u arms=%u\n",frame,fails,policy_skips,meta_changes,vram_changes,binds,arms);
}
void room_end(){
    for(auto& e:entries)if(e.valid)verify(e,"room",true);
    re4dc_log("texchk: room frame=%u fails=%u changes=%u binds=%u total_fails=%u total_changes=%u\n",frame,room_fails,room_changes,room_binds,fails,meta_changes+vram_changes);
    room_fails=room_changes=room_binds=0;nseen=0;
}
}
#define RE4DC_TEXCHK_FAIL(k,why) texchk::fail((k),(why),image)
#define RE4DC_TEXCHK_SKIP(k,why) texchk::fail((k),(why),image,true)
#define RE4DC_TEXCHK_BIND(e) texchk::bind(e)
#else
#define RE4DC_TEXCHK_BIND(e) ((void)0)
#define RE4DC_TEXCHK_FAIL(k,why) ((void)0)
#define RE4DC_TEXCHK_SKIP(k,why) ((void)0)
#endif
#if RE4DC_WORLD_HOLE_DIAG
// WORLD_HOLE_DIAG (worldhole.mk, test only): load()'s refusal reason (the texchk reason text, stringified so a build
// without TEX_CHECK records it too) for re4dc_ps2_world_direct_begin's per-part reason (native_static.cpp WHD lines).
const char* whd_load_why;
unsigned whd_why; // re4dc_ps2_world_direct_begin's last refusal (worldhole.mk lists the codes)
// The first stream abort of the frame: kind 1 model part queue full (defer_part), 2 re4dc_model_packet_abort (ra =
// caller), 3 UI quad queue full; q = required, frame queue top, spill top, spill capacity, queued parts, quads.
unsigned whd_abort_frame=~0U,whd_abort_kind,whd_abort_q[6],whd_aborts;void* whd_abort_ra;
#define RE4DC_WHD_ABORT(kind,ra,req) do{++whd_aborts;if(whd_abort_frame!=frame){whd_abort_frame=frame;whd_abort_kind=(kind);\
    whd_abort_ra=(ra);whd_abort_q[0]=(req);whd_abort_q[1]=deferred_top;whd_abort_q[2]=deferred_spill_top;\
    whd_abort_q[3]=deferred_spill_capacity;whd_abort_q[4]=deferred_count;whd_abort_q[5]=nquad;}}while(0)
#undef RE4DC_TEXCHK_FAIL
#undef RE4DC_TEXCHK_SKIP
#if RE4DC_TEX_CHECK
#define RE4DC_TEXCHK_FAIL(k,why) (whd_load_why=#why,texchk::fail((k),(why),image))
#define RE4DC_TEXCHK_SKIP(k,why) (whd_load_why=#why,texchk::fail((k),(why),image,true))
#else
#define RE4DC_TEXCHK_FAIL(k,why) (whd_load_why=#why)
#define RE4DC_TEXCHK_SKIP(k,why) (whd_load_why=#why)
#endif
#define RE4DC_WHD(code) (whd_why=(code))
#else
#define RE4DC_WHD(code) ((void)0)
#define RE4DC_WHD_ABORT(kind,ra,req) ((void)0)
#endif
#if RE4DC_WORLD_HOLE_FIX
// WORLD_HOLE_FIX: translucent model parts dropped because the frame queue (frame_storage + the 8 KiB spill) was full.
// One WHFIX line per frame with drops (the first 64 such frames, then every 120th frame): parts and bytes asked for.
unsigned whfix_frame=~0U,whfix_parts,whfix_bytes,whfix_frames,whfix_total;
void whfix_flush(){
    if(whfix_frame==~0U || !whfix_parts)return;
    ++whfix_frames;whfix_total+=whfix_parts;
    if(whfix_frames<=64 || !(whfix_frame%120))
        re4dc_log("WHFIX frame=%u dropped_parts=%u bytes=%u frames=%u total=%u\n",whfix_frame,whfix_parts,whfix_bytes,whfix_frames,whfix_total);
    whfix_parts=whfix_bytes=0;
}
void whfix_drop(unsigned required){
    if(whfix_frame!=frame){whfix_flush();whfix_frame=frame;}
    ++whfix_parts;whfix_bytes+=required;
}
#endif
#if defined(RE4DC_FRAME_QUEUE_DIAG) && RE4DC_FRAME_QUEUE_DIAG
// FRAME_QUEUE_DIAG=1 (Makefile; log only; lane fix18 #39): per frame with frame-queue drops (translucent model parts and
// effect sprites refused because frame_storage + the deferred spill were full), one FQDIAG line: what was dropped
// (count, bytes asked for), what the queue held (deferred parts, UI quads, sprites queued, spill used / capacity).
// The peak "need" is the bytes the drops asked for beyond the spill: the size a larger spill must add.
unsigned fq_frame=~0U,fq_parts,fq_part_bytes,fq_sprites,fq_sprite_bytes,fq_frames,fq_peak,fq_q[5];
void fq_flush(){
    if(fq_frame==~0U || !(fq_parts|fq_sprites))return;
    ++fq_frames;const unsigned need=fq_part_bytes+fq_sprite_bytes;if(need>fq_peak)fq_peak=need;
    if(fq_frames<=96 || !(fq_frame%120))
        re4dc_log("FQDIAG frame=%u parts=%u part_bytes=%u sprites=%u sprite_bytes=%u need=%u peak=%u queued=%u quads=%u fx=%u spill=%u/%u frames=%u\n",
            fq_frame,fq_parts,fq_part_bytes,fq_sprites,fq_sprite_bytes,need,fq_peak,fq_q[0],fq_q[1],fq_q[2],fq_q[3],fq_q[4],fq_frames);
    fq_parts=fq_part_bytes=fq_sprites=fq_sprite_bytes=0;
}
void fq_drop(bool sprite,unsigned required){
    if(fq_frame!=frame){fq_flush();fq_frame=frame;}
    if(sprite){++fq_sprites;fq_sprite_bytes+=required;}else{++fq_parts;fq_part_bytes+=required;}
    // the queue at this frame's latest drop
    fq_q[0]=deferred_count;fq_q[1]=nquad;
#if RE4DC_EFFECT_SPRITES
    fq_q[2]=fx_count;
#endif
    fq_q[3]=deferred_spill_capacity-deferred_spill_top;fq_q[4]=deferred_spill_capacity;
}
#define RE4DC_FQ_DROP(sprite,required) fq_drop((sprite),(required))
#else
#define RE4DC_FQ_DROP(sprite,required) ((void)0)
#endif
#if RE4DC_VRAM_ROOM_LOG
// VRAM_ROOM_LOG=1 (Makefile; render/log only, needs UI_VRAM=1 VRAM_PAGES=1): the per-room VRAM report of the CLAUDE.md
// graphics memory rule (lane vram12 D4). Two lines per sample, at the room-entry preload ("preload"), every 600 frames
// of a visit ("tick") and when the room changes ("exit": the visit's minima / peak / counters; its current fields are
// already the next room's first frame):
//   vram room: pinned = texture cache bytes drawn in the last 60 frames, leased or effect-pool pinned (the working
//     set), dynamic = the other resident cache bytes (evictable without a reload this second), other = allocations
//     that are not cache entries (glyph atlas, overlay slab, OSD, movie, sub screen, lake; page padding), free and
//     largest = free texture RAM and its largest contiguous extent, min_free / min_largest over the visit (sampled
//     every frame / every 30 frames), peak_pinned over the visit; this visit's uploads (loads, the preload's
//     included), evictions (evicted: each is a disc re-read when the texture is drawn again) and fragmentation
//     retries (an upload that fitted only after evicting for a hole).
//   vram gaps: this visit's counts: refusals (budget fail-fast, load()), guard (EFFECT_ROOM thrash-guard skips, all
//     causes), guard_p (those while the cache evicted this frame or the last: VRAM pressure; the rest are the
//     kFxNewLoads per-frame load cap, which loads the texture a frame later),
//     nocontig ("no contiguous block"), latched (loads refused while a fragmentation latch holds), absent (packages
//     not on the disc), gc_fx (distinct effect textures drawn from their GameCube picture with FX_PS2_PACK=1: no
//     PS2 conversion; -1 without FX_PS2_PACK), dropped (WORLD_HOLE_FIX queue-full parts), fx_dropped (effect sprites
//     past the queue), tex_rej (model parts without their texture), snd_fail (AICA bank blocks left silent),
//     snd_used (AICA bytes held now), meta (TEX_META_EVICT evictions for KOS heap: a refused package descriptor or
//     the kKosReserve the cache leaves free), kos (KOS heap headroom now, TEX_META_EVICT; 0 without it).
//   vram gc-fx: one line per distinct GameCube-picture effect key per visit (the first 64), for the gate's ps2lib
//     INDEX.tsv lookup (tools/d367/vram/vram_gate.py; ps2_source=NONE rows are the known gaps).
// Gates: tools/d367/vram/vram_gate.py (benchmark runs) and fullplay/fp_check.py fail on refusals, guard_p skips,
// nocontig and GC-picture effects that ps2lib does not list as NONE.
extern "C" void re4dc_vram_pages_census(unsigned* out);   // vram_pages.cpp
extern "C" unsigned re4dc_aica_skipped_blocks(void);      // audio_aica.cpp / audio_stub.cpp
extern "C" unsigned re4dc_aica_used_bytes(void);
unsigned vram_nocontig,vram_guard_pressure;
constexpr unsigned kVramCounters=15;
struct VramRoom { unsigned room=~0U,since,min_free,min_largest,peak_pinned,base[kVramCounters]; };
VramRoom vroom;
#if defined(RE4DC_FX_PS2_PACK) && RE4DC_FX_PS2_PACK
unsigned char gcfx_seen[kTextureCount]; Key gcfx_keys[64]; unsigned gcfx_n,vram_gcfx;
void vram_room_gcfx(const Entry& e){   // re4dc_effect_sprite: an effect texture without the PS2 cover flag
    const unsigned i=unsigned(&e-entries);
    if(i>=kTextureCount || gcfx_seen[i])return;
    gcfx_seen[i]=1;
    for(unsigned k=0;k<gcfx_n;++k)if(gcfx_keys[k]==e.key)return;
    ++vram_gcfx;
    if(gcfx_n<sizeof(gcfx_keys)/sizeof(gcfx_keys[0])){
        gcfx_keys[gcfx_n++]=e.key;
        re4dc_log("vram gc-fx: r=%03x f=%u key=%08x-%08x\n",vroom.room,frame,e.key.crc,e.key.fnv);
    }
}
#endif
void vram_room_counters(unsigned* c){
    c[0]=vram_rejects;
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
    c[1]=fx_resident_skips;
#else
    c[1]=0;
#endif
    c[2]=vram_nocontig;
#if RE4DC_UI_FRAG_LATCH
    c[3]=frag_latched;
#else
    c[3]=0;
#endif
#if RE4DC_TEX_RESIDENT || RE4DC_SUBSCREEN
    c[4]=nmissing;
#else
    c[4]=0;
#endif
#if defined(RE4DC_FX_PS2_PACK) && RE4DC_FX_PS2_PACK
    c[5]=vram_gcfx;
#else
    c[5]=0;
#endif
#if RE4DC_WORLD_HOLE_FIX
    c[6]=whfix_total+whfix_parts;
#else
    c[6]=0;
#endif
#if RE4DC_EFFECT_SPRITES
    c[7]=fx_dropped;
#else
    c[7]=0;
#endif
    c[8]=model_texture_rejects;
    c[9]=re4dc_aica_skipped_blocks();
    c[10]=vram_guard_pressure;
    c[11]=loads;c[12]=reclaimed;c[13]=vram_retries;
#if RE4DC_TEX_META_EVICT
    c[14]=vram_meta_evicts;
#else
    c[14]=0;
#endif
}
void vram_room_largest(unsigned& largest,unsigned& alloc_bytes){
    unsigned c[13]={};re4dc_vram_pages_census(c);largest=c[4];alloc_bytes=c[1];
}
void vram_room_sample(const char* at){
    unsigned pinned=0,dynamic=0;
    for(const auto& e:entries)if(e.valid){
        const unsigned sz=e.package.vram_bytes();
        if(RE4DC_ENTRY_PINNED(e) || e.frame+60>=frame)pinned+=sz;else dynamic+=sz;
    }
    unsigned largest,alloc;vram_room_largest(largest,alloc);
    const unsigned free_bytes=(unsigned)pvr_mem_available();
    if(at[0]!='e'){   // "exit" runs on the next room's first frame: its state is not the visit's
        if(free_bytes<vroom.min_free)vroom.min_free=free_bytes;
        if(largest<vroom.min_largest)vroom.min_largest=largest;
        if(pinned>vroom.peak_pinned)vroom.peak_pinned=pinned;
    }
    unsigned c[kVramCounters];vram_room_counters(c);
    for(unsigned k=0;k<kVramCounters;++k)c[k]-=vroom.base[k];
    // re4dc_log formats into 256 bytes: both lines stay under it with 7-digit values (vram_gate.py parses key=value)
    re4dc_log("vram room: r=%03x at=%s f=%u frames=%u pinned=%u dynamic=%u other=%u free=%u largest=%u min_free=%u min_largest=%u peak_pinned=%u loads=%u evicted=%u retries=%u\n",
        vroom.room,at,frame,frame-vroom.since,pinned,dynamic,alloc>pinned+dynamic?alloc-pinned-dynamic:0U,free_bytes,largest,
        vroom.min_free,vroom.min_largest,vroom.peak_pinned,c[11],c[12],c[13]);
#if defined(RE4DC_FX_PS2_PACK) && RE4DC_FX_PS2_PACK
    const int gc=int(c[5]);
#else
    const int gc=-1;
#endif
    re4dc_log("vram gaps: r=%03x at=%s f=%u refusals=%u guard=%u guard_p=%u nocontig=%u latched=%u absent=%u gc_fx=%d dropped=%u fx_dropped=%u tex_rej=%u snd_fail=%u snd_used=%u meta=%u kos=%u\n",
        vroom.room,at,frame,c[0],c[1],c[10],c[2],c[3],c[4],gc,c[6],c[7],c[8],c[9],re4dc_aica_used_bytes(),c[14],
#if RE4DC_TEX_META_EVICT
        kos_headroom());
#else
        0U);
#endif
}
// Every frame (re4dc_ui_present) and before the preload sample: the visit's room, minima and samples.
void vram_room_track(){
    re4dc::profile::Source s{};
#if defined(__sh__)
    re4dc_profile_source(&s);
#endif
    if(s.room!=vroom.room){
        if(vroom.room!=~0U)vram_room_sample("exit");
        vroom.room=s.room;vroom.since=frame;vroom.min_free=vroom.min_largest=~0U;vroom.peak_pinned=0;
        vram_room_counters(vroom.base);
#if defined(RE4DC_FX_PS2_PACK) && RE4DC_FX_PS2_PACK
        for(auto& b:gcfx_seen)b=0;
        gcfx_n=0;
#endif
    }
    const unsigned free_bytes=(unsigned)pvr_mem_available();
    if(free_bytes<vroom.min_free)vroom.min_free=free_bytes;
}
void vram_room_frame(){
    OVLG("frame");
    vram_room_track();
    if(frame%30==0){unsigned largest,alloc;vram_room_largest(largest,alloc);if(largest<vroom.min_largest)vroom.min_largest=largest;}
    if(frame!=vroom.since && (frame-vroom.since)%600==0)vram_room_sample("tick");
#if defined(RE4DC_GANADO_ATLAS_DROP) && (RE4DC_GANADO_ATLAS_DROP & 0x100)
    else if(frame!=vroom.since && (frame-vroom.since)%150==0)vram_room_sample("t150");   // GANADO_ATLAS_DROP bit 8 (diagnostic)
#endif
}
#endif
#if defined(RE4DC_FX_PS2_NONE_CUT) && RE4DC_FX_PS2_NONE_CUT
// FX_PS2_NONE_CUT (lane purge-fx24, render only; effects30.mk): an effect picture the PS2 dropped (ps2lib effects-tex
// ps2_source=NONE) is not drawn. Decided once per texture entry and room, then a byte test per sprite.
}   // namespace (fx_none_cut.inc is plain data)
#if defined(RE4DC_FX_NONE_CUT_PACK) && RE4DC_FX_NONE_CUT_PACK
// FX_NONE_CUT_PACK (lane heap-margin25; effects30.mk): the same table packed (fx_none_cut_pack.inc, tools/d367/purge-fx24/
// fx_none_cut_pack.py: each key once, rows as one-byte key indices per room) and the per-entry decision in one u16
// ((room + 1) | cut << 15). Same answers and log lines; ~4 KB less image (heap 4 at r100 s30).
struct FxPackKey { unsigned crc,fnv; };
#include "fx_none_cut_pack.inc"
#else
struct FxNoneCutRow { unsigned short room; unsigned crc,fnv; };
#include "fx_none_cut.inc"
#endif
extern "C" void re4dc_profile_source(re4dc::profile::Source* out);   // ui_bridge.cpp
namespace {
#if defined(RE4DC_FX_NONE_CUT_PACK) && RE4DC_FX_NONE_CUT_PACK
unsigned short fxnone_room[kTextureCount];   // (room + 1) | cut << 15 when decided for the entry's current texture
#else
unsigned short fxnone_room[kTextureCount];   // room + 1 when decided for the entry's current texture
unsigned char fxnone_cut[kTextureCount];
#endif
unsigned fxnone_cuts,fxnone_frame=~0U,fxnone_now;
bool fx_none_cut(const Entry& e){
    const unsigned i=unsigned(&e-entries);
    if(i>=kTextureCount)return false;
    if(fxnone_frame!=frame){re4dc::profile::Source s{};re4dc_profile_source(&s);fxnone_now=s.room&0xffffU;fxnone_frame=frame;}
    const unsigned room=fxnone_now;
#if defined(RE4DC_FX_NONE_CUT_PACK) && RE4DC_FX_NONE_CUT_PACK
    if((fxnone_room[i]&0x7fffU)==((room+1U)&0x7fffU))return (fxnone_room[i]&0x8000U)!=0;
    bool lib=false,cut=false;
    for(unsigned short r:kFxNoneRooms)if(r==room){lib=true;break;}
    for(unsigned j=0;j<sizeof(kFxPackRoom)/sizeof(kFxPackRoom[0]) && !cut;++j){
        const unsigned r=kFxPackRoom[j];
        if(!(r==room || (r==0xffffU && !lib)))continue;
        for(unsigned k=kFxPackBeg[j];k<kFxPackBeg[j+1];++k){
            const FxPackKey& c=kFxPackKeys[kFxPackIdx[k]];
            if(c.crc==e.key.crc && c.fnv==e.key.fnv){cut=true;break;}
        }
    }
    fxnone_room[i]=(unsigned short)(((room+1U)&0x7fffU)|(cut?0x8000U:0U));
#else
    if(fxnone_room[i]==room+1U)return fxnone_cut[i]!=0;
    bool lib=false,cut=false;
    for(unsigned short r:kFxNoneRooms)if(r==room){lib=true;break;}
    for(const auto& c:kFxNoneCut){
        if(c.crc==e.key.crc && c.fnv==e.key.fnv && (c.room==room || (c.room==0xffffU && !lib))){cut=true;break;}
    }
    fxnone_room[i]=(unsigned short)(room+1U);fxnone_cut[i]=cut;
#endif
    if(cut)re4dc_log("fx ps2 none cut: room=%03x key=%08x-%08x total=%u\n",room,e.key.crc,e.key.fnv,fxnone_cuts);
    return cut;
}
#if defined(RE4DC_FX_EARLY_CUT) && RE4DC_FX_EARLY_CUT
// FX_EARLY_CUT (lane fxcut28, render only; effects30.mk): the FX_PS2_NONE_CUT answer before the texture is loaded.
// load() asks fx_none_key() on a miss for an effect sprite (fxearly_armed) and returns no entry without opening the
// package, so a picture the PS2 dropped is never uploaded. The answer per image descriptor (pixels, palette, shape) is
// kept in a small table stamped like the UI handles (handle_reset: sources reset on room / archive change) and the
// room, so later frames skip the resolve too. Same table, same answers as fx_none_cut(); same "fx ps2 none cut:" line.
bool fx_none_key(const Key& key,unsigned room){
#if defined(RE4DC_FX_NONE_CUT_PACK) && RE4DC_FX_NONE_CUT_PACK
    bool lib=false;
    for(unsigned short r:kFxNoneRooms)if(r==room){lib=true;break;}
    for(unsigned j=0;j<sizeof(kFxPackRoom)/sizeof(kFxPackRoom[0]);++j){
        const unsigned r=kFxPackRoom[j];
        if(!(r==room || (r==0xffffU && !lib)))continue;
        for(unsigned k=kFxPackBeg[j];k<kFxPackBeg[j+1];++k){
            const FxPackKey& c=kFxPackKeys[kFxPackIdx[k]];
            if(c.crc==key.crc && c.fnv==key.fnv)return true;
        }
    }
    return false;
#else
    bool lib=false;
    for(unsigned short r:kFxNoneRooms)if(r==room){lib=true;break;}
    for(const auto& c:kFxNoneCut)
        if(c.crc==key.crc && c.fnv==key.fnv && (c.room==room || (c.room==0xffffU && !lib)))return true;
    return false;
#endif
}
bool fxearly_armed,fxearly_hit;
unsigned fxearly_skips,fxearly_refused;   // descriptor-table hits / loads declined in load()
struct FxEarlyNeg { const void* pixels; const void* palette; unsigned shape,stamp; unsigned short room,palette_bytes; };
FxEarlyNeg fxearly_neg[32];
unsigned fxearly_room(){
    if(fxnone_frame!=frame){re4dc::profile::Source s{};re4dc_profile_source(&s);fxnone_now=s.room&0xffffU;fxnone_frame=frame;}
    return fxnone_now;
}
inline unsigned fxearly_slot(const Re4dcUiImage& i){
    const unsigned a=unsigned(reinterpret_cast<std::uintptr_t>(i.pixels));return ((a>>5)^(a>>11))&31U;
}
inline unsigned fxearly_shape(const Re4dcUiImage& i){return i.width|i.height<<11|i.format<<22|(i.palette_format&15U)<<26;}
bool fxearly_known_cut(const Re4dcUiImage& i){
    const FxEarlyNeg& n=fxearly_neg[fxearly_slot(i)];
    return n.pixels && n.pixels==i.pixels && n.palette==i.palette && n.palette_bytes==i.palette_bytes &&
           n.shape==fxearly_shape(i) && n.stamp>handle_reset && n.room==(unsigned short)fxearly_room();
}
void fxearly_remember(const Re4dcUiImage& i){
    fxearly_neg[fxearly_slot(i)]={i.pixels,i.palette,fxearly_shape(i),++handle_clock,(unsigned short)fxearly_room(),
                                  (unsigned short)i.palette_bytes};
}
#endif
#endif
// PS2_UPLOAD_ADVANCE_BEGIN
#if RE4DC_PS2_UPLOAD_INCARNATION
void advance_upload_incarnation(Entry& entry) {
    // Saturate to the nonreusable zero sentinel; never resurrect an old token.
    if(entry.upload_incarnation)++entry.upload_incarnation;
}
#endif
// PS2_UPLOAD_ADVANCE_END
void close_entry(Entry& entry) {
#if RE4DC_PS2_UPLOAD_INCARNATION
    advance_upload_incarnation(entry); // revoke before any retirement callback
#endif
#if defined(RE4DC_FX_PS2_NONE_CUT) && RE4DC_FX_PS2_NONE_CUT
    fxnone_room[&entry-entries]=0;
#endif
#if RE4DC_GC_ASSET_GATE
    gcasset_texture_flush(entry);
    // A pending header cannot survive retirement/reuse of any texture entry.
    gcasset_packet_reset();
#endif
    struct OvlwAfter{~OvlwAfter(){OVLW("close");OVLG("close");}} ovlw_after;
#if RE4DC_TEX_CHECK
    if(entry.valid)texchk::verify(entry,"close",true);
    texchk::armed[&entry-entries]=false;
#endif
#if RE4DC_ACTOR_TRANSACTION
    // Revoke before freeing/fencing storage; forced retirement is observable.
    actor_texture_leases.retire_entry(unsigned(&entry-entries));
#endif
#if defined(RE4DC_FX_TEX_POOL) && RE4DC_FX_TEX_POOL
    {const unsigned i=unsigned(&entry-entries);
     if(i<kTextureCount && fx_pool_pin[i]){fx_pool_pin[i]=false;fx_pool_bytes-=fx_pool_size[i];}}
#endif
    if(entry.valid) used-=entry.package.vram_bytes();
    entry.package.close();entry.valid=false;
#if RE4DC_VRAM_ROOM_LOG && defined(RE4DC_FX_PS2_PACK) && RE4DC_FX_PS2_PACK
    gcfx_seen[&entry-entries]=0;
#endif
#if RE4DC_UI_VRAM && RE4DC_TEX_RESIDENT && RE4DC_UI_OVERLAY_SLAB_KB
    if(overlay_owner==&entry){overlay_owner=nullptr;overlay_slab_take();} // the freed hole comes back
#endif
#if RE4DC_D349_RENDERER_STACK
    entry.model_header_key=~0U;
#endif
#if RE4DC_UI_HANDLES
    entry_closed[&entry-entries]=++handle_clock;
#endif
#if RE4DC_UI_HEADERS
    entry.ui_header_key=~0U; // a new upload gets its own texture address
#endif
}
#if defined(RE4DC_GANADO_ATLAS_DROP) && RE4DC_GANADO_ATLAS_DROP
// GANADO_ATLAS_DROP=<mask> (game30.mk; render only; lane gatlas17, user 10-17: "We can lower ganado texture detail if
// that will make the room work"): in the rooms of GANADO_ATLAS_DROP_ROOMS (default r101), the PS2 cast's 512x512
// Ganado atlases of the mask (bit 0 em15-00 ebed7ba6, 1 em15-03 65c6fe5a, 2 em15-04 b4f70c44, 3 em15-0b df13f362,
// 4 em12-01 bbde9497) load without their top mip level: 256x256 with their mips, 23,894 B instead of 89,430 B in VRAM.
// The atlas files are shared by every room; the cut is made at load time, so other rooms load them whole. An entry
// in the wrong state for the room (kept from the previous room) closes at the room-entry preload and loads again.
// Bit 8 (diagnostic): every 150 UI frames the atlases' model-packet binds and ages, the large textures drawn, and a
// VRAM_ROOM_LOG sample (at=t150).
const Key kGadKeys[5]={{0xebed7ba6u,0x2ca7490fu},{0x65c6fe5au,0x2593694eu},{0xb4f70c44u,0x1e5fd331u},
                       {0xdf13f362u,0x0ed8fbddu},{0xbbde9497u,0x188ca895u}};
const unsigned kGadRooms[]={RE4DC_GANADO_ATLAS_DROP_ROOMS};
unsigned gad_hits[5],gad_drops,gad_closes;
int gad_index(const Key& k){for(unsigned i=0;i<5;++i)if(kGadKeys[i]==k)return int(i);return -1;}
bool gad_wanted(const Key& k){
    const int i=gad_index(k);
    if(i<0 || !((unsigned(RE4DC_GANADO_ATLAS_DROP)>>i)&1U))return false;
    re4dc::profile::Source s{};
#if defined(__sh__)
    re4dc_profile_source(&s);
#endif
    for(const unsigned r:kGadRooms)if(r==s.room)return true;
    return false;
}
bool gad_apply(re4dc::texture::Package& p,const Key& k){
    if(gad_wanted(k) && p.drop_top_level()){
        ++gad_drops;
        re4dc_log("ganado atlas drop: %08x-%08x top level left out: %u B (drops=%u)\n",k.crc,k.fnv,(unsigned)p.textures()[0].data_size,gad_drops);
    }
    return true;
}
// At a room-entry preload: close an atlas whose top-level state is not this room's (the fences are done, as for the
// room change evict's closes). A pinned entry stays as it is and is logged.
void gad_room_states(){
    for(auto& e:entries){
        if(!e.valid || gad_index(e.key)<0 || !e.package.upload_complete())continue;
        const bool dropped=(e.package.textures()[0].flags&re4dc::texture::kTopDrop)!=0;
        if(dropped==gad_wanted(e.key))continue;
        if(RE4DC_ENTRY_PINNED(e)){re4dc_log("ganado atlas state: %08x-%08x pinned, kept dropped=%d\n",e.key.crc,e.key.fnv,dropped?1:0);continue;}
        ++gad_closes;
        re4dc_log("ganado atlas state: %08x-%08x closed for this room (dropped=%d closes=%u)\n",e.key.crc,e.key.fnv,dropped?1:0,gad_closes);
        close_entry(e);
    }
}
#if RE4DC_GANADO_ATLAS_DROP & 0x100
#define RE4DC_GAD_HIT(k) do{const int gi_=gad_index(k);if(gi_>=0)++gad_hits[gi_];}while(0)
#else
#define RE4DC_GAD_HIT(k) do{}while(0)
#endif
#else
#define RE4DC_GAD_HIT(k) do{}while(0)
#endif
#if defined(RE4DC_TEX_FINAL_REFUSAL_LOG) && RE4DC_TEX_FINAL_REFUSAL_LOG
// Only terminal load() refusals call this: no extra line for intermediate
// retries, successful loads or cache hits. Read Package::error before close()
// clears it. Invalid descriptors/identity failures have kv=0, never a stale key.
void tex_final_refusal(const Re4dcUiImage& image,const Key& key,bool key_valid,
                       const char* stage,const char* reason,unsigned need) {
    unsigned census[13]={};re4dc_vram_pages_census(census);
    re4dc_log("TEX-REFUSE r=%03x f=%u k=%08x-%08x kv=%u s=%s why=%.56s wh=%ux%u fmt=%u need=%u free=%u max=%u\n",
              re4dc_room_id_now()&0xffffU,frame,key.crc,key.fnv,key_valid?1U:0U,
              stage,reason?reason:"unknown",image.width,image.height,image.format,
              need,census[3],census[4]);
}
#define RE4DC_TEX_FINAL_REFUSAL(...) tex_final_refusal(__VA_ARGS__);
#define RE4DC_TEX_REFUSE_RETURN(...) do{tex_final_refusal(__VA_ARGS__);return nullptr;}while(0)
#else
#define RE4DC_TEX_FINAL_REFUSAL(...)
#define RE4DC_TEX_REFUSE_RETURN(...) return nullptr
#endif
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
void fa29_tex_refusal(const Re4dcUiImage&,const Key&,bool,const char* stage,const char* reason,unsigned){
    using namespace re4dc::fa29;
    hit(TextureRefusal);
    if(!std::strcmp(stage,"guard"))hit(TextureGuard);
    if(!std::strcmp(stage,"slot"))hit(TextureSlot);
    if(reason && !std::strcmp(reason,"PVR texture allocation failed"))hit(TextureNoBlock);
    if(reason && (!std::strcmp(reason,"pack-error") || !std::strcmp(reason,"pack-payload-retry")))hit(TexturePack);
}
#undef RE4DC_TEX_FINAL_REFUSAL
#undef RE4DC_TEX_REFUSE_RETURN
#if defined(RE4DC_TEX_FINAL_REFUSAL_LOG) && RE4DC_TEX_FINAL_REFUSAL_LOG
#define RE4DC_TEX_FINAL_REFUSAL(...) do{fa29_tex_refusal(__VA_ARGS__);tex_final_refusal(__VA_ARGS__);}while(0);
#else
#define RE4DC_TEX_FINAL_REFUSAL(...) do{fa29_tex_refusal(__VA_ARGS__);}while(0);
#endif
#define RE4DC_TEX_REFUSE_RETURN(...) do{RE4DC_TEX_FINAL_REFUSAL(__VA_ARGS__)return nullptr;}while(0)
#endif
#line 3874
#if RE4DC_TEX_CHECK
__attribute__((noinline))   // TEX_CHECK: texchk::site is this function's caller
#endif
#if defined(RE4DC_UI_HASH_DIAG) && RE4DC_UI_HASH_DIAG
__attribute__((noinline))
#endif
#if defined(RE4DC_G1_PART_CENSUS) && RE4DC_G1_PART_CENSUS
// G1_PART_CENSUS (g1parts.mk, diagnostic only): texture lookups (load) and how many repeat the previous lookup's image
// descriptor (pixels, palette, size, formats) with no prepared key; "G1PC tex" every 120 UI frames, with the model
// header cache's hits / builds over the same frames.
namespace g1pc_ui {
unsigned frame0,loads,same_prev,prepared,hdr_hits0,hdr_builds0; Re4dcUiImage prev{}; bool have;
void note(const Re4dcUiImage& image,const Key* prepared_key){
    if(frame-frame0>=120U){
        re4dc_log("G1PC tex: frame=%u loads=%u same_prev=%u prepared=%u header_hits=%u header_builds=%u\n",frame,loads,
                  same_prev,prepared,model_header_hits-hdr_hits0,model_header_builds-hdr_builds0);
        frame0=frame;loads=same_prev=prepared=0;hdr_hits0=model_header_hits;hdr_builds0=model_header_builds;
    }
    ++loads;
    if(prepared_key){++prepared;have=false;return;}
    if(have && prev.pixels==image.pixels && prev.palette==image.palette && prev.width==image.width &&
       prev.height==image.height && prev.format==image.format && prev.palette_format==image.palette_format &&
       prev.palette_bytes==image.palette_bytes)++same_prev;
    prev=image;have=true;
}
}
#endif
Entry* load(const Re4dcUiImage& image,bool pin=true,const Key* prepared_key=nullptr) {
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT && !RE4DC_UI_HANDLES
    re4dc::dfa26::hit(re4dc::dfa26::TextureFullNoHandle);
#endif
#if defined(RE4DC_G1_PART_CENSUS) && RE4DC_G1_PART_CENSUS
    g1pc_ui::note(image,prepared_key);
#endif
#if RE4DC_TEX_CHECK
    texchk::site=__builtin_return_address(0);
#endif
#if defined(RE4DC_UI_HASH_DIAG) && RE4DC_UI_HASH_DIAG
    hashdiag::site=__builtin_return_address(0);
#endif
    RE4DC_PROFILE_SCOPE(TextureResolve);RE4DC_PROFILE_COUNT(TextureLookups,1);
    if(!image.pixels || !image_size(image) || !image.width || !image.height || image.width>1024 || image.height>1024) RE4DC_TEX_REFUSE_RETURN(image,Key{},false,"input","invalid-image",0);
    Key key{};if(prepared_key)key=*prepared_key;else if(!image_key(image,key)){RE4DC_TEXCHK_FAIL(Key{},"identity");RE4DC_TEX_REFUSE_RETURN(image,Key{},false,"identity","identity",0);}
#if RE4DC_COPY_LEAN
    const unsigned hint=(key.crc^(key.crc>>7)^key.fnv)&127U;
    if(const unsigned h=entry_hint[hint]){
        Entry& e=entries[h-1];
        if(e.valid && e.key==key){RE4DC_TOUCH(e);RE4DC_GAD_HIT(e.key);RE4DC_PROFILE_COUNT(TextureHits,1);RE4DC_TEXCHK_BIND(e);return &e;}
    }
    for(auto& e:entries) if(e.valid && e.key==key) {entry_hint[hint]=EntryHint(&e-entries+1);RE4DC_TOUCH(e);RE4DC_GAD_HIT(e.key);RE4DC_PROFILE_COUNT(TextureHits,1);RE4DC_TEXCHK_BIND(e);return &e;}
#else
    for(auto& e:entries) if(e.valid && e.key==key) {RE4DC_TOUCH(e);RE4DC_GAD_HIT(e.key);RE4DC_PROFILE_COUNT(TextureHits,1);RE4DC_TEXCHK_BIND(e);return &e;}
#endif
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
    re4dc::fa29::hit(re4dc::fa29::TextureMiss);
#endif
#line 3927
#if defined(RE4DC_FX_PS2_NONE_CUT) && RE4DC_FX_PS2_NONE_CUT && defined(RE4DC_FX_EARLY_CUT) && RE4DC_FX_EARLY_CUT
    // FX_EARLY_CUT: an effect picture the PS2 dropped is declined before any eviction, budget test or file I/O.
    if(fxearly_armed && fx_none_key(key,fxearly_room())){
        fxearly_hit=true;++fxearly_refused;
        re4dc_log("fx ps2 none cut: room=%03x key=%08x-%08x total=%u early\n",fxearly_room(),key.crc,key.fnv,fxnone_cuts);
        return nullptr;
    }
#endif
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    // WORLD_METER: a failed texture-RAM allocation from here on names this key in its VRAMFAIL log line (vram_pages.cpp).
    struct VramKeyScope{VramKeyScope(const Key& k){re4dc_vram_key_crc=k.crc;re4dc_vram_key_fnv=k.fnv;}
                        ~VramKeyScope(){re4dc_vram_key_crc=0;re4dc_vram_key_fnv=0;}} vram_key_scope(key);
#endif
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
    if(fx_resident_only){++fx_resident_skips;
#if RE4DC_VRAM_ROOM_LOG
        if(frame-fx_evict_frame<=1)++vram_guard_pressure;   // VRAM_ROOM_LOG: skipped under eviction pressure
#endif
        RE4DC_TEXCHK_SKIP(key,"fx-resident-only");RE4DC_TEX_REFUSE_RETURN(image,key,true,"guard","fx-resident-only",0);}
#endif
#if RE4DC_UI_VRAM
    {
        // Fail fast, before any eviction or file I/O (open_streamed CRC-reads
        // the whole package), when even the smallest native form of the padded
        // image (16-bit or full-codebook VQ) cannot fit beside this frame's
        // pinned uploads. Retrying such a load every frame stalls the frame loop.
        unsigned pw=8,ph=8;while(pw<image.width)pw*=2;while(ph<image.height)ph*=2;
        const unsigned least=std::min(pw*ph*2,2048+pw*ph/4);
        unsigned pinned=0;for(const auto& e:entries)if(e.valid && RE4DC_ENTRY_PINNED(e))pinned+=e.package.vram_bytes();
        if(pinned+least>vram_budget){++vram_rejects;RE4DC_PROFILE_COUNT(TextureBudgetFailures,1);RE4DC_TEXCHK_FAIL(key,"vram-budget");RE4DC_TEX_REFUSE_RETURN(image,key,true,"budget","vram-budget",least);}
    }
#endif
#if RE4DC_TEX_RESIDENT || RE4DC_SUBSCREEN
    // A package absent from the disc: fail without evicting an entry or
    // touching the filesystem again (it was retried every frame).
    for(const auto& m:missing_keys) if(m.crc|m.fnv) if(m==key) {RE4DC_TEXCHK_FAIL(key,"missing");RE4DC_TEX_REFUSE_RETURN(image,key,true,"lookup","missing",0);}
#endif
#if RE4DC_UI_VRAM && RE4DC_UI_FRAG_LATCH
#if RE4DC_UI_FRAG_RESERVE
    if(key==frag_key && !frag_held && frame-frag_frame<kFragRetryFrames){++frag_latched;RE4DC_TEXCHK_FAIL(key,"frag-latched");RE4DC_TEX_REFUSE_RETURN(image,key,true,"guard","frag-latched",0);} // before any eviction
#else
    if(key==frag_key && frame-frag_frame<kFragRetryFrames){++frag_latched;RE4DC_TEXCHK_FAIL(key,"frag-latched");RE4DC_TEX_REFUSE_RETURN(image,key,true,"guard","frag-latched",0);} // before any eviction
#endif
#endif
    Entry* slot=nullptr;
    for(auto& e:entries) if(!e.valid){slot=&e;break;}
    if(!slot) for(auto& e:entries) if(!RE4DC_ENTRY_PINNED(e) && !RE4DC_CORE_PINNED(e) && (!slot || e.frame<slot->frame)) slot=&e;
    if(!slot) {RE4DC_PROFILE_COUNT(TextureNoSlot,1);RE4DC_TEXCHK_FAIL(key,"no-slot");RE4DC_TEX_REFUSE_RETURN(image,key,true,"slot","no-slot",0);}
#if RE4DC_TEX_RESIDENT
    // Never evict a resident texture for a package that is not on the disc:
    // check it exists first (only when this load would evict), and remember
    // an absent key so it is never tried again.
#if RE4DC_TEX_PACK
    unsigned pack_offset=0,pack_size=0;
#if RE4DC_TEX_PAYLOAD_RETRY
    unsigned pack_member=~0U,pack_epoch=0;
#define RE4DC_PACK_FIND() texpack::find(key,pack_offset,pack_size,frame,&pack_member,&pack_epoch)
#else
#define RE4DC_PACK_FIND() texpack::find(key,pack_offset,pack_size,frame)
#endif
#if RE4DC_QUALITY_ASSETS
    // texlow/ keys (Standard index additions) are never in tex/, so never in the pack: skip the lookup.
    const texpack::Result pack=re4dc_std_texlow(key.crc,key.fnv)?texpack::kNotInPack:RE4DC_PACK_FIND();
#else
    const texpack::Result pack=RE4DC_PACK_FIND();
#endif
    // A pack read error is transient: no eviction, no per-file probe, and the key is not remembered as missing
    // (on a packed disc its loose file is gone); a later use retries (texpack_index.inc spaces the retries in UI frames).
    if(pack==texpack::kError){++pack_error_skips;RE4DC_PROFILE_COUNT(TextureOpenFailures,1);RE4DC_TEXCHK_FAIL(key,"pack-error");RE4DC_TEX_REFUSE_RETURN(image,key,true,"lookup","pack-error",0);}
    const bool in_pack=pack==texpack::kFound;
#undef RE4DC_PACK_FIND
#if RE4DC_TEX_PAYLOAD_RETRY
    // Existing resident hits returned above. Only this exact failed member waits,
    // before close_entry/eviction or a new package open; never a loose-key miss.
    if(in_pack && texpack::payload_blocked(pack_member,frame,pack_epoch)){
        RE4DC_TEXCHK_FAIL(key,"pack-payload-retry");RE4DC_TEX_REFUSE_RETURN(image,key,true,"guard","pack-payload-retry",0);
    }
#endif
    if(slot->valid && !in_pack){
#else
    if(slot->valid){
#endif
        char probe[96];RE4DC_TEX_PATH(probe,key);
        const file_t f=fs_open(probe,O_RDONLY);
        if(f==FILEHND_INVALID){
            re4dc_log("native UI: package absent, not evicting: %s\n",probe);
            missing_keys[nmissing++%(sizeof(missing_keys)/sizeof(missing_keys[0]))]=key;
            RE4DC_PROFILE_COUNT(TextureOpenFailures,1);RE4DC_TEXCHK_FAIL(key,"absent");RE4DC_TEX_REFUSE_RETURN(image,key,true,"lookup","absent",0);
        }
        fs_close(f);
    }
#endif
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
    if(slot->valid)re4dc::fa29::hit(re4dc::fa29::TextureEvict);
#endif
#line 4019
    if(slot->valid){RE4DC_PROFILE_COUNT(TextureEvictions,1);RE4DC_FX_EVICTED();RE4DC_HOLD_EVICTED(*slot);}
    close_entry(*slot); // caller has completed both TA and render fences
    char path[96];RE4DC_TEX_PATH(path,key);
    re4dc_log("native UI: load %s %ux%u fmt=%u\n",path,image.width,image.height,image.format);
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
    ++load_opens;
#endif
    const int heap_before=re4dc_ui_heap_free();
#if RE4DC_TEX_META_EVICT
    const unsigned kos_before=kos_headroom();   // the KOS heap one load takes (bounded upload line)
#endif
#if RE4DC_TEX_PACK
#define RE4DC_OPEN_PACKAGE_RAW() (in_pack?slot->package.open_streamed_at(texpack::kPath,pack_offset,pack_size):slot->package.open_streamed(path))
#else
#define RE4DC_OPEN_PACKAGE_RAW() slot->package.open_streamed(path)
#endif
#if defined(RE4DC_GANADO_ATLAS_DROP) && RE4DC_GANADO_ATLAS_DROP
#define RE4DC_OPEN_PACKAGE() (RE4DC_OPEN_PACKAGE_RAW() && gad_apply(slot->package,key))
#else
#define RE4DC_OPEN_PACKAGE() RE4DC_OPEN_PACKAGE_RAW()
#endif
#if RE4DC_GC_ASSET_GATE
    // Hash only the accepted member at immutable load. This is preparation,
    // not an emission; cached/culled/preloaded Entries produce no GC-ASSET row.
    // gc-catalog24b: the digest is taken from the bytes open/upload read
    // (gcasset_texture_finish after a successful upload).
    slot->asset={};gca_tex_arm(*slot);
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    DFA26_HIT(TextureUpload)
#endif
    bool ok=RE4DC_OPEN_PACKAGE();
#if defined(RE4DC_TEX_FINAL_REFUSAL_LOG) && RE4DC_TEX_FINAL_REFUSAL_LOG
    unsigned refusal_need=0;
    const char* refusal_stage="open";
    const char* refusal_reason="open";
#endif
    if(!ok) {RE4DC_PROFILE_COUNT(TextureOpenFailures,1);re4dc_log("native UI: package rejected: %s\n",slot->package.error());}
#if RE4DC_UI_FRAG_RESERVE
    if(frag_held && key==frag_key){
        // Free the held block just before this upload: the best fit takes it (nothing else allocates in between).
        pvr_mem_free(frag_held);frag_held=nullptr;++frag_handoffs;frag_key=Key{};
        re4dc_log("native UI: frag reserve handed over: %ux%u frame=%u\n",image.width,image.height,frame);
    }
#endif
#if RE4DC_TEX_RESIDENT || RE4DC_SUBSCREEN
#if RE4DC_TEX_PACK
    // The pack failing to open is a read error of the pack, not a missing package.
    if(!ok && !in_pack && slot->package.error() && !std::strcmp(slot->package.error(),"open failed"))
#else
    if(!ok && slot->package.error() && !std::strcmp(slot->package.error(),"open failed"))
#endif
        missing_keys[nmissing++%(sizeof(missing_keys)/sizeof(missing_keys[0]))]=key;
#endif
#if RE4DC_UI_VRAM
    // Evict the least recently used upload that this frame's scene does not
    // reference (frame!=current); LRU order spends uploads idle >=2 frames
    // first. A previous-frame upload may still be read by the render in
    // flight: close() waits for it first via re4dc_pvr_vram_fence():
    // PVR_PIPELINE=1 until the presenter resolved that scene (render done),
    // PVR_PIPELINE=2 while pvr_present_pending() (the async decision is only
    // applied by the render-done IRQ; a present stays pending until its flip).
    // Without a pipeline, re4dc_ui_begin() quiesced the render before this frame.
    auto evict=[slot]{
        Entry* victim=nullptr;
        for(auto& e:entries) if(&e!=slot && e.valid && !RE4DC_ENTRY_PINNED(e) && !RE4DC_CORE_PINNED(e) && (!victim || e.frame<victim->frame)) victim=&e;
        if(!victim) return false;
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
        re4dc::fa29::hit(re4dc::fa29::TextureEvict);
#endif
#line 4086
        RE4DC_PROFILE_COUNT(TextureEvictions,1);RE4DC_FX_EVICTED();RE4DC_HOLD_EVICTED(*victim);close_entry(*victim);++reclaimed;return true;
    };
#if RE4DC_TEX_META_EVICT
    // TEX_META_EVICT=1 (Makefile; render only): each open package keeps its descriptor prefix (header + texture record,
    // 144 B for one texture) in the KOS heap, which ends at ARENA_FIT_KOS_BYTES and cannot grow without moving heap 4
    // (whose free bytes the game's spawn checks read). With VRAM no longer the limit (lane vram12 D5: r101 holds ~330
    // packages, KOS heap full) a refused prefix is a capacity miss like a full pool: evict the least recently used
    // upload this frame does not draw and open again (at most 8 evictions per load). Without it the load fails every
    // frame (r101 benchmark, D5 data: 1,604 failed loads of 6 textures, one Ganado body among them).
    // These are KOS heap evictions, not VRAM pressure: they do not arm the effect thrash guard (RE4DC_FX_EVICTED).
    auto evict_kos=[&evict]{
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
        const unsigned keep=fx_evict_frame;const bool r=evict();fx_evict_frame=keep;return r;
#else
        return evict();
#endif
    };
    for(unsigned tries=0;!ok && tries<8 && slot->package.error() && !std::strcmp(slot->package.error(),"streamed metadata allocation failed") && evict_kos();++tries){
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
        re4dc::fa29::hit(re4dc::fa29::TextureMeta);
#endif
#line 4104
        ++vram_meta_evicts;
        ok=RE4DC_OPEN_PACKAGE();
    }
    // The tex.pak index lookup and file reads take KOS heap too (with the heap full a sector read failed: "tex pack:
    // index sector N read error ... re-read in 30 frames"), so after a load the heap keeps kKosReserve bytes free:
    // least recently used uploads the frame does not draw are evicted until it does.
    for(unsigned tries=0;tries<32 && kos_headroom()<kKosReserve && evict_kos();++tries)++vram_meta_evicts;
#endif
#if RE4DC_TEX_RESIDENT
    unsigned need=0;
    if(ok) {
        const auto& h=slot->package.header();need=h.data_size;
#else
    if(ok) {
        const auto& h=slot->package.header();
#endif
#if defined(RE4DC_TEX_FINAL_REFUSAL_LOG) && RE4DC_TEX_FINAL_REFUSAL_LOG
        refusal_need=h.data_size;refusal_stage="budget";
        refusal_reason=h.texture_count!=1?"texture-count":"vram-budget";
#endif
        ok=h.texture_count==1 && h.data_size<=vram_budget;
        // Accounted budget first, then the real pool (allocator overhead).
        while(ok && (used+h.data_size>vram_budget || pvr_mem_available()<h.data_size))
            if(!evict()) {RE4DC_PROFILE_COUNT(TextureBudgetFailures,1);ok=false;}
    }
    const unsigned vram_before=pvr_mem_available();
#if defined(RE4DC_VRAM_ROOM_ARENA) && RE4DC_VRAM_ROOM_ARENA
    // VRAM_ROOM_ARENA: core keys (cross-room) from the top of texture RAM, every other texture from the bottom.
    struct ArenaClass { explicit ArenaClass(unsigned c){re4dc_vram_arena_class=c;} ~ArenaClass(){re4dc_vram_arena_class=0;} };
    bool arena_core=false;
#if defined(RE4DC_CORE_PIN) && RE4DC_CORE_PIN
#if defined(RE4DC_TEX_ARENA_CURRENT_KEY) && RE4DC_TEX_ARENA_CURRENT_KEY
    // close_entry() retains the old slot key until success is published below.
    // Placement belongs to this request, including all upload retries.
    for(unsigned k=0;k<core_nkeys && !arena_core;++k)arena_core=core_keys[k]==key;
#else
    for(unsigned k=0;k<core_nkeys && !arena_core;++k)arena_core=core_keys[k]==slot->key;
#endif
#endif
    const ArenaClass arena_class(arena_core?2U:1U);
#endif
    if(ok) {RE4DC_PROFILE_SCOPE(TextureUpload);
#if defined(RE4DC_TEX_FINAL_REFUSAL_LOG) && RE4DC_TEX_FINAL_REFUSAL_LOG
        refusal_stage="upload";refusal_reason="upload";
#endif
        ok=slot->package.upload();
#if RE4DC_TEX_RESIDENT && RE4DC_UI_OVERLAY_SLAB_KB
        // No contiguous block: take the overlay slab before evicting anything the scene uses.
        if(!ok && overlay_slab && need<=kOverlaySlabBytes && slot->package.error() &&
           !std::strcmp(slot->package.error(),"PVR texture allocation failed")){
            pvr_mem_free(overlay_slab);overlay_slab=nullptr;
            ok=RE4DC_OPEN_PACKAGE() && slot->package.upload();
            if(ok){overlay_owner=slot;++overlay_uses;}
            else{ // did not fit the hole: give the slab back, then the normal retry below
                slot->package.close();overlay_slab_take();
                ok=RE4DC_OPEN_PACKAGE() && slot->package.upload();
            }
            re4dc_log("native UI: overlay slab %s: %ux%u need=%u uses=%u\n",overlay_owner==slot?"taken":"too small",image.width,image.height,need,overlay_uses);
        }
#endif
#if defined(RE4DC_CORE_PIN) && RE4DC_CORE_PIN==2 && RE4DC_TEX_RESIDENT
        // CORE_PIN=2: a large fragmented picture outside every VRAM claim (no sub screen / route movie open) may take the
        // core keys' blocks, in the frag window and in the LRU retry below. Inside a claim (the radio call's 640x360
        // pictures) they stay pinned.
        core_yield=!ok && need>=kCoreYieldBytes && !vram_claims && slot->package.error() &&
                   !std::strcmp(slot->package.error(),"PVR texture allocation failed");
        if(core_yield){++core_yields;re4dc_log("native UI: core keys yield to %ux%u need=%u (yields=%u)\n",image.width,image.height,need,core_yields);}
#endif
#if RE4DC_UI_FRAG_WINDOW
        // UI_FRAG_WINDOW (Makefile): one hole of the size, not LRU evictions until one appears. =3: only for uploads of
        // at least kFragDropBytes (the r105 results pictures); smaller ones keep the LRU retry (r100 s20 fight: =1
        // released windows of effect textures for 8..89 KiB uploads and the thrash guard then dropped 11 effect sprites).
        if(!ok && (RE4DC_UI_FRAG_WINDOW!=3 || need>=kFragDropBytes) && slot->package.error() &&
           !std::strcmp(slot->package.error(),"PVR texture allocation failed")){
            unsigned wb=0;frag_min_age=kFragMinAge;const unsigned wr=movie_window_release(need,false,wb);frag_min_age=0;
            if(wr){ok=RE4DC_OPEN_PACKAGE() && slot->package.upload();frag_win_bytes+=wb;}
            if(ok)++frag_win_ok;else ++frag_win_none;
            re4dc_log("native UI: frag window %s: %ux%u need=%u released=%u entries/%u B free=%u frame=%u\n",ok?"ok":wr?"short":"none",
                      image.width,image.height,need,wr,wb,(unsigned)pvr_mem_available(),frame);
        }
#endif
        // A fragmented pool can refuse a block that the totals admit. Free one
        // more unreferenced upload and retry; reopening releases the partial
        // allocation (Package refuses to resume a partial upload in place).
        for(const char* e=slot->package.error();!ok && e && !std::strcmp(e,"PVR texture allocation failed") && evict();e=slot->package.error()){
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
            re4dc::fa29::hit(re4dc::fa29::TextureReopen);
#endif
#line 4189
            ++vram_retries;
            re4dc_log("native UI: fragmented VRAM, evicted and retrying (retries=%u free=%u)\n",vram_retries,(unsigned)pvr_mem_available());
#if RE4DC_TEX_RESIDENT
            // Evict until one contiguous block of the size fits, then read the
            // package once more (was: a full re-read per single eviction).
            for(;;){pvr_ptr_t probe=pvr_mem_malloc(need);if(probe){pvr_mem_free(probe);break;}if(!evict())break;}
#endif
            ok=RE4DC_OPEN_PACKAGE() && slot->package.upload();
        }
#if defined(RE4DC_CORE_PIN) && RE4DC_CORE_PIN==2 && RE4DC_TEX_RESIDENT
        core_yield=false;
#endif
#if RE4DC_UI_FRAG_WINDOW==2
        // The LRU retry found no hole either: it is blocked by uploads this frame already took (its draws, or the
        // room preload's picks at the frame start). Release the cheapest window including them and close this
        // frame's scene unrendered at its present (frag_discard: the previous picture stays one more frame). The rest
        // of the frame draws as usual (a released texture reloads on first sight; no part is refused, so no actor
        // falls back to its source model), but none of it is shown. close_entry() waits for the render in flight
        // (re4dc_pvr_vram_fence), as every eviction does. Never inside a direct model write.
#if RE4DC_TA_DIRECT
        const bool direct=direct_open;
#else
        const bool direct=false;
#endif
        if(!ok && slot->package.error() && !std::strcmp(slot->package.error(),"PVR texture allocation failed") &&
           need>=kFragDropBytes && !stream_aborted && !direct && frame-frag_drop_frame>kFragRetryFrames){
            const bool scene=stream_scene;
            if(scene)frag_discard=true;
            frag_drop_frame=frame;++frag_drops;
            unsigned db=0;const unsigned dr=movie_window_release(need,true,db);
            if(dr)ok=RE4DC_OPEN_PACKAGE() && slot->package.upload();
            if(ok)++frag_drop_ok;
            re4dc_log("native UI: frag drop frame=%u scene=%d pin=%d %s: %ux%u need=%u released=%u entries/%u B free=%u\n",frame,
                      scene?1:0,pin?1:0,ok?"ok":"FAILED",image.width,image.height,need,dr,db,(unsigned)pvr_mem_available());
        }
#endif
#if RE4DC_UI_FRAG_LATCH && RE4DC_TEX_RESIDENT
        if(!ok && slot->package.error() && !std::strcmp(slot->package.error(),"PVR texture allocation failed")){
            frag_key=key;frag_frame=frame;
#if RE4DC_VRAM_ROOM_LOG
            ++vram_nocontig;
#endif
            re4dc_log("native UI: no contiguous block for %ux%u (need=%u free=%u): latched %u frames\n",image.width,image.height,need,(unsigned)pvr_mem_available(),kFragRetryFrames);
#if RE4DC_UI_FRAG_RESERVE
            if(!frag_held)frag_want=need;
#endif
#if RE4DC_VRAM_CENSUS && RE4DC_VRAM_PAGES
            {void vram_frag_dump(unsigned);vram_frag_dump(need);}
#endif
        }
#endif
#if defined(RE4DC_TEX_FINAL_REFUSAL_LOG) && RE4DC_TEX_FINAL_REFUSAL_LOG
        if(ok){refusal_stage="payload";refusal_reason="release-payload";}
#endif
        ok=ok && slot->package.release_payload();
        if(ok){RE4DC_PROFILE_COUNT(TextureUploads,1);RE4DC_PROFILE_COUNT(TextureUploadBytes,slot->package.vram_bytes());}
        else RE4DC_PROFILE_COUNT(TextureUploadFailures,1);
    }
    // The byte-wise VRAM readback below costs milliseconds per large VQ texture
    // on hardware; VQ UI/model packages are ordinary here, so log without it.
    if(ok && slot->package.textures()[0].payload==re4dc::texture::kPayloadVq)
        re4dc_log("native texture VQ: bytes=%u raw16=%u free_vram=%u allocation_delta=%u\n",slot->package.textures()[0].data_size,
            slot->package.textures()[0].width*slot->package.textures()[0].height*2,(unsigned)pvr_mem_available(),vram_before-(unsigned)pvr_mem_available());
#else
    if(ok) {
        const auto& h=slot->package.header();
        ok=h.texture_count==1 && h.data_size<=kVramBudget;
        if(ok) {
            while(used+h.data_size>kVramBudget) {
                Entry* victim=nullptr;
                for(auto& e:entries) if(e.valid && !RE4DC_ENTRY_PINNED(e) && (!victim || e.frame<victim->frame)) victim=&e;
                if(!victim) {RE4DC_PROFILE_COUNT(TextureBudgetFailures,1);ok=false;break;} RE4DC_PROFILE_COUNT(TextureEvictions,1);close_entry(*victim);
            }
        }
    }
    const unsigned vram_before=pvr_mem_available();
    if(ok) {RE4DC_PROFILE_SCOPE(TextureUpload);
        ok=slot->package.upload() && slot->package.release_payload();
        if(ok){RE4DC_PROFILE_COUNT(TextureUploads,1);RE4DC_PROFILE_COUNT(TextureUploadBytes,slot->package.vram_bytes());}
        else RE4DC_PROFILE_COUNT(TextureUploadFailures,1);
    }
    if(ok && slot->package.textures()[0].payload==re4dc::texture::kPayloadVq){
        const auto& t=slot->package.textures()[0];
        const volatile unsigned char* data=(const volatile unsigned char*)slot->package.pvr_texture(0);
        unsigned fnv=2166136261U;
        for(unsigned n=0;n<t.data_size;++n)fnv=(fnv^data[n])*16777619U;
        re4dc_log("native texture VQ: ptr=%08x bytes=%u raw16=%u format=%08x readback_fnv=%08x free_vram=%u allocation_delta=%u\n",(unsigned)data,t.data_size,t.width*t.height*2,re4dc::texture::pvr_format(t),fnv,(unsigned)pvr_mem_available(),vram_before-(unsigned)pvr_mem_available());
    }
#endif
    re4dc_log("native UI: upload %s vram=%u\n",ok?"ok":"FAILED",slot->package.vram_bytes());
    OVLW("upload");
#if defined(RE4DC_ARENA_RING) && RE4DC_ARENA_RING
#if defined(RE4DC_TEX_ARENA_CURRENT_KEY) && RE4DC_TEX_ARENA_CURRENT_KEY
    re4dc_vram_ring_upload(key.crc, ok ? slot->package.vram_bytes() : 0xFFFFFFFFU, &slot->package);
#else
    re4dc_vram_ring_upload(slot->key.crc, ok ? slot->package.vram_bytes() : 0xFFFFFFFFU, &slot->package);
#endif
#endif
    OVLG("upload");
#if RE4DC_TEX_CHECK
    const char* const texchk_why=slot->package.error()?slot->package.error():"upload";
#endif
#if RE4DC_TEX_PAYLOAD_RETRY
    if(in_pack){
        if(ok)texpack::payload_succeeded(pack_member,pack_epoch);
        else if(texpack_payload_retry::source_error(slot->package.error()))texpack::payload_failed(pack_member,frame,pack_epoch);
    }
#endif
#if defined(RE4DC_TEX_FINAL_REFUSAL_LOG) && RE4DC_TEX_FINAL_REFUSAL_LOG
    if(!ok) RE4DC_TEX_FINAL_REFUSAL(image,key,true,refusal_stage,
                                 slot->package.error()?slot->package.error():refusal_reason,refusal_need)
#endif
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
#if !defined(RE4DC_TEX_FINAL_REFUSAL_LOG) || !RE4DC_TEX_FINAL_REFUSAL_LOG
    if(!ok)fa29_tex_refusal(image,key,true,"upload",slot->package.error(),0);
#endif
#endif
#line 4301
    if(!ok) slot->package.close();
#if RE4DC_TEX_META_EVICT
    re4dc_log("native UI: bounded upload heap=%d->%d metadata=%u staging=shared-16384 source_allocation=0 kos=%u->%u\n",heap_before,re4dc_ui_heap_free(),slot->package.metadata_bytes(),kos_before,kos_headroom());
#else
    re4dc_log("native UI: bounded upload heap=%d->%d metadata=%u staging=shared-16384 source_allocation=0\n",heap_before,re4dc_ui_heap_free(),slot->package.metadata_bytes());
#endif
    if(ok)++loads;
#if RE4DC_GC_ASSET_GATE
    if(ok){
#if RE4DC_TEX_PACK
        const bool fingerprint_ok=gcasset_texture_finish(*slot,key,in_pack?texpack::kPath:path,
            in_pack?pack_offset:0,in_pack?pack_size:0);
#else
        const bool fingerprint_ok=gcasset_texture_finish(*slot,key,path,0,0);
#endif
        if(!fingerprint_ok)re4dc_log("GC-ASSET-ERROR v=2 why=texture-fingerprint key=%08x-%08x\n",key.crc,key.fnv);
    } else gca_tex_disarm();
#endif
    if(!ok) {RE4DC_TEXCHK_FAIL(key,texchk_why);return nullptr;}
    // PS2_UPLOAD_PUBLICATION_BEGIN
#if RE4DC_PS2_UPLOAD_INCARNATION
    advance_upload_incarnation(*slot); // accepted upload; retries were unpublished
#endif
    slot->valid=true;slot->key=key;
    // PS2_UPLOAD_PUBLICATION_END
#if RE4DC_TEX_RESIDENT
    slot->frame=pin?frame:frame?frame-1:0;
#else
    slot->frame=pin?frame:0;
#endif
   used+=slot->package.vram_bytes();
    if(used>peak) peak=used;
#if RE4DC_TEX_CHECK
    texchk::arm(*slot);
#endif
    return slot;
}
#undef RE4DC_OPEN_PACKAGE
#undef RE4DC_OPEN_PACKAGE_RAW
#undef RE4DC_TEX_FINAL_REFUSAL
#undef RE4DC_TEX_REFUSE_RETURN
#if RE4DC_UI_HANDLES
// Direct texture handles. The first draw of a source image (with its alpha
// mask for masked model parts) takes the full path: image_key() (source scan,
// identity tables or texel hash) and load() (entry scan, upload). Its result
// is kept in a direct-mapped handle: one 32-byte line holding the descriptor
// and the entry index. Later draws compare the descriptor words and the stamp
// and use the entry directly: no hashing, keying, memcmp or table scan.
// Exactness: the handle is dropped by any entry close (eviction, retire) and
// by every source descriptor boundary (sources_reset(): room/core/option/
// player/weapon/enemy binds, invalidate_sources), the same contract under
// which sources[] already maps a descriptor to its key without rehashing.
// Indexed (C4/C8) images, e.g. the HUD: image_key() re-qualifies the CURRENT
// palette each time. Their handle also keeps a copy of the palette qualified
// at fill time (palette_copies[], one per handle slot group) and hits only
// while the live palette is identical, so a hit is exactly what the full path
// would resolve; any palette change takes the full path again.
// entry: one byte while the cache fits (the default image); TEX_SLOTS above 255 needs the padding byte too (same size).
using HandleEntry=std::conditional_t<(kTextureCount<256),unsigned char,unsigned short>;
struct alignas(32) Handle { const void *pixels,*palette,*mask_pixels,*mask_palette; unsigned shape,mask_shape,stamp; HandleEntry entry; unsigned short palette_bytes; };
static_assert(sizeof(Handle)==32 && kTextureCount<65536);
static_assert(sizeof(void*)!=4 || sizeof(Handle)==32,"one SH-4 D-cache line per handle");
Handle handle_table[256];
#ifndef RE4DC_UI_PALETTE_SLOTS
#define RE4DC_UI_PALETTE_SLOTS 0
#endif
#if RE4DC_UI_PALETTE_SLOTS
static_assert(RE4DC_UI_PALETTE_SLOTS>0 && RE4DC_UI_PALETTE_SLOTS<256,"slot + 1 fits a byte");
constexpr unsigned kPaletteCopies=RE4DC_UI_PALETTE_SLOTS;
#else
constexpr unsigned kPaletteCopies=16;
#endif
#if RE4DC_UI_PALETTE_SLOTS
struct alignas(4) PaletteCopy { unsigned short owner,bytes; unsigned short data[256]; }; // owner: handle index+1
#else
struct PaletteCopy { unsigned short owner,bytes; unsigned short data[256]; }; // owner: handle index+1
#endif
PaletteCopy palette_copies[kPaletteCopies];
#if RE4DC_UI_PALETTE_SLOTS
typedef unsigned palette_word __attribute__((may_alias));
// UI_PALETTE_SLOTS=N (game30.mk; exact): the copies are N slots given to handles on demand, the least
// recently used replaced, instead of 16 fixed to handle index % 16: the HUD's indexed images evicted
// each other's copies every frame (6 full resolves per tick in the r101 square). A hit still needs the
// copy's owner and the identical live palette.
unsigned char palette_slot[256];               // handle index -> copy slot + 1 (0: none)
unsigned palette_used[kPaletteCopies],palette_clock;
inline PaletteCopy* palette_copy(unsigned index){
    const unsigned s=palette_slot[index];
    return s && palette_copies[s-1].owner==index+1 ? &palette_copies[s-1] : nullptr;
}
#endif
inline bool handle_shape(const Re4dcUiImage& i,unsigned& shape,bool allow_indexed){
    // The bridges mark "no palette" as palette_format 0xffffffff (GX TLUT formats are 0-2).
    const unsigned palette_format=i.palette_format==0xffffffffU?3U:i.palette_format;
    const bool indexed=i.format==8 || i.format==9;
    if(indexed ? (!allow_indexed || !i.palette || !i.palette_bytes || i.palette_bytes>512 || (i.palette_bytes&1) ||
                  (reinterpret_cast<std::uintptr_t>(i.palette)&1))
               : i.palette_bytes!=0)return false;
    if(!i.pixels || i.format>15 || palette_format>3 || !i.width || !i.height || i.width>1024 || i.height>1024)return false;
    shape=i.width|i.height<<11|i.format<<22|palette_format<<26|1U<<31;return true;
}
inline bool palette_same(unsigned index,const Re4dcUiImage& i){
#if RE4DC_UI_PALETTE_SLOTS
    const PaletteCopy* cp=palette_copy(index);
    if(!cp || cp->bytes!=i.palette_bytes)return DFA26_FALSE(TexturePalette);
    const PaletteCopy& c=*cp;
#else
    const PaletteCopy& c=palette_copies[index%kPaletteCopies];
    if(c.owner!=index+1 || c.bytes!=i.palette_bytes)return DFA26_FALSE(TexturePalette);
#endif
    const auto* p=static_cast<const unsigned short*>(i.palette);
#if RE4DC_UI_PALETTE_SLOTS
    if(!((unsigned(reinterpret_cast<std::uintptr_t>(p))|i.palette_bytes)&3)){   // word compare
        const auto* w=reinterpret_cast<const palette_word*>(p);
        const auto* cw=reinterpret_cast<const palette_word*>(c.data);
        for(unsigned n=0;n<i.palette_bytes/4;++n)if(cw[n]!=w[n])return DFA26_FALSE(TexturePalette);
    }else
#endif
    for(unsigned n=0;n<i.palette_bytes/2;++n)if(c.data[n]!=p[n])return DFA26_FALSE(TexturePalette);
#if RE4DC_UI_PALETTE_SLOTS
    palette_used[&c-palette_copies]=++palette_clock;
#endif
    return true;
}
inline void palette_keep(unsigned index,const Re4dcUiImage& i){
#if RE4DC_UI_PALETTE_SLOTS
    PaletteCopy* cp=palette_copy(index);
    if(!cp){
        unsigned best=0;
        for(unsigned k=1;k<kPaletteCopies;++k)if(palette_used[k]<palette_used[best])best=k;
        palette_slot[index]=(unsigned char)(best+1);cp=&palette_copies[best];
    }
    PaletteCopy& c=*cp;palette_used[cp-palette_copies]=++palette_clock;
#else
    PaletteCopy& c=palette_copies[index%kPaletteCopies];
#endif
    c.owner=(unsigned short)(index+1);c.bytes=(unsigned short)i.palette_bytes;
    std::memcpy(c.data,i.palette,i.palette_bytes);
}
Entry* resolve_full(const Re4dcUiImage& image,const Re4dcModelPart* masked,bool pin){
#if RE4DC_D349_RENDERER_STACK
    if(masked){Key key{};if(!model_mask_key(masked,key))return nullptr;Entry* e=load(image,pin,&key);if(!e)log_pair_miss(masked,key);return e;}
#else
    (void)masked;
#endif
    return load(image,pin);
}
Entry* resolve(const Re4dcUiImage& image,const Re4dcModelPart* masked,bool pin){
    const Re4dcUiImage* mask=masked?&masked->mask:nullptr;
    unsigned shape,mask_shape=0;
    if(!handle_shape(image,shape,!mask) || (mask && !handle_shape(*mask,mask_shape,false))){DFA26_HIT(TextureShape)++handle_bypass;return resolve_full(image,masked,pin);}
    const bool indexed=image.format==8 || image.format==9;
    const void* mask_pixels=mask?mask->pixels:nullptr;const void* mask_palette=mask?mask->palette:nullptr;
    const unsigned a=unsigned(reinterpret_cast<std::uintptr_t>(image.pixels)),b=unsigned(reinterpret_cast<std::uintptr_t>(mask_pixels));
#if RE4DC_UI_QUAD_LEAN
    // UI_QUAD_LEAN (make-room F1; exact): two ways, the hashed slot and its partner (slot ^ 1). In the r101 square two
    // pairs of images (HUD / character) shared a slot and evicted each other every frame: 4 full resolves per drawn
    // tick (identity tables, memcmp, palette copies). A hit is the same whole-descriptor + stamp + live-palette test
    // in either way, so it returns the entry the full path resolves; only where a handle is kept changes. A miss
    // refills the way that holds this descriptor (a changed palette), else a stale way, else the older fill.
    // =2 also runs the full path on every hit and compares the entry ("UQL handle" lines); =3 is =2 with the handles
    // folded onto 8 slots (4 pairs), a stress check that exercises both ways and the refill choice.
    {
#if RE4DC_UI_QUAD_LEAN==3
        const unsigned slot=((a>>5)^(a>>13)^(b>>6)^(shape>>11))&7U;
#else
        const unsigned slot=((a>>5)^(a>>13)^(b>>6)^(shape>>11))&255U;
#endif
        Handle* const way[2]={&handle_table[slot],&handle_table[slot^1U]};
        for(unsigned w=0;w<2;++w){
            Handle& h=*way[w];
            if(h.pixels==image.pixels && h.shape==shape && h.palette==image.palette && h.mask_pixels==mask_pixels &&
               h.mask_shape==mask_shape && h.mask_palette==mask_palette && h.stamp>handle_reset && h.stamp>entry_closed[h.entry] &&
               h.palette_bytes==image.palette_bytes && (!indexed || palette_same(unsigned(&h-handle_table),image))){
                Entry& e=entries[h.entry];
                RE4DC_TOUCH(e);
#if RE4DC_UI_QUAD_LEAN>=2
                {
                    static unsigned hits[2],mismatch;
                    ++hits[w];
                    Entry* ref=resolve_full(image,masked,pin);
                    if(ref!=&e && mismatch++<8)re4dc_log("UQL handle MISMATCH way=%u entry=%d full=%d\n",w,int(&e-entries),ref?int(ref-entries):-1);
                    if(((hits[0]+hits[1])&4095)==0)re4dc_log("UQL handle hits=%u,%u misses=%u mismatch=%u\n",hits[0],hits[1],handle_misses,mismatch);
                }
#endif
                ++handle_hits;RE4DC_PROFILE_COUNT(TextureHits,1);return &e;
            }
        }
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
        DFA26_HIT(TextureHandleMiss)
#endif
        ++handle_misses;
        Entry* e=resolve_full(image,masked,pin);
        if(e){
            auto same=[&](const Handle& x){return x.pixels==image.pixels && x.shape==shape && x.palette==image.palette &&
                x.mask_pixels==mask_pixels && x.mask_shape==mask_shape && x.mask_palette==mask_palette;};
            auto stale=[&](const Handle& x){return !(x.stamp>handle_reset && x.stamp>entry_closed[x.entry]);};
            Handle& h=same(*way[0])?*way[0]:same(*way[1])?*way[1]:stale(*way[0])?*way[0]:stale(*way[1])?*way[1]:
                      way[0]->stamp<=way[1]->stamp?*way[0]:*way[1];
            h={image.pixels,image.palette,mask_pixels,mask_palette,shape,mask_shape,++handle_clock,HandleEntry(e-entries),(unsigned short)image.palette_bytes};
            if(indexed)palette_keep(unsigned(&h-handle_table),image);
        }
        return e;
    }
#endif
    Handle& h=handle_table[((a>>5)^(a>>13)^(b>>6)^(shape>>11))&255U];
    if(h.pixels==image.pixels && h.shape==shape && h.palette==image.palette && h.mask_pixels==mask_pixels &&
       h.mask_shape==mask_shape && h.mask_palette==mask_palette && h.stamp>handle_reset && h.stamp>entry_closed[h.entry] &&
       h.palette_bytes==image.palette_bytes && (!indexed || palette_same(unsigned(&h-handle_table),image))){
        Entry& e=entries[h.entry];
        RE4DC_TOUCH(e);
        ++handle_hits;RE4DC_PROFILE_COUNT(TextureHits,1);return &e;
    }
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    DFA26_HIT(TextureHandleMiss)
#endif
    ++handle_misses;
    Entry* e=resolve_full(image,masked,pin);
    if(e){
        h={image.pixels,image.palette,mask_pixels,mask_palette,shape,mask_shape,++handle_clock,HandleEntry(e-entries),(unsigned short)image.palette_bytes};
        if(indexed)palette_keep(unsigned(&h-handle_table),image);
    }
    return e;
}
#endif
#if RE4DC_TEX_RESIDENT
// Room-entry preload: runs on the render thread at the first frame after an
// identity set was bound (the room's entry fade), never while moving.
// 1. Select in priority order (room, enemy sets, player, weapon) while the
//    least possible size (16-bit or full-codebook VQ, as the fail-fast check)
//    fits the budget minus the byte reserve and the selection leaves
//    RE4DC_TEX_RESIDENT_RESERVE_SLOTS entries for first-sight loads.
// 2. Load the selection in package-name order, which is the order of the
//    files on the disc (ISO 9660 sorts names): short forward seeks instead of
//    a random walk (r101 took ~0.4 s per package in table order in Flycast).
// Loads pin to this frame so the loop only evicts older uploads (the previous
// room), never its own; at the end they become "requested last frame", so the
// scene's first frame is never short of an entry.
unsigned preload_least(unsigned width,unsigned height){
    unsigned pw=8,ph=8;while(pw<width)pw*=2;while(ph<height)ph*=2;
    return std::min(pw*ph*2,2048+pw*ph/4);
}
struct PreloadPick { Key key; unsigned short width,height,format; };
PreloadPick preload_picks[kTextureCount];
#if defined(RE4DC_ROOM_CHANGE_EVICT) && RE4DC_ROOM_CHANGE_EVICT
unsigned rce_retire_frame;bool rce_armed;   // ROOM_CHANGE_EVICT: set at room retirement (room_change_retire)
#endif
#if defined(RE4DC_ROOM_REENTRY_EVICT) && RE4DC_ROOM_REENTRY_EVICT
unsigned rce_last_room=~0U;                 // ROOM_REENTRY_EVICT: the room of the previous room-change evict
#endif
#if defined(RE4DC_SS11_ROOM_EVICT) && RE4DC_SS11_ROOM_EVICT
bool rce_force_all;                          // SS11_ROOM_EVICT: the next room-change evict closes every unpinned entry
#endif
#if RE4DC_QUALITY_ASSETS
bool preload_room_pass; // Standard: skip the index's drop keys in the room-identity pass only
#endif
#if RE4DC_COARSE_WORLD & 64
// COARSE_WORLD R3, this visit to the world's room (renderer-contract.md Revision 2): the new world VRAM and keys the
// world pass picked, against BUDGET.md revision 2's caps, and per kWorldTex entry (kWorldTexCount <= 48) whether it
// was new world VRAM, found resident by an earlier pass, or logged as capped.
constexpr unsigned kWorldNewKeys=16,kWorldNewBytes=84448;
unsigned world_new_n,world_new_bytes;
std::uint64_t world_new_mask,world_seen_mask,world_capped_mask;
#endif
#if defined(RE4DC_TEX_PKG_SKIP) && RE4DC_TEX_PKG_SKIP
// TEX_PKG_SKIP (native_model_registry.mk): a source texture of the room package's role rows (the GC TPLs its
// descriptors replace) is not uploaded at room entry; the package draws its own atlas. A source draw (fallback)
// still loads it on first sight.
extern "C" int re4dc_registry_source_key(unsigned crc,unsigned fnv);
unsigned pkg_skips;
#if defined(RE4DC_TEX_PKG_SKIP_LISTED) && RE4DC_TEX_PKG_SKIP_LISTED
unsigned pkg_listed_kept;   // TEX_PKG_SKIP_LISTED: room-list keys kept in the pass although a role row names them
#endif
#define RE4DC_PKG_SKIP(c,f) (re4dc_registry_source_key((c),(f))?(++pkg_skips,true):false)
#else
#define RE4DC_PKG_SKIP(c,f) false
#endif
#if defined(RE4DC_TEX_PKG_SKIP) && RE4DC_TEX_PKG_SKIP
void preload_select(const re4dc::texture::SourceIdentityTable& table,unsigned& n,unsigned& resident,unsigned& bytes,unsigned limit,unsigned byte_limit,bool pkg=false){
#else
void preload_select(const re4dc::texture::SourceIdentityTable& table,unsigned& n,unsigned& resident,unsigned& bytes,unsigned limit,unsigned byte_limit){
#endif
    for(unsigned i=0;i<table.count() && n+resident<limit;++i){
        unsigned crc,fnv,width,height,format;
        if(!table.record(i,crc,fnv,width,height,format) || !width || !height || width>1024 || height>1024)continue;
#if defined(RE4DC_TEX_PKG_SKIP) && RE4DC_TEX_PKG_SKIP
        if(pkg && RE4DC_PKG_SKIP(crc,fnv))continue;
#endif
#if RE4DC_QUALITY_ASSETS
        if(preload_room_pass && re4dc_std_dropped(crc,fnv))continue; RE4DC_GCIDLE_SKIP(crc,fnv)
#endif
        const Key key{crc,fnv};
        bool known=false;
        for(auto& e:entries)if(e.valid && e.key==key){if(e.frame!=frame){e.frame=frame;++resident;bytes+=e.package.vram_bytes();}known=true;break;}
        for(const auto& m:missing_keys)if(!known && (m.crc|m.fnv) && m==key)known=true;
        for(unsigned k=0;k<n && !known;++k)if(preload_picks[k].key==key)known=true;
        if(known)continue;
        const unsigned least=preload_least(width,height);
        if(bytes+least>byte_limit)continue; // a smaller one later may still fit
        preload_picks[n++]={key,(unsigned short)width,(unsigned short)height,(unsigned short)format};bytes+=least;
    }
}
#if RE4DC_ROOM_RESIDENT
// ROOM_RESIDENT=1 (Makefile; render only; lane vram12 D5): dc/resident.bin lists, per room, the textures its scenes
// load on first sight after the preload (tools/d367/vram/resident_keys.py, from benchmark and play logs: effects,
// PS2 cast and room objects, HUD). They join each room-entry pass after all the others, under the same slot and
// byte limits, so the room's set loads once at its entry instead of in its first frames of play. The file is
// 16-byte records (u16 room, width, height, format; u32 crc, fnv; room 0 pads it to whole 512-byte pieces), read a
// piece at a time into a stack buffer (re4dc::texture::read_file_range: a handle per read, IO_SERIAL like the opens);
// without the file there is no list.
unsigned resident_listed,resident_picked;
#if defined(RE4DC_RESIDENT_LIST_CACHE) && RE4DC_RESIDENT_LIST_CACHE
re4dc::texture::ResidentListCache resident_list_cache;
#endif
void preload_resident(unsigned& n,unsigned& resident,unsigned& bytes,unsigned limit,unsigned byte_limit){
    re4dc::profile::Source src{};
#if defined(__sh__)
    re4dc_profile_source(&src);
#endif
    resident_listed=resident_picked=0;
#if defined(RE4DC_RESIDENT_LIST_CACHE) && RE4DC_RESIDENT_LIST_CACHE
    using Rec=re4dc::texture::ResidentListRecord;
#else
    struct Rec { std::uint16_t room,width,height,format; std::uint32_t crc,fnv; };
#endif
    static_assert(sizeof(Rec)==16,"dc/resident.bin record");
    Rec buf[32];
    unsigned pieces=0;
#if defined(RE4DC_CORE_PIN) && RE4DC_CORE_PIN==2
    unsigned own=0;
#endif
#if defined(RE4DC_RESIDENT_LIST_CACHE) && RE4DC_RESIDENT_LIST_CACHE
    // The disc list is immutable. Keep only copied rows for this room, never owner/archive pointers.
    const bool cached=resident_list_cache.matches(src.room);
    if(!cached)resident_list_cache.begin(src.room);
    unsigned long long first_file_bytes=0;
    bool have_file_bytes=false,same_file_bytes=true;
    for(unsigned block=0;;++block){
        const Rec* records=buf;
        unsigned record_count=32;
        if(cached){
            if(block)break;
            records=resident_list_cache.data();record_count=resident_list_cache.size();
        }else{
            unsigned long long file_bytes=0;
            const auto result=re4dc::texture::read_file_range("/cd/dc/resident.bin",pieces*sizeof(buf),buf,
                                                            sizeof(buf),&file_bytes);
            if(!have_file_bytes){first_file_bytes=file_bytes;have_file_bytes=true;}
            else if(first_file_bytes!=file_bytes)same_file_bytes=false;
            if(result!=re4dc::texture::RangeRead::ok){
                // An exact EOF certifies a complete list. Errors, trailing partial pieces and overflow retry later.
                const bool complete=result==re4dc::texture::RangeRead::short_file && same_file_bytes &&
                                    file_bytes==static_cast<unsigned long long>(pieces)*sizeof(buf);
                resident_list_cache.finish(complete);break;
            }
            ++pieces;
            // Capture independently of today's admission limits: a later owner/pass may have more space.
            for(const auto& r:buf)resident_list_cache.append(r);
        }
        // Discovery must not depend on texture admission: earlier owner passes may fill the budget.
        for(unsigned i=0;i<record_count;++i){
            const Rec& r=records[i];
#else
    for(;re4dc::texture::read_file_range("/cd/dc/resident.bin",pieces*sizeof(buf),buf,sizeof(buf),nullptr)==
          re4dc::texture::RangeRead::ok;++pieces){
        for(unsigned i=0;i<32 && n+resident<limit;++i){
            const Rec& r=buf[i];
#endif
#if defined(RE4DC_CORE_PIN) && RE4DC_CORE_PIN
            if(!r.room && r.width && (r.crc|r.fnv)){   // CORE_PIN: a core key, pinned and listed in every room
                const Key ck{r.crc,r.fnv};bool have=false;
                for(unsigned k=0;k<core_nkeys && !have;++k)have=core_keys[k]==ck;
                if(!have && core_nkeys<kCoreKeys)core_keys[core_nkeys++]=ck;
            }
#if RE4DC_CORE_PIN==2
            if(r.room && r.room==src.room)++own;
#endif
            if((r.room!=src.room && r.room) || !r.width || !r.height || r.width>1024 || r.height>1024)continue;
#else
            if(r.room!=src.room || !r.width || !r.height || r.width>1024 || r.height>1024)continue;
#endif
#if defined(RE4DC_RESIDENT_LIST_CACHE) && RE4DC_RESIDENT_LIST_CACHE
            // Keep admission and its accounting bounded after discovering core keys and room-list ownership.
            if(n+resident>=limit)continue;
#endif
            ++resident_listed;
#if defined(RE4DC_TEX_PKG_SKIP) && RE4DC_TEX_PKG_SKIP
#if defined(RE4DC_TEX_PKG_SKIP_LISTED) && RE4DC_TEX_PKG_SKIP_LISTED
            // TEX_PKG_SKIP_LISTED (native_model_registry.mk): a key of this room's own list (a texture its scenes loaded
            // on first sight) stays in the pass even when a package role row names it: registry actors still draw it
            // from the source path on some frames (r207: the inventory open draws the zealot / Ashley roles' source
            // TPLs, 16 uploads in play). Core keys (room 0) keep the skip.
            if(!r.room && RE4DC_PKG_SKIP(r.crc,r.fnv))continue;
            if(r.room && re4dc_registry_source_key(r.crc,r.fnv))++pkg_listed_kept;
#else
            if(RE4DC_PKG_SKIP(r.crc,r.fnv))continue;
#endif
#endif
            const Key key{r.crc,r.fnv};
            bool known=false;
            for(auto& e:entries)if(e.valid && e.key==key){if(e.frame!=frame){e.frame=frame;++resident;bytes+=e.package.vram_bytes();}known=true;break;}
            for(const auto& m:missing_keys)if(!known && (m.crc|m.fnv) && m==key)known=true;
            for(unsigned k=0;k<n && !known;++k)if(preload_picks[k].key==key)known=true;
            const unsigned least=preload_least(r.width,r.height);
            if(known || bytes+least>byte_limit)continue;
            preload_picks[n++]={key,r.width,r.height,r.format};bytes+=least;++resident_picked;
        }
    }
    if(pieces)re4dc_log("native texture preload: resident list room=%03x pieces=%u listed=%u picked=%u\n",src.room,pieces,
                        resident_listed,resident_picked);
#if defined(RE4DC_RESIDENT_LIST_CACHE) && RE4DC_RESIDENT_LIST_CACHE
    if(cached)re4dc_log("native resident list cache: room=%03x rows=%u listed=%u picked=%u reads=0\n",
                       src.room,resident_list_cache.size(),resident_listed,resident_picked);
#endif
#if defined(RE4DC_TEX_PKG_SKIP) && RE4DC_TEX_PKG_SKIP && defined(RE4DC_TEX_PKG_SKIP_LISTED) && RE4DC_TEX_PKG_SKIP_LISTED
    if(pieces)re4dc_log("TEXPKG listed kept=%u\n",pkg_listed_kept);
    pkg_listed_kept=0;
#endif
#if defined(RE4DC_CORE_PIN) && RE4DC_CORE_PIN
#if RE4DC_CORE_PIN==2
    // CORE_PIN=2: the core keys are pinned only where the room has its own list (r101: the post-bell radio call's frag
    // window evicted them; test 14 open VRAM item). Elsewhere they are plain LRU entries as with CORE_PIN=0: pinned in
    // r105 they left the chapter 1-2 results picture (495x150) without a contiguous block even with the yield.
    core_room_on=own!=0;
    if(pieces)re4dc_log("native texture preload: core keys=%u (%s)\n",core_nkeys,core_room_on?"pinned":"not pinned: no room list");
#else
    if(pieces)re4dc_log("native texture preload: core keys=%u (pinned)\n",core_nkeys);
#endif
#endif
}
#endif
#if RE4DC_IO_PROBE
extern "C" void re4dc_iowrap_reset(void);                                            // io_wrap.cpp
extern "C" void re4dc_iowrap_report(const char* what, unsigned cycle, unsigned long long wall_us);
#endif
#if RE4DC_TEX_META_EVICT
bool ensure_model_storage();   // below: the native model slab (64 KiB of KOS heap, kept once allocated)
#endif
void preload_identities(){
    preload_pending=false;++preload_runs;
#if defined(RE4DC_GANADO_ATLAS_DROP) && RE4DC_GANADO_ATLAS_DROP
    gad_room_states();
#endif
#if RE4DC_TEX_META_EVICT
    // The native model slab first: the slab is allocated at the first native model draw and kept from then on, which
    // came after the room-entry preload, so a preload that filled the KOS heap with texture descriptors took its
    // 64 KiB (lane vram12 D5 trial: "native model slab: allocation failed", the native model path off for r101).
    if(!model_packets)ensure_model_storage();
#endif
#if RE4DC_IO_PROBE
    re4dc_iowrap_reset(); // IO_PROBE (test only): this pass's IO tables ("iowrap: preload" below)
#endif
#if RE4DC_UI_VRAM && RE4DC_UI_FRAG_LATCH
#if RE4DC_UI_FRAG_RESERVE
    frag_release("room");frag_want=0;
#endif
    frag_key=Key{}; // a new room: the pool has a new shape
#endif
#if defined(RE4DC_PS2_ROOM_PIN) && RE4DC_PS2_ROOM_PIN
    {
        const unsigned r=re4dc_ps2_mesh_room();room_pin_key=Key{};
        for(const auto& q:kRoomPins)if(q.room==r)room_pin_key=q.key;
        if(room_pin_key.crc)re4dc_log("PS2PIN room=%03x key=%08x-%08x\n",r,room_pin_key.crc,room_pin_key.fnv);
    }
#endif
    const std::uint64_t start=timer_us_gettime64();
    const unsigned loads=preload_loads,skipped=preload_skipped;
#if RE4DC_TEX_PACK
    const unsigned pack_errors=pack_error_skips;
#endif
    const unsigned budget=(RE4DC_UI_VRAM?vram_budget:kVramBudget),reserve=RE4DC_TEX_RESIDENT_RESERVE_KB*1024U;
    unsigned pinned=0,pinned_bytes=0;
    for(const auto& e:entries)if(e.valid && RE4DC_ENTRY_PINNED(e)){++pinned;pinned_bytes+=e.package.vram_bytes();}
    const unsigned limit=kTextureCount>RE4DC_TEX_RESIDENT_RESERVE_SLOTS+pinned?kTextureCount-RE4DC_TEX_RESIDENT_RESERVE_SLOTS-pinned:0;
    const unsigned byte_limit=budget>reserve+pinned_bytes?budget-reserve-pinned_bytes:0;
    unsigned n=0,resident=0,bytes=0; // resident: already uploaded, pinned for the loop
#if RE4DC_PS2_PRELOAD_LEAN
    // PS2_PRELOAD_LEAN (game30.mk): with the room's PS2 world package open, its scenery is drawn from the package's
    // own textures, so those are the room pass; the room archive's identities (the GameCube scenery, ~1 MB nothing
    // draws: TEX_USE_CENSUS r100 east walk 103 of 105 idle for 20 s) and the Standard index's shells / impostor
    // atlases are not preloaded. Anything an object of the room does draw from them loads on first sight.
    unsigned ps2t[4];
    const bool ps2_lean=re4dc_ps2_mesh_texture(0,ps2t)!=0;
    if(ps2_lean){
        ++preload_ps2_lean_runs;
        for(unsigned i=0;re4dc_ps2_mesh_texture(i,ps2t) && n+resident<limit;++i){
            const Key key{ps2t[0],ps2t[1]};
            bool known=false;
            for(auto& e:entries)if(e.valid && e.key==key){if(e.frame!=frame){e.frame=frame;++resident;bytes+=e.package.vram_bytes();}known=true;break;}
            for(const auto& m:missing_keys)if(!known && (m.crc|m.fnv) && m==key)known=true;
            for(unsigned k=0;k<n && !known;++k)if(preload_picks[k].key==key)known=true;
            const unsigned least=preload_least(ps2t[2],ps2t[3]);
            if(known || bytes+least>byte_limit)continue;
            preload_picks[n++]={key,(unsigned short)ps2t[2],(unsigned short)ps2t[3],5};bytes+=least;
        }
    }
    else {
#endif
#if RE4DC_QUALITY_ASSETS
    preload_room_pass=true;preload_select(room_identities,n,resident,bytes,limit,byte_limit);preload_room_pass=false;
    // Standard: the textures the index adds (shells, impostor atlases), after the room pass.
    {unsigned t[5];
     for(unsigned i=0;re4dc_std_texture(i,t) && n+resident<limit;++i){
        const Key key{t[0],t[1]};
        bool known=false;
        for(auto& e:entries)if(e.valid && e.key==key){if(e.frame!=frame){e.frame=frame;++resident;bytes+=e.package.vram_bytes();}known=true;break;}
        for(const auto& m:missing_keys)if(!known && (m.crc|m.fnv) && m==key)known=true;
        for(unsigned k=0;k<n && !known;++k)if(preload_picks[k].key==key)known=true;
        if(known || bytes+t[4]>byte_limit)continue;
        preload_picks[n++]={key,(unsigned short)t[2],(unsigned short)t[3],5};bytes+=t[4];
     }}
#else
    preload_select(room_identities,n,resident,bytes,limit,byte_limit);
#endif
#if RE4DC_PS2_PRELOAD_LEAN
    }
#endif
#if defined(RE4DC_TEX_PKG_SKIP) && RE4DC_TEX_PKG_SKIP
    {const unsigned s0=pkg_skips;
     for(auto& e:enemy_identities)if(e.archive)preload_select(e.table,n,resident,bytes,limit,byte_limit,true);
     re4dc_log("TEXPKG preload enemy skips=%u total=%u\n",pkg_skips-s0,pkg_skips);}
#else
    for(auto& e:enemy_identities)if(e.archive)preload_select(e.table,n,resident,bytes,limit,byte_limit);
#endif
    preload_select(player_identities,n,resident,bytes,limit,byte_limit);preload_select(weapon_identities,n,resident,bytes,limit,byte_limit);
#if RE4DC_COARSE_WORLD & 64
    // COARSE_WORLD R3 (renderer-contract.md 5, Revision 2): in the world data's room, its texture list (kWorldTex,
    // most important first), after the room, Standard and character passes, so their picks are the same as without it.
    // - A listed key one of those passes picked counts as resident (it loads pinned with them).
    // - A listed key already uploaded is pinned like the room set while picks + pins stay under the world's slot
    //   limit, which lends it half of the first-sight reserve (192 - 16 - pinned); past that it stays resident but
    //   unpinned (unpinned=).
    // - A listed key that an earlier pass of this visit found resident or picked, and that is no longer uploaded
    //   (evicted while unpinned), loads on first sight, as without R3 (evicted=): it is not picked again.
    // - Any other key is new world VRAM: picked in list order within BUDGET.md revision 2's caps for this visit to
    //   the room (16 keys, 84,448 B; a key counts once) while it fits the slot limit and the byte budget. Past the
    //   caps (capped=; one log line per key and visit) or the limits (nofit=) it loads on first sight, as without R3.
    //   Its size is the entry's bytes, which the data gate (coarse_world.cpp static_asserts, ref_decoder.py) holds
    //   to its real size: 2048 + w*h/4 (VQ), w*h*2 (16-bit), or 2048 + w*h/16 + 32 for a TreeAtlas key (4-bit
    //   palettised VQ). No disc access: the pass runs in every room-entry preload, some of them inside the room's
    //   load wait, where a stall would change the number of frames the wait takes.
    unsigned world_listed=0,world_resident=0,world_unpinned=0,world_np=0,world_nofit=0,world_absent=0,world_capped=0,world_evicted=0;
    Key world_picks[kWorldNewKeys];
    if(!re4dc_coarse_world_room()){ // another room: the next visit starts afresh
        world_new_n=0;world_new_bytes=0;world_new_mask=0;world_seen_mask=0;world_capped_mask=0;
    }else{
        const unsigned wlimit=kTextureCount>RE4DC_TEX_RESIDENT_RESERVE_SLOTS/2+pinned?kTextureCount-RE4DC_TEX_RESIDENT_RESERVE_SLOTS/2-pinned:0;
        unsigned t[5];
        for(unsigned i=0;i<64 && re4dc_coarse_world_tex(i,t);++i){
            ++world_listed;
            const Key key{t[0],t[1]};
            const std::uint64_t bit=std::uint64_t(1)<<i;
            bool picked=false;
            for(unsigned k=0;k<n && !picked;++k)if(preload_picks[k].key==key)picked=true;
            if(picked){world_seen_mask|=bit;++world_resident;continue;}
            Entry* up=nullptr;
            for(auto& e:entries)if(e.valid && e.key==key){up=&e;break;}
            if(up){
                world_seen_mask|=bit;
                if(up->frame==frame)++world_resident;
                else if(n+resident<wlimit){up->frame=frame;++resident;bytes+=up->package.vram_bytes();++world_resident;}
                else ++world_unpinned;
                continue;
            }
            bool absent=false;
            for(const auto& m:missing_keys)if((m.crc|m.fnv) && m==key)absent=true;
            if(absent){++world_absent;continue;}
            if((world_seen_mask|world_new_mask)&bit){++world_evicted;continue;}
            const unsigned size=t[4];
            if(world_new_n>=kWorldNewKeys || world_new_bytes+size>kWorldNewBytes){
                ++world_capped;
                if(!(world_capped_mask&bit)){
                    world_capped_mask|=bit;
                    re4dc_log("COARSE world tex capped %08x-%08x %ux%u bytes=%u visit_new=%u/%u keys=%u/%u\n",key.crc,key.fnv,t[2],t[3],
                        size,world_new_bytes,kWorldNewBytes,world_new_n,kWorldNewKeys);
                }
                continue;
            }
            if(n+resident>=wlimit || bytes+size>byte_limit){++world_nofit;continue;}
            world_new_mask|=bit;++world_new_n;world_new_bytes+=size;
            world_picks[world_np++]=key;
            preload_picks[n++]={key,(unsigned short)t[2],(unsigned short)t[3],5};bytes+=size;
        }
    }
#endif
#if RE4DC_ROOM_RESIDENT
    preload_resident(n,resident,bytes,limit,byte_limit);
#endif
    // Package-name order ("%08x-%08x": crc, then fnv).
    for(unsigned i=1;i<n;++i){
        const PreloadPick p=preload_picks[i];unsigned j=i;
        for(;j && (preload_picks[j-1].key.crc>p.key.crc || (preload_picks[j-1].key.crc==p.key.crc && preload_picks[j-1].key.fnv>p.key.fnv));--j)preload_picks[j]=preload_picks[j-1];
        preload_picks[j]=p;
    }
#if RE4DC_PRELOAD_LARGE_FIRST
    // PRELOAD_LARGE_FIRST=1 (Makefile; render only): two forward sweeps instead of one, the picks of at least
    // kPreloadLarge bytes first, then the rest, each in package-name order (disc order). Small packages loaded
    // between large ones leave holes no later large package fits ("no contiguous block" with free VRAM).
    {
        constexpr unsigned kPreloadLarge=16U*1024U;
        unsigned m=0;
        for(unsigned i=0;i<n;++i)if(preload_least(preload_picks[i].width,preload_picks[i].height)>=kPreloadLarge){
            const PreloadPick p=preload_picks[i];
            for(unsigned j=i;j>m;--j)preload_picks[j]=preload_picks[j-1];
            preload_picks[m++]=p;
        }
    }
#endif
#if defined(RE4DC_SS_HOLD_RESTORE) && RE4DC_SS_HOLD_RESTORE
    if(hold_restore){
        // SS_HOLD_RESTORE: this pass loads only the keys the sub screen evicted from the view before it opened.
        unsigned m=0;
        for(unsigned i=0;i<n;++i){
            bool keep=false;
            for(unsigned k=0;k<hold_nkeys && !keep;++k)keep=hold_keys[k]==preload_picks[i].key;
            if(keep)preload_picks[m++]=preload_picks[i];
        }
        re4dc_log("native texture hold restore: picks=%u of %u (remembered %u)\n",m,n,hold_nkeys);
        n=m;hold_restore=false;hold_nkeys=0;
    }
#endif
#if defined(RE4DC_ROOM_CHANGE_EVICT) && RE4DC_ROOM_CHANGE_EVICT
    if(rce_armed){
        // ROOM_CHANGE_EVICT: the first pass of a new room. Its listed resident entries are pinned to this frame by
        // preload_select; close every other kept entry the old room did not draw in its last RE4DC_ROOM_CHANGE_EVICT
        // frames (leased, fx-pool and room-pinned entries stay). The caller completed the TA and render fences, as for
        // load()'s evictions.
        rce_armed=false;
        unsigned closed=0,closed_bytes=0,kept=0,kept_bytes=0;
#if defined(RE4DC_ROOM_REENTRY_EVICT) && RE4DC_ROOM_REENTRY_EVICT
        // ROOM_REENTRY_EVICT: the same room entered again (Continue after a death, a room's own door): the old visit's
        // last frames drew this room's dynamic set, so the window kept it (57 entries, 526 KB in r101) beside the
        // pinned resident list and the next uploads found no contiguous block. On a re-entry every entry this pass did
        // not pin closes; the room's listed set is pinned above and loads with the preload.
        re4dc::profile::Source rce_src{};
#if defined(__sh__)
        re4dc_profile_source(&rce_src);
#endif
        bool rce_same=rce_src.room==rce_last_room;rce_last_room=rce_src.room;
#if defined(RE4DC_SS11_ROOM_EVICT) && RE4DC_SS11_ROOM_EVICT
        if(rce_force_all){rce_same=true;rce_force_all=false;}   // a room change behind a chapter-end screen
#endif
#endif
        for(auto& e:entries){
            if(!e.valid || RE4DC_ENTRY_PINNED(e))continue;
            const unsigned sz=e.package.vram_bytes();
#if defined(RE4DC_VRAM_ROOM_ARENA) && RE4DC_VRAM_ROOM_ARENA
            // VRAM_ROOM_ARENA: the old room's region is freed as one block; core keys live at the top. Nothing else
            // is kept, so the new room's preload fills one hole-free region from the bottom.
            if(RE4DC_CORE_PINNED(e)){++kept;kept_bytes+=sz;continue;}
#elif defined(RE4DC_ROOM_REENTRY_EVICT) && RE4DC_ROOM_REENTRY_EVICT
            if(!rce_same && e.frame+RE4DC_ROOM_CHANGE_EVICT>=rce_retire_frame){++kept;kept_bytes+=sz;continue;}
#else
            if(e.frame+RE4DC_ROOM_CHANGE_EVICT>=rce_retire_frame){++kept;kept_bytes+=sz;continue;}
#endif
            close_entry(e);++closed;closed_bytes+=sz;
        }
#if defined(RE4DC_ROOM_REENTRY_EVICT) && RE4DC_ROOM_REENTRY_EVICT
        if(rce_same)re4dc_log("native UI: room re-entry evict: room=%03x\n",unsigned(rce_src.room));
#endif
        re4dc_log("native UI: room change evict: closed=%u kb=%u kept=%u kept_kb=%u listed_resident=%u free=%u window=%u\n",
            closed,closed_bytes/1024,kept,kept_bytes/1024,resident,(unsigned)pvr_mem_available(),unsigned(RE4DC_ROOM_CHANGE_EVICT));
    }
#endif
    bool full=false;
#if RE4DC_TEX_KEEP
    // Kept entries of earlier rooms still hold VRAM and count in `used`; load() evicts them
    // (oldest first) for these uploads. Full is judged on this frame's pins plus what is
    // evictable, recomputed per load as pins grow and evictions free the pool.
    unsigned kept=0,kept_bytes=0;
    for(const auto& e:entries)if(e.valid && e.frame!=frame){++kept;kept_bytes+=e.package.vram_bytes();}
#endif
#if defined(RE4DC_TEX_PACK_WINDOW) && RE4DC_TEX_PACK_WINDOW
    // TEX_PACK_WINDOW (game30.mk): this pass reads tex.pak through a read-ahead window (texture_package.hpp), a staging
    // buffer from the current heap held only for the pass (the same transient staging load() uses). tex.pak is laid
    // out in each room's preload order, so the room's pictures come in a few large reads. No buffer: as before.
    void* win_mem=n?re4dc_ui_stage_alloc(RE4DC_TEX_PACK_WINDOW*1024U+32U):nullptr;
    const auto win0=re4dc::texture::pack_window_stats();
    const bool win_on=win_mem && re4dc::texture::pack_window_open(texpack::kPath,
        reinterpret_cast<void*>((reinterpret_cast<std::uintptr_t>(win_mem)+31U)&~std::uintptr_t(31)),RE4DC_TEX_PACK_WINDOW*1024U);
#endif
    for(unsigned i=0;i<n;++i){
        // The reserve is also kept in the real pool: VQ page placement pads blocks
        // beyond the accounted bytes (r100 ended at 8,936 B free with 182 KB of budget left).
#if RE4DC_TEX_KEEP
        unsigned pins=0,stale=0;
        for(const auto& e:entries)if(e.valid){if(e.frame==frame)pins+=e.package.vram_bytes();else stale+=e.package.vram_bytes();}
        if(pins+reserve>=budget || pvr_mem_available()+stale<reserve+preload_least(preload_picks[i].width,preload_picks[i].height)){full=true;break;}
#else
        if(used+reserve>=budget || pvr_mem_available()<reserve+preload_least(preload_picks[i].width,preload_picks[i].height)){full=true;break;}
#endif
#if RE4DC_TEX_META_EVICT
        if(kos_headroom()<kKosReserve){full=true;break;}   // KOS heap: the rest load on first sight
#endif
        const PreloadPick& p=preload_picks[i];
        const Re4dcUiImage image{reinterpret_cast<const void*>(1),nullptr,p.width,p.height,p.format,0xffffffffU,0};
        if(load(image,true,&p.key))++preload_loads;else ++preload_skipped;
    }
#if defined(RE4DC_TEX_PACK_WINDOW) && RE4DC_TEX_PACK_WINDOW
    if(win_on){
        re4dc::texture::pack_window_close();
        const auto w=re4dc::texture::pack_window_stats();
        re4dc_log("native texture preload: pack window kb=%u fills=%u hits=%u misses=%u read_kb=%u\n",unsigned(RE4DC_TEX_PACK_WINDOW),
            w.fills-win0.fills,w.hits-win0.hits,w.misses-win0.misses,w.kb-win0.kb);
    }else if(n)re4dc_log("native texture preload: pack window off (buffer %s)\n",win_mem?"ok, pack open failed":"not allocated");
    if(win_mem)re4dc_ui_stage_free(win_mem);
#endif
#if RE4DC_UI_VRAM && RE4DC_VRAM_CENSUS
    // VRAM_CENSUS (test only): the picks a full pass left for first sight.
    if(full){unsigned left=0,least=0;for(unsigned k=0;k<n;++k){bool have=false;for(const auto& e:entries)if(e.valid && e.key==preload_picks[k].key){have=true;break;}
        if(have)continue;++left;least+=preload_least(preload_picks[k].width,preload_picks[k].height);
        re4dc_log("native texture preload: left %08x-%08x %ux%u fmt=%u\n",unsigned(preload_picks[k].key.crc),unsigned(preload_picks[k].key.fnv),
            unsigned(preload_picks[k].width),unsigned(preload_picks[k].height),unsigned(preload_picks[k].format));}
        re4dc_log("native texture preload: full pass left=%u least_bytes=%u\n",left,least);}
#endif
    if(frame)for(auto& e:entries)if(e.valid && e.frame==frame)e.frame=frame-1;
#if defined(RE4DC_ROOM_LEFTOVER_FIT) && RE4DC_ROOM_LEFTOVER_FIT
    {
        // ROOM_LEFTOVER_FIT (Makefile; render only; lane fix18, #39): ROOM_CHANGE_EVICT keeps what the old room drew in
        // its last frames. Through a door that shows the old room to the end (r10f -> r200: 54 r10f world pictures,
        // 611 KB) the leftovers sat beside r200's large set: 72 KB free, 8 KB largest block, every later load evicted,
        // the EFFECT_ROOM guard refused 20 effect loads (366 sprites dropped) and the PS2 world prep of fa6fe38c found
        // no block. After each preload pass, while the budget has less than kLeftoverHeadroom free, close the previous
        // room's leftovers (last drawn at or before the room change, not pinned, leased or core), oldest first. A room
        // with room to spare keeps them as before (the common set the old room drew to the end).
        constexpr unsigned kLeftoverHeadroom=512U*1024U;
        unsigned lclosed=0,lbytes=0;
        while(used+kLeftoverHeadroom>budget){
            Entry* victim=nullptr;
            for(auto& e:entries)if(e.valid && e.frame<=rce_retire_frame && !RE4DC_ENTRY_PINNED(e) && !RE4DC_CORE_PINNED(e) &&
                                   (!victim || e.frame<victim->frame))victim=&e;
            if(!victim)break;
            lbytes+=victim->package.vram_bytes();++lclosed;close_entry(*victim);
        }
        if(lclosed)re4dc_log("native UI: room leftover fit: closed=%u kb=%u used=%u budget=%u free=%u\n",lclosed,lbytes/1024,used,budget,
                             (unsigned)pvr_mem_available());
    }
#endif
    re4dc_log("native texture preload: frame=%u picked=%u resident=%u loads=%u skipped=%u full=%d used=%u budget=%u entries=%u us=%u\n",frame,n,resident,preload_loads-loads,
        preload_skipped-skipped,full?1:0,used,budget,kTextureCount,unsigned(timer_us_gettime64()-start));
#if RE4DC_TEX_PACK
    // Only while the pack's init is waiting to retry: a failed lookup sector of a ready pack would otherwise re-arm
    // the pass every frame (its keys load on first sight once the sector re-reads).
    if(pack_error_skips!=pack_errors && !texpack::settled()){
        preload_after_pack=true;
        re4dc_log("native texture preload: %u picks met a pack read error; the pass runs again when the pack settles\n",
                  pack_error_skips-pack_errors);
    }
#endif
#if RE4DC_PS2_PRELOAD_LEAN
    if(ps2_lean)re4dc_log("native texture preload: ps2 world room pass (runs=%u)\n",preload_ps2_lean_runs);
#endif
#if RE4DC_IO_PROBE
    re4dc_iowrap_report("preload",preload_runs,timer_us_gettime64()-start);
#endif
#if RE4DC_TEX_KEEP
    re4dc_log("native texture keep: kept=%u kept_kb=%u reused=%u free=%u retries=%u\n",kept,kept_bytes/1024,resident,(unsigned)pvr_mem_available(),vram_retries);
#endif
#if RE4DC_COARSE_WORLD & 64
    if(world_listed){
        // loaded: the world picks now uploaded (new: their VRAM); missing: listed keys neither resident nor loaded
        // (they load on first sight, as without R3); visit: this visit's new world VRAM and keys against the caps
        unsigned world_loaded=0,world_bytes=0;
        for(unsigned k=0;k<world_np;++k)for(const auto& e:entries)if(e.valid && e.key==world_picks[k]){++world_loaded;world_bytes+=e.package.vram_bytes();break;}
        re4dc_log("COARSE world tex listed=%u loaded=%u resident=%u new=%u missing=%u nofit=%u absent=%u unpinned=%u evicted=%u "
            "capped=%u visit=%u/%u B %u/%u keys\n",world_listed,world_loaded,world_resident,world_bytes,
            world_listed-world_resident-world_unpinned-world_loaded,world_nofit,world_absent,world_unpinned,world_evicted,world_capped,
            world_new_bytes,kWorldNewBytes,world_new_n,kWorldNewKeys);
    }
#endif
#if RE4DC_UI_VRAM && RE4DC_VRAM_CENSUS
    void vram_census(const char*);vram_census("preload");
#endif
#if RE4DC_VRAM_ROOM_LOG
    vram_room_track();vram_room_sample("preload");
#endif
}
#endif
#if RE4DC_PS2_FX_ADDITIONS && RE4DC_TEX_RESIDENT
#include "include/native_effect_stage1_prepare.inc"
#endif
#if RE4DC_UI_VRAM && RE4DC_VRAM_CENSUS
// VRAM_CENSUS (test only): texture RAM census. VRAM_PAGES reports its own lists; the KOS dlmalloc
// heap is walked chunk by chunk (4-byte size word, PREV_INUSE in the next chunk; top chunk free).
std::uintptr_t census_heap_base;
#if RE4DC_VRAM_PAGES
extern "C" void re4dc_vram_pages_census(unsigned* out);
#else
extern "C" struct mallinfo pvr_int_mallinfo(void);
#endif
void vram_census(const char* where){
    unsigned c[13]={};
#if RE4DC_VRAM_PAGES
    re4dc_vram_pages_census(c);
#else
    if(census_heap_base){
        const struct mallinfo mi=pvr_int_mallinfo();
        const std::uintptr_t end=census_heap_base+unsigned(mi.arena);
        std::uintptr_t ch=census_heap_base;
        while(((ch+8)&31U)!=0)ch+=4;             // first chunk: its user pointer is 32-byte aligned
        for(unsigned guard=0;ch+16<=end && guard<4096;++guard){
            const unsigned sz=*reinterpret_cast<volatile const unsigned*>(ch+4)&~3U;
            if(sz<16 || ch+sz>end+32)break;
            const std::uintptr_t nx=ch+sz;
            const bool inuse=nx+8<=end && (*reinterpret_cast<volatile const unsigned*>(nx+4)&1U);
            if(inuse){++c[0];c[1]+=sz;}
            else {++c[2];c[3]+=sz;if(sz>c[4])c[4]=sz;++c[5+(sz<2048?0:sz<8192?1:sz<32768?2:sz<131072?3:4)];}
            ch=nx;
        }
        const unsigned tail=unsigned(PVR_RAM_INT_TOP-end); // never sbrk'd: free, contiguous with top
        c[3]+=tail;
    }
#endif
    unsigned ntex=0,tex_bytes=0;
    for(const auto& e:entries)if(e.valid){++ntex;tex_bytes+=e.package.vram_bytes();}
    re4dc_log("vram census: %s frame=%u pages=%d budget=%u used=%u textures=%u tex_bytes=%u claims=%u avail=%u allocs=%u alloc_bytes=%u extents=%u free=%u largest=%u hist=%u/%u/%u/%u/%u fails=%u peak_alloc=%u peak_free=%u retries=%u evicted=%u\n",
        where,frame,RE4DC_VRAM_PAGES,vram_budget,used,ntex,tex_bytes,vram_claims,(unsigned)pvr_mem_available(),c[0],c[1],c[2],c[3],c[4],c[5],c[6],c[7],c[8],c[9],c[10],c[11],c[12],vram_retries,reclaimed);
}
#if RE4DC_VRAM_PAGES
// VRAM_CENSUS: the texture RAM map when a load finds no contiguous block (first two failures of a run).
// One token per allocation: offset/KiB then P (cache entry used this frame or leased), U (cache entry,
// evictable) or X (no cache entry: glyph atlas, overlay slab, OSD, movie, sub screen, lake, ...), and the
// entry key for P / U. Free extents in between show as gaps in the offsets.
extern "C" unsigned re4dc_vram_pages_snapshot(unsigned* off,unsigned* len,unsigned cap,unsigned* base,unsigned* pool);
void vram_frag_dump(unsigned need){
    static unsigned dumps;
    if(dumps>=2)return;
    ++dumps;
    constexpr unsigned kCap=512;
    static unsigned off[kCap],len[kCap];static short owner[kCap];
    unsigned base=0,pool=0;
    const unsigned n=re4dc_vram_pages_snapshot(off,len,kCap,&base,&pool);
    auto block_of=[&](unsigned a)->int{unsigned lo=0,hi=n;while(lo<hi){const unsigned m=(lo+hi)/2;if(off[m]+len[m]<=a)lo=m+1;else hi=m;}
        return lo<n && off[lo]<=a ? int(lo) : -1;};
    for(unsigned i=0;i<n;++i)owner[i]=-1;
    for(unsigned ei=0;ei<kTextureCount;++ei){
        const Entry& e=entries[ei];
        if(!e.valid || !e.package.vram_bytes())continue;
        const unsigned count=e.package.header().texture_count;
        for(unsigned t=0;t<count;++t){
            const pvr_ptr_t p=e.package.pvr_texture(t);if(!p)continue;
            const int b=block_of(unsigned(p)-base);if(b>=0)owner[b]=short(ei);
        }
    }
    unsigned xb=0,pb=0,ub=0;
    for(unsigned i=0;i<n;++i){if(owner[i]<0)xb+=len[i];else if(RE4DC_ENTRY_PINNED(entries[owner[i]]))pb+=len[i];else ub+=len[i];}
    re4dc_log("vram frag: frame=%u need=%u base=%08x pool=%u allocs=%u other=%u pinned=%u evictable=%u free=%u\n",
        frame,need,base,pool,n,xb,pb,ub,(unsigned)pvr_mem_available());
    char line[200];unsigned at=0;
    for(unsigned i=0;i<n;++i){
        int w;
        if(owner[i]<0)w=snprintf(line+at,sizeof(line)-at," %x/%uX",off[i],len[i]/1024U);
        else{const Entry& e=entries[owner[i]];
            w=snprintf(line+at,sizeof(line)-at," %x/%u%c%08x",off[i],len[i]/1024U,RE4DC_ENTRY_PINNED(e)?'P':'U',e.key.crc);}
        if(w<0)break;
        at+=unsigned(w);
        if(at>150 || i+1==n){re4dc_log("vram frag:%s\n",line);at=0;}
    }
}
#endif
#endif
}
#if RE4DC_PVR_PIPELINE
// Called by room/texture_package.cpp (PVR_PIPELINE builds) before VRAM is
// freed or uploaded: it may be referenced by the scene not yet resolved.
#if defined(RE4DC_ENC_CENSUS) && RE4DC_ENC_CENSUS
extern "C" void re4dc_enc_frame(unsigned frame); // ENC_CENSUS (diagnostic): coarse.cpp, one line per frame mark
#endif
#if RE4DC_TA_BIN_DIAG
extern "C" void re4dc_pvr_vram_fence(){if(stream_scene)tabin::partial(frame);present_fence();}
#else
extern "C" void re4dc_pvr_vram_fence(){present_fence();}
#endif
#endif
#if RE4DC_PAD_PROMPTS
extern "C" int re4dc_ui_binocular_prompt(const Re4dcUiImage* original,unsigned kind,Re4dcUiImage* out){
    if(!frame_ready || !original || !out || kind<1 || kind>2 ||
       original->width!=36 || original->height!=36)return 0;
    Key source{};
    if(!image_key(*original,source) || source.crc!=0x11cdf896U || source.fnv!=0x15c51351U)return 0;
    const Re4dcUiImage image=prompt_image(kind-1);
    // Load through the normal bounded cache and pin until this scene completes.
    // Missing, invalid or unaffordable packages leave the original glyph intact.
    if(!load(image,true))return 0;
    *out=image;return 1;
}
#endif
#if RE4DC_PAD_PROMPT_MANUAL_ART
#include "manual_pages_native.inc"
#endif
extern "C" void re4dc_ui_invalidate_sources(){sources_reset();re4dc_model_reset_draw_plans();}
#if RE4DC_TA_DOUBLEBUF && RE4DC_PVR_PIPELINE
// Sub-screen backing open (subscreen_backing.cpp), before it writes bank 1: the open scene is
// finished unpresented (its TA input may be in bank 1), its render fenced, then the TA stays on
// bank 0. A refused switch halts: the backing must never share a bank with the TA.
extern "C" void re4dc_ui_ta_single_bank(){
    if(!ta_double){ta_double_wanted=false;return;}
    const bool open=stream_scene;
#if RE4DC_PVR_STREAM
    if(stream_scene)stream_close(false);
#endif
    const auto t=timer_us_gettime64();
    present_fence();
    if(pvr_set_vbuf_doublebuf(false)<0)re4dc_missing("TA single-bank switch refused");
    ta_double=false;
#if RE4DC_PVR_LATCH
    latch::put('s');
#endif
    re4dc_log("ta bank: single at frame %u (sub screen backing) scene_discarded=%d fence_us=%llu" "\n",frame,open?1:0,
              (unsigned long long)(timer_us_gettime64()-t));
}
// Backing closed (bank 1 read back): double buffering returns at the next stream_open.
extern "C" void re4dc_ui_ta_double_bank_later(){if(!ta_double)ta_double_wanted=true;}
#endif
#if RE4DC_SUBSCREEN
// Sub screen backing (subscreen_backing.cpp): releases the least recently used upload that
// this frame's scene does not reference, as load() evicts for a new upload (a previous-frame
// upload is fenced by close()). Returns its VRAM bytes, 0 when none is left.
extern "C" unsigned re4dc_ui_reclaim_one(){
    Entry* victim=nullptr;
    for(auto& e:entries) if(e.valid && !RE4DC_ENTRY_PINNED(e) && (!victim || e.frame<victim->frame)) victim=&e;
    if(!victim) return 0;
    const unsigned bytes=victim->package.vram_bytes();
    RE4DC_PROFILE_COUNT(TextureEvictions,1);close_entry(*victim);
#if RE4DC_SS_PACK && RE4DC_TEX_RESIDENT
    if(vram_claims)++claim_released; // the preload after the last unclaim brings it back
#endif
    return bytes?bytes:1;
}
#endif
#if RE4DC_TEX_RESIDENT
// A VRAM user outside the texture cache (route movie texture, sub screen backing)
// claims `bytes`: least recently used uploads that this frame's scene does not
// reference are released (close() fences a previous-frame upload) until one
// contiguous block of that size is available. The room preload keeps the pool
// nearly full for the hitch fix, so such a user found no room (r100: s40 movie,
// transceiver). Returns 1 when the block fits. Every claim is paired with
// re4dc_ui_vram_unclaim(); the preload waits while one is open and afterwards
// reloads what the claims released (it skips what is still resident).
// ROUTE_MOVIE_DIAG=2/3 (test only; 0/1 compile it out): the route movie's claim skips its
// normal pass, as if every upload were referenced by this frame's scene, so only the
// fallback below can free the block (2), or nothing does and the open fails as it did on
// a fragmented pool before the fallback existed (3). ROUTE_MOVIE_DIAG=4: the claim is
// normal and the movie opens inside a scene of the interrupted frame, so a movie whose open
// fails later (r100 s20 staging) retires its texture with that scene open.
#if defined(RE4DC_ROUTE_MOVIE_DIAG) && RE4DC_ROUTE_MOVIE_DIAG>=2
#define RE4DC_CLAIM_TEST RE4DC_ROUTE_MOVIE_DIAG
#else
#define RE4DC_CLAIM_TEST 0
#endif
namespace {
#if RE4DC_MOVIE_WINDOW
// MOVIE_WINDOW=1 (needs VRAM_PAGES): the route movie's claim releases one window instead of the least
// recently used uploads. LRU release in a fragmented pool freed 0.5-1.1 MB (58-129 entries) before a
// 256 KiB hole appeared, and all of it reloaded from disc after the movie (r100 s44 at the police car:
// 160-240 loads, seconds of slow frames, after each 5 s movie). Here every page-aligned window of
// `bytes` that starts at an allocation or a free extent is scored by the VRAM bytes of the cache
// entries it overlaps; a window touching a block no releasable entry owns (glyph atlas, overlay slab,
// sub screen, a pinned entry unless `pinned_ok`) is skipped. The cheapest window's entries are closed.
// Returns the entries released (0: no window qualifies).
extern "C" unsigned re4dc_vram_pages_snapshot(unsigned* off,unsigned* len,unsigned cap,unsigned* base,unsigned* pool);
unsigned movie_window_release(unsigned bytes,bool pinned_ok,unsigned& released_bytes){
    constexpr unsigned kCap=512,kPage=2048;
    static unsigned off[kCap],len[kCap];static short owner[kCap];static unsigned seen[kTextureCount];static unsigned stamp;
    unsigned base=0,pool=0;
    const unsigned n=re4dc_vram_pages_snapshot(off,len,kCap,&base,&pool);
    auto block_of=[&](unsigned a)->int{unsigned lo=0,hi=n;while(lo<hi){const unsigned m=(lo+hi)/2;if(off[m]+len[m]<=a)lo=m+1;else hi=m;}
        return lo<n && off[lo]<=a ? int(lo) : -1;};
    for(unsigned i=0;i<n;++i)owner[i]=-1;
    for(unsigned ei=0;ei<kTextureCount;++ei){
        const Entry& e=entries[ei];
        if(!e.valid || !e.package.vram_bytes() || (!pinned_ok && RE4DC_ENTRY_PINNED(e)))continue;
#if defined(RE4DC_CORE_PIN) && RE4DC_CORE_PIN==2
        if(!pinned_ok && RE4DC_CORE_PINNED(e))continue; // CORE_PIN=2: core keys only in a yield (or a pinned_ok pass)
#endif
#if RE4DC_UI_FRAG_WINDOW
        if(!pinned_ok && frag_min_age && frame-e.frame<frag_min_age)continue; // UI_FRAG_WINDOW: recently drawn
#endif
        const unsigned count=e.package.header().texture_count;
        for(unsigned t=0;t<count;++t){
            const pvr_ptr_t p=e.package.pvr_texture(t);if(!p)continue;
            const int b=block_of(unsigned(p)-base);if(b>=0)owner[b]=short(ei);
        }
    }
    unsigned best_cost=~0U,best_start=0;
    auto score=[&](unsigned s){
        s=(s+kPage-1)&~(kPage-1);
        if(s+bytes>pool)return;
        if(++stamp==0){std::memset(seen,0,sizeof(seen));stamp=1;}
        unsigned cost=0;
        for(int b=block_of(s)>=0?block_of(s):0;b<int(n) && off[b]<s+bytes;++b){
            if(off[b]+len[b]<=s)continue;
            if(owner[b]<0)return;
            if(seen[owner[b]]!=stamp){seen[owner[b]]=stamp;cost+=entries[owner[b]].package.vram_bytes();}
            if(cost>=best_cost)return;
        }
        best_cost=cost;best_start=s;
    };
    score(0);
    for(unsigned i=0;i<n;++i){score(off[i]);score(off[i]+len[i]);}
    if(best_cost==~0U)return 0;
    unsigned released=0;
    for(unsigned b=0;b<n;++b){
        if(off[b]>=best_start+bytes || off[b]+len[b]<=best_start || owner[b]<0)continue;
        Entry& e=entries[owner[b]];
        if(!e.valid)continue; // closed through an earlier block of the same entry
        released_bytes+=e.package.vram_bytes();++released;
        RE4DC_PROFILE_COUNT(TextureEvictions,1);close_entry(e);
    }
    re4dc_log("native texture claim: movie window at %08x cost=%u B entries=%u pinned_ok=%d\n",base+best_start,best_cost,released,pinned_ok?1:0);
    return released;
}
#endif
int vram_claim(unsigned bytes,bool movie){
    ++vram_claims;
    unsigned released=0,released_bytes=0;
    // Probe only when the total would do: a failed pvr_mem_malloc() logs an error.
    auto fits=[bytes]{if(pvr_mem_available()<bytes)return false;pvr_ptr_t p=pvr_mem_malloc(bytes);if(!p)return false;pvr_mem_free(p);return true;};
    // Fragmented pool: re-probe only after each 64 KiB released, not after every small texture
    // (the sub screen's 1 MiB claim probed 146 times at r101, each failure a KOS "out of PVR
    // memory" line, warp-r101-pbdoor8); at most 64 KiB more is released than strictly needed.
#if RE4DC_CLAIM_TEST==2 || RE4DC_CLAIM_TEST==3
    const bool forced=movie; // test: the normal pass finds nothing it may release
    bool ok=!forced && fits();
#else
    const bool forced=false;
    bool ok=fits();
#endif
    // Route movie fallback (second pass). The movie opens from a source task in the middle of a
    // frame (r100 s20: the s03 Ganado's death event), so this frame's uploads are still referenced
    // by the open scene and the normal pass may not touch them; ~680 KB of them scattered through
    // a fragmented pool left no 256 KiB hole (fits=0, the movie ended with no picture: terminal=3,
    // game-20260924-140901). The movie hides the world and owns the next presentations, so: finish
    // the open scene unpresented (as re4dc_ui_ta_single_bank does), fence its render, end this
    // frame's emission (the rest of it is not presented: nothing more is resolved or uploaded
    // before the next frame), then release this frame's uploads too, with the same 64 KiB probe
    // steps. re4dc_ui_vram_unclaim schedules the preload that reloads them before the next frame
    // draws. Render only: no source state is touched.
    bool fell_back=false;
    unsigned fallback_released=0,fallback_bytes=0;
    for(;;){
        unsigned since_probe=0;
#if RE4DC_MOVIE_WINDOW
        // The movie releases one window: unpinned entries first; when none qualifies, the scene is ended
        // (fallback below) and pinned entries may go too. Plain LRU release only if that also fails.
        if(!ok && movie && !forced){
            unsigned wb=0;const unsigned wr=movie_window_release(bytes,fell_back,wb);
            released+=wr;released_bytes+=wb;if(fell_back){fallback_released+=wr;fallback_bytes+=wb;}
            if(wr)ok=fits();
        }
        const bool skip_lru=movie && !forced && !fell_back;
#else
        const bool skip_lru=false;
#endif
        while(!ok && !skip_lru){
            Entry* victim=nullptr;
            for(auto& e:entries) if(e.valid && (fell_back || (!forced && !RE4DC_ENTRY_PINNED(e))) && (!victim || e.frame<victim->frame)) victim=&e;
            if(!victim){ok=since_probe && fits();break;}
            const unsigned vb=victim->package.vram_bytes();
            released_bytes+=vb;++released;since_probe+=vb?vb:1;
            if(fell_back){fallback_bytes+=vb;++fallback_released;}
            RE4DC_PROFILE_COUNT(TextureEvictions,1);close_entry(*victim);
            if(since_probe<65536U)continue;
            since_probe=0;
            ok=fits();
        }
        if(ok || !movie || fell_back || RE4DC_CLAIM_TEST==3)break;
#if RE4DC_PVR_STREAM
        if(stream_scene)stream_close(false);
#endif
#if RE4DC_PVR_PIPELINE
        present_fence();
#endif
        if(re4dc::gpu::quiesce()!=re4dc::gpu::FenceResult::ready){re4dc_log("native texture claim: fallback fence pending\n");break;}
#if RE4DC_D349_RENDERER_STACK
        if(deferred_first || draining_parts)reset_deferred();
#endif
#if RE4DC_PVR_STREAM
        stream_aborted=true;
#endif
        fell_back=true;
    }
    claim_released+=released;
    re4dc_log("native texture claim: bytes=%u fits=%d released=%u (%u B) free=%u used=%u claims=%u fallback=%d (%u, %u B)\n",bytes,ok?1:0,released,released_bytes,
        (unsigned)pvr_mem_available(),used,vram_claims,fell_back?1:0,fallback_released,fallback_bytes);
    return ok?1:0;
}
}
extern "C" int re4dc_ui_vram_claim(unsigned bytes){return vram_claim(bytes,false);}
#if RE4DC_SS_PACK
// SS_PACK=1: the packed sub screen backing holds the preload like a claim but releases nothing here;
// it takes free pool blocks as it fills and only then re4dc_ui_reclaim_one (counted in claim_released).
extern "C" void re4dc_ui_vram_hold(){
#if defined(RE4DC_SS_HOLD_RESTORE) && RE4DC_SS_HOLD_RESTORE
    if(!vram_claims){hold_frame=frame;hold_nkeys=0;hold_dropped=0;}   // SS_HOLD_RESTORE: a new hold
#endif
    ++vram_claims;
    re4dc_log("native texture hold: claims=%u free=%u\n",vram_claims,(unsigned)pvr_mem_available());
}
#endif
extern "C" void re4dc_ui_vram_unclaim(){
    if(!vram_claims)return;
#if defined(RE4DC_SS_HOLD_RESTORE) && RE4DC_SS_HOLD_RESTORE
    // SS_HOLD_RESTORE: a pass of only the remembered keys, unless a claim release already asks for the full pass.
    if(vram_claims==1 && !claim_released && hold_nkeys){preload_pending=true;hold_restore=true;
        re4dc_log("native texture hold restore: keys=%u dropped=%u\n",hold_nkeys,hold_dropped);}
#endif
    if(!--vram_claims && claim_released){preload_pending=true;claim_released=0;}
    re4dc_log("native texture unclaim: claims=%u preload=%d free=%u\n",vram_claims,preload_pending?1:0,(unsigned)pvr_mem_available());
}
#endif
#if defined(RE4DC_SS11_PRELOAD) && RE4DC_SS11_PRELOAD
// SS11_PRELOAD (subscreen.mk; VRAM graphics memory rule): MemDestroyHeap(11) (main_mem.cpp) calls this when the chapter
// title card or the chapter-end results / save screens close (they live in SS heap 11; the game is paused there). Their
// pictures (~1 MB with the results screen) evicted the room's set, which then came back from disc one first sight at a
// time in play (r105 after the chapter 1-2 save screen: 81 uploads). A room preload pass at the close loads the room's
// set back in one pass, before play resumes, as at room entry.
#if defined(RE4DC_LAKE_FIX_TOGGLE) && RE4DC_LAKE_FIX_TOGGLE
// LAKE_FIX_TOGGLE (effects30.mk; scenario / QA discs): the lake switches' run-time flag (esp_sub.cpp SHORE_FX_LEVEL,
// filter06.cpp rain streaks, the SS11_ROOM_EVICT evict below). bench.cpp's scenario menu sets it (A); on by default.
extern "C" { unsigned char re4dc_lake_fix = 1; }
#endif
extern "C" void re4dc_ui_room_preload_again(){
#if RE4DC_TEX_RESIDENT
    preload_pending=true;
#endif
#if defined(RE4DC_SS11_ROOM_EVICT) && RE4DC_SS11_ROOM_EVICT
    {
        // SS11_ROOM_EVICT (Makefile; render only; lane lake20, #43): a chapter end changes the room behind its results /
        // save screens without a room retirement (Del Lago r10b -> the night shore r11b), so r10b's 1.6 MB dynamic set
        // stayed beside r11b's preload and three 256x256 pictures found no contiguous block (~2 s latched waits). When
        // the room differs from the last room-change evict's, arm one here: every unpinned, unleased entry closes at the
        // preload pass, as on a re-entry; the new room's listed set is pinned and loads into the freed pool.
        re4dc::profile::Source src{};
#if defined(__sh__)
        re4dc_profile_source(&src);
#endif
#if defined(RE4DC_LAKE_FIX_TOGGLE) && RE4DC_LAKE_FIX_TOGGLE
        if(src.room!=rce_last_room && re4dc_lake_fix){   // LAKE_FIX_TOGGLE: only with the lake switches on
#else
        if(src.room!=rce_last_room){
#endif
            for(auto& e:entries)if(e.frame>=frame)e.frame=frame?frame-1:0U;
            rce_retire_frame=frame;rce_armed=true;rce_force_all=true;
            re4dc_log("native texture preload again: room %03x -> %03x behind SS heap 11, room change evict armed\n",
                      rce_last_room&0xfffU,unsigned(src.room));
        }
    }
#endif
    re4dc_log("native texture preload again: SS heap 11 closed free=%u\n",(unsigned)pvr_mem_available());
}
#endif
extern "C" int re4dc_ui_bind_core(void* archive,unsigned bytes){
    RE4DC_GCA_ADOPT(&core_identities,archive,bytes,false);
    sources_reset();
    const bool ok=core_identities.adopt(archive,bytes);
    if(ok)re4dc_model_bind_draw_owner(&core_identities,archive,bytes,0);
    else re4dc_model_unbind_draw_owner(&core_identities);
    re4dc_log("native core identities: %s count=%u archive=%u metadata_owner=core\n",ok?"ok":"REJECTED",core_identities.count(),bytes);
    return ok;
}
extern "C" int re4dc_ui_bind_room(void* archive,unsigned bytes){
    RE4DC_GCA_ADOPT(&room_identities,archive,bytes,true);
    sources_reset();identity_hits=0;
    const bool ok=room_identities.adopt(archive,bytes);
#if RE4DC_D349_RENDERER_STACK
    re4dc_model_preparation_owner(ok?archive:nullptr);
#endif
    if(ok)re4dc_model_bind_draw_owner(&room_identities,archive,bytes,1);
#if RE4DC_TEX_RESIDENT
    if(ok)preload_pending=true;
#endif
    else re4dc_model_unbind_draw_owner(&room_identities);
    re4dc_log("native room identities: %s count=%u archive=%u metadata_owner=room\n",ok?"ok":"REJECTED",room_identities.count(),bytes);
    return ok;
}
// Option/death UI remains resident across rooms. Borrow only its validated
// identity table; source overwrite invalidates descriptor lookups first.
extern "C" int re4dc_ui_bind_option(void* archive,unsigned bytes){
    RE4DC_GCA_ADOPT(&option_identities,archive,bytes,false);
    sources_reset();bool ok=option_identities.adopt(archive,bytes);
    if(ok)re4dc_model_bind_draw_owner(&option_identities,archive,bytes,0);
    else re4dc_model_unbind_draw_owner(&option_identities);
    re4dc_log("native option identities: %s count=%u archive=%u\n",ok?"ok":"REJECTED",option_identities.count(),bytes);return ok;
}
extern "C" void re4dc_ui_unbind_option(){RE4DC_GCA_RETIRE(&option_identities);re4dc_model_unbind_draw_owner(&option_identities);option_identities.clear();sources_reset();}
// Player and weapon regions persist across room retirement when the source
// retains them. Their explicit source release/overwrite boundaries clear views.
extern "C" int re4dc_ui_bind_player(void* archive,unsigned bytes){
    RE4DC_GCA_ADOPT(&player_identities,archive,bytes,false,re4dc_gcasset::PlayerOwner);
    sources_reset();bool ok=player_identities.adopt(archive,bytes);
    if(ok)re4dc_actor_archive_adopt(&player_identities,archive,bytes,1);
    else re4dc_actor_archive_retire(&player_identities);
    if(ok)re4dc_model_bind_draw_owner(&player_identities,archive,bytes,0);
#if RE4DC_TEX_RESIDENT
    if(ok)preload_pending=true;
#endif
    else re4dc_model_unbind_draw_owner(&player_identities);
    re4dc_log("native player identities: %s count=%u archive=%u\n",ok?"ok":"REJECTED",player_identities.count(),bytes);return ok;
}
extern "C" int re4dc_ui_bind_weapon(void* archive,unsigned bytes){
    RE4DC_GCA_ADOPT(&weapon_identities,archive,bytes,false,re4dc_gcasset::WeaponOwner);
    sources_reset();bool ok=weapon_identities.adopt(archive,bytes);
    if(ok)re4dc_actor_archive_adopt(&weapon_identities,archive,bytes,3);
    else re4dc_actor_archive_retire(&weapon_identities);
    if(ok)re4dc_model_bind_draw_owner(&weapon_identities,archive,bytes,0);
#if RE4DC_TEX_RESIDENT
    if(ok)preload_pending=true;
#endif
    else re4dc_model_unbind_draw_owner(&weapon_identities);
    re4dc_log("native weapon identities: %s count=%u archive=%u\n",ok?"ok":"REJECTED",weapon_identities.count(),bytes);return ok;
}
extern "C" void re4dc_ui_unbind_player(){RE4DC_GCA_RETIRE(&player_identities);re4dc_actor_archive_retire(&player_identities);re4dc_model_unbind_draw_owner(&player_identities);player_identities.clear();sources_reset();}
extern "C" void re4dc_ui_unbind_weapon(){RE4DC_GCA_RETIRE(&weapon_identities);re4dc_actor_archive_retire(&weapon_identities);re4dc_model_unbind_draw_owner(&weapon_identities);weapon_identities.clear();sources_reset();}
#if defined(RE4DC_OT_PROF) && RE4DC_OT_PROF
extern "C" unsigned re4dc_stream_model_bytes_now(){return stream_model_bytes;}
extern "C" unsigned long long re4dc_otp_now_us(){return timer_us_gettime64();}
#endif
extern "C" int re4dc_ui_bind_enemy(void* archive,unsigned bytes){
    RE4DC_GCA_ADOPT(archive,archive,bytes,true);
    re4dc::texture::SourceIdentityTable table;
    if(!table.adopt(archive,bytes))return 0;
    if(!table.count()) {
        re4dc_actor_archive_adopt(archive,archive,bytes,2);
        re4dc_model_bind_draw_owner(archive,archive,bytes,1);
        return 1; // ordinary archive; no texture view needed
    }
    EnemyIdentity* slot=nullptr;
    for(auto& e:enemy_identities){if(e.archive==archive)return 0;if(!e.archive && !slot)slot=&e;}
    if(!slot)return 0;
    slot->archive=archive;slot->table=table;sources_reset();
#if RE4DC_TEX_RESIDENT
    preload_pending=true;
#endif
    re4dc_actor_archive_adopt(archive,archive,bytes,2);
    re4dc_model_bind_draw_owner(archive,archive,bytes,1);
    re4dc_log("native enemy identities: count=%u archive=%u metadata_owner=enemy upload_staging=0\n",table.count(),bytes);
    return 1;
}
extern "C" void re4dc_ui_unbind_enemy(void* archive){
    RE4DC_GCA_RETIRE(archive);
    re4dc_actor_archive_retire(archive);
#if RE4DC_D349_RENDERER_STACK
    if(deferred_first){reset_deferred();stream_aborted=true;}
#endif
    re4dc_model_unbind_draw_owner(archive);
    for(auto& e:enemy_identities)if(archive && e.archive==archive){e.table.clear();e.archive=nullptr;}
    // Queued packets own copied native vertices/headers and cache handles; no
    // queued reader borrows archive texels. This does not free live VRAM uploads.
    sources_reset();
}
#if defined(RE4DC_RETIRE_KOS_FLOOR) && RE4DC_RETIRE_KOS_FLOOR
namespace {
// RETIRE_KOS_FLOOR (Makefile; render only): at room retirement close kept texture entries, least recently used first,
// until the KOS heap has RE4DC_RETIRE_KOS_FLOOR bytes of headroom for the next room's start. Runs after the retire
// fence (or at Render_swap for a deferred retirement), before the entries are marked oldest; actor-leased and
// room-pinned entries stay.
void retire_kos_floor(){
    const unsigned before=kos_headroom();
    unsigned closed=0;
    while(kos_headroom()<RE4DC_RETIRE_KOS_FLOOR){
        Entry* victim=nullptr;
        for(auto& e:entries){
            if(!e.valid || RE4DC_ROOM_PINNED(e))continue;
#if RE4DC_ACTOR_TRANSACTION
            if(actor_texture_leases.pinned(unsigned(&e-entries)))continue;
#endif
            if(!victim || e.frame<victim->frame)victim=&e;
        }
        if(!victim)break;
        close_entry(*victim);++closed;
    }
    re4dc_log("native UI: room retire KOS floor: closed=%u kos=%u->%u floor=%u\n",closed,before,kos_headroom(),
        unsigned(RE4DC_RETIRE_KOS_FLOOR));
}
}  // namespace
#endif
#if defined(RE4DC_ROOM_CHANGE_EVICT) && RE4DC_ROOM_CHANGE_EVICT
namespace {
// ROOM_CHANGE_EVICT (Makefile; render only): retirement keeps the entries' last-drawn frames (LRU order across the
// room change) and arms one eviction at the next room's first preload pass (room_change_evict below).
void room_change_retire(){
    for(auto& e:entries)if(e.frame>=frame)e.frame=frame?frame-1:0U;   // none stays "drawn this frame"
    rce_retire_frame=frame;rce_armed=true;
}
}  // namespace
#endif
extern "C" void re4dc_ui_retire_room(){
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    sob33_barrier(re4dc::sob33::SourceReset);
#endif
#if RE4DC_WORLD_SCRATCH
    // Close admission immediately; the final synchronous borrower restores mode.
    re4dc_world_scratch_cancel();
#endif
#if defined(RE4DC_FX_TEX_POOL) && RE4DC_FX_TEX_POOL
    for(unsigned i=0;i<kTextureCount;++i)fx_pool_pin[i]=false;   // FX_TEX_POOL: the next room fills its own pool
    fx_pool_bytes=0;fx_pool_full=0;
#endif
#if RE4DC_MOVIE_WORLD_ARENA
    // gameRoomMemInit can retire directly, without StageSet/re4dc_room_leave.
    if(!re4dc_movie_world_before_room_retire()){
        re4dc_missing("movie arena active during direct room retirement");return;
    }
#endif
#if RE4DC_TEX_CHECK
    texchk::room_end();
#endif
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset_retire();
#endif
    re4dc_actor_archive_retire_transient();
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::member_retire_transient();
#endif
#if RE4DC_TEX_PACK
    texpack::room_loaded();   // after read errors: the next pack init attempt runs at once (texpack_index.inc)
#endif
#if RE4DC_MODEL_SLAB_LATCH
    model_slab_failed=false;
#endif
#if RE4DC_D349_RENDERER_STACK
    reset_deferred();
    re4dc_model_preparation_owner(nullptr);
#endif
    re4dc_model_retire_draw_plans();
    // Packets hold copied native vertices, so no queued draw borrows a package.
#if RE4DC_NATIVE_STATIC
    re4dc_static_retire_all();
#endif
#if RE4DC_PVR_STREAM
    // Source room retirement can occur on a task while the main thread owns an
    // unfinished TA list. Keep submitted texture owners until that thread closes
    // and fences the discarded scene at Render_swap; no source CPU pointer is
    // retained by PVR. Waiting here would deadlock the caller against main.
    if(stream_scene){stream_aborted=true;stream_retire=true;}
    else
#endif
#if RE4DC_PVR_PIPELINE
    // The presenter owns the last scene until it resolves; then fence as before.
    if(ready && (present_fence(),re4dc::gpu::quiesce())!=re4dc::gpu::FenceResult::ready)
#else
    if(ready && re4dc::gpu::quiesce()!=re4dc::gpu::FenceResult::ready)
#endif
        re4dc_missing("native room retire fence failed");
    // No queued draw may outlive its source room. Shared cached uploads may be
    // reloaded from their stable identities; no archive texels are needed.
    // Core descriptors belong to the persistent core region and survive this reset.
    nquad=0;model_used=0;model_handle=nullptr;sources_reset();room_identities.clear();identity_hits=0;
    for(auto& e:enemy_identities){e.table.clear();e.archive=nullptr;}
#if RE4DC_PVR_STREAM
    if(!stream_retire)
#endif
#if RE4DC_TEX_KEEP
#if defined(RE4DC_RETIRE_KOS_FLOOR) && RE4DC_RETIRE_KOS_FLOOR
    retire_kos_floor();                      // RETIRE_KOS_FLOOR: KOS headroom for the next room first (LRU order)
#endif
#if defined(RE4DC_ROOM_CHANGE_EVICT) && RE4DC_ROOM_CHANGE_EVICT
    room_change_retire();                    // ROOM_CHANGE_EVICT: kept resident in LRU order, evictable
#else
    for(auto& entry:entries)entry.frame=0;   // kept resident, oldest: evictable
#endif
#else
    for(auto& entry:entries)close_entry(entry);
#endif
}

#if RE4DC_NATIVE_STATIC
extern "C" unsigned re4dc_ui_frame(){return frame;}
#endif
#if RE4DC_NATIVE_MES
// NATIVE_MES=1 (Makefile; default off = previous image): message glyphs. mes.cpp draw() sends
// each glyph here instead of to the GX stub (which sinks it). Glyph texels live in one 256x256
// PAL4 twiddled atlas (32 KiB of VRAM, allocated in re4dc_ui_init() before the UI_VRAM budget is
// taken from the pool, so the texture cache and the room preload account for it): 64 cells of
// 32x32, each holding one glyph decoded on first use from the font's GC CI4 sheet and kept least
// recently used. A cell used by the previous frame is only rewritten after its render fence; a
// cell used by this frame never (the glyph is then counted as "full" and not drawn). Font TLUTs
// go to 16-entry palette banks in ARGB8888 (no other native path uses the palette). Glyph order
// is the source order: a run of consecutive glyphs is one sentinel entry in the UI quad queue.
namespace {
#ifndef RE4DC_NATIVE_MES_CELLS
#define RE4DC_NATIVE_MES_CELLS 64
#endif
static_assert(RE4DC_NATIVE_MES_CELLS==64 || RE4DC_NATIVE_MES_CELLS==128,"NATIVE_MES_CELLS: 64 (256x256) or 128 (256x512)");
// A 256x512 twiddled texture is two 256x256 squares one after the other; cell c: square c/64, cell c%64 in it.
constexpr unsigned kGlyphCells=RE4DC_NATIVE_MES_CELLS,kGlyphCapacity=384,kGlyphBanks=8,kGlyphAtlasH=kGlyphCells/8*32,kGlyphAtlasBytes=256*kGlyphAtlasH/2;
struct GlyphCell { const void* sheet; const void* clut; short u,v; unsigned char cw,ch,bank; bool valid; unsigned frame;
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::CheckedAsset asset{};unsigned serial=0,palette_serial=0;
#endif
};
struct GlyphQuad { short x0,y0,x1,y1; unsigned char cell,cw,ch,bank; unsigned argb;
#if RE4DC_GC_ASSET_GATE
    unsigned serial=0,palette_serial=0;
#endif
}; // x/y in 1/4 px
#if !RE4DC_GC_ASSET_GATE
static_assert(sizeof(GlyphQuad)==16);
#endif
struct GlyphBank { const void* clut; unsigned sum; bool valid;
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::CheckedAsset asset{};unsigned serial=0;
#endif
};
#if RE4DC_GC_ASSET_GATE
unsigned glyph_asset_serial;
re4dc_gcasset::CheckedAsset gcasset_glyph_payload(const char* kind,const void* payload,unsigned bytes){
    if(!re4dc_gcasset::ensure_disc_catalog())return {};
    const auto digest=re4dc_gcasset::fingerprint(payload,bytes);char id[41];
    for(unsigned i=0;i<20;++i)snprintf(id+2*i,3,"%02x",digest.bytes[i]);
    return re4dc_gcasset::bind_checked(kind,id,digest);
}
unsigned gcasset_glyph_version(){
    if(glyph_asset_serial==0xffffffffU){re4dc_gcasset::unresolved(re4dc_gcasset::Font,"glyph-version-overflow");return 0;}
    return ++glyph_asset_serial;
}
#endif
pvr_ptr_t glyph_atlas;
GlyphCell glyph_cells[kGlyphCells];
GlyphQuad glyph_quads[kGlyphCapacity];
GlyphBank glyph_banks[kGlyphBanks];
pvr_poly_hdr_t glyph_headers[kGlyphBanks];
bool glyph_header_ready[kGlyphBanks];
unsigned char glyph_hint[128];
bool glyph_total_first;
unsigned short glyph_twx[32],glyph_twy[32]; // PVR twiddle: y bits to even, x bits to odd positions
unsigned nglyph,glyph_peak,glyph_total,glyph_drawn,glyph_hits,glyph_misses,glyph_evictions,glyph_fenced,glyph_full,
    glyph_dropped,glyph_unsupported,glyph_culled,glyph_font_changes,glyph_logged_total,glyph_logged_problems;
Entry* const kGlyphRun=reinterpret_cast<Entry*>(glyph_cells); // sentinel handle, never dereferenced
void glyph_init(){
    for(unsigned i=0;i<32;++i){
        unsigned x=0,y=0;
        for(unsigned k=0;k<5;++k)if(i>>k&1){x|=2U<<(2*k);y|=1U<<(2*k);}
        glyph_twx[i]=(unsigned short)x;glyph_twy[i]=(unsigned short)y;
    }
    const unsigned before=pvr_mem_available();
    #if defined(RE4DC_VRAM_ROOM_ARENA) && RE4DC_VRAM_ROOM_ARENA
    re4dc_vram_arena_class=2;   // VRAM_ROOM_ARENA: long-lived, from the top
#endif
    glyph_atlas=pvr_mem_malloc(kGlyphAtlasBytes);
#if defined(RE4DC_VRAM_ROOM_ARENA) && RE4DC_VRAM_ROOM_ARENA
    re4dc_vram_arena_class=0;
#endif
    if(!glyph_atlas){re4dc_log("native mes: glyph atlas allocation FAILED (free=%u); message text off\n",before);return;}
    alignas(32) static const unsigned char zero[512]={};
    for(unsigned n=0;n<kGlyphAtlasBytes;n+=sizeof(zero))pvr_txr_load(zero,(char*)glyph_atlas+n,sizeof(zero));
#if !RE4DC_TEX_PAL4_ALPHA
    pvr_set_pal_format(PVR_PAL_ARGB8888);
#endif
    re4dc_log("native mes: glyph atlas 256x%u PAL4 at %p, %u B (pool %u -> %u before the UI budget), %u cells, %u glyphs/frame\n",
        kGlyphAtlasH,glyph_atlas,kGlyphAtlasBytes,before,(unsigned)pvr_mem_available(),kGlyphCells,kGlyphCapacity);
}
unsigned glyph_color(unsigned c,unsigned format){
    auto x5=[](unsigned v){return (v<<3)|(v>>2);};
    switch(format){
    case 0: return ((c>>8)<<24)|((c&255)*0x010101U);                                        // IA8
    case 1: return 0xff000000U|(x5(c>>11)<<16)|((((c>>5)&63)<<2|((c>>5)&63)>>4)<<8)|x5(c&31); // RGB565
    default:
        if(c&0x8000)return 0xff000000U|(x5((c>>10)&31)<<16)|(x5((c>>5)&31)<<8)|x5(c&31);      // RGB5A3 opaque
        {const unsigned a=(c>>12)&7;
         return (((a<<5)|(a<<2)|(a>>1))<<24)|(((c>>8)&15)*17<<16)|(((c>>4)&15)*17<<8)|((c&15)*17);}
    }
}
int glyph_bank(const void* clut,unsigned format,unsigned entries){
    if(!clut || format>2 || entries<16)return -1;
    const unsigned char* p=static_cast<const unsigned char*>(clut);
    unsigned sum=format;
    for(unsigned i=0;i<32;++i)sum=sum*31+p[i];
    int free_bank=-1;
    for(unsigned b=0;b<kGlyphBanks;++b){
        if(glyph_banks[b].valid && glyph_banks[b].clut==clut && glyph_banks[b].sum==sum)return int(b);
        if(!glyph_banks[b].valid && free_bank<0)free_bank=int(b);
    }
    if(free_bank<0)return -1;
#if RE4DC_PVR_MID_FENCE
    present_fence();   // PVR_MID_FENCE: no palette RAM write while a queued render runs
#endif
#if RE4DC_GC_ASSET_GATE
    unsigned palette[16];for(unsigned i=0;i<16;++i)palette[i]=glyph_color((p[2*i]<<8)|p[2*i+1],format);
    for(unsigned i=0;i<16;++i)pvr_set_pal_entry(unsigned(free_bank)*16+i,palette[i]);
#else
    for(unsigned i=0;i<16;++i)pvr_set_pal_entry(unsigned(free_bank)*16+i,glyph_color((p[2*i]<<8)|p[2*i+1],format));
#endif
    glyph_banks[free_bank]={clut,sum,true};
#if RE4DC_GC_ASSET_GATE
    glyph_banks[free_bank].asset=gcasset_glyph_payload("font-palette",palette,sizeof palette);
    glyph_banks[free_bank].serial=gcasset_glyph_version();
#endif
    re4dc_log("native mes: palette bank %d <- tlut %p format %u\n",free_bank,clut,format);
    return free_bank;
}
int glyph_cell(const Re4dcUiGlyph& g){
    const unsigned h=((unsigned)(std::size_t)g.sheet>>5^unsigned(g.u)*7U^unsigned(g.v)*131U)&127U;
    auto match=[&g](const GlyphCell& c){return c.valid && c.sheet==g.sheet && c.clut==g.clut && c.u==g.u && c.v==g.v && c.cw==g.cw && c.ch==g.ch;};
    if(const unsigned k=glyph_hint[h])if(match(glyph_cells[k-1])){glyph_cells[k-1].frame=frame;++glyph_hits;return int(k-1);}
    for(unsigned i=0;i<kGlyphCells;++i)if(match(glyph_cells[i])){glyph_hint[h]=(unsigned char)(i+1);glyph_cells[i].frame=frame;++glyph_hits;return int(i);}
    const int bank=glyph_bank(g.clut,g.clut_format,g.clut_entries);
    if(bank<0){++glyph_unsupported;return -1;}
    // Victim: an idle cell (neither this frame nor the previous one), invalid first, then the
    // least recently used; else a previous-frame cell after the render fence; else none.
    int victim=-1;
    for(unsigned i=0;i<kGlyphCells;++i){
        const GlyphCell& c=glyph_cells[i];
        if(c.frame+1>=frame && frame)continue;
        if(victim<0 || (!c.valid && glyph_cells[victim].valid) || (c.valid==glyph_cells[victim].valid && c.frame<glyph_cells[victim].frame))victim=int(i);
    }
    if(victim<0){
        for(unsigned i=0;i<kGlyphCells;++i)if(glyph_cells[i].frame!=frame){victim=int(i);break;}
        if(victim<0){++glyph_full;return -1;}
#if RE4DC_PVR_PIPELINE
        present_fence(); // the previous scene may still sample this cell
#endif
        ++glyph_fenced;
    }
    GlyphCell& c=glyph_cells[victim];
    if(c.valid)++glyph_evictions;
    ++glyph_misses;
    // Decode the 32x32 window at (u, v) (the glyph plus the sheet texels right of / below it,
    // which bilinear filtering reads there as on the GameCube); clamp at the sheet edges.
    alignas(32) unsigned char cell[512];
    std::memset(cell,0,sizeof(cell));
    const unsigned char* s=static_cast<const unsigned char*>(g.sheet);
    const unsigned bw=g.sheet_w>>3;
    for(unsigned y=0;y<32;++y){
        const int yy=g.v+int(y);
        const unsigned sy=unsigned(yy<0?0:yy>=int(g.sheet_h)?int(g.sheet_h)-1:yy);
        const unsigned char* row=s+(sy>>3)*bw*32+(sy&7)*4;
        for(unsigned x=0;x<32;++x){
            const int xx=g.u+int(x);
            const unsigned sx=unsigned(xx<0?0:xx>=int(g.sheet_w)?int(g.sheet_w)-1:xx);
            const unsigned byte=row[(sx>>3)*32+((sx&7)>>1)];
            const unsigned index=(sx&1)?byte&15:byte>>4;
            const unsigned t=glyph_twx[x]|glyph_twy[y];
            cell[t>>1]|=(unsigned char)((t&1)?index<<4:index);
        }
    }
    const unsigned cx=unsigned(victim)&7,cy=(unsigned(victim)>>3)&7,square=unsigned(victim)>>6;
#if RE4DC_PVR_MID_FENCE
    present_fence();   // PVR_MID_FENCE: no texel write while a queued render runs (even into an idle cell)
#endif
    pvr_txr_load(cell,(char*)glyph_atlas+square*32768U+((glyph_twx[cx]|glyph_twy[cy])<<9),sizeof(cell));
    c={g.sheet,g.clut,(short)g.u,(short)g.v,(unsigned char)g.cw,(unsigned char)g.ch,(unsigned char)bank,true,frame};
#if RE4DC_GC_ASSET_GATE
    c.asset=gcasset_glyph_payload("font-glyph",cell,sizeof cell);c.serial=gcasset_glyph_version();c.palette_serial=glyph_banks[bank].serial;
#endif
    glyph_hint[h]=(unsigned char)(victim+1);
    return victim;
}
const pvr_poly_hdr_t& glyph_header(unsigned bank){
    if(!glyph_header_ready[bank]){
        pvr_poly_cxt_t c;
        pvr_poly_cxt_txr(&c,PVR_LIST_TR_POLY,PVR_TXRFMT_PAL4BPP|PVR_TXRFMT_4BPP_PAL(bank)|PVR_TXRFMT_TWIDDLED,256,kGlyphAtlasH,glyph_atlas,PVR_FILTER_BILINEAR);
        c.gen.culling=PVR_CULLING_NONE;c.depth.comparison=PVR_DEPTHCMP_ALWAYS;c.depth.write=PVR_DEPTHWRITE_DISABLE;
        c.blend.src=PVR_BLEND_SRCALPHA;c.blend.dst=PVR_BLEND_INVSRCALPHA;c.txr.env=PVR_TXRENV_MODULATEALPHA;c.txr.uv_clamp=PVR_UVCLAMP_UV;
        pvr_poly_compile(&glyph_headers[bank],&c);glyph_header_ready[bank]=true;
    }
    return glyph_headers[bank];
}
#if RE4DC_GC_ASSET_GATE
bool gcasset_glyph_matches(const GlyphQuad& glyph){
#if RE4DC_TREE_IMPOSTOR && !RE4DC_TEX_PAL4_ALPHA
    // Legacy package palettes do not reserve the glyph banks. That profile
    // needs an actual shared-palette ownership bridge before it can qualify.
    (void)glyph;return false;
#else
    if(glyph.cell>=kGlyphCells || glyph.bank>=kGlyphBanks)return false;
    const auto& cell=glyph_cells[glyph.cell];const auto& bank=glyph_banks[glyph.bank];
    return glyph.serial && glyph.palette_serial && cell.serial==glyph.serial && cell.bank==glyph.bank &&
        cell.palette_serial==glyph.palette_serial && bank.serial==glyph.palette_serial;
#endif
}
void gcasset_glyph_emitted(const GlyphQuad& glyph){
    if(!gcasset_glyph_matches(glyph)){re4dc_gcasset::unresolved(re4dc_gcasset::Font,"glyph-cell-version");return;}
    const auto tile=glyph_cells[glyph.cell].asset,palette=glyph_banks[glyph.bank].asset;
    const re4dc_gcasset::Consumer consumers[]={re4dc_gcasset::Font,re4dc_gcasset::Texture,re4dc_gcasset::Ui};
    for(const auto consumer:consumers){
        re4dc_gcasset::emitted_checked(consumer,tile);re4dc_gcasset::emitted_checked(consumer,palette);
    }
}
#endif
// One run: a header when the palette bank changes, then a 4-vertex strip per glyph (a strip
// after an end-of-strip vertex reuses the last header).
#if RE4DC_UI_DRAW_LEAN
// Ordinary quads do not need this run's 2080-byte packet buffer in their stack frame.
__attribute__((noinline))
#endif
void glyph_draw_run(unsigned first,unsigned count){
#if RE4DC_TA_MATERIAL_DIAG
    tamat::Scope source_scope(3);
#endif
    alignas(32) pvr_vertex_t buf[1+4*16];
    unsigned n=0;int bank=-1;
#if RE4DC_GC_ASSET_GATE
    const GlyphQuad* asset_quads[16];unsigned asset_count=0;
#endif
    auto flush=[&]{
        if(!n)return;
#if RE4DC_GC_ASSET_GATE
        bool verified=asset_count!=0;
        for(unsigned i=0;i<asset_count;++i)verified=verified && gcasset_glyph_matches(*asset_quads[i]);
        GcAssetGeneratedPacket packet{buf,unsigned(n*sizeof(pvr_vertex_t)),unsigned(reinterpret_cast<std::uintptr_t>(glyph_atlas))&0x007fffffU,re4dc_gcasset::Font,verified};
        {GcAssetGeneratedScope asset_scope(packet);
#endif
#if RE4DC_PVR_STREAM
        stream_send(buf,n*sizeof(pvr_vertex_t));
#else
        re4dc::render::submit_pvr(buf,n*sizeof(pvr_vertex_t));
#endif
#if RE4DC_GC_ASSET_GATE
        }
        if(packet.accepted && verified){for(unsigned i=0;i<asset_count;++i)gcasset_glyph_emitted(*asset_quads[i]);}
        else re4dc_gcasset::unresolved(re4dc_gcasset::Font,"unqualified-glyph-packet");
        asset_count=0;
#endif
        n=0;
    };
    for(unsigned i=first;i<first+count && i<nglyph;++i){
        const GlyphQuad& g=glyph_quads[i];
        if(n+5>sizeof(buf)/sizeof(buf[0]))flush();
        if(g.bank!=bank){std::memcpy(&buf[n++],&glyph_header(g.bank),sizeof(pvr_vertex_t));bank=g.bank;}
        const float layer=overlay_depth();
        constexpr float kH=float(kGlyphAtlasH);
        const float u0=float((g.cell&7)*32)/256.0f,v0=float((g.cell>>3)*32)/kH;
#if RE4DC_UI_DRAW_LEAN
        // The queue already holds exact quarter-pixel endpoints. Emit from scalars instead
        // of writing and rereading four temporary arrays for this four-vertex strip.
        const float x0=g.x0*0.25f,x1=g.x1*0.25f,y0=g.y0*0.25f,y1=g.y1*0.25f;
        const float u1=u0+g.cw/256.0f,v1=v0+g.ch/kH;
        auto vertex=[&](float x,float y,float u,float v,unsigned flags) __attribute__((always_inline)) {
            pvr_vertex_t& p=buf[n++];
            p.flags=flags;p.x=RE4DC_UI_X(x);p.y=RE4DC_UI_Y(y);p.z=layer;p.u=u;p.v=v;p.argb=g.argb;p.oargb=0;
        };
        vertex(x0,y0,u0,v0,PVR_CMD_VERTEX);
        vertex(x1,y0,u1,v0,PVR_CMD_VERTEX);
        vertex(x0,y1,u0,v1,PVR_CMD_VERTEX);
        vertex(x1,y1,u1,v1,PVR_CMD_VERTEX_EOL);
#else
        const float x[4]={g.x0*0.25f,g.x1*0.25f,g.x0*0.25f,g.x1*0.25f},y[4]={g.y0*0.25f,g.y0*0.25f,g.y1*0.25f,g.y1*0.25f};
        const float u[4]={u0,u0+g.cw/256.0f,u0,u0+g.cw/256.0f},v[4]={v0,v0,v0+g.ch/kH,v0+g.ch/kH};
        for(unsigned k=0;k<4;++k){
            pvr_vertex_t& p=buf[n++];
            p.flags=k==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;p.x=RE4DC_UI_X(x[k]);p.y=RE4DC_UI_Y(y[k]);p.z=layer;p.u=u[k];p.v=v[k];p.argb=g.argb;p.oargb=0;
        }
#endif
        ++glyph_drawn;
#if RE4DC_GC_ASSET_GATE
        asset_quads[asset_count++]=&g;
#endif
    }
    flush();
}
short glyph_quarter(float f){f*=4.0f;return (short)(f<-32000.0f?-32000:f>32000.0f?32000:int(f<0?f-0.5f:f+0.5f));}
}
extern "C" void re4dc_ui_glyph(const Re4dcUiGlyph* g){
    if(!frame_ready || !glyph_atlas)return;
#if RE4DC_PVR_STREAM
    if(stream_aborted)return;
#endif
    ++glyph_total;
    if((g->argb>>24)==0){++glyph_culled;return;}
    if(g->format!=8 || !g->sheet || g->cw<=0 || g->cw>32 || g->ch<=0 || g->ch>32 || !g->sheet_w || !g->sheet_h ||
       (g->sheet_w&7) || (g->sheet_h&7)){++glyph_unsupported;return;}
    if(nglyph==kGlyphCapacity){++glyph_dropped;return;}
    #if RE4DC_SS_UI_ORDER
    // A submitted glyph run is immutable, even if the next source command is text.
    const bool extend=nquad>quads_flushed && handles[nquad-1]==kGlyphRun && quads[nquad-1].image.width+quads[nquad-1].image.height==nglyph;
#else
    const bool extend=nquad && handles[nquad-1]==kGlyphRun && quads[nquad-1].image.width+quads[nquad-1].image.height==nglyph;
#endif
#if RE4DC_D349_RENDERER_STACK
    if(!extend && (nquad+1)*sizeof(Re4dcUiQuad)>deferred_top){++glyph_dropped;return;}
#else
    if(!extend && nquad==kQuadCount){++glyph_dropped;return;}
#endif
    const int cell=glyph_cell(*g);
    if(cell<0)return;
    if(!glyph_total_first){glyph_total_first=true;
        re4dc_log("native mes: first glyph frame=%u sheet=%p %ux%u window=%d,%d %dx%d at %d,%d-%d,%d argb=%08x\n",frame,g->sheet,g->sheet_w,g->sheet_h,
            g->u,g->v,g->cw,g->ch,int(g->x0),int(g->y0),int(g->x1),int(g->y1),g->argb);}
    glyph_quads[nglyph]={glyph_quarter(g->x0),glyph_quarter(g->y0),glyph_quarter(g->x1),glyph_quarter(g->y1),(unsigned char)cell,
        (unsigned char)g->cw,(unsigned char)g->ch,glyph_cells[cell].bank,g->argb};
#if RE4DC_GC_ASSET_GATE
    glyph_quads[nglyph].serial=glyph_cells[cell].serial;glyph_quads[nglyph].palette_serial=glyph_cells[cell].palette_serial;
#endif
    if(extend)++quads[nquad-1].image.height;
    else {
        Re4dcUiQuad* q=new(quads+nquad) Re4dcUiQuad{};
        q->image.width=nglyph;q->image.height=1; // run: first glyph, count
        handles[nquad++]=kGlyphRun;
    }
    if(++nglyph>glyph_peak)glyph_peak=nglyph;
}
// MessageFont::create(): a font buffer may be reloaded with other content at the same address.
extern "C" void re4dc_ui_glyph_fonts_changed(){
    for(auto& c:glyph_cells)c.valid=false;
    for(auto& b:glyph_banks)b.valid=false;
    std::memset(glyph_hint,0,sizeof(glyph_hint));
    ++glyph_font_changes;
}
#endif
#if RE4DC_TA_HEADROOM && (RE4DC_TA_GUARD || !RE4DC_PVR_STREAM)
#error TA_HEADROOM needs PVR_STREAM=1 and TA_GUARD=0 (the guard budgets the full TA_VERTBUF_KB)
#endif
#if RE4DC_PVR_MID_FENCE && !RE4DC_PVR_PIPELINE
#error PVR_MID_FENCE waits in present_fence: needs PVR_PIPELINE
#endif
#if RE4DC_RES_MODES
#if RE4DC_TA_BIN_DIAG || !RE4DC_PVR_STREAM || RE4DC_PVR_PIPELINE!=2 || !RE4DC_TA_HEADROOM
#error RES_MODES needs PVR_STREAM=1, PVR_PIPELINE=2, TA_HEADROOM>=1 (ta_vertex_bytes) and TA_BIN_DIAG=0 (its 20x15 tile replay)
#endif
extern "C" unsigned re4dc_res_params(pvr_init_params_t* p);
extern "C" void re4dc_res_init();
extern "C" int re4dc_res_pending();
extern "C" void re4dc_res_apply_pending();
#endif
#if RE4DC_VGA_SOFT
extern "C" void re4dc_vga_soft_init(void); // vga_soft.cpp (VGA_SOFT): the vertical filter on a VGA box, once
#endif
#if RE4DC_GC_ASSET_GATE
// GC_ASSET_LIFECYCLE_BEGIN
namespace {
unsigned gcasset_visit_serial;bool gcasset_started,gcasset_visit_live;
enum GcAssetPhase { GcStartup,GcRoom,GcTransition };GcAssetPhase gcasset_phase;unsigned gcasset_current_room;
constexpr unsigned gcasset_wired_mask(){
    // Specialized static/coarse payload bridges are not integrated yet. Keep
    // both affected consumer classes visibly incomplete, even in empty rooms.
    // gc-catalog24b: Weapon (actor/static/model weapon producers) and Motion
    // (every FCV lease + SEQ set) are wired; source geometry stays incomplete.
    unsigned mask=re4dc_gcasset::Required&~(1U<<re4dc_gcasset::SourceGeometry);
#if !RE4DC_NATIVE_MES
    mask&=~(1U<<re4dc_gcasset::Font); // legacy font consumer is not qualified
#endif
    return mask;
}
void gcasset_flush(){
#if RE4DC_GC_ASSET_MOTION_UNKNOWN
    re4dc_gcasset::motion_unknown_flush();
#endif
    for(auto& entry:entries)gcasset_texture_flush(entry);
    re4dc_gcasset::member_flush();re4dc_gcasset::motion_flush();re4dc_gcasset::payload_flush_all();
    re4dc_gcasset::bank_pump();re4dc_gcasset::pump();
}
void gcasset_startup(){
    if(gcasset_started)return;
    gcasset_started=true;gcasset_phase=GcStartup;re4dc_gcasset_audio_admission(0);
    re4dc_gcasset::ensure_disc_catalog();
    re4dc_gcasset::begin_startup_closed(++gcasset_visit_serial,gcasset_wired_mask());
#if defined(RE4DC_GC_ASSET_COARSE_LEON) && RE4DC_GC_ASSET_COARSE_LEON
    re4dc_gcasset_actor_startup();
#endif
    gcasset_visit_live=true;re4dc_gcasset_audio_admission(1);
}
// Judge contract v2: the in-room checkpoint marks the render-side consumers
// as close_visit does (audio consumers keep what their own flush reported).
void gcasset_checkpoint(){
    for(auto consumer:{re4dc_gcasset::Texture,re4dc_gcasset::EffectPicture,re4dc_gcasset::Weapon,re4dc_gcasset::Ui,re4dc_gcasset::Movie,re4dc_gcasset::Motion})
        re4dc_gcasset::checked(consumer);
#if RE4DC_NATIVE_MES
    re4dc_gcasset::checked(re4dc_gcasset::Font);
#endif
    re4dc_gcasset::checkpoint(frame);
}
void gcasset_close_visit(unsigned audio){
    gcasset_flush();gcasset_packet_reset();re4dc_gcasset::motion_visit_reset();
    // The actual renderer observer/flush paths are source-extracted in tests.
    // Active sound coverage additionally requires the real audio_step flush.
    for(auto consumer:{re4dc_gcasset::Texture,re4dc_gcasset::EffectPicture,re4dc_gcasset::Weapon,re4dc_gcasset::Ui,re4dc_gcasset::Movie,re4dc_gcasset::Motion})
        re4dc_gcasset::checked(consumer);
#if RE4DC_NATIVE_MES
    re4dc_gcasset::checked(re4dc_gcasset::Font);
#endif
    for(auto consumer:{re4dc_gcasset::SoundBank,re4dc_gcasset::SoundStream})
        if(audio&(1U<<consumer))re4dc_gcasset::checked(consumer);
    re4dc_gcasset::end(frame);gcasset_visit_live=false;
}
}
// fixture end (W11 fixture / warp script done): one more checkpoint.
extern "C" void re4dc_gcasset_fixture_end(){if(gcasset_visit_live){gcasset_flush();gcasset_checkpoint();}}
extern "C" void re4dc_gcasset_finish(){
    const unsigned audio=re4dc_gcasset_audio_admission(0);
    if(gcasset_visit_live)gcasset_close_visit(audio);else re4dc_gcasset::pump();
}
extern "C" void re4dc_gcasset_retire(){
    if(!gcasset_visit_live){re4dc_gcasset::pump();return;}
    if(gcasset_phase==GcTransition){gcasset_flush();return;} // repeated accepted retirement is idempotent
    if(gcasset_visit_serial==~0U){re4dc_gcasset::unresolved(re4dc_gcasset::Ui,"visit-serial-exhausted");re4dc_gcasset_finish();return;}
    const unsigned next=gcasset_visit_serial+1;
    const unsigned from=gcasset_phase==GcStartup?re4dc_gcasset::FromStartup:gcasset_current_room;
    const auto why=gcasset_phase==GcStartup?re4dc_gcasset::InitialRoom:re4dc_gcasset::RoomRetire;
    const unsigned audio=re4dc_gcasset_audio_handoff(0,next);
    gcasset_close_visit(audio);gcasset_phase=GcTransition;gcasset_visit_serial=next;
    re4dc_gcasset::begin_transition_handoff(next,gcasset_wired_mask(),from,why);gcasset_visit_live=true;
}
extern "C" void re4dc_gcasset_room_enter(unsigned room){
    if(!gcasset_started){re4dc_gcasset::unresolved(re4dc_gcasset::Ui,"room-without-startup");gcasset_startup();}
    if(gcasset_visit_serial==~0U){re4dc_gcasset::unresolved(re4dc_gcasset::Ui,"visit-serial-exhausted");re4dc_gcasset_finish();return;}
    const unsigned next=gcasset_visit_serial+1;
    if(!gcasset_visit_live || gcasset_phase!=GcTransition)re4dc_gcasset::unresolved(re4dc_gcasset::Ui,"room-enter-without-transition");
    const unsigned audio=re4dc_gcasset_audio_handoff(room,next);
    if(gcasset_visit_live)gcasset_close_visit(audio);
    gcasset_phase=GcRoom;gcasset_current_room=room;gcasset_visit_serial=next;
    re4dc_gcasset::begin_room_handoff(room,next,gcasset_wired_mask());gcasset_visit_live=true;
}
// GC_ASSET_LIFECYCLE_END
#endif
extern "C" void re4dc_ui_init(){
    if(ready)return;
    pvr_init_params_t params=pvr_default_params;
#if RE4DC_PVR_STREAM
    // Serialized ownership uses one TA bank. This pinned KOS still reserves
    // both banks, so doubling their size costs another 1MiB of actual VRAM.
    // Flycast's zero TA-used register does not qualify physical TA capacity.
    params.vertex_buf_size=RE4DC_TA_VERTBUF_KB*1024;params.vbuf_doublebuf_disabled=!RE4DC_TA_DOUBLEBUF;
    if(RE4DC_TA_OPB_BINS==32){params.opb_sizes[PVR_LIST_OP_POLY]=PVR_BINSIZE_32;params.opb_sizes[PVR_LIST_TR_POLY]=PVR_BINSIZE_32;}
#if RE4DC_TREE_IMPOSTOR
    // Impostor quads (re4dc_model_pt_begin). A scene that sends no PT list
    // gets KOS's blank one at pvr_scene_finish(), so every scene completes.
    params.opb_sizes[PVR_LIST_PT_POLY]=PVR_BINSIZE_8; // 8 words: half the OPB VRAM of 16
#endif
    params.opb_overflow_count=RE4DC_TA_OPB_OVERFLOW;
#if RE4DC_TA_HEADROOM
    {
        // TA_HEADROOM=n (issue 9 i9d): n more overflow pools per bank, each the size of the initial object pointer
        // blocks (KOS pvr_allocate_buffers: opb_total_size x (1 + opb_overflow_count) after the vertex buffer),
        // paid for by the vertex buffer so the texture pool does not shrink.
        unsigned words=0;
        for(unsigned l=0;l<PVR_OPB_COUNT;++l)words+=unsigned(params.opb_sizes[l]);
        const unsigned step=words*4U*(640U/32U)*(480U/32U),shrink=(step*unsigned(RE4DC_TA_HEADROOM)+1023U)&~1023U;
        params.opb_overflow_count=RE4DC_TA_OPB_OVERFLOW+RE4DC_TA_HEADROOM;
        params.vertex_buf_size=RE4DC_TA_VERTBUF_KB*1024-int(shrink);
        ta_vertex_bytes=unsigned(params.vertex_buf_size);
        re4dc_log("TA headroom %u: opb overflow %u -> %u (+%u B pool per bank), vertex buffer %u -> %u B per bank\n",
            unsigned(RE4DC_TA_HEADROOM),unsigned(RE4DC_TA_OPB_OVERFLOW),unsigned(params.opb_overflow_count),
            step*unsigned(RE4DC_TA_HEADROOM),unsigned(RE4DC_TA_VERTBUF_KB)*1024U,ta_vertex_bytes);
    }
#endif
#endif
#if RE4DC_MV_SHADOWS
    {
        // MV_SHADOWS: object pointer blocks for the opaque modifier volume list (MV_OPB_BINS words per tile), in the
        // initial blocks and every overflow pool (KOS pvr_allocate_buffers: opb_total_size x (1 + overflow) after the
        // vertex buffer), paid for by the vertex buffer so the texture pool does not shrink.
        params.opb_sizes[PVR_LIST_OP_MOD]=RE4DC_MV_OPB_BINS==16?PVR_BINSIZE_16:PVR_BINSIZE_8;
        const unsigned words=RE4DC_MV_OPB_BINS==16?16U:8U;
        const unsigned shrink=(words*4U*(640U/32U)*(480U/32U)*(1U+unsigned(params.opb_overflow_count))+1023U)&~1023U;
        params.vertex_buf_size-=int(shrink);
        ta_vertex_bytes=unsigned(params.vertex_buf_size);
        re4dc_log("MV shadows: OP_MOD blocks %u words, %u B per bank from the vertex buffer (now %d B)\n",words,shrink,params.vertex_buf_size);
    }
#endif
    params.autosort_disabled=1; // source OT is the UI blending order
#if RE4DC_RES_MODES
    ta_vertex_bytes=re4dc_res_params(&params); // res_mode.cpp: the allocation for the largest available mode
#endif
    ready=pvr_init(&params)==0;
#if RE4DC_GC_ASSET_GATE
    if(ready)gcasset_startup();
#endif
#if RE4DC_MV_SHADOWS
    if(ready)pvr_set_shadow_scale(true,float(RE4DC_MV_SCALE)/100.0f); // cheap shadow: receivers inside a volume at this intensity
#endif
#if RE4DC_RES_MODES
    if(ready)re4dc_res_init();
#endif
#if RE4DC_VGA_SOFT
    if(ready)re4dc_vga_soft_init(); // vga_soft.cpp (VGA_SOFT)
#endif
    re4dc_log("native UI: PVR init %s; source ID adapter, 640x480\n",ready?"ok":"FAILED");
#if RE4DC_POISON_RAM
    if(ready){
        size_t n=pvr_mem_available()&~31U;void* v=nullptr;
        while(n>=65536 && !(v=pvr_mem_malloc(n)))n-=32768;
        if(v){
            const std::uint32_t w=0x01010101U*unsigned(RE4DC_POISON_RAM);
            volatile std::uint32_t* d=static_cast<volatile std::uint32_t*>(v);
            for(size_t i=0;i<n/4;++i)d[i]=w;
            pvr_mem_free(v);
        }
        re4dc_log("native UI: POISON_RAM %02x VRAM %u bytes\n",unsigned(RE4DC_POISON_RAM),unsigned(v?n:0));
    }
#endif
    if(ready){
#if RE4DC_PVR_STREAM
        if(pvr_set_manual_flip(true)<0)re4dc_missing("native manual presentation init failed");
        re4dc_log("native source stream: enabled, scratch=65536 TA=1048576 single-bank; late hold/retire/black preserved\n");
#endif
#if RE4DC_PVR_FAST_WAKE || RE4DC_PVR_PIPELINE
        install_fast_wake();
#endif
#if RE4DC_PVR_PIPELINE
        start_presenter();
#endif
#if RE4DC_TA_GUARD
        install_guard();
#endif
#if RE4DC_PVR_RECOVER
        pvr_recover::install();   // above the fast-wake chain, below the latch (a recovery calls the chain below it)
#endif
#if RE4DC_PVR_LATCH
        latch::install();   // after install_fast_wake: chains its render-done handler
#endif
#if RE4DC_TA_GUARD || RE4DC_PERF_HUD || RE4DC_TA_VERTBUF_KB!=1024 || RE4DC_TA_DOUBLEBUF || RE4DC_TA_OPB_BINS!=16 || RE4DC_TA_OPB_OVERFLOW!=3
        re4dc_log("native VRAM layout: vertbuf=%u KiB x%u banks (%s) opb_bins=%u overflow=%u texture_pool_free=%u\n",
            unsigned(RE4DC_TA_VERTEX_BYTES/1024U),2U,RE4DC_TA_DOUBLEBUF?"double-buffered":"single-bank use",unsigned(RE4DC_TA_OPB_BINS),unsigned(RE4DC_TA_OPB_OVERFLOW+RE4DC_TA_HEADROOM),(unsigned)pvr_mem_available());
#endif
#if RE4DC_TEX_PAL4_ALPHA
        // One global format and bank owner for message glyphs and packages.
        if(!re4dc::texture::initialize_palettes(RE4DC_NATIVE_MES ? 0xffU : 0U))
            re4dc_missing("native palette configuration changed");
#endif
#if RE4DC_NATIVE_MES
#if RE4DC_UI_VRAM && RE4DC_VRAM_CENSUS
        census_heap_base=PVR_RAM_INT_TOP-pvr_mem_available(); // no texture RAM allocated yet
#endif
        glyph_init(); // before the UI_VRAM budget: the atlas is part of the accounted pool
#endif
#if RE4DC_UI_VRAM && RE4DC_TEX_RESIDENT && RE4DC_UI_OVERLAY_SLAB_KB
        overlay_slab_take(); // beside the glyph atlas, before the budget: never part of the pool
        re4dc_log("native UI: overlay slab %u B at %08x\n",kOverlaySlabBytes,(unsigned)overlay_slab);
#endif
#if RE4DC_UI_VRAM
        {
            const unsigned pool=pvr_mem_available(),reserve=RE4DC_UI_VRAM_RESERVE_KB*1024U;
            vram_budget=pool>reserve?pool-reserve:0;
            re4dc_log("native UI: texture VRAM budget=%u pool=%u reserve=%u (LRU evict + fragmentation retry)\n",vram_budget,pool,reserve);
        }
#endif
        pvr_set_bg_color(0,0,0);
        // Source camera-space units can exceed 10,000. KOS's default 0.0001
        // inverse background depth hides those valid source polygons. Leave
        // near/far visibility to the existing source-projection clipper and
        // place the background behind every positive inverse model depth.
        pvr_set_zclip(0.0f);
#if RE4DC_TREE_IMPOSTOR
        PVR_SET(PVR_PT_ALPHA_REF,128); // punch-through keeps texels with alpha >= 50%
#endif
    }
}
#if RE4DC_PACE_CATCHUP
unsigned pace_skipped_frames;   // skipped iterations: frame + this = iterations (PC sampler marks)
// Skipped iteration (pace.cpp): the per-tick model preparation and asset registration run as in
// re4dc_ui_begin; the frame is not begun (frame_ready=false: every emission entry returns before
// any work, no texture is resolved or uploaded, no preload, no fog), `frame` does not advance.
extern "C" void re4dc_ui_begin_skip(){
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    sob33_barrier(re4dc::sob33::FrameReset);
#endif
#if RE4DC_WORLD_SCRATCH
    re4dc_world_scratch_boundary(1,re4dc_ps2_mesh_room());
#endif
#if RE4DC_SS_UI_ORDER
    ui_order=false;quads_flushed=0;
#endif
    re4dc_model_preparation_frame();
#if RE4DC_D349_RENDERER_STACK
    if(deferred_first)re4dc_missing("source pose queue crossed frame reset");
    reset_deferred();source_draws_finished=false;desired_list=PVR_LIST_OP_POLY;
#endif
#if RE4DC_PVR_STREAM
    if(stream_scene || stream_retire)re4dc_missing("native previous frame unresolved");
    stream_aborted=false;stream_model_bytes=0;
#endif
    nquad=0;model_used=0;frame_ready=false;pace_skip_frame=true;++pace_skipped_frames;
#if RE4DC_WORLD_SCRATCH
    re4dc_world_scratch_begin(re4dc_ps2_mesh_room());
#endif
    re4dc_prepare_model_assets();
}
// Skipped iteration: nothing to present; the previous picture stays. Frame boundary only.
extern "C" void re4dc_ui_end_frame_skip(){
#if RE4DC_WORLD_SCRATCH
    Re4dcWorldScratchFrameEnd scratch_frame_end{&stream_aborted};
#endif
    re4dc_pcs_frame(frame+pace_skipped_frames);
}
#endif
#if RE4DC_DOOR_FREEZE && RE4DC_PVR_STREAM
// DOOR_FREEZE=1 (Makefile, default 0; render only): the door transition's stop filter (src/game/filter09.cpp, the
// GameCube's Filter09: the last picture frozen, spreading outwards, under the 120-frame fade while the next room loads;
// Render() draws it every frame, also while System_flg 0x100000 stops Trans()).
// Capture: the picture on screen (any RES mode: read through the display registers) into a 320x240 RGB565 stride
// texture (150 KiB, pvr_mem_malloc). Draw: per frame the feedback terms as layered quads inside the source's scissor
// band (y 56..424 of 480), then the source fades over them. Free: at the first frame start where the filter is off
// (Filter09SetbUse(0) / FilterRoomInit) or a room texture preload is due, before any of the next room's uploads.
extern "C" int re4dc_door_in_use(void);                        // filter09.cpp
extern "C" unsigned re4dc_door_fades(unsigned* argb,unsigned max); // filter09.cpp
namespace {
constexpr unsigned kDoorW=320,kDoorH=240,kDoorBytes=kDoorW*kDoorH*2,kDoorMargin=32768,kDoorLayers=8;
// The picture's size: 320x240, else (fragmented VRAM: r101 -> r103 had 0.9 MB free and no 150 KiB block) 160x240, 160x120.
unsigned door_w=kDoorW,door_h=kDoorH,door_tw=512,door_th=256;
pvr_ptr_t door_tex;unsigned door_frame=~0U,door_steps,door_captures,door_draws,door_held_frames;bool door_held;
// LOAD_INDICATOR + DOOR_FREEZE: the first UI quad drawn after FadeControl (the PS2 loading banner); the picture and the
// fades go under it, as the PS2 draws the banner after the fade. ~0U = none this frame (draw order unchanged).
unsigned door_ui_mark=~0U;
// The last frame that drew the loading banner: the room set-up turns the filter off (FilterRoomInit) while the banner is
// still up, so the hold below also lasts while the banner is drawn (else the held frame is the bare clear colour +
// the banner). Never set without LOAD_INDICATOR.
unsigned door_banner_frame=~0U;
bool door_hold_now(){return re4dc_door_in_use()!=0 || door_banner_frame==frame;}
void door_release(const char* why){
    if(!door_tex)return;
#if RE4DC_PVR_PIPELINE
    present_fence();
#endif
    if(re4dc::gpu::quiesce()!=re4dc::gpu::FenceResult::ready){re4dc_log("door freeze: release fence pending\n");return;}
    pvr_mem_free(door_tex);door_tex=nullptr;
    // Freed for the next room's preload while the filter is still on (the load continues): its frames would be empty
    // (black); they are not presented, so the last frozen picture stays on screen until the filter goes off.
    door_held=door_hold_now();
    re4dc_log("door freeze: released (%s) frame=%u draws=%u free=%u\n",why,frame,door_draws,(unsigned)pvr_mem_available());
}
// One textured quad: the picture scaled by (kx, ky) about the screen centre, clipped to x 0..640, y 56..425 (the
// source's GXSetScissor(0, 56, W, H - 111)), alpha a.
void door_quad(float kx,float ky,unsigned a){
#if RE4DC_TA_MATERIAL_DIAG
    tamat::Scope source_scope(3);
#endif
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,PVR_LIST_TR_POLY,PVR_TXRFMT_RGB565|PVR_TXRFMT_NONTWIDDLED|PVR_TXRFMT_X32_STRIDE,
        door_tw,door_th,door_tex,PVR_FILTER_BILINEAR);
    c.gen.culling=PVR_CULLING_NONE;c.depth.comparison=PVR_DEPTHCMP_ALWAYS;c.depth.write=PVR_DEPTHWRITE_DISABLE;
    c.blend.src=PVR_BLEND_SRCALPHA;c.blend.dst=PVR_BLEND_INVSRCALPHA;c.txr.env=PVR_TXRENV_MODULATEALPHA;c.txr.uv_clamp=PVR_UVCLAMP_NONE;
    pvr_poly_hdr_t header;pvr_poly_compile(&header,&c);
    alignas(32) pvr_vertex_t packet[5]{};std::uint32_t count;
    re4dc::render::begin_pvr_packet(packet,count,header);
    // Screen x = 320 + (u' - 0.5) * 640 kx for picture u' in 0..1; inverted at the clipped edges.
    const float x0=0,x1=640,y0=56,y1=425;
    const float u0=0.5f+(x0-320)/(640*kx),u1=0.5f+(x1-320)/(640*kx),v0=0.5f+(y0-240)/(480*ky),v1=0.5f+(y1-240)/(480*ky);
    const float su=float(door_w)/float(door_tw),sv=float(door_h)/float(door_th),layer=overlay_depth();
    const float xs[]={x0,x1,x0,x1},ys[]={y0,y0,y1,y1},us[]={u0,u1,u0,u1},vs[]={v0,v0,v1,v1};
    for(unsigned i=0;i<4;++i){auto& v=packet[count+i];v.flags=i==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;
        v.x=RE4DC_UI_X(xs[i]);v.y=RE4DC_UI_Y(ys[i]);v.z=layer;v.u=us[i]*su;v.v=vs[i]*sv;v.argb=(a<<24)|0xffffffU;v.oargb=0;}
    stream_send(packet,sizeof(packet));
}
void door_fade(unsigned argb,float y0=56,float y1=425){
#if RE4DC_TA_MATERIAL_DIAG
    tamat::Scope source_scope(3);
#endif
    alignas(32) pvr_vertex_t v[5];
    pvr_poly_cxt_t c;pvr_poly_cxt_col(&c,PVR_LIST_TR_POLY);
    c.gen.culling=PVR_CULLING_NONE;c.depth.comparison=PVR_DEPTHCMP_ALWAYS;c.depth.write=PVR_DEPTHWRITE_DISABLE;
    pvr_poly_hdr_t header;pvr_poly_compile(&header,&c);std::memcpy(&v[0],&header,sizeof(header));
    // fade.cpp fadeDraw: x 0..fbWidth, y 56..xfbHeight - 55.
    const float xs[]={0,640,0,640},ys[]={y0,y0,y1,y1},layer=overlay_depth();
    for(unsigned j=0;j<4;++j){auto& q=v[1+j];q.flags=j==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;q.x=RE4DC_UI_X(xs[j]);q.y=RE4DC_UI_Y(ys[j]);
        q.z=layer;q.u=q.v=0;q.argb=argb;q.oargb=0;}
    stream_send(v,sizeof(v));
}
void door_draw(){
    if(door_frame!=frame)return;
    if(!door_tex){ // no picture (no VRAM block at the capture): the fades and the black bars only
        unsigned fades[8];const unsigned nf=re4dc_door_fades(fades,8);
        for(unsigned i=0;i<nf;++i)if(fades[i]>>24)door_fade(fades[i]);
        door_fade(0xff000000U,0,56);door_fade(0xff000000U,425,480);
        return;
    }
    // Terms j = 0..n of B(n): weight C(n,j) (1-a)^(n-j) a^j, scale S^j; past kDoorLayers the tail is folded into the
    // last layer. Drawn back to front with "over" blending: alpha_j = w_j / sum_{i<=j} w_i.
    const float a=64.0f/255.0f,sx=680.0f/640.0f,sy=520.0f/480.0f;
    const unsigned n=door_steps;
    float w[kDoorLayers+1]{};unsigned m=0;float c=1;
    for(unsigned j=0;j<=n;++j){
        if(j)c=c*float(n-j+1)/float(j);
        float t=c;for(unsigned k=0;k<j;++k)t*=a;for(unsigned k=j;k<n;++k)t*=1-a;
        if(j<=kDoorLayers)w[m++]=t;else w[kDoorLayers]+=t;
    }
    float sum=0,kx=1,ky=1;
    for(unsigned j=0;j<m;++j){
        sum+=w[j];
        const unsigned al=j?unsigned(255.0f*w[j]/sum+0.5f):255U;
        if(al)door_quad(kx,ky,al>255?255:al);
        kx*=sx;ky*=sy;
    }
    unsigned fades[8];const unsigned nf=re4dc_door_fades(fades,8);
    for(unsigned i=0;i<nf;++i)if(fades[i]>>24)door_fade(fades[i]);
    // The game's letterbox bars are not drawn during the door: outside the band the frame showed the fogged scene
    // (Flycast r100 -> r101: grey-tan bars). Black bars, as the GameCube / PS2 door.
    door_fade(0xff000000U,0,56);door_fade(0xff000000U,425,480);
    ++door_draws;
#if defined(RE4DC_DOOR_FREEZE_SLOW_MS) && RE4DC_DOOR_FREEZE_SLOW_MS
    // Stills arms only (DOOR_FREEZE_SLOW_MS, test builds): every drawn door frame logged and held, so periodic
    // framebuffer shots land about every 10 frames. Changes door wall time: never in a gate arm.
    re4dc_log("door freeze: draw frame=%u steps=%u layers=%u fade0=%08x\n",frame,n,m,nf?fades[0]:0U);
    {const auto t=timer_us_gettime64();while(timer_us_gettime64()-t<RE4DC_DOOR_FREEZE_SLOW_MS*1000ULL){}}
#else
    if(door_draws%30==1)re4dc_log("door freeze: draw frame=%u steps=%u layers=%u fade0=%08x\n",frame,n,m,nf?fades[0]:0U);
#endif
}
}
// filter09.cpp Filter09DrawBuffer on the capture frame (inside Render(), the frame's scene is open).
extern "C" int re4dc_ui_door_capture(){
    if(!ready)return 0;
    const auto t0=timer_us_gettime64();
    if(!door_tex){
        const unsigned avail=unsigned(pvr_mem_available());
        static const unsigned short sizes[3][4]={{320,240,512,256},{160,240,256,256},{160,120,256,128}};
        for(unsigned i=0;i<3 && !door_tex;++i){
            const unsigned bytes=sizes[i][0]*sizes[i][1]*2U;
            if(avail<bytes+kDoorMargin)continue;
            door_tex=pvr_mem_malloc(bytes);
            if(door_tex){door_w=sizes[i][0];door_h=sizes[i][1];door_tw=sizes[i][2];door_th=sizes[i][3];
                if(i)re4dc_log("door freeze: fallback %ux%u (free=%u)\n",door_w,door_h,avail);}
        }
        if(!door_tex){re4dc_log("door freeze: no texture (free=%u)\n",avail);return 0;}
    }
    // The displayed field 1: start, words per line, lines, modulus (FB_R_SIZE), 16-bit RGB565 (FB_R_CTRL depth 1).
    const std::uint32_t sof=PVR_GET(PVR_FB_ADDR)&(PVR_RAM_SIZE-1),size=PVR_GET(PVR_FB_SIZE),cfg=PVR_GET(PVR_FB_CFG_1);
    const unsigned words=(size&0x3ffU)+1,lines=((size>>10)&0x3ffU)+1,mod=(size>>20)&0x3ffU;
    const unsigned stride=(words+(mod?mod:1)-1)*4,pixels=words*2;
    if(((cfg>>2)&3U)!=1U){re4dc_log("door freeze: frame buffer depth %u not RGB565\n",unsigned((cfg>>2)&3U));pvr_mem_free(door_tex);door_tex=nullptr;return 0;}
    alignas(32) std::uint16_t row[kDoorW];
    for(unsigned dy=0;dy<door_h;++dy){
        const volatile std::uint16_t* src=reinterpret_cast<const volatile std::uint16_t*>(PVR_RAM_BASE+sof+(dy*lines/door_h)*stride);
        if(pixels==2*door_w)for(unsigned dx=0;dx<door_w;++dx)row[dx]=src[2*dx];
        else for(unsigned dx=0;dx<door_w;++dx)row[dx]=src[dx*pixels/door_w];
        pvr_txr_load(row,reinterpret_cast<char*>(door_tex)+dy*door_w*2,door_w*2);
    }
    PVR_SET(PVR_TEXTURE_MODULO,door_w/32); // X32_STRIDE textures: door_w texels per row (no other stride user)
    ++door_captures;
    re4dc_log("door freeze: capture %u frame=%u fb=%06x size=%08x (%ux%u stride %u) us=%u free=%u\n",door_captures,frame,
        unsigned(sof),unsigned(size),pixels,lines,stride,unsigned(timer_us_gettime64()-t0),(unsigned)pvr_mem_available());
    return 1;
}
// filter09.cpp every frame the filter is in use: draw the picture after `steps` feedback steps at this frame's present.
extern "C" void re4dc_ui_door_queue(unsigned steps){door_frame=frame;door_steps=steps;}
// load_indicator.cpp (LOAD_INDICATOR with DOOR_FREEZE): the banner's quads start here.
extern "C" void re4dc_ui_door_mark(){if(door_ui_mark==~0U)door_ui_mark=nquad;door_banner_frame=frame;}
#endif
#if defined(RE4DC_FX_CORE_TEX_PREP) && RE4DC_FX_CORE_TEX_PREP
#include "include/native_ui_fx_core_prep.inc"
#endif
#if RE4DC_ACTOR_TEX_PREP
#include "include/native_ui_actor_tex_prep.inc"
#endif
#if RE4DC_PS2_WORLD_SOURCE_OWNER
#include "include/native_ui_source_world.inc"
#endif
#if defined(RE4DC_FX_ROOM_SPILL_FORCE) && RE4DC_FX_ROOM_SPILL_FORCE
extern "C" void* re4dc_model_deferred_storage(unsigned* bytes);
#endif
extern "C" void re4dc_ui_begin(){
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    sob33_report(frame);sob33_barrier(re4dc::sob33::FrameReset);
#endif
#if RE4DC_WORLD_SCRATCH
    re4dc_world_scratch_boundary(0,re4dc_ps2_mesh_room());
#endif
#if RE4DC_KOS_HEAP_CHECK
    re4dc_heap_check();
#endif
#if defined(RE4DC_UI_HASH_DIAG) && RE4DC_UI_HASH_DIAG
    if(++hashdiag::frames>=60){
#if defined(RE4DC_UI_SOURCE_LRU) && RE4DC_UI_SOURCE_LRU
        re4dc_log("uihash: lru evict=%u late_hits=%u bad=%u%s",source_evict,source_late_hits,source_bad,"\n");
#endif
        re4dc_log("uihash: frames=%u calls=%u bytes=%u full=%u nsource=%u/%u%s",hashdiag::frames,hashdiag::calls,hashdiag::bytes,
            hashdiag::full,nsource,kSourceCount,"\n");
        for(unsigned k=0;k<hashdiag::nrec;++k){const auto& r=hashdiag::rec[k];
            re4dc_log("uihash:  site=%08x px=%08x %ux%u fmt=%u bytes=%u n=%u%s",(unsigned)reinterpret_cast<std::uintptr_t>(r.site),
                (unsigned)reinterpret_cast<std::uintptr_t>(r.px),r.w,r.h,r.fmt,r.bytes,r.n,"\n");}
        hashdiag::frames=hashdiag::calls=hashdiag::bytes=hashdiag::full=hashdiag::nrec=0;
    }
#endif
#if RE4DC_DOOR_FREEZE && RE4DC_PVR_STREAM
    door_ui_mark=~0U;
#if RE4DC_TEX_RESIDENT
    if(door_tex && (!re4dc_door_in_use() || preload_pending))door_release(preload_pending?"preload due":"filter off");
#else
    if(door_tex && !re4dc_door_in_use())door_release("filter off");
#endif
#endif
#if RE4DC_PACE_CATCHUP
    pace_skip_frame=false;
#endif
#if RE4DC_RES_MODES
    // RES_MODES safe point: a requested render size applies before this frame computes any screen position, once
    // the previous scene is presented and the PVR is idle (res_mode.cpp; else the next frame tries again).
    if(ready && !stream_scene && !stream_retire && re4dc_res_pending()){present_fence();re4dc_res_apply_pending();}
#endif
#if RE4DC_PERF_HUD
    hud_begin_prev=hud_begin;hud_begin=timer_us_gettime64();
#endif
    re4dc_model_preparation_frame();
#if defined(RE4DC_FX_ROOM_SPILL_FORCE) && RE4DC_FX_ROOM_SPILL_FORCE
    {unsigned force_bytes=0;(void)re4dc_model_deferred_storage(&force_bytes);}   // FX_ROOM_SPILL_FORCE (test only): spill cell at the room's first frame
#endif
#if RE4DC_D349_RENDERER_STACK
    if(deferred_first)re4dc_missing("source pose queue crossed frame reset");
    reset_deferred();source_draws_finished=false;desired_list=PVR_LIST_OP_POLY;
#if RE4DC_SS_UI_ORDER
    ui_order=re4dc_ss_ui_order()!=0;quads_flushed=0;
#if RE4DC_ITEM_UI_ORDER
    ui_order=ui_order || re4dc_item_ui_order()!=0;
#endif
#if RE4DC_ROUTE_MOVIES
    if(movie_texture && movie_picture)ui_order=false;
#endif
    // Subscreen models and prior 2D art share one source-ordered TR stream.
    // The ordinary gameplay OP/TR/deferred policy remains the same.
    if(ui_order){source_draws_finished=true;desired_list=PVR_LIST_TR_POLY;}
#endif
#endif
#if RE4DC_PVR_STREAM
    if(stream_scene || stream_retire)re4dc_missing("native previous frame unresolved");
    stream_aborted=false;stream_model_bytes=0;
#endif
    if(model_diagnostic==1 && frame%120==0)
        re4dc_log("native model DIAGNOSTIC boundary: frame=%u previous_bytes=%u committed_parts=%u invalid=%u resource=%u overflow=%u presented=%u\n",frame,model_used*32,model_parts,model_invalid,model_resource,model_overflow,model_presented);
#if defined(RE4DC_FX_QUEUE_LOG) && RE4DC_FX_QUEUE_LOG
    {   // FX_QUEUE_LOG (mendezfx.mk, log only): per 120 frames the peak UI quads of a frame and the peak sprites.
        static unsigned fql_quads,fql_fx,fql_used;
        fql_quads=std::max(fql_quads,nquad);fql_fx=std::max(fql_fx,fx_count);
        fql_used=std::max(fql_used,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
        if(frame%120==0){re4dc_log("fxqueue: frame=%u ui_quads_peak=%u quad_bytes=%u storage=%u fx_peak=%u queue_used_peak=%u dropped=%u\n",
            frame,fql_quads,unsigned(sizeof(Re4dcUiQuad)),unsigned(sizeof(frame_storage)),fql_fx,fql_used,fx_dropped);fql_quads=fql_fx=fql_used=0;}
    }
#endif
    nquad=0;model_used=0;++frame;
#if RE4DC_WORLD_SCRATCH
    re4dc_world_scratch_begin(re4dc_ps2_mesh_room());
#endif
#if RE4DC_TEX_CHECK
    texchk::frame_sweep();
#endif
#if RE4DC_ACTOR_TRANSACTION
#if RE4DC_ACTOR_EARLY_COARSE
    actor_texture_leases.begin_frame(frame); // Trans tickets name this exact next frame
#else
    actor_texture_leases.retire_frame(); // submitted pins retain normal GPU fencing
#endif
#endif
#if RE4DC_UI_FRAG_RESERVE
    // UI_FRAG_RESERVE: nothing is pinned by this frame yet. Fence the previous render (it may read the
    // uploads released here), release the cheapest window of unpinned uploads (leases stay), and hold the block.
    if(frag_held && frame-frag_held_frame>kFragRetryFrames)frag_release("unused");
    if(frag_want && !frag_held){
        const unsigned want=frag_want;frag_want=0;
        present_fence();
        unsigned wb=0;const unsigned wr=movie_window_release(want,false,wb);
        frag_held=pvr_mem_malloc(want);frag_held_frame=frame;
        if(frag_held){++frag_reserves;frag_frame=0;}
        re4dc_log("native UI: frag reserve %s: need=%u released=%u entries/%u B free=%u frame=%u\n",frag_held?"held":"FAILED",
                  want,wr,wb,(unsigned)pvr_mem_available(),frame);
    }
#endif
#if RE4DC_NATIVE_MES
    nglyph=0;
#endif
#if RE4DC_PVR_PIPELINE
    // The previous scene may still render/await its flip: do not wait here.
    // Its fence precedes this frame's scene begin and any VRAM change.
    frame_ready=ready;
#else
    frame_ready=ready && re4dc::gpu::quiesce()==re4dc::gpu::FenceResult::ready;
#if RE4DC_NATIVE_FOG
    if(frame_ready)re4dc_fog_frame(); // PVR fog table/colour; the previous render has completed
#endif
#endif
#if RE4DC_TEX_RESIDENT
#if RE4DC_TEX_PACK
    // A preload pass that met a pack read error: once the pack is ready (or absent / invalid: per-file loads), run it
    // again for the picks it skipped (resident ones are kept).
    if(preload_after_pack && texpack::settled()){preload_after_pack=false;preload_pending=true;}
#endif
    if(preload_pending && frame_ready && !vram_claims)preload_identities();
#endif
    re4dc_prepare_model_assets(); // registration/update work precedes frame submission
#if defined(RE4DC_FX_CORE_TEX_PREP) && RE4DC_FX_CORE_TEX_PREP
    fxCoreTexturePrepare(); // accepted potential FX demand before world/current-frame pins
#endif
#if RE4DC_PS2_FX_ADDITIONS && RE4DC_TEX_RESIDENT
    stage1_prepare_image(); // existing guarded preload/load path; no effect submission
#endif
#if RE4DC_ACTOR_TEX_PREP
    actor_texture_prepare(); // ordinary preload demotion has already finished
#endif
#if RE4DC_PS2_WORLD_SOURCE_OWNER
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    {
    // Common world preflight/texture work is charged once to Near OP / Other.
    re4dc::wc24::Scope wc24_prepare(re4dc::wc24::NearOP,re4dc::wc24::Other);
#endif
    sourceWorldTexturePrepare();
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    }
#endif
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    {
    re4dc::wc24::Scope wc24_prepare(re4dc::wc24::NearOP,re4dc::wc24::Other);
#endif
    re4dc_r11f_prepare(frame);
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    }
#endif
#endif
    re4dc::profile::begin();
#if defined(__sh__)
    re4dc_profile_source(&render_source_begin);
#endif
    frame_render_start=timer_us_gettime64();frame_work_start=*re4dc_model_work_stats();preparation_start=*re4dc_model_preparation_stats();
    frame_header_hits=model_header_hits;frame_header_builds=model_header_builds;
    frame_pvr_calls=frame_pvr_bytes=frame_queue_peak=frame_queue_drops=0;
}
extern "C" void re4dc_ui_submit(const Re4dcUiQuad* q){
    RE4DC_PROFILE_SCOPE(UiEnqueue);
    if(!frame_ready)return;
#if RE4DC_PVR_STREAM
    if(stream_aborted)return;
#endif
    // Source IdCommonTrans alpha-compare is GREATER 1 after modulation.
    // Zero material alpha cannot produce a surviving fragment for any blend.
    if((q->color>>24)==0){++culled;return;}
    if(q->masked || q->blend>4){++unsupported;return;}
#if RE4DC_D349_RENDERER_STACK
    if((nquad+1)*sizeof(Re4dcUiQuad)>deferred_top){RE4DC_WHD_ABORT(3,__builtin_return_address(0),unsigned(sizeof(Re4dcUiQuad)));++dropped;++frame_queue_drops;stream_aborted=true;return;}
#else
    if(nquad==kQuadCount){++dropped;return;}
#endif
#if RE4DC_UI_QUAD_LEAN
    {
        // UI_QUAD_LEAN (game30.mk, make-room F1; exact): std::isfinite on the bits. A coordinate is Inf / NaN
        // exactly when its exponent field is all ones, and then (bits & 0x7f800000) + 0x00800000 carries into bit
        // 31; any smaller exponent leaves bit 31 clear. One pass over the 16 words instead of a __unordsf2 call and a
        // compare per coordinate. =2 also runs the original test and compares the verdicts ("UQL fin" lines).
        typedef std::uint32_t quad_word __attribute__((may_alias));
        const quad_word* xy=reinterpret_cast<const quad_word*>(q->xy);
        const quad_word* uv=reinterpret_cast<const quad_word*>(q->uv);
        std::uint32_t top=0;
        for(unsigned n=0;n<8;++n) top|=((xy[n]&0x7f800000U)+0x00800000U)|((uv[n]&0x7f800000U)+0x00800000U);
#if RE4DC_UI_QUAD_LEAN>=2
        {
            static unsigned tests,rejects,mismatch;
            bool ref=false;
            for(unsigned n=0;n<8;++n) if(!std::isfinite(q->xy[n]) || !std::isfinite(q->uv[n])) {ref=true;break;}
            rejects+=ref;
            if(ref!=((top&0x80000000U)!=0) && mismatch++<8)
                re4dc_log("UQL fin MISMATCH isfinite=%d bits=%d\n",ref?0:1,(top&0x80000000U)?0:1);
            if((++tests&2047)==0) re4dc_log("UQL fin tests=%u rejects=%u mismatch=%u\n",tests,rejects,mismatch);
        }
#endif
        if(top&0x80000000U) {++unsupported;return;}
    }
#else
    for(unsigned n=0;n<8;++n) if(!std::isfinite(q->xy[n]) || !std::isfinite(q->uv[n])) {++unsupported;return;}
#endif
    if(!drawn && !nquad) re4dc_log("native UI: first quad xy=%d,%d color=%08x\n",(int)q->xy[0],(int)q->xy[1],q->color);
    // Source texture storage can be retired by the following TaskScheduler.
    // Resolve/upload while the OT consumer still owns valid source pointers.
#if RE4DC_UI_HANDLES
    Entry* handle=resolve(q->image,nullptr,true);
#else
    Entry* handle=load(q->image);
#endif
    if(!handle){++missing;return;}
    handles[nquad]=handle;new(quads+nquad++) Re4dcUiQuad(*q);
    RE4DC_PROFILE_COUNT(UiQuads,1);RE4DC_PROFILE_COUNT(UiBytes,sizeof(Re4dcUiQuad));
    RE4DC_PROFILE_HIGH(UiCapacity,sizeof(frame_storage));
}
#if RE4DC_UI_HUD_MASK
#include "include/hud_source_mask_native.inc"
#endif
#if RE4DC_PACE_CATCHUP && RE4DC_PACE_DEBUG && RE4DC_PVR_STREAM
extern "C" int re4dc_pace_note(int* mode);   // pace.cpp
// Test builds: the 2 s note after the pacing chord (text needs a native message renderer):
// three boxes at the top left, the current mode's filled (Smooth green, Fast yellow, Off red).
void pace_note_draw(int mode){
    alignas(32) pvr_vertex_t v[1+3*4];
    pvr_poly_cxt_t c;pvr_poly_cxt_col(&c,PVR_LIST_TR_POLY);
    c.gen.culling=PVR_CULLING_NONE;c.depth.comparison=PVR_DEPTHCMP_ALWAYS;c.depth.write=PVR_DEPTHWRITE_DISABLE;
    pvr_poly_hdr_t header;pvr_poly_compile(&header,&c);std::memcpy(&v[0],&header,sizeof(header));
    static const std::uint32_t on[3]={0xf040ff40U,0xf0ffff40U,0xf0ff4040U};
    unsigned n=1;
    for(int k=0;k<3;++k){
        const float x=40.0f+k*36,y=40.0f,w=28.0f,h=16.0f;const std::uint32_t argb=k==mode?on[k]:0x60ffffffU;
        const float xs[4]={x,x,x+w,x+w},ys[4]={y+h,y,y+h,y};
        const float layer=overlay_depth();
        for(unsigned j=0;j<4;++j){auto& q=v[n++];q.flags=j==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;q.x=RE4DC_UI_X(xs[j]);q.y=RE4DC_UI_Y(ys[j]);q.z=layer;q.u=q.v=0;q.argb=argb;q.oargb=0;}
    }
    stream_send(v,n*32);
}
#endif
#if RE4DC_SS_UI_ORDER
// Same quad bytes/header path as final present; source model barriers can consume
// a prefix without dropping/reordering the unconsumed UI or reallocating storage.
static void ui_draw_quad(unsigned i){
#if RE4DC_TA_MATERIAL_DIAG
    tamat::Scope source_scope(3);
#endif
        if(!handles[i])return;
#if RE4DC_NATIVE_MES
        if(handles[i]==kGlyphRun){glyph_draw_run(quads[i].image.width,quads[i].image.height);return;}
#endif
        const auto& q=quads[i];const auto& t=handles[i]->package.textures()[0];
#if RE4DC_UI_HEADERS
        // Stable HUD/UI elements: the header (texture binding, blend) is compiled
        // once per cache entry and blend mode; later frames only write vertices.
        pvr_poly_hdr_t header;
        if(handles[i]->ui_header_key==q.blend){header=handles[i]->ui_header;}
        else {
#endif
        unsigned fmt=re4dc::texture::pvr_format(t);
        pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,PVR_LIST_TR_POLY,fmt,RE4DC_TSP_W(t),RE4DC_TSP_H(t),
                            handles[i]->package.pvr_texture(0),PVR_FILTER_BILINEAR);
        c.gen.culling=PVR_CULLING_NONE;c.depth.comparison=PVR_DEPTHCMP_ALWAYS;c.depth.write=PVR_DEPTHWRITE_DISABLE;
        const pvr_blend_mode_t src[]={PVR_BLEND_SRCALPHA,PVR_BLEND_SRCALPHA,PVR_BLEND_ONE,PVR_BLEND_DESTCOLOR,PVR_BLEND_DESTCOLOR};
        const pvr_blend_mode_t dst[]={PVR_BLEND_INVSRCALPHA,PVR_BLEND_ONE,PVR_BLEND_ONE,PVR_BLEND_ONE,PVR_BLEND_ZERO};
        c.blend.src=src[q.blend];c.blend.dst=dst[q.blend];c.txr.env=PVR_TXRENV_MODULATEALPHA;c.txr.uv_clamp=PVR_UVCLAMP_UV;
#if RE4DC_UI_HEADERS
        pvr_poly_compile(&header,&c);
        handles[i]->ui_header=header;handles[i]->ui_header_key=q.blend;
        }
#else
        pvr_poly_hdr_t header;pvr_poly_compile(&header,&c);
#endif
#if RE4DC_UI_DRAW_LEAN
        alignas(32) pvr_vertex_t commands[5];std::uint32_t count;
#else
        alignas(32) pvr_vertex_t commands[5]{};std::uint32_t count;
#endif
        re4dc::render::begin_pvr_packet(commands,count,header);
        pvr_vertex_t* v=commands+count;const unsigned order[]={0,1,3,2};
        const float layer=overlay_depth();
#if RE4DC_UI_DRAW_LEAN
        const float cover_w=float(RE4DC_COVER_W(handles[i]->package,q.image.width)),
                    texture_w=float(t.width),
                    cover_h=float(RE4DC_COVER_H(handles[i]->package,q.image.height)),
                    texture_h=float(t.height);
#endif
        for(unsigned n=0;n<4;++n){unsigned j=order[n];v[n].flags=n==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;
            v[n].x=RE4DC_UI_X(q.xy[2*j]);v[n].y=RE4DC_UI_Y(q.xy[2*j+1]);v[n].z=layer;
#if RE4DC_UI_DRAW_LEAN
            v[n].u=q.uv[2*j]*cover_w/texture_w;v[n].v=q.uv[2*j+1]*cover_h/texture_h;v[n].argb=q.color;v[n].oargb=0;}
#else
            v[n].u=q.uv[2*j]*RE4DC_COVER_W(handles[i]->package,q.image.width)/t.width;v[n].v=q.uv[2*j+1]*RE4DC_COVER_H(handles[i]->package,q.image.height)/t.height;v[n].argb=q.color;}
#endif
#if RE4DC_PVR_STREAM
        stream_send(commands,sizeof(commands));
#else
        re4dc::render::submit_pvr(commands,sizeof(commands));
#endif
        RE4DC_GCA_TEXTURE(handles[i],re4dc_gcasset::Ui);++drawn;

}
static void ui_order_flush(){
    if(re4dc_vi_black() || stream_aborted)return;
    stream_select(PVR_LIST_TR_POLY);
    while(quads_flushed<nquad && !stream_aborted)ui_draw_quad(quads_flushed++);
}
#endif
extern "C" void re4dc_ui_present(){
    RE4DC_PROFILE_SCOPE(UiDrain);
    if(!frame_ready)return; RE4DC_TEX_USE_KEYS()
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    // A missing source drain must discard a provisional image before the
    // ordinary deferred-queue assertion can treat it as a presentable scene.
    if(!source_draws_finished && !re4dc_source_world_present(frame,0,stream_aborted)){
        if(stream_scene)stream_close(false);return;
    }
#endif
#if RE4DC_D349_RENDERER_STACK
    if(deferred_first)re4dc_missing("source render barrier did not drain models");
    stream_select(PVR_LIST_TR_POLY);
#endif
#if RE4DC_PVR_STREAM
    if(!stream_scene)stream_open();
#else
    pvr_scene_begin();pvr_list_begin(PVR_LIST_TR_POLY);
    if(model_used && !re4dc_vi_black()){
        re4dc::render::submit_pvr(model_packets,model_used*sizeof(pvr_vertex_t));
        if(model_presented++<3)re4dc_log("native model DIAGNOSTIC presented: frame=%u bytes=%u\n",frame,model_used*32);
    }
#endif
#if RE4DC_ROUTE_MOVIES
    // A background picture (a route QTE cut's game frames) keeps this frame's UI quads over it.
    const bool movie_override=movie_texture && movie_picture && !movie_background;
    if(movie_texture && movie_picture)movie_draw();
#else
    constexpr bool movie_override=false;
#endif
#if RE4DC_DOOR_FREEZE && RE4DC_PVR_STREAM
    // The door picture goes over the UI drawn before the loading banner and under the banner (door_ui_mark).
    bool door_done=false;
#define RE4DC_DOOR_SPLIT(i) if((i)==door_ui_mark && !stream_aborted){door_draw();door_done=true;}
#else
#define RE4DC_DOOR_SPLIT(i)
#endif
#if RE4DC_SS_UI_ORDER
    if(frame%120==0)re4dc_log("native UI order: frame=%u active=%u flushed=%u queued=%u\n",frame,unsigned(ui_order),quads_flushed,nquad);
    for(unsigned i=quads_flushed;i<nquad && !movie_override && !re4dc_vi_black();++i){RE4DC_DOOR_SPLIT(i)ui_draw_quad(i);}
#else
    for(unsigned i=0;i<nquad && !movie_override && !re4dc_vi_black();++i){
        RE4DC_DOOR_SPLIT(i)
        if(!handles[i])continue;
#if RE4DC_NATIVE_MES
        if(handles[i]==kGlyphRun){glyph_draw_run(quads[i].image.width,quads[i].image.height);continue;}
#endif
        const auto& q=quads[i];const auto& t=handles[i]->package.textures()[0];
#if RE4DC_UI_HEADERS
        // Stable HUD/UI elements: the header (texture binding, blend) is compiled
        // once per cache entry and blend mode; later frames only write vertices.
        pvr_poly_hdr_t header;
        if(handles[i]->ui_header_key==q.blend){header=handles[i]->ui_header;}
        else {
#endif
        unsigned fmt=re4dc::texture::pvr_format(t);
        pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,PVR_LIST_TR_POLY,fmt,RE4DC_TSP_W(t),RE4DC_TSP_H(t),
                            handles[i]->package.pvr_texture(0),PVR_FILTER_BILINEAR);
        c.gen.culling=PVR_CULLING_NONE;c.depth.comparison=PVR_DEPTHCMP_ALWAYS;c.depth.write=PVR_DEPTHWRITE_DISABLE;
        const pvr_blend_mode_t src[]={PVR_BLEND_SRCALPHA,PVR_BLEND_SRCALPHA,PVR_BLEND_ONE,PVR_BLEND_DESTCOLOR,PVR_BLEND_DESTCOLOR};
        const pvr_blend_mode_t dst[]={PVR_BLEND_INVSRCALPHA,PVR_BLEND_ONE,PVR_BLEND_ONE,PVR_BLEND_ONE,PVR_BLEND_ZERO};
        c.blend.src=src[q.blend];c.blend.dst=dst[q.blend];c.txr.env=PVR_TXRENV_MODULATEALPHA;c.txr.uv_clamp=PVR_UVCLAMP_UV;
#if RE4DC_UI_HEADERS
        pvr_poly_compile(&header,&c);
        handles[i]->ui_header=header;handles[i]->ui_header_key=q.blend;
        }
#else
        pvr_poly_hdr_t header;pvr_poly_compile(&header,&c);
#endif
#if RE4DC_UI_DRAW_LEAN
        alignas(32) pvr_vertex_t commands[5];std::uint32_t count;
#else
        alignas(32) pvr_vertex_t commands[5]{};std::uint32_t count;
#endif
        re4dc::render::begin_pvr_packet(commands,count,header);
        pvr_vertex_t* v=commands+count;const unsigned order[]={0,1,3,2};
        const float layer=overlay_depth();
#if RE4DC_UI_DRAW_LEAN
        const float cover_w=float(RE4DC_COVER_W(handles[i]->package,q.image.width)),
                    texture_w=float(t.width),
                    cover_h=float(RE4DC_COVER_H(handles[i]->package,q.image.height)),
                    texture_h=float(t.height);
#endif
        for(unsigned n=0;n<4;++n){unsigned j=order[n];v[n].flags=n==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;
            v[n].x=RE4DC_UI_X(q.xy[2*j]);v[n].y=RE4DC_UI_Y(q.xy[2*j+1]);v[n].z=layer;
#if RE4DC_UI_DRAW_LEAN
            v[n].u=q.uv[2*j]*cover_w/texture_w;v[n].v=q.uv[2*j+1]*cover_h/texture_h;v[n].argb=q.color;v[n].oargb=0;}
#else
            v[n].u=q.uv[2*j]*RE4DC_COVER_W(handles[i]->package,q.image.width)/t.width;v[n].v=q.uv[2*j+1]*RE4DC_COVER_H(handles[i]->package,q.image.height)/t.height;v[n].argb=q.color;}
#endif
#if RE4DC_PVR_STREAM
        stream_send(commands,sizeof(commands));
#else
        re4dc::render::submit_pvr(commands,sizeof(commands));
#endif
        RE4DC_GCA_TEXTURE(handles[i],re4dc_gcasset::Ui);++drawn;
    }
#endif
#if RE4DC_DOOR_FREEZE && RE4DC_PVR_STREAM
    if(!door_done && !re4dc_vi_black() && !stream_aborted)door_draw(); // over the frame's world and UI, as Render() ends with it
#endif
#if RE4DC_PACE_CATCHUP && RE4DC_PACE_DEBUG && RE4DC_PVR_STREAM
    {int pace_mode;if(re4dc_pace_note(&pace_mode) && !re4dc_vi_black())pace_note_draw(pace_mode);}
#endif
#if defined(RE4DC_RENDER_OPTION) && RE4DC_RENDER_OPTION && RE4DC_PVR_STREAM
    if(!re4dc_vi_black())speed_draw();
#if defined(RE4DC_BENCHMARK) && RE4DC_BENCHMARK
    if(!re4dc_vi_black() && !stream_aborted)bench_banner_draw();   // bench.mk: on every presented frame
#elif defined(RE4DC_QA_BANNER) && RE4DC_QA_BANNER
    if(!re4dc_vi_black() && !stream_aborted && re4dc_qa_banner_on())bench_banner_draw();   // qamenu.mk: title screens
#endif
#endif
#if RE4DC_PERF_HUD
    if(!re4dc_vi_black()){
        pvr_stats_t hud_stats;pvr_get_stats(&hud_stats);
        const unsigned start=PVR_GET(PVR_TA_VERTBUF_START),pos=PVR_GET(PVR_TA_VERTBUF_POS);
        unsigned ta_bytes=pos>start?pos-start:0;   // live on hardware, 0 in Flycast
        bool ta_fault=false;
#if RE4DC_TA_GUARD
        static unsigned hud_faults;
        ta_bytes=std::max(ta_bytes,guard_estimate());
        ta_fault=guard_fault_frames+guard_render_fault_frames!=hud_faults;hud_faults=guard_fault_frames+guard_render_fault_frames;
#else
        ta_bytes=std::max(ta_bytes,stream_model_bytes/32*24);
#endif
#if RE4DC_PVR_PIPELINE
        static std::uint64_t hud_fence;
        const unsigned wait_us=unsigned(fence_wait_us-hud_fence);hud_fence=fence_wait_us;
#else
        const unsigned wait_us=completed_frame.present_wait_us;
#endif
        hud_draw(unsigned(hud_stats.frame_last_time/1000),unsigned(hud_stats.rnd_last_time/1000),wait_us,
                 ta_bytes,RE4DC_TA_VERTBUF_KB*1024U,ta_fault);
    }
#endif
#if RE4DC_PVR_STREAM
    stream_close(true);
#if RE4DC_ROUTE_MOVIES
    if(movie_texture && movie_picture && movie_shown_serial!=movie_upload_serial){
        movie_shown_serial=movie_upload_serial;++movie_presentations;
        if(!movie_first_picture_us)movie_first_picture_us=timer_us_gettime64();
    }
#endif
    if(stream_model_bytes && model_presented++<3)
        re4dc_log("native model DIAGNOSTIC presented: frame=%u bytes=%u\n",frame,stream_model_bytes);
    if(frame%120==0 || (stream_model_bytes && model_presented<=3)){
        pvr_stats_t stats;pvr_get_stats(&stats);
        re4dc_log("native stream: frame=%u model_bytes=%u peak=%u discarded=%u black_frames=%u vram_free=%u textures=%u used=%u loads=%u missing=%u ta_used=%u ta_peak=%u present_us=%llu registration_us=%llu render_us=%llu\n",frame,stream_model_bytes,stream_peak_bytes,stream_discards,stream_black_frames,(unsigned)pvr_mem_available(),kTextureCount,used,loads,missing,(unsigned)stats.vtx_buffer_used,(unsigned)stats.vtx_buffer_used_max,(unsigned long long)(stats.frame_last_time/1000),(unsigned long long)(stats.reg_last_time/1000),(unsigned long long)(stats.rnd_last_time/1000));
    }
#if defined(RE4DC_KOS_WATCH) && RE4DC_KOS_WATCH
    {
        // KOS_WATCH=1 (diagnostic, default 0): KOS malloc headroom = free chunks + what sbrk may still take below the
        // kernel stack. Logged every 60 frames and whenever it drops 2 KiB below the lowest value so far.
        extern void re4dc_kos_heap_state_cpp(unsigned*, unsigned*, unsigned*);
        static unsigned kw_min = 0xffffffffu;
        unsigned kf = 0, ku = 0, kb = 0;
        re4dc_kos_heap_state_cpp(&kf, &ku, &kb);
        const unsigned head = kf + kb;
        if (head + 2048 <= kw_min || frame % 60 == 0) {
            if (head < kw_min) kw_min = head;
            // top: the largest block KOS can still hand out in one piece (sbrk room + the top chunk); holes: free
            // chunks below the top (smaller pieces only)
            const struct mallinfo mi = mallinfo();
            const unsigned keep = (unsigned) mi.keepcost;
            re4dc_log("kos watch: frame=%u free=%u used=%u break=%u headroom=%u min=%u top=%u holes=%u\n", frame, kf, ku, kb, head,
                      kw_min, kb + keep, kf > keep ? kf - keep : 0u);
        }
    }
#endif
#if RE4DC_PVR_FAST_WAKE || RE4DC_PVR_PIPELINE
    if(frame%120==0){
#if RE4DC_PVR_PIPELINE
        re4dc_log("native pipeline: frame=%u mode=%s submitted=%u resolved=%u fence_blocked=%u fence_wait_us=%llu fence_timeouts=%u failures=%u wake_render=%u wake_vblank=%u\n",
            frame,RE4DC_PVR_PIPELINE==2?"kos-async":"presenter",present_submitted,present_resolved,fence_blocked,(unsigned long long)fence_wait_us,fence_timeouts,present_failures,wake_renders,wake_vblanks);
#else
        re4dc_log("native pipeline: frame=%u mode=fast-wake wake_render=%u wake_vblank=%u\n",frame,wake_renders,wake_vblanks);
#endif
    }
#endif
#if RE4DC_TA_GUARD
    if(frame%120==0)re4dc_log("native TA guard: frame=%u hw_param=%u hw_peak=%u est=%u est_peak=%u scale=%u reserve=%u skips=%u ta_fault_frames=%u render_fault_frames=%u discards=%u opb_pos=%08x\n",
        frame,guard_hw_last,guard_hw_peak,guard_sw_last,guard_sw_peak,guard_scale,guard_reserve,guard_skips,guard_fault_frames,guard_render_fault_frames,guard_discards,guard_opb_last);
#endif
#if RE4DC_TA_DIRECT
    if(frame%120==0)re4dc_log("native direct: frame=%u parts=%u slots=%u\n",frame,direct_parts,direct_slots);
#endif
#else
    pvr_list_finish();pvr_scene_finish();
#endif
    if(frame%120==0 && model_diagnostic==1)
        re4dc_log("native model DIAGNOSTIC: frame=%u packets=%u parts=%u invalid=%u resource=%u overflow=%u input=%u emitted=%u peak=%u heap=%d black=%d\n",frame,model_used*32,model_parts,model_invalid,model_resource,model_overflow,model_input,model_output,model_peak,re4dc_ui_heap_free(),re4dc_vi_black());
    if(frame%120==0 && model_diagnostic==1)
        re4dc_log("native model rejection: capacity=%u state=%u texture=%u wrap=%u empty=%u scale_rebuild=%u\n",model_capacity_rejects,model_state_rejects,model_texture_rejects,model_wrap_rejects,model_empty_parts,model_scale_rebuilds);
    if(frame%120==0 && model_diagnostic==1)re4dc_log("native model alpha: material=%u vertex=%u faded=%u masks=unsupported\n",model_alpha_material,model_alpha_vertex,model_alpha_faded);
#if defined(RE4DC_MODEL_DROP_LOG) && RE4DC_MODEL_DROP_LOG
    if(frame%600==0)re4dc_model_drop_summary();
#endif
#if defined(RE4DC_GANADO_ATLAS_DROP) && (RE4DC_GANADO_ATLAS_DROP & 0x100)
    if(frame%150==0){
        // the frames since each atlas entry was last touched (drawn, leased or pinned by a preload), -1 = not resident
        unsigned age[5];for(unsigned i=0;i<5;++i){age[i]=~0U;for(const auto& e:entries)if(e.valid && e.key==kGadKeys[i])age[i]=frame-e.frame;}
        re4dc_log("ganado atlas hits: frame=%u em15-00=%u/%d em15-03=%u/%d em15-04=%u/%d em15-0b=%u/%d em12-01=%u/%d drops=%u closes=%u\n",frame,
                  gad_hits[0],int(age[0]),gad_hits[1],int(age[1]),gad_hits[2],int(age[2]),gad_hits[3],int(age[3]),gad_hits[4],int(age[4]),gad_drops,gad_closes);
        // diagnostic: every 256+ texture touched in the last 150 frames
        for(const auto& e:entries)if(e.valid && e.package.upload_complete() && e.package.textures()[0].width>=256 && frame-e.frame<150)
            re4dc_log("ganado atlas diag: touched %08x-%08x %ux%u age=%u bytes=%u\n",e.key.crc,e.key.fnv,e.package.textures()[0].width,
                      e.package.textures()[0].height,frame-e.frame,(unsigned)e.package.vram_bytes());
    }
#endif
    if(frame%120==0) re4dc_log("native UI: frame=%u quads=%u drawn=%u missing=%u unsupported=%u drops=%u vram=%u peak=%u staging=%u loads=%u freed=%u culled=%u fb=%08x,%08x black=%d\n",frame,nquad,drawn,missing,unsupported,dropped,used,peak,staging_peak,loads,reclaimed,culled,(unsigned)pvr_get_front_buffer(),(unsigned)pvr_get_back_buffer(),re4dc_vi_black());
#if RE4DC_UI_VRAM
    if(frame%120==0) re4dc_log("native UI VRAM: frame=%u budget=%u used=%u free=%u rejects=%u retries=%u evicted=%u\n",frame,vram_budget,used,(unsigned)pvr_mem_available(),vram_rejects,vram_retries,reclaimed);
#if RE4DC_UI_FRAG_WINDOW
    if(frame%120==0) re4dc_log("native UI frag window: frame=%u ok=%u none=%u bytes=%u drops=%u drop_ok=%u\n",frame,frag_win_ok,frag_win_none,frag_win_bytes,frag_drops,frag_drop_ok);
#endif
#if RE4DC_TEX_USE_CENSUS
    // TEX_USE_CENSUS (test only): how much of the resident set the last 2 s / 20 s actually drew (entry.frame is the
    // last frame a draw or a preload touched it).
    if(frame%600==0){
        unsigned n=0,b=0,i60=0,b60=0,i600=0,b600=0;
        for(const auto& e:entries)if(e.valid){
            const unsigned sz=e.package.vram_bytes();++n;b+=sz;
            if(e.frame+60<frame){++i60;b60+=sz;}
            if(e.frame+600<frame){++i600;b600+=sz;}
        }
        // the room archive's identities among them (the room-entry preload's first pass)
        unsigned rn=0,rb=0,r600=0,rb600=0;
        for(unsigned i=0;i<room_identities.count();++i){
            unsigned crc,fnv,w,h,f;
            if(!room_identities.record(i,crc,fnv,w,h,f))continue;
            const Key key{crc,fnv};
            for(const auto& e:entries)if(e.valid && e.key==key){
                const unsigned sz=e.package.vram_bytes();++rn;rb+=sz;
                if(e.frame+600<frame){++r600;rb600+=sz;}
                break;
            }
        }
        re4dc_log("tex use census: frame=%u resident=%u/%u B idle2s=%u/%u B idle20s=%u/%u B loads=%u freed=%u "
                  "room=%u/%u B room_idle20s=%u/%u B\n",frame,n,b,i60,b60,i600,b600,loads,reclaimed,rn,rb,r600,rb600);
    }
#endif
#if RE4DC_VRAM_CENSUS
    if(frame%120==0)vram_census("frame");
#endif
#if RE4DC_VRAM_ROOM_LOG
    vram_room_frame();
#endif
#endif
#if RE4DC_EFFECT_SPRITES
    if(frame%120==0) re4dc_log("native effect sprites: frame=%u queued=%u direct=%u missing=%u dropped=%u capped=%u culled=%u peak=%u\n",frame,fx_queued,fx_direct,fx_missing,fx_dropped,fx_capped,fx_culled,fx_peak);
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
    if(frame%120==0) re4dc_log("native effect guard: frame=%u resident_only_skips=%u\n",frame,fx_resident_skips);
#if defined(RE4DC_FX_TEX_POOL) && RE4DC_FX_TEX_POOL
    if(frame%120==0) re4dc_log("native effect pool: frame=%u pinned_bytes=%u pins=%u full=%u budget=%u vram_free=%u\n",frame,
                               fx_pool_bytes,fx_pool_pins,fx_pool_full,unsigned(RE4DC_FX_TEX_POOL)*1024U,(unsigned)pvr_mem_available());
#endif
#endif
#endif
#if RE4DC_NATIVE_MES
    if(frame%120==0 && (glyph_total!=glyph_logged_total || glyph_full+glyph_dropped+glyph_unsupported!=glyph_logged_problems)){
        glyph_logged_total=glyph_total;glyph_logged_problems=glyph_full+glyph_dropped+glyph_unsupported;
        unsigned live=0;for(const auto& c:glyph_cells)live+=c.valid;
        re4dc_log("native mes: frame=%u glyphs=%u peak=%u total=%u drawn=%u cells=%u/%u hits=%u misses=%u evictions=%u fenced=%u full=%u dropped=%u unsupported=%u culled=%u fonts=%u\n",
            frame,nglyph,glyph_peak,glyph_total,glyph_drawn,live,kGlyphCells,glyph_hits,glyph_misses,glyph_evictions,glyph_fenced,glyph_full,glyph_dropped,glyph_unsupported,glyph_culled,glyph_font_changes);
    }
#endif
#if RE4DC_UI_HANDLES
    if(frame%120==0) re4dc_log("native UI handles: frame=%u hits=%u misses=%u bypass=%u\n",frame,handle_hits,handle_misses,handle_bypass);
#endif
}

extern "C" void re4dc_ui_end_frame(int present){
#if RE4DC_GC_ASSET_GATE
    struct GcAssetFrameFlush {
        ~GcAssetFrameFlush(){
            gcasset_flush();
            // the open visit at 120 frames, then every 600 (judge contract v2; a 60 s
            // census run reaches only a few hundred room frames)
            static unsigned serial,frames;
            if(!gcasset_visit_live)return;
            if(serial!=gcasset_visit_serial){serial=gcasset_visit_serial;frames=0;}
            ++frames;if(frames==60 || (frames>60 && !((frames-60)%600)))gcasset_checkpoint();
        }
    } gcasset_frame_flush;
#endif
#if RE4DC_WORLD_SCRATCH
    Re4dcWorldScratchFrameEnd scratch_frame_end{&stream_aborted};
#endif
#if defined(RE4DC_FX_CORE_TEX_PREP) && RE4DC_FX_CORE_TEX_PREP
    fxCoreFinish();
#endif
    const auto render_end=timer_us_gettime64();
#if RE4DC_DOOR_FREEZE && RE4DC_PVR_STREAM
    if(door_held){
        if(door_hold_now()){present=0;++door_held_frames;}
        else {re4dc_log("door freeze: hold ended frame=%u held=%u\n",frame,door_held_frames);door_held=false;door_held_frames=0;}
    }
#endif
    re4dc_model_draw_plan_frame(frame);
#if RE4DC_PVR_STREAM
#if RE4DC_WORLD_SCRATCH
    if(!frame_ready || stream_aborted)re4dc_world_scratch_cancel();
#endif
    if(!frame_ready)return;
#if RE4DC_ROUTE_MOVIES
    const bool movie_shown=movie_texture && movie_picture;
    if(movie_shown)present=1;
    const bool black=re4dc_vi_black()!=0 && !movie_shown;
#else
    const bool black=re4dc_vi_black()!=0;
#endif
    if(present && !stream_aborted && !black)re4dc_ui_present();
    else {
        if(stream_scene)stream_close(false);
        // A late VI-black request must show a genuinely empty framebuffer;
        // previously submitted world packets cannot simply be ignored now.
        if(present && black){stream_open();stream_close(true);++stream_black_frames;}
    }
#if RE4DC_TEX_KEEP
#if defined(RE4DC_RETIRE_KOS_FLOOR) && RE4DC_RETIRE_KOS_FLOOR
    if(stream_retire)retire_kos_floor();     // RETIRE_KOS_FLOOR: the deferred retirement, scene closed and fenced
#endif
#if defined(RE4DC_ROOM_CHANGE_EVICT) && RE4DC_ROOM_CHANGE_EVICT
    if(stream_retire){room_change_retire();stream_retire=false;}   // ROOM_CHANGE_EVICT: LRU order kept
#else
    if(stream_retire){for(auto& entry:entries)entry.frame=0;stream_retire=false;}
#endif
#else
    if(stream_retire){for(auto& entry:entries)close_entry(entry);stream_retire=false;}
#endif
#else
    if(present)re4dc_ui_present();
#endif
    for(const auto& e:entries)if(e.valid){RE4DC_PROFILE_COUNT(TextureResidentCount,1);
        if(e.frame==frame){RE4DC_PROFILE_COUNT(TexturePinnedCount,1);RE4DC_PROFILE_COUNT(TexturePinnedBytes,e.package.vram_bytes());}}
    re4dc::profile::finish(completed_render_profile,frame,render_source_begin);
#if RE4DC_PACE_CATCHUP
    re4dc_pcs_frame(frame+pace_skipped_frames); // one mark per iteration, skipped ones included
#else
    re4dc_pcs_frame(frame); // PC_SAMPLER=1 only: frame boundary in the sample ring
#endif
#if defined(RE4DC_ENC_CENSUS) && RE4DC_ENC_CENSUS
#if RE4DC_PACE_CATCHUP
    re4dc_enc_frame(frame+pace_skipped_frames);
#else
    re4dc_enc_frame(frame);
#endif
#endif
    completed_frame.sequence=completed_frame.sequence+1;
    asm volatile("" ::: "memory");
    completed_frame.frame=frame;
    const auto now=*re4dc_model_work_stats();
    unsigned current[sizeof(now)/sizeof(unsigned)],before[sizeof(now)/sizeof(unsigned)];
    std::memcpy(current,&now,sizeof(now));std::memcpy(before,&frame_work_start,sizeof(now));
    for(unsigned n=0;n<sizeof(now)/sizeof(unsigned);++n)current[n]-=before[n];
    std::memcpy(&completed_frame.work,current,sizeof(now));
    completed_frame.pvr_calls=frame_pvr_calls;completed_frame.pvr_bytes=frame_pvr_bytes;
    completed_frame.header_hits=model_header_hits-frame_header_hits;
    completed_frame.header_builds=model_header_builds-frame_header_builds;
    const auto* plans=re4dc_model_draw_plan_stats();
    completed_frame.plan_used=plans->used;completed_frame.plan_capacity=plans->capacity;
    completed_frame.queue_peak=frame_queue_peak;completed_frame.queue_drops=frame_queue_drops;
    completed_frame.texture_vram=used;completed_frame.texture_peak=peak;
    completed_frame.native_slab=model_packets?kModelSlabBytes:0;
#if defined(RE4DC_UI_HEAP_LAZY) && RE4DC_UI_HEAP_LAZY
    // UI_HEAP_LAZY=N: this readback field's whole-heap walk (OSCheckHeap) runs every Nth frame only.
    {static int heap_free_last=-1;static unsigned heap_free_age;
     if(heap_free_last<0 || ++heap_free_age>=RE4DC_UI_HEAP_LAZY){heap_free_age=0;heap_free_last=re4dc_ui_heap_free();}
     completed_frame.source_heap_free=heap_free_last;}
#else
    completed_frame.source_heap_free=re4dc_ui_heap_free();
#endif
    completed_frame.render_wall_us=unsigned(render_end-frame_render_start);
    completed_frame.present_wait_us=unsigned(timer_us_gettime64()-render_end);
    completed_frame.present_requested=present;
#if RE4DC_PVR_STREAM
    completed_frame.aborted=stream_aborted;
#if defined(RE4DC_CLOTH_PUBLICATION11) && RE4DC_CLOTH_PUBLICATION11
    if(stream_aborted)re4dc_cloth_publication11.abort(frame);
#endif
#endif
    asm volatile("" ::: "memory");
    completed_frame.sequence=completed_frame.sequence+1;
    completed_preparation.sequence++;
    asm volatile("" ::: "memory");
    completed_preparation.frame=frame;
    unsigned prep_now[sizeof(Re4dcPreparationStats)/4],prep_before[sizeof(Re4dcPreparationStats)/4];
    std::memcpy(prep_now,re4dc_model_preparation_stats(),sizeof(prep_now));std::memcpy(prep_before,&preparation_start,sizeof(prep_before));
    for(unsigned i=0;i<sizeof(prep_now)/4;++i)prep_now[i]-=prep_before[i];
    std::memcpy(&completed_preparation.work,prep_now,sizeof(prep_now));
    completed_preparation.scratch_bytes=kModelPreparationBytes;completed_preparation.packet_bytes=kModelPacketBytes;
    asm volatile("" ::: "memory");completed_preparation.sequence++;

}

#if defined(RE4DC_G1_DIAG_INLINE) && RE4DC_G1_DIAG_INLINE
extern "C" { int re4dc_model_diag_latch=-1; }  // G1_DIAG_INLINE (native_model.h RE4DC_MODEL_DIAG): model_diagnostic, once known
#endif
extern "C" int re4dc_model_diagnostic_enabled(){
    if(model_diagnostic<0){
        file_t f=fs_open("/cd/dc/model-diagnostic.flag",O_RDONLY);
        model_diagnostic=f>=0;if(f>=0)fs_close(f);
#if defined(RE4DC_G1_DIAG_INLINE) && RE4DC_G1_DIAG_INLINE
        re4dc_model_diag_latch=model_diagnostic;
#endif
        if(model_diagnostic)re4dc_log("native model DIAGNOSTIC stack=%u source pose/camera; packets=%u metadata=%u static_lights=%u slab=%u; full TEV/fog acceptance pending\n",RE4DC_D349_RENDERER_STACK,kModelPacketBytes,kModelMetadataBytes,kModelStaticLightBytes,kModelSlabBytes);
    }
    return model_diagnostic;
}
namespace {
bool ensure_model_storage(){
#if RE4DC_MODEL_SLAB_LATCH
    if(!model_packets && model_slab_failed)return false;
#endif
    if(!model_packets){
        model_packets=(pvr_vertex_t*)memalign(32,kModelSlabBytes);
        if(!model_packets)RE4DC_PROFILE_COUNT(AllocationFailures,1);
        re4dc_log("native model slab=%08x bytes=%u source_heap=%d\n",(unsigned)model_packets,kModelSlabBytes,re4dc_ui_heap_free());
#if RE4DC_MODEL_SLAB_LATCH
        if(!model_packets){model_slab_failed=true;++model_slab_failures;
            re4dc_log("native model slab: allocation failed (%u), native model path off until the next room\n",model_slab_failures);}
#endif
    }
    return model_packets!=nullptr;
}
}
#if defined(RE4DC_MODEL_DROP_LOG) && RE4DC_MODEL_DROP_LOG
// MODEL_DROP_LOG (game30.mk, diagnostic; lane crowd12 2026-10-14, ledger G5/G6): which model parts are refused and
// why. One MODELDROP first line per (model, image, reason), then every 600 frames a MODELDROP sum line per row that
// grew. Reasons: s state (with the reason bits), g TA guard, c packet slab full, m no packet storage, t texture not
// loaded, w padded texture on a wrapping part (texture size, image size, key); actor rows a<inner> are the actor
// path's resource rejects (native_actor_fast.cpp), inner p = packet left under kCacheSlots + 64, d = direct scratch.
extern "C" unsigned re4dc_model_drop_describe(const void* model);  // model_bridge.cpp: kind<<24|id<<16|type<<8|nParts
namespace {
struct DropRow { unsigned desc, why, count, logged; const void* image; const void* info; unsigned short iw, ih, tw, th;
                 unsigned crc, fnv, wrap, verts; };
DropRow drop_rows[96]; unsigned drop_n, drop_lost, drop_last;
}
extern "C" void re4dc_model_drop(const Re4dcModelPart* p, unsigned why, unsigned a, unsigned b, unsigned crc,
                                 unsigned fnv) {
    if ((why & 0xffU) != 'a') drop_last = why;
    if (!p) return;
    const unsigned desc = re4dc_model_drop_describe(p->model);
    for (unsigned i = 0; i < drop_n; ++i) {
        DropRow& r = drop_rows[i];
        if (r.desc == desc && r.why == why && r.image == p->image.pixels && r.info == p->info) { ++r.count; return; }
    }
    if (drop_n == 96) { ++drop_lost; return; }
    DropRow& r = drop_rows[drop_n++];
    r = DropRow{desc, why, 1, 0, p->image.pixels, p->info, (unsigned short) p->image.width,
                (unsigned short) p->image.height, (unsigned short) a, (unsigned short) b, crc, fnv,
                p->wrap_s << 8 | p->wrap_t, p->position_count};
    re4dc_log("MODELDROP first frame=%u why=%c%c kind=%u id=%02x type=%u nparts=%u model=%08x info=%08x part=%08x "
              "img=%08x %ux%u fmt=%u wrap=%u,%u tex=%ux%u key=%08x-%08x verts=%u blend=%u mat=%02x\n", frame,
              why & 0xffU, (why >> 8) ? (why >> 8) & 0xffU : ' ', desc >> 24, (desc >> 16) & 0xffU, (desc >> 8) & 0xffU,
              desc & 0xffU, (unsigned) p->model, (unsigned) p->info, (unsigned) p->part, (unsigned) p->image.pixels,
              p->image.width, p->image.height, p->image.format, p->wrap_s, p->wrap_t, a, b, crc, fnv,
              p->position_count, p->blend, p->material_flags);
}
extern "C" unsigned re4dc_model_drop_last() { return drop_last; }
extern "C" void re4dc_model_drop_summary() {
    for (unsigned i = 0; i < drop_n; ++i) {
        DropRow& r = drop_rows[i];
        if (r.count == r.logged) continue;
        re4dc_log("MODELDROP sum frame=%u why=%c%c kind=%u id=%02x type=%u nparts=%u info=%08x img=%08x %ux%u wrap=%u,%u "
                  "tex=%ux%u key=%08x-%08x verts=%u count=%u new=%u lost=%u\n", frame, r.why & 0xffU,
                  (r.why >> 8) ? (r.why >> 8) & 0xffU : ' ', r.desc >> 24, (r.desc >> 16) & 0xffU,
                  (r.desc >> 8) & 0xffU, r.desc & 0xffU, (unsigned) r.info, (unsigned) r.image, r.iw, r.ih,
                  r.wrap >> 8, r.wrap & 0xffU, r.tw, r.th, r.crc, r.fnv, r.verts, r.count, r.count - r.logged,
                  drop_lost);
        r.logged = r.count;
    }
}
#define RE4DC_DROP(pp, why, a, b, crc, fnv) re4dc_model_drop((pp), (why), (a), (b), (crc), (fnv))
#define RE4DC_DROP_CLEAR() (drop_last = 0)
#else
#define RE4DC_DROP(pp, why, a, b, crc, fnv) do { } while (0)
#define RE4DC_DROP_CLEAR() do { } while (0)
#endif
extern "C" int re4dc_model_packet_reserve(const Re4dcModelPart* p,Re4dcModelPacket* out){
    RE4DC_DROP_CLEAR();
    unsigned reason=0;
    if(!frame_ready || !RE4DC_MODEL_DIAG())reason|=1;
#if RE4DC_PVR_STREAM
    if(stream_aborted)reason|=1;
#endif
    if(p->blend>4 || p->cull>2)reason|=2;
    if(p->depth_mode>2)reason|=4;
    if(p->wrap_s>1 || p->wrap_t>1)reason|=8;
#if RE4DC_D349_RENDERER_STACK
    // Same-coordinate, equal-resolution source masks are prepared offline into
    // one native texture. Other TEV/alpha-test policies remain explicit gaps.
    if((p->material_flags&4) && (!p->mask.pixels || !p->mask_same_uv || p->mask_ref!=0 ||
       p->mask.width!=p->image.width || p->mask.height!=p->image.height))reason|=16;
#else
    if(p->material_flags&4)reason|=16;
#endif
    if(p->image.format>=8 && p->image.format!=14)reason|=32;
#if RE4DC_TA_GUARD && RE4DC_D349_RENDERER_STACK
    if(!reason && !guard_admit(draining_parts)){
        // Budget skip, not a state reject: the part is simply not drawn.
        RE4DC_DROP(p,'g',0,0,0,0);++model_capacity_rejects;return 0;
    }
#endif
    if(!p->image.pixels)reason|=64;
    if(!p->image.width || !p->image.height || p->image.width>1024 || p->image.height>1024)reason|=128;
    if(reason){
        ++model_state_rejects;RE4DC_DROP(p,'s',reason,0,0,0);
        for(unsigned bit=0;bit<8;++bit)if(reason&(1U<<bit)){
            if(model_state_bits[bit]++<2)re4dc_log("native model state reject: reason=%02x model=%08x info=%08x part=%08x material=%02x blend=%u depth=%u wrap=%u,%u image=%08x %ux%u fmt=%u vertices=%u stream=%u\n",reason,(unsigned)p->model,(unsigned)p->info,(unsigned)p->part,p->material_flags,p->blend,p->depth_mode,p->wrap_s,p->wrap_t,(unsigned)p->image.pixels,p->image.width,p->image.height,p->image.format,p->position_count,p->stream_bytes);
        }
        return 0;
    }
    if(!ensure_model_storage()){RE4DC_DROP(p,'m',0,0,0,0);return 0;}
    if(model_used+4>kModelPacketBytes/32){RE4DC_DROP(p,'c',model_used,0,0,0);++model_capacity_rejects;return 0;}
    // Same default padding policy as convert_tpl; binding below checks the
    // actual package. A different native layout triggers exact UV preparation.
    unsigned width=8,height=8;
    while(width<p->image.width)width*=2;
    while(height<p->image.height)height*=2;
    model_pending=model_used+1;
    out->vertices=model_packets+model_pending;out->capacity=kModelPacketBytes/32-model_pending;
#if defined(RE4DC_G1_FP_UNSIGNED) && RE4DC_G1_FP_UNSIGNED
    // G1_FP_UNSIGNED (g1parts.mk; exact): the sizes are 1..2048 (checked above), so the signed conversion gives the
    // same floats without the double-precision unsigned conversion (two FPSCR.PR switches each).
    out->u_scale=float(int(p->image.width))/float(int(width));out->v_scale=float(int(p->image.height))/float(int(height));
#else
    out->u_scale=float(p->image.width)/width;out->v_scale=float(p->image.height)/height;
#endif
    return 1;
}
extern "C" void* re4dc_model_preparation_storage(unsigned* bytes){
    *bytes=model_packets?kModelPreparationBytes:0;
    return *bytes?reinterpret_cast<unsigned char*>(model_packets)+kModelPacketBytes:nullptr;
}
extern "C" void* re4dc_model_metadata_storage(unsigned* bytes){
    if(kModelMetadataBytes && !ensure_model_storage()){*bytes=0;return nullptr;}
    // The common slab owns allocation. This tail cannot overlap packet writes, survives
    // frame resets, and is invalidated by the same source owner generations.
    *bytes=model_packets?kModelMetadataBytes:0;
    return *bytes?reinterpret_cast<unsigned char*>(model_packets)+kModelPacketBytes+kModelPreparationBytes+kModelStaticLightBytes+kModelDeferredSpillBytes:nullptr;
}
#if RE4DC_ACTOR_UV16
extern "C" void re4dc_model_next_header_pcw(unsigned set,unsigned clear){next_pcw_set=set;next_pcw_clear=clear;}
#endif
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
extern "C" void re4dc_model_uv16_request32(unsigned certificate){actor_uv32_request.prepare(certificate);}
extern "C" unsigned re4dc_model_uv16_result32(){return actor_uv32_request.result;}
extern "C" unsigned re4dc_model_uv16_live32(const Re4dcModelPart* p,unsigned certificate){
    if(!p || !direct_open || !actor_uv32_binding.valid || actor_uv32_binding.handle!=model_handle)
        return re4dc::format32::Binding;
    return re4dc::format32::uv_decide(certificate,(p->flags&0x80000000U)!=0,p->uv_offset,
        actor_uv32_binding.width,actor_uv32_binding.height,actor_uv32_binding.u_scale,actor_uv32_binding.v_scale);
}
#endif
#if RE4DC_FRONT_NATIVE>=2 && RE4DC_UI_HANDLES && RE4DC_D349_RENDERER_STACK
// FRONT_NATIVE=2 group 8 (model_bridge.cpp): the PVR header a part would get, computed without
// side effects (no texture load, no handle touch, no pass switch, no header cache). A copy of
// re4dc_model_packet_reserve's state checks and re4dc_model_packet_begin's header build; the
// compare against the header packet_begin really built for the source part proves the copy.
extern "C" void re4dc_front_header_built(const void* header,unsigned alpha_state);
#endif
#if (RE4DC_FRONT_NATIVE>=2 || (defined(RE4DC_PREPARED_BINDING34) && RE4DC_PREPARED_BINDING34)) && RE4DC_UI_HANDLES && RE4DC_D349_RENDERER_STACK
// Read-only resident lookup. A miss leaves binding and any I/O at the old
// post-geometry packet_begin boundary; this path touches no allocator or file.
Entry* resolve_peek(const Re4dcUiImage& image,const Re4dcModelPart* masked){
    const Re4dcUiImage* mask=masked?&masked->mask:nullptr;
    unsigned shape,mask_shape=0;
    if(!handle_shape(image,shape,!mask) || (mask && !handle_shape(*mask,mask_shape,false)))return nullptr;
    const bool indexed=image.format==8 || image.format==9;
    const void* mask_pixels=mask?mask->pixels:nullptr;const void* mask_palette=mask?mask->palette:nullptr;
    const unsigned a=unsigned(reinterpret_cast<std::uintptr_t>(image.pixels)),b=unsigned(reinterpret_cast<std::uintptr_t>(mask_pixels));
    const Handle& h=handle_table[((a>>5)^(a>>13)^(b>>6)^(shape>>11))&255U];
    if(h.pixels==image.pixels && h.shape==shape && h.palette==image.palette && h.mask_pixels==mask_pixels &&
       h.mask_shape==mask_shape && h.mask_palette==mask_palette && h.stamp>handle_reset && h.stamp>entry_closed[h.entry] &&
       h.palette_bytes==image.palette_bytes && (!indexed || palette_same(unsigned(&h-handle_table),image)))return &entries[h.entry];
    return nullptr;
}
#endif
#if RE4DC_FRONT_NATIVE>=2 && RE4DC_UI_HANDLES && RE4DC_D349_RENDERER_STACK
extern "C" int re4dc_model_header_preview(const Re4dcModelPart* p,void* out){
    if(p->blend>4 || p->cull>2 || p->depth_mode>2 || p->wrap_s>1 || p->wrap_t>1)return 0;
    if((p->material_flags&4) && (!p->mask.pixels || !p->mask_same_uv || p->mask_ref!=0 ||
       p->mask.width!=p->image.width || p->mask.height!=p->image.height))return 0;
    if(p->image.format>=8 && p->image.format!=14)return 0;
    if(!p->image.pixels || !p->image.width || !p->image.height || p->image.width>1024 || p->image.height>1024)return 0;
    Entry* handle=resolve_peek(p->image,(p->material_flags&4)?p:nullptr);
    if(!handle)return 0;
    const auto& t=handle->package.textures()[0];
    if(((p->wrap_s && t.width!=p->image.width)||(p->wrap_t && t.height!=p->image.height)) && !RE4DC_WRAP_SAFE(handle->package))return 0;
    unsigned fmt=re4dc::texture::pvr_format(t);
    const pvr_list_t list=select_model_pass(p);
    pvr_poly_hdr_t header;
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,list,fmt,RE4DC_TSP_W(t),RE4DC_TSP_H(t),handle->package.pvr_texture(0),PVR_FILTER_BILINEAR);
    const pvr_cull_mode_t cull[]={PVR_CULLING_NONE,PVR_CULLING_CCW,PVR_CULLING_CW};
    c.gen.culling=cull[p->cull];
    c.depth.comparison=p->depth_mode==2?PVR_DEPTHCMP_ALWAYS:PVR_DEPTHCMP_GEQUAL;
    c.depth.write=p->depth_mode==0?PVR_DEPTHWRITE_ENABLE:PVR_DEPTHWRITE_DISABLE;
    const pvr_blend_mode_t src[]={PVR_BLEND_SRCALPHA,PVR_BLEND_SRCALPHA,PVR_BLEND_ONE,PVR_BLEND_DESTCOLOR,PVR_BLEND_ONE};
    const pvr_blend_mode_t dst[]={PVR_BLEND_INVSRCALPHA,PVR_BLEND_ONE,PVR_BLEND_ONE,PVR_BLEND_ONE,PVR_BLEND_ZERO};
    c.blend.src=src[p->blend];c.blend.dst=dst[p->blend];c.txr.env=PVR_TXRENV_MODULATEALPHA;
    c.txr.alpha=PVR_TXRALPHA_DISABLE;
    if(p->material_flags&4)c.txr.alpha=PVR_TXRALPHA_ENABLE;
    c.txr.uv_clamp=(pvr_uv_clamp_t)((p->wrap_s?0:PVR_UVCLAMP_U)|(p->wrap_t?0:PVR_UVCLAMP_V));
#if RE4DC_NATIVE_FOG
    c.gen.fog_type=p->source_key[2]?PVR_FOG_TABLE:PVR_FOG_DISABLE;
#endif
    pvr_poly_compile(&header,&c);
    std::memcpy(out,&header,sizeof(header));
    return 1;
}
#endif
#if RE4DC_MESH_TEXTURES
#if !RE4DC_D349_RENDERER_STACK
#error MESH_TEXTURES extends the D349 model packet path
#endif
// MESH_TEXTURES (native_static.cpp): set around one native mesh part's draw.
// That part binds this prepared package {crc, fnv, width, height} instead of
// its source image; its UVs address the package texture directly (scale 1).
namespace { const unsigned* model_texture=nullptr; }
extern "C" void re4dc_model_texture(const unsigned* key){model_texture=key;}
#endif
#if RE4DC_COARSE_ONE_SUBMIT && RE4DC_TA_DIRECT
// COARSE_ONE_SUBMIT (game30.mk; native_actor_fast.cpp re4dc_actor_submit_chunks): the part that opens a coarse
// actor's TA window has just been reserved (re4dc_model_packet_reserve returned 1 into *reserved, nothing ran in
// between), so packet_begin takes that reservation instead of repeating it: the same part and owner state give
// the same result, model_pending and packet fields.
namespace { const Re4dcModelPacket* model_reserved=nullptr; }
#endif
#if defined(RE4DC_PREPARED_BINDING34) && RE4DC_PREPARED_BINDING34
#if !RE4DC_PLAN_OWNER_SCOPED || !RE4DC_MODEL_DRAW_PLANS || !RE4DC_ACTOR_TRANSACTION || !RE4DC_UI_HANDLES || !RE4DC_PS2_UPLOAD_INCARNATION || !RE4DC_D349_RENDERER_STACK
#error PREPARED_BINDING34 requires scoped draw plans, texture handles and upload leases
#endif
namespace {
bool prepared_sources34(const Re4dcModelPart* p,const Re4dcModelPreparedBinding34* b,
                        Re4dcDrawOwnerStamp* capture=nullptr){
    if(!p || !p->part || !p->stream || !p->positions || !p->normals || !p->uv || !p->image.pixels ||
       !b->uv_bytes || !p->position_count || !p->normal_count || !p->position_stride || !p->normal_stride ||
       p->position_count>~0U/p->position_stride || p->normal_count>~0U/p->normal_stride)return false;
    const void* const ptr[]={p->part,p->stream,p->positions,p->normals,p->uv,p->colors,p->image.pixels,p->image.palette};
    // max_uv/max_color are the plan's highest *referenced address*, not a
    // claimed source UV/colour logical count. The old parser remains the
    // authority for index semantics; these bytes only need archive backing.
    const unsigned bytes[]={32U,p->stream_bytes,p->position_count*p->position_stride,p->normal_count*p->normal_stride,
        b->uv_bytes,b->color_bytes,b->pixel_bytes,p->image.palette_bytes};
    for(unsigned i=0;i<Re4dcModelPreparedBinding34::SpanCount;++i){
        if(!bytes[i]){
            if(capture)capture[i]={};
            else if(b->source[i].valid())return false;
            continue;
        }
        const auto stamp=re4dc_model_draw_owner_stamp(ptr[i],bytes[i]);
        if(!stamp.valid() || (!capture && !(stamp==b->source[i])))return false;
        if(capture)capture[i]=stamp;
    }
    return true;
}
Entry* prepared_entry34(const Re4dcModelPart* p,const Re4dcModelPreparedBinding34* b){
    if(!b || !b->active || !frame_ready || stream_aborted || direct_open || frame!=b->frame ||
       draining_parts || (p->material_flags&4) ||
       b->pass!=unsigned(select_model_pass(p)))return nullptr;
#if RE4DC_MESH_TEXTURES
    if(model_texture)return nullptr;
#endif
#if defined(RE4DC_PVR_RTT) && RE4DC_PVR_RTT
    unsigned rw=0,rh=0;if(re4dc_rtt_override_texture(&rw,&rh))return nullptr;
#endif
    unsigned index=~0U;
    if(!actor_texture_leases.resolve(b->texture,frame,index) || index!=b->entry || index>=kTextureCount)return nullptr;
    Entry& e=entries[index];
    if(!e.valid || !(e.key==Key{b->crc,b->fnv}) || !e.upload_incarnation ||
       e.upload_incarnation!=b->upload || !e.package.upload_complete() ||
       e.package.header().texture_count!=1 || !e.package.pvr_texture(0))return nullptr;
    const auto& t=e.package.textures()[0];
    if(t.width!=b->width || t.height!=b->height ||
       ((p->wrap_s && t.width!=p->image.width)||(p->wrap_t && t.height!=p->image.height)) && !RE4DC_WRAP_SAFE(e.package))return nullptr;
    return &e;
}
}
extern "C" int re4dc_model_packet_prepared_current34(const Re4dcModelPart* p,const Re4dcModelPreparedBinding34* b){
    return p && b && prepared_sources34(p,b) &&
        !std::memcmp(p->part,b->descriptor,sizeof(b->descriptor)) && prepared_entry34(p,b);
}
extern "C" void re4dc_model_packet_prepared_release34(Re4dcModelPreparedBinding34* b){
    if(b){actor_texture_leases.release(b->texture);b->active=0;}
}
extern "C" int re4dc_model_packet_prepare34(const Re4dcModelPart* p,unsigned uv_bytes,unsigned color_bytes,
                                                Re4dcModelPreparedBinding34* out){
    if(!out || out->active || out->texture.slot || out->texture.serial)return 0;
    // This first class is an archive-backed rigid part with an ordinary
    // resident texture. No early I/O widens the source-content interval.
    if(!p || !p->part || !p->static_geometry || !frame_ready || stream_aborted || direct_open || draining_parts ||
       (p->material_flags&4) || !actor_texture_leases.available() ||
       p->stream!=(const unsigned char*)p->part+32 || p->image.format>6 ||
       p->image.palette || p->image.palette_bytes)return 0;
#if RE4DC_MESH_TEXTURES
    if(model_texture)return 0;
#endif
#if defined(RE4DC_PVR_RTT) && RE4DC_PVR_RTT
    unsigned rw=0,rh=0;if(re4dc_rtt_override_texture(&rw,&rh))return 0;
#endif
    Re4dcModelPreparedBinding34 b{};
    b.uv_bytes=uv_bytes;b.color_bytes=color_bytes;b.pixel_bytes=image_size(p->image);
    if(!b.pixel_bytes || !prepared_sources34(p,&b,b.source))return 0;
    std::memcpy(b.descriptor,p->part,sizeof(b.descriptor));
    b.frame=frame;b.pass=unsigned(select_model_pass(p));
    // This existing resident-handle query has no I/O or allocator side effect.
    // Cold and ambiguous textures retain the original later resolve/replay.
    Entry* e=resolve_peek(p->image,nullptr);
    if(!e)return 0;
    if(frame!=b.frame || !frame_ready || stream_aborted || direct_open || draining_parts ||
       b.pass!=unsigned(select_model_pass(p)) || !prepared_sources34(p,&b) ||
       std::memcmp(p->part,b.descriptor,sizeof(b.descriptor)))return -1;
    if(!e->valid || !e->upload_incarnation || !e->package.upload_complete() ||
       e->package.header().texture_count!=1 || !e->package.pvr_texture(0))return 0;
    const auto& t=e->package.textures()[0];
    if(((p->wrap_s && t.width!=p->image.width)||(p->wrap_t && t.height!=p->image.height)) &&
       !RE4DC_WRAP_SAFE(e->package))return 0;
    b.entry=unsigned(e-entries);b.upload=e->upload_incarnation;
    b.crc=e->key.crc;b.fnv=e->key.fnv;b.width=t.width;b.height=t.height;
#if defined(RE4DC_G1_FP_UNSIGNED) && RE4DC_G1_FP_UNSIGNED
    b.u_scale=float(int(p->image.width))/float(int(t.width));
    b.v_scale=float(int(p->image.height))/float(int(t.height));
#else
    b.u_scale=float(p->image.width)/t.width;b.v_scale=float(p->image.height)/t.height;
#endif
    if(!actor_texture_leases.acquire(b.entry,frame,b.texture))return -1;
    b.active=1;
    if(!re4dc_model_packet_prepared_current34(p,&b)){
        actor_texture_leases.release(b.texture);return -1;
    }
    *out=b;return 1;
}
#endif
extern "C" int re4dc_model_packet_begin(const Re4dcModelPart* p,Re4dcModelPacket* out){
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    sob33_packet_eligible=false;sob33_packet_marker=0;
#endif
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
    // Consume before every possible return. A failed/foreign begin cannot
    // leave an actor-format request for a later unrelated part.
    const unsigned actor_uv32_pending=actor_uv32_request.take();
    actor_uv32_binding.valid=false;
#endif
#if RE4DC_GC_ASSET_GATE && defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
    gcasset_probe_outer=__builtin_return_address(0);
#endif
#if RE4DC_TA_MATERIAL_DIAG
    tamat::packet_source=2;
#endif
    RE4DC_PROFILE_SCOPE(PacketPack);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif

#if RE4DC_ACTOR_UV16
    // The actor path's per-part PCW bits (16-bit UV, strip length) go on this
    // part's slab copy only; the cached per-texture header stays generic.
    const unsigned pcw_set=next_pcw_set,pcw_clear=next_pcw_clear;next_pcw_set=next_pcw_clear=0;
#endif
#if RE4DC_COARSE_ONE_SUBMIT && RE4DC_TA_DIRECT
    if(model_reserved){*out=*model_reserved;model_reserved=nullptr;}
    else
#endif
    if(!re4dc_model_packet_reserve(p,out))return 0;
#if RE4DC_MESH_TEXTURES
    Entry* handle=nullptr;
    if(model_texture){
        const Key baked_key{model_texture[0],model_texture[1]};
        const Re4dcUiImage baked{&baked_key,nullptr,model_texture[2],model_texture[3],5,0,0}; // size checks only
        handle=load(baked,false,&baked_key);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif
if(!handle){RE4DC_DROP(p,'t',0,0,0,0);++model_texture_rejects;return 0;}
    }else{
#endif
#if RE4DC_UI_HANDLES
    const Re4dcModelPart* masked=nullptr;
#if RE4DC_D349_RENDERER_STACK
    if(p->material_flags&4)masked=p;
#endif
#if RE4DC_MESH_TEXTURES
    handle=resolve(p->image,masked,false);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif
if(!handle){RE4DC_DROP(p,'t',0,0,0,0);++model_texture_rejects;return 0;}
#else
    Entry* handle=resolve(p->image,masked,false);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif
if(!handle){RE4DC_DROP(p,'t',0,0,0,0);++model_texture_rejects;return 0;}
#endif
#else
    Key prepared{};const Key* key=nullptr;
#if RE4DC_D349_RENDERER_STACK
    if(p->material_flags&4){if(!model_mask_key(p,prepared)){RE4DC_DROP(p,'t',0,0,0,0);++model_texture_rejects;return 0;}key=&prepared;}
#endif
#if RE4DC_MESH_TEXTURES
    handle=load(p->image,false,key);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif
if(!handle){
#if RE4DC_D349_RENDERER_STACK
        if(key)log_pair_miss(p,*key);
#endif
        RE4DC_DROP(p,'t',0,0,0,0);++model_texture_rejects;return 0;}
#else
    Entry* handle=load(p->image,false,key);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif
if(!handle){
#if RE4DC_D349_RENDERER_STACK
        if(key)log_pair_miss(p,*key);
#endif
        RE4DC_DROP(p,'t',0,0,0,0);++model_texture_rejects;return 0;}
#endif
#endif
#if RE4DC_MESH_TEXTURES
    }
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
    if(!re4dc_r11f_binding_valid()){re4dc_r11f_binding_failed();return 0;}
#endif
    const auto& t=handle->package.textures()[0];
    // Repeating a padded image would repeat its border. Reject, never change wrap.
#if RE4DC_MESH_TEXTURES
    // A baked texture is addressed 0..1 as authored: no source image size to match.
    if(!model_texture && (((p->wrap_s && t.width!=p->image.width)||(p->wrap_t && t.height!=p->image.height)) && !RE4DC_WRAP_SAFE(handle->package))){RE4DC_DROP(p,'w',t.width,t.height,handle->key.crc,handle->key.fnv);++model_wrap_rejects;return 0;}
#else
    if(((p->wrap_s && t.width!=p->image.width)||(p->wrap_t && t.height!=p->image.height)) && !RE4DC_WRAP_SAFE(handle->package)){RE4DC_DROP(p,'w',t.width,t.height,handle->key.crc,handle->key.fnv);++model_wrap_rejects;return 0;}
#endif
    unsigned fmt=re4dc::texture::pvr_format(t);
    pvr_list_t list=PVR_LIST_TR_POLY;
#if RE4DC_D349_RENDERER_STACK
    if(stream_aborted)return 0;
#if RE4DC_SS_UI_ORDER
    if(ui_order && quads_flushed<nquad)ui_order_flush();
#endif
    list=draining_parts?draining_list:select_model_pass(p);
    stream_select(list);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif

#if RE4DC_PS2_WORLD_R11F_OWNER
    if(!re4dc_r11f_binding_valid()){re4dc_r11f_binding_failed();return 0;}
#endif
#endif
    pvr_poly_hdr_t header;std::uint32_t count;
#if defined(RE4DC_PVR_RTT) && RE4DC_PVR_RTT
    // PVR_RTT: the ice pass (coarse_actor_transaction.inc) draws the part again with the render target's texture,
    // UV0 in the target's repeat space, blended by the target's alpha (trans.cpp TextureBlend3, blend type 2).
    unsigned rtt_w=0,rtt_h=0;void* const rtt_tex=re4dc_rtt_override_texture(&rtt_w,&rtt_h);
    const bool rtt_pass=rtt_tex!=nullptr;
    if(rtt_pass){
        pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,list,PVR_TXRFMT_ARGB4444|PVR_TXRFMT_NONTWIDDLED,rtt_w,rtt_h,rtt_tex,PVR_FILTER_BILINEAR);
        const pvr_cull_mode_t cull[]={PVR_CULLING_NONE,PVR_CULLING_CCW,PVR_CULLING_CW};
        c.gen.culling=cull[p->cull];
        c.depth.comparison=PVR_DEPTHCMP_GEQUAL;c.depth.write=PVR_DEPTHWRITE_DISABLE;
        c.blend.src=PVR_BLEND_SRCALPHA;c.blend.dst=PVR_BLEND_INVSRCALPHA;c.txr.env=PVR_TXRENV_MODULATEALPHA;
        c.txr.alpha=PVR_TXRALPHA_ENABLE;c.txr.uv_clamp=PVR_UVCLAMP_NONE;
#if RE4DC_NATIVE_FOG
        c.gen.fog_type=p->source_key[2]?PVR_FOG_TABLE:PVR_FOG_DISABLE;
#endif
        pvr_poly_compile(&header,&c);
    } else
#endif
    {
#if RE4DC_D349_RENDERER_STACK
    const unsigned header_key=list|(p->blend<<3)|(p->depth_mode<<6)|(p->wrap_s<<8)|(p->wrap_t<<10)|((p->material_flags&4)<<12)|(p->cull<<16)
#if RE4DC_NATIVE_FOG
        |(p->source_key[2]?1U<<20:0U) // NATIVE_FOG flag (model_bridge.cpp)
#endif
        ;
    if(handle->model_header_key==header_key){header=handle->model_header;++model_header_hits;}
    else {
#endif
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,list,fmt,RE4DC_TSP_W(t),RE4DC_TSP_H(t),handle->package.pvr_texture(0),PVR_FILTER_BILINEAR);
#if RE4DC_D349_RENDERER_STACK
    // Same mapping as D349 room_strip_headers; p.cull already includes the
    // recovered game's corrected facing. Clipped fallback retains its winding.
    const pvr_cull_mode_t cull[]={PVR_CULLING_NONE,PVR_CULLING_CCW,PVR_CULLING_CW};
    c.gen.culling=cull[p->cull];
#else
    c.gen.culling=PVR_CULLING_NONE; // reference CPU-cull path
#endif
    c.depth.comparison=p->depth_mode==2?PVR_DEPTHCMP_ALWAYS:PVR_DEPTHCMP_GEQUAL;
    c.depth.write=p->depth_mode==0?PVR_DEPTHWRITE_ENABLE:PVR_DEPTHWRITE_DISABLE;
    const pvr_blend_mode_t src[]={PVR_BLEND_SRCALPHA,PVR_BLEND_SRCALPHA,PVR_BLEND_ONE,PVR_BLEND_DESTCOLOR,PVR_BLEND_ONE};
    const pvr_blend_mode_t dst[]={PVR_BLEND_INVSRCALPHA,PVR_BLEND_ONE,PVR_BLEND_ONE,PVR_BLEND_ONE,PVR_BLEND_ZERO};
    // Source materialSetup passes channel alpha through; only alphaSetup adds
    // the separate source-selected mask. UI keeps its own
    // texture-alpha policy. Never make base CMPR/intensity alpha the model mask.
    c.blend.src=src[p->blend];c.blend.dst=dst[p->blend];c.txr.env=PVR_TXRENV_MODULATEALPHA;
    c.txr.alpha=PVR_TXRALPHA_DISABLE; // unmasked source base alpha is not a mask
#if RE4DC_D349_RENDERER_STACK
    if(p->material_flags&4)c.txr.alpha=PVR_TXRALPHA_ENABLE;
#endif
    c.txr.uv_clamp=(pvr_uv_clamp_t)((p->wrap_s?0:PVR_UVCLAMP_U)|(p->wrap_t?0:PVR_UVCLAMP_V));
#if RE4DC_NATIVE_FOG
    c.gen.fog_type=p->source_key[2]?PVR_FOG_TABLE:PVR_FOG_DISABLE; // table: native_static.cpp re4dc_fog_frame
#endif
    pvr_poly_compile(&header,&c);DFA26_COUNT(model_header_builds,PacketHeaderBuild);
#if RE4DC_D349_RENDERER_STACK
        handle->model_header=header;handle->model_header_key=header_key;
    }
#endif
    }
#if RE4DC_D349_RENDERER_STACK
    if(p->cull){
        if(list==PVR_LIST_OP_POLY)RE4DC_PROFILE_COUNT(HardwareCullOP,1);
        else if(list==PVR_LIST_PT_POLY)RE4DC_PROFILE_COUNT(HardwareCullPT,1);
        else RE4DC_PROFILE_COUNT(HardwareCullTR,1);
    }
#endif
#if RE4DC_FRONT_NATIVE>=2 && RE4DC_UI_HANDLES && RE4DC_D349_RENDERER_STACK
    if(!draining_parts)re4dc_front_header_built(&header,p->alpha_state);
#endif
    re4dc::render::begin_pvr_packet(model_packets+model_used,count,header);
#if RE4DC_ACTOR_UV16
    model_packets[model_used].flags=(model_packets[model_used].flags&~pcw_clear)|pcw_set;
#endif
#if RE4DC_MV_SHADOWS
    // A shadow receiver (native_static.cpp MeshDraw: room scenery / objects) in the opaque list: cheap-shadow modifier
    // bit on this part's slab copy only (the cached header stays generic).
    if(re4dc_mv_receiver && list==PVR_LIST_OP_POLY){model_packets[model_used].flags|=PVR_TA_CMD_MODIFIER;++mv_receivers;}
#endif
    RE4DC_GAD_HIT(handle->key);RE4DC_PART_DUMP_KEY(handle->key);
    RE4DC_GCA_MODEL_PREPARE(nullptr);model_pending=model_used+count;model_handle=handle;
    out->vertices=model_packets+model_pending;out->capacity=kModelPacketBytes/32-model_pending;
#if RE4DC_MESH_TEXTURES
    if(model_texture){out->u_scale=1.0f;out->v_scale=1.0f;}
    else {
#endif
#if defined(RE4DC_G1_FP_UNSIGNED) && RE4DC_G1_FP_UNSIGNED
    {   // G1_FP_UNSIGNED: sizes <= 1024 (reserve checked them; t is a loaded texture): the same floats through int, once
        const float us=float(int(p->image.width))/float(int(t.width)),vs=float(int(p->image.height))/float(int(t.height));
        if(out->u_scale!=us || out->v_scale!=vs)DFA26_COUNT(model_scale_rebuilds,PacketUvScale);
        out->u_scale=us;out->v_scale=vs;
    }
#else
    if(out->u_scale!=float(p->image.width)/t.width || out->v_scale!=float(p->image.height)/t.height)DFA26_COUNT(model_scale_rebuilds,PacketUvScale);
    out->u_scale=float(p->image.width)/t.width;out->v_scale=float(p->image.height)/t.height;
#endif
#if RE4DC_MESH_TEXTURES
    }
#endif
#if defined(RE4DC_PVR_RTT) && RE4DC_PVR_RTT
    if(rtt_pass){out->u_scale=1.0f;out->v_scale=1.0f;}
#endif
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
    // All texture overrides and final scales are now known. Only the slab
    // copy changes; cached headers stay generic. Direct begin sends it after
    // this function returns, so the actor learns the actual committed format.
    if(actor_uv32_pending){
        unsigned width=t.width,height=t.height;
#if defined(RE4DC_PVR_RTT) && RE4DC_PVR_RTT
        if(rtt_pass){width=rtt_w;height=rtt_h;}
#endif
        actor_uv32_request.result=re4dc::format32::uv_decide(actor_uv32_pending&63U,
            (p->flags&0x80000000U)!=0,p->uv_offset,width,height,out->u_scale,out->v_scale);
        constexpr unsigned mask=(3U<<18)|1U;
        const unsigned set=(3U<<18)|(actor_uv32_request.result==re4dc::format32::Uv16?1U:0U);
        model_packets[model_used].flags=(model_packets[model_used].flags&~mask)|set;
        actor_uv32_binding={handle,width,height,out->u_scale,out->v_scale,true};
    }else actor_uv32_request.result=re4dc::format32::NotRequested;
#endif
    if(p->alpha_state&256)++model_alpha_vertex;else ++model_alpha_material;
    if(!(p->alpha_state&256) && (p->alpha_state&255)<255)++model_alpha_faded;
    if(model_parts<6)re4dc_log("native model DIAGNOSTIC source=%08x info=%08x part=%08x positions=%u stride=%u stream=%u flags=%08x material=%02x cull=%u\n",(unsigned)p->model,(unsigned)p->info,(unsigned)p->part,p->position_count,p->position_stride,p->stream_bytes,p->flags,p->material_flags,p->cull);
    RE4DC_GCA_MODEL_PREPARE(p);
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    sob33_packet_marker=p->source_key[3];sob33_packet_eligible=re4dc::sob33::marked(sob33_packet_marker);
#endif
    return 1;
}
#if defined(RE4DC_PREPARED_BINDING34) && RE4DC_PREPARED_BINDING34
extern "C" int re4dc_model_packet_begin_prepared34(const Re4dcModelPart* p,Re4dcModelPacket* out,
                                                      const Re4dcModelPreparedBinding34* prepared){
    // The ordinary header builder still owns RTT/baked/wrap/pass semantics.
    // Its second resolve should be a resident handle hit, but may yield after
    // retirement; compare the actual bound Entry before any packet commit.
    if(!prepared || !re4dc_model_packet_prepared_current34(p,prepared) ||
       !re4dc_model_packet_begin(p,out))return 0;
    return re4dc_model_packet_prepared_current34(p,prepared) &&
        model_handle==prepared_entry34(p,prepared) &&
        out->u_scale==prepared->u_scale && out->v_scale==prepared->v_scale;
}
#endif
extern "C" void re4dc_model_packet_commit(unsigned count){
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    if(!count){++sob33_stats.empty;sob33_barrier(re4dc::sob33::EmptyPacket);}
#endif
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    const re4dc::dsa24::Scope dsa_submit(re4dc::dsa24::Submit);
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    re4dc::wc24::Scope wc24_submit(re4dc::wc24::Submit);
#endif
#if RE4DC_TA_MATERIAL_DIAG
    tamat::Scope source_scope(tamat::packet_source);
#endif
    // A loaded but wholly clipped/rolled-back part owns no submitted packets.
    // Keep its upload cached; pin only when this part actually commits a draw.
    if(count){
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
        // The ordinary packet emitter stores exactly one packed-colour
        // header followed by 32-byte vertices. Incomplete/unknown layouts
        // retain their header and cannot publish a receipt for the next draw.
        const bool sob33_layout=model_packets && model_used==0 && model_pending==1 &&
            count<=kModelPacketBytes/32-1 && stream_scene && !stream_aborted;
        const bool sob33_eol=sob33_layout && model_packets[model_pending+count-1].flags==PVR_CMD_VERTEX_EOL;
        re4dc::sob33::Decision sob33_decision;
        if(sob33_packet_eligible && (!sob33_layout || !sob33_eol)){
            sob33_run.barrier();sob33_decision=re4dc::sob33::Format;
            if(sob33_layout && !sob33_eol)++sob33_stats.incomplete;
        }else sob33_decision=sob33_run.begin(reinterpret_cast<const std::uint32_t*>(model_packets),
            frame,unsigned(stream_list),frame_pvr_bytes,sob33_packet_eligible && sob33_eol);
        sob33_stats.begin(sob33_decision,unsigned(stream_list),false,sob33_packet_marker);
        const unsigned sob33_skip=sob33_decision==re4dc::sob33::Reuse?32U:0U;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        if(!sob33_skip)re4dc::wc24::submitted_header(reinterpret_cast<const std::uint32_t*>(model_packets+model_used));
#endif
#else
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24 && RE4DC_PVR_STREAM
        re4dc::wc24::submitted_header(reinterpret_cast<const std::uint32_t*>(model_packets+model_used));
#endif
#endif
        RE4DC_GCA_MODEL_TEXTURE(model_handle);
        RE4DC_GCA_MODEL_PACKET_ACCEPT(model_packets+model_pending,count);
        model_handle->frame=frame;model_used=model_pending+count;
        if(model_used*32>model_peak)model_peak=model_used*32;
#if RE4DC_PVR_STREAM
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
        const bool sob33_pending=sob33_run.pending;
        stream_send33(model_packets,model_used*32,sob33_skip);
        if(sob33_pending){
            if(sob33_run.finish(frame,unsigned(stream_list),frame_pvr_bytes,count,
                sob33_eol && stream_scene && !stream_aborted))++sob33_stats.completed;
            else ++sob33_stats.incomplete;
        }
#else
        stream_send(model_packets,model_used*32);
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        re4dc::wc24::count(re4dc::wc24::Corners,count);
#endif
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
        stream_model_bytes+=model_used*32-sob33_skip;
#else
        stream_model_bytes+=model_used*32;
#endif
        if(stream_model_bytes>stream_peak_bytes)stream_peak_bytes=stream_model_bytes;
        model_used=0; // PVR owns copied packets; reuse the same bounded scratch.
#endif
    }
}
extern "C" void re4dc_model_result(unsigned reason,unsigned input,unsigned output){
#if defined(RE4DC_MODEL_PART_DUMP)
    if(frame>=unsigned(RE4DC_MODEL_PART_DUMP) && frame<unsigned(RE4DC_MODEL_PART_DUMP)+3)
        re4dc_log("PARTDUMP f=%u key=%08x-%08x in=%u out=%u r=%u\n",frame,model_dump_crc,model_dump_fnv,input,output,reason);
    model_dump_crc=model_dump_fnv=0;
#endif
    if(reason==0){++model_parts;if(!output)++model_empty_parts;}else if(reason==1)++model_invalid;else if(reason==2)++model_resource;else ++model_overflow;
    model_input+=input;model_output+=output;
}
#if (defined(RE4DC_COARSE_PREGATE) && RE4DC_COARSE_PREGATE == 2) || (defined(RE4DC_CROWD_OUTPUT) && RE4DC_CROWD_OUTPUT)
// COARSE_PREGATE=2 (check build): the emitted-triangle total, read around each cast Ganado chunk's submission.
// CROWD_CENSUS / CROWD_CULL=2 (crowd.mk): the same total, read around each owner-path Ganado pass.
extern "C" unsigned re4dc_model_output_count(){return model_output;}
#if defined(RE4DC_ENCV) && RE4DC_ENCV
extern "C" unsigned re4dc_model_input_count(){return model_input;}  // ENC_CENSUS=2 (game30.mk): triangles in
#endif
#endif

extern "C" int re4dc_model_packet_streaming(){return RE4DC_PVR_STREAM;}
extern "C" void re4dc_model_packet_abort(){
#if RE4DC_NATIVE_FE_CONTINUATION
    re4dc_actor_native_pose_retire();
#endif
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    sob33_barrier(re4dc::sob33::PacketAbort);
#endif
#if RE4DC_WORLD_SCRATCH
    // Close admission immediately; the final synchronous borrower restores mode.
    re4dc_world_scratch_cancel();
#endif
#if RE4DC_PVR_STREAM
    RE4DC_WHD_ABORT(2,__builtin_return_address(0),0);
    // Previous chunks may already be in TA. Never present an incomplete model:
    // reject further submissions and let the same source owner discard/fence it.
    stream_aborted=true;model_used=0;model_handle=nullptr;
#endif
}

extern "C" int re4dc_model_direct_enabled(){return RE4DC_TA_DIRECT;}
#if RE4DC_TA_HASH
extern "C" void re4dc_ta_hash(const void* data,unsigned bytes){
    const unsigned l=(unsigned)stream_list<5?(unsigned)stream_list:2;
#if RE4DC_TA_HASH == 4
    {const auto* w4=static_cast<const std::uint32_t*>(data);if(bytes==4 && (w4[0]>>16)==0xF00Du)ta4_mark(w4[0]&0xFFFFu);(void)l;return;}
#endif
#if defined(RE4DC_MCHECK_PT) && RE4DC_MCHECK_PT
    pt_audit_feed(unsigned(stream_list),data,bytes,__builtin_return_address(0));
#endif
#if defined(RE4DC_BACKFACE_CENSUS) && RE4DC_BACKFACE_CENSUS
    re4dc_bfc_feed(unsigned(stream_list),data,bytes);  // backface_census.cpp (lane backface22)
#endif
#if RE4DC_TA_BIN_DIAG
    tabin::cur_ra=__builtin_return_address(0);
    tabin::feed(l,data,bytes);
#endif
    const auto* w=static_cast<const std::uint32_t*>(data);
    std::uint32_t h=ta_hash_h[l];
#if RE4DC_TA_HASH == 3
    // TA_HASH=3 (lane iv): as 2, and a header counts only once a vertex (para type 7) follows it in its list: polygons
    // with no vertex, which draw nothing, are left out (the words count counts hashed words only).
    if(bytes<32){
        for(unsigned i=0;i<bytes/4;++i)h=(h^w[i])*16777619u;
        ta_hash_words[l]+=bytes/4;
    } else for(unsigned b=0;b<bytes/32;++b){
        const std::uint32_t* q=w+b*8;
        const unsigned t=q[0]>>29;
        if(t==4u || t==5u){for(unsigned k=0;k<4;++k)ta_hash_pend[l][k]=q[k];ta_hash_pending[l]=true;continue;}
        if(t==7u && ta_hash_pending[l]){
            for(unsigned k=0;k<4;++k)h=(h^ta_hash_pend[l][k])*16777619u;
            ta_hash_words[l]+=4;ta_hash_pending[l]=false;
        }
        for(unsigned k=0;k<8;++k)h=(h^q[k])*16777619u;
        ta_hash_words[l]+=8;
    }
    ta_hash_h[l]=h;
    return;
#elif RE4DC_TA_HASH == 2
    // TA_HASH=2 (lane iv): comparable across builds: a 32-byte block whose first word is a polygon / sprite header
    // (PCW para type 4 / 5) hashes words 0..3 only (KOS leaves header words 4..7 as stack garbage).
    for(unsigned i=0;i<bytes/4;++i){
        if(bytes>=32 && (i&7)>=4 && ((w[i&~7u]>>29)==4u || (w[i&~7u]>>29)==5u))continue;
        h=(h^w[i])*16777619u;
    }
#else
    for(unsigned i=0;i<bytes/4;++i)h=(h^w[i])*16777619u;
#endif
    ta_hash_h[l]=h;ta_hash_words[l]+=bytes/4;
}
#endif
extern "C" int re4dc_model_direct_begin(const Re4dcModelPart* p,Re4dcModelDirect* out){
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    sob33_direct_candidate=false;
    if(!p || !re4dc::sob33::marked(p->source_key[3]))sob33_barrier(re4dc::sob33::ForeignDirect);
#endif
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
    struct ActorUv32BeginGuard {
        bool success=false;
        ~ActorUv32BeginGuard(){if(!success){actor_uv32_request.cancel();actor_uv32_binding.valid=false;}}
    } actor_uv32_guard;
#endif
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    const re4dc::dsa24::Scope dsa_submit(re4dc::dsa24::Submit);
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    re4dc::wc24::Scope wc24_material(re4dc::wc24::HeaderMaterial);
#endif
#if RE4DC_TA_MATERIAL_DIAG
    tamat::Scope source_scope(2);
#endif
#if RE4DC_TA_DIRECT
    if(direct_open){re4dc_missing("native direct part nested");return 0;}
    Re4dcModelPacket packet{};
#if RE4DC_GC_ASSET_GATE && defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
    const void* gcasset_direct_caller=__builtin_return_address(0);
#endif
    // Same qualification, texture bind, pass selection and header as the
    // packet path; the header lands in the slab, then goes out by store queue.
    if(!re4dc_model_packet_begin(p,&packet))return 0;
#if RE4DC_GC_ASSET_GATE && defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
    gcasset_probe_outer=gcasset_direct_caller;
#endif
    if(!stream_scene)stream_open();
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif

#if RE4DC_PS2_WORLD_R11F_OWNER
    if(!re4dc_r11f_binding_valid()){re4dc_r11f_binding_failed();return 0;}
#endif
    auto* sq=static_cast<std::uint32_t*>(static_cast<void*>(sq_lock((void*)PVR_TA_INPUT)));
    const auto* header=reinterpret_cast<const std::uint32_t*>(model_packets+model_used);
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    const auto sob33_decision=sob33_run.begin(header,frame,unsigned(stream_list),frame_pvr_bytes,
        sob33_packet_eligible && !stream_aborted);
    sob33_stats.begin(sob33_decision,unsigned(stream_list),true,sob33_packet_marker);
    const bool sob33_skip=sob33_decision==re4dc::sob33::Reuse;
    sob33_direct_candidate=sob33_run.pending;
    if(!sob33_skip){
        for(unsigned i=0;i<8;++i)sq[i]=header[i];
#if RE4DC_TA_HASH
        re4dc_ta_hash(header,32);
#endif
        sq_flush(sq);
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        re4dc::wc24::submitted_header(header);
#endif
    }
#else
    for(unsigned i=0;i<8;++i)sq[i]=header[i];
#if RE4DC_TA_HASH
    re4dc_ta_hash(header,32);
#endif
    sq_flush(sq);
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    re4dc::wc24::submitted_header(header);
#endif
#endif
    direct_open=true;
    model_handle->frame=frame; // the header is in the TA: pinned for this scene
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    if(!sob33_skip){++frame_pvr_calls;frame_pvr_bytes+=32;stream_model_bytes+=32;}
    out->sq=sq+(sob33_skip?0:8);out->scratch=packet.vertices;out->scratch_capacity=packet.capacity;
#else
    ++frame_pvr_calls;frame_pvr_bytes+=32;stream_model_bytes+=32;
    out->sq=sq+8;out->scratch=packet.vertices;out->scratch_capacity=packet.capacity;
#endif
    out->u_scale=packet.u_scale;out->v_scale=packet.v_scale;
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
    actor_uv32_guard.success=true;
#endif
    return 1;
#else
    (void)p;(void)out;return 0;
#endif
}
// WORLD_SUBMIT_END_IMPLEMENTATION
#if RE4DC_SCENERY_SUBMIT_BATCH
// The same logical end for ordinary and batched world parts. Only the caller
// decides whether to release the physical SQ mutex before this accounting.
static void model_direct_account(unsigned vertices){
#else
extern "C" void re4dc_model_direct_end(unsigned vertices){
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    const re4dc::dsa24::Scope dsa_submit(re4dc::dsa24::Submit);
#endif
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    re4dc::wc24::Scope wc24_submit(re4dc::wc24::Submit);
#endif
#if RE4DC_TA_DIRECT
#if !RE4DC_SCENERY_SUBMIT_BATCH
    if(!direct_open)return;
    sq_unlock();direct_open=false;
#endif
    if(vertices>32767)re4dc_missing("native direct part exceeded the store-queue window");
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    re4dc::wc24::count(re4dc::wc24::Corners,vertices);
#endif
#if RE4DC_GC_ASSET_MOTION_UNKNOWN
    re4dc_gcasset::motion_accept_pending(vertices);
#endif
    if(vertices) { RE4DC_GCA_MODEL_TEXTURE(model_handle);RE4DC_GCA_MODEL_ACCEPT(); }
    ++direct_parts;direct_slots+=vertices;
#if RE4DC_TA_GUARD
    guard_account(1,vertices);
#endif
    frame_pvr_bytes+=vertices*32;stream_model_bytes+=vertices*32;
    if(stream_model_bytes>stream_peak_bytes)stream_peak_bytes=stream_model_bytes;
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    // Marked bridge classes reach the ordinary actor emitter: whole meshlets
    // carry their terminal index EOL, strip emission forces its last EOL and
    // clipped triangles end at their third corner. Failure calls packet_abort
    // before this end; no read from write-only SQ memory is needed. World,
    // coarse-window and foreign producers clear this candidate at begin.
    if(sob33_direct_candidate){
        if(!vertices)++sob33_stats.empty;
        if(sob33_run.finish(frame,unsigned(stream_list),frame_pvr_bytes,vertices,
            stream_scene && !stream_aborted))++sob33_stats.completed;
        else ++sob33_stats.incomplete;
    }
    sob33_direct_candidate=false;
#endif
    model_used=0;
#else
    (void)vertices;
#endif
}
#if RE4DC_SCENERY_SUBMIT_BATCH
extern "C" void re4dc_model_direct_end(unsigned vertices){
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    const re4dc::dsa24::Scope dsa_submit(re4dc::dsa24::Submit);
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    re4dc::wc24::Scope wc24_submit(re4dc::wc24::Submit);
#endif
    if(!direct_open)return;
    sq_unlock();direct_open=false;
#if RE4DC_PS2_PVS_BATCH_COMPOSE
    sourceWorldDiagnosticSqHeld=false;sourceWorldTextureFlushAcquired();
#endif
    model_direct_account(vertices);
}
extern "C" void re4dc_ps2_world_batch_close(Re4dcWorldSubmitBatch* batch){
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    const re4dc::dsa24::Scope dsa_submit(re4dc::dsa24::Submit);
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    re4dc::wc24::Scope wc24_submit(re4dc::wc24::Submit);
#endif
    // A nested-begin refusal does not revoke the current part's ownership.
    if(batch && batch->sq && !direct_open){
        sq_unlock();batch->sq=nullptr;
#if RE4DC_PS2_PVS_BATCH_COMPOSE
        sourceWorldDiagnosticSqHeld=false;sourceWorldTextureFlushAcquired();
#endif
    }
}
extern "C" void re4dc_ps2_world_direct_end_batch(unsigned vertices,Re4dcWorldSubmitBatch* batch){
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    const re4dc::dsa24::Scope dsa_submit(re4dc::dsa24::Submit);
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    re4dc::wc24::Scope wc24_submit(re4dc::wc24::Submit);
#endif
    if(!batch || !batch->sq){re4dc_model_direct_end(vertices);return;}
    if(!direct_open)return;
    direct_open=false;
    // The original end reports overflow after unlocking. Keep that boundary.
    if(vertices>32767U)re4dc_ps2_world_batch_close(batch);
    model_direct_account(vertices);
}
#endif
// WORLD_SUBMIT_END_IMPLEMENTATION_END
#if RE4DC_MV_SHADOWS
// mv_shadow.cpp, inside stream_close only: one caster's volume (headers and 64-byte triangles, 32-byte multiples).
extern "C" int re4dc_ui_mv_send(const void* data,unsigned bytes){
    if(!stream_scene || stream_aborted || direct_open || !bytes || (bytes&31))return 0;
    if(!mv_open){stream_select(PVR_LIST_OP_MOD);if(stream_aborted || stream_list!=PVR_LIST_OP_MOD)return 0;mv_open=true;}
    stream_send(data,bytes);
    ++mv_sends;mv_bytes+=bytes;
    return 1;
}
extern "C" void re4dc_ui_mv_stats(unsigned* sends,unsigned* bytes,unsigned* scenes,unsigned* receivers){
    *sends=mv_sends;*bytes=mv_bytes;*scenes=mv_scenes;*receivers=mv_receivers;
}
#endif
#if defined(RE4DC_SHADOW_BLOB) && RE4DC_SHADOW_BLOB
// blob_shadow.cpp, inside stream_close only: one caster's blob (a TR header and its strips, 32-byte multiples). Only
// into an open or not yet used TR list (a closed list is never reopened).
extern "C" int re4dc_ui_blob_send(const void* data,unsigned bytes){
    if(!stream_scene || stream_aborted || direct_open || !world_autosort || !bytes || (bytes&31))return 0;
    if(stream_list!=PVR_LIST_TR_POLY){
        if(stream_closed_lists&(1u<<unsigned(PVR_LIST_TR_POLY)))return 0;
        stream_select(PVR_LIST_TR_POLY);
        if(stream_aborted || stream_list!=PVR_LIST_TR_POLY)return 0;
    }
    stream_send(data,bytes);
    ++blob_sends;blob_bytes+=bytes;
    return 1;
}
#endif
#if RE4DC_COARSE_ONE_SUBMIT && RE4DC_TA_DIRECT
extern "C" int re4dc_model_direct_begin_reserved(const Re4dcModelPart* p,const Re4dcModelPacket* reserved,Re4dcModelDirect* out){
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    const re4dc::dsa24::Scope dsa_submit(re4dc::dsa24::Submit);
#endif
#if RE4DC_TA_MATERIAL_DIAG
    tamat::Scope source_scope(2);
#endif
    model_reserved=reserved;
    const int begun=re4dc_model_direct_begin(p,out);
    model_reserved=nullptr; // a nested-part refusal returns before packet_begin takes it
    return begun;
}
#endif
#if defined(RE4DC_LEON_NATIVE_PIPE) && RE4DC_LEON_NATIVE_PIPE
// LEON_NATIVE_PIPE (native_model_registry.mk; render only, exact): Leon's lean owner pass keeps one store-queue window
// across the material changes of its runs. Right after a material's own window began (re4dc_model_direct_begin, in
// this submission), re4dc_leon_direct_capture records what that begin used. re4dc_leon_direct_switch, at a later
// change back to that material inside the open window (only the actor kernels ran since), does what
// re4dc_model_direct_end(vertices) followed by re4dc_model_direct_begin(part) would do for it: the same refusals for
// this state, the same header words from the same texture entry's header cache, the same slab copy and counters;
// only the store queues stay locked (their pointer continues).
#if !RE4DC_COARSE_ONE_SUBMIT || !RE4DC_TA_DIRECT || !RE4DC_D349_RENDERER_STACK || RE4DC_ACTOR_UV16 || RE4DC_TA_GUARD
#error LEON_NATIVE_PIPE extends the COARSE_ONE_SUBMIT TA_DIRECT D349 window (ACTOR_UV16=0, TA_GUARD=0)
#endif
#include "include/leon_native_pipe.h"
namespace {
unsigned leon_header_key(const Re4dcModelPart* p,unsigned list){
    // re4dc_model_packet_begin's header-cache key.
    return list|(p->blend<<3)|(p->depth_mode<<6)|(p->wrap_s<<8)|(p->wrap_t<<10)|((p->material_flags&4)<<12)|(p->cull<<16)
#if RE4DC_NATIVE_FOG
        |(p->source_key[2]?1U<<20:0U)
#endif
        ;
}
}
extern "C" int re4dc_leon_direct_capture(const Re4dcModelPart* p,Re4dcLeonHeader* out){
    out->valid=0;
#if RE4DC_MESH_TEXTURES
    if(model_texture)return 0;
#endif
    if(!p || !direct_open || !model_handle || draining_parts || !stream_scene)return 0;
    const unsigned list=unsigned(stream_list),key=leon_header_key(p,list);
    if(select_model_pass(p)!=stream_list || model_handle->model_header_key!=key)return 0;
    std::memcpy(out->words,model_packets+model_used,32);
    if(std::memcmp(out->words,&model_handle->model_header,32))return 0;
    // re4dc_model_packet_reserve's padded scale against the bound texture (re4dc_model_packet_begin's rebuild count).
    unsigned width=8,height=8;
    while(width<p->image.width)width*=2;
    while(height<p->image.height)height*=2;
    const auto& t=model_handle->package.textures()[0];
    out->scale_rebuild=(float(p->image.width)/width!=float(p->image.width)/t.width ||
                        float(p->image.height)/height!=float(p->image.height)/t.height)?1u:0u;
    out->entry=model_handle;out->list=list;out->key=key;out->valid=1;
    return 1;
}
extern "C" std::uint32_t* re4dc_leon_direct_switch(const Re4dcModelPart* p,const Re4dcLeonHeader* h,unsigned vertices,std::uint32_t* sq){
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    sob33_barrier(re4dc::sob33::ForeignDirect);
#endif
#if RE4DC_TA_MATERIAL_DIAG
    tamat::Scope source_scope(2);
#endif
    Entry* handle=static_cast<Entry*>(h?h->entry:nullptr);
#if RE4DC_MESH_TEXTURES
    if(model_texture)return nullptr;
#endif
    // The refusals the close + begin pair would meet for this captured material in this state (packet_reserve's
    // frame / stream terms, packet_begin's list and cache hit, direct_begin's nesting).
    if(!p || !h || !h->valid || !handle || !direct_open || !frame_ready || stream_aborted || draining_parts || !stream_scene ||
       !RE4DC_MODEL_DIAG() || model_used+4>kModelPacketBytes/32 || vertices>32767 ||
       unsigned(stream_list)!=h->list || select_model_pass(p)!=stream_list || leon_header_key(p,h->list)!=h->key ||
       handle->model_header_key!=h->key || std::memcmp(h->words,&handle->model_header,32))return nullptr;
    // re4dc_model_direct_end(vertices)
#if RE4DC_GC_ASSET_MOTION_UNKNOWN
    re4dc_gcasset::motion_accept_pending(vertices);
#endif
    if(vertices) { RE4DC_GCA_MODEL_TEXTURE(model_handle);RE4DC_GCA_MODEL_ACCEPT(); }
    ++direct_parts;direct_slots+=vertices;
    frame_pvr_bytes+=vertices*32;stream_model_bytes+=vertices*32;
    if(stream_model_bytes>stream_peak_bytes)stream_peak_bytes=stream_model_bytes;
    model_used=0;
    // re4dc_model_direct_begin(p): packet_reserve, packet_begin (cached header), the header into the store queue
    model_pending=model_used+1;
    desired_list=pvr_list_t(h->list);  // stream_select: the list is already open
    const pvr_poly_hdr_t header=handle->model_header;++model_header_hits;
    if(p->cull){
        if(stream_list==PVR_LIST_OP_POLY)RE4DC_PROFILE_COUNT(HardwareCullOP,1);
        else if(stream_list==PVR_LIST_PT_POLY)RE4DC_PROFILE_COUNT(HardwareCullPT,1);
        else RE4DC_PROFILE_COUNT(HardwareCullTR,1);
    }
#if RE4DC_FRONT_NATIVE>=2
    re4dc_front_header_built(&header,p->alpha_state);
#endif
    std::uint32_t count;re4dc::render::begin_pvr_packet(model_packets+model_used,count,header);
    RE4DC_GAD_HIT(handle->key);RE4DC_PART_DUMP_KEY(handle->key);
    RE4DC_GCA_MODEL_PREPARE(nullptr);model_pending=model_used+count;model_handle=handle;
    if(h->scale_rebuild)DFA26_COUNT(model_scale_rebuilds,PacketUvScale);
    if(p->alpha_state&256)++model_alpha_vertex;else ++model_alpha_material;
    if(!(p->alpha_state&256) && (p->alpha_state&255)<255)++model_alpha_faded;
    if(model_parts<6)re4dc_log("native model DIAGNOSTIC source=%08x info=%08x part=%08x positions=%u stride=%u stream=%u flags=%08x material=%02x cull=%u\n",(unsigned)p->model,(unsigned)p->info,(unsigned)p->part,p->position_count,p->position_stride,p->stream_bytes,p->flags,p->material_flags,p->cull);
    RE4DC_GCA_MODEL_PREPARE(p);
    const auto* words=reinterpret_cast<const std::uint32_t*>(model_packets+model_used);
    for(unsigned i=0;i<8;++i)sq[i]=words[i];
#if RE4DC_TA_HASH
    re4dc_ta_hash(words,32);
#endif
    sq_flush(sq);
    model_handle->frame=frame;
    ++frame_pvr_calls;frame_pvr_bytes+=32;stream_model_bytes+=32;
    return sq+8;
}
#endif
#if RE4DC_ACTOR_TRANSACTION
// One immutable, non-paletted reviewed atlas. The lease pins the real upload,
// not a descriptor pointer. Source frame/room/primitive ownership is additional.
extern "C" int re4dc_actor_texture_acquire(const Re4dcUiImage* image,unsigned crc,unsigned fnv,Re4dcActorTextureLease* out){
    if(!image || !out || out->slot || out->serial || !frame_ready || stream_aborted || direct_open || !actor_texture_leases.available())return 0;
    const Key key{crc,fnv};Entry* e=load(*image,false,&key);
    if(!e || !e->valid || !(e->key==key) || !e->package.upload_complete() || e->package.header().texture_count!=1 || !e->package.pvr_texture(0))return 0;
    const auto& t=e->package.textures()[0];
    if(t.width!=image->width || t.height!=image->height || t.format>re4dc::texture::kArgb4444)return 0;
#if RE4DC_ACTOR_TEX_PREP && RE4DC_ACTOR_TEX_PREP_DIAG
    if(!actor_texture_leases.acquire(unsigned(e-entries),frame,*out))return 0;
    actor_tex_prep_bound(key);return 1;
#else
    return actor_texture_leases.acquire(unsigned(e-entries),frame,*out)?1:0;
#endif
}
#if RE4DC_ACTOR_EARLY_COARSE
extern "C" int re4dc_actor_texture_acquire_next(const Re4dcUiImage* image,unsigned crc,unsigned fnv,Re4dcActorTextureLease* out){
    if(frame==~0u || !image || !out || out->slot || out->serial || !frame_ready || stream_aborted || direct_open || !actor_texture_leases.available())return 0;
    const Key key{crc,fnv};Entry* e=load(*image,false,&key);
    if(!e || !e->valid || !(e->key==key) || !e->package.upload_complete() || e->package.header().texture_count!=1 || !e->package.pvr_texture(0))return 0;
    const auto& t=e->package.textures()[0];
    if(t.width!=image->width || t.height!=image->height || t.format>re4dc::texture::kArgb4444)return 0;
    return actor_texture_leases.acquire(unsigned(e-entries),frame+1,*out)?1:0;
}
extern "C" int re4dc_actor_texture_validate_key(const Re4dcActorTextureLease* lease,unsigned crc,unsigned fnv){
    unsigned index;
    return lease && frame_ready && !stream_aborted && !direct_open &&
        actor_texture_leases.resolve(*lease,frame,index) && entries[index].valid &&
        entries[index].key==Key{crc,fnv} && entries[index].package.upload_complete() && entries[index].package.pvr_texture(0);
}
#endif
extern "C" int re4dc_actor_texture_validate(const Re4dcActorTextureLease* lease){
    unsigned index;
    return lease && frame_ready && !stream_aborted && !direct_open &&
        actor_texture_leases.resolve(*lease,frame,index) && entries[index].valid && entries[index].package.upload_complete() && entries[index].package.pvr_texture(0);
}
extern "C" int re4dc_actor_texture_commit(const Re4dcActorTextureLease* lease){
    // Call before the first TA header. From this point even a released ticket
    // leaves the ordinary submitted-scene pin intact until normal retirement.
    if(!re4dc_actor_texture_validate(lease))return 0;
    unsigned index;if(!actor_texture_leases.resolve(*lease,frame,index))return 0;
    entries[index].frame=frame;return 1;
}
extern "C" void re4dc_actor_texture_release(Re4dcActorTextureLease* lease){
    if(lease)actor_texture_leases.release(*lease);
}
extern "C" void re4dc_actor_texture_retire_all(){
    actor_texture_leases.retire_frame(); // never clears submitted Entry::frame pins
}
#include "include/native_ui_actor_material.inc"
#if RE4DC_ACTOR_TRANSACTION_DIAG
extern "C" void re4dc_actor_vis_stream(re4dc_visdiag::Stream* out){
    *out={frame,avd_queue_epoch,deferred_count,unsigned(stream_list),
#if RE4DC_PS2_WORLD_DRAW
        stream_closed_lists,
#else
        0,
#endif
        unsigned(frame_ready)|(unsigned(stream_aborted)<<1)|(unsigned(stream_scene)<<2)|
        (unsigned(source_draws_finished)<<3)|(unsigned(draining_parts)<<4)|(unsigned(direct_open)<<5),
        uintptr_t(deferred_first),uintptr_t(deferred_last)};
}
#endif
extern "C" int re4dc_actor_stream_state(Re4dcActorStreamState* out){
    if(!out || !frame_ready || stream_aborted)return 0;
    *out={frame,model_invalid,model_resource,model_overflow};return 1;
}
#endif
#if RE4DC_COARSE_LEON && !RE4DC_COARSE
// ACTOR_SWAP (version A benchmark, COARSE=0): the reduced-mesh adapters' texture check.
extern "C" int re4dc_coarse_leon_texture_ready(const Re4dcUiImage* image,unsigned crc,unsigned fnv){
    if(!frame_ready || stream_aborted || direct_open)return 0;
    const Key key{crc,fnv};return load(*image,false,&key)!=nullptr;
}
#endif
#if RE4DC_COARSE
#if !RE4DC_TA_DIRECT || !RE4DC_PVR_STREAM || !RE4DC_D349_RENDERER_STACK
#error COARSE extends the TA_DIRECT PVR_STREAM=1 D349 frame owner
#endif
// COARSE (coarse.cpp): the coarse square's opaque view. One untextured Gouraud header (depth
// GEQUAL with write, no culling, the fog table when asked) goes out by store queue; the caller
// writes its vertices from the returned address (8 words each, EOL ends a strip) and closes with
// their count. nullptr: no frame to draw into.
#if RE4DC_COARSE_LEON
extern "C" int re4dc_coarse_leon_texture_ready(const Re4dcUiImage* image,unsigned crc,unsigned fnv){
    if(!frame_ready || stream_aborted || direct_open)return 0;
    const Key key{crc,fnv};return load(*image,false,&key)!=nullptr;
}
#endif
extern "C" std::uint32_t* re4dc_coarse_begin(int fog){
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    sob33_barrier(re4dc::sob33::ForeignDirect);
#endif
#if RE4DC_COARSE >= 2
    static unsigned dbg;
    if(dbg<4 || dbg%600==0)re4dc_log("COARSE2 begin n=%u frame=%u ready=%d scene=%d list=%d desired=%d aborted=%d direct=%d finished=%d\n",
        dbg,frame,(int)frame_ready,(int)stream_scene,(int)stream_list,(int)desired_list,(int)stream_aborted,(int)direct_open,(int)source_draws_finished);
    ++dbg;
#endif
    if(!frame_ready || stream_aborted || direct_open)return nullptr;
#if RE4DC_UI_POLY_ORDER && RE4DC_SS_UI_ORDER
    if(ui_order && quads_flushed<nquad)ui_order_flush();
    if(stream_aborted)return nullptr;
#endif
    static pvr_poly_hdr_t header[2];static bool built[2];
    const unsigned f=fog?1:0;
    if(!built[f]){
        pvr_poly_cxt_t c;pvr_poly_cxt_col(&c,PVR_LIST_OP_POLY);
        c.gen.culling=PVR_CULLING_NONE;c.depth.comparison=PVR_DEPTHCMP_GEQUAL;c.depth.write=PVR_DEPTHWRITE_ENABLE;
#if RE4DC_NATIVE_FOG
        c.gen.fog_type=f?PVR_FOG_TABLE:PVR_FOG_DISABLE;
#endif
        pvr_poly_compile(&header[f],&c);built[f]=true;
    }
    stream_select(PVR_LIST_OP_POLY);
    auto* sq=static_cast<std::uint32_t*>(static_cast<void*>(sq_lock((void*)PVR_TA_INPUT)));
#if RE4DC_UI_POLY_ORDER
    pvr_poly_hdr_t local_header=header[f];ui_order_polygon_header(local_header);
    const auto* h=reinterpret_cast<const std::uint32_t*>(&local_header);
#else
    const auto* h=reinterpret_cast<const std::uint32_t*>(&header[f]);
#endif
    for(unsigned i=0;i<8;++i)sq[i]=h[i];
#if RE4DC_TA_HASH
    re4dc_ta_hash(h,32);
#endif
    sq_flush(sq);
    direct_open=true;
    ++frame_pvr_calls;frame_pvr_bytes+=32;stream_model_bytes+=32;
    return sq+8;
}
#if RE4DC_COARSE_WORLD
// COARSE_WORLD (coarse_world.cpp, lane wd test): as re4dc_coarse_begin, with a prepared package texture
// bound by key and pinned for this frame; the vertices carry their UVs (texture x vertex colour).
// mode: 1 fog table, 2 repeat UVs (tiled materials; else clamped), 4 offset colour (vertex word 7 is
// added: the sky's fade into the fog colour), 8 / 16 PVR back-face cull of positive / negative screen
// area, 32 16-bit UVs (vertex word 4), 64 no depth write (bit 32 builds: R7's sky dome). nullptr: no frame, or
// the package cannot be loaded.
extern "C" std::uint32_t* re4dc_coarse_begin_mode(unsigned crc,unsigned fnv,unsigned width,unsigned height,unsigned mode){
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    sob33_barrier(re4dc::sob33::ForeignDirect);
#endif
    if(!frame_ready || stream_aborted || direct_open)return nullptr;
#if RE4DC_UI_POLY_ORDER && RE4DC_SS_UI_ORDER
    if(ui_order && quads_flushed<nquad)ui_order_flush();
    if(stream_aborted)return nullptr;
#endif
    const Key key{crc,fnv};
    const Re4dcUiImage image{&key,nullptr,width,height,5,0,0}; // size checks only: pixels are never read
    Entry* handle=load(image,false,&key);if(!handle){++model_texture_rejects;return nullptr;}
    handle->frame=frame; // the header goes to the TA now: pinned for this scene
    const auto& t=handle->package.textures()[0];
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,PVR_LIST_OP_POLY,re4dc::texture::pvr_format(t),RE4DC_TSP_W(t),RE4DC_TSP_H(t),handle->package.pvr_texture(0),PVR_FILTER_BILINEAR);
    c.gen.culling=PVR_CULLING_NONE;c.depth.comparison=PVR_DEPTHCMP_GEQUAL;c.depth.write=PVR_DEPTHWRITE_ENABLE;
    c.txr.env=PVR_TXRENV_MODULATE;c.txr.uv_clamp=(mode&2)?PVR_UVCLAMP_NONE:PVR_UVCLAMP_UV;
    if(mode&4)c.gen.specular=PVR_SPECULAR_ENABLE;
    if(mode&8)c.gen.culling=PVR_CULLING_CW;        // rejects positive screen area (pvr_geometry.hpp convention)
    if(mode&16)c.gen.culling=PVR_CULLING_CCW;      // rejects negative screen area
    if(mode&32)c.fmt.uv=PVR_UVFMT_16BIT;           // vertex word 4 = PVR_PACK_16BIT_UV
#if RE4DC_COARSE_WORLD & 32
    if(mode&64)c.depth.write=PVR_DEPTHWRITE_DISABLE; // 64: no depth write (R7: the sky dome behind the backdrop segments)
#endif
#if RE4DC_NATIVE_FOG
    c.gen.fog_type=(mode&1)?PVR_FOG_TABLE:PVR_FOG_DISABLE;
#endif
    pvr_poly_hdr_t header;pvr_poly_compile(&header,&c);DFA26_COUNT(model_header_builds,PacketHeaderBuild);
    stream_select(PVR_LIST_OP_POLY);
    auto* sq=static_cast<std::uint32_t*>(static_cast<void*>(sq_lock((void*)PVR_TA_INPUT)));
#if RE4DC_UI_POLY_ORDER
    ui_order_polygon_header(header);
#endif
    const auto* h=reinterpret_cast<const std::uint32_t*>(&header);
    for(unsigned i=0;i<8;++i)sq[i]=h[i];
#if RE4DC_TA_HASH
    re4dc_ta_hash(h,32);
#endif
    sq_flush(sq);
    direct_open=true;
    ++frame_pvr_calls;frame_pvr_bytes+=32;stream_model_bytes+=32;
    return sq+8;
}
#endif
extern "C" void re4dc_coarse_end(unsigned vertices){
    if(!direct_open)return;
    sq_unlock();direct_open=false;
    if(vertices>32767)re4dc_missing("coarse view exceeded the store-queue window");
#if RE4DC_TA_GUARD
    guard_account(1,vertices);
#endif
    frame_pvr_bytes+=vertices*32;stream_model_bytes+=vertices*32;
    if(stream_model_bytes>stream_peak_bytes)stream_peak_bytes=stream_model_bytes;
}
#endif
#if RE4DC_TREE_IMPOSTOR
#if !RE4DC_PVR_STREAM || !RE4DC_D349_RENDERER_STACK
#error TREE_IMPOSTOR extends the PVR_STREAM=1 D349 frame owner
#endif
// TREE_IMPOSTOR (native_static.cpp): one punch-through batch per impostor
// atlas; the vertices follow in the returned packet, then
// re4dc_model_packet_commit(). The atlas is bound by its prepared package key
// (/cd/dc/tex/<crc>-<fnv>.re4tex); no source image exists for it.
extern "C" void re4dc_static_flush_impostors();
extern "C" int re4dc_model_pt_begin(unsigned crc,unsigned fnv,unsigned width,unsigned height,int fog,Re4dcModelPacket* out){
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    sob33_barrier(re4dc::sob33::CustomPacket); // no marked source-part begin
#endif
#if RE4DC_TA_MATERIAL_DIAG
    tamat::packet_source=2;
#endif
    if(!frame_ready || stream_aborted || !ensure_model_storage() || model_used+8>kModelPacketBytes/32)return 0;
#if RE4DC_UI_POLY_ORDER && RE4DC_SS_UI_ORDER
    if(ui_order && quads_flushed<nquad)ui_order_flush();
    if(stream_aborted)return 0;
#endif
    const Key key{crc,fnv};
    const Re4dcUiImage image{&key,nullptr,width,height,5,0,0}; // size checks only: pixels are never read
    Entry* handle=load(image,false,&key);if(!handle){++model_texture_rejects;return 0;}
    const auto& t=handle->package.textures()[0];
    stream_select(PVR_LIST_PT_POLY);
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,PVR_LIST_PT_POLY,re4dc::texture::pvr_format(t),RE4DC_TSP_W(t),RE4DC_TSP_H(t),handle->package.pvr_texture(0),PVR_FILTER_BILINEAR);
    c.gen.culling=PVR_CULLING_NONE;c.depth.comparison=PVR_DEPTHCMP_GEQUAL;c.depth.write=PVR_DEPTHWRITE_ENABLE;
    c.blend.src=RE4DC_PT_BLEND_FIX?PVR_BLEND_SRCALPHA:PVR_BLEND_ONE;
    c.blend.dst=RE4DC_PT_BLEND_FIX?PVR_BLEND_INVSRCALPHA:PVR_BLEND_ZERO;
    c.txr.env=PVR_TXRENV_MODULATEALPHA;c.txr.alpha=PVR_TXRALPHA_ENABLE;
    c.txr.uv_clamp=PVR_UVCLAMP_UV;
#if RE4DC_NATIVE_FOG
    c.gen.fog_type=fog?PVR_FOG_TABLE:PVR_FOG_DISABLE;
#else
    (void)fog;
#endif
    pvr_poly_hdr_t header;pvr_poly_compile(&header,&c);DFA26_COUNT(model_header_builds,PacketHeaderBuild);

#if RE4DC_UI_POLY_ORDER
    ui_order_polygon_header(header);
#endif
    std::uint32_t count;re4dc::render::begin_pvr_packet(model_packets+model_used,count,header);
    RE4DC_GAD_HIT(handle->key);RE4DC_PART_DUMP_KEY(handle->key);
    RE4DC_GCA_MODEL_PREPARE(nullptr);model_pending=model_used+count;model_handle=handle;
    out->vertices=model_packets+model_pending;out->capacity=kModelPacketBytes/32-model_pending;
    out->u_scale=1.0f;out->v_scale=1.0f;
    return 1;
}
#endif

#if RE4DC_COPY_LEAN && RE4DC_D349_RENDERER_STACK
namespace {
// re4dc_model_defer_part() below with 'source' as the lighting to snapshot
// (nullptr: none) and the same queue layout and admission. The view diff is
// taken once into stack scratch (it was walked twice: size, then fill) and a
// found lighting record supplies its own light set (no second list scan).
int defer_part(const Re4dcModelPart* p,const SourceLighting* source
#if RE4DC_NATIVE_FE_CONTINUATION
    ,re4dc::NativeDrawResult* result=nullptr
#endif
){
#if RE4DC_NATIVE_FE_CONTINUATION
    if(result)*result={re4dc::NativeDrawOutcome::UnsupportedBeforePublication};
#endif
    if(draining_parts){AVD_EVENT(Direct,nullptr,p,0);return 0;}
    if(source_draws_finished){AVD_EVENT(Direct,nullptr,p,1);RE4DC_PROFILE_COUNT(DirectTR,1);return 0;}
    if(select_model_pass(p)==PVR_LIST_OP_POLY){AVD_EVENT(Direct,nullptr,p,2);RE4DC_PROFILE_COUNT(DirectOP,1);return 0;}
    RE4DC_PROFILE_SCOPE(TranslucentEnqueue);
    if(!frame_ready || stream_aborted) {
#if RE4DC_NATIVE_FE_CONTINUATION
        if(result){*result={re4dc::NativeDrawOutcome::Refused};re4dc_model_result(2,0,0);}
#endif
        return 1;
    }
    DeferredLighting* lighting=nullptr;
    if(source)for(auto* l=deferred_lights;l;l=l->next)
        if(same_lighting(l,*source)){lighting=l;break;}
    DeferredLightSet* light_set=lighting?const_cast<DeferredLightSet*>(lighting->lights):nullptr;
    if(source && !lighting)for(auto* l=deferred_light_sets;l;l=l->next)
        if(same_light_set(l,*source)){light_set=l;break;}
    const unsigned set_bytes=source && !light_set?(deferred_set_bytes(*source)+31)&~31U:0;
    const unsigned state_bytes=source && !lighting?(deferred_light_bytes(*source)+31)&~31U:0;
    Re4dcModelPart view=*p;view.lighting=nullptr; // separately snapshotted below
    const bool had_basis=deferred_basis!=nullptr;
    unsigned masks[kViewMasks],values[kViewWords];
    const unsigned basis_bytes=had_basis?0:(sizeof(Re4dcModelPart)+31)&~31U;
    const unsigned words=had_basis?view_words(view,*deferred_basis,masks,values):0;
    const unsigned bytes=(sizeof(DeferredPart)+4*words+31)&~31U;
    const unsigned required=bytes+state_bytes+basis_bytes+set_bytes;
    RE4DC_PROFILE_COUNT(ViewBytes,bytes);RE4DC_PROFILE_COUNT(LightSetBytes,set_bytes);
    RE4DC_PROFILE_COUNT(LightStateBytes,state_bytes);RE4DC_PROFILE_COUNT(BasisBytes,basis_bytes);
    if(p->material_flags&4){RE4DC_PROFILE_COUNT(DeferredMasked,1);RE4DC_PROFILE_COUNT(MaskedBytes,required);}
    else if(p->depth_mode){RE4DC_PROFILE_COUNT(DeferredDepth,1);RE4DC_PROFILE_COUNT(DepthBytes,required);}
    else {RE4DC_PROFILE_COUNT(DeferredBlend,1);RE4DC_PROFILE_COUNT(BlendBytes,required);}
    RE4DC_PROFILE_HIGH(QueueCapacity,sizeof(frame_storage)-8192+kModelDeferredSpillBytes);
    unsigned char* storage=frame_storage;unsigned* top=&deferred_top;
    if(required>deferred_top || deferred_top-required<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad)))){
        if(!deferred_spill){deferred_spill=static_cast<unsigned char*>(re4dc_model_deferred_storage(&deferred_spill_capacity));deferred_spill_top=deferred_spill_capacity;}
        if(!deferred_spill || required>deferred_spill_top){
#if RE4DC_NATIVE_FE_CONTINUATION
            if(result)*result={re4dc::NativeDrawOutcome::Refused};
#endif
            RE4DC_WHD_ABORT(1,__builtin_return_address(0),required);
#if RE4DC_WORLD_HOLE_FIX
            // WORLD_HOLE_FIX (worldhole.mk): the queue is full: drop this translucent part only. Nothing of it was
            // queued or sent, so the frame stays whole (aborting it hid the whole frame and refused every later
            // PS2 world PT / TR part: r117 entry, the r119 El Gigante fight).
            ++deferred_drops;++frame_queue_drops;whfix_drop(required);RE4DC_FQ_DROP(false,required);re4dc_model_result(3,0,0);return 1;
#else
            ++deferred_drops;++frame_queue_drops;stream_aborted=true;re4dc_model_result(3,0,0);return 1;
#endif
        }
        storage=deferred_spill;top=&deferred_spill_top; DFA26_HIT(DeferredSpill)
    }
    if(basis_bytes){*top-=basis_bytes;deferred_basis=new(storage+*top) Re4dcModelPart(view);}
    if(set_bytes){
        *top-=set_bytes;light_set=new(storage+*top) DeferredLightSet{};
        store_light_set(light_set,*source);light_set->next=deferred_light_sets;deferred_light_sets=light_set;
    }
    if(state_bytes){
        *top-=state_bytes;lighting=new(storage+*top) DeferredLighting{};
        lighting->lights=light_set;store_lighting(lighting,*source);lighting->next=deferred_lights;deferred_lights=lighting;
    }
    *top-=bytes;
    auto* node=new(storage+*top) DeferredPart{};
    if(had_basis){
        for(unsigned m=0;m<kViewMasks;++m)node->changed[m]=masks[m];
        auto* out=reinterpret_cast<unsigned*>(node+1);
        for(unsigned i=0;i<words;++i)out[i]=values[i];
    } // else: the basis is this view, no differing words (changed[] stays zero)
    node->lighting=lighting;
#if RE4DC_GC_ASSET_GATE
    const auto& proof=re4dc_gcasset::source_use;
    if(proof.model==view.model && proof.info==view.info){node->asset_serial=proof.serial;node->asset_mask=proof.mask;node->asset_payload=proof.payload;}
#endif
    if(deferred_last)deferred_last->next=node;else deferred_first=node;
    deferred_last=node;++deferred_count;
#if RE4DC_NATIVE_FE_CONTINUATION
    if(result)*result={re4dc::NativeDrawOutcome::Queued,0,1};
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    DFA26_HIT(DeferredModel)
#endif
    AVD_EVENT(Enqueue,node,&view,unsigned(uintptr_t(node->lighting)));
    deferred_peak=std::max(deferred_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
    frame_queue_peak=std::max(frame_queue_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
    RE4DC_PROFILE_HIGH(QueuePeak,frame_queue_peak);
    return 1;
}
}
// Lit native scenery (native_static.cpp): the replay never reads lighting.
extern "C" int re4dc_model_defer_part_unlit(const Re4dcModelPart* p){return defer_part(p,nullptr);}
#elif RE4DC_COPY_LEAN
extern "C" int re4dc_model_defer_part_unlit(const Re4dcModelPart*){return 0;}
#endif
#if RE4DC_NATIVE_FE_CONTINUATION
extern "C" int re4dc_model_defer_native_result(const Re4dcModelPart* p,re4dc::NativeDrawResult* result){
    if(!p || !result){if(result)*result={re4dc::NativeDrawOutcome::Refused};return 1;}
    return defer_part(p,p?p->lighting:nullptr,result);
}
#endif
extern "C" int re4dc_model_defer_part(const Re4dcModelPart* p){
#if RE4DC_COPY_LEAN && RE4DC_D349_RENDERER_STACK
    return defer_part(p,p->lighting);
#elif RE4DC_D349_RENDERER_STACK
    if(draining_parts){AVD_EVENT(Direct,nullptr,p,0);return 0;}
    if(source_draws_finished){AVD_EVENT(Direct,nullptr,p,1);RE4DC_PROFILE_COUNT(DirectTR,1);return 0;}
    if(select_model_pass(p)==PVR_LIST_OP_POLY){AVD_EVENT(Direct,nullptr,p,2);RE4DC_PROFILE_COUNT(DirectOP,1);return 0;}
    RE4DC_PROFILE_SCOPE(TranslucentEnqueue);
    if(!frame_ready || stream_aborted)return 1;
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    DFA26_HIT(DeferredSnapshotRepeat)
#endif
    // Full current state snapshot; arrays/display-list remain source-owned.
    // Only nonopaque models borrow this space, typically a small minority.
    DeferredLighting* lighting=nullptr;
    if(p->lighting)for(auto* l=deferred_lights;l;l=l->next)
        if(same_lighting(l,*p->lighting)){lighting=l;break;}
    DeferredLightSet* light_set=nullptr;
    if(p->lighting)for(auto* l=deferred_light_sets;l;l=l->next)
        if(same_light_set(l,*p->lighting)){light_set=l;break;}
    const unsigned set_bytes=p->lighting && !light_set?(deferred_set_bytes(*p->lighting)+31)&~31U:0;
    const unsigned state_bytes=p->lighting && !lighting?(deferred_light_bytes(*p->lighting)+31)&~31U:0;
    Re4dcModelPart view=*p;view.lighting=nullptr; // separately snapshotted below
    const unsigned basis_bytes=deferred_basis?0:(sizeof(Re4dcModelPart)+31)&~31U;
    const unsigned words=deferred_basis?view_words(view,*deferred_basis,nullptr,nullptr):0;
    const unsigned bytes=(sizeof(DeferredPart)+4*words+31)&~31U;
    const unsigned required=bytes+state_bytes+basis_bytes+set_bytes;
    RE4DC_PROFILE_COUNT(ViewBytes,bytes);RE4DC_PROFILE_COUNT(LightSetBytes,set_bytes);
    RE4DC_PROFILE_COUNT(LightStateBytes,state_bytes);RE4DC_PROFILE_COUNT(BasisBytes,basis_bytes);
    if(p->material_flags&4){RE4DC_PROFILE_COUNT(DeferredMasked,1);RE4DC_PROFILE_COUNT(MaskedBytes,required);}
    else if(p->depth_mode){RE4DC_PROFILE_COUNT(DeferredDepth,1);RE4DC_PROFILE_COUNT(DepthBytes,required);}
    else {RE4DC_PROFILE_COUNT(DeferredBlend,1);RE4DC_PROFILE_COUNT(BlendBytes,required);}
    RE4DC_PROFILE_HIGH(QueueCapacity,sizeof(frame_storage)-8192+kModelDeferredSpillBytes);
    unsigned char* storage=frame_storage;unsigned* top=&deferred_top;
    // Source UI arrives after model registration. Preserve a measured 8 KiB
    // lane for it and spill snapshots into the former native static-cache tail.
    // This never grows the source arena, native slab or total allocated memory.
    if(required>deferred_top || deferred_top-required<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad)))){
        if(!deferred_spill){deferred_spill=static_cast<unsigned char*>(re4dc_model_deferred_storage(&deferred_spill_capacity));deferred_spill_top=deferred_spill_capacity;}
        if(!deferred_spill || required>deferred_spill_top){
            RE4DC_WHD_ABORT(1,__builtin_return_address(0),required);
#if RE4DC_WORLD_HOLE_FIX
            // WORLD_HOLE_FIX (worldhole.mk): the queue is full: drop this translucent part only. Nothing of it was
            // queued or sent, so the frame stays whole (aborting it hid the whole frame and refused every later
            // PS2 world PT / TR part: r117 entry, the r119 El Gigante fight).
            ++deferred_drops;++frame_queue_drops;whfix_drop(required);RE4DC_FQ_DROP(false,required);re4dc_model_result(3,0,0);return 1;
#else
            ++deferred_drops;++frame_queue_drops;stream_aborted=true;re4dc_model_result(3,0,0);return 1;
#endif
        }
        storage=deferred_spill;top=&deferred_spill_top; DFA26_HIT(DeferredSpill)
    }
    if(basis_bytes){*top-=basis_bytes;deferred_basis=new(storage+*top) Re4dcModelPart(view);}
    if(set_bytes){
        *top-=set_bytes;light_set=new(storage+*top) DeferredLightSet{};
        store_light_set(light_set,*p->lighting);light_set->next=deferred_light_sets;deferred_light_sets=light_set;
    }
    if(state_bytes){
        *top-=state_bytes;lighting=new(storage+*top) DeferredLighting{};
        lighting->lights=light_set;store_lighting(lighting,*p->lighting);lighting->next=deferred_lights;deferred_lights=lighting;
    }
    *top-=bytes;
    auto* node=new(storage+*top) DeferredPart{};
    view_words(view,*deferred_basis,node->changed,reinterpret_cast<unsigned*>(node+1));
    node->lighting=lighting;
#if RE4DC_GC_ASSET_GATE
    const auto& proof=re4dc_gcasset::source_use;
    if(proof.model==view.model && proof.info==view.info){node->asset_serial=proof.serial;node->asset_mask=proof.mask;node->asset_payload=proof.payload;}
#endif
    if(deferred_last)deferred_last->next=node;else deferred_first=node;
    deferred_last=node;++deferred_count;
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    DFA26_HIT(DeferredModel)
#endif
    AVD_EVENT(Enqueue,node,&view,unsigned(uintptr_t(node->lighting)));
    deferred_peak=std::max(deferred_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
    frame_queue_peak=std::max(frame_queue_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
    RE4DC_PROFILE_HIGH(QueuePeak,frame_queue_peak);
    return 1;
#else
    (void)p;return 0;
#endif
}
#if RE4DC_ACTOR_GANADO_DEATH_FADE
#include "include/native_ui_actor_fade.inc"
#endif
#if RE4DC_EFFECT_SPRITES
#if !RE4DC_D349_RENDERER_STACK || !RE4DC_PVR_STREAM
#error EFFECT_SPRITES needs the D349 renderer stack and PVR_STREAM (deferred translucent queue)
#endif
#ifndef RE4DC_EFFECT_SPRITE_MAX
#define RE4DC_EFFECT_SPRITE_MAX 64
#endif
#include <dc/pvr/pvr_misc.h>
namespace {
// A queued sprite: a DeferredPart whose lighting is this tag, then its 96-byte packet
// (header + textured sprite body). The drain sends it in OT order between model parts.
DeferredLighting* const kSpriteTag=reinterpret_cast<DeferredLighting*>(1);
constexpr unsigned kSpriteNode=(sizeof(DeferredPart)+31)&~31U,kSpritePacket=sizeof(pvr_poly_hdr_t)+sizeof(pvr_sprite_txr_t);
#if defined(RE4DC_ESP_SETUP_BATCH)
// Guard admission and packet diagnostics retain their original full packets.
// A body-only node reserves the same bytes, so queue pressure admits the same
// sprites. Its unused header line is neither written nor read.
DeferredLighting* const kSpriteBodyTag=reinterpret_cast<DeferredLighting*>(9);
#endif
#if defined(RE4DC_NATIVE_LASER) && RE4DC_NATIVE_LASER
DeferredLighting* const kLineTag=reinterpret_cast<DeferredLighting*>(3);
constexpr unsigned kLinePacket=sizeof(pvr_poly_hdr_t)+4*sizeof(pvr_vertex_t);
#if RE4DC_NATIVE_FOG
extern "C" unsigned re4dc_fog_enabled();
#endif
#endif
#if defined(RE4DC_ESP_SPRITE_FAST) && RE4DC_ESP_SPRITE_FAST
// ESP_SPRITE_FAST: the compiled header is a pure function of the texture (format, size, VRAM address) and the
// sprite's blend and screen flag; consecutive sprites mostly share them, so the last one is kept.
#if defined(RE4DC_ESP_SETUP_BATCH)
struct FxHeaderKey{unsigned fmt,w,h;const void* txr;unsigned char src,dst,screen;
    const DeferredPart* owner;unsigned color;
};
alignas(32)
#else
struct FxHeaderKey{unsigned fmt,w,h;const void* txr;unsigned char src,dst,screen;};
#endif
FxHeaderKey fx_hdr_key{~0U,0,0,nullptr,0,0,0};
alignas(32) pvr_poly_hdr_t fx_hdr_cache;
#if defined(RE4DC_ESP_SETUP_BATCH)
void fx_setup_forget(){fx_hdr_key.owner=nullptr;}
#endif
#endif
#if RE4DC_GC_ASSET_GATE
void gcasset_fx_stream_send(const void* packet,unsigned bytes){
    const auto previous=gcasset_packet_consumer;
    gcasset_packet_consumer=re4dc_gcasset::EffectPicture;
    stream_send(packet,bytes);
    gcasset_packet_consumer=previous;
}
#else
#define gcasset_fx_stream_send stream_send
#endif
#if defined(RE4DC_ESP_SETUP_BATCH)
void fx_send(unsigned char* packet,bool screen,bool body_only=false){
#else
void fx_send(unsigned char* packet,bool screen){
#endif
#if RE4DC_TA_MATERIAL_DIAG
    tamat::Scope source_scope(4);
#endif
#if RE4DC_WORLD_AUTOSORT
    if(world_autosort && screen){
        auto* b=reinterpret_cast<pvr_sprite_txr_t*>(packet+sizeof(pvr_poly_hdr_t));
        b->az=b->bz=b->cz=overlay_depth();
    }
#else
    (void)screen;
#endif
#if defined(RE4DC_ESP_SETUP_BATCH)
    if(body_only)gcasset_fx_stream_send(packet+sizeof(pvr_poly_hdr_t),sizeof(pvr_sprite_txr_t));
    else gcasset_fx_stream_send(packet,kSpritePacket);
#else
    gcasset_fx_stream_send(packet,kSpritePacket);
#endif
}
#if defined(RE4DC_EFFECT_HAZE_LEAN) && (RE4DC_EFFECT_HAZE_LEAN & 4)
// EFFECT_HAZE_LEAN bit 4 (STUDY2 M2): a PS2 haze sprite (esp_sub.cpp sets pad 1) as a regular octagon inscribed in
// its square (apothem 0.9 of the half side: 67 % of the pixels), one textured strip of 8 vertices with the sprite's
// texture, blend, depth and fog. The soft blob's corners are near 0, so the look barely changes.
DeferredLighting* const kOctTag=reinterpret_cast<DeferredLighting*>(7); // unique: see kGradeTag
constexpr unsigned kOctPacket=sizeof(pvr_poly_hdr_t)+8*sizeof(pvr_vertex_t);
void oct_packet(const Re4dcEffectSprite& s,Entry* e,unsigned char* out){
    const auto& t=e->package.textures()[0];
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,PVR_LIST_TR_POLY,re4dc::texture::pvr_format(t),RE4DC_TSP_W(t),RE4DC_TSP_H(t),
                                      const_cast<void*>(e->package.pvr_texture(0)),PVR_FILTER_BILINEAR);
    c.gen.culling=PVR_CULLING_NONE;
    c.depth.comparison=PVR_DEPTHCMP_GEQUAL;c.depth.write=PVR_DEPTHWRITE_DISABLE;
    c.blend.src=(pvr_blend_mode_t)s.src;c.blend.dst=(pvr_blend_mode_t)s.dst;
    c.txr.env=PVR_TXRENV_MODULATEALPHA;c.txr.uv_clamp=PVR_UVCLAMP_UV;
#if RE4DC_NATIVE_FOG
    c.gen.fog_type=PVR_FOG_TABLE;
#endif
    pvr_poly_compile(reinterpret_cast<pvr_poly_hdr_t*>(out),&c);
    // Local (p, q) of the corners A(0,1) B(1,1) C(1,0) D(0,0): point = D + p (C - D) + q (A - D); strip order
    // 0 1 7 2 6 3 5 4 over the octagon's vertices at 22.5 + 45 k degrees, radius 0.45 / cos 22.5.
    static const float kp[8]={0.95f,0.68637f,0.31363f,0.05f,0.05f,0.31363f,0.68637f,0.95f};
    static const float kq[8]={0.68637f,0.95f,0.95f,0.68637f,0.31363f,0.05f,0.05f,0.31363f};
    static const unsigned char order[8]={0,1,7,2,6,3,5,4};
#if defined(RE4DC_G1_FP_UNSIGNED) && RE4DC_G1_FP_UNSIGNED
    // G1_FP_UNSIGNED: picture and texture sizes are < 2^31 (a loaded texture), so the signed conversion is the same float.
    const float su=float(int(RE4DC_COVER_W(e->package,s.image.width)))/float(int(t.width)),
                sv=float(int(RE4DC_COVER_H(e->package,s.image.height)))/float(int(t.height));
#else
    const float su=float(RE4DC_COVER_W(e->package,s.image.width))/t.width,sv=float(RE4DC_COVER_H(e->package,s.image.height))/t.height;
#endif
    auto* v=reinterpret_cast<pvr_vertex_t*>(out+sizeof(pvr_poly_hdr_t));
    for(unsigned i=0;i<8;++i){
        const unsigned k=order[i];const float p=kp[k],q=kq[k];
        v[i].flags=i==7?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;
        v[i].x=s.x[3]+p*(s.x[2]-s.x[3])+q*(s.x[0]-s.x[3]);
        v[i].y=s.y[3]+p*(s.y[2]-s.y[3])+q*(s.y[0]-s.y[3]);
        v[i].z=s.z[0];
        v[i].u=(s.u[3]+p*(s.u[2]-s.u[3])+q*(s.u[0]-s.u[3]))*su;
        v[i].v=(s.v[3]+p*(s.v[2]-s.v[3])+q*(s.v[0]-s.v[3]))*sv;
        v[i].argb=s.color;v[i].oargb=0;
    }
}
#endif
#if RE4DC_FX_SPRITE_TRIM || RE4DC_FX_SPRITE_TRIM_DIAG
#include "include/fx_sprite_trim.inc"   // fxtrim.mk
#endif
#if defined(RE4DC_ESP_SETUP_BATCH)
bool fx_packet(const Re4dcEffectSprite& s,Entry* e,unsigned char* out,
               const DeferredPart* previous=nullptr){
#else
void fx_packet(const Re4dcEffectSprite& s,Entry* e,unsigned char* out){
#endif
    const auto& t=e->package.textures()[0];
    auto* h=reinterpret_cast<pvr_poly_hdr_t*>(out);
#if defined(RE4DC_ESP_SPRITE_FAST) && RE4DC_ESP_SPRITE_FAST
    const unsigned fmt=re4dc::texture::pvr_format(t);const void* txr=e->package.pvr_texture(0);
#if defined(RE4DC_ESP_SETUP_BATCH)
    const bool same=fx_hdr_key.fmt==fmt && fx_hdr_key.w==t.width && fx_hdr_key.h==t.height && fx_hdr_key.txr==txr &&
        fx_hdr_key.src==s.src && fx_hdr_key.dst==s.dst && fx_hdr_key.screen==s.screen;
    // A queued call passes its predecessor, or its own fresh node for a head.
    // Other callers (including RTT capture) pass null: do not subtract before
    // their standalone output buffer. Four arguments fit the SH-4 call ABI.
    const auto* owner=previous?reinterpret_cast<const DeferredPart*>(out-kSpriteNode):nullptr;
    // Queue allocations never reuse/retag an admitted node before reset, which
    // forgets owner. Provenance alone suffices; do not fetch the preceding node.
    const bool body_only=previous && previous!=owner && fx_hdr_key.owner==previous && same && fx_hdr_key.color==s.color;
    if(!same){
#else
    if(fx_hdr_key.fmt!=fmt || fx_hdr_key.w!=t.width || fx_hdr_key.h!=t.height || fx_hdr_key.txr!=txr ||
       fx_hdr_key.src!=s.src || fx_hdr_key.dst!=s.dst || fx_hdr_key.screen!=s.screen){
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
        DFA26_HIT(EffectHeaderChange)
#endif
        pvr_sprite_cxt_t c;pvr_sprite_cxt_txr(&c,PVR_LIST_TR_POLY,fmt,RE4DC_TSP_W(t),RE4DC_TSP_H(t),
                                              const_cast<void*>(txr),PVR_FILTER_BILINEAR);
        c.gen.culling=PVR_CULLING_NONE;
        c.depth.comparison=s.screen?PVR_DEPTHCMP_ALWAYS:PVR_DEPTHCMP_GEQUAL;c.depth.write=PVR_DEPTHWRITE_DISABLE;
        c.blend.src=(pvr_blend_mode_t)s.src;c.blend.dst=(pvr_blend_mode_t)s.dst;
        c.txr.env=PVR_TXRENV_MODULATEALPHA;c.txr.uv_clamp=PVR_UVCLAMP_UV;
#if RE4DC_NATIVE_FOG
        c.gen.fog_type=s.screen?PVR_FOG_DISABLE:PVR_FOG_TABLE; // table: native_static.cpp re4dc_fog_frame
#endif
        pvr_sprite_compile(&fx_hdr_cache,&c);
        fx_hdr_key=FxHeaderKey{fmt,RE4DC_TSP_W(t),RE4DC_TSP_H(t),txr,(unsigned char)s.src,(unsigned char)s.dst,(unsigned char)s.screen};
    }
#if defined(RE4DC_ESP_SETUP_BATCH)
    if(!body_only){DFA26_HIT(EffectBatchBreak)*h=fx_hdr_cache;h->argb=s.color;h->oargb=0;}
    fx_hdr_key.owner=owner;fx_hdr_key.color=s.color;
#else
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    DFA26_HIT(EffectSetupDisabled)
#endif
    *h=fx_hdr_cache;h->argb=s.color;h->oargb=0;
#endif
#else
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    DFA26_HIT(EffectSetupDisabled)
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    DFA26_HIT(EffectHeaderChange)
#endif
    pvr_sprite_cxt_t c;pvr_sprite_cxt_txr(&c,PVR_LIST_TR_POLY,re4dc::texture::pvr_format(t),RE4DC_TSP_W(t),RE4DC_TSP_H(t),
                                          e->package.pvr_texture(0),PVR_FILTER_BILINEAR);
    c.gen.culling=PVR_CULLING_NONE;
    c.depth.comparison=s.screen?PVR_DEPTHCMP_ALWAYS:PVR_DEPTHCMP_GEQUAL;c.depth.write=PVR_DEPTHWRITE_DISABLE;
    c.blend.src=(pvr_blend_mode_t)s.src;c.blend.dst=(pvr_blend_mode_t)s.dst;
    c.txr.env=PVR_TXRENV_MODULATEALPHA;c.txr.uv_clamp=PVR_UVCLAMP_UV;
#if RE4DC_NATIVE_FOG
    c.gen.fog_type=s.screen?PVR_FOG_DISABLE:PVR_FOG_TABLE; // table: native_static.cpp re4dc_fog_frame
#endif
    pvr_sprite_compile(h,&c);h->argb=s.color;h->oargb=0;
#endif
    auto* b=reinterpret_cast<pvr_sprite_txr_t*>(out+sizeof(pvr_poly_hdr_t));
    const float su=float(RE4DC_COVER_W(e->package,s.image.width))/t.width,sv=float(RE4DC_COVER_H(e->package,s.image.height))/t.height;
    b->flags=PVR_CMD_VERTEX_EOL;
    b->ax=s.x[0];b->ay=s.y[0];b->az=s.z[0];b->bx=s.x[1];b->by=s.y[1];b->bz=s.z[1];
    b->cx=s.x[2];b->cy=s.y[2];b->cz=s.z[2];b->dx=s.x[3];b->dy=s.y[3];b->dummy=0;
    b->auv=PVR_PACK_16BIT_UV(s.u[0]*su,s.v[0]*sv);b->buv=PVR_PACK_16BIT_UV(s.u[1]*su,s.v[1]*sv);
    b->cuv=PVR_PACK_16BIT_UV(s.u[2]*su,s.v[2]*sv);
#if defined(RE4DC_ESP_SETUP_BATCH)
    return body_only;
#endif
}
}
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
extern "C" float re4dc_fog_gate_far() __attribute__((weak)); // ACTOR_FOG_GATE builds (native_static.cpp)
#endif
#if defined(RE4DC_PVR_RTT) && RE4DC_PVR_RTT
#include "include/pvr_rtt.inc"   // pvr_rtt.mk
#endif
// EFFECT_SPRITES (effects30.mk): one effect sprite from EspCommonTrans. Never aborts the
// frame: without texture, over the per-frame cap or without queue room the sprite is dropped.
#if RE4DC_GC_ASSET_GATE
#define stream_send gcasset_fx_stream_send
#endif
extern "C" int re4dc_effect_sprite(const Re4dcEffectSprite* s){
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
    // Legacy sprites count admitted output only: policy/cull/refusal stay 0.
    return re4dc_effect_sprite_result(s).published()?1:0;
#else
#include "native_effect_sprite03.inc"
#endif
}
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
extern "C" re4dc::NativeDrawResult re4dc_effect_sprite_result(const Re4dcEffectSprite* s){
    // The existing entry guard refuses a stopped stream before RTT selection.
    // A terminal frame cannot authorize whole-producer fallback, even at zero output.
    if(stream_aborted)return {re4dc::NativeDrawOutcome::PartialAbort};
#include "native_effect_sprite03.inc"
}
#endif
#if defined(RE4DC_PS2_FX_COMMON_HAZE) && RE4DC_PS2_FX_COMMON_HAZE
#include "include/native_effect_haze_batch.inc"
#endif
#if defined(RE4DC_PS2_FX_ADDITIONS) && RE4DC_PS2_FX_ADDITIONS
#include "include/native_effect_stage1_batch.inc"
#endif
#if defined(RE4DC_FX_STRIP21) && RE4DC_FX_STRIP21
#include "include/native_effect_strip21.inc"
#endif
#if defined(RE4DC_FLASHLIGHT_POOL) && RE4DC_FLASHLIGHT_POOL
#include "include/native_flashlight_pool.inc"
#endif
#if RE4DC_GC_ASSET_GATE
#undef stream_send
#endif
#if defined(RE4DC_NATIVE_LASER) && RE4DC_NATIVE_LASER
// Esp19's source line becomes one untextured, colour-interpolated strip in
// the same bounded OT queue as effect sprites. All packet bytes are copied
// before returning; no source pointer, texture, heap or frame owner is added.
extern "C" int re4dc_effect_line(const Re4dcEffectLine* s){
    if(!s || !frame_ready || stream_aborted || draining_parts)return 0;
    if(s->blend_mode>1){++unsupported;return 0;}
#if RE4DC_RES_MODES
    Re4dcEffectLine scaled;      // projected to 640x480 by its owner: the current render size (no copy at 640x480)
    if(re4dc_ui_sy!=1.0f || re4dc_ui_sx!=1.0f){scaled=*s;for(unsigned i=0;i<2;++i){scaled.x[i]*=re4dc_ui_sx;scaled.y[i]*=re4dc_ui_sy;}s=&scaled;}
#endif
    for(unsigned i=0;i<2;++i)
        if(!re4dc::render::is_finite(s->x[i]) || !re4dc::render::is_finite(s->y[i]) ||
           !re4dc::render::is_finite(s->z[i]) || s->z[i]<=0.0f)return 0;
    const float dx=s->x[1]-s->x[0],dy=s->y[1]-s->y[0];
    const float length=std::sqrt(dx*dx+dy*dy);
    if(!re4dc::render::is_finite(length) || length<.0001f)return 0;
    const float ox=-dy*(.5f/length),oy=dx*(.5f/length);
    alignas(32) unsigned char packet[kLinePacket]{};
    pvr_poly_cxt_t c;pvr_poly_cxt_col(&c,PVR_LIST_TR_POLY);
    c.gen.culling=PVR_CULLING_NONE;c.gen.shading=PVR_SHADE_GOURAUD;
    c.depth.comparison=s->depth_test?PVR_DEPTHCMP_GEQUAL:PVR_DEPTHCMP_ALWAYS;
    c.depth.write=PVR_DEPTHWRITE_ENABLE; // source GXSetZMode's update flag is 1
    c.blend.src=s->blend_mode?(pvr_blend_mode_t)s->src:PVR_BLEND_ONE;
    c.blend.dst=s->blend_mode?(pvr_blend_mode_t)s->dst:PVR_BLEND_ZERO;
#if RE4DC_NATIVE_FOG
    c.gen.fog_type=re4dc_fog_enabled()?PVR_FOG_TABLE:PVR_FOG_DISABLE;
#endif
    pvr_poly_compile(reinterpret_cast<pvr_poly_hdr_t*>(packet),&c);
    auto* v=reinterpret_cast<pvr_vertex_t*>(packet+sizeof(pvr_poly_hdr_t));
    for(unsigned i=0;i<4;++i){
        const unsigned end=i/2;const float side=i&1?-1.0f:1.0f;
        v[i]={PVR_CMD_VERTEX,s->x[end]+side*ox,s->y[end]+side*oy,s->z[end],0,0,s->color[end],0};
    }
    v[3].flags=PVR_CMD_VERTEX_EOL;
    if(source_draws_finished){
        AVD_EVENT(Direct,nullptr,nullptr,3);
        stream_select(PVR_LIST_TR_POLY);stream_send(packet,kLinePacket);++fx_direct;return 1;
    }
    const unsigned required=kSpriteNode+kLinePacket,margin=RE4DC_FX_QUEUE_MARGIN;
    unsigned char* storage=frame_storage;unsigned* top=&deferred_top;
    if(required+margin>deferred_top || deferred_top-required-margin<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad)))){
        if(!deferred_spill){deferred_spill=static_cast<unsigned char*>(re4dc_model_deferred_storage(&deferred_spill_capacity));deferred_spill_top=deferred_spill_capacity;}
#if defined(RE4DC_FX_R200_ENTRY_CAP) && RE4DC_FX_R200_ENTRY_CAP
        if(!deferred_spill || required>deferred_spill_top){
            if(!fx_r200_tail_select(required,storage,top)){++fx_dropped;RE4DC_FQ_DROP(true,required);return 0;}
        }else{storage=deferred_spill;top=&deferred_spill_top; DFA26_HIT(DeferredSpill)}
#else
        if(!deferred_spill || required>deferred_spill_top){++fx_dropped;RE4DC_FQ_DROP(true,required);return 0;}
        storage=deferred_spill;top=&deferred_spill_top; DFA26_HIT(DeferredSpill)
#endif
    }
    *top-=required;auto* node=new(storage+*top) DeferredPart{};node->lighting=kLineTag;
    std::memcpy(storage+*top+kSpriteNode,packet,kLinePacket);
    if(deferred_last)deferred_last->next=node;else deferred_first=node;
    deferred_last=node;++deferred_count;
    AVD_EVENT(Enqueue,node,nullptr,unsigned(uintptr_t(node->lighting)));
    ++fx_queued;
    frame_queue_peak=std::max(frame_queue_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
    return 1;
}
#endif
#if defined(RE4DC_RAIN_DC) && RE4DC_RAIN_DC
// RAIN_DC (effects30.mk, filter06.cpp): the Dreamcast rain streaks. One untextured gouraud TR header, then one
// 4-vertex strip per streak, straight into the open TR list; only once the source draws finished (gx_stub.cpp
// GXSetDrawSync 0xADEB), else nothing. Depth tested (GEQUAL on 1/w), no depth write, alpha blended, fog table as
// the scene. No texture, no frame storage. Returns the streaks sent.
extern "C" unsigned re4dc_rain_dc_streaks(const Re4dcRainStreak* s,unsigned n){
    if(!s || !n || !frame_ready || stream_aborted || draining_parts || !source_draws_finished)return 0;
    alignas(32) pvr_poly_hdr_t hdr;
    pvr_poly_cxt_t c;pvr_poly_cxt_col(&c,PVR_LIST_TR_POLY);
    c.gen.culling=PVR_CULLING_NONE;c.gen.shading=PVR_SHADE_GOURAUD;
    c.depth.comparison=PVR_DEPTHCMP_GEQUAL;c.depth.write=PVR_DEPTHWRITE_DISABLE;
    c.blend.src=PVR_BLEND_SRCALPHA;c.blend.dst=PVR_BLEND_INVSRCALPHA;
#if RE4DC_NATIVE_FOG
    c.gen.fog_type=re4dc_fog_enabled()?PVR_FOG_TABLE:PVR_FOG_DISABLE;
#endif
    pvr_poly_compile(&hdr,&c);
    stream_select(PVR_LIST_TR_POLY);stream_send(&hdr,sizeof hdr);
    float sx=1.0f,sy=1.0f;
#if RE4DC_RES_MODES
    sx=re4dc_ui_sx;sy=re4dc_ui_sy;
#endif
    alignas(32) pvr_vertex_t v[32];unsigned k=0;
    for(unsigned i=0;i<n;++i){
        const Re4dcRainStreak& r=s[i];
        const float hw=r.w*0.5f*sx,x=r.x*sx,y0=r.y0*sy,y1=r.y1*sy;
        v[k++]={PVR_CMD_VERTEX,x-hw,y0,r.z,0,0,r.tail,0};
        v[k++]={PVR_CMD_VERTEX,x+hw,y0,r.z,0,0,r.tail,0};
        v[k++]={PVR_CMD_VERTEX,x-hw,y1,r.z,0,0,r.head,0};
        v[k++]={PVR_CMD_VERTEX_EOL,x+hw,y1,r.z,0,0,r.head,0};
        if(k==32){stream_send(v,sizeof v);k=0;}
    }
    if(k)stream_send(v,k*sizeof(pvr_vertex_t));
    return n;
}
#endif
#endif
#if RE4DC_SUBSCREEN && RE4DC_D349_RENDERER_STACK && RE4DC_PVR_STREAM
#include "include/subscreen_quad_geometry.hpp"
namespace {
DeferredLighting* const kSubscreenQuadTag=reinterpret_cast<DeferredLighting*>(4);
constexpr unsigned kSubscreenQuadNode=(sizeof(DeferredPart)+31)&~31U;
}
static int subscreen_submit(const Re4dcSubscreenQuad* q,const pvr_vertex_t* vertices,unsigned count){
    if(!count)return 0;
    alignas(32) pvr_vertex_t packet[13];
    pvr_poly_cxt_t c;pvr_poly_cxt_col(&c,PVR_LIST_TR_POLY);
    c.gen.culling=PVR_CULLING_NONE;c.gen.shading=PVR_SHADE_FLAT;c.gen.fog_type=PVR_FOG_DISABLE;
    c.depth.comparison=q->depth_test?PVR_DEPTHCMP_GEQUAL:PVR_DEPTHCMP_ALWAYS;
    c.depth.write=PVR_DEPTHWRITE_DISABLE;
    constexpr pvr_blend_mode_t src[]={PVR_BLEND_ONE,PVR_BLEND_SRCALPHA,PVR_BLEND_SRCALPHA,PVR_BLEND_ONE};
    constexpr pvr_blend_mode_t dst[]={PVR_BLEND_ZERO,PVR_BLEND_INVSRCALPHA,PVR_BLEND_ONE,PVR_BLEND_ONE};
    c.blend.src=src[q->blend];c.blend.dst=dst[q->blend];
    pvr_poly_compile(reinterpret_cast<pvr_poly_hdr_t*>(packet),&c);
    std::memcpy(packet+1,vertices,count*sizeof(pvr_vertex_t));
    const unsigned bytes=(count+1)*sizeof(pvr_vertex_t);
    if(source_draws_finished){AVD_EVENT(Direct,nullptr,nullptr,4);stream_select(PVR_LIST_TR_POLY);stream_send(packet,bytes);return 1;}
    const unsigned required=kSubscreenQuadNode+bytes,margin=8192;
    unsigned char* storage=frame_storage;unsigned* top=&deferred_top;
    if(required+margin>deferred_top || deferred_top-required-margin<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad)))){
        if(!deferred_spill){deferred_spill=static_cast<unsigned char*>(re4dc_model_deferred_storage(&deferred_spill_capacity));deferred_spill_top=deferred_spill_capacity;}
        if(!deferred_spill || required>deferred_spill_top){++dropped;return 0;}
        storage=deferred_spill;top=&deferred_spill_top; DFA26_HIT(DeferredSpill)
    }
    *top-=required;auto* node=new(storage+*top) DeferredPart{};
    node->lighting=kSubscreenQuadTag;node->changed[0]=bytes;
    std::memcpy(storage+*top+kSubscreenQuadNode,packet,bytes);
    if(deferred_last)deferred_last->next=node;else deferred_first=node;
    deferred_last=node;++deferred_count;
    AVD_EVENT(Enqueue,node,nullptr,unsigned(uintptr_t(node->lighting)));
    frame_queue_peak=std::max(frame_queue_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
    return 1;
}
extern "C" int re4dc_subscreen_quad(const Re4dcSubscreenQuad* q){
    if(!q || !frame_ready || stream_aborted || draining_parts)return 0;
    pvr_vertex_t vertices[12];
    return subscreen_submit(q,vertices,re4dc::subscreen::vertices(*q,vertices));
}
extern "C" int re4dc_subscreen_line(const Re4dcSubscreenQuad* q,unsigned width){
    if(!q || !frame_ready || stream_aborted || draining_parts)return 0;
    pvr_vertex_t vertices[12];
    return subscreen_submit(q,vertices,re4dc::subscreen::line_vertices(*q,width,vertices));
}
#if defined(RE4DC_WATER45_NATIVE) && RE4DC_WATER45_NATIVE
// WATER45_NATIVE (ROUTE_CH13, r10b; espgen45.cpp re4dc_water45_draw): one view-space cell of the open-air
// water surface. The GameCube draws the scene behind the water (its screen copy) times the TEV colour, alpha
// blended by the raster alpha; here the same product is the PVR multiply blend (DESTCOLOR, ZERO) with the
// per-corner factor rgb (owner-computed: alpha mix and fog fade to 1). Untextured, Gouraud, no fog (the
// factor carries it), depth tested, no depth write; queued in source OT order like the subscreen quads.
extern "C" int re4dc_water45_quad(const float positions[4][3],const float rgb[4][3],const float* projection,
                                  const float* viewport){
    if(!frame_ready || stream_aborted || draining_parts)return 0;
    Re4dcSubscreenQuad q;
    std::memcpy(q.positions,positions,sizeof(q.positions));
    std::memcpy(q.projection,projection,sizeof(q.projection));
    std::memcpy(q.viewport,viewport,sizeof(q.viewport));
    q.color=0xFFFFFFFFU;q.blend=0;q.depth_test=1;
    if(q.projection[0]!=0 || q.viewport[2]<=0 || q.viewport[3]<=0)return 0;
    for(float f:q.projection)if(!re4dc::render::is_finite(f))return 0;
    for(float f:q.viewport)if(!re4dc::render::is_finite(f))return 0;
    for(const auto& p:q.positions)for(float f:p)if(!re4dc::render::is_finite(f))return 0;
    const float near=q.projection[6]/(q.projection[5]-1),far=q.projection[6]/q.projection[5];
    if(!re4dc::render::is_finite(near) || !re4dc::render::is_finite(far) || near<=0 || far<=near)return 0;
    re4dc::render::ClipParameters clip{near,far,RE4DC_SCREEN_WF,RE4DC_SCREEN_HF,re4dc::subscreen::project,&q};
    re4dc::render::RenderVertex v[4]{};
    for(unsigned i=0;i<4;++i){
        auto& p=v[i].position;
        p.world_x=p.x=q.positions[i][0];p.world_y=p.y=q.positions[i][1];p.world_z=p.z=q.positions[i][2];
        p.depth=-p.world_z;
        if(p.depth>=near)re4dc::subscreen::project(p.x,p.y,p.z,&q);
        v[i].light_red=rgb[i][0];v[i].light_green=rgb[i][1];v[i].light_blue=rgb[i][2];
    }
    alignas(32) pvr_vertex_t packet[13];
    constexpr unsigned strips[2][3]={{0,1,2},{2,1,3}};
    unsigned used=0;
    for(const auto& indices:strips){
        const re4dc::render::RenderVertex tri[]={v[indices[0]],v[indices[1]],v[indices[2]]};
        used+=3*re4dc::render::clip_projected_triangle(tri,packet+1+used,0,clip);
    }
    if(!used)return 0;
    pvr_poly_cxt_t c;pvr_poly_cxt_col(&c,PVR_LIST_TR_POLY);
    c.gen.culling=PVR_CULLING_NONE;c.gen.shading=PVR_SHADE_GOURAUD;c.gen.fog_type=PVR_FOG_DISABLE;
    c.depth.comparison=PVR_DEPTHCMP_GEQUAL;c.depth.write=PVR_DEPTHWRITE_DISABLE;
    c.blend.src=PVR_BLEND_DESTCOLOR;c.blend.dst=PVR_BLEND_ZERO;
    pvr_poly_compile(reinterpret_cast<pvr_poly_hdr_t*>(packet),&c);
    const unsigned bytes=(used+1)*sizeof(pvr_vertex_t);
    if(source_draws_finished){AVD_EVENT(Direct,nullptr,nullptr,4);stream_select(PVR_LIST_TR_POLY);stream_send(packet,bytes);return 1;}
    const unsigned required=kSubscreenQuadNode+bytes,margin=8192;
    unsigned char* storage=frame_storage;unsigned* top=&deferred_top;
    if(required+margin>deferred_top || deferred_top-required-margin<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad)))){
        if(!deferred_spill){deferred_spill=static_cast<unsigned char*>(re4dc_model_deferred_storage(&deferred_spill_capacity));deferred_spill_top=deferred_spill_capacity;}
        if(!deferred_spill || required>deferred_spill_top){++dropped;return 0;}
        storage=deferred_spill;top=&deferred_spill_top; DFA26_HIT(DeferredSpill)
    }
    *top-=required;auto* node=new(storage+*top) DeferredPart{};
    node->lighting=kSubscreenQuadTag;node->changed[0]=bytes;
    std::memcpy(storage+*top+kSubscreenQuadNode,packet,bytes);
    if(deferred_last)deferred_last->next=node;else deferred_first=node;
    deferred_last=node;++deferred_count;
    AVD_EVENT(Enqueue,node,nullptr,unsigned(uintptr_t(node->lighting)));
    frame_queue_peak=std::max(frame_queue_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
    return 1;
}
#if defined(RE4DC_WATER_PS2) && RE4DC_WATER_PS2
#include "include/native_water_ps2.inc"   // WATER_PS2 (lane water16): PS2 water layers
#endif
#if defined(RE4DC_LAKE_RIPPLES) && RE4DC_LAKE_RIPPLES
// LAKE_RIPPLES (native_lake.cpp): a prebuilt TR packet (headers and vertices) queued like the water quad above.
extern "C" int re4dc_ui_tr_packet(const void* packet,unsigned bytes){
    if(!frame_ready || stream_aborted || draining_parts || !bytes)return 0;
    if(source_draws_finished){AVD_EVENT(Direct,nullptr,nullptr,4);stream_select(PVR_LIST_TR_POLY);stream_send(packet,bytes);return 1;}
    const unsigned required=kSubscreenQuadNode+((bytes+31)&~31U);
    if(required+8192>deferred_top || deferred_top-required-8192<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad))))return 0;
    deferred_top-=required;auto* node=new(frame_storage+deferred_top) DeferredPart{};
    node->lighting=kSubscreenQuadTag;node->changed[0]=bytes;
    std::memcpy(frame_storage+deferred_top+kSubscreenQuadNode,packet,bytes);
    if(deferred_last)deferred_last->next=node;else deferred_first=node;
    deferred_last=node;++deferred_count;
    AVD_EVENT(Enqueue,node,nullptr,unsigned(uintptr_t(node->lighting)));
    return 1;
}
#endif
#endif
#else
extern "C" int re4dc_subscreen_quad(const Re4dcSubscreenQuad*){return 0;}
extern "C" int re4dc_subscreen_line(const Re4dcSubscreenQuad*,unsigned){return 0;}
#endif
#if RE4DC_POST_F00
#if !RE4DC_D349_RENDERER_STACK || !RE4DC_PVR_STREAM
#error POST_F00 needs the D349 renderer stack and PVR_STREAM (deferred translucent queue)
#endif
#if RE4DC_POST_F00!=1 && RE4DC_POST_F00!=4
#error POST_F00: 1 (one gain quad) or 4 (gain and bias, four quads)
#endif
#if defined(RE4DC_FILTER00_DC) && defined(RE4DC_LOOK_TOGGLE)
extern "C" int re4dc_look_filter00(void);  // native_static.cpp: the look preset's Filter00 switch (B)
#endif
namespace {
// POST_F00 (post30.mk): Filter00's look as full-screen translucent quads blended in the PVR's 8-bit tile buffer,
// before the RGB565 write-out (the PVR has no frame copy for the GameCube's half-size blur buffer). A queued post
// is a DeferredPart whose lighting is this tag and whose changed[0] holds its packet bytes (a header and four
// vertices per pass); the translucent drain sends it in OT order, so the HUD's UI quads (drained later) stay out.
DeferredLighting* const kPostTag=reinterpret_cast<DeferredLighting*>(2);
constexpr unsigned kPostNode=(sizeof(DeferredPart)+31)&~31U,kPostPass=sizeof(pvr_poly_hdr_t)+4*sizeof(pvr_vertex_t);
constexpr unsigned kPostBytes=(RE4DC_POST_F00==4?4:1)*kPostPass;
unsigned post_calls,post_queued,post_direct,post_dropped,post_skipped,post_key1=~0U,post_key2=~0U;
unsigned post_c,post_h;
// One full-screen pass: a flat grey quad blended with (src, dst) over the whole tile buffer.
void post_pass(unsigned char* out,pvr_blend_mode_t src,pvr_blend_mode_t dst,unsigned grey){
    pvr_poly_cxt_t c;pvr_poly_cxt_col(&c,PVR_LIST_TR_POLY);
    c.gen.culling=PVR_CULLING_NONE;c.depth.comparison=PVR_DEPTHCMP_ALWAYS;c.depth.write=PVR_DEPTHWRITE_DISABLE;
    c.blend.src=src;c.blend.dst=dst;
    pvr_poly_compile(reinterpret_cast<pvr_poly_hdr_t*>(out),&c);
    auto* v=reinterpret_cast<pvr_vertex_t*>(out+sizeof(pvr_poly_hdr_t));
    const float xs[4]={0,0,640,640},ys[4]={480,0,480,0};
    const std::uint32_t argb=0xff000000U|grey<<16|grey<<8|grey;
    for(unsigned k=0;k<4;++k){
        v[k].flags=k==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;v[k].x=RE4DC_UI_X(xs[k]);v[k].y=RE4DC_UI_Y(ys[k]);v[k].z=1.0f;
        v[k].u=v[k].v=0;v[k].argb=argb;v[k].oargb=0;
    }
}
void post_send(unsigned char* packet,unsigned bytes){
#if RE4DC_WORLD_AUTOSORT
    if(world_autosort)for(unsigned offset=0;offset<bytes;offset+=kPostPass){
        auto* v=reinterpret_cast<pvr_vertex_t*>(packet+offset+sizeof(pvr_poly_hdr_t));
        const float layer=overlay_depth();for(unsigned i=0;i<4;++i)v[i].z=layer;
    }
#endif
    stream_send(packet,bytes);
}
void post_packet(unsigned char* out){
    post_pass(out,PVR_BLEND_DESTCOLOR,PVR_BLEND_ONE,post_c);                    // d + c d
#if RE4DC_POST_F00==4
    post_pass(out+kPostPass,PVR_BLEND_INVDESTCOLOR,PVR_BLEND_ZERO,255);          // 1 - x
    post_pass(out+2*kPostPass,PVR_BLEND_ONE,PVR_BLEND_ONE,post_h);               // x + h (clamps at 1)
    post_pass(out+3*kPostPass,PVR_BLEND_INVDESTCOLOR,PVR_BLEND_ZERO,255);        // 1 - x = max(0, g d - h)
#endif
}
// Filter00's flat-field steady state: blur type 2 feeds back E = S + a max(0, E - p) (a = rate/255, only while the
// GameCube's buffer is valid), the contrast adds k max(0, E - b) (k = pow/255 2^(level-1)). Types 0 / 1 blend the
// buffer back (no gain on a flat field). POST_F00=1: c = F(d0)/d0 - 1 at the mid-tone d0 = 48; =4: F = max(0, g d - h)
// with g = (1+k)/(1-a), h = (1+k) a p/(1-a) + k b (the curve above its knee).
void post_params(unsigned rate,unsigned type,int power,unsigned level,unsigned pow,unsigned bias,bool valid){
    const float a=(type==2 && valid)?rate/255.0f:0.0f,p=power>0?power/255.0f:0.0f;
    const float k=level?pow/255.0f*float(1U<<(level-1)):0.0f,b=bias/255.0f;
#if RE4DC_POST_F00==4
    const float g=(1+k)/(1-a),h=(1+k)*a*p/(1-a)+k*b;
    post_c=unsigned(std::min(255.0f,std::max(0.0f,(g-1)*255+0.5f)));
    post_h=unsigned(std::min(255.0f,std::max(0.0f,h*255+0.5f)));
#else
    const float d0=48/255.0f,e=std::max(d0,(d0-a*p)/(1-a)),f=e+k*std::max(0.0f,e-b);
    post_c=unsigned(std::min(255.0f,std::max(0.0f,(f/d0-1)*255+0.5f)));
    post_h=0;
#endif
}
}
extern "C" void re4dc_post_filter00(unsigned char rate,unsigned char type,signed char power,unsigned char level,
                                    unsigned char pow,unsigned char bias,int valid){
    ++post_calls;
    const unsigned key1=rate|unsigned(type)<<8|unsigned((unsigned char)power)<<16|unsigned(level)<<24;
    const unsigned key2=pow|unsigned(bias)<<8|(valid?0x10000U:0U);
    if(key1!=post_key1 || key2!=post_key2){
        post_key1=key1;post_key2=key2;post_params(rate,type,power,level,pow,bias,valid!=0);
        re4dc_log("post f00: mode=%d rate=%u type=%u power=%d level=%u pow=%u bias=%u valid=%d -> c=%u h=%u gain=%u/1000 frame=%u"
                  " (calls=%u queued=%u direct=%u dropped=%u skipped=%u)\n",RE4DC_POST_F00,unsigned(rate),unsigned(type),int(power),
                  unsigned(level),unsigned(pow),unsigned(bias),valid!=0,post_c,post_h,1000U+post_c*1000U/255U,frame,
                  post_calls,post_queued,post_direct,post_dropped,post_skipped);
    }
    if(!frame_ready || stream_aborted || draining_parts)return;
#if defined(RE4DC_FILTER00_DC) && defined(RE4DC_LOOK_TOGGLE)
    if(!re4dc_look_filter00()){++post_skipped;return;}   // FILTER00_DC + LOOK_TOGGLE: preset B only
#endif
    if(!post_c && !post_h){++post_skipped;return;}
#if RE4DC_POST_F00_DIAG
    post_diag_frame();
#endif
    if(source_draws_finished){
        AVD_EVENT(Direct,nullptr,nullptr,2);
        alignas(32) unsigned char packet[kPostBytes];post_packet(packet);
        stream_select(PVR_LIST_TR_POLY);post_send(packet,kPostBytes);++post_direct;return;
    }
    const unsigned required=kPostNode+kPostBytes,margin=8192;
    unsigned char* storage=frame_storage;unsigned* top=&deferred_top;
    if(required+margin>deferred_top || deferred_top-required-margin<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad)))){
        if(!deferred_spill){deferred_spill=static_cast<unsigned char*>(re4dc_model_deferred_storage(&deferred_spill_capacity));deferred_spill_top=deferred_spill_capacity;}
        if(!deferred_spill || required>deferred_spill_top){++post_dropped;return;}
        storage=deferred_spill;top=&deferred_spill_top; DFA26_HIT(DeferredSpill)
    }
    *top-=required;
    auto* node=new(storage+*top) DeferredPart{};node->lighting=kPostTag;node->changed[0]=kPostBytes;
    post_packet(storage+*top+kPostNode);
    if(deferred_last)deferred_last->next=node;else deferred_first=node;
    deferred_last=node;++deferred_count;
    AVD_EVENT(Enqueue,node,nullptr,unsigned(uintptr_t(node->lighting)));
    ++post_queued;
    frame_queue_peak=std::max(frame_queue_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
}
#endif
#if defined(RE4DC_LOOK_TOGGLE)
#if !RE4DC_D349_RENDERER_STACK || !RE4DC_PVR_STREAM
#error LOOK_TOGGLE: the grade quad needs the D349 renderer stack and PVR_STREAM (deferred translucent queue)
#endif
namespace {
// LOOK_TOGGLE GM / GA (look study 2026-10-10): one full-screen translucent quad, blend (DESTCOLOR, ZERO), colour c:
// d -> d c per channel in the 8-bit tile buffer before the RGB565 write-out. Queued at Filter00Render's OT slot (as
// POST_F00), so the scenery, actors and translucent parts drawn before it are graded and the HUD is not.
DeferredLighting* const kGradeTag=reinterpret_cast<DeferredLighting*>(6); // unique: 1 sprite, 2 post, 3 laser line, 4 sub screen
constexpr unsigned kGradeNode=(sizeof(DeferredPart)+31)&~31U,kGradeBytes=sizeof(pvr_poly_hdr_t)+4*sizeof(pvr_vertex_t);
unsigned grade_queued,grade_direct,grade_dropped;
void grade_packet(unsigned char* out,std::uint32_t argb){
    pvr_poly_cxt_t c;pvr_poly_cxt_col(&c,PVR_LIST_TR_POLY);
    c.gen.culling=PVR_CULLING_NONE;c.depth.comparison=PVR_DEPTHCMP_ALWAYS;c.depth.write=PVR_DEPTHWRITE_DISABLE;
    c.blend.src=PVR_BLEND_DESTCOLOR;c.blend.dst=PVR_BLEND_ZERO;
    pvr_poly_compile(reinterpret_cast<pvr_poly_hdr_t*>(out),&c);
    auto* v=reinterpret_cast<pvr_vertex_t*>(out+sizeof(pvr_poly_hdr_t));
    const float xs[4]={0,0,640,640},ys[4]={480,0,480,0};
    for(unsigned k=0;k<4;++k){
        v[k].flags=k==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;v[k].x=RE4DC_UI_X(xs[k]);v[k].y=RE4DC_UI_Y(ys[k]);v[k].z=1.0f;
        v[k].u=v[k].v=0;v[k].argb=argb;v[k].oargb=0;
    }
}
#if RE4DC_GC_ASSET_GATE
extern pvr_ptr_t osd_vram;
#endif
void grade_send(unsigned char* packet,unsigned bytes){
#if RE4DC_WORLD_AUTOSORT
    if(world_autosort)for(unsigned off=0;off<bytes;off+=kGradeBytes){
        auto* v=reinterpret_cast<pvr_vertex_t*>(packet+off+sizeof(pvr_poly_hdr_t));
        const float layer=overlay_depth();for(unsigned i=0;i<4;++i)v[i].z=layer;}
#endif
#if RE4DC_GC_ASSET_GATE
    // gc-catalog24b: the look/preset label is KOS BIOS-font text rendered at run
    // time into osd_vram (osd_texture), not a disc asset: a generated packet.
    GcAssetGeneratedPacket asset_packet{packet,bytes,unsigned(reinterpret_cast<std::uintptr_t>(osd_vram))&0x007fffffU,re4dc_gcasset::Ui,true};
    {GcAssetGeneratedScope asset_scope(asset_packet);
#endif
    stream_send(packet,bytes);
#if RE4DC_GC_ASSET_GATE
    }
#endif
}
// The preset label: the BIOS font (bfont, 12x24, as the crash screen) rendered into a 512x32 RGB565 texture when
// the text changes (32 KiB of VRAM, allocated on first use; no label if that fails), drawn as one quad in the top
// picture top-left corner (y 66..98, under the top letterbox bar the game draws over y < 60; the HUD is bottom right).
constexpr unsigned kOsdW=512,kOsdH=32;
pvr_ptr_t osd_vram;const char* osd_loaded;bool osd_failed;
bool osd_texture(const char* text){
    if(osd_failed)return false;
    if(!osd_vram){osd_vram=pvr_mem_malloc(kOsdW*kOsdH*2);if(!osd_vram){osd_failed=true;re4dc_log("look label: no VRAM\n");return false;}}
    if(text!=osd_loaded){
        static unsigned short buf[kOsdW*kOsdH];
        memset(buf,0,sizeof(buf));bfont_draw_str_ex(buf+4*kOsdW+4,kOsdW,0xFFFFU,0,16,1,text);
#if RE4DC_PVR_MID_FENCE
        present_fence();   // PVR_MID_FENCE: the previous frame's render samples this texture
#endif
        pvr_txr_load(buf,osd_vram,sizeof(buf));osd_loaded=text;
        re4dc_log("look label: '%s' vram=%p frame=%u\n",text,(void*)osd_vram,frame);
    }
    return true;
}
void osd_packet(unsigned char* out){
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,PVR_LIST_TR_POLY,PVR_TXRFMT_RGB565|PVR_TXRFMT_NONTWIDDLED,kOsdW,kOsdH,osd_vram,PVR_FILTER_NONE);
    c.gen.culling=PVR_CULLING_NONE;c.depth.comparison=PVR_DEPTHCMP_ALWAYS;c.depth.write=PVR_DEPTHWRITE_DISABLE;
    c.blend.src=PVR_BLEND_ONE;c.blend.dst=PVR_BLEND_ZERO;c.gen.fog_type=PVR_FOG_DISABLE;
    pvr_poly_compile(reinterpret_cast<pvr_poly_hdr_t*>(out),&c);
    auto* v=reinterpret_cast<pvr_vertex_t*>(out+sizeof(pvr_poly_hdr_t));
    const float w=float(std::min(kOsdW,unsigned(strlen(osd_loaded))*12U+8U)),u1=w/float(kOsdW); // the text's width only
    const float x0=20,y0=66,xs[4]={x0,x0,x0+w,x0+w},ys[4]={y0+kOsdH,y0,y0+kOsdH,y0},us[4]={0,0,u1,u1},vs[4]={1,0,1,0};
    for(unsigned k=0;k<4;++k){
        v[k].flags=k==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;v[k].x=RE4DC_UI_X(xs[k]);v[k].y=RE4DC_UI_Y(ys[k]);v[k].z=1.0f;
        v[k].u=us[k];v[k].v=vs[k];v[k].argb=0xffffffffU;v[k].oargb=0;
    }
}
}
extern "C" unsigned re4dc_look_grade_argb(void);
extern "C" const char* re4dc_look_osd_text(void);
extern "C" void re4dc_look_grade_post(void){
    const unsigned argb=re4dc_look_grade_argb();
    const char* text=re4dc_look_osd_text();
    if((!argb && !text) || !frame_ready || stream_aborted || draining_parts)return;
    const bool osd=text && osd_texture(text);
    if(!argb && !osd)return;
    const unsigned bytes=(argb?kGradeBytes:0U)+(osd?kGradeBytes:0U);
    if(source_draws_finished){
        AVD_EVENT(Direct,nullptr,nullptr,6);
        alignas(32) unsigned char packet[2*kGradeBytes];
        if(argb)grade_packet(packet,argb);
        if(osd)osd_packet(packet+(argb?kGradeBytes:0U));
        stream_select(PVR_LIST_TR_POLY);grade_send(packet,bytes);++grade_direct;return;
    }
    const unsigned required=kGradeNode+bytes,margin=8192;
    unsigned char* storage=frame_storage;unsigned* top=&deferred_top;
    if(required+margin>deferred_top || deferred_top-required-margin<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad)))){
        if(!deferred_spill){deferred_spill=static_cast<unsigned char*>(re4dc_model_deferred_storage(&deferred_spill_capacity));deferred_spill_top=deferred_spill_capacity;}
        if(!deferred_spill || required>deferred_spill_top){++grade_dropped;return;}
        storage=deferred_spill;top=&deferred_spill_top; DFA26_HIT(DeferredSpill)
    }
    *top-=required;
    auto* node=new(storage+*top) DeferredPart{};node->lighting=kGradeTag;node->changed[0]=bytes;
    if(argb)grade_packet(storage+*top+kGradeNode,argb);
    if(osd)osd_packet(storage+*top+kGradeNode+(argb?kGradeBytes:0U));
    if(deferred_last)deferred_last->next=node;else deferred_first=node;
    deferred_last=node;++deferred_count;
    AVD_EVENT(Enqueue,node,nullptr,unsigned(uintptr_t(node->lighting)));
    if(!(grade_queued++%1800))re4dc_log("look grade: argb=%08x queued=%u direct=%u dropped=%u\n",argb,grade_queued,grade_direct,grade_dropped);
    frame_queue_peak=std::max(frame_queue_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
}
#endif
#if RE4DC_COARSE_WORLD & 8
extern "C" void re4dc_coarse_world_flush();
#endif
#if RE4DC_PS2_WORLD_DRAW
// Called only between owned actor material runs, before one_chunk creates any
// packet/scratch reservation or resolves its Entry. Never call from packet_begin
// or stream_select: those callers can hold an uncommitted Entry and shared scratch.
extern "C" int re4dc_ps2_world_before_owned_tr(const Re4dcModelPart* part){
    if(!part || !frame_ready || stream_aborted || direct_open || model_used)return 0;
    if(select_model_pass(part)!=PVR_LIST_TR_POLY)return 1;
#if RE4DC_PS2_WORLD_R11F_OWNER
    if(!re4dc_r11f_barrier(frame))return 0;
#endif
    if(!re4dc_ps2_world_pending()){
#if RE4DC_COARSE_SCENERY_FALLBACK && RE4DC_TREE_IMPOSTOR
        // A room drawing its own scenery (trans.cpp COARSE_SCENERY_FALLBACK) queues tree impostors (PT):
        // close that PT window before the first owned-actor TR, as the PS2 world barrier below does.
        if(!(stream_scene && stream_list==PVR_LIST_TR_POLY)){
            re4dc_static_flush_impostors();
            return frame_ready && !stream_aborted && !direct_open && !model_used;
        }
#endif
        return 1;
    }
    if(stream_scene && stream_list==PVR_LIST_TR_POLY){
        re4dc_log("PS2PASS late-world frame=%u mask=%x\n",frame,stream_closed_lists);
        return 0; // existing transaction failure discards this incomplete scene
    }
    if(world_barrier_logs<8 || !(frame%120)){
        ++world_barrier_logs;
        re4dc_log("PS2PASS barrier frame=%u from=%u scene=%u\n",frame,unsigned(stream_list),unsigned(stream_scene));
    }
    // Keep the single PT window before either PS2 or owned-actor TR. The final
    // source drain still calls both idempotent flushes if there is no owned TR.
    re4dc_static_flush_impostors();
    re4dc_ps2_world_flush();
    return frame_ready && !stream_aborted && !direct_open && !model_used;
}
#if defined(RE4DC_LEON_NATIVE_PIPE) && RE4DC_LEON_NATIVE_PIPE
// LEON_NATIVE_PIPE: 1 when re4dc_ps2_world_before_owned_tr(part) would return 1 without a side effect once the window
// were closed (direct_end leaves direct_open false and model_used 0): the lean Leon pass then changes material inside
// its open window instead (re4dc_leon_direct_switch). 0: close the window and call the barrier as usual.
extern "C" int re4dc_leon_owned_tr_idle(const Re4dcModelPart* part){
    if(!part || !frame_ready || stream_aborted)return 0;
    if(select_model_pass(part)!=PVR_LIST_TR_POLY)return 1;
    if(re4dc_ps2_world_pending())return 0;
#if RE4DC_COARSE_SCENERY_FALLBACK && RE4DC_TREE_IMPOSTOR
    if(!(stream_scene && stream_list==PVR_LIST_TR_POLY))return 0;
#endif
    return 1;
}
#endif
// Included once at native_ui.cpp global scope, after the normal packet APIs.
// Explicit keys reach the existing loader; submitted Entry::frame pins preserve
// its TA/render-fence lifetime. No pointer hash, preload, private VRAM or lease.
#if RE4DC_NATIVE_FOG && RE4DC_PS2_WORLD_FOG_SOURCE
extern "C" unsigned re4dc_ps2_world_fog(); // native_ps2_world.cpp: latched at this frame's scenery draw
#endif
extern "C" int re4dc_ps2_world_packet(unsigned crc,unsigned fnv,unsigned width,unsigned height,unsigned pass,Re4dcModelPacket* out){
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    sob33_barrier(re4dc::sob33::CustomPacket); // may retain the current list
#endif
#if RE4DC_TA_MATERIAL_DIAG
    tamat::packet_source=1;
#endif
    if(!out || pass>2 || !frame_ready || stream_aborted || direct_open ||
       !ensure_model_storage() || model_used+32>kModelPacketBytes/32)return 0;
#if RE4DC_UI_POLY_ORDER && RE4DC_SS_UI_ORDER
    if(ui_order && quads_flushed<nquad)ui_order_flush();
    if(stream_aborted)return 0;
#endif
    const Key key{crc,fnv};
    const Re4dcUiImage image{&key,nullptr,width,height,5,0,0};
    Entry* handle=load(image,false,&key);
    if(!handle || !frame_ready || stream_aborted || direct_open){++model_texture_rejects;return 0;}
    const auto& t=handle->package.textures()[0];
    if(t.width!=width || t.height!=height)return 0; // repeated UVs cannot use padding
    const pvr_list_t list=pass==0?PVR_LIST_OP_POLY:pass==1?PVR_LIST_PT_POLY:PVR_LIST_TR_POLY;
    stream_select(list);
#if RE4DC_WORLD_AUTOSORT
    world_sort_begin();
#endif
    if(stream_aborted)return 0;
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,list,re4dc::texture::pvr_format(t),RE4DC_TSP_W(t),RE4DC_TSP_H(t),handle->package.pvr_texture(0),PVR_FILTER_BILINEAR);
    c.gen.culling=PVR_CULLING_NONE; // authored cull already applied after clipping
    c.depth.comparison=PVR_DEPTHCMP_GEQUAL;
    c.depth.write=pass==2?PVR_DEPTHWRITE_DISABLE:PVR_DEPTHWRITE_ENABLE;
    c.blend.src=(pass==2 || (RE4DC_PT_BLEND_FIX && pass==1))?PVR_BLEND_SRCALPHA:PVR_BLEND_ONE;
    c.blend.dst=(pass==2 || (RE4DC_PT_BLEND_FIX && pass==1))?PVR_BLEND_INVSRCALPHA:PVR_BLEND_ZERO;
    c.txr.env=PVR_TXRENV_MODULATEALPHA;
    c.txr.alpha=pass?PVR_TXRALPHA_ENABLE:PVR_TXRALPHA_DISABLE;
    c.txr.uv_clamp=PVR_UVCLAMP_NONE;
#if RE4DC_NATIVE_FOG && RE4DC_PS2_WORLD_FOG_SOURCE
    c.gen.fog_type=re4dc_ps2_world_fog()?PVR_FOG_TABLE:PVR_FOG_DISABLE; // source GX fog at the scenery draw
#elif RE4DC_NATIVE_FOG
    c.gen.fog_type=PVR_FOG_TABLE;
#endif
    pvr_poly_hdr_t header;pvr_poly_compile(&header,&c);DFA26_COUNT(model_header_builds,PacketHeaderBuild);

#if RE4DC_UI_POLY_ORDER
    ui_order_polygon_header(header);
#endif
    std::uint32_t count;re4dc::render::begin_pvr_packet(model_packets+model_used,count,header);
    RE4DC_GAD_HIT(handle->key);RE4DC_PART_DUMP_KEY(handle->key);
    RE4DC_GCA_MODEL_PREPARE(nullptr);model_pending=model_used+count;model_handle=handle;
    out->vertices=model_packets+model_pending;out->capacity=kModelPacketBytes/32-model_pending;
    out->u_scale=out->v_scale=1;
    return 1;
}
#if RE4DC_PS2_WORLD_KERNEL==4
extern "C" int re4dc_ps2_world_packet_cull(unsigned crc,unsigned fnv,unsigned width,unsigned height,unsigned pass,unsigned cull,Re4dcModelPacket* out){
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    sob33_barrier(re4dc::sob33::CustomPacket);
#endif
#if RE4DC_TA_MATERIAL_DIAG
    tamat::packet_source=1;
#endif
    if(!out || pass>2 || !frame_ready || stream_aborted || direct_open ||
       !ensure_model_storage() || model_used+32>kModelPacketBytes/32)return 0;
#if RE4DC_UI_POLY_ORDER && RE4DC_SS_UI_ORDER
    if(ui_order && quads_flushed<nquad)ui_order_flush();
    if(stream_aborted)return 0;
#endif
    const Key key{crc,fnv};
    const Re4dcUiImage image{&key,nullptr,width,height,5,0,0};
    Entry* handle=load(image,false,&key);
    if(!handle || !frame_ready || stream_aborted || direct_open){++model_texture_rejects;return 0;}
    const auto& t=handle->package.textures()[0];
    if(t.width!=width || t.height!=height)return 0; // repeated UVs cannot use padding
    const pvr_list_t list=pass==0?PVR_LIST_OP_POLY:pass==1?PVR_LIST_PT_POLY:PVR_LIST_TR_POLY;
    stream_select(list);
#if RE4DC_WORLD_AUTOSORT
    world_sort_begin();
#endif
    if(stream_aborted)return 0;
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,list,re4dc::texture::pvr_format(t),RE4DC_TSP_W(t),RE4DC_TSP_H(t),handle->package.pvr_texture(0),PVR_FILTER_BILINEAR);
    // PS2_WORLD_KERNEL=4 strips: the authored cull (0 drops screen area >= 0, i.e. clockwise with y down).
    c.gen.culling=cull==0?PVR_CULLING_CW:cull==1?PVR_CULLING_CCW:PVR_CULLING_NONE;
    c.depth.comparison=PVR_DEPTHCMP_GEQUAL;
    c.depth.write=pass==2?PVR_DEPTHWRITE_DISABLE:PVR_DEPTHWRITE_ENABLE;
    c.blend.src=(pass==2 || (RE4DC_PT_BLEND_FIX && pass==1))?PVR_BLEND_SRCALPHA:PVR_BLEND_ONE;
    c.blend.dst=(pass==2 || (RE4DC_PT_BLEND_FIX && pass==1))?PVR_BLEND_INVSRCALPHA:PVR_BLEND_ZERO;
    c.txr.env=PVR_TXRENV_MODULATEALPHA;
    c.txr.alpha=pass?PVR_TXRALPHA_ENABLE:PVR_TXRALPHA_DISABLE;
    c.txr.uv_clamp=PVR_UVCLAMP_NONE;
#if RE4DC_NATIVE_FOG && RE4DC_PS2_WORLD_FOG_SOURCE
    c.gen.fog_type=re4dc_ps2_world_fog()?PVR_FOG_TABLE:PVR_FOG_DISABLE; // source GX fog at the scenery draw
#elif RE4DC_NATIVE_FOG
    c.gen.fog_type=PVR_FOG_TABLE;
#endif
    pvr_poly_hdr_t header;pvr_poly_compile(&header,&c);DFA26_COUNT(model_header_builds,PacketHeaderBuild);

#if RE4DC_UI_POLY_ORDER
    ui_order_polygon_header(header);
#endif
    std::uint32_t count;re4dc::render::begin_pvr_packet(model_packets+model_used,count,header);
    RE4DC_GAD_HIT(handle->key);RE4DC_PART_DUMP_KEY(handle->key);
    RE4DC_GCA_MODEL_PREPARE(nullptr);model_pending=model_used+count;model_handle=handle;
    out->vertices=model_packets+model_pending;out->capacity=kModelPacketBytes/32-model_pending;
    out->u_scale=out->v_scale=1;
    return 1;
}
#endif
#endif
#if RE4DC_PS2_WORLD_DRAW && RE4DC_PS2_WORLD_MESH
#if RE4DC_PS2_WORLD_HDR_CACHE
// PS2_WORLD_HDR_CACHE (game30.mk; exact in pixels): the compiled header of each PS2 world material (texture key and
// size, pass, cull, latched fog) with the Entry it was compiled for. A hit skips the texture lookup (load(): hint,
// else the TEX_SLOTS scan) and pvr_poly_cxt_txr + pvr_poly_compile. A slot is used only while its Entry is valid,
// still holds that key and still has the same VRAM address. PS2_UPLOAD_INCARNATION additionally requires the
// exact published upload: allocator address reuse alone cannot authorize format/mip header words. Words 4..7:
// KOS pvr_poly_compile never writes them for a header without a modifier volume, so the uncached path sends whatever
// the stack held there (the PVR ignores them for these packed-colour, non-modifier headers); with this knob both
// paths send zeros. 32 sets of 4 slots; a miss refills the set's slots in turn.
namespace {
// PS2_HDR_SETS=N (game30.mk, lane fx19; exact): N sets instead of 32 (r101 thrashed the 128 slots: ~29 refills a picture).
#ifndef RE4DC_PS2_HDR_SETS
#define RE4DC_PS2_HDR_SETS 32
#endif
constexpr unsigned kPs2HdrSets=RE4DC_PS2_HDR_SETS,kPs2HdrWays=4;
static_assert((kPs2HdrSets&(kPs2HdrSets-1U))==0,"PS2_HDR_SETS is a power of two");
// PS2_UPLOAD_SLOT_BEGIN
#if RE4DC_PS2_UPLOAD_INCARNATION
struct Ps2HdrSlot { unsigned crc,fnv,size,mode; Entry* entry; pvr_ptr_t texture; std::uint32_t words[4];
    std::uint32_t upload_incarnation;
};
#else
struct Ps2HdrSlot { unsigned crc,fnv,size,mode; Entry* entry; pvr_ptr_t texture; std::uint32_t words[4]; };
#endif
// PS2_UPLOAD_SLOT_END
#if RE4DC_PS2_UPLOAD_INCARNATION
bool ps2_hdr_upload_current(const Ps2HdrSlot& slot,const Entry* entry) {
    return entry && slot.upload_incarnation && slot.upload_incarnation==entry->upload_incarnation;
}
#endif
static_assert(sizeof(pvr_poly_hdr_t)==32);
Ps2HdrSlot ps2_hdr[kPs2HdrSets][kPs2HdrWays];
unsigned char ps2_hdr_next[kPs2HdrSets];
unsigned ps2_hdr_hits,ps2_hdr_fills,ps2_hdr_log=~0U;
#if RE4DC_SCENERY_PIECE_STATE
unsigned ps2_piece_hits; // SCENERY_PIECE_STATE: hits found through the part's slot word
#endif
#if RE4DC_PS2_WORLD_HDR_CACHE==2
unsigned ps2_hdr_checked,ps2_hdr_bad;
#endif
#if RE4DC_PS2_WORLD_HDR_CACHE==3
// =3 (layout control, diagnostic): this .data word picks the path (1 = uncached, 2 = cached; never 0, so it stays
// in .data), so the two arms differ in this word only (PS2_WORLD_HDR_CACHE_SELECT=0|1).
#ifndef RE4DC_PS2_WORLD_HDR_CACHE_SELECT
#define RE4DC_PS2_WORLD_HDR_CACHE_SELECT 0
#endif
volatile unsigned ps2_hdr_select=1U+RE4DC_PS2_WORLD_HDR_CACHE_SELECT;
#define RE4DC_PS2_HDR_ON (ps2_hdr_select==2U)
#else
#define RE4DC_PS2_HDR_ON true
#endif
}
#endif
// PS2_WORLD_MESH (native_static.cpp): re4dc_ps2_world_packet's texture bind and pass header, with the
// part's cull (0 none, 1 CCW, 2 CW, as re4dc_model_packet_begin maps a part's cull), sent by store queue
// as re4dc_model_direct_begin does. key: crc, fnv, width, height, pass, cull.
#if RE4DC_PS2_INTERIOR_CULL==2 && RE4DC_TA_DIRECT
// PS2_INTERIOR_CULL=2 (game30.mk): the check run's header is the part's own with texturing and fog off, so every
// pixel takes the corners' colour (native_static.cpp sets it to opaque magenta). The vertex words are unchanged:
// an untextured packed-colour vertex reads the same 32-byte layout (colour in word 6, UV ignored).
extern "C" unsigned re4dc_ps2_check_header; // native_static.cpp: set around the check run
static void ps2_check_header(pvr_poly_hdr_t& header){
    auto* hw=reinterpret_cast<std::uint32_t*>(&header);
    hw[0]&=~std::uint32_t(PVR_TA_CMD_TXRENABLE|PVR_TA_CMD_SPECULAR);
    hw[1]&=~std::uint32_t(PVR_TA_PM1_TXRENABLE);
    hw[2]=(hw[2]&~std::uint32_t(PVR_TA_PM2_FOG))|FIELD_PREP(PVR_TA_PM2_FOG,PVR_FOG_DISABLE);
}
#endif
#if defined(RE4DC_SKY_FAR) || defined(RE4DC_LOOK_TOGGLE)
// SKY_FAR=2 (post30.mk, look study): the sky / backdrop rows' headers with the table fog off (words 0..3 after
// the compile or the header cache, as ps2_check_header).
extern "C" unsigned re4dc_ps2_sky_header; // native_static.cpp ps2_pass
static void ps2_sky_header(pvr_poly_hdr_t& header){
    auto* hw=reinterpret_cast<std::uint32_t*>(&header);
    hw[2]=(hw[2]&~std::uint32_t(PVR_TA_PM2_FOG))|FIELD_PREP(PVR_TA_PM2_FOG,PVR_FOG_DISABLE);
}
#endif
#if defined(RE4DC_PS2_PLACE_GATE) && RE4DC_PS2_PLACE_GATE
// PS2_PLACE_GATE (native_static.cpp re4dc_ps2_place_ready): is this key's texture resident now? Lookup only: no load,
// no LRU touch. A scan of the entries: call it at room setup / until ready, not per frame.
extern "C" int re4dc_ui_texture_resident(unsigned crc,unsigned fnv){
    const Key key{crc,fnv};
    for(const auto& e:entries)if(e.valid && e.key==key)return 1;
    return 0;
}
#endif
#if RE4DC_SCENERY_PIECE_STATE
extern "C" { std::uint32_t* re4dc_ps2_piece_slot=nullptr; } // native_static.cpp sets it around a PS2 part's bind
#endif
#if defined(RE4DC_PS2_PVS) && RE4DC_PS2_PVS
// A refused/closed/discarded image supplies no usable receipt identity.
extern "C" int re4dc_pvs23_scene(unsigned out[2]){
#if RE4DC_TA_DIRECT && RE4DC_D349_RENDERER_STACK && RE4DC_PVR_STREAM
    if(!out || !frame_ready || stream_aborted || !stream_scene)return 0;
    out[0]=frame;out[1]=pvs23_scene_epoch;return pvs23_scene_epoch!=0;
#else
    (void)out;return 0;
#endif
}
// Read-only proof prerequisite. Never loads, pins, allocates, evicts, updates
// header slots, selects a list or publishes packets. False means draw normally.
// True is only current material eligibility, never proof of eventual submission.
// The proof caller must separately establish source/LOD/clip eligibility and
// successful covering geometry submission before using any dependent cut.
extern "C" int re4dc_pvs23_opaque_ready(const unsigned k[6],unsigned minimum_scratch){
#if RE4DC_TA_DIRECT && RE4DC_D349_RENDERER_STACK && RE4DC_PVR_STREAM && !RE4DC_SCENERY_PIECE_STATE
    if(!k || k[4]!=0U || (k[5]!=0U && k[5]!=2U) || !minimum_scratch ||
       !frame_ready || stream_aborted || direct_open || draining_parts || source_draws_finished || !model_packets)return 0;
    const unsigned slots=kModelPacketBytes/32U;
    if(model_used>=slots || minimum_scratch>slots-model_used-1U)return 0;
#if RE4DC_PS2_INTERIOR_CULL==2
    if(re4dc_ps2_check_header)return 0;
#endif
#if defined(RE4DC_SKY_FAR) || defined(RE4DC_LOOK_TOGGLE)
    if(re4dc_ps2_sky_header)return 0;
#endif
    if(stream_scene){
        if(stream_list!=PVR_LIST_OP_POLY || (stream_closed_lists&(1U<<unsigned(PVR_LIST_OP_POLY))))return 0;
    }else if(desired_list!=PVR_LIST_OP_POLY)return 0;
#if RE4DC_UI_POLY_ORDER
    if(ui_order)return 0;
#endif
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(!re4dc_source_world_binding_valid())return 0;
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
    if(!re4dc_r11f_binding_valid())return 0;
#endif
    const Key key{k[0],k[1]};const Entry* resident=nullptr;
    for(const auto& entry:entries)if(entry.valid && entry.key==key){
        if(resident)return 0; // ambiguous cache identity is not a proof
        resident=&entry;
    }
    if(!resident || resident->frame!=frame || !resident->package.upload_complete() ||
       resident->package.header().texture_count!=1U)return 0;
    const auto& texture=resident->package.textures()[0];
    const auto address=resident->package.pvr_texture(0);
    // RGB565 is intrinsically opaque. Only the same authenticated rect21
    // representation accepted by direct_begin may bridge logical dimensions.
    if(!address || texture.format!=re4dc::texture::kRgb565 ||
       (texture.flags&(re4dc::texture::kAlpha|re4dc::texture::kBinaryAlpha|re4dc::texture::kTopDrop)))return 0;
    if(texture.width!=k[2] || texture.height!=k[3]){
#if RE4DC_WORLD_RECT21
        float u=1.0f,v=1.0f;
        if(!re4dc::rect21::adapt(k[0],k[1],k[2],k[3],
            {texture.width,texture.height,texture.format,texture.flags,texture.payload,texture.data_size,
             resident->package.header().payload_crc32},u,v,true))return 0;
#else
        return 0;
#endif
    }
    pvr_poly_cxt_t c;
    pvr_poly_cxt_txr(&c,PVR_LIST_OP_POLY,re4dc::texture::pvr_format(texture),
        RE4DC_TSP_W(texture),RE4DC_TSP_H(texture),address,PVR_FILTER_BILINEAR);
    c.gen.culling=k[5]==2U?PVR_CULLING_CW:PVR_CULLING_NONE;
    c.depth.comparison=PVR_DEPTHCMP_GEQUAL;c.depth.write=PVR_DEPTHWRITE_ENABLE;
    c.blend.src=PVR_BLEND_ONE;c.blend.dst=PVR_BLEND_ZERO;
    c.txr.env=PVR_TXRENV_MODULATEALPHA;c.txr.alpha=PVR_TXRALPHA_DISABLE;c.txr.uv_clamp=PVR_UVCLAMP_NONE;
#if RE4DC_NATIVE_FOG && RE4DC_PS2_WORLD_FOG_SOURCE
    const unsigned fog=re4dc_ps2_world_fog()?1U:0U;
    c.gen.fog_type=fog?PVR_FOG_TABLE:PVR_FOG_DISABLE;
#else
    const unsigned fog=0;
#if RE4DC_NATIVE_FOG
    c.gen.fog_type=PVR_FOG_TABLE;
#endif
#endif
    pvr_poly_hdr_t expected;pvr_poly_compile(&expected,&c);
#if RE4DC_PS2_WORLD_HDR_CACHE
    if(RE4DC_PS2_HDR_ON){
        const unsigned size=k[2]|k[3]<<16,mode=k[5]<<2|fog<<4|0x100U;
        const unsigned set=(k[0]^(k[1]>>7)^(k[1]<<3)^(k[5]*0x3c1U))&(kPs2HdrSets-1U);
        for(const auto& slot:ps2_hdr[set])if(slot.mode==mode && slot.crc==k[0] && slot.fnv==k[1] && slot.size==size){
            // PS2_UPLOAD_READY_BEGIN
#if RE4DC_PS2_UPLOAD_INCARNATION
            if(slot.entry!=resident || slot.texture!=address || !ps2_hdr_upload_current(slot,resident) || std::memcmp(slot.words,&expected,16))return 0;
#else
            if(slot.entry!=resident || slot.texture!=address || std::memcmp(slot.words,&expected,16))return 0;
#endif
            // PS2_UPLOAD_READY_END
        }
    }
#endif
    return 1;
#else
    (void)k;(void)minimum_scratch;return 0;
#endif
}
#endif

// WORLD_SUBMIT_BEGIN_IMPLEMENTATION
#if RE4DC_SCENERY_SUBMIT_BATCH
// One implementation for the ordinary and batched entry points: the cache,
// material gates, header modifiers and accounting below remain shared.
extern "C" __attribute__((noinline,noclone)) int re4dc_ps2_world_direct_begin_batch(const unsigned* k,Re4dcModelDirect* out,Re4dcWorldSubmitBatch* batch){
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    const re4dc::dsa24::Scope dsa_submit(re4dc::dsa24::Submit);
#endif
    struct FailedBegin {
        Re4dcWorldSubmitBatch* batch;bool accepted=false;
        ~FailedBegin(){if(!accepted)re4dc_ps2_world_batch_close(batch);}
    } failed_begin{batch};
#else
extern "C" int re4dc_ps2_world_direct_begin(const unsigned* k,Re4dcModelDirect* out){
#endif
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    sob33_barrier(re4dc::sob33::ForeignDirect);
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    re4dc::wc24::Scope wc24_material(re4dc::wc24::HeaderMaterial);
#endif
#if RE4DC_TA_MATERIAL_DIAG
#if RE4DC_SCENERY_SUBMIT_BATCH
    re4dc_ps2_world_batch_close(batch);
#endif
    tamat::Scope source_scope(1);
#endif
#if RE4DC_TA_DIRECT
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    // A claimed group's validity walk can log and mutate failure state itself.
    // Its ordinary unlocked entry boundary must precede the predicate too.
    if(batch && batch->sq && re4dc_source_world_group_claimed())re4dc_ps2_world_batch_close(batch);
    if(!re4dc_source_world_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_source_world_binding_failed();return 0;}
#else
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif
#endif
    if(direct_open){RE4DC_WHD(1);re4dc_missing("native direct part nested");return 0;}
#if RE4DC_SCENERY_SUBMIT_BATCH
    // ensure_model_storage may allocate and log only when the slab is absent.
    if(!model_packets)re4dc_ps2_world_batch_close(batch);
#endif
#if RE4DC_WORLD_HOLE_DIAG
    whd_why=(!k || !out || k[4]>2 || k[5]>2)?10U:!frame_ready?2U:stream_aborted?3U:!ensure_model_storage()?4U:
            model_used+32>kModelPacketBytes/32?5U:0U;
    if(whd_why)return 0;
#else
    if(!k || !out || k[4]>2 || k[5]>2 || !frame_ready || stream_aborted ||
       !ensure_model_storage() || model_used+32>kModelPacketBytes/32)return 0;
#endif
#if RE4DC_UI_POLY_ORDER && RE4DC_SS_UI_ORDER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(ui_order && quads_flushed<nquad){re4dc_ps2_world_batch_close(batch);ui_order_flush();}
#else
    if(ui_order && quads_flushed<nquad)ui_order_flush();
#endif
    if(stream_aborted)return 0;
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!re4dc_r11f_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_r11f_binding_failed();return 0;}
#else
    if(!re4dc_r11f_binding_valid()){re4dc_r11f_binding_failed();return 0;}
#endif
#endif
    const Key key{k[0],k[1]};
#if RE4DC_WORLD_RECT21
    float rect_u=1.0f,rect_v=1.0f;
    // The selected representation owns its UV rule. Repeat-square scales the
    // short axis; filtered shorter-square keeps normalized UVs unchanged.
    // Never infer either rule from a dimension mismatch alone.
    const auto rect_scale=[&](const Entry& entry){
        const auto& t=entry.package.textures()[0];
        if(t.width==k[2] && t.height==k[3])return true;
        return re4dc::rect21::adapt(k[0],k[1],k[2],k[3],
            {t.width,t.height,t.format,t.flags,t.payload,t.data_size,entry.package.header().payload_crc32},
            rect_u,rect_v,true);
    };
#endif
#if RE4DC_PS2_WORLD_PREFLIGHT_DIAG
#if RE4DC_SCENERY_SUBMIT_BATCH
    re4dc_ps2_world_batch_close(batch);
#endif
    sourceWorldDiagBind(key); // before a cache hit or a load, and before SQ lock
#endif
#if RE4DC_PS2_WORLD_HDR_CACHE
    const bool hdr_on=RE4DC_PS2_HDR_ON;
    unsigned hdr_size=0,hdr_mode=0,hdr_set=0;Ps2HdrSlot* hit=nullptr;
    if(hdr_on){
        // The fog latch changes only at the scenery draw (native_ps2_world.cpp), never inside stream_select.
#if RE4DC_NATIVE_FOG && RE4DC_PS2_WORLD_FOG_SOURCE
        const unsigned hdr_fog=re4dc_ps2_world_fog()?1U:0U;
#else
        const unsigned hdr_fog=0;
#endif
        hdr_size=k[2]|k[3]<<16;hdr_mode=k[4]|k[5]<<2|hdr_fog<<4|0x100U;
        hdr_set=(k[0]^(k[1]>>7)^(k[1]<<3)^(k[4]*0x9e5U)^(k[5]*0x3c1U))&(kPs2HdrSets-1U);
        if(frame-ps2_hdr_log>=600U){
#if RE4DC_SCENERY_SUBMIT_BATCH
            re4dc_ps2_world_batch_close(batch);
#endif
            ps2_hdr_log=frame;
#if RE4DC_PS2_WORLD_HDR_CACHE==2
            re4dc_log("PS2HDR frame=%u hits=%u fills=%u checked=%u mismatched=%u\n",frame,ps2_hdr_hits,ps2_hdr_fills,ps2_hdr_checked,ps2_hdr_bad);
#elif RE4DC_SCENERY_PIECE_STATE
            re4dc_log("PS2HDR frame=%u hits=%u fills=%u piece_hits=%u\n",frame,ps2_hdr_hits,ps2_hdr_fills,ps2_piece_hits);
#else
            re4dc_log("PS2HDR frame=%u hits=%u fills=%u\n",frame,ps2_hdr_hits,ps2_hdr_fills);
#endif
        }
#if RE4DC_SCENERY_PIECE_STATE
        // SCENERY_PIECE_STATE: the part's slot word (room file SCPS) names its slot: no set scan when it still holds
        // this key (the entry / VRAM address test below applies as for any hit)
        if(re4dc_ps2_piece_slot && *re4dc_ps2_piece_slot && *re4dc_ps2_piece_slot<=kPs2HdrSets*kPs2HdrWays){
            Ps2HdrSlot& s=(&ps2_hdr[0][0])[*re4dc_ps2_piece_slot-1U];
            // PS2_UPLOAD_PIECE_BEGIN
#if RE4DC_PS2_UPLOAD_INCARNATION
            if(s.mode==hdr_mode && s.crc==k[0] && s.fnv==k[1] && s.size==hdr_size && ps2_hdr_upload_current(s,s.entry)){hit=&s;++ps2_piece_hits;}
#else
            if(s.mode==hdr_mode && s.crc==k[0] && s.fnv==k[1] && s.size==hdr_size){hit=&s;++ps2_piece_hits;}
#endif
            // PS2_UPLOAD_PIECE_END
        }
        if(!hit)
#endif
        for(auto& s:ps2_hdr[hdr_set])
            if(s.mode==hdr_mode && s.crc==k[0] && s.fnv==k[1] && s.size==hdr_size){hit=&s;break;}
#if RE4DC_SCENERY_PIECE_STATE
        if(hit && re4dc_ps2_piece_slot)*re4dc_ps2_piece_slot=unsigned(hit-&ps2_hdr[0][0])+1U;
#endif
    }
#if RE4DC_WORLD_RECT21
    if(hit && hit->entry->valid && hit->entry->key==key){
        const auto& resident=hit->entry->package.textures()[0];
        if(!re4dc::rect21::header_dimensions(hit->words[2],RE4DC_TSP_W(resident),RE4DC_TSP_H(resident)))hit=nullptr;
    }
#endif
    // PS2_UPLOAD_HIT_BEGIN
#if RE4DC_PS2_UPLOAD_INCARNATION
    if(hit && hit->entry->valid && hit->entry->key==key && hit->entry->package.pvr_texture(0)==hit->texture && ps2_hdr_upload_current(*hit,hit->entry)){
#else
    if(hit && hit->entry->valid && hit->entry->key==key && hit->entry->package.pvr_texture(0)==hit->texture){
#endif
    // PS2_UPLOAD_HIT_END
        const Ps2HdrSlot& slot=*hit;
        Entry* const handle=slot.entry;
#if RE4DC_WORLD_RECT21
        // The same complete descriptor gate runs on hot and cold paths, before
        // any header reaches the TA. Top-level drops or replaced data reject.
        if(!rect_scale(*handle)){RE4DC_WHD(7);return 0;}
#endif
        {constexpr bool pin=false;RE4DC_TOUCH(*handle);} // load()'s hit bookkeeping (pin=false)
        const unsigned pass=k[4];
        const pvr_list_t list=pass==0?PVR_LIST_OP_POLY:pass==1?PVR_LIST_PT_POLY:PVR_LIST_TR_POLY;
#if RE4DC_SCENERY_SUBMIT_BATCH
        if(!stream_scene || stream_list!=list
#if RE4DC_UI_POLY_ORDER
           || ui_order
#endif
        )re4dc_ps2_world_batch_close(batch);
#endif
        stream_select(list);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!re4dc_source_world_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_source_world_binding_failed();return 0;}
#else
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif
#endif

#if RE4DC_PS2_WORLD_R11F_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
        if(!re4dc_r11f_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_r11f_binding_failed();return 0;}
#else
        if(!re4dc_r11f_binding_valid()){re4dc_r11f_binding_failed();return 0;}
#endif
#endif
#if RE4DC_WORLD_AUTOSORT
#if RE4DC_SCENERY_SUBMIT_BATCH
        if(!world_autosort)re4dc_ps2_world_batch_close(batch);
#endif
        world_sort_begin();
#endif
        if(stream_aborted){RE4DC_WHD(8);return 0;}
        pvr_poly_hdr_t header;
        auto* hw=reinterpret_cast<std::uint32_t*>(&header);
        for(unsigned i=0;i<4;++i){hw[i]=slot.words[i];hw[4+i]=0;}
        ++model_header_hits;++ps2_hdr_hits;
#if RE4DC_PS2_WORLD_HDR_CACHE==2
        // =2 (diagnostic): the uncached lookup and compile beside every hit; a different Entry or word is counted.
        {
            const Re4dcUiImage image{&key,nullptr,k[2],k[3],5,0,0};
            Entry* const ref_handle=load(image,false,&key);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!re4dc_source_world_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_source_world_binding_failed();return 0;}
#else
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif
#endif

#if RE4DC_PS2_WORLD_R11F_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
            if(!re4dc_r11f_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_r11f_binding_failed();return 0;}
#else
            if(!re4dc_r11f_binding_valid()){re4dc_r11f_binding_failed();return 0;}
#endif
#endif
            bool bad=ref_handle!=handle;
            if(!bad){
                const auto& t=ref_handle->package.textures()[0];
                pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,list,re4dc::texture::pvr_format(t),RE4DC_TSP_W(t),RE4DC_TSP_H(t),ref_handle->package.pvr_texture(0),PVR_FILTER_BILINEAR);
                const pvr_cull_mode_t cull[]={PVR_CULLING_NONE,PVR_CULLING_CCW,PVR_CULLING_CW};
                c.gen.culling=cull[k[5]];
                c.depth.comparison=PVR_DEPTHCMP_GEQUAL;
                c.depth.write=pass==2?PVR_DEPTHWRITE_DISABLE:PVR_DEPTHWRITE_ENABLE;
                c.blend.src=(pass==2 || (RE4DC_PT_BLEND_FIX && pass==1))?PVR_BLEND_SRCALPHA:PVR_BLEND_ONE;
                c.blend.dst=(pass==2 || (RE4DC_PT_BLEND_FIX && pass==1))?PVR_BLEND_INVSRCALPHA:PVR_BLEND_ZERO;
                c.txr.env=PVR_TXRENV_MODULATEALPHA;
                c.txr.alpha=pass?PVR_TXRALPHA_ENABLE:PVR_TXRALPHA_DISABLE;
                c.txr.uv_clamp=PVR_UVCLAMP_NONE;
#if RE4DC_NATIVE_FOG && RE4DC_PS2_WORLD_FOG_SOURCE
                c.gen.fog_type=re4dc_ps2_world_fog()?PVR_FOG_TABLE:PVR_FOG_DISABLE;
#elif RE4DC_NATIVE_FOG
                c.gen.fog_type=PVR_FOG_TABLE;
#endif
                pvr_poly_hdr_t ref;pvr_poly_compile(&ref,&c);
                bad=std::memcmp(&ref,&header,16)!=0; // words 0..3: pvr_poly_compile leaves 4..7 unset
            }
            ++ps2_hdr_checked;
            if(bad && ++ps2_hdr_bad<=8)re4dc_log("PS2HDR mismatch frame=%u key=%08x-%08x pass=%u cull=%u entry=%d/%d\n",
                frame,k[0],k[1],pass,k[5],int(handle-entries),ref_handle?int(ref_handle-entries):-1);
        }
#endif
#if RE4DC_PS2_INTERIOR_CULL==2
        if(re4dc_ps2_check_header)ps2_check_header(header);
#endif
#if defined(RE4DC_SKY_FAR) || defined(RE4DC_LOOK_TOGGLE)
        if(re4dc_ps2_sky_header)ps2_sky_header(header);
#endif
#if RE4DC_MV_SHADOWS
        if(re4dc_mv_receiver && list==PVR_LIST_OP_POLY
#if RE4DC_UI_POLY_ORDER
            && !ui_order
#endif
        ){reinterpret_cast<std::uint32_t*>(&header)[0]|=PVR_TA_CMD_MODIFIER;++mv_receivers;}
#endif

#if RE4DC_UI_POLY_ORDER
        ui_order_polygon_header(header);
#endif
        std::uint32_t count;re4dc::render::begin_pvr_packet(model_packets+model_used,count,header);
        RE4DC_GAD_HIT(handle->key);RE4DC_PART_DUMP_KEY(handle->key);
    RE4DC_GCA_MODEL_PREPARE(nullptr);model_pending=model_used+count;model_handle=handle;
#if RE4DC_SCENERY_SUBMIT_BATCH
        if(!stream_scene){re4dc_ps2_world_batch_close(batch);stream_open();}
#else
        if(!stream_scene)stream_open();
#endif
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!re4dc_source_world_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_source_world_binding_failed();return 0;}
#else
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif
#endif

#if RE4DC_PS2_WORLD_R11F_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
        if(!re4dc_r11f_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_r11f_binding_failed();return 0;}
#else
        if(!re4dc_r11f_binding_valid()){re4dc_r11f_binding_failed();return 0;}
#endif
#endif
#if RE4DC_SCENERY_SUBMIT_BATCH
        auto* sq=batch && batch->sq?batch->sq:static_cast<std::uint32_t*>(static_cast<void*>(sq_lock((void*)PVR_TA_INPUT)));
        if(batch)batch->sq=sq;
#else
        auto* sq=static_cast<std::uint32_t*>(static_cast<void*>(sq_lock((void*)PVR_TA_INPUT)));
#endif
#if RE4DC_PS2_PVS_BATCH_COMPOSE
        sourceWorldDiagnosticSqHeld=true;
#endif
        const auto* words=reinterpret_cast<const std::uint32_t*>(model_packets+model_used);
        for(unsigned i=0;i<8;++i)sq[i]=words[i];
#if RE4DC_TA_HASH
        re4dc_ta_hash(words,32);
#endif
        sq_flush(sq);
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        re4dc::wc24::submitted_header(words);
#endif
        direct_open=true;
        model_handle->frame=frame; // the header is in the TA: pinned for this scene
#if RE4DC_PS2_WORLD_SOURCE_TEX_PREP
        sourceWorldTextureAcquired(key);
#endif
        ++frame_pvr_calls;frame_pvr_bytes+=32;stream_model_bytes+=32;
        out->sq=sq+8;out->scratch=model_packets+model_pending;out->scratch_capacity=kModelPacketBytes/32-model_pending;
#if RE4DC_WORLD_RECT21
        out->u_scale=rect_u;out->v_scale=rect_v;
#else
        out->u_scale=out->v_scale=1;
#endif
#if RE4DC_SCENERY_SUBMIT_BATCH
        failed_begin.accepted=true;
#endif
        return 1;
    }
#endif
    const Re4dcUiImage image{&key,nullptr,k[2],k[3],5,0,0};
#if RE4DC_WORLD_HOLE_DIAG
    whd_load_why="other";
#endif
#if RE4DC_SCENERY_SUBMIT_BATCH
    re4dc_ps2_world_batch_close(batch);
#endif
    Entry* handle=load(image,false,&key);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!re4dc_source_world_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_source_world_binding_failed();return 0;}
#else
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif
#endif

#if RE4DC_PS2_WORLD_R11F_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!re4dc_r11f_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_r11f_binding_failed();return 0;}
#else
    if(!re4dc_r11f_binding_valid()){re4dc_r11f_binding_failed();return 0;}
#endif
#endif
    if(!handle || !frame_ready || stream_aborted || direct_open){RE4DC_WHD(!handle?6U:!frame_ready?2U:stream_aborted?3U:1U);++model_texture_rejects;return 0;}
    const auto& t=handle->package.textures()[0];
#if RE4DC_WORLD_RECT21
    if(!rect_scale(*handle)){RE4DC_WHD(7);return 0;}
#else
    if(t.width!=k[2] || t.height!=k[3]){RE4DC_WHD(7);return 0;} // repeated UVs cannot use padding
#endif
    const unsigned pass=k[4];
    const pvr_list_t list=pass==0?PVR_LIST_OP_POLY:pass==1?PVR_LIST_PT_POLY:PVR_LIST_TR_POLY;
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!stream_scene || stream_list!=list
#if RE4DC_UI_POLY_ORDER
       || ui_order
#endif
    )re4dc_ps2_world_batch_close(batch);
#endif
    stream_select(list);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!re4dc_source_world_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_source_world_binding_failed();return 0;}
#else
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif
#endif

#if RE4DC_PS2_WORLD_R11F_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!re4dc_r11f_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_r11f_binding_failed();return 0;}
#else
    if(!re4dc_r11f_binding_valid()){re4dc_r11f_binding_failed();return 0;}
#endif
#endif
#if RE4DC_WORLD_AUTOSORT
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!world_autosort)re4dc_ps2_world_batch_close(batch);
#endif
    world_sort_begin();
#endif
    if(stream_aborted){RE4DC_WHD(8);return 0;}
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,list,re4dc::texture::pvr_format(t),RE4DC_TSP_W(t),RE4DC_TSP_H(t),handle->package.pvr_texture(0),PVR_FILTER_BILINEAR);
    const pvr_cull_mode_t cull[]={PVR_CULLING_NONE,PVR_CULLING_CCW,PVR_CULLING_CW};
    c.gen.culling=cull[k[5]];
    c.depth.comparison=PVR_DEPTHCMP_GEQUAL;
    c.depth.write=pass==2?PVR_DEPTHWRITE_DISABLE:PVR_DEPTHWRITE_ENABLE;
    c.blend.src=(pass==2 || (RE4DC_PT_BLEND_FIX && pass==1))?PVR_BLEND_SRCALPHA:PVR_BLEND_ONE;
    c.blend.dst=(pass==2 || (RE4DC_PT_BLEND_FIX && pass==1))?PVR_BLEND_INVSRCALPHA:PVR_BLEND_ZERO;
    c.txr.env=PVR_TXRENV_MODULATEALPHA;
    c.txr.alpha=pass?PVR_TXRALPHA_ENABLE:PVR_TXRALPHA_DISABLE;
    c.txr.uv_clamp=PVR_UVCLAMP_NONE;
#if RE4DC_NATIVE_FOG && RE4DC_PS2_WORLD_FOG_SOURCE
    c.gen.fog_type=re4dc_ps2_world_fog()?PVR_FOG_TABLE:PVR_FOG_DISABLE; // source GX fog at the scenery draw
#elif RE4DC_NATIVE_FOG
    c.gen.fog_type=PVR_FOG_TABLE;
#endif
    pvr_poly_hdr_t header;pvr_poly_compile(&header,&c);DFA26_COUNT(model_header_builds,PacketHeaderBuild);
#if RE4DC_PS2_WORLD_HDR_CACHE
    if(hdr_on){
        auto* hw=reinterpret_cast<std::uint32_t*>(&header);
        hw[4]=hw[5]=hw[6]=hw[7]=0; // never written by pvr_poly_compile here (stack contents before; unused by the PVR)
        // The key's stale slot if it has one, else the set's next slot in turn.
        Ps2HdrSlot& slot=hit?*hit:ps2_hdr[hdr_set][ps2_hdr_next[hdr_set]++%kPs2HdrWays];
        slot.crc=k[0];slot.fnv=k[1];slot.size=hdr_size;slot.mode=hdr_mode;slot.entry=handle;
        slot.texture=handle->package.pvr_texture(0);
#if RE4DC_PS2_UPLOAD_INCARNATION
        slot.upload_incarnation=handle->upload_incarnation;
#endif
        for(unsigned i=0;i<4;++i)slot.words[i]=hw[i];
        ++ps2_hdr_fills;
#if RE4DC_SCENERY_PIECE_STATE
        if(re4dc_ps2_piece_slot)*re4dc_ps2_piece_slot=unsigned(&slot-&ps2_hdr[0][0])+1U;
#endif
    }
#endif
#if RE4DC_PS2_INTERIOR_CULL==2
    if(re4dc_ps2_check_header)ps2_check_header(header);
#endif
#if defined(RE4DC_SKY_FAR) || defined(RE4DC_LOOK_TOGGLE)
    if(re4dc_ps2_sky_header)ps2_sky_header(header);
#endif
#if RE4DC_MV_SHADOWS
    if(re4dc_mv_receiver && list==PVR_LIST_OP_POLY
#if RE4DC_UI_POLY_ORDER
            && !ui_order
#endif
        ){reinterpret_cast<std::uint32_t*>(&header)[0]|=PVR_TA_CMD_MODIFIER;++mv_receivers;}
#endif

#if RE4DC_UI_POLY_ORDER
    ui_order_polygon_header(header);
#endif
    std::uint32_t count;re4dc::render::begin_pvr_packet(model_packets+model_used,count,header);
    RE4DC_GAD_HIT(handle->key);RE4DC_PART_DUMP_KEY(handle->key);
    RE4DC_GCA_MODEL_PREPARE(nullptr);model_pending=model_used+count;model_handle=handle;
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!stream_scene){re4dc_ps2_world_batch_close(batch);stream_open();}
#else
    if(!stream_scene)stream_open();
#endif
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!re4dc_source_world_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_source_world_binding_failed();return 0;}
#else
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif
#endif

#if RE4DC_PS2_WORLD_R11F_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!re4dc_r11f_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_r11f_binding_failed();return 0;}
#else
    if(!re4dc_r11f_binding_valid()){re4dc_r11f_binding_failed();return 0;}
#endif
#endif
#if RE4DC_SCENERY_SUBMIT_BATCH
    auto* sq=batch && batch->sq?batch->sq:static_cast<std::uint32_t*>(static_cast<void*>(sq_lock((void*)PVR_TA_INPUT)));
    if(batch)batch->sq=sq;
#else
    auto* sq=static_cast<std::uint32_t*>(static_cast<void*>(sq_lock((void*)PVR_TA_INPUT)));
#endif
#if RE4DC_PS2_PVS_BATCH_COMPOSE
    sourceWorldDiagnosticSqHeld=true;
#endif
    const auto* words=reinterpret_cast<const std::uint32_t*>(model_packets+model_used);
    for(unsigned i=0;i<8;++i)sq[i]=words[i];
#if RE4DC_TA_HASH
    re4dc_ta_hash(words,32);
#endif
    sq_flush(sq);
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    re4dc::wc24::submitted_header(words);
#endif
    direct_open=true;
    model_handle->frame=frame; // the header is in the TA: pinned for this scene
#if RE4DC_PS2_WORLD_SOURCE_TEX_PREP
        sourceWorldTextureAcquired(key);
#endif
    ++frame_pvr_calls;frame_pvr_bytes+=32;stream_model_bytes+=32;
    out->sq=sq+8;out->scratch=model_packets+model_pending;out->scratch_capacity=kModelPacketBytes/32-model_pending;
#if RE4DC_WORLD_RECT21
    out->u_scale=rect_u;out->v_scale=rect_v;
#else
    out->u_scale=out->v_scale=1;
#endif
#if RE4DC_SCENERY_SUBMIT_BATCH
    failed_begin.accepted=true;
#endif
    return 1;
#else
    (void)k;(void)out;return 0;
#endif
}
#if RE4DC_SCENERY_SUBMIT_BATCH
extern "C" int re4dc_ps2_world_direct_begin(const unsigned* k,Re4dcModelDirect* out){
    return re4dc_ps2_world_direct_begin_batch(k,out,nullptr);
}
#endif
// WORLD_SUBMIT_BEGIN_IMPLEMENTATION_END
#if RE4DC_WORLD_HOLE_DIAG
// WORLD_HOLE_DIAG: the last refusal of re4dc_ps2_world_direct_begin (0 none) and load()'s reason text; cleared.
extern "C" unsigned re4dc_whd_abort(void** ra,unsigned* q){
    if(whd_abort_frame!=frame)return 0;
    *ra=whd_abort_ra;for(unsigned i=0;i<6;++i)q[i]=whd_abort_q[i];
    return whd_abort_kind;
}
extern "C" unsigned re4dc_whd_take(const char** load_why,unsigned* used,unsigned* overflow){
    const unsigned w=whd_why;whd_why=0;
    *load_why=w==6?whd_load_why:nullptr;*used=model_used;*overflow=model_overflow;
    return w;
}
#endif
#endif
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
extern "C" int re4dc_source_world_op_window(){
    return frame_ready && !stream_aborted && !direct_open && !model_used && !source_draws_finished &&
        (!stream_scene || (!(stream_closed_lists&(1U<<PVR_LIST_OP_POLY)) && stream_list==PVR_LIST_OP_POLY));
}
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
extern "C" int re4dc_r11f_op_window() {
    return frame_ready && !stream_aborted && !direct_open && !model_used && !source_draws_finished &&
        (!stream_scene || (!(stream_closed_lists&(1U<<PVR_LIST_OP_POLY)) && stream_list==PVR_LIST_OP_POLY));
}
extern "C" unsigned re4dc_r11f_packet_bytes(){return stream_model_bytes;}
namespace {
struct R11fSourceFinishScope {
    ~R11fSourceFinishScope(){re4dc_r11f_source_finished(frame,source_draws_finished,stream_aborted);}
};
}
#endif
extern "C" void re4dc_model_finish_source_draws(){
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    // This queue also contains UI, effects, water and post-processing nodes.
    // Only the actual model branch below belongs to the model-list bucket.
    const re4dc::dsa24::Scope dsa_drain(re4dc::dsa24::RenderOther);
#endif
    AVD_EVENT(FinishBegin,nullptr,nullptr,0);
    RE4DC_PROFILE_SCOPE(TranslucentDrain);
#if RE4DC_PS2_WORLD_R11F_OWNER
    R11fSourceFinishScope r11fFinishScope;
    if(!re4dc_r11f_barrier(frame))return;
#endif
#if RE4DC_TREE_IMPOSTOR
    re4dc_static_flush_impostors(); // PT list, between the OP pass and the TR drain
#if RE4DC_COARSE_WORLD & 8
    re4dc_coarse_world_flush();     // COARSE_WORLD trees (coarse_world.cpp): the same PT window
#endif
#endif
#if RE4DC_PS2_WORLD_DRAW
    re4dc_ps2_world_flush(); // after all existing PT, before ordinary source TR
#endif
#if RE4DC_D349_RENDERER_STACK
    if(!deferred_first){source_draws_finished=true;AVD_EVENT(FinishEnd,nullptr,nullptr,1);return;}
    draining_parts=true;
    // Current PVR setup enables OP/TR only. Do not submit a dummy PT list:
    // pinned KOS compares completed-list bits to exactly the enabled-list mask.
    // A future qualified PT material must also budget/enable that list.
    stream_select(PVR_LIST_TR_POLY);draining_list=PVR_LIST_TR_POLY;
    while(deferred_first && !stream_aborted){
        AVD_EVENT(Drain,deferred_first,nullptr,unsigned(uintptr_t(deferred_first->lighting)));
#if RE4DC_ACTOR_GANADO_DEATH_FADE
#if RE4DC_ACTOR_TRANSACTION_DIAG
        if(actor_fade_queue_seen)re4dc_log("AFD_FIFO visit ep=%u i=%u node=%p next=%p tag=%p\n",actor_fade_queue_epoch,
            actor_fade_queue_walk++,deferred_first,deferred_first->next,deferred_first->lighting);
#endif
        if(actor_fade_drain_head())continue;
#endif
#if RE4DC_SUBSCREEN && RE4DC_PVR_STREAM
        if(deferred_first->lighting==kSubscreenQuadTag){
#if RE4DC_TA_MATERIAL_DIAG
    tamat::Scope source_scope(3);
#endif
            const auto* packet=reinterpret_cast<const unsigned char*>(deferred_first)+kSubscreenQuadNode;
            const unsigned bytes=deferred_first->changed[0];
            deferred_first=deferred_first->next;stream_send(packet,bytes);continue;
        }
#if defined(RE4DC_WATER_PS2) && RE4DC_WATER_PS2
        if(deferred_first->lighting==kWaterTag){   // WATER_PS2: the layer's vertices are generated here
            const auto* w=reinterpret_cast<const WaterNode*>(reinterpret_cast<const unsigned char*>(deferred_first)+kWaterNode);
            deferred_first=deferred_first->next;water_emit(*w);continue;
        }
#endif
#endif
#if RE4DC_EFFECT_SPRITES
#if defined(RE4DC_FX_STRIP21) && RE4DC_FX_STRIP21
        if(deferred_first->lighting==kEffectQuad21Tag){
            const auto* packet=reinterpret_cast<const unsigned char*>(deferred_first)+kEffectQuad21Node;
            const unsigned bytes=deferred_first->changed[0];
#if defined(RE4DC_CLOTH_PUBLICATION11) && RE4DC_CLOTH_PUBLICATION11
            // Effect-tag nodes use changed[0] only, never restore_view masks.
            // Other effect producers value-initialize this unused token to 0.
            const unsigned cloth_observation=deferred_first->changed[1];
#endif
            deferred_first=deferred_first->next;gcasset_fx_stream_send(packet,bytes);
#if defined(RE4DC_CLOTH_PUBLICATION11) && RE4DC_CLOTH_PUBLICATION11
            re4dc_cloth_publication11.drain(cloth_observation,frame,stream_aborted);
#endif
            continue;
        }
#endif
#if defined(RE4DC_ESP_SETUP_BATCH)
        if(deferred_first->lighting==kSpriteTag || deferred_first->lighting==kSpriteBodyTag){
            auto* packet=reinterpret_cast<unsigned char*>(deferred_first)+kSpriteNode;
            const bool screen=deferred_first->changed[0]!=0;
            const bool body_only=deferred_first->lighting==kSpriteBodyTag;
            deferred_first=deferred_first->next;fx_send(packet,screen,body_only);continue;
        }
#else
        if(deferred_first->lighting==kSpriteTag){
            auto* packet=reinterpret_cast<unsigned char*>(deferred_first)+kSpriteNode;
            const bool screen=deferred_first->changed[0]!=0;
            deferred_first=deferred_first->next;fx_send(packet,screen);continue;
        }
#endif
#if RE4DC_FX_SPRITE_TRIM
        if(deferred_first->lighting==kFxOctTag){   // FX_SPRITE_TRIM octagon (fx_sprite_trim.inc)
#if RE4DC_TA_MATERIAL_DIAG
    tamat::Scope source_scope(4);
#endif
            const auto* packet=reinterpret_cast<const unsigned char*>(deferred_first)+kSpriteNode;
#if RE4DC_TA_BIN_DIAG
            tabin::skip_fill=true;
#endif
            deferred_first=deferred_first->next;gcasset_fx_stream_send(packet,kFxOctPacket);
#if RE4DC_TA_BIN_DIAG
            tabin::skip_fill=false;
#endif
            continue;
        }
#endif
#if defined(RE4DC_EFFECT_HAZE_LEAN) && (RE4DC_EFFECT_HAZE_LEAN & 4)
        if(deferred_first->lighting==kOctTag){
#if RE4DC_TA_MATERIAL_DIAG
    tamat::Scope source_scope(4);
#endif
            const auto* packet=reinterpret_cast<const unsigned char*>(deferred_first)+kSpriteNode;
#if RE4DC_TA_BIN_DIAG
            tabin::skip_fill=true;
#endif
            deferred_first=deferred_first->next;gcasset_fx_stream_send(packet,kOctPacket);
#if RE4DC_TA_BIN_DIAG
            tabin::skip_fill=false;
#endif
            continue;
        }
#endif
#if defined(RE4DC_NATIVE_LASER) && RE4DC_NATIVE_LASER
        if(deferred_first->lighting==kLineTag){
#if RE4DC_TA_MATERIAL_DIAG
    tamat::Scope source_scope(4);
#endif
            const auto* packet=reinterpret_cast<const unsigned char*>(deferred_first)+kSpriteNode;
            deferred_first=deferred_first->next;stream_send(packet,kLinePacket);continue;
        }
#endif
#endif
#if defined(RE4DC_LOOK_TOGGLE)
        if(deferred_first->lighting==kGradeTag){
#if RE4DC_TA_MATERIAL_DIAG
    tamat::Scope source_scope(4);
#endif
            auto* packet=reinterpret_cast<unsigned char*>(deferred_first)+kGradeNode;
            const unsigned bytes=deferred_first->changed[0];
            deferred_first=deferred_first->next;grade_send(packet,bytes);continue;
        }
#endif
#if RE4DC_POST_F00
        if(deferred_first->lighting==kPostTag){
            auto* packet=reinterpret_cast<unsigned char*>(deferred_first)+kPostNode;
            const unsigned bytes=deferred_first->changed[0];
            deferred_first=deferred_first->next;post_send(packet,bytes);continue;
        }
#endif
        // Copy the small view before I/O can yield. Retirement clears the queue
        // and aborts this same frame; it never frees an in-flight PVR texture.
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
        const re4dc::dsa24::Scope dsa_model(re4dc::dsa24::ModelList);
#endif
        Re4dcModelPart view=restore_view(deferred_first);
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
        const re4dc::dsa24::x28::ModelScope dsa28_model(view.model);
#endif
#if RE4DC_GC_ASSET_MOTION_UNKNOWN
        re4dc_gcasset::MotionUnknownScope gcasset_motion_scope(re4dc_gcasset::MotionDelayedModel|re4dc_gcasset::MotionViewTrack);
#endif
#if RE4DC_GC_ASSET_GATE
        re4dc_gcasset::ReplayScope gcasset_replay_scope(deferred_first->asset_serial,deferred_first->asset_mask,deferred_first->asset_payload);
#endif
        AVD_EVENT(DrainModel,deferred_first,&view,0);
#if RE4DC_ACTOR_GANADO_DEATH_FADE && RE4DC_ACTOR_TRANSACTION_DIAG
        if(actor_fade_queue_seen)re4dc_log("AFD_FIFO model ep=%u node=%p m=%p info=%p part=%p alpha=%08x\n",
            actor_fade_queue_epoch,deferred_first,view.model,view.info,view.part,view.alpha_state);
#endif
        const auto* saved_lighting=deferred_first->lighting;
        deferred_first=deferred_first->next;
#if RE4DC_COPY_LEAN
        if(saved_lighting){
            SourceLighting lighting;restore_lighting_into(saved_lighting,lighting);
            view.lighting=&lighting;re4dc_model_submit(&view);
        }else re4dc_model_submit(&view);
#else
        SourceLighting lighting{};
        if(saved_lighting){lighting=restore_lighting(saved_lighting);view.lighting=&lighting;}
        re4dc_model_submit(&view);
#endif
    }
    AVD_EVENT(FinishEnd,nullptr,nullptr,stream_aborted?3u:2u);
    draining_parts=false;source_draws_finished=true;reset_deferred();
#endif
}

extern "C" void re4dc_model_invalidate_pending(){
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    sob33_barrier(re4dc::sob33::SourceReset);
#endif
    re4dc_model_invalidate_static_lighting();
#if RE4DC_D349_RENDERER_STACK
    if(deferred_first || draining_parts){reset_deferred();stream_aborted=true;}
#endif
}

extern "C" void* re4dc_model_static_lighting_storage(unsigned* bytes){
    *bytes=model_packets?kModelStaticLightBytes:0;
    return *bytes?reinterpret_cast<unsigned char*>(model_packets)+kModelPacketBytes+kModelPreparationBytes:nullptr;
}

extern "C" const Re4dcNativeFrameStats* re4dc_native_frame_stats(){return &completed_frame;}

#if defined(RE4DC_FX_ROOM_SPILL_KB) && RE4DC_FX_ROOM_SPILL_KB
// FX_ROOM_SPILL_KB=<n> (mendezfx.mk; render only, #41 / #55): the frame queue's spill (asked for only once frame_storage is
// full) becomes an <n> KiB heap-4 room cell instead of the 8 KiB model-slab tail. It is allocated on the room's first
// overflow (rooms that never overflow pay nothing) under the native-static reserve rule, kept for the room and freed
// with the room's cells at room leave; a refused allocation falls back to the slab tail.
extern "C" void* re4dc_static_alloc(unsigned bytes);
extern "C" int re4dc_room4_state(unsigned* generation,unsigned* cells,unsigned* bytes,unsigned* stale,unsigned* refused);
namespace fxroomspill {
unsigned char* cell=nullptr;unsigned generation=~0U;bool tried=false;unsigned allocs=0,refusals=0;
}
#endif
extern "C" void* re4dc_model_deferred_storage(unsigned* bytes){
#if defined(RE4DC_FX_ROOM_SPILL_KB) && RE4DC_FX_ROOM_SPILL_KB
    {
        unsigned g,c,b,st,rf;
        if(re4dc_room4_state(&g,&c,&b,&st,&rf)){
            if(fxroomspill::generation!=g){fxroomspill::generation=g;fxroomspill::cell=nullptr;fxroomspill::tried=false;}
            if(!fxroomspill::cell && !fxroomspill::tried){
                fxroomspill::tried=true;
                auto* p=static_cast<unsigned char*>(re4dc_static_alloc(RE4DC_FX_ROOM_SPILL_KB*1024U+32U));
                if(p){fxroomspill::cell=reinterpret_cast<unsigned char*>((reinterpret_cast<std::uintptr_t>(p)+31U)&~std::uintptr_t(31));++fxroomspill::allocs;}
                else ++fxroomspill::refusals;
                re4dc_log("fx room spill: room=%03x generation=%u kib=%u %s allocs=%u refusals=%u\n",unsigned(re4dc_ps2_mesh_room()),g,
                    unsigned(RE4DC_FX_ROOM_SPILL_KB),p?"ok":"refused",fxroomspill::allocs,fxroomspill::refusals);
            }
            if(fxroomspill::cell){*bytes=RE4DC_FX_ROOM_SPILL_KB*1024U;return fxroomspill::cell;}
        }
    }
#endif
    *bytes=model_packets?kModelDeferredSpillBytes:0;
    return *bytes?reinterpret_cast<unsigned char*>(model_packets)+kModelPacketBytes+kModelPreparationBytes+kModelStaticLightBytes:nullptr;
}

#if defined(RE4DC_FX_R200_ENTRY_CAP) && RE4DC_FX_R200_ENTRY_CAP
// FX_R200_TAIL_ADAPTER_BEGIN
namespace {
#if defined(RE4DC_FRAME_QUEUE_DIAG) && RE4DC_FRAME_QUEUE_DIAG
unsigned fx_r200_attempts,fx_r200_grants,fx_r200_refused,fx_r200_reasons,fx_r200_frames,fx_r200_peak;
#endif
bool fx_r200_tail_select(unsigned required,unsigned char*& storage,unsigned*& top){
    re4dc::fx_r200::Context c{};
    c.room=re4dc_room_id_now();
    if(c.room==0x200U){
        unsigned cells,bytes,stale,refused;
        c.room_live=re4dc_room4_state(&c.generation,&cells,&bytes,&stale,&refused)!=0;
        c.room_cell=fxroomspill::cell;c.room_generation=fxroomspill::generation;
        c.room_bytes=RE4DC_FX_ROOM_SPILL_KB*1024U;
        c.spill=deferred_spill;c.spill_top=deferred_spill_top;c.spill_bytes=deferred_spill_capacity;
        c.tail=model_packets?reinterpret_cast<unsigned char*>(model_packets)+kModelPacketBytes+kModelPreparationBytes+kModelStaticLightBytes:nullptr;
        c.tail_bytes=model_packets?kModelDeferredSpillBytes:0;
    }
    const auto result=fx_r200_tail.select(c,required,storage,top);
#if defined(RE4DC_FRAME_QUEUE_DIAG) && RE4DC_FRAME_QUEUE_DIAG
    if(c.room==0x200U || fx_r200_tail.data){
        ++fx_r200_attempts;
        if(result==re4dc::fx_r200::Result::Accepted)++fx_r200_grants;
        else{++fx_r200_refused;fx_r200_reasons|=1U<<unsigned(result);}
    }
#endif
    return result==re4dc::fx_r200::Result::Accepted;
}
void fx_r200_tail_reset(){
#if defined(RE4DC_FRAME_QUEUE_DIAG) && RE4DC_FRAME_QUEUE_DIAG
    if(fx_r200_attempts){
        const unsigned used=fx_r200_tail.data?re4dc::fx_r200::kTailBytes-fx_r200_tail.top:0;
        fx_r200_peak=std::max(fx_r200_peak,used);++fx_r200_frames;
        if(fx_r200_frames<=96 || !(frame%120))
            re4dc_log("FQDIAG r200_tail frame=%u room=%03x used=%u/%u grants=%u refused=%u reasons=%03x peak=%u queues=%u\n",
                frame,re4dc_room_id_now(),used,re4dc::fx_r200::kTailBytes,fx_r200_grants,fx_r200_refused,fx_r200_reasons,fx_r200_peak,fx_r200_frames);
        fx_r200_attempts=fx_r200_grants=fx_r200_refused=fx_r200_reasons=0;
    }
#endif
    fx_r200_tail.reset();
}
} // namespace
// FX_R200_TAIL_ADAPTER_END
#endif

#if RE4DC_MOVIE_WORLD_ARENA || RE4DC_CABIN_SOURCE
#if RE4DC_CABIN_SOURCE
static int movie_cabin_ui_try_close_body(){
#else
extern "C" int re4dc_ui_movie_try_close(){
#endif
    // This path runs before source heap destruction: all checks are nonblocking.
#if RE4DC_CABIN_HANDOFF_DIAG
    unsigned blocked=(direct_open?1u:0u)|(stream_scene?2u:0u)|(pvr_state.ta_busy?4u:0u)|(pvr_state.render_busy?8u:0u);
#if RE4DC_D349_RENDERER_STACK
    if(draining_parts)blocked|=16u;
#endif
#if RE4DC_PVR_PIPELINE==2
    if(pvr_present_pending())blocked|=32u;
#elif RE4DC_PVR_PIPELINE
    if(present_submitted!=present_resolved)blocked|=32u;
#endif
#if RE4DC_PVR_PIPELINE
    if(present_failures)blocked|=64u;
#endif
    static unsigned calls=0,last=~0u;
    ++calls;
    if(calls<=3 || blocked!=last || calls%120==0)
        re4dc_log("CABIN_UI_CLOSE n=%u frame=%u blocked=%u tex=%08x picture=%u bg=%u upload=%u shown=%u\n",
            calls,frame,blocked,unsigned(reinterpret_cast<uintptr_t>(movie_texture)),unsigned(movie_picture),unsigned(movie_background),movie_upload_serial,movie_shown_serial);
    last=blocked;
#endif
    if(direct_open || stream_scene || pvr_state.ta_busy || pvr_state.render_busy)return 0;
#if RE4DC_D349_RENDERER_STACK
    if(draining_parts)return 0;
#endif
#if RE4DC_PVR_PIPELINE==2
    if(pvr_present_pending())return 0;
#elif RE4DC_PVR_PIPELINE
    if(present_submitted!=present_resolved)return 0;
#endif
#if RE4DC_PVR_PIPELINE
    if(present_failures)return 0;
#endif
    movie_background=false;movie_picture=false;
    if(movie_texture){
#if RE4DC_GC_ASSET_GATE
        gcasset_movie_forget();
#endif
        pvr_mem_free(movie_texture);movie_texture=nullptr;
#if RE4DC_TEX_RESIDENT
        re4dc_ui_vram_unclaim();
#endif
    }
    return 1;
}
#if RE4DC_CABIN_SOURCE
// CABIN_UI_API_BEGIN
extern "C" int re4dc_ui_movie_try_close(){
    MovieCabinUiScope owner;if(!owner.held)return 0;
    return movie_cabin_ui_try_close_body();
}
extern "C" int re4dc_ui_movie_cabin_try_close(unsigned generation){
    MovieCabinUiScope owner;
    if(!owner.held || !movie_texture || !generation || generation!=movie_cabin_ui_epoch)return 0;
    return movie_cabin_ui_try_close_body();
}
#if RE4DC_CABIN_COMPLETE_HANDOFF
extern "C" int re4dc_ui_movie_cabin_complete(unsigned generation,const void* texture,unsigned final_upload,unsigned movie_generation){
    MovieCabinUiScope owner;
    const auto current=[&](){return generation && generation==movie_cabin_ui_epoch &&
        texture && texture==movie_texture && final_upload &&
        final_upload==movie_upload_serial && final_upload==movie_shown_serial &&
        movie_cabin_ui_close_fault!=generation && re4dc_movie_cabin_complete_current(movie_generation);};
    if(!owner.held || !ready || !current() || direct_open)return 0;
#if RE4DC_D349_RENDERER_STACK
    if(draining_parts)return 0;
    reset_deferred();source_draws_finished=true;
#endif
#if RE4DC_WORLD_SCRATCH
    re4dc_world_scratch_cancel();
#endif
    re4dc_ps2_world_movie_discard();stream_aborted=true;
#if RE4DC_PVR_STREAM
    if(stream_scene)stream_close(false);
    if(!current())return 0;
#endif
#if RE4DC_PVR_PIPELINE
    present_fence();
    if(!current())return 0;
#if RE4DC_PVR_PIPELINE==2
    if(pvr_present_pending())return 0;
#else
    if(present_submitted!=present_resolved)return 0;
#endif
    if(present_failures)return 0;
#endif
#if RE4DC_PVR_RECOVER
    if(!pvr_ready::wait_clear(pvr_state.ta_busy,"cabin complete TA",'K',pvr_ready::ta_timeouts) ||
       !current() ||
       !pvr_ready::wait_clear(pvr_state.render_busy,"cabin complete render",'Q',pvr_ready::render_timeouts))return 0;
#else
    if(re4dc::gpu::quiesce()!=re4dc::gpu::FenceResult::ready)return 0;
#endif
    if(!current())return 0;
    return movie_cabin_ui_try_close_body();
}
#endif
extern "C" unsigned re4dc_ui_movie_cabin_generation(){return movie_texture?movie_cabin_ui_epoch:0;}
extern "C" unsigned re4dc_ui_movie_cabin_upload(){return movie_upload_serial;}
extern "C" unsigned re4dc_ui_movie_cabin_shown(){return movie_shown_serial;}
// CABIN_UI_API_END
#endif
extern "C" int re4dc_ui_movie_handoff_ready(){
    if(!ready || movie_texture || direct_open)return 0;
#if RE4DC_D349_RENDERER_STACK
    if(draining_parts)return 0; // executing readers cannot be discarded
    reset_deferred();source_draws_finished=true;
#endif
#if RE4DC_WORLD_SCRATCH
    re4dc_world_scratch_cancel();
#endif
    re4dc_ps2_world_movie_discard();stream_aborted=true;
#if RE4DC_PVR_STREAM
    if(stream_scene)stream_close(false);
#endif
#if RE4DC_PVR_PIPELINE
    present_fence();
#if RE4DC_PVR_PIPELINE==2
    if(pvr_present_pending())return 0;
#else
    if(present_submitted!=present_resolved)return 0;
#endif
    if(present_failures)return 0;
#endif
#if RE4DC_PVR_RECOVER
    if(!pvr_ready::wait_clear(pvr_state.ta_busy,"movie arena TA",'K',pvr_ready::ta_timeouts) ||
       !pvr_ready::wait_clear(pvr_state.render_busy,"movie arena render",'Q',pvr_ready::render_timeouts))return 0;
#else
    if(re4dc::gpu::quiesce()!=re4dc::gpu::FenceResult::ready)return 0;
#endif
    return !stream_scene && !direct_open && !pvr_state.ta_busy && !pvr_state.render_busy;
}
#endif
#if RE4DC_ROUTE_MOVIES
extern "C" int re4dc_ui_movie_open(unsigned width,unsigned height){
#if RE4DC_WORLD_SCRATCH
    // Close admission immediately; the final synchronous borrower restores mode.
    re4dc_world_scratch_cancel();
#endif
#if RE4DC_CABIN_SOURCE
    MovieCabinUiScope owner;if(!owner.held || movie_cabin_ui_epoch==~0u)return 0;
#endif
    // Macroblock sizes inside the 512x256 texture; rows load as 32-byte blocks.
    if(movie_texture || !ready || !width || !height || width>512 || height>256 || (width&15))return 0;
#if RE4DC_CABIN_SOURCE
    ++movie_cabin_ui_epoch; // Failed attempts consume a generation too; never reuse one.
#endif
#if RE4DC_MOVIE_WINDOW
    // Only the picture's rows are allocated (1024-byte rows; v is clamped inside them, rows below are
    // never sampled): 288x192 needs 192 KiB of the 512x256 texture's 256 KiB.
    const unsigned movie_bytes=1024U*height;
#else
    const unsigned movie_bytes=512*256*2;
#endif
#if RE4DC_TEX_RESIDENT
    // Released with the texture (re4dc_ui_movie_close). The movie's claim may end this frame's
    // scene and release its uploads when nothing else frees a block (fallback in vram_claim).
#if RE4DC_CLAIM_TEST==3
    if(!vram_claim(movie_bytes,true)){re4dc_ui_vram_unclaim();return 0;} // test: the pre-fallback outcome
#else
    vram_claim(movie_bytes,true);
#endif
#endif
    movie_texture=pvr_mem_malloc(movie_bytes);movie_picture=false;movie_width=width;movie_height=height;
    movie_upload_serial=movie_shown_serial=movie_presentations=0;movie_first_picture_us=0;
#if RE4DC_TEX_RESIDENT
    if(!movie_texture)re4dc_ui_vram_unclaim();
#endif
#if RE4DC_CLAIM_TEST==4 && RE4DC_PVR_STREAM
    if(movie_texture && !stream_scene)stream_open(); // test: the interrupted frame's scene is open
#endif
    return movie_texture!=nullptr;
}
// The previous scene must have finished sampling the texture before rows change.
extern "C" int re4dc_ui_movie_upload_begin(){
#if RE4DC_WORLD_SCRATCH
    // Close admission immediately; the final synchronous borrower restores mode.
    re4dc_world_scratch_cancel();
#endif
    if(!movie_texture)return 0;
#if RE4DC_PVR_STREAM
    // A movie-owned presentation interrupts a source frame: its open (hidden
    // world) scene is discarded first, or the render fence below never completes.
    if(stream_scene)stream_close(false);
#endif
#if RE4DC_PVR_PIPELINE
    present_fence();
#endif
#if RE4DC_PVR_RECOVER
    // PVR_RECOVER: the movie upload fence (gpu::quiesce: KOS pvr_wait_ready / pvr_wait_render_done, 100 ms each)
    // gave up on a busy TA bank (r119 s30, r117 lane: terminal 3, nothing uploaded). Here it waits in the same
    // bounded, recovering 100 ms slices as the scene starts (K TA bank, Q render done); same result when not busy.
    {
        const bool ta=pvr_ready::wait_clear(pvr_state.ta_busy,"re4dc movie TA bank",'K',pvr_ready::ta_timeouts);
        const bool rd=ta && pvr_ready::wait_clear(pvr_state.render_busy,"re4dc movie render",'Q',pvr_ready::render_timeouts);
        if(!ta || !rd)re4dc_log("route movie upload fence: strict wait failed ta=%d render=%d\n",ta?1:0,rd?1:0);
        return ta && rd;
    }
#endif
#if RE4DC_MOVIE_FENCE_RETRY
    // A not-ready fence on the first picture ended r119 s30 (terminal=3, uploaded=0) in one image
    // layout (r118 lane, 2026-10-10): retry before failing the movie. Timing only.
    for(int attempt=0;;++attempt){
        const auto qr=re4dc::gpu::quiesce();
        if(qr==re4dc::gpu::FenceResult::ready)return 1;
        re4dc_log("route movie upload fence: result=%d attempt=%d\n",(int)qr,attempt);
        if(attempt>=3)return 0;
    }
#else
    return re4dc::gpu::quiesce()==re4dc::gpu::FenceResult::ready;
#endif
}
// movie_width active UYVY pixels per 1024-byte texture row; padding is never sampled.
extern "C" void re4dc_ui_movie_upload_rows(const void* uyvy,unsigned y,unsigned rows){
    const auto* src=static_cast<const unsigned char*>(uyvy);const unsigned bytes=movie_width*2;
    for(unsigned r=0;r<rows && y+r<movie_height;++r)pvr_txr_load(src+r*bytes,(char*)movie_texture+(y+r)*1024,bytes);
}
extern "C" void re4dc_ui_movie_upload_end(){movie_picture=true;++movie_upload_serial;}
extern "C" unsigned re4dc_ui_movie_presented(){return movie_presentations;}
#if RE4DC_GC_ASSET_GATE
// GC_ASSET_MOVIE_API_BEGIN
extern "C" unsigned re4dc_gcasset_movie_bind(const void* texture,unsigned width,unsigned height,unsigned asset){
    gcasset_movie_forget();
    if(!texture || texture!=movie_texture || width!=movie_width || height!=movie_height ||
       !width || !height || gcasset_movie_serial==~0U){
        re4dc_gcasset::unresolved(re4dc_gcasset::Movie,"movie-bind");return 0;
    }
    gcasset_movie={texture,width,height,++gcasset_movie_serial,0,0,{asset},asset==0,0};
    return gcasset_movie.owner;
}
extern "C" void re4dc_gcasset_movie_begin_upload(unsigned owner,const void* texture){
    // Even a stale writer can overwrite the current VRAM allocation. Revoke
    // before checking its owner, so it cannot leave a previous picture valid.
    gcasset_movie.upload=0;gcasset_movie.uploading=0;
    if(!owner || owner!=gcasset_movie.owner || texture!=gcasset_movie.texture)
        re4dc_gcasset::unresolved(re4dc_gcasset::Movie,"movie-upload-owner");
    else gcasset_movie.uploading=owner;
}
extern "C" void re4dc_gcasset_movie_uploaded(unsigned owner,const void* texture,unsigned width,unsigned height,unsigned asset){
    const unsigned uploading=gcasset_movie.uploading;gcasset_movie.uploading=0;
    if(!owner || uploading!=owner || owner!=gcasset_movie.owner || texture!=gcasset_movie.texture || texture!=movie_texture ||
       width!=gcasset_movie.width || height!=gcasset_movie.height || width!=movie_width || height!=movie_height ||
       asset!=gcasset_movie.asset.value || !movie_picture || !movie_upload_serial){
        gcasset_movie.upload=0;re4dc_gcasset::unresolved(re4dc_gcasset::Movie,"movie-upload-version");return;
    }
    gcasset_movie.upload=movie_upload_serial;
}
extern "C" void re4dc_gcasset_movie_resolved(unsigned owner,unsigned asset,int complete){
    if(!owner || owner!=gcasset_movie.owner || !gcasset_movie.pending){
        if(owner){re4dc_gcasset::unresolved(re4dc_gcasset::Movie,"movie-resolve-owner");}
        return;
    }
    const unsigned uses=gcasset_movie.pending_uses;gcasset_movie.pending=false;gcasset_movie.pending_uses=0;
    if(!complete || !asset){re4dc_gcasset::unresolved(re4dc_gcasset::Movie,"movie-incomplete-hash");return;}
    gcasset_movie.asset={asset};
    // Pictures were shown (and audio started) under this owner: one emission each,
    // the same verdict as per-picture emission (first room use logs once).
    re4dc_gcasset::emitted_checked(re4dc_gcasset::Movie,gcasset_movie.asset);
    if(uses)re4dc_gcasset::emitted_checked(re4dc_gcasset::Texture,gcasset_movie.asset);
}
// GC_ASSET_MOVIE_API_END
#endif
extern "C" uint64_t re4dc_ui_movie_first_picture_us(){return movie_first_picture_us;}
// The PVR YUV converter writes the movie texture directly (native_movie.cpp).
extern "C" void* re4dc_ui_movie_texture(){return movie_texture;}
extern "C" int re4dc_ui_movie_last_presented(){return movie_picture && movie_upload_serial==movie_shown_serial;}
// Movie-owned presentation (native_movie.cpp re4dc_movie_play): the source task
// playing the movie does not return to the frame loop, so the picture is
// presented here as a scene of its own. An open stream scene of the
// interrupted frame (hidden world) is discarded; that frame reopens one.
extern "C" int re4dc_ui_movie_present_now(){
    if(!ready || !movie_texture || !movie_picture)return 0;
#if RE4DC_PVR_STREAM
    if(stream_scene)stream_close(false);
#if RE4DC_D349_RENDERER_STACK
    const pvr_list_t list=desired_list;desired_list=PVR_LIST_TR_POLY;
#endif
    stream_open();
    movie_draw();
#if defined(RE4DC_BENCHMARK) && RE4DC_BENCHMARK
    bench_banner_draw();   // bench.mk: the banner over movie pictures too (same TR list as movie_draw)
#endif
    stream_close(true);
#if RE4DC_D349_RENDERER_STACK
    desired_list=list;
#endif
    if(movie_shown_serial!=movie_upload_serial){
        movie_shown_serial=movie_upload_serial;++movie_presentations;
        if(!movie_first_picture_us)movie_first_picture_us=timer_us_gettime64();
    }
    return 1;
#else
    return 0;
#endif
}
// Route QTE cuts (native_movie.cpp re4dc_movie_step): the open movie's picture is drawn by the game's
// own frames, under their UI quads (the action prompt), until switched off.
extern "C" void re4dc_ui_movie_background(int on){movie_background=on!=0;}
extern "C" int re4dc_ui_movie_close(){
#if RE4DC_WORLD_SCRATCH
    // Close admission immediately; the final synchronous borrower restores mode.
    re4dc_world_scratch_cancel();
#endif
#if RE4DC_CABIN_SOURCE
    MovieCabinUiScope owner;if(!owner.held)return 0;
#endif
#if RE4DC_MOVIE_WORLD_ARENA
    if(re4dc_movie_world_active()){
        if(direct_open)return 0;
#if RE4DC_D349_RENDERER_STACK
        if(draining_parts)return 0;
#endif
    }
#endif
    movie_background=false;
    if(!movie_texture)return 1;
#if RE4DC_PVR_STREAM
    // A movie whose open fails after the texture was allocated (snd_stream_init_ex without heap)
    // retires inside the frame it interrupted. That frame's open scene is discarded first, as in
    // re4dc_ui_movie_upload_begin, and the frame is not presented; otherwise the fence below never
    // completes and the texture and its claim leak (r100 s20: 101 retries, 11 s, preload blocked).
    if(stream_scene){
        re4dc_log("route movie texture retirement: open scene discarded\n");
        stream_close(false);
#if RE4DC_D349_RENDERER_STACK
        if(deferred_first || draining_parts)reset_deferred();
#endif
        stream_aborted=true;
    }
#endif
#if RE4DC_PVR_PIPELINE
    present_fence();
#endif
#if RE4DC_MOVIE_WORLD_ARENA && RE4DC_PVR_PIPELINE
    if(re4dc_movie_world_active()){
#if RE4DC_PVR_PIPELINE==2
        if(pvr_present_pending())return 0;
#else
        if(present_submitted!=present_resolved)return 0;
#endif
        if(present_failures)return 0;
    }
#endif
    if(re4dc::gpu::quiesce()!=re4dc::gpu::FenceResult::ready){re4dc_log("route movie texture retirement fence pending\n");return 0;}
#if RE4DC_MOVIE_WORLD_ARENA
    if(re4dc_movie_world_active() && (pvr_state.ta_busy || pvr_state.render_busy))return 0;
#endif
#if RE4DC_GC_ASSET_GATE
    gcasset_movie_forget();
#endif
    pvr_mem_free(movie_texture);movie_texture=nullptr;movie_picture=false;
#if RE4DC_TEX_RESIDENT
    re4dc_ui_vram_unclaim();
#endif
    return 1;
}
namespace {
void movie_draw(){
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,PVR_LIST_TR_POLY,
        PVR_TXRFMT_YUV422|PVR_TXRFMT_NONTWIDDLED,512,256,movie_texture,PVR_FILTER_BILINEAR);
    c.gen.culling=PVR_CULLING_NONE;c.depth.comparison=PVR_DEPTHCMP_ALWAYS;c.depth.write=PVR_DEPTHWRITE_DISABLE;
    c.blend.src=PVR_BLEND_ONE;c.blend.dst=PVR_BLEND_ZERO;c.txr.uv_clamp=PVR_UVCLAMP_UV;
    pvr_poly_hdr_t header;pvr_poly_compile(&header,&c);
    alignas(32) pvr_vertex_t packet[5]{};std::uint32_t count;
    re4dc::render::begin_pvr_packet(packet,count,header);
    const float x[]={0,640,0,640},y[]={0,0,480,480};
    for(unsigned i=0;i<4;++i){auto& v=packet[count+i];v.flags=i==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;
        v.x=RE4DC_UI_X(x[i]);v.y=RE4DC_UI_Y(y[i]);v.z=1;v.u=(i&1)?(movie_width-0.5f)/512:0.5f/512;v.v=i>=2?(movie_height-0.5f)/256:0.5f/256;v.argb=0xffffffff;}
#if RE4DC_GC_ASSET_GATE
    const bool verified=movie_picture && gcasset_movie.owner && gcasset_movie.texture==movie_texture &&
        gcasset_movie.width==movie_width && gcasset_movie.height==movie_height &&
        gcasset_movie.upload && gcasset_movie.upload==movie_upload_serial;
    GcAssetGeneratedPacket asset_packet{packet,unsigned(sizeof(packet)),unsigned(reinterpret_cast<std::uintptr_t>(movie_texture))&0x007fffffU,re4dc_gcasset::Movie,verified};
    {GcAssetGeneratedScope asset_scope(asset_packet);
#endif
#if RE4DC_PVR_STREAM
    stream_send(packet,sizeof(packet));
#else
    re4dc::render::submit_pvr(packet,sizeof(packet));
#endif
#if RE4DC_GC_ASSET_GATE
    }
    if(asset_packet.accepted && verified && gcasset_movie.pending)++gcasset_movie.pending_uses;
    else if(asset_packet.accepted && verified){
        re4dc_gcasset::emitted_checked(re4dc_gcasset::Movie,gcasset_movie.asset);
        re4dc_gcasset::emitted_checked(re4dc_gcasset::Texture,gcasset_movie.asset);
    }else re4dc_gcasset::unresolved(re4dc_gcasset::Movie,"unqualified-movie-picture");
#endif
}
}
#endif // RE4DC_ROUTE_MOVIES
#if defined(RE4DC_LEON_LIGHT_HEADROOM) && RE4DC_LEON_LIGHT_HEADROOM
#include "../charbake_variants.h"
// LEON_LIGHT_HEADROOM (crowd.mk): 1 when `image` samples one of Leon's 2x packages, the key set
// tools/d367/charbake/cb_headroom.py doubles (every Leon atlas, hair colour and hair pair key of charbake_variants.h,
// plus the pl08 atlas). Used by re4dc_model_submit (native_model.cpp) for draws outside Leon's owner path. Only the
// two sizes those packages have reach the key lookup (image_key's identity cache), so other parts cost one compare.
extern "C" int re4dc_leon_hr_image(const Re4dcUiImage* image){
    if(!image || !image->pixels)return 0;
    if(!((image->width==512 && image->height==512) || (image->width==64 && image->height==128)))return 0;
    Key k{};
    if(!image_key(*image,k))return 0;
    if(k.crc==0x7506e95fU && k.fnv==0x68cf2211U)return 1;  // the pl08 atlas
    for(const auto& v:re4dc_charbake::variants){
        if(k.crc==v.leon_crc && k.fnv==v.leon_fnv)return 1;
        for(unsigned i=0;i<2;++i)
            if((k.crc==v.hair_colour_crc[i] && k.fnv==v.hair_colour_fnv[i]) || (k.crc==v.hair_pair_crc[i] && k.fnv==v.hair_pair_fnv[i]))
                return 1;
    }
    return 0;
}
#endif

#if defined(RE4DC_SOB_DUMP) && RE4DC_SOB_DUMP
// SOB_DUMP (crowd.mk, diagnostic): the texture key the model path resolves for a part (masked pair when flag 4).
extern "C" int re4dc_ui_part_key(const Re4dcModelPart* p,unsigned* crc,unsigned* fnv){
    Key k{};bool ok;
#if RE4DC_D349_RENDERER_STACK
    ok=(p->material_flags&4)?model_mask_key(p,k):image_key(p->image,k);
#else
    ok=image_key(p->image,k);
#endif
    *crc=k.crc;*fnv=k.fnv;return ok?1:0;
}
#endif

#if defined(RE4DC_TEX_MIP_DADJ) && RE4DC_TEX_MIP_DADJ
// TEX_MIP_DADJ (lane mipmap22): replace KOS's default mipmap D adjust in every compiled header (render only).
extern "C" void __real_pvr_poly_compile(pvr_poly_hdr_t* dst,const pvr_poly_cxt_t* src);
extern "C" void __real_pvr_sprite_compile(pvr_sprite_hdr_t* dst,const pvr_sprite_cxt_t* src);
extern "C" void __real_pvr_poly_mod_compile(pvr_poly_mod_hdr_t* dst,const pvr_poly_cxt_t* src);
#if defined(RE4DC_HDR_ALIGN_PROBE) && RE4DC_HDR_ALIGN_PROBE
// HDR_ALIGN_PROBE (lane mipfault22, diagnostic): KOS compiles headers with movca.l, which allocates the whole
// 32-byte line without reading it; a header dst that is not 32-byte aligned leaves stale bytes in the line on
// console (emulators zero/keep memory). Logs each distinct caller once.
static void hdr_align_probe(const void* dst,const char* kind,void* pr) {
    static void* seen[16];static unsigned n;
    if((reinterpret_cast<std::uintptr_t>(dst)&31U)==0)return;
    for(unsigned i=0;i<n;++i)if(seen[i]==pr)return;
    if(n<16)seen[n++]=pr;
    std::printf("re4dc-hdr-misaligned: %s dst=%p pr=%p\n",kind,dst,pr);
}
#define RE4DC_HDR_PROBE(d,k) hdr_align_probe(d,k,__builtin_return_address(0))
#else
#define RE4DC_HDR_PROBE(d,k) ((void)0)
#endif
extern "C" void __wrap_pvr_poly_compile(pvr_poly_hdr_t* dst,const pvr_poly_cxt_t* src) {
    RE4DC_HDR_PROBE(dst,"poly");
    pvr_poly_cxt_t c=*src;
    if(c.txr.mipmap_bias==PVR_MIPBIAS_NORMAL)c.txr.mipmap_bias=(pvr_mip_bias_t)RE4DC_TEX_MIP_DADJ;
    __real_pvr_poly_compile(dst,&c);
}
extern "C" void __wrap_pvr_sprite_compile(pvr_sprite_hdr_t* dst,const pvr_sprite_cxt_t* src) {
    RE4DC_HDR_PROBE(dst,"sprite");
    pvr_sprite_cxt_t c=*src;
    if(c.txr.mipmap_bias==PVR_MIPBIAS_NORMAL)c.txr.mipmap_bias=(pvr_mip_bias_t)RE4DC_TEX_MIP_DADJ;
    __real_pvr_sprite_compile(dst,&c);
}
extern "C" void __wrap_pvr_poly_mod_compile(pvr_poly_mod_hdr_t* dst,const pvr_poly_cxt_t* src) {
    RE4DC_HDR_PROBE(dst,"mod");
    pvr_poly_cxt_t c=*src;
    if(c.txr.mipmap_bias==PVR_MIPBIAS_NORMAL)c.txr.mipmap_bias=(pvr_mip_bias_t)RE4DC_TEX_MIP_DADJ;
    if(c.txr2.mipmap_bias==PVR_MIPBIAS_NORMAL)c.txr2.mipmap_bias=(pvr_mip_bias_t)RE4DC_TEX_MIP_DADJ;
    __real_pvr_poly_mod_compile(dst,&c);
}
#endif

#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
extern "C" unsigned re4dc_dsa24_model_translucent(const Re4dcModelPart* p){
    return (draining_parts?draining_list:select_model_pass(p))==PVR_LIST_TR_POLY;
}
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
// XLU28 area class of a model part's list: 0 opaque, 1 punch-through, 2 translucent.
extern "C" unsigned re4dc_dsa28_model_class(const Re4dcModelPart* p){
    const unsigned list=draining_parts?draining_list:select_model_pass(p);
    return list==PVR_LIST_TR_POLY?2U:list==PVR_LIST_PT_POLY?1U:0U;
}
#endif
#endif
