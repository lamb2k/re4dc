// E2 boss slice (lane eng-boss): engine forms and explicit stubs of what the hosted boss and room script reach beyond
// the E1 shell. As in host/e1_stubs.cpp, every stub that could change the hosted behaviour logs its first calls and
// counts every call (e1_stub_hit); the report lists them.
//   - scroll (room model) objects: an engine table of stand-in records, one per scroll id, whose be_flag bit 1 is the
//     show / hide state the room script sets (SmdSetTrans): the world-piece visibility the renderer would read;
//   - the room save record (RsfSet / RsfCheck through RoomData.getRoomSavePtr): engine storage;
//   - events, ETC models, sound streams, the cockpit, the data controller, debug text: stubs;
//   - GX projection queries: computed from the camera's projection (the screen tests some AI makes).
#include "global.h"
#include "model.h"
#include "em.h"
#include "obj.h"
#include "scroll.h"
#include "room_data.h"
#include "event.h"
#include "etc_model.h"
#include "cockpit.h"
#include "datactrl.h"
#include "quake.h"
#include "esp.h"
#include "game.h"
#include "sce.h"
#include "snd.h"
#include "e1_engine.h"
#include "e1_core.h"
#include "camera/eng_camera.h"
#include <string.h>
#include <new>
#include <math.h>

#define STUB(name) e1_stub_hit(name, 0)
#define STORAGE(type, sym) __attribute__((aligned(32))) unsigned char e2_##sym[sizeof(type)] asm("_" #sym);
STORAGE(Cockpit, Cckpt)
STORAGE(cDataCtrl, DC)
STORAGE(EventMgr, EvtMgr)

// ---- scroll objects ----
#define E2_SMD 256
static __attribute__((aligned(32))) unsigned char smd_obj[E2_SMD][sizeof(cObj)];
static __attribute__((aligned(32))) unsigned char smd_work[E2_SMD][sizeof(SmdWork)];
static unsigned smd_trans_calls;
unsigned e2_smd_hidden[8];      // bit per scroll id: hidden by the room script (world pieces the renderer drops)
cObj* SmdGetObjPtr(u32 id)
{
    if (id >= E2_SMD) return 0;
    cObj* o = (cObj*) smd_obj[id];
    static bool made[E2_SMD];
    if (!made[id]) { made[id] = true; new (o) cObj(); o->be_flag |= 0x23; }   // first use: a real object record, shown (bit 1)
    return o;
}
SmdWork* SmdGetWorkPtr(int id) { return id >= 0 && id < E2_SMD ? (SmdWork*) smd_work[id] : 0; }
void SmdSetTrans(u32 id, int on)
{
    cObj* o = SmdGetObjPtr(id);
    if (!o) return;
    if (on == 1) { o->be_flag |= 2; e2_smd_hidden[id >> 5] &= ~(1u << (id & 31)); }
    else { o->be_flag &= ~2; e2_smd_hidden[id >> 5] |= 1u << (id & 31); }
    if (smd_trans_calls++ < 64) e1_log("E2 SMD %lu %s tick %lu\n", (unsigned long) id, on == 1 ? "shown" : "hidden", (unsigned long) e1_tick);
}

// ---- the room save record (room_data.cpp; RsfSet / RsfCheck read word 1 on) ----
static __attribute__((aligned(32))) u8 room_save[64];
u8* cRoomData::getRoomSavePtr(u16 room) { (void) room; return room_save; }
STORAGE(cRoomData, RoomData)

// ---- events (the cut scenes are movies on the old port; the engine plays none in this slice) ----
int EventMgr::EvtReadExec(char* name, int em, u32 flags) { e1_log("E2 event %s em %x flags %lx tick %lu (not played)\n", name, em, (unsigned long) flags, (unsigned long) e1_tick); STUB("EvtReadExec"); return 0; }
int EventMgr::EvtReadAram(char*, int, int*, int, u32) { return 0; }
int EventMgr::SetFunc(char*, void*) { return 0; }
int Event::GetMod(void** mod, char*, u8*, int*) { if (mod) *mod = 0; STUB("Event::GetMod"); return 0; }
int Event::SetMod(char*, void*, u8, void*, u8, int*) { STUB("Event::SetMod"); return 0; }
void Event::EspSetModelPtr(cModel*) { STUB("Event::EspSetModelPtr"); }

// ---- ETC models (room torches / props drawn by the ETC system) ----
int setRoomEtcDisp(int no, int on, int flag) { e1_stub_hit("setRoomEtcDisp", no << 8 | on); (void) flag; return 0; }
int getRoomEtcTorch(int no, cEm** out, int flag) { (void) flag; if (out) *out = 0; e1_stub_hit("getRoomEtcTorch", no); return 0; }

// ---- game points, quake, tool state, data controller, sound streams, debug ----
// GameAddPoint / GamePointBossReset: hosted (src/game/game.cpp, the difficulty points and rank)
void QuakeExec(u8 id, u16, s16, f32, u8) { e1_stub_hit("QuakeExec", id); }
u8 EffGetToolState() { return 0; }
void EffSetToolStateCallBack(int, void (*)(), void (*)()) {}
void cDataCtrl::setAramSort(int) {}
void SndRoomStrStop(int) { STUB("SndRoomStrStop"); }
extern "C" void SceSndCallThunder() {}
extern "C" void SceDebugDisp(const char*, ...) {}
int DebugTrg(int) { return 0; }

// ---- GX projection queries (the screen tests some AI makes: em2b's on-screen test, GetScreenPos) ----
// Lane eng-e2g (as eng-e2d did for the fight, fight/fight_stubs.cpp): the game's screen (main_sub.cpp: the viewport is
// Screen, 512 x 448) and the camera record's projection terms (services/camera/eng_camera.h: the camera service's
// perspective, x scale cot / (4/3) and y scale cot, as the original's C_MTXPerspective of pG->Cam.ProjMat). Before, a
// 640 x 480 view and a 640 / 448 aspect, against which the screen rules' 512 x 448 bounds tested other points than the
// original's (the right 18 % of the screen read as off it, a strip past its left edge as on).
extern "C" {
void GXGetViewportv(f32* vp) { vp[0] = 0; vp[1] = 0; vp[2] = 512; vp[3] = 448; vp[4] = 0; vp[5] = 1; }
void GXGetProjectionv(f32* p)
{
    const EngCamera& r = eng_cam;
    p[0] = r.proj_type; p[1] = r.p00; p[2] = r.p02; p[3] = r.p11; p[4] = r.p12; p[5] = r.p22; p[6] = r.p23;
}
// GXProject (SDK formula): model point -> view (mtx) -> clip (projection pm) -> window (viewport vp)
void GXProject(f32 x, f32 y, f32 z, const f32 mtx[3][4], const f32* pm, const f32* vp, f32* sx, f32* sy, f32* sz)
{
    f32 px = mtx[0][0] * x + mtx[0][1] * y + mtx[0][2] * z + mtx[0][3];
    f32 py = mtx[1][0] * x + mtx[1][1] * y + mtx[1][2] * z + mtx[1][3];
    f32 pz = mtx[2][0] * x + mtx[2][1] * y + mtx[2][2] * z + mtx[2][3];
    f32 xc, yc, zc, wc;
    if (pm[0] == 0) { xc = px * pm[1] + pz * pm[2]; yc = py * pm[3] + pz * pm[4]; zc = pz * pm[5] + pm[6]; wc = -pz; }
    else { xc = px * pm[1] + pm[2]; yc = py * pm[3] + pm[4]; zc = pz * pm[5] + pm[6]; wc = 1.0f; }
    if (wc == 0) wc = 1e-6f;
    *sx = vp[0] + vp[2] * 0.5f * (1.0f + xc / wc);
    *sy = vp[1] + vp[3] * 0.5f * (1.0f - yc / wc);
    *sz = vp[5] + (vp[5] - vp[4]) * (zc / wc);
}
}
