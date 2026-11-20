// svc_cloth_glue.cpp (game side; lane eng-svc2): what the hosted cloth (game/pendulum.cpp) needs beyond the plain
// build's objects. Linked by every svc build (svc/svc.mk SVC_HG_OBJS).
#include "hostref.h"
#include "dbmodule.h"

// The old port's stand-in for the GameCube's locked cache: penClothAtMake builds a tick's collision volumes there.
extern "C" {
unsigned char re4dc_locked_cache[16384] __attribute__((aligned(32)));
}

// Debug drawing (pG->Debug_flg[0] & 0x400): nothing to draw in the reference.
void Draw_cylinderMtx(Mtx, Vec*, f32, f32, u32) {}
