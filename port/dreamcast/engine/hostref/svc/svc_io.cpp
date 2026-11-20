// svc_io.cpp (PC side; lane eng-svc): file output and the environment for the game-side svc files (they include the
// game's own libc headers, so they reach the system C library through these).
#include "hostref.h"
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>

extern "C" void* svc_out_open(const char* name, const char* mode)
{
    const char* d = getenv("RE4_SVC_OUT");
    char p[1024];
    snprintf(p, sizeof p, "%s/%s", d && *d ? d : ".", name);
    return fopen(p, mode);
}
extern "C" void svc_out_write(void* f, const void* data, unsigned bytes) { if (f) fwrite(data, 1, bytes, (FILE*) f); }
extern "C" void svc_out_printf(void* f, const char* fmt, ...)
{
    if (!f) return;
    va_list ap;
    va_start(ap, fmt);
    vfprintf((FILE*) f, fmt, ap);
    va_end(ap);
}
extern "C" void svc_out_close(void* f) { if (f) fclose((FILE*) f); }
extern "C" const char* svc_env(const char* name) { return getenv(name); }
extern "C" double svc_atof(const char* s) { return atof(s); }

// The engine's service memory: 4 MiB at 0x8E000000 (outside the guest arena), mapped once.
extern "C" void* svc_region(uint32_t* bytes)
{
    static void* r;
    *bytes = 0x00400000u;
    if (!r) {
        void* want = (void*) (uintptr_t) 0x8E000000u;
        r = mmap(want, *bytes, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
        if (r != want) { fprintf(stderr, "svc: cannot map the service region\n"); exit(2); }
    }
    return r;
}
