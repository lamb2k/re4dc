// em10_pres.cpp (lane eng-e2b, 2026-11-21): the Ganado's presentation, native. The sound numbers of its voice kind,
// the voice, breath, chainsaw and footstep sounds, its weapon's sound and effect numbers, the blood effect a hit makes,
// the kick's hit mark and the water splashes. The behaviour (em10.cpp's routines) calls these by their original names
// and keeps every decision of its own; em10's bodies are weak in the image (game/fight.mk EM10_NATIVE) and in the PC
// reference's native build (hostref svc/svc.mk), so these are the ones reached. docs/engine/lanes/eng-e2b.md lists, per
// function, how it differs from the original.
//
// Engine form: tables instead of switches. A voice kind is one row of 19 sound numbers; a model type maps to its voice
// bank; a weapon's sounds are one row per weapon kind; a footstep is one row per step number (sound, foot, chain
// rattle); a hit's blood is a weapon class (one table per variant) and one choice of effect by class, armour, range,
// water and the big-effect lock. Sounds stay calls to the sound entry points (SndCall, SndStop, Ctrl11*: the driver is
// lane eng-snd1's); effects are started through the effect service's entry points (EstSet, EmDmBloodSet2,
// EspEstSetSelect): no effect is drawn here.
//
// Randomness: the voice timers, the sound rates and the blood scatter are presentation and draw from the engine's
// presentation generator (eng_pres_u8), in the order the original drew them, as the split images did (game/fight.mk
// PRESENT_em10, hostref PRESENT_EM10). em10BehindSeCk's own breath timer draws from the behaviour generator (Rnd) as
// the original does in both builds today: moving it needs a reference change (eng-e2b.md, H-016.8).
#define fabsf em10p_game_fabsf
#include "types.h"
#include "global.h"
#include "model.h"
#include "em.h"
#include "em10.h"
#include "player.h"
#include "em_sub.h"
#include "emwep.h"
#include "esp.h"
#include "est.h"
#include "ctrl.h"
#include "snd.h"
#include "atari.h"
#include "math_sub.h"
#include "rnd.h"
#undef fabsf
#include "cam_math.h"

extern "C" {
unsigned char eng_pres_u8();
// counters (the PC check's e2b.txt; the image's report)
struct Em10PresCounters {
    u32 se_tables, voices, voices2, breaths, csaw, damage_voices, behind, feet, step_sounds, chain_rattles, wep_sets;
    u32 bloods, bloods_1c, blood_parts, marks, water_hits, water_wades;
};
Em10PresCounters em10p_cnt;
// Controls (set only by the PC check, hostref svc/e2b_dump.cpp RE4_SVC_CONTROL; each must make e2b.txt differ):
// 1 "voicebank": the village man's voice bank is the woman's; 2 "bloodswap": the big spray's near and far forms
// swapped; 3 "footpart": a step's sound placed at the other foot.
int em10p_control;
}
// the ctrl11 entry point the original reaches under its old name (em10.cpp's int view of the u16 arguments)
u32 Ctrl11SetSe2I(cCtrl* c, cModel* m, s16 time, int no, int idx, int blk) asm("Ctrl11SetSe2__FP5cCtrlP6cModelsUsiUs");
// the behaviour's decision (hosted): is this part armoured
int em10ArmorCk(cEm10* em, int parts);

// The engine's own entry points, by the names the behaviour calls.
extern "C" {
void Em10SetSeTbl(cEm10* em, int type);
void em10CallVoiceSe(cEm10* em, u16 no);
void em10CsawSignSe(cEm10* em);
void em10BehindSeCk(cEm10* em);
void em10WepSeEffSet(cEm10* em, cEmWep* wep, int type);
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

namespace {
using namespace camsvc;

// ---- sounds ----
// Se_tbl, one row per voice kind (0 village man, 1 woman, 2 zealot, 3 soldier): voice, grunt, damage, death, find,
// attack ... numbers; a kind past the table is the village man. The merchant type (6) has its own first sound.
const u8 kVoiceSet[4][19] = {
    {0x16, 0x17, 0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x25, 0x47, 0x48, 0x49, 0x4A, 0x4B, 0x4C, 0x4D, 0x4E, 0x5B, 0xB5, 0x15},
    {0x1E, 0x1F, 0x20, 0x21, 0x22, 0x23, 0x24, 0x27, 0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x5C, 0xB6, 0x1D},
    {0x2E, 0x2F, 0x30, 0x31, 0x32, 0x33, 0x34, 0x29, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x6B, 0x6C, 0x5D, 0xB7, 0x2D},
    {0x36, 0x37, 0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x2B, 0x6F, 0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x5E, 0xB8, 0x35},
};
const u8 kMerchantVoice = 0x0E;
// the ctrl11 voice bank of each model type; types past the table use bank 0
const u8 kVoiceBank[26] = {0, 1, 2, 3, 4, 2, 5, 2, 2, 2, 2, 0, 0, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0, 2, 2, 2};
// the voice's playback slot (ctrl11 index) for the second voice and the breath
const int kVoiceSlot = 6;

u8 voice_bank(u8 type)
{
    if (em10p_control == 1 && type == 0) return 1;
    return type < sizeof(kVoiceBank) ? kVoiceBank[type] : 0;
}
// presentation draws, as the original's Rnd() % n on the presentation generator
int pres(int n) { return eng_pres_u8() % n; }
s16 voice_rate() { return (s16) (pres(20) + 20); }
u16 breath_wait() { return (u16) (pres(120) + 120); }
bool muted(const Em10Work* w) { return w->flags & 0x80; }   // the head is gone: no voice
void voice_stop(Em10Work* w)
{
    SndStop(w->Seid_voice, 0);
    SndStop(w->Seid_breath, 0);
}

// ---- footsteps: one row per step number (seNo - 1) ----
struct Step {
    u8 sound;   // block 5 sound number
    u8 foot;    // the part the sound is placed at
    u8 chain;   // the flail's chain: 1 rattle on the next tick (Chain_se_wait 1), 2 rattle now (block 8, 0xA4)
};
const Step kStepVillage[4] = {{0x10, 0x15, 1}, {0x11, 0x19, 1}, {0x12, 0x15, 2}, {0x13, 0x19, 2}};
const Step kStepClaw[4] = {{0x18, 0x15, 1}, {0x19, 0x19, 1}, {0x1A, 0x15, 2}, {0x1B, 0x19, 2}};
const u16 kClawLand[2] = {0x6F, 0x70};   // the claw types' steps 4 and 5: block 6 at the root, and done
bool claw_type(const cEm10* em) { return em->type == 0xA || em->type == 0xD; }

// ---- the weapon's sounds and effects, one row per weapon kind (em10MakeWeapon's types) ----
struct WepSound {
    u8 none;    // no set (the empty hand, the dynamite)
    u8 hit, fall, thrown;
};
const WepSound kWepSound[17] = {
    {1, 0, 0, 0},           // 0
    {0, 0x0B, 0x41, 0x45},  // 1 hoe
    {0, 0x0B, 0x40, 0x45},  // 2 hatchet
    {0, 0x0B, 0x40, 0x45},  // 3 sickle
    {0, 0x0B, 0x40, 0x45},  // 4 chainsaw
    {0, 0x0B, 0x40, 0x45},  // 5 bucket
    {0, 0x0B, 0x41, 0x45},  // 6 scythe
    {0, 0x46, 0x43, 0x42},  // 7 torch
    {0, 0x0B, 0x41, 0x45},  // 8 bowgun
    {1, 0, 0, 0},           // 9 dynamite
    {0, 0x0B, 0x40, 0x45},  // 10 pitchfork
    {0, 0x0B, 0x40, 0x45},  // 11 flail
    {0, 0x0B, 0x41, 0x45},  // 12 rocket launcher
    {0, 0x0B, 0x40, 0x45},  // 13
    {0, 0x0B, 0x40, 0x45},  // 14
    {0, 0x0B, 0x40, 0x45},  // 15 stun rod
    {0, 0x0B, 0x40, 0x45},  // 16
};
const WepSound kWepSoundOther = {0, 0x0B, 0x40, 0x45};

// ---- blood: a hit's weapon as a class, and the effect each class makes ----
enum Blood : u8 {
    B_NONE,     // nothing
    B_SMALL,    // handguns and the like: the small spray (0x3B in water)
    B_MAGNUM,   // 0x29
    B_SHOT,     // shotguns: 0xC (0x3D in water) and a quarter of the time the scatter 0xD at the hit
    B_RIFLE,    // rifles: the big spray when near, else the small one
    B_BLAST,    // blasts: 0x87 and the 0x88 sprites stuck to the hit part
    B_BIG,      // the rest: the big spray
    B_ARMOUR,   // (em10's armour table only: no blood on armour, the big spray elsewhere: weapon 0x17)
};
// em10BloodSet's classes by weapon id (0..0x2D); past the table: B_BIG
const u8 kBloodEm10[0x2E] = {
    B_NONE, B_SMALL, B_SMALL, B_SMALL, B_SMALL, B_BIG, B_BIG, B_RIFLE,             // 0x00..0x07
    B_RIFLE, B_BLAST, B_BLAST, B_SHOT, B_SHOT, B_BIG, B_BIG, B_BIG,                // 0x08..0x0F
    B_MAGNUM, B_SMALL, B_BIG, B_BIG, B_NONE, B_BIG, B_BIG, B_ARMOUR,               // 0x10..0x17
    B_BIG, B_SMALL, B_MAGNUM, B_SHOT, B_SMALL, B_SHOT, B_BIG, B_SMALL,             // 0x18..0x1F
    B_SMALL, B_RIFLE, B_NONE, B_NONE, B_NONE, B_NONE, B_SMALL, B_SHOT,             // 0x20..0x27
    B_BLAST, B_BIG, B_NONE, B_SMALL, B_BIG, B_BIG,                                 // 0x28..0x2D
};
// em1cBloodSet's (the parasite-headed types 0xA / 0xD): blasts are small, 0x22..0x25 and 0x2A the big spray
const u8 kBloodEm1c[0x2E] = {
    B_NONE, B_SMALL, B_SMALL, B_SMALL, B_SMALL, B_BIG, B_BIG, B_RIFLE,             // 0x00..0x07
    B_RIFLE, B_SMALL, B_SMALL, B_SHOT, B_SHOT, B_BIG, B_BIG, B_BIG,                // 0x08..0x0F
    B_MAGNUM, B_SMALL, B_BIG, B_BIG, B_NONE, B_BIG, B_BIG, B_BIG,                  // 0x10..0x17
    B_BIG, B_SMALL, B_MAGNUM, B_SHOT, B_SMALL, B_SHOT, B_BIG, B_SMALL,             // 0x18..0x1F
    B_SMALL, B_RIFLE, B_BIG, B_BIG, B_BIG, B_BIG, B_SMALL, B_SHOT,                 // 0x20..0x27
    B_SMALL, B_BIG, B_BIG, B_SMALL, B_BIG, B_BIG,                                  // 0x28..0x2D
};
u8 blood_class(const u8* tbl, u8 wep) { return wep < 0x2E ? tbl[wep] : B_BIG; }
// the em1c parasite part (0x25): no blood for 0, 0x14, 0x22..0x25, the near rifle its big splash 0x27, the small
// classes 0x26, the rest 0x27
const u8 kParasitePart = 0x25;
const f32 kNearBlood2 = 16000000.0f;   // within 4000 units of the camera: the big spray's near form
const int kBigEffLock = 0x2D;          // ticks the big spray locks the next big one (ctrl12 BIGEFF)
// the part the blood scatter of the damage position belongs to (the head, for the parasite's own blood)
const int kHeadPart = 5;

void blood(cEm10* em, int no) { EmDmBloodSet2(em, 0x10, no, 0, 0, 0); }
bool water(cEm10* em) { return ChkWaterEffectEnable(&em->pos); }
// the squared distance from the camera to the body's root part
f32 camera_dist2(cEm10* em)
{
    const v3 d = vsub(V(pG->Cam.param.pos), V(em->getPartsPtr(0)->world));
    return d.x * d.x + d.y * d.y + d.z * d.z;
}
// the big spray: the lock held by another Ganado's big spray makes this one the near / far variant of the locked set
void blood_big(cEm10* em, Em10Work* w, f32 dist2)
{
    const bool near = (dist2 < kNearBlood2) != (em10p_control == 2);
    if (Ctrl12Ck(w->pCtrl12, CTRL12_ID_BIGEFF)) {
        blood(em, near ? (water(em) ? 0x40 : 0x37) : (water(em) ? 0x3E : 0x35));
        return;
    }
    blood(em, near ? (water(em) ? 0x3F : 0x36) : (water(em) ? 0x3C : 0x02));
    Ctrl12Set(w->pCtrl12, CTRL12_ID_BIGEFF, kBigEffLock);
}
void blood_small(cEm10* em) { blood(em, water(em) ? 0x3B : 0x01); }
void blood_shot(cEm10* em)
{
    blood(em, water(em) ? 0x3D : 0x0C);
    if ((eng_pres_u8() & 3) == 0) {   // a quarter of the hits: the scatter at the damage position
        Vec pos, dir;
        if (EmGetDmPos(em, &pos, &dir)) EstSet(0, -1, &pos, 0, 0x10, 0x0D, 0, 0, 0, 0);
    }
}
// the blast's sprites (0x88) stuck to the hit part: each placed at the damage position in the part's own frame
void blood_blast(cEm10* em, const YARARE_INFO* part)
{
    blood(em, 0x87);
    Vec pos, dir;
    if (!EmGetDmPos(em, &pos, &dir)) return;
    EspSeqData* est = EspGetEstAddr(0x10, 0x88, 1);
    if (!est) return;
    cModel* parent = em->getPartsPtr(part->partsNo - 1);
    const FrameInverse inv = frame_inverse(frame_of(parent->mat));
    const v3 local = inverse_point(inv, V(pos));
    for (u32 i = 0; i < est->num; i++) {
        cEsp* esp;
        if (!EspEstSetSelect(0x10, 0x88, i, &esp, 0)) continue;
        put(&esp->m_Pos, local);
        esp->parent = parent;
        esp->m_Parts_no = (u8) ((part->partsNo & 0xFF) - 1);
        em10p_cnt.blood_parts++;
    }
}
void blood_by_class(cEm10* em, Em10Work* w, u8 cls, int near, f32 dist2, const YARARE_INFO* part)
{
    switch (cls) {
    case B_NONE: return;
    case B_SMALL: blood_small(em); return;
    case B_MAGNUM: blood(em, 0x29); return;
    case B_SHOT: blood_shot(em); return;
    case B_RIFLE: if (near) blood_big(em, w, dist2); else blood_small(em); return;
    case B_BLAST: blood_blast(em, part); return;
    default: blood_big(em, w, dist2); return;
    }
}
}   // namespace

// ---- the sound numbers of a voice kind ----
extern "C" void Em10SetSeTbl(cEm10* em, int type)
{
    Em10Work* w = EM10_WK(em);
    em10p_cnt.se_tables++;
    __builtin_memcpy(w->Se_tbl, kVoiceSet[(u32) type < 4 ? type : 0], sizeof(w->Se_tbl));
    if (em->type == 6) w->Se_tbl[0] = kMerchantVoice;
}

// ---- voices ----
// the voice `no` of the model type's bank, stopping the voice and breath playing; the breath re-armed
extern "C" void em10CallVoiceSe(cEm10* em, u16 no)
{
    Em10Work* w = EM10_WK(em);
    voice_stop(w);
    if (muted(w)) return;
    em10p_cnt.voices++;
    w->Seid_voice = Ctrl11StopAndSetSe(w->pCtrlSe, em, voice_rate(), no, voice_bank(em->type));
    w->Breath_se_wait = breath_wait();
}
// the voice `no` from bank block `a` (the death cry, the "behind you" call)
void em10CallVoiceSe2(cEm10* em, int no, int a)
{
    Em10Work* w = EM10_WK(em);
    voice_stop(w);
    if (muted(w)) return;
    em10p_cnt.voices2++;
    w->Seid_voice = Ctrl11SetSe2I(w->pCtrlSe, em, voice_rate(), no, kVoiceSlot, a);
    w->Breath_se_wait = breath_wait();
}
// the breath (Se_tbl[7]) each time its timer runs out
void em10BreathSe(cEm10* em)
{
    Em10Work* w = EM10_WK(em);
    if (w->Breath_se_wait) {
        w->Breath_se_wait--;
        return;
    }
    w->Breath_se_wait = breath_wait();
    if (muted(w)) return;
    em10p_cnt.breaths++;
    w->Seid_breath = Ctrl11SetSe(w->pCtrlSe, em, voice_rate(), w->Se_tbl[7], kVoiceSlot);
}
// the hit's voice: the death cry when killed (and the parasite's screech when it is out), else voice `a`
void em10SetDamageVoice(cEm10* em, int a, int b)
{
    Em10Work* w = EM10_WK(em);
    em10p_cnt.damage_voices++;
    if (em->hp > 0) {
        if (!muted(w)) em10CallVoiceSe(em, (u16) a);
        return;
    }
    if (!muted(w)) em10CallVoiceSe2(em, b, 8);
    const bool parasite_out = !claw_type(em) && (w->pParasite || w->pCore);
    if (!parasite_out) return;
    voice_stop(w);
    w->Seid_voice = Ctrl11SetSe2(w->pCtrlSe, em, voice_rate(), 0x89, kVoiceSlot, 8);
    w->Breath_se_wait = breath_wait();
}

// ---- the chainsaw's tell: the far rev on its own timer, the near rev every 150 ticks ----
extern "C" void em10CsawSignSe(cEm10* em)
{
    Em10Work* w = EM10_WK(em);
    const bool sawing = (w->flags & 0x80000000) && w->Wep_type == 4 && (s16) pG->pl_life > 0;
    if (!sawing) return;
    em10p_cnt.csaw++;
    const bool far = em->plDist2 > 25000000.0f;
    if (far) {
        if (w->Csaw_fake_timer) {
            w->Csaw_fake_timer--;
            return;
        }
        w->Csaw_fake_timer = (u16) (pres(150) + 150);
        w->Csaw_sign_wait = 150;
        w->Seid_csaw = SndCall(6, 0x4B, &em->pos, 0, 0, em);
        return;
    }
    if (w->Csaw_sign_wait != 0) return;
    SndStop(w->Seid_csaw, 0);
    w->Seid_csaw = SndCall(6, 0x3E, &em->pos, 0, 0, em);
    w->Csaw_sign_wait = 150;
    w->Csaw_fake_timer = (u16) (pres(150) + 150);
}

// ---- "behind you": a Ganado close behind the player's back who sees him calls out, and locks the call for all ----
extern "C" void em10BehindSeCk(cEm10* em)
{
    Em10Work* w = EM10_WK(em);
    if (Ctrl12Ck(w->pCtrl12, CTRL12_ID_BACKSIGN)) return;
    const bool close_behind = w->Atk_wait == 0 && !(em->plDist2 > 9000000.0f) && !(w->Pl_rot > 1.5707964f) &&
                              w->Wep_type != 4 && !(__builtin_fabsf(Muku(&pPL->pos, &em->pos, pPL->ang.y, 3.1415927f)) < 1.5707964f) &&
                              (w->flags & 1);
    if (!close_behind) return;
    em10p_cnt.behind++;
    em10CallVoiceSe2(em, w->Se_tbl[16], 8);
    Ctrl12Set(w->pCtrl12, CTRL12_ID_BACKSIGN, 300);
    w->Breath_se_wait = (u16) (Rnd() % 120 + 120);   // the behaviour generator, as the original (eng-e2b.md)
}

// ---- footsteps ----
void em10FootSe(cEm10* em)
{
    Em10Work* w = EM10_WK(em);
    const bool claw = claw_type(em);
    const bool flail = w->Wep_type == 0xB;
    if ((claw || flail) && w->Chain_se_wait && --w->Chain_se_wait == 0) {
        em10p_cnt.chain_rattles++;
        SndCall(8, 0xA0, &em->getPartsPtr(0)->world, em->id, 0, em);
    }
    if (em->seNo == 0) return;
    em10p_cnt.feet++;
    const u32 step = em->seNo - 1;
    if (CheckInWater(em, 0) && (step <= 5 || step == 0x77)) {   // wading: no step sound
        em->seNo = 0;
        return;
    }
    if (claw && (step == 4 || step == 5)) {
        em->seNo = 0;
        SndCall(6, kClawLand[step - 4], &em->getPartsPtr(0)->world, 0, 0, em);
        return;
    }
    if (step > 3) return;
    const Step& s = (claw ? kStepClaw : kStepVillage)[step];
    if (claw || flail) {
        if (s.chain == 1) w->Chain_se_wait = 1;
        else SndCall(8, 0xA4, &em->getPartsPtr(0)->world, em->id, 0, em);
    }
    em->seNo = 0;
    const int foot = em10p_control == 3 ? (s.foot == 0x15 ? 0x19 : 0x15) : s.foot;
    cModel* p = em->getPartsPtr(foot);
    em10p_cnt.step_sounds++;
    SndCall(5, s.sound, &p->world, 0, 0, em);
    if (ChkWaterEffectEnable(&em->pos)) {   // the ripple on the floor under the foot
        Vec v = p->world;
        v.y = SatMgr.getFloor(&v, 600.0f, 100000.0f, 0, 0);
        EstSet(0, -1, &v, 0, 0x10, 0x3A, 0, 0, 0, 0);
    }
}

// ---- the weapon's sound and effect numbers ----
extern "C" void em10WepSeEffSet(cEm10* em, cEmWep* wep, int type)
{
    if (!wep) return;
    const WepSound& s = (u32) type < 17 ? kWepSound[type] : kWepSoundOther;
    if (s.none) return;
    em10p_cnt.wep_sets++;
    wep->setSeDamage(8, 0x3F, em->id);
    wep->setSeHit(8, s.hit, em->id);
    wep->setSeFall(8, s.fall, em->id);
    wep->setSeThrow(8, s.thrown, em->id, 4);
    wep->setEffDamage(0, 0x18);
    wep->setEffHit(0x10, 0x0B);
    wep->setEffWater(1, 0x37);
}

// ---- blood at a hit ----
void em10BloodSet(cEm10* em, int near)
{
    if (claw_type(em)) {
        em1cBloodSet(em, near);
        return;
    }
    Em10Work* w = EM10_WK(em);
    const f32 dist2 = camera_dist2(em);
    const YARARE_INFO* part = em->dmg.m_pDamageYarare;
    if (!part) return;
    em10p_cnt.bloods++;
    const u8 cls = blood_class(kBloodEm10, em->dmg.m_Wep);
    if (em10ArmorCk(em, part->partsNo)) {   // armour: a spark, the rifle's near one bigger
        if (cls == B_NONE || cls == B_ARMOUR) return;
        blood(em, cls == B_RIFLE && near ? 0x65 : 0x64);
        return;
    }
    if (part->partsNo == kHeadPart && (w->pCore || w->pParasite)) {   // the parasite's own blood at the head
        blood(em, 0x26);
        return;
    }
    blood_by_class(em, w, cls == B_ARMOUR ? (u8) B_BIG : cls, near, dist2, part);
}
// the parasite-headed types (0xA / 0xD)
void em1cBloodSet(cEm10* em, int near)
{
    Em10Work* w = EM10_WK(em);
    const f32 dist2 = camera_dist2(em);
    const YARARE_INFO* part = em->dmg.m_pDamageYarare;
    const u8 wep = em->dmg.m_Wep;
    em10p_cnt.bloods_1c++;
    if (part->partsNo == kParasitePart) {
        if (wep == 0 || wep == 0x14 || (wep >= 0x22 && wep <= 0x25)) return;
        const u8 cls = blood_class(kBloodEm1c, wep);
        const bool small = cls == B_SMALL || cls == B_MAGNUM || cls == B_SHOT || (cls == B_RIFLE && !near);
        blood(em, small ? 0x26 : 0x27);
        return;
    }
    const bool armour = em10ArmorCk(em, part->partsNo);
    const u8 cls = blood_class(kBloodEm1c, wep);
    if (cls == B_NONE) return;
    if (armour) {
        blood(em, cls == B_RIFLE && near ? 0x65 : 0x64);
        return;
    }
    blood_by_class(em, w, cls, near, dist2, part);
}

// ---- the kick's hit mark at the hip, facing where the kick came from ----
void em10KickHitMark(cEm10* em)
{
    cModel* hip = em->getPartsPtr(4);
    Vec rot = {0.0f, GetXZAngle(&em->dmg.m_PosFrom, &em->pos), 0.0f};
    em10p_cnt.marks++;
    EstSet(0, -1, &hip->world, &rot, 0x10, ChkWaterEffectEnable(&em->pos) ? 0x38 : 0x25, 0, 0, 0, 0);
}

// ---- water ----
// a hit or a fall in water: the splash (a 0 small, 1 big) and its sound, at most every 5 / 10 ticks
void em10SetDmWaterEff(cEm10* em, int a)
{
    Em10Work* w = EM10_WK(em);
    if (!CheckInWater(em, 4) || w->Water_eff_wait3 != 0) return;
    const bool big = a == 1;
    em10p_cnt.water_hits++;
    cModel* root = em->getPartsPtr(0);
    EstSet((int) em, -1, 0, 0, 1, big ? 0x33 : 0x34, 0, 0, (u32) em, 0);
    SndCall(6, big ? 0x16 : 0x11, &root->world, 0, 0, em);
    w->Water_eff_wait3 = big ? 10 : 5;
}
// standing in water: a ripple every 9 ticks; wading (moved more than 15 units across): a splash and its sound every 6
void em10SetWaterEff(cEm10* em)
{
    Em10Work* w = EM10_WK(em);
    if ((w->flags & 0x00400000) || !CheckInWater(em, 4)) return;
    em10p_cnt.water_wades++;
    if (w->Water_eff_wait) w->Water_eff_wait--;
    else {
        w->Water_eff_wait = 8;
        EstSet((int) em, -1, 0, 0, 1, 0x30, 0, 0, (u32) em, 0);
    }
    const f32 dx = em->pos.x - em->pos_old.x, dz = em->pos.z - em->pos_old.z;
    if (!(dx * dx + dz * dz > 225.0f)) return;
    if (w->Water_eff_wait2) w->Water_eff_wait2--;
    else {
        w->Water_eff_wait2 = 5;
        EstSet((int) em, -1, 0, 0, 1, 0x31, 0, 0, (u32) em, 0);
        SndCall(6, 0x11, &em->pos, 0, 0, em);
    }
}
