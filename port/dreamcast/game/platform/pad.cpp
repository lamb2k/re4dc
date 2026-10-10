// Controller interface over maple: the four GameCube channels map to the four
// Dreamcast ports; each controller fills the PADStatus the game's PadRead
// (src/game/pad.cpp) translates into its JOY words (mapping: re4dcMapPad).
#include <kos.h>
#include <dc/maple.h>
#include <dc/maple/controller.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#include "re4dc_platform.h"
#include "re4dc_pad_prompts.h"
#include "re4dc_manual_pages.h"
#if RE4DC_VMU_DEBUG_SLOT
extern "C" unsigned re4dc_dbgslot_pad(unsigned buttons);  // dbgslot_bridge.cpp
#endif
#if RE4DC_DBG_WARP
extern "C" void re4dc_warp_pad(unsigned short* buttons, signed char* stickY);  // dbgwarp_bridge.cpp
#endif

typedef signed char s8;
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned long u32;
typedef int BOOL;

struct PADStatus {
    u16 button;
    s8 stickX, stickY, substickX, substickY;
    u8 triggerLeft, triggerRight, analogA, analogB;
    s8 err;
    u8 pad_B;
};

enum {
    PAD_BUTTON_LEFT = 0x0001, PAD_BUTTON_RIGHT = 0x0002, PAD_BUTTON_DOWN = 0x0004, PAD_BUTTON_UP = 0x0008,
    PAD_TRIGGER_Z = 0x0010, PAD_TRIGGER_R = 0x0020, PAD_TRIGGER_L = 0x0040,
    PAD_BUTTON_A = 0x0100, PAD_BUTTON_B = 0x0200, PAD_BUTTON_X = 0x0400, PAD_BUTTON_Y = 0x0800, PAD_BUTTON_START = 0x1000,
};
enum { PAD_ERR_NONE = 0, PAD_ERR_NO_CONTROLLER = -1 };

// ---- Controller mapping (platform adapter only) ----------------------------
// The game's PadRead / Key_type_tbl stay source-authoritative: this layer only
// decides which GameCube PADStatus a Dreamcast controller produces.
//
// Ranges: the GameCube SDK's PADClamp (called by PadRead right after PADRead)
// leaves stick 0..72 (octagon corner 40), C-stick 0..59 (corner 31) and
// triggers 0..150, each past a 15 / 15 / 30 dead zone; game code is tuned to
// those numbers (cam_qfps C_RANGE 59, pl0f /72, PadRead's 30-unit direction
// threshold, and any nonzero analog trigger counts as L / R held). Maple axes
// (-128..127) are scaled to the GameCube's raw span (about +-100) and pushed
// through the same clamp here, so PADClamp itself stays a no-op.
//
// Pad kinds (per port, like dca3-game's IsDualAnalog):
//   dual   - the device advertises a second analog stick or C / Z buttons
//            (twin-analog pads, arcade sticks), or reports second-stick axes
//            beyond +-64 on two consecutive polls, or a C / Z press is seen.
//            Native: joy2 -> C-stick, C or Z -> Z, D-pad -> D-pad.
//   standard - A/B/X/Y/Start, stick, triggers as on the GameCube; the D-pad
//            (a pure duplicate of the stick in Key_type_tbl) is reused by
//            game context (re4dc_pad_context, port/dreamcast/game/ui_bridge.cpp):
//     LOOK   free movement, where CameraQuasiFPS reads Key.substick: the
//            D-pad is an 8-way C-stick (59 cardinal, 31/31 diagonal: a fully
//            deflected GameCube C-stick after PADClamp) and sends no D-pad
//            bits. A lone D-pad-down tap (released within Z_TAP_POLLS polls,
//            no other direction) sends Z (map) for Z_PULSE_POLLS polls.
//     ZOOM   rifle scope / binoculars (Status_flg[0] 0x40 / 0x400), where the
//            C-stick Y zooms: D-pad up / down -> C-stick Y +-ZOOM_MAG, left /
//            right stay D-pad (fine pan).
//     NATIVE everything else (menus, sub screen, aiming, knife, events, QTEs):
//            D-pad -> D-pad, no C-stick, no Z.
//
// Debug chords the source leaves live on pad 0 are blocked here by default
// (re4dcBlockDebugChords; RE4DC_DEBUG_PAD=1, Makefile DEBUG_PAD=1, restores them):
//   L + START  gameDebug (game.cpp) opens DbMenuExec whenever Debug_flg[0]
//              bit 31 is clear: START is masked for a press that starts with
//              L held, only while that flag would open the menu (options stay
//              closed with L held anyway: gameMainLoop tests !Key 0x400000).
//   Z          inside the sub screen (any open type except the Z-opened map,
//              where Z closes it) the raw Joy Z toggles the item-make / puzzle
//              debug menus (ss_item.cpp SsItemMain::move, ss_pzzl.cpp): masked.
// Fixture (padscript) bits are ORed in after both and are never filtered.
// Cost: a few dozen integer ops per port per frame plus two field-read calls.
enum { RE4DC_PAD_CTX_NATIVE = 0, RE4DC_PAD_CTX_LOOK = 1, RE4DC_PAD_CTX_ZOOM = 2 };
enum { RE4DC_PAD_DBG_MENU = 1, RE4DC_PAD_DBG_SUBSCREEN_Z = 2 };  // re4dc_pad_debug_state bits
enum { LOOK_MAG = 59, LOOK_DIAG = 31, ZOOM_MAG = 30, Z_TAP_POLLS = 10, Z_PULSE_POLLS = 2, DUAL_AXIS = 64 };
#ifndef RE4DC_DEBUG_PAD
#define RE4DC_DEBUG_PAD 0
#endif

struct Re4dcPadIn { u32 buttons; int ltrig, rtrig, joyx, joyy, joy2x, joy2y; };  // maple units, joyy grows downward
struct Re4dcPadMap { u8 dual, dualVotes, tapPolls, tapClean, zPulse, startHeld, startBlocked; };

// Dolphin SDK ClampStick: dead zone `min`, octagon of radius `max` with corner `xy`.
static void gcClampStick(int* px, int* py, int max, int xy, int min)
{
    int x = *px, y = *py, sx = 1, sy = 1, d;
    if (x < 0) { sx = -1; x = -x; }
    if (y < 0) { sy = -1; y = -y; }
    x = x <= min ? 0 : x - min;
    y = y <= min ? 0 : y - min;
    if (x == 0 && y == 0) { *px = *py = 0; return; }
    d = xy * y <= xy * x ? xy * x + (max - xy) * y : xy * y + (max - xy) * x;
    if (xy * max < d) {
        x = xy * max * x / d;
        y = xy * max * y / d;
    }
    *px = sx * x;
    *py = sy * y;
}

static int gcRaw(int maple) { return maple * 100 / 128; }  // maple -128..127 -> GameCube raw -100..99

static u8 gcClampTrigger(int t)  // SDK ClampTrigger(30, 180)
{
    if (t <= 30) return 0;
    if (t > 180) t = 180;
    return (u8) (t - 30);
}

static u16 gcDpad(u32 buttons)
{
    u16 b = 0;
    if (buttons & CONT_DPAD_UP) b |= PAD_BUTTON_UP;
    if (buttons & CONT_DPAD_DOWN) b |= PAD_BUTTON_DOWN;
    if (buttons & CONT_DPAD_LEFT) b |= PAD_BUTTON_LEFT;
    if (buttons & CONT_DPAD_RIGHT) b |= PAD_BUTTON_RIGHT;
    return b;
}

// One poll of one port: `in` (maple), `ctx` (RE4DC_PAD_CTX_*), `capsDual` (the
// device advertises C / Z / a second stick) -> button, sticks and triggers of `p`.
static void re4dcMapPad(const Re4dcPadIn* in, int ctx, int capsDual, Re4dcPadMap* m, PADStatus* p)
{
    const u32 dirs = CONT_DPAD_UP | CONT_DPAD_DOWN | CONT_DPAD_LEFT | CONT_DPAD_RIGHT;
    u32 dpad = in->buttons & dirs;
    u16 b = 0;
    int sx, sy, cx = 0, cy = 0;

    if (!m->dual) {
        if (capsDual || (in->buttons & (CONT_C | CONT_Z))) {
            m->dual = 1;
        } else if (in->joy2x > DUAL_AXIS || in->joy2x < -DUAL_AXIS || in->joy2y > DUAL_AXIS || in->joy2y < -DUAL_AXIS) {
            if (++m->dualVotes >= 2) m->dual = 1;
        } else {
            m->dualVotes = 0;
        }
    }

    if (in->buttons & CONT_A) b |= PAD_BUTTON_A;
    if (in->buttons & CONT_B) b |= PAD_BUTTON_B;
    if (in->buttons & CONT_X) b |= PAD_BUTTON_X;
    if (in->buttons & CONT_Y) b |= PAD_BUTTON_Y;
    if (in->buttons & CONT_START) b |= PAD_BUTTON_START;
    p->triggerLeft = gcClampTrigger(in->ltrig);
    p->triggerRight = gcClampTrigger(in->rtrig);
    if (p->triggerLeft) b |= PAD_TRIGGER_L;    // PadRead ORs JOY_L / JOY_R for any nonzero analog value anyway
    if (p->triggerRight) b |= PAD_TRIGGER_R;
    sx = gcRaw(in->joyx);
    sy = -gcRaw(in->joyy);                     // maple Y grows downward, the GameCube stick upward
    gcClampStick(&sx, &sy, 72, 40, 15);

    if (m->dual) {
        cx = gcRaw(in->joy2x);
        cy = -gcRaw(in->joy2y);
        gcClampStick(&cx, &cy, 59, 31, 15);
        if (in->buttons & (CONT_C | CONT_Z)) b |= PAD_TRIGGER_Z;   // six-button pads: C = Z
        b |= gcDpad(dpad);
        m->tapPolls = 0;
        m->tapClean = 0;
        m->zPulse = 0;
    } else {
        if (ctx == RE4DC_PAD_CTX_LOOK) {
            int dx = ((dpad & CONT_DPAD_RIGHT) != 0) - ((dpad & CONT_DPAD_LEFT) != 0);
            int dy = ((dpad & CONT_DPAD_UP) != 0) - ((dpad & CONT_DPAD_DOWN) != 0);
            int mag = dx && dy ? LOOK_DIAG : LOOK_MAG;
            cx = dx * mag;
            cy = dy * mag;
        } else if (ctx == RE4DC_PAD_CTX_ZOOM) {
            cy = (dpad & CONT_DPAD_UP) ? ZOOM_MAG : (dpad & CONT_DPAD_DOWN) ? -ZOOM_MAG : 0;
            b |= gcDpad(dpad & (CONT_DPAD_LEFT | CONT_DPAD_RIGHT));
        } else {
            b |= gcDpad(dpad);
        }
        // Z: a lone D-pad-down tap, every poll of it in LOOK.
        if (dpad == 0) {
            if (m->tapClean && m->tapPolls && m->tapPolls <= Z_TAP_POLLS) m->zPulse = Z_PULSE_POLLS;
            m->tapPolls = 0;
            m->tapClean = 1;
        } else if (dpad == CONT_DPAD_DOWN && ctx == RE4DC_PAD_CTX_LOOK && m->tapClean) {
            if (m->tapPolls < 255) m->tapPolls++;
        } else {
            m->tapClean = 0;
        }
        if (m->zPulse) {
            m->zPulse--;
            b |= PAD_TRIGGER_Z;
        }
    }
    p->button = b;
    p->stickX = (s8) sx;
    p->stickY = (s8) sy;
    p->substickX = (s8) cx;
    p->substickY = (s8) cy;
}

// Pad 0's mapped buttons with the source's debug chords removed (`dbg`: RE4DC_PAD_DBG_* from
// re4dc_pad_debug_state). A START press that begins with L held stays masked until released.
static u16 re4dcBlockDebugChords(u16 b, int dbg, Re4dcPadMap* m)
{
    if (b & PAD_BUTTON_START) {
        if (!m->startHeld && (dbg & RE4DC_PAD_DBG_MENU) && (b & PAD_TRIGGER_L)) m->startBlocked = 1;
        m->startHeld = 1;
    } else {
        m->startHeld = 0;
        m->startBlocked = 0;
    }
    if (m->startBlocked) b &= (u16) ~PAD_BUTTON_START;
    if (dbg & RE4DC_PAD_DBG_SUBSCREEN_Z) b &= (u16) ~PAD_TRIGGER_Z;
    return b;
}


// Scripted input fixture: /cd/dc/padscript.txt lists
//   frame buttons hold [state=value [timeout]]
// per line: the retrace count at which the press becomes due ("+N" = N frames
// after the previous delivered press), GameCube PAD_* button bits in hex,
// frames held, and optionally the game state the press is meant for. A
// qualified press is delivered at the first due frame at which the named
// state holds and is dropped (logged) once `timeout` frames (default 600)
// pass without it, so the script never pushes a button into the wrong
// screen. Game code reports its states through re4dc_fixture_state (card
// screen, title state); every transition and every delivered or dropped
// press is logged with its frame, separately from real controller input.
// An optional first directive "clock source" uses pG->Frame_cnt for due/hold/
// timeout scheduling. Absolute entries then align boot fixtures across renderer
// variants without changing the game's counter, tasks or state. State-transition
// logs still report retraces; the script load explicitly labels its own clock.
// /cd/dc/diag.txt switches on the heavy periodic diagnostics (thread dumps).
struct PadScriptEntry { u32 frame; u16 buttons; u16 hold; int relative; char state[16]; int value_a, value_b; u32 timeout; int done; };
static PadScriptEntry g_script[64];
static int g_scriptCount = -1;  // -1: not loaded yet
static u32 g_lastDelivered;
static bool g_scriptSourceClock; // opt-in fixture clock; never modifies source time
static int g_scriptActive = -1;   // entry currently held down

struct FixtureState { char name[16]; int a, b; };
static FixtureState g_states[8];
static int g_stateCount;
int re4dc_diag;

extern "C" u32 re4dc_vi_retrace_count(void);
extern "C" unsigned re4dc_fixture_source_frame(void);

extern "C" void re4dc_fixture_state(const char* name, int a, int b)
{
    int i;
    for (i = 0; i < g_stateCount; i++) {
        if (strcmp(g_states[i].name, name) == 0) break;
    }
    if (i == g_stateCount) {
        if (g_stateCount >= 8) return;
        g_stateCount++;
        strncpy(g_states[i].name, name, 15);
        g_states[i].a = -1;
        g_states[i].b = -1;
    }
    if (g_states[i].a == a && g_states[i].b == b) return;
    g_states[i].a = a;
    g_states[i].b = b;
    if (b >= 0) re4dc_log("fixture: state %s=%d/%d at frame %lu" "\n", name, a, b, (unsigned long) re4dc_vi_retrace_count());
    else re4dc_log("fixture: state %s=%d at frame %lu" "\n", name, a, (unsigned long) re4dc_vi_retrace_count());
}

static int stateHolds(const PadScriptEntry* e)
{
    if (!e->state[0]) return 1;
    for (int i = 0; i < g_stateCount; i++) {
        if (strcmp(g_states[i].name, e->state) == 0) {
            return g_states[i].a == e->value_a && (e->value_b < 0 || g_states[i].b == e->value_b);
        }
    }
    return 0;
}

static void loadScript(void)
{
    g_scriptCount = 0;
    file_t d = fs_open("/cd/dc/diag.txt", O_RDONLY);
    if (d >= 0) {
        fs_close(d);
        re4dc_diag = 1;
        re4dc_log("fixture: /cd/dc/diag.txt present, periodic diagnostics on" "\n");
    }
    file_t f = fs_open("/cd/dc/padscript.txt", O_RDONLY);
    if (f < 0) return;
    static char text[4096];
    ssize_t n = fs_read(f, text, sizeof(text) - 1);
    fs_close(f);
    if (n <= 0) return;
    text[n] = 0;
    char* line = text;
    while (line && *line && g_scriptCount < 64) {
        char* next = strchr(line, '\n');
        if (next) *next++ = 0;
        while (*line == ' ' || *line == '\t') line++;
        char* hash = strchr(line, '#');
        if (hash) *hash = 0;
        char* end = line + strlen(line);
        while (end > line && (end[-1] == '\r' || end[-1] == ' ' || end[-1] == '\t')) *--end = 0;
        if (strcmp(line, "clock source") == 0 && g_scriptCount == 0) {
            g_scriptSourceClock = true;
            line = next;
            continue;
        }
        unsigned frame, buttons, hold, timeout = 600;
        char state[32] = "";
        int relative = line[0] == '+';
        int got = sscanf(line + relative, "%u %x %u %31s %u", &frame, &buttons, &hold, state, &timeout);
        if (got >= 3) {
            PadScriptEntry* e = &g_script[g_scriptCount++];
            memset(e, 0, sizeof(*e));
            e->frame = frame;
            e->relative = relative;
            e->buttons = (u16) buttons;
            e->hold = (u16) hold;
            e->timeout = timeout;
            e->value_a = e->value_b = -1;
            char* eq = strchr(state, '=');
            if (got >= 4 && eq) {
                *eq++ = 0;
                strncpy(e->state, state, 15);
                e->value_a = atoi(eq);
                char* slash = strchr(eq, '/');
                if (slash) e->value_b = atoi(slash + 1);
            }
        }
        line = next;
    }
    re4dc_log("fixture: /cd/dc/padscript.txt: %d entries, %s clock\n", g_scriptCount, g_scriptSourceClock ? "source" : "retrace");
}

static u16 scriptButtons(void)
{
    if (g_scriptCount < 0) loadScript();
    u32 now = g_scriptSourceClock ? re4dc_fixture_source_frame() : re4dc_vi_retrace_count();
    if (g_scriptActive >= 0) {
        PadScriptEntry* e = &g_script[g_scriptActive];
        if (now < e->frame + e->hold) return e->buttons;
        g_scriptActive = -1;
    }
    // the next pending entry, in file order: a script is a sequence
    for (int i = 0; i < g_scriptCount; i++) {
        PadScriptEntry* e = &g_script[i];
        if (e->done) continue;
        u32 due = e->relative ? g_lastDelivered + e->frame : e->frame;
        if (now < due) return 0;
        if (stateHolds(e)) {
            e->done = 1;
            e->frame = now;
            g_scriptActive = i;
            g_lastDelivered = now;
            re4dc_log("fixture: delivered %04x at frame %lu (entry %d%s%s)" "\n", e->buttons, (unsigned long) now, i,
                      e->state[0] ? " for " : "", e->state);
            return e->buttons;
        }
        if (now >= due + e->timeout) {
            e->done = 1;
            re4dc_log("fixture: dropped %04x (entry %d): state %s=%d/%d never held between frames %lu and %lu" "\n",
                      e->buttons, i, e->state, e->value_a, e->value_b, (unsigned long) due, (unsigned long) now);
            continue;
        }
        return 0;  // waiting for the state, in order
    }
    return 0;
}

extern "C" {

BOOL PADInit(void) { return 1; }
int PADReset(u32 mask) { (void) mask; return 1; }
BOOL PADRecalibrate(u32 mask) { (void) mask; return 1; }
void PADSetAnalogMode(u32 mode) { (void) mode; }
void PADControlMotor(int chan, u32 cmd) { (void) chan; (void) cmd; }

void re4dc_audio_frame(void);
int re4dc_pad_context(void);      // ui_bridge.cpp: RE4DC_PAD_CTX_* from the game state of the last frame
int re4dc_pad_debug_state(void);  // ui_bridge.cpp: RE4DC_PAD_DBG_* (which debug chords would fire)
#if RE4DC_PACE_CATCHUP && RE4DC_PACE_DEBUG
void re4dc_pace_cycle_mode(void);  // pace.cpp: Smooth -> Fast -> Off (test builds)
#endif
#if defined(RE4DC_LOOK_TOGGLE)
extern "C" void re4dc_look_cycle(void);  // native_static.cpp (post30.mk LOOK_TOGGLE)
extern "C" void re4dc_look_osd_toggle(void);  // native_static.cpp: the preset label always shown / 3 s
#endif
#if defined(RE4DC_EFFECT_PS2_TOGGLE) && RE4DC_EFFECT_PS2_TOGGLE
void re4dc_ps2fx_cycle(void);  // esp_sub.cpp: the next effect look (effects30.mk EFFECT_PS2_TOGGLE)
#endif

#if RE4DC_ROUTE_MOVIES
static u16 movie_skip_latch;
void re4dc_pad_consume_movie_skip(unsigned mask) { movie_skip_latch |= mask & 0x1200; }
// Port 0 as GameCube PAD bits while a movie owns the frame (no PADRead, so no
// audio-frame callback and no source Key update): the fixture script plus
// the controller's START/B/A.
unsigned re4dc_pad_movie_buttons(void)
{
    unsigned b = scriptButtons();
    maple_device_t* dev = maple_enum_type(0, MAPLE_FUNC_CONTROLLER);
    const cont_state_t* st = dev ? (const cont_state_t*) maple_dev_status(dev) : NULL;
    if (st) {
        if (st->buttons & CONT_START) b |= 0x1000;
        if (st->buttons & CONT_B) b |= 0x0200;
        if (st->buttons & CONT_A) b |= 0x0100;
    }
    return b;
}
#endif

#if RE4DC_PAD_PROMPTS
// Set only by the existing real sample, after mapping has made its decision.
// A C/Z-only pad and a fixture-only port deliberately remain UNKNOWN.
static unsigned prompt_kind[4], prompt_context[4];
#if RE4DC_PAD_PROMPT_MANUAL_ART
static unsigned manual_standard[4];
extern "C" unsigned re4dc_pad_manual_standard(unsigned index){
    return index<4 ? manual_standard[index] : 0;
}
#endif
unsigned re4dc_pad_prompt_kind(unsigned index, int live_zoom)
{
    if(index>=4 || (live_zoom && prompt_context[index]!=RE4DC_PAD_CTX_ZOOM))
        return RE4DC_PROMPT_UNKNOWN;
    return prompt_kind[index];
}
#endif

u32 PADRead(PADStatus* status)
{
    // The sound driver's audio-frame callback (audio_stub.cpp): once per game
    // frame from the frame loop, the earliest point on the game's own thread.
    re4dc_audio_frame();
    static Re4dcPadMap maps[4];
    static maple_device_t* lastDev[4];
    int ctx0 = re4dc_pad_context();
    u32 connected = 0;
    for (int i = 0; i < 4; i++) {
        PADStatus* p = &status[i];
        memset(p, 0, sizeof(*p));
        u16 scripted = i == 0 ? scriptButtons() : 0;
        maple_device_t* dev = maple_enum_type(i, MAPLE_FUNC_CONTROLLER);
        const cont_state_t* st = dev ? (const cont_state_t*) maple_dev_status(dev) : NULL;
        static const cont_state_t idle = {};
#if RE4DC_PAD_PROMPTS
        const int prompt_real = dev && st;
        // Clear before every poll, including absence and failed status reads.
        prompt_kind[i]=RE4DC_PROMPT_UNKNOWN;
        prompt_context[i]=RE4DC_PAD_CTX_NATIVE;
#if RE4DC_PAD_PROMPT_MANUAL_ART
        manual_standard[i]=0;
#endif
#endif
        if (dev != lastDev[i]) {  // plugged / unplugged / swapped: classify the pad again
            lastDev[i] = dev;
            memset(&maps[i], 0, sizeof(maps[i]));
        }
        if (st == NULL && (i != 0 || g_scriptCount <= 0)) {
            p->err = PAD_ERR_NO_CONTROLLER;
            continue;
        }
        if (st == NULL) st = &idle;  // a scripted port counts as connected
        connected |= 0x80000000u >> i;
        {
            static int seen[4];
            if (!seen[i]) { seen[i] = 1; re4dc_log("pad %d: controller present\n", i); }
        }
        int capsDual = dev && (cont_has_capabilities(dev, CONT_CAPABILITIES_SECONDARY_ANALOG) ||
                               cont_has_capabilities(dev, CONT_CAPABILITY_C) || cont_has_capabilities(dev, CONT_CAPABILITY_Z));
        Re4dcPadIn in = {(u32) st->buttons, st->ltrig, st->rtrig, st->joyx, st->joyy, st->joy2x, st->joy2y};
        PADStatus mapped;
        u8 wasDual = maps[i].dual;
        re4dcMapPad(&in, i == 0 ? ctx0 : RE4DC_PAD_CTX_NATIVE, capsDual, &maps[i], &mapped);
#if RE4DC_PAD_PROMPTS
        if(prompt_real) {
#if RE4DC_PAD_PROMPT_MANUAL_ART
            // Exact full standard capabilities, not merely D-pad presence.
            // Fixture-only, unknown, failed reads and dual mappings stay false.
            manual_standard[i]=!maps[i].dual && cont_is_type(dev,CONT_TYPE_STANDARD_CONTROLLER)==1;
#endif
            prompt_context[i]=i==0 ? ctx0 : RE4DC_PAD_CTX_NATIVE;
            // These inspect the already enumerated device metadata, not a new
            // input poll. Exact ==1 excludes the API's invalid-device -1.
            if(!maps[i].dual && cont_has_capabilities(dev,CONT_CAPABILITIES_DPAD)==1)
                prompt_kind[i]=RE4DC_PROMPT_DPAD;
            else if(maps[i].dual && cont_has_capabilities(dev,CONT_CAPABILITIES_SECONDARY_ANALOG)==1)
                prompt_kind[i]=RE4DC_PROMPT_SECOND_ANALOG;
        }
#endif
        if (maps[i].dual != wasDual) re4dc_log("pad %d: dual-analog mapping (C-stick = joy2, Z = C/Z)\n", i);
        u16 b = mapped.button;
        if (st->buttons & CONT_Z) b |= PAD_TRIGGER_Z;
        {
            static u16 lastLogged[4];
            if (b != lastLogged[i]) {
                re4dc_log("pad %d: real buttons %04x\n", i, (unsigned) b);
                lastLogged[i] = b;
            }
        }
        b |= scripted;
        p->button = b;
        if (i == 0 && !RE4DC_DEBUG_PAD) {  // debug chords come off the real bits only; fixture bits pass
            u16 real = mapped.button | ((st->buttons & CONT_Z) ? PAD_TRIGGER_Z : 0);
            p->button = (u16) (re4dcBlockDebugChords(real, re4dc_pad_debug_state(), &maps[0]) | scripted);
        }
#if RE4DC_PACE_CATCHUP && RE4DC_PACE_DEBUG
        // Test builds: a START press that begins with R held (and L not held: L + START is the
        // debug-slot chord) cycles the frame pacing mode (pace.cpp); that START is masked until
        // released, so the game never sees the chord's press. Real bits only; fixture bits pass.
        if (i == 0) {
            static u8 paceStartHeld, paceChord;
            if (mapped.button & PAD_BUTTON_START) {
                if (!paceStartHeld && (mapped.button & (PAD_TRIGGER_L | PAD_TRIGGER_R)) == PAD_TRIGGER_R) {
                    paceChord = 1;
                    re4dc_pace_cycle_mode();
                }
                paceStartHeld = 1;
            } else {
                paceStartHeld = 0;
                paceChord = 0;
            }
            if (paceChord) p->button &= (u16) ~PAD_BUTTON_START;
        }
#endif
#if defined(RE4DC_LOOK_TOGGLE)
        // Test builds (post30.mk LOOK_TOGGLE, look study 2026-10-10): a START press that begins with X held (L and R
        // up) steps the look preset (native_static.cpp re4dc_look_cycle: DC, GC, GD, G7, SK, GH; with
        // EFFECT_PS2_TOGGLE the preset also sets the effect look); that START is masked until released.
        if (i == 0) {
            static u8 lookStartHeld, lookChord;
            if (mapped.button & PAD_BUTTON_START) {
                const unsigned held = mapped.button & (PAD_TRIGGER_L | PAD_TRIGGER_R | PAD_BUTTON_X | PAD_BUTTON_Y);
                if (!lookStartHeld && held == (PAD_BUTTON_X | PAD_BUTTON_Y)) {
                    lookChord = 1;
                    re4dc_look_osd_toggle();  // X + Y + START: the on-screen preset label always shown / 3 s
                } else if (!lookStartHeld && held == PAD_BUTTON_X) {
                    lookChord = 1;
                    re4dc_look_cycle();
                }
                lookStartHeld = 1;
            } else {
                lookStartHeld = 0;
                lookChord = 0;
            }
            if (lookChord) p->button &= (u16) ~PAD_BUTTON_START;
        }
#elif defined(RE4DC_EFFECT_PS2_TOGGLE) && RE4DC_EFFECT_PS2_TOGGLE
        // Test builds (effects30.mk EFFECT_PS2_TOGGLE): a START press that begins with X held (L and R up: R + START
        // paces, L + START is the debug slot) steps the effect look (esp_sub.cpp re4dc_ps2fx_cycle: GC, GF, PH,
        // PS); that START is masked until released. X has no game function. Real bits only; fixture bits pass.
        if (i == 0) {
            static u8 fxStartHeld, fxChord;
            if (mapped.button & PAD_BUTTON_START) {
                if (!fxStartHeld && (mapped.button & (PAD_TRIGGER_L | PAD_TRIGGER_R | PAD_BUTTON_X)) == PAD_BUTTON_X) {
                    fxChord = 1;
                    re4dc_ps2fx_cycle();
                }
                fxStartHeld = 1;
            } else {
                fxStartHeld = 0;
                fxChord = 0;
            }
            if (fxChord) p->button &= (u16) ~PAD_BUTTON_START;
        }
#endif
#if RE4DC_VMU_DEBUG_SLOT
        // Debug slot chord (hold L + START): START never reaches the game while L is held.
        if (i == 0) p->button &= (u16) ~re4dc_dbgslot_pad(p->button);
#endif
#if RE4DC_ROUTE_MOVIES
        // A consumed movie skip stays masked until its buttons are released
        // (after the debug-chord filter, which rewrites p->button).
        if (i == 0) { movie_skip_latch &= p->button; p->button &= (u16) ~movie_skip_latch; }
#endif
        p->stickX = mapped.stickX;       // SDK-clamped; maple Y already flipped
        p->stickY = mapped.stickY;
        p->substickX = mapped.substickX;
        p->substickY = mapped.substickY;
        p->triggerLeft = mapped.triggerLeft;
        p->triggerRight = mapped.triggerRight;
#if RE4DC_DBG_WARP
        if (i == 0) {
            re4dc_warp_pad(&p->button, &p->stickY);  // test warp rig: boot card screen, door test
            // A warp `act` mask with R (0x0020) also gives the analog trigger the aim reads.
            if ((p->button & PAD_TRIGGER_R) && !p->triggerRight) p->triggerRight = 0xC0;
        }
#endif
        p->err = PAD_ERR_NONE;
    }
    return connected;
}

void PADClamp(PADStatus* status)
{
    (void) status;  // PADRead already applied the SDK clamp regions (re4dcMapPad)
}

}  // extern "C"
