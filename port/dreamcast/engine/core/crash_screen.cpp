// The engine's crash screen (lane eng-crash1, 2026-11-22; plan 3.3 section 8, SALVAGE_20261121.md row 44).
//
// Lifted from the old port: port/dreamcast/game/platform/crash_screen.cpp on origin/t15/int, last changed in commit
// 503f38de14180f912b39d938d04869cbfe6caaee, in its release form (CRASH_SCREEN=1 CRASH_TASK_DETAIL=1; Test 27.2, testers
// photographed it, issue #63). Taken as it was: the BIOS thin font copied into RAM at boot (12 x 24, 96 glyphs) so the
// fault path never calls the BIOS (its font lock is shared with the GD-ROM syscalls); put_text into the frame buffer
// being scanned out (FB_R_SOF1); the in-flight render waited out before drawing; the KOS thread list by tid with
// state, saved pc / pr and wait message; the return-address scan of a saved stack (words just past a jsr / bsr / bsrf);
// the newest log lines, oldest first, cut to the screen width; the dbgio ring handler of the old fault.cpp (the log ring
// is every line the program prints).
// Left out (old-port globals and hooks the engine does not have): the game task scheduler's rows (re4dc_task_brief,
// task_detail, missing_detail: the engine runs its ticks on one thread, no task slots), re4dc_stage / re4dc_ui_frame,
// the HALT and MISSING entry points, the PVR latch, overlay, VRAM-ring, heap-event, issue-52 and RES_MODES rows, the
// 30 s hang watchdog thread (it woke once a second, a thread switch inside the timed pictures, which lane eng-loop2
// removed from the console loop for that reason; on the console disc a hang is the loader's deadline, CL_RUN_TIMEOUT),
// and /cd/dc/crashtest.txt (replaced by the engine boot file CRASHCTL below).
// New (the engine's, marked "new:" below): the scene and tick row from the engine's record (image, scene, route room,
// e1_tick, the loop stage e1_state[0], the console loop's arguments), the memory row (image end, sbrk, the behaviour
// arena, the faulting stack pointer, the main stack's used bytes from its paint), the faulting context's return-address
// row, the in-play log lines flushed before the log rows (they are held in RAM during the ticks, core/globals.cpp), the
// serial copy of every row ("CRASHSCREEN ..."), the still request for the Flycast runner (m1_state, as the STILLS boot
// option hands a picture over), the hand-over to the console loop's own crash handler after a hold, and CRASHCTL.
//
// Cost when nothing faults: e1_crash_boot runs once before play; the only code after it is the ring handler's copy of
// each printed byte (printing is outside the timed pictures: core/globals.cpp buffers e1_log during the ticks). Nothing
// is on the per-picture path.
//
// CRASHCTL (a control, never on a play disc): "<kind> <tick>", kind addr (a 32-bit read of the odd address 8c0abcd1:
// a data address error, event 0e0, TEA the address) or ill (the illegal instruction fffd: event 180); default "addr 300".
// A thread above the main thread's priority waits for that tick of play and faults there; the armed line names the
// planted pc and address, which tools/engine/crashcheck.py compares with the screen's serial copy.
#include <kos.h>
#include <kos/dbgio.h>
#include <dc/biosfont.h>
#include <dc/video.h>
#include <dc/pvr.h>
#include <arch/irq.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "e1_core.h"
#include "crash_screen.h"

extern volatile uint32_t e1_tick;      // core/main.cpp
extern volatile uint32_t e1_state[8];  // core/main.cpp: 0 stage (4 = the ticks), 1 tick
extern volatile uint32_t m1_state[8];  // core/draw_e1.c: 2 still request, 3 acknowledge, 4 frame buffer, 5 stage
extern "C" {
void e1_log(const char* fmt, ...);
void e1_log_flush(void);                        // core/globals.cpp: the lines held during the ticks
const char* cl_args(void) __attribute__((weak));   // loader/client.c (SENDABLE=1 only)
extern char e1_image_end asm("_end");
extern uintptr_t arch_stack_16m;
extern char e1_crash_plant_ld[], e1_crash_plant_ill[];   // the planted instructions' addresses (below)
}
SLIST_HEAD(dbgio_handlers_list, dbgio_handler);   // as kernel/debug/dbgio.c declares its handler list
extern struct dbgio_handlers_list dbgio_handlers;

namespace {
constexpr int kGW = 12, kGH = 24;              // BIOS thin font
int kW = 640, kH = 480, kCols = 640 / kGW, kRows = 480 / kGH;   // from vid_mode at show()
unsigned short g_glyph[96][kGH];               // 12 bits per row, bit 11 = leftmost pixel
bool g_ready;
volatile int g_shown;
kthread_t* g_threads[24];
int g_nthreads;

// ---- the log ring: every byte printed, in front of the serial line (old fault.cpp ringWriteBuffer) ----
constexpr unsigned kLogSize = 2048;   // the screen shows at most 20 rows
char g_log[kLogSize];
volatile unsigned long g_log_head;
dbgio_handler_t* g_prev_dbgio;
int ring_write(const uint8_t* data, int len, int xlat)
{
    if (len > 0 && data) {
        const irq_mask_t old = irq_disable();
        unsigned long h = g_log_head;
        for (int i = 0; i < len; ++i) g_log[(h + i) % kLogSize] = (char) data[i];
        g_log_head = h + (unsigned long) len;
        irq_restore(old);
    }
    return g_prev_dbgio ? g_prev_dbgio->write_buffer(data, len, xlat) : len;
}
int ring_detected(void) { return 1; }
int ring_init(void) { return 0; }
int ring_shutdown(void) { return g_prev_dbgio ? g_prev_dbgio->shutdown() : 0; }
int ring_irq(int mode) { return g_prev_dbgio ? g_prev_dbgio->set_irq_usage(mode) : 0; }
int ring_flush(void) { return g_prev_dbgio ? g_prev_dbgio->flush() : 0; }
int ring_read(uint8_t* data, int len) { return g_prev_dbgio ? g_prev_dbgio->read_buffer(data, len) : -1; }
dbgio_handler_t g_ring = {"e1-ring", ring_detected, ring_init, ring_shutdown, ring_irq, ring_flush, ring_write, ring_read, {NULL}};

// ---- the rows: composed first, then drawn, then copied to the serial line ----
constexpr int kMaxRows = 24, kLine = 64;   // 20 rows of 24 lines at 480
char g_row[kMaxRows][kLine];
unsigned short g_rowc[kMaxRows];
int g_nrows;
void row(unsigned short fg, const char* fmt, ...) __attribute__((format(printf, 2, 3)));
void row(unsigned short fg, const char* fmt, ...)
{
    if (g_nrows >= kMaxRows || g_nrows >= kRows) return;
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(g_row[g_nrows], kLine, fmt, ap);
    va_end(ap);
    g_rowc[g_nrows++] = fg;
}

int collect(kthread_t* t, void*)
{
    if (g_nthreads < 24 && t->state != STATE_FINISHED && t->state != STATE_ZOMBIE && strcmp(t->label, "[idle]"))
        g_threads[g_nthreads++] = t;
    return 0;
}
bool trace_waiter(const kthread_t* t)
{
    return t->state == STATE_WAIT && strcmp(t->label, "[reaper]") &&
           (!t->wait_timeout || !strcmp(t->label, "[kernel]"));
}

// Return-address candidates on a saved stack (old crash_screen.cpp's waiter rows): words pointing just past a jsr /
// bsr / bsrf, newest first, as the low 24 bits of 8cXXXXXX; symbolize with addr2line.
void bt_row(const char* tag, unsigned long sp_word, unsigned short fg)
{
    char line[kLine];
    const unsigned long* sp = (const unsigned long*) (sp_word & ~3ul);
    int n = snprintf(line, sizeof(line), "%s", tag), found = 0;
    for (int w = 0; w < 256 && found < 7; ++w) {
        const unsigned long a = (unsigned long) (sp + w);
        if (a < 0x8c010000ul || a >= 0x8d000000ul) break;
        const unsigned long v = sp[w];
        if ((v & 1) || v < 0x8c010004ul || v >= 0x8d000000ul) continue;
        const unsigned op = *(const unsigned short*) (v - 4);
        if ((op & 0xF0FF) != 0x400B && (op & 0xF000) != 0xB000 && (op & 0xF0FF) != 0x0003) continue;
        if (n + 7 > kCols) break;  // never truncate a return address in the photograph
        n += snprintf(line + n, sizeof(line) - n, " %06lx", v & 0xFFFFFFul);
        ++found;
    }
    row(fg, "%s", line);
}

// Fields counted from the sync status with interrupts off (SPG_STATUS bit 13, vsync): the hold and the render wait.
void wait_fields(unsigned n)
{
    volatile uint32_t* spg = (volatile uint32_t*) 0xa05f810c;
    for (unsigned k = 0; k < n; ++k) {
        while (*spg & 0x2000) {}
        while (!(*spg & 0x2000)) {}
    }
}

void* g_fb;
bool g_fb32;
void put_text(int col, int r, const char* s, unsigned short fg)
{
    for (; *s && col < kCols; ++s, ++col) {
        int c = (unsigned char) *s;
        if (c < 32 || c > 127) c = '?';
        const unsigned short* g = g_glyph[c - 32];
        for (int y = 0; y < kGH; ++y) {
            const int at = (r * kGH + y) * kW + col * kGW;
            for (int x = 0; x < kGW; ++x) {
                const unsigned short px = (g[y] >> (11 - x)) & 1 ? fg : 0x0008;
                if (g_fb32) ((uint32_t*) g_fb)[at + x] = (uint32_t) (px >> 11) << 19 | (uint32_t) (px >> 5 & 63) << 10 | (uint32_t) (px & 31) << 3;
                else ((unsigned short*) g_fb)[at + x] = px;
            }
        }
    }
}

const char* image_name()
{
#if defined(E2_FIGHT)
    return "FIGHT";
#elif defined(E2_BOSS)
    return "BOSS";
#else
    return "E1";
#endif
}

void show(const char* kind, const char* detail, const irq_context_t* ctx)
{
    if (!g_ready || g_shown) return;
    g_shown = 1;
    wait_fields(2);  // let an in-flight PVR render finish before drawing over the buffer on screen
    if (vid_mode) {
        kW = vid_mode->width;
        kH = vid_mode->height;
        kCols = kW / kGW;
        kRows = kH / kGH;
        g_fb32 = vid_mode->pm == PM_RGB888P || vid_mode->pm == PM_RGB0888;
    }
    g_fb = (void*) (PVR_RAM_BASE | (PVR_GET(PVR_FB_ADDR) & (PVR_RAM_SIZE - 1)));
    g_nrows = 0;
    row(0xFFE0, "RE4DC engine stopped - please photograph this screen");
    row(0xF800, "%s %s", kind, detail);
    // new: the scene and tick from the engine's record
    row(0xFFFF, "%s scene %s room %03x tick %lu stage %lu", image_name(), e1_scene == E1_SCENE_HILL ? "hill" : "village",
        e1_route().room, (unsigned long) e1_tick, (unsigned long) e1_state[0]);
    if (cl_args) row(0xFFFF, "args %.56s", cl_args());
    // new: the memory row (no allocator call: the fault may be inside it)
    {
        const uintptr_t lo = arch_stack_16m - 64 * 1024;
        uintptr_t a = lo;
        while (a < arch_stack_16m && *(volatile uint32_t*) a == 0x5a5aa5a5u) a += 4;   // core/memmap.cpp's paint
        row(0xFFFF, "mem end %08lx sbrk %08lx sp %08lx stk %lu", (unsigned long) (uintptr_t) &e1_image_end,
            (unsigned long) (uintptr_t) sbrk(0), ctx ? (unsigned long) ctx->r[15] : 0ul, (unsigned long) (arch_stack_16m - a));
    }
    // new: the faulting context's return addresses
    if (ctx) bt_row("Fbt", ctx->r[15], 0xFFE0);
    // Threads, from the KOS thread list by tid (old crash_screen.cpp): tid, label, state, saved pc (pr when it
    // differs), and for a blocked one the wait message + object ("ever" = no timeout); * = the faulting thread.
    g_nthreads = 0;
    thd_each(collect, nullptr);
    for (int i = 1; i < g_nthreads; ++i)
        for (int j = i; j > 0 && g_threads[j]->tid < g_threads[j - 1]->tid; --j) {
            kthread_t* x = g_threads[j];
            g_threads[j] = g_threads[j - 1];
            g_threads[j - 1] = x;
        }
    kthread_t* waiters[3];
    int nwait = 0;
    for (int i = 0; i < g_nthreads && g_nrows < kRows - 6; ++i) {
        kthread_t* t = g_threads[i];
        const bool cur = t == thd_current;
        const unsigned long pc = cur && ctx ? ctx->pc : t->context.pc, pr = cur && ctx ? ctx->pr : t->context.pr;
        char line[kLine];
        int n = snprintf(line, sizeof(line), "t%d %.8s s%d %08lx%s", (int) t->tid, t->label, (int) t->state, pc, cur ? "*" : "");
        const bool wait = t->state == STATE_WAIT;
        if (!wait && pr != pc && n < (int) sizeof(line)) n += snprintf(line + n, sizeof(line) - n, " pr %08lx", pr);
        if (wait && n < (int) sizeof(line))
            snprintf(line + n, sizeof(line) - n, " %.12s %08lx%s", t->wait_msg ? t->wait_msg : "-",
                     (unsigned long) t->wait_obj, t->wait_timeout ? "" : " ever");
        row(0x07FF, "%s", line);
        if (!cur && trace_waiter(t) && nwait < 3) waiters[nwait++] = t;
    }
    for (int i = 0; i < nwait && g_nrows < kRows - 4; ++i) {
        char tag[8];
        snprintf(tag, sizeof(tag), "bt%d", (int) waiters[i]->tid);
        bt_row(tag, waiters[i]->context.r[15], 0xFFE0);
    }
    // new: the lines held during the ticks go out (serial, the console loop's report, the ring) before the log rows
    if (e1_state[0] == 4) e1_log_flush();
    // Newest log lines, oldest first, cut to the screen width (old crash_screen.cpp).
    const int head_rows = g_nrows;
    {
        const unsigned long head = g_log_head;
        const int want = kRows - g_nrows;
        unsigned long pos = head, start = head > kLogSize ? head - kLogSize : 0;
        int lines = 0;
        while (pos > start && lines <= want) {
            --pos;
            if (g_log[pos % kLogSize] == '\n' && pos + 1 != head) ++lines;
        }
        if (lines > want) ++pos;
        char line[kLine];
        int col = 0;
        const int width = kCols < kLine - 1 ? kCols : kLine - 1;
        for (; pos < head && g_nrows < kRows; ++pos) {
            const char c = g_log[pos % kLogSize];
            if (c == '\n' || col == width) {
                line[col] = 0;
                row(0xC618, "%s", line);
                col = 0;
                if (c == '\n') continue;
            }
            line[col++] = c;
        }
        if (col && g_nrows < kRows) {
            line[col] = 0;
            row(0xC618, "%s", line);
        }
    }
    // Draw: the buffer on screen now, the display left where it is.
    const unsigned pixels = (unsigned) kW * (unsigned) kH;
    for (unsigned i = 0; i < pixels; ++i) {
        if (g_fb32) ((uint32_t*) g_fb)[i] = 0x00000040u;
        else ((unsigned short*) g_fb)[i] = 0x0008;
    }
    for (int r = 0; r < g_nrows; ++r) put_text(0, r, g_row[r], g_rowc[r]);
    // new: the serial copy (one line a row; the log rows are marked, the serial line has them already)
    char line[kLine + 32];
    for (int r = 0; r < g_nrows; ++r) {
        const int n = snprintf(line, sizeof(line), "CRASHSCREEN %s%s\n", r >= head_rows ? "log| " : "", g_row[r]);
        dbgio_write_buffer_xlat((const uint8_t*) line, n > (int) sizeof(line) - 1 ? (int) sizeof(line) - 1 : n);
    }
    const int n = snprintf(line, sizeof(line), "CRASHSCREEN END rows %d of %d (%dx%d)\n", g_nrows, kRows, kW, kH);
    dbgio_write_buffer_xlat((const uint8_t*) line, n);
    dbgio_flush();
    // new: hand the picture to the Flycast runner (s/fly.py --stills: m1_state 2 request, 3 acknowledge, 4 frame buffer
    // in its 64-bit-area form, 5 = 3 open), at most 3 s, as core/draw_e1.c's STILLS does
    m1_state[4] = 0xa5000000u + 2u * (*(volatile uint32_t*) 0xa05f8050 & 0x7ffffcu);
    m1_state[5] = 3;
    m1_state[2] = 4999;
    for (unsigned k = 0; k < 180 && m1_state[3] != m1_state[2]; ++k) wait_fields(1);
}

irq_cb_t g_prev_exc, g_prev_dbl;

void on_fault(irq_t code, irq_context_t* ctx, void* data)
{
    (void) data;
    irq_disable();
    const unsigned long tea = *(volatile unsigned long*) 0xff00000c;      // the faulting data address
    const unsigned long expevt = *(volatile unsigned long*) 0xff000024;
    char d[80];
    snprintf(d, sizeof(d), "code %03x pc %08lx pr %08lx addr %08lx", (unsigned) code, ctx ? (unsigned long) ctx->pc : 0ul,
             ctx ? (unsigned long) ctx->pr : 0ul, tea);
    (void) expevt;
    show("FAULT", d, ctx);
    // new: on the console disc the loader's crash handler hands the scene in (the selector marks it FAILED with the
    // event and pc); the screen stays up 8 s first. Booted from its own disc the screen stays until power-off.
    const irq_cb_t& prev = code == EXC_DOUBLE_FAULT ? g_prev_dbl : g_prev_exc;
    if (prev.hdl) {
        wait_fields(480);
        prev.hdl(code, ctx, prev.data);
    }
    for (;;) {}
}

// ---- CRASHCTL: the forced fault at a named tick (a control) ----
int g_ctl_kind;           // 1 addr, 2 ill
unsigned g_ctl_tick;
void __attribute__((noinline)) plant_addr()
{
    uint32_t a = 0x8c0abcd1u;
    __asm__ volatile(".global _e1_crash_plant_ld\n_e1_crash_plant_ld:\n\tmov.l @%0,%0\n" : "+r"(a) : : "memory");
}
void __attribute__((noinline)) plant_ill()
{
    __asm__ volatile(".global _e1_crash_plant_ill\n_e1_crash_plant_ill:\n\t.short 0xfffd\n" : : : "memory");
}
void* ctl_thread(void*)
{
    while (!(e1_state[0] == 4 && e1_tick >= g_ctl_tick)) thd_sleep(1);
    if (g_ctl_kind == 1) plant_addr();
    else plant_ill();
    e1_log("E1 CRASHCTL: the planted fault did not stop the program (tick %lu)\n", (unsigned long) e1_tick);
    return nullptr;
}
}  // namespace

extern "C" void e1_crash_boot(void)
{
    // 12x24 glyphs drawn by the BIOS into a small 16 bpp scratch, kept as bit rows (old crash_screen.cpp).
    static unsigned short scratch[kGW * kGH];
    char s[2] = {0, 0};
    for (int c = 32; c < 128; ++c) {
        s[0] = (char) (c == 127 ? '?' : c);
        memset(scratch, 0, sizeof(scratch));
        bfont_draw_str_ex(scratch, kGW, 0xFFFF, 0, 16, true, s);
        for (int y = 0; y < kGH; ++y) {
            unsigned short bits = 0;
            for (int x = 0; x < kGW; ++x)
                if (scratch[y * kGW + x]) bits |= (unsigned short) (1u << (11 - x));
            g_glyph[c - 32][y] = bits;
        }
    }
    // the log ring in front of the device in use (the console loop's tee when it runs, else the serial line)
    const char* cur = dbgio_dev_get();
    dbgio_handler_t* h;
    SLIST_FOREACH(h, &dbgio_handlers, entry)
        if (cur && !strcmp(h->name, cur)) g_prev_dbgio = h;
    if (g_prev_dbgio) {
        dbgio_add_handler(&g_ring);
        if (dbgio_dev_select("e1-ring") < 0) g_prev_dbgio = nullptr;
    }
    g_prev_exc = irq_get_handler(EXC_UNHANDLED_EXC);
    g_prev_dbl = irq_get_handler(EXC_DOUBLE_FAULT);
    irq_set_handler(EXC_UNHANDLED_EXC, on_fault, nullptr);
    irq_set_handler(EXC_DOUBLE_FAULT, on_fault, nullptr);
    g_ready = true;
    e1_log("E1 CRASH screen ready: ring %s (%u bytes, before %s), fault handlers %s, glyphs %u bytes\n",
           g_prev_dbgio ? "on" : "OFF", kLogSize, cur ? cur : "-", g_prev_exc.hdl ? "chained to the console loop's" : "own",
           (unsigned) sizeof(g_glyph));
    file_t f = fs_open("/cd/CRASHCTL", O_RDONLY);
    if (f < 0) return;
    char t[32] = {0};
    const ssize_t n = fs_read(f, t, sizeof(t) - 1);
    fs_close(f);
    g_ctl_kind = 1;
    g_ctl_tick = 300;
    if (n > 0) {
        if (!strncmp(t, "ill", 3)) g_ctl_kind = 2;
        const char* sp = strchr(t, ' ');
        if (sp && atoi(sp + 1) > 0) g_ctl_tick = (unsigned) atoi(sp + 1);
    }
    e1_log("E1 CRASHCTL armed: %s at tick %u, expect code %03x pc %08lx addr %s (control)\n",
           g_ctl_kind == 1 ? "address fault" : "illegal instruction", g_ctl_tick, g_ctl_kind == 1 ? 0x0e0u : 0x180u,
           (unsigned long) (uintptr_t) (g_ctl_kind == 1 ? e1_crash_plant_ld : e1_crash_plant_ill),
           g_ctl_kind == 1 ? "8c0abcd1" : "-");
    kthread_attr_t a = {};
    a.stack_size = 4096;
    a.prio = PRIO_DEFAULT - 1;   // above the main thread: it runs as soon as its tick is reached
    a.label = "e1crashctl";
    a.create_detached = true;
    thd_create_ex(&a, ctl_thread, nullptr);
}
