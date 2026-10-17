// actor_plan.h (actorplan.mk ACTOR_PLAN; render only, exact): the character draw plan's shared switch and counters.
// ACTOR_PLAN=1 replays what the owned character path proved before (in this transaction call, or since the last
// lifetime change) instead of proving it again; =2 (compare build) also runs every original proof, lets the original
// decide, and counts each reuse whose verdict differed ("APLAN" lines; every *_bad must stay 0). With ACTOR_PLAN=0 this
// header defines RE4DC_PLAN_ON as 0 and nothing else.
//
// re4dc_actor_plan_on: runtime switch (1 by default). The benchmark disc's lever (BENCH_LEVERS, bench_lever.h
// RE4DC_LV_NOPLAN) sets it to 0 at boot so one image measures the plan on and off on the console with the same code
// layout. 0 = every proof runs as with ACTOR_PLAN=0.
#pragma once
#if defined(RE4DC_ACTOR_PLAN) && RE4DC_ACTOR_PLAN
#ifdef __cplusplus
extern "C" {
#endif
extern unsigned re4dc_actor_plan_on;
// Compare / hit counters (ACTOR_PLAN=2 prints them; =1 keeps only the hit counts for ACTOR_PROF's report).
enum {
    APLAN_BIND = 0,   // Leon's palette bind replays the plan's bind of this call
    APLAN_PRE,        // the first submission replays the acquisition preflight of this call
    APLAN_ROLES,      // re4dc_actor_role_bindings replayed from the role memo
    APLAN_ROW,        // actor_current_role replayed from the row memo
    APLAN_HAND,       // a hand info's TPL texture verdict replayed
    APLAN_SEM,        // actor_semantics' chunk proofs / sums / run checks replayed
    APLAN_MAT,        // a Ganado source material replayed
    APLAN_KINDS
};
void re4dc_actor_plan_note(unsigned kind, int hit, int bad);
#ifdef __cplusplus
}
#endif
#define RE4DC_PLAN_ON (re4dc_actor_plan_on != 0)
#define RE4DC_PLAN_COMPARE (RE4DC_ACTOR_PLAN == 2)
#ifdef __cplusplus
// Every one of n floats is finite, by the same exponent test as coarse_finite (coarse_skin.h): bit 31 of (exponent
// field + 0x00800000) is set iff the field is all ones. One OR per word instead of a branch per float.
inline bool re4dc_plan_all_finite(const float* f, unsigned n) {
    typedef unsigned __attribute__((may_alias)) Word;
    const Word* w = reinterpret_cast<const Word*>(f);
    unsigned bad = 0;
    for (unsigned i = 0; i < n; ++i) bad |= (w[i] & 0x7f800000u) + 0x00800000u;
    return !(bad & 0x80000000u);
}
#endif
#else
#define RE4DC_PLAN_ON 0
#define RE4DC_PLAN_COMPARE 0
#endif
