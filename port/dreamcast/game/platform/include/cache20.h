// cache20.h: PREF_WALK=1 (lane cache20, cache20.mk): `pref` of the next unit in a walk while the current one is worked on,
// when bit 2 of the run-time mask re4dc_cache20_mask (platform/cache20.cpp) is set. Without PREF_WALK the macros are
// empty and nothing changes. A prefetch only moves a line into the operand cache early: no value the game reads changes.
#pragma once
#if defined(RE4DC_PREF_WALK) && RE4DC_PREF_WALK
#ifdef __cplusplus
extern "C" volatile unsigned re4dc_cache20_mask;
#else
extern volatile unsigned re4dc_cache20_mask;
#endif
#define RE4DC_C20_PREF_ON() ((re4dc_cache20_mask & 4u) != 0u)
#define RE4DC_C20_PREF(p) do { const void* c20p_ = (const void*) (p); if (c20p_) __asm__ __volatile__("pref @%0" : : "r"(c20p_) : "memory"); } while (0)
// the first two cache lines of an object (a model's header, flags and matrix head)
#define RE4DC_C20_PREF_OBJ(p) do { if (RE4DC_C20_PREF_ON() && (p)) { RE4DC_C20_PREF(p); RE4DC_C20_PREF((const char*) (p) + 32); } } while (0)
#else
#define RE4DC_C20_PREF_ON() 0
#define RE4DC_C20_PREF(p) ((void) 0)
#define RE4DC_C20_PREF_OBJ(p) ((void) 0)
#endif
