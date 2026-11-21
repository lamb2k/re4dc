// guard_hooks.cpp: the old port's functions the corrections and guards reach in the hosted units, answered by the
// engine, and the guards' counts (lane eng-fix1, H-026; docs/engine/CORRECTIONS_20261121.md section 4).
//
//   re4dc_log        printf-style log line. Under RE4DC_GAME (a correction) the hosted units call it on rare paths
//                    (cManager.h createBack of an unbacked slot, em_set, emtree, pl_sub, wep02): to the engine log.
//   re4dc_em_sleep   the guard EM_READ_RETRY's EM_MUST retry (em_set.cpp emMustCreate): a progress-critical enemy (El
//                    Gigante, the r11b boat) whose create failed sleeps and is created again, without limit, as the
//                    release does. Counted: guard em_must_retry. On the engine a module is never refused for space or
//                    a disc error, so a count other than 0 means the engine refused the spawn (an unhosted kind, a
//                    missing archive, a full enemy table).
//
// The guards without a hook of their own are not counted (E1 GUARDS names them "uncounted"): EM_OK in room code
// (include/types.h, a macro: the spawn that returned 0 is skipped), R10C_SPAWN_LIVE_GUARD (r10c, a test in the room
// code), R117_EFFECT_FAILURE_SAFE (r117, a test in the room code).
//
// Quick weapon select (game setting 4, owner 2026-11-21): ON, but its code is in units the engine does not host yet
// (src/game/sscrn.cpp re4dc_qw_frame / qwTask: the sub screen and the weapon list) and in the old port's pad layer (the
// X + D-pad chord). Until the lane that hosts the items brings them it reaches nothing: a stub counted once at start-up
// so every scene summary shows it (E1 STUBCOUNT "quick weapon select ..." calls=1), never silently dead.
#include <stdarg.h>
#include <stdio.h>
#include "e1_engine.h"

extern "C" void SceSleep(int frames) __attribute__((weak));

static unsigned guard_em_must_retry;

extern "C" void re4dc_log(const char* fmt, ...)
{
    char b[160];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(b, sizeof(b), fmt, ap);
    va_end(ap);
    e1_log("E1 RE4DC_LOG %s", b);
}

extern "C" void re4dc_em_sleep(int frames)
{
    guard_em_must_retry++;
    e1_stub_hit("guard em_must_retry (EM_MUST: a required enemy was not created)", frames);
    if (SceSleep) SceSleep(frames);
}

// The scene summary's line (core/frame.cpp e1_report); the selector fails a timing scene where a count is not 0.
extern "C" void e1_guards_report(void)
{
    e1_log("E1 GUARDS em_must_retry %u; uncounted em_ok_skip r10c_spawn_live r117_beam_null\n", guard_em_must_retry);
}

namespace {
struct QuickWeaponNotHosted {
    QuickWeaponNotHosted()
    {
        e1_stub_hit("quick weapon select ON (owner), not hosted: sscrn.cpp re4dc_qw_frame, weapon list, X+D-pad chord", 0);
    }
} quick_weapon_not_hosted;
}
