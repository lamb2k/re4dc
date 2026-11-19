// Service-boundary accounting (lane eng-e1): the random-number generator's draw count and the time spent inside the
// skeleton and collision services, measured at the entry points the hosted behaviour calls (link-time --wrap, so
// neither the behaviour nor the service code is edited). Nested service calls are counted once (depth counter).
#include "e1_kos.h"
#include "e1_engine.h"
#include "e1_core.h"

extern "C" {
unsigned e1_rnd_draws;
unsigned short re4dc_rnd_state(void);   // src/game/rnd.cpp, compiled with its read-only trace accessor
unsigned short e1_rnd_state(void) { return re4dc_rnd_state(); }

static int depth;
static uint64_t svc_t0, svc_acc;
// per outermost entry point: total time over the run (the services row split by entry)
struct SvcRow { const char* name; uint64_t us; uint32_t calls; };
static SvcRow svc_rows[24];
static unsigned nsvc, svc_cur;
static unsigned svc_slot(const char* n) { for (unsigned i = 0; i < nsvc; i++) if (svc_rows[i].name == n) return i; svc_rows[nsvc].name = n; return nsvc++; }
static inline void enter(unsigned slot) { if (depth++ == 0) { svc_t0 = timer_us_gettime64(); svc_cur = slot; } }
static inline void leave() { if (--depth == 0) { uint64_t d = timer_us_gettime64() - svc_t0; svc_acc += d; svc_rows[svc_cur].us += d; svc_rows[svc_cur].calls++; } }
}
void e1_svc_begin() { svc_acc = 0; depth = 0; }
uint32_t e1_svc_end() { return (uint32_t) svc_acc; }

#define WRAP(ret, mangled, params, args)                          \
    extern "C" ret __real_##mangled params;                       \
    extern "C" ret __wrap_##mangled params                        \
    {                                                             \
        static unsigned slot = svc_slot(#mangled);                \
        enter(slot);                                              \
        ret r = __real_##mangled args;                            \
        leave();                                                  \
        return r;                                                 \
    }
#define WRAPV(mangled, params, args)                              \
    extern "C" void __real_##mangled params;                      \
    extern "C" void __wrap_##mangled params                       \
    {                                                             \
        static unsigned slot = svc_slot(#mangled);                \
        enter(slot);                                              \
        __real_##mangled args;                                    \
        leave();                                                  \
    }

extern "C" unsigned char __real__Z3Rndv();
extern "C" unsigned char __wrap__Z3Rndv() { e1_rnd_draws++; return __real__Z3Rndv(); }

// skeleton and pose

WRAPV(_Z13MotionSetCoreP6cModelPvS1_iiii, (void* m, void* w, void* d, int a, int b, int c, int e), (m, w, d, a, b, c, e))
WRAPV(PartsWorldPosCalc, (void* m), (m))
WRAPV(_ZN6cModel14partsWorldCalcEv, (void* m), (m))
WRAPV(_ZN6cModel14partsFixAdjustEv, (void* m), (m))
WRAPV(_ZN6cModel12updateOldPosEv, (void* m), (m))
WRAPV(_ZN6cModel9matUpdateEv, (void* m), (m))
WRAPV(_ZN8cMotBase4moveEv, (void* m), (m))
WRAPV(_ZN8cMotBase6adjustEv, (void* m), (m))
// collision
WRAPV(_ZN7cSatMgr5checkEP6cModeli, (void* s, void* m, int k), (s, m, k))
WRAPV(EmAtCheck, (void* m), (m))
WRAPV(_ZN10cAtariInfo4moveEv, (void* a), (a))
// skeleton: IK, cloth, shape, the model's motion step
WRAPV(InverseKinematics, (void* m, int f), (m, f))
WRAPV(_Z15PlClothMoveLeonP6cModelP7PlClothS2_S2_, (void* m, void* a, void* b, void* c), (m, a, b, c))
WRAPV(ShapeMove, (void* i), (i))
WRAP(int, _ZN6cModel10motionMoveEv, (void* m), (m))
// collision queries
WRAP(float, _ZN7cSatMgr8getFloorEP3VecffPmi, (void* s, void* p, float u, float d, void* a, int f), (s, p, u, d, a, f))
WRAP(int, _ZN7cSatMgr8hitCheckEP3VecS1_S1_S1_ii, (void* s, void* a, void* b, void* c, void* d, int f, int m), (s, a, b, c, d, f, m))
WRAP(int, _ZN7cSatMgr9hitCheck2EP3VecS1_S1_Pmii, (void* s, void* a, void* b, void* c, void* d, int f, int m), (s, a, b, c, d, f, m))

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
        printf("E1 SVC %s us %lu calls %lu\n", svc_rows[i].name, (unsigned long) svc_rows[i].us, (unsigned long) svc_rows[i].calls);
    for (unsigned i = 0; i < nprof; i++)
        printf("E1 PROF %s us %lu calls %lu\n", prof[i].name, (unsigned long) prof[i].us, (unsigned long) prof[i].calls);
}
