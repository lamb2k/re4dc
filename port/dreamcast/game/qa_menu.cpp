#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
#include "platform/include/draw_fallback_audit.h"
#include "platform/include/draw_fallback_link26.hpp"
#endif
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
#include "platform/include/draw_setup_audit.h"
#endif
#if defined(RE4DC_ACTOR_LIGHT_FAST_ONLY) && RE4DC_ACTOR_LIGHT_FAST_ONLY
#include "platform/include/actor_light_fast_only.h"
#endif
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
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#if defined(RE4DC_QA_LINK) && RE4DC_QA_LINK
#include <stdlib.h>
#include <ctype.h>
#include <strings.h>
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
#include "world_census24.h"
#define QA_CENSUS_ROW A_CENSUS,
#if defined(RE4DC_PERF_PHASE_MISS) && RE4DC_PERF_PHASE_MISS
#include "platform/include/perf_phase_miss.h"
#endif
#else
#define QA_CENSUS_ROW
#endif
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
int re4dc_world_meter_window(unsigned out[11]) __attribute__((weak));                           // tick_log.cpp (GAME_TICK_LOG != 0)
int re4dc_world_meter_geometry_supported(void);
void re4dc_world_meter_resume(void);
int re4dc_view_dist_get(void) __attribute__((weak));                                         // option_rows.cpp
#endif
extern volatile unsigned long re4dc_log_head;                                                  // platform/mem.cpp
#ifndef RE4DC_LOG_TRIM
#define RE4DC_LOG_TRIM 0
#endif
extern char re4dc_logbuf[0x10000 - RE4DC_LOG_TRIM];                                            // mem.cpp RE4DC_LOG_SIZE
#if defined(RE4DC_QA_LINK) && RE4DC_QA_LINK
// qa_link.cpp (QA_LINK=1): modem + PPP + UDP transport
void re4dc_qalink_config(const char* number, const char* host, unsigned port, unsigned lport);
int re4dc_qalink_start(void);
void re4dc_qalink_stop(void);
int re4dc_qalink_up(void);
int re4dc_qalink_wanted(void);
void re4dc_qalink_state_text(char* out, unsigned n);
void re4dc_qalink_counters(unsigned* tx, unsigned* rx, unsigned* drops, unsigned* queued);
int re4dc_qalink_send(const void* p, unsigned n);
int re4dc_qalink_send_bulk(const void* p, unsigned n);
unsigned re4dc_qalink_bulk_skips(void);
int re4dc_qalink_recv(char* p, unsigned max);
#endif
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
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
char g_diag[12288];            // existing 8 KiB DSA snapshot plus compact fallback rows
#else
char g_diag[7168];             // existing 3 KiB QA snapshot plus 4 KiB of compact fallback rows
#endif
unsigned g_diag_page;
#elif defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
char g_diag[8192];             // sealed draw audit + existing rows + log; QR keeps all pages
unsigned g_diag_page;
#elif defined(RE4DC_ACTOR_LIGHT_FAST_ONLY) && RE4DC_ACTOR_LIGHT_FAST_ONLY
char g_diag[4096];             // light invariant/reason rows + existing rows and log
unsigned g_diag_page;
#else
char g_diag[3072];             // the snapshot: "key=value" lines, then LOG and the last log lines
#endif
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
#if (defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT) || \
    (defined(RE4DC_ACTOR_LIGHT_FAST_ONLY) && RE4DC_ACTOR_LIGHT_FAST_ONLY) || \
    (defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT)
    g_diag_page=0;
#endif
    int a = 0;
    a = addf(a, "RE4DCQA1\nbuild=%s\nroom=%03x preset=%s\n", RE4DC_QA_NAME, g_game.room,
             g_game.preset[0] ? g_game.preset : "-");
#if defined(RE4DC_WORLD_SCRATCH) && RE4DC_WORLD_SCRATCH
    a = scratch_rows(a); // separate completed arm/window, not the restored mode's live FPS
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    {
        char row[256];
        if (re4dc::wc24::summary(row, sizeof(row)) > 0) a = addf(a, "%s\n", row);
        else a = addf(a, "WORLD CENSUS: collecting first complete drawn-frame window\n");
    }
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
        if(re4dc_world_meter_window && re4dc_world_meter_window(window))a=addf(a,"world_window room=%03x View=%u PVS=%u frames=%u-%u ticks=%u seq=%u\n",window[0],window[1],window[2],window[7],window[8],window[9],window[10]);
        (void) total;
#else
        a = addf(a, "ms10 logic=%u fx=%u models=%u scenery=%u post=%u draw=%u wait=%u total=%u\n",
                 ms(logic > em ? logic - em : 0), ms(em + et), ms(objs), ms(other), ms(post), ms(draw), ms(wait), ms(total));
#endif
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
        }else a=addf(a,"world timing/vertices=NA collecting this room/View/PVS window\n");
#endif
    } else a = addf(a, "ms10=NA\n");
#if defined(RE4DC_ACTOR_LIGHT_FAST_ONLY) && RE4DC_ACTOR_LIGHT_FAST_ONLY
    {
        Re4dcActorLight25Stats s{};
        re4dc_actor_light25_snapshot(&s);
        a = addf(a, "AL25 lifetime parts=%u fallback=%u MUST=0\n", s.parts, s.fallback_parts);
        a = addf(a, "AL25 avoided vcolour=%u diffuse_scale=%u lights_over3=%u probe_decline=%u basis=%u\n",
                 s.avoided[0], s.avoided[1], s.avoided[2], s.avoided[3], s.avoided[4]);
        a = addf(a, "AL25 vertices flat=%u multiply=%u (avoided != fallback)\n",
                 s.flat_vertices, s.multiply_vertices);
    }
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    for(unsigned i=0;i<re4dc::dfa26::line_count();++i){
        char row[192];
        if(re4dc::dfa26::format_line(i,row,sizeof(row))>0)a=addf(a,"%s\n",row);
    }
#endif
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    for(unsigned i=0;i<re4dc::dsa24::line_count();++i){
        char row[240];
        if(re4dc::dsa24::format_line(i,row,sizeof(row))>0)a=addf(a,"%s\n",row);
    }
#endif
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
#if (defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT) || \
    (defined(RE4DC_ACTOR_LIGHT_FAST_ONLY) && RE4DC_ACTOR_LIGHT_FAST_ONLY) || \
    (defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT)
unsigned diag_page_rows(const Fb& fb){return fb.h>92?unsigned((fb.h-76)/16):1U;}
unsigned diag_rows(const Fb& fb,unsigned first,bool paint){
    unsigned cols=fb.w>60?unsigned((fb.w-60)/6):1U;
    if(cols>100)cols=100;
    const unsigned limit=first+diag_page_rows(fb);
    unsigned row=0;
    for(int i=0;i<g_diag_len;){
        int j=i;while(j<g_diag_len&&g_diag[j]!='\n')++j;
        if(i){
            for(unsigned off=0;off<unsigned(j-i);off+=cols,++row){
                if(!paint||row<first||row>=limit)continue;
                char part[101];const unsigned left=unsigned(j-i)-off;
                const unsigned take=left<cols?left:cols;
                memcpy(part,g_diag+i+off,take);part[take]=0;
                fb_text(fb,30,40+int(row-first)*16,1,2,kCyan,part);
            }
        }
        i=j+1;
    }
    return row;
}
unsigned diag_pages(const Fb& fb){
    const unsigned n=diag_rows(fb,0,false),rows=diag_page_rows(fb);
    return n?(n+rows-1)/rows:1U;
}
void draw_diag(const Fb& fb){
    const unsigned pages=diag_pages(fb);g_diag_page%=pages;
    fb_fill(fb,0,0,fb.w,fb.h,0x000000);fb_fill(fb,20,8,fb.w-40,22,kRed);
    char title[80];snprintf(title,sizeof(title),"DIAGNOSTICS - PAUSED %u/%u",g_diag_page+1,pages);
    fb_center(fb,12,1,2,kWhite,title);
    diag_rows(fb,g_diag_page*diag_page_rows(fb),true);
    fb_text(fb,30,fb.h-26,1,2,kGrey,"RIGHT/LEFT: PAGE  X: QR SNAPSHOT  B: BACK");
}
#else
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

#endif

#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
// The game is paused here. Read only the sealed census, wrapping all its rows
// rather than truncating the counters at the framebuffer's right edge.
unsigned census_page_rows(const Fb& fb) {
    return fb.h > 92 ? unsigned((fb.h - 76) / 16) : 1U;
}
unsigned census_rows(const Fb& fb, unsigned first, bool paint) {
    unsigned cols = fb.w > 60 ? unsigned((fb.w - 60) / 6) : 1U;
    if (cols > 100) cols = 100;
    const unsigned limit = first + census_page_rows(fb);
    unsigned row = 0;
    const unsigned n = re4dc::wc24::line_count();
    for (unsigned i = 0; i < n; ++i) {
        char line[256];
        if (re4dc::wc24::format_line(i, line, sizeof(line)) <= 0) continue;
        const unsigned length = unsigned(strlen(line));
        for (unsigned offset = 0; offset < length; offset += cols, ++row) {
            if (!paint || row < first || row >= limit) continue;
            char part[101];
            const unsigned take = length - offset < cols ? length - offset : cols;
            memcpy(part, line + offset, take); part[take] = 0;
            fb_text(fb, 30, 40 + int(row - first) * 16, 1, 2, kCyan, part);
        }
    }
    if (!row && paint)
        fb_text(fb, 30, 40, 1, 2, kYellow, "COLLECTING THE FIRST COMPLETE DRAWN-FRAME WINDOW");
    return row;
}
unsigned census_pages(const Fb& fb) {
    const unsigned n = census_rows(fb, 0, false), rows = census_page_rows(fb);
    return n ? (n + rows - 1) / rows : 1U;
}
void draw_census(const Fb& fb, unsigned page) {
    const unsigned pages = census_pages(fb);
    page %= pages;
    fb_fill(fb, 0, 0, fb.w, fb.h, 0x000000);
    fb_fill(fb, 20, 8, fb.w - 40, 22, kRed);
    char title[96];
    snprintf(title, sizeof(title), fb.w < 480 ? "WORLD CENSUS - PAUSED %u/%u" :
             "WORLD CENSUS - SEALED WINDOW (GAME PAUSED) %u/%u", page + 1, pages);
    fb_center(fb, 12, 1, 2, kWhite, title);
    census_rows(fb, page * census_page_rows(fb), true);
#if defined(RE4DC_PERF_PHASE_MISS) && RE4DC_PERF_PHASE_MISS
    fb_text(fb, 30, fb.h - 26, 1, 2, kGrey, "A/RIGHT: NEXT LEFT: PREV X: PMU CONTROLS B: BACK");
#else
    fb_text(fb, 30, fb.h - 26, 1, 2, kGrey, fb.w < 480 ? "A/RIGHT: NEXT LEFT: PREV B: BACK" :
            "A/RIGHT: NEXT PAGE   LEFT: PREVIOUS   B: BACK");
#endif
}
#endif

// ---------------------------------------------------------------- menu
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
enum { M_MAIN, M_CHAP, M_PRE, M_DIAG, M_QR, M_CENSUS };
#else
enum { M_MAIN, M_CHAP, M_PRE, M_DIAG, M_QR };
#endif
#if defined(RE4DC_WORLD_SCRATCH) && RE4DC_WORLD_SCRATCH
#define QA_WS_ROW A_WSCR,
#define QA_WS_ENUM , A_WSCR
#else
#define QA_WS_ROW
#define QA_WS_ENUM
#endif
#if defined(RE4DC_QA_LINK) && RE4DC_QA_LINK
#define QA_LINK_ROW A_LINK,
#define QA_LINK_ENUM , A_LINK
#else
#define QA_LINK_ROW
#define QA_LINK_ENUM
#endif
enum { A_RESUME, A_TELEPORT_MENU, A_HEALTH, A_LEON, A_PARTNER, A_ENEMY, A_SPEED, A_TITLE, A_NORMAL, A_DIAG, A_SHORE, A_WOPQ, A_WXLU, A_WSHELL
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    , A_PVS
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    , A_CENSUS
#endif
    QA_WS_ENUM QA_LINK_ENUM
};
struct Menu {
    bool boot;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    int screen, sel[6], chap, qr_page, census_page;
    int items[18], nitems;
#else
    int screen, sel[5], chap, qr_page;
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    int items[16], nitems;
#else
    int items[12], nitems;
#endif
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
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    case A_CENSUS: snprintf(out, n, "WORLD CENSUS (LAST COMPLETE WINDOW)"); break;
#endif
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
#if defined(RE4DC_QA_LINK) && RE4DC_QA_LINK
    case A_LINK: { char st[64]; re4dc_qalink_state_text(st, sizeof(st)); snprintf(out, n, "REMOTE LINK: %s", st); break; }
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
#if defined(RE4DC_QA_LINK) && RE4DC_QA_LINK
// ---------------------------------------------------------------- remote link protocol (QA_LINK; tools/qalink/README.md)
// Console -> Pi, one UDP datagram each (text; the first line is the header):
//   T <seq> <ms> <part>/<parts>   telemetry, once a second: the Diagnostics page's rows (DRAW_SETUP_AUDIT rows included)
//                                 and a "link" row; split into parts of <= 1100 bytes
//   L <seq> <dropped bytes>       new RAM log lines since the last L (at most 640 bytes a second; the rest is counted)
//   R <id> <first tick>           RECORD: the wall time of each game tick (us, comma separated), 30 ticks a datagram
//   A <id> <OK|ERR> <text>        the answer to command <id>
//   D <id> <part>/<parts>         DIAG: the full Diagnostics snapshot (rows + the last 20 log lines)
// Pi -> console: "<id> <COMMAND> [args]" (id = any token without spaces; the console echoes it):
//   PING [x] | TELEPORT <preset file or label words> | QA <row> <value> | RECORD <ticks> | MENU | RESUME | DIAG | HELLO
//   QA rows: LEON / PARTNER / ENEMY ON|OFF, SPEED ON|OFF, SHORE 30|45, HEALTH, TITLE, and with WORLD_METER: WOPQ / WXLU
//   GAME|FULL|12.5|10|8, WSHELL GAME|ON|OFF, PVS ON|OFF; WORLD_SCRATCH: WSCR A|B|C.
// Commands run on the game thread inside the QA menu's own handlers (no input is synthesized). TELEPORT / TITLE wait
// for free play (the in-game menu's rule) and then take the menu's soft-reset path; MENU opens the in-game menu at the
// next free-play tick; while it is open the menu itself answers commands (RESUME closes it).
enum { LA_NONE, LA_TELEPORT, LA_TITLE, LA_HEALTH, LA_MENU, LA_RESUME };
struct Link {
    bool cfg_read, auto_start;
    unsigned seq, log_seq;
    unsigned long log_sent;
    uint64_t next_ms, cost_us, cost_t0;
    unsigned cost_last;                  // us spent in link_tick over the last whole second (game thread)
    int pending;                          // LA_TELEPORT / LA_TITLE / LA_MENU waiting for free play
    char pending_id[16];
    char last_state[64];
    // RECORD
    char rec_id[16];
    unsigned rec_left, rec_n, rec_first;
    uint64_t rec_prev_us;
    unsigned rec_us[1800];
    char rec_line[400];
    int rec_len;
    void (*game)(void);
} g_link;
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
re4dc::dfa26::Telemetry<sizeof(g_diag)+160> g_fallback_telemetry;
#endif

void link_send_text(const char* s, int n) { re4dc_qalink_send(s, (unsigned) n); }
void link_reply(const char* id, bool ok, const char* fmt, ...) __attribute__((format(printf, 3, 4)));
void link_reply(const char* id, bool ok, const char* fmt, ...) {
    char b[300];
    int k = snprintf(b, sizeof(b), "A %s %s ", id, ok ? "OK" : "ERR");
    va_list ap;
    va_start(ap, fmt);
    const int m = vsnprintf(b + k, sizeof(b) - k, fmt, ap);
    va_end(ap);
    k = m < 0 ? k : (k + m >= (int) sizeof(b) ? (int) sizeof(b) - 1 : k + m);
    link_send_text(b, k);
}
void link_read_cfg() {
    if (g_link.cfg_read) return;
    g_link.cfg_read = true;
    char text[512];
    const int len = re4dc_fixture_read("/cd/dc/qa/link.txt", text, sizeof(text) - 1);
    char number[24] = "", host[24] = "";
    unsigned port = 0, lport = 0;
    if (len > 0) {
        text[len] = 0;
        for (char* line = text; line && *line;) {
            char* next = strchr(line, '\n');
            if (next) *next++ = 0;
            char* cr = strchr(line, '\r');
            if (cr) *cr = 0;
            if (!strncmp(line, "number ", 7)) strncpy(number, line + 7, sizeof(number) - 1);
            else if (!strncmp(line, "host ", 5)) strncpy(host, line + 5, sizeof(host) - 1);
            else if (!strncmp(line, "port ", 5)) port = (unsigned) atoi(line + 5);
            else if (!strncmp(line, "lport ", 6)) lport = (unsigned) atoi(line + 6);
            else if (!strncmp(line, "auto ", 5)) g_link.auto_start = atoi(line + 5) != 0;
            line = next;
        }
    }
    re4dc_qalink_config(number, host, port, lport);
    re4dc_log("qalink: config %s number=%s host=%s port=%u lport=%u auto=%d\n", len > 0 ? "link.txt" : "defaults",
              number[0] ? number : "default", host[0] ? host : "peer", port, lport, (int) g_link.auto_start);
}
void link_toggle() {
    link_read_cfg();
    if (re4dc_qalink_wanted()) { re4dc_qalink_stop(); re4dc_log("qa: remote link off\n"); }
    else { re4dc_qalink_start(); re4dc_log("qa: remote link on\n"); }
}
bool link_state_changed() {
    char st[64];
    re4dc_qalink_state_text(st, sizeof(st));
    if (!strcmp(st, g_link.last_state)) return false;
    strcpy(g_link.last_state, st);
    return true;
}
bool word_is(const char* a, const char* b) { return !strcasecmp(a, b); }
int on_off(const char* v) { return word_is(v, "ON") || word_is(v, "1") ? 1 : word_is(v, "OFF") || word_is(v, "0") ? 0 : -1; }
// Finds a preset by its fixture file (with or without .txt) or by words of its label; -1 none.
int find_preset(const char* q) {
    for (int i = 0; i < g_np; ++i) {
        const char* f = g_p[i].file;
        const size_t ql = strlen(q);
        if (!strcasecmp(f, q) || (!strncasecmp(f, q, ql) && !strcasecmp(f + ql, ".txt"))) return i;
    }
    for (int i = 0; i < g_np; ++i) {
        char lab[48];
        unsigned k = 0;
        for (; g_p[i].label[k] && k < sizeof(lab) - 1; ++k) lab[k] = (char) toupper((unsigned char) g_p[i].label[k]);
        lab[k] = 0;
        char qq[48];
        for (k = 0; q[k] && k < sizeof(qq) - 1; ++k) qq[k] = (char) toupper((unsigned char) q[k]);
        qq[k] = 0;
        if (strstr(lab, qq)) return i;
    }
    return -1;
}
// QA <row> <value>: the menu rows' own state changes. Returns LA_HEALTH / LA_TITLE for the rows that act on the game.
int link_qa_row(const char* id, const char* row, const char* v) {
    unsigned bit = word_is(row, "LEON") ? 1 : word_is(row, "PARTNER") ? 2 : word_is(row, "ENEMY") ? 4 : 0;
    if (bit) {
        const int o = on_off(v);
        if (o < 0) { link_reply(id, false, "QA %s needs ON or OFF", row); return LA_NONE; }
        g_flags = o ? (g_flags | bit) : (g_flags & ~bit);
        re4dc_log("qa: toggles %x (link)\n", (unsigned) g_flags);
        link_reply(id, true, "QA %s %s flags=%x", row, o ? "ON" : "OFF", (unsigned) g_flags);
        return LA_NONE;
    }
    if (word_is(row, "SPEED")) {
        const int o = on_off(v);
        if (o < 0) { link_reply(id, false, "QA SPEED needs ON or OFF"); return LA_NONE; }
        for (int k = 0; k < 4 && ((re4dc_quality_speed() & 2) != 0) != (o != 0); ++k) re4dc_speed_cycle();
        link_reply(id, true, "QA SPEED %s", speed_name());
        return LA_NONE;
    }
    if (word_is(row, "SHORE")) {
        if (!&re4dc_qa_shore_far_mm) { link_reply(id, false, "QA SHORE: not in this build (LAKE_FAR)"); return LA_NONE; }
        re4dc_qa_shore_far_mm = atoi(v) == 30 ? 30000u : 0u;
        link_reply(id, true, "QA SHORE %s", re4dc_qa_shore_far_mm ? "30 M" : "45 M");
        return LA_NONE;
    }
    if (word_is(row, "HEALTH")) { link_reply(id, true, "QA HEALTH refilled"); return LA_HEALTH; }
    if (word_is(row, "TITLE")) return LA_TITLE;
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    if (word_is(row, "WOPQ") || word_is(row, "WXLU")) {
        const unsigned mm = word_is(v, "GAME") ? 0u : word_is(v, "FULL") ? 1u : (unsigned) (atof(v) * 1000.0 + 0.5);
        const bool opq = word_is(row, "WOPQ");
        bool okv = false;
        if (opq) { for (unsigned x : kOpq) okv |= x == mm; } else { for (unsigned x : kXlu) okv |= x == mm; }
        if (!okv) { link_reply(id, false, "QA %s: value not on the row", row); return LA_NONE; }
        (opq ? re4dc_qa_wopq_mm : re4dc_qa_wxlu_mm) = mm;
        link_reply(id, true, "QA world rows opq=%s xlu=%s shell=%s", wm_opq_name(), wm_xlu_name(), wm_shell_name());
        return LA_NONE;
    }
    if (word_is(row, "WSHELL")) {
        const int s = word_is(v, "GAME") ? 0 : word_is(v, "ON") ? 1 : word_is(v, "OFF") ? 2 : -1;
        if (s < 0) { link_reply(id, false, "QA WSHELL needs GAME, ON or OFF"); return LA_NONE; }
        re4dc_qa_wshell = (unsigned) s;
        link_reply(id, true, "QA WSHELL %s", wm_shell_name());
        return LA_NONE;
    }
    if (word_is(row, "PVS")) {
        const int o = on_off(v);
        if (o < 0 || !re4dc_ps2_pvs_set) { link_reply(id, false, "QA PVS needs ON or OFF (and a PVS build)"); return LA_NONE; }
        re4dc_ps2_pvs_set((unsigned) o);
        link_reply(id, true, "QA PVS %s this boot", o ? "ON" : "OFF");
        return LA_NONE;
    }
#endif
#if defined(RE4DC_WORLD_SCRATCH) && RE4DC_WORLD_SCRATCH
    if (word_is(row, "WSCR")) {
        const int s = word_is(v, "A") ? 0 : word_is(v, "B") ? 1 : word_is(v, "C") ? 2 : -1;
        if (s < 0) { link_reply(id, false, "QA WSCR needs A, B or C"); return LA_NONE; }
        re4dc_world_scratch_live = (unsigned) s;
        link_reply(id, true, "QA WSCR %c", 'A' + s);
        return LA_NONE;
    }
#endif
    link_reply(id, false, "QA: unknown row %s", row);
    return LA_NONE;
}
// The full Diagnostics snapshot in parts (DIAG) / the rows only (telemetry).
void link_send_parts(char kind, const char* id, const char* text, int len) {
    constexpr int kPart = 1100;
    const int parts = len ? (len + kPart - 1) / kPart : 1;
    char b[kPart + 64];
    for (int p = 0; p < parts; ++p) {
        const int off = p * kPart, n = len - off < kPart ? len - off : kPart;
        const int h = kind == 'T' ? snprintf(b, sizeof(b), "T %u %u %d/%d\n", g_link.seq,
                                             (unsigned) (timer_ms_gettime64() & 0xFFFFFFFFu), p + 1, parts)
                                  : snprintf(b, sizeof(b), "D %s %d/%d\n", id, p + 1, parts);
        memcpy(b + h, text + off, n > 0 ? n : 0);
        if (kind == 'T') re4dc_qalink_send_bulk(b, (unsigned) (h + (n > 0 ? n : 0)));   // telemetry: skipped when backlogged
        else link_send_text(b, h + (n > 0 ? n : 0));
    }
}
int drive_row(char* out, int n);   // remote driving (below): Leon's room / position / facing / camera and the queue
void link_telemetry() {
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    if (g_fallback_telemetry.pending) return;
    const unsigned diag_page=g_diag_page;
#endif
    if (g_link.game) g_link.game();
    snap_diag();
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    g_diag_page=diag_page; // background telemetry must not reset the viewed page
#endif
    const char* rows = strchr(g_diag, '\n');   // the stats rows after "RE4DCQA1"
    rows = rows ? rows + 1 : g_diag;
    int n = g_diag_stats - (int) (rows - g_diag);
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    auto& t=g_fallback_telemetry.text;
#else
    static char t[sizeof(g_diag) + 160];
#endif
    if (n < 0) n = 0;
    memcpy(t, rows, n);
    unsigned tx, rx, dr, q;
    re4dc_qalink_counters(&tx, &rx, &dr, &q);
    n += snprintf(t + n, sizeof(t) - n, "link tx=%u rx=%u drops=%u queued=%u skips=%u cost_us_per_s=%u\n", tx, rx, dr,
                  q, re4dc_qalink_bulk_skips(), g_link.cost_last);
    n += drive_row(t + n, (int) sizeof(t) - n);
    ++g_link.seq;
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    g_fallback_telemetry.begin((unsigned)n,g_link.seq,(unsigned)timer_ms_gettime64());
#else
    link_send_parts('T', "", t, n);
#endif
}
void link_log() {   // new RAM log bytes since the last call, at most 640 a second
    const unsigned long head = re4dc_log_head, size = sizeof(re4dc_logbuf);
    if (!g_link.log_sent || head - g_link.log_sent > size) g_link.log_sent = head > size ? head - size : 0;
    unsigned long n = head - g_link.log_sent, dropped = 0;
    if (!n) return;
    if (n > 640) { dropped = n - 640; g_link.log_sent += dropped; n = 640; }
    char b[720];
    int h = snprintf(b, sizeof(b), "L %u %lu\n", ++g_link.log_seq, dropped);
    for (unsigned long i = 0; i < n; ++i) {
        const char c = re4dc_logbuf[(g_link.log_sent + i) % size];
        b[h++] = (c >= 32 && c < 127) || c == '\n' ? c : ' ';
    }
    g_link.log_sent += n;
    re4dc_qalink_send_bulk(b, (unsigned) h);   // skipped (those bytes are not sent) when backlogged
}
void record_flush() {
    if (g_link.rec_len) link_send_text(g_link.rec_line, g_link.rec_len);
    g_link.rec_len = 0;
}
void record_tick(uint64_t now_us) {
    if (!g_link.rec_left) return;
    const unsigned us = g_link.rec_prev_us ? (unsigned) (now_us - g_link.rec_prev_us) : 0;
    g_link.rec_prev_us = now_us;
    if (!us) return;   // the first tick has no previous one
    if (g_link.rec_n < sizeof(g_link.rec_us) / sizeof(g_link.rec_us[0])) g_link.rec_us[g_link.rec_n] = us;
    if (!g_link.rec_len)
        g_link.rec_len = snprintf(g_link.rec_line, sizeof(g_link.rec_line), "R %s %u\n", g_link.rec_id, g_link.rec_n);
    g_link.rec_len += snprintf(g_link.rec_line + g_link.rec_len, sizeof(g_link.rec_line) - g_link.rec_len, "%u,", us);
    ++g_link.rec_n;
    if (g_link.rec_n % 30 == 0) record_flush();
    if (--g_link.rec_left) return;
    record_flush();
    // summary: mean / p50 / p99 / max of the recorded ticks, then the phase rows (fps / ms10) of the Diagnostics page
    const unsigned n = g_link.rec_n < 1800 ? g_link.rec_n : 1800;
    unsigned* v = g_link.rec_us;
    for (unsigned i = 1; i < n; ++i) {   // insertion sort (<= 1800 values, once per RECORD)
        const unsigned x = v[i];
        unsigned j = i;
        for (; j && v[j - 1] > x; --j) v[j] = v[j - 1];
        v[j] = x;
    }
    unsigned long long sum = 0;
    for (unsigned i = 0; i < n; ++i) sum += v[i];
    if (g_link.game) g_link.game();
    snap_diag();
    char rows[400];
    int k = 0;
    rows[0] = 0;
    for (const char* p = g_diag; p && *p && p < g_diag + g_diag_stats;) {
        const char* e = strchr(p, '\n');
        const int len = e ? (int) (e - p) : (int) strlen(p);
        if ((!strncmp(p, "fps", 3) || !strncmp(p, "ms10", 4)) && k + len + 3 < (int) sizeof(rows))
            k += snprintf(rows + k, sizeof(rows) - k, " | %.*s", len, p);
        p = e ? e + 1 : nullptr;
    }
    link_reply(g_link.rec_id, true, "RECORD ticks=%u mean_us=%u p50_us=%u p99_us=%u max_us=%u%s", n,
               n ? (unsigned) (sum / n) : 0u, n ? v[n / 2] : 0u, n ? v[(n * 99) / 100 < n ? (n * 99) / 100 : n - 1] : 0u,
               n ? v[n - 1] : 0u, rows);
}
// ---------------------------------------------------------------- remote driving (lane linkpad28, user 10-28)
// PAD / GOTO / SCRIPT / MARK and TELEPORT POS: the PC moves Leon and cuts the session into sections. One queue of steps
// (PAD: buttons + stick for N ticks; GOTO: autopilot to x/z; MARK: a marker), applied at the game's pad read
// (platform/pad.cpp re4dc_qa_drive_pad, game thread) in free play only (no QA menu, movie, event, sub screen or door
// load; a step with ANY runs anywhere). Any real pad input (or a fixture press) cancels the queue at once and blocks
// driving for 3 s. The on-screen label "PC DRIVING" (the look label, native_static.cpp) shows while a step runs.
enum { DK_PAD, DK_GOTO, DK_MARK };
struct DriveStep {
    unsigned char kind, run, any, verb;   // verb: 'P' PAD, 'G' GOTO, 'S' SCRIPT
    unsigned short buttons, ticks;        // PAD: GameCube PAD_* bits, ticks; GOTO: timeout ticks
    signed char lx, ly;
    float x, z;
    char id[16];
    char label[40];                       // MARK label / SCRIPT name
};
struct Drive {
    DriveStep q[64];
    unsigned head, n;                     // ring
    unsigned done_ticks;                  // ticks spent on the head step
    bool feed, free_now;
    unsigned room;
    float x, y, z, ang, cam;
    uint64_t block_until_ms, cancel_ms;
    unsigned cancels;
    unsigned short ob;                    // GOTO output, applied at the next pad read
    signed char ox, oy;
    float chk_x, chk_z;                   // GOTO stuck check
    unsigned chk_t;
    bool tpos_pending;
    float tpos[4];
    bool tpos_ang;
    char tpos_id[16];
} g_drv;
const char* verb_name(unsigned char v) { return v == 'G' ? "GOTO" : v == 'S' ? "SCRIPT" : "PAD"; }
DriveStep* drv_head() { return g_drv.n ? &g_drv.q[g_drv.head % 64] : nullptr; }
bool drv_push(const DriveStep& s) {
    if (g_drv.n >= 64) return false;
    g_drv.q[(g_drv.head + g_drv.n) % 64] = s;
    ++g_drv.n;
    return true;
}
void drv_report(const DriveStep& s, const char* why) {
    link_reply(s.id, true, "%s DONE %s room=%03x pos=%d,%d,%d ang=%d/1000", verb_name(s.verb), why, g_drv.room,
               (int) g_drv.x, (int) g_drv.y, (int) g_drv.z, (int) (g_drv.ang * 1000.0f));
    re4dc_log("qadrive: %s %s DONE %s pos=%d,%d,%d\n", s.id, verb_name(s.verb), why, (int) g_drv.x, (int) g_drv.y,
              (int) g_drv.z);
}
// The head step finished (why = reason): pop it; when no later step shares its id, the command is DONE. A failed GOTO
// drops the rest of its command (a script stops where its walk failed).
void drv_pop(const char* why, bool fail) {
    DriveStep* h = drv_head();
    if (!h) return;
    const DriveStep s = *h;
    g_drv.head = (g_drv.head + 1) % 64;
    --g_drv.n;
    g_drv.done_ticks = 0;
    if (fail) while (g_drv.n && !strcmp(drv_head()->id, s.id)) { g_drv.head = (g_drv.head + 1) % 64; --g_drv.n; }
    if (!g_drv.n || strcmp(drv_head()->id, s.id)) drv_report(s, why);
}
void drv_clear(const char* why) {
    char last[16] = "";
    while (g_drv.n) {
        DriveStep* h = drv_head();
        if (strcmp(last, h->id)) { drv_report(*h, why); strcpy(last, h->id); }
        g_drv.head = (g_drv.head + 1) % 64;
        --g_drv.n;
    }
    g_drv.done_ticks = 0;
    g_drv.ob = 0; g_drv.ox = g_drv.oy = 0;
}
void drv_mark(const char* id, const char* label) {
    char b[96];
    const int k = snprintf(b, sizeof(b), "M %u %s", (unsigned) (timer_ms_gettime64() & 0xFFFFFFFFu), label);
    link_send_text(b, k < (int) sizeof(b) ? k : (int) sizeof(b) - 1);
    re4dc_log("qamark: %s\n", label);
    if (id) link_reply(id, true, "MARK %s", label);
}
float wrap_pi(float a) {
    while (a > 3.14159265f) a -= 6.2831853f;
    while (a < -3.14159265f) a += 6.2831853f;
    return a;
}
// GOTO, once per game tick (feed): the stick and buttons for the next pad read, or the step's end.
// RE4's tank controls: stick X turns Leon (right = clockwise from above = his angle falls), stick Y walks; B + forward runs.
void drv_goto_tick(DriveStep* s) {
    // A straight line, no path finding (user 10-28: teleport to exact spots; a human walks the rest). Under 0.3 m of
    // progress in 3 s = stuck.
    const float dx = s->x - g_drv.x, dz = s->z - g_drv.z, d = sqrtf(dx * dx + dz * dz);
    if (d < 500.0f) { drv_pop("arrived", false); return; }
    if (g_drv.done_ticks >= s->ticks) { drv_pop("timeout", true); return; }
    if (g_drv.done_ticks == 0) { g_drv.chk_t = 0; g_drv.chk_x = g_drv.x; g_drv.chk_z = g_drv.z; }
    if (g_drv.done_ticks - g_drv.chk_t >= 90) {
        const float mx = g_drv.x - g_drv.chk_x, mz = g_drv.z - g_drv.chk_z;
        if (mx * mx + mz * mz < 300.0f * 300.0f) { drv_pop("stuck", true); return; }
        g_drv.chk_x = g_drv.x; g_drv.chk_z = g_drv.z; g_drv.chk_t = g_drv.done_ticks;
    }
    const float err = wrap_pi(atan2f(dx, dz) - g_drv.ang);
    float sx = -err * 120.0f;   // stick right turns Leon clockwise (his angle falls); full rate from ~0.6 rad of error
    if (sx > 70.0f) sx = 70.0f;
    if (sx < -70.0f) sx = -70.0f;
    const float ae = err < 0 ? -err : err;
    g_drv.ox = (signed char) sx;
    g_drv.oy = ae > 0.7f ? 0 : d < 1500.0f ? 45 : 70;
    g_drv.ob = (s->run && ae < 0.3f && d > 2000.0f) ? 0x0200 : 0;   // PAD_BUTTON_B: run
}
// Button words: hex GameCube bits as the fixtures (0108), or names joined by '+' (A+B, UP, R+A, NONE).
bool parse_buttons(const char* w, unsigned short* out) {
    static const struct { const char* n; unsigned short b; } kN[] = {
        {"LEFT", 0x1}, {"RIGHT", 0x2}, {"DOWN", 0x4}, {"UP", 0x8}, {"Z", 0x10}, {"R", 0x20}, {"L", 0x40},
        {"A", 0x100}, {"B", 0x200}, {"X", 0x400}, {"Y", 0x800}, {"START", 0x1000}, {"NONE", 0}, {"-", 0}};
    char* e = nullptr;
    const unsigned long v = strtoul(w, &e, 16);
    if (e && !*e && *w) { *out = (unsigned short) v; return true; }
    unsigned short b = 0;
    char tmp[48];
    strncpy(tmp, w, sizeof(tmp) - 1);
    tmp[sizeof(tmp) - 1] = 0;
    char* sv = nullptr;
    for (char* t = strtok_r(tmp, "+", &sv); t; t = strtok_r(nullptr, "+", &sv)) {
        bool f = false;
        for (const auto& k : kN) if (!strcasecmp(t, k.n)) { b |= k.b; f = true; break; }
        if (!f) return false;
    }
    *out = b;
    return true;
}
int clamp_stick(int v) { return v > 72 ? 72 : v < -72 ? -72 : v; }
// SCRIPT <name>: /cd/dc/qa/pad/<name>.txt. Lines as the harness fixtures ("[+]frame buttons hold [state ...]": a
// press due `frame` ticks after the previous press starts, held `hold` ticks; state qualifiers are ignored here),
// plus "stick=<lx>,<ly>" on a press line, "goto <x> <z> [run] [timeout_s]", "mark <label>" and "wait <ticks>".
int drv_script(const char* id, const char* name, bool any) {
    char path[96];
    snprintf(path, sizeof(path), "/cd/dc/qa/pad/%s%s", name, strchr(name, '.') ? "" : ".txt");
    static char text[4096];
    const int len = re4dc_fixture_read(path, text, sizeof(text) - 1);
    if (len <= 0) return -1;
    text[len] = 0;
    int steps = 0;
    unsigned t = 0, last_start = 0;
    DriveStep s;
    for (char* line = text; line && *line;) {
        char* next = strchr(line, '\n');
        if (next) *next++ = 0;
        char* h = strchr(line, '#');
        if (h) *h = 0;
        char* sv = nullptr;
        char* w[8] = {};
        int nw = 0;
        for (char* tk = strtok_r(line, " \t\r", &sv); tk && nw < 8; tk = strtok_r(nullptr, " \t\r", &sv)) w[nw++] = tk;
        line = next;
        if (!nw || !strcmp(w[0], "clock")) continue;
        memset(&s, 0, sizeof(s));
        strncpy(s.id, id, sizeof(s.id) - 1);
        strncpy(s.label, name, sizeof(s.label) - 1);
        s.verb = 'S';
        s.any = any;
        if (!strcasecmp(w[0], "goto") && nw >= 3) {
            s.kind = DK_GOTO;
            s.x = (float) atof(w[1]); s.z = (float) atof(w[2]);
            s.run = nw >= 4 && !strcasecmp(w[3], "run");
            const int to = nw >= 4 ? atoi(w[nw - 1]) : 0;
            s.ticks = (unsigned short) ((to > 0 ? to : 20) * 30);
        } else if (!strcasecmp(w[0], "mark") && nw >= 2) {
            s.kind = DK_MARK;
            strncpy(s.label, w[1], sizeof(s.label) - 1);
        } else if (!strcasecmp(w[0], "wait") && nw >= 2) {
            s.kind = DK_PAD; s.ticks = (unsigned short) atoi(w[1]);
        } else if (nw >= 3) {
            const bool rel = w[0][0] == '+';
            const unsigned f = (unsigned) atoi(w[0] + rel);
            const unsigned start = rel ? last_start + f : f;
            if (start > t) {   // idle until the press is due
                DriveStep idle = s;
                idle.kind = DK_PAD; idle.ticks = (unsigned short) (start - t);
                if (!drv_push(idle)) return -2;
                ++steps;
                t = start;
            }
            s.kind = DK_PAD;
            if (!parse_buttons(w[1], &s.buttons)) continue;
            s.ticks = (unsigned short) atoi(w[2]);
            for (int k = 3; k < nw; ++k)
                if (!strncasecmp(w[k], "stick=", 6)) {
                    int lx = 0, ly = 0;
                    sscanf(w[k] + 6, "%d,%d", &lx, &ly);
                    s.lx = (signed char) clamp_stick(lx); s.ly = (signed char) clamp_stick(ly);
                }
            last_start = t;
            t += s.ticks;
        } else continue;
        if (!drv_push(s)) return -2;
        ++steps;
    }
    return steps;
}
// The command verbs. Returns true when `cmd` was one of them (answered here).
bool drive_command(const char* id, const char* cmd, char* rest, bool in_menu) {
    char* sv = nullptr;
    char* w[8] = {};
    int nw = 0;
    if (word_is(cmd, "MARK")) {
        drv_mark(id, rest && *rest ? rest : "-");
        return true;
    }
    if (!word_is(cmd, "PAD") && !word_is(cmd, "GOTO") && !word_is(cmd, "SCRIPT")) return false;
    char tmp[200];
    strncpy(tmp, rest ? rest : "", sizeof(tmp) - 1);
    tmp[sizeof(tmp) - 1] = 0;
    for (char* tk = strtok_r(tmp, " ", &sv); tk && nw < 8; tk = strtok_r(nullptr, " ", &sv)) w[nw++] = tk;
    bool any = false;
    if (nw && word_is(w[nw - 1], "ANY")) { any = true; --nw; }
    if (word_is(cmd, "PAD") && nw && word_is(w[0], "STOP")) {
        drv_clear("stopped");
        link_reply(id, true, "PAD STOP");
        return true;
    }
    const uint64_t now = timer_ms_gettime64();
    if (now < g_drv.block_until_ms) {
        link_reply(id, false, "%s: real pad input %u ms ago; driving blocked for 3 s", cmd,
                   (unsigned) (3000 - (g_drv.block_until_ms - now)));
        return true;
    }
    if (in_menu && !any) { link_reply(id, false, "%s: the QA menu is open (RESUME first, or add ANY)", cmd); return true; }
    DriveStep s;
    memset(&s, 0, sizeof(s));
    strncpy(s.id, id, sizeof(s.id) - 1);
    s.any = any;
    if (word_is(cmd, "PAD")) {
        // PAD <buttons> <lx> <ly> <ticks> [ANY]
        if (nw < 4 || !parse_buttons(w[0], &s.buttons)) {
            link_reply(id, false, "PAD <buttons> <lx> <ly> <ticks> [ANY] | PAD STOP");
            return true;
        }
        s.kind = DK_PAD; s.verb = 'P';
        s.lx = (signed char) clamp_stick(atoi(w[1])); s.ly = (signed char) clamp_stick(atoi(w[2]));
        const int t = atoi(w[3]);
        s.ticks = (unsigned short) (t < 1 ? 1 : t > 1800 ? 1800 : t);
        if (!drv_push(s)) { link_reply(id, false, "PAD: queue full (64 steps)"); return true; }
        link_reply(id, true, "PAD queued %04x stick=%d,%d ticks=%u steps=%u", s.buttons, s.lx, s.ly, s.ticks, g_drv.n);
        return true;
    }
    if (word_is(cmd, "GOTO")) {
        // GOTO <x> <z> [run] [timeout_s] [ANY]
        if (nw < 2) { link_reply(id, false, "GOTO <x> <z> [run] [timeout_s] [ANY]"); return true; }
        s.kind = DK_GOTO; s.verb = 'G';
        s.x = (float) atof(w[0]); s.z = (float) atof(w[1]);
        int to = 20;
        for (int k = 2; k < nw; ++k) { if (word_is(w[k], "RUN")) s.run = 1; else if (atoi(w[k]) > 0) to = atoi(w[k]); }
        s.ticks = (unsigned short) ((to > 60 ? 60 : to) * 30);
        if (!drv_push(s)) { link_reply(id, false, "GOTO: queue full"); return true; }
        const float dx = s.x - g_drv.x, dz = s.z - g_drv.z;
        link_reply(id, true, "GOTO started to %d,%d%s dist=%d timeout=%ds from %d,%d", (int) s.x, (int) s.z, s.run ? " run" : "",
                   (int) sqrtf(dx * dx + dz * dz), to, (int) g_drv.x, (int) g_drv.z);
        return true;
    }
    // SCRIPT <name> [ANY]
    if (!nw) { link_reply(id, false, "SCRIPT <name> (/cd/dc/qa/pad/<name>.txt)"); return true; }
    const unsigned before = g_drv.n;
    const int n = drv_script(id, w[0], any);
    if (n < 0) {
        while (g_drv.n > before) --g_drv.n;   // drop a half-queued script
        link_reply(id, false, n == -1 ? "SCRIPT: no /cd/dc/qa/pad/%s(.txt)" : "SCRIPT %s: more than 64 steps", w[0]);
        return true;
    }
    link_reply(id, true, "SCRIPT %s started steps=%d", w[0], n);
    return true;
}
// TELEPORT POS <x> <y> <z> [yaw]: Leon moved within this room at the next free-play tick (dbgwarp_bridge.cpp qa_poll,
// the warp rig's `goto` path: setPos / setAng).
bool tpos_command(const char* id, char* rest, bool in_menu) {
    float v[4] = {0, 0, 0, 0};
    const int n = rest ? sscanf(rest, "%*s %f %f %f %f", &v[0], &v[1], &v[2], &v[3]) : 0;
    if (n < 3) { link_reply(id, false, "TELEPORT POS <x> <y> <z> [yaw]"); return true; }
    if (in_menu) { link_reply(id, false, "TELEPORT POS: the QA menu is open (RESUME first)"); return true; }
    if (!g_drv.free_now) { link_reply(id, false, "TELEPORT POS: not in free play (movie, event, door or sub screen)"); return true; }
    memcpy(g_drv.tpos, v, sizeof(v));
    g_drv.tpos_ang = n >= 4;
    g_drv.tpos_pending = true;
    strncpy(g_drv.tpos_id, id, sizeof(g_drv.tpos_id) - 1);
    return true;
}
int drive_row(char* out, int n) {
    if (n <= 0) return 0;
    const DriveStep* h = g_drv.n ? &g_drv.q[g_drv.head % 64] : nullptr;
    const uint64_t now = timer_ms_gettime64();
    char st[64];
    if (now < g_drv.block_until_ms) snprintf(st, sizeof(st), "HOLD(real pad)");
    else if (!h) snprintf(st, sizeof(st), "IDLE");
    else if (h->kind == DK_GOTO)
        snprintf(st, sizeof(st), "GOTO %s to=%d,%d d=%d", h->id, (int) h->x, (int) h->z,
                 (int) sqrtf((h->x - g_drv.x) * (h->x - g_drv.x) + (h->z - g_drv.z) * (h->z - g_drv.z)));
    else snprintf(st, sizeof(st), "%s %s %04x %u/%u", verb_name(h->verb), h->id, h->buttons, g_drv.done_ticks, h->ticks);
    const int k = snprintf(out, n, "drv room=%03x pos=%d,%d,%d ang=%d cam=%d free=%d q=%u cancels=%u %s\n", g_drv.room,
                           (int) g_drv.x, (int) g_drv.y, (int) g_drv.z, (int) (g_drv.ang * 1000.0f),
                           (int) (g_drv.cam * 1000.0f), (int) g_drv.free_now, g_drv.n, g_drv.cancels, st);
    return k < 0 ? 0 : k >= n ? n - 1 : k;
}
// One command datagram. in_menu: the in-game menu is open (MENU / RESUME differ).
int link_command(char* line, bool in_menu) {
    char* save = nullptr;
    char* id = strtok_r(line, " \r\n", &save);
    char* cmd = id ? strtok_r(nullptr, " \r\n", &save) : nullptr;
    char* rest = save ? save + strspn(save, " ") : nullptr;
    if (rest) { char* e = rest + strlen(rest); while (e > rest && (e[-1] == '\n' || e[-1] == '\r' || e[-1] == ' ')) *--e = 0; }
    if (!id || !cmd) return LA_NONE;
    if (strlen(id) > 15) id[15] = 0;
    re4dc_log("qalink: cmd %s %s %s\n", id, cmd, rest ? rest : "");
    if (word_is(cmd, "PING") || word_is(cmd, "HELLO")) {
        link_reply(id, true, "PONG %s build=%s menu=%d", rest ? rest : "", RE4DC_QA_NAME, (int) in_menu);
        return LA_NONE;
    }
    if (word_is(cmd, "DIAG")) {
        if (g_link.game) g_link.game();
        snap_diag();
        link_send_parts('D', id, g_diag, g_diag_len);
        return LA_NONE;
    }
    if (word_is(cmd, "RECORD")) {
        const int n = rest ? atoi(rest) : 0;
        if (n <= 0 || n > 1800) { link_reply(id, false, "RECORD needs 1..1800 ticks"); return LA_NONE; }
        strncpy(g_link.rec_id, id, sizeof(g_link.rec_id) - 1);
        g_link.rec_left = (unsigned) n; g_link.rec_n = 0; g_link.rec_prev_us = 0; g_link.rec_len = 0;
        link_reply(id, true, "RECORD %d ticks started", n);
        return LA_NONE;
    }
    if (drive_command(id, cmd, rest, in_menu)) return LA_NONE;
    if (word_is(cmd, "TELEPORT") && rest && !strncasecmp(rest, "POS ", 4)) { tpos_command(id, rest, in_menu); return LA_NONE; }
    int act = LA_NONE;
    if (word_is(cmd, "QA")) {
        char* s2 = nullptr;
        char* row = rest ? strtok_r(rest, " ", &s2) : nullptr;
        char* val = row ? strtok_r(nullptr, " ", &s2) : nullptr;
        if (!row) { link_reply(id, false, "QA <row> <value>"); return LA_NONE; }
        act = link_qa_row(id, row, val ? val : "");
        if (act == LA_HEALTH) return in_menu ? LA_HEALTH : LA_HEALTH;
    } else if (word_is(cmd, "TELEPORT")) {
        load_presets();
        const int i = rest && *rest ? find_preset(rest) : -1;
        if (i < 0) { link_reply(id, false, "TELEPORT: no preset matches '%s' (%d presets)", rest ? rest : "", g_np); return LA_NONE; }
        snprintf(g_path, sizeof(g_path), "/cd/dc/qa/%s", g_p[i].file);
        re4dc_log("qa: teleport %s (%s) (link)\n", g_path, g_p[i].label);
        link_reply(id, true, "TELEPORT %s (%s)%s", g_p[i].file, g_p[i].label, in_menu ? "" : " at the next free-play tick");
        act = LA_TELEPORT;
    } else if (word_is(cmd, "MENU")) {
        if (in_menu) { link_reply(id, true, "MENU already open"); return LA_NONE; }
        link_reply(id, true, "MENU opens at the next free-play tick");
        act = LA_MENU;
    } else if (word_is(cmd, "RESUME")) {
        if (!in_menu) { link_reply(id, true, "RESUME: the menu is not open"); return LA_NONE; }
        link_reply(id, true, "RESUME");
        return LA_RESUME;
    } else {
        link_reply(id, false, "unknown command %s", cmd);
        return LA_NONE;
    }
    if (act == LA_TITLE) link_reply(id, true, "TITLE%s", in_menu ? "" : " at the next free-play tick");
    if (in_menu) return act;
    g_link.pending = act;   // TELEPORT / TITLE / MENU wait for free play
    strncpy(g_link.pending_id, id, sizeof(g_link.pending_id) - 1);
    return LA_NONE;
}
// Each pass: commands in, then once a second telemetry + log out. Returns an LA_ action for the caller.
int link_pump(bool in_menu) {
    const uint64_t t0 = timer_us_gettime64();
    if (!g_link.cfg_read) {
        link_read_cfg();
        if (g_link.auto_start) re4dc_qalink_start();
    }
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    if (!re4dc_qalink_up()) { g_fallback_telemetry.cancel(); return LA_NONE; }
#else
    if (!re4dc_qalink_up()) return LA_NONE;
#endif
    int act = LA_NONE;
    char buf[1400];
    for (int k = 0; k < 4 && act == LA_NONE && re4dc_qalink_recv(buf, sizeof(buf)) >= 0; ++k) act = link_command(buf, in_menu);
    const uint64_t ms = t0 / 1000;
    if (ms >= g_link.next_ms) {
        g_link.next_ms = ms + 1000;
        link_telemetry();
        link_log();
    }
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    g_fallback_telemetry.step(ms,[](const char* bytes,unsigned count){
        return re4dc_qalink_send_bulk(bytes,count);
    });
#endif
    const uint64_t t1 = timer_us_gettime64();
    g_link.cost_us += t1 - t0;
    if (t1 - g_link.cost_t0 >= 1000000) {
        g_link.cost_last = (unsigned) g_link.cost_us; g_link.cost_us = 0; g_link.cost_t0 = t1;
    }
    return act;
}
#endif

void draw_screen(const Fb& fb, const Menu& m);
// The screen, then a log line with the framebuffer for the harness captures (capture_ui_vram.py reads "fb=front,back" as
// KOS pointers: 0xa5000000 + 2 x the display offset).
void draw(const Fb& fb, const Menu& m) {
    draw_screen(fb, m);
    const unsigned long ptr = 0xa5000000ul + 2ul * ((unsigned long) fb.base & 0x007FFFFFul);
    re4dc_log("qa: screen %d fb=%08lx,%08lx\n", m.screen, ptr, ptr);
}
void draw_screen(const Fb& fb, const Menu& m) {
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    if (m.screen == M_CENSUS) { draw_census(fb, unsigned(m.census_page)); return; }
#endif
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
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        if (m.screen == M_CENSUS) {
#if defined(RE4DC_PERF_PHASE_MISS) && RE4DC_PERF_PHASE_MISS
            if (press & CONT_X) { re4dc::ppm14::run_controls(); dirty = true; }
#endif
            const int pages = int(census_pages(fb));
            if (press & (CONT_A | CONT_DPAD_RIGHT | CONT_DPAD_DOWN)) {
                m.census_page = (m.census_page + 1) % pages; dirty = true;
            } else if (press & (CONT_DPAD_LEFT | CONT_DPAD_UP)) {
                m.census_page = (m.census_page + pages - 1) % pages; dirty = true;
            }
        }
#endif
#if (defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT) || \
    (defined(RE4DC_ACTOR_LIGHT_FAST_ONLY) && RE4DC_ACTOR_LIGHT_FAST_ONLY) || \
    (defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT)
        if(m.screen==M_DIAG){
            const unsigned pages=diag_pages(fb);
            if(press&(CONT_DPAD_RIGHT|CONT_DPAD_DOWN)){
                g_diag_page=(g_diag_page+1)%pages;dirty=true;
            }else if(press&(CONT_DPAD_LEFT|CONT_DPAD_UP)){
                g_diag_page=(g_diag_page+pages-1)%pages;dirty=true;
            }
        }
#endif
        if (press & CONT_B) {
            dirty = true;
            if (m.screen == M_PRE) m.screen = M_CHAP;
            else if (m.screen == M_QR) m.screen = M_DIAG;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
            else if (m.screen == M_CENSUS) m.screen = M_MAIN;
#endif
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
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
                else if (a == A_CENSUS) { m.census_page = 0; m.screen = M_CENSUS; }
#endif
                else if (a == A_SHORE) { if (&re4dc_qa_shore_far_mm) re4dc_qa_shore_far_mm = re4dc_qa_shore_far_mm ? 0u : 30000u; }
#if defined(RE4DC_QA_LINK) && RE4DC_QA_LINK
                else if (a == A_LINK) link_toggle();
#endif
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
#if defined(RE4DC_QA_LINK) && RE4DC_QA_LINK
        if (!boot) {   // remote commands while the in-game menu holds the frame loop
            const int la = link_pump(true);
            if (la == LA_TELEPORT) return -1;
            if (la == LA_RESUME) return A_RESUME;
            if (la == LA_TITLE) return A_TITLE;
            if (la == LA_HEALTH) return A_HEALTH;
            if (la != LA_NONE || link_state_changed()) dirty = true;
        }
#endif
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

#if defined(RE4DC_QA_LINK) && RE4DC_QA_LINK
// The remote link's game-thread pass (dbgwarp_bridge.cpp qa_poll, every game tick). game() fills the Diagnostics
// page's game side (room, Ganados alive, heap 4); free_play = the in-game menu could open now. Returns 0 nothing,
// 1 teleport (*path), 2 quit to the title, 3 refill health, 4 open the in-game menu.
int re4dc_qa_link_tick(void (*game)(void), int free_play, const char** path) {
    g_link.game = game;
    const uint64_t now = timer_us_gettime64();
    int act = link_pump(false);
    if (re4dc_qalink_up()) record_tick(now);
    if (act == LA_HEALTH) return 3;
    if (!g_link.pending || !free_play) return 0;
    act = g_link.pending;
    g_link.pending = LA_NONE;
    re4dc_log("qalink: %s (command %s)\n", act == LA_TELEPORT ? "teleport" : act == LA_TITLE ? "quit to title" : "menu",
              g_link.pending_id);
    if (act == LA_TELEPORT) { *path = g_path; return 1; }
    return act == LA_TITLE ? 2 : 4;
}
// Remote driving, game side (dbgwarp_bridge.cpp qa_poll, every tick before re4dc_qa_link_tick): Leon's state and
// whether the game is in free play now. Runs the GOTO / MARK steps.
void re4dc_qa_drive_feed(unsigned room, float x, float y, float z, float ang, float cam, int free_play) {
    g_drv.feed = true;
    g_drv.room = room; g_drv.x = x; g_drv.y = y; g_drv.z = z; g_drv.ang = ang; g_drv.cam = cam;
    g_drv.free_now = free_play != 0;
    g_drv.ob = 0; g_drv.ox = g_drv.oy = 0;
    for (int guard = 0; guard < 8; ++guard) {
        DriveStep* h = drv_head();
        if (!h) return;
        if (h->kind == DK_MARK) { drv_mark(nullptr, h->label); drv_pop("marked", false); continue; }
        if (h->kind != DK_GOTO) return;
        if (!free_play && !h->any) return;   // paused (event, door, movie); resumes in free play
        drv_goto_tick(h);
        if (drv_head() == h && g_drv.n) { ++g_drv.done_ticks; return; }
    }
}
// TELEPORT POS, at the next free-play tick: 1 and the position (x y z yaw; *has_ang) when one is due.
int re4dc_qa_link_tpos(float* p, int* has_ang) {
    if (!g_drv.tpos_pending || !g_drv.free_now) return 0;
    g_drv.tpos_pending = false;
    memcpy(p, g_drv.tpos, sizeof(g_drv.tpos));
    *has_ang = g_drv.tpos_ang;
    link_reply(g_drv.tpos_id, true, "TELEPORT POS %d,%d,%d%s from %d,%d,%d room=%03x", (int) p[0], (int) p[1], (int) p[2],
               *has_ang ? " yaw set" : "", (int) g_drv.x, (int) g_drv.y, (int) g_drv.z, g_drv.room);
    return 1;
}
// platform/pad.cpp PADRead, port A, after the mapping: real = any real button / stick past 24 / fixture press. A real
// input cancels driving (3 s block); otherwise the head step's buttons and stick go in.
void re4dc_qa_drive_pad(unsigned short* buttons, signed char* sx, signed char* sy, unsigned char* trig_r, int real) {
    if (real) {
        if (g_drv.n) {
            ++g_drv.cancels;
            re4dc_log("qadrive: real pad input: driving cancelled (%u steps)\n", g_drv.n);
            drv_clear("cancelled by real pad");
            g_drv.cancel_ms = timer_ms_gettime64();
        }
        const uint64_t until = timer_ms_gettime64() + 3000;
        if (g_drv.block_until_ms < until) g_drv.block_until_ms = until;
        return;
    }
    DriveStep* h = drv_head();
    if (!h || (!g_drv.free_now && !h->any)) {
        // a PAD press interrupted by an event / door / movie ends there (no stale press after it)
        if (h && h->kind == DK_PAD && g_drv.done_ticks) drv_pop("ended by an event", false);
        return;
    }
    unsigned short b;
    signed char x, y;
    if (h->kind == DK_GOTO) { b = g_drv.ob; x = g_drv.ox; y = g_drv.oy; }
    else if (h->kind == DK_PAD) {
        b = h->buttons; x = h->lx; y = h->ly;
        if (++g_drv.done_ticks >= h->ticks) drv_pop("ok", false);
    } else return;
    *buttons |= b;
    if (x) *sx = x;
    if (y) *sy = y;
    if ((b & 0x20) && !*trig_r) *trig_r = 0xC0;   // R: the analog trigger the aim reads
}
// native_static.cpp re4dc_look_osd_text: the on-screen label while the PC drives (or holds after a real press).
const char* re4dc_qa_drive_osd_text(void) {
    if (g_drv.cancels && timer_ms_gettime64() < g_drv.cancel_ms + 3000) return "PC DRIVE: HOLD (PAD PRESSED)";
    return g_drv.n ? "PC DRIVING (QA LINK)" : nullptr;
}
#endif

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
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    re4dc::dsa24::pause();
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    re4dc::dfa26::pause();
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    re4dc::wc24::pause();
#endif
    static Menu m;
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    const int items[] = {A_RESUME, A_TELEPORT_MENU, A_DIAG, QA_CENSUS_ROW A_HEALTH, A_LEON, A_PARTNER, A_ENEMY, A_SPEED, A_SHORE,
                         A_WOPQ, A_WXLU, A_WSHELL, QA_LINK_ROW QA_WS_ROW A_TITLE};
#else
    const int items[] = {A_RESUME, A_TELEPORT_MENU, A_DIAG, QA_CENSUS_ROW A_HEALTH, A_LEON, A_PARTNER, A_ENEMY, A_SPEED, A_SHORE, QA_LINK_ROW QA_WS_ROW A_TITLE};
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
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        const unsigned pages = census_pages(fb_displayed());
        for (unsigned pg = 0; pg < pages; ++pg) {
            m.screen = M_CENSUS; m.census_page = int(pg);
            draw(fb_displayed(), m);
            re4dc_log("qa: auto world census page %u/%u\n", pg + 1, pages);
            for (unsigned t = 0; t < hold_ms; t += 16) spin_us(16000);
        }
#endif
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
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    re4dc::wc24::resume();
#endif
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    re4dc::dsa24::resume();
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    re4dc::dfa26::resume();
#endif
    if (!file || !file[0]) return 0;
    snprintf(g_path, sizeof(g_path), "/cd/dc/qa/%s", file);
    re4dc_log("qa: auto teleport %s\n", g_path);
    *path = g_path;
    return 1;
}

// In-game menu (the warp rig's poll, frame loop stopped). 0 resume, 1 teleport (*path), 2 title, 3 refill health.
int re4dc_qa_menu(const char** path) {
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    re4dc::dsa24::pause();
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    re4dc::dfa26::pause();
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    re4dc::wc24::pause();
#endif
    static Menu m;
    m.boot = false;
    if (m.screen != M_MAIN) m.screen = M_MAIN;
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    const int items[] = {A_RESUME, A_TELEPORT_MENU, A_DIAG, QA_CENSUS_ROW A_HEALTH, A_LEON, A_PARTNER, A_ENEMY, A_SPEED, A_SHORE,
                         A_WOPQ, A_WXLU, A_WSHELL, QA_LINK_ROW QA_WS_ROW A_TITLE};
#else
    const int items[] = {A_RESUME, A_TELEPORT_MENU, A_DIAG, QA_CENSUS_ROW A_HEALTH, A_LEON, A_PARTNER, A_ENEMY, A_SPEED, A_SHORE, QA_LINK_ROW QA_WS_ROW A_TITLE};
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
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    re4dc::wc24::resume();
#endif
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    re4dc::dsa24::resume();
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    re4dc::dfa26::resume();
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
