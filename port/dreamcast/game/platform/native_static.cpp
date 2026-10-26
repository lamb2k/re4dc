#include "../world_scratch.h"
#include "include/bfc_class.h"
#include "include/movie_world_arena.h"
#include "include/native_cabin.h"
#if RE4DC_MOVIE_WORLD_ARENA
#include "native_io.h"
#endif
#if RE4DC_PS2_WORLD_SOURCE_OWNER || RE4DC_PS2_WORLD_R11F_OWNER
#include "include/ps2_source_world.h"
#endif
#ifndef RE4DC_PS2_WORLD_DRAW
#define RE4DC_PS2_WORLD_DRAW 0
#endif
#if RE4DC_PS2_WORLD_DRAW
#include "re4dc_screen.h"
#include "include/native_ps2_world.h"
#endif
#ifndef RE4DC_PS2_WORLD_MESH
#define RE4DC_PS2_WORLD_MESH 0
#endif
#ifndef RE4DC_ROOT_POSE_CAP_FALLBACK
#define RE4DC_ROOT_POSE_CAP_FALLBACK 0
#endif
#ifndef RE4DC_ROOT_POSE_WITNESS_PREFLIGHT
#define RE4DC_ROOT_POSE_WITNESS_PREFLIGHT 0
#endif
#ifndef RE4DC_ROOT_POSE_REFUSAL_DIAG
#define RE4DC_ROOT_POSE_REFUSAL_DIAG 0
#endif
#if (RE4DC_ROOT_POSE_CAP_FALLBACK != 0 && RE4DC_ROOT_POSE_CAP_FALLBACK != 1) || \
    (RE4DC_ROOT_POSE_WITNESS_PREFLIGHT != 0 && RE4DC_ROOT_POSE_WITNESS_PREFLIGHT != 1) || \
    (RE4DC_ROOT_POSE_REFUSAL_DIAG != 0 && RE4DC_ROOT_POSE_REFUSAL_DIAG != 1)
#error Root-pose refusal controls must be 0 or 1
#endif
#if (RE4DC_ROOT_POSE_CAP_FALLBACK || RE4DC_ROOT_POSE_WITNESS_PREFLIGHT || RE4DC_ROOT_POSE_REFUSAL_DIAG) && \
    (!RE4DC_PS2_WORLD_ROOT_POSE || !RE4DC_PS2_WORLD_PARTS || !RE4DC_PS2_WORLD_DYNAMIC || !RE4DC_PS2_WORLD_ROOMS)
#error Root-pose refusal controls need the room root-pose adapter
#endif
#ifndef RE4DC_SCENERY_SELECT_ONLY
#define RE4DC_SCENERY_SELECT_ONLY 0
#endif
#if RE4DC_SCENERY_SELECT_ONLY != 0 && RE4DC_SCENERY_SELECT_ONLY != 1
#error SCENERY_SELECT_ONLY must be 0 or 1
#endif
#if RE4DC_SCENERY_SELECT_ONLY && !RE4DC_SCENERY_CHUNK
#error SCENERY_SELECT_ONLY needs SCENERY_CHUNK
#endif
#ifndef RE4DC_SCENERY_STREAM
#define RE4DC_SCENERY_STREAM 0
#endif
#ifndef RE4DC_SCENERY_REPLAY_LEAN
#define RE4DC_SCENERY_REPLAY_LEAN 0
#endif
#if RE4DC_SCENERY_REPLAY_LEAN != 0 && RE4DC_SCENERY_REPLAY_LEAN != 1
#error SCENERY_REPLAY_LEAN must be 0 or 1
#endif
#if RE4DC_SCENERY_REPLAY_LEAN && (!RE4DC_SCENERY_CHUNK || !RE4DC_MESH_DIRECT || !RE4DC_PS2_WORLD_MESH)
#error SCENERY_REPLAY_LEAN needs the direct PS2 scenery chunk path
#endif
#if RE4DC_SCENERY_REPLAY_LEAN && RE4DC_WORLD_SCRATCH
#error SCENERY_REPLAY_LEAN needs WORLD_SCRATCH=0 (ordinary per-part scratch lifetime)
#endif
#ifndef RE4DC_SCENERY_UV_SNAPSHOT
#define RE4DC_SCENERY_UV_SNAPSHOT 0
#endif
#if RE4DC_SCENERY_UV_SNAPSHOT != 0 && RE4DC_SCENERY_UV_SNAPSHOT != 1
#error SCENERY_UV_SNAPSHOT must be 0 or 1
#endif
#if RE4DC_SCENERY_UV_SNAPSHOT && !RE4DC_SCENERY_CHUNK
#error SCENERY_UV_SNAPSHOT needs SCENERY_CHUNK
#endif
#ifndef RE4DC_SCENERY_SUBMIT_BATCH
#define RE4DC_SCENERY_SUBMIT_BATCH 0
#endif
#if RE4DC_SCENERY_SUBMIT_BATCH != 0 && RE4DC_SCENERY_SUBMIT_BATCH != 1
#error SCENERY_SUBMIT_BATCH must be 0 or 1
#endif
#if RE4DC_SCENERY_SUBMIT_BATCH && (!RE4DC_SCENERY_CHUNK || !RE4DC_MESH_DIRECT || !RE4DC_PS2_WORLD_MESH)
#error SCENERY_SUBMIT_BATCH needs the direct PS2 scenery chunk path
#endif
#if RE4DC_SCENERY_SUBMIT_BATCH && (RE4DC_PS2_PVS || RE4DC_WORLD_SCRATCH || RE4DC_TA_GUARD)
#error SCENERY_SUBMIT_BATCH does not yet qualify PS2_PVS, WORLD_SCRATCH or TA_GUARD
#endif
#ifndef RE4DC_SCENERY_EMIT_PREFETCH
#define RE4DC_SCENERY_EMIT_PREFETCH 0
#endif
#if RE4DC_SCENERY_EMIT_PREFETCH != 0 && RE4DC_SCENERY_EMIT_PREFETCH != 1
#error SCENERY_EMIT_PREFETCH must be 0 or 1
#endif
#if RE4DC_SCENERY_EMIT_PREFETCH && (!RE4DC_SCENERY_CHUNK || !RE4DC_MESH_DIRECT || !RE4DC_PS2_WORLD_MESH)
#error SCENERY_EMIT_PREFETCH needs the direct PS2 scenery chunk path
#endif
#ifndef RE4DC_SCENERY_LOCAL_INDEXED
#define RE4DC_SCENERY_LOCAL_INDEXED 0
#endif
#ifndef RE4DC_SCENERY_DIRECT_STRIPS
#define RE4DC_SCENERY_DIRECT_STRIPS 0
#endif
#if RE4DC_SCENERY_LOCAL_INDEXED || RE4DC_SCENERY_DIRECT_STRIPS
#if (RE4DC_SCENERY_LOCAL_INDEXED != 0 && RE4DC_SCENERY_LOCAL_INDEXED != 1) || \
    (RE4DC_SCENERY_DIRECT_STRIPS != 0 && RE4DC_SCENERY_DIRECT_STRIPS != 1) || \
    (RE4DC_SCENERY_LOCAL_INDEXED && RE4DC_SCENERY_DIRECT_STRIPS)
#error Select one Build 12 world data variant, value 1
#endif
#if !RE4DC_PS2_WORLD_ROOMS || !RE4DC_IO_ALIGNED || !RE4DC_SCENERY_CHUNK || \
    !RE4DC_MESH_DIRECT || !RE4DC_PS2_WORLD_MESH || RE4DC_WORLD_VERT || RE4DC_SCENERY21_AB || \
    RE4DC_SCENERY_DEDUP || RE4DC_SCENERY_CONE || RE4DC_SCENERY_PIECE_STATE || RE4DC_PS2_PVS || RE4DC_PS2_INTERIOR_CULL || RE4DC_WORLD_RECT21
#error Unsupported world data variant recipe
#endif
#include "../../room/scenery_data_variants.hpp"
#endif
#ifndef RE4DC_WORLD_RECT21
#define RE4DC_WORLD_RECT21 0
#endif
#ifndef RE4DC_SCENERY_RECORD_SPLIT
#define RE4DC_SCENERY_RECORD_SPLIT 0
#endif
#if RE4DC_SCENERY_RECORD_SPLIT != 0 && RE4DC_SCENERY_RECORD_SPLIT != 1
#error SCENERY_RECORD_SPLIT must be 0 or 1
#endif
#if RE4DC_SCENERY_RECORD_SPLIT
#if RE4DC_SCENERY_LOCAL_INDEXED || RE4DC_SCENERY_DIRECT_STRIPS
#error SCENERY_RECORD_SPLIT has not qualified Build12 payload/lineage composition
#endif
#if RE4DC_WORLD_VERT || RE4DC_SCENERY21_AB || RE4DC_SCENERY_DEDUP || RE4DC_SCENERY_CONE || RE4DC_SCENERY_PIECE_STATE || RE4DC_PS2_PVS || RE4DC_PS2_INTERIOR_CULL || RE4DC_WORLD_RECT21
#error SCENERY_RECORD_SPLIT needs independent matched metadata controls
#endif
#define RE4DC_SCENERY_RECORD re4dc::record_split::Record
#else
#define RE4DC_SCENERY_RECORD re4dc::room::Meshlet
#endif
#if RE4DC_WORLD_RECT21
#if !RE4DC_PS2_WORLD_DRAW || !RE4DC_PS2_WORLD_MESH
#error WORLD_RECT21 provenance requires the PS2 world mesh consumer
#endif
#include "../../tools/d367/texture_rect21/world_rect_provenance.h"
#include "../../tools/d367/texture_rect21/scoped_origin.h"
#endif
// MESH_DEPTH_CULL: the meshlet fast path drops a strip whose corners all lie outside one depth
// plane instead of clipping it to nothing (exact). On with PS2_WORLD_MESH.
#ifndef RE4DC_MESH_DEPTH_CULL
#define RE4DC_MESH_DEPTH_CULL RE4DC_PS2_WORLD_MESH
#endif
// Recovered scroll objects -> D349 native static room packages (v4 AoS20).
//
// The source still decides everything about an object: setObj creates and
// places it, its visibility gates decide whether commonModelTrans runs, and
// materialSetup/alphaSetup/blend/cull state is captured per part exactly as
// for the generic path. Only the geometry changes: a bound part draws the
// prelit package batches whose material carries its (texId, alphaTex) key,
// instead of decoding its GX display list and lighting its vertices.
//
// Ownership reuses the existing boundaries. A package view opens on the first
// bind of its owner (main scenario or source block) and retires with that
// owner. Each package source slot records the one live object bound to it and
// that object's creation serial; nothing else is registered. Packets, headers,
// texture pins, pass selection and translucent deferral are the existing
// native_ui frame owner's (re4dc_model_packet_*/re4dc_model_defer_part).
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
#if RE4DC_PS2_PVS_BATCH_COMPOSE
#if RE4DC_SCENERY_CHUNK != 1 || RE4DC_SCENERY_SELECT_ONLY != 1 || RE4DC_SCENERY_REPLAY_LEAN != 1 || RE4DC_MESH_DIRECT != 1 || RE4DC_MESH_FASTPATH != 1 || RE4DC_MESH_VP_SCHED != 1 || RE4DC_HW_LEAN != 1 || RE4DC_PS2_STRIP_GROUPS != 1 || RE4DC_PS2_WORLD_MESH != 1
#error PS2_PVS_BATCH_COMPOSE needs the qualified static selection/replay path
#endif
#endif
// PVS_BATCH_COMPOSITION_GUARD_END
#include <kos.h>
#include <fcntl.h>
#include <malloc.h>
#include <unistd.h>
#include <cmath>
#include <stdio.h>
#include <cstring>
#include <cstdlib>
#include "native_static.h"
#if defined(RE4DC_PS2_PVS) && RE4DC_PS2_PVS
#include "include/pvs23_format.hpp"
#include "include/pvs23_proof.hpp"
extern "C" void re4dc_pvs23_observe(unsigned,unsigned,unsigned,const void*,const std::uint8_t*,unsigned,
                                   const std::uint8_t*,unsigned,unsigned,unsigned,unsigned*);
extern "C" void re4dc_pvs23_commit(unsigned,unsigned,const unsigned*,const unsigned*);
#endif
#include "cache20.h"
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
#include "include/world_census24.h"
static unsigned wc24_generation; // native package and far-shell residency epoch
#if defined(RE4DC_VIEW_DIST_OPTION) && RE4DC_VIEW_DIST_OPTION
extern "C" int re4dc_view_dist_get(void);
#endif
#endif
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
#include "include/pvs23_meter.hpp"
extern "C" void re4dc_wm_corners(const std::uint8_t*,unsigned,unsigned);
// WORLD_METER (game30.mk): the QA menu's world rows (0 = the game's own far / shell; defined before re4dc_ps2_mesh_draw).
extern "C" volatile unsigned re4dc_qa_wopq_mm,re4dc_qa_wxlu_mm,re4dc_qa_wshell;
#endif
#if defined(RE4DC_RIGID_CENSUS) && RE4DC_RIGID_CENSUS == 2
extern "C" volatile unsigned re4dc_rigid_hide;   // native_actor_fast.cpp (RIGID_CENSUS=2)
#endif
#if RE4DC_QUALITY
#include "quality.h"
#endif
#include "native_model.h"
#include "include/gc_asset_static.h"
#include "include/gc_asset_static_source.inc"
#if RE4DC_SCENERY_SUBMIT_BATCH
#include "include/scenery_submit_batch.h"
#endif
#include "re4dc_platform.h"
#include "../../room/room_package.hpp"
#include "../../room/static_room_prepare.hpp"
#include "../../room/pvr_geometry.hpp"
#if RE4DC_PS2_WORLD_NONEMPTY_LOD
#include "../../room/nonempty_lod.hpp"
#endif

#ifndef RE4DC_NATIVE_STATIC
#define RE4DC_NATIVE_STATIC 0
#endif
#ifndef RE4DC_NATIVE_STATIC_OWNERS
#define RE4DC_NATIVE_STATIC_OWNERS 1U // bit 0 main scenario, bit n+1 block n
#endif
#ifndef RE4DC_NATIVE_MESH
#define RE4DC_NATIVE_MESH 0
#endif
#if RE4DC_NATIVE_MESH
#include "../../room/instanced_mesh.hpp"
#if RE4DC_SCENERY_RECORD_SPLIT
#include "../../room/scenery_record_split.hpp"
#endif
#endif
// COARSE_NO_STD_SCENERY (game30.mk; COARSE=1 with COARSE_WORLD only; default off): in the room the coarse
// world draws (coarse.cpp re4dc_coarse_world_room: coarse_world.h kRoom) bind_mesh() neither opens nor binds
// the room's scenery mesh package, so its heap-4 cell stays free (r101 Standard low/MAINSCENARIO.re4mesh,
// 599,328 B). Nothing a coarse image does reads it: a coarse tick's Trans() runs no ModelTrans (objTrans /
// emTrans) and its Render() draws the coarse view in place of the world OTs, so neither the part walk
// (re4dc_static_submit -> mesh_submit: LOD, impostors, tree quads, light_part, baked shells) nor trans.cpp's
// FRONT_LEAN / SCENERY_GATE queries (re4dc_static_mesh_lit, re4dc_static_gate) run for it. re4dc_static_bind
// returns nothing to the game: objects, collision and game state are unchanged. An image the coarse path does
// not draw in that room (outside in-room play: door demo, death, continue) draws its scroll parts through the
// generic path (a released part has no GX stream: nothing). "native mesh: no-std" lines: the heap-4 free where
// the package would have opened, and a census of its readers on coarse / other images (coarse.cpp latches
// the image kind per tick: re4dc_std_scenery_tick).
#ifndef RE4DC_NO_STD_SCENERY
#define RE4DC_NO_STD_SCENERY 0
#endif
#ifndef RE4DC_PS2_WORLD_ROOMS
#define RE4DC_PS2_WORLD_ROOMS 0
#endif
// The scenery-package skip + census: COARSE_NO_STD_SCENERY (the coarse world's room) or PS2_WORLD_ROOMS=2
// (a room whose PS2 world package opened at its first scenery bind).
#define RE4DC_NO_STD_ANY (RE4DC_NO_STD_SCENERY || RE4DC_PS2_WORLD_ROOMS >= 2)
#if RE4DC_PS2_WORLD_ROOMS >= 2
extern "C" int re4dc_ps2_mesh_preload(unsigned room);                  // below (PS2_WORLD_MESH)
extern "C" void re4dc_ps2_mesh_source(unsigned room,const Re4dcModelPart& p); // below
#endif
#if RE4DC_NO_STD_SCENERY
#if !RE4DC_NATIVE_MESH
#error COARSE_NO_STD_SCENERY skips the NATIVE_MESH scenery package (game30.mk)
#endif
extern "C" unsigned re4dc_coarse_world_room();   // coarse.cpp: coarse_world.h kRoom (stage << 8 | room)
#endif
// Transform-once meshlet path for R4IM meshes (room/mesh_fastpath.hpp). 0 keeps
// the per-strip-corner Emitter path for every meshlet (A/B reference).
#ifndef RE4DC_MESH_FASTPATH
#define RE4DC_MESH_FASTPATH 1
#endif
#ifndef RE4DC_MESH_CLASSIFY
#define RE4DC_MESH_CLASSIFY 0 // 1: skip outcodes in wholly visible meshlets (+1.5 KiB image)
#endif
#ifndef RE4DC_MESH_PRIME_LAZY
#define RE4DC_MESH_PRIME_LAZY 0 // 1: prime only the cache entries meshlets use (exact)
#endif
#ifndef RE4DC_MESH_CLIP_LEAN
#define RE4DC_MESH_CLIP_LEAN 0 // 1: clipper frustum pre-cull + one clip_vertex per corner (exact in pixels)
#endif
#ifndef RE4DC_WORLD_VERT
#define RE4DC_WORLD_VERT 0
#endif
#if RE4DC_WORLD_VERT
#ifndef RE4DC_WORLD_VERT_LEVEL
#define RE4DC_WORLD_VERT_LEVEL 0
#endif
// WORLD_VERT (lane worldvert): the wanted wholesale world level (0 = the source package), set by WORLD_VERT_LEVEL or at
// open time. This POC does not expose the unqualified in-place runtime swap.
static unsigned world_vert_level=RE4DC_WORLD_VERT_LEVEL;
#endif
static constexpr unsigned kClipOnce=16; // MESH_CLIP_LEAN: longer clipped strips take the per-triangle path
#if defined(RE4DC_MESH_CLIP_ACCEPT) && RE4DC_MESH_CLIP_ACCEPT==2
// MESH_CLIP_ACCEPT=2 (diagnostic): accepted triangles checked, dropped triangles checked, mismatches, crossings.
static unsigned clip_accept_stats[4];
#endif
#if defined(RE4DC_MESH_CLIP_ACCEPT) && RE4DC_MESH_CLIP_ACCEPT==3
// MESH_CLIP_ACCEPT=3 (layout control, diagnostic): both paths linked, this .data word picks one (1 = the MESH_CLIP_LEAN
// path, 2 = the accept path; never 0, so it stays in .data); MESH_CLIP_ACCEPT_SELECT=0|1.
#ifndef RE4DC_MESH_CLIP_ACCEPT_SELECT
#define RE4DC_MESH_CLIP_ACCEPT_SELECT 0
#endif
static volatile unsigned clip_accept_select=1U+RE4DC_MESH_CLIP_ACCEPT_SELECT;
#define RE4DC_CLIP_ACCEPT_ON (clip_accept_select==2U)
#else
#define RE4DC_CLIP_ACCEPT_ON true
#endif
#if defined(RE4DC_PS2_PASS_MASK) && RE4DC_PS2_PASS_MASK==3
// PS2_PASS_MASK=3 (layout control, diagnostic): the mask is built, this .data word picks its use (1 = the scan,
// 2 = the mask; never 0); PS2_PASS_MASK_SELECT=0|1.
#ifndef RE4DC_PS2_PASS_MASK_SELECT
#define RE4DC_PS2_PASS_MASK_SELECT 0
#endif
static volatile unsigned ps2_mask_select=1U+RE4DC_PS2_PASS_MASK_SELECT;
#define RE4DC_PS2_MASK_ON (ps2_mask_select==2U)
#else
#define RE4DC_PS2_MASK_ON true
#endif
#ifndef RE4DC_MESH_VP_SCHED
#define RE4DC_MESH_VP_SCHED 0 // 1: software-pipelined kChecksAll transform (exact); 2: both, compare; 3: layout control (diagnostics)
#endif
#if RE4DC_NATIVE_MESH && RE4DC_MESH_FASTPATH
#include "../../room/mesh_fastpath.hpp"
#if defined(RE4DC_CPU_BACKFACE) && RE4DC_CPU_BACKFACE == 2
#if defined(RE4DC_BACKFACE_ROOMS) && RE4DC_BACKFACE_ROOMS
// BACKFACE_ROOMS (backface.mk, lane fix-hideout23): the cull only in BACKFACE_ROOM_LIST; the flag is set per scene open.
extern "C" { unsigned char re4dc_bf_room_on; }
extern "C" unsigned re4dc_room_id_now();
extern "C" void re4dc_bf_room_update(){
    static const unsigned short rooms[]={RE4DC_BACKFACE_ROOM_LIST};
    const unsigned r=re4dc_room_id_now();unsigned char on=0;
    for(unsigned short x:rooms)if(x==r)on=1;
    if(on!=re4dc_bf_room_on){re4dc_bf_room_on=on;re4dc_log("backface rooms: room %03x cpu back-face %s\n",r,on?"on":"off");}
}
#endif
#include "../../room/backface_sh4.hpp"  // common SH-4 SQ ABI, owned by the main lane
#elif defined(RE4DC_CPU_BACKFACE) && RE4DC_CPU_BACKFACE
#include "../../room/backface_emit.hpp"  // CPU_BACKFACE (backface.mk, lane backface22)
#endif
#if RE4DC_MESH_VP_SCHED
#include "../../room/mesh_fastpath_sched.hpp"
#endif
#if RE4DC_SCENERY_DIRECT_STRIPS
#include "../../room/scenery_direct_strips.hpp"
#endif
#endif
#ifndef RE4DC_MESH_STRIP_LEAN
#define RE4DC_MESH_STRIP_LEAN 0 // 1: lean meshlet strip walk (exact); 2: both, compare; 3: layout control (diagnostics)
#endif
#if RE4DC_MESH_STRIP_LEAN && !(RE4DC_NATIVE_MESH && RE4DC_MESH_FASTPATH && RE4DC_MESH_DIRECT && RE4DC_MESH_DEPTH_CULL && defined(__sh__))
#undef RE4DC_MESH_STRIP_LEAN
#define RE4DC_MESH_STRIP_LEAN 0 // the lean walk covers the direct, depth-culling SH4 path only; others keep the original
#endif
#if RE4DC_MESH_STRIP_LEAN
#include "../../room/mesh_strip_lean.hpp"
#endif
// R4IM v2 levels of detail (convert_room_bins.py --lod). Per visible cluster
// the coarsest level whose error projects to at most RE4DC_MESH_LOD_PX pixels
// at the cluster's nearest depth is drawn. 0 accepts v1 packages only.
#ifndef RE4DC_MESH_LOD
#define RE4DC_MESH_LOD 0
#endif
#ifndef RE4DC_MESH_LOD_PX
#define RE4DC_MESH_LOD_PX 3
#endif
// Source fog on the native path: GXSetFog state becomes PVR table fog on model
// headers (native_ui.cpp), ramped to 100% at the source View far plane, and
// scenery clusters/meshlets beyond that far plane are rejected (the source's
// own object gate distance, light.cpp setFog/hokanMove -> View.setFarPlane).
#ifndef RE4DC_NATIVE_FOG
#define RE4DC_NATIVE_FOG 0
#endif
#ifndef RE4DC_FOG_FAR
#define RE4DC_FOG_FAR 0 // >0: DC fog/cull far plane (source units) when shorter than the source's
#endif
#if defined(RE4DC_LAKE_FAR_ON)
// LAKE_FAR (post30.mk, lane lake17): the far (mm) of the lake rooms r10b / r11a / r11b in place of the 25 m cap; the
// given cap elsewhere. Defined at the end of this file (reads the open PS2 world's room).
extern "C" float re4dc_far_cap(float cap);
#endif
#ifndef RE4DC_FOG_BACKGROUND
#define RE4DC_FOG_BACKGROUND 1 // background colour follows the fog colour while fog is on
#endif
// Look knobs (post30.mk, look study 2026-10-10; all off = the previous image): FOG_CURVE, FOG_CAP, FOG_RGB_PCT,
// SKY_FAR at build time, or LOOK_TOGGLE's runtime presets (hold X + press START; warp `look <n>`).
#if defined(RE4DC_FOG_CURVE) || defined(RE4DC_FOG_RGB_PCT) || defined(RE4DC_LOOK_TOGGLE)
#define RE4DC_LOOK_ANY 1
#else
#define RE4DC_LOOK_ANY 0
#endif
#if defined(RE4DC_LOOK_TOGGLE)
// Presets: curve, cap %, fog colour %, sky (0 culled, 1 drawn + table fog, 2 drawn unfogged), effect flags
// (EFFECT_PS2_TOGGLE builds: 1 fade clamp, 2 PS2 haze, 4 PS2 light shafts; 7 = the play build), grade (1: the r100
// outdoor colour match, one full-screen multiply quad, native_ui.cpp re4dc_look_grade_post), soft (PVR scaler vertical
// filter: 0 as KOS set it at boot, 1 forced on = VSCALE 1025, 2 forced off = 1024), f00 (FILTER00_DC: 1 = the room's
// own GameCube Filter00 contrast, native_ui.cpp re4dc_post_filter00), chr (CHARBAKE_TOGGLE: charbake_variants.h row,
// 0 = the play textures), VMU label, on-screen text.
// User decision 2026-10-11 (test 7): two presets, A (boot) = today's look, B = GameCube (GD fog + GM colour match +
// FILTER00_DC, today's character textures; the CG character bake preset was dropped). LOOK_TOGGLE_ALL=1 (test builds) keeps the
// look study's 11 instead (disc 3 order: GD GM GS GA DC GX CA CS CG CV CQ).
struct Re4dcLook { unsigned char curve,cap,rgb,sky,fx,grade,soft,f00,chr; char label[3]; const char* text; };
static const Re4dcLook re4dc_looks[]={
#if defined(RE4DC_LOOK_TOGGLE_ALL)
    {1,100, 70,1,7,0,0,0,0,"GD","GD: GC fog, fog colour 70%"},   // GameCube fog curve + sky / treeline, fog colour 70 %
    {1,100, 70,1,7,1,0,0,0,"GM","GM: GD + r100 colour match"},   // GD + the r100 outdoor brightness / colour match
    {1,100, 70,1,7,0,1,0,0,"GS","GS: GD + flicker filter on"},   // GD + the PVR vertical flicker filter forced on
    {1,100, 70,1,7,1,1,0,0,"GA","GA: GC fog + r100 colour + filter"},   // GD + match + filter
    {0,100,100,0,7,0,0,0,0,"DC","DC: current look"},             // the play build's look (as the knobs-off image)
    {1,100, 70,1,7,0,2,0,0,"GX","GX: GD, flicker filter off"},   // GD with the vertical filter forced OFF
#if defined(RE4DC_CHARBAKE_TOGGLE) && RE4DC_CHARBAKE_TOGGLE
    // charbake (charbake.mk CHARBAKE_TOGGLE): the DC look with each character texture variant
    {0,100,100,0,7,0,0,0,1,"CA","CA: DC + characters AO"},     // ambient occlusion baked into Leon + Ganados
    {0,100,100,0,7,0,0,0,2,"CS","CS: DC + characters AO + sky"},   // AO + soft sky / ground light
    {0,100,100,0,7,0,0,0,3,"CG","CG: DC + characters GC bright"},  // SKY graded toward the GameCube (hair too)
    {0,100,100,0,7,0,0,0,4,"CV","CV: DC + Leon VQ texture"},   // Leon atlas as VQ (66 KB VRAM, not 524), play shading
    {0,100,100,0,7,0,0,0,5,"CQ","CQ: CG with Leon VQ"},        // CG with Leon atlas as VQ
#endif
#else
    {0,100,100,0,7,0,0,0,0,"A","A: Current"},                   // the play build's look (as the knobs-off image)
    {1,100, 70,1,7,1,0,1,0,"B","B: GameCube"},                  // GD fog + GM colour match + Filter00, today's characters
#endif
};
constexpr unsigned kLooks=sizeof(re4dc_looks)/sizeof(re4dc_looks[0]);
#if defined(RE4DC_CHARBAKE_TOGGLE) && RE4DC_CHARBAKE_TOGGLE
#include "../charbake_variants.h"
extern "C" void re4dc_charbake_set(unsigned variant);  // coarse_actor.cpp (charbake.mk CHARBAKE_TOGGLE)
static_assert(re4dc_charbake::kCount==6 && re4dc_charbake::variants[3].label[0]=='G',"chr rows: CG = GCB = row 3");
static unsigned re4dc_look_chr(unsigned mode){return re4dc_looks[mode%kLooks].chr;}
static unsigned re4dc_look_chr_last; // the variant the presets last set (0 at boot)
#endif
extern "C" { unsigned re4dc_look_mode; }
#if defined(RE4DC_EFFECT_PS2_TOGGLE) && RE4DC_EFFECT_PS2_TOGGLE
extern "C" void re4dc_ps2fx_set(unsigned flags);
#endif
#include "pvr_internal.h"   // KOS pvr_state.render_busy (post30.mk LOOK_TOGGLE: -I$(KOS_BASE)/kernel/arch/dreamcast/hardware/pvr)
static unsigned re4dc_look_scaler_boot=~0U; // PVR_SCALER_CFG as KOS left it (vertical filter on for 480i TV)
static bool re4dc_look_applied;
// Issue #11 (console, VGA box, 2026-10-10): stepping to GS hung the PVR (render started, never finished; error
// bits ISP + OPB out of memory). The preset wrote SCALER_CFG from the pad poll, i.e. at any point of a render: the
// ISP/TSP write-out reads the vertical scale factor while it renders, and on VGA KOS never enables the vertical
// filter at all (pvr_init: VSCALE 1024 for VGA, 1025 only for interlaced TV), so GS switched the scaler on in a mode
// the port never runs it in, mid-render. Now (render only, LOOK_TOGGLE builds only):
// - VGA: SCALER_CFG is never written (GS / GA / GX change nothing there);
// - an unchanged value is not written (GS / GA on a TV, where KOS already set 1025);
// - a real change (GX on a TV, and back) is applied in the ISP render-done interrupt, after KOS's handler, only
//   while no render is in flight (pvr_state.render_busy clear, interrupts off: renders start only from the PVR
//   interrupts / vblank, so none can start under the write). The next render is the first to use it.
static volatile unsigned re4dc_look_scaler_want=~0U,re4dc_look_scaler_writes;
static asic_evt_handler_entry_t re4dc_look_kos_done;
static bool re4dc_look_chained;
static void re4dc_look_render_done(uint32_t code,void* data){
    (void)data;
    if(re4dc_look_kos_done.hdl)re4dc_look_kos_done.hdl(code,re4dc_look_kos_done.data);
    const unsigned w=re4dc_look_scaler_want;
    if(w==~0U || pvr_state.render_busy)return;
#if RE4DC_RES_MODES
    PVR_SET(PVR_SCALER_CFG,(PVR_GET(PVR_SCALER_CFG)&~0xffffU)|(w&0xffffU));re4dc_look_scaler_want=~0U; // keep RES_MODES' FSAA bit
#else
    PVR_SET(PVR_SCALER_CFG,w);re4dc_look_scaler_want=~0U;
#endif
    re4dc_look_scaler_writes=re4dc_look_scaler_writes+1;
}
static const char* re4dc_look_scaler_request(unsigned cfg){
    if(vid_mode && vid_mode->cable_type==CT_VGA){re4dc_look_scaler_want=~0U;return "vga: scaler untouched";}
    const int o=irq_disable();
    const bool same=unsigned(PVR_GET(PVR_SCALER_CFG))==cfg;
    re4dc_look_scaler_want=same?~0U:cfg;
    if(!same && !re4dc_look_chained){
        re4dc_look_kos_done=asic_evt_set_handler(ASIC_EVT_PVR_RENDERDONE_TSP,re4dc_look_render_done,nullptr);
        re4dc_look_chained=true;
    }
    irq_restore(o);
    return same?"unchanged":"queued for render done";
}
// On-screen label (native_ui.cpp re4dc_look_grade_post draws it in the top letterbox): 3 s after each preset change,
// or always while "always show" is on (hold X + Y, press START).
extern "C" unsigned re4dc_vi_retrace_count(void);
#if defined(RE4DC_MIST_CUT)
extern "C" unsigned re4dc_mist_cut;   // esp_sub.cpp (hwfog.mk MIST_CUT)
#endif
static unsigned re4dc_look_osd_until;static bool re4dc_look_osd_always;
extern "C" void re4dc_look_osd_toggle(void){
    re4dc_look_osd_always=!re4dc_look_osd_always;re4dc_look_osd_until=re4dc_vi_retrace_count()+180U;
    re4dc_log("look: label always %s\n",re4dc_look_osd_always?"on":"off");
}
#if RE4DC_RES_MODES
extern "C" const char* re4dc_res_osd_text(void); // res_mode.cpp: the render mode's name, 3 s after a change
#endif
#if defined(RE4DC_HW_FOG_HAZE_TOGGLE) && RE4DC_HW_FOG_HAZE_TOGGLE
extern "C" const char* re4dc_hwfog_osd_text(void); // hwfog.cpp: HW fog on / off, 3 s after a change
#endif
#if defined(RE4DC_EFFECT_HAZE_LEAN_TOGGLE)
extern "C" const char* re4dc_haze_lean_osd_text(void); // esp_sub.cpp: the haze mode's name, 3 s after a change
#endif
#if defined(RE4DC_SHADOW_BLOB_TOGGLE)
extern "C" const char* re4dc_blob_osd_text(void); // blob_shadow.cpp: the blob strength's name, 3 s after a change
#endif
#if defined(RE4DC_FX_LEVEL_TOGGLE) && RE4DC_FX_LEVEL_TOGGLE
extern "C" const char* re4dc_fx_level_osd_text(void); // esp_sub.cpp: the FX level, 3 s after a change
#endif
#if defined(RE4DC_LEON_LIGHT_TOGGLE) && RE4DC_LEON_LIGHT_TOGGLE
extern "C" const char* re4dc_leon_light_osd_text(void); // native_actor_fast.cpp: the Leon lighting mode, 3 s after a change
#endif
extern "C" const char* re4dc_look_osd_text(void){
#if defined(RE4DC_FX_LEVEL_TOGGLE) && RE4DC_FX_LEVEL_TOGGLE
    if(const char* fl=re4dc_fx_level_osd_text())return fl;
#endif
#if defined(RE4DC_LEON_LIGHT_TOGGLE) && RE4DC_LEON_LIGHT_TOGGLE
    if(const char* ll=re4dc_leon_light_osd_text())return ll;
#endif
#if defined(RE4DC_SHADOW_BLOB_TOGGLE)
    if(const char* bl=re4dc_blob_osd_text())return bl;
#endif
#if RE4DC_RES_MODES
    if(const char* res=re4dc_res_osd_text())return res;
#endif
#if defined(RE4DC_HW_FOG_HAZE_TOGGLE) && RE4DC_HW_FOG_HAZE_TOGGLE
    if(const char* hf=re4dc_hwfog_osd_text())return hf;
#endif
#if defined(RE4DC_EFFECT_HAZE_LEAN_TOGGLE)
    if(const char* hz=re4dc_haze_lean_osd_text())return hz;
#endif
    if(!re4dc_look_osd_always && int(re4dc_look_osd_until-re4dc_vi_retrace_count())<=0)return nullptr;
    return re4dc_looks[re4dc_look_mode%kLooks].text;
}
extern "C" void re4dc_look_set(unsigned mode){
    re4dc_look_mode=mode%kLooks;re4dc_look_applied=true;re4dc_look_osd_until=re4dc_vi_retrace_count()+180U;
    const Re4dcLook& lk=re4dc_looks[re4dc_look_mode];
#if defined(RE4DC_EFFECT_PS2_TOGGLE) && RE4DC_EFFECT_PS2_TOGGLE
    re4dc_ps2fx_set(lk.fx); // masked to the built features
#endif
#if defined(RE4DC_CHARBAKE_TOGGLE) && RE4DC_CHARBAKE_TOGGLE
    if(re4dc_look_chr(re4dc_look_mode)!=re4dc_look_chr_last){
        re4dc_look_chr_last=re4dc_look_chr(re4dc_look_mode);re4dc_charbake_set(re4dc_look_chr_last);
    }
#endif
    if(re4dc_look_scaler_boot==~0U)re4dc_look_scaler_boot=PVR_GET(PVR_SCALER_CFG);
    const unsigned vs=lk.soft==1?1025U:lk.soft==2?1024U:(re4dc_look_scaler_boot&0xffffU);
    const char* how=re4dc_look_scaler_request((re4dc_look_scaler_boot&~0xffffU)|vs);
    re4dc_log("look: preset %u %s (curve %u cap %u fog colour %u%% sky %u fx %u grade %u f00 %u chr %u vscale %u scaler %08x %s)\n",re4dc_look_mode,lk.label,
        lk.curve,lk.cap,lk.rgb,lk.sky,lk.fx,lk.grade,lk.f00,lk.chr,vs,unsigned(PVR_GET(PVR_SCALER_CFG)),how);
}
// GM / GA: the r100 outdoor cuts (fog colour 8d8775 with a negative fog start: cuts 0-3, 5-9, 12-15; the house
// cuts 4 / 10 / 11 start at 9.8 m and match the GameCube already) get one full-screen multiply. Per channel
// GameCube / Dreamcast mean over the r100 start + path stills (GD preset): r 0.87, g 0.89, b 0.845.
static unsigned re4dc_look_grade_rgb_now;
extern "C" unsigned re4dc_look_grade_argb(void){
    if(!re4dc_look_applied)re4dc_look_set(re4dc_look_mode); // the first frame applies preset 0's effect look + scaler
    return re4dc_looks[re4dc_look_mode%kLooks].grade?re4dc_look_grade_rgb_now:0U;
}
extern "C" void re4dc_look_cycle(void){re4dc_look_set(re4dc_look_mode+1);}
extern "C" const char* re4dc_look_label(void){return re4dc_looks[re4dc_look_mode%kLooks].label;}
extern "C" int re4dc_look_filter00(void){ // FILTER00_DC (native_ui.cpp re4dc_post_filter00): this preset's switch
    if(!re4dc_look_applied)re4dc_look_set(re4dc_look_mode);
    return re4dc_looks[re4dc_look_mode%kLooks].f00;
}
static inline unsigned re4dc_look_curve(){return re4dc_looks[re4dc_look_mode%kLooks].curve;}
static inline unsigned re4dc_look_cap(){return re4dc_looks[re4dc_look_mode%kLooks].cap;}
static inline unsigned re4dc_look_rgb_pct(){return re4dc_looks[re4dc_look_mode%kLooks].rgb;}
static inline unsigned re4dc_look_sky(){return re4dc_looks[re4dc_look_mode%kLooks].sky;}
#define RE4DC_SKY_ANY 1
static inline unsigned re4dc_sky_mode(){return re4dc_look_sky();}
#elif RE4DC_LOOK_ANY
#ifndef RE4DC_FOG_CURVE
#define RE4DC_FOG_CURVE 0
#endif
#ifndef RE4DC_FOG_CAP
#define RE4DC_FOG_CAP 100
#endif
#ifndef RE4DC_FOG_RGB_PCT
#define RE4DC_FOG_RGB_PCT 100
#endif
static inline unsigned re4dc_look_curve(){return RE4DC_FOG_CURVE;}
static inline unsigned re4dc_look_cap(){return RE4DC_FOG_CAP;}
static inline unsigned re4dc_look_rgb_pct(){return RE4DC_FOG_RGB_PCT;}
#endif
#ifndef RE4DC_SKY_ANY
#if defined(RE4DC_SKY_FAR)
#define RE4DC_SKY_ANY 1
static inline unsigned re4dc_sky_mode(){return RE4DC_SKY_FAR;}
#else
#define RE4DC_SKY_ANY 0
#endif
#endif
// D367 frontend30 (obj/frontend30.h; all default off = previous image).
// COPY_LEAN: no zero-fill of clip scratch written before it is read, one
// XMTRX load per mesh part, and no lighting snapshot for deferred parts that
// are already lit. MESH_DIRECT: mesh strips go to the TA through the store
// queues (re4dc_model_direct_begin, TA_DIRECT=1) instead of slab + pvr_prim.
#ifndef RE4DC_COPY_LEAN
#define RE4DC_COPY_LEAN 0
#endif
#ifndef RE4DC_FRONT_LEAN
#define RE4DC_FRONT_LEAN 0
#endif
#ifndef RE4DC_MESH_DIRECT
#define RE4DC_MESH_DIRECT 0
#endif
#ifndef RE4DC_HW_LEAN
#define RE4DC_HW_LEAN 0 // frontend30 pass 2: SH-4 hardware-cost trims (fsrra 1/w in the clipper projection)
#endif
// Clip-path colour / alpha scaling: HW_LEAN multiplies by 1/255 (no fdiv; <= 1 ulp).
#if RE4DC_HW_LEAN
#define RE4DC_INV255 *(1.0f/255.0f)
#else
#define RE4DC_INV255 /255.0f
#endif
#if RE4DC_MESH_DIRECT
#if !RE4DC_NATIVE_MESH || !RE4DC_MESH_FASTPATH
#error MESH_DIRECT extends the NATIVE_MESH fast path
#endif
#include "ta_direct.hpp"
#endif
#if defined(RE4DC_PS2_INTERIOR_CULL) && RE4DC_PS2_INTERIOR_CULL==2
// PS2_INTERIOR_CULL=2: set around the check run; native_ui.cpp then strips texturing and fog from the direct header.
extern "C" { unsigned re4dc_ps2_check_header=0; }
#endif
#if RE4DC_COPY_LEAN
#include <new>
// native_ui.cpp: the translucent queue without a lighting snapshot.
extern "C" int re4dc_model_defer_part_unlit(const Re4dcModelPart*);
#endif
// D367 item 20, TREE_IMPOSTOR (blender30.mk; default off = previous image): a
// mesh with an impostor record draws beyond RE4DC_TREE_IMPOSTOR_MM of view
// depth as one camera-facing punch-through quad (mesh_impostor below).
#if RE4DC_TREE_IMPOSTOR
#if !RE4DC_NATIVE_MESH || !RE4DC_MESH_LOD
#error TREE_IMPOSTOR draws R4IM v2 impostor records (NATIVE_MESH=1 MESH_LOD=1)
#endif
extern "C" int re4dc_model_pt_begin(unsigned crc,unsigned fnv,unsigned width,unsigned height,int fog,Re4dcModelPacket* out);
#endif
// D367 item 21, MESH_TEXTURES (blender30.mk; default off = previous image): a
// part with a texture record draws with that prepared package (mesh_submit).
#if RE4DC_MESH_TEXTURES
#if !RE4DC_NATIVE_MESH || !RE4DC_MESH_LOD
#error MESH_TEXTURES draws R4IM v2 texture records (NATIVE_MESH=1 MESH_LOD=1)
#endif
extern "C" void re4dc_model_texture(const unsigned* key);
#endif

#if RE4DC_QUALITY_ASSETS
#if !RE4DC_QUALITY || !RE4DC_TREE_IMPOSTOR || !RE4DC_MESH_TEXTURES
#error QUALITY_ASSETS needs QUALITY=1 TREE_IMPOSTOR=1 MESH_TEXTURES=1
#endif
extern "C" int re4dc_fixture_read(const char* path,char* buffer,unsigned size);   // os.cpp
#endif
#if RE4DC_MV_SHADOWS
// MV_SHADOWS (game30.mk; mv_shadow.cpp): every MeshDraw part (room scenery, room objects, the PS2 world) is a shadow
// receiver: native_ui.cpp sets the cheap-shadow modifier bit on its opaque header while this flag is set. The
// perspective projection and viewport of the frame's first receiver are kept for the shadow volumes.
extern "C" {
unsigned re4dc_mv_receiver;
float re4dc_mv_projection[7],re4dc_mv_viewport[6];
unsigned re4dc_mv_camera_frame=~0U;
}
#endif
#if defined(RE4DC_SHADOW_BLOB) && RE4DC_SHADOW_BLOB
// SHADOW_BLOB (game30.mk; blob_shadow.cpp): the perspective projection and viewport of the frame's first MeshDraw part
// are kept for the ground blobs (the same camera MV_SHADOWS keeps).
extern "C" {
float re4dc_blob_projection[7],re4dc_blob_viewport[6];
unsigned re4dc_blob_camera_frame=~0U;
}
#endif

namespace {
using re4dc::room::Package;
#if RE4DC_GC_ASSET_GATE
#if RE4DC_PS2_WORLD_MESH
void gcasset_invalidate_world();
#else
void gcasset_invalidate_world(){}
#endif
void gcasset_static_policy(re4dc_gcasset::StaticManifest&,unsigned room);
void gcasset_static_invalidate_all();
// Borrowed only during a cold load. Movie/re-adopt calls omit this argument
// and cannot reconstruct original sidecar identities from prepared storage.
#define GCASSET_STATIC_ONLY_PARAM re4dc_gcasset::StaticManifest* gcmanifest=nullptr
#define GCASSET_STATIC_PARAM ,GCASSET_STATIC_ONLY_PARAM
#define GCASSET_STATIC_ARG ,&gcasset_source
void gcasset_static_state(re4dc_gcasset::StaticManifest* m,re4dc_gcasset::StaticRole role,re4dc_gcasset::StaticState state){
    if(m)re4dc_gcasset::static_manifest_note(*m,role,state);
}
void gcasset_static_bytes(re4dc_gcasset::StaticManifest* m,re4dc_gcasset::StaticRole role,const void* p,unsigned n,unsigned version=0,unsigned flags=0){
    if(m)re4dc_gcasset::static_manifest_bytes(*m,role,p,n,version,flags);
}
#else
#define GCASSET_STATIC_ONLY_PARAM
#define GCASSET_STATIC_PARAM
#define GCASSET_STATIC_ARG
#endif
#if RE4DC_GC_ASSET_GATE
unsigned gcasset_static_profile(){
    return 0x01000000U | (unsigned(RE4DC_SCENERY_ENCODING)&3U) |
        ((RE4DC_MESH_LOD!=0)?4U:0U)
#if defined(RE4DC_SCENERY_DEDUP)
        | ((unsigned(RE4DC_SCENERY_DEDUP)&3U)<<4)
#endif
        ; // absent knob is the same mode0 as the existing preprocessor paths
}
void gcasset_static_ordinary_manifest(re4dc_gcasset::StaticManifest& source,re4dc_gcasset::StaticOwner owner,unsigned room,const void* data,unsigned bytes){
    using namespace re4dc_gcasset;
    static_manifest_begin(source,owner,room,gcasset_static_profile(),data,bytes);
    for(unsigned i=0;i<StaticRoleCount;++i)if(i!=STD_INDEX && i!=PCL1_CELL)static_manifest_note(source,StaticRole(i),NotApplicable);
    gcasset_static_policy(source,room);
}
#endif
#if RE4DC_QUALITY_ASSETS
// Standard asset set (D367_ASSET_PIPELINE.md s16). re4dc_std_room_enter() parses
// native/<room>/low/index.txt once per room entry (Standard mode only) into these
// fixed tables; the text buffer is freed after parsing. A rejected or missing index
// leaves the room on the Original packages (lod_px stays the Standard 5).
struct StdTex { unsigned crc,fnv; unsigned short width,height; unsigned vram; };
struct StdKey { unsigned crc,fnv; };
struct StdCull { unsigned char view,common; unsigned short mesh,bin; float mm; };
struct StdImp { unsigned char view,common; unsigned short bin; float mm; re4dc::room::MeshImpostor rec; };
struct StdPtex { unsigned char view,common; unsigned short part,bin; unsigned key[4]; };
// s16.5 split groves: one impostor per tree = a cluster range of one part.
struct StdImpt { unsigned char view,common; unsigned short bin,part,first,count; float mm; re4dc::room::MeshImpostor rec; };
constexpr unsigned kStdMesh=16,kStdTex=32,kStdDrop=16,kStdCull=64,kStdImp=32,kStdPtex=32,kStdImpt=32,kStdText=4096;
constexpr unsigned kStdTokens=24; // widest record: impt, 21 tokens
struct StdRoom {
    unsigned room=~0U; bool active=false;                 // active: index accepted for this room
    unsigned mesh_bytes[8]; unsigned char mesh_views;     // bit per mesh view: open low/<OWNER>
    unsigned char checked;                                // bit per mesh view: records verified at open
    unsigned ntex,ndrop,ncull,nimp,nptex,nimpt;
    StdTex tex[kStdTex]; StdKey drop[kStdDrop]; StdCull cull[kStdCull]; StdImp imp[kStdImp]; StdPtex ptex[kStdPtex]; StdImpt impt[kStdImpt];
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::PayloadProof asset_proof;
    // gc-catalog24b: the room's index was looked up and not used: 1 missing
    // (Absent), 2 oversized or rejected (Rejected). The room then draws Original
    // packages exactly as with no index.
    unsigned char gca_unused=0;
#endif
};
StdRoom std_room;
unsigned std_stats[6]; // culled draws, impostor records used, baked parts, low/ opens, tree quads, tree cluster ranges drawn
#endif

constexpr unsigned kViews=6;           // main + source blocks 0..4
constexpr unsigned kMaxMaterials=64;   // per-frame key ownership is one mask word
// Package coordinates are source world units times --source-unit-scale.
constexpr float kPackageToSource=1000.0f;

struct Binding {
    const void* object; unsigned serial, frame;
    unsigned long long drawn, fallback; // material bits owned this frame
    unsigned first_group, group_count;  // resolve_source() at bind
    float world[12];                    // placement the package was baked at
};
struct View {
    Package package;
    unsigned char* storage=nullptr; unsigned bytes=0;
    Binding* bindings=nullptr;
    re4dc::room::MaterialSourceKey keys[kMaxMaterials];
    unsigned room=0; bool attempted=false;
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::PayloadProof asset_proof;
#endif
};
View views[kViews];
#if RE4DC_GC_ASSET_GATE && !RE4DC_NATIVE_MESH
void gcasset_static_invalidate_all(){
    for(auto& v:views)if(v.asset_proof.owner)re4dc_gcasset::payload_invalidate(v.asset_proof,&v);
    gcasset_invalidate_world();
}
void gcasset_static_policy(re4dc_gcasset::StaticManifest& source,unsigned room){
    (void)room;
    re4dc_gcasset::static_manifest_note(source,re4dc_gcasset::STD_INDEX,re4dc_gcasset::Disabled);
    re4dc_gcasset::static_manifest_note(source,re4dc_gcasset::PCL1_CELL,re4dc_gcasset::Disabled);
}
#endif
Re4dcStaticStats stats{};
#if defined(RE4DC_SCN_CENSUS) && RE4DC_SCN_CENSUS
// SCN_CENSUS=1 (logiclod20.mk; test only): per meshlet drawn by meshlet(): visits, corners, corners of meshlets none of
// whose strips reached the screen (all culled after the transform), strips emitted / culled, triangles emitted, plus the
// strip-group corner skips; one "scnc:" line every 120 frames (sums over those frames).
unsigned scn_cen[10];
#endif
unsigned last_log_frame=~0U;

unsigned view_index(int block){return block<0?0U:unsigned(block)+1U;}
const char* owner_name(unsigned index,char* out,unsigned size){
    if(!index)snprintf(out,size,"MAINSCENARIO");
    else snprintf(out,size,"FILE_%02u",index-1U);
    return out;
}

#if RE4DC_QUALITY_ASSETS
constexpr unsigned kStdCommon=kViews; // COMMON's mesh view (mesh_views[kCommonView])
int std_owner(const char* s){
    if(!std::strcmp(s,"COMMON"))return int(kStdCommon);
    char name[16];
    for(unsigned i=0;i<kViews;++i)if(!std::strcmp(owner_name(i,name,sizeof(name)),s))return int(i);
    return -1;
}
bool std_hex_key(const char* s,unsigned& crc,unsigned& fnv){
    char* e=nullptr;
    crc=unsigned(std::strtoul(s,&e,16));if(e!=s+8 || *e!='-')return false;
    fnv=unsigned(std::strtoul(e+1,&e,16));return e==s+17 && !*e;
}
// Splits one line into at most kStdTokens space-separated tokens (in place).
unsigned std_tokens(char* line,char** t){
    unsigned n=0;
    for(char* s=line;*s && n<kStdTokens;){
        while(*s==' ')++s;
        if(!*s)break;
        t[n++]=s;
        while(*s && *s!=' ')++s;
        if(*s)*s++=0;
    }
    return n;
}
// Parses the index text; false (with a log line) rejects the whole index.
bool std_parse(char* text,unsigned room){
    StdRoom& r=std_room;
    unsigned lines=0;bool header=false,ended=false;
    char* next=text;
    while(*next && !ended){
        char* line=next;
        while(*next && *next!='\n')++next;
        if(*next)*next++=0;
        if(!*line)continue;                      // an empty last line
        if(*line=='#'){++lines;continue;}
        char* t[kStdTokens];const unsigned n=std_tokens(line,t);
        if(!n){++lines;continue;}
        const char* k=t[0];
        const auto num=[](const char* s){return unsigned(std::strtoul(s,nullptr,10));};
        const auto fp=[](const char* s){return float(std::strtod(s,nullptr));};
        if(!header){
            char want[8];snprintf(want,sizeof(want),"r%x%02x",room>>8,room&255U);
            if(n!=3 || std::strcmp(k,"re4dc-std") || std::strcmp(t[1],"1") || std::strcmp(t[2],want)){
                re4dc_log("quality assets: index header rejected (room %s)\n",want);return false;}
            header=true;++lines;continue;
        }
        if(!std::strcmp(k,"end")){
            if(n!=2 || num(t[1])!=lines){re4dc_log("quality assets: index end %s != %u lines\n",n>1?t[1]:"-",lines);return false;}
            ended=true;continue;
        }
        ++lines;
        if(!std::strcmp(k,"lod_px")){
            if(n>=2 && unsigned(fp(t[1])+0.5f)!=unsigned(re4dc_quality()->lod_px+0.5f))
                re4dc_log("quality assets: index lod_px %s, runtime %u\n",t[1],unsigned(re4dc_quality()->lod_px));
        }else if(!std::strcmp(k,"mesh")){
            const int v=n>=4?std_owner(t[1]):-1;
            if(v<0 || (r.mesh_views>>v)&1U){re4dc_log("quality assets: bad mesh record %s\n",n>1?t[1]:"-");return false;}
            r.mesh_views|=1U<<v;r.mesh_bytes[v]=num(t[2]);
        }else if(!std::strcmp(k,"tex")){
            StdTex x{};
            if(n<6 || !std_hex_key(t[1],x.crc,x.fnv) || r.ntex>=kStdTex){re4dc_log("quality assets: bad tex record\n");return false;}
            x.width=(unsigned short)num(t[2]);x.height=(unsigned short)num(t[3]);x.vram=num(t[4]);r.tex[r.ntex++]=x;
        }else if(!std::strcmp(k,"drop")){
            StdKey x{};
            if(n<2 || !std_hex_key(t[1],x.crc,x.fnv) || r.ndrop>=kStdDrop){re4dc_log("quality assets: bad drop record\n");return false;}
            r.drop[r.ndrop++]=x;
        }else if(!std::strcmp(k,"cull")){
            const int v=n>=6?std_owner(t[1]):-1;
            if(v<0 || r.ncull>=kStdCull){re4dc_log("quality assets: bad cull record\n");return false;}
            r.cull[r.ncull++]={(unsigned char)v,(unsigned char)(num(t[4])!=0),(unsigned short)num(t[2]),(unsigned short)num(t[3]),fp(t[5])};
        }else if(!std::strcmp(k,"imp")){
            const int v=n>=18?std_owner(t[1]):-1;
            StdImp x{};
            unsigned kc=0,kf=0;
            if(v<0 || r.nimp>=kStdImp || !std_hex_key(t[6],kc,kf)){re4dc_log("quality assets: bad imp record\n");return false;}
            x.view=(unsigned char)v;x.bin=(unsigned short)num(t[3]);x.common=(unsigned char)(num(t[4])!=0);x.mm=fp(t[5]);
            auto& q=x.rec;q.mesh=num(t[2]);q.key_crc=kc;q.key_fnv=kf;
            q.views=(std::uint16_t)num(t[7]);q.cols=(std::uint16_t)num(t[8]);q.cell_w=(std::uint16_t)num(t[9]);q.cell_h=(std::uint16_t)num(t[10]);
            q.atlas_w=(std::uint16_t)num(t[11]);q.atlas_h=(std::uint16_t)num(t[12]);
            q.centre[0]=fp(t[13]);q.centre[1]=fp(t[14]);q.centre[2]=fp(t[15]);q.half_w=fp(t[16]);q.half_h=fp(t[17]);q.reserved=0;
            if(!q.views || !q.cols || !q.cell_w || !q.cell_h || !(q.half_w>0.0f) || !(q.half_h>0.0f)){re4dc_log("quality assets: bad imp values\n");return false;}
            r.imp[r.nimp++]=x;
        }else if(!std::strcmp(k,"impt")){
            const int v=n>=21?std_owner(t[1]):-1;
            StdImpt x{};unsigned kc=0,kf=0;
            if(v<0 || r.nimpt>=kStdImpt || !std_hex_key(t[9],kc,kf)){re4dc_log("quality assets: bad impt record\n");return false;}
            x.view=(unsigned char)v;x.bin=(unsigned short)num(t[3]);x.common=(unsigned char)(num(t[4])!=0);
            x.part=(unsigned short)num(t[5]);x.first=(unsigned short)num(t[6]);x.count=(unsigned short)num(t[7]);x.mm=fp(t[8]);
            auto& q=x.rec;q.mesh=num(t[2]);q.key_crc=kc;q.key_fnv=kf;
            q.views=(std::uint16_t)num(t[10]);q.cols=(std::uint16_t)num(t[11]);q.cell_w=(std::uint16_t)num(t[12]);q.cell_h=(std::uint16_t)num(t[13]);
            q.atlas_w=(std::uint16_t)num(t[14]);q.atlas_h=(std::uint16_t)num(t[15]);
            q.centre[0]=fp(t[16]);q.centre[1]=fp(t[17]);q.centre[2]=fp(t[18]);q.half_w=fp(t[19]);q.half_h=fp(t[20]);q.reserved=0;
            if(!q.views || !q.cols || !q.cell_w || !q.cell_h || !x.count || x.first+x.count>64U || !(q.half_w>0.0f) || !(q.half_h>0.0f)){
                re4dc_log("quality assets: bad impt values\n");return false;}
            r.impt[r.nimpt++]=x;
        }else if(!std::strcmp(k,"ptex")){
            const int v=n>=8?std_owner(t[1]):-1;
            StdPtex x{};
            if(v<0 || r.nptex>=kStdPtex || !std_hex_key(t[5],x.key[0],x.key[1])){re4dc_log("quality assets: bad ptex record\n");return false;}
            x.view=(unsigned char)v;x.part=(unsigned short)num(t[2]);x.bin=(unsigned short)num(t[3]);x.common=(unsigned char)(num(t[4])!=0);
            x.key[2]=num(t[6]);x.key[3]=num(t[7]);r.ptex[r.nptex++]=x;
        }
        // orig and unknown record types: ignored (staging checks orig)
    }
    if(!header || !ended){re4dc_log("quality assets: index truncated (no end line)\n");return false;}
    return true;
}
// Verifies this view's records against the package opened for it (s16.3: mesh
// index in range with the recorded bin/common; ptex part inside such a mesh).
bool std_check_view(unsigned view,const re4dc::room::MeshPackage& pk){
    const StdRoom& r=std_room;
    const unsigned meshes=pk.header().mesh_count;
    const auto ok=[&](unsigned m,unsigned bin,unsigned common){
        return m<meshes && pk.meshes()[m].bin==bin && (pk.meshes()[m].common!=0)==(common!=0);};
    for(unsigned i=0;i<r.ncull;++i)if(r.cull[i].view==view && !ok(r.cull[i].mesh,r.cull[i].bin,r.cull[i].common))return false;
    for(unsigned i=0;i<r.nimp;++i)if(r.imp[i].view==view && !ok(r.imp[i].rec.mesh,r.imp[i].bin,r.imp[i].common))return false;
    for(unsigned i=0;i<r.nimpt;++i){
        const StdImpt& x=r.impt[i];if(x.view!=view)continue;
        if(!ok(x.rec.mesh,x.bin,x.common))return false;
        const auto& rec=pk.meshes()[x.rec.mesh];
        if(x.part<rec.first_part || x.part>=rec.first_part+rec.part_count)return false;
        if(x.first+x.count>pk.part_lods()[x.part].cluster_count)return false;
        for(unsigned j=0;j<r.nimp;++j)if(r.imp[j].view==view && r.imp[j].rec.mesh==x.rec.mesh)return false; // imp or impt, never both
    }
    for(unsigned i=0;i<r.nptex;++i){
        const StdPtex& x=r.ptex[i];if(x.view!=view)continue;
        bool found=false;
        for(unsigned m=0;m<meshes && !found;++m){
            const auto& rec=pk.meshes()[m];
            found=ok(m,x.bin,x.common) && x.part>=rec.first_part && x.part<rec.first_part+rec.part_count;
        }
        if(!found)return false;
    }
    return true;
}
#endif
void retire(View& v){
#if RE4DC_GC_ASSET_GATE
    if(v.asset_proof.owner)re4dc_gcasset::payload_invalidate(v.asset_proof,&v);
#endif
    v.package.close();
    if(v.storage){re4dc_static_free(v.storage);stats.package_bytes-=v.bytes;--stats.owners_open;}
    v.storage=nullptr;v.bytes=0;v.bindings=nullptr;v.attempted=false;v.room=0;
}

#if RE4DC_IO_ALIGNED
// Door U2: the whole file into 32-byte-aligned `dst` (room for (size+31)&~31 bytes): one KOS
// stream for size&~31 from offset 0, then fs_seek away and back (aborts the stream: KOS's own
// <32 B stream request never returns, R4_5A) and the tail through the block cache into a
// misaligned stack buffer. Returns the bytes read, or -2 for an unaligned destination. The
// caller falls back to the misaligned body read on anything short.
int read_whole_aligned(file_t f,unsigned char* dst,unsigned size){
    if(reinterpret_cast<std::uintptr_t>(dst)&31U)return -2;
    if(fs_seek(f,0,SEEK_SET)<0)return -1;
    const unsigned body=size&~31U;unsigned got=0;
    while(got<body){const ssize_t n=fs_read(f,dst+got,body-got);if(n<=0)break;got+=unsigned(n);}
    if(got==body && got<size){
        if(got){fs_seek(f,0,SEEK_SET);fs_seek(f,got,SEEK_SET);}
        alignas(32) unsigned char tail[64];                         // tail+16: misaligned on purpose
        const unsigned start=got;
        while(got<size){const ssize_t n=fs_read(f,tail+16+(got-start),size-got);if(n<=0)break;got+=unsigned(n);}
        std::memcpy(dst+start,tail+16,got-start);
    }
    return int(got);
}
unsigned aligned_reads,aligned_fallbacks;
// Aligned whole read, else today's body read after the header already in `storage`.
bool read_package(file_t f,unsigned char* storage,unsigned size,unsigned head){
    if(read_whole_aligned(f,storage,size)==int(size)){++aligned_reads;return true;}
    ++aligned_fallbacks;re4dc_log("native static: aligned read fell back (%u)\n",aligned_fallbacks);
    const ssize_t rest=ssize_t(size-head);
    return fs_seek(f,head,SEEK_SET)==off_t(head) && fs_read(f,storage+head,rest)==rest;
}
#endif
[[maybe_unused]] bool open(View& v,unsigned index,unsigned room){
    if(v.storage && v.room==room)return true;
    if(v.attempted && v.room==room)return false;
    retire(v);v.attempted=true;v.room=room;
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::payload_retire(v.asset_proof); // cold, before read/adopt
#endif
    char name[16],path[64];
    snprintf(path,sizeof(path),"/cd/dc/native/r%x%02x/%s.re4room",room>>8,room&255U,owner_name(index,name,sizeof(name)));
    const file_t file=fs_open(path,O_RDONLY);
    if(file==FILEHND_INVALID){++stats.open_failures;re4dc_log("native static: %s missing\n",path);return false;}
    const unsigned size=unsigned(fs_total(file));
    // Package bytes first (32-aligned for v4 sections), then one slot per source.
    const unsigned package_bytes=(size+31U)&~31U;
    stats.heap_before=re4dc_static_heap_free();
    unsigned char* storage=nullptr;
    if(size>=sizeof(re4dc::room::CompactHeader)){
        re4dc::room::CompactHeader header;
        if(fs_read(file,&header,sizeof(header))==ssize_t(sizeof(header)) && header.source_count<=4096){
            const unsigned bytes=package_bytes+header.source_count*unsigned(sizeof(Binding));
            storage=static_cast<unsigned char*>(re4dc_static_alloc(bytes));
            if(storage){
                v.bytes=bytes;std::memcpy(storage,&header,sizeof(header));
                const ssize_t rest=ssize_t(size-sizeof(header));
#if RE4DC_IO_ALIGNED
                (void)rest;if(!read_package(file,storage,size,unsigned(sizeof(header)))){re4dc_static_free(storage);storage=nullptr;}
#else
                if(fs_read(file,storage+sizeof(header),rest)!=rest){re4dc_static_free(storage);storage=nullptr;}
#endif
            }else ++stats.alloc_rejects;
        }
    }
    fs_close(file);
    stats.heap_after=re4dc_static_heap_free();
    if(!storage){re4dc_log("native static: %s not loaded (size=%u heap=%d)\n",path,size,stats.heap_before);return false;}
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::StaticManifest gcasset_source;
    gcasset_static_ordinary_manifest(gcasset_source,re4dc_gcasset::StaticView,room,storage,size);
#endif
    v.storage=storage;
    if(!v.package.adopt(storage,size) || !v.package.material_keys() ||
       v.package.header().material_count>kMaxMaterials){
        re4dc_log("native static: %s rejected: %s keyed=%d materials=%u\n",path,
            v.package.error()?v.package.error():"layout",v.package.material_keys(),v.package.header().material_count);
        re4dc_static_free(storage);v.storage=nullptr;v.bytes=0;v.package.close();++stats.open_failures;return false;
    }
    const auto& b=v.package.header();
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::payload_capture_composite(v.asset_proof,&v,storage,size,nullptr,0,gcasset_source);
#endif
    for(unsigned m=0;m<b.material_count;++m)
        re4dc::room::material_source_key(v.package.materials()[m],v.keys[m]);
    v.bindings=reinterpret_cast<Binding*>(storage+package_bytes);
    std::memset(v.bindings,0,v.package.compact_header()->source_count*sizeof(Binding));
    ++stats.owners_open;stats.package_bytes+=v.bytes;
    // KOS heap headroom: the source arena is a fixed 13 MiB memalign, so image
    // growth comes out of this. Free chunks plus the sbrk break (D367 failed
    // with the break 4 KiB below 0x8cff0000).
    const struct mallinfo kos=mallinfo();
    re4dc_log("native static: %s bytes=%u sources=%u groups=%u batches=%u materials=%u heap4=%d->%d kos_free=%d kos_break=%p\n",
        path,v.bytes,v.package.compact_header()->source_count,b.group_count,b.batch_count,b.material_count,
        stats.heap_before,stats.heap_after,kos.fordblks,sbrk(0));
    return true;
}

// 3x4 row-major affine helpers (GX Mtx layout).
void concat(const float* a,const float* b,float* out){
    for(unsigned r=0;r<3;++r)for(unsigned c=0;c<4;++c)
        out[4*r+c]=a[4*r]*b[c]+a[4*r+1]*b[4+c]+a[4*r+2]*b[8+c]+(c==3?a[4*r+3]:0.0f);
}
bool inverse(const float* m,float* out){
    const float a=m[0],b=m[1],c=m[2],d=m[4],e=m[5],f=m[6],g=m[8],h=m[9],i=m[10];
    const float A=e*i-f*h,B=f*g-d*i,C=d*h-e*g,det=a*A+b*B+c*C;
    if(!std::isfinite(det) || std::fabs(det)<1e-12f)return false;
    const float s=1.0f/det;
    const float r[9]={A*s,(c*h-b*i)*s,(b*f-c*e)*s,B*s,(a*i-c*g)*s,(c*d-a*f)*s,C*s,(b*g-a*h)*s,(a*e-b*d)*s};
    for(unsigned row=0;row<3;++row){
        out[4*row]=r[3*row];out[4*row+1]=r[3*row+1];out[4*row+2]=r[3*row+2];
        out[4*row+3]=-(r[3*row]*m[3]+r[3*row+1]*m[7]+r[3*row+2]*m[11]);
    }
    return true;
}

// Combined screen matrix whose W is view depth: the same mapping as
// native_model.cpp project() applied to modelview-space positions.
void load_screen(const float* mv,const float* p,const float* v){
#if RE4DC_SCENERY_REPLAY_LEAN && RE4DC_SCENERY_SCREEN_MEMO
    alignas(32) static matrix_t screen;
    static float last[20]; static bool have=false;
    // Compare the existing bitwise key in place. A memo hit needs no 80-byte
    // temporary input copy, and still reloads the matrix after a yielding bind.
    if(have && !std::memcmp(mv,last,48) && !std::memcmp(p+1,last+12,16) &&
       !std::memcmp(v,last+16,16)){mat_load(&screen);return;}
    std::memcpy(last,mv,48);std::memcpy(last+12,p+1,16);std::memcpy(last+16,v,16);have=true;
#endif
    const float sx=RE4DC_SCREEN_WF/v[2],sy=RE4DC_SCREEN_HF/v[3];
    const float row0[4]={RE4DC_SCREEN_HALF_WF*p[1],0,RE4DC_SCREEN_HALF_WF*p[2]-sx*(v[0]+v[2]*.5f),0};
    const float row1[4]={0,-RE4DC_SCREEN_HALF_HF*p[3],-RE4DC_SCREEN_HALF_HF*p[4]-sy*(v[1]+v[3]*.5f),0};
    const float row2[4]={0,0,1,0},row3[4]={0,0,-1,0};
    const float* rows[4]={row0,row1,row2,row3};
#if !(RE4DC_SCENERY_REPLAY_LEAN && RE4DC_SCENERY_SCREEN_MEMO)
    alignas(32) static matrix_t screen;
#endif
#if RE4DC_SCENERY_SCREEN_MEMO && !RE4DC_SCENERY_REPLAY_LEAN
    // SCENERY_SCREEN_MEMO (scenery19): parts of one placement bind with the same inputs; the same inputs give the
    // same matrix (identical arithmetic), so reload the last one. Exact.
    static float last[20]; static bool have=false;
    float in[20];
    std::memcpy(in,mv,48);in[12]=p[1];in[13]=p[2];in[14]=p[3];in[15]=p[4];std::memcpy(in+16,v,16);
    if(have && !std::memcmp(in,last,sizeof(in))){mat_load(&screen);return;}
    std::memcpy(last,in,sizeof(in));have=true;
#endif
#if RE4DC_SCENERY_STREAM
    // SCENERY_STREAM: the same per-element chain (start value, then += row[k] * mv[4k + c] for k = 0, 1, 2) written out
    // without the -Os loops.
#define RE4DC_LS_EL(r,c,start) {float value=(start);value+=rows[r][0]*mv[c];value+=rows[r][1]*mv[4+c];value+=rows[r][2]*mv[8+c];screen[c][r]=value;}
#define RE4DC_LS_ROW(r) RE4DC_LS_EL(r,0,0.0f) RE4DC_LS_EL(r,1,0.0f) RE4DC_LS_EL(r,2,0.0f) RE4DC_LS_EL(r,3,rows[r][3])
    RE4DC_LS_ROW(0) RE4DC_LS_ROW(1) RE4DC_LS_ROW(2) RE4DC_LS_ROW(3)
#undef RE4DC_LS_ROW
#undef RE4DC_LS_EL
#if defined(RE4DC_SCENERY_STREAM_CHECK) && RE4DC_SCENERY_STREAM_CHECK
    {   // check build: the loop form must give the same words
        float ref[4][4];
        for(unsigned r=0;r<4;++r)for(unsigned c=0;c<4;++c){
            float value=c==3?rows[r][3]:0.0f;
            for(unsigned k=0;k<3;++k)value+=rows[r][k]*mv[4*k+c];
            ref[c][r]=value;
        }
        extern unsigned stream_ls[2];++stream_ls[0];if(std::memcmp(ref,screen,sizeof(ref)))++stream_ls[1];
    }
#endif
#else
    for(unsigned r=0;r<4;++r)for(unsigned c=0;c<4;++c){
        float value=c==3?rows[r][3]:0.0f;
        for(unsigned k=0;k<3;++k)value+=rows[r][k]*mv[4*k+c];
        screen[c][r]=value; // KOS matrix_t is column-major for ftrv
    }
#endif
    mat_load(&screen);
}

struct Located { View* view; Binding* binding; unsigned source; };
bool locate(const Re4dcModelPart& p,Located& out){
    for(auto& v:views){
        if(!v.storage)continue;
        const unsigned count=v.package.compact_header()->source_count;
        for(unsigned s=0;s<count;++s){
            Binding& b=v.bindings[s];
            if(b.object!=p.model)continue;
            if(b.serial!=p.serial){++stats.stale_bindings;return false;}
            out={&v,&b,s};return true;
        }
    }
    return false;
}

// Strip emission shared by package and mesh draws: one source part's packet.
#if RE4DC_PS2_WORLD_MESH
extern "C" int re4dc_ps2_world_direct_begin(const unsigned* key,Re4dcModelDirect* out); // native_ui.cpp
#if RE4DC_SCENERY_PIECE_STATE
} // namespace: the slot word is a global C symbol
extern "C" std::uint32_t* re4dc_ps2_piece_slot; // native_ui.cpp: the slot word for the next re4dc_ps2_world_direct_begin
namespace {
#endif
#if RE4DC_SCENERY21_AB
} // namespace
extern "C" char re4dc_bench_arm(void) __attribute__((weak)); // bench.cpp: the start screen's arm
namespace {
// SCENERY21_AB (bench disc): arm B = the scenery21 data and paths (sc21/ packages), arm A = as shipped
bool scn21_arm_b(){return re4dc_bench_arm && re4dc_bench_arm()=='B';}
#endif
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
// Accumulate scalar fallback work locally; one integer-only census call on
// every exit, including a capacity failure partway through a strip.
struct Wc24Count {
    re4dc::wc24::Counter counter; unsigned n=0;
    explicit Wc24Count(re4dc::wc24::Counter c):counter(c){}
    ~Wc24Count(){if(n)re4dc::wc24::count(counter,n);}
};
// A rejected/aborted native pass may leave legacy world work outside the
// census scope. Keep that window visibly invalid instead of pricing a part.
struct Wc24PassResult {
    bool complete=false;
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    re4dc::wc24::ErrorDetail why;
    const unsigned* diag_fallback=nullptr;
    const unsigned* diag_aborts=nullptr;
    ~Wc24PassResult(){if(!complete){
        if(why.context==UINT32_MAX && diag_fallback){
            why.reason=*diag_aborts?re4dc::wc24::ErrorPassAbort:re4dc::wc24::ErrorPassIncomplete;
            why.detail0=*diag_fallback;why.detail1=*diag_aborts;
        }
        why.report();
    }}
#else
    ~Wc24PassResult(){if(!complete)re4dc::wc24::fault();}
#endif
};
#endif
struct Emitter {
    const Re4dcModelPart& p;
    float mv[12];  // package -> view: group bounds
    float near,far;
    float mvq[12]={}; // stored corner -> view (mv, or mv with the AoS12 grid folded in)
    const std::uint32_t* palette=nullptr;
    Re4dcModelPacket packet{}; pvr_vertex_t* dst=nullptr;
    unsigned used=0,input=0,output=0,alpha=0;
    unsigned limit=0; // packet slots strips may use: packet.capacity less any borrowed tail
    bool streaming=false,bound=false,submitted=false;
    bool vertex_alpha=false; // corner alpha from the colour palette (source vertex alpha)
#if RE4DC_SCENERY_DEDUP==3
    const re4dc::room::CompactVertex12* dd_base=nullptr;
    unsigned dd_unique=0,dd_count=0; // borrowed meshlet context, no allocation or retained mask
#endif
    re4dc::render::ClipParameters clip{};
#if RE4DC_PS2_WORLD_MESH
    const unsigned* ps2=nullptr; // PS2_WORLD_MESH part: {crc, fnv, width, height, pass, cull}; binds by key, not by p
#if RE4DC_SCENERY_PIECE_STATE
    std::uint32_t* piece_slot=nullptr; // SCENERY_PIECE_STATE: this part's header-slot word (SCPS), nullptr: none
#endif
#endif
#if RE4DC_HW_LEAN
    float proj_bx=0,proj_by=0; // project()'s viewport offsets in 640x480 pixels
#if RE4DC_RES_MODES
    float proj_hw=320,proj_hh=240; // RES_MODES: the render size's halves per part (project() reads no globals)
#endif
    void set_clip(){
        const float* v=p.viewport;
#if RE4DC_RES_MODES
        proj_hw=RE4DC_SCREEN_HALF_WF;proj_hh=RE4DC_SCREEN_HALF_HF;
#endif
        proj_bx=(v[0]+v[2]*.5f)*RE4DC_SCREEN_WF/v[2];proj_by=(v[1]+v[3]*.5f)*RE4DC_SCREEN_HF/v[3];
        clip={near,far,RE4DC_SCREEN_W,RE4DC_SCREEN_H,project,this};
    }
#else
    void set_clip(){clip={near,far,RE4DC_SCREEN_W,RE4DC_SCREEN_H,project,this};}
#endif

    static void project(float& x,float& y,float& z,void* context){
        const auto& d=*static_cast<const Emitter*>(context);
        const float* p=d.p.projection;const float* v=d.p.viewport;
#if RE4DC_HW_LEAN && defined(__sh__)
        // 1/|z| by fsrra(z*z): the clipper only keeps corners with depth=-z >= near > 0.
        // The viewport terms are per part (proj_setup): v[2]*.5*W/v[2] = W/2, v[3]*.5*H/v[3] = H/2 for the current
        // render size (RES_MODES: 320/120 in a 240-line mode; the defaults are the 640x480 constants).
        float inv=z*z;
        __asm__("fsrra %0" : "+f"(inv));
        (void)v;
#if RE4DC_RES_MODES
        x=d.proj_hw*(p[1]*x+p[2]*z)*inv+d.proj_bx;
        y=-d.proj_hh*(p[3]*y+p[4]*z)*inv+d.proj_by;
#else
        x=RE4DC_SCREEN_HALF_WF*(p[1]*x+p[2]*z)*inv+d.proj_bx;
        y=-RE4DC_SCREEN_HALF_HF*(p[3]*y+p[4]*z)*inv+d.proj_by;
#endif
        z=inv;
        return;
#else
        const float inv=1.0f/(-z);
#endif
        x=(v[2]*.5f*(p[1]*x+p[2]*z)*inv+v[0]+v[2]*.5f)*RE4DC_SCREEN_WF/v[2];
        y=(-v[3]*.5f*(p[3]*y+p[4]*z)*inv+v[1]+v[3]*.5f)*RE4DC_SCREEN_HF/v[3];
        z=inv;
    }
#if RE4DC_MESH_DIRECT
    // Store-queue sink (MeshDraw only): the header goes to the TA at bind(),
    // strips follow as they are accepted; the slab range is staging for the
    // clipper and the transform cache only. Nothing can be rolled back once
    // bound, so later failures abort the frame (submitted).
    bool direct=false; std::uint32_t* sq=nullptr; unsigned slots=0;
#if RE4DC_SCENERY_SUBMIT_BATCH
    Re4dcWorldSubmitBatch* submit_batch=nullptr; // borrowed only inside chunk_flush
    void end_direct(){if(sq){
        if(submit_batch)re4dc_ps2_world_direct_end_batch(slots,submit_batch);
        else re4dc_model_direct_end(slots);
        sq=nullptr;
    }}
#else
    void end_direct(){if(sq){re4dc_model_direct_end(slots);sq=nullptr;}}
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
#define RE4DC_WC24_PUT_SCOPE() const re4dc::wc24::Scope wc_submit(re4dc::wc24::Submit);
#else
#define RE4DC_WC24_PUT_SCOPE()
#endif
    void put(unsigned n){RE4DC_WC24_PUT_SCOPE()sq=re4dc_ta_put(sq,dst+used,n);slots+=n;}
#undef RE4DC_WC24_PUT_SCOPE
#endif
    bool bind(){
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        const re4dc::wc24::Scope wc_header(re4dc::wc24::HeaderMaterial);
#endif
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
        // Claimed transition groups may log from the validity walk itself.
        if(submit_batch && !sq && re4dc_source_world_group_claimed())
            re4dc_ps2_world_batch_close(submit_batch);
        if(!re4dc_source_world_binding_valid()){
            // A new part has not bound yet; release the previous part's idle
            // lock before the existing owner-failure/abort callback.
            if(submit_batch && !sq)re4dc_ps2_world_batch_close(submit_batch);
            re4dc_source_world_binding_failed();return false;
        }
#else
        if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return false;}
#endif
#endif
        if(bound)return true;
#if RE4DC_MV_SHADOWS
        struct MvReceiver{MvReceiver(){re4dc_mv_receiver=1;}~MvReceiver(){re4dc_mv_receiver=0;}} mv_receiver;
        if(p.projection[0]==0 && p.viewport[2]>0 && p.viewport[3]>0 && re4dc_mv_camera_frame!=re4dc_ui_frame()){
            std::memcpy(re4dc_mv_projection,p.projection,sizeof(re4dc_mv_projection));
            std::memcpy(re4dc_mv_viewport,p.viewport,sizeof(re4dc_mv_viewport));
            re4dc_mv_camera_frame=re4dc_ui_frame();
        }
#endif
#if defined(RE4DC_SHADOW_BLOB) && RE4DC_SHADOW_BLOB
        if(p.projection[0]==0 && p.viewport[2]>0 && p.viewport[3]>0 && re4dc_blob_camera_frame!=re4dc_ui_frame()){
            std::memcpy(re4dc_blob_projection,p.projection,sizeof(re4dc_blob_projection));
            std::memcpy(re4dc_blob_viewport,p.viewport,sizeof(re4dc_blob_viewport));
            re4dc_blob_camera_frame=re4dc_ui_frame();
        }
#endif
#if RE4DC_MESH_DIRECT
        if(direct){
            Re4dcModelDirect out{};
#if RE4DC_PS2_WORLD_MESH
#if RE4DC_SCENERY_PIECE_STATE
            re4dc_ps2_piece_slot=ps2?piece_slot:nullptr;
#if RE4DC_SCENERY_SUBMIT_BATCH
            const int begun=ps2?(submit_batch?re4dc_ps2_world_direct_begin_batch(ps2,&out,submit_batch):
                                re4dc_ps2_world_direct_begin(ps2,&out)):re4dc_model_direct_begin(&p,&out);
#else
            const int begun=ps2?re4dc_ps2_world_direct_begin(ps2,&out):re4dc_model_direct_begin(&p,&out);
#endif
            re4dc_ps2_piece_slot=nullptr;
            if(!begun)return false;
#else
#if RE4DC_SCENERY_SUBMIT_BATCH
            if(!(ps2?(submit_batch?re4dc_ps2_world_direct_begin_batch(ps2,&out,submit_batch):
                                  re4dc_ps2_world_direct_begin(ps2,&out)):re4dc_model_direct_begin(&p,&out)))return false;
#else
            if(!(ps2?re4dc_ps2_world_direct_begin(ps2,&out):re4dc_model_direct_begin(&p,&out)))return false;
#endif
#endif
#else
            if(!re4dc_model_direct_begin(&p,&out))return false;
#endif
            sq=out.sq;submitted=true;
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
            if(!re4dc_source_world_binding_valid()){
#if RE4DC_SCENERY_SUBMIT_BATCH
                end_direct();
                if(submit_batch)re4dc_ps2_world_batch_close(submit_batch);
                re4dc_source_world_binding_failed();return false;
#else
                end_direct();re4dc_source_world_binding_failed();return false;
#endif
            }
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
            if(!re4dc_r11f_binding_valid()) {
#if RE4DC_SCENERY_SUBMIT_BATCH
                end_direct();
                if(submit_batch)re4dc_ps2_world_batch_close(submit_batch);
                re4dc_r11f_binding_failed();return false;
#else
                end_direct();re4dc_r11f_binding_failed();return false;
#endif
            }
#endif
            packet.vertices=out.scratch;packet.capacity=out.scratch_capacity;
            packet.u_scale=out.u_scale;packet.v_scale=out.v_scale;
            dst=static_cast<pvr_vertex_t*>(out.scratch);bound=true;limit=out.scratch_capacity;
            load_screen(mvq,p.projection,p.viewport); // binding may yield
            return true;
        }
#endif
        if(!re4dc_model_packet_begin(&p,&packet))return false;
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
        if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return false;}
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
        if(!re4dc_r11f_binding_valid()){re4dc_r11f_binding_failed();return false;}
#endif
        dst=static_cast<pvr_vertex_t*>(packet.vertices);bound=true;limit=packet.capacity;
        load_screen(mvq,p.projection,p.viewport); // binding may yield
        return true;
    }
    bool flush(){
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        const re4dc::wc24::Scope wc_submit(re4dc::wc24::Submit);
#endif
        if(!streaming || !used)return false;
        re4dc_model_packet_commit(used);submitted=true;used=0;
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
        if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return false;}
#endif
        load_screen(mvq,p.projection,p.viewport);
        return true;
    }
    float u(float value)const{return (value+p.uv_offset[0])*packet.u_scale;}
    float v(float value)const{return (value+p.uv_offset[1])*packet.v_scale;}
    // AoS12 corners stay in grid units: mvq folds origin + q * step in, so the
    // per-corner cost is three integer conversions, not a dequantize.
    re4dc::render::StaticCorner corner(const re4dc::room::CompactVertex& in)const{
        return {in.x,in.y,in.z,in.u,in.v,in.argb};
    }
    // Packages index a palette; lit meshes (palette==nullptr) store ARGB1555.
    [[gnu::always_inline]] static std::uint32_t argb1555(std::uint16_t c){
        const std::uint32_t r=(c>>10)&31U,g=(c>>5)&31U,b=c&31U;
        return ((c&0x8000U)?0xff000000U:0U)|(((r<<3)|(r>>2))<<16)|(((g<<3)|(g>>2))<<8)|((b<<3)|(b>>2));
    }
    // Per corner: this unit is -Os, which otherwise keeps the decode out of line.
#if RE4DC_PS2_VERTEX_ALPHA
    // PS2_VERTEX_ALPHA (game30.mk): a marked PS2 world part stores ARGB4444 corner colours (the vertex alpha).
    bool c4444=false;
    [[gnu::always_inline]] static std::uint32_t argb4444(std::uint16_t c){
        return ((c>>12)&15U)*0x11000000U|((c>>8)&15U)*0x110000U|((c>>4)&15U)*0x1100U|(c&15U)*0x11U;
    }
    [[gnu::always_inline]] re4dc::render::StaticCorner corner(const re4dc::room::CompactVertex12& in)const{
#if RE4DC_SCENERY_DEDUP==3
        const auto& xyz=re4dc::room::MeshPackage::offline_position(dd_base,dd_unique,dd_count,in);
        return {float(xyz.x),float(xyz.y),float(xyz.z),in.u,in.v,
                palette?palette[in.color]:c4444?argb4444(in.color):argb1555(in.color)};
#else
        return {float(in.x),float(in.y),float(in.z),in.u,in.v,
                palette?palette[in.color]:c4444?argb4444(in.color):argb1555(in.color)};
#endif
    }
#else
    [[gnu::always_inline]] re4dc::render::StaticCorner corner(const re4dc::room::CompactVertex12& in)const{
#if RE4DC_SCENERY_DEDUP==3
        const auto& xyz=re4dc::room::MeshPackage::offline_position(dd_base,dd_unique,dd_count,in);
        return {float(xyz.x),float(xyz.y),float(xyz.z),in.u,in.v,palette?palette[in.color]:argb1555(in.color)};
#else
        return {float(in.x),float(in.y),float(in.z),in.u,in.v,palette?palette[in.color]:argb1555(in.color)};
#endif
    }
#endif
    void clip_vertex(const re4dc::render::StaticCorner& in,const re4dc::room::CompactBatch& batch,
                     re4dc::render::RenderVertex& out){
        float x=mvq[0]*in.x+mvq[1]*in.y+mvq[2]*in.z+mvq[3];
        float y=mvq[4]*in.x+mvq[5]*in.y+mvq[6]*in.z+mvq[7];
        float z=mvq[8]*in.x+mvq[9]*in.y+mvq[10]*in.z+mvq[11];
#if RE4DC_COPY_LEAN
        out.offset_color=0; // every other field is assigned below (no 52-byte memset per corner)
#else
        out={};
#endif
        out.position.world_x=x;out.position.world_y=y;out.position.world_z=z;out.position.depth=-z;
        if(z!=0)project(x,y,z,this);
        out.position.x=x;out.position.y=y;out.position.z=z;
        out.u=u(batch.uv_bias[0]+float(in.u)*batch.uv_scale[0]);
        out.v=v(batch.uv_bias[1]+float(in.v)*batch.uv_scale[1]);
        out.light_red=float((in.argb>>16)&255U)RE4DC_INV255;
        out.light_green=float((in.argb>>8)&255U)RE4DC_INV255;
        out.light_blue=float(in.argb&255U)RE4DC_INV255;
    }
    // 1 emitted/culled, 0 failed before anything was published, -1 failed after.
    template<class Vertex,class Index>
    int strip(const Vertex* base,const re4dc::room::CompactBatch& batch,
              const Index* index,unsigned count){
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        re4dc::wc24::Scope wc_phase(re4dc::wc24::Transform);
        re4dc::wc24::count(re4dc::wc24::StripInputs,count);
        Wc24Count wc_transformed(re4dc::wc24::Transformed);
#endif
        input+=count-2;
        if(count<=limit){
            if(count>limit-used && !flush())return submitted?-1:0;
            unsigned outside=15;
            const float screen_w=RE4DC_SCREEN_WF,screen_h=RE4DC_SCREEN_HF; // RES_MODES: one load per strip, not per corner
            const bool ready=re4dc::render::prepare_direct_strip(dst+used,count,near,far,
                [&](std::uint32_t local,re4dc::render::DirectStripVertex& out){
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
                    ++wc_transformed.n;
#endif
                    out=re4dc::render::prepare_static_vertex(corner(base[index[local]]),batch,0.0f);
                    out.u=u(out.u);out.v=v(out.v);
                    if(!vertex_alpha)out.argb=(out.argb&0xffffffU)|alpha;
                    outside&=(out.x<0?1U:0U)|(out.x>screen_w?2U:0U)|(out.y<0?4U:0U)|(out.y>screen_h?8U:0U);
                    return true;
                });
            stats.vertices+=count;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
            wc_phase.phase(re4dc::wc24::Submit);
#endif
            if(ready){
                if(outside)++stats.strips_culled;
#if RE4DC_MESH_DIRECT
                else if(sq){put(count);output+=count-2;++stats.strips;}
#endif
                else {used+=count;output+=count-2;++stats.strips;}
                return 1;
            }
        }
        return clip_strip(base,batch,index,count);
    }
    // Near/far crossing or oversize: the shared clipper, triangle by triangle,
    // keeping strip winding (odd triangles swap their first two corners).
    // input was already counted by the caller.
    template<class Vertex,class Index>
    int clip_strip(const Vertex* base,const re4dc::room::CompactBatch& batch,
                   const Index* index,unsigned count){
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        const re4dc::wc24::Scope wc_clip(re4dc::wc24::Clip);
        Wc24Count wc_transformed(re4dc::wc24::Transformed);
#endif
        ++stats.strips_clipped;
        float alphas[3]={float(alpha>>24)RE4DC_INV255,float(alpha>>24)RE4DC_INV255,float(alpha>>24)RE4DC_INV255};
#if RE4DC_MESH_CLIP_LEAN && RE4DC_HW_LEAN && defined(__sh__)
        // MESH_CLIP_LEAN (exact in pixels). 1) A strip whose corners are all outside one plane of the
        // frustum {0<=X<=640W, 0<=Y<=480W, near<=W<=far} (homogeneous screen coordinates, W=-z; the
        // test holds behind the camera too, the region being convex) draws nothing: the clipper would
        // only produce triangles off that screen edge or outside near/far. 2) Each corner goes through
        // clip_vertex once, not once per triangle that uses it (the same values, reused).
        {
            const float* pp=p.projection;
            const float screen_w=RE4DC_SCREEN_WF,screen_h=RE4DC_SCREEN_HF,half_w=RE4DC_SCREEN_HALF_WF,half_h=RE4DC_SCREEN_HALF_HF;
            unsigned all=0x3fU;
            for(unsigned i=0;i<count && all;++i){
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
                ++wc_transformed.n;
#endif
                const auto c=corner(base[index[i]]);
                const float x=mvq[0]*c.x+mvq[1]*c.y+mvq[2]*c.z+mvq[3];
                const float y=mvq[4]*c.x+mvq[5]*c.y+mvq[6]*c.z+mvq[7];
                const float z=mvq[8]*c.x+mvq[9]*c.y+mvq[10]*c.z+mvq[11];
                const float W=-z;
                const float X=half_w*(pp[1]*x+pp[2]*z)+proj_bx*W, Y=-half_h*(pp[3]*y+pp[4]*z)+proj_by*W;
                all&=(X<0.0f?1U:0U)|(X>screen_w*W?2U:0U)|(Y<0.0f?4U:0U)|(Y>screen_h*W?8U:0U)|
                     (W<near?16U:0U)|(W>far?32U:0U);
            }
            if(all){++stats.strips_culled;return 1;}
        }
#if RE4DC_MESH_CLIP_ACCEPT
        // MESH_CLIP_ACCEPT (game30.mk; the same TA words). Corner i goes through clip_vertex once, into a ring of the
        // strip's last three corners (s2 = i-2, s1 = i-1, s0 = i; any strip length), and is packed at most once the
        // way clip_projected_triangle writes an accepted corner (shade_color, then the alpha byte from the same float).
        // Per triangle (strip winding: odd triangles swap their first two corners), the clipper's own cases:
        // all three corners at depth >= near = its accept (the same beyond-far and triangle_visible_xy tests, then
        // the packed corners, EOL on the third), none = it emits nothing, a crossing = clip_projected_triangle.
        if(RE4DC_CLIP_ACCEPT_ON){
            re4dc::render::RenderVertex ring[3];float ring_alpha[3];
            // A corner is packed (8 words) the first time an accepted triangle uses it; corners of dropped and
            // crossing triangles never are.
            typedef std::uint32_t __attribute__((may_alias)) Word;
            alignas(4) Word packed[3][8];bool is_packed[3];
            const auto pack=[&](unsigned s){
                if(is_packed[s])return;
                is_packed[s]=true;
                // pvr_geometry.cpp's shade_color and alpha byte, inline: static_cast<uint32_t>(std::clamp(f*255, 0, 255)).
                const auto byte=[](float f){const float x=f*255.0f;return static_cast<std::uint32_t>(x<0.0f?0.0f:255.0f<x?255.0f:x);};
                const re4dc::render::RenderVertex& r=ring[s];Word* w=packed[s];
                w[0]=PVR_CMD_VERTEX;w[1]=__builtin_bit_cast(std::uint32_t,r.position.x);w[2]=__builtin_bit_cast(std::uint32_t,r.position.y);
                w[3]=__builtin_bit_cast(std::uint32_t,r.position.z);w[4]=__builtin_bit_cast(std::uint32_t,r.u);w[5]=__builtin_bit_cast(std::uint32_t,r.v);
                w[6]=(byte(ring_alpha[s])<<24U)|(byte(r.light_red)<<16U)|(byte(r.light_green)<<8U)|byte(r.light_blue);
                w[7]=r.offset_color;
            };
            const float near_d=clip.near_distance,far_d=clip.far_distance;
            unsigned s2=0,s1=1,s0=2;
            for(unsigned i=0;i<count;++i){
                {const unsigned t=s2;s2=s1;s1=s0;s0=t;}
                const re4dc::render::StaticCorner c=corner(base[index[i]]);
                re4dc::render::RenderVertex& v=ring[s0];
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
                ++wc_transformed.n;
#endif
                clip_vertex(c,batch,v);
                ring_alpha[s0]=vertex_alpha?float(c.argb>>24)RE4DC_INV255:alphas[0];
                is_packed[s0]=false;
                if(i<2)continue;
                const unsigned ia=(i&1)?s1:s2,ib=(i&1)?s2:s1;
                if(limit-used<6 && !flush())return submitted?-1:0;
                const re4dc::render::RenderVertex& va=ring[ia];const re4dc::render::RenderVertex& vb=ring[ib];
                const unsigned inside=(va.position.depth>=near_d?1U:0U)+(vb.position.depth>=near_d?1U:0U)+(v.position.depth>=near_d?1U:0U);
                unsigned emitted=0;
                if(inside==3U){
                    if(!(va.position.depth>far_d && vb.position.depth>far_d && v.position.depth>far_d) &&
                       re4dc::render::triangle_visible_xy(va.position,vb.position,v.position,p.cull,clip.width,clip.height)){
                        pack(ia);pack(ib);pack(s0);
                        Word* o=reinterpret_cast<Word*>(dst+used);
                        for(unsigned k=0;k<8;++k){o[k]=packed[ia][k];o[8+k]=packed[ib][k];o[16+k]=packed[s0][k];}
                        o[16]=PVR_CMD_VERTEX_EOL;
                        emitted=1;
                    }
                }else if(inside){
                    const re4dc::render::RenderVertex tri[3]={va,vb,v};
                    const float ta[3]={ring_alpha[ia],ring_alpha[ib],ring_alpha[s0]};
                    emitted=re4dc::render::clip_projected_triangle(tri,dst+used,p.cull,clip,nullptr,ta);
                }
#if RE4DC_MESH_CLIP_ACCEPT==2
                if(inside==3U || !inside){
                    // The clipper on the same corners into scratch: the same triangle count and words.
                    alignas(32) pvr_vertex_t ref[6];
                    const re4dc::render::RenderVertex tri[3]={va,vb,v};
                    const float ta[3]={ring_alpha[ia],ring_alpha[ib],ring_alpha[s0]};
                    const unsigned n=re4dc::render::clip_projected_triangle(tri,ref,p.cull,clip,nullptr,ta);
                    ++clip_accept_stats[inside?0:1];
                    if((n!=emitted || (n && std::memcmp(ref,dst+used,3*sizeof(pvr_vertex_t)))) && ++clip_accept_stats[2]<=8)
                        re4dc_log("CLIPACC mismatch inside=%u n=%u/%u\n",inside,emitted,n);
                }else ++clip_accept_stats[3];
#endif
#if RE4DC_MESH_DIRECT
                if(sq){if(emitted)put(emitted*3);output+=emitted;stats.triangles_clipped+=emitted;continue;}
#endif
                used+=emitted*3;output+=emitted;stats.triangles_clipped+=emitted;
            }
            return 1;
        }
#endif
        if(count<=kClipOnce){
            re4dc::render::RenderVertex once[kClipOnce];float once_alpha[kClipOnce];
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
            wc_transformed.n+=count;
#endif
            for(unsigned i=0;i<count;++i){
                const re4dc::render::StaticCorner c=corner(base[index[i]]);
                clip_vertex(c,batch,once[i]);
                once_alpha[i]=vertex_alpha?float(c.argb>>24)RE4DC_INV255:alphas[0];
            }
            for(unsigned i=2;i<count;++i){
                const unsigned ia=i-2+(i&1),ib=i-1-(i&1);
                const re4dc::render::RenderVertex tri[3]={once[ia],once[ib],once[i]};
                const float ta[3]={once_alpha[ia],once_alpha[ib],once_alpha[i]};
                if(limit-used<6 && !flush())return submitted?-1:0;
                const unsigned emitted=re4dc::render::clip_projected_triangle(tri,dst+used,p.cull,clip,nullptr,ta);
#if RE4DC_MESH_DIRECT
                if(sq){if(emitted)put(emitted*3);output+=emitted;stats.triangles_clipped+=emitted;continue;}
#endif
                used+=emitted*3;output+=emitted;stats.triangles_clipped+=emitted;
            }
            return 1;
        }
#endif
        for(unsigned i=2;i<count;++i){
            re4dc::render::RenderVertex tri[3];
            const re4dc::render::StaticCorner corners[3]={corner(base[index[i-2+(i&1)]]),
                corner(base[index[i-1-(i&1)]]),corner(base[index[i]])};
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
            wc_transformed.n+=3U;
#endif
            for(unsigned k=0;k<3;++k){
                clip_vertex(corners[k],batch,tri[k]);
                if(vertex_alpha)alphas[k]=float(corners[k].argb>>24)RE4DC_INV255;
            }
            if(limit-used<6 && !flush())return submitted?-1:0;
            const unsigned emitted=re4dc::render::clip_projected_triangle(tri,dst+used,p.cull,clip,nullptr,alphas);
#if RE4DC_MESH_DIRECT
            if(sq){if(emitted)put(emitted*3);output+=emitted;stats.triangles_clipped+=emitted;continue;}
#endif
            used+=emitted*3;output+=emitted;stats.triangles_clipped+=emitted;
        }
        return 1;
    }
};
struct Draw : Emitter {
    View& view; unsigned material;
    // 1 drawn (possibly nothing visible), 0 fallback allowed, -1 frame aborted.
    int run(const re4dc::room::CompactSourceRange& range){
        const auto& package=view.package;
        if(!re4dc_model_packet_reserve(&p,&packet)){++stats.reserve_rejects;return 0;}
        streaming=re4dc_model_packet_streaming()!=0;
#if RE4DC_HW_LEAN
        set_clip();
#else
        clip={near,far,RE4DC_SCREEN_W,RE4DC_SCREEN_H,project,static_cast<Emitter*>(this)};
#endif
        const auto* groups=package.compact_groups();
        const auto* batches=package.compact_batches();
        const auto* vertices=package.compact_vertices();
        const auto* vertices12=package.compact_vertices12();
        palette=package.compact_palette();
        const auto* prims=package.primitives();
        const auto* strip_index=package.local_primitive_indices();
        const auto* triangle_index=package.local_indices();
        for(unsigned g=range.first_group;g<range.first_group+range.group_count;++g){
            const auto& group=groups[g];
            bool has=false;
            for(unsigned k=0;k<group.batch_count && !has;++k)has=batches[group.first_batch+k].draw.material==material;
            if(!has)continue;
            const re4dc::render::DrawBounds bounds{{group.bounds_min[0],group.bounds_min[1],group.bounds_min[2]},
                                                   {group.bounds_max[0],group.bounds_max[1],group.bounds_max[2]}};
            if(!re4dc::render::group_visible(bounds,mv,p.projection,p.viewport,near,far,0)){++stats.groups_culled;continue;}
            ++stats.groups_visible;
            if(!bind()){++stats.bind_rejects;return submitted?-1:0;}
            for(unsigned k=0;k<group.batch_count;++k){
                const auto& batch=batches[group.first_batch+k];
                if(batch.draw.material!=material)continue;
                ++stats.batches;
                const auto walk=[&](const auto* base){
                    int result=1;
                    if(batch.draw.flags&re4dc::room::kBatchTrianglesResident){
                        for(unsigned t=0;t<batch.draw.index_count && result>0;t+=3)
                            result=strip(base,batch,triangle_index+batch.draw.first_index+t,3);
                    }else for(unsigned s=0;s<batch.draw.primitive_count && result>0;++s){
                        const auto& prim=prims[batch.draw.first_primitive+s];
                        result=strip(base,batch,strip_index+prim.first_vertex,prim.vertex_count);
                    }
                    return result;
                };
                const int result=vertices12?walk(vertices12+batch.first_vertex):walk(vertices+batch.first_vertex);
                if(result<=0)return result;
            }
        }
        if(used)re4dc_model_packet_commit(used);
        re4dc_model_result(0,input,output);
        return 1;
    }
};

#if RE4DC_NATIVE_MESH
// Instanced native meshes (R4IM): one per source BIN in model space, drawn with
// the part's live source modelview. setObj records object -> mesh in its
// owner's table (inside the owner's allocation); the room's common BIN set is
// a seventh view owned with the room.
// The table holds one entry per placement: 4 per packaged BIN (r101: 209
// placements of 81 BINs, r103: 286 of 119), a power of two from 128 to 1024.
constexpr unsigned kMeshViews=kViews+1,kCommonView=kViews,kEntries=128,kEntriesMax=1024;
unsigned entries_for(unsigned meshes){unsigned n=kEntries;while(n<4U*meshes && n<kEntriesMax)n<<=1;return n;}
struct MeshEntry { const void* object; std::uint16_t mesh; std::uint8_t common,used; };
struct MeshView {
    re4dc::room::MeshPackage package;
    unsigned char* storage=nullptr; unsigned bytes=0;
    MeshEntry* entries=nullptr; unsigned capacity=0; // owner views only
    const std::uint32_t* lut=nullptr; // ARGB1555 -> 8888 halves, same allocation
    re4dc::room::CompactVertex12* gather=nullptr; // v3: one meshlet's gathered corners, same allocation
    unsigned room=0; bool attempted=false;
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::PayloadProof asset_proof;
#endif
#if RE4DC_SCENERY_ENCODING
    const std::uint32_t* vertex_colors=nullptr; // kColorOctVertex: each vertex's CLR0 (ARGB8888), read in place of the palette
#endif
};
MeshView mesh_views[kMeshViews];
#if RE4DC_GC_ASSET_GATE
void gcasset_static_invalidate_all(){
    for(auto& v:views)if(v.asset_proof.owner)re4dc_gcasset::payload_invalidate(v.asset_proof,&v);
    for(auto& v:mesh_views)if(v.asset_proof.owner)re4dc_gcasset::payload_invalidate(v.asset_proof,&v);
    gcasset_invalidate_world();
}
#endif
#if RE4DC_TREE_IMPOSTOR
// This frame's impostor quads (screen x, y, 1/w per corner: TL, TR, BL, BR),
// sent per atlas by re4dc_static_flush_impostors(). A retired view clears it.
struct ImpostorQuad { const re4dc::room::MeshImpostor* record; std::uint32_t argb; std::uint16_t cell; std::uint8_t fog,pad; float s[4][3];
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::PayloadQuadUse source;
#endif
};
constexpr unsigned kImpostorQuads=48;
ImpostorQuad impostor_queue[kImpostorQuads];
unsigned impostor_count=0,impostor_frame=~0U,impostor_flushed=~0U;
const void* impostor_object=nullptr; bool impostor_queued=false; // the last first-part decision
unsigned impostor_stats[4]; // quads queued, parts skipped, queue full, batches sent
#endif
#if RE4DC_MESH_FASTPATH
constexpr unsigned kLutBytes=512*4;
#else
constexpr unsigned kLutBytes=0;
#endif
// v3: a meshlet has at most 256 corners (R4IM meshlet bound).
constexpr unsigned kGatherBytes=(256U*unsigned(sizeof(re4dc::room::CompactVertex12))+31U)&~31U;

void retire(MeshView& v){
#if RE4DC_GC_ASSET_GATE
    if(v.asset_proof.owner)re4dc_gcasset::payload_invalidate(v.asset_proof,&v);
#endif
#if RE4DC_TREE_IMPOSTOR
    impostor_frame=~0U; // queued records may point into this view
#endif
    v.package.close();
    if(v.storage){re4dc_static_free(v.storage);stats.package_bytes-=v.bytes;--stats.owners_open;}
    v.storage=nullptr;v.bytes=0;v.entries=nullptr;v.capacity=0;v.lut=nullptr;v.gather=nullptr;v.attempted=false;v.room=0;
#if RE4DC_SCENERY_ENCODING
    v.vertex_colors=nullptr;
#endif
}

bool open(MeshView& v,unsigned index,unsigned room){
    if(v.storage && v.room==room)return true;
    if(v.attempted && v.room==room)return false;
    retire(v);v.attempted=true;v.room=room;
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::payload_retire(v.asset_proof); // cold, before read/adopt
#endif
    char name[16],path[64];
    if(index==kCommonView)snprintf(name,sizeof(name),"COMMON");
    else owner_name(index,name,sizeof(name));
    snprintf(path,sizeof(path),"/cd/dc/native/r%x%02x/%s.re4mesh",room>>8,room&255U,name);
#if RE4DC_QUALITY_ASSETS
    const unsigned view=unsigned(&v-mesh_views);
    const bool low=std_room.active && std_room.room==room && ((std_room.mesh_views>>view)&1U);
    if(low){snprintf(path,sizeof(path),"/cd/dc/native/r%x%02x/low/%s.re4mesh",room>>8,room&255U,name);++std_stats[3];}
#endif
    const file_t file=fs_open(path,O_RDONLY);
    if(file==FILEHND_INVALID){++stats.open_failures;re4dc_log("native mesh: %s missing\n",path);return false;}
    const unsigned size=unsigned(fs_total(file));
#if RE4DC_QUALITY_ASSETS
    if(low && size!=std_room.mesh_bytes[view]){
#if RE4DC_GC_ASSET_GATE
        gcasset_static_invalidate_all();
        re4dc_gcasset::payload_invalidate(std_room.asset_proof,&std_room);
#endif
        re4dc_log("quality assets: %s is %u B, index says %u: Original package\n",path,size,std_room.mesh_bytes[view]);
        fs_close(file);std_room.mesh_views&=~(1U<<view);v.attempted=false;return open(v,index,room);
    }
#endif
    const unsigned package_bytes=(size+31U)&~31U;
    // Header first: the placement table is sized from its mesh count.
    re4dc::room::MeshHeader head{};
    const bool headed=size>=sizeof(head) && fs_read(file,&head,sizeof(head))==ssize_t(sizeof(head));
    const unsigned capacity=index==kCommonView?0U:entries_for(headed?head.mesh_count:0U);
    const unsigned table=capacity*unsigned(sizeof(MeshEntry));
    // v3 indexed meshlets gather their corners here (kGatherBytes after the LUT): heap 4, not the
    // packet range (with MESH_DIRECT only ~400 slots remain there after the part headers, less than
    // the transform cache plus a gather) and not static storage (the KOS heap has a few KiB).
    const unsigned gather=headed && head.version==3?kGatherBytes:0U;
    stats.heap_before=re4dc_static_heap_free();
    auto* storage=headed?static_cast<unsigned char*>(re4dc_static_alloc(package_bytes+table+kLutBytes+gather)):nullptr;
    const ssize_t rest=ssize_t(size-sizeof(head));
    if(!storage){if(headed)++stats.alloc_rejects;}
    else{
        std::memcpy(storage,&head,sizeof(head));
#if RE4DC_IO_ALIGNED
        (void)rest;if(!read_package(file,storage,size,unsigned(sizeof(head)))){re4dc_static_free(storage);storage=nullptr;}
#else
        if(fs_read(file,storage+sizeof(head),rest)!=rest){re4dc_static_free(storage);storage=nullptr;}
#endif
    }
    fs_close(file);
    stats.heap_after=re4dc_static_heap_free();
    if(!storage){re4dc_log("native mesh: %s not loaded (size=%u heap=%d)\n",path,size,stats.heap_before);return false;}
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::StaticManifest gcasset_source;
    gcasset_static_ordinary_manifest(gcasset_source,re4dc_gcasset::StaticMesh,room,storage,size);
#endif
#if RE4DC_SCENERY_ENCODING
    if(!re4dc::room::adopt_by_encoding(v.package,storage,size,RE4DC_MESH_LOD!=0,&v.vertex_colors)){
#else
    if(!v.package.adopt(storage,size,RE4DC_MESH_LOD!=0)){
#endif
        re4dc_log("native mesh: %s rejected: %s\n",path,v.package.error());
        re4dc_static_free(storage);++stats.open_failures;
#if RE4DC_QUALITY_ASSETS
        // A rejected Standard package: this owner opens its Original package instead.
        if(low){
#if RE4DC_GC_ASSET_GATE
            gcasset_static_invalidate_all();
            re4dc_gcasset::payload_invalidate(std_room.asset_proof,&std_room);
#endif
            std_room.mesh_views&=~(1U<<view);v.attempted=false;re4dc_log("quality assets: Original package for this owner\n");return open(v,index,room);}
#endif
        return false;
    }
    v.storage=storage;v.bytes=package_bytes+table+kLutBytes+gather;
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::payload_capture_composite(v.asset_proof,&v,storage,size,nullptr,0,gcasset_source);
#endif
#if RE4DC_SCENERY_ENCODING
    {
        std::uint32_t encoding;std::memcpy(&encoding,storage+offsetof(re4dc::room::MeshHeader,reserved),4);
        re4dc_log("native mesh: %s color encoding %u (%s)\n",path,unsigned(encoding),
            encoding==re4dc::room::kColorArgb1555?"prelit ARGB1555, parts marked lit":
            v.vertex_colors?"oct + vertex colours, lit at first draw":"oct, lit at first draw");
    }
#endif
#if RE4DC_QUALITY_ASSETS
    // Per-mesh records apply only to the package they were built against.
    if(std_room.active && std_room.room==room){
        if(!low || !std_check_view(view,v.package)){
            if(low)re4dc_log("quality assets: %s records do not match the package: records off for this room\n",path);
            if(low){
#if RE4DC_GC_ASSET_GATE
                gcasset_static_invalidate_all();
                re4dc_gcasset::payload_invalidate(std_room.asset_proof,&std_room);
#endif
                std_room.ncull=std_room.nimp=std_room.nptex=std_room.nimpt=0;}
        }else std_room.checked|=1U<<view;
    }
#endif
    if(gather)v.gather=reinterpret_cast<re4dc::room::CompactVertex12*>(storage+package_bytes+table+kLutBytes);
    if(table){v.entries=reinterpret_cast<MeshEntry*>(storage+package_bytes);v.capacity=capacity;std::memset(v.entries,0,table);}
#if RE4DC_MESH_FASTPATH
    auto* lut=reinterpret_cast<std::uint32_t*>(storage+package_bytes+table);
    re4dc::vp::build_lut(lut);v.lut=lut;
#endif
    ++stats.owners_open;stats.package_bytes+=v.bytes;
    const struct mallinfo kos=mallinfo();
    const auto& h=v.package.header();
    re4dc_log("native mesh: %s bytes=%u version=%u meshes=%u parts=%u meshlets=%u vertices=%u heap4=%d->%d kos_free=%d entries=%u\n",
        path,v.bytes,h.version,h.mesh_count,h.part_count,h.meshlet_count,h.vertex_count,
        stats.heap_before,stats.heap_after,kos.fordblks,v.capacity);
    return true;
}

unsigned entry_slot(const void* object,unsigned capacity){
    return unsigned(reinterpret_cast<std::uintptr_t>(object)>>4)&(capacity-1U);}
const MeshEntry* find_entry(const void* object,unsigned& owner){
    for(unsigned i=0;i<kViews;++i){
        const MeshView& v=mesh_views[i];
        if(!v.entries)continue;
        const unsigned n=v.capacity;
        for(unsigned k=0,s=entry_slot(object,n);k<n;++k,s=(s+1)&(n-1U)){
            const MeshEntry& e=v.entries[s];
            if(!e.used)break;
            if(e.object==object){owner=i;return &e;}
        }
    }
    return nullptr;
}

#if RE4DC_NO_STD_ANY
// COARSE_NO_STD_SCENERY: the room whose package bind_mesh skipped, and a census of the calls that would have
// read it while in that room, by the image kind the tick latched (coarse.cpp -> re4dc_std_scenery_tick):
// reads[kind][reader], kind 1 coarse image / 0 other; reader 0 re4dc_static_submit scroll part (mesh_submit),
// 1 re4dc_static_mesh_lit (FRONT_LEAN), 2 re4dc_static_gate (SCENERY_GATE).
struct NoStd {
    unsigned room=~0U,binds=0;   // the skipped room (cleared at room retirement) and its skipped owned binds
    int coarse=0;                // this tick's image is coarse
    unsigned reads[2][3]={};
    unsigned no_stream=0;        // other-image scroll parts without a GX stream (released: drawn as nothing)
    unsigned spans=0,last=~0U;   // runs of consecutive UI frames with other-image reads
    unsigned ticks=0;
};
NoStd no_std;
void no_std_log(const char* when);
bool no_std_skip(unsigned room){
#if RE4DC_PS2_WORLD_ROOMS >= 2
    if(no_std.room!=~0U && no_std.room!=room){no_std_log("leave");no_std=NoStd();}
    if(no_std.room!=room && !re4dc_ps2_mesh_preload(room))return false; // no PS2 world: the scenery package
#else
    if(room!=re4dc_coarse_world_room())return false;
#endif
    if(no_std.room!=room){
        no_std.room=room;
        re4dc_log("native mesh: no-std room=%x%02x: scenery package not opened (%s) heap4=%d\n",
            room>>8,room&255U,RE4DC_NO_STD_SCENERY?"COARSE_NO_STD_SCENERY":"PS2_WORLD_ROOMS=2",re4dc_static_heap_free());
    }
    ++no_std.binds;
    return true;
}
void no_std_read(unsigned reader,const Re4dcModelPart* p){
    if(no_std.room==~0U)return;
    const unsigned frame=re4dc_ui_frame();
    if(no_std.coarse){
        if(++no_std.reads[1][reader]<=4)re4dc_log("native mesh: no-std READ ON A COARSE IMAGE reader=%u frame=%u\n",reader,frame);
        return;
    }
    ++no_std.reads[0][reader];
    if(p && !p->stream_bytes)++no_std.no_stream;
    if(frame!=no_std.last && frame!=no_std.last+1U && ++no_std.spans<=16)
        re4dc_log("native mesh: no-std other-image reads from frame %u (span %u, reader %u)\n",frame,no_std.spans,reader);
    no_std.last=frame;
}
void no_std_log(const char* when){
    const auto& r=no_std.reads;
    re4dc_log("native mesh: no-std %s room=%x%02x binds=%u coarse=%u/%u/%u other=%u/%u/%u no_stream=%u spans=%u frame=%u\n",
        when,no_std.room>>8,no_std.room&255U,no_std.binds,r[1][0],r[1][1],r[1][2],r[0][0],r[0][1],r[0][2],
        no_std.no_stream,no_std.spans,re4dc_ui_frame());
}
#endif
void bind_mesh(const void* object,unsigned room,int block,unsigned bin,unsigned common){
    const unsigned index=view_index(block);
    if(index>=kViews || !(RE4DC_NATIVE_STATIC_OWNERS&(1U<<index)) ||
       (common && !(RE4DC_NATIVE_STATIC_OWNERS&(1U<<kCommonView)))){++stats.unowned_binds;return;}
#if RE4DC_NO_STD_ANY
    if(no_std_skip(room))return;   // the coarse world / PS2 world draws this room: no package, no binding
#endif
    MeshView& owner=mesh_views[index];
    if(!open(owner,index,room))return;
    MeshView& target=common?mesh_views[kCommonView]:owner;
    if(common && !open(target,kCommonView,room))return;
    const unsigned mesh=target.package.find(bin,common!=0);
    if(mesh>=target.package.header().mesh_count){
        ++stats.bind_misses;
        if(stats.bind_misses<=48)re4dc_log("native mesh: bind miss view=%u bin=%u common=%u\n",index,bin,common);
        return;
    }
    const unsigned n=owner.capacity;
    for(unsigned k=0,s=entry_slot(object,n);k<n;++k,s=(s+1)&(n-1U)){
        MeshEntry& e=owner.entries[s];
        if(e.used && e.object!=object)continue;
        e={object,std::uint16_t(mesh),std::uint8_t(common!=0),1};++stats.binds;return;
    }
    ++stats.bind_conflicts;
    re4dc_log("native mesh: view=%u object table full\n",index);
}

// 6+6-bit octahedral code -> unit normal (tools/convert_room_bins.py oct12).
void oct_normal(unsigned code,float n[3]){
    float x=float(code&63U)*(2.0f/63.0f)-1.0f,y=float((code>>6)&63U)*(2.0f/63.0f)-1.0f;
    const float z=1.0f-std::fabs(x)-std::fabs(y);
    if(z<0){
        const float ox=x;
        x=(1.0f-std::fabs(y))*(ox>=0?1.0f:-1.0f);
        y=(1.0f-std::fabs(ox))*(y>=0?1.0f:-1.0f);
    }
    const float inverse=1.0f/std::sqrt(x*x+y*y+z*z);
    n[0]=x*inverse;n[1]=y*inverse;n[2]=z*inverse;
}
std::uint16_t pack1555(const float rgb[3],unsigned alpha){
    const auto c=[](float v){return unsigned((v<0?0.0f:v>1?1.0f:v)*31.0f+0.5f);};
    return std::uint16_t((alpha>=128?0x8000U:0U)|(c(rgb[0])<<10)|(c(rgb[1])<<5)|c(rgb[2]));
}
// Prelights one part once, at its first draw, with the source evaluator and
// this draw's live light state (view-space, like the generic path): the
// stored slot becomes ARGB1555. Instances share the result and camera-
// relative lights stay as first seen - the labelled Dreamcast compromise.
void light_part(MeshView& v,const re4dc::room::MeshRecord& mesh,re4dc::room::MeshPart& part,
                const Re4dcModelPart& p){
#if RE4DC_GC_ASSET_GATE
    // A first-light rewrite outlives this caller and later deferred lighting
    // snapshots. Unknown derivation must revoke the stable owner as well as
    // this draw's selected use; a later flag-free caller cannot promote it.
    if(v.asset_proof.owner && (!re4dc_gcasset::source_use.serial || re4dc_gcasset::source_use.payload!=&v.asset_proof ||
       re4dc_gcasset::source_use.serial!=v.asset_proof.serial))
        re4dc_gcasset::payload_invalidate(v.asset_proof,&v);
#endif
    auto* vertices=reinterpret_cast<re4dc::room::CompactVertex12*>(v.storage+v.package.header().vertex_offset);
    const std::uint32_t* palette=v.package.palette();
    re4dc::render::PreparedSourceLights lights;
    if(p.lighting)lights=re4dc::render::prepare_actor_lights(*p.lighting);
    const float* m=p.modelview;
    const auto* lets=v.package.meshlets()+part.first_meshlet;
    // v3 indexed meshlets share their part's pool: light the pool [lo, hi)
    // once (adopt() proved pools disjoint) instead of each meshlet's corners.
    std::uint32_t lo=0,hi=0;
    const bool pool=v.package.shared() && v.package.part_pool(part,lo,hi);
    const unsigned ranges=pool?1U:part.meshlet_count;
    for(unsigned i=0;i<ranges;++i){
        const std::uint32_t first=pool?lo:lets[i].first_vertex,count=pool?hi-lo:lets[i].vertex_count;
        for(unsigned k=0;k<count;++k){
            auto& corner=vertices[first+k];
#if RE4DC_SCENERY_ENCODING
            const std::uint32_t argb=v.vertex_colors?v.vertex_colors[first+k]:palette[corner.color>>12];
#else
            const std::uint32_t argb=palette[corner.color>>12];
#endif
            const std::uint8_t color[4]={std::uint8_t(argb>>16),std::uint8_t(argb>>8),std::uint8_t(argb),std::uint8_t(argb>>24)};
            float rgb[3]={1.0f,1.0f,1.0f};
            if(p.lighting){
                const float x=mesh.origin[0]+float(corner.x)*mesh.step[0];
                const float y=mesh.origin[1]+float(corner.y)*mesh.step[1];
                const float z=mesh.origin[2]+float(corner.z)*mesh.step[2];
                float n[3];oct_normal(corner.color&0xfffU,n);
                const float* nm=p.lighting->normal_matrix;
#if RE4DC_GROUND_LIGHT_FIX&1
                // GROUND_LIGHT_FIX bit 1: light with the transformed normal at unit length, as GX does (Dolphin's
                // vertex shader normalises it). The source normal matrix carries the placement scale: r101's
                // ground layers are placed at scale 10, so their normals came out 0.1 long (ambient-only ground).
                float t[3]={nm[0]*n[0]+nm[1]*n[1]+nm[2]*n[2],nm[4]*n[0]+nm[5]*n[1]+nm[6]*n[2],nm[8]*n[0]+nm[9]*n[1]+nm[10]*n[2]};
                const float t2=t[0]*t[0]+t[1]*t[1]+t[2]*t[2];
                if(t2>0.0f){const float r=1.0f/std::sqrt(t2);t[0]*=r;t[1]*=r;t[2]*=r;}
                re4dc::render::evaluate_prepared_source_lighting(
                    m[0]*x+m[1]*y+m[2]*z+m[3],m[4]*x+m[5]*y+m[6]*z+m[7],m[8]*x+m[9]*y+m[10]*z+m[11],
                    t[0],t[1],t[2],*p.lighting,lights,color,rgb);
#else
                re4dc::render::evaluate_prepared_source_lighting(
                    m[0]*x+m[1]*y+m[2]*z+m[3],m[4]*x+m[5]*y+m[6]*z+m[7],m[8]*x+m[9]*y+m[10]*z+m[11],
                    nm[0]*n[0]+nm[1]*n[1]+nm[2]*n[2],nm[4]*n[0]+nm[5]*n[1]+nm[6]*n[2],nm[8]*n[0]+nm[9]*n[1]+nm[10]*n[2],
                    *p.lighting,lights,color,rgb);
#endif
            }
            corner.color=pack1555(rgb,color[3]);
        }
    }
    part.reserved=1;
    ++stats.parts_lit;
}

#if RE4DC_NATIVE_MESH && RE4DC_MESH_FASTPATH && RE4DC_MESH_VP_SCHED==2
// MESH_VP_SCHED=2 (diagnostic): the reference transform<kChecksAll> fills the drawn cache; the pipelined
// kernel transforms the same meshlet into a scratch cache, and its x,y,z,u,v,argb words and the outcodes'
// defined bits (0x3f) are compared with the reference's. Counts are logged with the frame stats.
static pvr_vertex_t vp_sched_cache[re4dc::vp::kCacheEntries] __attribute__((aligned(32)));
static std::uint8_t vp_sched_codes[re4dc::vp::kCacheEntries];
static unsigned vp_sched_stats[4]; // meshlets, vertices, mismatched vertices, mismatched words/codes
static void vp_sched_compare(const re4dc::vp::Vertex12* in,unsigned count,const pvr_vertex_t* cache,
                             const std::uint8_t* codes,const re4dc::vp::Constants& k){
    re4dc::vp::transform_sched<re4dc::vp::kChecksAll>(in,count,vp_sched_cache,vp_sched_codes,k);
    ++vp_sched_stats[0];vp_sched_stats[1]+=count;
    for(unsigned i=0;i<count;++i){
        const auto* a=reinterpret_cast<const std::uint32_t*>(cache+i);
        const auto* b=reinterpret_cast<const std::uint32_t*>(vp_sched_cache+i);
        unsigned bad=0;
        for(unsigned w=1;w<7;++w)bad+=a[w]!=b[w];
        bad+=((codes[i]^vp_sched_codes[i])&0x3fU)!=0;
        if(!bad)continue;
        if(++vp_sched_stats[2]<=8)re4dc_log("VPSCHED mismatch vertex=%u/%u ref=%08x %08x %08x %08x %08x %08x %02x new=%08x %08x %08x %08x %08x %08x %02x\n",
            i,count,unsigned(a[1]),unsigned(a[2]),unsigned(a[3]),unsigned(a[4]),unsigned(a[5]),unsigned(a[6]),unsigned(codes[i]),
            unsigned(b[1]),unsigned(b[2]),unsigned(b[3]),unsigned(b[4]),unsigned(b[5]),unsigned(b[6]),unsigned(vp_sched_codes[i]));
        vp_sched_stats[3]+=bad;
    }
}
#endif
#if RE4DC_NATIVE_MESH && RE4DC_MESH_FASTPATH && RE4DC_MESH_VP_SCHED==3
// MESH_VP_SCHED=3 (layout control, diagnostic): both kernels are linked and this .data word picks one
// (1 = reference, 2 = pipelined; never 0, so it stays in .data), so the two arms' images differ in this word
// only and their TA hashes compare frame by frame without the static-layout confounder.
#ifndef RE4DC_MESH_VP_SCHED_SELECT
#define RE4DC_MESH_VP_SCHED_SELECT 0
#endif
static volatile unsigned vp_sched_select=1U+RE4DC_MESH_VP_SCHED_SELECT;
#endif
#if RE4DC_MESH_STRIP_LEAN==2 && defined(RE4DC_TA_HASH) && RE4DC_TA_HASH
#error "MESH_STRIP_LEAN=2 runs emit_sq() into RAM for its compare, so TA_HASH would hash that dry run too: use =3"
#endif
#if RE4DC_MESH_STRIP_LEAN==2
// MESH_STRIP_LEAN=2 (diagnostic): meshlets, strips, emitted strips, mismatched runs, counter-formula mismatches,
// emitted vertices, skipped meshlets; two RAM stand-ins for the store queues (a run emits at most one vertex
// per strip byte).
constexpr unsigned kStripLeanVertices=512;
static unsigned strip_lean_stats[7];
static std::uint32_t strip_lean_buf[2][kStripLeanVertices*8] __attribute__((aligned(32)));
#endif
#if RE4DC_MESH_STRIP_LEAN==3
// MESH_STRIP_LEAN=3 (layout control, diagnostic): both walks are linked and this .data word picks one
// (1 = original, 2 = lean; never 0, so it stays in .data); MESH_STRIP_LEAN_SELECT=0|1.
#ifndef RE4DC_MESH_STRIP_LEAN_SELECT
#define RE4DC_MESH_STRIP_LEAN_SELECT 0
#endif
static volatile unsigned strip_lean_select=1U+RE4DC_MESH_STRIP_LEAN_SELECT;
#endif

#if RE4DC_PS2_INTERIOR_CULL
#if !RE4DC_PS2_WORLD_MESH || !RE4DC_PS2_WORLD_ROOMS || !RE4DC_MESH_LOD
#error "PS2_INTERIOR_CULL needs PS2_WORLD_MESH=1, PS2_WORLD_ROOMS and MESH_LOD"
#endif
// PS2_INTERIOR_CULL (game30.mk, render only): the r100 house interior cell. Built offline
// (tools/d367/ps2world/interior/build_cell.py) from the PS2 package's own opaque triangles: sub-cells (eye
// regions inside the house, inset past the near plane from every wall) and, per sub-cell, portal rectangles on the
// faces of the house hull where any view ray from the sub-cell first leaves the hull unoccluded. A box wholly outside
// the house box kPcOuter can only be seen along such a ray, so it is drawn only if it meets the frustum from the eye
// through one of the sub-cell's portals (each frustum is the intersection of five half-spaces: past the portal's
// plane and inside its four edge planes; a box outside any one of them cannot meet it).
// The sub-cells and portals are not in the image: the r100 package's open reads them from the disc file
// /cd/dc/native/r100/interior.cell (tools/d367/ps2world/interior/cell_file.py) into one heap-4 block with both states'
// frustum arrays, freed with the package. A route movie borrows the block (native_movie.cpp open, before heap_before:
// no world is drawn during a route movie) and route_movie_bridge.cpp reads it again after the movie. Without the block
// (file missing, heap 4 short, lent) nothing is culled.
namespace pc {
struct Cell { float lo[3],hi[3]; std::uint16_t first,count; };
struct Portal { std::uint32_t axis; float plane,u0,u1,v0,v1; }; // u = axis+1, v = axis+2 (mod 3)
#include "include/ps2_interior_cell.inc"
#if defined(RE4DC_PS2_R100_TR4) && RE4DC_PS2_R100_TR4
// PS2_R100_TR4=1 (game30.mk; needs PS2_R100_SMX=1): the SMX package plus --vertex-alpha tr4 (the 155 overlay faces
// move to the translucent pass; geometry and placements are the same), so the same cell with its CRCs and bytes.
constexpr unsigned kPcSidecarUse=0x14118acdU,kPcMeshUse=0xfb35ea9cU,kPcMeshBytesUse=1537920U;
#elif defined(RE4DC_PS2_R100_SMX) && RE4DC_PS2_R100_SMX
// PS2_R100_SMX=1 (game30.mk; needs PS2_PT_CUTOUT=1): the r100 package rebuilt with --color-light ps2 --tev-scale 1
// --vc-clamp 2.0 (PS2 vertex colour x SMX ColorRGB; colour bytes and 2 un-instanced BINs differ, the geometry is the
// same), so the same sub-cells and portals with that package's mesh CRC, sidecar CRC and mesh bytes.
constexpr unsigned kPcSidecarUse=0xd888094fU,kPcMeshUse=0x6122bba4U,kPcMeshBytesUse=1536992U;
#elif defined(RE4DC_PS2_PT_VARIANT_CRC) && RE4DC_PS2_PT_VARIANT_CRC
// Candidate CRC is genuine and must match both R4PW and PCL1. Offline proof
// retains the exact mesh, placements, cell boxes and portal geometry. No cull
// test or identity check is bypassed by selecting the reviewed candidate.
constexpr unsigned kPcSidecarUse=RE4DC_PS2_PT_VARIANT_CRC,kPcMeshUse=kPcMeshCrc,kPcMeshBytesUse=kPcMeshBytes;
#elif defined(RE4DC_PS2_PT_CUTOUT) && RE4DC_PS2_PT_CUTOUT
// PS2_PT_CUTOUT=1 (game30.mk): the r100 package rebuilt with ps2_room_r4im.py --cutout-max-alpha 224 (only part passes
// 2 -> 1 and those parts' texture keys differ; mesh and placements are the same), so the same cell with that sidecar CRC.
constexpr unsigned kPcSidecarUse=0x8c31fa61U,kPcMeshUse=kPcMeshCrc,kPcMeshBytesUse=kPcMeshBytes;
#else
constexpr unsigned kPcSidecarUse=kPcSidecarCrc,kPcMeshUse=kPcMeshCrc,kPcMeshBytesUse=kPcMeshBytes;
#endif
constexpr float kSlack=64.0f; // mm added to every tested box (float rounding of the box and plane maths)
constexpr unsigned kMaxFr=24; // portals per sub-cell the runtime takes
#if RE4DC_PS2_INTERIOR_CULL==3
#ifndef RE4DC_PS2_INTERIOR_CULL_SELECT
#define RE4DC_PS2_INTERIOR_CULL_SELECT 0
#endif
static volatile unsigned select_word=1U+RE4DC_PS2_INTERIOR_CULL_SELECT; // =3: 1 off, 2 on (one .data word)
#endif
struct Plane { float n[3]; };
struct Frustum { std::uint32_t axis; float plane; bool beyond_high; Plane edge[4]; float an[4][3]; }; // an: |edge normal|
struct State {
    bool ok=false;           // the open package is the one the cell was built from
    bool active=false;       // this frame's eye is in a sub-cell
    float eye[3]{};
    int cell=-1; unsigned nfr=0; Frustum* fr=nullptr; // kMaxFr frustums in the cell block (null: not loaded)
    unsigned frame=~0U,setup_frame=~0U,done_frame=~0U;float corner=0; // done_frame: the frame the cell was last set up for
    unsigned placements=0,clusters=0,meshlets=0,tests=0,active_frames=0,frames=0; PC_STATE_EXTRA // culled (=1/=3) or checked (=2)
} st;
// The disc cell (r100 only): one heap-4 block = file (header, cells, portals) + both states' frustum arrays.
struct Data {
    void* block=nullptr;const Cell* cells=nullptr;const Portal* portals=nullptr;
    bool lent=false; unsigned loads=0,fails=0,lends=0;
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::PayloadProof asset_proof;
#endif
} data;
constexpr unsigned kFrBytes=kMaxFr*unsigned(sizeof(Frustum));
// The eye from a 3x4 row-major view matrix: the inverse's translation.
inline bool eye_of(const float* v,float e[3]){
    float inv[12];if(!inverse(v,inv))return false;
    e[0]=inv[3];e[1]=inv[7];e[2]=inv[11];
    return std::isfinite(e[0]) && std::isfinite(e[1]) && std::isfinite(e[2]);
}
#if RE4DC_PS2_INTERIOR_ACTORS
State st_trans; // PS2_INTERIOR_ACTORS: the cell for the next Render's camera, set up at Trans start (ModelTrans)
inline State& trans_state(){return st_trans;}
#else
inline State& trans_state(){static State none;return none;}
#endif
// Per frame (each pass call): the sub-cell holding the eye and its portal frustums, relative to the eye. st: the
// render state (pc::st) or the Trans-time actor state.
inline void setup_state(State& st,const float* view,const float* P,float near){
    st.active=false;st.cell=-1;st.nfr=0;
#if RE4DC_PS2_INTERIOR_CULL==3
    if(select_word!=2U)return;
#endif
    if(!st.ok || !st.fr || !data.cells)return;
    // the near plane's corners must lie within the cell's near margin of the eye (the sub-cells are inset by it)
    const float tx=(1.0f+std::fabs(P[2]))/std::fabs(P[1]),ty=(1.0f+std::fabs(P[4]))/std::fabs(P[3]);
    const float corner=near*std::sqrt(1.0f+tx*tx+ty*ty);
    st.corner=corner;
    if(!(corner<=kPcNearMax))return;
    float e[3];if(!eye_of(view,e))return;
    for(unsigned i=0;i<kPcCellCount;++i){
        const Cell& c=data.cells[i];
        if(e[0]>=c.lo[0] && e[0]<=c.hi[0] && e[1]>=c.lo[1] && e[1]<=c.hi[1] && e[2]>=c.lo[2] && e[2]<=c.hi[2]){st.cell=int(i);break;}
    }
    if(st.cell<0)return; PC_PICK_HOUSE(st)
    const Cell& c=data.cells[st.cell];
    if(c.count>kMaxFr)return;
    for(unsigned k=0;k<3;++k)st.eye[k]=e[k];
    for(unsigned i=0;i<c.count;++i){
        const Portal& p=data.portals[c.first+i];
        const unsigned ax=p.axis,ua=(ax+1U)%3U,va=(ax+2U)%3U;
        Frustum& f=st.fr[st.nfr++];
        f.axis=ax;f.plane=p.plane;f.beyond_high=p.plane>e[ax];
        float q[4][3];const float uu[4]={p.u0,p.u1,p.u1,p.u0},vv[4]={p.v0,p.v0,p.v1,p.v1};
        float cen[3]={0,0,0};
        for(unsigned k=0;k<4;++k){q[k][ax]=p.plane-e[ax];q[k][ua]=uu[k]-e[ua];q[k][va]=vv[k]-e[va];
            for(unsigned a=0;a<3;++a)cen[a]+=q[k][a];}
        for(unsigned k=0;k<4;++k){
            const float* a=q[k];const float* b=q[(k+1)&3];
            float n[3]={a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};
            if(n[0]*cen[0]+n[1]*cen[1]+n[2]*cen[2]<0)for(auto& x:n)x=-x;
            const float l=std::sqrt(n[0]*n[0]+n[1]*n[1]+n[2]*n[2]);
            if(!(l>0)){st.nfr=0;return;} // degenerate: no cull this frame
            for(unsigned a=0;a<3;++a){f.edge[k].n[a]=n[a]/l;f.an[k][a]=std::fabs(n[a]/l);}
        }
    }
    st.active=true;st.setup_frame=re4dc_ui_frame();
}
inline void setup(const float* view,const float* P,float near){setup_state(st,view,P,near);}
// World box (centre / half extents): 1 hidden, 0 drawn (seen through a portal), -1 meets the house box.
inline int hidden_state(State& st,const float c[3],const float h[3]){
    ++st.tests; PC_OUTER_DECL(st)
    float lo[3],hi[3];
    for(unsigned a=0;a<3;++a){lo[a]=c[a]-h[a]-kSlack;hi[a]=c[a]+h[a]+kSlack;}
    if(hi[0]>kPcOuter[0] && lo[0]<kPcOuter[3] && hi[1]>kPcOuter[1] && lo[1]<kPcOuter[4] && hi[2]>kPcOuter[2] && lo[2]<kPcOuter[5])return -1;
    const float rc[3]={c[0]-st.eye[0],c[1]-st.eye[1],c[2]-st.eye[2]},rh[3]={h[0]+kSlack,h[1]+kSlack,h[2]+kSlack};
    for(unsigned i=0;i<st.nfr;++i){
        const Frustum& f=st.fr[i];
        if(f.beyond_high?!(hi[f.axis]>f.plane):!(lo[f.axis]<f.plane))continue;
        bool in=true;
        for(unsigned k=0;k<4 && in;++k){
            const float* n=f.edge[k].n;const float* an=f.an[k];
            in=n[0]*rc[0]+n[1]*rc[1]+n[2]*rc[2]+an[0]*rh[0]+an[1]*rh[1]+an[2]*rh[2]>=0.0f;
        }
        if(in)return 0;
    }
    return 1;
}
inline int hidden(const float c[3],const float h[3]){return hidden_state(st,c,h);}
// A box in a 3x4 matrix's input space (model or grid units) -> world centre / half extents.
inline void world_box(const float* m,const float lo[3],const float hi[3],float c[3],float h[3]){
    for(unsigned r=0;r<3;++r){
        c[r]=m[4*r+3];h[r]=0;
        for(unsigned k=0;k<3;++k){const float mc=(lo[k]+hi[k])*0.5f,mh=(hi[k]-lo[k])*0.5f;c[r]+=m[4*r+k]*mc;h[r]+=std::fabs(m[4*r+k])*mh;}
    }
}
// wq: 3x4 placement affine x grid, then its 3x3 absolute values (wq[12..20], set by abs_rows).
inline void abs_rows(float* wq){for(unsigned r=0;r<3;++r)for(unsigned k=0;k<3;++k)wq[12+3*r+k]=std::fabs(wq[4*r+k]);}
inline int grid_hidden(const float* wq,const std::uint16_t lo[3],const std::uint16_t hi[3]){
    float mc[3],mh[3],c[3],h[3];
    for(unsigned k=0;k<3;++k){mc[k]=(float(lo[k])+float(hi[k]))*0.5f;mh[k]=(float(hi[k])-float(lo[k]))*0.5f;}
    for(unsigned r=0;r<3;++r){
        const float* m=wq+4*r;const float* a=wq+12+3*r;
        c[r]=m[3]+m[0]*mc[0]+m[1]*mc[1]+m[2]*mc[2];h[r]=a[0]*mh[0]+a[1]*mh[1]+a[2]*mh[2];
    }
    return hidden(c,h);
}
State& trans_state();
// Frees the cell block (both states inactive: nothing is culled until it is read again).
inline unsigned unload(){
#if RE4DC_GC_ASSET_GATE
    gcasset_static_invalidate_all();
    if(data.asset_proof.owner)re4dc_gcasset::payload_invalidate(data.asset_proof,&data);
#endif
    if(!data.block)return 0;
    re4dc_static_free(data.block);
    data.block=nullptr;data.cells=nullptr;data.portals=nullptr;
    st.fr=nullptr;st.active=false;st.nfr=0;
    State& t=trans_state();t.fr=nullptr;t.active=false;t.nfr=0;
    return kPcFileBytes+2U*kFrBytes;
}
// Reads /cd/dc/native/r100/interior.cell into a heap-4 block (the r100 package open, and after a route movie).
inline bool load(){ PC_LOAD_HOOK
    if(data.block)return true;
    if(!st.ok)return false;
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::payload_retire(data.asset_proof); // safe cold reload
#endif
    const int before=re4dc_static_heap_free();
    const char* why=nullptr;
    const file_t file=fs_open("/cd/dc/native/r100/interior.cell",O_RDONLY);
    unsigned char* b=nullptr;
    if(file==FILEHND_INVALID)why="missing";
    else{
        if(unsigned(fs_total(file))!=kPcFileBytes)why="size";
        else if(!(b=static_cast<unsigned char*>(re4dc_static_alloc(kPcFileBytes+2U*kFrBytes))))why="heap4";
        else if(fs_read(file,b,kPcFileBytes)!=ssize_t(kPcFileBytes))why="read";
        fs_close(file);
    }
    if(!why){
        std::uint32_t w[8];std::memcpy(w,b,sizeof(w));
        if(std::memcmp(b,"PCL1",4) || w[1]!=kPcRoom || w[2]!=kPcMeshUse || w[3]!=kPcSidecarUse || w[4]!=kPcMeshBytesUse ||
           w[5]!=kPcCellCount || w[6]!=kPcPortalCount)why="header";
    }
    const Cell* cells=b?reinterpret_cast<const Cell*>(b+32):nullptr;
    for(unsigned i=0;!why && i<kPcCellCount;++i)
        if(cells[i].count>kMaxFr || unsigned(cells[i].first)+cells[i].count>kPcPortalCount)why="cells";
    if(why){
        if(b)re4dc_static_free(b);
        ++data.fails;
        re4dc_log("PCCULL cell file %s: not culling (heap4=%d)\n",why,before);
        return false;
    }
#if RE4DC_GC_ASSET_GATE
    gcasset_static_invalidate_all();
    const auto gcasset_digest=re4dc_gcasset::fingerprint(b,kPcFileBytes);
    re4dc_gcasset::payload_capture_receipt(data.asset_proof,&data,gcasset_digest,kPcFileBytes);
#endif
    data.block=b;data.cells=cells;data.portals=reinterpret_cast<const Portal*>(b+32+kPcCellCount*sizeof(Cell));
    st.fr=reinterpret_cast<Frustum*>(b+kPcFileBytes);trans_state().fr=reinterpret_cast<Frustum*>(b+kPcFileBytes+kFrBytes);
    ++data.loads;
    re4dc_log("PCCULL cell file loaded %u B (+%u B states) heap4=%d->%d loads=%u lends=%u\n",kPcFileBytes,2U*kFrBytes,before,
              re4dc_static_heap_free(),data.loads,data.lends);
    return true;
}
} // namespace pc
#if RE4DC_PS2_INTERIOR_ACTORS
namespace pcact {
float view[12],P[7],near=0;bool have=false;unsigned reused=0;
unsigned trans_frames=0,active=0,tests=0,hid=0,view_checked=0,view_mis=0;
#if RE4DC_PS2_INTERIOR_CULL==2
struct Box{float lo[3],hi[3];};
constexpr unsigned kBoxes=32;
Box box[kBoxes];unsigned nbox=0,boxes=0,drawn=0,unchecked=0,overflow=0;
unsigned key[6];bool have_key=false;
#endif
#if RE4DC_PS2_INTERIOR_OWNER
unsigned owner_tests=0,owner_hid=0; // PS2_INTERIOR_ACTORS=2: owner-path Ganados tested / hidden (also counted in hid)
#endif
}
#endif
#endif
#if RE4DC_GC_ASSET_GATE
void gcasset_static_policy(re4dc_gcasset::StaticManifest& source,unsigned room){
    using namespace re4dc_gcasset;
#if RE4DC_QUALITY_ASSETS
    if(!re4dc_quality_std_assets())static_manifest_note(source,STD_INDEX,Disabled);
    else if(std_room.active && std_room.room==room)static_manifest_receipt(source,STD_INDEX,std_room.asset_proof,&std_room,1,StaticConsumedSpan);
    else if(std_room.room==room && std_room.gca_unused)static_manifest_note(source,STD_INDEX,std_room.gca_unused==1?Absent:Rejected);
    else static_manifest_note(source,STD_INDEX,Unproven);
#else
    static_manifest_note(source,STD_INDEX,Disabled);
#endif
#if RE4DC_PS2_INTERIOR_CULL
    if(room!=pc::kPcRoom)static_manifest_note(source,PCL1_CELL,NotApplicable);
    else if(pc::data.block)static_manifest_receipt(source,PCL1_CELL,pc::data.asset_proof,&pc::data,1);
    // A null block also follows rejected/short/failed reads or an unqualified
    // package. No durable original absence receipt exists for those cases.
    else static_manifest_note(source,PCL1_CELL,Unproven);
#else
    (void)room;static_manifest_note(source,PCL1_CELL,Disabled);
#endif
}
#endif
#if RE4DC_PS2_WORLD_LEAN
// PS2_WORLD_LEAN (game30.mk, render only, default 0; lane objs 2026-10-14, r101 world submit). Bits:
//  1 world-space placement pretest: per pass the six cull planes (the four screen edges group_visible uses, near and
//    the pass's cull far) go to world space once; a placement whose mesh box (world AABB of the affine'd box) lies
//    wholly outside one of them by more than a unit is culled without its view concat and view-space box test.
//  2 fully-inside propagation: a placement box (grown by one grid step, the cluster rounding) wholly inside every plane
//    skips its clusters' and meshlets' box tests; a cluster wholly inside skips its meshlets' tests (meshlet boxes nest
//    in their cluster box: lane objs nest.py, r101 0 of 1726 outside). Same rejections as group_visible otherwise.
//  4 the meshlet cache's constant words (MESH_PRIME_LAZY) are primed once per pass, not once per part: in the
//    direct path the cache is the model packet buffer's fixed tail, and only the transform (which never writes those
//    words) and the walks touch it inside a pass.
//  8 (diagnostic) checks 2 and 4: every skipped box test is run anyway and every reused prime word is read back;
//    disagreements counted in the PS2LEAN line (check_bad / prime_bad must stay 0).
#pragma GCC push_options
#pragma GCC optimize("O2")
namespace lean {
constexpr unsigned kMode=RE4DC_PS2_WORLD_LEAN;
struct Stats { unsigned pre_culled,pl_inside,cl_inside,skipped,prime_reuse,check_bad,prime_bad,dyn_fast,class_diff;
               unsigned sg_tests,sg_culled,sg_meshlets,sg_vskip; } st;
const pvr_vertex_t* prime_at=nullptr; unsigned primed=0;
// native_static.cpp is built at -O1 (no unrolling): these are written out by hand (the hw model priced the loop forms
// at ~2x group_visible).
// The four screen-edge planes of group_visible (bias 0) for this pass: plane k = a[k] * (x for k < 2, y for k >= 2)
// + c[k] * z, with |a|, |c| for the box support.
struct Side { float a[4],c[4],aa[4],ac[4]; } side;
inline void side_setup(const float* p,const float* vp){
    const float ox=2*vp[0]/vp[2],oy=2*vp[1]/vp[3];
    side.a[0]=p[1];side.c[0]=p[2]-1-ox;side.a[1]=-p[1];side.c[1]=-p[2]-1+ox;
    side.a[2]=-p[3];side.c[2]=-p[4]-1-oy;side.a[3]=p[3];side.c[3]=p[4]-1+oy;
    for(unsigned k=0;k<4;++k){side.aa[k]=std::fabs(side.a[k]);side.ac[k]=std::fabs(side.c[k]);}
}
inline void abs9(const float* m,float* am){
    am[0]=std::fabs(m[0]);am[1]=std::fabs(m[1]);am[2]=std::fabs(m[2]);
    am[3]=std::fabs(m[4]);am[4]=std::fabs(m[5]);am[5]=std::fabs(m[6]);
    am[6]=std::fabs(m[8]);am[7]=std::fabs(m[9]);am[8]=std::fabs(m[10]);
}
// 0 outside (group_visible's rejection: same planes, view-space box support, -0.0001 slack), 1 straddles, 2 inside
// every plane with a unit of margin (the box grown by grow[], model units per axis, for that verdict only).
// m: the 3x4 matrix; am: its 3x3 absolute values (abs9).
inline unsigned box_class(const float lo[3],const float hi[3],const float* m,const float* am,
                          float near_distance,float far_distance,const float* grow){
    const float cx=(lo[0]+hi[0])*0.5f,cy=(lo[1]+hi[1])*0.5f,cz=(lo[2]+hi[2])*0.5f;
    const float ex=(hi[0]-lo[0])*0.5f,ey=(hi[1]-lo[1])*0.5f,ez=(hi[2]-lo[2])*0.5f;
    const float vz=m[8]*cx+m[9]*cy+m[10]*cz+m[11],rz=am[6]*ex+am[7]*ey+am[8]*ez;
    if(-vz+rz<near_distance || -vz-rz>far_distance)return 0;
    const float vx=m[0]*cx+m[1]*cy+m[2]*cz+m[3],rx=am[0]*ex+am[1]*ey+am[2]*ez;
    const Side& S=side;
    const float s0=S.a[0]*vx+S.c[0]*vz,t0=S.aa[0]*rx+S.ac[0]*rz;if(s0+t0<-0.0001f)return 0;
    const float s1=S.a[1]*vx+S.c[1]*vz,t1=S.aa[1]*rx+S.ac[1]*rz;if(s1+t1<-0.0001f)return 0;
    const float vy=m[4]*cx+m[5]*cy+m[6]*cz+m[7],ry=am[3]*ex+am[4]*ey+am[5]*ez;
    const float s2=S.a[2]*vy+S.c[2]*vz,t2=S.aa[2]*ry+S.ac[2]*rz;if(s2+t2<-0.0001f)return 0;
    const float s3=S.a[3]*vy+S.c[3]*vz,t3=S.aa[3]*ry+S.ac[3]*rz;if(s3+t3<-0.0001f)return 0;
    float gx=rx,gy=ry,gz=rz;
    if(grow){
        gx+=am[0]*grow[0]+am[1]*grow[1]+am[2]*grow[2];gy+=am[3]*grow[0]+am[4]*grow[1]+am[5]*grow[2];
        gz+=am[6]*grow[0]+am[7]*grow[1]+am[8]*grow[2];
    }
    if(!(-vz-gz>=near_distance+1.0f && -vz+gz<=far_distance-1.0f))return 1;
    if(!(s0-(S.aa[0]*gx+S.ac[0]*gz)>1.0f) || !(s1-(S.aa[1]*gx+S.ac[1]*gz)>1.0f) ||
       !(s2-(S.aa[2]*gy+S.ac[2]*gz)>1.0f) || !(s3-(S.aa[3]*gy+S.ac[3]*gz)>1.0f))return 1;
    return 2;
}
// The six planes in world space: n.w + d >= 0 inside; an = |n|.
struct World { float n[6][3],an[6][3],d[6]; };
inline void world_planes(const float* V,const float* P,const float* vp,float near_distance,float far_distance,World& w){
    const float ox=2*vp[0]/vp[2],oy=2*vp[1]/vp[3];
    const float pl[6][4]={{P[1],0,P[2]-1-ox,0},{-P[1],0,-P[2]-1+ox,0},{0,-P[3],-P[4]-1-oy,0},{0,P[3],P[4]-1+oy,0},
                          {0,0,-1,-near_distance},{0,0,1,far_distance}};
    for(unsigned k=0;k<6;++k){
        const float a=pl[k][0],b=pl[k][1],c=pl[k][2];
        for(unsigned i=0;i<3;++i){w.n[k][i]=a*V[i]+b*V[4+i]+c*V[8+i];w.an[k][i]=std::fabs(w.n[k][i]);}
        w.d[k]=a*V[3]+b*V[7]+c*V[11]+pl[k][3];
    }
}
// true: the box lo..hi under the 3x4 affine A is wholly outside one plane (by more than a unit).
inline bool world_out(const World& w,const float* A,const float lo[3],const float hi[3]){
    const float mx=(lo[0]+hi[0])*0.5f,my=(lo[1]+hi[1])*0.5f,mz=(lo[2]+hi[2])*0.5f;
    const float hx=(hi[0]-lo[0])*0.5f,hy=(hi[1]-lo[1])*0.5f,hz=(hi[2]-lo[2])*0.5f;
    const float c0=A[0]*mx+A[1]*my+A[2]*mz+A[3],c1=A[4]*mx+A[5]*my+A[6]*mz+A[7],c2=A[8]*mx+A[9]*my+A[10]*mz+A[11];
    const float h0=std::fabs(A[0])*hx+std::fabs(A[1])*hy+std::fabs(A[2])*hz;
    const float h1=std::fabs(A[4])*hx+std::fabs(A[5])*hy+std::fabs(A[6])*hz;
    const float h2=std::fabs(A[8])*hx+std::fabs(A[9])*hy+std::fabs(A[10])*hz;
#define RE4DC_LEAN_PLANE(k) if(w.n[k][0]*c0+w.n[k][1]*c1+w.n[k][2]*c2+w.d[k]+w.an[k][0]*h0+w.an[k][1]*h1+w.an[k][2]*h2<-1.0f)return true;
    RE4DC_LEAN_PLANE(0) RE4DC_LEAN_PLANE(1) RE4DC_LEAN_PLANE(4) RE4DC_LEAN_PLANE(5) RE4DC_LEAN_PLANE(2) RE4DC_LEAN_PLANE(3)
#undef RE4DC_LEAN_PLANE
    return false;
}
// concat() written out: the same expression per element (incl. the +0.0f of the loop form), so the same result.
inline void concat_u(const float* a,const float* b,float* o){
#define RE4DC_LEAN_ROW(r) \
    o[4*r+0]=a[4*r]*b[0]+a[4*r+1]*b[4]+a[4*r+2]*b[8]+0.0f; \
    o[4*r+1]=a[4*r]*b[1]+a[4*r+1]*b[5]+a[4*r+2]*b[9]+0.0f; \
    o[4*r+2]=a[4*r]*b[2]+a[4*r+1]*b[6]+a[4*r+2]*b[10]+0.0f; \
    o[4*r+3]=a[4*r]*b[3]+a[4*r+1]*b[7]+a[4*r+2]*b[11]+a[4*r+3];
    RE4DC_LEAN_ROW(0) RE4DC_LEAN_ROW(1) RE4DC_LEAN_ROW(2)
#undef RE4DC_LEAN_ROW
}
#if RE4DC_PS2_STRIP_GROUPS
// PS2_STRIP_GROUPS: a meshlet's box against the cull planes. -1 outside (group_visible's rejection, same planes and
// slack), else a mask of the planes the box crosses: bits 0..3 the screen edges (side order), bit 4 near.
inline int box_mask(const float lo[3],const float hi[3],const float* m,const float* am,float near_distance,float far_distance){
    const float cx=(lo[0]+hi[0])*0.5f,cy=(lo[1]+hi[1])*0.5f,cz=(lo[2]+hi[2])*0.5f;
    const float ex=(hi[0]-lo[0])*0.5f,ey=(hi[1]-lo[1])*0.5f,ez=(hi[2]-lo[2])*0.5f;
    const float vz=m[8]*cx+m[9]*cy+m[10]*cz+m[11],rz=am[6]*ex+am[7]*ey+am[8]*ez;
    if(-vz+rz<near_distance || -vz-rz>far_distance)return -1;
    const float vx=m[0]*cx+m[1]*cy+m[2]*cz+m[3],rx=am[0]*ex+am[1]*ey+am[2]*ez;
    const float vy=m[4]*cx+m[5]*cy+m[6]*cz+m[7],ry=am[3]*ex+am[4]*ey+am[5]*ez;
    const Side& S=side;int mask=0;
    for(unsigned k=0;k<4;++k){
        const float v=k<2?vx:vy,r=k<2?rx:ry;
        const float sv=S.a[k]*v+S.c[k]*vz,t=S.aa[k]*r+S.ac[k]*rz;
        if(sv+t<-0.0001f)return -1;
        if(!(sv-t>0.0f))mask|=1<<k;
    }
    if(!(-vz-rz>near_distance))mask|=16;
    return mask;
}
// Per part (mvq): the five planes a group can be culled by (4 screen edges in side order, near) as grid-space linear
// forms n.g + d >= 0 inside, split into P = max(n, 0) and Q = min(n, 0), so a box's largest value is P.hi + Q.lo + d.
// 8 floats per plane: P[3] Q[3] d pad (read in order through one pointer: SH-4 fmov has no displacement form).
inline void sg_coef(const float* m,float near_distance,float* out){
    const Side& S=side;
    for(unsigned k=0;k<5;++k,out+=8){
        float n[3],d;
        if(k<4){
            const float* r=m+(k<2?0:4);
            for(unsigned a=0;a<3;++a)n[a]=S.a[k]*r[a]+S.c[k]*m[8+a];
            d=S.a[k]*r[3]+S.c[k]*m[11];
        }else{
            for(unsigned a=0;a<3;++a)n[a]=-m[8+a];
            d=-m[11]-near_distance;
        }
        for(unsigned a=0;a<3;++a){out[a]=n[a]>0.0f?n[a]:0.0f;out[3+a]=n[a]<0.0f?n[a]:0.0f;}
        out[6]=d;out[7]=0.0f;
    }
}
// One meshlet's group records g (n x 16 bytes: grid lo[3] hi[3], strip end, first | last corner << 8) against only the
// planes the meshlet crosses (mask bits 0..4 from box_mask; coef from sg_coef): a group whose box is wholly outside one
// of them by more than a unit is culled (every strip in it would have been culled after the transform). Returns the
// visible groups' strip ranges r0..r1, their corner range lo..hi and how many are left; counts culled.
__attribute__((noinline)) unsigned sg_select(const std::uint16_t* g,unsigned n,const float* coef,unsigned mask,
        std::uint16_t* r0,std::uint16_t* r1,unsigned& lo,unsigned& hi,unsigned& culled){
    unsigned prev=0,nr=0,vlo=255,vhi=0,cut=0;
    // the crossed planes, once per meshlet (not a 5-step skip loop per group)
    const float* pl[5];unsigned np=0;
    for(unsigned k=0;k<5;++k)if((mask>>k)&1U)pl[np++]=coef+8*k;
    for(unsigned i=0;i<n;++i,g+=8){
        const unsigned gend=g[6];
        if(gend==prev)continue;
        const float l0=float(g[0]),l1=float(g[1]),l2=float(g[2]),h0=float(g[3]),h1=float(g[4]),h2=float(g[5]);
        bool out=false;
        for(unsigned k=0;k<np;++k){
            const float* c=pl[k];
            const float P0=*c++,P1=*c++,P2=*c++,Q0=*c++,Q1=*c++,Q2=*c++,D=*c;
            if(P0*h0+P1*h1+P2*h2+Q0*l0+Q1*l1+Q2*l2+D<-1.0f){out=true;break;}
        }
        if(out){++cut;prev=gend;continue;}
        r0[nr]=std::uint16_t(prev);r1[nr]=std::uint16_t(gend);++nr;
        const unsigned v0=g[7]&255U,v1=g[7]>>8;
        if(v0<vlo)vlo=v0;
        if(v1>vhi)vhi=v1;
        prev=gend;
    }
    lo=vlo;hi=vhi;culled=cut;
    return nr;
}
#if RE4DC_SG_SELECT_LEAN
// SG_SELECT_LEAN (t2exact.mk; exact, render only): sg_select / sg_coef / box_mask with the same results bit for bit.
// sg_select's plane value is the chain fl(P1*h1), fmac P0*h0, P2*h2, Q0*l0, Q1*l1, Q2*l2, fadd D, compared with -1 (the
// order GCC gives the knob-off expression P0*h0+P1*h1+P2*h2+Q0*l0+Q1*l1+Q2*l2+D). P = max(n, 0), Q = min(n, 0): per axis
// at most one of them is non-zero, and a zero term leaves the running value as it was (fma(+0, x, t) == t; only the
// sign of a zero can change, which neither comparison sees). A zero term may also stand first: fl(+0 * x) = +0 and the
// next fmac then gives fl(c * x), the same as the knob-off fl(P1 * h1) or fmac into +0. So each axis contributes one
// term: n > 0 its P term (corner h), else its Q term (corner l; n == 0 gives a zero term), in the order of the P terms
// (axes 1, 0, 2) then the Q terms (axes 0, 1, 2): three terms whose order follows from the 3-bit sign pattern.
// SgPlane: the three coefficients, D, and the byte offset of each term's corner in the group record (u16 l0 l1 l2 h0 h1 h2).
struct SgPlane { float c0,c1,c2,d; std::int32_t o0,o1,o2,pad; };
inline void sg_coef_lean(const float* m,float near_distance,SgPlane* out){
    // pattern bit a = (n[a] > 0): the axes in term order, and the corners' byte offsets in the record
    // per pattern, packed in one 16-byte table: 3 x (axis a in 2 bits, corner u16 index 0..5 in 3 bits), term k at
    // bits 5k..5k+4: axes {0,1,2} {0,1,2} {1,0,2} {1,0,2} {2,0,1} {0,2,1} {1,2,0} {1,0,2}, corner = a (l) or 3 + a (h)
#define RE4DC_SG_T(a0,c0,a1,c1,a2,c2) std::uint16_t((a0)|(c0)<<2|(a1)<<5|(c1)<<7|(a2)<<10|(c2)<<12)
    static const std::uint16_t kTerms[8]={RE4DC_SG_T(0,0,1,1,2,2),RE4DC_SG_T(0,3,1,1,2,2),RE4DC_SG_T(1,4,0,0,2,2),
        RE4DC_SG_T(1,4,0,3,2,2),RE4DC_SG_T(2,5,0,0,1,1),RE4DC_SG_T(0,3,2,5,1,1),RE4DC_SG_T(1,4,2,5,0,0),RE4DC_SG_T(1,4,0,3,2,5)};
#undef RE4DC_SG_T
    const Side& S=side;
    for(unsigned k=0;k<5;++k,++out){
        float n[3],d;
        if(k<4){
            const float* r=m+(k<2?0:4);
            for(unsigned a=0;a<3;++a)n[a]=S.a[k]*r[a]+S.c[k]*m[8+a];
            d=S.a[k]*r[3]+S.c[k]*m[11];
        }else{
            for(unsigned a=0;a<3;++a)n[a]=-m[8+a];
            d=-m[11]-near_distance;
        }
        const unsigned pat=(n[0]>0.0f?1U:0U)|(n[1]>0.0f?2U:0U)|(n[2]>0.0f?4U:0U);
        const unsigned w=kTerms[pat];
        // max(n, 0) or min(n, 0), as sg_coef (a NaN or a signed zero gives +0)
#define RE4DC_SG_TERM(v) ((v)>0.0f?(v):((v)<0.0f?(v):0.0f))
        out->c0=RE4DC_SG_TERM(n[w&3U]);out->c1=RE4DC_SG_TERM(n[(w>>5)&3U]);out->c2=RE4DC_SG_TERM(n[(w>>10)&3U]);out->d=d;
#undef RE4DC_SG_TERM
        out->o0=std::int32_t(2U*((w>>2)&7U));out->o1=std::int32_t(2U*((w>>7)&7U));out->o2=std::int32_t(2U*((w>>12)&7U));
        out->pad=0;
    }
}
// sg_select with SgPlane terms. Also: the crossed planes picked without a shift loop, the box converted once per group,
// the plane records read in order.
__attribute__((noinline)) unsigned sg_select_lean(const std::uint16_t* g,unsigned n,const SgPlane* planes,unsigned mask,
        std::uint16_t* r0,std::uint16_t* r1,unsigned& lo,unsigned& hi,unsigned& culled){
    const SgPlane* pl[5];unsigned np=0;
    if(mask&1U)pl[np++]=planes;
    if(mask&2U)pl[np++]=planes+1;
    if(mask&4U)pl[np++]=planes+2;
    if(mask&8U)pl[np++]=planes+3;
    if(mask&16U)pl[np++]=planes+4;
    unsigned prev=0,nr=0,vlo=255,vhi=0,cut=0;
    for(const std::uint16_t* const end=g+8*n;g!=end;g+=8){
        const unsigned gend=g[6];
        if(gend==prev)continue;
        const char* const gb=reinterpret_cast<const char*>(g);
        bool out=false;
        for(unsigned k=0;k<np;++k){
            // fl(c0 * x0), then fmac c1 * x1, fmac c2 * x2 (explicit: GCC's contraction would fuse the first product
            // instead), then fadd d: the knob-off chain's operations on its non-zero terms. x: the corner's u16, read
            // from the record where the term needs it.
            const SgPlane* p=pl[k];
            const float x0=float(*reinterpret_cast<const std::uint16_t*>(gb+p->o0));
            const float x1=float(*reinterpret_cast<const std::uint16_t*>(gb+p->o1));
            const float x2=float(*reinterpret_cast<const std::uint16_t*>(gb+p->o2));
            float t=p->c0*x0;
            t=__builtin_fmaf(p->c1,x1,t);
            t=__builtin_fmaf(p->c2,x2,t);
            t=t+p->d;
            if(t<-1.0f){out=true;break;}
        }
        if(out){++cut;prev=gend;continue;}
        r0[nr]=std::uint16_t(prev);r1[nr]=std::uint16_t(gend);++nr;
        const unsigned w=g[7],v0=w&255U,v1=w>>8;
        if(v0<vlo)vlo=v0;
        if(v1>vhi)vhi=v1;
        prev=gend;
    }
    lo=vlo;hi=vhi;culled=cut;
    return nr;
}
// box_mask with the same expressions, the plane loop written out (no per-plane select of x / y).
inline int box_mask_lean(const float lo[3],const float hi[3],const float* m,const float* am,float near_distance,float far_distance){
    const float cx=(lo[0]+hi[0])*0.5f,cy=(lo[1]+hi[1])*0.5f,cz=(lo[2]+hi[2])*0.5f;
    const float ex=(hi[0]-lo[0])*0.5f,ey=(hi[1]-lo[1])*0.5f,ez=(hi[2]-lo[2])*0.5f;
    const float vz=m[8]*cx+m[9]*cy+m[10]*cz+m[11],rz=am[6]*ex+am[7]*ey+am[8]*ez;
    if(-vz+rz<near_distance || -vz-rz>far_distance)return -1;
    const float vx=m[0]*cx+m[1]*cy+m[2]*cz+m[3],rx=am[0]*ex+am[1]*ey+am[2]*ez;
    const float vy=m[4]*cx+m[5]*cy+m[6]*cz+m[7],ry=am[3]*ex+am[4]*ey+am[5]*ez;
    const Side& S=side;int mask=0;
#define RE4DC_SG_BM_PLANE(k,v,r) { \
        const float sv=S.a[k]*v+S.c[k]*vz,t=S.aa[k]*r+S.ac[k]*rz; \
        if(sv+t<-0.0001f)return -1; \
        if(!(sv-t>0.0f))mask|=1<<k; }
    RE4DC_SG_BM_PLANE(0,vx,rx) RE4DC_SG_BM_PLANE(1,vx,rx) RE4DC_SG_BM_PLANE(2,vy,ry) RE4DC_SG_BM_PLANE(3,vy,ry)
#undef RE4DC_SG_BM_PLANE
    if(!(-vz-rz>near_distance))mask|=16;
    return mask;
}
struct LeanSgStats { unsigned calls,bm,sel_bad,coef_bad,bm_bad; } lst;
#endif
#if defined(RE4DC_SCENERY_SELECT_LEAN2) && RE4DC_SCENERY_SELECT_LEAN2
#include "include/scenery_select_lean2.inc"
#endif
#endif
}
#pragma GCC pop_options
#if RE4DC_SG_SELECT_LEAN
// Runtime switch for an A/B on one image (warp line "sglean 0|1"; benchmark POC disc): 1 the lean functions, 0 the
// original ones.
extern "C" { volatile unsigned re4dc_sg_lean_on=1; void re4dc_sg_select_lean_set(unsigned on){re4dc_sg_lean_on=on?1U:0U;} }
#endif
#endif
#if RE4DC_PS2_PVS
namespace pvs { unsigned cl_tested=0,cl_skipped=0; } // PS2_PVS cluster counters (the rest of namespace pvs is at ps2_open)
#endif
#if RE4DC_SCENERY_DEDUP
// SCENERY_DEDUP (scenery19.mk; exact, render only): at room load (ps2_open, and again after a movie reload) every PS2
// world meshlet's corners are reordered in place: the corners whose grid position is new first (in their order), the
// repeats after them. Strip indices, v3 pool offsets and each strip group's corner range (now the first copies the
// group reads) follow, so the triangles, their order and the clipper's inputs are unchanged. A draw transforms only the
// first copies and builds each repeat from its first copy's x, y, 1/w and outcode plus its own u, v (the transform's
// fmac) and colour (the same LUT words): every vertex word is the knob-off word. One word per meshlet (repeat offset |
// repeat count << 24) and one byte per repeat (its first copy), in heap 4 beside the strip groups.
namespace dedup {
#if RE4DC_SCENERY_DEDUP!=3
const void* pkg=nullptr;          // the package the tables belong to (ps2w.package once applied)
std::uint32_t* lets=nullptr;      // per meshlet: offset into src | repeats << 24
std::uint8_t* src=nullptr;        // per repeat: its first copy's corner
void* block=nullptr; unsigned nlets=0,nsrc=0,bytes=0;
#endif // mode3 derives every source from its current package, without retained table state
// cache[u..n) from their first copies (cache[src[..]]), in[u..n) u, v, colour; oc likewise.
__attribute__((noinline)) void fill(const re4dc::vp::Vertex12* in,pvr_vertex_t* cache,std::uint8_t* oc,unsigned u,
                                    unsigned n,const std::uint8_t* s,const re4dc::vp::Constants& k,unsigned clo=0,unsigned chi=255){
    const float au=k.f.au,bu=k.f.bu,av=k.f.av,bv=k.f.bv;
    const std::uint32_t* lut=k.lut;const std::uint32_t andm=k.and_mask,orb=k.or_bits;
    for(unsigned j=u;j<n;++j){
#if RE4DC_SCENERY_DEDUP==3
        const unsigned q=in[j].x; // validated SDO3 refs are this repeat vertex's x word
        (void)s;
        if(q<clo || q>chi)continue; // an unselected repeat never reads an unprimed first
#else
        const unsigned q=*s++;
#endif
        const pvr_vertex_t& a=cache[q];pvr_vertex_t& d=cache[j];
        d.x=a.x;d.y=a.y;d.z=a.z;oc[j]=oc[q];
        const auto& v=in[j];
        float fu=float(v.u),fv=float(v.v),ru=bu,rv=bv;
        // the transform's u = fmac(float(u), au, bu), v = fmac(float(v), av, bv)
        __asm__("fmac fr0,%1,%0" : "+f"(ru) : "f"(au),"w"(fu));
        __asm__("fmac fr0,%1,%0" : "+f"(rv) : "f"(av),"w"(fv));
        d.u=ru;d.v=rv;
        const unsigned c=v.color;
        d.argb=((lut[c>>8]|lut[256U+(c&255U)])&andm)|orb;
#if defined(RE4DC_SCENERY_DEDUP_CHECK) && RE4DC_SCENERY_DEDUP_CHECK
        // check build: the knob-off kernel on this corner, word for word (outcode screen/depth bits only)
        static unsigned checked=0,bad=0;
        alignas(32) pvr_vertex_t t[2];std::uint8_t to[8];
#if RE4DC_SCENERY_DEDUP==3
        auto ref=v;ref.x=in[q].x;ref.y=in[q].y;ref.z=in[q].z;
        re4dc::vp::transform_sched<re4dc::vp::kChecksAll>(&ref,1,t,to,k);
#else
        re4dc::vp::transform_sched<re4dc::vp::kChecksAll>(&v,1,t,to,k);
#endif
        std::uint32_t wa[6],wb[6];
        std::memcpy(wa,&t[0].x,24);std::memcpy(wb,&d.x,24);
        ++checked;
        if(q<clo || q>chi){--checked;continue;}   // its first copy was not transformed: the repeat is not drawn
        if(std::memcmp(wa,wb,24) || ((to[0]^oc[j])&0x3fU)){
            if(++bad<=16)re4dc_log("SCNDEDUP CHECK bad j=%u q=%u n=%u ref %08x %08x %08x %08x %08x %08x oc %02x got %08x %08x %08x %08x %08x %08x oc %02x\n",
                j,q,n,wa[0],wa[1],wa[2],wa[3],wa[4],wa[5],to[0],wb[0],wb[1],wb[2],wb[3],wb[4],wb[5],oc[j]);
        }
        if(!(checked&0x3ffffU) || bad==1)re4dc_log("SCNDEDUP CHECK checked=%u bad=%u\n",checked,bad);
#endif
    }
}
}
#endif
#if RE4DC_SCENERY_CONE
// SCENERY_CONE (scenery21.mk; render only): the room file's SCCN section (tools/d367/scenery21/scn21_build.py), one
// back-face cone per strip group (8 B: s8 axis[3], u8 k, f32 R; k 0 = none). chunk_select drops a group whose every
// triangle faces the culled side for this eye (in grid coordinates): the PVR would cull each of them.
namespace cone {
const std::uint8_t* rec=nullptr;  // meshlet x groups x 8 B
const float* tab2=nullptr;        // 64 squared slopes (T_k^2)
const void* pkg=nullptr;          // the package the section matches
unsigned tests=0,rejects=0,vskip=0,picks_dropped=0,logged=0;
}
#endif
#if RE4DC_SCENERY_PIECE_STATE
// SCENERY_PIECE_STATE (scenery21.mk; exact): the room file's SCPS section, one header-slot word per PS2 world part
// (native_ui.cpp PS2_WORLD_HDR_CACHE slot index + 1, 0 = none yet), written at the part's first bind in the room and
// checked at every bind (native_ui.cpp re4dc_ps2_piece_slot).
namespace piece { std::uint32_t* table=nullptr; const void* pkg=nullptr; }
#endif
#if RE4DC_SCENERY_CHUNK
// SCENERY_CHUNK (scenery19.mk): the per-part / per-meshlet walk at -O2 (this unit is -Os). The same expressions, so the
// same decisions and vertex words (FP contraction is the same at -Os and -O2).
#pragma GCC push_options
#pragma GCC optimize("O2")
#endif
#if RE4DC_WORLD_SCRATCH
#if !RE4DC_NATIVE_MESH || !RE4DC_MESH_FASTPATH || !RE4DC_MESH_DIRECT || !RE4DC_PS2_WORLD_MESH
#error WORLD_SCRATCH requires the original indexed direct mesh fast path
#endif
static_assert(sizeof(pvr_vertex_t)*re4dc::vp::kCacheEntries==re4dc::world_scratch::kVertexBytes);
static_assert(sizeof(pvr_vertex_t)*re4dc::vp::kCacheSlots==re4dc::world_scratch::kReservedBytes);
extern "C" void re4dc_world_scratch_prime_reset(){
#if RE4DC_PS2_WORLD_LEAN
    lean::prime_at=nullptr;lean::primed=0;
#endif
}
#endif
#if defined(RE4DC_SCENERY_STREAM_CHECK) && RE4DC_SCENERY_STREAM_CHECK
unsigned stream_ls[2]; // SCENERY_STREAM check build: load_screen memo misses compared, mismatches
unsigned stream_ck[3]; // SCENERY_STREAM check build: indexed picks compared, corners, mismatching picks
#endif
struct MeshDraw : Emitter {
#if RE4DC_SCENERY_RECORD_SPLIT
    const re4dc::record_split::RecordView package; const re4dc::room::MeshPart& part;
#else
    const re4dc::room::MeshPackage& package; const re4dc::room::MeshPart& part;
#endif
    const std::uint32_t* lut; // mesh view's colour LUT (nullptr: per-corner path)
    re4dc::room::CompactVertex12* gather_pool; // mesh view's v3 gather buffer (nullptr: v1/v2)
#if RE4DC_PS2_PVS
    // (after the four members MeshDraw{...} initializes by position) PS2_PVS: this frame's visible set (nullptr: no
    // set) and the instance number of this part's first cluster in it (pvs::base + pvs::poff)
    const std::uint8_t* pvs_set=nullptr; unsigned pvs_first=0;
#endif
#if RE4DC_PS2_WORLD_LEAN
    // (after the four members MeshDraw{...} initializes by position)
    bool lean_inside=false; // PS2_WORLD_LEAN bit 2: the placement box is inside every plane (no cluster / meshlet tests)
    bool lean_part=false;   // PS2_WORLD_LEAN: a ps2_pass part (bit 2 cluster classes; bit 4 the cache prime kept across the pass)
    const float* lean_am=nullptr; // bit 2: |mvq| 3x3 (lean::abs9), set by ps2_pass
#if RE4DC_PS2_STRIP_GROUPS
    const std::uint8_t* sg=nullptr; unsigned sg_groups=0; // PS2_STRIP_GROUPS: the package's group records (ps2_pass)
    bool sg_whole=false; // this meshlet's cluster / placement is inside every plane: no group tests
    unsigned sg_mask=0;  // the planes the meshlet's box crosses (lean::box_mask)
    bool sg_coef_ok=false; float sg_coef[40] __attribute__((aligned(8))); // lean::sg_coef for this part's mvq
#if RE4DC_SG_SELECT_LEAN
    bool sg_lp_ok=false; lean::SgPlane sg_lp[5]; // SG_SELECT_LEAN: lean::sg_coef_lean for this part's mvq
#endif
#endif
#endif
#if RE4DC_PS2_INTERIOR_CULL
    // PS2_INTERIOR_CULL: pc_mode 0 no test, 1 skip hidden geometry, 2 draw only hidden geometry (the =2 check run);
    // pc_wq: placement affine x grid (world box of a cluster / meshlet); pc_all: the whole placement is hidden.
    unsigned pc_mode=0; const float* pc_wq=nullptr; bool pc_all=false,pc_check=false;
#endif
    // Cluster/meshlet rejection distance: min(projection far, source View far)
    // with RE4DC_NATIVE_FOG, else the projection far. Vertices still clip
    // against the projection far, so a straddling strip is drawn whole (fully
    // fogged past the View far) instead of going through the clipper.
    float cull_far=0;
    unsigned part_index=0; // v2: index into the package's part LOD table
#if RE4DC_PS2_PVS
    unsigned pvs_placement=~0U,pvs_pending[3]={~0U,~0U,0};
    void pvs_finish(bool success){
        if(success && pvs_pending[2] && ps2)re4dc_pvs23_commit(pvs_placement,part_index,pvs_pending,ps2);
        pvs_pending[2]=0;
    }
#endif
#if RE4DC_QUALITY_ASSETS
    std::uint64_t skip_clusters=0; // Standard impt: clusters (bit = index in the part) drawn as tree quads
#endif
    float lod_scale=0;     // v2: level error (model units) * lod_scale <= depth
    re4dc::room::CompactBatch batch{};
    // v3: an indexed meshlet's corners are gathered from its part pool into
    // the view's gather buffer (kGatherBytes in the package allocation), so the
    // transform and the clipper still read one contiguous meshlet.
    re4dc::room::CompactVertex12* gathered=nullptr;
    bool borrow_gather(){
        if(gathered || !package.shared())return true;
        gathered=gather_pool;
        return gathered!=nullptr;
    }
#if RE4DC_SCENERY_STREAM
    // SCENERY_STREAM: the indexed meshlet whose gather is still owed (emit_pick transformed it from its pool). The
    // clipper reads corners by meshlet index, so the gather runs (once, the same copy as corners()) before its first
    // clip strip.
    const RE4DC_SCENERY_RECORD* stream_l=nullptr;
    __attribute__((noinline)) const re4dc::room::CompactVertex12* stream_gather(){
        if(stream_l){const auto* l=stream_l;stream_l=nullptr;return corners(*l);}
        return gathered;
    }
#if defined(RE4DC_SCENERY_STREAM_CHECK) && RE4DC_SCENERY_STREAM_CHECK
    // Check build: the gathered copy through transform_sched must give the same cache words and outcode bits 5..0.
    __attribute__((noinline)) void stream_check(const RE4DC_SCENERY_RECORD& l,unsigned lo,unsigned n){
        static pvr_vertex_t ref[256] __attribute__((aligned(32)));static std::uint8_t roc[256];
        const auto* g=corners(l);
        re4dc::vp::prime(ref,256);
        re4dc::vp::transform_sched<re4dc::vp::kChecksAll>(reinterpret_cast<const re4dc::vp::Vertex12*>(g)+lo,n,ref,roc,k);
        ++stream_ck[0];stream_ck[1]+=n;
        for(unsigned i=0;i<n;++i)
            if(std::memcmp(&ref[i].x,&cache[lo+i].x,24) || ((roc[i]^outcodes[lo+i])&0x3fU)){++stream_ck[2];break;}
    }
#endif
#endif
#if RE4DC_SCENERY_RECORD_SPLIT
    template<class EmitRecord>
    const re4dc::room::CompactVertex12* corners(const EmitRecord& l){
#else
    const re4dc::room::CompactVertex12* corners(const RE4DC_SCENERY_RECORD& l){
#endif
        const auto* base=package.vertices()+l.first_vertex;
#if RE4DC_SCENERY_DEDUP==3
        const unsigned rep=package.repeat_count(l);
        dd_base=rep?base:nullptr;dd_unique=l.vertex_count-rep;dd_count=l.vertex_count;
#endif
        if(!package.indexed(l))return base;
        // Three word moves per corner: R4IM vertices are 4-byte aligned.
        typedef std::uint32_t __attribute__((may_alias)) Word;
        const std::uint16_t* offsets=package.pool_offsets(l);
        const Word* in=reinterpret_cast<const Word*>(base);Word* out=reinterpret_cast<Word*>(gathered);
        for(unsigned k=0;k<l.vertex_count;++k,out+=3){
            const Word* c=in+3U*offsets[k];
            out[0]=c[0];out[1]=c[1];out[2]=c[2];
        }
        return gathered;
    }
#if RE4DC_SCENERY_DEDUP
    // These getters follow corners(l), which refreshes the current meshlet's decoder
    // even for plain/indexed geometry. Reuse that context rather than decode it twice.
    // Modes 1/2 retain their external table word (src offset | repeats << 24).
    std::uint32_t dd_word(const RE4DC_SCENERY_RECORD& l)const{
#if RE4DC_SCENERY_DEDUP==3
        (void)l;
        return (dd_count-dd_unique)<<24;
#else
        return dedup::pkg==static_cast<const void*>(&package)?dedup::lets[&l-package.meshlets()]:0U;
#endif
    }
    bool dd_active(std::uint32_t dw)const{
#if RE4DC_SCENERY_DEDUP==3
        (void)dw;return dd_base!=nullptr;
#else
        return dw>>24;
#endif
    }
    unsigned dd_unique_count(const RE4DC_SCENERY_RECORD& l,std::uint32_t dw)const{
#if RE4DC_SCENERY_DEDUP==3
        (void)l;(void)dw;return dd_unique;
#else
        return l.vertex_count-(dw>>24);
#endif
    }
    const std::uint8_t* dd_source(const RE4DC_SCENERY_RECORD& l,std::uint32_t dw)const{
#if RE4DC_SCENERY_DEDUP==3
        (void)l;(void)dw;
        return reinterpret_cast<const std::uint8_t*>(dd_base+dd_unique);
#else
        (void)l;return dedup::src+(dw&0xffffffU);
#endif
    }
#endif
#if RE4DC_MESH_FASTPATH
    // Transform-once state: the cache borrows the last kCacheSlots slots of
    // the bound packet range (never sent: strips stop at 'limit').
    pvr_vertex_t* cache=nullptr; std::uint8_t* outcodes=nullptr;
    re4dc::vp::Constants k{};
#if RE4DC_PS2_PVS
    void pvs_observed(const RE4DC_SCENERY_RECORD& l){
#if RE4DC_MESH_DIRECT
        if(ps2 && direct && sq && pvs_placement!=~0U)
            re4dc_pvs23_observe(pvs_placement,part_index,unsigned(&l-package.meshlets()),cache,
                outcodes,l.vertex_count,package.strip_begin(l),l.strip_bytes,p.cull,limit,pvs_pending);
#else
        (void)l;
#endif
    }
#endif
#if RE4DC_MESH_PRIME_LAZY
    // MESH_PRIME_LAZY (exact): the cache's constant words are written for the entries a meshlet
    // uses, the first time they are needed, instead of all kCacheEntries at every borrow (one
    // borrow per part per placement: ~30k entries a frame for ~24k transformed PS2 world vertices).
    unsigned primed=0;
#endif
#if RE4DC_WORLD_SCRATCH
    bool scratch_borrowed=false;
    ~MeshDraw(){if(scratch_borrowed)re4dc_world_scratch_release();}
#endif
    bool borrow(){
        if(cache)return true;
        if(!lut || limit<re4dc::vp::kCacheSlots+64U)return false; // small slab: per-corner path
        limit-=re4dc::vp::kCacheSlots;
        cache=dst+limit;outcodes=reinterpret_cast<std::uint8_t*>(cache+re4dc::vp::kCacheEntries);
#if RE4DC_WORLD_SCRATCH
        // Outcodes and all 264 packet slots remain in the original RAM tail.
        // The only relocated storage is the projected record array, for PS2 world.
        if(ps2){
            void* selected=cache;
            const int borrowed=re4dc_world_scratch_acquire(cache,&selected);
            if(borrowed<0){re4dc_model_packet_abort();return false;}
            if(borrowed){
                cache=static_cast<pvr_vertex_t*>(selected);scratch_borrowed=true;
                // acquire resets retained prime state on each mode/storage epoch.
                // The unchanged prime below (or lazy per-entry prime) initializes
                // flags and oargb before any projected entry can be consumed.
            }
        }
#endif
#if !RE4DC_MESH_PRIME_LAZY
        re4dc::vp::prime(cache,re4dc::vp::kCacheEntries);
#endif
#if RE4DC_PS2_WORLD_LEAN && RE4DC_MESH_PRIME_LAZY
        if((lean::kMode&4U) && lean_part && cache==lean::prime_at){
            primed=lean::primed;++lean::st.prime_reuse;
            if(lean::kMode&8U)for(unsigned i=0;i<primed;++i)
                if(cache[i].flags!=PVR_CMD_VERTEX || cache[i].oargb!=0){++lean::st.prime_bad;primed=0;break;}
        }
#endif
        // After bind(): packet.u_scale/v_scale are the bound texture's.
        k={part.uv_scale[0],part.uv_bias[0],p.uv_offset[0],packet.u_scale,
           part.uv_scale[1],part.uv_bias[1],p.uv_offset[1],packet.v_scale,near,far,
           vertex_alpha?~0U:0x00ffffffU,vertex_alpha?0U:alpha,lut,{}};
#if RE4DC_PS2_INTERIOR_CULL==2
        if(pc_check){k.and_mask=0;k.or_bits=0xffff00ffU;} // the check run: every corner opaque magenta
#endif
        k.finish();
        return true;
    }
#if RE4DC_SCENERY_DIRECT_STRIPS
    // SDS1_DIRECT_BEGIN: reuse the ordinary material/SQ owner and transform
    // arithmetic. Only the authenticated sequential payload, a full pick,
    // a conservative inside bound and ordinary sized strips may bypass the
    // transformed cache. Every refusal returns to the original path before
    // emitting a corner. TA_HASH/back-face diagnostics retain that path too.
    bool sequential_direct(const re4dc::room::Meshlet& l){
#if !RE4DC_TA_HASH && !RE4DC_CPU_BACKFACE && RE4DC_MESH_VP_SCHED==1 && RE4DC_HW_LEAN
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        re4dc::wc24::Scope wc_phase(re4dc::wc24::Selection);
#endif
        namespace data=re4dc::scenery_data;
        if(!ps2 || !direct || !sq || data::kind(package)!=data::Kind::DirectStrips)return false;
        const float bmin[3]={float(l.bounds_min[0]),float(l.bounds_min[1]),float(l.bounds_min[2])};
        const float bmax[3]={float(l.bounds_max[0]),float(l.bounds_max[1]),float(l.bounds_max[2])};
        if(re4dc::vp::classify(bmin,bmax,mvq,p.projection,p.viewport,near,far)!=re4dc::vp::kChecksNone)return false;
        const auto source=data::payload(package,l);
        const auto* end=source.strips+source.strip_bytes;
        // The old path sends oversize strips through its clipper even inside.
        // Keep that exact fallback and decide it before any irreversible SQ burst.
        for(const auto* s=source.strips;s<end;){const unsigned n=*s++;if(n>limit)return false;s+=n;}
        const auto* in=reinterpret_cast<const re4dc::vp::Vertex12*>(source.vertices);
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        // Fused work has no separate cached-submit interval. Charge the whole
        // transform/SQ loop here; output corners stay in direct-account once.
        wc_phase.phase(re4dc::wc24::Transform);
#endif
        unsigned vertices=0,strips=0;
        for(const auto* s=source.strips;s<end;){
            const unsigned n=*s++;
            sq=data::emit_direct_strip(sq,in+vertices,n,k);
            vertices+=n;++strips;s+=n;
        }
        input+=vertices-2U*strips;output+=vertices-2U*strips;slots+=vertices;
        stats.vertices+=vertices;stats.strips+=strips;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        re4dc::wc24::count(re4dc::wc24::Transformed,vertices);
        re4dc::wc24::count(re4dc::wc24::StripInputs,vertices);
#endif
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
        re4dc_wm_corners(nullptr,vertices,0U); // the bound proves every transformed input inside
#endif
        return true;
#else
        (void)l;return false;
#endif
    }
    // SDS1_DIRECT_END
#endif
    // One visible meshlet: every vertex once through XMTRX, then each strip is
    // accepted (copied from the cache), culled (all corners outside one screen
    // edge) or handed to the unchanged clipper (a corner outside near/far),
    // the same three outcomes, in the same order, as Emitter::strip().
    int meshlet(const RE4DC_SCENERY_RECORD& l,const re4dc::room::CompactBatch& batch){
        namespace vp=re4dc::vp;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        re4dc::wc24::Scope wc_phase(re4dc::wc24::Selection);
        Wc24Count wc_strip_inputs(re4dc::wc24::StripInputs);
#endif
#if defined(RE4DC_SCN_CENSUS) && RE4DC_SCN_CENSUS
        struct CenScope {
            const Emitter* e;unsigned n,s0,c0,o0,v0;
            ~CenScope(){
                const unsigned es=stats.strips-s0,cs=stats.strips_culled-c0;
                scn_cen[0]++;scn_cen[1]+=n;if(!es)scn_cen[2]+=n;scn_cen[3]+=es;scn_cen[4]+=cs;scn_cen[5]+=e->output-o0;
                if(!es && cs)scn_cen[6]++;
            }
        } cen{this,l.vertex_count,stats.strips,stats.strips_culled,output,0};
#endif
#if RE4DC_SCENERY_DIRECT_STRIPS
        if(sequential_direct(l))return 1;
#endif
        const float bmin[3]={float(l.bounds_min[0]),float(l.bounds_min[1]),float(l.bounds_min[2])};
        const float bmax[3]={float(l.bounds_max[0]),float(l.bounds_max[1]),float(l.bounds_max[2])};
        // RE4DC_MESH_CLASSIFY=0 (default) saves ~1.5 KiB of image, i.e. KOS heap,
        // at ~8 cycles per vertex for outcodes in every meshlet.
        const unsigned checks=RE4DC_MESH_CLASSIFY?vp::classify(bmin,bmax,mvq,p.projection,p.viewport,near,far):vp::kChecksAll;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        wc_phase.phase(re4dc::wc24::Transform);
#endif
        const auto* base=corners(l);
        const auto* in=reinterpret_cast<const vp::Vertex12*>(base);
#if RE4DC_MESH_PRIME_LAZY
        if(l.vertex_count>primed){vp::prime(cache+primed,l.vertex_count-primed);primed=l.vertex_count;
#if RE4DC_PS2_WORLD_LEAN
            if(lean_part){lean::prime_at=cache;lean::primed=primed;}
#endif
        }
#endif
#if RE4DC_PS2_STRIP_GROUPS
        // PS2_STRIP_GROUPS: a straddling meshlet tests its strip groups' grid boxes (outside one screen edge or nearer
        // than near: every strip of the group would be culled after the transform), transforms only the corner
        // range of the groups left and walks only their strips (in stored order). All groups left: the whole path.
        RE4DC_WO26_SG_CELL if(sg && !sg_whole && checks==vp::kChecksAll && sq && lean_am){
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
            re4dc::wc24::Scope wc_groups(re4dc::wc24::Selection);
#endif
            const auto* g=reinterpret_cast<const std::uint16_t*>(sg+16U*sg_groups*unsigned(&l-package.meshlets()));
            unsigned lo,hi,culled;std::uint16_t r0[8],r1[8];
#if RE4DC_SG_SELECT_LEAN
            unsigned nr;
            if(re4dc_sg_lean_on){
                if(!sg_lp_ok){lean::sg_coef_lean(mvq,near,sg_lp);sg_lp_ok=true;}
                nr=lean::sg_select_lean(g,sg_groups,sg_lp,sg_mask,r0,r1,lo,hi,culled);
                ++lean::lst.calls;
#if RE4DC_SG_SELECT_LEAN==2
                // the check build: the original functions on the same input must agree in every output
                if(!sg_coef_ok){lean::sg_coef(mvq,near,sg_coef);sg_coef_ok=true;}
                unsigned lo2,hi2,culled2;std::uint16_t q0[8],q1[8];
                const unsigned nr2=lean::sg_select(g,sg_groups,sg_coef,sg_mask,q0,q1,lo2,hi2,culled2);
                bool bad=nr2!=nr || culled2!=culled || (nr && (lo2!=lo || hi2!=hi));
                for(unsigned i=0;i<nr && i<nr2;++i)if(q0[i]!=r0[i] || q1[i]!=r1[i])bad=true;
                if(bad && ++lean::lst.sel_bad<=8)
                    re4dc_log("SGLEAN select mismatch nr=%u/%u culled=%u/%u lo=%u/%u hi=%u/%u mask=%u\n",nr,nr2,culled,culled2,
                        lo,lo2,hi,hi2,sg_mask);
#endif
            }else{
                if(!sg_coef_ok){lean::sg_coef(mvq,near,sg_coef);sg_coef_ok=true;}
                nr=lean::sg_select(g,sg_groups,sg_coef,sg_mask,r0,r1,lo,hi,culled);
            }
#else
            if(!sg_coef_ok){lean::sg_coef(mvq,near,sg_coef);sg_coef_ok=true;}
            const unsigned nr=lean::sg_select(g,sg_groups,sg_coef,sg_mask,r0,r1,lo,hi,culled);
#endif
            ++lean::st.sg_tests;
            if(culled){
                lean::st.sg_culled+=culled;++lean::st.sg_meshlets;
                if(!nr){lean::st.sg_vskip+=l.vertex_count;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
                    re4dc::wc24::count(re4dc::wc24::PickedEmpty);
#endif
#if defined(RE4DC_SCN_CENSUS) && RE4DC_SCN_CENSUS
                    cen.n=0;
#endif
                    return 1;}
                const unsigned vn=hi-lo+1U;lean::st.sg_vskip+=l.vertex_count-vn;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
                wc_groups.phase(re4dc::wc24::Transform);
                re4dc::wc24::count(re4dc::wc24::Transformed,vn);
#endif
#if defined(RE4DC_SCN_CENSUS) && RE4DC_SCN_CENSUS
                cen.n=vn;
#endif
#if RE4DC_MESH_VP_SCHED==1
                vp::transform_sched<vp::kChecksAll>(in+lo,vn,cache+lo,outcodes+lo,k);
#if RE4DC_SCENERY_DEDUP
                if(const std::uint32_t dw=dd_word(l);dd_active(dw))
                    dedup::fill(in,cache,outcodes,dd_unique_count(l,dw),l.vertex_count,dd_source(l,dw),k,lo,hi);
#endif
#else
                vp::transform<vp::kChecksAll>(in+lo,vn,cache+lo,outcodes+lo,k);
#endif
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
                if(ps2)re4dc_wm_corners(outcodes+lo,vn,0x3fU);
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
                wc_groups.phase(re4dc::wc24::Submit);
#endif
                const std::uint8_t* const sb=package.strip_begin(l);
                for(unsigned i=0;i<nr;++i){
                    int result=1;
                    strips_lean(sb+r0[i],sb+r1[i],base,batch,result);
                    if(result<=0)return result;
                }
                return 1;
            }
        }
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        // Count the actual arithmetic input range. DEDUP's copied entries are
        // prepared output but are not additional position transforms.
        unsigned wc_vertices=l.vertex_count;
#if RE4DC_SCENERY_DEDUP==3
        if(checks!=vp::kChecksAll)
            if(const std::uint32_t dw=dd_word(l);dd_active(dw))wc_vertices=dd_unique_count(l,dw);
#endif
#if RE4DC_MESH_VP_SCHED==1 && RE4DC_SCENERY_DEDUP
        if(checks==vp::kChecksAll)
            if(const std::uint32_t dw=dd_word(l);dd_active(dw))wc_vertices=dd_unique_count(l,dw);
#endif
        re4dc::wc24::count(re4dc::wc24::Transformed,wc_vertices);
#endif
#if RE4DC_SCENERY_DEDUP==3
        if(const std::uint32_t dw=dd_word(l);dd_active(dw) && checks!=vp::kChecksAll){
            const unsigned u=dd_unique_count(l,dw);
            if(checks==vp::kChecksNone)vp::transform<vp::kChecksNone>(in,u,cache,outcodes,k);
            else vp::transform<vp::kChecksScreen>(in,u,cache,outcodes,k);
            dedup::fill(in,cache,outcodes,u,l.vertex_count,dd_source(l,dw),k);
        }else
#endif
        if(checks==vp::kChecksNone)vp::transform<vp::kChecksNone>(in,l.vertex_count,cache,outcodes,k);
        else if(checks==vp::kChecksScreen)vp::transform<vp::kChecksScreen>(in,l.vertex_count,cache,outcodes,k);
#if RE4DC_MESH_VP_SCHED==1 && RE4DC_SCENERY_DEDUP
        else if(const std::uint32_t dw=dd_word(l);dd_active(dw)){
            const unsigned u=dd_unique_count(l,dw);
            vp::transform_sched<vp::kChecksAll>(in,u,cache,outcodes,k);
            dedup::fill(in,cache,outcodes,u,l.vertex_count,dd_source(l,dw),k);
        }
        else vp::transform_sched<vp::kChecksAll>(in,l.vertex_count,cache,outcodes,k);
#elif RE4DC_MESH_VP_SCHED==1
        else vp::transform_sched<vp::kChecksAll>(in,l.vertex_count,cache,outcodes,k);
#elif RE4DC_MESH_VP_SCHED==3
        else if(vp_sched_select==2U)vp::transform_sched<vp::kChecksAll>(in,l.vertex_count,cache,outcodes,k);
        else vp::transform<vp::kChecksAll>(in,l.vertex_count,cache,outcodes,k);
#else
        else vp::transform<vp::kChecksAll>(in,l.vertex_count,cache,outcodes,k);
#endif
#if RE4DC_MESH_VP_SCHED==2
        if(checks==vp::kChecksAll)vp_sched_compare(in,l.vertex_count,cache,outcodes,k);
#endif
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
        if(ps2){
            unsigned count=l.vertex_count;
#if RE4DC_MESH_VP_SCHED==1 && RE4DC_SCENERY_DEDUP
            if(checks==vp::kChecksAll)if(const std::uint32_t dw=dd_word(l);dw>>24)count-=dw>>24;
#endif
            re4dc_wm_corners(outcodes,count,checks==vp::kChecksNone?0U:checks==vp::kChecksScreen?0x0fU:0x3fU);
        }
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        wc_phase.phase(re4dc::wc24::Submit);
#endif
        const unsigned screen=vp::screen_mask(checks),depth=vp::depth_mask(checks);
#if RE4DC_MESH_STRIP_LEAN==2
        if(checks==vp::kChecksAll && sq)strip_lean_compare(l);
#endif
        const std::uint8_t* s=package.strip_begin(l);
        const std::uint8_t* const end=s+l.strip_bytes;
#if RE4DC_MESH_STRIP_LEAN==1 || RE4DC_MESH_STRIP_LEAN==3
        // The lean walk takes kChecksAll meshlets on the store-queue sink (n > limit is one of its clip
        // stops, as below); other meshlets keep this original walk.
        if(checks==vp::kChecksAll && sq
#if RE4DC_MESH_STRIP_LEAN==3
           && strip_lean_select==2U
#endif
          ){int result=1;s=strips_lean(s,end,base,batch,result);
#if RE4DC_PS2_PVS
                if(!s && result>0 && checks==vp::kChecksAll)pvs_observed(l);
#endif
                if(!s)return result;}
#endif
        while(s<end){
            const unsigned n=*s++;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
            wc_strip_inputs.n+=n;
#endif
            input+=n-2;
            vp::StripCodes c{0,0};
            if(screen)c=vp::codes(outcodes,s,n);
#if RE4DC_MESH_DEPTH_CULL
            // Every corner outside the same depth plane (nearer than near, which includes behind the
            // camera, or past far): the clipper would emit nothing, so the strip is dropped here.
            if(c.all&depth){stats.vertices+=n;++stats.strips_culled;s+=n;continue;}
#endif
            if((c.any&depth) || n>limit){
                if(n<=limit)stats.vertices+=n;
                const int result=clip_strip(base,batch,s,n);
                if(result<=0)return result;
            }else {
                stats.vertices+=n;
                if(c.all&screen)++stats.strips_culled;
#if RE4DC_MESH_DIRECT
#if defined(RE4DC_CPU_BACKFACE) && RE4DC_CPU_BACKFACE
                else if(sq && bf_on()){bf_send(s,n);output+=n-2;++stats.strips;}
#endif
                else if(sq){sq=vp::emit_sq(sq,cache,s,n);slots+=n;output+=n-2;++stats.strips;}
#endif
                else {
                    if(n>limit-used && !flush())return submitted?-1:0;
                    vp::emit(dst+used,cache,s,n);
                    used+=n;output+=n-2;++stats.strips;
                }
            }
            s+=n;
        }
#if RE4DC_PS2_PVS
        if(checks==vp::kChecksAll)pvs_observed(l);
#endif
        return 1;
    }
#if defined(RE4DC_CPU_BACKFACE) && RE4DC_CPU_BACKFACE == 2
    // The caller's source material still owns cull/depth/alpha. Two-sided cards and
    // no-depth-write runs keep their original walk; accepted opaque strips use
    // only the common assembly emitter for facing, run splitting and SQ writes.
#if defined(RE4DC_BACKFACE_ROOMS) && RE4DC_BACKFACE_ROOMS
    bool bf_on()const{return re4dc_bf_room_on && (p.cull==1U || p.cull==2U) && !(p.material_flags&4U) && p.depth_mode==0U;}
#else
    bool bf_on()const{return (p.cull==1U || p.cull==2U) && !(p.material_flags&4U) && p.depth_mode==0U;}
#endif
    void bf_send(const std::uint8_t* s,unsigned n){
        slots+=re4dc::bf::strip_sq(cache,s,n,0xffU,p.cull,sq);
    }
#endif
#if RE4DC_MESH_STRIP_LEAN==1 || RE4DC_MESH_STRIP_LEAN==3
    // MESH_STRIP_LEAN: meshlet()'s strip walk for kChecksAll meshlets on the store-queue sink. walk_lean()
    // (room/mesh_strip_lean.hpp) takes the strips up to the next one that needs the clipper with the same
    // StripCodes words, decisions, order and TA bursts as the original loop, keeping the per-strip counter
    // updates in registers. Between clip strips every strip is culled or emitted, so for the strips in
    // [mark, s):  sum n = (s - mark) - strips,  slots = (q - qmark) / 32 B,  output = slots - 2 * emitted,
    // input = sum n - 2 * strips, stats.vertices = sum n. lean_flush() writes these back before the
    // clipper (which reads and updates the members) and at the end; the clip strip itself runs the
    // original code. Returns nullptr when the meshlet is done (result: meshlet()'s value).
#if defined(RE4DC_CPU_BACKFACE) && RE4DC_CPU_BACKFACE == 1
    // CPU_BACKFACE (lane backface22): parts whose header culls (p.cull 1 CCW, 2 CW) send only the triangles the ISP would
    // keep (room/backface_emit.hpp); cull-none parts keep the unchanged paths. strips_bf: the lean walk's decisions in C
    // (depth-all cull, clipper for a depth crossing or n > limit, screen-all cull, else the back-face split).
    bool bf_on()const{return p.cull==1U || p.cull==2U;}
    void bf_send(const std::uint8_t* s,unsigned n){
        slots+=re4dc::bf::strip(cache,s,n,0xffU,p.cull,[&](const std::uint8_t* i,unsigned c){sq=re4dc::vp::emit_sq(sq,cache,i,c);});
    }
    const std::uint8_t* strips_bf(const std::uint8_t* s,const std::uint8_t* end,const re4dc::room::CompactVertex12* base,
                                  const re4dc::room::CompactBatch& batch,int& result){
        namespace vp=re4dc::vp;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        Wc24Count wc_strip_inputs(re4dc::wc24::StripInputs);
#endif
        constexpr unsigned screen=vp::screen_mask(vp::kChecksAll),depth=vp::depth_mask(vp::kChecksAll);
        while(s<end){
            const unsigned n=*s++;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
            wc_strip_inputs.n+=n;
#endif
            input+=n-2;
            const vp::StripCodes c=vp::codes(outcodes,s,n);
            if(c.all&depth){stats.vertices+=n;++stats.strips_culled;s+=n;continue;}
            if((c.any&depth) || n>limit){
                if(n<=limit)stats.vertices+=n;
                result=clip_strip(base,batch,s,n);
                if(result<=0)return nullptr;
            }else{
                stats.vertices+=n;
                if(c.all&screen)++stats.strips_culled;
                else{bf_send(s,n);output+=n-2;++stats.strips;}
            }
            s+=n;
        }
        result=1;return nullptr;
    }
#endif
#if defined(RE4DC_CPU_BACKFACE) && RE4DC_CPU_BACKFACE == 2
    const std::uint8_t* strips_bf_sq(const std::uint8_t* s,const std::uint8_t* end,const re4dc::room::CompactVertex12* base,
                                     const re4dc::room::CompactBatch& batch,int& result){
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        Wc24Count wc_strip_inputs(re4dc::wc24::StripInputs);
#endif
        for(;;){
            const std::uint8_t* const mark=s;std::uint32_t* q=sq;const std::uint32_t* const qmark=q;
            unsigned culled=0,emitted=0,accepted_triangles=0;
            s=re4dc::vp::walk_lean_sq(s,end,outcodes,cache,limit,p.cull,q,culled,emitted,accepted_triangles);
            // Backface splitting may send zero vertices or several pieces.
            // Keep the C reference's source-strip counters; slots track actual
            // SQ writes. lean_flush's output=slots-2*strips cannot be used here.
            const unsigned strips=culled+emitted,sum=unsigned(s-mark)-strips;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
            wc_strip_inputs.n+=sum;
#endif
            input+=sum-2U*strips;stats.vertices+=sum;stats.strips_culled+=culled;stats.strips+=emitted;
            slots+=unsigned(q-qmark)/8U;output+=accepted_triangles;sq=q;
            // Actual emitted pieces are hashed by the common assembly trace
            // hook in diagnostic builds. Do not replay rejected original strips.
            if(s>=end){result=1;return nullptr;}
            const unsigned n=*s++; // unchanged depth-crossing / oversize clipper
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
            wc_strip_inputs.n+=n;
#endif
            input+=n-2;
            if(n<=limit)stats.vertices+=n;
#if RE4DC_SCENERY_STREAM
            if(!base)base=stream_gather();   // backface26: the owed gather before a clip strip, as strips_lean
#endif
            result=clip_strip(base,batch,s,n);
            if(result<=0)return nullptr;
            s+=n;
        }
    }
#endif
    void lean_flush(const std::uint8_t* s,const std::uint8_t* mark,std::uint32_t* q,const std::uint32_t* qmark,
                    unsigned culled,unsigned emitted){
        const unsigned strips=culled+emitted,sum=unsigned(s-mark)-strips,v=unsigned(q-qmark)/8U;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        re4dc::wc24::count(re4dc::wc24::StripInputs,sum);
#endif
        input+=sum-2U*strips;stats.vertices+=sum;stats.strips_culled+=culled;stats.strips+=emitted;
        slots+=v;output+=v-2U*emitted;sq=q;
    }
    const std::uint8_t* strips_lean(const std::uint8_t* s,const std::uint8_t* end,const re4dc::room::CompactVertex12* base,
                                    const re4dc::room::CompactBatch& batch,int& result){
#if defined(RE4DC_CPU_BACKFACE) && RE4DC_CPU_BACKFACE == 2
        if(bf_on())return strips_bf_sq(s,end,base,batch,result);
#elif defined(RE4DC_CPU_BACKFACE) && RE4DC_CPU_BACKFACE
        if(bf_on())return strips_bf(s,end,base,batch,result);
#endif
        for(;;){
            const std::uint8_t* const mark=s;std::uint32_t* q=sq;const std::uint32_t* const qmark=q;
            unsigned culled=0,emitted=0;
            s=re4dc::vp::walk_lean(s,end,outcodes,cache,limit,q,culled,emitted);
#if defined(RE4DC_TA_HASH) && RE4DC_TA_HASH && RE4DC_TA_HASH != 4
            // TA_HASH (test builds): walk_lean writes the store queues itself, so the run is walked again here
            // and every emitted strip's words are hashed as emit_sq() hashes them (EOL in the last flags word).
            // Every strip in [mark, s) was culled or emitted (walk_lean stops before a clip strip).
            for(const std::uint8_t* h=mark;h<s;){
                const unsigned n=*h++;const re4dc::vp::StripCodes c=re4dc::vp::codes(outcodes,h,n);
                if(!(c.all&(re4dc::vp::depth_mask(re4dc::vp::kChecksAll)|re4dc::vp::screen_mask(re4dc::vp::kChecksAll))))
                    for(unsigned k=0;k<n;++k){
                        std::uint32_t w[8];__builtin_memcpy(w,cache+h[k],32);
                        if(k+1==n)w[0]=PVR_CMD_VERTEX_EOL;
                        ::re4dc_ta_hash(w,32);
                    }
                h+=n;
            }
#endif
            lean_flush(s,mark,q,qmark,culled,emitted);
            if(s>=end){result=1;return nullptr;}
            const unsigned n=*s++; // a strip for the clipper: meshlet()'s code
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
            re4dc::wc24::count(re4dc::wc24::StripInputs,n);
#endif
            input+=n-2;
            if(n<=limit)stats.vertices+=n;
#if RE4DC_SCENERY_STREAM
            if(!base)base=stream_gather();
#endif
            result=clip_strip(base,batch,s,n);
            if(result<=0)return nullptr;
            s+=n;
        }
    }
#endif
#if RE4DC_MESH_STRIP_LEAN==2
    // MESH_STRIP_LEAN=2 (diagnostic): before the original walk draws the meshlet, each run of strips up to
    // a clip strip is walked twice into RAM (in place of the store queues): the reference is meshlet()'s
    // loop body (codes(), the decisions, emit_sq()), the candidate is walk_lean(). Compared: stop strip,
    // culled / emitted counts, every written word, and the lean_flush() counter formulas against the
    // reference's per-strip sums. Meshlets with more strip bytes than the buffers hold are counted as
    // skipped.
    void strip_lean_compare(const RE4DC_SCENERY_RECORD& l){
        namespace vp=re4dc::vp;
        constexpr unsigned screen=vp::screen_mask(vp::kChecksAll),depth=vp::depth_mask(vp::kChecksAll);
        const std::uint8_t* s=package.strip_begin(l);
        const std::uint8_t* const end=s+l.strip_bytes;
        ++strip_lean_stats[0];
        if(l.strip_bytes>kStripLeanVertices){++strip_lean_stats[6];return;}
        while(s<end){
            const std::uint8_t* sa=s;std::uint32_t* qa=strip_lean_buf[0];unsigned ca=0,ea=0;
            unsigned ref[4]={}; // input, vertices, slots, output
            while(sa<end){
                const unsigned n=*sa;const vp::StripCodes c=vp::codes(outcodes,sa+1,n);
                ++strip_lean_stats[1];
                if(c.all&depth){ref[0]+=n-2;ref[1]+=n;++ca;sa+=1+n;continue;}
                if((c.any&depth) || n>limit)break;
                ref[0]+=n-2;ref[1]+=n;
                if(c.all&screen){++ca;sa+=1+n;continue;}
                qa=vp::emit_sq(qa,cache,sa+1,n);ref[2]+=n;ref[3]+=n-2;++ea;strip_lean_stats[5]+=n;sa+=1+n;
            }
            std::uint32_t* qb=strip_lean_buf[1];unsigned cb=0,eb=0;
            const std::uint8_t* const sb=vp::walk_lean(s,end,outcodes,cache,limit,qb,cb,eb);
            strip_lean_stats[2]+=ea;
            const unsigned strips=cb+eb,sum=unsigned(sb-s)-strips,v=unsigned(qb-strip_lean_buf[1])/8U;
            const unsigned lean[4]={sum-2U*strips,sum,v,v-2U*eb};
            bool bad=sa!=sb || ca!=cb || ea!=eb || qa-strip_lean_buf[0]!=qb-strip_lean_buf[1] ||
                     __builtin_memcmp(strip_lean_buf[0],strip_lean_buf[1],4U*unsigned(qa-strip_lean_buf[0]))!=0;
            for(unsigned i=0;i<4;++i)if(lean[i]!=ref[i]){bad=true;++strip_lean_stats[4];}
            if(bad && ++strip_lean_stats[3]<=8)
                re4dc_log("STRIPLEAN mismatch stop=%d/%d culled=%u/%u emitted=%u/%u words=%d/%d sums=%u,%u,%u,%u/%u,%u,%u,%u\n",
                    int(sa-s),int(sb-s),ca,cb,ea,eb,int(qa-strip_lean_buf[0]),int(qb-strip_lean_buf[1]),
                    ref[0],ref[1],ref[2],ref[3],lean[0],lean[1],lean[2],lean[3]);
            if(sa>=end)break;
            s=sa+1+*sa; // past the clip strip: the original code path in both walks
        }
    }
#endif
#endif
    // One meshlet: 1 drawn or culled, 0 fallback allowed, -1 frame aborted.
    int draw(const RE4DC_SCENERY_RECORD& l
#if RE4DC_PS2_WORLD_LEAN
             ,bool known=false // PS2_WORLD_LEAN bit 2: the meshlet's cluster (or placement) is inside every plane
#endif
            ){
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        re4dc::wc24::Scope wc_phase(re4dc::wc24::Selection);
#endif
#if RE4DC_PS2_WORLD_LEAN
        if(known){
            ++lean::st.skipped;
            if(lean::kMode&8U){
                const re4dc::render::DrawBounds bounds{
                    {float(l.bounds_min[0]),float(l.bounds_min[1]),float(l.bounds_min[2])},
                    {float(l.bounds_max[0]),float(l.bounds_max[1]),float(l.bounds_max[2])}};
                if(!re4dc::render::group_visible(bounds,mvq,p.projection,p.viewport,near,cull_far,0))++lean::st.check_bad;
            }
        }else{
#endif
#if RE4DC_PS2_STRIP_GROUPS
        if(sg && lean_am){
            const float blo[3]={float(l.bounds_min[0]),float(l.bounds_min[1]),float(l.bounds_min[2])};
            const float bhi[3]={float(l.bounds_max[0]),float(l.bounds_max[1]),float(l.bounds_max[2])};
#if RE4DC_SG_SELECT_LEAN
            int mk;
            if(re4dc_sg_lean_on){
                mk=lean::box_mask_lean(blo,bhi,mvq,lean_am,near,cull_far);
                ++lean::lst.bm;
#if RE4DC_SG_SELECT_LEAN==2
                if(lean::box_mask(blo,bhi,mvq,lean_am,near,cull_far)!=mk && ++lean::lst.bm_bad<=8)re4dc_log("SGLEAN box_mask mismatch\n");
#endif
                // the group records sg_select reads (64 B for 4 groups): fetched while bind / borrow / the gather run
                if(mk>0){
                    const std::uint8_t* rec=sg+16U*sg_groups*unsigned(&l-package.meshlets());
                    __builtin_prefetch(rec);__builtin_prefetch(rec+16U*sg_groups-1U);
                }
            }else mk=lean::box_mask(blo,bhi,mvq,lean_am,near,cull_far);
#else
            const int mk=lean::box_mask(blo,bhi,mvq,lean_am,near,cull_far);
#endif
            if(mk<0){++stats.groups_culled;return 1;}
            sg_mask=unsigned(mk);
        }else{
#endif
        const re4dc::render::DrawBounds bounds{
            {float(l.bounds_min[0]),float(l.bounds_min[1]),float(l.bounds_min[2])},
            {float(l.bounds_max[0]),float(l.bounds_max[1]),float(l.bounds_max[2])}};
        if(!re4dc::render::group_visible(bounds,mvq,p.projection,p.viewport,near,cull_far,0)){++stats.groups_culled;return 1;}
#if RE4DC_PS2_STRIP_GROUPS
        }
#endif
#if RE4DC_PS2_WORLD_LEAN
        }
#endif
        ++stats.groups_visible;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        re4dc::wc24::count(package.indexed(l)?re4dc::wc24::PickedIndexed:re4dc::wc24::PickedPlain);
        wc_phase.phase(re4dc::wc24::Other);
#endif
        if(!bind()){++stats.bind_rejects;return submitted?-1:0;}
        ++stats.batches;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        wc_phase.phase(re4dc::wc24::Transform);
#endif
        if(!borrow_gather()){++stats.reserve_rejects;return submitted?-1:0;}
#if RE4DC_MESH_FASTPATH
        // A slab too small to lend the cache behaves like any other
        // capacity failure: generic fallback, or abort once published.
        if(!borrow()){++stats.reserve_rejects;return submitted?-1:0;}
#if RE4DC_PS2_STRIP_GROUPS
        sg_whole=known || !sg_mask;
        if(known)sg_mask=0;
#endif
        return meshlet(l,batch);
#else
        const auto* base=corners(l);
        const std::uint8_t* s=package.strip_begin(l);
        const std::uint8_t* const end=s+l.strip_bytes;
        while(s<end){
            const unsigned n=*s++;
            const int result=strip(base,batch,s,n);
            if(result<=0)return result;
            s+=n;
        }
        return 1;
#endif
    }
#if RE4DC_MESH_LOD
    // v2: cluster test, then the coarsest level within tolerance at the
    // cluster's nearest view depth (group_visible's support radius along z).
    int draw_clusters(){
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        const re4dc::wc24::Scope wc_selection(re4dc::wc24::Selection);
#endif
        const auto& lod=package.part_lods()[part_index];
        const auto* clusters=package.clusters();const auto* levels=package.levels();
        for(unsigned c=lod.first_cluster;c<lod.first_cluster+lod.cluster_count;++c){
#if RE4DC_QUALITY_ASSETS
            if(skip_clusters && c-lod.first_cluster<64U && ((skip_clusters>>(c-lod.first_cluster))&1U))continue;
#endif
#if RE4DC_PS2_PVS
            if(pvs_set){
                // PS2_PVS: a cluster the camera's cell cannot see (offline occlusion set) is not tested or drawn
                const unsigned bit=pvs_first+(c-lod.first_cluster);++pvs::cl_tested;
                if(!((pvs_set[bit>>3]>>(bit&7U))&1U)){++pvs::cl_skipped;continue;}
            }
#endif
            const auto& cl=clusters[c];
            float lo[3],hi[3];
            for(unsigned a=0;a<3;++a){lo[a]=float(cl.bounds_min[a]);hi[a]=float(cl.bounds_max[a]);}
            const re4dc::render::DrawBounds bounds{{lo[0],lo[1],lo[2]},{hi[0],hi[1],hi[2]}};
#if RE4DC_PS2_WORLD_LEAN
            unsigned cin;
            if(lean_inside){
                cin=2;++lean::st.skipped;
                if((lean::kMode&8U) && !re4dc::render::group_visible(bounds,mvq,p.projection,p.viewport,near,cull_far,0))++lean::st.check_bad;
            }else if((lean::kMode&2U) && lean_am)cin=lean::box_class(lo,hi,mvq,lean_am,near,cull_far,nullptr);
            else cin=re4dc::render::group_visible(bounds,mvq,p.projection,p.viewport,near,cull_far,0)?1U:0U;
            if(!cin){++stats.clusters_culled;continue;}
            if(cin==2)++lean::st.cl_inside;
#else
            if(!re4dc::render::group_visible(bounds,mvq,p.projection,p.viewport,near,cull_far,0)){++stats.clusters_culled;continue;}
#endif
#if RE4DC_PS2_INTERIOR_CULL
            // 1 the cluster is hidden, 0 seen (or not tested), -1 it meets the house box: each meshlet is tested.
            const int pc_state=!pc_mode?0:pc_all?1:pc::grid_hidden(pc_wq,cl.bounds_min,cl.bounds_max);
            if(pc_state>0 && pc_mode==1){++pc::st.clusters;continue;}
            if(!pc_state && pc_mode==2)continue;
#endif
            ++stats.clusters_visible;
            float depth=-mvq[11],radius=0;
            for(unsigned a=0;a<3;++a){
                depth-=mvq[8+a]*(lo[a]+hi[a])*0.5f;
                radius+=std::fabs(mvq[8+a])*(hi[a]-lo[a])*0.5f;
            }
            depth-=radius;
            if(depth<near)depth=near;
            unsigned level=cl.level_count-1;
            while(level && levels[cl.first_level+level].error*lod_scale>depth)--level;
#if RE4DC_PS2_WORLD_NONEMPTY_LOD
            if(ps2)level=re4dc::room::nonempty_lod(levels+cl.first_level,cl.level_count,level);
#endif
            ++stats.lod_draws[level<3?level:3];
            const auto& lv=levels[cl.first_level+level];
#if RE4DC_SCENERY_RECORD_SPLIT
            const auto lets=package.meshlets()+lv.first_meshlet;
#else
            const auto* lets=package.meshlets()+lv.first_meshlet;
#endif
            for(unsigned i=0;i<lv.meshlet_count;++i){
#if RE4DC_PS2_INTERIOR_CULL
                if(pc_state<0){
                    const bool hid=pc::grid_hidden(pc_wq,lets[i].bounds_min,lets[i].bounds_max)>0;
                    if(hid==(pc_mode==1)){if(hid)++pc::st.meshlets;continue;} // =1: skip hidden; check run: skip seen
                }
#endif
#if RE4DC_PS2_WORLD_LEAN
                const int result=draw(lets[i],cin==2);
#else
                const int result=draw(lets[i]);
#endif
                if(result<=0)return result;
            }
        }
        return 1;
    }
#endif
#if RE4DC_SCENERY_CHUNK
#if !(RE4DC_MESH_LOD && RE4DC_MESH_FASTPATH && RE4DC_MESH_DIRECT && RE4DC_PS2_WORLD_LEAN && RE4DC_MESH_PRIME_LAZY && \
      RE4DC_MESH_VP_SCHED==1 && RE4DC_MESH_STRIP_LEAN==1 && RE4DC_HW_LEAN && !RE4DC_MESH_CLASSIFY)
#error SCENERY_CHUNK needs the Test 18 world recipe (MESH_LOD, MESH_FASTPATH, MESH_DIRECT, PS2_WORLD_LEAN, MESH_PRIME_LAZY, MESH_VP_SCHED=1, MESH_STRIP_LEAN=1, HW_LEAN)
#endif
    // SCENERY_CHUNK: a PS2 world part drawn in two phases. chunk_select() runs every cluster / LOD / meshlet /
    // strip-group decision of draw_clusters() + draw() + meshlet() with the same functions and expressions, in the same
    // order, and records each meshlet to draw as a pick; ps2_pass selects a run of parts, then chunk_emit() binds,
    // transforms and walks each part's picks in the same order. The same strips reach the TA in the same order with
    // the same words; the selection code and the emission code each stay in the instruction cache for a burst instead
    // of alternating per meshlet. Used only when no PVS set, interior cull, Standard impostor skip or check mode
    // (lean bit 8) applies (chunk_ok()).
    struct Pick {
        std::uint16_t let;            // meshlet index in the package
        std::uint8_t nr,gmask,lo,hi;  // nr 0xff: the whole meshlet; else the strip groups left (gmask: group bits)
        std::uint8_t pad[2];
    };
#include "include/scenery_chunk_select.inc"
#if RE4DC_SCENERY_EMIT_PREFETCH
    // SCENERY_EMIT_PREFETCH_MEMBERS_BEGIN
    // Only immutable package input is hinted. No binding, matrix, material or
    // scratch ownership is carried across the next part's bind (which may yield).
    static void emit_prefetch_span(const void* ptr,unsigned bytes){
        const auto* p=static_cast<const std::uint8_t*>(ptr);
        __builtin_prefetch(p);
        if((reinterpret_cast<std::uintptr_t>(p)&31U)+bytes>32U)
            __builtin_prefetch(p+bytes-1U);
    }
    void prefetch_emit_header(const Pick& pk)const{
        // Meshlet has a 28-byte stride; only the first 16 bytes feed emission.
#if RE4DC_SCENERY_RECORD_SPLIT
        emit_prefetch_span(&package.emit(pk.let),16U);
#else
        emit_prefetch_span(package.meshlets()+pk.let,16U);
#endif
    }
    void prefetch_emit_payload(const Pick& pk)const{
        if(!pk.nr)return;
#if RE4DC_SCENERY_RECORD_SPLIT
        const auto& l=package.emit(pk.let);
#else
        const auto& l=package.meshlets()[pk.let];
#endif
        const auto* base=package.vertices()+l.first_vertex;
        const auto* raw=package.strips()+l.first_strip;
        if(package.indexed(l)){
            const auto* offsets=reinterpret_cast<const std::uint16_t*>(raw);
            __builtin_prefetch(offsets);
            // The pool base need not be referenced by this meshlet. Warm the
            // first corner actually gathered, not vertex zero of the part pool.
            emit_prefetch_span(base+offsets[0],sizeof(*base));
            raw+=2U*l.vertex_count;
        }else{
            // The transform already streams three vertices ahead. Seed only
            // its first (at most) three inputs, including a partial pick's lo.
            const unsigned first=pk.nr==0xffU?0U:pk.lo;
            const unsigned count=pk.nr==0xffU?l.vertex_count:unsigned(pk.hi-pk.lo)+1U;
            if(first>=l.vertex_count || count>l.vertex_count-first)return;
            emit_prefetch_span(base+first,(count<3U?count:3U)*sizeof(*base));
        }
        if(pk.nr==0xffU)__builtin_prefetch(raw);
        else if(sg)__builtin_prefetch(sg+16U*sg_groups*pk.let);
    }
#if RE4DC_SCENERY_RECORD_SPLIT
    template<class EmitRecord>
    const re4dc::room::CompactVertex12* emit_corners(const EmitRecord& l,const Pick& pk){
#else
    const re4dc::room::CompactVertex12* emit_corners(const RE4DC_SCENERY_RECORD& l,const Pick& pk){
#endif
        const auto* base=package.vertices()+l.first_vertex;
#if RE4DC_SCENERY_DEDUP==3
        // Match corners(): refresh or clear the decoder before every early return.
        const unsigned rep=package.repeat_count(l);
        dd_base=rep?base:nullptr;dd_unique=l.vertex_count-rep;dd_count=l.vertex_count;
#endif
        if(!package.indexed(l))return base;
        if(!pk.nr)return gathered; // bind/borrow/prime still run; no consumer for this pick
        // Keep the full gather for nonempty partial picks: the runtime R4SG
        // reader has not proved that group lo/hi encloses every clipper input,
        // and DEDUP's fill can read corners outside that interval. Hoist the
        // immutable count before may-alias stores instead of rereading it.
        const unsigned count=l.vertex_count;
        typedef std::uint32_t __attribute__((may_alias)) Word;
        const std::uint16_t* offsets=package.pool_offsets(l);
        const Word* in=reinterpret_cast<const Word*>(base);
        Word* out=reinterpret_cast<Word*>(gathered);
        for(unsigned k=0;k<count;++k,out+=3){
            const Word* c=in+3U*offsets[k];
            out[0]=c[0];out[1]=c[1];out[2]=c[2];
        }
        return gathered;
    }
    // SCENERY_EMIT_PREFETCH_MEMBERS_END
#endif
    int emit_pick(const Pick& pk){
        namespace vp=re4dc::vp;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        re4dc::wc24::Scope wc_phase(re4dc::wc24::Other);
#endif
        ++stats.groups_visible;
        if(!bind()){++stats.bind_rejects;return submitted?-1:0;}
        ++stats.batches;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        wc_phase.phase(re4dc::wc24::Transform);
#endif
        if(!borrow_gather()){++stats.reserve_rejects;return submitted?-1:0;}
        if(!borrow()){++stats.reserve_rejects;return submitted?-1:0;}
#if RE4DC_SCENERY_RECORD_SPLIT
        const auto& l=package.emit(pk.let);
#else
        const auto& l=package.meshlets()[pk.let];
#endif
#if defined(RE4DC_SCN_CENSUS) && RE4DC_SCN_CENSUS
        struct CenScope {
            const Emitter* e;unsigned n,s0,c0,o0,v0;
            ~CenScope(){
                const unsigned es=stats.strips-s0,cs=stats.strips_culled-c0;
                scn_cen[0]++;scn_cen[1]+=n;if(!es)scn_cen[2]+=n;scn_cen[3]+=es;scn_cen[4]+=cs;scn_cen[5]+=e->output-o0;
                if(!es && cs)scn_cen[6]++;
            }
        } cen{this,l.vertex_count,stats.strips,stats.strips_culled,output,0};
#endif
#if RE4DC_SCENERY_DIRECT_STRIPS
        if(pk.nr==0xffU && sequential_direct(l))return 1;
#endif
#if RE4DC_SCENERY_EMIT_PREFETCH
        const auto* base=emit_corners(l,pk);
#elif RE4DC_SCENERY_STREAM
        // SCENERY_STREAM: an indexed pick is transformed from its pool (no gather); base stays null until a strip
        // reaches the clipper (strips_lean gathers then, stream_gather()).
        const bool ix=package.indexed(l);
        stream_l=ix?&l:nullptr;
        const auto* base=ix?nullptr:corners(l);
        const auto* pool=reinterpret_cast<const vp::Vertex12*>(package.vertices()+l.first_vertex);
        const std::uint16_t* offs=ix?package.pool_offsets(l):nullptr;
#else
        const auto* base=corners(l);
#endif
        const auto* in=reinterpret_cast<const vp::Vertex12*>(base);
        if(l.vertex_count>primed){vp::prime(cache+primed,l.vertex_count-primed);primed=l.vertex_count;
            if(lean_part){lean::prime_at=cache;lean::primed=primed;}
        }
        const std::uint8_t* const sb=package.strip_begin(l);
        if(pk.nr!=0xffU){
#if defined(RE4DC_SCN_CENSUS) && RE4DC_SCN_CENSUS
            cen.n=pk.nr?pk.hi-pk.lo+1U:0U;  // corners transformed (the strip groups left)
#endif
            if(!pk.nr)return 1;
            const unsigned vn=pk.hi-pk.lo+1U;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
            re4dc::wc24::count(re4dc::wc24::Transformed,vn);
#endif
#if RE4DC_SCENERY_STREAM && !RE4DC_SCENERY_EMIT_PREFETCH
            if(ix){
                vp::transform_sched_ix(pool,offs+pk.lo,vn,cache+pk.lo,outcodes+pk.lo,k);
#if defined(RE4DC_SCENERY_STREAM_CHECK) && RE4DC_SCENERY_STREAM_CHECK
                stream_check(l,pk.lo,vn);
#endif
            }else
#endif
            vp::transform_sched<vp::kChecksAll>(in+pk.lo,vn,cache+pk.lo,outcodes+pk.lo,k);
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
            if(ps2)re4dc_wm_corners(outcodes+pk.lo,vn,0x3fU);
#endif
#if RE4DC_SCENERY_DEDUP
#if RE4DC_SCENERY_STREAM && !RE4DC_SCENERY_EMIT_PREFETCH
            if(!ix)   // the SCDD tables never cover an indexed meshlet (scdd_compile.py; the loader refuses one)
#endif
            if(const std::uint32_t dw=dd_word(l);dd_active(dw))
                dedup::fill(in,cache,outcodes,dd_unique_count(l,dw),l.vertex_count,dd_source(l,dw),k,pk.lo,pk.hi);
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
            wc_phase.phase(re4dc::wc24::Submit);
#endif
            const auto* g=reinterpret_cast<const std::uint16_t*>(sg+16U*sg_groups*pk.let);
            unsigned prev=0;
            for(unsigned q=0;q<sg_groups;++q){
                const unsigned gend=g[8*q+6];
                if(gend==prev)continue;
                if((pk.gmask>>q)&1U){
                    int result=1;
                    strips_lean(sb+prev,sb+gend,base,batch,result);
                    if(result<=0)return result;
                }
                prev=gend;
            }
            return 1;
        }
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        unsigned wc_vertices=l.vertex_count;
#if RE4DC_SCENERY_DEDUP
        if(const std::uint32_t dw=dd_word(l);dd_active(dw))wc_vertices=dd_unique_count(l,dw);
#endif
        re4dc::wc24::count(re4dc::wc24::Transformed,wc_vertices);
#endif
#if RE4DC_SCENERY_STREAM && !RE4DC_SCENERY_EMIT_PREFETCH
        if(ix){
            vp::transform_sched_ix(pool,offs,l.vertex_count,cache,outcodes,k);
#if defined(RE4DC_SCENERY_STREAM_CHECK) && RE4DC_SCENERY_STREAM_CHECK
            stream_check(l,0,l.vertex_count);
#endif
        }else
#endif
#if RE4DC_SCENERY_DEDUP
        if(const std::uint32_t dw=dd_word(l);dd_active(dw)){
            const unsigned u=dd_unique_count(l,dw);
            vp::transform_sched<vp::kChecksAll>(in,u,cache,outcodes,k);
            dedup::fill(in,cache,outcodes,u,l.vertex_count,dd_source(l,dw),k);
        }else
#endif
        vp::transform_sched<vp::kChecksAll>(in,l.vertex_count,cache,outcodes,k);
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
        if(ps2){
            unsigned count=l.vertex_count;
#if RE4DC_SCENERY_DEDUP
            if(const std::uint32_t dw=dd_word(l);dw>>24)count-=dw>>24;
#endif
            re4dc_wm_corners(outcodes,count,0x3fU);
        }
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        wc_phase.phase(re4dc::wc24::Submit);
#endif
        int result=1;
        strips_lean(sb,sb+l.strip_bytes,base,batch,result);
#if RE4DC_PS2_PVS
        if(result>0)pvs_observed(l);
#endif
        return result;
    }
#if RE4DC_SCENERY_REPLAY_LEAN
    // CHUNK_REPLAY_RESTART: a replay never calls selection/run on this object.
    // bind overwrites packet/dst/limit; borrow overwrites outcodes and all of k.
    // The gather buffer and clip setup belong to this unchanged package/pass.
    // Reset the logical part and force borrow to validate each newly bound slab.
    [[gnu::always_inline]] void chunk_restart(){
        used=input=output=slots=0;
        bound=submitted=false;
        cache=nullptr;primed=0;
#if RE4DC_PS2_PVS
        pvs_pending[0]=pvs_pending[1]=~0U;pvs_pending[2]=0;
#endif
    }
    // CHUNK_REPLAY_RESTART_END
#endif
#if RE4DC_SCENERY_EMIT_PREFETCH
    __attribute__((noinline)) int chunk_emit(const Pick* pk,unsigned n,const Pick* following=nullptr){
#else
    __attribute__((noinline)) int chunk_emit(const Pick* pk,unsigned n){
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        const re4dc::wc24::Scope wc_replay(re4dc::wc24::Other);
#endif
#if RE4DC_SCENERY_EMIT_PREFETCH
        if(n>1U)prefetch_emit_header(pk[1]);
        else if(n && following)prefetch_emit_header(*following);
#endif
#if !RE4DC_SCENERY_REPLAY_LEAN
        streaming=re4dc_model_packet_streaming()!=0;
        set_clip();
        palette=nullptr;
#endif
        batch.uv_bias[0]=part.uv_bias[0];batch.uv_bias[1]=part.uv_bias[1];
        batch.uv_scale[0]=part.uv_scale[0];batch.uv_scale[1]=part.uv_scale[1];
        for(unsigned i=0;i<n;++i){
#if RE4DC_SCENERY_EMIT_PREFETCH
            // Two selected headers ahead; one payload ahead. The current
            // transform plus its strips supplies the lead time. following is
            // the next queued part's first pick, still in this package/run.
            if(i+2U<n)prefetch_emit_header(pk[i+2U]);
            else if(i+2U==n && following)prefetch_emit_header(*following);
            if(i+1U<n)prefetch_emit_payload(pk[i+1U]);
            else if(following)prefetch_emit_payload(*following);
#elif defined(RE4DC_PREF_WALK) && RE4DC_PREF_WALK
            // PREF_WALK (cache20.h): the next pick's corners and first strip bytes while this one is transformed / sent
            if(i+1<n && RE4DC_C20_PREF_ON()){
#if RE4DC_SCENERY_RECORD_SPLIT
                const auto& nl=package.emit(pk[i+1].let);
#else
                const auto& nl=package.meshlets()[pk[i+1].let];
#endif
                RE4DC_C20_PREF(package.vertices()+nl.first_vertex);RE4DC_C20_PREF(package.strip_begin(nl));
            }
#endif
            const int r=emit_pick(pk[i]);if(r<=0)return r;}
        if(used)re4dc_model_packet_commit(used);
        re4dc_model_result(0,input,output);
        return 1;
    }
#endif
    int run(){
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        const re4dc::wc24::Scope wc_selection(re4dc::wc24::Selection);
#endif
#if RE4DC_PS2_WORLD_MESH
        // A PS2 part has no source image to reserve against; its direct bind checks the frame state.
        if(!ps2 && !re4dc_model_packet_reserve(&p,&packet)){++stats.reserve_rejects;return 0;}
#else
        if(!re4dc_model_packet_reserve(&p,&packet)){++stats.reserve_rejects;return 0;}
#endif
        streaming=re4dc_model_packet_streaming()!=0;
#if RE4DC_HW_LEAN
        set_clip();
#else
        clip={near,far,RE4DC_SCREEN_W,RE4DC_SCREEN_H,project,static_cast<Emitter*>(this)};
#endif
        palette=nullptr; // lit ARGB1555 corners (light_part)
#if RE4DC_PS2_INTERIOR_CULL
        if(pc_mode==2 && !package.lod())return 1; // the check run needs cluster tables (=1 draws a v1 part whole)
#endif
        batch.uv_bias[0]=part.uv_bias[0];batch.uv_bias[1]=part.uv_bias[1];
        batch.uv_scale[0]=part.uv_scale[0];batch.uv_scale[1]=part.uv_scale[1];
#if RE4DC_MESH_LOD
        if(package.lod()){
            const int result=draw_clusters();
            if(result<=0)return result;
        }else
#endif
        {
#if RE4DC_SCENERY_RECORD_SPLIT
            const auto lets=package.meshlets()+part.first_meshlet;
#else
            const auto* lets=package.meshlets()+part.first_meshlet;
#endif
            for(unsigned i=0;i<part.meshlet_count;++i){
                const int result=draw(lets[i]);
                if(result<=0)return result;
            }
        }
        if(used)re4dc_model_packet_commit(used);
        re4dc_model_result(0,input,output);
        return 1;
    }
};
#if RE4DC_SCENERY_CHUNK
#if RE4DC_SCENERY_SELECT_ONLY
// Selection borrows placement inputs only for this synchronous call. Replay
// still owns the existing ChunkPart snapshot and constructs its full emitter.
// The user-provided constructor deliberately leaves the lazy coefficient
// arrays uninitialized; their guards are false until chunk_select fills them.
struct ScenerySelector {
    using Pick=MeshDraw::Pick;
#if RE4DC_SCENERY_RECORD_SPLIT
    const re4dc::record_split::RecordView package;
#else
    const re4dc::room::MeshPackage& package;
#endif
    const Re4dcModelPart& p;
    const float* mvq;
    float near,cull_far,lod_scale=0;
    unsigned part_index=0;
    const float* lean_am=nullptr;
    const std::uint8_t* sg=nullptr;
    unsigned sg_groups=0;
    const unsigned* ps2=nullptr;
#if RE4DC_PS2_PVS
    const std::uint8_t* pvs_set=nullptr;
#endif
#if RE4DC_PS2_INTERIOR_CULL
    unsigned pc_mode=0;
#endif
#if RE4DC_QUALITY_ASSETS
    std::uint64_t skip_clusters=0;
#endif
    bool lean_inside=false,sg_coef_ok=false;
    float sg_coef[40] __attribute__((aligned(8)));
#if RE4DC_SG_SELECT_LEAN
    bool sg_lp_ok=false;
    lean::SgPlane sg_lp[5];
#endif
#if RE4DC_SCENERY_RECORD_SPLIT
    ScenerySelector(const Re4dcModelPart& source,re4dc::record_split::RecordView mesh,
#else
    ScenerySelector(const Re4dcModelPart& source,const re4dc::room::MeshPackage& mesh,
#endif
                    const float* matrix,float clip_near,float reject_far)
        :package(mesh),p(source),mvq(matrix),near(clip_near),cull_far(reject_far){}
#include "include/scenery_chunk_select.inc"
};
#endif
#pragma GCC pop_options
#endif
#endif
} // namespace

extern "C" void re4dc_static_bind(const void* object,unsigned room,int block,unsigned work,
                                  unsigned bin,unsigned common,unsigned serial,const float world[12]){
#if RE4DC_NATIVE_MESH
    (void)work;(void)serial;(void)world;
    bind_mesh(object,room,block,bin,common);
#elif RE4DC_NATIVE_STATIC
    const unsigned index=view_index(block);
    if(index>=kViews || !(RE4DC_NATIVE_STATIC_OWNERS&(1U<<index))){
        ++stats.unowned_binds;
        if(stats.unowned_binds<=48)re4dc_log("native static: unowned bind block=%d work=%u bin=%u common=%u object=%p\n",block,work,bin,common,object);
        return;
    }
    View& v=views[index];
    if(!open(v,index,room))return;
    re4dc::room::CompactSourceRange range;
    if(!v.package.resolve_source(block<0?0xffU:std::uint8_t(block),std::uint16_t(work),
                                 std::uint16_t(bin),common!=0,range)){
        ++stats.bind_misses;
        if(stats.bind_misses<=48)re4dc_log("native static: bind miss view=%u work=%u bin=%u common=%u object=%p\n",index,work,bin,common,object);
        return;
    }
    Binding& b=v.bindings[range.source];
    if(b.object && (b.object!=object || b.serial!=serial)){
        ++stats.bind_conflicts;
        if(stats.bind_conflicts<=48)re4dc_log("native static: bind conflict view=%u source=%u work=%u bin=%u common=%u object=%p previous=%p\n",
            index,range.source,work,bin,common,object,b.object);
    }
    b={object,serial,~0U,0,0,range.first_group,range.group_count,{}};
    std::memcpy(b.world,world,sizeof(b.world));
    ++stats.binds;
#else
    (void)object;(void)room;(void)block;(void)work;(void)bin;(void)common;(void)serial;(void)world;
#endif
}

extern "C" void re4dc_static_retire_owner(int block){
#if RE4DC_PS2_WORLD_DRAW
    if(block==-1)re4dc_ps2_world_retire();
#endif
    const unsigned index=view_index(block);
    if(index<kViews && views[index].attempted)retire(views[index]);
#if RE4DC_NATIVE_MESH
    if(index<kViews && mesh_views[index].attempted)retire(mesh_views[index]);
#endif
}
extern "C" void re4dc_static_retire_all(){
#if RE4DC_PS2_WORLD_DRAW
    re4dc_ps2_world_retire();
#endif
    for(auto& v:views)if(v.attempted)retire(v);
#if RE4DC_NATIVE_MESH
    for(auto& v:mesh_views)if(v.attempted)retire(v);
#endif
#if RE4DC_NO_STD_ANY
    if(no_std.room!=~0U){no_std_log("leave");no_std=NoStd();}
#endif
}
extern "C" const Re4dcStaticStats* re4dc_static_stats(){return &stats;}
#if RE4DC_GC_ASSET_GATE
extern "C" void re4dc_gcasset_room_parent_retire(){gcasset_static_invalidate_all();}
#endif
#if RE4DC_NO_STD_ANY
// coarse.cpp re4dc_coarse_tick(), once per Trans(): 1 when this tick's image (drawn by the next Render()) is coarse.
extern "C" void re4dc_std_scenery_tick(int coarse){
    no_std.coarse=coarse;
    if(no_std.room!=~0U && ++no_std.ticks%1200U==0)no_std_log("census");
}
#endif
#if RE4DC_QUALITY_ASSETS
// ui_bridge.cpp re4dc_room_enter(): after the quality freeze, before any package
// of the room opens. Original never reads the index (nor low/ or texlow/).
extern "C" void re4dc_std_room_enter(unsigned room){
    StdRoom& r=std_room;
#if RE4DC_GC_ASSET_GATE
    gcasset_static_invalidate_all();re4dc_gcasset::payload_retire(r.asset_proof);
#endif
    r.room=room;r.active=false;r.mesh_views=0;r.checked=0;r.ntex=r.ndrop=r.ncull=r.nimp=r.nptex=r.nimpt=0;
#if RE4DC_GC_ASSET_GATE
    r.gca_unused=0;
#endif
    if(!re4dc_quality_std_assets())return;
    char path[64];snprintf(path,sizeof(path),"/cd/dc/native/r%x%02x/low/index.txt",room>>8,room&255U);
    char* text=static_cast<char*>(std::malloc(kStdText));
    const int n=text?re4dc_fixture_read(path,text,kStdText):-1;
#if RE4DC_GC_ASSET_GATE
    r.gca_unused=n<=0?1:2;   // cleared once the index is accepted below
#endif
    if(n<=0){re4dc_log("quality assets: %s missing: Original packages\n",path);std::free(text);return;}
    if(n>=int(kStdText)){re4dc_log("quality assets: %s larger than %u B: Original packages\n",path,kStdText);std::free(text);return;}
#if RE4DC_GC_ASSET_GATE
    // fixture_read is one bounded read: receipt its exact n-byte consumed span,
    // never claim a full file or hash the tokenized/freed buffer later.
    const auto gcasset_digest=re4dc_gcasset::fingerprint(text,unsigned(n));
#endif
    text[n]=0;
    r.active=std_parse(text,room);
    std::free(text);
    if(!r.active){r.mesh_views=0;r.ntex=r.ndrop=r.ncull=r.nimp=r.nptex=r.nimpt=0;re4dc_log("quality assets: %s rejected: Original packages\n",path);return;}
#if RE4DC_GC_ASSET_GATE
    r.gca_unused=0;
    re4dc_gcasset::payload_capture_receipt(r.asset_proof,&r,gcasset_digest,unsigned(n));
#endif
    re4dc_log("quality assets: %s mesh=%02x tex=%u drop=%u cull=%u imp=%u impt=%u ptex=%u\n",path,r.mesh_views,r.ntex,r.ndrop,r.ncull,r.nimp,r.nimpt,r.nptex);
}
// native_ui.cpp: texture keys Standard adds (texlow/), and the room keys it drops.
extern "C" int re4dc_std_texlow(unsigned crc,unsigned fnv){
    const StdRoom& r=std_room;if(!r.active)return 0;
    for(unsigned i=0;i<r.ntex;++i)if(r.tex[i].crc==crc && r.tex[i].fnv==fnv)return 1;
    return 0;
}
extern "C" int re4dc_std_dropped(unsigned crc,unsigned fnv){
    const StdRoom& r=std_room;if(!r.active)return 0;
    for(unsigned i=0;i<r.ndrop;++i)if(r.drop[i].crc==crc && r.drop[i].fnv==fnv)return 1;
    return 0;
}
// i-th added texture: key, size and VRAM bytes; 0 past the end.
extern "C" int re4dc_std_texture(unsigned i,unsigned out[5]){
    const StdRoom& r=std_room;if(!r.active || i>=r.ntex)return 0;
    const StdTex& t=r.tex[i];out[0]=t.crc;out[1]=t.fnv;out[2]=t.width;out[3]=t.height;out[4]=t.vram;return 1;
}
#endif
#if RE4DC_TREE_IMPOSTOR
// native_ui re4dc_model_finish_source_draws(): after the OP pass, before the
// translucent drain. One PT packet per (atlas, fog) with each quad as a
// 4-corner strip; a later impostor candidate this frame draws geometry.
extern "C" void re4dc_static_flush_impostors(){
    const unsigned frame=re4dc_ui_frame();
    if(impostor_flushed==frame)return;
    impostor_flushed=frame;
    if(impostor_frame!=frame)return;
    for(unsigned i=0;i<impostor_count;++i){
        const auto* first=impostor_queue[i].record;
        if(!first)continue;
        const unsigned fog=impostor_queue[i].fog;
        Re4dcModelPacket packet{};
        const bool bound=re4dc_model_pt_begin(first->key_crc,first->key_fnv,first->atlas_w,first->atlas_h,int(fog),&packet)!=0;
        auto* out=static_cast<pvr_vertex_t*>(packet.vertices);unsigned used=0;
#if RE4DC_GC_ASSET_GATE
        re4dc_gcasset::PayloadQuadUse accepted[kImpostorQuads];unsigned accepted_count=0;
#endif
        for(unsigned j=i;j<impostor_count;++j){
            ImpostorQuad& q=impostor_queue[j];
            const auto* r=q.record;
            if(!r || r->key_crc!=first->key_crc || r->key_fnv!=first->key_fnv || q.fog!=fog)continue;
            q.record=nullptr;
            if(!bound || used+4>packet.capacity)continue;
            const unsigned col=q.cell%r->cols,row=q.cell/r->cols;
            const float iw=1.0f/float(r->atlas_w),ih=1.0f/float(r->atlas_h); // half-texel inset: no neighbour bleed
            const float u0=(float(col*r->cell_w)+0.5f)*iw,u1=(float((col+1)*r->cell_w)-0.5f)*iw;
            const float v0=(float(row*r->cell_h)+0.5f)*ih,v1=(float((row+1)*r->cell_h)-0.5f)*ih;
            for(unsigned k=0;k<4;++k){
                pvr_vertex_t& o=out[used+k];
                o.flags=k==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;
                o.x=q.s[k][0];o.y=q.s[k][1];o.z=q.s[k][2];
                o.u=(k&1)?u1:u0;o.v=(k&2)?v1:v0;o.argb=q.argb;o.oargb=0;
            }
#if RE4DC_GC_ASSET_GATE
            accepted[accepted_count++]=q.source;
#endif
            used+=4;
        }
        if(bound){
#if RE4DC_GC_ASSET_GATE
            const re4dc_gcasset::PayloadQuadBatch batch{accepted,accepted_count,out,used};
            re4dc_gcasset::PayloadQuadScope selected(batch);
#endif
            re4dc_model_packet_commit(used);++impostor_stats[3];}
    }
    impostor_count=0;
}
#endif
#if RE4DC_FRONT_LEAN
// 1 when 'object' is bound to a native mesh whose source identity matches
// (vertices, display lists) and every part of it is already lit (light_part
// ran): the mesh then never reads source lighting again (trans.cpp).
extern "C" int re4dc_static_mesh_lit(const void* object,unsigned vertices,unsigned parts){
#if RE4DC_NATIVE_MESH
#if RE4DC_NO_STD_ANY
    no_std_read(1,nullptr);
#endif
    if(!stats.owners_open)return 0;
    unsigned owner=0;
    const MeshEntry* e=find_entry(object,owner);
    if(!e)return 0;
    const MeshView& v=e->common?mesh_views[kCommonView]:mesh_views[owner];
    if(!v.package.valid() || e->mesh>=v.package.header().mesh_count)return 0;
    const auto& mesh=v.package.meshes()[e->mesh];
    if(!v.package.source_identity(e->mesh,vertices,parts) || !mesh.part_count)return 0;
    const auto* list=v.package.parts()+mesh.first_part;
    for(unsigned i=0;i<mesh.part_count;++i)if(!list[i].reserved)return 0;
    return 1;
#else
    (void)object;(void)vertices;(void)parts;return 0;
#endif
}
#endif

#ifndef RE4DC_SCENERY_GATE
#define RE4DC_SCENERY_GATE 0 // obj/scenery30.h (D367 scenery30 S1a)
#endif
#if RE4DC_SCENERY_GATE
namespace { unsigned gate_tests,gate_culled,gate_frame_log=~0U; }
extern "C" float re4dc_fog_far_for_gate(float zfar);
// S1a: 1 when the whole native mesh bound to 'object' lies beyond the depth at which
// mesh_submit's MeshDraw rejects every cluster (cull_far: the projection far, or the fogged
// source View far when fog is on). The mesh's grid box (origin .. origin + 65535 step) contains
// every cluster box, so each cluster would have failed the same depth test: the caller may
// skip the model's render setup with identical pixels.
extern "C" int re4dc_static_gate(const void* object,const float mv[12],const float projection[7],float zfar){
#if RE4DC_NATIVE_MESH
#if RE4DC_NO_STD_ANY
    no_std_read(2,nullptr);
#endif
    if(!stats.owners_open)return 0;
    unsigned owner=0;
    const MeshEntry* e=find_entry(object,owner);
    if(!e)return 0;
    const MeshView& v=e->common?mesh_views[kCommonView]:mesh_views[owner];
    if(!v.package.valid() || e->mesh>=v.package.header().mesh_count)return 0;
    if(projection[0]!=0)return 0;
    const float near=projection[6]/(projection[5]-1),far=projection[6]/projection[5];
    if(!re4dc::render::is_finite(near)||!re4dc::render::is_finite(far)||near<=0||far<=near)return 0;
    float cull_far=far;
#if RE4DC_NATIVE_FOG
    if(re4dc_fog_enabled()){const float view_far=re4dc_fog_far_for_gate(zfar);if(view_far>near && view_far<far)cull_far=view_far;}
#else
    (void)zfar;
#endif
    const auto& mesh=v.package.meshes()[e->mesh];
    float vz=mv[11],rz=0;
    for(unsigned a=0;a<3;++a){
        const float extent=mesh.step[a]*(65535.0f*0.5f),center=mesh.origin[a]+extent;
        vz+=mv[8+a]*center;rz+=std::fabs(mv[8+a])*extent;
    }
    ++gate_tests;
    const unsigned frame=re4dc_ui_frame();
    if(frame%600==0 && frame!=gate_frame_log){gate_frame_log=frame;re4dc_log("native scenery gate: frame=%u tests=%u culled=%u\n",frame,gate_tests,gate_culled);}
    if(-vz-rz>cull_far){++gate_culled;return 1;}
    return 0;
#else
    (void)object;(void)mv;(void)projection;(void)zfar;return 0;
#endif
}
#endif
#if RE4DC_NATIVE_FOG
#if defined(RE4DC_VIEW_DIST_OPTION) && RE4DC_VIEW_DIST_OPTION
extern "C" float re4dc_view_far(float far);   // option_rows.cpp: the Options View distance far plane
extern "C" float re4dc_view_indoor_depth(void);   // option_rows.cpp: the indoor area's farthest point from the eye, or 0
#endif
#if RE4DC_FAR_SHELL
extern "C" int re4dc_far_shell_keeps_fog(void);       // far_shell.inc
extern "C" void re4dc_far_shell_note_far(float far);
#endif
namespace {
// Last GXSetFog state (gx_stub.cpp) and the source View far plane seen by the
// model bridge. Temporary type-0 calls (effects, filters, thermal/black) reach
// parts as fog off through Re4dcModelPart::source_key[2]; the table keeps the last
// fogged state and is rewritten only when that state changes.
struct FogState { int type; float start,end,far; unsigned rgba; };
FogState fog_now{0,0,0,0,0},fog_loaded{-1,0,0,0,0};
constexpr float kFogRamp=0.8f; // ramp to 100% over the last 20% before the far plane
#if defined(RE4DC_VIEW_DIST_OPTION) && RE4DC_VIEW_DIST_OPTION
// VIEW_DIST_OPTION (option_rows.cpp, Options View distance; render only): re4dc_fog_note_far moves the fogged far in
// to Near / Short (18.75 / 12.5 m). Then the ramp to 100 % keeps Full's width, 20 % of 25 m = 5 m before the cut
// (never more than half the far), so distant scenery fades out over the same depth instead of popping.
bool fog_view_cut;
// Indoors (option_rows.cpp re4dc_view_indoor_depth: the player in one of the room's indoor effect areas) the ramp
// starts behind that area instead (its farthest point from the eye + 0.5 m, at most 2 m before the cut), so the room
// around the player keeps Full's look while scenery seen through doors and windows still fades out before the cut.
// The start moves 0.5 m per frame toward its target (no jump in the fog when stepping through a door); 0 = not indoors.
float fog_indoor_start,fog_indoor_loaded=-1.0f;
float fog_ramp_base(float far){
    const float s=far-(1.0f-kFogRamp)*25000.0f;
    return s>0.5f*far?s:0.5f*far;
}
float fog_ramp_start(float far){
    if(!fog_view_cut)return kFogRamp*far;
    const float s=fog_ramp_base(far);
    return fog_indoor_start>s?fog_indoor_start:s;
}
float fog_ramp(float z,float far){const float s=fog_ramp_start(far);return (z-s)/(far-s);}
#endif
// 2^x for x in [-8, 0] without libm (powf alone is ~2 KB of image): halve
// per whole step, then e^y on y=frac*ln2 in (-0.7, 0] (Taylor, error < 2e-4,
// far below the table's 8-bit alpha).
float fog_exp2(float x){
    float r=1.0f;
    while(x<=-1.0f){r*=0.5f;x+=1.0f;}
    const float y=x*0.69314718f;
    return r*(1.0f+y*(1.0f+y*(0.5f+y*(1.0f/6.0f+y*(1.0f/24.0f+y*(1.0f/120.0f))))));
}
// GX fog amount at eye depth z (GXSetFog: perspective and orthographic
// variants share the curve on t=(z-start)/(end-start)).
float gx_fog(int type,float start,float end,float z){
    if(!(end>start))return z>=end?1.0f:0.0f;
    float t=(z-start)/(end-start);
    t=t<0?0.0f:t>1?1.0f:t;
    switch(type&7){
    case 4: return 1.0f-fog_exp2(-8.0f*t);
    case 5: return 1.0f-fog_exp2(-8.0f*t*t);
    case 6: return fog_exp2(-8.0f*(1.0f-t));
    case 7: return fog_exp2(-8.0f*(1.0f-t)*(1.0f-t));
    default: return t;
    }
}
}
extern "C" void re4dc_fog_capture(int type,float start,float end,unsigned rgba){
    fog_now.type=type;fog_now.start=start;fog_now.end=end;fog_now.rgba=rgba;
}
extern "C" unsigned re4dc_fog_enabled(){return fog_now.type!=0;}
#if defined(RE4DC_WATER45_NATIVE) && RE4DC_WATER45_NATIVE
// WATER45_NATIVE (espgen45.cpp): the fog amount re4dc_fog_frame's table gives eye depth z (GX curve + far ramp).
// The table this frame's PVR fog holds (fog_loaded): effects switch the source fog off around their own draws.
extern "C" float re4dc_fog_amount(float z){
    if(fog_loaded.type<=0)return 0.0f;
    const float far=fog_loaded.far>1.0f?fog_loaded.far:(fog_loaded.end>1.0f?fog_loaded.end:1.0f);
    float f=gx_fog(fog_loaded.type,fog_loaded.start,fog_loaded.end,z);
#if defined(RE4DC_VIEW_DIST_OPTION) && RE4DC_VIEW_DIST_OPTION
    const float ramp=fog_ramp(z,far);
#else
    const float ramp=(z-kFogRamp*far)/((1.0f-kFogRamp)*far);
#endif
#if RE4DC_LOOK_ANY
    if(ramp>0){
        const unsigned curve=re4dc_look_curve();const float cap=float(re4dc_look_cap())/100.0f;
        const float s=ramp>=1?1.0f:ramp*ramp*(3.0f-2.0f*ramp);
        if(!curve)f+=(1.0f-f)*s;
        else if(curve==2 && f<cap*s)f=cap*s;
    }
#else
    if(ramp>0){const float s=ramp>=1?1.0f:ramp*ramp*(3.0f-2.0f*ramp);f+=(1.0f-f)*s;}
#endif
    return f;
}
#endif
#if RE4DC_ACTOR_FOG_GATE
// ACTOR_FOG_GATE: the fogged source View far last noted (re4dc_fog_note_far, already clamped to
// FOG_FAR), the value re4dc_fog_far_for_gate gives SCENERY_GATE for the same View; 0 when unknown.
extern "C" float re4dc_fog_gate_far(){return fog_now.type?fog_now.far:0.0f;}
#endif
#if RE4DC_SCENERY_GATE
extern "C" float re4dc_fog_far_for_gate(float far){ // re4dc_fog_note_far's clamp, without noting
#if RE4DC_FOG_FAR > 0
#if defined(RE4DC_LAKE_FAR_ON)
    {const float cap=re4dc_far_cap(float(RE4DC_FOG_FAR));if(!(far<=cap))far=cap;}
#else
    if(!(far<=float(RE4DC_FOG_FAR)))far=float(RE4DC_FOG_FAR);
#endif
#endif
#if defined(RE4DC_VIEW_DIST_OPTION) && RE4DC_VIEW_DIST_OPTION
#if RE4DC_FAR_SHELL
    if(!re4dc_far_shell_keeps_fog())   // FAR_SHELL: Full's fog (and its gates) while the shell replaces the far world
#endif
    far=re4dc_view_far(far);
#endif
    return far;
}
#endif
extern "C" void re4dc_fog_note_far(float far){
#if RE4DC_FOG_FAR > 0
#if defined(RE4DC_LAKE_FAR_ON)
    {const float cap=re4dc_far_cap(float(RE4DC_FOG_FAR));if(!(far<=cap))far=cap;}
#else
    if(!(far<=float(RE4DC_FOG_FAR)))far=float(RE4DC_FOG_FAR);
#endif
#endif
#if defined(RE4DC_VIEW_DIST_OPTION) && RE4DC_VIEW_DIST_OPTION
#if RE4DC_FAR_SHELL
    re4dc_far_shell_note_far(far);
    if(re4dc_far_shell_keeps_fog())fog_view_cut=false;else
#endif
    {const float v=re4dc_view_far(far);fog_view_cut=v<far;far=v;}   // Options View distance (render only)
#endif
    fog_now.far=far;
}
#if defined(RE4DC_VIEW_DIST_OPTION) && RE4DC_VIEW_DIST_OPTION
// The indoor ramp start for this frame (see fog_indoor_start): one 0.5 m step toward the target, 0 once back at the
// level's own ramp start.
static float fog_indoor_next(){
    const float far=fog_now.far,base=fog_ramp_base(far);
    float t=base;
    if(fog_view_cut && fog_now.type){
        const float d=re4dc_view_indoor_depth();
        if(d>0.0f){t=d+500.0f;const float lim=far-2000.0f;if(t>lim)t=lim;if(t<base)t=base;}
    }
    float c=fog_indoor_start>base?fog_indoor_start:base;
    if(t>c){c+=500.0f;if(c>t)c=t;}else if(t<c){c-=500.0f;if(c<t)c=t;}
    return c>base?c:0.0f;
}
#endif
#if defined(RE4DC_EFFECT_HAZE_LEAN) && (RE4DC_EFFECT_HAZE_LEAN & 2)
// EFFECT_HAZE_LEAN bit 2 (STUDY2 M3): the fog table carries about 55 % of the PS2 haze's mean veil, which ramps in
// from 1 to 5 m (Monte Carlo of the PS2 haze), so the sparse haze subset only adds the drifting blotches.
// re4dc_haze_key (esp_sub.cpp): (fade step 0..8 << 4) | room (1 r100, 2 r101, 3 r103), 0 without haze.
extern "C" unsigned re4dc_haze_key(void);
namespace {
unsigned haze_loaded=~0U;
float haze_veil(unsigned key,float z){
    static const float kB[4]={0.0f,0.034f,0.025f,0.035f};
    static const float kz[7]={500.0f,1000.0f,1500.0f,2000.0f,3000.0f,4000.0f,5000.0f};
    static const float ks[7]={0.0f,0.04f,0.09f,0.20f,0.47f,0.87f,1.0f};
    const unsigned room=key&15U,step=key>>4;
    if(!room || room>3 || !step)return 0.0f;
    float s=1.0f;
    if(z<=kz[0])s=0.0f;
    else for(unsigned i=1;i<7;++i)if(z<kz[i]){s=ks[i-1]+(ks[i]-ks[i-1])*(z-kz[i-1])/(kz[i]-kz[i-1]);break;}
    return kB[room]*s*float(step)/8.0f;
}
void haze_table(float* table,float tfar,unsigned key){
    for(unsigned j=0;j<129;++j){
        const float v=j<128?float((j&15U)+16U)/16.0f*float(1U<<(j>>4)):256.0f;
        table[j]=1.0f-(1.0f-table[j])*(1.0f-haze_veil(key,tfar/v));
    }
}
}
#endif
#if defined(RE4DC_HW_FOG_HAZE) && RE4DC_HW_FOG_HAZE
// HW_FOG_HAZE (hwfog.mk, game/hwfog.cpp): the distant camera haze as fog; the key is (FX_LEVEL << 12) | (indoor step << 8) | row.
extern "C" unsigned re4dc_hwfog_key(void);
extern "C" void re4dc_hwfog_table(float* table,float tfar,unsigned key);
namespace { unsigned hwfog_loaded=~0U; }
#endif
#if RE4DC_FOG_TA_DOUBLEBUF
// With a double-buffered TA the previous scene may still render at frame start and reads the fog
// registers: native_ui fences only when this frame changes them.
extern "C" int re4dc_fog_frame_pending(){
#if defined(RE4DC_EFFECT_HAZE_LEAN) && (RE4DC_EFFECT_HAZE_LEAN & 2)
    if(fog_now.type && re4dc_haze_key()!=haze_loaded)return 1;
#endif
#if defined(RE4DC_HW_FOG_HAZE) && RE4DC_HW_FOG_HAZE
    if(fog_now.type && re4dc_hwfog_key()!=hwfog_loaded)return 1;
#endif
#if defined(RE4DC_VIEW_DIST_OPTION) && RE4DC_VIEW_DIST_OPTION
    if(fog_now.type && fog_indoor_next()!=fog_indoor_loaded)return 1;
#endif
    return fog_now.type && !(fog_now.type==fog_loaded.type && fog_now.start==fog_loaded.start &&
        fog_now.end==fog_loaded.end && fog_now.far==fog_loaded.far && fog_now.rgba==fog_loaded.rgba);
}
#endif
// Frame start (native_ui re4dc_ui_begin, after the previous render's fence):
// PVR table fog indexes scaled 1/w, entry j <-> depth far/v(j) with
// v(j)=2^(j>>4)*((j&15)+16)/16 (KOS pvr_fog.c), entry 0 at the far plane.
#if defined(RE4DC_SS_BG_BLACK) && RE4DC_SS_BG_BLACK
// SS_BG_BLACK (subscreen.mk): while the sub screen hides the room the background is black, as the
// GameCube's black copy clear shows it; the fog colour comes back with the room.
extern "C" int re4dc_ss_scene_hidden(void); // sscrn_bridge.cpp
static int ss_bg_hidden;
static float ss_bg_rgb[3];
static int ss_bg_rgb_set;
#endif
#if defined(RE4DC_TRANS_POLICY)
// TRANS_POLICY FAR: a copy of the PVR fog table this frame loaded (entry j <-> eye depth tfar/v(j)), so ps2_pass can
// turn "fog amount >= threshold" into a depth with the room's real fog (curve, far ramp, hwfog veil, haze).
namespace { float trans_fog_table[129]; float trans_fog_tfar; }
#endif
extern "C" void re4dc_fog_frame(){
#if defined(RE4DC_SS_BG_BLACK) && RE4DC_SS_BG_BLACK
    {const int hidden=re4dc_ss_scene_hidden();
     if(hidden!=ss_bg_hidden){
        ss_bg_hidden=hidden;
        re4dc_log("ss bg: %s (scene %s) colour=%s%02x%02x%02x\n",RE4DC_SS_BG_BLACK==1?"set":"diag",
            hidden?"hidden":"shown",hidden?"black was ":"",unsigned(ss_bg_rgb[0]*255.0f),unsigned(ss_bg_rgb[1]*255.0f),
            unsigned(ss_bg_rgb[2]*255.0f));
#if RE4DC_SS_BG_BLACK==1
        if(hidden)pvr_set_bg_color(0,0,0);
        else if(ss_bg_rgb_set)pvr_set_bg_color(ss_bg_rgb[0],ss_bg_rgb[1],ss_bg_rgb[2]);
#endif
     }}
#endif
#if defined(RE4DC_FOG_OFF_CLEAR) && RE4DC_FOG_OFF_CLEAR
    // FOG_OFF_CLEAR (castle lane 2026-10-15): until the first fog-on frame nothing loads a PVR fog table, but table-fog
    // draws (actor packets whose material asks for fog) still read it: after a boot or warp straight into a fog-off
    // room that is KOS's start-up table (the castle rooms: Leon drawn flat grey). Load an all-clear table once, only
    // while no table was ever loaded (fog_loaded.type -1); the source turns fog off around later draws of fog rooms,
    // so a fog-off frame after a load must keep the loaded table.
    if(!fog_now.type && fog_loaded.type==-1){
        static int cleared;
        if(!cleared){
            float clear[129];
            for(unsigned j=0;j<129;++j)clear[j]=0.0f;
            pvr_fog_table_custom(clear);
            cleared=1;
            re4dc_log("native fog: off since boot, table cleared\n");
        }
        return;
    }
#endif
#if RE4DC_LOOK_ANY
#if defined(RE4DC_LOOK_TOGGLE)
    re4dc_look_grade_rgb_now=(fog_now.type && (fog_now.rgba>>8)==0x8d8775U && fog_now.start<1000.0f)?0xffdee3d7U:0U;
#endif
    if(!fog_now.type)return;
    // Look knobs (post30.mk, look study 2026-10-10): FOG_CURVE / FOG_CAP / FOG_RGB_PCT, or LOOK_TOGGLE's preset.
    const unsigned curve=re4dc_look_curve(),rgb_pct=re4dc_look_rgb_pct();const float cap=float(re4dc_look_cap())/100.0f;
    static unsigned look_loaded=~0U;
    const unsigned look_key=curve|rgb_pct<<4|unsigned(re4dc_look_cap())<<12;
#if defined(RE4DC_HW_FOG_HAZE) && RE4DC_HW_FOG_HAZE
    const unsigned hwfog_key=re4dc_hwfog_key();
#endif
#if defined(RE4DC_VIEW_DIST_OPTION) && RE4DC_VIEW_DIST_OPTION
    fog_indoor_start=fog_indoor_next();
#endif
#if defined(RE4DC_EFFECT_HAZE_LEAN) && (RE4DC_EFFECT_HAZE_LEAN & 2)
    const unsigned haze_key=re4dc_haze_key();
    if(haze_key==haze_loaded &&
#else
    if(
#endif
#if defined(RE4DC_HW_FOG_HAZE) && RE4DC_HW_FOG_HAZE
       hwfog_key==hwfog_loaded &&
#endif
#if defined(RE4DC_VIEW_DIST_OPTION) && RE4DC_VIEW_DIST_OPTION
       fog_indoor_start==fog_indoor_loaded &&
#endif
       look_key==look_loaded && fog_now.type==fog_loaded.type && fog_now.start==fog_loaded.start &&
       fog_now.end==fog_loaded.end && fog_now.far==fog_loaded.far && fog_now.rgba==fog_loaded.rgba)return;
#if defined(RE4DC_EFFECT_HAZE_LEAN) && (RE4DC_EFFECT_HAZE_LEAN & 2)
    haze_loaded=haze_key;
#endif
#if defined(RE4DC_HW_FOG_HAZE) && RE4DC_HW_FOG_HAZE
    hwfog_loaded=hwfog_key;
#endif
#if defined(RE4DC_VIEW_DIST_OPTION) && RE4DC_VIEW_DIST_OPTION
    if(fog_indoor_start!=fog_indoor_loaded && (fog_indoor_start==0.0f || fog_indoor_loaded<=0.0f))
        re4dc_log("view distance: indoor fog %s (ramp start %u mm, far %u)\n",fog_indoor_start>0.0f?"on":"off",
                  unsigned(fog_indoor_start),unsigned(fog_now.far));
    fog_indoor_loaded=fog_indoor_start;
#endif
    look_loaded=look_key;
    fog_loaded=fog_now;
    const float far=fog_now.far>1.0f?fog_now.far:(fog_now.end>1.0f?fog_now.end:1.0f);
    const float rgb_k=float(rgb_pct)/100.0f; // FOG_RGB_PCT: the fog colour, and so the background, scaled down
    const float r=float((fog_now.rgba>>24)&255U)/255.0f*rgb_k,g=float((fog_now.rgba>>16)&255U)/255.0f*rgb_k,
                b=float((fog_now.rgba>>8)&255U)/255.0f*rgb_k;
    float table[129];
    // FOG_CURVE: the table spans the source fog curve out to its end (the GameCube's GXSetFog), not the cull far;
    // =2 adds a ramp to FOG_CAP % at the cull far. 0: the 100 % ramp over the last 20 % before the cull far.
    const float tfar=curve && fog_now.end>far?fog_now.end:far;
    for(unsigned j=0;j<129;++j){
        const float v=j<128?float((j&15U)+16U)/16.0f*float(1U<<(j>>4)):256.0f;
        const float z=tfar/v;
        float f=gx_fog(fog_now.type,fog_now.start,fog_now.end,z);
#if defined(RE4DC_VIEW_DIST_OPTION) && RE4DC_VIEW_DIST_OPTION
        const float ramp=fog_ramp(z,far);
#else
        const float ramp=(z-kFogRamp*far)/((1.0f-kFogRamp)*far);
#endif
        if(ramp>0){
            const float s=ramp>=1?1.0f:ramp*ramp*(3.0f-2.0f*ramp);
            if(!curve)f+=(1.0f-f)*s;
            else if(curve==2 && f<cap*s)f=cap*s;
        }
        table[j]=f;
    }
#if defined(RE4DC_EFFECT_HAZE_LEAN) && (RE4DC_EFFECT_HAZE_LEAN & 2)
    haze_table(table,tfar,haze_key);
#endif
#if defined(RE4DC_HW_FOG_HAZE) && RE4DC_HW_FOG_HAZE
    re4dc_hwfog_table(table,tfar,hwfog_key);
#endif
    pvr_fog_table_color(1.0f,r,g,b);
    pvr_fog_far_depth(tfar);
    pvr_fog_table_custom(table);
#if defined(RE4DC_TRANS_POLICY)
    std::memcpy(trans_fog_table,table,sizeof(table));trans_fog_tfar=tfar;
#endif
#else
    if(!fog_now.type)return;
#if defined(RE4DC_HW_FOG_HAZE) && RE4DC_HW_FOG_HAZE
    const unsigned hwfog_key=re4dc_hwfog_key();
#endif
#if defined(RE4DC_VIEW_DIST_OPTION) && RE4DC_VIEW_DIST_OPTION
    fog_indoor_start=fog_indoor_next();
#endif
#if defined(RE4DC_EFFECT_HAZE_LEAN) && (RE4DC_EFFECT_HAZE_LEAN & 2)
    const unsigned haze_key=re4dc_haze_key();
    if(haze_key==haze_loaded &&
#else
    if(
#endif
#if defined(RE4DC_HW_FOG_HAZE) && RE4DC_HW_FOG_HAZE
       hwfog_key==hwfog_loaded &&
#endif
#if defined(RE4DC_VIEW_DIST_OPTION) && RE4DC_VIEW_DIST_OPTION
       fog_indoor_start==fog_indoor_loaded &&
#endif
       fog_now.type==fog_loaded.type && fog_now.start==fog_loaded.start && fog_now.end==fog_loaded.end &&
       fog_now.far==fog_loaded.far && fog_now.rgba==fog_loaded.rgba)return;
#if defined(RE4DC_EFFECT_HAZE_LEAN) && (RE4DC_EFFECT_HAZE_LEAN & 2)
    haze_loaded=haze_key;
#endif
#if defined(RE4DC_HW_FOG_HAZE) && RE4DC_HW_FOG_HAZE
    hwfog_loaded=hwfog_key;
#endif
#if defined(RE4DC_VIEW_DIST_OPTION) && RE4DC_VIEW_DIST_OPTION
    fog_indoor_loaded=fog_indoor_start;
#endif
    fog_loaded=fog_now;
    const float far=fog_now.far>1.0f?fog_now.far:(fog_now.end>1.0f?fog_now.end:1.0f);
    const float r=float((fog_now.rgba>>24)&255U)/255.0f,g=float((fog_now.rgba>>16)&255U)/255.0f,
                b=float((fog_now.rgba>>8)&255U)/255.0f;
    float table[129];
    for(unsigned j=0;j<129;++j){
        const float v=j<128?float((j&15U)+16U)/16.0f*float(1U<<(j>>4)):256.0f;
        const float z=far/v;
        float f=gx_fog(fog_now.type,fog_now.start,fog_now.end,z);
#if defined(RE4DC_VIEW_DIST_OPTION) && RE4DC_VIEW_DIST_OPTION
        const float ramp=fog_ramp(z,far);
#else
        const float ramp=(z-kFogRamp*far)/((1.0f-kFogRamp)*far);
#endif
        if(ramp>0){const float s=ramp>=1?1.0f:ramp*ramp*(3.0f-2.0f*ramp);f+=(1.0f-f)*s;}
        table[j]=f;
    }
#if defined(RE4DC_EFFECT_HAZE_LEAN) && (RE4DC_EFFECT_HAZE_LEAN & 2)
    haze_table(table,far,haze_key);
#endif
#if defined(RE4DC_HW_FOG_HAZE) && RE4DC_HW_FOG_HAZE
    re4dc_hwfog_table(table,far,hwfog_key);
#endif
    pvr_fog_table_color(1.0f,r,g,b);
    pvr_fog_far_depth(far);
    pvr_fog_table_custom(table);
#if defined(RE4DC_TRANS_POLICY)
    std::memcpy(trans_fog_table,table,sizeof(table));trans_fog_tfar=far;
#endif
#endif
#if RE4DC_FOG_BACKGROUND
#if defined(RE4DC_SS_BG_BLACK) && RE4DC_SS_BG_BLACK
    ss_bg_rgb[0]=r;ss_bg_rgb[1]=g;ss_bg_rgb[2]=b;ss_bg_rgb_set=1;
#if RE4DC_SS_BG_BLACK==1
    if(!ss_bg_hidden)
#endif
#endif
    pvr_set_bg_color(r,g,b);
#endif
    re4dc_log("native fog: type=%d start=%d end=%d far=%d colour=%08x near=%u%% mid=%u%%\n",fog_now.type,
        int(fog_now.start),int(fog_now.end),int(far),fog_now.rgba,unsigned(table[128]*100.0f),unsigned(table[64]*100.0f));
}
#endif

#if RE4DC_NATIVE_STATIC
namespace {
// Lowest alpha in the source colour array; 0 when it cannot be bounded.
unsigned vertex_alpha_min(const Re4dcModelPart& p){
    if(!(p.flags&0x80000000U) || !p.colors || p.uv<=p.colors)return 0;
    const unsigned bytes=unsigned(p.uv-p.colors);
    if(bytes%4 || bytes>65536)return 0;
    unsigned low=255;
    for(unsigned i=3;i<bytes;i+=4)if(p.colors[i]<low)low=p.colors[i];
    return low;
}
void log_stats(unsigned frame){
    if(frame!=last_log_frame && frame%600==0){
        last_log_frame=frame;
        re4dc_log("native static: frame=%u native=%u skipped=%u fallback=%u key_misses=%u groups=%u/%u strips=%u culled=%u clipped=%u moved=%u stale=%u vertex_alpha=%u opaque=%u alpha_unused=%u alpha_min=%u reserve=%u bind=%u aborts=%u\n",
            frame,stats.parts_native,stats.parts_skipped,stats.parts_fallback,stats.key_misses,stats.groups_visible,
            stats.groups_visible+stats.groups_culled,stats.strips,stats.strips_culled,stats.strips_clipped,stats.moved_objects,stats.stale_bindings,
            stats.vertex_alpha,stats.vertex_opaque,stats.vertex_alpha_unused,stats.vertex_alpha_min,stats.reserve_rejects,stats.bind_rejects,stats.aborts);
        re4dc_log("native static: frame=%u vertices=%u batches=%u binds=%u misses=%u conflicts=%u unowned=%u unbound=%u lit=%u\n",
            frame,stats.vertices,stats.batches,stats.binds,stats.bind_misses,stats.bind_conflicts,stats.unowned_binds,
            stats.locate_misses,stats.parts_lit);
#if RE4DC_MESH_STRIP_LEAN==2
        re4dc_log("STRIPLEAN frame=%u meshlets=%u skipped=%u strips=%u emitted=%u vertices=%u mismatch=%u counters=%u\n",frame,
            strip_lean_stats[0],strip_lean_stats[6],strip_lean_stats[1],strip_lean_stats[2],strip_lean_stats[5],
            strip_lean_stats[3],strip_lean_stats[4]);
#endif
#if RE4DC_NATIVE_MESH && RE4DC_MESH_FASTPATH && RE4DC_MESH_VP_SCHED==2
        re4dc_log("VPSCHED frame=%u meshlets=%u vertices=%u mismatch=%u words=%u\n",frame,
            vp_sched_stats[0],vp_sched_stats[1],vp_sched_stats[2],vp_sched_stats[3]);
#endif
#if RE4DC_MESH_LOD || RE4DC_NATIVE_FOG
        re4dc_log("native static: frame=%u clusters=%u/%u lod=%u/%u/%u/%u px=%u\n",frame,stats.clusters_visible,
            stats.clusters_visible+stats.clusters_culled,stats.lod_draws[0],stats.lod_draws[1],stats.lod_draws[2],
            stats.lod_draws[3],unsigned(RE4DC_MESH_LOD_PX));
#endif
#if RE4DC_TREE_IMPOSTOR
        re4dc_log("native static: frame=%u impostors=%u parts_skipped=%u queue_full=%u batches=%u switch_mm=%u\n",frame,
            impostor_stats[0],impostor_stats[1],impostor_stats[2],impostor_stats[3],unsigned(RE4DC_TREE_IMPOSTOR_MM));
#if RE4DC_QUALITY_ASSETS
        if(std_room.active)re4dc_log("quality assets: frame=%u culled=%u imp=%u baked=%u low_opens=%u tree_quads=%u tree_geom=%u checked=%02x\n",frame,
            std_stats[0],std_stats[1],std_stats[2],std_stats[3],std_stats[4],std_stats[5],std_room.checked);
#endif
#endif
    }
}
#if RE4DC_NATIVE_MESH
// Source ModelData identity words read from the live BIN (cModelInfo::pData at
// 0x0C; nVtx 0x38, displist_num 0x1A and the relocated pParts 0x1C after the
// load-time byte-order mirror).
#if RE4DC_COPY_LEAN
// Same words as below as aligned loads (cModelInfo/ModelData are 4-aligned);
// a 2/4-byte memcpy through char* is a libcall on SH-4.
typedef const unsigned char* __attribute__((may_alias)) AliasPtr;
typedef std::uint16_t __attribute__((may_alias)) AliasHalf;
const unsigned char* model_data(const Re4dcModelPart& p){
    return *reinterpret_cast<const AliasPtr*>(static_cast<const unsigned char*>(p.info)+0x0C);
}
const unsigned char* first_part(const unsigned char* data){
    return *reinterpret_cast<const AliasPtr*>(data+0x1C);
}
#else
const unsigned char* model_data(const Re4dcModelPart& p){
    const unsigned char* data;
    std::memcpy(&data,static_cast<const unsigned char*>(p.info)+0x0C,sizeof(data));
    return data;
}
const unsigned char* first_part(const unsigned char* data){
    const unsigned char* parts;
    std::memcpy(&parts,data+0x1C,sizeof(parts));
    return parts;
}
#endif
#if RE4DC_TREE_IMPOSTOR
// atan2(y, x) in turns, [0, 1): octant reduction and a 7th-order minimax
// arctangent (error < 1e-5 rad); libm's atan2 would grow this -Os unit.
float turns(float y,float x){
    const float ax=std::fabs(x),ay=std::fabs(y),lo=ax<ay?ax:ay,hi=ax<ay?ay:ax;
    if(!(hi>0.0f))return 0.0f;
    const float a=lo/hi,s=a*a;
    float r=((-0.0464964749f*s+0.15931422f)*s-0.327622764f)*s*a+a;
    if(ay>ax)r=1.57079633f-r;
    if(x<0.0f)r=3.14159265f-r;
    r*=0.159154943f;
    return y<0.0f?1.0f-r:r;
}
// Area-weighted mean lit colour of the mesh's full-detail surface (level 0 of
// every cluster of every lit part; ARGB8888), cached in the record once every
// part is lit. The quad modulates the atlas's unlit albedo by it, as the
// geometry modulates the same texture by its per-vertex lighting.
std::uint32_t impostor_color(const MeshView& v,const re4dc::room::MeshRecord& mesh,re4dc::room::MeshImpostor& r){
    if(r.reserved)return r.reserved;
    float sum[3]={0,0,0},total=0;bool all=true;
    const auto& pk=v.package;
    for(unsigned i=mesh.first_part;i<mesh.first_part+mesh.part_count;++i){
        if(!pk.parts()[i].reserved){all=false;continue;}
        const auto& lod=pk.part_lods()[i];
        for(unsigned c=lod.first_cluster;c<lod.first_cluster+lod.cluster_count;++c){
            const auto& lv=pk.levels()[pk.clusters()[c].first_level];
            for(unsigned l=lv.first_meshlet;l<lv.first_meshlet+lv.meshlet_count;++l){
                const auto& let=pk.meshlets()[l];
                const auto* base=pk.vertices()+let.first_vertex;
                const std::uint8_t* s=pk.strips()+let.first_strip;const std::uint8_t* end=s+let.strip_bytes;
                while(s<end){
                    const unsigned n=*s++;
                    for(unsigned k=2;k<n;++k){
                        const auto &a=base[s[k-2]],&b=base[s[k-1]],&d=base[s[k]];
                        float e[2][3];
                        for(unsigned x=0;x<3;++x){
                            const float o=float((&a.x)[x]);
                            e[0][x]=(float((&b.x)[x])-o)*mesh.step[x];e[1][x]=(float((&d.x)[x])-o)*mesh.step[x];
                        }
                        const float cx=e[0][1]*e[1][2]-e[0][2]*e[1][1],cy=e[0][2]*e[1][0]-e[0][0]*e[1][2],
                                    cz=e[0][0]*e[1][1]-e[0][1]*e[1][0],area=std::sqrt(cx*cx+cy*cy+cz*cz);
                        const re4dc::room::CompactVertex12* corners[3]={&a,&b,&d};
                        for(const auto* q:corners){
                            const unsigned col=q->color;
                            sum[0]+=area*float((col>>10)&31U);sum[1]+=area*float((col>>5)&31U);sum[2]+=area*float(col&31U);
                        }
                        total+=3.0f*area;
                    }
                    s+=n;
                }
            }
        }
    }
    std::uint32_t argb=0xffffffffU;
    if(total>0){argb=0xff000000U;for(unsigned a=0;a<3;++a)argb|=unsigned(sum[a]*(255.0f/31.0f)/total+0.5f)<<(16-8*a);}
    if(all && total>0)r.reserved=argb;
    return argb;
}
// 0: draw the geometry; 1: the mesh is its impostor's (queued, or hidden
// beyond the fog/far plane or the screen). The mesh's first part decides for
// the whole object; its other parts follow that decision.
int mesh_impostor(MeshView& v,unsigned mesh_index,const re4dc::room::MeshPart& part,const Re4dcModelPart& p,
                  float near,float far){
#if RE4DC_QUALITY_ASSETS
    // Standard: the index's imp records replace the package's (s16.3), with their own switch depth.
    re4dc::room::MeshImpostor* r=nullptr;float switch_mm=float(RE4DC_TREE_IMPOSTOR_MM);
    if(std_room.active){
        const unsigned view=unsigned(&v-mesh_views);
        if((std_room.checked>>view)&1U)
            for(unsigned i=0;i<std_room.nimp;++i)if(std_room.imp[i].view==view && std_room.imp[i].rec.mesh==mesh_index){
                r=&std_room.imp[i].rec;switch_mm=std_room.imp[i].mm;break;}
    }else r=const_cast<re4dc::room::MeshImpostor*>(v.package.impostor(mesh_index));
#else
    auto* r=const_cast<re4dc::room::MeshImpostor*>(v.package.impostor(mesh_index));
#endif
    if(!r)return 0;
    const unsigned frame=re4dc_ui_frame();
    const auto& mesh=v.package.meshes()[mesh_index];
    if(&part!=v.package.parts()+mesh.first_part){
        if(impostor_frame!=frame || p.model!=impostor_object || !impostor_queued)return 0;
        ++impostor_stats[1];return 1;
    }
    if(impostor_frame!=frame){impostor_frame=frame;impostor_count=0;}
    impostor_object=p.model;impostor_queued=false;
    if(impostor_flushed==frame)return 0; // after this frame's PT batches: geometry
    const float* m=p.modelview;const float* C=r->centre;
    float c[3];
    for(unsigned i=0;i<3;++i)c[i]=m[4*i]*C[0]+m[4*i+1]*C[1]+m[4*i+2]*C[2]+m[4*i+3];
#if RE4DC_QUALITY_ASSETS
    if(!(-c[2]>=switch_mm))return 0;
    if(std_room.active)++std_stats[1];
#else
    if(!(-c[2]>=float(RE4DC_TREE_IMPOSTOR_MM)))return 0;
#endif
    const float scale=std::sqrt(m[0]*m[0]+m[1]*m[1]+m[2]*m[2]);
    if(-c[2]-(r->half_w>r->half_h?r->half_w:r->half_h)*scale>far){impostor_queued=true;return 1;} // as its clusters
    if(impostor_count>=kImpostorQuads){++impostor_stats[2];return 0;}
    // Camera direction in model space (A^T of a rotation-and-uniform-scale
    // modelview, unnormalised), its azimuth's cell, and the facing quad.
    const float dx=-(m[0]*c[0]+m[4]*c[1]+m[8]*c[2]),dz=-(m[2]*c[0]+m[6]*c[1]+m[10]*c[2]);
    const float length=std::sqrt(dx*dx+dz*dz),bx=length>0?dx/length:1.0f,bz=length>0?dz/length:0.0f;
    unsigned cell=unsigned(turns(-dz,dx)*float(r->views)+0.5f);
    if(cell>=r->views)cell-=r->views;
    ImpostorQuad& q=impostor_queue[impostor_count];
    const float* P=p.projection;const float* V=p.viewport;
    unsigned left=0,right=0,top=0,bottom=0;
    for(unsigned k=0;k<4;++k){
        const float sx=(k&1)?r->half_w:-r->half_w,sy=(k&2)?-r->half_h:r->half_h;
        const float x=C[0]+sx*bz,y=C[1]+sy,z=C[2]-sx*bx;
        const float vx=m[0]*x+m[1]*y+m[2]*z+m[3],vy=m[4]*x+m[5]*y+m[6]*z+m[7],vz=m[8]*x+m[9]*y+m[10]*z+m[11];
        if(!(-vz>near))return 0;
        const float inv=1.0f/(-vz);
        float* s=q.s[k];
        s[0]=(V[2]*.5f*(P[1]*vx+P[2]*vz)*inv+V[0]+V[2]*.5f)*RE4DC_SCREEN_WF/V[2];
        s[1]=(-V[3]*.5f*(P[3]*vy+P[4]*vz)*inv+V[1]+V[3]*.5f)*RE4DC_SCREEN_HF/V[3];
        s[2]=inv;
        left+=s[0]<0;right+=s[0]>RE4DC_SCREEN_WF;top+=s[1]<0;bottom+=s[1]>RE4DC_SCREEN_HF;
    }
    impostor_queued=true;
    if(left==4 || right==4 || top==4 || bottom==4)return 1;
    q.record=r;q.cell=std::uint16_t(cell);q.fog=p.source_key[2]?1:0;q.argb=impostor_color(v,mesh,*r);
#if RE4DC_GC_ASSET_GATE
    q.source={re4dc_gcasset::source_use.payload,re4dc_gcasset::source_use.serial,re4dc_gcasset::source_use.mask};
#endif
    ++impostor_count;++impostor_stats[0];
    return 1;
}
#endif
#if RE4DC_QUALITY_ASSETS
// s16.5: one tree of a split grove. 1: the tree is its quad (queued, or hidden
// beyond the far plane / off screen): skip its clusters. 0: draw its clusters.
int tree_quad(MeshView& v,const re4dc::room::MeshRecord& mesh,StdImpt& t,const Re4dcModelPart& p,float near,float far){
    const unsigned frame=re4dc_ui_frame();
    if(impostor_frame!=frame){impostor_frame=frame;impostor_count=0;}
    if(impostor_flushed==frame)return 0; // after this frame's PT batches: geometry
    re4dc::room::MeshImpostor* r=&t.rec;
    const float* m=p.modelview;const float* C=r->centre;
    float c[3];
    for(unsigned i=0;i<3;++i)c[i]=m[4*i]*C[0]+m[4*i+1]*C[1]+m[4*i+2]*C[2]+m[4*i+3];
    if(!(-c[2]>=t.mm))return 0;
    const float scale=std::sqrt(m[0]*m[0]+m[1]*m[1]+m[2]*m[2]);
    if(-c[2]-(r->half_w>r->half_h?r->half_w:r->half_h)*scale>far)return 1;
    if(impostor_count>=kImpostorQuads){++impostor_stats[2];return 0;}
    const float dx=-(m[0]*c[0]+m[4]*c[1]+m[8]*c[2]),dz=-(m[2]*c[0]+m[6]*c[1]+m[10]*c[2]);
    const float length=std::sqrt(dx*dx+dz*dz),bx=length>0?dx/length:1.0f,bz=length>0?dz/length:0.0f;
    unsigned cell=unsigned(turns(-dz,dx)*float(r->views)+0.5f);
    if(cell>=r->views)cell-=r->views;
    ImpostorQuad& q=impostor_queue[impostor_count];
    const float* P=p.projection;const float* V=p.viewport;
    unsigned left=0,right=0,top=0,bottom=0;
    for(unsigned k=0;k<4;++k){
        const float sx=(k&1)?r->half_w:-r->half_w,sy=(k&2)?-r->half_h:r->half_h;
        const float x=C[0]+sx*bz,y=C[1]+sy,z=C[2]-sx*bx;
        const float vx=m[0]*x+m[1]*y+m[2]*z+m[3],vy=m[4]*x+m[5]*y+m[6]*z+m[7],vz=m[8]*x+m[9]*y+m[10]*z+m[11];
        if(!(-vz>near))return 0;
        const float inv=1.0f/(-vz);
        float* s=q.s[k];
        s[0]=(V[2]*.5f*(P[1]*vx+P[2]*vz)*inv+V[0]+V[2]*.5f)*RE4DC_SCREEN_WF/V[2];
        s[1]=(-V[3]*.5f*(P[3]*vy+P[4]*vz)*inv+V[1]+V[3]*.5f)*RE4DC_SCREEN_HF/V[3];
        s[2]=inv;
        left+=s[0]<0;right+=s[0]>RE4DC_SCREEN_WF;top+=s[1]<0;bottom+=s[1]>RE4DC_SCREEN_HF;
    }
    if(left==4 || right==4 || top==4 || bottom==4)return 1;
    q.record=r;q.cell=std::uint16_t(cell);q.fog=p.source_key[2]?1:0;q.argb=impostor_color(v,mesh,*r);
#if RE4DC_GC_ASSET_GATE
    q.source={re4dc_gcasset::source_use.payload,re4dc_gcasset::source_use.serial,re4dc_gcasset::source_use.mask};
#endif
    ++impostor_count;++impostor_stats[0];++std_stats[4];
    return 1;
}
#endif
int mesh_submit(const Re4dcModelPart& p){
    if(!p.static_geometry || !p.info || !p.part || !stats.owners_open)return 0;
    unsigned owner=0;
    const MeshEntry* e=find_entry(p.model,owner);
    if(!e){
        ++stats.locate_misses;
        if(stats.locate_misses<=32)re4dc_log("native mesh: unbound part model=%p\n",p.model);
        return 0;
    }
    MeshView& v=e->common?mesh_views[kCommonView]:mesh_views[owner];
#if RE4DC_GC_ASSET_GATE
    GcStaticSourceScope gcasset_source_scope(v.asset_proof,&v,&p);
#endif
    if(!v.package.valid() || e->mesh>=v.package.header().mesh_count){++stats.stale_bindings;return 0;}
    const auto& mesh=v.package.meshes()[e->mesh];
    const unsigned char* data=model_data(p);
    std::uint16_t vertices=0,parts=0;
#if RE4DC_COPY_LEAN
    if(data){vertices=*reinterpret_cast<const AliasHalf*>(data+0x38);parts=*reinterpret_cast<const AliasHalf*>(data+0x1A);}
#else
    if(data){std::memcpy(&vertices,data+0x38,2);std::memcpy(&parts,data+0x1A,2);}
#endif
    const std::uintptr_t offset=data?reinterpret_cast<std::uintptr_t>(p.part)-reinterpret_cast<std::uintptr_t>(first_part(data)):~std::uintptr_t(0);
    // Source layout, or a room archive that released this BIN's GX payload
    // (instanced_mesh.hpp source_part; such a part has no GX fallback).
    const auto* part=(data && offset<0x100000U)?
        v.package.source_part(e->mesh,vertices,parts,std::uint32_t(offset),p.stream_bytes):nullptr;
    if(!part){
        ++stats.key_misses;
        if(stats.key_misses<=32)re4dc_log("native mesh: part mismatch bin=%u common=%u vertices=%u/%u parts=%u/%u offset=%u size=%u\n",
            mesh.bin,mesh.common,vertices,mesh.source_vertices,parts,mesh.source_parts,unsigned(offset),p.stream_bytes);
        return 0;
    }
    // Before any deferral: p.lighting points at the bridge's stack copy.
    // The package lives in this view's writable heap-4 allocation.
    if(!part->reserved){
#if RE4DC_COPY_LEAN
        // Queued parts replay without a lighting snapshot (they were lit when
        // queued); only a package reopened within the frame arrives here unlit.
        if(!p.lighting)return 1;
#endif
        light_part(v,mesh,const_cast<re4dc::room::MeshPart&>(*part),p);
    }
    // Source vertex alpha: the mesh palette carries the authored CLR0 alpha, so
    // translucent vertex-alpha parts draw natively (and defer like any other).
#if RE4DC_COPY_LEAN
    union OpaqueCopy { Re4dcModelPart part; OpaqueCopy(){} } opaque; // built only when used
#else
    Re4dcModelPart opaque;
#endif
    const Re4dcModelPart* drawn=&p;
    bool vertex_alpha=false;
    if(p.alpha_state&256){
        const unsigned low=vertex_alpha_min(p);
        const bool alpha_unused=p.blend==0 && !(p.material_flags&4) && p.mask_ref>255;
        if(low<255 && !alpha_unused){vertex_alpha=true;++stats.vertex_alpha;}
        else {
#if RE4DC_COPY_LEAN
            new(&opaque.part) Re4dcModelPart(p);opaque.part.alpha_state=255;drawn=&opaque.part;
#else
            opaque=p;opaque.alpha_state=255;drawn=&opaque;
#endif
            if(low<255)++stats.vertex_alpha_unused;else ++stats.vertex_opaque;
        }
    }
    if(p.cull==3)return 1;
    if(p.projection[0]!=0 || p.viewport[2]<=0 || p.viewport[3]<=0)return 0;
    const float near=p.projection[6]/(p.projection[5]-1),far=p.projection[6]/p.projection[5];
    if(!re4dc::render::is_finite(near)||!re4dc::render::is_finite(far)||near<=0||far<=near)return 0;
#if RE4DC_QUALITY_ASSETS
    // Standard clutter cull (s16.3): the mesh's bounds centre at view depth >= mm draws nothing.
    if(std_room.active){
        const unsigned view=unsigned(&v-mesh_views);
        if((std_room.checked>>view)&1U)
            for(unsigned i=0;i<std_room.ncull;++i){
                const StdCull& c=std_room.cull[i];
                if(c.view!=view || c.mesh!=e->mesh)continue;
                const float* m=drawn->modelview;
                const float cx=(mesh.bounds_min[0]+mesh.bounds_max[0])*0.5f,cy=(mesh.bounds_min[1]+mesh.bounds_max[1])*0.5f,
                            cz=(mesh.bounds_min[2]+mesh.bounds_max[2])*0.5f;
                if(-(m[8]*cx+m[9]*cy+m[10]*cz+m[11])>=c.mm){++std_stats[0];return 1;}
                break;
            }
    }
#endif
#if RE4DC_TREE_IMPOSTOR
    {
        float cull=far;
#if RE4DC_NATIVE_FOG
        if(p.source_key[2] && fog_now.far>near && fog_now.far<far)cull=fog_now.far; // as MeshDraw::cull_far
#endif
        if(mesh_impostor(v,e->mesh,*part,*drawn,near,cull))return 1;
    }
#endif
    // Queued translucent parts replay through this function in pass order.
#if RE4DC_COPY_LEAN
    // The part is lit (above): a replay never reads its lighting again.
    if(re4dc_model_defer_part_unlit(drawn))return 1;
#else
    if(re4dc_model_defer_part(drawn))return 1;
#endif
    MeshDraw d{{*drawn,{},near,far},v.package,*part,v.lut,v.gather};
#if RE4DC_QUALITY_ASSETS
    if(std_room.active && std_room.nimpt){
        const unsigned view=unsigned(&v-mesh_views),index=unsigned(part-v.package.parts());
        if((std_room.checked>>view)&1U){
            float quad_far=far;
#if RE4DC_NATIVE_FOG
            if(drawn->source_key[2] && fog_now.far>near && fog_now.far<far)quad_far=fog_now.far;
#endif
            unsigned trees=0,quads=0;
            for(unsigned i=0;i<std_room.nimpt;++i){
                StdImpt& t=std_room.impt[i];
                if(t.view!=view || t.part!=index)continue;
                ++trees;
                if(tree_quad(v,mesh,t,*drawn,near,quad_far)){d.skip_clusters|=((std::uint64_t(1)<<t.count)-1U)<<t.first;++quads;}
                else ++std_stats[5];
            }
            const unsigned all=v.package.part_lods()[index].cluster_count;
            if(trees && quads==trees && all<=64U && d.skip_clusters==(all==64U?~std::uint64_t(0):(std::uint64_t(1)<<all)-1U))return 1;
        }
    }
#endif
    d.alpha=(drawn->alpha_state&255U)<<24;d.vertex_alpha=vertex_alpha;
    d.cull_far=far;
#if RE4DC_MESH_DIRECT
    d.direct=true;
#endif
#if RE4DC_NATIVE_FOG
    {
        const float view_far=fog_now.far; // source View._zfar, noted by model_bridge.cpp
        if(p.source_key[2] && view_far>near && view_far<far)d.cull_far=view_far; // hidden by the fog ramp
    }
#endif
#if RE4DC_MESH_LOD
    {
        // Pixels per model unit at unit depth: modelview scale (largest row,
        // placement scale included) times the projection's pixel scale.
        const float* m=drawn->modelview;
        float scale=0;
        for(unsigned r=0;r<3;++r){
            const float n=m[4*r]*m[4*r]+m[4*r+1]*m[4*r+1]+m[4*r+2]*m[4*r+2];
            if(n>scale)scale=n;
        }
        const float px_x=RE4DC_SCREEN_HALF_WF*std::fabs(p.projection[1]),px_y=RE4DC_SCREEN_HALF_HF*std::fabs(p.projection[3]);
        const float px=px_x>px_y?px_x:px_y;
        d.part_index=unsigned(part-v.package.parts());
#if RE4DC_QUALITY
        d.lod_scale=std::sqrt(scale)*px/re4dc_quality()->lod_px;   // Standard: 5 px (RQ_LOD_COARSE)
#else
        d.lod_scale=std::sqrt(scale)*px/float(RE4DC_MESH_LOD_PX);
#endif
    }
#endif
    // Mesh grid -> source model space -> live source view (node matrix included).
    const float grid[12]={mesh.step[0],0,0,mesh.origin[0], 0,mesh.step[1],0,mesh.origin[1],
                          0,0,mesh.step[2],mesh.origin[2]};
    concat(drawn->modelview,grid,d.mvq);
#if RE4DC_COPY_LEAN
    // MeshDraw reads mvq only, and bind() loads XMTRX before its first use
    // (culled parts never need it): no mv copy, no second matrix build.
#else
    std::memcpy(d.mv,d.mvq,sizeof(d.mv));
    load_screen(d.mvq,p.projection,p.viewport);
#endif
#if RE4DC_MESH_TEXTURES
    // A part with a texture record (a baked house shell) binds that package.
    unsigned baked[4];
#if RE4DC_QUALITY_ASSETS
    // Standard: the index's ptex records replace the package's texture records (s16.3).
    const unsigned* texture=nullptr;
    if(std_room.active){
        const unsigned view=unsigned(&v-mesh_views),index=unsigned(part-v.package.parts());
        if((std_room.checked>>view)&1U)
            for(unsigned i=0;i<std_room.nptex;++i)if(std_room.ptex[i].view==view && std_room.ptex[i].part==index){texture=std_room.ptex[i].key;++std_stats[2];break;}
        if(texture)re4dc_model_texture(texture);
    }else{
        const auto* record=v.package.texture(unsigned(part-v.package.parts()));
        if(record){baked[0]=record->key_crc;baked[1]=record->key_fnv;baked[2]=record->width;baked[3]=record->height;re4dc_model_texture(baked);texture=baked;}
    }
#else
    const auto* texture=v.package.texture(unsigned(part-v.package.parts()));
    if(texture){baked[0]=texture->key_crc;baked[1]=texture->key_fnv;baked[2]=texture->width;baked[3]=texture->height;re4dc_model_texture(baked);}
#endif
    const int result=d.run();
    if(texture)re4dc_model_texture(nullptr);
#else
    const int result=d.run();
#endif
#if RE4DC_MESH_DIRECT
    d.end_direct(); // before any abort: releases the store queues
#endif
    if(result>0){++stats.parts_native;return 1;}
    if(result<0){re4dc_model_packet_abort();++stats.aborts;return 1;}
    ++stats.parts_fallback;return 0;
}
#endif
}
#endif
extern "C" int re4dc_static_submit(const Re4dcModelPart* part){
    RE4DC_BFC_SCOPE(2u,0u);  // BACKFACE_CENSUS
#if RE4DC_NATIVE_STATIC
    const Re4dcModelPart& p=*part;
    const unsigned frame=re4dc_ui_frame();
    log_stats(frame);
#if RE4DC_NATIVE_MESH
#if RE4DC_NO_STD_ANY
    if(p.static_geometry)no_std_read(0,&p);
#endif
#if RE4DC_PS2_WORLD_ROOMS >= 2
    // An image the coarse path does not draw: the PS2 world where the skipped package would have drawn.
    if(p.static_geometry && no_std.room!=~0U && !no_std.coarse)re4dc_ps2_mesh_source(no_std.room,p);
#endif
    return mesh_submit(p);
#endif
    if(!p.world || !p.view || !p.static_geometry || !stats.owners_open)return 0;
    Located at;
    if(!locate(p,at)){
        ++stats.locate_misses;
        if(stats.locate_misses<=32)re4dc_log("native static: unlocated part model=%p serial=%u key=%u/%u\n",p.model,p.serial,p.source_key[0],p.source_key[1]);
        return 0;
    }
    Binding& b=*at.binding;View& v=*at.view;
#if RE4DC_GC_ASSET_GATE
    GcStaticSourceScope gcasset_source_scope(v.asset_proof,&v,&p);
#endif
    if(b.frame!=frame){b.frame=frame;b.drawn=b.fallback=0;}
    const auto& header=v.package.header();
    unsigned material=header.material_count;
    for(unsigned m=0;m<header.material_count;++m)
        if(v.keys[m].texture==p.source_key[0] && v.keys[m].alpha==p.source_key[1]){material=m;break;}
    if(material==header.material_count){++stats.key_misses;return 0;}
    const unsigned long long bit=1ULL<<material;
    // One part per key draws all of that key's batches; its twins either skip
    // (drawn) or follow it to the generic path, never both.
    if(b.fallback&bit){++stats.parts_fallback;return 0;}
    if(b.drawn&bit){++stats.parts_skipped;return 1;}
    // Per-vertex source alpha: the prelit package is opaque, which is exact only
    // while every entry of the model's colour array (pClr up to pTex) is 255.
    Re4dcModelPart opaque;
    const Re4dcModelPart* drawn=&p;
    if(p.alpha_state&256){
        const unsigned low=vertex_alpha_min(p);
        if((!stats.vertex_alpha && !stats.vertex_opaque) || low<stats.vertex_alpha_min)stats.vertex_alpha_min=low;
        // Vertex alpha only reaches the image through blending or an alpha
        // test. An opaque (blend 0), unmasked, non-alpha-texture material draws
        // the same whatever its vertex alpha, so it is native opaque too.
        const bool alpha_unused=p.blend==0 && !(p.material_flags&4) && p.mask_ref>255;
        if(low<255 && !alpha_unused){b.fallback|=bit;++stats.parts_fallback;++stats.vertex_alpha;return 0;}
        opaque=p;opaque.alpha_state=255;drawn=&opaque;
        if(low<255)++stats.vertex_alpha_unused;else ++stats.vertex_opaque;
    }
    if(p.cull==3){b.drawn|=bit;return 1;}
    if(p.projection[0]!=0 || p.viewport[2]<=0 || p.viewport[3]<=0){b.fallback|=bit;return 0;}
    const float near=p.projection[6]/(p.projection[5]-1),far=p.projection[6]/p.projection[5];
    if(!re4dc::render::is_finite(near)||!re4dc::render::is_finite(far)||near<=0||far<=near){b.fallback|=bit;return 0;}
    // Queued translucent parts replay through this function in pass order.
    if(re4dc_model_defer_part(drawn))return 1;

    Draw d{{*drawn,{},near,far},v,material};
    d.alpha=(drawn->alpha_state&255U)<<24;
    // Package space -> source world (x1000), then the object's movement since
    // it was bound (usually none), then the live source camera.
    float to_world[12]={kPackageToSource,0,0,0, 0,kPackageToSource,0,0, 0,0,kPackageToSource,0};
    if(std::memcmp(p.world,b.world,sizeof(b.world))){
        float inv[12],delta[12],moved[12];
        if(!inverse(b.world,inv)){b.fallback|=bit;return 0;}
        concat(p.world,inv,delta);concat(delta,to_world,moved);
        std::memcpy(to_world,moved,sizeof(moved));++stats.moved_objects;
    }
    concat(p.view,to_world,d.mv);
    if(const auto* q=v.package.compact_quantization()){
        const float grid[12]={q->step[0],0,0,q->origin[0], 0,q->step[1],0,q->origin[1], 0,0,q->step[2],q->origin[2]};
        concat(d.mv,grid,d.mvq);
    }else std::memcpy(d.mvq,d.mv,sizeof(d.mv));
    load_screen(d.mvq,p.projection,p.viewport);
    const int result=d.run({at.source,b.first_group,b.group_count});
    if(result>0){b.drawn|=bit;++stats.parts_native;return 1;}
    if(result<0){re4dc_model_packet_abort();b.drawn|=bit;++stats.aborts;return 1;}
    b.fallback|=bit;++stats.parts_fallback;return 0;
#else
    (void)part;return 0;
#endif
}

#if RE4DC_PS2_WORLD_MESH
// PS2_WORLD_MESH (game30.mk, render only): the PS2 r101 world converted offline to R4IM v3 (prelit
// ARGB1555 corners) plus an R4PW placement sidecar (tools/ps2_world_r4im.py), drawn by MeshDraw: cluster
// LOD, the transform-once meshlet fast path and direct TA submission; nothing is lit at runtime. The
// package is this path's own static allocation (not the room's), so a room reload keeps it; the room's
// retire (re4dc_ps2_world_retire) frees it. native_ps2_world.cpp routes draw/flush here.
namespace {
struct Ps2Part { std::uint32_t crc,fnv; std::uint16_t width,height; std::uint8_t pass,cull,texture,reserved; };
struct Ps2Placement { std::uint16_t mesh,placement; float affine[12]; };
struct Ps2Head { char magic[4]; std::uint32_t version,placements,parts,meshes,crc,reserved[2]; };
static_assert(sizeof(Ps2Part)==16 && sizeof(Ps2Placement)==52 && sizeof(Ps2Head)==32);
struct Ps2Counts { unsigned placements,culled,parts,native,fallback,aborts; float near,far,cull_far; };
struct Ps2World {
#if RE4DC_SCENERY_RECORD_SPLIT
    re4dc::record_split::WorldPackage package;
#else
    re4dc::room::MeshPackage package;
#endif
    unsigned char* storage=nullptr; unsigned bytes=0;
    const Ps2Part* parts=nullptr; const Ps2Placement* placements=nullptr; unsigned nplacements=0;
    const std::uint32_t* lut=nullptr; re4dc::room::CompactVertex12* gather=nullptr;
    float view[12]{},projection[7]{},viewport[6]{}; bool camera=false,attempted=false;
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::PayloadProof asset_proof;
#endif
    Ps2Counts count[3]{};
#if RE4DC_PS2_WORLD_ROOMS
    unsigned room=0,want=0x101; // package loaded / attempted for; the room re4dc_ps2_mesh_select asks for
#endif
#if RE4DC_PS2_PASS_MASK
    // PS2_PASS_MASK (game30.mk; exact): bit p = the placement's mesh has a part in pass p, built at open.
    static constexpr unsigned kMaskPlacements=2048;
    std::uint8_t pass_mask[kMaskPlacements]{}; bool masked=false;
#endif
#if RE4DC_PS2_STRIP_GROUPS
    unsigned char* sg_block=nullptr; const std::uint8_t* sg=nullptr; unsigned sg_groups=0; // ps2-world.r4sg (heap 4)
#if RE4DC_SCENERY21_AB
    bool alt=false; // SCENERY21_AB: the package came from dc/native/rXXX/sc21/ (arm B)
#endif
#endif
#if RE4DC_WORLD_VERT
    unsigned vert_loaded=0; // WORLD_VERT: the level resident in storage
    unsigned sg_bytes=0;    // WORLD_VERT: bytes of the strip-group block (level 0's size)
#endif
} ps2w;
#if RE4DC_GC_ASSET_GATE
void gcasset_invalidate_world(){if(ps2w.asset_proof.owner)re4dc_gcasset::payload_invalidate(ps2w.asset_proof,&ps2w);}
// cast-ps2-25 r16 item 5: the world's sealed manifest as captured at open (gate builds only). A route movie lends the
// interior cell (pc::unload invalidates the world proof) or the whole package (movie arena); when the same bytes come
// back (the cell's digest equal to the one the manifest sealed, the package at the same storage, crc/fnv checked by the
// reload) the world proof is captured again from this manifest instead of faulting every later draw.
struct GcWorldSeal {
    re4dc_gcasset::StaticManifest manifest; const unsigned char* base=nullptr; unsigned bytes=0,layout_bytes=0;
    const unsigned char* layout=nullptr; re4dc_gcasset::Digest cell{}; bool cell_sealed=false,have=false;
} gcasset_world_seal;
bool gcasset_world_cell_digest(re4dc_gcasset::Digest& d){
#if RE4DC_PS2_INTERIOR_CULL
    re4dc_gcasset::AssetDescription desc;
    if(!pc::data.block || pc::data.asset_proof.owner!=&pc::data || !pc::data.asset_proof.serial ||
       !re4dc_gcasset::describe_checked(pc::data.asset_proof.asset,&desc))return false;
    d=desc.digest;return true;
#else
    (void)d;return false;
#endif
}
void gcasset_world_seal_keep(const re4dc_gcasset::StaticManifest& m,const unsigned char* s,unsigned msize,const unsigned char* layout,unsigned psize){
    auto& k=gcasset_world_seal;
    k.have=ps2w.asset_proof.owner==&ps2w && ps2w.asset_proof.serial;
    k.manifest=m;k.base=s;k.bytes=msize;k.layout=layout;k.layout_bytes=psize;
    k.cell_sealed=gcasset_world_cell_digest(k.cell);
}
void gcasset_world_reseal(){
    auto& k=gcasset_world_seal;
    if(!k.have || !ps2w.storage || ps2w.storage!=k.base || (ps2w.asset_proof.owner==&ps2w && ps2w.asset_proof.serial))return;
    if(k.cell_sealed){
        re4dc_gcasset::Digest now{};
        if(!gcasset_world_cell_digest(now) || std::memcmp(now.bytes,k.cell.bytes,sizeof now.bytes))return; // stays unproven
    }
    re4dc_gcasset::payload_retire(ps2w.asset_proof);
    re4dc_gcasset::payload_capture_composite(ps2w.asset_proof,&ps2w,k.base,k.bytes,k.layout,k.layout_bytes,k.manifest);
}
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
unsigned r11fPackageGeneration=1,r11fSidecarCrc;
void r11fPackageAdvance() {
    if(r11fPackageGeneration!=~0U)++r11fPackageGeneration;
    r11fSidecarCrc=0;re4dc_r11f_native_cancel(0);
}
#endif
#if RE4DC_MOVIE_WORLD_ARENA
#include "include/movie_world_arena_lifecycle.inc"
movie_world::Ledger ps2_movie;
struct MovieWorldFiles { unsigned mesh=0,side=0,mesh_crc=0,mesh_fnv=0,side_crc=0,side_fnv=0; } ps2_movie_files;
bool ps2_movie_layout(unsigned room){
    const auto& f=ps2_movie_files;
    if(room==0x11f)return f.mesh==797056 && f.side==9076 && ps2_movie.capacity==811264;
#if RE4DC_MOVIE_WORLD_ARENA_S30
    // The current r100 SMX/TR4 package, with its LUT and gather storage.
#if RE4DC_SCENERY_DEDUP==3
    // Exact compact SDO3 lineage: fresh open authenticated its original extent/CRC.
    // h_ remains retained while the movie borrows this captured physical block.
    if(room==0x100 && ps2w.package.offline_dedup() && ps2w.package.source_bytes()==1537920 &&
       ps2w.package.header().bytes==1488192)
        return f.mesh==1488192 && f.side==19612 && ps2_movie.capacity==1512928;
#endif
    // n256r100 (SCENERY_N256, 256-vertex meshlets): the same sidecar, LUT and gather after a 1,461,184 B mesh.
    if(room==0x100 && f.mesh==1461184)return f.side==19612 && ps2_movie.capacity==1461184U+(1562656U-1537920U);
    if(room==0x100)return f.mesh==1537920 && f.side==19612 && ps2_movie.capacity==1562656;
#endif
    return false;
}
struct MovieWorldRead { MovieWorldRead(){++ps2_movie.readers;} ~MovieWorldRead(){--ps2_movie.readers;} };
bool ps2_movie_blocked(){if(!ps2_movie.unavailable())return false;++ps2_movie.blocked;return true;}
bool ps2_movie_current(){
    unsigned gen=0;
    return re4dc_room4_live_generation(&gen) && gen==ps2_movie.generation &&
        ps2_movie.base==ps2w.storage && ps2_movie.capacity==ps2w.bytes &&
        re4dc_room4_cell_valid(ps2_movie.base,ps2_movie.capacity,gen);
}
void ps2_movie_unpublish(){
#if RE4DC_GC_ASSET_GATE
    gcasset_invalidate_world();
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
    r11fPackageAdvance();
#endif
    ps2w.package.close();ps2w.parts=nullptr;ps2w.placements=nullptr;ps2w.nplacements=0;
    ps2w.lut=nullptr;ps2w.gather=nullptr;ps2w.camera=false;
#if RE4DC_PS2_PASS_MASK
    ps2w.masked=false;
#endif
#if RE4DC_SCENERY_DEDUP && RE4DC_SCENERY_DEDUP!=3
    dedup::pkg=nullptr; // until ps2_movie_reload reorders the package again
#endif
}
#endif
#if RE4DC_PS2_WORLD_SOURCE_OWNER
unsigned sourceWorldPackageGeneration=1,sourceWorldSidecarCrc;
#endif
#if RE4DC_PS2_VERTEX_ALPHA
// PS2_VERTEX_ALPHA (game30.mk): the ARGB4444 halves of a marked part's corner colour, laid out as vp::build_lut's
// ARGB1555 table ([0,256) high byte A4 R4, [256,512) low byte G4 B4), so the LUT path ORs the two the same way.
alignas(32) std::uint32_t ps2_lut4[512];
bool ps2_lut4_built=false;
const std::uint32_t* ps2_vertex_alpha_lut(){
    if(!ps2_lut4_built){
        for(unsigned i=0;i<256;++i){
            ps2_lut4[i]=(i>>4)*0x11000000U|(i&15U)*0x110000U;
            ps2_lut4[256+i]=(i>>4)*0x1100U|(i&15U)*0x11U;
        }
        ps2_lut4_built=true;
    }
    return ps2_lut4;
}
#endif
#if RE4DC_PS2_PASS_MASK==2
unsigned ps2_mask_stats[2]; // =2: placement-pass decisions checked, mismatched
#endif
#if RE4DC_PS2_PLACE_GATE
// PS2_PLACE_GATE (game30.mk; render only, default 0; lane objs 2026-10-15 for crowd12's STATIC_OBJ_BAKE): game objects
// baked into the PS2 world package own their placements. An owned placement is drawn by the world only while its object
// says so (re4dc_ps2_place_gate(room, placement, 1): the game asks to draw it AND its pose equals the baked one); with 0
// the object's live draw runs and the world skips it. Ownership is registered at object setup
// (re4dc_ps2_place_own, before the first render; the first call for another room drops the old set). The last call per
// placement holds: gate(..., 0) clears it (an object that leaves the baked pose or is deleted calls 0). Once per ui frame,
// at the first PS2 pass (before the scene's pass 0 is submitted, after every move of the tick), the registered prepare
// callback runs (re4dc_ps2_place_prepare_fn: the baking lane decides all its objects there, calling own() / gate()),
// then the requests are latched, so all passes of a frame agree. The callback is dropped at room exit
// (re4dc_ps2_mesh_retire): register it again at each room setup.
namespace gate {
constexpr unsigned kMax=512,kWords=kMax/32;
unsigned room=~0U,latched=~0U,owned_n=0,prep_room=~0U,skipped=0;
void (*prep)(unsigned)=nullptr;
std::uint32_t owned[kWords],want[kWords],cur[kWords];
#if RE4DC_PS2_PLACE_GATE==2
void diag(unsigned r);  // =2 (diagnostic, no caller needed): owns every 8th placement, toggles them every 64 frames
#endif
void begin(unsigned r){
    const unsigned f=re4dc_ui_frame();
    if(f==latched)return;
    latched=f;
#if RE4DC_PS2_PLACE_GATE==2
    diag(r);
#endif
    if(prep && prep_room==r)prep(r);
    for(unsigned w=0;w<kWords;++w)cur[w]=want[w];
}
void retire(){prep=nullptr;prep_room=~0U;room=~0U;owned_n=0;latched=~0U;
    for(unsigned w=0;w<kWords;++w)owned[w]=want[w]=cur[w]=0;}
inline bool skip(unsigned placement){
    return placement<kMax && ((owned[placement>>5]>>(placement&31U))&1U) && !((cur[placement>>5]>>(placement&31U))&1U);
}
void set_room(unsigned r){
    if(r==room)return;
    room=r;owned_n=0;
    for(unsigned w=0;w<kWords;++w)owned[w]=want[w]=cur[w]=0;
}
}
extern "C" void re4dc_ps2_place_prepare_fn(unsigned room,void (*fn)(unsigned room)){gate::prep=fn;gate::prep_room=room;}
extern "C" int re4dc_ui_texture_resident(unsigned crc,unsigned fnv);
// 1 when room's package is open, has this placement and every part texture of its mesh is resident (tex.pak key,
// lookup only); 0 otherwise. The baking lane owns a placement only once it is ready (call it at room setup, or from
// the prepare callback until it says 1): a missing key then only ever means the object's live draw.
extern "C" int re4dc_ps2_place_ready(unsigned room,unsigned placement){
    if(!ps2w.storage || !ps2w.parts || ps2w.room!=room)return 0;
    const auto& pk=ps2w.package;bool found=false;
    for(unsigned i=0;i<ps2w.nplacements;++i){
        const auto& pl=ps2w.placements[i];
        if(pl.placement!=placement)continue;
        found=true;
        const auto& mesh=pk.meshes()[pl.mesh];
        for(unsigned k=0;k<mesh.part_count;++k){
            const auto& q=ps2w.parts[mesh.first_part+k];
            if(!re4dc_ui_texture_resident(q.crc,q.fnv))return 0;
        }
    }
    return found?1:0;
}
extern "C" void re4dc_ps2_place_own(unsigned room,unsigned placement){
    gate::set_room(room);
    if(placement>=gate::kMax){re4dc_log("PS2GATE room=%03x placement=%u out of range\n",room,placement);return;}
    const std::uint32_t b=1U<<(placement&31U);
    if(!(gate::owned[placement>>5]&b)){gate::owned[placement>>5]|=b;++gate::owned_n;}
}
extern "C" void re4dc_ps2_place_gate(unsigned room,unsigned placement,int draw_world){
    if(room!=gate::room || placement>=gate::kMax)return;
    const std::uint32_t b=1U<<(placement&31U);
    if(draw_world)gate::want[placement>>5]|=b;else gate::want[placement>>5]&=~b;
}
#if RE4DC_PS2_PLACE_GATE==2
void gate::diag(unsigned r){
    const unsigned f=re4dc_ui_frame();
    for(unsigned p=0;p<kMax;p+=8){re4dc_ps2_place_own(r,p);re4dc_ps2_place_gate(r,p,(f>>6)&1U);}
    if(!(f%300U))re4dc_log("PS2GATE diag room=%03x frame=%u owned=%u state=%u skipped=%u ready0=%d ready8=%d\n",r,f,owned_n,
                           (f>>6)&1U,skipped,re4dc_ps2_place_ready(r,0),re4dc_ps2_place_ready(r,8));
}
#endif
#endif
#if RE4DC_PS2_AREA_HIDE
// PS2_AREA_HIDE (game30.mk; render only; lane objs 2026-10-15, PS2-ENEMY-CODE-DIFF-20261015 item 11): PS2 room code
// that shows / hides scenery groups by area (SmdSetTrans; be_flag bit 1 = drawn), applied to the PS2 world placements
// only: the game's objects, flags and logic are untouched. r107: PS2 st1_1.rel R107Main (0xf130) reads Room_flg[2]
// bits 31 / 30, which the PS2-only AEV flag areas 9 (flag 64 = bit 31) and 10 / 11 (flag 65 = bit 30) set each frame
// while the player is inside; r107.cpp tests the same quads (read only) and reports the bits (re4dc_ps2_area_flags):
//   bit 31: groups 60 70 80 90 drawn, 50 100 hidden;  bit 30: 90 100 drawn, 50 60 70 80 hidden;
//   neither: 50 60 drawn, 70 80 90 100 hidden.
// Groups -> placements are baked from the package's ps2-world.ids (t11-20261014/blackgc/r107, R4PW crc 9081e7fd, 71
// placements) and used only when the open package's sidecar crc matches. (r11f's re-show of groups 30 / 15 after its
// barn event is r11f.cpp r11f_ps2Area9: game objects, not this table.)
namespace area {
struct Group { unsigned id; std::uint32_t mask[3]; };
struct Room { unsigned room; std::uint32_t crc; unsigned placements; Group groups[6]; std::uint8_t shown[3]; };
constexpr Room kRooms[]={{0x107,0x9081e7fdU,71,{
    {50,{0x000003e0U,0,0}},{60,{0x00078000U,0,0}},{70,{0x07800000U,0,0}},
    {80,{0,0x00000fc0U,0}},{90,{0,0x001e0000U,0}},{100,{0,0x0fc00000U,0}}},
    {0x03,0x30,0x1e}}};  // shown groups (bit g = groups[g]) for flag state 0 neither, 1 bit 30, 2 bit 31
const Room* cur=nullptr; std::uint32_t hidden[3]={0,0,0};
unsigned state=~0U,flags_room=0,flags=0,skipped=0;
void open(unsigned room,std::uint32_t crc,unsigned n){
    cur=nullptr;state=~0U;hidden[0]=hidden[1]=hidden[2]=0;
    for(const auto& r:kRooms)if(r.room==room){
#if RE4DC_WORLD_RECT21
        // The retained r107 R4ID binds all 71 placement ordinals to this
        // original source CRC; its six group masks exactly match this table.
        // Certified remaps supply that policy identity, never a forged file CRC.
        const bool source_crc=r.crc==crc ||
            (r.room==0x107 && r.placements==71 && crc==0x43dc8ff9U);
        if(source_crc && r.placements==n)cur=&r;
#else
        if(r.crc==crc && r.placements==n)cur=&r;
#endif
        re4dc_log("PS2AREA room=%03x package crc=%08x placements=%u %s\n",room,unsigned(crc),n,cur?"ok":"mismatch: off");
    }
}
void update(){
    if(!cur || flags_room!=cur->room)return;  // r107.cpp has not reported this visit yet: draw everything
    const unsigned k=(flags&2U)?2U:(flags&1U)?1U:0U;
    if(k==state)return;
    state=k;hidden[0]=hidden[1]=hidden[2]=0;
    for(unsigned g=0;g<6;++g)if(!((cur->shown[k]>>g)&1U))for(unsigned w=0;w<3;++w)hidden[w]|=cur->groups[g].mask[w];
    re4dc_log("PS2AREA room=%03x state=%u hidden=%08x %08x %08x skipped=%u\n",cur->room,k,unsigned(hidden[0]),
              unsigned(hidden[1]),unsigned(hidden[2]),skipped);
}
inline bool hide(unsigned placement){return placement<96U && ((hidden[placement>>5]>>(placement&31U))&1U);}
}
extern "C" void re4dc_ps2_area_flags(unsigned room,unsigned flags){area::flags_room=room;area::flags=flags;}
#endif
#if RE4DC_PS2_WORLD_DYNAMIC
// PS2_WORLD_DYNAMIC (game30.mk; render only): the PS2 world package is baked at each SMD row's rest pose, so a
// scenery object the room code moves, turns or hides (SmdGetObjPtr / SmdSetTrans: r105's emblem puzzle and door,
// r100's gate swaps, r101's ladder, doors and dials) kept its baked look. The optional dc/native/r%03x/ps2-world.ids
// (tools/ps2_room_ids.py) gives each placement its scroll object id. scroll.cpp setObj reports each id's game object
// and its rest matrix (re4dc_ps2_dyn_bind); a placement whose id is unique in the package is then skipped while that
// object is hidden (be_flag bit 1 clear) and drawn through mat * inverse(rest) once its matrix left the rest pose.
// Ids shared by several placements and ids the game has no object for keep the baked draw.
namespace dyn {
constexpr unsigned kIds=250,kMoved=16,kNone=0xFF;
struct Head { char magic[4]; std::uint32_t version,count,crc; };
#if RE4DC_PS2_WORLD_PARTS
struct PartPose { const unsigned char* part; float pose[9]; };
constexpr unsigned part_cell_bytes(unsigned count){
    // Single-root witnesses append bind-root and inverse matrices to this cell.
    // Room4 validates exact payload size, including a refused root witness.
    return count*sizeof(PartPose)
#if RE4DC_PS2_WORLD_ROOT_POSE
        +(count==1?24U*sizeof(float):0U)
#endif
        ;
}
#endif
#if RE4DC_ROOT_POSE_WITNESS_PREFLIGHT
// Stored after the unique-ID Slot array in its one Room4 cell. The existing
// root reader's PartPose + two matrices layout is retained byte for byte.
struct RootWitness { PartPose part; float root[24]; };
static_assert(__builtin_offsetof(RootWitness,root)==sizeof(PartPose));
static_assert(sizeof(RootWitness)==part_cell_bytes(1));
#endif
#if RE4DC_ROOT_POSE_REFUSAL_DIAG
struct RootDiag { std::uint64_t refused,spill; unsigned reasons,dirty; };
enum RootReason : unsigned { RootFlags=1,RootSerial=2,RootMissing=4,RootInvalid=8,
    RootCapacity=16,RootHeap=32,RootChain=64 };
#endif
struct Slot {
    const unsigned char* obj; std::uint32_t serial; float rest[12];
#if RE4DC_PS2_WORLD_PARTS
    PartPose* parts; unsigned nparts,pose_offset; bool source;
#if RE4DC_PS2_WORLD_ROOT_POSE
    unsigned root_matrix_offset; // offset plus one; ~0U invalid; nonzero records a refused root witness
#endif
#endif
#if RE4DC_ROOT_POSE_REFUSAL_DIAG
    RootDiag diag;
#endif
};
unsigned char* block=nullptr;                      // heap-4 block: the ids file
const std::uint8_t* ids=nullptr; unsigned nids=0; // placement field -> id
Slot* slots=nullptr; unsigned nslots=0;
std::uint8_t slot_of[kIds];                        // id -> slot (kNone: baked)
#if RE4DC_ROOT_POSE_WITNESS_PREFLIGHT
static_assert(alignof(Slot)>=alignof(RootWitness));
constexpr unsigned slot_cell_bytes(unsigned count){
    constexpr unsigned stride=sizeof(Slot)+sizeof(RootWitness);
    return count && count<=kIds && count<=~0U/stride?count*stride:0U;
}
Slot* reserve_slots(unsigned count){
    const unsigned bytes=slot_cell_bytes(count);
    return bytes?static_cast<Slot*>(re4dc_static_alloc(bytes)):nullptr;
}
PartPose* reserved_pose(const Slot& s){
    if(!slots)return nullptr;
    const auto at=reinterpret_cast<std::uintptr_t>(&s),base_slot=reinterpret_cast<std::uintptr_t>(slots);
    if(at<base_slot || (at-base_slot)%sizeof(Slot) || (at-base_slot)/sizeof(Slot)>=nslots)return nullptr;
    auto* base=reinterpret_cast<RootWitness*>(slots+nslots);
    return &base[(at-base_slot)/sizeof(Slot)].part;
}
void release_parts(Slot& s){
    if(s.parts && s.parts!=reserved_pose(s))re4dc_static_free(s.parts);
}
#endif
#if RE4DC_ROOT_POSE_REFUSAL_DIAG
unsigned diag_cursor=0,diag_frame=~0U;
void root_note(Slot& s,unsigned reason,bool spill=false){
    if(spill)++s.diag.spill;else ++s.diag.refused;
    s.diag.reasons|=reason;s.diag.dirty=1;
}
void root_report(unsigned id,Slot& s,const char* when){
    if(!s.diag.dirty)return;
    re4dc_log("ROOTPOSE room=%03x id=%02x serial=%u object=%p when=%s refused=%llu spill=%llu reasons=%02x frame=%u\n",
        ps2w.room,id,s.serial,static_cast<const void*>(s.obj),when,
        static_cast<unsigned long long>(s.diag.refused),static_cast<unsigned long long>(s.diag.spill),
        s.diag.reasons,re4dc_ui_frame());
    s.diag.dirty=0;
}
// At pass entry, before any chunk/SQ ownership. At most four dirty owners per
// 120 native frames; totals are never sampled or cleared by periodic emission.
void root_reports(bool final=false){
    if(!slots)return;
    const unsigned now=re4dc_ui_frame();
    if(!final && diag_frame!=~0U && now-diag_frame<120U)return;
    diag_frame=now;
    unsigned budget=final?kIds:4U;
    for(unsigned walked=0;walked<kIds && budget;++walked){
        const unsigned id=diag_cursor++;if(diag_cursor==kIds)diag_cursor=0;
        const unsigned slot=slot_of[id];
        if(slot==kNone || slot>=nslots || !slots[slot].diag.dirty)continue;
        root_report(id,slots[slot],final?"retire":"periodic");--budget;
    }
}
#endif
#if RE4DC_PS2_WORLD_PARTS
std::uint8_t object_order[kIds]; unsigned nobjects=0;
#if RE4DC_PS2_WORLD_LEAN
// PS2_WORLD_LEAN bit 16: a 64-bit hash mask of every bound object address. re4dc_ps2_dyn_source (once per scenery
// object per frame, ~200 calls in r101) returns 0 at once when no bound object hashes to the asked address's bit;
// any other address takes the search as before (the answer is the same either way).
std::uint32_t lean_mask[2];
inline unsigned lean_bit(std::uintptr_t a){return unsigned((a>>4)^(a>>10)^(a>>16))&63U;}
void lean_rebuild(){
    lean_mask[0]=lean_mask[1]=0;
    for(unsigned i=0;i<nobjects;++i){
        const unsigned b=lean_bit(reinterpret_cast<std::uintptr_t>(slots[slot_of[object_order[i]]].obj));
        lean_mask[b>>5]|=1U<<(b&31U);
    }
}
#endif
void order_object(unsigned id){
    unsigned at=0;
    for(;at<nobjects && object_order[at]!=id;++at){}
    if(at<nobjects){for(unsigned j=at+1;j<nobjects;++j)object_order[j-1]=object_order[j];--nobjects;}
    const auto key=reinterpret_cast<std::uintptr_t>(slots[slot_of[id]].obj);
    at=0;
    while(at<nobjects && reinterpret_cast<std::uintptr_t>(slots[slot_of[object_order[at]]].obj)<key)++at;
    for(unsigned j=nobjects;j>at;--j)object_order[j]=object_order[j-1];
    object_order[at]=std::uint8_t(id);++nobjects;
#if RE4DC_PS2_WORLD_LEAN
    lean_rebuild();
#endif
}
#endif
unsigned off_flag=0,off_serial=0,off_mat=0;        // cObj field offsets (from the first bind)
unsigned frame=~0U,nmoved=0;
std::uint8_t state[kIds];                          // this frame: 0 unknown, 1 baked, 2 hidden, 3 moved, 4 source hierarchy
std::uint8_t moved_of[kIds];
float delta[kMoved][12];
unsigned binds=0,hidden=0,moved=0,overflow=0,logged_frame=0;
void reset(){
#if RE4DC_GC_ASSET_GATE
    gcasset_invalidate_world();
#endif
#if RE4DC_ROOT_POSE_REFUSAL_DIAG
    root_reports(true);diag_cursor=0;diag_frame=~0U;
#endif
    if(block)re4dc_static_free(block);
#if RE4DC_PS2_WORLD_PARTS
#if RE4DC_ROOT_POSE_WITNESS_PREFLIGHT
    if(slots)for(unsigned i=0;i<nslots;++i)release_parts(slots[i]);
#else
    if(slots)for(unsigned i=0;i<nslots;++i)if(slots[i].parts)re4dc_static_free(slots[i].parts);
#endif
    nobjects=0;
#if RE4DC_PS2_WORLD_LEAN
    lean_mask[0]=lean_mask[1]=0;
#endif
#endif
    if(slots)re4dc_static_free(slots);
    block=nullptr;ids=nullptr;nids=0;slots=nullptr;nslots=0;std::memset(slot_of,kNone,sizeof(slot_of));frame=~0U;
}
// 0 baked, 1 hidden, 2 moved (delta[moved_of[id]] = mat * inverse(rest)), 3 source hierarchy
unsigned query(unsigned id){
    const unsigned f=re4dc_ui_frame();
    if(f!=frame){frame=f;nmoved=0;std::memset(state,0,sizeof(state));}
    if(state[id])return state[id]-1U;
#if defined(RE4DC_RIGID_CENSUS) && RE4DC_RIGID_CENSUS == 2
    // RIGID_CENSUS=2 (cache20 census bench): `rigid <frame> off` also hides every PS2 world placement bound to a source
    // object (props drawn as PS2 world parts: r100's truck obm2d00, the police car, crates); render only
    if(re4dc_rigid_hide){++hidden;return 1;}
#endif
    unsigned r=0;
    Slot& s=slots[slot_of[id]];
    std::uint32_t flag=0,serial=0;
    if(s.obj){std::memcpy(&flag,s.obj+off_flag,4);std::memcpy(&serial,s.obj+off_serial,4);}
#if RE4DC_PS2_WORLD_ROOT_POSE
    // A one-bone model has one rigid transform for all of its geometry. Follow
    // that live root on the existing PS2 mesh instead of switching to the
    // source BIN, whose geometry may have been released by offline staging.
    if(s.root_matrix_offset){
        if(!s.obj || (flag&7U)!=7U || serial!=s.serial || !s.parts || s.root_matrix_offset==~0U){
#if RE4DC_ROOT_POSE_REFUSAL_DIAG
            root_note(s,!s.obj || serial!=s.serial?RootSerial:(flag&7U)!=7U?RootFlags:
                !s.parts?RootMissing:RootInvalid);
#endif
            state[id]=2;++hidden;return 1;
        }
        const auto* now=reinterpret_cast<const float*>(s.parts[0].part+s.root_matrix_offset-1U);
        const auto* rest=reinterpret_cast<const float*>(s.parts+1);
        const float* inv=rest+12; // computed once at bind, before any changed tick
        float change[12];
        bool valid=true;
#if RE4DC_ROOT_POSE_REFUSAL_DIAG
        bool capacity=false;
#endif
        for(unsigned i=0;i<12;++i)valid=valid && std::isfinite(now[i]);
        if(valid && std::memcmp(now,rest,12U*sizeof(float))){
            concat(now,inv,change);
            for(float v:change)valid=valid && std::isfinite(v);
            if(valid && nmoved<kMoved){
                std::memcpy(delta[nmoved],change,sizeof(change));moved_of[id]=std::uint8_t(nmoved++);
                state[id]=3;++moved;return 2;
            }
#if RE4DC_ROOT_POSE_REFUSAL_DIAG
            capacity=valid;
#endif
#if RE4DC_ROOT_POSE_CAP_FALLBACK
            if(valid){
                ++overflow;++moved;
#if RE4DC_ROOT_POSE_REFUSAL_DIAG
                root_note(s,RootCapacity,true);
#endif
                state[id]=5;return 4; // valid root, recomputed in this placement's draw scratch
            }
#else
            if(valid)++overflow;
#endif
            valid=false;
        }
#if RE4DC_ROOT_POSE_REFUSAL_DIAG
        if(!valid)root_note(s,capacity?RootCapacity:RootInvalid);
#endif
        if(!valid){state[id]=2;++hidden;return 1;} // never display stale baked geometry on refusal
        state[id]=1;return 0;
    }
#endif
    if(s.obj && (flag&1U) && serial==s.serial){
        const float* m=reinterpret_cast<const float*>(s.obj+off_mat);
#if RE4DC_PS2_WORLD_PARTS
        if(!s.source)for(unsigned i=0;i<s.nparts;++i){
            const PartPose& p=s.parts[i];
            if(std::memcmp(p.part+s.pose_offset,p.pose,sizeof(p.pose))){
                s.source=true;
                re4dc_log("PS2PART source id=%02x part=%u parts=%u frame=%u\n",id,i,s.nparts,f);
                break;
            }
        }
#endif
        if(!(flag&2U)){r=1;++hidden;}
#if RE4DC_PS2_WORLD_PARTS
        else if(s.source)r=3;
#endif
        else if(std::memcmp(m,s.rest,sizeof(s.rest))){
            float inv[12];
            if(nmoved<kMoved && inverse(s.rest,inv)){concat(m,inv,delta[nmoved]);moved_of[id]=std::uint8_t(nmoved++);r=2;++moved;}
            else ++overflow;
        }
    }
    state[id]=std::uint8_t(r+1U);
    return r;
}
#if RE4DC_ROOT_POSE_CAP_FALLBACK
// 0 refusal, 1 exact bind pose (use the baked affine directly), 2 moved.
// Revalidate before touching the borrowed part: eligibility and native drawing
// are separate callers, and a reused/hidden owner must never inherit a spill.
// The output belongs to one placement, never to the 16-entry frame cache.
int root_affine(unsigned id,const float* baked,float* out){
    if(id>=kIds || !slots || slot_of[id]==kNone || slot_of[id]>=nslots)return 0;
    Slot& s=slots[slot_of[id]];
    std::uint32_t flag=0,serial=0;
    if(s.obj){std::memcpy(&flag,s.obj+off_flag,4);std::memcpy(&serial,s.obj+off_serial,4);}
    if(!s.obj || (flag&7U)!=7U || serial!=s.serial || !s.parts || !s.root_matrix_offset || s.root_matrix_offset==~0U){
#if RE4DC_ROOT_POSE_REFUSAL_DIAG
        root_note(s,!s.obj || serial!=s.serial?RootSerial:(flag&7U)!=7U?RootFlags:
            !s.parts?RootMissing:RootInvalid);
#endif
        state[id]=2;++hidden;return 0;
    }
    const auto* now=reinterpret_cast<const float*>(s.parts[0].part+s.root_matrix_offset-1U);
    const auto* rest=reinterpret_cast<const float*>(s.parts+1);
    float change[12];
    bool valid=true;
    for(unsigned i=0;i<12;++i)valid=valid && std::isfinite(now[i]);
    if(valid && !std::memcmp(now,rest,12U*sizeof(float)))return 1;
    if(valid){
        concat(now,rest+12,change);
        for(float v:change)valid=valid && std::isfinite(v);
    }
    if(!valid){
#if RE4DC_ROOT_POSE_REFUSAL_DIAG
        root_note(s,RootInvalid);
#endif
        state[id]=2;++hidden;return 0;
    }
    concat(change,baked,out);
    return 2;
}
#endif
}
#endif
#if (defined(RE4DC_ENEMY_VIS_CULL) && RE4DC_ENEMY_VIS_CULL) || RE4DC_PS2_PVS
// ENEMY_VIS_CULL (engine_preview.mk; lane engine19; read only). re4dc_ps2_world_intact: 1 when the PS2 world drawn
// this frame is the package the room data file's OCCL section was compiled from (room and sidecar crc).
// re4dc_ps2_placements_intact: 1 when every listed placement (an occluder's sources, u16 LE fields) is drawn at its
// baked rest pose now (PS2_WORLD_DYNAMIC: a bound object not hidden, at rest, not on the source hierarchy;
// PS2_PLACE_GATE: not an owned placement the world skips; PS2_AREA_HIDE: not in a hidden group). Mirrors dyn::query /
// gate::skip / area::hide without touching their per-frame state.
std::uint32_t enemyVisSidecarCrc=0;
extern "C" int re4dc_ps2_world_intact(unsigned room,std::uint32_t crc){
#if RE4DC_PS2_WORLD_ROOMS
    if(ps2w.room!=room)return 0;
#endif
    return (ps2w.storage && ps2w.parts && crc && enemyVisSidecarCrc==crc)?1:0;
}
extern "C" int re4dc_ps2_placements_intact(unsigned room,const unsigned char* fields,unsigned n){
#if RE4DC_PS2_PVS
    if(!ps2w.storage || !ps2w.parts || (!fields && n))return 0;
#if RE4DC_PS2_WORLD_ROOMS
    if(ps2w.room!=room)return 0;
#endif
#endif
    (void)room;
    for(unsigned i=0;i<n;++i){
        const unsigned p=unsigned(fields[2*i])|(unsigned(fields[2*i+1])<<8);
        (void)p;
#if RE4DC_PS2_WORLD_DYNAMIC
        if(dyn::ids && dyn::slots && p<dyn::nids){
            const unsigned id=dyn::ids[p];
            if(id<dyn::kIds && dyn::slot_of[id]!=dyn::kNone){
                const dyn::Slot& s=dyn::slots[dyn::slot_of[id]];
#if RE4DC_PS2_WORLD_ROOT_POSE
                if(s.root_matrix_offset){
                    if(!s.obj || !s.parts || s.root_matrix_offset==~0U)return 0;
                    std::uint32_t flag=0,serial=0;
                    std::memcpy(&flag,s.obj+dyn::off_flag,4);std::memcpy(&serial,s.obj+dyn::off_serial,4);
                    if((flag&7U)!=7U || serial!=s.serial)return 0;
                    const auto* now=s.parts[0].part+s.root_matrix_offset-1U;
                    const auto* rest=reinterpret_cast<const float*>(s.parts+1);
                    if(std::memcmp(now,rest,12U*sizeof(float)))return 0;
                }
#endif
                if(s.obj){
                    std::uint32_t flag=0,serial=0;
                    std::memcpy(&flag,s.obj+dyn::off_flag,4);std::memcpy(&serial,s.obj+dyn::off_serial,4);
                    if((flag&1U) && serial==s.serial){   // query(): otherwise drawn baked
                        if(!(flag&2U))return 0;
#if RE4DC_PS2_WORLD_PARTS
                        if(s.source)return 0;
                        for(unsigned k=0;k<s.nparts;++k)
                            if(std::memcmp(s.parts[k].part+s.pose_offset,s.parts[k].pose,sizeof(s.parts[k].pose)))return 0;
#endif
                        if(std::memcmp(s.obj+dyn::off_mat,s.rest,sizeof(s.rest)))return 0;
                    }
                }
            }
        }
#endif
#if RE4DC_PS2_PLACE_GATE
        if(gate::room==room && p<gate::kMax && ((gate::owned[p>>5]>>(p&31U))&1U) &&
           !(((gate::cur[p>>5]&gate::want[p>>5])>>(p&31U))&1U))return 0;
#endif
#if RE4DC_PS2_AREA_HIDE
        if(area::cur && area::hide(p))return 0;
#endif
    }
    return 1;
}
#endif
std::uint32_t ps2_crc32(const unsigned char* p,unsigned n){
    std::uint32_t c=~0U;
    for(unsigned i=0;i<n;++i){c^=p[i];for(unsigned b=0;b<8;++b)c=(c>>1)^(0xedb88320U&(0U-(c&1U)));}
    return ~c;
}
#if RE4DC_PS2_WORLD_ROOMS
void ps2_free();
#endif
#if RE4DC_PS2_PVS
// Admission and frame guards are provided by the independently qualified static
// world proof unit. No guard/certificate, or a legacy sampled table: draw all.
extern "C" int re4dc_pvs23_table_guard(unsigned,const void*,unsigned,unsigned,unsigned,unsigned) __attribute__((weak));
extern "C" int re4dc_pvs23_frame_guard(unsigned,const float*,const float*,const float*,float,float) __attribute__((weak));
// PS2_PVS (t2exact.mk; exact, render only; lane t2exact 2026-10-15, backlog B4): an offline potentially visible set per
// camera cell (tools/d367/ps2world/pvs: pvs_prep.py, pvs_cast.cpp, pvs_emit.py). The room's X/Z grid of cells, each
// with a Y range (local ground + the camera heights) and a bit set over the package's cluster instances (placement
// order, the mesh's parts in order, each part's clusters in order). A cluster whose bit is clear cannot be seen from
// anywhere in the cell (the opaque world occludes it), so ps2_pass skips it, and a placement with no bit set at all.
// A camera outside every cell's volume, no file, or a file built for another package: no set, everything is drawn as
// before. Runtime toggle re4dc_ps2_pvs_on (warp line "pvs 0|1"; re4dc_ps2_pvs_set for a benchmark sweep row) on top of
// the build knob. The file is read into one heap-4 block with the per-placement and per-part instance offsets.
extern "C" { volatile unsigned re4dc_ps2_pvs_on=RE4DC_PS2_PVS_DEFAULT; void re4dc_ps2_pvs_set(unsigned on); }
namespace pvs {
struct Head { char magic[4]; std::uint32_t version,mesh_crc,mesh_bytes,sidecar_crc,ninst,nx,nz; float x0,z0,cell;
              std::uint32_t nsets,set_bytes,ncells,pad[2]; };
struct Cell { std::uint16_t set; std::int16_t ylo,yhi,pad; };
static_assert(sizeof(Head)==64 && sizeof(Cell)==8);
unsigned loaded_room=~0U,generation=0;
bool can_cut(unsigned placement);
unsigned char* block=nullptr; Head h{}; const Cell* cells=nullptr; const std::uint8_t* sets=nullptr;
const std::uint16_t* base=nullptr; const std::uint16_t* poff=nullptr; // per placement (n+1) / per part: first instance
const std::uint8_t* cur=nullptr; unsigned cur_frame=~0U,last_on=~0U; float last_view[12]{}; int cur_cell=-1; float eye[3]={0,0,0};
unsigned frames=0,active=0,pl_tested=0,pl_skipped=0,logged=~0U,bytes=0; const char* why="off";
void close(){
#if RE4DC_GC_ASSET_GATE
    gcasset_invalidate_world();
#endif
    ++generation;if(block)re4dc_static_free(block);block=nullptr;cells=nullptr;sets=nullptr;base=nullptr;poff=nullptr;cur=nullptr;
             cur_frame=~0U;cur_cell=-1;bytes=0;loaded_room=~0U;h={};why="off";}
// The camera's world position from the world-to-view affine (rows): v = R w + t, so w = -R^-1 t.
bool eye_of(const float* v,float e[3]){
    const float a=v[0],b=v[1],c=v[2],d=v[4],f=v[5],g=v[6],k=v[8],l=v[9],m=v[10];
    const float c0=f*m-g*l,c1=g*k-d*m,c2=d*l-f*k,det=a*c0+b*c1+c*c2;
    if(!(std::fabs(det)>1e-12f))return false;
    const float id=1.0f/det,t0=v[3],t1=v[7],t2=v[11];
    const float i00=c0*id,i01=(c*l-b*m)*id,i02=(b*g-c*f)*id;
    const float i10=c1*id,i11=(a*m-c*k)*id,i12=(c*d-a*g)*id;
    const float i20=c2*id,i21=(b*k-a*l)*id,i22=(a*f-b*d)*id;
    e[0]=-(i00*t0+i01*t1+i02*t2);e[1]=-(i10*t0+i11*t1+i12*t2);e[2]=-(i20*t0+i21*t1+i22*t2);
    return re4dc::render::is_finite(e[0]) && re4dc::render::is_finite(e[1]) && re4dc::render::is_finite(e[2]);
}
void open(unsigned room,std::uint32_t mesh_crc,std::uint32_t mesh_bytes,std::uint32_t side_crc GCASSET_STATIC_PARAM){
    close();why="absent";
    char path[48];snprintf(path,sizeof(path),"/cd/dc/native/r%03x/ps2-world.pvs",room);
    const file_t f=fs_open(path,O_RDONLY);
    if(f==FILEHND_INVALID){
#if RE4DC_GC_ASSET_GATE
        gcasset_static_state(gcmanifest,re4dc_gcasset::R4PV,re4dc_gcasset::Absent);
#endif
        re4dc_log("PS2PVS room=%03x file=absent\n",room);return;}
    const unsigned size=unsigned(fs_total(f));
    const unsigned np=ps2w.nplacements,nparts=ps2w.package.header().part_count;
    if(np>=65536U || nparts>=65536U){fs_close(f);why="instance capacity";return;}
    const unsigned extra=((np+1U)*2U+nparts*2U+31U)&~31U;
    auto* b=size>=sizeof(Head) && size<=262144U && !(size&31U)?static_cast<unsigned char*>(re4dc_static_alloc(size+extra)):nullptr;
    why=b?"read":"size or heap";
#if RE4DC_IO_ALIGNED
    const bool ok=b && read_package(f,b,size,0);
#else
    const bool ok=b && fs_read(f,b,size)==ssize_t(size);
#endif
    fs_close(f);
    if(ok){
        std::memcpy(&h,b,sizeof(h));why="header";
        if(std::memcmp(h.magic,"R4PV",4))why="magic";
        else if(h.version!=1U)why="version";
        else if(h.mesh_crc!=mesh_crc)why="mesh crc";
        else if(h.mesh_bytes!=mesh_bytes)why="mesh bytes";
        else if(h.sidecar_crc!=side_crc)why="physical policy crc";
        else if(!re4dc::pvs23::layout(h,size))why="layout";
        else why=nullptr;
        if(!why){
            const unsigned used=sizeof(Head)+8U*h.nx*h.nz+h.nsets*h.set_bytes;
            bool padding=true;for(unsigned i=used;i<size;++i)padding=padding && b[i]==0;
            if(!padding){re4dc_static_free(b);why="padding";return;}
            // instance offsets, counted as pvs_prep.py counts them; the total must be the file's
            auto* pb=reinterpret_cast<std::uint16_t*>(b+size);auto* po=pb+np+1U;
            const auto& pk=ps2w.package;const auto* lods=pk.part_lods();
            bool offsets_ok=true;
            for(unsigned m=0;m<pk.header().mesh_count;++m){
                const auto& mesh=pk.meshes()[m];std::uint64_t o=0;
                for(unsigned k=0;k<mesh.part_count;++k){
                    if(o>=65536U)offsets_ok=false;
                    po[mesh.first_part+k]=std::uint16_t(o);o+=lods[mesh.first_part+k].cluster_count;
                }
                if(o>=65536U)offsets_ok=false;
            }
            std::uint64_t n=0;
            for(unsigned i=0;i<np;++i){
                pb[i]=std::uint16_t(n);const auto& mesh=pk.meshes()[ps2w.placements[i].mesh];
                for(unsigned k=0;k<mesh.part_count;++k)n+=lods[mesh.first_part+k].cluster_count;
            }
            pb[np]=std::uint16_t(n);
            why="instances";
            if(offsets_ok && n==h.ninst && n<65536U){
                why=nullptr;
                cells=reinterpret_cast<const Cell*>(b+sizeof(Head));sets=b+sizeof(Head)+8U*h.nx*h.nz;base=pb;poff=po;
                unsigned valid_cells=0;
                for(unsigned c=0;c<h.nx*h.nz;++c){
                    const Cell& cell=cells[c];
                    if(cell.pad || (cell.set!=0xffffU && (cell.set>=h.nsets || cell.ylo>cell.yhi))){why="cell set/range";break;}
                    if(cell.set!=0xffffU)++valid_cells;
                }
                if(!why && valid_cells!=h.ncells)why="cell count";
                if(!why && (!re4dc_pvs23_table_guard || !re4dc_pvs23_frame_guard ||
                    !re4dc_pvs23_table_guard(room,b,size,mesh_crc,mesh_bytes,side_crc)))why="uncertified";
            }
        }else{
            re4dc_log("PS2PVS header reject room=%03x why=%s version=%u mesh_crc=%08x/%08x mesh_bytes=%u/%u physical_policy=%08x/%08x file_bytes=%u\n",
                      room,why,unsigned(h.version),unsigned(h.mesh_crc),unsigned(mesh_crc),unsigned(h.mesh_bytes),mesh_bytes,
                      unsigned(h.sidecar_crc),unsigned(side_crc),size);
        }
    }
    if(why){if(b)re4dc_static_free(b);cells=nullptr;sets=nullptr;base=nullptr;poff=nullptr;}
    else {
#if RE4DC_GC_ASSET_GATE
        gcasset_static_bytes(gcmanifest,re4dc_gcasset::R4PV,b,size,h.version);
#endif
        block=b;bytes=size+extra;loaded_room=room;}
    re4dc_log("PS2PVS room=%03x file=%s bytes=%u cells=%ux%u with_set=%u sets=%u instances=%u cell_mm=%d heap=%d\n",room,why?why:"ok",
              size+extra,unsigned(h.nx),unsigned(h.nz),unsigned(h.ncells),unsigned(h.nsets),unsigned(h.ninst),
              std::isfinite(h.cell) && h.cell>=0 && h.cell<2147483520.0f?int(h.cell):0,re4dc_static_heap_free());
}
// Once per frame: the camera's cell and its set (cur), or none.
void frame(const float* view,const float* projection,const float* viewport,float near,float far){
    const unsigned f=re4dc_ui_frame();
    const unsigned on=re4dc_ps2_pvs_on;
    if(!cells || on!=1U || !re4dc_pvs23_frame_guard ||
       !re4dc_pvs23_frame_guard(loaded_room,view,projection,viewport,near,far)){
        cur=nullptr;cur_frame=~0U;cur_cell=-1;return;
    }
    if(f==cur_frame && on==last_on && !std::memcmp(last_view,view,sizeof(last_view)))return;
    std::memcpy(last_view,view,sizeof(last_view));last_on=on;
    cur_frame=f;cur=nullptr;cur_cell=-1;++frames;
    if(!cells || re4dc_ps2_pvs_on!=1U || !eye_of(view,eye))return;
    const float fx=(eye[0]-h.x0)/h.cell,fz=(eye[2]-h.z0)/h.cell;
    if(!(fx>=0 && fz>=0 && fx<float(h.nx) && fz<float(h.nz)))return;
    const unsigned c=unsigned(fz)*h.nx+unsigned(fx);const Cell& e=cells[c];
    if(e.set==0xffffU || eye[1]<float(e.ylo)*100.0f || eye[1]>float(e.yhi)*100.0f)return;
    cur=sets+unsigned(e.set)*h.set_bytes;cur_cell=int(c);++active;
}
// A placement with no visible instance (no bit set in [base[i], base[i+1])).
bool hidden(unsigned i){
    if(!cur || !base || i>=ps2w.nplacements || !can_cut(i))return false;
    unsigned a=base[i];const unsigned e=base[i+1];
    ++pl_tested;
    for(;a<e;++a)if((cur[a>>3]>>(a&7U))&1U)return false;
    ++pl_skipped;return true;
}
} // namespace pvs
#include "include/pvs23_runtime.inc"
extern "C" void re4dc_ps2_pvs_set(unsigned on){
    re4dc_ps2_pvs_on=on<=2U?on:1U;
    pvs::cur=nullptr;pvs::cur_frame=~0U;pvs::cur_cell=-1;
}
extern "C" void re4dc_ps2_pvs_state(unsigned out[4]){
    out[0]=re4dc_ps2_pvs_on;out[1]=pvs::block?1U:0U;out[2]=pvs::cur?1U:0U;out[3]=pvs::bytes;
}
#endif
#if RE4DC_FAR_SHELL
#define RE4DC_FAR_SHELL_PART 1
#include "far_shell.inc"
#undef RE4DC_FAR_SHELL_PART
#endif
#if defined(RE4DC_TRANS_POLICY)
// TRANS_POLICY=<mask> (hwfog.mk, lane trans17 2026-10-17, TRANSPARENCY-PLAN-20261017.md sections 4-6; render only;
// unset = no code, image byte-identical). One offline class per R4PW part (tools/d367/tr_classify.py) in the room's
// sidecar ps2-world.r4tc ("R4TC" v1: the classifier version, the part count and the R4PW body crc it was made from,
// the crc32 of the class bytes, then one byte per part). A room without the file, or with a file made for another R4PW,
// draws exactly as today and logs why. Runtime word re4dc_trans_policy (.data), one bit per sub-switch:
//   1 FLAT  FLAT (uniform 14/15 alpha, r109 / r119 cabin walls and floor) and OPAQUE_IN_TR parts of the TR pass
//           draw in the opaque list (Tier 2: bounded 17/255 per channel, automated diff tools/d367/tr_pixdiff.py);
//   128 DROP a TR part whose shipped texture is alpha 0 in every texel is not drawn (Tier 1: draws nothing).
//   2 CARD / 4 SOFTA  CARD_NEAR / CARD_SOFTA parts draw punch-through (alpha test at PT_ALPHA_REF; Tier 2 or 3 by diff);
//   8 FAR  passes 1-2 stop at the depth where this frame's fog table reaches re4dc_trans_far_pct (see far_of).
// Vertex-alpha parts (R4PW reserved bit 0) are never moved. Bits 16 VA, 32 FX, 64 WATER are
// reserved (hwfog.mk refuses them until each is built and gated). The table lives in heap 4 beside the world and is
// freed with it; the movie-arena re-adopt path does no I/O, so after a movie return the policy is idle until the next open.
} // namespace (re4dc_trans_policy at file scope: dbgwarp_bridge.cpp links to it by its C name)
extern "C" { volatile unsigned re4dc_trans_policy=RE4DC_TRANS_POLICY; volatile unsigned re4dc_trans_far_pct=70U|(90U<<8); }
#if RE4DC_TRANS_POLICY_DEBUG
extern "C" { volatile unsigned re4dc_trans_debug=0; }
#endif
namespace {
namespace trans{
enum : unsigned { kUnknown=0,kOp=1,kPtBin=2,kOpaqueInTr=3,kFlat=4,kFlatMid=5,kCardNear=6,kCardSoftA=7,kSoft=8,kVa=9,kDrop=10 };
enum : unsigned { kTpFlat=1U,kTpCard=2U,kTpSofta=4U,kTpFar=8U,kTpDrop=128U };
struct Head { char magic[4]; std::uint32_t version,classifier,parts,r4pw_crc,body_crc; };
static_assert(sizeof(Head)==24);
static std::uint8_t* block=nullptr; static const std::uint8_t* cls=nullptr;
static unsigned room=~0U,nparts=0,flat=0,carded=0,dropped=0,last_room=~0U; static std::uint32_t last_frame;
static void close(){
#if RE4DC_GC_ASSET_GATE
    gcasset_invalidate_world();
#endif
    if(block)re4dc_static_free(block); block=nullptr;cls=nullptr;room=~0U;nparts=0; }
// After the R4PW sidecar is accepted (room, its body crc, its part count). Reads the class sidecar into heap 4.
// The disc's sidecar index (dc/native/trclass.idx, tools/d367/tr_classify.py: "R4TI", u32 count, u16 room ids), read
// once at the first world open, so a room without a sidecar costs no disc access at its entry (a door's wall-timed
// load would otherwise shift, coordinator 10-17). No index = the policy is idle for the whole session.
static std::uint16_t idx_rooms[128]; static unsigned idx_n=0; static int idx_state=0; // 0 unread, 1 ok, -1 none
#if RE4DC_GC_ASSET_GATE
static re4dc_gcasset::PayloadProof idx_asset_proof;
#endif
static bool listed(unsigned r){
    if(!idx_state){
        idx_state=-1;
        const file_t f=fs_open("/cd/dc/native/trclass.idx",O_RDONLY);
        if(f!=FILEHND_INVALID){
            unsigned char b[8+2*128];
            const ssize_t got=fs_read(f,b,sizeof(b));fs_close(f);
            std::uint32_t n=0;
            if(got>=8 && !std::memcmp(b,"R4TI",4)){std::memcpy(&n,b+4,4);
                if(n<=128 && got>=ssize_t(8+2*n)){
#if RE4DC_GC_ASSET_GATE
                    // The existing single bounded read consumes got bytes;
                    // it establishes no digest of an unread file suffix.
                    if(got<=ssize_t(sizeof(b))){
                        const auto digest=re4dc_gcasset::fingerprint(b,unsigned(got));
                        re4dc_gcasset::payload_capture_receipt(idx_asset_proof,idx_rooms,digest,unsigned(got));
                    }
#endif
                    std::memcpy(idx_rooms,b+8,2*n);idx_n=n;idx_state=1;}}
        }
        re4dc_log("trans: index %s rooms=%u\n",idx_state>0?"ok":"absent",idx_n);
    }
    for(unsigned i=0;i<idx_n;++i)if(idx_rooms[i]==r)return true;
    return false;
}
static void open(unsigned r,std::uint32_t r4pw_crc,unsigned parts GCASSET_STATIC_PARAM){
    close();
#if RE4DC_GC_ASSET_GATE
    const bool has_table=listed(r);
    if(gcmanifest){
        if(idx_state==1)re4dc_gcasset::static_manifest_receipt(*gcmanifest,re4dc_gcasset::R4TI_SELECTOR,idx_asset_proof,idx_rooms,1,re4dc_gcasset::StaticConsumedSpan);
        else gcasset_static_state(gcmanifest,re4dc_gcasset::R4TI_SELECTOR,re4dc_gcasset::Unproven);
    }
    if(!has_table){
#else
    if(!listed(r)){
#endif
#if RE4DC_GC_ASSET_GATE
        gcasset_static_state(gcmanifest,re4dc_gcasset::R4TC,idx_state==1?re4dc_gcasset::Absent:re4dc_gcasset::Unproven);
#endif
        re4dc_log("trans: room=%03x policy=%u classes=unlisted\n",r,unsigned(re4dc_trans_policy));return;}
    char path[48];snprintf(path,sizeof(path),"/cd/dc/native/r%03x/ps2-world.r4tc",r);
    const file_t f=fs_open(path,O_RDONLY);
    const char* why=nullptr;
#if RE4DC_GC_ASSET_GATE
    if(f==FILEHND_INVALID)gcasset_static_state(gcmanifest,re4dc_gcasset::R4TC,re4dc_gcasset::Absent);
#endif
    if(f==FILEHND_INVALID)why="no file";
    else{
        const unsigned size=unsigned(fs_total(f));
        Head h{};
        if(size!=sizeof(Head)+((parts+3U)&~3U))why="size";
        else if(!(block=static_cast<std::uint8_t*>(re4dc_static_alloc(size))))why="heap";
        else if(fs_read(f,block,size)!=ssize_t(size))why="read";
        else{
            std::memcpy(&h,block,sizeof(h));
            if(std::memcmp(h.magic,"R4TC",4) || h.version!=1 || h.parts!=parts)why="header";
            else if(h.r4pw_crc!=r4pw_crc)why="other r4pw";
            else if(ps2_crc32(block+sizeof(Head),parts)!=h.body_crc)why="crc";
        }
        fs_close(f);
        if(!why){
#if RE4DC_GC_ASSET_GATE
            gcasset_static_bytes(gcmanifest,re4dc_gcasset::R4TC,block,size,h.version);
#endif
            cls=block+sizeof(Head);room=r;nparts=parts;}
        else if(block){re4dc_static_free(block);block=nullptr;}
#if RE4DC_GC_ASSET_GATE
        // gc-catalog24b: present but rejected by its own checks (size, header,
        // stale r4pw crc, body crc): none of it is used. Heap/read faults stay Unproven.
        if(why && std::strcmp(why,"heap") && std::strcmp(why,"read"))
            gcasset_static_state(gcmanifest,re4dc_gcasset::R4TC,re4dc_gcasset::Rejected);
#endif
    }
    re4dc_log("trans: room=%03x policy=%u classes=%s parts=%u heap=%d\n",r,unsigned(re4dc_trans_policy),why?why:"ok",parts,
              re4dc_static_heap_free());
}
// The pass a translucent (pass 2, no vertex alpha) part of class c moves to under policy word p; 2 = stays.
static unsigned target(unsigned c,unsigned p){
    if((p&kTpFlat) && (c==kFlat || c==kOpaqueInTr))return 0;
    if((p&kTpCard) && c==kCardNear)return 1;
    if((p&kTpSofta) && c==kCardSoftA)return 1;
    return 2;
}
#if RE4DC_PS2_PASS_MASK
// The pass mask (one byte per placement) must list the pass a moved part can draw in (FLAT -> 0, CARD / SOFTA -> 1), or
// ps2_pass would skip the placement before reaching the part. Set for every movable part whatever the runtime bits: an
// extra bit costs a scan, never a draw.
static void mask(const Ps2Part* parts,const Ps2Placement* pl,unsigned n){
    if(!cls || !ps2w.masked)return;
    for(unsigned i=0;i<n;++i){
        const auto& mesh=ps2w.package.meshes()[pl[i].mesh];
        for(unsigned k=0;k<mesh.part_count;++k){
            const unsigned p=mesh.first_part+k;
            if(p>=nparts || parts[p].pass!=2 || (parts[p].reserved&1U))continue;
            const unsigned t=target(cls[p],kTpFlat|kTpCard|kTpSofta);
            if(t<2)ps2w.pass_mask[i]|=std::uint8_t(1U<<t);
        }
    }
}
#endif
// The pass a part draws in under the policy: 0 / 1 / 2, or 3 = not drawn. `now` is the pass after FOLIAGE_TRIM.
// re4dc_trans_debug (TRANS_POLICY_DEBUG=1 builds, warp line `transdbg <mask>`; never shipped): parts of the classes in
// the mask (bit = class number; 1 = FLAT and OPAQUE_IN_TR) are not drawn at all, so an A-vs-debug still pair gives
// tr_pixdiff.py --mask-diff the silhouette of the converted class.
static unsigned pass_of(const Ps2Part& m,unsigned index,unsigned now){
    if(!cls || room!=ps2w.room || index>=nparts)return now;
#if RE4DC_TRANS_POLICY_DEBUG
    {const unsigned dm=re4dc_trans_debug==1U?((1U<<kFlat)|(1U<<kOpaqueInTr)):re4dc_trans_debug;
     if((dm>>cls[index])&1U)return 3;}   // any pass, vertex alpha included (class VA = bit 9)
#endif
    if(m.pass!=2 || now!=2 || (m.reserved&1U))return now;
    const unsigned c=cls[index],p=re4dc_trans_policy;
    if((p&kTpDrop) && c==kDrop)return 3;
    const unsigned t=target(c,p);
    return t<2?t:now;
}
// For the unmasked placement scan: a part that the policy may move into `pass`.
static bool candidate(unsigned index,unsigned pass){
    if(!cls || room!=ps2w.room || index>=nparts || pass>1)return false;
    const auto& m=ps2w.parts[index];
    return m.pass==2 && !(m.reserved&1U) && target(cls[index],re4dc_trans_policy)==pass;
}
#if RE4DC_NATIVE_FOG
// FAR (bit 8): the depth beyond which the PVR fog table this frame is at or above a threshold everywhere, from the
// loaded table itself (trans_fog_table, entry 0 = the far plane). 0 = no such depth (fog off, or never that thick).
// Thresholds (percent): re4dc_trans_far_pct low byte = cards moved to punch-through (CARD / SOFTA / FOLIAGE Near),
// next byte = everything else drawn in passes 1-2 (native punch-through cutouts, soft cards, glass, unmoved cards).
// Vertex-alpha overlays are TP_VA's (not built), opaque parts are never touched. Warp line `transfar <low> <high>`.
static float cut_low,cut_high;
static float depth_at(float t){
    if(fog_loaded.type<=0 || !(trans_fog_tfar>0))return 0.0f;
    unsigned j=0;
    while(j<129 && trans_fog_table[j]>=t)++j;
    if(!j)return 0.0f;
    --j;
    const float v=j<128?float((j&15U)+16U)/16.0f*float(1U<<(j>>4)):256.0f;
    return trans_fog_tfar/v;
}
static void frame_cuts(){
    if(!(re4dc_trans_policy&kTpFar)){cut_low=cut_high=0.0f;return;}
    const unsigned w=re4dc_trans_far_pct;
    cut_low=depth_at(float(w&255U)/100.0f);cut_high=depth_at(float((w>>8)&255U)/100.0f);
    static unsigned logged=~0U;const unsigned f=re4dc_ui_frame();
    if(f-logged>=600U){logged=f;
        re4dc_log("trans: far room=%03x fog=%d tfar=%u cut=%u/%u mm (%u/%u %%)\n",unsigned(ps2w.room),fog_loaded.type,
                  unsigned(trans_fog_tfar),unsigned(cut_low),unsigned(cut_high),w&255U,(w>>8)&255U);}
}
// The far cut for a part drawn in pass `drawn` (1 or 2), 0 = none.
static float far_of(const Ps2Part& m,unsigned index,unsigned drawn){
    if(!(re4dc_trans_policy&kTpFar) || !drawn || drawn>2 || (m.reserved&1U))return 0.0f;
    if(drawn==1 && m.pass==2)return cut_low;          // a card moved to punch-through
    if(!cls || room!=ps2w.room || index>=nparts)return cut_high;
    const unsigned c=cls[index];
    return (c==kFlat || c==kOpaqueInTr || c==kOp)?0.0f:cut_high;
}
#endif
static void note(unsigned pass,unsigned drawn){
    if(drawn==0 && pass==0)++flat;
    if(drawn==1 && pass==1)++carded;
    if(drawn==3 && pass==2)++dropped;
    const std::uint32_t f=re4dc_vi_retrace_count();
    if(last_room!=ps2w.room || f-last_frame>=1200U){
#if RE4DC_NATIVE_FOG
        re4dc_log("trans: policy=%u room=%03x table=%u flat=%u card=%u dropped=%u far=%u/%u mm\n",unsigned(re4dc_trans_policy),
                  unsigned(ps2w.room),cls?1U:0U,flat,carded,dropped,unsigned(cut_low),unsigned(cut_high));
#else
        re4dc_log("trans: policy=%u room=%03x table=%u flat=%u card=%u dropped=%u\n",unsigned(re4dc_trans_policy),
                  unsigned(ps2w.room),cls?1U:0U,flat,carded,dropped);
#endif
        last_room=ps2w.room;last_frame=f;flat=carded=dropped=0;
    }
}
} // namespace trans
#endif
#if RE4DC_SCENERY_DEDUP==2 || RE4DC_SCENERY_CONE || RE4DC_SCENERY_PIECE_STATE
#include "include/room_file.h"
#endif
#if RE4DC_SCENERY_CONE || RE4DC_SCENERY_PIECE_STATE
// scenery21: the room file's SCCN / SCPS sections against this package (crc, bytes, counts; SCCN also needs the
// package's strip groups). A missing or stale section leaves its knob's path off for the room (SCN21 log line says why).
void scn21_open(GCASSET_STATIC_ONLY_PARAM){
#if RE4DC_GC_ASSET_GATE
    gcasset_invalidate_world();
#endif
    auto& pk=ps2w.package;const auto& h=pk.header();
    unsigned len=0,ver=0,fl=0;
#if RE4DC_SCENERY21_AB
    if(!ps2w.alt){   // arm A (or no sc21 package for this room): both paths stay off
#if RE4DC_SCENERY_CONE
        cone::pkg=nullptr;cone::rec=nullptr;cone::tab2=nullptr;
#endif
#if RE4DC_SCENERY_PIECE_STATE
        piece::pkg=nullptr;piece::table=nullptr;
#endif
        re4dc_log("SCN21 room=%03x arm A or no sc21 package: off\n",ps2w.room);
#if RE4DC_GC_ASSET_GATE
#if RE4DC_SCENERY_CONE
        gcasset_static_state(gcmanifest,re4dc_gcasset::SCCN,re4dc_gcasset::Disabled);
#endif
#if RE4DC_SCENERY_PIECE_STATE
        gcasset_static_state(gcmanifest,re4dc_gcasset::SCPS,re4dc_gcasset::Disabled);
#endif
#endif
        return;
    }
#endif
#if RE4DC_SCENERY_CONE
    {
        cone::pkg=nullptr;cone::rec=nullptr;cone::tab2=nullptr;
        const re4dc_room_header* source_header=nullptr;
        const auto* sec=static_cast<const std::uint8_t*>(re4dc_room_section("SCCN",&len,&ver,&fl,&source_header));
        const char* why=nullptr;std::uint32_t w[4]={};
        if(!sec)why="no section";
        else if(re4dc_room_file_room()!=ps2w.room)why="room";
        else if(!ps2w.sg)why="no strip groups";
        else{
            std::memcpy(w,sec,16);
            if(ver!=1 || w[0]!=h.crc || w[1]!=h.bytes || w[2]!=h.meshlet_count || w[3]!=ps2w.sg_groups ||
               len<16U+256U+8U*w[2]*w[3])why="package";
        }
#if RE4DC_GC_ASSET_GATE
        if(!sec)gcasset_static_state(gcmanifest,re4dc_gcasset::SCCN,re4dc_gcasset::Absent);
        else if(!why && re4dc_gcasset_room_span(sec,len,ver,fl,source_header))gcasset_static_bytes(gcmanifest,re4dc_gcasset::SCCN,sec,len,ver,fl);
#endif
        if(!why){cone::tab2=reinterpret_cast<const float*>(sec+16);cone::rec=sec+16+256;cone::pkg=&pk;}
        re4dc_log("SCN21 cone room=%03x %s groups=%u bytes=%u\n",ps2w.room,why?why:"on",unsigned(w[3]),len);
    }
#endif
#if RE4DC_SCENERY_PIECE_STATE
    {
        piece::pkg=nullptr;piece::table=nullptr;
        const re4dc_room_header* source_header=nullptr;
        const auto* sec=static_cast<const std::uint8_t*>(re4dc_room_section("SCPS",&len,&ver,&fl,&source_header));
        const char* why=nullptr;std::uint32_t w[4]={};
        if(!sec)why="no section";
        else if(re4dc_room_file_room()!=ps2w.room)why="room";
        else{
            std::memcpy(w,sec,16);
            if(ver!=1 || w[0]!=h.crc || w[1]!=h.bytes || w[2]!=h.part_count || len<16U+4U*w[2])why="package";
        }
        if(!why){
#if RE4DC_GC_ASSET_GATE
            if(re4dc_gcasset_room_original(sec,len,ver,fl,source_header))gcasset_static_bytes(gcmanifest,re4dc_gcasset::SCPS,sec,len,ver,fl);
#endif
            piece::table=reinterpret_cast<std::uint32_t*>(const_cast<std::uint8_t*>(sec)+16);
            std::memset(piece::table,0,4U*w[2]);   // slot words are this program's: start empty at every open
            piece::pkg=&pk;
        }
#if RE4DC_GC_ASSET_GATE
        if(!sec)gcasset_static_state(gcmanifest,re4dc_gcasset::SCPS,re4dc_gcasset::Absent);
#endif
        re4dc_log("SCN21 piece room=%03x %s parts=%u\n",ps2w.room,why?why:"on",unsigned(w[2]));
    }
#endif
}
#endif
#if RE4DC_SCENERY_DEDUP==3
// SDO3 is already reordered in the alternate package. The existing package owns
// all source bytes; there is no room section, mask, table allocation or reload reorder.
void dedup_free(){
#if RE4DC_GC_ASSET_GATE
    gcasset_invalidate_world();
#endif
} // no retained pointers, mask, generation state or allocation in mode3
void dedup_open(GCASSET_STATIC_ONLY_PARAM){
    auto& pk=ps2w.package;
    if(!pk.offline_dedup())return;
    unsigned repeats=0;
    for(unsigned i=0;i<pk.header().meshlet_count;++i)repeats+=pk.repeat_count(pk.meshlets()[i]);
    re4dc_log("SCNDEDUP3 room=%03x meshlets=%u repeats=%u extra_heap=0 source_crc=%08x actual_crc=%08x\n",
        ps2w.room,unsigned(pk.header().meshlet_count),repeats,unsigned(pk.source_crc()),unsigned(pk.header().crc));
}
#elif RE4DC_SCENERY_DEDUP
namespace dedup {
inline const re4dc::room::CompactVertex12& rec(const re4dc::room::MeshPackage& pk,const re4dc::room::Meshlet& l,unsigned k){
    const auto* v=pk.vertices()+l.first_vertex;
    return pk.indexed(l)?v[pk.pool_offsets(l)[k]]:v[k];
}
// first[k]: the first corner of the meshlet with corner k's grid position (k itself when new). Returns the repeats.
unsigned firsts(const re4dc::room::MeshPackage& pk,const re4dc::room::Meshlet& l,std::uint8_t* first){
    std::uint16_t table[512];std::memset(table,0,sizeof(table));
    unsigned rep=0;
    for(unsigned k=0;k<l.vertex_count;++k){
        const auto& a=rec(pk,l,k);
        for(unsigned h=(a.x*73856093U^a.y*19349663U^a.z*83492791U)&511U;;h=(h+1U)&511U){
            if(!table[h]){table[h]=std::uint16_t(k+1U);first[k]=std::uint8_t(k);break;}
            const auto& b=rec(pk,l,table[h]-1U);
            if(b.x==a.x && b.y==a.y && b.z==a.z){first[k]=std::uint8_t(table[h]-1U);++rep;break;}
        }
    }
    return rep;
}
// mode 0: count the repeats (no change). 1: reorder every meshlet, fill lets / src, rewrite the strip groups' corner
// ranges (sg: the records, groups per meshlet). 2: reorder and fill only (movie reload: the records stay rewritten).
// scratch: 256 corners (the package's gather buffer).
#if RE4DC_SCENERY_DEDUP==2
// SCENERY_DEDUP=2: lets / src / the repeat masks come from the room file's SCDD section (tools/d367/scenery19/
// scdd_compile.py), so the load reorder needs no position hashing and no allocation of its own.
const std::uint8_t* mask=nullptr;
// The section against this package, before anything is changed: extents, counts, and every repeat's first copy is an
// earlier non-repeat corner at the same grid position (a missed repeat only costs a transform; a wrong one would not
// be exact, so it refuses the whole section).
// scratch: the gather buffer (kGatherBytes), used for the indexed meshlets' pool ranges.
bool check(const re4dc::room::MeshPackage& pk,unsigned len,void* scratch){
    const auto* all=pk.meshlets();const unsigned nl=pk.header().meshlet_count;
    const std::uint8_t* m=mask;const std::uint8_t* const mend=reinterpret_cast<const std::uint8_t*>(lets)-16U+len;
    unsigned total=0;std::uint8_t pos[256],ipos[256];
    // A plain meshlet's corners are reordered in place in the vertex array, which indexed meshlets address through
    // their part pools: no pool may reach into a plain meshlet that has repeats (scdd_compile.py leaves those out).
    auto* pool=static_cast<std::uint32_t*>(scratch);unsigned npool=0;
    const unsigned maxpool=unsigned(sizeof(re4dc::room::CompactVertex12))*256U/8U;
    for(unsigned j=0;j<nl;++j){
        const auto& x=all[j];
        if(!pk.indexed(x) || !x.vertex_count)continue;
        if(npool>=maxpool)return false;
        const std::uint16_t* o=pk.pool_offsets(x);unsigned lo=0xffffU,hi=0;
        for(unsigned t=0;t<x.vertex_count;++t){if(o[t]<lo)lo=o[t];if(o[t]>hi)hi=o[t];}
        pool[2*npool]=x.first_vertex+lo;pool[2*npool+1]=x.first_vertex+hi+1U;++npool;
    }
    for(unsigned i=0;i<nl;++i){
        const unsigned rep=lets[i]>>24;
        if(!rep)continue;
        const auto& l=all[i];const unsigned n=l.vertex_count;
        if(n<2U || n>256U || rep>=n || (lets[i]&0xffffffU)!=total || m+((n+7U)>>3)>mend)return false;
        if(!pk.indexed(l)){
            const unsigned a=l.first_vertex,b=a+n;
            for(unsigned j=0;j<npool;++j)if(pool[2*j]<b && pool[2*j+1]>a)return false;
        }
        const unsigned u0=n-rep;unsigned u=0,d=u0;
        for(unsigned k=0;k<n;++k){pos[k]=std::uint8_t(m[k>>3]>>(k&7U)&1U?d++:u++);ipos[pos[k]]=std::uint8_t(k);}
        if(u!=u0 || d!=n)return false;
        for(unsigned k=0;k<n;++k){
            if(!(m[k>>3]>>(k&7U)&1U))continue;
            const unsigned f=src[total+pos[k]-u0];
            if(f>=u0)return false;
            const unsigned fk=ipos[f];
            const auto& a=rec(pk,l,k);const auto& b=rec(pk,l,fk);
            if(fk>=k || a.x!=b.x || a.y!=b.y || a.z!=b.z)return false;
        }
        m+=(n+7U)>>3;total+=rep;
    }
    return total==nsrc;
}
#endif
unsigned run(re4dc::room::MeshPackage& pk,std::uint8_t* sg,unsigned groups,void* scratch,int mode){
    const auto* all=pk.meshlets();
    unsigned total=0;
    std::uint8_t first[256],pos[256];
#if RE4DC_SCENERY_DEDUP==2
    const std::uint8_t* m=mask;(void)first;
#endif
    for(unsigned i=0;i<pk.header().meshlet_count;++i){
        const auto& l=all[i];const unsigned n=l.vertex_count;
#if RE4DC_SCENERY_DEDUP==2
        const unsigned rep=lets[i]>>24;
        if(!rep)continue;
        const unsigned u0=n-rep;
        unsigned u=0,d=u0;
        for(unsigned k=0;k<n;++k)pos[k]=std::uint8_t(m[k>>3]>>(k&7U)&1U?d++:u++);
        m+=(n+7U)>>3;
        std::uint8_t* s=src+total;total+=rep;
#else
        if(mode)lets[i]=0;
        if(n<2U || n>256U)continue;
        const unsigned rep=firsts(pk,l,first);
        if(!rep)continue;
        if(!mode){total+=rep;continue;}
        const unsigned u0=n-rep;
        unsigned u=0,d=u0;
        for(unsigned k=0;k<n;++k)pos[k]=std::uint8_t(first[k]==k?u++:d++);
        std::uint8_t* s=src+total;
        for(unsigned k=0;k<n;++k)if(first[k]!=k)s[pos[k]-u0]=pos[first[k]];
        lets[i]=total|(rep<<24);total+=rep;
#endif
        if(pk.indexed(l)){
            auto* off=const_cast<std::uint16_t*>(pk.pool_offsets(l));auto* t=static_cast<std::uint16_t*>(scratch);
            for(unsigned k=0;k<n;++k)t[pos[k]]=off[k];
            std::memcpy(off,t,2U*n);
        }else{
            auto* v=const_cast<re4dc::room::CompactVertex12*>(pk.vertices()+l.first_vertex);
            auto* t=static_cast<re4dc::room::CompactVertex12*>(scratch);
            for(unsigned k=0;k<n;++k)t[pos[k]]=v[k];
            std::memcpy(static_cast<void*>(v),t,sizeof(*v)*n);
        }
        auto* sb=const_cast<std::uint8_t*>(pk.strip_begin(l));const std::uint8_t* const end=sb+l.strip_bytes;
        for(std::uint8_t* p=sb;p<end;){const unsigned m=*p++;for(unsigned j=0;j<m;++j)p[j]=pos[p[j]];p+=m;}
        if(mode==1 && sg){
            auto* g=reinterpret_cast<std::uint16_t*>(sg+16U*groups*i);unsigned prev=0;
            for(unsigned q=0;q<groups;++q,g+=8){
                const unsigned gend=g[6];
                if(gend==prev)continue;
                unsigned lo=255,hi=0;
                for(const std::uint8_t* p=sb+prev;p<sb+gend;){
                    const unsigned m=*p++;
                    for(unsigned j=0;j<m;++j){unsigned c=p[j];if(c>=u0)c=s[c-u0];if(c<lo)lo=c;if(c>hi)hi=c;}
                    p+=m;
                }
                g[7]=std::uint16_t(lo|(hi<<8));prev=gend;
            }
        }
    }
    return total;
}
}
#if RE4DC_SCENERY_DEDUP==2
// the room file's heap-4 block (room_file.c) holds the section: never freed here, valid until the room leave
void dedup_free(){
#if RE4DC_GC_ASSET_GATE
    gcasset_invalidate_world();
#endif
    dedup::block=nullptr;dedup::pkg=nullptr;dedup::lets=nullptr;dedup::src=nullptr;dedup::mask=nullptr;
    dedup::nlets=dedup::nsrc=dedup::bytes=0;
}
void dedup_open(GCASSET_STATIC_ONLY_PARAM){
    dedup_free();
    auto& pk=ps2w.package;const unsigned nl=pk.header().meshlet_count;
    const std::uint64_t t0=timer_us_gettime64();
    unsigned len=0,ver=0,fl=0;
    const re4dc_room_header* source_header=nullptr;
    const auto* sec=static_cast<const std::uint8_t*>(re4dc_room_section("SCDD",&len,&ver,&fl,&source_header));
    const char* why=nullptr;unsigned nrep=0;
    if(!sec)why="no section";
#if defined(RE4DC_SCENERY_DEDUP_LOADONLY) && RE4DC_SCENERY_DEDUP_LOADONLY
    else if(sec)why="load only (test arm)";   // SCENERY_DEDUP_LOADONLY=1: the section is read (heap 4 as =2), draws as knob off
#endif
    else if(re4dc_room_file_room()!=ps2w.room)why="room";
    else if(ver!=1 || len<16U+4U*nl)why="size";
    else{
        std::uint32_t h[4];std::memcpy(h,sec,16);
        nrep=h[3];
        if(h[0]!=pk.header().crc || h[1]!=pk.header().bytes || h[2]!=nl || nrep>=(1U<<24) || len<16U+4U*nl+nrep)why="package";
        else{
            dedup::lets=reinterpret_cast<std::uint32_t*>(const_cast<std::uint8_t*>(sec)+16);
            dedup::src=const_cast<std::uint8_t*>(sec)+16+4U*nl;dedup::mask=dedup::src+nrep;
            dedup::nlets=nl;dedup::nsrc=nrep;
            if(!ps2w.gather || !dedup::check(pk,len,ps2w.gather)){why="check";dedup_free();}
        }
    }
    if(!why){
#if RE4DC_GC_ASSET_GATE
        if(re4dc_gcasset_room_original(sec,len,ver,fl,source_header))gcasset_static_bytes(gcmanifest,re4dc_gcasset::SCDD,sec,len,ver,fl);
#endif
        dedup::block=const_cast<void*>(re4dc_room_file_block());dedup::bytes=len;
        dedup::run(pk,ps2w.sg_block?ps2w.sg_block+32:nullptr,ps2w.sg_groups,ps2w.gather,1);
        dedup::pkg=&pk;
    }
#if RE4DC_GC_ASSET_GATE
    if(!sec)gcasset_static_state(gcmanifest,re4dc_gcasset::SCDD,re4dc_gcasset::Absent);
#endif
    re4dc_log("SCNDEDUP room=%03x meshlets=%u repeats=%u bytes=%u %s load_us=%u heap=%d\n",ps2w.room,nl,nrep,len,
              why?why:"applied",unsigned(timer_us_gettime64()-t0),re4dc_static_heap_free());
}
#else
void dedup_free(){
#if RE4DC_GC_ASSET_GATE
    gcasset_invalidate_world();
#endif
    if(dedup::block)re4dc_static_free(dedup::block);
    dedup::block=nullptr;dedup::pkg=nullptr;dedup::lets=nullptr;dedup::src=nullptr;dedup::nlets=dedup::nsrc=dedup::bytes=0;
}
#endif
#if RE4DC_SCENERY_DEDUP!=2
void dedup_open(GCASSET_STATIC_ONLY_PARAM){
    dedup_free();
    auto& pk=ps2w.package;const unsigned nl=pk.header().meshlet_count;
    const std::uint64_t t0=timer_us_gettime64();
    const unsigned nrep=dedup::run(pk,nullptr,0,ps2w.gather,0);
    const unsigned b=(4U*nl+nrep+31U)&~31U;
    void* blk=nrep && nrep<(1U<<24)?re4dc_static_alloc(b):nullptr;
    if(blk){
        dedup::block=blk;dedup::bytes=b;dedup::lets=static_cast<std::uint32_t*>(blk);
        dedup::src=static_cast<std::uint8_t*>(blk)+4U*nl;dedup::nlets=nl;dedup::nsrc=nrep;
        dedup::run(pk,ps2w.sg_block?ps2w.sg_block+32:nullptr,ps2w.sg_groups,ps2w.gather,1);
        dedup::pkg=&pk;
    }
    re4dc_log("SCNDEDUP room=%03x meshlets=%u repeats=%u bytes=%u %s load_us=%u heap=%d\n",ps2w.room,nl,nrep,b,
              blk?"applied":"off",unsigned(timer_us_gettime64()-t0),re4dc_static_heap_free());
}
#endif
#endif
#if RE4DC_SCENERY_LOCAL_INDEXED || RE4DC_SCENERY_DIRECT_STRIPS
constexpr auto kSceneryVariant=RE4DC_SCENERY_LOCAL_INDEXED?
    re4dc::scenery_data::Kind::LocalIndexed:re4dc::scenery_data::Kind::DirectStrips;
bool scenery_variant_room(unsigned room){
    // These consumers certify physical package layouts. Build 12 does not
    // relax their ownership/movie contracts to admit a differently sized file.
#if RE4DC_MOVIE_WORLD_ARENA
    if(room==0x11f)return false;
#if RE4DC_MOVIE_WORLD_ARENA_S30
    if(room==0x100)return false;
#endif
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
    if(room==0x11f)return false;
#endif
#if RE4DC_PS2_WORLD_SOURCE_OWNER
    if(room==0x200)return false;
#endif
    (void)room;return true;
}
#endif
#if RE4DC_SCENERY_RECORD_SPLIT
bool record_split_room(unsigned room){
#if RE4DC_MOVIE_WORLD_ARENA || RE4DC_PS2_WORLD_R11F_OWNER
    if(room==0x11f)return false;
#endif
#if RE4DC_MOVIE_WORLD_ARENA && RE4DC_MOVIE_WORLD_ARENA_S30
    if(room==0x100)return false;
#endif
#if RE4DC_PS2_WORLD_SOURCE_OWNER
    if(room==0x200)return false;
#endif
    (void)room;return true;
}
#endif
bool ps2_open(){
#if RE4DC_MOVIE_WORLD_ARENA
    if(ps2_movie_blocked())return false; // BEFORE storage/room-mismatch paths
#endif
#if RE4DC_PS2_WORLD_ROOMS
    if((ps2w.storage || ps2w.attempted) && ps2w.room!=ps2w.want)ps2_free(); // another room's package
#endif
#if RE4DC_FAR_SHELL
    if(ps2w.storage){farshell::sync();return true;}   // FAR_SHELL: read / free the shell as the View distance and heap 4 allow
#else
    if(ps2w.storage)return true;
#endif
    if(ps2w.attempted)return false;
    ps2w.attempted=true;
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::payload_retire(ps2w.asset_proof);gcasset_world_seal.have=false;
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
    r11fPackageAdvance();
#endif
#if RE4DC_PS2_WORLD_ROOMS
    ps2w.room=ps2w.want;
    char mpath[48],ppath[48];
    snprintf(mpath,sizeof(mpath),"/cd/dc/native/r%03x/ps2-world.re4mesh",ps2w.room);
    snprintf(ppath,sizeof(ppath),"/cd/dc/native/r%03x/ps2-world.r4pw",ps2w.room);
    re4dc_log("PS2MESH room=%03x open\n",ps2w.room);
#if RE4DC_SCENERY21_AB
    // SCENERY21_AB (bench disc): arm B reads the sc21 package of a room that has one (dc/native/rXXX/sc21/)
    ps2w.alt=false;
    file_t fm=FILEHND_INVALID;
    if(scn21_arm_b()){
        char apath[48];snprintf(apath,sizeof(apath),"/cd/dc/native/r%03x/sc21/ps2-world.re4mesh",ps2w.room);
        fm=fs_open(apath,O_RDONLY);
        if(fm!=FILEHND_INVALID)ps2w.alt=true;
    }
    if(fm==FILEHND_INVALID)fm=fs_open(mpath,O_RDONLY);
#elif RE4DC_WORLD_VERT || RE4DC_SCENERY_DEDUP==3 || RE4DC_SCENERY_LOCAL_INDEXED || RE4DC_SCENERY_DIRECT_STRIPS || RE4DC_SCENERY_RECORD_SPLIT
    file_t fm=fs_open(mpath,O_RDONLY);
#else
    const file_t fm=fs_open(mpath,O_RDONLY);
#endif
#if RE4DC_SCENERY_LOCAL_INDEXED || RE4DC_SCENERY_DIRECT_STRIPS
    unsigned variant_source_crc=0,variant_source_bytes=0;
    bool variant_alternate=false,variant_source_ok=false;
    if(!scenery_variant_room(ps2w.room)){
        re4dc_log("SCNVAR room=%03x requested=%s admitted=base reason=pinned-owner-or-movie\n",
            ps2w.room,re4dc::scenery_data::stem(kSceneryVariant));
    }else if(fm!=FILEHND_INVALID){
        char vpath[48];snprintf(vpath,sizeof(vpath),"/cd/dc/native/r%03x/%s.re4mesh",ps2w.room,
                               re4dc::scenery_data::stem(kSceneryVariant));
        const file_t fv=fs_open(vpath,O_RDONLY);
        if(fv!=FILEHND_INVALID){
            alignas(32) re4dc::room::MeshHeader source{};
            const auto bytes=fs_total(fm);
            variant_source_ok=bytes>=112 && bytes<=UINT32_MAX &&
                read_package(fm,reinterpret_cast<unsigned char*>(&source),sizeof(source),0) &&
                re4dc::scenery_data::source_header(source,unsigned(bytes));
            if(variant_source_ok){variant_source_crc=source.crc;variant_source_bytes=source.bytes;}
            fs_close(fm);fm=fv;variant_alternate=true;
        }else re4dc_log("SCNVAR room=%03x requested=%s admitted=base reason=alternate-absent\n",
                       ps2w.room,re4dc::scenery_data::stem(kSceneryVariant));
    }
#endif
#if RE4DC_SCENERY_RECORD_SPLIT
    unsigned split_source_crc=0,split_source_bytes=0;
    bool split_alternate=false,split_source_ok=false;
    if(!record_split_room(ps2w.room)){
        re4dc_log("SCNSPLIT room=%03x admitted=base reason=pinned-owner-or-movie\n",ps2w.room);
    }else if(fm!=FILEHND_INVALID){
        char path[64];snprintf(path,sizeof(path),"/cd/dc/native/r%03x/ps2-world-split.re4mesh",ps2w.room);
        const file_t alternate=fs_open(path,O_RDONLY);
        if(alternate!=FILEHND_INVALID){
            alignas(32) re4dc::room::MeshHeader source{};
            const auto extent=fs_total(fm);
            split_source_ok=extent>=112 && extent<=UINT32_MAX && read_package(fm,reinterpret_cast<unsigned char*>(&source),80U,0) &&
                re4dc::record_split::source_header(source,unsigned(extent));
            if(split_source_ok){split_source_crc=source.crc;split_source_bytes=source.bytes;}
            fs_close(fm);fm=alternate;split_alternate=true;
        }else re4dc_log("SCNSPLIT room=%03x admitted=base reason=alternate-absent\n",ps2w.room);
    }
#endif
#if RE4DC_SCENERY_DEDUP==3
    // Bind alternate source CRC/extent to the freshly read standard file header.
    unsigned dd_base_crc=0,dd_base_bytes=0;bool dd_alternate=false;
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::Digest gcasset_base80{};
#endif
    if(fm!=FILEHND_INVALID){
        char dpath[48];snprintf(dpath,sizeof(dpath),"/cd/dc/native/r%03x/ps2-dd3.re4mesh",ps2w.room);
        const file_t fd=fs_open(dpath,O_RDONLY);
        if(fd!=FILEHND_INVALID){
            alignas(32) std::uint32_t head[24];
            const auto base_bytes=fs_total(fm);
            if(fs_total(fd)>=112 && fs_total(fd)<=base_bytes && read_package(fm,reinterpret_cast<unsigned char*>(head),80U,0) &&
               head[0]==0x4d493452U && head[1]==3U && head[2]==unsigned(base_bytes) && head[16]==re4dc::room::kColorArgb1555 && !head[17] && !head[18] && !head[19]){
                dd_base_crc=head[3];dd_base_bytes=head[2];dd_alternate=true;fs_close(fm);fm=fd;
#if RE4DC_GC_ASSET_GATE
                gcasset_base80=re4dc_gcasset::fingerprint(head,80U);
#endif
            }else{fs_close(fd);fs_seek(fm,0,SEEK_SET);}
        }
    }
#endif
    const file_t fp=fs_open(ppath,O_RDONLY);
#else
#if RE4DC_WORLD_VERT
#error "WORLD_VERT needs PS2_WORLD_ROOMS"
#endif
    const file_t fm=fs_open("/cd/dc/native/r101/ps2-world.re4mesh",O_RDONLY);
    const file_t fp=fs_open("/cd/dc/native/r101/ps2-world.r4pw",O_RDONLY);
#endif
#if RE4DC_WORLD_VERT
    // WORLD_VERT (lane worldvert, render only): level N of the room's wholesale world reduction
    // (tools/ps2_world_vert_ladder.py) is ps2-wvN.re4mesh (+ ps2-wvN.r4sg; ISO9660 allows one dot) beside the level-0 package; the
    // R4PW sidecar and ids file are shared (same mesh / part / placement records). Memory neutral: the heap-4 block is
    // always sized by the level-0 file (one buffer the size of level 0; the sidecar sits at the same offset), and a level
    // file larger than level 0, or absent, falls back to level 0. ps2w.vert_loaded records what is resident.
    const unsigned l0size=fm!=FILEHND_INVALID?unsigned(fs_total(fm)):0U;
    ps2w.vert_loaded=0;
    if(world_vert_level && fm!=FILEHND_INVALID){
        char vpath[48];snprintf(vpath,sizeof(vpath),"/cd/dc/native/r%03x/ps2-wv%u.re4mesh",ps2w.room,world_vert_level);
        const file_t fv=fs_open(vpath,O_RDONLY);
        if(fv!=FILEHND_INVALID && unsigned(fs_total(fv))<=l0size && fs_total(fv)>0){fs_close(fm);fm=fv;ps2w.vert_loaded=world_vert_level;}
        else if(fv!=FILEHND_INVALID)fs_close(fv);
        re4dc_log("WORLDVERT room=%03x want=%u loaded=%u\n",ps2w.room,world_vert_level,ps2w.vert_loaded);
    }
    const unsigned msize=fm!=FILEHND_INVALID?unsigned(fs_total(fm)):0U,psize=fp!=FILEHND_INVALID?unsigned(fs_total(fp)):0U;
    const unsigned mbytes=(l0size+31U)&~31U,pbytes=(psize+31U)&~31U,total=mbytes+pbytes+kLutBytes+kGatherBytes;
#else
    const unsigned msize=fm!=FILEHND_INVALID?unsigned(fs_total(fm)):0U,psize=fp!=FILEHND_INVALID?unsigned(fs_total(fp)):0U;
    const unsigned mbytes=(msize+31U)&~31U,pbytes=(psize+31U)&~31U,total=mbytes+pbytes+kLutBytes+kGatherBytes;
#endif
    const int before=re4dc_static_heap_free();
#if RE4DC_PS2_OPEN_TRACE
    re4dc_log("PS2OPEN opened mesh=%d/%u sidecar=%d/%u heap=%d\n",int(fm),msize,int(fp),psize,before);
#endif
    auto* s=msize && psize>=sizeof(Ps2Head)?static_cast<unsigned char*>(re4dc_static_alloc(total)):nullptr;
#if RE4DC_PS2_OPEN_TRACE
    re4dc_log("PS2OPEN alloc %p bytes=%u align32=%u\n",static_cast<void*>(s),total,unsigned(reinterpret_cast<std::uintptr_t>(s)&31U));
    bool ok=s!=nullptr;
#if RE4DC_PS2_OPEN_READ
    const auto read_all=[](file_t f,unsigned char* d,unsigned n){return read_package(f,d,n,0)?ssize_t(n):ssize_t(-1);};
#else
    const auto read_all=[](file_t f,unsigned char* d,unsigned n){return fs_read(f,d,n);};
#endif
    if(ok){
        re4dc_log("PS2OPEN read mesh dst=%p bytes=%u tail=%u\n",static_cast<void*>(s),msize,msize&31U);
        const ssize_t got=read_all(fm,s,msize);ok=got==ssize_t(msize);
        re4dc_log("PS2OPEN read mesh got=%d\n",int(got));
    }
    if(ok){
        re4dc_log("PS2OPEN read sidecar dst=%p bytes=%u tail=%u\n",static_cast<void*>(s+mbytes),psize,psize&31U);
        const ssize_t got=read_all(fp,s+mbytes,psize);ok=got==ssize_t(psize);
        re4dc_log("PS2OPEN read sidecar got=%d\n",int(got));
    }
#elif RE4DC_PS2_OPEN_READ
#if !RE4DC_IO_ALIGNED
#error "PS2_OPEN_READ needs IO_ALIGNED=1 (read_package)"
#endif
    // PS2_OPEN_READ: both files through the IO_ALIGNED whole-file reader (s and s+mbytes are 32-byte aligned).
    bool ok=s && read_package(fm,s,msize,0) && read_package(fp,s+mbytes,psize,0);
#else
    bool ok=s && fs_read(fm,s,msize)==ssize_t(msize) && fs_read(fp,s+mbytes,psize)==ssize_t(psize);
#endif
    if(fm!=FILEHND_INVALID)fs_close(fm);
    if(fp!=FILEHND_INVALID)fs_close(fp);
    const char* why=ok?nullptr:s?"read":"missing or no heap";
#if RE4DC_SCENERY_DEDUP==3
    if(ok && msize>=80U){
        std::uint32_t marker=0,crc=0,source=0,extent=0;std::memcpy(&marker,s+76,4);std::memcpy(&crc,s+12,4);std::memcpy(&source,s+72,4);std::memcpy(&extent,s+68,4);
        if(dd_alternate && (marker!=re4dc::room::kOfflineDedupMarker || source!=dd_base_crc || (extent?extent:msize)!=dd_base_bytes)){why="offline source identity";ok=false;}
        else if(!dd_alternate && marker){why="offline filename";ok=false;}
        else if(dd_alternate && ps2_crc32(s+80,msize-80U)!=crc){why="offline crc";ok=false;}
    }
#endif
#if RE4DC_SCENERY_RECORD_SPLIT
    if(ok){
        re4dc::room::MeshHeader file{};
        if(msize>=sizeof(file))std::memcpy(&file,s,sizeof(file));
        if(split_alternate && (!split_source_ok || file.version!=4U || msize<112U)){
            why="split source/header";ok=false;
        }else if(!split_alternate && file.version==4U){why="split filename";ok=false;}
        else if(split_alternate && ps2_crc32(s+80,msize-80U)!=file.crc){why="split crc";ok=false;}
    }
#endif
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::StaticManifest gcasset_source;
    if(ok && msize<=mbytes && mbytes<=total && psize<=total-mbytes && total<=40U*1024*1024)
        re4dc_gcasset::static_manifest_begin(gcasset_source,re4dc_gcasset::StaticWorld,ps2w.room,gcasset_static_profile(),s,msize);
    using namespace re4dc_gcasset;
#if !(RE4DC_PS2_WORLD_DYNAMIC && RE4DC_PS2_WORLD_ROOMS)
    static_manifest_note(gcasset_source,R4ID,Disabled);
#endif
#if !defined(RE4DC_TRANS_POLICY)
    static_manifest_note(gcasset_source,R4TC,Disabled);static_manifest_note(gcasset_source,R4TI_SELECTOR,Disabled);
#endif
#if !RE4DC_PS2_PVS
    static_manifest_note(gcasset_source,R4PV,Disabled);
#endif
#if !RE4DC_PS2_STRIP_GROUPS
    static_manifest_note(gcasset_source,R4SG,Disabled);
#endif
#if !RE4DC_SCENERY_CONE
    static_manifest_note(gcasset_source,SCCN,Disabled);
#endif
#if !RE4DC_SCENERY_PIECE_STATE
    static_manifest_note(gcasset_source,SCPS,Disabled);
#endif
#if RE4DC_SCENERY_DEDUP!=2
    static_manifest_note(gcasset_source,SCDD,NotApplicable);
#endif
#if RE4DC_SCENERY_DEDUP==3
    if(dd_alternate)static_manifest_note(gcasset_source,SDO3_BASE80,Accepted,80U,3,StaticConsumedSpan,&gcasset_base80);
    else static_manifest_note(gcasset_source,SDO3_BASE80,NotApplicable);
#else
    static_manifest_note(gcasset_source,SDO3_BASE80,NotApplicable);
#endif
#endif
    if(ok && !ps2w.package.adopt(s,msize,true,true)){why=ps2w.package.error();ok=false;}
#if RE4DC_SCENERY_RECORD_SPLIT
    if(ok && split_alternate && !ps2w.package.source_identity(split_source_crc,split_source_bytes)){
        why="split source identity";ok=false;
    }
#endif
#if RE4DC_SCENERY_LOCAL_INDEXED || RE4DC_SCENERY_DIRECT_STRIPS
    if(ok){
        if(variant_alternate){
            if(!variant_source_ok)why="variant standard header";
            else if(ps2_crc32(s+80,msize-80U)!=ps2w.package.header().crc)why="variant crc";
            else why=re4dc::scenery_data::validate(ps2w.package,kSceneryVariant,variant_source_bytes,variant_source_crc);
            if(why)ok=false;
        }else if(ps2w.package.header().reserved[3]){why="variant filename";ok=false;}
    }
#endif
#if RE4DC_PS2_OPEN_TRACE
    re4dc_log("PS2OPEN adopt ok=%d why=%s\n",int(ok),why?why:"-");
#endif
    Ps2Head h{};
    if(ok){
        std::memcpy(&h,s+mbytes,sizeof(h));
        const auto& mh=ps2w.package.header();
        const unsigned body=psize-unsigned(sizeof(h));
        if(std::memcmp(h.magic,"R4PW",4) || h.version!=1 || h.parts!=mh.part_count || h.meshes!=mh.mesh_count ||
           body!=h.parts*sizeof(Ps2Part)+h.placements*sizeof(Ps2Placement) || ps2_crc32(s+mbytes+sizeof(h),body)!=h.crc){why="sidecar";ok=false;}
    }
    if(ok){
        ps2w.parts=reinterpret_cast<const Ps2Part*>(s+mbytes+sizeof(h));
        ps2w.placements=reinterpret_cast<const Ps2Placement*>(ps2w.parts+h.parts);
        for(unsigned i=0;i<h.parts && ok;++i){
            const auto& q=ps2w.parts[i];
            ok=q.pass<=2 && q.cull<=2 && q.width && q.height && q.width<=1024 && q.height<=1024;
        }
        for(unsigned i=0;i<h.placements && ok;++i){
            const auto& q=ps2w.placements[i];ok=q.mesh<h.meshes;
            for(float f:q.affine)ok=ok && re4dc::render::is_finite(f);
        }
        if(!ok)why="sidecar records";
    }
#if RE4DC_PS2_OPEN_TRACE
    re4dc_log("PS2OPEN sidecar ok=%d why=%s\n",int(ok),why?why:"-");
#endif
    if(!ok){
        ps2w.package.close();if(s)re4dc_static_free(s);ps2w.parts=nullptr;ps2w.placements=nullptr;
        re4dc_log("PS2MESH open failed: %s mesh=%u sidecar=%u heap=%d\n",why?why:"?",msize,psize,before);
        return false;
    }
    ps2w.storage=s;ps2w.bytes=total;ps2w.nplacements=h.placements;
#if RE4DC_GC_ASSET_GATE
    if(gcasset_source.geometry_base==s)static_manifest_bytes(gcasset_source,R4PW,s+mbytes,psize,h.version);
    else static_manifest_note(gcasset_source,R4PW,Unproven);
#endif
    // Geometry/material policy identity is separate from the physical R4PW
    // checksum. Only the certified scoped17 lineage can reuse original baked
    // metadata; profiles, logs and movie lifetime fingerprints remain actual.
    const std::uint32_t policySourceCrc=
#if RE4DC_WORLD_RECT21 && RE4DC_PS2_WORLD_ROOMS
        re4dc::rect21::provenance::policy_source_crc(ps2w.room,s+mbytes,psize,
#if RE4DC_SCENERY_DEDUP==3
            ps2w.package.source_crc(),ps2w.package.source_bytes(),
#else
            ps2w.package.header().crc,ps2w.package.header().bytes,
#endif
            ps2w.package.header().part_count,ps2w.package.header().mesh_count);
#else
        h.crc;
#endif
#if RE4DC_PS2_AREA_HIDE
#if RE4DC_WORLD_RECT21
    // A certified scoped world keeps its original group table (from 63644457; mipfix22).
    area::open(ps2w.room,policySourceCrc,h.placements);
#else
    area::open(ps2w.room,h.crc,h.placements);
#endif
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
    r11fSidecarCrc=h.crc;
#endif
#if RE4DC_PS2_WORLD_SOURCE_OWNER
    if(sourceWorldPackageGeneration!=~0U)++sourceWorldPackageGeneration;
    sourceWorldSidecarCrc=h.crc;
#endif
#if (defined(RE4DC_ENEMY_VIS_CULL) && RE4DC_ENEMY_VIS_CULL) || RE4DC_PS2_PVS
    enemyVisSidecarCrc=policySourceCrc;
#endif
#if RE4DC_PS2_WORLD_DYNAMIC && RE4DC_PS2_WORLD_ROOMS
    {
        // The id sidecar of this package (optional; a mismatched or absent file leaves every placement baked): the
        // whole file in one heap-4 block (32-byte padded, read as the package is), then a slot (object, serial, rest
        // matrix) per id unique in the package in a second block.
        dyn::reset();
        char ipath[48];snprintf(ipath,sizeof(ipath),"/cd/dc/native/r%03x/ps2-world.ids",ps2w.room);
        const file_t fi=fs_open(ipath,O_RDONLY);
        const unsigned isize=fi!=FILEHND_INVALID?unsigned(fs_total(fi)):0U;
        const char* iwhy="absent";
        auto* ib=isize>=sizeof(dyn::Head) && isize<=4096U && !(isize&31U)?static_cast<unsigned char*>(re4dc_static_alloc(isize)):nullptr;
        if(fi!=FILEHND_INVALID && !ib)iwhy="size or heap";
#if RE4DC_IO_ALIGNED
        const bool iread=ib && read_package(fi,ib,isize,0);
#else
        const bool iread=ib && fs_read(fi,ib,isize)==ssize_t(isize);
#endif
        if(fi!=FILEHND_INVALID)fs_close(fi);
        dyn::Head ih{};
        if(iread){
            std::memcpy(&ih,ib,sizeof(ih));
            iwhy="header";
            if(!std::memcmp(ih.magic,"R4ID",4) && ih.version==1 && ih.crc==policySourceCrc && ih.count==h.placements &&
               ih.count<=isize-sizeof(ih)){
                const std::uint8_t* idv=ib+sizeof(ih);
                std::uint8_t count[dyn::kIds]={};
                for(unsigned i=0;i<ih.count;++i)if(idv[i]<dyn::kIds && count[idv[i]]<2)++count[idv[i]];
                unsigned n=0;
                for(unsigned id=0;id<dyn::kIds;++id)if(count[id]==1)++n;
#if RE4DC_ROOT_POSE_WITNESS_PREFLIGHT
                // R4ID has placement IDs, not part counts: any unique ID can
                // become a one-root owner at setObj. Reserve every original
                // witness now, in the same cell as its Slot, before publication.
                auto* sb=dyn::reserve_slots(n);
                if(n && !sb){
                    re4dc_log("ROOTPOSE_PREFLIGHT room=%03x unique=%u bytes=%u heap=%d refused\n",
                        ps2w.room,n,dyn::slot_cell_bytes(n),re4dc_static_heap_free());
                    re4dc_static_free(ib);ib=nullptr;
                    // Only the newly opened package is live here. The old
                    // room was retired at the existing room-mismatch boundary;
                    // no dyn owner or movie borrower has been published.
                    ps2_free();
                    re4dc_missing("root-pose witness preflight");return false;
                }
#else
                auto* sb=n?static_cast<dyn::Slot*>(re4dc_static_alloc(n*sizeof(dyn::Slot))):nullptr;
#endif
                iwhy="no heap";
                if(sb){
#if RE4DC_GC_ASSET_GATE
                    static_manifest_bytes(gcasset_source,R4ID,ib,isize,ih.version);
#endif
                    unsigned k=0;
                    for(unsigned id=0;id<dyn::kIds;++id)if(count[id]==1)dyn::slot_of[id]=std::uint8_t(k++);
#if RE4DC_ROOT_POSE_WITNESS_PREFLIGHT
                    std::memset(static_cast<void*>(sb),0,dyn::slot_cell_bytes(n));
#else
                    std::memset(static_cast<void*>(sb),0,n*sizeof(dyn::Slot));
#endif
                    dyn::block=ib;dyn::ids=idv;dyn::nids=ih.count;dyn::slots=sb;dyn::nslots=n;ib=nullptr;
                    iwhy=nullptr;
                }
            }
        } else if(ib)iwhy="read";
#if RE4DC_GC_ASSET_GATE
        if(fi==FILEHND_INVALID)static_manifest_note(gcasset_source,R4ID,Absent);
        else if(iwhy && !std::strcmp(iwhy,"header"))static_manifest_note(gcasset_source,R4ID,Rejected); // gc-catalog24b: present, not used
#endif
        if(ib)re4dc_static_free(ib);
        re4dc_log("PS2DYN room=%03x ids=%s placements=%u unique=%u heap=%d\n",ps2w.room,iwhy?iwhy:"ok",dyn::nids,dyn::nslots,re4dc_static_heap_free());
    }
#endif
#if RE4DC_PS2_PASS_MASK
    // ps2_pass then skips a placement with no part in the pass on one byte, without reading its placement and mesh
    // records and scanning the mesh's parts (three passes x every placement, every drawn image). More placements
    // than the table: the scan, as before.
    ps2w.masked=h.placements<=Ps2World::kMaskPlacements;
    for(unsigned i=0;ps2w.masked && i<h.placements;++i){
        const auto& mesh=ps2w.package.meshes()[ps2w.placements[i].mesh];
        unsigned m=0;
        for(unsigned k=0;k<mesh.part_count;++k)m|=1U<<ps2w.parts[mesh.first_part+k].pass;
        ps2w.pass_mask[i]=std::uint8_t(m);
    }
#endif
#if defined(RE4DC_TRANS_POLICY)
    trans::open(ps2w.room,policySourceCrc,h.parts GCASSET_STATIC_ARG);
#if RE4DC_PS2_PASS_MASK
    trans::mask(ps2w.parts,ps2w.placements,h.placements);
#endif
#endif
#if RE4DC_PS2_PVS
    // PVS23 authenticates the exact physical scoped policy, unlike original
    // baked AREA/IDs/SG metadata which uses the provenance-mapped source CRC.
#if RE4DC_SCENERY_DEDUP==3
    // SDO3 certifies this exact source package's bounds, placements, meshlets and strip geometry.
    pvs::open(ps2w.room,ps2w.package.source_crc(),ps2w.package.source_bytes(),h.crc GCASSET_STATIC_ARG);
#else
    pvs::open(ps2w.room,ps2w.package.header().crc,ps2w.package.header().bytes,h.crc GCASSET_STATIC_ARG);
#endif
#endif
#if RE4DC_MESH_FASTPATH
    auto* lut=reinterpret_cast<std::uint32_t*>(s+mbytes+pbytes);re4dc::vp::build_lut(lut);ps2w.lut=lut;
#endif
    ps2w.gather=reinterpret_cast<re4dc::room::CompactVertex12*>(s+mbytes+pbytes+kLutBytes);
    const auto& mh=ps2w.package.header();
#if RE4DC_PS2_INTERIOR_CULL
    // The cell's portals hold for the package it was built from only.
#if RE4DC_SCENERY_DEDUP==3
    pc::st.ok=PC_ADOPT_PRE(ps2w.room,ps2w.package.source_crc(),policySourceCrc,ps2w.package.source_bytes()) ps2w.room==pc::kPcRoom && ps2w.package.source_crc()==pc::kPcMeshUse && policySourceCrc==pc::kPcSidecarUse && ps2w.package.source_bytes()==pc::kPcMeshBytesUse;
#else
    pc::st.ok=PC_ADOPT_PRE(ps2w.room,mh.crc,policySourceCrc,mh.bytes) ps2w.room==pc::kPcRoom && mh.crc==pc::kPcMeshUse && policySourceCrc==pc::kPcSidecarUse && mh.bytes==pc::kPcMeshBytesUse;
#endif
    re4dc_log("PCCULL cell room=%03x mesh_crc=%08x sidecar_crc=%08x %s cells=%u portals=%u mode=%d\n",ps2w.room,unsigned(mh.crc),unsigned(h.crc),
        pc::st.ok?"adopted":"not this package",pc::kPcCellCount,pc::kPcPortalCount,int(RE4DC_PS2_INTERIOR_CULL));
    pc::data.lent=false;
    if(pc::st.ok)pc::load();
#endif
#if RE4DC_MOVIE_WORLD_ARENA
    if(ps2w.room==0x11f
#if RE4DC_MOVIE_WORLD_ARENA_S30
       || ps2w.room==0x100
#endif
    ){
        unsigned gen=0;
        if(!re4dc_room4_live_generation(&gen) || !re4dc_room4_cell_valid(s,total,gen) || !ps2_movie.capture(s,total,gen)){
            re4dc_missing("movie world arena initial owner invalid");return false;
        }
        ps2_movie_files={msize,psize,ps2_crc32(s,msize),movie_world::fnv(s,msize),
                        ps2_crc32(s+mbytes,psize),movie_world::fnv(s+mbytes,psize)};
    }
#endif
#if RE4DC_PS2_STRIP_GROUPS
    {
        // PS2_STRIP_GROUPS: tools/ps2_strip_groups.py's group records for this exact package (mesh crc / bytes, R4PW
        // crc, record crc). Absent or not matching: no groups (the whole-meshlet path).
        char gpath[48];snprintf(gpath,sizeof(gpath),"/cd/dc/native/r%03x/ps2-world.r4sg",ps2w.room);
#if RE4DC_SCENERY_RECORD_SPLIT
        if(ps2w.package.is_split())snprintf(gpath,sizeof(gpath),"/cd/dc/native/r%03x/ps2-world-split.r4sg",ps2w.room);
#endif
#if RE4DC_SCENERY_LOCAL_INDEXED || RE4DC_SCENERY_DIRECT_STRIPS
        if(re4dc::scenery_data::kind(ps2w.package)!=re4dc::scenery_data::Kind::None)
            snprintf(gpath,sizeof(gpath),"/cd/dc/native/r%03x/%s.r4sg",ps2w.room,re4dc::scenery_data::stem(kSceneryVariant));
#endif
#if RE4DC_SCENERY_DEDUP==3
        if(ps2w.package.offline_dedup())snprintf(gpath,sizeof(gpath),"/cd/dc/native/r%03x/ps2-dd3.r4sg",ps2w.room);
#endif
#if RE4DC_SCENERY21_AB
        if(ps2w.alt)snprintf(gpath,sizeof(gpath),"/cd/dc/native/r%03x/sc21/ps2-world.r4sg",ps2w.room);
#endif
#if RE4DC_WORLD_VERT
        // WORLD_VERT: the level's own group records, in a block sized by level 0's (memory neutral; larger: no groups).
        file_t fg=fs_open(gpath,O_RDONLY);
        const unsigned g0size=fg!=FILEHND_INVALID?unsigned(fs_total(fg)):0U;
        if(ps2w.vert_loaded && fg!=FILEHND_INVALID){
            fs_close(fg);
            snprintf(gpath,sizeof(gpath),"/cd/dc/native/r%03x/ps2-wv%u.r4sg",ps2w.room,ps2w.vert_loaded);
            fg=fs_open(gpath,O_RDONLY);
            if(fg!=FILEHND_INVALID && unsigned(fs_total(fg))>g0size){fs_close(fg);fg=FILEHND_INVALID;}
        }
        const unsigned galloc=(g0size+31U)&~31U;
#else
        const file_t fg=fs_open(gpath,O_RDONLY);
#endif
        const unsigned gsize=fg!=FILEHND_INVALID?unsigned(fs_total(fg)):0U;
        const char* gwhy=fg==FILEHND_INVALID?"absent":nullptr;
        unsigned char* gb=nullptr;
        if(!gwhy && (gsize<32U || gsize>262144U || (gsize&15U)))gwhy="size";
#if RE4DC_WORLD_VERT
        if(!gwhy && !(gb=static_cast<unsigned char*>(re4dc_static_alloc(galloc))))gwhy="heap";
#else
        if(!gwhy && !(gb=static_cast<unsigned char*>(re4dc_static_alloc((gsize+31U)&~31U))))gwhy="heap";
#endif
        if(!gwhy && fs_read(fg,gb,gsize)!=ssize_t(gsize))gwhy="read";
        if(fg!=FILEHND_INVALID)fs_close(fg);
        std::uint32_t w[8]={};
        if(!gwhy){
            std::memcpy(w,gb,32);
            if(std::memcmp(gb,"R4SG",4) || w[1]!=1U || w[2]!=mh.meshlet_count || !w[3] || w[3]>8U || w[4]!=mh.crc ||
               w[5]!=mh.bytes || w[6]!=policySourceCrc || gsize!=32U+16U*w[2]*w[3] || ps2_crc32(gb+32,gsize-32U)!=w[7])gwhy="header";
        }
#if RE4DC_SCENERY_DEDUP==3
        if(!gwhy && ps2w.package.offline_dedup() && !ps2w.package.offline_groups(gb+32,gsize-32U,w[3]))gwhy="offline ranges";
#endif
#if RE4DC_SCENERY_RECORD_SPLIT
        if(!gwhy && ps2w.package.is_split())gwhy=ps2w.package.group_error(gb+32,gsize-32U,w[3]);
#endif
#if RE4DC_GC_ASSET_GATE
        if(fg==FILEHND_INVALID)static_manifest_note(gcasset_source,R4SG,Absent);
        // gc-catalog24b: present but rejected by its own checks: none of it is used
        else if(gwhy && std::strcmp(gwhy,"heap") && std::strcmp(gwhy,"read"))static_manifest_note(gcasset_source,R4SG,Rejected);
        else if(!gwhy){
#if RE4DC_WORLD_VERT
            if(gsize<=galloc && galloc<=40U*1024*1024)
#endif
                static_manifest_bytes(gcasset_source,R4SG,gb,gsize,w[1]);
        }
#endif
        if(gwhy){if(gb)re4dc_static_free(gb);}
        else {ps2w.sg_block=gb;ps2w.sg=gb+32;ps2w.sg_groups=w[3];
#if RE4DC_WORLD_VERT
              ps2w.sg_bytes=galloc;
#endif
        }
        re4dc_log("PS2SG room=%03x groups=%s per_meshlet=%u bytes=%u heap=%d\n",ps2w.room,gwhy?gwhy:"ok",unsigned(w[3]),gsize,
                  re4dc_static_heap_free());
    }
#endif
#if RE4DC_SCENERY_CONE || RE4DC_SCENERY_PIECE_STATE
    scn21_open(
#if RE4DC_GC_ASSET_GATE
        &gcasset_source
#endif
    );
#endif
#if RE4DC_SCENERY_DEDUP
    dedup_open(
#if RE4DC_GC_ASSET_GATE
        &gcasset_source
#endif
    );
#endif
#if RE4DC_GC_ASSET_GATE
    gcasset_static_policy(gcasset_source,ps2w.room);
    // A skipped enabled reader or a rejected/short/failed read is explicit
    // unproven data, never an inferred absence or geometry-only ancestry.
    for(unsigned r=0;r<StaticRoleCount;++r)if(!(gcasset_source.seen&(1U<<r)))static_manifest_note(gcasset_source,StaticRole(r),Unproven);
    payload_capture_composite(ps2w.asset_proof,&ps2w,s,msize,s+mbytes,psize,gcasset_source);
    gcasset_world_seal_keep(gcasset_source,s,msize,s+mbytes,psize);
#endif
    re4dc_log("PS2MESH open bytes=%u version=%u meshes=%u parts=%u meshlets=%u vertices=%u placements=%u heap=%d->%d\n",
        total,mh.version,mh.mesh_count,mh.part_count,mh.meshlet_count,mh.vertex_count,h.placements,before,re4dc_static_heap_free());
#if RE4DC_SCENERY_RECORD_SPLIT
    re4dc_log("SCNSPLIT room=%03x admitted=%s version=%u mesh_bytes=%u actual_crc=%08x source_crc=%08x source_bytes=%u emit_offset=%u bounds_offset=%u gather_reserved=%u\n",
        ps2w.room,ps2w.package.is_split()?"v4":"base",mh.version,mh.bytes,mh.crc,
        ps2w.package.is_split()?mh.reserved[2]:mh.crc,ps2w.package.is_split()?mh.reserved[3]:mh.bytes,
        mh.meshlet_offset,ps2w.package.is_split()?mh.reserved[1]:0U,kGatherBytes);
#endif
#if RE4DC_SCENERY_LOCAL_INDEXED || RE4DC_SCENERY_DIRECT_STRIPS
    re4dc_log("SCNVAR room=%03x requested=%s admitted=%s mesh_bytes=%u gather_reserved=%u actual_crc=%08x source_crc=%08x\n",
        ps2w.room,re4dc::scenery_data::stem(kSceneryVariant),variant_alternate?re4dc::scenery_data::stem(kSceneryVariant):"base",
        mh.bytes,kGatherBytes,mh.crc,re4dc::scenery_data::source_crc(ps2w.package));
#endif
#if RE4DC_FAR_SHELL
    farshell::pol.tried=false;
    farshell::sync();   // FAR_SHELL: the room's far shell, read with its world package only at View distance Short
#endif
#if RE4DC_PS2_VERTEX_ALPHA
    {unsigned marked=0;for(unsigned i=0;i<h.parts;++i)marked+=ps2w.parts[i].reserved&1U;
     re4dc_log("PS2VA marked_parts=%u of %u (ARGB4444 vertex alpha, translucent pass)\n",marked,unsigned(h.parts));}
#endif
    return true;
}
#if RE4DC_MOVIE_WORLD_ARENA
bool ps2_movie_reload(){
#if RE4DC_GC_ASSET_GATE
    gcasset_invalidate_world(); // mesh/R4PW alone cannot renew prepared sidecars
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
    r11fPackageAdvance();
#endif
    if(!ps2_movie_current() || ps2_movie.phase!=movie_world::Phase::returning)return false;
    MovieWorldRead read; // retirement must refuse any I/O-yielded reader
    const auto& files=ps2_movie_files;
    const unsigned mb=(files.mesh+31u)&~31u,pb=(files.side+31u)&~31u;
    if(!ps2_movie_layout(ps2w.room) || ps2w.room!=ps2w.want || mb+pb+kLutBytes+kGatherBytes!=ps2_movie.capacity)return false;
    Re4dcIoScope io;
    char mesh_path[64],side_path[64];
    snprintf(mesh_path,sizeof(mesh_path),"/cd/dc/native/r%03x/ps2-world.re4mesh",ps2w.room);
#if RE4DC_SCENERY21_AB
    if(ps2w.alt)snprintf(mesh_path,sizeof(mesh_path),"/cd/dc/native/r%03x/sc21/ps2-world.re4mesh",ps2w.room);
#endif
#if RE4DC_SCENERY_DEDUP==3
    // MeshPackage::close retains h_ while a movie borrows its storage; this chooses the captured file again.
    if(ps2w.package.offline_dedup())snprintf(mesh_path,sizeof(mesh_path),"/cd/dc/native/r%03x/ps2-dd3.re4mesh",ps2w.room);
#endif
    snprintf(side_path,sizeof(side_path),"/cd/dc/native/r%03x/ps2-world.r4pw",ps2w.room);
    const file_t fm=fs_open(mesh_path,O_RDONLY);
    const file_t fp=fs_open(side_path,O_RDONLY);
    bool ok=fm!=FILEHND_INVALID && fp!=FILEHND_INVALID && fs_total(fm)==ssize_t(files.mesh) && fs_total(fp)==ssize_t(files.side);
    auto* data=static_cast<unsigned char*>(ps2_movie.base);
    // Keep source timeslicing outside the native file calls, including fallback reads.
    if(ok)ok=ps2_movie_current() && read_package(fm,data,files.mesh,0);
    if(ok)ok=ps2_movie_current() && read_package(fp,data+mb,files.side,0);
    if(fm!=FILEHND_INVALID)fs_close(fm);
    if(fp!=FILEHND_INVALID)fs_close(fp);
    if(!ok || !ps2_movie_current())return false;
    if(ps2_crc32(data,files.mesh)!=files.mesh_crc || movie_world::fnv(data,files.mesh)!=files.mesh_fnv ||
       ps2_crc32(data+mb,files.side)!=files.side_crc || movie_world::fnv(data+mb,files.side)!=files.side_fnv)return false;
    if(!ps2w.package.adopt(data,files.mesh,true,true))return false;
    Ps2Head h{};std::memcpy(&h,data+mb,sizeof(h));
    const auto& mh=ps2w.package.header();
    const unsigned body=files.side-unsigned(sizeof(h));
    if(std::memcmp(h.magic,"R4PW",4) || h.version!=1 || h.parts!=mh.part_count || h.meshes!=mh.mesh_count ||
       body!=h.parts*sizeof(Ps2Part)+h.placements*sizeof(Ps2Placement) || ps2_crc32(data+mb+sizeof(h),body)!=h.crc){
        ps2w.package.close();return false;
    }
    auto* parts=reinterpret_cast<const Ps2Part*>(data+mb+sizeof(h));
    auto* placements=reinterpret_cast<const Ps2Placement*>(parts+h.parts);
    for(unsigned i=0;i<h.parts;++i){const auto& q=parts[i];
        if(q.pass>2 || q.cull>2 || !q.width || !q.height || q.width>1024 || q.height>1024){ps2w.package.close();return false;}}
    for(unsigned i=0;i<h.placements;++i){const auto& q=placements[i];
        if(q.mesh>=h.meshes){ps2w.package.close();return false;}
        for(float f:q.affine)if(!re4dc::render::is_finite(f)){ps2w.package.close();return false;}}
    ps2w.parts=parts;ps2w.placements=placements;ps2w.nplacements=h.placements;
#if RE4DC_PS2_PVS
    if(ps2w.room==0x11f)pvs::close(); // the original arena package has no set
    else {pvs::cur=nullptr;pvs::cur_frame=~0u;pvs::cur_cell=-1;}
#endif
#if RE4DC_PS2_PASS_MASK
    ps2w.masked=h.placements<=Ps2World::kMaskPlacements;
    for(unsigned i=0;ps2w.masked && i<h.placements;++i){
        const auto& mesh=ps2w.package.meshes()[placements[i].mesh];unsigned mask=0;
        for(unsigned k=0;k<mesh.part_count;++k)mask|=1u<<parts[mesh.first_part+k].pass;
        ps2w.pass_mask[i]=std::uint8_t(mask);
    }
#endif
#if defined(RE4DC_TRANS_POLICY)
    trans::close(); // no I/O here: the policy idles until the next ps2_open (logged by trans::note as table=0)
#endif
#if RE4DC_MESH_FASTPATH
    auto* lut=reinterpret_cast<std::uint32_t*>(data+mb+pb);re4dc::vp::build_lut(lut);ps2w.lut=lut;
#endif
    ps2w.gather=reinterpret_cast<re4dc::room::CompactVertex12*>(data+mb+pb+kLutBytes);
#if RE4DC_SCENERY_DEDUP
#if RE4DC_SCENERY_DEDUP==3
    dedup_open(); // same stored order, refresh the package borrow only
#else
    // the package was read again in its stored order: reorder it as at open (the strip groups stay rewritten)
    if(dedup::block){dedup::run(ps2w.package,nullptr,0,ps2w.gather,2);dedup::pkg=&ps2w.package;}
#endif
#endif
    ps2w.camera=false; // next source/coarse draw supplies the current camera
#if RE4DC_PS2_WORLD_R11F_OWNER
    r11fSidecarCrc=h.crc;
#endif
#if RE4DC_PS2_WORLD_DYNAMIC
    // Preserve ids, slots, source flags, object/serials, original rest matrices,
    // part witnesses and ordering. Same UI frame can contain source S11 edits.
    dyn::frame=~0u;dyn::nmoved=0;std::memset(dyn::state,0,sizeof(dyn::state));
#endif
    return true;
}
bool ps2_movie_dyn_valid(){
#if RE4DC_PS2_PVS
    if(pvs::block && !re4dc_room4_cell_valid(pvs::block,pvs::bytes,ps2_movie.generation))return false;
#endif
#if RE4DC_PS2_STRIP_GROUPS
    if(ps2w.sg_block && !re4dc_room4_cell_valid(ps2w.sg_block,0,ps2_movie.generation))return false;
#endif
#if RE4DC_SCENERY_DEDUP && RE4DC_SCENERY_DEDUP!=3
    if(dedup::block && !re4dc_room4_cell_valid(dedup::block,0,ps2_movie.generation))return false;
#endif
#if RE4DC_PS2_WORLD_DYNAMIC
    if(dyn::block && !re4dc_room4_cell_valid(dyn::block,0,ps2_movie.generation))return false;
#if RE4DC_ROOT_POSE_WITNESS_PREFLIGHT
    if(dyn::slots && !re4dc_room4_cell_valid(dyn::slots,dyn::slot_cell_bytes(dyn::nslots),ps2_movie.generation))return false;
    if(dyn::slots)for(unsigned i=0;i<dyn::nslots;++i){
        const dyn::Slot& s=dyn::slots[i];
        if(!s.parts)continue;
        if(s.nparts==1){if(s.parts!=dyn::reserved_pose(s))return false;}
        else if(!re4dc_room4_cell_valid(s.parts,dyn::part_cell_bytes(s.nparts),ps2_movie.generation))return false;
    }
#else
    if(dyn::slots && !re4dc_room4_cell_valid(dyn::slots,dyn::nslots*sizeof(dyn::Slot),ps2_movie.generation))return false;
#if RE4DC_PS2_WORLD_PARTS
    if(dyn::slots)for(unsigned i=0;i<dyn::nslots;++i)if(dyn::slots[i].parts &&
        !re4dc_room4_cell_valid(dyn::slots[i].parts,dyn::part_cell_bytes(dyn::slots[i].nparts),ps2_movie.generation))return false;
#endif
#endif
#endif
    return true;
}
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
} // namespace
#include "include/native_source_world_r11f.inc"
namespace {
#endif
// 1 complete, 0 a part fell back (not drawn) or the camera is unusable, -1 aborted after publishing.
#if RE4DC_SKY_ANY
// SKY_FAR (post30.mk, look study 2026-10-10): the PS2 world rows (R4PW placement field = OBJ group = SMD row) that
// hold the room's sky dome and backdrop cards, from the PS2 OBJ exports (TYPE_08 / SMX 029 rows reaching 25-56 m up
// and 60-240 m out). r100: BIN 127 / 128 / 126 (rows 2, 3, 75) and the SMX 029 treeline cards (rows 33..37);
// r101: the cloud dome BIN 1 (row 0) and the treeline BIN 2 / 7 (rows 1, 2).
static bool ps2_sky_row(unsigned room,unsigned row){
    if(room==0x100)return row==2 || row==3 || row==75 || (row>=33 && row<=37);
    if(room==0x101)return row<=2;
    return false;
}
} // namespace
extern "C" { unsigned re4dc_ps2_sky_header; } // native_ui.cpp: 1 = the next PS2 world header has its fog off
namespace {
#endif
#if RE4DC_WORLD_HOLE_DIAG
// WORLD_HOLE_DIAG (worldhole.mk, test only): why each PS2 world part that is not drawn (a pass fallback: with
// PS2_WORLD_ROOMS=2 a hole) was refused. Codes = native_ui.cpp re4dc_ps2_world_direct_begin's refusals:
// 0 draw (no bind refusal recorded), 1 nested, 2 frame not ready, 3 stream aborted (an earlier model part overflowed),
// 4 no packet storage, 5 packet store full, 6 texture not resident (load() reason in tex=), 7 texture size, 8 stream
// aborted at the list switch, 9 owner binding, 10 bad key. One WHD line per pass of a frame with refusals (the first
// part's key and the model packet use / overflow count at it), a WHDSUM line per room every 120 frames.
extern "C" unsigned re4dc_whd_take(const char** load_why,unsigned* used,unsigned* overflow); // native_ui.cpp
extern "C" unsigned re4dc_whd_abort(void** ra,unsigned* q); // native_ui.cpp: the frame's first stream abort
namespace whd {
constexpr unsigned kCodes=11,kWhy=8;
const char* const kName[kCodes]={"draw","nested","notready","aborted","storage","full","tex","size","abort2","owner","key"};
unsigned frame_code[kCodes],total[3][kCodes],parts[3],refused[3],frames_with[3],lines;
const char* why_name[kWhy];unsigned why_count[kWhy],why_frame[kWhy];
unsigned first_key[2],first_used,first_overflow,room,window_frame;
void note(unsigned pass,const unsigned* key){
    const char* lw=nullptr;unsigned used=0,ovf=0;
    unsigned code=re4dc_whd_take(&lw,&used,&ovf);
    if(code>=kCodes)code=0;
    if(!frame_code[0] && !frame_code[1] && !frame_code[2] && !frame_code[3] && !frame_code[4] && !frame_code[5] &&
       !frame_code[6] && !frame_code[7] && !frame_code[8] && !frame_code[9] && !frame_code[10]){
        first_key[0]=key[0];first_key[1]=key[1];first_used=used;first_overflow=ovf;
    }
    ++frame_code[code];++total[pass][code];++refused[pass];
    if(lw){
        unsigned i=0;while(i<kWhy && why_name[i] && why_name[i]!=lw)++i;
        if(i<kWhy){why_name[i]=lw;++why_count[i];++why_frame[i];}
    }
}
void end_pass(unsigned pass,unsigned nparts,unsigned frame,unsigned r){
    parts[pass]+=nparts;
    if(r!=room){
        for(auto& t:total)for(auto& x:t)x=0;
        for(unsigned i=0;i<kWhy;++i){why_name[i]=nullptr;why_count[i]=0;}
        parts[0]=parts[1]=parts[2]=refused[0]=refused[1]=refused[2]=frames_with[0]=frames_with[1]=frames_with[2]=0;
        room=r;window_frame=frame;
    }
    unsigned n=0;for(unsigned c=0;c<kCodes;++c)n+=frame_code[c];
    if(n){
        ++frames_with[pass];
        if(++lines<=4000){
            char tw[160];unsigned o=0;tw[0]=0;
            for(unsigned i=0;i<kWhy && why_name[i] && o<140;++i)if(why_frame[i])
                o+=snprintf(tw+o,sizeof(tw)-o,"%s%s:%u",o?",":"",why_name[i],why_frame[i]);
            re4dc_log("WHD frame=%u room=%03x pass=%u parts=%u refused=%u draw=%u nested=%u notready=%u aborted=%u storage=%u full=%u tex=%u size=%u abort2=%u owner=%u key=%u first=%08x-%08x used=%u overflow=%u texwhy=%s\n",
                frame,r,pass,nparts,n,frame_code[0],frame_code[1],frame_code[2],frame_code[3],frame_code[4],frame_code[5],
                frame_code[6],frame_code[7],frame_code[8],frame_code[9],frame_code[10],first_key[0],first_key[1],first_used,
                first_overflow,o?tw:"-");
            void* ra=nullptr;unsigned q[6]={};
            if(const unsigned kind=re4dc_whd_abort(&ra,q))
                re4dc_log("WHDABORT frame=%u room=%03x kind=%u ra=%p required=%u queue_top=%u spill_top=%u spill_cap=%u queued=%u quads=%u\n",
                    frame,r,kind,ra,q[0],q[1],q[2],q[3],q[4],q[5]);
        }
    }
    for(auto& x:frame_code)x=0;
    for(auto& x:why_frame)x=0;
    if(pass==2 && frame-window_frame>=120){
        window_frame=frame;
        for(unsigned q=0;q<3;++q)
            re4dc_log("WHDSUM frame=%u room=%03x pass=%u parts=%u refused=%u frames=%u draw=%u notready=%u aborted=%u storage=%u full=%u tex=%u size=%u abort2=%u other=%u\n",
                frame,r,q,parts[q],refused[q],frames_with[q],total[q][0],total[q][2],total[q][3],total[q][4],total[q][5],
                total[q][6],total[q][7],total[q][8],total[q][1]+total[q][9]+total[q][10]);
    }
}
}
#endif
#if defined(RE4DC_MIST_CUT)
// MIST_CUT (hwfog.mk, lane mist16 2026-10-16; esp_sub.cpp re4dc_mist_cut, render only). Bit 2: the world's translucent
// mist / backdrop cards. The chapter 1 outdoor inventory (port/dreamcast/docs/MIST_CUT.md) found one: the grey fogged
// treeline band e967b886 (r10b texture 7, staged in r10b / r11b); every other TR-pass part there is foliage, leaf litter,
// ground blend overlays or shadow decals. Bit 16 (diagnostic ceiling only, never a look): no TR-pass world part at all.
namespace mistcut{
constexpr std::uint32_t kMistParts[][2]={{0xe967b886U,0x9bd0a435U}};
static unsigned skipped,last_room;static std::uint32_t last_frame;
static bool world_part(unsigned pass,std::uint32_t crc,std::uint32_t fnv){
    if(pass!=2)return false;
#if RE4DC_WORLD_RECT21
    re4dc::rect21::origin::original(crc,fnv); // policy keys are original material keys (mipfix22)
#endif
    bool cut=(re4dc_mist_cut&16U)!=0;
    if(!cut && (re4dc_mist_cut&2U))for(const auto& k:kMistParts)cut=cut||(k[0]==crc && k[1]==fnv);
    if(!cut)return false;
    ++skipped;
    const std::uint32_t f=re4dc_vi_retrace_count();
    if(last_room!=ps2w.room || f-last_frame>=1200U){
        re4dc_log("mist cut world: mask=%u room=%03x parts=%u\n",re4dc_mist_cut,unsigned(ps2w.room),skipped);
        last_room=ps2w.room;last_frame=f;skipped=0;
    }
    return true;
}
}
#endif
#if defined(RE4DC_FOLIAGE_TRIM)
// FOLIAGE_TRIM=<level> (hwfog.mk, lane mist16 2026-10-16, user: "we should get the fixes from foliage agent in"; render
// only; unset = no code). The chapter 1 outdoor overdraw is the PS2 world's translucent (pass 2) brush / leaf cards, not
// mist (port/dreamcast/docs/MIST_CUT.md). include/foliage_keys.inc classes their texture keys offline by texel alpha:
// 1 near-invisible (max alpha < 0.1), 2 near-binary cut-out (>= 95 % of texels at 0 or >= 0.9, or max at the opaque level
// with <= 25 % mid texels: leaf / brush / branch cards, fence gaps), 3 soft but reaching the opaque level (listed, drawn as
// today), 4 soft card below the opaque level (shadow strips, mist, grass fades; drawn as today at NEAR). Surfaces without
// cut-out holes (< 10 % fully transparent texels: r109's cabin walls and floor at alpha 238, water) are not listed.
// re4dc_foliage (one .data word; a later Options row sets it): 0 FULL = today; 1 NEAR = a class 1 part is not
// drawn, a class 2 part is drawn in the punch-through list (alpha test at PT_ALPHA_REF 128, PT_BLEND_FIX header: no
// blend, no per-tile sort) and only to FOLIAGE_NEAR_MM (the cards beyond it are hidden by the fog ramp's far half);
// soft decals, shadow strips, ground blends and the vertex-alpha overlays (reserved bit 0) stay translucent;
// 2 OFF = classes 1-4 are not drawn; unlisted translucent parts (surfaces, water, keys outside the chapter 1 census) and
// the vertex-alpha overlays still are. (The first OFF dropped the whole translucent world pass, the tester's 10-16 patch:
// it removed r109's walls and floor.)
} // namespace (re4dc_foliage at file scope: option_rows.cpp and dbgwarp_bridge.cpp link to it by its C name)
extern "C" { unsigned re4dc_foliage=RE4DC_FOLIAGE_TRIM; }
namespace {
namespace foliage{
struct Key { std::uint32_t crc,fnv; unsigned level; };
constexpr Key kKeys[]={
#include "include/foliage_keys.inc"
};
constexpr float kNear=float(RE4DC_FOLIAGE_NEAR_MM);
static unsigned moved,dropped,last_room;static std::uint32_t last_frame;
// The pass a pass-2 part draws in at NEAR / OFF: 1 punch-through, 2 translucent (as today), 3 not drawn.
static unsigned pass_of(const Ps2Part& m){
    if(m.pass!=2 || re4dc_foliage-1U>1U || (m.reserved&1U))return m.pass;
#if RE4DC_WORLD_RECT21
    std::uint32_t crc=m.crc,fnv=m.fnv;
    // A scoped rect21 key (texture loading) keeps its original material's class (mipfix22).
    re4dc::rect21::origin::original(crc,fnv);
    unsigned level=0,lo=0,hi=sizeof(kKeys)/sizeof(kKeys[0]); // kKeys is sorted by crc, fnv
    while(lo<hi){
        const unsigned mid=(lo+hi)/2;const Key& k=kKeys[mid];
        if(k.crc<crc || (k.crc==crc && k.fnv<fnv))lo=mid+1;
        else{if(k.crc==crc && k.fnv==fnv)level=k.level;hi=mid;}
    }
#else
    unsigned level=0,lo=0,hi=sizeof(kKeys)/sizeof(kKeys[0]); // kKeys is sorted by crc, fnv
    while(lo<hi){
        const unsigned mid=(lo+hi)/2;const Key& k=kKeys[mid];
        if(k.crc<m.crc || (k.crc==m.crc && k.fnv<m.fnv))lo=mid+1;
        else{if(k.crc==m.crc && k.fnv==m.fnv)level=k.level;hi=mid;}
    }
#endif
    if(re4dc_foliage==2U)return level?3U:2U;
    return level==1?3U:level==2?1U:2U;
}
static void note(unsigned pass,unsigned drawn_pass){
    if(drawn_pass==3){if(pass==2)++dropped;}else if(pass==1)++moved;
    const std::uint32_t f=re4dc_vi_retrace_count();
    if(last_room!=ps2w.room || f-last_frame>=1200U){
        re4dc_log("foliage: level=%u room=%03x moved=%u dropped=%u near=%u\n",re4dc_foliage,unsigned(ps2w.room),moved,dropped,
                  unsigned(RE4DC_FOLIAGE_NEAR_MM));
        last_room=ps2w.room;last_frame=f;moved=dropped=0;
    }
}
}
#endif
int ps2_pass(unsigned pass,float zfar){
#if RE4DC_ROOT_POSE_REFUSAL_DIAG
    dyn::root_reports(); // bounded emission before any direct/chunk/SQ ownership
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    const re4dc::wc24::Scope wc_selection(re4dc::wc24::Selection);
    Wc24PassResult wc_result;
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    wc_result.why.tag(re4dc::wc24::ErrorPs2Pass,re4dc::wc24::ErrorPassIncomplete,pass);
#endif
#endif
#if RE4DC_GC_ASSET_GATE
    GcStaticSourceScope gcasset_source_scope(ps2w.asset_proof,&ps2w);
#endif
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    if(!re4dc_source_world_binding_valid()){
        wc_result.why.first(re4dc::wc24::ErrorBindingLost,pass);
        re4dc_source_world_binding_failed();return -1;
    }
#else
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return -1;}
#endif
#endif
    auto& c=ps2w.count[pass];c={};
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    wc_result.diag_fallback=&c.fallback;wc_result.diag_aborts=&c.aborts;
#endif
#if RE4DC_PS2_AREA_HIDE
    area::update();
#endif
#if RE4DC_PS2_PLACE_GATE
    gate::begin(ps2w.room);
    const bool gated=gate::owned_n && gate::room==ps2w.room;
#endif
#if RE4DC_SKY_ANY
    re4dc_ps2_sky_header=0;
#endif
    const float* P=ps2w.projection;
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    if(P[0]!=0 || ps2w.viewport[2]<=0 || ps2w.viewport[3]<=0){
        wc_result.why.first(re4dc::wc24::ErrorProjection,pass,
            unsigned(P[0]!=0)|(unsigned(ps2w.viewport[2]<=0)<<1)|(unsigned(ps2w.viewport[3]<=0)<<2));return 0;
    }
#else
    if(P[0]!=0 || ps2w.viewport[2]<=0 || ps2w.viewport[3]<=0)return 0;
#endif
    const float near=P[6]/(P[5]-1),far=P[6]/P[5];
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    if(!re4dc::render::is_finite(near)||!re4dc::render::is_finite(far)||near<=0||far<=near){
        uint32_t a,b;std::memcpy(&a,&near,4);std::memcpy(&b,&far,4);
        wc_result.why.first(re4dc::wc24::ErrorDepth,a,b);return 0;
    }
#else
    if(!re4dc::render::is_finite(near)||!re4dc::render::is_finite(far)||near<=0||far<=near)return 0;
#endif
    float cull_far=far;
    if(zfar>near && zfar<cull_far)cull_far=zfar;
#ifdef RE4DC_FAR_CAP
    if(cull_far>float(RE4DC_FAR_CAP))cull_far=float(RE4DC_FAR_CAP); // FOG_FAR_CAP (post30.mk): follows FOG_FAR
#elif defined(RE4DC_LAKE_FAR_ON)
    {const float cap=re4dc_far_cap(25000.0f);if(cull_far>cap)cull_far=cap;} // LAKE_FAR: the lakes' far
#else
    if(cull_far>25000.0f)cull_far=25000.0f; // native_ps2_world.cpp's far
#endif
#if RE4DC_NATIVE_FOG
    if(fog_now.far>near && fog_now.far<cull_far)cull_far=fog_now.far; // hidden by the fog ramp
#endif
#if RE4DC_PS2_FOLIAGE_FAR
    // PS2_FOLIAGE_FAR (game30.mk; changes the look): the PT / TR passes stop at this depth. One .data word, so arms
    // with different distances differ in that word only (a distance past the 25 m cap, e.g. 1000000, is a no-op).
    static volatile float foliage_far=float(RE4DC_PS2_FOLIAGE_FAR);
    if(pass){const float f=foliage_far;if(f>near && f<cull_far)cull_far=f;}
#endif
    c.near=near;c.far=far;c.cull_far=cull_far;
#if defined(RE4DC_TRANS_POLICY) && RE4DC_NATIVE_FOG
    if(pass)trans::frame_cuts();
#endif
#if RE4DC_SKY_ANY
    const float pass_cull_far=cull_far;
#endif
#if RE4DC_PS2_WORLD_LEAN
    lean::World lw;
    const bool lw_on=(lean::kMode&1U)!=0;
    if(lw_on)lean::world_planes(ps2w.view,P,ps2w.viewport,near,cull_far,lw);
    if(lean::kMode&2U)lean::side_setup(P,ps2w.viewport);
    lean::prime_at=nullptr;lean::primed=0; // bit 4: the prime holds within this pass only
    if(!pass){
        const unsigned f=re4dc_ui_frame();
#if defined(RE4DC_SCN_CENSUS) && RE4DC_SCN_CENSUS
        if(!(f%120)){
            re4dc_log("scnc: frame=%u meshlets=%u corners=%u corners_no_strip=%u strips=%u strips_culled=%u tris=%u all_culled_meshlets=%u sg_vskip=%u\n",
                f,scn_cen[0],scn_cen[1],scn_cen[2],scn_cen[3],scn_cen[4],scn_cen[5],scn_cen[6],lean::st.sg_vskip);
            for(unsigned& x:scn_cen)x=0;
        }
#endif
        if(!(f%120))re4dc_log("PS2LEAN frame=%u mode=%u pre_culled=%u pl_inside=%u cl_inside=%u skipped=%u prime_reuse=%u check_bad=%u prime_bad=%u dyn_fast=%u class_diff=%u sg_tests=%u sg_culled=%u sg_meshlets=%u sg_vskip=%u\n",
            f,lean::kMode,lean::st.pre_culled,lean::st.pl_inside,lean::st.cl_inside,lean::st.skipped,lean::st.prime_reuse,
            lean::st.check_bad,lean::st.prime_bad,lean::st.dyn_fast,lean::st.class_diff,lean::st.sg_tests,lean::st.sg_culled,
            lean::st.sg_meshlets,lean::st.sg_vskip);
#if RE4DC_PS2_STRIP_GROUPS && RE4DC_SG_SELECT_LEAN
        if(!(f%120))re4dc_log("SGLEAN frame=%u knob=%u on=%u calls=%u box=%u sel_bad=%u bm_bad=%u\n",f,unsigned(RE4DC_SG_SELECT_LEAN),
            unsigned(re4dc_sg_lean_on),lean::lst.calls,lean::lst.bm,lean::lst.sel_bad,lean::lst.bm_bad);
#endif
    }
#endif
#if RE4DC_PS2_WORLD_DYNAMIC
    if(!pass && dyn::ids){
        const unsigned f=re4dc_ui_frame();
        if(f-dyn::logged_frame>=120U){
            dyn::logged_frame=f;
            re4dc_log("PS2DYN frame=%u room=%03x binds=%u hidden=%u moved=%u overflow=%u\n",f,ps2w.room,dyn::binds,dyn::hidden,dyn::moved,dyn::overflow);
        }
    }
#endif
#if RE4DC_PS2_INTERIOR_CULL
    {
        // Once per frame (pass 0, or the first pass of a frame): passes 1 / 2 reuse it. With PS2_INTERIOR_ACTORS the
        // Trans-time cell is taken as is when it was set up from the same view, projection and near plane.
        const unsigned sf=re4dc_ui_frame();
        if(!pass || pc::st.done_frame!=sf){
            bool reused=false;
#if RE4DC_PS2_INTERIOR_ACTORS
            if(pcact::have && pcact::near==near && !std::memcmp(pcact::view,ps2w.view,sizeof(pcact::view)) &&
               !std::memcmp(pcact::P,P,sizeof(pcact::P))){
                const pc::State& t=pc::st_trans;pc::State& s=pc::st;
                s.active=t.active;s.cell=t.cell;s.nfr=t.nfr;s.corner=t.corner; PC_COPY_EXTRA(s,t)
                for(unsigned a=0;a<3;++a)s.eye[a]=t.eye[a];
                if(s.fr && t.fr)for(unsigned i=0;i<t.nfr;++i)s.fr[i]=t.fr[i];else s.active=false;
                if(s.active)s.setup_frame=sf;
                reused=true;++pcact::reused;
            }
#endif
            if(!reused)pc::setup(ps2w.view,P,near);
            pc::st.done_frame=sf;
        }
    }
    if(!pass){
        const unsigned frame=re4dc_ui_frame();
#if RE4DC_PS2_INTERIOR_ACTORS
        if(pcact::have){
            pcact::have=false;++pcact::view_checked;
            if(std::memcmp(pcact::view,ps2w.view,sizeof(pcact::view)))++pcact::view_mis;
        }
        if(!(frame%120))
            re4dc_log("PCACT frame=%u trans=%u active=%u tests=%u hidden=%u view=%u/%u reused=%u"
#if RE4DC_PS2_INTERIOR_CULL==2
                " boxes=%u drawn=%u unchecked=%u overflow=%u"
#endif
                "\n",frame,pcact::trans_frames,pcact::active,pcact::tests,pcact::hid,pcact::view_mis,pcact::view_checked,pcact::reused
#if RE4DC_PS2_INTERIOR_CULL==2
                ,pcact::boxes,pcact::drawn,pcact::unchecked,pcact::overflow
#endif
                );
#endif
        ++pc::st.frames;if(pc::st.active)++pc::st.active_frames;
        if(!(frame%120) || frame-pc::st.frame>=120U){
            pc::st.frame=frame;
            float e[3]={0,0,0};pc::eye_of(ps2w.view,e);
            re4dc_log("PCCULL frame=%u active=%d cell=%d eye=%d,%d,%d corner=%d portals=%u frames=%u/%u placements=%u clusters=%u meshlets=%u tests=%u\n",
                frame,int(pc::st.active),pc::st.cell,int(e[0]),int(e[1]),int(e[2]),int(pc::st.corner),pc::st.nfr,pc::st.active_frames,pc::st.frames,
                pc::st.placements,pc::st.clusters,pc::st.meshlets,pc::st.tests);
#if RE4DC_PS2_INTERIOR_OWNER
            re4dc_log("PCOWN frame=%u tests=%u hidden=%u\n",frame,pcact::owner_tests,pcact::owner_hid);
#endif
        }
#if RE4DC_PS2_INTERIOR_CULL==2
        else {
            // =2: every frame's eye (coverage of the sub-cells along a walk)
            float e[3]={0,0,0};pc::eye_of(ps2w.view,e);
            const float* v=ps2w.view;
            re4dc_log("PCEYE frame=%u active=%d cell=%d eye=%d,%d,%d corner=%d view=%d,%d,%d,%d,%d,%d,%d,%d,%d P=%d,%d,%d,%d\n",frame,int(pc::st.active),pc::st.cell,
                int(e[0]),int(e[1]),int(e[2]),int(pc::st.corner),int(v[0]*1e4f),int(v[1]*1e4f),int(v[2]*1e4f),int(v[4]*1e4f),int(v[5]*1e4f),int(v[6]*1e4f),
                int(v[8]*1e4f),int(v[9]*1e4f),int(v[10]*1e4f),int(P[1]*1e4f),int(P[2]*1e4f),int(P[3]*1e4f),int(P[4]*1e4f));
        }
#endif
    }
#endif
#if RE4DC_PS2_PVS
    pvs::frame(ps2w.view,P,ps2w.viewport,near,cull_far);
    if(!pass){
        const unsigned f=re4dc_ui_frame();
        if(!(f%120) && pvs::logged!=f){
            pvs::logged=f;
            re4dc_log("PS2PVS frame=%u on=%u file=%s cell=%d eye=%d,%d,%d active=%u/%u placements=%u/%u admitted_clusters=%u/%u prefix=%x commits=%u\n",f,
                unsigned(re4dc_ps2_pvs_on),pvs::why?pvs::why:"ok",pvs::cur_cell,int(pvs::eye[0]),int(pvs::eye[1]),int(pvs::eye[2]),
                pvs::active,pvs::frames,pvs::pl_skipped,pvs::pl_tested,pvs::cl_skipped,pvs::cl_tested,proof23::receipts.committed,proof23::commits);
        }
    }
    if(!pass && re4dc_ps2_pvs_on==2U){
        // pvs 2 (measurement): no set, and this frame's camera for the offline occlusion count (pvs_ceiling.py)
        std::uint32_t w[25];std::memcpy(w,ps2w.view,48);std::memcpy(w+12,P,28);std::memcpy(w+19,ps2w.viewport,24);
        std::uint32_t far_bits;std::memcpy(&far_bits,&cull_far,sizeof(far_bits));
        re4dc_log("PS2CAM f=%u cf=%08x c=%08x %08x %08x %08x %08x %08x %08x %08x %08x %08x %08x %08x p=%08x %08x %08x %08x %08x %08x %08x vp=%08x %08x %08x %08x %08x %08x\n",
            re4dc_ui_frame(),unsigned(far_bits),w[0],w[1],w[2],w[3],w[4],w[5],w[6],w[7],w[8],w[9],w[10],w[11],
            w[12],w[13],w[14],w[15],w[16],w[17],w[18],w[19],w[20],w[21],w[22],w[23],w[24]);
    }
#endif
#if defined(RE4DC_SCENERY_STREAM_CHECK) && RE4DC_SCENERY_STREAM_CHECK
    if(!pass){
        static unsigned logged=0;const unsigned f=re4dc_ui_frame();
        if(f-logged>=300U){logged=f;
            re4dc_log("SCNSTREAM check frame=%u room=%03x picks=%u corners=%u bad=%u screens=%u screen_bad=%u\n",f,ps2w.room,stream_ck[0],stream_ck[1],
                      stream_ck[2],stream_ls[0],stream_ls[1]);}
    }
#endif
#if RE4DC_SCENERY_CONE
    if(!pass){
        const unsigned f=re4dc_ui_frame();
        if(f-cone::logged>=600U){
            cone::logged=f;
            re4dc_log("SCN21 cone frame=%u room=%03x on=%u tests=%u rejects=%u picks_dropped=%u vskip=%u\n",f,ps2w.room,
                      cone::pkg?1U:0U,cone::tests,cone::rejects,cone::picks_dropped,cone::vskip);
        }
    }
#endif
    Re4dcModelPart part{};
    std::memcpy(part.projection,P,sizeof(part.projection));std::memcpy(part.viewport,ps2w.viewport,sizeof(part.viewport));
    part.alpha_state=255;part.source_key[2]=1;
#if RE4DC_SCENERY_CHUNK
    // SCENERY_CHUNK: the selected parts of this run (ChunkPart) and their picks, emitted in order by chunk_flush()
    // before any part that takes the ordinary path, when either list is full, and at the end of the pass.
    struct ChunkPart { float mvq[12]; unsigned key[6]; float cull_far,lod_scale; unsigned index,first,count;
#if RE4DC_SCENERY_UV_SNAPSHOT
                       float uv_offset[2];
#endif
#if RE4DC_PS2_PVS
                       unsigned placement;
#endif
                       std::uint8_t cull; bool marked; std::uint8_t sky; };
    static constexpr unsigned kChunkParts=48,kChunkPicks=320;
    ChunkPart cctx[kChunkParts];MeshDraw::Pick cpk[kChunkPicks];unsigned nctx=0,npk=0;
    const auto& cpkg=ps2w.package;
    auto chunk_flush=[&]()->int{
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        const re4dc::wc24::Scope wc_replay(re4dc::wc24::Other);
#endif
#if RE4DC_SCENERY_REPLAY_LEAN
        if(!nctx){npk=0;return 1;}
#endif
        // The pending selection/ordinary draw references this shared record.
        // Queued emitters borrow its cull; restore the pending part on every exit.
        struct CullScope {
            unsigned& value;unsigned saved;
            ~CullScope(){value=saved;}
        } cull_scope{part.cull,part.cull};
#if RE4DC_SCENERY_UV_SNAPSHOT
        // A capacity drain may run after the next owner's UV was prepared.
        // Restore that pending draw's bits on normal and abort exits alike.
        // Component copies are plain SH4 moves; -Os calls memcpy even for 8 B.
        struct UvScope {
            float* value;float saved[2];
            explicit UvScope(float* p):value(p),saved{p[0],p[1]}{}
            ~UvScope(){value[0]=saved[0];value[1]=saved[1];}
        } uv_scope(part.uv_offset);
#endif
#if RE4DC_SCENERY_SUBMIT_BATCH
        // Only this synchronous replay owns the borrowed lock. Selection,
        // ordinary draws, aborts and returning to the source never retain it.
        struct SubmitScope {
            Re4dcWorldSubmitBatch batch{};
            ~SubmitScope(){re4dc_ps2_world_batch_close(&batch);}
        } submit_scope;
#endif
#if RE4DC_SKY_ANY
        const unsigned sky_now=re4dc_ps2_sky_header; // the placement being selected keeps its own after the run
#endif
#if RE4DC_SCENERY_REPLAY_LEAN
        // One full context per synchronous replay. Only UV fields of MeshPart
        // are read by chunk_emit/borrow; selection/run still use their own part.
        // Keep a stable reference to these four current-part values without
        // changing the shared renderer's part-reference layout or hot methods.
        re4dc::room::MeshPart replay_part{};
        MeshDraw e{{part,{},near,far},cpkg,replay_part,ps2w.lut,ps2w.gather};
        e.alpha=0xff000000U;e.direct=true;e.lean_part=true;
        e.sg=ps2w.sg;e.sg_groups=ps2w.sg_groups;
        e.streaming=re4dc_model_packet_streaming()!=0;e.set_clip();
#if RE4DC_SCENERY_SUBMIT_BATCH
        e.submit_batch=&submit_scope.batch;
#endif
#endif
        for(unsigned j=0;j<nctx;++j){
            const ChunkPart& x=cctx[j];
            part.cull=x.cull;
#if RE4DC_SCENERY_UV_SNAPSHOT
            part.uv_offset[0]=x.uv_offset[0];part.uv_offset[1]=x.uv_offset[1];
#endif
#if RE4DC_SKY_ANY
            re4dc_ps2_sky_header=x.sky;
#endif
#if RE4DC_SCENERY_REPLAY_LEAN
            const auto& active_part=cpkg.parts()[x.index];
            replay_part.uv_bias[0]=active_part.uv_bias[0];replay_part.uv_bias[1]=active_part.uv_bias[1];
            replay_part.uv_scale[0]=active_part.uv_scale[0];replay_part.uv_scale[1]=active_part.uv_scale[1];
            e.chunk_restart();
#if RE4DC_PS2_VERTEX_ALPHA
            e.lut=x.marked&&ps2w.lut?ps2_vertex_alpha_lut():ps2w.lut;
            e.vertex_alpha=x.marked;e.c4444=x.marked;
#endif
            e.part_index=x.index;
#else
#if RE4DC_PS2_VERTEX_ALPHA
            MeshDraw e{{part,{},near,far},cpkg,cpkg.parts()[x.index],x.marked&&ps2w.lut?ps2_vertex_alpha_lut():ps2w.lut,ps2w.gather};
            e.alpha=0xff000000U;e.vertex_alpha=x.marked;e.c4444=x.marked;e.cull_far=x.cull_far;e.direct=true;
#else
            MeshDraw e{{part,{},near,far},cpkg,cpkg.parts()[x.index],ps2w.lut,ps2w.gather};
            e.alpha=0xff000000U;e.vertex_alpha=false;e.cull_far=x.cull_far;e.direct=true;
#endif
            e.part_index=x.index;e.lod_scale=x.lod_scale;e.lean_part=true;
#endif
#if RE4DC_SCENERY_SUBMIT_BATCH && !RE4DC_SCENERY_REPLAY_LEAN
            e.submit_batch=&submit_scope.batch;
#endif
#if RE4DC_PS2_PVS
            e.pvs_placement=x.placement;
#endif
#if !RE4DC_SCENERY_REPLAY_LEAN
            e.sg=ps2w.sg;e.sg_groups=ps2w.sg_groups;
            std::memcpy(e.mvq,x.mvq,sizeof(x.mvq));std::memcpy(e.mv,x.mvq,sizeof(x.mvq));e.ps2=x.key;
#else
            // mv is used by bounds/selection only; emit_pick and the clipper
            // consume mvq. The queued snapshot remains owned by this flush.
            std::memcpy(e.mvq,x.mvq,sizeof(x.mvq));e.ps2=x.key;
#endif
#if RE4DC_SCENERY_PIECE_STATE
            e.piece_slot=piece::pkg==static_cast<const void*>(&cpkg)?piece::table+x.index:nullptr;
#endif
#if RE4DC_SCENERY_EMIT_PREFETCH
            // Picks are packed even when an intervening part has no picks.
            // Never look beyond this flush or change the selected draw order.
            const unsigned next=x.first+x.count;
            const int result=e.chunk_emit(cpk+x.first,x.count,next<npk?cpk+next:nullptr);
#else
            const int result=e.chunk_emit(cpk+x.first,x.count);
#endif
            e.end_direct();
#if RE4DC_SCENERY_SUBMIT_BATCH
#if RE4DC_PS2_PVS_BATCH_COMPOSE
            // Logical completion/accounting precedes release. Only actual
            // source witnesses drain; opaque_ready remains outside SQ.
            if(result<=0 || e.pvs_pending[2])re4dc_ps2_world_batch_close(&submit_scope.batch);
#else
            if(result<=0)re4dc_ps2_world_batch_close(&submit_scope.batch);
#endif
#endif
#if RE4DC_PS2_PVS
            e.pvs_finish(result>0);
#endif
            if(result>0)++c.native;
            else if(result<0){re4dc_model_packet_abort();++c.aborts;nctx=npk=0;return -1;}
#if RE4DC_WORLD_HOLE_DIAG
            else {++c.fallback;whd::note(pass,x.key);}
#else
            else ++c.fallback;
#endif
        }
        nctx=npk=0;
#if RE4DC_SKY_ANY
        re4dc_ps2_sky_header=sky_now;
#endif
        return 1;
    };
#endif
    const float px_x=RE4DC_SCREEN_HALF_WF*std::fabs(P[1]),px_y=RE4DC_SCREEN_HALF_HF*std::fabs(P[3]);
    const float px=px_x>px_y?px_x:px_y;
#if RE4DC_QUALITY
    const float lod_px=re4dc_quality()->lod_px;
#else
    const float lod_px=float(RE4DC_MESH_LOD_PX);
#endif
#ifdef RE4DC_SCENERY_FAR_LOD
    // SCENERY_FAR_LOD=<n> (scenery19, approximation): the PS2 world takes coarser levels sooner; the allowed
    // projected error is n times the quality setting's (lod_px), so distant clusters swap to far levels.
    const float lod_div=lod_px*float(RE4DC_SCENERY_FAR_LOD);
#else
    const float lod_div=lod_px;
#endif
    const auto& pk=ps2w.package;
    for(unsigned i=0;i<ps2w.nplacements;++i){
#if RE4DC_PS2_PVS
#if RE4DC_PS2_PVS_BATCH_COMPOSE
        // Qualification mode ONLY: internal pvs::cur still authenticates source
        // observation, but never supplies legacy target-hide/selector authority.
        const std::uint8_t* const pvs_cur=nullptr;
#else
        const std::uint8_t* const pvs_cur=pvs::can_cut(i)?pvs::cur:nullptr;
#endif
#endif
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
        if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();++c.aborts;return -1;}
#endif
#if RE4DC_PS2_PASS_MASK==2
        if(ps2w.masked){
            // =2 (diagnostic): the scan beside the mask bit.
            const auto& m=pk.meshes()[ps2w.placements[i].mesh];
            bool any=false;
            for(unsigned k=0;k<m.part_count && !any;++k)any=ps2w.parts[m.first_part+k].pass==pass;
            ++ps2_mask_stats[0];
            if(any!=(((ps2w.pass_mask[i]>>pass)&1U)!=0))++ps2_mask_stats[1];
        }
#endif
#if defined(RE4DC_FOLIAGE_TRIM) && RE4DC_FOLIAGE_NEAR_FIX
        // FOLIAGE_NEAR_FIX (hwfog.mk, lane lake17): at NEAR the cut-out cards of pass 2 draw in pass 1, so a placement
        // whose cards are its only pass-1 candidates must not be skipped by the pass scan below (without this, NEAR drew
        // no card that sits in a translucent-only placement: Near looked like Off). The per-part pass_of test decides.
        const unsigned pass_bits=(1U<<pass)|((pass==1 && re4dc_foliage==1U)?4U:0U);
#define RE4DC_PASS_HIT(p) (((pass_bits>>(p))&1U)!=0)
#else
#define RE4DC_PASS_HIT(p) ((p)==pass)
#endif
#if RE4DC_PS2_PASS_MASK
        const bool masked=ps2w.masked && RE4DC_PS2_MASK_ON;
#if defined(RE4DC_FOLIAGE_TRIM) && RE4DC_FOLIAGE_NEAR_FIX
        if(masked && !(ps2w.pass_mask[i]&pass_bits))continue;
#else
        if(masked && !((ps2w.pass_mask[i]>>pass)&1U))continue;
#endif
#endif
        const auto& pl=ps2w.placements[i];const auto& mesh=pk.meshes()[pl.mesh];
#if RE4DC_PS2_PVS
        if(pvs_cur && pvs::hidden(i))continue;
#endif
#if RE4DC_PS2_AREA_HIDE
        if(area::cur && area::hide(pl.placement)){++area::skipped;continue;}
#endif
#if RE4DC_PS2_PLACE_GATE
        if(gated && gate::skip(pl.placement)){++gate::skipped;continue;}
#endif
#if RE4DC_PS2_PASS_MASK
        if(!masked)
#endif
        {
        bool any=false;
        for(unsigned k=0;k<mesh.part_count && !any;++k)any=RE4DC_PASS_HIT(ps2w.parts[mesh.first_part+k].pass);
#if defined(RE4DC_TRANS_POLICY)
        // TRANS_POLICY FLAT / CARD / SOFTA: a translucent-only placement can hold parts that now draw in pass 0 or 1
        for(unsigned k=0;pass<2 && k<mesh.part_count && !any;++k)any=trans::candidate(mesh.first_part+k,pass);
#endif
        if(!any)continue;
        }
#undef RE4DC_PASS_HIT
#if RE4DC_PS2_WORLD_DYNAMIC
        const float* affine=pl.affine;float moved_affine[12];
        // The r11f owner admits only the whole immutable authored group.
        // Its baked placements need no dynamic slot or source-pointer reads.
        if(
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
           !re4dc_source_world_group_claimed() &&
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
           !r11fNativeClaimed() &&
#endif
           dyn::ids && pl.placement<dyn::nids){
            const unsigned id=dyn::ids[pl.placement];
            if(id<dyn::kIds && dyn::slot_of[id]!=dyn::kNone){
                const unsigned st=dyn::query(id);
                if(st==1
#if RE4DC_PS2_WORLD_PARTS
                    || st==3
#endif
                )continue;   // hidden, or drawn with its source part hierarchy
                if(st==2){concat(dyn::delta[dyn::moved_of[id]],pl.affine,moved_affine);affine=moved_affine;}
#if RE4DC_ROOT_POSE_CAP_FALLBACK
                else if(st==4){
                    const int result=dyn::root_affine(id,pl.affine,moved_affine);
                    if(!result)continue;
                    if(result==2)affine=moved_affine;
                }
#endif
            }
        }
#if RE4DC_PS2_WORLD_LEAN
        ++c.placements;
#define RE4DC_PS2_AFFINE affine
#else
        ++c.placements;
        float mv[12];concat(ps2w.view,affine,mv);
#define RE4DC_PS2_AFFINE affine
#endif
#else
        ++c.placements;
#if !RE4DC_PS2_WORLD_LEAN
        float mv[12];concat(ps2w.view,pl.affine,mv);
#endif
#define RE4DC_PS2_AFFINE pl.affine
#endif
#if RE4DC_PS2_PVS
        // A receipt must describe the immutable baked geometry actually selected.
        // Capture this with mvq; fresh source state can change before queued replay.
        const unsigned pvs_source_placement=(RE4DC_PS2_AFFINE==pl.affine)?i:~0U;
#endif
#if RE4DC_PS2_WORLD_LEAN
#if RE4DC_SKY_ANY
        const bool lean_sky=re4dc_sky_mode() && ps2_sky_row(ps2w.room,pl.placement); // sky rows: their own far, no pretest
#else
        constexpr bool lean_sky=false;
#endif
        if(lw_on && !lean_sky && lean::world_out(lw,RE4DC_PS2_AFFINE,mesh.bounds_min,mesh.bounds_max)){++c.culled;++lean::st.pre_culled;continue;}
#if RE4DC_SCENERY_UNIT_CONCAT
        float mv[12];
        {   // SCENERY_UNIT_CONCAT (scenery19.mk; exact): a placement whose rotation / scale part is exactly the identity
            // (the Ninja guide's NJD_EVAL_UNIT_ANG / SCL) gives concat_u's result without its products: each of
            // the 3x3 elements is a + 0.0f (a * 1 is exact, the two +-0 products leave a non-zero a as it is, and the
            // trailing + 0.0f turns -0 into +0 as concat_u does); the translation column keeps concat_u's expression.
            const float* b=RE4DC_PS2_AFFINE;const float* a=ps2w.view;
            if(b[0]==1.0f && b[5]==1.0f && b[10]==1.0f && b[1]==0.0f && b[2]==0.0f && b[4]==0.0f && b[6]==0.0f &&
               b[8]==0.0f && b[9]==0.0f){
                for(unsigned r=0;r<3;++r){
                    mv[4*r]=a[4*r]+0.0f;mv[4*r+1]=a[4*r+1]+0.0f;mv[4*r+2]=a[4*r+2]+0.0f;
                    mv[4*r+3]=a[4*r]*b[3]+a[4*r+1]*b[7]+a[4*r+2]*b[11]+a[4*r+3];
                }
            }else lean::concat_u(a,b,mv);
        }
#else
        float mv[12];lean::concat_u(ps2w.view,RE4DC_PS2_AFFINE,mv);
#endif
        if(lean::kMode&8U){float r[12];concat(ps2w.view,RE4DC_PS2_AFFINE,r);if(std::memcmp(r,mv,sizeof(r)))++lean::st.check_bad;}
#endif
        const re4dc::render::DrawBounds bounds{{mesh.bounds_min[0],mesh.bounds_min[1],mesh.bounds_min[2]},
                                               {mesh.bounds_max[0],mesh.bounds_max[1],mesh.bounds_max[2]}};
#if RE4DC_SKY_ANY
        // SKY_FAR (post30.mk, look study): the room's sky / backdrop rows draw to the projection far.
        const unsigned sky_mode=re4dc_sky_mode();
        const bool sky=sky_mode && ps2_sky_row(ps2w.room,pl.placement);
        const float cull_far=sky?far:pass_cull_far;
        re4dc_ps2_sky_header=(sky_mode==2 && sky)?1U:0U;
#endif
#if RE4DC_PS2_WORLD_LEAN
        unsigned lean_in;
        if(lean::kMode&2U){
            const float grow[3]={std::fabs(mesh.step[0]),std::fabs(mesh.step[1]),std::fabs(mesh.step[2])}; // cluster boxes round out by < 1 step
            float am[9];lean::abs9(mv,am);
            lean_in=lean::box_class(mesh.bounds_min,mesh.bounds_max,mv,am,near,cull_far,grow);
            if((lean::kMode&8U) && (lean_in!=0)!=re4dc::render::group_visible(bounds,mv,P,ps2w.viewport,near,cull_far,0))++lean::st.class_diff;
        }else lean_in=re4dc::render::group_visible(bounds,mv,P,ps2w.viewport,near,cull_far,0)?1U:0U;
        if(!lean_in){++c.culled;continue;}
        if(lean_in==2)++lean::st.pl_inside;
#else
        if(!re4dc::render::group_visible(bounds,mv,P,ps2w.viewport,near,cull_far,0)){++c.culled;continue;}
#endif
        const float grid[12]={mesh.step[0],0,0,mesh.origin[0], 0,mesh.step[1],0,mesh.origin[1], 0,0,mesh.step[2],mesh.origin[2]};
#if RE4DC_PS2_INTERIOR_CULL
        // 0 no test (no cell, or the placement is inside the house box), 1 test its clusters, 2 wholly hidden.
        unsigned pc_state=0;float pc_wq[21];
        if(pc::st.active){
            float wc[3],wh[3];
            const float blo[3]={mesh.bounds_min[0],mesh.bounds_min[1],mesh.bounds_min[2]},bhi[3]={mesh.bounds_max[0],mesh.bounds_max[1],mesh.bounds_max[2]};
            pc::world_box(RE4DC_PS2_AFFINE,blo,bhi,wc,wh);
            bool inside=true; // the placement box inside the house box: nothing in it can be outside
            for(unsigned a=0;a<3;++a)inside=inside && wc[a]-wh[a]>=PC_OUTER_RENDER[a] && wc[a]+wh[a]<=PC_OUTER_RENDER[3+a];
            if(!inside){
                pc_state=pc::hidden(wc,wh)>0?2U:1U;
                concat(RE4DC_PS2_AFFINE,grid,pc_wq);pc::abs_rows(pc_wq);
            }
#if RE4DC_PS2_INTERIOR_CULL!=2
            if(pc_state==2){++pc::st.placements;continue;}
#endif
        }
#endif
#if RE4DC_PS2_WORLD_LEAN
        float mvq[12];lean::concat_u(mv,grid,mvq);
        if(lean::kMode&8U){float r[12];concat(mv,grid,r);if(std::memcmp(r,mvq,sizeof(r)))++lean::st.check_bad;}
        float amq[9];if(lean::kMode&2U)lean::abs9(mvq,amq);
#else
        float mvq[12];concat(mv,grid,mvq);
#endif
        float scale=0;
        for(unsigned r=0;r<3;++r){
            const float n=mv[4*r]*mv[4*r]+mv[4*r+1]*mv[4*r+1]+mv[4*r+2]*mv[4*r+2];
            if(n>scale)scale=n;
        }
        const float lod_scale=std::sqrt(scale)*px/lod_div;
        for(unsigned k=0;k<mesh.part_count;++k){
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
            if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();++c.aborts;return -1;}
#endif
            const unsigned index=mesh.first_part+k;const auto& meta=ps2w.parts[index];
#if RE4DC_PS2_WORLD_R11F_OWNER
            R11fUvScope uvScope(part,pl.placement,pl.mesh,index,pass);
#endif
#if defined(RE4DC_FOLIAGE_TRIM)
            const unsigned foliage_pass=foliage::pass_of(meta);
            if(foliage_pass!=meta.pass && (pass==1 || pass==2))foliage::note(pass,foliage_pass);
#if defined(RE4DC_TRANS_POLICY)
            const unsigned trans_pass=trans::pass_of(meta,index,foliage_pass);
            if(trans_pass!=foliage_pass)trans::note(pass,trans_pass);
            if(trans_pass!=pass)continue;
#else
            if(foliage_pass!=pass)continue;
#endif
#elif defined(RE4DC_TRANS_POLICY)
            const unsigned trans_pass=trans::pass_of(meta,index,meta.pass);
            if(trans_pass!=meta.pass)trans::note(pass,trans_pass);
            if(trans_pass!=pass)continue;
#else
            if(meta.pass!=pass)continue;
#endif
#if defined(RE4DC_MIST_CUT)
            if(mistcut::world_part(pass,meta.crc,meta.fnv))continue;
#endif
            ++c.parts;part.cull=meta.cull;
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
            // Offset belongs to this exact placement/part draw, never its
            // shared texture key, cached header or package metadata.
            if(!re4dc_source_world_uv(pl.placement,pl.mesh,index,pass,part.uv_offset)){
                re4dc_source_world_binding_failed();++c.aborts;return -1;
            }
#endif
#if RE4DC_SCENERY_SELECT_ONLY
            {
                ScenerySelector d{part,pk,mvq,near,cull_far};
                d.part_index=index;d.lod_scale=lod_scale;
                d.lean_inside=lean_in==2;d.lean_am=(lean::kMode&2U)?amq:nullptr;
                d.sg=ps2w.sg;d.sg_groups=ps2w.sg_groups;
#if RE4DC_PS2_PVS
                d.pvs_set=pvs_cur;
#endif
#if RE4DC_PS2_INTERIOR_CULL
                d.pc_mode=pc_state?1U:0U;
#endif
                const auto& selected_part=pk.parts()[index];
                if(d.chunk_ok() && selected_part.meshlet_count<=kChunkPicks){
#if RE4DC_PS2_VERTEX_ALPHA
                    const bool marked=(meta.reserved&1U)!=0;
                    // Keep the original lazy LUT preparation at selection.
                    if(marked && ps2w.lut)(void)ps2_vertex_alpha_lut();
#else
                    const bool marked=false;
#endif
#if defined(RE4DC_FOLIAGE_TRIM)
                    const bool foliage_near=foliage_pass!=meta.pass && foliage::kNear<cull_far;
#endif
#include "include/scenery_part_far.inc"
                    const unsigned key[6]={meta.crc,meta.fnv,meta.width,meta.height,pass,meta.cull};d.ps2=key;
#if RE4DC_PS2_INTERIOR_ACTORS && RE4DC_PS2_INTERIOR_CULL==2
                    if(!pass && !pcact::have_key){std::memcpy(pcact::key,key,sizeof(key));pcact::key[5]=0;pcact::have_key=true;}
#endif
                    // Preserve the original capacity flush and queue snapshot.
                    if(nctx==kChunkParts || npk+selected_part.meshlet_count>kChunkPicks){if(chunk_flush()<0)return -1;}
                    ChunkPart& x=cctx[nctx++];
                    std::memcpy(x.mvq,mvq,sizeof(mvq));std::memcpy(x.key,key,sizeof(key));
#if RE4DC_SCENERY_UV_SNAPSHOT
                    x.uv_offset[0]=part.uv_offset[0];x.uv_offset[1]=part.uv_offset[1];
#endif
                    x.cull_far=d.cull_far;x.lod_scale=lod_scale;x.index=index;x.cull=meta.cull;
#if RE4DC_PS2_PVS
                    x.placement=pvs_source_placement;
#endif
                    x.marked=marked;x.first=npk;
#if RE4DC_SKY_ANY
                    x.sky=std::uint8_t(re4dc_ps2_sky_header);
#endif
                    x.count=d.chunk_select(cpk+npk);npk+=x.count;
                    continue;
                }
            }
#endif
#if RE4DC_PS2_VERTEX_ALPHA
            const bool marked=(meta.reserved&1U)!=0; // a --vertex-alpha tr4 part: ARGB4444 corners, alpha kept
            MeshDraw d{{part,{},near,far},pk,pk.parts()[index],
                       marked&&ps2w.lut?ps2_vertex_alpha_lut():ps2w.lut,ps2w.gather};
            d.alpha=0xff000000U;d.vertex_alpha=marked;d.c4444=marked;d.cull_far=cull_far;d.direct=true;
#else
            MeshDraw d{{part,{},near,far},pk,pk.parts()[index],ps2w.lut,ps2w.gather};
            d.alpha=0xff000000U;d.vertex_alpha=false;d.cull_far=cull_far;d.direct=true;
#endif
            d.part_index=index;d.lod_scale=lod_scale;
#if RE4DC_PS2_PVS
            d.pvs_placement=pvs_source_placement;
#endif
#if defined(RE4DC_FOLIAGE_TRIM)
            const bool foliage_near=foliage_pass!=meta.pass && foliage::kNear<cull_far;
#endif
#if RE4DC_PS2_PVS
            if(pvs_cur){d.pvs_set=pvs_cur;d.pvs_first=pvs::base[i]+pvs::poff[index];}
#endif
#if RE4DC_PS2_WORLD_LEAN
            d.lean_inside=lean_in==2;d.lean_part=true;d.lean_am=(lean::kMode&2U)?amq:nullptr;
#if RE4DC_PS2_STRIP_GROUPS
            d.sg=ps2w.sg;d.sg_groups=ps2w.sg_groups;
#endif
#endif
#include "include/scenery_part_far.inc"
            std::memcpy(d.mvq,mvq,sizeof(mvq));std::memcpy(d.mv,mvq,sizeof(mvq));
            const unsigned key[6]={meta.crc,meta.fnv,meta.width,meta.height,pass,meta.cull};d.ps2=key;
#if RE4DC_SCENERY_PIECE_STATE
            d.piece_slot=piece::pkg==static_cast<const void*>(&pk)?piece::table+index:nullptr;
#endif
#if RE4DC_PS2_INTERIOR_ACTORS && RE4DC_PS2_INTERIOR_CULL==2
            if(!pass && !pcact::have_key){std::memcpy(pcact::key,key,sizeof(key));pcact::key[5]=0;pcact::have_key=true;}
#endif
#if RE4DC_PS2_INTERIOR_CULL
            d.pc_mode=pc_state?1U:0U;d.pc_wq=pc_wq;
#endif
#if RE4DC_SCENERY_CHUNK
            // SCENERY_CHUNK: select now, emit with the run (chunk_flush), in order.
#if !RE4DC_SCENERY_SELECT_ONLY
            if(d.chunk_ok() && d.part.meshlet_count<=kChunkPicks){
                if(nctx==kChunkParts || npk+d.part.meshlet_count>kChunkPicks){if(chunk_flush()<0)return -1;}
                ChunkPart& x=cctx[nctx++];
                std::memcpy(x.mvq,mvq,sizeof(mvq));std::memcpy(x.key,key,sizeof(key));
#if RE4DC_SCENERY_UV_SNAPSHOT
                x.uv_offset[0]=part.uv_offset[0];x.uv_offset[1]=part.uv_offset[1];
#endif
                x.cull_far=d.cull_far;x.lod_scale=lod_scale;x.index=index;x.cull=meta.cull;
#if RE4DC_PS2_PVS
                x.placement=pvs_source_placement;
#endif
                x.marked=d.vertex_alpha;x.first=npk;
#if RE4DC_SKY_ANY
                x.sky=std::uint8_t(re4dc_ps2_sky_header);
#endif
                x.count=d.chunk_select(cpk+npk);npk+=x.count;
                continue;
            }
#endif
            if(chunk_flush()<0)return -1;
#endif
#if RE4DC_PS2_INTERIOR_CULL
#if RE4DC_PS2_INTERIOR_CULL==2
            if(pc_state==2)d.pc_mode=0;
            const int result=pc_state==2?1:d.run(); // =2: the hidden placement is drawn by the check run only
            if(pc_state!=2)d.end_direct();
#else
            const int result=d.run();
            d.end_direct(); // before any abort: releases the store queues
#endif
#else
            const int result=d.run();
            d.end_direct(); // before any abort: releases the store queues
#endif
#if RE4DC_PS2_PVS
            d.pvs_finish(result>0);
#endif
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
            part.uv_offset[0]=part.uv_offset[1]=0.f;
            if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();++c.aborts;return -1;}
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
            if(r11fNativeClaimed() && !re4dc_r11f_binding_valid()) {
                re4dc_r11f_binding_failed();++c.aborts;return -1;
            }
#endif
            if(result>0)++c.native;
            else if(result<0){re4dc_model_packet_abort();++c.aborts;return -1;}
#if RE4DC_WORLD_HOLE_DIAG
            else {++c.fallback;whd::note(pass,key);}
#else
            else ++c.fallback;
#endif
#if RE4DC_PS2_INTERIOR_CULL==2
            if(pc_state){
                // The check run: only the hidden clusters / meshlets, opaque magenta, untextured and unfogged.
                MeshDraw k{{part,{},near,far},pk,pk.parts()[index],ps2w.lut,ps2w.gather};
                k.alpha=0xff000000U;k.vertex_alpha=false;k.cull_far=cull_far;k.direct=true;
                k.part_index=index;k.lod_scale=lod_scale;
                std::memcpy(k.mvq,mvq,sizeof(mvq));std::memcpy(k.mv,mvq,sizeof(mvq));
                k.ps2=key;k.pc_mode=2;k.pc_wq=pc_wq;k.pc_all=pc_state==2;k.pc_check=true;
                re4dc_ps2_check_header=1;
                const int checked=k.run();
                k.end_direct();
                re4dc_ps2_check_header=0;
                if(checked<0){re4dc_model_packet_abort();++c.aborts;return -1;}
                if(pc_state==2)++pc::st.placements;
            }
#endif
        }
    }
#if RE4DC_SCENERY_CHUNK
    if(chunk_flush()<0)return -1;
#endif
#if RE4DC_PS2_INTERIOR_ACTORS && RE4DC_PS2_INTERIOR_CULL==2
    if(!pass && pcact::nbox && pcact::have_key){
        // The actor check: each queued box (an actor the cell would have skipped) as six opaque magenta quads.
        const float* v=ps2w.view;const float* V=ps2w.viewport;
        Re4dcModelDirect out{};
        re4dc_ps2_check_header=1;
        const bool bound=re4dc_ps2_world_direct_begin(pcact::key,&out)!=0;
        re4dc_ps2_check_header=0;
        if(bound){
            std::uint32_t* sq=out.sq;unsigned slots=0;
            auto* buf=static_cast<pvr_vertex_t*>(out.scratch);
            for(unsigned b=0;b<pcact::nbox;++b){
                const auto& bx=pcact::box[b];
                float s[8][3];bool ok=true;
                for(unsigned k=0;k<8 && ok;++k){
                    const float w[3]={(k&1)?bx.hi[0]:bx.lo[0],(k&2)?bx.hi[1]:bx.lo[1],(k&4)?bx.hi[2]:bx.lo[2]};
                    const float x=v[0]*w[0]+v[1]*w[1]+v[2]*w[2]+v[3],y=v[4]*w[0]+v[5]*w[1]+v[6]*w[2]+v[7],
                                z=v[8]*w[0]+v[9]*w[1]+v[10]*w[2]+v[11];
                    if(!(-z>near*1.01f)){ok=false;break;}
                    const float inv=1.0f/(-z);
                    s[k][0]=(V[2]*.5f*(P[1]*x+P[2]*z)*inv+V[0]+V[2]*.5f)*RE4DC_SCREEN_WF/V[2];
                    s[k][1]=(-V[3]*.5f*(P[3]*y+P[4]*z)*inv+V[1]+V[3]*.5f)*RE4DC_SCREEN_HF/V[3];
                    s[k][2]=inv;
                }
                if(!ok || out.scratch_capacity<24){++pcact::unchecked;continue;}
                // faces as strips a,b,c,d (corner bits: x 1, y 2, z 4)
                static const unsigned char face[6][4]={{0,2,1,3},{4,5,6,7},{0,1,4,5},{2,6,3,7},{0,4,2,6},{1,3,5,7}};
                for(unsigned f=0;f<6;++f){
                    for(unsigned k=0;k<4;++k){
                        pvr_vertex_t& o=buf[k];const float* q=s[face[f][k]];
                        o.flags=k==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;o.x=q[0];o.y=q[1];o.z=q[2];
                        o.u=0;o.v=0;o.argb=0xffff00ffU;o.oargb=0;
                    }
                    sq=re4dc_ta_put(sq,buf,4);slots+=4;
                }
                ++pcact::drawn;
            }
            re4dc_model_direct_end(slots);
        } else pcact::unchecked+=pcact::nbox;
        pcact::nbox=0;
    }
#endif
#if RE4DC_SKY_ANY
    re4dc_ps2_sky_header=0;
#endif
#if RE4DC_WORLD_HOLE_DIAG
    whd::end_pass(pass,c.parts,re4dc_ui_frame(),ps2w.room);
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    wc_result.complete=!c.fallback;
#endif
    return c.fallback?0:1;
}
}
#if RE4DC_MOVIE_WORLD_ARENA || RE4DC_CABIN_SOURCE
extern "C" int re4dc_movie_world_before_heap_change(const void* start,unsigned bytes){
#if RE4DC_CABIN_SOURCE
    if(!re4dc_cabin_before_heap_change(start,bytes))return 0;
#endif
#if RE4DC_MOVIE_WORLD_ARENA
    if(!ps2_movie.base || !bytes)return 1;
    const auto lo=reinterpret_cast<std::uintptr_t>(start),hi=lo+bytes;
    const auto base=reinterpret_cast<std::uintptr_t>(ps2_movie.base);
    // Include the retained cell's OS/Room4 headers and MAD trailer. No payload
    // dereference until both range overlap and the current generation validate.
    if(hi<lo)return 0;
    const auto begin=base-64u,end=base+ps2_movie.capacity+32u;
    if(hi<=begin || lo>=end)return 1;
    if(ps2_movie.readers || !ps2_movie_current())return 0;
    if(ps2_movie.phase==movie_world::Phase::borrowed){
        if(!re4dc_movie_world_before_room_retire())return 0;
    }else if(ps2_movie.unavailable())return 0;
    // The still-live heap owns every free. Ready-world retirement and a safely
    // cancelled borrow both reach this same existing owner boundary exactly once.
    re4dc_ps2_mesh_retire();
    return !ps2w.storage;
#else
    return 1;
#endif
}
#endif
#if RE4DC_MOVIE_WORLD_ARENA
extern "C" int re4dc_ps2_mesh_movie_blocked(){return ps2_movie_blocked();}
extern "C" unsigned re4dc_ps2_mesh_movie_borrow(unsigned id){
    const bool supported=(ps2w.room==0x11f && (id==0x11f10 || id==0x11f11))
#if RE4DC_MOVIE_WORLD_ARENA_S30
        || (ps2w.room==0x100 && id==0x10030)
#endif
        ;
    if(!supported || ps2w.room!=ps2w.want || !ps2_movie_layout(ps2w.room) ||
       ps2_movie.phase!=movie_world::Phase::ready || ps2_movie.readers || !ps2_movie_current() ||
       !ps2w.parts || !ps2w.placements || !ps2_movie_dyn_valid())return 0;
    if(!re4dc_ui_movie_handoff_ready())return 0;
    // Fence may yield: revalidate the owner before touching retained memory.
    const unsigned token=ps2_movie.borrow(ps2_movie_current() && ps2_movie_dyn_valid(),true);
    if(!token)return 0;
    re4dc_ps2_world_movie_discard();ps2_movie_unpublish();
    re4dc_log("MOVIEARENA borrow id=%05x token=%u gen=%u base=%p capacity=%u budget=%u\n",
        id,token,ps2_movie.generation,ps2_movie.base,ps2_movie.capacity,movie_world::arena_bytes);
    return token;
}
extern "C" int re4dc_ps2_mesh_movie_valid(unsigned token){return ps2_movie.valid(token,ps2_movie_current());}
extern "C" void* re4dc_ps2_mesh_movie_alloc(unsigned token,unsigned bytes){
    return ps2_movie.alloc(token,bytes,ps2_movie_current());
}
extern "C" int re4dc_ps2_mesh_movie_free(unsigned token,void* p){
    return ps2_movie.release(token,p,ps2_movie_current());
}
extern "C" int re4dc_ps2_mesh_movie_return(unsigned token,int retiring){
    if(!ps2_movie.begin_return(token,ps2_movie_current()))return -1;
    const unsigned used=ps2_movie.used,slots=ps2_movie.nslots,blocked=ps2_movie.blocked;
    if(retiring){
        const bool ok=ps2_movie.retire(token,ps2_movie_current());
        re4dc_log("MOVIEARENA retire token=%u used=%u slots=%u blocked=%u ok=%u\n",token,used,slots,blocked,unsigned(ok));
        return ok?0:-1; // normal room owner subsequently frees exactly once
    }
    bool restored=false;unsigned attempt=0;
    for(;attempt<2 && !restored;++attempt){
        restored=ps2_movie_reload();
        if(!restored)ps2_movie_unpublish();
    }
#if RE4DC_GC_ASSET_GATE
    if(restored)gcasset_world_reseal();
#endif
    const bool ok=ps2_movie.restored(token,ps2_movie_current(),restored);
    re4dc_log("MOVIEARENA return token=%u used=%u slots=%u blocked=%u attempts=%u restored=%u\n",
        token,used,slots,blocked,attempt,unsigned(ok));
    return ok?1:-1;
}
#endif
extern "C" void re4dc_ps2_mesh_camera(const float* view,const float* projection,const float* viewport){
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    const re4dc::wc24::Scope wc_world(re4dc::wc24::NearOP,re4dc::wc24::Other);
    Wc24PassResult wc_result;
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    wc_result.why.tag(re4dc::wc24::ErrorMeshCamera,re4dc::wc24::ErrorMovieSuppressed,ps2w.room);
#endif
#endif
#if RE4DC_MOVIE_WORLD_ARENA
    if(ps2_movie_blocked())return;
#endif
    std::memcpy(ps2w.view,view,sizeof(ps2w.view));
    std::memcpy(ps2w.projection,projection,sizeof(ps2w.projection));
    std::memcpy(ps2w.viewport,viewport,sizeof(ps2w.viewport));
    ps2w.camera=true;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    wc_result.complete=true;
#endif
}
#if RE4DC_PS2_INTERIOR_CULL==2
// =2: count the check colour (RGB565 magenta, any dither of green) in the displayed framebuffer: the image the PVR
// finished last, i.e. one of the previous frames. Each nonzero count is a pixel =1 would have lost.
namespace {
unsigned pc_scan_frames=0,pc_scan_hits=0,pc_scan_max=0,pc_scan_last=~0U,pc_scan_pixels=0;
void pc_scan(unsigned frame){
    if(frame==pc_scan_last)return;
    pc_scan_last=frame;
    const std::uint32_t base=PVR_GET(PVR_FB_ADDR)&0x7fffffU;
    const unsigned w=vid_mode->width,h=vid_mode->height;
    const auto* fb=reinterpret_cast<const volatile std::uint16_t*>(PVR_RAM_BASE|base);
    unsigned n=0,x0=~0U,y0=~0U,x1=0,y1=0;
    for(unsigned i=0;i<w*h;++i){const unsigned px=fb[i];if((px&0xf81fU)==0xf81fU && ((px>>5)&63U)<=2U){
        ++n;const unsigned x=i%w,y=i/w;if(x<x0)x0=x;if(x>x1)x1=x;if(y<y0)y0=y;if(y>y1)y1=y;}}
    ++pc_scan_frames;pc_scan_pixels+=n;
    if(n){++pc_scan_hits;if(n>pc_scan_max)pc_scan_max=n;}
    if(n || !(frame%120))re4dc_log("PCCHECK frame=%u magenta=%u active=%d cell=%d scanned=%u hit_frames=%u max=%u pixels=%u fb=%06x %ux%u box=%u,%u-%u,%u\n",
        frame,n,int(pc::st.active),pc::st.cell,pc_scan_frames,pc_scan_hits,pc_scan_max,pc_scan_pixels,unsigned(base),w,h,
        n?x0:0U,n?y0:0U,x1,y1);
}
}
#endif
#if RE4DC_FAR_SHELL
#define RE4DC_FAR_SHELL_PART 2
#include "far_shell.inc"
#undef RE4DC_FAR_SHELL_PART
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
// Independent of WORLD_METER: enabling the census must not enable its QA
// distance overrides or alter the renderer's existing selection policy.
extern "C" void re4dc_wc24_identity(unsigned out[7]){
#if defined(RE4DC_VIEW_DIST_OPTION) && RE4DC_VIEW_DIST_OPTION
    out[0]=unsigned(re4dc_view_dist_get());
#else
    out[0]=~0U;
#endif
#if RE4DC_PS2_PVS
    out[1]=re4dc_ps2_pvs_on;
#else
    out[1]=~0U;
#endif
#if RE4DC_FAR_SHELL
    out[2]=unsigned(far_shell_mode);
#else
    out[2]=~0U;
#endif
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    out[3]=re4dc_qa_wopq_mm;out[4]=re4dc_qa_wxlu_mm;out[5]=re4dc_qa_wshell;
#else
    out[3]=out[4]=out[5]=0;
#endif
    out[6]=wc24_generation;
}
#endif
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
// WORLD_METER (game30.mk; QA disc only; display / render only). Per tick: us and vertices of the PS2 world's opaque pass
// (0), its punch-through + translucent passes (1), the far shell (2); tick_log.cpp takes them once per tick.
extern "C" { volatile unsigned re4dc_qa_wopq_mm,re4dc_qa_wxlu_mm,re4dc_qa_wshell; }
extern "C" unsigned re4dc_wm_room(void);
static unsigned wm_generation;
extern "C" void re4dc_world_meter_identity(unsigned out[7]){
    out[6]=wm_generation;
    out[0]=re4dc_wm_room();out[1]=unsigned(re4dc_view_dist_get()); // existing FAR_SHELL/VIEW_DIST_OPTION interface
#if RE4DC_PS2_PVS
    out[2]=re4dc_ps2_pvs_on;
#else
    out[2]=~0U;
#endif
    out[3]=re4dc_qa_wopq_mm;out[4]=re4dc_qa_wxlu_mm;out[5]=re4dc_qa_wshell;
}
namespace wmeter {
unsigned long long us[3];unsigned vtx[3],key[7];bool have_key=false;
unsigned active_pass=3;re4dc::pvs23::Geometry geometry;
void identity(){
    unsigned now[7];re4dc_world_meter_identity(now);
    if(!have_key || !re4dc::pvs23::same(now,key)){
        std::memcpy(key,now,sizeof(key));have_key=true;
        for(unsigned k=0;k<3;++k){us[k]=0;vtx[k]=0;}
        geometry.clear();
    }
}
struct Scope {
    unsigned k,v0,previous;unsigned long long t0;const unsigned* src;
    Scope(unsigned kind,const unsigned* vsrc,unsigned pass=3):k(kind),v0(*vsrc),previous(active_pass),t0(timer_us_gettime64()),src(vsrc){identity();active_pass=pass;}
    ~Scope(){us[k]+=timer_us_gettime64()-t0;const unsigned v1=*src;if(v1>=v0)vtx[k]+=v1-v0;active_pass=previous;}
};
}
extern "C" void re4dc_wm_corners(const std::uint8_t* codes,unsigned count,unsigned mask){
    wmeter::geometry.add(wmeter::active_pass,codes,count,mask);
}
extern "C" void re4dc_world_meter_resume(){++wm_generation;}
extern "C" int re4dc_world_meter_geometry_supported(){
    return RE4DC_MESH_FASTPATH && RE4DC_MESH_VP_SCHED!=2;
}
extern "C" void re4dc_world_meter_take(unsigned* us_out,unsigned* vtx_out,unsigned* geometry_out,unsigned* identity_out){
    wmeter::identity();std::memcpy(identity_out,wmeter::key,sizeof(wmeter::key));
    for(unsigned k=0;k<3;++k){
        us_out[k]=unsigned(wmeter::us[k]);vtx_out[k]=wmeter::vtx[k];wmeter::us[k]=0;wmeter::vtx[k]=0;
        geometry_out[k]=unsigned(wmeter::geometry.transformed[k]);
        geometry_out[k+3]=unsigned(wmeter::geometry.input_inside[k]);
    }
    wmeter::geometry.clear();
}
// The far a world pass draws with under the QA rows: pass 0 the opaque cut, passes 1 / 2 the translucent far (1 = Full: the
// far before the View distance cut: re4dc_fog_note_far's, already within FOG_FAR / the lake cap).
extern "C" float re4dc_wm_far(unsigned pass,float far){
    const unsigned o=pass?re4dc_qa_wxlu_mm:re4dc_qa_wopq_mm;
    if(!o)return far;
    return o==1U?(far_shell_noted>far?far_shell_noted:far):float(o);
}
extern "C" float re4dc_wm_full(void){return far_shell_noted;}
// native_ps2_world.cpp: the far shell's draw, metered (vertices = strip vertices sent).
extern "C" int re4dc_wm_shell_draw(float cut,float full){
    const wmeter::Scope wm_scope(2U,&farshell::st.strip_verts);
    return re4dc_far_shell_draw(cut,full);
}
#endif
extern "C" int re4dc_ps2_mesh_draw(unsigned pass,float zfar){
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    const re4dc::wc24::Scope wc_world(pass<3U?static_cast<re4dc::wc24::Path>(pass):re4dc::wc24::PathCount,
                                     re4dc::wc24::Other);
    Wc24PassResult wc_result;
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    wc_result.why.tag(re4dc::wc24::ErrorMeshDraw,re4dc::wc24::ErrorPassIncomplete,pass,ps2w.room);
#endif
#endif
    RE4DC_BFC_SCOPE(1u,0u);  // BACKFACE_CENSUS
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    const wmeter::Scope wm_scope(pass?1U:0U,&stats.vertices,pass);
    zfar=re4dc_wm_far(pass,zfar);
#endif
#if RE4DC_MOVIE_WORLD_ARENA
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    if(ps2_movie_blocked()){wc_result.why.first(re4dc::wc24::ErrorMovieSuppressed,pass,ps2w.room);return 1;}
#else
    if(ps2_movie_blocked())return 1;
#endif
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    if(r11fNativeClaimed()){
        const int result=r11fNativePass(pass,zfar);
        wc_result.complete=result>0;
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
        if(!wc_result.complete)wc_result.why.first(re4dc::wc24::ErrorReceiptIncomplete,pass,uint32_t(result));
#endif
        return result;
    }
#else
    if(r11fNativeClaimed())return r11fNativePass(pass,zfar);
#endif
#endif
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    if(!re4dc_source_world_binding_valid()){
        wc_result.why.first(re4dc::wc24::ErrorBindingLost,pass,ps2w.room);
        re4dc_source_world_binding_failed();return -1;
    }
#else
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return -1;}
#endif
#endif
#if RE4DC_PS2_INTERIOR_CULL==2
    if(!pass)pc_scan(re4dc_ui_frame());
#endif
#if defined(RE4DC_FOLIAGE_TRIM)
#endif
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    if(pass>2){wc_result.why.first(re4dc::wc24::ErrorInvalidPass,pass);return 0;}
    if(!ps2w.camera){wc_result.why.first(re4dc::wc24::ErrorCameraUnavailable,pass);return 0;}
    if(!ps2_open()){wc_result.why.first(re4dc::wc24::ErrorPackageUnavailable,ps2w.room,ps2w.want);return 0;}
#else
    if(pass>2 || !ps2w.camera || !ps2_open())return 0;
#endif
#if RE4DC_MOVIE_WORLD_ARENA
    MovieWorldRead read;
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    // ps2_pass owns all of its early returns and the final fallback count.
    wc_result.complete=true;
#endif
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    const int result=ps2_pass(pass,zfar);
    // Only the claimed transaction consumes numeric pass evidence. Ordinary
    // native/D41 callers retain the original boolean return contract.
    return re4dc_source_world_group_claimed()?result:result>0;
#else
    return ps2_pass(pass,zfar)>0;
#endif
}
#if RE4DC_PS2_INTERIOR_CULL
// native_movie.cpp open (before heap_before): a route movie borrows the cell block. Returns the bytes freed.
extern "C" unsigned re4dc_ps2_interior_movie_release(){
    const unsigned freed=pc::unload();
    if(freed){pc::data.lent=true;++pc::data.lends;re4dc_log("PCCULL cell lent to a movie (%u B)\n",freed);}
    return freed;
}
// route_movie_bridge.cpp after RouteMoviePlay / RouteMoviePlayQte: the block a movie borrowed is read again (the r100
// package still open; a room change in between retires it with the package).
extern "C" void re4dc_ps2_interior_movie_restore(){
    if(!pc::data.lent)return;
    pc::data.lent=false;
    if(pc::st.ok)pc::load();
#if RE4DC_GC_ASSET_GATE
    gcasset_world_reseal();
#endif
}
// The cell's test for any world box, e.g. an actor's (lane iv's CROWD_INVIS_SKIP could call it after the game's own
// view test): 1 when this frame's cell hides the box. 0 unless the PS2 world's pass 0 set the cell up in this same
// frame (the camera is then this frame's), and 0 for a box touching the house box.
extern "C" int re4dc_ps2_interior_hidden(const float lo[3],const float hi[3]){
    if(!pc::st.active || pc::st.setup_frame!=re4dc_ui_frame())return 0;
    float c[3],h[3];
    for(unsigned a=0;a<3;++a){c[a]=(lo[a]+hi[a])*0.5f;h[a]=std::fabs(hi[a]-lo[a])*0.5f;}
    return pc::hidden(c,h)>0;
}
#endif
#if RE4DC_PS2_INTERIOR_ACTORS
// PS2_INTERIOR_ACTORS (game30.mk; lane pc): the cell for actors. ModelTrans runs before Render's PS2 pass 0, so the
// cell is set up again at Trans start (re4dc_invis_begin -> re4dc_ps2_interior_trans) from the camera Trans sees
// (pG->Cam.v_mat, the projection CameraSetProjection(1) will load), in its own state (pc::st_trans). Render's pass 0
// compares that view with the one it draws with (PCACT view_mis: must stay 0). =2 (check build, with
// PS2_INTERIOR_CULL=2): nothing is skipped; each box the cell would have hidden is drawn as an opaque magenta box in
// pass 0 (depth tested, the world check's header), so the framebuffer scan covers the actors too.
extern "C" void re4dc_ps2_interior_trans(const float* view,const float* P){
    pc::State& s=pc::st_trans;
    s.ok=pc::st.ok;s.active=false;pcact::have=false;
#if RE4DC_PS2_INTERIOR_CULL==2
    pcact::nbox=0;
#endif
    if(!view || !P || P[0]!=0.0f)return;
    const float near=P[6]/(P[5]-1.0f);
    if(!(near>0.0f) || !re4dc::render::is_finite(near))return;
    pc::setup_state(s,view,P,near);
    std::memcpy(pcact::view,view,sizeof(pcact::view));std::memcpy(pcact::P,P,sizeof(pcact::P));pcact::near=near;pcact::have=true;
    ++pcact::trans_frames;if(s.active)++pcact::active;
}
// 1: the Trans-time cell hides the world box (lo / hi) and the actor may be skipped; 0 otherwise (and always at =2,
// which queues the box for the magenta check instead).
#if defined(RE4DC_OWNER_SETUP_LEAN) && RE4DC_OWNER_SETUP_LEAN
// OWNER_SETUP_LEAN (crowd.mk): 1 while the hidden tests below can return 1 (their own first condition).
extern "C" int re4dc_ps2_interior_trans_active(){
    const pc::State& s=pc::st_trans;
    return s.active && s.setup_frame==re4dc_ui_frame();
}
#endif
extern "C" int re4dc_ps2_interior_actor_hidden(const float lo[3],const float hi[3]){
    pc::State& s=pc::st_trans;
    if(!s.active || s.setup_frame!=re4dc_ui_frame())return 0;
    float c[3],h[3];
    for(unsigned a=0;a<3;++a){c[a]=(lo[a]+hi[a])*0.5f;h[a]=std::fabs(hi[a]-lo[a])*0.5f;}
    ++pcact::tests;
    if(!(pc::hidden_state(s,c,h)>0))return 0;
    ++pcact::hid;
#if RE4DC_PS2_INTERIOR_CULL==2
    if(pcact::nbox<pcact::kBoxes){
        auto& b=pcact::box[pcact::nbox++];
        for(unsigned a=0;a<3;++a){b.lo[a]=lo[a];b.hi[a]=hi[a];}
        ++pcact::boxes;
    } else ++pcact::overflow;
    return 0;
#else
    return 1;
#endif
}
#if RE4DC_PS2_INTERIOR_OWNER
// PS2_INTERIOR_ACTORS=2: the same test for an owner-path Ganado's cast-ball box (coarse_actor_owner_ganado.inc
// invis_owner_interior). 1 when the Trans-time cell hides it, also at =2, where the box is queued for the magenta
// check as above and the caller draws the Ganado and checks its crowd entry instead of skipping it.
extern "C" int re4dc_ps2_interior_owner_hidden(const float lo[3],const float hi[3]){
    pc::State& s=pc::st_trans;
    if(!s.active || s.setup_frame!=re4dc_ui_frame())return 0;
    float c[3],h[3];
    for(unsigned a=0;a<3;++a){c[a]=(lo[a]+hi[a])*0.5f;h[a]=std::fabs(hi[a]-lo[a])*0.5f;}
    ++pcact::owner_tests;
    if(!(pc::hidden_state(s,c,h)>0))return 0;
    ++pcact::owner_hid;++pcact::hid;
#if RE4DC_PS2_INTERIOR_CULL==2
    if(pcact::nbox<pcact::kBoxes){
        auto& b=pcact::box[pcact::nbox++];
        for(unsigned a=0;a<3;++a){b.lo[a]=lo[a];b.hi[a]=hi[a];}
        ++pcact::boxes;
    } else ++pcact::overflow;
#endif
    return 1;
}
#endif
#endif
extern "C" void re4dc_ps2_mesh_log(unsigned frame){
    for(unsigned p=0;p<3;++p){
        const auto& c=ps2w.count[p];
        re4dc_log("PS2MESH frame=%u pass=%u placements=%u culled=%u parts=%u native=%u fallback=%u aborts=%u near=%d far=%d cull_far=%d\n",
            frame,p,c.placements,c.culled,c.parts,c.native,c.fallback,c.aborts,int(c.near),int(c.far),int(c.cull_far));
    }
    re4dc_log("PS2MESH frame=%u strips=%u culled=%u clipped=%u vertices=%u clusters=%u/%u lod=%u,%u,%u,%u\n",frame,
        stats.strips,stats.strips_culled,stats.strips_clipped,stats.vertices,stats.clusters_visible,stats.clusters_culled,
        stats.lod_draws[0],stats.lod_draws[1],stats.lod_draws[2],stats.lod_draws[3]);
#if RE4DC_PS2_PASS_MASK==2
    re4dc_log("PS2MASK frame=%u masked=%d checked=%u mismatched=%u\n",frame,int(ps2w.masked),ps2_mask_stats[0],ps2_mask_stats[1]);
#endif
#if RE4DC_MESH_CLIP_ACCEPT==2
    re4dc_log("CLIPACC frame=%u accepted=%u dropped=%u mismatched=%u crossings=%u\n",frame,clip_accept_stats[0],
        clip_accept_stats[1],clip_accept_stats[2],clip_accept_stats[3]);
#endif
}
extern "C" void re4dc_ps2_mesh_retire(){
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    ++wc24_generation;
#endif
#if RE4DC_GC_ASSET_GATE
    gcasset_invalidate_world();
#endif
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    ++wm_generation; // also invalidate a same-room package reload or teleport
#endif
#if RE4DC_MOVIE_WORLD_ARENA
    if(ps2_movie.readers || ps2_movie.unavailable()){
        re4dc_missing("movie world arena retired before borrower cleanup");return;
    }
    if(ps2_movie.base && !ps2_movie.retire(ps2_movie.serial,ps2_movie_current())){
        re4dc_missing("movie world arena stale owner retirement");return;
    }
    ps2_movie_files={};
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
    r11fPackageAdvance();
#endif
#if RE4DC_PS2_WORLD_SOURCE_OWNER
    if(sourceWorldPackageGeneration!=~0U)++sourceWorldPackageGeneration;
    sourceWorldSidecarCrc=0;
#endif
#if (defined(RE4DC_ENEMY_VIS_CULL) && RE4DC_ENEMY_VIS_CULL) || RE4DC_PS2_PVS
    enemyVisSidecarCrc=0;
#endif
#if RE4DC_PS2_PLACE_GATE
    gate::retire();
#endif
#if RE4DC_FAR_SHELL
    farshell::close();farshell::pol.tried=false;farshell::pol.movie=false;
#endif
#if defined(RE4DC_TRANS_POLICY)
    trans::close();
#endif
#if defined(RE4DC_TRANS_POLICY)
    trans::close();
#endif
    ps2w.package.close();
    if(ps2w.storage)re4dc_static_free(ps2w.storage);
    ps2w.storage=nullptr;ps2w.bytes=0;ps2w.parts=nullptr;ps2w.placements=nullptr;ps2w.nplacements=0;
    ps2w.lut=nullptr;ps2w.gather=nullptr;ps2w.attempted=false;
#if RE4DC_PS2_PASS_MASK
    ps2w.masked=false;
#endif
#if RE4DC_PS2_STRIP_GROUPS
    if(ps2w.sg_block)re4dc_static_free(ps2w.sg_block);
    ps2w.sg_block=nullptr;ps2w.sg=nullptr;ps2w.sg_groups=0;
#endif
#if RE4DC_SCENERY_DEDUP
    dedup_free();
#endif
#if RE4DC_PS2_WORLD_DYNAMIC
    dyn::reset();
#endif
#if RE4DC_PS2_INTERIOR_CULL
    pc::unload();pc::data.lent=false;
    pc::st.ok=false;pc::st.active=false;
#endif
#if RE4DC_PS2_PVS
    pvs::close();
#endif
}
#if RE4DC_PS2_WORLD_DYNAMIC
// scroll.cpp setObj, after the object's matUpdate and re4dc_static_bind (which opens this room's PS2 world): the
// game object registered under scroll id `id`, its be_flag / serial / mat fields and its rest matrix.
extern "C" void re4dc_ps2_dyn_bind(unsigned room,unsigned id,const void* object,const void* flag,const void* serial,
                                   const float* mat){
    if(!dyn::ids || ps2w.room!=room || id>=dyn::kIds || dyn::slot_of[id]==dyn::kNone)return;
    const auto* o=static_cast<const unsigned char*>(object);
    dyn::off_flag=unsigned(static_cast<const unsigned char*>(flag)-o);
    dyn::off_serial=unsigned(static_cast<const unsigned char*>(serial)-o);
    dyn::off_mat=unsigned(reinterpret_cast<const unsigned char*>(mat)-o);
    dyn::Slot& s=dyn::slots[dyn::slot_of[id]];
#if RE4DC_ROOT_POSE_REFUSAL_DIAG
    dyn::root_report(id,s,"rebind");s.diag={};
#endif
#if RE4DC_PS2_WORLD_PARTS
#if RE4DC_ROOT_POSE_WITNESS_PREFLIGHT
    dyn::release_parts(s);
#else
    if(s.parts)re4dc_static_free(s.parts);
#endif
    s.parts=nullptr;s.nparts=0;s.source=false;
#if RE4DC_PS2_WORLD_ROOT_POSE
    s.root_matrix_offset=0;
#endif
#endif
    s.obj=o;std::memcpy(&s.serial,serial,4);std::memcpy(s.rest,mat,sizeof(s.rest));
#if RE4DC_PS2_WORLD_PARTS
    dyn::order_object(id);dyn::state[id]=0;
#endif
    ++dyn::binds;
}
#if RE4DC_PS2_WORLD_PARTS
extern "C" void re4dc_ps2_dyn_parts(unsigned room,unsigned id,const void* object,const void* first,
                                     unsigned count,unsigned next_offset,unsigned pose_offset
#if RE4DC_PS2_WORLD_ROOT_POSE
                                     ,unsigned matrix_offset
#endif
                                     ){
    if(!dyn::ids || ps2w.room!=room || id>=dyn::kIds || dyn::slot_of[id]==dyn::kNone || !count || count>255)return;
    dyn::Slot& s=dyn::slots[dyn::slot_of[id]];
    if(s.obj!=object || s.parts)return;
#if RE4DC_ROOT_POSE_WITNESS_PREFLIGHT
    // Register once at the original setObj bind. In particular, a refused
    // chain/owner must never retry with an animated matrix as its bind pose.
    if(count==1 && s.root_matrix_offset)return;
    if(count==1)s.root_matrix_offset=matrix_offset<~0U-1U && !(matrix_offset%alignof(float))?matrix_offset+1U:~0U;
    std::uint32_t serial=0;
    if(object)std::memcpy(&serial,s.obj+dyn::off_serial,sizeof(serial));
    if(!object || serial!=s.serial || (count==1 && s.root_matrix_offset==~0U)){
#if RE4DC_ROOT_POSE_REFUSAL_DIAG
        if(count==1)dyn::root_note(s,!object || serial!=s.serial?dyn::RootSerial:dyn::RootInvalid);
#endif
        return;
    }
#else
#if RE4DC_PS2_WORLD_ROOT_POSE
    if(count==1)s.root_matrix_offset=matrix_offset+1U;
#endif
#endif
    const unsigned part_bytes=dyn::part_cell_bytes(count);
#if RE4DC_ROOT_POSE_WITNESS_PREFLIGHT
    auto* poses=count==1?dyn::reserved_pose(s):static_cast<dyn::PartPose*>(re4dc_static_alloc(part_bytes));
#else
    auto* poses=static_cast<dyn::PartPose*>(re4dc_static_alloc(part_bytes));
#endif
#if RE4DC_ROOT_POSE_REFUSAL_DIAG
    if(!poses && count==1)dyn::root_note(s,dyn::RootHeap);
#endif
    if(!poses){re4dc_log("PS2PART no heap id=%02x parts=%u\n",id,count);return;}
    const auto* p=static_cast<const unsigned char*>(first);
    for(unsigned i=0;i<count;++i){
#if RE4DC_ROOT_POSE_WITNESS_PREFLIGHT || RE4DC_ROOT_POSE_REFUSAL_DIAG
        if(!p){
#if RE4DC_ROOT_POSE_WITNESS_PREFLIGHT
            if(count!=1)re4dc_static_free(poses);
#else
            re4dc_static_free(poses);
#endif
#if RE4DC_ROOT_POSE_REFUSAL_DIAG
            if(count==1)dyn::root_note(s,dyn::RootChain);
#endif
            re4dc_log("PS2PART short chain id=%02x part=%u/%u\n",id,i,count);return;}
#else
        if(!p){re4dc_static_free(poses);re4dc_log("PS2PART short chain id=%02x part=%u/%u\n",id,i,count);return;}
#endif
        poses[i].part=p;std::memcpy(poses[i].pose,p+pose_offset,sizeof(poses[i].pose));
        std::memcpy(&p,p+next_offset,sizeof(p));
    }
#if RE4DC_PS2_WORLD_ROOT_POSE
    if(count==1){
        auto* root=reinterpret_cast<float*>(poses+1);
        std::memcpy(root,static_cast<const unsigned char*>(first)+matrix_offset,12U*sizeof(float));
        bool valid=inverse(root,root+12);
        for(unsigned i=0;i<24;++i)valid=valid && std::isfinite(root[i]);
#if RE4DC_ROOT_POSE_REFUSAL_DIAG
        if(!valid)dyn::root_note(s,dyn::RootInvalid);
#endif
        if(!valid)s.root_matrix_offset=~0U;
    }
#endif
    s.parts=poses;s.nparts=count;s.pose_offset=pose_offset;
    re4dc_log("PS2PART bind id=%02x parts=%u bytes=%u heap=%d\n",id,count,part_bytes,re4dc_static_heap_free());
}
extern "C" int re4dc_ps2_dyn_source(unsigned room,const void* object,unsigned serial){
    if(!dyn::ids || ps2w.room!=room)return 0;
#if RE4DC_PS2_WORLD_LEAN
    if(lean::kMode&16U){
        const unsigned b=dyn::lean_bit(reinterpret_cast<std::uintptr_t>(object));
        if(!((dyn::lean_mask[b>>5]>>(b&31U))&1U)){++lean::st.dyn_fast;return 0;}
    }
#endif
    // This small owner table is shared with the placement adapter. Match the
    // serial before inspecting any borrowed part addresses after object reuse.
    const auto key=reinterpret_cast<std::uintptr_t>(object);
    unsigned lo=0,hi=dyn::nobjects;
    while(lo<hi){
        const unsigned mid=(lo+hi)/2,id=dyn::object_order[mid];
        const dyn::Slot& s=dyn::slots[dyn::slot_of[id]];
        const auto at=reinterpret_cast<std::uintptr_t>(s.obj);
        if(at<key)lo=mid+1;
        else hi=mid;
    }
    // The object pool can reuse one address for a different scenery ID. A stale
    // binding at the same address must not hide the current serial's binding.
    for(;lo<dyn::nobjects;++lo){
        const unsigned id=dyn::object_order[lo];
        const dyn::Slot& s=dyn::slots[dyn::slot_of[id]];
        if(reinterpret_cast<std::uintptr_t>(s.obj)!=key)break;
        if(s.serial==serial)return dyn::query(id)==3;
    }
    return 0;
}
#endif
#endif
#if RE4DC_PS2_WORLD_ROOMS
namespace { void ps2_free(){re4dc_ps2_mesh_retire();} }
// The rooms that have a PS2 world package (tools/ps2_room_r4im.py, dc/native/r%03x/ps2-world.*): the one list
// native_ps2_world.cpp (re4dc_ps2_world_covers) and the =2 preload share. r106: the route lane (stage 1-1 end);
// r104 / r105 / r107 (chapter 1-2, route lane): their GC scenery is released like r106's.
#if RE4DC_PS2_WORLD_REGISTRY
// PS2_WORLD_REGISTRY=1 (game30.mk): the list is generated from the validated package manifest
// (tools/d367/ps2world/world_registry.py -> include/ps2_world_rooms.inc): one bit per room, stage = room >> 8.
// A listed room whose package is absent falls back to its own scenery (re4dc_ps2_mesh_failed): drawn only if oct-encoded, or prelit with SCENERY_ENCODING=1.
namespace { const std::uint32_t kPs2WorldRoomBits[6][8]={
#include "include/ps2_world_rooms.inc"
}; }
#if defined(RE4DC_ROUTE_CH3) && RE4DC_ROUTE_CH3
// ROUTE_CH3 (stage-3 first pass): the island rooms whose PS2 world package passed the lane's conversion and
// runtime_open validation (/root/probe/lanes-20261014/st3/st3-handback-state.json; all but r313 / r314 / r334).
namespace { const std::uint32_t kPs2WorldSt3Bits[8]={0x3de7fffbU,0x000f03ffU,0x00000000U,0x00000000U,0x00000000U,0x00000000U,0x00000000U,0x00000000U}; }
#endif
extern "C" int re4dc_ps2_world_room(unsigned room){
    const unsigned stage=room>>8,index=room&255U;
#if defined(RE4DC_ROUTE_CH3) && RE4DC_ROUTE_CH3
    if(stage==3)return (kPs2WorldSt3Bits[index>>5]>>(index&31U))&1U;
#endif
#if defined(RE4DC_ROUTE_CH41) && RE4DC_ROUTE_CH41
    // ROUTE_CH41 (lane ch4found16): r222 and r22b, whose packages postdate the 10-04 registry (castle lane step 1:
    // all 42 castle packages match Codex's READY hand-backs); without them both rooms drew the released GC scenery.
    if(room==0x222 || room==0x22B)return 1;
#endif
    return stage<6 && ((kPs2WorldRoomBits[stage][index>>5]>>(index&31U))&1U);
}
#else
extern "C" int re4dc_ps2_world_room(unsigned room){
    return room==0x100 || room==0x101 || room==0x103 || room==0x104 || room==0x105 || room==0x106 || room==0x107;
}
#endif
#if RE4DC_PS2_WORLD_ROOMS >= 2
// bind_mesh (room entry, file I/O allowed): open this room's PS2 world before its scenery package would open.
extern "C" int re4dc_ps2_mesh_preload(unsigned room){
#if RE4DC_MOVIE_WORLD_ARENA
    if(ps2_movie_blocked())return 0;
#endif
    if(!re4dc_ps2_world_room(room))return 0;
    ps2w.want=room;
    return ps2_open();
}
extern "C" int re4dc_ps2_world_source_draw();   // native_ps2_world.cpp: pass 0 now, PT / TR at the flush
#ifndef RE4DC_SS_UI_ORDER
// subscreen.mk force-includes subscreen.h into this object; without it the inventory exclusion below would compile
// out without a word (the first 6819f3a2 prototype did exactly that).
#error "native_static.cpp needs $(OBJDIR)/subscreen.h (subscreen.mk -include): RE4DC_SS_UI_ORDER is not defined"
#endif
#if RE4DC_SS_UI_ORDER
extern "C" int re4dc_ss_ui_order(); // the subscreen owns the swapped model area
#endif
extern "C" int re4dc_coarse_source_camera(float view[12],float projection[7],float viewport[6]); // coarse.cpp
#if RE4DC_PS2_WORLD_SOURCE_OWNER
#include "include/native_source_world.inc"
#endif
#if RE4DC_PS2_WORLD_PREFLIGHT_DIAG
extern "C" int re4dc_source_world_diag_active(unsigned);
extern "C" void re4dc_source_world_diag_report(unsigned,const char*);
#endif
// re4dc_static_submit on a non-coarse image of a no-std room: once per image, the loaded package only (no I/O).
extern "C" void re4dc_ps2_mesh_source(unsigned room,const Re4dcModelPart& p){
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    const re4dc::wc24::Scope wc_world(re4dc::wc24::NearOP,re4dc::wc24::Other);
    Wc24PassResult wc_result;
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    wc_result.why.tag(re4dc::wc24::ErrorMeshSource,re4dc::wc24::ErrorMovieSuppressed,room);
#endif
#endif
#if RE4DC_MOVIE_WORLD_ARENA
    if(ps2_movie_blocked())return;
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    // Ownership arbitration and inventory/duplicate callbacks need not launch
    // another world. Once this adapter must launch, package/camera failure is
    // an incomplete world, even when ordinary source geometry can fall back.
    wc_result.complete=true;
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
    if(room==0x11f && re4dc_r11f_legacy_blocked(re4dc_ui_frame()))return;
#endif
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    // A planned or provisional transaction owns launch arbitration even after
    // revocation. Unmatched rigid parts keep their ordinary source geometry.
    if(!re4dc_source_world_legacy_allowed(re4dc_ui_frame()))return;
#endif
#if RE4DC_PS2_WORLD_SOURCE_OWNER
    unsigned generation=0;
    // A qualified whole-room frame starts only at its original owned callback.
    if(room==0x200 && re4dc_ps2_source_package(&generation) &&
       re4dc_source_world_current(re4dc_ui_frame(),generation))return;
#endif
#if RE4DC_SS_UI_ORDER
    // Inventory rigid models also carry static_geometry. They are not room scenery:
    // submitting the PS2 world here would close the subscreen's ordered TR list.
    if(re4dc_ss_ui_order())return;
#endif
    static unsigned last=~0U,images=0;
    const unsigned frame=re4dc_ui_frame();
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    wc_result.complete=frame==last;
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    wc_result.why.tag(re4dc::wc24::ErrorMeshSource,re4dc::wc24::ErrorPackageUnavailable,room,ps2w.room);
#endif
#endif
    (void)p; // an unbound scenery part carries no camera (world / view are the binding's): the game's
    if(frame==last || !ps2w.storage || ps2w.room!=room)return;
#if RE4DC_PS2_WORLD_PREFLIGHT_DIAG
    if(re4dc_source_world_diag_active(frame)){
        // The already qualified descriptor supplies values only. Do not read
        // the borrowed model/info/part objects or rerun the ownership walker.
        re4dc_log("PS2PF legacy f=%u room=%03x model=%p serial=%u info=%p part=%p key=%02x/%02x/%02x/%02x\n",
            frame,room,p.model,p.serial,p.info,p.part,unsigned(p.source_key[0]),unsigned(p.source_key[1]),unsigned(p.source_key[2]),unsigned(p.source_key[3]));
        re4dc_source_world_diag_report(frame,"legacy");
    }
#endif
    last=frame;
    float view[12],projection[7],viewport[6];
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    if(!re4dc_coarse_source_camera(view,projection,viewport)){
        wc_result.why.first(re4dc::wc24::ErrorCameraUnavailable,frame,room);return;
    }
#else
    if(!re4dc_coarse_source_camera(view,projection,viewport))return;
#endif
    re4dc_ps2_mesh_camera(view,projection,viewport);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    re4dc_ps2_source_legacy_started(frame);
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
    if(room==0x11f)r11fLegacyStamp(frame);
#endif
    const int drawn=re4dc_ps2_world_source_draw();
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    wc_result.complete=drawn>0;
#if defined(RE4DC_WORLD_CENSUS24_ERRORS) && RE4DC_WORLD_CENSUS24_ERRORS
    if(!wc_result.complete)wc_result.why.first(re4dc::wc24::ErrorPassIncomplete,uint32_t(drawn),frame);
#endif
#endif
    if(++images<=8 || !(images%120))re4dc_log("PS2MESH source image frame=%u room=%03x drawn=%d images=%u\n",frame,room,drawn,images);
}
#endif
#if RE4DC_PS2_PRELOAD_LEAN
// PS2_PRELOAD_LEAN (game30.mk): the open package's part textures for the room preload (native_ui.cpp), in part
// order with repeats (the caller skips keys it has); 0 past the end or when no package is open.
extern "C" int re4dc_ps2_mesh_texture(unsigned i,unsigned out[4]){
#if RE4DC_MOVIE_WORLD_ARENA
    if(ps2_movie_blocked())return 0;
#endif
    if(!ps2w.storage || !ps2w.parts || ps2w.room!=ps2w.want || i>=ps2w.package.header().part_count)return 0;
    const auto& q=ps2w.parts[i];
    out[0]=q.crc;out[1]=q.fnv;out[2]=q.width;out[3]=q.height;
    return 1;
}
#endif
#if defined(RE4DC_PS2_ROOM_PIN) && RE4DC_PS2_ROOM_PIN
// PS2_ROOM_PIN (native_ui.cpp preload): the open package's room, 0 when none is open.
extern "C" unsigned re4dc_ps2_mesh_room(){return ps2w.storage?ps2w.room:0U;}
#endif
// The room the next ps2_open serves (native_ps2_world.cpp, before each draw).
extern "C" void re4dc_ps2_mesh_select(unsigned room){
#if RE4DC_MOVIE_WORLD_ARENA
    if(ps2_movie_blocked())return;
#endif
    ps2w.want=room;
}
// This room's package was tried and did not open: its own scenery draws (re4dc_ps2_world_covers).
extern "C" int re4dc_ps2_mesh_failed(unsigned room){
#if RE4DC_MOVIE_WORLD_ARENA
    if(ps2_movie_blocked())return 0; // a loan is still covered, never a source fallback
#endif
    return ps2w.attempted && !ps2w.storage && ps2w.room==room;
}
#endif
#endif
#if defined(RE4DC_LAKE_FAR_ON)
// LAKE_FAR=<mm> (post30.mk, lane lake17 2026-10-17, user option (a)): in the lake rooms (r10b Del Lago, r11a shore, r11b
// night lake) the world, the coarse view and the fog far reach this distance instead of the 25 m cap. The fog ramp still
// takes the last 20 % of the far to 100 % fog colour, so the cut is hidden there as at 25 m. Render only.
// Per room (user 2026-10-17): LAKE_FAR for r10b (boat), LAKE_FAR_SHORE (default LAKE_FAR) for r11a / r11b; 0 = 25 m cap.
#if defined(RE4DC_QA_MENU) && RE4DC_QA_MENU
// QA_MENU (qamenu.mk): the QA menu's "Lake shore view" row; 0 = the build's LAKE_FAR_SHORE.
extern "C" { volatile unsigned re4dc_qa_shore_far_mm; }
#endif
extern "C" float re4dc_far_cap(float cap){
    const unsigned r=ps2w.room;
    float lake=0.0f;
    if(r==0x10bU)lake=float(RE4DC_LAKE_FAR);
#if defined(RE4DC_QA_MENU) && RE4DC_QA_MENU
    else if((r==0x11aU || r==0x11bU) && re4dc_qa_shore_far_mm)lake=float(re4dc_qa_shore_far_mm);
#endif
    else if(r==0x11aU || r==0x11bU)lake=float(RE4DC_LAKE_FAR_SHORE);
    return lake>cap?lake:cap;
}
#endif
