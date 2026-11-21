// em10_cam.cpp (lane eng-e2b, 2026-11-21): the Ganado's cut-in cameras and its on-screen check, native. The grabs, the
// critical hits, the hold on Ashley and the take-away each frame the work's own camera (Em10Work::Cam) for the camera
// service to show as the extra camera (CamCtrl.m_pExtraCamera); em10ScreenInCk asks the view whether the Ganado is on
// screen. The behaviour (em10.cpp's routines) calls these by their original names and keeps its decisions (which shot,
// when, the ease rate, the shake); em10's bodies are weak in the image and the PC reference's native build.
//
// Engine form: one shot routine (cut_in) for every cut-in. A shot is an eye and a target in a frame (the player's or
// the Ganado's), eased from the game camera at a rate, optionally shaken, optionally pulled in front of the scenery
// (the eye kept 250 units clear: the effect collision's line test), then framed (up, distance, field of view) by the
// camera service (CameraSetOrientationUp) and handed to it as the extra camera. The fixed shots are tables. Points
// through a frame are SH4ZAM vectors (camera/cam_math.h); the ease is the math service's PosToPos.
//
// Randomness: the shake is presentation and draws from the engine's presentation generator, three bytes an axis as
// fRand1_1 forms them, in the original's order. em10SetCampos2's side (left or right of the player) draws from the
// behaviour generator, as the original does in both builds today (not in the split list): noted in eng-e2b.md.
#define fabsf em10c_game_fabsf
#include "types.h"
#include "global.h"
#include "model.h"
#include "em.h"
#include "em10.h"
#include "player.h"
#include "camera.h"
#include "cam_ctrl.h"
#include "atari.h"
#include "esp.h"
#include "math_sub.h"
#include "rnd.h"
#undef fabsf
#include "cam_math.h"

extern "C" {
unsigned char eng_pres_u8();
struct Em10CamCounters {
    u32 shots, shakes, wall_pulls, wall_hits, installs, screen_checks;
};
Em10CamCounters em10c_cnt;
// Controls (set only by the PC check, hostref svc/e2b_dump.cpp RE4_SVC_CONTROL; each must make e2b.txt differ):
// 1 "camease": every cut-in eased at 0.9 of its rate; 2 "screenhalf": the screen's right edge at 256.
int em10c_control;

void em10CamMove(cEm10* em, int no, f32 rate, int shake);
void em10CamMoveCri(cEm10* em, u32 no, int shake);
void em10CamMoveAshley(cEm10* em, u32 no);
void em10CamMoveTakeaway(cEm10* em);
void em10SetCampos2(cEm10* em);
int em10ScreenInCk(cEm10* em);
}
void em10CamMove2(cEm10* em);

namespace {
using namespace camsvc;

// a shot: the eye and the target in a frame, and its field of view
struct Shot {
    f32 eye[3], at[3];
    f32 fovy;
};
// the critical hits (em10CamMoveCri): shot 1 and 3 have a second form for regions other than 0
const Shot kCri[5] = {
    {{1716.6f, 3074.7f, 266.8f}, {-124.6f, 748.4f, -23.5f}, 50.0f},
    {{762.0f, 1953.0f, 263.0f}, {-110.0f, 1083.0f, 212.0f}, 50.0f},
    {{120.0f, 1689.9f, 1118.5f}, {9.2f, 1518.8f, -149.1f}, 30.0f},
    {{-1120.0f, 1269.0f, -494.1f}, {-16.0f, 1288.0f, 90.0f}, 50.0f},
    {{-957.6f, 1741.7f, -87.0f}, {104.5f, 1234.5f, 120.06f}, 50.0f},
};
const Shot kCriOtherRegion[5] = {
    kCri[0],
    {{-651.2f, 2688.1f, 147.3f}, {174.0f, 887.6f, -17.1f}, 50.0f},
    kCri[2],
    {{-87.3f, 1451.2f, -543.1f}, {15.6f, 1250.6f, 293.6f}, 50.0f},
    kCri[4],
};
// the hold on Ashley and its throw-off (em10CamMoveAshley)
const Shot kAshley[4] = {
    {{957.0f, 1872.0f, 676.0f}, {-122.0f, 1622.0f, 49.0f}, 50.0f},
    {{-1105.0f, 1590.1884f, -686.0f}, {-114.0f, 1589.0f, 54.0f}, 50.0f},
    {{-1665.0f, 1750.1f, 1387.4f}, {-39.4f, 1339.7f, 376.8f}, 50.0f},
    {{1563.0f, 976.6f, -693.4f}, {-71.6f, 1339.7f, 318.0f}, 50.0f},
};
// the grab's eye beside the player (em10CamMove: 0 behind right, 1 right)
const f32 kGrabEye[2][3] = {{500.0f, 1600.0f, -2000.0f}, {1500.0f, 1600.0f, 500.0f}};
// the take-away (em10CamMoveTakeaway), in the Ganado's frame
const Shot kTakeaway = {{250.0f, 579.0f, -2530.0f}, {0.0f, 1075.0f, 0.0f}, 55.0f};
// the NeckHang throw-off's second eye (em10SetCampos2), beside the Ganado
const f32 kThrowSide = 1300.0f, kThrowHeight = 500.0f;
const f32 kCutinFovy = 55.0f;
const f32 kWallClear = 250.0f;   // the eye kept this far in front of the scenery
const u32 kWallAttr = 0x8000;    // the effect collision's attribute mask for the eye's line
const f32 kNeckHangReach = 1700.0f;

v3 vec3(const f32* p) { return shz_vec3_init(p[0], p[1], p[2]); }
v3 through(const Mtx m, const f32* p) { return frame_point(frame_of(m), vec3(p)); }
v3 head_of(cModel* m) { return V(m->getPartsPtr(4)->world); }
v3 ease(const Vec& from, v3 to, f32 rate)
{
    Vec t, out;
    put(&t, to);
    PosToPos(const_cast<Vec*>(&from), &t, &out, rate);
    return V(out);
}
// one presentation draw as fRand1_1 forms it: [1, 2) from three bytes, then to [-1, 1)
f32 pres_f11()
{
    const unsigned a = eng_pres_u8(), b = eng_pres_u8(), c = eng_pres_u8();
    const unsigned u = a + (b << 8) + ((c & 0x7F) << 16) + 0x3F800000;
    f32 f;
    __builtin_memcpy(&f, &u, 4);
    return f * 2.0f - 3.0f;
}
// the eye pulled in front of the scenery: the line from the target to the eye pushed 250 units on is tested, and the
// eye kept 250 units short of what it meets
v3 clear_of_walls(v3 at, v3 eye)
{
    const v3 d = vsub(eye, at);
    if (!(vlen2(d) > 100.0f)) return eye;
    em10c_cnt.wall_pulls++;
    const v3 push = vscale(vunit(d), kWallClear);
    Vec a, e, hit;
    put(&a, at);
    put(&e, vadd(eye, push));
    v3 far = V(e);
    if (EatMgr.hitCheck(&a, &e, &hit, 0, kWallAttr, 0)) {
        em10c_cnt.wall_hits++;
        far = V(hit);
    }
    return vsub(far, push);
}
// frame the work's camera on (eye, at) and, when asked, hand it to the camera service as the extra camera
void frame(Camera& cam, v3 eye, v3 at, f32 fovy, bool install)
{
    put(&cam.param.pos, eye);
    put(&cam.param.at, at);
    cam.up = Vec{0.0f, 1.0f, 0.0f};
    cam.dist = vdist(eye, at);
    if (fovy > 0.0f) cam.param.fovy = fovy;
    CameraSetOrientationUp(&cam);
    if (install) {
        em10c_cnt.installs++;
        CamCtrl.m_pExtraCamera = (s32) &cam;
    }
}
enum { SHAKE = 1, WALLS = 2, INSTALL = 4 };
// the cut-in: eased from the game camera to (eye, at) at `rate`, shaken, pulled in front of walls, framed
void cut_in(Em10Work* w, v3 eye, v3 at, f32 rate, u32 how, f32 fovy)
{
    em10c_cnt.shots++;
    const Camera& game = pG->Cam;
    if (em10c_control == 1) rate *= 0.9f;
    v3 a = ease(game.param.at, at, rate);
    v3 e = ease(game.param.pos, eye, rate);
    if (how & SHAKE) {
        em10c_cnt.shakes++;
        const f32 x = pres_f11() * 10.0f, y = pres_f11() * 10.0f, z = pres_f11() * 10.0f;
        const v3 s = shz_vec3_init(x, y, z);
        e = vadd(e, s);
        a = vadd(a, s);
    }
    if (how & WALLS) e = clear_of_walls(a, e);
    frame(w->Cam, e, a, fovy, how & INSTALL);
}
}   // namespace

// the grab: the eye beside the player, the target between his head and the Ganado's
extern "C" void em10CamMove(cEm10* em, int no, f32 rate, int shake)
{
    Em10Work* w = EM10_WK(em);
    const v3 eye = through(pPL->mat, kGrabEye[no == 1 ? 1 : 0]);
    put(&w->Campos, eye);
    const v3 at = vscale(vadd(head_of(pPL), head_of(em)), 0.5f);
    cut_in(w, eye, at, rate, (shake ? SHAKE : 0) | WALLS | INSTALL, kCutinFovy);
}
// the NeckHang throw-off: the eye (Campos, em10SetCampos2) drawn in to 1700 units across, the target the player's head
void em10CamMove2(cEm10* em)
{
    Em10Work* w = EM10_WK(em);
    const v3 pl = head_of(pPL);
    const v3 d = vsub(V(w->Campos), pl);
    if (d.x * d.x + d.z * d.z > kNeckHangReach * kNeckHangReach) {
        v3 to = vadd(pl, vscale(vunit(shz_vec3_init(d.x, 0.0f, d.z)), kNeckHangReach));
        to.y = w->Campos.y;
        put(&w->Campos, ease(w->Campos, to, 0.2f));
    }
    cut_in(w, V(w->Campos), pl, 1.0f, WALLS | INSTALL, kCutinFovy);
}
// the critical hits: fixed shots in the player's frame
extern "C" void em10CamMoveCri(cEm10* em, u32 no, int shake)
{
    Em10Work* w = EM10_WK(em);
    const Shot& s = (pSys->region == 0 ? kCri : kCriOtherRegion)[no < 5 ? no : 0];
    cut_in(w, through(pPL->mat, s.eye), through(pPL->mat, s.at), 1.0f, (shake ? SHAKE : 0) | WALLS | INSTALL, s.fovy);
}
// the hold on Ashley: fixed shots in the player's frame, eased at 0.2
extern "C" void em10CamMoveAshley(cEm10* em, u32 no)
{
    Em10Work* w = EM10_WK(em);
    const Shot& s = kAshley[no < 4 ? no : 0];
    cut_in(w, through(pPL->mat, s.eye), through(pPL->mat, s.at), 0.2f, WALLS | INSTALL, s.fovy);
}
// the take-away: a fixed shot in the Ganado's frame, no wall test
extern "C" void em10CamMoveTakeaway(cEm10* em)
{
    Em10Work* w = EM10_WK(em);
    cut_in(w, through(em->mat, kTakeaway.eye), through(em->mat, kTakeaway.at), 1.0f, INSTALL, kTakeaway.fovy);
}
// the throw-off's eye: 1300 units to one side of the Ganado (the behaviour generator picks the side), raised out of
// water, kept 250 units clear of the scenery on the line from the player's head; the camera framed, not installed
extern "C" void em10SetCampos2(cEm10* em)
{
    Em10Work* w = EM10_WK(em);
    const f32 side[3] = {(Rnd() & 1) ? kThrowSide : -kThrowSide, kThrowHeight, 0.0f};
    put(&w->Campos, through(em->mat, side));
    const v3 pl = head_of(pPL);
    f32 h;
    if (GetWaterHeight(&em->pos, &h) && w->Campos.y < h) w->Campos.y = em->pos.y + 1500.0f;
    Vec from, out;
    put(&from, pl);
    if (EatMgr.hitCheck(&from, &w->Campos, &out, 0, 0, 0)) {
        const v3 d = vsub(V(out), pl);
        put(&w->Campos, vadd(pl, vscale(vunit(d), vlen(d) - kWallClear)));
    }
    frame(w->Cam, V(w->Campos), pl, kCutinFovy, false);
}

// on screen: the Ganado's root, or else its head, inside the 512 x 448 screen
extern "C" int em10ScreenInCk(cEm10* em)
{
    em10c_cnt.screen_checks++;
    const f32 right = em10c_control == 2 ? 256.0f : 512.0f;
    for (int k = 0; k < 2; k++) {
        Vec p = k == 0 ? em->pos : em->getPartsPtr(4)->world, scr;
        if (GetScreenPos(&p, &scr) && scr.x > 0.0f && scr.x < right && scr.y > 0.0f && scr.y < 448.0f) return 1;
    }
    return 0;
}
