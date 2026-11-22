// E1 main-loop globals the hosted behaviour reads (lane eng-e1): the global work (pG), system work (pSys), the input
// arrays (Joy, Key), the debug log (pLog: lines go to the engine log), and the engine log / stub accounting.
#include "global.h"
#include "main.h"
#include "joy.h"
#include "db_log.h"
#include "e1_engine.h"
#include "e1_core.h"
#include "rnd.h"
#include "e1_kos.h"
#include "camera/eng_camera.h"   // lane eng-e1l: the renderer's planes and the RNEARFAR control
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

GlobalWork Global;
GlobalWork* pG = &Global;
static SystemWork System;
SystemWork* pSys = &System;
JOY Joy[4];
KeyWork Key;
static cLog LogWork;
cLogPtr pLog;

// ---- engine log: serial (printf) ----
// Lane eng-e1e (E1 audit section 5): nothing prints over serial inside the timed ticks. While the tick loop runs
// (e1_state[0] == 4) a log line goes to a RAM buffer, printed by e1_log_flush after the loop (e1_report), with the tick
// it was written at kept in the text; lines that do not fit are counted and reported.
static char log_buf[16 * 1024];
static unsigned log_len, log_dropped;
extern "C" void e1_log(const char* fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    if (e1_state[0] == 4) {
        const unsigned room = sizeof(log_buf) - log_len;
        const int n = vsnprintf(log_buf + log_len, room, fmt, ap);
        if (n >= 0 && (unsigned) n < room) log_len += (unsigned) n;
        else { log_buf[log_len] = 0; log_dropped++; }
    } else {
        vprintf(fmt, ap);
    }
    va_end(ap);
}
extern "C" void e1_log_flush(void)
{
    if (log_len) fwrite(log_buf, 1, log_len, stdout);
    printf("E1 LOGBUF %u bytes buffered during the ticks, %u lines dropped\n", log_len, log_dropped);
    log_len = 0;
}

// ---- stubs into other behaviour: every call counted, the first 4 of each with their argument and tick ----
// Lane eng-sched3 (H-043 ruling 1: stub logging is not timed work). Each stub is indexed once, at its first call, in a
// table keyed by the name's address (open addressing, STUB_SLOTS slots); a call is a hash, a compare and a count, with
// no string search and no formatting. Outside the ticks the first four calls of a stub print at once, as before;
// inside the ticks (e1_state[0] == 4) their argument and tick are kept in the entry and printed after play
// (e1_stub_report). The same text under two addresses (two units' literals) is two entries, merged by name in the
// report. e1_stub_calls counts every call (the scheduler's cost split reads it, host/sched_host.cpp).
// Lab arm STUBOLD (boot file, read before play; the comparison arm of the lane's cost pair, never a default): the
// accounting as it was before this lane (strcmp along the table on every call, the first four calls of each formatted
// into the log buffer inside the ticks).
enum { STUB_SLOTS = 256, STUB_MAX = 200 };
struct StubCount { const char* name; unsigned calls, first_tick, held; int arg[4]; unsigned tick[4]; };
static StubCount stubs[STUB_MAX];
static unsigned short stub_slot[STUB_SLOTS];   // index + 1 into stubs; 0 empty
static unsigned nstubs, stub_full;
static int stub_old;
extern "C" { unsigned e1_stub_calls; }
static StubCount* stub_new(const char* name)
{
    if (nstubs >= STUB_MAX) { stub_full++; return 0; }
    StubCount* s = &stubs[nstubs++];
    *s = {};
    s->name = name;
    s->first_tick = e1_tick;
    return s;
}
static void stub_hit_old(const char* name, int arg)   // STUBOLD: the search before lane eng-sched3
{
    unsigned i = 0;
    while (i < nstubs && stubs[i].name != name && strcmp(stubs[i].name, name)) i++;
    if (i == nstubs && !stub_new(name)) return;
    if (stubs[i].calls < 4) e1_log("E1 STUB %s arg=%d tick=%lu\n", name, arg, (unsigned long) e1_tick);
    stubs[i].calls++;
}
extern "C" void e1_stub_hit(const char* name, int arg)
{
    e1_stub_calls++;
    if (stub_old) { stub_hit_old(name, arg); return; }
    unsigned h = ((unsigned) (uintptr_t) name >> 2) * 2654435761u >> 24;   // STUB_SLOTS 256: the top 8 bits
    StubCount* s;
    for (;;) {
        const unsigned k = stub_slot[h];
        if (!k) {
            if (!(s = stub_new(name))) return;
            stub_slot[h] = (unsigned short) nstubs;
            break;
        }
        s = &stubs[k - 1];
        if (s->name == name) break;
        h = (h + 1) & (STUB_SLOTS - 1);
    }
    if (s->calls < 4) {
        if (e1_state[0] == 4) { s->arg[s->held] = arg; s->tick[s->held] = e1_tick; s->held++; }
        else e1_log("E1 STUB %s arg=%d tick=%lu\n", name, arg, (unsigned long) e1_tick);
    }
    s->calls++;
}
extern "C" void e1_stub_report(void)
{
    // after play: the first calls kept during the ticks, then one count line a name (entries of the same text merged)
    for (unsigned i = 0; i < nstubs; i++)
        for (unsigned j = 0; j < stubs[i].held; j++)
            e1_log("E1 STUB %s arg=%d tick=%u\n", stubs[i].name, stubs[i].arg[j], stubs[i].tick[j]);
    for (unsigned i = 0; i < nstubs; i++) {
        unsigned calls = stubs[i].calls, first = stubs[i].first_tick, dup = 0;
        for (unsigned j = 0; j < i && !dup; j++) dup = !strcmp(stubs[j].name, stubs[i].name);
        if (dup) continue;
        for (unsigned j = i + 1; j < nstubs; j++)
            if (!strcmp(stubs[j].name, stubs[i].name)) {
                calls += stubs[j].calls;
                if (stubs[j].first_tick < first) first = stubs[j].first_tick;
            }
        e1_log("E1 STUBCOUNT %s calls=%u first_tick=%u\n", stubs[i].name, calls, first);
    }
    e1_log("E1 STUB accounting: %s, %u names indexed, %u calls, %u not counted (table full)\n",
           stub_old ? "STUBOLD (strcmp search, formatted in the ticks: lab arm)" : "indexed at the first call",
           nstubs, e1_stub_calls, stub_full);
}

// ---- debug log (db_log.cpp), engine form: every line to the engine log ----
static void logline(const char* kind, const char* fmt, va_list ap)
{
    char b[160];
    vsnprintf(b, sizeof(b), fmt, ap);
    e1_log("E1 %s %s (tick %lu)\n", kind, b, (unsigned long) e1_tick);
}
void cLog::mes(int, int, const char* fmt, ...) { va_list ap; va_start(ap, fmt); logline("LOGMES", fmt, ap); va_end(ap); }
void cLog::err(int, int, const char* fmt, ...) { va_list ap; va_start(ap, fmt); logline("LOGERR", fmt, ap); va_end(ap); }
void cLog::warn(int, int, const char* fmt, ...) { va_list ap; va_start(ap, fmt); logline("LOGWARN", fmt, ap); va_end(ap); }
void cLog::vmes(int, int, const char* fmt, va_list ap) { logline("LOGMES", fmt, ap); }
void cLog::verr(int, int, const char* fmt, va_list ap) { logline("LOGERR", fmt, ap); }
void cLog::vwarn(int, int, const char* fmt, va_list ap) { logline("LOGWARN", fmt, ap); }
extern "C" void OSReport(const char* fmt, ...) { va_list ap; va_start(ap, fmt); logline("OSREPORT", fmt, ap); va_end(ap); }

// ---- the game's projection constants (main.cpp systemScreenInit, lane eng-e1l) ----
// Game state the hosted behaviour and the camera service read: the near and far distances (the shoulder camera's wall
// probe width and near offset, cam_eval.cpp; the water clamp, cam_ctrl.cpp; the view frustum and its bounding sphere,
// camera_svc.cpp VIEW) and the orthographic bounds. They are the original's values, set where the engine sets up the
// game's globals. They are not the renderer's planes: those are the camera record's own constants (eng_camera.h
// ENG_RENDERER_NEAR / ENG_RENDERER_FAR, 18,750, never 1,000,000).
// Lab arm ZCLIP0 (boot file): ZNEAR and ZFAR stay zero, as every E1 image had them before this lane (control of the
// camera comparison, hostref/svc/camengine.sh). Not a build switch.
f32 ZNEAR, ZFAR, ORTHO_T, ORTHO_B, ORTHO_L, ORTHO_R;
static void projection_init()
{
    ZNEAR = 100.0f;
    ZFAR = 1000000.0f;
    ORTHO_T = 240.0f;
    ORTHO_B = -240.0f;
    ORTHO_L = -320.0f;
    ORTHO_R = 320.0f;
    file_t f = fs_open("/cd/ZCLIP0", O_RDONLY);
    if (f >= 0) {
        fs_close(f);
        ZNEAR = ZFAR = 0.0f;
        e1_log("E1 ZCLIP0: the game's near and far distances left at zero (lab arm, control)\n");
    }
    // RNEARFAR (boot file, control of the record's finite check): the renderer's far plane equals its near
    f = fs_open("/cd/RNEARFAR", O_RDONLY);
    if (f >= 0) {
        fs_close(f);
        eng_cam_nearfar_control = 1;
        e1_log("E1 RNEARFAR: the renderer's far plane set to its near (control: the record's depth terms not finite)\n");
    }
    e1_log("E1 PROJECTION game ZNEAR %d ZFAR %d; renderer near %d far %d (the camera record's)\n", (int) ZNEAR, (int) ZFAR,
           (int) ENG_RENDERER_NEAR, (int) (eng_cam_nearfar_control ? ENG_RENDERER_NEAR : ENG_RENDERER_FAR));
}

void e1_globals_init()
{
    memset(&Global, 0, sizeof(Global));
    memset(&System, 0, sizeof(System));
    pLog.p = &LogWork;
    projection_init();
    file_t f = fs_open("/cd/STUBOLD", O_RDONLY);   // lane eng-sched3: the stub accounting's comparison arm (above)
    if (f >= 0) { fs_close(f); stub_old = 1; e1_log("E1 STUBOLD: the stub accounting before lane eng-sched3 (lab arm)\n"); }
}

// The warp rig's flags (dbgwarp_bridge.cpp start / "flags applied"): room, first-visit flag, and the r101 room
// flags of the reference fixture (rsf 0x101 7 10: after the bell, terminal done). Behaviour reads them at room init.
void e1_room_globals(const E1Route& r)
{
    pG->room_id = r.room;
    pG->pl_type = 0;
    pG->pl_costume = 0;
    pG->Item_find_flg |= r.find;
    pSys->region = 1;
    pG->game_mode = 5;          // gameInit: a new game
    pG->mot_speed = 1.0f;       // gameInit: the global motion speed
    pG->System_flg |= 0x800;    // gameRoomInit (Debug_flg[3] bit 27 off); the reference trace reads sy=00000800
    // Boot options (empty files in the disc root), for the plays-right controls:
    //   CTRLSPD  the global motion speed 0.97 instead of 1.0: every motion, the walk included, runs 3% slow (must fail)
    //   SEED     the shared generator starts from 0x5A5A instead of 0 (shows which fields depend on its draws)
    file_t f = fs_open("/cd/CTRLSPD", O_RDONLY);
    if (f >= 0) { fs_close(f); pG->mot_speed = 0.97f; e1_log("E1 CONTROL: motion speed 0.97\n"); }
    f = fs_open("/cd/SEED", O_RDONLY);
    if (f >= 0) { fs_close(f); RndInit(0x5A5A); e1_game_seed_option = 1; e1_log("E1 SEED: generator 5a5a\n"); }
}
int e1_game_seed_option;
