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
extern "C" u32 __real__Z7SndCallttP3VeciiP5cUnit(u16 blk, u16 no, Vec* p, int id, int a, cUnit* o);
extern "C" u32 __wrap__Z7SndCallttP3VeciiP5cUnit(u16 blk, u16 no, Vec* p, int id, int a, cUnit* o)
{
    if (g_f && g_in) {
        P(g_f, "%u SC %u %u", g_tick, blk, no);
        if (p) pv(p); else P(g_f, " P-");
        P(g_f, " %x %d %u\n", id, a, actor(o));
    }
    return __real__Z7SndCallttP3VeciiP5cUnit(blk, no, p, id, a, o);
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
    }
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
}
extern "C" void e2c_finish()
{
    if (!g_f) return;
    svc_out_close(g_f);
    g_f = 0;
}
