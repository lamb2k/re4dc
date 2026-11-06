// Video interface over KOS: mode set-up, retrace wait and the post-retrace
// callback the game's frame loop is paced by (main.cpp postVSyncCallback
// counts vsyncs and resumes the interrupt task scheduler).
#include <kos.h>
#include <dc/vblank.h>
#if defined(RE4DC_PVR_DITHER) && RE4DC_PVR_DITHER
#include <dc/pvr/pvr_regs.h>
#endif

#include "re4dc_platform.h"

typedef unsigned long u32;
typedef int BOOL;
typedef void (*VIRetraceCallback)(void);

static VIRetraceCallback g_postRetrace;
static int g_vblankHandle = -1;
static volatile u32 g_retraceCount;
static int g_black = 1;

extern "C" void re4dc_audio_frame(void);
extern "C" void re4dc_threads_dump(void);
extern "C" void re4dc_threads_freshen(void);
extern int re4dc_diag;

extern "C" volatile unsigned long re4dc_stage;

// Poll-based memory watch: the vblank handler compares a checksum of a region
// every frame and logs the running context the first time it changes.
static volatile unsigned long* g_watchAddr;
static unsigned long g_watchWords;
static unsigned long g_watchSum;
static int g_watchArmed;

static unsigned long watchSum(void)
{
    unsigned long s = 0;
    for (unsigned long i = 0; i < g_watchWords; i++) s = s * 31 + g_watchAddr[i];
    return s;
}

extern "C" void re4dc_watch_set(const void* addr, unsigned long words)
{
    g_watchAddr = (volatile unsigned long*) addr;
    g_watchWords = words;
    g_watchSum = watchSum();
    g_watchArmed = 1;
    re4dc_log("watch: %p x%lu sum %08lx [%08lx %08lx %08lx %08lx]\n", addr, words, g_watchSum,
              g_watchAddr[0], g_watchAddr[1], g_watchAddr[2], g_watchAddr[3]);
}

static void watchPoll(void)
{
    if (!g_watchArmed) return;
    unsigned long s = watchSum();
    if (s == g_watchSum) return;
    g_watchArmed = 0;
    irq_context_t* c = irq_get_context();
    re4dc_log("watch: CHANGED at vblank %lu stage %08lx pc %08lx pr %08lx [%08lx %08lx %08lx %08lx]\n",
              (unsigned long) g_retraceCount, (unsigned long) re4dc_stage, c ? (unsigned long) c->pc : 0,
              c ? (unsigned long) c->pr : 0, g_watchAddr[0], g_watchAddr[1], g_watchAddr[2], g_watchAddr[3]);
    re4dc_threads_dump();
}

#if defined(RE4DC_STALL_DIAG) && RE4DC_STALL_DIAG
// STALL_DIAG=1 (test builds only, dbgwarp.mk; default 0 compiles this out): a 1 s vblank heartbeat
// carrying the frame loop's vsync count, and a log-only stall report once the frame loop has not
// finished an iteration for 3 s (main.cpp resets vsync_cnt every iteration; haltExecCheck HALTs only
// at 3600): the interrupted context, the main thread's saved PC/PR and the return addresses on its
// stack, then every game thread (re4dc_threads_dump). Repeated every 10 s while the stall lasts.
extern volatile int vsync_cnt;  // main.cpp
static kthread_t* g_stallMain;  // the thread VIInit ran on (main's)

static void stallReport(unsigned long stage)
{
    const int v = vsync_cnt;
    if (v < 180 || ((v - 180) % 600) != 0) return;
    irq_context_t* c = irq_get_context();
    re4dc_log("stall: frame loop %d vsyncs vbl=%lu stage=%08lx running=%s pc=%08lx pr=%08lx sr=%08lx\n", v,
              (unsigned long) g_retraceCount, stage, thd_current ? thd_current->label : "?",
              c ? (unsigned long) c->pc : 0ul, c ? (unsigned long) c->pr : 0ul, c ? (unsigned long) c->sr : 0ul);
    kthread_t* m = g_stallMain;
    if (m) {
        irq_context_t* mc = (m == thd_current && c) ? c : &m->context;
        re4dc_log("stall: main thread tid %d state %d wait %s pc=%08lx pr=%08lx sp=%08lx\n", (int) m->tid,
                  (int) m->state, m->wait_msg ? m->wait_msg : "-", (unsigned long) mc->pc, (unsigned long) mc->pr,
                  (unsigned long) mc->r[15]);
        extern char stall_etext[] __asm__("_etext");
        const unsigned long* sp = (const unsigned long*) (mc->r[15] & ~3ul);
        char line[400];
        int n = 0;
        line[0] = 0;
        for (int i = 0; i < 512 && n < 32 && (unsigned long) (sp + i) < 0x8d000000ul && (unsigned long) sp >= 0x8c000000ul;
             ++i) {
            const unsigned long a = sp[i];
            if (a >= 0x8c010000ul && a < (unsigned long) stall_etext && (a & 1) == 0) {
                snprintf(line + strlen(line), sizeof(line) - strlen(line), " %08lx", a);
                ++n;
            }
        }
        re4dc_log("stall: main stack:%s\n", line);
    }
    re4dc_threads_dump();
}
#endif

static void vblankHandler(uint32_t code, void* data)
{
    watchPoll();
    re4dc_threads_freshen();
    (void) code;
    (void) data;
    unsigned long prev = re4dc_stage;
    re4dc_stage = 0x1000;
    g_retraceCount++;
#if defined(RE4DC_STALL_DIAG) && RE4DC_STALL_DIAG
    if ((g_retraceCount % 60) == 0)
        re4dc_log("vblank %lu loop=%d\n", (unsigned long) g_retraceCount, (int) vsync_cnt);
    stallReport(prev);
#else
    if ((g_retraceCount % 600) == 0) re4dc_log("vblank %lu\n", (unsigned long) g_retraceCount);
#endif
    if (re4dc_diag && (g_retraceCount % 600) == 0) re4dc_threads_dump();
    (void) re4dc_audio_frame;  // the audio frame runs from the frame loop (pad.cpp), not the ISR
    if (g_postRetrace) {
        re4dc_stage = 0x1001;
        g_postRetrace();
    }
    re4dc_stage = prev;
}

extern "C" {

void VIInit(void)
{
    static int done;
    if (done) {
        return;
    }
    done = 1;
#if defined(RE4DC_SCREEN_W) && RE4DC_SCREEN_W == 320
    vid_set_mode(DM_320x240, PM_RGB565);  // SCREEN_320 (game30.mk, test builds)
#else
    vid_set_mode(DM_640x480, PM_RGB565);
#endif
#if defined(RE4DC_PVR_DITHER) && RE4DC_PVR_DITHER
    // PVR_DITHER (post30.mk): the RGB565 write-out dither is FB_W_CTRL bit 3. KOS's vid_set_mode sets it for
    // PM_RGB565 (vid_bpp_to_pvr_cfg2), so =1 only asserts it; =2 (diagnostic) clears it.
    vid_set_dithering(RE4DC_PVR_DITHER == 1);
    re4dc_log("pvr dither: FB_W_CTRL=%08lx (bit 3 dither=%lu) PVR_DITHER=%d\n", (u32) PVR_GET(PVR_FB_CFG_2),
              (u32) (PVR_GET(PVR_FB_CFG_2) >> 3) & 1, RE4DC_PVR_DITHER);
#endif
#if defined(RE4DC_STALL_DIAG) && RE4DC_STALL_DIAG
    g_stallMain = thd_current;
#endif
    g_vblankHandle = vblank_handler_add(vblankHandler, NULL);
    re4dc_log("VIInit: 640x480, vblank handler %d\n", g_vblankHandle);
}

void VIConfigure(const void* rm)
{
    (void) rm;  // the Dreamcast renderer owns the display mode
}

void VISetBlack(BOOL black)
{
    g_black = black;
    vid_border_color(0, 0, 0);
}

void VIFlush(void) {}

void VIWaitForRetrace(void)
{
    u32 start = g_retraceCount;
    while (g_retraceCount == start) {
        // the vblank interrupt advances the count; nothing else to do
    }
}

VIRetraceCallback VISetPostRetraceCallback(VIRetraceCallback cb)
{
    VIRetraceCallback old = g_postRetrace;
    g_postRetrace = cb;
    return old;
}

void VISetNextFrameBuffer(void* fb)
{
    (void) fb;  // presentation belongs to the renderer
}

u32 VIGetTvFormat(void) { return 0; }  // VI_NTSC
u32 VIGetNextField(void) { return g_retraceCount & 1; }
u32 VIGetDTVStatus(void) { return 0; }

int re4dc_vi_black(void) { return g_black; }

u32 re4dc_vi_retrace_count(void) { return g_retraceCount; }

}  // extern "C"
