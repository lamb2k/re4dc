// E1 route (lane eng-e1): start state and pad script, the same inputs the reference fixture gives the old game
// (E:\RE4DC-Lanes\eng-e1\s\fixtures\r101-route.txt: dbgwarp `act` lines, source clock). Semantics of the warp rig
// (dbgwarp_bridge.cpp re4dc_warp_pad): a pad-frame counter advances once per PADRead; an action fires when the counter
// reaches its frame and holds its buttons and stick for `hold` pad frames; a held R also gives the analog trigger 0xC0.
// Ports 1-3 have no controller (PAD_ERR_NO_CONTROLLER), as in the reference's Flycast.
//
// Pad frame at engine tick 0 (the tick the player is placed): E1_PAD_AT_PLACE, calibrated against the reference
// trace (the walk motion starts on the reference tick that reads pad frame 60).
#include "e1_core.h"
#include "e1_engine.h"
#include "types.h"
#include "e1_kos.h"
#include <string.h>

#ifndef E1_PAD_AT_PLACE
#define E1_PAD_AT_PLACE 13
#endif
#ifndef E1_ROUTE_TICKS
#define E1_ROUTE_TICKS 640
#endif
// Control (the plays-right check must fail): a different input stream (one tick later on every action).
#ifndef E1_CONTROL_SHIFT
#define E1_CONTROL_SHIFT 0
#endif

struct Act { unsigned frame; uint16_t buttons; int8_t sx, sy; unsigned hold; };
// r101-route.txt, in order
static const Act acts[] = {
    {60, 0x0000, 0, 80, 90},     // walk
    {160, 0x0000, 80, 80, 40},   // walk, turning right
    {210, 0x0000, 80, 0, 30},    // turn right in place
    {250, 0x0200, 0, 80, 60},    // run
    {320, 0x0200, -80, 80, 36},  // run, turning left
    {400, 0x0020, 0, 0, 30},     // aim (R)
    {430, 0x0020, -80, 0, 24},   // aim, turning left
    {454, 0x0020, 80, 0, 24},    // aim, turning right
    {478, 0x0020, 0, 0, 20},     // aim
    {530, 0x0000, 0, 80, 30},    // walk
    {570, 0x0000, 0, -80, 20},   // back step
};
static const E1Route route = {0x101, 0x00002000, E1_ROUTE_TICKS, {-7914.0f, 0.0f, 2000.0f}, 1.5708f, 0x0d37};   // e1-route.txt

// The hill scene (lane eng-e1b; boot option HILL): Ashley follows Leon on the r11d hill path, the re4ref fixture
// tools/plays_right/fixtures/hill-follow.txt (tick n = the old game's t 372 + n in the full-field fixture fx-hill-1).
// Pads are re4ref's: from that tick on (stick forward 80 for 60 ticks from tick 28, again from tick 148).
static const E1Route hill = {0x11d, 0x00100000, 728, {20214.0f, 0.0f, 13952.0f}, -1.8170f, 0x0d37};   // hill-follow.txt
struct TickPad { unsigned tick; E1Pad pad; };
static const TickPad hill_pads[] = {
    {0, {0x0000, 0, 0, 0}},
    {28, {0x0000, 0, 80, 0}},
    {88, {0x0000, 0, 0, 0}},
    {148, {0x0000, 0, 80, 0}},
    {208, {0x0000, 0, 0, 0}},
};
const E1Route& e1_route() { return e1_scene == E1_SCENE_HILL ? hill : route; }

static E1Pad latched;
static unsigned next_act, cur_until;
static int cur_act = -1;

void e1_input_latch(unsigned tick)
{
    if (e1_scene == E1_SCENE_HILL) {
        E1Pad p = {0, 0, 0, 0};
        for (const TickPad& tp : hill_pads)
            if (tp.tick <= tick - E1_CONTROL_SHIFT) p = tp.pad;
        latched = p;
        e1_pad_now = p;
        return;
    }
    const unsigned pad = E1_PAD_AT_PLACE + tick - E1_CONTROL_SHIFT;
    E1Pad p = {0, 0, 0, 0};
    if (cur_act >= 0 && pad < cur_until) {
        const Act& a = acts[cur_act];
        p.buttons |= a.buttons;
        if (a.sy) p.sy = a.sy;
        if (a.sx) p.sx = a.sx;
    } else if (next_act < sizeof(acts) / sizeof(acts[0]) && pad >= acts[next_act].frame) {
        const Act& a = acts[next_act];
        cur_act = (int) next_act++;
        cur_until = pad + a.hold;
        p.buttons |= a.buttons;
        if (a.sy) p.sy = a.sy;
        if (a.sx) p.sx = a.sx;
        e1_log("E1 act %d buttons=%04x stick=%d,%d hold=%u pad=%u tick=%u\n", cur_act, a.buttons, a.sx, a.sy, a.hold, pad, tick);
    }
    if ((p.buttons & 0x0020) && !p.trig_r) p.trig_r = 0xC0;
    latched = p;
    e1_pad_now = p;
}

// The SDK pad read the hosted PadRead (src/game/pad.cpp) calls.
struct PADStatus {
    u16 button;
    s8 stickX, stickY, substickX, substickY;
    u8 triggerLeft, triggerRight, analogA, analogB;
    s8 err;
};
extern "C" {
u32 PADRead(PADStatus* status)
{
    memset(status, 0, sizeof(PADStatus) * 4);
    status[0].button = latched.buttons;
    status[0].stickX = latched.sx;
    status[0].stickY = latched.sy;
    status[0].triggerRight = latched.trig_r;
    status[0].err = 0;
    for (int i = 1; i < 4; i++) status[i].err = -1;
    return 0x80000000u;
}
// The stick and trigger values above are raw controller units; the engine's input service clamps them on its pad path
// as the original game does (services/input/input.cpp pad_clamp, lane eng-e1g: stick 80 reaches the game as 65,
// trigger 0xC0 as 150), so this file has no PADClamp and no PADCLAMP boot option any more.
int PADReset(u32) { return 1; }
int GetSystemVcnt() { return 2; }
}
