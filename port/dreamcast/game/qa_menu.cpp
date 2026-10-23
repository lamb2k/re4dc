// QA menu (QA_MENU=1 in qamenu.mk; the tester QA disc only, never a release image). Lane qa20, user 2026-10-20.
//
// One general QA disc: a teleporter (chapter -> place, each place a warp rig fixture that sets the story state), the
// main weapons in the case from a new game (QUICK_WEAPON_POC_KIT), and runtime toggles. Screens are drawn straight
// into a framebuffer with the 5x7 font of the benchmark disc (bench.cpp), so the menu needs no game resources:
//  - boot: the KOS framebuffer before pvr_init (__wrap_OSInit), as the benchmark start screen;
//  - in game: the displayed framebuffer while the frame loop is stopped in the warp rig's poll (dbgwarp_bridge.cpp
//    qa_poll), as the benchmark results screen. The poll opens it only in free play.
// Presets: /cd/dc/qa/menu.txt, lines `ch <chapter title>` and `p <fixture file> <S|B> <label>` (S = story state:
// the fixture sets progress flags and the room loads its own enemy list; B = bare room jump, enemies may be missing).
// The fixture is /cd/dc/qa/<file>. tools/d367/qa20/mkqa.py writes both.
#include <kos.h>
#include <dc/maple.h>
#include <dc/maple/controller.h>
#include <dc/video.h>
#include <arch/timer.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#if defined(RE4DC_WORLD_SCRATCH) && RE4DC_WORLD_SCRATCH
#include "world_scratch.h"
#endif

extern "C" {
void re4dc_log(const char* fmt, ...);
int re4dc_fixture_read(const char* path, char* buffer, unsigned size);
void __real_OSInit(void);
int re4dc_quality_speed(void);      // platform/quality.cpp: 0 off, 1 VMU, 2 screen, 3 both
void re4dc_speed_cycle(void);       // pace.cpp
// Diagnostics sources; weak: a build without the knob shows "N/A" for that row.
int re4dc_qa_speed(unsigned v[3]) __attribute__((weak));                                       // pace.cpp
int re4dc_tick_log_snapshot(const char** name, unsigned* avg_us, unsigned* max_us, int max, unsigned* seq)
    __attribute__((weak));                                                                     // tick_log.cpp
void re4dc_kos_heap_state(unsigned* free_chunks, unsigned* used, unsigned* break_room) __attribute__((weak));
void re4dc_vram_pages_census(unsigned* out) __attribute__((weak));                             // vram_pages.cpp
void re4dc_disc_meter_totals(unsigned* reads, unsigned long long* bytes, unsigned long long* block_us)
    __attribute__((weak));                                                                     // dvd_read_safe.cpp
extern unsigned long re4dc_fx_esp_live[32] __attribute__((weak));                            // esp.cpp (FX_SCAN)
extern volatile unsigned re4dc_qa_shore_far_mm __attribute__((weak));                      // native_static.cpp (LAKE_FAR)
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
// WORLD_METER (game30.mk): the world rows (0 = the game's own) and the VRAM failure rooms.
extern volatile unsigned re4dc_qa_wopq_mm, re4dc_qa_wxlu_mm, re4dc_qa_wshell;               // native_static.cpp
unsigned re4dc_vram_fail_rooms(unsigned* last_room, unsigned* last_n, unsigned* rooms, unsigned* counts, unsigned max);
void re4dc_ps2_pvs_set(unsigned on) __attribute__((weak));
void re4dc_ps2_pvs_state(unsigned out[4]) __attribute__((weak));
void re4dc_pvs23_receipt_state(unsigned out[5]) __attribute__((weak));
int re4dc_world_meter_window(unsigned out[11]);
int re4dc_world_meter_geometry_supported(void);
void re4dc_world_meter_resume(void);
int re4dc_view_dist_get(void) __attribute__((weak));                                         // option_rows.cpp
#endif
extern volatile unsigned long re4dc_log_head;                                                  // platform/mem.cpp
extern char re4dc_logbuf[0x10000];
}
#include "third_party/qrcodegen/qrcodegen.h"

namespace {
constexpr uint32_t kWhite = 0xFFFFFF, kYellow = 0xFFE040, kGrey = 0x909090, kCyan = 0x60E0FF, kRed = 0x900000,
                   kBlue = 0x102850, kGreen = 0x60FF60;

// ---------------------------------------------------------------- framebuffer text (bench.cpp, hwcal r21v)
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
        {'<', 0x02, 0x04, 0x08, 0x10, 0x08, 0x04, 0x02}, {'\'', 0x04, 0x04, 0x08, 0, 0, 0, 0},
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
Fb fb_boot() {   // KOS framebuffer before pvr_init (vid_set_mode 640x480 RGB565)
    Fb fb{};
    fb.base = (uint8_t*) vram_s; fb.w = 640; fb.h = 480; fb.bpp = 2; fb.stride = 1280; fb.rgb565 = true;
    return fb;
}
Fb fb_displayed() {  // the framebuffer the display reads now (FB_R_SOF1 / FB_R_CTRL), linear
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

// ---------------------------------------------------------------- input (port A, raw: the game's mapping is bypassed)
struct Pad { unsigned buttons; int l, r; };
Pad pad_read() {
    Pad p{0, 0, 0};
    maple_device_t* c = maple_enum_type(0, MAPLE_FUNC_CONTROLLER);
    cont_state_t* st = c ? (cont_state_t*) maple_dev_status(c) : nullptr;
    if (st) { p.buttons = st->buttons; p.l = st->ltrig; p.r = st->rtrig; }
    return p;
}
volatile unsigned g_menu_ticks;   // moves CRASH_SCREEN's hang watchdog while a menu waits (bench.cpp's method)
void spin_us(uint32_t us) {   // busy wait on the TMU: no scheduler dependence while the frame loop is stopped
    const uint64_t t0 = timer_us_gettime64();
    while (timer_us_gettime64() - t0 < us) {}
    g_menu_ticks = g_menu_ticks + 1;
}

// ---------------------------------------------------------------- presets
constexpr int kMaxP = 96, kMaxCh = 16;
struct Preset { char file[24]; char kind; char label[44]; unsigned char ch; };
Preset g_p[kMaxP];
char g_ch[kMaxCh][40];
int g_np, g_nch;
bool g_loaded;
char g_path[48];
const char* g_boot_path;
volatile unsigned g_flags;   // bit 0 Leon, bit 1 partner, bit 2 enemies invincible
volatile int g_in_room;

void load_presets() {
    if (g_loaded) return;
    g_loaded = true;
    static char text[8192];
    const int len = re4dc_fixture_read("/cd/dc/qa/menu.txt", text, sizeof(text) - 1);
    if (len <= 0) { re4dc_log("qa: no /cd/dc/qa/menu.txt\n"); return; }
    text[len] = 0;
    for (char* line = text; line && *line;) {
        char* next = strchr(line, '\n');
        if (next) *next++ = 0;
        char* cr = strchr(line, '\r');
        if (cr) *cr = 0;
        if (!strncmp(line, "ch ", 3) && g_nch < kMaxCh) {
            strncpy(g_ch[g_nch++], line + 3, sizeof(g_ch[0]) - 1);
        } else if (!strncmp(line, "p ", 2) && g_np < kMaxP && g_nch > 0) {
            Preset& p = g_p[g_np];
            char* f = line + 2;
            char* sp = strchr(f, ' ');
            if (sp && sp[1] && sp[2] == ' ') {
                *sp = 0;
                strncpy(p.file, f, sizeof(p.file) - 1);
                p.kind = sp[1];
                strncpy(p.label, sp + 3, sizeof(p.label) - 1);
                p.ch = (unsigned char) (g_nch - 1);
                ++g_np;
            }
        }
        line = next;
    }
    re4dc_log("qa: %d presets in %d chapters\n", g_np, g_nch);
}

#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
// ---------------------------------------------------------------- world rows (WORLD_METER; this boot only)
// Opaque world cut: GAME (the Options View distance) / 12.5 / 10 / 8 m. Translucent world far: GAME / FULL (the far before
// the View distance cut, 25 m) / 12.5 / 8 m. Far shell: GAME (drawn at View distance Short) / ON (any View distance) / OFF.
const unsigned kOpq[] = {0u, 12500u, 10000u, 8000u}, kXlu[] = {0u, 1u, 12500u, 8000u};
template <unsigned N> unsigned next_of(const unsigned (&t)[N], unsigned v) {
    for (unsigned i = 0; i < N; ++i) if (t[i] == v) return t[(i + 1) % N];
    return t[0];
}
const char* mm_name(unsigned v) {
    switch (v) { case 0: return "GAME"; case 1: return "FULL"; case 12500: return "12.5 M"; case 10000: return "10 M";
                 case 8000: return "8 M"; default: return "?"; }
}
const char* wm_opq_name() { return mm_name(re4dc_qa_wopq_mm); }
const char* wm_xlu_name() { return mm_name(re4dc_qa_wxlu_mm); }
const char* wm_shell_name() { return re4dc_qa_wshell == 1 ? "ON" : re4dc_qa_wshell == 2 ? "OFF" : "GAME"; }
#endif

// ---------------------------------------------------------------- diagnostics
// The game side (dbgwarp_bridge.cpp qa_poll, at menu open): room, Ganados alive, heap 4 free, preset name.
struct QaGame { unsigned room; int alive, heap4; char preset[24]; };
QaGame g_game;
char g_diag[3072];             // the snapshot: "key=value" lines, then LOG and the last log lines
int g_diag_len, g_diag_stats;  // bytes, bytes before LOG
constexpr int kLogLines = 20, kLogCols = 96;
char g_log[kLogLines][kLogCols + 1];
int g_nlog;

void snap_log() {   // the last kLogLines lines of the RAM log ring (platform/mem.cpp), oldest first
    const unsigned long head = re4dc_log_head;
    const unsigned long size = sizeof(re4dc_logbuf);
    const unsigned long avail = head < size ? head : size;
    unsigned long end = head, p = head;
    int n = 0;
    char tmp[kLogLines][kLogCols + 1];
    if (p && re4dc_logbuf[(p - 1) % size] == '\n') { --p; end = p; }
    while (n < kLogLines && head - p < avail) {
        unsigned long s = p;
        while (head - s < avail && s > 0 && re4dc_logbuf[(s - 1) % size] != '\n') --s;
        unsigned long len = end - s;
        if (len > kLogCols) len = kLogCols;
        for (unsigned long i = 0; i < len; ++i) {
            const char c = re4dc_logbuf[(s + i) % size];
            tmp[n][i] = c >= 32 && c < 127 ? c : ' ';
        }
        tmp[n][len] = 0;
        ++n;
        if (s == 0 || head - s >= avail) break;
        p = s - 1; end = p;
    }
    g_nlog = n;
    for (int i = 0; i < n; ++i) memcpy(g_log[i], tmp[n - 1 - i], sizeof(g_log[i]));
}

int addf(int at, const char* fmt, ...) __attribute__((format(printf, 2, 3)));
int addf(int at, const char* fmt, ...) {
    if (at >= (int) sizeof(g_diag) - 1) return at;
    va_list ap;
    va_start(ap, fmt);
    const int k = vsnprintf(g_diag + at, sizeof(g_diag) - at, fmt, ap);
    va_end(ap);
    return k < 0 ? at : (at + k >= (int) sizeof(g_diag) ? (int) sizeof(g_diag) - 1 : at + k);
}

#if defined(RE4DC_WORLD_SCRATCH) && RE4DC_WORLD_SCRATCH
int scratch_rows(int at) {
    re4dc::world_scratch::MeterSnapshot s{};
    if (!re4dc_world_scratch_meter_read(&s)) return addf(at, "scratch no measured window\n");
    if (s.kind != 1 || s.target != 600) return addf(at, "scratch unsupported measurement\n");
    const char* phase = s.phase == 3 && s.complete ? "COMPLETE" : s.phase == 4 || s.phase == 3 ? "INVALID" :
                        s.phase == 2 ? "PENDING BOUNDARY" : "ACTIVE";
    const char arm = s.window_serial && s.arm <= 2 ? char('A' + s.arm) : '?';
    at = addf(at, "scratch %s %c room=%03x n=%u/%u draw=%u skip=%u\n", phase, arm, s.room, s.periods, s.target, s.drawn, s.skipped);
    auto us = [](unsigned lo, unsigned hi) { return (static_cast<unsigned long long>(hi) << 32) | lo; };
    const auto total = us(s.wall_us_lo, s.wall_us_hi), maximum = us(s.max_us_lo, s.max_us_hi);
    const auto mean = s.periods ? total / s.periods : 0;
    at = addf(at, "scratch wall+wait avg=%llu.%03llu ms max=%llu.%03llu ms\n", mean / 1000, mean % 1000, maximum / 1000, maximum % 1000);
    at = addf(at, "scratch borrows=%u faults=%u CCR=%x restored=%u\n", s.borrows, s.faults, s.ccr, s.restored);
    return addf(at, "scratch entry=%lluus exit=%lluus INCLUDED IN WALL\n", us(s.enter_us_lo, s.enter_us_hi), us(s.exit_us_lo, s.exit_us_hi));
}
#endif

void snap_diag() {
    int a = 0;
    a = addf(a, "RE4DCQA1\nbuild=%s\nroom=%03x preset=%s\n", RE4DC_QA_NAME, g_game.room,
             g_game.preset[0] ? g_game.preset : "-");
#if defined(RE4DC_WORLD_SCRATCH) && RE4DC_WORLD_SCRATCH
    a = scratch_rows(a); // separate completed arm/window, not the restored mode's live FPS
#endif
    unsigned v[3];
    if (re4dc_qa_speed && re4dc_qa_speed(v)) a = addf(a, "fps=%u.%u speed=%u cpu=%u\n", v[0] / 10, v[0] % 10, v[1], v[2]);
    else a = addf(a, "fps=NA\n");
    if (re4dc_tick_log_snapshot) {
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
        constexpr int kSnap = 48;   // tick_log.cpp's WORLD_METER slots
#else
        constexpr int kSnap = 32;
#endif
        const char* nm[kSnap]; unsigned avg[kSnap]; unsigned seq = 0;
        const int n = re4dc_tick_log_snapshot(nm, avg, nullptr, kSnap, &seq);
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
        if(n>0){
#endif
        auto get = [&](const char* k) -> unsigned { for (int i = 0; i < n; ++i) if (nm[i] && !strcmp(nm[i], k)) return avg[i]; return 0u; };
        const unsigned logic = get("logic"), em = get("EspMove"), et = get("EspTrans");
        const unsigned objs = get("objTrans") + get("ShadowTrans") + get("MirrorTrans") + get("ClothTrans");
        const unsigned trans = get("trans"), post = get("post"), cpu = get("cpu"), remain = get("remain"), total = get("total");
        const unsigned other = trans > et + objs ? trans - et - objs : 0;
        const unsigned draw = remain > cpu ? remain - cpu : 0, wait = total > remain ? total - remain : 0;
        auto ms = [](unsigned us) { return (us + 50) / 100; };   // 0.1 ms
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
        // WORLD_METER: Render() (the "setup" phase: the world draw, the models' OT draw) split into the PS2 world passes
        // and the rest (render); total = the tick's wall time; other = total minus every part shown, from the rounded
        // parts, so the rows add up exactly. All values are means per tick (drawn and skipped ticks) over the window.
        const unsigned p_logic = ms(logic > em ? logic - em : 0), p_fx = ms(em + et), p_mod = ms(objs), p_scn = ms(other),
                       p_post = ms(post), p_draw = ms(draw), p_wait = ms(wait);
        const unsigned wopq = ms(get("wopq")), wxlu = ms(get("wxlu")), wsh = ms(get("wshell")), wall = ms(get("wall"));
        const int p_render = (int) ms(get("setup")) - (int) (wopq + wxlu + wsh);
        const int shown = (int) (p_logic + p_fx + p_mod + p_scn + p_post + p_draw + p_wait + wopq + wxlu + wsh) + p_render;
        a = addf(a, "ms10 logic=%u fx=%u models=%u scenery=%u post=%u draw=%u wait=%u\n", p_logic, p_fx, p_mod, p_scn, p_post,
                 p_draw, p_wait);
        a = addf(a, "ms10 world_opq=%u world_xlu=%u shell=%u render=%d other=%d total=%u\n", wopq, wxlu, wsh, p_render,
                 (int) wall - shown, wall);
        a = addf(a, "strip_input opq=%u xlu=%u shell_sent=%u per_tick\n", get("vopq"), get("vxlu"), get("vshell"));
        if(re4dc_world_meter_geometry_supported()){
            a=addf(a,"TRANSFORMED / INSIDE VIEW OPQ=%u / %u per tick\n",get("topq"),get("iopq"));
            a=addf(a,"TRANSFORMED / INSIDE VIEW PT=%u / %u per tick\n",get("tpt"),get("ipt"));
            a=addf(a,"TRANSFORMED / INSIDE VIEW TR=%u / %u per tick\n",get("ttr"),get("itr"));
            a=addf(a,"Crossing triangles may have 0 corners inside; depth visibility NA.\n");
        }else a=addf(a,"cache_xform/input_inside=NA unsupported transform path\n");
        unsigned window[11];
        if(re4dc_world_meter_window(window))a=addf(a,"world_window room=%03x View=%u PVS=%u frames=%u-%u ticks=%u seq=%u\n",window[0],window[1],window[2],window[7],window[8],window[9],window[10]);
        (void) total;
#else
        a = addf(a, "ms10 logic=%u fx=%u models=%u scenery=%u post=%u draw=%u wait=%u total=%u\n",
                 ms(logic > em ? logic - em : 0), ms(em + et), ms(objs), ms(other), ms(post), ms(draw), ms(wait), ms(total));
#endif
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
        }else a=addf(a,"world timing/vertices=NA collecting this room/View/PVS window\n");
#endif
    } else a = addf(a, "ms10=NA\n");
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    {
        const int vd = re4dc_view_dist_get ? re4dc_view_dist_get() : -1;
        a = addf(a, "world rows opq=%s xlu=%s shell=%s view=%s\n", wm_opq_name(), wm_xlu_name(), wm_shell_name(),
                 vd == 2 ? "short" : vd == 1 ? "near" : vd == 0 ? "full" : "na");
    }
#endif
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    if(re4dc_ps2_pvs_state){unsigned state[4];re4dc_ps2_pvs_state(state);a=addf(a,"PVS current=%u file=%s geometric_cell=%u heap_bytes=%u\n",state[0],state[1]?"loaded":"fallback",state[2],state[3]);}
    if(re4dc_pvs23_receipt_state){unsigned state[5];re4dc_pvs23_receipt_state(state);a=addf(a,"PVS prefix=%x/%x boot_commits=%u boot_cuts_placement/cluster=%u/%u\n",state[0],state[1],state[2],state[3],state[4]);}
#endif
    a = addf(a, "heap4=%d\n", g_game.heap4);
    if (re4dc_kos_heap_state) { unsigned f = 0, u = 0, b = 0; re4dc_kos_heap_state(&f, &u, &b); a = addf(a, "kos free=%u used=%u brk=%u\n", f, u, b); }
    if (re4dc_vram_pages_census) { unsigned o[16] = {0}; re4dc_vram_pages_census(o); a = addf(a, "vram free=%u big=%u fails=%u\n", o[3], o[4], o[10]); }
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    {   // VRAM failures by room (the VRAMFAIL log lines carry each one's size, caller and texture key)
        unsigned lr = 0, ln = 0, rr[8], rc[8];
        const unsigned k = re4dc_vram_fail_rooms(&lr, &ln, rr, rc, 8);
        a = addf(a, "vram fails last_room=%03x n=%u by room:", lr, ln);
        for (unsigned i = 0; i < k; ++i) a = addf(a, " %03x=%u", rr[i], rc[i]);
        a = addf(a, "\n");
    }
#endif
    if (re4dc_disc_meter_totals) {
        unsigned r = 0; unsigned long long by = 0, bl = 0;
        re4dc_disc_meter_totals(&r, &by, &bl);
        a = addf(a, "disc reads=%u kb=%u blocked_ms=%u\n", r, (unsigned) (by >> 10), (unsigned) (bl / 1000));
    } else a = addf(a, "disc=NA\n");
    a = addf(a, "ganados_alive=%d\n", g_game.alive);
    if (re4dc_fx_esp_live) {
        unsigned n = 0;
        for (int i = 0; i < 32; ++i) n += (unsigned) __builtin_popcountl(re4dc_fx_esp_live[i]);
        a = addf(a, "fx_live=%u\n", n);
    }
    g_diag_stats = a;
    snap_log();
    a = addf(a, "LOG\n");
    for (int i = 0; i < g_nlog; ++i) a = addf(a, "%.72s\n", g_log[i]);
    g_diag_len = a;
}

// QR pages: each page is "RE4DCQA <p>/<n>\n" + a slice of g_diag (ECC high, version <= 23: 109 modules, 4 px each).
constexpr int kQrChunk = 300, kQrMaxVer = 23;
int qr_pages() { return (g_diag_len + kQrChunk - 1) / kQrChunk; }
void draw_qr(const Fb& fb, int page) {
    static uint8_t qr[qrcodegen_BUFFER_LEN_FOR_VERSION(kQrMaxVer)], tmp[qrcodegen_BUFFER_LEN_FOR_VERSION(kQrMaxVer)];
    char text[kQrChunk + 32];
    const int n = qr_pages();
    const int off = page * kQrChunk, len = g_diag_len - off < kQrChunk ? g_diag_len - off : kQrChunk;
    const int h = snprintf(text, sizeof(text), "RE4DCQA %d/%d\n", page + 1, n);
    memcpy(text + h, g_diag + off, len);
    text[h + len] = 0;
    fb_fill(fb, 0, 0, fb.w, fb.h, 0xFFFFFF);
    if (!qrcodegen_encodeText(text, tmp, qr, qrcodegen_Ecc_HIGH, 1, kQrMaxVer, qrcodegen_Mask_AUTO, false)) {
        fb_center(fb, 200, 2, 3, 0x000000, "QR ENCODE FAILED");
        return;
    }
    const int size = qrcodegen_getSize(qr);
    int px = (fb.h - 16) / (size + 4);
    if (px > 8) px = 8;
    const int x0 = 24 + 2 * px, y0 = (fb.h - size * px) / 2;
    for (int y = 0; y < size; ++y)
        for (int x = 0; x < size; ++x)
            if (qrcodegen_getModule(qr, x, y)) fb_fill(fb, x0 + x * px, y0 + y * px, px, px, 0x000000);
    char buf[48];
    const int tx = x0 + size * px + 3 * px;
    snprintf(buf, sizeof(buf), "PAGE %d/%d", page + 1, n);
    fb_text(fb, tx, 60, 2, 3, 0x000000, buf);
    fb_text(fb, tx, 100, 1, 2, 0x000000, "X: NEXT PAGE");
    fb_text(fb, tx, 120, 1, 2, 0x000000, "B: BACK");
    fb_text(fb, tx, 160, 1, 2, 0x000000, "PHOTO EACH PAGE");
}
void draw_diag(const Fb& fb) {
    fb_fill(fb, 0, 0, fb.w, fb.h, 0x000000);
    fb_fill(fb, 20, 8, fb.w - 40, 22, kRed);
    fb_center(fb, 12, 1, 2, kWhite, RE4DC_QA_NAME " - DIAGNOSTICS (GAME PAUSED)");
    int y = 38;
    for (int i = 0; i < g_diag_stats;) {   // the stats, one row each (after the first line)
        int j = i;
        while (j < g_diag_stats && g_diag[j] != '\n') ++j;
        if (i) {
            char row[100];
            int k = j - i < 99 ? j - i : 99;
            memcpy(row, g_diag + i, k); row[k] = 0;
            fb_text(fb, 30, y, 1, 2, kCyan, row);
            y += 16;
        }
        i = j + 1;
    }
    y += 4;
    fb_text(fb, 30, y, 1, 2, kYellow, "LAST LOG LINES"); y += 16;
    for (int i = 0; i < g_nlog && y < fb.h - 36; ++i) {
        char row[100];
        snprintf(row, sizeof(row), "%.100s", g_log[i]);
        fb_text(fb, 30, y, 1, 1, kWhite, row);
        y += 10;
    }
    fb_text(fb, 30, fb.h - 26, 1, 2, kGrey, "X: QR SNAPSHOT (PHOTO IT)   B: BACK");
}

// ---------------------------------------------------------------- menu
enum { M_MAIN, M_CHAP, M_PRE, M_DIAG, M_QR };
#if defined(RE4DC_WORLD_SCRATCH) && RE4DC_WORLD_SCRATCH
#define QA_WS_ROW A_WSCR,
#define QA_WS_ENUM , A_WSCR
#else
#define QA_WS_ROW
#define QA_WS_ENUM
#endif
enum { A_RESUME, A_TELEPORT_MENU, A_HEALTH, A_LEON, A_PARTNER, A_ENEMY, A_SPEED, A_TITLE, A_NORMAL, A_DIAG, A_SHORE, A_WOPQ, A_WXLU, A_WSHELL
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    , A_PVS
#endif
    QA_WS_ENUM
};
struct Menu {
    bool boot;
    int screen, sel[5], chap, qr_page;
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    int items[16], nitems;
#else
    int items[12], nitems;
#endif
};
const char* onoff(unsigned bit) { return (g_flags & bit) ? "ON" : "OFF"; }
const char* speed_name() { return (re4dc_quality_speed() & 2) ? "ON" : "OFF"; }
void item_text(int a, char* out, unsigned n) {
    switch (a) {
    case A_RESUME: snprintf(out, n, "RESUME"); break;
    case A_NORMAL: snprintf(out, n, "START THE GAME NORMALLY"); break;
    case A_TELEPORT_MENU: snprintf(out, n, "TELEPORT..."); break;
    case A_HEALTH: snprintf(out, n, "REFILL HEALTH (LEON AND PARTNER)"); break;
    case A_LEON: snprintf(out, n, "LEON INVINCIBLE: %s", onoff(1)); break;
    case A_PARTNER: snprintf(out, n, "PARTNER INVINCIBLE: %s", onoff(2)); break;
    case A_ENEMY: snprintf(out, n, "ENEMIES INVINCIBLE: %s", onoff(4)); break;
    case A_SPEED: snprintf(out, n, "SPEED DISPLAY: %s", speed_name()); break;
    case A_TITLE: snprintf(out, n, "QUIT TO THE TITLE SCREEN"); break;
    case A_DIAG: snprintf(out, n, "DIAGNOSTICS"); break;
    case A_SHORE: snprintf(out, n, "LAKE SHORE VIEW: %s", &re4dc_qa_shore_far_mm && re4dc_qa_shore_far_mm ? "30 M" : "45 M"); break;
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    case A_WOPQ: snprintf(out, n, "OPAQUE WORLD CUT: %s", wm_opq_name()); break;
    case A_WXLU: snprintf(out, n, "TRANSLUCENT WORLD: %s", wm_xlu_name()); break;
    case A_WSHELL: snprintf(out, n, "FAR SHELL: %s", wm_shell_name()); break;
    case A_PVS: {unsigned state[4]={};if(re4dc_ps2_pvs_state)re4dc_ps2_pvs_state(state);snprintf(out,n,"WORLD PVS (THIS BOOT): %s",state[0]==1?(state[1]?"ON / GUARDED":"ON / DRAW ALL"):"OFF");break;}
#endif
#if defined(RE4DC_WORLD_SCRATCH) && RE4DC_WORLD_SCRATCH
    case A_WSCR: snprintf(out, n, "WORLD SCRATCH: %s", re4dc_world_scratch_live == 2 ? "C SCRATCH" :
                          re4dc_world_scratch_live == 1 ? "B HALF CACHE" : "A NORMAL"); break;
#endif
    default: out[0] = 0;
    }
}
int presets_of(int ch, int* idx) {
    int n = 0;
    for (int i = 0; i < g_np; ++i)
        if (g_p[i].ch == ch) idx[n++] = i;
    return n;
}
void draw_screen(const Fb& fb, const Menu& m);
// The screen, then a log line with the framebuffer for the harness captures (capture_ui_vram.py reads "fb=front,back" as
// KOS pointers: 0xa5000000 + 2 x the display offset).
void draw(const Fb& fb, const Menu& m) {
    draw_screen(fb, m);
    const unsigned long ptr = 0xa5000000ul + 2ul * ((unsigned long) fb.base & 0x007FFFFFul);
    re4dc_log("qa: screen %d fb=%08lx,%08lx\n", m.screen, ptr, ptr);
}
void draw_screen(const Fb& fb, const Menu& m) {
    if (m.screen == M_DIAG) { draw_diag(fb); return; }
    if (m.screen == M_QR) { draw_qr(fb, m.qr_page); return; }
    fb_fill(fb, 0, 0, fb.w, fb.h, 0x000000);
    fb_fill(fb, 20, 14, fb.w - 40, 44, kRed);
    fb_center(fb, 20, 2, 3, kWhite, RE4DC_QA_NAME);
    fb_center(fb, 42, 1, 2, kYellow, "TEST BUILD FOR TESTERS - NOT THE RELEASE GAME");
    int y = 76;
    char buf[96];
    int n = 0, first = 0;
    const int rows = 16;
    if (m.screen == M_MAIN) {
        fb_text(fb, 40, y, 2, 2, kCyan, m.boot ? "QA MENU" : "QA MENU (GAME PAUSED)"); y += 26;
        n = m.nitems;
    } else if (m.screen == M_CHAP) {
        fb_text(fb, 40, y, 2, 2, kCyan, "TELEPORT: CHAPTER"); y += 26;
        n = g_nch;
    }
    int idx[kMaxP];
    if (m.screen == M_PRE) {
        snprintf(buf, sizeof(buf), "TELEPORT: %s", g_ch[m.chap]);
        fb_text(fb, 40, y, 2, 2, kCyan, buf); y += 26;
        n = presets_of(m.chap, idx);
    }
    const int sel = m.sel[m.screen];
    if (sel >= rows) first = sel - rows + 1;
    for (int i = first; i < n && i < first + rows; ++i) {
        uint32_t col = i == sel ? kYellow : kWhite;
        if (i == sel) fb_fill(fb, 30, y - 3, fb.w - 60, 20, kBlue);
        if (m.screen == M_MAIN) item_text(m.items[i], buf, sizeof(buf));
        else if (m.screen == M_CHAP) snprintf(buf, sizeof(buf), "%s", g_ch[i]);
        else {
            const Preset& p = g_p[idx[i]];
            snprintf(buf, sizeof(buf), "%s", p.label);
            fb_text(fb, 520, y, 1, 2, p.kind == 'S' ? kGreen : kGrey, p.kind == 'S' ? "STORY" : "BARE JUMP");
        }
        fb_text(fb, 44, y, 2, 2, col, buf);
        y += 21;
    }
    y = fb.h - 70;
    if (m.screen == M_PRE && n) {
        const Preset& p = g_p[idx[sel]];
        fb_text(fb, 40, y, 1, 2, p.kind == 'S' ? kGreen : kGrey,
                p.kind == 'S' ? "STORY STATE: PROGRESS SET, ENEMIES FROM THE ROOM'S OWN LIST"
                              : "BARE JUMP: NO STORY STATE, ENEMIES MAY BE MISSING");
    }
    y += 22;
    fb_text(fb, 40, y, 1, 2, kGrey, m.boot ? "D-PAD: CHOOSE   A: SELECT / SWITCH   B: BACK"
                                           : "D-PAD: CHOOSE   A: SELECT / SWITCH   B: BACK / RESUME");
    y += 18;
    fb_text(fb, 40, y, 1, 2, kGrey, "IN GAME: HOLD L + R AND PRESS D-PAD DOWN FOR THIS MENU");
}

// Runs a menu until a choice that leaves it. Returns A_RESUME / A_NORMAL / A_TITLE / A_HEALTH (then the menu is shown
// again by the caller if it wants) or -1 = teleport (g_path set).
int run(Menu& m, bool boot) {
    load_presets();
    uint32_t last_sof = ~0u;
    bool dirty = true;
    unsigned prev = ~0u;   // every button must be up before a press counts (the opening chord is still held)
    uint64_t rep_t = 0;
    for (;;) {
        const Fb fb = boot ? fb_boot() : fb_displayed();
        const uint32_t sof = boot ? 0 : *(volatile uint32_t*) 0xA05F8050;
        if (dirty || sof != last_sof) { draw(fb, m); last_sof = sof; dirty = false; }
        const Pad p = pad_read();
        const unsigned b = p.buttons;
        if (prev == ~0u) prev = b;   // buttons held when the menu opens count only after release
        unsigned press = b & ~prev;
        prev = b;
        const uint64_t now = timer_us_gettime64();
        const unsigned dirs = b & (CONT_DPAD_UP | CONT_DPAD_DOWN);
        if (press & dirs) rep_t = now + 400000;
        else if (dirs && rep_t && now >= rep_t) { press |= dirs; rep_t = now + 120000; }
        int n = m.screen == M_MAIN ? m.nitems : m.screen == M_CHAP ? g_nch : 0;
        int idx[kMaxP];
        if (m.screen == M_PRE) n = presets_of(m.chap, idx);
        int& s = m.sel[m.screen];
        if ((press & CONT_DPAD_UP) && n) { s = (s + n - 1) % n; dirty = true; }
        if ((press & CONT_DPAD_DOWN) && n) { s = (s + 1) % n; dirty = true; }
        if (press & CONT_B) {
            dirty = true;
            if (m.screen == M_PRE) m.screen = M_CHAP;
            else if (m.screen == M_QR) m.screen = M_DIAG;
            else if (m.screen == M_CHAP || m.screen == M_DIAG) m.screen = M_MAIN;
            else if (!boot) return A_RESUME;
        }
        if ((press & CONT_START) && m.screen == M_MAIN && !boot) return A_RESUME;
        if ((press & CONT_X) && (m.screen == M_DIAG || m.screen == M_QR)) {
            m.qr_page = m.screen == M_QR ? (m.qr_page + 1) % qr_pages() : 0;
            m.screen = M_QR;
            dirty = true;
            re4dc_log("qa: diagnostics QR page %d/%d\n", m.qr_page + 1, qr_pages());
        }
        if ((press & CONT_A) && n) {
            dirty = true;
            if (m.screen == M_CHAP) { m.chap = s; m.screen = M_PRE; m.sel[M_PRE] = 0; }
            else if (m.screen == M_PRE) {
                snprintf(g_path, sizeof(g_path), "/cd/dc/qa/%s", g_p[idx[s]].file);
                re4dc_log("qa: teleport %s (%s)\n", g_path, g_p[idx[s]].label);
                return -1;
            } else {
                const int a = m.items[s];
                if (a == A_TELEPORT_MENU) { if (g_nch) m.screen = M_CHAP; }
                else if (a == A_LEON) g_flags ^= 1;
                else if (a == A_PARTNER) g_flags ^= 2;
                else if (a == A_ENEMY) g_flags ^= 4;
                else if (a == A_SPEED) {   // until the on-screen bit changes (SPEED_VMU_OFF reads VMU as off)
                    const int was = re4dc_quality_speed() & 2;
                    for (int k = 0; k < 4 && (re4dc_quality_speed() & 2) == was; ++k) re4dc_speed_cycle();
                }
                else if (a == A_DIAG) { snap_diag(); m.screen = M_DIAG; }
                else if (a == A_SHORE) { if (&re4dc_qa_shore_far_mm) re4dc_qa_shore_far_mm = re4dc_qa_shore_far_mm ? 0u : 30000u; }
#if defined(RE4DC_WORLD_SCRATCH) && RE4DC_WORLD_SCRATCH
                else if (a == A_WSCR) {   // live arm, this boot only: A -> B -> C -> A
                    re4dc_world_scratch_live = (re4dc_world_scratch_live + 1) % 3;
                    re4dc_log("qa: world scratch arm=%u\n", (unsigned) re4dc_world_scratch_live);
                }
#endif
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
                else if(a==A_PVS){
                    unsigned state[4]={};if(re4dc_ps2_pvs_state)re4dc_ps2_pvs_state(state);
                    if(re4dc_ps2_pvs_set)re4dc_ps2_pvs_set(state[0]==1?0U:1U);
                    re4dc_log("qa: PVS %s this boot; meter recollects window\n",state[0]==1?"OFF":"ON");
                }
                else if (a == A_WOPQ || a == A_WXLU || a == A_WSHELL) {
                    if (a == A_WOPQ) re4dc_qa_wopq_mm = next_of(kOpq, re4dc_qa_wopq_mm);
                    else if (a == A_WXLU) re4dc_qa_wxlu_mm = next_of(kXlu, re4dc_qa_wxlu_mm);
                    else re4dc_qa_wshell = (re4dc_qa_wshell + 1) % 3;
                    re4dc_log("qa: world rows opq=%s xlu=%s shell=%s\n", wm_opq_name(), wm_xlu_name(), wm_shell_name());
                }
#endif
                else return a;
                if (a >= A_LEON && a <= A_ENEMY) re4dc_log("qa: toggles %x\n", (unsigned) g_flags);
            }
        }
        spin_us(16000);
    }
}
void wait_release() {
    for (int quiet = 0; quiet < 6;) {
        const Pad p = pad_read();
        quiet = (p.buttons & (CONT_A | CONT_B | CONT_START | CONT_DPAD_UP | CONT_DPAD_DOWN)) || p.l > 40 || p.r > 40 ? 0 : quiet + 1;
        spin_us(16000);
    }
}
}  // namespace

extern "C" {

// The boot menu's choice: the preset fixture, or nullptr (start normally / a harness disc with dc/warp.txt).
const char* re4dc_qa_boot_path(void) { return g_boot_path; }

// The in-game chord: L and R triggers held and D-pad Down (port A, raw).
int re4dc_qa_combo(void) {
    const Pad p = pad_read();
    return p.l > 200 && p.r > 200 && (p.buttons & CONT_DPAD_DOWN);
}

unsigned re4dc_qa_flags(void) { return g_flags; }
void re4dc_qa_set_flags(unsigned f) { g_flags = f & 7; }

// The game side of the Diagnostics page (dbgwarp_bridge.cpp, at menu open).
void re4dc_qa_game(unsigned room, int alive, int heap4, const char* preset) {
    g_game.room = room; g_game.alive = alive; g_game.heap4 = heap4;
    strncpy(g_game.preset, preset ? preset : "", sizeof(g_game.preset) - 1);
}

// Harness (`qa_menu` / `qa_diag` warp lines): the menu drawn once, the Diagnostics page and its QR pages held for
// hold_ms each (captures), then a teleport to /cd/dc/qa/<file> (file empty: resume).
int re4dc_qa_menu_auto(const char* file, const char** path, unsigned hold_ms) {
    static Menu m;
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    const int items[] = {A_RESUME, A_TELEPORT_MENU, A_DIAG, A_HEALTH, A_LEON, A_PARTNER, A_ENEMY, A_SPEED, A_SHORE,
                         A_WOPQ, A_WXLU, A_WSHELL, QA_WS_ROW A_TITLE};
#else
    const int items[] = {A_RESUME, A_TELEPORT_MENU, A_DIAG, A_HEALTH, A_LEON, A_PARTNER, A_ENEMY, A_SPEED, A_SHORE, QA_WS_ROW A_TITLE};
#endif
    m.nitems = (int) (sizeof(items) / sizeof(items[0]));
    memcpy(m.items, items, sizeof(items));
    load_presets();
    m.screen = M_MAIN;
    draw(fb_displayed(), m);
    spin_us(500000);
    if (hold_ms) {
        snap_diag();
        m.screen = M_DIAG;
        draw(fb_displayed(), m);
        re4dc_log("qa: auto diagnostics (%d bytes, %d QR pages)\n", g_diag_len, qr_pages());
        for (unsigned t = 0; t < hold_ms; t += 16) spin_us(16000);
        for (int pg = 0; pg < qr_pages(); ++pg) {
            m.screen = M_QR; m.qr_page = pg;
            draw(fb_displayed(), m);
            re4dc_log("qa: auto QR page %d/%d\n", pg + 1, qr_pages());
            for (unsigned t = 0; t < hold_ms; t += 16) spin_us(16000);
        }
    }
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    re4dc_world_meter_resume(); // captures keep the sealed snapshot; all exits reset the next interval
#endif
    if (!file || !file[0]) return 0;
    snprintf(g_path, sizeof(g_path), "/cd/dc/qa/%s", file);
    re4dc_log("qa: auto teleport %s\n", g_path);
    *path = g_path;
    return 1;
}

// In-game menu (the warp rig's poll, frame loop stopped). 0 resume, 1 teleport (*path), 2 title, 3 refill health.
int re4dc_qa_menu(const char** path) {
    static Menu m;
    m.boot = false;
    if (m.screen != M_MAIN) m.screen = M_MAIN;
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    const int items[] = {A_RESUME, A_TELEPORT_MENU, A_DIAG, A_HEALTH, A_LEON, A_PARTNER, A_ENEMY, A_SPEED, A_SHORE,
                         A_WOPQ, A_WXLU, A_WSHELL, QA_WS_ROW A_TITLE};
#else
    const int items[] = {A_RESUME, A_TELEPORT_MENU, A_DIAG, A_HEALTH, A_LEON, A_PARTNER, A_ENEMY, A_SPEED, A_SHORE, QA_WS_ROW A_TITLE};
#endif
    m.nitems = (int) (sizeof(items) / sizeof(items[0]));
    memcpy(m.items, items, sizeof(items));
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    if(re4dc_ps2_pvs_set && re4dc_ps2_pvs_state){m.items[m.nitems-1]=A_PVS;m.items[m.nitems++]=A_TITLE;}
#endif
    re4dc_log("qa: menu open\n");
    const int a = run(m, false);
    wait_release();
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    re4dc_world_meter_resume(); // exclude paused-menu wall time from the next window
#endif
    re4dc_log("qa: menu closed (%d)\n", a);
    if (a == -1) { *path = g_path; return 1; }
    if (a == A_TITLE) return 2;
    if (a == A_HEALTH) return 3;
    return 0;
}

// Banner on the title screens (platform/native_ui.cpp, RE4DC_QA_BANNER): the QA name until the first room entry.
const char* re4dc_bench_banner(void) { return RE4DC_QA_NAME " - QA TEST BUILD"; }
int re4dc_qa_banner_on(void) { return !g_in_room; }
void re4dc_qa_in_room(int on) { g_in_room = on; }

#if defined(RE4DC_QA_UI_WRAP) && RE4DC_QA_UI_WRAP
unsigned __real_re4dc_ui_frame(void);
unsigned __wrap_re4dc_ui_frame(void) { return __real_re4dc_ui_frame() + g_menu_ticks; }
#endif

void __wrap_OSInit(void)
{
    static bool done;
    __real_OSInit();
    if (done) return;
    done = true;
    char probe[4] = {0, 0, 0, 0};
    if (re4dc_fixture_read("/cd/dc/warp.txt", probe, sizeof(probe)) > 0 && probe[0]) {
        re4dc_log("qa: dc/warp.txt present: boot menu skipped (harness disc)\n");
        return;
    }
    vid_set_mode(DM_640x480, PM_RGB565);
    Menu m{};
    m.boot = true;
    const int items[] = {A_NORMAL, A_TELEPORT_MENU, A_LEON, A_PARTNER, A_ENEMY};
    m.nitems = 5;
    memcpy(m.items, items, sizeof(items));
    const int a = run(m, true);
    g_boot_path = a == -1 ? g_path : nullptr;
    const Fb fb = fb_boot();
    fb_fill(fb, 0, 0, 640, 480, 0x000000);
    fb_center(fb, 200, 3, 4, kWhite, RE4DC_QA_NAME);
    fb_center(fb, 250, 2, 3, kCyan, g_boot_path ? "LOADING THE PRESET..." : "STARTING...");
    wait_release();
    re4dc_log("qa: boot choice %s\n", g_boot_path ? g_boot_path : "normal");
}

}  // extern "C"
