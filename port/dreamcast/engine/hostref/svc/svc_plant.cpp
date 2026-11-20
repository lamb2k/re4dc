// svc_plant.cpp (game side; lane eng-svc): the census's control. With RE4_SVC_CONTROL=plant the census builds call
// svc_plant_read once a tick: a read of Leon's bone 3 world position straight from its cParts record (no
// getPartsPtr), from a unit the census classifies as behaviour. The fields table must show it (1 access a tick,
// one bone); a census that missed it would be reading wrong.
#include "model.h"
#include "em.h"

extern "C" volatile float svc_plant_sink;
volatile float svc_plant_sink;

extern "C" void svc_plant_read()
{
    cModel* m = EmMgr.pAlive;
    if (!m || !m->pParts) return;
    cModel* p = m->pParts;
    for (int i = 0; i < 3 && p->pParts; i++) p = p->pParts;
    svc_plant_sink = p->world.y;
}
