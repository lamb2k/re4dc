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
#include <stdio.h>

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
// STAGE_OVL=1 (lane ch3found16 2026-10-16, heap 4): every stage module (st1_0..st1_3, st2_0..st2_3, st4_0) is a
// room overlay (/cd/dc/<st>.ovl), read into heap 3 beside the room REL when linkRelData links it and dropped with heap 3 at the next relink, so
// only the current room's stage code is resident. A stopRelData unlink (sub screen, movies) keeps the block, so the
// relink restarts with the module's state.
#if defined(RE4DC_STAGE_OVL) && RE4DC_STAGE_OVL
#define SMODULE_DECL(name)
#else
#define SMODULE_DECL(name) MODULE(name)
#endif
#define MODULE(name) void name##_prolog(void); void name##_epilog(void); \
    extern char re4dc_mod_##name##_data[], re4dc_mod_##name##_data_end[], re4dc_mod_##name##_bss[], \
        re4dc_mod_##name##_bss_end[], re4dc_mod_##name##_pristine[];
// WORLD_STAGE_MODULES=1 rows first: tools/assetpipe/wiring.py wire() appends after the default list's last row.
#if defined(RE4DC_WORLD_STAGE_MODULES) && RE4DC_WORLD_STAGE_MODULES
SMODULE_DECL(st2_0)
SMODULE_DECL(st4_0)
MODULE(pl11)
#endif
#if defined(RE4DC_WORLD_ROOM_MODULES) && RE4DC_WORLD_ROOM_MODULES
SMODULE_DECL(st2_2)
MODULE(em1f)
#endif
#if defined(RE4DC_ROUTE_CH23) && RE4DC_ROUTE_CH23
SMODULE_DECL(st2_0)
#endif
#if defined(RE4DC_ROUTE_CH31) && RE4DC_ROUTE_CH31
SMODULE_DECL(st2_1)
MODULE(em1a)
MODULE(em1b)
MODULE(em14)
#endif
#if defined(RE4DC_ROUTE_CH32) && RE4DC_ROUTE_CH32
MODULE(em19)
#endif
#if defined(RE4DC_ROUTE_CH41) && RE4DC_ROUTE_CH41
MODULE(em1c)
SMODULE_DECL(st2_3)
#endif
#if defined(RE4DC_ROUTE_BOSS4) && RE4DC_ROUTE_BOSS4 && !(defined(RE4DC_ROUTE_CH41) && RE4DC_ROUTE_CH41)
SMODULE_DECL(st2_3)
#endif
#if defined(RE4DC_ROUTE_CH3) && RE4DC_ROUTE_CH3
SMODULE_DECL(st3_0)
SMODULE_DECL(st3_1)
SMODULE_DECL(st3_2)
SMODULE_DECL(st3_3)
#endif
#if !(defined(RE4DC_DISC2) && RE4DC_DISC2)
SMODULE_DECL(st1_0)
SMODULE_DECL(st1_1)
SMODULE_DECL(st1_2)
SMODULE_DECL(st1_3)
#endif
MODULE(wep02)
#if !(defined(RE4DC_DISC2) && RE4DC_DISC2)
MODULE(em12)
#endif
MODULE(em23)
#if !(defined(RE4DC_DISC2) && RE4DC_DISC2)
MODULE(em15)
MODULE(em26)
MODULE(em28)
MODULE(em21)
MODULE(em2a)
MODULE(em29)
MODULE(em2e)
MODULE(em13)
MODULE(em27)
#endif
#if defined(RE4DC_ROUTE_CH13) && RE4DC_ROUTE_CH13
MODULE(em18)
#if !(defined(RE4DC_DISC2) && RE4DC_DISC2)
MODULE(em17)
MODULE(em24)
#if defined(RE4DC_ROUTE_CH21) && RE4DC_ROUTE_CH21
MODULE(em11)
#endif
#if defined(RE4DC_ROUTE_CH23) && RE4DC_ROUTE_CH23
MODULE(em16)
#endif
#endif
#if !RE4DC_ROUTE_OVL
MODULE(pl0f)
MODULE(em2f)
#if defined(RE4DC_ROUTE_CH21) && RE4DC_ROUTE_CH21
MODULE(em22)
MODULE(em2b)
MODULE(pl11)
#endif
#if defined(RE4DC_ROUTE_CH22) && RE4DC_ROUTE_CH22
MODULE(pl14)
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

#if defined(RE4DC_STAGE_OVL) && RE4DC_STAGE_OVL
#define SMODULE(id, name) {id, #name, 0, 0, 0, 0, 0, 0, 0}
#else
#define SMODULE(id, name) MODULE(id, name)
#endif
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
    SMODULE(75, st2_0), // WORLD_STAGE_MODULES: r200..r203, r207, r208, r210, r222
    SMODULE(96, st4_0), // WORLD_STAGE_MODULES: the St4 rooms
    MODULE(47, pl11),  // WORLD_STAGE_MODULES: the partner Ashley (cSubAshley; r210 spawns her at entry)
#endif
#if defined(RE4DC_WORLD_ROOM_MODULES) && RE4DC_WORLD_ROOM_MODULES
    SMODULE(83, st2_2), // WORLD_ROOM_MODULES: r211..r219
    MODULE(109, em1f), // WORLD_ROOM_MODULES: the St4 Ganados (r406, r40a, r40b, r40d, r410)
#endif
#if defined(RE4DC_ROUTE_CH23) && RE4DC_ROUTE_CH23
    SMODULE(75, st2_0), // chapter 2-3 castle approach (r200)
    {63, "em3b", 0, 0, 0, 0, 0, 0, 0}, // vehicles, room overlay
    {61, "em35", 0, 0, 0, 0, 0, 0, 0}, // Mendez, room overlay
#endif
#if defined(RE4DC_ROUTE_CH31) && RE4DC_ROUTE_CH31
    SMODULE(82, st2_1), // ROUTE_CH31: castle chapter 3 (r204 r205 r206 r209 r20a..r20f)
    MODULE(24, em1a),  // ROUTE_CH31: r208 / r209 Ganados (em10g group)
    MODULE(25, em1b),  // ROUTE_CH31: r201 / r20c Ganados (em10g group)
    MODULE(35, em14),  // ROUTE_CH31: r204 / r20f Ganados (em10g group)
#endif
#if defined(RE4DC_ROUTE_CH32) && RE4DC_ROUTE_CH32
    {32, "em2d", 0, 0, 0, 0, 0, 0, 0}, // ROUTE_CH32: r205 / r20a, room overlay
    {10, "em25", 0, 0, 0, 0, 0, 0, 0}, // ROUTE_CH32: r20c / r20f / r20d, room overlay
    MODULE(23, em19),  // ROUTE_CH32: r20d Ganados (em10g group)
    {68, "em3c", 0, 0, 0, 0, 0, 0, 0}, // ROUTE_CH32: r20e armor, room overlay
#endif
#if defined(RE4DC_ROUTE_CH41) && RE4DC_ROUTE_CH41
    MODULE(81, em1c),  // ROUTE_CH41: r218 Ganados (em10g group)
    SMODULE(97, st2_3), // ROUTE_CH41: castle chapter 4 (r220..r22c; 4-1 ends in r229 / r221 / r22b)
    {31, "em2c", 0, 0, 0, 0, 0, 0, 0}, // ROUTE_CH41: r221 boss, room overlay
#endif
#if defined(RE4DC_ROUTE_BOSS4) && RE4DC_ROUTE_BOSS4
#if !(defined(RE4DC_ROUTE_CH41) && RE4DC_ROUTE_CH41)
    SMODULE(97, st2_3), // ROUTE_BOSS4: r221 / r228 room code
    {31, "em2c", 0, 0, 0, 0, 0, 0, 0}, // ROUTE_BOSS4: r221 Verdugo, room overlay
#endif
    {79, "em38", 0, 0, 0, 0, 0, 0, 0}, // ROUTE_BOSS4: r228 Salazar + the Queen, room overlay
#endif
#if defined(RE4DC_ROUTE_CH3) && RE4DC_ROUTE_CH3
    SMODULE(76, st3_0),  // ROUTE_CH3: r300..r30c, r30e (island, disc 2)
    SMODULE(87, st3_1),  // ROUTE_CH3: r30d, r30f, r310..r312
    SMODULE(88, st3_2),  // ROUTE_CH3: r315..r31d
    SMODULE(101, st3_3), // ROUTE_CH3: r320..r333
    {90, "em1d", 0, 0, 0, 0, 0, 0, 0},  // ROUTE_CH3: r300 soldiers, room overlay
    {92, "em1e", 0, 0, 0, 0, 0, 0, 0},  // ROUTE_CH3: r301 / r303 / r305 soldiers, room overlay
#if !(defined(RE4DC_ROUTE_CH32) && RE4DC_ROUTE_CH32)
    {10, "em25", 0, 0, 0, 0, 0, 0, 0},  // ROUTE_CH3: r304 (room entry), room overlay (ROUTE_CH32 has the same row)
#endif
    {85, "em36", 0, 0, 0, 0, 0, 0, 0},  // ROUTE_CH3: r306..r310 / r326, room overlay
#if !(defined(RE4DC_WORLD_ROOM_MODULES) && RE4DC_WORLD_ROOM_MODULES)
    {109, "em1f", 0, 0, 0, 0, 0, 0, 0}, // ROUTE_CH3: island Ganados (r304 r30b r30c r30f r311 r321 r330), room overlay
#endif
#if !(defined(RE4DC_ROUTE_CH23) && RE4DC_ROUTE_CH23)
    {63, "em3b", 0, 0, 0, 0, 0, 0, 0},  // ROUTE_CH3: r301 vehicles, room overlay
#endif
#endif
#if !(defined(RE4DC_DISC2) && RE4DC_DISC2)
    SMODULE(74, st1_0),
    SMODULE(73, st1_1),
    SMODULE(78, st1_2),
    SMODULE(86, st1_3),
#endif
    MODULE(4, wep02),
#if !(defined(RE4DC_DISC2) && RE4DC_DISC2)
    MODULE(18, em12),
#endif
    MODULE(7, em23),
#if !(defined(RE4DC_DISC2) && RE4DC_DISC2)
    MODULE(19, em15),
    MODULE(14, em26),
    MODULE(17, em28),
    MODULE(6, em21),
    MODULE(28, em2a),  // r100 after state (flag 10): bear traps and tripwire bombs
    MODULE(27, em29),  // r106: script-load
    MODULE(38, em2e),  // r106: script-load
    MODULE(34, em13),  // r104: enabled-later
    MODULE(16, em27),  // r107: entry
#endif
#if defined(RE4DC_ROUTE_CH13) && RE4DC_ROUTE_CH13
    MODULE(22, em18),  // ROUTE_CH13: r102 (the merchant): enabled-later,script-load
#if !(defined(RE4DC_DISC2) && RE4DC_DISC2)
    MODULE(21, em17),  // ROUTE_CH13: r108: enabled-later,entry,script-load
    MODULE(8, em24),   // ROUTE_CH13: r108 (room entry) / r10a: entry
#endif
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
    {30, "em2b", 0, 0, 0, 0, 0, 0, 0},  // ROUTE_CH21: r119: enabled-later,script-spawn (El Gigante); overlay em2b.ovl
    {47, "pl11", 0, 0, 0, 0, 0, 0, 0},  // ROUTE_CH21: r117 on: Ashley (enemy module 3, cSubAshley); overlay pl11.ovl
#else
    MODULE(5, em22),   // ROUTE_CH21: r11b: script-spawn (the shore wolves)
    MODULE(30, em2b),  // ROUTE_CH21: r119: enabled-later,script-spawn (El Gigante)
    MODULE(47, pl11),  // ROUTE_CH21: r117 on: Ashley (enemy module 3, cSubAshley)
#endif
#if !(defined(RE4DC_DISC2) && RE4DC_DISC2)
    MODULE(13, em11),  // ROUTE_CH21: r117: enabled-later (the Ganados of a later visit; em10g group)
#endif
#endif
#if defined(RE4DC_ROUTE_CH23) && RE4DC_ROUTE_CH23
    MODULE(20, em16),  // ROUTE_CH23: r11d: enabled-later,entry (the night village Ganados + Bella sisters; em10g group)
#endif
#if defined(RE4DC_ROUTE_CH22) && RE4DC_ROUTE_CH22
#if RE4DC_ROUTE_OVL
    {66, "pl14", 0, 0, 0, 0, 0, 0, 0},  // chapter 2-2 cabin partner, enemy module 4
#else
    MODULE(66, pl14),
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
#if defined(RE4DC_ROUTE_CH3) && RE4DC_ROUTE_CH3
// ROUTE_CH3: one slot per overlay id (any knob combination); ids not in the table are never bound. Holds every id of
// the per-knob tables below (ROUTE_CH21..CH41, ROUTE_BOSS4) plus the island's em1d (90), em1e (92), em36 (85), em1f (109).
constexpr u32 kRouteOvlIds[] = {43, 39, 5, 30, 47, 66, 63, 61, 32, 10, 68, 31, 79, 90, 92, 85, 109};
RouteOverlay g_route_ovl[sizeof(kRouteOvlIds) / sizeof(kRouteOvlIds[0])];
int routeOvlSlot(u32 id)
{
    for (unsigned i = 0; i < sizeof(kRouteOvlIds) / sizeof(kRouteOvlIds[0]); ++i)
        if (kRouteOvlIds[i] == id) return int(i);
    return -1;
}
#define ROUTE_OVL_SLOT(id) routeOvlSlot(id)
#define ROUTE_OVL_ID(id) (routeOvlSlot(id) >= 0)
#elif defined(RE4DC_ROUTE_BOSS4) && RE4DC_ROUTE_BOSS4 && defined(RE4DC_ROUTE_CH22) && RE4DC_ROUTE_CH22
// ROUTE_BOSS4 (needs ROUTE_CH32): the ROUTE_CH41 twelve (em2c 31 at 11), then em38 (79).
RouteOverlay g_route_ovl[13];
#define ROUTE_OVL_SLOT(id) ((id) == 43 ? 0 : (id) == 39 ? 1 : (id) == 5 ? 2 : (id) == 30 ? 3 : (id) == 47 ? 4 : (id) == 66 ? 5 : (id) == 63 ? 6 : (id) == 61 ? 7 : (id) == 32 ? 8 : (id) == 10 ? 9 : (id) == 68 ? 10 : (id) == 31 ? 11 : 12)
#define ROUTE_OVL_ID(id) ((id) == 43 || (id) == 39 || (id) == 5 || (id) == 30 || (id) == 47 || (id) == 66 || (id) == 63 || (id) == 61 || (id) == 32 || (id) == 10 || (id) == 68 || (id) == 31 || (id) == 79)
#elif defined(RE4DC_ROUTE_BOSS4) && RE4DC_ROUTE_BOSS4
// ROUTE_BOSS4 without ROUTE_CH22: the ROUTE_CH41 eleven (em2c 31 at 10), then em38 (79).
RouteOverlay g_route_ovl[12];
#define ROUTE_OVL_SLOT(id) ((id) == 43 ? 0 : (id) == 39 ? 1 : (id) == 5 ? 2 : (id) == 30 ? 3 : (id) == 47 ? 4 : (id) == 63 ? 5 : (id) == 61 ? 6 : (id) == 32 ? 7 : (id) == 10 ? 8 : (id) == 68 ? 9 : (id) == 31 ? 10 : 11)
#define ROUTE_OVL_ID(id) ((id) == 43 || (id) == 39 || (id) == 5 || (id) == 30 || (id) == 47 || (id) == 63 || (id) == 61 || (id) == 32 || (id) == 10 || (id) == 68 || (id) == 31 || (id) == 79)
#elif defined(RE4DC_ROUTE_CH41) && RE4DC_ROUTE_CH41 && defined(RE4DC_ROUTE_CH22) && RE4DC_ROUTE_CH22
// ROUTE_CH41 (needs ROUTE_CH32): the ROUTE_CH32 eleven, then em2c (31).
RouteOverlay g_route_ovl[12];
#define ROUTE_OVL_SLOT(id) ((id) == 43 ? 0 : (id) == 39 ? 1 : (id) == 5 ? 2 : (id) == 30 ? 3 : (id) == 47 ? 4 : (id) == 66 ? 5 : (id) == 63 ? 6 : (id) == 61 ? 7 : (id) == 32 ? 8 : (id) == 10 ? 9 : (id) == 68 ? 10 : 11)
#define ROUTE_OVL_ID(id) ((id) == 43 || (id) == 39 || (id) == 5 || (id) == 30 || (id) == 47 || (id) == 66 || (id) == 63 || (id) == 61 || (id) == 32 || (id) == 10 || (id) == 68 || (id) == 31)
#elif defined(RE4DC_ROUTE_CH41) && RE4DC_ROUTE_CH41
// ROUTE_CH41 without ROUTE_CH22: the ROUTE_CH32 ten, then em2c (31).
RouteOverlay g_route_ovl[11];
#define ROUTE_OVL_SLOT(id) ((id) == 43 ? 0 : (id) == 39 ? 1 : (id) == 5 ? 2 : (id) == 30 ? 3 : (id) == 47 ? 4 : (id) == 63 ? 5 : (id) == 61 ? 6 : (id) == 32 ? 7 : (id) == 10 ? 8 : (id) == 68 ? 9 : 10)
#define ROUTE_OVL_ID(id) ((id) == 43 || (id) == 39 || (id) == 5 || (id) == 30 || (id) == 47 || (id) == 63 || (id) == 61 || (id) == 32 || (id) == 10 || (id) == 68 || (id) == 31)
#elif defined(RE4DC_ROUTE_CH32) && RE4DC_ROUTE_CH32 && defined(RE4DC_ROUTE_CH22) && RE4DC_ROUTE_CH22
// ROUTE_CH32 (needs ROUTE_CH31 -> ROUTE_CH23): the ROUTE_CH22 + CH23 eight, then em2d (32), em25 (10), em3c (68).
RouteOverlay g_route_ovl[11];
#define ROUTE_OVL_SLOT(id) ((id) == 43 ? 0 : (id) == 39 ? 1 : (id) == 5 ? 2 : (id) == 30 ? 3 : (id) == 47 ? 4 : (id) == 66 ? 5 : (id) == 63 ? 6 : (id) == 61 ? 7 : (id) == 32 ? 8 : (id) == 10 ? 9 : 10)
#define ROUTE_OVL_ID(id) ((id) == 43 || (id) == 39 || (id) == 5 || (id) == 30 || (id) == 47 || (id) == 66 || (id) == 63 || (id) == 61 || (id) == 32 || (id) == 10 || (id) == 68)
#elif defined(RE4DC_ROUTE_CH32) && RE4DC_ROUTE_CH32
// ROUTE_CH32 without ROUTE_CH22: the ROUTE_CH23 seven, then em2d (32), em25 (10), em3c (68).
RouteOverlay g_route_ovl[10];
#define ROUTE_OVL_SLOT(id) ((id) == 43 ? 0 : (id) == 39 ? 1 : (id) == 5 ? 2 : (id) == 30 ? 3 : (id) == 47 ? 4 : (id) == 63 ? 5 : (id) == 61 ? 6 : (id) == 32 ? 7 : (id) == 10 ? 8 : 9)
#define ROUTE_OVL_ID(id) ((id) == 43 || (id) == 39 || (id) == 5 || (id) == 30 || (id) == 47 || (id) == 63 || (id) == 61 || (id) == 32 || (id) == 10 || (id) == 68)
#elif defined(RE4DC_ROUTE_CH23) && RE4DC_ROUTE_CH23 && defined(RE4DC_ROUTE_CH22) && RE4DC_ROUTE_CH22
RouteOverlay g_route_ovl[8];  // old five, then pl14, em3b and em35
#define ROUTE_OVL_SLOT(id) ((id) == 43 ? 0 : (id) == 39 ? 1 : (id) == 5 ? 2 : (id) == 30 ? 3 : (id) == 47 ? 4 : (id) == 66 ? 5 : (id) == 63 ? 6 : 7)
#define ROUTE_OVL_ID(id) ((id) == 43 || (id) == 39 || (id) == 5 || (id) == 30 || (id) == 47 || (id) == 66 || (id) == 63 || (id) == 61)
#elif defined(RE4DC_ROUTE_CH23) && RE4DC_ROUTE_CH23
RouteOverlay g_route_ovl[7];  // retain the old five slots, then em3b and em35
#define ROUTE_OVL_SLOT(id) ((id) == 43 ? 0 : (id) == 39 ? 1 : (id) == 5 ? 2 : (id) == 30 ? 3 : (id) == 47 ? 4 : (id) == 63 ? 5 : 6)
#define ROUTE_OVL_ID(id) ((id) == 43 || (id) == 39 || (id) == 5 || (id) == 30 || (id) == 47 || (id) == 63 || (id) == 61)
#elif defined(RE4DC_ROUTE_CH22) && RE4DC_ROUTE_CH22
RouteOverlay g_route_ovl[6];  // old five, then pl14
#define ROUTE_OVL_SLOT(id) ((id) == 43 ? 0 : (id) == 39 ? 1 : (id) == 5 ? 2 : (id) == 30 ? 3 : (id) == 47 ? 4 : 5)
#define ROUTE_OVL_ID(id) ((id) == 43 || (id) == 39 || (id) == 5 || (id) == 30 || (id) == 47 || (id) == 66)
#elif defined(RE4DC_ROUTE_CH21) && RE4DC_ROUTE_CH21
RouteOverlay g_route_ovl[5];  // 0 = pl0f, 1 = em2f, 2 = em22 (ROUTE_CH21: r11b), 3 = em2b (r119), 4 = pl11 (r117 on)
#define ROUTE_OVL_SLOT(id) ((id) == 43 ? 0 : (id) == 39 ? 1 : (id) == 5 ? 2 : (id) == 30 ? 3 : 4)
#define ROUTE_OVL_ID(id) ((id) == 43 || (id) == 39 || (id) == 5 || (id) == 30 || (id) == 47)
#else
RouteOverlay g_route_ovl[2];  // 0 = pl0f, 1 = em2f
#define ROUTE_OVL_SLOT(id) ((id) == 43 ? 0 : 1)
#define ROUTE_OVL_ID(id) ((id) == 43 || (id) == 39)
#endif
#if defined(RE4DC_STAGE_OVL) && RE4DC_STAGE_OVL
RouteOverlay g_stage_ovl[13];
inline int stageSlot(u32 id)
{
    switch (id) {
    case 74: return 0; case 73: return 1; case 78: return 2; case 86: return 3;   // st1_0 st1_1 st1_2 st1_3
    case 75: return 4; case 82: return 5; case 83: return 6; case 97: return 7;   // st2_0 st2_1 st2_2 st2_3
    case 96: return 8;                                                           // st4_0
    case 76: return 9; case 87: return 10; case 88: return 11; case 101: return 12; // st3_0 st3_1 st3_2 st3_3 (ROUTE_CH3)
    }
    return -1;
}
#define OVL_ID(id) (ROUTE_OVL_ID(id) || stageSlot(id) >= 0)
#define OVL_REF(id) (stageSlot(id) >= 0 ? g_stage_ovl[stageSlot(id)] : g_route_ovl[ROUTE_OVL_SLOT(id)])
#else
#define OVL_ID(id) ROUTE_OVL_ID(id)
#define OVL_REF(id) g_route_ovl[ROUTE_OVL_SLOT(id)]
#endif
u32 ovlHash(const void* p, u32 bytes)
{
    u32 h = 2166136261U;
    for (u32 i = 0; i < bytes; i += 4) h = (h ^ *reinterpret_cast<const u32*>(static_cast<const u8*>(p) + i)) * 16777619U;
    return h;
}
}

#if defined(RE4DC_OVL_ID_GUARD) && RE4DC_OVL_ID_GUARD
// OVL_ID_GUARD: this image's identity (FNV-1a of its linked .text, .text bytes), written after the link by
// tools/ovl_id_patch.py over the "RID1" mark. Initialised data, so it lands in .data and the patch leaves .text alone.
extern "C" { volatile u32 re4dc_image_id[2] = {0x31444952U, 0x31444952U}; }
#endif
// src/game/main_mem.cpp (C++ linkage, include/main_mem.h).
void* mem_alloc(u32 size, const char* file, int line, int flag, int heap);
void Mem_free_h(void* p, int heap);

// On a link of pl0f / em2f (/ em22 / em2b) with no code loaded: read /cd/dc/<mod>.ovl into heap 4, check, relocate,
// bind the table entry. Any failure stops the game here (re4dc_missing): never a stub.
static void routeOverlayLoad(unsigned index)
{
    const Re4dcModule& m = g_modules[index];
    RouteOverlay& o = OVL_REF(m.id);
    char path[32];
    snprintf(path, sizeof(path), "/cd/dc/%s.ovl", m.name);
    file_t f = fs_open(path, O_RDONLY);
    if (f < 0) re4dc_missing("route overlay missing on the disc");
    const u32 total = u32(fs_total(f));
    const int free_before = re4dc_static_heap_free();
#if defined(RE4DC_STAGE_OVL) && RE4DC_STAGE_OVL
    // A stage module is linked by cRoomData::linkRelData into heap 3 (the dll heap, before heap 4 exists); its
    // overlay shares the REL's heap and lifetime: MemReplaceHeap(2, 3) on the next relink drops both.
    const int heap = stageSlot(m.id) >= 0 ? 3 : 4;
#else
    const int heap = 4;
#endif
    u8* block = static_cast<u8*>(mem_alloc(total, "route overlay", 0, 1, heap));
    if (!block) {
        fs_close(f);
#if defined(RE4DC_STAGE_OVL) && RE4DC_STAGE_OVL
        re4dc_log("route overlay: %s %lu B does not fit heap %d (heap4 free %d)\n", m.name, total, heap, free_before);
#else
        re4dc_log("route overlay: %s %lu B does not fit heap 4 (free %d)\n", m.name, total, free_before);
#endif
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
#if defined(RE4DC_OVL_ID_GUARD) && RE4DC_OVL_ID_GUARD
    // OVL_ID_GUARD: header words 14/15 name the main image the overlay was linked against (FNV-1a of its .text, .text
    // bytes; gen_overlay.py). Another build's overlay would relocate against this image's addresses and corrupt memory
    // silently (the r118 fixture fault, 10-15): stop here instead. The image's own id is patched in after the link
    // (re4dc_image_id; the running .text differs from the linked one, so it is not hashed at run time).
    if (!h.pad[1] || h.pad[0] != re4dc_image_id[0] || h.pad[1] != re4dc_image_id[1]) {
        re4dc_log("route overlay: %s built for another program (id %08lx/%lu, this program %08lx/%lu)\n", m.name,
                  h.pad[0], h.pad[1], u32(re4dc_image_id[0]), u32(re4dc_image_id[1]));
        re4dc_missing("route overlay built for another program");
    }
#endif
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
#if defined(RE4DC_STAGE_OVL) && RE4DC_STAGE_OVL
    re4dc_log("route overlay: %s load %u %lu B (%lu relocs) at %08lx heap%d heap4 %d -> %d\n", m.name, o.loads,
              h.image_bytes, h.relocs, u32(image), heap, free_before, re4dc_static_heap_free());
#else
    re4dc_log("route overlay: %s load %u %lu B (%lu relocs) at %08lx heap4 %d -> %d\n", m.name, o.loads, h.image_bytes,
              h.relocs, u32(image), free_before, re4dc_static_heap_free());
#endif
}

// Unlink or room heap rebuild: fill the code with `trapa #0xFF` (a stale call into it stops loudly
// in the exception handler instead of running reused memory as code until the cell is reused), free it,
// empty the table entry (the next link reads the overlay again: a fresh link).
static void routeOverlayRelease(unsigned index, const char* why)
{
    Re4dcModule& m = g_modules[index];
    if (!OVL_ID(m.id)) return;
    RouteOverlay& o = OVL_REF(m.id);
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
    for (unsigned i = 0; i < kModules; ++i) {
#if defined(RE4DC_STAGE_OVL) && RE4DC_STAGE_OVL
        if (stageSlot(g_modules[i].id) >= 0) continue;  // heap 3 with the room REL: dropped at the relink
#endif
        routeOverlayRelease(i, "room reset");
    }
}
#endif

#if RE4DC_CRASH_TASK_DETAIL
// Issue 23 (CRASH_TASK_DETAIL): the last refused link / unlink, one stop-screen row (crash_screen.cpp).
static char g_dll_fail[80];
static void dllFail(const void* header, const char* why)
{
    const u32* h = (const u32*) header;
    snprintf(g_dll_fail, sizeof(g_dll_fail), "DLL %s hdr %08lx id %lu w1 %08lx w7 %08lx", why, (unsigned long) h,
             h ? (unsigned long) h[0] : 0ul, h ? (unsigned long) h[1] : 0ul, h ? (unsigned long) h[7] : 0ul);
}
extern "C" const char* re4dc_dll_fail_line(void) { return g_dll_fail; }
#define DLL_FAIL(h, why) dllFail(h, why)
#else
#define DLL_FAIL(h, why) ((void) 0)
#endif

// Binds the header the game read (include/main_sub.h OSModuleHeader: id at 0,
// prolog at 0x34, epilog at 0x38) to the compiled module; 1 = known module.
extern "C" int re4dc_module_bind(void* header)
{
    if (header == 0) {
        re4dc_log("module: null header; link failed\n"); DLL_FAIL(header, "null");
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
                re4dc_log("module: malformed native descriptor; link failed\n"); DLL_FAIL(header, "malformed");
                h[0x34 / 4] = h[0x38 / 4] = 0;
                return 0;
            }
        }
    }
    const Re4dcModule* m = index >= 0 ? &g_modules[index] : 0;
    void (**prolog)(void) = (void (**)(void)) &h[0x34 / 4];
    void (**epilog)(void) = (void (**)(void)) &h[0x38 / 4];
    if (m == 0) {
        re4dc_log("module: id %lu not in the image; link failed\n", h[0]); DLL_FAIL(header, "not-in-image");
        *prolog = 0;
        *epilog = 0;
        return 0;
    }
    if (h[0x1c / 4] == 0xDC000001 &&
        ((h[0x34 / 4] && *prolog != m->prolog) || (h[0x38 / 4] && *epilog != m->epilog))) {
        re4dc_log("module: invalid native entry points; link failed\n"); DLL_FAIL(header, "entry");
        *prolog = 0;
        *epilog = 0;
        return 0;
    }
#if RE4DC_ROUTE_OVL
#if defined(RE4DC_STAGE_OVL) && RE4DC_STAGE_OVL
    if (!restart && stageSlot(m->id) >= 0 && g_stage_ovl[stageSlot(m->id)].block) {
        // MemReplaceHeap(2, 3) rebuilt heap 3 since the last link: the old block is gone with it (no free, no fill).
        g_stage_ovl[stageSlot(m->id)].block = 0;
        re4dc_module_overlay(m->id, 0, 0, 0, 0, 0, 0, 0);
        re4dc_log("route overlay: %s dropped with heap 3 (relink)\n", m->name);
    }
#endif
    if (m->prolog == 0 && OVL_ID(m->id)) {
        routeOverlayLoad(unsigned(index));
    }
#endif
#if RE4DC_MODULE_OVL
    if (m->prolog == 0) {
        re4dc_log("module: %s is an overlay that is not loaded; link failed\n", m->name); DLL_FAIL(header, "ovl-unloaded");
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
    if (header == 0) {
        DLL_FAIL(header, "unlink-null");
        return 0;
    }
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
#if defined(RE4DC_STAGE_OVL) && RE4DC_STAGE_OVL
    if (stageSlot(h[0]) < 0)  // a stage overlay stays in heap 3 with its REL (stopRelData / restartRelData keep it)
#endif
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
