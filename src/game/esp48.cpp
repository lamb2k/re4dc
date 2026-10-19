// game/esp48.cpp: effect id 0x48, a sprite whose rotation oscillates: each axis swings by a sine of
// its own amplitude (Vec0/1/2.x in 10ths) and frequency (Vec0/1/2.y) around the base rotation.

#include "atari.h"
#include "rnd.h"
#include "math_sub.h"
#include "esp.h"

struct Esp48Work {
    f32 dist_x;    // 0x00
    f32 time_x;   // 0x04
    f32 dist_y;    // 0x08
    f32 time_y;   // 0x0C
    f32 dist_z;    // 0x10
    f32 time_z;   // 0x14
    f32 timer;    // 0x18
    Vec add_ang;   // 0x1C rotation added this frame
#if defined(RE4DC_FX_MIST_PS2) && RE4DC_FX_MIST_PS2
    u32 dormant;   // 0x28 FX_MIST_PS2: a GC-only sheet kept in its slot, never moved (esp_sub.cpp EspSeqSet)
#endif
};

// Effect whose rotation swings on a sine wave around the base rotation.
class cEsp48 : public cEsp {
public:
    Esp48Work m_Free;  // 0xF8

    virtual void move();
    virtual int SetFreeWork(EspGenWork* gen, u32* seed);
#if defined(RE4DC_FX_MOVE) && RE4DC_FX_MOVE == 2
    void moveSrc();   // GAME_FX_MOVE=2: the source move beside the kernel
#endif
};

// EspCreateTbl[0x48] factory.
cEsp* Esp48_Create()
{
    return new cEsp48;
}
#if defined(RE4DC_FX_MIST_PS2) && RE4DC_FX_MIST_PS2
static_assert(sizeof(cEsp48) <= 0x150, "cEsp48 fits a pool slot");
// FX_MIST_PS2 (hwfog.mk): PullEsp zeroes a slot, so a new sheet starts awake.
extern "C" void re4dc_esp48_dormant(cEsp* esp)
{
    static_cast<cEsp48*>(esp)->m_Free.dormant = 1;
}
extern "C" int re4dc_esp48_is_dormant(const cEsp* esp)
{
    return static_cast<const cEsp48*>(esp)->m_Free.dormant != 0;
}
#define FX48_DORMANT_RETURN() \
    if (m_Free.dormant) {     \
        return;               \
    }
#else
#define FX48_DORMANT_RETURN()
#endif

// Removes last frame's swing from m_Ang, runs the base update, advances the timer by 0.01 and adds
// the new per-axis sine offsets. Released when the animation ends.
#if defined(RE4DC_FX_MOVE) && RE4DC_FX_MOVE
// GAME_FX_MOVE (esp.h): the same operations with the fields read through walking pointers.
#if RE4DC_FX_MOVE == 2
extern "C" int re4dc_fx_common_kernel(cEsp* e);   // esp_sub.cpp: CommonMove without its pushes
extern "C" int re4dc_fx_anm_kernel(cEsp* e, int quiet);
#define FX48_COMMON(e, pure) ((pure) ? re4dc_fx_common_kernel(e) == 0 : (e)->CommonMove() != 0)
#else
#define FX48_COMMON(e, pure) ((e)->CommonMove() != 0)
#endif
// sinf(x): the fdlibm sinf (game30_trig.c / the GAME_FDLIBM one) returns x itself for |x| < 2^-27
// (k_sinf's first test, reached through sinf's |x| <= pi/4 branch), so those arguments skip the call
// (+-0 included: effects with a zero frequency, all of them in the square).
static inline f32 fx48Sin(f32 x)
{
    union {
        f32 f;
        u32 u;
    } v;
    v.f = x;
    if ((v.u & 0x7FFFFFFFu) < 0x32000000u) {
        return x;
    }
    return sinf(x);
}
// The move up to AnmMove: 1 when CommonMove kept the effect. pure: CommonMove's kernel (a =2 copy,
// never pushed) in place of the member.
static inline __attribute__((always_inline)) int fx48Kernel(cEsp48* e, int pure)
{
    Esp48Work* w = &e->m_Free;
    f32 gx, gy, gz, ax, ay, az;
    f32* q = &e->m_Ang.x;

    FXL(q, gx);
    FXL(q, gy);
    FXL(q, gz);
    q = &w->add_ang.x;
    FXL(q, ax);
    FXL(q, ay);
    FXL(q, az);
    gx = gx - ax;
    gy = gy - ay;
    gz = gz - az;
    q = &e->m_Ang_plus.x;
    FXS(q, gz);
    FXS(q, gy);
    FXS(q, gx);
    if (FX48_COMMON(e, pure)) {
        f32 dx, dy, dz, t, s0, s1, s2;
        t = w->timer + 0.01f;
        w->timer = t;
        s0 = fx48Sin(t * w->time_x);
        s1 = fx48Sin(t * w->time_y);
        s2 = fx48Sin(t * w->time_z);
        q = &w->dist_x;   // dist_x, time_x, dist_y, time_y, dist_z
        FXL(q, dx);
        q++;
        FXL(q, dy);
        q++;
        FXL(q, dz);
        ax = dx * s0;
        ay = dy * s1;
        az = dz * s2;
        q = &w->add_ang.z + 1;
        FXS(q, az);
        FXS(q, ay);
        FXS(q, ax);
        q = &e->m_Ang.x;
        FXL(q, gx);
        FXL(q, gy);
        FXL(q, gz);
        gx = gx + ax;
        gy = gy + ay;
        gz = gz + az;
        FXS(q, gz);
        FXS(q, gy);
        FXS(q, gx);
        return 1;
    }
    return 0;
}
#if RE4DC_FX_MOVE == 2
#include <string.h>
extern "C" void re4dc_log(const char* fmt, ...);
static u32 fx48Calls, fx48Mis, fx48Zero, fx48TimeSame, fx48Same, fx48Tiny;
static inline u32 fx48Bits(f32 f)
{
    union {
        f32 f;
        u32 u;
    } v;
    v.f = f;
    return v.u;
}
static inline int fx48Tiny1(f32 a)
{
    return (fx48Bits(a) & 0x7FFFFFFF) < 0x32000000;
}
#endif
void cEsp48::move()
{
    FX48_DORMANT_RETURN();
#if RE4DC_FX_MOVE == 2
    // The source move runs live and the kernel on a copy; the copy must match while the effect
    // lives, and die when it dies. A census of the swing parameters rides along.
    u32 copy[sizeof(cEsp48) / 4 + 1];
    cEsp48* c = (cEsp48*) copy;
    Esp48Work* w = &m_Free;
    int alive;
    memcpy(copy, this, sizeof(cEsp48));
    fx48Calls++;
    if (fx48Bits(w->dist_x) << 1 == 0 || fx48Bits(w->dist_y) << 1 == 0 || fx48Bits(w->dist_z) << 1 == 0) {
        fx48Zero++;
    }
    if (fx48Bits(w->time_x) == fx48Bits(w->time_y) || fx48Bits(w->time_y) == fx48Bits(w->time_z) ||
        fx48Bits(w->time_x) == fx48Bits(w->time_z)) {
        fx48TimeSame++;
    }
    {
        f32 t = w->timer + 0.01f;
        f32 x = t * w->time_x;
        f32 y = t * w->time_y;
        f32 z = t * w->time_z;
        if (fx48Bits(x) == fx48Bits(y) || fx48Bits(y) == fx48Bits(z) || fx48Bits(x) == fx48Bits(z)) {
            fx48Same++;
        }
        fx48Tiny += fx48Tiny1(x) + fx48Tiny1(y) + fx48Tiny1(z);   // sinf calls skipped
        if (fx48Tiny1(x) && fx48Bits(sinf(x)) != fx48Bits(x)) {
            fx48Mis++;   // the fdlibm small-argument identity must hold bit for bit
        }
    }
    alive = fx48Kernel(c, 1) && re4dc_fx_anm_kernel(c, 1);
    moveSrc();
    if (alive != ((m_Be_flg & 1) != 0) || (alive && memcmp(copy, this, sizeof(cEsp48)) != 0)) {
        fx48Mis++;
    }
    if (fx48Calls % 8192 == 0) {
        re4dc_log("FX48 calls=%u mismatch=%u zero_dist=%u same_time=%u same_arg=%u tiny_axes=%u\n", fx48Calls,
                  fx48Mis, fx48Zero, fx48TimeSame, fx48Same, fx48Tiny);
    }
#else
    if (fx48Kernel(this, 0)) {
        if (!AnmMove()) {
            PushEsp(this);
        }
    }
#endif
}
#endif
#if !(defined(RE4DC_FX_MOVE) && RE4DC_FX_MOVE) || RE4DC_FX_MOVE == 2
#if defined(RE4DC_FX_MOVE) && RE4DC_FX_MOVE == 2
void cEsp48::moveSrc()
#else
void cEsp48::move()
#endif
{
    Esp48Work* w = &m_Free;

#if !(defined(RE4DC_FX_MOVE) && RE4DC_FX_MOVE == 2)
    FX48_DORMANT_RETURN();
#endif
    PSVECSubtract(&m_Ang, &w->add_ang, &m_Ang);
    if (CommonMove()) {
        w->timer += 0.01f;
        w->add_ang.x = w->dist_x * sinf(w->timer * w->time_x);
        w->add_ang.y = w->dist_y * sinf(w->timer * w->time_y);
        w->add_ang.z = w->dist_z * sinf(w->timer * w->time_z);
        PSVECAdd(&m_Ang, &w->add_ang, &m_Ang);
        if (!AnmMove()) {
            PushEsp(this);
        }
    }
}
#endif

// Amplitudes (x 0.1) and frequencies per axis from Vec0..Vec2; the timer starts at a random phase.
int cEsp48::SetFreeWork(EspGenWork* gen, u32* seed)
{
    Esp48Work* w = &m_Free;

    w->dist_x = gen->Vec0.x * 0.1f;
    w->time_x = gen->Vec0.y;
    w->dist_y = gen->Vec1.x * 0.1f;
    w->time_y = gen->Vec1.y;
    w->dist_z = gen->Vec2.x * 0.1f;
    w->time_z = gen->Vec2.y;
    w->timer = fRandSeed1_1(seed) * 2.0f * PI;
    return 1;
}
