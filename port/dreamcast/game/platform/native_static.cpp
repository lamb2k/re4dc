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
#include <kos.h>
#include <fcntl.h>
#include <malloc.h>
#include <unistd.h>
#include <cmath>
#include <stdio.h>
#include <cstring>
#include <cstdlib>
#include "native_static.h"
#if RE4DC_QUALITY
#include "quality.h"
#endif
#include "native_model.h"
#include "re4dc_platform.h"
#include "../../room/room_package.hpp"
#include "../../room/static_room_prepare.hpp"
#include "../../room/pvr_geometry.hpp"

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
#if RE4DC_MESH_VP_SCHED
#include "../../room/mesh_fastpath_sched.hpp"
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
// filter: 0 as KOS set it at boot, 1 forced on = VSCALE 1025, 2 forced off = 1024), VMU label.
// Disc 2 order (look study 2026-10-10): GD first (the new base), then its variants, DC last for reference.
struct Re4dcLook { unsigned char curve,cap,rgb,sky,fx,grade,soft; char label[3]; const char* text; };
static const Re4dcLook re4dc_looks[]={
    {1,100, 70,1,7,0,0,"GD","GD: GC fog, fog colour 70%"},   // GameCube fog curve + sky / treeline, fog colour 70 %
    {1,100, 70,1,7,1,0,"GM","GM: GD + r100 colour match"},   // GD + the r100 outdoor brightness / colour match
    {1,100, 70,1,7,0,1,"GS","GS: GD + flicker filter on"},   // GD + the PVR vertical flicker filter forced on
    {1,100, 70,1,7,1,1,"GA","GA: GC fog + r100 colour + filter"},   // GD + match + filter
    {0,100,100,0,7,0,0,"DC","DC: current look"},             // the play build's look (as the knobs-off image)
    {1,100, 70,1,7,0,2,"GX","GX: GD, flicker filter off"},   // GD with the vertical filter forced OFF
};
constexpr unsigned kLooks=sizeof(re4dc_looks)/sizeof(re4dc_looks[0]);
extern "C" { unsigned re4dc_look_mode; }
#if defined(RE4DC_EFFECT_PS2_TOGGLE) && RE4DC_EFFECT_PS2_TOGGLE
extern "C" void re4dc_ps2fx_set(unsigned flags);
#endif
static unsigned re4dc_look_scaler_boot=~0U; // PVR_SCALER_CFG as KOS left it (vertical filter on for 480i TV)
static bool re4dc_look_applied;
// On-screen label (native_ui.cpp re4dc_look_grade_post draws it in the top letterbox): 3 s after each preset change,
// or always while "always show" is on (hold X + Y, press START).
extern "C" unsigned re4dc_vi_retrace_count(void);
static unsigned re4dc_look_osd_until;static bool re4dc_look_osd_always;
extern "C" void re4dc_look_osd_toggle(void){
    re4dc_look_osd_always=!re4dc_look_osd_always;re4dc_look_osd_until=re4dc_vi_retrace_count()+180U;
    re4dc_log("look: label always %s\n",re4dc_look_osd_always?"on":"off");
}
extern "C" const char* re4dc_look_osd_text(void){
    if(!re4dc_look_osd_always && int(re4dc_look_osd_until-re4dc_vi_retrace_count())<=0)return nullptr;
    return re4dc_looks[re4dc_look_mode%kLooks].text;
}
extern "C" void re4dc_look_set(unsigned mode){
    re4dc_look_mode=mode%kLooks;re4dc_look_applied=true;re4dc_look_osd_until=re4dc_vi_retrace_count()+180U;
    const Re4dcLook& lk=re4dc_looks[re4dc_look_mode];
#if defined(RE4DC_EFFECT_PS2_TOGGLE) && RE4DC_EFFECT_PS2_TOGGLE
    re4dc_ps2fx_set(lk.fx); // masked to the built features
#endif
    if(re4dc_look_scaler_boot==~0U)re4dc_look_scaler_boot=PVR_GET(PVR_SCALER_CFG);
    const unsigned vs=lk.soft==1?1025U:lk.soft==2?1024U:(re4dc_look_scaler_boot&0xffffU);
    PVR_SET(PVR_SCALER_CFG,(re4dc_look_scaler_boot&~0xffffU)|vs);
    re4dc_log("look: preset %u %s (curve %u cap %u fog colour %u%% sky %u fx %u grade %u vscale %u scaler %08x)\n",re4dc_look_mode,lk.label,
        lk.curve,lk.cap,lk.rgb,lk.sky,lk.fx,lk.grade,vs,unsigned(PVR_GET(PVR_SCALER_CFG)));
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

namespace {
using re4dc::room::Package;
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
};
View views[kViews];
Re4dcStaticStats stats{};
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
    v.storage=storage;
    if(!v.package.adopt(storage,size) || !v.package.material_keys() ||
       v.package.header().material_count>kMaxMaterials){
        re4dc_log("native static: %s rejected: %s keyed=%d materials=%u\n",path,
            v.package.error()?v.package.error():"layout",v.package.material_keys(),v.package.header().material_count);
        re4dc_static_free(storage);v.storage=nullptr;v.bytes=0;v.package.close();++stats.open_failures;return false;
    }
    const auto& b=v.package.header();
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
    const float sx=RE4DC_SCREEN_WF/v[2],sy=RE4DC_SCREEN_HF/v[3];
    const float row0[4]={RE4DC_SCREEN_HALF_WF*p[1],0,RE4DC_SCREEN_HALF_WF*p[2]-sx*(v[0]+v[2]*.5f),0};
    const float row1[4]={0,-RE4DC_SCREEN_HALF_HF*p[3],-RE4DC_SCREEN_HALF_HF*p[4]-sy*(v[1]+v[3]*.5f),0};
    const float row2[4]={0,0,1,0},row3[4]={0,0,-1,0};
    const float* rows[4]={row0,row1,row2,row3};
    alignas(32) static matrix_t screen;
    for(unsigned r=0;r<4;++r)for(unsigned c=0;c<4;++c){
        float value=c==3?rows[r][3]:0.0f;
        for(unsigned k=0;k<3;++k)value+=rows[r][k]*mv[4*k+c];
        screen[c][r]=value; // KOS matrix_t is column-major for ftrv
    }
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
    re4dc::render::ClipParameters clip{};
#if RE4DC_PS2_WORLD_MESH
    const unsigned* ps2=nullptr; // PS2_WORLD_MESH part: {crc, fnv, width, height, pass, cull}; binds by key, not by p
#endif
#if RE4DC_HW_LEAN
    float proj_bx=0,proj_by=0; // project()'s viewport offsets in 640x480 pixels
    void set_clip(){
        const float* v=p.viewport;
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
        // The viewport terms are per part (proj_setup): v[2]*.5*640/v[2] = 320, v[3]*.5*480/v[3] = 240.
        float inv=z*z;
        __asm__("fsrra %0" : "+f"(inv));
        (void)v;
        x=320.f*(p[1]*x+p[2]*z)*inv+d.proj_bx;
        y=-240.f*(p[3]*y+p[4]*z)*inv+d.proj_by;
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
    void end_direct(){if(sq){re4dc_model_direct_end(slots);sq=nullptr;}}
    void put(unsigned n){sq=re4dc_ta_put(sq,dst+used,n);slots+=n;}
#endif
    bool bind(){
        if(bound)return true;
#if RE4DC_MESH_DIRECT
        if(direct){
            Re4dcModelDirect out{};
#if RE4DC_PS2_WORLD_MESH
            if(!(ps2?re4dc_ps2_world_direct_begin(ps2,&out):re4dc_model_direct_begin(&p,&out)))return false;
#else
            if(!re4dc_model_direct_begin(&p,&out))return false;
#endif
            sq=out.sq;submitted=true;
            packet.vertices=out.scratch;packet.capacity=out.scratch_capacity;
            packet.u_scale=out.u_scale;packet.v_scale=out.v_scale;
            dst=static_cast<pvr_vertex_t*>(out.scratch);bound=true;limit=out.scratch_capacity;
            load_screen(mvq,p.projection,p.viewport); // binding may yield
            return true;
        }
#endif
        if(!re4dc_model_packet_begin(&p,&packet))return false;
        dst=static_cast<pvr_vertex_t*>(packet.vertices);bound=true;limit=packet.capacity;
        load_screen(mvq,p.projection,p.viewport); // binding may yield
        return true;
    }
    bool flush(){
        if(!streaming || !used)return false;
        re4dc_model_packet_commit(used);submitted=true;used=0;
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
    [[gnu::always_inline]] re4dc::render::StaticCorner corner(const re4dc::room::CompactVertex12& in)const{
        return {float(in.x),float(in.y),float(in.z),in.u,in.v,palette?palette[in.color]:argb1555(in.color)};
    }
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
        input+=count-2;
        if(count<=limit){
            if(count>limit-used && !flush())return submitted?-1:0;
            unsigned outside=15;
            const bool ready=re4dc::render::prepare_direct_strip(dst+used,count,near,far,
                [&](std::uint32_t local,re4dc::render::DirectStripVertex& out){
                    out=re4dc::render::prepare_static_vertex(corner(base[index[local]]),batch,0.0f);
                    out.u=u(out.u);out.v=v(out.v);
                    if(!vertex_alpha)out.argb=(out.argb&0xffffffU)|alpha;
                    outside&=(out.x<0?1U:0U)|(out.x>RE4DC_SCREEN_WF?2U:0U)|(out.y<0?4U:0U)|(out.y>RE4DC_SCREEN_HF?8U:0U);
                    return true;
                });
            stats.vertices+=count;
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
            unsigned all=0x3fU;
            for(unsigned i=0;i<count && all;++i){
                const auto c=corner(base[index[i]]);
                const float x=mvq[0]*c.x+mvq[1]*c.y+mvq[2]*c.z+mvq[3];
                const float y=mvq[4]*c.x+mvq[5]*c.y+mvq[6]*c.z+mvq[7];
                const float z=mvq[8]*c.x+mvq[9]*c.y+mvq[10]*c.z+mvq[11];
                const float W=-z;
                const float X=320.f*(pp[1]*x+pp[2]*z)+proj_bx*W, Y=-240.f*(pp[3]*y+pp[4]*z)+proj_by*W;
                all&=(X<0.0f?1U:0U)|(X>RE4DC_SCREEN_WF*W?2U:0U)|(Y<0.0f?4U:0U)|(Y>RE4DC_SCREEN_HF*W?8U:0U)|
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
#if RE4DC_SCENERY_ENCODING
    const std::uint32_t* vertex_colors=nullptr; // kColorOctVertex: each vertex's CLR0 (ARGB8888), read in place of the palette
#endif
};
MeshView mesh_views[kMeshViews];
#if RE4DC_TREE_IMPOSTOR
// This frame's impostor quads (screen x, y, 1/w per corner: TL, TR, BL, BR),
// sent per atlas by re4dc_static_flush_impostors(). A retired view clears it.
struct ImpostorQuad { const re4dc::room::MeshImpostor* record; std::uint32_t argb; std::uint16_t cell; std::uint8_t fog,pad; float s[4][3]; };
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
#if RE4DC_SCENERY_ENCODING
    if(!re4dc::room::adopt_by_encoding(v.package,storage,size,RE4DC_MESH_LOD!=0,&v.vertex_colors)){
#else
    if(!v.package.adopt(storage,size,RE4DC_MESH_LOD!=0)){
#endif
        re4dc_log("native mesh: %s rejected: %s\n",path,v.package.error());
        re4dc_static_free(storage);++stats.open_failures;
#if RE4DC_QUALITY_ASSETS
        // A rejected Standard package: this owner opens its Original package instead.
        if(low){std_room.mesh_views&=~(1U<<view);v.attempted=false;re4dc_log("quality assets: Original package for this owner\n");return open(v,index,room);}
#endif
        return false;
    }
    v.storage=storage;v.bytes=package_bytes+table+kLutBytes+gather;
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
            if(low){std_room.ncull=std_room.nimp=std_room.nptex=std_room.nimpt=0;}
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
    unsigned placements=0,clusters=0,meshlets=0,tests=0,active_frames=0,frames=0; // culled (=1/=3) or checked (=2)
} st;
// The disc cell (r100 only): one heap-4 block = file (header, cells, portals) + both states' frustum arrays.
struct Data {
    void* block=nullptr;const Cell* cells=nullptr;const Portal* portals=nullptr;
    bool lent=false; unsigned loads=0,fails=0,lends=0;
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
    if(st.cell<0)return;
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
    ++st.tests;
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
    if(!data.block)return 0;
    re4dc_static_free(data.block);
    data.block=nullptr;data.cells=nullptr;data.portals=nullptr;
    st.fr=nullptr;st.active=false;st.nfr=0;
    State& t=trans_state();t.fr=nullptr;t.active=false;t.nfr=0;
    return kPcFileBytes+2U*kFrBytes;
}
// Reads /cd/dc/native/r100/interior.cell into a heap-4 block (the r100 package open, and after a route movie).
inline bool load(){
    if(data.block)return true;
    if(!st.ok)return false;
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
        if(std::memcmp(b,"PCL1",4) || w[1]!=kPcRoom || w[2]!=kPcMeshCrc || w[3]!=kPcSidecarCrc || w[4]!=kPcMeshBytes ||
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
struct MeshDraw : Emitter {
    const re4dc::room::MeshPackage& package; const re4dc::room::MeshPart& part;
    const std::uint32_t* lut; // mesh view's colour LUT (nullptr: per-corner path)
    re4dc::room::CompactVertex12* gather_pool; // mesh view's v3 gather buffer (nullptr: v1/v2)
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
    const re4dc::room::CompactVertex12* corners(const re4dc::room::Meshlet& l){
        const auto* base=package.vertices()+l.first_vertex;
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
#if RE4DC_MESH_FASTPATH
    // Transform-once state: the cache borrows the last kCacheSlots slots of
    // the bound packet range (never sent: strips stop at 'limit').
    pvr_vertex_t* cache=nullptr; std::uint8_t* outcodes=nullptr;
    re4dc::vp::Constants k{};
#if RE4DC_MESH_PRIME_LAZY
    // MESH_PRIME_LAZY (exact): the cache's constant words are written for the entries a meshlet
    // uses, the first time they are needed, instead of all kCacheEntries at every borrow (one
    // borrow per part per placement: ~30k entries a frame for ~24k transformed PS2 world vertices).
    unsigned primed=0;
#endif
    bool borrow(){
        if(cache)return true;
        if(!lut || limit<re4dc::vp::kCacheSlots+64U)return false; // small slab: per-corner path
        limit-=re4dc::vp::kCacheSlots;
        cache=dst+limit;outcodes=reinterpret_cast<std::uint8_t*>(cache+re4dc::vp::kCacheEntries);
#if !RE4DC_MESH_PRIME_LAZY
        re4dc::vp::prime(cache,re4dc::vp::kCacheEntries);
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
    // One visible meshlet: every vertex once through XMTRX, then each strip is
    // accepted (copied from the cache), culled (all corners outside one screen
    // edge) or handed to the unchanged clipper (a corner outside near/far),
    // the same three outcomes, in the same order, as Emitter::strip().
    int meshlet(const re4dc::room::Meshlet& l,const re4dc::room::CompactBatch& batch){
        namespace vp=re4dc::vp;
        const float bmin[3]={float(l.bounds_min[0]),float(l.bounds_min[1]),float(l.bounds_min[2])};
        const float bmax[3]={float(l.bounds_max[0]),float(l.bounds_max[1]),float(l.bounds_max[2])};
        // RE4DC_MESH_CLASSIFY=0 (default) saves ~1.5 KiB of image, i.e. KOS heap,
        // at ~8 cycles per vertex for outcodes in every meshlet.
        const unsigned checks=RE4DC_MESH_CLASSIFY?vp::classify(bmin,bmax,mvq,p.projection,p.viewport,near,far):vp::kChecksAll;
        const auto* base=corners(l);
        const auto* in=reinterpret_cast<const vp::Vertex12*>(base);
#if RE4DC_MESH_PRIME_LAZY
        if(l.vertex_count>primed){vp::prime(cache+primed,l.vertex_count-primed);primed=l.vertex_count;}
#endif
        if(checks==vp::kChecksNone)vp::transform<vp::kChecksNone>(in,l.vertex_count,cache,outcodes,k);
        else if(checks==vp::kChecksScreen)vp::transform<vp::kChecksScreen>(in,l.vertex_count,cache,outcodes,k);
#if RE4DC_MESH_VP_SCHED==1
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
          ){int result=1;s=strips_lean(s,end,base,batch,result);if(!s)return result;}
#endif
        while(s<end){
            const unsigned n=*s++;
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
        return 1;
    }
#if RE4DC_MESH_STRIP_LEAN==1 || RE4DC_MESH_STRIP_LEAN==3
    // MESH_STRIP_LEAN: meshlet()'s strip walk for kChecksAll meshlets on the store-queue sink. walk_lean()
    // (room/mesh_strip_lean.hpp) takes the strips up to the next one that needs the clipper with the same
    // StripCodes words, decisions, order and TA bursts as the original loop, keeping the per-strip counter
    // updates in registers. Between clip strips every strip is culled or emitted, so for the strips in
    // [mark, s):  sum n = (s - mark) - strips,  slots = (q - qmark) / 32 B,  output = slots - 2 * emitted,
    // input = sum n - 2 * strips, stats.vertices = sum n. lean_flush() writes these back before the
    // clipper (which reads and updates the members) and at the end; the clip strip itself runs the
    // original code. Returns nullptr when the meshlet is done (result: meshlet()'s value).
    void lean_flush(const std::uint8_t* s,const std::uint8_t* mark,std::uint32_t* q,const std::uint32_t* qmark,
                    unsigned culled,unsigned emitted){
        const unsigned strips=culled+emitted,sum=unsigned(s-mark)-strips,v=unsigned(q-qmark)/8U;
        input+=sum-2U*strips;stats.vertices+=sum;stats.strips_culled+=culled;stats.strips+=emitted;
        slots+=v;output+=v-2U*emitted;sq=q;
    }
    const std::uint8_t* strips_lean(const std::uint8_t* s,const std::uint8_t* end,const re4dc::room::CompactVertex12* base,
                                    const re4dc::room::CompactBatch& batch,int& result){
        for(;;){
            const std::uint8_t* const mark=s;std::uint32_t* q=sq;const std::uint32_t* const qmark=q;
            unsigned culled=0,emitted=0;
            s=re4dc::vp::walk_lean(s,end,outcodes,cache,limit,q,culled,emitted);
#if defined(RE4DC_TA_HASH) && RE4DC_TA_HASH
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
            input+=n-2;
            if(n<=limit)stats.vertices+=n;
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
    void strip_lean_compare(const re4dc::room::Meshlet& l){
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
    int draw(const re4dc::room::Meshlet& l){
        const re4dc::render::DrawBounds bounds{
            {float(l.bounds_min[0]),float(l.bounds_min[1]),float(l.bounds_min[2])},
            {float(l.bounds_max[0]),float(l.bounds_max[1]),float(l.bounds_max[2])}};
        if(!re4dc::render::group_visible(bounds,mvq,p.projection,p.viewport,near,cull_far,0)){++stats.groups_culled;return 1;}
        ++stats.groups_visible;
        if(!bind()){++stats.bind_rejects;return submitted?-1:0;}
        ++stats.batches;
        if(!borrow_gather()){++stats.reserve_rejects;return submitted?-1:0;}
#if RE4DC_MESH_FASTPATH
        // A slab too small to lend the cache behaves like any other
        // capacity failure: generic fallback, or abort once published.
        if(!borrow()){++stats.reserve_rejects;return submitted?-1:0;}
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
        const auto& lod=package.part_lods()[part_index];
        const auto* clusters=package.clusters();const auto* levels=package.levels();
        for(unsigned c=lod.first_cluster;c<lod.first_cluster+lod.cluster_count;++c){
#if RE4DC_QUALITY_ASSETS
            if(skip_clusters && c-lod.first_cluster<64U && ((skip_clusters>>(c-lod.first_cluster))&1U))continue;
#endif
            const auto& cl=clusters[c];
            float lo[3],hi[3];
            for(unsigned a=0;a<3;++a){lo[a]=float(cl.bounds_min[a]);hi[a]=float(cl.bounds_max[a]);}
            const re4dc::render::DrawBounds bounds{{lo[0],lo[1],lo[2]},{hi[0],hi[1],hi[2]}};
            if(!re4dc::render::group_visible(bounds,mvq,p.projection,p.viewport,near,cull_far,0)){++stats.clusters_culled;continue;}
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
            ++stats.lod_draws[level<3?level:3];
            const auto& lv=levels[cl.first_level+level];
            const auto* lets=package.meshlets()+lv.first_meshlet;
            for(unsigned i=0;i<lv.meshlet_count;++i){
#if RE4DC_PS2_INTERIOR_CULL
                if(pc_state<0){
                    const bool hid=pc::grid_hidden(pc_wq,lets[i].bounds_min,lets[i].bounds_max)>0;
                    if(hid==(pc_mode==1)){if(hid)++pc::st.meshlets;continue;} // =1: skip hidden; check run: skip seen
                }
#endif
                const int result=draw(lets[i]);
                if(result<=0)return result;
            }
        }
        return 1;
    }
#endif
    int run(){
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
            const auto* lets=package.meshlets()+part.first_meshlet;
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
    r.room=room;r.active=false;r.mesh_views=0;r.checked=0;r.ntex=r.ndrop=r.ncull=r.nimp=r.nptex=r.nimpt=0;
    if(!re4dc_quality_std_assets())return;
    char path[64];snprintf(path,sizeof(path),"/cd/dc/native/r%x%02x/low/index.txt",room>>8,room&255U);
    char* text=static_cast<char*>(std::malloc(kStdText));
    const int n=text?re4dc_fixture_read(path,text,kStdText):-1;
    if(n<=0){re4dc_log("quality assets: %s missing: Original packages\n",path);std::free(text);return;}
    if(n>=int(kStdText)){re4dc_log("quality assets: %s larger than %u B: Original packages\n",path,kStdText);std::free(text);return;}
    text[n]=0;
    r.active=std_parse(text,room);
    std::free(text);
    if(!r.active){r.mesh_views=0;r.ntex=r.ndrop=r.ncull=r.nimp=r.nptex=r.nimpt=0;re4dc_log("quality assets: %s rejected: Original packages\n",path);return;}
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
            used+=4;
        }
        if(bound){re4dc_model_packet_commit(used);++impostor_stats[3];}
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
namespace {
// Last GXSetFog state (gx_stub.cpp) and the source View far plane seen by the
// model bridge. Temporary type-0 calls (effects, filters, thermal/black) reach
// parts as fog off through Re4dcModelPart::source_key[2]; the table keeps the last
// fogged state and is rewritten only when that state changes.
struct FogState { int type; float start,end,far; unsigned rgba; };
FogState fog_now{0,0,0,0,0},fog_loaded{-1,0,0,0,0};
constexpr float kFogRamp=0.8f; // ramp to 100% over the last 20% before the far plane
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
    const float ramp=(z-kFogRamp*far)/((1.0f-kFogRamp)*far);
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
    if(!(far<=float(RE4DC_FOG_FAR)))far=float(RE4DC_FOG_FAR);
#endif
    return far;
}
#endif
extern "C" void re4dc_fog_note_far(float far){
#if RE4DC_FOG_FAR > 0
    if(!(far<=float(RE4DC_FOG_FAR)))far=float(RE4DC_FOG_FAR);
#endif
    fog_now.far=far;
}
#if RE4DC_FOG_TA_DOUBLEBUF
// With a double-buffered TA the previous scene may still render at frame start and reads the fog
// registers: native_ui fences only when this frame changes them.
extern "C" int re4dc_fog_frame_pending(){
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
#if RE4DC_LOOK_ANY
#if defined(RE4DC_LOOK_TOGGLE)
    re4dc_look_grade_rgb_now=(fog_now.type && (fog_now.rgba>>8)==0x8d8775U && fog_now.start<1000.0f)?0xffdee3d7U:0U;
#endif
    if(!fog_now.type)return;
    // Look knobs (post30.mk, look study 2026-10-10): FOG_CURVE / FOG_CAP / FOG_RGB_PCT, or LOOK_TOGGLE's preset.
    const unsigned curve=re4dc_look_curve(),rgb_pct=re4dc_look_rgb_pct();const float cap=float(re4dc_look_cap())/100.0f;
    static unsigned look_loaded=~0U;
    const unsigned look_key=curve|rgb_pct<<4|unsigned(re4dc_look_cap())<<12;
    if(look_key==look_loaded && fog_now.type==fog_loaded.type && fog_now.start==fog_loaded.start &&
       fog_now.end==fog_loaded.end && fog_now.far==fog_loaded.far && fog_now.rgba==fog_loaded.rgba)return;
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
        const float ramp=(z-kFogRamp*far)/((1.0f-kFogRamp)*far);
        if(ramp>0){
            const float s=ramp>=1?1.0f:ramp*ramp*(3.0f-2.0f*ramp);
            if(!curve)f+=(1.0f-f)*s;
            else if(curve==2 && f<cap*s)f=cap*s;
        }
        table[j]=f;
    }
    pvr_fog_table_color(1.0f,r,g,b);
    pvr_fog_far_depth(tfar);
    pvr_fog_table_custom(table);
#else
    if(!fog_now.type)return;
    if(fog_now.type==fog_loaded.type && fog_now.start==fog_loaded.start && fog_now.end==fog_loaded.end &&
       fog_now.far==fog_loaded.far && fog_now.rgba==fog_loaded.rgba)return;
    fog_loaded=fog_now;
    const float far=fog_now.far>1.0f?fog_now.far:(fog_now.end>1.0f?fog_now.end:1.0f);
    const float r=float((fog_now.rgba>>24)&255U)/255.0f,g=float((fog_now.rgba>>16)&255U)/255.0f,
                b=float((fog_now.rgba>>8)&255U)/255.0f;
    float table[129];
    for(unsigned j=0;j<129;++j){
        const float v=j<128?float((j&15U)+16U)/16.0f*float(1U<<(j>>4)):256.0f;
        const float z=far/v;
        float f=gx_fog(fog_now.type,fog_now.start,fog_now.end,z);
        const float ramp=(z-kFogRamp*far)/((1.0f-kFogRamp)*far);
        if(ramp>0){const float s=ramp>=1?1.0f:ramp*ramp*(3.0f-2.0f*ramp);f+=(1.0f-f)*s;}
        table[j]=f;
    }
    pvr_fog_table_color(1.0f,r,g,b);
    pvr_fog_far_depth(far);
    pvr_fog_table_custom(table);
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
    re4dc::room::MeshPackage package;
    unsigned char* storage=nullptr; unsigned bytes=0;
    const Ps2Part* parts=nullptr; const Ps2Placement* placements=nullptr; unsigned nplacements=0;
    const std::uint32_t* lut=nullptr; re4dc::room::CompactVertex12* gather=nullptr;
    float view[12]{},projection[7]{},viewport[6]{}; bool camera=false,attempted=false;
    Ps2Counts count[3]{};
#if RE4DC_PS2_WORLD_ROOMS
    unsigned room=0,want=0x101; // package loaded / attempted for; the room re4dc_ps2_mesh_select asks for
#endif
#if RE4DC_PS2_PASS_MASK
    // PS2_PASS_MASK (game30.mk; exact): bit p = the placement's mesh has a part in pass p, built at open.
    static constexpr unsigned kMaskPlacements=2048;
    std::uint8_t pass_mask[kMaskPlacements]{}; bool masked=false;
#endif
} ps2w;
#if RE4DC_PS2_PASS_MASK==2
unsigned ps2_mask_stats[2]; // =2: placement-pass decisions checked, mismatched
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
#endif
struct Slot {
    const unsigned char* obj; std::uint32_t serial; float rest[12];
#if RE4DC_PS2_WORLD_PARTS
    PartPose* parts; unsigned nparts,pose_offset; bool source;
#endif
};
unsigned char* block=nullptr;                      // heap-4 block: the ids file
const std::uint8_t* ids=nullptr; unsigned nids=0; // placement field -> id
Slot* slots=nullptr; unsigned nslots=0;
std::uint8_t slot_of[kIds];                        // id -> slot (kNone: baked)
#if RE4DC_PS2_WORLD_PARTS
std::uint8_t object_order[kIds]; unsigned nobjects=0;
void order_object(unsigned id){
    unsigned at=0;
    for(;at<nobjects && object_order[at]!=id;++at){}
    if(at<nobjects){for(unsigned j=at+1;j<nobjects;++j)object_order[j-1]=object_order[j];--nobjects;}
    const auto key=reinterpret_cast<std::uintptr_t>(slots[slot_of[id]].obj);
    at=0;
    while(at<nobjects && reinterpret_cast<std::uintptr_t>(slots[slot_of[object_order[at]]].obj)<key)++at;
    for(unsigned j=nobjects;j>at;--j)object_order[j]=object_order[j-1];
    object_order[at]=std::uint8_t(id);++nobjects;
}
#endif
unsigned off_flag=0,off_serial=0,off_mat=0;        // cObj field offsets (from the first bind)
unsigned frame=~0U,nmoved=0;
std::uint8_t state[kIds];                          // this frame: 0 unknown, 1 baked, 2 hidden, 3 moved, 4 source hierarchy
std::uint8_t moved_of[kIds];
float delta[kMoved][12];
unsigned binds=0,hidden=0,moved=0,overflow=0,logged_frame=0;
void reset(){
    if(block)re4dc_static_free(block);
#if RE4DC_PS2_WORLD_PARTS
    if(slots)for(unsigned i=0;i<nslots;++i)if(slots[i].parts)re4dc_static_free(slots[i].parts);
    nobjects=0;
#endif
    if(slots)re4dc_static_free(slots);
    block=nullptr;ids=nullptr;nids=0;slots=nullptr;nslots=0;std::memset(slot_of,kNone,sizeof(slot_of));frame=~0U;
}
// 0 baked, 1 hidden, 2 moved (delta[moved_of[id]] = mat * inverse(rest)), 3 source hierarchy
unsigned query(unsigned id){
    const unsigned f=re4dc_ui_frame();
    if(f!=frame){frame=f;nmoved=0;std::memset(state,0,sizeof(state));}
    if(state[id])return state[id]-1U;
    unsigned r=0;
    Slot& s=slots[slot_of[id]];
    std::uint32_t flag=0,serial=0;
    if(s.obj){std::memcpy(&flag,s.obj+off_flag,4);std::memcpy(&serial,s.obj+off_serial,4);}
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
bool ps2_open(){
#if RE4DC_PS2_WORLD_ROOMS
    if((ps2w.storage || ps2w.attempted) && ps2w.room!=ps2w.want)ps2_free(); // another room's package
#endif
    if(ps2w.storage)return true;
    if(ps2w.attempted)return false;
    ps2w.attempted=true;
#if RE4DC_PS2_WORLD_ROOMS
    ps2w.room=ps2w.want;
    char mpath[48],ppath[48];
    snprintf(mpath,sizeof(mpath),"/cd/dc/native/r%03x/ps2-world.re4mesh",ps2w.room);
    snprintf(ppath,sizeof(ppath),"/cd/dc/native/r%03x/ps2-world.r4pw",ps2w.room);
    re4dc_log("PS2MESH room=%03x open\n",ps2w.room);
    const file_t fm=fs_open(mpath,O_RDONLY);
    const file_t fp=fs_open(ppath,O_RDONLY);
#else
    const file_t fm=fs_open("/cd/dc/native/r101/ps2-world.re4mesh",O_RDONLY);
    const file_t fp=fs_open("/cd/dc/native/r101/ps2-world.r4pw",O_RDONLY);
#endif
    const unsigned msize=fm!=FILEHND_INVALID?unsigned(fs_total(fm)):0U,psize=fp!=FILEHND_INVALID?unsigned(fs_total(fp)):0U;
    const unsigned mbytes=(msize+31U)&~31U,pbytes=(psize+31U)&~31U,total=mbytes+pbytes+kLutBytes+kGatherBytes;
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
    if(ok && !ps2w.package.adopt(s,msize,true,true)){why=ps2w.package.error();ok=false;}
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
            if(!std::memcmp(ih.magic,"R4ID",4) && ih.version==1 && ih.crc==h.crc && ih.count==h.placements &&
               ih.count<=isize-sizeof(ih)){
                const std::uint8_t* idv=ib+sizeof(ih);
                std::uint8_t count[dyn::kIds]={};
                for(unsigned i=0;i<ih.count;++i)if(idv[i]<dyn::kIds && count[idv[i]]<2)++count[idv[i]];
                unsigned n=0;
                for(unsigned id=0;id<dyn::kIds;++id)if(count[id]==1)++n;
                auto* sb=n?static_cast<dyn::Slot*>(re4dc_static_alloc(n*sizeof(dyn::Slot))):nullptr;
                iwhy="no heap";
                if(sb){
                    unsigned k=0;
                    for(unsigned id=0;id<dyn::kIds;++id)if(count[id]==1)dyn::slot_of[id]=std::uint8_t(k++);
                    std::memset(static_cast<void*>(sb),0,n*sizeof(dyn::Slot));
                    dyn::block=ib;dyn::ids=idv;dyn::nids=ih.count;dyn::slots=sb;dyn::nslots=n;ib=nullptr;
                    iwhy=nullptr;
                }
            }
        } else if(ib)iwhy="read";
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
#if RE4DC_MESH_FASTPATH
    auto* lut=reinterpret_cast<std::uint32_t*>(s+mbytes+pbytes);re4dc::vp::build_lut(lut);ps2w.lut=lut;
#endif
    ps2w.gather=reinterpret_cast<re4dc::room::CompactVertex12*>(s+mbytes+pbytes+kLutBytes);
    const auto& mh=ps2w.package.header();
#if RE4DC_PS2_INTERIOR_CULL
    // The cell's portals hold for the package it was built from only.
    pc::st.ok=ps2w.room==pc::kPcRoom && mh.crc==pc::kPcMeshCrc && h.crc==pc::kPcSidecarCrc && mh.bytes==pc::kPcMeshBytes;
    re4dc_log("PCCULL cell room=%03x mesh_crc=%08x sidecar_crc=%08x %s cells=%u portals=%u mode=%d\n",ps2w.room,unsigned(mh.crc),unsigned(h.crc),
        pc::st.ok?"adopted":"not this package",pc::kPcCellCount,pc::kPcPortalCount,int(RE4DC_PS2_INTERIOR_CULL));
    pc::data.lent=false;
    if(pc::st.ok)pc::load();
#endif
    re4dc_log("PS2MESH open bytes=%u version=%u meshes=%u parts=%u meshlets=%u vertices=%u placements=%u heap=%d->%d\n",
        total,mh.version,mh.mesh_count,mh.part_count,mh.meshlet_count,mh.vertex_count,h.placements,before,re4dc_static_heap_free());
    return true;
}
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
int ps2_pass(unsigned pass,float zfar){
    auto& c=ps2w.count[pass];c={};
#if RE4DC_SKY_ANY
    re4dc_ps2_sky_header=0;
#endif
    const float* P=ps2w.projection;
    if(P[0]!=0 || ps2w.viewport[2]<=0 || ps2w.viewport[3]<=0)return 0;
    const float near=P[6]/(P[5]-1),far=P[6]/P[5];
    if(!re4dc::render::is_finite(near)||!re4dc::render::is_finite(far)||near<=0||far<=near)return 0;
    float cull_far=far;
    if(zfar>near && zfar<cull_far)cull_far=zfar;
#ifdef RE4DC_FAR_CAP
    if(cull_far>float(RE4DC_FAR_CAP))cull_far=float(RE4DC_FAR_CAP); // FOG_FAR_CAP (post30.mk): follows FOG_FAR
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
#if RE4DC_SKY_ANY
    const float pass_cull_far=cull_far;
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
                s.active=t.active;s.cell=t.cell;s.nfr=t.nfr;s.corner=t.corner;
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
    Re4dcModelPart part{};
    std::memcpy(part.projection,P,sizeof(part.projection));std::memcpy(part.viewport,ps2w.viewport,sizeof(part.viewport));
    part.alpha_state=255;part.source_key[2]=1;
    const float px_x=RE4DC_SCREEN_HALF_WF*std::fabs(P[1]),px_y=RE4DC_SCREEN_HALF_HF*std::fabs(P[3]);
    const float px=px_x>px_y?px_x:px_y;
#if RE4DC_QUALITY
    const float lod_px=re4dc_quality()->lod_px;
#else
    const float lod_px=float(RE4DC_MESH_LOD_PX);
#endif
    const auto& pk=ps2w.package;
    for(unsigned i=0;i<ps2w.nplacements;++i){
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
#if RE4DC_PS2_PASS_MASK
        const bool masked=ps2w.masked && RE4DC_PS2_MASK_ON;
        if(masked && !((ps2w.pass_mask[i]>>pass)&1U))continue;
#endif
        const auto& pl=ps2w.placements[i];const auto& mesh=pk.meshes()[pl.mesh];
#if RE4DC_PS2_PASS_MASK
        if(!masked)
#endif
        {
        bool any=false;
        for(unsigned k=0;k<mesh.part_count && !any;++k)any=ps2w.parts[mesh.first_part+k].pass==pass;
        if(!any)continue;
        }
#if RE4DC_PS2_WORLD_DYNAMIC
        const float* affine=pl.affine;float moved_affine[12];
        if(dyn::ids && pl.placement<dyn::nids){
            const unsigned id=dyn::ids[pl.placement];
            if(id<dyn::kIds && dyn::slot_of[id]!=dyn::kNone){
                const unsigned st=dyn::query(id);
                if(st==1
#if RE4DC_PS2_WORLD_PARTS
                    || st==3
#endif
                )continue;   // hidden, or drawn with its source part hierarchy
                if(st==2){concat(dyn::delta[dyn::moved_of[id]],pl.affine,moved_affine);affine=moved_affine;}
            }
        }
        ++c.placements;
        float mv[12];concat(ps2w.view,affine,mv);
#define RE4DC_PS2_AFFINE affine
#else
        ++c.placements;
        float mv[12];concat(ps2w.view,pl.affine,mv);
#define RE4DC_PS2_AFFINE pl.affine
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
        if(!re4dc::render::group_visible(bounds,mv,P,ps2w.viewport,near,cull_far,0)){++c.culled;continue;}
        const float grid[12]={mesh.step[0],0,0,mesh.origin[0], 0,mesh.step[1],0,mesh.origin[1], 0,0,mesh.step[2],mesh.origin[2]};
#if RE4DC_PS2_INTERIOR_CULL
        // 0 no test (no cell, or the placement is inside the house box), 1 test its clusters, 2 wholly hidden.
        unsigned pc_state=0;float pc_wq[21];
        if(pc::st.active){
            float wc[3],wh[3];
            const float blo[3]={mesh.bounds_min[0],mesh.bounds_min[1],mesh.bounds_min[2]},bhi[3]={mesh.bounds_max[0],mesh.bounds_max[1],mesh.bounds_max[2]};
            pc::world_box(RE4DC_PS2_AFFINE,blo,bhi,wc,wh);
            bool inside=true; // the placement box inside the house box: nothing in it can be outside
            for(unsigned a=0;a<3;++a)inside=inside && wc[a]-wh[a]>=pc::kPcOuter[a] && wc[a]+wh[a]<=pc::kPcOuter[3+a];
            if(!inside){
                pc_state=pc::hidden(wc,wh)>0?2U:1U;
                concat(RE4DC_PS2_AFFINE,grid,pc_wq);pc::abs_rows(pc_wq);
            }
#if RE4DC_PS2_INTERIOR_CULL!=2
            if(pc_state==2){++pc::st.placements;continue;}
#endif
        }
#endif
        float mvq[12];concat(mv,grid,mvq);
        float scale=0;
        for(unsigned r=0;r<3;++r){
            const float n=mv[4*r]*mv[4*r]+mv[4*r+1]*mv[4*r+1]+mv[4*r+2]*mv[4*r+2];
            if(n>scale)scale=n;
        }
        const float lod_scale=std::sqrt(scale)*px/lod_px;
        for(unsigned k=0;k<mesh.part_count;++k){
            const unsigned index=mesh.first_part+k;const auto& meta=ps2w.parts[index];
            if(meta.pass!=pass)continue;
            ++c.parts;part.cull=meta.cull;
            MeshDraw d{{part,{},near,far},pk,pk.parts()[index],ps2w.lut,ps2w.gather};
            d.alpha=0xff000000U;d.vertex_alpha=false;d.cull_far=cull_far;d.direct=true;
            d.part_index=index;d.lod_scale=lod_scale;
            std::memcpy(d.mvq,mvq,sizeof(mvq));std::memcpy(d.mv,mvq,sizeof(mvq));
            const unsigned key[6]={meta.crc,meta.fnv,meta.width,meta.height,pass,meta.cull};d.ps2=key;
#if RE4DC_PS2_INTERIOR_ACTORS && RE4DC_PS2_INTERIOR_CULL==2
            if(!pass && !pcact::have_key){std::memcpy(pcact::key,key,sizeof(key));pcact::key[5]=0;pcact::have_key=true;}
#endif
#if RE4DC_PS2_INTERIOR_CULL
            d.pc_mode=pc_state?1U:0U;d.pc_wq=pc_wq;
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
            if(result>0)++c.native;
            else if(result<0){re4dc_model_packet_abort();++c.aborts;return -1;}
            else ++c.fallback;
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
    return c.fallback?0:1;
}
}
extern "C" void re4dc_ps2_mesh_camera(const float* view,const float* projection,const float* viewport){
    std::memcpy(ps2w.view,view,sizeof(ps2w.view));
    std::memcpy(ps2w.projection,projection,sizeof(ps2w.projection));
    std::memcpy(ps2w.viewport,viewport,sizeof(ps2w.viewport));
    ps2w.camera=true;
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
extern "C" int re4dc_ps2_mesh_draw(unsigned pass,float zfar){
#if RE4DC_PS2_INTERIOR_CULL==2
    if(!pass)pc_scan(re4dc_ui_frame());
#endif
    if(pass>2 || !ps2w.camera || !ps2_open())return 0;
    return ps2_pass(pass,zfar)>0;
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
    ps2w.package.close();
    if(ps2w.storage)re4dc_static_free(ps2w.storage);
    ps2w.storage=nullptr;ps2w.bytes=0;ps2w.parts=nullptr;ps2w.placements=nullptr;ps2w.nplacements=0;
    ps2w.lut=nullptr;ps2w.gather=nullptr;ps2w.attempted=false;
#if RE4DC_PS2_PASS_MASK
    ps2w.masked=false;
#endif
#if RE4DC_PS2_WORLD_DYNAMIC
    dyn::reset();
#endif
#if RE4DC_PS2_INTERIOR_CULL
    pc::unload();pc::data.lent=false;
    pc::st.ok=false;pc::st.active=false;
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
#if RE4DC_PS2_WORLD_PARTS
    if(s.parts)re4dc_static_free(s.parts);
    s.parts=nullptr;s.nparts=0;s.source=false;
#endif
    s.obj=o;std::memcpy(&s.serial,serial,4);std::memcpy(s.rest,mat,sizeof(s.rest));
#if RE4DC_PS2_WORLD_PARTS
    dyn::order_object(id);dyn::state[id]=0;
#endif
    ++dyn::binds;
}
#if RE4DC_PS2_WORLD_PARTS
extern "C" void re4dc_ps2_dyn_parts(unsigned room,unsigned id,const void* object,const void* first,
                                     unsigned count,unsigned next_offset,unsigned pose_offset){
    if(!dyn::ids || ps2w.room!=room || id>=dyn::kIds || dyn::slot_of[id]==dyn::kNone || !count || count>255)return;
    dyn::Slot& s=dyn::slots[dyn::slot_of[id]];
    if(s.obj!=object || s.parts)return;
    auto* poses=static_cast<dyn::PartPose*>(re4dc_static_alloc(count*sizeof(dyn::PartPose)));
    if(!poses){re4dc_log("PS2PART no heap id=%02x parts=%u\n",id,count);return;}
    const auto* p=static_cast<const unsigned char*>(first);
    for(unsigned i=0;i<count;++i){
        if(!p){re4dc_static_free(poses);re4dc_log("PS2PART short chain id=%02x part=%u/%u\n",id,i,count);return;}
        poses[i].part=p;std::memcpy(poses[i].pose,p+pose_offset,sizeof(poses[i].pose));
        std::memcpy(&p,p+next_offset,sizeof(p));
    }
    s.parts=poses;s.nparts=count;s.pose_offset=pose_offset;
    re4dc_log("PS2PART bind id=%02x parts=%u bytes=%u heap=%d\n",id,count,unsigned(count*sizeof(dyn::PartPose)),re4dc_static_heap_free());
}
extern "C" int re4dc_ps2_dyn_source(unsigned room,const void* object,unsigned serial){
    if(!dyn::ids || ps2w.room!=room)return 0;
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
extern "C" int re4dc_ps2_world_room(unsigned room){
    const unsigned stage=room>>8,index=room&255U;
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
// re4dc_static_submit on a non-coarse image of a no-std room: once per image, the loaded package only (no I/O).
extern "C" void re4dc_ps2_mesh_source(unsigned room,const Re4dcModelPart& p){
#if RE4DC_SS_UI_ORDER
    // Inventory rigid models also carry static_geometry. They are not room scenery:
    // submitting the PS2 world here would close the subscreen's ordered TR list.
    if(re4dc_ss_ui_order())return;
#endif
    static unsigned last=~0U,images=0;
    const unsigned frame=re4dc_ui_frame();
    (void)p; // an unbound scenery part carries no camera (world / view are the binding's): the game's
    if(frame==last || !ps2w.storage || ps2w.room!=room)return;
    last=frame;
    float view[12],projection[7],viewport[6];
    if(!re4dc_coarse_source_camera(view,projection,viewport))return;
    re4dc_ps2_mesh_camera(view,projection,viewport);
    const int drawn=re4dc_ps2_world_source_draw();
    if(++images<=8 || !(images%120))re4dc_log("PS2MESH source image frame=%u room=%03x drawn=%d images=%u\n",frame,room,drawn,images);
}
#endif
#if RE4DC_PS2_PRELOAD_LEAN
// PS2_PRELOAD_LEAN (game30.mk): the open package's part textures for the room preload (native_ui.cpp), in part
// order with repeats (the caller skips keys it has); 0 past the end or when no package is open.
extern "C" int re4dc_ps2_mesh_texture(unsigned i,unsigned out[4]){
    if(!ps2w.storage || !ps2w.parts || ps2w.room!=ps2w.want || i>=ps2w.package.header().part_count)return 0;
    const auto& q=ps2w.parts[i];
    out[0]=q.crc;out[1]=q.fnv;out[2]=q.width;out[3]=q.height;
    return 1;
}
#endif
// The room the next ps2_open serves (native_ps2_world.cpp, before each draw).
extern "C" void re4dc_ps2_mesh_select(unsigned room){ps2w.want=room;}
// This room's package was tried and did not open: its own scenery draws (re4dc_ps2_world_covers).
extern "C" int re4dc_ps2_mesh_failed(unsigned room){return ps2w.attempted && !ps2w.storage && ps2w.room==room;}
#endif
#endif
