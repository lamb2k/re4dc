// E1 main-loop globals the hosted behaviour reads (lane eng-e1): the global work (pG), system work (pSys), the input
// arrays (Joy, Key), the debug log (pLog: lines go to the engine log), and the engine log / stub accounting.
#include "global.h"
#include "main.h"
#include "joy.h"
#include "db_log.h"
#include "e1_engine.h"
#include "e1_core.h"
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
extern "C" void e1_log(const char* fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
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
}
