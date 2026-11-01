// game/pl_dmg: the player's damage routines — routine 0 == 1 (Pl_R0_Damage: normal hit, blown
// away, blast stagger, each with the get-up steps) and routine 0 == 2 (Pl_R0_Die). Entered from
// cPlayer::setDamage; r_no_3 carries the hit direction, m_Fwork0 the attacker's yaw (123 = keep),
// and the motions come from the player archive (0x48.. hits, 0x4C death, 0x51 fly, 0x52 stagger).

#include "atari.h"
#include "light.h"
#include "player.h"
#include "global.h"
#include "db_log.h"
#include "main.h"
#include "pad.h"
#include "snd.h"
#include "esp.h"
#include "math_sub.h"
#if defined(RE4DC_WARP_GOD_HOOK) && RE4DC_WARP_GOD_HOOK
// Warp builds only (dbgwarp.mk): the `god` line turns the two lethal damage endings (r_no_3 6, the knock-down
// with m_Work0) into their non-lethal ones; the rig logs each as god-rescue (not a real outcome).
extern "C" int re4dc_warp_god;
extern "C" unsigned re4dc_warp_god_rescues;
static inline int warpGodRescue() { if (!re4dc_warp_god) return 0; ++re4dc_warp_god_rescues; return 1; }
#else
static inline int warpGodRescue() { return 0; }
#endif

#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_DEATH_TRACE) && RE4DC_DEATH_TRACE
extern "C" void re4dc_log(const char*, ...);
#endif

void MotionSetCore(cModel* m, void* work, void* data, int a, int b, int c, int d);  // game/motion.cpp (result unused here: void keeps the `mr r3` before the arg li`s)
extern "C" {
int MotionCheckCrossFrame(void* work, f32 frame);  // game/motion.cpp
void PlSetDamageSe(int no);                        // game/pl_sub.cpp
void EndPlDamage();                                // game/pl_sub.cpp
int ChkWaterEffectEnable(Vec* pos);                // game/est.cpp
}

void damageNormal(cPlayer* pl);
void damageBlow(cPlayer* pl);
void damageBlast(cPlayer* pl);
void Pl_R0_Die(cPlayer* pl);

// Routine bytes through int parameters: the four zeros become one SImode pseudo that cse cannot
// merge with the QImode zero of `dmg.m_Flag` stored before the EndPlDamage call, so the original's
// second `li r0, 0` after the call is reproduced instead of a callee-saved zero.
static inline void PlRoutineSet(cPlayer* pl, int r0, int r1, int r2, int r3)
{
    pl->r_no_0 = r0;
    pl->r_no_1 = r1;
    pl->r_no_2 = r2;
    pl->r_no_3 = r3;
}

// Routine 0 == 1 (damage, entered by cPlayer::setDamage): r_no_1 0 normal hit, 1 blown away,
// 2 blast stagger.
void Pl_R0_Damage(cPlayer* pl)
{
    static void (*funcTbl[])(cPlayer*) = {
        damageNormal,
        damageBlow,
        damageBlast,
    };

    funcTbl[pl->r_no_1](pl);
}

// Damage sub-routine 0: r_no_2 0 picks the hit motion by r_no_3 (0 front, 1 back, 2/4 left, 3/5
// right; 6 = life is 0: the collapse) turned toward m_Fwork0 (the attacker's yaw; 123 = keep),
// then 1 plays it — the player may cut it short with a key after m_Work0 frames; life 0 goes to
// routine 2/2 (die, already lying). r_no_2 0xA/0xB: the knocked-down variant, standing up with
// splash effects when in water. Ends with EndPlDamage and routine 0/0.
void damageNormal(cPlayer* pl)
{
    void* mot = 0;
    void* mot2 = 0;
    f32 ang;
    f32 wh;
    Vec* pos;

    switch (pl->r_no_2) {
    case 0:
        pl->beginDamage();
        if ((s16) pG->pl_life <= 0) {
            pl->r_no_3 = 6;
        }
        switch (pl->r_no_3) {
        default:
            pl->r_no_3 = 0;
        case 0:
            mot = PL_ARC_PTR(pG->pPlayer, 0x48);
            pl->m_Work0 = 0x1E;
            break;
        case 1:
            mot = PL_ARC_PTR(pG->pPlayer, 0x49);
            pl->m_Work0 = 0x23;
            break;
        case 2:
        case 4:
            mot = PL_ARC_PTR(pG->pPlayer, 0x4A);
            mot2 = PL_ARC_PTR(pG->pPlayer, 0x64);
            pl->m_Work0 = 0x23;
            break;
        case 3:
        case 5:
            mot = PL_ARC_PTR(pG->pPlayer, 0x4B);
            mot2 = PL_ARC_PTR(pG->pPlayer, 0x65);
            pl->m_Work0 = 0x23;
            break;
        case 6:
            mot = PL_ARC_PTR(pG->pPlayer, 0x4C);
            mot2 = PL_ARC_PTR(pG->pPlayer, 0x4D);
            pl->m_Work0 = 0x3E7;
            break;
        }
        MotionSetCore(pl, &pl->pMotion, mot, (int) mot2, 5, 1, 0);
        if (pl->m_Fwork0 != 123.0f) {
            ang = Muku2(pl->ang.y, pl->m_Fwork0, PI);
            pl->ang.y += ang;
            pl->ang.y = LIMIT_ANGLE(pl->ang.y);
            pl->getPartsPtr(0)->ang.y -= ang;
            pl->m_Work1 = 1;
        } else {
            pl->m_Work1 = 0;
        }
        if (pl->r_no_3 != 6) {
            PlSetDamageSe(0);
        }
        pl->setFace(1);
        pl->r_no_2 = 1;
        pl->dmg.m_Timer |= 0x80;
    case 1:
        if (pl->frame > 19.7f && pl->frame < 20.3f) {
            pl->setFace(0);
        }
        if (pl->m_Work0 != 0) {
            pl->m_Work0--;
        }
        if (pl->motionMove() != 0 || (pl->m_Work0 == 0 && (Key.on & 0x10F))) {
            if (pl->r_no_3 == 6 && !warpGodRescue()) {
                pl->r_no_0 = 2;
                pl->r_no_2 = 0;
                pl->r_no_1 = 2;
                pl->r_no_3 = 0;
            } else {
                pl->dmg.m_Flag = 0;
                pl->dmg.m_Timer = 5;
                EndPlDamage();
                PlRoutineSet(pl, 0, 0, 0, 0);
            }
        }
        if (pl->m_Work1 != 0) {
            cModel* p = pl->getPartsPtr(0);
            p->ang.y += Muku2(pl->getPartsPtr(0)->ang.y, 0.0f, PI / 10.0f);
        }
        break;
    case 0xA:
        MotionSetCore(pl, &pl->pMotion, PL_ARC_PTR(pG->pPlayer, 0x4F), pG->pPlayer->ofs[0x50] + (u32) pG->pPlayer, 3, 5, 0);
        EstSet((int) pl, -1, 0, 0, 3, ChkWaterEffectEnable(&pl->pos) ? 0x10 : 0xF, 0, 0, (u32) pl, 0);
        pl->r_no_2 = 0xB;
    case 0xB:
        pos = &pl->pos;
        if (pl->frame > 34.7f && pl->frame < 35.3f) {
            SndCall(5, 3, pos, 0, 0, 0);
        }
        if (pl->frame > 52.7f && pl->frame < 53.3f) {
            SndCall(5, 2, pos, 0, 0, 0);
        }
        if (pl->frame > 59.7f && pl->frame < 60.3f) {
            SndCall(1, 0x29, &pl->getPartsPtr(2)->world, 0, 0, 0);
        }
        if (GetWaterHeight(pos, &wh) && wh > pl->pos.y) {
            if (MotionCheckCrossFrame(&pl->pMotion, 48.0f) || MotionCheckCrossFrame(&pl->pMotion, 54.0f) ||
                MotionCheckCrossFrame(&pl->pMotion, 65.0f)) {
                EstSet((int) pl, -1, 0, 0, 1, 0x23, 0, 0, (u32) pl, 0);
            }
        }
        if (GetWaterHeight(pos, &wh) && pl->pParts->world.y < wh) {
            if (MotionCheckCrossFrame(&pl->pMotion, 18.0f)) {
                EstSet((int) pl, -1, 0, 0, 1, 0x24, 0, 0, (u32) pl, 0);
            }
        }
        if (pl->motionMove()) {
            pl->dmg.m_Flag = 0;
            pl->dmg.m_Timer = 5;
            EndPlDamage();
            PlRoutineSet(pl, 0, 0, 0, 0);
        }
        break;
    default:
        pLog->err(0, 0, "invalid r_no_2 %d", pl->r_no_2);
        break;
    }
}

// Damage sub-routine 1 (blown off the feet, e.g. by a blast or a big enemy): the fly motion (0x51,
// or 0x4E + 0x66 when dead), landing splash / dust, then the get-up (r_no_2 0xA/0xB) or routine
// 2/2 when dead.
void damageBlow(cPlayer* pl)
{
    void* mot;
    void* mot2;
    f32 ang;
    f32 wh;
    Vec* pos;
    int splash;
    u32 dead;
    u32 n;

    switch (pl->r_no_2) {
    case 0:
        pl->beginDamage();
        dead = 1;
        if ((s16) pG->pl_life > 0) {
            dead = 0;
        }
        BitSet(pl->m_Work0, dead);
        if (dead) {
            mot = PL_ARC_PTR(pG->pPlayer, 0x4E);
            mot2 = PL_ARC_PTR(pG->pPlayer, 0x66);
        } else {
            mot = PL_ARC_PTR(pG->pPlayer, 0x51);
            mot2 = PL_ARC_PTR(pG->pPlayer, 0x67);
        }
        MotionSetCore(pl, &pl->pMotion, mot, (int) mot2, 5, 1, 0);
        n = pl->m_Work0;
        if (n) {
            EstSet((int) pl, -1, 0, 0, 3, ChkWaterEffectEnable(&pl->pos) ? 0xE : 0xD, 0, 0, (u32) pl, 0);
        } else {
            EstSet((int) pl, -1, 0, 0, 3, ChkWaterEffectEnable(&pl->pos) ? 6 : 5, 0, 0, (u32) pl, (void*) n);
        }
        if (pl->m_Fwork0 != 123.0f) {
            ang = Muku2(pl->ang.y, pl->m_Fwork0, PI);
            pl->ang.y += ang;
            pl->ang.y = LIMIT_ANGLE(pl->ang.y);
            pl->getPartsPtr(0)->ang.y -= ang;
            pl->m_Work1 = 1;
        } else {
            pl->m_Work1 = 0;
        }
        if (pl->m_Work0 == 0) {
            PlSetDamageSe(0);
        } else {
            SndCall(1, 0x4A, &pl->getPartsPtr(2)->world, 0, 0, 0);
        }
        pl->setFace(1);
        pl->m_Work2 = 0;
        pl->r_no_2 = 1;
        pl->dmg.m_Timer |= 0x80;
    case 1:
        if (MotionCheckCrossFrame(&pl->pMotion, 20.0f)) {
            pl->setFace(0);
        }
        if (pl->m_Work0 == 0 && pl->frame > 9.7f && pl->frame < 10.3f) {
            SndCall(5, 5, &pl->pos, 0, 0, 0);
        }
        if (pl->frame >= 5.0f) {
            splash = pl->m_Work2;
            if (splash == 0 && GetWaterHeight(&pl->pParts->world, &wh) && pl->pParts->world.y < wh + 400.0f) {
                pl->m_Work2 = 1;
                EstSet((int) pl, -1, 0, 0, 1, 0x24, 0, 0, (u32) pl, (void*) splash);
            }
        }
        if (pl->motionMove()) {
            if (pl->m_Work0 != 0 && !warpGodRescue()) {
                pl->r_no_0 = 2;
                pl->r_no_1 = 2;
                pl->r_no_2 = 0;
                pl->r_no_3 = 0;
            } else {
                pl->r_no_2 = 0xA;
            }
        }
        break;
    case 0xA:
        MotionSetCore(pl, &pl->pMotion, PL_ARC_PTR(pG->pPlayer, 0x4F), pG->pPlayer->ofs[0x50] + (u32) pG->pPlayer, 3, 5, 0);
        EstSet((int) pl, -1, 0, 0, 3, ChkWaterEffectEnable(&pl->pos) ? 0x10 : 0xF, 0, 0, (u32) pl, 0);
        pl->r_no_2 = 0xB;
    case 0xB:
        pos = &pl->pos;
        if (pl->frame > 34.7f && pl->frame < 35.3f) {
            SndCall(5, 3, pos, 0, 0, 0);
        }
        if (pl->frame > 52.7f && pl->frame < 53.3f) {
            SndCall(5, 2, pos, 0, 0, 0);
        }
        if (pl->frame > 59.7f && pl->frame < 60.3f) {
            SndCall(1, 0x29, &pl->getPartsPtr(2)->world, 0, 0, 0);
        }
        if (GetWaterHeight(pos, &wh) && wh > pl->pos.y) {
            if (MotionCheckCrossFrame(&pl->pMotion, 48.0f) || MotionCheckCrossFrame(&pl->pMotion, 54.0f) ||
                MotionCheckCrossFrame(&pl->pMotion, 65.0f)) {
                EstSet((int) pl, -1, 0, 0, 1, 0x23, 0, 0, (u32) pl, 0);
            }
        }
        if (GetWaterHeight(pos, &wh) && pl->pParts->world.y < wh) {
            if (MotionCheckCrossFrame(&pl->pMotion, 18.0f)) {
                EstSet((int) pl, -1, 0, 0, 1, 0x24, 0, 0, (u32) pl, 0);
            }
        }
        if (pl->motionMove()) {
            pl->dmg.m_Flag = 0;
            pl->dmg.m_Timer = 5;
            EndPlDamage();
            PlRoutineSet(pl, 0, 0, 0, 0);
        }
        break;
    }
}

// Damage sub-routine 2 (blast stagger, motion 0x52): turns toward m_Fwork0, pained face for 20
// frames, then back to routine 0/0.
void damageBlast(cPlayer* pl)
{
    f32 ang;
    int no = pl->r_no_2;

    switch (no) {
    case 0:
        pl->beginDamage();
        MotionSetCore(pl, &pl->pMotion, PL_ARC_PTR(pG->pPlayer, 0x52), 0, 5, 1, 0);
        if (pl->m_Fwork0 != 123.0f) {
            ang = Muku2(pl->ang.y, pl->m_Fwork0, PI);
            pl->ang.y += ang;
            pl->ang.y = LIMIT_ANGLE(pl->ang.y);
            pl->getPartsPtr(0)->ang.y -= ang;
            pl->m_Work1 = 1;
        } else {
            pl->m_Work1 = no;
        }
        pl->setFace(1);
        pl->r_no_2 = 1;
        pl->dmg.m_Timer |= 0x80;
    case 1:
        if (pl->frame > 19.7f && pl->frame < 20.3f) {
            pl->setFace(0);
        }
        if (pl->motionMove()) {
            pl->dmg.m_Flag = 0;
            pl->dmg.m_Timer = 5;
            EndPlDamage();
            PlRoutineSet(pl, 0, 0, 0, 0);
        }
        break;
    }
}

// Routine 0 == 2 (death): r_no_1 0 starts the death motion (0x4C/0x4D) with the blood effect,
// scream (when the character has hair data — Leon), rumble at frames 40 / 70; 1 plays it, 2 holds
// the last frame while the game-over sequence runs.
#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_DEATH_TRACE) && RE4DC_DEATH_TRACE
__attribute__((noinline))
#endif
void Pl_R0_Die(cPlayer* pl)
{
    int no = pl->r_no_1;
#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_DEATH_TRACE) && RE4DC_DEATH_TRACE
    static bool death_seen;
    if (!death_seen || no == 0) {
        death_seen = true;
        re4dc_log("death trace: die.enter frame=%u caller=%08x life=%d rno=%u/%u/%u/%u\n",
                  unsigned(pG->Frame_cnt), unsigned((u32) __builtin_return_address(0)),
                  int(s16(pG->pl_life)), unsigned(pl->r_no_0), unsigned(pl->r_no_1),
                  unsigned(pl->r_no_2), unsigned(pl->r_no_3));
    }
#endif

    switch (no) {
    case 0:
        pl->beginDamage();
        MotionSetCore(pl, &pl->pMotion, PL_ARC_PTR(pG->pPlayer, 0x4C), pG->pPlayer->ofs[0x4D] + (u32) pG->pPlayer, 5, 1, 0);
        EstSet((int) pl, -1, 0, 0, 3, ChkWaterEffectEnable(&pl->pos) ? 4 : 3, 0, 0, (u32) pl, (void*) no);
        pl->dmg.m_Timer |= 0x80;
        if (pl->Body->pHair) {
            SndCall(1, 0xD, &pl->getPartsPtr(4)->world, 0, 0, 0);
            pl->setFace(1);
        }
        pl->atari.m_parts_no = 4;
        pl->r_no_1 = 1;
        pl->m_Work0 = no;
    case 1:
        if (pl->frame > 39.7f && pl->frame < 40.3f) {
            VibSetData((VibDataTbl*) (pG->pArc->ofs_1C + (u32) pG->pArc), 3, 1);
        }
        if (pl->frame > 69.7f && pl->frame < 70.3f) {
            VibSetData((VibDataTbl*) (pG->pArc->ofs_1C + (u32) pG->pArc), 3, 1);
        }
        if (pl->motionMove()) {
            pl->r_no_1 = 2;
        }
        break;
    case 2:
        pl->motionMove();
        break;
    }
}
