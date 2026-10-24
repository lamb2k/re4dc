// Small platform pieces: cache control, performance counters, the SN host
// file API, the asm memset/memclr units, the SDK texture-palette lookup, the
// room-archive decoder entry (a C port is the next dependency) and the
// bridges for members the sources call through GCC 2.95 link names.
#include <kos.h>
#include "cache_lines.h"
#include <string.h>

#include "re4dc_platform.h"

typedef unsigned char u8;
typedef unsigned short u16;
typedef signed long s32;
typedef unsigned long u32;

extern "C" {

// ---- cache (DC* = the SDK's data-cache ops)
void DCFlushRange(void* addr, u32 n) { RE4DC_DCACHE_WBACK((uintptr_t) addr, n); }
void DCFlushRangeNoSync(void* addr, u32 n) { RE4DC_DCACHE_WBACK((uintptr_t) addr, n); }
void DCStoreRange(void* addr, u32 n) { RE4DC_DCACHE_WBACK((uintptr_t) addr, n); }
void DCStoreRangeNoSync(void* addr, u32 n) { RE4DC_DCACHE_WBACK((uintptr_t) addr, n); }
#if (defined(RE4DC_DCINV_PURGE) && RE4DC_DCINV_PURGE) || (defined(RE4DC_DCINV_AUDIT) && RE4DC_DCINV_AUDIT)
}  // extern "C"
#if defined(RE4DC_DCINV_AUDIT) && RE4DC_DCINV_AUDIT
#include <stdio.h>
// DCINV_AUDIT=1 (Makefile): dirty operand-cache lines a DCInvalidateRange would discard, per caller. The OC is 16 KiB
// direct mapped (KOS CCR: no OIX, no OC RAM): entry = address bits 13..5; the address array word holds the line's
// physical tag (bits 28..10), U (dirty, bit 1) and V (bit 0).
namespace {
struct DcinvCaller { u32 pr, calls, dirty, last_addr, last_n; };
const int kCallers = 24;
DcinvCaller g_dc[kCallers];
int g_dc_n;
u32 g_dc_calls, g_dc_dirty, g_dc_dirty_logged;
unsigned long long g_dc_last_ms;
inline u32 oc_entry(u32 line) { return *(volatile u32*) (0xF4000000u | (line & 0x3FE0u)); }
u32 dirty_lines(uintptr_t a, u32 n)
{
    if (!n || (a & 0xE0000000u) == 0xA0000000u) return 0;  // P2 is not cached
    const u32 s = (u32) a & ~31u, e = (u32) a + n;
    u32 d = 0;
    if (e - s <= 16384) {
        for (u32 l = s; l < e; l += 32) {
            const u32 v = oc_entry(l);
            if ((v & 3u) == 3u && (v & 0x1FFFFC00u) == (l & 0x1FFFFC00u)) ++d;
        }
    } else {
        const u32 ps = s & 0x1FFFFFFFu, pe = ps + (e - s);
        for (u32 i = 0; i < 512; ++i) {
            const u32 v = *(volatile u32*) (0xF4000000u | (i << 5));
            if ((v & 3u) != 3u) continue;
            const u32 pa = (v & 0x1FFFFC00u) | ((i << 5) & 0x3E0u);
            if (pa >= ps && pa < pe) ++d;
        }
    }
    return d;
}
void dcinv_audit(void* addr, u32 n, u32 pr)
{
    const u32 d = dirty_lines((uintptr_t) addr, n);
    ++g_dc_calls;
    int i = 0;
    while (i < g_dc_n && g_dc[i].pr != pr) ++i;
    if (i == g_dc_n) {
        if (g_dc_n < kCallers) g_dc[g_dc_n++].pr = pr;
        else i = kCallers - 1;  // the last slot also collects the overflow
    }
    DcinvCaller& c = g_dc[i];
    ++c.calls;
    if (!d) return;
    const bool first = c.dirty == 0;
    c.dirty += d;
    c.last_addr = (u32) (uintptr_t) addr;
    c.last_n = n;
    g_dc_dirty += d;
    if (irq_inside_int()) return;
    if (first)
        re4dc_log("dcinv: DIRTY pr=%08lx addr=%08lx n=%lu dirty=%lu lines (first for this caller; total %lu)\n",
                  (unsigned long) pr, (unsigned long) (uintptr_t) addr, (unsigned long) n, (unsigned long) d,
                  (unsigned long) g_dc_dirty);
    const unsigned long long now = timer_ms_gettime64();
    if (g_dc_dirty != g_dc_dirty_logged && now - g_dc_last_ms >= 5000) {
        g_dc_last_ms = now;
        g_dc_dirty_logged = g_dc_dirty;
        int top[3] = {-1, -1, -1};
        for (int k = 0; k < g_dc_n; ++k) {
            for (int j = 0; j < 3; ++j) {
                if (top[j] < 0 || g_dc[k].dirty > g_dc[top[j]].dirty) {
                    for (int m = 2; m > j; --m) top[m] = top[m - 1];
                    top[j] = k;
                    break;
                }
            }
        }
        char line[160];
        int o = snprintf(line, sizeof(line), "dcinv: calls %lu dirty %lu |", (unsigned long) g_dc_calls,
                         (unsigned long) g_dc_dirty);
        for (int j = 0; j < 3 && top[j] >= 0 && g_dc[top[j]].dirty && o < (int) sizeof(line); ++j)
            o += snprintf(line + o, sizeof(line) - o, " %08lx:%lu", (unsigned long) g_dc[top[j]].pr,
                          (unsigned long) g_dc[top[j]].dirty);
        re4dc_log("%s\n", line);
    }
}
}  // namespace
#endif
extern "C" {
void __attribute__((noinline)) DCInvalidateRange(void* addr, u32 n)
{
#if defined(RE4DC_DCINV_AUDIT) && RE4DC_DCINV_AUDIT
    dcinv_audit(addr, n, (u32) (uintptr_t) __builtin_return_address(0));
#endif
#if defined(RE4DC_DCINV_PURGE) && RE4DC_DCINV_PURGE
    // ocbp per line (write back, then invalidate: no store is lost). Not KOS dcache_purge_range: above 39936 bytes it
    // purges the whole cache through a 16 KiB static buffer (static growth starves heap 4).
    for (uintptr_t l = (uintptr_t) addr & ~(uintptr_t) 31, e = (uintptr_t) addr + n; l < e; l += 32)
        __asm__ __volatile__("ocbp @%0" : : "r"(l) : "memory");
#else
    dcache_inval_range((uintptr_t) addr, n);
#endif
}
#else
void DCInvalidateRange(void* addr, u32 n) { dcache_inval_range((uintptr_t) addr, n); }
#endif

// ---- performance monitor / MSR
void PPCMtmmcr0(u32 v) { (void) v; }
void PPCMtmmcr1(u32 v) { (void) v; }
void PPCMtpmc1(u32 v) { (void) v; }
void PPCMtpmc2(u32 v) { (void) v; }
void PPCMtpmc3(u32 v) { (void) v; }
void PPCMtpmc4(u32 v) { (void) v; }
u32 PPCMfpmc1(void) { return 0; }
void PPCMtmsr(u32 v) { (void) v; }
void PPCSync(void) {}

// ---- SN host file system (dev-mode only): unavailable
int PCinit(void) { return -1; }
int PCopen(const char* path, int flags, int mode) { (void) path; (void) flags; (void) mode; return -1; }
int PCcreat(const char* path, int mode) { (void) path; (void) mode; return -1; }
int PCclose(int fd) { (void) fd; return -1; }
int PCread(int fd, void* buf, int n) { (void) fd; (void) buf; (void) n; return -1; }
int PCwrite(int fd, const void* buf, int n) { (void) fd; (void) buf; (void) n; return -1; }
int PClseek(int fd, int ofs, int whence) { (void) fd; (void) ofs; (void) whence; return -1; }

// ---- game/memset_2.s
void memclr_asm(void* dst, u32 n) { memset(dst, 0, n); }
void memset_asm(void* dst, int c, u32 n) { memset(dst, c, n); }

// ---- charPipeline texPalette.c
struct TEXDescriptor { u32 w[2]; };  // textureHeader, CLUTHeader
struct TEXPalette { u32 versionNumber; u32 numDescriptors; TEXDescriptor* descriptorArray; };
TEXDescriptor* TEXGet(TEXPalette* pal, u32 id) { return &pal->descriptorArray[id]; }

// ---- game/yz2asm.s: the room-archive decoder loop. Not ported yet; the
// first room load reports it.
void yz2Decode_Decode(void* ctx, void* dst, u32 size, void* ev)
{
    (void) ctx; (void) dst; (void) size; (void) ev;
    re4dc_missing("yz2Decode_Decode (room archive decoder)");
}

}  // extern "C"

// ---- bridges: members the sources reach through their GCC 2.95 link name
// where the SH-4 build has no out-of-line copy.
struct Event;
extern "C" void re4dc_FlgOnStatus(Event* e, u32 no) asm("FlgOnStatus__5EventUl");
void re4dc_FlgOnStatus(Event* e, u32 no)
{
    // include/event.h: `f = &StatusFlag (0x44); f[no >> 5] |= 0x80000000 >> (no & 0x1F)`
    u32* f = (u32*) ((u8*) e + 0x44);
    f[no >> 5] |= 0x80000000u >> (no & 0x1F);
}

#if defined(RE4DC_MAPLE_RECV_PURGE) && RE4DC_MAPLE_RECV_PURGE
// MAPLE_RECV_PURGE=1 (Makefile): before KOS clears a maple frame's receive buffer through P2 (and maple DMA writes the
// device's answer there), write back and drop the buffer's cached P1 lines, so a dirty line left by the calloc of the
// device (or the start-up .bss clear of the detect frame) can never be evicted over the answer. Same buffer KOS picks:
// recv_buf_arr rounded up to 32 bytes, 1024 bytes.
extern "C" void __real_maple_frame_init(maple_frame_t* frame);
extern "C" void __wrap_maple_frame_init(maple_frame_t* frame)
{
    const uintptr_t b = (((uintptr_t) frame->recv_buf_arr + 31) & ~(uintptr_t) 31 & 0x1FFFFFFFu) | 0x80000000u;
    for (uintptr_t l = b; l < b + 1024; l += 32)
        __asm__ __volatile__("ocbp @%0" : : "r"(l) : "memory");
    __real_maple_frame_init(frame);
}
#endif
