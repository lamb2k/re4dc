// e2_dump.cpp (game side; lane eng-e2a): the boundary log of the fight image's enemy hit geometry (em_sub.cpp's service
// functions, native in services/aim/em_hit.cpp), linked into odump (the original em_sub) and native (the engine bodies)
// alike. RE4_SVC_OUT=<dir> receives e2.txt: every call the behaviour makes to one of those entry points (--wrap: svc.mk
// E2_WRAP), in call order, with its tick, inputs and outputs, and every effect start (EstSet) made inside one. Only
// top-level calls are logged (not those inside another logged call, a round-4 call or a collision query), so both builds
// log the same boundary whatever their internals call. While an e2 call runs, svc4_dump.cpp's round-4 log skips the
// calls made inside it (svc_e2_depth): they are the e2 service's internals, compared here at its boundary.
//
// Tokens (svc/e2_compare.py): plain integers and hex compare exactly; "P" x,y,z a position within 0.01 unit; "R" a
// length within 0.01 unit; "D" a squared distance whose root is within 0.01 unit; "A" an angle within 0.01 degree.
// Lines starting with '#' are counters.
//
// Controls (RE4_SVC_CONTROL, native only): hitwide (every capsule radius and box extent of the line tests 10% larger),
// dmposmid (the damage position on the box's axis), sphereshort (the melee sphere 20% smaller). Exercise
// (RE4_SVC_EXERCISE=e2geom), the same calls in both builds at fixed ticks, since the fixtures' play reaches only the
// water test, the debug boxes and the blood placement: every live actor's boxes against lines, spheres and damage
// positions (from tick 30, every 7th); the pure shapes (capsule, box, quad) on 1500 generated cases (ticks 20 and 400);
// the attack checks against Leon and the partner, line attacks, blast lists at each Ganado and a rack planted in a free
// character slot (from tick 40, every 11th); the caught-actor follow on a Ganado, its record put back (ticks 60 .. 90);
// once each, an attack that lands (tick 250) and a blast's knock-down and a grenade list (tick 270).
// RE4_E2_BOXGEOM=1 (diagnosis, both builds alike) appends the chosen box's capsule (G tokens) to each emLineAtCk line.
#include "hostref.h"
#include "model.h"
#include "em.h"
#include "player.h"
#include "pl_npc.h"
#include "emhit.h"
#include "em_sub.h"
#include "obj.h"
#include "emrack.h"
#include "math_sub.h"
#include "dmg.h"
#include "area.h"
#include "geometry.h"

extern "C" {
void* svc_out_open(const char* name, const char* mode);
void svc_out_printf(void* f, const char* fmt, ...);
void svc_out_close(void* f);
const char* svc_env(const char* name);
int svc_col_depth(void);
int svc4_depth(void) __attribute__((weak));
extern int emhit_control __attribute__((weak));
extern int dmg_control __attribute__((weak));
extern int area_control __attribute__((weak));
}
#define P svc_out_printf

namespace {
void* g_f;
unsigned g_tick;
int g_depth;
u32 actor(const void* m)
{
    const u32 a = (u32) m, elo = (u32) EmMgr.pArray, olo = (u32) ObjMgr.pArray;
    if (a >= elo && a < elo + EmMgr.size * EmMgr.nArray) return (a - elo) / EmMgr.size;
    if (a >= olo && a < olo + ObjMgr.size * ObjMgr.nArray) return 64 + (a - olo) / ObjMgr.size;
    return 999;
}
// a hit box as its actor and its place in that actor's chain (the same in both builds)
void box(const YARARE_INFO* b)
{
    if (!b) { P(g_f, " box-"); return; }
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext) {
        int k = 0;
        for (const YARARE_INFO* p = &e->hitInfo; p; p = p->next, k++)
            if (p == b) { P(g_f, " box%u.%d %x", actor(e), k, b->flags); return; }
    }
    P(g_f, " box?");
}
void pv(const Vec* v)
{
    if (v) P(g_f, " P%.9g,%.9g,%.9g", (double) v->x, (double) v->y, (double) v->z);
    else P(g_f, " P-");
}
void len(f32 r) { P(g_f, " R%.9g", (double) r); }
// a matrix's three axes and its position, as positions
void mcols(const Mtx m)
{
    for (int c = 0; c < 4; c++) {
        const Vec col = {m[0][c], m[1][c], m[2][c]};
        pv(&col);
    }
}
void d2(f32 r) { P(g_f, " D%.9g", (double) r); }
void ang(f32 a) { P(g_f, " A%.9g", (double) a); }
bool is_top() { return g_f && g_depth == 0 && svc_col_depth() == 0 && (!svc4_depth || svc4_depth() == 0); }
// the effect starts made inside the current top-level call, printed after its line
struct Es { int a, b, c, d, e, f; u32 g; Vec p, r; bool rot; };
Es g_es[8];
int g_nes;
int g_open;   // a top-level call is being logged
void es_flush()
{
    for (int i = 0; i < g_nes; i++) {
        const Es& e = g_es[i];
        P(g_f, "%u ES %d %d %d %d %d %d %u", g_tick, e.a, e.b, e.c, e.d, e.e, e.f, actor((void*) e.g));
        pv(&e.p);
        if (e.rot) ang(e.r.y);
        P(g_f, "\n");
    }
    if (g_nes > 8) P(g_f, "%u ES overflow %d\n", g_tick, g_nes);
    g_nes = 0;
}
}   // namespace

extern "C" int svc_e2_depth(void) { return g_depth; }

namespace {
// diagnosis only (RE4_E2_BOXGEOM): a box's capsule as the SDK computes it, appended to its line as " G" tokens
void boxgeom(cEm* em, const YARARE_INFO* p)
{
    cModel* part = p->partsNo ? em->getPartsPtr(p->partsNo - 1) : (cModel*) em;
    Vec b = p->ofs, t = p->ofs, s = {0.0f, 0.0f, p->width};
    if (p->flags & 6) { if (p->flags & 2) t.x += p->height; else t.z += p->height; } else t.y += p->height;
    PSMTXMultVec(part->mat, &b, &b);
    PSMTXMultVec(part->mat, &t, &t);
    PSMTXMultVecSR(part->mat, &s, &s);
    P(g_f, " G%.9g,%.9g,%.9g G%.9g,%.9g,%.9g G%.9g", (double) t.x, (double) t.y, (double) t.z, (double) b.x, (double) b.y,
      (double) b.z, (double) PSVECMag(&s));
}
}   // namespace

// ---- the wrappers: W (a value), WV (void) ----
#define W(ret, name, params, args, log_in, log_out)                                                                      \
    extern "C" ret __real_##name params;                                                                               \
    extern "C" ret __wrap_##name params                                                                                \
    {                                                                                                                  \
        const bool t = is_top();                                                                                          \
        if (t) { P(g_f, "%u", g_tick); log_in; g_open = 1; }                                                                     \
        g_depth++;                                                                                                     \
        ret r = __real_##name args;                                                                                    \
        g_depth--;                                                                                                     \
        if (t) { P(g_f, " ->"); log_out; P(g_f, "\n"); es_flush(); g_open = 0; }                                               \
        return r;                                                                                                      \
    }
#define WV(name, params, args, log_in, log_out)                                                                          \
    extern "C" void __real_##name params;                                                                              \
    extern "C" void __wrap_##name params                                                                               \
    {                                                                                                                  \
        const bool t = is_top();                                                                                          \
        if (t) { P(g_f, "%u", g_tick); log_in; g_open = 1; }                                                                     \
        g_depth++;                                                                                                     \
        __real_##name args;                                                                                            \
        g_depth--;                                                                                                     \
        if (t) { P(g_f, " ->"); log_out; P(g_f, "\n"); es_flush(); g_open = 0; }                                               \
    }

W(int, emLinePolyCrossCk, (Vec* a, Vec* b, Vec* poly, Vec* hit), (a, b, poly, hit),
  { P(g_f, " LQ"); pv(a); pv(b); for (int i = 0; i < 4; i++) pv(&poly[i]); }, { P(g_f, " %d", r); if (r) pv(hit); })
W(int, emLineCubeCrossCk, (Vec* a, Vec* b, Mtx m, f32 sx, f32 sy, f32 sz, Vec* ofs, Vec* hit), (a, b, m, sx, sy, sz, ofs, hit),
  { P(g_f, " LB"); pv(a); pv(b); len(sx); len(sy); len(sz); pv(ofs); mcols(m); },
  { P(g_f, " %d", r); if (r) pv(hit); })
W(int, emLineCapsuleCrossCk, (Vec* a, Vec* b, Vec* tp, Vec* bm, f32 rr, Vec* hit), (a, b, tp, bm, rr, hit),
  { P(g_f, " LC"); pv(a); pv(b); pv(tp); pv(bm); len(rr); }, { P(g_f, " %d", r); if (r) pv(hit); })
W(YARARE_INFO*, emLineAtCk, (cEm* em, Vec* a, Vec* b, f32 l, int flag), (em, a, b, l, flag),
  { P(g_f, " LA %u", actor(em)); pv(a); pv(b); d2(l); P(g_f, " %x", flag); },
  { box(r); if (r) { pv(&r->pos); d2(r->rad); d2(r->dist); } if (r && svc_env("RE4_E2_BOXGEOM")) boxgeom(em, r); })
W(YARARE_INFO*, emSphereAtCk, (cEm* em, Vec* pos, Vec* pos2, f32 rr, int flag, f32 r2), (em, pos, pos2, rr, flag, r2),
  { P(g_f, " SA %u", actor(em)); pv(pos); pv(pos2); len(rr); P(g_f, " %x", flag); len(r2); },
  { box(r); if (r) d2(r->rad); })
W(int, EmGetDmPos, (cEm* em, Vec* pos, Vec* dir), (em, pos, dir), { P(g_f, " DP %u", actor(em)); box(em->dmg.m_pDamageYarare); },
  { P(g_f, " %d", r); if (r) { pv(pos); ang(dir->y); } })
W(int, EmAtkHitCk2, (EmAtkInfo* info, Vec* p, Vec* o), (info, p, o), { P(g_f, " AK2"); len(info->range); pv(p); pv(o); },
  { P(g_f, " %d", r); box(pPL->dmg.m_pDamageYarare); })
W(YARARE_INFO*, EmAtkHitSubCk2, (EmAtkInfo* info, Vec* p, Vec* o), (info, p, o), { P(g_f, " AKS"); len(info->range); pv(p); pv(o); },
  { box(r); })
W(int, EmAtkHitCk, (EmAtkInfo* info, Vec* p, Vec* o, int noSub), (info, p, o, noSub),
  { P(g_f, " AK"); len(info->range); P(g_f, " %u %x", info->dmg, info->flag); pv(p); pv(o); P(g_f, " %d", noSub); },
  { P(g_f, " %d life %d", r, (int) (s16) pG->pl_life); box(pPL->dmg.m_pDamageYarare); })
W(cEm*, EmAtkLineHitCk, (Vec* a, Vec* b, Vec* hit, Vec* nrm, u32* attr), (a, b, hit, nrm, attr),
  { P(g_f, " AL"); pv(a); pv(b); },
  { box((YARARE_INFO*) r); pv(hit); pv(nrm); if (attr) P(g_f, " %x", *attr); })
W(int, EmRackCk, (cEm* em, Vec* pos, f32 a), (em, pos, a), { P(g_f, " RK %u", actor(em)); pv(pos); ang(a); }, { P(g_f, " %d", r); })
W(int, CheckInWater, (cModel* m, int parts), (m, parts), { P(g_f, " WA %u %d", actor(m), parts); }, { P(g_f, " %d", r); })
W(int, EmCatchMotionMove, (cEm* em, f32 rate, f32 rate2), (em, rate, rate2),
  { P(g_f, " CM %u", actor(em)); P(g_f, " %.9g %.9g", (double) rate, (double) rate2); pv(&em->pos); ang(em->ang.y); },
  { P(g_f, " %d", r); pv(&em->pos); pv(&em->catchOfs); ang(em->ang.y); ang(em->catchTurn); pv((Vec*) &em->mat[0][0]);
    pv((Vec*) &em->mat[1][0]); pv((Vec*) &em->mat[2][0]); P(g_f, " P%.9g,%.9g,%.9g", (double) em->mat[0][3], (double) em->mat[1][3], (double) em->mat[2][3]); })
WV(EmYarareDisp, (cEm* em), (em), { P(g_f, " YD %u", actor(em)); }, {})
WV(EmDmBloodSet2, (cEm* em, int no, int prm, int rnd, int core, int f), (em, no, prm, rnd, core, f),
   { P(g_f, " BD %u %d %d %d %d %d", actor(em), no, prm, rnd, core, f); }, {})
WV(EmPlBloodSet2, (cModel* m, Vec* p, int type, int eff, int est), (m, p, type, eff, est), { P(g_f, " BP %d %d %d", type, eff, est); }, {})
WV(EmSubBloodSet, (cEm* em, Vec* p, int type, int eff, int est), (em, p, type, eff, est),
   { P(g_f, " BS %u", actor(em)); pv(p); P(g_f, " %d %d %d", type, eff, est); }, {})
W(int, PlBombHitCk, (Vec* pos, f32 rr), (pos, rr), { P(g_f, " BH"); pv(pos); len(rr); }, { P(g_f, " %d life %d", r, (int) (s16) pG->pl_life); })
W(int, GetWepTargetListBomb, (Vec* pos, f32 rr, WepTarget* list, int max, int type, int flag), (pos, rr, list, max, type, flag),
  { P(g_f, " BL"); pv(pos); len(rr); P(g_f, " %d %x %x", max, type, flag); },
  { P(g_f, " %d", r); for (int i = 0; i < r && i < max; i++) { P(g_f, " em%u", actor(list[i].em)); box(list[i].part); } })

// ---- the damage volumes (dmg.cpp; native in services/volumes/dmg_vol.cpp) ----
namespace {
// the table's live records (slot, kind, frames left, the shape's numbers): what the point tests read
void dmg_table(const cDmgMgr* m)
{
    P(g_f, " n%u", m->nArray);
    for (u32 i = 0; i < m->nArray; i++) {
        const cDmg* p = (const cDmg*) ((const u8*) m->pArray + m->size * i);
        if ((p->be_flag & 0x201) != 1) continue;
        P(g_f, " s%u:%d:%d:%u", i, p->kind, p->m_Time, p->m_Id);
        if (p->m_Id == 1) for (int k = 0; k < 4; k++) pv(&((const cDmgP4*) p)->m_Pos[k]);
        else { pv(&((const cDmgCyl*) p)->m_Pos); len(((const cDmgCyl*) p)->m_Radius); len(((const cDmgCyl*) p)->m_Height); }
    }
}
}   // namespace
W(int, _ZN7cDmgMgr8hitCheckEP3VecS1_, (cDmgMgr* m, Vec* pos, Vec* out), (m, pos, out), { P(g_f, " DH"); pv(pos); P(g_f, " %d", out != 0); },
  { P(g_f, " %d", r); if (r && out) pv(out); })
W(int, _ZN7cDmgMgr3setEiiP3Vecff, (cDmgMgr* m, int kind, int time, Vec* pos, f32 rr, f32 h), (m, kind, time, pos, rr, h),
  { P(g_f, " DS %d %d", kind, time); pv(pos); len(rr); len(h); }, { P(g_f, " %d", r); dmg_table(m); })
W(int, _ZN7cDmgMgr3setEiiP3Vecf, (cDmgMgr* m, int kind, int time, Vec* pt, f32 h), (m, kind, time, pt, h),
  { P(g_f, " DQ %d %d", kind, time); for (int k = 0; k < 4; k++) pv(&pt[k]); len(h); }, { P(g_f, " %d", r); dmg_table(m); })
WV(_ZN7cDmgMgr4moveEv, (cDmgMgr* m), (m), { P(g_f, " DM"); }, { dmg_table(m); })

// ---- the scenario areas (area.cpp; native in services/volumes/area_vol.cpp) ----
namespace {
void area_rec(const AreaData* a)
{
    P(g_f, " t%d b%d", a->type, a->Be_flag);
    const f32* w = (const f32*) &a->u;
    for (int i = 0; i < 11; i++) P(g_f, " R%.9g", (double) w[i]);
}
}   // namespace
W(int, _Z12AreaHitCheckPvP3Vec, (void* a, Vec* p), (a, p), { P(g_f, " AH t%d", ((AreaData*) a)->type); pv(p); }, { P(g_f, " %d", r); })
W(int, areaHitCheck_xz4, (AreaXZ4* q, Vec* p), (q, p), { P(g_f, " AQ"); pv(p); }, { P(g_f, " %d", r); })
W(int, areaHitCheck_Cylinder, (AreaCylinder* c, Vec* p), (c, p), { P(g_f, " AC"); pv(p); }, { P(g_f, " %d", r); })
namespace {
struct { bool on; Vec p, face; f32 margin, angle; } g_cn;   // the view-cone question asked inside the logged call
}
W(int, AreaViewCheck, (AreaData* a, GeoCone* c), (a, c), { P(g_f, " AV t%d", a->type); g_cn.on = false; },
  { P(g_f, " %d", r); if (g_cn.on) { P(g_f, " cone"); pv(&g_cn.p); pv(&g_cn.face); len(g_cn.margin); ang(g_cn.angle); } })
WV(AreaGetCenterPos, (Vec* out, AreaData* a), (out, a), { P(g_f, " AG t%d", a->type); }, { pv(out); })
WV(AreaGetInsidePos, (Vec* out, AreaData* a), (out, a), { P(g_f, " AI t%d", a->type); }, { pv(out); })
WV(AreaDataInit, (AreaData* a, Vec* pos, u8 type, f32 size, f32 h), (a, pos, type, size, h),
   { P(g_f, " AD %d", type); pv(pos); len(size); len(h); }, { area_rec(a); })
// The view-cone test (geometry.cpp) is not hosted in the fight image (its generated stub answers 0) nor in the PC
// reference: this stand-in answers the same 0 in both builds and logs what it was asked (the trigger's point, look
// direction, margin and facing limit), so the native AreaViewCheck's question is compared.
extern "C" int collision_point_cone_rev_play_face(Vec* p, GeoCone* cone, Vec* face, f32 margin, f32 angle)
{
    (void) cone;
    g_cn.on = true, g_cn.p = *p, g_cn.face = *face, g_cn.margin = margin, g_cn.angle = angle;
    return 0;
}

// Effect starts: logged when made inside an e2 call (the blood placed at a hit), as their own line.
extern "C" void __real_EstSet(int a, int b, Vec* p, Vec* r, int c, int d, int e, int f, u32 g, void* h);
// lane eng-e2b: em10's service functions' log (e2b_dump.cpp) sees every start too (it logs those outside a service call)
extern "C" void e2b_est(int a, int b, Vec* p, Vec* r, int c, int d, int e, int f, u32 g) __attribute__((weak));
extern "C" void __wrap_EstSet(int a, int b, Vec* p, Vec* r, int c, int d, int e, int f, u32 g, void* h)
{
    if (e2b_est) e2b_est(a, b, p, r, c, d, e, f, g);
    if (g_f && g_open && g_depth == 1) {   // inside a top-level e2 call: printed after its line (es_flush)
        if (g_nes < 8) g_es[g_nes] = Es{a, b, c, d, e, f, g, *p, r ? *r : Vec{0.0f, 0.0f, 0.0f}, r != 0};
        g_nes++;
    }
    __real_EstSet(a, b, p, r, c, d, e, f, g, h);
}

// ---- exercises: the same calls in both builds at fixed ticks ----
namespace {
int g_ex = -1;
Vec g_dmg_c, g_dmg_q;   // the planted damage volumes' centres
// every live actor's boxes: three lines across each box (through its middle from 600 units off in x, z and a diagonal,
// to 600 past), a sphere of 150 at its middle moving 200 in x, a still sphere 100 off; and for each damaged box, the
// damage position of a hit registered 300 units away
void ex_geom()
{
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext) {
        if (!(e->be_flag & 1)) continue;
        for (YARARE_INFO* p = &e->hitInfo; p; p = p->next) {
            if (!(p->flags & 1)) continue;
            cModel* part = p->partsNo ? e->getPartsPtr(p->partsNo - 1) : (cModel*) e;
            Vec c;
            PSMTXMultVec(part->mat, &p->ofs, &c);
            c.y += p->height * 0.5f;
            const f32 offs[3][3] = {{600.0f, 37.0f, 0.0f}, {0.0f, -23.0f, 600.0f}, {420.0f, 15.0f, 430.0f}};
            for (const auto& o : offs) {
                Vec a = {c.x - o[0], c.y - o[1], c.z - o[2]}, b = {c.x + o[0], c.y + o[1], c.z + o[2]};
                emLineAtCk(e, &a, &b, 1e16f, 2);
            }
            Vec s0 = {c.x - 200.0f, c.y, c.z}, s1 = {c.x - 100.0f, c.y + 40.0f, c.z + 60.0f};
            emSphereAtCk(e, &c, &s0, 150.0f, 0x18, 150.0f);
            emSphereAtCk(e, &s1, &s1, 120.0f, 0x18, 300.0f);
        }
        YARARE_INFO* keep = e->dmg.m_pDamageYarare;
        Vec from = e->dmg.m_PosFrom;
        int k = 0;
        for (YARARE_INFO* p = &e->hitInfo; p && k < 6; p = p->next, k++) {
            if (!(p->flags & 1)) continue;
            const u16 fl = p->flags;
            p->flags &= ~0x4000;
            e->dmg.m_pDamageYarare = p;
            e->dmg.m_PosFrom = e->pos;
            e->dmg.m_PosFrom.x += 300.0f * (k & 1 ? 1.0f : -1.0f);
            e->dmg.m_PosFrom.y += 900.0f - 200.0f * k;
            e->dmg.m_PosFrom.z += 170.0f;
            Vec pos, dir;
            EmGetDmPos(e, &pos, &dir);
            p->flags = fl;
        }
        e->dmg.m_pDamageYarare = keep;
        e->dmg.m_PosFrom = from;
    }
}

// The pure shapes on generated inputs (a fixed generator of this file, the same stream in both builds): capsules of
// random length, radius and direction against segments aimed near them (some starting inside, some short, some along
// the axis); boxes in random frames (rotation, uneven scale, every 8th mirrored) against segments; planar quads (a box's
// face, from both sides).
u32 g_lcg = 12345u;
f32 urand() { g_lcg = g_lcg * 1103515245u + 12345u; return (f32) ((g_lcg >> 8) & 0xFFFF) / 65536.0f; }
f32 srand1() { return urand() * 2.0f - 1.0f; }
Vec rvec(f32 s) { return Vec{srand1() * s, srand1() * s, srand1() * s}; }
Vec vadd3(const Vec& a, const Vec& b) { return Vec{a.x + b.x, a.y + b.y, a.z + b.z}; }
void ex_shapes(int n)
{
    const Vec base = pPL ? pPL->pos : Vec{0.0f, 0.0f, 0.0f};
    for (int i = 0; i < n; i++) {
        // capsule
        Vec bottom = vadd3(base, rvec(800.0f)), axis = rvec(600.0f);
        if (i % 9 == 0) axis = Vec{0.0f, 0.0f, 0.0f};
        Vec top = vadd3(bottom, axis);
        const f32 r = 40.0f + urand() * 260.0f;
        Vec a = vadd3(bottom, rvec(1500.0f)), b = vadd3(top, rvec(i % 5 == 0 ? 200.0f : 900.0f));
        if (i % 11 == 0) a = vadd3(bottom, rvec(r * 0.4f));            // starting inside
        if (i % 13 == 0) b = vadd3(a, rvec(0.15f));                     // too short
        if (i % 17 == 0) { a = vadd3(bottom, Vec{-axis.x, -axis.y, -axis.z}); b = vadd3(top, axis); }   // along the axis
        Vec hit;
        emLineCapsuleCrossCk(&a, &b, &top, &bottom, r, &hit);
        // box in a random frame
        Mtx m;
        Vec rot = rvec(3.1415927f);
        RotMatrix(m, &rot);
        const f32 sc[3] = {0.6f + urand(), 0.6f + urand(), 0.6f + urand()};
        for (int rr = 0; rr < 3; rr++)
            for (int c = 0; c < 3; c++) m[rr][c] *= sc[c] * ((i % 8 == 7 && c == 0) ? -1.0f : 1.0f);
        m[0][3] = base.x + srand1() * 500.0f, m[1][3] = base.y + srand1() * 500.0f, m[2][3] = base.z + srand1() * 500.0f;
        Vec ofs = rvec(100.0f);
        const f32 sx = 50.0f + urand() * 300.0f, sy = 50.0f + urand() * 600.0f, sz = 50.0f + urand() * 300.0f;
        Vec ca = {m[0][3] + srand1() * 1200.0f, m[1][3] + srand1() * 1200.0f, m[2][3] + srand1() * 1200.0f};
        Vec cb = {m[0][3] + srand1() * 300.0f, m[1][3] + 200.0f + srand1() * 300.0f, m[2][3] + srand1() * 300.0f};
        if (i % 7 == 0) ca = Vec{m[0][3], m[1][3] + sy * 0.5f, m[2][3]};   // starting inside
        emLineCubeCrossCk(&ca, &cb, m, sx, sy, sz, &ofs, &hit);
        // a quad (the box's +z face) from in front and from behind
        Vec q[4];
        const f32 lx[4] = {-sx, sx, sx, -sx}, ly[4] = {0.0f, 0.0f, sy, sy};
        for (int k = 0; k < 4; k++) {
            const Vec l = {lx[k], ly[k], sz};
            PSMTXMultVec(m, &l, &q[k]);
        }
        Vec qa = vadd3(q[0], vadd3(rvec(400.0f), Vec{m[0][2] * 800.0f, m[1][2] * 800.0f, m[2][2] * 800.0f}));
        Vec qb = vadd3(q[2], rvec(400.0f));
        emLinePolyCrossCk(&qa, &qb, q, &hit);
        emLinePolyCrossCk(&qb, &qa, q, &hit);
    }
}

// The attack checks against Leon (and the partner when there is one): spheres of 250 around his chest arriving from
// four sides at three heights (moving, and still), lines through him, the blast list at each Ganado and the blood at
// his damaged box; a rack planted in a free character slot for EmRackCk (the slot restored after the call).
void ex_attack(unsigned t)
{
    if (!pPL) return;
    const Vec c = pPL->pos;
    EmAtkInfo info = {250.0f, 0, 10, 0, 0, 0};
    for (int s = 0; s < 4; s++) {
        const f32 dx = s == 0 ? 1.0f : s == 1 ? -1.0f : 0.0f, dz = s == 2 ? 1.0f : s == 3 ? -1.0f : 0.0f;
        for (int h = 0; h < 3; h++) {
            const f32 y = c.y + 500.0f + 500.0f * h;
            Vec p = {c.x + dx * 150.0f, y, c.z + dz * 150.0f}, o = {c.x + dx * 450.0f, y, c.z + dz * 450.0f};
            if (EmAtkHitCk2(&info, &p, &o)) EmPlBloodSet2(pPL, &p, h == 1, 0xFF, 0xFF);
            Vec o2 = {p.x + 30.0f, p.y, p.z};
            EmAtkHitCk2(&info, &p, &o2);
            EmAtkHitSubCk2(&info, &p, &o);
            Vec la = {c.x + dx * 2000.0f + dz * 37.0f, y, c.z + dz * 2000.0f - dx * 41.0f}, lb = {c.x - dx * 900.0f, y + 60.0f, c.z - dz * 900.0f};
            Vec hit, nrm;
            u32 attr;
            EmAtkLineHitCk(&la, &lb, &hit, &nrm, &attr);
            if (pSUB) EmSubBloodSet(pPL, &p, h & 1, 0xFF, 0xFF);
        }
    }
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext) {
        if (e == (cEm*) pPL || !(e->be_flag & 1)) continue;
        WepTarget list[8];
        Vec bp = {e->pos.x + 300.0f, e->pos.y + 800.0f, e->pos.z - 200.0f};
        GetWepTargetListBomb(&bp, 2200.0f, list, 4, 0x10, 0);
        GetWepTargetListBomb(&bp, 900.0f, list, 2, 0x10, 1);
    }
    // a rack in a free slot, ahead of Leon or not, by tick
    for (u32 i = 1; i < EmMgr.nArray; i++) {
        cEm* e = (cEm*) EmMgr.workAt(i);
        if (!e || (e->be_flag & 0x601)) continue;
        static u8 save[0x1000];
        const u32 n = EmMgr.size < sizeof(save) ? EmMgr.size : sizeof(save);
        __builtin_memcpy(save, (void*) e, n);
        e->be_flag = 1, e->id = 0x45, e->hp = 1;
        Vec rr = {0.0f, 0.3f * (f32) (t % 5), 0.0f};
        RotMatrix(e->mat, &rr);
        const f32 ahead = 300.0f + 150.0f * (f32) (t % 13);
        e->pos = Vec{c.x + __builtin_sinf(pPL->ang.y) * ahead, c.y, c.z + __builtin_cosf(pPL->ang.y) * ahead};
        e->mat[0][3] = e->pos.x, e->mat[1][3] = e->pos.y, e->mat[2][3] = e->pos.z;
        EMRACK_WK(e)->size = Vec{200.0f, 400.0f, 120.0f};
        Vec to = c;
        EmRackCk(pPL, &to, pPL->ang.y);
        EmRackCk(pPL, &to, pPL->ang.y + 1.6f);
        __builtin_memcpy((void*) e, save, n);
        break;
    }
}

// The caught-actor follow on the first live Ganado, its record kept and put back after the call (its own move runs
// later in the tick from the record as it was).
void ex_catch(unsigned t)
{
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext) {
        if (e == (cEm*) pPL || !(e->be_flag & 1)) continue;
        static u8 save[0x1000];
        const u32 n = EmMgr.size < sizeof(save) ? EmMgr.size : sizeof(save);
        __builtin_memcpy(save, (void*) e, n);
        e->dmgType = (int) pPL;
        e->catchOfs = Vec{200.0f, 30.0f, -120.0f};
        e->catchTurn = 0.4f + 0.01f * (f32) (t % 10);
        pPL->x3A8 = Vec{pPL->pos.x - 12.0f, pPL->pos.y, pPL->pos.z + 7.0f};
        EmCatchMotionMove(e, 0.2f, 0.25f);
        __builtin_memcpy((void*) e, save, n);
        pPL->x3A8 = pPL->pos;
        return;
    }
}
}   // namespace
extern "C" void e2_ready()
{
    g_f = svc_out_open("e2.txt", "w");
    if (&emhit_control) {
        const char* c = svc_env("RE4_SVC_CONTROL");
        if (c && !__builtin_strcmp(c, "hitwide")) emhit_control = 1;
        if (c && !__builtin_strcmp(c, "dmposmid")) emhit_control = 2;
        if (c && !__builtin_strcmp(c, "sphereshort")) emhit_control = 3;
        if (c && !__builtin_strcmp(c, "hitnudge")) emhit_control = 4;
    }
    if (&dmg_control) {   // lane eng-e2a item 2: every damage cylinder 10% wider
        const char* c = svc_env("RE4_SVC_CONTROL");
        if (c && !__builtin_strcmp(c, "dmgwide")) dmg_control = 1;
    }
    if (&area_control) {   // lane eng-e2a item 3: every cylinder area 10% wider, every area's band 100 higher
        const char* c = svc_env("RE4_SVC_CONTROL");
        if (c && !__builtin_strcmp(c, "areawide")) area_control = 1;
    }
    const char* e = svc_env("RE4_SVC_EXERCISE");
    g_ex = e && !__builtin_strcmp(e, "e2geom") ? 1 : 0;
}
extern "C" void e2_tick(unsigned t)
{
    g_tick = t;
    if (g_ex != 1 || !g_f) return;
    if (t >= 30 && t % 7 == 2) {
        P(g_f, "# e2geom boxes %u\n", t);
        ex_geom();
    }
    if (t == 20 || t == 400) {
        P(g_f, "# e2geom shapes %u\n", t);
        ex_shapes(1500);
    }
    if (t >= 40 && t % 11 == 4) {
        P(g_f, "# e2geom attack %u\n", t);
        ex_attack(t);
    }
    if (t >= 60 && t <= 90) {
        P(g_f, "# e2geom catch %u\n", t);
        ex_catch(t);
    }
    // the consequences once each: an attack that lands (50 damage, the behaviour's reaction), a blast's knock-down
    // (2800 units off, radius 3000) and a grenade list (the player's test inside it, the blast 7000 units off)
    if (pPL && t == 250) {
        P(g_f, "# e2geom attack-hit %u\n", t);
        EmAtkInfo info = {300.0f, 0, 50, 0, 0, 0};
        Vec p = {pPL->pos.x + 100.0f, pPL->pos.y + 1000.0f, pPL->pos.z}, o = {pPL->pos.x + 600.0f, pPL->pos.y + 1000.0f, pPL->pos.z};
        EmAtkHitCk(&info, &p, &o, 0);
    }
    // damage volumes (kinds 0x21 and 0x22, which no behaviour reacts to): a cylinder at the first Ganado and a quad
    // beside Leon, then a grid of point tests around each until both have expired (lifetimes 40 and 25 ticks)
    if (pPL && t == 33) {
        P(g_f, "# e2geom dmg-set %u\n", t);
        Vec c = pPL->pos;
        for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext)
            if (e != (cEm*) pPL && (e->be_flag & 1)) { c = e->pos; break; }
        g_dmg_c = Vec{c.x + 150.0f, c.y + 20.0f, c.z - 90.0f};
        DmgMgr.set(0x21, 40, &g_dmg_c, 700.0f, 400.0f);
        const Vec& l = pPL->pos;
        Vec q[4] = {{l.x + 300.0f, l.y, l.z - 200.0f}, {l.x + 1100.0f, l.y, l.z - 350.0f}, {l.x + 1250.0f, l.y, l.z + 500.0f},
                    {l.x + 250.0f, l.y, l.z + 420.0f}};
        g_dmg_q = Vec{l.x + 700.0f, l.y, l.z + 100.0f};
        DmgMgr.set(0x22, 25, q, 300.0f);
    }
    if (pPL && t >= 33 && t <= 80 && t % 3 == 0) {
        P(g_f, "# e2geom dmg-probe %u\n", t);
        for (int k = 0; k < 2; k++) {
            const Vec& c = k ? g_dmg_q : g_dmg_c;
            for (int i = -2; i <= 2; i++)
                for (int j = -2; j <= 2; j++) {
                    Vec p = {c.x + 330.0f * i, c.y + 190.0f * (i + j), c.z + 310.0f * j}, out;
                    DmgMgr.hitCheck(&p, (i + j) & 1 ? &out : 0);
                }
        }
    }
    // scenario areas: every 9th tick from 34 to 160, a square, a cylinder and an eye trigger made around Leon
    // (AreaDataInit), the square's corners then moved into an irregular quad, an area of an unknown kind; each asked for
    // its centre, three inside points and the view check, and a grid of 49 points tested against each
    if (pPL && t >= 34 && t <= 160 && t % 9 == 7) {
        P(g_f, "# e2geom areas %u\n", t);
        AreaData a[4] = {};   // the unknown kind is left as it was: zero in both builds
        Vec c = pPL->pos;
        for (int k = 0; k < 4; k++) {
            Vec at = {c.x + 400.0f * k - 600.0f, c.y + 20.0f * (f32) (t % 5), c.z + 250.0f};
            AreaDataInit(&a[k], &at, k == 3 ? 7 : (u8) (k + 1), 1200.0f + 37.0f * (f32) (t % 7), 1500.0f);
        }
        for (int i = 0; i < 4; i++) a[0].u.xz4.p[i].x += srand1() * 250.0f, a[0].u.xz4.p[i].z += srand1() * 250.0f;
        a[2].u.eye.ang_x = srand1() * 0.6f, a[2].u.eye.ang_y = srand1() * 3.1f, a[2].u.eye.open = (t % 2) ? 0.0f : 1.2f;
        GeoCone cone = {{c.x, c.y + 1600.0f, c.z}, {0.0f, -0.6f, 0.8f}, 0.5f, 3000.0f, 0.0f};
        for (int k = 0; k < 4; k++) {
            Vec o;
            AreaGetCenterPos(&o, &a[k]);
            for (int n = 0; n < 3; n++) AreaGetInsidePos(&o, &a[k]);
            AreaViewCheck(&a[k], &cone);
            for (int i = -3; i <= 3; i++)
                for (int j = -3; j <= 3; j++) {
                    Vec p = {c.x + 230.0f * i - 300.0f, c.y + 330.0f * (i + j) - 150.0f, c.z + 210.0f * j + 250.0f};
                    AreaHitCheck(&a[k], &p);
                }
        }
        Vec p = {c.x - 650.0f, c.y + 10.0f, c.z + 300.0f};
        areaHitCheck_xz4(&a[0].u.xz4, &p);
        areaHitCheck_Cylinder(&a[1].u.cyl, &p);
    }
    if (pPL && t == 270) {
        P(g_f, "# e2geom blast %u\n", t);
        Vec b = {pPL->pos.x + 2800.0f, pPL->pos.y + 500.0f, pPL->pos.z};
        PlBombHitCk(&b, 3000.0f);
        WepTarget list[8];
        Vec g = {pPL->pos.x - 7000.0f, pPL->pos.y + 300.0f, pPL->pos.z};
        GetWepTargetListBomb(&g, 2500.0f, list, 4, 0xD, 0);
    }
}
extern "C" void e2_finish()
{
    if (!g_f) return;
    svc_out_close(g_f);
    g_f = 0;
}
