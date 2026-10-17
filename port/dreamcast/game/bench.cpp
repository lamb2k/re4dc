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

extern "C" {
void re4dc_log(const char* fmt, ...);
void re4dc_kos_heap_state(unsigned* free_chunks, unsigned* used, unsigned* break_room);  // platform/os.cpp
int re4dc_tick_log_snapshot(const char** name, unsigned* avg_us, unsigned* max_us, int max, unsigned* seq);  // tick_log.cpp
void __real_OSInit(void);
void* __real_maple_dev_status(maple_device_t* dev);
maple_device_t* __real_maple_enum_dev(int p, int u);
unsigned __real_re4dc_ui_frame(void);
}

namespace {
// ---------------------------------------------------------------- scenes
// RE4DC_BENCH_SCENES (default 2; STRESS_SADDLER's stress disc: 4 = full, g70, g50, full again): scene k > 1 is
// /cd/dc/bench<k>.txt. RE4DC_BENCH_NAME: the disc's name on the start / results screens and the banner.
#ifndef RE4DC_BENCH_SCENES
#define RE4DC_BENCH_SCENES 2
#endif
#ifndef RE4DC_BENCH_MENU
#define RE4DC_BENCH_MENU "X: SCENE 1 ONLY  Y: SCENE 2  B: SCENE 3"
#endif
#ifndef RE4DC_BENCH_NAME
#define RE4DC_BENCH_NAME "BENCHMARK DISC"
#endif
constexpr int kScenes = RE4DC_BENCH_SCENES;
static_assert(kScenes >= 2 && kScenes <= 4, "RE4DC_BENCH_SCENES 2..4");
constexpr bool kTight = kScenes > 2;   // more result rows: smaller rows, no photo note
const char* const kScenePath[4] = {"/cd/dc/warp.txt", "/cd/dc/bench2.txt", "/cd/dc/bench3.txt", "/cd/dc/bench4.txt"};
// The start screen's choice on a disc of more than two scenes (the Saddler stress disc: START all, X / Y / B one scene):
// -1 = every scene in order, k = scene k + 1 alone (then the results screen).
int g_only = -1;
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
Scene g_scene[kScenes];
int g_cur;                        // scene being run
unsigned g_run = 1;               // run number (A on the results screen starts the next)
unsigned g_room_frame;
bool g_prev_include, g_last_include;
unsigned g_tick_seq;

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
    char body[256], parts[224] = "";
    for (int k = 0; k < kScenes; ++k) {
        if (k) strncat(parts, " ", sizeof(parts) - strlen(parts) - 1);
        strncat(parts, part[k], sizeof(parts) - strlen(parts) - 1);
    }
    snprintf(body, sizeof(body), "%s %s", RE4DC_BENCH_ID, parts);
    unsigned ck = 0;
    for (const char* p = body; *p; ++p) ck = (ck * 31 + (unsigned char) *p) % 251;
    snprintf(out, size, "%s %02X", parts, ck);
}

void draw_results(const Fb& fb) {
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
    fb_text(fb, 36, y, 2, 3, kCyan, "PRESS A TO RUN AGAIN");
}

void log_results() {
    char code[256];
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
    if (no < 1 || no > kScenes) return;
    Scene& s = g_scene[no - 1];
    memset(&s, 0, sizeof(s));
    strncpy(s.name, name ? name : "-", sizeof(s.name) - 1);
    s.begin = begin; s.end = end; s.defined = true;
    s.min_fps10 = ~0u; s.kos_min = ~0u;
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
    if (g_only >= 0) return nullptr;
    return g_cur + 1 < kScenes ? kScenePath[g_cur + 1] : nullptr;
}
// The first scene's fixture (the warp rig's first load): scene 1, or the start screen's single scene.
const char* re4dc_bench_first_scene(void) { return kScenePath[g_only >= 0 ? g_only : 0]; }
int re4dc_bench_scene_no(void) { return g_cur + 1; }

// Results screen (the warp rig's poll, the frame loop stopped there): returns when A was pressed and released; the
// caller then runs scene 1 again. Draws into the displayed framebuffer, again whenever the display flips.
const char* re4dc_bench_results(void)
{
    log_results();
    re4dc_log("bench: results screen fb=%08lx ctrl=%08lx\n", (unsigned long) *(volatile uint32_t*) 0xA05F8050,
              (unsigned long) *(volatile uint32_t*) 0xA05F8044);
    uint32_t last_sof = ~0u;
    bool up = false, down = false;   // A must be up first (a held A does not restart), then pressed and released
    for (;;) {
        const uint32_t sof = *(volatile uint32_t*) 0xA05F8050;
        if (sof != last_sof) { last_sof = sof; draw_results(fb_displayed()); }
        const bool a = (pad_buttons() & CONT_A) != 0;
        if (!a) { if (down) break; up = true; }
        else if (up) down = true;
        ++g_results_ticks;
        spin_us(30000);
    }
    ++g_run;
    re4dc_log("bench: A pressed: run %u\n", g_run);
    g_cur = 0;
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

extern "C" void __wrap_OSInit(void)
{
    g_hide_vmu = true;
    static bool done;
    __real_OSInit();
    if (done) return;
    done = true;
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
            fb_center(fb, y, 3, 4, kWhite, RE4DC_BENCH_NAME); y += 36;
            fb_center(fb, y, 3, 4, kWhite, "THIS IS NOT THE GAME"); y += 50;
            fb_center(fb, y, 2, 3, kYellow, "RE4 DREAMCAST PORT - PERFORMANCE TEST"); y += 36;
            const char* body[] = {"THIS DISC ONLY MEASURES PERFORMANCE.",
                                  "IT CANNOT BE PLAYED AND SAVES NOTHING.",
                                  "TO PLAY, USE THE CURRENT TEST RELEASE:",
                                  "GITHUB.COM/LAMB2K/RE4DC - RELEASES",
                                  "",
                                  kTight ? "IT RUNS FOUR SCRIPTED SCENES BY ITSELF" : "IT RUNS TWO SCRIPTED SCENES BY ITSELF",
                                  kTight ? "(ABOUT 6 MINUTES), THEN SHOWS RESULTS." : "(ABOUT 4 MINUTES), THEN SHOWS RESULTS.",
                                  "AFTER START DO NOT TOUCH THE CONTROLLER.",
                                  "PHOTOGRAPH THE RESULTS SCREEN."};
            if (kTight) {
                // the scene menu (a disc of more than two scenes)
                const char* menu[] = {"START: ALL SCENES IN ORDER", RE4DC_BENCH_MENU};
                fb_text(fb, 60, 418, 2, 2, kYellow, menu[0]);
                fb_text(fb, 60, 440, 2, 2, kYellow, menu[1]);
            }
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
        if (kTight && !pressed) {
            // X / Y / B: one scene alone (the stress disc's arm menu); released like START
            static unsigned held;
            const unsigned pick = btn & (CONT_X | CONT_Y | CONT_B);
            if (pick) held = pick;
            else if (held) {
                g_only = (held & CONT_X) ? 0 : (held & CONT_Y) ? 1 : 2;
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
    re4dc_log("bench: start (%s) build %s scene %s\n", pressed ? "START" : "auto", RE4DC_BENCH_ID,
              g_only >= 0 ? kScenePath[g_only] : "all");
}

}  // extern "C"
