#include <type_traits>
#ifndef RE4DC_WORLD_AUTOSORT
#define RE4DC_WORLD_AUTOSORT 0
#endif
#ifndef RE4DC_PS2_WORLD_DRAW
#define RE4DC_PS2_WORLD_DRAW 0
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
#include <dc/sq.h>
#include <fcntl.h>
#include <cstdio>
#include <cstring>
#include <cmath>
#include <malloc.h>
#include <new>
#include <cstddef>
#include <algorithm>
#ifndef RE4DC_ACTOR_TRANSACTION
#define RE4DC_ACTOR_TRANSACTION 0
#endif
#if RE4DC_ACTOR_TRANSACTION
#include "include/actor_resource_lease.h"
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
// UI_HANDLES=1 (default off = previous image): direct texture handles. A
// source image descriptor resolves to its cache entry once; later draws reach
// it by one direct-mapped compare (no source scan, identity lookup, texel
// hash or entry scan). See resolve() below.
#ifndef RE4DC_UI_HANDLES
#define RE4DC_UI_HANDLES 0
#endif
// UI_HEADERS=1 (default off = previous image): each UI/HUD quad's PVR header
// (texture binding and blend) is compiled once per cache entry and blend mode
// and reused while the entry lives; the per-frame UI path only writes vertices.
#ifndef RE4DC_UI_HEADERS
#define RE4DC_UI_HEADERS 0
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
#include "native_ui.h"
#include "hud_source_mask.h"
#include "native_model.h"
#include "native_static.h"
#include "native_render_profile.hpp"
#include "pc_sampler.h"
#include "re4dc_platform.h"
#include "../../room/texture_package.hpp"
#include "../../room/room_storage.hpp"
#include "../../room/gpu_lifecycle.hpp"
#include "../../room/pvr_geometry.hpp"
#if RE4DC_COARSE_WORLD & 64
extern "C" int re4dc_coarse_world_room(void);                        // coarse.cpp: the world data's room (R3)
extern "C" int re4dc_coarse_world_tex(unsigned i,unsigned out[5]);   // coarse_world.cpp: its texture list
#endif

#if RE4DC_COARSE_LEON
extern "C" int re4dc_coarse_actor_texture_key(const Re4dcUiImage*,unsigned*,unsigned*);
#endif
namespace {
constexpr unsigned kQuadCount=256, kTextureCount=RE4DC_TEX_RESIDENT?RE4DC_TEX_SLOTS:RE4DC_PVR_STREAM?80:48, kSourceCount=RE4DC_PVR_STREAM?128:256, kVramBudget=4*1024*1024;
#if RE4DC_UI_VRAM
unsigned vram_budget,vram_retries,vram_rejects; // budget: set by re4dc_ui_init() from the actual pool
#endif
struct Key { unsigned crc,fnv; bool operator==(const Key& b)const{return crc==b.crc && fnv==b.fnv;} };
#if RE4DC_TEX_PACK
// TEX_PACK (game30.mk; tools/d367/texpack.py): dc/tex.pak index, validation and failure policy.
#include "texpack_index.inc"
#endif
struct Entry { re4dc::texture::Package package; Key key{}; unsigned frame=0; bool valid=false;
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
#if RE4DC_ACTOR_TRANSACTION
re4dc_actor::TextureLeases<kTextureCount> actor_texture_leases;
#define RE4DC_ENTRY_PINNED(e) ((e).frame==frame || actor_texture_leases.pinned(unsigned(&(e)-entries)))
#else
#define RE4DC_ENTRY_PINNED(e) ((e).frame==frame)
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
#if RE4DC_UI_HANDLES
// One 32-bit clock stamps every event that invalidates a handle: closing an
// entry (entry_closed[]) and every source descriptor boundary (each sources[]
// reset, handle_reset). A handle stamped later than both is still exact.
unsigned entry_closed[kTextureCount]; unsigned handle_clock=1,handle_reset=1,handle_hits,handle_misses,handle_bypass;
inline void sources_reset(){nsource=0;handle_reset=++handle_clock;}
#else
inline void sources_reset(){nsource=0;}
#endif
#if RE4DC_TEX_RESIDENT || RE4DC_SUBSCREEN
// (SUBSCREEN: sub screen images without a converted package are drawn every frame.)
Key missing_keys[32]; unsigned nmissing;
#endif
#if RE4DC_UI_VRAM && RE4DC_UI_FRAG_LATCH
constexpr unsigned kFragRetryFrames=120;
Key frag_key{}; unsigned frag_frame,frag_latched;
#endif
#if RE4DC_UI_VRAM && RE4DC_TEX_RESIDENT && RE4DC_UI_OVERLAY_SLAB_KB
constexpr unsigned kOverlaySlabBytes=RE4DC_UI_OVERLAY_SLAB_KB*1024U;
pvr_ptr_t overlay_slab; const Entry* overlay_owner; unsigned overlay_uses;
void overlay_slab_take(){ if(!overlay_slab && !overlay_owner)overlay_slab=pvr_mem_malloc(kOverlaySlabBytes); }
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
struct DeferredPart { DeferredPart* next;DeferredLighting* lighting;unsigned changed[kViewMasks]; };
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
bool draining_parts=false,source_draws_finished=false;
pvr_list_t draining_list=PVR_LIST_TR_POLY;
void reset_deferred(){deferred_spill=nullptr;deferred_spill_top=deferred_spill_capacity=0;deferred_light_sets=nullptr;deferred_basis=nullptr;deferred_lights=nullptr;deferred_first=deferred_last=nullptr;deferred_top=sizeof(frame_storage);deferred_count=0;}
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
bool movie_background;  // re4dc_ui_movie_background: the frame draws the picture behind its UI
unsigned movie_upload_serial,movie_shown_serial,movie_presentations;
uint64_t movie_first_picture_us;
void movie_draw();
#endif
// Diagnostic only: 64 KiB of copied native packets, allocated on first model.
// Roll back an entire part on overflow. No deferred source/primitive pointers.
constexpr unsigned kModelSlabBytes=64*1024;
constexpr unsigned kModelMetadataBytes=RE4DC_MODEL_DRAW_PLANS?32*1024:0;
// Whole-stack bisection: two static-cache contexts yielded ~1 hit/frame while
// late UI collided with source snapshots. Reassign those same 8 KiB to bounded
// frame ownership; evaluate unchanged source lighting without that tiny cache.
constexpr unsigned kModelStaticLightBytes=0;
constexpr unsigned kModelDeferredSpillBytes=RE4DC_D349_RENDERER_STACK?8192:0;
constexpr unsigned kModelPreparationBytes=RE4DC_D349_RENDERER_STACK?12288:0;
constexpr unsigned kModelPacketBytes=kModelSlabBytes-kModelMetadataBytes-kModelStaticLightBytes-kModelDeferredSpillBytes-kModelPreparationBytes;
pvr_vertex_t* model_packets; unsigned model_used,model_pending; Entry* model_handle;
#if RE4DC_ACTOR_UV16
unsigned next_pcw_set,next_pcw_clear; // actors30: re4dc_model_next_header_pcw, one packet_begin
#endif
int model_diagnostic=-1;
unsigned model_parts,model_invalid,model_resource,model_overflow,model_input,model_output,model_peak,model_presented;
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
volatile unsigned errors;          // error event bits: 1 ISP out of memory, 2 strip halt, 4 OPB out of memory, 8 TA input error, 16 TA input overflow
volatile unsigned last_flips;
asic_evt_handler_entry_t prev[12];
constexpr std::uint16_t kEvents[12]={ASIC_EVT_PVR_OPAQUEDONE,ASIC_EVT_PVR_OPAQUEMODDONE,ASIC_EVT_PVR_TRANSDONE,
    ASIC_EVT_PVR_TRANSMODDONE,ASIC_EVT_PVR_PTDONE,ASIC_EVT_PVR_RENDERDONE_TSP,ASIC_EVT_PVR_RENDERDONE_ISP,
    ASIC_EVT_PVR_ISP_OUTOFMEM,ASIC_EVT_PVR_STRIP_HALT,ASIC_EVT_PVR_OPB_OUTOFMEM,ASIC_EVT_PVR_TA_INPUT_ERR,
    ASIC_EVT_PVR_TA_INPUT_OVERFLOW};
constexpr char kCodes[12]={'o','m','t','n','p','R','I','1','2','3','4','5'};
constexpr unsigned char kCount[12]={kO,kO,kT,kT,kP,kR,kI,kE,kE,kE,kE,kE};
void put(char c){
    const int o=irq_disable();
    const unsigned h=head;
    ring_code[h%kRing]=static_cast<unsigned char>(c);ring_frame[h%kRing]=static_cast<unsigned short>(frame);head=h+1;
    irq_restore(o);
}
void bump(unsigned k){const int o=irq_disable();counts[k]=counts[k]+1;irq_restore(o);}
void event(uint32_t code,void* data){
    const unsigned i=unsigned(reinterpret_cast<std::uintptr_t>(data));
    if(i>=12)return;
    if(prev[i].hdl)prev[i].hdl(code,prev[i].data);
    put(kCodes[i]);counts[kCount[i]]=counts[kCount[i]]+1;
    if(i>=7)errors=errors|(1U<<(i-7));
}
void vblank(uint32_t,void*){
    const unsigned f=unsigned(pvr_state.frame_count);
    if(f!=last_flips){last_flips=f;put('F');counts[kF]=counts[kF]+1;}
}
void install(){
    last_flips=unsigned(pvr_state.frame_count);
    for(unsigned i=0;i<12;++i)prev[i]=asic_evt_set_handler(kEvents[i],event,reinterpret_cast<void*>(std::uintptr_t(i)));
    const int handle=vblank_handler_add(vblank,nullptr);
    re4dc_log("native PVR latch: 12 events chained (kos handlers %d/%d/%d) vblank=%d\n",prev[0].hdl!=nullptr,
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
    const int o=irq_disable();
    unsigned slices=0;
    while(flag && slices<kSlices)
        if(genwait_wait((void*)&flag,what,kSliceMs)<0 && flag){note(code,n);++slices;}
    const bool ok=!flag;
    irq_restore(o);
    return ok;
}
// Before KOS's own 100 ms waits run (they then return at once).
void acquire_bank(){
    if(pvr_state.ta_checked_ready)return;   // this scene already owns its TA bank
    // Crash test (dc/crashtest.txt "pvrwait", never on a play disc): one expired 100 ms slice per scene, counted as
    // a TA bank timeout, so the stop screen's rdy row can be checked in Flycast (renders never stall there).
    if(test_slices>0){
        test_slices=test_slices-1;
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
extern "C" void __wrap_pvr_set_presort_mode(bool presort){
    pvr_ready::acquire_bank();   // the target bank's tile matrix is free only once the bank is acquired
    __real_pvr_set_presort_mode(presort);
}
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
        char tmp[kRing*4+8];unsigned len=0,last=~0U;
        for(unsigned k=h-n;k!=h;++k){
            const unsigned f=ring_frame[k%kRing];
            if(f!=last){tmp[len++]=' ';tmp[len++]=char('0'+f/10%10);tmp[len++]=char('0'+f%10);tmp[len++]=':';last=f;}
            tmp[len++]=char(ring_code[k%kRing]);
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
        if(pvr_ready::first_frame==~0U)snprintf(out,size,"rdy K0 Q0 Y0");
        else snprintf(out,size,"rdy K%u Q%u Y%u first %u last %u",pvr_ready::ta_timeouts,pvr_ready::render_timeouts,
                      pvr_ready::present_timeouts,pvr_ready::first_frame,pvr_ready::last_frame);
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
    if(!pvr_present_pending())return;
#if RE4DC_PVR_LATCH
    latch::put('f');
#endif
    const auto start=timer_us_gettime64();
    // The timed waiter can become runnable before the render/vblank IRQ
    // completes, then resume with its old error after presentation finished.
    // Recheck ownership before treating that timeout as an unfinished frame.
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
    // One decision is outstanding at a time: frame N's flip normally happened
    // long before frame N+1 finishes, so this rarely blocks.
    if(pvr_present_async(present)<0){
        present_fence();
        if(pvr_present_async(present)<0){present_failures=present_failures|2;present_report();}
    }
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
#if RE4DC_TA_HASH == 3
std::uint32_t ta_hash_pend[5][4];  // TA_HASH=3: a header's words 0..3, hashed once a vertex follows it
bool ta_hash_pending[5];
void ta_hash_reset(){for(unsigned i=0;i<5;++i){ta_hash_h[i]=2166136261u;ta_hash_words[i]=0;ta_hash_pending[i]=false;}}
#else
void ta_hash_reset(){for(unsigned i=0;i<5;++i){ta_hash_h[i]=2166136261u;ta_hash_words[i]=0;}}
#endif
void ta_hash_marker(pvr_list_t list){const std::uint32_t w=0xF00D0000u|(unsigned)list;re4dc_ta_hash(&w,4);}
#endif
#if RE4DC_TA_DOUBLEBUF
// TA double buffering at run time (design-doublebuf, KOS pvr_set_vbuf_doublebuf): on in play, off
// while the sub-screen backing holds bank 1's vertex buffer (re4dc_ui_ta_single_bank at backing
// open), back on at the first scene after the backing closed (no extra fence: the single-bank
// stream_open fenced already).
bool ta_double=true,ta_double_wanted=false;
#endif
void stream_open() {
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
    pvr_scene_begin();
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
#if RE4DC_WORLD_AUTOSORT
    // list_begin, not scene_begin, waits for and acquires this TA bank.
    // Set its tiles only after that wait, never while the old bank renders.
    world_autosort=false;overlay_layer=0;pvr_set_presort_mode(true);
#endif
}
#if RE4DC_D349_RENDERER_STACK
void stream_select(pvr_list_t list){
    desired_list=list;
    if(!stream_scene){stream_open();return;}
    if(stream_list==list)return;
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
#if RE4DC_TA_HASH
    ta_hash_marker(list);
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
void stream_send(const void* data,unsigned bytes) {
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
    re4dc::render::submit_pvr(data,bytes);
    sq_unlock();
#if RE4DC_TA_GUARD
    guard_account(1,bytes/32-1); // every call is one header + its vertices
#endif
}
void stream_close(bool present) {
    RE4DC_PROFILE_SCOPE(PresentFence);
    if(!stream_scene)stream_open();
#if RE4DC_TA_GUARD
    const unsigned ta_faults=guard_scene_end();
#else
    const unsigned ta_faults=0;
#endif
    (void)ta_faults;
#if RE4DC_TA_HASH
    re4dc_log("ta_hash: frame=%u present=%u op=%08x/%u tr=%08x/%u pt=%08x/%u mod=%08x/%u,%08x/%u\n",frame,present?1u:0u,
              ta_hash_h[0],ta_hash_words[0],ta_hash_h[2],ta_hash_words[2],ta_hash_h[4],ta_hash_words[4],
              ta_hash_h[1],ta_hash_words[1],ta_hash_h[3],ta_hash_words[3]);
#endif
    sq_lock((void*)PVR_TA_INPUT);
    if(pvr_list_finish()<0 || pvr_scene_finish()<0)re4dc_missing("native stream finish failed");
    stream_scene=false;
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
    if(pvr_resolve_frame(shown)<0)re4dc_missing("native source presentation resolve failed");
    }
#endif
    if(!present)++stream_discards;
}
#endif
#if RE4DC_PERF_HUD
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
void hud_flush(HudBatch& b){if(b.n>1)stream_send(b.v,b.n*32);b.n=1;}
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
        if(h && h<=nsource && same_image(sources[h-1].image,image)){key=sources[h-1].key;return true;}
        for(unsigned n=0;n<nsource;++n) if(same_image(sources[n].image,image)) {source_hint[hint]=(unsigned char)(n+1);key=sources[n].key;return true;}
    }
#else
    if(!native)for(unsigned n=0;n<nsource;++n) if(same_image(sources[n].image,image)) {key=sources[n].key;return true;}
#endif
    if(!indexed)native=external_image_key(image,external);
    if(native<0){re4dc_log("native source identity: incompatible descriptor rejected\n");return false;}
    if(native) {
        if(identity_hits++<3)re4dc_log("native source identity: %08x-%08x (no source-texel hash)\n",external.crc,external.fnv);
#if RE4DC_COPY_LEAN
        if(!indexed && nsource<kSourceCount){source_hint[hint]=(unsigned char)(nsource+1);sources[nsource++]={image,external};}
#else
        if(!indexed && nsource<kSourceCount)sources[nsource++]={image,external};
#endif
        key=external;return true;
    }
    const unsigned metadata[]={image.width,image.height,image.format,image.palette_format,image.palette_bytes};
    key={0xffffffffU,2166136261U};hash_bytes(key,metadata,sizeof(metadata));
    hash_bytes(key,image.pixels,image_size(image));
    if(image.palette_bytes) hash_bytes(key,image.palette,image.palette_bytes);
    key.crc=~key.crc;
#if RE4DC_COPY_LEAN
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
void close_entry(Entry& entry) {
#if RE4DC_ACTOR_TRANSACTION
    // Revoke before freeing/fencing storage; forced retirement is observable.
    actor_texture_leases.retire_entry(unsigned(&entry-entries));
#endif
    if(entry.valid) used-=entry.package.vram_bytes();
    entry.package.close();entry.valid=false;
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
Entry* load(const Re4dcUiImage& image,bool pin=true,const Key* prepared_key=nullptr) {
    RE4DC_PROFILE_SCOPE(TextureResolve);RE4DC_PROFILE_COUNT(TextureLookups,1);
    if(!image.pixels || !image_size(image) || !image.width || !image.height || image.width>1024 || image.height>1024) return nullptr;
    Key key{};if(prepared_key)key=*prepared_key;else if(!image_key(image,key))return nullptr;
#if RE4DC_COPY_LEAN
    const unsigned hint=(key.crc^(key.crc>>7)^key.fnv)&127U;
    if(const unsigned h=entry_hint[hint]){
        Entry& e=entries[h-1];
        if(e.valid && e.key==key){RE4DC_TOUCH(e);RE4DC_PROFILE_COUNT(TextureHits,1);return &e;}
    }
    for(auto& e:entries) if(e.valid && e.key==key) {entry_hint[hint]=EntryHint(&e-entries+1);RE4DC_TOUCH(e);RE4DC_PROFILE_COUNT(TextureHits,1);return &e;}
#else
    for(auto& e:entries) if(e.valid && e.key==key) {RE4DC_TOUCH(e);RE4DC_PROFILE_COUNT(TextureHits,1);return &e;}
#endif
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
    if(fx_resident_only){++fx_resident_skips;return nullptr;}
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
        if(pinned+least>vram_budget){++vram_rejects;RE4DC_PROFILE_COUNT(TextureBudgetFailures,1);return nullptr;}
    }
#endif
#if RE4DC_TEX_RESIDENT || RE4DC_SUBSCREEN
    // A package absent from the disc: fail without evicting an entry or
    // touching the filesystem again (it was retried every frame).
    for(const auto& m:missing_keys) if(m.crc|m.fnv) if(m==key) return nullptr;
#endif
#if RE4DC_UI_VRAM && RE4DC_UI_FRAG_LATCH
    if(key==frag_key && frame-frag_frame<kFragRetryFrames){++frag_latched;return nullptr;} // before any eviction
#endif
    Entry* slot=nullptr;
    for(auto& e:entries) if(!e.valid){slot=&e;break;}
    if(!slot) for(auto& e:entries) if(!RE4DC_ENTRY_PINNED(e) && (!slot || e.frame<slot->frame)) slot=&e;
    if(!slot) {RE4DC_PROFILE_COUNT(TextureNoSlot,1);return nullptr;}
#if RE4DC_TEX_RESIDENT
    // Never evict a resident texture for a package that is not on the disc:
    // check it exists first (only when this load would evict), and remember
    // an absent key so it is never tried again.
#if RE4DC_TEX_PACK
    unsigned pack_offset=0,pack_size=0;
#if RE4DC_QUALITY_ASSETS
    // texlow/ keys (Standard index additions) are never in tex/, so never in the pack: skip the lookup.
    const texpack::Result pack=re4dc_std_texlow(key.crc,key.fnv)?texpack::kNotInPack:texpack::find(key,pack_offset,pack_size,frame);
#else
    const texpack::Result pack=texpack::find(key,pack_offset,pack_size,frame);
#endif
    // A pack read error is transient: no eviction, no per-file probe, and the key is not remembered as missing
    // (on a packed disc its loose file is gone); a later use retries (texpack_index.inc spaces the retries in UI frames).
    if(pack==texpack::kError){++pack_error_skips;RE4DC_PROFILE_COUNT(TextureOpenFailures,1);return nullptr;}
    const bool in_pack=pack==texpack::kFound;
    if(slot->valid && !in_pack){
#else
    if(slot->valid){
#endif
        char probe[96];RE4DC_TEX_PATH(probe,key);
        const file_t f=fs_open(probe,O_RDONLY);
        if(f==FILEHND_INVALID){
            re4dc_log("native UI: package absent, not evicting: %s\n",probe);
            missing_keys[nmissing++%(sizeof(missing_keys)/sizeof(missing_keys[0]))]=key;
            RE4DC_PROFILE_COUNT(TextureOpenFailures,1);return nullptr;
        }
        fs_close(f);
    }
#endif
    if(slot->valid){RE4DC_PROFILE_COUNT(TextureEvictions,1);RE4DC_FX_EVICTED();}
    close_entry(*slot); // caller has completed both TA and render fences
    char path[96];RE4DC_TEX_PATH(path,key);
    re4dc_log("native UI: load %s %ux%u fmt=%u\n",path,image.width,image.height,image.format);
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
    ++load_opens;
#endif
    const int heap_before=re4dc_ui_heap_free();
#if RE4DC_TEX_PACK
#define RE4DC_OPEN_PACKAGE() (in_pack?slot->package.open_streamed_at(texpack::kPath,pack_offset,pack_size):slot->package.open_streamed(path))
#else
#define RE4DC_OPEN_PACKAGE() slot->package.open_streamed(path)
#endif
    bool ok=RE4DC_OPEN_PACKAGE();
    if(!ok) {RE4DC_PROFILE_COUNT(TextureOpenFailures,1);re4dc_log("native UI: package rejected: %s\n",slot->package.error());}
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
        for(auto& e:entries) if(&e!=slot && e.valid && !RE4DC_ENTRY_PINNED(e) && (!victim || e.frame<victim->frame)) victim=&e;
        if(!victim) return false;
        RE4DC_PROFILE_COUNT(TextureEvictions,1);RE4DC_FX_EVICTED();close_entry(*victim);++reclaimed;return true;
    };
#if RE4DC_TEX_RESIDENT
    unsigned need=0;
    if(ok) {
        const auto& h=slot->package.header();need=h.data_size;
#else
    if(ok) {
        const auto& h=slot->package.header();
#endif
        ok=h.texture_count==1 && h.data_size<=vram_budget;
        // Accounted budget first, then the real pool (allocator overhead).
        while(ok && (used+h.data_size>vram_budget || pvr_mem_available()<h.data_size))
            if(!evict()) {RE4DC_PROFILE_COUNT(TextureBudgetFailures,1);ok=false;}
    }
    const unsigned vram_before=pvr_mem_available();
    if(ok) {RE4DC_PROFILE_SCOPE(TextureUpload);
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
        // A fragmented pool can refuse a block that the totals admit. Free one
        // more unreferenced upload and retry; reopening releases the partial
        // allocation (Package refuses to resume a partial upload in place).
        for(const char* e=slot->package.error();!ok && e && !std::strcmp(e,"PVR texture allocation failed") && evict();e=slot->package.error()){
            ++vram_retries;
            re4dc_log("native UI: fragmented VRAM, evicted and retrying (retries=%u free=%u)\n",vram_retries,(unsigned)pvr_mem_available());
#if RE4DC_TEX_RESIDENT
            // Evict until one contiguous block of the size fits, then read the
            // package once more (was: a full re-read per single eviction).
            for(;;){pvr_ptr_t probe=pvr_mem_malloc(need);if(probe){pvr_mem_free(probe);break;}if(!evict())break;}
#endif
            ok=RE4DC_OPEN_PACKAGE() && slot->package.upload();
        }
#if RE4DC_UI_FRAG_LATCH && RE4DC_TEX_RESIDENT
        if(!ok && slot->package.error() && !std::strcmp(slot->package.error(),"PVR texture allocation failed")){
            frag_key=key;frag_frame=frame;
            re4dc_log("native UI: no contiguous block for %ux%u (need=%u free=%u): latched %u frames\n",image.width,image.height,need,(unsigned)pvr_mem_available(),kFragRetryFrames);
        }
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
    if(!ok) slot->package.close();
    re4dc_log("native UI: bounded upload heap=%d->%d metadata=%u staging=shared-16384 source_allocation=0\n",heap_before,re4dc_ui_heap_free(),slot->package.metadata_bytes());
    if(ok)++loads;
    if(!ok) return nullptr;
    slot->valid=true;slot->key=key;
#if RE4DC_TEX_RESIDENT
    slot->frame=pin?frame:frame?frame-1:0;
#else
    slot->frame=pin?frame:0;
#endif
   used+=slot->package.vram_bytes();
    if(used>peak) peak=used;
    return slot;
}
#undef RE4DC_OPEN_PACKAGE
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
    if(!cp || cp->bytes!=i.palette_bytes)return false;
    const PaletteCopy& c=*cp;
#else
    const PaletteCopy& c=palette_copies[index%kPaletteCopies];
    if(c.owner!=index+1 || c.bytes!=i.palette_bytes)return false;
#endif
    const auto* p=static_cast<const unsigned short*>(i.palette);
#if RE4DC_UI_PALETTE_SLOTS
    if(!((unsigned(reinterpret_cast<std::uintptr_t>(p))|i.palette_bytes)&3)){   // word compare
        const auto* w=reinterpret_cast<const palette_word*>(p);
        const auto* cw=reinterpret_cast<const palette_word*>(c.data);
        for(unsigned n=0;n<i.palette_bytes/4;++n)if(cw[n]!=w[n])return false;
    }else
#endif
    for(unsigned n=0;n<i.palette_bytes/2;++n)if(c.data[n]!=p[n])return false;
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
    if(!handle_shape(image,shape,!mask) || (mask && !handle_shape(*mask,mask_shape,false))){++handle_bypass;return resolve_full(image,masked,pin);}
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
void preload_select(const re4dc::texture::SourceIdentityTable& table,unsigned& n,unsigned& resident,unsigned& bytes,unsigned limit,unsigned byte_limit){
    for(unsigned i=0;i<table.count() && n+resident<limit;++i){
        unsigned crc,fnv,width,height,format;
        if(!table.record(i,crc,fnv,width,height,format) || !width || !height || width>1024 || height>1024)continue;
#if RE4DC_QUALITY_ASSETS
        if(preload_room_pass && re4dc_std_dropped(crc,fnv))continue;
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
#if RE4DC_IO_PROBE
extern "C" void re4dc_iowrap_reset(void);                                            // io_wrap.cpp
extern "C" void re4dc_iowrap_report(const char* what, unsigned cycle, unsigned long long wall_us);
#endif
void preload_identities(){
    preload_pending=false;++preload_runs;
#if RE4DC_IO_PROBE
    re4dc_iowrap_reset(); // IO_PROBE (test only): this pass's IO tables ("iowrap: preload" below)
#endif
#if RE4DC_UI_VRAM && RE4DC_UI_FRAG_LATCH
    frag_key=Key{}; // a new room: the pool has a new shape
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
    for(auto& e:enemy_identities)if(e.archive)preload_select(e.table,n,resident,bytes,limit,byte_limit);
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
    // Package-name order ("%08x-%08x": crc, then fnv).
    for(unsigned i=1;i<n;++i){
        const PreloadPick p=preload_picks[i];unsigned j=i;
        for(;j && (preload_picks[j-1].key.crc>p.key.crc || (preload_picks[j-1].key.crc==p.key.crc && preload_picks[j-1].key.fnv>p.key.fnv));--j)preload_picks[j]=preload_picks[j-1];
        preload_picks[j]=p;
    }
    bool full=false;
#if RE4DC_TEX_KEEP
    // Kept entries of earlier rooms still hold VRAM and count in `used`; load() evicts them
    // (oldest first) for these uploads. Full is judged on this frame's pins plus what is
    // evictable, recomputed per load as pins grow and evictions free the pool.
    unsigned kept=0,kept_bytes=0;
    for(const auto& e:entries)if(e.valid && e.frame!=frame){++kept;kept_bytes+=e.package.vram_bytes();}
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
        const PreloadPick& p=preload_picks[i];
        const Re4dcUiImage image{reinterpret_cast<const void*>(1),nullptr,p.width,p.height,p.format,0xffffffffU,0};
        if(load(image,true,&p.key))++preload_loads;else ++preload_skipped;
    }
    if(frame)for(auto& e:entries)if(e.valid && e.frame==frame)e.frame=frame-1;
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
}
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
#endif
}
#if RE4DC_PVR_PIPELINE
// Called by room/texture_package.cpp (PVR_PIPELINE builds) before VRAM is
// freed or uploaded: it may be referenced by the scene not yet resolved.
#if defined(RE4DC_ENC_CENSUS) && RE4DC_ENC_CENSUS
extern "C" void re4dc_enc_frame(unsigned frame); // ENC_CENSUS (diagnostic): coarse.cpp, one line per frame mark
#endif
extern "C" void re4dc_pvr_vram_fence(){present_fence();}
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
    ++vram_claims;
    re4dc_log("native texture hold: claims=%u free=%u\n",vram_claims,(unsigned)pvr_mem_available());
}
#endif
extern "C" void re4dc_ui_vram_unclaim(){
    if(!vram_claims)return;
    if(!--vram_claims && claim_released){preload_pending=true;claim_released=0;}
    re4dc_log("native texture unclaim: claims=%u preload=%d free=%u\n",vram_claims,preload_pending?1:0,(unsigned)pvr_mem_available());
}
#endif
extern "C" int re4dc_ui_bind_core(void* archive,unsigned bytes){
    sources_reset();
    const bool ok=core_identities.adopt(archive,bytes);
    if(ok)re4dc_model_bind_draw_owner(&core_identities,archive,bytes,0);
    else re4dc_model_unbind_draw_owner(&core_identities);
    re4dc_log("native core identities: %s count=%u archive=%u metadata_owner=core\n",ok?"ok":"REJECTED",core_identities.count(),bytes);
    return ok;
}
extern "C" int re4dc_ui_bind_room(void* archive,unsigned bytes){
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
    sources_reset();bool ok=option_identities.adopt(archive,bytes);
    if(ok)re4dc_model_bind_draw_owner(&option_identities,archive,bytes,0);
    else re4dc_model_unbind_draw_owner(&option_identities);
    re4dc_log("native option identities: %s count=%u archive=%u\n",ok?"ok":"REJECTED",option_identities.count(),bytes);return ok;
}
extern "C" void re4dc_ui_unbind_option(){re4dc_model_unbind_draw_owner(&option_identities);option_identities.clear();sources_reset();}
// Player and weapon regions persist across room retirement when the source
// retains them. Their explicit source release/overwrite boundaries clear views.
extern "C" int re4dc_ui_bind_player(void* archive,unsigned bytes){
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
extern "C" void re4dc_ui_unbind_player(){re4dc_actor_archive_retire(&player_identities);re4dc_model_unbind_draw_owner(&player_identities);player_identities.clear();sources_reset();}
extern "C" void re4dc_ui_unbind_weapon(){re4dc_actor_archive_retire(&weapon_identities);re4dc_model_unbind_draw_owner(&weapon_identities);weapon_identities.clear();sources_reset();}
extern "C" int re4dc_ui_bind_enemy(void* archive,unsigned bytes){
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
extern "C" void re4dc_ui_retire_room(){
    re4dc_actor_archive_retire_transient();
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
    for(auto& entry:entries)entry.frame=0;   // kept resident, oldest: evictable
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
struct GlyphCell { const void* sheet; const void* clut; short u,v; unsigned char cw,ch,bank; bool valid; unsigned frame; };
struct GlyphQuad { short x0,y0,x1,y1; unsigned char cell,cw,ch,bank; unsigned argb; }; // x/y in 1/4 px
static_assert(sizeof(GlyphQuad)==16);
struct GlyphBank { const void* clut; unsigned sum; bool valid; };
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
    glyph_atlas=pvr_mem_malloc(kGlyphAtlasBytes);
    if(!glyph_atlas){re4dc_log("native mes: glyph atlas allocation FAILED (free=%u); message text off\n",before);return;}
    alignas(32) static const unsigned char zero[512]={};
    for(unsigned n=0;n<kGlyphAtlasBytes;n+=sizeof(zero))pvr_txr_load(zero,(char*)glyph_atlas+n,sizeof(zero));
    pvr_set_pal_format(PVR_PAL_ARGB8888);
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
    for(unsigned i=0;i<16;++i)pvr_set_pal_entry(unsigned(free_bank)*16+i,glyph_color((p[2*i]<<8)|p[2*i+1],format));
    glyph_banks[free_bank]={clut,sum,true};
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
    pvr_txr_load(cell,(char*)glyph_atlas+square*32768U+((glyph_twx[cx]|glyph_twy[cy])<<9),sizeof(cell));
    c={g.sheet,g.clut,(short)g.u,(short)g.v,(unsigned char)g.cw,(unsigned char)g.ch,(unsigned char)bank,true,frame};
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
// One run: a header when the palette bank changes, then a 4-vertex strip per glyph (a strip
// after an end-of-strip vertex reuses the last header).
void glyph_draw_run(unsigned first,unsigned count){
    alignas(32) pvr_vertex_t buf[1+4*16];
    unsigned n=0;int bank=-1;
    auto flush=[&]{
        if(!n)return;
#if RE4DC_PVR_STREAM
        stream_send(buf,n*sizeof(pvr_vertex_t));
#else
        re4dc::render::submit_pvr(buf,n*sizeof(pvr_vertex_t));
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
        const float x[4]={g.x0*0.25f,g.x1*0.25f,g.x0*0.25f,g.x1*0.25f},y[4]={g.y0*0.25f,g.y0*0.25f,g.y1*0.25f,g.y1*0.25f};
        const float u[4]={u0,u0+g.cw/256.0f,u0,u0+g.cw/256.0f},v[4]={v0,v0,v0+g.ch/kH,v0+g.ch/kH};
        for(unsigned k=0;k<4;++k){
            pvr_vertex_t& p=buf[n++];
            p.flags=k==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;p.x=RE4DC_UI_X(x[k]);p.y=RE4DC_UI_Y(y[k]);p.z=layer;p.u=u[k];p.v=v[k];p.argb=g.argb;p.oargb=0;
        }
        ++glyph_drawn;
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
#endif
    params.autosort_disabled=1; // source OT is the UI blending order
    ready=pvr_init(&params)==0;
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
#if RE4DC_PVR_LATCH
        latch::install();   // after install_fast_wake: chains its render-done handler
#endif
#if RE4DC_TA_GUARD || RE4DC_PERF_HUD || RE4DC_TA_VERTBUF_KB!=1024 || RE4DC_TA_DOUBLEBUF || RE4DC_TA_OPB_BINS!=16 || RE4DC_TA_OPB_OVERFLOW!=3
        re4dc_log("native VRAM layout: vertbuf=%u KiB x%u banks (%s) opb_bins=%u overflow=%u texture_pool_free=%u\n",
            unsigned(RE4DC_TA_VERTBUF_KB),2U,RE4DC_TA_DOUBLEBUF?"double-buffered":"single-bank use",unsigned(RE4DC_TA_OPB_BINS),unsigned(RE4DC_TA_OPB_OVERFLOW),(unsigned)pvr_mem_available());
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
    re4dc_prepare_model_assets();
}
// Skipped iteration: nothing to present; the previous picture stays. Frame boundary only.
extern "C" void re4dc_ui_end_frame_skip(){
    re4dc_pcs_frame(frame+pace_skipped_frames);
}
#endif
extern "C" void re4dc_ui_begin(){
#if RE4DC_PACE_CATCHUP
    pace_skip_frame=false;
#endif
#if RE4DC_PERF_HUD
    hud_begin_prev=hud_begin;hud_begin=timer_us_gettime64();
#endif
    re4dc_model_preparation_frame();
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
    nquad=0;model_used=0;++frame;
#if RE4DC_ACTOR_TRANSACTION
#if RE4DC_ACTOR_EARLY_COARSE
    actor_texture_leases.begin_frame(frame); // Trans tickets name this exact next frame
#else
    actor_texture_leases.retire_frame(); // submitted pins retain normal GPU fencing
#endif
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
    if((nquad+1)*sizeof(Re4dcUiQuad)>deferred_top){++dropped;++frame_queue_drops;stream_aborted=true;return;}
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
        pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,PVR_LIST_TR_POLY,fmt,t.width,t.height,
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
        alignas(32) pvr_vertex_t commands[5]{};std::uint32_t count;
        re4dc::render::begin_pvr_packet(commands,count,header);
        pvr_vertex_t* v=commands+count;const unsigned order[]={0,1,3,2};
        const float layer=overlay_depth();
        for(unsigned n=0;n<4;++n){unsigned j=order[n];v[n].flags=n==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;
            v[n].x=RE4DC_UI_X(q.xy[2*j]);v[n].y=RE4DC_UI_Y(q.xy[2*j+1]);v[n].z=layer;
            v[n].u=q.uv[2*j]*q.image.width/t.width;v[n].v=q.uv[2*j+1]*q.image.height/t.height;v[n].argb=q.color;}
#if RE4DC_PVR_STREAM
        stream_send(commands,sizeof(commands));
#else
        re4dc::render::submit_pvr(commands,sizeof(commands));
#endif
        ++drawn;

}
static void ui_order_flush(){
    if(re4dc_vi_black() || stream_aborted)return;
    stream_select(PVR_LIST_TR_POLY);
    while(quads_flushed<nquad && !stream_aborted)ui_draw_quad(quads_flushed++);
}
#endif
extern "C" void re4dc_ui_present(){
    RE4DC_PROFILE_SCOPE(UiDrain);
    if(!frame_ready)return;
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
#if RE4DC_SS_UI_ORDER
    if(frame%120==0)re4dc_log("native UI order: frame=%u active=%u flushed=%u queued=%u\n",frame,unsigned(ui_order),quads_flushed,nquad);
    for(unsigned i=quads_flushed;i<nquad && !movie_override && !re4dc_vi_black();++i)ui_draw_quad(i);
#else
    for(unsigned i=0;i<nquad && !movie_override && !re4dc_vi_black();++i){
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
        pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,PVR_LIST_TR_POLY,fmt,t.width,t.height,
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
        alignas(32) pvr_vertex_t commands[5]{};std::uint32_t count;
        re4dc::render::begin_pvr_packet(commands,count,header);
        pvr_vertex_t* v=commands+count;const unsigned order[]={0,1,3,2};
        const float layer=overlay_depth();
        for(unsigned n=0;n<4;++n){unsigned j=order[n];v[n].flags=n==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;
            v[n].x=RE4DC_UI_X(q.xy[2*j]);v[n].y=RE4DC_UI_Y(q.xy[2*j+1]);v[n].z=layer;
            v[n].u=q.uv[2*j]*q.image.width/t.width;v[n].v=q.uv[2*j+1]*q.image.height/t.height;v[n].argb=q.color;}
#if RE4DC_PVR_STREAM
        stream_send(commands,sizeof(commands));
#else
        re4dc::render::submit_pvr(commands,sizeof(commands));
#endif
        ++drawn;
    }
#endif
#if RE4DC_PACE_CATCHUP && RE4DC_PACE_DEBUG && RE4DC_PVR_STREAM
    {int pace_mode;if(re4dc_pace_note(&pace_mode) && !re4dc_vi_black())pace_note_draw(pace_mode);}
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
    if(frame%120==0) re4dc_log("native UI: frame=%u quads=%u drawn=%u missing=%u unsupported=%u drops=%u vram=%u peak=%u staging=%u loads=%u freed=%u culled=%u fb=%08x,%08x black=%d\n",frame,nquad,drawn,missing,unsupported,dropped,used,peak,staging_peak,loads,reclaimed,culled,(unsigned)pvr_get_front_buffer(),(unsigned)pvr_get_back_buffer(),re4dc_vi_black());
#if RE4DC_UI_VRAM
    if(frame%120==0) re4dc_log("native UI VRAM: frame=%u budget=%u used=%u free=%u rejects=%u retries=%u evicted=%u\n",frame,vram_budget,used,(unsigned)pvr_mem_available(),vram_rejects,vram_retries,reclaimed);
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
#endif
#if RE4DC_EFFECT_SPRITES
    if(frame%120==0) re4dc_log("native effect sprites: frame=%u queued=%u direct=%u missing=%u dropped=%u capped=%u culled=%u peak=%u\n",frame,fx_queued,fx_direct,fx_missing,fx_dropped,fx_capped,fx_culled,fx_peak);
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
    if(frame%120==0) re4dc_log("native effect guard: frame=%u resident_only_skips=%u\n",frame,fx_resident_skips);
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
    const auto render_end=timer_us_gettime64();
    re4dc_model_draw_plan_frame(frame);
#if RE4DC_PVR_STREAM
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
    if(stream_retire){for(auto& entry:entries)entry.frame=0;stream_retire=false;}
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

extern "C" int re4dc_model_diagnostic_enabled(){
    if(model_diagnostic<0){
        file_t f=fs_open("/cd/dc/model-diagnostic.flag",O_RDONLY);
        model_diagnostic=f>=0;if(f>=0)fs_close(f);
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
extern "C" int re4dc_model_packet_reserve(const Re4dcModelPart* p,Re4dcModelPacket* out){
    unsigned reason=0;
    if(!frame_ready || !re4dc_model_diagnostic_enabled())reason|=1;
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
        ++model_capacity_rejects;return 0;
    }
#endif
    if(!p->image.pixels)reason|=64;
    if(!p->image.width || !p->image.height || p->image.width>1024 || p->image.height>1024)reason|=128;
    if(reason){
        ++model_state_rejects;
        for(unsigned bit=0;bit<8;++bit)if(reason&(1U<<bit)){
            if(model_state_bits[bit]++<2)re4dc_log("native model state reject: reason=%02x model=%08x info=%08x part=%08x material=%02x blend=%u depth=%u wrap=%u,%u image=%08x %ux%u fmt=%u vertices=%u stream=%u\n",reason,(unsigned)p->model,(unsigned)p->info,(unsigned)p->part,p->material_flags,p->blend,p->depth_mode,p->wrap_s,p->wrap_t,(unsigned)p->image.pixels,p->image.width,p->image.height,p->image.format,p->position_count,p->stream_bytes);
        }
        return 0;
    }
    if(!ensure_model_storage())return 0;
    if(model_used+4>kModelPacketBytes/32){++model_capacity_rejects;return 0;}
    // Same default padding policy as convert_tpl; binding below checks the
    // actual package. A different native layout triggers exact UV preparation.
    unsigned width=8,height=8;
    while(width<p->image.width)width*=2;
    while(height<p->image.height)height*=2;
    model_pending=model_used+1;
    out->vertices=model_packets+model_pending;out->capacity=kModelPacketBytes/32-model_pending;
    out->u_scale=float(p->image.width)/width;out->v_scale=float(p->image.height)/height;
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
#if RE4DC_FRONT_NATIVE>=2 && RE4DC_UI_HANDLES && RE4DC_D349_RENDERER_STACK
// FRONT_NATIVE=2 group 8 (model_bridge.cpp): the PVR header a part would get, computed without
// side effects (no texture load, no handle touch, no pass switch, no header cache). A copy of
// re4dc_model_packet_reserve's state checks and re4dc_model_packet_begin's header build; the
// compare against the header packet_begin really built for the source part proves the copy.
extern "C" void re4dc_front_header_built(const void* header,unsigned alpha_state);
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
extern "C" int re4dc_model_header_preview(const Re4dcModelPart* p,void* out){
    if(p->blend>4 || p->cull>2 || p->depth_mode>2 || p->wrap_s>1 || p->wrap_t>1)return 0;
    if((p->material_flags&4) && (!p->mask.pixels || !p->mask_same_uv || p->mask_ref!=0 ||
       p->mask.width!=p->image.width || p->mask.height!=p->image.height))return 0;
    if(p->image.format>=8 && p->image.format!=14)return 0;
    if(!p->image.pixels || !p->image.width || !p->image.height || p->image.width>1024 || p->image.height>1024)return 0;
    Entry* handle=resolve_peek(p->image,(p->material_flags&4)?p:nullptr);
    if(!handle)return 0;
    const auto& t=handle->package.textures()[0];
    if((p->wrap_s && t.width!=p->image.width)||(p->wrap_t && t.height!=p->image.height))return 0;
    unsigned fmt=re4dc::texture::pvr_format(t);
    const pvr_list_t list=select_model_pass(p);
    pvr_poly_hdr_t header;
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,list,fmt,t.width,t.height,handle->package.pvr_texture(0),PVR_FILTER_BILINEAR);
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
extern "C" int re4dc_model_packet_begin(const Re4dcModelPart* p,Re4dcModelPacket* out){
    RE4DC_PROFILE_SCOPE(PacketPack);
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
        handle=load(baked,false,&baked_key);if(!handle){++model_texture_rejects;return 0;}
    }else{
#endif
#if RE4DC_UI_HANDLES
    const Re4dcModelPart* masked=nullptr;
#if RE4DC_D349_RENDERER_STACK
    if(p->material_flags&4)masked=p;
#endif
#if RE4DC_MESH_TEXTURES
    handle=resolve(p->image,masked,false);if(!handle){++model_texture_rejects;return 0;}
#else
    Entry* handle=resolve(p->image,masked,false);if(!handle){++model_texture_rejects;return 0;}
#endif
#else
    Key prepared{};const Key* key=nullptr;
#if RE4DC_D349_RENDERER_STACK
    if(p->material_flags&4){if(!model_mask_key(p,prepared)){++model_texture_rejects;return 0;}key=&prepared;}
#endif
#if RE4DC_MESH_TEXTURES
    handle=load(p->image,false,key);if(!handle){
#if RE4DC_D349_RENDERER_STACK
        if(key)log_pair_miss(p,*key);
#endif
        ++model_texture_rejects;return 0;}
#else
    Entry* handle=load(p->image,false,key);if(!handle){
#if RE4DC_D349_RENDERER_STACK
        if(key)log_pair_miss(p,*key);
#endif
        ++model_texture_rejects;return 0;}
#endif
#endif
#if RE4DC_MESH_TEXTURES
    }
#endif
    const auto& t=handle->package.textures()[0];
    // Repeating a padded image would repeat its border. Reject, never change wrap.
#if RE4DC_MESH_TEXTURES
    // A baked texture is addressed 0..1 as authored: no source image size to match.
    if(!model_texture && ((p->wrap_s && t.width!=p->image.width)||(p->wrap_t && t.height!=p->image.height))){++model_wrap_rejects;return 0;}
#else
    if((p->wrap_s && t.width!=p->image.width)||(p->wrap_t && t.height!=p->image.height)){++model_wrap_rejects;return 0;}
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
#endif
    pvr_poly_hdr_t header;std::uint32_t count;
#if RE4DC_D349_RENDERER_STACK
    const unsigned header_key=list|(p->blend<<3)|(p->depth_mode<<6)|(p->wrap_s<<8)|(p->wrap_t<<10)|((p->material_flags&4)<<12)|(p->cull<<16)
#if RE4DC_NATIVE_FOG
        |(p->source_key[2]?1U<<20:0U) // NATIVE_FOG flag (model_bridge.cpp)
#endif
        ;
    if(handle->model_header_key==header_key){header=handle->model_header;++model_header_hits;}
    else {
#endif
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,list,fmt,t.width,t.height,handle->package.pvr_texture(0),PVR_FILTER_BILINEAR);
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
    pvr_poly_compile(&header,&c);++model_header_builds;
#if RE4DC_D349_RENDERER_STACK
        handle->model_header=header;handle->model_header_key=header_key;
    }
#endif
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
    model_pending=model_used+count;model_handle=handle;
    out->vertices=model_packets+model_pending;out->capacity=kModelPacketBytes/32-model_pending;
#if RE4DC_MESH_TEXTURES
    if(model_texture){out->u_scale=1.0f;out->v_scale=1.0f;}
    else {
#endif
    if(out->u_scale!=float(p->image.width)/t.width || out->v_scale!=float(p->image.height)/t.height)++model_scale_rebuilds;
    out->u_scale=float(p->image.width)/t.width;out->v_scale=float(p->image.height)/t.height;
#if RE4DC_MESH_TEXTURES
    }
#endif
    if(p->alpha_state&256)++model_alpha_vertex;else ++model_alpha_material;
    if(!(p->alpha_state&256) && (p->alpha_state&255)<255)++model_alpha_faded;
    if(model_parts<6)re4dc_log("native model DIAGNOSTIC source=%08x info=%08x part=%08x positions=%u stride=%u stream=%u flags=%08x material=%02x cull=%u\n",(unsigned)p->model,(unsigned)p->info,(unsigned)p->part,p->position_count,p->position_stride,p->stream_bytes,p->flags,p->material_flags,p->cull);
    return 1;
}
extern "C" void re4dc_model_packet_commit(unsigned count){
    // A loaded but wholly clipped/rolled-back part owns no submitted packets.
    // Keep its upload cached; pin only when this part actually commits a draw.
    if(count){
        model_handle->frame=frame;model_used=model_pending+count;
        if(model_used*32>model_peak)model_peak=model_used*32;
#if RE4DC_PVR_STREAM
        stream_send(model_packets,model_used*32);
        stream_model_bytes+=model_used*32;
        if(stream_model_bytes>stream_peak_bytes)stream_peak_bytes=stream_model_bytes;
        model_used=0; // PVR owns copied packets; reuse the same bounded scratch.
#endif
    }
}
extern "C" void re4dc_model_result(unsigned reason,unsigned input,unsigned output){
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
#if RE4DC_PVR_STREAM
    // Previous chunks may already be in TA. Never present an incomplete model:
    // reject further submissions and let the same source owner discard/fence it.
    stream_aborted=true;model_used=0;model_handle=nullptr;
#endif
}

extern "C" int re4dc_model_direct_enabled(){return RE4DC_TA_DIRECT;}
#if RE4DC_TA_HASH
extern "C" void re4dc_ta_hash(const void* data,unsigned bytes){
    const unsigned l=(unsigned)stream_list<5?(unsigned)stream_list:2;
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
#if RE4DC_TA_DIRECT
    if(direct_open){re4dc_missing("native direct part nested");return 0;}
    Re4dcModelPacket packet{};
    // Same qualification, texture bind, pass selection and header as the
    // packet path; the header lands in the slab, then goes out by store queue.
    if(!re4dc_model_packet_begin(p,&packet))return 0;
    if(!stream_scene)stream_open();
    auto* sq=static_cast<std::uint32_t*>(static_cast<void*>(sq_lock((void*)PVR_TA_INPUT)));
    const auto* header=reinterpret_cast<const std::uint32_t*>(model_packets+model_used);
    for(unsigned i=0;i<8;++i)sq[i]=header[i];
#if RE4DC_TA_HASH
    re4dc_ta_hash(header,32);
#endif
    sq_flush(sq);
    direct_open=true;
    model_handle->frame=frame; // the header is in the TA: pinned for this scene
    ++frame_pvr_calls;frame_pvr_bytes+=32;stream_model_bytes+=32;
    out->sq=sq+8;out->scratch=packet.vertices;out->scratch_capacity=packet.capacity;
    out->u_scale=packet.u_scale;out->v_scale=packet.v_scale;
    return 1;
#else
    (void)p;(void)out;return 0;
#endif
}
extern "C" void re4dc_model_direct_end(unsigned vertices){
#if RE4DC_TA_DIRECT
    if(!direct_open)return;
    sq_unlock();direct_open=false;
    if(vertices>32767)re4dc_missing("native direct part exceeded the store-queue window");
    ++direct_parts;direct_slots+=vertices;
#if RE4DC_TA_GUARD
    guard_account(1,vertices);
#endif
    frame_pvr_bytes+=vertices*32;stream_model_bytes+=vertices*32;
    if(stream_model_bytes>stream_peak_bytes)stream_peak_bytes=stream_model_bytes;
    model_used=0;
#else
    (void)vertices;
#endif
}
#if RE4DC_COARSE_ONE_SUBMIT && RE4DC_TA_DIRECT
extern "C" int re4dc_model_direct_begin_reserved(const Re4dcModelPart* p,const Re4dcModelPacket* reserved,Re4dcModelDirect* out){
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
    Entry* handle=static_cast<Entry*>(h?h->entry:nullptr);
#if RE4DC_MESH_TEXTURES
    if(model_texture)return nullptr;
#endif
    // The refusals the close + begin pair would meet for this captured material in this state (packet_reserve's
    // frame / stream terms, packet_begin's list and cache hit, direct_begin's nesting).
    if(!p || !h || !h->valid || !handle || !direct_open || !frame_ready || stream_aborted || draining_parts || !stream_scene ||
       !re4dc_model_diagnostic_enabled() || model_used+4>kModelPacketBytes/32 || vertices>32767 ||
       unsigned(stream_list)!=h->list || select_model_pass(p)!=stream_list || leon_header_key(p,h->list)!=h->key ||
       handle->model_header_key!=h->key || std::memcmp(h->words,&handle->model_header,32))return nullptr;
    // re4dc_model_direct_end(vertices)
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
    model_pending=model_used+count;model_handle=handle;
    if(h->scale_rebuild)++model_scale_rebuilds;
    if(p->alpha_state&256)++model_alpha_vertex;else ++model_alpha_material;
    if(!(p->alpha_state&256) && (p->alpha_state&255)<255)++model_alpha_faded;
    if(model_parts<6)re4dc_log("native model DIAGNOSTIC source=%08x info=%08x part=%08x positions=%u stride=%u stream=%u flags=%08x material=%02x cull=%u\n",(unsigned)p->model,(unsigned)p->info,(unsigned)p->part,p->position_count,p->position_stride,p->stream_bytes,p->flags,p->material_flags,p->cull);
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
    return actor_texture_leases.acquire(unsigned(e-entries),frame,*out)?1:0;
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
#if RE4DC_COARSE >= 2
    static unsigned dbg;
    if(dbg<4 || dbg%600==0)re4dc_log("COARSE2 begin n=%u frame=%u ready=%d scene=%d list=%d desired=%d aborted=%d direct=%d finished=%d\n",
        dbg,frame,(int)frame_ready,(int)stream_scene,(int)stream_list,(int)desired_list,(int)stream_aborted,(int)direct_open,(int)source_draws_finished);
    ++dbg;
#endif
    if(!frame_ready || stream_aborted || direct_open)return nullptr;
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
    const auto* h=reinterpret_cast<const std::uint32_t*>(&header[f]);
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
    if(!frame_ready || stream_aborted || direct_open)return nullptr;
    const Key key{crc,fnv};
    const Re4dcUiImage image{&key,nullptr,width,height,5,0,0}; // size checks only: pixels are never read
    Entry* handle=load(image,false,&key);if(!handle){++model_texture_rejects;return nullptr;}
    handle->frame=frame; // the header goes to the TA now: pinned for this scene
    const auto& t=handle->package.textures()[0];
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,PVR_LIST_OP_POLY,re4dc::texture::pvr_format(t),t.width,t.height,handle->package.pvr_texture(0),PVR_FILTER_BILINEAR);
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
    pvr_poly_hdr_t header;pvr_poly_compile(&header,&c);++model_header_builds;
    stream_select(PVR_LIST_OP_POLY);
    auto* sq=static_cast<std::uint32_t*>(static_cast<void*>(sq_lock((void*)PVR_TA_INPUT)));
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
    if(!frame_ready || stream_aborted || !ensure_model_storage() || model_used+8>kModelPacketBytes/32)return 0;
    const Key key{crc,fnv};
    const Re4dcUiImage image{&key,nullptr,width,height,5,0,0}; // size checks only: pixels are never read
    Entry* handle=load(image,false,&key);if(!handle){++model_texture_rejects;return 0;}
    const auto& t=handle->package.textures()[0];
    stream_select(PVR_LIST_PT_POLY);
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,PVR_LIST_PT_POLY,re4dc::texture::pvr_format(t),t.width,t.height,handle->package.pvr_texture(0),PVR_FILTER_BILINEAR);
    c.gen.culling=PVR_CULLING_NONE;c.depth.comparison=PVR_DEPTHCMP_GEQUAL;c.depth.write=PVR_DEPTHWRITE_ENABLE;
    c.blend.src=PVR_BLEND_ONE;c.blend.dst=PVR_BLEND_ZERO;c.txr.env=PVR_TXRENV_MODULATEALPHA;c.txr.alpha=PVR_TXRALPHA_ENABLE;
    c.txr.uv_clamp=PVR_UVCLAMP_UV;
#if RE4DC_NATIVE_FOG
    c.gen.fog_type=fog?PVR_FOG_TABLE:PVR_FOG_DISABLE;
#else
    (void)fog;
#endif
    pvr_poly_hdr_t header;pvr_poly_compile(&header,&c);++model_header_builds;
    std::uint32_t count;re4dc::render::begin_pvr_packet(model_packets+model_used,count,header);
    model_pending=model_used+count;model_handle=handle;
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
int defer_part(const Re4dcModelPart* p,const SourceLighting* source){
    if(draining_parts)return 0;
    if(source_draws_finished){RE4DC_PROFILE_COUNT(DirectTR,1);return 0;}
    if(select_model_pass(p)==PVR_LIST_OP_POLY){RE4DC_PROFILE_COUNT(DirectOP,1);return 0;}
    RE4DC_PROFILE_SCOPE(TranslucentEnqueue);
    if(!frame_ready || stream_aborted)return 1;
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
            ++deferred_drops;++frame_queue_drops;stream_aborted=true;re4dc_model_result(3,0,0);return 1;
        }
        storage=deferred_spill;top=&deferred_spill_top;
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
    if(deferred_last)deferred_last->next=node;else deferred_first=node;
    deferred_last=node;++deferred_count;
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
extern "C" int re4dc_model_defer_part(const Re4dcModelPart* p){
#if RE4DC_COPY_LEAN && RE4DC_D349_RENDERER_STACK
    return defer_part(p,p->lighting);
#elif RE4DC_D349_RENDERER_STACK
    if(draining_parts)return 0;
    if(source_draws_finished){RE4DC_PROFILE_COUNT(DirectTR,1);return 0;}
    if(select_model_pass(p)==PVR_LIST_OP_POLY){RE4DC_PROFILE_COUNT(DirectOP,1);return 0;}
    RE4DC_PROFILE_SCOPE(TranslucentEnqueue);
    if(!frame_ready || stream_aborted)return 1;
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
            ++deferred_drops;++frame_queue_drops;stream_aborted=true;re4dc_model_result(3,0,0);return 1;
        }
        storage=deferred_spill;top=&deferred_spill_top;
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
    if(deferred_last)deferred_last->next=node;else deferred_first=node;
    deferred_last=node;++deferred_count;
    deferred_peak=std::max(deferred_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
    frame_queue_peak=std::max(frame_queue_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
    RE4DC_PROFILE_HIGH(QueuePeak,frame_queue_peak);
    return 1;
#else
    (void)p;return 0;
#endif
}
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
struct FxHeaderKey{unsigned fmt,w,h;const void* txr;unsigned char src,dst,screen;};
FxHeaderKey fx_hdr_key{~0U,0,0,nullptr,0,0,0};
alignas(32) pvr_poly_hdr_t fx_hdr_cache;
#endif
void fx_send(unsigned char* packet,bool screen){
#if RE4DC_WORLD_AUTOSORT
    if(world_autosort && screen){
        auto* b=reinterpret_cast<pvr_sprite_txr_t*>(packet+sizeof(pvr_poly_hdr_t));
        b->az=b->bz=b->cz=overlay_depth();
    }
#else
    (void)screen;
#endif
    stream_send(packet,kSpritePacket);
}
void fx_packet(const Re4dcEffectSprite& s,Entry* e,unsigned char* out){
    const auto& t=e->package.textures()[0];
    auto* h=reinterpret_cast<pvr_poly_hdr_t*>(out);
#if defined(RE4DC_ESP_SPRITE_FAST) && RE4DC_ESP_SPRITE_FAST
    const unsigned fmt=re4dc::texture::pvr_format(t);const void* txr=e->package.pvr_texture(0);
    if(fx_hdr_key.fmt!=fmt || fx_hdr_key.w!=t.width || fx_hdr_key.h!=t.height || fx_hdr_key.txr!=txr ||
       fx_hdr_key.src!=s.src || fx_hdr_key.dst!=s.dst || fx_hdr_key.screen!=s.screen){
        pvr_sprite_cxt_t c;pvr_sprite_cxt_txr(&c,PVR_LIST_TR_POLY,fmt,t.width,t.height,
                                              const_cast<void*>(txr),PVR_FILTER_BILINEAR);
        c.gen.culling=PVR_CULLING_NONE;
        c.depth.comparison=s.screen?PVR_DEPTHCMP_ALWAYS:PVR_DEPTHCMP_GEQUAL;c.depth.write=PVR_DEPTHWRITE_DISABLE;
        c.blend.src=(pvr_blend_mode_t)s.src;c.blend.dst=(pvr_blend_mode_t)s.dst;
        c.txr.env=PVR_TXRENV_MODULATEALPHA;c.txr.uv_clamp=PVR_UVCLAMP_UV;
#if RE4DC_NATIVE_FOG
        c.gen.fog_type=s.screen?PVR_FOG_DISABLE:PVR_FOG_TABLE; // table: native_static.cpp re4dc_fog_frame
#endif
        pvr_sprite_compile(&fx_hdr_cache,&c);
        fx_hdr_key=FxHeaderKey{fmt,t.width,t.height,txr,(unsigned char)s.src,(unsigned char)s.dst,(unsigned char)s.screen};
    }
    *h=fx_hdr_cache;h->argb=s.color;h->oargb=0;
#else
    pvr_sprite_cxt_t c;pvr_sprite_cxt_txr(&c,PVR_LIST_TR_POLY,re4dc::texture::pvr_format(t),t.width,t.height,
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
    const float su=float(s.image.width)/t.width,sv=float(s.image.height)/t.height;
    b->flags=PVR_CMD_VERTEX_EOL;
    b->ax=s.x[0];b->ay=s.y[0];b->az=s.z[0];b->bx=s.x[1];b->by=s.y[1];b->bz=s.z[1];
    b->cx=s.x[2];b->cy=s.y[2];b->cz=s.z[2];b->dx=s.x[3];b->dy=s.y[3];b->dummy=0;
    b->auv=PVR_PACK_16BIT_UV(s.u[0]*su,s.v[0]*sv);b->buv=PVR_PACK_16BIT_UV(s.u[1]*su,s.v[1]*sv);
    b->cuv=PVR_PACK_16BIT_UV(s.u[2]*su,s.v[2]*sv);
}
}
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
extern "C" float re4dc_fog_gate_far() __attribute__((weak)); // ACTOR_FOG_GATE builds (native_static.cpp)
#endif
// EFFECT_SPRITES (effects30.mk): one effect sprite from EspCommonTrans. Never aborts the
// frame: without texture, over the per-frame cap or without queue room the sprite is dropped.
extern "C" int re4dc_effect_sprite(const Re4dcEffectSprite* s){
    if(!frame_ready || stream_aborted || draining_parts)return 0;
    if(fx_frame!=frame){fx_frame=frame;fx_count=0;
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
        fx_new_loads=0;
#endif
    }
    if((s->color>>24)==0){++fx_culled;return 0;}
#if defined(RE4DC_ESP_SPRITE_FAST) && RE4DC_ESP_SPRITE_FAST
    {   // ESP_SPRITE_FAST: std::isfinite on the bits (UI_QUAD_LEAN's test): an all-ones exponent carries into bit
        // 31 of (bits & 0x7f800000) + 0x00800000; no __unordsf2 call per coordinate.
        typedef std::uint32_t fx_word __attribute__((may_alias));
        const fx_word* xw=reinterpret_cast<const fx_word*>(s->x);
        const fx_word* yw=reinterpret_cast<const fx_word*>(s->y);
        const fx_word* zw=reinterpret_cast<const fx_word*>(s->z);
        std::uint32_t top=0;
        for(unsigned i=0;i<4;++i)
            top|=((xw[i]&0x7f800000U)+0x00800000U)|((yw[i]&0x7f800000U)+0x00800000U)|((zw[i]&0x7f800000U)+0x00800000U);
        if(top&0x80000000U){++fx_culled;return 0;}
    }
#else
    for(unsigned i=0;i<4;++i)if(!std::isfinite(s->x[i]) || !std::isfinite(s->y[i]) || !std::isfinite(s->z[i])){++fx_culled;return 0;}
#endif
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
    {   // EFFECT_ROOM: spend the cap and the queue only on sprites that can change a pixel. Off screen:
        // all four corners past one edge of the 640x480 frame. Beyond the fog: every corner deeper than
        // the fogged View far, where the fog table is at 100% (the sprite is the fog colour there).
        float x0=s->x[0],x1=s->x[0],y0=s->y[0],y1=s->y[0],zmax=s->z[0];
        for(unsigned i=1;i<4;++i){
            x0=std::min(x0,s->x[i]);x1=std::max(x1,s->x[i]);y0=std::min(y0,s->y[i]);y1=std::max(y1,s->y[i]);
            zmax=std::max(zmax,s->z[i]);
        }
        if(x1<0.0f || x0>640.0f || y1<0.0f || y0>480.0f){++fx_culled;return 0;}
        const float fog_far=(!s->screen && re4dc_fog_gate_far)?re4dc_fog_gate_far():0.0f;
        if(fog_far>0.0f && zmax*fog_far<1.0f){++fx_culled;return 0;}
    }
#endif
    if(fx_count>=RE4DC_EFFECT_SPRITE_MAX){++fx_capped;return 0;}
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
    fx_resident_only=frame-fx_evict_frame<=1 || fx_new_loads>=kFxNewLoads;
    const unsigned opens=load_opens;
#endif
#if RE4DC_UI_HANDLES
    Entry* e=resolve(s->image,nullptr,true);
#else
    Entry* e=load(s->image);
#endif
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
    fx_resident_only=false;fx_new_loads+=load_opens-opens;
#endif
    if(!e){++fx_missing;return 0;}
    if(source_draws_finished){
        alignas(32) unsigned char packet[kSpritePacket];fx_packet(*s,e,packet);
        stream_select(PVR_LIST_TR_POLY);fx_send(packet,s->screen);
        ++fx_direct;++fx_count;return 1;
    }
    const unsigned required=kSpriteNode+kSpritePacket,margin=8192;
    unsigned char* storage=frame_storage;unsigned* top=&deferred_top;
    if(required+margin>deferred_top || deferred_top-required-margin<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad)))){
        if(!deferred_spill){deferred_spill=static_cast<unsigned char*>(re4dc_model_deferred_storage(&deferred_spill_capacity));deferred_spill_top=deferred_spill_capacity;}
        // The spill tail holds only model snapshots and sprites (no UI lane): no margin.
        if(!deferred_spill || required>deferred_spill_top){++fx_dropped;return 0;}
        storage=deferred_spill;top=&deferred_spill_top;
    }
    *top-=required;
    auto* node=new(storage+*top) DeferredPart{};node->lighting=kSpriteTag;node->changed[0]=s->screen;
    fx_packet(*s,e,storage+*top+kSpriteNode);
    if(deferred_last)deferred_last->next=node;else deferred_first=node;
    deferred_last=node;++deferred_count;++fx_queued;++fx_count;
    fx_peak=std::max(fx_peak,fx_count);
    frame_queue_peak=std::max(frame_queue_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
    return 1;
}
#if defined(RE4DC_NATIVE_LASER) && RE4DC_NATIVE_LASER
// Esp19's source line becomes one untextured, colour-interpolated strip in
// the same bounded OT queue as effect sprites. All packet bytes are copied
// before returning; no source pointer, texture, heap or frame owner is added.
extern "C" int re4dc_effect_line(const Re4dcEffectLine* s){
    if(!s || !frame_ready || stream_aborted || draining_parts)return 0;
    if(s->blend_mode>1){++unsupported;return 0;}
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
        stream_select(PVR_LIST_TR_POLY);stream_send(packet,kLinePacket);++fx_direct;return 1;
    }
    const unsigned required=kSpriteNode+kLinePacket,margin=8192;
    unsigned char* storage=frame_storage;unsigned* top=&deferred_top;
    if(required+margin>deferred_top || deferred_top-required-margin<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad)))){
        if(!deferred_spill){deferred_spill=static_cast<unsigned char*>(re4dc_model_deferred_storage(&deferred_spill_capacity));deferred_spill_top=deferred_spill_capacity;}
        if(!deferred_spill || required>deferred_spill_top){++fx_dropped;return 0;}
        storage=deferred_spill;top=&deferred_spill_top;
    }
    *top-=required;auto* node=new(storage+*top) DeferredPart{};node->lighting=kLineTag;
    std::memcpy(storage+*top+kSpriteNode,packet,kLinePacket);
    if(deferred_last)deferred_last->next=node;else deferred_first=node;
    deferred_last=node;++deferred_count;++fx_queued;
    frame_queue_peak=std::max(frame_queue_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
    return 1;
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
    if(source_draws_finished){stream_select(PVR_LIST_TR_POLY);stream_send(packet,bytes);return 1;}
    const unsigned required=kSubscreenQuadNode+bytes,margin=8192;
    unsigned char* storage=frame_storage;unsigned* top=&deferred_top;
    if(required+margin>deferred_top || deferred_top-required-margin<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad)))){
        if(!deferred_spill){deferred_spill=static_cast<unsigned char*>(re4dc_model_deferred_storage(&deferred_spill_capacity));deferred_spill_top=deferred_spill_capacity;}
        if(!deferred_spill || required>deferred_spill_top){++dropped;return 0;}
        storage=deferred_spill;top=&deferred_spill_top;
    }
    *top-=required;auto* node=new(storage+*top) DeferredPart{};
    node->lighting=kSubscreenQuadTag;node->changed[0]=bytes;
    std::memcpy(storage+*top+kSubscreenQuadNode,packet,bytes);
    if(deferred_last)deferred_last->next=node;else deferred_first=node;
    deferred_last=node;++deferred_count;
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
    if(source_draws_finished){stream_select(PVR_LIST_TR_POLY);stream_send(packet,bytes);return 1;}
    const unsigned required=kSubscreenQuadNode+bytes,margin=8192;
    unsigned char* storage=frame_storage;unsigned* top=&deferred_top;
    if(required+margin>deferred_top || deferred_top-required-margin<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad)))){
        if(!deferred_spill){deferred_spill=static_cast<unsigned char*>(re4dc_model_deferred_storage(&deferred_spill_capacity));deferred_spill_top=deferred_spill_capacity;}
        if(!deferred_spill || required>deferred_spill_top){++dropped;return 0;}
        storage=deferred_spill;top=&deferred_spill_top;
    }
    *top-=required;auto* node=new(storage+*top) DeferredPart{};
    node->lighting=kSubscreenQuadTag;node->changed[0]=bytes;
    std::memcpy(storage+*top+kSubscreenQuadNode,packet,bytes);
    if(deferred_last)deferred_last->next=node;else deferred_first=node;
    deferred_last=node;++deferred_count;
    frame_queue_peak=std::max(frame_queue_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
    return 1;
}
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
        v[k].flags=k==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;v[k].x=xs[k];v[k].y=ys[k];v[k].z=1.0f;
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
    if(!post_c && !post_h){++post_skipped;return;}
#if RE4DC_POST_F00_DIAG
    post_diag_frame();
#endif
    if(source_draws_finished){
        alignas(32) unsigned char packet[kPostBytes];post_packet(packet);
        stream_select(PVR_LIST_TR_POLY);post_send(packet,kPostBytes);++post_direct;return;
    }
    const unsigned required=kPostNode+kPostBytes,margin=8192;
    unsigned char* storage=frame_storage;unsigned* top=&deferred_top;
    if(required+margin>deferred_top || deferred_top-required-margin<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad)))){
        if(!deferred_spill){deferred_spill=static_cast<unsigned char*>(re4dc_model_deferred_storage(&deferred_spill_capacity));deferred_spill_top=deferred_spill_capacity;}
        if(!deferred_spill || required>deferred_spill_top){++post_dropped;return;}
        storage=deferred_spill;top=&deferred_spill_top;
    }
    *top-=required;
    auto* node=new(storage+*top) DeferredPart{};node->lighting=kPostTag;node->changed[0]=kPostBytes;
    post_packet(storage+*top+kPostNode);
    if(deferred_last)deferred_last->next=node;else deferred_first=node;
    deferred_last=node;++deferred_count;++post_queued;
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
    if(!out || pass>2 || !frame_ready || stream_aborted || direct_open ||
       !ensure_model_storage() || model_used+32>kModelPacketBytes/32)return 0;
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
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,list,re4dc::texture::pvr_format(t),t.width,t.height,handle->package.pvr_texture(0),PVR_FILTER_BILINEAR);
    c.gen.culling=PVR_CULLING_NONE; // authored cull already applied after clipping
    c.depth.comparison=PVR_DEPTHCMP_GEQUAL;
    c.depth.write=pass==2?PVR_DEPTHWRITE_DISABLE:PVR_DEPTHWRITE_ENABLE;
    c.blend.src=pass==2?PVR_BLEND_SRCALPHA:PVR_BLEND_ONE;
    c.blend.dst=pass==2?PVR_BLEND_INVSRCALPHA:PVR_BLEND_ZERO;
    c.txr.env=PVR_TXRENV_MODULATEALPHA;
    c.txr.alpha=pass?PVR_TXRALPHA_ENABLE:PVR_TXRALPHA_DISABLE;
    c.txr.uv_clamp=PVR_UVCLAMP_NONE;
#if RE4DC_NATIVE_FOG && RE4DC_PS2_WORLD_FOG_SOURCE
    c.gen.fog_type=re4dc_ps2_world_fog()?PVR_FOG_TABLE:PVR_FOG_DISABLE; // source GX fog at the scenery draw
#elif RE4DC_NATIVE_FOG
    c.gen.fog_type=PVR_FOG_TABLE;
#endif
    pvr_poly_hdr_t header;pvr_poly_compile(&header,&c);++model_header_builds;
    std::uint32_t count;re4dc::render::begin_pvr_packet(model_packets+model_used,count,header);
    model_pending=model_used+count;model_handle=handle;
    out->vertices=model_packets+model_pending;out->capacity=kModelPacketBytes/32-model_pending;
    out->u_scale=out->v_scale=1;
    return 1;
}
#if RE4DC_PS2_WORLD_KERNEL==4
extern "C" int re4dc_ps2_world_packet_cull(unsigned crc,unsigned fnv,unsigned width,unsigned height,unsigned pass,unsigned cull,Re4dcModelPacket* out){
    if(!out || pass>2 || !frame_ready || stream_aborted || direct_open ||
       !ensure_model_storage() || model_used+32>kModelPacketBytes/32)return 0;
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
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,list,re4dc::texture::pvr_format(t),t.width,t.height,handle->package.pvr_texture(0),PVR_FILTER_BILINEAR);
    // PS2_WORLD_KERNEL=4 strips: the authored cull (0 drops screen area >= 0, i.e. clockwise with y down).
    c.gen.culling=cull==0?PVR_CULLING_CW:cull==1?PVR_CULLING_CCW:PVR_CULLING_NONE;
    c.depth.comparison=PVR_DEPTHCMP_GEQUAL;
    c.depth.write=pass==2?PVR_DEPTHWRITE_DISABLE:PVR_DEPTHWRITE_ENABLE;
    c.blend.src=pass==2?PVR_BLEND_SRCALPHA:PVR_BLEND_ONE;
    c.blend.dst=pass==2?PVR_BLEND_INVSRCALPHA:PVR_BLEND_ZERO;
    c.txr.env=PVR_TXRENV_MODULATEALPHA;
    c.txr.alpha=pass?PVR_TXRALPHA_ENABLE:PVR_TXRALPHA_DISABLE;
    c.txr.uv_clamp=PVR_UVCLAMP_NONE;
#if RE4DC_NATIVE_FOG && RE4DC_PS2_WORLD_FOG_SOURCE
    c.gen.fog_type=re4dc_ps2_world_fog()?PVR_FOG_TABLE:PVR_FOG_DISABLE; // source GX fog at the scenery draw
#elif RE4DC_NATIVE_FOG
    c.gen.fog_type=PVR_FOG_TABLE;
#endif
    pvr_poly_hdr_t header;pvr_poly_compile(&header,&c);++model_header_builds;
    std::uint32_t count;re4dc::render::begin_pvr_packet(model_packets+model_used,count,header);
    model_pending=model_used+count;model_handle=handle;
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
// still holds that key and still has the same VRAM address: a closed (evicted, retired) and reloaded upload fails
// the address test and recompiles, so header words 0..3 are always the ones a compile would give now. Words 4..7:
// KOS pvr_poly_compile never writes them for a header without a modifier volume, so the uncached path sends whatever
// the stack held there (the PVR ignores them for these packed-colour, non-modifier headers); with this knob both
// paths send zeros. 32 sets of 4 slots; a miss refills the set's slots in turn.
namespace {
constexpr unsigned kPs2HdrSets=32,kPs2HdrWays=4;
struct Ps2HdrSlot { unsigned crc,fnv,size,mode; Entry* entry; pvr_ptr_t texture; std::uint32_t words[4]; };
static_assert(sizeof(pvr_poly_hdr_t)==32);
Ps2HdrSlot ps2_hdr[kPs2HdrSets][kPs2HdrWays];
unsigned char ps2_hdr_next[kPs2HdrSets];
unsigned ps2_hdr_hits,ps2_hdr_fills,ps2_hdr_log=~0U;
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
extern "C" int re4dc_ps2_world_direct_begin(const unsigned* k,Re4dcModelDirect* out){
#if RE4DC_TA_DIRECT
    if(direct_open){re4dc_missing("native direct part nested");return 0;}
    if(!k || !out || k[4]>2 || k[5]>2 || !frame_ready || stream_aborted ||
       !ensure_model_storage() || model_used+32>kModelPacketBytes/32)return 0;
    const Key key{k[0],k[1]};
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
            ps2_hdr_log=frame;
#if RE4DC_PS2_WORLD_HDR_CACHE==2
            re4dc_log("PS2HDR frame=%u hits=%u fills=%u checked=%u mismatched=%u\n",frame,ps2_hdr_hits,ps2_hdr_fills,ps2_hdr_checked,ps2_hdr_bad);
#else
            re4dc_log("PS2HDR frame=%u hits=%u fills=%u\n",frame,ps2_hdr_hits,ps2_hdr_fills);
#endif
        }
        for(auto& s:ps2_hdr[hdr_set])
            if(s.mode==hdr_mode && s.crc==k[0] && s.fnv==k[1] && s.size==hdr_size){hit=&s;break;}
    }
    if(hit && hit->entry->valid && hit->entry->key==key && hit->entry->package.pvr_texture(0)==hit->texture){
        const Ps2HdrSlot& slot=*hit;
        Entry* const handle=slot.entry;
        {constexpr bool pin=false;RE4DC_TOUCH(*handle);} // load()'s hit bookkeeping (pin=false)
        const unsigned pass=k[4];
        const pvr_list_t list=pass==0?PVR_LIST_OP_POLY:pass==1?PVR_LIST_PT_POLY:PVR_LIST_TR_POLY;
        stream_select(list);
#if RE4DC_WORLD_AUTOSORT
        world_sort_begin();
#endif
        if(stream_aborted)return 0;
        pvr_poly_hdr_t header;
        auto* hw=reinterpret_cast<std::uint32_t*>(&header);
        for(unsigned i=0;i<4;++i){hw[i]=slot.words[i];hw[4+i]=0;}
        ++model_header_hits;++ps2_hdr_hits;
#if RE4DC_PS2_WORLD_HDR_CACHE==2
        // =2 (diagnostic): the uncached lookup and compile beside every hit; a different Entry or word is counted.
        {
            const Re4dcUiImage image{&key,nullptr,k[2],k[3],5,0,0};
            Entry* const ref_handle=load(image,false,&key);
            bool bad=ref_handle!=handle;
            if(!bad){
                const auto& t=ref_handle->package.textures()[0];
                pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,list,re4dc::texture::pvr_format(t),t.width,t.height,ref_handle->package.pvr_texture(0),PVR_FILTER_BILINEAR);
                const pvr_cull_mode_t cull[]={PVR_CULLING_NONE,PVR_CULLING_CCW,PVR_CULLING_CW};
                c.gen.culling=cull[k[5]];
                c.depth.comparison=PVR_DEPTHCMP_GEQUAL;
                c.depth.write=pass==2?PVR_DEPTHWRITE_DISABLE:PVR_DEPTHWRITE_ENABLE;
                c.blend.src=pass==2?PVR_BLEND_SRCALPHA:PVR_BLEND_ONE;
                c.blend.dst=pass==2?PVR_BLEND_INVSRCALPHA:PVR_BLEND_ZERO;
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
        std::uint32_t count;re4dc::render::begin_pvr_packet(model_packets+model_used,count,header);
        model_pending=model_used+count;model_handle=handle;
        if(!stream_scene)stream_open();
        auto* sq=static_cast<std::uint32_t*>(static_cast<void*>(sq_lock((void*)PVR_TA_INPUT)));
        const auto* words=reinterpret_cast<const std::uint32_t*>(model_packets+model_used);
        for(unsigned i=0;i<8;++i)sq[i]=words[i];
#if RE4DC_TA_HASH
        re4dc_ta_hash(words,32);
#endif
        sq_flush(sq);
        direct_open=true;
        model_handle->frame=frame; // the header is in the TA: pinned for this scene
        ++frame_pvr_calls;frame_pvr_bytes+=32;stream_model_bytes+=32;
        out->sq=sq+8;out->scratch=model_packets+model_pending;out->scratch_capacity=kModelPacketBytes/32-model_pending;
        out->u_scale=out->v_scale=1;
        return 1;
    }
#endif
    const Re4dcUiImage image{&key,nullptr,k[2],k[3],5,0,0};
    Entry* handle=load(image,false,&key);
    if(!handle || !frame_ready || stream_aborted || direct_open){++model_texture_rejects;return 0;}
    const auto& t=handle->package.textures()[0];
    if(t.width!=k[2] || t.height!=k[3])return 0; // repeated UVs cannot use padding
    const unsigned pass=k[4];
    const pvr_list_t list=pass==0?PVR_LIST_OP_POLY:pass==1?PVR_LIST_PT_POLY:PVR_LIST_TR_POLY;
    stream_select(list);
#if RE4DC_WORLD_AUTOSORT
    world_sort_begin();
#endif
    if(stream_aborted)return 0;
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,list,re4dc::texture::pvr_format(t),t.width,t.height,handle->package.pvr_texture(0),PVR_FILTER_BILINEAR);
    const pvr_cull_mode_t cull[]={PVR_CULLING_NONE,PVR_CULLING_CCW,PVR_CULLING_CW};
    c.gen.culling=cull[k[5]];
    c.depth.comparison=PVR_DEPTHCMP_GEQUAL;
    c.depth.write=pass==2?PVR_DEPTHWRITE_DISABLE:PVR_DEPTHWRITE_ENABLE;
    c.blend.src=pass==2?PVR_BLEND_SRCALPHA:PVR_BLEND_ONE;
    c.blend.dst=pass==2?PVR_BLEND_INVSRCALPHA:PVR_BLEND_ZERO;
    c.txr.env=PVR_TXRENV_MODULATEALPHA;
    c.txr.alpha=pass?PVR_TXRALPHA_ENABLE:PVR_TXRALPHA_DISABLE;
    c.txr.uv_clamp=PVR_UVCLAMP_NONE;
#if RE4DC_NATIVE_FOG && RE4DC_PS2_WORLD_FOG_SOURCE
    c.gen.fog_type=re4dc_ps2_world_fog()?PVR_FOG_TABLE:PVR_FOG_DISABLE; // source GX fog at the scenery draw
#elif RE4DC_NATIVE_FOG
    c.gen.fog_type=PVR_FOG_TABLE;
#endif
    pvr_poly_hdr_t header;pvr_poly_compile(&header,&c);++model_header_builds;
#if RE4DC_PS2_WORLD_HDR_CACHE
    if(hdr_on){
        auto* hw=reinterpret_cast<std::uint32_t*>(&header);
        hw[4]=hw[5]=hw[6]=hw[7]=0; // never written by pvr_poly_compile here (stack contents before; unused by the PVR)
        // The key's stale slot if it has one, else the set's next slot in turn.
        Ps2HdrSlot& slot=hit?*hit:ps2_hdr[hdr_set][ps2_hdr_next[hdr_set]++%kPs2HdrWays];
        slot.crc=k[0];slot.fnv=k[1];slot.size=hdr_size;slot.mode=hdr_mode;slot.entry=handle;
        slot.texture=handle->package.pvr_texture(0);
        for(unsigned i=0;i<4;++i)slot.words[i]=hw[i];
        ++ps2_hdr_fills;
    }
#endif
#if RE4DC_PS2_INTERIOR_CULL==2
    if(re4dc_ps2_check_header)ps2_check_header(header);
#endif
    std::uint32_t count;re4dc::render::begin_pvr_packet(model_packets+model_used,count,header);
    model_pending=model_used+count;model_handle=handle;
    if(!stream_scene)stream_open();
    auto* sq=static_cast<std::uint32_t*>(static_cast<void*>(sq_lock((void*)PVR_TA_INPUT)));
    const auto* words=reinterpret_cast<const std::uint32_t*>(model_packets+model_used);
    for(unsigned i=0;i<8;++i)sq[i]=words[i];
#if RE4DC_TA_HASH
    re4dc_ta_hash(words,32);
#endif
    sq_flush(sq);
    direct_open=true;
    model_handle->frame=frame; // the header is in the TA: pinned for this scene
    ++frame_pvr_calls;frame_pvr_bytes+=32;stream_model_bytes+=32;
    out->sq=sq+8;out->scratch=model_packets+model_pending;out->scratch_capacity=kModelPacketBytes/32-model_pending;
    out->u_scale=out->v_scale=1;
    return 1;
#else
    (void)k;(void)out;return 0;
#endif
}
#endif
extern "C" void re4dc_model_finish_source_draws(){
    RE4DC_PROFILE_SCOPE(TranslucentDrain);
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
    if(!deferred_first){source_draws_finished=true;return;}
    draining_parts=true;
    // Current PVR setup enables OP/TR only. Do not submit a dummy PT list:
    // pinned KOS compares completed-list bits to exactly the enabled-list mask.
    // A future qualified PT material must also budget/enable that list.
    stream_select(PVR_LIST_TR_POLY);draining_list=PVR_LIST_TR_POLY;
    while(deferred_first && !stream_aborted){
#if RE4DC_SUBSCREEN && RE4DC_PVR_STREAM
        if(deferred_first->lighting==kSubscreenQuadTag){
            const auto* packet=reinterpret_cast<const unsigned char*>(deferred_first)+kSubscreenQuadNode;
            const unsigned bytes=deferred_first->changed[0];
            deferred_first=deferred_first->next;stream_send(packet,bytes);continue;
        }
#endif
#if RE4DC_EFFECT_SPRITES
        if(deferred_first->lighting==kSpriteTag){
            auto* packet=reinterpret_cast<unsigned char*>(deferred_first)+kSpriteNode;
            const bool screen=deferred_first->changed[0]!=0;
            deferred_first=deferred_first->next;fx_send(packet,screen);continue;
        }
#if defined(RE4DC_NATIVE_LASER) && RE4DC_NATIVE_LASER
        if(deferred_first->lighting==kLineTag){
            const auto* packet=reinterpret_cast<const unsigned char*>(deferred_first)+kSpriteNode;
            deferred_first=deferred_first->next;stream_send(packet,kLinePacket);continue;
        }
#endif
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
        Re4dcModelPart view=restore_view(deferred_first);
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
    draining_parts=false;source_draws_finished=true;reset_deferred();
#endif
}

extern "C" void re4dc_model_invalidate_pending(){
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

extern "C" void* re4dc_model_deferred_storage(unsigned* bytes){
    *bytes=model_packets?kModelDeferredSpillBytes:0;
    return *bytes?reinterpret_cast<unsigned char*>(model_packets)+kModelPacketBytes+kModelPreparationBytes+kModelStaticLightBytes:nullptr;
}

#if RE4DC_ROUTE_MOVIES
extern "C" int re4dc_ui_movie_open(unsigned width,unsigned height){
    // Macroblock sizes inside the 512x256 texture; rows load as 32-byte blocks.
    if(movie_texture || !ready || !width || !height || width>512 || height>256 || (width&15))return 0;
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
    if(!movie_texture)return 0;
#if RE4DC_PVR_STREAM
    // A movie-owned presentation interrupts a source frame: its open (hidden
    // world) scene is discarded first, or the render fence below never completes.
    if(stream_scene)stream_close(false);
#endif
#if RE4DC_PVR_PIPELINE
    present_fence();
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
    if(re4dc::gpu::quiesce()!=re4dc::gpu::FenceResult::ready){re4dc_log("route movie texture retirement fence pending\n");return 0;}
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
#if RE4DC_PVR_STREAM
    stream_send(packet,sizeof(packet));
#else
    re4dc::render::submit_pvr(packet,sizeof(packet));
#endif
}
}
#endif // RE4DC_ROUTE_MOVIES
