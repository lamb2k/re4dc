// E2 fight slice (lane eng-e2): service accounting for the entry points the hosted Ganado code calls beyond the ones
// host/e1_wraps.cpp wraps for every image (lane eng-e1c: motion, cloth, parts, collision cores): the actor volume tests
// and the route checks (collision group) and the native effect service (effects group: its tick and the effect starts
// the behaviour makes). Link-time --wrap (game/fight.mk), so neither the behaviour nor the service code is edited; the
// accounting is E1's (nested calls counted once, one services number per tick, split by group in the ROW lines).
#include "global.h"
#include "model.h"
#include "em.h"
#include "atari.h"
#include "e1_engine.h"
#include "e1_core.h"
#include "fx.h"

extern "C" unsigned e1_svc_slot_named(const char* n, unsigned group);
extern "C" void e1_svc_enter(unsigned slot);
extern "C" void e1_svc_leave();
#define SLOT(n, g) static unsigned slot = e1_svc_slot_named(n, g)
struct SvcScope { SvcScope(unsigned s) { e1_svc_enter(s); } ~SvcScope() { e1_svc_leave(); } };
#define COL E1_SVC_COLLISION
#define FX E1_SVC_EFFECTS

extern "C" {
int __real_At_box_sphere_ck(Vec* b, Vec* p, f32 r);
int __wrap_At_box_sphere_ck(Vec* b, Vec* p, f32 r) { SLOT("At_box_sphere_ck", COL); SvcScope s(slot); return __real_At_box_sphere_ck(b, p, r); }
u32 __real_AtBoxCapsuleCk3(Vec* b, Vec* p0, f32 r, Vec* p1);
u32 __wrap_AtBoxCapsuleCk3(Vec* b, Vec* p0, f32 r, Vec* p1) { SLOT("AtBoxCapsuleCk3", COL); SvcScope s(slot); return __real_AtBoxCapsuleCk3(b, p0, r, p1); }
int __real_RouteCkToEm(cEm* e, cEm* t, Vec* o, int f);
int __wrap_RouteCkToEm(cEm* e, cEm* t, Vec* o, int f) { SLOT("RouteCkToEm", COL); SvcScope s(slot); return __real_RouteCkToEm(e, t, o, f); }
void __real_RouteCkEscEm(cEm* e, cEm* fr, Vec* o);
void __wrap_RouteCkEscEm(cEm* e, cEm* fr, Vec* o) { SLOT("RouteCkEscEm", COL); SvcScope s(slot); __real_RouteCkEscEm(e, fr, o); }
int __real_RouteCkToPos(cEm* e, Vec* t, Vec* o, int f, f32* d);
int __wrap_RouteCkToPos(cEm* e, Vec* t, Vec* o, int f, f32* d) { SLOT("RouteCkToPos", COL); SvcScope s(slot); return __real_RouteCkToPos(e, t, o, f, d); }
int __real_RouteCkConnectPosCk(Vec* a, Vec* b);
int __wrap_RouteCkConnectPosCk(Vec* a, Vec* b) { SLOT("RouteCkConnectPosCk", COL); SvcScope s(slot); return __real_RouteCkConnectPosCk(a, b); }
f32 __real_RouteCkPosToPosDis(Vec* a, Vec* b);
f32 __wrap_RouteCkPosToPosDis(Vec* a, Vec* b) { SLOT("RouteCkPosToPosDis", COL); SvcScope s(slot); return __real_RouteCkPosToPosDis(a, b); }
int __real_RouteCkGetNearPoint(Vec* p);
int __wrap_RouteCkGetNearPoint(Vec* p) { SLOT("RouteCkGetNearPoint", COL); SvcScope s(slot); return __real_RouteCkGetNearPoint(p); }
// the native effect service: the behaviour's effect starts
void __real_EstSet(int a, int b, Vec* p, Vec* r, int c, int d, int e, int f, u32 g, void* h);
void __wrap_EstSet(int a, int b, Vec* p, Vec* r, int c, int d, int e, int f, u32 g, void* h) { SLOT("fx EstSet", FX); SvcScope s(slot); __real_EstSet(a, b, p, r, c, d, e, f, g, h); }
// em10.cpp also names EstSet and MotionMove by their raw link names (asm labels, no C underscore; link.sh's aliases
// bind them): the wraps rename those references to the raw __wrap_ names, given here as the same entries
void e2_wrap_est_raw(int a, int b, Vec* p, Vec* r, int c, int d, int e, int f, u32 g, void* h) asm("__wrap_EstSet");
void e2_wrap_est_raw(int a, int b, Vec* p, Vec* r, int c, int d, int e, int f, u32 g, void* h) { __wrap_EstSet(a, b, p, r, c, d, e, f, g, h); }
}   // (MotionMove: host/e1_wraps.cpp gives both names since lane eng-e1c)
// the native effect service's tick (core main.cpp calls e2_fx_move inside the tick's service accounting)
void e2_fx_move()
{
    SLOT("fx_move", FX);
    SvcScope s(slot);
    fx_move();
}
