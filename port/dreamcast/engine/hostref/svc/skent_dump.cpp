// skent_dump.cpp (game side; lane eng-skel1): the skeleton service's bone entries (services/skeleton/skel.h: added
// rotation, local and world post-multiply, pose, world position and history, world matrix) against the original's
// effect, and the native chain object (services/cloth/chain.cpp) against game/obj1d.cpp. Linked into odump and native.
//
// RE4_SVC_EXERCISE=skent (both builds): from tick 30, at the end of every tick (before the palettes are taken), on the
// first live Ganado, the statements the ten em10 functions that wait for these entries make (em10NeckMove, WaistMove,
// BombNeckMove, BowgunMove, ClawMove, GatlingRollMove, MouthPartsReset; ChainSet, BeltSet, Em1fClothSet through the
// chain object and the cloth) on planted values:
//   odump   as the original makes them: getPartsPtr, then the record's addRot and flag 0x40000000, pos / ang / scale,
//           PSMTXConcat on l_mat / mat, reads of world / world_old / world_old2 / mat
//   native  through the entries (skel_addrot_set ...), which this file finds as weak symbols
// skent.txt logs every value read back (float bits); pal.bin / hist.bin (svc_dump.cpp) carry the effect on every bone.
// Parts numbers are taken modulo the model's part count, so every fixture's Ganado has them. History reads are logged
// from tick 33 (the entries' and getPartsPtr's history starts at the first ask).
//
// RE4_SVC_EXERCISE=skchain (both builds): at tick 40 the first live Ganado is made a chain Ganado for one call
// (type 10: em10ChainSet, archive models 0x225 / 0x226, hung from part 0x25 with its 4-link cloth) and at tick 41 a
// gatling one (type 2: em10BeltSet, 0x22D / 0x22E, part 0x23, 8 links), both on the original em10 code (each then hung
// again from its part number modulo the village Ganado's part count, which is below both); at tick 60
// the first chain is hung between two parts (setParent2, parts 3 and 4, two offsets) and at tick 80 the second is
// handed a new parent-free state. The objects then move every tick (ObjMgr), their bones in pal.bin; skent.txt logs
// each object's routine numbers, position and the cloth's link positions each tick.
#include "hostref.h"
#include "model.h"
#include "motion.h"
#include "em.h"
#include "em10.h"
#include "obj.h"
#include "global.h"
#include "pendulum.h"
#include "pl_cloth.h"
#include "player.h"

extern "C" {
void* svc_out_open(const char* name, const char* mode);
void svc_out_printf(void* f, const char* fmt, ...);
void svc_out_close(void* f);
const char* svc_env(const char* name);
// the entries (native build only)
int skel_addrot_get(cModel* m, int no, Vec* rot) __attribute__((weak));
int skel_addrot_set(cModel* m, int no, const Vec* rot, int on) __attribute__((weak));
int skel_local_post(cModel* m, int no, const f32 (*r)[4]) __attribute__((weak));
int skel_world_post(cModel* m, int no, const f32 (*r)[4]) __attribute__((weak));
int skel_pose_get(cModel* m, int no, Vec* pos, Vec* ang, Vec* scale) __attribute__((weak));
int skel_pose_set(cModel* m, int no, const Vec* pos, const Vec* ang, const Vec* scale) __attribute__((weak));
int skel_bone_world(cModel* m, int no, Vec* world, Vec* old, Vec* old2) __attribute__((weak));
int skel_bone_mat(cModel* m, int no, f32 (*out)[4]) __attribute__((weak));
// the collision service's room release (native build only)
void col_room_release(void) __attribute__((weak));
void col_bake_all(void) __attribute__((weak));
unsigned col_piece_count(void) __attribute__((weak));
unsigned svc_pool_room_used(void) __attribute__((weak));
unsigned col_baked_bytes(void) __attribute__((weak));   // lane eng-skel2: the pieces baked in the room archive
static unsigned room_bytes() { return svc_pool_room_used() + (col_baked_bytes ? col_baked_bytes() : 0); }
}
void em10ChainSet(cEm10* em);
void em10BeltSet(cEm10* em);
#define P svc_out_printf

namespace {
void* g_f;
int g_ex;   // 1 skent, 2 skchain
bool native() { return skel_addrot_set != 0; }
u32 bits(f32 f)
{
    u32 u;
    __builtin_memcpy(&u, &f, 4);
    return u;
}
void pv(const Vec& v) { P(g_f, " %08x,%08x,%08x", bits(v.x), bits(v.y), bits(v.z)); }
bool ganado(const cEm* e) { return e && (e->be_flag & 1) && e->id >= 0x10 && e->id <= 0x20; }
cParts* rec(cModel* m, int no) { return (cParts*) m->getPartsPtr(no); }

// ---- the operations: the original's statements (odump) or the entries (native) ----
void addrot_set(cModel* m, int no, const Vec& r, int on)
{
    if (native()) { skel_addrot_set(m, no, &r, on); return; }
    cParts* p = rec(m, no);
    if (on) p->motParts.flags |= 0x40000000; else p->motParts.flags &= ~0x40000000;
    p->addRot = r;
}
int addrot_get(cModel* m, int no, Vec* r)
{
    if (native()) return skel_addrot_get(m, no, r);
    cParts* p = rec(m, no);
    *r = p->addRot;
    return (p->motParts.flags & 0x40000000) ? 1 : 0;
}
void post(cModel* m, int no, int world, char axis, f32 a)
{
    Mtx r;
    PSMTXRotRad(r, axis, a);
    if (native()) { world ? skel_world_post(m, no, r) : skel_local_post(m, no, r); return; }
    cParts* p = rec(m, no);
    if (world) PSMTXConcat(p->mat, r, p->mat);
    else PSMTXConcat(p->l_mat, r, p->l_mat);
}
void pose_get(cModel* m, int no, Vec* pos, Vec* ang, Vec* scl)
{
    if (native()) { skel_pose_get(m, no, pos, ang, scl); return; }
    cParts* p = rec(m, no);
    if (pos) *pos = p->pos;
    if (ang) *ang = p->ang;
    if (scl) *scl = p->scale;
}
void pose_set(cModel* m, int no, const Vec* pos, const Vec* ang, const Vec* scl)
{
    if (native()) { skel_pose_set(m, no, pos, ang, scl); return; }
    cParts* p = rec(m, no);
    if (pos) p->pos = *pos;
    if (ang) p->ang = *ang;
    if (scl) p->scale = *scl;
}
void world_get(cModel* m, int no, Vec* w, Vec* o, Vec* o2)
{
    if (native()) { skel_bone_world(m, no, w, o, o2); return; }
    cParts* p = rec(m, no);
    *w = p->world;
    *o = p->world_old;
    *o2 = p->world_old2;
}
void mat_get(cModel* m, int no, Mtx out)
{
    if (native()) { skel_bone_mat(m, no, out); return; }
    __builtin_memcpy(out, rec(m, no)->mat, 48);
}

// one claw part towards its target, at most spd a tick (em10ClawMove's EM10_CLAW_PART_MOVE)
void claw_step(Vec* dst, const Vec& tgt, f32 spd)
{
    Vec d;
    PSVECSubtract(&tgt, dst, &d);
    if (d.x * d.x + d.y * d.y + d.z * d.z < spd * spd) {
        *dst = tgt;
    } else {
        PSVECNormalize(&d, &d);
        PSVECScale(&d, &d, spd);
        PSVECAdd(dst, &d, dst);
    }
}

void exercise(unsigned t, cEm10* e)
{
    const int n = e->nParts > 0 ? e->nParts : 1;
    const unsigned k = t - 30;
    auto no = [n](int x) { return x % n; };
    P(g_f, "%u X %d\n", t, n);
    // em10NeckMove: the neck's added rotation (part 3), flag on three ticks of four; the finger's local turn (part 13)
    const Vec neck = {0.01f * (f32) (k % 17) - 0.08f, 0.02f * (f32) (k % 11) - 0.1f, 0.0f};
    addrot_set(e, no(3), neck, k % 4 != 3);
    Vec r;
    const int fl = addrot_get(e, no(3), &r);
    P(g_f, "%u AR %d", t, fl), pv(r), P(g_f, "\n");
    if (k % 3 == 0) post(e, no(13), 0, 'z', 0.05f * (f32) (k % 9));
    // em10WaistMove: parts 1 and 2 the same yaw
    const Vec waist = {0.0f, 0.03f * (f32) (k % 7) - 0.09f, 0.0f};
    addrot_set(e, no(1), waist, 1);
    addrot_set(e, no(2), waist, 1);
    // even rounds: a world pass now (the behaviour's partsWorldCalc after its neck and waist moves), so the added
    // rotations and the local turn reach this tick's bones
    if (k % 2 == 0) e->partsWorldCalc();
    // em10BombNeckMove: the neck's pose angle, the scale shrinking (the yaw into two world matrices: below, last)
    Vec a, s, p;
    pose_get(e, no(0x24), 0, &a, 0);
    a.x = a.x * 0.9f + -0.06981317f;
    pose_set(e, no(0x24), 0, &a, 0);
    const f32 yaw = 0.5235988f * (0.5f + 0.02f * (f32) (k % 25));
    pose_get(e, no(0x1B), 0, 0, &s);
    s.x *= 0.9f;
    if (s.x < 0.1f) s.x = 0.1f;
    s.z = s.y = s.x;
    if (k % 2) pose_set(e, no(0x1B), 0, 0, &s);
    switch (k % 4) {
    case 0: {   // em10MouthPartsReset: the jaw parts' angles to 0
        const Vec z = {0.0f, 0.0f, 0.0f};
        for (int i = 0x1B; i <= 0x21; i++) pose_set(e, no(i), 0, &z, 0);
        break;
    }
    case 1:     // em10GatlingRollMove: the barrel's roll
        pose_get(e, no(0x22), 0, &a, 0);
        a.x += 0.34906584f;
        pose_set(e, no(0x22), 0, &a, 0);
        break;
    case 2: {   // em10ClawMove: both claws' position and scale towards their extended targets
        const Vec tp[2] = {{-359.22f, 0.0f, -106.02f}, {359.22f, 0.0f, -106.02f}}, ts = {1.0f, 1.0f, 1.0f};
        for (int c = 0; c < 2; c++) {
            pose_get(e, no(0x22 + c), &p, 0, &s);
            claw_step(&p, tp[c], 50.0f);
            claw_step(&s, ts, 0.1f);
            pose_set(e, no(0x22 + c), &p, 0, &s);
        }
        break;
    }
    case 3: {   // em10BowgunMove: the arrows shown by count (on the Ganado's weapon when it holds one)
        Em10Work* w = EM10_WK(e);
        cModel* wm = w->pWep ? (cModel*) w->pWep : (cModel*) e;
        const int wn = wm->nParts > 0 ? wm->nParts : 1;
        const unsigned arrows = (k / 4) % 4;
        for (int i = 1; i <= 4; i++) {
            const f32 v = (i == 4 || (i == 1 && arrows > 2) || (i == 2 && arrows > 1) || (i == 3 && arrows > 0)) ? 1.0f : 0.0f;
            const Vec sc = {v, v, v};
            pose_set(wm, i % wn, 0, 0, &sc);
            pose_get(wm, i % wn, 0, 0, &s);
            P(g_f, "%u BW %d", t, i), pv(s), P(g_f, "\n");
        }
        break;
    }
    }
    // what the pose now holds on the parts touched
    static const int touched[] = {0x24, 0x1B, 0x1C, 0x21, 0x22, 0x23};
    for (int x : touched) {
        Vec q, an, sc;
        pose_get(e, no(x), &q, &an, &sc);
        P(g_f, "%u PG %d", t, no(x)), pv(q), pv(an), pv(sc), P(g_f, "\n");
    }
    // odd rounds: the pose's matrices and a world pass now, so the pose writes reach this tick's bones
    if (k % 2 == 1) {
        e->partsMatCalc();
        e->partsWorldCalc();
    }
    // em10BombNeckMove's yaw into the two world matrices, after the last world pass (as the original, after its move)
    post(e, no(0x24), 1, 'y', yaw);
    post(e, no(0x1B), 1, 'y', yaw);
    // reads: the head's and the bomb neck's world position and history, the player's head matrix (em10NeckMove's)
    Vec w, o, o2;
    static const int heads[] = {4, 0x24};
    for (int x : heads) {
        world_get(e, no(x), &w, &o, &o2);
        P(g_f, "%u WD %d", t, no(x)), pv(w);
        if (t >= 33) pv(o), pv(o2);
        P(g_f, "\n");
    }
    if (pPL && pPL->pParts) {
        Mtx m;
        mat_get(pPL, 4, m);
        P(g_f, "%u PM", t);
        for (int i = 0; i < 12; i++) P(g_f, " %08x", bits((&m[0][0])[i]));
        P(g_f, "\n");
    }
}

// ---- the chain objects ----
cModel* g_chain[2];
void chains(unsigned t, cEm10* e)
{
    if (t == 40 || t == 41) {
        Em10Work* w = EM10_WK(e);
        const u8 keep_type = e->type;
        cModel* keep_chain = w->pChain;
        cModel* keep_belt = w->pGunBelt;
        e->type = t == 40 ? 10 : 2;
        if (t == 40) em10ChainSet(e);
        else em10BeltSet(e);
        g_chain[t - 40] = t == 40 ? w->pChain : w->pGunBelt;
        // the village Ganado has fewer parts than the chain and gatling models' parents (0x25, 0x23): hung again from
        // the same part number taken modulo its part count, as the set-up hangs it (flag 1)
        const int n = e->nParts > 0 ? e->nParts : 1;
        Vec z = {0.0f, 0.0f, 0.0f};
        if (g_chain[t - 40]) ((cObjChain*) g_chain[t - 40])->setParent(e, (t == 40 ? 0x25 : 0x23) % n, &z, 1);
        // each chain on its own copy of the description: both set-ups write the Ganado's one PenCloth (the native cloth
        // keeps one chain a PenCloth: lane eng-skel1's finding, a request to the cloth's owner)
        static PenCloth pc[2];
        pc[t - 40] = w->Cloth;
        if (g_chain[t - 40]) ((cObjChain*) g_chain[t - 40])->setChain(&pc[t - 40]);
        w->pChain = keep_chain;
        w->pGunBelt = keep_belt;
        e->type = keep_type;
        P(g_f, "%u CS %d %d\n", t, t - 40, g_chain[t - 40] != 0);
    }
    if (t == 60 && g_chain[0]) {
        Vec a = {-40.0f, 25.0f, 10.0f}, b = {30.0f, -60.0f, 5.0f};
        ((cObjChain*) g_chain[0])->setParent2(e, 3, &a, 4, &b, 0);
    }
    if (t == 80 && g_chain[1]) {
        Vec a = {0.0f, 0.0f, 0.0f};
        ((cObjChain*) g_chain[1])->setParent(e, 5, &a, 0);
    }
    for (int i = 0; i < 2; i++) {
        cObj* o = (cObj*) g_chain[i];
        if (!o) continue;
        if (!(o->be_flag & 1)) { P(g_f, "%u CG %d gone\n", t, i); g_chain[i] = 0; continue; }
        P(g_f, "%u CO %d r%u,%u,%u", t, i, o->r_no_0, o->r_no_1, o->r_no_2), pv(o->pos), pv(o->ang);
        for (int r = 0; r < 3; r++) P(g_f, " %08x,%08x,%08x,%08x", bits(o->mat[r][0]), bits(o->mat[r][1]), bits(o->mat[r][2]), bits(o->mat[r][3]));
        P(g_f, " be%x\n", o->be_flag);
    }
}
}   // namespace

// RE4_SVC_EXERCISE=colrel (native build; lane eng-skel1, eng-load1's request R2): at tick 100 the room is left and
// entered again as a room change does it: col_room_release, then col_bake_all. colrel.txt logs the pieces and the room
// carve's bytes before, after the release and after the bake: the release must leave 0 and 0, the bake the same as
// before; the queries go on against the reference (svc_compare.py).
void colrel(unsigned t)
{
    if (t != 100 || !col_room_release) return;
    P(g_f, "%u before pieces %u room %u\n", t, col_piece_count(), room_bytes());
    col_room_release();
    P(g_f, "%u released pieces %u room %u\n", t, col_piece_count(), room_bytes());
    col_bake_all();
    P(g_f, "%u rebaked pieces %u room %u\n", t, col_piece_count(), room_bytes());
}
extern "C" void skchain_kind_register(void);   // skchain_kind.cpp
extern "C" void skent_ready()
{
    skchain_kind_register();
    const char* e = svc_env("RE4_SVC_EXERCISE");
    g_ex = !e ? 0 : !__builtin_strcmp(e, "skent") ? 1 : !__builtin_strcmp(e, "skchain") ? 2 : !__builtin_strcmp(e, "colrel") ? 3 : 0;
    if (g_ex) g_f = svc_out_open(g_ex == 3 ? "colrel.txt" : "skent.txt", "w");
}
extern "C" void skent_tick(unsigned t, int begin)
{
    if (!g_f || begin || t < 30) return;
    if (g_ex == 3) { colrel(t); return; }
    cEm10* e = 0;
    for (cEm* x = EmMgr.pAlive; x; x = (cEm*) x->pNext)
        if (ganado(x)) { e = (cEm10*) x; break; }
    if (!e) { P(g_f, "%u none\n", t); return; }
    if (g_ex == 1) exercise(t, e);
    else chains(t, e);
}
extern "C" void skent_finish()
{
    if (g_f) svc_out_close(g_f);
    g_f = 0;
}
