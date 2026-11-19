// game/rnd: the game's random numbers — a 16-bit generator (Rnd: one random byte per call,
// seeded by RndInit) and float helpers on it (fRand0_1 / fRand1_1), plus the seeded LCG variants
// (fRandSeed*) effects use for repeatable per-instance randomness.
#include "types.h"
#include "rnd.h"

static u16 Random;

#if (defined(RE4DC_LOGIC_TRACE) && RE4DC_LOGIC_TRACE) || (defined(RE4DC_ESP_CENSUS) && RE4DC_ESP_CENSUS)
// Determinism trace only (LOGIC_TRACE=1): the generator is seeded once (main.cpp RndInit), so its
// state is a running fingerprint of how many Rnd() draws the game made.
extern "C" unsigned short re4dc_rnd_state(void) { return Random; }
#endif

// Seeds the global 16-bit generator (Rnd / fRand*).
void RndInit(u16 seed)
{
    Random = seed;
}

// The 16-bit truncation `(n << 16) >> 16` keeps m out of n's cse equivalence class (cse does not
// fold the shift pair; combine later reduces it to the copy `mr r0,r9`, which survives because n is
// still needed for `n + 0x101`), so m gets its own register like the original.
u8 Rnd()
{
    u16 r = Random;
    u32 n = ((u8) ((r >> 1) + (r >> 8)) << 8) | (u8) (r >> 1);
    u32 m = (n << 16) >> 16;

    if (m == r) {
        m = n + 0x101;
    }
    Random = m;
    return m >> 8;
}

// Random float in [0, 1) from three Rnd() bytes (23-bit mantissa).
f32 fRand0_1()
{
    u32 a = Rnd();
    u32 b = Rnd();
    u32 c = Rnd();
    u32 u = a + (b << 8) + ((c & 0x7F) << 16) + 0x3F800000;

    return *(f32*) &u - 1.0f;
}

// Random float in [-1, 1).
f32 fRand1_1()
{
    u32 a = Rnd();
    u32 b = Rnd();
    u32 c = Rnd();
    u32 u = a + (b << 8) + ((c & 0x7F) << 16) + 0x3F800000;

    return *(f32*) &u * 2.0f - 3.0f;
}

// Random float in [0, 1) from a caller-owned LCG seed (deterministic per effect / enemy).
f32 fRandSeed0_1(u32* seed)
{
    f32 f;

    *seed = *seed * 0x19660D + 0x3C6EF35F;
    *(u32*) &f = (*seed & 0x007FFFFF) | 0x3F800000;
    f -= 1.0f;
    return f;
}

// Random float in [-1, 1) from a caller-owned LCG seed.
f32 fRandSeed1_1(u32* seed)
{
    f32 f;

    *seed = *seed * 0x19660D + 0x3C6EF35F;
    *(u32*) &f = (*seed & 0x007FFFFF) | 0x3F800000;
    f = f * 2.0f - 2.0f - 1.0f;
    return f;
}
