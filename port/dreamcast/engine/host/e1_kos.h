// The KallistiOS headers engine units that also include the original headers may use (not <kos.h>: it pulls newlib's
// math.h, whose fabsf conflicts with the original headers' inline fabsf).
#ifndef E1_KOS_H
#define E1_KOS_H
#include <sys/types.h>
#include <kos/fs.h>
#include <kos/thread.h>
#include <arch/timer.h>
#include <malloc.h>
#include <stdio.h>
#endif
