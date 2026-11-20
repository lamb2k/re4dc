/* The engine's presentation generator behind services/cloth/pres_rng.h's interface (lane eng-e1d; owner 2026-11-19,
   "Split it"). Force-included before the cloth service (game/Makefile), so pres_rng.h's own body is skipped by its
   include guard: the cloth's draws (wind phase, floor jitter) come from the engine generator of host/e1_wraps.cpp
   (e1_pres_u32: the original algorithm on its own state, the same stream as eye wander, camera sway, effects and the
   face), never from the behaviour's Rnd. A stream's state only records its id: every stream draws from the one
   engine generator, so a chain's draws depend on the order presentation code runs in, not on behaviour. */
#ifndef PRES_RNG_H
#define PRES_RNG_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct PresRng {
    uint32_t s;
} PresRng;
uint32_t e1_pres_u32(void);
static inline void pres_seed(PresRng* r, uint32_t id) { r->s = id; }
static inline uint32_t pres_next(PresRng* r) { (void) r; return e1_pres_u32(); }
static inline float pres_f01(PresRng* r) { return (float) (pres_next(r) >> 8) * (1.0f / 16777216.0f); }
static inline float pres_f11(PresRng* r) { return pres_f01(r) * 2.0f - 1.0f; }
#ifdef __cplusplus
}
#endif
#endif
