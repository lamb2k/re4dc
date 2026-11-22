// scene_event.cpp (lane eng-e2d): the scenario layer's "event starts / ends" on the engine's record tables.
//
// SceEventStart and SceEventEnd (hosted sce_com: whether an event starts, its mode, which tables hear it, the camera's
// return) tell every live record of the character, object and damage tables that an event begins or ends. The
// original walks the table itself (sce_com.cpp's cManager<T>::beginEvent / endEvent template, which GCC had inlined
// into SceEventStart and SceEventEnd, out of the link check's sight: tools/engine/split_check.py). Those walks are the
// engine's record tables' (ruling H-014.4: actor and object tables are the engine's), so the image takes these
// explicit specializations; sce_com is built without the interprocedural optimisations (game/Makefile
// SPLIT_NOIPA_UNITS), so its calls reach them, and --gc-sections drops its own copies.
//
// The engine walk: the records of the table in slot order, each alive by its own test, told through its own virtual
// entry (the record decides what an event does to it: an enemy stops, a damage volume removes itself). Slot order, not
// the alive list's, because a record's handler may take itself off the list (cDmg::beginEvent destroys its volume).
#include "cManager.h"
#include "em.h"
#include "obj.h"
#include "dmg.h"

namespace {
// A record's event entries take the event mode (the shared header declares them without it): the vtable slots after
// the virtual destructor's two.
struct EventView {
    u32 be_flag;
    cUnit* next;
    virtual ~EventView();
    virtual void beginEvent(int mode);
    virtual void endEvent(int mode);
};

template <class T, bool Begin> void tell(cManager<T>* m, int mode)
{
    const u32 n = m->nArray;
    for (u32 i = 0; i < n; i++) {
        T* p = m->workAt(i);
        if (p == 0 || !p->isAlive()) continue;
        EventView* v = reinterpret_cast<EventView*>(p);
        if (Begin) v->beginEvent(mode);
        else v->endEvent(mode);
    }
}
}   // namespace

template <> void cManager<cEm>::beginEvent(int mode) { tell<cEm, true>(this, mode); }
template <> void cManager<cEm>::endEvent(int mode) { tell<cEm, false>(this, mode); }
template <> void cManager<cObj>::beginEvent(int mode) { tell<cObj, true>(this, mode); }
template <> void cManager<cObj>::endEvent(int mode) { tell<cObj, false>(this, mode); }
template <> void cManager<cDmg>::beginEvent(int mode) { tell<cDmg, true>(this, mode); }
template <> void cManager<cDmg>::endEvent(int mode) { tell<cDmg, false>(this, mode); }
