// follow.cpp: the native root-motion follower (lane eng-svc4; follow.h, docs/engine/SERVICES.md section 26).
//
// What it owns (the original unit cMotBase.cpp, every function it links): cMotBase, 0x38 bytes in the actor's record
// (cEm+0x7A4), which behaviour starts with a pose and a count:
//   - each tick the followed pose advances by the motion's root speed (the native clock's MotionGetSpeed) turned into
//     world space by the model's matrix (rotation only), and its rotation by the root's rotation speed;
//   - while the count runs, the model moves 1/cnt of the way to the followed position and turns toward its yaw by at
//     most PI/cnt; when the count reaches 0 the motion's own root motion (Mot_attr bit 0) is switched back on and the
//     follower stops; a follower started with count 0 pins the model to the followed pose every tick;
//   - adjust: movement the model made outside the follower (a push, the collision slide) is carried into the pose.
// Arithmetic: the original's, operation for operation (single precision, contraction off), so the PC reference
// compares bit for bit. The follower stays in the actor's record, where behaviour reads it.
#include "cMotBase.h"
#include "math_sub.h"
#include "motion.h"
#include "follow.h"

extern "C" {
FollowCounters follow_cnt;
int follow_control;
}

namespace {
constexpr u8 kIdle = 0xFF;   // cnt: no follower
}

cMotBase::cMotBase()
{
    cnt = kIdle;
    pModel = 0;
}

void cMotBase::set(cMotModel* m, MotionData* data, Vec* p, Vec* r, u8 c)
{
    (void) data;
    follow_cnt.sets++;
    pModel = m;
    pos_old = *p;
    pos = pos_old;
    ang_old = *r;
    ang = ang_old;
    cnt = c;
}

// Starts following with the model's current motion; the motion stops moving the model itself (Mot_attr bit 0) while
// the follower drives it.
void cMotBase::set(cMotModel* m, Vec* p, Vec* r, u8 hokan0)
{
    set(m, m->Motion.pMot, p, r, hokan0);
    m->Motion.Mot_attr &= ~1;
}

void cMotBase::adjust()
{
    if (cnt == kIdle) return;
    follow_cnt.adjusts++;
    Vec d;
    PSVECSubtract(&pModel->pos, &pos_old, &d);
    PSVECAdd(&pos, &d, &pos);
    ang.y += pModel->ang.y - ang_old.y;
}

void cMotBase::move()
{
    if (cnt == kIdle) return;
    follow_cnt.moves++;
    Vec spd;
    Vec rot;
    MotionGetSpeed(pModel, &pModel->Motion, 0, &spd, &rot);
    PSMTXMultVecSR(pModel->mat, &spd, &spd);
    PSVECAdd(&pos, &spd, &pos);
    PSVECAdd(&ang, &rot, &ang);
    if (cnt != 0) {
        follow_cnt.blends++;
        const int steps = follow_control == 1 ? (int) cnt + 1 : (int) cnt;
        Vec d;
        PSVECSubtract(&pos, &pModel->pos, &d);
        PSVECScale(&d, &d, 1.0f / (f32) steps);
        PSVECAdd(&pModel->pos, &d, &pModel->pos);
        pModel->ang.y += Muku2(pModel->ang.y, ang.y, PI / (f32) steps);
        if (--cnt == 0) {
            follow_cnt.ends++;
            pModel->Motion.Mot_attr |= 1;
            cnt = kIdle;
        }
    } else {
        follow_cnt.pins++;
        pModel->pos = pos;
        pModel->ang = ang;
    }
    pos_old = pModel->pos;
    ang_old = pModel->ang;
}
