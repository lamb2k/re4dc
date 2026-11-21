// aimcheck.cpp (game side; lane eng-e1g): the native weapon-target query (services/aim/aim.cpp) against the original
// (em_sub.cpp GetWepTargetPos) on the PC reference, in one run. Linked only into the aimchk build (svc.mk): every call
// the behaviour makes (the laser sight while aiming, the push target) reaches this wrapper, which asks the original
// (__real_) and the native body (renamed eng_GetWepTargetPos) the same question on copies of the inputs and compares
// the answers: the return (0 nothing, 1 scenery, 2 / 3 an enemy's box), the enemy named, the surface attribute and the
// hit point. RE4_AIM_USE=native hands the behaviour the native answer (the outcome arm: kills, hits, traces against the
// reference); otherwise the original's (the run is the reference). RE4_AIM_CONTROL=grow sets the native control (every
// enemy box and capsule 25% larger: the comparison must fail). RE4_SVC_OUT=<dir> gets aim.txt (summary, rewritten at
// every call) and aim-diff.txt (one line per call that differs).
#include "hostref.h"
#include "global.h"
#include "em.h"
#include "player.h"

extern "C" {
void* svc_out_open(const char* name, const char* mode);
void svc_out_printf(void* f, const char* fmt, ...);
void svc_out_close(void* f);
const char* svc_env(const char* name);
int __real_GetWepTargetPos(Vec* p0, Vec* p1, int plCheck, int wepNo, cEm** outEm, int* outAttr);
int eng_GetWepTargetPos(Vec* p0, Vec* p1, int plCheck, int wepNo, cEm** outEm, int* outAttr);
extern int aim_control;
}

namespace { extern unsigned vib_skipped; }
namespace {
struct {
    int init, use_native;
    unsigned calls, same, ret_diff, em_diff, attr_diff, point_over;   // point_over: hit points more than 1 unit apart
    unsigned by_ret[4][4];   // [original][native]
    float max_point, hit_min, hit_max;   // the original's hit distance from p0, over the calls
    void* diff;
} A;
bool is(const char* c, const char* name) { return c && !__builtin_strcmp(c, name); }
void summary()
{
    void* f = svc_out_open("aim.txt", "w");
    if (!f) return;
    svc_out_printf(f, "aim calls %u same %u ret_diff %u em_diff %u attr_diff %u point_over_1u %u max_point %.4f use %s control %d"
                   " hit_distance %.0f..%.0f vib_skipped %u\n",
                   A.calls, A.same, A.ret_diff, A.em_diff, A.attr_diff, A.point_over, (double) A.max_point,
                   A.use_native ? "native" : "original", aim_control, (double) A.hit_min, (double) A.hit_max, vib_skipped);
    for (int o = 0; o < 4; o++)
        for (int n = 0; n < 4; n++)
            if (A.by_ret[o][n]) svc_out_printf(f, "ret original %d native %d: %u\n", o, n, A.by_ret[o][n]);
    svc_out_close(f);
}
}   // namespace

// The magazine (svc.mk AIM_MAG_STUBS): RE4_AIM_MAG rounds, never used up (as the engine image's e1_stubs.cpp, 10);
// unset, 0: the reference's empty magazine.
namespace {
int aim_mag()
{
    static int m = -1;
    if (m < 0) {
        const char* s = svc_env("RE4_AIM_MAG");
        m = 0;
        for (; s && *s >= '0' && *s <= '9'; s++) m = m * 10 + (*s - '0');
    }
    return m;
}
}   // namespace
extern "C" u16 aimchk_bulletNum(void*) __asm__("_ZN8cItemMgr9bulletNumEv");
extern "C" u32 aimchk_bulletNumCurrent(void*) __asm__("_ZN8cItemMgr16bulletNumCurrentEv");
extern "C" u16 aimchk_bulletNum(void*) { return (u16) aim_mag(); }
extern "C" u32 aimchk_bulletNumCurrent(void*) { return (u32) aim_mag(); }

// The shot's rumble (objRuger moveFire: VibSetData on the core archive's table at ofs_1C): on the PC tree that table's
// offsets read byte-swapped (0x04010000 for 0x104), so the pattern address falls outside the archive and the reference
// crashes on the first shot. Rumble is presentation: the aimchk build (svc.mk --wrap=VibSetData) skips a pattern whose
// address is not inside the table's first MiB, counts it (aim.txt), and passes every other call on.
namespace { unsigned vib_skipped; }
extern "C" void __real_VibSetData(void* t, u32 no, u32 type);
extern "C" void __wrap_VibSetData(void* t, u32 no, u32 type)
{
    const u32* w = (const u32*) t;   // {num, ofs[num]}
    if (w && no < w[0] && w[1 + no] >= 0x100000u) { vib_skipped++; return; }
    __real_VibSetData(t, no, type);
}

extern "C" int __wrap_GetWepTargetPos(Vec* p0, Vec* p1, int plCheck, int wepNo, cEm** outEm, int* outAttr)
{
    if (!A.init) {
        A.init = 1;
        if (is(svc_env("RE4_AIM_CONTROL"), "grow")) aim_control = 1;
        A.use_native = is(svc_env("RE4_AIM_USE"), "native");
        A.diff = svc_out_open("aim-diff.txt", "w");
    }
    Vec a1 = *p0, b1 = *p1, a2 = *p0, b2 = *p1;
    cEm *e1 = 0, *e2 = 0;
    int t1 = -1, t2 = -1;
    const int r1 = __real_GetWepTargetPos(&a1, &b1, plCheck, wepNo, &e1, &t1);
    const int r2 = eng_GetWepTargetPos(&a2, &b2, plCheck, wepNo, &e2, &t2);
    A.calls++;
    if (r1 >= 0 && r1 < 4 && r2 >= 0 && r2 < 4) A.by_ret[r1][r2]++;
    const float dx = b1.x - b2.x, dy = b1.y - b2.y, dz = b1.z - b2.z;
    const float d = __builtin_sqrtf(dx * dx + dy * dy + dz * dz);
    if (d > A.max_point) A.max_point = d;
    {
        const float hx = b1.x - p0->x, hy = b1.y - p0->y, hz = b1.z - p0->z, h = __builtin_sqrtf(hx * hx + hy * hy + hz * hz);
        if (A.calls == 1 || h < A.hit_min) A.hit_min = h;
        if (h > A.hit_max) A.hit_max = h;
    }
    const bool rd = r1 != r2, ed = e1 != e2, td = (r1 == 1 || r2 == 1) && t1 != t2, pd = d > 1.0f;
    A.ret_diff += rd;
    A.em_diff += ed;
    A.attr_diff += td;
    A.point_over += pd;
    if (!rd && !ed && !td && !pd) A.same++;
    else if (A.diff)
        svc_out_printf(A.diff, "call %u frame %u pl %d ret %d/%d em %p/%p attr %d/%d point %.3f %.3f %.3f / %.3f %.3f %.3f (%.3f)\n",
                       A.calls, (unsigned) pG->Frame_cnt, plCheck, r1, r2, (void*) e1, (void*) e2, t1, t2, (double) b1.x,
                       (double) b1.y, (double) b1.z, (double) b2.x, (double) b2.y, (double) b2.z, (double) d);
    summary();
    const bool nat = A.use_native;
    *p1 = nat ? b2 : b1;
    if (outEm) *outEm = nat ? e2 : e1;
    const int r = nat ? r2 : r1;
    if (outAttr && r == 1) *outAttr = nat ? t2 : t1;
    return r;
}
