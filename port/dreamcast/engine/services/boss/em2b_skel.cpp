// em2b_skel.cpp (lane eng-e2c): El Gigante's pose entry points, native: the head's turn toward what it watches, the
// two-motion blends (the giant's walk and stamp aim, the player's strangle), and the dying body's vertical squash.
//
// Engine form: the head's turn is one damped angle the skeleton applies through the neck part's added rotation (the
// skeleton's mailbox: the part record handed out by getPartsPtr, read back by the service); the target is chosen from a
// table of the three watchers. A blend is one set-up for both callers: the main and the blended motion started on the
// motion service (MotionSetCore), the blend's weight |rate| / 256, the hokan count stepped down and the sequence frame
// stepped round the clip. The squash is the skeleton service's (skel_compress_y), as em10ScaleCompress's is (lane
// eng-e1h). No random number is drawn.
#define fabsf e2c_game_fabsf
#include "types.h"
#include "global.h"
#include "model.h"
#include "em.h"
#include "player.h"
#include "pl_npc.h"
#include "em2b.h"
#include "motion.h"
#include "math_sub.h"
#undef fabsf
#include "skel.h"
#include "boss_svc.h"

namespace {
// What the head watches: the other giant's root while it targets a friend (Be_flg bit 7), the partner's head while it
// targets her (bit 2), else Leon's head.
cModel* watched(cEm2b* em)
{
    Em2bWork* w = EM2B_WK(em);
    if ((w->Be_flg & 0x80) && w->pFriend) return w->pFriend->getPartsPtr(0);
    if ((w->Be_flg & 4) && pSUB) return pSUB->getPartsPtr(4);
    return pPL->getPartsPtr(4);
}

// One blend set-up: `main` on the model's own motion work, `other` on `blend`, weight |rate| / 256; the hokan count
// steps down to 0, the sequence frame steps and wraps at the clip's length.
template <class Cnt, class Seq>
void blend_setup(cModel* m, MotionWork* blend, void* main, int main_arg, void* other, int other_arg, Cnt& hokan, int start,
                 Seq& seq, f32 rate)
{
    MotionSetCore(m, &m->Motion, main, main_arg, (u8) hokan, start, (u16) seq);
    MotionSetCore(m, blend, other, other_arg, (u8) hokan, start, (u16) seq);
    m->motBlend = blend;
    blend->Brate = __builtin_fabsf(rate) * (boss_control == 4 ? 1.0f / 255.0f : 0.00390625f);   // control bossblend
    if (hokan) hokan--;
    seq++;
    if ((u32) seq >= m->frameMax) seq = 0;
    boss_cnt.blends++;
}
}   // namespace

// The head turned toward what the giant watches: 90% of last tick's angle, plus, while a routine runs (Be_flg bit 4),
// a tenth of the turn toward the target's position (at most 60 degrees, the math service's Muku); applied by the
// skeleton as the neck part's added rotation about y.
void em2bNeckMove(cEm2b* em)
{
    Em2bWork* w = EM2B_WK(em);
    cModel* t = watched(em);
    f32 a = w->Neck_dir_y * (boss_control == 3 ? 0.85f : 0.899999976f);   // control bossneck
    if (w->Be_flg & 0x10) a += Muku(&em->pos, &t->world, em->ang.y, 1.04719758f) * 0.100000001f;
    w->Neck_dir_y = a;
    cParts* neck = (cParts*) em->getPartsPtr(3);
    neck->motParts.flags |= 0x40000000;
    neck->addRot.x = 0.0f;
    neck->addRot.y = a;
    neck->addRot.z = 0.0f;
    boss_cnt.necks++;
}

// The giant's blend (walk, stamp aim): m0 on the main work; m1 (argument b) when the blend rate is negative, else m2
// (argument c), on the work's blend motion; hokan count and sequence frame are the work's.
void em2bBlendMotSet(cEm2b* em, void* m0, void* m1, void* m2, int a, int b, int c, u16 d)
{
    Em2bWork* w = EM2B_WK(em);
    const bool back = w->Blend < 0.0f;
    blend_setup(em, EM2B_BLEND_MOT(w), m0, a, back ? m1 : m2, back ? b : c, w->blendCnt, (int) d, w->blendSeq, w->Blend);
}

// The player's strangle blend: m1 on the neck motion work at the button-mash rate (0x500); the hokan count and the
// sequence frame are the player's (0x4FD, 0x4FC); start frame 1.
void plBlendMotSet(cPlayer* pl, void* m0, void* m1, int a, int b)
{
    blend_setup(pl, (MotionWork*) &pl->neckMot, m0, a, m1, b, pl->x4FD, 1, pl->x4FC, pl->blendRate500);
}

// The lost die routine (r_no 3, 1): every part squashed by the work's y scale, world positions kept: the skeleton.
void em2bScaleCompress(cEm2b* em)
{
    if (em->r_no_0 != 3 || em->r_no_1 != 1) return;
    boss_cnt.squashes++;
    skel_compress_y(em, EM2B_WK(em)->scaleRate);
}
