// Force-included ahead of every hosted original unit and every engine C++ unit of the E1 image (lane eng-e1).
//
// The hosted units are the original sources built with every RE4DC_ knob off. They declare the few libc functions
// they use in their own spellings (as the old port's prelude notes); these declarations make them visible to every
// unit. RE4DC_XM_* (named unconditionally by cam_motion.cpp) are the plain PSMTXMultVec forms (re4dc_xm.h, knob off).
#ifndef E1_PRELUDE_H
#define E1_PRELUDE_H
#ifdef __cplusplus
extern "C" {
#endif
void* memcpy(void* dst, const void* src, unsigned int n);
int strcmp(const char* a, const char* b);
#ifdef __cplusplus
}
#endif
// Endian adapter (not a knob): cModel::stat is the routine bytes r_no_0..3 read as one word; the sources write its
// constants as GameCube big-endian words. On the little-endian SH-4 they are byte-swapped, as the reference build does
// (STAT_ROUTINE_BYTES=1 in the release recipe). Measured by s/knobdiff.sh: this swap (7 sites in player, pl_class,
// pl_sub, pl_wep) is the only code difference between the hosted files and the reference build's beyond hooks.
#define STAT_BE(x) ((unsigned int) __builtin_bswap32((unsigned int) (x)))
#ifdef __cplusplus
#include "re4dc_xm.h"
#endif
#endif
