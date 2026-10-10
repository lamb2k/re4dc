// D367 frame pacing: render skip with catch-up (PACE_CATCHUP, pace.mk; design-pacing DESIGN.md).
//
// The game runs one 30 Hz logic tick per frame-loop iteration and has no delta time, so without
// this a frame slower than 2 vblanks slows the whole game. Here logic keeps a 29.97 Hz clock on
// the vblank counter: tick k may not start before anchor + 2k vblanks (so an overrun is repaid by
// shorter waits later), and when the game is at least one tick behind the next iteration runs
// its complete logic tick with the draw skipped:
//   v1 (PACE_CATCHUP=1): ModelRender returns at entry, the native frame is not begun
//      (re4dc_ui_begin_skip: frame_ready=false, so no UI quad, effect sprite, ID quad or model
//      packet can be emitted), nothing is presented (the previous picture stays). Everything
//      else (TaskScheduler, all of Trans(), every other OT callback, pad, sound, fades,
//      messages, cinescope, iTask on the policy below) runs unchanged.
//   v2 (PACE_CATCHUP=2): the drop of image k is decided before Trans() of tick k: that Trans()
//      builds no model OT (no emTrans/objTrans -> ModelTrans) and iteration k+1 skips as above.
// Limits: at most PACE_CAP consecutive skips (default 1: 2 ticks per drawn frame); lag beyond the
// cap is dropped (slow motion, as today) and a lag over 0.5 s (load, movie, reset) re-anchors.
// Runtime mode (re4dc_pace_mode, refreshed every iteration, safe to change at any moment). Source:
// the RE4DCCFG pacing setting (quality.h re4dc_quality_pace: 0 build default, 1 Smooth, 2 Fast,
// 3 Off; set by the quality menu or quality.txt pace=N), else PACE_MODE; the test-build chord
// (pad.cpp) and PACE_TEST_TOGGLE_S override it for this boot without a VMU write:
//   Smooth  a skip only while the present-to-present gap stays <= 1/PACE_FLOOR_FPS (15 fps):
//           load beyond it degrades to slow motion instead of dropping more frames (default);
//   Fast    no floor: catch-up up to the cap;
//   Off     no pacing at all: today's loop and wait (slow motion under load; for A/B).
// It only changes which ticks draw: the logic tick is the same in every mode.
// Pacing runs only in in-room play (Rno0 3) with GetSystemVcnt()==2 and no movie, sub screen or
// held picture (System_flg 0x400); elsewhere the original vsync_cnt wait runs.
// The hang detector is untouched: main.cpp still zeroes vsync_cnt after every iteration.
#include "global.h"
#include "main.h"
#include "re4dc_platform.h"
#include <kos/timer.h>
#include <string.h>

#ifndef RE4DC_PACE_CATCHUP
#define RE4DC_PACE_CATCHUP 0
#endif
#ifndef RE4DC_PACE_TEST_TOGGLE_S
#define RE4DC_PACE_TEST_TOGGLE_S 0
#endif
#ifndef RE4DC_PACE_MODE
#define RE4DC_PACE_MODE 0
#endif
#ifndef RE4DC_PACE_CAP2_SPEED
#define RE4DC_PACE_CAP2_SPEED 0
#endif
#include "warp_late.h"
#ifndef RE4DC_PACE_VMU
#define RE4DC_PACE_VMU 0
#endif
#ifndef RE4DC_PACE_VMU_GPU
#define RE4DC_PACE_VMU_GPU 0
#endif
#if RE4DC_PACE_VMU
#include <dc/maple.h>
#include <dc/maple/vmu.h>
#include <dc/vmu_fb.h>
#include <stdio.h>
#if RE4DC_PACE_VMU_GPU
#include <arch/irq.h>
#endif
#endif

extern "C" u32 re4dc_vi_retrace_count(void);
extern "C" void* re4dc_ui_movie_texture() __attribute__((weak));   // ROUTE_MOVIES builds
extern "C" int re4dc_quality_pace(void) __attribute__((weak));      // QUALITY builds (quality.cpp)
#if RE4DC_PACE_CHECK
extern "C" unsigned re4dc_logic_trace_hash(void);                  // logic_trace.cpp
#endif
#if defined(RE4DC_EFFECT_PS2_TOGGLE) && RE4DC_EFFECT_PS2_TOGGLE
extern "C" const char* re4dc_ps2fx_label(void);
#if defined(RE4DC_LOOK_TOGGLE)
extern "C" const char* re4dc_look_label(void);  // native_static.cpp (post30.mk LOOK_TOGGLE): the look preset
#define re4dc_ps2fx_label re4dc_look_label
#endif                    // esp_sub.cpp (effects30.mk EFFECT_PS2_TOGGLE)
#endif

enum { PACE_SMOOTH = 0, PACE_FAST = 1, PACE_OFF = 2 };
// Smooth's floor; PACE_FLOOR_FPS=0 makes Fast the default mode.
constexpr unsigned kFloorFps = RE4DC_PACE_FLOOR_FPS ? RE4DC_PACE_FLOOR_FPS : 15;

extern "C" {
int re4dc_pace_skipping;     // this iteration draws nothing (ModelRender, Render_before/_swap)
int re4dc_pace_drop_models;  // v2: this Trans() builds no model OT (its image is dropped)
int re4dc_pace_mode = RE4DC_PACE_MODE;   // pace.mk PACE_MODE (build default before any setting)
void re4dc_pace_cycle_mode(void);
}

namespace {
constexpr unsigned kVbUs = 16683;          // NTSC field (59.94 Hz)
constexpr int kReanchorVb = 30;            // > 0.5 s behind: a load / movie / reset, not load
constexpr int kKeepVb = 2 * RE4DC_PACE_CAP;  // lag kept after a cap drop (repaid by skips)
constexpr const char* kModeName[3] = {"smooth", "fast", "off"};

bool ok_now;                // this iteration may pace (context, vcnt, mode)
bool active;                // the clock runs (the previous iteration paced too)
int vcnt_prev;
u32 anchor, ticks;          // tick k is due at anchor + 2k vblanks
unsigned run;               // consecutive skipped iterations up to this one
bool drop_next;             // v2: the next iteration skips (its image was dropped)
unsigned long long iter_us, decide_us, last_present_us;
unsigned draw_ema, skip_ema, rest_ema;   // us: drawn / skipped iteration, decide -> work end
unsigned render_ema;        // us: iteration start -> end of Render() on drawn iterations
unsigned since_skip;        // iterations since the last skip (skip_ema is forgotten after 32)
unsigned itask_idle;
unsigned force_idx;
u32 rng = RE4DC_PACE_SEED ? RE4DC_PACE_SEED : 1;
u32 note_until;             // retrace count until which the mode note shows (test builds)
int override_mode = -1;     // chord / test toggle: this boot only (-1: the stored setting)

// Telemetry window.
u32 w_vb0;
unsigned w_ticks, w_drawn, w_skip, w_lagmax, w_dropped, w_reanchor, w_floor, w_cap, w_ctx, w_starve;
unsigned hud_speed, hud_fps10;
#if RE4DC_PACE_CHECK
unsigned chk_hash, chk_n, chk_fail;
#endif

unsigned ema(unsigned e, unsigned v) { return e ? e - (e >> 3) + (v >> 3) : v; }

void burn(unsigned us)
{
    const unsigned long long until = timer_us_gettime64() + us;
    while (timer_us_gettime64() < until) {
    }
}

// Full-screen UI, movies, loads and doors keep today's loop: in-room play only.
bool context_ok()
{
    if (!pG || pG->Rno0 != 3) return false;
    if (pG->System_flg & (0x400 | 0x100000)) return false;   // held picture / room change
    if (pG->Status_flg[2] & 0x04000000) return false;         // sub screen requested or open
    if (re4dc_ui_movie_texture && re4dc_ui_movie_texture()) return false;
    return true;
}

// PACE_FORCE: the pattern is a pure function of the eligible-tick index.
int forced()
{
    const unsigned i = force_idx++;
#if RE4DC_PACE_FORCE == 1
    (void) i;
    return 1;
#elif RE4DC_PACE_FORCE == -2
    return i % 3 != 0;   // PACE_FORCE=T: one image drawn, two dropped (the PACE_CAP=2 saturated pattern)
#elif RE4DC_PACE_FORCE < 0
    (void) i;
    rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5;
    return (rng >> 16) & 1;
#else
    return i % RE4DC_PACE_FORCE == RE4DC_PACE_FORCE - 1;
#endif
}

// Smooth: a skip is allowed when the gap between two presents stays within the floor. `since` is
// what has already elapsed since the last present (or will have, for a v2 decision).
bool floor_blocks(unsigned since)
{
    if (re4dc_pace_mode != PACE_SMOOTH) return false;
    // A skipped iteration costs about a drawn one minus its Render(): the estimate until skips
    // are measured (and again after 32 iterations without one, so a stale cost cannot lock out).
    const unsigned skip = skip_ema ? skip_ema : (draw_ema > render_ema ? draw_ema - render_ema : 0);
    return since + skip + draw_ema > 1000000U / kFloorFps;
}

// Behind by at least one tick (`lag` vblanks): skip unless the cap or the floor blocks it.
int want_skip(int lag, unsigned since)
{
    if (lag < 2) return 0;
    if (run >= RE4DC_PACE_CAP) { ++w_cap; return 0; }
#if RE4DC_PACE_CAP2_SPEED
    // PACE_CAP2_SPEED=N (pace.mk): a second (or later) consecutive skip only while one skip per drawn image would
    // leave the game below N% speed: 2 ticks (2 x 2 fields) per drawn + skipped pair, draw_ema + skip_ema of wall time.
    if (run >= 1) {
        const unsigned skip = skip_ema ? skip_ema : (draw_ema > render_ema ? draw_ema - render_ema : 0);
        if ((unsigned long long) (draw_ema + skip) * RE4DC_PACE_CAP2_SPEED <= 4ULL * kVbUs * 100) { ++w_cap; return 0; }
    }
#endif
    if (floor_blocks(since)) { ++w_floor; return 0; }
    return 1;
}

void report(u32 now)
{
    const u32 dvb = now - w_vb0;
    if (!dvb) return;
    const unsigned speed = unsigned(w_ticks * 200ULL * 10 / dvb);          // 0.1 %
    const unsigned fps10 = unsigned(w_drawn * 59940ULL / 100 / dvb);        // 0.1 fps
    hud_speed = (speed + 5) / 10; hud_fps10 = fps10;
    re4dc_log("PACE t=%u win=%u drawn=%u skip=%u fps=%u.%u speed=%u.%u lag_max=%u dropped_vb=%u slow=%u "
              "reanchor=%u floor_block=%u cap_block=%u ctx_block=%u draw_us=%u skip_us=%u itask_starve=%u mode=%s\n",
              pG ? (unsigned) pG->Frame_cnt : 0, w_ticks, w_drawn, w_skip, fps10 / 10, fps10 % 10, speed / 10,
              speed % 10, w_lagmax, w_dropped, w_dropped / 2, w_reanchor, w_floor, w_cap, w_ctx, draw_ema,
              skip_ema, w_starve, kModeName[re4dc_pace_mode % 3]);
#if RE4DC_PACE_CHECK
    re4dc_log("PACE pacechk=%u/%u\n", chk_n, chk_fail);
#endif
    w_vb0 = now;
    w_ticks = w_drawn = w_skip = w_lagmax = w_dropped = w_reanchor = w_floor = w_cap = w_ctx = w_starve = 0;
}

#if RE4DC_PACE_VMU
// PACE_VMU: the speed page on the VMU LCD, one second per window (60 vblanks), console tests
// without a serial link. Reads the window counters only; the write is queued (maple, next vblank)
// and retried on the following iterations while the maple frame is busy.
u32 v_vb0;
unsigned v_ticks, v_drawn, v_tries;
unsigned long long v_cost_us;
vmufb_t v_lcd;

#if RE4DC_PACE_VMU_GPU
// PACE_VMU_GPU: the graphics chip's (PVR) render time per scene: the interval of KOS's rnd_last_time statistic, taken
// for every render. KOS (pvr_irq.c) stamps PVR_SYNC_RNDSTART in pvr_render_lists right after pvr_begin_queued_render
// wrote ISP_START, and PVR_SYNC_RNDDONE in the TSP render-done interrupt (ASIC_EVT_PVR_RENDERDONE_TSP). KOS starts a
// render only once the scene's lists are all in the TA, the previous render is done and the previous picture was
// flipped or discarded, so no wait for the previous render (nor for a flip or a present decision) is inside the
// interval; the latency of the render-done interrupt is. pvr_sync_stats is wrapped at link time (pace.mk) and the
// same events are stamped right after KOS's own (integers only, interrupt context), so each render counts once in
// the window in which its render-done interrupt arrives. (Sampling pvr_get_stats once per iteration and counting
// changed values missed renders whenever two in a row had the same length: Flycast's fixed ~7.5 ms showed 27 renders
// for 30 drawn frames. The hwcal disc, 2026-10-04, read the statistic once per tick: P50 over 600 ticks, each tick
// repeating the last render.) The log also gets two intervals that stay off the LCD: wait = the scene's last list in
// (PVR_SYNC_REGDONE) to its render start, the time a finished scene queued behind the previous render and its flip
// (~0 while the CPU is the bottleneck); reg = pvr_scene_begin to the last list in (KOS reg_last_time: here the scene
// opens at the frame's first PVR packet and closes at Render_swap, so it is mostly CPU time, not the TA's own).
// pvr_sync_stats events (KOS kernel/arch/dreamcast/hardware/pvr/pvr_internal.h; the toolchain is pinned).
constexpr int kSyncRegStart = 4, kSyncRegDone = 5, kSyncRndStart = 6, kSyncRndDone = 7;
struct GpuAcc {
    unsigned long long rnd_sum, rnd_max, wait_sum, wait_max, reg_sum;   // ns
    unsigned rnd_n, wait_n, reg_n;
};
GpuAcc g_gpu;                                      // interrupt side; vmu_window takes it with interrupts off
unsigned long long g_reg_t0, g_regdone_t, g_rnd_t0;
}  // namespace

extern "C" void __real_pvr_sync_stats(int event);
extern "C" void __wrap_pvr_sync_stats(int event)
{
    __real_pvr_sync_stats(event);                  // KOS's own statistics first, unchanged
    if (event < kSyncRegStart || event > kSyncRndDone) return;
    const auto irq = irq_disable();                // REGSTART comes from pvr_scene_begin (thread context)
    const unsigned long long t = timer_ns_gettime64();
    switch (event) {
    case kSyncRegStart:
        g_reg_t0 = t;
        break;
    case kSyncRegDone:
        if (g_reg_t0) {
            g_gpu.reg_sum += t - g_reg_t0;
            ++g_gpu.reg_n;
            g_reg_t0 = 0;
        }
        g_regdone_t = t;
        break;
    case kSyncRndStart:
        if (g_regdone_t) {
            const unsigned long long w = t - g_regdone_t;
            g_gpu.wait_sum += w;
            ++g_gpu.wait_n;
            if (w > g_gpu.wait_max) g_gpu.wait_max = w;
            g_regdone_t = 0;
        }
        g_rnd_t0 = t;
        break;
    default:                                       // kSyncRndDone
        if (g_rnd_t0) {
            const unsigned long long d = t - g_rnd_t0;
            g_gpu.rnd_sum += d;
            ++g_gpu.rnd_n;
            if (d > g_gpu.rnd_max) g_gpu.rnd_max = d;
            g_rnd_t0 = 0;
        }
        break;
    }
    irq_restore(irq);
}

namespace {
#endif

void vmu_try()
{
    maple_device_t* dev = maple_enum_type(0, MAPLE_FUNC_LCD);
    if (!dev) { v_tries = 0; return; }
    // vmufb_present's orientation rule (dbgslot_bridge.cpp), keeping the return code.
    maple_device_t* cont = maple_enum_dev(dev->port, 0);
    const int rc = (cont && (cont->info.functions & MAPLE_FUNC_CONTROLLER) &&
                    cont->info.connector_direction != dev->info.connector_direction)
                       ? vmu_draw_lcd(dev, v_lcd.data)
                       : vmu_draw_lcd_rotated(dev, v_lcd.data);
    v_tries = rc == MAPLE_EAGAIN ? v_tries - 1 : 0;
}

void vmu_window(unsigned cost, u32 now)
{
    if (v_tries) vmu_try();
    if (!v_vb0) { v_vb0 = now; return; }
    ++v_ticks; v_cost_us += cost;
    const u32 dvb = now - v_vb0;
    if (dvb < 60) return;
    const unsigned fps10 = unsigned(v_drawn * 59940ULL / 100 / dvb);   // 0.1 fps
    const unsigned speed = unsigned((v_ticks * 2000ULL / dvb + 5) / 10);   // %
    // CPU: work per tick (before the vblank wait) as % of a 30 Hz tick (2 NTSC fields, 33,367 us); above 100 the
    // console is saturated even when it skips drawing (user's console readings, 2026-10-04).
    const unsigned cpu = unsigned((v_cost_us * 100ULL / v_ticks + 16683) / 33367);
    char text[64];
#if RE4DC_PACE_VMU_GPU
    GpuAcc a;   // the renders whose render-done interrupt arrived in this window
    {
        const auto irq = irq_disable();
        a = g_gpu;
        g_gpu = GpuAcc{};
        irq_restore(irq);
    }
    // GPU <mean>/<max>: ms per render (rounded, capped at 999) over the renders completed in this window.
    char gpu[16];
    if (a.rnd_n) {
        const unsigned long long mean = (a.rnd_sum / a.rnd_n + 500000) / 1000000, peak = (a.rnd_max + 500000) / 1000000;
#if defined(RE4DC_EFFECT_PS2_TOGGLE) && RE4DC_EFFECT_PS2_TOGGLE
        // EFFECT_PS2_TOGGLE: the effect look (GC / GF / PH / PS) after the GPU numbers
        snprintf(gpu, sizeof(gpu), "GPU %u/%u %s", unsigned(mean < 999 ? mean : 999), unsigned(peak < 999 ? peak : 999),
                 re4dc_ps2fx_label());
    } else {
        snprintf(gpu, sizeof(gpu), "GPU - %s", re4dc_ps2fx_label());
    }
#else
        snprintf(gpu, sizeof(gpu), "GPU %u/%u", unsigned(mean < 999 ? mean : 999), unsigned(peak < 999 ? peak : 999));
    } else {
        snprintf(gpu, sizeof(gpu), "GPU -");
    }
#endif
    snprintf(text, sizeof(text), "FPS %u.%u\nSPD %u%%\nCPU %u%%\n%s\nMODE %s", fps10 / 10, fps10 % 10, speed, cpu,
             gpu, kModeName[re4dc_pace_mode % 3]);
    // busy: the window's summed render time as % of its wall time (dvb fields of 16,683 us)
    const unsigned busy = unsigned(a.rnd_sum / (dvb * 166830ULL));
    char page[sizeof(text)];
    unsigned i = 0;
    for (; text[i]; ++i) page[i] = text[i] == '\n' ? '|' : text[i];
    page[i] = 0;
    re4dc_log("PACE vmu t=%u win_vb=%u drawn=%u gpu_n=%u gpu_avg_us=%u gpu_max_us=%u gpu_busy=%u%% wait_n=%u "
              "wait_avg_us=%u wait_max_us=%u reg_n=%u reg_avg_us=%u page=%s\n",
              pG ? (unsigned) pG->Frame_cnt : 0, (unsigned) dvb, v_drawn, a.rnd_n,
              a.rnd_n ? unsigned(a.rnd_sum / a.rnd_n / 1000) : 0, unsigned(a.rnd_max / 1000), busy, a.wait_n,
              a.wait_n ? unsigned(a.wait_sum / a.wait_n / 1000) : 0, unsigned(a.wait_max / 1000), a.reg_n,
              a.reg_n ? unsigned(a.reg_sum / a.reg_n / 1000) : 0, page);
#else
#if defined(RE4DC_EFFECT_PS2_TOGGLE) && RE4DC_EFFECT_PS2_TOGGLE
    snprintf(text, sizeof(text), "FPS %u.%u\nSPD %u%%\nCPU %u%% %s\nMODE %s", fps10 / 10, fps10 % 10, speed, cpu,
             re4dc_ps2fx_label(), kModeName[re4dc_pace_mode % 3]);
#else
    snprintf(text, sizeof(text), "FPS %u.%u\nSPD %u%%\nCPU %u%%\nMODE %s", fps10 / 10, fps10 % 10, speed, cpu,
             kModeName[re4dc_pace_mode % 3]);
#endif
#endif
    vmufb_clear(&v_lcd);
    vmufb_print_string(&v_lcd, nullptr, text);
    v_tries = 30;
    vmu_try();
    v_vb0 = now; v_ticks = v_drawn = 0; v_cost_us = 0;
}
#endif

#if RE4DC_PACE_TEST_TOGGLE_S
// Test knob: cycle the mode every N seconds of wall time (the STRICT toggle gate).
void test_toggle(u32 now)
{
    static u32 next;
    if (!next) next = now + RE4DC_PACE_TEST_TOGGLE_S * 60;
    if ((int) (now - next) >= 0) {
        next = now + RE4DC_PACE_TEST_TOGGLE_S * 60;
        re4dc_pace_cycle_mode();
    }
}
#endif
}  // namespace

// Mode (PACE_SMOOTH/FAST/OFF): any moment. A pending v2 drop is still honoured by the next
// iteration (its model OT does not exist), and a clock that stopped re-anchors when it resumes.
static void refresh_mode(const char* why)
{
    int mode = override_mode;
    if (mode < 0) {
        const int stored = re4dc_quality_pace ? re4dc_quality_pace() : 0;
        mode = stored ? stored - 1 : RE4DC_PACE_MODE;
    }
    if (mode != re4dc_pace_mode)
        re4dc_log("PACE mode=%s (%s) t=%u\n", kModeName[mode % 3], why, pG ? (unsigned) pG->Frame_cnt : 0);
    re4dc_pace_mode = mode;
}
// This-boot override (chord, test toggle); the stored setting belongs to quality.cpp.
extern "C" void re4dc_pace_set_mode(int mode, const char* why)
{
    if (mode < PACE_SMOOTH || mode > PACE_OFF) return;
    override_mode = mode;
    refresh_mode(why ? why : "-");
}
extern "C" int re4dc_pace_get_mode(void) { refresh_mode("setting"); return re4dc_pace_mode; }
// Test builds: the live chord (pad.cpp) cycles Smooth -> Fast -> Off and shows a note for 2 s.
extern "C" void re4dc_pace_cycle_mode(void)
{
    re4dc_pace_set_mode((re4dc_pace_mode + 1) % 3, "cycle");
    note_until = re4dc_vi_retrace_count() + 120;
}
// The note (native_ui.cpp, test builds): 1 while it shows; *mode = the current mode.
extern "C" int re4dc_pace_note(int* mode)
{
    *mode = re4dc_pace_mode;
    return note_until && (int) (note_until - re4dc_vi_retrace_count()) > 0;
}

extern "C" void re4dc_pace_reset(void)
{
    active = false; ok_now = false; run = 0; drop_next = false;
    re4dc_pace_skipping = 0; re4dc_pace_drop_models = 0;
}

// Top of the iteration (after the trace point): decides whether this iteration draws.
extern "C" void re4dc_pace_begin(void)
{
    const u32 now = re4dc_vi_retrace_count();
    iter_us = timer_us_gettime64();
    decide_us = iter_us;
    if (!w_vb0) w_vb0 = now;
#if defined(RE4DC_DBG_WARP) && RE4DC_DBG_WARP
    if (RE4DC_WARP_LATE(RE4DC_LATE_NODRAW)) override_mode = PACE_FAST;   // test arms only (warp_late.h)
#endif
    refresh_mode("setting");
#if RE4DC_PACE_TEST_TOGGLE_S
    test_toggle(now);
#endif
    const int vcnt = GetSystemVcnt();
    ok_now = vcnt == 2 && re4dc_pace_mode != PACE_OFF && context_ok();
    int skip = 0;
    if (!ok_now) {
        active = false;
        ++w_ctx;
    } else {
        if (!active || vcnt != vcnt_prev) {
            anchor = now; ticks = 0; active = true;
        }
        int lag = (int) (now - (anchor + 2 * ticks));
        if (lag > kReanchorVb) {
            ++w_reanchor; anchor = now - 2 * ticks; lag = 0;
        } else if (lag > 2 * (RE4DC_PACE_CAP + 1)) {
            w_dropped += lag - kKeepVb; anchor += lag - kKeepVb; lag = kKeepVb;
        }
        if ((unsigned) lag > w_lagmax) w_lagmax = lag;
#if RE4DC_PACE_CATCHUP == 1
#if RE4DC_PACE_FORCE
        skip = forced();
#else
        skip = want_skip(lag, unsigned(iter_us - last_present_us));
#endif
#endif
    }
    vcnt_prev = vcnt;
#if RE4DC_PACE_CATCHUP >= 2
    // The image this iteration would draw was dropped before its Trans(): no model OT exists,
    // so the iteration skips whatever the context or the mode says now.
    skip = drop_next;
    drop_next = false;
#endif
    run = skip ? run + 1 : 0;
    re4dc_pace_skipping = skip;
    re4dc_pace_drop_models = 0;
}

// v2: before Trans() of tick k, decides whether image k (drawn by iteration k+1) is dropped.
extern "C" void re4dc_pace_decide_image(void)
{
#if RE4DC_PACE_CATCHUP >= 2
    const unsigned long long us = timer_us_gettime64();
    decide_us = us;
    int drop = 0;
    if (ok_now && active && re4dc_pace_mode != PACE_OFF && context_ok()) {
#if RE4DC_PACE_FORCE
        drop = forced();
#else
        // Predicted lag at the start of iteration k+1 (due at anchor + 2(ticks+1)).
        const u32 now = re4dc_vi_retrace_count();
        const int lag = (int) (now - (anchor + 2 * (ticks + 1))) + int(rest_ema / kVbUs);
        const unsigned since = re4dc_pace_skipping ? unsigned(us - last_present_us) + rest_ema : 0;
        drop = want_skip(lag, since);
#endif
    }
    drop_next = drop;
    re4dc_pace_drop_models = drop;
#endif
}

// iTaskScheduler policy: drawn iterations run it as today; skipped ones do not (its time up to
// the vblank would be paid in game speed) unless it has not run for 4 iterations. FORCE: always.
extern "C" int re4dc_pace_itask(void)
{
#if RE4DC_PACE_FORCE
    return 1;
#else
    if (!re4dc_pace_skipping) { itask_idle = 0; return 1; }
    if (++itask_idle >= 4) { itask_idle = 0; ++w_starve; return 1; }
    return 0;
#endif
}

// End of the iteration's work (after Render_swap): 1 when this waited on the anchor clock, 0 when
// the caller must run the original vsync_cnt wait (pacing inactive).
extern "C" int re4dc_pace_end(void)
{
    const unsigned long long us = timer_us_gettime64();
    const unsigned cost = unsigned(us - iter_us);
    if (re4dc_pace_skipping) {
        skip_ema = ema(skip_ema, cost); ++w_skip; since_skip = 0;
    } else {
        draw_ema = ema(draw_ema, cost); ++w_drawn; last_present_us = us;
#if RE4DC_PACE_VMU
        ++v_drawn;
#endif
        if (++since_skip > 32) skip_ema = 0;
    }
#if RE4DC_PACE_CATCHUP >= 2
    rest_ema = ema(rest_ema, unsigned(us - decide_us));
#endif
    ++w_ticks;
#if RE4DC_PACE_VMU
    vmu_window(cost, re4dc_vi_retrace_count());
#endif
    int waited = 0;
    if (active) {
        ++ticks;
        const u32 due = anchor + 2 * ticks;
        while ((int) (re4dc_vi_retrace_count() - due) < 0) {
        }
        waited = 1;
    }
    re4dc_pace_skipping = 0;
    re4dc_pace_drop_models = 0;
    if (w_ticks >= RE4DC_PACE_LOG) report(re4dc_vi_retrace_count());
    return waited;
}

// After Render() (main.cpp): the draw-cost estimate, and the Flycast speed check's emulated load
// on drawn iterations (the skippable half; PACE_TEST_DRAW_US).
extern "C" void re4dc_pace_test_draw(void)
{
    if (re4dc_pace_skipping) return;
#if RE4DC_PACE_TEST_DRAW_US
    burn(RE4DC_PACE_TEST_DRAW_US);
#endif
    render_ema = ema(render_ema, unsigned(timer_us_gettime64() - iter_us));
}
extern "C" void re4dc_pace_test_tick(void)
{
#if RE4DC_PACE_TEST_TICK_US
    burn(RE4DC_PACE_TEST_TICK_US);
#endif
}

// PERF_HUD row: game speed (%) and drawn fps (0.1) of the last telemetry window.
extern "C" int re4dc_pace_hud(unsigned v[2])
{
    v[0] = hud_speed; v[1] = hud_fps10;
    return 1;
}

#if RE4DC_PACE_CHECK
// PACE_CHECK=2: a dropped image still runs ModelTrans between these two calls; every logic-trace
// field must be unchanged by it.
extern "C" void re4dc_pace_check(int phase)
{
    if (!phase) { chk_hash = re4dc_logic_trace_hash(); return; }
    ++chk_n;
    if (re4dc_logic_trace_hash() != chk_hash) {
        ++chk_fail;
        re4dc_log("PACE check: ModelTrans changed logic state at t=%u\n", pG ? (unsigned) pG->Frame_cnt : 0);
    }
}
#endif
