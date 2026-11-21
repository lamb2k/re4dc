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
   kinds: bench, or e1:<timing|function>:<drawn|headless> (lane eng-e1o: the run kind and mode are the schedule's).
   kind bench: the summary is the bench's own WINDOW rows (mean, p99, worst, over 14, over 33.3, presented intervals
   over two fields; 600 pictures a window). kind e1: the summary is computed here from the image's ROW lines, pictures
   41 to 640 (600; the lane tools' budget.py rows): drawing (the ROW draw column: the renderer's own span, phase
   stamps 5 to 7, chip ready to picture submitted; the plan's drawing row since lane eng-e1e), busy picture (frame
   less the pacer's and PVR waits), services, behaviour, the PVR wait on its own row (not in drawing), and the
   presented-field intervals over two fields with the worst (lane eng-e1f: the image's vblank count of page flips,
   its E1 FIELDS line names the mode; a headless image presents nothing and counts each tick's fields instead).

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

/* lane eng-e1o (H-017.6): an E1-family scene's run kind and drawing mode come from the schedule, never from the image:
   kind "e1:timing:drawn", "e1:timing:headless", "e1:function:drawn" or "e1:function:headless". The image's own run
   line and headless line must agree with it (a scheduled timing scene whose image says "function" fails). A bare "e1"
   or any other spelling is a schedule error: the scene FAILS without being run. */
typedef struct {
    char name[16], title[48], prog[40], kind[24], need[256], args[256];
    unsigned deadline;
    int e1, timing, headless;   /* e1: an E1-family scene; timing: scheduled timing run; headless: scheduled headless */
    char plan_err[48];          /* the schedule line's kind could not be read */
} scene_t;
static scene_t g_sc[SEL_MAX];
static unsigned g_n;
/* lane eng-e1n: every entry of the schedule, also those past SEL_MAX; a longer schedule is refused (main), so the run
   never reports "N of N scenes OK" for a plan it cut */
static unsigned g_listed;
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
/* lane eng-e1p (H-018.3): the schedule is read to its end, whatever its length (up to 1 MiB; a longer file is refused),
   and every line that is not blank or a comment ('#' first, after any blanks) must parse: six fields, each within its
   size (name 15, title 47, program 39, kind 23, files 255 characters), the deadline all digits (1 to 100000 s), the rest
   of the line the arguments (255 characters at most). A line that does not parse refuses the whole schedule (main:
   "CDISC SCHEDULE REFUSED"); no entry may vanish. Before, 4,095 bytes were read and a line that sscanf could not fill
   was skipped. */
static char g_plan_refused[96];
static int plan_field(char **p, char *out, size_t cap) {   /* the next blank-separated field, or 0 (none, or too long) */
    while (**p == ' ' || **p == '\t') ++*p;
    const char *t = *p;
    while (**p && **p != ' ' && **p != '\t') ++*p;
    const size_t n = (size_t)(*p - t);
    if (!n) return 0;
    if (n >= cap) return -1;
    memcpy(out, t, n);
    out[n] = 0;
    return 1;
}
static int read_plan(void) {
    FILE *f = fopen("/cd/SCENES.TXT", "rb");
    if (!f) return 0;
    size_t cap = 4096, n = 0;
    char *text = (char *)malloc(cap);
    for (;;) {
        if (!text) { snprintf(g_plan_refused, sizeof(g_plan_refused), "schedule: no memory to read it"); fclose(f); return 1; }
        if (n + 1 >= cap) {
            if (cap >= (1u << 20)) { snprintf(g_plan_refused, sizeof(g_plan_refused), "schedule: larger than 1 MiB"); fclose(f); return 1; }
            cap *= 2;
            text = (char *)realloc(text, cap);
            continue;
        }
        const size_t r = fread(text + n, 1, cap - 1 - n, f);
        if (!r) break;
        n += r;
    }
    const int bad_read = ferror(f);
    fclose(f);
    text[n] = 0;
    g_plan_crc = cl_crc32(0, text, n);
    if (bad_read) { snprintf(g_plan_refused, sizeof(g_plan_refused), "schedule: read error after %u bytes", (unsigned)n); return 1; }
    if (strlen(text) != n) { snprintf(g_plan_refused, sizeof(g_plan_refused), "schedule: a NUL byte at %u", (unsigned)strlen(text)); return 1; }
    static scene_t over;   /* lane eng-e1n: an entry past SEL_MAX, read only to be counted */
    unsigned lineno = 0;
    for (char *l = text; l && *l;) {
        char *e = strchr(l, '\n');
        if (e) *e = 0;
        ++lineno;
        char *r = strchr(l, '\r');
        if (r) *r = 0;
        scene_t *s = g_n < SEL_MAX ? &g_sc[g_n] : &over;
        char *p = l;
        while (*p == ' ' || *p == '\t') ++p;
        if (*p && *p != '#') {
            char dl[12];
            static const char *const what[6] = {"name", "title", "program", "deadline", "kind", "files"};
            int got[6];
            got[0] = plan_field(&p, s->name, sizeof(s->name));
            got[1] = got[0] > 0 ? plan_field(&p, s->title, sizeof(s->title)) : 0;
            got[2] = got[1] > 0 ? plan_field(&p, s->prog, sizeof(s->prog)) : 0;
            got[3] = got[2] > 0 ? plan_field(&p, dl, sizeof(dl)) : 0;
            got[4] = got[3] > 0 ? plan_field(&p, s->kind, sizeof(s->kind)) : 0;
            got[5] = got[4] > 0 ? plan_field(&p, s->need, sizeof(s->need)) : 0;
            int k = 0;
            while (k < 6 && got[k] > 0) ++k;
            if (k < 6) {
                snprintf(g_plan_refused, sizeof(g_plan_refused), "schedule line %u: %s %s", lineno, what[k],
                         got[k] < 0 ? "too long" : "missing (6 fields needed)");
                return 1;
            }
            unsigned long d = 0;
            int ok = 1;
            for (const char *c = dl; *c; ++c) ok &= *c >= '0' && *c <= '9';
            if (ok) d = strtoul(dl, NULL, 10);
            if (!ok || d < 1 || d > 100000) {
                snprintf(g_plan_refused, sizeof(g_plan_refused), "schedule line %u: deadline %.11s not 1-100000", lineno, dl);
                return 1;
            }
            s->deadline = (unsigned)d;
            while (*p == ' ' || *p == '\t') ++p;
            if (strlen(p) >= sizeof(s->args)) {
                snprintf(g_plan_refused, sizeof(g_plan_refused), "schedule line %u: arguments too long", lineno);
                return 1;
            }
            snprintf(s->args, sizeof(s->args), "%s", p);
            for (char *t = s->title; *t; ++t) if (*t == '_') *t = ' ';
            s->e1 = !strncmp(s->kind, "e1", 2);
            s->plan_err[0] = 0;
            if (s->e1) {
                static const char *const forms[4] = {"e1:timing:drawn", "e1:timing:headless", "e1:function:drawn",
                                                     "e1:function:headless"};
                int f = -1;
                for (int k = 0; k < 4; ++k) if (!strcmp(s->kind, forms[k])) f = k;
                if (f < 0) snprintf(s->plan_err, sizeof(s->plan_err), "schedule: kind %.20s (run and mode not said)", s->kind);
                s->timing = f == 0 || f == 1;
                s->headless = f == 1 || f == 3;
                strcpy(s->kind, "e1");
            } else if (strcmp(s->kind, "bench")) {
                snprintf(s->plan_err, sizeof(s->plan_err), "schedule: unknown kind %.20s", s->kind);
            }
            ++g_listed;
            if (s != &over) ++g_n;
        }
        l = e ? e + 1 : NULL;
    }
    free(text);
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
                                         "E1 load: missing", "E1 load: read failed", "E1 load: bad DRS", "E1 load: camera tracks refused", "CRASH event",
                                         "ABORT", "DEADLINE", "E2 SHOT REFUSED", NULL};

/* the value after the keyword (first match at or after *from) */
static const char *after(const char *line, const char *key) {
    const char *p = strstr(line, key);
    if (!p) return NULL;
    p += strlen(key);
    while (*p == ' ') ++p;
    return p;
}

/* lane eng-e1o (H-017.6): strict numbers. Lane eng-e1p (H-018.3): each judged line is matched whole against its
   template (tmatch), so every field ends at its own delimiter and the line is consumed to its end:
     literal text      must be there, character for character;
     %u                an unsigned decimal: digits only, at most 4294967295;
     %d                a signed decimal: an optional '-', digits, within -2147483648 .. 2147483647;
     %x                hexadecimal digits, at most ffffffff;
     %w                a word: up to the next blank (at most 15 characters);
     %s                the rest of the line (the last field).
   A number stops at its first non-digit, and the template's next character must be the line's next character: "17,"
   where "%u " is expected, "12x", "none", an empty field, a missing field or a value past 32 bits do not match (before,
   a number could end at any of " );,", strtoul's overflow was not checked, and the text after a matched keyword was not
   read). Returns 1 when the whole line matches; otherwise 0 and *at points into the template where matching stopped
   (the failure reason names that field). */
static int tmatch(const char *line, const char *tpl, const char **at, ...) {
    va_list ap;
    va_start(ap, at);
    const char *p = line, *t = tpl;
    int ok = 1;
    while (*t && ok) {
        if (*t != '%') {
            if (*p != *t) { ok = 0; break; }
            ++p, ++t;
            continue;
        }
        const char f = t[1];
        if (f == 'u' || f == 'd' || f == 'x') {
            int neg = 0;
            if (f == 'd' && *p == '-') neg = 1, ++p;
            const int base = f == 'x' ? 16 : 10;
            uint64_t v = 0;
            const char *d0 = p;
            for (;; ++p) {
                int dv;
                if (*p >= '0' && *p <= '9') dv = *p - '0';
                else if (base == 16 && *p >= 'a' && *p <= 'f') dv = *p - 'a' + 10;
                else if (base == 16 && *p >= 'A' && *p <= 'F') dv = *p - 'A' + 10;
                else break;
                v = v * (uint64_t)base + (uint64_t)dv;
                if (v > 0xffffffffull) { ok = 0; break; }
            }
            if (!ok || p == d0) { ok = 0; break; }
            if (f == 'd') {
                if (v > (neg ? 2147483648ull : 2147483647ull)) { ok = 0; break; }
                *va_arg(ap, long *) = (long)(neg ? -(int64_t)v : (int64_t)v);
            } else if (f == 'x') {
                *va_arg(ap, unsigned long *) = (unsigned long)v;
            } else {
                *va_arg(ap, unsigned *) = (unsigned)v;
            }
        } else if (f == 'w') {
            char *o = va_arg(ap, char *);
            unsigned n = 0;
            while (*p && *p != ' ' && *p != '\t') { if (n >= 15) { ok = 0; break; } o[n++] = *p++; }
            o[n] = 0;
            if (!n) ok = 0;
            if (!ok) break;
        } else if (f == 's') {
            *va_arg(ap, const char **) = p;
            p += strlen(p);
        } else {
            ok = 0;
            break;
        }
        t += 2;
    }
    if (ok && *p) ok = 0;   /* text left over: the line is not consumed whole */
    va_end(ap);
    if (at) *at = t;
    return ok;
}
/* the template's words where matching stopped (a failure reason): up to 24 characters, field markers shown */
static void tmatch_where(const char *at, char *out, size_t cap) {
    snprintf(out, cap, "%.24s", at && *at ? at : "(end of line)");
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
static unsigned g_rows, g_last_row, g_late, g_headless;
static char g_fmode[12];   /* the image's E1 FIELDS mode: presented, tick, or "" (an image that does not count) */
static unsigned g_flips, g_pictures;
/* lane eng-e1k (H-016.6): the record proves its own completeness. Each picture's row once (a repeated row is counted,
   never summed twice); the image's release-queue drops; the run's kind (a traced or stills run says "not a timing
   run"); the after-play memory line (stack guard, arena margin, video memory). */
static uint8_t g_seen[E1_COUNT];
static unsigned g_dups, g_drops, g_drops_seen, g_function, g_mem_after;
static char g_runkind[48];
static long g_mem_stack, g_mem_arena, g_mem_vram;
/* lane eng-e1o (H-017.6): rows with a field that is not a number; the after-play memory line's completeness; the
   image's own tick count (E1 DONE); the in-play file opens (E1 FILES, H-017.7) */
static unsigned g_bad_rows, g_mem_ok, g_mem_guard_broken, g_mem_lost, g_done_ticks, g_done_seen;
static unsigned g_files_seen, g_files_opens;
static char g_mem_why[64], g_files_first[48];
/* lane eng-e1p (H-018.4, H-018.1, H-018.3): the in-play disc reads and drive requests (E1 FILES), the camera tracks
   converted in play (E1 CAMTRACK); the FIELDS line's own counts, cross-checked against the rows */
static unsigned g_files_reads, g_files_sectors, g_ctrack_seen, g_ctrack_inplay;
/* the console loop client's closing count (loader/cl_send.c): rows it dropped once the report's row budget was spent
   (always the last rows: the budget only fills), so the image's tick count is the last row received plus these */
static unsigned g_cl_seen, g_cl_rows_dropped;
static unsigned g_fl_counted, g_fl_over, g_fl_worst, g_fl_worst_pic;
static void e1_row(const char *l) {
    /* compact rows: "ROW n in tick svc trace draw wait frame fields pl obj cam pvr chars ..." as numbers only; every
       field must be a number (lane eng-e1o: a text field is a malformed row and fails the record, never skipped).
       Lane eng-e1p (H-018.3): each value is digits only, at most 4294967295, and ends at one blank or the line's end
       ("17,missing" is not 17); the row is read to its end. */
    unsigned long v[24];
    int k = 0;
    const char *p = l + 4;
    for (;;) {
        if (k >= 24 || *p < '0' || *p > '9') { ++g_bad_rows; return; }
        uint64_t x = 0;
        while (*p >= '0' && *p <= '9') {
            x = x * 10u + (uint64_t)(*p++ - '0');
            if (x > 0xffffffffull) { ++g_bad_rows; return; }
        }
        v[k++] = (unsigned long)x;
        if (!*p) break;
        if (*p != ' ' || !p[1]) { ++g_bad_rows; return; }   /* a value ends at one blank before the next, or the end */
        ++p;
    }
    if (k < 13) { ++g_bad_rows; return; }
    const unsigned n = (unsigned)v[0];
    if (n > g_last_row) g_last_row = n;
    if (n < E1_FIRST || n >= E1_FIRST + E1_COUNT) return;
    const unsigned i = n - E1_FIRST;
    if (g_seen[i]) { ++g_dups; return; }   /* lane eng-e1k: a repeated picture row fails the record */
    g_seen[i] = 1;
    const uint32_t tick = (uint32_t)v[2], svc = (uint32_t)v[3], draw = (uint32_t)v[5], wait = (uint32_t)v[6];
    const uint32_t frame = (uint32_t)v[7], pvr = (uint32_t)v[12];
    g_v[0][i] = draw;
    g_v[1][i] = frame > wait + pvr ? frame - wait - pvr : 0;   /* busy picture */
    g_v[2][i] = svc;
    g_v[3][i] = tick > svc ? tick - svc : 0;                  /* behaviour */
    g_v[4][i] = pvr;                                          /* PVR wait: the chip, not CPU work; not in draw */
    g_fields[i] = (uint32_t)v[8];
    g_late += wait == 0;   /* the 30 Hz pacer had no time left to wait: the picture was late */
    ++g_rows;
}
static int cmp_u32(const void *a, const void *b) {
    const uint32_t x = *(const uint32_t *)a, y = *(const uint32_t *)b;
    return (x > y) - (x < y);
}
static void e1_summary(sel_entry_t *e) {
    /* draw = the ROW draw column, the renderer's own span (stamps 5 to 7): the plan's drawing row; pvrw = the PVR
       wait before it, shown apart so nothing is hidden (no budget: the chip, not CPU work) */
    static const char *const names[5] = {"draw", "busy", "svc", "behav", "pvrw"};
    static const uint32_t budget_us[5] = {14000, 33333, 9000, 2000, 0};
    static uint32_t s[E1_COUNT];
    const unsigned n = g_rows;
    if (g_function) {   /* lane eng-e1k: a traced or stills run: its rows are not timing */
        sum_add(e, "run: %.44s", g_runkind);   /* "function (traced): not a timing run" */
        sum_add(e, "rows %u of %u ticks: not reported as timing", n, g_last_row);
        if (g_files_seen) sum_add(e, "disc in play: opens %u reads %u sectors %u", g_files_opens, g_files_reads, g_files_sectors);
        if (g_ctrack_seen) sum_add(e, "camera tracks converted in play %u", g_ctrack_inplay);
        return;
    }
    sum_add(e, "pictures %u (%u-%u of %u ticks) ms:", n, E1_FIRST, E1_FIRST + n - 1, g_last_row);
    if (g_mem_after)
        sum_add(e, "after play: stack %ld B, arena margin %ld B, vram free %ld B", g_mem_stack, g_mem_arena, g_mem_vram);
    if (g_files_seen)   /* lane eng-e1o (H-017.7); lane eng-e1p (H-018.4): reads and drive requests too */
        sum_add(e, "disc in play: opens %u reads %u sectors %u", g_files_opens, g_files_reads, g_files_sectors);
    if (g_ctrack_seen) sum_add(e, "camera tracks converted in play %u", g_ctrack_inplay);   /* lane eng-e1p (H-018.1) */
    if (!n) return;
    if (!g_headless) sum_add(e, "draw = renderer span (stamps 5-7): drawing row");
    for (unsigned r = 0; r < 5; ++r) {
        if ((r == 0 || r == 4) && g_headless) {   /* "E1 draw: headless": no drawing row, rather than "0 over 14" */
            if (r == 0) sum_add(e, "draw  not drawn (headless image)");
            continue;
        }
        uint64_t sum = 0;
        unsigned worst = 0, wi = 0, over = 0;
        for (unsigned i = 0; i < n; ++i) {
            const uint32_t x = g_v[r][i];
            s[i] = x;
            sum += x;
            if (x > worst) { worst = x; wi = i; }
            over += budget_us[r] && x > budget_us[r];
        }
        qsort(s, n, 4, cmp_u32);
        const unsigned p99 = s[(unsigned)(0.99 * n) < n ? (unsigned)(0.99 * n) : n - 1];
        if (budget_us[r])
            sum_add(e, "%-5s m%u.%02u p%u.%02u w%u.%02u@%u >%u.%u:%u", names[r], (unsigned)(sum / n / 1000),
                    (unsigned)(sum / n % 1000 / 10), p99 / 1000, p99 % 1000 / 10, worst / 1000, worst % 1000 / 10,
                    wi + E1_FIRST, budget_us[r] / 1000, budget_us[r] % 1000 / 100, over);
        else
            sum_add(e, "%-5s m%u.%02u p%u.%02u w%u.%02u@%u (PVR wait)", names[r], (unsigned)(sum / n / 1000),
                    (unsigned)(sum / n % 1000 / 10), p99 / 1000, p99 % 1000 / 10, worst / 1000, worst % 1000 / 10,
                    wi + E1_FIRST);
    }
    unsigned iv = 0, wf = 0, wfi = 0, counted = 0;
    for (unsigned i = 0; i < n; ++i) {
        counted += g_fields[i] != 0;
        if (g_fields[i] > 2) ++iv;
        if (g_fields[i] > wf) { wf = g_fields[i]; wfi = i; }
    }
    /* an image that does not count fields prints 0 in the column: say so, never "0 over" */
    if (!g_fmode[0] || !counted) {
        sum_add(e, "late (no pacer wait) %u; fields not counted", g_late);
        return;
    }
    sum_add(e, "%s fields: >2 %u, worst %u@%u (%u)", strcmp(g_fmode, "tick") ? "presented" : "tick (headless)", iv, wf,
            wfi + E1_FIRST, counted);
    if (!strcmp(g_fmode, "presented") && g_flips < g_pictures) sum_add(e, "flips %u of %u pictures", g_flips, g_pictures);
    sum_add(e, "late (no pacer wait) %u", g_late);
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
    }
    /* the report: refusal lines and rows */
    g_rows = g_last_row = g_late = g_headless = 0;
    g_fmode[0] = 0;
    g_flips = g_pictures = 0;
    memset(g_seen, 0, sizeof(g_seen));
    memset(g_fields, 0, sizeof(g_fields));
    g_dups = g_drops = g_drops_seen = g_function = g_mem_after = 0;
    g_bad_rows = g_mem_ok = g_mem_guard_broken = g_mem_lost = g_done_ticks = g_done_seen = 0;
    g_files_seen = g_files_opens = 0;
    g_files_reads = g_files_sectors = g_ctrack_seen = g_ctrack_inplay = 0;
    g_cl_seen = g_cl_rows_dropped = 0;
    g_fl_counted = g_fl_over = g_fl_worst = g_fl_worst_pic = 0;
    g_mem_why[0] = g_files_first[0] = 0;
    g_runkind[0] = 0;
    g_mem_stack = g_mem_arena = g_mem_vram = -1;
    unsigned windows = 0, done = 0, run_lines = 0, fields_bad = 0, camrec_ticks = 0;
    int pool_seen = 0, pub_seen = 0, camrec_seen = 0, wep_seen = 0;
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
            else if (!strncmp(line, "E1 draw: headless", 17)) g_headless = 1;
            else if (!strncmp(line, "E1 FIELDS mode ", 15)) {
                /* lane eng-e1o: every field strict; lane eng-e1p (H-018.3): the line matched whole, and its counts kept
                   to be checked against the rows ("E1 FIELDS mode presented|tick flips F of P pictures; pictures 41-640:
                   counted C intervals>2 N worst W (picture K); release queue full D") */
                char mode[16];
                g_fmode[0] = 0;
                g_drops_seen = 0;
                if (!tmatch(line, "E1 FIELDS mode %w flips %u of %u pictures; pictures 41-640: counted %u intervals>2 %u "
                                  "worst %u (picture %u); release queue full %u", NULL, mode, &g_flips, &g_pictures,
                            &g_fl_counted, &g_fl_over, &g_fl_worst, &g_fl_worst_pic, &g_drops))
                    ++fields_bad;
                else if (strcmp(mode, "presented") && strcmp(mode, "tick")) ++fields_bad;
                else {
                    snprintf(g_fmode, sizeof(g_fmode), "%s", mode);
                    g_drops_seen = 1;
                }
            } else if (!strncmp(line, "E1 RUN ", 7)) {
                snprintf(g_runkind, sizeof(g_runkind), "%.40s", line + 7);
                ++run_lines;
                if (!strncmp(line, "E1 RUN timing ", 14)) g_function = 0;
                else if (!strncmp(line, "E1 RUN function ", 16) && strstr(line, "not a timing run")) g_function = 1;
                else g_function = 2;   /* a run line that says neither: fails below */
            } else if (!strncmp(line, "E1 MEM after play:", 18)) {
                /* lane eng-e1o (H-017.6): the line is complete and numeric, or the record fails. Lane eng-e1p (H-018.3):
                   matched whole, clause by clause (mallinfo free included; before, the line was searched by keyword and
                   mallinfo free was never read). The guard is read from this line. */
                unsigned hw = 0, of = 0, blocks = 0, use = 0, peak = 0, mu = 0, mf = 0;
                unsigned long sbrk_top = 0;
                long arena = 0, vram = 0;
                char guard[16], where[32];
                const char *at = NULL;
                ++g_mem_after;
                if (!tmatch(line, "E1 MEM after play:stack high water %u of %u guard %w | heap blocks %u in use %u peak %u "
                                  "| sbrk %x free to arena %d | mallinfo used %u free %u | vram free %d | lost %u", &at,
                            &hw, &of, guard, &blocks, &use, &peak, &sbrk_top, &arena, &mu, &mf, &vram, &g_mem_lost)) {
                    tmatch_where(at, where, sizeof(where));
                    snprintf(g_mem_why, sizeof(g_mem_why), "after-play memory line: no match at '%s'", where);
                } else if (strcmp(guard, "intact") && strcmp(guard, "BROKEN")) {
                    snprintf(g_mem_why, sizeof(g_mem_why), "after-play memory line: guard %s", guard);
                } else {
                    g_mem_ok = 1;
                    g_mem_guard_broken = !strcmp(guard, "BROKEN");
                    g_mem_stack = (long)hw, g_mem_arena = arena, g_mem_vram = vram;
                }
                (void)of; (void)blocks; (void)use; (void)peak; (void)mu; (void)mf; (void)sbrk_top;
            }
            else if (!strncmp(line, "E1 DONE ticks=", 14)) {
                unsigned t = 0;
                g_done_seen = tmatch(line, "E1 DONE ticks=%u", NULL, &t) && t > 0;
                g_done_ticks = g_done_seen ? t : 0;
            }
            else if (!strncmp(line, "E1 FILES in play: opens ", 24)) {
                /* lane eng-e1o (H-017.7): files opened between the first and the last picture; lane eng-e1p (H-018.4):
                   and the reads on disc-backed handles and the CD drive's read requests ("E1 FILES in play: opens N reads
                   R sector-requests S first-open-tick T first-read-tick T first-sector-tick T name X"); a timing scene
                   needs all three 0 */
                unsigned t1 = 0, t2 = 0, t3 = 0;
                const char *nm = NULL;
                g_files_seen = tmatch(line, "E1 FILES in play: opens %u reads %u sector-requests %u first-open-tick %u "
                                            "first-read-tick %u first-sector-tick %u name %s", NULL, &g_files_opens,
                                      &g_files_reads, &g_files_sectors, &t1, &t2, &t3, &nm);
                snprintf(g_files_first, sizeof(g_files_first), "%.40s", g_files_seen && nm ? nm : "?");
                (void)t1; (void)t2; (void)t3;
            }
            else if (!strncmp(line, "cl-send: pack loader stage", 26) && e->why[0]) sum_add(e, "%.50s", line + 9);
            else if (!strncmp(line, "cl-send: lines ", 15)) {
                unsigned nl = 0, kept = 0, skipped = 0, full = 0, cut = 0;
                long code = 0;
                g_cl_seen = tmatch(line, "cl-send: lines %u kept %u rows dropped %u skipped %u dropped when full %u cut long %u, "
                                         "end code %d", NULL, &nl, &kept, &g_cl_rows_dropped, &skipped, &full, &cut, &code);
                (void)nl; (void)kept; (void)skipped; (void)full; (void)cut; (void)code;
            }
            else if (!strncmp(line, "E1 POOL full ", 13)) {
                /* lane eng-e1i (ruling H-015.3): a record pool's refusal is an engine fault, the scene fails */
                unsigned full = 0, bad = 0;
                pool_seen = tmatch(line, "E1 POOL full %u bad_frees %u", NULL, &full, &bad);
                if ((!pool_seen || full || bad) && !e->why[0])
                    snprintf(e->why, sizeof(e->why), "pool refused: full %u, bad frees %u", full, bad);
            }
            else if (!strncmp(line, "E1 PUB camera ", 14)) {
                /* lane eng-e1j (ruling H-016.2): no per-tick conversion of game state into draw records; lane eng-e1n
                   (H-017.5): the line counts only what has a producer, the camera copy control and the light-view
                   misses (a character drawn without its light view); either not 0, or the line incomplete, fails */
                unsigned cam = 0, miss = 0;
                pub_seen = tmatch(line, "E1 PUB camera %u light-view-misses %u", NULL, &cam, &miss);
                if ((!pub_seen || cam || miss) && !e->why[0])
                    snprintf(e->why, sizeof(e->why), "%sPUB: camera copies %u, light-view misses %u",
                             pub_seen ? "" : "incomplete ", cam, miss);
            }
            else if (!strncmp(line, "E1 WEP pictures ", 16)) {
                /* lane eng-look1: Leon's weapon is drawn every picture the hosted code says it is drawn (cObjWep's
                   be_flag gate, services/weapon_view.h) and never when it says not: visible must equal drawn and
                   drawn-hidden be 0, or the line incomplete, fails (timing and function runs alike). Control: the NOWEP
                   boot file (CNOWEP) draws no weapon: drawn 0 against visible */
                unsigned pics = 0, present = 0, vis = 0, drawn = 0, hidden = 0, nodraw = 0, on = 0, ret = 0, lines = 0, ctl = 0;
                wep_seen = tmatch(line, "E1 WEP pictures %u present %u visible %u drawn %u drawn-hidden %u not-drawable %u "
                                        "on-screen %u world-copies-retired %u trace-lines %u control %u", NULL, &pics,
                                  &present, &vis, &drawn, &hidden, &nodraw, &on, &ret, &lines, &ctl);
                if ((!wep_seen || vis != drawn || hidden) && !e->why[0])
                    snprintf(e->why, sizeof(e->why), "%sweapon: visible %u drawn %u drawn-hidden %u not-drawable %u",
                             wep_seen ? "" : "incomplete ", vis, drawn, hidden, nodraw);
                (void)pics; (void)present; (void)on; (void)ret; (void)lines; (void)ctl;
            }
            else if (!strncmp(line, "E1 CAMTRACK part-frame-decodes ", 31)) {
                /* lane eng-e1p (H-018.1): camera tracks are converted when the room is loaded; one converted in play is
                   counted ("in-play N") and fails a timing scene */
                unsigned v[9];
                g_ctrack_seen = tmatch(line, "E1 CAMTRACK part-frame-decodes %u moves %u not-played %u conversions %u "
                                             "in-play %u lookups %u room-tracks %u room-bytes %u store-peak %u of %u", NULL,
                                       &v[0], &v[1], &v[2], &v[3], &g_ctrack_inplay, &v[4], &v[5], &v[6], &v[7], &v[8]);
            }
            else if (!strncmp(line, "E1 CAMREC ticks ", 16)) {
                /* lane eng-e1l: no word of the camera record may be an infinity or not a number at a tick's end */
                unsigned ticks = 0, bad = 0, first = 0, word = 0;
                unsigned long bits = 0;
                long nearp = 0, farp = 0;
                camrec_seen = tmatch(line, "E1 CAMREC ticks %u non-finite %u (first tick %u word %u bits %x) near %d far %d",
                                     NULL, &ticks, &bad, &first, &word, &bits, &nearp, &farp);
                camrec_ticks = ticks;   /* lane eng-e1o: ticks checked, compared with the scene's ticks below */
                if ((!camrec_seen || bad) && !e->why[0])
                    snprintf(e->why, sizeof(e->why), "camera record not finite: %u of %u ticks (first tick %u)", bad, ticks, first);
                (void)word; (void)bits; (void)nearp; (void)farp;
            }
        }
    }
    if (!strcmp(s->kind, "e1") && e->report_ok && done && !pool_seen && !e->why[0])
        snprintf(e->why, sizeof(e->why), "no E1 POOL line in the report");
    /* lane eng-e1j (H-016.2): timing and function runs alike must report their conversions (a missing line fails) */
    if (!strcmp(s->kind, "e1") && e->report_ok && done && !pub_seen && !e->why[0])
        snprintf(e->why, sizeof(e->why), "no E1 PUB line in the report");
    /* lane eng-look1: timing and function runs alike report the weapon's draw against the hosted gate (a missing line fails) */
    if (!strcmp(s->kind, "e1") && e->report_ok && done && !wep_seen && !e->why[0])
        snprintf(e->why, sizeof(e->why), "no E1 WEP line in the report");
    /* lane eng-e1l: timing and function runs alike report the camera record's finite check (a missing line fails) */
    if (!strcmp(s->kind, "e1") && e->report_ok && done && !camrec_seen && !e->why[0])
        snprintf(e->why, sizeof(e->why), "no E1 CAMREC line in the report");
    /* lane eng-e1k (H-016.6): a timing scene is OK only with a complete record: the run's kind line, 600 picture rows
       once each (41-640), drawn images in presented mode with 600 measured flip intervals (a headless image: 600 tick
       intervals), zero release-queue drops, the after-play memory line (its guard is a refusal line of its own) */
    /* lane eng-e1o (H-017.6, H-017.7): every E1-family scene, timing or function, has its run line in the schedule's
       kind and its drawing mode, its tick count, the camera record checked on every one of those ticks, and the
       in-play file count line */
    if (!strcmp(s->kind, "e1") && e->report_ok && done && !e->why[0]) {
        if (!g_runkind[0]) snprintf(e->why, sizeof(e->why), "no E1 RUN line: timing or function run not said");
        else if (run_lines != 1) snprintf(e->why, sizeof(e->why), "%u E1 RUN lines", run_lines);
        else if (g_function == 2) snprintf(e->why, sizeof(e->why), "run line not read: %.40s", g_runkind);
        else if (s->timing && g_function)
            snprintf(e->why, sizeof(e->why), "run kind: image says function, schedule says timing");
        else if (!s->timing && !g_function)
            snprintf(e->why, sizeof(e->why), "run kind: image says timing, schedule says function");
        else if (s->headless != (g_headless != 0))
            snprintf(e->why, sizeof(e->why), "mode: image %s, schedule %s", g_headless ? "headless" : "drawn",
                     s->headless ? "headless" : "drawn");
        else if (!g_done_seen) snprintf(e->why, sizeof(e->why), "no E1 DONE tick count (or not a number)");
        else if (camrec_ticks != g_done_ticks)
            snprintf(e->why, sizeof(e->why), "camera record checked %u of %u ticks", camrec_ticks, g_done_ticks);
        /* lane eng-e1p (H-018.3): the image's tick count (and with it the camera ticks) against the rows received: the
           last row, plus the rows the client dropped past its row budget (its closing line, required) */
        else if (!g_cl_seen) snprintf(e->why, sizeof(e->why), "no cl-send closing count (or a field not a number)");
        else if (g_done_ticks != g_last_row + g_cl_rows_dropped)
            snprintf(e->why, sizeof(e->why), "E1 DONE says %u ticks, rows end at %u (+%u dropped)", g_done_ticks, g_last_row,
                     g_cl_rows_dropped);
        else if (!g_files_seen) snprintf(e->why, sizeof(e->why), "no E1 FILES line (or a field not a number)");
        else if (s->timing && g_files_opens)
            snprintf(e->why, sizeof(e->why), "files opened in play %u (first %.30s)", g_files_opens, g_files_first);
        /* lane eng-e1p (H-018.4): reads on disc-backed handles and CD drive requests in play */
        else if (s->timing && (g_files_reads || g_files_sectors))
            snprintf(e->why, sizeof(e->why), "disc read in play: reads %u, sector requests %u", g_files_reads, g_files_sectors);
        /* lane eng-e1p (H-018.1): camera tracks converted at room load, none in play */
        else if (!g_ctrack_seen) snprintf(e->why, sizeof(e->why), "no E1 CAMTRACK line (or a field not a number)");
        else if (s->timing && g_ctrack_inplay)
            snprintf(e->why, sizeof(e->why), "camera tracks converted in play %u", g_ctrack_inplay);
    }
    if (!strcmp(s->kind, "e1") && e->report_ok && done && !e->why[0] && s->timing) {
        unsigned distinct = 0, counted = 0;
        for (unsigned i = 0; i < E1_COUNT; ++i) { distinct += g_seen[i]; counted += g_seen[i] && g_fields[i] != 0; }
        if (!g_mem_after) snprintf(e->why, sizeof(e->why), "no after-play memory line");
        else if (g_mem_after != 1) snprintf(e->why, sizeof(e->why), "%u after-play memory lines", g_mem_after);
        else if (!g_mem_ok) snprintf(e->why, sizeof(e->why), "%.60s", g_mem_why);
        else if (g_mem_guard_broken) snprintf(e->why, sizeof(e->why), "after-play memory line: stack guard BROKEN");
        else if (g_mem_lost) snprintf(e->why, sizeof(e->why), "after-play memory line: %u heap blocks not tracked", g_mem_lost);
        else if (g_mem_stack <= 0) snprintf(e->why, sizeof(e->why), "after-play memory line: stack high water %ld", g_mem_stack);
        else if (g_mem_arena < 0) snprintf(e->why, sizeof(e->why), "after-play memory line: arena margin %ld", g_mem_arena);
        else if (!s->headless && g_mem_vram < 0)   /* -1 is the headless image's sentinel: never a drawn scene's */
            snprintf(e->why, sizeof(e->why), "after-play memory line: drawn scene, vram free %ld", g_mem_vram);
        else if (s->headless && g_mem_vram != -1)
            snprintf(e->why, sizeof(e->why), "after-play memory line: headless scene, vram free %ld", g_mem_vram);
        else if (g_bad_rows) snprintf(e->why, sizeof(e->why), "rows: %u with a field that is not a number", g_bad_rows);
        else if (fields_bad) snprintf(e->why, sizeof(e->why), "E1 FIELDS line: a field missing or not a number");
        else if (g_dups || distinct != E1_COUNT)
            snprintf(e->why, sizeof(e->why), "rows: %u of 600 pictures, %u repeated", distinct, g_dups);
        else if (!g_fmode[0]) snprintf(e->why, sizeof(e->why), "no E1 FIELDS line");
        else if (!g_headless && strcmp(g_fmode, "presented"))
            snprintf(e->why, sizeof(e->why), "drawn image in %s mode, not presented flips", g_fmode);
        else if (g_headless && strcmp(g_fmode, "tick"))
            snprintf(e->why, sizeof(e->why), "headless image in %s mode", g_fmode);
        else if (!g_drops_seen || g_drops)   /* before the intervals: a dropped release also costs a flip */
            snprintf(e->why, sizeof(e->why), g_drops_seen ? "release queue drops %u" : "no release queue count", g_drops);
        else if (counted != E1_COUNT)
            snprintf(e->why, sizeof(e->why), "%s intervals: %u of 600 measured", g_fmode, counted);
        else {   /* lane eng-e1p (H-018.3): the FIELDS line's own counts recomputed from the rows received */
            unsigned rc = 0, rover = 0, rworst = 0, rpic = 0;
            for (unsigned i = 0; i < E1_COUNT; ++i) {
                if (!g_seen[i] || !g_fields[i]) continue;
                ++rc;
                rover += g_fields[i] > 2;
                if (g_fields[i] > rworst) { rworst = g_fields[i]; rpic = i + E1_FIRST; }
            }
            if (g_pictures != g_last_row + g_cl_rows_dropped)
                snprintf(e->why, sizeof(e->why), "E1 FIELDS says %u pictures, rows end at %u (+%u dropped)", g_pictures,
                         g_last_row, g_cl_rows_dropped);
            else if (rc != g_fl_counted || rover != g_fl_over || rworst != g_fl_worst || rpic != g_fl_worst_pic)
                snprintf(e->why, sizeof(e->why), "E1 FIELDS %u/%u/%u@%u, rows %u/%u/%u@%u", g_fl_counted, g_fl_over,
                         g_fl_worst, g_fl_worst_pic, rc, rover, rworst, rpic);
        }
    }
    if (!e->why[0] && e->exit_code) snprintf(e->why, sizeof(e->why), "exit %d", (int)e->exit_code);   /* after the
                                                                    report: a refusal line says more than its exit code */
    if (!strcmp(s->kind, "e1")) e1_summary(e);
    e->rows = !strcmp(s->kind, "bench") ? windows : g_rows;
    if (!e->why[0] && !e->rows && !g_function) snprintf(e->why, sizeof(e->why), "no rows in the report");
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
    if (g_plan_refused[0]) {   /* lane eng-e1p (H-018.3): a schedule that does not parse whole: refused, nothing run */
        printf("CDISC START %s: plan crc %08x\n", LOADER_BUILD, (unsigned)g_plan_crc);
        printf("CDISC SCHEDULE REFUSED: %s\n", g_plan_refused);
        printf("CDISC SUMMARY BEGIN %s run 00000000 boots 1\n", LOADER_BUILD);
        printf("CDISC SUMMARY END FAILED: %s\n", g_plan_refused);
        vid_clear(0, 0, 0);
        line_at(0, RED, "FAILED: SCHEDULE DOES NOT PARSE");
        line_at(1, RED, "%.52s", g_plan_refused);
        for (;;) thd_sleep(1000);
    }
    if (!planned) {
        line_at(0, RED, "RE4DC CONSOLE DISC: NO /cd/SCENES.TXT");
        printf("CDISC no plan\n");
        for (;;) thd_sleep(1000);
    }
    if (g_listed > SEL_MAX) {   /* lane eng-e1n: more entries than the selector can run: refused, nothing run */
        printf("CDISC START %s: %u scenes, plan crc %08x\n", LOADER_BUILD, g_listed, (unsigned)g_plan_crc);
        printf("CDISC SCHEDULE REFUSED: schedule has %u scenes, the selector runs %u\n", g_listed, (unsigned)SEL_MAX);
        printf("CDISC SUMMARY BEGIN %s run 00000000 boots 1\n", LOADER_BUILD);
        printf("CDISC SUMMARY END FAILED: schedule has %u scenes, the selector runs %u\n", g_listed, (unsigned)SEL_MAX);
        vid_clear(0, 0, 0);
        line_at(0, RED, "FAILED: SCHEDULE HAS %u SCENES, SELECTOR RUNS %u", g_listed, (unsigned)SEL_MAX);
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
        else if (s->plan_err[0]) fail(i, "%s", s->plan_err);   /* lane eng-e1o: a kind without run and mode */
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
