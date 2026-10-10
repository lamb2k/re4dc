// D367 test warp rig (DBG_WARP=1, test builds only; compiled out otherwise, and a disc without
// /cd/dc/warp.txt boots normally). Starts the game in a chosen room with Leon placed and the
// scenario state an event needs, within seconds of boot:
//  - Title: once the title data is loaded (title state 2) the title, picker and menus are skipped;
//    titleExit takes the debug-start path (cRoomJmp over debug/roomInfo.dat, the same path as
//    config.txt [STAGE]/[ROOM] + START) with the warp room, so the room loads normally
//    (GameTask -> gameInit new game -> gameStageInit -> gameRoomInit). Quality comes from
//    RE4DCCFG / quality.txt as usual (re4dc_quality_freeze in titleExit).
//  - Position: `pos` / `dir` replace the jump point's NextPos / NextY (-> sub_pos / sub_angle).
//  - Flags: applied once, at the first room entry (re4dc_room_enter: after gameInit cleared the
//    new-game state, before the room's init function reads them): room save flags (RsfSet),
//    Scenario_flg, Item_find_flg, door_unlock, and `dead` enemy-list entries (EmListSetAlive(no, 0),
//    as the event that removes them does: r101's bell list, so a post-bell start has no villagers).
//  - Actions: `act <frame> <button> <hold>` presses a button / pushes the stick in the first
//    room (door test mode). Frames count PADRead calls in that room: one per game frame in play,
//    and they keep counting inside the sub screen (inventory, files), whose loop pauses the game
//    loop, so `act 300 y 3` + `act 600 b 3` opens and closes the inventory. Every room entry and
//    action is logged with vblank and wall time.
//  - Boot: the VMU_SAVE card screen (card=8/1) is answered Up+A, so a warp disc needs no padscript.
//  - Debug trigger: `trg <no> <room frame> [room]` makes the source's developer shortcut
//    DebugTrg(no) (retail stub: always 0) return 1 once, at or after that frame of the current room
//    (of `room` only, when given). r101_checkEmNum rings the bell on DebugTrg(0), so a square fight
//    reaches the bell event without 15 kills or 11,700 fight frames. r100 reads DebugTrg(1) for its
//    own shortcut; the number keeps the two apart.
//  - Kill: `kill <em id> <room frame> [room]` kills the first live enemy with that model id, once at
//    or after that frame of the current room (of `room` only, when given), through the source's own
//    damage path: a handgun hit (cDmgInfo::set kind 1 on the hit box emSphereAtCk picks, as
//    PlWepHitCheck3 registers a hit) every frame no hit is pending, until its hp is gone. The enemy's
//    own damage check then runs its death, and whatever the room links to it (SceExecLinkEmDead) runs
//    as in play: r100's s03 Ganado (id 0x12) -> r100_Sce_zombi_dead -> the ambush + s20.
//    `kill <em id> <room frame> <room> <kind>` registers that weapon kind instead (cDmgInfo m_Wep): r119's
//    giant (id 0x2b) loses hp only on the parasite (part 0x3F) or to kind 0xD, which em2b's damage check
//    turns into hp 0 (the rocket launcher kill of the original game).
//  - Move: `goto <room frame> x y z [ang]` (first room, up to 4) moves Leon there at or after that
//    frame, outside events; an area trigger at the spot then fires as when he walks in (r100: area
//    6 pre-reads s03/s20, area 0xA starts s03), so a fresh room entry (its entry event and call)
//    reaches a later event without a scripted walk.
// A warp start is NOT STRICT against continued play (fresh room entry with synthesized flags; the
// RNG, timers and enemy state are those of a new game). It is for iteration and bring-up only.
//
// /cd/dc/warp.txt (tools/d367/warp.py writes it from a named preset):
//   room 0x100 | jp 0 | pos x y z | dir 0x8000 | ang <rad> | rsf <room> <bit>... |
//   scenario <0|1> <hex> | find <hex> | unlock <0|1> <hex> | dead <no>... | inv default | area <no> [dx dz] |
//   act <frame> <a|b|x|y|start|fwd|back|none|0xMASK> <hold> | arm <frame> <item id> | trg <no> <frame> [room] | kill <id> <frame> [room [kind]] |
//   goto <frame> x y z [ang] | dump | name <preset> | late <mask> [tick] [room] (warp_late.h) | entry <n> |
//   radio <frame> <call no 0..23> (source radio replay, resource-lifetime test only)
//   god (Leon's life refilled every frame) | alert <frame> (the crowd hunts Leon from that frame of its entry)
//   fxmode <flags> (EFFECT_PS2_TOGGLE builds: the effect look at load; 1 fade clamp, 2 PS2 haze, 4 PS2 streak)
//   charbake <variant> [room frame] (CHARBAKE_TOGGLE builds: the character texture variant at load, or switched at
//   that frame of the first room, as the look toggle switches it at run time; up to 8 timed lines)
//   lookstep <room frame> (LOOK_TOGGLE builds: the next look preset at that frame of the first room, the call the
//   X + START chord makes; up to 16 timed lines; issue #11 preset stepping checks)
//  - Later rooms: `entry <n>` (n >= 2) scopes the `act` / `goto` lines after it to the n-th room entry of the run
//    (their frames count in that room; the door that leads there is the source's). Without it every act / goto
//    belongs to the first room, as before. A fixture with entries also logs Leon's placement in those rooms.
#if RE4DC_DBG_WARP
#include "types.h"
#include "global.h"
#include "player.h"
#include "room_data.h"
#include "flag_rsf.h"
#include "sce_at.h"
#include "area.h"
#include "em_set.h"
#include "em.h"
#include "em_sub.h"
#include "item.h"
#include "main_mem.h"
#include "snd.h"
#include "sce.h"
#include "sce_sys.h"
#include "sscrn.h"
#include "re4dc_platform.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <arch/timer.h>
#include <kos/thread.h>

extern "C" {
u32 re4dc_vi_retrace_count(void);

int re4dc_fixture_read(const char* path, char* buffer, unsigned size);
void re4dc_fixture_state(const char* name, int a, int b);  // pad.cpp fixture anchors (overlay)
#if defined(RE4DC_LOOK_TOGGLE)
extern "C" void re4dc_look_set(unsigned mode);  // native_static.cpp (post30.mk LOOK_TOGGLE)
extern "C" void re4dc_look_osd_toggle(void);  // native_static.cpp (post30.mk LOOK_TOGGLE)
extern "C" void re4dc_look_cycle(void);  // native_static.cpp (post30.mk LOOK_TOGGLE)
#endif
#if defined(RE4DC_EFFECT_PS2_TOGGLE) && RE4DC_EFFECT_PS2_TOGGLE
void re4dc_ps2fx_set(unsigned flags);  // esp_sub.cpp (effects30.mk EFFECT_PS2_TOGGLE)
#endif
}
#if defined(RE4DC_CHARBAKE_TOGGLE) && RE4DC_CHARBAKE_TOGGLE
extern "C" void re4dc_charbake_set(unsigned variant);  // coarse_actor.cpp (charbake.mk CHARBAKE_TOGGLE)
#endif

namespace {
struct Act { u32 frame; u16 buttons; s8 stick; u16 hold; u8 entry; };
struct Rsf { u16 room; u8 bit; };
// Replays a source radio call to test movie-to-subscreen resource handoff.
// This command exists only in the DBG_WARP test rig; it does not certify route order.
static void radio_fixture(int no) {
    re4dc_log("warp: radio replay begin no=%d frame=%u\n",no,(unsigned)pG->Frame_cnt);
    OpeSetOpenTerm(no,0,0,0,0);
    re4dc_log("warp: radio replay end no=%d frame=%u\n",no,(unsigned)pG->Frame_cnt);
}
struct Warp {
    bool loaded, active, placed_logged, applied, dump;
    char name[32];
    u16 room;
    int jp;
    bool has_pos, has_dir, has_area;
    f32 pos[3], dir;
    int area_no;
    f32 area_dx, area_dz;
    Rsf rsf[32];
    unsigned n_rsf;
    u32 scenario[2], find, unlock[2], items[2];  // items: pG->item_flags[0..1] (key-item pickups, r105 area 8)
    u8 dead[64];
    unsigned n_dead;
    Act act[16];
    unsigned n_act;
    bool has_trg, trg_fired;
    int trg_no;
    u32 trg_frame;
    u16 trg_room;  // 0: any room
    bool has_kill, kill_done;
    int kill_id;
    u32 kill_frame, kill_hits;
    u16 kill_room;  // 0: any room
    u8 kill_kind;   // cDmgInfo kind of each hit (1: handgun)
    cEm* kill_em;   // the target once found (kept until its hp is gone)
    u32 kill_watch; // after the kill: state lines left
    struct Goto { u32 frame; f32 pos[3]; f32 ang; bool has_ang, done; u8 entry; } go[4];
    unsigned n_go;
    // arm <room frame> <item id>: once at that frame of the first room, ItemMgr.debugWeapon(id) (the case's armed
    // weapon) and the weapon reload SubScreenExit does when a new weapon was equipped in the inventory (SndBlkStop(2),
    // weaponRelease / weaponLoad / weaponInit: ReadWepData's DVD read, as on the inventory exit).
    struct ArmItem { u32 frame; u16 id; bool done; } arm[8];
    unsigned n_arm;
    bool has_radio, radio_done;
    u32 radio_frame;
    int radio_no;
    // census <room frame>: heap 4 occupancy by allocation tag and its free cells, once at that frame (test only).
    u32 census[6];
    bool census_done[6];
    unsigned n_census;
#if defined(RE4DC_CHARBAKE_TOGGLE) && RE4DC_CHARBAKE_TOGGLE
    struct CharbakeAt { u32 frame; u8 variant; bool done; } charbake_at[8];  // charbake <variant> <room frame>
    unsigned n_charbake_at;
    struct LookStep { u32 frame; bool done; } lookstep[16];  // lookstep <room frame> (LOOK_TOGGLE)
    unsigned n_lookstep;
#endif
    bool act_source_clock;  // opt-in fixture holds count source pad ticks, not wall-time stalls
    u8 parse_entry, max_entry;  // `entry <n>`: the room entry later act / goto lines belong to (1 = first room)
#if RE4DC_WARP_JUMP
    struct Jump { u32 frame; u16 from, to; f32 pos[3]; f32 ang; bool done; } jump[8];
    unsigned n_jump;
    bool jump_wait;  // a jump fired: the next one waits for the room entry it asked for
    unsigned jump_fired, jump_frame, jump_retries;  // the fired entry, its room frame, re-issues so far
#endif
    // runtime
    u32 room_frames, first_room_gen, rooms;
    u32 pad_frames;  // PADRead calls in the current room: the action clock
    int cur_act;
    u32 cur_until;
    unsigned next_act;
    unsigned long long boot_us;
    u32 card_frames;
    u32 last_pad_vbl;
    // late <mask> [tick] [room] (warp_late.h): same-binary A/B switches from a global tick on
    bool has_late, late_logged;
    u32 late_mask, late_tick;
    u16 late_room;
    // god: Leon's life refilled every frame (benchmark fixtures; hwcal's invuln). alert <frame>: the room-forced
    // alert + the "Ganado hurt" alarm at Leon once at that room frame of its entry (hwcal's alert): the crowd hunts him.
    bool god, has_alert, alert_done;
    u32 alert_frame;
    u8 alert_entry;
    // freeze <tick>: the game thread stops at the top of that global tick (look checks: the last presented image
    // stays on screen, the same image in two arms whose logic is STRICT).
    bool has_freeze;
    u32 freeze_tick;
};
Warp wp;

u32 num(const char* s) { return (u32) strtoul(s, nullptr, 0); }

void load()
{
    wp.loaded = true;
    wp.parse_entry = wp.max_entry = 1;
    static char text[2048];
    const int len = re4dc_fixture_read("/cd/dc/warp.txt", text, sizeof(text) - 1);
    if (len <= 0) return;
    text[len] = 0;
    for (char* line = text; line && *line;) {
        char* next = strchr(line, '\n');
        if (next) *next++ = 0;
        char* hash = strchr(line, '#');
        if (hash) *hash = 0;
        char* tok[12];
        int n = 0;
        for (char* t = strtok(line, " \t\r"); t && n < 12; t = strtok(nullptr, " \t\r")) tok[n++] = t;
        line = next;
        if (!n) continue;
        const char* k = tok[0];
        if (!strcmp(k, "room") && n >= 2) {
            wp.room = (u16) num(tok[1]);
            wp.active = true;
        } else if (!strcmp(k, "name") && n >= 2) {
            strncpy(wp.name, tok[1], sizeof(wp.name) - 1);
        } else if (!strcmp(k, "jp") && n >= 2) {
            wp.jp = (int) num(tok[1]);
        } else if (!strcmp(k, "pos") && n >= 4) {
            for (int i = 0; i < 3; ++i) wp.pos[i] = (f32) strtod(tok[1 + i], nullptr);
            wp.has_pos = true;
            if (n >= 6 && !strcmp(tok[4], "dir")) {
                wp.dir = (f32) (s16) num(tok[5]) * (3.14159265f / 32768.0f);
                wp.has_dir = true;
            }
        } else if (!strcmp(k, "dir") && n >= 2) {
            wp.dir = (f32) (s16) num(tok[1]) * (3.14159265f / 32768.0f);
            wp.has_dir = true;
        } else if (!strcmp(k, "ang") && n >= 2) {
            wp.dir = (f32) strtod(tok[1], nullptr);
            wp.has_dir = true;
        } else if (!strcmp(k, "rsf") && n >= 3) {
            const u16 room = (u16) num(tok[1]);
            for (int i = 2; i < n && wp.n_rsf < 32; ++i) {
                const u32 bit = num(tok[i]);
                if (bit < 32) wp.rsf[wp.n_rsf++] = {room, (u8) bit};
            }
        } else if (!strcmp(k, "scenario") && n >= 3) {
            wp.scenario[num(tok[1]) & 1] |= num(tok[2]);
        } else if (!strcmp(k, "find") && n >= 2) {
            wp.find |= num(tok[1]);
        } else if (!strcmp(k, "unlock") && n >= 3) {
            wp.unlock[num(tok[1]) & 1] |= num(tok[2]);
        } else if (!strcmp(k, "items") && n >= 3) {
            wp.items[num(tok[1]) & 1] |= num(tok[2]);
        } else if (!strcmp(k, "dead") && n >= 2) {
            for (int i = 1; i < n && wp.n_dead < 64; ++i) wp.dead[wp.n_dead++] = (u8) num(tok[i]);
        } else if (!strcmp(k, "inv") && n >= 2) {
            if (strcmp(tok[1], "default")) re4dc_log("warp: inv %s not supported (new-game inventory kept)\n", tok[1]);
        } else if (!strcmp(k, "radio") && n >= 3 && num(tok[2]) < 24) {
            wp.has_radio=true;wp.radio_frame=num(tok[1]);wp.radio_no=(int)num(tok[2]);
        } else if (!strcmp(k, "area") && n >= 2) {
            wp.area_no = (int) num(tok[1]);
            wp.area_dx = n >= 3 ? (f32) strtod(tok[2], nullptr) : 0.0f;
            wp.area_dz = n >= 4 ? (f32) strtod(tok[3], nullptr) : 0.0f;
            wp.has_area = true;
        } else if (!strcmp(k, "act_clock") && n >= 2) {
            if (strcmp(tok[1], "source") && strcmp(tok[1], "wall"))
                re4dc_missing("warp act_clock must be source or wall");
            wp.act_source_clock = !strcmp(tok[1], "source");
            re4dc_log("warp: action holds clock=%s\n", wp.act_source_clock ? "source" : "wall");
        } else if (!strcmp(k, "entry") && n >= 2 && num(tok[1]) >= 1 && num(tok[1]) <= 8) {
            wp.parse_entry = (u8) num(tok[1]);
            if (wp.parse_entry > wp.max_entry) wp.max_entry = wp.parse_entry;
        } else if (!strcmp(k, "act") && n >= 4 && wp.n_act < 16) {
            Act& a = wp.act[wp.n_act++];
            a.entry = wp.parse_entry;
            a.frame = num(tok[1]);
            a.hold = (u16) num(tok[3]);
            a.buttons = 0;
            a.stick = 0;
            const char* b = tok[2];
            if (!strcmp(b, "a")) a.buttons = 0x0100;
            else if (!strcmp(b, "b")) a.buttons = 0x0200;
            else if (!strcmp(b, "x")) a.buttons = 0x0400;
            else if (!strcmp(b, "y")) a.buttons = 0x0800;
            else if (!strcmp(b, "start")) a.buttons = 0x1000;
            else if (!strcmp(b, "fwd")) a.stick = 80;
            else if (!strcmp(b, "back")) a.stick = -80;
            else if (b[0] == '0' && b[1] == 'x') a.buttons = (u16) num(b);  // a raw button mask (R 0x0020 + A: 0x0120)
        } else if (!strcmp(k, "census") && n >= 2 && wp.n_census < 6) {
            wp.census_done[wp.n_census] = false;
            wp.census[wp.n_census++] = num(tok[1]);
        } else if (!strcmp(k, "arm") && n >= 3 && wp.n_arm < 8) {
            Warp::ArmItem& a = wp.arm[wp.n_arm++];
            a.frame = num(tok[1]);
            a.id = (u16) num(tok[2]);
            a.done = false;
        } else if (!strcmp(k, "trg") && n >= 3) {
            wp.has_trg = true;
            wp.trg_no = (int) num(tok[1]);
            wp.trg_frame = num(tok[2]);
            wp.trg_room = n >= 4 ? (u16) num(tok[3]) : 0;
        } else if (!strcmp(k, "kill") && n >= 3) {
            wp.has_kill = true;
            wp.kill_id = (int) num(tok[1]);
            wp.kill_frame = num(tok[2]);
            wp.kill_room = n >= 4 ? (u16) num(tok[3]) : 0;
            wp.kill_kind = n >= 5 ? (u8) num(tok[4]) : 1;
        } else if (!strcmp(k, "goto") && n >= 5 && wp.n_go < 4) {
            Warp::Goto& g = wp.go[wp.n_go++];
            g.entry = wp.parse_entry;
            g.frame = num(tok[1]);
            for (int i = 0; i < 3; ++i) g.pos[i] = (f32) strtod(tok[2 + i], nullptr);
            g.has_ang = n >= 6;
            g.ang = g.has_ang ? (f32) strtod(tok[5], nullptr) : 0.0f;
            g.done = false;
#if RE4DC_WARP_JUMP
        } else if (!strcmp(k, "jump") && n >= 8 && wp.n_jump < 8) {
            Warp::Jump& j = wp.jump[wp.n_jump++];
            j.frame = num(tok[1]);
            j.from = (u16) num(tok[2]);
            j.to = (u16) num(tok[3]);
            for (int i = 0; i < 3; ++i) j.pos[i] = (f32) strtod(tok[4 + i], nullptr);
            j.ang = (f32) strtod(tok[7], nullptr);
            j.done = false;
#endif
        } else if (!strcmp(k, "dump")) {
            wp.dump = true;
        } else if (!strcmp(k, "god")) {
            wp.god = true;
            re4dc_log("warp: god (Leon's life refilled every frame)\n");
        } else if (!strcmp(k, "alert") && n >= 2) {
            wp.has_alert = true;
            wp.alert_frame = num(tok[1]);
            wp.alert_entry = wp.parse_entry;
#if defined(RE4DC_LOOK_TOGGLE)
        } else if (!strcmp(k, "look") && n >= 2) {
            re4dc_look_set(num(tok[1]));   // post30.mk LOOK_TOGGLE: the look preset at load (gallery columns)
        } else if (!strcmp(k, "lookosd")) {
            re4dc_look_osd_toggle();       // LOOK_TOGGLE: the on-screen preset label always shown (label checks)
        } else if (!strcmp(k, "lookstep") && n >= 2 && wp.n_lookstep < 16) {
            wp.lookstep[wp.n_lookstep++] = {num(tok[1]), false};   // LOOK_TOGGLE: next preset at a room frame
#endif
        } else if (!strcmp(k, "freeze") && n >= 2) {
            wp.has_freeze = true;
            wp.freeze_tick = num(tok[1]);
#if defined(RE4DC_EFFECT_PS2_TOGGLE) && RE4DC_EFFECT_PS2_TOGGLE
        } else if (!strcmp(k, "fxmode") && n >= 2) {
            re4dc_ps2fx_set(num(tok[1]));
#endif
        } else if (!strcmp(k, "late") && n >= 2) {
            wp.has_late = true;
            wp.late_mask = num(tok[1]);
            wp.late_tick = n >= 3 ? num(tok[2]) : 1400;
            wp.late_room = n >= 4 ? (u16) num(tok[3]) : 0x100;
#if defined(RE4DC_CHARBAKE_TOGGLE) && RE4DC_CHARBAKE_TOGGLE
        } else if (!strcmp(k, "charbake") && n >= 2) {
            // charbake.mk CHARBAKE_TOGGLE: the character variant at load, or at a room frame of the first room
            if (n < 3) re4dc_charbake_set(num(tok[1]));
            else if (wp.n_charbake_at < 8) wp.charbake_at[wp.n_charbake_at++] = {num(tok[2]), (u8) num(tok[1]), false};
#endif
        } else {
            re4dc_log("warp: unknown line '%s'\n", k);
        }
    }
    re4dc_log("warp: /cd/dc/warp.txt %s room=%03x jp=%d pos=%s rsf=%u scenario=%08x/%08x find=%08x unlock=%08x/%08x acts=%u\n",
              wp.name[0] ? wp.name : "-", (unsigned) wp.room, wp.jp, wp.has_pos ? "set" : "jump point", wp.n_rsf,
              (unsigned) wp.scenario[0], (unsigned) wp.scenario[1], (unsigned) wp.find, (unsigned) wp.unlock[0],
              (unsigned) wp.unlock[1], wp.n_act);
    if (wp.has_kill) {
        re4dc_log("warp: kill 0x%02x armed at room frame %u room %03x\n", (unsigned) wp.kill_id,
                  (unsigned) wp.kill_frame, (unsigned) wp.kill_room);
    }
}

void stamp(const char* what)
{
    re4dc_log("warp: %s vbl=%u wall_ms=%u\n", what, (unsigned) re4dc_vi_retrace_count(),
              (unsigned) (timer_us_gettime64() / 1000));
}

void dump_areas()
{
    for (int no = 0; no < 256; ++no) {
        SceAtWork* w = SceAtPtr(no);
        if (!w) continue;
        Vec c = {0.0f, 0.0f, 0.0f};
        AreaData area;
        sceAtGetArea(&area, w);
        AreaGetCenterPos(&c, &area);
        if (w->type == 1) {
            re4dc_log("warp: area %02x type=%u flag=%02x trig=%02x shape=%u center=%d,%d,%d door->%u:%02x dst=%d,%d,%d lock=%u/%u\n",
                      no, w->type, w->flag, w->trigger, area.type, (int) c.x, (int) c.y, (int) c.z, w->dstStage,
                      w->dstRoom, (int) w->dstPos.x, (int) w->dstPos.y, (int) w->dstPos.z, w->lockType, w->lockFlag);
        } else {
            re4dc_log("warp: area %02x type=%u flag=%02x trig=%02x shape=%u center=%d,%d,%d check=%02x angle=%d range=%d\n",
                      no, w->type, w->flag, w->trigger, area.type, (int) c.x, (int) c.y, (int) c.z, w->checkFlag,
                      2 * (int) w->angle, 2 * (int) w->angleRange);  // degrees (sce_at.h: * 2 degrees)
            if (area.type == AREA_TYPE_XZ4) {
                const AreaXZ4& q = area.u.xz4;
                re4dc_log("warp: area %02x xz4 floor=%d height=%d p=%d,%d %d,%d %d,%d %d,%d\n", no, (int) q.floor,
                          (int) q.height, (int) q.p[0].x, (int) q.p[0].z, (int) q.p[1].x, (int) q.p[1].z, (int) q.p[2].x,
                          (int) q.p[2].z, (int) q.p[3].x, (int) q.p[3].z);
            }
        }
    }
}

// `kill`: once at or after its room frame, the first live enemy with the model id takes a handgun
// hit (kind 1) whenever none is pending, registered as PlWepHitCheck3 does (cDmgInfo::set on the
// hit box emSphereAtCk picks around the enemy); its own damage check applies it (LifeDownSet2,
// the hp <= 0 death, the scene links). Ends when its hp is gone or it left the live list.
void kill_poll()
{
    if (wp.kill_watch && wp.kill_em && (wp.room_frames % 15) == 0) {
        --wp.kill_watch;
        cEm* em = wp.kill_em;
        bool live = false;  // still in the enemy manager's list (else the object may be gone / reused)
        for (cEm* e = EmMgr.getEmPtr(wp.kill_id, 0); e; e = EmMgr.getEmPtr(wp.kill_id, e)) live |= e == em;
        re4dc_log("warp: kill watch frame %u t=%u m=%08x listed=%d be_flag=%08x hp=%d r=%u/%u/%u pos=%d,%d,%d color=%08x\n",
                  (unsigned) wp.room_frames, (unsigned) pG->Frame_cnt, (unsigned) (uintptr_t) em, (int) live,
                  live ? (unsigned) em->be_flag : 0u, live ? (int) em->hp : 0, live ? (unsigned) em->r_no_0 : 0u,
                  live ? (unsigned) em->r_no_1 : 0u, live ? (unsigned) em->r_no_2 : 0u, live ? (int) em->pos.x : 0,
                  live ? (int) em->pos.y : 0, live ? (int) em->pos.z : 0,
                  live && em->pModelInfo ? (unsigned) em->pModelInfo->colorWord : 0u);
    }
    if (!wp.has_kill || wp.kill_done) return;
    if (wp.kill_room && pG->room_id != wp.kill_room) return;
    if (wp.room_frames < wp.kill_frame) return;
    cEm* em = wp.kill_em;
    char what[64];
    if (!em) {
        for (em = EmMgr.getEmPtr(wp.kill_id, 0); em; em = EmMgr.getEmPtr(wp.kill_id, em)) {
            if ((em->be_flag & 0x21) == 0x21 && em->hp > 0) break;
        }
        if (!em) return;  // not placed yet: keep looking
        wp.kill_em = em;
        snprintf(what, sizeof(what), "kill 0x%02x fired in %03x at room frame %u hp=%d", (unsigned) wp.kill_id,
                 (unsigned) pG->room_id, (unsigned) wp.room_frames, (int) em->hp);
        stamp(what);
        re4dc_log("warp: kill target m=%08x pos=%d,%d,%d t=%u\n", (unsigned) (uintptr_t) em, (int) em->pos.x, (int) em->pos.y,
                  (int) em->pos.z, (unsigned) pG->Frame_cnt);
    }
    if (!(em->be_flag & 1) || em->hp <= 0) {
        wp.kill_done = true;
        wp.kill_watch = 40;  // then its state every 15 room frames, 40 times (death motion, fade, removal)
        snprintf(what, sizeof(what), "kill 0x%02x hp<=0 at room frame %u after %u hits", (unsigned) wp.kill_id,
                 (unsigned) wp.room_frames, (unsigned) wp.kill_hits);
        stamp(what);
        return;
    }
    if (em->dmg.m_Flag & 1) return;  // the last hit is still pending
    Vec c = em->pos;
    YARARE_INFO* part = emSphereAtCk(em, &c, &c, 5000.0f, 1, 5000.0f);
    if (!part) part = &em->hitInfo;
    Vec from = pPL ? pPL->pos : em->pos;
    em->dmg.set(0, 10, wp.kill_kind, &from, part->rad, part);
    ++wp.kill_hits;
}

// `goto`: in the first room, at or after its room frame and outside events (Status_flg[1]
// 0x10000000), Leon is moved to the position (an area's trigger then fires as when he walks in).
// census <frame> (test only): heap 4 cells in address order grouped by their "\0MAD" + file(line) tag (line
// dropped), the free cells from the OSAlloc descriptor (total, largest, count), and the untagged allocated rest.
static void warp_heap4_census(unsigned frame)
{
    struct Row { char tag[28]; unsigned bytes, count; } rows[48];
    unsigned n = 0, untagged = 0, untagged_cells = 0, freeb = 0, freen = 0, largest = 0;
    if (!memCheckHeapActive(4) || Heap[4].handle < 0) return;
    const OSHeapDescriptor* d = reinterpret_cast<const OSHeapDescriptor*>((u32(re4dc_mem.heap) + 0x1FU) & ~0x1FU) + Heap[4].handle;
    for (const OSHeapCell* f = d->free; f; f = f->next) {
        freeb += (unsigned) f->size; ++freen;
        if ((unsigned) f->size > largest) largest = (unsigned) f->size;
    }
    for (const OSHeapCell* c = d->allocated; c; c = c->next) {
        const int size = c->size;
        const unsigned char* t = reinterpret_cast<const unsigned char*>(c) + size - 0x20;
        if (size >= 0x40 && !t[0] && t[1] == 'M' && t[2] == 'A' && t[3] == 'D') {
            char tag[28];
            unsigned k = 0;
            const char* src = reinterpret_cast<const char*>(t + 4);
            while (k + 1 < sizeof(tag) && src[k] && src[k] != '(') { tag[k] = src[k]; ++k; }
            tag[k] = 0;
            unsigned r = 0;
            while (r < n && strcmp(rows[r].tag, tag)) ++r;
            if (r == n && n < 48) { memcpy(rows[n].tag, tag, sizeof(tag)); rows[n].bytes = 0; rows[n].count = 0; ++n; }
            if (r < n) { rows[r].bytes += (unsigned) size; ++rows[r].count; continue; }
        }
        untagged += (unsigned) size; ++untagged_cells;
    }
    for (unsigned i = 0; i < n; ++i)
        for (unsigned j = i + 1; j < n; ++j)
            if (rows[j].bytes > rows[i].bytes) { Row x = rows[i]; rows[i] = rows[j]; rows[j] = x; }
    re4dc_log("warp: census room %03x frame %u span=%u free=%u in %u cells largest=%u untagged=%u x%u tags=%u\n",
              (unsigned) pG->room_id, frame, (unsigned) (Heap[4].end - Heap[4].start), freeb, freen, largest, untagged,
              untagged_cells, n);
    for (unsigned i = 0; i < n; ++i) re4dc_log("warp: census %8u B x%-4u %s\n", rows[i].bytes, rows[i].count, rows[i].tag);
}

void goto_poll()
{
    for (unsigned i = 0; i < wp.n_go; ++i) {
        Warp::Goto& g = wp.go[i];
        if (g.done || g.entry != wp.rooms || wp.room_frames < g.frame || !pPL || (pG->Status_flg[1] & 0x10000000)) continue;
        g.done = true;
        Vec p = {g.pos[0], g.pos[1], g.pos[2]};
        pPL->setPos(&p);
        if (g.has_ang) {
            Vec a = {0.0f, g.ang, 0.0f};
            pPL->setAng(&a);
        }
        char what[64];
        snprintf(what, sizeof(what), "goto %u at room frame %u pl=%d,%d,%d", i, (unsigned) wp.room_frames, (int) p.x,
                 (int) p.y, (int) p.z);
        stamp(what);
        // padscript presses can wait for the move ("goto=<n>", n = goto index + 1; c13 door walks)
        re4dc_fixture_state("goto", int(i + 1), -1);
    }
}
// `god` / `alert` (benchmark fixtures, the hwcal disc's invuln / alert): every frame / once at the room frame.
void god_alert_poll()
{
    if (wp.god && pG) pG->pl_life = pG->pl_life_max;
    if (!wp.has_alert || wp.alert_done || wp.rooms != wp.alert_entry || wp.room_frames < wp.alert_frame || !pPL ||
        (pG->Status_flg[1] & 0x10000000)) return;
    wp.alert_done = true;
    pG->Status_flg[0] |= 0x00800000;
    pG->Status_flg[1] |= 0x20000000;
    pG->bell_pos = pPL->pos;
    pG->bell_stat = 0;
    char what[64];
    snprintf(what, sizeof(what), "alert at room frame %u (entry %u) pl=%d,%d,%d", (unsigned) wp.room_frames,
             (unsigned) wp.rooms, (int) pPL->pos.x, (int) pPL->pos.y, (int) pPL->pos.z);
    stamp(what);
}
#if RE4DC_WARP_JUMP
// `jump` (WARP_JUMP=1, diagnostic room change; not a source door/event route): in room `from`, at or after its
// room frame and outside events, the first pending entry changes room to `to` at the position through the
// source's own scenario room change (SceAtExecRoomJump: a door area made up and fired). Each entry fires once,
// so a list alternating two rooms leaves and re-enters each of them; after one fires, the next waits for the room
// entry it asked for (two pending entries from the same room fired on consecutive frames before, the second
// overriding the first's destination), re-issuing the fired one every 30 room frames (at most 4 times) if the room
// change was not taken. `from` == `to` re-enters the room.
void jump_poll()
{
    for (unsigned i = 0; i < wp.n_jump; ++i) {
        Warp::Jump& j = wp.jump[i];
        if (j.done) continue;
        if (wp.jump_wait) {
            // the room change was not taken (seen in r219 at room frame 600): re-issue the same entry every 30 room
            // frames, at most 4 times, until the room entry it asked for happens
            Warp::Jump& f = wp.jump[wp.jump_fired];
            if (wp.jump_retries >= 4 || wp.room_frames < wp.jump_frame + 30 || !pPL ||
                (pG->Status_flg[1] & 0x10000000)) return;
            ++wp.jump_retries;
            wp.jump_frame = wp.room_frames;
            Vec fp = {f.pos[0], f.pos[1], f.pos[2]};
            Vec fr = {0.0f, f.ang, 0.0f};
            char again[64];
            snprintf(again, sizeof(again), "jump %u retry %u at room frame %u", wp.jump_fired, wp.jump_retries,
                     (unsigned) wp.room_frames);
            stamp(again);
            SceAtExecRoomJump(f.to, &fp, &fr, 0);
            return;
        }
        if (pG->room_id != j.from) continue;
        if (wp.room_frames < j.frame || !pPL || (pG->Status_flg[1] & 0x10000000)) return;
        j.done = true;
        wp.jump_wait = true;
        wp.jump_fired = i;
        wp.jump_frame = wp.room_frames;
        wp.jump_retries = 0;
        Vec p = {j.pos[0], j.pos[1], j.pos[2]};
        Vec r = {0.0f, j.ang, 0.0f};
        char what[64];
        snprintf(what, sizeof(what), "jump %u %03x -> %03x at room frame %u", i, (unsigned) j.from, (unsigned) j.to,
                 (unsigned) wp.room_frames);
        stamp(what);
        SceAtExecRoomJump(j.to, &p, &r, 0);
        return;
    }
}
#endif
}  // namespace

extern "C" {

// title.cpp Title_task: 1 = skip the title screens and go to titleExit.
int re4dc_warp_title(void)
{
    if (!wp.loaded) load();
    if (wp.active && !wp.boot_us) {
        wp.boot_us = 1;
        stamp("title skipped");
    }
    return wp.active;
}

// title.cpp titleExit, before the debug start menu: the room to start in. 1 = warp (no menu).
int re4dc_warp_title_exit(void)
{
    if (!wp.active) return 0;
    pG->stage_no = (u8) (wp.room >> 8);
    pG->room_no = (u8) wp.room;
    pG->JumpPoint = (u8) wp.jp;
    return 1;
}

// title.cpp titleExit, after the jump point's setNextPos: the warp position.
void re4dc_warp_next_pos(void)
{
    if (!wp.active) return;
    if (wp.has_pos) {
        pG->NextPos.x = wp.pos[0];
        pG->NextPos.y = wp.pos[1];
        pG->NextPos.z = wp.pos[2];
    }
    if (wp.has_dir) pG->NextY = wp.dir;
    re4dc_log("warp: start room=%03x next_room=%03x pos=%d,%d,%d ang=%d/1000\n", (unsigned) wp.room,
              (unsigned) pG->next_room, (int) pG->NextPos.x, (int) pG->NextPos.y, (int) pG->NextPos.z,
              (int) (pG->NextY * 1000.0f));
}

// ui_bridge.cpp re4dc_room_enter (every room entry).
void re4dc_warp_room_enter(void)
{
    if (!wp.active) return;
    ++wp.rooms;
    wp.room_frames = 0;
#if RE4DC_WARP_JUMP
    wp.jump_wait = false;
#endif
    wp.pad_frames = 0;
    if (wp.max_entry > 1) {
        // A held action never carries over into the next room's clock.
        wp.cur_act = -1;
        wp.cur_until = 0;
    }
    char what[48];
    snprintf(what, sizeof(what), "room enter %03x (#%u)", (unsigned) pG->room_id, (unsigned) wp.rooms);
    stamp(what);
    if (wp.applied) return;
    wp.applied = true;
    for (unsigned i = 0; i < wp.n_rsf; ++i) {
        if (RoomData.getRoomSavePtr(wp.rsf[i].room)) RsfSet(wp.rsf[i].room, wp.rsf[i].bit);
    }
    pG->Scenario_flg[0] |= wp.scenario[0];
    pG->Scenario_flg[1] |= wp.scenario[1];
    pG->Item_find_flg |= wp.find;
    pG->door_unlock[0] |= wp.unlock[0];
    pG->door_unlock[1] |= wp.unlock[1];
    pG->item_flags[0] |= wp.items[0];
    pG->item_flags[1] |= wp.items[1];
    if (wp.items[0] | wp.items[1]) re4dc_log("warp: item_flags %08x/%08x\n", (unsigned) pG->item_flags[0], (unsigned) pG->item_flags[1]);
    for (unsigned i = 0; i < wp.n_dead; ++i) EmListSetAlive(wp.dead[i], 0);
    if (wp.n_dead) re4dc_log("warp: %u enemy-list entries set dead\n", wp.n_dead);
    re4dc_log("warp: flags applied rsf[%03x]=%08x scenario=%08x/%08x find=%08x unlock=%08x/%08x\n",
              (unsigned) pG->room_id,
              RoomData.getRoomSavePtr(pG->room_id) ? (unsigned) RsfFlags(pG->room_id)[0] : 0u,
              (unsigned) pG->Scenario_flg[0], (unsigned) pG->Scenario_flg[1], (unsigned) pG->Item_find_flg,
              (unsigned) pG->door_unlock[0], (unsigned) pG->door_unlock[1]);
}

// ui_bridge.cpp re4dc_room_cycle_poll (top of gameMainLoop, game thread).
void re4dc_warp_poll(void)
{
    if (!wp.active) return;
    if (wp.has_freeze && pG && (u32) pG->Frame_cnt >= wp.freeze_tick) {
        re4dc_log("warp: frozen at tick %u\n", (unsigned) pG->Frame_cnt);
        for (;;) thd_sleep(1000);
    }
    ++wp.room_frames;
    god_alert_poll();
    kill_poll();
#if RE4DC_WARP_JUMP
    jump_poll();
#endif
    if (wp.rooms != 1) {
        if (wp.rooms > wp.max_entry) return;
        // A scripted later room (`entry`): its moves, its placement and periodic positions.
        goto_poll();
        if ((wp.room_frames == 1 || (wp.room_frames % 300) == 0) && pPL) {
            re4dc_log("warp: entry %u frame %u room=%03x pl=%d,%d,%d ang=%d/1000 status1=%08x vbl=%u\n", (unsigned) wp.rooms,
                      (unsigned) wp.room_frames, (unsigned) pG->room_id, (int) pPL->pos.x, (int) pPL->pos.y, (int) pPL->pos.z,
                      (int) (pPL->ang.y * 1000.0f), (unsigned) pG->Status_flg[1], (unsigned) re4dc_vi_retrace_count());
        }
        return;
    }
    goto_poll();
    if (wp.has_radio && !wp.radio_done && wp.room_frames >= wp.radio_frame &&
        pG->Rno0 == 3 && pG->Rno1 == 0 && pPL && pPL->checkEvent() == 1 &&
        !(pG->Status_flg[1] & 0x10000000) && !SubScreenWk.type && !SceSys.event_start_cnt) {
        if (SceExec(0x12,(TaskFunc)radio_fixture,wp.radio_no,0,SCE_PRIO_DEF_2,0))wp.radio_done=true;
    }
    for (unsigned i = 0; i < wp.n_census; ++i) {
        if (!wp.census_done[i] && wp.room_frames >= wp.census[i]) {
            wp.census_done[i] = true;
            warp_heap4_census((unsigned) wp.room_frames);
        }
    }
#if defined(RE4DC_CHARBAKE_TOGGLE) && RE4DC_CHARBAKE_TOGGLE
    for (unsigned i = 0; i < wp.n_charbake_at; ++i) {
        Warp::CharbakeAt& c = wp.charbake_at[i];
        if (c.done || wp.room_frames < c.frame) continue;
        c.done = true;
        re4dc_log("warp: charbake %u at room frame %u\n", (unsigned) c.variant, (unsigned) wp.room_frames);
        re4dc_charbake_set(c.variant);
    }
#endif
#if defined(RE4DC_LOOK_TOGGLE)
    for (unsigned i = 0; i < wp.n_lookstep; ++i) {
        Warp::LookStep& s = wp.lookstep[i];
        if (s.done || wp.room_frames < s.frame) continue;
        s.done = true;
        re4dc_log("warp: lookstep at room frame %u\n", (unsigned) wp.room_frames);
        re4dc_look_cycle();
    }
#endif
    for (unsigned i = 0; i < wp.n_arm; ++i) {
        Warp::ArmItem& a = wp.arm[i];
        if (a.done || wp.room_frames < a.frame) continue;
        a.done = true;
        ItemMgr.debugWeapon(a.id);
        const int no = WeaponId2WeaponNo(a.id), type = WeaponId2WeaponType(a.id);
        re4dc_log("warp: arm item 0x%02x at room frame %u: weapon %u/%u -> %u/%u\n", (unsigned) a.id,
                  (unsigned) wp.room_frames, (unsigned) pG->weapon_no, (unsigned) pG->weapon_type, (unsigned) no,
                  (unsigned) type);
        if (pPL && pG->pl_type != 1 && (pG->weapon_no != no || pG->weapon_type != type)) {
            // SubScreenExit step 4 (sscrn.cpp), as when the weapon is equipped in the inventory and the case closes.
            SndBlkStop(2);
            pPL->weaponRelease();
            pPL->weaponLoad(no, type);
            pG->bullet_type = 0;
            pPL->weaponInit();
            re4dc_log("warp: arm item 0x%02x loaded: weapon %u/%u pWep=%08x\n", (unsigned) a.id, (unsigned) pG->weapon_no,
                      (unsigned) pG->weapon_type, (unsigned) (uintptr_t) pG->pWep);
        }
    }
    if (wp.room_frames == 1) {
        if (wp.has_area && pPL) {
            Vec c = {0.0f, 0.0f, 0.0f};
            if (SceAtPtr(wp.area_no)) {
                SceAtGetCenterPos(&c, wp.area_no);
                c.x += wp.area_dx;
                c.z += wp.area_dz;
                c.y = pPL->pos.y;
                pPL->setPos(&c);
            } else {
                re4dc_log("warp: area %02x not found\n", wp.area_no);
            }
        }
        if (pPL) {
            re4dc_log("warp: placed room=%03x pl=%d,%d,%d ang=%d/1000 vbl=%u wall_ms=%u\n", (unsigned) pG->room_id,
                      (int) pPL->pos.x, (int) pPL->pos.y, (int) pPL->pos.z, (int) (pPL->ang.y * 1000.0f),
                      (unsigned) re4dc_vi_retrace_count(), (unsigned) (timer_us_gettime64() / 1000));
        }
        re4dc_fixture_state("warp", 1, -1);
    }
    if (wp.dump && wp.room_frames == 2) dump_areas();
    if ((wp.room_frames % 300) == 0 && pPL) {
        re4dc_log("warp: frame %u room=%03x pl=%d,%d,%d status1=%08x rsf=%08x vbl=%u\n", (unsigned) wp.room_frames,
                  (unsigned) pG->room_id, (int) pPL->pos.x, (int) pPL->pos.y, (int) pPL->pos.z,
                  (unsigned) pG->Status_flg[1],
                  RoomData.getRoomSavePtr(pG->room_id) ? (unsigned) RsfFlags(pG->room_id)[0] : 0u,
                  (unsigned) re4dc_vi_retrace_count());
    }
}

// A route movie or an event started (movies pause PADRead): the running action ends there.
static void re4dc_warp_cut(const char* why)
{
    if (!wp.active || wp.rooms < 1 || wp.rooms > wp.max_entry || wp.pad_frames >= wp.cur_until) return;
    wp.cur_until = wp.pad_frames;
    char what[48];
    snprintf(what, sizeof(what), "act cut by %s", why);
    stamp(what);
}

// platform/pad.cpp PADRead, port A after the real / scripted bits: the scheduled warp actions.
void re4dc_warp_pad(unsigned short* buttons, signed char* stickY)
{
    if (!wp.loaded) load();
    if (!wp.active) return;
    const u32 vbl = re4dc_vi_retrace_count();
    const u32 gap = wp.last_pad_vbl ? vbl - wp.last_pad_vbl : 0;
    wp.last_pad_vbl = vbl;
    if (!wp.boot_us) {
        // Before the title skip only the boot screens run: the VMU_SAVE card screen ("create the
        // system file?") is answered Up (Yes) then A, repeated every second while it waits. No
        // padscript needed; on the other boot screens the pulses are harmless.
        const u32 t = wp.card_frames++ % 60;
        if (t == 10) stamp("card pulse: Up+A");
        if (t >= 10 && t < 13) *buttons |= 0x0008;
        if (t >= 30 && t < 33) *buttons |= 0x0100;
        return;
    }
    // A source-clock fixture holds for its requested pad ticks across rendering/IO stalls.
    // Source event/movie cuts below and at their existing call sites remain unchanged.
    if (!wp.act_source_clock && gap > 30) re4dc_warp_cut("hold");
    if (wp.rooms < 1 || wp.rooms > wp.max_entry) return;
    ++wp.pad_frames;
    // An event took the game (Status_flg[1] 0x10000000): the running action ends there, so a
    // held stick never walks Leon back into the trigger after the event (movies pause PADRead).
    if (pG->Status_flg[1] & 0x10000000) {
        re4dc_warp_cut("event");
        return;
    }
    if (wp.cur_act >= 0 && wp.cur_act < (int) wp.n_act && wp.pad_frames < wp.cur_until) {
        const Act& a = wp.act[wp.cur_act];
        *buttons |= a.buttons;
        if (a.stick) *stickY = a.stick;
        return;
    }
    while (wp.next_act < wp.n_act && wp.act[wp.next_act].entry < wp.rooms) ++wp.next_act;  // an earlier room's, unfired
    if (wp.next_act < wp.n_act && wp.act[wp.next_act].entry == wp.rooms && wp.pad_frames >= wp.act[wp.next_act].frame) {
        const Act& a = wp.act[wp.next_act];
        wp.cur_act = (int) wp.next_act++;
        wp.cur_until = wp.pad_frames + a.hold;
        char what[48];
        snprintf(what, sizeof(what), "act %u buttons=%04x stick=%d hold=%u", (unsigned) wp.cur_act,
                 (unsigned) a.buttons, (int) a.stick, (unsigned) a.hold);
        stamp(what);
        *buttons |= a.buttons;
        if (a.stick) *stickY = a.stick;
    }
}

// sce_com.cpp DebugTrg (DBG_WARP builds): 1 once for the armed trigger, else 0 (the retail stub).
int re4dc_warp_debug_trg(int no)
{
    if (!wp.active || !wp.has_trg || wp.trg_fired || no != wp.trg_no) return 0;
    if (wp.trg_room && pG->room_id != wp.trg_room) return 0;
    if (wp.room_frames < wp.trg_frame) return 0;
    wp.trg_fired = true;
    char what[48];
    snprintf(what, sizeof(what), "trg %d fired in %03x at room frame %u", no, (unsigned) pG->room_id,
             (unsigned) wp.room_frames);
    stamp(what);
    return 1;
}

// warp_late.h: the `late` mask from global tick late_tick (pG->Frame_cnt) in room late_room, else 0. The
// first open call logs once in every arm (mask 0 included), so the arms' logs stay alike.
unsigned re4dc_warp_late(void)
{
    if (!wp.has_late || !pG || pG->room_id != wp.late_room || pG->Frame_cnt < wp.late_tick) return 0;
    if (!wp.late_logged) {
        wp.late_logged = true;
        re4dc_log("warp: late 0x%02x open at t=%u room=%03x (1=world20px 2=actor8px 4=nodraw 8=cap 10=leon-source)\n",
                  (unsigned) wp.late_mask, (unsigned) pG->Frame_cnt, (unsigned) pG->room_id);
    }
    return wp.late_mask;
}

int re4dc_warp_late_set(void) { return wp.has_late ? 1 : 0; }

}  // extern "C"
#endif  // RE4DC_DBG_WARP
