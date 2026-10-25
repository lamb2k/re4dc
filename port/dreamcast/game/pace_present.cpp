// D367 pacing presentation (pace.mk PACE_STEADY / PACE_HOLD_LOG; lane pace20, 2026-10-20). Compiled only with one of
// them; native_ui.cpp calls the hooks from present_submit / present_fence (PVR_PIPELINE=2, KOS manual flip).
//
// PACE_STEADY: in the "Steady" pacing mode each presented picture is held for a constant number of TV fields
// (pace.cpp re4dc_pace_steady_hold: 2, 3 or 4, chosen from recent work with hysteresis). A finished picture is not handed
// to KOS at once: its present decision joins a queue (two pictures deep) and a vblank handler releases it one field
// before its target field (the previous picture's target + hold), so the flip lands on the target. A late picture flips
// as soon as it can and the next target counts from it. The game thread waits only when the queue is full (a third
// finished picture) or at a fence (VRAM, single bank, discard), and that wait is not counted as work (pace.cpp).
// Discards, movies and every other mode present as before.
//
// PACE_HOLD_LOG: telemetry in every mode (bench builds). Per picture: the fields it was held (flip to flip), the logic
// ticks it covers, the ready deadline (target field), CPU work end (scene finish) and the actual flip. A histogram line
// per pace report window; =2 also one "PACE pic" line per picture.
#include "global.h"
#include "re4dc_platform.h"
#include <kos.h>
#include <dc/vblank.h>
#include <kos/timer.h>
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
#include "world_census24.h"
#endif

#ifndef RE4DC_PACE_STEADY
#define RE4DC_PACE_STEADY 0
#endif
#ifndef RE4DC_PACE_HOLD_LOG
#define RE4DC_PACE_HOLD_LOG 0
#endif

extern "C" u32 re4dc_vi_retrace_count(void);
extern "C" int re4dc_pace_steady_hold(void);     // pace.cpp: 0 unless Steady is pacing now
extern "C" unsigned re4dc_pace_tick_total(void); // pace.cpp: logic ticks run under the pacing clock

namespace {
// Steady queue (game thread pushes with interrupts off, the vblank handler pops).
constexpr unsigned kQ = 2;
volatile u32 q_target[kQ];
volatile unsigned q_head, q_n;
volatile u32 last_target;          // target of the picture scheduled last (queued or handed over)
volatile int watch;                // a present decision was handed to KOS and has not flipped yet
volatile u32 last_flip_vb;         // field of the last flip
volatile u32 flip_n;               // flips seen
int handler_id = -1;
volatile unsigned releases_late, releases_on_time;
constexpr unsigned kPhaseRun = 8;
unsigned early_run, rephase;
volatile unsigned late_cool;     // pictures to go without a rephase after one flipped later than its target
volatile unsigned cool_len = 64;   // doubles on every late flip (jittery work stops rephasing), reset on a hold change
unsigned last_hold;
unsigned waits;
unsigned long long wait_us, wait_iter_us, ta_wait_us;

// Hold telemetry (IRQ side writes, game side reads and clears).
constexpr int kHoldBins = 8;       // 1..6 fields, 7 = 7 or more
volatile unsigned hold_hist[kHoldBins];
volatile unsigned long long lat_sum_us;   // scene finish -> flip
volatile unsigned lat_n, lat_max_us;
// Pictures between scene finish and flip, oldest first.
constexpr unsigned kP = 4;
struct Pic { u32 submit_vb, target_vb, flip_vb, ticks; unsigned long long submit_us, flip_us; };
volatile Pic pic[kP];
volatile unsigned p_head, p_n;
#if RE4DC_PACE_HOLD_LOG >= 2
constexpr unsigned kDone = 8;
volatile Pic done[kDone];
volatile unsigned d_w, d_r;
#endif

void on_flip(u32 now)
{
    const unsigned long long t = timer_us_gettime64();
    if (flip_n) {
        u32 h = now - last_flip_vb;
        if (h >= (u32) kHoldBins) h = kHoldBins - 1;
        ++hold_hist[h];
    }
    ++flip_n;
    last_flip_vb = now;
    if (p_n) {
        volatile Pic& p = pic[p_head];
        if ((int) (now - p.target_vb) > 0) {   // flipped late: the cadence was too early; back off longer each time
            late_cool = cool_len;
            if (cool_len < 4096) cool_len *= 2;
        }
        const unsigned d = unsigned(t - p.submit_us);
        lat_sum_us += d; ++lat_n;
        if (d > lat_max_us) lat_max_us = d;
#if RE4DC_PACE_HOLD_LOG >= 2
        if (d_w - d_r < kDone) {
            volatile Pic& o = done[d_w % kDone];
            o.submit_vb = p.submit_vb; o.target_vb = p.target_vb; o.flip_vb = now; o.ticks = p.ticks;
            o.submit_us = p.submit_us; o.flip_us = t;
            ++d_w;
        }
#endif
        p_head = (p_head + 1) % kP; --p_n;
    }
}

bool post_head(u32 now)
{
    if (pvr_present_async(true) != 0) return false;
    if (now + 1 == q_target[q_head]) ++releases_on_time; else ++releases_late;
    q_head = (q_head + 1) % kQ; --q_n;
    watch = 1;
    return true;
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
    if (q_n && !watch && (int) (now + 1 - q_target[q_head]) >= 0) post_head(now);
}

void ensure_handler()
{
    if (handler_id < 0) handler_id = vblank_handler_add(vbl, nullptr);
}

void wait_until(unsigned max_n)
{
    if (q_n <= max_n) return;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    re4dc::wc24::WaitScope wc24_wait(re4dc::wc24::PaceWait);
#endif
    const unsigned long long t0 = timer_us_gettime64();
    while (q_n > max_n) thd_pass();
    const unsigned long long d = timer_us_gettime64() - t0;
    ++waits; wait_us += d; wait_iter_us += d;
}

void note_submit(u32 now, u32 target)
{
    if (p_n == kP) { p_head = (p_head + 1) % kP; --p_n; }   // telemetry only: drop the oldest
    volatile Pic& p = pic[(p_head + p_n) % kP];
    p.submit_vb = now; p.target_vb = target; p.flip_vb = 0; p.ticks = re4dc_pace_tick_total();
    p.submit_us = timer_us_gettime64();
    ++p_n;
}
}  // namespace

extern "C" {

// present_fence (game thread): every queued picture is handed to KOS first.
void re4dc_steady_wait(void) { wait_until(0); }

int re4dc_steady_pending(void) { return q_n != 0; }

// pace.cpp (Steady drop decision): 1 while queued pictures reach more than hold + 1 fields ahead, i.e. the pictures
// are waiting longer than one hold for their slot (a backlog left by a hold change or a stall). Dropping the next image
// drains it without changing the flip cadence.
int re4dc_steady_backlog(unsigned hold)
{
    if (!q_n) return 0;
    return (int) (last_target - re4dc_vi_retrace_count()) > (int) hold + 1;
}

// native_ui.cpp stream_open, after pvr_scene_begin: in Steady the next scene's TA bank frees only when a held picture
// flips, so KOS's own wait at the first list (pvr_wait_ready) is taken here and timed as a wait, not as work.
void re4dc_steady_ta_wait(void)
{
#if RE4DC_PACE_STEADY
    if (!re4dc_pace_steady_hold()) return;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    re4dc::wc24::WaitScope wc24_wait(re4dc::wc24::PvrWait);
#endif
    const unsigned long long t0 = timer_us_gettime64();
    pvr_wait_ready();
    const unsigned long long d = timer_us_gettime64() - t0;
    wait_iter_us += d; ta_wait_us += d;
#endif
}

// pace.cpp: the game thread's queue wait in this iteration (not work), then cleared.
unsigned re4dc_steady_wait_take(void)
{
    const unsigned w = unsigned(wait_iter_us);
    wait_iter_us = 0;
    return w;
}

// present_submit, before pvr_present_async. Returns 1 when the present decision was queued (the caller skips it).
int re4dc_steady_present(int present)
{
    ensure_handler();
#if RE4DC_PACE_HOLD_LOG >= 2
    while (d_r != d_w) {
        const volatile Pic& o = done[d_r % kDone];
        re4dc_log("PACE pic sub=%u tgt=%u flip=%u ticks=%u lat_us=%u\n", (unsigned) o.submit_vb, (unsigned) o.target_vb,
                  (unsigned) o.flip_vb, (unsigned) o.ticks, unsigned(o.flip_us - o.submit_us));
        ++d_r;
    }
#endif
    if (!present) { wait_until(0); return 0; }       // a discard applies to the oldest finished scene: queue empty first
    const u32 now = re4dc_vi_retrace_count();
#if RE4DC_PACE_STEADY
    const int hold = re4dc_pace_steady_hold();
    if (hold && (unsigned) hold != last_hold) { last_hold = hold; cool_len = 64; }
    if (hold && flip_n) {
        wait_until(kQ - 1);                           // room in the queue
        const int irq = irq_disable();
        const u32 base = (q_n || watch) ? last_target : last_flip_vb;
        u32 target = base + (u32) hold;
        if ((int) (now + 1 - target) > 0) target = now + 1;   // late: as soon as possible, the next counts from here
        // Phase: when kPhaseRun pictures in a row could have flipped a field earlier, the cadence is late against
        // the work; one hold one field shorter moves it earlier (input latency), then the hold is constant again.
        if ((int) (target - (now + 1)) >= 1) {
            if (late_cool) {
                --late_cool; early_run = 0;
            } else if (++early_run >= kPhaseRun && (int) (target - 1 - (now + 1)) >= 0 && (int) (target - 1 - base) >= 1) {
                --target; early_run = 0; ++rephase;
            }
        } else {
            early_run = 0;
        }
        if (!q_n && !watch && target == now + 1) {
            last_target = target;
            irq_restore(irq);
            note_submit(now, target);
            return 0;                                 // due now: the caller presents at once
        }
        q_target[(q_head + q_n) % kQ] = target;
        ++q_n;
        last_target = target;
        irq_restore(irq);
        note_submit(now, target);
        return 1;                                     // released by vbl() at field target - 1
    }
#endif
    wait_until(0);                                    // leaving Steady: queued pictures first, in order
    last_target = now + 1;
    note_submit(now, now + 1);
    return 0;
}

// present_submit, after a successful pvr_present_async(present) by the game thread (interrupts off).
void re4dc_present_posted(int present)
{
    if (present) watch = 1;
}

// pace.cpp report(): one histogram line per telemetry window.
void re4dc_present_hold_report(void)
{
    unsigned h[kHoldBins];
    unsigned long long ls;
    unsigned ln, lm, rl, ro;
    {
        const int irq = irq_disable();
        for (int i = 0; i < kHoldBins; ++i) { h[i] = hold_hist[i]; hold_hist[i] = 0; }
        ls = lat_sum_us; ln = lat_n; lm = lat_max_us; rl = releases_late; ro = releases_on_time;
        lat_sum_us = 0; lat_n = 0; lat_max_us = 0; releases_late = releases_on_time = 0;
        irq_restore(irq);
    }
    re4dc_log("PACE hold h1=%u h2=%u h3=%u h4=%u h5=%u h6=%u h7p=%u lat_avg_us=%u lat_max_us=%u steady_late=%u "
              "steady_on_time=%u steady_waits=%u steady_wait_us=%u steady_rephase=%u\n",
              h[1], h[2], h[3], h[4], h[5], h[6], h[7], ln ? unsigned(ls / ln) : 0, lm, rl, ro, waits, unsigned(wait_us), unsigned(ta_wait_us),
              rephase);
    waits = 0; wait_us = 0; ta_wait_us = 0; rephase = 0;
}

}  // extern "C"
