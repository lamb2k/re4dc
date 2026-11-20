/* cl_send.c: makes an engine image send-able through the console loop without touching its sources (lane eng-loop2,
   2026-11-20; docs/engine/CONSOLE_LOOP.md section 10). Linked by loader/sendable.mk (SENDABLE=1) next to client.c.

   Booted from its own disc the image runs as before: cl_init() finds no RUNNING hand-off and every piece below stays
   off. Started by the loader, a constructor (after KallistiOS has mounted /cd, before main) turns on:
    - the report: a dbgio handler in front of the selected one copies the program's own text output (printf, dbglog)
      into the hand-off report, line by line, and passes everything on unchanged (serial still works);
    - the end: the image's own last line (CL_SEND_END, e.g. "SCHEDULE DONE", "E1 END") hands in DONE, exit 0; a
      refusal line (CL_SEND_FAIL) hands in DONE, exit 1. A deadline from the PC still hands in TIMEOUT;
    - the data root: the loader disc holds each image's files in a folder; "root=E1" in the PC's arguments makes
      /cd/<path> open /cd/E1/<path> first (then /cd/<path>), through fs_open (-Wl,--wrap=fs_open). "root=E1H:E1"
      tries E1H, then E1, then the disc root.
   PC arguments (consoleloop.py run --args "..."): root=<dir>[:<dir>...], rows=skip|compact|keep (default compact),
   skip=<prefix>[,<prefix>...] (default T: the E1 trace lines). Lines starting "ROW " are per-picture rows: compact
   drops their alphabetic field names; rows may fill the report only up to CL_ROW_BUDGET so the summary lines after
   them still fit. The report ends with a "cl-send:" line counting what was dropped. */
#include <kos.h>
#include <kos/dbgio.h>
#include <kos/fs.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cl_client.h"
#include "cl_core.h"
#include "cl_handoff.h"

#ifndef CL_SEND_END
#define CL_SEND_END "SCHEDULE DONE|E1 END"
#endif
#ifndef CL_SEND_FAIL
/* the bench's refusals; the E1 images' file and pack failures (the E1 image goes on headless when its pack is refused,
   and would hand in a run without drawing; a headless scene asks for it with the HEADLESS root file instead) */
#define CL_SEND_FAIL "SCHEDULE REFUSED|M1 native pack REFUSED|E1 draw: renderer refused|E1 load: missing|E1 load: read failed|E1 load: bad DRS"
#endif
#define H ((cl_handoff_t *)CL_HANDOFF_ADDR)
#define CL_CAP CL_REPORT_CAP(&H->h)
#define CL_ROW_BUDGET (CL_CAP - 20u * 1024u)

static dbgio_handler_t *g_prev;
static char g_line[320];
static unsigned g_len, g_lines, g_kept, g_dropped_rows, g_dropped_skip, g_dropped_full, g_truncated;
static int g_rows = 1;                      /* 0 skip, 1 compact, 2 keep */
static char g_skip[8][16];
static unsigned g_nskip = 1;
static char g_root[4][24];
static unsigned g_nroot;
static volatile int g_end = -1;             /* exit code once an end line was seen */
static semaphore_t g_end_sem = SEM_INITIALIZER(0);
static volatile uint64_t g_last_ms;         /* when the program last printed */

static int starts(const char *s, const char *p) { return strncmp(s, p, strlen(p)) == 0; }

/* "a|b|c": does the line start with any of them */
static int match_list(const char *line, const char *list) {
    /* no strtok: this runs inside any thread's printf, and strtok would clobber that thread's own tokenizer */
    for (const char *t = list; *t;) {
        const char *e = strchr(t, '|');
        const size_t n = e ? (size_t)(e - t) : strlen(t);
        if (n && !strncmp(line, t, n)) return 1;
        t += n + (e ? 1 : 0);
    }
    return 0;
}

static void keep(const char *s, unsigned n) {
    cl_report_bytes(s, n);
    ++g_kept;
}

static void line_done(void) {
    g_line[g_len] = 0;
    const char *l = g_line;
    ++g_lines;
    if (g_end < 0) {
        if (match_list(l, CL_SEND_END)) g_end = 0;
        else if (match_list(l, CL_SEND_FAIL)) g_end = 1;
        if (g_end >= 0) sem_signal(&g_end_sem);   /* wakes the ender (it sleeps until then: no polling) */
    }
    for (unsigned i = 0; i < g_nskip; ++i)
        if (g_skip[i][0] && starts(l, g_skip[i]) && l[strlen(g_skip[i])] == ' ') { ++g_dropped_skip; return; }
    const uint32_t used = H->h.report_len;
    if (starts(l, "ROW ")) {
        if (g_rows == 0 || used + g_len > CL_ROW_BUDGET) { ++g_dropped_rows; return; }
        if (g_rows == 1) {   /* compact: drop the purely alphabetic tokens (the field names) */
            char c[sizeof(g_line)];
            unsigned n = 0;
            const char *p = l;
            int first = 1;
            while (*p) {
                while (*p == ' ') ++p;
                const char *t = p;
                int alpha = 1;
                while (*p && *p != ' ' && *p != '\n') { if (!((*p >= 'a' && *p <= 'z') || (*p >= 'A' && *p <= 'Z'))) alpha = 0; ++p; }
                if (p > t && (first || !alpha)) {
                    if (n && n < sizeof(c) - 1) c[n++] = ' ';
                    for (const char *q = t; q < p && n < sizeof(c) - 2; ++q) c[n++] = *q;
                }
                first = 0;
                if (*p == '\n') break;
            }
            c[n++] = '\n';
            keep(c, n);
            return;
        }
    }
    if (used + g_len > CL_CAP - 256u) { ++g_dropped_full; return; }   /* room for the closing line */
    keep(l, g_len);
}

static int tee_write(const uint8_t *data, int len, int xlat) {
    if (cl_active() && data && len > 0) {
        g_last_ms = timer_ms_gettime64();
        const irq_mask_t irq = irq_disable();
        for (int i = 0; i < len; ++i) {
            const char ch = (char)data[i];
            if (ch == '\r') continue;
            if (g_len < sizeof(g_line) - 2) g_line[g_len++] = ch;
            else if (ch != '\n') { ++g_truncated; continue; }
            else g_line[g_len++] = ch;
            if (ch == '\n') { line_done(); g_len = 0; }
        }
        irq_restore(irq);
    }
    return g_prev ? g_prev->write_buffer(data, len, xlat) : len;
}
static int tee_detected(void) { return 1; }
static int tee_init(void) { return 0; }
static int tee_shutdown(void) { return g_prev ? g_prev->shutdown() : 0; }
static int tee_set_irq_usage(int mode) { return g_prev ? g_prev->set_irq_usage(mode) : 0; }
static int tee_flush(void) { return g_prev ? g_prev->flush() : 0; }
static int tee_read_buffer(uint8_t *data, int len) { return g_prev ? g_prev->read_buffer(data, len) : -1; }
static dbgio_handler_t g_tee = {.name = "cl-tee", .detected = tee_detected, .init = tee_init, .shutdown = tee_shutdown,
                                .set_irq_usage = tee_set_irq_usage, .flush = tee_flush, .write_buffer = tee_write,
                                .read_buffer = tee_read_buffer};

/* ---------------------------------------------------------------- /cd/<root>/ first (-Wl,--wrap=fs_open) */
file_t __real_fs_open(const char *fn, int mode);
file_t __wrap_fs_open(const char *fn, int mode) {
    if (g_nroot && fn && starts(fn, "/cd/") && !starts(fn, "/cd/LOADER.BIN")) {
        char p[256];
        for (unsigned i = 0; i < g_nroot; ++i) {
            snprintf(p, sizeof(p), "/cd/%s/%s", g_root[i], fn + 4);
            const file_t f = __real_fs_open(p, mode);
            if (f >= 0) return f;
        }
    }
    return __real_fs_open(fn, mode);
}

static void parse_args(const char *a) {
    g_nskip = 1;
    strcpy(g_skip[0], "T");
    char b[512];
    strncpy(b, a, sizeof(b) - 1);
    b[sizeof(b) - 1] = 0;
    for (char *t = strtok(b, " "); t; t = strtok(NULL, " ")) {
        if (starts(t, "root=")) {
            g_nroot = 0;
            for (char *r = t + 5; *r && g_nroot < 4;) {
                char *e = strchr(r, ':');
                const size_t n = e ? (size_t)(e - r) : strlen(r);
                if (n && n < sizeof(g_root[0])) { memcpy(g_root[g_nroot], r, n); g_root[g_nroot][n] = 0; ++g_nroot; }
                r += n + (e ? 1 : 0);
            }
        } else if (!strcmp(t, "rows=skip")) g_rows = 0;
        else if (!strcmp(t, "rows=compact")) g_rows = 1;
        else if (!strcmp(t, "rows=keep")) g_rows = 2;
        else if (starts(t, "skip=")) {
            g_nskip = 0;
            for (char *r = t + 5; *r && g_nskip < 8;) {
                char *e = strchr(r, ',');
                const size_t n = e ? (size_t)(e - r) : strlen(r);
                if (n && n < sizeof(g_skip[0])) { memcpy(g_skip[g_nskip], r, n); g_skip[g_nskip][n] = 0; ++g_nskip; }
                r += n + (e ? 1 : 0);
            }
        }
    }
}

static void *ender(void *arg) {
    (void)arg;
    while (g_end < 0) sem_wait(&g_end_sem);
    /* the lines after the end line (the boss and fight images print their event and effect lists after "E1 END"):
       hand in once the program has printed nothing for 1.5 s */
    do thd_sleep(500); while (timer_ms_gettime64() - g_last_ms < 1500);
    cl_report("cl-send: lines %u kept %u rows dropped %u skipped %u dropped when full %u cut long %u, end code %d\n",
              g_lines, g_kept, g_dropped_rows, g_dropped_skip, g_dropped_full, g_truncated, g_end);
    cl_exit(g_end);
}

extern struct dbgio_handlers_list dbgio_handlers;
static void __attribute__((constructor)) cl_send_start(void) {
    if (!cl_init(0)) return;
    parse_args(cl_args());
    cl_report("cl-send: run %08x args \"%s\" roots %u rows %d\n", (unsigned)cl_run_id(), cl_args(), g_nroot, g_rows);
    const char *cur = dbgio_dev_get();
    dbgio_handler_t *h;
    SLIST_FOREACH(h, &dbgio_handlers, entry)
        if (cur && !strcmp(h->name, cur)) g_prev = h;
    dbgio_add_handler(&g_tee);
    if (dbgio_dev_select("cl-tee") < 0) cl_report("cl-send: dbgio tee refused: no text report\n");
    kthread_attr_t a;
    memset(&a, 0, sizeof(a));
    a.create_detached = true;
    a.prio = PRIO_DEFAULT;
    a.label = "cl-send-end";
    thd_create_ex(&a, ender, NULL);
}
