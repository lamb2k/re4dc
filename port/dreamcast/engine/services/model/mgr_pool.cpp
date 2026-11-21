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

// Lane eng-e1i (ruling H-015.1): the object table (cObj: the handgun object wep02's Wep02_init makes with
// ObjMgr.createBack, objects the scripts make) on the same pool. Before, the default image took cManager<cObj>::
// createBack and ::destroy and cObjMgr::memClear from wep02's copy of the template. The table's manager is the engine's
// (services/managers.cpp cObjMgr: construct by ObjInitFunc, move, destroy with the object's push); its records are
// cleared by cObjMgr::memClear called directly, so the inline body is emitted here, as cEmMgr's above.
#ifndef E1_MGR_ORIG_COBJ   // control build only (MGR_EXTRA=-DE1_MGR_ORIG_COBJ=1): wep02's original template instances
#include "obj.h"
namespace eng_pool {
template <> struct traits<cObj> {
    template <class... A> static void log(cManager<cObj>* m, const char* fmt, A... a) { m->log(fmt, a...); }
    static void clear(cManager<cObj>* m, cObj* p);
    static void dtor(cObj* p) { p->~cObj(); }
};
void traits<cObj>::clear(cManager<cObj>* m, cObj* p)
{
    static_cast<cObjMgr*>(m)->cObjMgr::memClear(p, m->size);
}
}   // namespace eng_pool
ENG_POOL(cObj)
ENG_POOL_BACK(cObj)
#endif

// Lane eng-e1i (ruling H-015.3): a refused double free or a full table fails the scene (engine/loader/selector.c reads
// the report's "E1 POOL" line). The control: with the boot file POOLCTL the image destroys a character record that is
// not alive (the first free slot of the character table, after the room's set-up), which the pool refuses and counts
// as a bad free; the selector must then mark the scene FAILED.
#include <kos/fs.h>
extern cEmMgr EmMgr;
extern "C" void e1_pool_control(void)
{
    file_t f = fs_open("/cd/POOLCTL", O_RDONLY);
    if (f < 0) return;
    fs_close(f);
    for (u32 i = 0; i < EmMgr.nArray; i++) {
        cEm* p = (cEm*) ((u8*) EmMgr.pArray + i * EmMgr.size);
        if ((p->be_flag & 0x201) != 1) {
            e1_log("E1 POOLCTL: destroying the free character record %lu (control)\n", (unsigned long) i);
            EmMgr.destroy(p);
            return;
        }
    }
    e1_log("E1 POOLCTL: no free character record\n");
}
