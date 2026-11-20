// host_present.cpp (lane eng-e1d): re4ref's random numbers split as the engine image splits them (owner 2026-11-19,
// "Split it"; ENGINE_PLAN section 3). The original generator (rnd.cpp Rnd / fRand0_1 / fRand1_1) serves behaviour
// only; presentation code draws from a generator of its own: the same algorithm on its own state, starting from 0, as
// host/e1_wraps.cpp in the engine image. The presentation functions are the engine's list (game/Makefile PRESENT_*):
// eye wander (cPlayer::moveEyeNormal), the damage voice choice (PlSetDamageSe), the water shot (wepSetWaterShot), the
// scope and look-at camera sway (CameraScope::move, CameraLookAt::CameraLookAt), the cartridge (cObjRuger::setCartridge)
// and the partner's face (cSubChar::moveFace). The aim sway (PlWepLockRand) moves Leon and his shots: behaviour, on Rnd.
// Their code is moved to the section re4ref_present at build time (Makefile PRESENT_*: objcopy --rename-section, the
// code unchanged); the link wraps Rnd, fRand0_1 and fRand1_1 (-Wl,--wrap) and a draw whose caller lies in that section
// is answered here. With the split, the engine and re4ref compare without a per-tick generator feed.
// RE4_PRESENT_SPLIT=0 turns the split off (every draw from the original generator, as before this lane): the control.
#include "hostref.h"

extern "C" char* getenv(const char*);
extern "C" char __start_re4ref_present[] __attribute__((weak));
extern "C" char __stop_re4ref_present[] __attribute__((weak));

extern "C" {
unsigned host_present_draws;   // presentation draws (generator steps) over the run
}
static unsigned short prnd_state;
static int split = -1;

static inline int present_caller(void* ra)
{
    if (split < 0) {
        const char* e = getenv("RE4_PRESENT_SPLIT");
        split = !(e && e[0] == '0');
    }
    return split && (char*) ra >= __start_re4ref_present && (char*) ra < __stop_re4ref_present;
}
static unsigned char prnd()
{
    unsigned short r = prnd_state;
    unsigned n = ((unsigned char) ((r >> 1) + (r >> 8)) << 8) | (unsigned char) (r >> 1);
    unsigned m = n & 0xFFFF;
    if (m == r) m = n + 0x101;
    prnd_state = (unsigned short) m;
    host_present_draws++;
    return (unsigned char) (m >> 8);
}
static float prnd_unit()   // [1, 2) from three draws, as fRand0_1 / fRand1_1 form it
{
    unsigned a = prnd(), b = prnd(), c = prnd();
    unsigned u = a + (b << 8) + ((c & 0x7F) << 16) + 0x3F800000;
    float f;
    __builtin_memcpy(&f, &u, 4);
    return f;
}
// lane eng-svc4: the engine's presentation byte for the native services (services/input: the rumble strength); the same
// stream as the presentation callers above (the engine image: host/e1_wraps.cpp's prnd)
extern "C" unsigned char eng_pres_u8() { return prnd(); }
extern "C" unsigned char __real_Rnd();
extern "C" unsigned char __wrap_Rnd()
{
    if (present_caller(__builtin_return_address(0))) return prnd();
    return __real_Rnd();
}
extern "C" float __real_fRand1_1();
extern "C" float __wrap_fRand1_1()
{
    if (present_caller(__builtin_return_address(0))) return prnd_unit() * 2.0f - 3.0f;
    return __real_fRand1_1();
}
extern "C" float __real_fRand0_1();
extern "C" float __wrap_fRand0_1()
{
    if (present_caller(__builtin_return_address(0))) return prnd_unit() - 1.0f;
    return __real_fRand0_1();
}
