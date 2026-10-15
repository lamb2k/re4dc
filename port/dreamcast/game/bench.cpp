// D367 public benchmark disc (BENCHMARK=1 in bench.mk; benchmark disc only, never a play image).
//
// User 2026-10-15: "Can we make the benchmark disk public for testers to help out with? With a clear indicator that it
// isn't the game?" The disc boots into a start screen that says it is not the game, runs scripted scenes through the
// warp rig (dbgwarp_bridge.cpp) and ends on a results screen with a code testers can type. Built on the 10-04 hwcal r21v
// console disc (start screen in the KOS framebuffer before pvr_init, own 5x7 font, results drawn into the displayed
// framebuffer while the frame loop stops, re4dc_ui_frame kept moving for CRASH_SCREEN's watchdog) and on the T12 Phases
// disc meters (one-second pace windows, tick log CPU, disc read meter). hwcal traps kept out: no VMU file (its write
// failed with -7 on the console: results are on screen only), no PMC rotation per vblank tick.
//
// v2 (2026-10-15, after the first console run: console / Flycast CPU 1.39 with Ganados, 1.23 without): results page 2
// (B or Y) splits the CPU frame into parts and shows per drawn frame the time and the SH-4 counters of each part, so one
// photo tells whether actor work is memory-bound. Counter 1 (PRFC0) stays KOS's cycle timer (perf_cntr_timer_ns) and
// gives the time; counter 2 (PRFC1) counts one event per drawn-frame period (a drawn iteration and the skipped ones after
// it, up to the next drawn iteration), in turn: D-cache miss pipeline freeze cycles (0x25), operand-cache read misses
// (0x04), operand-cache write misses (0x05), I-cache miss freeze cycles (0x24). Each event's value is taken against the
// cycles of the same periods and parts (ratio), so a draw / skip pattern that lines up with the rotation cannot bias it.
// Parts are marked by re4dc_bench_phase() in src/game/main.cpp (logic = TaskScheduler, wait = after DRAW REMAIN: vblank
// and pace wait, swap), src/game/trans.cpp (actor prep = the objTrans / emTrans / source actor prepare and plan stage of
// Trans; actor draw = ModelRender of an EmMgr model (Leon, partner, enemies) wherever its OT runs, nested; Render's
// SCROLL OT = world draw) and coarse.cpp (the coarse image: PS2 world + coarse world = world draw, draw_actors = actor
// draw). Everything else is "other" (effects, HUD, ids, messages, watchers, iTask, render begin / done). Interrupts and other KOS
// threads count in the part they interrupt. Where the counters do not count (an emulator), page 2 says so and shows
// times only (from the TMU).
//
// Flow:
//   OSInit wrap   start screen: what the disc is, that it is not the game, START or 20 s; memory cards are hidden from
//                 the game from here on (maple_enum_dev wrap: the no-card boot path, nothing is saved) and after START
//                 every controller reads idle (maple_dev_status wrap: only the scripted warp input reaches the game).
//   scene k       /cd/dc/warp.txt (scene 1) or /cd/dc/bench2.txt (scene 2): a warp fixture with a line
//                 `bench <no> <begin> <end> <name>`; room frames [begin, end) are measured. At `end` the warp rig logs
//                 the scene state, asks for the next scene and requests the source's soft reset (systemSoftReset); the
//                 next fixture is armed from the reset (WARP_AFTER_RESET hook), so each scene starts from the same
//                 state as a boot into it.
//   results       after the last scene: the frame loop stops in the warp rig's poll and this file draws the table and
//                 the code into the displayed framebuffer, redrawn when the display flips. A (pressed and released) runs
//                 both scenes again.
// Measurement (whole one-second pace windows inside [begin, end); pace.cpp vmu_window / dvd_read_safe.cpp):
//   FPS    drawn frames / wall time;   MIN1S  the lowest one-second window;   SPD  game ticks / (30 per second)
//   CPU    ms per tick to the source's "CPU" ProcessTickGet mark (tick log windows of GAME_TICK_LOG ticks)
//   GPU    ms per PVR render (render-done interrupts in the window, PACE_VMU_GPU)
//   RD/S   GD-ROM reads per second (game + loaders, not the music stream);  WAIT  ms the game thread spent in them
//   KOS    lowest KOS malloc headroom (free chunks + sbrk room) from the scene's first room frame to its end
#include <kos.h>
#include <dc/maple.h>
#include <dc/maple/controller.h>
#include <dc/video.h>
#include <dc/perfctr.h>
#include <arch/timer.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>

extern "C" {
void re4dc_log(const char* fmt, ...);
void re4dc_kos_heap_state(unsigned* free_chunks, unsigned* used, unsigned* break_room);  // platform/os.cpp
int re4dc_tick_log_snapshot(const char** name, unsigned* avg_us, unsigned* max_us, int max, unsigned* seq);  // tick_log.cpp
void __real_OSInit(void);
void* __real_maple_dev_status(maple_device_t* dev);
maple_device_t* __real_maple_enum_dev(int p, int u);
unsigned __real_re4dc_ui_frame(void);
int re4dc_bench_frozen;   // geometry sweep: main.cpp does not run TaskScheduler (the game logic holds still)
void re4dc_bench_state_now(const char* why);   // dbgwarp_bridge.cpp: the scene state line (hash) now
void re4dc_bench_ta(unsigned* calls, unsigned* bytes);   // platform/native_ui.cpp: the last completed frame's TA input
int re4dc_pace_get_mode(void);   // pace.cpp
void re4dc_pace_set_mode(int mode, const char* why);
}

namespace {
// ---------------------------------------------------------------- scenes
constexpr int kScenes = 2;       // the measured scenes (results pages 1 and 2)
constexpr int kAllScenes = 3;    // and scene 3, the geometry sweep (results page 3)
constexpr int kSweepScene = 2;
const char* const kScenePath[kAllScenes] = {"/cd/dc/warp.txt", "/cd/dc/bench2.txt", "/cd/dc/bench3.txt"};
struct Scene {
    char name[24];
    unsigned begin, end;          // measured room frames [begin, end)
    bool defined, measuring, done;
    // one-second pace windows wholly inside the measured range
    unsigned windows, drawn, ticks, vblanks, min_fps10;
    unsigned long long rnd_sum_ns;
    unsigned rnd_n;
    unsigned long long cpu_us_sum;
    unsigned cpu_n;
    unsigned reads;
    unsigned long long block_us, disc_us;
    unsigned kos_min;
    unsigned end_frame;
};
Scene g_scene[kAllScenes];
int g_cur;                        // scene being run
unsigned g_run = 1;               // run number (A on the results screen starts the next)
unsigned g_room_frame;
bool g_prev_include, g_last_include;
unsigned g_tick_seq;

// ---------------------------------------------------------------- counters (results page 2)
constexpr int kPh = 6;   // parts of the frame (re4dc_bench_phase numbers)
constexpr int kWork = 5; // parts that are CPU work (not the wait)
const char* const kPhName[kPh] = {"LOGIC", "ACTOR PREP", "ACTOR DRAW", "WORLD DRAW", "OTHER", "WAIT"};
constexpr int kEv = 4;
const unsigned kEvCode[kEv] = {0x25, 0x04, 0x05, 0x24};   // D-miss freeze cyc, OC read miss, OC write miss, I-miss freeze
enum { EV_DSTALL, EV_RDMISS, EV_WRMISS, EV_ISTALL };
struct Pmc {
    unsigned periods;                     // drawn-frame periods measured
    unsigned long long cyc[kPh];          // cycles of every period, by part
    unsigned ev_periods[kEv];             // periods that counted event e
    unsigned long long ev[kEv][kPh];      // event e's count, by part
    unsigned long long ev_cyc[kEv][kPh];  // cycles of the periods that counted event e, by part
};
Pmc g_pmc[kScenes];
bool g_pmc_hw;          // counter 2 counts here (the console; not Flycast)
bool g_cyc_pmc;         // counter 1 is KOS's cycle timer here; else cycles = TMU microseconds x 200
int g_ph = 4, g_ev_i;
struct Pmc* g_period_dst;   // where the running drawn-frame period is counted (nullptr: nowhere)
bool g_period_live;
unsigned long long g_c0, g_e0, g_pc[kPh], g_pe[kPh];
inline unsigned long long cyc_now() { return g_cyc_pmc ? perf_cntr_count(PRFC0) : timer_us_gettime64() * 200ULL; }
void pmc_event(unsigned ev)
{
    perf_cntr_stop(PRFC1);
    perf_cntr_clear(PRFC1);
    perf_cntr_start(PRFC1, (perf_cntr_event_t) ev, PMCR_COUNT_CPU_CYCLES);
}
// Whether the counters count: 2 ms of busy wait must give ~400,000 cycles on each.
void pmc_detect()
{
    pmc_event(PMCR_ELAPSED_TIME_MODE);
    const unsigned long long a0 = perf_cntr_count(PRFC1), c0 = perf_cntr_count(PRFC0);
    const uint64_t t0 = timer_us_gettime64();
    while (timer_us_gettime64() - t0 < 2000) {}
    const unsigned long long a = perf_cntr_count(PRFC1) - a0, c = perf_cntr_count(PRFC0) - c0;
    perf_cntr_stop(PRFC1);
    g_pmc_hw = a > 300000 && a < 500000;
    g_cyc_pmc = perf_cntr_timer_enabled() && c > 300000 && c < 500000;
    re4dc_log("bench: counters: counter 2 %llu cycles in 2 ms (%s), counter 1 %llu (%s)\n", a,
              g_pmc_hw ? "counts" : "does not count", c, g_cyc_pmc ? "cycle timer" : "TMU time");
}
// per drawn frame values of scene k, part p
unsigned pm_ms10(const Pmc& m, int p) { return m.periods ? (unsigned) ((m.cyc[p] / m.periods + 10000) / 20000) : 0; }
bool pm_has(const Pmc& m, int e, int p) { return g_pmc_hw && m.ev_periods[e] && m.ev_cyc[e][p]; }
unsigned pm_pct(const Pmc& m, int e, int p)   // a cycle event as % of the part's cycles
{
    return pm_has(m, e, p) ? (unsigned) ((m.ev[e][p] * 100ULL + m.ev_cyc[e][p] / 2) / m.ev_cyc[e][p]) : 0;
}
unsigned pm_k10(const Pmc& m, int e, int p)   // a count event per drawn frame, 0.1 k (density x the part's cycles)
{
    if (!pm_has(m, e, p) || !m.periods) return 0;
    const unsigned long long per_frame = m.ev[e][p] * (m.cyc[p] / m.periods) / m.ev_cyc[e][p];
    return (unsigned) ((per_frame + 50) / 100);
}
// several parts together (actors = prep + draw; all work = parts 0..4)
unsigned pm_ms10_sum(const Pmc& m, int p0, int p1)
{
    unsigned long long c = 0;
    for (int p = p0; p <= p1; ++p) c += m.cyc[p];
    return m.periods ? (unsigned) ((c / m.periods + 10000) / 20000) : 0;
}
unsigned pm_pct_sum(const Pmc& m, int e, int p0, int p1)
{
    unsigned long long n = 0, c = 0;
    for (int p = p0; p <= p1; ++p) { n += m.ev[e][p]; c += m.ev_cyc[e][p]; }
    return g_pmc_hw && c ? (unsigned) ((n * 100ULL + c / 2) / c) : 0;
}
unsigned pm_miss_k10_sum(const Pmc& m, int p0, int p1)   // read + write misses of several parts, 0.1 k per drawn frame
{
    unsigned v = 0;
    for (int p = p0; p <= p1; ++p) v += pm_k10(m, EV_RDMISS, p) + pm_k10(m, EV_WRMISS, p);
    return v;
}

// ---------------------------------------------------------------- geometry sweep (scene 3, results page 3)
// Coordinator 2026-10-15: what cutting triangles buys on the console. Scene 3 holds the r101 cross view (scene 1's
// fixture) and from its `bench 3 <room frame>` line on the game logic stands still (main.cpp skips TaskScheduler:
// AI, motion, camera, effects move, scenario and the warp rig; the state hash is logged at the freeze, at the end of
// the sweep and at the scene end, and must not change) while pacing is off (every iteration draws). Six render-only
// settings, each kSettleUs then kMeasureUs: as shipped; every other Ganado not drawn (odd places in EmMgr's alive list); no Ganado
// drawn; the PS2 world's far plane at 18.75 m (shipped 25 m); Leon not drawn; the far plane at 12.5 m. A Ganado or Leon "not drawn" returns before its draw (coarse.cpp draw_model, trans.cpp
// ModelRender), as on a skipped iteration. The shipped Ganados are the PS2 cast (coarse_ganado_cast.cpp): no LOD
// levels (its far bundle, CROWD_FAR, is not in this build), so a forced crowd tier changes nothing there (Flycast
// check: identical TA counts) and the Ganado rows remove whole Ganados instead; Leon (coarse_leon) has no LOD
// levels either (a 16 px LOD threshold changed nothing). Removing a model also removes its per-model work (bones,
// set-up), which an LOD would keep: the "ms per 1k vertices" of a removal is an upper bound for an LOD's saving. Per setting and drawn frame: TA vertices (the frame's 32-byte TA commands less its headers,
// native_ui's frame counters) and headers, CPU ms by part, GPU ms, D-stall %, data cache misses. Page 3 derives ms per
// 1k vertices from the differences against "as shipped".
constexpr int kSet = 6;
const char* const kSetName[kSet] = {"AS SHIPPED", "HALF GANADO", "NO GANADOS", "WORLD 18.8M", "NO LEON", "WORLD 12.5M"};
constexpr unsigned long long kSettleUs = 1500000, kMeasureUs = 5000000, kSlotUs = kSettleUs + kMeasureUs;
constexpr float kNearFar = 12500.0f, kMidFar = 18750.0f;   // the PS2 world's far plane (shipped 25000)
struct Sweep {
    Pmc pmc;
    unsigned long long ta_calls, ta_bytes;
    unsigned ta_n;
    unsigned long long rnd_sum_ns;
    unsigned rnd_n, windows;
};
Sweep g_sw[kSet];
enum { SW_IDLE, SW_RUN, SW_DONE };
int g_sw_state, g_sw_k = -1, g_sw_saved_pace, g_sw_prev_win = -1;
bool g_sw_measuring, g_sw_logged;
unsigned long long g_sw_t0;
unsigned g_hide;
float g_world_far;
void sweep_apply(int k)
{
    g_hide = k == 1 ? 4u : k == 2 ? 1u : k == 4 ? 2u : 0u;
    g_world_far = k == 5 ? kNearFar : k == 3 ? kMidFar : 0.0f;
}
unsigned sw_verts10(const Sweep& w)   // TA vertices per frame, 0.1 k
{
    if (!w.ta_n || w.ta_bytes / 32 < w.ta_calls) return 0;
    return (unsigned) (((w.ta_bytes / 32 - w.ta_calls) / w.ta_n + 50) / 100);
}
unsigned sw_hdrs(const Sweep& w) { return w.ta_n ? (unsigned) ((w.ta_calls + w.ta_n / 2) / w.ta_n) : 0; }
unsigned sw_cpu10(const Sweep& w) { return pm_ms10_sum(w.pmc, 0, kWork - 1); }
unsigned sw_act10(const Sweep& w) { return pm_ms10_sum(w.pmc, 1, 2); }
unsigned sw_wld10(const Sweep& w) { return pm_ms10(w.pmc, 3); }
unsigned sw_gpu10(const Sweep& w) { return w.rnd_n ? (unsigned) ((w.rnd_sum_ns / w.rnd_n + 50000) / 100000) : 0; }
// ms per 1k vertices x100 from setting 0 against setting b (0.1 ms and 0.1 k units); -1 when the vertices did not drop
int sw_slope100(unsigned (*f)(const Sweep&), int b)
{
    const int dv = (int) sw_verts10(g_sw[0]) - (int) sw_verts10(g_sw[b]);
    if (dv <= 0 || !g_sw[0].pmc.periods || !g_sw[b].pmc.periods) return -1;
    return ((int) f(g_sw[0]) - (int) f(g_sw[b])) * 100 / dv;
}
const char* d2s(int v100, char* buf)
{
    if (v100 < 0 && v100 != -1) { snprintf(buf, 12, "-%d.%02d", -v100 / 100, -v100 % 100); return buf; }
    if (v100 == -1) { snprintf(buf, 12, "-"); return buf; }
    snprintf(buf, 12, "%d.%02d", v100 / 100, v100 % 100);
    return buf;
}

// ---------------------------------------------------------------- framebuffer text (hwcal r21v)
const uint8_t* glyph(char c) {
    static const uint8_t kFont[][8] = {
        {' ', 0, 0, 0, 0, 0, 0, 0},
        {'0', 0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E}, {'1', 0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E},
        {'2', 0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F}, {'3', 0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E},
        {'4', 0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02}, {'5', 0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E},
        {'6', 0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E}, {'7', 0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08},
        {'8', 0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E}, {'9', 0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C},
        {'A', 0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11}, {'B', 0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E},
        {'C', 0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E}, {'D', 0x1C, 0x12, 0x11, 0x11, 0x11, 0x12, 0x1C},
        {'E', 0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F}, {'F', 0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10},
        {'G', 0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F}, {'H', 0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11},
        {'I', 0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E}, {'J', 0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C},
        {'K', 0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11}, {'L', 0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F},
        {'M', 0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11}, {'N', 0x11, 0x11, 0x19, 0x15, 0x13, 0x11, 0x11},
        {'O', 0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E}, {'P', 0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10},
        {'Q', 0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D}, {'R', 0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11},
        {'S', 0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E}, {'T', 0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04},
        {'U', 0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E}, {'V', 0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04},
        {'W', 0x11, 0x11, 0x11, 0x15, 0x15, 0x15, 0x0A}, {'X', 0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11},
        {'Y', 0x11, 0x11, 0x11, 0x0A, 0x04, 0x04, 0x04}, {'Z', 0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F},
        {'.', 0, 0, 0, 0, 0, 0x0C, 0x0C}, {'-', 0, 0, 0, 0x1F, 0, 0, 0}, {':', 0, 0x0C, 0x0C, 0, 0x0C, 0x0C, 0},
        {'/', 0, 0x01, 0x02, 0x04, 0x08, 0x10, 0}, {'%', 0x18, 0x19, 0x02, 0x04, 0x08, 0x13, 0x03},
        {'(', 0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02}, {')', 0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08},
        {'=', 0, 0, 0x1F, 0, 0x1F, 0, 0}, {'+', 0, 0x04, 0x04, 0x1F, 0x04, 0x04, 0},
        {'>', 0x08, 0x04, 0x02, 0x01, 0x02, 0x04, 0x08}, {',', 0, 0, 0, 0, 0x0C, 0x04, 0x08},
        {'#', 0x0A, 0x0A, 0x1F, 0x0A, 0x1F, 0x0A, 0x0A}, {'!', 0x04, 0x04, 0x04, 0x04, 0x04, 0, 0x04},
        {'?', 0x0E, 0x11, 0x01, 0x02, 0x04, 0, 0x04}, {'*', 0, 0x15, 0x0E, 0x1F, 0x0E, 0x15, 0},
    };
    if (c >= 'a' && c <= 'z') c = (char) (c - 32);
    for (const auto& g : kFont)
        if (g[0] == (uint8_t) c) return g + 1;
    return kFont[0] + 1;
}
struct Fb { uint8_t* base; int w, h, bpp, stride; bool rgb565; };
void fb_fill(const Fb& fb, int x, int y, int w, int h, uint32_t rgb) {
    if (x < 0) { w += x; x = 0; }
    if (y < 0) { h += y; y = 0; }
    if (x + w > fb.w) w = fb.w - x;
    if (y + h > fb.h) h = fb.h - y;
    if (w <= 0 || h <= 0) return;
    const uint16_t c565 = (uint16_t) (((rgb >> 8) & 0xF800) | ((rgb >> 5) & 0x07E0) | ((rgb >> 3) & 0x1F));
    const uint16_t c555 = (uint16_t) (((rgb >> 9) & 0x7C00) | ((rgb >> 6) & 0x03E0) | ((rgb >> 3) & 0x1F));
    for (int j = 0; j < h; ++j) {
        uint8_t* row = fb.base + (y + j) * fb.stride + x * fb.bpp;
        for (int i = 0; i < w; ++i) {
            if (fb.bpp == 2) ((uint16_t*) row)[i] = fb.rgb565 ? c565 : c555;
            else if (fb.bpp == 4) ((uint32_t*) row)[i] = rgb;
            else { row[i * 3] = (uint8_t) rgb; row[i * 3 + 1] = (uint8_t) (rgb >> 8); row[i * 3 + 2] = (uint8_t) (rgb >> 16); }
        }
    }
}
// 5x7 glyphs, each font pixel sx by sy screen pixels, 1 pixel between characters
void fb_text(const Fb& fb, int x, int y, int sx, int sy, uint32_t rgb, const char* s) {
    for (; *s; ++s, x += 5 * sx + 1) {
        const uint8_t* g = glyph(*s);
        for (int r = 0; r < 7; ++r)
            for (int c = 0; c < 5; ++c)
                if (g[r] & (0x10 >> c)) fb_fill(fb, x + c * sx, y + r * sy, sx, sy, rgb);
    }
}
int text_w(const char* s, int sx) { return (int) strlen(s) * (5 * sx + 1); }
void fb_center(const Fb& fb, int y, int sx, int sy, uint32_t rgb, const char* s) {
    fb_text(fb, (fb.w - text_w(s, sx)) / 2, y, sx, sy, rgb, s);
}
Fb fb_boot() {   // KOS framebuffer before pvr_init (vid_set_mode 640x480 RGB565, as VIInit)
    Fb fb{};
    fb.base = (uint8_t*) vram_s; fb.w = 640; fb.h = 480; fb.bpp = 2; fb.stride = 1280; fb.rgb565 = true;
    return fb;
}
Fb fb_displayed() {  // the framebuffer the display reads now (FB_R_SOF1 / FB_R_CTRL), linear 640 wide
    Fb fb{};
    const uint32_t sof1 = *(volatile uint32_t*) 0xA05F8050, ctrl = *(volatile uint32_t*) 0xA05F8044;
    const int depth = (ctrl >> 2) & 3;
    fb.bpp = depth == 0 || depth == 1 ? 2 : depth == 2 ? 3 : 4;
    fb.rgb565 = depth == 1;
    fb.w = vid_mode ? vid_mode->width : 640;
    fb.h = vid_mode ? vid_mode->height : 480;
    fb.stride = fb.w * fb.bpp;
    fb.base = (uint8_t*) (0xA5000000u | (sof1 & 0x007FFFFFu));
    return fb;
}

// ---------------------------------------------------------------- input
bool g_masked, g_hide_vmu;
volatile unsigned g_results_ticks;   // moves CRASH_SCREEN's hang watchdog while a screen of this file waits
unsigned pad_buttons() {
    maple_device_t* c = maple_enum_type(0, MAPLE_FUNC_CONTROLLER);
    cont_state_t* st = c ? (cont_state_t*) __real_maple_dev_status(c) : nullptr;
    return st ? st->buttons : 0;
}
void spin_us(uint32_t us) {   // busy wait on the TMU: no scheduler dependence once the frame loop stops
    const uint64_t t0 = timer_us_gettime64();
    while (timer_us_gettime64() - t0 < us) {}
}

// ---------------------------------------------------------------- results
const uint32_t kWhite = 0xFFFFFF, kYellow = 0xFFFF40, kCyan = 0x40FFFF, kGrey = 0xA0A0A0, kGreen = 0x60FF60,
               kRed = 0xFF5050;
unsigned fps10(const Scene& s) { return s.vblanks ? (unsigned) ((unsigned long long) s.drawn * 59940ULL / 100 / s.vblanks) : 0; }
unsigned cpu10(const Scene& s) { return s.cpu_n ? (unsigned) ((s.cpu_us_sum / s.cpu_n + 50) / 100) : 0; }
unsigned gpu10(const Scene& s) { return s.rnd_n ? (unsigned) ((s.rnd_sum_ns / s.rnd_n + 50000) / 100000) : 0; }
unsigned speed_pct(const Scene& s) { return s.vblanks ? (unsigned) ((s.ticks * 2000ULL / s.vblanks + 5) / 10) : 0; }
unsigned reads_ps10(const Scene& s) { return s.disc_us ? (unsigned) ((unsigned long long) s.reads * 10000000ULL / s.disc_us) : 0; }
unsigned wait_ms(const Scene& s) { return s.disc_us ? (unsigned) ((s.block_us * 1000ULL + s.disc_us / 2) / s.disc_us) : 0; }  // ms per s
unsigned kos_kb(const Scene& s) { return s.kos_min == ~0u ? 0 : s.kos_min / 1024; }
const char* d1(unsigned v10, char* buf) { snprintf(buf, 12, "%u.%u", v10 / 10, v10 % 10); return buf; }

// The code testers type: per scene A/B fps*10.min1s*10.cpu*10.gpu*10.reads/s*10.wait ms/s.kos KB, then a check value over
// the build id and the numbers (two hex digits) so a mistyped code shows.
void make_code(char* out, unsigned size) {
    char part[kScenes][48];
    for (int k = 0; k < kScenes; ++k) {
        const Scene& s = g_scene[k];
        snprintf(part[k], sizeof(part[k]), "%c%u.%u.%u.%u.%u.%u.%u", 'A' + k, fps10(s), s.windows ? s.min_fps10 : 0,
                 cpu10(s), gpu10(s), reads_ps10(s), wait_ms(s), kos_kb(s));
    }
    char body[128];
    snprintf(body, sizeof(body), "%s %s %s", RE4DC_BENCH_ID, part[0], part[1]);
    unsigned ck = 0;
    for (const char* p = body; *p; ++p) ck = (ck * 31 + (unsigned char) *p) % 251;
    snprintf(out, size, "%s %s %02X", part[0], part[1], ck);
}

void draw_results(const Fb& fb) {
    char a[12], b[12], c[12], d[12], e[12], line[96], code[96];
    fb_fill(fb, 0, 0, fb.w, fb.h, 0x000000);
    int y = 30;
    fb_fill(fb, 30, y - 4, 580, 30, 0x900000);
    fb_center(fb, y, 2, 3, kWhite, "BENCHMARK DISC - NOT THE GAME"); y += 34;
    fb_center(fb, y, 2, 3, kYellow, "RE4 DREAMCAST BENCHMARK RESULTS"); y += 30;
    snprintf(line, sizeof(line), "BUILD %s   RUN %u", RE4DC_BENCH_ID, g_run);
    fb_center(fb, y, 2, 2, kGrey, line); y += 26;
    fb_text(fb, 36, y, 2, 2, kCyan, "SCENE         FPS MIN1S   CPU   GPU SPD%"); y += 22;
    for (int k = 0; k < kScenes; ++k) {
        const Scene& s = g_scene[k];
        if (!s.windows) { snprintf(line, sizeof(line), "%d %-10s  NOT MEASURED", k + 1, s.name); fb_text(fb, 36, y, 2, 3, kRed, line); y += 28; continue; }
        snprintf(line, sizeof(line), "%d %-10s%5s %5s %5s %5s %4u", k + 1, s.name, d1(fps10(s), a), d1(s.min_fps10, b),
                 d1(cpu10(s), c), d1(gpu10(s), d), speed_pct(s));
        fb_text(fb, 36, y, 2, 3, kWhite, line); y += 28;
    }
    y += 4;
    fb_text(fb, 36, y, 2, 2, kCyan, "SCENE        READS/S WAIT MS/S KOS MIN KB"); y += 22;
    for (int k = 0; k < kScenes; ++k) {
        const Scene& s = g_scene[k];
        snprintf(line, sizeof(line), "%d %-10s %7s %9u %8u", k + 1, s.name, d1(reads_ps10(s), e), wait_ms(s), kos_kb(s));
        fb_text(fb, 36, y, 2, 3, kWhite, line); y += 28;
    }
    y += 2;
    fb_text(fb, 36, y, 1, 2, kGrey, "FPS: DRAWN FRAMES PER SECOND (AVERAGE)  MIN1S: LOWEST ONE-SECOND WINDOW"); y += 16;
    fb_text(fb, 36, y, 1, 2, kGrey, "CPU: MS OF GAME CPU WORK PER TICK  GPU: MS PER RENDER  SPD%: GAME SPEED (100 = REAL TIME)"); y += 16;
    fb_text(fb, 36, y, 1, 2, kGrey, "WAIT MS/S: TIME THE GAME WAITED ON THE DISC  KOS MIN: LOWEST FREE SYSTEM MEMORY"); y += 22;
    make_code(code, sizeof(code));
    fb_text(fb, 36, y, 2, 2, kGreen, "CODE:"); y += 20;
    if (text_w(code, 2) <= fb.w - 32) fb_text(fb, 16, y, 2, 3, kGreen, code);
    else fb_text(fb, 16, y, 1, 3, kGreen, code);   // a long code still fits on one line
    y += 32;
    fb_text(fb, 36, y, 2, 2, kWhite, "PHOTOGRAPH THIS SCREEN. POST IT WITH YOUR"); y += 20;
    fb_text(fb, 36, y, 2, 2, kWhite, "CONSOLE REGION AND GDEMU / ODE / BURNED DISC."); y += 26;
    fb_text(fb, 36, y, 2, 3, kCyan, "A: RUN AGAIN   B: PAGE 2 (COUNTERS)");
}

// The second code: per scene P/Q, ms x10 of the six parts . D-miss stall % of the five work parts . operand-cache
// misses (read + write) per drawn frame in whole k of the five work parts, then a check value as on page 1.
void make_code2(char* out, unsigned size)
{
    char part[kScenes][96];
    for (int k = 0; k < kScenes; ++k) {
        const Pmc& m = g_pmc[k];
        char* q = part[k];
        char* const end = part[k] + sizeof(part[k]);
        q += snprintf(q, end - q, "%c", 'P' + k);
        for (int p = 0; p < kPh; ++p) q += snprintf(q, end - q, p ? ".%u" : "%u", pm_ms10(m, p));
        for (int p = 0; p < kWork; ++p) q += snprintf(q, end - q, p ? ".%u" : "/%u", pm_pct(m, EV_DSTALL, p));
        for (int p = 0; p < kWork; ++p)
            q += snprintf(q, end - q, p ? ".%u" : "/%u", (pm_k10(m, EV_RDMISS, p) + pm_k10(m, EV_WRMISS, p) + 5) / 10);
    }
    char body[256];
    snprintf(body, sizeof(body), "%s %s %s", RE4DC_BENCH_ID, part[0], part[1]);
    unsigned ck = 0;
    for (const char* p = body; *p; ++p) ck = (ck * 31 + (unsigned char) *p) % 251;
    snprintf(out, size, "%s %s %02X", part[0], part[1], ck);
}

// Page 2: the CPU frame by part, per drawn frame, both scenes side by side.
void draw_counters(const Fb& fb)
{
    char line[128], code[224], a[12], b[12], c[12], d[12];
    fb_fill(fb, 0, 0, fb.w, fb.h, 0x000000);
    int y = 30;
    fb_fill(fb, 30, y - 4, 580, 30, 0x900000);
    fb_center(fb, y, 2, 3, kWhite, "BENCHMARK DISC - NOT THE GAME"); y += 34;
    fb_center(fb, y, 2, 3, kYellow, "PAGE 2: WHERE THE CPU TIME GOES"); y += 30;
    snprintf(line, sizeof(line), "BUILD %s   RUN %u", RE4DC_BENCH_ID, g_run);
    fb_center(fb, y, 2, 2, kGrey, line); y += 24;
    // columns: part (10) then per scene MS (5) STALL% (3) READ k (5) WRITE k (5)
    snprintf(line, sizeof(line), "%-10s %-21s %-21s", "", g_scene[0].name, g_scene[1].name);
    fb_text(fb, 14, y, 2, 2, kCyan, line); y += 18;
    snprintf(line, sizeof(line), "%-10s %5s %3s %5s %5s %5s %3s %5s %5s", "PART", "MS", "ST%", "RD K", "WR K", "MS", "ST%",
             "RD K", "WR K");
    fb_text(fb, 14, y, 2, 2, kCyan, line); y += 20;
    for (int p = 0; p <= kPh; ++p) {   // kPh = the total row
        char col[kScenes][32];
        for (int k = 0; k < kScenes; ++k) {
            const Pmc& m = g_pmc[k];
            if (!m.periods) { snprintf(col[k], sizeof(col[k]), "%5s %3s %5s %5s", "-", "-", "-", "-"); continue; }
            if (p == kPh) {   // total: all parts; stall % of the work parts
                snprintf(col[k], sizeof(col[k]), "%5s %3s %5s %5s", d1(pm_ms10_sum(m, 0, kPh - 1), a),
                         g_pmc_hw ? (snprintf(c, sizeof(c), "%u", pm_pct_sum(m, EV_DSTALL, 0, kWork - 1)), c) : "-", "", "");
            } else if (p == kPh - 1 || !g_pmc_hw) {
                snprintf(col[k], sizeof(col[k]), "%5s %3s %5s %5s", d1(pm_ms10(m, p), a), "-", "-", "-");
            } else {
                snprintf(c, sizeof(c), "%u", pm_pct(m, EV_DSTALL, p));
                snprintf(col[k], sizeof(col[k]), "%5s %3s %5s %5s", d1(pm_ms10(m, p), a), c, d1(pm_k10(m, EV_RDMISS, p), b),
                         d1(pm_k10(m, EV_WRMISS, p), d));
            }
        }
        char row[128];
        snprintf(row, sizeof(row), "%-10s %s %s", p == kPh ? "TOTAL" : kPhName[p], col[0], col[1]);
        fb_text(fb, 14, y, 2, 2, p == kPh ? kYellow : (p == 1 || p == 2) ? kGreen : kWhite, row); y += 18;
    }
    y += 4;
    if (g_pmc_hw) {
        for (int k = 0; k < kScenes; ++k) {
            const Pmc& m = g_pmc[k];
            if (!m.periods) continue;
            snprintf(line, sizeof(line), "%s: ACTORS %s MS, %u%% STALLED ON MEMORY", g_scene[k].name, d1(pm_ms10_sum(m, 1, 2), a),
                     pm_pct_sum(m, EV_DSTALL, 1, 2));
            fb_text(fb, 14, y, 2, 2, kGreen, line); y += 20;
        }
    } else {
        fb_text(fb, 14, y, 2, 2, kRed, "COUNTERS DO NOT COUNT HERE (EMULATOR?)"); y += 20;
        fb_text(fb, 14, y, 2, 2, kRed, "TIMES ONLY. RUN IT ON A DREAMCAST."); y += 20;
    }
    y += 2;
    fb_text(fb, 14, y, 1, 2, kGrey, "PER DRAWN FRAME. MS: CPU TIME. ST%: SHARE OF IT THE CPU STOOD WAITING FOR MEMORY (CACHE MISSES)"); y += 16;
    fb_text(fb, 14, y, 1, 2, kGrey, "RD K / WR K: THOUSANDS OF DATA CACHE MISSES ON READS / WRITES. WAIT: IDLE UNTIL THE NEXT FRAME"); y += 20;
    make_code2(code, sizeof(code));
    fb_text(fb, 14, y, 2, 2, kGreen, "CODE 2 (ONE LINE WHEN TYPED):"); y += 18;
    if (text_w(code, 1) <= fb.w - 16) { fb_text(fb, 8, y, 1, 3, kGreen, code); y += 26; }
    else {   // wraps after the first scene
        char* sp = strchr(code, ' ');
        if (sp) *sp = 0;
        fb_text(fb, 8, y, 1, 3, kGreen, code); y += 24;
        if (sp) { fb_text(fb, 8, y, 1, 3, kGreen, sp + 1); y += 26; }
    }
    fb_text(fb, 14, y, 2, 3, kCyan, "A: RUN AGAIN   B: PAGE 3 (GEOMETRY)");
}

void log_counters()
{
    char code[224];
    make_code2(code, sizeof(code));
    for (int k = 0; k < kScenes; ++k) {
        const Pmc& m = g_pmc[k];
        re4dc_log("bench: pmc run %u scene %d %s periods=%u hw=%d cyc=%s ev_periods=%u/%u/%u/%u\n", g_run, k + 1,
                  g_scene[k].name, m.periods, g_pmc_hw ? 1 : 0, g_cyc_pmc ? "pmc" : "tmu", m.ev_periods[0],
                  m.ev_periods[1], m.ev_periods[2], m.ev_periods[3]);
        for (int p = 0; p < kPh; ++p)
            re4dc_log("bench: pmc scene %d part %s ms10=%u dstall%%=%u istall%%=%u rd_k10=%u wr_k10=%u cyc=%llu "
                      "ev=%llu/%llu/%llu/%llu\n", k + 1, kPhName[p], pm_ms10(m, p), pm_pct(m, EV_DSTALL, p),
                      pm_pct(m, EV_ISTALL, p), pm_k10(m, EV_RDMISS, p), pm_k10(m, EV_WRMISS, p), m.cyc[p],
                      m.ev[0][p], m.ev[1][p], m.ev[2][p], m.ev[3][p]);
    }
    re4dc_log("bench: code2 %s build %s\n", code, RE4DC_BENCH_ID);
}

// The third code: S, then per setting TA vertices per frame (0.1 k) . CPU ms x10 . GPU ms x10, settings joined by /,
// then a check value as on page 1.
void make_code3(char* out, unsigned size)
{
    char body[160], part[160];
    char* q = part;
    char* const end = part + sizeof(part);
    q += snprintf(q, end - q, "S");
    for (int k = 0; k < kSet; ++k)
        q += snprintf(q, end - q, "%s%u.%u.%u", k ? "/" : "", sw_verts10(g_sw[k]), sw_cpu10(g_sw[k]), sw_gpu10(g_sw[k]));
    snprintf(body, sizeof(body), "%s %s", RE4DC_BENCH_ID, part);
    unsigned ck = 0;
    for (const char* p = body; *p; ++p) ck = (ck * 31 + (unsigned char) *p) % 251;
    snprintf(out, size, "%s %02X", part, ck);
}

// Page 3: the geometry sweep, one row per setting, and the cost per 1k vertices derived from the rows.
void draw_sweep(const Fb& fb)
{
    char line[128], code[192], a[12], b[12], c[12], d[12], e[12], f[12], g[12];
    fb_fill(fb, 0, 0, fb.w, fb.h, 0x000000);
    int y = 30;
    fb_fill(fb, 30, y - 4, 580, 30, 0x900000);
    fb_center(fb, y, 2, 3, kWhite, "BENCHMARK DISC - NOT THE GAME"); y += 34;
    fb_center(fb, y, 2, 3, kYellow, "PAGE 3: WHAT GEOMETRY COSTS"); y += 30;
    snprintf(line, sizeof(line), "BUILD %s   RUN %u   R101 CROSS, GAME FROZEN", RE4DC_BENCH_ID, g_run);
    fb_center(fb, y, 2, 2, kGrey, line); y += 24;
    snprintf(line, sizeof(line), "%-11s %5s %5s %5s %5s %5s %3s %5s", "SETTING", "VERTK", "CPU", "ACTOR", "WORLD", "GPU",
             "ST%", "MISSK");
    fb_text(fb, 14, y, 2, 2, kCyan, line); y += 20;
    for (int k = 0; k < kSet; ++k) {
        const Sweep& w = g_sw[k];
        if (!w.pmc.periods) {
            snprintf(line, sizeof(line), "%-11s  NOT MEASURED", kSetName[k]);
            fb_text(fb, 14, y, 2, 2, kRed, line); y += 18;
            continue;
        }
        snprintf(e, sizeof(e), "%u", pm_pct_sum(w.pmc, EV_DSTALL, 0, kWork - 1));
        snprintf(line, sizeof(line), "%-11s %5s %5s %5s %5s %5s %3s %5s", kSetName[k], d1(sw_verts10(w), a),
                 d1(sw_cpu10(w), b), d1(sw_act10(w), c), d1(sw_wld10(w), d), d1(sw_gpu10(w), f), g_pmc_hw ? e : "-",
                 g_pmc_hw ? d1(pm_miss_k10_sum(w.pmc, 0, kWork - 1), g) : "-");
        fb_text(fb, 14, y, 2, 2, k ? kWhite : kYellow, line); y += 18;
    }
    y += 6;
    fb_text(fb, 14, y, 2, 2, kCyan, "MS PER 1000 VERTICES     CPU    GPU  VERTK"); y += 20;
    struct Row { const char* name; int b; };
    const Row rows[] = {{"GANADOS (NONE)", 2}, {"GANADOS (HALF)", 1}, {"LEON (NONE)", 4}, {"WORLD (18.8 M FAR)", 3},
                        {"WORLD (12.5 M FAR)", 5}};
    for (const Row& r : rows) {
        const int dv = (int) sw_verts10(g_sw[0]) - (int) sw_verts10(g_sw[r.b]);
        snprintf(line, sizeof(line), "%-22s %6s %6s %6s", r.name, d2s(sw_slope100(sw_cpu10, r.b), a),
                 d2s(sw_slope100(sw_gpu10, r.b), b), dv > 0 ? d1((unsigned) dv, c) : "-");
        fb_text(fb, 14, y, 2, 2, kGreen, line); y += 18;
    }
    y += 4;
    fb_text(fb, 14, y, 1, 2, kGrey, "VERTK: THOUSANDS OF VERTICES SENT TO THE GRAPHICS CHIP PER FRAME. CPU / ACTOR / WORLD / GPU: MS"); y += 16;
    fb_text(fb, 14, y, 1, 2, kGrey, "PER FRAME. LOWER ROWS: WHAT 1000 FEWER VERTICES SAVE, FROM THE DIFFERENCE TO AS SHIPPED"); y += 20;
    make_code3(code, sizeof(code));
    fb_text(fb, 14, y, 2, 2, kGreen, "CODE 3:"); y += 18;
    fb_text(fb, 8, y, 1, 3, kGreen, code); y += 28;
    fb_text(fb, 14, y, 2, 3, kCyan, "A: RUN AGAIN   B: PAGE 1 (RESULTS)");
}

void log_sweep()
{
    char code[192];
    for (int k = 0; k < kSet; ++k) {
        const Sweep& w = g_sw[k];
        re4dc_log("bench: sweep run %u setting %d %s frames=%u verts10=%u hdrs=%u cpu10=%u act10=%u wld10=%u logic10=%u "
                  "other10=%u gpu10=%u gpu_windows=%u dstall%%=%u miss_k10=%u ta_calls=%llu ta_bytes=%llu ta_n=%u\n",
                  g_run, k + 1, kSetName[k], w.pmc.periods, sw_verts10(w), sw_hdrs(w), sw_cpu10(w), sw_act10(w),
                  sw_wld10(w), pm_ms10(w.pmc, 0), pm_ms10(w.pmc, 4), sw_gpu10(w), w.windows,
                  pm_pct_sum(w.pmc, EV_DSTALL, 0, kWork - 1), pm_miss_k10_sum(w.pmc, 0, kWork - 1), w.ta_calls,
                  w.ta_bytes, w.ta_n);
    }
    char a[12], b[12];
    const int bs[5] = {2, 1, 3, 4, 5};
    for (int b_ : bs)
        re4dc_log("bench: sweep slope vs setting %d %s: cpu %s gpu %s ms per 1k vertices\n", b_ + 1, kSetName[b_],
                  d2s(sw_slope100(sw_cpu10, b_), a), d2s(sw_slope100(sw_gpu10, b_), b));
    make_code3(code, sizeof(code));
    re4dc_log("bench: code3 %s build %s\n", code, RE4DC_BENCH_ID);
}

void sweep_start()
{
    memset(g_sw, 0, sizeof(g_sw));
    g_sw_state = SW_RUN; g_sw_k = -1; g_sw_prev_win = -1;
    g_sw_logged = false; g_sw_measuring = false;
    g_sw_saved_pace = re4dc_pace_get_mode();
    re4dc_pace_set_mode(2, "bench sweep");   // PACE_OFF: every iteration draws
    re4dc_bench_frozen = 1;
    re4dc_log("bench: sweep: game logic frozen after room frame %u (pace mode %d -> off)\n", g_room_frame, g_sw_saved_pace);
}
// Top of a main loop iteration while the sweep runs: the setting by elapsed time; after the last one the logic resumes.
void sweep_step()
{
    if (g_sw_state != SW_RUN) return;
    const unsigned long long now = timer_us_gettime64();
    if (!g_sw_logged) {
        g_sw_logged = true;
        g_sw_t0 = now;
        re4dc_bench_state_now("sweep start (logic frozen)");
    }
    const unsigned long long t = now - g_sw_t0;
    const int k = (int) (t / kSlotUs);
    if (k >= kSet) {
        g_sw_measuring = false;
        sweep_apply(-1);
        re4dc_bench_state_now("sweep end (logic still frozen)");
        re4dc_bench_frozen = 0;
        re4dc_pace_set_mode(g_sw_saved_pace, "bench sweep end");
        g_sw_state = SW_DONE;
        re4dc_log("bench: sweep done\n");
        return;
    }
    if (k != g_sw_k) {
        g_sw_k = k;
        sweep_apply(k);
        re4dc_log("bench: sweep setting %d %s\n", k + 1, kSetName[k]);
    }
    g_sw_measuring = t - (unsigned long long) k * kSlotUs >= kSettleUs;
}
Pmc* period_target()
{
    if (g_cur == kSweepScene) return g_sw_measuring && g_sw_k >= 0 ? &g_sw[g_sw_k].pmc : nullptr;
    const Scene& s = g_scene[g_cur];
    return g_cur < kScenes && s.defined && s.measuring ? &g_pmc[g_cur] : nullptr;
}

void log_results() {
    char code[96];
    make_code(code, sizeof(code));
    for (int k = 0; k < kScenes; ++k) {
        const Scene& s = g_scene[k];
        re4dc_log("bench: result run %u scene %d %s windows=%u drawn=%u ticks=%u vblanks=%u fps10=%u min1s10=%u cpu10=%u "
                  "gpu10=%u speed=%u reads=%u reads_ps10=%u wait_ms=%u kos_min=%u end_frame=%u\n",
                  g_run, k + 1, s.name, s.windows, s.drawn, s.ticks, s.vblanks, fps10(s), s.min_fps10, cpu10(s), gpu10(s),
                  speed_pct(s), s.reads, reads_ps10(s), wait_ms(s), s.kos_min, s.end_frame);
    }
    re4dc_log("bench: code %s build %s\n", code, RE4DC_BENCH_ID);
}
}  // namespace

extern "C" {

// ---------------------------------------------------------------- warp rig (dbgwarp_bridge.cpp)
// A `bench <no> <begin> <end> <name>` line of the current fixture: the measured room frames of scene no (1-based).
void re4dc_bench_scene_def(int no, unsigned begin, unsigned end, const char* name)
{
    if (no < 1 || no > kAllScenes) return;
    Scene& s = g_scene[no - 1];
    memset(&s, 0, sizeof(s));
    strncpy(s.name, name ? name : "-", sizeof(s.name) - 1);
    s.begin = begin; s.end = end; s.defined = true;
    s.min_fps10 = ~0u; s.kos_min = ~0u;
    if (no - 1 < kScenes) memset(&g_pmc[no - 1], 0, sizeof(g_pmc[no - 1]));
    if (no - 1 == kSweepScene) {
        memset(g_sw, 0, sizeof(g_sw));
        g_sw_state = SW_IDLE; g_sw_k = -1; g_sw_measuring = false;
        re4dc_bench_frozen = 0;
        sweep_apply(-1);
    }
    g_period_live = false;
    g_period_dst = nullptr;
    g_cur = no - 1;
    g_prev_include = g_last_include = false;
    re4dc_log("bench: scene %d %s armed: measure room frames %u..%u (run %u)\n", no, s.name, begin, end, g_run);
}

// Each game tick of the scene's room (re4dc_warp_poll, first room): KOS headroom, the measured range. 1 = the scene
// ended at this room frame (the caller logs the state and moves on).
int re4dc_bench_tick(unsigned room_frame)
{
    Scene& s = g_scene[g_cur];
    if (!s.defined || s.done) return 0;
    g_room_frame = room_frame;
    unsigned f = 0, u = 0, b = 0;
    re4dc_kos_heap_state(&f, &u, &b);
    if (f + b < s.kos_min) s.kos_min = f + b;
    if (g_cur == kSweepScene) {   // 2 = the logic freezes after this tick, 1 = the sweep is over
        if (g_sw_state == SW_DONE) {
            s.done = true;
            s.end_frame = room_frame;
            re4dc_log("bench: scene 3 end room frame %u (sweep done)\n", room_frame);
            return 1;
        }
        if (g_sw_state == SW_IDLE && room_frame >= s.begin) {
            sweep_start();
            return 2;
        }
        return 0;
    }
    if (room_frame == s.begin) {
        s.measuring = true;
        re4dc_log("bench: scene %d begin room frame %u\n", g_cur + 1, room_frame);
    }
    if (room_frame >= s.end) {
        s.measuring = false;
        s.done = true;
        s.end_frame = room_frame;
        re4dc_log("bench: scene %d end room frame %u windows=%u fps10=%u min1s10=%u cpu10=%u gpu10=%u kos_min=%u\n",
                  g_cur + 1, room_frame, s.windows, fps10(s), s.windows ? s.min_fps10 : 0, cpu10(s), gpu10(s), s.kos_min);
        return 1;
    }
    return 0;
}

// After a scene ended: the fixture of the next scene, or nullptr after the last one (then the results screen).
const char* re4dc_bench_next_scene(void)
{
    return g_cur + 1 < kAllScenes ? kScenePath[g_cur + 1] : nullptr;
}
int re4dc_bench_scene_no(void) { return g_cur + 1; }

// Results screen (the warp rig's poll, the frame loop stopped there): returns when A was pressed and released; the
// caller then runs scene 1 again. Draws into the displayed framebuffer, again whenever the display flips.
const char* re4dc_bench_results(void)
{
    g_period_live = false;   // no counter period runs on the results screen
    if (g_pmc_hw) perf_cntr_stop(PRFC1);
    log_results();
    log_counters();
    log_sweep();
    re4dc_log("bench: results screen fb=%08lx ctrl=%08lx\n", (unsigned long) *(volatile uint32_t*) 0xA05F8050,
              (unsigned long) *(volatile uint32_t*) 0xA05F8044);
    uint32_t last_sof = ~0u;
    int page = 0, shown = -1;
    bool up = false, down = false;   // A must be up first (a held A does not restart), then pressed and released
    bool pup = false, pdown = false; // B or Y: the same, switches the page
    for (;;) {
        const uint32_t sof = *(volatile uint32_t*) 0xA05F8050;
        if (sof != last_sof || page != shown) {
            last_sof = sof; shown = page;
            if (page == 2) draw_sweep(fb_displayed());
            else if (page == 1) draw_counters(fb_displayed());
            else draw_results(fb_displayed());
        }
        const unsigned btn = pad_buttons();
        const bool a = (btn & CONT_A) != 0, by = (btn & (CONT_B | CONT_Y)) != 0;
        if (!a) { if (down) break; up = true; }
        else if (up) down = true;
        if (!by) {
            if (pdown) { page = (page + 1) % 3; pdown = false; re4dc_log("bench: results page %d\n", page + 1); }
            pup = true;
        } else if (pup) pdown = true;
        ++g_results_ticks;
        spin_us(30000);
    }
    ++g_run;
    re4dc_log("bench: A pressed: run %u\n", g_run);
    g_cur = 0;
    return kScenePath[0];
}

// ---------------------------------------------------------------- measurement hooks
// pace.cpp vmu_window, each one-second window close: drawn frames, game ticks, vblanks, PVR render time of the renders
// that completed in the window. A window counts when the scene measured at its start and at its end.
void re4dc_bench_window(unsigned drawn, unsigned ticks, unsigned vblanks, unsigned long long rnd_sum_ns, unsigned rnd_n)
{
    if (g_cur == kSweepScene) {   // geometry sweep: GPU render time of windows wholly inside one setting's measure
        const int k = g_sw_measuring ? g_sw_k : -1;
        if (k >= 0 && k == g_sw_prev_win) {
            g_sw[k].rnd_sum_ns += rnd_sum_ns; g_sw[k].rnd_n += rnd_n; ++g_sw[k].windows;
        }
        g_sw_prev_win = k;
        g_prev_include = g_last_include = false;
        return;
    }
    Scene& s = g_scene[g_cur];
    const bool now = s.defined && s.measuring;
    const bool include = now && g_prev_include;
    g_prev_include = now;
    g_last_include = include;
    if (!include || !vblanks) return;
    ++s.windows;
    s.drawn += drawn; s.ticks += ticks; s.vblanks += vblanks;
    s.rnd_sum_ns += rnd_sum_ns; s.rnd_n += rnd_n;
    const unsigned f10 = (unsigned) ((unsigned long long) drawn * 59940ULL / 100 / vblanks);
    if (f10 < s.min_fps10) s.min_fps10 = f10;
    // CPU: a new tick log window, wholly inside the range (GAME_TICK_LOG ticks after its begin)
    const char* nm[32];
    unsigned avg[32], seq = 0;
    const int n = re4dc_tick_log_snapshot(nm, avg, nullptr, 32, &seq);
    if (n > 0 && seq != g_tick_seq) {
        g_tick_seq = seq;
        if (g_room_frame >= s.begin + 2 * 60)
            for (int i = 0; i < n; ++i)
                if (nm[i] && !strcmp(nm[i], "cpu")) { s.cpu_us_sum += avg[i]; ++s.cpu_n; }
    }
}
// dvd_read_safe.cpp re4dc_disc_meter_window, right after re4dc_bench_window in the same window close: the window's
// game reads (not the music stream) and the game thread's time inside drive calls.
void re4dc_bench_disc(unsigned reads, unsigned long long block_us, unsigned long long dt_us)
{
    if (!g_last_include) return;
    Scene& s = g_scene[g_cur];
    s.reads += reads; s.block_us += block_us; s.disc_us += dt_us;
}

// ---------------------------------------------------------------- counter marks (main.cpp, trans.cpp, coarse.cpp)
// The frame enters part `phase` (0 logic, 1 actor prep, 2 actor draw, 3 world draw, 4 other, 5 wait): the part left
// gets the cycles and the counter 2 events since the last mark.
void re4dc_bench_phase(int phase)
{
    if (g_period_live) {
        const unsigned long long c = cyc_now(), e = g_pmc_hw ? perf_cntr_count(PRFC1) : 0;
        g_pc[g_ph] += c - g_c0;
        g_pe[g_ph] += e - g_e0;
        g_c0 = c; g_e0 = e;
    }
    g_ph = phase;
}
// A nested part (an actor's OT callback inside another part): returns the part to resume.
int re4dc_bench_push(int phase)
{
    const int prev = g_ph;
    re4dc_bench_phase(phase);
    return prev;
}
// Top of every main loop iteration (after the pace decision). A drawn iteration closes the running drawn-frame period
// (counted when the scene measured all through it) and starts the next one on the next event.
void re4dc_bench_iter(int drawn)
{
    re4dc_bench_phase(4);   // the wait of the previous iteration ends here
    sweep_step();
    if (!drawn) return;
    Pmc* const target = period_target();
    const bool now = target != nullptr;
    if (g_period_live && now && g_period_dst == target) {
        Pmc& m = *target;
        if (g_cur == kSweepScene && g_sw_k >= 0) {   // the frame just completed was drawn under this setting
            unsigned calls = 0, bytes = 0;
            re4dc_bench_ta(&calls, &bytes);
            g_sw[g_sw_k].ta_calls += calls; g_sw[g_sw_k].ta_bytes += bytes; ++g_sw[g_sw_k].ta_n;
        }
        ++m.periods;
        ++m.ev_periods[g_ev_i];
        for (int p = 0; p < kPh; ++p) {
            m.cyc[p] += g_pc[p];
            m.ev[g_ev_i][p] += g_pe[p];
            m.ev_cyc[g_ev_i][p] += g_pc[p];
        }
        g_ev_i = (g_ev_i + 1) % kEv;
    }
    for (int p = 0; p < kPh; ++p) g_pc[p] = g_pe[p] = 0;
    g_period_live = now;
    g_period_dst = target;
    if (now) {
        if (g_pmc_hw) {
            pmc_event(kEvCode[g_ev_i]);
            g_e0 = perf_cntr_count(PRFC1);
        }
        g_c0 = cyc_now();
    }
}

// ---------------------------------------------------------------- banner (native_ui.cpp, every presented frame)
const char* re4dc_bench_banner(void) { return "BENCHMARK DISC - NOT THE GAME"; }

// ---------------------------------------------------------------- geometry sweep settings (render only)
unsigned re4dc_bench_hide(void) { return g_hide; }   // 1 every Ganado, 4 every other Ganado, 2 Leon not drawn
float re4dc_bench_world_far(float far) { return g_world_far > 0.0f && g_world_far < far ? g_world_far : far; }

// ---------------------------------------------------------------- wraps
extern "C" void* __wrap_maple_dev_status(maple_device_t* dev)
{
    static cont_state_t idle;
    void* st = __real_maple_dev_status(dev);
    if (g_masked && st && dev && (dev->info.functions & MAPLE_FUNC_CONTROLLER)) {
        memset(&idle, 0, sizeof(idle));
        return &idle;
    }
    return st;
}

// The game's VMU layer (platform/vmu_store.cpp, vmu_lcd.cpp) finds cards through maple_enum_dev: it sees none, so the
// boot takes the no-card path and the disc writes nothing to any VMU.
extern "C" maple_device_t* __wrap_maple_enum_dev(int p, int u)
{
    maple_device_t* d = __real_maple_enum_dev(p, u);
    if (g_hide_vmu && d && (d->info.functions & MAPLE_FUNC_MEMCARD)) return nullptr;
    return d;
}

extern "C" unsigned __wrap_re4dc_ui_frame(void)
{
    return __real_re4dc_ui_frame() + g_results_ticks;
}

extern "C" void __wrap_OSInit(void)
{
    g_hide_vmu = true;
    static bool done;
    __real_OSInit();
    if (done) return;
    done = true;
    pmc_detect();
    vid_set_mode(DM_640x480, PM_RGB565);
    const Fb fb = fb_boot();
    const uint64_t t0 = timer_us_gettime64();
    constexpr unsigned kAuto = 20;
    unsigned shown = ~0u;
    bool pressed = false;
    for (;;) {
        const unsigned el = (unsigned) ((timer_us_gettime64() - t0) / 1000000);
        if (el != shown) {
            shown = el;
            fb_fill(fb, 0, 0, 640, 480, 0x000000);
            int y = 30;
            fb_fill(fb, 30, y - 6, 580, 76, 0x900000);
            fb_center(fb, y, 3, 4, kWhite, "BENCHMARK DISC"); y += 36;
            fb_center(fb, y, 3, 4, kWhite, "THIS IS NOT THE GAME"); y += 50;
            fb_center(fb, y, 2, 3, kYellow, "RE4 DREAMCAST PORT - PERFORMANCE TEST"); y += 36;
            const char* body[] = {"THIS DISC ONLY MEASURES PERFORMANCE.",
                                  "IT CANNOT BE PLAYED AND SAVES NOTHING.",
                                  "TO PLAY, USE THE CURRENT TEST RELEASE:",
                                  "GITHUB.COM/LAMB2K/RE4DC - RELEASES",
                                  "",
                                  "IT RUNS THREE SCRIPTED SCENES BY ITSELF",
                                  "(ABOUT 5 MINUTES), THEN SHOWS RESULTS.",
                                  "AFTER START DO NOT TOUCH THE CONTROLLER.",
                                  "PHOTOGRAPH BOTH RESULTS PAGES (B SWITCHES)."};
            for (const char* s : body) { fb_text(fb, 60, y, 2, 2, s[0] == 'G' ? kGreen : kWhite, s); y += 22; }
            y += 8;
            char msg[64];
            snprintf(msg, sizeof(msg), "BUILD %s", RE4DC_BENCH_ID);
            fb_text(fb, 60, y, 2, 2, kGrey, msg); y += 30;
            snprintf(msg, sizeof(msg), "PRESS START TO BEGIN (AUTO IN %u S)", el < kAuto ? kAuto - el : 0);
            fb_text(fb, 60, y, 2, 3, kCyan, msg);
        }
        const unsigned btn = pad_buttons();
        if (btn & CONT_START) pressed = true;
        if ((pressed && !(btn & CONT_START)) || el >= kAuto) break;   // START released, or timeout
        thd_sleep(20);
    }
    fb_fill(fb, 0, 0, 640, 480, 0x000000);
    fb_center(fb, 200, 3, 4, kWhite, "BENCHMARK DISC - NOT THE GAME");
    fb_center(fb, 250, 2, 3, kCyan, "STARTING - HANDS OFF THE CONTROLLER");
    g_masked = true;
    re4dc_log("bench: start (%s) build %s\n", pressed ? "START" : "auto", RE4DC_BENCH_ID);
}

}  // extern "C"
