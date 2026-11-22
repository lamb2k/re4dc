// r101_voice.cpp (lane eng-e2f): the village square's Ganado voices before the fight (room r101), native presentation.
// The room script (R101Main, hosted) arms area 0x13 with the voices as a scenario task (SceAtDataSet_exec); the task
// calls a voice from the square until the fight's room flag (6) is set.
//
// Engine form: a presentation loop on the sound entry point. Each voice is one of the square's ten (sound bank 6),
// never the same twice running, from the square's centre; the wait between two is 75 to 120 ticks. Both draws come from
// the engine's presentation generator (eng_pres_u8): the owner's split rule (voices are presentation), as lane eng-e2c's
// thunder. The original drew them from Rnd, the behaviour generator, so the fight's behaviour stream no longer carries
// these draws (the PC reference hosts no room script: its stream never did). The sound request is the original's.
// r101.cpp's function is static: fight/r101_weak.h (force-included into the hosted unit) makes it a weak global, and
// this strong body takes its place by symbol (game/fight.mk; R101_VOICE_ORIG=1, a control build, keeps the original).
#define fabsf e2f_game_fabsf
#include "types.h"
#include "global.h"
#include "flag_rsf.h"
#include "snd.h"
#include "sce.h"
#undef fabsf

extern "C" unsigned char eng_pres_u8();   // the engine's presentation generator (host/e1_wraps.cpp)

#define E2F_STR2(x) #x
#define E2F_STR(x) E2F_STR2(x)
#define E2F_SYM(name) asm(E2F_STR(__USER_LABEL_PREFIX__) #name)
extern "C" void eng_r101_voice(void) E2F_SYM(_ZL20r101_callGanadoVoicev);
extern "C" unsigned r101_voice_cnt;
unsigned r101_voice_cnt;

namespace {
const Vec kSquare = {-5356.0f, 1000.0f, 3250.0f};   // where the voices come from
constexpr int kVoices = 10;
}   // namespace

extern "C" void eng_r101_voice(void)
{
    int last = -1;
    while (!RsfCheck(G_ROOM_ID, 6)) {
        int v;
        do v = eng_pres_u8() % kVoices;
        while (v == last);
        last = v;
        r101_voice_cnt++;
        Vec at = kSquare;
        SndCall(6, (u16) v, &at, 0, 0, 0);
        SceSleep(eng_pres_u8() * 45 / 255 + 75);
    }
}
