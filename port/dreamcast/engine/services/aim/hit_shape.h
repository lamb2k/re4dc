// hit_shape.h (lane eng-e2a): the rules the enemy hit geometry (services/aim/em_hit.cpp) shares with the weapon-target
// query of lanes eng-e1f / eng-e1g / eng-e1k (services/aim/aim.cpp): the handgun class, the big enemies, a line's ground
// frame and (lane eng-e2g) the segment's tests against a capsule and an oriented box, so the shot and the enemy hit
// geometry answer by one rule (aim.cpp kept its own copies until eng-e2g; its capsule then took the head where the game
// takes the body: lanes/eng-e2g.md). An actor's
// hit box (YARARE_INFO) is a capsule along one of its part's axes, or, with flag 8, an oriented box; a weapon or an
// attack line is filtered by its ground frame first. SH4ZAM's vector type through the camera service's helpers
// (services/camera/cam_math.h): plain single precision, exact roots and true divisions.
#pragma once
#include "../camera/cam_math.h"

namespace hitsvc {
using camsvc::v3;
using camsvc::V;

// The weapons whose shots pass the boxes flagged 0x10 (the handguns and the guns that share their hit rule).
inline bool handgun_class(int wep)
{
    switch (wep) {
    case 1: case 2: case 3: case 4: case 0x11: case 0x26: case 0x2B: return true;
    default: return false;
    }
}

// The big enemies (El Gigante's kind and the like): no ground-frame or facing filter on their boxes.
inline bool big_enemy(int id)
{
    switch (id) {
    case 0x2B: case 0x2F: case 0x31: case 0x37: case 0x38: case 0x3B: case 0x3E: case 0x4D: return true;
    default: return false;
    }
}

// A line's ground frame: forward along p0 -> p1 in XZ, the side to its right; when dx == dz (the original's yaw-only
// frame falls back to the identity there) the world axes. outside() is the 10000-unit box ahead of the line that the
// weapon and attack queries test a body's root against.
struct LineFrame {
    v3 a, fwd, side;
    bool turned;
    LineFrame(v3 p0, v3 p1) : a(p0)
    {
        fwd = shz_vec3_init(p1.x - p0.x, 0.0f, p1.z - p0.z);
        const f32 fl = camsvc::vlen2(fwd);
        turned = !(p1.x - p0.x == p1.z - p0.z) && fl > 0.0f;
        if (turned) fwd = camsvc::vscale(fwd, 1.0f / __builtin_sqrtf(fl));
        side = shz_vec3_init(fwd.z, 0.0f, -fwd.x);
    }
    // a point's coordinates in the frame: across (x) and ahead (z)
    f32 across(v3 p) const { const v3 r = camsvc::vsub(p, a); return turned ? camsvc::vdot(r, side) : r.x; }
    f32 ahead(v3 p) const { const v3 r = camsvc::vsub(p, a); return turned ? camsvc::vdot(r, fwd) : r.z; }
    bool outside(v3 p) const
    {
        const f32 lx = across(p), lz = ahead(p);
        return lz < -10000.0f || lx > 10000.0f || lx < -10000.0f;
    }
};

// ---- a segment against the shapes: the parameter t in [0, 1] where a + t (b - a) first counts as entering, or -1 ----
// (moved here from em_hit.cpp by lane eng-e2g, unchanged but for cube_in's counter argument; em_hit.cpp and aim.cpp
// both use them)

// Into a sphere (centre c, squared radius rr) from outside: the near root of |a + t d - c|^2 = rr, taken from the line's
// nearest approach to the centre (t0, squared miss e2) as t0 - sqrt(rr - e2) / |d|: no difference of large squares.
inline f32 sphere_in(v3 a, v3 d, v3 c, f32 rr)
{
    const f32 A = camsvc::vlen2(d);
    if (A <= 0.0f) return -1.0f;
    const v3 m = camsvc::vsub(a, c);
    const f32 t0 = -camsvc::vdot(m, d) / A;
    const f32 e2 = camsvc::vlen2(camsvc::vadd(m, camsvc::vscale(d, t0)));
    if (!(e2 < rr)) return -1.0f;
    const f32 t = t0 - __builtin_sqrtf(rr - e2) / __builtin_sqrtf(A);
    return t >= 0.0f && t <= 1.0f ? t : -1.0f;
}

// Into the capsule p0 -> p1 of radius r, by the game's acceptance rule (em_sub.cpp emLineCapsuleCrossCk), which is not
// the true geometry. A start inside (either end sphere, or the cylinder between the end planes) is t = 0. A segment
// shorter than sqrt(0.1) meets nothing. Otherwise an end sphere's entry counts only when it lies beyond that end's plane
// (the p1 end first); an end-sphere entry between the end planes is left to the side test. The side's point is the
// game's, not the surface entry: from the segment's nearest approach to the axis (q across it), back toward a by
// h = sqrt(r^2 - q^2) measured ALONG THE SEGMENT, where the true entry steps back h across the axis. For a segment
// slanted to the axis that point lies inside the cylinder and, near an end, beyond the end plane: the side then refuses
// a capsule the segment truly crosses (knock-ganado's tick-521 shot passes 17 units from the head capsule's axis and the
// game gives the body). Which part a shot hits is gameplay (the damage, the death routine, the knock-down), so the engine
// answers by this rule (lanes/eng-e2a.md item 1; lanes/eng-e2g.md).
inline f32 capsule_in(v3 a, v3 b, v3 p0, v3 p1, f32 r)
{
    using namespace camsvc;
    const f32 rr = r * r;
    const v3 ax = vsub(p1, p0);
    const f32 len = vlen(ax);
    // The axis's direction for the along / across split. The game takes an axis within 0.01 rad of the vertical (up or
    // down) as the upward vertical, and a zero axis as upward too; the end spheres stay at the real ends. Lane eng-e2g:
    // the angle is the game's own, acosf of the unit axis's y against 0.01 and PI - 0.01 in single precision (a fixed
    // cosine threshold put about 1 in 1,000 axes generated within 0.02 rad of the vertical on the other side: aimprop).
    v3 u = vzero(ax) ? shz_vec3_init(0.0f, 1.0f, 0.0f) : vscale(ax, 1.0f / len);
    const f32 ang = __builtin_acosf(u.y);
    if (!(ang > 0.01f && ang < 3.1415927f - 0.01f)) u = shz_vec3_init(0.0f, 1.0f, 0.0f);
    const v3 ra = vsub(a, p0);
    const f32 sa = vdot(ra, u);
    const v3 qa = vsub(ra, vscale(u, sa));   // a across the axis
    if (vlen2(vsub(a, p1)) < rr || vlen2(ra) < rr || (sa > 0.0f && sa < len && vlen2(qa) < rr)) return 0.0f;
    const v3 d = vsub(b, a);
    if (vlen2(d) <= 0.1f) return -1.0f;
    const f32 sd = vdot(d, u);
    const v3 ends[2] = {p1, p0};
    for (const v3& c : ends) {
        const f32 t = sphere_in(a, d, c, rr);
        if (t < 0.0f) continue;
        const f32 s = sa + t * sd;
        if (s < 0.0f || s > len) return t;
    }
    const v3 qd = vsub(d, vscale(u, sd));   // the motion across the axis
    const f32 A = vlen2(qd);
    if (!(A > 0.1f)) return -1.0f;
    const f32 tn = -vdot(qa, qd) / A;                          // the nearest approach to the axis
    const f32 q2 = vlen2(vadd(qa, vscale(qd, tn)));
    if (!(q2 < rr)) return -1.0f;
    const f32 back = __builtin_sqrtf(rr - q2) / vlen(d);      // h along the segment, as a parameter
    const f32 t = tn > 0.0f ? tn - back : tn + back, s = sa + t * sd;
    return t >= 0.0f && t <= 1.0f && s >= 0.0f && s <= len ? t : -1.0f;
}

// The oriented box: its centre at `ofs` in the frame, the frame's axes, x in [-sx, sx], y in [0, sy], z in [-sz, sz] about
// the centre (em_sub.cpp emLineCubeCrossCk: the six faces as quads in turn, a crossing counted from a face's front to its
// back). In the box's own coordinates (the axes' adjugate over the determinant applied to the point less the frame's
// position, then less ofs: no world-size centre is formed) each axis gives the interval of t inside its slab; the box is
// their overlap. The faces face out of the box for a frame with a positive determinant: the segment must start outside
// and enter before b (strictly, as a crossing from one side of a face to the other); a start inside is no hit. A
// mirrored frame turns every face in: what the original's face rule then finds is where the segment leaves the box
// (counted in *mirrored when given).
inline f32 cube_in(v3 a, v3 b, const camsvc::Frame& f, v3 ofs, f32 sx, f32 sy, f32 sz, u32* mirrored = 0)
{
    using namespace camsvc;
    shz_mat3x3_t axes, adj;
    axes.col[0] = f.left, axes.col[1] = f.up, axes.col[2] = f.forward;
    shz_mat3x3_adjugate(&axes, &adj);
    const f32 det = vdot(f.left, vcross(f.up, f.forward));
    if (det == 0.0f) return -1.0f;
    const f32 k = 1.0f / det;
    auto local = [&](v3 p) {
        const v3 q = vsub(p, f.pos);
        return vsub(vscale(vadd(vadd(vscale(adj.col[0], q.x), vscale(adj.col[1], q.y)), vscale(adj.col[2], q.z)), k), ofs);
    };
    const v3 la = local(a), lb = local(b);
    const f32 lo[3] = {-sx, 0.0f, -sz}, hi[3] = {sx, sy, sz};
    const f32 pa[3] = {la.x, la.y, la.z}, pb[3] = {lb.x, lb.y, lb.z};
    f32 t_in = -1e30f, t_out = 1e30f;
    for (int i = 0; i < 3; i++) {
        const f32 dd = pb[i] - pa[i];
        if (dd == 0.0f) {
            if (pa[i] < lo[i] || pa[i] > hi[i]) return -1.0f;
            continue;
        }
        f32 t0 = (lo[i] - pa[i]) / dd, t1 = (hi[i] - pa[i]) / dd;
        if (t0 > t1) { const f32 s = t0; t0 = t1; t1 = s; }
        if (t0 > t_in) t_in = t0;
        if (t1 < t_out) t_out = t1;
    }
    if (t_in > t_out) return -1.0f;
    if (det < 0.0f) {
        if (mirrored) (*mirrored)++;
        return t_out > 0.0f && t_out < 1.0f ? t_out : -1.0f;
    }
    return t_in > 0.0f && t_in < 1.0f ? t_in : -1.0f;
}

}   // namespace hitsvc
