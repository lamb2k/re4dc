// e1_qalink.cpp: the RE4 engine's layer on dc-qalink 0.2 (lane eng-link2, 2026-11-23; docs/engine/CONSOLE_LOOP.md
// section 17). Linked only into QA and test images (game/qalink.mk: SENDABLE=1 with DCQL_ENABLE=1); it is the only
// RE4 code that calls dc-qalink's live data, in-game menu and network disc. dc-qalink itself is the pinned submodule
// engine/loader/dc-qalink; RE4 keeps no copy of it.
//
// What it does, and where (every step outside the tick's rows: core/main.cpp calls it after the picture's frame time is
// taken and before the room-change check, as the loading state is):
//   - live data: a record per picture (the ROW columns as phases, room, Leon's position, counters), copied into
//     dc-qalink's fixed ring (dcql_live_frame); the link thread sends it. No allocation, no network, no disc here.
//   - commands from the PC run here, at the end of a picture (dc-qalink runs the callback inside dcql_live_frame):
//       warp <preset>   plants the room-change request (the stores the door handler makes, as core/room_change.cpp's
//                       DOOR scene does) toward the preset's room, position and angle; the loop's own loading state
//                       (e1_room_change_run) answers it right after: the first room's memory returned, the next
//                       loaded, play resumes on a field boundary. Refused in the one-room images (FIGHT, BOSS) and in
//                       the hill scene (its partner is not moved between rooms).
//       option menu=N   opens the in-game menu for N seconds (0 closes it); the console's own pad opens it with
//                       LT + RT + START. While it is open the game is held (pictures held, nothing ticks).
//       option end=1    ends the run after this picture (E1 END: the report, then back to the loader).
//       option crash=1  a forced crash (an address error) on the next picture: the way back's exception path.
//       option readx=1  CONTROL: opens and reads 4 KiB of the room's pack in play on the next picture; the play-file
//                       guards (core/play_files.c) must count it and tools/consoleloop/re4_link_check.py must FAIL.
//   - the in-game menu (dc-qalink's dcql_menu, way (b): drawn into the displayed frame buffer while the game is held):
//     RE4 pages Scene (image, room, Leon, enemies, picture), Timing (last, mean and worst picture and drawing), Warp
//     (the presets); dc-qalink's own Link, Log and Snapshot pages.
//   - the network disc: at boot, before any /cd read, dc-qalink's /cd handler is mounted when the loader started the
//     image on the adapter. Main mode (owner 2026-11-23): the PC serves the whole RE4 disc (each build's staged disc
//     folder), so an increment is build, stage, push, run with only the loader on the SD card; secondary mode (disc
//     timing): the GDEMU disc as the base with the PC's changed files over it. All of it is load-time reading: nothing
//     reads a file inside a picture (the play-file guards, and readx as the control). Room-entry times are logged
//     (E1 QL LOADTIME) and sent as live log lines, with the disc mode named.
#include "global.h"
#include "player.h"
#include "em.h"
#include "e1_engine.h"
#include "e1_core.h"
#include "e1_kos.h"
#include "e1_qalink.h"
#include <dc/maple.h>
#include <dc/maple/controller.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
extern "C" {
#include "cl_client.h"
#include "dcql_live.h"
#include "dcql_menu.h"
#include "dcql_disc.h"
void e1_play_files_counts(unsigned* opens, unsigned* reads);   // core/play_files.c (lane eng-link2)
}

static const char DEF[] =
#if defined(E2_FIGHT)
    "program RE4 engine: the fight at the cross (FIGHT)\n"
#elif defined(E2_BOSS)
    "program RE4 engine: El Gigante (BOSS)\n"
#else
    "program RE4 engine: village route (E1)\n"
#endif
    "rate 30\n"
    "phase in - - Input\n"
    "phase beh - - Behaviour\n"
    "phase svc 9000 - Services\n"
    "phase draw 14000 - Drawing\n"
    "phase pvr - - PVR wait\n"
    "phase pace - - Pacer wait\n"
    "phase frame 33333 total Picture\n"
    "ctr enemies 0 Scene Enemies alive\n"
    "ctr loads 0 Scene Room loads\n"
    "ctr menu 0 Scene Menu opens\n"
    "ctr discopen 1 Guards Disc opens in play\n"
    "ctr discread 1 Guards Disc reads in play\n"
    "ctr over 0 Timing Pictures over two fields (36.7 ms)\n"
    "lane 1 Loads\n"
    "lane 2 Menu\n"
    "preset village Village Route start (r101)\n"
    "preset square Village The square (r101)\n"
    "preset farm Farm Farm entry (r103)\n"
    "preset gate Village Back through the farm gate (r101)\n"
    "preset hill Hill Hill path, Leon alone (r11d)\n"
    "option menu int 0 120 0 Menu open (seconds)\n"
    "option end bool 0 End the run now\n"
    "option crash bool 0 Forced crash (way back check)\n"
    "option readx bool 0 Control: pack read in play\n";

struct Preset { const char* id; const char* label; unsigned room; float pos[3]; float ang; };
// Positions: the scenes' own fixtures (core/route.cpp: the village route and the hill; tools/plays_right/fixtures/
// bell-ganado.txt: the square) and the DOOR scene's two door destinations (eng-load2 run d1-fly2g serial: E1 DOOR
// request lines, r101 area 2 -> r103 and r103 area 0 -> r101). Rooms with a pack in core/room_change.cpp room_pack.
static const Preset PRESETS[] = {
    {"village", "Route start", 0x101, {-7914.0f, 0.0f, 2000.0f}, 1.5708f},
    {"square", "The square", 0x101, {-7914.0f, 0.0f, -254.0f}, 2.9600f},
    {"farm", "Farm entry", 0x103, {-47609.0f, 11.0f, 7083.0f}, 1.888f},
    {"gate", "Farm gate (village)", 0x101, {39371.0f, 3201.0f, -26666.0f}, -1.503f},
    {"hill", "Hill path", 0x11d, {20214.0f, 0.0f, 13952.0f}, -1.8170f},
};
static const unsigned NPRESETS = sizeof(PRESETS) / sizeof(PRESETS[0]);

static int g_on;                 // started by the loader with the link on the adapter
static int g_end, g_crash, g_readx;
static int g_menu_secs;          // option menu=N: open for N seconds
static uint64_t g_menu_until;    // the remote opening's close time (us), 0 = none
static unsigned g_loads, g_menus, g_over, g_last_room, g_warps, g_warps_refused;
static int g_warp_pending = -1;  // preset index planted at this picture's end
static int g_disc = -99;         // the network disc's mount result
static int g_disc_whole;         // the PC serves the whole disc (the main mode, owner 2026-11-23)
static uint64_t g_t_boot, g_t_last_end;   // room-entry times (us)
static const char* disc_name()
{
    return g_disc != 0 ? "GDEMU disc" : g_disc_whole ? "network disc, whole" : "network disc over GDEMU";
}
// the Timing page's figures (us)
static uint32_t t_last, t_worst, t_draw_last, t_draw_worst;
static uint64_t t_sum, t_draw_sum;
static uint32_t t_n;

static unsigned enemies_alive()
{
    unsigned n = 0;
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext)
        if (e->id >= 0x10) n++;   // 0x01.. Leon and the partners; enemies from 0x10
    return n;
}

static int plant_warp(int i, char* why)
{
#ifdef E2_BOSS
    (void) i;
    snprintf(why, 60, "this image is one room (FIGHT/BOSS)");
    return 2;
#else
    if (e1_scene == E1_SCENE_HILL) { snprintf(why, 60, "the hill scene's partner does not change rooms"); return 2; }
    if (pG->Rno0 == 4) { snprintf(why, 60, "a room change is already under way"); return 2; }
    const Preset& p = PRESETS[i];
    // the door handler's stores (sce_at.cpp sceAtFunc_door 1038-1085), as core/room_change.cpp plants them for the
    // DOOR scene; the destination is the preset's instead of an AEV record's
    pG->Stop_flg = 0xFFFFFFFFu;
    pG->NextPos.x = p.pos[0];
    pG->NextPos.y = p.pos[1];
    pG->NextPos.z = p.pos[2];
    pG->NextY = p.ang;
    pG->room_id_prev = pG->room_id;
    pG->Part_old = pG->Part;
    pG->next_stage = (u8) (p.room >> 8);
    pG->next_room_no = (u8) (p.room & 0xff);
    pG->next_point = 0;
    pG->door_no = 0;
    pG->Rno0 = 4;
    pG->Rno1 = pG->Rno2 = pG->Rno3 = 0;
    pG->r_continue_cnt = 0;
    pG->System_flg &= ~0x40u;
    g_warp_pending = i;
    return 0;
#endif
}

static int find_preset(const char* id)
{
    for (unsigned i = 0; i < NPRESETS; i++)
        if (!strcmp(id, PRESETS[i].id)) return (int) i;
    return -1;
}

static int on_command(int code, const char* arg, unsigned len, char* why, void* user)
{
    (void) len;
    (void) user;
    if (code == DCQL_CMD_WARP) {
        const int i = find_preset(arg);
        if (i < 0) { snprintf(why, 60, "no preset '%.30s'", arg); g_warps_refused++; return 2; }
        const int rc = plant_warp(i, why);
        if (rc) g_warps_refused++;
        else e1_log("E1 QL warp %s requested at tick %lu: room %03x -> %03x\n", arg, (unsigned long) e1_tick,
                    (unsigned) pG->room_id, PRESETS[i].room);
        return rc;
    }
    if (code == DCQL_CMD_OPTION) {
        const char* eq = strchr(arg, '=');
        if (!eq) { snprintf(why, 60, "name=value"); return 2; }
        const int v = atoi(eq + 1);
        const size_t n = (size_t) (eq - arg);
        if (n == 4 && !strncmp(arg, "menu", 4)) {
            if (v < 0 || v > 120) { snprintf(why, 60, "menu 0..120 seconds"); return 2; }
            g_menu_secs = v;
            if (!v) dcql_menu_close();
            return 0;
        }
        if (n == 3 && !strncmp(arg, "end", 3)) { g_end = v != 0; return 0; }
        if (n == 5 && !strncmp(arg, "crash", 5)) { g_crash = v != 0; return 0; }
        if (n == 5 && !strncmp(arg, "readx", 5)) { g_readx = v != 0; return 0; }
        snprintf(why, 60, "no option '%.*s'", (int) (n < 30 ? n : 30), arg);
        return 2;
    }
    snprintf(why, 60, "the engine's pad is its scene script");
    return 2;
}

// ---- the in-game menu: RE4's pages ----
static void i_image(char* o, int n, void*)
{
#if defined(E2_FIGHT)
    snprintf(o, n, "FIGHT (the cross)");
#elif defined(E2_BOSS)
    snprintf(o, n, "BOSS (El Gigante)");
#else
    snprintf(o, n, "%s", e1_scene == E1_SCENE_HILL ? "E1 (hill scene)" : "E1 (village route)");
#endif
}
static void i_room(char* o, int n, void*) { snprintf(o, n, "r%03x", (unsigned) pG->room_id); }
static void i_leon(char* o, int n, void*)
{
    if (pPL) snprintf(o, n, "%d %d %d", (int) pPL->pos.x, (int) pPL->pos.y, (int) pPL->pos.z);
    else snprintf(o, n, "-");
}
static void i_enemies(char* o, int n, void*) { snprintf(o, n, "%u", enemies_alive()); }
static void i_tick(char* o, int n, void*) { snprintf(o, n, "%lu of %lu", (unsigned long) e1_tick, (unsigned long) e1_state[2]); }
static void i_disc(char* o, int n, void*)
{
    snprintf(o, n, "%s", disc_name());
}
static void ms(char* o, int n, uint32_t us) { snprintf(o, n, "%lu.%02lu ms", (unsigned long) (us / 1000), (unsigned long) (us % 1000 / 10)); }
static void i_last(char* o, int n, void*) { ms(o, n, t_last); }
static void i_mean(char* o, int n, void*) { ms(o, n, t_n ? (uint32_t) (t_sum / t_n) : 0); }
static void i_worst(char* o, int n, void*) { ms(o, n, t_worst); }
static void i_dlast(char* o, int n, void*) { ms(o, n, t_draw_last); }
static void i_dmean(char* o, int n, void*) { ms(o, n, t_n ? (uint32_t) (t_draw_sum / t_n) : 0); }
static void i_dworst(char* o, int n, void*) { ms(o, n, t_draw_worst); }
static void i_over(char* o, int n, void*) { snprintf(o, n, "%u of %lu", g_over, (unsigned long) t_n); }
static void i_guard(char* o, int n, void*)
{
    unsigned op = 0, rd = 0;
    e1_play_files_counts(&op, &rd);
    snprintf(o, n, "opens %u reads %u", op, rd);
}
static void i_loads(char* o, int n, void*) { snprintf(o, n, "%u (warps %u, refused %u)", g_loads, g_warps, g_warps_refused); }

static int m_warp(const dcql_menu_row_t* r, int v, void* u)
{
    (void) r;
    (void) v;
    char why[64] = "";
    const int i = (int) (intptr_t) u;
    if (plant_warp(i, why)) { dcql_menu_log(why); return 0; }
    g_warps++;
    e1_log("E1 QL warp %s requested from the menu at tick %lu\n", PRESETS[i].id, (unsigned long) e1_tick);
    return 1;   // close: the loop's loading state runs next
}

static const dcql_menu_row_t SCENE[] = {
    DCQL_MENU_HEAD("RE4 engine"),
    DCQL_MENU_INFO("Image", i_image, 0),
    DCQL_MENU_INFO("Room", i_room, 0),
    DCQL_MENU_INFO("Leon (mm)", i_leon, 0),
    DCQL_MENU_INFO("Enemies alive", i_enemies, 0),
    DCQL_MENU_INFO("Tick", i_tick, 0),
    DCQL_MENU_INFO("Room loads", i_loads, 0),
    DCQL_MENU_INFO("Disc", i_disc, 0),
    DCQL_MENU_INFO("Files in play", i_guard, 0),
};
static const dcql_menu_row_t TIMING[] = {
    DCQL_MENU_HEAD("Picture (this run; tier of the machine)"),
    DCQL_MENU_INFO("Last", i_last, 0),
    DCQL_MENU_INFO("Mean", i_mean, 0),
    DCQL_MENU_INFO("Worst", i_worst, 0),
    DCQL_MENU_INFO("Over two fields", i_over, 0),
    DCQL_MENU_GAP,
    DCQL_MENU_HEAD("Drawing (row 14 ms)"),
    DCQL_MENU_INFO("Last", i_dlast, 0),
    DCQL_MENU_INFO("Mean", i_dmean, 0),
    DCQL_MENU_INFO("Worst", i_dworst, 0),
};
static const dcql_menu_row_t WARP[] = {
    DCQL_MENU_HEAD("Warp (the loop's room loading)"),
    DCQL_MENU_ACTION("Village: route start", "r101", m_warp, (void*) 0),
    DCQL_MENU_ACTION("Village: the square", "r101", m_warp, (void*) 1),
    DCQL_MENU_ACTION("Farm entry", "r103", m_warp, (void*) 2),
    DCQL_MENU_ACTION("Village: farm gate", "r101", m_warp, (void*) 3),
    DCQL_MENU_ACTION("Hill path (Leon alone)", "r11d", m_warp, (void*) 4),
};
static const dcql_menu_row_t SNAP[] = {
    DCQL_MENU_INFO("room", i_room, 0),
    DCQL_MENU_INFO("leon", i_leon, 0),
    DCQL_MENU_INFO("worst", i_worst, 0),
};
static const dcql_menu_row_t LINKROWS[] = {
    DCQL_MENU_INFO("Files in play", i_guard, 0),
};

static maple_device_t* pad_dev()
{
    return maple_enum_type(0, MAPLE_FUNC_CONTROLLER);
}
static uint32_t pad_now()
{
    maple_device_t* d = pad_dev();
    if (!d) return 0;
    const cont_state_t* s = (const cont_state_t*) maple_dev_status(d);
    return s ? dcql_menu_pad(s->buttons, s->ltrig, s->rtrig) : 0;
}
static uint32_t menu_pad(void*)
{
    uint32_t b = pad_now();
    if (g_menu_until && timer_us_gettime64() >= g_menu_until) {
        g_menu_until = 0;
        dcql_menu_close();   // the PC's opening ends at its time
    }
    return b;
}

// The declaration and the command handler are set before KallistiOS's constructors bring the link up (cl_send.c's
// cl_send_start runs at the default priority, after this one): the PC subscribes as soon as the program's link is up,
// and dc-qalink sends the declaration only then (Flycast run r1: declared in main, the PC got an empty one: rows
// without phase names). Storing two pointers; nothing is sent or started here.
__attribute__((constructor(200))) static void e1_ql_declare()
{
    dcql_live_declare(DEF);
    dcql_live_on_command(on_command, 0);
}

void e1_ql_early()
{
    if (!cl_active()) return;   // booted from its own disc: nothing
    const char* a = cl_args();
    g_on = 1;
    g_t_boot = timer_us_gettime64();
    // the network disc (owner 2026-11-23: "I want to run increments of re4 from the network drive"): the main mode is
    // the whole RE4 disc served by the PC (the bridge's --disc <staged folder> --whole); with an overlay over the GDEMU
    // disc it is the secondary mode (disc timing); args disc=gd: the GDEMU disc alone
    if (!strstr(a, "disc=gd") && !strstr(a, "net=0")) {
        g_disc = dcql_disc_mount(NULL);
        dcql_disc_stats_t s;
        dcql_disc_stats(&s);
        g_disc_whole = g_disc == 0 && (s.table_flags & DCQL_DT_WHOLE);
        e1_log("E1 QL network disc: mount %d (%s), files %lu\n", g_disc,
               g_disc == 0 ? (g_disc_whole ? "the whole disc from the PC" : "the PC's changed files over the GDEMU disc") :
               g_disc == -1 ? "no link" : g_disc == -2 ? "the PC did not answer" : g_disc == -3 ? "the PC serves no disc" :
               "refused", (unsigned long) s.files);
    }
    dcql_menu_config_t mc;
    memset(&mc, 0, sizeof mc);
    mc.combo = DCQL_MENU_LT | DCQL_MENU_RT | DCQL_MENU_START;
    mc.title = "RE4DC";
    mc.snapshot = SNAP;
    mc.nsnapshot = sizeof(SNAP) / sizeof(SNAP[0]);
    mc.link_rows = LINKROWS;
    mc.nlink_rows = 1;
    dcql_menu_init(&mc);
    dcql_menu_add_page("Scene", SCENE, sizeof(SCENE) / sizeof(SCENE[0]));
    dcql_menu_add_page("Timing", TIMING, sizeof(TIMING) / sizeof(TIMING[0]));
    dcql_menu_add_page("Warp", WARP, sizeof(WARP) / sizeof(WARP[0]));
    e1_log("E1 QL layer on: live data, menu (LT+RT+START), %u warp presets, args \"%s\"\n", NPRESETS, a);
}

unsigned e1_ql_ticks(unsigned ticks)
{
    if (!g_on) return ticks;
    const char* t = strstr(cl_args(), "ticks=");
    if (!t) return ticks;
    const unsigned long n = strtoul(t + 6, 0, 10);
    // ROW lines and the fields column keep the last E1_TICKS pictures (ring buffers); 30 minutes at most
    if (n >= 1 && n <= 54000) {
        e1_log("E1 QL run length %lu ticks (the scene's own %u)\n", n, ticks);
        return (unsigned) n;
    }
    return ticks;
}

static void run_menu()
{
    g_menus++;
    const unsigned at = e1_tick;
    dcql_live_trace(2, 0, "menu open");
    e1_log("E1 QL menu opened at tick %u\n", at);
    const uint64_t t0 = timer_us_gettime64();
    const int rc = dcql_menu_stopped(menu_pad, 0);
    const uint32_t ms_open = (uint32_t) ((timer_us_gettime64() - t0) / 1000);
    e1_log("E1 QL menu closed at tick %u after %lu ms (%s)\n", at, (unsigned long) ms_open,
           rc == 0 ? "closed" : "no usable frame buffer");
    dcql_live_trace(2, 0, rc == 0 ? "menu closed" : "menu: no frame buffer");
    g_menu_until = 0;
}

int e1_ql_picture(const E1Timing& tm)
{
    if (!g_on) return 0;
    const uint64_t now = timer_us_gettime64();
    // the picture's record (copies only)
    unsigned op = 0, rd = 0;
    e1_play_files_counts(&op, &rd);
    if (!g_last_room) {   // room-entry time of the first room: from the layer's start (boot) to the first picture's end
        const uint32_t ms_boot = (uint32_t) ((now - g_t_boot) / 1000);
        e1_log("E1 QL LOADTIME first room %03x: %lu ms from boot to the first picture (disc: %s)\n",
               (unsigned) pG->room_id, (unsigned long) ms_boot, disc_name());
        dcql_live_log(DCQL_LOG_INFO, "load: first room r%03x %lu ms from boot (%s)", (unsigned) pG->room_id,
                      (unsigned long) ms_boot, disc_name());
    }
    if (pG->room_id != g_last_room) {
        if (g_last_room) {
            g_loads++;
            // room entry: the time between the last picture of the old room and this one's start, less this picture
            const uint64_t gap = now - g_t_last_end;
            const uint32_t ms_load = (uint32_t) ((gap > tm.frame_us ? gap - tm.frame_us : 0) / 1000);
            e1_log("E1 QL LOADTIME room %03x>%03x: %lu ms (disc: %s)\n", g_last_room, (unsigned) pG->room_id,
                   (unsigned long) ms_load, disc_name());
            dcql_live_log(DCQL_LOG_INFO, "load: room %03x>%03x %lu ms (%s)", g_last_room, (unsigned) pG->room_id,
                          (unsigned long) ms_load, disc_name());
            char l[40];
            snprintf(l, sizeof l, "room %03x>%03x", g_last_room, (unsigned) pG->room_id);
            dcql_live_trace(1, 0, l);
        }
        g_last_room = pG->room_id;
    }
    t_last = tm.frame_us;
    t_draw_last = tm.draw_us;
    if (t_last > t_worst) t_worst = t_last;
    if (t_draw_last > t_draw_worst) t_draw_worst = t_draw_last;
    // a paced picture is two fields (33.37 ms) and its frame time reads a little over it: count a picture that took
    // more than two fields plus 10% (36.7 ms) as over
    if (t_last > 36700) g_over++;
    t_sum += t_last;
    t_draw_sum += t_draw_last;
    t_n++;
    dcql_frame_t f;
    memset(&f, 0, sizeof f);
    f.n = e1_tick;
    f.nph = 7;
    f.phase_us[0] = tm.input_us;
    f.phase_us[1] = tm.tick_us > tm.services_us ? tm.tick_us - tm.services_us : 0;
    f.phase_us[2] = tm.services_us;
    f.phase_us[3] = tm.draw_us;
    f.phase_us[4] = tm.pvr_us;
    f.phase_us[5] = tm.wait_us;
    f.phase_us[6] = tm.frame_us;
    f.nctr = 6;
    f.ctr[0] = (int32_t) enemies_alive();
    f.ctr[1] = (int32_t) g_loads;
    f.ctr[2] = (int32_t) g_menus;
    f.ctr[3] = (int32_t) op;
    f.ctr[4] = (int32_t) rd;
    f.ctr[5] = (int32_t) g_over;
    f.room = pG->room_id;
    if (pPL) {
        f.has_pos = 1;
        f.pos[0] = pPL->pos.x;
        f.pos[1] = pPL->pos.y;
        f.pos[2] = pPL->pos.z;
    }
    g_warp_pending = -1;
    dcql_live_frame(&f);   // the PC's commands run in here (on_command)
    if (g_warp_pending >= 0) {
        g_warps++;
        char l[40];
        snprintf(l, sizeof l, "warp %s", PRESETS[g_warp_pending].id);
        dcql_live_trace(1, 0, l);
    }
    if (g_readx) {   // CONTROL: a pack read inside play (must be counted, and fail the check)
        g_readx = 0;
        file_t fd = fs_open("/cd/CROSS.PAK", O_RDONLY);
        static char b[4096];
        const int got = fd >= 0 ? (int) fs_read(fd, b, sizeof b) : -1;
        if (fd >= 0) fs_close(fd);
        e1_log("E1 QL CONTROL readx: /cd/CROSS.PAK opened and read in play at tick %lu (%d bytes)\n",
               (unsigned long) e1_tick, got);
    }
    if (g_crash) {   // the way back's exception path (dc-qalink's client reports the registers)
        g_crash = 0;
        e1_log("E1 QL forced crash at tick %lu\n", (unsigned long) e1_tick);
        e1_log_flush();
        // a trap instruction (an unhandled exception on this CPU and in Flycast; an unaligned read was not raised by
        // Flycast in run r2: the program went on)
        __builtin_trap();
    }
    // the in-game menu: the console's pad (combo) or the PC's option menu=N
    if (g_menu_secs > 0) {
        g_menu_until = timer_us_gettime64() + (uint64_t) g_menu_secs * 1000000u;
        g_menu_secs = 0;
        dcql_menu_open();
    } else if (dcql_menu_input(pad_now()) == 0) {
        g_t_last_end = timer_us_gettime64();
        return g_end;
    }
    if (dcql_menu_is_open()) run_menu();
    g_t_last_end = timer_us_gettime64();
    return g_end;
}
