// svc4_dump.cpp (game side; lane eng-svc4): the boundary log of the round-4 native services, linked into odump (the
// original units) and native (the engine bodies) alike. RE4_SVC_OUT=<dir> receives svc4.txt: every call the behaviour
// makes to a service entry point (--wrap: svc4.mk SVC4_WRAP), in call order, with its tick, inputs and outputs as
// float bits. Only top-level calls are logged: not those made inside another logged call or inside a collision query
// (svc_dump.cpp's depth), so both builds log the same boundary whatever their internals call. svc_compare.py's
// companion svc4_compare.py compares the two logs line by line; svc4.txt's last lines are the native counters.
#include "hostref.h"
#include "model.h"
#include "em.h"
#include "obj.h"
#include "atari.h"
#include "at_sub.h"
#include "at_mod.h"
#include "../../services/volumes/volumes.h"
#include "../../services/collision/col_model.h"
#include "../../services/routes/routes.h"
#include "route_ck.h"
#include "cMotBase.h"
#include "../../services/motion/follow.h"
#include "player.h"
#include "../../services/model/model_svc.h"
#include "../../services/camera/camera_svc.h"
#include "../../services/input/input.h"
#include "pad.h"
#include "joy.h"
#include "main.h"
#include "camera.h"
#include "cam_ctrl.h"
#include "cam_extra.h"
#include "cam_motion.h"
#include "view.h"
#include "motion.h"

extern "C" {
void* svc_out_open(const char* name, const char* mode);
void svc_out_printf(void* f, const char* fmt, ...);
void svc_out_close(void* f);
const char* svc_env(const char* name);
int svc_col_depth(void);
extern VolCounters vol_cnt __attribute__((weak));
extern int vol_control __attribute__((weak));
extern ColModelCounters colm_cnt __attribute__((weak));
extern int colm_control __attribute__((weak));
extern RouteCounters route_cnt __attribute__((weak));
extern int route_control __attribute__((weak));
extern FollowCounters follow_cnt __attribute__((weak));
extern int follow_control __attribute__((weak));
extern ModelCounters model_cnt __attribute__((weak));
extern int model_control __attribute__((weak));
extern u32 eng_pool_full __attribute__((weak));
extern CameraCounters cam_cnt __attribute__((weak));
extern int cam_control __attribute__((weak));
extern InputCounters input_cnt __attribute__((weak));
extern int input_control __attribute__((weak));
}
#define P svc_out_printf

namespace {
void* g_f;
void* g_cam;   // lane eng-e1j: cam.txt, the frame's camera once a CameraMove (svc/camcheck.py)
unsigned g_tick;
int g_depth;
// lane eng-e1j: 1 while CameraMove runs; a line logged then has its tick token marked "c" (svc4_compare --camera-tol)
int g_in_cam;
u32 bits(f32 f)
{
    u32 u;
    __builtin_memcpy(&u, &f, 4);
    return u;
}
void pv(const Vec* v)
{
    if (v) P(g_f, " %08x,%08x,%08x", bits(v->x), bits(v->y), bits(v->z));
    else P(g_f, " -");
}
u32 actor(const void* m)
{
    const u32 a = (u32) m, elo = (u32) EmMgr.pArray, olo = (u32) ObjMgr.pArray;
    if (a >= elo && a < elo + EmMgr.size * EmMgr.nArray) return (a - elo) / EmMgr.size;
    if (a >= olo && a < olo + ObjMgr.size * ObjMgr.nArray) return 64 + (a - olo) / ObjMgr.size;
    return 999;
}
// every alive body: model position and body position, folded (pushes move other actors than the caller)
u32 bodies()
{
    u32 h = 2166136261u;
    auto mix = [&](u32 w) { h = (h ^ w) * 16777619u; };
    for (int l = 0; l < 2; l++)
        for (cEm* e = l ? (cEm*) ObjMgr.pAlive : (cEm*) EmMgr.pAlive; e; e = (cEm*) e->pNext) {
            mix(actor(e));
            mix(bits(e->pos.x)), mix(bits(e->pos.y)), mix(bits(e->pos.z));
            mix(bits(e->atari.m_Pos.x)), mix(bits(e->atari.m_Pos.y)), mix(bits(e->atari.m_Pos.z));
            mix(e->atari.m_stat);
        }
    return h;
}
void body(const cAtariInfo* a)
{
    P(g_f, " %08x %08x %08x %08x %x %x %x", bits(a->m_radius), bits(a->m_radius2), bits(a->m_radius_n), bits(a->m_radius2_n),
      a->m_hokan, a->m_flag, a->m_stat);
}
}   // namespace

extern "C" void svc4_ready()
{
    g_f = svc_out_open("svc4.txt", "w");
    if (&vol_control) {
        const char* c = svc_env("RE4_SVC_CONTROL");
        if (c && !__builtin_strcmp(c, "volpush")) vol_control = 1;
        if (c && !__builtin_strcmp(c, "volline")) vol_control = 2;
    }
    if (&colm_control) {
        const char* c = svc_env("RE4_SVC_CONTROL");
        if (c && !__builtin_strcmp(c, "colfloor")) colm_control = 1;
        if (c && !__builtin_strcmp(c, "colwall")) colm_control = 2;
    }
    if (&route_control) {
        const char* c = svc_env("RE4_SVC_CONTROL");
        if (c && !__builtin_strcmp(c, "routenear")) route_control = 1;
        if (c && !__builtin_strcmp(c, "routehop")) route_control = 2;
    }
    if (&follow_control) {
        const char* c = svc_env("RE4_SVC_CONTROL");
        if (c && !__builtin_strcmp(c, "followslow")) follow_control = 1;
    }
    if (&model_control) {
        const char* c = svc_env("RE4_SVC_CONTROL");
        if (c && !__builtin_strcmp(c, "modelslot")) model_control = 1;
    }
    if (&cam_control) {
        const char* c = svc_env("RE4_SVC_CONTROL");
        if (c && !__builtin_strcmp(c, "camfov")) cam_control = 1;
        if (c && !__builtin_strcmp(c, "camroll")) cam_control = 2;
        // lane eng-e1j: the camera check's controls (svc/camcheck.py must fail each)
        if (c && !__builtin_strcmp(c, "camsmooth")) cam_control = 3;
        if (c && !__builtin_strcmp(c, "caminterp")) cam_control = 4;
        if (c && !__builtin_strcmp(c, "camrail")) cam_control = 5;
    }
    g_cam = svc_out_open("cam.txt", "w");
    if (&input_control) {
        const char* c = svc_env("RE4_SVC_CONTROL");
        if (c && !__builtin_strcmp(c, "padstick")) input_control = 1;
        if (c && !__builtin_strcmp(c, "rumblernd")) input_control = 2;
    }
}
// Service exercises (RE4_SVC_EXERCISE=<name>): inputs that drive a service the fixtures' play does not reach, made at
// the start of a tick from this file, so the reference and the native build get the same calls. They change the play;
// the comparison stays reference against native on the same inputs.
//   follow: Leon's root-motion follower (cMotBase, started by ledge climbs, fence vaults and falls, which no fixture
//           has): tick 40 a 10-tick blend onto a pose 250 units off and 0.5 rad turned, tick 100 a pin (count 0)
//           released at tick 130, tick 200 a 25-tick blend.
//   camtrack: the keyed camera tracks and the rail spline, which no fixture reaches (cutscene cameras, rail areas):
//           tick 10 two rail cuts around Leon (5 keys every 30 frames; 5 keys at uneven frames) are exported as camera
//           motion files (HermiteExport) and a CameraMotion is bound to each (one looping); every tick after, both
//           tracks move and one track's keys are evaluated directly at a sweeping frame, alternately searching
//           forwards, backwards and looping. The rail fit and evaluation (Parametrize, BSpline) are not exercised:
//           their de Boor-Cox basis allocates from the debug heap, which re4ref does not provide.
namespace {
int g_exercise = -1;
unsigned g_ex_tick = ~0u;
Vec g_cut_pos[5], g_cut_at[5];
f32 g_cut_roll[5], g_cut_fovy[5];
u16 g_cut_frames[5] = {0, 20, 70, 90, 150};
CameraCut g_cut[2];
alignas(8) u8 g_cmfile[2][0x440];
alignas(8) u8 g_cmobj[2][sizeof(CameraMotion)];
CameraMotion* g_cm[2];
u16 g_hist[3];
void exercise_camtrack(unsigned t)
{
    if (t == 10) {
        for (int k = 0; k < 5; k++) {
            g_cut_pos[k] = pPL->pos;
            g_cut_pos[k].x += 800.0f * k - 1600.0f;
            g_cut_pos[k].y += 1500.0f + 100.0f * (k & 1);
            g_cut_pos[k].z -= 2500.0f - 300.0f * k;
            g_cut_at[k] = pPL->pos;
            g_cut_at[k].y += 1000.0f;
            g_cut_at[k].x += 50.0f * k;
            g_cut_roll[k] = 0.05f * (k - 2);
            g_cut_fovy[k] = 40.0f + 5.0f * k;
        }
        for (int c = 0; c < 2; c++) {
            __builtin_memset(&g_cut[c], 0, sizeof(CameraCut));
            g_cut[c].num = 5;
            g_cut[c].pos = g_cut_pos;
            g_cut[c].at = g_cut_at;
            g_cut[c].roll = g_cut_roll;
            g_cut[c].fovy = g_cut_fovy;
            g_cut[c].frames = c ? g_cut_frames : 0;
            CamCtrl.HermiteExport(&g_cut[c], g_cmfile[c]);
            g_cm[c] = new (g_cmobj[c]) CameraMotion(g_cmfile[c], 0, c ? 4 : 0, 0.0f);
        }
        return;
    }
    if (t < 10 || !g_cm[0]) return;
    for (int c = 0; c < 2; c++) {
        g_cm[c]->CameraMotion::move();
    }
    HermitePrm prm;
    prm.frame = (f32) ((t * 7) % 140);
    prm.maxFrame = 121.0f;
    prm.flags = t % 3 == 0 ? 1 : t % 3 == 1 ? 0 : 4;
    prm.type = 0;
    prm.key = (u8*) g_cm[0]->m_info.keyTbl[0];   // track 0 (pos), relocated by the binding
    Vec v;
    HermiteInterpolation(&prm, &v, g_hist);
}
//   rumble: random-strength rumble (type bit 15), which no fixture starts: rumble switched on (pSys->flags 0x08000000),
//           then every 40 ticks from tick 20 a 30-tick random-strength rumble and a 12-tick constant one. Its strength
//           is presentation: the behaviour must not change (control rumblernd draws it from Rnd and must fail).
void exercise_rumble(unsigned t)
{
    if (t < 20 || (t - 20) % 40 != 0) return;
    pSys->flags |= 0x08000000;
    VibSet(30, 0xC0, 0, 0x8001);
    VibSet(12, 0x40, 4, 0x0002);
}
// Lane eng-e1j: the camera check's exercises (the fixtures' play has no cut blend and no rail):
//   camblend: ticks 100 and 300, a 30-tick cut blend from a camera 600 units above and 400 to the side of the current
//             one (CamCtrl.interp.set, as a cut switch with a blend record sets it): the frame's camera blends back.
//   camrail:  tick 10 a 6-key rail cut around Leon (uneven key spacing, roll and fov changing); every tick after, the
//             rail fitted (Parametrize, tick 10 and every 50th), searched for the point nearest Leon's aim (searchRail)
//             and evaluated (BSpline), the result written to cam.txt as an "R" line.
CameraBSpline g_bs;
Vec g_rail_pos[6], g_rail_at[6];
f32 g_rail_roll[6], g_rail_fovy[6];
CameraCut g_rail;
void exercise_camblend(unsigned t)
{
    if (t != 100 && t != 300) return;
    CameraParam p = CamCtrl.camera.param;
    p.pos.y += 600.0f;
    p.pos.x += 400.0f;
    p.fovy += 10.0f;
    CamCtrl.interp.set(30, &p);
}
void exercise_camrail(unsigned t)
{
    if (t < 10) return;
    if (t == 10) {
        static const f32 dx[6] = {-2400.0f, -1500.0f, -700.0f, 200.0f, 1300.0f, 2500.0f};
        for (int k = 0; k < 6; k++) {
            g_rail_pos[k] = pPL->pos;
            g_rail_pos[k].x += dx[k];
            g_rail_pos[k].y += 1800.0f + 150.0f * (k % 3);
            g_rail_pos[k].z -= 2200.0f - 250.0f * k;
            g_rail_at[k] = pPL->pos;
            g_rail_at[k].x += 0.6f * dx[k];
            g_rail_at[k].y += 900.0f + 40.0f * k;
            g_rail_at[k].z += 100.0f * (k & 1);
            g_rail_roll[k] = 0.03f * (k - 3);
            g_rail_fovy[k] = 45.0f + 3.0f * k;
        }
        __builtin_memset(&g_rail, 0, sizeof g_rail);
        g_rail.num = 6;
        g_rail.pos = g_rail_pos;
        g_rail.at = g_rail_at;
        g_rail.roll = g_rail_roll;
        g_rail.fovy = g_rail_fovy;
    }
    if (t == 10 || t % 50 == 0) Parametrize(&g_rail, &g_bs);
    Vec aim = pPL->pos;
    aim.y += 1000.0f;
    aim.x += 30.0f * (f32) ((int) (t % 160) - 80);   // sweeps the aim along the rail
    searchRail(&g_bs, &g_rail, &aim, 0);
    Camera c;
    BSpline(&g_bs, &c, 0);
    if (g_cam)
        P(g_cam, "R %u %.9g %.9g %.9g %.9g %.9g %.9g %.9g %.9g %d %d %d %d\n", t, c.param.pos.x, c.param.pos.y, c.param.pos.z,
          c.param.at.x, c.param.at.y, c.param.at.z, c.param.roll, c.param.fovy, g_bs.seg, g_bs.k, g_bs.num, 0);
}
void exercise(unsigned t)
{
    if (g_exercise < 0) {
        const char* e = svc_env("RE4_SVC_EXERCISE");
        g_exercise = e && !__builtin_strcmp(e, "follow") ? 1 : e && !__builtin_strcmp(e, "camtrack") ? 2
                   : e && !__builtin_strcmp(e, "rumble") ? 3 : e && !__builtin_strcmp(e, "camblend") ? 4
                   : e && !__builtin_strcmp(e, "camrail") ? 5 : 0;
    }
    if (g_exercise == 4 || g_exercise == 5) {
        if (t != g_ex_tick && pPL) {
            g_ex_tick = t;
            if (g_exercise == 4) exercise_camblend(t);
            else exercise_camrail(t);
        }
        return;
    }
    if (g_exercise == 3) {
        if (t != g_ex_tick) {
            g_ex_tick = t;
            exercise_rumble(t);
        }
        return;
    }
    if (g_exercise == 2) {
        if (t != g_ex_tick && pPL) {
            g_ex_tick = t;
            exercise_camtrack(t);
        }
        return;
    }
    if (!g_exercise || t == g_ex_tick || !pPL || !pPL->MotBase) return;
    g_ex_tick = t;
    cMotModel* m = (cMotModel*) (cModel*) pPL;
    Vec p = pPL->pos, r = pPL->ang;
    switch (t) {
    case 40: p.x += 200.0f, p.z -= 150.0f, r.y += 0.5f; pPL->MotBase->set(m, &p, &r, 10); break;
    case 100: pPL->MotBase->set(m, &p, &r, 0); break;
    case 130: pPL->MotBase->cnt = 0xFF; m->Motion.Mot_attr |= 1; break;
    case 200: p.x -= 300.0f, p.z += 100.0f, r.y -= 0.8f; pPL->MotBase->set(m, &p, &r, 25); break;
    }
}
}   // namespace
extern "C" void svc4_tick(unsigned t)
{
    g_tick = t;
    // lane eng-e1j: control pos005 (svc_controls.sh): Leon's model 0.005 unit along x at tick 100, every bone with it;
    // the reference-against-native rows (camera lines loosened only) must still FAIL on it
    static int pos005 = -1;
    if (pos005 < 0) {
        const char* c = svc_env("RE4_SVC_CONTROL");
        pos005 = c && !__builtin_strcmp(c, "pos005");
    }
    if (pos005 && t == 100 && pPL) pPL->pos.x += 0.005f;
    exercise(t);
}
extern "C" void svc4_finish()
{
    if (!g_f) return;
    if (&vol_cnt) {
        const VolCounters& v = vol_cnt;
        P(g_f, "# volumes: at_checks %u at_skipped %u pairs %u pairs_prio %u pushes %u pairs_box %u line_tests %u line_bodies %u line_hits %u "
               "capsule_tests %u box_sphere %u debug_draws %u\n",
          v.at_checks, v.at_skipped, v.pairs, v.pairs_prio, v.pushes, v.pairs_box, v.line_tests, v.line_bodies, v.line_hits,
          v.capsule_tests, v.box_sphere, v.debug_draws);
    }
    if (&colm_cnt) {
        const ColModelCounters& c = colm_cnt;
        P(g_f, "# collision response: checks %u rects %u spheres %u slides %u floors %u floor_lost %u pieces %u debug_draws %u\n",
          c.checks, c.rects, c.spheres, c.slides, c.floors, c.floor_lost, c.pieces, c.debug_draws);
    }
    if (&route_cnt) {
        const RouteCounters& r = route_cnt;
        P(g_f, "# routes: near_calls %u near_cached %u near_lines %u near_none %u steps %u steps_direct %u lines %u dists %u debug_draws %u\n",
          r.near_calls, r.near_cached, r.near_lines, r.near_none, r.steps, r.steps_direct, r.lines, r.dists, r.debug_draws);
    }
    if (&follow_cnt) {
        const FollowCounters& f = follow_cnt;
        P(g_f, "# root-motion follower: sets %u moves %u blends %u pins %u ends %u adjusts %u\n", f.sets, f.moves, f.blends, f.pins, f.ends,
          f.adjusts);
    }
    if (&model_cnt) {
        const ModelCounters& m = model_cnt;
        P(g_f, "# models: inits %u infos %u parts_runs %u parts_single %u parts_made %u relocs %u debug_draws %u; pools full %u\n",
          m.inits, m.infos, m.parts_runs, m.parts_single, m.parts_made, m.relocs, m.debug_draws, &eng_pool_full ? eng_pool_full : 0);
    }
    if (&cam_cnt) {
        const CameraCounters& c = cam_cnt;
        P(g_f, "# camera: frames %u frustums %u orients %u orient_cams %u tracks %u keys %u key_errors %u attached %u rails %u "
               "projections %u debug_draws %u blends %u smooths %u areas %u probes %u shoulder %u\n", c.frames, c.frustums,
          c.orients, c.orient_cams, c.tracks, c.keys, c.key_errors, c.attached, c.rails, c.projections, c.debug_draws, c.blends,
          c.smooths, c.areas, c.probes, c.shoulder);
    }
    if (g_cam) {
        svc_out_close(g_cam);
        g_cam = 0;
    }
    if (&input_cnt) {
        const InputCounters& n = input_cnt;
        P(g_f, "# input: reads %u vib_ticks %u vib_random %u vib_queued %u motor_changes %u debug_prints %u\n", n.reads,
          n.vib_ticks, n.vib_random, n.vib_queued, n.motor_changes, n.debug_prints);
    }
    svc_out_close(g_f);
    g_f = 0;
}

#define TOP (g_depth == 0 && svc_col_depth() == 0 && g_f)
#define W(ret, mangled, params, args, log_in, log_out)                                                               \
    extern "C" ret __real_##mangled params;                                                                          \
    extern "C" ret __wrap_##mangled params                                                                           \
    {                                                                                                                \
        const bool top = TOP;                                                                                        \
        if (top) { P(g_f, g_in_cam ? "c%u" : "%u", g_tick); log_in; }                                                                  \
        g_depth++;                                                                                                   \
        ret r = __real_##mangled args;                                                                               \
        g_depth--;                                                                                                   \
        if (top) { P(g_f, " ->"); log_out; P(g_f, "\n"); }                                                          \
        return r;                                                                                                    \
    }
#define WV(mangled, params, args, log_in, log_out)                                                                   \
    extern "C" void __real_##mangled params;                                                                         \
    extern "C" void __wrap_##mangled params                                                                          \
    {                                                                                                                \
        const bool top = TOP;                                                                                        \
        if (top) { P(g_f, g_in_cam ? "c%u" : "%u", g_tick); log_in; }                                                                  \
        g_depth++;                                                                                                   \
        __real_##mangled args;                                                                                       \
        g_depth--;                                                                                                   \
        if (top) { P(g_f, " ->"); log_out; P(g_f, "\n"); }                                                          \
        return;                                                                                                      \
    }

// WT: a transparent wrapper: one line after the call, the calls inside it logged as top-level lines of their own (a
// whole-frame entry point such as CameraMove, whose inner service calls are what is compared)
#define WT(mangled, params, args, log_out)                                                                          \
    extern "C" void __real_##mangled params;                                                                         \
    extern "C" void __wrap_##mangled params                                                                          \
    {                                                                                                                \
        const bool top = TOP;                                                                                        \
        __real_##mangled args;                                                                                       \
        if (top) { P(g_f, "%u", g_tick); log_out; P(g_f, "\n"); }                                                  \
    }

// ---- actor volumes (atariInfo, at_mod, at_sub) ----
WV(EmAtCheck, (cEm* em), (em), { P(g_f, " AT %u", actor(em)); pv(&em->pos); },
   { pv(&em->pos); pv(&em->atari.m_Pos); P(g_f, " %x h%08x", em->atari.m_stat, bodies()); })
W(int, EmHitCheck, (Vec* hit, Vec* nrm, Vec* p0, Vec* p1, int flag), (hit, nrm, p0, p1, flag),
  { P(g_f, " EH"); pv(p0); pv(p1); P(g_f, " %x", flag); }, { P(g_f, " %d", r); pv(hit); if (r) pv(nrm); })
W(int, ObjHitCheck, (Vec* hit, Vec* nrm, Vec* p0, Vec* p1, int flag), (hit, nrm, p0, p1, flag),
  { P(g_f, " OH"); pv(p0); pv(p1); P(g_f, " %x", flag); }, { P(g_f, " %d", r); pv(hit); if (r) pv(nrm); })
W(int, ObaLineHitChk, (cEm* m, cAtariInfo* info, Vec* a, Vec* b, Vec* hit, Vec* nrm), (m, info, a, b, hit, nrm),
  { P(g_f, " OB %u", actor(m)); pv(a); pv(b); }, { P(g_f, " %d", r); if (r) { pv(hit); pv(nrm); } })
W(u32, AtSphereCapsuleCk, (Vec* c, Vec* p0, f32 rad, f32 r2, Vec* p1), (c, p0, rad, r2, p1),
  { P(g_f, " SC"); pv(c); pv(p0); pv(p1); P(g_f, " %08x %08x", bits(rad), bits(r2)); }, { P(g_f, " %u", r); })
W(u32, AtBoxCapsuleCk3, (Vec* box, Vec* p0, f32 rr, Vec* p1), (box, p0, rr, p1),
  { P(g_f, " BC"); for (int i = 0; i < 8; i++) pv(&box[i]); pv(p0); pv(p1); P(g_f, " %08x", bits(rr)); }, { P(g_f, " %u", r); })
W(int, At_box_sphere_ck, (Vec* box, Vec* p, f32 rr), (box, p, rr),
  { P(g_f, " BS"); for (int i = 0; i < 8; i++) pv(&box[i]); pv(p); P(g_f, " %08x", bits(rr)); }, { P(g_f, " %d", r); })
// ---- per-model collision response (atari): check / checkAir / getFloor are logged by svc_dump.cpp (col.txt) ----
extern "C" AtEffInfo* __real__ZN7cEatMgr10getEffInfoEi(cEatMgr* e, int type);
extern "C" AtEffInfo* __wrap__ZN7cEatMgr10getEffInfoEi(cEatMgr* e, int type)
{
    const bool top = TOP;
    AtEffInfo* r = __real__ZN7cEatMgr10getEffInfoEi(e, type);
    if (top) P(g_f, "%u EI %d -> %d %x\n", g_tick, type, r != 0, r ? r->flag : 0);
    return r;
}
W(int, EatGetEffectType, (u32 attr), (attr), { P(g_f, " ET %x", attr); }, { P(g_f, " %d", r); })
W(u32, At_poly_line_ck, (AtPolyData* pd, Vec* out, AtPoly* poly, Vec* v0, Vec* v1, u32 flag, u32 mask),
  (pd, out, poly, v0, v1, flag, mask), { P(g_f, " PL %x", (u32) poly); pv(v0); pv(v1); P(g_f, " %x %x", flag, mask); },
  { P(g_f, " %x", r); if (r) pv(out); })
WV(YarareInit, (cEm* em, f32 x, f32 y, f32 z, f32 w, f32 h, s16 no, u16 flags), (em, x, y, z, w, h, no, flags),
   { P(g_f, " YI %u %08x %08x %08x %08x %08x %d %x", actor(em), bits(x), bits(y), bits(z), bits(w), bits(h), no, flags); }, {})
WV(YarareAdd, (cEm* em, YARARE_INFO* box, f32 x, f32 y, f32 z, f32 w, f32 h, s16 no, u16 flags),
   (em, box, x, y, z, w, h, no, flags),
   { P(g_f, " YA %u %d %08x %08x %08x %08x %08x %d %x", actor(em), (int) ((char*) box - (char*) em), bits(x), bits(y), bits(z), bits(w),
       bits(h), no, flags); },
   { int n = 0; for (YARARE_INFO* p = &em->hitInfo; p; p = p->next) n++; P(g_f, " chain %d", n); })
WV(_ZN10cAtariInfo4moveEv, (cAtariInfo* a), (a), { P(g_f, " AM %u", actor(a->m_pMod)); body(a); }, { body(a); })
WV(_ZN10cAtariInfo3setEiff, (cAtariInfo* a, int mode, f32 x, f32 y), (a, mode, x, y),
   { P(g_f, " AS %d %08x %08x", mode, bits(x), bits(y)); body(a); }, { body(a); })
WV(_ZN10cAtariInfo11setPriorityEi, (cAtariInfo* a, int prio), (a, prio), { P(g_f, " AP %d %x", prio, a->m_flag); }, { P(g_f, " %x", a->m_flag); })
WV(_ZN10cAtariInfo6getPosEP6cModelP3Vec, (cAtariInfo* a, cModel* m, Vec* out), (a, m, out), { P(g_f, " AG %u", actor(m)); },
   { pv(out); })
WV(_ZN10cAtariInfo14getSpeedVectorEP6cModelP3VecS3_, (cAtariInfo* a, cModel* m, Vec* o, Vec* n), (a, m, o, n),
   { P(g_f, " AV %u", actor(m)); }, { pv(o); pv(n); })
// ---- routes (route_ck) ----
namespace {
void rck(const cEm* e) { P(g_f, " rck %x %d %d %d", e->RckStat, e->RckMy, e->RckTo, e->RckNear); }
}
W(int, RouteCkToPos, (cEm* em, Vec* t, Vec* out, int flag, f32* dist), (em, t, out, flag, dist),
  { P(g_f, " RP %u", actor(em)); pv(&em->pos); pv(t); P(g_f, " %x %d", flag, dist != 0); },
  { P(g_f, " %d", r); pv(out); if (dist) P(g_f, " %08x", bits(*dist)); rck(em); })
W(int, RouteCkToEm, (cEm* em, cEm* t, Vec* out, int flag), (em, t, out, flag),
  { P(g_f, " RE %u %u", actor(em), actor(t)); pv(&em->pos); pv(&t->pos); P(g_f, " %x", flag); },
  { P(g_f, " %d", r); pv(out); rck(em); rck(t); })
WV(RouteCkEscEm, (cEm* em, cEm* from, Vec* out), (em, from, out), { P(g_f, " RX %u %u", actor(em), actor(from)); },
   { pv(out); rck(em); })
W(int, RouteCkPosToPos, (Vec* a, Vec* b, Vec* out), (a, b, out), { P(g_f, " RQ"); pv(a); pv(b); }, { P(g_f, " %d", r); pv(out); })
W(f32, RouteCkPosToPosDis, (Vec* a, Vec* b), (a, b), { P(g_f, " RD"); pv(a); pv(b); }, { P(g_f, " %08x", bits(r)); })
W(f32, RouteCkGetDist, (int a, int b), (a, b), { P(g_f, " RG %d %d", a, b); }, { P(g_f, " %08x", bits(r)); })
W(int, RouteCkConnectPosCk, (Vec* a, Vec* b), (a, b), { P(g_f, " RC"); pv(a); pv(b); }, { P(g_f, " %d", r); })
W(s8, getNearPoint, (Vec* pos, int mode, int mask), (pos, mode, mask), { P(g_f, " NP"); pv(pos); P(g_f, " %d %x", mode, mask); },
  { P(g_f, " %d", r); })
W(int, getNearInfo, (cEm* em, int mode, int mask), (em, mode, mask), { P(g_f, " NI %u", actor(em)); P(g_f, " %d %x", mode, mask); },
  { P(g_f, " %d", r); rck(em); })
WV(RouteCk, (), (), { P(g_f, " RK"); }, {})
// ---- root-motion follower (cMotBase) ----
namespace {
void mb(const cMotBase* b)
{
    P(g_f, " %x", b->cnt);
    pv(&b->pos);
    pv(&b->ang);
    if (b->pModel) { pv(&b->pModel->pos); pv(&b->pModel->ang); P(g_f, " %x", b->pModel->Motion.Mot_attr); }
}
}
WV(_ZN8cMotBase4moveEv, (cMotBase* b), (b), { P(g_f, " MB %u", actor(b->pModel)); mb(b); }, { mb(b); })
WV(_ZN8cMotBase6adjustEv, (cMotBase* b), (b), { P(g_f, " MJ %u", actor(b->pModel)); mb(b); }, { mb(b); })
WV(_ZN8cMotBase3setEP9cMotModelP3VecS3_h, (cMotBase* b, cMotModel* m, Vec* p, Vec* r, u8 c), (b, m, p, r, c),
   { P(g_f, " MS %u", actor(m)); pv(p); pv(r); P(g_f, " %x", c); }, { mb(b); })
// ---- models (model.cpp: the record, the model-data chain, the pools) ----
namespace {
// the model's record as the service leaves it: flags, parts (count, run flag, every part's pointer and parent folded),
// the model-info chain (pointers, data, flags), the motion tables
void md(const cModel* m)
{
    u32 h = 2166136261u;
    auto mix = [&](u32 w) { h = (h ^ w) * 16777619u; };
    int np = 0;
    for (cParts* p = m->pList; p && np < 300; p = p->pList, np++) mix((u32) p), mix((u32) p->pParent), mix(p->be_flag);
    int ni = 0;
    for (cModelInfo* i = m->pModelInfo; i && ni < 50; i = i->pList, ni++)
        mix((u32) i), mix((u32) i->pData), mix((u32) i->tpl_addr), mix(i->be_flag), mix(bits(i->bound.size.x)),
            mix(bits(i->bound.center.y));
    // a motion table in the arena by address; one in the program's own data (a default table) as "img": the two
    // builds are different programs, so their data addresses differ
    auto tbl = [](const void* t) { return (u32) t >= 0x8C000000u && (u32) t < 0x8D000000u ? (u32) t : (t ? 1u : 0u); };
    P(g_f, " %x %d/%d %d %08x %08x %x %x", m->be_flag, m->nParts, np, ni, h, bits(m->invisible_factor), tbl(m->Motion.blendTbl),
      tbl(m->Motion.flip));
}
}
W(int, _ZN6cModel9modelInitEPvS0_, (cModel* m, void* bin, void* tpl), (m, bin, tpl), { P(g_f, " MI %u %x %x", actor(m), (u32) bin, (u32) tpl); },
  { P(g_f, " %x", (u32) r); md(m); })
W(int, _ZN6cModel9initJointEPv, (cModel* m, void* bin), (m, bin), { P(g_f, " MJ %u %x", actor(m), (u32) bin); }, { P(g_f, " %d", r); md(m); })
W(int, _ZN6cModel13makePartsListEi, (cModel* m, int n), (m, n), { P(g_f, " ML %u %d", actor(m), n); }, { P(g_f, " %d", r); md(m); })
WV(_ZN6cModel4pushEv, (cModel* m), (m), { P(g_f, " MP %u", actor(m)); }, { md(m); })
WV(_ZN6cModel8addModelEP10cModelInfo, (cModel* m, cModelInfo* i), (m, i), { P(g_f, " MA %u %x", actor(m), (u32) i); }, { md(m); })
W(int, _ZN6cModel15deleteModelInfoEP10cModelInfo, (cModel* m, cModelInfo* i), (m, i), { P(g_f, " MD %u %x", actor(m), (u32) i); },
  { P(g_f, " %d", r); md(m); })
W(int, _ZN6cModel13swapModelInfoEP9ModelDataP10cModelInfo, (cModel* m, ModelData* d, cModelInfo* i), (m, d, i),
  { P(g_f, " MW %u %x %x", actor(m), (u32) d, (u32) i); }, { P(g_f, " %d", r); md(m); })
W(cModelInfo*, _ZN11cModInfoMgr6createEPvS0_, (cModInfoMgr* mg, void* bin, void* tpl), (mg, bin, tpl),
  { P(g_f, " MC %x %x", (u32) bin, (u32) tpl); },
  { P(g_f, " %x", (u32) r); if (r) P(g_f, " %x %08x %08x %08x", r->be_flag, bits(r->bound.size.x), bits(r->bound.size.y), bits(r->bound.center.z)); })
WV(ModelInfoSetTrans, (cModel* m, int no, int on), (m, no, on), { P(g_f, " MT %u %d %d", actor(m), no, on); }, { md(m); })
// ---- camera (view, camera, cam_motion, HermiteInterpolation; cam_ctrl / cam_sys / cam_extra evaluation) ----
namespace {
u32 words(const void* p, u32 bytes)
{
    u32 h = 2166136261u;
    const u8* b = (const u8*) p;
    for (u32 i = 0; i < bytes; i++) h = (h ^ b[i]) * 16777619u;
    return h;
}
void campar(const Camera* c) { pv(&c->param.pos); pv(&c->param.at); P(g_f, " %08x %08x", bits(c->param.roll), bits(c->param.fovy)); }
}
WV(_ZN4VIEW15initPerspectiveEffff, (VIEW* v, f32 fy, f32 a, f32 zn, f32 zf), (v, fy, a, zn, zf),
   { P(g_f, " VP %08x %08x %08x %08x", bits(fy), bits(a), bits(zn), bits(zf)); },
   { P(g_f, " h%08x h%08x", words(&v->localFull, sizeof(ViewFrustum)), words(&v->sphere, sizeof(ViewSphere))); })
// the frame's camera and the frustum it leaves (VIEW::move is not wrapped: in the native build CameraMove calls it
// inside one object, where --wrap does not reach, so the two builds would log it differently)
extern "C" void __real_CameraMove();
extern "C" void __wrap_CameraMove()
{
    const bool top = TOP;
    g_in_cam++;
    __real_CameraMove();
    g_in_cam--;
    if (!top) return;
    P(g_f, "%u CM", g_tick);
    campar(&pG->Cam);
    P(g_f, " h%08x %08x %08x h%08x h%08x h%08x\n", words(&pG->Cam, sizeof(Camera)), bits(View._fovy), bits(View._zfar),
      words(&View.worldFull, sizeof(ViewFrustum)), words(&View.world, sizeof(ViewFrustum)), words(&View.sphereWorld, sizeof(ViewSphere)));
    // lane eng-e1j: the camera check's line: tick, eye, target, roll (radians), fov (degrees) as decimal floats, and the
    // controller's decisions (area, camera cut, routine, cut blend frames left)
    if (g_cam) {
        const Camera& c = pG->Cam;
        P(g_cam, "%u %.9g %.9g %.9g %.9g %.9g %.9g %.9g %.9g %d %d %d %d\n", g_tick, c.param.pos.x, c.param.pos.y, c.param.pos.z,
          c.param.at.x, c.param.at.y, c.param.at.z, c.param.roll, c.param.fovy, CamCtrl.areaNo, CamCtrl.cameraNo, CamCtrl.r0,
          CamCtrl.interp.frame);
    }
}
WV(_ZN12CameraMotion4moveEv, (CameraMotion* c), (c), { P(g_f, " CT %08x", bits(c->m_info.frame)); },
   { campar(c); P(g_f, " %d %u h%08x", c->end, c->m_info.state, words(c->m_info.hist, sizeof(c->m_info.hist))); })
W(int, HermiteInterpolation, (HermitePrm* prm, Vec* out, u16* hist), (prm, out, hist),
  { P(g_f, " HI %08x %08x %x %u %x,%x,%x", bits(prm->frame), bits(prm->maxFrame), prm->flags, prm->type, hist[0], hist[1], hist[2]); },
  { P(g_f, " %d", r); pv(out); P(g_f, " %x,%x,%x", hist[0], hist[1], hist[2]); })
WV(CameraSetOrientationRoll, (Camera* c), (c), { P(g_f, " OR"); campar(c); }, { P(g_f, " h%08x", words(c->mat, sizeof(Mtx))); })
WV(CameraSetOrientationUp, (Camera* c), (c), { P(g_f, " OU"); campar(c); pv(&c->up); }, { P(g_f, " h%08x", words(c->mat, sizeof(Mtx))); })
WV(_ZN22CameraAttachedToMotion4moveEv, (CameraAttachedToMotion* c), (c), { P(g_f, " CA"); }, { campar(c); })
W(int, _ZN13CameraControl13HermiteExportEP9CameraCutPh, (CameraControl* cc, CameraCut* cut, u8* buf), (cc, cut, buf),
  { P(g_f, " HX %d", cut->num); }, { P(g_f, " %d h%08x", r, words(buf, r > 0 && r < 0x10000 ? r : 0)); })
WV(_Z7BSplineP13CameraBSplineP6Camerai, (CameraBSpline* bs, Camera* c, int x), (bs, c, x), { P(g_f, " BS %08x", bits(bs->t)); },
   { campar(c); })
WV(_Z11ParametrizeP9CameraCutP13CameraBSpline, (CameraCut* cut, CameraBSpline* bs), (cut, bs), { P(g_f, " PZ %d", cut->num); },
   { P(g_f, " %d %d h%08x", bs->num, bs->k, words(bs, sizeof(CameraBSpline))); })
// ---- input (pad.cpp) ----
namespace {
u32 joyh()
{
    u32 h = words(&Joy[0].vib, sizeof(Joy[0].vib));
    return h ^ Joy[0].motor_state;
}
}
WT(PadRead, (), (), {
    P(g_f, " PR %x %x %08x%08x %08x%08x %d,%d %08x", Joy[0].on, Joy[0].trg, (u32) (Key.on >> 32), (u32) Key.on, (u32) (Key.rep >> 32),
      (u32) Key.rep, Key.stickX, Key.stickY, joyh());
})
WV(VibSet, (u32 time, u32 level, u16 wait, u16 type), (time, level, wait, type), { P(g_f, " VS %u %u %u %x", time, level, wait, type); },
   { P(g_f, " %08x", joyh()); })
WV(KeyStop, (u64 mask), (mask), { P(g_f, " KS %08x%08x", (u32) (mask >> 32), (u32) mask); },
   { P(g_f, " %08x%08x", (u32) (Key.on >> 32), (u32) Key.on); })
