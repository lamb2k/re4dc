// cache20.cpp: lane cache20 (cache-stalls, 2026-10-20; cache20.mk). Built only with GAME_SHZ_MEMSET=1 and/or SQ_OUT=1
// and/or PREF_WALK=1; with all three at 0 nothing here is compiled or linked (knob-off image unchanged).
//
// Question (user's console report 10-20 on the Test 21 preview): dense scenes run ~50-58 ms a frame on the console against
// ~38 MODELLED. The 10-15 console bench put 41-51% of CPU in cache stalls. These levers change only memory traffic, never
// the bytes written, so the logic trace stays STRICT; they are judged by console A/B only (hwmodel trust policy).
//
// re4dc_cache20_mask (run time; the benchmark disc's start screen sets it: arm A = 0, arm B = every built bit):
//   bit 0 SHZ   memset of >= 64 bytes through SH4ZAM's shz_memset8 (8-byte FMOV.D stores; newlib stores 4 bytes) for
//               every destination (the 10-15 GAME_SHZ_MEMSET, lane sh4zam-adopt 0efa5516, rebuilt here; exact).
//   bit 1 SQ    memset / memcpy of >= SQ_OUT_MIN bytes into cached main RAM: every whole 32-byte line of the destination
//               goes out through the SH-4 store queues (32-byte bursts, no write-allocate fill and, unlike MEM_MOVCA,
//               no cache line taken: the 16 KB operand cache keeps its contents). Each line is invalidated (ocbi) first
//               so no stale dirty copy can be written back over it later; the destination bytes are then only in RAM
//               and the next read fetches them. Head / tail bytes and other areas go to the normal routines.
//               QACR0/1 are saved and restored around each chunk with interrupts off (at most SQ_OUT_CHUNK bytes per
//               interrupts-off window), so a TA store-queue user that set QACR before the call is unaffected.
//               memcpy needs the source 4-byte aligned at the first whole destination line (else the normal routine).
//   bit 2 PREF  `pref` of the next unit in the walks (cache20_pref): the scenery chunk walk (next meshlet's corners and
//               strips; next meshlet header in the selection) and the Trans object / enemy loops (next model).
#if defined(RE4DC_CACHE20) && RE4DC_CACHE20
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <arch/irq.h>

#ifndef RE4DC_CACHE20_BOOT
#define RE4DC_CACHE20_BOOT 0u
#endif
#ifndef RE4DC_CACHE20_BUILT
#define RE4DC_CACHE20_BUILT 0u
#endif
#ifndef RE4DC_SQ_OUT_MIN
#define RE4DC_SQ_OUT_MIN 512u
#endif
#ifndef RE4DC_SQ_OUT_CHUNK
#define RE4DC_SQ_OUT_CHUNK 4096u
#endif

extern "C" {
volatile unsigned re4dc_cache20_mask = RE4DC_CACHE20_BOOT;
// counters for the benchmark log (calls / bytes that took each path)
unsigned re4dc_cache20_stat[6];
void re4dc_log(const char* fmt, ...);
}

#if (defined(RE4DC_SHZ_MEMSET) && RE4DC_SHZ_MEMSET) || (defined(RE4DC_SQ_OUT) && RE4DC_SQ_OUT)
#if defined(RE4DC_SHZ_MEMSET) && RE4DC_SHZ_MEMSET
#include <sh4zam/shz_mem.h>
#endif
extern "C" void* __real_memset(void* dst, int c, std::size_t n);
extern "C" void* __real_memcpy(void* dst, const void* src, std::size_t n);

namespace {
#define C20_QACR0 (*(volatile std::uint32_t*) 0xff000038u)
#define C20_QACR1 (*(volatile std::uint32_t*) 0xff00003cu)
// cached main RAM through P1 (0x8c000000..0x8cffffff) or P0/U0 (0x0c...): the only areas the SQ path writes
inline bool c20_ram(std::uintptr_t a, std::size_t n)
{
    const std::uintptr_t e = a + n - 1;
    return ((a >> 24) == 0x8cu && (e >> 24) == 0x8cu) || ((a >> 24) == 0x0cu && (e >> 24) == 0x0cu);
}
inline void c20_ocbi(std::uintptr_t p) { __asm__ __volatile__("ocbi @%0" : : "r"(p) : "memory"); }
inline void c20_pref(const void* p) { __asm__ __volatile__("pref @%0" : : "r"(p) : "memory"); }

#if defined(RE4DC_SQ_OUT) && RE4DC_SQ_OUT
// lines [lo, hi) (32-byte aligned, main RAM): fill with w, or copy from s (4-byte aligned) when s is set
void sq_lines(std::uintptr_t lo, std::uintptr_t hi, std::uint32_t w, const std::uint32_t* s)
{
    while (lo < hi) {
        const std::uintptr_t ce = hi - lo > RE4DC_SQ_OUT_CHUNK ? lo + RE4DC_SQ_OUT_CHUNK : hi;
        const int o = irq_disable();
        const std::uint32_t q0 = C20_QACR0, q1 = C20_QACR1;
        const std::uint32_t bits = (std::uint32_t) ((lo >> 24) & 0x1cu);
        C20_QACR0 = bits;
        C20_QACR1 = bits;
        for (std::uintptr_t p = lo; p < ce; p += 32) {
            c20_ocbi(p);
            volatile std::uint32_t* d = (volatile std::uint32_t*) (0xe0000000u | (p & 0x03ffffe0u));
            if (s) {
                c20_pref(s + 16);
                d[0] = s[0]; d[1] = s[1]; d[2] = s[2]; d[3] = s[3];
                d[4] = s[4]; d[5] = s[5]; d[6] = s[6]; d[7] = s[7];
                s += 8;
            } else {
                d[0] = w; d[1] = w; d[2] = w; d[3] = w; d[4] = w; d[5] = w; d[6] = w; d[7] = w;
            }
            c20_pref((const void*) d);
        }
        // wait for both queues (KOS sq_wait), then give QACR back
        volatile std::uint32_t* z = (volatile std::uint32_t*) 0xe0000000u;
        z[0] = 0;
        z[8] = 0;
        C20_QACR0 = q0;
        C20_QACR1 = q1;
        irq_restore(o);
        lo = ce;
    }
}
#endif

void* body_memset(void* dst, int c, std::size_t n)
{
#if defined(RE4DC_SHZ_MEMSET) && RE4DC_SHZ_MEMSET
    if (re4dc_cache20_mask & 1u) {
        ++re4dc_cache20_stat[0];
        volatile std::uint8_t* p = (volatile std::uint8_t*) dst;   // volatile: GCC must not turn the loops into memset
        const std::uint8_t b = (std::uint8_t) c;
        while ((std::uintptr_t) p & 7u) { *p++ = b; --n; }
        const std::size_t body = n & ~(std::size_t) 7u;
        const std::uint32_t w = (std::uint32_t) b * 0x01010101u;
        shz_memset8((void*) p, ((std::uint64_t) w << 32) | w, body);
        p += body;
        n -= body;
        while (n--) *p++ = b;
        return dst;
    }
#endif
    return __real_memset(dst, c, n);
}
}  // namespace

extern "C" void* __wrap_memset(void* dst, int c, std::size_t n)
{
    if (n < 64u) return __real_memset(dst, c, n);
#if defined(RE4DC_SQ_OUT) && RE4DC_SQ_OUT
    const std::uintptr_t a = (std::uintptr_t) dst;
    if ((re4dc_cache20_mask & 2u) && n >= RE4DC_SQ_OUT_MIN && c20_ram(a, n) && !irq_inside_int()) {
        const std::uintptr_t lo = (a + 31) & ~(std::uintptr_t) 31, hi = (a + n) & ~(std::uintptr_t) 31;
        if (lo > a) __real_memset(dst, c, lo - a);
        const std::uint32_t w = (std::uint32_t) (std::uint8_t) c * 0x01010101u;
        sq_lines(lo, hi, w, nullptr);
        if (a + n > hi) __real_memset((void*) hi, c, a + n - hi);
        ++re4dc_cache20_stat[2];
        re4dc_cache20_stat[3] += (unsigned) (hi - lo);
        return dst;
    }
#endif
    return body_memset(dst, c, n);
}
// A raw (unprefixed) "memset" reference (route_ck.cpp's asm, st2 / st3 rooms) wraps to the raw symbol (as MEMPROF).
extern "C" void* c20_raw_wrap_memset(void* d, int c, std::size_t n) __asm__("__wrap_memset");
extern "C" void* c20_raw_wrap_memset(void* d, int c, std::size_t n) { return __wrap_memset(d, c, n); }

#if defined(RE4DC_SQ_OUT) && RE4DC_SQ_OUT
extern "C" void* __wrap_memcpy(void* dst, const void* src, std::size_t n)
{
    const std::uintptr_t a = (std::uintptr_t) dst;
    if (!(re4dc_cache20_mask & 2u) || n < RE4DC_SQ_OUT_MIN || !c20_ram(a, n) || irq_inside_int())
        return __real_memcpy(dst, src, n);
    const std::uintptr_t lo = (a + 31) & ~(std::uintptr_t) 31, hi = (a + n) & ~(std::uintptr_t) 31;
    const unsigned char* s = (const unsigned char*) src;
    if (((std::uintptr_t) (s + (lo - a))) & 3u) return __real_memcpy(dst, src, n);
    // memcpy never overlaps; a source range that shares lines with the destination would read invalidated lines
    const std::uintptr_t sa = (std::uintptr_t) s;
    if (sa < ((a + n + 31) & ~(std::uintptr_t) 31) && sa + n > (a & ~(std::uintptr_t) 31)) return __real_memcpy(dst, src, n);
    if (lo > a) __real_memcpy(dst, s, lo - a);
    sq_lines(lo, hi, 0, (const std::uint32_t*) (s + (lo - a)));
    if (a + n > hi) __real_memcpy((void*) hi, s + (hi - a), a + n - hi);
    ++re4dc_cache20_stat[4];
    re4dc_cache20_stat[5] += (unsigned) (hi - lo);
    return dst;
}
#endif
#endif

// Benchmark census disc start screen (bench.cpp): arm A = no lever, arm B = every lever this image was built with.
extern "C" void re4dc_cache20_arm(int on)
{
    re4dc_cache20_mask = on ? (unsigned) RE4DC_CACHE20_BUILT : 0u;
    re4dc_log("cache20: arm %c mask=%u\n", on ? 'B' : 'A', re4dc_cache20_mask);
}

// Log line (benchmark scene ends): how much each path took since the last line.
extern "C" void re4dc_cache20_log(const char* why)
{
    re4dc_log("cache20: %s mask=%u shz_calls=%u sq_set=%u/%uB sq_cpy=%u/%uB\n", why ? why : "-", re4dc_cache20_mask,
              re4dc_cache20_stat[0], re4dc_cache20_stat[2], re4dc_cache20_stat[3], re4dc_cache20_stat[4],
              re4dc_cache20_stat[5]);
    for (unsigned& v : re4dc_cache20_stat) v = 0;
}
#endif  // RE4DC_CACHE20
