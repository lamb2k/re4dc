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
#if defined(RE4DC_HOUSE_ARENA27) && RE4DC_HOUSE_ARENA27
#include <kos/cache.h>
#include <stdint.h>
#endif
#include <malloc.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#include "re4dc_platform.h"
#if defined(RE4DC_LOG_CRASH_TEST) && RE4DC_LOG_CRASH_TEST
extern "C" void re4dc_halt(const char*, int);
#endif

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

#if RE4DC_IMAGE_PAD_BYTES > 0
// IMAGE_PAD_BYTES (Makefile): image padding that moves _end (the KOS break, the arena, heap 4) to a reference image's.
static_assert(RE4DC_IMAGE_PAD_BYTES % 32 == 0);
extern "C" unsigned char re4dc_image_pad[RE4DC_IMAGE_PAD_BYTES];
unsigned char re4dc_image_pad[RE4DC_IMAGE_PAD_BYTES] __attribute__((used, aligned(32)));
#endif

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
#if RE4DC_IMAGE_PAD_BYTES > 0
    printf("re4dc_mem: image pad %lu bytes at %08lx\n", (unsigned long) RE4DC_IMAGE_PAD_BYTES, (unsigned long) re4dc_image_pad);
#endif
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
#ifndef RE4DC_LOG_TRIM
#define RE4DC_LOG_TRIM 0
#endif
#define RE4DC_LOG_SIZE (0x10000 - RE4DC_LOG_TRIM)
volatile unsigned long re4dc_log_magic __attribute__((aligned(32))) = 0x52453444;  // "RE4D"
#if defined(RE4DC_HOUSE_ARENA27) && RE4DC_HOUSE_ARENA27
// Keep the public 4-byte head symbol, but isolate its physical cache line.
// VI writes stage through P1; it must never evict a stale copy of this P2 head.
struct alignas(32) Arena27LogHeadLine { volatile uint32_t value; uint32_t pad[7]; };
Arena27LogHeadLine re4dc_arena27_log_head_line;
static_assert(sizeof(Arena27LogHeadLine)==32,"arena log head owns one cache line");
asm(".global _re4dc_log_head\n\t.type _re4dc_log_head, @object\n\t.set _re4dc_log_head, _re4dc_arena27_log_head_line\n\t.size _re4dc_log_head, 4");
#define re4dc_log_head re4dc_arena27_log_head_line.value
#else
volatile unsigned long re4dc_log_head;   // bytes written so far (wraps in the ring)
#endif
volatile unsigned long re4dc_stage;      // last platform stage reached (re4dc_set_stage)
#if defined(RE4DC_LOG_RING_HDR) && RE4DC_LOG_RING_HDR
// LOG_PLAY_KB (Makefile, play images only): the ring is shorter than the harness's 64 KB default, so 32 bytes before it
// say how long it is: "LGSZ", its complement, the size (read_log.py reads them; written with the first log byte).
struct Re4dcLogRing { unsigned long magic, nmagic, size, pad[5]; char buf[RE4DC_LOG_SIZE]; };
extern "C" { Re4dcLogRing re4dc_logring __attribute__((aligned(32))); }
#define RE4DC_LOG_STR2(x) #x
#define RE4DC_LOG_STR(x) RE4DC_LOG_STR2(x)
// a sized object symbol, so sh-elf-nm -S lists it like the plain array (route-build.sh syms.txt)
asm(".global _re4dc_logbuf\n\t.type _re4dc_logbuf, @object\n\t.set _re4dc_logbuf, _re4dc_logring+32\n\t"
    ".size _re4dc_logbuf, 65536-" RE4DC_LOG_STR(RE4DC_LOG_TRIM));
#define re4dc_logbuf re4dc_logring.buf
#else
char re4dc_logbuf[RE4DC_LOG_SIZE] __attribute__((aligned(32)));
#endif

// 1 while stdout is a separate device; 0 once fault.cpp routes the KOS
// debug output into this ring (printing would then loop back here).
int re4dc_log_console = 1;
unsigned char re4dc_dvd_buff[RE4DC_DVD_BUFF_BYTES] __attribute__((aligned(32)));

#if defined(RE4DC_HOUSE_ARENA27) && RE4DC_HOUSE_ARENA27
static uintptr_t arena27_log_alias(uintptr_t address){
#if defined(RE4DC_HOUSE_ARENA27_LOG_HOST_TEST)
    extern uintptr_t re4dc_house_arena27_log_test_alias(uintptr_t);
    return re4dc_house_arena27_log_test_alias(address);
#elif defined(__sh__)
    return address|uintptr_t(0xa0000000U);
#else
    return address;
#endif
}
static void arena27_log_startup(){
    static bool coherent=false;
    if(coherent)return;
#if defined(RE4DC_LOG_RING_HDR) && RE4DC_LOG_RING_HDR
    const uintptr_t begin=reinterpret_cast<uintptr_t>(&re4dc_logring);
    const unsigned bytes=sizeof(re4dc_logring);
#else
    const uintptr_t begin=reinterpret_cast<uintptr_t>(re4dc_logbuf);
    const unsigned bytes=sizeof(re4dc_logbuf);
#endif
    // KOS clears BSS through P1 after cache enable. Retire its dirty zeros
    // before the first P2 append. Bounded ranges avoid a whole-cache helper.
    for(unsigned off=0;off<bytes;off+=16384U){
        const unsigned count=bytes-off<16384U?bytes-off:16384U;
        dcache_wback_range(begin+off,count);dcache_inval_range(begin+off,count);
    }
    const uintptr_t head=reinterpret_cast<uintptr_t>(&re4dc_arena27_log_head_line);
    dcache_wback_range(head,32);dcache_inval_range(head,32);
    coherent=true;
}
#endif

// RE4DC_LOG_ATOMIC (LOGIC_TRACE=1 or TA_MATERIAL_DIAG=1): each call appends with interrupts off, so a
// preemptive thread (the aica sequencer's "aica: t=... note" lines) cannot splice its text into the
// middle of a trace line (LT/LU/LX/LP are one re4dc_log call each). Release builds keep the plain loop.
void re4dc_log_raw(const char* data, unsigned long len)
{
#if RE4DC_LOG_ATOMIC
    const int irq = irq_disable();
#endif
#if defined(RE4DC_HOUSE_ARENA27) && RE4DC_HOUSE_ARENA27
    arena27_log_startup();
    auto* const bytes=reinterpret_cast<volatile char*>(arena27_log_alias(reinterpret_cast<uintptr_t>(re4dc_logbuf)));
    auto* const head=reinterpret_cast<volatile uint32_t*>(arena27_log_alias(reinterpret_cast<uintptr_t>(&re4dc_log_head)));
#if defined(RE4DC_LOG_RING_HDR) && RE4DC_LOG_RING_HDR
    auto* const ring=reinterpret_cast<volatile Re4dcLogRing*>(arena27_log_alias(reinterpret_cast<uintptr_t>(&re4dc_logring)));
    if(!ring->magic){ring->size=RE4DC_LOG_SIZE;ring->nmagic=~0x5A53474CUL;ring->magic=0x5A53474CUL;}
#endif
    while(len--){bytes[*head%RE4DC_LOG_SIZE]=*data++;++*head;}
#else
#if defined(RE4DC_LOG_RING_HDR) && RE4DC_LOG_RING_HDR
    if (!re4dc_logring.magic) {
        re4dc_logring.size = RE4DC_LOG_SIZE;
        re4dc_logring.nmagic = ~0x5A53474CUL;
        re4dc_logring.magic = 0x5A53474CUL;  // "LGSZ"
    }
#endif
    while (len--) {
        re4dc_logbuf[re4dc_log_head % RE4DC_LOG_SIZE] = *data++;
        re4dc_log_head++;
    }
#endif
#if RE4DC_LOG_ATOMIC
    irq_restore(irq);
#endif
#if defined(RE4DC_LOG_CRASH_TEST) && RE4DC_LOG_CRASH_TEST
    // LOG_CRASH_TEST=N (test arm only): halt to the crash screen after the N-th log append, so its log rows can be
    // checked on a play image (LOG_PLAY_KB). (A misaligned store does not fault under Flycast.)
    static unsigned long calls;
    if (++calls == (unsigned long) RE4DC_LOG_CRASH_TEST) re4dc_halt("LOG_CRASH_TEST", RE4DC_LOG_CRASH_TEST);
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
