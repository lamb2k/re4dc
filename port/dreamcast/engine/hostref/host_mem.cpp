// hostref: guest memory. One 16 MiB arena mapped at the Dreamcast's main RAM address; data archives
// (core, player, weapon, room) are placed at the top, a deterministic first-fit heap fills the rest.
// The game's 13-heap API (main_mem.cpp) maps onto the one heap: the reference does not model heap
// pressure (risk 1 in SHELL_MAP.md: allocation failures that decide spawns are an E2 question).
// PC side (system headers); the game's memory API on top of it is host_memapi.cpp.
#include "hostref.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>

namespace {
struct Block {          // 32 bytes, so every payload stays 32-aligned
    uint32_t size;      // payload bytes (multiple of 32)
    uint32_t used;
    uint32_t magic;
    uint32_t pad[5];
};
constexpr uint32_t kMagic = 0x52453452u;   // "RE4R"
constexpr uint32_t kHeapBase = HOST_ARENA_BASE + 0x10000u;
uint32_t heap_end;       // first byte above the heap (data region below it grows down)
uint32_t fixed_top;      // data region: [fixed_top, arena end)
bool ready;
uint32_t used_bytes;

Block* first() { return (Block*) (uintptr_t) kHeapBase; }
Block* next(Block* b) { return (Block*) ((uint8_t*) b + sizeof(Block) + b->size); }
}

extern "C" void host_arena_init()
{
    if (ready) return;
    void* want = (void*) (uintptr_t) HOST_ARENA_BASE;
    void* p = mmap(want, HOST_ARENA_SIZE, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
    if (p != want) {
        fprintf(stderr, "re4ref: cannot map the guest arena at %08x\n", HOST_ARENA_BASE);
        exit(2);
    }
    fixed_top = HOST_ARENA_BASE + HOST_ARENA_SIZE;
    heap_end = HOST_ARENA_BASE + HOST_ARENA_SIZE - 0x00600000u;   // 6 MiB for data archives
    Block* b = first();
    b->size = heap_end - kHeapBase - sizeof(Block);
    b->used = 0;
    b->magic = kMagic;
    ready = true;
}

extern "C" void* host_fixed(uint32_t size, const char* why)
{
    host_arena_init();
    uint32_t top = (fixed_top - size) & ~31u;
    if (top < heap_end) {
        fprintf(stderr, "re4ref: data region full (%s, %u bytes)\n", why, size);
        exit(2);
    }
    fixed_top = top;
    memset((void*) (uintptr_t) top, 0, size);
    return (void*) (uintptr_t) top;
}

// Lane eng-load1: a door's room change returns the last room's archive when it is the data region's newest block (the
// region is a stack; the first room's archive lies under the weapon archive and stays). Returns 1 when returned.
extern "C" int host_fixed_release(void* p, uint32_t size)
{
    const uint32_t a = (uint32_t) (uintptr_t) p;
    if (a != fixed_top) return 0;
    fixed_top = (a + size + 31u) & ~31u;
    return 1;
}

extern "C" void* host_alloc(uint32_t size, uint32_t align, const char* why)
{
    (void) align;   // every block is 32-aligned
    host_arena_init();
    uint32_t need = (size + 31u) & ~31u;
    if (need == 0) need = 32;
    for (Block* b = first(); (uint32_t) (uintptr_t) b < heap_end; b = next(b)) {
        if (b->magic != kMagic) {
            fprintf(stderr, "re4ref: heap corrupt at %p (%s)\n", (void*) b, why);
            exit(3);
        }
        if (b->used) continue;
        // coalesce following free blocks
        for (Block* n = next(b); (uint32_t) (uintptr_t) n < heap_end && !n->used; n = next(b))
            b->size += sizeof(Block) + n->size;
        if (b->size < need) continue;
        if (b->size >= need + sizeof(Block) + 32) {
            Block* rest = (Block*) ((uint8_t*) b + sizeof(Block) + need);
            rest->size = b->size - need - sizeof(Block);
            rest->used = 0;
            rest->magic = kMagic;
            b->size = need;
        }
        b->used = 1;
        used_bytes += b->size;
        void* p = (uint8_t*) b + sizeof(Block);
        memset(p, 0, b->size);
        return p;
    }
    fprintf(stderr, "re4ref: heap exhausted (%s, %u bytes)\n", why, size);
    return 0;
}

extern "C" void host_free(void* p)
{
    if (!p) return;
    uint32_t a = (uint32_t) (uintptr_t) p;
    if (a < kHeapBase || a >= heap_end) return;   // data region or foreign: never freed
    Block* b = (Block*) ((uint8_t*) p - sizeof(Block));
    if (b->magic != kMagic || !b->used) {
        fprintf(stderr, "re4ref: bad free %p\n", p);
        return;
    }
    b->used = 0;
    used_bytes -= b->size;
}

extern "C" uint32_t host_heap_used() { return used_bytes; }

