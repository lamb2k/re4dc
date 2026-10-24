// Force-included ahead of every recovered game unit in the Dreamcast build.
//
// The units declare the few libc functions they use themselves, in the
// spellings below, instead of including a libc header (the original tree's
// headers are CodeWarrior's). A handful of units rely on another unit's
// declaration having been seen first; this makes the same declarations
// visible everywhere. Spellings match the game's own (joy.h,
// emwindow.cpp), so a unit's later re-declaration is identical rather than
// conflicting. Only the functions some unit fails to declare are here.
#ifndef RE4DC_PRELUDE_H
#define RE4DC_PRELUDE_H

#ifdef __cplusplus
extern "C" {


#endif
void* memcpy(void* dst, const void* src, unsigned int n);

int strcmp(const char* a, const char* b);
#ifdef __cplusplus
}


#endif



// STAT_ROUTINE_BYTES=1 (Makefile; lane stat-bytes23 2026-10-23): cModel::stat is the four routine bytes
// r_no_0..3 read as one word. The recovered sources store / test it as a GameCube big-endian word (r_no_0 in the
// top byte); on the little-endian Dreamcast r_no_0 is the low byte, so those constants named the wrong routine /
// step. STAT_BE() wraps every such constant (stores, masks and compare values); off it is the constant unchanged.
#if defined(RE4DC_STAT_ROUTINE_BYTES) && RE4DC_STAT_ROUTINE_BYTES && !defined(__PPC__)
#define STAT_BE(x) ((unsigned int) __builtin_bswap32((unsigned int) (x)))
#else
#define STAT_BE(x) (x)
#endif

#endif
