// Per-subsystem frame timing for real hardware (GAME_TICK_LOG=N in game30.mk; default off).
//
// The game already stamps its frame with ProcessTickGet(no, name) (debug.cpp: proc_tick[32],
// OSGetTick = timer_us_gettime64 scaled to 40.5 MHz, relative to the frame start): 4 RENDER SETUP;
// then in call order CamCtrl.Check, ScenarioMove, EmMgr.move, Player, ObjMgr.move, CameraMove,
// EspMove, LightMove (game.cpp), TaskScheduler (main.cpp), EspTrans, ShadowTrans, MirrorTrans,
// ClothTrans, objTrans (trans.cpp), SndWatcher; 2 PROCESS CPU, 1 RENDER END, 3 DRAW REMAIN,
// 0 PROCESS TOTAL. At the end of every frame (after PROCESS TOTAL) main.cpp hands the sealed array
// here. Every N frames:
//
//  * log lines through re4dc_log (RAM log ring read by the emulator tooling; also stdout, i.e. the
//    dcload/serial console, when re4dc_log_console is set). re4dc_log truncates at 256 bytes, so a
//    window is split into lines of at most ~200 characters, all starting with the same window tag:
//      PT f=<first>-<last> n=<frames> total=<avg>/<max> setup=... CamCtrl.Check=... EmMgr.move=...
//      PT f=<first>-<last> ... objTrans=... cpu=... end=... remain=... logic=... trans=... post=... rotcache=<hits>/<misses>
//    values in microseconds, avg/max over the window (avg/max/count when a marker was not stamped
//    in every frame);
//  * a sealed snapshot of the same window for an on-screen readout (GDEMU consoles have no
//    serial): re4dc_tick_log_snapshot() below. It draws nothing itself; the frame-pipeline
//    PERF_HUD (or any debug bar display) reads it, e.g. the logic / trans / post group bars
//    (logic = RENDER SETUP..TaskScheduler, trans = ..SndWatcher, post = ..PROCESS CPU).
//
// Sequential markers (index >= 5) are reported as the delta from the previous marker, so each value
// is the time spent in the phase that the marker closes. Observation only: reads the tick array,
// writes only this file's statics; costs one short loop per frame and a few formatted lines per
// window. Game logic, RNG and frame sequencing are untouched.
#include "re4dc_platform.h"
#include <stdio.h>
#include <string.h>

#ifndef RE4DC_TICK_LOG
#define RE4DC_TICK_LOG 30
#endif

// Optional counters of other game30 knobs (weak: absent unless that knob is built in).
extern "C" unsigned long re4dc_rot_cache_hits __attribute__((weak));
extern "C" unsigned long re4dc_rot_cache_misses __attribute__((weak));
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
#include <arch/timer.h>
extern "C" void re4dc_world_meter_take(unsigned* us_out, unsigned* vtx_out);   // platform/native_static.cpp
extern "C" void re4dc_vram_fail_drain(unsigned room);   // platform/vram_pages.cpp
extern "C" unsigned re4dc_wm_room(void);                  // dbgwarp_bridge.cpp
#endif
#if RE4DC_PWC_DIAG_LOG   // GAME_PWC_DIAG=2 check builds only
extern "C" unsigned long re4dc_pwc_diag_checks __attribute__((weak));
extern "C" unsigned long re4dc_pwc_diag_mismatch __attribute__((weak));
#endif

namespace {
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
constexpr int kSlots = 40;   // WORLD_METER: 7 more slots
#else
constexpr int kSlots = 32;
#endif
constexpr unsigned kTicksPerUs10 = 405;   // 40.5 ticks per microsecond, x10
struct Slot { const char* name; unsigned long long sum; unsigned max; unsigned n; };
Slot g_slots[kSlots];
unsigned g_first, g_frames;

// Sealed copy of the last complete window (for on-screen readouts).
const char* g_snapName[kSlots];
unsigned g_snapAvg[kSlots], g_snapMax[kSlots];
int g_snapCount;
unsigned g_snapSeq;

unsigned us(unsigned ticks) { return (unsigned) ((unsigned long long) ticks * 10u / kTicksPerUs10); }

void add(const char* name, unsigned ticks)
{
    int i;
    for (i = 0; i < kSlots && g_slots[i].name; i++)
        if (g_slots[i].name == name) break;
    if (i == kSlots) return;
    Slot& s = g_slots[i];
    s.name = name;
    const unsigned v = us(ticks);
    s.sum += v;
    if (v > s.max) s.max = v;
    s.n++;
}
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
void add_us(const char* name, unsigned v)   // a value already in us (or a count)
{
    int i;
    for (i = 0; i < kSlots && g_slots[i].name; i++)
        if (g_slots[i].name == name) break;
    if (i == kSlots) return;
    Slot& s = g_slots[i];
    s.name = name;
    s.sum += v;
    if (v > s.max) s.max = v;
    s.n++;
}
#endif

// Appends one field; flushes the current line first when it would pass the line budget.
struct Line {
    char buf[224];
    int n = 0, fields = 0;
    char head[40];
    void flush()
    {
        if (fields) re4dc_log("%s%s\n", head, buf);
        n = 0; fields = 0; buf[0] = 0;
    }
    void field(const char* text)
    {
        int len = 0;
        while (text[len]) len++;
        if (fields && n + len >= 200) flush();
        if (n + len >= (int) sizeof(buf)) return;
        for (int k = 0; k <= len; k++) buf[n + k] = text[k];
        n += len;
        fields++;
    }
};
}  // namespace

extern "C" __attribute__((section(".text.re4dc_tick_log"))) void re4dc_tick_log_frame(const unsigned long* ticks, const char* const* names, int count, unsigned frame)
{
    static const char kTotal[] = "total", kSetup[] = "setup", kCpu[] = "cpu", kEnd[] = "end", kRemain[] = "remain";
    if (g_frames == 0) g_first = frame;
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
    // WORLD_METER (game30.mk): the PS2 world passes this tick (us, vertices; native_static.cpp) and the wall time since the
    // previous tick's log call (the whole iteration, pacing wait and Render_before included), as raw us slots.
    {
        static const char kWopq[] = "wopq", kWxlu[] = "wxlu", kWshell[] = "wshell", kWall[] = "wall", kVopq[] = "vopq",
                          kVxlu[] = "vxlu", kVshell[] = "vshell";
        static unsigned long long last_us;
        unsigned u[3], v[3];
        re4dc_world_meter_take(u, v);
        const unsigned long long now = timer_us_gettime64();
        const unsigned wall = last_us ? unsigned(now - last_us) : 0;
        last_us = now;
        add_us(kWopq, u[0]); add_us(kWxlu, u[1]); add_us(kWshell, u[2]); add_us(kWall, wall);
        add_us(kVopq, v[0]); add_us(kVxlu, v[1]); add_us(kVshell, v[2]);
        re4dc_vram_fail_drain(re4dc_wm_room());
    }
#endif
    add(kTotal, ticks[0]);
    add(kSetup, ticks[4]);
    unsigned prev = ticks[4];
    for (int i = 5; i < count && i < kSlots; i++) {
        if (!names[i]) continue;
        add(names[i], ticks[i] - prev);
        prev = ticks[i];
    }
    add(kCpu, ticks[2]);
    add(kEnd, ticks[1]);
    add(kRemain, ticks[3]);
    // Groups for a 3-bar readout: logic = RENDER SETUP .. TaskScheduler (every game.cpp move phase
    // and the task threads), trans = .. SndWatcher (IdSys, Trans(): Esp/Shadow/Mirror/Cloth/objTrans,
    // Dvd, sound), post = .. PROCESS CPU (messages, fades, cinesco, OT draw, debug print).
    static const char kLogic[] = "logic", kTrans[] = "trans", kPost[] = "post";
    int iTask = -1, iSnd = -1;
    for (int i = 5; i < count && i < kSlots; i++) {
        if (!names[i]) continue;
        if (!strcmp(names[i], "TaskScheduler")) iTask = i;
        else if (!strcmp(names[i], "SndWatcher")) iSnd = i;
    }
    if (iTask > 0 && iSnd > iTask) {
        add(kLogic, ticks[iTask] - ticks[4]);
        add(kTrans, ticks[iSnd] - ticks[iTask]);
        add(kPost, ticks[2] - ticks[iSnd]);
    }
    if (++g_frames < (unsigned) RE4DC_TICK_LOG) return;

    Line line;
    snprintf(line.head, sizeof(line.head), "PT f=%u-%u n=%u", g_first, frame, g_frames);
    int c = 0;
    for (int i = 0; i < kSlots && g_slots[i].name; i++, c++) {
        const Slot& s = g_slots[i];
        const unsigned avg = s.n ? (unsigned) (s.sum / s.n) : 0;
        char tag[24], text[64];
        int k = 0;
        while (s.name[k] && s.name[k] != ' ' && s.name[k] != '(' && k < 23) { tag[k] = s.name[k]; k++; }  // "EmMgr.move" etc.
        tag[k] = 0;
        if (s.n == g_frames) snprintf(text, sizeof(text), " %s=%u/%u", tag, avg, s.max);
        else snprintf(text, sizeof(text), " %s=%u/%u/%u", tag, avg, s.max, s.n);
        line.field(text);
        g_snapName[i] = s.name;
        g_snapAvg[i] = avg;
        g_snapMax[i] = s.max;
    }
    g_snapCount = c;
    g_snapSeq++;
    if (&re4dc_rot_cache_hits && &re4dc_rot_cache_misses) {
        static unsigned long lastHits, lastMisses;
        char text[48];
        snprintf(text, sizeof(text), " rotcache=%lu/%lu", re4dc_rot_cache_hits - lastHits,
                 re4dc_rot_cache_misses - lastMisses);
        line.field(text);
        lastHits = re4dc_rot_cache_hits;
        lastMisses = re4dc_rot_cache_misses;
    }
#if RE4DC_PWC_DIAG_LOG
    if (&re4dc_pwc_diag_checks && &re4dc_pwc_diag_mismatch) {
        char text[48];
        snprintf(text, sizeof(text), " pwcdiag=%lu/%lu", re4dc_pwc_diag_checks, re4dc_pwc_diag_mismatch);
        line.field(text);
    }
#endif
    line.flush();
    for (auto& s : g_slots) s = Slot{};
    g_frames = 0;
}

// Last complete window: fills up to `max` entries (name as passed to ProcessTickGet, or "total",
// "setup", "cpu", "end", "remain", "logic", "trans", "post"; mean and max in microseconds) and returns the entry count.
// *seq (optional) increments once per window, so a readout can tell a fresh window from a repeat.
// Weak-reference it from a HUD: `extern "C" int re4dc_tick_log_snapshot(...) __attribute__((weak));`
// (shares its input section with re4dc_tick_log_frame, so --gc-sections keeps it whenever
// GAME_TICK_LOG is on and a weak reference finds it).
extern "C" __attribute__((section(".text.re4dc_tick_log"))) int re4dc_tick_log_snapshot(const char** name, unsigned* avg_us, unsigned* max_us, int max, unsigned* seq)
{
    const int n = g_snapCount < max ? g_snapCount : max;
    for (int i = 0; i < n; i++) {
        if (name) name[i] = g_snapName[i];
        if (avg_us) avg_us[i] = g_snapAvg[i];
        if (max_us) max_us[i] = g_snapMax[i];
    }
    if (seq) *seq = g_snapSeq;
    return n;
}
