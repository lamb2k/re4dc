// hostref: the C++ runtime pieces the game needs (no 32-bit libstdc++ on the build machine) and the
// floating-point environment.
#include "hostref.h"
#include <stdio.h>
#include <stdlib.h>
#include <xmmintrin.h>
#include <pmmintrin.h>

// operator new / delete: the game's own `operator new` (main_mem.cpp) allocates from the current heap;
// here every allocation comes from the guest arena (host_mem.cpp), so addresses fall in 0x8C000000+.
void* operator new(size_t n) { return host_alloc((uint32_t) n, 32, "new"); }
void* operator new[](size_t n) { return host_alloc((uint32_t) n, 32, "new[]"); }
void operator delete(void* p) noexcept { host_free(p); }
void operator delete[](void* p) noexcept { host_free(p); }
void operator delete(void* p, size_t) noexcept { host_free(p); }
void operator delete[](void* p, size_t) noexcept { host_free(p); }

extern "C" {

int __cxa_atexit(void (*)(void*), void*, void*) { return 0; }
int __cxa_guard_acquire(long long* g) { return *(char*) g == 0; }
void __cxa_guard_release(long long* g) { *(char*) g = 1; }
void __cxa_guard_abort(long long*) {}
void __cxa_pure_virtual() { fprintf(stderr, "re4ref: pure virtual call\n"); abort(); }
}

// SH-4 FPSCR.DN = 1: denormal inputs and results are zero (the old port runs with it; game30_trig.c
// notes the same for its exhaustive check). SSE: flush-to-zero + denormals-are-zero, round to nearest.
void host_fp_init()
{
    _MM_SET_FLUSH_ZERO_MODE(_MM_FLUSH_ZERO_ON);
    _MM_SET_DENORMALS_ZERO_MODE(_MM_DENORMALS_ZERO_ON);
    _MM_SET_ROUNDING_MODE(_MM_ROUND_NEAREST);
}
