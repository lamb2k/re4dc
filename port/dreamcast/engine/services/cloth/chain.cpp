// chain.cpp (lane eng-skel1): the chain object, native. A chain (object kind 0x1D, the original game/obj1d.cpp) is a
// small model the behaviour hangs on its characters: the chain Ganado's ball and chain, the gatling Ganado's ammunition
// belt, El Gigante's rope and arm chains, the trolley's chains. Its links swing as a pendulum chain of the cloth service.
// game/obj1d.cpp is not linked in any image.
//
// The behaviour makes and holds it through the original's names (SetChain, cObjChain::setChain / setParent /
// setParent2, ObjMgr.destroy, invisible_factor, setNoSuspend), so the object is a record of the engine's object pool
// (ObjMgr) constructed for kind 0x1D below, and the pool moves it every tick. Its state:
//   free     its own matrix from its angles, position and scale (or its motion)
//   hung     between two parts of a parent (one part twice for setParent): the frame half-way between the two parts'
//            frames (each frame part x own matrix, its axes made unit unless the flag keeps them; the two as
//            quaternions, the half-way rotation by slerp) placed at the mid-point of the two offsets in their parts
//   fading   90 ticks, then fades out by 0.1 a tick (or goes at once when off screen), then lost
//   lost     hidden and given back to the pool
// It dies with its parent. After its pose its pendulum chain is stepped by the cloth service (PenClothMove on the
// object's own bones), and the cloth's reset / warp request bits (be_flag 0x00E00000) are cleared.
//
// Engine form: the parent's two part frames are read from the skeleton's tables (skel_bone_mat: the bones do not become
// mailbox bones); the frame, quaternion and slerp work is the engine's math service (services/math: the SDK's maths,
// same operations); the matrices and the world pass are the skeleton's (partsMatCalc / partsWorldCalc / MotionMove).
// No random number is drawn.
#include "atari.h"
#include "obj.h"
#include "global.h"
#include "math_sub.h"
#include "motion.h"
#include "pendulum.h"
#include "db_log.h"
#include "skel.h"
#include <new>

void PenClothSet(cModel* m, PenCloth* c, f32 len);
void PenClothMove(cModel* m, PenCloth* c);

class cObjChain : public cObj {
public:
    virtual void move();
    virtual ~cObjChain() {}
    void setParent(cModel* parent, int parts, Vec* ofs, int flag);
    void setParent2(cModel* parent, int parts1, Vec* ofs1, int parts2, Vec* ofs2, int flag);
    void setChain(PenCloth* cloth);
};

extern "C" {
struct ChainCounters {
    u32 made, refused, moves, hung, steps, orphans, lost;
};
ChainCounters chain_cnt;
int chain_control;   // lane eng-skel1's control (RE4_SVC_CONTROL=chainmid): the hung link at its first offset, not the mid-point
}
extern "C" const char* svc_env(const char* name) __attribute__((weak));
extern void (*ObjInitFunc[0x40])(cObj*);

namespace {
enum { CH_FREE = 0, CH_FADE = 1, CH_LOST = 2, CH_HUNG = 3 };

void chain_init(cObj* p) { new (p) cObjChain(); }
// The object kind is registered by the first SetChain (not at start-up: an image whose behaviour makes no chain does
// not keep this unit, --gc-sections)
void chain_kind()
{
    static int done;
    if (done) return;
    done = 1;
    ObjInitFunc[0x1D] = chain_init;
    const char* c = svc_env ? svc_env("RE4_SVC_CONTROL") : 0;
    if (c && !__builtin_strcmp(c, "chainmid")) chain_control = 1;
}

void to_state(cObj* o, u8 s)
{
    o->r_no_0 = 1;
    o->r_no_1 = s;
    o->r_no_2 = 0;
    o->r_no_3 = 0;
}
void own_matrix(cObj* o)
{
    RotMatrix(o->mat, &o->ang);
    TransMatrix(o->mat, &o->pos);
    ScaleMatrix(o->mat, &o->scale);
}
// part x own, its three axes made unit (an axis of zero length becomes that axis' unit vector) unless kept
void part_frame(const f32 (*part)[4], f32 (*own)[4], bool keep, f32 (*out)[4])
{
    PSMTXConcat(part, own, out);
    if (keep) return;
    for (int c = 0; c < 3; c++) {
        Vec v = {out[0][c], out[1][c], out[2][c]};
        if (v.x == 0.0f && v.y == 0.0f && v.z == 0.0f) (&v.x)[c] = 1.0f;
        VECNormalize(&v, &v);
        out[0][c] = v.x;
        out[1][c] = v.y;
        out[2][c] = v.z;
    }
}
// the hung pose: own matrix, then (with a parent that has parts) the half-way frame and the offsets' mid-point
void hang(cObj* o)
{
    ChainWork& w = o->chain;
    own_matrix(o);
    cModel* par = w.parent;
    Mtx pa, pb;
    if (par && par->pParts && skel_bone_mat(par, w.parts1, pa) == 0 && skel_bone_mat(par, w.parts2, pb) == 0) {
        const bool keep = (w.flags & 2) != 0;
        Mtx fa, fb;
        part_frame(pa, o->mat, keep, fa);
        part_frame(pb, o->mat, keep, fb);
        Quaternion qa, qb, q;
        C_QUATMtx(&qa, fa);
        C_QUATMtx(&qb, fb);
        C_QUATSlerp(&qa, &qb, &q, 0.5f);
        PSMTXQuat(o->mat, &q);
        Vec ea, eb, mid;
        PSMTXMultVec(pa, &w.ofs1, &ea);
        PSMTXMultVec(pb, &w.ofs2, &eb);
        PosToPos(&ea, &eb, &mid, chain_control ? 0.0f : 0.5f);
        TransMatrix(o->mat, &mid);
        chain_cnt.hung++;
    }
    if (o->pMotion) {
        o->motFlags2 |= 0x40000000;
        MotionMove(o);
    } else {
        o->partsMatCalc();
    }
    o->partsWorldCalc();
}
// the free pose: the motion, or the own matrix
void free_pose(cObj* o)
{
    if (o->pMotion) {
        MotionMove(o);
    } else {
        own_matrix(o);
        o->partsMatCalc();
    }
    o->partsWorldCalc();
}
// fading: 90 ticks, then 0.1 a tick to nothing (lost); off screen (behind the near plane) lost at once
void fade(cObj* o)
{
    ChainWork& w = o->chain;
    if (o->r_no_2 == 0) {
        w.timer = 90;
        o->r_no_2 = 1;
    }
    bool gone = false;
    if (w.timer != 0) {
        w.timer--;
    } else {
        o->invisible_factor -= 0.1f;
        if (o->invisible_factor <= 0.0f) {
            o->invisible_factor = 0.0f;
            to_state(o, CH_LOST);
            gone = true;
        }
    }
    if (!gone) {
        Vec p = o->pos, scr;
        GetScreenPos(&p, &scr);
        if (scr.z > 1.0f) to_state(o, CH_LOST);
    }
    own_matrix(o);
    o->partsMatCalc();
    o->partsWorldCalc();
}
void hang_on(cObj* o, cModel* parent, int p1, const Vec* ofs1, int p2, const Vec* ofs2, int flag)
{
    ChainWork& w = o->chain;
    w.parent = parent;
    w.parts1 = p1;
    w.parts2 = p2;
    w.ofs1 = *ofs1;
    w.ofs2 = *ofs2;
    if (flag) w.flags |= 2;
    else w.flags &= ~2u;
    to_state(o, CH_HUNG);
}
}   // namespace

// A chain object of models bin / tpl at pos, turned rot, free (no parent, no pendulum chain); 0 when the pool is full or
// the model cannot be set up. It passes through characters and has the object kind's light record.
cObjChain* SetChain(void* bin, void* tpl, Vec* pos, Vec* rot)
{
    chain_kind();
    cObj* o = ObjMgr.createBack(0x1D);
    if (!o) {
        chain_cnt.refused++;
        return 0;
    }
    if (o->modelInit(bin, tpl) == 0) {
        pLog->err(0, 0, "SetChain() modelInit() failed.");
        ObjMgr.destroy(o);
        chain_cnt.refused++;
        return 0;
    }
    static const Vec light_at = {0.0f, 0.0f, 0.0f};
    static const Vec light_size = {10000.0f, 10000.0f, 100000.0f};
    o->sub2B4.atari.throughOn();
    o->LightInfo.init2(0, 1, &light_at, &light_size, 2);
    o->pos = *pos;
    o->pos_old = *pos;
    o->ang = *rot;
    ChainWork& w = o->chain;
    w.parent = 0;
    w.parts1 = 0;
    w.parts2 = 0;
    w.cloth = 0;
    to_state(o, CH_FREE);
    free_pose(o);
    chain_cnt.made++;
    return (cObjChain*) o;
}

void cObjChain::move()
{
    ChainWork& w = chain;
    chain_cnt.moves++;
    if (w.parent && (w.parent->be_flag & 0x201) != 1) {
        chain_cnt.orphans++;
        ObjMgr.destroy(this);
        return;
    }
    if (pMotion) MotionMove(this);
    switch (r_no_1) {
    case CH_FREE: free_pose(this); break;
    case CH_FADE: fade(this); break;
    case CH_LOST:
        if (r_no_2 == 0) {
            r_no_2 = 1;
            be_flag &= ~0x22u;
            chain_cnt.lost++;
            ObjMgr.destroy(this);
        }
        break;
    case CH_HUNG: hang(this); break;
    default: break;
    }
    if ((be_flag & 0x201) == 1 && w.cloth) {
        PenClothMove(this, w.cloth);
        be_flag &= ~0x00E00000u;
        chain_cnt.steps++;
    }
}

void cObjChain::setParent(cModel* parent, int parts, Vec* ofs, int flag) { hang_on(this, parent, parts, ofs, parts, ofs, flag); }
void cObjChain::setParent2(cModel* parent, int parts1, Vec* ofs1, int parts2, Vec* ofs2, int flag)
{
    hang_on(this, parent, parts1, ofs1, parts2, ofs2, flag);
}
// The pendulum chain on the object's own bones, links 100 long (the cloth service resolves it once)
void cObjChain::setChain(PenCloth* cloth)
{
    chain.cloth = cloth;
    if (cloth) PenClothSet(this, cloth, 100.0f);
}
