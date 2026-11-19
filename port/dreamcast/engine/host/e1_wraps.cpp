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
static inline void enter() { if (depth++ == 0) svc_t0 = timer_us_gettime64(); }
static inline void leave() { if (--depth == 0) svc_acc += timer_us_gettime64() - svc_t0; }
}
void e1_svc_begin() { svc_acc = 0; depth = 0; }
uint32_t e1_svc_end() { return (uint32_t) svc_acc; }

#define WRAP(ret, mangled, params, args)                          \
    extern "C" ret __real_##mangled params;                       \
    extern "C" ret __wrap_##mangled params                        \
    {                                                             \
        enter();                                                  \
        ret r = __real_##mangled args;                            \
        leave();                                                  \
        return r;                                                 \
    }
#define WRAPV(mangled, params, args)                              \
    extern "C" void __real_##mangled params;                      \
    extern "C" void __wrap_##mangled params                       \
    {                                                             \
        enter();                                                  \
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
