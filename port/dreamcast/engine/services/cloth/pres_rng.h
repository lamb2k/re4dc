/*! \file
 *  \brief   The engine's presentation random numbers (lane eng-svc3): the interface the cloth draws through.
 *
 *  Random numbers are split (owner 2026-11-19, "Split it"): the original generator (Rnd / fRand*) serves behaviour
 *  only; presentation (effects, cloth, sway) draws from an engine generator, so a native presentation service never
 *  changes an AI decision. This is that generator's interface: a stream is one 32-bit state; a service keeps one
 *  stream per object (a cloth chain) seeded from a stream id, so its draws depend on nothing else.
 *
 *  The implementation is xorshift32 (a shift-xor triple and, for the floats, a shift and a multiply). The engine
 *  image may replace it with its own generator behind the same four functions.
 *
 *  \author lane eng-svc3 (RE4 Dreamcast engine line)
 *  \copyright MIT
 */
#ifndef PRES_RNG_H
#define PRES_RNG_H
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

//! One presentation stream.
typedef struct PresRng {
    uint32_t s;
} PresRng;

//! Seeds a stream from its id (any 32-bit value; never a zero state).
static inline void pres_seed(PresRng* r, uint32_t id) {
    r->s = 0x9E3779B9u * id ^ 0x2545F491u;
    if (!r->s) r->s = 0x2545F491u;
}

//! The next 32-bit draw.
static inline uint32_t pres_next(PresRng* r) {
    uint32_t x = r->s;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    r->s = x;
    return x;
}

//! A float in [0, 1) (24 bits), as fRand0_1 gives one.
static inline float pres_f01(PresRng* r) {
    return (float) (pres_next(r) >> 8) * (1.0f / 16777216.0f);
}

//! A float in [-1, 1), as fRand1_1 gives one.
static inline float pres_f11(PresRng* r) {
    return pres_f01(r) * 2.0f - 1.0f;
}

#ifdef __cplusplus
}
#endif
#endif
