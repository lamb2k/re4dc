// autoplay_engine.cpp (lane eng-ref): the outcome check's closed-loop player in an engine image, as a link-time wrap
// of PADRead (-Wl,--wrap=PADRead; s/abuild.sh). The engine's code is not changed: the route's pad is read, then
// replaced by autoplay.inc's choice, except while an event holds the game (the route gives no pad then either).
#include "global.h"
#include "player.h"
#include "em.h"
#include "autoplay.inc"

struct PADStatus {
    u16 button;
    s8 stickX, stickY, substickX, substickY;
    u8 triggerLeft, triggerRight, analogA, analogB;
    s8 err;
};
extern "C" u32 __real_PADRead(PADStatus* status);
extern "C" u32 __wrap_PADRead(PADStatus* status)
{
    u32 r = __real_PADRead(status);
    if (pG->Status_flg[1] & 0x10000000) return r;
    unsigned short b = status[0].button;
    signed char x = status[0].stickX, y = status[0].stickY;
    if (re4ap_pad(&b, &x, &y)) {
        status[0].button = b;
        status[0].stickX = x;
        status[0].stickY = y;
        status[0].triggerRight = (b & 0x0020) ? 0xC0 : 0;
    }
    return r;
}
