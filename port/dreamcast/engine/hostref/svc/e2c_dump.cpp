// e2c_dump.cpp (game side; lane eng-e2c): the boss's service entry points against the original on the PC reference.
// The reference's fixtures do not host El Gigante, so this is an exercise (RE4_SVC_EXERCISE=e2cboss), as lane eng-e2a's
// e2geom: at fixed ticks of a fixture it plants a giant (a copy of a live actor's model header, so its parts are that
// actor's, and a cleared giant work area) and calls the entry points, the same calls in odump (the original em2b.cpp,
// host copy) and native (services/boss/). RE4_SVC_OUT=<dir> receives e2c.txt: per call its tick, inputs and outputs,
// and the requests it made (QuakeExec, SndCall, EstSet, MotionSetCore: logged, the motion set-up not run on the planted
// giant). Tokens as e2_dump.cpp's (svc/e2_compare.py reads them with lane eng-e2a's bounds, unchanged): plain integers
// and hex exact, "P" a position, "R" a length, "A" an angle; lines starting with '#' are markers.
//
// Groups and schedule (begin of a tick unless said):
//   presentation  from tick 30, every 3rd: the four event cameras (blow at a rate stepped by tick, stamp, escape,
//                 parasite attack) planted on Leon; the quake at 14 distances from the game camera; foot landings in
//                 8 of the 32 combinations of sound key, mirrored motion, second dust, form and chain
//   view          from tick 30, every tick: the on-screen test planted on every live actor
//   skeleton      from tick 31, every 3rd: the neck turn (three calls) planted on each live Ganado, the watcher and the
//                 last angle stepped by tick, the neck part's record put back after; the giant's blend and the player's
//                 strangle blend on planted works; at the end of every 9th tick from 45, the squash on one live
//                 Ganado's own record (its routine and scale planted and put back; its parts handed out first)
// Controls (RE4_SVC_CONTROL, native only; services/boss/boss_svc.h): bosscam, bossquake, bossneck, bossblend.
#include "hostref.h"
#include "model.h"
#include "em.h"
#include "player.h"
#include "pl_npc.h"
#include "em2b.h"
#include "camera.h"
#include "cam_ctrl.h"
#include "motion.h"
#include "math_sub.h"
#include "atari.h"
#include "obj.h"
#include "wep_mod.h"
#include "ctrl.h"
#include "TexRender.h"
#include "pendulum.h"
#include "pl_cloth.h"
#include "light.h"

extern "C" {
void* svc_out_open(const char* name, const char* mode);
void svc_out_printf(void* f, const char* fmt, ...);
void svc_out_close(void* f);
const char* svc_env(const char* name);
extern int boss_control __attribute__((weak));
}
#define P svc_out_printf

namespace {
void* g_f;
unsigned g_tick;
int g_ex;
int g_in;   // inside an exercise call: the requests are logged (and the motion set-up not run)
alignas(32) u8 g_gi_mem[0x2000];
cEm2b* const g_gi = (cEm2b*) g_gi_mem;
alignas(32) u8 g_save[0x2000];

u32 actor(const void* m)
{
    const u32 a = (u32) m, elo = (u32) EmMgr.pArray, olo = (u32) ObjMgr.pArray;
    if (m == g_gi) return 900;
    if (a >= elo && a < elo + EmMgr.size * EmMgr.nArray) return (a - elo) / EmMgr.size;
    if (a >= olo && a < olo + ObjMgr.size * ObjMgr.nArray) return 64 + (a - olo) / ObjMgr.size;
    return 999;
}
void pv(const Vec* v) { P(g_f, " P%.9g,%.9g,%.9g", (double) v->x, (double) v->y, (double) v->z); }
void len(f32 r) { P(g_f, " R%.9g", (double) r); }
void ang(f32 a) { P(g_f, " A%.9g", (double) a); }
// a float's bits (compared exactly: a value both builds compute by the same exact operations)
u32 bits(f32 v)
{
    u32 b;
    __builtin_memcpy(&b, &v, 4);
    return b;
}
void mcols(const Mtx m)
{
    for (int c = 0; c < 4; c++) {
        const Vec col = {m[0][c], m[1][c], m[2][c]};
        pv(&col);
    }
}
int parts_count(cModel* m)
{
    int n = 0;
    for (cModel* p = m->pParts; p && n < 256; p = p->pParts) n++;
    return n;
}
// a planted giant: the model header of `src` (its parts list, matrix, position, motion work), the giant's work cleared
void plant(cModel* src)
{
    const u32 head = (u32) ((u8*) EM2B_WK(g_gi) - g_gi_mem);
    __builtin_memset(g_gi_mem, 0, sizeof(g_gi_mem));
    __builtin_memcpy(g_gi_mem, (void*) src, head);
}
bool live_ganado(cEm* e) { return e != (cEm*) pPL && (void*) e != (void*) pSUB && (e->be_flag & 0x201) == 1 && parts_count(e) > 4; }
}   // namespace

// ---- the requests made inside an exercise call ----
extern "C" void __real_QuakeExec(u8 id, u16 delay, s16 time, f32 power, u8 axis);
extern "C" void __wrap_QuakeExec(u8 id, u16 delay, s16 time, f32 power, u8 axis)
{
    if (g_f && g_in) {
        P(g_f, "%u QE %u %u %d", g_tick, id, delay, time);
        len(power);
        P(g_f, " %u\n", axis);
    }
    __real_QuakeExec(id, delay, time, power, axis);
}
// sound calls: from e2b_dump.cpp's SndCall wrapper (its hook; both lanes log the same entry point)
extern "C" void e2c_snd_hook(u16 blk, u16 no, Vec* p, int id, int a, cUnit* o)
{
    if (g_f && g_in) {
        P(g_f, "%u SC %u %u", g_tick, blk, no);
        if (p) pv(p); else P(g_f, " P-");
        P(g_f, " %x %d %u\n", id, a, actor(o));
    }
}
// effect requests: from e2_dump.cpp's EstSet wrapper (the hook below)
extern "C" void e2c_est_hook(int a, int b, Vec* p, Vec* r, int c, int d, int e, int f, u32 g, void* h)
{
    if (!g_f || !g_in) return;
    P(g_f, "%u ES %u %d", g_tick, actor((void*) a), b);
    if (p) pv(p); else P(g_f, " P-");
    P(g_f, " %d %d %d %d %u %d %d\n", r != 0, c, d, e, actor((void*) g), f, h != 0);
}
extern "C" void __real__Z13MotionSetCoreP6cModelPvS1_iiii(cModel* m, void* w, void* data, int seq, int hokan, int flags, int frame);
extern "C" void __wrap__Z13MotionSetCoreP6cModelPvS1_iiii(cModel* m, void* w, void* data, int seq, int hokan, int flags, int frame)
{
    if (g_f && g_in) {   // the planted giant's works: logged, not run (the data words are the exercise's tokens)
        P(g_f, "%u MS %u %d %x %d %d %d %d\n", g_tick, actor(m), (int) ((u8*) w - (u8*) m), (u32) data, seq, hokan, flags, frame);
        return;
    }
    __real__Z13MotionSetCoreP6cModelPvS1_iiii(m, w, data, seq, hokan, flags, frame);
}
// The screen projection asked inside an exercise call: answered by this file's own projection of the game camera
// (eye and target of pG->Cam, its field of view, a 512 x 448 picture, depth 0.5 in front and 2 behind), the same in
// both builds. The test compares the entry point's question (which point) and its window, not the projection: the
// image's projection is the engine's already, and the PC reference's native build has no projection state to read
// (its GXGetProjectionv returns the last GXSetProjection, which the native camera service never calls: every point
// lands at the picture's centre there).
namespace {
Vec g_scr_in;   // the point the entry point asked about (its answer is the line's last word; the projection is this
                // file's own and is not compared: a point near the eye's plane magnifies the builds' 0.002-unit camera
                // difference)
}
extern "C" int __real_GetScreenPos(Vec* pos, Vec* scr);
extern "C" int __wrap_GetScreenPos(Vec* pos, Vec* scr)
{
    if (!(g_f && g_in)) return __real_GetScreenPos(pos, scr);
    const Vec& e = pG->Cam.param.pos;
    const Vec& a = pG->Cam.param.at;
    f32 lx = e.x - a.x, ly = e.y - a.y, lz = e.z - a.z;
    f32 l = __builtin_sqrtf(lx * lx + ly * ly + lz * lz);
    lx /= l, ly /= l, lz /= l;                             // look (eye - target)
    f32 rx = lz, rz = -lx, r = __builtin_sqrtf(rx * rx + rz * rz);
    rx /= r, rz /= r;                                       // right = up x look, horizontal
    const f32 ux = ly * rz, uy = lz * rx - lx * rz, uz = -ly * rx;   // up = look x right
    const f32 dx = pos->x - e.x, dy = pos->y - e.y, dz = pos->z - e.z;
    const f32 vx = rx * dx + rz * dz, vy = ux * dx + uy * dy + uz * dz, vz = lx * dx + ly * dy + lz * dz;
    const f32 t = 1.0f / __builtin_tanf(pG->Cam.param.fovy * 0.5f * 0.0174532925f);
    // behind the eye: the picture's centre at depth 2; in front, clamped to +-10000 (far outside the window either way:
    // a point near the eye's plane would otherwise turn the two builds' 0.002-unit camera difference into pixels)
    const f32 w = -vz;
    const f32 sx = w > 0.0f ? 256.0f * (1.0f + vx * t * (448.0f / 512.0f) / w) : 256.0f;
    const f32 sy = w > 0.0f ? 224.0f * (1.0f - vy * t / w) : 224.0f;
    scr->x = sx < -10000.0f ? -10000.0f : sx > 10000.0f ? 10000.0f : sx;
    scr->y = sy < -10000.0f ? -10000.0f : sy > 10000.0f ? 10000.0f : sy;
    scr->z = w > 0.0f ? 0.5f : 2.0f;
    g_scr_in = *pos;
    return w > 0.0f;
}

namespace {
// ---- presentation ----
void log_cam(const char* tag)
{
    const Camera& c = EM2B_WK(g_gi)->Cam;
    P(g_f, "%u %s", g_tick, tag);
    len(c.param.fovy);
    pv(&c.param.pos);
    pv(&c.param.at);
    len(c.dist);
    mcols(c.mat);
    pv(&c.Look);
    pv(&c.Right);
    P(g_f, " slot %d\n", CamCtrl.m_pExtraCamera == (s32) &EM2B_WK(g_gi)->Cam);
}
void ex_cameras(unsigned t)
{
    const s32 keep = CamCtrl.m_pExtraCamera;
    plant(pPL);
    g_in = 1;
    const f32 rate = 0.05f + 0.1f * (f32) (t % 9);
    em2bBlowCamMove(g_gi, rate);
    P(g_f, "%u CB", t);
    len(rate);
    P(g_f, "\n");
    log_cam("cam");
    em2bStampCamMove(g_gi);
    log_cam("CS");
    em2bEscapeCamMove(g_gi);
    log_cam("CE");
    {   // coverage: whether the effect collision lay between the escape camera's target and eye (the pull-in branch)
        Vec a = {-244.0f, 809.0f, 52.5999985f}, b = {-376.0f, 575.0f, -1831.0f}, h;
        PSMTXMultVec(pPL->mat, &a, &a);
        PSMTXMultVec(pPL->mat, &b, &b);
        P(g_f, "%u CE-hit %d\n", t, EatMgr.hitCheck(&a, &b, &h, 0, 0x8000, 0) ? 1 : 0);
    }
    em2bParasiteAtkCamMove(g_gi);
    log_cam("CP");
    g_in = 0;
    CamCtrl.m_pExtraCamera = keep;
}
void ex_quake(unsigned t)
{
    static const f32 dist[14] = {0.0f, 3000.0f, 4999.0f, 5001.0f, 7000.0f, 9999.0f, 10001.0f, 12500.0f, 14999.0f, 15001.0f,
                                 18000.0f, 19999.0f, 20001.0f, 30000.0f};
    const Vec& eye = pG->Cam.param.pos;
    const f32 a = 0.37f * (f32) t, s = __builtin_sinf(a), c = __builtin_cosf(a);
    g_in = 1;
    for (int k = 0; k < 14; k++) {
        Vec p = {eye.x + dist[k] * s * 0.8f, eye.y + dist[k] * 0.6f, eye.z + dist[k] * c * 0.8f};
        P(g_f, "%u QK", t);
        pv(&p);
        P(g_f, "\n");
        em2bQuakeSet(&p);
    }
    g_in = 0;
}
void ex_feet(unsigned t)
{
    if (parts_count(pPL) < 0x1A) {
        P(g_f, "%u FS skipped parts %d\n", t, parts_count(pPL));
        return;
    }
    static u32 chain_token;   // a non-null chain object (only tested for null)
    for (int k = 0; k < 8; k++) {
        const u32 combo = (t * 8 + k) % 32;   // seNo 0..3, mirrored, second dust, form 3, chain
        plant(pPL);
        Em2bWork* w = EM2B_WK(g_gi);
        g_gi->seNo = (u8) (combo & 3);
        g_gi->motFlags = (u16) (((combo >> 2) & 1) ? (g_gi->motFlags | 0x40) : (g_gi->motFlags & ~0x40));
        w->Be_flg = (combo >> 3) & 1 ? 0x100 : 0;
        g_gi->type = (combo >> 4) & 1 ? 3 : 0;
        w->pChain = (k & 1) ? (cObj*) &chain_token : 0;
        w->espKind2 = (u8) (0x40 + k);
        g_gi->id = 0x2B;
        P(g_f, "%u FS %u %x %x %u %d\n", t, g_gi->seNo, g_gi->motFlags & 0x40, w->Be_flg, g_gi->type, w->pChain != 0);
        g_in = 1;
        em2bFootSe(g_gi);
        g_in = 0;
        P(g_f, "%u FS-> %u\n", t, g_gi->seNo);
    }
}
void ex_screen(unsigned t)
{
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext) {
        if ((e->be_flag & 0x201) != 1 || parts_count(e) < 1) continue;
        plant(e);
        g_in = 1;
        const int r = em2bInScreenCk(g_gi);
        g_in = 0;
        P(g_f, "%u SI %u", t, actor(e));
        pv(&g_scr_in);
        P(g_f, " %d\n", r);
    }
    // the root part swept round the game camera (12 headings, 3 pitches, 3 distances: in front, at the window's edges,
    // behind): Leon's root part record lent to the planted giant, its position put back after each call (the parts must
    // be guest records: the model services refuse a pointer outside the game's memory)
    plant(pPL);
    cModel* part = pPL->getPartsPtr(0);
    const Vec keep = part->world;
    const Vec eye = pG->Cam.param.pos;
    for (int h = 0; h < 12; h++)
        for (int v = 0; v < 3; v++) {
            const f32 yaw = 0.5236f * (f32) h + 0.05f * (f32) (t % 7), pitch = -0.35f + 0.35f * (f32) v;
            const f32 d = 800.0f + 4000.0f * (f32) ((h + v + t) % 3);
            part->world = Vec{eye.x + d * __builtin_cosf(pitch) * __builtin_sinf(yaw), eye.y + d * __builtin_sinf(pitch),
                              eye.z + d * __builtin_cosf(pitch) * __builtin_cosf(yaw)};
            g_in = 1;
            const int r = em2bInScreenCk(g_gi);
            g_in = 0;
            part->world = keep;
            P(g_f, "%u SI 900", t);
            pv(&g_scr_in);
            P(g_f, " %d\n", r);
        }
}

// ---- skeleton ----
void ex_neck(unsigned t)
{
    cEm* first = 0;
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext) {
        if (!live_ganado(e)) continue;
        if (!first) first = e;
        cParts* neck = (cParts*) e->getPartsPtr(3);
        const u32 flags = neck->motParts.flags;
        const Vec rot = neck->addRot;
        plant(e);
        Em2bWork* w = EM2B_WK(g_gi);
        static const u32 be[4] = {0x10, 0, 0x90, 0x14};
        w->Be_flg = be[(t / 3 + actor(e)) % 4];
        w->pFriend = (w->Be_flg & 0x80) ? (first != e ? first : (cEm*) pPL) : 0;
        w->Neck_dir_y = 0.25f * (f32) ((int) (t % 11) - 5) / 5.0f;
        g_gi->ang.y += 0.3f * (f32) (t % 7);
        P(g_f, "%u NK %u %x %u", t, actor(e), w->Be_flg, actor(w->pFriend));
        ang(w->Neck_dir_y);
        P(g_f, "\n");
        for (int n = 0; n < 3; n++) {
            g_in = 1;
            em2bNeckMove(g_gi);
            g_in = 0;
            cParts* p = (cParts*) g_gi->getPartsPtr(3);
            P(g_f, "%u NK->", t);
            ang(w->Neck_dir_y);
            P(g_f, " %x", p->motParts.flags);
            ang(p->addRot.x);
            ang(p->addRot.y);
            ang(p->addRot.z);
            P(g_f, "\n");
        }
        neck->motParts.flags = flags;
        neck->addRot = rot;
    }
}
void ex_blend(unsigned t)
{
    static const f32 rate[5] = {-200.0f, -1.0f, 0.0f, 37.5f, 255.0f};
    cEm* src = 0;
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext)
        if (live_ganado(e)) { src = e; break; }
    plant(src ? (cModel*) src : (cModel*) pPL);
    Em2bWork* w = EM2B_WK(g_gi);
    g_gi->frameMax = 40;
    w->Blend = rate[t % 5];
    w->blendCnt = (t % 2) ? 3 : 0;
    w->blendSeq = (t % 4 == 1) ? 39 : (int) (t % 40);
    const int a = 0x10 + (int) (t % 3), b = 0x20, c = 0x30;
    const u16 d = (u16) (t % 3);
    P(g_f, "%u BM", t);
    len(w->Blend);
    P(g_f, " %d %d %d %d %d %u\n", w->blendCnt, w->blendSeq, a, b, c, d);
    g_in = 1;
    for (int n = 0; n < 2; n++) {
        em2bBlendMotSet(g_gi, (void*) 0x1000, (void*) 0x2000, (void*) 0x3000, a, b, c, d);
        P(g_f, "%u BM-> %d %08x", t, (int) ((u8*) g_gi->motBlend - (u8*) g_gi), bits(EM2B_BLEND_MOT(w)->Brate));
        P(g_f, " %d %d\n", w->blendCnt, w->blendSeq);
    }
    // the player's strangle blend, planted on Leon's header (cPlayer layout)
    plant(pPL);
    cPlayer* pl = (cPlayer*) g_gi;
    pl->frameMax = 25;
    pl->blendRate500 = rate[(t + 2) % 5];
    pl->x4FD = (u8) ((t % 3) ? 2 : 0);
    pl->x4FC = (u8) ((t % 4 == 3) ? 24 : t % 25);
    P(g_f, "%u PB", t);
    len(pl->blendRate500);
    P(g_f, " %u %u\n", pl->x4FD, pl->x4FC);
    for (int n = 0; n < 2; n++) {
        plBlendMotSet(pl, (void*) 0x4000, (void*) 0x5000, 0x11, 0x22);
        P(g_f, "%u PB-> %d %08x", t, (int) ((u8*) pl->motBlend - (u8*) pl), bits(((MotionWork*) &pl->neckMot)->Brate));
        P(g_f, " %u %u\n", pl->x4FD, pl->x4FC);
    }
    g_in = 0;
}
// the squash on one live Ganado's own record, at the end of the tick (its pose is rebuilt next tick in both builds)
void ex_squash(unsigned t)
{
    cEm* e = 0;
    int k = 0;
    for (cEm* q = EmMgr.pAlive; q; q = (cEm*) q->pNext)
        if (live_ganado(q) && k++ == (int) (t / 9) % 3) { e = q; break; }
    if (!e) return;
    const int n = parts_count(e);
    for (int i = 0; i < n; i++) e->getPartsPtr(i);   // every part handed out (the native skeleton serves them back)
    cEm2b* g = (cEm2b*) e;
    Em2bWork* w = EM2B_WK(g);
    if ((u8*) &w->scaleRate + 4 > (u8*) e + EmMgr.size) {
        P(g_f, "%u SQ skipped record %u\n", t, EmMgr.size);
        return;
    }
    const u8 r0 = e->r_no_0, r1 = e->r_no_1;
    const f32 keep = w->scaleRate;
    static const u8 rr[3][2] = {{3, 1}, {3, 0}, {2, 1}};
    e->r_no_0 = rr[(t / 9) % 3][0];
    e->r_no_1 = rr[(t / 9) % 3][1];
    w->scaleRate = 0.3f + 0.05f * (f32) (t % 13);
    P(g_f, "# e2cboss squash %u\n", t);
    P(g_f, "%u SQ %u %u %u", t, actor(e), e->r_no_0, e->r_no_1);
    len(w->scaleRate);
    P(g_f, " %d\n", n);
    g_in = 1;
    em2bScaleCompress(g);
    g_in = 0;
    e->r_no_0 = r0, e->r_no_1 = r1;
    w->scaleRate = keep;
    int i = 0;
    for (cModel* p = e->pParts; p && i < n; p = p->pParts, i++) {
        P(g_f, "%u SQ-> %d", t, i);
        mcols(p->mat);
        P(g_f, "\n");
    }
}

}   // namespace
// The giant's virtual table, empty and strong (svc/svc.mk: the copies in em2b.cpp and the engine's are weak and would
// pull the whole of em2b into the link through their entries); the destructor under test only stores its address.
extern "C" const u32 e2c_em2b_vtable[17] asm("_ZTV5cEm2b") = {};
namespace {
// ---- lifetime: a giant's destructor releases the objects it holds ----
// Test objects of a free object kind (a plain cObj), the pool's: planted in the giant's object slots (some left empty),
// the destructor called, each one's state read back, the survivors released after.
constexpr int kTestKind = 0x3D;
void test_obj_init(cObj* p) { new (p) cObj(); }
bool g_kind_ok;
void ex_life(unsigned t)
{
    if (!g_kind_ok) return;
    plant(pPL);
    Em2bWork* w = EM2B_WK(g_gi);
    cObj* made[6] = {};
    for (int k = 0; k < 6; k++) made[k] = ((t / 50 + k) % 4 == 3) ? 0 : ObjMgr.create(kTestKind);
    w->pParasite = (cObj16*) made[0];
    w->pTen[(t / 50) % 10] = (cObj16*) made[1];
    w->pTen[9] = (cObj16*) made[2];
    w->pChain = made[3], w->pChain2 = made[4], w->pChain3 = made[5];
    P(g_f, "%u LF", t);
    for (int k = 0; k < 6; k++) P(g_f, " %u", made[k] ? actor(made[k]) : 999);
    P(g_f, "\n");
    g_in = 1;
    g_gi->cEm2b::~cEm2b();
    g_in = 0;
    P(g_f, "%u LF->", t);
    for (int k = 0; k < 6; k++) P(g_f, " %x", made[k] ? (made[k]->be_flag & 0x601) : 0xFFF);
    P(g_f, "\n");
    for (int k = 0; k < 6; k++)
        if (made[k] && (made[k]->be_flag & 0x201) == 1) ObjMgr.destroy(made[k]);
}

// ---- object: the oba bodies, made at tick 40 on two live actors (a part and the origin), one standing alone and one on a
// test object released at tick 70 (its oba must go with it); their place, matrix and cylinder logged every tick ----
}   // namespace
// The kind's constructor: the class is obj20.cpp's / oba_obj.cpp's cObjObaModel (declared here under its own name)
class cObjObaModel : public cObj {
public:
    virtual void move();
};
extern "C" cObj* SetObaModel(cObj* parent, int partsNo, Vec* ofs, f32 rad, u8 type, f32 h);
namespace {
void oba_init(cObj* p) { new (p) cObjObaModel(); }
cObj* g_oba[4];
cObj* g_oba_parent;
void ex_oba_make(unsigned t)
{
    if (!ObjInitFunc[0x20]) ObjInitFunc[0x20] = oba_init;
    cEm* a = 0;
    cEm* b = 0;
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext) {
        if (e == (cEm*) pPL || (e->be_flag & 0x201) != 1 || parts_count(e) < 4) continue;
        if (!a) a = e; else if (!b) { b = e; break; }
    }
    if (!a) a = (cEm*) pPL;
    if (!b) b = a;
    g_oba_parent = g_kind_ok ? ObjMgr.create(kTestKind) : 0;
    if (g_oba_parent) g_oba_parent->pos = Vec{pPL->pos.x + 900.0f, pPL->pos.y, pPL->pos.z - 400.0f};
    Vec o0 = {0.0f, 100.0f, 50.0f}, o1 = {200.0f, 0.0f, -150.0f}, o2 = {pPL->pos.x - 1500.0f, pPL->pos.y, pPL->pos.z + 700.0f},
        o3 = {0.0f, 300.0f, 0.0f};
    g_in = 1;
    g_oba[0] = SetObaModel((cObj*) a, 3, &o0, 300.0f, 0, 1000.0f);
    g_oba[1] = SetObaModel((cObj*) b, 0, &o1, 500.0f, 1, 800.0f);
    g_oba[2] = SetObaModel(0, 0, &o2, 400.0f, 0, 600.0f);
    g_oba[3] = g_oba_parent ? SetObaModel(g_oba_parent, 0, &o3, 250.0f, 1, 500.0f) : 0;
    g_in = 0;
    P(g_f, "%u OB made %u %u", t, actor(a), actor(b));
    for (int k = 0; k < 4; k++) P(g_f, " %u", g_oba[k] ? actor(g_oba[k]) : 999);
    P(g_f, "\n");
}
void ex_oba_log(unsigned t)
{
    if (t == 70 && g_oba_parent) {
        ObjMgr.destroy(g_oba_parent);
        P(g_f, "%u OB parent released\n", t);
        g_oba_parent = 0;
    }
    for (int k = 0; k < 4; k++) {
        cObj* o = g_oba[k];
        if (!o) continue;
        P(g_f, "%u OB %d %x", t, k, o->be_flag & 0x601);
        if ((o->be_flag & 0x201) != 1) {
            P(g_f, " gone\n");
            g_oba[k] = 0;
            continue;
        }
        pv(&o->pos);
        mcols(o->mat);
        const cAtariInfo& v = o->sub2B4.atari;
        P(g_f, " %x %x", (u32) (u16) v.m_flag, (u32) v.m_stat);
        P(g_f, "\n");
    }
}

// ---- hit check: the giants' push-apart. A live Ganado is made a giant in battle for the call (its id, status put
// back); a planted giant with no parts stands at offsets from it (inside 3000, outside, on it); its place is logged ----
void ex_push(unsigned t)
{
    cEm* b = 0;
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext)
        if (live_ganado(e)) { b = e; break; }
    if (!b) return;
    const u32 id = b->id, status = b->status;
    b->id = 0x2B;
    b->setStatus(EM_STATUS_ACTIVE);
    static const f32 ofs[6][2] = {{1000.0f, 400.0f}, {-2000.0f, 1500.0f}, {2999.0f, 0.0f}, {3001.0f, 10.0f}, {0.0f, 0.0f},
                                  {-450.0f, -2800.0f}};
    for (int k = 0; k < 6; k++) {
        plant(b);
        g_gi->pParts = 0;
        g_gi->pos = Vec{b->pos.x + ofs[k][0], b->pos.y + 120.0f * (f32) (k % 3), b->pos.z + ofs[k][1]};
        P(g_f, "%u PU %u", t, actor(b));
        pv(&g_gi->pos);
        g_in = 1;
        em2bObaHitCk(g_gi);
        g_in = 0;
        P(g_f, " ->");
        pv(&g_gi->pos);
        P(g_f, "\n");
    }
    b->id = id;
    b->status = status;
}

// ---- set-ups: the cloth, rope and chain descriptions and requests, the texture-render manager ----
// a chain record by its contents (the two builds' tables are at different addresses): every field, arrays through
// their pointers, floats by their bits (compared exactly)
void hex_bytes(const void* p, int n)
{
    if (!p) { P(g_f, " -"); return; }
    P(g_f, " ");
    for (int i = 0; i < n; i++) P(g_f, "%02x", ((const u8*) p)[i]);
}
void log_pen(const PenCloth* c)
{
    if (!c) { P(g_f, " pen-"); return; }
    const int n = c->Num > 0 && c->Num < 64 ? c->Num : 0;
    P(g_f, " n%d", c->Num);
    const u8* const links[7] = {c->pCloth, c->pLeft, c->pRight, c->pUpLeft, c->pUpRight, c->pParent, c->pChild};
    for (const u8* a : links) hex_bytes(a, n);
    const f32* const rows[5] = {c->pGravity, c->pRate, c->pMax, c->pWindSin, c->pWindRate};
    for (const f32* a : rows) hex_bytes(a, 4 * n);
    hex_bytes(c->pAtset, c->At_num > 0 && c->At_num < 16 ? c->At_num * (int) sizeof(CLOTH_AT_SET) : 0);
    P(g_f, " at%d %08x %08x %u %08x %08x %08x %d %u %x", c->At_num, bits(c->Gravity), bits(c->Rate), c->Bundle_num,
      bits(c->WindSin), bits(c->Stretchy), bits(c->Move_rate), c->pPtbl != 0, actor(c->pEm_at), c->Flag);
}
// offsets in the giant's archive of the models a chain object is made from
cEm* g_setup_em;
int arc_ofs(const void* p) { return g_setup_em ? (int) ((const u8*) p - (const u8*) g_setup_em->subArc) : -1; }
alignas(32) u8 g_trm_mem[sizeof(TexRenderMng)];   // a manager record (its constructor is the renderer's: not linked)
TexRenderMng& g_trm = *(TexRenderMng*) g_trm_mem;
int g_trm_on;
}   // namespace
extern "C" cObjChain* __real__Z8SetChainPvS_P3VecS1_(void* bin, void* tpl, Vec* pos, Vec* rot);
extern "C" cObjChain* __wrap__Z8SetChainPvS_P3VecS1_(void* bin, void* tpl, Vec* pos, Vec* rot)
{
    if (!(g_f && g_in)) return __real__Z8SetChainPvS_P3VecS1_(bin, tpl, pos, rot);
    P(g_f, "%u CH %d %d", g_tick, arc_ofs(bin), arc_ofs(tpl));
    pv(pos);
    pv(rot);
    P(g_f, "\n");
    return 0;   // no chain object kind in the boss image either (a stub that answers none)
}
extern "C" void __real__ZN9cObjChain8setChainEP8PenCloth(cObjChain* o, PenCloth* c);
extern "C" void __wrap__ZN9cObjChain8setChainEP8PenCloth(cObjChain* o, PenCloth* c)
{
    if (!(g_f && g_in)) { __real__ZN9cObjChain8setChainEP8PenCloth(o, c); return; }
    P(g_f, "%u CC %d", g_tick, o != 0);
    log_pen(c);
    P(g_f, "\n");
}
extern "C" void __real__ZN9cObjChain9setParentEP6cModeliP3Veci(cObjChain* o, cModel* m, int parts, Vec* ofs, int flag);
extern "C" void __wrap__ZN9cObjChain9setParentEP6cModeliP3Veci(cObjChain* o, cModel* m, int parts, Vec* ofs, int flag)
{
    if (!(g_f && g_in)) { __real__ZN9cObjChain9setParentEP6cModeliP3Veci(o, m, parts, ofs, flag); return; }
    P(g_f, "%u CA %d %u %x", g_tick, o != 0, actor(m), parts);
    pv(ofs);
    P(g_f, " %d\n", flag);
}
// not in the reference at all (the boss's rope only): a logging body in both builds
void cObjChain::setParent2(cModel* m, int p1, Vec* o1, int p2, Vec* o2, int flag)
{
    if (!(g_f && g_in)) return;
    P(g_f, "%u CA2 %d %u %x", g_tick, this != 0, actor(m), p1);
    pv(o1);
    P(g_f, " %x", p2);
    pv(o2);
    P(g_f, " %d\n", flag);
}
TexRenderMng* Ctrl12GetTexRenderEm2b(cCtrl* c)
{
    if (g_f && g_in) P(g_f, "%u TR %d %d\n", g_tick, c != 0, g_trm_on);
    return g_trm_on ? &g_trm : 0;
}
extern "C" int e2c_cloth_hook(cModel* m, PenCloth* c, f32 len)
{
    if (!(g_f && g_in)) return 0;
    P(g_f, "%u PC %u", g_tick, actor(m));
    log_pen(c);
    P(g_f, " R%.9g\n", (double) len);
    return 1;
}
namespace {
void log_setup(unsigned t, const char* tag)
{
    Em2bWork* w = EM2B_WK(g_gi);
    P(g_f, "%u %s cloth", t, tag);
    log_pen(&w->Cloth);
    P(g_f, "\n%u %s rope0", t, tag);
    log_pen(&w->rope[0]);
    P(g_f, "\n%u %s rope1", t, tag);
    log_pen(&w->rope[1]);
    P(g_f, "\n%u %s objs %d %d %d mgr %d", t, tag, w->pChain != 0, w->pChain2 != 0, w->pChain3 != 0, w->pMgr != 0);
    hex_bytes(w->Tex_buf, 8);
    P(g_f, " %x %u %u %d\n", g_trm.texId, g_trm.m_W_size, g_trm.m_H_size, g_trm.m_Rep_type);
}
// every form (0 to 3) through the three set-ups; the texture-render set-up in room 224 with and without a manager and in
// this room. The planted giant's archive is Leon's (only offsets into it are logged)
void ex_setup(unsigned t)
{
    for (int type = 0; type < 4; type++) {
        plant(pPL);
        g_gi->type = (u8) type;
        // the giant's archive: a table of model offsets of this file's own (Leon's archive pointer may be none here)
        static PlArc arc;
        for (u32 i = 0; i < 0x20; i++) arc.ofs[i] = 0x1000 + 0x40 * i;
        g_gi->subArc = &arc;
        g_setup_em = g_gi;
        g_in = 1;
        em2bClothSet(g_gi);
        if (type == 0) em2bShortRopeSet(g_gi);
        if (type == 3) em2bChainSet(g_gi);
        g_in = 0;
        char tag[8] = {'S', 'U', (char) ('0' + type), 0};
        log_setup(t, tag);
    }
    const u16 room = pG->room_id;
    for (int k = 0; k < 3; k++) {
        plant(pPL);
        __builtin_memset(g_trm_mem, 0, sizeof(g_trm_mem));
        g_trm.texId = (u8) (0xF8 + k);
        g_trm_on = k == 1;
        pG->room_id = k == 2 ? room : 0x224;
        g_in = 1;
        em2bTexrenderInit(g_gi);
        g_in = 0;
        pG->room_id = room;
        char tag[8] = {'T', 'X', (char) ('0' + k), 0};
        log_setup(t, tag);
    }
    g_trm_on = 0;
    g_setup_em = 0;
}
}   // namespace

// ---- the room's thunder (r119_ThunderMove and its two light callbacks; native: services/boss/r119_thunder.cpp) ----
// The task runs as a coroutine from tick 30, resumed once a tick (SceSleep yields back). Its interval draws are answered
// from this file's own stream in both builds (svc/svc.mk renames the original's Rnd and the engine's eng_pres_u8 to
// e2c_thunder_rnd in the exercise's copies: in the image the engine draws from the presentation generator, the original
// drew from the behaviour generator), so the timer's logic is compared, not the generators. Every 7th tick from 33 the
// callbacks the task registered are called with the effect tool in state 0, 1 or 2, on a planted light table.
extern "C" {
void r119_task_orig(void) asm("_ZL16r119_ThunderMovev");
void e2c_co_start(void (*fn)());   // svc/e2c_co.cpp (PC side)
void e2c_co_resume();
void e2c_co_yield();
}
namespace {
unsigned g_th_wake;
int g_th_started;
u32 g_th_lcg = 4242u;
void (*g_th_on)();
void (*g_th_off)();
u8 g_tool;
void ex_thunder(unsigned t)
{
    if (!g_th_started) {
        e2c_co_start(r119_task_orig);
        g_th_started = 1;
        g_th_wake = t;
    }
    if (t >= g_th_wake) {
        g_in = 1;
        e2c_co_resume();
        g_in = 0;
    }
    if (t >= 33 && t % 7 == 5 && g_th_on && g_th_off) {
        alignas(32) static u8 lights[8 * sizeof(cLight)];
        __builtin_memset(lights, 0, sizeof(lights));
        void* const keep_a = LightMgr.pArray;
        const u32 keep_n = LightMgr.nArray, keep_s = LightMgr.size;
        LightMgr.pArray = (cLight*) lights, LightMgr.nArray = 8, LightMgr.size = sizeof(cLight);
        g_tool = (u8) (t % 3);
        g_in = 1;
        g_th_on();
        const f32 a2 = LightMgr.getWorkPtr(2)->Intensity, a6 = LightMgr.getWorkPtr(6)->Intensity;
        g_th_off();
        g_in = 0;
        P(g_f, "%u TL %u %08x %08x %08x %08x\n", t, g_tool, bits(a2), bits(a6), bits(LightMgr.getWorkPtr(2)->Intensity),
          bits(LightMgr.getWorkPtr(6)->Intensity));
        LightMgr.pArray = (cLight*) keep_a, LightMgr.nArray = keep_n, LightMgr.size = keep_s;
    }
}
}   // namespace
extern "C" void SceSleep(int frames)
{
    if (g_f) P(g_f, "%u TS %d\n", g_tick, frames);
    g_th_wake = g_tick + (frames > 0 ? frames : 1);
    e2c_co_yield();
}
extern "C" unsigned char e2c_thunder_rnd()
{
    g_th_lcg = g_th_lcg * 1103515245u + 12345u;
    const unsigned char r = (unsigned char) (g_th_lcg >> 16);
    if (g_f) P(g_f, "%u TD %u\n", g_tick, r);
    return r;
}
extern "C" void SceSndCallThunder()
{
    if (g_f) P(g_f, "%u TN\n", g_tick);
}
extern "C" void EffSetToolStateCallBack(int no, void (*on)(), void (*off)())
{
    g_th_on = on, g_th_off = off;
    if (g_f) P(g_f, "%u TC %d %d %d\n", g_tick, no, on != 0, off != 0);
}
extern "C" u8 EffGetToolState() { return g_tool; }

extern "C" void e2c_ready()
{
    const char* e = svc_env("RE4_SVC_EXERCISE");
    g_ex = e && !__builtin_strcmp(e, "e2cboss");
    if (!g_ex) return;
    g_f = svc_out_open("e2c.txt", "w");
    if (&boss_control) {
        const char* c = svc_env("RE4_SVC_CONTROL");
        if (c && !__builtin_strcmp(c, "bosscam")) boss_control = 1;
        if (c && !__builtin_strcmp(c, "bossquake")) boss_control = 2;
        if (c && !__builtin_strcmp(c, "bossneck")) boss_control = 3;
        if (c && !__builtin_strcmp(c, "bossblend")) boss_control = 4;
        if (c && !__builtin_strcmp(c, "bossheld")) boss_control = 5;
        if (c && !__builtin_strcmp(c, "bossoba")) boss_control = 6;
        if (c && !__builtin_strcmp(c, "bosspush")) boss_control = 7;
        if (c && !__builtin_strcmp(c, "bossrope")) boss_control = 8;
        if (c && !__builtin_strcmp(c, "bossthunder")) boss_control = 9;
    }
    g_kind_ok = !ObjInitFunc[kTestKind];
    if (g_kind_ok) ObjInitFunc[kTestKind] = test_obj_init;
}
extern "C" void e2c_tick(unsigned t, int begin)
{
    g_tick = t;
    if (!g_ex || !g_f || !pPL) return;
    if (!begin) {
        if (t >= 45 && t % 9 == 0) ex_squash(t);
        return;
    }
    if (t >= 30 && t % 3 == 0) {
        P(g_f, "# e2cboss presentation %u\n", t);
        ex_cameras(t);
        ex_quake(t);
        ex_feet(t);
    }
    if (t >= 30) {
        P(g_f, "# e2cboss view %u\n", t);
        ex_screen(t);
    }
    if (t >= 31 && t % 3 == 1) {
        P(g_f, "# e2cboss skeleton %u\n", t);
        ex_neck(t);
        ex_blend(t);
    }
    if (t >= 100 && t % 50 == 0) {
        P(g_f, "# e2cboss lifetime %u\n", t);
        ex_life(t);
    }
    if (t == 40) {
        P(g_f, "# e2cboss object %u\n", t);
        ex_oba_make(t);
    }
    if (t > 40) ex_oba_log(t);
    if (t >= 35 && t % 10 == 5) {
        P(g_f, "# e2cboss push %u\n", t);
        ex_push(t);
    }
    if (t % 100 == 36) {
        P(g_f, "# e2cboss set-up %u\n", t);
        ex_setup(t);
    }
    if (t >= 30) ex_thunder(t);
}
extern "C" void e2c_finish()
{
    if (!g_f) return;
    svc_out_close(g_f);
    g_f = 0;
}
