/* cl_handoff.h: the hand-off area between the console-loop loader and the program it runs (lane eng-loop,
   2026-11-19; docs/engine/CONSOLE_LOOP.md section 4).

   The top 128 KiB of main RAM. KallistiOS puts the main thread's stack at the weak symbol arch_stack_16m and keeps
   the heap below stack - 64 KiB; the loader and every client program define arch_stack_16m = CL_HANDOFF_ADDR (and
   arch_stack_32m = CL_HANDOFF_ADDR + 16 MiB, so startup.S's 16/32 MB mirror test compares the same offset), so the
   area survives the jump to the program, the program's whole run, and the jump back. */
#ifndef CL_HANDOFF_H
#define CL_HANDOFF_H
#include <stdint.h>

#define CL_HANDOFF_ADDR 0x8cfe0000u
#define CL_HANDOFF_SIZE 0x20000u
#define CL_HANDOFF_MAGIC 0x31484c43u   /* "CLH1" */
#define CL_HANDOFF_VERSION 1

enum { CL_RUN_NONE = 0, CL_RUN_RUNNING = 1, CL_RUN_DONE = 2, CL_RUN_CRASHED = 3, CL_RUN_TIMEOUT = 4, CL_RUN_LOST = 5 };

#define CL_TRAMP_WORDS 32
typedef struct {
    uint32_t magic, version;
    uint32_t header_crc;          /* CRC-32 of the header from boot_count to the end of the header */
    uint32_t boot_count;          /* loader boots since the area was made (power-on resets it) */
    uint32_t run_id;              /* the PC's session of the program that runs / ran */
    uint32_t state;               /* CL_RUN_* */
    int32_t exit_code;
    uint32_t deadline_s;          /* 0 = none */
    uint32_t flags;
    uint32_t link_host, link_port, link_lport, console_ip;   /* the loader's link (network order host / ip) */
    char number[24];
    char args[512];               /* the PC's arguments, NUL-terminated */
    uint32_t crash_evt, crash_pc, crash_pr, crash_sp;
    uint32_t loader_len;          /* bytes of /cd/LOADER.BIN the client preloaded (diagnostic) */
    uint32_t report_len, report_crc;
    uint32_t reserved[9];
    uint32_t tramp[CL_TRAMP_WORDS];   /* scratch for the client's raw jump back (not covered by the CRC) */
    uint32_t tramp_stack[8];
} cl_handoff_hdr_t;

#define CL_HANDOFF_HDR_CRC_FROM 12u
#define CL_HANDOFF_HDR_CRC_TO ((uint32_t)__builtin_offsetof(cl_handoff_hdr_t, tramp))
#define CL_REPORT_MAX (CL_HANDOFF_SIZE - (uint32_t)sizeof(cl_handoff_hdr_t))

typedef struct {
    cl_handoff_hdr_t h;
    uint8_t report[CL_REPORT_MAX];
} cl_handoff_t;

#endif
