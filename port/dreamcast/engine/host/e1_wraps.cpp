// Service-boundary accounting (lane eng-e1): the random-number generator's draw count and the time spent inside the
// skeleton and collision services, measured at the entry points the hosted behaviour calls (link-time --wrap, so
// neither the behaviour nor the service code is edited). Nested service calls are counted once (depth counter).
// Lane eng-e1c: each entry point has a group (motion, cloth, parts and palette, collision: the services row split),
// timed per tick, with a MODELLED stamp at each group boundary.
#include "e1_kos.h"
#include "e1_engine.h"
#include "e1_core.h"

extern "C" {
unsigned e1_rnd_draws;
unsigned short re4dc_rnd_state(void);   // src/game/rnd.cpp, compiled with its read-only trace accessor
unsigned short e1_rnd_state(void) { return re4dc_rnd_state(); }

static int depth;
static uint64_t svc_t0, svc_acc, svc_grp[E1_SVC_GROUPS];
// per outermost entry point: total time over the run (the services row split by entry and group)
struct SvcRow { const char* name; uint64_t us; uint32_t calls; unsigned group; };
static SvcRow svc_rows[48];
static unsigned nsvc, svc_cur;
static unsigned svc_slot(const char* n, unsigned g) { for (unsigned i = 0; i < nsvc; i++) if (svc_rows[i].name == n) return i; svc_rows[nsvc].name = n; svc_rows[nsvc].group = g; return nsvc++; }
// MODELLED service stamps (lane eng-e1c): a store to word k of e1_svc_stamp when the tick enters a service group k
// (1 motion, 2 cloth, 3 parts and palette, 4 collision) and to word 0 when it returns to the behaviour. The hardware
// model's observer (s/model_profile_svc.py) prints each store with its cycle time. A plain store; no other effect.
volatile uint32_t e1_svc_stamp[8] __attribute__((aligned(32)));
static inline void enter(unsigned slot) { if (depth++ == 0) { svc_cur = slot; e1_svc_stamp[svc_rows[slot].group] = 1; svc_t0 = timer_us_gettime64(); } }
static inline void leave() { if (--depth == 0) { uint64_t d = timer_us_gettime64() - svc_t0; svc_acc += d; svc_rows[svc_cur].us += d; svc_rows[svc_cur].calls++; svc_grp[svc_rows[svc_cur].group] += d; e1_svc_stamp[0] = 1; } }
}
void e1_svc_begin() { svc_acc = 0; depth = 0; for (unsigned g = 0; g < E1_SVC_GROUPS; g++) svc_grp[g] = 0; }
uint32_t e1_svc_end() { return (uint32_t) svc_acc; }
uint32_t e1_svc_group(unsigned g) { return g < E1_SVC_GROUPS ? (uint32_t) svc_grp[g] : 0; }

#define WRAP(ret, mangled, group, params, args)                   \
    extern "C" ret __real_##mangled params;                       \
    extern "C" ret __wrap_##mangled params                        \
    {                                                             \
        static unsigned slot = svc_slot(#mangled, group);         \
        enter(slot);                                              \
        ret res_ = __real_##mangled args;                         \
        leave();                                                  \
        return res_;                                              \
    }
#define WRAPV(mangled, group, params, args)                       \
    extern "C" void __real_##mangled params;                      \
    extern "C" void __wrap_##mangled params                       \
    {                                                             \
        static unsigned slot = svc_slot(#mangled, group);         \
        enter(slot);                                              \
        __real_##mangled args;                                    \
        leave();                                                  \
    }
enum { MOT = E1_SVC_MOTION, CLOTH = E1_SVC_CLOTH, PARTS = E1_SVC_PARTS, COL = E1_SVC_COLLISION };

extern "C" unsigned char __real__Z3Rndv();
extern "C" unsigned char __wrap__Z3Rndv() { e1_rnd_draws++; return __real__Z3Rndv(); }

// Groups (lane eng-e1c): every entry point of the skeleton and collision services the behaviour can call, the same
// list for the original units (first form) and the native services.
// motion: sampling, blends, hokan, IK, shape keys, the model's motion step
WRAPV(_Z13MotionSetCoreP6cModelPvS1_iiii, MOT, (void* m, void* w, void* d, int a, int b, int c, int e), (m, w, d, a, b, c, e))
WRAP(int, _ZN6cModel10motionMoveEv, MOT, (void* m), (m))
WRAP(unsigned short, MotionMove, MOT, (void* m), (m))
WRAPV(MotionClear, MOT, (void* m, int f), (m, f))
WRAPV(MotionHokan, MOT, (void* m, void* w), (m, w))
WRAPV(_ZN8cMotBase4moveEv, MOT, (void* m), (m))
WRAPV(_ZN8cMotBase6adjustEv, MOT, (void* m), (m))
WRAPV(InverseKinematics, MOT, (void* m, int f), (m, f))
WRAPV(ShapeMove, MOT, (void* i), (i))
// the sources call MotionMove under its PowerPC link name too (no symbol prefix): the linker sends those references
// to this unprefixed name
extern "C" unsigned short e1_wrap_mm_ppc(void* m) asm("__wrap_MotionMove");
extern "C" unsigned short e1_wrap_mm_ppc(void* m) { return __wrap_MotionMove(m); }
// cloth: Leon's and Ashley's cloth and the pendulum cloth they hang
WRAPV(_Z15PlClothMoveLeonP6cModelP7PlClothS2_S2_, CLOTH, (void* m, void* a, void* b, void* c), (m, a, b, c))
WRAPV(_Z15PlClothMoveGirlP6cModelP7PlClothS2_S2_, CLOTH, (void* m, void* a, void* b, void* c), (m, a, b, c))
WRAPV(PenClothMove, CLOTH, (void* m, void* c), (m, c))
WRAPV(PenClothMove3, CLOTH, (void* m, void* c), (m, c))
// parts: the world pass, history, fixes, the record hand-out (the mailbox in the native service); the palette
WRAPV(PartsWorldPosCalc, PARTS, (void* m), (m))
WRAPV(_ZN6cModel14partsWorldCalcEv, PARTS, (void* m), (m))
WRAPV(_ZN6cModel12partsMatCalcEv, PARTS, (void* m), (m))
WRAPV(_ZN6cModel8matBlendEf, PARTS, (void* m, float r), (m, r))
WRAPV(_ZN6cModel14partsFixAdjustEv, PARTS, (void* m), (m))
WRAPV(_ZN6cModel12updateOldPosEv, PARTS, (void* m), (m))
WRAPV(_ZN6cModel9matUpdateEv, PARTS, (void* m), (m))
WRAP(void*, _ZN6cModel11getPartsPtrEi, PARTS, (void* m, int no), (m, no))
WRAP(void*, GetPartsAddr, PARTS, (void* m, int no), (m, no))
WRAPV(_ZN6cModel9setParentEPS_P3VecS2_, PARTS, (void* m, void* p, void* a, void* b), (m, p, a, b))
WRAPV(_ZN6cModel9setParentEPS_iP3VecS2_, PARTS, (void* m, void* p, int n, void* a, void* b), (m, p, n, a, b))
// collision: scenery queries, the actor volumes
WRAP(int, _ZN7cSatMgr5checkEP6cModeli, COL, (void* s, void* m, int k), (s, m, k))
WRAP(int, _ZN7cSatMgr8checkAirEP6cModeli, COL, (void* s, void* m, int k), (s, m, k))
WRAP(float, _ZN7cSatMgr8getFloorEP3VecffPmi, COL, (void* s, void* p, float u, float d, void* a, int f), (s, p, u, d, a, f))
WRAP(int, _ZN7cSatMgr8hitCheckEP3VecS1_S1_S1_ii, COL, (void* s, void* a, void* b, void* c, void* d, int f, int m), (s, a, b, c, d, f, m))
WRAP(int, _ZN7cSatMgr9hitCheck2EP3VecS1_S1_Pmii, COL, (void* s, void* a, void* b, void* c, void* d, int f, int m), (s, a, b, c, d, f, m))
WRAP(int, _ZN7cSatMgr12polySphereCkEP3VecS1_fiS1_i, COL, (void* s, void* a, void* b, float r, int f, void* n, int m), (s, a, b, r, f, n, m))
WRAPV(EmAtCheck, COL, (void* m), (m))
WRAPV(_ZN10cAtariInfo4moveEv, COL, (void* a), (a))

// The palette (world x bind) once a tick after the behaviour: native skeleton only (the first form has none; its
// drawing multiplied world x bind itself). Called by the main loop inside the tick's service accounting.
extern "C" void skel_publish_all(void) __attribute__((weak));
void e1_svc_publish()
{
    static unsigned slot = svc_slot("skel_publish_all", PARTS);
    if (!skel_publish_all) return;
    enter(slot);
    skel_publish_all();
    leave();
}

// ---- behaviour profile (diagnostic): time inside the player's per-tick sub-steps, totals over the run ----
struct ProfRow { const char* name; uint64_t us; uint32_t calls; };
static ProfRow prof[16];
static unsigned nprof;
static unsigned prof_slot(const char* n) { for (unsigned i = 0; i < nprof; i++) if (prof[i].name == n) return i; prof[nprof].name = n; return nprof++; }
#define PROF(mangled)                                                         \
    extern "C" void __real_##mangled(void* t);                                \
    extern "C" void __wrap_##mangled(void* t)                                 \
    {                                                                         \
        static unsigned slot = prof_slot(#mangled);                           \
        uint64_t a = timer_us_gettime64();                                    \
        __real_##mangled(t);                                                  \
        prof[slot].us += timer_us_gettime64() - a; prof[slot].calls++;        \
    }
PROF(_ZN7cPlNeck4moveEv)
PROF(_ZN7cPlBody4moveEv)
PROF(_ZN7cPlayer7moveEyeEv)
PROF(_ZN7cPlayer10shadowCtrlEv)
PROF(_ZN7cPlayer9seqSeCtrlEv)
PROF(_ZN7cPlayer11visibleCtrlEv)
PROF(_ZN6cPlWep4moveEv)
PROF(_ZN7cPlayer8dmgCheckEv)
PROF(_ZN7cPlayer9keyConfigEv)
PROF(_ZN7cPlayer13moveBinocularEv)
PROF(_ZN7cPlayer16subCharLiveCheckEv)
PROF(_ZN7cPlayer9debugMoveEv)
PROF(pl_R0_Move)
void e1_prof_report()
{
    for (unsigned i = 0; i < nsvc; i++)
        printf("E1 SVC %s us %lu calls %lu group %u\n", svc_rows[i].name, (unsigned long) svc_rows[i].us, (unsigned long) svc_rows[i].calls, svc_rows[i].group);
    for (unsigned i = 0; i < nprof; i++)
        printf("E1 PROF %s us %lu calls %lu\n", prof[i].name, (unsigned long) prof[i].us, (unsigned long) prof[i].calls);
}
