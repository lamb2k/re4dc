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
#include "model.h"
#include "em_sub.h"

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
struct WepTargetRec { cEm* em; YARARE_INFO* part; };
extern "C" u32 __real_GetWepTargetList2(Vec* p0, Vec* p1, WepTargetRec* list, u32 max, Vec* hit, Vec* nrm, u32* attr,
                                        int type, int flag, f32 len);
// lane eng-e1k: the native target list (services/aim/aim.cpp GetWepTargetList2, renamed eng_GetWepTargetList2 here)
extern "C" u32 eng_GetWepTargetList2(Vec* p0, Vec* p1, WepTargetRec* list, u32 max, Vec* hit, Vec* nrm, u32* attr,
                                     int type, int flag);
static void aim_init();
namespace {
// The shot's target list, both answers on every call (lane eng-e1k): the count, each entry's enemy and hit box, each
// box's distance (rad, the squared distance the damage and the order read, compared as its square root), the scenery
// attribute and hit point. aimlist.txt: the summary (rewritten at every call); aimlist-diff.txt: a line per call that
// differs. Both bodies write the boxes they list (rad, dist, pos, flag 0x4000), so the one whose answer the behaviour
// gets runs last: the original, or the native under RE4_AIM_USE=native.
struct ListAnswer { u32 n, attr; WepTargetRec e[20]; float rad[20]; Vec hit; };
struct {
    unsigned calls, same, count_diff, em_diff, part_diff, attr_diff, hit_over, rad_over;
    float max_hit, max_rad;
} L;
void list_summary()
{
    void* f = svc_out_open("aimlist.txt", "w");
    if (!f) return;
    svc_out_printf(f, "list calls %u same %u count_diff %u em_diff %u part_diff %u attr_diff %u hit_over_1u %u rad_over_1u %u"
                   " max_hit %.4f max_rad_units %.4f use %s control %d\n", L.calls, L.same, L.count_diff, L.em_diff,
                   L.part_diff, L.attr_diff, L.hit_over, L.rad_over, (double) L.max_hit, (double) L.max_rad,
                   A.use_native ? "native" : "original", aim_control);
    svc_out_close(f);
}
int box_index(cEm* em, const YARARE_INFO* b)   // a hit box's place in its enemy's chain (-1: not in it)
{
    int k = 0;
    for (const YARARE_INFO* p = &em->hitInfo; p; p = p->next, k++)
        if (p == b) return k;
    return -1;
}
void list_take(ListAnswer& r, const WepTargetRec* list, u32 n, const Vec& hit, u32 attr)
{
    r.n = n > 20 ? 20 : n;
    r.attr = attr;
    r.hit = hit;
    for (u32 i = 0; i < r.n; i++) { r.e[i] = list[i]; r.rad[i] = list[i].part->rad; }
}
void list_compare(const ListAnswer& o, const ListAnswer& w)   // o: the original's answer, w: the native's
{
    L.calls++;
    const bool cd = o.n != w.n, td = o.attr != w.attr;
    bool ed = false, pd = false;
    float mr = 0.0f;
    for (u32 i = 0; i < o.n && i < w.n; i++) {
        ed |= o.e[i].em != w.e[i].em;
        pd |= o.e[i].part != w.e[i].part;
        const float d = __builtin_fabsf(__builtin_sqrtf(o.rad[i]) - __builtin_sqrtf(w.rad[i]));
        if (d > mr) mr = d;
    }
    const float hx = o.hit.x - w.hit.x, hy = o.hit.y - w.hit.y, hz = o.hit.z - w.hit.z;
    const float hd = __builtin_sqrtf(hx * hx + hy * hy + hz * hz);
    const bool ho = hd > 1.0f, ro = mr > 1.0f;
    if (hd > L.max_hit) L.max_hit = hd;
    if (mr > L.max_rad) L.max_rad = mr;
    L.count_diff += cd; L.em_diff += ed; L.part_diff += pd; L.attr_diff += td; L.hit_over += ho; L.rad_over += ro;
    if (!cd && !ed && !pd && !td && !ho && !ro) L.same++;
    else {
        static void* fd;
        if (!fd) fd = svc_out_open("aimlist-diff.txt", "w");
        if (fd) {
            svc_out_printf(fd, "call %u frame %u count %u/%u attr %08x/%08x first em %p/%p hit %.3f units apart, rad %.3f units apart\n",
                           L.calls, (unsigned) pG->Frame_cnt, o.n, w.n, (unsigned) o.attr, (unsigned) w.attr,
                           (void*) (o.n ? o.e[0].em : 0), (void*) (w.n ? w.e[0].em : 0), (double) hd, (double) mr);
            // lane eng-e2g: the hit box each answer chose (its place in the enemy's chain, flags, part, distance)
            for (u32 i = 0; i < o.n && i < w.n; i++)
                svc_out_printf(fd, "  entry %u box original #%d (flags %x part %d, %.3f units) native #%d (flags %x part %d,"
                               " %.3f units)\n", i, box_index(o.e[i].em, o.e[i].part), o.e[i].part->flags,
                               o.e[i].part->partsNo, (double) __builtin_sqrtf(o.rad[i]), box_index(w.e[i].em, w.e[i].part),
                               w.e[i].part->flags, w.e[i].part->partsNo, (double) __builtin_sqrtf(w.rad[i]));
        }
    }
    list_summary();
}
// lane eng-e2g, diagnosis only (RE4_AIM_BOXES=1; the comparison above is unchanged): boxes.txt gets, per shot, the
// line and every live hit box of the first listed enemy: its place, flags, part, sizes, the capsule's ends and radius
// in the world (the original's construction, em_sub.cpp emLineAtCk) or the box's part matrix, and the original's own
// answer for that box alone (emLineCapsuleCrossCk / emLineCubeCrossCk: hit or not, the point, its distance from p0).
void box_dump(const Vec* p0, const Vec* p1, cEm* em)
{
    static void* f;
    if (!f) f = svc_out_open("boxes.txt", "w");
    if (!f || !em) return;
    svc_out_printf(f, "shot frame %u a %.9g %.9g %.9g b %.9g %.9g %.9g em %p\n", (unsigned) pG->Frame_cnt, p0->x, p0->y,
                   p0->z, p1->x, p1->y, p1->z, (void*) em);
    int k = 0;
    for (YARARE_INFO* p = &em->hitInfo; p; p = p->next, k++) {
        if (!(p->flags & 1)) continue;
        cModel* part = p->partsNo ? em->getPartsPtr(p->partsNo - 1) : (cModel*) em;
        Vec a = *p0, b = *p1, hit = {0, 0, 0};
        int r;
        svc_out_printf(f, "  box #%d flags %x part %d w %.9g h %.9g d %.9g ofs %.9g %.9g %.9g", k, p->flags, p->partsNo,
                       p->width, p->height, p->depth, p->ofs.x, p->ofs.y, p->ofs.z);
        if (p->flags & 8) {
            r = emLineCubeCrossCk(&a, &b, part->mat, p->width, p->height, p->depth, &p->ofs, &hit);
            svc_out_printf(f, " M");
            for (int i = 0; i < 3; i++)
                for (int j = 0; j < 4; j++) svc_out_printf(f, " %.9g", part->mat[i][j]);
        } else {
            Vec top = p->ofs, bot = p->ofs, s = {0.0f, 0.0f, p->width};
            if (p->flags & 6) { if (p->flags & 2) top.x += p->height; else top.z += p->height; }
            else top.y += p->height;
            PSMTXMultVec(part->mat, &top, &top);
            PSMTXMultVec(part->mat, &bot, &bot);
            PSMTXMultVecSR(part->mat, &s, &s);
            const f32 rr = __builtin_sqrtf(s.x * s.x + s.y * s.y + s.z * s.z);
            r = emLineCapsuleCrossCk(&a, &b, &top, &bot, rr, &hit);
            svc_out_printf(f, " T %.9g %.9g %.9g B %.9g %.9g %.9g R %.9g", top.x, top.y, top.z, bot.x, bot.y, bot.z, rr);
        }
        const f32 dx = hit.x - p0->x, dy = hit.y - p0->y, dz = hit.z - p0->z;
        svc_out_printf(f, " -> %d", r);
        if (r) svc_out_printf(f, " at %.9g %.9g %.9g dist %.6g", hit.x, hit.y, hit.z, __builtin_sqrtf(dx * dx + dy * dy + dz * dz));
        svc_out_printf(f, "\n");
    }
}
}   // namespace
extern "C" u32 __wrap_GetWepTargetList2(Vec* p0, Vec* p1, WepTargetRec* list, u32 max, Vec* hit, Vec* nrm, u32* attr,
                                        int type, int flag, f32 len)
{
    aim_init();
    static void* f;
    if (!f) f = svc_out_open("shots.txt", "w");
    // lane eng-e1k: the other arm's answer first, on copies; then the answer the behaviour gets, last
    WepTargetRec tmp[20];
    Vec c0 = *p0, c1 = *p1, th, tn;
    u32 tattr = 0;
    ListAnswer first, last;
    const u32 n1 = A.use_native ? __real_GetWepTargetList2(&c0, &c1, tmp, max, &th, &tn, &tattr, type, flag, len)
                                : eng_GetWepTargetList2(&c0, &c1, tmp, max, &th, &tn, &tattr, type, flag);
    list_take(first, tmp, n1, th, tattr);
    const u32 n = A.use_native ? eng_GetWepTargetList2(p0, p1, list, max, hit, nrm, attr, type, flag)
                               : __real_GetWepTargetList2(p0, p1, list, max, hit, nrm, attr, type, flag, len);
    list_take(last, list, n, *hit, *attr);
    if (A.use_native) list_compare(first, last);
    else list_compare(last, first);
    if (is(svc_env("RE4_AIM_BOXES"), "1")) box_dump(p0, p1, first.n ? first.e[0].em : (last.n ? last.e[0].em : 0));
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

static void aim_init()
{
    if (!A.init) {
        A.init = 1;
        if (is(svc_env("RE4_AIM_CONTROL"), "grow")) aim_control = 1;
        if (is(svc_env("RE4_AIM_CONTROL"), "truegeom")) aim_control = 2;   // lane eng-e2g: the true-geometry boxes
        A.use_native = is(svc_env("RE4_AIM_USE"), "native");
        A.diff = svc_out_open("aim-diff.txt", "w");
    }
}
extern "C" int __wrap_GetWepTargetPos(Vec* p0, Vec* p1, int plCheck, int wepNo, cEm** outEm, int* outAttr)
{
    aim_init();
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
