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
//  - Observe: alivelog <period> without a room directive keeps the original title,
//    CardLoad and gameplay path. After native room entry it only reports alive
//    enemies/in-view counts; placement, flags, input and damage actions stay off.
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
//  - Move: `goto <room frame> x y z [ang] [sub]` (up to 8; `sub` moves Ashley beside him) moves Leon there at or after that
//    frame, outside events; an area trigger at the spot then fires as when he walks in (r100: area
//    6 pre-reads s03/s20, area 0xA starts s03), so a fresh room entry (its entry event and call)
//    reaches a later event without a scripted walk.
// A warp start is NOT STRICT against continued play (fresh room entry with synthesized flags; the
// RNG, timers and enemy state are those of a new game). It is for iteration and bring-up only.
//
// /cd/dc/warp.txt (tools/d367/warp.py writes it from a named preset):
//   room 0x100 | jp 0 | pos x y z | dir 0x8000 | ang <rad> | rsf <room> <bit>... |
//   scenario <0|1> <hex> | find <hex> | unlock <0|1> <hex> | status <0..3> <hex> | dead <no>... | inv default | area <no> [dx dz] |
//   act <frame> <a|b|x|y|start|fwd|back|none|0xMASK> <hold> | arm <frame> <item id> | trg <no> <frame> [room] | kill <id> <frame> [room [kind]] |
//   killnext <id> <frame> <room> <kind> <repeat> <gap> (WARP_KILL_PHASE=1 only): one next target after death/event.
//   killrep <count> <gap> | killpart <partsNo> (every kill hit on that hit box; 5 = the head, so the kill loses it) |
//   killnear (each kill target is the live enemy nearest Leon) | handpose <frame> <type> <id> (cEm10::setHand, both hands) |
//   bring <distance> [side] (the handpose / kill target moved that far in front of Leon, side to his right: still pairs) |
//   setem <room frame> <esl index> [chkDead, default 1] (once: the setEm(index, -1, 0, 1, 1) work, as r104_execEvent20 sets the merchant 0x5E; census and
//   still pairs of event-spawned characters without the event or its sub screen) |
//   goto <frame> x y z [ang] | dump | name <preset> | late <mask> [tick] [room] (warp_late.h) | entry <n> |
//   radio <frame> <call no 0..23> (source radio replay, resource-lifetime test only)
//   god (Leon's life refilled every frame) | alert <frame> (the crowd hunts Leon from that frame of its entry)
//   face <target|corpse> (still pairs: Leon, and so the camera behind him, turns every frame toward the `kill`
//   target (target: alive or dying; stump / blood stills) or toward the most recent kill still in the enemy list
//   (corpse: the death fade); with `freeze <tick>` the frame then holds the subject in view in both arms)
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
#include <math.h>
#if defined(RE4DC_VIEW_DIST_OPTION) && RE4DC_VIEW_DIST_OPTION
extern "C" void re4dc_view_dist_set(int level, const char* why);   // option_rows.cpp (Options View distance)
#endif
#if defined(RE4DC_FAR_SHELL) && RE4DC_FAR_SHELL
extern "C" void re4dc_far_shell_set(int mode, const char* why);   // native_static.cpp far_shell.inc
extern "C" s32 OSCheckHeap(int heap);
static u32 farshell_probe_frame;   // warp line farshellprobe (test only)
#endif
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
extern "C" volatile unsigned re4dc_qa_wopq_mm, re4dc_qa_wxlu_mm, re4dc_qa_wshell;   // native_static.cpp (WORLD_METER)
#endif
#if defined(RE4DC_WORLD_SCRATCH) && RE4DC_WORLD_SCRATCH
extern "C" volatile unsigned re4dc_world_scratch_live;   // world_scratch.cpp (live arm)
#endif
#if defined(RE4DC_FOLIAGE_OPTION) && RE4DC_FOLIAGE_OPTION
extern "C" unsigned re4dc_foliage;   // platform/native_static.cpp (FOLIAGE_TRIM level; the Options Foliage row)
#endif
#if defined(RE4DC_TRANS_POLICY)
extern "C" volatile unsigned re4dc_trans_policy;   // platform/native_static.cpp (TRANS_POLICY sub-switch mask)
extern "C" volatile unsigned re4dc_trans_far_pct;  // TRANS_POLICY FAR thresholds (low byte moved cards, next the rest)
#if defined(RE4DC_TRANS_POLICY_DEBUG) && RE4DC_TRANS_POLICY_DEBUG
extern "C" volatile unsigned re4dc_trans_debug;    // TRANS_POLICY_DEBUG silhouette arm
#endif
#endif
#include "global.h"
#include "player.h"
#include "room_data.h"
#include "flag_rsf.h"
#include "sce_at.h"
#include "area.h"
#include "em_set.h"
#include "em.h"
#include "em_sub.h"
#include "em10.h"
#include "model.h"
// cModel::swapModelInfo (main image), as src/em10/em10.cpp declares it: em10HandSet itself lives in the em10 overlay.
extern "C" void cModel_swapModelInfo(cModel* m, ModelData* old, cModelInfo* info) asm("swapModelInfo__6cModelP9ModelDataP10cModelInfo");
#include "item.h"
#include "main_mem.h"
#include "snd.h"
#include "sce.h"
#include "sce_sys.h"
#include "etc_model.h"
#include "emdoor.h"
#include "embox.h"
#include "sscrn.h"
#include "re4dc_platform.h"
#include "geometry.h"
#include "camera.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <arch/timer.h>
#include <kos/thread.h>
#include "read.h"   // EmReadSearch (setem: the enemy read-table entry)

#if defined(RE4DC_QA_MENU) && RE4DC_QA_MENU
extern volatile int vsync_cnt;   // main.cpp: presentation heartbeat, also used by the source hang detector
#endif

extern "C" {
u32 re4dc_vi_retrace_count(void);
#if defined(RE4DC_CAP_COMPARE)
// CAP_COMPARE=1 (Makefile; lane cap16 2026-10-16): the runtime alive cap, default the build's ALIVE_CAP; a `cap <N>` warp
// line sets it. em_set.cpp (RE4DC_ALIVE_CAP_N) and r101.cpp (RE4DC_R101_CAP_N) read it in place of the constant.
int re4dc_cap_rt = RE4DC_CAP_COMPARE;
#if defined(RE4DC_CAP_MISTCUT) && RE4DC_CAP_MISTCUT
extern unsigned re4dc_mist_cut;   // esp_sub.cpp (hwfog.mk MIST_CUT): the runtime mask of the translucency arms
#endif
#endif

int re4dc_fixture_read(const char* path, char* buffer, unsigned size);
void re4dc_fixture_state(const char* name, int a, int b);  // pad.cpp fixture anchors (overlay)
#if defined(RE4DC_QA_MENU) && RE4DC_QA_MENU
const char* re4dc_qa_boot_path(void);   // qa_menu.cpp (qamenu.mk QA_MENU)
int re4dc_qa_combo(void);
unsigned re4dc_qa_flags(void);
int re4dc_qa_menu(const char** path);
int re4dc_qa_menu_auto(const char* file, const char** path, unsigned hold_ms);
void re4dc_qa_game(unsigned room, int alive, int heap4, const char* preset);
void re4dc_qa_set_flags(unsigned f);
void re4dc_qa_in_room(int on);
#endif
#if defined(RE4DC_BENCHMARK) && RE4DC_BENCHMARK
void re4dc_bench_scene_def(int no, unsigned begin, unsigned end, const char* name);  // bench.cpp (bench.mk BENCHMARK)
int re4dc_bench_tick(unsigned room_frame);
const char* re4dc_bench_next_scene(void);
const char* re4dc_bench_first_scene(void);
void re4dc_bench_alive(int n);
int re4dc_bench_scene_no(void);
const char* re4dc_bench_results(void);
#if defined(RE4DC_BENCH_CENSUS) && RE4DC_BENCH_CENSUS
void re4dc_bench_fixture_begin(const char* path);
void re4dc_bench_census(unsigned esp_live, unsigned hits, unsigned rg_parts, unsigned rg_verts);
unsigned re4dc_bench_esp_live(void);                                  // esp.cpp (BENCH_CENSUS)
void re4dc_cache20_arm(int on) __attribute__((weak));               // platform/cache20.cpp
extern volatile unsigned re4dc_rigid_hide __attribute__((weak));     // native_actor_fast.cpp (RIGID_CENSUS=2)
extern unsigned re4dc_rigid_census[6] __attribute__((weak));
extern const void* re4dc_rigid_census_big __attribute__((weak));
#if defined(RE4DC_BENCH_MISTCUT) && RE4DC_BENCH_MISTCUT
extern unsigned re4dc_mist_cut;   // esp_sub.cpp (hwfog.mk MIST_CUT): effect classes not drawn (render only)
#endif
#endif
#endif
#if defined(RE4DC_ACTOR_PLAN) && RE4DC_ACTOR_PLAN
extern "C" unsigned re4dc_actor_plan_on;  // platform/native_actor_fast.cpp (actorplan.mk ACTOR_PLAN)
#endif
#if defined(RE4DC_PS2_PVS) && RE4DC_PS2_PVS
extern "C" void re4dc_ps2_pvs_set(unsigned on);  // native_static.cpp (t2exact.mk PS2_PVS)
#endif
#if defined(RE4DC_SG_SELECT_LEAN) && RE4DC_SG_SELECT_LEAN
extern "C" void re4dc_sg_select_lean_set(unsigned on);  // native_static.cpp (t2exact.mk SG_SELECT_LEAN)
#endif
#if defined(RE4DC_LEON_LIGHT_TOGGLE) && RE4DC_LEON_LIGHT_TOGGLE
extern "C" void re4dc_leon_light_set(unsigned mode);  // native_actor_fast.cpp (crowd.mk LEON_LIGHT_TOGGLE)
#endif
#if defined(RE4DC_GANADO_LIT_TOGGLE) && RE4DC_GANADO_LIT_TOGGLE
extern "C" void re4dc_ganlit_set(unsigned mode);  // native_actor_fast.cpp (crowd.mk GANADO_LIT_TOGGLE)
extern "C" void re4dc_ganlit_fill_set(unsigned percent);  // (the toggle build always compiles the fill)
#endif
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
#if defined(RE4DC_LEON_LOD) && RE4DC_LEON_LOD
extern "C" void re4dc_leon_lod_set(unsigned level);  // coarse_actor_leon_lod.inc (ps2leon.mk LEON_LOD)
#endif
#if defined(RE4DC_GANADO_LOD) && RE4DC_GANADO_LOD
extern "C" void re4dc_ganado_lod_set(unsigned level);  // coarse_ganado_lod.inc (ps2leon.mk GANADO_LOD)
#endif

namespace {
struct Act { u32 frame; u16 buttons; s8 stick; u16 hold; u8 entry; bool ev; s8 stickx; };
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
    u32 status[4];  // `status <0..3> <hex>`: pG->Status_flg bits (3: 0x04000000 Ashley follows, sce_sys.cpp)
    int chapter;    // `chapter <n>`: pG->chapter (chapters finished) before the first room loads, 0 = unset (+1 stored)
    u8 dead[64];
    unsigned n_dead;
    Act act[96];
    unsigned n_act;
    bool has_trg, trg_fired;
    int trg_no;
    bool has_atlog, atlog_done;  // `atlog <frame>` (lane backface22): the room's scenario areas, once
    unsigned atlog_frame;
    u32 trg_frame;
    u16 trg_room;  // 0: any room
#if defined(RE4DC_WARP_KILL_PHASE) && RE4DC_WARP_KILL_PHASE
    bool kill_next_pending;
    u32 kill_next_id, kill_next_frame, kill_next_room, kill_next_kind, kill_next_rep, kill_next_gap;
#endif
    bool has_kill, kill_done;
    int kill_id;
    u32 kill_frame, kill_hits;
    u16 kill_room;  // 0: any room
    u8 kill_kind;   // cDmgInfo kind of each hit (1: handgun)
    cEm* kill_em;   // the target once found (kept until its hp is gone)
    int kill_cur;   // its enemy id (`kill 0`: the nearest live Ganado, ids 0x10..0x20)
    u32 kill_watch; // after the kill: state lines left
    u32 away_from, away_to; f32 away_pos[3];
    u32 atf_frame; int atf_no; bool atf_done;     // `atfunc <frame> <area>` (test rigs)
    u32 etd_frame; int etd_no; u32 etd_or; bool etd_done;  // `etcdoor <frame> <no> <flag>` (test rigs)  // `emaway <from> <to> <x> <y> <z>` (test rigs)
    u32 kill_rep, kill_gap;  // `killrep <count> <gap>`: kill `count` more, each `gap` room frames after the last
    s16 kill_part;  // `killpart <partsNo>`: every hit on that hit box (5: the head; lane stump17 10-17)
    bool kill_near; // `killnear`: the target is the live enemy nearest Leon (still pairs: the corpse falls in view)
    // `handpose <room frame> <type> <em id>` (lane stump17 still pairs): once at that frame, the live enemy of that id
    // nearest Leon shows a hand pose. Type 1: cEm10::setHand on both hands (BIN 449 / 454), as the event code does.
    // Type 2: em10HandSet(em, 2)'s alert pose (right mot[8] = 450, left mot[11] = 453). Type 4: its left-handed form
    // (flag 0x01000000: right mot[6] = 448, left mot[13] = 455). em10HandSet is in the em10 overlay, so the rig swaps
    // the two infos the same way (ModInfoMgr.create + cModel::swapModelInfo) and leaves Hand_type alone: the routine's
    // own em10HandSet(em, 0) sees no change and keeps the pose (setHand does not touch Hand_type either).
    bool has_hand, hand_done;
    u32 box_frame, box_dist; bool has_box, box_done;  // `boxbreak <frame> [dist]` (lane purge-props24 still rig)
    bool has_setem, setem_done;
    u32 setem_frame;
    s16 setem_no;
    int setem_chkdead;
    u32 bring;  // `bring <distance> [side]` (still pairs): the handpose / kill target is moved this far in front of Leon
    s32 bring_side;  // (and `side` to his right), facing him
    u32 hand_frame;
    int hand_type, hand_id;
    u32 alive_period, alive_last;  // `alivelog <period>`
    bool has_drop;  // `drop <item id> [num]` (issue 23): the kill target drops this item instead of its own roll
    u16 drop_id;
    int drop_num;
    struct Goto { u32 frame; f32 pos[3]; f32 ang; bool has_ang, done, sub; u8 entry; } go[8];  // `sub`: Ashley too
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
    // lodat <room frame> <leon level|-> <ganado level|-> (up to 8; leonlod): a LEON_LOD / GANADO_LOD level change in the
    // first room, applied by the game at its next actor retirement (the poc101 sweep's mid-room path).
    struct LodAt { u32 frame; int leon, ganado; bool done; } lodat[8];
    unsigned n_lodat;
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
    int money;   // `money N`: adds N PTAS once, at the first room frame (shop fixtures)
    bool god, has_alert, alert_done, ammo;  // ammo: `ammo` keeps the equipped weapon loaded (shotfx20 rigs)
    // face <target|corpse>: 1 = the current kill target, 2 = the newest kill still listed (ring of the last 8 kills)
    u8 face_mode;
    u8 face_n;
    cEm* face_ring[8];
    u8 face_id[8];
    u32 alert_frame;
    // bell108 <room frame> [count] [gap] (test 16.1 cap 4 gate): r108's bell-shot handler, count times, gap frames apart
    u32 b108_frame, b108_n, b108_gap;
    u8 alert_entry;
    // freeze <tick>: the game thread stops at the top of that global tick (look checks: the last presented image
    // stays on screen, the same image in two arms whose logic is STRICT).
    bool has_freeze;
    u32 freeze_tick;
    // still <room frame> <ms> (up to 8; leonlod 2026-10-15): the game thread holds at the top of that frame of the first
    // room for <ms>
    // (the last presented image stays on screen for the harness's periodic framebuffer shots), then play goes on.
    u32 still_tick[8], still_ms[8];
    unsigned n_still, still_next;
#if defined(RE4DC_BENCH_CENSUS) && RE4DC_BENCH_CENSUS
    // BENCH_CENSUS (lane cache20, census bench disc), timed lines of the first room (room frames):
    //   rigid <frame> on|off       rigid model parts drawn / not drawn (RIGID_CENSUS=2, render only)
    //   fx <frame> on|off          every effect sprite + mist card drawn / not (MIST_CUT mask 239, render only)
    //   crowd <frame> <n> [dist]   n more live Ganados (nearest first) put in front of Leon, dist (default 450) ahead,
    //                              spread across the view, facing him (a census of n on screen; they then act as usual)
    //   tank <frame>               the brought Ganado nearest Leon becomes the tank: its hp is held at 30000 every tick
    //                              (hits, reactions, blood and gore still happen; it does not die), hits counted
    //   autofire <frame> <end> [period]  Leon aims (R) at the tank and fires (A) every period frames (default 30),
    //                              infinite ammo (Debug_flg[2] 0x00400000) while it runs
    struct CenAt { u32 frame; u8 kind; s32 a, b; bool done; } cen[24];
    unsigned n_cen;
    cEm* crowd_em[8];
    unsigned n_crowd;
    cEm* tank;
    u32 tank_hits, fire_from, fire_to, fire_period;
#endif
#if defined(RE4DC_WARP_AFTER_RESET) && RE4DC_WARP_AFTER_RESET
    // after_reset (WARP_AFTER_RESET=1, lane resetmem): the rig stays passive (title, card load, play) until the first
    // soft reset, then warps from the title shown after it (the s30 heap gate after load -> reset -> New Game).
    bool after_reset;
#endif
    // Observation only, when alivelog is present without any room directive.
    // Kept at the end so existing warp field offsets remain unchanged.
    bool observe_ready;
    u16 observe_room;
};
Warp wp;

#if defined(RE4DC_WARP_KILL_PHASE) && RE4DC_WARP_KILL_PHASE
static bool kill_phase_args_valid(u32 id, u32 frame, u32 room, u32 kind, u32 repeat, u32 gap)
{
    return id <= 0x5F && frame > 0 && frame <= 0x7FFFFFFF && room > 0 && room <= 0x3FF &&
           kind <= 0xFF && repeat <= 255 && gap > 0 && gap <= 60000;
}
#endif

u32 num(const char* s) { return (u32) strtoul(s, nullptr, 0); }

#if defined(RE4DC_BENCHMARK) && RE4DC_BENCHMARK
// BENCHMARK=1 (bench.mk, bench.cpp): the scene fixture to arm at the next soft reset, and the reset is pending.
const char* bench_next;
bool bench_pending;
void load(const char* path = nullptr)
#elif defined(RE4DC_QA_MENU) && RE4DC_QA_MENU
// QA_MENU (qamenu.mk): the teleport preset armed at the next soft reset, and the reset is pending.
const char* qa_next;
bool qa_pending;
unsigned qa_frames;     // free-play poll frames in the current room (the menu opens from 30 on)
bool qa_enemy_on;       // enemies invincible was on last frame (off again: hp back to hp_max)
// Harness lines (a fixture in dc/warp.txt; the QA disc has none): `qa_flags <mask>` sets the toggles, `qa_menu <free
// frame> <preset file | -> [hold ms]` opens the in-game menu at that free-play frame, with hold ms also shows the
// Diagnostics page and each QR page for that long (captures), then teleports to /cd/dc/qa/<file> (`-`: resumes):
// the menu -> soft reset -> preset chain without pad input.
unsigned qa_auto_frame, qa_auto_hold;
char qa_auto_file[24];
bool qa_auto_armed;
void load(const char* path = nullptr)
#else
void load()
#endif
{
    wp.loaded = true;
    wp.parse_entry = wp.max_entry = 1;
    static char text[4096];
#if defined(RE4DC_BENCHMARK) && RE4DC_BENCHMARK
    if (!path) path = re4dc_bench_first_scene();   // scene 1, or the start screen's single scene
#if defined(RE4DC_BENCH_CENSUS) && RE4DC_BENCH_CENSUS
    re4dc_bench_fixture_begin(path);
#if defined(RE4DC_BENCH_MISTCUT) && RE4DC_BENCH_MISTCUT
    re4dc_mist_cut = 0;   // every fixture starts with every effect drawn
#endif
    if (&re4dc_rigid_hide) re4dc_rigid_hide = 0;
#endif
    const int len = re4dc_fixture_read(path, text, sizeof(text) - 1);
    re4dc_log("warp: bench fixture %s (%d bytes)\n", path, len);
#elif defined(RE4DC_QA_MENU) && RE4DC_QA_MENU
    if (!path) path = re4dc_qa_boot_path();        // the boot menu's preset, else dc/warp.txt (harness discs)
    if (!path) path = "/cd/dc/warp.txt";
    const int len = re4dc_fixture_read(path, text, sizeof(text) - 1);
    re4dc_log("warp: qa fixture %s (%d bytes)\n", path, len);
#else
    const int len = re4dc_fixture_read("/cd/dc/warp.txt", text, sizeof(text) - 1);
#endif
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
        } else if (!strcmp(k, "chapter") && n >= 2) {
            wp.chapter = (int) num(tok[1]) + 1;  // DISC_SET disc check (game.cpp StageInit) reads pG->chapter
        } else if (!strcmp(k, "status") && n >= 3) {
            wp.status[num(tok[1]) & 3] |= num(tok[2]);
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
        } else if (!strcmp(k, "act") && n >= 4 && wp.n_act < 96) {
            Act& a = wp.act[wp.n_act++];
            a.entry = wp.parse_entry;
            a.frame = num(tok[1]);
            a.hold = (u16) num(tok[3]);
            a.buttons = 0;
            a.stick = 0;
            a.ev = n >= 5 && !strcmp(tok[4], "ev");  // `ev`: pressed during an event too (issue 23: answers a prompt)
            a.stickx = 0;
            // one input or several joined by '+' (leonlod 2026-10-15: "b+fwd" runs, "b+back" quick-turns,
            // "0x0020+left" aims and turns); left / right push the stick's X axis.
            char ib[48];
            strncpy(ib, tok[2], sizeof(ib) - 1); ib[sizeof(ib) - 1] = 0;
            for (char* b = ib; b && *b;) {
                char* nx = strchr(b, '+');
                if (nx) *nx++ = 0;
                if (!strcmp(b, "a")) a.buttons |= 0x0100;
                else if (!strcmp(b, "b")) a.buttons |= 0x0200;
                else if (!strcmp(b, "x")) a.buttons |= 0x0400;
                else if (!strcmp(b, "y")) a.buttons |= 0x0800;
                else if (!strcmp(b, "start")) a.buttons |= 0x1000;
                else if (!strcmp(b, "fwd")) a.stick = 80;
                else if (!strcmp(b, "back")) a.stick = -80;
                else if (!strcmp(b, "left")) a.stickx = -80;
                else if (!strcmp(b, "right")) a.stickx = 80;
                else if (b[0] == '0' && b[1] == 'x') a.buttons |= (u16) num(b);  // a raw mask (R 0x0020 + A: 0x0120)
                b = nx;
            }
        } else if (!strcmp(k, "census") && n >= 2 && wp.n_census < 6) {
            wp.census_done[wp.n_census] = false;
            wp.census[wp.n_census++] = num(tok[1]);
        } else if (!strcmp(k, "arm") && n >= 3 && wp.n_arm < 8) {
            Warp::ArmItem& a = wp.arm[wp.n_arm++];
            a.frame = num(tok[1]);
            a.id = (u16) num(tok[2]);
            a.done = false;
        } else if (!strcmp(k, "atlog") && n >= 2) {
            wp.has_atlog = true; wp.atlog_done = false; wp.atlog_frame = num(tok[1]);
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
#if defined(RE4DC_WARP_KILL_PHASE) && RE4DC_WARP_KILL_PHASE
        } else if (!strcmp(k, "killnext")) {
            // One later source-damage target; no direct HP, room flag or event edits.
            if (n != 7 || wp.kill_next_pending ||
                !kill_phase_args_valid(num(tok[1]), num(tok[2]), num(tok[3]), num(tok[4]), num(tok[5]), num(tok[6]))) {
                wp.kill_next_pending = false;
                re4dc_missing("warp killnext requires id frame room kind repeat gap (one phase)");
            } else {
                wp.kill_next_id = num(tok[1]); wp.kill_next_frame = num(tok[2]);
                wp.kill_next_room = num(tok[3]); wp.kill_next_kind = num(tok[4]);
                wp.kill_next_rep = num(tok[5]); wp.kill_next_gap = num(tok[6]);
                wp.kill_next_pending = true;
            }
#endif
        } else if (!strcmp(k, "alivelog") && n >= 2) {
            wp.alive_period = num(tok[1]);
            wp.alive_last = ~0u;
        } else if (!strcmp(k, "atfunc") && n >= 3) {
            // `atfunc <frame> <area>`: test rigs only: at that room frame run the area's room callback (the function
            // SceAtDataSet_exec set) as its own task, as if the player had triggered it (r203 key pickup wave)
            wp.atf_frame = num(tok[1]);
            wp.atf_no = (int) num(tok[2]);
            wp.atf_done = false;
        } else if (!strcmp(k, "etcdoor") && n >= 4) {
            // `etcdoor <frame> <no> <flag>`: test rigs only: at that room frame room door `no` (getRoomEtcDoor) is set
            // normal (unlocked) and `flag` is ORed into its flag word (r209 door 4 opened: 0x10000000)
            wp.etd_frame = num(tok[1]);
            wp.etd_no = (int) num(tok[2]);
            wp.etd_or = num(tok[3]);
            wp.etd_done = false;
        } else if (!strcmp(k, "emaway") && n >= 6) {
            // `emaway <from> <to> <x> <y> <z>`: test rigs only (castle cap-4 r208 crank): between those room frames
            // every live Ganado is moved to x,y,z each frame, so a long player action is not hit
            wp.away_from = num(tok[1]);
            wp.away_to = num(tok[2]);
            for (int i = 0; i < 3; ++i) wp.away_pos[i] = (f32) strtod(tok[3 + i], nullptr);
        } else if (!strcmp(k, "boxbreak") && n >= 2) {
            // `boxbreak <frame> [dist]`: at that room frame the intact breakable box / barrel (cEmBox, etc ids 01 02 11
            // 12 1e 1f 2d 2e 2f 3c) nearest Leon is broken where it stands (or put dist in front of him first) (emBoxSetBreak
            // kind 0: the shot break), so a still pair shows the break model and debris. Test rig only (DBG_WARP).
            wp.has_box = true;
            wp.box_frame = num(tok[1]);
            wp.box_dist = n >= 3 ? num(tok[2]) : 0;
        } else if (!strcmp(k, "handpose") && n >= 4) {
            wp.has_hand = true;
            wp.hand_frame = num(tok[1]);
            wp.hand_type = (int) num(tok[2]);
            wp.hand_id = (int) num(tok[3]);
        } else if (!strcmp(k, "setem") && n >= 3) {
            wp.has_setem = true;
            wp.setem_frame = num(tok[1]);
            wp.setem_no = (s16) num(tok[2]);
            wp.setem_chkdead = n >= 4 ? (int) num(tok[3]) : 1;
        } else if (!strcmp(k, "bring") && n >= 2) {
            wp.bring = num(tok[1]);
            wp.bring_side = n >= 3 ? (s32) strtol(tok[2], nullptr, 0) : 0;
        } else if (!strcmp(k, "killnear")) {
            wp.kill_near = true;
        } else if (!strcmp(k, "killpart") && n >= 2) {
            wp.kill_part = (s16) num(tok[1]);
        } else if (!strcmp(k, "killrep") && n >= 3) {
            wp.kill_rep = num(tok[1]);
            wp.kill_gap = num(tok[2]);
        } else if (!strcmp(k, "drop") && n >= 2) {
            wp.has_drop = true;
            wp.drop_id = (u16) num(tok[1]);
            wp.drop_num = n >= 3 ? (int) num(tok[2]) : 0;
        } else if (!strcmp(k, "goto") && n >= 5 && wp.n_go < 8) {
            Warp::Goto& g = wp.go[wp.n_go++];
            g.entry = wp.parse_entry;
            g.frame = num(tok[1]);
            for (int i = 0; i < 3; ++i) g.pos[i] = (f32) strtod(tok[2 + i], nullptr);
            // trailing `sub`: the partner (pSUB, Ashley) is moved beside Leon too, so a door she must follow through
            // (CheckDoorJumpWithAshley: within 5000 by route) works after a long move (chapter 2-2 / 2-3 door walks)
            g.sub = !strcmp(tok[n - 1], "sub");
            const int m = g.sub ? n - 1 : n;
            g.has_ang = m >= 6;
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
#if defined(RE4DC_GANADO_LIT_TOGGLE) && RE4DC_GANADO_LIT_TOGGLE
        } else if (!strcmp(k, "ganlit") && n >= 2) {
            re4dc_ganlit_set(num(tok[1]));   // GANADO_LIT_TOGGLE: the Ganado lighting mode at load (0..9)
        } else if (!strcmp(k, "ganfill") && n >= 2) {
            re4dc_ganlit_fill_set(num(tok[1]));   // GANADO_LIT_TOGGLE: the Ganado camera fill, percent (0..100)
#endif
        } else if (!strcmp(k, "dump")) {
            wp.dump = true;
        } else if (!strcmp(k, "face") && n >= 2) {
            wp.face_mode = !strcmp(tok[1], "corpse") ? 2 : !strcmp(tok[1], "near") ? 3 : 1;
            if (wp.face_mode == 3) wp.face_id[0] = (u8) (n >= 3 ? num(tok[2]) : 0x15);  // `face near <em id> [dist/100 mm]` (shotfx20 rigs)
            if (wp.face_mode == 3) wp.face_id[1] = (u8) (n >= 4 ? num(tok[3]) : 0);
            re4dc_log("warp: face %s\n", wp.face_mode == 2 ? "corpse" : "target");
        } else if (!strcmp(k, "money") && n >= 2) {
            wp.money = num(tok[1]);
        } else if (!strcmp(k, "ammo")) {
            wp.ammo = true;
        } else if (!strcmp(k, "god")) {
            wp.god = true;
            re4dc_log("warp: god (Leon's life refilled every frame)\n");
        } else if (!strcmp(k, "bell108") && n >= 2) {
            wp.b108_frame = num(tok[1]);
            wp.b108_n = n >= 3 ? num(tok[2]) : 1;
            wp.b108_gap = n >= 4 ? num(tok[3]) : 60;
        } else if (!strcmp(k, "alert") && n >= 2) {
            wp.has_alert = true;
            wp.alert_frame = num(tok[1]);
            wp.alert_entry = wp.parse_entry;
#if defined(RE4DC_LOOK_TOGGLE)
        } else if (!strcmp(k, "look") && n >= 2) {
            re4dc_look_set(num(tok[1]));   // post30.mk LOOK_TOGGLE: the look preset at load (gallery columns)
#if defined(RE4DC_LEON_LIGHT_TOGGLE) && RE4DC_LEON_LIGHT_TOGGLE
        } else if (!strcmp(k, "leonlight") && n >= 2) {
            re4dc_leon_light_set(num(tok[1]));   // LEON_LIGHT_TOGGLE: the Leon lighting mode at load (0..3)
#endif
        } else if (!strcmp(k, "lookosd")) {
            re4dc_look_osd_toggle();       // LOOK_TOGGLE: the on-screen preset label always shown (label checks)
        } else if (!strcmp(k, "lookstep") && n >= 2 && wp.n_lookstep < 16) {
            wp.lookstep[wp.n_lookstep++] = {num(tok[1]), false};   // LOOK_TOGGLE: next preset at a room frame
#endif
        } else if (!strcmp(k, "lodat") && n >= 4 && wp.n_lodat < 8) {
            wp.lodat[wp.n_lodat++] = {num(tok[1]), tok[2][0] == '-' ? -1 : (int) num(tok[2]),
                                      tok[3][0] == '-' ? -1 : (int) num(tok[3]), false};
        } else if (!strcmp(k, "still") && n >= 3 && wp.n_still < 8) {
            wp.still_tick[wp.n_still] = num(tok[1]);
            wp.still_ms[wp.n_still++] = num(tok[2]);
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
#if defined(RE4DC_WARP_AFTER_RESET) && RE4DC_WARP_AFTER_RESET
        } else if (!strcmp(k, "after_reset")) {
            wp.after_reset = true;
#endif
#if defined(RE4DC_LEON_LOD) && RE4DC_LEON_LOD
        } else if (!strcmp(k, "leonlod") && n >= 2) {
            // ps2leon.mk LEON_LOD: Leon's mesh level (package order), applied at the next room enter / first draw
            re4dc_leon_lod_set(num(tok[1]));
            re4dc_log("warp: leonlod %u\n", num(tok[1]));
#endif
#if defined(RE4DC_GANADO_LOD) && RE4DC_GANADO_LOD
        } else if (!strcmp(k, "glod") && n >= 2) {
            // ps2leon.mk GANADO_LOD: the cast Ganados' mesh level (package order), applied at the first draw / next retire
            re4dc_ganado_lod_set(num(tok[1]));
            re4dc_log("warp: glod %u\n", num(tok[1]));
#endif
#if defined(RE4DC_KOS_SQUEEZE) && RE4DC_KOS_SQUEEZE
        } else if (!strcmp(k, "squeeze")) {
            // KOS_SQUEEZE (platform/os.cpp reads this line at OSInit)
#endif
#if defined(RE4DC_ACTOR_PLAN) && RE4DC_ACTOR_PLAN
        } else if (!strcmp(k, "actorplan") && n >= 2) {
            // ACTOR_PLAN (actorplan.mk): `actorplan 0|1` turns the plan's reuses off / on at run time (same image).
            re4dc_actor_plan_on = num(tok[1]) != 0;
            re4dc_log("warp: actorplan %u\n", re4dc_actor_plan_on);
#endif
#if defined(RE4DC_PS2_PVS) && RE4DC_PS2_PVS
        } else if (!strcmp(k, "pvs") && n >= 2) {
            // PS2_PVS (t2exact.mk): `pvs 0|1` switches the occlusion set off / on at run time (same image)
            re4dc_ps2_pvs_set(num(tok[1]));
            re4dc_log("warp: pvs %u\n", (unsigned) num(tok[1]));
#endif
#if defined(RE4DC_SG_SELECT_LEAN) && RE4DC_SG_SELECT_LEAN
        } else if (!strcmp(k, "sglean") && n >= 2) {
            // SG_SELECT_LEAN (t2exact.mk): `sglean 0|1` original / lean strip-group tests at run time (same image)
            re4dc_sg_select_lean_set(num(tok[1]));
            re4dc_log("warp: sglean %u\n", (unsigned) num(tok[1]));
#endif
#if defined(RE4DC_VIEW_DIST_OPTION) && RE4DC_VIEW_DIST_OPTION
        } else if (!strcmp(k, "viewdist") && n >= 2) {
            // VIEW_DIST_OPTION (option_rows.cpp): the Options View distance at load, 0 full / 1 near / 2 short (render
            // only; stills and the forced-Short STRICT arm without a menu walk)
            re4dc_view_dist_set((int) num(tok[1]), "warp");
#endif
#if defined(RE4DC_FAR_SHELL) && RE4DC_FAR_SHELL
        } else if (!strcmp(k, "farshell") && n >= 2) {
            // FAR_SHELL (far_shell.inc): 0 the View distance cut as before, 1 the far shell, 2 opaque cut only (pricing)
            re4dc_far_shell_set((int) num(tok[1]), "warp");
        } else if (!strcmp(k, "farshellprobe") && n >= 2) {
            // `farshellprobe <room frame>` (test only): at that frame of the first room, one heap-4 request of all the free
            // bytes (it cannot fit: cell headers), so the shell's shortfall path runs; the block is freed if it fit.
            farshell_probe_frame = (u32) num(tok[1]);
#endif
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
        } else if (!strcmp(k, "wmeter") && n >= 4) {
            // WORLD_METER: `wmeter <opaque cut mm> <translucent far mm, 1 = full> <shell 0 game, 1 on, 2 off>`, 0 = game's
            re4dc_qa_wopq_mm = (unsigned) num(tok[1]); re4dc_qa_wxlu_mm = (unsigned) num(tok[2]);
            re4dc_qa_wshell = (unsigned) num(tok[3]);
            re4dc_log("warp: wmeter opq=%u xlu=%u shell=%u\n", re4dc_qa_wopq_mm, re4dc_qa_wxlu_mm, re4dc_qa_wshell);
#endif
#if defined(RE4DC_WORLD_SCRATCH) && RE4DC_WORLD_SCRATCH
        } else if (!strcmp(k, "wscratch") && n >= 2) {
            // WORLD_SCRATCH: `wscratch <arm>` the live arm from boot, 0 A normal / 1 B half cache / 2 C scratch
            re4dc_world_scratch_live = (unsigned) num(tok[1]) % 3;
            re4dc_log("warp: wscratch arm=%u\n", re4dc_world_scratch_live);
#endif
#if defined(RE4DC_FOLIAGE_OPTION) && RE4DC_FOLIAGE_OPTION
        } else if (!strcmp(k, "foliage") && n >= 2) {
            // FOLIAGE_OPTION: the Options Foliage level at load, 0 full / 1 near / 2 off (render only; stills)
            re4dc_foliage = (unsigned) num(tok[1]) > 2U ? 0U : (unsigned) num(tok[1]);
            re4dc_log("warp: foliage %u\n", re4dc_foliage);
#endif
#if defined(RE4DC_TRANS_POLICY)
        } else if (!strcmp(k, "trans") && n >= 2) {
            // TRANS_POLICY (hwfog.mk): the runtime sub-switch mask at load (render only; still pairs, tr_pixdiff arms)
            re4dc_trans_policy = (unsigned) num(tok[1]) & 0xffU;
            re4dc_log("warp: trans %u\n", re4dc_trans_policy);
        } else if (!strcmp(k, "transfar") && n >= 3) {
            // TRANS_POLICY FAR thresholds (percent fog): moved cards, everything else in passes 1-2
            re4dc_trans_far_pct = ((unsigned) num(tok[1]) & 0xffU) | (((unsigned) num(tok[2]) & 0xffU) << 8);
            re4dc_log("warp: transfar %u %u\n", re4dc_trans_far_pct & 0xffU, re4dc_trans_far_pct >> 8);
#if defined(RE4DC_TRANS_POLICY_DEBUG) && RE4DC_TRANS_POLICY_DEBUG
        } else if (!strcmp(k, "transdbg") && n >= 2) {
            re4dc_trans_debug = (unsigned) num(tok[1]);   // class mask not drawn (1 = FLAT): silhouette arm (tr_pixdiff --mask-diff)
            re4dc_log("warp: transdbg %u\n", re4dc_trans_debug);
#endif
#endif
#if defined(RE4DC_CAP_COMPARE)
        } else if (!strcmp(k, "cap") && n >= 2) {
            // CAP_COMPARE (lane cap16, stress / test builds only): `cap <N>` = at most N Ganados alive at once, read by the
            // r101 cap (R101_ALIVE_CAP code) and the generic ALIVE_CAP hold from the next room entry on
            re4dc_cap_rt = (int) num(tok[1]);
            re4dc_log("warp: cap %d (CAP_COMPARE runtime alive cap)\n", re4dc_cap_rt);
#if defined(RE4DC_CAP_MISTCUT) && RE4DC_CAP_MISTCUT
        } else if (!strcmp(k, "mistcut") && n >= 2) {
            // CAP_COMPARE + MIST_CUT: `mistcut <mask>` = the translucent draws left out (docs/MIST_CUT.md: 16 the world's
            // translucent pass, 237 every effect sprite class, 255 both; 0 as shipped). Draw-time only.
            re4dc_mist_cut = num(tok[1]);
            re4dc_log("warp: mistcut %u (CAP_COMPARE translucency arm)\n", re4dc_mist_cut);
#endif
#endif
#if defined(RE4DC_QA_MENU) && RE4DC_QA_MENU
        } else if (!strcmp(k, "qa_flags") && n >= 2) {
            re4dc_qa_set_flags(num(tok[1]));
            re4dc_log("warp: qa_flags %x\n", (unsigned) num(tok[1]));
        } else if (!strcmp(k, "qa_menu") && n >= 3) {
            qa_auto_frame = num(tok[1]);
            strncpy(qa_auto_file, strcmp(tok[2], "-") ? tok[2] : "", sizeof(qa_auto_file) - 1);
            qa_auto_file[sizeof(qa_auto_file) - 1] = 0;
            qa_auto_hold = n >= 4 ? num(tok[3]) : 0;
            qa_auto_armed = true;
            re4dc_log("warp: qa_menu at free frame %u -> %s\n", qa_auto_frame, qa_auto_file);
#endif
#if defined(RE4DC_BENCHMARK) && RE4DC_BENCHMARK
#if defined(RE4DC_BENCH_CENSUS) && RE4DC_BENCH_CENSUS
        } else if ((!strcmp(k, "rigid") || !strcmp(k, "fx")) && n >= 3 && wp.n_cen < 24) {
            wp.cen[wp.n_cen++] = {num(tok[1]), (u8) (k[0] == 'r' ? 1 : 2), !strcmp(tok[2], "off") ? 1 : 0, 0, false};
        } else if (!strcmp(k, "crowd") && n >= 3 && wp.n_cen < 24) {
            wp.cen[wp.n_cen++] = {num(tok[1]), 3, (s32) num(tok[2]), n >= 4 ? (s32) num(tok[3]) : 450, false};
        } else if (!strcmp(k, "objdump") && n >= 2 && wp.n_cen < 24) {
            wp.cen[wp.n_cen++] = {num(tok[1]), 5, 0, 0, false};
        } else if (!strcmp(k, "tank") && n >= 2 && wp.n_cen < 24) {
            wp.cen[wp.n_cen++] = {num(tok[1]), 4, 0, 0, false};
        } else if (!strcmp(k, "cachearm") && n >= 2) {
            // test runs only (Flycast smoke of arm B without the start screen): the cache20 arm, 0 = A, 1 = B
            if (re4dc_cache20_arm) re4dc_cache20_arm((int) num(tok[1]));
        } else if (!strcmp(k, "autofire") && n >= 3) {
            wp.fire_from = num(tok[1]);
            wp.fire_to = num(tok[2]);
            wp.fire_period = n >= 4 ? num(tok[3]) : 30;
            if (wp.fire_period < 8) wp.fire_period = 8;
#endif
        } else if (!strcmp(k, "bench") && n >= 5) {
            // BENCHMARK: `bench <scene no> <begin room frame> <end room frame> <name...>` (bench.cpp measures [begin, end))
            char name[24] = "";
            for (int i = 4; i < n; ++i) {
                if (i > 4) strncat(name, " ", sizeof(name) - strlen(name) - 1);
                strncat(name, tok[i], sizeof(name) - strlen(name) - 1);
            }
            re4dc_bench_scene_def((int) num(tok[1]), num(tok[2]), num(tok[3]), name);
#endif
        } else {
            re4dc_log("warp: unknown line '%s'\n", k);
        }
    }
#if defined(RE4DC_WARP_AFTER_RESET) && RE4DC_WARP_AFTER_RESET
    if (wp.after_reset && wp.active) {
        wp.active = false;
        re4dc_log("warp: after_reset: passive until the first soft reset\n");
    }
#endif
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
#if defined(RE4DC_WARP_KILL_PHASE) && RE4DC_WARP_KILL_PHASE
static void kill_phase_poll()
{
    if (!wp.kill_next_pending || !wp.has_kill || !wp.kill_done || !pG ||
        pG->room_id != wp.kill_next_room || wp.room_frames < wp.kill_next_frame ||
        (pG->Status_flg[1] & 0x10000000) || SceSys.event_start_cnt) return;
    wp.kill_next_pending = false;
    wp.kill_id = (int) wp.kill_next_id;
    wp.kill_frame = wp.kill_next_frame;
    wp.kill_room = (u16) wp.kill_next_room;
    wp.kill_kind = (u8) wp.kill_next_kind;
    wp.kill_rep = wp.kill_next_rep;
    wp.kill_gap = wp.kill_next_gap;
    wp.kill_done = false;
    wp.kill_em = nullptr;
    wp.kill_hits = wp.kill_watch = 0;
    wp.kill_part = 0;
    wp.kill_near = false;
    re4dc_log("warp: killnext 0x%02x activated in %03x at room frame %u after original death/event\n",
              (unsigned) wp.kill_id, (unsigned) pG->room_id, (unsigned) wp.room_frames);
}
#endif

// With no room directive the title/card-load path remains untouched. Only the
// existing alive/frustum report is requested; none of the warp actions can run.
bool native_alive_observe_enabled()
{
    return !wp.active && !wp.room && wp.alive_period;
}

void native_alive_room_enter()
{
    if (!native_alive_observe_enabled() || !pG) return;
    wp.observe_ready = true;
    wp.observe_room = pG->room_id;
    wp.room_frames = 0;
    wp.alive_last = ~0u;
    re4dc_log("warp: observe room enter %03x (native load, no room override)\n", (unsigned) pG->room_id);
}

void alive_log_poll()
{
    if (wp.alive_period && (wp.room_frames % wp.alive_period) == 0 && wp.room_frames != wp.alive_last) {
        // `alivelog <period>`: Ganados alive (the rooms' own count, ids 0x10..0x20) every period room frames
        wp.alive_last = wp.room_frames;
        re4dc_log("warp: alive %d room %03x frame %u\n", SceCountEmAlive(0x10, 0x20), (unsigned) pG->room_id,
                  (unsigned) wp.room_frames);
        // NOT-DRAWN gate (release lane rel17b, 10-18; warp builds only): every enemy id alive in logic (SceCheckEmAlive,
        // as SceCountEmAlive counts), as id x count @ nearest distance to Leon. tools/d367/cast_gc.py --not-drawn
        // fails a room where an id is alive here but has no NMRS census draw row (Krauser r31c, 10-18).
        // fix18 (10-18): "/vN" = how many of them are inside the camera's view frustum (body sphere y+900 r1200, as
        // act_cap.cpp inView without its margin; a read of the frustum, no logic state). cast_gc.py judges only ids
        // seen in view, so out-of-view enemies held for a script need no allowlist row (replaces the 12 m rule).
        unsigned char cnt[256] = {};
        unsigned char vis[256] = {};
        int nearest[256];
        GeoHexahedron* fr = (GeoHexahedron*) CameraViewFrustumPtr(&pG->Cam);
        for (u32 i = 0; i < EmMgr.nArray; i++) {
            cEm* em = (cEm*) EmMgr.workAt(i);
            if (!em || SceCheckEmAlive(em) != 1) continue;
            const unsigned id = (unsigned) em->id & 0xff;
            int d = -1;
            if (pPL) {
                const float dx = em->pos.x - pPL->pos.x, dz = em->pos.z - pPL->pos.z;
                d = (int) sqrtf(dx * dx + dz * dz);
            }
            if (!cnt[id] || (d >= 0 && d < nearest[id])) nearest[id] = d;
            if (cnt[id] < 255) ++cnt[id];
            GeoSphere s;
            s.pos.x = em->pos.x;
            s.pos.y = em->pos.y + 900.0f;
            s.pos.z = em->pos.z;
            s.r = 1200.0f;
            if (fr && collision_sphere_hexahedron(&s, fr) && vis[id] < 255) ++vis[id];
        }
        char line[256];
        int len = 0;
        for (unsigned id = 0; id < 256 && len < (int) sizeof(line) - 28; ++id)
            if (cnt[id])
                len += snprintf(line + len, sizeof(line) - len, " %02x*%u@%d/v%u", id, (unsigned) cnt[id], nearest[id],
                                (unsigned) vis[id]);
        line[len] = 0;
        re4dc_log("warp: alivelist room %03x frame %u ids%s\n", (unsigned) pG->room_id, (unsigned) wp.room_frames, line);
    }
}

void native_alive_poll()
{
    // Never inspect EmMgr while the title, load, room jump or teardown owns it.
    // A new room must reach the normal entry hook before it can be observed.
    if (!native_alive_observe_enabled() || !wp.observe_ready || !pG || !pPL ||
        pG->room_id != wp.observe_room || pG->Rno0 != 3 || pG->Rno1 != 0) return;
    ++wp.room_frames;
    alive_log_poll();
}

void kill_poll()
{
#if defined(RE4DC_WARP_KILL_PHASE) && RE4DC_WARP_KILL_PHASE
    kill_phase_poll();
#endif
#if defined(RE4DC_FAR_SHELL) && RE4DC_FAR_SHELL
    if (farshell_probe_frame && wp.rooms == 1 && wp.room_frames >= farshell_probe_frame) {
        farshell_probe_frame = 0;
        const s32 free_bytes = memCheckHeapActive(4) ? OSCheckHeap(Heap[4].handle) : -1;
        void* p = free_bytes > 0 ? mem_alloc((u32) free_bytes, "warp farshellprobe", 0, 0, 4) : nullptr;
        re4dc_log("warp: farshellprobe room frame %u heap4 free=%d request %s, free after=%d\n", (unsigned) wp.room_frames,
                  (int) free_bytes, p ? "fit" : "short", memCheckHeapActive(4) ? (int) OSCheckHeap(Heap[4].handle) : -1);
        if (p) Mem_free_h(p, 4);
    }
#endif
    alive_log_poll();
    if (wp.kill_watch && wp.kill_em && (wp.room_frames % 15) == 0) {
        --wp.kill_watch;
        cEm* em = wp.kill_em;
        bool live = false;  // still in the enemy manager's list (else the object may be gone / reused)
        for (cEm* e = EmMgr.getEmPtr(wp.kill_cur, 0); e; e = EmMgr.getEmPtr(wp.kill_cur, e)) live |= e == em;
        re4dc_log("warp: kill watch frame %u t=%u m=%08x listed=%d be_flag=%08x hp=%d r=%u/%u/%u pos=%d,%d,%d color=%08x\n",
                  (unsigned) wp.room_frames, (unsigned) pG->Frame_cnt, (unsigned) (uintptr_t) em, (int) live,
                  live ? (unsigned) em->be_flag : 0u, live ? (int) em->hp : 0, live ? (unsigned) em->r_no_0 : 0u,
                  live ? (unsigned) em->r_no_1 : 0u, live ? (unsigned) em->r_no_2 : 0u, live ? (int) em->pos.x : 0,
                  live ? (int) em->pos.y : 0, live ? (int) em->pos.z : 0,
                  live && em->pModelInfo ? (unsigned) em->pModelInfo->colorWord : 0u);
    }
    if (wp.away_to && pPL && wp.room_frames >= wp.away_from && wp.room_frames < wp.away_to) {
        for (int id = 0x10; id <= 0x20; ++id) {
            for (cEm* e = EmMgr.getEmPtr(id, 0); e; e = EmMgr.getEmPtr(id, e)) {
                if ((e->be_flag & 0x21) != 0x21 || e->hp <= 0) continue;
                Vec p = {wp.away_pos[0], wp.away_pos[1], wp.away_pos[2]};
                e->setPos(&p);
            }
        }
    }
    if (wp.atf_frame && !wp.atf_done && wp.room_frames >= wp.atf_frame) {
        wp.atf_done = true;
        SceAtWork* w = SceAtPtr(wp.atf_no);
        re4dc_log("warp: atfunc area %02x func=%08x at room frame %u\n", (unsigned) wp.atf_no,
                  w ? (unsigned) (uintptr_t) w->func : 0u, (unsigned) wp.room_frames);
        if (w && w->func) SceExec(0x12, w->func, w->arg, 0, SCE_PRIO_DEF_2, 0);
    }
    if (wp.etd_frame && !wp.etd_done && wp.room_frames >= wp.etd_frame) {
        wp.etd_done = true;
        cEm* d = nullptr;
        if (getRoomEtcDoor(wp.etd_no, &d, 1) == 1 && d) {
            ((cEmDoor*) d)->setNormal();
            d->flag |= wp.etd_or;
        }
        re4dc_log("warp: etcdoor %d %s flag|=%08x at room frame %u\n", wp.etd_no, d ? "set" : "missing",
                  (unsigned) wp.etd_or, (unsigned) wp.room_frames);
    }
    if (wp.has_box && !wp.box_done && wp.room_frames >= wp.box_frame && pPL) {
        static const u8 box_ids[] = {0x01, 0x02, 0x11, 0x12, 0x1E, 0x1F, 0x2D, 0x2E, 0x2F, 0x3C};
        cEm* best = nullptr;
        f32 best_d = 1e30f;
        for (int no = 0; no < 0x40; ++no) {
            for (unsigned k2 = 0; k2 < sizeof(box_ids); ++k2) {
                cEm* e = nullptr;
                if (getRoomEtc(no, box_ids[k2], &e, 0) != 1 || !e || e->hp <= 0) continue;
                const f32 dx = e->pos.x - pPL->pos.x, dz = e->pos.z - pPL->pos.z, d = dx * dx + dz * dz;
                if (d < best_d) { best_d = d; best = e; }
            }
        }
        wp.box_done = true;
        if (best) {
            if (wp.box_dist) {  // dist 0: break it where it stands
                const f32 a = pPL->ang.y, d = (f32) wp.box_dist;
                best->pos.x = pPL->pos.x + __builtin_sinf(a) * d;
                best->pos.z = pPL->pos.z + __builtin_cosf(a) * d;
                best->pos.y = pPL->pos.y;
            }
            emBoxSetBreak(static_cast<cEmBox*>(best), 0);
            re4dc_log("warp: boxbreak m=%08x at room frame %u pos=%d,%d,%d\n", (unsigned) (uintptr_t) best,
                      (unsigned) wp.room_frames, (int) best->pos.x, (int) best->pos.y, (int) best->pos.z);
        } else {
            re4dc_log("warp: boxbreak: no intact box in the room\n");
        }
    }
    if (wp.has_setem && !wp.setem_done && wp.room_frames >= wp.setem_frame && pPL) {
        wp.setem_done = true;
        // setEm lives in the stage modules only (gen_modules.py), so its body (st/em_wrap.cpp cEmWrap::setEm) runs here
        // on the image's em_set functions: an entry already set is fetched, else created, then marked alive.
        const int listok = checkListId(wp.setem_no);
        void* const rd = EmReadSearch(EM_LIST(wp.setem_no)->id, nullptr, 0);   // the read-table entry cEmMgr::construct needs
        cEm* e = GetEmPtrFromList(wp.setem_no);
        if (!e) {
            e = EmSetFromList2(wp.setem_no, wp.setem_chkdead);
            if (e == errEm) e = nullptr;
        }
        if (e) EmListSetAlive(wp.setem_no, 1);
        if (e) re4dc_log("warp: setem pos=%d,%d,%d\n", (int) e->pos.x, (int) e->pos.y, (int) e->pos.z);
        if (!e) {   // which room entries hold the alive cap's slots (a `dead` line can leave them out for a still)
            for (int i = 0; i < 0x100; ++i) {
                const EmListData* q = EM_LIST(i);
                if (q->id && q->room == EM_LIST(wp.setem_no)->room && i != wp.setem_no)
                    re4dc_log("warp: setem room entry 0x%02x id=%02x be_flag=%02x\n", i, (unsigned) q->id, (unsigned) q->be_flag);
            }
        }
        re4dc_log("warp: setem 0x%x -> m=%08x at room frame %u list=%d id=%02x type=%d room=%04x be_flag=%02x listok=%d nArray=%u read=%08x dbg2=%08x stage=%d room_no=%d\n", (unsigned) wp.setem_no,
                  (unsigned) (uintptr_t) e, (unsigned) wp.room_frames, (int) pG->em_list_no, (unsigned) EM_LIST(wp.setem_no)->id,
                  (int) EM_LIST(wp.setem_no)->type, (unsigned) EM_LIST(wp.setem_no)->room,
                  (unsigned) EM_LIST(wp.setem_no)->be_flag, listok, (unsigned) EmMgr.nArray,
                  (unsigned) (uintptr_t) rd, (unsigned) pG->Debug_flg[2], (int) pG->stage_no, (int) pG->room_no);
    }
    if (wp.has_hand && !wp.hand_done && wp.room_frames >= wp.hand_frame && pPL) {
        auto bring = [](cEm* e) {
            if (!wp.bring || !pPL) return;
            const f32 a = pPL->ang.y, d = (f32) wp.bring;
            e->pos.x = pPL->pos.x + __builtin_sinf(a) * d - __builtin_cosf(a) * (f32) wp.bring_side;
            e->pos.z = pPL->pos.z + __builtin_cosf(a) * d + __builtin_sinf(a) * (f32) wp.bring_side;
            e->ang.y = a + 3.14159265f;
        };
        cEm* best = nullptr;
        f32 best_d = 1e30f;
        for (cEm* e = EmMgr.getEmPtr(wp.hand_id, 0); e; e = EmMgr.getEmPtr(wp.hand_id, e)) {
            if ((e->be_flag & 0x21) != 0x21 || e->hp <= 0) continue;
            const f32 dx = e->pos.x - pPL->pos.x, dz = e->pos.z - pPL->pos.z, d = dx * dx + dz * dz;
            if (d < best_d) { best_d = d; best = e; }
        }
        if (best) {
            wp.hand_done = true;
            bring(best);
            if (wp.hand_type == 2 || wp.hand_type == 4) {
                cEm10* em = static_cast<cEm10*>(best);
                Em10Work* w = EM10_WK(em);
                void* bins[2] = {wp.hand_type == 4 ? w->mot[6] : w->mot[8], wp.hand_type == 4 ? w->mot[13] : w->mot[11]};
                cModelInfo** slots[2] = {&w->pRHand, &w->pLHand};
                for (int h = 0; h < 2; ++h) {
                    cModelInfo* info = *slots[h] ? ModInfoMgr.create(bins[h], w->mot[0]) : nullptr;
                    if (!info) continue;
                    cModel_swapModelInfo(em, (*slots[h])->pData, info);
                    *slots[h] = info;
                }
            } else {
                static_cast<cEm10*>(best)->setHand(1, wp.hand_type);
                static_cast<cEm10*>(best)->setHand(0, wp.hand_type);
            }
            re4dc_log("warp: handpose %d on m=%08x at room frame %u pos=%d,%d,%d\n", wp.hand_type, (unsigned) (uintptr_t) best,
                      (unsigned) wp.room_frames, (int) best->pos.x, (int) best->pos.y, (int) best->pos.z);
        }
    }
    if (!wp.has_kill || wp.kill_done) return;
    if (wp.kill_room && pG->room_id != wp.kill_room) return;
    if (wp.room_frames < wp.kill_frame) return;
    cEm* em = wp.kill_em;
    char what[64];
    if (!em) {
        if (wp.kill_id == 0) {
            // `kill 0`: the nearest live Ganado to Leon (on screen in the benchmark fights: hurt / death / blood there)
            f32 best = 1e30f;
            for (int id = 0x10; id <= 0x20 && pPL; ++id) {
                for (cEm* e = EmMgr.getEmPtr(id, 0); e; e = EmMgr.getEmPtr(id, e)) {
                    if ((e->be_flag & 0x21) != 0x21 || e->hp <= 0) continue;
                    const f32 dx = e->pos.x - pPL->pos.x, dz = e->pos.z - pPL->pos.z, d2 = dx * dx + dz * dz;
                    if (d2 < best) { best = d2; em = e; }
                }
            }
        } else {
            cEm* best = nullptr;
            f32 best_d = 1e30f;
            for (em = EmMgr.getEmPtr(wp.kill_id, 0); em; em = EmMgr.getEmPtr(wp.kill_id, em)) {
                if ((em->be_flag & 0x21) != 0x21 || em->hp <= 0) continue;
                if (!wp.kill_near || !pPL) break;
                const f32 dx = em->pos.x - pPL->pos.x, dz = em->pos.z - pPL->pos.z, d = dx * dx + dz * dz;
                if (d < best_d) { best_d = d; best = em; }
            }
            if (wp.kill_near && pPL) em = best;
        }
        if (!em) return;  // not placed yet: keep looking
        wp.kill_cur = em->id;
        wp.kill_em = em;
        if (wp.bring && pPL) {
            const f32 a = pPL->ang.y, d = (f32) wp.bring;
            em->pos.x = pPL->pos.x + __builtin_sinf(a) * d - __builtin_cosf(a) * (f32) wp.bring_side;
            em->pos.z = pPL->pos.z + __builtin_cosf(a) * d + __builtin_sinf(a) * (f32) wp.bring_side;
            em->ang.y = a + 3.14159265f;
        }
        snprintf(what, sizeof(what), "kill 0x%02x fired in %03x at room frame %u hp=%d", (unsigned) wp.kill_cur,
                 (unsigned) pG->room_id, (unsigned) wp.room_frames, (int) em->hp);
        stamp(what);
        re4dc_log("warp: kill target m=%08x pos=%d,%d,%d t=%u\n", (unsigned) (uintptr_t) em, (int) em->pos.x, (int) em->pos.y,
                  (int) em->pos.z, (unsigned) pG->Frame_cnt);
    }
    if (wp.has_drop && !(em->be_flag & 0x10000)) em->be_flag |= 0x10000;  // its own drop (EmSetDropItem) is done
    if (!(em->be_flag & 1) || em->hp <= 0) {
        if (wp.has_drop) {
            Vec at = em->pos;
            const int no = SceAtCreateItemAt(&at, wp.drop_id, wp.drop_num, -1, -1, 0, -1);
            re4dc_log("warp: drop item 0x%02x x%d at %d,%d,%d -> %d\n", (unsigned) wp.drop_id, wp.drop_num, (int) at.x,
                      (int) at.y, (int) at.z, no);
        }
        wp.kill_done = true;
        if (wp.face_mode) {  // `face corpse`: the newest kill first
            wp.face_ring[wp.face_n & 7] = em;
            wp.face_id[wp.face_n & 7] = (u8) em->id;
            ++wp.face_n;
        }
        wp.kill_watch = 40;  // then its state every 15 room frames, 40 times (death motion, fade, removal)
        snprintf(what, sizeof(what), "kill 0x%02x hp<=0 at room frame %u after %u hits", (unsigned) wp.kill_cur,
                 (unsigned) wp.room_frames, (unsigned) wp.kill_hits);
        stamp(what);
        if (wp.kill_rep) {  // `killrep <count> <gap>`: the next live one, gap room frames later
            --wp.kill_rep;
            wp.kill_done = false;
            wp.kill_watch = 0;
            wp.kill_em = nullptr;
            wp.kill_hits = 0;
            wp.kill_frame = wp.room_frames + wp.kill_gap;
            re4dc_log("warp: kill repeat %u left, next at room frame %u\n", (unsigned) wp.kill_rep,
                      (unsigned) wp.kill_frame);
        }
        return;
    }
    if (em->dmg.m_Flag & 1) return;  // the last hit is still pending
    Vec c = em->pos;
    YARARE_INFO* part = emSphereAtCk(em, &c, &c, 5000.0f, 1, 5000.0f);
    if (!part) part = &em->hitInfo;
    // `killpart <n>`: aim at the hit box of that parts number instead (5 = the head: em10's damage check then loses
    // the head on the killing hit, em10LostHead -> em10HeadSet mot[3], the stump; CAST-GC stump gate, lane stump17).
    if (wp.kill_part)
        for (YARARE_INFO* q = &em->hitInfo; q; q = q->next)
            if ((q->flags & 1) && q->partsNo == wp.kill_part) { part = q; break; }
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
    // `atlog <frame>` (lane backface22, finding event trigger areas for fixtures): every enabled scenario area of the
    // room with its type, number, trigger bits and its area's first words (xz4: floor, height, radius, 4 x/z corners).
    if (wp.has_atlog && !wp.atlog_done && wp.room_frames >= wp.atlog_frame) {
        wp.atlog_done = true;
        for (int no = 0; no < 128; ++no) {
            SceAtWork* w = SceAtPtr(no);
            if (!w) continue;
            const f32* f = (const f32*) &w->area.u;
            re4dc_log("warp: atlog room %03x no=%d type=%u flag=%02x trig=%02x chk=%u atype=%u f=%d,%d,%d %d,%d %d,%d %d,%d %d,%d\n",
                      (unsigned) pG->room_id, no, w->type, w->flag, w->trigger, w->checkType, w->area.type, (int) f[0],
                      (int) f[1], (int) f[2], (int) f[3], (int) f[4], (int) f[5], (int) f[6], (int) f[7], (int) f[8],
                      (int) f[9], (int) f[10]);
        }
    }
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
        bool sub = false;
        if (g.sub && pSubEm) {
            Vec q = {p.x + 120.0f, p.y, p.z + 120.0f};
            pSubEm->setPos(&q);
            sub = true;
        }
        char what[80];
        snprintf(what, sizeof(what), "goto %u at room frame %u pl=%d,%d,%d%s", i, (unsigned) wp.room_frames, (int) p.x,
                 (int) p.y, (int) p.z, sub ? " +sub" : "");
        stamp(what);
        // padscript presses can wait for the move ("goto=<n>", n = goto index + 1; c13 door walks)
        re4dc_fixture_state("goto", int(i + 1), -1);
    }
}
// `face <target|corpse>`: Leon (and the camera that follows him) turns toward the subject every frame. A pointer
// is used only while the enemy manager still lists it under its id (a removed enemy's object may be reused).
static bool face_listed(cEm* em, int id)
{
    for (cEm* e = EmMgr.getEmPtr(id, 0); e; e = EmMgr.getEmPtr(id, e))
        if (e == em) return true;
    return false;
}
void face_poll()
{
    if (!wp.face_mode || !pPL || (pG->Status_flg[1] & 0x10000000)) return;
    cEm* em = nullptr;
    if (wp.face_mode == 3) {  // `face near <id>`: the live enemy of that id nearest Leon (shooting rigs)
        f32 best = 1e30f;
        for (cEm* e = EmMgr.getEmPtr(wp.face_id[0], 0); e; e = EmMgr.getEmPtr(wp.face_id[0], e)) {
            if ((e->be_flag & 0x21) != 0x21 || e->hp <= 0) continue;
            const f32 dx = e->pos.x - pPL->pos.x, dz = e->pos.z - pPL->pos.z, d2 = dx * dx + dz * dz;
            if (d2 < best) { best = d2; em = e; }
        }
        static cEm* near_last;  // `face near <id> <mm>`: each new target is placed that far in front of Leon once
        if (em && em != near_last && wp.face_id[1]) {
            near_last = em;
            const f32 a = pPL->ang.y, d = (f32) wp.face_id[1] * 100.0f;
            em->pos.x = pPL->pos.x + __builtin_sinf(a) * d;
            em->pos.z = pPL->pos.z + __builtin_cosf(a) * d;
            em->pos.y = pPL->pos.y;
            em->ang.y = a + 3.14159265f;
            re4dc_log("warp: face near target m=%08x placed %d mm ahead t=%u\n", (unsigned) (uintptr_t) em, (int) d,
                      (unsigned) pG->Frame_cnt);
        }
    } else if (wp.face_mode == 1) {
        if (wp.kill_em && face_listed(wp.kill_em, wp.kill_cur)) em = wp.kill_em;
    } else {
        for (unsigned k = 0; k < 8 && k < wp.face_n && !em; ++k) {
            const unsigned i = (wp.face_n - 1 - k) & 7;
            if (face_listed(wp.face_ring[i], wp.face_id[i])) em = wp.face_ring[i];
        }
    }
    if (!em) return;
    const f32 dx = em->pos.x - pPL->pos.x, dz = em->pos.z - pPL->pos.z;
    if (dx * dx + dz * dz < 1.0f) return;
    pPL->ang.y = atan2f(dx, dz);
}
// `god` / `alert` (benchmark fixtures, the hwcal disc's invuln / alert): every frame / once at the room frame.
}   // namespace (closed for the C symbol below)
// bell108: requests for r108's bell task (src/st1/r108.cpp r108_initChurchBell, DBG_WARP builds), one per shot
extern "C" { int re4dc_bell108_req = 0; }
int addMoney(int n);   // src/game/item.cpp
namespace {
void god_alert_poll()
{
    if (wp.god && pG) pG->pl_life = pG->pl_life_max;
    if (wp.money > 0 && pG) {
        const int have = addMoney(wp.money);
        re4dc_log("warp: money +%d -> %d\n", wp.money, have);
        wp.money = 0;
    }
    if (wp.ammo && ItemMgr.pArm && (ItemMgr.pArm->bullet & 0x1FFF) < 3)
        ItemMgr.pArm->bullet = (u16) ((ItemMgr.pArm->bullet & 0xE000) | 9);
    if (wp.b108_n && pG && pG->room_id == 0x108 && wp.room_frames >= wp.b108_frame) {
        char what[64];
        snprintf(what, sizeof(what), "bell108 shot at room frame %u (alive %d)", (unsigned) wp.room_frames,
                 SceCountEmAlive(0x10, 0x20));
        stamp(what);
        ++re4dc_bell108_req;
        --wp.b108_n;
        wp.b108_frame = wp.room_frames + wp.b108_gap;
    }
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
#if defined(RE4DC_BENCH_CENSUS) && RE4DC_BENCH_CENSUS
bool cen_live(cEm* e) { return e && (e->be_flag & 0x21) == 0x21 && e->hp > 0; }
bool cen_listed(cEm* e)
{
    for (int id = 0x10; id <= 0x20; ++id)
        for (cEm* x = EmMgr.getEmPtr(id, 0); x; x = EmMgr.getEmPtr(id, x))
            if (x == e) return true;
    return false;
}
// BENCH_CENSUS timed lines (first room, each tick), the tank's hp hold and Leon facing it while auto-fire runs.
void census_poll()
{
    if (wp.rooms != 1 || !pPL || !pG) return;
    for (unsigned i = 0; i < wp.n_cen; ++i) {
        auto& c = wp.cen[i];
        if (c.done || wp.room_frames < c.frame) continue;
        c.done = true;
        char what[96];
        if (c.kind == 1) {
            if (&re4dc_rigid_hide) re4dc_rigid_hide = (unsigned) c.a;
            snprintf(what, sizeof(what), "census: rigid %s at room frame %u", c.a ? "off" : "on", (unsigned) wp.room_frames);
        } else if (c.kind == 2) {
#if defined(RE4DC_BENCH_MISTCUT) && RE4DC_BENCH_MISTCUT
            re4dc_mist_cut = c.a ? 239u : 0u;
#endif
            snprintf(what, sizeof(what), "census: fx %s at room frame %u", c.a ? "off" : "on", (unsigned) wp.room_frames);
        } else if (c.kind == 3) {
            unsigned put = 0;
            for (s32 m = 0; m < c.a && wp.n_crowd < 8; ++m) {
                cEm* best = nullptr;
                f32 best_d = 1e30f;
                for (int id = 0x10; id <= 0x20; ++id)
                    for (cEm* e = EmMgr.getEmPtr(id, 0); e; e = EmMgr.getEmPtr(id, e)) {
                        if (!(e->be_flag & 1) || e->hp <= 0) continue;   // listed and alive (a far one may be suspended)
                        bool used = false;
                        for (unsigned q = 0; q < wp.n_crowd; ++q) used = used || wp.crowd_em[q] == e;
                        if (used) continue;
                        const f32 dx = e->pos.x - pPL->pos.x, dz = e->pos.z - pPL->pos.z, d = dx * dx + dz * dz;
                        if (d < best_d) { best_d = d; best = e; }
                    }
                if (!best) break;
                // spread across the view: -1.5, +1.5, -0.5, +0.5, -2.5, +2.5 m ... to Leon's side, dist ahead
                const unsigned slot = wp.n_crowd;
                const f32 side = ((slot & 1) ? 1.0f : -1.0f) * (slot < 2 ? 150.0f : slot < 4 ? 50.0f : 250.0f);
                const f32 a = pPL->ang.y, d = (f32) c.b + (f32) (slot / 2) * 60.0f;
                best->pos.x = pPL->pos.x + __builtin_sinf(a) * d - __builtin_cosf(a) * side;
                best->pos.z = pPL->pos.z + __builtin_cosf(a) * d + __builtin_sinf(a) * side;
                best->pos.y = pPL->pos.y;
                best->ang.y = a + 3.14159265f;
                wp.crowd_em[wp.n_crowd++] = best;
                ++put;
            }
            snprintf(what, sizeof(what), "census: crowd %u put in front (asked %d, %u brought) at room frame %u", put,
                     (int) c.a, wp.n_crowd, (unsigned) wp.room_frames);
        } else if (c.kind == 5) {
            // objdump: every listed object (ObjMgr) and enemy (EmMgr) with id, kind and position (finding the props)
            unsigned no = 0;
            for (cUnit* u = ObjMgr.pAlive; u; u = u->pNext, ++no) {
                const cModel* m = (const cModel*) u;
                re4dc_log("census: obj %u id=%02x kind=%u pos=%d,%d,%d\n", no, (unsigned) m->id, (unsigned) m->kindid,
                          (int) m->pos.x, (int) m->pos.y, (int) m->pos.z);
            }
            for (cUnit* u = EmMgr.pAlive; u; u = u->pNext, ++no) {
                const cEm* e = (const cEm*) u;
                re4dc_log("census: em %u id=%02x be=%08x hp=%d pos=%d,%d,%d\n", no, (unsigned) e->id, (unsigned) e->be_flag,
                          (int) e->hp, (int) e->pos.x, (int) e->pos.y, (int) e->pos.z);
            }
            snprintf(what, sizeof(what), "census: objdump %u at room frame %u pl=%d,%d,%d", no, (unsigned) wp.room_frames,
                     (int) pPL->pos.x, (int) pPL->pos.y, (int) pPL->pos.z);
        } else {
            cEm* best = nullptr;
            f32 best_d = 1e30f;
            for (unsigned q = 0; q < wp.n_crowd; ++q) {
                cEm* e = wp.crowd_em[q];
                if (!cen_listed(e) || !cen_live(e)) continue;
                const f32 dx = e->pos.x - pPL->pos.x, dz = e->pos.z - pPL->pos.z, d = dx * dx + dz * dz;
                if (d < best_d) { best_d = d; best = e; }
            }
            wp.tank = best;
            if (best) best->hp = 30000;
            snprintf(what, sizeof(what), "census: tank %s at room frame %u", best ? "set" : "none", (unsigned) wp.room_frames);
        }
        stamp(what);
    }
    if (wp.tank) {
        if (!cen_listed(wp.tank) || wp.tank->hp <= 0) {
            re4dc_log("census: tank lost at room frame %u (hits %u)\n", (unsigned) wp.room_frames, (unsigned) wp.tank_hits);
            wp.tank = nullptr;
        } else {
            if (wp.tank->hp < 30000) { ++wp.tank_hits; wp.tank->hp = 30000; }
        }
    }
    const bool firing = wp.fire_to && wp.room_frames >= wp.fire_from && wp.room_frames < wp.fire_to;
    if (firing) {
        pG->Debug_flg[2] |= 0x00400000;   // infinite ammo
        if (wp.tank && !(pG->Status_flg[1] & 0x10000000)) {
            const f32 dx = wp.tank->pos.x - pPL->pos.x, dz = wp.tank->pos.z - pPL->pos.z;
            if (dx * dx + dz * dz >= 1.0f) pPL->ang.y = atan2f(dx, dz);
        }
    }
    unsigned rp = 0, rv = 0;
    if (re4dc_rigid_census) {
        rp = re4dc_rigid_census[0]; rv = re4dc_rigid_census[2];
        if (!(wp.room_frames % 150) && rp)
            re4dc_log("census: rigid frame %u parts=%u meshlets=%u verts=%u big=%p big_verts=%u big_ml=%u big_lod=%u\n",
                      (unsigned) wp.room_frames, rp, re4dc_rigid_census[1], rv,
                      re4dc_rigid_census_big ? re4dc_rigid_census_big : nullptr, re4dc_rigid_census[3],
                      re4dc_rigid_census[4], re4dc_rigid_census[5]);
        if (!(wp.room_frames % 150) && re4dc_rigid_census_big) {
            const cModel* m = (const cModel*) re4dc_rigid_census_big;
            re4dc_log("census: rigid big model id=%02x kind=%u pos=%d,%d,%d\n", (unsigned) m->id, (unsigned) m->kindid,
                      (int) m->pos.x, (int) m->pos.y, (int) m->pos.z);
        }
        for (unsigned i = 0; i < 6; ++i) re4dc_rigid_census[i] = 0;
        re4dc_rigid_census_big = nullptr;
    }
    re4dc_bench_census(re4dc_bench_esp_live(), wp.tank_hits, rp, rv);
}
#endif
#if defined(RE4DC_BENCHMARK) && RE4DC_BENCHMARK
// BENCHMARK: the scene's end state (the determinism check compares these lines between runs): Leon, the Ganados of
// the rooms' count range (model ids 0x10..0x20) with position, hp and flags, folded into one hash.
void bench_state_log(unsigned frame)
{
    unsigned h = 2166136261u;
    int alive = 0, listed = 0;
    for (int id = 0x10; id <= 0x20; ++id) {
        for (cEm* e = EmMgr.getEmPtr(id, 0); e; e = EmMgr.getEmPtr(id, e)) {
            ++listed;
            if ((e->be_flag & 1) && e->hp > 0) ++alive;
            const int v[6] = {id, (int) e->pos.x, (int) e->pos.y, (int) e->pos.z, (int) e->hp, (int) (e->be_flag & 0xFF)};
            for (int x : v) h = (h ^ (unsigned) x) * 16777619u;
        }
    }
    if (pPL) {
        const int v[3] = {(int) pPL->pos.x, (int) pPL->pos.y, (int) pPL->pos.z};
        for (int x : v) h = (h ^ (unsigned) x) * 16777619u;
    }
    re4dc_log("bench: state scene %d room %03x room_frame %u tick %u alive %d listed %d counted %d pl=%d,%d,%d hash=%08x\n",
              re4dc_bench_scene_no(), (unsigned) pG->room_id, frame, (unsigned) pG->Frame_cnt, alive, listed,
              SceCountEmAlive(0x10, 0x20), pPL ? (int) pPL->pos.x : 0, pPL ? (int) pPL->pos.y : 0,
              pPL ? (int) pPL->pos.z : 0, h);
}
// BENCHMARK, each game tick of the scene's room: 1 while the scene is over (the rest of the poll is skipped). At the
// scene's end the next scene is chosen (after the last one: the results screen, which returns on A with scene 1) and
// the source's soft reset is requested (Game Reset path, systemResetCheck at the end of this frame; 0x200 locks it
// while the game forbids a reset). re4dc_warp_soft_reset arms the next fixture.
bool bench_poll()
{
    if (bench_pending) {
        if (wp.god && pG) pG->pl_life = pG->pl_life_max;
        return true;
    }
    {   // Ganados alive now (ids 0x10..0x20 in the enemy manager, alive and hp > 0): SceCountEmAlive also counts the
        // ALIVE_CAP hold's waiting entries (the rooms' scripts read uncapped), so it would not show the cap reached
        int live = 0;
        for (int id = 0x10; id <= 0x20; ++id)
            for (cEm* e = EmMgr.getEmPtr(id, 0); e; e = EmMgr.getEmPtr(id, e))
                if ((e->be_flag & 1) && e->hp > 0) ++live;
        re4dc_bench_alive(live);
    }
    if (!re4dc_bench_tick(wp.room_frames)) return false;
    bench_state_log(wp.room_frames);
    const char* next = re4dc_bench_next_scene();
    if (!next) {
        pG->System_flg |= 0x20000000;   // no hang check while the results screen holds the frame loop (as `freeze`)
        SndSoftReset();                 // silence: the frame loop stops feeding the sound driver
        next = re4dc_bench_results();
    }
    bench_next = next;
    bench_pending = true;
    pG->System_flg |= 0x4000000;        // soft reset request (systemResetCheck: dev_mode path)
    stamp("bench: soft reset requested");
    return true;
}
#endif
#if defined(RE4DC_QA_MENU) && RE4DC_QA_MENU
// QA_MENU, each game tick (active rig or not): the invincibility toggles, then the in-game menu on the chord (L + R +
// D-pad Down) in free play only: the main game state (Rno0 3 / Rno1 0), no event or event start, no sub screen
// (inventory, files, map), Leon free (checkEvent 1, as the rig's radio replay), and 30 such frames since the last room
// entry or menu (no door load). The menu holds the frame loop (no hang check meanwhile, as `still`). A teleport or
// "quit to title" requests the source's soft reset (as the benchmark disc); re4dc_warp_soft_reset arms the preset.
// true = a reset is pending: the rest of the poll is skipped.
bool qa_poll()
{
    if (!pG) return false;
    if (qa_pending) return true;
    const unsigned f = re4dc_qa_flags();
    if (f & 1) pG->pl_life = pG->pl_life_max;
    if ((f & 2) && pG->ashley_life_max) pG->ashley_life = pG->ashley_life_max;
    const bool en = (f & 4) != 0;
    if (en || qa_enemy_on) {
        // Enemies invincible: hp held high every tick (hits, reactions, blood and gore still run; no death); off again:
        // hp back to hp_max.
        for (int id = 0x10; id < 0x80; ++id)
            for (cEm* e = EmMgr.getEmPtr(id, 0); e; e = EmMgr.getEmPtr(id, e)) {
                if (!(e->be_flag & 1) || e->hp <= 0) continue;
                if (en) e->hp = 30000;
                else if (e->hp_max > 0 && e->hp > e->hp_max) e->hp = e->hp_max;
            }
        qa_enemy_on = en;
    }
    const bool free_play = pPL && pG->Rno0 == 3 && pG->Rno1 == 0 && !(pG->Status_flg[1] & 0x10000000) &&
                           !SubScreenWk.type && !SceSys.event_start_cnt && pPL->checkEvent() == 1;
    qa_frames = free_play ? qa_frames + 1 : 0;
    const bool autom = qa_auto_armed && qa_frames >= (qa_auto_frame > 30 ? qa_auto_frame : 30);
    if (!autom && (qa_frames < 30 || !re4dc_qa_combo())) return false;
    const u32 keep = pG->System_flg & 0x20000000;
    pG->System_flg |= 0x20000000;   // no hang check while the menu holds the frame loop
    const char* path = nullptr;
    int r;
    {   // the Diagnostics page's game side
        int live = 0;
        for (int id = 0x10; id <= 0x20; ++id)
            for (cEm* e = EmMgr.getEmPtr(id, 0); e; e = EmMgr.getEmPtr(id, e))
                if ((e->be_flag & 1) && e->hp > 0) ++live;
        re4dc_qa_game((unsigned) pG->room_id, live, memCheckHeapActive(4) ? (int) OSCheckHeap(Heap[4].handle) : -1,
                      wp.name[0] ? wp.name : nullptr);
    }
    if (autom) {
        r = re4dc_qa_menu_auto(qa_auto_file, &path, qa_auto_hold);
        qa_auto_armed = false;
    } else while ((r = re4dc_qa_menu(&path)) == 3) {
        pG->pl_life = pG->pl_life_max;
        if (pG->ashley_life_max) pG->ashley_life = pG->ashley_life_max;
        re4dc_log("qa: health refilled\n");
    }
    // Retraces continue during this intentional pause. Refresh the presentation heartbeat before
    // restoring the source hang check: otherwise a menu held for 60 s HALTs main.cpp(548) on close.
    // The check stays enabled in gameplay, and an already-disabled check keeps its original state.
    vsync_cnt = 0;
    pG->System_flg = (pG->System_flg & ~0x20000000) | keep;
    qa_frames = 0;
    if (r == 0) return false;
    qa_next = r == 1 ? path : nullptr;
    qa_pending = true;
    SndSoftReset();
    pG->System_flg |= 0x4000000;    // soft reset request (systemResetCheck), as the benchmark disc's next scene
    stamp(r == 1 ? "qa: teleport: soft reset requested" : "qa: quit to title: soft reset requested");
    return true;
}
#endif
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

#if defined(RE4DC_WARP_AFTER_RESET) && RE4DC_WARP_AFTER_RESET
// main.cpp systemSoftReset: an after_reset warp turns active for the title that follows.
void re4dc_warp_soft_reset(void)
{
#if defined(RE4DC_BENCHMARK) && RE4DC_BENCHMARK
    if (bench_pending && bench_next) {
        // BENCHMARK: the next scene's fixture, from a clean rig (the title that follows is skipped as at boot)
        const char* path = bench_next;
        bench_next = nullptr;
        bench_pending = false;
        wp = Warp{};
        load(path);
        stamp("bench: next scene armed at soft reset");
        return;
    }
#endif
#if defined(RE4DC_QA_MENU) && RE4DC_QA_MENU
    re4dc_qa_in_room(0);
    qa_frames = 0;
    if (qa_pending) {
        // QA_MENU: the chosen preset from a clean rig (the title that follows is skipped as at boot), or a passive rig
        // for "quit to title" (the title and its menus run normally).
        const char* path = qa_next;
        qa_next = nullptr;
        qa_pending = false;
        wp = Warp{};
        if (path) { load(path); stamp("qa: preset armed at soft reset"); }
        else { wp.loaded = true; stamp("qa: title at soft reset"); }
        return;
    }
#endif
    if (!wp.loaded) load();
    if (wp.after_reset && !wp.active && wp.room) {
        wp.active = true;
        wp.boot_us = 0;
        stamp("after_reset armed");
    }
}
#endif

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
    if (wp.chapter) {
        pG->chapter = wp.chapter - 1;
        re4dc_log("warp: chapter %d\n", wp.chapter - 1);
    }
    re4dc_log("warp: start room=%03x next_room=%03x pos=%d,%d,%d ang=%d/1000\n", (unsigned) wp.room,
              (unsigned) pG->next_room, (int) pG->NextPos.x, (int) pG->NextPos.y, (int) pG->NextPos.z,
              (int) (pG->NextY * 1000.0f));
}

// ui_bridge.cpp re4dc_room_enter (every room entry).
void re4dc_warp_room_enter(void)
{
#if defined(RE4DC_QA_MENU) && RE4DC_QA_MENU
    re4dc_qa_in_room(1);
    qa_frames = 0;
#endif
    if (!wp.active) {
        native_alive_room_enter();
        return;
    }
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
    for (unsigned i = 0; i < 4; ++i) {
        if (!wp.status[i]) continue;
        pG->Status_flg[i] |= wp.status[i];
        re4dc_log("warp: Status_flg[%u] |= %08x\n", i, (unsigned) wp.status[i]);
    }
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
#if defined(RE4DC_QA_MENU) && RE4DC_QA_MENU
    if (qa_poll()) return;
#endif
    if (!wp.active) {
        native_alive_poll();
        return;
    }
    // `still` counts this room's poll frames (wp.room_frames, the clock the act lines share in the first room).
    if (wp.still_next < wp.n_still && pG && wp.rooms == 1 && wp.room_frames >= wp.still_tick[wp.still_next]) {
        const unsigned i = wp.still_next++;
        re4dc_log("warp: still %u at room frame %u tick %u pad %u hold %u ms\n", i, (unsigned) wp.room_frames,
                  (unsigned) pG->Frame_cnt, (unsigned) wp.pad_frames, (unsigned) wp.still_ms[i]);
        const u32 keep = pG->System_flg & 0x20000000;
        pG->System_flg |= 0x20000000;   // no hang check while held (as `freeze`)
        if (wp.still_ms[i]) thd_sleep(wp.still_ms[i]);
        pG->System_flg = (pG->System_flg & ~0x20000000) | keep;
        re4dc_log("warp: still %u released\n", i);
    }
    if (wp.has_freeze && pG && (u32) pG->Frame_cnt >= wp.freeze_tick) {
        re4dc_log("warp: frozen at tick %u\n", (unsigned) pG->Frame_cnt);
        // A still fixture, not a hang: set the game's own "no hang check" bit (exception.cpp sets it
        // too) so haltExecCheck does not HALT main.cpp(548) 60 s into the freeze.
        pG->System_flg |= 0x20000000;
        for (;;) thd_sleep(1000);
    }
    ++wp.room_frames;
#if defined(RE4DC_BENCH_CENSUS) && RE4DC_BENCH_CENSUS
    census_poll();
#endif
#if defined(RE4DC_BENCHMARK) && RE4DC_BENCHMARK
    if (wp.rooms == 1 && bench_poll()) return;
#endif
    god_alert_poll();
    kill_poll();
    face_poll();
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
    for (unsigned i = 0; i < wp.n_lodat; ++i) {
        Warp::LodAt& c = wp.lodat[i];
        if (c.done || wp.rooms != 1 || wp.room_frames < c.frame) continue;
        c.done = true;
        re4dc_log("warp: lodat leon %d ganado %d at room frame %u\n", c.leon, c.ganado, (unsigned) wp.room_frames);
#if defined(RE4DC_LEON_LOD) && RE4DC_LEON_LOD
        if (c.leon >= 0) re4dc_leon_lod_set((unsigned) c.leon);
#endif
#if defined(RE4DC_GANADO_LOD) && RE4DC_GANADO_LOD
        if (c.ganado >= 0) re4dc_ganado_lod_set((unsigned) c.ganado);
#endif
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
        if (wp.has_drop && ItemMgr.pItems) {
            int n = 0;
            for (int i = 0; i < ItemMgr.nItems; ++i)
                if ((ItemMgr.pItems[i].flags & 1) && ItemMgr.pItems[i].id == wp.drop_id) n += ItemMgr.pItems[i].num;
            re4dc_log("warp: inv item 0x%02x count %d wep %02x\n", (unsigned) wp.drop_id, n, (unsigned) ItemMgr.m_wep_id);
        }
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
void re4dc_warp_pad(unsigned short* buttons, signed char* stickX, signed char* stickY)
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
    const bool ev_act = (wp.cur_act >= 0 && wp.cur_act < (int) wp.n_act && wp.pad_frames < wp.cur_until &&
                         wp.act[wp.cur_act].ev) ||
                        (wp.next_act < wp.n_act && wp.act[wp.next_act].ev);
    if ((pG->Status_flg[1] & 0x10000000) && !ev_act) {
        re4dc_warp_cut("event");
        return;
    }
#if defined(RE4DC_BENCH_CENSUS) && RE4DC_BENCH_CENSUS
    if (wp.fire_to && wp.rooms == 1 && wp.room_frames >= wp.fire_from && wp.room_frames < wp.fire_to) {
        *buttons |= 0x0020;                                                     // R: aim
        if ((wp.room_frames - wp.fire_from) % wp.fire_period >= 4 &&
            (wp.room_frames - wp.fire_from) % wp.fire_period < 7) *buttons |= 0x0100;   // A: fire (after 4 aimed frames)
    }
#endif
    if (wp.cur_act >= 0 && wp.cur_act < (int) wp.n_act && wp.pad_frames < wp.cur_until) {
        const Act& a = wp.act[wp.cur_act];
        *buttons |= a.buttons;
        if (a.stick) *stickY = a.stick;
        if (a.stickx) *stickX = a.stickx;
        return;
    }
    while (wp.next_act < wp.n_act && wp.act[wp.next_act].entry < wp.rooms) ++wp.next_act;  // an earlier room's, unfired
    if (wp.next_act < wp.n_act && wp.act[wp.next_act].entry == wp.rooms && wp.pad_frames >= wp.act[wp.next_act].frame) {
        const Act& a = wp.act[wp.next_act];
        wp.cur_act = (int) wp.next_act++;
        wp.cur_until = wp.pad_frames + a.hold;
        char what[72];
        snprintf(what, sizeof(what), "act %u buttons=%04x stick=%d,%d hold=%u pad=%u", (unsigned) wp.cur_act,
                 (unsigned) a.buttons, (int) a.stickx, (int) a.stick, (unsigned) a.hold, (unsigned) wp.pad_frames);
        stamp(what);
        *buttons |= a.buttons;
        if (a.stick) *stickY = a.stick;
        if (a.stickx) *stickX = a.stickx;
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

#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
// WORLD_METER (game30.mk): the room the VRAMFAIL lines name (tick_log.cpp, once per tick).
unsigned re4dc_wm_room(void) { return pG ? (unsigned) pG->room_id : 0u; }
#endif
// Read-only activation query, including mask0 OFF controls; does not log or arm.
int re4dc_warp_late_open(void)
{
    return wp.has_late && pG && pG->room_id == wp.late_room && pG->Frame_cnt >= wp.late_tick ? 1 : 0;
}

// The validated late target/current game room, only while its window is open.
unsigned re4dc_warp_late_room(void)
{
    return re4dc_warp_late_open() ? wp.late_room : 0u;
}

}  // extern "C"
#endif  // RE4DC_DBG_WARP
