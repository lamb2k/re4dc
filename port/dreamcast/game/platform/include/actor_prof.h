// actor_prof.h (actorplan.mk ACTOR_PROF=1; diagnostic builds only, default 0: every macro is empty and nothing is
// compiled): SH-4 time in 200 MHz cycles (TMU2 ns timer / 5; Flycast does not count PRFC0) per character class and per
// phase of the owned character path, logged as "APROF" lines every 300 source frames (per-frame averages). Classes:
// 0 Leon (model id 0), 1 Ganado (ids 0x10..0x20), 2 other owned actors, 3 one_chunk outside a transaction. Phases are
// listed in kAprofNames (native_actor_fast.cpp); nested phases are inside their parent (PAL and PRE1 inside ACQ,
// PRE2/CHUNK inside SUB, POS/LIT/PACK inside CHUNK); WFL (the PS2 world flush an owned run triggers) is world work and
// is subtracted from TX and SUB. The counter reads themselves add a few hundred cycles per call: compare arms that
// both have ACTOR_PROF=1, never against a build without it.
#pragma once
#if defined(RE4DC_ACTOR_PROF) && RE4DC_ACTOR_PROF
#ifdef __cplusplus
extern "C" {
#endif
enum {
    APROF_TX = 0, APROF_PLAN, APROF_SEM1, APROF_CROWD, APROF_ACQ, APROF_PAL, APROF_PRE1, APROF_PASS, APROF_SUB,
    APROF_PRE2, APROF_WFL, APROF_CHUNK, APROF_POS, APROF_LIT, APROF_PACK, APROF_PHASES
};
// N_UVI / N_UNI: distinct position / normal indices per chunk (the records drawn repeat them across meshlets and seams)
// N_UTR: distinct (position, normal, uv) records per chunk (approximate: the last triple seen per position);
// N_UVM: distinct positions per meshlet, summed (what a per-meshlet cache could share)
enum { APROF_N_CALLS = 0, APROF_N_CHUNKS, APROF_N_VERTS, APROF_N_MESHLETS, APROF_N_HITS, APROF_N_UVI, APROF_N_UNI,
       APROF_N_UTR, APROF_N_UVM, APROF_COUNTS };
extern unsigned re4dc_aprof_cls;
extern unsigned re4dc_aprof_wfl_cycles;  // WFL cycles so far (TX / SUB subtract their share)
unsigned re4dc_aprof_now(void);
void re4dc_aprof_add(unsigned phase, unsigned cycles);
void re4dc_aprof_count(unsigned what, unsigned n);
void re4dc_aprof_frame(unsigned frame);
#ifdef __cplusplus
}
#endif
#define APROF_T0(v) const unsigned v = re4dc_aprof_now()
#define APROF_ADD(ph, v) re4dc_aprof_add((ph), re4dc_aprof_now() - (v))
#define APROF_COUNT(w, n) re4dc_aprof_count((w), (n))
#define APROF_CLS(c) (re4dc_aprof_cls = (c))
#define APROF_FRAME(f) re4dc_aprof_frame(f)
#ifdef __cplusplus
// A phase span that ends at stop() or at scope exit (early returns), whichever comes first.
struct AprofSpan {
    unsigned ph, t; bool on;
    explicit AprofSpan(unsigned p) : ph(p), t(re4dc_aprof_now()), on(true) {}
    void stop() { if (on) { re4dc_aprof_add(ph, re4dc_aprof_now() - t); on = false; } }
    ~AprofSpan() { stop(); }
};
#define APROF_SPAN(name, ph) AprofSpan name(ph)
#define APROF_STOP(name) name.stop()
#endif
#else
#define APROF_SPAN(name, ph) ((void)0)
#define APROF_STOP(name) ((void)0)
#define APROF_T0(v) ((void)0)
#define APROF_ADD(ph, v) ((void)0)
#define APROF_COUNT(w, n) ((void)0)
#define APROF_CLS(c) ((void)0)
#define APROF_FRAME(f) ((void)0)
#endif
