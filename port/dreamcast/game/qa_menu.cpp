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
#include <stdio.h>
#include <string.h>
#include <stdint.h>

extern "C" {
void re4dc_log(const char* fmt, ...);
int re4dc_fixture_read(const char* path, char* buffer, unsigned size);
void __real_OSInit(void);
int re4dc_quality_speed(void);      // platform/quality.cpp: 0 off, 1 VMU, 2 screen, 3 both
void re4dc_speed_cycle(void);       // pace.cpp
}

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

// ---------------------------------------------------------------- menu
enum { M_MAIN, M_CHAP, M_PRE };
enum { A_RESUME, A_TELEPORT_MENU, A_HEALTH, A_LEON, A_PARTNER, A_ENEMY, A_SPEED, A_TITLE, A_NORMAL };
struct Menu {
    bool boot;
    int screen, sel[3], chap;
    int items[10], nitems;
};
const char* onoff(unsigned bit) { return (g_flags & bit) ? "ON" : "OFF"; }
const char* speed_name() {
    static const char* const k[4] = {"OFF", "VMU", "SCREEN", "VMU + SCREEN"};
    return k[re4dc_quality_speed() & 3];
}
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
    default: out[0] = 0;
    }
}
int presets_of(int ch, int* idx) {
    int n = 0;
    for (int i = 0; i < g_np; ++i)
        if (g_p[i].ch == ch) idx[n++] = i;
    return n;
}
void draw(const Fb& fb, const Menu& m) {
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
            else if (m.screen == M_CHAP) m.screen = M_MAIN;
            else if (!boot) return A_RESUME;
        }
        if ((press & CONT_START) && m.screen == M_MAIN && !boot) return A_RESUME;
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
                else if (a == A_SPEED) re4dc_speed_cycle();
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

// In-game menu (the warp rig's poll, frame loop stopped). 0 resume, 1 teleport (*path), 2 title, 3 refill health.
int re4dc_qa_menu(const char** path) {
    static Menu m;
    m.boot = false;
    if (m.screen != M_MAIN) m.screen = M_MAIN;
    const int items[] = {A_RESUME, A_TELEPORT_MENU, A_HEALTH, A_LEON, A_PARTNER, A_ENEMY, A_SPEED, A_TITLE};
    m.nitems = 8;
    memcpy(m.items, items, sizeof(items));
    re4dc_log("qa: menu open\n");
    const int a = run(m, false);
    wait_release();
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
