// REL modules: on the GameCube the stage, enemy, weapon and sub-screen code
// lives in relocatable modules the game reads from disc, links (OSLink) and
// enters through the header's prolog. Here every module in the Makefile's
// MODULES list is a partially linked object in the image (tools/gen_modules.py)
// and this table maps a REL header id to its entry points; OSLink (os.cpp)
// rewrites the header the game read so pModule->prolog() / epilog() reach
// the compiled code and the loader's control flow (readRelData, DLL_Link,
// prolog) stays as recovered.
//
// Link-time state follows the GameCube loader. A fresh link (the header was
// just read from disc) starts from the module's pristine .data and a zeroed
// .bss, exactly what a newly read REL has; the pristine .data is captured at
// the module's first link, before any of its code has run. A relink of the
// same header after OSUnlink (cRoomData::stopRelData / restartRelData around
// the sub screen) keeps the state: the source restores its bss backup there.
// tools/gen_modules.py bounds each module's .data/.bss span and rejects
// modules with static constructors, so the empty _ctors list the prologs walk
// is also what a per-link constructor pass would run.

#include "re4dc_platform.h"

typedef unsigned long u32;

// ROUTE_OVL=1 (Makefile, with ROUTE_CH13=1): pl0f and em2f are room overlays (/cd/dc/pl0f.ovl,
// /cd/dc/em2f.ovl, tools/link.sh). The table entry stays empty until the game links the module;
// the bind then reads the overlay into heap 4 and relocates it. The unlink, or the room heap
// rebuild (gameRoomMemInit), fills the code with trap instructions and frees it.
#ifndef RE4DC_ROUTE_OVL
#define RE4DC_ROUTE_OVL 0
#endif
#define RE4DC_MODULE_OVL (RE4DC_SUBSCREEN_OVL || RE4DC_ROUTE_OVL)

extern "C" {
// The stage entry objects (src/st<N>/st<N>.cpp) walk the linker-script
// ctor / dtor label lists renamed to these; no module has constructors
// (checked when the module object is linked), so both lists are empty.
void (*re4dc_module_ctors[])(void) = {0};
void (*re4dc_module_dtors[])(void) = {0};
#define MODULE(name) void name##_prolog(void); void name##_epilog(void); \
    extern char re4dc_mod_##name##_data[], re4dc_mod_##name##_data_end[], re4dc_mod_##name##_bss[], \
        re4dc_mod_##name##_bss_end[], re4dc_mod_##name##_pristine[];
// WORLD_STAGE_MODULES=1 rows first: tools/assetpipe/wiring.py wire() appends after the default list's last row.
#if defined(RE4DC_WORLD_STAGE_MODULES) && RE4DC_WORLD_STAGE_MODULES
MODULE(st2_0)
MODULE(st4_0)
MODULE(pl11)
#endif
#if defined(RE4DC_WORLD_ROOM_MODULES) && RE4DC_WORLD_ROOM_MODULES
MODULE(st2_2)
MODULE(em1f)
#endif
MODULE(st1_0)
MODULE(st1_1)
MODULE(st1_2)
MODULE(st1_3)
MODULE(wep02)
MODULE(em12)
MODULE(em23)
MODULE(em15)
MODULE(em26)
MODULE(em28)
MODULE(em21)
MODULE(em2a)
MODULE(em29)
MODULE(em2e)
MODULE(em13)
MODULE(em27)
#if defined(RE4DC_ROUTE_CH13) && RE4DC_ROUTE_CH13
MODULE(em18)
MODULE(em17)
MODULE(em24)
#if !RE4DC_ROUTE_OVL
MODULE(pl0f)
MODULE(em2f)
#if defined(RE4DC_ROUTE_CH21) && RE4DC_ROUTE_CH21
MODULE(em22)
#endif
#endif
#endif
#if defined(RE4DC_WEAPON_MODULES) && RE4DC_WEAPON_MODULES
MODULE(wep01)
MODULE(wep07)
MODULE(wep09)
MODULE(wep11)
MODULE(wep13)
MODULE(wep19)
#endif
#if RE4DC_SUBSCREEN && !RE4DC_SUBSCREEN_OVL
MODULE(Sscrn)
#endif
#undef MODULE
}

struct Re4dcModule {
    u32 id;             // REL header id (config/G4BE08/modules/<mod>/rel.json module_id)
    const char* name;
    void (*prolog)(void);
    void (*epilog)(void);
    char* data;         // writable state span (gen_modules.py state.ld)
    char* data_end;
    char* bss;
    char* bss_end;
    char* pristine;     // .data as linked, captured before the first prolog
};

#define MODULE(id, name) {id, #name, name##_prolog, name##_epilog, re4dc_mod_##name##_data, \
    re4dc_mod_##name##_data_end, re4dc_mod_##name##_bss, re4dc_mod_##name##_bss_end, re4dc_mod_##name##_pristine}
#if RE4DC_MODULE_OVL
// SUBSCREEN_OVL=1: the Sscrn entry is filled by re4dc_module_overlay() each time sscrn_bridge.cpp
// has read and relocated sscrn.ovl; the image holds no pointer into the overlay. ROUTE_OVL=1: the
// same for pl0f / em2f, loaded by re4dc_module_bind() below.
static Re4dcModule g_modules[] = {
#else
static const Re4dcModule g_modules[] = {
#endif
#if defined(RE4DC_WORLD_STAGE_MODULES) && RE4DC_WORLD_STAGE_MODULES
    MODULE(75, st2_0), // WORLD_STAGE_MODULES: r200..r203, r207, r208, r210, r222
    MODULE(96, st4_0), // WORLD_STAGE_MODULES: the St4 rooms
    MODULE(47, pl11),  // WORLD_STAGE_MODULES: the partner Ashley (cSubAshley; r210 spawns her at entry)
#endif
#if defined(RE4DC_WORLD_ROOM_MODULES) && RE4DC_WORLD_ROOM_MODULES
    MODULE(83, st2_2), // WORLD_ROOM_MODULES: r211..r219
    MODULE(109, em1f), // WORLD_ROOM_MODULES: the St4 Ganados (r406, r40a, r40b, r40d, r410)
#endif
    MODULE(74, st1_0),
    MODULE(73, st1_1),
    MODULE(78, st1_2),
    MODULE(86, st1_3),
    MODULE(4, wep02),
    MODULE(18, em12),
    MODULE(7, em23),
    MODULE(19, em15),
    MODULE(14, em26),
    MODULE(17, em28),
    MODULE(6, em21),
    MODULE(28, em2a),  // r100 after state (flag 10): bear traps and tripwire bombs
    MODULE(27, em29),  // r106: script-load
    MODULE(38, em2e),  // r106: script-load
    MODULE(34, em13),  // r104: enabled-later
    MODULE(16, em27),  // r107: entry
#if defined(RE4DC_ROUTE_CH13) && RE4DC_ROUTE_CH13
    MODULE(22, em18),  // ROUTE_CH13: r102 (the merchant): enabled-later,script-load
    MODULE(21, em17),  // ROUTE_CH13: r108: enabled-later,entry,script-load
    MODULE(8, em24),   // ROUTE_CH13: r108 (room entry) / r10a: entry
#if RE4DC_ROUTE_OVL
    {43, "pl0f", 0, 0, 0, 0, 0, 0, 0},  // ROUTE_CH13: r10b: entry (Leon's boat); overlay pl0f.ovl
    {39, "em2f", 0, 0, 0, 0, 0, 0, 0},  // ROUTE_CH13: r10b: enabled-later,script-load (Del Lago); overlay em2f.ovl
#else
    MODULE(43, pl0f),  // ROUTE_CH13: r10b: entry (Leon's boat)
    MODULE(39, em2f),  // ROUTE_CH13: r10b: enabled-later,script-load (Del Lago)
#endif
#if defined(RE4DC_ROUTE_CH21) && RE4DC_ROUTE_CH21
#if RE4DC_ROUTE_OVL
    {5, "em22", 0, 0, 0, 0, 0, 0, 0},   // ROUTE_CH21: r11b: script-spawn (the shore wolves); overlay em22.ovl
#else
    MODULE(5, em22),   // ROUTE_CH21: r11b: script-spawn (the shore wolves)
#endif
#endif
#endif
#if defined(RE4DC_WEAPON_MODULES) && RE4DC_WEAPON_MODULES
    MODULE(3, wep01),  // WEAPON_MODULES: Punisher
    MODULE(54, wep07), // WEAPON_MODULES: shotgun
    MODULE(62, wep09), // WEAPON_MODULES: rifle (+ the scope archives wep21 / wep24)
    MODULE(52, wep11), // WEAPON_MODULES: TMP (+ the stock archive wep20)
    MODULE(59, wep13), // WEAPON_MODULES: rocket launcher
    MODULE(53, wep19), // WEAPON_MODULES: hand / incendiary / flash grenades
#endif
#if RE4DC_SUBSCREEN_OVL
    {71, "Sscrn", 0, 0, 0, 0, 0, 0, 0},  // sub screen overlay (entry points set per load)
#elif RE4DC_SUBSCREEN
    MODULE(71, Sscrn),  // sub screen (SUBSCREEN=1; linked into the ARAM-swapped area while open)
#endif
};
#undef MODULE

#if RE4DC_SUBSCREEN
// The sub screen's per-link constructors (tools/gen_modules.py PER_LINK_CTORS) register the
// destructors of its static objects here instead of KOS's __cxa_atexit list, where one entry
// per open would accumulate. Its _epilog (DLL_Unlink) walks re4dc_mod_Sscrn_dtors.
namespace {
struct ModuleExit { void (*fn)(void*); void* arg; };
ModuleExit sscrn_exits[16];
unsigned sscrn_nexit;
void sscrn_run_exits()
{
    while (sscrn_nexit) {
        const ModuleExit e = sscrn_exits[--sscrn_nexit];
        e.fn(e.arg);
    }
}
}
extern "C" int re4dc_mod_Sscrn_atexit(void (*fn)(void*), void* arg, void* dso)
{
    (void) dso;
    if (sscrn_nexit >= sizeof(sscrn_exits) / sizeof(sscrn_exits[0])) re4dc_missing("Sscrn atexit table full");
    sscrn_exits[sscrn_nexit++] = {fn, arg};
    return 0;
}
extern "C" { void (*re4dc_mod_Sscrn_dtors[])(void) = {sscrn_run_exits, 0}; }
#endif

namespace {
constexpr unsigned kModules = sizeof(g_modules) / sizeof(g_modules[0]);
// OSUnlink leaves this in the header's (OS-owned) link.next word; a header
// read fresh from disc has 0 there, so a restart is told from a new read
// even when the new REL lands at the address of the old one.
constexpr u32 kUnlinkedMark = 0x57365552;  // "W6UR"
struct ModuleState {
    const void* header;     // header of the current link (nullptr when unlinked)
    const void* stopped;    // header unlinked by OSUnlink, eligible for restart
    bool captured;
    unsigned fresh_links, restarts, unlinks;
};
ModuleState g_state[kModules];
}

static int moduleIndex(u32 id)
{
    for (unsigned i = 0; i < kModules; i++) {
        if (g_modules[i].id == id) return int(i);
    }
    return -1;
}

// RELs linked as one group object (gen_modules.py group_rules, EM10_SHARED=1) share one state
// span: the pristine .data is captured once for the span, at the first link of any member, and
// a member linked while another is still linked resets the state that member is using.
static bool sameSpan(const Re4dcModule& a, const Re4dcModule& b)
{
    return a.data == b.data && a.data_end == b.data_end && a.bss == b.bss && a.bss_end == b.bss_end &&
           a.pristine == b.pristine && (a.data_end != a.data || a.bss_end != a.bss);
}

// Fresh link: pristine .data, zero .bss (the GameCube OSLink of a newly read REL).
static void freshState(unsigned i)
{
    const Re4dcModule& m = g_modules[i];
    ModuleState& s = g_state[i];
    const unsigned data = unsigned(m.data_end - m.data);
    for (unsigned j = 0; j < kModules; j++) {
        if (j == i || !sameSpan(m, g_modules[j])) continue;
        if (g_state[j].captured) s.captured = true;
        if (g_state[j].header)
            re4dc_log("module state: %s shares its state span with linked %s (reset)\n", m.name, g_modules[j].name);
    }
    const bool capture = !s.captured;
    if (capture) {
        __builtin_memcpy(m.pristine, m.data, data);
        s.captured = true;
    } else {
        __builtin_memcpy(m.data, m.pristine, data);
    }
    __builtin_memset(m.bss, 0, unsigned(m.bss_end - m.bss));
    ++s.fresh_links;
    re4dc_log("module state: %s fresh link %u data=%u bss=%u %s\n", m.name, s.fresh_links, data,
              unsigned(m.bss_end - m.bss), capture ? "captured" : "restored");
}

#if RE4DC_ROUTE_OVL
#include <stdio.h>
#include <stdint.h>
#include <kos/fs.h>
#include <arch/cache.h>
typedef unsigned char u8;
extern "C" void re4dc_module_overlay(u32 id, void (*prolog)(void), void (*epilog)(void), char* data, char* data_end,
                                     char* bss, char* bss_end, char* pristine);
extern "C" int re4dc_static_heap_free();  // ui_bridge.cpp: heap 4 free bytes
namespace {
// tools/gen_overlay.py: a 64-byte header, the module bytes as linked at `base`, the relocation offsets.
struct RouteOverlayHeader {
    u32 magic, version, image_bytes, relocs, base;
    u32 prolog, epilog, data, data_end, bss, bss_end, pristine;  // offsets from base
    u32 image_hash, reloc_hash, pad[2];
};
constexpr u32 kRouteOverlayMagic = 0x4F344552;  // "RE4O"
struct RouteOverlay { u8* block; u32 image_bytes; unsigned loads; };
#if defined(RE4DC_ROUTE_CH21) && RE4DC_ROUTE_CH21
RouteOverlay g_route_ovl[3];  // 0 = pl0f, 1 = em2f, 2 = em22 (ROUTE_CH21: r11b)
#define ROUTE_OVL_SLOT(id) ((id) == 43 ? 0 : (id) == 39 ? 1 : 2)
#define ROUTE_OVL_ID(id) ((id) == 43 || (id) == 39 || (id) == 5)
#else
RouteOverlay g_route_ovl[2];  // 0 = pl0f, 1 = em2f
#define ROUTE_OVL_SLOT(id) ((id) == 43 ? 0 : 1)
#define ROUTE_OVL_ID(id) ((id) == 43 || (id) == 39)
#endif
u32 ovlHash(const void* p, u32 bytes)
{
    u32 h = 2166136261U;
    for (u32 i = 0; i < bytes; i += 4) h = (h ^ *reinterpret_cast<const u32*>(static_cast<const u8*>(p) + i)) * 16777619U;
    return h;
}
}

// src/game/main_mem.cpp (C++ linkage, include/main_mem.h).
void* mem_alloc(u32 size, const char* file, int line, int flag, int heap);
void Mem_free_h(void* p, int heap);

// On a link of pl0f / em2f (/ em22) with no code loaded: read /cd/dc/<mod>.ovl into heap 4, check, relocate,
// bind the table entry. Any failure stops the game here (re4dc_missing): never a stub.
static void routeOverlayLoad(unsigned index)
{
    const Re4dcModule& m = g_modules[index];
    RouteOverlay& o = g_route_ovl[ROUTE_OVL_SLOT(m.id)];
    char path[32];
    snprintf(path, sizeof(path), "/cd/dc/%s.ovl", m.name);
    file_t f = fs_open(path, O_RDONLY);
    if (f < 0) re4dc_missing("route overlay missing on the disc");
    const u32 total = u32(fs_total(f));
    const int free_before = re4dc_static_heap_free();
    u8* block = static_cast<u8*>(mem_alloc(total, "route overlay", 0, 1, 4));
    if (!block) {
        fs_close(f);
        re4dc_log("route overlay: %s %lu B does not fit heap 4 (free %d)\n", m.name, total, free_before);
        re4dc_missing("route overlay does not fit heap 4");
    }
    u32 got = 0;
    while (got < total) {
        const ssize_t r = fs_read(f, block + got, total - got);
        if (r <= 0) break;
        got += u32(r);
    }
    fs_close(f);
    const RouteOverlayHeader h = *reinterpret_cast<const RouteOverlayHeader*>(block);
    u8* image = block + sizeof(RouteOverlayHeader);
    u32* reloc = reinterpret_cast<u32*>(image + h.image_bytes);
    if (got != total || h.magic != kRouteOverlayMagic || h.version != 1 ||
        sizeof(RouteOverlayHeader) + h.image_bytes + h.relocs * 4 != total ||
        ovlHash(image, h.image_bytes) != h.image_hash || ovlHash(reloc, h.relocs * 4) != h.reloc_hash)
        re4dc_missing("route overlay corrupt (size / hash)");
    const u32 delta = u32(image) - h.base;
    for (u32 i = 0; i < h.relocs; ++i) {
        const u32 at = reloc[i];
        if (at + 4 > h.image_bytes || (at & 3)) re4dc_missing("route overlay relocation out of range");
        *reinterpret_cast<u32*>(image + at) += delta;
    }
    dcache_flush_range(reinterpret_cast<uintptr_t>(image), h.image_bytes);
    icache_flush_range(reinterpret_cast<uintptr_t>(image), h.image_bytes);
    o.block = block;
    o.image_bytes = h.image_bytes;
    ++o.loads;
    re4dc_module_overlay(m.id, reinterpret_cast<void (*)(void)>(image + h.prolog),
                         reinterpret_cast<void (*)(void)>(image + h.epilog), reinterpret_cast<char*>(image + h.data),
                         reinterpret_cast<char*>(image + h.data_end), reinterpret_cast<char*>(image + h.bss),
                         reinterpret_cast<char*>(image + h.bss_end), reinterpret_cast<char*>(image + h.pristine));
    re4dc_log("route overlay: %s load %u %lu B (%lu relocs) at %08lx heap4 %d -> %d\n", m.name, o.loads, h.image_bytes,
              h.relocs, u32(image), free_before, re4dc_static_heap_free());
}

// Unlink or room heap rebuild: fill the code with `trapa #0xFF` (a stale call into it stops loudly
// in the exception handler instead of running reused memory as code until the cell is reused), free it,
// empty the table entry (the next link reads the overlay again: a fresh link).
static void routeOverlayRelease(unsigned index, const char* why)
{
    Re4dcModule& m = g_modules[index];
    if (!ROUTE_OVL_ID(m.id)) return;
    RouteOverlay& o = g_route_ovl[ROUTE_OVL_SLOT(m.id)];
    if (!o.block) return;
    u8* image = o.block + sizeof(RouteOverlayHeader);
    for (u32 i = 0; i + 2 <= o.image_bytes; i += 2) *reinterpret_cast<unsigned short*>(image + i) = 0xC3FF;
    dcache_flush_range(reinterpret_cast<uintptr_t>(image), o.image_bytes);
    icache_flush_range(reinterpret_cast<uintptr_t>(image), o.image_bytes);
    Mem_free_h(o.block, 4);
    o.block = 0;
    re4dc_module_overlay(m.id, 0, 0, 0, 0, 0, 0, 0);
    re4dc_log("route overlay: %s released (%s) heap4 %d\n", m.name, why, re4dc_static_heap_free());
}

// gameRoomMemInit (src/game/game.cpp), before heap 4 is rebuilt.
extern "C" void re4dc_route_overlay_room_reset()
{
    for (unsigned i = 0; i < kModules; ++i) routeOverlayRelease(i, "room reset");
}
#endif

// Binds the header the game read (include/main_sub.h OSModuleHeader: id at 0,
// prolog at 0x34, epilog at 0x38) to the compiled module; 1 = known module.
extern "C" int re4dc_module_bind(void* header)
{
    if (header == 0) {
        re4dc_log("module: null header; link failed\n");
        return 0;
    }
    u32* h = (u32*) header;
    const int index = moduleIndex(h[0]);
    // Relink of the header this module last unlinked: state is kept.
    const bool restart = h[1] == kUnlinkedMark && index >= 0 && g_state[index].stopped == header;
    if (h[1] == kUnlinkedMark) h[1] = 0;
    if (h[0x1c / 4] == 0xDC000001) {
        // Compact offline descriptor: no section, name, import or raw code fields.
        for (unsigned i = 1; i < 16; ++i) {
            if (i != 0x1c / 4 && i != 0x20 / 4 && i != 0x34 / 4 && i != 0x38 / 4 && h[i] != 0) {
                re4dc_log("module: malformed native descriptor; link failed\n");
                h[0x34 / 4] = h[0x38 / 4] = 0;
                return 0;
            }
        }
    }
    const Re4dcModule* m = index >= 0 ? &g_modules[index] : 0;
    void (**prolog)(void) = (void (**)(void)) &h[0x34 / 4];
    void (**epilog)(void) = (void (**)(void)) &h[0x38 / 4];
    if (m == 0) {
        re4dc_log("module: id %lu not in the image; link failed\n", h[0]);
        *prolog = 0;
        *epilog = 0;
        return 0;
    }
    if (h[0x1c / 4] == 0xDC000001 &&
        ((h[0x34 / 4] && *prolog != m->prolog) || (h[0x38 / 4] && *epilog != m->epilog))) {
        re4dc_log("module: invalid native entry points; link failed\n");
        *prolog = 0;
        *epilog = 0;
        return 0;
    }
#if RE4DC_ROUTE_OVL
    if (m->prolog == 0 && ROUTE_OVL_ID(m->id)) {
        routeOverlayLoad(unsigned(index));
    }
#endif
#if RE4DC_MODULE_OVL
    if (m->prolog == 0) {
        re4dc_log("module: %s is an overlay that is not loaded; link failed\n", m->name);
        *prolog = 0;
        *epilog = 0;
        return 0;
    }
#endif
    ModuleState& s = g_state[index];
    if (s.header && s.header != header) {
        re4dc_log("module: %s linked again without unlink\n", m->name);
    }
    if (restart) {
        ++s.restarts;
        re4dc_log("module: id %lu -> %s (static, restart %u keeps state)\n", h[0], m->name, s.restarts);
    } else {
        re4dc_log("module: id %lu -> %s (static)\n", h[0], m->name);
#if RE4DC_SUBSCREEN
        if (m->id == 71 && sscrn_nexit) {  // the last link was not left through DLL_Unlink
            re4dc_log("module: Sscrn fresh link drops %u stale destructors\n", sscrn_nexit);
            sscrn_nexit = 0;
        }
#endif
        freshState(unsigned(index));
    }
    s.header = header;
    s.stopped = 0;
    *prolog = m->prolog;
    *epilog = m->epilog;
    return 1;
}

#if RE4DC_MODULE_OVL
// sscrn_bridge.cpp, after reading and relocating an overlay: its entry points and state span.
// The bytes came fresh from disc (pristine .data, zero .bss): the next link captures them.
extern "C" void re4dc_module_overlay(u32 id, void (*prolog)(void), void (*epilog)(void), char* data, char* data_end,
                                     char* bss, char* bss_end, char* pristine)
{
    const int index = moduleIndex(id);
    if (index < 0) re4dc_missing("overlay module id not in the table");
    Re4dcModule& m = g_modules[index];
    m.prolog = prolog;
    m.epilog = epilog;
    m.data = data;
    m.data_end = data_end;
    m.bss = bss;
    m.bss_end = bss_end;
    m.pristine = pristine;
    ModuleState& s = g_state[index];
    s.header = 0;
    s.stopped = 0;
    s.captured = false;
}
#endif

// OSUnlink: the module's code stays resident; mark the header so a relink of
// this very header (restartRelData) is a restart rather than a fresh read.
extern "C" int re4dc_module_unbind(void* header)
{
    if (header == 0) return 0;
    u32* h = (u32*) header;
    const int index = moduleIndex(h[0]);
    if (index < 0 || g_state[index].header != header) {
        re4dc_log("module: unlink of id %lu that is not linked\n", h[0]);
        return 1;
    }
    ModuleState& s = g_state[index];
    s.header = 0;
    s.stopped = header;
    ++s.unlinks;
    h[1] = kUnlinkedMark;
#if RE4DC_ROUTE_OVL
    routeOverlayRelease(unsigned(index), "unlink");
#endif
    return 1;
}

// Room-lifecycle audit: fresh links / restarts / unlinks summed over modules.
extern "C" void re4dc_module_counts(unsigned* fresh, unsigned* restarts, unsigned* unlinks, unsigned* linked)
{
    unsigned f = 0, r = 0, u = 0, l = 0;
    for (const auto& s : g_state) { f += s.fresh_links; r += s.restarts; u += s.unlinks; l += s.header != 0; }
    *fresh = f; *restarts = r; *unlinks = u; *linked = l;
}
