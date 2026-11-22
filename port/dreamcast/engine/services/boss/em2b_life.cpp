// em2b_life.cpp (lane eng-e2c): the lifetime of the boss arena's characters on the engine's pools. The character pool
// (services/model/pool.h) calls a record's destructor when it releases the record; these are the bodies it reaches for
// El Gigante and the thrown tree and torch.
//
// Engine form: a giant releases what it holds (the parasite's head, its ten face tentacles, the three chain objects of
// the chained form) as one table of the work's object slots, each through the object pool when it is still alive. The
// original destroyed a tentacle without the alive test; the engine's pool refuses a dead record and counts it as a bad
// free (a scene with one fails), so the engine releases only live ones (the same objects end released). The tree's and
// the torch's destructors release nothing: their originals are one return (4 bytes, `rts`), and the records are the
// pool's.
#define fabsf e2c_game_fabsf
#include "types.h"
#include "global.h"
#include "model.h"
#include "em.h"
#include "obj.h"
#include "em2b.h"
#undef fabsf
#include "boss_svc.h"

// The giant's held objects, released with it.
cEm2b::~cEm2b()
{
    Em2bWork* w = EM2B_WK(this);
    // the parasite and its tentacles are cObj16 records (an object kind derived from cObj alone, declared in em10.h,
    // which this file does not include): the same address as their object record
#define AS_OBJ(p) ((cObj*) (void*) (p))
    cObj* const held[] = {AS_OBJ(w->pParasite), AS_OBJ(w->pTen[0]), AS_OBJ(w->pTen[1]), AS_OBJ(w->pTen[2]),
                          AS_OBJ(w->pTen[3]), AS_OBJ(w->pTen[4]), AS_OBJ(w->pTen[5]), AS_OBJ(w->pTen[6]), AS_OBJ(w->pTen[7]),
                          AS_OBJ(w->pTen[8]), AS_OBJ(w->pTen[9]), w->pChain, w->pChain2, w->pChain3};
#undef AS_OBJ
    boss_cnt.giant_releases++;
    for (cObj* o : held) {
        if (!o || !o->isAlive() || (boss_control == 5 && o == w->pChain3)) continue;   // control bossheld
        ObjMgr.destroy(o);
        boss_cnt.held_released++;
    }
}

// The thrown tree's and the torch's destructors (the compiler's inline copies in the hosted units are weak: these strong
// bodies take their place). Nothing to release.
#define E2C_STR2(x) #x
#define E2C_STR(x) E2C_STR2(x)
#define E2C_SYM(name) asm(E2C_STR(__USER_LABEL_PREFIX__) #name)
extern "C" {
void eng_tree_release0(void*) E2C_SYM(_ZN7cEmTreeD0Ev);
void eng_tree_release1(void*) E2C_SYM(_ZN7cEmTreeD1Ev);
void eng_tree_release2(void*) E2C_SYM(_ZN7cEmTreeD2Ev);
void eng_torch_release0(void*) E2C_SYM(_ZN8cEmTorchD0Ev);
void eng_torch_release1(void*) E2C_SYM(_ZN8cEmTorchD1Ev);
void eng_torch_release2(void*) E2C_SYM(_ZN8cEmTorchD2Ev);
void eng_tree_release0(void*) { boss_cnt.empty_releases++; }
void eng_tree_release1(void*) { boss_cnt.empty_releases++; }
void eng_tree_release2(void*) { boss_cnt.empty_releases++; }
void eng_torch_release0(void*) { boss_cnt.empty_releases++; }
void eng_torch_release1(void*) { boss_cnt.empty_releases++; }
void eng_torch_release2(void*) { boss_cnt.empty_releases++; }
}
