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
                   " hit_distance %.0f..%.0f\n",
                   A.calls, A.same, A.ret_diff, A.em_diff, A.attr_diff, A.point_over, (double) A.max_point,
                   A.use_native ? "native" : "original", aim_control, (double) A.hit_min, (double) A.hit_max);
    for (int o = 0; o < 4; o++)
        for (int n = 0; n < 4; n++)
            if (A.by_ret[o][n]) svc_out_printf(f, "ret original %d native %d: %u\n", o, n, A.by_ret[o][n]);
    svc_out_close(f);
}
}   // namespace

// The shot lines (lane eng-e1h): every GetWepTargetList2 call (the handgun's shot, PlWepHitCheck2) to shots.txt: the
// line, the scenery hit (attribute, point, distance), the enemies the line crossed, and each alive enemy's root position
// with its distance from the line, so a shot fixture can be aimed at a Ganado and read back.
struct WepTargetRec { cEm* em; void* part; };
extern "C" u32 __real_GetWepTargetList2(Vec* p0, Vec* p1, WepTargetRec* list, u32 max, Vec* hit, Vec* nrm, u32* attr,
                                        int type, int flag, f32 len);
extern "C" u32 __wrap_GetWepTargetList2(Vec* p0, Vec* p1, WepTargetRec* list, u32 max, Vec* hit, Vec* nrm, u32* attr,
                                        int type, int flag, f32 len)
{
    static void* f;
    if (!f) f = svc_out_open("shots.txt", "w");
    const u32 n = __real_GetWepTargetList2(p0, p1, list, max, hit, nrm, attr, type, flag, len);
    if (!f) return n;
    const float hx = hit->x - p0->x, hy = hit->y - p0->y, hz = hit->z - p0->z;
    svc_out_printf(f, "shot frame %u type %d from %.0f %.0f %.0f to %.0f %.0f %.0f attr %08x hit %.0f %.0f %.0f at %.0f enemies %u",
                   (unsigned) pG->Frame_cnt, type, p0->x, p0->y, p0->z, p1->x, p1->y, p1->z, (unsigned) *attr, hit->x,
                   hit->y, hit->z, __builtin_sqrtf(hx * hx + hy * hy + hz * hz), (unsigned) n);
    for (u32 i = 0; i < n; i++) svc_out_printf(f, " [%02x]", (unsigned) list[i].em->id);
    const float dx = p1->x - p0->x, dy = p1->y - p0->y, dz = p1->z - p0->z;
    const float dl = __builtin_sqrtf(dx * dx + dy * dy + dz * dz);
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext) {
        if (e == (cEm*) pPL) continue;
        const float ex = e->pos.x - p0->x, ey = e->pos.y - p0->y, ez = e->pos.z - p0->z;
        const float along = (ex * dx + ey * dy + ez * dz) / dl;
        const float px = ex - dx * along / dl, py = ey - dy * along / dl, pz = ez - dz * along / dl;
        svc_out_printf(f, " | em %02x set %02x hp %d at %.0f %.0f %.0f along %.0f off %.0f (y %.0f)", (unsigned) e->id,
                       (unsigned) e->emset_no, (int) e->hp, e->pos.x, e->pos.y, e->pos.z, along,
                       __builtin_sqrtf(px * px + py * py + pz * pz), py);
    }
    svc_out_printf(f, "\n");
    return n;
}

// Lane eng-e1h: the magazine and the shot's rumble are the reference's own now (host_stubs.cpp: the new game's 10
// rounds; host_glue.cpp: the core archive's rumble table converted to the PC's order at load), so this build no longer
// answers the magazine (RE4_AIM_MAG) or skips a rumble pattern (vib_skipped), as lane eng-e1g's did.

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
