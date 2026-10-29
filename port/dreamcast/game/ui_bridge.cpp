#include "platform/include/movie_world_arena.h"
#include "platform/include/gc_asset_lifecycle.h"
#if defined(RE4DC_KOS_CACHE_P2_DIAG) && RE4DC_KOS_CACHE_P2_DIAG
#include "platform/include/kos_cache_p2_diag.h"
#endif
// Source ID layout/animation/ordering -> existing native texture/PVR mechanisms.
#include "light.h"
#include "id_sys.h"
#include "texture.h"
#include "camera.h"
#include "main_mem.h"
#include "gx.h"
#include "native_ui.h"
#include "hud_source_mask.h"
#include "re4dc_pad_prompts.h"
#include "re4dc_manual_pages.h"
#if RE4DC_OPTION_ROW_STYLE && RE4DC_RENDER_OPTION
extern "C" void re4dc_option_rows_art(const Re4dcUiQuad*);
#endif
#if RE4DC_NATIVE_STATIC && RE4DC_NATIVE_PKG_HIGH
#include "re4dc_platform.h"
#endif
extern "C" void GXGetProjectionv(float*);
extern "C" void GXGetViewportv(float*);
extern "C" void GXProject(float,float,float,const float[3][4],const float*,const float*,float*,float*,float*);

#if RE4DC_ITEM_UI_ORDER
#include "global.h"
// sceAtGetItem sets this bit for the source ItemExamine pickup lifecycle.
// This is a rendering-order query only; it does not imply a swapped heap.
extern "C" int re4dc_item_ui_order() { return pG && (pG->Status_flg[1] & 2U); }
#endif
extern "C" int OSCheckHeap(int);
#if defined(RE4DC_MOTION_CAPACITY) && RE4DC_MOTION_CAPACITY
extern "C" int OSDisableInterrupts();
extern "C" int OSRestoreInterrupts(int);
#endif
extern "C" int re4dc_ui_heap_free() { return OSCheckHeap(Heap[MemGetCurrentHeap()].handle); }

extern "C" void* re4dc_ui_stage_alloc(unsigned bytes) {
    return mem_alloc(bytes, "native UI texture staging", 0, 1, MEM_HEAP_CURRENT);
}
extern "C" void re4dc_ui_stage_free(void* data) { Mem_free(data); }

#ifndef RE4DC_UI_QUAD_LEAN
#define RE4DC_UI_QUAD_LEAN 0
#endif
#ifndef RE4DC_UI_DRAW_LEAN
#define RE4DC_UI_DRAW_LEAN 0
#endif
#if RE4DC_UI_QUAD_LEAN
// UI_QUAD_LEAN (game30.mk, make-room F1; exact): the four corners of an ID quad are projected inline with
// GXProject's own x / y expressions (platform/gx_stub.cpp). This object is built with the same game flags as
// gx_stub.o (-O1 -ffp-contract=off), so every corner gets the same fmul / fadd / fdiv on the same operands in the
// same order. Gone: the call per corner and the depth output (sz, and vz under an orthographic projection), which
// the quad never reads. =2 also calls GXProject and compares x and y bit for bit ("UQL xy" lines).
static inline void ui_project_xy(f32 x, f32 y, f32 z, const f32 mtx[3][4], const f32* pm, const f32* vp,
                                 f32* sx, f32* sy)
{
    f32 vx = mtx[0][0] * x + mtx[0][1] * y + mtx[0][2] * z + mtx[0][3];
    f32 vy = mtx[1][0] * x + mtx[1][1] * y + mtx[1][2] * z + mtx[1][3];
    f32 px, py, pw;
    if (pm[0] == 0.0f) {
        f32 vz = mtx[2][0] * x + mtx[2][1] * y + mtx[2][2] * z + mtx[2][3];
        px = pm[1] * vx + pm[2] * vz;
        py = pm[3] * vy + pm[4] * vz;
        pw = -vz;
        if (pw == 0.0f) pw = 1e-6f;
        pw = 1.0f / pw;
    } else {
        px = pm[1] * vx + pm[2];
        py = pm[3] * vy + pm[4];
        pw = 1.0f;
    }
    *sx = vp[2] / 2.0f * px * pw + vp[0] + vp[2] / 2.0f;
    *sy = -(vp[3] / 2.0f) * py * pw + vp[1] + vp[3] / 2.0f;
}
#if RE4DC_UI_QUAD_LEAN >= 2
#include "re4dc_platform.h"
static unsigned uql_quads, uql_corners, uql_persp, uql_mismatch;
static void uql_check(f32 x, f32 y, f32 cx, f32 cy, const f32* pm)
{
    unsigned a[2], b[2]; const f32 n[2] = {x, y}, o[2] = {cx, cy};
    __builtin_memcpy(a, n, sizeof(a)); __builtin_memcpy(b, o, sizeof(b));
    ++uql_corners; if (pm[0] == 0.0f) ++uql_persp;
    if ((a[0] != b[0] || a[1] != b[1]) && uql_mismatch++ < 8)
        re4dc_log("UQL xy MISMATCH inline=%08x,%08x GXProject=%08x,%08x\n", a[0], a[1], b[0], b[1]);
}
#endif
#endif
#if defined(RE4DC_LETTERBOX_CLIP) && RE4DC_LETTERBOX_CLIP
extern "C" void re4dc_lbx_note(unsigned cls,unsigned tex_id,unsigned tex_no,unsigned argb,const float* xy);
#endif
extern "C" void re4dc_draw_id_quad(const IdUnit* u) {
    TexWk* wk = IdGetTexWk(u->texId, 1);
    if (!wk || !wk->pTpl || u->texNo >= wk->pTpl->numDescriptors) return;
    const TEXDescriptor* descriptor = TEXGet(wk->pTpl, u->texNo);
    const TEXHeader* tex = descriptor->textureHeader;
#if RE4DC_UI_DRAW_LEAN
    // All other fields are assigned below, including every XY/UV word. Only an absent
    // palette needs defaults; avoid clearing the 104-byte quad before overwriting it.
    Re4dcUiQuad q;
    q.image.palette = nullptr;
    q.image.palette_bytes = 0;
#else
    Re4dcUiQuad q = {};
#endif
    q.image.pixels = tex->data;
    q.image.width = tex->width; q.image.height = tex->height;
    q.image.format = tex->format; q.image.palette_format = 0xffffffffU;
    if (descriptor->CLUTHeader) {
        q.image.palette = descriptor->CLUTHeader->data;
        q.image.palette_format = descriptor->CLUTHeader->format;
        q.image.palette_bytes = descriptor->CLUTHeader->numEntries * 2;
    }
#if RE4DC_PAD_PROMPTS
    // Only the live binocular zoom glyph, never shared C-stick textures.
    if(u->classNo==0x24 && u->markNo==0x30 && u->texId==0x89 &&
       u->texNo==0 && !(u->tex_flag&1)) {
        const unsigned kind=re4dc_pad_prompt_kind(0,1);
        Re4dcUiImage image;
        if(kind && re4dc_ui_binocular_prompt(&q.image,kind,&image))q.image=image;
    }
#endif
    CameraCurrentProjection();
    Mtx model;
    RE4DC_RENDER_MTXConcat(IDSystem::m_scrn_mat, u->mat, model);
    float projection[7], viewport[6];
    RE4DC_GXF_GET_PROJECTION(projection); RE4DC_GXF_GET_VIEWPORT(viewport);
    for (unsigned i=0; i<4; ++i) {
#if RE4DC_UI_QUAD_LEAN
        float x,y;
        ui_project_xy(u->vtx[i].x, u->vtx[i].y, u->vtx[i].z, model, projection, viewport, &x, &y);
#if RE4DC_UI_QUAD_LEAN >= 2
        {float cx,cy,cz;
         GXProject(u->vtx[i].x, u->vtx[i].y, u->vtx[i].z, model, projection, viewport, &cx, &cy, &cz);
         uql_check(x, y, cx, cy, projection);}
#endif
#else
        float x,y,z;
        GXProject(u->vtx[i].x, u->vtx[i].y, u->vtx[i].z, model,
                  projection, viewport, &x, &y, &z);
#endif
        q.xy[2*i] = x * 640.0f / viewport[2];
        q.xy[2*i+1] = y * 480.0f / viewport[3];
    }
#if RE4DC_UI_QUAD_LEAN >= 2
    if ((++uql_quads & 2047) == 0)
        re4dc_log("UQL xy quads=%u corners=%u perspective=%u mismatch=%u\n", uql_quads, uql_corners, uql_persp, uql_mismatch);
#endif
#if defined(RE4DC_LETTERBOX_CLIP) && RE4DC_LETTERBOX_CLIP
    re4dc_lbx_note(u->classNo,u->texId,u->texNo,((unsigned)(u8)u->col[3]<<24)|((unsigned)(u8)u->col[0]<<16)|
                   ((unsigned)(u8)u->col[1]<<8)|(u8)u->col[2],q.xy);  // platform/letterbox_clip.cpp
#endif
    const float uv[8]={u->u0,u->v0,u->u1,u->v0,u->u1,u->v1,u->u0,u->v1};
    for(unsigned i=0;i<8;++i) q.uv[i]=uv[i];
    q.color=((unsigned)(u8)u->col[3]<<24)|((unsigned)(u8)u->col[0]<<16)|
            ((unsigned)(u8)u->col[1]<<8)|(u8)u->col[2];
    q.blend=u->blend_type; q.masked=u->tex_flag & 1;
#if RE4DC_UI_HUD_MASK
    // Source IdCommonTrans only: exact constant core colour + two HUD masks.
    // Keep live vertices/UV/colour/blend and the original OT callback order.
    if(u->trans_type==0 && q.masked && u->texId==0x0a && u->texNo==0 &&
       u->maskNo==0 && (u->maskId==0x12 || u->maskId==0x17) && q.blend<=1) {
        TexWk* mask_wk=IdGetTexWk(u->maskId,1);
        if(mask_wk && mask_wk->pTpl && mask_wk->pTpl->numDescriptors) {
            const TEXDescriptor* md=TEXGet(mask_wk->pTpl,0);
            const TEXHeader* mt=md?md->textureHeader:nullptr;
            if(mt && md->CLUTHeader && mt->minFilter==1 && mt->magFilter==1 &&
               mt->minLOD==0 && mt->maxLOD==0 && mt->LODBias==0.0f &&
               !mt->edgeLODEnable) {
                Re4dcUiImage mask={mt->data,md->CLUTHeader->data,mt->width,mt->height,
                    mt->format,md->CLUTHeader->format,unsigned(md->CLUTHeader->numEntries)*2};
                if(re4dc_ui_hud_mask_submit(&q,&mask))return;
            }
        }
    }
#endif
    re4dc_ui_submit(&q);
#if RE4DC_OPTION_ROW_STYLE && RE4DC_RENDER_OPTION
    if (u->classNo == 0x2A && u->markNo == 5)
        re4dc_option_rows_art(&q);
#endif
}

#include "global.h"
#include "player.h"
#include "native_render_profile.hpp"
#include <stdio.h>
#include <string.h>
extern "C" void re4dc_profile_source(re4dc::profile::Source* out){
    *out={};if(!pG)return;
    out->tick=pG->Frame_cnt;out->system=pG->System_flg;out->stop=pG->Stop_flg;
    out->room=(unsigned(pG->stage_no)<<8)|pG->room_no;
    memcpy(out->room_flags,pG->Room_flg,sizeof(out->room_flags));memcpy(out->status,pG->Status_flg,sizeof(out->status));
    memcpy(out->camera,&pG->Cam.param,sizeof(out->camera));
    if(pPL){memcpy(out->player,&pPL->pos,12);memcpy(out->player+3,&pPL->ang,12);
        out->motion_frame=pPL->Motion.Mot_frame;out->motion_state=pPL->Motion.Mot_state;}
}

extern "C" unsigned re4dc_fixture_source_frame(){ return pG ? pG->Frame_cnt : 0; }

// Controller context for platform/pad.cpp (reads last frame's state, writes nothing):
// 1 LOOK while CameraQuasiFPS::calcDepressionRatio takes Key.substick (player free
// movement: routine 1 idle / walk / back / run / turn / 180 turn / crouch, not aiming),
// 2 ZOOM while the scope (Status_flg[0] 0x40, CameraScope) or binocular (0x400,
// CameraBinocular) camera zooms on the C-stick Y, 0 NATIVE otherwise. The title never
// reads as play: every return to it goes through systemRestartInit, which clears Rno0.
#if RE4DC_W11_FIXTURE
extern "C" void re4dc_w11_frame();
#endif
extern "C" int re4dc_pad_context(){
#if RE4DC_W11_FIXTURE
    re4dc_w11_frame();                                  // W11 test instrumentation (sscrn_bridge.cpp)
#endif
    if(!pG||!pPL||pG->Rno0!=3)return 0;             // gameMainLoop only (not options / door demo / ending)
    unsigned s0=pG->Status_flg[0];
    if(!(s0&0x02000000))return 0;                    // sub screen open or look-down camera (arm bit cleared)
    if(s0&0x400)return 2;                            // binoculars read Joy[0] directly, even under KeyStop
    if(pG->Stop_flg&0x80000000)return 0;             // KeyStop: events, messages, QTEs
    if(s0&0x40)return 2;                             // scope: CameraScope zooms while R (Key 0x10) is held
    if(s0&0x8000)return 0;                           // other first-person views
    if(pPL->hp<=0||pPL->r_no_0!=0)return 0;
    switch(pPL->r_no_1){case 0:case 1:case 2:case 3:case 4:case 5:case 0x11:return 1;}
    return 0;
}

// Which source debug chords would fire now (platform/pad.cpp masks them unless RE4DC_DEBUG_PAD):
// 1 gameDebug's L+START debug menu (game.cpp: Debug_flg[0] bit 31 clear), 2 the sub screen is
// open in a type whose raw Joy Z toggles the item-make / puzzle debug menus (all but the
// Z-opened map, SS_OPEN_MAP, where Z closes the map).
#include "sscrn.h"
extern "C" int re4dc_pad_debug_state(){
    if(!pG)return 0;
    int s=(s32)pG->Debug_flg[0]>=0?1:0;
    if(SubScreenWk.type!=0&&SubScreenWk.type!=SS_OPEN_MAP)s|=2;
    return s;
}

// ---------------------------------------------------------------- room lifecycle
// Order of a room change (src/game): gameDoordemo -> gameStageInit -> StageSet
// [re4dc_room_leave; reload: MemReplaceHeap(1,2); relink: stopRelData,
// MemReplaceHeap(2,3), linkRelData] -> gameRoomInit -> gameRoomMemInit
// [retire hooks again (idempotent), MemReplaceHeap(3,4), re4dc_room_enter].
// One audit line per phase, compared by the capture tooling across round
// trips: enter (heap 4 just rebuilt), steady (a fixed frame count into the
// room) and leave (native owners retired, before any heap is replaced).
#include "room_data.h"
#include "sce_sys.h"
#include "game.h"
#include "native_motion.h"
#include "native_effect.h"
#include "re4dc_platform.h"
extern "C" void re4dc_kos_heap_state(unsigned* free_chunks,unsigned* used,unsigned* break_room);
extern "C" unsigned re4dc_vram_free();
extern "C" int re4dc_fixture_read(const char* path,char* buffer,unsigned size);
extern "C" void re4dc_aram_state(unsigned long* stack_pointer,unsigned long* free_blocks);
extern "C" void re4dc_module_counts(unsigned* fresh,unsigned* restarts,unsigned* unlinks,unsigned* linked);
extern "C" void re4dc_os_thread_stats(unsigned* registered,unsigned* reaped,unsigned* pending);
extern "C" void re4dc_room4_open();
extern "C" void re4dc_room4_close();
#if defined(RE4DC_ROOM_FILE) && RE4DC_ROOM_FILE
#include "room_file.h"  // ENGINE_PREVIEW / ENEMY_VIS_CULL (engine_preview.mk): the room data file's lifecycle
#endif
#if defined(RE4DC_ENGINE_PREVIEW) && RE4DC_ENGINE_PREVIEW
#include "actor_rt.h"
#endif
#if defined(RE4DC_ENEMY_VIS_CULL) && RE4DC_ENEMY_VIS_CULL
#include "room_vis.h"
#endif
#if defined(RE4DC_KOS_CENSUS) && RE4DC_KOS_CENSUS
extern "C" void re4dc_kos_census_log(const char* phase,unsigned room);  // platform/kos_census.cpp
#if RE4DC_KOS_CENSUS>=2
extern "C" void re4dc_kos_census_window(unsigned room,unsigned frame);
extern "C" void re4dc_kos_threads_report(void);
#endif
#endif
extern "C" int re4dc_room4_state(unsigned* generation,unsigned* cells,unsigned* bytes,unsigned* stale,unsigned* refused);
namespace {
struct AuditValues { int heap4_free; unsigned vram_free,kos_free,kos_break; bool valid; };
AuditValues last_audit[3];         // enter, steady, leave
const char* const kPhase[3]={"enter","steady","leave"};
unsigned room_frames;              // gameMainLoop frames since the room was entered
bool steady_logged;
void audit(int phase){
    unsigned kos_free=0,kos_used=0,kos_break=0,fresh=0,restarts=0,unlinks=0,linked=0,threads=0,reaped=0,pending=0;
    unsigned generation=0,cells=0,cell_bytes=0,stale=0,refused=0;
    unsigned long aram_sp=0,aram_blocks=0;
    re4dc_kos_heap_state(&kos_free,&kos_used,&kos_break);
    re4dc_aram_state(&aram_sp,&aram_blocks);
    re4dc_module_counts(&fresh,&restarts,&unlinks,&linked);
    re4dc_os_thread_stats(&threads,&reaped,&pending);
    re4dc_room4_state(&generation,&cells,&cell_bytes,&stale,&refused);
    const unsigned vram=re4dc_vram_free();
    // Every existing source heap must pass the SDK's own consistency walk.
    char bad[16]="";unsigned nbad=0;
    for(int h=0;h<MEM_HEAP_NUM;++h){
        if(Heap[h].handle<0 || Heap[h].status)continue;
        if(OSCheckHeap(Heap[h].handle)<0 && nbad<8){bad[nbad++]=char(h<10?'0'+h:'a'+h-10);bad[nbad]=0;}
    }
    const int heap4=Heap[4].handle>=0?OSCheckHeap(Heap[4].handle):-2;
    // Two lines: re4dc_log formats into 256 bytes.
    re4dc_log("room lifecycle: phase=%s room=%03x generation=%u frames=%u heap4=%08x-%08x size=%u free=%d "
        "heap_check=%s%s native4=%u/%u stale=%u refused=%u\n",
        kPhase[phase],unsigned(pG?pG->room_id:0),generation,room_frames,Heap[4].start,Heap[4].end,
        Heap[4].end-Heap[4].start,heap4,nbad?"bad:":"ok",bad,cells,cell_bytes,stale,refused);
    re4dc_log("room lifecycle: phase=%s vram_free=%u kos_free=%u kos_used=%u kos_break=%u aram_sp=%lx "
        "aram_blocks=%lu modules=%u/%u/%u/%u threads=%u/%u/%u heap=%d\n",
        kPhase[phase],vram,kos_free,kos_used,kos_break,aram_sp,aram_blocks,fresh,restarts,unlinks,linked,
        threads,reaped,pending,int(MemGetCurrentHeap()));
    AuditValues& previous=last_audit[phase];
    const AuditValues now{heap4,vram,kos_free,kos_break,true};
    if(previous.valid)
        re4dc_log("room lifecycle: phase=%s drift heap4=%d vram=%d kos=%d\n",kPhase[phase],
            now.heap4_free-previous.heap4_free,int(now.vram_free-previous.vram_free),
            int(now.kos_free+now.kos_break)-int(previous.kos_free+previous.kos_break));
    previous=now;
    // KOS malloc has only a few KB left once the source arena is carved;
    // thread records, file handles and texture metadata come out of it.
    if(kos_free+kos_break<1024)re4dc_log("room lifecycle: WARNING KOS headroom %u < 1024\n",kos_free+kos_break);
#if defined(RE4DC_KOS_CENSUS) && RE4DC_KOS_CENSUS
    re4dc_kos_census_log(kPhase[phase],unsigned(pG?pG->room_id:0));  // KOS_CENSUS=1 (diagnostic): live KOS blocks by caller
#endif
}
}

#if RE4DC_IO_PROBE
// IO_PROBE: room-entry telemetry for the room cycle fixture. At the door request the DVD
// blocking counters (dvd.cpp), the motion-key wait total (native_motion.cpp) and, with
// DISC_ASYNC, the disc service counters are reset. On the first in-room frame one "iotime:"
// line reports the wall time and game frames of the transition, the time the game spent
// blocked in source DVD reads and in motion-key reads, and the bytes; the rest of the wall
// time is CPU. After 240 in-room frames a second line reports the same for steady play.
#include <kos/timer.h>
extern "C" void re4dc_dvd_block_stats(unsigned* n, unsigned long long* total_us, unsigned* worst_us, int reset);
extern "C" unsigned long long re4dc_motion_wait_total_us;
extern "C" unsigned re4dc_ui_frame();
extern "C" void re4dc_iowrap_reset(void);                          // io_wrap.cpp
extern "C" void re4dc_iowrap_report(const char* what, unsigned cycle, unsigned long long wall_us);
#include "native_motion.h"
namespace {
struct IoCycle { unsigned no; const char* mode; unsigned long long t0, t_enter; unsigned f0; bool pending, steady; Re4dcMotionStats m0; unsigned uf0; };
IoCycle io_cycle{};
void io_reset(){
    unsigned a,b;unsigned long long t;
    re4dc_dvd_block_stats(&a,&t,&b,1);
    re4dc_motion_wait_total_us=0;
    re4dc_motion_get_stats(&io_cycle.m0);
    io_cycle.uf0=re4dc_ui_frame();
    re4dc_iowrap_reset();
}
void io_report(const char* what,unsigned long long wall){
    unsigned bn,bw;unsigned long long bt;
    re4dc_dvd_block_stats(&bn,&bt,&bw,1);
    Re4dcMotionStats m;re4dc_motion_get_stats(&m);
    re4dc_log("iotime: %s cycle=%u mode=%s wall_us=%llu enter_us=%llu game_frames=%u dvd_block n=%u total_us=%llu "
              "worst_us=%u motion loads=%u kb=%llu wait_us=%llu worst_wait_us=%llu ui_frames=%u-%u\n",what,io_cycle.no,io_cycle.mode,wall,
              io_cycle.t_enter>io_cycle.t0?io_cycle.t_enter-io_cycle.t0:0ULL,unsigned(pG->Frame_cnt-io_cycle.f0),bn,bt,bw,
              m.loads-io_cycle.m0.loads,(m.bytes_read-io_cycle.m0.bytes_read)/1024,re4dc_motion_wait_total_us,m.worst_wait_us,io_cycle.uf0,re4dc_ui_frame());
    re4dc_iowrap_report(what,io_cycle.no,wall);
    io_reset();
}
extern "C" void re4dc_dvdhold_begin(void);   // platform/dvd.cpp: test-only equalized-door hold
extern "C" void re4dc_dvdhold_end(void);
void io_cycle_begin(unsigned no,const char* mode){
    re4dc_dvdhold_begin();
    io_cycle.no=no;io_cycle.mode=mode;io_cycle.t0=timer_us_gettime64();io_cycle.t_enter=0;
    io_cycle.f0=unsigned(pG->Frame_cnt);io_cycle.pending=true;io_cycle.steady=false;
    io_reset();
}
void io_cycle_enter(){ if(io_cycle.pending && !io_cycle.t_enter)io_cycle.t_enter=timer_us_gettime64(); }
void io_cycle_frame(unsigned frames_in_room){
    if(!io_cycle.pending)return;
    if(frames_in_room==1){
        const unsigned long long t=timer_us_gettime64();
        re4dc_dvdhold_end();
        io_report("door",t>io_cycle.t0?t-io_cycle.t0:0ULL);
        io_cycle.t0=timer_us_gettime64();io_cycle.t_enter=0;io_cycle.f0=unsigned(pG->Frame_cnt);io_cycle.steady=true;
    } else if(io_cycle.steady && frames_in_room==241){
        const unsigned long long t=timer_us_gettime64();
        io_report("steady",t>io_cycle.t0?t-io_cycle.t0:0ULL);
        io_cycle.pending=false;
    }
}
}
#endif
// StageSet entry (src/game/stage.cpp): the old room is over and every heap
// is still in place. Idempotent; gameRoomMemInit retires again for the paths
// that do not pass through StageSet (ending) and for the first room.
#if RE4DC_NATIVE_MODEL_REGISTRY_PACK
extern "C" void re4dc_registry_room_enter(unsigned room);   // coarse_actor_registry_pack.inc
extern "C" void re4dc_registry_room_leave();
#if defined(RE4DC_GANADO_VAR) && RE4DC_GANADO_VAR
extern "C" void re4dc_ganado_var_room_leave();         // coarse_actor_owner_ganado.inc (ACTOR_GANADO_PS2_STUMP)
#endif
#endif
#if RE4DC_ACTOR_PL08_PACK
extern "C" void re4dc_pl08_pack_room_enter();               // coarse_actor_pl08_pack.inc
extern "C" void re4dc_pl08_pack_room_leave();
#endif
#if defined(RE4DC_LEON_HAND_PACK) && RE4DC_LEON_HAND_PACK
extern "C" void re4dc_leon_hands_room_enter();              // coarse_actor_leon_hands.inc
#endif
#if defined(RE4DC_LEON_LOD) && RE4DC_LEON_LOD
extern "C" void re4dc_leon_lod_room_enter();                // coarse_actor_leon_lod.inc
#endif
#if defined(RE4DC_STATIC_OBJ_BATCH) && RE4DC_STATIC_OBJ_BATCH
extern "C" void re4dc_sob_room_leave();                     // model_bridge.cpp STATIC_OBJ_BATCH
#endif
#if defined(RE4DC_DISC_READ_METER) && RE4DC_DISC_READ_METER
extern "C" void re4dc_disc_meter_room(int what, unsigned room);  // platform/dvd_read_safe.cpp
#endif
#if defined(RE4DC_STATIC_OBJ_BAKE) && RE4DC_STATIC_OBJ_BAKE
extern "C" void re4dc_sob_bake_room_leave();                // model_bridge.cpp STATIC_OBJ_BAKE
#endif
extern "C" void re4dc_room_leave(){
#if defined(RE4DC_DISC_READ_METER) && RE4DC_DISC_READ_METER
    re4dc_disc_meter_room(0,unsigned(pG->room_id));   // the room-entry load time starts at the door
#endif
#if RE4DC_MOVIE_WORLD_ARENA
    // Must run before any native owner or source heap is retired.
    if(!re4dc_movie_world_before_room_retire()){
        re4dc_missing("movie world arena has an active reader at room retirement");return;
    }
#endif
    unsigned generation,cells,bytes,stale,refused;
    if(!re4dc_room4_state(&generation,&cells,&bytes,&stale,&refused))return;
    re4dc_motion_retire_all();
    re4dc_effect_retire_room();
#if RE4DC_NATIVE_MODEL_REGISTRY_PACK
    re4dc_registry_room_leave();                         // the room's model registry package (coarse_actor_registry_pack.inc)
#endif
#if RE4DC_ACTOR_PL08_PACK
    re4dc_pl08_pack_room_leave();                        // the pl08 costume package cell (coarse_actor_pl08_pack.inc)
#endif
#if defined(RE4DC_GANADO_VAR) && RE4DC_GANADO_VAR
    re4dc_ganado_var_room_leave();                       // ACTOR_GANADO_PS2_STUMP variant cell (coarse_actor_owner_ganado.inc)
#endif
#if defined(RE4DC_STATIC_OBJ_BATCH) && RE4DC_STATIC_OBJ_BATCH
    re4dc_sob_room_leave();                              // merged static-object lists (heap-4 cells)
#endif
#if defined(RE4DC_STATIC_OBJ_BAKE) && RE4DC_STATIC_OBJ_BAKE
    re4dc_sob_bake_room_leave();                         // baked-object state and rest copies (heap-4 cells)
#endif
    re4dc_ui_retire_room();
#if defined(RE4DC_ENGINE_PREVIEW) && RE4DC_ENGINE_PREVIEW
    re4dc_rt_room_leave();
#endif
#if defined(RE4DC_ENEMY_VIS_CULL) && RE4DC_ENEMY_VIS_CULL
    re4dc_room_vis_leave();
#endif
#if defined(RE4DC_ROOM_FILE) && RE4DC_ROOM_FILE
    re4dc_room_file_leave();                             // the room data file's heap-4 block (platform/room_file.c)
#endif
    re4dc_room4_close();
    audit(2);
#if defined(RE4DC_KOS_CACHE_P2_DIAG) && RE4DC_KOS_CACHE_P2_DIAG
    re4dc_cache_p2_diag_leave(unsigned(pG?pG->room_id:0xffff));
#endif
    re4dc_room4_state(&generation,&cells,&bytes,&stale,&refused);
    if(cells)re4dc_log("room lifecycle: %u native heap-4 cells (%u B) outlived retirement\n",cells,bytes);
}

// gameRoomMemInit after the source replaced heap 4: a new room heap exists.
#if RE4DC_QUALITY
extern "C" void re4dc_quality_freeze(const char* where);
#endif
#if RE4DC_VMU_DEBUG_SLOT
extern "C" void re4dc_dbgslot_room_enter();
extern "C" void re4dc_dbgslot_poll(unsigned generation, unsigned room_frames);
#endif
#if RE4DC_DBG_WARP
extern "C" void re4dc_warp_room_enter(void);
extern "C" void re4dc_warp_poll(void);
#endif
#if RE4DC_QUALITY_ASSETS
extern "C" void re4dc_std_room_enter(unsigned room);   // platform/native_static.cpp
#endif
extern "C" void re4dc_room_enter(){
#if defined(RE4DC_KOS_CACHE_P2_DIAG) && RE4DC_KOS_CACHE_P2_DIAG
    re4dc_cache_p2_diag_enter(unsigned(pG?pG->room_id:0xffff));
#endif
#if defined(RE4DC_DISC_READ_METER) && RE4DC_DISC_READ_METER
    re4dc_disc_meter_room(1,unsigned(pG->room_id));   // or here for the first room (no door)
#endif
#if RE4DC_QUALITY
    re4dc_quality_freeze("room");
#endif
#if RE4DC_QUALITY_ASSETS
    re4dc_std_room_enter((unsigned(pG->stage_no)<<8)|pG->room_no); // before any package open
#endif
#if RE4DC_IO_PROBE
    io_cycle_enter();
#endif
#if RE4DC_VMU_DEBUG_SLOT
    re4dc_dbgslot_room_enter();                         // ring entry; FILE 20 start (dbgslot_bridge.cpp)
#endif
#if RE4DC_DBG_WARP
    re4dc_warp_room_enter();                            // test warp rig: flags at the first entry
#endif
    re4dc_room4_open();
#if RE4DC_GC_ASSET_GATE
    if(pG)re4dc_gcasset_room_enter((unsigned(pG->stage_no)<<8)|pG->room_no);
    else re4dc_gcasset::unresolved(re4dc_gcasset::Ui,"room-without-global");
#endif
#if defined(RE4DC_ROOM_FILE) && RE4DC_ROOM_FILE
    re4dc_room_file_enter((unsigned(pG->stage_no)<<8)|pG->room_no);  // room data file into heap 4; absent = source path
#endif
#if defined(RE4DC_ENGINE_PREVIEW) && RE4DC_ENGINE_PREVIEW
    re4dc_rt_room_enter((unsigned(pG->stage_no)<<8)|pG->room_no);
#endif
#if defined(RE4DC_ENEMY_VIS_CULL) && RE4DC_ENEMY_VIS_CULL
    re4dc_room_vis_enter((unsigned(pG->stage_no)<<8)|pG->room_no);
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY_PACK
    re4dc_registry_room_enter((unsigned(pG->stage_no)<<8)|pG->room_no); // before the room's archives load and adopt
#endif
#if RE4DC_ACTOR_PL08_PACK
    re4dc_pl08_pack_room_enter();                        // reload the pl08 costume package if pl08 is bound
#endif
#if defined(RE4DC_LEON_HAND_PACK) && RE4DC_LEON_HAND_PACK
    re4dc_leon_hands_room_enter();                       // Leon's home hand poses into the AICA hand cache
#endif
#if defined(RE4DC_LEON_LOD) && RE4DC_LEON_LOD
    re4dc_leon_lod_room_enter();                         // a LEON_LOD level change requested since the last enter
#endif
    room_frames=0;steady_logged=false;
    audit(0);
}

// ---------------------------------------------------------------- room cycle fixture
// /cd/dc/roomcycle.txt "<mode> <count> <frames>": after <frames> gameMainLoop
// frames in a room (no event holding the game), leave through the source door
// demo into the same room at the same point, <count> times. Test only: absent
// file, no effect. Modes select the source path StageSet takes:
//   door    same room REL, heap 4 rebuilt in place;
//   relink  the room REL is relinked (RoomData.m_RelNo cleared, the r100->r101
//           path: MemReplaceHeap(2,3) over the live heap 4, fresh OSLink);
//   reload  the source continue (GameContinue(1): the save gameStageInit
//           wrote, System_flg 0x80000): stage heap 2, heap 3 and the REL are
//           all rebuilt.
namespace {
struct CycleFixture { bool loaded; int mode; unsigned count,frames,done; Vec pos; float y; unsigned char point; bool anchored; };
CycleFixture cycle{};
const char* const kCycleMode[3]={"door","relink","reload"};
void load_cycle(){
    cycle.loaded=true;
    char text[64]={};
    if(re4dc_fixture_read("/cd/dc/roomcycle.txt",text,sizeof(text)-1)<=0)return;
    char mode[16]={};unsigned count=0,frames=0;
    if(sscanf(text,"%15s %u %u",mode,&count,&frames)!=3)return;
    for(int i=0;i<3;++i)if(!strcmp(mode,kCycleMode[i]))cycle.mode=i+1;
    if(!cycle.mode)return;
    cycle.count=count;cycle.frames=frames;
    re4dc_log("room cycle: fixture mode=%s count=%u frames=%u\n",mode,count,frames);
}
}

// Top of gameMainLoop (Rno0 == 3). 1 = the door demo was requested.
#if RE4DC_W11_FIXTURE
extern "C" int re4dc_w11_room_poll(unsigned generation);
#endif
#if defined(RE4DC_EM35_DIAG) && RE4DC_EM35_DIAG
#include "em35_diag.h"
// EM35_DIAG=1 (game30.mk; diagnostic): game frames counted here; a live Mendez half that em35.cpp has not moved for
// 60 of them is logged once (cEmMgr::move skipped it: Stop_flg 0x20000000, or it left the alive list).
extern "C" { Re4dcEm35Diag re4dc_em35_diag[2]; unsigned re4dc_em35_diag_polls; }
namespace { unsigned em35_room; unsigned em35_nomove_logged[2]; }
static void em35_diag_poll(){
    ++re4dc_em35_diag_polls;
    const unsigned room=pG?unsigned(pG->room_id):0u;
    if(room!=em35_room){em35_room=room;for(auto& d:re4dc_em35_diag)d.live=0;em35_nomove_logged[0]=em35_nomove_logged[1]=0;}
    for(unsigned t=0;t<2;++t){
        auto& d=re4dc_em35_diag[t];
        if(!d.live)continue;
        const unsigned idle=re4dc_em35_diag_polls-d.last_poll;
        if(idle<=1){em35_nomove_logged[t]=0;continue;}
        if(idle==60 && em35_nomove_logged[t]<4 && d.hp>0){
            ++em35_nomove_logged[t];
            re4dc_log("EM35 NOMOVE ty=%u idle=%u r=%08x mot=%02x fr=%d hp=%d stop=%08x life=%d\n",t,idle,d.r,d.mot,d.frame10,
                      d.hp,unsigned(pG->Stop_flg),int(s16(pG->pl_life)));
        }
    }
}
#endif
extern "C" int re4dc_room_cycle_poll(){
    unsigned generation,cells,bytes,stale,refused;
#if defined(RE4DC_EM35_DIAG) && RE4DC_EM35_DIAG
    em35_diag_poll();
#endif
    if(!re4dc_room4_state(&generation,&cells,&bytes,&stale,&refused))return 0;
#if RE4DC_W11_FIXTURE
    re4dc_w11_room_poll(generation);                    // death / life fixture (sscrn_bridge.cpp)
#endif
    ++room_frames;
#if defined(RE4DC_KOS_CACHE_P2_DIAG) && RE4DC_KOS_CACHE_P2_DIAG
    if(room_frames%150==0)re4dc_cache_p2_diag_poll(unsigned(pG?pG->room_id:0xffff),room_frames);
#endif
#if defined(RE4DC_DISC_READ_METER) && RE4DC_DISC_READ_METER
    if(room_frames==1)re4dc_disc_meter_room(2,unsigned(pG->room_id)); if(room_frames==1)RE4DC_DOORPH_END(unsigned(pG->room_id));   // first gameMainLoop frame: the load ends
#endif
#if defined(RE4DC_KOS_CENSUS) && RE4DC_KOS_CENSUS>=2
    if(room_frames==1 || room_frames%150==0){  // KOS_CENSUS=2 (diagnostic): peak census per window, thread stacks
        re4dc_kos_census_window(unsigned(pG?pG->room_id:0),room_frames);
        re4dc_kos_threads_report();
    }
#endif
#if defined(RE4DC_KOS_TRACE) && RE4DC_KOS_TRACE
    if(room_frames%RE4DC_KOS_TRACE==0){  // KOS_TRACE (crowd.mk, diagnostic): KOS malloc headroom through the room
        unsigned kf=0,ku=0,kb=0;re4dc_kos_heap_state(&kf,&ku,&kb);
        re4dc_log("kos trace: room=%03x frame=%u tick=%u kos_free=%u kos_break=%u sum=%u\n",unsigned(pG?pG->room_id:0),
            room_frames,unsigned(pG?pG->Frame_cnt:0),kf,kb,kf+kb);
    }
#endif
#if RE4DC_DBG_WARP
    re4dc_warp_poll();                                  // test warp rig: placement log, area dump
#endif
#if RE4DC_VMU_DEBUG_SLOT
    re4dc_dbgslot_poll(generation, room_frames);        // L+START debug save (dbgslot_bridge.cpp)
#endif
#if RE4DC_IO_PROBE
    io_cycle_frame(room_frames);
#endif
    if(!cycle.loaded)load_cycle();
    if(!cycle.mode || !pPL || (pG->Status_flg[1]&0x10000000))return 0;
    if(room_frames<cycle.frames)return 0;
    if(!steady_logged){steady_logged=true;audit(1);}
    if(cycle.done>=cycle.count)return 0;
    if(!cycle.anchored){
        // Every round trip re-enters where the first one left.
        cycle.anchored=true;cycle.pos=pPL->pos;cycle.y=pPL->ang.y;cycle.point=pG->Part;
    }
    ++cycle.done;
#if RE4DC_IO_PROBE
    io_cycle_begin(cycle.done,kCycleMode[cycle.mode-1]);
#endif
    if(cycle.mode==3){
        re4dc_log("room cycle: reload %u/%u room=%03x via GameContinue\n",cycle.done,cycle.count,unsigned(pG->room_id));
        GameContinue(1);
        return 1;
    }
    re4dc_log("room cycle: %s %u/%u room=%03x at (%d,%d,%d)\n",kCycleMode[cycle.mode-1],cycle.done,cycle.count,
        unsigned(pG->room_id),int(cycle.pos.x),int(cycle.pos.y),int(cycle.pos.z));
    pG->room_id_prev=pG->room_id;pG->Part_old=pG->Part;
    pG->next_room=pG->room_id;pG->next_point=cycle.point;
    pG->NextPos=cycle.pos;pG->NextY=cycle.y;
    if(cycle.mode==2)RoomData.m_RelNo=0;
    SceSys.m_door_fade_eff=2;
    pG->Rno0=4;pG->Rno1=0;pG->Rno2=0;pG->Rno3=0;
    return 1;
}

#include "native_model.h"
#include "re4dc_platform.h"
namespace {
void* preparation_owner=nullptr;
void* retained_preparation=nullptr;
bool preparation_attempted=false;
#if RE4DC_MOVIE_HEAP_EVICT && RE4DC_D349_RENDERER_STACK
// The cache is lent to a route movie's staging (re4dc_model_release_retained) until the movie retires
// (re4dc_model_return_retained). While lent no draw may take it back or latch preparation_attempted.
bool preparation_lent=false;
unsigned lent_requests=0;
#endif
constexpr unsigned kRetainedBytes=131072;
// D360 frees147232 bytes without shrinking game capacity. Charge the complete
// new cell (payload + OS header + MAD tag), and leave >=80KiB for source use.
constexpr unsigned kSourceReserve=81920,kAllocationOverhead=64;
}

// ---------------------------------------------------------------- room heap-4 cells
#include <cstdint>
// Native owners that borrow the source room heap (heap 4). The source rebuilds
// heap 4 wholesale at every room change, and on a stage reload or room-REL
// relink StageSet recreates heaps 2/3 over the live heap 4 range first
// (MemReplaceHeap(1,2)/(2,3)) before gameRoomMemInit replaces heap 4. Native
// room owners therefore retire at StageSet entry, while heap 4 is intact (the
// room lifecycle above), and every native heap-4 cell carries the heap-4
// generation it came from: a free after the rebuild is dropped (the cell went
// with the old heap) instead of being threaded into whatever heap now covers
// that address. Frees name heap 4's handle; Mem_free_h frees to the OS
// current heap, which is heap 3 while StageSet links the next room's REL.
extern "C" void OSFreeToHeap(int,void*);
namespace {
struct alignas(32) Room4Cell { unsigned magic,generation,bytes,reserved[5]; };
static_assert(sizeof(Room4Cell)==32);
constexpr unsigned kRoom4Magic=0x57364834; // "W6H4"
struct Room4 {
    bool live;                     // a room heap 4 exists and native owners may use it
    unsigned generation;           // heap-4 rebuilds seen (gameRoomMemInit)
    unsigned live_cells,live_bytes,stale_frees,refused;
};
Room4 room4{};
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
// Never recycle a token, even across heap rebuilds. Exhaustion refuses reuse,
// while unrelated room allocations and gameplay continue with token zero.
unsigned room4_incarnation=0;
unsigned room4_next_incarnation(){
    return room4_incarnation==~0U?0U:++room4_incarnation;
}
#endif
#if defined(RE4DC_GC_CENSUS_TRIM) && RE4DC_GC_CENSUS_TRIM
}
// GC_CENSUS_TRIM (lane t2exact): sourceActorIdentity (trans.cpp, ~110-170 calls a frame) reads the two words it uses
// from re4dc_room4_state() directly.
extern "C" const bool* const re4dc_room4_live_ptr=&room4.live;
extern "C" const unsigned* const re4dc_room4_generation_ptr=&room4.generation;
namespace {
#endif

void* room_alloc4(unsigned bytes,const char* tag,bool clear){
    if(!room4.live || !memCheckHeapActive(4)){
        ++room4.refused;
        re4dc_log("room lifecycle: refused %s bytes=%u outside a live room heap\n",tag,bytes);
        return nullptr;
    }
    auto* cell=static_cast<Room4Cell*>(clear?mem_calloc(bytes+sizeof(Room4Cell),tag,0,0,4)
                                           :mem_alloc(bytes+sizeof(Room4Cell),tag,0,0,4));
    if(!cell)return nullptr;
    *cell={kRoom4Magic,room4.generation,bytes,{}};
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
    cell->reserved[0]=room4_next_incarnation();
#endif
    ++room4.live_cells;room4.live_bytes+=bytes;
    return cell+1;
}
void room_free4(void* p,const char* who){
    if(!p)return;
    auto* cell=static_cast<Room4Cell*>(p)-1;
    const auto address=reinterpret_cast<std::uintptr_t>(cell);
    if(cell->magic!=kRoom4Magic || cell->generation!=room4.generation || !memCheckHeapActive(4) ||
#if defined(RE4DC_RESET_HEAP_FIX) && RE4DC_RESET_HEAP_FIX
       // A soft reset (Game Reset, the game over quit) destroys heap 4 without a gameRoomMemInit: handle -1, and
       // OSFreeToHeap(-1) wrote before the heap table (issue #26: load a save, reset, New Game, console crash).
       Heap[4].handle<0 ||
#endif
       address<Heap[4].start || address>=Heap[4].end){
        ++room4.stale_frees;
        re4dc_log("room lifecycle: %s dropped stale heap-4 cell %p\n",who,p);
        return;
    }
    cell->magic=0;--room4.live_cells;room4.live_bytes-=cell->bytes;
    OSFreeToHeap(Heap[4].handle,cell);
}
#if RE4DC_NATIVE_STATIC && RE4DC_NATIVE_PKG_HIGH
// NATIVE_PKG_HIGH: room_alloc4 from the top of the highest free heap-4 cell that fits. The cell is
// laid out as mem_alloc's (32-byte header, payload, 32-byte MAD tag for the heap-4 census) and
// joins the allocated list as OSAllocFromHeap's does, so room_free4 / OSFreeToHeap return it.
void* room_alloc4_high(unsigned bytes,const char* tag){
    if(!room4.live || !memCheckHeapActive(4)){
        ++room4.refused;
        re4dc_log("room lifecycle: refused %s bytes=%u outside a live room heap\n",tag,bytes);
        return nullptr;
    }
    // SystemMemInit hands the aligned arena start to OSInitAlloc, which puts the descriptors there.
    auto* d=reinterpret_cast<OSHeapDescriptor*>((u32(re4dc_mem.heap)+0x1FU)&~0x1FU)+Heap[4].handle;
    const u32 payload=(bytes+sizeof(Room4Cell)+0x1FU)&~0x1FU;
    const s32 size=s32(payload+0x40U);
#if defined(RE4DC_MOTION_CAPACITY) && RE4DC_MOTION_CAPACITY
    // Paired with OSAlloc.c's list mutation guards. No I/O or allocation inside.
    const int motion_capacity_irq=OSDisableInterrupts();
#endif
    OSHeapCell* best=nullptr;
    for(OSHeapCell* c=d->free;c;c=c->next)if(c->size>=size)best=c;  // address order: the last fit is highest
    if(!best) {
#if defined(RE4DC_MOTION_CAPACITY) && RE4DC_MOTION_CAPACITY
        OSRestoreInterrupts(motion_capacity_irq);
#endif
        return nullptr;
    }
    OSHeapCell* cell;
    if(best->size-size<0x40){
        if(best->prev)best->prev->next=best->next;else d->free=best->next;
        if(best->next)best->next->prev=best->prev;
        cell=best;
    }else{
        best->size-=size;
        cell=reinterpret_cast<OSHeapCell*>(reinterpret_cast<u8*>(best)+best->size);
        cell->size=size;
    }
    cell->prev=nullptr;cell->next=d->allocated;
    if(cell->next)cell->next->prev=cell;
    d->allocated=cell;
#if defined(RE4DC_MOTION_CAPACITY) && RE4DC_MOTION_CAPACITY
    OSRestoreInterrupts(motion_capacity_irq);
#endif
    auto* p=reinterpret_cast<u8*>(cell)+0x20;
    u8* t=p+payload;
    t[0]=0;t[1]='M';t[2]='A';t[3]='D';
    snprintf(reinterpret_cast<char*>(t)+4,0x1C,"%s(0)",tag);
    auto* rc=reinterpret_cast<Room4Cell*>(p);
    *rc={kRoom4Magic,room4.generation,bytes,{}};
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
    rc->reserved[0]=room4_next_incarnation();
#endif
    ++room4.live_cells;room4.live_bytes+=bytes;
    return rc+1;
}
#endif
}
#if RE4DC_MOVIE_WORLD_ARENA || (defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05)
extern "C" int re4dc_room4_live_generation(unsigned* generation){
    *generation=room4.generation;
    return room4.live && memCheckHeapActive(4) && Heap[4].handle>=0;
}
extern "C" int re4dc_room4_cell_valid(const void* p,unsigned bytes,unsigned generation){
    // Check epoch, handle and address range before reading the Room4 header.
    // In particular a stale pointer may already refer to inaccessible memory.
    if(!p || !room4.live || generation!=room4.generation || !memCheckHeapActive(4) || Heap[4].handle<0)return 0;
    const auto a=reinterpret_cast<std::uintptr_t>(p),lo=std::uintptr_t(Heap[4].start),hi=std::uintptr_t(Heap[4].end);
    if(a<lo || a-lo<sizeof(Room4Cell) || a>=hi || (a&31u) || bytes>hi-a)return 0;
    const auto* c=static_cast<const Room4Cell*>(p)-1;
    return c->magic==kRoom4Magic && c->generation==generation && c->bytes<=hi-a && (!bytes || c->bytes==bytes);
}
#endif
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
extern "C" unsigned re4dc_room4_cell_incarnation(const void* p,unsigned bytes,unsigned generation){
    if(!re4dc_room4_cell_valid(p,bytes,generation))return 0;
    return (static_cast<const Room4Cell*>(p)-1)->reserved[0];
}
#endif
// gameRoomMemInit rebuilt heap 4: a new generation of native cells may start.
extern "C" void re4dc_room4_open(){++room4.generation;room4.live_cells=0;room4.live_bytes=0;room4.live=true;}
// StageSet entry, after the native owners retired: no new cells until the rebuild.
extern "C" void re4dc_room4_close(){room4.live=false;}
extern "C" int re4dc_room4_state(unsigned* generation,unsigned* cells,unsigned* bytes,unsigned* stale,unsigned* refused){
    *generation=room4.generation;*cells=room4.live_cells;*bytes=room4.live_bytes;
    *stale=room4.stale_frees;*refused=room4.refused;return room4.live;
}

extern "C" void re4dc_model_preparation_owner(void* owner){
#if RE4DC_D349_RENDERER_STACK
    if(preparation_owner==owner)return;
    re4dc_model_detach_retained_storage();
    if(retained_preparation)room_free4(retained_preparation,"native model preparation");
    retained_preparation=nullptr;preparation_owner=owner;preparation_attempted=false;
#endif
}
#if RE4DC_NATIVE_STATIC
// D367 diagnostic: what occupies the room heap when the room first draws.
// OSAlloc cells tile the heap; a mem_alloc block ends with "\0MAD" + file(line).
static void heap4_census(){
    struct Row { const char* tag; unsigned bytes, count; } rows[40];
    unsigned n=0,other=0,other_cells=0,total=0;
    unsigned a=(Heap[4].start+31U)&~31U;const unsigned end=Heap[4].end;
    while(a+0x20U<=end){
        const int size=reinterpret_cast<const OSHeapCell*>(a)->size;
        if(size<0x20 || (size&31) || a+unsigned(size)>end){re4dc_log("heap4 census: stop at %08x size=%d\n",a,size);break;}
        const auto* t=reinterpret_cast<const unsigned char*>(a+unsigned(size)-0x20U);
        if(size>=0x40 && !t[0] && t[1]=='M' && t[2]=='A' && t[3]=='D'){
            const char* tag=reinterpret_cast<const char*>(t+4);unsigned r=0;
            while(r<n && strcmp(rows[r].tag,tag))++r;
            if(r==n && n<40)rows[n++]={tag,0,0};
            if(r<n){rows[r].bytes+=unsigned(size);++rows[r].count;}else{other+=unsigned(size);++other_cells;}
        }else{other+=unsigned(size);++other_cells;}
        total+=unsigned(size);a+=unsigned(size);
    }
    for(unsigned i=0;i<n;++i)for(unsigned j=i+1;j<n;++j)if(rows[j].bytes>rows[i].bytes){Row x=rows[i];rows[i]=rows[j];rows[j]=x;}
    re4dc_log("heap4 census: span=%u walked=%u free=%d untagged_or_free=%u cells=%u tags=%u\n",
        end-Heap[4].start,total,OSCheckHeap(Heap[4].handle),other,other_cells,n);
    for(unsigned i=0;i<n;++i)re4dc_log("heap4 census: %7u B x%-3u %s\n",rows[i].bytes,rows[i].count,rows[i].tag);
}
#endif
#if RE4DC_MOVIE_HEAP_EVICT
// MOVIE_HEAP_EVICT diagnostic (platform/native_movie.cpp, a staging allocation that still fails): heap 4's free
// cells of 4 KB or more in address order, with the tagged cells on either side ("-" = untagged or free).
namespace {
const char* heap4_tag(unsigned a,int size){
    if(size<0x40)return "-";
    const auto* t=reinterpret_cast<const unsigned char*>(a+unsigned(size)-0x20U);
    return !t[0] && t[1]=='M' && t[2]=='A' && t[3]=='D'?reinterpret_cast<const char*>(t+4):"-";
}
}
extern "C" void re4dc_heap4_free_map(){
    if(!memCheckHeapActive(4))return;
    const auto* d=reinterpret_cast<const OSHeapDescriptor*>((u32(re4dc_mem.heap)+0x1FU)&~0x1FU)+Heap[4].handle;
    const OSHeapCell* f=d->free;
    unsigned a=(Heap[4].start+31U)&~31U,prev=0,logged=0;int prev_size=0;
    const unsigned end=Heap[4].end;
    while(a+0x20U<=end && logged<24){
        const int size=reinterpret_cast<const OSHeapCell*>(a)->size;
        if(size<0x20 || (size&31) || a+unsigned(size)>end)break;
        while(f && unsigned(f)<a)f=f->next;
        if(f && unsigned(f)==a && size>=4096){
            const unsigned next=a+unsigned(size);
            const int next_size=next+0x20U<=end?reinterpret_cast<const OSHeapCell*>(next)->size:0;
            re4dc_log("heap4 free map: %08x %u between %s %d and %s %d\n",a,unsigned(size),
                prev?heap4_tag(prev,prev_size):"start",prev_size,next_size>0?heap4_tag(next,next_size):"end",next_size);
            ++logged;
        }
        prev=a;prev_size=size;a+=unsigned(size);
    }
}
#endif
extern "C" void* re4dc_model_retained_storage(unsigned* bytes){
    *bytes=0;
#if RE4DC_D349_RENDERER_STACK
#if RE4DC_MOVIE_HEAP_EVICT
    if(preparation_lent){++lent_requests;return nullptr;}   // the movie holds it; no attempt is latched
#endif
    if(!preparation_owner || MemGetCurrentHeap()!=4 || !memCheckHeapActive(4))return nullptr;
#if defined(RE4DC_MODEL_PREP_SKIP_R11E) && RE4DC_MODEL_PREP_SKIP_R11E
    // MODEL_PREP_SKIP_R11E (game30.mk): r11e (El Gigante) keeps its 128 KB of heap 4 for the PS2 pickup pack; models
    // prepare without the retained cache there (acquire_batch tolerates a null cache).
    if(pG && ((unsigned(pG->stage_no)<<8)|pG->room_no)==0x11eU)return nullptr;
#endif
    if(!preparation_attempted){
        preparation_attempted=true;
#if RE4DC_NATIVE_STATIC
        heap4_census();
#endif
        const int before=OSCheckHeap(Heap[4].handle);
        if(before>=int(kRetainedBytes+kAllocationOverhead+sizeof(Room4Cell)+kSourceReserve))
            retained_preparation=room_alloc4(kRetainedBytes,"native model preparation",true);
        re4dc_log("native model preparation: bytes=%u source_free=%d->%d owner=%p reserve=%u\n",
            retained_preparation?kRetainedBytes:0,before,OSCheckHeap(Heap[4].handle),preparation_owner,kSourceReserve);
    }
    if(retained_preparation)*bytes=kRetainedBytes;
    return retained_preparation;
#else
    return nullptr;
#endif
}
#if RE4DC_MOVIE_HEAP_EVICT && RE4DC_D349_RENDERER_STACK
// MOVIE_HEAP_EVICT (platform/native_movie.cpp): a route movie owns the frame, so the model preparation cache (rebuilt
// every frame) is lent to its staging. r100 s30 after the ambush (route-hm1): the decoder's second 55,296 B plane
// found 197 KB free in holes of at most 40,736 B, that one next to this 131,168 B cell. Ownership (architect review
// 2026-10-03): the loan is explicit state here. While lent, re4dc_model_retained_storage returns null without latching
// preparation_attempted (a stepped movie's game frames keep drawing models); the movie's retirement
// (re4dc_model_return_retained, after its staging is freed) clears the loan, re-arms the attempt and allocates.
extern "C" unsigned re4dc_model_release_retained(){
    if(!retained_preparation || preparation_lent)return 0;
    re4dc_model_detach_retained_storage();
    room_free4(retained_preparation,"native model preparation");
    retained_preparation=nullptr;preparation_attempted=false;preparation_lent=true;lent_requests=0;
    return kRetainedBytes;
}
// The movie retired: 0 when nothing was lent; else 1 with *bytes = the restored capacity. 0 bytes is a failure (no
// room heap now, or heap 4 short): the attempt stays armed, so the next model draw tries once more. *requests = model
// draws that asked for the cache during the loan.
extern "C" int re4dc_model_return_retained(unsigned* bytes,unsigned* requests){
    *bytes=0;*requests=0;
    if(!preparation_lent)return 0;
    preparation_lent=false;*requests=lent_requests;lent_requests=0;
    preparation_attempted=false;
    re4dc_model_retained_storage(bytes);
    if(!*bytes)preparation_attempted=false;
    return 1;
}
#endif

// Native static packages share heap 4 and the retained preparation's reserve
// policy: never below 80 KiB left for the source. Opened at the first bind of
// their owner, which precedes the lazy retained allocation at first draw.
#if RE4DC_NATIVE_STATIC
#include "native_static.h"
#if (defined(RE4DC_MOTION_COLD_POOL_CASTLE) && RE4DC_MOTION_COLD_POOL_CASTLE) || (defined(RE4DC_BACKFACE_ROOMS) && RE4DC_BACKFACE_ROOMS) || (defined(RE4DC_FX_R200_ENTRY_CAP) && RE4DC_FX_R200_ENTRY_CAP) || (defined(RE4DC_TEX_FINAL_REFUSAL_LOG) && RE4DC_TEX_FINAL_REFUSAL_LOG)
extern "C" unsigned re4dc_room_id_now(){return pG?unsigned(pG->room_id):0u;}   // native_motion.cpp
#endif
extern "C" int re4dc_static_heap_free(){
    return memCheckHeapActive(4)?OSCheckHeap(Heap[4].handle):-1;
}
#if defined(RE4DC_FAR_SHELL) && RE4DC_FAR_SHELL
extern "C" int re4dc_far_shell_shortfall(unsigned need,const char* site);   // platform/far_shell.inc
// FAR_SHELL: a package refused for the reserve, or not placed, first takes the far shell's heap-4 block back.
extern "C" void* re4dc_static_alloc(unsigned bytes){
    int before=re4dc_static_heap_free();
    const int need=int(bytes+kAllocationOverhead+sizeof(Room4Cell)+kSourceReserve);
    if(before<need && re4dc_far_shell_shortfall(bytes,"native static package"))before=re4dc_static_heap_free();
    if(before<need){
        re4dc_log("native static: reject bytes=%u heap4_free=%d reserve=%u\n",bytes,before,kSourceReserve);
        return nullptr;
    }
#if RE4DC_NATIVE_PKG_HIGH
    void* p=room_alloc4_high(bytes,"native static package");
    if(!p && re4dc_far_shell_shortfall(bytes,"native static package"))p=room_alloc4_high(bytes,"native static package");
#else
    void* p=room_alloc4(bytes,"native static package",false);
    if(!p && re4dc_far_shell_shortfall(bytes,"native static package"))p=room_alloc4(bytes,"native static package",false);
#endif
    return p;
}
#else
extern "C" void* re4dc_static_alloc(unsigned bytes){
    const int before=re4dc_static_heap_free();
    if(before<int(bytes+kAllocationOverhead+sizeof(Room4Cell)+kSourceReserve)){
        re4dc_log("native static: reject bytes=%u heap4_free=%d reserve=%u\n",bytes,before,kSourceReserve);
        return nullptr;
    }
#if RE4DC_NATIVE_PKG_HIGH
    return room_alloc4_high(bytes,"native static package");
#else
    return room_alloc4(bytes,"native static package",false);
#endif
}
#endif
extern "C" void re4dc_static_free(void* data){room_free4(data,"native static package");}
#if defined(RE4DC_WORLD_PORTAL29) && RE4DC_WORLD_PORTAL29
// A missing/stale/invalid optional cell must leave all existing backing intact.
extern "C" void* re4dc_world_portal29_alloc(unsigned bytes){
    constexpr unsigned floor=96U*1024U;
    if(bytes>512U*1024U+8192U)return nullptr;
    const int before=re4dc_static_heap_free();
    if(before<0 || unsigned(before)<bytes+kAllocationOverhead+sizeof(Room4Cell)+floor)return nullptr;
#if RE4DC_NATIVE_PKG_HIGH
    void* p=room_alloc4_high(bytes,"world portal29");
    if(p && re4dc_static_heap_free()<int(floor)){room_free4(p,"world portal29");return nullptr;}
    return p;
#else
    return nullptr;
#endif
}
#endif
#if defined(RE4DC_WORLD_PART_PLAN29) && RE4DC_WORLD_PART_PLAN29
// An optional setup cache must never evict a far shell to find a contiguous
// block. Use the same room-cell lifetime with a side-effect-free refusal.
extern "C" void* re4dc_world_part_plan29_alloc(unsigned bytes){
    constexpr unsigned floor=96U*1024U;
    if(bytes>64U*1024U+31U)return nullptr;
    const int before=re4dc_static_heap_free();
    if(before<0 || unsigned(before)<bytes+kAllocationOverhead+sizeof(Room4Cell)+floor)return nullptr;
#if RE4DC_NATIVE_PKG_HIGH
    void* p=room_alloc4_high(bytes,"world part plan29");
    if(p && re4dc_static_heap_free()<int(floor)){room_free4(p,"world part plan29");return nullptr;}
    return p;
#else
    return nullptr; // mem_alloc's low allocator can evict shell/motion backing.
#endif
}
#endif
#endif


#if RE4DC_PAD_PROMPT_MANUAL_ART
#include "manual_pages_bridge.inc"
#endif
