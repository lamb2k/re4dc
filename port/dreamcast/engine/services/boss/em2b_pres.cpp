// em2b_pres.cpp (lane eng-e2c): El Gigante's presentation and view entry points, native. The hosted boss decides when
// (which routine, which frame); these place what is presented: the event cameras of the catch, blow, stamp, escape and
// parasite scenes, the camera quake of a heavy step or blow, the foot landing (sound, dust, quake, chain rattle), and
// the on-screen test the attack choice reads.
//
// Engine form: an event camera is an eye and a target placed in the player's frame (cam_math.h, SH4ZAM types) or
// blended from the game camera, then finished in one place: the camera service builds its frame
// (CameraSetOrientationUp) and the controller's extra-camera slot points at it. The quake's strength is a table of
// distance bands; a foot landing is a table row (foot part, sound number) and the same three requests to the sound
// entry point, the effect setter and the quake. Sounds stay calls to the sound entry point (SndCall); effects are
// requests to the effect setter (EstSet), nothing is drawn here. No random number is drawn.
#define fabsf e2c_game_fabsf
#include "types.h"
#include "global.h"
#include "model.h"
#include "em.h"
#include "player.h"
#include "em2b.h"
#include "camera.h"
#include "cam_ctrl.h"
#include "atari.h"
#include "math_sub.h"
#include "esp.h"
#include "quake.h"
#undef fabsf
#include "cam_math.h"
#include "boss_svc.h"

u32 SndCall(u16 blk, u16 no, Vec* pos, int id, int a, cUnit* owner);   // the sound entry point (stays a call)

extern "C" {
BossSvcCounters boss_cnt;
int boss_control;
}

namespace {
using namespace camsvc;

Em2bWork* work(cEm2b* em) { return EM2B_WK(em); }
v3 game_eye() { return V(pG->Cam.param.pos); }
v3 game_target() { return V(pG->Cam.param.at); }
// a point given in a model's own frame (its matrix), in the world
v3 in_frame(const cModel* m, f32 x, f32 y, f32 z) { return frame_point(frame_of(m->mat), shz_vec3_init(x, y, z)); }
v3 root_of(cModel* m) { return V(m->getPartsPtr(0)->world); }
// from a toward b by t (the math service's blend: a (1 - t) + b t)
v3 toward(v3 a, v3 b, f32 t) { return vmix(a, 1.0f - t, b, t); }

// The giant's event camera, finished: eye, target and field of view in the work's camera; up is the world's; the
// distance and the frame (the camera service); the controller then plays it instead of the game camera.
void event_camera(cEm2b* em, v3 eye, v3 at, f32 fovy)
{
    Camera* c = &work(em)->Cam;
    if (boss_control == 1) eye = vadd(at, vscale(vsub(eye, at), 1.01f));   // control bosscam
    c->param.fovy = fovy;
    put(&c->param.pos, eye);
    put(&c->param.at, at);
    put(&c->up, shz_vec3_init(0.0f, 1.0f, 0.0f));
    c->dist = vdist(eye, at);
    CameraSetOrientationUp(c);
    CamCtrl.m_pExtraCamera = (s32) c;
}
}   // namespace

// Catch and blow: the game camera's eye, its target drawn toward Leon's root by `rate`.
void em2bBlowCamMove(cEm2b* em, f32 rate)
{
    CAM_SVC("em2b event camera");
    boss_cnt.cam_moves[0]++;
    event_camera(em, game_eye(), toward(game_target(), root_of(pPL), rate), pG->Cam.param.fovy);
}

// Stamp: the eye a tenth of the way to a point 3000 above and 3000 behind Leon, the target three tenths of the way to
// his root.
void em2bStampCamMove(cEm2b* em)
{
    CAM_SVC("em2b event camera");
    boss_cnt.cam_moves[1]++;
    const v3 eye = toward(game_eye(), in_frame(pPL, 0.0f, 3000.0f, -3000.0f), 0.1f);
    event_camera(em, eye, toward(game_target(), root_of(pPL), 0.3f), pG->Cam.param.fovy);
}

// Escape: eye and target at fixed points of Leon's frame (behind his left shoulder, looking past his right); when the
// effect collision lies between them, the eye comes in to 250 short of the hit.
void em2bEscapeCamMove(cEm2b* em)
{
    CAM_SVC("em2b event camera");
    boss_cnt.cam_moves[2]++;
    Vec at, eye, hit;
    put(&at, in_frame(pPL, -244.0f, 809.0f, 52.5999985f));
    put(&eye, in_frame(pPL, -376.0f, 575.0f, -1831.0f));
    if (EatMgr.hitCheck(&at, &eye, &hit, 0, 0x8000, 0)) {
        boss_cnt.cam_pulls++;
        const v3 d = vsub(V(hit), V(at));
        put(&eye, vadd(V(at), vscale(vunit(d), vlen(d) - 250.0f)));
    }
    event_camera(em, V(eye), V(at), pG->Cam.param.fovy);
}

// Parasite attack: a field of view of 50; eye 3000 to Leon's left and target 1000 ahead, both in his frame and lifted to
// the height of his root part.
void em2bParasiteAtkCamMove(cEm2b* em)
{
    CAM_SVC("em2b event camera");
    boss_cnt.cam_moves[3]++;
    const v3 lift = shz_vec3_init(0.0f, pPL->getPartsPtr(0)->world.y - pPL->pos.y, 0.0f);
    event_camera(em, vadd(in_frame(pPL, -3000.0f, 0.0f, 1000.0f), lift), vadd(in_frame(pPL, 0.0f, 0.0f, 1000.0f), lift), 50.0f);
}

// The camera quake of a heavy landing at `pos`: its strength by the distance from the game camera, in bands (10 within
// 5000, 8 within 10000, 6 within 15000, 4 nearer than 20000, none further).
void em2bQuakeSet(Vec* pos)
{
    static const f32 band[3] = {25000000.0f, 100000000.0f, 225000000.0f};   // squared band ends
    static const f32 power[3] = {10.0f, 8.0f, 6.0f};
    boss_cnt.quakes++;
    const f32 d2 = vlen2(vsub(V(pos), game_eye()));
    if (!(d2 < 400000000.0f)) return;
    f32 p = 4.0f;
    for (int k = 0; k < 3; k++) {
        const f32 end = (k == 0 && boss_control == 2) ? 20250000.0f : band[k];   // control bossquake
        if (d2 <= end) {
            p = power[k];
            break;
        }
    }
    boss_cnt.quake_sets++;
    QuakeExec(0, 0, 5, p, 2);
}

// A foot landing (the motion's sound key seNo: 1 left, 2 right; a mirrored motion lands the other foot): the quake
// there, the step sound, the dust (a second dust set on the giant while Be_flg bit 8 is up) and, for the chained form,
// the chain's rattle at the root.
void em2bFootSe(cEm2b* em)
{
    static const u8 foot_part[2] = {0x15, 0x19};
    const u32 key = (u32) em->seNo - 1;
    if (key > 1) return;
    em->seNo = 0;
    Em2bWork* w = work(em);
    const u32 foot = key ^ ((em->motFlags & 0x40) ? 1u : 0u);
    Vec* at = &em->getPartsPtr(foot_part[foot])->world;
    boss_cnt.feet++;
    em2bQuakeSet(at);
    SndCall(8, foot, at, em->id, 0, em);
    EstSet(0, -1, at, 0, w->espKind2, 4, 0, 0, 0, 0);
    if (w->Be_flg & 0x100) EstSet((int) em, -1, 0, 0, w->espKind2, 0xF, 0, 0, (u32) em, 0);
    if (em->type == 3 && w->pChain) SndCall(6, 0x11, &em->getPartsPtr(0)->world, em->id, 0, em);
}

// The root part within the picture widened by 300 on every side (x -300 .. 812, y -300 .. 748) and not behind the
// eye (depth at most 1), through the camera's projection (the math service's GetScreenPos). A comparison with no
// answer (not a number) counts as inside, as the original's tests do.
int em2bInScreenCk(cEm2b* em)
{
    const f32 margin = 300.0f;
    Vec root = em->getPartsPtr(0)->world, s;
    boss_cnt.screen_tests++;
    GetScreenPos(&root, &s);
    return !(s.z > 1.0f) && !(s.x < -margin) && !(s.x > 512.0f + margin) && !(s.y < -margin) && !(s.y > 448.0f + margin);
}
