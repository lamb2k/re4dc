// aim.cpp: the native weapon-target query (lane eng-e1f, 2026-11-20): GetWepTargetPos, the point the weapon line hits.
//
// Behaviour calls it by its original name (objWep.cpp's laser sight: the laser's end, the target and the "don't fire"
// surface; pl_push.cpp's push target; em39 and the mine): from p0 towards p1 it returns 1 when the scenery stops the
// line, 2 when an enemy's hit box does (3 when that box has flag 0x40), 0 otherwise, moves p1 to the hit point and names
// the enemy and the surface attribute. Aim is behaviour; this query draws no random number (the original does not).
//
// Engine form, not the original's arithmetic (em_sub.cpp GetWepTargetPos / emLineAtCk2 / emLineCapsuleCrossCk /
// emLineCubeCrossCk): the scenery through the native collision service (EatMgr.hitCheck, services/collision); the
// enemies on the actor table with the same filters (alive, not hidden, life left, the 10000-unit box ahead of the line
// and the player's front half for ordinary enemies; the original asks its box test with weapon 0, so no handgun-proof
// box is skipped here); each hit box
// tested as an oriented box (flag 8: x -sx..sx, y 0..sy, z -sz..sz about the box centre in the part's frame) by a slab
// test, or as a capsule (axis ofs -> ofs + height along the part's y, or x / z by flags 2 / 4, radius the part's scale of
// the width) by the segment's entry point into the infinite cylinder and the two end spheres. The nearest box by the
// XZ distance from p0 wins inside an enemy, the nearest enemy by the 3D distance overall, as the original.
// include/math_sub.h defines a static fabsf (the SDK header's) that clashes with the C library's, which SH4ZAM's headers
// declare: the game headers see it under another name (as services/math/math_svc.cpp).
#define fabsf aim_game_fabsf
#include "types.h"
#include "global.h"
#include "model.h"
#include "player.h"
#include "em.h"
#include "atari.h"
#undef fabsf
#include "sh4zam/shz_scalar.h"
#include "sh4zam/shz_trig.h"

extern "C" {
// counters for the lane's checks (printed with the image's report: core/frame.cpp)
struct AimCounters { u32 calls, scenery, enemy, enemy_flag40, boxes, capsules, cubes; };
AimCounters aim_cnt;
// Control (lane eng-e1g; set only by the PC reference's aim check, hostref svc/aimcheck.cpp, RE4_AIM_CONTROL=grow):
// 1 makes every enemy hit box and capsule 25% larger, which the shadow comparison and the hit fixtures must catch.
int aim_control;
int GetWepTargetPos(Vec* pPos, Vec* pPos2, int plCheck, int wepNo, cEm** outEm, int* outAttr);
}

namespace {

struct V { f32 x, y, z; };
inline V v(const Vec& a) { return {a.x, a.y, a.z}; }
inline V sub(V a, V b) { return {a.x - b.x, a.y - b.y, a.z - b.z}; }
inline V add(V a, V b) { return {a.x + b.x, a.y + b.y, a.z + b.z}; }
inline V mul(V a, f32 s) { return {a.x * s, a.y * s, a.z * s}; }
inline f32 dot(V a, V b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
// a point through a part's 3x4 matrix (rows: the part's axes and position, as cModel::mat)
inline V point(const Mtx m, V p)
{
    return {m[0][0] * p.x + m[0][1] * p.y + m[0][2] * p.z + m[0][3], m[1][0] * p.x + m[1][1] * p.y + m[1][2] * p.z + m[1][3],
            m[2][0] * p.x + m[2][1] * p.y + m[2][2] * p.z + m[2][3]};
}
inline V axis(const Mtx m, int c) { return {m[0][c], m[1][c], m[2][c]}; }

// The handguns (and the guns that share their hit rule) ignore the boxes with flag 0x10 (em_sub.cpp HandgunCk).
bool handgun(int wep)
{
    switch (wep) {
    case 1: case 2: case 3: case 4: case 0x11: case 0x26: case 0x2B: return true;
    default: return false;
    }
}

// Entry of segment a + t (b - a), t in [0, 1], into the oriented box: centre c, axes e (not unit: the part's scale),
// extents lo..hi per axis. Returns t or -1.
f32 box_entry(V a, V b, V c, const V e[3], const f32 lo[3], const f32 hi[3])
{
    f32 t0 = 0.0f, t1 = 1.0f;
    const V d = sub(b, a), r = sub(a, c);
    for (int k = 0; k < 3; k++) {
        const f32 n = dot(e[k], e[k]);
        if (n <= 0.0f) return -1.0f;
        const f32 p = dot(r, e[k]) / n, q = dot(d, e[k]) / n;   // local coordinate and its rate
        if (q == 0.0f) {
            if (p < lo[k] || p > hi[k]) return -1.0f;
            continue;
        }
        f32 ta = (lo[k] - p) / q, tb = (hi[k] - p) / q;
        if (ta > tb) { const f32 s = ta; ta = tb; tb = s; }
        if (ta > t0) t0 = ta;
        if (tb < t1) t1 = tb;
        if (t0 > t1) return -1.0f;
    }
    return t0;
}

// Entry of the segment (a, direction d) into a sphere; t in [0, 1] or -1.
f32 sphere_entry(V a, V d, V c, f32 r)
{
    const V m = sub(a, c);
    const f32 A = dot(d, d), B = dot(m, d), C = dot(m, m) - r * r;
    if (C <= 0.0f) return 0.0f;   // starts inside
    if (A <= 0.0f) return -1.0f;
    const f32 disc = B * B - A * C;
    if (disc < 0.0f) return -1.0f;
    const f32 t = (-B - shz_sqrtf(disc)) / A;
    return t >= 0.0f && t <= 1.0f ? t : -1.0f;
}
// Entry of the segment into the capsule (axis p -> q, radius r): the cylinder's side between the end planes, or an end
// sphere. Returns t in [0, 1] or -1.
f32 capsule_entry(V a, V b, V p, V q, f32 r)
{
    const V d = sub(b, a), ax = sub(q, p);
    const f32 aa = dot(ax, ax);
    f32 best = -1.0f;
    if (aa > 0.0f) {
        // the side: |(x - p) - ((x - p).ax / aa) ax| = r with x = a + t d
        const V m = sub(a, p);
        const f32 md = dot(m, ax), nd = dot(d, ax);
        const V mp = sub(m, mul(ax, md / aa)), dp = sub(d, mul(ax, nd / aa));
        const f32 A = dot(dp, dp), B = dot(mp, dp), C = dot(mp, mp) - r * r;
        f32 t = -1.0f;
        if (C <= 0.0f) t = 0.0f;
        else if (A > 0.0f && B * B - A * C >= 0.0f) t = (-B - shz_sqrtf(B * B - A * C)) / A;
        if (t >= 0.0f && t <= 1.0f) {
            const f32 s = (md + t * nd) / aa;   // where along the axis
            if (s >= 0.0f && s <= 1.0f) best = t;
        }
    }
    const f32 tp = sphere_entry(a, d, p, r), tq = sphere_entry(a, d, q, r);
    if (tp >= 0.0f && (best < 0.0f || tp < best)) best = tp;
    if (tq >= 0.0f && (best < 0.0f || tq < best)) best = tq;
    return best;
}

cModel* hit_part(cEm* em, YARARE_INFO* p) { return p->partsNo ? em->getPartsPtr(p->partsNo - 1) : (cModel*) em; }

// The enemy's hit box the line meets nearest to p0 in XZ (squared XZ distance under `limit`); its point in *out.
YARARE_INFO* enemy_line(cEm* em, V a, V b, f32 limit, V* out, int wep)
{
    YARARE_INFO* ret = 0;
    f32 best = limit;
    for (YARARE_INFO* p = &em->hitInfo; p; p = p->next) {
        if (!(p->flags & 1)) continue;
        if ((p->flags & 0x10) && handgun(wep)) continue;
        cModel* part = hit_part(em, p);
        aim_cnt.boxes++;
        const f32 g = aim_control == 1 ? 1.25f : 1.0f;   // the control only
        f32 t;
        if (p->flags & 8) {
            aim_cnt.cubes++;
            const V e[3] = {axis(part->mat, 0), axis(part->mat, 1), axis(part->mat, 2)};
            const f32 lo[3] = {-p->width * g, 0.0f, -p->depth * g}, hi[3] = {p->width * g, p->height * g, p->depth * g};
            t = box_entry(a, b, point(part->mat, v(p->ofs)), e, lo, hi);
        } else {
            aim_cnt.capsules++;
            V top = v(p->ofs);
            if (p->flags & 6) { if (p->flags & 2) top.x += p->height; else top.z += p->height; }
            else top.y += p->height;
            const V az = axis(part->mat, 2);
            t = capsule_entry(a, b, point(part->mat, v(p->ofs)), point(part->mat, top), p->width * g * shz_sqrtf(dot(az, az)));
        }
        if (t < 0.0f) continue;
        const V h = add(a, mul(sub(b, a), t));
        const f32 dx = a.x - h.x, dz = a.z - h.z, d2 = dx * dx + dz * dz;
        if (d2 > best) continue;
        best = d2;
        ret = p;
        *out = h;
    }
    return ret;
}

}  // namespace

extern "C" int GetWepTargetPos(Vec* pPos, Vec* pPos2, int plCheck, int wepNo, cEm** outEm, int* outAttr)
{
    (void) wepNo;   // unused by the original too
    aim_cnt.calls++;
    if (outEm) *outEm = 0;
    int ret = 0;
    Vec hitv;
    const int attr = EatMgr.hitCheck(pPos, pPos2, &hitv, 0, 0, 0x400000);   // the scenery (native collision service)
    V hit;
    if (attr) {
        ret = 1;
        aim_cnt.scenery++;
        if (outAttr) *outAttr = attr;
        hit = v(hitv);
    } else {
        hit = v(*pPos2);
    }
    const V a = v(*pPos), b = v(*pPos2);
    f32 dist = dot(sub(a, hit), sub(a, hit));
    const f32 len = dist;   // each enemy's box test is limited by the scenery hit's distance, as the original's
    // the line's frame on the ground: forward along a -> b in XZ (the original's yaw-only inverse matrix; it falls back
    // to the identity when dx == dz)
    V fwd = {b.x - a.x, 0.0f, b.z - a.z};
    const f32 fl = dot(fwd, fwd);
    const bool frame = !(b.x - a.x == b.z - a.z) && fl > 0.0f;
    if (frame) fwd = mul(fwd, 1.0f / shz_sqrtf(fl));
    const V side = {fwd.z, 0.0f, -fwd.x};
    for (u32 i = 0; i < EmMgr.nArray; i++) {
        cEm* em = (cEm*) EmMgr.workAt(i);
        if (!em) continue;
        if ((em->be_flag & 0x201) != 1 || (em->be_flag & 0x10000000)) continue;
        if (plCheck ? i != 0 : i == 0) continue;
        const int life = plCheck ? pG->pl_life : em->hp;
        if (life <= 0) continue;
        switch (em->id) {
        case 0x2B: case 0x2F: case 0x31: case 0x37: case 0x38: case 0x3B: case 0x3E: case 0x4D:
            break;   // the big enemies: no box or front filter
        default: {
            const V w = v(em->getPartsPtr(0)->world), r = sub(w, a);
            const f32 lz = frame ? dot(r, fwd) : r.z, lx = frame ? dot(r, side) : r.x;
            if (lz < -10000.0f || lx > 10000.0f || lx < -10000.0f) continue;
            // the player's front half (sub2.cpp Front_check(pPL, em, PI / 2)): within 90 degrees of the facing
            const f32 fx = shz_sinf(pPL->ang.y), fz = shz_cosf(pPL->ang.y);
            if ((em->pos.x - pPL->pos.x) * fx + (em->pos.z - pPL->pos.z) * fz < 0.0f) continue;
        }
        }
        V h2;
        YARARE_INFO* part = enemy_line(em, a, b, len, &h2, 0);   // the original passes weapon 0 here: no box skipped
        if (!part) continue;
        const f32 e2 = dot(sub(a, h2), sub(a, h2));
        if (e2 > dist) continue;
        dist = e2;
        hit = h2;
        if (outEm) *outEm = em;
        ret = part->flags & 0x40 ? 3 : 2;
    }
    if (ret >= 2) { aim_cnt.enemy++; if (ret == 3) aim_cnt.enemy_flag40++; }
    pPos2->x = hit.x; pPos2->y = hit.y; pPos2->z = hit.z;
    return ret;
}
