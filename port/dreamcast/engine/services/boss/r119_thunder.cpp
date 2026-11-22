// r119_thunder.cpp (lane eng-e2c): the village square's thunder (room r119), native presentation. The room script's set-up
// (R119Init, hosted) starts it as a scenario task; the hut lights flash through the effect tool's callbacks.
//
// Engine form: a presentation timer. The interval (240 to 385 ticks in steps of 5) draws from the engine's presentation
// generator (eng_pres_u8): the owner's split rule, integrator ruling 2026-11-21. The original drew it from Rnd, the
// behaviour generator, so the boss's behaviour stream differs from the old game's from the task's first run (tick 1):
// the split's known and accepted consequence, as for the Ganado's voices. Each thunder is the same two requests as the
// original's (the effect setter's flash, effect kind 1, and the thunder sound). The two hut lights are one table (light
// record, intensity at rest, intensity in each of the effect tool's two flash states).
// r119.cpp's three static functions are replaced by symbol through r119_weak.h (force-included into the hosted unit).
#define fabsf e2c_game_fabsf
#include "types.h"
#include "global.h"
#include "light.h"
#include "esp.h"
#include "sce.h"
#undef fabsf
#include "boss_svc.h"

extern "C" unsigned char eng_pres_u8();   // the engine's presentation generator (host/e1_wraps.cpp)
extern "C" void SceSleep(int frames);
extern "C" void SceSndCallThunder();

#define E2C_STR2(x) #x
#define E2C_STR(x) E2C_STR2(x)
#define E2C_SYM(name) asm(E2C_STR(__USER_LABEL_PREFIX__) #name)
extern "C" {
void eng_r119_thunder(void) E2C_SYM(_ZL16r119_ThunderMovev);
void eng_r119_flash_on(void) E2C_SYM(_ZL18r119_ThunderFlagOnv);
void eng_r119_flash_off(void) E2C_SYM(_ZL19r119_ThunderFlagOffv);
}

namespace {
struct HutLight {
    u32 record;      // the light table's record
    f32 rest;        // intensity between flashes
    f32 flash[2];    // intensity in the effect tool's flash states 1 and 2
};
const HutLight kHut[2] = {{2, 0.509f, {1.5f, 1.0f}}, {6, 0.897f, {1.5f, 0.95f}}};

int interval()
{
    boss_cnt.thunder_draws++;
    return (int) (eng_pres_u8() % 30) * 5 + 240 + (boss_control == 9 ? 5 : 0);   // control bossthunder
}
}   // namespace

extern "C" void eng_r119_flash_on(void)
{
    const u8 s = EffGetToolState();
    if (s != 1 && s != 2) return;
    for (const HutLight& h : kHut) LightMgr.getWorkPtr(h.record)->Intensity = h.flash[s - 1];
    boss_cnt.thunder_flashes++;
}

extern "C" void eng_r119_flash_off(void)
{
    for (const HutLight& h : kHut) LightMgr.getWorkPtr(h.record)->Intensity = h.rest;
}

// The task: a tick's wait, then a thunder whenever the interval runs out (flash and sound), the next interval drawn.
extern "C" void eng_r119_thunder(void)
{
    SceSleep(1);
    int left = interval();
    EffSetToolStateCallBack(0, eng_r119_flash_on, eng_r119_flash_off);
    for (;;) {
        if (left == 0) {
            EstSet(0, -1, 0, 0, 1, 0, 1, 0, 0, 0);
            left = interval();
            SceSndCallThunder();
            boss_cnt.thunders++;
        }
        left--;
        SceSleep(1);
    }
}
