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
#include <stdarg.h>
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
static char log_buf[48 * 1024];
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

// ---- stubs into other behaviour: first 4 calls of each logged with the tick, every call counted ----
struct StubCount { const char* name; unsigned calls; unsigned first_tick; };
static StubCount stubs[160];
static unsigned nstubs;
extern "C" void e1_stub_hit(const char* name, int arg)
{
    unsigned i = 0;
    while (i < nstubs && stubs[i].name != name && strcmp(stubs[i].name, name)) i++;
    if (i == nstubs && nstubs < 160) stubs[nstubs++] = {name, 0, e1_tick};
    if (i < 160) {
        if (stubs[i].calls < 4) e1_log("E1 STUB %s arg=%d tick=%lu\n", name, arg, (unsigned long) e1_tick);
        stubs[i].calls++;
    }
}
extern "C" void e1_stub_report(void)
{
    for (unsigned i = 0; i < nstubs; i++)
        e1_log("E1 STUBCOUNT %s calls=%u first_tick=%u\n", stubs[i].name, stubs[i].calls, stubs[i].first_tick);
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

void e1_globals_init()
{
    memset(&Global, 0, sizeof(Global));
    memset(&System, 0, sizeof(System));
    pLog.p = &LogWork;
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
