// E2 fight route (lane eng-e2): start state and pad script of the village square fight, the same inputs the reference
// fixture gives the old game (E:\RE4DC-Lanes\eng-e2\s\fixtures\cross-fight<N>-warp.txt: r101 fight, god, ammo, source
// clock; the act lines are generated into acts_cross.inc by s/mkacts.py). Replaces core/route.cpp in the FIGHT=1 image.
// Pad semantics are the warp rig's (dbgwarp_bridge.cpp re4dc_warp_pad): a pad-frame counter advances once per PADRead;
// an action fires when the counter reaches its frame and holds its buttons and stick for `hold` pad frames; while an
// event holds the game (Status_flg[1] 0x10000000) the running action is cut and no button is given; a held R also
// gives the analog trigger 0xC0. Ports 1-3 have no controller.
#include "global.h"
#include "player.h"
#include "e1_core.h"
#include "e1_engine.h"
#include "types.h"
#include "e1_kos.h"
#include <string.h>

#ifndef E1_PAD_AT_PLACE
#define E1_PAD_AT_PLACE 13
#endif
// Controls (the plays-right check must fail): every action one pad frame later (E1_CONTROL_SHIFT=1).
#ifndef E1_CONTROL_SHIFT
#define E1_CONTROL_SHIFT 0
#endif
unsigned e1_control_shift = E1_CONTROL_SHIFT;

struct Act { unsigned frame; uint16_t buttons; int8_t sx, sy; unsigned hold; };
#include "acts_cross.inc"   // static const Act acts[]; E2_FIGHT_TICKS; E2_FIGHT_POS / ANG

static const E1Route route = {0x101, 0x00002000, E2_FIGHT_TICKS, E2_FIGHT_POS, E2_FIGHT_ANG};
const E1Route& e1_route() { return route; }

// Diagnostic arm FEED (boot option; plays right is reported without it): the old run's generator state at the start of
// every tick (FEED.BIN, s/mkfeed.py), as re4ref --rng-feed. Since the owner's split the old game's effects draw from the
// game generator and the engine's do not, so the feed shows what the AI does when it is given the old run's numbers.
void RndInit(u16 seed);
extern "C" void* e1_file_load(const char* path, uint32_t* size, uint32_t align);
static unsigned short* feed;
static unsigned feed_n;
static int feed_open = -1;

static E1Pad latched;
static unsigned next_act, cur_until, pad_frames;
static int cur_act = -1;

void e1_input_latch(unsigned tick)
{
    if (feed_open < 0) {
        feed_open = 0;
        file_t f = fs_open("/cd/FEED.BIN", O_RDONLY);
        if (f >= 0) {
            fs_close(f);
            uint32_t n = 0;
            feed = (unsigned short*) e1_file_load("/cd/FEED.BIN", &n, 32);
            feed_n = feed ? n / 2 : 0;
            e1_log("E2 FEED: the old run's generator state at the start of %u ticks\n", feed_n);
        }
    }
    if (feed && tick < feed_n) RndInit(feed[tick]);
    // god (the fixture's warp): Leon's life refilled every frame
    pG->pl_life = pG->pl_life_max;
    // goto (the fixture's warp, dbgwarp_bridge.cpp goto_poll): at or after its room frame and outside events, Leon is
    // moved and turned once; room frame R is the old run's tick 184 + R + 1, engine tick R + 1
    static unsigned next_goto;
    if (pPL && gotos[next_goto].frame != 0xFFFFFFFFu && tick >= gotos[next_goto].frame + 1 &&
        !(pG->Status_flg[1] & 0x10000000)) {
        const Goto& g = gotos[next_goto++];
        Vec gp = {g.x, g.y, g.z};
        pPL->setPos(&gp);
        if (g.ang < 90.0f) { Vec ga = {0.0f, g.ang, 0.0f}; pPL->setAng(&ga); }
        e1_log("E2 goto at tick %u\n", tick);
    }
    pad_frames = E1_PAD_AT_PLACE + tick - E1_CONTROL_SHIFT;
    E1Pad p = {0, 0, 0, 0};
    if (pG->Status_flg[1] & 0x10000000) {   // an event holds the game: the running action ends here
        if (cur_act >= 0 && pad_frames < cur_until) cur_until = pad_frames;
        latched = p;
        e1_pad_now = p;
        return;
    }
    if (cur_act >= 0 && pad_frames < cur_until) {
        const Act& a = acts[cur_act];
        p.buttons |= a.buttons;
        if (a.sy) p.sy = a.sy;
        if (a.sx) p.sx = a.sx;
    } else if (next_act < sizeof(acts) / sizeof(acts[0]) && pad_frames >= acts[next_act].frame) {
        const Act& a = acts[next_act];
        cur_act = (int) next_act++;
        cur_until = pad_frames + a.hold;
        p.buttons |= a.buttons;
        if (a.sy) p.sy = a.sy;
        if (a.sx) p.sx = a.sx;
    }
    if ((p.buttons & 0x0020) && !p.trig_r) p.trig_r = 0xC0;
    latched = p;
    e1_pad_now = p;
}

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
void PADClamp(PADStatus*) {}
int PADReset(u32) { return 1; }
int GetSystemVcnt() { return 2; }
}
