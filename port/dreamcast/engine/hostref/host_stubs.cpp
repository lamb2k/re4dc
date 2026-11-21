// hostref (game side): everything the player and camera call that the E1 reference does not host. Each
// body logs the call (host_stub_hit: counted per tick, names hashed in call order, written to the trace)
// and returns the neutral answer: no hit, no item, no water, no partner, nothing drawn or played.
// Categories follow SHELL_MAP.md section 5 (closure-iface-B.tsv): HUD and 2D, audio, effects, lights,
// drawing, debug, pad rumble, files the room does not need, other behaviour (the 72 E1 stubs).
#include "hostref.h"
#include "global.h"
#include "main.h"
#include "joy.h"
#include "model.h"
#include "em.h"
#include "player.h"
#include "act_btn.h"
#include "dmg.h"
#include "item.h"
#include "obj.h"
#include "light.h"
#include "db_cam.h"
#include "cockpit.h"
#include "mes.h"
#include "id_sys.h"
#include "db_log.h"
#include "snd.h"
#include "emwindow.h"
#include "emrack.h"
#include "pendulum.h"
#include "pl_wep.h"
#include "pl_npc.h"

#define HOST_STUB(n) host_stub_hit(n)

// ---------------- C linkage ----------------
extern "C" {
// effects
void AddSandPower(Vec*, f32) { HOST_STUB("AddSandPower"); }
void AddWaterPower(Vec*, f32) { HOST_STUB("AddWaterPower"); }
int ChkWaterEffectEnable(Vec*) { HOST_STUB("ChkWaterEffectEnable"); return 0; }
void EffectEfmDelete(int, int, int) { HOST_STUB("EffectEfmDelete"); }
void EffectEspDelete(int, int, u32, cModel*) { HOST_STUB("EffectEspDelete"); }
void EffectEspgenDelete(int, int, int) { HOST_STUB("EffectEspgenDelete"); }
int EspDataLoad(u32, u32, int) { HOST_STUB("EspDataLoad"); return 1; }
int EspDataRelease(u32, int, int) { HOST_STUB("EspDataRelease"); return 1; }
void EspSetEatEffect(Vec*, Vec*, int, int) { HOST_STUB("EspSetEatEffect"); }
void EspSetWaterHitmark(Vec*) { HOST_STUB("EspSetWaterHitmark"); }
void EstSet(int, int, Vec*, Vec*, int, int, int, int, u32, void*) { HOST_STUB("EstSet"); }
int GetWaterCrossPos(Vec*, Vec*, Vec*) { HOST_STUB("GetWaterCrossPos"); return 0; }
void QuakeMove() { HOST_STUB("QuakeMove"); }
void PenClothMove(cModel*, PenCloth*) { HOST_STUB("PenClothMove"); }
void PenClothMove3(cModel*, PenCloth*) { HOST_STUB("PenClothMove3"); }
void PenClothSet(cModel*, PenCloth*, f32) { HOST_STUB("PenClothSet"); }
// other behaviour (enemies, scenario, windows, racks, items, score); the actors' own entry points
// (spawn lists, damage, partner, Ganado) are original code since lane eng-host2
int ChkWindow(cModel*, Vec*, Vec*, int, u16*, Vec*, Vec*, cEmWindow**) { HOST_STUB("ChkWindow"); return 0; }
void GameAddPoint(int) { HOST_STUB("GameAddPoint"); }
void* SceExec(int, void*, int, u8, int, void*) { HOST_STUB("SceExec"); return 0; }
int ExeWindowEventTask(void*) asm("ExeWindowEvent__9cEmWindow");
int ExeWindowEventTask(void*) { HOST_STUB("cEmWindow::ExeWindowEvent"); return 0; }
// pad rumble, performance counters
u32 PPCMfpmc1() { return 0; }
void PPCMtmmcr0(u32) {}
void PPCMtmmcr1(u32) {}
void PPCMtpmc1(u32) {}
void PPCMtpmc2(u32) {}
void PPCMtpmc3(u32) {}
void PPCMtpmc4(u32) {}
// drawing and debug primitives
void Draw_cylinder(Vec*, f32, f32, u32) { HOST_STUB("Draw_cylinder"); }
void Draw_line3d(Vec*, Vec*, u32, int) { HOST_STUB("Draw_line3d"); }
void Draw_line3d_local(Vec*, Vec*, Mtx, u32, int) { HOST_STUB("Draw_line3d_local"); }
void Draw_local_pos(Vec*, int, Mtx) { HOST_STUB("Draw_local_pos"); }
void Draw_poly(Vec*, u32, int) { HOST_STUB("Draw_poly"); }
void Draw_poly_local(Vec*, Mtx, u32, int) { HOST_STUB("Draw_poly_local"); }
void Draw_pos(Vec*, int) { HOST_STUB("Draw_pos"); }
void Draw_quad(Vec*, Vec*, u32) { HOST_STUB("Draw_quad"); }
void Draw_sphere(Vec*, f32, u32, int, int) { HOST_STUB("Draw_sphere"); }
void Filter01SetParam(int, int, u8, f32) { HOST_STUB("Filter01SetParam"); }
void GXSetLineWidth(u8, int) {}
int EspEstSetSelect(int, int, int, void** out, int) { HOST_STUB("EspEstSetSelect"); if (out) *out = 0; return 0; }
void EspDrawLaserLine(Vec, Vec, f32) { HOST_STUB("EspDrawLaserLine"); }
// HUD textures
int IdTexDataLoad(void*, int) { HOST_STUB("IdTexDataLoad"); return 1; }
void IdTexRelease(int) { HOST_STUB("IdTexRelease"); }
// old-port hooks reached with every knob off
void re4dc_model_assets_changed() {}
// re4dc_motion_acquire / re4dc_motion_release: host_data.cpp (the prepared archives' separate keys)
void re4dc_halt(const char* file, int line) { host_fatal(4, "HALT %s(%d)", file, line); }
void* _impure_ptr;
}

// ---------------- C++ linkage ----------------
void CameraDebugInformation() { HOST_STUB("CameraDebugInformation"); }
int GetWaterHeight(Vec*, f32*) { HOST_STUB("GetWaterHeight"); return 0; }
void TaskSleep(int) { HOST_STUB("TaskSleep"); }
void QuakeInit() { HOST_STUB("QuakeInit"); }
int BtoX(int bits) { return bits; }   // eprintf.cpp: pad debug page only
void eprintf(int, int, int, int, const char*, ...) { HOST_STUB("eprintf"); }
void eprintf2(int, int, int, int, int, int, const char*, ...) { HOST_STUB("eprintf2"); }
u32 SndCall(u16, u16, Vec*, int, int, cUnit*) { HOST_STUB("SndCall"); return 0; }
int SndStop(u32, int) { HOST_STUB("SndStop"); return 0; }

void cActionButton::set(int, int, int, int, int, int, int, int) { HOST_STUB("cActionButton::set"); }
// The armed handgun's magazine (lane eng-e1h): the new game's Punisher with its 10 rounds loaded and no ammo carried, as
// the engine images serve it (host/e1_stubs.cpp; the fight image's fight_stubs.cpp the same for its first 7 shots).
// Until this lane the reference answered 0, an empty gun: A while aiming took the empty-gun branch and no shot fired.
// item.cpp's rules for a type-1 weapon: trigger spends a loaded round (0 when empty), reloadable when not full and
// ammo is carried, reload moves carried rounds in.
namespace { int g_mag_loaded = 10, g_mag_spare = 0; }
u16 cItemMgr::bulletNum() { return (u16) g_mag_loaded; }
u32 cItemMgr::bulletNumCurrent() { return (u32) g_mag_loaded; }
int cItemMgr::num(int, u8) { HOST_STUB("cItemMgr::num"); return 0; }
int cLightMgr::update(int, int) { HOST_STUB("cLightMgr::update"); return 0; }
cLightInfo::cLightInfo() {}
int cLightInfo::init2(int, int, const Vec*, const Vec*, int) { HOST_STUB("cLightInfo::init2"); return 1; }
void cLightInfo::updateMatrix(cModel*) { HOST_STUB("cLightInfo::updateMatrix"); }
void debugCamera::move(Camera*, JOY*, int) { HOST_STUB("debugCamera::move"); }
void Cockpit::lifeMeterDisp(int) { HOST_STUB("Cockpit::lifeMeterDisp"); }
void Cockpit::roomInit() { HOST_STUB("Cockpit::roomInit"); }
void cLog::err(int, int, const char* fmt, ...)
{
    host_log("cLog::err: %s", fmt);
    HOST_STUB("cLog::err");
}
void cLog::mes(int, int, const char*, ...) { HOST_STUB("cLog::mes"); }
int cEmRack::adjustRange(u8) { HOST_STUB("cEmRack::adjustRange"); return 0; }
int cEmWindow::ChkBreakDir(Vec*) { HOST_STUB("cEmWindow::ChkBreakDir"); return 0; }
int cEmWindow::ChkStatus() { HOST_STUB("cEmWindow::ChkStatus"); return 0; }
int cItemMgr::reload()
{
    int n = 10 - g_mag_loaded;
    if (n > g_mag_spare) n = g_mag_spare;
    g_mag_loaded += n;
    g_mag_spare -= n;
    return n > 0;
}
int cItemMgr::trigger()
{
    if (g_mag_loaded == 0) return 0;
    g_mag_loaded--;
    return 1;
}
cObj* SetObj10(void*, void*, Vec*, Vec*, Vec*, f32, f32, int, int) { HOST_STUB("SetObj10"); return 0; }
void Obj10SetEst(cObj*, int, int, u32, int, int, int, int, int, int) { HOST_STUB("Obj10SetEst"); }
int cItemMgr::reloadable() { return g_mag_loaded < 10 && g_mag_spare > 0; }
void cObjLauncher::grip(int) { HOST_STUB("cObjLauncher::grip"); }
void cObjLauncher::gripBack() { HOST_STUB("cObjLauncher::gripBack"); }
void cLog::warn(int, int, const char*, ...) { HOST_STUB("cLog::warn"); }
void cLog::vwarn(int, int, const char*, char*) { HOST_STUB("cLog::vwarn"); }
