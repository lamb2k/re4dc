// CRASH_SCREEN=1 (hardware readiness, default 0): on a real Dreamcast the log ring cannot be read
// without a serial cable, so a fault, a source HALT() or a hang would only leave a frozen picture.
// This draws a report straight into frame buffer 0 and shows it: what stopped, where (PC / PR /
// stage / frame), the threads, and the newest log lines, for the player to photograph.
// - Fault and HALT: called from fault.cpp with interrupts off; it never calls into the BIOS
//   (the BIOS font lock is shared with GD-ROM syscalls), so the ASCII glyphs are copied from the
//   BIOS font into RAM at boot (96 x 36 bytes).
// - Hang: a low-cost watchdog thread checks once a second that the UI frame counter or the PVR
//   frame count moves; after 30 s of neither it draws the report (interrupts stay on, the game is
//   left as it is, so a game that resumes simply draws over it).
// Game logic is untouched: nothing here runs unless the game has already stopped.
#include <kos.h>
#include <dc/biosfont.h>
#include <dc/video.h>
#include <dc/pvr.h>
#include <stdio.h>
#include <string.h>

#include "re4dc_platform.h"
#if defined(RE4DC_CRASH_OVL_LINE) && RE4DC_CRASH_OVL_LINE
extern "C" int re4dc_ovl_crash_line(char* out, int size);   // modules.cpp
#endif
#if defined(RE4DC_ARENA_RING) && RE4DC_ARENA_RING
extern "C" int re4dc_vram_ring_line(unsigned age, char* out, unsigned size);   // vram_pages.cpp (OVL_GUARD=3)
#endif
#if defined(RE4DC_ISSUE52_ACTOR_DIAG) && RE4DC_ISSUE52_ACTOR_DIAG
#include "issue52_actor_diag.h"
#endif
#if RE4DC_CRASH_FAULT_DETAIL
#include "fault_trace.hpp"
#endif
#if RE4DC_KOS_HEAP_CHECK
extern "C" int re4dc_heap_event_line(unsigned age, char* out, unsigned size);
#endif

#if RE4DC_CRASH_SCREEN

extern "C" volatile unsigned long re4dc_stage;
extern "C" volatile unsigned long re4dc_log_head;
extern "C" char re4dc_logbuf[];
extern "C" unsigned re4dc_ui_frame();
extern "C" int re4dc_fixture_read(const char* path, char* buffer, unsigned size);
extern "C" void re4dc_halt(const char* file, int line);
extern "C" void re4dc_task_brief(char* out, unsigned size, const void* wait);  // scheduler.cpp
extern "C" void re4dc_subscreen_brief(char* out, unsigned size) __attribute__((weak));
extern "C" int pvr_present_pending(void) __attribute__((weak));
#if RE4DC_PVR_LATCH
extern "C" int re4dc_pvr_latch_line(unsigned which, char* out, unsigned size) __attribute__((weak));  /* native_ui.cpp */ extern "C" void re4dc_pvr_ready_test_arm(int slices) __attribute__((weak));  // PVR_READY_STRICT; one line: keeps __LINE__
#endif
#ifndef RE4DC_LOG_TRIM
#define RE4DC_LOG_TRIM 0
#endif
static const unsigned kLogSize = 0x10000 - RE4DC_LOG_TRIM;  // mem.cpp RE4DC_LOG_SIZE

#if defined(RE4DC_ISSUE52_ACTOR_DIAG) && RE4DC_ISSUE52_ACTOR_DIAG
struct Issue52ActorSnapshot {
    unsigned phase, frame, room;
    unsigned long base, actor;
};
static volatile Issue52ActorSnapshot g_issue52_actor{};
static Issue52Attempt g_issue52_attempt{};

extern "C" unsigned re4dc_issue52_begin(unsigned long task, unsigned frame,
    unsigned room, unsigned entry, unsigned id)
{
    const unsigned long base = re4dc_issue52_stage_base();
    const int old = irq_disable();
    const unsigned token = g_issue52_attempt.begin(task, frame, room, entry, id, base);
    irq_restore(old);
    return token;
}
extern "C" unsigned re4dc_issue52_current(unsigned long task, unsigned id)
{
    const int old = irq_disable();
    const unsigned token = g_issue52_attempt.current(task, id);
    irq_restore(old);
    return token;
}
extern "C" void re4dc_issue52_detail(unsigned token, unsigned long task,
    unsigned kind, int a, int b)
{
    const int old = irq_disable();
    g_issue52_attempt.detail(token, task, kind, a, b);
    irq_restore(old);
}
extern "C" void re4dc_issue52_finish(unsigned token, unsigned long task,
    unsigned reason, unsigned long actor, unsigned frame)
{
    const unsigned long base = re4dc_issue52_stage_base();
    const int old = irq_disable();
    g_issue52_attempt.finish(token, task, reason, actor, frame, base);
    irq_restore(old);
}

extern "C" void re4dc_issue52_actor_note(unsigned phase, unsigned frame,
                                         unsigned room, unsigned long actor)
{
    const unsigned long base = re4dc_issue52_stage_base();
    const int old = irq_disable();
    g_issue52_actor.phase = 0;
    g_issue52_actor.frame = frame;
    g_issue52_actor.room = room;
    g_issue52_actor.base = base;
    g_issue52_actor.actor = actor;
    g_issue52_actor.phase = phase;
    irq_restore(old);
}

static bool issue52_actor_line(char* out, unsigned size)
{
    // The crash path reads copied integers only, never source lists/actors or
    // the overlay's storage. Retain the original register/stack snapshot.
    const int old = irq_disable();
    const Issue52ActorSnapshot s{g_issue52_actor.phase, g_issue52_actor.frame,
        g_issue52_actor.room, g_issue52_actor.base, g_issue52_actor.actor};
    irq_restore(old);
    if (!s.phase) return false;
    snprintf(out, size, "I52 %u r%03x b%08lx a%08lx f%u",
             s.phase, s.room, s.base, s.actor, s.frame);
    return true;
}

static bool issue52_attempt_line(char* out, unsigned size)
{
    const int old = irq_disable();
    const Issue52Attempt s = g_issue52_attempt;
    irq_restore(old);
    if (!s.serial) return false;
    // Integers copied while live only. Pending/abandoned is not a causal result.
    snprintf(out, size, "52 t%u s%u w%x c%x R%x q%d r%d n%x", s.serial,
        s.state, s.reason, s.construct, s.read_path, s.request, s.poll, s.negatives);
    return true;
}
#endif

namespace {
constexpr int kGW = 12, kGH = 24;              // BIOS thin font
int kW = 640, kH = 480, kCols = 640 / kGW, kRows = 480 / kGH;  // from vid_mode at show()
unsigned short g_glyph[96][kGH];               // 12 bits per row, bit 11 = leftmost pixel
bool g_ready;
unsigned short* g_fb;  // the frame buffer being scanned out (FB_R_SOF1), as vid_set_start maps it
volatile int g_shown;
kthread_t* g_threads[24];
int g_nthreads;
#if RE4DC_CRASH_FAULT_DETAIL
struct FaultSnapshot {
    std::uint32_t r[16], sr, stack_lo, stack_hi;
    int tid;
    bool valid;
};
FaultSnapshot g_fault{};
#endif

// First-failure state survives the 30-second watchdog delay. In issue 9 the
// missing handler's deliberate sleep obscured a presentation timeout. Current
// versus captured frame/vblank counts also show whether PVR later completed.
struct MissingSnapshot {
    char reason[80];
    unsigned ui, frames, vbl, vtx[3], opb[3], isp;
    unsigned asic[3], opb_init;  // issue 9: raw ASIC event status A/B/C (latched even when not enabled)
#if RE4DC_PVR_LATCH
#if RE4DC_PVR_LATCH >= 2
    char latch[6][54];           // latch v2: rows 0..5 (state, totals, ring, rdy, er/max, last two scenes)
#else
    char latch[4][54];           // re4dc_pvr_latch_line 0..3 at the failure (one screen row each)
#endif
#endif
    int pending, ta_ready;
    bool valid, pvr_valid;
#if RE4DC_CRASH_TASK_DETAIL
    kthread_t* thread;  // issue 23: the thread that called re4dc_missing (it then sleeps: a timed wait, not traced)
#endif
};
MissingSnapshot g_missing{};

void capture_missing(const char* name)
{
    const int old = irq_disable();
    if (!g_missing.valid) {
        snprintf(g_missing.reason, sizeof(g_missing.reason), "%s", name ? name : "unknown");
        g_missing.ui = re4dc_ui_frame();
        pvr_stats_t st{};
        g_missing.pvr_valid = pvr_get_stats(&st) == 0;
        if (g_missing.pvr_valid) {
            g_missing.frames = st.frame_count;
            g_missing.vbl = st.vbl_count;
            g_missing.pending = pvr_present_pending ? pvr_present_pending() : -1;
            g_missing.ta_ready = pvr_check_ready();
            g_missing.vtx[0] = PVR_GET(PVR_TA_VERTBUF_START);
            g_missing.vtx[1] = PVR_GET(PVR_TA_VERTBUF_POS);
            g_missing.vtx[2] = PVR_GET(PVR_TA_VERTBUF_END);
            g_missing.opb[0] = PVR_GET(PVR_TA_OPB_START);
            g_missing.opb[1] = PVR_GET(PVR_TA_OPB_POS); // raw register; word units on hardware
            g_missing.opb[2] = PVR_GET(PVR_TA_OPB_END);
            g_missing.isp = PVR_GET(PVR_ISP_VERTBUF_ADDR);
            g_missing.opb_init = PVR_GET(PVR_TA_OPB_INIT);
            // A pending render-done bit (A bit 2) means the interrupt was lost; C bits 0..4 are
            // ISP out of memory, strip halt, OPB out of memory, TA input error, TA input overflow.
            g_missing.asic[0] = *(volatile uint32_t*) ASIC_ACK_A;
            g_missing.asic[1] = *(volatile uint32_t*) ASIC_ACK_B;
            g_missing.asic[2] = *(volatile uint32_t*) ASIC_ACK_C;
#if RE4DC_PVR_LATCH
            for (unsigned i = 0; i < sizeof(g_missing.latch) / sizeof(g_missing.latch[0]); ++i)
                if (!re4dc_pvr_latch_line || !re4dc_pvr_latch_line(i, g_missing.latch[i], sizeof(g_missing.latch[i])))
                    g_missing.latch[i][0] = 0;
#endif
        }
#if RE4DC_CRASH_TASK_DETAIL
        g_missing.thread = thd_current;
#endif
        g_missing.valid = true;
    }
    irq_restore(old);
}

int collect(kthread_t* t, void*)
{
    if (g_nthreads < 24 && t->state != STATE_FINISHED && t->state != STATE_ZOMBIE &&
        strcmp(t->label, "re4crash") && strcmp(t->label, "[idle]"))
        g_threads[g_nthreads++] = t;
    return 0;
}

// A timed main-thread wait hid the caller in issue 9. Keep the full signed
// distance to its deadline; ffffffff is a wait object, not a duration.
void wait_detail(char* out, unsigned size, const kthread_t* t, uint64_t now)
{
    if (!t->wait_timeout) {
        snprintf(out, size, "main pr %08lx wait untimed", (unsigned long) t->context.pr);
    } else {
        const uint64_t due = t->wait_timeout;
        snprintf(out, size, "main pr %08lx wait %c%llums", (unsigned long) t->context.pr,
                 due >= now ? '+' : '-', (unsigned long long) (due >= now ? due - now : now - due));
    }
}

bool trace_waiter(const kthread_t* t)
{
    return t->state == STATE_WAIT && strcmp(t->label, "[reaper]") &&
           (!t->wait_timeout || !strcmp(t->label, "[kernel]"));
}

void put_text(int col, int row, const char* s, unsigned short fg)
{
#if RE4DC_CRASH_FAULT_DETAIL
    if (row < 0 || row >= kRows) return;
#endif
    unsigned short* fb = g_fb;
    for (; *s && col < kCols; ++s, ++col) {
        int c = (unsigned char) *s;
        if (c < 32 || c > 127) c = '?';
        const unsigned short* g = g_glyph[c - 32];
        for (int y = 0; y < kGH; ++y) {
            unsigned short* p = fb + (row * kGH + y) * kW + col * kGW;
            for (int x = 0; x < kGW; ++x) p[x] = (g[y] >> (11 - x)) & 1 ? fg : 0x0008;
        }
    }
}

#if RE4DC_CRASH_FAULT_DETAIL
void fault_detail(int& row)
{
    if (!g_fault.valid) return;
    char line[96];
    snprintf(line, sizeof(line), "FAULT t%d sp %08x sr %08x", g_fault.tid, g_fault.r[15], g_fault.sr);
    put_text(0, row++, line, 0xFFE0);
    for (unsigned i = 0; i < 16; i += 4) {
        snprintf(line, sizeof(line), "%x:%08x %x:%08x %x:%08x %x:%08x",
                 i, g_fault.r[i], i+1, g_fault.r[i+1], i+2, g_fault.r[i+2], i+3, g_fault.r[i+3]);
        put_text(0, row++, line, 0xFFFF);
    }
    std::uint32_t candidates[12];
    const unsigned count = re4dc::fault_trace::collect(g_fault.r[15], g_fault.stack_lo, g_fault.stack_hi,
        0x8c010000U, 0x8d000000U, candidates, 12,
        [](std::uint32_t a) { return *reinterpret_cast<const std::uint32_t*>(a); },
        [](std::uint32_t a) { return *reinterpret_cast<const std::uint16_t*>(a); });
    for (unsigned i = 0; i < (count ? count : 1); i += 6) {
        int used = snprintf(line, sizeof(line), "Fbt");
        for (unsigned j = i; j < count && j < i+6; ++j)
            used += snprintf(line+used, sizeof(line)-used, " %06x", candidates[j] & 0xffffffU);
        if (!count) snprintf(line, sizeof(line), "Fbt none (bounded stack candidates)");
        put_text(0, row++, line, 0xFFE0);
    }
}
#endif

#if RE4DC_CRASH_TASK_DETAIL
}  // namespace
extern "C" const void* re4dc_task_waited(const void* wait, int* slot);  // scheduler.cpp
extern "C" void* re4dc_os_thread_kt(const void* thread);                 // os.cpp
namespace {
int find_main_wait(kthread_t* t, void* out)
{
    if (t->state == STATE_WAIT && !strcmp(t->label, "[kernel]")) *(kthread_t**) out = t;
    return 0;
}
// CRASH_TASK_DETAIL (issue 21): the main thread's os-sema wait only says which game task has not yielded; that
// task's own thread is what hangs. Up to three rows (W = waited-on task): slot, tid, label, state, saved pc / pr;
// its wait message, object and timeout (or "not waiting": busy or ready); its return-address candidates.
void task_detail(int& row)
{
    kthread_t* mt = nullptr;
    thd_each(find_main_wait, &mt);
    if (!mt) return;
    int slot = -1;
    const void* th = re4dc_task_waited(mt->wait_obj, &slot);
    if (!th) return;
    const kthread_t* t = (const kthread_t*) re4dc_os_thread_kt(th);
    char line[96];
    if (!t) {
        snprintf(line, sizeof(line), "W slot %d no thread", slot);
        put_text(0, row++, line, 0xFFE0);
        return;
    }
    snprintf(line, sizeof(line), "W slot %d t%d %.8s s%d pc %08lx pr %08lx", slot, (int) t->tid, t->label,
             (int) t->state, (unsigned long) t->context.pc, (unsigned long) t->context.pr);
    put_text(0, row++, line, 0xFFE0);
    if (t->state == STATE_WAIT) {
        const uint64_t now = timer_ms_gettime64(), due = t->wait_timeout;
        if (!due)
            snprintf(line, sizeof(line), "W wait %.16s %08lx ever", t->wait_msg ? t->wait_msg : "-",
                     (unsigned long) t->wait_obj);
        else
            snprintf(line, sizeof(line), "W wait %.16s %08lx %c%llums", t->wait_msg ? t->wait_msg : "-",
                     (unsigned long) t->wait_obj, due >= now ? '+' : '-',
                     (unsigned long long) (due >= now ? due - now : now - due));
    } else {
        snprintf(line, sizeof(line), "W not waiting (s%d: busy or ready)", (int) t->state);
    }
    put_text(0, row++, line, 0xFFE0);
    const unsigned long* sp = (const unsigned long*) (t->context.r[15] & ~3ul);
    int n = snprintf(line, sizeof(line), "Wbt"), found = 0;
    for (int w = 0; w < 256 && found < 7; ++w) {
        const unsigned long a = (unsigned long) (sp + w);
        if (a < 0x8c010000ul || a >= 0x8d000000ul) break;
        const unsigned long v = sp[w];
        if ((v & 1) || v < 0x8c010004ul || v >= 0x8d000000ul) continue;
        const unsigned op = *(const unsigned short*) (v - 4);
        if ((op & 0xF0FF) != 0x400B && (op & 0xF000) != 0xB000 && (op & 0xF0FF) != 0x0003) continue;
        if (n + 7 > kCols) break;
        n += snprintf(line + n, sizeof(line) - n, " %06lx", v & 0xFFFFFFul);
        ++found;
    }
    put_text(0, row++, line, 0xFFE0);
}
}  // namespace
extern "C" const char* re4dc_dll_fail_line(void) __attribute__((weak));  // modules.cpp (issue 23)
namespace {
// Issue 23: the thread that stopped the game (re4dc_missing then sleeps in a timed wait, so the waiter rows
// leave it out): tid, label, return-address candidates; and a DLL link / unlink failure's module id and reason.
void missing_detail(int& row)
{
    char line[96];
    if (re4dc_dll_fail_line && re4dc_dll_fail_line()[0]) put_text(0, row++, re4dc_dll_fail_line(), 0xFFE0);
    const kthread_t* t = g_missing.valid ? g_missing.thread : nullptr;
    if (!t) return;
    const unsigned long* sp = (const unsigned long*) (t->context.r[15] & ~3ul);
    int n = snprintf(line, sizeof(line), "Mt%d %.8s", (int) t->tid, t->label), found = 0;
    for (int w = 0; w < 256 && found < 6; ++w) {
        const unsigned long a = (unsigned long) (sp + w);
        if (a < 0x8c010000ul || a >= 0x8d000000ul) break;
        const unsigned long v = sp[w];
        if ((v & 1) || v < 0x8c010004ul || v >= 0x8d000000ul) continue;
        const unsigned op = *(const unsigned short*) (v - 4);
        if ((op & 0xF0FF) != 0x400B && (op & 0xF000) != 0xB000 && (op & 0xF0FF) != 0x0003) continue;
        if (n + 7 > kCols) break;
        n += snprintf(line + n, sizeof(line) - n, " %06lx", v & 0xFFFFFFul);
        ++found;
    }
    put_text(0, row++, line, 0xFFE0);
}
#endif
#if RE4DC_RES_MODES
extern "C" void re4dc_res_crash_display(void);  // res_mode.cpp
#endif
// Keeps __LINE__ below as in a build without CRASH_TASK_DETAIL (crash_test's re4dc_halt).
#line 144
void show(const char* kind, const char* detail, bool wait_render)
{
    if (!g_ready || g_shown) return;
    g_shown = 1;
    if (wait_render) {
        for (volatile unsigned i = 0; i < 20000000u; ++i) {
        }  // let an in-flight PVR render finish before drawing over buffer 0
    }
    if (vid_mode) {
        kW = vid_mode->width;
        kH = vid_mode->height;
        kCols = kW / kGW;
        kRows = kH / kGH;
    }
    // Draw into the buffer on screen now; the display is left where it is.
#if RE4DC_RES_MODES
    re4dc_res_crash_display();  // RES_MODES: the 640x480 display layout back (the frame buffers are 640x480)
#endif
    g_fb = (unsigned short*) (PVR_RAM_BASE | (PVR_GET(PVR_FB_ADDR) & (PVR_RAM_SIZE - 1)));
    unsigned short* fb = g_fb;
    for (int i = 0; i < kW * kH; ++i) fb[i] = 0x0008;
    char line[96];
    int row = 0;
    put_text(0, row++, "RE4DC stopped - please raise a ticket with a photo", 0xFFE0);
    put_text(0, row++, "of this screen: github.com/lamb2k/re4dc/issues", 0xFFE0);
    snprintf(line, sizeof(line), "%s %s", kind, detail);
    put_text(0, row++, line, 0xF800);
    snprintf(line, sizeof(line), "stage %08lx  ui frame %u" RE4DC_GD_FMT, re4dc_stage, re4dc_ui_frame() RE4DC_GD_ARGS);
    put_text(0, row++, line, 0xFFFF);
#if defined(RE4DC_CRASH_OVL_LINE) && RE4DC_CRASH_OVL_LINE
    {
        char ol[192];
        if (re4dc_ovl_crash_line(ol, sizeof(ol)))
            for (int k = 0; ol[k] && row < 40; k += 52) { snprintf(line, 53, "%s", ol + k); put_text(0, row++, line, 0x07FF); }
    }
#endif
#if defined(RE4DC_ARENA_RING) && RE4DC_ARENA_RING
    {
        for (unsigned age = 0; age < 12 && row < 40; ++age)
            if (re4dc_vram_ring_line(age, line, 53)) put_text(0, row++, line, 0xF81F);
    }
#endif
#if defined(RE4DC_ISSUE52_ACTOR_DIAG) && RE4DC_ISSUE52_ACTOR_DIAG
    if (issue52_actor_line(line, sizeof(line))) put_text(0, row++, line, 0xFFE0);
    if (issue52_attempt_line(line, sizeof(line))) put_text(0, row++, line, 0xFFE0);
#endif
#if RE4DC_CRASH_FAULT_DETAIL
    fault_detail(row);
#endif
#if RE4DC_KOS_HEAP_CHECK
    for (unsigned age = 0; age < 2; ++age)
        if (re4dc_heap_event_line(age, line, 54)) put_text(0, row++, line, 0xFFE0);
#endif
#if RE4DC_CRASH_TASK_DETAIL
    task_detail(row);  // rows 4..6, before the latch rows (at most 4 + 3 + 6 + 1 of the 20 rows)
    missing_detail(row);
#endif
#line 170
#if RE4DC_CRASH_FAULT_DETAIL
    if (!g_fault.valid) {
#endif
#if RE4DC_PVR_LATCH
    // PVR_LATCH: the same snapshot in two rows, then the latch rows (state, totals, event ring) captured at the
    // first failure; a hang without a failure prints the latch rows as they are now.
    if (g_missing.valid && g_missing.pvr_valid) {
        pvr_stats_t st{};
        pvr_get_stats(&st);
        snprintf(line, sizeof(line), "snap ui%u p%d ta%d pvr %u/%u vb %u/%u", g_missing.ui, g_missing.pending,
                 g_missing.ta_ready, g_missing.frames, (unsigned) st.frame_count, g_missing.vbl,
                 (unsigned) st.vbl_count);
        put_text(0, row++, line, 0xFFFF);
        snprintf(line, sizeof(line), "v%06x/%06x/%06x o%06x/%06x/%06x i%06x", g_missing.vtx[0], g_missing.vtx[1],
                 g_missing.vtx[2], g_missing.opb[0], g_missing.opb[1], g_missing.opb[2], g_missing.isp);
        put_text(0, row++, line, 0xFFFF);
        for (unsigned i = 0; i < sizeof(g_missing.latch) / sizeof(g_missing.latch[0]); ++i)
            if (g_missing.latch[i][0]) put_text(0, row++, g_missing.latch[i], 0x07FF);
    } else if (re4dc_pvr_latch_line) {
        for (unsigned i = 0; i < sizeof(g_missing.latch) / sizeof(g_missing.latch[0]); ++i)
            if (re4dc_pvr_latch_line(i, line, sizeof(line) < 54 ? sizeof(line) : 54)) put_text(0, row++, line, 0x07FF);
    }
#else
    if (g_missing.valid && g_missing.pvr_valid) {
        pvr_stats_t st{};
        pvr_get_stats(&st);
        snprintf(line, sizeof(line), "snap ui%u pending%d ta%d", g_missing.ui,
                 g_missing.pending, g_missing.ta_ready);
        put_text(0, row++, line, 0xFFFF);
        snprintf(line, sizeof(line), "pvr %u/%u vb %u/%u", g_missing.frames, (unsigned)st.frame_count,
                 g_missing.vbl, (unsigned)st.vbl_count);
        put_text(0, row++, line, 0xFFFF);
        snprintf(line, sizeof(line), "vtx %06x/%06x/%06x isp %06x", g_missing.vtx[0],
                 g_missing.vtx[1], g_missing.vtx[2], g_missing.isp);
        put_text(0, row++, line, 0xFFFF);
        snprintf(line, sizeof(line), "opb %06x/%06x/%06x (pos raw)", g_missing.opb[0],
                 g_missing.opb[1], g_missing.opb[2]);
        put_text(0, row++, line, 0xFFFF);
        snprintf(line, sizeof(line), "asic %08x %08x %08x opbi %06x", g_missing.asic[0],
                 g_missing.asic[1], g_missing.asic[2], g_missing.opb_init);
        put_text(0, row++, line, 0xFFFF);
    }
#endif
#if RE4DC_CRASH_FAULT_DETAIL
    }
#endif
#line 210
    if (re4dc_subscreen_brief) {
        re4dc_subscreen_brief(line, sizeof(line));
        if (line[0]) put_text(0, row++, line, 0xFFFF);
    }
    // Threads, from the KOS thread list (issue #2: tids grow with every game task run, so the old
    // tid 1..24 walk, capped at six rows, never showed the re4-task threads the main thread's
    // os-sema wait leads to). Per thread: tid, label, state, saved pc (pr when it differs), and for
    // a blocked one the genwait message + object ("ever" = no timeout). The watchdog, the idle
    // thread and finished records are left out.
    g_nthreads = 0;
    thd_each(collect, nullptr);
    for (int i = 1; i < g_nthreads; ++i)  // by tid
        for (int j = i; j > 0 && g_threads[j]->tid < g_threads[j - 1]->tid; --j) {
            kthread_t* x = g_threads[j];
            g_threads[j] = g_threads[j - 1];
            g_threads[j - 1] = x;
        }
    kthread_t* waiters[3];
    int nwait = 0;
    const void* mainwait = nullptr;
    for (int i = 0; i < g_nthreads && row < kRows - 5; ++i) {
        kthread_t* t = g_threads[i];
        const unsigned long pc = t->context.pc, pr = t->context.pr;
        int n = snprintf(line, sizeof(line), "t%d %.8s s%d %08lx%s", (int) t->tid, t->label, (int) t->state, pc,
                         t == thd_current ? "*" : "");
        const bool wait = t->state == STATE_WAIT;
        if (!wait && pr != pc && n < (int) sizeof(line)) n += snprintf(line + n, sizeof(line) - n, " pr %08lx", pr);
        if (wait && n < (int) sizeof(line))
            snprintf(line + n, sizeof(line) - n, " %.12s %08lx%s", t->wait_msg ? t->wait_msg : "-",
                     (unsigned long) t->wait_obj, t->wait_timeout ? "" : " ever");
        put_text(0, row++, line, 0x07FF);
        if (trace_waiter(t) && nwait < 3) waiters[nwait++] = t;
        if (wait && !strcmp(t->label, "[kernel]")) {
            mainwait = t->wait_obj;
            wait_detail(line, sizeof(line), t, timer_ms_gettime64());
            put_text(0, row++, line, 0xFFFF);
        }
    }
    // The game's task slots (scheduler.cpp): "slot:status/tid", x = thread finished; Y / R marks the slot
    // whose yield / resume semaphore the main thread waits on.
    {
        char tb[160];
        re4dc_task_brief(tb, sizeof(tb), mainwait);
        snprintf(line, sizeof(line), "tasks%s", tb);
        put_text(0, row++, line, 0xFFFF);
        if (strlen(line) > (size_t) kCols && row < kRows - 3) put_text(0, row++, line + kCols, 0xFFFF);
    }
    // Main and untimed waiters: return-address candidates on the saved stack (words pointing just past a
    // jsr / bsr / bsrf), newest first, as the low 24 bits of 8cXXXXXX; symbolize with addr2line.
    for (int i = 0; i < nwait && row < kRows - 2; ++i) {
        kthread_t* t = waiters[i];
        const unsigned long* sp = (const unsigned long*) (t->context.r[15] & ~3ul);
        int n = snprintf(line, sizeof(line), "bt%d", (int) t->tid), found = 0;
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
        put_text(0, row++, line, 0xFFE0);
    }
    // Newest log lines, oldest first, cut to the screen width.
    const unsigned long head = re4dc_log_head;
    const int want = kRows - row;
    unsigned long pos = head, start = head > kLogSize ? head - kLogSize : 0;
    int lines = 0;
    while (pos > start && lines <= want) {
        --pos;
        if (re4dc_logbuf[pos % kLogSize] == '\n' && pos + 1 != head) ++lines;
    }
    if (lines > want) ++pos;  // pos is on the newline before the first shown line
    int col = 0;
    line[0] = 0;
    for (; pos < head && row < kRows; ++pos) {
        const char c = re4dc_logbuf[pos % kLogSize];
        if (c == '\n' || col == kCols) {
            line[col] = 0;
            put_text(0, row++, line, 0xC618);
            col = 0;
            if (c == '\n') continue;
        }
        line[col++] = c;
    }
    if (col && row < kRows) {
        line[col] = 0;
        put_text(0, row++, line, 0xC618);
    }
}

void* watchdog(void*)
{
    unsigned last_ui = re4dc_ui_frame(), still = 0;
    size_t last_pvr = 0;
    for (;;) {
        thd_sleep(1000);
        pvr_stats_t st;
        size_t pvr = pvr_get_stats(&st) == 0 ? st.frame_count : 0;
        const unsigned ui = re4dc_ui_frame();
        if (ui != last_ui || pvr != last_pvr) {
            last_ui = ui;
            last_pvr = pvr;
            still = 0;
            continue;
        }
        if (++still == 30) {
            re4dc_log("CRASH_SCREEN: no new frame for 30 s (ui frame %u)\n", ui);
            show(g_missing.valid ? "MISSING" : "HANG",
                 g_missing.valid ? g_missing.reason : "no new frame for 30 s", false);
        }
    }
    return nullptr;
}

// Test hook: /cd/dc/crashtest.txt ("fault", "halt", "hang", "block", "sleep" or "missing") stops the game that way 20 s after boot,
// so the report can be checked in Flycast. The file is never on a play disc.
int g_test;
}  // namespace
extern "C" {
volatile int re4dc_crashtest_block;  // read by os.cpp OSSignalSemaphore
}
namespace {
void* crash_test(void*)
{
    thd_sleep(20000);
    if (g_test == 1) {
        re4dc_log("CRASH_SCREEN test: fault\n");
        __asm__ volatile(".short 0xfffd");  // illegal instruction: an unhandled exception, the path an
                                            // address error takes on hardware (Flycast raises neither)
    } else if (g_test == 2) {
        re4dc_halt(__FILE__, __LINE__);
    } else if (g_test == 3) {
        for (;;) {
        }  // above the game's priority: no frame is drawn again
    } else if (g_test == 4) {
        re4dc_log("CRASH_SCREEN test: block\n");
        re4dc_crashtest_block = 1;  // the next game task to signal blocks forever; main waits on it
    } else if (g_test == 5) {
        re4dc_log("CRASH_SCREEN test: main timed sleep\n");
        re4dc_crashtest_block = 2;  // the next main-thread signal sleeps, preserving a real saved caller
    } else if (g_test == 6) {
        re4dc_crashtest_block = 1;
        re4dc_missing("native stream completion fence failed");
    }
#if RE4DC_PVR_LATCH
    else if (g_test == 7 && re4dc_pvr_ready_test_arm) {
        // PVR_READY_STRICT: three scenes each see one expired TA-bank slice, then the stop screen (rdy row).
        re4dc_pvr_ready_test_arm(3);
        thd_sleep(3000);
        re4dc_crashtest_block = 1;  // as "missing": the game then stops, so the watchdog draws the screen
        re4dc_missing("crash test: PVR ready wait");
    }
#endif
    return nullptr;
}
}  // namespace

extern "C" void re4dc_crash_screen_init(void)
{
    // 12x24 glyphs drawn by the BIOS into a small 16 bpp scratch, kept as bit rows.
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
    g_ready = true;
    kthread_attr_t a = {};
    a.stack_size = 4096;
    a.prio = 8;  // above the game threads so a busy hang still lets it run; it sleeps 1 s at a time
    a.label = "re4crash";
    thd_create_ex(&a, watchdog, nullptr);
    re4dc_log("CRASH_SCREEN: ready (fault, halt, 30 s hang)\n");
    char t[16] = {0};
    if (re4dc_fixture_read("/cd/dc/crashtest.txt", t, sizeof(t) - 1) > 0) {
        g_test = !strncmp(t, "fault", 5) ? 1 : !strncmp(t, "halt", 4) ? 2 : !strncmp(t, "hang", 4) ? 3
                 : !strncmp(t, "block", 5) ? 4 : !strncmp(t, "sleep", 5) ? 5 : !strncmp(t, "missing", 7) ? 6 : 0;
#if RE4DC_PVR_LATCH
        if (!g_test && !strncmp(t, "pvrwait", 7)) g_test = 7;
#endif
        kthread_attr_t b = {};
        b.stack_size = 4096;
        b.prio = 9;
        b.label = "re4ctest";
        if (g_test) thd_create_ex(&b, crash_test, nullptr);
        re4dc_log("CRASH_SCREEN: test %d armed\n", g_test);
    }
}

extern "C" void re4dc_crash_screen_fault(unsigned code, unsigned long pc, unsigned long pr, unsigned long addr)
{
    char d[80];
    snprintf(d, sizeof(d), "code %03x pc %08lx pr %08lx addr %08lx", code, pc, pr, addr);
    show("FAULT", d, true);
}

#if RE4DC_CRASH_FAULT_DETAIL
extern "C" void re4dc_crash_screen_context(const irq_context_t* ctx)
{
    if (g_fault.valid || !ctx) return;
    for (unsigned i = 0; i < 16; ++i) g_fault.r[i] = ctx->r[i];
    g_fault.sr = ctx->sr;
    const kthread_t* t = thd_current;
    g_fault.tid = t ? t->tid : -1;
    const std::uintptr_t lo = t ? reinterpret_cast<std::uintptr_t>(t->stack) : 0;
    const unsigned bytes = t ? t->stack_size : 0;
    if (lo >= 0x8c010000U && lo < 0x8d000000U && bytes <= 0x8d000000U-lo) {
        g_fault.stack_lo = lo; g_fault.stack_hi = lo + bytes;
    }
    g_fault.valid = true;
}
#endif

extern "C" void re4dc_crash_screen_halt(const char* file, int line)
{
    char d[80];
    const char* base = file ? strrchr(file, '/') : nullptr;
    snprintf(d, sizeof(d), "%s(%d)", base ? base + 1 : (file ? file : "?"), line);
    show("HALT", d, true);
}

extern "C" void re4dc_crash_screen_missing(const char* name)
{
    capture_missing(name);
}

#endif
