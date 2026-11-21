// E1 main RAM map (lane eng-e1). Every KOS-heap block (the engine room pack: renderer pack, world runtime, archives)
// goes through the malloc wrappers and is tagged with the load stage; e1_memmap_sample prints the map after the room
// load (the low point: nothing is allocated while ticks run), with the image, the behaviour arena and the stack.
#include "e1_core.h"
#include "e1_engine.h"
#include <kos.h>
#include <malloc.h>
#include <stdlib.h>
#include <string.h>
extern "C" {
void* __real_malloc(size_t);void* __real_calloc(size_t,size_t);void* __real_memalign(size_t,size_t);
void* __real_realloc(void*,size_t);void __real_free(void*);
extern char e1_image_end asm("_end");
extern uintptr_t arch_stack_16m;
int e1_draw_opened_c(void);   // core/draw_e1.c: the renderer opened (video memory is the renderer's)
}
#define MM_BLOCKS 1024
struct MmBlock { uintptr_t lo, hi; uint32_t tag; };
static MmBlock mm_live[MM_BLOCKS];
static unsigned mm_n, mm_lost;
// lane eng-e1k: the bytes the tracked blocks hold, and their peak (two adds a call: the worst during load and play)
static size_t mm_bytes, mm_peak;
static void mm_add(void* p, size_t n){ if(!p)return; if(mm_n<MM_BLOCKS){mm_live[mm_n++]={(uintptr_t)p,(uintptr_t)p+n,e1_state[0]}; mm_bytes+=n; if(mm_bytes>mm_peak)mm_peak=mm_bytes;} else mm_lost++; }
static void mm_del(void* p){ if(!p)return; for(unsigned i=0;i<mm_n;i++)if(mm_live[i].lo==(uintptr_t)p){mm_bytes-=mm_live[i].hi-mm_live[i].lo; mm_live[i]=mm_live[--mm_n];return;} }
extern "C" {
void* __wrap_malloc(size_t n){void* p=__real_malloc(n);mm_add(p,n);return p;}
void* __wrap_calloc(size_t a,size_t b){void* p=__real_calloc(a,b);mm_add(p,a*b);return p;}
void* __wrap_memalign(size_t a,size_t n){void* p=__real_memalign(a,n);mm_add(p,n);return p;}
void* __wrap_realloc(void* q,size_t n){void* p=__real_realloc(q,n);if(p||!n){mm_del(q);mm_add(p,n);}return p;}
void __wrap_free(void* p){mm_del(p);__real_free(p);}
}
#define STACK_PAINT 0x5a5aa5a5u
static uintptr_t stack_lo, stack_hi;
void e1_memmap_boot()
{
    stack_hi = arch_stack_16m; stack_lo = stack_hi - 64 * 1024;
    uintptr_t sp; __asm__ volatile("mov r15,%0" : "=r"(sp));
    for (uintptr_t a = stack_lo; a + 512 < sp; a += 4) *(volatile uint32_t*) a = STACK_PAINT;
}
static unsigned stack_high_water(){ uintptr_t a=stack_lo; while(a<stack_hi && *(volatile uint32_t*)a==STACK_PAINT)a+=4; return stack_hi-a; }
static int cmpb(const void* a,const void* b){uintptr_t x=((const MmBlock*)a)->lo,y=((const MmBlock*)b)->lo;return (x>y)-(x<y);}
void e1_memmap_sample()
{
    static MmBlock b[MM_BLOCKS]; unsigned n = mm_n; memcpy(b, mm_live, n * sizeof(MmBlock));
    qsort(b, n, sizeof(MmBlock), cmpb);
    unsigned overlaps = 0; uint32_t tagb[8] = {0};
    for (unsigned i = 0; i < n; i++) {
        if (i && b[i].lo < b[i-1].hi) overlaps++;
        if (b[i].lo < (uintptr_t) &e1_image_end) overlaps++;
        if (b[i].hi > E1_ARENA_LO && b[i].lo < E1_ARENA_HI) overlaps++;
        tagb[b[i].tag & 7] += b[i].hi - b[i].lo;
    }
    uintptr_t top = (uintptr_t) sbrk(0);
    if (top > E1_ARENA_LO) overlaps++;
    struct mallinfo mi = mallinfo();
    e1_log("E1 MEM image 8c010000-%08lx heap blocks %u %08lx-%08lx sbrk %08lx | boot %lu arena-init %lu room %lu draw %lu | "
           "arena %08lx-%08lx | stack %08lx-%08lx high water %u | free to arena %ld | mallinfo used %lu free %lu | overlaps %u lost %u\n",
           (unsigned long) (uintptr_t) &e1_image_end, n, (unsigned long) (n ? b[0].lo : 0), (unsigned long) (n ? b[n-1].hi : 0), (unsigned long) top,
           (unsigned long) (tagb[0] + tagb[1]), (unsigned long) tagb[2], (unsigned long) tagb[3], (unsigned long) (tagb[4] + tagb[5]),
           (unsigned long) E1_ARENA_LO, (unsigned long) E1_ARENA_HI, (unsigned long) stack_lo, (unsigned long) stack_hi,
           stack_high_water(), (long) (E1_ARENA_LO - top), (unsigned long) mi.uordblks, (unsigned long) mi.fordblks, overlaps, mm_lost);
    for (unsigned i = 0; i < n; i++)
        if (b[i].hi - b[i].lo >= 16384)
            e1_log("E1 MEMBLK %08lx %lu stage %lu\n", (unsigned long) b[i].lo, (unsigned long) (b[i].hi - b[i].lo), (unsigned long) b[i].tag);
    if (e1_draw_opened_c()) e1_log("E1 MEM before play: vram free %lu\n", (unsigned long) pvr_mem_available());
}

// ---- after play (lane eng-e1k, H-016.6): the record's memory facts are taken when the ticks are over, not only before
// them. The stack's paint is a high-water mark (the worst depth any tick reached); its lowest 1 KiB is the guard, which
// must still hold the paint. The KOS heap's tracked bytes keep their peak in the wrappers (the worst through load and
// play); sbrk only grows, so its top after play is the worst. Video memory is sampled after play (the renderer takes
// it at pack open; no cheap per-tick sample is taken).
#define STACK_GUARD 1024u
static unsigned stack_guard_broken()
{
    unsigned bad = 0;
    for (uintptr_t a = stack_lo; a < stack_lo + STACK_GUARD; a += 4) bad += *(volatile uint32_t*) a != STACK_PAINT;
    return bad;
}
void e1_memmap_after()
{
    const uintptr_t top = (uintptr_t) sbrk(0);
    struct mallinfo mi = mallinfo();
    const unsigned bad = stack_guard_broken();
    e1_log("E1 MEM after play: stack high water %u of %u guard %s | heap blocks %u in use %lu peak %lu | sbrk %08lx free to arena %ld "
           "| mallinfo used %lu free %lu | vram free %ld | lost %u\n", stack_high_water(), (unsigned) (stack_hi - stack_lo),
           bad ? "BROKEN" : "intact", mm_n, (unsigned long) mm_bytes, (unsigned long) mm_peak, (unsigned long) top,
           (long) (E1_ARENA_LO - top), (unsigned long) mi.uordblks, (unsigned long) mi.fordblks,
           e1_draw_opened_c() ? (long) pvr_mem_available() : -1l, mm_lost);
    if (bad) e1_log("E1 STACK GUARD BROKEN: %u of %u guard words below %08lx overwritten\n", bad, STACK_GUARD / 4,
                    (unsigned long) (stack_lo + STACK_GUARD));
}
// Control STACKX (boot file): at tick 300 one guard word is overwritten, as a stack overrun would; the after-play check
// must break the guard and the selector FAIL the scene.
void e1_memmap_control(unsigned tick)
{
    static int on = -1;
    if (on < 0) { file_t f = fs_open("/cd/STACKX", O_RDONLY); on = f >= 0; if (f >= 0) { fs_close(f); e1_log("E1 STACKX: a guard word overwritten at tick 300 (control)\n"); } }
    if (on && tick == 300) *(volatile uint32_t*) (stack_lo + 64) = 0;
}
