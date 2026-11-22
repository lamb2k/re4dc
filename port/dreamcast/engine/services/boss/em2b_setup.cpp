// em2b_setup.cpp (lane eng-e2c): the giant's set-up requests at its first move, native: the chained form's arm cloth
// (type 1), the village giant's rope chain between its neck parts (type 0, this arena's), the chained form's three arm
// chains (type 3), and room 224's texture-render manager for the hole attack's freeze.
//
// Engine form: each pendulum chain is a row of one table of chain descriptions (the links and their neighbours, the swing
// limits and damping, the collision volumes it keeps off the giant's body, gravity, damping, constraint iterations and
// stiffness) written whole into the giant's chain record, then handed to the cloth service (PenClothSet) or to a chain
// object made from the giant's archive (SetChain, then the object's setChain and its attachment to one or two parts). The
// tables are the engine's copy of the original's data. In the boss image the cloth service and the chain object kind are
// not present yet (logged stubs: host/e1_svc_stubs.cpp, boss/boss_stubs2.cpp); the requests are made as the original makes
// them, so the stubs' counts are unchanged. The texture-render manager is the renderer's: asked of the controller
// (Ctrl12GetTexRenderEm2b: a stub in the boss image, which answers none) and refused and counted when there is none.
#define fabsf e2c_game_fabsf
#include "types.h"
#include "global.h"
#include "model.h"
#include "em.h"
#include "obj.h"
#include "ctrl.h"
#include "TexRender.h"
#include "pendulum.h"
#include "pl_cloth.h"
#include "db_log.h"
#include "em2b.h"
#undef fabsf
#include "boss_svc.h"

namespace {
// ---- the chain descriptions (the original's tables: em2b.cpp em2b_cloth_*, em2b_rope_*, em2b_chain_*) ----
const u8 kClothParts[12] = {0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0, 0};
const u8 kClothUp[12] = {0xFF, 0x40, 0xFF, 0x42, 0xFF, 0x44, 0xFF, 0x46, 0xFF, 0x48, 0, 0};
const u8 kClothDown[12] = {0x41, 0xFF, 0x43, 0xFF, 0x45, 0xFF, 0x47, 0xFF, 0x49, 0xFF, 0, 0};
const u8 kClothSide[12] = {0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0xFF, 0xFF, 0, 0};
const f32 kClothMax[10] = {0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f};
const f32 kClothRate[10] = {0.8f, 0.8f, 0.8f, 0.8f, 0.8f, 0.8f, 0.8f, 0.8f, 0.8f, 0.8f};
CLOTH_AT_SET kClothAt[2] = {
    {0, 4, 4, 1.0f, 300.0f, {0.0f, -200.0f, 210.0f}, {0.0f, 0.0f, 0.0f}},
    {0, 4, 4, 1.0f, 300.0f, {0.0f, -300.0f, 250.0f}, {0.0f, 0.0f, 0.0f}},
};
const u8 kRopeParts[8] = {1, 2, 3, 4, 5, 0, 0, 0};
const u8 kRopeUp[8] = {0xFF, 1, 2, 3, 4, 0, 0, 0};
const u8 kRopeDown[8] = {2, 3, 4, 5, 0xFF, 0, 0, 0};
const u8 kChainParts[8] = {1, 2, 3, 4, 5, 6, 7, 8};
const u8 kChainUp[8] = {0xFF, 1, 2, 3, 4, 5, 6, 7};
const u8 kChainDown[8] = {2, 3, 4, 5, 6, 7, 8, 0xFF};
// the rope's and the first arm chain's volumes are the same five
CLOTH_AT_SET kRopeAt[5] = {
    {0, 3, 3, 1.0f, 650.0f, {-70.0f, 0.0f, 0.0f}, {-70.0f, 0.0f, 0.0f}},
    {0, 2, 3, 0.5f, 750.0f, {70.0f, 0.0f, 0.0f}, {70.0f, 0.0f, 0.0f}},
    {0, 2, 2, 1.0f, 900.0f, {70.0f, 0.0f, 0.0f}, {70.0f, 0.0f, 0.0f}},
    {0, 5, 5, 1.0f, 700.0f, {70.0f, 0.0f, 0.0f}, {70.0f, 0.0f, 0.0f}},
    {0, 0xB, 0xB, 1.0f, 700.0f, {70.0f, 0.0f, 0.0f}, {70.0f, 0.0f, 0.0f}},
};
CLOTH_AT_SET kChainAt[5] = {
    {0, 3, 3, 1.0f, 650.0f, {-70.0f, 0.0f, 0.0f}, {-70.0f, 0.0f, 0.0f}},
    {0, 2, 3, 0.5f, 750.0f, {70.0f, 0.0f, 0.0f}, {70.0f, 0.0f, 0.0f}},
    {0, 2, 2, 1.0f, 900.0f, {70.0f, 0.0f, 0.0f}, {70.0f, 0.0f, 0.0f}},
    {0, 5, 5, 1.0f, 700.0f, {70.0f, 0.0f, 0.0f}, {70.0f, 0.0f, 0.0f}},
    {0, 0xB, 0xB, 1.0f, 700.0f, {70.0f, 0.0f, 0.0f}, {70.0f, 0.0f, 0.0f}},
};
CLOTH_AT_SET kChainAt2[5] = {
    {0, 2, 3, 0.5f, 900.0f, {0.0f, 0.0f, 150.0f}, {0.0f, 0.0f, 150.0f}},
    {0, 2, 2, 1.0f, 900.0f, {0.0f, 0.0f, 150.0f}, {0.0f, 0.0f, 150.0f}},
    {0, 1, 1, 1.0f, 850.0f, {0.0f, 0.0f, 150.0f}, {0.0f, 0.0f, 150.0f}},
    {0, 0x12, 0x12, 1.0f, 650.0f, {0.0f, 0.0f, 150.0f}, {0.0f, 0.0f, 150.0f}},
    {0, 0x16, 0x16, 1.0f, 650.0f, {0.0f, 0.0f, 150.0f}, {0.0f, 0.0f, 150.0f}},
};

// One pendulum chain: links, neighbours (side, up, down), per-link limits and damping, collision volumes, and the
// chain's gravity, damping, constraint iterations, stiffness and flags.
struct Chain {
    int num;
    const u8 *parts, *side, *up, *down;
    const f32 *max, *rate;
    CLOTH_AT_SET* at;
    int at_num;
    f32 gravity, damping;
    u32 bundle;
    f32 stretchy;
    u32 flag;
};
const Chain kArmCloth = {10, kClothParts, kClothSide, kClothUp, kClothDown, kClothMax, kClothRate, kClothAt, 2, 20.0f,
                         0.800000012f, 4, 0.0500000007f, 0x100};
const Chain kRope = {5, kRopeParts, 0, kRopeUp, kRopeDown, 0, 0, kRopeAt, 5, 20.0f, 0.800000012f, 100, 0.100000001f, 0};
const Chain kArmChain[3] = {
    {8, kChainParts, 0, kChainUp, kChainDown, 0, 0, kChainAt, 5, 30.0f, 0.800000012f, 0, 1.0f, 0},
    {8, kChainParts, 0, kChainUp, kChainDown, 0, 0, 0, 0, 30.0f, 0.800000012f, 0, 1.0f, 0},
    {8, kChainParts, 0, kChainUp, kChainDown, 0, 0, kChainAt2, 5, 30.0f, 0.800000012f, 0, 1.0f, 0},
};
// the arm chains' parts on the giant (the third description is written over the second's record: the original's)
const int kArmChainPart[3] = {0x3B, 0x40, 0x41};

// The chain record written whole: the description; no wind, no parent speed, no part table; the volumes on the giant.
void describe(PenCloth& c, const Chain& k, cEm* owner)
{
    c = PenCloth{};
    c.Num = k.num;
    c.pCloth = k.parts;
    c.pLeft = k.side;
    c.pParent = k.up;
    c.pChild = k.down;
    c.pMax = k.max;
    c.pRate = k.rate;
    c.pAtset = k.at;
    c.At_num = k.at_num;
    c.Gravity = k.gravity;
    c.Rate = k.damping;
    c.Bundle_num = k.bundle;
    c.Stretchy = k.stretchy;
    c.Flag = k.flag;
    c.pEm_at = owner;
    if (boss_control == 8 && &k == &kRope) c.Bundle_num = 99;   // control bossrope
}

// A chain object of the giant's archive (models `bin` and bin + 1) at the origin, given its record.
cObjChain* chain_object(cEm2b* em, int bin, PenCloth* c)
{
    Vec pos = {0.0f, 0.0f, 0.0f}, rot = {0.0f, 0.0f, 0.0f};
    cObjChain* o = SetChain(PL_ARC_PTR(em->subArc, bin), PL_ARC_PTR(em->subArc, bin + 1), &pos, &rot);
    o->setChain(c);
    boss_cnt.chains++;
    return o;
}
}   // namespace

// The chained form's arm cloth (type 1 only), on the cloth service with a link length of 100.
void em2bClothSet(cEm2b* em)
{
    if (em->type != 1) return;
    Em2bWork* w = EM2B_WK(em);
    describe(w->Cloth, kArmCloth, em);
    boss_cnt.cloths++;
    PenClothSet(em, &w->Cloth, 100.0f);
}

// The village giant's short rope: a rope object (archive models 0x11, 0x12) on the work's second chain record, hung
// between the neck parts 3 and 4.
void em2bShortRopeSet(cEm2b* em)
{
    Em2bWork* w = EM2B_WK(em);
    describe(w->rope[1], kRope, em);
    cObjChain* o = chain_object(em, 0x11, &w->rope[1]);
    w->pChain = (cObj*) o;
    Vec neck = {-290.0f, -162.949997f, 655.0f}, head = {-290.0f, -412.320007f, 39.1500015f};
    o->setParent2(em, 3, &neck, 4, &head, 0);
}

// The chained form's three arm chains (archive models 0x13, 0x14): the first on the work's first record, the other two
// on its second (written again for the third), each hung from one part.
void em2bChainSet(cEm2b* em)
{
    Em2bWork* w = EM2B_WK(em);
    cObj** slot[3] = {&w->pChain, &w->pChain2, &w->pChain3};
    for (int k = 0; k < 3; k++) {
        PenCloth* c = &w->rope[k == 0 ? 0 : 1];
        describe(*c, kArmChain[k], em);
        cObjChain* o = chain_object(em, 0x13, c);
        *slot[k] = (cObj*) o;
        Vec at = {0.0f, 0.0f, 0.0f};
        o->setParent(em, kArmChainPart[k], &at, 0);
    }
}

// Room 224's texture-render manager for the hole attack's freeze (the renderer's): asked of the giant's controller; none
// is refused and counted; with one, the work's blend table names its texture (wrap, 64 x 64). Other rooms: nothing.
void em2bTexrenderInit(cEm2b* em)
{
    if (pG->room_id != 0x224) return;
    Em2bWork* w = EM2B_WK(em);
    w->pMgr = Ctrl12GetTexRenderEm2b(w->pCtrlGroup);
    if (!w->pMgr) {
        boss_cnt.texrender_refused++;
        pLog->err(0, 0, "em2bTexrenderInit:: Manager alloc failed!!");
        return;
    }
    u8* t = w->Tex_buf;
    t[0] = 1, t[1] = 0, t[4] = 0xF7, t[5] = w->pMgr->texId;
    w->pMgr->m_Rep_type = 1;
    w->pMgr->m_H_size = w->pMgr->m_W_size = 0x40;
}
