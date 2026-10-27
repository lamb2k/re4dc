// D367 public benchmark disc (BENCHMARK=1 in bench.mk; benchmark disc only, never a play image).
//
// User 2026-10-15: "Can we make the benchmark disk public for testers to help out with? With a clear indicator that it
// isn't the game?" The disc boots into a start screen that says it is not the game, runs scripted scenes through the
// warp rig (dbgwarp_bridge.cpp) and ends on a results screen with a code testers can type. Built on the 10-04 hwcal r21v
// console disc (start screen in the KOS framebuffer before pvr_init, own 5x7 font, results drawn into the displayed
// framebuffer while the frame loop stops, re4dc_ui_frame kept moving for CRASH_SCREEN's watchdog) and on the T12 Phases
// disc meters (one-second pace windows, tick log CPU, disc read meter). hwcal traps kept out: no VMU file (its write
// failed with -7 on the console: results are on screen only), no per-frame PMC rotation (no PMC at all).
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
#include <arch/timer.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#if defined(RE4DC_HOUSE_ARENA27_COUNTS) && RE4DC_HOUSE_ARENA27_COUNTS
#include "platform/include/house_arena27_counts.h"
#endif

extern "C" {
void re4dc_log(const char* fmt, ...);
void re4dc_kos_heap_state(unsigned* free_chunks, unsigned* used, unsigned* break_room);  // platform/os.cpp
int re4dc_tick_log_snapshot(const char** name, unsigned* avg_us, unsigned* max_us, int max, unsigned* seq);  // tick_log.cpp
void __real_OSInit(void);
void* __real_maple_dev_status(maple_device_t* dev);
maple_device_t* __real_maple_enum_dev(int p, int u);
unsigned __real_re4dc_ui_frame(void);
uint32_t re4dc_vi_retrace_count(void);   // TAIL_METER
void re4dc_cache20_arm(int on) __attribute__((weak));   // platform/cache20.cpp (BENCH_CENSUS: the arm's levers)
}

namespace {
// ---------------------------------------------------------------- scenes
// RE4DC_BENCH_SCENES (default 2; STRESS_SADDLER's stress disc: 4 = full, g70, g50, full again; CAP_COMPARE's cap
// comparison disc: 8 = r101 cross at cap 3 / 4 / 5 / 6, r103 farm at cap 3 / 6 with and without the animals): scene k > 1
// is /cd/dc/bench<k>.txt. RE4DC_BENCH_NAME: the disc's name on the start / results screens and the banner.
// RE4DC_BENCH_CAPCMP (CAP_COMPARE=1, lane cap16 2026-10-16): the results screen adds the Ganados alive (avg / min / max,
// one digit per second), drawn vs skipped ticks, ms per picture and the logic split (EmMgr.move = enemies and animals,
// Player = Leon) from the tick log; the start screen picks one scene with X / Y / A / B (r101) or the d-pad (farm), and
// scenes 9..14 (the translucency arms, coordinator 10-16) with a d-pad + face combo. With TA_HASH=4 (count only) a second
// results page (Y) shows the TA input per display list per presented frame (OP / PT / TR / modifier KB) beside the GPU
// render time, for the translucency arms (world translucent pass off, effect sprites off, both).
#ifndef RE4DC_BENCH_SCENES
#define RE4DC_BENCH_SCENES 2
#endif
#ifndef RE4DC_BENCH_MENU
#define RE4DC_BENCH_MENU "X: SCENE 1 ONLY  Y: SCENE 2  B: SCENE 3"
#endif
#ifndef RE4DC_BENCH_NAME
#define RE4DC_BENCH_NAME "BENCHMARK DISC"
#endif
#ifndef RE4DC_HOUSE_ARENA27
#define RE4DC_HOUSE_ARENA27 0
#endif
#if RE4DC_HOUSE_ARENA27
#ifndef RE4DC_HOUSE_ARENA27_AUTO
#define RE4DC_HOUSE_ARENA27_AUTO 0
#endif
static_assert(RE4DC_BENCH_SCENES == 3, "house arena needs exactly three scenes");
static_assert(RE4DC_HOUSE_ARENA27_BEGIN > 0 && RE4DC_HOUSE_ARENA27_END > RE4DC_HOUSE_ARENA27_BEGIN + 120,
              "house arena needs warmup and more than 120 measured ticks for the existing CPU snapshot");
#ifndef RE4DC_HOUSE_ARENA27_COUNTS
#define RE4DC_HOUSE_ARENA27_COUNTS 0
#endif
static const char* const kArenaNames[3] = {"Original", "Rebuilt", "Sparse"};
#endif
constexpr int kScenes = RE4DC_BENCH_SCENES;
#ifndef RE4DC_BENCH_CENSUS
#define RE4DC_BENCH_CENSUS 0
#endif
static_assert(kScenes >= 2 && kScenes <= (RE4DC_BENCH_CENSUS ? 24 : 16), "RE4DC_BENCH_SCENES 2..16 (census discs 24)");
#ifndef RE4DC_BENCH_CAPCMP
#define RE4DC_BENCH_CAPCMP 0
#endif
#ifndef RE4DC_BENCH_MENU2
#define RE4DC_BENCH_MENU2 ""
#endif
#ifndef RE4DC_BENCH_MENU3
#define RE4DC_BENCH_MENU3 ""
#endif
constexpr bool kTight = kScenes > 2;   // more result rows: smaller rows, no photo note
const char* const kScenePath[16] = {"/cd/dc/warp.txt", "/cd/dc/bench2.txt", "/cd/dc/bench3.txt", "/cd/dc/bench4.txt",
                                    "/cd/dc/bench5.txt", "/cd/dc/bench6.txt", "/cd/dc/bench7.txt", "/cd/dc/bench8.txt",
                                    "/cd/dc/bench9.txt", "/cd/dc/bench10.txt", "/cd/dc/bench11.txt", "/cd/dc/bench12.txt",
                                    "/cd/dc/bench13.txt", "/cd/dc/bench14.txt", "/cd/dc/bench15.txt", "/cd/dc/bench16.txt"};
// The start screen's choice on a disc of more than two scenes (the Saddler stress disc: START all, X / Y / B one scene):
// -1 = every scene in order, k = scene k + 1 alone (then the results screen).
int g_only = -1;
// BENCH_CENSUS (lane cache20, cache20 bench disc): a fixture file may hold several `bench` lines (rows): the rows of one
// file run back to back in the same room without a reset (a row ends, the next row of the file starts at its own begin
// frame), so timed warp lines between them (rigid / fx / crowd / tank / autofire) change one thing per row. Files:
// RE4DC_BENCH_FILES (warp.txt, bench2.txt, ...); rows: RE4DC_BENCH_SCENES. The start screen also picks the arm:
// D-pad LEFT = A (re4dc_cache20_mask 0), RIGHT = B (every built cache20 lever); the results show it.
#ifndef RE4DC_BENCH_FILES
#define RE4DC_BENCH_FILES RE4DC_BENCH_SCENES
#endif
constexpr int kFiles = RE4DC_BENCH_FILES;
int g_file;                       // fixture file of the running rows
bool g_file_first;                // the next `bench` line is the file's first row
char g_arm = 'A';
#if RE4DC_HOUSE_ARENA27 && RE4DC_HOUSE_ARENA27_COUNTS
constexpr unsigned kGeometryMetrics = 7;
struct ArenaGeometry {
    unsigned n, first_room, last_room, first_ui, last_ui, last_sequence, invalid, sequence_bad, identity_bad;
    unsigned mesh_crc, mesh_bytes, camera_hash;
    unsigned long long sum[kGeometryMetrics];
    unsigned min[kGeometryMetrics], max[kGeometryMetrics];
    Re4dcHouseArena27Geometry baseline, sample[4];
    unsigned sample_mask;
    bool have_baseline;
};
#endif
struct Scene {
#if RE4DC_HOUSE_ARENA27 && RE4DC_HOUSE_ARENA27_COUNTS
    ArenaGeometry geometry[3];
#endif
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
    // Ganados alive (the rooms' own count, SceCountEmAlive(0x10, 0x20)) each measured tick; one sample per second
    unsigned long long alive_sum;
    unsigned alive_n, alive_min, alive_max, n_sec;
    unsigned char alive_sec[48];
    // tick log (GAME_TICK_LOG) phases by marker name (g_ph_name): us per tick summed over the measured tick-log windows,
    // e.g. EmMgr.move (every enemy and animal's logic), Player (Leon's logic), EspMove / EspTrans (effects)
    unsigned long long ph_sum[24];
    unsigned ph_n[24];
    unsigned cpu_max_us;          // the worst tick-log window's slowest tick (cpu marker max)
    // TA input per display list (TA_HASH=4 count-only: native_ui.cpp re4dc_ta_count): 32-bit words summed over the
    // presented scenes of the measured windows (0 op, 1 op modifier, 2 tr, 3 tr modifier, 4 pt), and those scenes
    unsigned long long ta_words[5];
    unsigned ta_scenes;
    // TAIL_METER: per drawn picture (us; T_VB / T_ITER are counts), summed and worst over the measured pictures
    unsigned long long tl_sum[10];
    unsigned tl_max[10], tl_n, tl_rnd_n;
    // BENCH_CENSUS, each measured tick: live effects (esp pool), hits on the tank target (total at the row end), rigid
    // parts / vertices reaching the draw
    int file;
    unsigned long long esp_sum, rg_parts_sum, rg_verts_sum;
    unsigned esp_max, cen_n, hits0, hits1;
};
#ifndef RE4DC_TAIL_METER
#define RE4DC_TAIL_METER 0
#endif
// TAIL_METER columns: picture period, CPU work, CPU blocked in the PVR scene open / close, spin to the next vblank,
// spin over further vblanks (pacing), TA done (after the drawn tick's start), PVR render, queue (TA done to render
// start: a finished scene waiting for the PVR), vblanks per picture, ticks per picture
enum { T_PIC, T_WORK, T_BLK, T_ROUND, T_PACE, T_TA, T_RND, T_QUEUE, T_VB, T_ITER, kTN };
Scene g_scene[kScenes];
int g_cur;                        // scene being run
unsigned g_run = 1;               // run number (A on the results screen starts the next)
unsigned g_room_frame;
bool g_prev_include, g_last_include;
unsigned g_tick_seq;
int g_alive_now;                  // re4dc_bench_alive, this tick
const char* g_ph_name[24];        // tick log marker names (string literals of the game: stable pointers)
unsigned g_ta_prev[6];            // re4dc_ta_count at the previous window close
int g_page;                       // results page (Y switches; CAP_COMPARE with more than 8 scenes)
}  // namespace
// TA_HASH=4 (count only; native_ui.cpp): words per list of the presented scenes so far ([0..4]) and those scenes ([5]);
// weak: absent without TA_HASH=4.
extern "C" unsigned* re4dc_ta_count_ptr(void) __attribute__((weak));
namespace {

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
unsigned mspic10(const Scene& s) { return s.drawn ? (unsigned) ((unsigned long long) s.vblanks * 1000000ULL / (5994ULL * s.drawn)) : 0; }
unsigned skipped(const Scene& s) { return s.ticks > s.drawn ? s.ticks - s.drawn : 0; }
unsigned alive10(const Scene& s) { return s.alive_n ? (unsigned) ((s.alive_sum * 10 + s.alive_n / 2) / s.alive_n) : 0; }
unsigned ph_us(const Scene& s, const char* name) {   // a phase's average us per tick, 0 when never seen
    for (int i = 0; i < 24 && g_ph_name[i]; ++i)
        if (!strcmp(g_ph_name[i], name)) return s.ph_n[i] ? (unsigned) (s.ph_sum[i] / s.ph_n[i]) : 0;
    return 0;
}
unsigned ms10(unsigned us) { return (us + 50) / 100; }
unsigned cen_avg(unsigned long long sum, unsigned n) { return n ? (unsigned) ((sum + n / 2) / n) : 0; }
unsigned em10(const Scene& s) { return ms10(ph_us(s, "EmMgr.move")); }
unsigned pl10(const Scene& s) { return ms10(ph_us(s, "Player")); }
unsigned fx10(const Scene& s) { return ms10(ph_us(s, "EspMove") + ph_us(s, "EspTrans")); }
unsigned takb10(const Scene& s, int l) {   // KB of TA input per presented frame in list l, x10
    return s.ta_scenes ? (unsigned) ((s.ta_words[l] * 4 * 10 / 1024 + s.ta_scenes / 2) / s.ta_scenes) : 0;
}
const char* d1(unsigned v10, char* buf) { snprintf(buf, 12, "%u.%u", v10 / 10, v10 % 10); return buf; }

// The code testers type: per scene A/B fps*10.min1s*10.cpu*10.gpu*10.reads/s*10.wait ms/s.kos KB, then a check value over
// the build id and the numbers (two hex digits) so a mistyped code shows.
void make_code(char* out, unsigned size) {
    char part[kScenes][64];
    for (int k = 0; k < kScenes; ++k) {
        const Scene& s = g_scene[k];
        if (RE4DC_BENCH_CAPCMP)
            snprintf(part[k], sizeof(part[k]), "%c%u.%u.%u.%u.%u", 'A' + k, fps10(s), cpu10(s), gpu10(s), alive10(s),
                     s.alive_max);
        else
            snprintf(part[k], sizeof(part[k]), "%c%u.%u.%u.%u.%u.%u.%u", 'A' + k, fps10(s), s.windows ? s.min_fps10 : 0,
                     cpu10(s), gpu10(s), reads_ps10(s), wait_ms(s), kos_kb(s));
    }
    char body[384], parts[352] = "";
    for (int k = 0; k < kScenes; ++k) {
        if (k) strncat(parts, " ", sizeof(parts) - strlen(parts) - 1);
        strncat(parts, part[k], sizeof(parts) - strlen(parts) - 1);
    }
    snprintf(body, sizeof(body), "%s %s", RE4DC_BENCH_ID, parts);
    unsigned ck = 0;
    for (const char* p = body; *p; ++p) ck = (ck * 31 + (unsigned char) *p) % 251;
    snprintf(out, size, "%s %02X", parts, ck);
}

// CAP_COMPARE results: 8 scenes per 640x480 page (no footnotes; the log has every number). Page 0: scenes 1..8 (the
// caps and the farm animals); page 1 (more than 8 scenes): the translucency arms beside their as-shipped scenes.
int page_scenes(int page, int* idx) {
    if (page == 0 || kScenes <= 8) { int n = 0; for (int k = 0; k < kScenes && k < 8; ++k) idx[n++] = k; return n; }
    static const int kT[8] = {3, 8, 9, 10, 6, 11, 12, 13};   // r101 cap 6 T0..T3, farm cap 6 T0..T3
    int n = 0;
    for (int k : kT) if (k < kScenes) idx[n++] = k;
    return n;
}
void draw_results_capcmp(const Fb& fb, int page) {
    char a[12], b[12], c[12], d[12], e[12], f[12], line[160];
    int idx[8];
    const int ns = page_scenes(page, idx);
    fb_fill(fb, 0, 0, fb.w, fb.h, 0x000000);
    int y = 8;
    fb_fill(fb, 30, y - 4, 580, 29, 0x900000);
    fb_center(fb, y, 2, 3, kWhite, RE4DC_BENCH_NAME " - NOT THE GAME"); y += 26;
    snprintf(line, sizeof(line), "BUILD %s  RUN %u  PAGE %d/%d %s  A: RUN AGAIN%s", RE4DC_BENCH_ID, g_run, page + 1,
             kScenes > 8 ? 2 : 1, page ? "TRANSLUCENCY (CAP 6)" : "GANADO CAP + FARM ANIMALS", kScenes > 8 ? "  Y: NEXT PAGE" : "");
    fb_center(fb, y, 1, 2, kGrey, line); y += 18;
    fb_text(fb, 20, y, 2, 2, kCyan, "SCENE            FPS  MIN MS/PIC CPU/T   GPU SPD%"); y += 18;
    for (int q = 0; q < ns; ++q) {
        const int k = idx[q];
        const Scene& s = g_scene[k];
        if (!s.windows) { snprintf(line, sizeof(line), "%d %-14s NOT MEASURED", k + 1, s.name); fb_text(fb, 20, y, 2, 2, kRed, line); y += 16; continue; }
        snprintf(line, sizeof(line), "%d %-14s%5s%5s%7s%6s%6s%5u", k + 1, s.name, d1(fps10(s), a), d1(s.min_fps10, b),
                 d1(mspic10(s), c), d1(cpu10(s), d), d1(gpu10(s), e), speed_pct(s));
        fb_text(fb, 20, y, 2, 2, kWhite, line); y += 16;
    }
    y += 4;
    if (page) {
        // TA input per presented frame by display list (TA_HASH=4), the render time and the effect / logic phases
        fb_text(fb, 20, y, 1, 2, kCyan, "SCENE           TA KB PER FRAME:   OP    PT    TR  TRMOD  OPMOD   RENDER MS  FX MS/TICK  ALIVE"); y += 16;
        for (int q = 0; q < ns; ++q) {
            const int k = idx[q];
            const Scene& s = g_scene[k];
            char g[12], h[12], i2[12];
            snprintf(line, sizeof(line), "%2d %-14s %20s %5s %5s %6s %6s %11s %11s %6s", k + 1, s.name, d1(takb10(s, 0), a),
                     d1(takb10(s, 4), b), d1(takb10(s, 2), c), d1(takb10(s, 3), d), d1(takb10(s, 1), e), d1(gpu10(s), f),
                     d1(fx10(s), g), d1(alive10(s), h));
            (void) i2;
            fb_text(fb, 20, y, 1, 2, kWhite, line); y += 14;
        }
        y += 6;
        fb_text(fb, 20, y, 1, 2, kGrey, "T0 AS SHIPPED  T1 NO WORLD TRANSLUCENT PASS  T2 NO EFFECT SPRITES  T3 BOTH (NO ALPHA)"); y += 14;
        fb_text(fb, 20, y, 1, 2, kGrey, "RENDER MS = PVR RENDER TIME PER PICTURE (ISP/TSP); TA KB = TA INPUT PER PRESENTED FRAME"); y += 14;
        return;
    }
    fb_text(fb, 20, y, 1, 2, kCyan, "SCENE          ALIVE AVG MIN MAX  TICKS DRAWN SKIP  MS/TICK ENEMY LEON  FX WORST  READS/S WAIT KOS"); y += 16;
    for (int q = 0; q < ns; ++q) {
        const int k = idx[q];
        const Scene& s = g_scene[k];
        char g[12], h[12];
        snprintf(line, sizeof(line), "%d %-14s %9s %3u %3u  %11u %4u  %13s %4s %3s %5s  %7s %4u %3u", k + 1, s.name,
                 d1(alive10(s), a), s.alive_n ? s.alive_min : 0, s.alive_max, s.drawn, skipped(s), d1(em10(s), f),
                 d1(pl10(s), e), d1(fx10(s), g), d1(ms10(s.cpu_max_us), h), d1(reads_ps10(s), b), wait_ms(s), kos_kb(s));
        fb_text(fb, 20, y, 1, 2, kWhite, line); y += 14;
    }
    y += 4;
    fb_text(fb, 20, y, 1, 2, kCyan, "GANADOS ALIVE, ONE DIGIT PER SECOND OF THE MEASURED WINDOW"); y += 16;
    for (int q = 0; q < ns; ++q) {
        const int k = idx[q];
        const Scene& s = g_scene[k];
        char digits[49];
        unsigned n = s.n_sec < 48 ? s.n_sec : 48;
        for (unsigned i = 0; i < n; ++i) digits[i] = s.alive_sec[i] > 9 ? '+' : (char) ('0' + s.alive_sec[i]);
        digits[n] = 0;
        snprintf(line, sizeof(line), "%d %-14s %s", k + 1, s.name, digits);
        fb_text(fb, 20, y, 1, 2, kGreen, line); y += 14;
    }
}

// TAIL_METER results page 2 (Y): where each drawn picture's time goes, average / worst per scene, 0.1 ms.
unsigned tl_avg(const Scene& s, int c) { return s.tl_n ? (unsigned) (s.tl_sum[c] / s.tl_n) : 0; }
const char* tl_cell(const Scene& s, int c, char* buf) {   // "avg/worst" in ms (counts: x.x / n)
    char a[12], b[12];
    if (c == T_VB || c == T_ITER) {
        const unsigned avg10 = s.tl_n ? (unsigned) ((s.tl_sum[c] * 10 + s.tl_n / 2) / s.tl_n) : 0;
        snprintf(buf, 16, "%s/%u", d1(avg10, a), s.tl_max[c]);
    } else if (c == T_RND || c == T_QUEUE) {
        const unsigned avg = s.tl_rnd_n ? (unsigned) (s.tl_sum[c] / s.tl_rnd_n) : 0;
        snprintf(buf, 16, "%s/%s", d1(ms10(avg), a), d1(ms10(s.tl_max[c]), b));
    } else {
        snprintf(buf, 16, "%s/%s", d1(ms10(tl_avg(s, c)), a), d1(ms10(s.tl_max[c]), b));
    }
    return buf;
}
void draw_results_tail(const Fb& fb) {
    char line[160], c1[16], c2[16], c3[16], c4[16], c5[16], c6[16];
    fb_fill(fb, 0, 0, fb.w, fb.h, 0x000000);
    int y = 8;
    fb_fill(fb, 30, y - 4, 580, 29, 0x900000);
    fb_center(fb, y, 2, 3, kWhite, RE4DC_BENCH_NAME " - NOT THE GAME"); y += 30;
    snprintf(line, sizeof(line), "FRAME TAIL  BUILD %s  RUN %u  PAGE 2/2  Y: PAGE 1  A: RUN AGAIN", RE4DC_BENCH_ID, g_run);
    fb_center(fb, y, 1, 2, kGrey, line); y += 18;
    fb_text(fb, 16, y, 1, 2, kYellow, "MS PER DRAWN PICTURE, AVERAGE/WORST"); y += 18;
    fb_text(fb, 16, y, 1, 2, kCyan, "SCENE           PICTURE    CPU WORK    WAIT GPU   TO VBLANK      PACING     VB/PIC"); y += 16;
    for (int k = 0; k < kScenes; ++k) {
        const Scene& s = g_scene[k];
        if (!s.tl_n) { snprintf(line, sizeof(line), "%d %-12s NOT MEASURED", k + 1, s.name); fb_text(fb, 16, y, 1, 2, kRed, line); y += 15; continue; }
        snprintf(line, sizeof(line), "%d %-12s %10s %11s %11s %11s %11s %10s", k + 1, s.name, tl_cell(s, T_PIC, c1),
                 tl_cell(s, T_WORK, c2), tl_cell(s, T_BLK, c3), tl_cell(s, T_ROUND, c4), tl_cell(s, T_PACE, c5), tl_cell(s, T_VB, c6));
        fb_text(fb, 16, y, 1, 2, kWhite, line); y += 15;
    }
    y += 8;
    fb_text(fb, 16, y, 1, 2, kCyan, "SCENE           TA DONE      RENDER   TA->RENDER  GPU BUSY%  TICKS/PIC   PICTURES"); y += 16;
    for (int k = 0; k < kScenes; ++k) {
        const Scene& s = g_scene[k];
        if (!s.tl_n) continue;
        snprintf(line, sizeof(line), "%d %-12s %10s %11s %11s %10u %10s %10u", k + 1, s.name, tl_cell(s, T_TA, c1),
                 tl_cell(s, T_RND, c2), tl_cell(s, T_QUEUE, c3),
                 (unsigned) (s.tl_rnd_n && s.tl_sum[T_PIC] ? s.tl_sum[T_RND] * 100ULL * s.tl_n / s.tl_rnd_n / s.tl_sum[T_PIC] : 0),
                 tl_cell(s, T_ITER, c4), s.tl_n);
        fb_text(fb, 16, y, 1, 2, kWhite, line); y += 15;
    }
    y += 10;
    const char* notes[] = {
        "PICTURE: TIME BETWEEN SHOWN PICTURES.  CPU WORK: GAME CPU TIME OF ALL TICKS OF THE PICTURE.",
        "WAIT GPU: CPU STOPPED IN THE GRAPHICS CHIP SCENE OPEN / FINISH (FENCES, TA BANK, PRESENT).",
        "TO VBLANK: SPIN FROM THE END OF WORK TO THE NEXT VBLANK.  PACING: SPIN OVER FURTHER VBLANKS.",
        "TA DONE: SCENE FULLY IN THE TA, MS AFTER THE DRAWN TICK STARTED.  RENDER: PVR RENDER TIME.",
        "TA->RENDER: A FINISHED SCENE WAITING FOR THE PVR TO START IT.  GPU BUSY%: RENDER TIME / PICTURE TIME.",
        "PLEASE PHOTOGRAPH BOTH PAGES."};
    for (const char* n : notes) { fb_text(fb, 16, y, 1, 2, kGrey, n); y += 15; }
}

// BENCH_CENSUS results page 1: every row with fps, CPU per tick, GPU, the frame-tail buckets (CPU work, GPU wait, to vblank,
// pacing), the logic phases (enemies, Leon, effects), Ganados alive, live effects, hits on the tank target, rigid parts.
void draw_results_census(const Fb& fb) {
    char line[160], a[12], b[12], c[12], d[12], e[12], g[12], h[12], i2[12], j[12], k2[12];
    fb_fill(fb, 0, 0, fb.w, fb.h, 0x000000);
    int y = 6;
    fb_fill(fb, 30, y - 4, 580, 26, 0x900000);
    fb_center(fb, y, 2, 2, kWhite, RE4DC_BENCH_NAME " - NOT THE GAME"); y += 24;
    snprintf(line, sizeof(line), "ARM %c (%s)  BUILD %s  RUN %u  PAGE 1/2  Y: FRAME TAIL PAGE  A: RUN AGAIN", g_arm,
             g_arm == 'B' ? "CACHE LEVERS ON" : "AS SHIPPED", RE4DC_BENCH_ID, g_run);
    fb_center(fb, y, 1, 2, kYellow, line); y += 18;
    fb_text(fb, 6, y, 1, 2, kCyan, "ROW              FPS CPU/T  GPU  WORK WAITG VBLNK  PACE ENEMY LEON  FX ALIVE FXLIVE HITS RIGID  RD/S"); y += 16;
    for (int k = 0; k < kScenes; ++k) {
        const Scene& s = g_scene[k];
        if (!s.defined) continue;
        if (!s.windows) { snprintf(line, sizeof(line), "%2d %-14s NOT MEASURED", k + 1, s.name); fb_text(fb, 6, y, 1, 2, kRed, line); y += 15; continue; }
        snprintf(line, sizeof(line), "%2d %-14s%5s %5s %4s %5s %5s %5s %5s %5s %4s %4s %5s %3u/%-3u %4u %2u/%-2uK %5s",
                 k + 1, s.name, d1(fps10(s), a), d1(cpu10(s), b), d1(gpu10(s), c), d1(ms10(tl_avg(s, T_WORK)), d),
                 d1(ms10(tl_avg(s, T_BLK)), e), d1(ms10(tl_avg(s, T_ROUND)), g), d1(ms10(tl_avg(s, T_PACE)), h),
                 d1(em10(s), i2), d1(pl10(s), j), d1(fx10(s), k2), d1(alive10(s), a), cen_avg(s.esp_sum, s.cen_n),
                 s.esp_max, s.hits1 - s.hits0, cen_avg(s.rg_parts_sum, s.cen_n),
                 (cen_avg(s.rg_verts_sum, s.cen_n) + 500) / 1000, d1(reads_ps10(s), b));
        fb_text(fb, 6, y, 1, 2, kWhite, line); y += 15;
    }
    y += 6;
    const char* notes[] = {
        "FPS: SHOWN PICTURES PER SECOND.  CPU/T: GAME CPU MS PER TICK.  GPU: PVR RENDER MS.  ALL MS PER DRAWN PICTURE:",
        "WORK: CPU WORK  WAITG: CPU WAITING ON THE GRAPHICS CHIP  VBLNK: SPIN TO VBLANK  PACE: SPIN OVER FURTHER VBLANKS",
        "ENEMY / LEON / FX: LOGIC MS PER TICK.  FXLIVE: LIVE EFFECTS AVG/MAX.  HITS: SHOTS THAT HIT THE TANK GANADO IN THE ROW",
        "RIGID: RIGID PARTS / K VERTICES DRAWN PER FRAME.  RD/S: DISC READS PER SECOND.  PHOTOGRAPH BOTH PAGES, BOTH ARMS."};
    for (const char* n : notes) { fb_text(fb, 6, y, 1, 2, kGrey, n); y += 14; }
}

void draw_results(const Fb& fb) {
    if (RE4DC_TAIL_METER && g_page) { draw_results_tail(fb); return; }
    if (RE4DC_BENCH_CENSUS) { draw_results_census(fb); return; }
    if (RE4DC_BENCH_CAPCMP) { draw_results_capcmp(fb, g_page); return; }
    char a[12], b[12], c[12], d[12], e[12], line[96], code[256];
    const int rs = kTight ? 2 : 3, rh = kTight ? 20 : 28;
    fb_fill(fb, 0, 0, fb.w, fb.h, 0x000000);
    int y = 30;
    fb_fill(fb, 30, y - 4, 580, 30, 0x900000);
    fb_center(fb, y, 2, 3, kWhite, RE4DC_BENCH_NAME " - NOT THE GAME"); y += 34;
    fb_center(fb, y, 2, 3, kYellow, "RE4 DREAMCAST BENCHMARK RESULTS"); y += 30;
    snprintf(line, sizeof(line), "BUILD %s   RUN %u", RE4DC_BENCH_ID, g_run);
    fb_center(fb, y, 2, 2, kGrey, line); y += 26;
    fb_text(fb, 36, y, 2, 2, kCyan, "SCENE         FPS MIN1S   CPU   GPU SPD%"); y += 22;
    for (int k = 0; k < kScenes; ++k) {
        const Scene& s = g_scene[k];
        if (!s.windows) { snprintf(line, sizeof(line), "%d %-10s  NOT MEASURED", k + 1, s.name); fb_text(fb, 36, y, 2, rs, kRed, line); y += rh; continue; }
        snprintf(line, sizeof(line), "%d %-10s%5s %5s %5s %5s %4u", k + 1, s.name, d1(fps10(s), a), d1(s.min_fps10, b),
                 d1(cpu10(s), c), d1(gpu10(s), d), speed_pct(s));
        fb_text(fb, 36, y, 2, rs, kWhite, line); y += rh;
    }
    y += 4;
    fb_text(fb, 36, y, 2, 2, kCyan, "SCENE        READS/S WAIT MS/S KOS MIN KB"); y += 22;
    for (int k = 0; k < kScenes; ++k) {
        const Scene& s = g_scene[k];
        snprintf(line, sizeof(line), "%d %-10s %7s %9u %8u", k + 1, s.name, d1(reads_ps10(s), e), wait_ms(s), kos_kb(s));
        fb_text(fb, 36, y, 2, rs, kWhite, line); y += rh;
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
    if (!kTight) {
        fb_text(fb, 36, y, 2, 2, kWhite, "PHOTOGRAPH THIS SCREEN. POST IT WITH YOUR"); y += 20;
        fb_text(fb, 36, y, 2, 2, kWhite, "CONSOLE REGION AND GDEMU / ODE / BURNED DISC."); y += 26;
    }
    fb_text(fb, 36, y, 2, 3, kCyan, RE4DC_TAIL_METER ? "Y: FRAME TAIL PAGE  A: RUN AGAIN" : "PRESS A TO RUN AGAIN");
}

#if RE4DC_HOUSE_ARENA27 && RE4DC_HOUSE_ARENA27_COUNTS
void arena_geometry_values(const Re4dcHouseArena27Geometry& o, unsigned v[kGeometryMetrics]) {
    v[0]=o.transformed_positions; v[1]=o.transformed_cache; v[2]=o.transformed_clip;
    v[3]=o.emitted_corners; v[4]=o.emitted_triangles; v[5]=o.fallback; v[6]=o.aborts;
}
void arena_geometry_sample(unsigned scene, const char* phase, unsigned slot, const Re4dcHouseArena27Geometry& o) {
    re4dc_log("arena27: geo_sample run=%u scene=%u phase=%s slot=%u pass=%u seq=%u ui=%u frame=%u camera=%08x xform=%u corners=%u tris=%u valid=%u result=%d\n",
              g_run,scene,phase,slot,o.pass,o.sequence,o.ui_frame,o.room_frame,o.camera_hash,
              o.transformed_positions,o.emitted_corners,o.emitted_triangles,o.valid,o.result);
}
void log_arena_geometry(unsigned scene, const Scene& s) {
    static const char* const names[kGeometryMetrics]={"transformed_positions","transformed_cache","transformed_clip",
                                                     "emitted_corners","emitted_triangles","fallback","aborts"};
    for(unsigned pass=0;pass<3;++pass) {
        const ArenaGeometry& g=s.geometry[pass];
        re4dc_log("arena27: geo_pass run=%u scene=%u pass=%u n=%u first=%u last=%u ui_first=%u ui_last=%u invalid=%u sequence_bad=%u identity_bad=%u mesh_crc=%08x mesh_bytes=%u camera=%08x\n",
                  g_run,scene,pass,g.n,g.first_room,g.last_room,g.first_ui,g.last_ui,g.invalid,g.sequence_bad,g.identity_bad,
                  g.mesh_crc,g.mesh_bytes,g.camera_hash);
        if(g.have_baseline)arena_geometry_sample(scene,"baseline",0,g.baseline);
        for(unsigned slot=0;slot<4;++slot)if(g.sample_mask&(1U<<slot))arena_geometry_sample(scene,"measured",slot,g.sample[slot]);
        if(!g.n)continue; // absent pass stays absent; a completed zero-output pass has n > 0
        for(unsigned metric=0;metric<kGeometryMetrics;++metric)
            re4dc_log("arena27: geo_metric run=%u scene=%u pass=%u name=%s sum=%llu min=%u max=%u\n",
                      g_run,scene,pass,names[metric],g.sum[metric],g.min[metric],g.max[metric]);
    }
}
#endif

void log_results() {
    char code[384];
    make_code(code, sizeof(code));
    for (int k = 0; k < kScenes; ++k) {
        const Scene& s = g_scene[k];
#if RE4DC_HOUSE_ARENA27 && RE4DC_HOUSE_ARENA27_COUNTS
        log_arena_geometry(k+1,s);
#endif
        re4dc_log("bench: result run %u scene %d %s windows=%u drawn=%u ticks=%u vblanks=%u fps10=%u min1s10=%u cpu10=%u "
                  "gpu10=%u speed=%u reads=%u reads_ps10=%u wait_ms=%u kos_min=%u end_frame=%u\n",
                  g_run, k + 1, s.name, s.windows, s.drawn, s.ticks, s.vblanks, fps10(s), s.min_fps10, cpu10(s), gpu10(s),
                  speed_pct(s), s.reads, reads_ps10(s), wait_ms(s), s.kos_min, s.end_frame);
#if RE4DC_HOUSE_ARENA27
        re4dc_log("arena27: result run=%u scene=%d variant=%s begin=%u end=%u end_frame=%u cpu_n=%u cpu_sum_us=%llu gpu_n=%u gpu_sum_ns=%llu\n",
                  g_run, k + 1, kArenaNames[k], s.begin, s.end, s.end_frame, s.cpu_n, s.cpu_us_sum, s.rnd_n, s.rnd_sum_ns);
#endif
        if (RE4DC_BENCH_CENSUS)
            re4dc_log("bench: census arm %c run %u row %d %s esp_avg=%u esp_max=%u hits=%u rigid_parts=%u rigid_verts=%u n=%u\n",
                      g_arm, g_run, k + 1, s.name, cen_avg(s.esp_sum, s.cen_n), s.esp_max, s.hits1 - s.hits0,
                      cen_avg(s.rg_parts_sum, s.cen_n), cen_avg(s.rg_verts_sum, s.cen_n), s.cen_n);
        re4dc_log("bench: result2 run %u scene %d %s mspic10=%u skipped=%u alive10=%u alive_min=%u alive_max=%u alive_n=%u "
                  "cpu_max_us=%u secs=%u \n", g_run, k + 1, s.name, mspic10(s), skipped(s), alive10(s),
                  s.alive_n ? s.alive_min : 0, s.alive_max, s.alive_n, s.cpu_max_us, s.n_sec);
        re4dc_log("bench: ta run %u scene %d scenes=%u op_b=%u opm_b=%u tr_b=%u trm_b=%u pt_b=%u (bytes per presented frame)\n",
                  g_run, k + 1, s.ta_scenes, s.ta_scenes ? (unsigned) (s.ta_words[0] * 4 / s.ta_scenes) : 0,
                  s.ta_scenes ? (unsigned) (s.ta_words[1] * 4 / s.ta_scenes) : 0, s.ta_scenes ? (unsigned) (s.ta_words[2] * 4 / s.ta_scenes) : 0,
                  s.ta_scenes ? (unsigned) (s.ta_words[3] * 4 / s.ta_scenes) : 0, s.ta_scenes ? (unsigned) (s.ta_words[4] * 4 / s.ta_scenes) : 0);
        // every tick log phase, us per tick (lines of at most ~6 phases: re4dc_log truncates at 256 bytes)
        char ph[200];
        int len = 0;
        for (int i = 0; i < 24 && g_ph_name[i]; ++i) {
            len += snprintf(ph + len, sizeof(ph) - len, " %s=%u", g_ph_name[i], s.ph_n[i] ? (unsigned) (s.ph_sum[i] / s.ph_n[i]) : 0);
            if (len > 150 || i == 23 || !g_ph_name[i + 1]) { re4dc_log("bench: phases run %u scene %d%s\n", g_run, k + 1, ph); len = 0; ph[0] = 0; }
        }
        if (RE4DC_TAIL_METER) {
            static const char* const kTName[kTN] = {"pic", "work", "blk", "round", "pace", "ta", "rnd", "queue", "vb", "iter"};
            char tl[220];
            int tn = snprintf(tl, sizeof(tl), "bench: tail run %u scene %d pics=%u rnd_n=%u", g_run, k + 1, s.tl_n, s.tl_rnd_n);
            for (int c = 0; c < kTN && tn < (int) sizeof(tl); ++c)
                tn += snprintf(tl + tn, sizeof(tl) - tn, " %s=%llu/%u", kTName[c],
                               (c == T_RND || c == T_QUEUE ? (s.tl_rnd_n ? s.tl_sum[c] / s.tl_rnd_n : 0) : (s.tl_n ? s.tl_sum[c] / s.tl_n : 0)),
                               s.tl_max[c]);
            re4dc_log("%s\n", tl);
        }
    }
    re4dc_log("bench: code %s build %s\n", code, RE4DC_BENCH_ID);
}
}  // namespace

extern "C" {

// ---------------------------------------------------------------- warp rig (dbgwarp_bridge.cpp)
#if RE4DC_HOUSE_ARENA27 && RE4DC_HOUSE_ARENA27_COUNTS
// Draw observes the frame already latched by dbgwarp; never relabel an older picture at the next tick.
unsigned re4dc_house_arena27_room_frame(void) { return g_room_frame; }
void re4dc_house_arena27_geometry(const Re4dcHouseArena27Geometry* observation) {
    if(!observation)return;
    const auto& o=*observation;
    Scene& s=g_scene[g_cur];
    if(!s.defined || s.done || o.pass>=3)return;
    ArenaGeometry& g=s.geometry[o.pass];
    if(o.room_frame<s.begin) { g.baseline=o;g.have_baseline=true;return; }
    if(o.room_frame>=s.end)return;
    if(g.n && (o.sequence<=g.last_sequence || o.ui_frame<=g.last_ui || o.room_frame<g.last_room)) {
        ++g.sequence_bad;return;
    }
    if(!g.n) {
        g.first_room=o.room_frame;g.first_ui=o.ui_frame;g.mesh_crc=o.mesh_crc;g.mesh_bytes=o.mesh_bytes;g.camera_hash=o.camera_hash;
    } else if(o.mesh_crc!=g.mesh_crc || o.mesh_bytes!=g.mesh_bytes || o.camera_hash!=g.camera_hash)++g.identity_bad;
    if(o.schema!=1 || !o.valid || o.result<0 || o.fallback || o.aborts)++g.invalid;
    unsigned v[kGeometryMetrics];arena_geometry_values(o,v);
    for(unsigned i=0;i<kGeometryMetrics;++i) {
        g.sum[i]+=v[i];if(!g.n || v[i]<g.min[i])g.min[i]=v[i];if(v[i]>g.max[i])g.max[i]=v[i];
    }
    g.last_room=o.room_frame;g.last_ui=o.ui_frame;g.last_sequence=o.sequence;++g.n;
    unsigned slot=0;
    if(o.room_frame>=s.begin+120)slot=2;else if(o.room_frame>=s.begin+60)slot=1;
    if(!(g.sample_mask&(1U<<slot))){g.sample[slot]=o;g.sample_mask|=1U<<slot;}
    g.sample[3]=o;g.sample_mask|=1U<<3; // last completed observation, not a fabricated end-frame sample
}
#endif
// A `bench <no> <begin> <end> <name>` line of the current fixture: the measured room frames of scene no (1-based).
void re4dc_bench_scene_def(int no, unsigned begin, unsigned end, const char* name)
{
    if (no < 1 || no > kScenes) return;
#if RE4DC_HOUSE_ARENA27
    if (no != g_file + 1 || begin != RE4DC_HOUSE_ARENA27_BEGIN || end != RE4DC_HOUSE_ARENA27_END) {
        re4dc_log("arena27: INVALID fixture scene=%d selected=%d begin=%u end=%u\n", no, g_file + 1, begin, end);
        return;
    }
    re4dc_log("arena27: armed run=%u scene=%d variant=%s begin=%u end=%u build=%s schema=2 counts=%u\n",
              g_run, no, kArenaNames[no - 1], begin, end, RE4DC_BENCH_ID, unsigned(RE4DC_HOUSE_ARENA27_COUNTS));
#endif
    Scene& s = g_scene[no - 1];
    memset(&s, 0, sizeof(s));
    strncpy(s.name, name ? name : "-", sizeof(s.name) - 1);
    s.begin = begin; s.end = end; s.defined = true;
    s.min_fps10 = ~0u; s.kos_min = ~0u; s.alive_min = ~0u;
    s.file = g_file;
    if (RE4DC_BENCH_CENSUS && !g_file_first) {
        re4dc_log("bench: row %d %s (file %d) frames %u..%u\n", no, s.name, g_file + 1, begin, end);
        return;
    }
    g_file_first = false;
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
    if (room_frame == s.begin) {
        s.measuring = true;
        re4dc_log("bench: scene %d begin room frame %u\n", g_cur + 1, room_frame);
    }
    if (s.measuring && room_frame < s.end) {
        const unsigned a = g_alive_now < 0 ? 0u : (unsigned) g_alive_now;
        s.alive_sum += a; ++s.alive_n;
        if (a < s.alive_min) s.alive_min = a;
        if (a > s.alive_max) s.alive_max = a;
        if ((room_frame - s.begin) % 30 == 0 && s.n_sec < sizeof(s.alive_sec)) {
            s.alive_sec[s.n_sec++] = (unsigned char) (a > 255 ? 255 : a);
            re4dc_log("bench: alive scene %d sec %u alive %u room frame %u\n", g_cur + 1, s.n_sec, a, room_frame);
        }
    }
    if (room_frame >= s.end) {
        s.measuring = false;
        s.done = true;
        s.end_frame = room_frame;
        re4dc_log("bench: scene %d end room frame %u windows=%u fps10=%u min1s10=%u cpu10=%u gpu10=%u kos_min=%u\n",
                  g_cur + 1, room_frame, s.windows, fps10(s), s.windows ? s.min_fps10 : 0, cpu10(s), gpu10(s), s.kos_min);
        if (RE4DC_BENCH_CENSUS)
            re4dc_log("bench: census row %d esp_avg=%u esp_max=%u hits=%u rigid_parts=%u reads_ps10=%u alive10=%u\n", g_cur + 1,
                      cen_avg(s.esp_sum, s.cen_n), s.esp_max, s.hits1 - s.hits0, cen_avg(s.rg_parts_sum, s.cen_n),
                      reads_ps10(s), alive10(s));
        if (RE4DC_BENCH_CENSUS && g_cur + 1 < kScenes && g_scene[g_cur + 1].defined && !g_scene[g_cur + 1].done &&
            g_scene[g_cur + 1].file == s.file && g_scene[g_cur + 1].begin > room_frame) {
            ++g_cur;   // the file's next row, same room, no reset
            g_prev_include = g_last_include = false;
            re4dc_log("bench: row %d %s next (frames %u..%u)\n", g_cur + 1, g_scene[g_cur].name, g_scene[g_cur].begin,
                      g_scene[g_cur].end);
            return 0;
        }
        return 1;
    }
    return 0;
}

// After a scene ended: the fixture of the next scene, or nullptr after the last one (then the results screen).
const char* re4dc_bench_next_scene(void)
{
    if (g_only >= 0) return nullptr;
    if (RE4DC_BENCH_CENSUS) return g_file + 1 < kFiles ? kScenePath[g_file + 1] : nullptr;
#if RE4DC_HOUSE_ARENA27
    if (g_cur + 1 < kScenes) g_file = g_cur + 1;   // select data before the next reset/room load
#endif
    return g_cur + 1 < kScenes ? kScenePath[g_cur + 1] : nullptr;
}
// The warp rig, before it parses a fixture: which file it is (BENCH_CENSUS rows).
void re4dc_bench_fixture_begin(const char* path)
{
    for (int i = 0; i < 16; ++i)
        if (path && !strcmp(path, kScenePath[i])) g_file = i;
    g_file_first = true;
}
// BENCH_CENSUS, each tick of the room before re4dc_bench_tick: live effects, hits on the tank target so far, rigid parts
// and vertices that reached the draw in the last frame.
void re4dc_bench_census(unsigned esp_live, unsigned hits, unsigned rg_parts, unsigned rg_verts)
{
    Scene& s = g_scene[g_cur];
    if (!s.defined || !s.measuring) return;
    if (!s.cen_n) s.hits0 = hits;
    s.hits1 = hits;
    ++s.cen_n;
    s.esp_sum += esp_live; s.rg_parts_sum += rg_parts; s.rg_verts_sum += rg_verts;
    if (esp_live > s.esp_max) s.esp_max = esp_live;
}
char re4dc_bench_arm(void) { return g_arm; }
// The first scene's fixture (the warp rig's first load): scene 1, or the start screen's single scene.
const char* re4dc_bench_first_scene(void) {
#if RE4DC_HOUSE_ARENA27
    g_file = g_only >= 0 ? g_only : 0;   // first fixture, before room data are opened
#endif
    return kScenePath[g_only >= 0 ? g_only : 0];
}
#if RE4DC_HOUSE_ARENA27
// Test-only data selector: 0 original, 1 simplifiedR4, 2 baked. Valid before room entry.
int re4dc_house_arena27_variant(void) { return g_file; }
#endif
int re4dc_bench_scene_no(void) { return g_cur + 1; }
// The warp rig, each game tick of the scene's room before re4dc_bench_tick: Ganados alive (SceCountEmAlive(0x10, 0x20)).
void re4dc_bench_alive(int n) { g_alive_now = n; }

// Results screen (the warp rig's poll, the frame loop stopped there): returns when A was pressed and released; the
// caller then runs scene 1 again. Draws into the displayed framebuffer, again whenever the display flips.
const char* re4dc_bench_results(void)
{
    log_results();
    re4dc_log("bench: results screen fb=%08lx ctrl=%08lx\n", (unsigned long) *(volatile uint32_t*) 0xA05F8050,
              (unsigned long) *(volatile uint32_t*) 0xA05F8044);
    uint32_t last_sof = ~0u;
    bool up = false, down = false;   // A must be up first (a held A does not restart), then pressed and released
    bool ydown = false;              // Y pressed and released: the next results page (CAP_COMPARE, more than 8 scenes)
    g_page = 0;
    for (;;) {
        const uint32_t sof = *(volatile uint32_t*) 0xA05F8050;
        if (sof != last_sof) { last_sof = sof; draw_results(fb_displayed()); }
        const bool yb = (pad_buttons() & CONT_Y) != 0;
        if (yb) ydown = true;
        else if (ydown) {
            ydown = false;
            if ((RE4DC_BENCH_CAPCMP && kScenes > 8) || RE4DC_TAIL_METER) { g_page ^= 1; draw_results(fb_displayed()); }
        }
        const bool a = (pad_buttons() & CONT_A) != 0;
        if (!a) { if (down) break; up = true; }
        else if (up) down = true;
        ++g_results_ticks;
        spin_us(30000);
    }
    ++g_run;
    re4dc_log("bench: A pressed: run %u\n", g_run);
    g_cur = 0;
#if RE4DC_HOUSE_ARENA27
    g_file = g_only >= 0 ? g_only : 0;
#endif
    if (RE4DC_BENCH_CENSUS) for (int k = 0; k < kScenes; ++k) g_scene[k].defined = false;
    return kScenePath[g_only >= 0 ? g_only : 0];
}

// ---------------------------------------------------------------- measurement hooks
// pace.cpp vmu_window, each one-second window close: drawn frames, game ticks, vblanks, PVR render time of the renders
// that completed in the window. A window counts when the scene measured at its start and at its end.
void re4dc_bench_window(unsigned drawn, unsigned ticks, unsigned vblanks, unsigned long long rnd_sum_ns, unsigned rnd_n)
{
    Scene& s = g_scene[g_cur];
    const bool now = s.defined && s.measuring;
    const bool include = now && g_prev_include;
    g_prev_include = now;
    g_last_include = include;
    unsigned ta_d[6] = {};
    if (re4dc_ta_count_ptr) {
        const unsigned* tc = re4dc_ta_count_ptr();
        for (int l = 0; l < 6; ++l) { ta_d[l] = tc[l] - g_ta_prev[l]; g_ta_prev[l] = tc[l]; }
    }
    if (!include || !vblanks) return;
#if RE4DC_HOUSE_ARENA27
    // The immediately following PACE vmu line belongs to this accepted whole window.
    re4dc_log("arena27: window run=%u scene=%d frame=%u drawn=%u ticks=%u vblanks=%u gpu_n=%u\n",
              g_run, g_cur + 1, g_room_frame, drawn, ticks, vblanks, rnd_n);
#endif
    ++s.windows;
    for (int l = 0; l < 5; ++l) s.ta_words[l] += ta_d[l];
    s.ta_scenes += ta_d[5];
    s.drawn += drawn; s.ticks += ticks; s.vblanks += vblanks;
    s.rnd_sum_ns += rnd_sum_ns; s.rnd_n += rnd_n;
    const unsigned f10 = (unsigned) ((unsigned long long) drawn * 59940ULL / 100 / vblanks);
    if (f10 < s.min_fps10) s.min_fps10 = f10;
    // CPU: a new tick log window, wholly inside the range (GAME_TICK_LOG ticks after its begin)
    const char* nm[32];
    unsigned avg[32], mx[32], seq = 0;
    const int n = re4dc_tick_log_snapshot(nm, avg, mx, 32, &seq);
    if (n > 0 && seq != g_tick_seq) {
        g_tick_seq = seq;
        if (g_room_frame >= s.begin + 2 * 60)
            for (int i = 0; i < n; ++i) {
                if (!nm[i]) continue;
                if (!strcmp(nm[i], "cpu")) {
                    s.cpu_us_sum += avg[i]; ++s.cpu_n;
                    if (mx[i] > s.cpu_max_us) s.cpu_max_us = mx[i];
                }
                // every phase by marker name (CAP_COMPARE results: logic split, effects)
                int j = 0;
                while (j < 24 && g_ph_name[j] && strcmp(g_ph_name[j], nm[i])) ++j;
                if (j == 24) continue;
                if (!g_ph_name[j]) g_ph_name[j] = nm[i];
                s.ph_sum[j] += avg[i]; ++s.ph_n[j];
            }
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

#if RE4DC_TAIL_METER
// ---------------------------------------------------------------- frame tail meter (TAIL_METER, lane frame-tail 10-19)
// Question: of a drawn picture's time, how much is CPU work, CPU blocked on the graphics chip, spin to the next vblank,
// and spin over further vblanks (the 30 Hz pacing clock), and is the PVR still rendering when the CPU is done?
// One "picture" = the iterations from after the previous drawn one up to and including the next drawn one (a skipped
// catch-up tick belongs to the picture that follows it). Hooks:
//   re4dc_tail_begin   pace.cpp re4dc_pace_begin (top of each iteration): closes the previous iteration
//   re4dc_tail_spin    main.cpp's two vblank waits (door_probe.h RE4DC_DOORSPIN) and pace_end's anchor wait
//   re4dc_tail_vb      main.cpp postVSyncCallback (every vblank, interrupt context)
//   re4dc_tail_gpu     native_ui.cpp stream_open / stream_close from the scene finish on (RE4DC_TAIL_GPU_SCOPE)
//   re4dc_tail_pvr     pace.cpp __wrap_pvr_sync_stats (interrupts off): TA done, render start, render done
// The per-picture log line and the bookkeeping run after the iteration's end stamp and before the next start stamp,
// so the meter's own time is in no column (the picture period comes from the vblank count).
namespace {
constexpr unsigned kVbUs = 16683;
volatile bool tl_in_spin, tl_vb_seen;
volatile unsigned long long tl_vb_first;            // first vblank inside the current spin (ns)
unsigned long long tl_spin_t0, tl_blk_t0;
int tl_blk_depth;
// current iteration
bool tl_open, tl_skip;
unsigned long long tl_t0, tl_last_spin_t0, it_spin, it_round, it_pace, it_blk;
// current picture
unsigned long long f_work, f_round, f_pace, f_blk;
unsigned f_iters, f_vb0, f_seq = 1;
bool f_vb0_set;
// PVR events (interrupt side)
volatile unsigned long long g_ta_t, g_rs_t, g_rs_queue, g_done_rnd, g_done_queue;
volatile unsigned g_ta_tag, g_rs_tag, g_done_tag;
volatile bool g_drawn_iter;                          // TA done stamps only count inside a drawn iteration
unsigned tl_counted_tag;                             // the last render counted (each render once)
}  // namespace

void re4dc_tail_vb(void)
{
    if (tl_in_spin && !tl_vb_seen) { tl_vb_first = timer_ns_gettime64(); tl_vb_seen = true; }
}

void re4dc_tail_spin(int end)
{
    if (!tl_open) return;
    if (!end) {
        const int o = irq_disable();
        tl_spin_t0 = timer_ns_gettime64();
        tl_vb_seen = false;
        tl_in_spin = true;
        irq_restore(o);
        tl_last_spin_t0 = tl_spin_t0;
        return;
    }
    const int o = irq_disable();
    const unsigned long long t = timer_ns_gettime64();
    const bool seen = tl_vb_seen;
    const unsigned long long vb = tl_vb_first;
    tl_in_spin = false;
    irq_restore(o);
    it_spin += t - tl_spin_t0;
    if (seen && vb >= tl_spin_t0 && vb <= t) { it_round += vb - tl_spin_t0; it_pace += t - vb; }
    else it_round += t - tl_spin_t0;
}

void re4dc_tail_gpu(int end)
{
    if (!end) { if (tl_blk_depth++ == 0) tl_blk_t0 = timer_ns_gettime64(); return; }
    if (tl_blk_depth > 0 && --tl_blk_depth == 0) it_blk += timer_ns_gettime64() - tl_blk_t0;
}

void re4dc_tail_pvr(int ev, unsigned long long t)   // interrupts off
{
    if (ev == 1) { if (g_drawn_iter) { g_ta_t = t; g_ta_tag = f_seq; } }
    else if (ev == 2) { g_rs_t = t; g_rs_tag = g_ta_tag; g_rs_queue = g_ta_t && t > g_ta_t ? t - g_ta_t : 0; }
    else if (ev == 3) {
        g_done_rnd = g_rs_t && t > g_rs_t ? t - g_rs_t : 0; g_done_queue = g_rs_queue; g_done_tag = g_rs_tag;
    }
}

namespace {
inline unsigned us_of(unsigned long long ns) { return (unsigned) (ns / 1000); }
void tl_put(Scene& s, int c, unsigned v) { s.tl_sum[c] += v; if (v > s.tl_max[c]) s.tl_max[c] = v; }
}  // namespace

void re4dc_tail_begin(int skip)
{
    const unsigned long long now = timer_ns_gettime64();
    const unsigned vbnow = re4dc_vi_retrace_count();
    if (!f_vb0_set) { f_vb0 = vbnow; f_vb0_set = true; }
    if (tl_open) {
        const unsigned long long dur = now - tl_t0;
        const unsigned long long spin = it_spin < dur ? it_spin : dur;
        f_work += dur - spin;
        f_round += it_round; f_pace += it_pace; f_blk += it_blk;
        ++f_iters;
        if (!tl_skip) {   // the drawn iteration closes the picture
            unsigned long long ta_t, done_rnd, done_queue;
            unsigned ta_tag, done_tag;
            {
                const int o = irq_disable();
                ta_t = g_ta_t; ta_tag = g_ta_tag; done_rnd = g_done_rnd; done_queue = g_done_queue; done_tag = g_done_tag;
                g_drawn_iter = false;
                irq_restore(o);
            }
            Scene& s = g_scene[g_cur];
            const unsigned vb = vbnow - f_vb0;
            const bool measured = s.defined && s.measuring
#if RE4DC_HOUSE_ARENA27
                                  && g_room_frame > s.begin   // exclude the picture already open at warmup end
#endif
                                  ;
            const unsigned ta = ta_tag == f_seq && ta_t > tl_t0 ? us_of(ta_t - tl_t0) : 0;
            // the newest finished render (this picture's or, pipelined, the previous one's), each render counted once
            const bool fresh = done_tag && done_tag != tl_counted_tag;
            if (fresh) tl_counted_tag = done_tag;
            if (measured && vb) {
                ++s.tl_n;
                tl_put(s, T_PIC, vb * kVbUs);
                tl_put(s, T_WORK, us_of(f_work));
                tl_put(s, T_BLK, us_of(f_blk));
                tl_put(s, T_ROUND, us_of(f_round));
                tl_put(s, T_PACE, us_of(f_pace));
                tl_put(s, T_TA, ta);
                tl_put(s, T_VB, vb);
                tl_put(s, T_ITER, f_iters);
                if (fresh) { tl_put(s, T_RND, us_of(done_rnd)); tl_put(s, T_QUEUE, us_of(done_queue)); ++s.tl_rnd_n; }
                re4dc_log("tail: sc=%d f=%u it=%u vb=%u work=%u blk=%u round=%u pace=%u ta=%u rnd=%u queue=%u lag=%u\n",
                          g_cur + 1, g_room_frame, f_iters, vb, us_of(f_work), us_of(f_blk), us_of(f_round), us_of(f_pace),
                          ta, fresh ? us_of(done_rnd) : 0, fresh ? us_of(done_queue) : 0, fresh ? f_seq - done_tag : 99u);
            }
            f_work = f_round = f_pace = f_blk = 0;
            f_iters = 0;
            f_vb0 = vbnow;
            ++f_seq;
        }
    }
    tl_open = true;
    tl_skip = skip != 0;
    it_spin = it_round = it_pace = it_blk = 0;
    tl_last_spin_t0 = 0;
    tl_blk_depth = 0;
    {
        const int o = irq_disable();
        g_drawn_iter = !tl_skip;
        irq_restore(o);
    }
    tl_t0 = timer_ns_gettime64();   // after the bookkeeping and the log line: the meter is in no column
}
#endif

// ---------------------------------------------------------------- banner (native_ui.cpp, every presented frame)
const char* re4dc_bench_banner(void) { return RE4DC_BENCH_NAME " - NOT THE GAME"; }

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

#if defined(RE4DC_BENCH_SCENARIO) && RE4DC_BENCH_SCENARIO
#if defined(RE4DC_LAKE_FIX_TOGGLE) && RE4DC_LAKE_FIX_TOGGLE
extern unsigned char re4dc_lake_fix;   // native_ui.cpp (effects30.mk LAKE_FIX_TOGGLE)
#endif
// BENCH_SCENARIO=1 (bench.mk; lane lake20 2026-10-20): a QA scenario disc. The start screen is a menu of start points
// (scene k = /cd/dc/warp.txt or bench<k>.txt, fixtures without a `bench` line, so a scene never ends: free play with
// the controller live); A switches the lake fixes (LAKE_FIX_TOGGLE) on / off before the start. Memory cards stay hidden.
static void scenario_menu(const Fb& fb)
{
    static const char* const kNames[16] = {"BOAT RIDE START (R10B PIER)", "DEL LAGO FIGHT START (R10B LAKE)",
                                           "NIGHT SHORE AFTER DEL LAGO (R11B, #43)", "DAM SIDE ROOM (R10D)",
                                           "THE DAM (R10C)"};
    int cur = 0;
    unsigned prev = ~0u, last = 0;
    bool redraw = true, fix = true;
#if defined(RE4DC_LAKE_FIX_TOGGLE) && RE4DC_LAKE_FIX_TOGGLE
    fix = re4dc_lake_fix != 0;
#endif
    for (;;) {
        if (redraw) {
            redraw = false;
            fb_fill(fb, 0, 0, 640, 480, 0x000000);
            fb_fill(fb, 30, 24, 580, 76, 0x900000);
            fb_center(fb, 30, 3, 4, kWhite, RE4DC_BENCH_NAME);
            fb_center(fb, 66, 3, 4, kWhite, "THIS IS NOT THE GAME");
            fb_text(fb, 40, 116, 2, 2, kYellow, "D-PAD UP / DOWN: START POINT");
            fb_text(fb, 40, 138, 2, 2, kYellow, "A: LAKE FIXES ON / OFF    START: GO");
            for (int k = 0; k < kScenes && k < 16; ++k) {
                char line[64];
                snprintf(line, sizeof(line), "%c %d  %s", k == cur ? '>' : ' ', k + 1, kNames[k] ? kNames[k] : "-");
                fb_text(fb, 40, 176 + 26 * k, 2, 2, k == cur ? kCyan : kWhite, line);
            }
            const int y = 176 + 26 * (kScenes < 16 ? kScenes : 16) + 16;
            fb_text(fb, 40, y, 2, 2, fix ? kGreen : kGrey, fix ? "LAKE FIXES: ON" : "LAKE FIXES: OFF (AS TEST 20)");
            fb_text(fb, 40, y + 24, 2, 2, kGrey, "NIGHT SHORE EFFECT LEVEL, RAIN 160, #43 PICTURES");
            fb_text(fb, 40, y + 52, 2, 2, kGrey, "NOTHING IS SAVED. TO CHANGE: POWER OFF AND ON.");
            char msg[48];
            snprintf(msg, sizeof(msg), "BUILD %s", RE4DC_BENCH_ID);
            fb_text(fb, 40, y + 80, 2, 2, kGrey, msg);
        }
#if defined(RE4DC_BENCH_SCENARIO_AUTO)
        // BENCH_SCENARIO_AUTO=<k><f> (check discs only): start scene k with the fixes f (0 / 1), no controller needed
        cur = RE4DC_BENCH_SCENARIO_AUTO / 10 - 1; fix = RE4DC_BENCH_SCENARIO_AUTO % 10 != 0;
        thd_sleep(1000);
        break;
#endif
        const unsigned btn = pad_buttons();
        const unsigned edge = btn & ~last;   // pressed this poll
        last = btn;
        if (prev == ~0u) { prev = 0; thd_sleep(20); continue; }   // ignore buttons held at boot
        if (edge & CONT_DPAD_UP) { cur = cur > 0 ? cur - 1 : kScenes - 1; redraw = true; }
        if (edge & CONT_DPAD_DOWN) { cur = cur + 1 < kScenes ? cur + 1 : 0; redraw = true; }
        if (edge & CONT_A) { fix = !fix; redraw = true; }
        if (edge & CONT_START) break;
        thd_sleep(20);
    }
#if defined(RE4DC_LAKE_FIX_TOGGLE) && RE4DC_LAKE_FIX_TOGGLE
    re4dc_lake_fix = fix ? 1 : 0;
#endif
    g_only = cur;
    fb_fill(fb, 0, 0, 640, 480, 0x000000);
    fb_center(fb, 200, 3, 4, kWhite, RE4DC_BENCH_NAME " - NOT THE GAME");
    fb_center(fb, 250, 2, 3, kCyan, kNames[cur] ? kNames[cur] : "STARTING");
    re4dc_log("bench: scenario start %d (%s) lake_fix=%d build %s\n", cur + 1, kScenePath[cur], fix ? 1 : 0, RE4DC_BENCH_ID);
}
#endif
extern "C" void __wrap_OSInit(void)
{
    g_hide_vmu = true;
    static bool done;
    __real_OSInit();
    if (done) return;
    done = true;
    vid_set_mode(DM_640x480, PM_RGB565);
    const Fb fb = fb_boot();
#if defined(RE4DC_BENCH_SCENARIO) && RE4DC_BENCH_SCENARIO
    scenario_menu(fb);
    return;
#endif
#if RE4DC_HOUSE_ARENA27 && RE4DC_HOUSE_ARENA27_AUTO
    g_only = RE4DC_HOUSE_ARENA27_AUTO - 1;
    g_file = g_only;
    g_masked = true;
    re4dc_log("arena27: auto scene=%d variant=%s build=%s\n", g_only + 1, kArenaNames[g_only], RE4DC_BENCH_ID);
    return;
#endif
#if RE4DC_HOUSE_ARENA27
    re4dc_log("arena27: menu ready build=%s auto=%d\n",RE4DC_BENCH_ID,RE4DC_HOUSE_ARENA27_AUTO);
#endif
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
            fb_center(fb, y, 3, 4, kWhite, RE4DC_BENCH_NAME); y += 36;
            fb_center(fb, y, 3, 4, kWhite, "THIS IS NOT THE GAME"); y += 50;
            fb_center(fb, y, 2, 3, kYellow, "RE4 DREAMCAST PORT - PERFORMANCE TEST"); y += 36;
#if !RE4DC_HOUSE_ARENA27
            const char* body_std[] = {"THIS DISC ONLY MEASURES PERFORMANCE.",
                                  "IT CANNOT BE PLAYED AND SAVES NOTHING.",
                                  "TO PLAY, USE THE CURRENT TEST RELEASE:",
                                  "GITHUB.COM/LAMB2K/RE4DC - RELEASES",
                                  "",
                                  kTight ? "IT RUNS FOUR SCRIPTED SCENES BY ITSELF" : "IT RUNS TWO SCRIPTED SCENES BY ITSELF",
                                  kTight ? "(ABOUT 6 MINUTES), THEN SHOWS RESULTS." : "(ABOUT 4 MINUTES), THEN SHOWS RESULTS.",
                                  "AFTER START DO NOT TOUCH THE CONTROLLER.",
                                  "PHOTOGRAPH THE RESULTS SCREEN."};
            // CAP_COMPARE: a shorter body, room for the scene menu (14 scenes)
            char run_line[64];
            snprintf(run_line, sizeof(run_line), "START RUNS ALL %d SCENES (ABOUT %d MIN),", kScenes, kScenes + 1);
            const char* body_cmp[] = {"THIS DISC ONLY MEASURES PERFORMANCE.", "IT CANNOT BE PLAYED AND SAVES NOTHING.", "",
                                      run_line, "THEN THE RESULTS (Y: NEXT PAGE).", "AFTER START DO NOT TOUCH THE CONTROLLER.",
                                      "PHOTOGRAPH EVERY RESULTS PAGE."};
#endif
#if RE4DC_HOUSE_ARENA27
            const char* body_arena[] = {"ONE LEON AND ONE COMPLETE HOUSE.", "A: ORIGINAL  B: REBUILT  C: SPARSE",
                                       "START RUNS A / B / C WITH SOFT RESETS.", "WARMUP AND LOADING ARE NOT MEASURED.",
                                       "AFTER START DO NOT TOUCH THE CONTROLLER.", "PHOTOGRAPH BOTH RESULTS PAGES.",
                                       "THIS DISC SAVES NOTHING."};
            const char* const* body = body_arena;
            const int nbody = 7;
#else
            const char* const* body = RE4DC_BENCH_CAPCMP ? body_cmp : body_std;
            const int nbody = RE4DC_BENCH_CAPCMP ? 7 : 9;
#endif
            if (kTight) {
                // the scene menu (a disc of more than two scenes)
                const char* menu[] = {"START: ALL SCENES IN ORDER", RE4DC_BENCH_MENU, RE4DC_BENCH_MENU2, RE4DC_BENCH_MENU3};
                const int my = RE4DC_BENCH_CAPCMP ? 370 : 414;
                for (int m = 0; m < 4; ++m)
                    if (menu[m][0]) fb_text(fb, 60, my + 20 * m, 2, 2, kYellow, menu[m]);
            }
            for (int bi = 0; bi < nbody; ++bi) { const char* s = body[bi]; fb_text(fb, 60, y, 2, 2, s[0] == 'G' ? kGreen : kWhite, s); y += 22; }
            y += 8;
            char msg[64];
            snprintf(msg, sizeof(msg), "BUILD %s", RE4DC_BENCH_ID);
            fb_text(fb, 60, y, 2, 2, kGrey, msg); y += 30;
            snprintf(msg, sizeof(msg), "PRESS START TO BEGIN (AUTO IN %u S)", el < kAuto ? kAuto - el : 0);
            fb_text(fb, 60, y, 2, 3, kCyan, msg);
            if (RE4DC_BENCH_CENSUS) {
                fb_fill(fb, 60, 452, 520, 22, 0x000000);
                snprintf(msg, sizeof(msg), "ARM %c - D-PAD LEFT: A (AS SHIPPED)  RIGHT: B", g_arm);
                fb_text(fb, 60, 452, 2, 2, g_arm == 'B' ? kGreen : kYellow, msg);
            }
        }
        const unsigned btn = pad_buttons();
        if (RE4DC_BENCH_CENSUS) {
            const char was = g_arm;
            if (btn & CONT_DPAD_LEFT) g_arm = 'A';
            if (btn & CONT_DPAD_RIGHT) g_arm = 'B';
            if (was != g_arm) shown = ~0u;   // redraw
        }
        if (btn & CONT_START) pressed = true;
        if (kTight && !pressed) {
            // X / Y / B: one scene alone (the stress disc's arm menu); released like START
            static unsigned held;
            // CAP_COMPARE: X / Y / A / B = scenes 1..4 (r101 cap 3 / 4 / 5 / 6), d-pad up / down / left / right = 5..8, and
            // the combos (held together, then released) UP + X / Y / A = 9..11 (r101 T1..T3), DOWN + X / Y / A = 12..14 (farm)
            const unsigned U = CONT_DPAD_UP, D = CONT_DPAD_DOWN;
            unsigned keys[16] = {CONT_X, CONT_Y, RE4DC_BENCH_CAPCMP ? CONT_A : CONT_B, RE4DC_BENCH_CAPCMP ? CONT_B : 0,
                                       U, D, CONT_DPAD_LEFT, CONT_DPAD_RIGHT,
                                       U | CONT_X, U | CONT_Y, U | CONT_A, D | CONT_X, D | CONT_Y, D | CONT_A, 0, 0};
            if (RE4DC_BENCH_CENSUS)   // census discs: X / Y / B pick a file; the d-pad picks the arm
                for (int k = 3; k < 16; ++k) keys[k] = 0;
            unsigned mask = 0;
            for (int k = 0; k < kScenes && k < 16; ++k) mask |= keys[k];
            const unsigned pick = btn & mask;
            if (pick) held |= pick;
            else if (held) {
                for (int k = 0; k < kScenes && k < 16; ++k)
                    if (keys[k] == held) { g_only = k; break; }
                if (g_only < 0)   // not a listed combo: the first single key of it
                    for (int k = 0; k < kScenes && k < 8; ++k)
                        if (held & keys[k]) { g_only = k; break; }
                pressed = true;
                break;
            }
        }
        if ((pressed && !(btn & CONT_START)) || el >= kAuto) break;   // START released, or timeout
        thd_sleep(20);
    }
    fb_fill(fb, 0, 0, 640, 480, 0x000000);
    fb_center(fb, 200, 3, 4, kWhite, RE4DC_BENCH_NAME " - NOT THE GAME");
    fb_center(fb, 250, 2, 3, kCyan, "STARTING - HANDS OFF THE CONTROLLER");
    g_masked = true;
    if (RE4DC_BENCH_CENSUS && re4dc_cache20_arm) re4dc_cache20_arm(g_arm == 'B');
    re4dc_log("bench: start (%s) build %s scene %s arm %c\n", pressed ? "START" : "auto", RE4DC_BENCH_ID,
              g_only >= 0 ? kScenePath[g_only] : "all", g_arm);
}

}  // extern "C"
