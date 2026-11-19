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
#include "e1_kos.h"
#include <stdio.h>
#include <string.h>

extern "C" unsigned short e1_rnd_state(void);
extern "C" unsigned e1_rnd_draws;
extern cModInfoMgr ModInfoMgr;
extern cPartsMgr PartsMgr;
void e1_prof_report();

void e1_managers_room_init()
{
    ModInfoMgr.roomInit();
    ModInfoMgr.arrayAlloc(64);
    PartsMgr.roomInit();
    PartsMgr.arrayAlloc(256);
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
    unsigned n = 0;
    for (cModel* p = m->pParts; p && n < 256; p = (cModel*) ((cParts*) p)->pList, ++n) coord_block(parts, p);
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
void e1_trace_tick(unsigned tick)
{
    static int notrace = -1;
    if (notrace < 0) { file_t f = fs_open("/cd/NOTRACE", O_RDONLY); notrace = f >= 0; if (f >= 0) fs_close(f); }
    if (notrace) return;
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
}

// ---- pacing: one logic tick a picture at 30 fps (two 60 Hz fields); a late picture runs the next tick at once ----
static uint64_t next_us;
void e1_pace_end(E1Timing& tm)
{
    uint64_t now = timer_us_gettime64();
    if (!next_us) next_us = now;
    next_us += 33367;
    if (now < next_us) {
        tm.wait_us = next_us - now;
        while (timer_us_gettime64() < next_us) thd_pass();
    } else {
        tm.wait_us = 0;
        next_us = now;
    }
}

void e1_report()
{
    e1_trace_flush();
    e1_log("E1 DONE ticks=%lu\n", (unsigned long) e1_state[2]);
    e1_stub_report();
    e1_prof_report();
    for (int i = 0; i < 13; i++)
        if (e1_arena.heap_hi[i])
            e1_log("E1 ARENA heap %d %08lx-%08lx used %lu peak %lu fails %lu\n", i, (unsigned long) e1_arena.heap_lo[i],
                   (unsigned long) e1_arena.heap_hi[i], (unsigned long) e1_arena.used[i], (unsigned long) e1_arena.peak[i],
                   (unsigned long) e1_arena.fails[i]);
    e1_log("E1 ARENA allocs %lu frees %lu\n", (unsigned long) e1_arena.allocs, (unsigned long) e1_arena.frees);
    unsigned n = e1_state[2] < E1_TICKS ? e1_state[2] : E1_TICKS;
    for (unsigned i = 0; i < n; i++) {
        const E1Timing& t = e1_timing[i];
        printf("ROW %u in %lu tick %lu svc %lu trace %lu draw %lu wait %lu frame %lu fields %lu pl %lu obj %lu cam %lu pvr %lu\n", i + 1,
               (unsigned long) t.input_us, (unsigned long) t.tick_us, (unsigned long) t.services_us, (unsigned long) t.trace_us,
               (unsigned long) t.draw_us, (unsigned long) t.wait_us, (unsigned long) t.frame_us, (unsigned long) t.fields,
               (unsigned long) t.player_us, (unsigned long) t.obj_us, (unsigned long) t.cam_us, (unsigned long) t.pvr_us);
    }
    e1_log("E1 END\n");
}
