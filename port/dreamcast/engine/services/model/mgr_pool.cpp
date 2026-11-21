// mgr_pool.cpp (lane eng-e1h, ruling H-014.4): the character table (cEm) and the light table (cLight) on the
// engine's record pool (pool.h; docs/engine/SERVICES.md section 41). Before this the default image took
// cManager<cEm>::createBack and cEmMgr::memClear from pl_sub's copy of the original manager template, and
// cManager<cLight>::destroy and ::log from pl_npc's.
//
// - cEm: create, createBack (the partners take the table's top slot: pl_sub SubCharCtrl), create at a slot, the count
//   and destroy are the pool's. The table's records are cleared by cEmMgr::memClear called directly, so its body is
//   emitted in this object, which links before the hosted units: the table's vtable (services/managers.cpp) reaches
//   this copy, not a hosted unit's.
// - cLight: the engine serves the lights (host/e1_stubs.cpp cLightMgr::createBack: the partner's light). LightMgr is
//   storage with no manager object (no vtable), so the pool's hooks for it are the engine's: log to the stub log,
//   clear with memset, no destructor (the records are engine storage). pl_npc's ~cSubChar destroys the partner's
//   light through this.
#include "pool.h"
#include "em.h"
#include "light.h"
#include "e1_engine.h"
#include <string.h>

namespace eng_pool {
template <> struct traits<cEm> {
    template <class... A> static void log(cManager<cEm>* m, const char* fmt, A... a) { m->log(fmt, a...); }
    static void clear(cManager<cEm>* m, cEm* p);
    static void dtor(cEm* p) { p->~cEm(); }
};
// A real call (this object is compiled with -fno-inline, game/Makefile), so the inline body is emitted in this object
// (see the head of the file).
void traits<cEm>::clear(cManager<cEm>* m, cEm* p)
{
    static_cast<cEmMgr*>(m)->cEmMgr::memClear(p, m->size);
}
template <> struct traits<cLight> {
    template <class... A> static void log(cManager<cLight>*, const char* fmt, A...) { e1_stub_hit(fmt, 0); }
    static void clear(cManager<cLight>* m, cLight* p) { memset((void*) p, 0, m->size); }
    static void dtor(cLight*) {}
};
}   // namespace eng_pool

ENG_POOL(cEm)
#ifndef E1_MGR_ORIG_CREATEBACK   // control build only (MGR_EXTRA=-DE1_MGR_ORIG_CREATEBACK=1): pl_sub's original back
ENG_POOL_BACK(cEm)
#endif
// The lights' creation is the engine's light service (cLightMgr::createBack, host/e1_stubs.cpp; light.h's inlines
// instantiate the template's create forms before this point, and nothing in an engine image reaches them); their
// release and the table's log are the pool's.
template <> void cManager<cLight>::destroy(cLight* p) { eng_pool::destroy(this, p); }
template <> void cManager<cLight>::log(const char* fmt, ...) { e1_stub_hit(fmt, 0); }
