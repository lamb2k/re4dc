/* testprog.c: the console loop's test program (lane eng-loop, 2026-11-19). Sent by consoleloop.py to the loader for
   the Flycast proof and the first console run; each word of the PC's --args picks a path back to the loader:

     report     (default) a few lines and DONE through cl_exit
     return     return from main (the atexit hand-in: DONE, exit 0)
     big:<n>    n more bytes of report (the report path under load)
     crash      a misaligned write: CRASHED with the registers, back through the preloaded loader
     hang       loop with interrupts on: the --deadline watchdog hands in TIMEOUT
     reboot     BIOS reboot without a hand-in: shows what GDEMU boots after a soft reboot (loader -> LOST)
     hangoff    interrupts off for ever: only a power cycle returns (the documented limit)
     preload0   skip the loader preload: crash / hang then go back by BIOS reboot

   It shows its state on screen so a photo tells which path ran. */
#include <kos.h>
#include <dc/biosfont.h>
#include <dc/video.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cl_client.h"
#include "cl_handoff.h"

int __real_cdrom_read_toc(cd_toc_t *toc, bool hd);
int __wrap_cdrom_read_toc(cd_toc_t *toc, bool hd) {
    int rc = __real_cdrom_read_toc(toc, true);
    return rc && !hd ? __real_cdrom_read_toc(toc, false) : rc;
}

static void say(int row, const char *s) {
    bfont_draw_str_ex(vram_s + (40 + row * 24) * 640 + 20, 640, 0xffe0, 0, 16, true, s);
}

static int has(const char *args, const char *w) { return strstr(args, w) != NULL; }

int main(int argc, char **argv) {
    (void)argc; (void)argv;
    vid_set_mode(DM_640x480, PM_RGB565);
    vid_clear(0, 0, 40);
    const char *args0 = "";
    /* cl_args reads the hand-off area; preload0 must be known before cl_init */
    const cl_handoff_t *h = (const cl_handoff_t *)CL_HANDOFF_ADDR;
    if (h->h.magic == CL_HANDOFF_MAGIC) args0 = h->h.args;
    const int active = cl_init(has(args0, "preload0") ? CL_NO_PRELOAD : 0);
    const char *args = cl_args();
    char line[64];
    say(0, "CONSOLE LOOP TEST PROGRAM");
    snprintf(line, sizeof(line), "RUN %08X  ACTIVE %d", (unsigned)cl_run_id(), active);
    say(1, line);
    snprintf(line, sizeof(line), "ARGS %.40s", args);
    say(2, line);
    if (!active) {
        say(4, "NOT STARTED BY THE LOADER. NOTHING TO DO.");
        for (;;) thd_sleep(1000);
    }
    cl_report("testprog run %08x args \"%s\"\n", (unsigned)cl_run_id(), args);
    cl_report("hand-off boot %u deadline %u s loader preloaded %u bytes\n", (unsigned)h->h.boot_count,
              (unsigned)h->h.deadline_s, (unsigned)h->h.loader_len);
    cl_report("timer %u ms since boot\n", (unsigned)timer_ms_gettime64());
    const char *big = strstr(args, "big:");
    if (big) {
        unsigned n = (unsigned)strtoul(big + 4, NULL, 10);
        char b[80];
        for (unsigned i = 0; i < n; i += 64) {
            snprintf(b, sizeof(b), "%08u the console loop report path carries this line...........\n", i);
            cl_report_bytes(b, n - i < 64 ? n - i : 64);
        }
    }
    if (has(args, "crash")) {
        say(4, "CRASH: MISALIGNED WRITE");
        thd_sleep(1500);
        volatile uint32_t *p = (volatile uint32_t *)0x8c100002u;
        *p = 0xdeadbeefu;
    }
    if (has(args, "hang") && !has(args, "hangoff")) {
        say(4, "HANG: WAITING FOR THE DEADLINE WATCHDOG");
        for (;;) thd_sleep(100);
    }
    if (has(args, "hangoff")) {
        say(4, "HANG WITH INTERRUPTS OFF: POWER CYCLE TO RETURN");
        thd_sleep(500);
        irq_disable();
        for (;;) {}
    }
    if (has(args, "reboot")) {
        say(4, "BIOS REBOOT, NO HAND-IN");
        thd_sleep(1500);
        arch_reboot();
    }
    if (has(args, "return")) {
        say(4, "RETURN FROM MAIN");
        thd_sleep(1500);
        return 0;
    }
    say(4, "DONE: BACK TO THE LOADER");
    thd_sleep(1500);
    cl_exit(0);
}
