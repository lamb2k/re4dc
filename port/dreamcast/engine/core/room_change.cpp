// Room change (lane eng-load1, 2026-11-21): the engine's side of a door. docs/engine/CONSOLE_LOOP.md section 14.
//
// Who decides: the game. Its area check (sce_at.cpp SceAtCheck -> sceAtCheck_main -> sceAtFunc_door, the door handler
// of area type 1) stores the destination in the global work (NextPos, NextY, next_stage / next_room_no, next_point,
// door_no) and sets the game routine pG->Rno0 to 4; game.cpp's routine 4 (gameDoordemo) then fades, moves the player's
// start to the destination and sets room_id, and routines 1 and 2 (gameStageInit, gameRoomInit) load and set up the new
// room. The engine reads that request after the tick (pG->Rno0 == 4) and answers it with a loading state:
//   - play is not timed: no tick runs, no ROW is written; the pacer's queued picture is flipped by the vblank handler
//     and stays on screen (a held picture; the fade is not drawn in E1, effects are not hosted);
//   - disc access is allowed and counted as loading (core/play_files.c: opens, reads, drive requests per transition),
//     camera tracks converted now are load work (cam_track_in_play off);
//   - the first room's memory is returned: the skeleton tables of its actors, its collision tables (collision release
//     entry), its room archive, its room heap (heap 4, made again), the renderer's pack (renderer entries);
//   - the second room is set up in gameRoomInit's order (core/main.cpp room_init), the player created at the door's
//     destination, the memory map sampled again and the room's memory marks taken;
//   - play resumes on the next field boundary (core/frame.cpp e1_loading_end).
// The round trip check: the marks of a room's second visit must equal those of its first (KOS heap in use, the
// behaviour arena in use, video memory free, collision pieces, skeleton tables). Control MEMKEEP keeps one 4 KiB block
// across the first leave: the check must report LEAK.
//
// Decision statements re-expressed here (the request's state handoff the original makes in game.cpp; listed for the
// integrator's ruling, as H-017.10 asks of an engine body that re-expresses decisions):
//   gameDoordemo (game.cpp 1533-1543): sub_pos = NextPos; sub_angle = NextY; room_id = next_room; Part = next_point;
//     JumpPoint = 0 unless the debug jump (Debug_flg[2] bit 31) or continue mode (System_flg 0x80000); Rno0..3 = 1,0,0,0.
//   gameRoomMemInit (game.cpp 1599-1604): the room part of the global work (pad_16C, 0x4E00 bytes) cleared; Debug_flg[0],
//     Debug_flg[1], Status_flg[0..2] cleared.
//   gameRoomInit's end (game.cpp 789): Rno0 = 3.
// The door's own callbacks (SceSys.pDoorFunc / pExitFunc) are room-script functions; no door of the DOOR scene has one
// (checked on the record) and the default image hosts no room script: a record with one is refused, logged.
//
// The DOOR scene (boot file /cd/DOOR.TXT): the fixture text the PC reference replays (re4ref, hostref/), so both run the
// same start and pads: room, pos, ang, seed, ticks, pad lines, and "door <tick> <area no>" lines. LOGGED STUB (hand-back
// request R1): the default image does not host the area check (game/sce_at), so the request is planted at the tick the
// fixture names, at SceAtCheck's place in the tick (before the player's move), from the room's own AEV record, with the
// stores the door handler makes (sce_at.cpp sceAtFunc_door 1038-1085: Stop_flg all set, NextPos, NextY, room_id_prev,
// Part_old, next_stage, next_room_no, next_point, door_no, Rno0 4, r_continue_cnt 0, System_flg bit 6 off). The PC
// reference hosts the area check itself and logs the tick its handler fired; the comparison checks both ticks agree.
#include "global.h"
#include "player.h"
#include "obj.h"
#include "em.h"
#include "model.h"
#include "main.h"
#include "rnd.h"
#include "sce_at.h"
#include "e1_engine.h"
#include "e1_core.h"
#include "e1_kos.h"
#include "room_change.h"
#include "skeleton/skel.h"
#include "camera/camera_svc.h"
#include <dc/pvr.h>
#include <malloc.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

void* GetDataExt(void* arc, const char* tag, int no);
void e1_room_release();                                  // core/loader.cpp: the room archive returned
extern "C" uint32_t e1_room_heap_bytes(void) __attribute__((weak));
extern "C" u32 col_piece_count(void);                   // services/collision/col.cpp
void e1_loading_begin(unsigned n, unsigned from, unsigned to);   // core/frame.cpp
void e1_loading_end(unsigned n, unsigned tick, uint32_t us);
void e1_memmap_sample();
void e1_heap_room_checks();
extern E1ArenaStats e1_arena;
// Release entries other lanes own (requests R2, R3 in the hand-back). Weak: absent, the room change logs a stub line
// and the round-trip check shows what is kept.
extern "C" void col_room_release(void) __attribute__((weak));             // collision: pieces and their tables
extern "C" void e1_draw_close_c(void) __attribute__((weak));               // renderer: the room's pack returned
extern "C" int e1_draw_reopen_c(const char* pack) __attribute__((weak));  // renderer: the next room's pack
extern "C" int e1_draw_opened_c(void);
extern "C" volatile uint32_t m1_open_us[10];   // render/native_scene.inc (lane eng-load2): the last pack open's phases

int e1_door_scene;
static E1Route door_route;
struct DoorPad { unsigned tick; E1Pad pad; };
struct DoorReq { unsigned tick, area; };
static DoorPad door_pads[96];
static unsigned n_pads;
static DoorReq door_reqs[8];
static unsigned n_reqs, door_seed;
static int ctl_memkeep, ctl_readx, ctl_discfail;
extern "C" void disc_safe_fail_arm(void);   // core/disc_safe.c (DISCFAIL)
extern "C" void disc_safe_nb_arm(void);     // core/disc_safe.c (DISCNB, lane eng-load2)
static file_t readx_fd = -1;
static unsigned readx_tick;

// ---- the fixture (the re4ref format, hostref/host_io.cpp; tools/plays_right/fixtures/door-r101-r103.txt) ----
static unsigned long num(const char* s) { return strtoul(s, 0, 0); }
static void parse_line(char* l)
{
    char* h = strchr(l, '#');
    if (h) *h = 0;
    char* w[10];
    unsigned n = 0;
    for (char* t = strtok(l, " \t\r"); t && n < 10; t = strtok(0, " \t\r")) w[n++] = t;
    if (!n) return;
    if (!strcmp(w[0], "room") && n >= 2) door_route.room = (unsigned) num(w[1]);
    else if (!strcmp(w[0], "pos") && n >= 4) for (int i = 0; i < 3; i++) door_route.pos[i] = strtof(w[1 + i], 0);
    else if (!strcmp(w[0], "ang") && n >= 2) door_route.ang = strtof(w[1], 0);
    else if (!strcmp(w[0], "seed") && n >= 2) door_seed = (unsigned) num(w[1]);
    else if (!strcmp(w[0], "ticks") && n >= 2) door_route.ticks = (unsigned) num(w[1]);
    else if (!strcmp(w[0], "pad") && n >= 5 && n_pads < sizeof(door_pads) / sizeof(door_pads[0])) {
        DoorPad& p = door_pads[n_pads++];
        p.tick = (unsigned) num(w[1]);
        p.pad.buttons = (uint16_t) num(w[2]);
        p.pad.sx = (int8_t) strtol(w[3], 0, 0);
        p.pad.sy = (int8_t) strtol(w[4], 0, 0);
        p.pad.trig_r = n >= 9 ? (uint8_t) num(w[8]) : 0;
    } else if (!strcmp(w[0], "door") && n >= 3 && n_reqs < sizeof(door_reqs) / sizeof(door_reqs[0])) {
        door_reqs[n_reqs].tick = (unsigned) num(w[1]);
        door_reqs[n_reqs].area = (unsigned) num(w[2]);
        n_reqs++;
    }
    // weapon, comment-only and reference-only lines (resume, actor, ...) are not read: the DOOR scene has none
}

void e1_room_change_boot()
{
#ifndef E2_BOSS
    file_t f = fs_open("/cd/DOOR.TXT", O_RDONLY);
    if (f < 0) return;
    const uint32_t n = fs_total(f);
    char* text = (char*) malloc(n + 1);
    const int got = text ? (int) fs_read(f, text, n) : -1;
    fs_close(f);
    if (got != (int) n) { e1_log("E1 DOOR: DOOR.TXT not read (%d of %lu bytes)\n", got, (unsigned long) n); free(text); return; }
    text[n] = 0;
    door_route.find = 0x00002000;   // the village route's find flags (core/route.cpp)
    for (char* l = text; l && *l;) {
        char* e = strchr(l, '\n');
        if (e) *e = 0;
        parse_line(l);
        l = e ? e + 1 : 0;
    }
    free(text);
    if (!door_route.room || !door_route.ticks || !n_reqs || door_route.ticks > E1_TICKS) {
        e1_log("E1 DOOR: DOOR.TXT refused (room %x ticks %u doors %u)\n", door_route.room, door_route.ticks, n_reqs);
        return;
    }
    e1_door_scene = 1;
    // the controls (boot files beside DOOR.TXT; core/e1_core.h lists the others)
    file_t c = fs_open("/cd/MEMKEEP", O_RDONLY);
    if (c >= 0) { fs_close(c); ctl_memkeep = 1; e1_log("E1 MEMKEEP: one 4 KiB block kept across the first leave (control)\n"); }
    c = fs_open("/cd/DOORREADX", O_RDONLY);
    if (c >= 0) { fs_close(c); ctl_readx = 1; e1_log("E1 DOORREADX: a disc file opened in the first load, read 10 ticks after it (control)\n"); }
    c = fs_open("/cd/DISCFAIL", O_RDONLY);
    if (c >= 0) { fs_close(c); ctl_discfail = 1; e1_log("E1 DISCFAIL: the first DMA transfer of the first load reported done without it (control)\n"); }
    c = fs_open("/cd/DISCNB", O_RDONLY);   // lane eng-load2 (control): the stream's last 32 bytes requested as KOS does
    if (c >= 0) { fs_close(c); disc_safe_nb_arm(); e1_log("E1 DISCNB: fs_iso9660's 32-byte stream request passed on non-blocking (control)\n"); }
    e1_log("E1 DOOR: room %03x pos %d %d %d ang %d/1000 ticks %u pads %u doors %u seed %04x\n", door_route.room,
           (int) door_route.pos[0], (int) door_route.pos[1], (int) door_route.pos[2], (int) (door_route.ang * 1000.0f),
           door_route.ticks, n_pads, n_reqs, door_seed);
#endif
}
const E1Route* e1_door_route() { return e1_door_scene ? &door_route : 0; }
int e1_door_pad(unsigned tick, E1Pad* out)
{
    if (!e1_door_scene) return 0;
    E1Pad p = {0, 0, 0, 0};
    for (unsigned i = 0; i < n_pads; i++)
        if (door_pads[i].tick <= tick) p = door_pads[i].pad;   // piecewise constant, as re4ref's pad_for
    *out = p;
    return 1;
}
unsigned e1_door_seed() { return door_seed; }

// ---- the request (LOGGED STUB until the area check is hosted in this image: request R1) ----
static unsigned fade_eff[8];
void e1_room_change_tick_begin(unsigned tick)
{
    if (!e1_door_scene) return;
    for (unsigned i = 0; i < n_reqs; i++) {
        if (door_reqs[i].tick != tick) continue;
        const uint8_t* aev = (const uint8_t*) GetDataExt(pG->pRoom, "AEV", 0);
        const unsigned num = aev ? *(const uint16_t*) (aev + 6) : 0;
        const SceAtWork* w = 0;
        for (unsigned k = 0; aev && k < num; k++) {
            const SceAtWork* r = (const SceAtWork*) (aev + 0x10 + k * sizeof(SceAtWork));
            if (r->no == door_reqs[i].area) w = r;
        }
        if (!w || w->type != 1 || w->doorFunc) {
            e1_log("E1 DOOR STUB refused at tick %u: room %03x area %u %s\n", tick, (unsigned) pG->room_id,
                   door_reqs[i].area, !w ? "not in the room's AEV" : w->type != 1 ? "not a door" : "has a door function");
            continue;
        }
        pG->Stop_flg = 0xFFFFFFFFu;
        pG->NextPos = w->dstPos;
        pG->NextY = w->dstAngle;
        pG->room_id_prev = pG->room_id;
        pG->Part_old = pG->Part;
        pG->next_stage = w->dstStage;
        pG->next_room_no = w->dstRoom;
        pG->next_point = w->dstPart;
        pG->door_no = w->doorNo;
        pG->Rno0 = 4;
        pG->Rno1 = pG->Rno2 = pG->Rno3 = 0;
        pG->r_continue_cnt = 0;
        pG->System_flg &= ~0x40u;
        fade_eff[i] = w->doorFadeEff;
        e1_stub_hit("SceAtCheck(door request planted: R1)", (int) door_reqs[i].area);
        e1_log("E1 DOOR request tick %u room %03x area %u -> r%x%02x part %u pos %d %d %d ang %d/1000 fade %u (planted: "
               "the area check is not hosted in this image)\n", tick, (unsigned) pG->room_id, door_reqs[i].area,
               (unsigned) w->dstStage, (unsigned) w->dstRoom, (unsigned) w->dstPart, (int) w->dstPos.x, (int) w->dstPos.y,
               (int) w->dstPos.z, (int) (w->dstAngle * 1000.0f), (unsigned) w->doorFadeEff);
    }
    if (ctl_readx && readx_fd >= 0 && tick == readx_tick) {   // DOORREADX (control): a read placed in play
        static char b[2048];
        fs_seek(readx_fd, 65536, SEEK_SET);
        fs_read(readx_fd, b, sizeof b);
    }
}
int e1_room_change_pending()
{
#ifdef E2_BOSS
    return 0;   // the fight and boss images do not change room (their scenes are one room; their engine code is r101/r119)
#else
    return pG->Rno0 == 4;
#endif
}

// ---- memory marks and the round trip ----
// Lane eng-load2: the KOS heap is judged on kos-net, the heap in use less the allocator's slack on the tracked blocks
// (core/memmap.cpp e1_mm_ledger). kos-used (mallinfo's uordblks) also counts the bytes a chunk keeps when its remainder
// is too small to split, which depend on where a block lands: on the DOOR scene the second village visit held the same
// 315 blocks, same sizes and same callers, as the first, and uordblks read 16 B more (a 256,212 B block placed with 16 B
// of slack, small blocks in reused chunks; Flycast run dbg1, a debug build). kos-net counts every block's bytes and
// header, tracked or not (a block KOS or newlib takes for itself is in uordblks and not in the slack), and does not
// depend on where the blocks land. kos-used is still printed. A ledger that lost blocks (list full) fails the check.
struct RoomMarks { unsigned room; uint32_t kos_used, kos_net, blocks, asked, lost, arena_used, vram_free, col_pieces, skel_tables; };
extern "C" void e1_mm_ledger(uint32_t* n, uint32_t* asked, uint32_t* slack, uint32_t* lost);   // core/memmap.cpp
static RoomMarks marks[8];
static unsigned n_marks;
static uint32_t kos_last;   // the KOS heap in use at the last tick's end or room mark (E1 KOSGROW)
struct Visit { unsigned room, ticks, first_tick; };
static Visit visits[8];
static unsigned n_visits;
void e1_room_marks_take(const char* when)
{
    if (n_marks >= 8) return;
    RoomMarks& m = marks[n_marks++];
    struct mallinfo mi = mallinfo();
    uint32_t arena = 0;
    for (int h = 0; h < 13; h++) arena += e1_arena.used[h];
    m.room = pG->room_id;
    m.kos_used = (uint32_t) mi.uordblks;
    uint32_t slack = 0;
    e1_mm_ledger(&m.blocks, &m.asked, &slack, &m.lost);
    m.kos_net = m.kos_used - slack;
    kos_last = m.kos_used;
    m.arena_used = arena;
    m.vram_free = e1_draw_opened_c() ? (uint32_t) pvr_mem_available() : 0xFFFFFFFFu;
    m.col_pieces = col_piece_count();
    m.skel_tables = skel_table_count();
    e1_log("E1 ROOMMARK %u room %03x %s kos-used %lu kos-net %lu blocks %lu asked %lu lost %lu arena-used %lu vram-free %ld "
           "col-pieces %lu skel-tables %lu\n", n_marks - 1, m.room, when, (unsigned long) m.kos_used, (unsigned long) m.kos_net,
           (unsigned long) m.blocks, (unsigned long) m.asked, (unsigned long) m.lost, (unsigned long) m.arena_used,
           m.vram_free == 0xFFFFFFFFu ? -1l : (long) m.vram_free, (unsigned long) m.col_pieces, (unsigned long) m.skel_tables);
    if (n_visits < 8) visits[n_visits++] = {m.room, 0, e1_tick + 1};
}
void e1_room_tick_done()
{
    if (n_visits) visits[n_visits - 1].ticks++;
    // DOOR scene (a function run): the KOS heap's growth in play, by tick (after the tick's rows; diagnostic): play
    // should take nothing from it, a room change should return what its room took
    if (!e1_door_scene) return;
    const uint32_t u = (uint32_t) mallinfo().uordblks;
    if (kos_last && u != kos_last)
        e1_log("E1 KOSGROW tick %lu room %03x kos-used %lu (%+ld)\n", (unsigned long) e1_tick, (unsigned) pG->room_id,
               (unsigned long) u, (long) u - (long) kos_last);
    kos_last = u;
}

// ---- the loading state ----
// The KOS heap in use after each step of a load (DOOR scene only; loading is not timed): where a round trip's
// difference is taken or kept (E1 LOADSTEP).
// Lane eng-load2: and the time each step took (us since the previous step; the first step of a room's set-up counts
// from the previous line, so the phases of a load are its steps from leave.start to enter.memory-map). The log line is
// formatted after the step's clock is read: its own cost is not in the next step's time.
void e1_load_step(const char* what)
{
    if (!e1_door_scene) return;
    static uint32_t last;
    static uint64_t t_last;
    const uint64_t t = timer_us_gettime64();
    const uint32_t u = (uint32_t) mallinfo().uordblks;
    e1_log("E1 LOADSTEP %s kos-used %lu (%+ld) us %lu\n", what, (unsigned long) u, (long) u - (long) last,
           (unsigned long) (t_last ? t - t_last : 0));
    last = u;
    t_last = timer_us_gettime64();
}
static unsigned n_loads, n_failed;
static void* kept_block;
static const char* room_pack(unsigned room)
{
    switch (room) {
    case 0x101: return "/cd/CROSS.PAK";   // the village's whole-room bake
    // the farm's whole-room bake, under its own name: /cd/FARM.PAK is one of the two packs the renderer sizes its
    // resident block from (render/native_scene.inc native_open), and the bench's farm bake needs 1.88 MB more of it than
    // the E1 image's: staged as FARM.PAK it put the KOS heap 1.47 MB into the behaviour arena (lane eng-load1, run 2)
    case 0x103: return "/cd/R103.PAK";
    case 0x11d: return "/cd/HILL.PAK";
    default: return 0;
    }
}
static int load_failed(unsigned from, unsigned to, const char* why)
{
    n_failed++;
    e1_log("E1 LOAD FAILED %u room %03x>%03x: %s\n", n_loads, from, to, why);
    return -1;
}
// The actors' skeleton tables (the skeleton service keys them by record; the records go with the room heap)
static unsigned release_skeletons()
{
    unsigned n = 0;
    while (skel_table_count()) {
        const u32 before = skel_table_count();
        cModel* m = (cModel*) skel_table_at(0)->model;
        m->releasePartsList(0);
        if (skel_table_count() >= before) break;   // not released: counted by the marks
        n++;
    }
    return n;
}
int e1_room_change_run(unsigned tick)
{
#ifdef E2_BOSS
    (void) tick;
    return 0;
#else
    const uint64_t t0 = timer_us_gettime64();
    const unsigned from = pG->room_id, to = pG->next_room;
    const unsigned load = n_loads;
    e1_loading_begin(load, from, to);
    if (ctl_discfail && load == 0) disc_safe_fail_arm();
    if (to !=(unsigned) (pG->next_stage << 8 | pG->next_room_no)) {
        e1_loading_end(load, tick, 0);
        return load_failed(from, to, "next_room and next_stage / next_room_no disagree");
    }
    {   // the trace's room line (LR): the engine's transition between two LT lines
        char l[128];
        const int k = snprintf(l, sizeof l, "LR t=%u room %03x>%03x pos %08lx,%08lx,%08lx ang %08lx\n", tick, from, to,
                               (unsigned long) *(uint32_t*) &pG->NextPos.x, (unsigned long) *(uint32_t*) &pG->NextPos.y,
                               (unsigned long) *(uint32_t*) &pG->NextPos.z, (unsigned long) *(uint32_t*) &pG->NextY);
        e1_trace_put(l, (unsigned) k);
    }
    const float pos[3] = {pG->NextPos.x, pG->NextPos.y, pG->NextPos.z};
    const float ang = pG->NextY;
    // leave: the first room's memory returned
    e1_load_step("leave.start");
    const unsigned skels = release_skeletons();
    e1_load_step("leave.skeletons");
    if (col_room_release) col_room_release();
    else e1_stub_hit("col_room_release (collision tables kept: R2)", (int) col_piece_count());
    if (e1_draw_opened_c()) {
        if (e1_draw_close_c) e1_draw_close_c();
        else e1_stub_hit("e1_draw_close_c (the first room's pack kept: R3)", (int) from);
    }
    e1_load_step("leave.collision+renderer");
    e1_room_release();
    e1_load_step("leave.archive");
    if (ctl_memkeep && load == 0) {   // MEMKEEP (control): a block kept across the leave
        kept_block = malloc(4096);
        e1_log("E1 MEMKEEP: 4096 bytes kept at %p\n", kept_block);
    }
    // the request's state handoff (game.cpp gameDoordemo 1533-1543 and gameRoomMemInit 1599-1604; see the head)
    pG->sub_pos.x = pos[0];
    pG->sub_pos.y = pos[1];
    pG->sub_pos.z = pos[2];
    pG->sub_angle = ang;
    pG->room_id = (u16) to;
    pG->Part = pG->next_point;
    if ((s32) pG->Debug_flg[2] >= 0 && !(pG->System_flg & 0x80000)) pG->JumpPoint = 0;
    memset(pG->pad_16C, 0, 0x4E00);
    pG->Debug_flg[0] = pG->Debug_flg[1] = 0;
    pG->Status_flg[0] = pG->Status_flg[1] = pG->Status_flg[2] = 0;
    pG->Rno0 = 1;
    pG->Rno1 = pG->Rno2 = pG->Rno3 = 0;
    // enter: the second room
    e1_load_step("handoff");
    e1_room_setup(to, pos, ang, 0);
    e1_load_step("enter.room-setup");
    if (!pG->pRoom) { e1_loading_end(load, tick, (uint32_t) (timer_us_gettime64() - t0)); return load_failed(from, to, "room archive missing"); }
    if (!pPL) { e1_loading_end(load, tick, (uint32_t) (timer_us_gettime64() - t0)); return load_failed(from, to, "player not created"); }
    if (e1_draw_opened_c() || e1_draw_close_c) {
        const char* pack = room_pack(to);
        if (!pack) { e1_loading_end(load, tick, 0); return load_failed(from, to, "no renderer pack for the room"); }
        if (e1_draw_reopen_c) {
            if (!e1_draw_reopen_c(pack)) {
                e1_loading_end(load, tick, (uint32_t) (timer_us_gettime64() - t0));
                return load_failed(from, to, "renderer pack refused or missing");
            }
        } else {
            e1_stub_hit("e1_draw_reopen_c (the next room drawn with the first room's pack: R3)", (int) to);
        }
    }
    if (ctl_readx && load == 0) {   // DOORREADX: a disc file opened while loading (allowed), read in play below
        readx_fd = fs_open("/cd/em/pl11.drs", O_RDONLY);
        readx_tick = tick + 10;
    }
    if (e1_draw_reopen_c && e1_door_scene)
        e1_log("E1 LOADPACK %s bytes %lu header %lu textures %lu resident %lu world %lu runtime %lu models %lu frame0 %lu "
               "bind+actors %lu vis %lu us\n", room_pack(to), (unsigned long) m1_open_us[9], (unsigned long) m1_open_us[0],
               (unsigned long) m1_open_us[1], (unsigned long) m1_open_us[2], (unsigned long) m1_open_us[3],
               (unsigned long) m1_open_us[4], (unsigned long) m1_open_us[5], (unsigned long) m1_open_us[6],
               (unsigned long) m1_open_us[7], (unsigned long) m1_open_us[8]);
    e1_load_step("enter.renderer");
    e1_memmap_sample();      // the memory map after each load (overlaps, the arena, the stack)
    e1_heap_room_checks();   // the heap descriptors' map
    e1_load_step("enter.memory-map");
    const uint32_t us = (uint32_t) (timer_us_gettime64() - t0);
    n_loads++;
    e1_log("E1 LOAD %u room %03x>%03x at tick %u: skeleton tables released %u, player %d %d %d ang %d/1000, fade %u\n",
           load, from, to, tick, skels, (int) pPL->pos.x, (int) pPL->pos.y, (int) pPL->pos.z, (int) (pPL->ang.y * 1000.0f),
           fade_eff[load < 8 ? load : 7]);
    e1_room_marks_take("after a load");
    e1_loading_end(load, tick, us);
    return 0;
#endif
}

// The scene's report: each visit's ticks, the marks of each room's first and last visit, the verdict.
void e1_room_change_report()
{
    if (!e1_door_scene) return;
    for (unsigned i = 0; i < n_visits; i++)
        e1_log("E1 ROOM visit %u room %03x ticks %u first-tick %u\n", i, visits[i].room, visits[i].ticks, visits[i].first_tick);
    const char* bad = 0;
    unsigned a = 0, b = 0;
    if (n_marks < 3) bad = "fewer than three rooms ready";
    else {
        a = 0;
        b = n_marks - 1;
        const RoomMarks &x = marks[a], &y = marks[b];
        if (x.room != y.room) bad = "the last room is not the first";
        else if (x.lost || y.lost) bad = "kos ledger incomplete";
        else if (x.kos_net != y.kos_net) bad = "kos-net";
        else if (x.arena_used != y.arena_used) bad = "arena-used";
        else if (x.vram_free != y.vram_free) bad = "vram-free";
        else if (x.col_pieces != y.col_pieces) bad = "col-pieces";
        else if (x.skel_tables != y.skel_tables) bad = "skel-tables";
    }
    char rooms[48] = "";
    for (unsigned i = 0; i < n_marks && i < 6; i++) {
        const size_t l = strlen(rooms);
        snprintf(rooms + l, sizeof rooms - l, "%s%03x", i ? ">" : "", marks[i].room);
    }
    const RoomMarks z = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
    const RoomMarks &x = n_marks ? marks[a] : z, &y = n_marks ? marks[b] : z;
    // the selector reads this line's format (loader/selector.c): the ledger goes on a line of its own before it
    e1_log("E1 ROUNDTRIP-LEDGER kos-net %lu/%lu blocks %lu/%lu asked %lu/%lu lost %lu/%lu (the KOS heap is judged on kos-net)\n",
           (unsigned long) x.kos_net, (unsigned long) y.kos_net, (unsigned long) x.blocks, (unsigned long) y.blocks,
           (unsigned long) x.asked, (unsigned long) y.asked, (unsigned long) x.lost, (unsigned long) y.lost);
    e1_log("E1 ROUNDTRIP rooms %s loads %u failed %u kos-used %lu/%lu arena-used %lu/%lu vram-free %ld/%ld col-pieces %lu/%lu "
           "skel-tables %lu/%lu: %s%s\n", rooms[0] ? rooms : "-", n_loads, n_failed, (unsigned long) x.kos_used,
           (unsigned long) y.kos_used, (unsigned long) x.arena_used, (unsigned long) y.arena_used,
           x.vram_free == 0xFFFFFFFFu ? -1l : (long) x.vram_free, y.vram_free == 0xFFFFFFFFu ? -1l : (long) y.vram_free,
           (unsigned long) x.col_pieces, (unsigned long) y.col_pieces, (unsigned long) x.skel_tables,
           (unsigned long) y.skel_tables, bad ? "LEAK " : "equal", bad ? bad : "");
}
