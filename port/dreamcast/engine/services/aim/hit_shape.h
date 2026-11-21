// hit_shape.h (lane eng-e2a): the rules the enemy hit geometry (services/aim/em_hit.cpp) shares with the weapon-target
// query of lanes eng-e1f / eng-e1g / eng-e1k (services/aim/aim.cpp keeps its own copies, unchanged, so its checked
// answers stay as they were): the handgun class, the big enemies, a line's ground frame. An actor's
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

}   // namespace hitsvc
