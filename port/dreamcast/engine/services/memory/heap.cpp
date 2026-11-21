// Native heap service (lane eng-svc5): the engine's allocator behind the SDK's OSAlloc interface (OSInitAlloc,
// OSCreateHeap, OSDestroyHeap, OSSetCurrentHeap, OSAllocFromHeap, OSFreeToHeap, OSCheckHeap), which the behaviour's
// memory API (host/e1_heap.cpp: mem_alloc, Mem_free, operator new) sits on. Write-up: docs/engine/SERVICES.md section 35.
//
// Placement is the SDK allocator's, so the behaviour's blocks land where the reference's do: the descriptor table at the
// start of the arena, 32-byte cells with a 32-byte header {prev, next, size} (e1_heap reads the size at p - 0x20), first
// fit over the free list in address order, a block split when 64 bytes or more are left, freed blocks merged with their
// neighbours. What is the engine's own (none of it moves a block the reference places):
//   - every free is checked: a pointer outside the heap's range, not 32-aligned, or whose cell is not on the heap's
//     allocated list is refused, counted and logged (the SDK walked into it: the E1 audit's heap 0 / heap 4 alias would
//     free a heap-4 block into heap 0's lists);
//   - a heap created over a range a live heap already covers is counted and logged (heap_cnt.overlaps), not refused:
//     the behaviour's heap table does this today (e1_heap.cpp's heap 0 over the whole arena), the image lane decides;
//   - OSCheckHeap returns the free bytes after checking both lists (links, order, sizes, ranges): -1 on any fault.
#include "types.h"
#include "heap.h"

extern "C" {
HeapCounters heap_cnt;
int heap_control;
volatile int __OSCurrHeap = -1;
void e1_log(const char* fmt, ...) __attribute__((weak));
}

namespace {
struct Cell {
    Cell* prev;
    Cell* next;
    s32 size;   // including the 32-byte header
};
struct HeapDesc {   // 12 bytes in the arena, as the SDK's
    s32 size;       // -1: unused
    Cell* free;
    Cell* allocated;
};
const u32 kAlign = 32, kHeader = 32;
inline u32 split_min() { return heap_control == 1 ? 32u : 64u; }   // control "heapsplit"
HeapDesc* g_desc;
int g_count;
const int kMaxHeaps = 32;
u32 g_lo[kMaxHeaps], g_hi[kMaxHeaps];   // each live heap's range (engine side, not in the arena)

void note(const char* what, int heap, const void* p)
{
    if (e1_log) e1_log("HEAP %s heap %d %08lx\n", what, heap, (unsigned long) (u32) p);
}
// insert into the address-ordered free list, merging with the neighbours
Cell* insert_free(Cell* list, Cell* cell)
{
    Cell* prev = 0;
    Cell* next = list;
    while (next && cell > next) prev = next, next = next->next;
    cell->next = next;
    cell->prev = prev;
    if (next) {
        next->prev = cell;
        if ((u8*) cell + cell->size == (u8*) next) {
            cell->size += next->size;
            next = next->next;
            cell->next = next;
            if (next) next->prev = cell;
        }
    }
    if (!prev) return cell;
    prev->next = cell;
    if ((u8*) prev + prev->size == (u8*) cell) {
        prev->size += cell->size;
        prev->next = next;
        if (next) next->prev = prev;
    }
    return list;
}
Cell* extract(Cell* list, Cell* cell)
{
    if (cell->next) cell->next->prev = cell->prev;
    if (!cell->prev) return cell->next;
    cell->prev->next = cell->next;
    return list;
}
bool live(int heap) { return heap >= 0 && heap < g_count && g_desc[heap].size >= 0; }
}   // namespace

extern "C" {

void* OSInitAlloc(void* arenaStart, void* arenaEnd, int maxHeaps)
{
    if (maxHeaps > kMaxHeaps) maxHeaps = kMaxHeaps;
    g_desc = (HeapDesc*) arenaStart;
    g_count = maxHeaps;
    for (int i = 0; i < maxHeaps; i++) g_desc[i] = {-1, 0, 0};
    __OSCurrHeap = -1;
    (void) arenaEnd;
    return (void*) (((u32) (g_desc + maxHeaps) + kAlign - 1) & ~(kAlign - 1));
}

int OSCreateHeap(void* start, void* end)
{
    const u32 lo = ((u32) start + kAlign - 1) & ~(kAlign - 1), hi = (u32) end & ~(kAlign - 1);
    for (int h = 0; h < g_count; h++)
        if (live(h) && lo < g_hi[h] && g_lo[h] < hi) {
            heap_cnt.overlaps++;
            note("create overlaps a live heap", h, (void*) lo);
        }
    for (int h = 0; h < g_count; h++) {
        HeapDesc& d = g_desc[h];
        if (d.size >= 0) continue;
        d.size = (s32) (hi - lo);
        Cell* c = (Cell*) lo;
        c->prev = c->next = 0;
        c->size = d.size;
        d.free = c;
        d.allocated = 0;
        g_lo[h] = lo, g_hi[h] = hi;
        heap_cnt.creates++;
        return h;
    }
    return -1;
}

void OSDestroyHeap(int heap)
{
    if (!live(heap)) return;
    g_desc[heap] = {-1, 0, 0};
    g_lo[heap] = g_hi[heap] = 0;
    if (__OSCurrHeap == heap) __OSCurrHeap = -1;
}

int OSSetCurrentHeap(int heap)
{
    const int prev = __OSCurrHeap;
    __OSCurrHeap = heap;
    return prev;
}

void* OSAllocFromHeap(int heap, u32 size)
{
    if (!live(heap)) return 0;
    HeapDesc& d = g_desc[heap];
    const s32 need = (s32) ((size + kHeader + kAlign - 1) & ~(kAlign - 1));
    Cell* c = d.free;
    while (c && need > c->size) c = c->next;   // first fit, in address order
    if (!c) {
        heap_cnt.fails++;
        return 0;
    }
    const s32 left = c->size - need;
    if ((u32) left < split_min()) {
        d.free = extract(d.free, c);   // the whole cell
    } else {
        Cell* rest = (Cell*) ((u8*) c + need);   // the rest stays free, in the cell's place in the list
        c->size = need;
        rest->size = left;
        rest->prev = c->prev;
        rest->next = c->next;
        if (rest->next) rest->next->prev = rest;
        if (rest->prev) rest->prev->next = rest;
        else d.free = rest;
    }
    c->next = d.allocated;   // allocated list: newest first
    c->prev = 0;
    if (d.allocated) d.allocated->prev = c;
    d.allocated = c;
    heap_cnt.allocs++;
    return (u8*) c + kHeader;
}

void OSFreeToHeap(int heap, void* ptr)
{
    const u32 p = (u32) ptr;
    if (!live(heap) || p < g_lo[heap] + kHeader || p >= g_hi[heap] || (p & (kAlign - 1))) {
        heap_cnt.bad_frees++;
        note("free outside the heap refused", heap, ptr);
        return;
    }
    HeapDesc& d = g_desc[heap];
    Cell* c = (Cell*) (p - kHeader);
    Cell* a = d.allocated;
    while (a && a != c) a = a->next;
    if (!a) {
        heap_cnt.bad_frees++;
        note("free of a block not allocated refused", heap, ptr);
        return;
    }
    d.allocated = extract(d.allocated, c);
    d.free = insert_free(d.free, c);
    heap_cnt.frees++;
}

// The free bytes of the heap after checking both lists (links, address order of the free list, cell sizes and
// ranges, and that free plus allocated covers the heap); -1 on any fault.
s32 OSCheckHeap(int heap)
{
    if (!live(heap)) return -1;
    const HeapDesc& d = g_desc[heap];
    s32 free = 0, used = 0;
    const Cell* prev = 0;
    for (const Cell* c = d.free; c; prev = c, c = c->next) {
        if ((u32) c < g_lo[heap] || (u32) c + c->size > g_hi[heap] || c->size < (s32) kHeader || c->prev != prev ||
            (prev && (u8*) prev + prev->size >= (u8*) c))
            return -1;
        free += c->size;
    }
    prev = 0;
    for (const Cell* c = d.allocated; c; prev = c, c = c->next) {
        if ((u32) c < g_lo[heap] || (u32) c + c->size > g_hi[heap] || c->size < (s32) kHeader || c->prev != prev) return -1;
        used += c->size;
    }
    return free + used == d.size ? free : -1;
}

}   // extern "C"
