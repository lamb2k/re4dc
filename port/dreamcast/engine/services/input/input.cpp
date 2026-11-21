// input.cpp: the native input service (lane eng-svc4; input.h, docs/engine/SERVICES.md section 29).
//
// What it owns (the original unit pad.cpp, every function):
//   - the read, once a tick: the four pads into Joy[] (buttons, the triggers as L / R, the main stick as direction bits
//     beyond a 30-unit dead zone with 70 / 110 / 30 / 150 degree sectors, the sub stick beyond 10, the press and
//     release edges, the two repeat masks on 24 / 6 and 18 / 3 tick timers), connection and reset bits;
//   - the game's Key word: Joy[0] through the key-type table (pSys->key_type), opposite directions cancelling, the same
//     edges and repeats on 64 bits, the sticks and triggers copied unless the key stop holds them (KeyStop, KeyClear);
//   - the rumble: ten slots a pad (VibSet, VibSetData, VibSetDataCore, VibSetClearType), mixed once a tick into motor
//     pulses (VibControl). A random-strength slot draws from the engine's presentation generator (input.h).
// The debug key display (Pad_test) draws nothing; it is counted.
//
// Arithmetic: the original's (single precision, contraction off), so the PC reference compares bit for bit.
#include "types.h"
#include "global.h"
#include "main.h"
#include "main_mem.h"
#include "joy.h"
#include "pad.h"
#include "math_sub.h"
#include "rnd.h"
#include "input.h"

extern "C" {
InputCounters input_cnt;
int input_control;
}

namespace {

constexpr f32 kStickOn = 30.0f;   // the main stick's dead zone for its direction bits
constexpr int kSubDead = 10;      // the sub stick's
inline constexpr f32 deg(f32 d) { return d * (PI / 180.0f); }
inline u64 kbit(int n) { return (u64) 1 << n; }

PADStatus pad_data[4];
int vib_level = 0;   // the motor's pulse accumulator (0x7F80 a pulse)
u32 reset_bits;

void key_stop_flags_clear()
{
    pG->Status_flg[0] &= ~0x4000;
    pG->Status_flg[0] &= ~0x40000000;
    pG->Status_flg[0] &= ~0x20000000;
}

// press / release edges and the two repeat masks of a button word (`on` already read; `old` the previous tick's)
template <class W, int N, class T> void edges(W& on, W& old, W& trg, W& rel, W& rep, W& rep2, T* rep_timer, T* rep2_timer)
{
    rep = 0;
    rep2 = 0;
    trg = (old ^ on) & on;
    rel = (old ^ on) & old;
    W bit = 1;
    for (int j = 0; j < N; j++, bit <<= 1) {
        if (on & bit) {
            if (trg & bit) {
                rep |= bit;
                rep2 |= bit;
            } else {
                if (rep_timer[j] <= 0) {
                    rep |= bit;
                    rep_timer[j] = 6;
                }
                if (rep2_timer[j] <= 0) {
                    rep2 |= bit;
                    rep2_timer[j] = 3;
                }
            }
            rep_timer[j] -= GetSystemVcnt();
            rep2_timer[j] -= GetSystemVcnt();
        } else {
            rep_timer[j] = 24;
            rep2_timer[j] = 18;
        }
    }
}

// The pad clamp (lane eng-e1g, H-014.2): the engine's pad path clamps stick and trigger as the original game does (the
// GameCube SDK's PADClamp, which the original PadRead calls right after PADRead and the PC reference links): main
// stick dead zone 15 inside an octagon of 72 (corner 40), sub stick 15 / 59 / 31, triggers 30 to 180 shifted to 0.
// Route fixtures stay in raw units (stick 80 reaches the game as 65, trigger 0xC0 as 150). Always on; the unclamped
// path exists only as a test build (PAD_EXTRA=-DE1_PAD_NOCLAMP=1, the plays-right control).
void clamp_stick(s8* px, s8* py, int max, int xy, int min)
{
    int x = *px, y = *py;
    const int sx = x < 0 ? -1 : 1, sy = y < 0 ? -1 : 1;
    x = x < 0 ? -x : x;
    y = y < 0 ? -y : y;
    x = x <= min ? 0 : x - min;
    y = y <= min ? 0 : y - min;
    if (!x && !y) {
        *px = *py = 0;
        return;
    }
    const int d = xy * y <= xy * x ? xy * x + (max - xy) * y : xy * y + (max - xy) * x;
    if (xy * max < d) {
        x = (s8) (xy * max * x / d);
        y = (s8) (xy * max * y / d);
    }
    *px = (s8) (sx * x);
    *py = (s8) (sy * y);
}
void clamp_trigger(u8* t, int min, int max)
{
    if (*t <= min) *t = 0;
    else {
        if (*t > max) *t = (u8) max;
        *t = (u8) (*t - min);
    }
}
void pad_clamp(PADStatus* s)
{
#ifndef E1_PAD_NOCLAMP
    for (int i = 0; i < 4; i++, s++) {
        if (s->err != PAD_ERR_NONE) continue;
        clamp_stick(&s->stickX, &s->stickY, 72, 40, 15);
        clamp_stick(&s->substickX, &s->substickY, 59, 31, 15);
        clamp_trigger(&s->triggerLeft, 30, 180);
        clamp_trigger(&s->triggerRight, 30, 180);
    }
#else
    (void) s;
#endif
}

}   // namespace

u32 Key_type_tbl[2][64] = {
    {
        0x00080008, 0x00040004, 0x00020002, 0x00010001, 0x00000020, 0x00000040, 0x00000200, 0x00000100,
        0x00000000, 0x00000400, 0x00000100, 0x00000040, 0x00001000, 0x00001000, 0x00800000, 0x00400000,
        0x00000800, 0x00000400, 0x00000200, 0x00000100, 0x00000800, 0x00000010, 0x00000040, 0x00000020,
        0x00080008, 0x00040004, 0x00020002, 0x00010001, 0x00000010, 0x00001000, 0x00000200, 0x00000100,
        0x00000001, 0x00000002, 0x00000004, 0x00000008, 0x00200000, 0x00100000,
    },
    {0},
};
u32 ConnectedBits;

void PadInit()
{
    PADInit();
    PADReset(0xF0000000);
    PADSetAnalogMode(3);
    vib_level = 0;
    Key.old = 0;
}

void PadRead()
{
    input_cnt.reads++;
    const f32 on_sq = input_control == 1 ? 81.0f * 81.0f : kStickOn * kStickOn;
    PADRead(pad_data);
    pad_clamp(pad_data);   // the engine's clamp (was the SDK's PADClamp; lane eng-e1g)
    for (int i = 0; i < 4; i++) {
        const u32 chan = PAD_CHAN0_BIT >> i;
        if (pad_data[i].err == PAD_ERR_NONE) ConnectedBits |= chan;
        else if (pad_data[i].err == PAD_ERR_NO_CONTROLLER) reset_bits |= chan;
    }
    if (reset_bits && PADReset(reset_bits)) reset_bits = 0;

    for (int i = 0; i < 4; i++) {
        JOY* joy = &Joy[i];
        const PADStatus* pad = &pad_data[i];
        joy->err = pad->err;
        if (joy->err != 0) {
            memclr_asm(joy, sizeof(JOY));
            joy->err = pad->err;
            continue;
        }
        joy->old = joy->on;
        joy->on = pad->button;
        joy->stickX = pad->stickX;
        joy->stickY = pad->stickY;
        joy->substickX = pad->substickX;
        joy->substickY = pad->substickY;
        joy->triggerLeft = pad->triggerLeft;
        joy->triggerRight = pad->triggerRight;
        joy->analogA = pad->analogA;
        joy->analogB = pad->analogB;
        if (joy->triggerLeft) joy->on |= JOY_L;
        if (joy->triggerRight) joy->on |= JOY_R;
        // the main stick's direction bits: up / down / side sectors of its angle (0 = up, clockwise positive)
        const f32 x = (f32) joy->stickX;
        const f32 y = (f32) joy->stickY;
        const f32 ang = -atan2f(x, y);
        if (x * x + y * y > on_sq) {
            if (ang < 0.0f) {
                if (ang > -deg(70.0f)) joy->on |= JOY_SUP;
                if (ang < -deg(110.0f)) joy->on |= JOY_SDOWN;
                if (ang < -deg(30.0f) && ang > -deg(150.0f)) joy->on |= JOY_SLEFT;
            } else {
                if (ang < deg(70.0f)) joy->on |= JOY_SUP;
                if (ang > deg(110.0f)) joy->on |= JOY_SDOWN;
                if (ang > deg(30.0f) && ang < deg(150.0f)) joy->on |= JOY_SRIGHT;
            }
        }
        if (joy->substickX < -kSubDead) joy->on |= JOY_SSLEFT;
        else if (kSubDead < joy->substickX) joy->on |= JOY_SSRIGHT;
        else joy->substickX = 0;
        if (joy->substickY < -kSubDead) joy->on |= JOY_SSDOWN;
        else if (kSubDead < joy->substickY) joy->on |= JOY_SSUP;
        else joy->substickY = 0;
        edges<u32, 32>(joy->on, joy->old, joy->trg, joy->rel, joy->rep, joy->rep2, joy->rep_timer, joy->rep2_timer);
    }

    // the game's Key word: Joy[0] through the key-type table; opposite directions cancel
    Key.on = 0;
    u64 bit = 1;
    for (int i = 0; i < 64; i++, bit <<= 1) {
        if (Joy[0].on & Key_type_tbl[pSys->key_type][i]) Key.on |= bit;
    }
    static const u8 opposite[8][2] = {{0, 1}, {2, 3}, {24, 25}, {27, 26}, {35, 34}, {32, 33}, {14, 15}, {37, 36}};
    for (int k = 0; k < 8; k++) {
        if ((Key.on & kbit(opposite[k][0])) && (Key.on & kbit(opposite[k][1]))) {
            Key.on &= ~kbit(opposite[k][0]);
            Key.on &= ~kbit(opposite[k][1]);
        }
    }
    u64 old = Key.old;
    edges<u64, 64>(Key.on, old, Key.trg, Key.rel, Key.rep, Key.rep2, Key.rep_timer, Key.rep2_timer);
    Key.old = Key.on;

    if (!(pG->Stop_flg & 0x80000000)) {
        Key.stickX = Joy[0].stickX;
        Key.stickY = Joy[0].stickY;
        Key.substickX = Joy[0].substickX;
        Key.substickY = Joy[0].substickY;
        Key.triggerLeft = Joy[0].triggerLeft;
        Key.triggerRight = Joy[0].triggerRight;
    } else {
        KeyStop(0);
    }
    Key.analogA = 0;
    Key.analogB = 0;
    Pad_test();
    if (pG->Stop_flg & 0x10000000) key_stop_flags_clear();
    VibControl();
}

// Every key but `mask` held until the stop flag clears (Stop_flg bit 31): events, menus.
void KeyStop(u64 mask)
{
    pG->Stop_flg |= 0x80000000;
    KeyClear(mask);
}

// Every key bit outside `mask` (the last non-zero mask is kept) dropped from the Key word and its edges, the triggers
// zeroed, the key-stop status flags cleared.
void KeyClear(u64 mask)
{
    static u64 un_stop_mask = 0;
    if (mask) un_stop_mask = mask;
    Key.on &= un_stop_mask;
    Key.trg &= un_stop_mask;
    Key.rel &= un_stop_mask;
    Key.rep &= un_stop_mask;
    Key.rep2 &= un_stop_mask;
    Key.triggerLeft = 0;
    Key.triggerRight = 0;
    key_stop_flags_clear();
}

// The rumble mixer, once a tick: each active slot of Joy[0] waits, then counts down and ramps its level; the strongest
// (a random-strength slot: a presentation draw up to its level) is accumulated into motor pulses (0x7F80 a pulse).
// Stop_flg 0x8000 brakes a running motor.
void VibControl()
{
    const u8 old = Joy[0].motor_state;
    int max = 0;
    for (int i = 0; i < 10; i++) {
        VibWork* v = &Joy[0].vib[i];
        if (v->time == 0) continue;
        if (v->wait) {
            v->wait--;
            continue;
        }
        input_cnt.vib_ticks++;
        v->time--;
        v->level += v->add;
        int lvl = v->level;
        if (v->type & 0x8000) {
            input_cnt.vib_random++;
            u32 hi, lo;
            if (input_control == 2) {   // rumblernd: the fault the split removes (behaviour generator)
                hi = Rnd();
                lo = Rnd();
            } else {
                hi = eng_pres_u8();
                lo = eng_pres_u8();
            }
            lvl = (u32) ((hi << 8) + lo) % (lvl + 1);
        }
        if (max < lvl) max = lvl;
    }
    vib_level += max;
    if (vib_level > 0x7F7F) {
        vib_level -= 0x7F80;
        Joy[0].motor_state = 1;
    } else {
        Joy[0].motor_state = 0;
    }
    if ((pG->Stop_flg & 0x8000) && old == 1) {
        Joy[0].motor_state = 2;
        input_cnt.motor_changes++;
        PADControlMotor(0, 2);
        vib_level = 0;
    } else if (Joy[0].motor_state != old) {
        input_cnt.motor_changes++;
        PADControlMotor(0, Joy[0].motor_state);
    }
}

// A free rumble slot of the ten, or NULL with rumble off (pSys->flags 0x08000000 clear).
VibWork* PullVibWork()
{
    if (!(pSys->flags & 0x08000000)) return NULL;
    VibWork* v = Joy[0].vib;
    for (int i = 0; i < 10; i++, v++) {
        if (v->time == 0) return v;
    }
    return NULL;
}

// A constant rumble: `level` (0..0xFF) for `time` ticks (at most 255) after `wait`; type bits 0-3 for VibSetClearType,
// bit 15 random strength.
void VibSet(u32 time, u32 level, u16 wait, u16 type)
{
    VibWork* v = PullVibWork();
    if (!v) return;
    input_cnt.vib_queued++;
    v->type = type;
    v->time = time > 0xFF ? 0xFF : time;
    v->wait = wait;
    v->level = level << 7;
    v->add = 0;
}

// Every entry of a rumble pattern (a level ramp over its time), its type or-ed with `type`.
void VibSetDataCore(VibData* d, u32 type)
{
    for (u32 i = 0; i < d->num; i++) {
        VibWork* v = PullVibWork();
        if (!v) return;
        input_cnt.vib_queued++;
        const VibDataEntry* e = &d->e[i];
        const int lvl = e->lvl0 << 12;
        const int add = ((e->lvl1 - e->lvl0) << 12) / e->time;
        v->type = e->type | type;
        v->time = e->time;
        v->wait = e->wait;
        v->level = lvl;
        v->add = add;
    }
}

// Pattern `no` of a rumble table.
void VibSetData(VibDataTbl* t, u32 no, u32 type)
{
    if (no < t->num && t->ofs[no]) VibSetDataCore((VibData*) (t->ofs[no] + (u32) t), type);
}

// The running rumbles whose type has one of the low four bits of `type` stopped.
void VibSetClearType(u32 type)
{
    type &= 0xF;
    VibWork* v = Joy[0].vib;
    for (int i = 0; i < 10; i++, v++) {
        if (v->type & type) v->time = 0;
    }
}

// 1 when the pad is connected and System_flg bit 3 (pads ignored) is off.
int PadCheckStatus(JOY* joy)
{
    if (pG->System_flg & 8) return 0;
    return joy->err == 0;
}

void Pad_test() { input_cnt.debug_prints++; }
