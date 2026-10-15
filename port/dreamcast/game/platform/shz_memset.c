/* shz_memset.c: GAME_SHZ_MEMSET=1 (game30.mk; lane sh4zam-direct 2026-10-15; EXACT, default 0 = not built).
 *
 * memset through SH4ZAM's shz_memset8 (third_party/sh4zam, MIT, Copyright (c) 2025, 2026 Falco Girgis and SH4ZAM
 * Contributors; pin 0fd3a1e1 v0.9.0; the out-of-line body is the unmodified upstream source/sh4/shz_mem_sh4.s): one
 * FMOV.D (8-byte) store per 8 bytes instead of newlib's 4-byte store loop. The link wraps memset
 * (-Wl,--wrap=memset), so every caller (the value-initialised aggregates GCC clears with memset, the game, KOS) takes
 * this path. Results are byte-identical to memset: the head up to 8-byte alignment and the tail are byte stores, the
 * body is the fill byte replicated into 64 bits. Below SHZ_MEMSET_MIN bytes the call goes straight to newlib.
 *
 * FPU: shz_memset8_sh4_ uses FR4/FR5 (call-clobbered) and toggles FPSCR.SZ twice (restored); KOS saves the whole FPU
 * state on interrupts (kernel/arch/dreamcast/kernel/entry.s), so a memset inside an IRQ handler is safe. */
#include <stddef.h>
#include <stdint.h>
#include <sh4zam/shz_mem.h>

#ifndef SHZ_MEMSET_MIN
#define SHZ_MEMSET_MIN 64u
#endif

void* __real_memset(void* dst, int c, size_t n);

void* __wrap_memset(void* dst, int c, size_t n)
{
    if (n < SHZ_MEMSET_MIN) {
        return __real_memset(dst, c, n);
    }
    volatile uint8_t* p = (volatile uint8_t*) dst; /* volatile: GCC must not turn the byte loops back into memset */
    const uint8_t b = (uint8_t) c;
    while ((uintptr_t) p & 7u) {
        *p++ = b;
        --n;
    }
    const size_t body = n & ~(size_t) 7u;
    const uint32_t w = (uint32_t) b * 0x01010101u;
    shz_memset8((void*) p, ((uint64_t) w << 32) | w, body);
    p += body;
    n -= body;
    while (n--) {
        *p++ = b;
    }
    return dst;
}

/* platform/aliases-manual.ld maps the unprefixed assembler name "memset" (route_ck.cpp and st2/st3 rooms declare
 * memset with asm("memset")) to _memset; the wrap turns that reference into "__wrap_memset" (no C prefix), so the
 * wrapper answers to that name too. */
void* shz_wrap_memset_asm(void* dst, int c, size_t n) __asm__("__wrap_memset") __attribute__((alias("__wrap_memset")));
