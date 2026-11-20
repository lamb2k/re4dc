// E1 frame services (lane eng-e1): room init of the engine tables, the per-tick trace, pacing and the report.
#include "global.h"
#include "player.h"
#include "em.h"
#include "obj.h"
#include "model.h"
#include "main.h"
#include "view.h"
#include "e1_engine.h"
#include "e1_core.h"
#include "skel.h"
#include "e1_kos.h"
#include <stdio.h>
#include <string.h>
#ifdef E2_BOSS
#include "boss_e2.h"
#endif

extern "C" unsigned short e1_rnd_state(void);
extern "C" unsigned e1_rnd_draws;
extern cModInfoMgr ModInfoMgr;
extern cPartsMgr PartsMgr;
void e1_prof_report();

void e1_managers_room_init()
{
    // the hill scene adds the partner: her model set (body, head, hair, two armour parts, hands) and her parts
    const bool hill = e1_scene == E1_SCENE_HILL;
    ModInfoMgr.roomInit();
    ModInfoMgr.arrayAlloc(hill ? 96 : 64);
    PartsMgr.roomInit();
    PartsMgr.arrayAlloc(hill ? 512 : 256);
    EmMgr.roomInit();
    EmMgr.arrayAlloc(4);
    ObjMgr.roomInit();
    ObjMgr.arrayAlloc(8);
}
void e1_view_room_init() { View.roomInit(); }

// ---- per-tick trace: the reference's LT fields for the player, plus the motion identity ----
// LT t=<tick> r=<rng16> d=<rng draws this tick> p=<pos bits> a=<ang bits> m=<Mot_frame bits>/<Mot_state> st=<stat>
//    mi=<motion data offset in its archive> c=<camera eye bits>
static unsigned last_draws;
// The reference trace's state digests (port/dreamcast/game/logic_trace.cpp model_state, FNV-1a over 32-bit words):
// ps = be_flag, stat, id, type, Mot_state; pf = the coordinate block (mat, l_mat, world .. prevMat), speed, pos_old,
// Mot_frame; pm = every cParts coordinate block on the pParts chain (the skeleton's output); c = pG->Cam.param.
struct Fnv {
    unsigned h = 2166136261u;
    void word(unsigned w) { h = (h ^ w) * 16777619u; }
    void words(const void* p, unsigned bytes) { const unsigned char* b = (const unsigned char*) p;
        for (unsigned i = 0; i + 4 <= bytes; i += 4) { unsigned w; memcpy(&w, b + i, 4); word(w); } }
    template <class T> void add(const T& v) { unsigned w = 0; memcpy(&w, &v, sizeof(v) < 4 ? sizeof(v) : 4); word(w); }
};
static void coord_block(Fnv& f, const void* unit)
{
    const unsigned char* b = (const unsigned char*) unit;
    f.words(b + 0x0C, 0x6C - 0x0C);
    f.words(b + 0x70, 0xF4 - 0x70);
}
static void model_state(Fnv& discrete, Fnv& coords, Fnv& parts, cModel* m)
{
    discrete.add(m->be_flag);
    discrete.add(m->stat);
    discrete.add(m->id);
    discrete.add(m->type);
    discrete.add(m->Motion.Mot_state);
    coord_block(coords, m);
    coords.words(&m->speed, sizeof(Vec) * 2);
    coords.add(m->Motion.Mot_frame);
    // the skeleton's output: the native table's world records and local matrices (lane eng-e1c)
    const SkelTable* t = skel_table_of(m);
    unsigned n = t ? t->n : 0;
    for (unsigned k = 0; k < n; k++) { parts.words(&t->world[k], 64); parts.words(&t->lmat[k], 48); }
    parts.word(n);
}
static uint32_t bits(float f) { uint32_t u; memcpy(&u, &f, 4); return u; }
static uint32_t motion_id(cModel* m)
{
    const uint8_t* d = (const uint8_t*) m->Motion.pMot;
    if (!d) return 0;
    if (pG->pPlayer && d >= (const uint8_t*) pG->pPlayer && d < (const uint8_t*) pG->pPlayer + 0x200000)
        return 0x10000000 | (uint32_t) (d - (const uint8_t*) pG->pPlayer);
    if (pG->pWep && d >= (const uint8_t*) pG->pWep && d < (const uint8_t*) pG->pWep + 0x100000)
        return 0x20000000 | (uint32_t) (d - (const uint8_t*) pG->pWep);
    return 0xF0000000;
}
// The trace lines go to a RAM buffer during the run (no serial time inside the pictures) and are printed with the
// report; with the NOTRACE boot option they are not formatted at all.
static char trace_buf[192 * 1024];
static unsigned trace_len;
void e1_trace_flush()
{
    fwrite(trace_buf, 1, trace_len, stdout);
    trace_len = 0;
}
void e1_trace_put(const char* line, unsigned n)
{
    if (trace_len + n + 1 > sizeof(trace_buf)) e1_trace_flush();
    memcpy(trace_buf + trace_len, line, n);
    trace_len += n;
}
void e1_trace_tick(unsigned tick)
{
    static int notrace = -1;
    if (notrace < 0) { file_t f = fs_open("/cd/NOTRACE", O_RDONLY); notrace = f >= 0; if (f >= 0) fs_close(f); }
    if (notrace) return;
    if (e1_scene == E1_SCENE_HILL) {   // lane eng-e1b: re4ref trace v2 lines (Leon and every character)
        e1_trace_v2(tick);
        return;
    }
    cPlayer* p = pPL;
    unsigned draws = e1_rnd_draws - last_draws;
    last_draws = e1_rnd_draws;
    if (!p) return;
    Fnv ps, pf, pm, cam;
    model_state(ps, pf, pm, p);
    cam.words(&pG->Cam.param, 32);
    if (trace_len + 256 > sizeof(trace_buf)) e1_trace_flush();
    trace_len += snprintf(trace_buf + trace_len, sizeof(trace_buf) - trace_len, "LT t=%u r=%04x d=%u p=%08lx,%08lx,%08lx a=%08lx,%08lx,%08lx m=%08lx/%x st=%08lx mi=%08lx k=%08lx ps=%08x pf=%08x pm=%08x c=%08x\n", tick,
           e1_rnd_state(), draws, (unsigned long) bits(p->pos.x), (unsigned long) bits(p->pos.y), (unsigned long) bits(p->pos.z),
           (unsigned long) bits(p->ang.x), (unsigned long) bits(p->ang.y), (unsigned long) bits(p->ang.z),
           (unsigned long) bits(p->Motion.Mot_frame), (unsigned) p->Motion.Mot_state, (unsigned long) p->stat,
           (unsigned long) motion_id(p), (unsigned long) Key.on, ps.h, pf.h, pm.h, cam.h);
#ifdef E2_BOSS
    if (trace_len + 4096 > sizeof(trace_buf)) e1_trace_flush();
    e2_trace_tick(tick, trace_buf, sizeof(trace_buf), &trace_len);
#endif
}

// ---- pacing on the display's field count (lane eng-e1g, H-014.1): one logic tick a picture, two 60 Hz fields ----
// The pacer waits on the vblank handler's field count (core/draw_e1.c), not on a timer: each tick starts on a field
// boundary, two fields after the last, so a picture that is ready in time is flipped every second field. A picture
// that finishes late (its target field has already begun) is shown on the next field by the chip; the pacer then adds
// no wait and the next target is two fields from now. The ROW wait column is this wait: from the end of the picture's
// submission (after the LATEPIC hold) to the target field, in microseconds; 0 means late.
// Lab arm PACETMU (boot option, for the console A/B; not a build switch): the earlier pacer, 33,367 us on the timer,
// whose phase drifts against the display (3-field gaps with no late picture, lane eng-e1f).
extern "C" uint32_t e1_fields_now_c(void);
extern "C" void e1_present_next_c(uint32_t field);
extern "C" unsigned e1_present_drops_c(void);
static int pace_tmu, pace_manual;
static uint32_t pace_field;
static uint64_t next_us;
void e1_pace_end(E1Timing& tm)
{
    const uint64_t now = timer_us_gettime64();
    if (pace_tmu) {
        if (!next_us) next_us = now;
        next_us += 33367;
        if (now < next_us) {
            tm.wait_us = next_us - now;
            while (timer_us_gettime64() < next_us) thd_pass();
        } else {
            tm.wait_us = 0;
            next_us = now;
        }
        return;
    }
    const uint32_t f = e1_fields_now_c();
    pace_field += 2;
    const bool late = (int32_t) (pace_field - f) <= 0;
    if (late) pace_field = f;
    e1_present_next_c(pace_field + 1);   // this picture is released when the next tick's second field begins
    if (!late) {
        while ((int32_t) (pace_field - e1_fields_now_c()) > 0) thd_pass();
        const uint64_t w = timer_us_gettime64() - now;
        tm.wait_us = w ? (uint32_t) w : 1;
    } else {
        tm.wait_us = 0;
    }
}

// ---- presented fields (lane eng-e1f): the 30 fps floor is judged on the interval between presented pictures ----
// A vblank handler (core/draw_e1.c, as the bench's bench/main.c) counts the 60 Hz fields and records the field number
// of each change of the display address (the chip's page flip): picture k (tick k + 1) is flip k, and its interval is
// flip k - flip k-1 in fields. This is the hardware's field count, not the software pacer. A headless image presents
// no picture: its interval is then the tick's, the field number at the end of each tick's pace (mode "tick").
// Control LATEPIC (boot option): picture 300 is held 100 ms after its scene is finished (inside no timed row but the
// frame), so picture 301 (tick 300 when headless) must show as the worst interval, at least five fields. A 40 ms hold
// gave 3 or 4 fields, which the pacer's own 3-field intervals can equal (lanes/eng-e1f.md).
extern "C" {
int e1_fields_start_c(int manual);
unsigned e1_fields_finish_c(const volatile uint32_t** field);
}
static uint32_t tick_field[E1_TICKS];
static int late_control;
void e1_fields_start()
{
    file_t f = fs_open("/cd/LATEPIC", O_RDONLY);
    if (f >= 0) { fs_close(f); late_control = 1; e1_log("E1 LATEPIC: picture 300 held 100 ms after its scene (control)\n"); }
    f = fs_open("/cd/PACETMU", O_RDONLY);
    if (f >= 0) { fs_close(f); pace_tmu = 1; }
    pace_manual = e1_fields_start_c(!pace_tmu);   // returns just after a field boundary
    pace_field = e1_fields_now_c();               // tick 1's target is two fields from here
    e1_log("E1 PACE %s, presentation %s\n", pace_tmu ? "tmu 33367 us (lab arm PACETMU)" : "fields 2 (display field count)",
           pace_manual ? "fixed field (release at the next tick's second field)" : "at render end (automatic flip)");
}
void e1_fields_late(unsigned tick)
{
    if (!late_control || tick != 300) return;
    uint64_t t = timer_us_gettime64();
    while (timer_us_gettime64() - t < 100000) {}
}
void e1_fields_tick(unsigned tick) { tick_field[(tick - 1) % E1_TICKS] = e1_fields_now_c(); }
// Fills each row's fields column and prints the window's line (pictures 41 to 640, as the selector and budget.py):
// "E1 FIELDS mode presented|tick flips F of P pictures; pictures 41-640: intervals>2 N worst W (picture K)".
void e1_fields_finish(unsigned ticks)
{
    const volatile uint32_t* flip = 0;
    const unsigned flips = e1_fields_finish_c(&flip);
    const unsigned n = ticks < E1_TICKS ? ticks : E1_TICKS;
    const bool presented = flips > 0;
    for (unsigned i = 0; i < n; i++) {
        uint32_t f = 0;
        if (i && presented && i < flips) f = flip[i] - flip[i - 1];
        else if (i && !presented) f = tick_field[i] - tick_field[i - 1];
        e1_timing[i].fields = f;
    }
    unsigned over = 0, worst = 0, wi = 0, counted = 0;
    for (unsigned i = 40; i < n && i < 640; i++) {
        const uint32_t f = e1_timing[i].fields;
        if (!f) continue;
        counted++;
        over += f > 2;
        if (f > worst) { worst = f; wi = i + 1; }
    }
    e1_log("E1 FIELDS mode %s flips %u of %u pictures; pictures 41-640: counted %u intervals>2 %u worst %u (picture %u)\n",
           presented ? "presented" : "tick", flips, n, counted, over, worst, wi);
}

void e1_report()
{
    e1_trace_flush();
    e1_log_flush();   // lane eng-e1e: the log lines written during the ticks (core/globals.cpp)
    e1_log("E1 DONE ticks=%lu\n", (unsigned long) e1_state[2]);
    e1_stub_report();
    e1_prof_report();
    e1_svc_report();
    for (int i = 0; i < 13; i++)
        if (e1_arena.heap_hi[i])
            e1_log("E1 ARENA heap %d %08lx-%08lx used %lu peak %lu fails %lu\n", i, (unsigned long) e1_arena.heap_lo[i],
                   (unsigned long) e1_arena.heap_hi[i], (unsigned long) e1_arena.used[i], (unsigned long) e1_arena.peak[i],
                   (unsigned long) e1_arena.fails[i]);
    e1_log("E1 ARENA allocs %lu frees %lu\n", (unsigned long) e1_arena.allocs, (unsigned long) e1_arena.frees);
    unsigned n = e1_state[2] < E1_TICKS ? e1_state[2] : E1_TICKS;
    for (unsigned i = 0; i < n; i++) {
        const E1Timing& t = e1_timing[i];
        printf("ROW %u in %lu tick %lu svc %lu trace %lu draw %lu wait %lu frame %lu fields %lu pl %lu obj %lu cam %lu pvr %lu chars %lu smot %lu scloth %lu sparts %lu scol %lu sfx %lu\n", i + 1,
               (unsigned long) t.input_us, (unsigned long) t.tick_us, (unsigned long) t.services_us, (unsigned long) t.trace_us,
               (unsigned long) t.draw_us, (unsigned long) t.wait_us, (unsigned long) t.frame_us, (unsigned long) t.fields,
               (unsigned long) t.player_us, (unsigned long) t.obj_us, (unsigned long) t.cam_us, (unsigned long) t.pvr_us,
               (unsigned long) t.chars_us,
               (unsigned long) t.svc_group_us[E1_SVC_MOTION], (unsigned long) t.svc_group_us[E1_SVC_CLOTH],
               (unsigned long) t.svc_group_us[E1_SVC_PARTS], (unsigned long) t.svc_group_us[E1_SVC_COLLISION],
               (unsigned long) t.svc_group_us[E1_SVC_EFFECTS]);
    }
    e1_log("E1 END\n");
}
