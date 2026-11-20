// E2 fight slice (lane eng-e2): service accounting for the entry points the hosted Ganado code calls beyond E1's
// (host/e1_wraps.cpp keeps the player's): the skeleton's MotionMove, the scenery and volume checks, the route checks,
// and the native effect service (its tick and the effect starts the behaviour makes). Link-time --wrap (game/fight.mk),
// so neither the behaviour nor the service code is edited; the accounting is E1's (nested calls counted once).
#include "global.h"
#include "model.h"
#include "em.h"
#include "atari.h"
#include "e1_engine.h"
#include "fx.h"

extern "C" unsigned e1_svc_slot_named(const char* n);
extern "C" void e1_svc_enter(unsigned slot);
extern "C" void e1_svc_leave();
#define SLOT(n) static unsigned slot = e1_svc_slot_named(n)
struct SvcScope { SvcScope(unsigned s) { e1_svc_enter(s); } ~SvcScope() { e1_svc_leave(); } };

extern "C" {
u16 __real_MotionMove(cModel* m);
u16 __wrap_MotionMove(cModel* m) { SLOT("MotionMove"); SvcScope s(slot); return __real_MotionMove(m); }
// em10.cpp names MotionMove by its PowerPC link name (asm label, no C underscore; link.sh's aliases bind it): the wrap
// renames those references to the raw __wrap_MotionMove, given here as the same entry
u16 e2_wrap_mm_raw(cModel* m) asm("__wrap_MotionMove");
u16 e2_wrap_mm_raw(cModel* m) { return __wrap_MotionMove(m); }
int __real__ZN7cSatMgr8checkAirEP6cModeli(cSatMgr* t, cModel* m, int f);
int __wrap__ZN7cSatMgr8checkAirEP6cModeli(cSatMgr* t, cModel* m, int f) { SLOT("cSatMgr::checkAir"); SvcScope s(slot); return __real__ZN7cSatMgr8checkAirEP6cModeli(t, m, f); }
int __real_At_box_sphere_ck(Vec* b, Vec* p, f32 r);
int __wrap_At_box_sphere_ck(Vec* b, Vec* p, f32 r) { SLOT("At_box_sphere_ck"); SvcScope s(slot); return __real_At_box_sphere_ck(b, p, r); }
u32 __real_AtBoxCapsuleCk3(Vec* b, Vec* p0, f32 r, Vec* p1);
u32 __wrap_AtBoxCapsuleCk3(Vec* b, Vec* p0, f32 r, Vec* p1) { SLOT("AtBoxCapsuleCk3"); SvcScope s(slot); return __real_AtBoxCapsuleCk3(b, p0, r, p1); }
int __real_RouteCkToEm(cEm* e, cEm* t, Vec* o, int f);
int __wrap_RouteCkToEm(cEm* e, cEm* t, Vec* o, int f) { SLOT("RouteCkToEm"); SvcScope s(slot); return __real_RouteCkToEm(e, t, o, f); }
void __real_RouteCkEscEm(cEm* e, cEm* fr, Vec* o);
void __wrap_RouteCkEscEm(cEm* e, cEm* fr, Vec* o) { SLOT("RouteCkEscEm"); SvcScope s(slot); __real_RouteCkEscEm(e, fr, o); }
int __real_RouteCkToPos(cEm* e, Vec* t, Vec* o, int f, f32* d);
int __wrap_RouteCkToPos(cEm* e, Vec* t, Vec* o, int f, f32* d) { SLOT("RouteCkToPos"); SvcScope s(slot); return __real_RouteCkToPos(e, t, o, f, d); }
int __real_RouteCkConnectPosCk(Vec* a, Vec* b);
int __wrap_RouteCkConnectPosCk(Vec* a, Vec* b) { SLOT("RouteCkConnectPosCk"); SvcScope s(slot); return __real_RouteCkConnectPosCk(a, b); }
f32 __real_RouteCkPosToPosDis(Vec* a, Vec* b);
f32 __wrap_RouteCkPosToPosDis(Vec* a, Vec* b) { SLOT("RouteCkPosToPosDis"); SvcScope s(slot); return __real_RouteCkPosToPosDis(a, b); }
int __real_RouteCkGetNearPoint(Vec* p);
int __wrap_RouteCkGetNearPoint(Vec* p) { SLOT("RouteCkGetNearPoint"); SvcScope s(slot); return __real_RouteCkGetNearPoint(p); }
// the native effect service: the behaviour's effect starts
void __real_EstSet(int a, int b, Vec* p, Vec* r, int c, int d, int e, int f, u32 g, void* h);
void __wrap_EstSet(int a, int b, Vec* p, Vec* r, int c, int d, int e, int f, u32 g, void* h) { SLOT("fx EstSet"); SvcScope s(slot); __real_EstSet(a, b, p, r, c, d, e, f, g, h); }
// em10.cpp also names EstSet by its raw link name (asm label): the same entry under the raw wrap name
void e2_wrap_est_raw(int a, int b, Vec* p, Vec* r, int c, int d, int e, int f, u32 g, void* h) asm("__wrap_EstSet");
void e2_wrap_est_raw(int a, int b, Vec* p, Vec* r, int c, int d, int e, int f, u32 g, void* h) { __wrap_EstSet(a, b, p, r, c, d, e, f, g, h); }
}
// the native effect service's tick (core main.cpp calls e2_fx_move inside the tick's service accounting)
void e2_fx_move()
{
    SLOT("fx_move");
    SvcScope s(slot);
    fx_move();
}
