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

// The engine's service memory: 16 MiB at 0x8E000000 (outside the guest arena), mapped once: the skeleton pool
// (1 MiB), the room's collision tables (to 4 MiB), the baked motion keys (from 4 MiB, lane eng-svc2).
extern "C" void svc_census_watch(uint32_t lo, uint32_t bytes) __attribute__((weak));
extern "C" void* svc_region(uint32_t* bytes)
{
    static void* r;
    *bytes = 0x01000000u;
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
    g_carve_left = 0x00400000u - 0x10000u - *bytes;   // the last 64 KiB: the original cloth's volume list (svc_cloth_glue)
    return r;
}
// The baked motion keys (bake/motion_keys.py; RE4_SVC_MK=<pack>), read once into the region at 4 MiB. Without
// RE4_SVC_MK the skeleton service keeps the original key decoder for every clip.
extern "C" const void* svc_mk_pack(uint32_t* bytes)
{
    static uint8_t* pk;
    static uint32_t n;
    if (!pk) {
        const char* path = getenv("RE4_SVC_MK");
        if (!path || !*path || !strcmp(path, "none")) return 0;   // none: every clip decoded from its keys (lane eng-svc3)
        FILE* f = fopen(path, "rb");
        if (!f) { fprintf(stderr, "svc: cannot read %s\n", path); exit(2); }
        fseek(f, 0, SEEK_END);
        n = (uint32_t) ftell(f);
        fseek(f, 0, SEEK_SET);
        uint32_t all;
        uint8_t* r = (uint8_t*) svc_region(&all);
        if (n > all - 0x00400000u) { fprintf(stderr, "svc: %s is %u bytes, the region holds %u\n", path, n, all - 0x00400000u); exit(2); }
        pk = r + 0x00400000u;
        if (fread(pk, 1, n, f) != n) { fprintf(stderr, "svc: short read %s\n", path); exit(2); }
        fclose(f);
    }
    *bytes = n;
    return pk;
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
// lane eng-skel1: the room carve (the collision tables), from the carve's top down, given back when the room is left
// (col_room_release), as in the engine image (host/e1_svc_mem.cpp)
static uint8_t* g_room_hi;
static uint8_t* g_room_top;
extern "C" void* svc_pool_carve_room(uint32_t bytes)
{
    if (!g_carve) {
        uint32_t b;
        svc_pool_base(&b);
    }
    if (!g_room_hi) g_room_hi = g_room_top = g_carve + g_carve_left;
    bytes = (bytes + 31u) & ~31u;
    if (bytes > g_carve_left) return 0;
    g_room_top -= bytes;
    g_carve_left -= bytes;
    return g_room_top;
}
extern "C" uint32_t svc_pool_room_reset(void* keep)
{
    if (!g_room_hi) return 0;
    uint8_t* to = keep ? (uint8_t*) keep : g_room_hi;
    if (to < g_room_top || to > g_room_hi) return 0;
    const uint32_t back = (uint32_t) (to - g_room_top);
    g_room_top = to;
    g_carve_left += back;
    return back;
}
extern "C" uint32_t svc_pool_room_used(void) { return g_room_hi ? (uint32_t) (g_room_hi - g_room_top) : 0; }
// Controls (RE4_SVC_CONTROL) and the check build's poison (RE4_SVC_POISON=0 turns it off), before the room is set
// up: the tables are made while the player is constructed.
extern "C" int skel_control_parent __attribute__((weak));
extern "C" int skel_control_no_ik __attribute__((weak));
extern "C" int skel_poison __attribute__((weak));
extern "C" float col_control_floor __attribute__((weak));
extern "C" int skel_control_mk __attribute__((weak));
extern "C" int skel_control_hist __attribute__((weak));
extern "C" int cloth_control_short __attribute__((weak));
extern "C" int col_control_grid __attribute__((weak));
extern "C" int col_verify __attribute__((weak));
extern "C" int col_grid_off __attribute__((weak));
extern "C" int cloth_control_nogravity __attribute__((weak));
extern "C" int cloth_control_wind __attribute__((weak));
extern "C" int cloth_passes __attribute__((weak));
extern "C" int col_sphere_grid_off __attribute__((weak));
extern "C" unsigned col_mask_min __attribute__((weak));
__attribute__((constructor)) static void svc_options()
{
    const char* c = getenv("RE4_SVC_CONTROL");
    if (c && *c) {
        if (!strncmp(c, "parent=", 7) && &skel_control_parent) skel_control_parent = atoi(c + 7);
        if (!strncmp(c, "noik", 4) && &skel_control_no_ik) skel_control_no_ik = 1;
        if (!strncmp(c, "mkrow", 5) && &skel_control_mk) skel_control_mk = 1;
        if (!strncmp(c, "mkroot", 6) && &skel_control_mk) skel_control_mk = 2;
        if (!strncmp(c, "mkcoarse", 8) && &skel_control_mk) skel_control_mk = 3;
        if (!strncmp(c, "histnone", 8) && &skel_control_hist) skel_control_hist = 1;
        if (!strncmp(c, "histfrozen", 10) && &skel_control_hist) skel_control_hist = 2;
        if (!strncmp(c, "clothshort", 10) && &cloth_control_short) cloth_control_short = 1;
        if (!strncmp(c, "colgrid", 7) && &col_control_grid) col_control_grid = 1;
        if (!strncmp(c, "clothnograv", 11) && &cloth_control_nogravity) cloth_control_nogravity = 1;
        if (!strncmp(c, "clothwind", 9) && &cloth_control_wind) cloth_control_wind = 1;
        if (!strncmp(c, "floor=", 6) && &col_control_floor) col_control_floor = (float) atof(c + 6);
    }
    uint32_t all;
    svc_region(&all);   // mapped before any game code runs (the hosted cloth's volume list lives in it)
    const char* p = getenv("RE4_SVC_POISON");
    if (&skel_poison) skel_poison = !(p && *p == '0');
    if (&col_verify) col_verify = !(p && *p == '0');   // the check build also tests every polygon the grid skips
    const char* cp = getenv("RE4_SVC_CLOTH_PASSES");   // 4: the cloth kernel in the original's pass order (proof)
    if (&cloth_passes && cp && *cp == '4') cloth_passes = 1;
    if (&cloth_passes && cp && *cp == '1') cloth_passes = 2;   // 1: one pass (measured, rejected)
    const char* sg = getenv("RE4_SVC_COLSPHERE");   // 0: the swept sphere without the grid (measurement; lane eng-svc3)
    if (&col_sphere_grid_off && sg && *sg == '0') col_sphere_grid_off = 1;
    const char* mm = getenv("RE4_SVC_COLMIN");      // the smallest leaf with masks (measurement; lane eng-svc3)
    if (&col_mask_min && mm && *mm) col_mask_min = (unsigned) atoi(mm);
    const char* g = getenv("RE4_SVC_COLGRID");
    if (&col_grid_off && g && *g == '0') col_grid_off = 1;   // measurement: the line queries without the grid
}
