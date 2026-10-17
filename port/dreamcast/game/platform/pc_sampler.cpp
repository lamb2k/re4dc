// Default-off statistical PC sampler (Makefile PC_SAMPLER=1). ABI and record
// layout: include/pc_sampler.h. Host side: read_pcs.py streams the ring out of
// the emulator, pcs_symbolize.py ranks functions against the ELF symbol table.
//
// Mechanism: TMU1 is the only TMU channel KOS leaves free (TMU0 = scheduler
// wakeups, TMU2 = uptime clock that native_render_profile.hpp reads). Its
// underflow interrupt goes through the normal KOS exception path, which saves
// the interrupted thread's registers into thd_current->context before calling
// handlers, so ctx->pc is SPC (the interrupted PC) and ctx->pr its PR. The
// handler never allocates, never logs and never touches FP registers.
//
// With the knob off this translation unit is empty.
#include "pc_sampler.h"
#if RE4DC_PC_SAMPLER && defined(__sh__)
#include <kos.h>
#include <arch/irq.h>
#include <arch/timer.h>
#include <kos/thread.h>
#include <stdint.h>

#include "re4dc_platform.h"
#ifndef RE4DC_NATIVE_RENDER_PROFILE
#define RE4DC_NATIVE_RENDER_PROFILE 0
#endif
#if RE4DC_NATIVE_RENDER_PROFILE
#include "native_render_profile.hpp"
#endif
#ifndef RE4DC_PC_SAMPLER_HZ
#define RE4DC_PC_SAMPLER_HZ 1000
#endif
#ifndef RE4DC_PC_SAMPLER_BYTES
#define RE4DC_PC_SAMPLER_BYTES 16384
#endif

static constexpr uint32_t kRecords = RE4DC_PC_SAMPLER_BYTES / 8;
static_assert(RE4DC_PC_SAMPLER_BYTES % 8 == 0 && kRecords >= 128 && (kRecords & (kRecords - 1)) == 0,
              "PC_SAMPLER_BYTES must be a power of two >= 1024");
static_assert(RE4DC_PC_SAMPLER_HZ >= 50 && RE4DC_PC_SAMPLER_HZ <= 20000, "PC_SAMPLER_HZ out of range");
static_assert(RE4DC_PCS_H_COUNT <= RE4DC_PCS_HEADER_WORDS, "pc sampler header overflow");

// SH7750 TMU registers (same map as KOS kernel/arch/dreamcast/kernel/timer.c).
#define PCS_TMU16(o) (*(volatile uint16_t*) (0xffd80000u + (o)))
#define PCS_TMU32(o) (*(volatile uint32_t*) (0xffd80000u + (o)))
static constexpr uint32_t kTCOR1 = 0x14, kTCNT1 = 0x18, kTCR1 = 0x1c;
static constexpr uint16_t kUNF = 0x0100;

struct alignas(32) Re4dcPcsRing {
    volatile uint32_t h[RE4DC_PCS_HEADER_WORDS];
    uint32_t rec[kRecords * 2];
};
static_assert(sizeof(Re4dcPcsRing) == RE4DC_PCS_HEADER_WORDS * 4 + RE4DC_PC_SAMPLER_BYTES, "pc sampler ring ABI");

// One fixed .bss object: the Makefile moves PC_SAMPLER_BYTES + 4 KiB from the
// source arena to the KOS heap (ARENA_KOS_BYTES) so the KOS heap is not reduced.
extern "C" {
__attribute__((used)) Re4dcPcsRing re4dc_pcs;
}

static uint32_t g_tcor;           // value TCNT1 reloads from at the next underflow
static uint32_t g_base;           // nominal period in 80 ns ticks
static uint32_t g_jitter;         // 2^n-1 <= period/16: breaks phase lock with periodic work
static uint32_t g_rng = 0x2545f491u;
static irq_cb_t g_previous;       // KOS default (irq_def_timer), restored by stop
#if RE4DC_PC_SAMPLER_PHASE
#if RE4DC_NATIVE_RENDER_PROFILE
#error "PC_SAMPLER_PHASE and NATIVE_RENDER_PROFILE both use the sample stage field"
#endif
// PC_SAMPLER_PHASE=1: id of the last game-phase marker, read by the ISR. Markers are keyed by
// their name pointer (string literals at the ProcessTickGet call sites); ids 0..29.
static volatile uint32_t g_phase = RE4DC_PCS_STAGE_NONE;
static const char* g_phase_names[RE4DC_PCS_PHASE_OTHER];
static uint32_t g_phase_count;
#endif

static inline uint32_t currentTid(void)
{
    const kthread_t* t = thd_current;
    return t ? (uint32_t(t->tid) & 0x1ffu) : 0u;
}

static void pcsIrq(irq_t code, irq_context_t* ctx, void* data)
{
    (void) code;
    (void) data;
    volatile uint32_t* h = re4dc_pcs.h;
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
    if ((pc & 0x1f000000u) != 0x0c000000u) flags |= RE4DC_PCS_F_PC_FOREIGN;
    if ((pr & 0x1f000000u) != 0x0c000000u) flags |= RE4DC_PCS_F_PR_FOREIGN;
    if (elapsed > h[RE4DC_PCS_H_LATE_TICKS]) {
        flags |= RE4DC_PCS_F_LATE;
        h[RE4DC_PCS_H_LATE] = h[RE4DC_PCS_H_LATE] + 1;
    }
    uint32_t stage = RE4DC_PCS_STAGE_NONE;
#if RE4DC_NATIVE_RENDER_PROFILE
    // Stage of the one native render thread; host filters by tid when needed.
    if (re4dc::profile::state.active) stage = re4dc::profile::state.stage & 31u;
#endif
#if RE4DC_PC_SAMPLER_PHASE
    stage = g_phase & 31u;
#endif
    const uint32_t head = h[RE4DC_PCS_H_HEAD];
    uint32_t* r = re4dc_pcs.rec + 2 * (head & (kRecords - 1));
    r[0] = currentTid() << 23 | (pc & 0xffffffu) >> 1;
    r[1] = flags | stage << 23 | (pr & 0xffffffu) >> 1;

    const uint32_t lo = h[RE4DC_PCS_H_LAT_SUM_LO] + elapsed;
    if (lo < elapsed) h[RE4DC_PCS_H_LAT_SUM_HI] = h[RE4DC_PCS_H_LAT_SUM_HI] + 1;
    h[RE4DC_PCS_H_LAT_SUM_LO] = lo;
    if (elapsed > h[RE4DC_PCS_H_LAT_MAX]) h[RE4DC_PCS_H_LAT_MAX] = elapsed;
    h[RE4DC_PCS_H_SAMPLES] = h[RE4DC_PCS_H_SAMPLES] + 1;
    __asm__ volatile("" ::: "memory");
    h[RE4DC_PCS_H_HEAD] = head + 1;                        // publish after the record
}

extern "C" {

void re4dc_pcs_start(void)
{
    volatile uint32_t* h = re4dc_pcs.h;
    if (h[RE4DC_PCS_H_STATE] == RE4DC_PCS_RUNNING) return;
    if (timer_running(TMU1) || timer_ints_enabled(TMU1)) {
        h[RE4DC_PCS_H_STATE] = RE4DC_PCS_BUSY;
        re4dc_log("pc sampler: TMU1 already in use; not started\n");
        return;
    }
    const irq_mask_t old = irq_disable();
    h[RE4DC_PCS_H_MAGIC] = RE4DC_PCS_MAGIC;
    h[RE4DC_PCS_H_VERSION] = RE4DC_PCS_VERSION;
    h[RE4DC_PCS_H_HEADER_WORDS] = RE4DC_PCS_HEADER_WORDS;
    h[RE4DC_PCS_H_CAPACITY] = kRecords;
    h[RE4DC_PCS_H_HZ] = RE4DC_PC_SAMPLER_HZ;
    h[RE4DC_PCS_H_STAGE_SOURCE] = RE4DC_PC_SAMPLER_PHASE ? RE4DC_PCS_STAGE_SRC_PHASE : RE4DC_NATIVE_RENDER_PROFILE;
    g_previous = irq_get_handler(EXC_TMU1_TUNI1);
    irq_set_handler(EXC_TMU1_TUNI1, pcsIrq, nullptr);
    timer_prime(TMU1, RE4DC_PC_SAMPLER_HZ, 1);  // Pck/4 (80 ns ticks), UNIE, IPR priority 15
    g_base = g_tcor = PCS_TMU32(kTCOR1);
    uint32_t j = 1;
    while ((j << 1) - 1 <= g_base / 16) j <<= 1;
    g_jitter = j - 1;
    h[RE4DC_PCS_H_PERIOD_TICKS] = g_base;
    h[RE4DC_PCS_H_JITTER_MASK] = g_jitter;
    h[RE4DC_PCS_H_LATE_TICKS] = g_base / 2 < 1250u ? g_base / 2 : 1250u;  // 100 us
    const timer_val_t now = __dreamcast_get_ticks();
    h[RE4DC_PCS_H_START_SECS] = now.secs;
    h[RE4DC_PCS_H_START_TICKS] = now.ticks;
    timer_clear(TMU1);
    timer_start(TMU1);
    h[RE4DC_PCS_H_STATE] = RE4DC_PCS_RUNNING;
    irq_restore(old);
    re4dc_log("pc sampler: TMU1 %u Hz period=%lu ticks jitter=%lu ring=%lu records at %p (%u bytes)\n",
              (unsigned) RE4DC_PC_SAMPLER_HZ, (unsigned long) g_base, (unsigned long) g_jitter,
              (unsigned long) kRecords, (void*) &re4dc_pcs, (unsigned) sizeof(re4dc_pcs));
}

void re4dc_pcs_stop(void)
{
    volatile uint32_t* h = re4dc_pcs.h;
    if (h[RE4DC_PCS_H_STATE] != RE4DC_PCS_RUNNING) return;
    const irq_mask_t old = irq_disable();
    timer_stop(TMU1);  // also masks TMU1 at the IPR
    timer_clear(TMU1);
    irq_set_handler(EXC_TMU1_TUNI1, g_previous.hdl, g_previous.data);
    h[RE4DC_PCS_H_STATE] = RE4DC_PCS_STOPPED;
    irq_restore(old);
}

void re4dc_pcs_frame(unsigned frame)
{
    volatile uint32_t* h = re4dc_pcs.h;
    if (h[RE4DC_PCS_H_STATE] != RE4DC_PCS_RUNNING) return;
    const irq_mask_t old = irq_disable();  // the ISR shares the head
    const uint32_t head = h[RE4DC_PCS_H_HEAD];
    uint32_t* r = re4dc_pcs.rec + 2 * (head & (kRecords - 1));
    r[0] = frame;
    r[1] = RE4DC_PCS_F_MARKER | currentTid();
    h[RE4DC_PCS_H_MARKERS] = h[RE4DC_PCS_H_MARKERS] + 1;
    h[RE4DC_PCS_H_LAST_FRAME] = frame;
    __asm__ volatile("" ::: "memory");
    h[RE4DC_PCS_H_HEAD] = head + 1;
    irq_restore(old);
}

#if RE4DC_PC_SAMPLER_PHASE
void re4dc_pcs_phase_mark(int no, const char* name)
{
    uint32_t id = 0;
    while (id < g_phase_count && g_phase_names[id] != name) ++id;
    if (id == g_phase_count) {
        if (g_phase_count < RE4DC_PCS_PHASE_OTHER) {
            g_phase_names[g_phase_count++] = name;
            re4dc_log("PCSPH id=%lu no=%d name=%s\n", (unsigned long) id, no, name ? name : "(null)");
        } else {
            id = RE4DC_PCS_PHASE_OTHER;
        }
    }
    g_phase = id;  // one aligned word store: the ISR sees the old or the new id
}
#endif

}  // extern "C"
#endif
