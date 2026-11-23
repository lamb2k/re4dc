// E2 fight slice (lane eng-e2): engine forms and explicit stubs of what the hosted Ganados and room script reach
// beyond the E1 shell (the boss slice's forms, engine/boss/boss_stubs*.cpp, carried here because that folder is not
// built in this image). As in host/e1_stubs.cpp, every stub that could change the hosted behaviour logs its first
// calls and counts every call (e1_stub_hit); the report lists them.
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
#include "item.h"
#include "mes.h"
#include "id_sys.h"
#include "sscrn.h"
#include "examine.h"
#include "dvd.h"
#include "main_sub.h"
#include "foot_shadow.h"
#include "obj00.h"
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
// managers of the HUD, messages and items the hosted room script and Ganados name (not hosted: zeroed records)
STORAGE(MessageControl, cMes)
STORAGE(IDSystem, IdSys)
STORAGE(SubScreenWork, SubScreenWk)
STORAGE(ItemExamine, itemExam)
u8 use_filter0a, filter0a_mask_flag, filter0a_mask_id, filter0a_mask_alpha;
STORAGE(cDvd, Dvd)
STORAGE(ScreenInfo, Screen)
FootShadowTbl Em10_fs_tbl;   // the Ganado's foot shadow table (drawing reads it; no foot shadows drawn in this slice)

// ---- scroll objects (room model pieces): engine records whose be_flag bit 1 is the show / hide state ----
#define E2_SMD 256
static __attribute__((aligned(32))) unsigned char smd_obj[E2_SMD][sizeof(cObj)];
static __attribute__((aligned(32))) unsigned char smd_work[E2_SMD][sizeof(SmdWork)];
unsigned e2_smd_hidden[8];
cObj* SmdGetObjPtr(u32 id)
{
    if (id >= E2_SMD) return 0;
    cObj* o = (cObj*) smd_obj[id];
    static bool made[E2_SMD];
    if (!made[id]) { made[id] = true; new (o) cObj(); o->be_flag |= 0x23; }
    return o;
}
SmdWork* SmdGetWorkPtr(int id) { return id >= 0 && id < E2_SMD ? (SmdWork*) smd_work[id] : 0; }
void SmdSetTrans(u32 id, int on)
{
    cObj* o = SmdGetObjPtr(id);
    if (!o) return;
    if (on == 1) { o->be_flag |= 2; e2_smd_hidden[id >> 5] &= ~(1u << (id & 31)); }
    else { o->be_flag &= ~2; e2_smd_hidden[id >> 5] |= 1u << (id & 31); }
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

// ---- quake, tool state, data controller, sound streams, debug ----
void QuakeExec(u8 id, u16, s16, f32, u8) { e1_stub_hit("QuakeExec", id); }
u8 EffGetToolState() { return 0; }
void EffSetToolStateCallBack(int, void (*)(), void (*)()) {}
void cDataCtrl::setAramSort(int) {}
void SndRoomStrStop(int) { STUB("SndRoomStrStop"); }

// ---- the armed weapon's magazine (item.cpp trigger / reload for the handgun): the fixture's "inv default" (10 rounds
// loaded) and its "ammo" rule (the warp refills the magazine to 9 when fewer than 3 are left, every frame) ----
static int mag = 10;
int cItemMgr::bulletNumTotal(int) { return mag + 50; }
u16 cItemMgr::bulletNum() { return (u16) mag; }
u32 cItemMgr::bulletNumCurrent() { return (u32) mag; }
int cItemMgr::trigger() { if (mag <= 0) return 0; mag--; if (mag < 3) mag = 9; return 1; }
int cItemMgr::reloadable() { return 0; }
int cItemMgr::reload() { STUB("cItemMgr::reload"); return 0; }
int cItemMgr::num(int) { STUB("cItemMgr::num"); return 0; }

// ---- GX projection queries (the screen tests some AI makes: GetScreenPos, em10ScreenInCk) ----
// Lane eng-e2d: the game's screen (main_sub.cpp: the viewport is Screen, 512 x 448) and the camera record's projection
// terms (services/camera/eng_camera.h: the camera service's perspective, x scale cot / (4/3) and y scale cot, as the
// original's C_MTXPerspective of pG->Cam.ProjMat). Before, a 640 x 480 view and a 640 / 448 aspect, against which the
// screen rules' 512 x 448 bounds tested other points than the original's. The PC reference's native build answers the
// same record (hostref/host_math.cpp), where e2bcheck compares the screen check with the original's.
extern "C" {
void GXGetViewportv(f32* vp) { vp[0] = 0; vp[1] = 0; vp[2] = 512; vp[3] = 448; vp[4] = 0; vp[5] = 1; }
void GXGetProjectionv(f32* p)
{
    const EngCamera& r = eng_cam;
    p[0] = r.proj_type; p[1] = r.p00; p[2] = r.p02; p[3] = r.p11; p[4] = r.p12; p[5] = r.p22; p[6] = r.p23;
}
unsigned e2_gx_projections;   // lane eng-e2f: the screen tests' projections (fight_trace.cpp prints the count)
void GXProject(f32 x, f32 y, f32 z, const f32 mtx[3][4], const f32* pm, const f32* vp, f32* sx, f32* sy, f32* sz)
{
    e2_gx_projections++;
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

// ---- the room script's prop object 0 (r101: obj00 at the square, kept unsuspended): an engine stand-in record, so
// the script's calls on it land on a real cObj (no behaviour is hosted for it; it is not drawn) ----
cObj* SetObj00(void*, void*, Vec* pos, Vec* rot)
{
    static __attribute__((aligned(32))) unsigned char rec[sizeof(cObj)];
    cObj* o = new (rec) cObj();
    if (pos) o->pos = *pos;
    if (rot) o->ang = *rot;
    e1_stub_hit("SetObj00 (stand-in record)", 0);
    return o;
}

// ---- event data units (datactrl.cpp cDataCtrl::setData): the engine plays no event data in this slice, so each request
// gets an empty unit (size 0, never loaded): the room script's size checks read 0 and its waits report "not loaded" ----
cDataUnit* cDataCtrl::setData(char* name)
{
    static __attribute__((aligned(32))) cDataUnit units[8];
    static unsigned n;
    cDataUnit* u = &units[n++ & 7];
    memset((void*) u, 0, sizeof(*u));
    e1_log("E2 event data %s: not loaded (engine plays no event data)\n", name ? name : "(null)");
    return u;
}
