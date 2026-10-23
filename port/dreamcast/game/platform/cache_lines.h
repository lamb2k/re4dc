// CACHE_LINEWISE=1 (lane arena23, default 0 = image unchanged): write back the operand cache line by line (ocbwb)
// for every range, never through KOS arch_dcache_wback_all. That inline path (taken for count >= 65560, e.g. the
// st1_1 overlay sync at 77 KB) reads and rewrites all 512 OC address-array entries (0xf4000008, tag | U | V) from
// cached P1 code. The console fault word 0x0c8a8001 has exactly that tag | V shape; this switch removes the only
// game-side path that handles such a value. Same effect (dirty lines in the range reach RAM), no address-array access.
#ifndef RE4DC_CACHE_LINES_H
#define RE4DC_CACHE_LINES_H
#include <stdint.h>
#include <stddef.h>
#if defined(RE4DC_CACHE_LINEWISE) && RE4DC_CACHE_LINEWISE
static inline void re4dc_dcache_wback_lines(uintptr_t start, size_t count)
{
    const uintptr_t end = start + count;
    for (start &= ~uintptr_t(0x1f); start < end; start += 32) __asm__ __volatile__("ocbwb @%0" : : "r"(start) : "memory");
}
#define RE4DC_DCACHE_WBACK(a, n) re4dc_dcache_wback_lines((a), (n))
#else
#define RE4DC_DCACHE_WBACK(a, n) dcache_wback_range((a), (n))
#endif
#endif
