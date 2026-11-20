// svc4_dump.cpp (game side; lane eng-svc4): the boundary log of the round-4 native services, linked into odump (the
// original units) and native (the engine bodies) alike. RE4_SVC_OUT=<dir> receives svc4.txt: every call the behaviour
// makes to a service entry point (--wrap: svc4.mk SVC4_WRAP), in call order, with its tick, inputs and outputs as
// float bits. Only top-level calls are logged: not those made inside another logged call or inside a collision query
// (svc_dump.cpp's depth), so both builds log the same boundary whatever their internals call. svc_compare.py's
// companion svc4_compare.py compares the two logs line by line; svc4.txt's last lines are the native counters.
#include "hostref.h"
#include "model.h"
#include "em.h"
#include "obj.h"
#include "atari.h"
#include "at_sub.h"
#include "at_mod.h"
#include "../../services/volumes/volumes.h"
#include "../../services/collision/col_model.h"
#include "../../services/routes/routes.h"
#include "route_ck.h"

extern "C" {
void* svc_out_open(const char* name, const char* mode);
void svc_out_printf(void* f, const char* fmt, ...);
void svc_out_close(void* f);
const char* svc_env(const char* name);
int svc_col_depth(void);
extern VolCounters vol_cnt __attribute__((weak));
extern int vol_control __attribute__((weak));
extern ColModelCounters colm_cnt __attribute__((weak));
extern int colm_control __attribute__((weak));
extern RouteCounters route_cnt __attribute__((weak));
extern int route_control __attribute__((weak));
}
#define P svc_out_printf

namespace {
void* g_f;
unsigned g_tick;
int g_depth;
u32 bits(f32 f)
{
    u32 u;
    __builtin_memcpy(&u, &f, 4);
    return u;
}
void pv(const Vec* v)
{
    if (v) P(g_f, " %08x,%08x,%08x", bits(v->x), bits(v->y), bits(v->z));
    else P(g_f, " -");
}
u32 actor(const void* m)
{
    const u32 a = (u32) m, elo = (u32) EmMgr.pArray, olo = (u32) ObjMgr.pArray;
    if (a >= elo && a < elo + EmMgr.size * EmMgr.nArray) return (a - elo) / EmMgr.size;
    if (a >= olo && a < olo + ObjMgr.size * ObjMgr.nArray) return 64 + (a - olo) / ObjMgr.size;
    return 999;
}
// every alive body: model position and body position, folded (pushes move other actors than the caller)
u32 bodies()
{
    u32 h = 2166136261u;
    auto mix = [&](u32 w) { h = (h ^ w) * 16777619u; };
    for (int l = 0; l < 2; l++)
        for (cEm* e = l ? (cEm*) ObjMgr.pAlive : (cEm*) EmMgr.pAlive; e; e = (cEm*) e->pNext) {
            mix(actor(e));
            mix(bits(e->pos.x)), mix(bits(e->pos.y)), mix(bits(e->pos.z));
            mix(bits(e->atari.m_Pos.x)), mix(bits(e->atari.m_Pos.y)), mix(bits(e->atari.m_Pos.z));
            mix(e->atari.m_stat);
        }
    return h;
}
void body(const cAtariInfo* a)
{
    P(g_f, " %08x %08x %08x %08x %x %x %x", bits(a->m_radius), bits(a->m_radius2), bits(a->m_radius_n), bits(a->m_radius2_n),
      a->m_hokan, a->m_flag, a->m_stat);
}
}   // namespace

extern "C" void svc4_ready()
{
    g_f = svc_out_open("svc4.txt", "w");
    if (&vol_control) {
        const char* c = svc_env("RE4_SVC_CONTROL");
        if (c && !__builtin_strcmp(c, "volpush")) vol_control = 1;
        if (c && !__builtin_strcmp(c, "volline")) vol_control = 2;
    }
    if (&colm_control) {
        const char* c = svc_env("RE4_SVC_CONTROL");
        if (c && !__builtin_strcmp(c, "colfloor")) colm_control = 1;
        if (c && !__builtin_strcmp(c, "colwall")) colm_control = 2;
    }
    if (&route_control) {
        const char* c = svc_env("RE4_SVC_CONTROL");
        if (c && !__builtin_strcmp(c, "routenear")) route_control = 1;
        if (c && !__builtin_strcmp(c, "routehop")) route_control = 2;
    }
}
extern "C" void svc4_tick(unsigned t) { g_tick = t; }
extern "C" void svc4_finish()
{
    if (!g_f) return;
    if (&vol_cnt) {
        const VolCounters& v = vol_cnt;
        P(g_f, "# volumes: at_checks %u at_skipped %u pairs %u pairs_prio %u pushes %u pairs_box %u line_tests %u line_bodies %u line_hits %u "
               "capsule_tests %u box_sphere %u debug_draws %u\n",
          v.at_checks, v.at_skipped, v.pairs, v.pairs_prio, v.pushes, v.pairs_box, v.line_tests, v.line_bodies, v.line_hits,
          v.capsule_tests, v.box_sphere, v.debug_draws);
    }
    if (&colm_cnt) {
        const ColModelCounters& c = colm_cnt;
        P(g_f, "# collision response: checks %u rects %u spheres %u slides %u floors %u floor_lost %u pieces %u debug_draws %u\n",
          c.checks, c.rects, c.spheres, c.slides, c.floors, c.floor_lost, c.pieces, c.debug_draws);
    }
    if (&route_cnt) {
        const RouteCounters& r = route_cnt;
        P(g_f, "# routes: near_calls %u near_cached %u near_lines %u near_none %u steps %u steps_direct %u lines %u dists %u debug_draws %u\n",
          r.near_calls, r.near_cached, r.near_lines, r.near_none, r.steps, r.steps_direct, r.lines, r.dists, r.debug_draws);
    }
    svc_out_close(g_f);
    g_f = 0;
}

#define TOP (g_depth == 0 && svc_col_depth() == 0 && g_f)
#define W(ret, mangled, params, args, log_in, log_out)                                                               \
    extern "C" ret __real_##mangled params;                                                                          \
    extern "C" ret __wrap_##mangled params                                                                           \
    {                                                                                                                \
        const bool top = TOP;                                                                                        \
        if (top) { P(g_f, "%u", g_tick); log_in; }                                                                  \
        g_depth++;                                                                                                   \
        ret r = __real_##mangled args;                                                                               \
        g_depth--;                                                                                                   \
        if (top) { P(g_f, " ->"); log_out; P(g_f, "\n"); }                                                          \
        return r;                                                                                                    \
    }
#define WV(mangled, params, args, log_in, log_out)                                                                   \
    extern "C" void __real_##mangled params;                                                                         \
    extern "C" void __wrap_##mangled params                                                                          \
    {                                                                                                                \
        const bool top = TOP;                                                                                        \
        if (top) { P(g_f, "%u", g_tick); log_in; }                                                                  \
        g_depth++;                                                                                                   \
        __real_##mangled args;                                                                                       \
        g_depth--;                                                                                                   \
        if (top) { P(g_f, " ->"); log_out; P(g_f, "\n"); }                                                          \
        return;                                                                                                      \
    }

// ---- actor volumes (atariInfo, at_mod, at_sub) ----
WV(EmAtCheck, (cEm* em), (em), { P(g_f, " AT %u", actor(em)); pv(&em->pos); },
   { pv(&em->pos); pv(&em->atari.m_Pos); P(g_f, " %x h%08x", em->atari.m_stat, bodies()); })
W(int, EmHitCheck, (Vec* hit, Vec* nrm, Vec* p0, Vec* p1, int flag), (hit, nrm, p0, p1, flag),
  { P(g_f, " EH"); pv(p0); pv(p1); P(g_f, " %x", flag); }, { P(g_f, " %d", r); pv(hit); if (r) pv(nrm); })
W(int, ObjHitCheck, (Vec* hit, Vec* nrm, Vec* p0, Vec* p1, int flag), (hit, nrm, p0, p1, flag),
  { P(g_f, " OH"); pv(p0); pv(p1); P(g_f, " %x", flag); }, { P(g_f, " %d", r); pv(hit); if (r) pv(nrm); })
W(int, ObaLineHitChk, (cEm* m, cAtariInfo* info, Vec* a, Vec* b, Vec* hit, Vec* nrm), (m, info, a, b, hit, nrm),
  { P(g_f, " OB %u", actor(m)); pv(a); pv(b); }, { P(g_f, " %d", r); if (r) { pv(hit); pv(nrm); } })
W(u32, AtSphereCapsuleCk, (Vec* c, Vec* p0, f32 rad, f32 r2, Vec* p1), (c, p0, rad, r2, p1),
  { P(g_f, " SC"); pv(c); pv(p0); pv(p1); P(g_f, " %08x %08x", bits(rad), bits(r2)); }, { P(g_f, " %u", r); })
W(u32, AtBoxCapsuleCk3, (Vec* box, Vec* p0, f32 rr, Vec* p1), (box, p0, rr, p1),
  { P(g_f, " BC"); for (int i = 0; i < 8; i++) pv(&box[i]); pv(p0); pv(p1); P(g_f, " %08x", bits(rr)); }, { P(g_f, " %u", r); })
W(int, At_box_sphere_ck, (Vec* box, Vec* p, f32 rr), (box, p, rr),
  { P(g_f, " BS"); for (int i = 0; i < 8; i++) pv(&box[i]); pv(p); P(g_f, " %08x", bits(rr)); }, { P(g_f, " %d", r); })
// ---- per-model collision response (atari): check / checkAir / getFloor are logged by svc_dump.cpp (col.txt) ----
extern "C" AtEffInfo* __real__ZN7cEatMgr10getEffInfoEi(cEatMgr* e, int type);
extern "C" AtEffInfo* __wrap__ZN7cEatMgr10getEffInfoEi(cEatMgr* e, int type)
{
    const bool top = TOP;
    AtEffInfo* r = __real__ZN7cEatMgr10getEffInfoEi(e, type);
    if (top) P(g_f, "%u EI %d -> %d %x\n", g_tick, type, r != 0, r ? r->flag : 0);
    return r;
}
W(int, EatGetEffectType, (u32 attr), (attr), { P(g_f, " ET %x", attr); }, { P(g_f, " %d", r); })
W(u32, At_poly_line_ck, (AtPolyData* pd, Vec* out, AtPoly* poly, Vec* v0, Vec* v1, u32 flag, u32 mask),
  (pd, out, poly, v0, v1, flag, mask), { P(g_f, " PL %x", (u32) poly); pv(v0); pv(v1); P(g_f, " %x %x", flag, mask); },
  { P(g_f, " %x", r); if (r) pv(out); })
WV(YarareInit, (cEm* em, f32 x, f32 y, f32 z, f32 w, f32 h, s16 no, u16 flags), (em, x, y, z, w, h, no, flags),
   { P(g_f, " YI %u %08x %08x %08x %08x %08x %d %x", actor(em), bits(x), bits(y), bits(z), bits(w), bits(h), no, flags); }, {})
WV(YarareAdd, (cEm* em, YARARE_INFO* box, f32 x, f32 y, f32 z, f32 w, f32 h, s16 no, u16 flags),
   (em, box, x, y, z, w, h, no, flags),
   { P(g_f, " YA %u %d %08x %08x %08x %08x %08x %d %x", actor(em), (int) ((char*) box - (char*) em), bits(x), bits(y), bits(z), bits(w),
       bits(h), no, flags); },
   { int n = 0; for (YARARE_INFO* p = &em->hitInfo; p; p = p->next) n++; P(g_f, " chain %d", n); })
WV(_ZN10cAtariInfo4moveEv, (cAtariInfo* a), (a), { P(g_f, " AM %u", actor(a->m_pMod)); body(a); }, { body(a); })
WV(_ZN10cAtariInfo3setEiff, (cAtariInfo* a, int mode, f32 x, f32 y), (a, mode, x, y),
   { P(g_f, " AS %d %08x %08x", mode, bits(x), bits(y)); body(a); }, { body(a); })
WV(_ZN10cAtariInfo11setPriorityEi, (cAtariInfo* a, int prio), (a, prio), { P(g_f, " AP %d %x", prio, a->m_flag); }, { P(g_f, " %x", a->m_flag); })
WV(_ZN10cAtariInfo6getPosEP6cModelP3Vec, (cAtariInfo* a, cModel* m, Vec* out), (a, m, out), { P(g_f, " AG %u", actor(m)); },
   { pv(out); })
WV(_ZN10cAtariInfo14getSpeedVectorEP6cModelP3VecS3_, (cAtariInfo* a, cModel* m, Vec* o, Vec* n), (a, m, o, n),
   { P(g_f, " AV %u", actor(m)); }, { pv(o); pv(n); })
// ---- routes (route_ck) ----
namespace {
void rck(const cEm* e) { P(g_f, " rck %x %d %d %d", e->RckStat, e->RckMy, e->RckTo, e->RckNear); }
}
W(int, RouteCkToPos, (cEm* em, Vec* t, Vec* out, int flag, f32* dist), (em, t, out, flag, dist),
  { P(g_f, " RP %u", actor(em)); pv(&em->pos); pv(t); P(g_f, " %x %d", flag, dist != 0); },
  { P(g_f, " %d", r); pv(out); if (dist) P(g_f, " %08x", bits(*dist)); rck(em); })
W(int, RouteCkToEm, (cEm* em, cEm* t, Vec* out, int flag), (em, t, out, flag),
  { P(g_f, " RE %u %u", actor(em), actor(t)); pv(&em->pos); pv(&t->pos); P(g_f, " %x", flag); },
  { P(g_f, " %d", r); pv(out); rck(em); rck(t); })
WV(RouteCkEscEm, (cEm* em, cEm* from, Vec* out), (em, from, out), { P(g_f, " RX %u %u", actor(em), actor(from)); },
   { pv(out); rck(em); })
W(int, RouteCkPosToPos, (Vec* a, Vec* b, Vec* out), (a, b, out), { P(g_f, " RQ"); pv(a); pv(b); }, { P(g_f, " %d", r); pv(out); })
W(f32, RouteCkPosToPosDis, (Vec* a, Vec* b), (a, b), { P(g_f, " RD"); pv(a); pv(b); }, { P(g_f, " %08x", bits(r)); })
W(f32, RouteCkGetDist, (int a, int b), (a, b), { P(g_f, " RG %d %d", a, b); }, { P(g_f, " %08x", bits(r)); })
W(int, RouteCkConnectPosCk, (Vec* a, Vec* b), (a, b), { P(g_f, " RC"); pv(a); pv(b); }, { P(g_f, " %d", r); })
W(s8, getNearPoint, (Vec* pos, int mode, int mask), (pos, mode, mask), { P(g_f, " NP"); pv(pos); P(g_f, " %d %x", mode, mask); },
  { P(g_f, " %d", r); })
W(int, getNearInfo, (cEm* em, int mode, int mask), (em, mode, mask), { P(g_f, " NI %u", actor(em)); P(g_f, " %d %x", mode, mask); },
  { P(g_f, " %d", r); rck(em); })
WV(RouteCk, (), (), { P(g_f, " RK"); }, {})
