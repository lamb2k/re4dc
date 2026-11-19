/* main.c: the console-loop loader (lane eng-loop, 2026-11-19; docs/engine/CONSOLE_LOOP.md).

   Boots from its own GDEMU disc, dials the DreamPi (link.c, the QA link's transport), beacons HELLO on UDP 52060 and
   waits for the PC (tools/consoleloop/consoleloop.py). It receives a program in checked chunks (cl_core.c), verifies
   it whole (stream CRC-32, bounded inflate, SHA-256), and on RUN writes the hand-off area, hangs up and jumps to it
   with arch_exec_at. A program built with the client library (client.c) comes back here with its report.

   The screen says what it is doing, for a photo: link state, WAITING FOR THE PC with a turning marker, transfer
   progress, the verdict, the last run. A on the pad redials at once. */
#include <kos.h>
#include <arch/exec.h>
#include <dc/biosfont.h>
#include <dc/video.h>
#include <dc/maple.h>
#include <dc/maple/controller.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cl_core.h"
#include "link.h"

#ifndef LOADER_BUILD
#define LOADER_BUILD "dev"
#endif

/* the hand-off area: this program's stack and heap end below it (cl_handoff.h) */
uintptr_t arch_stack_16m = CL_HANDOFF_ADDR;
uintptr_t arch_stack_32m = CL_HANDOFF_ADDR + 0x1000000u;

/* /cd on a GD-ROM image: KOS mounts the low-density TOC; the payload is on track 3 (as engine/bench/main.c) */
int __real_cdrom_read_toc(cd_toc_t *toc, bool hd);
int __wrap_cdrom_read_toc(cd_toc_t *toc, bool hd) {
    int rc = __real_cdrom_read_toc(toc, true);
    return rc && !hd ? __real_cdrom_read_toc(toc, false) : rc;
}

/* ---------------------------------------------------------------- log lines (screen + dbglog) */
#define LOG_LINES 6
static char g_log[LOG_LINES][54];
static volatile unsigned g_log_n;
void loader_log(const char *fmt, ...) {
    char b[160];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(b, sizeof(b), fmt, ap);
    va_end(ap);
    dbglog(DBG_INFO, "loader: %s\n", b);
    const irq_mask_t irq = irq_disable();
    unsigned i = g_log_n++ % LOG_LINES;
    strncpy(g_log[i], b, sizeof(g_log[i]) - 1);
    g_log[i][sizeof(g_log[i]) - 1] = 0;
    irq_restore(irq);
}

/* ---------------------------------------------------------------- platform for cl_core */
static int p_send(void *ctx, const uint8_t *p, size_t n) { (void)ctx; return link_send(p, (unsigned)n); }
static uint32_t p_now(void *ctx) { (void)ctx; return (uint32_t)timer_ms_gettime64(); }
static void *p_alloc(size_t n) {
    uint8_t *m = (uint8_t *)malloc(n);
    if (m && (uintptr_t)m + n > CL_HANDOFF_ADDR - 0x11000u) { free(m); return NULL; }   /* never near the hand-off */
    return m;
}
static void p_free(void *m) { free(m); }
static void p_log(void *ctx, const char *line) { (void)ctx; loader_log("%s", line); }

static cl_core_t g_core;
static cl_platform_t g_plat;

/* ---------------------------------------------------------------- settings: /cd/LINK.TXT */
static void read_settings(char *number, char *host, unsigned *port, unsigned *lport) {
    FILE *f = fopen("/cd/LINK.TXT", "r");
    if (!f) f = fopen("/cd/link.txt", "r");
    if (!f) { loader_log("no LINK.TXT: defaults"); return; }
    char line[96], k[24], v[64];
    while (fgets(line, sizeof(line), f)) {
        if (sscanf(line, "%23s %63s", k, v) != 2 || k[0] == '#') continue;
        if (!strcmp(k, "number")) { strncpy(number, v, 23); number[23] = 0; }
        else if (!strcmp(k, "host")) { strncpy(host, v, 31); host[31] = 0; }
        else if (!strcmp(k, "port")) *port = (unsigned)atoi(v);
        else if (!strcmp(k, "lport")) *lport = (unsigned)atoi(v);
    }
    fclose(f);
}

/* ---------------------------------------------------------------- screen */
static void line_at(int row, uint32_t colour, const char *fmt, ...) {
    char b[64];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(b, sizeof(b), fmt, ap);
    va_end(ap);
    if (n < 0) n = 0;
    for (int i = n; i < 53; ++i) b[i] = ' ';   /* pad: the old text goes */
    b[53] = 0;
    bfont_draw_str_ex(vram_s + (8 + row * 24) * 640 + 4, 640, colour, 0, 16, true, b);
}

static const char *run_state_name(uint32_t s) {
    static const char *n[] = {"NONE", "RUNNING", "DONE", "CRASHED", "TIMEOUT", "LOST (NO HAND-IN)"};
    return s < 6 ? n[s] : "?";
}

static void draw(unsigned frame, uint32_t rate_Bps) {
    enum { WHITE = 0xffff, GREY = 0x8410, GREEN = 0x07e0, YELLOW = 0xffe0, RED = 0xf800, CYAN = 0x07ff };
    char t[64];
    line_at(0, CYAN, "RE4DC CONSOLE LOOP LOADER  %s", LOADER_BUILD);
    line_at(1, GREY, "BOOT %u   PORT %u   HAND-OFF %08X", (unsigned)g_core.boot_count, link_port(),
            (unsigned)CL_HANDOFF_ADDR);
    link_text(t, sizeof(t));
    line_at(3, link_state() == LINK_UP ? GREEN : YELLOW, "LINK: %s", t);
    static const char spin[4] = {'|', '/', '-', '\\'};
    const cl_core_t *c = &g_core;
    if (link_state() != LINK_UP) {
        line_at(5, YELLOW, "NOT CONNECTED: A = DIAL NOW");
        line_at(6, GREY, "");
    } else if (c->state == CL_ST_RECEIVING) {
        line_at(5, WHITE, "RECEIVING %08X: %u / %u CHUNKS", (unsigned)c->session, (unsigned)c->have, (unsigned)c->nchunks);
        line_at(6, WHITE, "%u OF %u KB   %u.%02u KB/S   BAD %u DUP %u", (unsigned)(c->have * CL_CHUNK / 1024),
                (unsigned)(c->comp_len / 1024), (unsigned)(rate_Bps / 1000), (unsigned)(rate_Bps % 1000 / 10),
                (unsigned)c->rx_bad, (unsigned)c->rx_dup);
    } else if (c->state == CL_ST_VERIFIED) {
        line_at(5, GREEN, "VERIFIED %08X: %u BYTES, SHA-256 OK", (unsigned)c->session, (unsigned)c->raw_len);
        line_at(6, GREEN, "WAITING FOR RUN %c", spin[frame & 3]);
    } else if (c->state == CL_ST_FAILED) {
        line_at(5, RED, "REFUSED %08X: %s", (unsigned)c->session, cl_err_name(c->verdict));
        line_at(6, YELLOW, "NOTHING RAN. WAITING FOR THE PC %c", spin[frame & 3]);
    } else {
        line_at(5, GREEN, "WAITING FOR THE PC %c", spin[frame & 3]);
        line_at(6, GREY, "BEACONS SENT %u   RECEIVED %u", (unsigned)c->tx_pkts, (unsigned)c->rx_pkts);
    }
    const cl_handoff_hdr_t *h = &g_plat.handoff->h;
    line_at(8, GREY, "LAST RUN %08X: %s", (unsigned)h->run_id, run_state_name(h->state));
    if (h->state == CL_RUN_CRASHED)
        line_at(9, RED, "EXC %03X PC %08X PR %08X", (unsigned)h->crash_evt, (unsigned)h->crash_pc, (unsigned)h->crash_pr);
    else
        line_at(9, GREY, "EXIT %d   REPORT %u BYTES", (int)h->exit_code, (unsigned)h->report_len);
    unsigned tx, rx, txd, rxd;
    link_counters(&tx, &rx, &txd, &rxd);
    line_at(11, GREY, "LINK BYTES OUT %u IN %u DROPS %u/%u", tx, rx, txd, rxd);
    unsigned n = g_log_n;
    for (unsigned i = 0; i < LOG_LINES; ++i) {
        unsigned k = n >= LOG_LINES ? n - LOG_LINES + i : i;
        line_at(13 + (int)i, GREY, "%s", k < n ? g_log[k % LOG_LINES] : "");
    }
}

static int pad_a(void) {
    maple_device_t *d = maple_enum_type(0, MAPLE_FUNC_CONTROLLER);
    if (!d) return 0;
    cont_state_t *s = (cont_state_t *)maple_dev_status(d);
    return s && (s->buttons & CONT_A);
}

/* ---------------------------------------------------------------- the jump */
static void do_exec(void) {
    cl_core_t *c = &g_core;
    loader_log("exec %08x: %u bytes", (unsigned)c->session, (unsigned)c->raw_len);
    line_at(5, 0xffe0, "RUNNING %08X: %u BYTES", (unsigned)c->session, (unsigned)c->raw_len);
    line_at(6, 0x8410, "HANGING UP, THEN JUMPING");
    /* let EXEC leave: the ring, then the modem's buffer */
    uint64_t t0 = timer_ms_gettime64();
    while (link_tx_queued() && timer_ms_gettime64() - t0 < 2000) thd_sleep(20);
    thd_sleep(600);
    link_stop();
    t0 = timer_ms_gettime64();
    while ((link_busy() || link_state() != LINK_OFF) && timer_ms_gettime64() - t0 < 8000) thd_sleep(50);
    arch_exec_at(c->raw, (c->raw_len + 3) & ~3u, CL_LOAD_ADDR);
}

int main(int argc, char **argv) {
    (void)argc; (void)argv;
    vid_set_mode(DM_640x480, PM_RGB565);
    vid_clear(0, 0, 0);
    char number[24] = "1111111", host[32] = "peer";
    unsigned port = CL_PORT, lport = CL_PORT;
    read_settings(number, host, &port, &lport);
    link_config(number, host, port, lport);
    memset(&g_plat, 0, sizeof(g_plat));
    g_plat.send = p_send; g_plat.now_ms = p_now; g_plat.alloc = p_alloc; g_plat.free = p_free; g_plat.log = p_log;
    g_plat.handoff = (cl_handoff_t *)CL_HANDOFF_ADDR;
    g_plat.max_raw = CL_HANDOFF_ADDR - 0x11000u - CL_LOAD_ADDR;
    g_plat.number = link_number();
    g_plat.build = "loader " LOADER_BUILD;
    cl_core_init(&g_core, &g_plat);
    loader_log("number %s host %s port %u lport %u", number, host, port, lport);
    link_start();
    uint64_t next_dial = 0, last_draw = 0, rate_t = 0;
    uint32_t rate_have = 0, rate = 0;
    unsigned frame = 0;
    int was_up = 0, a_was = 0;
    static uint8_t buf[1408];
    for (;;) {
        const uint64_t now = timer_ms_gettime64();
        const int st = link_state();
        if (st == LINK_UP) {
            if (!was_up) {
                /* the platform's view of the link, for HELLO and the hand-off area */
                g_core.p.console_ip = link_console_ip();
                g_core.p.link_host = link_host(); g_core.p.link_port = link_port(); g_core.p.link_lport = link_lport();
                was_up = 1;
            }
            int n;
            while ((n = link_recv(buf, sizeof(buf))) >= 0) {
                if (n > 0) cl_core_input(&g_core, buf, (size_t)n);
                if (g_core.exec_pending) break;
            }
            cl_core_tick(&g_core);
        } else {
            was_up = 0;
            if (!link_busy() && (st == LINK_OFF || st == LINK_FAILED || st == LINK_DROPPED)) {
                if (st == LINK_DROPPED || now >= next_dial) {
                    loader_log("dialling (%s)", st == LINK_DROPPED ? "line dropped" : st == LINK_FAILED ? "retry" : "start");
                    link_start();
                    next_dial = now + 30000;
                }
            }
        }
        if (g_core.exec_pending) do_exec();
        const int a = pad_a();
        if (a && !a_was && st != LINK_UP) next_dial = 0;
        a_was = a;
        if (now - rate_t >= 2000) {
            rate = g_core.have >= rate_have ? (uint32_t)((g_core.have - rate_have) * CL_CHUNK * 1000ull / (now - rate_t)) : 0;
            rate_have = g_core.have;
            rate_t = now;
        }
        if (now - last_draw >= 250) {
            draw(frame++, rate);
            last_draw = now;
        }
        thd_sleep(10);
    }
}
