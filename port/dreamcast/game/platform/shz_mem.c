/* shz_mem.c: GAME_SHZ_MEM=1 (game30.mk; lane sh4zam-adopt 2026-10-15; EXACT; default 0 = not built, the previous image).
 *
 * Every memset / memcpy / memmove in the program (game, port, KOS, newlib / libstdc++ internals and GCC-emitted struct
 * copies that call memcpy) goes through the link wraps (-Wl,--wrap=memset,--wrap=memcpy,--wrap=memmove) to SH4ZAM's
 * routines from the kos-ports install (kos-ports/sh4zam, MIT, Copyright (c) 2025, 2026 Falco Girgis and SH4ZAM
 * Contributors; v0.9.0). User rule 10-15: the port copies with shz_memcpy, not newlib's memcpy.
 *
 * Run-time mask re4dc_shz_mem_mask (boot value SHZ_MEM_BOOT, a .data word, so arms that differ only in it share one
 * layout; re4dc_shz_mem_set from the bench menu):
 *   0x1 memset  >= 64 bytes: byte head to 8-byte alignment, shz_memset8 body (FMOV.D pairs), byte tail.
 *   0x2 memcpy  >= 32 bytes: shz_memcpy (32-byte destination prelude, then 8 / 4 / 2-byte bodies by source alignment).
 *   0x4 memmove >= 32 bytes: forward overlap (dst <= src) on shz_memcpy; backward overlap stays on newlib's memmove.
 * Below the size floors, and with a bit clear, the call goes straight to newlib (__real_*), so the many 4-16 byte copies
 * cost one compare more than before.
 * Results are byte-identical to newlib's: STRICT must stay identical.
 *
 * FPU / XMTRX: the SH4ZAM memcpy bodies use the FRONT bank only (dr0-dr14, declared clobbers) and toggle FPSCR.SZ in
 * pairs; XMTRX (the back bank) is never touched, so a skinning kernel's resident XMTRX survives. KOS saves the whole
 * FPU state on interrupt entry and thread switch, so a copy inside an IRQ handler is safe.
 * Caveat (upstream note, docs/lanes/sh4zam-upstream.md): shz_memcpy32_store_sh4_ does not name dr4-dr10 as inputs;
 * the load and store asm statements are adjacent in shz_memcpy32_sh4, and this file is built at -O2 and checked by
 * STRICT plus the identical-TA gates.
 */
#define NDEBUG 1
#include <stddef.h>
#include <stdint.h>
#include <sh4zam/shz_mem.h>

#ifndef RE4DC_SHZ_MEM_BOOT
#define RE4DC_SHZ_MEM_BOOT 0
#endif
#define SHZ_MEMSET_MIN 64u
#define SHZ_MEMCPY_MIN 32u

__attribute__((section(".data"))) unsigned re4dc_shz_mem_mask = RE4DC_SHZ_MEM_BOOT;
void re4dc_shz_mem_set(unsigned mask) { re4dc_shz_mem_mask = mask; }

/* Only main RAM (any P0-P3 mirror of 0x0C000000-0x0CFFFFFF) takes the SH4ZAM paths. VRAM, AICA sound RAM on the G2
 * bus (32-bit accesses only: no FMOV.D, no movca), the TA FIFO and P4 keep newlib. The first Flycast house run
 * without this check left the game in texture / movie loading (hwmodel-m6h / m7h, 10-15). */
static inline int shz_main_ram(const void* p, size_t n)
{
    const uintptr_t a = (uintptr_t) p & 0x1fffffffu;
    return ((uintptr_t) p >> 29) != 7u && a >= 0x0c000000u && a + n <= 0x0d000000u;
}

void* __real_memset(void* dst, int c, size_t n);
void* __real_memcpy(void* __restrict dst, const void* __restrict src, size_t n);
void* __real_memmove(void* dst, const void* src, size_t n);

void* __wrap_memset(void* dst, int c, size_t n)
{
    if (n < SHZ_MEMSET_MIN || !(re4dc_shz_mem_mask & 1u) || !shz_main_ram(dst, n))
        return __real_memset(dst, c, n);
    uint8_t* p = (uint8_t*) dst;
    const uint8_t b = (uint8_t) c;
    const size_t head = (8u - ((uintptr_t) p & 7u)) & 7u;
    if (head) { __real_memset(p, c, head); p += head; n -= head; }
    const size_t body = n & ~(size_t) 7u;
    const uint32_t w = (uint32_t) b * 0x01010101u;
    shz_memset8(p, ((uint64_t) w << 32) | w, body);
    if (n - body) __real_memset(p + body, c, n - body);
    return dst;
}

void* __wrap_memcpy(void* __restrict dst, const void* __restrict src, size_t n)
{
    if (n < SHZ_MEMCPY_MIN || !(re4dc_shz_mem_mask & 2u) || !shz_main_ram(dst, n) || !shz_main_ram(src, n)
        || ((uintptr_t) dst < (uintptr_t) src + n && (uintptr_t) src < (uintptr_t) dst + n)) /* overlap (UB): keep newlib */
        return __real_memcpy(dst, src, n);
    return shz_memcpy(dst, src, n);
}

void* __wrap_memmove(void* dst, const void* src, size_t n)
{
    if (n < SHZ_MEMCPY_MIN || !(re4dc_shz_mem_mask & 4u) || (uintptr_t) dst > (uintptr_t) src
        || !shz_main_ram(dst, n) || !shz_main_ram(src, n))
        return __real_memmove(dst, src, n);
    /* shz_memmove: dst <= src copies forward with shz_memcpy (each block is loaded before it is stored); its own
     * backward branch (memmove) is not reached here */
    return shz_memmove(dst, src, n);
}

/* platform/aliases-manual.ld maps unprefixed asm("memset") / asm("memcpy") references (route_ck.cpp, st2/st3 rooms)
 * to the C names; the wrap turns those into the raw "__wrap_*" names (no C prefix), so answer to them too. */
void* shz_wrap_memset_raw(void* d, int c, size_t n) __asm__("__wrap_memset") __attribute__((alias("__wrap_memset")));
void* shz_wrap_memcpy_raw(void* d, const void* s, size_t n) __asm__("__wrap_memcpy") __attribute__((alias("__wrap_memcpy")));
void* shz_wrap_memmove_raw(void* d, const void* s, size_t n) __asm__("__wrap_memmove") __attribute__((alias("__wrap_memmove")));
