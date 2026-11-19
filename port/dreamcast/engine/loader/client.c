/* client.c: the console-loop client library (lane eng-loop, 2026-11-19). API and use: cl_client.h. Design:
   docs/engine/CONSOLE_LOOP.md section 4.

   The way back to the loader, in order: (1) the loader image preloaded at cl_init, copied to 0x8C010000 by
   KallistiOS's own exec trampoline (placed in the hand-off area's scratch words, not on a stack the copy could
   overwrite), after the graphics chip, controller DMA and sound are stopped as arch_abort stops them; (2) a BIOS
   reboot (0xA0000000), which boots whatever image GDEMU presents (a console check). Both work from an exception
   handler: no disc access, no allocation, interrupts off. */
#include <kos.h>
#include <arch/arch.h>
#include <arch/irq.h>
#include <kos/cache.h>
#include <dc/pvr.h>
#include <dc/maple.h>
#include <dc/spu.h>
#include <dc/wdt.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cl_client.h"
#include "cl_core.h"

/* the program's stack and heap end below the hand-off area (cl_handoff.h) */
uintptr_t arch_stack_16m = CL_HANDOFF_ADDR;
uintptr_t arch_stack_32m = CL_HANDOFF_ADDR + 0x1000000u;

extern uint32_t _arch_exec_template[], _arch_exec_template_values[], _arch_exec_template_end[];
extern uint32_t _arch_old_sr, _arch_old_vbr, _arch_old_fpscr;

#define H ((cl_handoff_t *)CL_HANDOFF_ADDR)
static int g_active;
static uint8_t *g_loader;
static uint32_t g_loader_len;
static uint64_t g_deadline_ms;
static volatile int g_leaving;

int cl_active(void) { return g_active; }
const char *cl_args(void) { return g_active ? H->h.args : ""; }
uint32_t cl_run_id(void) { return g_active ? H->h.run_id : 0; }

void cl_report_bytes(const void *p, size_t n) {
    if (!g_active) return;
    uint32_t len = H->h.report_len;
    if (len > CL_REPORT_MAX) len = CL_REPORT_MAX;
    if (n > CL_REPORT_MAX - len) n = CL_REPORT_MAX - len;
    memcpy(H->report + len, p, n);
    H->h.report_len = len + (uint32_t)n;
    cl_handoff_seal(H);   /* the header stays valid at every moment: a reboot or power-off mid-run reads as LOST */
}
void cl_report(const char *fmt, ...) {
    if (!g_active) return;
    char b[512];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(b, sizeof(b), fmt, ap);
    va_end(ap);
    if (n > 0) cl_report_bytes(b, (size_t)n < sizeof(b) ? (size_t)n : sizeof(b) - 1);
}

static void seal(uint32_t state, int code) {
    H->h.state = state;
    H->h.exit_code = code;
    if (H->h.report_len > CL_REPORT_MAX) H->h.report_len = CL_REPORT_MAX;
    H->h.report_crc = cl_crc32(0, H->report, H->h.report_len);
    cl_handoff_seal(H);
}

static void __attribute__((noreturn)) reboot_bios(void) {
    irq_disable();   /* as arch_reboot */
    ((void (*)(void))0xa0000000u)();
    for (;;) {}
}

/* copy the loader down and start it: KallistiOS's exec trampoline, from the hand-off area's scratch words */
static void __attribute__((noreturn)) jump_loader(void) {
    irq_disable();
    wdt_disable();
    if (!g_loader || !g_loader_len) reboot_bios();
    PVR_SET(PVR_RESET, PVR_RESET_ALL);   /* as arch_abort: graphics chip, controller DMA, sound */
    PVR_SET(PVR_RESET, PVR_RESET_NONE);
    maple_dma_stop();
    spu_disable();
    const uintptr_t ts = (uintptr_t)_arch_exec_template, te = (uintptr_t)_arch_exec_template_end;
    const size_t words = (te - ts) / 4;
    if (words > CL_TRAMP_WORDS) reboot_bios();
    uint32_t *tr = H->h.tramp;
    for (size_t i = 0; i < words; ++i) tr[i] = _arch_exec_template[i];
    uint32_t *v = tr + (((uintptr_t)_arch_exec_template_values - ts) / 4);
    H->h.tramp_stack[6] = 0xa0000000u;   /* the PR the loader's start-up saves: a loader exit reboots */
    v[0] = (uintptr_t)g_loader;
    v[1] = CL_LOAD_ADDR;
    v[2] = (g_loader_len + 3) / 4;
    v[3] = (uintptr_t)&H->h.tramp_stack[6];
    dcache_wback_range((uintptr_t)g_loader, g_loader_len + 4);
    dcache_wback_range((uintptr_t)H->h.tramp, sizeof(H->h.tramp) + sizeof(H->h.tramp_stack));
    icache_sync_range((uintptr_t)tr, words * 4);
    __asm__ __volatile__("ldc %0, sr" : : "z"(_arch_old_sr) : "memory");
    __asm__ __volatile__("ldc %0, vbr" : : "z"(_arch_old_vbr) : "memory");
    __asm__ __volatile__("lds %0, fpscr" : : "z"(_arch_old_fpscr) : "memory");
    ((void (*)(void))tr)();
    for (;;) {}
}

static void __attribute__((noreturn)) finish(uint32_t state, int code) {
    irq_disable();
    if (!g_leaving) {   /* the first way out wins; a fault on the way out does not rewrite it */
        g_leaving = 1;
        seal(state, code);
    }
    jump_loader();
}

void cl_exit(int code) {
    if (!g_active) exit(code);
    finish(CL_RUN_DONE, code);
}

static void crash_handler(irq_t code, irq_context_t *ctx, void *data) {
    (void)data;
    if (!g_leaving) {
        H->h.crash_evt = code;
        H->h.crash_pc = ctx ? CONTEXT_PC(*ctx) : 0;
        H->h.crash_pr = ctx ? ctx->pr : 0;
        H->h.crash_sp = ctx ? CONTEXT_SP(*ctx) : 0;
        /* no printf in an exception handler: fixed text, hex by hand */
        char b[] = "\nCRASH event xxx pc xxxxxxxx pr xxxxxxxx sp xxxxxxxx\n";
        static const char hx[] = "0123456789abcdef";
        const uint32_t vals[4] = {(uint32_t)code, H->h.crash_pc, H->h.crash_pr, H->h.crash_sp};
        const int at[4] = {13, 20, 32, 44}, digits[4] = {3, 8, 8, 8};
        for (int k = 0; k < 4; ++k)
            for (int d = 0; d < digits[k]; ++d) b[at[k] + d] = hx[(vals[k] >> (4 * (digits[k] - 1 - d))) & 15];
        cl_report_bytes(b, sizeof(b) - 1);
    }
    finish(CL_RUN_CRASHED, -1);
}

#ifdef CL_WRAP_ABORT
void __real_arch_abort(void);
void __wrap_arch_abort(void) {
    if (g_active && !g_leaving) {
        cl_report("\nABORT (panic or failed assert)\n");
        finish(CL_RUN_CRASHED, -3);
    }
    __real_arch_abort();
}
#endif

static void at_exit(void) {
    if (g_active && !g_leaving) finish(CL_RUN_DONE, 0);
}

static void *watchdog(void *arg) {
    (void)arg;
    for (;;) {
        thd_sleep(250);
        if (timer_ms_gettime64() >= g_deadline_ms) {
            cl_report("\nDEADLINE %u s\n", (unsigned)H->h.deadline_s);
            finish(CL_RUN_TIMEOUT, -2);
        }
    }
    return NULL;
}

static void preload(void) {
    FILE *f = fopen("/cd/LOADER.BIN", "rb");
    if (!f) return;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (n > 0 && n < 4 * 1024 * 1024) {
        g_loader = (uint8_t *)memalign(32, (size_t)n + 4);
        if (g_loader) {
            memset(g_loader + n, 0, 4);
            if (fread(g_loader, 1, (size_t)n, f) == (size_t)n) g_loader_len = (uint32_t)n;
            else { free(g_loader); g_loader = NULL; }
        }
    }
    fclose(f);
    H->h.loader_len = g_loader_len;
    cl_handoff_seal(H);
}

int cl_init(unsigned flags) {
    g_active = cl_handoff_valid(H) && H->h.state == CL_RUN_RUNNING;
    if (!g_active) return 0;
    H->h.report_len = 0;
    cl_handoff_seal(H);
    if (!(flags & CL_NO_PRELOAD)) preload();
    irq_set_handler(EXC_UNHANDLED_EXC, crash_handler, NULL);
    irq_set_handler(EXC_DOUBLE_FAULT, crash_handler, NULL);
    atexit(at_exit);
    if (H->h.deadline_s) {
        g_deadline_ms = timer_ms_gettime64() + (uint64_t)H->h.deadline_s * 1000u;
        kthread_attr_t a;
        memset(&a, 0, sizeof(a));
        a.create_detached = true;
        a.prio = 1;
        a.label = "cl-watchdog";
        thd_create_ex(&a, watchdog, NULL);
    }
    return 1;
}
