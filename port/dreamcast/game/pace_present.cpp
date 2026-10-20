// D367 pacing presentation (pace.mk PACE_STEADY / PACE_HOLD_LOG; lane pace20, 2026-10-20). Compiled only with one of
// them; native_ui.cpp calls the hooks from present_submit / present_fence (PVR_PIPELINE=2, KOS manual flip).
//
// PACE_STEADY: in the "Steady" pacing mode each presented picture is held for a constant number of TV fields
// (pace.cpp re4dc_pace_steady_hold: 2, 3 or 4, chosen from recent work with hysteresis). A picture whose scene is
// finished early is not handed to KOS at once: its present decision is deferred and released by a vblank handler one
// field before its target field (last flip + hold), so the flip lands on the target. A late picture flips as soon as it
// can and the next target counts from that flip. Discards, movies, and every other mode present as before.
// One deferred picture at most: a second present waits (re4dc_steady_wait) until the first was handed over.
//
// PACE_HOLD_LOG: telemetry in every mode (bench builds). Per picture: the fields it was held (flip to flip), the logic
// ticks it covers, the ready deadline (target field), CPU work end (scene finish) and the actual flip. A histogram line
// per pace report window; =2 also one line per picture.
#include "global.h"
#include "re4dc_platform.h"
#include <kos.h>
#include <dc/vblank.h>
#include <kos/timer.h>

#ifndef RE4DC_PACE_STEADY
#define RE4DC_PACE_STEADY 0
#endif
#ifndef RE4DC_PACE_HOLD_LOG
#define RE4DC_PACE_HOLD_LOG 0
#endif

extern "C" u32 re4dc_vi_retrace_count(void);
extern "C" int re4dc_pace_steady_hold(void);   // pace.cpp: 0 unless Steady is pacing now
extern "C" unsigned re4dc_pace_tick_total(void); // pace.cpp: logic ticks run under the pacing clock

namespace {
volatile int st_deferred;          // a present decision waits for its target field
volatile u32 st_target;            // field (retrace count) the deferred picture should flip on
volatile int watch;                // a present decision was handed to KOS and has not flipped yet
volatile u32 last_flip_vb;         // field of the last flip
volatile u32 flip_n;               // flips seen
int handler_id = -1;
unsigned releases_late, releases_on_time, waits;
unsigned long long wait_us;

// Hold telemetry (IRQ side writes, game side reads and clears).
constexpr int kHoldBins = 8;       // 1..6 fields, 7 = 7 or more, 0 unused
volatile unsigned hold_hist[kHoldBins];
volatile unsigned long long lat_sum_us; // scene finish -> flip
volatile unsigned lat_n, lat_max_us;
volatile unsigned long long submit_us_v; // scene finish of the picture in flight
#if RE4DC_PACE_HOLD_LOG >= 2
struct Pic { u32 submit_vb, target_vb, flip_vb, ticks; unsigned long long submit_us, flip_us; };
volatile Pic cur, done;
volatile int done_ready;
#endif

void on_flip(u32 now)
{
    const unsigned long long t = timer_us_gettime64();
    if (flip_n) {
        u32 h = now - last_flip_vb;
        if (h >= kHoldBins) h = kHoldBins - 1;
        ++hold_hist[h];
    }
    ++flip_n;
    last_flip_vb = now;
    if (submit_us_v) {
        const unsigned d = unsigned(t - submit_us_v);
        lat_sum_us += d; ++lat_n;
        if (d > lat_max_us) lat_max_us = d;
        submit_us_v = 0;
    }
#if RE4DC_PACE_HOLD_LOG >= 2
    cur.flip_vb = now; cur.flip_us = t;
    done.submit_vb = cur.submit_vb; done.target_vb = cur.target_vb; done.flip_vb = cur.flip_vb;
    done.ticks = cur.ticks; done.submit_us = cur.submit_us; done.flip_us = cur.flip_us;
    done_ready = 1;
#endif
}

// Runs after KOS's own vblank handler (added later), so a flip KOS made in this vblank is already visible, and a
// decision released here flips at the next vblank.
void vbl(uint32_t, void*)
{
    const u32 now = re4dc_vi_retrace_count();
    if (watch && !pvr_present_pending()) {
        watch = 0;
        on_flip(now);
    }
    if (st_deferred && (int) (now + 1 - st_target) >= 0) {
        if (pvr_present_async(true) == 0) {
            st_deferred = 0;
            watch = 1;
            if (now + 1 == st_target) ++releases_on_time; else ++releases_late;
        }
    }
}

void ensure_handler()
{
    if (handler_id < 0) handler_id = vblank_handler_add(vbl, nullptr);
}
}  // namespace

extern "C" {

// present_fence (game thread): a deferred picture counts as pending; wait until it was handed to KOS.
void re4dc_steady_wait(void)
{
    if (!st_deferred) return;
    const unsigned long long t0 = timer_us_gettime64();
    while (st_deferred) thd_pass();
    ++waits; wait_us += timer_us_gettime64() - t0;
}

int re4dc_steady_pending(void) { return st_deferred; }

// present_submit, before pvr_present_async. Returns 1 when the present decision was deferred (the caller skips it).
int re4dc_steady_present(int present)
{
    ensure_handler();
    re4dc_steady_wait();                              // one deferred picture at most; a discard follows it too
    if (!present) return 0;
    const u32 now = re4dc_vi_retrace_count();
    const unsigned long long t = timer_us_gettime64();
    submit_us_v = t;
#if RE4DC_PACE_HOLD_LOG >= 2
    if (done_ready) {
        done_ready = 0;
        re4dc_log("PACE pic sub=%u tgt=%u flip=%u ticks=%u lat_us=%u\n", (unsigned) done.submit_vb,
                  (unsigned) done.target_vb, (unsigned) done.flip_vb, (unsigned) done.ticks,
                  unsigned(done.flip_us - done.submit_us));
    }
    cur.submit_vb = now; cur.submit_us = t; cur.target_vb = now + 1; cur.ticks = re4dc_pace_tick_total();
#endif
#if RE4DC_PACE_STEADY
    const int hold = re4dc_pace_steady_hold();
    if (hold && flip_n) {
        // The previous picture flips on its own target (still pending) or already did.
        const u32 base = watch ? st_target : last_flip_vb;
        const u32 target = base + (u32) hold;
#if RE4DC_PACE_HOLD_LOG >= 2
        cur.target_vb = target;
#endif
        if ((int) (now + 1 - target) < 0) {
            st_target = target;
            st_deferred = 1;                          // released by vbl() at field target - 1
            return 1;
        }
        st_target = now + 1;                          // late: present now, the next target counts from this flip
        ++releases_late;
    } else {
        st_target = now + 1;
    }
#endif
    return 0;
}

// present_submit, after a successful pvr_present_async(present) by the game thread.
void re4dc_present_posted(int present)
{
    if (present) watch = 1;
}

// pace.cpp report(): one histogram line per telemetry window.
void re4dc_present_hold_report(void)
{
    unsigned h[kHoldBins];
    unsigned long long ls;
    unsigned ln, lm;
    {
        const int irq = irq_disable();
        for (int i = 0; i < kHoldBins; ++i) { h[i] = hold_hist[i]; hold_hist[i] = 0; }
        ls = lat_sum_us; ln = lat_n; lm = lat_max_us;
        lat_sum_us = 0; lat_n = 0; lat_max_us = 0;
        irq_restore(irq);
    }
    re4dc_log("PACE hold h1=%u h2=%u h3=%u h4=%u h5=%u h6=%u h7p=%u lat_avg_us=%u lat_max_us=%u steady_late=%u "
              "steady_on_time=%u steady_waits=%u steady_wait_us=%u\n",
              h[1], h[2], h[3], h[4], h[5], h[6], h[7], ln ? unsigned(ls / ln) : 0, lm, releases_late,
              releases_on_time, waits, unsigned(wait_us));
    releases_late = releases_on_time = waits = 0; wait_us = 0;
}

}  // extern "C"
