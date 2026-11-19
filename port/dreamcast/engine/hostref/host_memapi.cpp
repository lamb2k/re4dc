// hostref (game side): the game's memory API (include/main_mem.h) on the guest arena (host_mem.cpp).
#include "hostref.h"
#include "types.h"
#include "main_mem.h"


// ---- the game's memory API (include/main_mem.h) ----
void* mem_alloc(u32 size, const char* file, int line, int a, int b)
{
    (void) file; (void) line; (void) a; (void) b;
    return host_alloc(size, 32, "mem_alloc");
}
void Mem_free(void* p) { host_free(p); }
void Mem_free_h(void* p, int) { host_free(p); }
void* MemAlloc(u32 size, int) { return host_alloc(size, 32, "MemAlloc"); }
void MemFree(void* p) { host_free(p); }
u8 MemGetCurrentHeap() { return 4; }
void memclr_asm(void* dst, u32 n) { __builtin_memset(dst, 0, n); }
