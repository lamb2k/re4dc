// The engine's sampling profiler (lane eng-crash1, 2026-11-22; plan 3.3 section 8, SALVAGE_20261121.md row 45).
//
// Lifted from the old port: port/dreamcast/game/platform/pc_sampler.cpp on origin/t15/int, last changed in commit
// c1a9f6dc4f49aebc834a36dc1960cb851c2f2263 (the console sampler of the 11-12 profile). Taken as it was: TMU1 (the only
// TMU channel KOS leaves free: TMU0 is the scheduler's wake-ups, TMU2 the uptime clock the engine's clock reads,
// core/e1_clock.h), the refusal when TMU1 is already in use, the underflow interrupt through KOS's exception path (ctx->pc
// is the interrupted pc, ctx->pr its pr), the xorshift jitter of the period (it breaks phase lock with the 30 fps
// pictures; the mean period stays the nominal one), the late-sample and latency counts, the record (tid << 23 | pc >> 1;
// flags | pr >> 1), publication of the head after the record, the handler that never allocates, logs or touches the
// FP registers.
// Left out: the PC_SAMPLER build knob (the engine has no default-off build switch: this is a lab arm, the boot file
// PCSAMPLE read before play), the fixed .bss ring and its arena move (allocated at load only when PCSAMPLE is there),
// the native render profile's stage field, the per-frame marker re4dc_pcs_frame (no per-picture hook: the engine's own
// rows time the pictures), and read_pcs.py's streaming header ABI (include/pc_sampler.h): the engine image ranks the
// samples itself after play.
// New: the helper thread that starts the sampler at the first tick of play and stops it after the last (no code in the
// main loop), the table printed after play (E1 PCS lines: totals, then the top pcs by samples), the timer check line
// (TMU1's period, TMU2's reload against the engine clock's E1_CLOCK_COUNTS), and the control "spin": the helper thread
// busy-spins 10 ms of every 33 ms of play in e1_pcs_spin, which the table must show near a quarter of the samples.
//
// PCSAMPLE (a lab arm for measurement runs, never in a timing scene): "[hz N] [spin]", default 200 Hz.
#include <kos.h>
#include <arch/irq.h>
#include <arch/timer.h>
#include <kos/thread.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "e1_core.h"
#include "e1_clock.h"
#include "pc_sampler.h"

extern volatile uint32_t e1_tick;      // core/main.cpp
extern volatile uint32_t e1_state[8];  // core/main.cpp: 0 stage (4 = the ticks, 5 after), 3 done
extern "C" void e1_log(const char* fmt, ...);

namespace {
// SH7750 TMU registers (same map as KOS kernel/arch/dreamcast/kernel/timer.c).
#define PCS_TMU16(o) (*(volatile uint16_t*) (0xffd80000u + (o)))
#define PCS_TMU32(o) (*(volatile uint32_t*) (0xffd80000u + (o)))
constexpr uint32_t kTCOR1 = 0x14, kTCNT1 = 0x18, kTCR1 = 0x1c, kTCOR2 = 0x20;
constexpr uint16_t kUNF = 0x0100;
constexpr uint32_t kRecords = 4096;   // 32 KiB, allocated at load with PCSAMPLE only
enum : uint32_t { F_PC_FOREIGN = 1u << 30, F_PR_FOREIGN = 1u << 29, F_LATE = 1u << 28 };

struct Ring {
    volatile uint32_t head, samples, late, lat_max, lat_sum_lo, lat_sum_hi, late_ticks, running;
    uint32_t* rec;
};
Ring g;
uint32_t g_tcor;           // value TCNT1 reloads from at the next underflow
uint32_t g_base;           // nominal period in 80 ns ticks
uint32_t g_jitter;         // 2^n-1 <= period/16: breaks phase lock with periodic work
uint32_t g_rng = 0x2545f491u;
irq_cb_t g_previous;       // KOS default, restored by stop
unsigned g_hz = 200;
int g_spin;

inline uint32_t current_tid()
{
    const kthread_t* t = thd_current;
    return t ? (uint32_t(t->tid) & 0x1ffu) : 0u;
}

void pcs_irq(irq_t code, irq_context_t* ctx, void* data)
{
    (void) code;
    (void) data;
    PCS_TMU16(kTCR1) = PCS_TMU16(kTCR1) & ~kUNF;          // acknowledge the underflow
    const uint32_t elapsed = g_tcor - PCS_TMU32(kTCNT1);   // ticks since underflow (IRQ latency)
    uint32_t x = g_rng;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    g_rng = x;
    g_tcor = g_base - (g_jitter >> 1) + (x & g_jitter);   // mean period stays g_base
    PCS_TMU32(kTCOR1) = g_tcor;                            // takes effect at the next reload

    const uint32_t pc = ctx->pc, pr = ctx->pr;
    uint32_t flags = 0;
    if ((pc & 0x1f000000u) != 0x0c000000u) flags |= F_PC_FOREIGN;
    if ((pr & 0x1f000000u) != 0x0c000000u) flags |= F_PR_FOREIGN;
    if (elapsed > g.late_ticks) {
        flags |= F_LATE;
        g.late = g.late + 1;
    }
    const uint32_t head = g.head;
    uint32_t* r = g.rec + 2 * (head & (kRecords - 1));
    r[0] = current_tid() << 23 | (pc & 0xffffffu) >> 1;
    r[1] = flags | (pr & 0xffffffu) >> 1;
    const uint32_t lo = g.lat_sum_lo + elapsed;
    if (lo < elapsed) g.lat_sum_hi = g.lat_sum_hi + 1;
    g.lat_sum_lo = lo;
    if (elapsed > g.lat_max) g.lat_max = elapsed;
    g.samples = g.samples + 1;
    __asm__ volatile("" ::: "memory");
    g.head = head + 1;                                     // publish after the record
}

bool pcs_start()
{
    if (timer_running(TMU1) || timer_ints_enabled(TMU1)) {
        e1_log("E1 PCS: TMU1 already in use; not started\n");
        return false;
    }
    const irq_mask_t old = irq_disable();
    g_previous = irq_get_handler(EXC_TMU1_TUNI1);
    irq_set_handler(EXC_TMU1_TUNI1, pcs_irq, nullptr);
    timer_prime(TMU1, g_hz, 1);   // Pck/4 (80 ns ticks), underflow interrupt on
    g_base = g_tcor = PCS_TMU32(kTCOR1);
    uint32_t j = 1;
    while ((j << 1) - 1 <= g_base / 16) j <<= 1;
    g_jitter = j - 1;
    g.late_ticks = g_base / 2 < 1250u ? g_base / 2 : 1250u;   // 100 us
    timer_clear(TMU1);
    timer_start(TMU1);
    g.running = 1;
    irq_restore(old);
    return true;
}

void pcs_stop()
{
    if (!g.running) return;
    const irq_mask_t old = irq_disable();
    timer_stop(TMU1);   // also masks TMU1 at the IPR
    timer_clear(TMU1);
    irq_set_handler(EXC_TMU1_TUNI1, g_previous.hdl, g_previous.data);
    g.running = 0;
    irq_restore(old);
}

int cmp_u32(const void* a, const void* b)
{
    const uint32_t x = *(const uint32_t*) a, y = *(const uint32_t*) b;
    return (x > y) - (x < y);
}

// The table: every kept sample's pc (0x8c000000 | pc), sorted, counted; the top 20 by samples.
void pcs_report(uint32_t tick_first, uint32_t tick_last)
{
    const uint32_t total = g.samples, kept = total < kRecords ? total : kRecords;
    uint32_t* pcs = (uint32_t*) malloc(kept * 4 + 4);
    unsigned foreign = 0, late = 0;
    const uint32_t first = g.head - kept;
    for (uint32_t i = 0; i < kept; ++i) {
        const uint32_t* r = g.rec + 2 * ((first + i) & (kRecords - 1));
        pcs[i] = 0x8c000000u | (r[0] & 0x7fffffu) << 1;
        if (r[1] & F_PC_FOREIGN) foreign++;
        if (r[1] & F_LATE) late++;
    }
    qsort(pcs, kept, 4, cmp_u32);
    const uint64_t lat_sum = (uint64_t) g.lat_sum_hi << 32 | g.lat_sum_lo;
    e1_log("E1 PCS samples %lu kept %lu hz %u period %lu ticks jitter %lu ticks 1-%lu (play) late %u foreign-pc %u "
           "latency mean %lu max %lu (80 ns ticks)%s\n",
           (unsigned long) total, (unsigned long) kept, g_hz, (unsigned long) g_base, (unsigned long) g_jitter,
           (unsigned long) tick_last, late, foreign, (unsigned long) (total ? lat_sum / total : 0),
           (unsigned long) g.lat_max, g_spin ? " spin control on" : "");
    (void) tick_first;
    for (int rank = 1; rank <= 20; ++rank) {
        uint32_t best = 0, best_pc = 0;
        for (uint32_t i = 0; i < kept;) {
            uint32_t j = i;
            while (j < kept && pcs[j] == pcs[i]) ++j;
            if (pcs[i] && j - i > best) { best = j - i; best_pc = pcs[i]; }
            i = j;
        }
        if (!best) break;
        e1_log("E1 PCS top %d pc %08lx samples %lu\n", rank, (unsigned long) best_pc, (unsigned long) best);
        for (uint32_t i = 0; i < kept; ++i) if (pcs[i] == best_pc) pcs[i] = 0;   // taken: a zero run is never ranked
    }
    free(pcs);
    // the timer check: TMU1 is the sampler's alone; TMU2 still reloads at the engine clock's rate (the pacer's fields
    // come from the vblank count, core/frame.cpp)
    const uint32_t tcor2 = PCS_TMU32(kTCOR2) + 1;
    e1_log("E1 PCS timers: TMU1 %s after play, TMU2 reload %lu counts (engine clock %lu: %s)\n",
           timer_running(TMU1) ? "RUNNING" : "stopped", (unsigned long) tcor2, (unsigned long) E1_CLOCK_COUNTS,
           tcor2 == E1_CLOCK_COUNTS || tcor2 - 1 == E1_CLOCK_COUNTS ? "same" : "DIFFERENT");
}

}  // namespace

// the control's known load: 10 ms, nearly all of it in this function's own loop (the clock read once in 4096 rounds)
extern "C" void __attribute__((noinline)) e1_pcs_spin(void)
{
    const uint64_t t = timer_us_gettime64();
    volatile uint32_t k = 0;
    do {
        for (unsigned i = 0; i < 4096; ++i) k = k + 1;
    } while (timer_us_gettime64() - t < 10000);
}

namespace {
void* helper(void*)
{
    while (e1_state[0] < 4) thd_sleep(2);
    const uint32_t t0 = e1_tick;
    if (!pcs_start()) return nullptr;
    while (e1_state[0] == 4) {
        if (g_spin) { e1_pcs_spin(); thd_sleep(23); }
        else thd_sleep(5);
    }
    const uint32_t t1 = e1_tick;
    pcs_stop();
    while (!e1_state[3]) thd_sleep(5);   // after the image's report (core/main.cpp)
    pcs_report(t0, t1);
    return nullptr;
}
}  // namespace

extern "C" void e1_pcs_boot(void)
{
    file_t f = fs_open("/cd/PCSAMPLE", O_RDONLY);
    if (f < 0) return;
    char t[32] = {0};
    const ssize_t n = fs_read(f, t, sizeof(t) - 1);
    fs_close(f);
    if (n > 0) {
        const char* h = strstr(t, "hz ");
        if (h && atoi(h + 3) >= 50 && atoi(h + 3) <= 20000) g_hz = (unsigned) atoi(h + 3);
        g_spin = strstr(t, "spin") != nullptr;
    }
    g.rec = (uint32_t*) memalign(32, kRecords * 8);
    if (!g.rec) { e1_log("E1 PCS: no ring (%lu bytes refused)\n", (unsigned long) (kRecords * 8)); return; }
    memset(g.rec, 0, kRecords * 8);
    e1_log("E1 PCSAMPLE: TMU1 sampler %u Hz over play, ring %lu records (%lu bytes at %p)%s (lab arm, never a timing "
           "scene)\n", g_hz, (unsigned long) kRecords, (unsigned long) (kRecords * 8), (void*) g.rec,
           g_spin ? ", spin control: 10 ms of every 33 ms in e1_pcs_spin" : "");
    kthread_attr_t a = {};
    a.stack_size = 4096;
    a.prio = PRIO_DEFAULT - 1;
    a.label = "e1pcs";
    a.create_detached = true;
    thd_create_ex(&a, helper, nullptr);
}
