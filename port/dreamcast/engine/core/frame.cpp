// E1 frame services (lane eng-e1): room init of the engine tables, the per-tick trace, pacing and the report.
#include "global.h"
#include "e1_clock.h"   // lane eng-clock1: the engine's clock (TMU2 counts at the reload's rate)
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
#include "memory/heap.h"
#include "camera/eng_camera.h"   // lane eng-e1l: the camera record's trace line
#include "camera/camera_svc.h"   // lane eng-e1p: the camera tracks' play brackets and controls
#include <stdio.h>
#include <string.h>
#ifdef E2_BOSS
#include "boss_e2.h"
#endif
#ifdef E2_FIGHT
#include "shot_e2.h"
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
static int notrace = -1;   // the NOTRACE boot file (lane eng-e1k: read by the run's kind line too)
// lane eng-e1m: the CAMDIAG boot file (trace runs only) sends the camera's diagnosis lines (eng_camera.h) to the trace
static void cam_diag_put(const char* line, unsigned n) { e1_trace_put(line, n); }
void e1_trace_tick(unsigned tick)
{
    if (notrace < 0) {
        file_t f = fs_open("/cd/NOTRACE", O_RDONLY); notrace = f >= 0; if (f >= 0) fs_close(f);
#ifdef E2_FIGHT
        if (e2_shot.active) notrace = 0;   // lane eng-e1k: the shot fixture is a traced function run, always
#endif
        if (!notrace) {
            f = fs_open("/cd/CAMDIAG", O_RDONLY);
            if (f >= 0) { fs_close(f); eng_cam_diag_sink = cam_diag_put; e1_log("E1 CAMDIAG: the camera's diagnosis lines in the trace\n"); }
        }
    }
    if (notrace) return;
    {   // lane eng-e1l: the camera record's eye, target, roll, fov and the controller's decisions (hostref/svc/camengine)
        if (trace_len + 192 > sizeof(trace_buf)) e1_trace_flush();
        trace_len += (unsigned) eng_cam_trace_line(trace_buf + trace_len, sizeof(trace_buf) - trace_len, tick);
    }
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
    const uint64_t now = e1_clock_us();
    if (pace_tmu) {
        if (!next_us) next_us = now;
        next_us += 33367;
        if (now < next_us) {
            tm.wait_us = next_us - now;
            while (e1_clock_us() < next_us) thd_pass();
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
        const uint64_t w = e1_clock_us() - now;
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
int e1_draw_opened_c(void);
int e1_draw_stills_c(void);
}
void e1_memmap_control(unsigned tick);
void e1_memmap_after();
static uint32_t tick_field[E1_TICKS];
static int late_control, rowdup_control;
// lane eng-e1o (H-017.7): the record's controls, read once before play (core/e1_core.h lists them)
E1Lab e1_lab;
static int boot_file(const char* name)
{
    file_t f = fs_open(name, O_RDONLY);
    if (f < 0) return 0;
    fs_close(f);
    return 1;
}
void e1_lab_boot()
{
    if ((e1_lab.camrec0 = boot_file("/cd/CAMREC0"))) e1_log("E1 CAMREC0: the camera record's check skipped every tick (control)\n");
    if ((e1_lab.memcut = boot_file("/cd/MEMCUT"))) e1_log("E1 MEMCUT: the after-play memory line cut short (control)\n");
    if ((e1_lab.runfunc = boot_file("/cd/RUNFUNC"))) e1_log("E1 RUNFUNC: the run line says function, nothing traced (control)\n");
    if ((e1_lab.numtext = boot_file("/cd/NUMTEXT"))) e1_log("E1 NUMTEXT: the release-queue count printed as text (control)\n");
    if ((e1_lab.openx = boot_file("/cd/OPENX"))) e1_log("E1 OPENX: a boot file looked up at picture 100 (control)\n");
    if ((e1_lab.stackx = boot_file("/cd/STACKX"))) e1_log("E1 STACKX: a guard word overwritten at tick 300 (control)\n");
    // lane eng-e1n: the publication and HUD controls (services/draw.cpp acts on them at the renderer's open)
    if ((e1_lab.lightmiss = boot_file("/cd/LIGHTMISS"))) e1_log("E1 LIGHTMISS: every character's light view refused (control)\n");
    if ((e1_lab.hudfreeze = boot_file("/cd/HUDFREEZE"))) e1_log("E1 HUDFREEZE: the HUD's ammo count frozen at the renderer's open (control)\n");
    // lane eng-e1p (H-018): the camera tracks', the record's and the disc reads' controls
    if ((e1_lab.cutconv = boot_file("/cd/CUTCONV"))) {
        cam_track_cut_convert = 1;
        e1_log("E1 CUTCONV: a cut switch converts its camera track in play, as before lane eng-e1p (control)\n");
    }
    if ((e1_lab.camstore = boot_file("/cd/CAMSTORE"))) {
        cam_track_limit = 1024;
        e1_log("E1 CAMSTORE: the camera track store limited to 1024 bytes (control: the room must be refused)\n");
    }
    if ((e1_lab.memnofree = boot_file("/cd/MEMNOFREE"))) e1_log("E1 MEMNOFREE: the after-play line without mallinfo free (control)\n");
    if ((e1_lab.ticks1 = boot_file("/cd/TICKS1"))) e1_log("E1 TICKS1: the tick count and the camera ticks reported as 1 (control)\n");
    if ((e1_lab.rowtoken = boot_file("/cd/ROWTOKEN"))) e1_log("E1 ROWTOKEN: row 300's fields value printed with a trailing token (control)\n");
    if ((e1_lab.readx = boot_file("/cd/READX"))) {
        // a disc file opened before play (the hill's partner archive: never read by the village scene, so not cached),
        // read at picture 100 (core/frame.cpp e1_fields_late)
        e1_lab.readx_fd = fs_open("/cd/em/pl11.drs", O_RDONLY);
        e1_log("E1 READX: a disc file opened before play (fd %d), 2048 bytes read at picture 100 (control)\n", e1_lab.readx_fd);
    }
}
void e1_fields_start()
{
    // lane eng-e1k (H-016.6): the run says what it is. Traces formatted inside the pictures, or stills handed over
    // during play, make it a function run: the selector never reports its rows as timing.
    {
        const int traced = notrace == 0, still = e1_draw_stills_c();
        if (traced || still)
            e1_log("E1 RUN function (%s%s%s): not a timing run\n", traced ? "traced" : "", traced && still ? ", " : "",
                   still ? "stills" : "");
        else if (e1_lab.runfunc)
            e1_log("E1 RUN function (lab arm RUNFUNC): not a timing run\n");
        else
            e1_log("E1 RUN timing (no trace, no stills)\n");
    }
    file_t f = fs_open("/cd/ROWDUP", O_RDONLY);
    if (f >= 0) { fs_close(f); rowdup_control = 1; e1_log("E1 ROWDUP: the row of picture 300 printed twice (control)\n"); }
    f = fs_open("/cd/LATEPIC", O_RDONLY);
    if (f >= 0) { fs_close(f); late_control = 1; e1_log("E1 LATEPIC: picture 300 held 100 ms after its scene (control)\n"); }
    f = fs_open("/cd/PACETMU", O_RDONLY);
    if (f >= 0) { fs_close(f); pace_tmu = 1; }
    pace_manual = e1_fields_start_c(!pace_tmu);   // returns just after a field boundary
    pace_field = e1_fields_now_c();               // tick 1's target is two fields from here
    e1_log("E1 PACE %s, presentation %s\n", pace_tmu ? "tmu 33367 us (lab arm PACETMU)" : "fields 2 (display field count)",
           pace_manual ? "fixed field (release at the next tick's second field)" : "at render end (automatic flip)");
    e1_play_files_begin();   // lane eng-e1o: from here to the last picture every file open is counted (E1 FILES)
    cam_track_in_play(1);    // lane eng-e1p: a camera track converted from here on is a conversion in play (E1 CAMTRACK)
}
void e1_fields_late(unsigned tick)
{
    e1_memmap_control(tick);   // STACKX (lane eng-e1k): the stack guard's control
    if (e1_lab.openx && tick == 100) { file_t f = fs_open("/cd/OPENX", O_RDONLY); if (f >= 0) fs_close(f); }   // OPENX (control)
    if (e1_lab.readx && tick == 100 && e1_lab.readx_fd >= 0) {   // READX (lane eng-e1p, control): no open, a read
        static char b[2048];
        fs_seek(e1_lab.readx_fd, 65536, SEEK_SET);
        fs_read(e1_lab.readx_fd, b, sizeof b);
    }
    if (!late_control || tick != 300) return;
    uint64_t t = e1_clock_us();
    while (e1_clock_us() - t < 100000) {}
}
void e1_fields_tick(unsigned tick) { tick_field[(tick - 1) % E1_TICKS] = e1_fields_now_c(); }
// Fills each row's fields column and prints the window's line (pictures 41 to 640, as the selector and budget.py):
// "E1 FIELDS mode presented|tick flips F of P pictures; pictures 41-640: intervals>2 N worst W (picture K)".
void e1_fields_finish(unsigned ticks)
{
    e1_play_files_end();
    cam_track_in_play(0);
    const volatile uint32_t* flip = 0;
    const unsigned flips = e1_fields_finish_c(&flip);
    const unsigned n = ticks < E1_TICKS ? ticks : E1_TICKS;
    // lane eng-e1k (H-016.6): an image that draws counts presented flips, always: one that showed no picture is a
    // drawing failure with no intervals (the selector fails it), never a headless run in tick mode as before
    const bool presented = e1_draw_opened_c() != 0;
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
    if (e1_lab.numtext)   // NUMTEXT (lane eng-e1o, control): a text field where the drop count belongs
        e1_log("E1 FIELDS mode %s flips %u of %u pictures; pictures 41-640: counted %u intervals>2 %u worst %u (picture %u)"
               "; release queue full none\n", presented ? "presented" : "tick", flips, n, counted, over, worst, wi);
    else
        e1_log("E1 FIELDS mode %s flips %u of %u pictures; pictures 41-640: counted %u intervals>2 %u worst %u (picture %u)"
               "; release queue full %u\n", presented ? "presented" : "tick", flips, n, counted, over, worst, wi,
               e1_present_drops_c());
}

extern "C" struct AimCounters { uint32_t calls, scenery, enemy, enemy_flag40, boxes, capsules, cubes; } aim_cnt;
extern "C" struct AimListCounters { uint32_t calls, scenery, listed, hit_only, empty; } aim_list_cnt;
#include "e1_laser.h"
extern "C" uint32_t eng_pool_full, eng_pool_bad_free;
extern "C" void e1_guards_report(void);   // lane eng-fix1 (H-026): host/guard_hooks.cpp, the guards' counts
void e1_report()
{
    e1_trace_flush();
    e1_log_flush();   // lane eng-e1e: the log lines written during the ticks (core/globals.cpp)
    // TICKS1 (lane eng-e1p, control): the tick count and the camera record's checked ticks both 1 (they agree with each
    // other; the selector must find them against the rows received)
    if (e1_lab.ticks1) eng_cam_check.ticks = 1;
    e1_log("E1 DONE ticks=%lu\n", e1_lab.ticks1 ? 1ul : (unsigned long) e1_state[2]);
    e1_memmap_after();   // lane eng-e1k: the stack guard, heap peak, arena margin and video memory after play
    e1_play_files_report();   // lane eng-e1o (H-017.7): the files opened during play (must be 0)
    e1_stub_report();
    e1_guards_report();
    e1_prof_report();
    e1_svc_report();
    // lane eng-e1g: the native heap service (services/memory/heap.cpp) under the behaviour arena (host/e1_heap.cpp)
    e1_log("E1 HEAPSVC creates %lu allocs %lu frees %lu fails %lu bad_frees %lu overlaps %lu\n",
           (unsigned long) heap_cnt.creates, (unsigned long) heap_cnt.allocs, (unsigned long) heap_cnt.frees,
           (unsigned long) heap_cnt.fails, (unsigned long) heap_cnt.bad_frees, (unsigned long) heap_cnt.overlaps);
    // lanes eng-e1f / eng-e1g: the native weapon-target query (services/aim/aim.cpp)
    e1_log("E1 AIM calls %lu scenery %lu enemy %lu (flag40 %lu) boxes %lu capsules %lu cubes %lu\n",
           (unsigned long) aim_cnt.calls, (unsigned long) aim_cnt.scenery, (unsigned long) aim_cnt.enemy,
           (unsigned long) aim_cnt.enemy_flag40, (unsigned long) aim_cnt.boxes, (unsigned long) aim_cnt.capsules,
           (unsigned long) aim_cnt.cubes);
    // lane eng-e1k: the shot's native target list (services/aim/aim.cpp GetWepTargetList2)
    e1_log("E1 AIM LIST shots %lu scenery %lu enemies listed %lu hit-only %lu empty %lu\n", (unsigned long) aim_list_cnt.calls,
           (unsigned long) aim_list_cnt.scenery, (unsigned long) aim_list_cnt.listed, (unsigned long) aim_list_cnt.hit_only,
           (unsigned long) aim_list_cnt.empty);
    // lane eng-e1h: the laser sight's setters and the renderer's laser pass (services/laser.cpp, core/draw_e1.c); the
    // record pools' refusals (services/model/pool.h: full tables, destroys of records not alive)
    e1_log("E1 LASER sets %lu lines drawn %lu dots drawn %lu\n", (unsigned long) e1_laser.sets,
           (unsigned long) e1_laser.drawn, (unsigned long) e1_laser.dots_drawn);
    e1_log("E1 POOL full %lu bad_frees %lu\n", (unsigned long) eng_pool_full, (unsigned long) eng_pool_bad_free);
    for (int i = 0; i < 13; i++)
        if (e1_arena.heap_hi[i])
            e1_log("E1 ARENA heap %d %08lx-%08lx used %lu peak %lu fails %lu\n", i, (unsigned long) e1_arena.heap_lo[i],
                   (unsigned long) e1_arena.heap_hi[i], (unsigned long) e1_arena.used[i], (unsigned long) e1_arena.peak[i],
                   (unsigned long) e1_arena.fails[i]);
    e1_log("E1 ARENA allocs %lu frees %lu\n", (unsigned long) e1_arena.allocs, (unsigned long) e1_arena.frees);
    unsigned n = e1_state[2] < E1_TICKS ? e1_state[2] : E1_TICKS;
    for (unsigned i = 0; i < n; i++) {
        const E1Timing& t = e1_timing[i];
        // ROWTOKEN (lane eng-e1p, control): row 300's fields value with a trailing token ("2,missing")
        const char* ffmt = e1_lab.rowtoken && i + 1 == 300 ? "%lu,missing" : "%lu";
        char fv[24];
        snprintf(fv, sizeof fv, ffmt, (unsigned long) t.fields);
        printf("ROW %u in %lu tick %lu svc %lu trace %lu draw %lu wait %lu frame %lu fields %s pl %lu obj %lu cam %lu pvr %lu chars %lu smot %lu scloth %lu sparts %lu scol %lu sfx %lu\n", i + 1,
               (unsigned long) t.input_us, (unsigned long) t.tick_us, (unsigned long) t.services_us, (unsigned long) t.trace_us,
               (unsigned long) t.draw_us, (unsigned long) t.wait_us, (unsigned long) t.frame_us, fv,
               (unsigned long) t.player_us, (unsigned long) t.obj_us, (unsigned long) t.cam_us, (unsigned long) t.pvr_us,
               (unsigned long) t.chars_us,
               (unsigned long) t.svc_group_us[E1_SVC_MOTION], (unsigned long) t.svc_group_us[E1_SVC_CLOTH],
               (unsigned long) t.svc_group_us[E1_SVC_PARTS], (unsigned long) t.svc_group_us[E1_SVC_COLLISION],
               (unsigned long) t.svc_group_us[E1_SVC_EFFECTS]);
        if (rowdup_control && i + 1 == 300) { rowdup_control = 0; --i; }   // ROWDUP: this row once more (control)
    }
    e1_log("E1 END\n");
}
