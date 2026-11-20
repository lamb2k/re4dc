// E2 boss route (lane eng-boss): start state and pad script of the El Gigante fight, the same inputs the reference
// fixture gives the old game (E:\RE4DC-Lanes\eng-boss\s\fixtures\boss-fight-2.txt: r119 entry, no room flag so the
// source appearance trigger fires, god, source clock, 88 act lines). Replaces core/route.cpp in the BOSS=1 image;
// the pad semantics are the warp rig's (dbgwarp_bridge.cpp re4dc_warp_pad), as in E1.
#include "e1_core.h"
#include "e1_engine.h"
#include "types.h"
#include <string.h>

#ifndef E1_PAD_AT_PLACE
#define E1_PAD_AT_PLACE 13
#endif
#ifndef E2_ROUTE_TICKS
#define E2_ROUTE_TICKS 900
#endif
// Control (the plays-right check must fail): every action one pad frame later.
#ifndef E1_CONTROL_SHIFT
#define E1_CONTROL_SHIFT 0
#endif
unsigned e1_control_shift = E1_CONTROL_SHIFT;

struct Act { unsigned frame; uint16_t buttons; int8_t sx, sy; unsigned hold; };
static const Act acts[] = {
    {30, 0x0020, 0, 0, 16},
    {46, 0x0120, 0, 0, 2},
    {48, 0x0020, 0, 0, 12},
    {60, 0x0120, 0, 0, 2},
    {62, 0x0020, 0, 0, 12},
    {74, 0x0120, 0, 0, 2},
    {76, 0x0020, 0, 0, 12},
    {88, 0x0120, 0, 0, 2},
    {90, 0x0020, 0, 0, 12},
    {102, 0x0120, 0, 0, 2},
    {104, 0x0020, 0, 0, 12},
    {116, 0x0120, 0, 0, 2},
    {118, 0x0020, 0, 0, 12},
    {130, 0x0000, 0, -80, 24},
    {154, 0x0000, -80, 0, 20},
    {174, 0x0020, 0, 0, 14},
    {188, 0x0120, 0, 0, 2},
    {190, 0x0020, 0, 0, 12},
    {202, 0x0120, 0, 0, 2},
    {204, 0x0020, 0, 0, 12},
    {216, 0x0120, 0, 0, 2},
    {218, 0x0020, 0, 0, 12},
    {230, 0x0120, 0, 0, 2},
    {232, 0x0020, 0, 0, 12},
    {244, 0x0120, 0, 0, 2},
    {246, 0x0020, 0, 0, 12},
    {258, 0x0000, 80, 80, 30},
    {288, 0x0020, 0, 0, 14},
    {302, 0x0120, 0, 0, 2},
    {304, 0x0020, 0, 0, 12},
    {316, 0x0120, 0, 0, 2},
    {318, 0x0020, 0, 0, 12},
    {330, 0x0120, 0, 0, 2},
    {332, 0x0020, 0, 0, 12},
    {344, 0x0120, 0, 0, 2},
    {346, 0x0020, 0, 0, 12},
    {358, 0x0120, 0, 0, 2},
    {360, 0x0020, 0, 0, 12},
    {372, 0x0200, 0, -80, 30},
    {402, 0x0020, -80, 0, 20},
    {422, 0x0020, 0, 0, 10},
    {432, 0x0120, 0, 0, 2},
    {434, 0x0020, 0, 0, 12},
    {446, 0x0120, 0, 0, 2},
    {448, 0x0020, 0, 0, 12},
    {460, 0x0120, 0, 0, 2},
    {462, 0x0020, 0, 0, 12},
    {474, 0x0120, 0, 0, 2},
    {476, 0x0020, 0, 0, 12},
    {488, 0x0000, 0, 80, 20},
    {508, 0x0020, 0, 0, 14},
    {522, 0x0120, 0, 0, 2},
    {524, 0x0020, 0, 0, 12},
    {536, 0x0120, 0, 0, 2},
    {538, 0x0020, 0, 0, 12},
    {550, 0x0120, 0, 0, 2},
    {552, 0x0020, 0, 0, 12},
    {564, 0x0120, 0, 0, 2},
    {566, 0x0020, 0, 0, 12},
    {578, 0x0000, 80, 0, 24},
    {602, 0x0020, 0, 0, 14},
    {616, 0x0120, 0, 0, 2},
    {618, 0x0020, 0, 0, 12},
    {630, 0x0120, 0, 0, 2},
    {632, 0x0020, 0, 0, 12},
    {644, 0x0120, 0, 0, 2},
    {646, 0x0020, 0, 0, 12},
    {658, 0x0120, 0, 0, 2},
    {660, 0x0020, 0, 0, 12},
    {672, 0x0000, 0, -80, 30},
    {702, 0x0200, -80, 0, 24},
    {726, 0x0020, 0, 0, 14},
    {740, 0x0120, 0, 0, 2},
    {742, 0x0020, 0, 0, 12},
    {754, 0x0120, 0, 0, 2},
    {756, 0x0020, 0, 0, 12},
    {768, 0x0120, 0, 0, 2},
    {770, 0x0020, 0, 0, 12},
    {782, 0x0120, 0, 0, 2},
    {784, 0x0020, 0, 0, 12},
    {796, 0x0000, -80, 80, 30},
    {826, 0x0020, 0, 0, 14},
    {840, 0x0120, 0, 0, 2},
    {842, 0x0020, 0, 0, 12},
    {854, 0x0120, 0, 0, 2},
    {856, 0x0020, 0, 0, 12},
    {868, 0x0120, 0, 0, 2},
    {870, 0x0020, 0, 0, 12},
};
static const E1Route route = {0x119, 0x00000000, E2_ROUTE_TICKS, {124500.0f, 2251.0f, 10888.0f}, -1.571f};
const E1Route& e1_route() { return route; }

static E1Pad latched;
static unsigned next_act, cur_until;
static int cur_act = -1;

void e1_input_latch(unsigned tick)
{
    const unsigned pad = E1_PAD_AT_PLACE + tick - e1_control_shift;
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
    }
    if ((p.buttons & 0x0020) && !p.trig_r) p.trig_r = 0xC0;
    latched = p;
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
