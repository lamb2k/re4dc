// em10_model.cpp (lane eng-e2b, 2026-11-21): the Ganado's model set-up and lifetime, native. Which model parts its body
// wears (the head, the hands for each pose and weapon grip, the merchant's coat and goods, the chainsaw man's sack, the
// hats, hoods, lanterns, glasses and other accessories its flags ask for), the motion blend of the aiming poses, and
// what it gives back when its record is destroyed. The behaviour (em10.cpp's routines) calls these by their original
// names and keeps its decisions (which pose, which head, when); em10's bodies are weak in the image and in the PC
// reference's native build.
//
// Engine form: a part change is one engine routine (wear: a model info made by the model service, ModInfoMgr.create,
// swapped in for the part's old one or added to the body); the accessory rules are a table per body group (village,
// zealot, soldier, gatling), each row a flag that asks for it, the two model files (a motion-table slot or an archive
// entry), where it goes and what it hides; the hand poses a table of motion-table slots with the grip and the mirror
// rules. Objects hung on the body are the object factory's (SetObj12) and are parented through the object; the blend is
// the motion service's (MotionSetCore); the lifetime gives the owned objects back to their pools in the original's order
// (the pool's free order decides later slots).
//
// Randomness: em10HeadSet's bent-neck head (the zealot's lost-head variant) draws from the behaviour generator, as the
// original does in both builds today (not in the split list): moving it needs a reference change (eng-e2b.md).
#define fabsf em10m_game_fabsf
#include "types.h"
#include "global.h"
#include "model.h"
#include "em.h"
#include "em10.h"
#include "obj.h"
#include "motion.h"
#include "atari.h"
#include "atari_init.h"
#include "esp.h"
#include "snd.h"
#include "db_log.h"
#include "foot_shadow.h"
#include "rnd.h"
#undef fabsf

extern "C" {
struct Em10ModelCounters {
    u32 inits, wears, swaps, adds, refused, accessories, objects, hands, heads, blends, released;
};
Em10ModelCounters em10m_cnt;
// Controls (set only by the PC check, hostref svc/e2b_dump.cpp RE4_SVC_CONTROL; each must make e2b.txt differ):
// 1 "handgrip": the weapon grip not forced (the pose asked is worn); 2 "accnone": the village's accessory rules skipped;
// 3 "keepcap": the destructor leaves the hung object (pCap) alive.
int em10m_control;

void em10SetAccesory(cEm10* em);
void em10ClothPartsSet(cEm10* em, int no);
void em10GoodsPartsSet(cEm10* em, int on);
void em10SackSet(cEm10* em);
void em10BlendMotSet(cEm10* em, void* m0, void* m1, void* m2, int a, int b, int c, int d);
void em10WeaponInit(cEm10* em);   // the behaviour's (hosted): which weapon it carries
void em10ShieldSet(cEm10* em);    // the behaviour's (hosted): the zealot's shield
void cModel_swapModelInfo(cModel* m, ModelData* old, cModelInfo* info) asm("swapModelInfo__6cModelP9ModelDataP10cModelInfo");
}
void em10HandSet(cEm10* em, int type);
void em10HeadSet(cEm10* em, int no);
int em10ModelInit(cEm10* em);
extern FootShadowTbl Em10_fs_tbl;

namespace {
// the claw, gatling and the two event types wear no hand or head models of their own
bool no_hands(const cEm10* em) { return em->type == 10 || em->type == 13 || em->type == 2 || em->type == 22 || em->type == 24; }
bool no_head(const cEm10* em) { return em->type == 10 || em->type == 13 || em->type == 2 || em->type == 22; }
void hide(cModelInfo* m) { if (m) m->be_flag &= ~8; }

// wear (bin, tpl) in place of `old` (or added when there is none); the new info, or 0 when the model service refused
cModelInfo* wear(cEm10* em, cModelInfo* old, void* bin, void* tpl)
{
    cModelInfo* info = ModInfoMgr.create(bin, tpl);
    em10m_cnt.wears++;
    if (!info) {
        em10m_cnt.refused++;
        return 0;
    }
    if (old) {
        em10m_cnt.swaps++;
        cModel_swapModelInfo(em, old->pData, info);
    } else {
        em10m_cnt.adds++;
        em->addModel(info);
    }
    return info;
}

// ---- accessories ----
// a model file: a slot of the motion table (>= 0) or an archive entry (ARC | entry)
enum : u16 { ARC = 0x8000 };
void* file(cEm10* em, u16 f) { return (f & ARC) ? PL_ARC_PTR(em->subArc, f & ~ARC) : EM10_WK(em)->mot[f]; }
bool present(cEm10* em, u16 f) { return (f & ARC) || EM10_WK(em)->mot[f]; }   // archive entries are not tested
enum Kind : u8 { HANG, GLASSES, PART };
enum Slot : u8 { CAP, GLASS, HOOD, WHOOD, ACC0 };   // ACC0 + n: pAccesory[n]
enum : u8 { HIDE_HEAD = 1, IF_EMPTY = 2, NO_TEST = 4, UNHOOD = 8 };
struct Acc {
    u32 flag;       // the cEm flag bit that asks for it
    u16 bin, tpl;   // its two model files
    u8 kind, slot, how;
    u8 cap_kind;    // a hung object's kind (Cap_type)
    f32 y, z;       // a hung object's place on the hip part (4)
};
// the village (types 0, 1, 3, 4, 6 and every type not listed below): hung objects first (one at most), then the glasses,
// then the hood parts
const Acc kVillage[] = {
    {0x00800000, 52, 53, HANG, CAP, IF_EMPTY, 1, 125.7f, 20.0f},
    {0x00080000, 52, 54, HANG, CAP, IF_EMPTY, 2, 125.7f, 20.0f},
    {0x00400000, 55, 56, HANG, CAP, IF_EMPTY, 3, 5.0f, 0.0f},
    {0x00040000, 55, 57, HANG, CAP, IF_EMPTY, 4, 5.0f, 0.0f},
    {0x00000200, 58, 59, HANG, CAP, IF_EMPTY, 5, 87.0f, 11.0f},
    {0x00000100, 58, 60, HANG, CAP, IF_EMPTY, 6, 87.0f, 11.0f},
    {0x00200000, 61, 62, GLASSES, GLASS, 0, 0, 54.71f, 72.73f},
    {0x00400000, 23, 24, PART, WHOOD, 0, 0, 0, 0},
    {0x00040000, 23, 25, PART, WHOOD, 0, 0, 0, 0},
};
// the zealots (types 5, 7, 8, 9): hoods, then the accessory parts; mot[0] is the body's texture file
const Acc kZealot[] = {
    {0x00080000, 26, 0, PART, HOOD, 0, 0, 0, 0},
    {0x00001000, 27, 0, PART, HOOD, HIDE_HEAD | UNHOOD, 0, 0, 0},
    {0x00800000, 28, 29, PART, ACC0 + 0, 0, 0, 0, 0},
    {0x00400000, 30, 31, PART, ACC0 + 1, 0, 0, 0, 0},
    {0x00040000, 32, 33, PART, ACC0 + 2, 0, 0, 0, 0},
    {0x00000002, 32, ARC | 0x220, PART, ACC0 + 2, IF_EMPTY, 0, 0, 0},
    {0x00000200, 34, 35, PART, ACC0 + 3, HIDE_HEAD, 0, 0, 0},
    {0x00000100, 36, 37, PART, ACC0 + 4, 0, 0, 0, 0},
    {0x00200000, 38, 39, PART, ACC0 + 5, 0, 0, 0, 0},
    {0x00004000, 38, 40, PART, ACC0 + 5, IF_EMPTY, 0, 0, 0},
};
// the soldiers (types 0xE..0x15, 0x17, 0x18): the archive's models
const Acc kSoldier[] = {
    {0x00800000, ARC | 0x265, ARC | 0x266, HANG, CAP, IF_EMPTY, 9, 80.0f, 0.0f},
    {0x00200000, ARC | 0x262, ARC | 0x263, HANG, CAP, IF_EMPTY, 9, 80.0f, 0.0f},
    {0x00080000, ARC | 0x262, ARC | 0x263, HANG, CAP, IF_EMPTY, 9, 80.0f, 0.0f},
    {0x00000200, ARC | 0x24F, ARC | 0x250, PART, ACC0 + 3, HIDE_HEAD, 0, 0, 0},
    {0x00000100, ARC | 0x243, ARC | 0x244, PART, ACC0 + 2, 0, 0, 0, 0},
    {0x00000002, ARC | 0x245, 0, PART, ACC0 + 2, IF_EMPTY | NO_TEST, 0, 0, 0},
    {0x00040000, ARC | 0x23D, ARC | 0x23E, PART, HOOD, IF_EMPTY, 0, 0, 0},
    {0x00004000, ARC | 0x23F, ARC | 0x240, PART, HOOD, IF_EMPTY, 0, 0, 0},
    {0x00001000, ARC | 0x241, ARC | 0x242, PART, HOOD, IF_EMPTY, 0, 0, 0},
};
// the gatling man (type 2): his hung ammunition box, always
const Acc kGatling[] = {{0, ARC | 0x25F, ARC | 0x260, HANG, CAP, 0, 0xA, 155.38f, 23.4f}};

void*& slot_of(Em10Work* w, u8 s)
{
    switch (s) {
    case CAP: return (void*&) w->pCap;
    case GLASS: return (void*&) w->pGlasses;
    case HOOD: return (void*&) w->pHood;
    case WHOOD: return (void*&) w->pWhood;
    default: return (void*&) w->pAccesory[s - ACC0];
    }
}
// one rule: a hung object made by the object factory and parented to the hip, or a model part worn on the body (the
// model service's refusal is passed on to addModel, as the original does)
void accessory(cEm10* em, const Acc& r)
{
    Em10Work* w = EM10_WK(em);
    void*& dst = slot_of(w, r.slot);
    if (r.flag && !(em->flag & r.flag)) return;   // (flag 0: always)
    if ((r.how & IF_EMPTY) && dst) return;
    if (!(r.how & NO_TEST) && !(present(em, r.bin) && present(em, r.tpl))) return;
    em10m_cnt.accessories++;
    if (r.kind == PART) {
        cModelInfo* info = ModInfoMgr.create(file(em, r.bin), file(em, r.tpl));
        em->addModel(info);
        dst = info;
        if (r.how & HIDE_HEAD) hide(w->pHead);
        if (r.how & UNHOOD) em->flag &= ~0x00204000;
        return;
    }
    Vec pos = {0.0f, r.y, r.z}, rot = {0.0f, 0.0f, 0.0f};
    cObj* o = SetObj12(file(em, r.bin), file(em, r.tpl), &pos, &rot);
    dst = o;
    if (!o) return;
    em10m_cnt.objects++;
    ((cObj12*) o)->setParent(em, 4, 1);
    if (r.kind == HANG) w->Cap_type = r.cap_kind;
}
template <unsigned N> void accessories(cEm10* em, const Acc (&rules)[N])
{
    if (em10m_control == 2 && rules == kVillage) return;
    for (unsigned i = 0; i < N; i++) accessory(em, rules[i]);
}
}   // namespace

extern "C" void em10SetAccesory(cEm10* em)
{
    Em10Work* w = EM10_WK(em);
    w->pCap = 0;
    w->Cap_type = 0;
    w->pGlasses = 0;
    w->pHood = 0;
    w->pWhood = 0;
    for (int i = 0; i < 7; i++) w->pAccesory[i] = 0;
    switch (em->type) {
    case 0xA: case 0xD:
        return;
    case 5: case 7: case 8: case 9: {
        // the zealots' head cover: a cap or a hood asked by bit 1 or 18 is the hood (bit 19) unless a helmet (bit 12)
        // or bit 19 is set already; a helmet or a mask (bits 8, 9) takes the helmet instead of the hood
        u32 f = em->flag;
        if ((f & 0x00040002) && !(f & 0x00081000)) f |= 0x00080000;
        if (f & 0x300) f = (f & ~0x00080000) | 0x1000;
        em->flag = f;
        accessories(em, kZealot);
        return;
    }
    case 0xE: case 0xF: case 0x10: case 0x11: case 0x12: case 0x13: case 0x14: case 0x15: case 0x17: case 0x18:
        accessories(em, kSoldier);
        return;
    case 2:
        accessories(em, kGatling);
        return;
    default:
        accessories(em, kVillage);
        return;
    }
}

// ---- hands ----
// the two hand models of each pose: [pose][0 right, 1 left] as motion-table slots; pose 2 (pointing) differs for a
// left-handed Ganado (flag bit 24); a weapon grips in the right (the left for the left-handed): slot 9 / 14, both for the
// hoe and the chainsaw, the scythe's left grip 15; the rocket launcher's right hand from the archive (0x18E)
const u8 kHandPose[3][2] = {{6, 11}, {7, 12}, {8, 11}};
const u8 kHandPoseLeft2[2] = {6, 13};
void em10HandSet(cEm10* em, int type)
{
    Em10Work* w = EM10_WK(em);
    if (no_hands(em)) return;
    if (w->pWep && em10m_control != 1) type = 3;   // a weapon in hand: the grip
    if (w->pRHand && w->pLHand && w->Hand_type == type) return;
    em10m_cnt.hands++;
    const bool lefty = em->flag & 0x01000000;
    const u32 pose = (u32) type < 3 ? (u32) type : 0;
    const u8* pair = (pose == 2 && lefty) ? kHandPoseLeft2 : kHandPose[pose];
    void* right = w->mot[pair[0]];
    void* left = w->mot[pair[1]];
    if (w->pWep) {
        if (lefty) left = w->mot[14];
        else right = w->mot[9];
        if (w->Wep_type == 1 || w->Wep_type == 4) right = w->mot[9], left = w->mot[14];
        if (w->Wep_type == 6) left = w->mot[15];
    }
    if (w->Wep_type == 12) right = PL_ARC_PTR(em->subArc, 0x18E);
    if (cModelInfo* r = wear(em, w->pRHand, right, w->mot[0])) w->pRHand = r;
    if (cModelInfo* l = wear(em, w->pLHand, left, w->mot[0])) w->pLHand = l;
    w->Hand_type = (u8) type;
}

// ---- the head ----
// 0 the head; 1 the lost head: the stump, or for a living zealot without hood or mask, three times in four (the
// behaviour generator), the bent-neck parasite head with the neck part (0x24) tilted 40 degrees
void em10HeadSet(cEm10* em, int no)
{
    Em10Work* w = EM10_WK(em);
    if (no_head(em)) return;
    em10m_cnt.heads++;
    void* bin = w->mot[2];
    if (no == 1) {
        const bool bent = w->Ganado == 1 && em->hp > 0 && (Rnd() & 3) && !(em->flag & 0x204000);
        if (bent) em->getPartsPtr(0x24)->ang.x = -0.6981317f;
        bin = bent ? w->mot[4] : w->mot[3];
    }
    if (cModelInfo* info = wear(em, w->pHead, bin, w->mot[5])) {
        w->pHead = info;
        info->be_flag |= 8;
    }
}

// ---- the merchant's coat (type 6): open (1) or closed, and the goods inside it shown or hidden ----
extern "C" void em10ClothPartsSet(cEm10* em, int no)
{
    Em10Work* w = EM10_WK(em);
    if (em->type != 6) return;
    if (cModelInfo* info = wear(em, w->pCloth, no == 1 ? w->mot[18] : w->mot[19], w->mot[17])) w->pCloth = info;
}
extern "C" void em10GoodsPartsSet(cEm10* em, int on)
{
    Em10Work* w = EM10_WK(em);
    if (em->type != 6) return;
    if (!w->pGoods) w->pGoods = wear(em, 0, w->mot[20], w->mot[0]);
    if (!w->pGoods) return;   // (the original writes through the refused info)
    if (on) w->pGoods->be_flag |= 8;
    else w->pGoods->be_flag &= ~8;
}
// ---- the chainsaw man's sack over the head; types 11 and 12 hide the head and start its effect (0x55) ----
extern "C" void em10SackSet(cEm10* em)
{
    Em10Work* w = EM10_WK(em);
    if (w->Wep_type != 4 || !w->mot[21] || !w->mot[22]) return;
    if (cModelInfo* info = wear(em, w->pSack, w->mot[21], w->mot[22])) w->pSack = info;
    if ((u8) (em->type - 11) <= 1) {
        hide(w->pHead);
        EstSet((int) em, -1, 0, 0, 0x10, 0x55, 0, 0, (u32) em, 0);
    }
}

// ---- the body at creation: the model, the merchant's robe, coat and goods, head, hands, foot shadows, accessories,
// the weapon and shield (the behaviour's), the sack ----
int em10ModelInit(cEm10* em)
{
    Em10Work* w = EM10_WK(em);
    if (!em->modelInit(w->mot[1], w->mot[0])) {
        pLog->err(0, 0, "EM10 pEm->modelInit() failed.");
        return 0;
    }
    em10m_cnt.inits++;
    w->pRobe = w->pCloth = w->pGoods = 0;
    if (em->type == 6) {
        if (w->mot[16] && w->mot[17]) w->pRobe = wear(em, 0, w->mot[16], w->mot[17]);
        em10ClothPartsSet(em, 0);
        em10GoodsPartsSet(em, 0);
    }
    w->pHead = 0;
    em10HeadSet(em, 0);
    w->pRHand = w->pLHand = 0;
    em10HandSet(em, 0);
    em->pFootShadowTbl = &Em10_fs_tbl;
    w->pCart = 0;
    em10SetAccesory(em);
    em10WeaponInit(em);
    em10ShieldSet(em);
    em10SackSet(em);
    return 1;
}

// ---- the aiming poses' blend: m0 on the body's motion, m1 (aiming down) or m2 (up) on the blend work, weighted by
// |blendRate| / 256; the blend's ease (Hokan) runs out and its frame advances, wrapping at the motion's length ----
extern "C" void em10BlendMotSet(cEm10* em, void* m0, void* m1, void* m2, int a, int b, int c, int d)
{
    Em10Work* w = EM10_WK(em);
    em10m_cnt.blends++;
    const f32 weight = __builtin_fabsf(w->blendRate) * (1.0f / 256.0f);
    const bool down = w->blendRate < 0.0f;
    MotionSetCore(em, MOTION(em), m0, a, (u8) w->Hokan, (u16) d, (u16) w->Frame);
    MotionWorkSub* bm = &w->blendMot;
    MotionSetCore(em, bm, down ? m1 : m2, down ? b : c, (u8) w->Hokan, (u16) d, (u16) w->Frame);
    em->blendMot = bm;
    bm->blendRate = weight;
    if (w->Hokan) w->Hokan--;
    if (++w->Frame >= em->frameMax) w->Frame = 0;
}

// ---- lifetime: what the Ganado owns goes back to its pool when its record is destroyed, in the original's order ----
namespace {
template <class Mgr, class T> void give_back(Mgr& mgr, T*& p)
{
    if (!p) return;
    if (p->isAlive()) {
        em10m_cnt.released++;
        mgr.destroy(p);
    }
    p = 0;
}
}   // namespace
cEm10::~cEm10()
{
    Em10Work* w = EM10_WK(this);
    if (w->pWep) give_back(EmMgr, w->pWep), w->Wep_type = 0;
    if (w->pWeapon2) give_back(EmMgr, w->pWeapon2), w->Wep_type2 = 0;
    if (em10m_control == 3) w->pCap = 0;
    give_back(ObjMgr, w->pCap);
    give_back(ObjMgr, w->pGlasses);
    if (w->pCart && w->mot[51]) {   // the cart he pushed goes back to standing, solid again
        cEm* cart = w->pCart;
        MotionSetCore(cart, MOTION(cart), w->mot[51], 0, 0, 0, 0);
        atariInitF(&cart->atari, 0.0f, 150.0f, -300.0f, 300.0f, 300.0f, 300.0f, 150.0f, 1, 0x2000, 10);
        cart->atari.m_flag = (cart->atari.m_flag & ~0x100) | 0x200 | 0x10;
        w->pCart = 0;
    }
    if (w->Wep_type == 4) SndStop(w->sndId, 0);   // the chainsaw's loop
    cObj* belt = (cObj*) w->pGunBelt;
    give_back(ObjMgr, belt);
    w->pGunBelt = 0;
    cObj* chain = (cObj*) w->pChain;
    give_back(ObjMgr, chain);
    w->pChain = 0;
    give_back(ObjMgr, w->pCore);
    if (w->pParasite) {
        if (w->pParasite->isAlive()) w->pParasite->setReset();
        w->pParasite = 0;
    }
}
