/* alloctest.c (lane eng-svc5): the native heap service (services/memory/heap.cpp) against the SDK allocator the
 * reference and the image link today (src/lib/OSAlloc.c, its global symbols renamed orig_<symbol>; svc.mk alloctest).
 * Each side gets its own 4 MiB arena at the same alignment; the same random sequence of heap creations, allocations of
 * 0 to 24 KiB, frees of random live blocks (in any order) and heap destructions runs on both; every returned block's
 * offset from its arena, every heap handle and every failure must be equal, and the native OSCheckHeap must find both
 * lists sound after every step. Then the native refusals: a free of a block another heap handed out, a free of a
 * pointer inside a block, a second free of the same block (each must be refused and counted, the heap still sound).
 *
 *   alloctest [count]   RE4_SVC_CONTROL=heapsplit sets the native control (split at 32 bytes, not 64: must FAIL)
 * Exit 0 PASS, 1 on any difference or unsound heap. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef unsigned long u32;
typedef long s32;
void* orig_OSInitAlloc(void*, void*, int);
int orig_OSCreateHeap(void*, void*);
void orig_OSDestroyHeap(int);
void* orig_OSAllocFromHeap(int, u32);
void orig_OSFreeToHeap(int, void*);
void* OSInitAlloc(void*, void*, int);
int OSCreateHeap(void*, void*);
void OSDestroyHeap(int);
void* OSAllocFromHeap(int, u32);
void OSFreeToHeap(int, void*);
s32 OSCheckHeap(int);
struct HeapCounters { u32 creates, allocs, frees, fails, bad_frees, overlaps; };
extern struct HeapCounters heap_cnt;
extern int heap_control;

#define ARENA (4u << 20)
static uint8_t arena[2][ARENA + 64] __attribute__((aligned(64)));
static uint32_t seed = 0xC0FFEE11u;
static uint32_t rnd(void) { seed ^= seed << 13; seed ^= seed >> 17; seed ^= seed << 5; return seed; }

#define MAXLIVE 4096
struct blk { int heap; void* p[2]; };
static struct blk live[MAXLIVE];
static int nlive;
static unsigned diffs, unsound, steps, allocs, nulls, frees, creates, destroys;
static char first[200];
static void differ(const char* what, long a, long b)
{
    if (!diffs++) snprintf(first, sizeof first, "step %u %s: original %ld native %ld", steps, what, a, b);
}

int main(int argc, char** argv)
{
    unsigned N = argc > 1 ? (unsigned) atoi(argv[1]) : 200000;
    const char* c = getenv("RE4_SVC_CONTROL");
    if (c && !strcmp(c, "heapsplit")) heap_control = 1;
    uint8_t* base[2] = {arena[0] + 32, arena[1] + 32};   /* both 32 past a 64 boundary */
    uint8_t* lo[2];
    lo[0] = orig_OSInitAlloc(base[0], base[0] + ARENA, 13);
    lo[1] = OSInitAlloc(base[1], base[1] + ARENA, 13);
    if (lo[0] - base[0] != lo[1] - base[1]) differ("arena start", lo[0] - base[0], lo[1] - base[1]);
    int heaps[13], hslice[13], nheaps = 0, used[4] = {0, 0, 0, 0};
    /* heaps over disjoint slices of the arena (the reference's room heaps do not overlap) */
    const u32 slice = (ARENA - 4096) / 4;
    for (unsigned it = 0; it < N; it++) {
        steps = it;
        unsigned op = rnd() % 100;
        if (nheaps == 0 || (op < 1 && nheaps < 4)) {
            int sl = 0;
            while (used[sl]) sl++;
            used[sl] = 1;
            const u32 off = 1024 + sl * slice + (rnd() % 64), len = slice - 2048 - (rnd() % 4096);
            int h0 = orig_OSCreateHeap(lo[0] + off, lo[0] + off + len);
            int h1 = OSCreateHeap(lo[1] + off, lo[1] + off + len);
            if (h0 != h1) differ("heap handle", h0, h1);
            hslice[nheaps] = sl;
            heaps[nheaps++] = h1;
            creates++;
        } else if (op < 2 && nheaps > 1) {
            int k = rnd() % nheaps, h = heaps[k];
            orig_OSDestroyHeap(h), OSDestroyHeap(h);
            for (int i = 0; i < nlive; i++)
                if (live[i].heap == h) live[i--] = live[--nlive];
            used[hslice[k]] = 0;
            --nheaps;
            heaps[k] = heaps[nheaps], hslice[k] = hslice[nheaps];
            destroys++;
        } else if (op < 55 && nlive < MAXLIVE) {
            int h = heaps[rnd() % nheaps];
            u32 size = rnd() % 8 ? rnd() % 2048 : rnd() % 24576;
            void* p0 = orig_OSAllocFromHeap(h, size);
            void* p1 = OSAllocFromHeap(h, size);
            long o0 = p0 ? (uint8_t*) p0 - base[0] : -1, o1 = p1 ? (uint8_t*) p1 - base[1] : -1;
            if (o0 != o1) differ("block offset", o0, o1);
            if (p0 && p1) live[nlive++] = (struct blk){h, {p0, p1}};
            allocs++;
            if (!p1) nulls++;
        } else if (nlive) {
            int k = rnd() % nlive;
            orig_OSFreeToHeap(live[k].heap, live[k].p[0]);
            OSFreeToHeap(live[k].heap, live[k].p[1]);
            live[k] = live[--nlive];
            frees++;
        }
        for (int i = 0; i < nheaps; i++)
            if (OSCheckHeap(heaps[i]) < 0) unsound++;
    }
    printf("steps %u: creates %u destroys %u allocs %u (no room %u) frees %u; offsets differ %u%s%s; unsound checks %u\n", N,
           creates, destroys, allocs, nulls, frees, diffs, diffs ? "; first " : "", diffs ? first : "", unsound);
    /* the native refusals (the original has no such check: it would corrupt its lists) */
    unsigned bad0 = heap_cnt.bad_frees, refused_ok = 1;
    if (nheaps >= 2) {
        int ha = heaps[0], hb = heaps[1];
        void* p = OSAllocFromHeap(ha, 100);
        OSFreeToHeap(hb, p);                              /* another heap's block */
        OSFreeToHeap(ha, (uint8_t*) p + 32);              /* inside a block */
        OSFreeToHeap(ha, p);                              /* the block itself: taken */
        OSFreeToHeap(ha, p);                              /* a second time */
        refused_ok = heap_cnt.bad_frees - bad0 == 3 && OSCheckHeap(ha) >= 0 && OSCheckHeap(hb) >= 0;
        printf("refusals: %lu of 3 refused (wrong heap, inside a block, double free); heaps sound %d\n",
               heap_cnt.bad_frees - bad0, OSCheckHeap(ha) >= 0 && OSCheckHeap(hb) >= 0);
    }
    printf("native counters: creates %lu allocs %lu frees %lu fails %lu bad_frees %lu overlaps %lu; control %d\n", heap_cnt.creates,
           heap_cnt.allocs, heap_cnt.frees, heap_cnt.fails, heap_cnt.bad_frees, heap_cnt.overlaps, heap_control);
    int bad = diffs || unsound || !refused_ok;
    printf("%s\n", bad ? "FAIL" : "PASS: every handle, block and failure equal; every heap sound; refusals as they must");
    return bad;
}
