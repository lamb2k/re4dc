#include "platform/include/movie_world_arena.h"
// Route cutscenes (PS2-inspired profile: prerecorded cinematics as presentation).
// The caller keeps its whole source sequence around the event: flags, enemy
// sets, positions, doors, ladders, SceAtDataReset. This replaces only the
// evd playback (bodies, camera, lights, messages) with the PS2 movie of the
// same event and reproduces the lasting parts of Event::ExeBeginEvt,
// Event::RunEvtCancel (skip) and Event::ExeEndEvt that outlive an event.
// None of the route evds (GC or PS2) carries SetPl/SetList/PosPl/Func packets.
#include "types.h"
#include "global.h"
#include "main.h"
#include "player.h"
#include "event.h"
#include "sce.h"
#include "snd.h"
#include "route_movie.h"
#include <string.h>
#if defined(RE4DC_ROUTE_CH21) && RE4DC_ROUTE_CH21
#include "cam_ctrl.h"
#define ROUTE_SCE_MODE(flags) (((flags) & ROUTE_MOVIE_SCE_TRUE) ? 1 : 0)
#else
#define ROUTE_SCE_MODE(flags) 0
#endif
extern "C" void re4dc_log(const char* fmt, ...);
#if (defined(RE4DC_DELLAGO_DIAG) && RE4DC_DELLAGO_DIAG) || (defined(RE4DC_ROUTE_QTE_CLOCK) && RE4DC_ROUTE_QTE_CLOCK)
extern "C" unsigned re4dc_vi_retrace_count(void);
#endif
#if defined(RE4DC_DELLAGO_DIAG) && RE4DC_DELLAGO_DIAG
#include <arch/timer.h>
extern "C" void re4dc_movie_diag(unsigned*, unsigned*, unsigned*, unsigned*, unsigned*, int*, int*, unsigned*);
#endif

// Source Evt_*_Func handlers read only funcMode (and NowCut/NowFrame in mode 1)
// in the begin/end/cancel modes used here; no event body exists to fetch.
#if defined(RE4DC_ROUTE_CH13) && RE4DC_ROUTE_CH13
static Event* routeEndEvent;  // ROUTE_MOVIE_ACT_COUNT: the QTE cut's event, handed to the end func
#endif
static void routeFunc(RouteEvtFunc func, int mode)
{
    if (func == 0) {
        return;
    }
#if defined(RE4DC_ROUTE_CH13) && RE4DC_ROUTE_CH13
    if (routeEndEvent != 0 && mode == 2) {
        Event* e = routeEndEvent;
        routeEndEvent = 0;
        e->funcMode = 2;
        func(e);
        return;
    }
#endif
    alignas(8) static u8 storage[sizeof(Event)];
    memset(storage, 0, sizeof(storage));
    Event* e = (Event*) storage;
    e->funcMode = mode;
    func(e);
}

extern "C" void re4dc_ui_movie_background(int on);
#if RE4DC_WEAPON_HEAP4
extern "C" void re4dc_weapon_heap4_movie_restore();   // read.cpp: a weapon body lent to the movie comes back
#else
static inline void re4dc_weapon_heap4_movie_restore() {}
#endif
#if RE4DC_PS2_INTERIOR_CULL
extern "C" void re4dc_ps2_interior_movie_restore();   // native_static.cpp: the r100 cell block a movie borrowed
#else
static inline void re4dc_ps2_interior_movie_restore() {}
#endif
#if defined(RE4DC_FAR_SHELL) && RE4DC_FAR_SHELL
extern "C" void re4dc_far_shell_movie_restore();   // native_static.cpp far_shell.inc: the shell a movie borrowed
#else
static inline void re4dc_far_shell_movie_restore() {}
#endif

#if defined(RE4DC_MOTION_RESUME) && RE4DC_MOTION_RESUME
extern "C" unsigned re4dc_motion_movie_restore();
#endif
#if defined(RE4DC_MOTION_PIN) && RE4DC_MOTION_PIN
extern "C" unsigned re4dc_motion_pin_restore();   // native_motion.cpp: re-read pinned keys a movie evicted
#else
static inline unsigned re4dc_motion_pin_restore() { return 0; }
#endif

// Event::ExeBeginEvt, lasting part: scenario event nesting, event-running status, begin func.
static void routeBegin(unsigned flags, RouteEvtFunc func)
{
    SceEventStart(0);
    BitOn(pG->Status_flg[2], 0x00080000);
    BitOn(pG->Status_flg[2], 0x00010000);
    BitOff(pG->Status_flg[3], 0x01000000);
    routeFunc(func, 0);
    pG->System_flg |= 0x400;
    if (flags & ROUTE_MOVIE_SND_EVENT) {
        SndEventInit();
    }
}

// Event::ExeEndEvt, lasting part (see RouteMoviePlay).
static void routeEnd(unsigned id, unsigned flags, RouteEvtFunc func, int st)
{
    if (!(flags & ROUTE_MOVIE_KEEP_POSE)) {
        Vec pos = pPL->pos;
        Vec rot = pPL->ang;
        pPL->zeroPartsPosInit(&pos, &rot);
    }
    pG->Disp_flg &= ~0x800;
    routeFunc(func, 2);
    pG->System_flg |= 0x40;
    if (flags & ROUTE_MOVIE_SND_EVENT) {
        SndEventEnd();
    }
    BitOff(pG->Status_flg[2], 0x00080000);
    BitOff(pG->Status_flg[2], 0x00010000);
    SceEventEnd(0);
#if defined(RE4DC_MOTION_RESUME) && RE4DC_MOTION_RESUME
    re4dc_motion_movie_restore();
#endif
    re4dc_log("route cutscene: id=%05x terminal=%d end_func=%d pose=%s scenario0=%08x system=%08x room0=%08x\n",
              id, st, func != 0, (flags & ROUTE_MOVIE_KEEP_POSE) ? "kept" : "zero-parts", pG->Scenario_flg[0],
              pG->System_flg, pG->Room_flg[0]);
}

extern "C" void re4dc_fixture_state(const char* name, int a, int b);  // platform/pad.cpp (padscript states)

int RouteMoviePlayQte(unsigned id, unsigned flags, RouteEvtFunc func, unsigned qte_cut, unsigned qte_picture,
                      unsigned qte_frames)
{
    if (!re4dc_movie_available(id)) {
        return RE4DC_MOVIE_UNHANDLED;
    }
    routeBegin(flags, func);
    const u32 disp = pG->Disp_flg;
    pG->Disp_flg = 0xFFFFFFFF;
    int st = re4dc_movie_play_until(id, 0x1000, 0, qte_picture);
    pG->System_flg &= ~0x400;
    if (st == RE4DC_MOVIE_SKIP) {
        // Event::RunEvtCancel with a cancel cut: the cancel marker and mode 3, then the cut itself.
        pG->Status_flg[3] |= 0x01000000;
        routeFunc(func, 3);
        st = re4dc_movie_play_stepped(id | RE4DC_MOVIE_CANCEL_CLIP);
        if (st != RE4DC_MOVIE_RUNNING) {
            re4dc_log("route cutscene: id=%05x cancel clip unavailable (terminal %d): the cut runs without a picture\n", id, st);
        }
    }
    const bool open = st == RE4DC_MOVIE_RUNNING;
    // The cut as game frames (Event::Run mode 1 at qte_cut): the world stays hidden, the action prompt
    // draws over the movie picture: its message (Disp_flg 0x1000 clear; the handler clears 0x800) and its
    // button icons, cockpit ID units of OT type 0x13 (0x2000 and 0x10000 clear, the source's event-UI mask,
    // sce_com.cpp).
    pG->Disp_flg = 0xFFFFFFFF & ~(0x1000 | 0x2000 | 0x10000);
    if (open) {
        re4dc_ui_movie_background(1);
    }
    alignas(8) static u8 storage[sizeof(Event)];
    memset(storage, 0, sizeof(storage));
    Event* e = (Event*) storage;
    e->funcMode = 1;
    e->NowCut = qte_cut;
    re4dc_fixture_state("qte", 1, -1);  // a padscript press can wait for the cut ("qte=1")
#if RE4DC_ROUTE_QTE_FRAMES
    qte_frames = RE4DC_ROUTE_QTE_FRAMES;  // test builds: hold the cut for a timed screenshot
#endif
    unsigned f = 0;
#if defined(RE4DC_ROUTE_QTE_CLOCK) && RE4DC_ROUTE_QTE_CLOCK
    // ROUTE_QTE_CLOCK: the r10b rope QTE (ROUTE_MOVIE_ACT_COUNT) counts its frames on the movie's picture clock, not per game
    // frame. The movie runs on the retrace clock (one picture per 2 fields, its sound too), so a game frame slower than that
    // let the movie end before the QTE's 285 frames did: its last picture stayed frozen under the "CUT" prompt (GitHub #66).
    // Frames the movie moved on in one game frame are not skipped (the event func sees every frame number once, e.g. frame
    // 100 starts the prompt); the A-press count still reads the pad once per game frame. At 30 fps nothing changes. The
    // log line says how long the QTE's game frames really took.
    const bool qclock = (flags & ROUTE_MOVIE_ACT_COUNT) != 0 && open;
    const unsigned ls_vi0 = re4dc_vi_retrace_count();
    unsigned ls_prev = ls_vi0, ls_slow = 0, ls_max = 0, ls_game = 0, ls_skipped = 0;
#endif
#if defined(RE4DC_DELLAGO_DIAG) && RE4DC_DELLAGO_DIAG
    // DELLAGO_DIAG (test only, lane dl66b, #66 "CUT" freeze): one line per 15 QTE game frames: the retrace count, the
    // movie's picture counters, how many fields each game frame took; RE4DC_QTE_BURN_US busy-waits per frame to stand in
    // for a slower console.
    unsigned dbg_prev_vi = re4dc_vi_retrace_count(), dbg_vi0 = dbg_prev_vi, dbg_held_f = 0, dbg_max_gap = 0;
    unsigned long long dbg_t0 = timer_us_gettime64();
#endif
    for (; f < qte_frames; ++f) {
#if defined(RE4DC_DELLAGO_DIAG) && RE4DC_DELLAGO_DIAG
        {
            unsigned k, shown, dropped, late, starved, v0; int held, pending;
            re4dc_movie_diag(&k, &shown, &dropped, &late, &starved, &held, &pending, &v0);
            const unsigned vi = re4dc_vi_retrace_count();
            if (vi - dbg_prev_vi > dbg_max_gap) dbg_max_gap = vi - dbg_prev_vi;
            dbg_prev_vi = vi;
            if (held && !dbg_held_f) { dbg_held_f = f; re4dc_log("dl66 qte: picture held (movie ended) at game frame %u vi+%u\n", f, vi - dbg_vi0); }
            if ((f % 15) == 0)
                re4dc_log("dl66 qte: f=%u vi+%u t+%ums k=%u shown=%u dropped=%u late=%u starved=%u held=%d pending=%d due=%d maxgap=%u presses=%d\n",
                          f, vi - dbg_vi0, (unsigned) ((timer_us_gettime64() - dbg_t0) / 1000), k, shown, dropped, late, starved, held,
                          pending, (int) (vi - (v0 + 2 * k)), dbg_max_gap, (int) e->actBtnCount);
#if defined(RE4DC_QTE_BURN_US) && RE4DC_QTE_BURN_US
            { const unsigned long long b0 = timer_us_gettime64(); while (timer_us_gettime64() - b0 < RE4DC_QTE_BURN_US) {} }
#endif
        }
#endif
#if defined(RE4DC_ROUTE_QTE_CLOCK) && RE4DC_ROUTE_QTE_CLOCK
        {
            const unsigned vi = re4dc_vi_retrace_count();
            if (ls_game && vi - ls_prev > 2) ++ls_slow;
            if (ls_game && vi - ls_prev > ls_max) ls_max = vi - ls_prev;
            ls_prev = vi;
            ++ls_game;
        }
#endif
        e->NowFrame = f;
        func(e);
#if defined(RE4DC_ROUTE_CH13) && RE4DC_ROUTE_CH13
        if (flags & ROUTE_MOVIE_ACT_COUNT) {
            e->ExecActBtn();  // Event::Run's prompt and A-press count (r10b s20, the rope)
        }
#endif
        if (e->StatusFlag & 0x4000) {
            break;  // CancelSet: the handler ends the cut (the QTE passed)
        }
        if (open) {
            const int s = re4dc_movie_step(0);
            if (s != RE4DC_MOVIE_RUNNING && s != RE4DC_MOVIE_EOF) {
                re4dc_log("route cutscene: id=%05x QTE picture ended (terminal %d) at frame %u\n", id, s, f);
            }
        }
        SceSleep(1);
#if defined(RE4DC_ROUTE_QTE_CLOCK) && RE4DC_ROUTE_QTE_CLOCK
        if (qclock) {
            const unsigned clk = re4dc_movie_clock();
            const unsigned want = clk > qte_picture ? clk - qte_picture : 0;   // the QTE frame the movie has reached
            while (f + 1 < want && f + 1 < qte_frames && !(e->StatusFlag & 0x4000)) {
                ++f;
                ++ls_skipped;
                e->NowFrame = f;
                func(e);   // a frame number the movie passed during a slow game frame: run it, no pad read
            }
        }
#endif
    }
#if defined(RE4DC_ROUTE_QTE_CLOCK) && RE4DC_ROUTE_QTE_CLOCK
    re4dc_log("route QTE: id=%05x clock=%d frames=%u game_frames=%u catch_up=%u fields=%u (30 fps = %u) slow_frames=%u max_gap_fields=%u\n", id,
              qclock ? 1 : 0, f, ls_game, ls_skipped, re4dc_vi_retrace_count() - ls_vi0, 2 * f, ls_slow, ls_max);
#endif
    re4dc_log("route QTE: id=%05x cut=%#x frames=%u/%u passed=%d room0=%08x picture=%s\n", id, qte_cut, f, qte_frames,
              (e->StatusFlag & 0x4000) != 0, pG->Room_flg[0], open ? "movie" : "none");
#if defined(RE4DC_ROUTE_CH13) && RE4DC_ROUTE_CH13
    if (flags & ROUTE_MOVIE_ACT_COUNT) {
        re4dc_log("route QTE: id=%05x act button %#x presses=%d\n", id, e->actBtnNo, e->actBtnCount);
    }
#endif
    re4dc_fixture_state("qte", 0, -1);
    re4dc_ui_movie_background(0);
    const int end = open ? re4dc_movie_end() : st;
    re4dc_weapon_heap4_movie_restore();
    re4dc_ps2_interior_movie_restore();
    re4dc_far_shell_movie_restore();
    re4dc_motion_pin_restore();
    pG->Disp_flg = disp;
#if defined(RE4DC_ROUTE_CH13) && RE4DC_ROUTE_CH13
    if (flags & ROUTE_MOVIE_ACT_COUNT) {
        // The end func reads the count from the cut's event (Event::ExeEndEvt calls it on the same event).
        routeEndEvent = e;
    }
#endif
    routeEnd(id, flags, func, end);
    return end == RE4DC_MOVIE_UNHANDLED ? RE4DC_MOVIE_ERROR : end;
}

int RouteMoviePlay(unsigned id, unsigned flags, RouteEvtFunc func, RouteMovieTick tick)
{
    if (!re4dc_movie_available(id)) {
        return RE4DC_MOVIE_UNHANDLED;
    }
    // Event::ExeBeginEvt: scenario event nesting, event-running status, begin func.
    SceEventStart(ROUTE_SCE_MODE(flags));
    BitOn(pG->Status_flg[2], 0x00080000);
    BitOn(pG->Status_flg[2], 0x00010000);
    BitOff(pG->Status_flg[3], 0x01000000);
    routeFunc(func, 0);
    pG->System_flg |= 0x400;
    if (flags & ROUTE_MOVIE_SND_EVENT) {
        SndEventInit();
    }
    // cSofdec::initWork display contract: the game is hidden while the picture
    // plays and Disp_flg is restored afterwards. Stop_flg stays exactly as the
    // source event left it, so enemy/NoSuspend timing matches a real event.
    const u32 disp = pG->Disp_flg;
    pG->Disp_flg = 0xFFFFFFFF;
    // The movie owns presentation until it ends (the task does not sleep, so no
    // game frame runs); skip is the event cancel key, Key bit 29 = PAD START.
#if RE4DC_MOVIE_WORLD_ARENA
    re4dc_movie_world_scope(id);
#endif
    int st = re4dc_movie_play(id, 0x1000, tick);
#if RE4DC_MOVIE_WORLD_ARENA
    re4dc_movie_world_scope(0);
#endif
    re4dc_weapon_heap4_movie_restore();
    re4dc_ps2_interior_movie_restore();
    re4dc_far_shell_movie_restore();
    re4dc_motion_pin_restore();
    pG->System_flg &= ~0x400;  // Event::Run releases the held picture after frame 0
    pG->Disp_flg = disp;
    if (st == RE4DC_MOVIE_UNHANDLED) {
        st = RE4DC_MOVIE_ERROR;  // media vanished after the check: effects still complete
    }
    if (st == RE4DC_MOVIE_SKIP) {
        // Event::RunEvtCancel: cancel marker, then the handler's cancel mode.
        pG->Status_flg[3] |= 0x01000000;
        routeFunc(func, 3);
    }
    // Event::ExeEndEvt, lasting part. No event player body existed, so the
    // player keeps its own position (the PS2 evds carry no pl0000 body).
    if (!(flags & ROUTE_MOVIE_KEEP_POSE)) {
        Vec pos = pPL->pos;
        Vec rot = pPL->ang;
        pPL->zeroPartsPosInit(&pos, &rot);
    }
    pG->Disp_flg &= ~0x800;
    routeFunc(func, 2);
    pG->System_flg |= 0x40;
    if (flags & ROUTE_MOVIE_SND_EVENT) {
        SndEventEnd();
    }
    BitOff(pG->Status_flg[2], 0x00080000);
    BitOff(pG->Status_flg[2], 0x00010000);
#if defined(RE4DC_ROUTE_CH21) && RE4DC_ROUTE_CH21
    if (flags & ROUTE_MOVIE_SCE_TRUE) {
        CamCtrl.Comeback(0);  // EvtReadExec's own Comeback (SceEventEnd(0) skips it after a mode-1 start)
    }
#endif
    SceEventEnd(0);
#if defined(RE4DC_MOTION_RESUME) && RE4DC_MOTION_RESUME
    re4dc_motion_movie_restore();
#endif
    re4dc_log("route cutscene: id=%05x terminal=%d skip_func=%d end_func=%d pose=%s scenario0=%08x system=%08x\n",
              id, st, st == RE4DC_MOVIE_SKIP && func != 0, func != 0,
              (flags & ROUTE_MOVIE_KEEP_POSE) ? "kept" : "zero-parts", pG->Scenario_flg[0], pG->System_flg);
    return st;
}
