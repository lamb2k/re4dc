// area_edge.h (lane eng-e2a): the ground-edge side test the camera's area containment (cam_eval.cpp, lane eng-e1j) and
// the scenario areas (services/volumes/area_vol.cpp) share. A point's side of the ground edge a -> b: the y component of
// (b - a) x (p - a), from the edge's start; >= 0 on the inner side of an area laid out counter-clockwise from above.
// The difference of the two products has the sign of their comparison (IEEE subtraction is exact in sign), so a test
// on it answers as the original's comparison of the two products does. Any point type with x and z (Vec, AreaXZ).
#pragma once
#include "types.h"

namespace areasvc {
template <class A, class B, class P> inline f32 edge_side(const A& a, const B& b, const P* p)
{
    return (b.z - a.z) * (p->x - a.x) - (b.x - a.x) * (p->z - a.z);
}
}   // namespace areasvc
