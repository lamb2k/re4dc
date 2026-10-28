/* dc-qalink example: dials at boot, sends one telemetry row a second, answers PING (built in), ECHO and GOTO, and
 * draws a tiny QA menu: a list of jump-to presets (pad: up/down + A to jump, X to hang up or redial) and a status line
 * that follows the link through its states. BIOS font straight into the framebuffer; no PVR, no assets. MIT licence.
 *
 * Build-time settings (make CFLAGS_EXTRA=...): -DEX_HOST=\"10.0.0.1\" (relay address, default: learn the peer)
 * -DEX_LPORT=52042 (console port; use a different port from the relay's under Flycast's modem emulation). */
#include <kos.h>
#include <dc/biosfont.h>
#include <dc/maple/controller.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include "dcql.h"

#ifndef EX_HOST
#define EX_HOST "peer"
#endif
#ifndef EX_LPORT
#define EX_LPORT 52040
#endif

/* The host program's presets: whatever "jump to" means for it (a level, a room, a camera, a test scene). */
typedef struct { const char* name; unsigned short colour; } preset_t;
static const preset_t g_presets[] = {
    {"title", 0x0010}, {"level1-start", 0x0200}, {"level1-boss", 0x4000}, {"stress-500-sprites", 0x4208},
};
enum { kPresets = sizeof(g_presets) / sizeof(g_presets[0]) };
static int g_cursor, g_scene;
static unsigned g_frame, g_jumps;
static int g_hangup_in;
static unsigned g_frame_1s;

static int jump_to(const char* name) {
    for (int i = 0; i < kPresets; ++i)
        if (!strcasecmp(name, g_presets[i].name) || (name[0] >= '0' && name[0] <= '9' && atoi(name) == i)) {
            g_scene = g_cursor = i;
            ++g_jumps;
            char m[64];
            snprintf(m, sizeof(m), "goto:%s", g_presets[i].name);
            dcql_mark(m);
            return 1;
        }
    return 0;
}

static int on_command(const char* id, const char* verb, const char* args, void* user) {
    (void) user;
    if (!strcmp(verb, "ECHO")) return dcql_answer(id, 1, "%s", args), 1;
    if (!strcmp(verb, "GOTO")) {
        if (jump_to(args)) dcql_answer(id, 1, "GOTO %s", g_presets[g_scene].name);
        else dcql_answer(id, 0, "no preset '%s'", args);
        return 1;
    }
    if (!strcmp(verb, "HANGUP")) { dcql_answer(id, 1, "hanging up"); g_hangup_in = 30; return 1; }  /* let the answer leave first */
    if (!strcmp(verb, "PRESETS")) {
        char b[512];
        int k = 0;
        for (int i = 0; i < kPresets && k < (int) sizeof(b) - 40; ++i)
            k += snprintf(b + k, sizeof(b) - k, "%d=%s;", i, g_presets[i].name);
        return dcql_answer(id, 1, "%s", b), 1;
    }
    return 0; /* the library answers "ERR unknown <verb>" */
}

static void on_log(const char* line) { printf("%s\n", line); }

/* opaque, padded to a fixed width, so a line is overwritten in place and the screen never needs clearing */
static void text(int x, int y, const char* s) {
    char b[50];
    snprintf(b, sizeof(b), "%-48s", s);
    bfont_draw_str(vram_s + y * 640 + x, 640, 1, b);
}

static void draw(void) {
    static int drawn_scene = -1;
    if (drawn_scene != g_scene) { /* clear only when the scene changes */
        drawn_scene = g_scene;
        const unsigned short bg = g_presets[g_scene].colour;
        for (int i = 0; i < 640 * 480; ++i) vram_s[i] = bg;
    }
    text(32, 24, "dc-qalink example");
    char b[96];
    snprintf(b, sizeof(b), "scene: %s   frame %u", g_presets[g_scene].name, g_frame);
    text(32, 56, b);
    text(32, 104, "JUMP TO (up/down, A)");
    for (int i = 0; i < kPresets; ++i) {
        snprintf(b, sizeof(b), "%c %d %s", i == g_cursor ? '>' : ' ', i, g_presets[i].name);
        text(48, 136 + i * 28, b);
    }
    /* status line: OFF / DIALLING n/3 / PPP / UP ip TO peer / FAILED / LINE DROPPED / HANGING UP */
    char st[64];
    dcql_state_text(st, sizeof(st));
    dcql_counters_t c;
    dcql_counters(&c);
    const dcql_state_t s = dcql_state();
    const char* hint = s == DCQL_UP ? "X: hang up" : (s == DCQL_OFF || s == DCQL_FAILED || s == DCQL_DROPPED) ?
                       "X: dial" : "";
    snprintf(b, sizeof(b), "LINK %s", st);
    text(32, 400, b);
    if (s == DCQL_UP) snprintf(b, sizeof(b), "rows out %u B  in %u B  skips %u  %s", c.tx_bytes, c.rx_bytes,
                               c.bulk_skips, hint);
    else snprintf(b, sizeof(b), "%s", hint);
    text(32, 428, b);
}

int main(int argc, char** argv) {
    (void) argc; (void) argv;
    vid_set_mode(DM_640x480, PM_RGB565);
    dcql_config_t cfg = {0};
    cfg.host = EX_HOST;
    cfg.lport = EX_LPORT;
    cfg.log = on_log;
    dcql_config(&cfg);
    dcql_set_command(on_command, NULL);
    dcql_start();
    uint32_t prev = 0;
    uint64_t next_t = timer_ms_gettime64() + 1000;
    for (;;) {
        vid_waitvbl();
        ++g_frame;
        dcql_poll();
        if (g_hangup_in && !--g_hangup_in) dcql_stop();
        maple_device_t* pad = maple_enum_type(0, MAPLE_FUNC_CONTROLLER);
        cont_state_t* ps = pad ? (cont_state_t*) maple_dev_status(pad) : NULL;
        const uint32_t btn = ps ? ps->buttons : 0, hit = btn & ~prev;
        prev = btn;
        if (hit & CONT_DPAD_UP) g_cursor = (g_cursor + kPresets - 1) % kPresets;
        if (hit & CONT_DPAD_DOWN) g_cursor = (g_cursor + 1) % kPresets;
        if (hit & CONT_A) { char n[8]; snprintf(n, sizeof(n), "%d", g_cursor); jump_to(n); }
        if (hit & CONT_X) { if (dcql_state() == DCQL_UP) dcql_stop(); else dcql_start(); }
        if (timer_ms_gettime64() >= next_t) {
            next_t += 1000;
            char t[128];
            dcql_counters_t c;
            dcql_counters(&c);
            snprintf(t, sizeof(t), "frame fps=%u scene=%d jumps=%u\nlink queued=%u skips=%u\n", g_frame - g_frame_1s,
                     g_scene, g_jumps, c.queued, c.bulk_skips);
            g_frame_1s = g_frame;
            dcql_telemetry(t);
        }
        draw();
    }
    return 0;
}
