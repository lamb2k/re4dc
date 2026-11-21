// sce_at_svc.cpp (lane eng-e2f): the scene attachments' services, the engine's.
//
// The scene attachments (SceAtWork records: doors, item spots, ladders, message and shadow areas, the room's trigger
// areas; include/sce_at.h) are decided by sce_at's hosted code: which record fires, what it does, when an item is
// taken. These are the questions it asks and the services it calls under those decisions (the link check's sce_at
// exceptions, game/allowed_original.txt); sce_at's own bodies are weak in the image (game/fight.mk) and in the PC
// check's native build (hostref svc/svc.mk), so these are reached by every caller.
//
//   room set-up   SceAtInit: the room's attachment data (AEV records, ITA item records) checked and linked into the
//                 at-list (services/scene/at_list.cpp), the system record cleared; loading work, at room entry only
//   geometry      sceAtGetArea (a record's area carried by its parent's frame), sceAtGetLadderPos (where the player
//                 stands to use a ladder)
//   questions     sceAtHitCheck (is a character in a record's area: the area service's tests, the facing limit, an
//                 item's sight lines), SceAtItemHitCheck (is an item in sight of the player: three line tests on the
//                 effect collision), InScreenCheck (does a point project into the screen's middle), SceAtHitCheck (was
//                 a record hit this tick: its bit in the system record)
//   item models   SceAtSetItemModel, sceAtSetItemModelParent, sceAtCheckItemModelParent, SceAtItemModelPtr: an item's
//                 model placed on its spot and carried by the spot's parent (the model service's parent link)
//   presentation  sceAtItemEffSet / sceAtItemEffDelete (the item's glow: which effect kinds, started and stopped on the
//                 effect service's entry points), sceAtCheckItemEffectCol (the glow colour of an item kind), the shadow
//                 area's handler (a shadow object's display bit)
//   logged stubs  itemZoom (the pick-up zoom read the item's model from the disc inside play: refused here, the
//                 engine reads nothing inside a picture; counted) and releaseModel (undoes only what itemZoom made: with
//                 no zoom model it has nothing to undo; counted)
//
// sce_at keeps its state in file statics; services/scene/sce_at_weak.h, force-included into the hosted unit, makes the
// system record (SceAtSys), its pointer (pS) and the shadow handler weak globals: SceAtInit points pS at the record as
// the original does, and the shadow handler here takes the handler table's entry.
//
// Controls (sce_svc_control, set only by the PC check, hostref svc/e2f_dump.cpp RE4_SVC_CONTROL; each must make the
// boundary log differ): 1 "atparent" the parent's rotation ignored, 2 "atfacing" the record's facing turned by
// 0.5 radian, 3 "screenmid" the screen's middle narrowed to 35..65 %, 4 "itemsight" the second sight line skipped, 5 "hitbit" a
// record's hit bit read from the low end, 6 "glowkind" ammo and treasure glows swapped, 7 "itemcol" ammo's colour 4,
// 8 "itemlink" ITA records not renumbered from 0x80, 9 "ladderofs" the ladder's stand 310 in front, 10 "itemrot" the
// item model's rotation not applied, 11 "shdbit" the shadow bit inverted, 12 "glowstop" the glow's third stop
// skipped, 13 "modelptr" the record itself answered for its model, 14 "parentscale" the parent's scale kept.
#define fabsf scesvc_game_fabsf
#include "types.h"
#include "atari.h"
#include "global.h"
#include "main_sub.h"
#include "sce_at.h"
#include "area.h"
#include "geometry.h"
#include "model.h"
#include "obj.h"
#include "em.h"
#include "player.h"
#include "item.h"
#include "esp.h"
#include "est.h"
#include "shadow.h"
#include "libgpu.h"
#include "math_sub.h"
#undef fabsf
#include "../camera/cam_math.h"

int GetScreenPos(Vec* pos, Vec* scr);

extern "C" {
struct SceSvcCounters {
    u32 inits, bad_data, records, areas, hit_tests, eye_tests, item_sights, screen_tests, hit_bits, glows, glow_starts,
        glow_stops, models, model_misses, zoom_refused, release_none, shadows;
};
SceSvcCounters scesvc_cnt;
int sce_svc_control;
int sceAtFunc_shd_disp(SceAtWork* w, cModel* m);
}

namespace {
using namespace camsvc;

// The system record (sce_at.cpp SceAtSysWork, 0x124 bytes): the fields the engine's services touch, at the record's
// offsets. The storage is sce_at's own (SceAtSys); pS is the pointer every decision reads it through.
struct SceAtSysView {
    void* atData;        // 0x00  the room's AEV file
    u32 atWork;          // 0x04  its records
    void* itemData;      // 0x08  the room's ITA file
    u32 itemWork;        // 0x0C  its records
    u32 hitFlg[8];       // 0x10  records hit this tick, bit 31 - (no & 31) of word no >> 5
    u32 execFlg[8];      // 0x30
    u32 ot[16];          // 0x50  the at-list's buckets
    u32 stop, x94;       // 0x90
    u8 hideActive;       // 0x98
    u8 pad_99[3];
    struct {
        u32 key;
        u8 saveNo, pad[3];
    } reserve[16];       // 0x9C
    u8 x11C, x11D, pad_11E[2];
    void* camAt;         // 0x120
};
static_assert(sizeof(SceAtSysView) == 0x124, "SceAtSysWork is 0x124 bytes");
static_assert(__builtin_offsetof(SceAtSysView, ot) == 0x50 && __builtin_offsetof(SceAtSysView, reserve) == 0x9C &&
              __builtin_offsetof(SceAtSysView, camAt) == 0x120, "SceAtSysWork layout");
#define SCESVC_STR2(x) #x
#define SCESVC_STR(x) SCESVC_STR2(x)
#define SCESVC_SYM(name) SCESVC_STR(__USER_LABEL_PREFIX__) #name
extern "C" SceAtSysView* sce_sys_ptr asm(SCESVC_SYM(_ZL2pS));
extern "C" SceAtSysView sce_sys asm(SCESVC_SYM(_ZL8SceAtSys));

// the attachment files' head (AEV version 0x104, ITA version 0x105), records from +0x10
struct AtFileHead {
    char magic[4];
    u16 version, num;
    u8 pad[8];
};
bool file_ok(const void* p, const char* magic, u16 version)
{
    const AtFileHead* h = static_cast<const AtFileHead*>(p);
    if (h->magic[0] != magic[0] || h->magic[1] != magic[1] || h->magic[2] != magic[2] || h->magic[3] != 0) {
        scesvc_cnt.bad_data++;
        return false;
    }
    if (h->version != version) {
        scesvc_cnt.bad_data++;
        return false;
    }
    return true;
}
SceAtWork* records(void* file) { return reinterpret_cast<SceAtWork*>(static_cast<u8*>(file) + 0x10); }
// a file's records into their buckets, the last first, so each bucket holds them in file order from its head
void link_file(void* file, u8 renumber)
{
    const AtFileHead* h = static_cast<const AtFileHead*>(file);
    SceAtWork* r = records(file);
    for (int i = h->num - 1; i >= 0; i--) {
        r[i].no += renumber;
        AddPrim(&sce_sys.ot[r[i].otNo], reinterpret_cast<u32*>(&r[i]));
        scesvc_cnt.records++;
    }
}

constexpr f32 kDegToRad = 3.14159265358979323846f / 180.0f;

// a record's parent frame: the parent's (or its part's) matrix; with flag bit 3 only its position (rotation ignored)
Frame parent_frame(const SceAtWork* w)
{
    cModel* p = w->pParent;
    Frame f = frame_of(w->parentParts >= 0 ? p->getPartsPtr(w->parentParts)->mat : p->mat);
    if ((w->flag & 8) || sce_svc_control == 1) {
        f.left = shz_vec3_init(1.0f, 0.0f, 0.0f);
        f.up = shz_vec3_init(0.0f, 1.0f, 0.0f);
        f.forward = shz_vec3_init(0.0f, 0.0f, 1.0f);
    }
    return f;
}
// a record's facing (its angle, turned by its parent's yaw unless the rotation is ignored)
f32 record_facing(const SceAtWork* w)
{
    f32 a = (f32) (w->angle * 2) * kDegToRad;
    if (w->pParent != 0 && !(w->flag & 8)) {
        const f32 yaw = w->parentParts >= 0 ? w->pParent->getPartsPtr(w->parentParts)->ang.y : w->pParent->ang.y;
        a = LIMIT_ANGLE(a + yaw);
    }
    return a;
}
// is the line from a to b clear of the effect collision
bool clear_line(v3 a, v3 b)
{
    Vec from, to;
    put(&from, a);
    put(&to, b);
    return EatMgr.hitCheck(&from, &to, 0, 0, 0, 0) == 0;
}
}   // namespace

extern "C" {

// ---- room set-up ----
void SceAtInit(void* atData, void* itemData)
{
    scesvc_cnt.inits++;
    SceAtSysView& s = sce_sys;
    sce_sys_ptr = &s;
    s.atData = 0, s.atWork = 0, s.camAt = 0, s.hideActive = 0;
    ClearOTagR(s.ot, 16);
    // (the item models' deferred frees: only releaseModel queues them, and the engine's queues none)
    for (int i = 0; i < 16; i++) s.reserve[i].key = 0, s.reserve[i].saveNo = 0;
    SceAtWorkLoopInit();
    s.x11C = 0, s.x11D = 0;
    if (atData != 0 && file_ok(atData, "AEV", 0x104)) {
        s.atData = atData;
        s.atWork = (u32) (uintptr_t) records(atData);
        link_file(atData, 0);
    }
    if (itemData != 0 && file_ok(itemData, "ITA", 0x105)) {
        s.itemData = itemData;
        s.itemWork = (u32) (uintptr_t) records(itemData);
        link_file(itemData, sce_svc_control == 8 ? 0 : 0x80);
    }
}

// was record `no` hit this tick
int SceAtHitCheck(u32 no)
{
    scesvc_cnt.hit_bits++;
    const u32 bit = sce_svc_control == 5 ? (no & 31) : 31 - (no & 31);
    return (sce_sys_ptr->hitFlg[no >> 5] >> bit) & 1;
}

// ---- geometry ----
void sceAtGetArea(AreaData* out, SceAtWork* w)
{
    scesvc_cnt.areas++;
    *out = w->area;
    if (w->pParent == 0) return;
    const Frame f = parent_frame(w);
    switch (out->type) {
    case 1: {   // a quad prism: its four ground corners at floor height, the floor the first corner's
        AreaXZ4& q = out->u.xz4;
        const f32 floor = q.floor;
        for (int i = 0; i < 4; i++) {
            const v3 c = frame_point(f, shz_vec3_init(q.p[i].x, floor, q.p[i].z));
            q.p[i].x = c.x, q.p[i].z = c.z;
            if (i == 0) q.floor = c.y;
        }
        break;
    }
    case 2:
    case 3: {   // a cylinder or an eye trigger: its point
        const v3 c = frame_point(f, shz_vec3_init(out->u.cyl.x, out->u.cyl.floor, out->u.cyl.z));
        out->u.cyl.x = c.x, out->u.cyl.floor = c.y, out->u.cyl.z = c.z;
        break;
    }
    }
}

void sceAtGetLadderPos(SceAtLadder* l, Vec* pos, f32* ang)
{
    Mtx m;
    Vec turn = {0.0f, l->angle, 0.0f};
    low_RotMatrix(m, &turn);
    Frame f = frame_of(m);
    f.pos = V(l->pos);
    put(pos, frame_point(f, shz_vec3_init(0.0f, 0.0f, sce_svc_control == 9 ? 310.0f : 300.0f)));
    *ang = LIMIT_ANGLE(l->angle + 3.14159265358979323846f);
}

// ---- questions ----
int InScreenCheck(Vec* pos)
{
    scesvc_cnt.screen_tests++;
    Vec p = *pos, scr;
    GetScreenPos(&p, &scr);
    const f32 lo = sce_svc_control == 3 ? 0.35f : 0.25f, hi = sce_svc_control == 3 ? 0.65f : 0.75f;
    return Screen.width * lo < scr.x && Screen.width * hi > scr.x && Screen.height * 0.1f < scr.y &&
           Screen.height * 0.9f > scr.y;
}

int SceAtItemHitCheck(SceAtWork* w, Vec* pos)
{
    scesvc_cnt.item_sights++;
    const SceAtItem& it = w->item;
    if (it.flag2 & 0x10) return 0;   // still hanging
    if (it.flag2 & 4) return 1;      // shown for the pick-up
    v3 at = pos != 0 ? V(pos) : V(it.pos);
    if (pos == 0 && w->pParent != 0) at = frame_point(parent_frame(w), at);
    // in sight when one of three lines to the player is clear: level at 200 and at 600 above the item, and from 200
    // above the item to 1,800 above the player
    const v3 pl = V(pPL->pos);
    if (clear_line(shz_vec3_init(at.x, at.y + 200.0f, at.z), shz_vec3_init(pl.x, at.y + 200.0f, pl.z))) return 1;
    if (sce_svc_control != 4 &&
        clear_line(shz_vec3_init(at.x, at.y + 600.0f, at.z), shz_vec3_init(pl.x, at.y + 600.0f, pl.z)))
        return 1;
    return clear_line(shz_vec3_init(at.x, at.y + 200.0f, at.z), shz_vec3_init(pl.x, pl.y + 1800.0f, pl.z));
}

int sceAtHitCheck(SceAtWork* w, cModel* m, Vec* front, Vec* pos)
{
    scesvc_cnt.hit_tests++;
    AreaData a;
    sceAtGetArea(&a, w);
    const f32 facing = record_facing(w);
    if (a.type == 3) {   // an eye trigger: seen through its cone, and its point in the screen's middle
        scesvc_cnt.eye_tests++;
        GeoCone cone[2];
        Vec c = {a.u.eye.xz, a.u.eye.floor, a.u.eye.z};
        return AreaViewCheck(&a, cone) == 1 && InScreenCheck(&c) == 1;
    }
    Vec* p = (w->checkFlag & 1) ? front : pos;
    if (p == 0 || AreaHitCheck(&a, p) != 1) return 0;
    if (m != 0 && (w->checkFlag & 2)) {   // the facing limit: the character within angleRange of the record's facing
        const f32 d = LIMIT_ANGLE(facing - m->ang.y + (sce_svc_control == 2 ? 0.5f : 0.0f));
        const int r = w->angleRange;
        if (d < (f32) (-r * 2) * kDegToRad || d > (f32) (r * 2) * kDegToRad) return 0;
    }
    if (w->type == 3 && SceAtItemHitCheck(w, 0) == 0) return 0;
    return 1;
}

// ---- item models ----
void sceAtSetItemModelParent(SceAtWork* w)
{
    if (w->pParent == 0) return;
    const Vec& s = w->pParent->scale;   // the parent's scale undone, so the item keeps its size
    Vec inv = {s.x != 0.0f ? 1.0f / s.x : 0.0f, s.y != 0.0f ? 1.0f / s.y : 0.0f, s.z != 0.0f ? 1.0f / s.z : 0.0f};
    if (sce_svc_control == 14) inv = s;
    cModel* im = w->item.pModel;
    im->be_flag &= ~0x4000;
    im->pParts->scale = inv;
    im->setParent(w->pParent, &im->pos, &im->ang);
}

}   // extern "C" (this form of SceAtSetItemModel has C++ linkage; the area-number form, sce_at's, calls it)
int SceAtSetItemModel(SceAtWork* w, cModel* m)
{
    if (w == 0 || m == 0) {
        scesvc_cnt.model_misses++;
        return 0;
    }
    scesvc_cnt.models++;
    SceAtItem& it = w->item;
    it.pModel = m;
    if (it.id == 0xAF) m->ot_type = 1;
    m->pos = it.pos;
    if (it.rot.z > 0.0f && sce_svc_control != 10) m->ang.x = it.rot.x, m->ang.y = it.rot.y, m->ang.z = 0.0f;
    m->setNoSuspend(0);
    sceAtSetItemModelParent(w);
    return 1;
}
extern "C" {

cModel* SceAtItemModelPtr(int no)
{
    SceAtWork* w = SceAtPtr(no);
    if (w == 0 || w->type != 3) {
        scesvc_cnt.model_misses++;
        return 0;
    }
    return sce_svc_control == 13 ? (cModel*) w : w->item.pModel;
}

// an item without a parent that lies in a parent-giving record's area (type 0x14) takes that record's parent
void sceAtCheckItemModelParent(SceAtWork* w)
{
    if (w->pParent != 0) return;
    Vec* at = &w->item.pos;
    SceAtWork* p = sceAtSetOtStart();
    while ((p = sceAtGetOtAddr(p)) != 0) {
        if (!(p->flag & 1) || p->type != 0x14 || p->pParent == 0) continue;
        if (sceAtHitCheck(p, 0, at, at) == 1) SceAtSetParent(w, p->pParent, 0);
    }
}

// ---- presentation ----
}   // extern "C"
namespace {
// an item's glow: the effect kinds started for its effType (1 to 9), alone or on a model. kind2 0: one start.
// below: the first start 800 under the item (a falling item's light).
struct Glow {
    u8 kind1, kind2, below;
};
const Glow kGlow[10] = {
    {0, 0, 0}, {0x21, 0, 0}, {0x33, 0x21, 0}, {0x2C, 0, 0}, {0x31, 0, 0},
    {0x2F, 0, 0}, {0, 0, 0}, {0x46, 0x21, 0}, {0x33, 0x21, 1}, {0x4D, 0, 0},
};
// on a parent: by effType and the parent class (0 the model, 1 part 2 in room 0x30F, 2 part 4 / 3 part 8 in 0x21B);
// 0 = no parented kind (types 1, 7, 8, 9 take the plain 0x2D only; type 2 adds it after its own)
const u8 kGlowParent[10][4] = {
    {0, 0, 0, 0}, {0, 0, 0, 0}, {0x4B, 0x1F, 0, 0}, {0x48, 0x1C, 6, 0xC}, {0x4A, 0x1E, 0xA, 0x10},
    {0x49, 0x1D, 8, 0xE}, {0, 0, 0, 0}, {0, 0, 0, 0}, {0, 0, 0, 0}, {0, 0, 0, 0},
};
void glow(int owner, Vec* p, int on_parts, int kind, u8 no)
{
    scesvc_cnt.glow_starts++;
    EstSet(owner, -1, p, 0, on_parts, kind, 0xC00, no, 0, 0);
}
}   // namespace
extern "C" {

void sceAtItemEffSet(SceAtWork* w, cModel* m)
{
    SceAtItem& it = w->item;
    if ((s8) pG->shooting_mode != 0) return;
    it.effNo = 0;
    if (it.effType == 0) return;
    it.effNo = EspPullCoreKind();
    if (it.effNo == 0) return;
    scesvc_cnt.glows++;
    const int type = it.effType;
    cModel* parent = w->pParent;
    if (parent == 0) {
        if (type > 9) return;
        Glow g = kGlow[type];
        if (sce_svc_control == 6 && (type == 4 || type == 5)) g = kGlow[type == 4 ? 5 : 4];
        Vec p = {it.pos.x + it.ofs.x, it.pos.y + it.ofs.y, it.pos.z + it.ofs.z};
        if (m != 0) {
            if (type == 1) {   // the plain glow follows the model
                Vec o = it.ofs;
                glow((int) m, &o, 0, 0x2D, it.effNo);
                return;
            }
            p = {m->pos.x + it.ofs.x, m->pos.y + it.ofs.y, m->pos.z + it.ofs.z};
        }
        if (g.kind1 == 0) return;
        Vec q = p;
        if (g.below) q.y -= 800.0f;
        glow(0, &q, 0, g.kind1, it.effNo);
        if (g.kind2) glow(0, &p, 0, g.kind2, it.effNo);
        return;
    }
    int cls;
    switch (w->parentParts) {
    case -1:
    case 0: cls = 0; break;
    case 2: cls = 1; if (pG->room_id != 0x30F) return; break;
    case 4: cls = 2; if (pG->room_id != 0x21B) return; break;
    case 8: cls = 3; if (pG->room_id != 0x21B) return; break;
    default: return;
    }
    if (type > 9 || type == 6) return;
    Vec p = {it.pos.x + it.ofs.x, it.pos.y + it.ofs.y, it.pos.z + it.ofs.z};
    int kind = kGlowParent[type][cls];
    if (sce_svc_control == 6 && (type == 4 || type == 5)) kind = kGlowParent[type == 4 ? 5 : 4][cls];
    if (type == 2 && cls >= 2) return;   // the recovery glow has no form on those parts
    if (kind != 0) glow((int) parent, &p, cls != 0, kind, it.effNo);
    if (type == 1 || type == 2 || type >= 7) glow((int) parent, &p, 0, 0x2D, it.effNo);
}

void sceAtItemEffDelete(SceAtItem* it)
{
    if (it->effType == 0 || it->effNo == 0) return;
    scesvc_cnt.glow_stops++;
    EffectEspDelete(0, it->effNo, 0, 0);
    EffectEspgenDelete(0, it->effNo, 0);
    if (sce_svc_control != 12) EffectEfmDelete(0, it->effNo, 0);
    it->effNo = 0;
}

// the glow colour of an item kind: 8 for item 0x8C; by the item's type: weapons and ammo 5, treasure 4, recovery,
// keys and money 2, the rest 3
int sceAtCheckItemEffectCol(u16 id)
{
    if (id == 0x8C) return 8;
    ItemInfo info;
    itemInfo(id, &info);
    static const u8 kCol[8] = {2, 5, 5, 5, 5, 2, 4, 2};
    if (info.type < 8) return (sce_svc_control == 7 && info.type == 1) ? 4 : kCol[info.type];
    return 3;
}

// the shadow area's handler: shadow object `no` shown or hidden once while a character is inside
int sceAtFunc_shd_disp(SceAtWork* w, cModel* m)
{
    (void) m;
    SceAtShdDisp& s = w->shd;
    if (s.done == 1) return 0;
    scesvc_cnt.shadows++;
    cObj* o = ShdGetObjPtr(s.no);
    if ((s.on == 1) != (sce_svc_control == 11)) o->be_flag |= 0x80;
    else o->be_flag &= ~0x80;
    s.done = 1;
    return 0;
}

// ---- logged stubs ----
// the pick-up zoom's model: refused (no disc read inside play); the original's load-failure answer
int itemZoom(SceAtWork* w)
{
    (void) w;
    scesvc_cnt.zoom_refused++;
    return 0;
}
// undoes itemZoom's model: the engine's itemZoom makes none (item.flag bits 1 and 3 are only its own)
void releaseModel(SceAtWork* w, int keep)
{
    (void) w;
    (void) keep;
    scesvc_cnt.release_none++;
}

}   // extern "C"
