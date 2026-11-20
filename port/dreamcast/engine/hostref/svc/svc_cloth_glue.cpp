// svc_cloth_glue.cpp (game side; lane eng-svc2): what the hosted cloth (game/pendulum.cpp) needs beyond the plain
// build's objects. Linked by every svc build (svc/svc.mk SVC_HG_OBJS).
#include "hostref.h"
#include "dbmodule.h"

// The old port's stand-in for the GameCube's locked cache: penClothAtMake builds a tick's collision volumes there.
// Placed in the service region's last 64 KiB below the motion keys (svc_io.cpp keeps the carve out of it), so the
// census traces the original's volume list as it traces the native cloth's.
asm(".globl re4dc_locked_cache\n.set re4dc_locked_cache, 0x8E3F0000");

// Debug drawing (pG->Debug_flg[0] & 0x400): nothing to draw in the reference.
void Draw_cylinderMtx(Mtx, Vec*, f32, f32, u32) {}
