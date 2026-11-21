// e2f_dump.cpp (game side; lane eng-e2f): the boundary log of sce_at's service functions (the scene attachments: the
// room set-up, area geometry, hit, sight and screen tests, item models and glows, the shadow area's handler; native in
// services/scene/sce_at_svc.cpp), linked into e2fodump (sce_at's original bodies) and e2fnative (the engine's) alike
// (svc/svc.mk; svc/e2fcheck.sh runs them). RE4_SVC_OUT=<dir> receives e2f.txt.
//
// The reference does not host the scenario layer (its entry points are stubs): these two builds add sce_at's own object
// with every global it defines weak (the reference's stubs keep answering the rest, as in odump), its file statics made
// weak globals by services/scene/sce_at_weak.h, and the at-list (libgpu's original in e2fodump, services/scene/at_list.cpp
// in e2fnative). The room's attachment data (r101: AEV and ITA from the room archive) is set up at the start
// (SceAtInit), and from tick 30, every 5th tick, each function is called on the room's records and on planted inputs,
// its outputs logged; every record is put back as it was. Tokens as svc/e2_compare.py reads them (--log e2f.txt):
// integers and hex exact; "P" x,y,z within max(0.01 unit, 2^-20 of the value); "A" an angle within 0.01 degree.
//
//   IN    the at-list after SceAtInit: each record in walk order (number, bucket, type)
//   GA    sceAtGetArea: a record's area (type, corners or point) as it is, then on a planted parent (Leon, his root
//         part), with and without its rotation
//   HC    sceAtHitCheck: Leon and the first live Ganado tested against each record as SceAtCheck tests them (the point
//         250 above the feet, the front point 550 ahead), on the record's own parent and on the planted ones
//   IS    SceAtItemHitCheck: each item record seen from Leon (its own point, and Leon's)
//   SC    InScreenCheck: each record's centre, each Ganado (feet and 1,500 above); the screen 512 x 448 as the game
//         sets it (the reference sets none)
//   HC f  sceAtHitCheck on a planted area round Leon facing each way (-180 to 180 degrees), narrow and wide
//   HB    SceAtHitCheck: the 256 record bits after two planted hits
//   LP    sceAtGetLadderPos: a planted ladder at Leon's feet, its angle turning with the tick
//   IC    sceAtCheckItemEffectCol: every item id once (the item table planted: itemInfo answers a fixed type per id)
//   MP    SceAtItemModelPtr: every record number
//   EF    (every 50th tick, with SM and CP) sceAtItemEffSet / sceAtItemEffDelete: each item record with each glow type, alone, on a planted model, on a
//         planted parent (each part class, in the rooms the parted glows need), the effect starts (ES) and stops (ED)
//   SM    SceAtSetItemModel (and sceAtSetItemModelParent): a planted item model put on each item record, with and
//         without the record's rotation and a parent; sceAtCheckItemModelParent on each item record (CP)
//   SH    the shadow area's handler on planted records (shown, hidden, done)
// Controls (RE4_SVC_CONTROL, e2fnative only; services/scene/sce_at_svc.cpp): atparent, atfacing, screenmid, itemsight,
// hitbit, glowkind, itemcol, itemlink, ladderofs, itemrot, shdbit, glowstop, modelptr, parentscale: each must make
// e2f.txt differ.
#include "hostref.h"
#include "global.h"
#include "main_sub.h"
#include "model.h"
#include "obj.h"
#include "em.h"
#include "player.h"
#include "sce_at.h"
#include "area.h"
#include "item.h"
#include "esp.h"
#include "est.h"
#include "shadow.h"
#include <new>

extern "C" {
void* svc_out_open(const char* name, const char* mode);
void svc_out_printf(void* f, const char* fmt, ...);
void svc_out_close(void* f);
const char* svc_env(const char* name);
extern int sce_svc_control __attribute__((weak));
int sceAtFunc_shd_disp(SceAtWork* w, cModel* m);   // sce_at's static handler, a weak global by sce_at_weak.h
}
void* GetDataExt(void* arc, const char* tag, int no);
int SceAtSetItemModel(SceAtWork* w, cModel* m);
void PSMTXMultVec(const Mtx m, const Vec* src, Vec* dst);

#define P svc_out_printf
namespace {
void* g_f;
unsigned g_tick;
int g_in;   // inside an exercise call: the wraps below answer the planted inputs and log
unsigned g_pull;
SceAtWork* g_rec[256];
int g_n;
alignas(32) unsigned char g_item_buf[sizeof(cObj)], g_shd_buf[sizeof(cObj)];
alignas(32) unsigned char g_parts_buf[2][1024];
cObj* g_item;
cObj* g_shadow;

void pt(const char* k, const Vec& v) { P(g_f, " %s%.6f,%.6f,%.6f", k, v.x, v.y, v.z); }
void area_line(const char* tag, int no, const AreaData& a)
{
    P(g_f, "%u %s %d %d %d", g_tick, tag, no, a.Be_flag, a.type);
    switch (a.type) {
    case 1:
        for (int i = 0; i < 4; i++) P(g_f, " P%.6f,%.6f,%.6f", a.u.xz4.p[i].x, a.u.xz4.floor, a.u.xz4.p[i].z);
        break;
    case 2:
    case 3: P(g_f, " P%.6f,%.6f,%.6f", a.u.cyl.x, a.u.cyl.floor, a.u.cyl.z); break;
    }
    P(g_f, "\n");
}
cEm* first_ganado()
{
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext)
        if (e != (cEm*) pPL && e->id >= 0x10 && e->id <= 0x20) return e;
    return 0;
}
// a character's two test points, as SceAtCheck takes them
void points(cModel* m, Vec* pos, Vec* front)
{
    *pos = m->pos;
    pos->y += 250.0f;
    Vec f = {0.0f, 250.0f, 550.0f};
    PSMTXMultVec(m->mat, &f, front);
}
void hit_line(SceAtWork* w, const char* variant)
{
    cModel* who[2] = {(cModel*) pPL, (cModel*) first_ganado()};
    P(g_f, "%u HC %d %s", g_tick, w->no, variant);
    for (int k = 0; k < 2; k++) {
        if (!who[k]) {
            P(g_f, " -");
            continue;
        }
        Vec pos, front;
        points(who[k], &pos, &front);
        g_in = 1;
        const int r = sceAtHitCheck(w, who[k], &front, &pos);
        g_in = 0;
        P(g_f, " %d", r);
    }
    P(g_f, "\n");
}
// the planted item model: an object record with its own root part
cObj* planted(unsigned char* buf, unsigned char* parts)
{
    cObj* o = new (buf) cObj();
    __builtin_memset(parts, 0, 1024);
    o->pList = (cParts*) parts;
    o->scale.x = o->scale.y = o->scale.z = 1.0f;
    return o;
}

void exercise()
{
    cModel* leon = (cModel*) pPL;
    // records: area, hit tests, item sight, screen
    for (int i = 0; i < g_n; i++) {
        SceAtWork* w = g_rec[i];
        AreaData a;
        sceAtGetArea(&a, w);
        area_line("GA", w->no, a);
        hit_line(w, "own");
        cModel* par = w->pParent;
        const s16 parts = w->parentParts;
        const u8 flag = w->flag;
        static const s16 kParts[2] = {-1, 0};
        for (int pv = 0; pv < 2; pv++) {
            for (int rv = 0; rv < 2; rv++) {
                w->pParent = leon, w->parentParts = kParts[pv];
                w->flag = rv ? (flag | 8) : (flag & ~8);
                sceAtGetArea(&a, w);
                area_line(pv ? (rv ? "GAp0n" : "GAp0") : (rv ? "GApn" : "GAp"), w->no, a);
                hit_line(w, pv ? (rv ? "p0n" : "p0") : (rv ? "pn" : "p"));
            }
        }
        w->pParent = par, w->parentParts = parts, w->flag = flag;
        if (w->type == 3) {
            g_in = 1;
            const int r0 = SceAtItemHitCheck(w, 0);
            const int r1 = SceAtItemHitCheck(w, &leon->pos);
            const u8 f2 = w->item.flag2;
            w->item.flag2 = f2 | 0x10;
            const int r2 = SceAtItemHitCheck(w, 0);
            w->item.flag2 = (f2 & ~0x10) | 4;
            const int r3 = SceAtItemHitCheck(w, 0);
            w->item.flag2 = f2;
            g_in = 0;
            P(g_f, "%u IS %d %d %d %d %d\n", g_tick, w->no, r0, r1, r2, r3);
        }
        Vec c;
        AreaGetCenterPos(&c, &w->area);
        P(g_f, "%u SC r%d %d\n", g_tick, w->no, InScreenCheck(&c));
    }
    // a planted area round Leon (a cylinder 1,000 wide, from 2,000 under him), facing each way, narrow and wide, tested
    // at his front point and his own (the facing limit and the area test on every turn)
    for (int ang = -90; ang <= 90; ang += 15) {
        for (int k = 0; k < 4; k++) {
            SceAtWork f = {};
            Vec c = leon->pos;
            c.y -= 2000.0f;
            AreaDataInit(&f.area, &c, 2, 2000.0f, 3000.0f);
            f.flag = 1, f.type = 0, f.no = 0xFF;
            f.checkFlag = (u8) (2 | (k & 1));
            f.angle = (s8) ang, f.angleRange = (s8) ((k & 2) ? 45 : 10);
            char v[16];
            __builtin_snprintf(v, sizeof v, "f%d.%d", ang, k);
            hit_line(&f, v);
        }
    }
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext) {
        Vec p = e->pos;
        P(g_f, "%u SC e%x %d", g_tick, e->id, InScreenCheck(&p));
        p.y += 1500.0f;
        P(g_f, " %d\n", InScreenCheck(&p));
    }
    // hit bits
    SceAtClearHitFlg();
    SceAtSetHitFlg(g_tick & 0xFF);
    SceAtSetHitFlg((g_tick * 7 + 3) & 0xFF);
    P(g_f, "%u HB", g_tick);
    for (int wd = 0; wd < 8; wd++) {
        u32 v = 0;
        for (int b = 0; b < 32; b++) v = (v << 1) | (u32) SceAtHitCheck(wd * 32 + b);
        P(g_f, " %08x", v);
    }
    P(g_f, "\n");
    SceAtClearHitFlg();
    // ladder
    SceAtLadder l = {};
    l.pos = leon->pos;
    l.angle = (f32) (int) (g_tick % 63) * 0.1f - 3.1f;
    Vec lp;
    f32 la;
    sceAtGetLadderPos(&l, &lp, &la);
    P(g_f, "%u LP", g_tick);
    pt("P", lp);
    P(g_f, " A%.6f\n", la);
    // record numbers
    P(g_f, "%u MP", g_tick);
    for (int no = 0; no < 256; no++) {
        g_in = 1;
        cModel* m = SceAtItemModelPtr(no);
        g_in = 0;
        SceAtWork* w = SceAtPtr(no);
        if (w) P(g_f, " %d:%d", no, m == 0 ? 0 : (m == w->item.pModel ? 1 : 2));
    }
    P(g_f, "\n");
    // items: glows, models, parents (every 50th tick: the full table)
    if (g_tick % 50 != 0) return;
    const u16 room = pG->room_id;
    for (int i = 0; i < g_n; i++) {
        SceAtWork* w = g_rec[i];
        if (w->type != 3) continue;
        SceAtWork keep = *w;
        static const s16 kPar[6] = {-2, -1, 0, 2, 4, 8};   // -2: no parent
        for (int ty = 0; ty <= 10; ty++) {
            for (int pv = 0; pv < 6; pv++) {
                for (int mv = 0; mv < 2; mv++) {
                    if (pv > 0 && mv) continue;
                    *w = keep;
                    w->item.effType = (u8) ty;
                    w->pParent = pv == 0 ? 0 : leon;
                    w->parentParts = pv == 0 ? -1 : kPar[pv];
                    pG->room_id = kPar[pv] == 2 ? 0x30F : (kPar[pv] >= 4 ? 0x21B : room);
                    P(g_f, "%u EF %d %d %d %d\n", g_tick, w->no, ty, kPar[pv], mv);
                    g_in = 1;
                    sceAtItemEffSet(w, mv ? (cModel*) g_item : 0);
                    P(g_f, "%u EFn %d\n", g_tick, w->item.effNo);
                    sceAtItemEffDelete(&w->item);
                    g_in = 0;
                    P(g_f, "%u EFd %d\n", g_tick, w->item.effNo);
                }
            }
        }
        pG->room_id = room;
        for (int v = 0; v < 4; v++) {
            *w = keep;
            g_item = planted(g_item_buf, g_parts_buf[0]);
            w->item.rot.z = (v & 1) ? 1.0f : 0.0f;
            w->item.rot.x = 0.25f, w->item.rot.y = -1.5f;
            w->pParent = (v & 2) ? leon : 0;
            w->item.id = (v == 3) ? 0xAF : keep.item.id;
            const Vec ls = leon->scale;   // a parent scaled unevenly (put back below)
            if (v & 2) leon->scale.x = 1.25f, leon->scale.y = 0.8f, leon->scale.z = 2.0f;
            g_in = 1;
            const int r = SceAtSetItemModel(w, (cModel*) g_item);
            g_in = 0;
            leon->scale = ls;
            cParts* pp = g_item->pList;
            P(g_f, "%u SM %d %d %d %d %x %x", g_tick, w->no, v, r, g_item->ot_type, g_item->be_flag, (u32) (pp->pParent == leon));
            pt("P", g_item->pos);
            pt("P", g_item->ang);
            pt("P", g_item->pParts->scale);
            P(g_f, "\n");
        }
        *w = keep;
        w->pParent = 0;
        g_in = 1;
        sceAtCheckItemModelParent(w);
        g_in = 0;
        P(g_f, "%u CP %d %d\n", g_tick, w->no, w->pParent != 0);
        *w = keep;
    }
}
void shadows()
{
    cModel* leon = (cModel*) pPL;
    // the shadow area's handler
    for (int v = 0; v < 6; v++) {
        SceAtWork s = {};
        s.type = 9;
        s.shd.no = (u16) v;
        s.shd.on = (u8) (v % 3);
        s.shd.done = (u8) (v / 3);
        g_shadow->be_flag = (v & 1) ? 0x80 : 0;
        g_in = 1;
        const int r = sceAtFunc_shd_disp(&s, leon);
        g_in = 0;
        P(g_f, "%u SH %d %d %x %d\n", g_tick, v, r, g_shadow->be_flag & 0x80, s.shd.done);
    }
}
}   // namespace

// ---- the planted inputs and the logged entry points (wrapped in e2fodump and e2fnative only) ----
extern "C" {
int __real_EspPullCoreKind() __attribute__((weak));   // the reference defines none
int __wrap_EspPullCoreKind()
{
    if (!g_in) return &__real_EspPullCoreKind ? __real_EspPullCoreKind() : 0;
    return (int) (++g_pull % 31) + 1;
}
cObj* __real_ShdGetObjPtr(int no) __attribute__((weak));
cObj* __wrap_ShdGetObjPtr(int no)
{
    if (!g_in) return &__real_ShdGetObjPtr ? __real_ShdGetObjPtr(no) : 0;
    P(g_f, "%u SHo %d\n", g_tick, no);
    return g_shadow;
}
void __real_itemInfo(u16 id, ItemInfo* info) __attribute__((weak));
void __wrap_itemInfo(u16 id, ItemInfo* info)
{
    if (!g_in && &__real_itemInfo) return __real_itemInfo(id, info);
    __builtin_memset(info, 0, sizeof(*info));
    info->id = id;
    info->type = (u8) ((id * 5u + 3u) % 14u);   // every type 0 to 13 in turn
}
void __real_EffectEspDelete(int a, int b, u32 c, cModel* model);
void __wrap_EffectEspDelete(int a, int b, u32 c, cModel* model)
{
    if (!g_in) return __real_EffectEspDelete(a, b, c, model);
    P(g_f, "%u ED esp %d %d %x %d\n", g_tick, a, b, c, model != 0);
}
void __real_EffectEspgenDelete(int a, int b, int c);
void __wrap_EffectEspgenDelete(int a, int b, int c)
{
    if (!g_in) return __real_EffectEspgenDelete(a, b, c);
    P(g_f, "%u ED gen %d %d %d\n", g_tick, a, b, c);
}
void __real_EffectEfmDelete(int a, int b, int c);
void __wrap_EffectEfmDelete(int a, int b, int c)
{
    if (!g_in) return __real_EffectEfmDelete(a, b, c);
    P(g_f, "%u ED efm %d %d %d\n", g_tick, a, b, c);
}
// the at-list's guard (services/scene/at_list.cpp, e2fnative): another table cleared, logged
__attribute__((weak)) void e1_stub_hit(const char* name, int arg)
{
    if (g_f) P(g_f, "%u STUB %s %d\n", g_tick, name, arg);
}
// every effect start (svc/e2_dump.cpp's EstSet wrap calls this first)
void e2f_est(int a, int b, Vec* p, Vec* r, int c, int d, int e, int f, u32 g)
{
    if (!g_f || !g_in) return;
    const char* owner = a == 0 ? "0" : (a == (int) (intptr_t) pPL ? "leon" : (a == (int) (intptr_t) g_item ? "item" : "other"));
    P(g_f, "%u ES %s %d", g_tick, owner, b);
    pt("P", *p);
    P(g_f, " %d %d %x %d %x %d\n", r != 0, c, d, e, f, g);
}

extern "C" void e2f_ready()
{
    g_f = svc_out_open("e2f.txt", "w");
    if (!g_f) return;
    const char* c = svc_env("RE4_SVC_CONTROL");
    if (c && &sce_svc_control) {
        static const char* const kNames[] = {"", "atparent", "atfacing", "screenmid", "itemsight", "hitbit", "glowkind",
                                             "itemcol", "itemlink", "ladderofs", "itemrot", "shdbit", "glowstop", "modelptr",
                                             "parentscale"};
        for (int i = 1; i < 15; i++)
            if (!__builtin_strcmp(c, kNames[i])) sce_svc_control = i;
    }
    g_item = planted(g_item_buf, g_parts_buf[0]);
    g_shadow = planted(g_shd_buf, g_parts_buf[1]);
    // the game's screen (main_sub.cpp ScreenReSize(512, 448)): the reference sets none, so the screen tests had no width
    if (Screen.width == 0.0f) Screen.width = 512.0f, Screen.height = 448.0f;
    P(g_f, "# screen %d %d\n", (int) Screen.width, (int) Screen.height);
    void* aev = GetDataExt(pG->pRoom, "AEV", 0);
    void* ita = GetDataExt(pG->pRoom, "ITA", 0);
    g_in = 1;
    SceAtInit(aev, ita);
    g_in = 0;
    g_n = 0;
    P(g_f, "# IN aev %d ita %d\n", aev != 0, ita != 0);
    SceAtWork* w = sceAtSetOtStart();
    while ((w = sceAtGetOtAddr(w)) != 0 && g_n < 256) {
        g_rec[g_n++] = w;
        P(g_f, "IN %d %d %d %d\n", w->no, w->otNo, w->type, w->flag);
    }
    g_tick = 0;
    g_in = 1;
    P(g_f, "IC");
    for (int id = 0; id < 0x140; id++) P(g_f, " %d", sceAtCheckItemEffectCol((u16) id));
    P(g_f, "\n");
    g_in = 0;
}
extern "C" void e2f_tick(unsigned t)
{
    g_tick = t;
    if (!g_f) return;
    if (t >= 30 && t % 5 == 0) exercise(), shadows();
}
extern "C" void e2f_finish()
{
    if (!g_f) return;
    svc_out_close(g_f);
    g_f = 0;
}
}
