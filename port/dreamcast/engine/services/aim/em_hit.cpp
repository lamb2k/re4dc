// em_hit.cpp (lane eng-e2a, 2026-11-21): the enemy hit geometry, native. The entry points em_sub.cpp's service functions
// had: the line, sphere, capsule, box and quad tests against the actors' hit boxes, the attack checks built on them, the
// damage position, the blast list, the rack and water tests, the caught actor's follow, and the blood effects placed at
// a hit. The behaviour (em10, the player, the partner, the weapons) calls them by their original names and keeps every
// decision that is its own: whether to attack, the damage amounts, the reactions (LifeDownSet2, PlSetDamage, cDmgInfo::set
// stay hosted and are called from here). docs/engine/lanes/eng-e2a.md lists, per function, how it differs from the
// original and the decision statements a composition here re-expresses.
//
// Engine form: a hit box is read once into a world-space volume (the part's frame from cam_math.h, the capsule's axis
// ends and radius, or the oriented box's centre and axes); a line meets a capsule at the root of one quadratic per piece
// (the side in the plane across the axis, the two end spheres), a box in its own coordinates by slabs (the axes'
// adjugate), a quad by its plane and four edge signs. The sphere touches of the melee checks are the actor-volume service's
// (services/volumes: AtSphereCapsuleCk, At_box_sphere_ck), which already answer that question for the bodies. No random
// number is drawn for behaviour; the blood scatter (EmDmBloodSet2 with `rnd`, never asked by the fight) draws from the
// engine's presentation generator.
#define fabsf emhit_game_fabsf
#include "types.h"
#include "global.h"
#include "model.h"
#include "em.h"
#include "player.h"
#include "pl_npc.h"
#include "emhit.h"
#include "em_sub.h"
#include "emrack.h"
#include "atari.h"
#include "at_sub.h"
#include "math_sub.h"
#include "esp.h"
#include "pad.h"
#undef fabsf
#include "hit_shape.h"

extern "C" {
int MotionMove(cModel* m, int a);
unsigned char eng_pres_u8();
// counters (the image's report, the PC check's e2.txt)
struct EmHitCounters {
    u32 line_tests, line_capsules, line_cubes, cube_mirrored, quads, line_hits;
    u32 sphere_tests, sphere_boxes, sphere_hits, dm_pos, atk_sphere, atk_line, atk_hits;
    u32 racks, water, catch_moves, bloods, blood_scatter, bomb_lists, bomb_player, debug_draws;
};
EmHitCounters emhit_cnt;
// Controls (set only by the PC check, hostref svc/e2_dump.cpp RE4_SVC_CONTROL): 1 "hitwide": every capsule radius and box
// extent of the line tests 10% larger; 2 "dmposmid": the damage position at the box's middle, not the near side; 3
// "sphereshort": the melee sphere 20% smaller; 4 "hitnudge": every line-test hit point 0.03 unit further along its line
// (it must fail both the position bound and the double-precision answer rule of e2_compare.py). Each must make the PC
// comparison fail.
int emhit_control;
}

namespace {
using namespace camsvc;
using hitsvc::LineFrame;
using hitsvc::sphere_in;
using hitsvc::capsule_in;
using hitsvc::cube_in;

// ---- a hit box in world space ----
struct HitBox {
    Frame f;      // the part's frame (axes with their scale, position)
    v3 base;      // the box's anchor: the capsule's first end, the cube's centre
    v3 tip;       // the capsule's other end (base + height along the box's axis, through the frame)
    f32 radius;   // the capsule's radius: the width through the frame's z axis
    int axis;     // the axis the height runs along: 0 x (flag 2), 2 z (flag 4), else 1 y
};
cModel* part_of(cEm* em, const YARARE_INFO* p) { return p->partsNo ? em->getPartsPtr(p->partsNo - 1) : (cModel*) em; }
int axis_of(const YARARE_INFO* p) { return (p->flags & 6) ? ((p->flags & 2) ? 0 : 2) : 1; }
v3 along(int axis, f32 h) { return shz_vec3_init(axis == 0 ? h : 0.0f, axis == 1 ? h : 0.0f, axis == 2 ? h : 0.0f); }
HitBox hit_box(cEm* em, const YARARE_INFO* p)
{
    HitBox b;
    b.f = frame_of(part_of(em, p)->mat);
    b.axis = axis_of(p);
    const v3 o = V(p->ofs);
    b.base = frame_point(b.f, o);
    b.tip = frame_point(b.f, vadd(o, along(b.axis, p->height)));
    b.radius = p->width * vlen(b.f.forward);
    return b;
}
v3 mid(const HitBox& b) { return vscale(vadd(b.base, b.tip), 0.5f); }
bool dying(cEm* em) { return em->dmg.m_Flag || em->dmg.m_Timer; }
bool debug_boxes() { return pG->Debug_flg[0] & 0x1000; }

// The shapes (a segment against a sphere, a capsule by the game's rule, an oriented box): hit_shape.h (lane eng-e2g
// moved them there unchanged so the shot's target list in aim.cpp answers by the same rule).

v3 at(v3 a, v3 b, f32 t)
{
    if (t == 0.0f) return a;
    const v3 d = vsub(b, a);
    if (emhit_control == 4) return vadd(a, vscale(d, t + 0.03f / vlen(d)));   // control hitnudge: 0.03 unit further on
    return vadd(a, vscale(d, t));
}

// Where the segment enters one hit box: true with the point in *hit.
bool box_line(cEm* em, const YARARE_INFO* p, v3 a, v3 b, v3* hit)
{
    emhit_cnt.line_tests++;
    const f32 g = emhit_control == 1 ? 1.1f : 1.0f;   // control hitwide only
    const HitBox hb = hit_box(em, p);
    f32 t;
    if (p->flags & 8) {
        emhit_cnt.line_cubes++;
        t = cube_in(a, b, hb.f, V(p->ofs), p->width * g, p->height * g, p->depth * g, &emhit_cnt.cube_mirrored);
    } else {
        emhit_cnt.line_capsules++;
        t = capsule_in(a, b, hb.base, hb.tip, hb.radius * g);
    }
    if (t < 0.0f) return false;
    *hit = at(a, b, t);
    return true;
}

// The eight corners of a cube box about its part's origin, in the order the volume service's box test reads them
// (bottom face -z/+z rows, then the top face): the melee sphere test's box.
void cube_corners(cEm* em, const YARARE_INFO* p, Vec out[8])
{
    const Frame f = frame_of(part_of(em, p)->mat);
    for (int i = 0; i < 8; i++) {
        const v3 l = shz_vec3_init(i & 1 ? p->width : -p->width, i & 4 ? p->height : 0.0f, i & 2 ? p->depth : -p->depth);
        put(&out[i], frame_point(f, l));
    }
}

// The damage reaction class of a hit on the player at `hit` coming along `d`: front or back by the player's facing,
// then low (under 800 above his feet), middle (under 1300) or high; 1-based as the behaviour reads it.
int reaction_class(Vec* hit, v3 d)
{
    Vec fwd = {0.0f, 0.0f, 1.0f};
    RotVector(&fwd, &pPL->ang, &fwd);
    int cls = vdot(V(fwd), d) >= 0.0f ? 1 : 0;
    const f32 dy = hit->y - pPL->pos.y;
    cls += dy < 800.0f ? 4 : dy < 1300.0f ? 2 : 0;
    return cls + 1;
}

}   // namespace

// ==== the shapes (em_sub.cpp emLinePolyCrossCk, emLineCubeCrossCk, emLineCapsuleCrossCk) ====

// A segment through a quad from its front: the quad's plane by the normal (p2 - p1) x (p0 - p1); a must lie strictly in
// front and b strictly behind; the crossing is on the inner side of each edge (p[k + 1] -> p[k]) or on it.
extern "C" int emLinePolyCrossCk(Vec* pPos, Vec* pPos2, Vec* poly, Vec* hit)
{
    emhit_cnt.quads++;
    const v3 a = V(pPos), b = V(pPos2);
    v3 q[4];
    for (int i = 0; i < 4; i++) q[i] = V(poly[i]);
    const v3 n = vcross(vsub(q[2], q[1]), vsub(q[0], q[1]));
    if (vzero(n)) return 0;
    const f32 da = vdot(n, vsub(a, q[0])), db = vdot(n, vsub(b, q[0]));
    if (!(da > 0.0f) || !(db < 0.0f)) return 0;
    const v3 x = at(a, b, da / (da - db));
    for (int k = 0; k < 4; k++) {
        const v3 o = q[(k + 1) & 3];
        if (vdot(n, vcross(vsub(x, o), vsub(q[k], o))) < 0.0f) return 0;
    }
    put(hit, x);
    return 1;
}

extern "C" int emLineCubeCrossCk(Vec* a, Vec* b, Mtx m, f32 sx, f32 sy, f32 sz, Vec* ofs, Vec* hit)
{
    emhit_cnt.line_cubes++;
    const Frame f = frame_of(m);
    const f32 t = cube_in(V(a), V(b), f, V(ofs), sx, sy, sz, &emhit_cnt.cube_mirrored);
    if (t < 0.0f) return 0;
    put(hit, at(V(a), V(b), t));
    return 1;
}

extern "C" int emLineCapsuleCrossCk(Vec* a, Vec* b, Vec* top, Vec* bottom, f32 r, Vec* hit)
{
    emhit_cnt.line_capsules++;
    const f32 t = capsule_in(V(a), V(b), V(bottom), V(top), r);
    if (t < 0.0f) return 0;
    put(hit, at(V(a), V(b), t));
    return 1;
}

// ==== an actor's boxes against a line or a sphere (emLineAtCk, emSphereAtCk) ====

// The box of `em` the segment enters nearest to a (squared distance at most len); that box records the point and the
// squared distance (rad, dist). Boxes flagged 0x10 pass the handgun class.
extern "C" YARARE_INFO* emLineAtCk(cEm* em, Vec* pPos, Vec* pPos2, f32 len, int flag)
{
    const v3 a = V(pPos), b = V(pPos2);
    YARARE_INFO* best = 0;
    f32 near = len;
    for (YARARE_INFO* p = &em->hitInfo; p; p = p->next) {
        if (!(p->flags & 1) || ((p->flags & 0x10) && hitsvc::handgun_class(flag))) continue;
        v3 h;
        if (!box_line(em, p, a, b, &h)) continue;
        const f32 d2 = vlen2(vsub(a, h));
        if (d2 > near) continue;
        near = d2;
        p->rad = p->dist = d2;
        put(&p->pos, h);
        best = p;
    }
    if (best) emhit_cnt.line_hits++;
    return best;
}

// The boxes of `em` the sphere (pos, r) touches. A moving sphere (more than 10 units from pos2) takes the box whose
// centre lies most along its motion: a box replaces the current one when it faces the motion at least as well, or,
// facing it at least 0.6 (cosine), when it is nearer. A still sphere takes the nearest centre. A box beyond r2 + its width
// in height is skipped when r2 differs from r. Every touched box records its centre's squared distance (rad).
extern "C" YARARE_INFO* emSphereAtCk(cEm* em, Vec* pos, Vec* pos2, f32 r, int flag, f32 r2)
{
    emhit_cnt.sphere_tests++;
    if (emhit_control == 3) r *= 0.8f;   // control sphereshort only
    const v3 c = V(pos);
    const v3 mv = vsub(c, V(pos2));
    const bool moving = vlen2(mv) > 100.0f;
    const v3 dir = moving ? vunit(mv) : mv;
    YARARE_INFO* best = 0;
    f32 best_d2 = 1e16f, best_cos = -3.1415927f;
    for (YARARE_INFO* p = &em->hitInfo; p; p = p->next) {
        if (!(p->flags & 1) || ((p->flags & 0x10) && hitsvc::handgun_class(flag))) continue;
        emhit_cnt.sphere_boxes++;
        const HitBox hb = hit_box(em, p);
        int touch;
        if (p->flags & 8) {
            Vec corners[8];
            cube_corners(em, p, corners);
            touch = At_box_sphere_ck(corners, pos, r);
        } else {
            Vec top, bottom;
            put(&top, hb.tip), put(&bottom, hb.base);
            touch = AtSphereCapsuleCk(pos, &top, r, hb.radius, &bottom) != 0;
        }
        if (!touch) continue;
        const v3 s = vsub(mid(hb), c);
        if (r != r2 && __builtin_fabsf(s.y) > r2 + p->width) continue;
        const f32 d2 = vlen2(s);
        p->rad = d2;
        if (moving) {
            const f32 cs = vdot(dir, vunit(s));
            if (cs < best_cos && (cs < 0.6f || d2 >= best_d2)) continue;
            best_cos = cs;
        } else if (d2 >= best_d2) {
            continue;
        }
        best_d2 = d2;
        best = p;
    }
    if (best) emhit_cnt.sphere_hits++;
    return best;
}

// ==== the damage position (EmGetDmPos) ====

// Where the registered hit (dmg.m_PosFrom) lands on its box: on the box's surface on the side facing the hit, at the
// hit's height along the box's axis (held to the box's length); the direction's yaw from the box's middle to the hit. A
// hit the weapon query marked (flag 0x4000) keeps its own point. In the box's frame (the part's frame moved to the box's
// first end), the hit's coordinates by the frame's inverse (the identity for a frame with no inverse).
extern "C" int EmGetDmPos(cEm* em, Vec* pos, Vec* dir)
{
    YARARE_INFO* p = em->dmg.m_pDamageYarare;
    if ((u32) p < RE4_MEM_LO || (u32) p > RE4_MEM_HI) return 0;
    emhit_cnt.dm_pos++;
    if (p->flags & 0x4000) {
        *pos = p->pos;
        dir->x = dir->z = 0.0f;
        dir->y = GetXZAngle(pos, &em->dmg.m_PosFrom);
        return 1;
    }
    const HitBox hb = hit_box(em, p);
    Frame g = hb.f;
    g.pos = hb.base;
    const v3 from = V(em->dmg.m_PosFrom);
    v3 l;
    if (vdot(g.left, vcross(g.up, g.forward)) == 0.0f) l = from;
    else l = inverse_point(frame_inverse(g), from);
    const int k = hb.axis;
    const f32 h = k == 0 ? l.x : k == 1 ? l.y : l.z;
    v3 across = vsub(l, along(k, h));   // the hit across the box's axis
    if (vzero(across)) across = k == 0 ? shz_vec3_init(0.0f, 1.0f, 0.0f) : shz_vec3_init(1.0f, 0.0f, 0.0f);
    const f32 surface = emhit_control == 2 ? 0.0f : hb.radius;   // control dmposmid: the box's axis, not its side
    const f32 hh = h < 0.0f ? 0.0f : h > p->height ? p->height : h;
    put(pos, frame_point(g, vadd(vscale(vunit(across), surface), along(k, hh))));
    Vec m;
    put(&m, mid(hb));
    dir->x = dir->z = 0.0f;
    dir->y = GetXZAngle(&m, &em->dmg.m_PosFrom);
    return 1;
}

// ==== the attack checks (EmAtkHitCk2, EmAtkHitSubCk2, EmAtkHitCk, EmAtkLineHitCk) ====

// An attack sphere (pPos, the info's range; pPosOld a tick before) against the player: the box it touches (with no
// scenery between the player and the sphere) becomes the player's damaged box; the answer is the reaction class, 0 for
// no hit. The direction is the sphere's motion, or from the sphere to the player when it moved under 100 units across.
extern "C" int EmAtkHitCk2(EmAtkInfo* info, Vec* pPos, Vec* pPosOld)
{
    emhit_cnt.atk_sphere++;
    if (debug_boxes()) emhit_cnt.debug_draws++;   // the attack sphere's debug drawing: not drawn
    if ((s16) pG->pl_life <= 0 || dying(pPL)) return 0;
    if (EatMgr.hitCheck(&pPL->getPartsPtr(0)->world, pPos, 0, 0, 0, 0)) return 0;
    YARARE_INFO* part = emSphereAtCk(pPL, pPos, pPosOld, info->range, 0x18, info->range);
    if (!part) return 0;
    part->flags &= 0xBFFF;
    pPL->dmg.m_pDamageYarare = part;
    const v3 a = V(pPos), o = V(pPosOld);
    const f32 dx = a.x - o.x, dz = a.z - o.z;
    const v3 d = dx * dx + dz * dz < 10000.0f ? vsub(V(pPL->pos), a) : vsub(a, o);
    emhit_cnt.atk_hits++;
    return reaction_class(pPos, d);
}

// The same sphere against the partner: her touched box (no scenery between her and the sphere), or none.
extern "C" YARARE_INFO* EmAtkHitSubCk2(EmAtkInfo* info, Vec* pPos, Vec* pPosOld)
{
    emhit_cnt.atk_sphere++;
    if (debug_boxes()) emhit_cnt.debug_draws++;
    cSubChar* sub = pSUB;
    if (!sub || sub->hp <= 0 || dying(sub)) return 0;
    if (EatMgr.hitCheck(&sub->getPartsPtr(0)->world, pPos, 0, 0, 0, 0)) return 0;
    YARARE_INFO* part = emSphereAtCk(sub, pPos, pPosOld, info->range, 0x18, info->range);
    if (part) part->flags &= ~0x4000;
    return part;
}

// The attack's consequences are the behaviour's own calls (LifeDownSet2 with the info's damage and keep flag,
// PlSetDamage with the reaction, the partner's cDmgInfo::set); the info's flag 8 empties the player's life (a decision
// statement of the original, docs/engine/lanes/eng-e2a.md). Bit 0: the player was hit, bit 1: the partner.
extern "C" int EmAtkHitCk(EmAtkInfo* info, Vec* pPos, Vec* pPosOld, int noSub)
{
    int ret = 0;
    if (const int cls = EmAtkHitCk2(info, pPos, pPosOld)) {
        LifeDownSet2(pPL, info->dmg, 0, (info->flag & 4) ? 1 : 0);
        if (info->flag & 8) pG->pl_life = 0;
        PlSetDamage(cls - 1, 0, 0);
        ret = 1;
    }
    if (noSub) return ret;
    if (YARARE_INFO* part = EmAtkHitSubCk2(info, pPos, pPosOld)) {
        pSUB->dmg.set(0, 10, 0x18, pPosOld, part->rad, part);
        ret |= 2;
    }
    return ret;
}

// A line attack (thrown weapons): the scenery stops it (hit, normal, attribute); then the player's box it enters before
// that point, when the player is alive, shown, not dying and his root lies in the line's ground frame. The box is
// marked (flag 0x4000) and returned in place of an actor, as the behaviour reads it.
extern "C" cEm* EmAtkLineHitCk(Vec* pPos, Vec* pPos2, Vec* hit, Vec* nrm, u32* attr)
{
    emhit_cnt.atk_line++;
    const int at = EatMgr.hitCheck(pPos, pPos2, hit, nrm, 0, 0x400000);
    f32 len = 1e16f;
    if (at) {
        len = vlen2(vsub(V(pPos), V(hit)));
    } else {
        *hit = *pPos2;
        nrm->x = nrm->y = nrm->z = 0.0f;
    }
    if (attr) *attr = at;
    cPlayer* pl = pPL;
    if (!(pl->be_flag & 1) || !(pl->be_flag & 0x20) || (s16) pG->pl_life <= 0 || dying(pl)) return 0;
    if (LineFrame(V(pPos), V(pPos2)).outside(V(pl->getPartsPtr(0)->world))) return 0;
    YARARE_INFO* part = emLineAtCk(pl, pPos, pPos2, len, 0x18);
    if (!part) return 0;
    part->flags |= 0x4000;
    emhit_cnt.atk_hits++;
    return (cEm*) part;
}

// ==== racks, water, the caught actor, the debug boxes ====

// A rack (kind 0x45, alive, life left, within 5000 units) in the way of `em` moving to `pos` heading `ang`: 0 when one
// of its four corners or two end midpoints (its size plus 50, through the rack's matrix) lies in the 800 x 2000 x 2000
// box ahead of the position, in the frame turned by `ang`.
extern "C" int EmRackCk(cEm* em, Vec* pos, f32 ang)
{
    emhit_cnt.racks++;
    const f32 s = sinf(ang), c = cosf(ang);
    for (u32 i = 0; i < EmMgr.nArray; i++) {
        cEm* e = (cEm*) EmMgr.workAt(i);
        if (!e || (e->be_flag & 0x201) != 1 || e->id != 0x45 || e->hp <= 0) continue;
        if (vlen2(vsub(V(em->pos), V(e->pos))) > 25000000.0f) continue;
        const EmRackWork* w = EMRACK_WK(e);
        const f32 hx = w->size.x + 50.0f, hz = w->size.z + 50.0f;
        const f32 pts[6][2] = {{hx, hz}, {hx, -hz}, {-hx, hz}, {-hx, -hz}, {0.0f, -hz}, {0.0f, hz}};
        const Frame rf = frame_of(e->mat);
        for (const auto& q : pts) {
            const v3 r = vsub(frame_point(rf, shz_vec3_init(q[0], 0.0f, q[1])), V(pos));
            const f32 x = c * r.x - s * r.z, z = s * r.x + c * r.z;
            if (x < 400.0f && x > -400.0f && z < 2000.0f && z > 0.0f && r.y < 1000.0f && r.y > -1000.0f) return 0;
        }
    }
    return 1;
}

// In water: the model's position at or under the room's water surface, and (for a part) that part's root not more than
// 300 under it.
extern "C" int CheckInWater(cModel* m, int parts)
{
    emhit_cnt.water++;
    f32 h;
    if (!GetWaterHeight(&m->pos, &h) || m->pos.y > h) return 0;
    return !(parts && m->getPartsPtr(parts)->world.y + 300.0f < h);
}

// The caught actor's tick: it follows its catcher's ground motion since the last tick and closes `rate2` of its catch
// offset on the ground; its motion steps with the remaining turn applied; then `rate` of the remaining turn is taken
// and its matrix rebuilt (rotation, position, scale).
extern "C" int EmCatchMotionMove(cEm* em, f32 rate, f32 rate2)
{
    emhit_cnt.catch_moves++;
    cEm* by = (cEm*) em->dmgType;
    v3 step = vsub(V(by->pos), V(by->x3A8));
    step.y = 0.0f;
    v3 p = vadd(V(em->pos), step);
    v3 close = vscale(V(em->catchOfs), rate2);
    close.y = 0.0f;
    p = vadd(p, close);
    put(&em->pos, p);
    put(&em->catchOfs, vsub(V(em->catchOfs), close));
    const f32 yaw = em->ang.y;
    em->ang.y = LIMIT_ANGLE(yaw + em->catchTurn);
    const int ret = MotionMove(em, 0);
    const f32 turn = em->catchTurn * rate;
    em->catchTurn -= turn;
    em->ang.y = LIMIT_ANGLE(yaw + turn);
    RotMatrix(em->mat, &em->ang);
    TransMatrix(em->mat, &em->pos);
    ScaleMatrix(em->mat, &em->scale);
    em->x3A8 = em->pos;
    return ret;
}

// The hit boxes' debug drawing: nothing is drawn (the engine's renderer has no debug wireframes); counted when asked.
extern "C" void EmYarareDisp(cEm* em)
{
    (void) em;
    if (debug_boxes()) emhit_cnt.debug_draws++;
}

// ==== blood at a hit (EmDmBloodSet2, EmPlBloodSet2, EmSubBloodSet): the effect service started at a computed place ====

extern "C" void EmDmBloodSet2(cEm* em, int no, int prm, int rnd, int esp_core_flg, int f)
{
    Vec pos, dir;
    if (!EmGetDmPos(em, &pos, &dir)) return;
    emhit_cnt.bloods++;
    if (rnd) {   // a scatter of up to 50 units: presentation, the engine's generator
        emhit_cnt.blood_scatter++;
        pos.x += ((f32) eng_pres_u8() * (2.0f / 255.0f) - 1.0f) * 50.0f;
        pos.y += ((f32) eng_pres_u8() * (2.0f / 255.0f) - 1.0f) * 50.0f;
        pos.z += ((f32) eng_pres_u8() * (2.0f / 255.0f) - 1.0f) * 50.0f;
    }
    EstSet(0, -1, &pos, &dir, no, prm & 0xFF, esp_core_flg, f & 0xFF, (u32) em, 0);
}

namespace {
// the player's and the partner's blood: the default set (type 1: the two-burst set) or the caller's effect
void blood_at(Vec* p, Vec* rot, int type, int eff_id, int est_id)
{
    emhit_cnt.bloods++;
    if (eff_id != 0xFF && est_id != 0xFF) {
        EstSet(0, -1, p, rot, eff_id, est_id, 0, 0, 0, 0);
    } else if (type == 1) {
        EstSet(0, -1, p, rot, 0, 1, 0, 0, 0, 0);
        EstSet(0, -1, p, rot, 0, 2, 0, 0, 0, 0);
    } else {
        EstSet(0, -1, p, rot, 0, 0, 0, 0, 0, 0);
    }
}
}   // namespace

extern "C" void EmPlBloodSet2(cModel* m, Vec* p, int type, int eff_id, int est_id)
{
    (void) m, (void) p;
    Vec pos, dir;
    if (EmGetDmPos(pPL, &pos, &dir)) blood_at(&pos, &dir, type, eff_id, est_id);
}

// The partner's blood: on her body's front (half its width out from its axis, turned toward `pos`), at `pos`'s height
// held within 0.7 of the body's height of its centre.
extern "C" void EmSubBloodSet(cEm* em, Vec* pos, int type, int eff_id, int est_id)
{
    (void) em;
    cSubChar* sub = pSUB;
    if (!sub) return;
    const YARARE_INFO* hit = &sub->hitInfo;
    Vec c;
    put(&c, frame_point(frame_of(sub->getPartsPtr(0)->mat), V(hit->ofs)));
    const f32 lim = hit->height * 0.7f;
    f32 h = pos->y - c.y;
    h = h > lim ? lim : h < -lim ? -lim : h;
    Vec rot = {0.0f, GetXZAngle(&c, pos), 0.0f};
    const f32 out = hit->width * 0.5f;
    Vec q = {c.x + sinf(rot.y) * out, c.y + h, c.z + cosf(rot.y) * out};
    blood_at(&q, &rot, type, eff_id, est_id);
}

// ==== a blast (PlBombHitCk, GetWepTargetListBomb) ====

// The blast (pos, r) against the player: none beyond 6000 units or beyond r + 300. Past the inner radius (1500 for the
// 0x0D02 weapons, else 2500) the behaviour's knock-down reaction (9); inside it, with no scenery between, the
// behaviour's life loss (1200, kept above 1 when over 500) and reaction 8 and the core archive's rumble 7. 1 when hit.
extern "C" int PlBombHitCk(Vec* pos, f32 r)
{
    emhit_cnt.bomb_player++;
    if ((s16) pG->pl_life <= 0 || dying(pPL)) return 0;
    Vec* root = &pPL->getPartsPtr(0)->world;
    const f32 d2 = vlen2(vsub(V(pos), V(root)));
    if (d2 > 36000000.0f || d2 > (r + 300.0f) * (r + 300.0f)) return 0;
    const f32 inner = (G_WEP_ID & 0xFFFF0000) == 0x0D020000 ? 1500.0f : 2500.0f;
    if (d2 > inner * inner) {
        PlSetDamage(9, 0, 0);
        return 1;
    }
    if (EatMgr.hitCheck(pos, root, 0, 0, 0, 0x400000)) return 0;
    LifeDownSet2(pPL, 1200, 0, (s16) pG->pl_life >= 501);
    PlSetDamage(8, 0, 0);
    VibSetData((VibDataTbl*) (pG->pArc->ofs_1C + (u32) pG->pArc), 7, 1);
    return 1;
}

// The actors a blast (pos, r) reaches, nearest first, at most `max`: every live enemy (and the partners 3 / 4 unless
// flag bit 0) with life left and not dying (kind 0x4F not for weapon 0xE), whose box the blast sphere touches
// (emSphereAtCk; the partners' radius held to 2500 / 1500, the grenade kinds' height reach to 2000), and with no scenery
// between the blast and the box's middle unless the box has flag 0x80 or the middle is within 0.3 of the radius (the
// partners and kind 0x39 always tested). A full list gives its farthest place to a nearer actor. The grenades (0xD,
// 0x12, 0x13) test the player first.
extern "C" int GetWepTargetListBomb(Vec* pos, f32 r, WepTarget* list, int max, int type, int flag)
{
    emhit_cnt.bomb_lists++;
    if (type == 0xD || type == 0x12 || type == 0x13) PlBombHitCk(pos, r);
    if (debug_boxes()) emhit_cnt.debug_draws++;
    const bool grenade = type == 0xD || type == 0x12 || type == 0x13 || type == 0x2D;
    int n = 0;
    for (u32 i = 0; i < EmMgr.nArray; i++) {
        cEm* em = (cEm*) EmMgr.workAt(i);
        if (!em || !(em->be_flag & 1) || !(em->be_flag & 0x20)) continue;
        const int id = em->id;
        const bool partner = id == 3 || id == 4;
        if ((id <= 0xF && !partner) || em->hp <= 0 || dying(em)) continue;
        if ((type == 0xE && id == 0x4F) || ((flag & 1) && partner)) continue;
        const f32 reach = id == 3 && r > 2500.0f ? 2500.0f : id == 4 && r > 1500.0f ? 1500.0f : r;
        const f32 tall = grenade && reach > 2000.0f ? 2000.0f : reach;
        YARARE_INFO* part = emSphereAtCk(em, pos, pos, reach, type, tall);
        if (!part) continue;
        part->flags &= ~0x4000;
        if (!(part->flags & 0x80)) {
            Vec c;
            put(&c, mid(hit_box(em, part)));
            const f32 near = reach * 0.3f;
            if (vlen2(vsub(V(pos), V(c))) > near * near || partner || id == 0x39) {
                if (EatMgr.hitCheck(pos, &c, 0, 0, 0, type != 0x10 ? 0x400000 : 0)) continue;
            }
        }
        if (n < max) {
            list[n].part = part, list[n].em = em;
            n++;
            continue;
        }
        int far = 0;
        for (int j = 1; j < max; j++)
            if (list[far].part->rad <= list[j].part->rad) far = j;
        if (list[far].part->rad > part->rad) list[far].part = part, list[far].em = em;
    }
    for (int i = 1; i < n; i++)   // nearest first (insertion: a list of a few)
        for (int j = i; j > 0 && list[j - 1].part->rad > list[j].part->rad; j--) {
            const WepTarget s = list[j];
            list[j] = list[j - 1];
            list[j - 1] = s;
        }
    return n;
}
