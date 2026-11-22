// oba_obj.cpp (lane eng-e2c): the giant's collision bodies, native. An oba object (object kind 0x20, the original
// game/obj20.cpp) is an invisible model carrying one collision cylinder that follows a part of its parent (El Gigante
// puts six on his legs at set-up and three more when an event kills him), so the player and the enemies collide with a
// moving body; game/obj20 is not hosted. The push-apart keeps two giants in battle 3000 apart (em2bObaHitCk).
//
// Engine form: the object is a record of the engine's object pool, its model the core archive's empty model (the
// model service), its cylinder an actor volume (services/volumes: init, priority, the tick's move), its light record
// the engine's; its follow is the parent part's frame applied to the offset (cam_math.h, SH4ZAM types) with the ground
// clamp, its matrix built by the math service. The push walks the character pool's slots in order and moves this giant
// to 3000 from each other giant in battle on the ground plane; the skeleton re-places its parts (PartsWorldPosCalc).
// No random number is drawn.
#define fabsf e2c_game_fabsf
#include "types.h"
#include "global.h"
#include "model.h"
#include "em.h"
#include "obj.h"
#include "atari.h"
#include "light.h"
#include "math_sub.h"
#include "motion.h"
#include "db_log.h"
#include "em2b.h"
#undef fabsf
#include "cam_math.h"
#include "boss_svc.h"

extern "C" void EmAtCheck(cModel* m);   // the actor-volume service's character check (at_mod.h names it for cEm)

class cObjObaModel : public cObj {
public:
    virtual void move();
};

namespace {
using namespace camsvc;

// The oba body on a new object record: the core archive's empty model, a light record of the object kind, a cylinder of
// radius r and height h (collision kind 0x2000, the first priority, the 0x100 flag down), hidden from drawing.
bool oba_body(cObj* o, f32 r, f32 h, u8 type)
{
    void* bin = (void*) (pG->pArc->ofs_20 + (u32) pG->pArc);
    void* tpl = (void*) (pG->pArc->ofs_24 + (u32) pG->pArc);
    if (o->modelInit(bin, tpl) == 0) return false;
    static const Vec light_at = {0.0f, 0.0f, 0.0f};
    static const Vec light_size = {1000.0f, 1000.0f, 0.0f};
    o->type = type;
    o->LightInfo.init2(0, 1, &light_at, &light_size, 0x10);
    cAtariInfo& v = o->sub2B4.atari;
    v.init(0, 0x2000, 10, 0.0f, 0.0f, 0.0f, r, r, r, h);
    v.clrFlag100();
    v.setPriority(PRI_LV1);
    o->be_flag &= ~2;
    return true;
}

// Where the object stands for its parent: kind 0 on the parent's part, set down to the parent's own height when less than
// 2000 above it; kind 1 at the parent's origin; other kinds keep their place.
void follow(cObj* o, cObj* parent, const ObaModelWork& w)
{
    switch (o->type) {
    case 0: {
        put(&o->pos, frame_point(frame_of(parent->getPartsPtr(w.partsNo)->mat), V(w.ofs)));
        const f32 clamp = boss_control == 6 ? 1500.0f : 2000.0f;   // control bossoba
        if (o->pos.y < parent->pos.y + clamp) o->pos.y = parent->pos.y;
        break;
    }
    case 1:
        put(&o->pos, frame_point(frame_of(parent->mat), V(w.ofs)));
        break;
    default:
        break;
    }
}

bool other_giant_in_battle(cEm* e, cEm2b* em)
{
    return e && (e->be_flag & 0x201) == 1 && e->id == 0x2B && e->hp > 0 && e != em && e->checkStatus(EM_STATUS_ACTIVE);
}
}   // namespace

// An oba object on `parent` (part partsNo + ofs for kind 0, the origin + ofs for kind 1), cylinder radius rad and
// height h; 0 when the object pool is full or the model cannot be set up.
extern "C" cObj* SetObaModel(cObj* parent, int partsNo, Vec* ofs, f32 rad, u8 type, f32 h)
{
    cObj* o = ObjMgr.create(0x20);
    if (!o) {
        boss_cnt.oba_refused++;
        return 0;
    }
    if (!oba_body(o, rad, h, type)) {
        pLog->err(0, 0, "SetObaModel() failed.");
        ObjMgr.destroy(o);
        boss_cnt.oba_refused++;
        return 0;
    }
    ObaModelWork& w = o->obaModel;
    w.parent = parent;
    w.ofs = *ofs;
    w.partsNo = partsNo;
    boss_cnt.oba_made++;
    o->move();
    return o;
}

// Each tick: released with a parent that is no longer alive; placed for the parent and taking its pass-through flag
// (0x200); the matrix from the angles, position and scale; the character check and the cylinder's move.
void cObjObaModel::move()
{
    ObaModelWork& w = obaModel;
    boss_cnt.oba_moves++;
    if (cObj* parent = w.parent) {
        if ((parent->be_flag & 0x201) != 1) {
            boss_cnt.oba_orphans++;
            ObjMgr.destroy(this);
            return;
        }
        follow(this, parent, w);
        if (parent->sub2B4.atari.m_flag & 0x200) {
            sub2B4.atari.m_flag |= 0x200;
        } else {
            sub2B4.atari.m_flag &= ~0x200;
        }
    }
    RotMatrix(mat, &ang);
    TransMatrix(mat, &pos);
    ScaleMatrix(mat, &scale);
    matUpdate();
    EmAtCheck(this);
    sub2B4.atari.move();
}

// This giant kept 3000 from every other giant in battle (slot order), on the ground plane: it takes that giant's height
// and stands 3000 away along the line between them (on top of it when they coincide).
void em2bObaHitCk(cEm2b* em)
{
    const f32 apart = boss_control == 7 ? 2900.0f : 3000.0f;   // control bosspush
    boss_cnt.push_tests++;
    for (u32 i = 0; i < EmMgr.nArray; i++) {
        cEm* e = (cEm*) EmMgr.workAt(i);
        if (!other_giant_in_battle(e, em)) continue;
        v3 d = vsub(V(em->pos), V(e->pos));
        d.y = 0.0f;
        if (d.x * d.x + d.z * d.z > 9000000.0f) continue;
        put(&em->pos, vadd(V(e->pos), vscale(vunit(d), apart)));
        PartsWorldPosCalc(em);
        boss_cnt.pushes++;
    }
}
