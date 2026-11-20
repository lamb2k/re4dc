// svc_io.cpp (PC side; lane eng-svc): file output and the environment for the game-side svc files (they include the
// game's own libc headers, so they reach the system C library through these).
#include "hostref.h"
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <string.h>

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
extern "C" void svc_census_watch(uint32_t lo, uint32_t bytes) __attribute__((weak));
extern "C" void* svc_region(uint32_t* bytes)
{
    static void* r;
    *bytes = 0x00400000u;
    if (!r) {
        void* want = (void*) (uintptr_t) 0x8E000000u;
        r = mmap(want, *bytes, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
        if (r != want) { fprintf(stderr, "svc: cannot map the service region\n"); exit(2); }
        if (svc_census_watch) svc_census_watch(0x8E000000u, *bytes);
    }
    return r;
}

// ---- the native services' host side (lane eng-svc), PC side so that every svc build shares it ----
// The service memory: the skeleton pool (1 MiB, tables come and go with the actors) and the room's collision
// tables above it, in the 4 MiB region at 0x8E000000.
static uint8_t* g_carve;
static uint32_t g_carve_left;
extern "C" void* svc_pool_base(uint32_t* bytes)
{
    uint32_t all;
    uint8_t* r = (uint8_t*) svc_region(&all);
    *bytes = 0x00100000;
    g_carve = r + *bytes;
    g_carve_left = all - *bytes;
    return r;
}
extern "C" void* svc_pool_carve(uint32_t bytes)
{
    if (!g_carve) {
        uint32_t b;
        svc_pool_base(&b);
    }
    bytes = (bytes + 31u) & ~31u;
    if (bytes > g_carve_left) return 0;
    void* p = g_carve;
    g_carve += bytes;
    g_carve_left -= bytes;
    return p;
}
// Controls (RE4_SVC_CONTROL) and the check build's poison (RE4_SVC_POISON=0 turns it off), before the room is set
// up: the tables are made while the player is constructed.
extern "C" int skel_control_parent __attribute__((weak));
extern "C" int skel_control_no_ik __attribute__((weak));
extern "C" int skel_poison __attribute__((weak));
extern "C" float col_control_floor __attribute__((weak));
__attribute__((constructor)) static void svc_options()
{
    const char* c = getenv("RE4_SVC_CONTROL");
    if (c && *c) {
        if (!strncmp(c, "parent=", 7) && &skel_control_parent) skel_control_parent = atoi(c + 7);
        if (!strncmp(c, "noik", 4) && &skel_control_no_ik) skel_control_no_ik = 1;
        if (!strncmp(c, "floor=", 6) && &col_control_floor) col_control_floor = (float) atof(c + 6);
    }
    const char* p = getenv("RE4_SVC_POISON");
    if (&skel_poison) skel_poison = !(p && *p == '0');
}
