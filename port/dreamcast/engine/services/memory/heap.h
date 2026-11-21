// Native heap service (lane eng-svc5): the engine's allocator behind the SDK's OSAlloc interface (heap.cpp).
#pragma once
#include "types.h"

struct HeapCounters {
    u32 creates;     // heaps created
    u32 allocs;      // blocks handed out
    u32 frees;       // blocks taken back
    u32 fails;       // allocations no free cell could serve (0 returned, as the SDK)
    u32 bad_frees;   // frees refused: outside the heap, misaligned, or not a block the heap handed out
    u32 overlaps;    // heaps created over a range a live heap already covers
};

extern "C" {
extern HeapCounters heap_cnt;
// Control (alloctest, RE4_SVC_CONTROL=heapsplit): 1: a block is split when 32 bytes or more are left, not 64.
extern int heap_control;
void* OSInitAlloc(void* arenaStart, void* arenaEnd, int maxHeaps);
int OSCreateHeap(void* start, void* end);
void OSDestroyHeap(int heap);
int OSSetCurrentHeap(int heap);
void* OSAllocFromHeap(int heap, u32 size);
void OSFreeToHeap(int heap, void* ptr);
s32 OSCheckHeap(int heap);
}
