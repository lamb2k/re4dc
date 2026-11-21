// The services row's phase account (lane eng-svcspd1): exclusive time per phase of the skeleton, cloth and collision
// services, kept per tick, for the account in docs/engine/SERVICES_COST_20261121.md. A run-time lab arm: the boot file
// SVCPROF (host/e1_svc_mem.cpp) sets svc_prof_on before play; without it every site is one load and a branch, and the
// PC reference (no clock linked) never turns it on. Exclusive: entering a phase pauses the one it is nested in, so the
// phases of a tick add up to the time spent inside them. Control (SVCPROFCTL): a known busy wait inside SP_PUBLISH
// must read as its length. Header only (C++17 inline variables): any unit may include it, nothing links against it.
#pragma once

enum {
    SP_REST = 0,      // not inside any phase below
    SP_SAMPLE,        // motion keys: MotionMoveCore (rows and key decodes)
    SP_MATCALC,       // the local matrices (partsMatCalc: R(ang) T(pos) S(scale) for every bone)
    SP_WORLD_PRE,     // MotionMove's world pass before the IK (the scale-cancelled model matrix)
    SP_WORLD_POST,    // MotionMove's world pass after the IK
    SP_WORLD_HOKAN,   // MotionMove's world pass after the hokan
    SP_WORLD_ENTRY,   // partsWorldCalc, matUpdate, setPartsOffset: the world pass called from outside MotionMove
    SP_IK,            // inverse kinematics (floor queries inside it are SP_COL_FLOOR)
    SP_HOKAN,         // the hokan (quaternion blend from the previous clip)
    SP_BLEND,         // matBlend (quaternion blend of two clips)
    SP_BLENDTBL,      // the blend table (per-bone quaternion blends)
    SP_MAILBOX,       // the mailbox: records taken back and served at every entry
    SP_TRANSLATE,     // PartsWorldPosCalc, at_pos_calc, setPos: every bone translated
    SP_PUBLISH,       // the palette (world x bind)
    SP_MOTION_REST,   // MotionMove / MotionSetCore outside the phases above (clock, root motion, set-up)
    SP_CLOTH_PRE,     // a chain's step set-up: floor query, volumes, wind, reset
    SP_CLOTH_KERNEL,  // the chain kernel (move, angle limit, constraints, volume tests, matrices)
    SP_CLOTH_POST,    // the chain's bones served to the mailbox
    SP_COL_LINE,      // collision: line queries (hitCheck, hitCheck2)
    SP_COL_FLOOR,     // collision: floor queries (getFloor, with their line query)
    SP_COL_SPHERE,    // collision: swept sphere (polySphereCk)
    SP_N
};

// the host's clock (ns); the PC reference has none, so the arm cannot turn on there
extern "C" unsigned long long svc_prof_clock(void) __attribute__((weak));

inline int svc_prof_on;                 // 1: the arm is on (boot file SVCPROF)
inline unsigned svc_prof_ns[SP_N];      // this tick's exclusive time per phase, ns (rolled by the host every tick)
inline unsigned svc_prof_calls[SP_N];   // entries per phase (the run's)
inline unsigned svc_prof_ctl_us;        // control (SVCPROFCTL): a busy wait of this many us a tick inside SP_PUBLISH
inline int svc_prof_stack[16];
inline int svc_prof_depth;
inline int svc_prof_k;
inline unsigned long long svc_prof_t0;

__attribute__((noinline)) inline void svc_prof_enter_(int k)
{
    const unsigned long long now = svc_prof_clock();
    if (svc_prof_depth > 0) svc_prof_ns[svc_prof_k] += (unsigned) (now - svc_prof_t0);
    if (svc_prof_depth < 16) svc_prof_stack[svc_prof_depth] = svc_prof_k;
    svc_prof_depth++;
    svc_prof_k = k;
    svc_prof_calls[k]++;
    svc_prof_t0 = now;
}
__attribute__((noinline)) inline void svc_prof_leave_(void)
{
    const unsigned long long now = svc_prof_clock();
    svc_prof_ns[svc_prof_k] += (unsigned) (now - svc_prof_t0);
    if (svc_prof_depth > 0) svc_prof_depth--;
    svc_prof_k = svc_prof_depth < 16 ? svc_prof_stack[svc_prof_depth] : SP_REST;
    svc_prof_t0 = now;
}
inline int svc_prof_cur(void) { return svc_prof_depth > 0 ? svc_prof_k : SP_REST; }

struct SvcProf {   // a phase for the scope of a block
    explicit SvcProf(int k) { if (svc_prof_on) svc_prof_enter_(k); }
    ~SvcProf() { if (svc_prof_on) svc_prof_leave_(); }
};
struct SvcProfUnless {   // a phase, unless the phase being timed is `outer` (a floor query's line stays the floor's)
    bool on;
    SvcProfUnless(int k, int outer) : on(svc_prof_on && svc_prof_cur() != outer) { if (on) svc_prof_enter_(k); }
    ~SvcProfUnless() { if (on) svc_prof_leave_(); }
};
