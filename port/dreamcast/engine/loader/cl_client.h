/* cl_client.h: the console-loop client library, for programs the loader runs (lane eng-loop, 2026-11-19).

   Link client.c, cl_util.c and cl_core.c's hand-off helpers (cl_util.c holds them) into the program. Linking client.c
   also lowers the program's RAM top to the hand-off area (arch_stack_16m), so the report survives the program.

     int main() {
         cl_init(0);                         // 1 = started by the loader; 0 = booted any other way (all calls no-op)
         const char *args = cl_args();       // the PC's --args
         ... cl_report("cross mean %u us\n", mean); ...
         cl_exit(0);                         // DONE, back to the loader with the report
     }

   Returning from main also hands in (DONE, exit code 0). A crash (unhandled exception, double fault) hands in
   CRASHED with the registers; the PC's --deadline hands in TIMEOUT from a watchdog thread. The way back: the loader
   image preloaded from /cd/LOADER.BIN at cl_init (needs /cd: on a GD image the program needs the cdrom_read_toc wrap,
   as engine/bench/main.c), copied down with KallistiOS's own exec trampoline; without it, a BIOS reboot.
   Build with -DCL_WRAP_ABORT and link with -Wl,--wrap=arch_abort to catch panics and failed asserts as well. */
#ifndef CL_CLIENT_H
#define CL_CLIENT_H
#include <stddef.h>
#include <stdint.h>

#define CL_NO_PRELOAD 1u     /* cl_init flag: do not read /cd/LOADER.BIN (crash and deadline then reboot via BIOS) */

int cl_init(unsigned flags);
int cl_active(void);
const char *cl_args(void);
uint32_t cl_run_id(void);
void cl_report(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
void cl_report_bytes(const void *p, size_t n);
void cl_exit(int code) __attribute__((noreturn));
#endif
