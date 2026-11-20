// Explicit stubs of the E1 image (lane eng-e1). Each one stands for code E1 does not host: other behaviour (enemies,
// items, the partner, events, damage), effects, sound, lights, cloth, HUD text and debug drawing. Every stub that could
// change what the hosted behaviour does logs its first calls and counts every call (e1_stub_hit; the report lists the
// counts). Debug-only drawing returns at once (no consequence). Return values are those of the reference situation
// (village square after the bell: no enemies, no water, no partner, a loaded handgun).
#include "types.h"
#include "vec.h"
#include "global.h"
#include "model.h"
#include "em.h"
#include "obj.h"
#include "player.h"
#include "pl_npc.h"
#include "pl_wep.h"
#include "act_btn.h"
#include "emwindow.h"
#include "item.h"
#include "dmg.h"
#include "db_cam.h"
#include "light.h"
#include "est.h"
#include "esp.h"
#include "em_sub.h"
#include "quake.h"
#include "snd.h"
#include "eprintf.h"
#include "dbmodule.h"
#include "pendulum.h"
#include "sce_sys.h"
#include "scheduler.h"
#include "game.h"
#include "emdoor.h"
#include "sce_at.h"
#include "view.h"
#include "main.h"
#include "e1_engine.h"
#include <string.h>

#define STUB(name) e1_stub_hit(name, 0)

// ---- objects of unhosted managers: zeroed storage under the original symbol (no constructor runs) ----
#define STORAGE(type, sym) __attribute__((aligned(32))) unsigned char e1_##sym[sizeof(type)] asm("_" #sym);
STORAGE(cActionButton, ActBtn)
#ifndef E2_BOSS   // eng-boss: hosted or engine-served in the boss image
STORAGE(cDmgMgr, DmgMgr)
#endif
STORAGE(cItemMgr, ItemMgr)
STORAGE(cLightMgr, LightMgr)
STORAGE(debugCamera, CamDbg)
STORAGE(QuakeWork, Quake)

// ---- main-loop globals defined by unhosted units ----
f32 ZNEAR, ZFAR, ORTHO_T, ORTHO_B, ORTHO_L, ORTHO_R;
const Vec vecZero = {0.0f, 0.0f, 0.0f};
#ifndef E2_BOSS   // eng-boss: game.cpp (hosted in the boss image) defines them
u32 g_at2_cnt[20], g_at2_cyc[20], g_at2_total, g_at2_total_cyc;
#endif
u8 pl_fs_tbl[0x40];   // foot shadow table (drawing reads it; E1 draws no foot shadows)
extern "C" void re4dc_halt(const char* file, int line)
{
    e1_log("E1 HALT %s(%d) tick %lu\n", file, line, (unsigned long) e1_tick);
    for (;;) {}
}
extern "C" void re4dc_sincosf(float x, float* s, float* c);
extern "C" float sinf(float);
extern "C" float cosf(float);
// mtx.c GAME_SINCOS form: sinf and cosf of one argument, the fdlibm kernels the reference runs (bit-identical).
extern "C" void re4dc_sincosf(float x, float* s, float* c)
{
    *s = sinf(x);
    *c = cosf(x);
}
// PowerPC performance-monitor registers (debug timing only)
extern "C" {
u32 PPCMfpmc1() { return 0; }
void PPCMtmmcr0(u32) {}
void PPCMtmmcr1(u32) {}
void PPCMtpmc1(u32) {}
void PPCMtpmc2(u32) {}
void PPCMtpmc3(u32) {}
void PPCMtpmc4(u32) {}
}

// ---- action button, damage, items, windows, racks (other behaviour) ----
void cActionButton::set(int, int, int, int, int, int, int, int) { STUB("cActionButton::set"); }
#ifndef E2_BOSS   // eng-boss: hosted or engine-served in the boss image
int cDmgMgr::hitCheck(Vec*, Vec*) { STUB("cDmgMgr::hitCheck"); return 0; }
#endif
#ifndef E2_BOSS   // eng-boss: the boss image keeps a magazine (boss/boss_stubs2.cpp)
u16 cItemMgr::bulletNum() { return 10; }            // new-game handgun magazine (the route never fires)
u32 cItemMgr::bulletNumCurrent() { return 10; }
int cItemMgr::reloadable() { STUB("cItemMgr::reloadable"); return 0; }
#endif
int cEmWindow::ChkBreakDir(Vec*) { STUB("cEmWindow::ChkBreakDir"); return 0; }
int cEmWindow::ChkStatus() { STUB("cEmWindow::ChkStatus"); return 0; }
int cEmWindow::ExeWindowEvent() { STUB("cEmWindow::ExeWindowEvent"); return 0; }
int ChkWindow(cModel*, Vec*, Vec*, int, u16*, Vec*, Vec*, cEmWindow**) { STUB("ChkWindow"); return 0; }
int cEmRack::adjustRange(u8) { STUB("cEmRack::adjustRange"); return 0; }
#ifndef E2_BOSS   // eng-boss: hosted or engine-served in the boss image
int EmRackCk(cEm*, Vec*, f32) { STUB("EmRackCk"); return 0; }
void EmYarareDisp(cEm*) {}
void EmScenario(cEm*) { STUB("EmScenario"); }
int LifeDownSet2(cEm*, int, int, int) { STUB("LifeDownSet2"); return 0; }
u32 GetWepTargetList2(Vec*, Vec*, WepTarget*, u32, Vec*, Vec*, u32*, int, int) { STUB("GetWepTargetList2"); return 0; }
int GetWepTargetListBomb(Vec*, f32, WepTarget*, int, int, int) { STUB("GetWepTargetListBomb"); return 0; }
int GetWepTargetPos(Vec*, Vec*, int, int, cEm**, int*) { STUB("GetWepTargetPos"); return 0; }
void GameAddPoint(int type) { if (type) STUB("GameAddPoint"); }
ScePrim* SceExec(int, TaskFunc, int, u8, int, void*) { STUB("SceExec"); return 0; }
void TaskSleep(int) { STUB("TaskSleep"); }
#endif
// the partner: hosted since lane eng-e1b (pl_npc.cpp, pl11.cpp; game/hosted.mk PARTNER_SRCS); the boss image hosts none
#ifdef E2_BOSS
u32 SubCharGetStatus() { return 0; }
u32 SubCharGetCondition() { return 0; }
void cSubChar::control(int) { STUB("cSubChar::control"); }
void cSubChar::registPlAction(Vec*, f32) { STUB("cSubChar::registPlAction"); }
#endif
// other weapons' objects
void cObjLauncher::grip(int) { STUB("cObjLauncher::grip"); }
void cObjLauncher::gripBack() { STUB("cObjLauncher::gripBack"); }

// doors and ladders the partner checks (lane eng-e1b): E1 hosts none, so the answer is "none"
cEmDoor* DoorOpenCk(cModel*) { STUB("DoorOpenCk"); return 0; }
void SubOpenDoorSet(cEmDoor*) { STUB("SubOpenDoorSet"); }
#ifndef E2_FIGHT   // eng-e2: sce_at.cpp is hosted in the fight image
int SceAtCheckLadder(cModel*, Vec*, f32*, u8*) { STUB("SceAtCheckLadder"); return 0; }
#endif
extern "C" int SubLadderClimbCk(cModel*) { STUB("SubLadderClimbCk"); return 0; }
extern "C" int SubLadderClimbCk2(cModel*) { STUB("SubLadderClimbCk2"); return 0; }

// ---- effects (E1 draws none; the generator draws they would make are reported, see the hand-back) ----
#ifndef E2_BOSS   // eng-boss: hosted or engine-served in the boss image
int EspDataLoad(u32, u32, int) { return 0; }
extern "C" int EspDataRelease(u32, int, int) { return 0; }
void EffectEspDelete(int, int, u32, cModel*) {}
void EffectEspgenDelete(int, int, int) {}
void EffectEfmDelete(int, int, int) {}
#endif
#ifndef E2_FIGHT   // eng-e2: the native effect service (services/effects/fx.cpp) in the fight image
void EspSetWaterHitmark(Vec*) { STUB("EspSetWaterHitmark"); }
void EspSetEatEffect(Vec*, Vec*, int, int) { STUB("EspSetEatEffect"); }
#endif
int ChkWaterEffectEnable(Vec*) { return 0; }
int GetWaterHeight(Vec*, f32*) { return 0; }        // no water in the village square
extern "C" void AddWaterPower(Vec*, f32) { STUB("AddWaterPower"); }
int GetWaterCrossPos(Vec*, Vec*, Vec*) { STUB("GetWaterCrossPos"); return 0; }
void AddSandPower(Vec*, f32) {}
void QuakeInit() {}
void QuakeMove() {}

// ---- sound (E1 plays none; calls are counted) ----
u32 SndCall(u16 blk, u16 no, Vec*, int, int, cUnit*) { e1_stub_hit("SndCall", blk << 16 | no); return 0; }
int SndStop(u32 id, int) { e1_stub_hit("SndStop", id); return 0; }

// ---- lights (E1 draws with the room's baked light set) ----
cLightInfo::cLightInfo() { memset(this, 0, sizeof(*this)); }
int cLightInfo::init2(int type, int partsNo, const Vec* pOffset, const Vec* pSize, int mask)
{
    Flag = type;
    PartsNo = partsNo;
    Offset = *pOffset;
    Size = *pSize;
    EnableMask = mask;
    SelectMask = 0xFFFFFFFF;   // lane eng-e1d: as lightInfo.cpp (the light inputs the renderer now reads per character)
    if ((Flag & 3) == 0) Radius = Size.x + Size.y;
    else if ((Flag & 3) != 2) Radius = Size.x;
    else Radius = __builtin_sqrtf(Size.x * Size.x + Size.y * Size.y + Size.z * Size.z);
    return 1;
}
void cLightInfo::updateMatrix(cModel*) {}
int cLightMgr::update(int, int) { return 0; }
// The partner's own light (pl_npc.cpp cSubChar::init: LightMgr.createBack(0, 2, 0, 0), then setParent(this)), lane
// eng-e1b: an engine light record (zeroed, one per partner) that keeps its parent; E1 draws with the room's baked
// light set, so nothing reads it yet. Both calls are counted.
static unsigned char e1_partner_light[sizeof(cLight)] __attribute__((aligned(32)));
cLight* cLightMgr::createBack(int lit, int cut, int light, int flag)
{
    e1_stub_hit("cLightMgr::createBack", lit << 8 | cut);
    return (cLight*) e1_partner_light;
}
int cLight::setParent(cModel* m)
{
    e1_stub_hit("cLight::setParent", 0);
    ParentType = 1;
    pParent = m;
    return 1;
}


// ---- debug text and drawing (no consequence) ----
void eprintf(int, int, int, int, const char*, ...) {}
void eprintf2(int, int, int, int, int, int, const char*, ...) {}
void Draw_line3d(Vec*, Vec*, u32, int) {}
void Draw_line3d_local(Vec*, Vec*, Mtx, u32, int) {}
void Draw_poly(Vec*, u32, int) {}
void Draw_poly_local(Vec*, Mtx, u32, int) {}
void Draw_sphere(Vec*, f32, u32, int, int) {}
void Draw_cylinder(Vec*, f32, f32, u32) {}
void Draw_pos(Vec*, int) {}
void Draw_local_pos(Vec*, int, Mtx) {}
void debugCamera::move(Camera*, JOY*, int) {}
void CameraDebugInformation() {}
// effect set table: the player's footstep / damage effect sets (E1 draws no effects)
#ifndef E2_BOSS   // eng-boss: hosted or engine-served in the boss image
extern "C" void EstSet(int, int, Vec*, Vec*, int c, int d, int, int, u32, void*) { e1_stub_hit("EstSet", c << 8 | d); }
#endif
int BtoX(int bits) { return bits; }
extern "C" void PADControlMotor(int, u32) {}
// the camera / weapon line test against enemy body boxes (em_sub.cpp): E1 hosts no enemy bodies
#ifndef E2_BOSS   // eng-boss: hosted or engine-served in the boss image
int emLineCubeCrossCk(Vec*, Vec*, Mtx, f32, f32, f32, Vec*, Vec*) { STUB("emLineCubeCrossCk"); return 0; }
#endif
// the weapon object's laser sight and its effect sets (drawing), the shell casing object (obj10), the other handgun
#ifndef E2_FIGHT   // eng-e2: the native effect service in the fight image
int EspEstSetSelect(int, int, int, cEsp** out, int) { STUB("EspEstSetSelect"); if (out) *out = 0; return 0; }
#endif
void EspDrawLaserLine(Vec, Vec, f32) {}
cObj* SetObj10(void*, void*, Vec*, Vec*, Vec*, float, float, int, int) { STUB("SetObj10"); return 0; }
void Obj10SetEst(cObj*, int, int, unsigned long, int, int, int, int, int, int) { STUB("Obj10SetEst"); }
void ObjMauser_init(cObj*) { STUB("ObjMauser_init"); }
#ifndef E2_BOSS
int cItemMgr::reload() { STUB("cItemMgr::reload"); return 0; }
int cItemMgr::trigger() { STUB("cItemMgr::trigger"); return 0; }
#endif
void Draw_cylinderMtx(Mtx, Vec*, f32, f32, u32) {}
// The GameCube's locked-cache scratch the pendulum cloth collision uses (pendulum.cpp): an engine scratch block.
extern "C" { unsigned char re4dc_locked_cache[16384] __attribute__((aligned(32))); }
