#pragma once
#include <stdint.h>
#ifndef RE4DC_KOS_CACHE_P2_DIAG
#define RE4DC_KOS_CACHE_P2_DIAG 0
#endif
#if RE4DC_KOS_CACHE_P2_DIAG
#ifdef __cplusplus
extern "C" {
#endif
/* Layout consumed by generated assembly; exactly two isolated cache lines. */
typedef struct Re4dcCacheP2Counters {
    uint32_t calls, timed, rejected, unavailable;
    uint32_t total_lo, total_hi, max_ticks, overflow;
    uint32_t full512, ram256, reserved[6];
} Re4dcCacheP2Counters;
void re4dc_cache_p2_diag_enter(unsigned room);
void re4dc_cache_p2_diag_leave(unsigned room);
void re4dc_cache_p2_diag_poll(unsigned room, unsigned frame);
#ifdef __cplusplus
}
#endif
#endif
