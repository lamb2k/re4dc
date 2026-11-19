// Behaviour arena with the 13-heap API (lane eng-e1, E1).
//
// One fixed region [E1_ARENA_LO, E1_ARENA_HI) independent of the image, managed by the SDK allocator the reference
// build runs (OSAlloc from src/lib, so cells, rounding and first-fit order are the reference's). The hosted behaviour
// sees the original API: mem_alloc / mem_calloc with heap and flag, MemAlloc / MemFree, Mem_free, operator new
// (zeroed, current heap), MemCreateHeap / MemDestroyHeap / MemSetCurrentHeap / MemReplaceHeap / suspend / signal.
// Every allocation and free is counted per heap; the high-water mark of each heap is reported (e1_arena).
#include "types.h"
#include "main_mem.h"
#include "db_log.h"
#include "e1_engine.h"
#include <string.h>
#include <stdio.h>

extern "C" {
void* OSInitAlloc(void* arenaStart, void* arenaEnd, int maxHeaps);
int OSCreateHeap(void* start, void* end);
void OSDestroyHeap(int heap);
int OSSetCurrentHeap(int heap);
void* OSAllocFromHeap(int heap, u32 size);
void OSFreeToHeap(int heap, void* ptr);
s32 OSCheckHeap(int heap);
}

MemHeap Heap[MEM_HEAP_NUM];
OSHeapCell* cell_main;
OSHeapCell* cell_game;
OSHeapCell* cell_dll;
u32 _epy_base = 40;
static u8 CurrentHeap;
E1ArenaStats e1_arena;
static u32 arena_base;

extern "C" void e1_arena_init(void)
{
    for (int i = 0; i < MEM_HEAP_NUM; i++) {
        Heap[i].handle = -1;
        Heap[i].status = 0;
    }
    arena_base = (u32) OSInitAlloc((void*) E1_ARENA_LO, (void*) E1_ARENA_HI, MEM_HEAP_NUM);
    arena_base = (arena_base + 0x1F) & ~0x1Fu;
    // Heap 0 (system) over the whole arena, as the original's boot heap; the game replaces it with its room heaps.
    MemCreateHeap(0, arena_base, E1_ARENA_HI);
    MemSetCurrentHeap(0);
}

int memGetHeapSattus(int no) { return Heap[no].status; }
int memCheckHeapActive(int no) { return Heap[no].status == 0; }
int MemSetCurrentHeap(int no)
{
    if (memCheckHeapActive(no) && Heap[no].handle >= 0) {
        CurrentHeap = no;
        OSSetCurrentHeap(Heap[no].handle);
        return 1;
    }
    return 0;
}
u8 MemGetCurrentHeap() { return CurrentHeap; }
u32 MemGetHeapStartAddr(int no) { return Heap[no].start; }
u32 MemGetHeapEndAddr(int no) { return Heap[no].end; }
void MemSuspendHeap(int no) { Heap[no].status = 1; }
void MemSignalHeap(int no) { Heap[no].status = 0; }
int MemCreateHeap(int no, u32 start, u32 end)
{
    if (!memCheckHeapActive(no)) return 0;
    if (Heap[no].handle >= 0) MemDestroyHeap(no);
    Heap[no].handle = OSCreateHeap((void*) start, (void*) end);
    if (Heap[no].handle < 0) return 0;
    Heap[no].start = start;
    Heap[no].end = end;
    e1_arena.heap_lo[no] = start;
    e1_arena.heap_hi[no] = end;
    e1_arena.used[no] = 0;
    e1_log("ARENA create heap %d %08lx-%08lx\n", no, (unsigned long) start, (unsigned long) end);
    return 1;
}
int MemDestroyHeap(int no)
{
    if (Heap[no].handle < 0) return 0;
    OSDestroyHeap(Heap[no].handle);
    Heap[no].handle = -1;
    e1_arena.used[no] = 0;
    return 1;
}
int MemReplaceHeap(int from, int to)
{
    // The original moves a heap's range to another number (stage -> room heap); the engine keeps the descriptor.
    Heap[to] = Heap[from];
    Heap[from].handle = -1;
    e1_arena.heap_lo[to] = Heap[to].start;
    e1_arena.heap_hi[to] = Heap[to].end;
    e1_arena.used[to] = e1_arena.used[from];
    e1_arena.peak[to] = e1_arena.peak[from];
    if (CurrentHeap == from) MemSetCurrentHeap(to);
    return 1;
}

static int heap_of(void* p)
{
    for (int i = 0; i < MEM_HEAP_NUM; i++)
        if (Heap[i].handle >= 0 && (u32) p >= Heap[i].start && (u32) p < Heap[i].end) return i;
    return -1;
}

// size rounded to 32 bytes; a 32-byte "MAD" tag follows tagged blocks (file != NULL), as the original.
void* mem_alloc(u32 size, const char* file, int line, int flag, int heap)
{
    if (size == 0) return NULL;
    if (heap == MEM_HEAP_CURRENT) heap = CurrentHeap;
    if (!memCheckHeapActive(heap) || Heap[heap].handle < 0) return NULL;
    size = (size + 0x1F) & ~0x1Fu;
    u32 cell = file ? size + 0x20 : size;
    u8* p = (u8*) OSAllocFromHeap(Heap[heap].handle, cell);
    e1_arena.allocs++;
    if (!p) {
        e1_arena.fails[heap]++;
        if (flag == 1) e1_log("ARENA alloc FAILED heap %d size %lu at %s(%d)\n", heap, (unsigned long) size, file ? file : "-", line);
        return NULL;
    }
    if (file) {
        u8* tag = p + size;
        tag[0] = 0; tag[1] = 'M'; tag[2] = 'A'; tag[3] = 'D';
        const char* name = strrchr(file, '/');
        snprintf((char*) tag + 4, 0x1C, "%s(%d)", name ? name + 1 : file, line);
    }
    e1_arena.used[heap] += ((OSHeapCell*) (p - 0x20))->size;
    if (e1_arena.used[heap] > e1_arena.peak[heap]) e1_arena.peak[heap] = e1_arena.used[heap];
    return p;
}
void* mem_calloc(u32 size, const char* file, int line, int flag, int heap)
{
    void* p = mem_alloc(size, file, line, flag, heap);
    if (p) memset(p, 0, (size + 0x1F) & ~0x1Fu);
    return p;
}
void Mem_free_h(void* p, int heap)
{
    if (!p) return;
    int h = heap_of(p);
    if (h < 0) {
        e1_log("ARENA free of a block outside the arena %08lx\n", (unsigned long) p);
        return;
    }
    s32 cell = ((OSHeapCell*) ((u8*) p - 0x20))->size;
    memclr_asm(p, cell - 0x20);
    OSFreeToHeap(Heap[h].handle, p);
    e1_arena.used[h] -= cell;
    e1_arena.frees++;
}
void Mem_free(void* p) { Mem_free_h(p, CurrentHeap); }
void* MemAlloc(u32 size, int flag) { return mem_alloc(size, "MemAlloc", 646, 1, MEM_HEAP_CURRENT); }
void MemFree(void* p) { Mem_free(p); }
void* Debug_alloc(u32 size, int flag) { return mem_alloc(size, "Debug_alloc", 0, flag, MEM_HEAP_CURRENT); }
void Debug_free(void* p) { Mem_free(p); }
void* operator new(unsigned int size) { return mem_calloc(size, "operator new", 0, 1, MEM_HEAP_CURRENT); }
void* operator new[](unsigned int size) { return mem_calloc(size, "operator new", 0, 1, MEM_HEAP_CURRENT); }
void operator delete(void* p) { Mem_free(p); }
void operator delete[](void* p) { Mem_free(p); }
void operator delete(void* p, unsigned int) { Mem_free(p); }
void operator delete[](void* p, unsigned int) { Mem_free(p); }
extern "C" void memclr_asm(void* dst, u32 n) { memset(dst, 0, n); }
extern "C" void memset_asm(void* dst, int c, u32 n) { memset(dst, c, n); }
