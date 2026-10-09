// Memory layout: one arena from the KOS heap, carved into the live regions the
// GameCube build keeps at fixed addresses. SndInit starts at 0x80370000; the
// source SystemMemMap names are boundary labels, not allocation owners. The
// DVD staging buffer is re4dc_dvd_buff below, outside this arena. What remains
// after sound and the archives is the game's OSAlloc arena. The
// GameCube had 21 MB after its ELF for these; the Dreamcast has 16 MB in
// total, so the heap is smaller and R4_ASSET_RESIDENCY_PLAN.md owns the
// consequences. The frame-buffer and FIFO regions (0x80460000, 0x803F0000)
// are not carved: the Dreamcast renderer owns its own.
#include <kos.h>
#include <malloc.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#include "re4dc_platform.h"

struct Re4dcMemLayout re4dc_mem;

// SND_DATA_TOP 0x80370000 to GX FIFO 0x803F0000 on the GameCube (512 KiB). SndInit fills it from
// the bottom (stream header, tables, 4 x 16 KiB blocks, 64 KiB block/BGM zone, 4 x 32 KiB stream
// buffers, sub data) and nothing uses the rest; SOUND_REGION_BYTES (Makefile) may carve less.
static const unsigned long kSoundSize = RE4DC_SOUND_REGION_BYTES;
static_assert(kSoundSize >= 0x40000 && kSoundSize <= 0x80000 && kSoundSize % 32 == 0);
// Makefile regenerates the one-object budget header when the selected profile
// changes. Default remains the full reference; candidate bytes come from the
// compact-core report, including identity records/table and 32-byte alignment.
static const unsigned long kCoreSize = RE4DC_CORE_RESIDENT_BYTES;
static_assert(kCoreSize >= 32 && kCoreSize <= 0x234000 && kCoreSize % 32 == 0);
static const unsigned long kOptionSize = RE4DC_OPTION_RESIDENT_BYTES;
static_assert(kOptionSize >= 32 && kOptionSize <= 0x40000 && kOptionSize % 32 == 0);
static const unsigned long kPlayerSize = RE4DC_PLAYER_RESIDENT_BYTES;  // 0x807EC000-0x80904000
static const unsigned long kWeaponSize = RE4DC_WEAPON_RESIDENT_BYTES;
static_assert(kPlayerSize >= 32 && kPlayerSize <= 0x118000 && kPlayerSize % 32 == 0);
static_assert(kWeaponSize >= 32 && kWeaponSize <= 0x70000 && kWeaponSize % 32 == 0);
static const unsigned long kMinHeap = 0x300000;
static const unsigned long kArenaKosBytes = RE4DC_ARENA_KOS_BYTES;
static_assert(kArenaKosBytes % 32 == 0 && kArenaKosBytes <= 0x40000);

static unsigned char g_frameBuffer[2][32] __attribute__((aligned(32)));
static unsigned char g_fifo[32] __attribute__((aligned(32)));

extern "C" {

void re4dc_mem_init(void)
{
    if (re4dc_mem.arena_lo) {
        return;
    }
    printf("re4dc_mem: selected core reservation %lu bytes\n", kCoreSize);
    printf("re4dc_mem: selected option reservation %lu bytes\n", kOptionSize);
    printf("re4dc_mem: selected player %lu weapon %lu bytes\n", kPlayerSize, kWeaponSize);
    unsigned long fixed = kSoundSize + kCoreSize + kOptionSize + kPlayerSize + kWeaponSize;
    // Take the largest arena the KOS heap gives us, leaving the runtime some room.
    // A selected candidate may leave RE4DC_ARENA_KOS_BYTES more to KOS (Makefile).
    unsigned long want = 13 * 1024 * 1024 - kArenaKosBytes;
    printf("re4dc_mem: arena request %lu bytes (%lu left to KOS)\n", want, kArenaKosBytes);
    unsigned long step = 0x40000;
#if defined(RE4DC_ARENA_FIT) && RE4DC_ARENA_FIT
    // ARENA_FIT=1: when the full request does not fit under the KOS break limit, take what does,
    // leaving RE4DC_ARENA_FIT_KOS_BYTES to KOS, in 4 KiB steps. The 256 KiB fallback below turns
    // an image a few KB too large for the full arena into 256 KiB less heap 4 (the arena's top).
    {
        const struct mallinfo mi = mallinfo();
        const unsigned long limit = (unsigned long) _arch_mem_top - THD_KERNEL_STACK_SIZE;
        const unsigned long brk = (unsigned long) sbrk(0);
        const unsigned long room = (brk < limit ? limit - brk : 0) + (unsigned long) mi.keepcost;
        const unsigned long reserve = RE4DC_ARENA_FIT_KOS_BYTES + 64;  // + chunk header, alignment
        const unsigned long fit = room > reserve ? (room - reserve) & ~0xFFFUL : 0;
        if (fit < want) {
            want = fit;
            printf("re4dc_mem: arena fit %lu bytes (%lu left to KOS)\n", want, room - want);
        }
        step = 0x1000;
    }
#endif
#if RE4DC_POISON_RAM
    {
        // Everything between the KOS break and the kernel stack is unowned (mm_sbrk's limit);
        // stay a page below the live stack pointer as well.
        unsigned long sp;
        __asm__ volatile("mov r15, %0" : "=r"(sp));
        unsigned long limit = (unsigned long) _arch_mem_top - THD_KERNEL_STACK_SIZE;
        if (sp - 4096 < limit) limit = sp - 4096;
        const unsigned long brk = ((unsigned long) sbrk(0) + 31) & ~31UL;
        if (brk < limit) memset((void*) brk, RE4DC_POISON_RAM, limit - brk);
        printf("re4dc_mem: POISON_RAM %02x break %08lx-%08lx\n", (unsigned) RE4DC_POISON_RAM, brk, limit);
    }
#endif
    void* p = NULL;
    while (want >= fixed + kMinHeap) {
        p = memalign(32, want);
        if (p) {
            break;
        }
        want -= step;
    }
    if (!p) {
        printf("re4dc_mem_init: no arena (need %lu)\n", fixed + kMinHeap);
        arch_exit();
    }
#if RE4DC_POISON_RAM
    memset(p, RE4DC_POISON_RAM, want);  // the arena may also reuse freed KOS chunks
    printf("re4dc_mem: POISON_RAM %02x arena %08lx-%08lx\n", (unsigned) RE4DC_POISON_RAM, (unsigned long) p,
           (unsigned long) p + want);
#endif
    unsigned long lo = (unsigned long) p;
    re4dc_mem.arena_lo = lo;
    re4dc_mem.arena_hi = lo + want;
    // dvd is the legacy SystemMemMap lower-bound marker, not DVD storage.
    // Only SndInit owns this arena region; actual DVD staging is separate.
    re4dc_mem.dvd = lo;
    re4dc_mem.sound = lo;
    re4dc_mem.core = re4dc_mem.sound + kSoundSize;
    re4dc_mem.option = re4dc_mem.core + kCoreSize;
    re4dc_mem.player = re4dc_mem.option + kOptionSize;
    re4dc_mem.weapon = re4dc_mem.player + kPlayerSize;
    re4dc_mem.heap = re4dc_mem.weapon + kWeaponSize;
    re4dc_mem.heap_end = re4dc_mem.arena_hi;
    printf("re4dc_mem: arena %08lx-%08lx dvd %08lx sound %08lx core %08lx option %08lx player %08lx weapon %08lx heap %08lx-%08lx (%lu KB)\n",
           re4dc_mem.arena_lo, re4dc_mem.arena_hi, re4dc_mem.dvd, re4dc_mem.sound, re4dc_mem.core,
           re4dc_mem.option, re4dc_mem.player, re4dc_mem.weapon, re4dc_mem.heap, re4dc_mem.heap_end,
           (re4dc_mem.heap_end - re4dc_mem.heap) / 1024);
}

// SndInit's layout end (the sub data's end) against the carved sound region (SOUND_REGION_BYTES).
void re4dc_sound_region_check(unsigned long end)
{
    const unsigned long used = end - re4dc_mem.sound;
    printf("re4dc_mem: sound region used %lu of %lu bytes\n", used, kSoundSize);
    if (used > kSoundSize) {
        printf("re4dc_mem: sound region overflow into core (SOUND_REGION_BYTES too small)\n");
        arch_exit();
    }
}

void* re4dc_frame_buffer(int index)
{
    return g_frameBuffer[index & 1];
}

void* re4dc_gx_fifo(void)
{
    return g_fifo;
}

// The boot log also lives in RAM (a ring the capture tooling reads out of the
// emulator process: evidence read_log.py), because the serial console is not
// captured by the Flycast launcher used here.
#define RE4DC_LOG_SIZE 0x10000
volatile unsigned long re4dc_log_magic __attribute__((aligned(32))) = 0x52453444;  // "RE4D"
volatile unsigned long re4dc_log_head;   // bytes written so far (wraps in the ring)
volatile unsigned long re4dc_stage;      // last platform stage reached (re4dc_set_stage)
char re4dc_logbuf[RE4DC_LOG_SIZE] __attribute__((aligned(32)));

// 1 while stdout is a separate device; 0 once fault.cpp routes the KOS
// debug output into this ring (printing would then loop back here).
int re4dc_log_console = 1;
unsigned char re4dc_dvd_buff[0x20000] __attribute__((aligned(32)));

// RE4DC_LOG_ATOMIC (LOGIC_TRACE=1 builds, game30.mk): each call appends with interrupts off, so a
// preemptive thread (the aica sequencer's "aica: t=... note" lines) cannot splice its text into the
// middle of a trace line (LT/LU/LX/LP are one re4dc_log call each). Release builds keep the plain loop.
void re4dc_log_raw(const char* data, unsigned long len)
{
#if RE4DC_LOG_ATOMIC
    const int irq = irq_disable();
#endif
    while (len--) {
        re4dc_logbuf[re4dc_log_head % RE4DC_LOG_SIZE] = *data++;
        re4dc_log_head++;
    }
#if RE4DC_LOG_ATOMIC
    irq_restore(irq);
#endif
}

static void logAppend(const char* s)
{
    re4dc_log_raw(s, strlen(s));
}

void re4dc_set_stage(unsigned long stage)
{
    re4dc_stage = stage;
}

void re4dc_log(const char* fmt, ...)
{
    char line[256];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(line, sizeof(line), fmt, ap);
    va_end(ap);
    logAppend(line);
    if (re4dc_log_console) {
        fputs(line, stdout);
    }
}

#if RE4DC_VMU_DEBUG_SLOT
void re4dc_dbgslot_ring(unsigned kind, unsigned a, unsigned b);
#endif
void re4dc_crash_screen_missing(const char* name) __attribute__((weak));
void re4dc_missing(const char* name)
{
    // Keep the first failure before the intentional sleep loop hides it from
    // the watchdog. The hook is absent when CRASH_SCREEN is disabled.
    if (re4dc_crash_screen_missing) re4dc_crash_screen_missing(name);
    re4dc_log("RE4DC MISSING: %s called; halting\n", name);
#if RE4DC_VMU_DEBUG_SLOT
    re4dc_dbgslot_ring(2, (unsigned) name, 0);
#endif
    fflush(stdout);
    for (;;) {
        thd_sleep(1000);
    }
}

}  // extern "C"
