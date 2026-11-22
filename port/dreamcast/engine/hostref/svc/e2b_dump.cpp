// e2b_dump.cpp (game side; lane eng-e2b): the boundary log of em10's service functions (the Ganado's sounds, voices,
// footsteps, weapon sound set, blood, hit mark, water, cut-in cameras, on-screen check; native in services/em10/),
// linked into odump (em10's original bodies) and native (the engine's) alike. RE4_SVC_OUT=<dir> receives e2b.txt:
//   - every call to the sound entry points (SndCall, SndStop, the ctrl11 voice slots, the ctrl12 locks) and to the
//     effect entry points (EstSet, EspGetEstAddr, EspEstSetSelect) made outside another service's logged call (the
//     enemy hit geometry's, round 4's, a collision query's: those compare at their own boundary), in call order, with
//     their tick and arguments: what em10's functions hand on is what they decided;
//   - at the start of every tick, each live Ganado's presentation state (its sound numbers, voice and breath timers, the
//     chainsaw's timers, the water and chain waits, its hand pose, its step number, its model parts as pool slots, the
//     work camera em10's cut-ins frame and the eye they keep) and the camera service's extra camera.
// Tokens as svc/e2_compare.py reads them (e2_compare.py --log e2b.txt): integers and hex exact; "P" x,y,z within
// max(0.01 unit, 2^-20 of the value); "R" a length the same. Lines starting with '#' are markers.
//
// Exercise (RE4_SVC_EXERCISE=e2b, both builds alike): the fixtures' own play reaches only the footsteps, the breath, the
// voices and the blood of a handgun hit; from tick 30, every 5th tick, the first live Ganado's record is kept, each of
// the functions above is called on planted inputs (voice kinds and model types, weapon kinds, every weapon id's blood
// with and without armour, near and far, each step number for a village, a claw and a flail Ganado, every cut-in shot
// and region, the take-away, the throw-off eye, the on-screen check) with its outputs logged, and the record is put back.
// Controls (RE4_SVC_CONTROL, native only): voicebank, bloodswap, footpart (services/em10/em10_pres.cpp), camease,
// screenhalf (em10_cam.cpp), handgrip, accnone, keepcap (em10_model.cpp). Each tick also logs the live character and
// object records (A), and the exercise changes the hands and head on the record as it is (XH, XD: their model infos
// stay, as when the behaviour changes them) and runs the aiming blend once (tick 300, the record put back).
#include "hostref.h"
#include "model.h"
#include "em.h"
#include "em10.h"
#include "player.h"
#include "camera.h"
#include "cam_ctrl.h"
#include "ctrl.h"
#include "esp.h"
#include "snd.h"
#include "emwep.h"
#include "global.h"
#include "motion.h"

extern "C" {
void* svc_out_open(const char* name, const char* mode);
void svc_out_printf(void* f, const char* fmt, ...);
void svc_out_close(void* f);
const char* svc_env(const char* name);
int svc_col_depth(void);
int svc4_depth(void) __attribute__((weak));
int svc_e2_depth(void) __attribute__((weak));
extern int em10p_control __attribute__((weak));
extern int em10c_control __attribute__((weak));
extern int em10m_control __attribute__((weak));
// em10's entry points the exercise calls (the original or the engine's, by the build)
void Em10SetSeTbl(cEm10* em, int type);
void em10CallVoiceSe(cEm10* em, u16 no);
void em10CsawSignSe(cEm10* em);
void em10BehindSeCk(cEm10* em);
void em10WepSeEffSet(cEm10* em, cEmWep* wep, int type);
void em10CamMove(cEm10* em, int no, f32 rate, int shake);
void em10CamMoveCri(cEm10* em, u32 no, int shake);
void em10CamMoveAshley(cEm10* em, u32 no);
void em10CamMoveTakeaway(cEm10* em);
void em10SetCampos2(cEm10* em);
int em10ScreenInCk(cEm10* em);
}
void em10CallVoiceSe2(cEm10* em, int no, int a);
void em10BreathSe(cEm10* em);
void em10SetDamageVoice(cEm10* em, int a, int b);
void em10FootSe(cEm10* em);
void em10BloodSet(cEm10* em, int near);
void em1cBloodSet(cEm10* em, int near);
void em10KickHitMark(cEm10* em);
void em10SetDmWaterEff(cEm10* em, int a);
void em10SetWaterEff(cEm10* em);
void em10CamMove2(cEm10* em);
void em10HandSet(cEm10* em, int type);
void em10HeadSet(cEm10* em, int no);
extern "C" void em10BlendMotSet(cEm10* em, void* m0, void* m1, void* m2, int a, int b, int c, int d);
extern "C" void em10SetAccesory(cEm10* em);
#define P svc_out_printf

int GetScreenPos(Vec* pos, Vec* scr);
namespace {
void* g_f;
void* g_diag;   // e2b-diag.txt: diagnostics, not compared
unsigned g_tick;
u32 actor(const void* m)
{
    const u32 a = (u32) m, elo = (u32) EmMgr.pArray, olo = (u32) ObjMgr.pArray;
    if (!m) return 998;
    if (a >= elo && a < elo + EmMgr.size * EmMgr.nArray) return (a - elo) / EmMgr.size;
    if (a >= olo && a < olo + ObjMgr.size * ObjMgr.nArray) return 64 + (a - olo) / ObjMgr.size;
    return 999;
}
// a model info as its pool slot ('-' none, '?' outside the pool)
void info(const void* p)
{
    const u32 a = (u32) p, lo = (u32) ModInfoMgr.pArray;
    if (!p) P(g_f, " -");
    else if (a >= lo && a < lo + ModInfoMgr.size * ModInfoMgr.nArray) P(g_f, " i%u:%x", (a - lo) / ModInfoMgr.size, ((const cModelInfo*) p)->be_flag);
    else P(g_f, " ?");
}
void pv(const Vec* v) { P(g_f, " P%.9g,%.9g,%.9g", (double) v->x, (double) v->y, (double) v->z); }
void len(f32 r) { P(g_f, " R%.9g", (double) r); }
// outside another service's logged call
bool top() { return g_f && svc_col_depth() == 0 && (!svc4_depth || svc4_depth() == 0) && (!svc_e2_depth || svc_e2_depth() == 0); }
bool ganado(const cEm* e) { return e && (e->be_flag & 1) && e->id >= 0x10 && e->id <= 0x20; }
void camera(const Camera& c)
{
    pv(&c.param.pos), pv(&c.param.at), pv(&c.up), len(c.dist), len(c.param.fovy);
    for (int k = 0; k < 4; k++) {
        const Vec col = {c.mat[0][k], c.mat[1][k], c.mat[2][k]};
        pv(&col);
    }
}
void extra()
{
    const u32 x = (u32) CamCtrl.m_pExtraCamera;
    if (!x) { P(g_f, " X-"); return; }
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext)
        if (x == (u32) &EM10_WK(e)->Cam) { P(g_f, " X%u", actor(e)); return; }
    P(g_f, " X?");
}
// a Ganado's presentation state
void state(cEm* e, const char* tag)
{
    const Em10Work* w = EM10_WK(e);
    P(g_f, "%u %s %u t%u se", g_tick, tag, actor(e), e->type);
    for (int i = 0; i < 19; i++) P(g_f, "%c%x", i ? ',' : ' ', w->Se_tbl[i]);
    P(g_f, " bw%u cf%u cs%d ww%d,%d,%u cw%u ht%u sn%u id%x,%x,%x", w->Breath_se_wait, w->Csaw_fake_timer, w->Csaw_sign_wait,
      w->Water_eff_wait, w->Water_eff_wait2, w->Water_eff_wait3, w->Chain_se_wait, w->Hand_type, e->seNo, w->Seid_voice,
      w->Seid_breath, w->Seid_csaw);
    P(g_f, " mi");
    info(w->pHead), info(w->pRHand), info(w->pLHand), info(w->pRobe), info(w->pCloth), info(w->pGoods), info(w->pSack);
    info(w->pHood), info(w->pWhood);
    for (int i = 0; i < 7; i++) info(w->pAccesory[i]);
    P(g_f, " ob %u %u wp %u %u k%u bl%d,%u", actor(w->pCap), actor(w->pGlasses), actor(w->pWep), actor(w->pWeapon2),
      w->Cap_type, w->Hokan, w->Frame);
    len(w->blendRate), len(w->blendMot.blendRate);
    P(g_f, " %d cam", e->blendMot == &w->blendMot);
    pv(&w->Campos);
    camera(w->Cam);
    extra();
    P(g_f, "\n");
}
}   // namespace

// ---- the outgoing calls ----
#define WR(ret, sym, params, args, log)                                                                              \
    extern "C" ret __real_##sym params;                                                                              \
    extern "C" ret __wrap_##sym params                                                                               \
    {                                                                                                                \
        ret r = __real_##sym args;                                                                                   \
        if (top()) { P(g_f, "%u", g_tick); log; P(g_f, "\n"); }                                                        \
        return r;                                                                                                    \
    }
#define WRV(sym, params, args, log)                                                                                  \
    extern "C" void __real_##sym params;                                                                             \
    extern "C" void __wrap_##sym params                                                                              \
    {                                                                                                                \
        __real_##sym args;                                                                                           \
        if (top()) { P(g_f, "%u", g_tick); log; P(g_f, "\n"); }                                                        \
    }
// (written out: lane eng-e2c's boss exercise sees every sound call too, through its weak hook, before this log)
extern "C" void e2c_snd_hook(u16 blk, u16 no, Vec* pos, int id, int vol, cUnit* o) __attribute__((weak));
extern "C" u32 __real__Z7SndCallttP3VeciiP5cUnit(u16 blk, u16 no, Vec* pos, int id, int vol, cUnit* o);
extern "C" u32 __wrap__Z7SndCallttP3VeciiP5cUnit(u16 blk, u16 no, Vec* pos, int id, int vol, cUnit* o)
{
    if (e2c_snd_hook) e2c_snd_hook(blk, no, pos, id, vol, o);
    u32 r = __real__Z7SndCallttP3VeciiP5cUnit(blk, no, pos, id, vol, o);
    if (top()) { P(g_f, "%u", g_tick); P(g_f, " SC %u %x", blk, no); if (pos) pv(pos); else P(g_f, " P-"); P(g_f, " %d %d %u -> %x", id, vol, actor(o), r); P(g_f, "\n"); }
    return r;
}
WR(int, _Z7SndStopmi, (unsigned long id, int t), (id, t), { P(g_f, " SS %lx %d", id, t); })
WR(u32, _Z11Ctrl11SetSeP5cCtrlP6cModelsti, (cCtrl* c, cModel* m, s16 time, u16 no, int idx), (c, m, time, no, idx),
   { P(g_f, " C11 %u %d %x %d -> %x", actor(m), time, no, idx, r); })
WR(u32, _Z12Ctrl11SetSe2P5cCtrlP6cModelstit, (cCtrl* c, cModel* m, s16 time, u16 no, int idx, u16 blk), (c, m, time, no, idx, blk),
   { P(g_f, " C11b %u %d %x %d %u -> %x", actor(m), time, no, idx, blk, r); })
WR(u32, Ctrl11SetSe2__FP5cCtrlP6cModelsUsiUs, (cCtrl* c, cModel* m, s16 time, int no, int idx, int blk), (c, m, time, no, idx, blk),
   { P(g_f, " C11i %u %d %x %d %d -> %x", actor(m), time, no, idx, blk, r); })
WR(u32, _Z18Ctrl11StopAndSetSeP5cCtrlP6cModelsti, (cCtrl* c, cModel* m, s16 time, u16 no, int idx), (c, m, time, no, idx),
   { P(g_f, " C11s %u %d %x %d -> %x", actor(m), time, no, idx, r); })
WR(int, _Z8Ctrl12CkP5cCtrli, (cCtrl* c, int idx), (c, idx), { P(g_f, " C12k %d -> %d", idx, r); })
WRV(_Z9Ctrl12SetP5cCtrlit, (cCtrl* c, int idx, u16 v), (c, idx, v), { P(g_f, " C12s %d %u", idx, v); })
WRV(Ctrl12Set__FP5cCtrliUs, (cCtrl* c, int idx, int v), (c, idx, v), { P(g_f, " C12S %d %d", idx, v); })
WR(EspSeqData*, EspGetEstAddr, (u32 owner, int id, int quiet), (owner, id, quiet), { P(g_f, " EA %x %x %d -> %d", owner, id, quiet, r != 0); })
WR(int, EspEstSetSelect, (int owner, int id, int no, cEsp** out, int ns), (owner, id, no, out, ns),
   { P(g_f, " EQ %x %x %d %d -> %d", owner, id, no, ns, r); })
// EstSet is wrapped by e2_dump.cpp (the enemy hit geometry's log): it calls this hook first for every start
extern "C" void e2b_est(int a, int b, Vec* p, Vec* r, int c, int d, int e, int f, u32 g)
{
    if (!top()) return;
    P(g_f, "%u ES %u %d", g_tick, a > 0x1000 ? actor((void*) a) : 0u, b);
    if (p) pv(p); else P(g_f, " P-");
    if (r) pv(r); else P(g_f, " r-");
    P(g_f, " %x %x %d %d %u\n", c, d, e, f, g > 0x1000 ? actor((void*) g) : (u32) g);
}

// ---- the exercise ----
namespace {
int g_ex;
unsigned g_end;   // RE4_E2B_END: the tick of the destructor step (0: none)
alignas(16) u8 g_save[0x1000];
alignas(16) u8 g_wep[0x800];   // a scratch weapon (cEmWep) for em10WepSeEffSet
void plant_blood(cEm10* e, u8 wep, s16 parts)
{
    static YARARE_INFO box;
    box = e->hitInfo;
    box.partsNo = parts;
    box.next = 0;
    e->dmg.m_Wep = wep;
    e->dmg.m_pDamageYarare = &box;
    e->dmg.m_PosFrom = e->pos;
    e->dmg.m_PosFrom.x += 400.0f, e->dmg.m_PosFrom.y += 1100.0f, e->dmg.m_PosFrom.z -= 250.0f;
}
void exercise(unsigned t)
{
    cEm10* e = 0;
    for (cEm* x = EmMgr.pAlive; x; x = (cEm*) x->pNext)
        if (ganado(x)) { e = (cEm10*) x; break; }
    if (!e) return;
    const u32 n = EmMgr.size < sizeof(g_save) ? EmMgr.size : sizeof(g_save);
    __builtin_memcpy(g_save, (void*) e, n);
    const s32 keep_extra = CamCtrl.m_pExtraCamera;
    const u8 keep_region = pSys->region;
    Em10Work* w = EM10_WK(e);
    const unsigned k = (t - 30) / 5;
    P(g_f, "# e2b %u ganado %u\n", t, actor(e));
    // sound numbers of a voice kind, on a model type
    e->type = (u8) (k % 26);
    Em10SetSeTbl(e, (int) (k % 5));
    state(e, "XT");
    // voices and breath, muted every third round, on every model type over the rounds
    if (k % 3 == 2) w->flags |= 0x80; else w->flags &= ~0x80;
    em10CallVoiceSe(e, (u16) (0x10 + k % 7));
    em10CallVoiceSe2(e, (int) (0x20 + k % 5), 8);
    w->Breath_se_wait = (u16) (k & 1);
    em10BreathSe(e);
    e->hp = (k % 3 == 0) ? 0 : 50;
    w->pCore = (k % 4 == 1) ? (class cObj16*) g_wep : 0;
    em10SetDamageVoice(e, 0x11, 0x12);
    w->pCore = 0;
    e->hp = 50;
    w->flags &= ~0x80;
    state(e, "XV");
    // the chainsaw's tell, near and far
    w->flags |= 0x80000000u;
    w->Wep_type = 4;
    e->plDist2 = (k & 1) ? 30000000.0f : 1000000.0f;
    w->Csaw_fake_timer = (u16) (k % 3);
    w->Csaw_sign_wait = (s16) ((k & 2) ? 0 : 5);
    em10CsawSignSe(e);
    state(e, "XC");
    // "behind you": close, not attacking, seen (the player's own facing decides the rest)
    w->Wep_type = 0;
    w->Atk_wait = 0;
    e->plDist2 = 4000000.0f;
    w->Pl_rot = 0.0f;
    if (k % 3) w->flags |= 1; else w->flags &= ~1u;
    em10BehindSeCk(e);
    state(e, "XB");
    // footsteps: each step number on a village, a claw and a flail Ganado, with and without a chain wait
    for (int kind = 0; kind < 3; kind++) {
        e->type = kind == 1 ? 0xA : 0;
        w->Wep_type = kind == 2 ? 0xB : 0;
        for (int s = 1; s <= 8; s++) {
            w->Chain_se_wait = (u8) ((s + k) % 3);
            e->seNo = (u8) s;
            em10FootSe(e);
            P(g_f, "%u XF %d %d sn%u cw%u\n", g_tick, kind, s, e->seNo, w->Chain_se_wait);
        }
    }
    e->type = 0;
    w->Wep_type = 0;
    // the weapon's sound and effect numbers
    for (int type = (int) (k % 3); type < 18; type += 3) {
        __builtin_memset(g_wep, 0, sizeof(g_wep));
        em10WepSeEffSet(e, (cEmWep*) g_wep, type);
        const EmWepWork* ww = EMWEP_WK((cEmWep*) g_wep);
        P(g_f, "%u XW %d", g_tick, type);
        const u8* b = (const u8*) ww;
        for (u32 i = 0; i < sizeof(EmWepWork); i++)
            if (b[i]) P(g_f, " %x:%x", i, b[i]);
        P(g_f, "\n");
    }
    // blood: a slice of the weapon ids each round, near and far, on the body and on the head with the parasite out, and
    // on the parasite-headed type (its parasite part 0x25 too); odd rounds armoured (the zealot or soldier's helmet)
    if (k & 1) {
        e->flag |= 0x200;
        w->Ganado = (u8) (1 + ((k >> 1) & 1));
    }
    for (int i = 0; i < 6; i++) {
        const u8 wep = (u8) ((k * 6 + i) % 0x30);
        const int near = (i + k) & 1;
        plant_blood(e, wep, (s16) (1 + (i % 3) * 2));
        e->type = 0;
        em10BloodSet(e, near);
        plant_blood(e, wep, 5);
        w->pParasite = (k & 1) ? (class cEmPartner*) g_wep : 0;
        em10BloodSet(e, near);
        w->pParasite = 0;
        e->type = 0xA;
        plant_blood(e, wep, (i & 1) ? 0x25 : 3);
        em10BloodSet(e, near);
        em1cBloodSet(e, near);
        e->type = 0;
    }
    plant_blood(e, 3, 4);
    em10KickHitMark(e);
    em10SetDmWaterEff(e, (int) (k & 1));
    em10SetWaterEff(e);
    // the damage record, the flags and the class back before the cameras
    const u32 dmg_at = (u32) ((u8*) &e->dmg - (u8*) e);
    __builtin_memcpy(&e->dmg, g_save + dmg_at, sizeof(e->dmg));
    e->flag = ((cEm10*) g_save)->flag;
    w->Ganado = EM10_WK((cEm10*) g_save)->Ganado;
    // cut-in cameras: each shot, region and shake over the rounds
    pSys->region = (u8) ((k / 5) & 1);
    em10CamMove(e, (int) (k & 1), 0.25f, (int) (k & 2));
    state(e, "XM");
    em10CamMoveCri(e, k % 6, (int) (k & 1));
    state(e, "XR");
    em10CamMoveAshley(e, k % 5);
    state(e, "XA");
    em10CamMoveTakeaway(e);
    state(e, "XK");
    em10SetCampos2(e);
    state(e, "XS");
    em10CamMove2(e);
    state(e, "X2");
    // the on-screen check, judged against its rule on this build's own projection (GetScreenPos is the math service's:
    // the original sub2.cpp in odump, services/math/math_svc.cpp in native, and the two answer differently here: the
    // projections go to e2b-diag.txt, which is not compared)
    {
        const int r = em10ScreenInCk(e);
        int expect = 0;
        Vec q[2] = {e->pos, e->getPartsPtr(4)->world}, scr[2];
        int front[2];
        for (int i = 0; i < 2; i++) {
            front[i] = GetScreenPos(&q[i], &scr[i]);
            if (!expect && front[i] && scr[i].x > 0.0f && scr[i].x < 512.0f && scr[i].y > 0.0f && scr[i].y < 448.0f) expect = 1;
        }
        if (r == expect) P(g_f, "%u XI rule-ok\n", g_tick);
        else P(g_f, "%u XI rule-broken %d %d\n", g_tick, r, expect);
        if (g_diag)
            P(g_diag, "%u XI %d front %d %d scr %.6g,%.6g %.6g,%.6g\n", g_tick, r, front[0], front[1], (double) scr[0].x,
              (double) scr[0].y, (double) scr[1].x, (double) scr[1].y);
    }
    pSys->region = keep_region;
    CamCtrl.m_pExtraCamera = keep_extra;
    __builtin_memcpy((void*) e, g_save, n);
    // the model parts, on the record as it is (their effect stays, as when the behaviour changes them): every 4th round
    // up to the 40th, each hand pose with and without a weapon in hand (each grip kind), and the head (the lost head of
    // a zealot), a handful of model infos each time
    if (k % 4 == 0 && k < 40) {
        cEmWep* keep_wep = w->pWep;
        const u8 keep_wt = w->Wep_type, keep_class = w->Ganado;
        static const u8 grips[4] = {0, 1, 4, 6};   // (12, the rocket launcher's hand, is an archive entry this room lacks)
        w->Wep_type = grips[(k / 4) % 4];
        w->pWep = (k & 4) ? (cEmWep*) g_wep : 0;
        w->Hand_type = 0xFF;
        em10HandSet(e, (int) ((k / 4) % 4));
        w->pWep = keep_wep;
        w->Wep_type = keep_wt;
        state(e, "XH");
        w->Ganado = (u8) (w->mot[4] && ((k / 8) & 1));   // the bent-neck head only where the room has its model
        em10HeadSet(e, (int) ((k / 4) & 1));
        w->Ganado = keep_class;
        state(e, "XD");
    }
    // the aiming blend once, on the motion the Ganado plays, its record put back after
    if (t == 300) {
        __builtin_memcpy(g_save, (void*) e, n);
        void* m = *(void**) MOTION(e);
        if (m) {
            w->blendRate = -96.0f;
            w->Hokan = 3;
            w->Frame = 5;
            em10BlendMotSet(e, m, m, m, 0, 0, 0, 4);
            state(e, "XL");
            w->blendRate = 64.0f;
            em10BlendMotSet(e, m, m, m, 0, 0, 0, 4);
            state(e, "XL");
        }
        __builtin_memcpy((void*) e, g_save, n);
    }
}
// Near the end of the run, on the record as it is (the effects stay): the village accessories a hat, a lantern and the
// glasses ask for (RE4_E2B_END less 12 ticks, the first Ganado), and that Ganado's destructor (at RE4_E2B_END: what it
// owns goes back to the pools; its class pointer put back so the run goes on). Only where the check asks for it (a few
// ticks before the fixture's end: the object handed over may be the player's weapon).
void last(unsigned t)
{
    cEm10* first = 0;
    cEm10* lastg = 0;
    for (cEm* x = EmMgr.pAlive; x; x = (cEm*) x->pNext)
        if (ganado(x)) {
            if (!first) first = (cEm10*) x;
            lastg = (cEm10*) x;
        }
    if (!first) return;
    P(g_f, "# e2b-last %u\n", t);
    if (t != g_end) {
        const u32 keep = first->flag;
        first->type = 0;
        first->flag |= 0x00800000 | 0x00400000 | 0x00200000;
        em10SetAccesory(first);
        first->flag = keep;
        state(first, "XY");
        return;
    }
    // the village Ganados of these fixtures own nothing (no weapon, no hung object): the first live object record is
    // handed to it as its hung object, so the destructor has something to give back (both builds alike)
    Em10Work* w = EM10_WK(first);
    if (!w->pCap) w->pCap = ObjMgr.pAlive;
    void* vptr = *(void**) first;
    first->~cEm10();
    *(void**) first = vptr;
    state(first, "XZ");
}
}   // namespace

extern "C" void e2b_ready()
{
    g_f = svc_out_open("e2b.txt", "w");
    g_diag = svc_out_open("e2b-diag.txt", "w");
    const char* c = svc_env("RE4_SVC_CONTROL");
    if (c && &em10p_control) {
        if (!__builtin_strcmp(c, "voicebank")) em10p_control = 1;
        if (!__builtin_strcmp(c, "bloodswap")) em10p_control = 2;
        if (!__builtin_strcmp(c, "footpart")) em10p_control = 3;
    }
    if (c && &em10c_control && !__builtin_strcmp(c, "camease")) em10c_control = 1;
    if (c && &em10c_control && !__builtin_strcmp(c, "screenhalf")) em10c_control = 2;
    if (c && &em10m_control) {
        if (!__builtin_strcmp(c, "handgrip")) em10m_control = 1;
        if (!__builtin_strcmp(c, "accnone")) em10m_control = 2;
        if (!__builtin_strcmp(c, "keepcap")) em10m_control = 3;
    }
    const char* e = svc_env("RE4_SVC_EXERCISE");
    g_ex = e && !__builtin_strcmp(e, "e2b");
    const char* end = svc_env("RE4_E2B_END");
    g_end = 0;
    for (; end && *end >= '0' && *end <= '9'; end++) g_end = g_end * 10 + (unsigned) (*end - '0');
}
extern "C" void e2b_tick(unsigned t)
{
    g_tick = t;
    if (!g_f) return;
    u32 ne = 0, no = 0;
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext) {
        ne++;
        if (ganado(e)) state(e, "G");
    }
    for (cObj* o = ObjMgr.pAlive; o; o = (cObj*) o->pNext) no++;
    P(g_f, "%u A %u %u\n", t, ne, no);   // the live character and object records (what the destructor gives back)
    if (g_ex && t >= 30 && t % 5 == 0) exercise(t);
    if (g_ex && g_end && (t + 12 == g_end || t == g_end)) last(t);
}
extern "C" void e2b_finish()
{
    if (g_diag) svc_out_close(g_diag);
    g_diag = 0;
    if (!g_f) return;
    svc_out_close(g_f);
    g_f = 0;
}
