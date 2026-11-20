// svc_cloth_glue.cpp (game side; lane eng-svc2): what the hosted cloth (game/pendulum.cpp) needs beyond the plain
// build's objects. Linked by every svc build (svc/svc.mk SVC_HG_OBJS).
#include "hostref.h"
#include "dbmodule.h"

// The old port's stand-in for the GameCube's locked cache: penClothAtMake builds a tick's collision volumes there.
// Placed in the service region's last 64 KiB below the motion keys (svc_io.cpp keeps the carve out of it), so the
// census traces the original's volume list as it traces the native cloth's.
asm(".globl re4dc_locked_cache\n.set re4dc_locked_cache, 0x8E3F0000");

// The hosted cloth's random numbers (pendulum.o's fRand0_1 / fRand1_1, renamed in the svc builds): a presentation
// stream of its own (xorshift32, values as rnd.cpp gives them), so the behaviour's Rnd sees no cloth draw.
static u32 g_pres = 0x2545F491u;
static u32 pres_next()
{
    u32 x = g_pres;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    return g_pres = x;
}
extern "C" f32 pen_fRand0_1() { return (f32) (pres_next() >> 8) * (1.0f / 16777216.0f); }
extern "C" f32 pen_fRand1_1() { return pen_fRand0_1() * 2.0f - 1.0f; }

// Debug drawing (pG->Debug_flg[0] & 0x400): nothing to draw in the reference.
void Draw_cylinderMtx(Mtx, Vec*, f32, f32, u32) {}
