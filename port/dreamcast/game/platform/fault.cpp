// Fault capture for the boot-forward work: KOS debug output (dbglog, panics,
// the unhandled-exception dump) is routed into the RAM log ring, and an
// unhandled SH-4 exception logs the faulting context and parks the CPU so the
// evidence tooling can still read the ring out of the emulator.
#include <kos.h>
#include <kos/dbgio.h>
#include <arch/irq.h>
#include <stdio.h>
#if defined(RE4DC_LOG_ATOMIC16) && RE4DC_LOG_ATOMIC16
#include <errno.h>
#endif

#include "re4dc_platform.h"

extern "C" void re4dc_log_raw(const char* data, unsigned long len);
extern "C" int re4dc_log_console;

static int ringDetected(void) { return 1; }
static int ringInit(void) { return 0; }
static int ringShutdown(void) { return 0; }
static int ringSetIrqUsage(int mode) { (void) mode; return 0; }
static int ringFlush(void) { return 0; }
static int ringWriteBuffer(const uint8_t* data, int len, int xlat)
{
    (void) xlat;
#if defined(RE4DC_LOG_ATOMIC16) && RE4DC_LOG_ATOMIC16
    // KOS dbgio handlers return -1 and set errno on failure. Do not turn a
    // negative signed device length into a huge unsigned masked append.
    if (len < 0) { errno = EINVAL; return -1; }
    if (!data && len) { errno = EFAULT; return -1; }
#endif
    re4dc_log_raw((const char*) data, (unsigned long) len);
    return len;
}
static int ringReadBuffer(uint8_t* data, int len)
{
    (void) data;
    (void) len;
    return -1;
}

static dbgio_handler_t g_ringHandler = {
    "re4ring", ringDetected, ringInit, ringShutdown, ringSetIrqUsage, ringFlush, ringWriteBuffer, ringReadBuffer, {NULL}};

#if RE4DC_VMU_DEBUG_SLOT
extern "C" void re4dc_dbgslot_ring(unsigned kind, unsigned a, unsigned b);
#endif
#if RE4DC_CRASH_SCREEN
extern "C" void re4dc_crash_screen_init(void);
extern "C" void re4dc_crash_screen_fault(unsigned code, unsigned long pc, unsigned long pr, unsigned long addr);
extern "C" void re4dc_crash_screen_halt(const char* file, int line);
#if RE4DC_CRASH_FAULT_DETAIL
extern "C" void re4dc_crash_screen_context(const irq_context_t* ctx);
#endif
#endif
#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK
extern "C" void re4dc_otwc_fault();
#endif
static void onFault(irq_t code, irq_context_t* ctx, void* data)
{
    (void) data;
#if RE4DC_CRASH_SCREEN && RE4DC_CRASH_FAULT_DETAIL
    re4dc_crash_screen_context(ctx);  // preserve the actual exception, before logging or other calls
#endif
    re4dc_log("fault context: expevt=%08lx inside=%08lx thread=%p tid=%d stack=%p bytes=%u\n",
              *(volatile unsigned long*)0xff000024, (unsigned long)irq_inside_int(),
              thd_current, thd_current ? thd_current->tid : -1,
              thd_current ? thd_current->stack : NULL, thd_current ? thd_current->stack_size : 0);
    re4dc_log("FAULT code=%03x pc=%08lx pr=%08lx sp=%08lx sr=%08lx\n", (unsigned) code, (unsigned long) ctx->pc,
              (unsigned long) ctx->pr, (unsigned long) ctx->r[15], (unsigned long) ctx->sr);
    for (int i = 0; i < 16; i += 4) {
        re4dc_log("  r%-2d %08lx  r%-2d %08lx  r%-2d %08lx  r%-2d %08lx\n", i, (unsigned long) ctx->r[i], i + 1,
                  (unsigned long) ctx->r[i + 1], i + 2, (unsigned long) ctx->r[i + 2], i + 3,
                  (unsigned long) ctx->r[i + 3]);
    }
#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK
    re4dc_otwc_fault();  // trans_ot.cpp: the ExecOt entry being called, if any
#endif
    re4dc_set_stage(0xDEAD0000ul | (unsigned long) code);
#if RE4DC_VMU_DEBUG_SLOT
    re4dc_dbgslot_ring(3, (unsigned) ctx->pc, (unsigned) ctx->pr);  // kept in RAM for the next debug save
#endif
    irq_disable();
#if RE4DC_CRASH_SCREEN
    re4dc_crash_screen_fault((unsigned) code, (unsigned long) ctx->pc, (unsigned long) ctx->pr,
                             *(volatile unsigned long*) 0xff00000c);  // TEA: the faulting data address
#endif
    for (;;) {
    }
}

// Source HALT() (types.h RE4DC_HALT_STORE): the game decided to stop. Log where, then stop
// deterministically like an unhandled fault (stage 0xDEAD0111, interrupts off, spin). Never
// touches area 4. Game logic is unchanged: this only runs after the game has chosen to halt.
extern "C" unsigned re4dc_ui_frame();
extern "C" void re4dc_halt(const char* file, int line)
{
    re4dc_log("HALT stop: %s(%d) ui_frame=%u thread=%d inside_int=%d\n", file ? file : "?", line, re4dc_ui_frame(),
              thd_current ? thd_current->tid : -1, (int) irq_inside_int());
    re4dc_set_stage(0xDEAD0111ul);
    irq_disable();
#if RE4DC_CRASH_SCREEN
    re4dc_crash_screen_halt(file, line);
#endif
    for (;;) {
    }
}

extern "C" void re4dc_fault_init(void)
{
    dbgio_add_handler(&g_ringHandler);
    if (dbgio_dev_select("re4ring") == 0) {
        re4dc_log_console = 0;  // stdout now lands in the ring itself
    }
    irq_set_handler(EXC_UNHANDLED_EXC, onFault, NULL);
    irq_set_handler(EXC_DOUBLE_FAULT, onFault, NULL);
    re4dc_log("re4dc_fault_init: dbgio -> ring, unhandled-exception handler set\n");
#if RE4DC_CRASH_SCREEN
    re4dc_crash_screen_init();
#endif
}
