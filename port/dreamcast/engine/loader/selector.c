/* selector.c: the console disc's scene runner (lane eng-loop2, 2026-11-20; docs/engine/CONSOLE_LOOP.md section 10).

   One GDEMU disc holds every engine scene: each engine image is a program file under /cd/PROG, built with the
   console loop's client library (SENDABLE=1, loader/sendable.mk). This program is the disc's 1ST_READ.BIN and its
   /cd/LOADER.BIN at once. For each scene of /cd/SCENES.TXT, in order, it checks the scene's files, writes the hand-off
   area (RUNNING, the scene's arguments and deadline) and jumps to the program, as the loader does after RUN. The
   program runs from its own folder on the disc (root=<dir>), and hands back through the client library (its end
   line, a refusal, a crash, or the deadline): the program's way back is /cd/LOADER.BIN, which is this program again.
   It reads the report, keeps the scene's summary rows in a journal at the top of the hand-off area (above the
   report cap it gives every program), and runs the next scene. After the last scene it shows the summary on screen,
   in pages, for a photo, and prints it on the serial line.

   /cd/SCENES.TXT, one scene a line ('#' comments):
     <name> <title, '_' for spaces> <program> <deadline s> <kind> <files that must exist, ',' separated, or -> <args>
   kind bench: the summary is the bench's own WINDOW rows (mean, p99, worst, over 14, over 33.3, presented intervals
   over two fields; 600 pictures a window). kind e1: the summary is computed here from the image's ROW lines, pictures
   41 to 640 (600; the lane tools' budget.py rows): drawing, busy picture (frame less the pacer's and PVR waits),
   services, behaviour, and intervals over two fields.

   A scene is FAILED, never skipped, when: a file is missing, the program cannot be read, it crashed, it ran into its
   deadline, it came back without handing in (LOST), it handed in a non-zero exit, its report fails its CRC, its report
   holds a refusal line, or it gave no rows. B held on the first controller while this screen counts down skips the
   next scene (recorded as FAILED, "skipped by the owner").

   A reset or power cycle during the run: if main RAM kept the journal, the scene that was running is recorded LOST and
   the run goes on with the next; otherwise the run starts again. After the summary is shown the journal is closed, so
   the next reset starts a new run. */
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

#ifndef LOADER_BUILD
#define LOADER_BUILD "dev"
#endif

/* this program's stack and heap end below the hand-off area, as the loader's (cl_handoff.h) */
uintptr_t arch_stack_16m = CL_HANDOFF_ADDR;
uintptr_t arch_stack_32m = CL_HANDOFF_ADDR + 0x1000000u;

int __real_cdrom_read_toc(cd_toc_t *toc, bool hd);
int __wrap_cdrom_read_toc(cd_toc_t *toc, bool hd) {
    int rc = __real_cdrom_read_toc(toc, true);
    return rc && !hd ? __real_cdrom_read_toc(toc, false) : rc;
}

#define H ((cl_handoff_t *)CL_HANDOFF_ADDR)
#define SEL_JOURNAL_SIZE (24u * 1024u)
#define SEL_JOURNAL_ADDR (CL_HANDOFF_ADDR + CL_HANDOFF_SIZE - SEL_JOURNAL_SIZE)
#define SEL_REPORT_CAP (CL_REPORT_MAX - SEL_JOURNAL_SIZE)
#define SEL_MAGIC 0x314c4553u   /* "SEL1" */
#define SEL_MAX 8
#define SEL_SUM 2560

enum { E_PENDING = 0, E_OK = 1, E_FAILED = 2 };
typedef struct {
    uint32_t state, run_state;
    int32_t exit_code;
    uint32_t crash_evt, crash_pc, report_len, report_ok, rows;
    char why[72];
    char sum[SEL_SUM];   /* summary lines, '\n' separated */
} sel_entry_t;
typedef struct {
    uint32_t magic, crc;          /* crc: CRC-32 from plan_crc to the end */
    uint32_t plan_crc, nonce, n, next, running, boots;
    sel_entry_t e[SEL_MAX];
} sel_journal_t;
_Static_assert(sizeof(sel_journal_t) <= SEL_JOURNAL_SIZE, "journal too large");
#define J ((sel_journal_t *)SEL_JOURNAL_ADDR)

typedef struct {
    char name[16], title[48], prog[40], kind[8], need[256], args[256];
    unsigned deadline;
} scene_t;
static scene_t g_sc[SEL_MAX];
static unsigned g_n;
static uint32_t g_plan_crc;

static uint32_t journal_crc(void) {
    return cl_crc32(0, (const uint8_t *)J + 8, sizeof(sel_journal_t) - 8);
}
static void journal_seal(void) {
    J->magic = SEL_MAGIC;
    J->crc = journal_crc();
}

/* ---------------------------------------------------------------- screen */
enum { WHITE = 0xffff, GREY = 0x8410, GREEN = 0x07e0, YELLOW = 0xffe0, RED = 0xf800, CYAN = 0x07ff };
static void line_at(int row, uint32_t colour, const char *fmt, ...) {
    char b[64];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(b, sizeof(b), fmt, ap);
    va_end(ap);
    if (n < 0) n = 0;
    if (n > 53) n = 53;
    for (int i = n; i < 53; ++i) b[i] = ' ';
    b[53] = 0;
    bfont_draw_str_ex(vram_s + (8 + row * 24) * 640 + 4, 640, colour, 0, 16, true, b);
}

static int pad_held(uint32_t button) {
    maple_device_t *d = maple_enum_type(0, MAPLE_FUNC_CONTROLLER);
    if (!d) return 0;
    cont_state_t *s = (cont_state_t *)maple_dev_status(d);
    return s && (s->buttons & button);
}

/* ---------------------------------------------------------------- the plan */
static int read_plan(void) {
    FILE *f = fopen("/cd/SCENES.TXT", "rb");
    if (!f) return 0;
    static char text[4096];
    size_t n = fread(text, 1, sizeof(text) - 1, f);
    fclose(f);
    text[n] = 0;
    g_plan_crc = cl_crc32(0, text, n);
    for (char *l = text; l && *l && g_n < SEL_MAX;) {
        char *e = strchr(l, '\n');
        if (e) *e = 0;
        char *r = strchr(l, '\r');
        if (r) *r = 0;
        scene_t *s = &g_sc[g_n];
        int used = 0;
        if (*l && *l != '#' &&
            sscanf(l, "%15s %47s %39s %u %7s %255s %n", s->name, s->title, s->prog, &s->deadline, s->kind, s->need, &used) >= 6) {
            snprintf(s->args, sizeof(s->args), "%s", used ? l + used : "");
            for (char *t = s->title; *t; ++t) if (*t == '_') *t = ' ';
            ++g_n;
        }
        l = e ? e + 1 : NULL;
    }
    return (int)g_n;
}

static int file_exists(const char *rel) {
    char p[128];
    snprintf(p, sizeof(p), "/cd/%s", rel);
    file_t f = fs_open(p, O_RDONLY);
    if (f < 0) return 0;
    fs_close(f);
    return 1;
}

/* ---------------------------------------------------------------- summaries from the report */
static void sum_add(sel_entry_t *e, const char *fmt, ...) {
    size_t len = strlen(e->sum);
    if (len + 2 >= sizeof(e->sum)) return;
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(e->sum + len, sizeof(e->sum) - len - 1, fmt, ap);
    va_end(ap);
    len = strlen(e->sum);
    e->sum[len] = '\n';
    e->sum[len + 1] = 0;
}

static const char *const FAIL_MARKS[] = {"SCHEDULE REFUSED", "M1 native pack REFUSED", "M1 missing pack", "STACK GUARD BROKEN", "E1 draw: renderer refused",
                                         "E1 load: missing", "E1 load: read failed", "E1 load: bad DRS", "CRASH event",
                                         "ABORT", "DEADLINE", NULL};

/* the value after the keyword (first match at or after *from) */
static const char *after(const char *line, const char *key) {
    const char *p = strstr(line, key);
    if (!p) return NULL;
    p += strlen(key);
    while (*p == ' ') ++p;
    return p;
}

/* bench WINDOW line: "WINDOW 0 CROSS arm 0 [novis] [delay5] [hold300] draw mean 12.910 p99 17.800 worst 17.800 (picture ..)
   over14 172 over33.3 0 wait .. flips 600 intervals>2 0 worst 2 fields (picture ..) .. content [L3] counts .." */
static void bench_window(sel_entry_t *e, const char *l) {
    unsigned w = 0;
    char room[12] = "?";
    sscanf(l, "WINDOW %u %11s", &w, room);
    const char *a = after(l, " arm "), *m = after(l, " mean "), *p = after(l, " p99 "), *wo = after(l, " p99 ");
    if (wo) wo = after(wo, " worst ");
    const char *o14 = after(l, " over14 "), *o33 = after(l, " over33.3 "), *iv = after(l, " intervals>2 ");
    const char *ct = after(l, " content ");
    char flags[4] = "", cs[16] = "";
    if (strstr(l, " novis")) strcat(flags, "n");
    if (strstr(l, " delay5")) strcat(flags, "d");
    if (strstr(l, " hold300")) strcat(flags, "h");
    if (ct && *ct == '[') { sscanf(ct + 1, "%15[^]]", cs); }
    sum_add(e, "%c%c%-2s m%.2f p%.2f w%.2f >14:%u >33:%u f>2:%u %s", room[0], a ? *a : '?', flags, m ? atof(m) : -1.0,
            p ? atof(p) : -1.0, wo ? atof(wo) : -1.0, o14 ? (unsigned)atoi(o14) : 999u, o33 ? (unsigned)atoi(o33) : 999u,
            iv ? (unsigned)atoi(iv) : 999u, cs);
    (void)w;
}

/* e1 ROW lines (compact: "ROW n in tick svc trace draw wait frame fields pl obj cam pvr ..."), pictures 41..640 */
#define E1_FIRST 41u
#define E1_COUNT 600u
static uint32_t g_v[5][E1_COUNT];
static uint32_t g_fields[E1_COUNT];
static unsigned g_rows, g_last_row, g_late;
static void e1_row(const char *l) {
    unsigned long v[14];
    int k = 0;
    const char *p = l + 4;
    while (k < 14 && *p) {
        char *end;
        unsigned long x = strtoul(p, &end, 10);
        if (end == p) break;
        v[k++] = x;
        p = end;
    }
    if (k < 13) return;
    const unsigned n = (unsigned)v[0];
    if (n > g_last_row) g_last_row = n;
    if (n < E1_FIRST || n >= E1_FIRST + E1_COUNT) return;
    const unsigned i = n - E1_FIRST;
    const uint32_t tick = (uint32_t)v[2], svc = (uint32_t)v[3], draw = (uint32_t)v[5], wait = (uint32_t)v[6];
    const uint32_t frame = (uint32_t)v[7], pvr = (uint32_t)v[12];
    g_v[0][i] = draw;
    g_v[1][i] = frame > wait + pvr ? frame - wait - pvr : 0;   /* busy picture */
    g_v[2][i] = svc;
    g_v[3][i] = tick > svc ? tick - svc : 0;                  /* behaviour */
    g_fields[i] = (uint32_t)v[8];
    g_late += wait == 0;   /* the 30 Hz pacer had no time left to wait: the picture was late */
    ++g_rows;
}
static int cmp_u32(const void *a, const void *b) {
    const uint32_t x = *(const uint32_t *)a, y = *(const uint32_t *)b;
    return (x > y) - (x < y);
}
static void e1_summary(sel_entry_t *e) {
    static const char *const names[4] = {"draw", "busy", "svc", "behav"};
    static const uint32_t budget_us[4] = {14000, 33333, 9000, 2000};
    static uint32_t s[E1_COUNT];
    const unsigned n = g_rows;
    sum_add(e, "pictures %u (%u-%u of %u ticks) ms:", n, E1_FIRST, E1_FIRST + n - 1, g_last_row);
    if (!n) return;
    for (unsigned r = 0; r < 4; ++r) {
        uint64_t sum = 0;
        unsigned worst = 0, wi = 0, over = 0;
        for (unsigned i = 0; i < n; ++i) {
            const uint32_t x = g_v[r][i];
            s[i] = x;
            sum += x;
            if (x > worst) { worst = x; wi = i; }
            over += x > budget_us[r];
        }
        qsort(s, n, 4, cmp_u32);
        const unsigned p99 = s[(unsigned)(0.99 * n) < n ? (unsigned)(0.99 * n) : n - 1];
        sum_add(e, "%-5s m%u.%02u p%u.%02u w%u.%02u@%u >%u.%u:%u", names[r], (unsigned)(sum / n / 1000),
                (unsigned)(sum / n % 1000 / 10), p99 / 1000, p99 % 1000 / 10, worst / 1000, worst % 1000 / 10,
                wi + E1_FIRST, budget_us[r] / 1000, budget_us[r] % 1000 / 100, over);
    }
    unsigned iv = 0, wf = 0, wfi = 0;
    for (unsigned i = 0; i < n; ++i) {
        if (g_fields[i] > 2) ++iv;
        if (g_fields[i] > wf) { wf = g_fields[i]; wfi = i; }
    }
    /* the E1 images print a fields column but do not count presented fields yet (all 0): say so, never "0 over" */
    if (wf) sum_add(e, "late %u; intervals>2 fields %u, worst %u@%u", g_late, iv, wf, wfi + E1_FIRST);
    else sum_add(e, "late (no pacer wait) %u; fields not counted", g_late);
}

static void collect(unsigned i) {
    sel_entry_t *e = &J->e[i];
    const scene_t *s = &g_sc[i];
    memset(e, 0, sizeof(*e));
    const int hv = cl_handoff_valid(H) && H->h.run_id == J->nonce + i;
    e->run_state = hv ? H->h.state : CL_RUN_LOST;
    e->exit_code = hv ? H->h.exit_code : 0;
    e->crash_evt = hv ? H->h.crash_evt : 0;
    e->crash_pc = hv ? H->h.crash_pc : 0;
    e->report_ok = hv && cl_handoff_report_ok(H);
    e->report_len = hv ? H->h.report_len : 0;
    if (!hv || H->h.state == CL_RUN_RUNNING) {
        e->run_state = CL_RUN_LOST;
        snprintf(e->why, sizeof(e->why), "LOST: came back without handing in");
    } else if (H->h.state == CL_RUN_CRASHED) {
        snprintf(e->why, sizeof(e->why), "CRASHED exc %03x pc %08x", (unsigned)e->crash_evt, (unsigned)e->crash_pc);
    } else if (H->h.state == CL_RUN_TIMEOUT) {
        snprintf(e->why, sizeof(e->why), "TIMEOUT after %u s", s->deadline);
    } else if (!e->report_ok) {
        snprintf(e->why, sizeof(e->why), "report CRC bad");
    } else if (e->exit_code) {
        snprintf(e->why, sizeof(e->why), "exit %d", (int)e->exit_code);
    }
    /* the report: refusal lines and rows */
    g_rows = g_last_row = g_late = 0;
    unsigned windows = 0, done = 0;
    if (e->report_ok) {
        static char line[400];
        const char *p = (const char *)H->report, *end = p + e->report_len;
        while (p < end) {
            const char *nl = memchr(p, '\n', (size_t)(end - p));
            size_t n = nl ? (size_t)(nl - p) : (size_t)(end - p);
            if (n >= sizeof(line)) n = sizeof(line) - 1;
            memcpy(line, p, n);
            line[n] = 0;
            p = nl ? nl + 1 : end;
            for (const char *const *m = FAIL_MARKS; *m; ++m)
                if (strstr(line, *m) && !e->why[0]) snprintf(e->why, sizeof(e->why), "%.60s", line);
            if (!strncmp(line, "WINDOW ", 7) && !strcmp(s->kind, "bench")) { bench_window(e, line); ++windows; }
            else if (!strncmp(line, "ROW ", 4) && !strcmp(s->kind, "e1")) e1_row(line);
            else if (!strncmp(line, "SCHEDULE DONE", 13) || !strncmp(line, "E1 END", 6)) done = 1;
        }
    }
    if (!strcmp(s->kind, "e1")) e1_summary(e);
    e->rows = !strcmp(s->kind, "bench") ? windows : g_rows;
    if (!e->why[0] && !e->rows) snprintf(e->why, sizeof(e->why), "no rows in the report");
    if (!e->why[0] && !done) snprintf(e->why, sizeof(e->why), "no end line in the report");
    e->state = e->why[0] ? E_FAILED : E_OK;
}

static void fail(unsigned i, const char *fmt, ...) {
    sel_entry_t *e = &J->e[i];
    memset(e, 0, sizeof(*e));
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(e->why, sizeof(e->why), fmt, ap);
    va_end(ap);
    e->state = E_FAILED;
}

static void print_entry(unsigned i) {
    const sel_entry_t *e = &J->e[i];
    const scene_t *s = &g_sc[i];
    printf("CDISC RESULT %u %s %s state %s exit %d report %u crc %s rows %u%s%s\n", i + 1, s->name,
           e->state == E_OK ? "OK" : "FAILED", e->run_state < 6 ? (const char *[]){"NONE", "RUNNING", "DONE", "CRASHED", "TIMEOUT", "LOST"}[e->run_state] : "?",
           (int)e->exit_code, (unsigned)e->report_len, e->report_ok ? "ok" : "bad", (unsigned)e->rows,
           e->why[0] ? " why: " : "", e->why);
    for (const char *p = e->sum; *p;) {
        const char *nl = strchr(p, '\n');
        const int n = nl ? (int)(nl - p) : (int)strlen(p);
        printf("CDISC SUM %s %.*s\n", s->name, n, p);
        p = nl ? nl + 1 : p + n;
    }
}

/* ---------------------------------------------------------------- run one scene (does not return) */
static void launch(unsigned i) {
    const scene_t *s = &g_sc[i];
    char path[96];
    snprintf(path, sizeof(path), "/cd/%s", s->prog);
    FILE *f = fopen(path, "rb");
    if (!f) { fail(i, "program %s missing", s->prog); return; }
    fseek(f, 0, SEEK_END);
    const long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    const uint32_t max = CL_HANDOFF_ADDR - 0x11000u - CL_LOAD_ADDR;
    uint8_t *img = n > 0 && (uint32_t)n <= max ? (uint8_t *)memalign(32, (size_t)n + 4) : NULL;
    if (!img || (uintptr_t)img + (size_t)n + 4 > CL_HANDOFF_ADDR - 0x11000u || fread(img, 1, (size_t)n, f) != (size_t)n) {
        fclose(f);
        fail(i, "program %s unreadable (%ld bytes)", s->prog, n);
        return;
    }
    fclose(f);
    memset(img + n, 0, 4);
    /* the hand-off area, as the loader writes it on RUN; the report cap keeps the client below the journal */
    cl_handoff_hdr_t *h = &H->h;
    memset(h, 0, sizeof(*h));
    h->magic = CL_HANDOFF_MAGIC;
    h->version = CL_HANDOFF_VERSION;
    h->boot_count = J->boots;
    h->run_id = J->nonce + i;
    h->state = CL_RUN_RUNNING;
    h->deadline_s = s->deadline;
    snprintf(h->args, sizeof(h->args), "%s", s->args);
    h->report_cap = SEL_REPORT_CAP;
    cl_handoff_seal(H);
    J->running = i + 1;
    journal_seal();
    printf("CDISC RUN %u %s %s deadline %u s args \"%s\" (%ld bytes)\n", i + 1, s->name, s->prog, s->deadline, s->args, n);
    line_at(16, YELLOW, "RUNNING %u/%u %s", i + 1, g_n, s->name);
    thd_sleep(300);
    arch_exec_at(img, ((uint32_t)n + 3) & ~3u, CL_LOAD_ADDR);
}

/* ---------------------------------------------------------------- summary screen */
static char g_lines[160][56];
static uint16_t g_col[160];
static unsigned g_nl;
static void add_line(uint16_t c, const char *fmt, ...) {
    if (g_nl >= 160) return;
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(g_lines[g_nl], sizeof(g_lines[0]), fmt, ap);
    va_end(ap);
    g_col[g_nl++] = c;
}

static void progress_screen(const char *head) {
    vid_clear(0, 0, 0);
    line_at(0, CYAN, "RE4DC CONSOLE DISC  %s", LOADER_BUILD);
    line_at(1, GREY, "%s", head);
    for (unsigned i = 0; i < g_n && i < 12; ++i) {
        const sel_entry_t *e = &J->e[i];
        const int done = i < J->next;
        line_at(3 + (int)i, !done ? GREY : e->state == E_OK ? GREEN : RED, "%u %-10s %s %.28s", i + 1, g_sc[i].name,
                !done ? "...   " : e->state == E_OK ? "OK    " : "FAILED", done ? (e->state == E_OK ? g_sc[i].title : e->why) : g_sc[i].title);
    }
}

int main(int argc, char **argv) {
    (void)argc; (void)argv;
    vid_set_mode(DM_640x480, PM_RGB565);
    vid_clear(0, 0, 0);
    const int planned = read_plan();
    if (!planned) {
        line_at(0, RED, "RE4DC CONSOLE DISC: NO /cd/SCENES.TXT");
        printf("CDISC no plan\n");
        for (;;) thd_sleep(1000);
    }
    const int jv = J->magic == SEL_MAGIC && J->crc == journal_crc() && J->plan_crc == g_plan_crc && J->n == g_n;
    if (!jv) {   /* power-on (or a finished run): a new run */
        memset(J, 0, sizeof(*J));
        J->plan_crc = g_plan_crc;
        J->n = g_n;
        J->nonce = ((uint32_t)timer_us_gettime64() * 2654435761u) & 0xffffff00u;
        printf("CDISC START %s: %u scenes, plan crc %08x, run %08x\n", LOADER_BUILD, g_n, (unsigned)g_plan_crc,
               (unsigned)J->nonce);
    }
    J->boots++;
    if (J->running) {   /* the scene that ran: its hand-in */
        const unsigned i = J->running - 1;
        collect(i);
        J->running = 0;
        J->next = i + 1;
        print_entry(i);
    }
    journal_seal();
    while (J->next < g_n) {
        const unsigned i = J->next;
        const scene_t *s = &g_sc[i];
        char head[64];
        snprintf(head, sizeof(head), "NEXT %u/%u: %.30s  (HOLD B: SKIP)", i + 1, g_n, s->title);
        progress_screen(head);
        int skip = 0;
        for (int t = 0; t < 30 && !skip; ++t) {   /* 3 s */
            skip = pad_held(CONT_B);
            thd_sleep(100);
        }
        char missing[64] = "";
        if (strcmp(s->need, "-")) {
            char need[256];
            snprintf(need, sizeof(need), "%s", s->need);
            for (char *t = need; t && *t && !missing[0];) {
                char *c = strchr(t, ',');
                if (c) *c = 0;
                if (*t && !file_exists(t)) snprintf(missing, sizeof(missing), "%.50s", t);
                t = c ? c + 1 : NULL;
            }
        }
        if (skip) fail(i, "skipped by the owner (B held)");
        else if (missing[0]) fail(i, "missing %s", missing);
        else launch(i);   /* returns only when the program could not be read */
        J->next = i + 1;
        journal_seal();
        print_entry(i);
    }
    /* the summary: serial, then the screen in pages for ever */
    unsigned ok = 0;
    for (unsigned i = 0; i < g_n; ++i) ok += J->e[i].state == E_OK;
    printf("CDISC SUMMARY BEGIN %s run %08x boots %u\n", LOADER_BUILD, (unsigned)J->nonce, (unsigned)J->boots);
    for (unsigned i = 0; i < g_n; ++i) print_entry(i);
    printf("CDISC SUMMARY END %u of %u scenes OK\n", ok, g_n);
    for (unsigned i = 0; i < g_n; ++i) {
        const sel_entry_t *e = &J->e[i];
        add_line(e->state == E_OK ? GREEN : RED, "%u %s %s %.36s", i + 1, g_sc[i].name, e->state == E_OK ? "OK" : "FAILED",
                 e->state == E_OK ? g_sc[i].title : e->why);
        for (const char *p = e->sum; *p;) {
            const char *nl = strchr(p, '\n');
            const int n = nl ? (int)(nl - p) : (int)strlen(p);
            add_line(WHITE, " %.*s", n > 52 ? 52 : n, p);
            p = nl ? nl + 1 : p + n;
        }
    }
    J->magic = 0;   /* the run is over: a reset starts a new one (the summary stays in this program's memory) */
    const unsigned per = 16, pages = (g_nl + per - 1) / per;
    for (unsigned page = 0;; page = (page + 1) % (pages ? pages : 1)) {
        vid_clear(0, 0, 0);
        line_at(0, ok == g_n ? GREEN : RED, "FINISHED: %u OF %u SCENES OK   PAGE %u/%u", ok, g_n, page + 1, pages);
        line_at(1, GREY, "RE4DC CONSOLE DISC %s  TIMES IN MS", LOADER_BUILD);
        for (unsigned k = 0; k < per && page * per + k < g_nl; ++k)
            line_at(2 + (int)k, g_col[page * per + k], "%s", g_lines[page * per + k]);
        line_at(18, GREY, "m mean p p99 w worst@picture >budget:count");
        thd_sleep(10000);
    }
}
