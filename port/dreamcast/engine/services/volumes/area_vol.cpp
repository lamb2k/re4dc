// area_vol.cpp (lane eng-e2a, 2026-11-21): the scenario areas, native. An area record (AreaData: the room script's and
// the scene attachments' trigger volumes, the Ganados' spawn zones) is a prism over a ground quad, a vertical cylinder,
// or an eye trigger (a point that looks along a direction). The behaviour keeps every decision about areas (which area,
// what entering it does); these are the questions it asks of one (docs/engine/lanes/eng-e2a.md, item 3).
//
// - In an area: both kinds take the same height band, from 100 under the floor up to (not including) floor + height. A
//   quad holds the point when it lies inside the wedges of two opposite corners (corner 0 between its edges to corners 1
//   and 3, corner 2 between its edges to corners 3 and 1), by the camera's ground-edge side test (camera/area_edge.h,
//   shared with lane eng-e1j's camera areas); a cylinder when the point's ground distance from its axis is under the
//   radius (an exact root, as the original's). An eye trigger holds no point.
// - Seen by an eye trigger: its point (floor height) and its view direction (the trigger's two angles through the math
//   service's rotation) handed to the view-cone test with the trigger's radius as margin and half its opening (all
//   round when 0) as the facing limit. The view-cone test (geometry.cpp) is not hosted in the fight image: its generated
//   stub answers 0, so an eye trigger never fires there, as before this lane (counted: E2 AREA eye-tests).
// - The centre: the quad's mean corner at floor height; the cylinder's and the eye's own point.
// - A point inside: the quad's bilinear point at two draws of the behaviour generator (fRand0_1: where an enemy appears
//   is behaviour), between its edges 0 -> 1 and 3 -> 2; the centre for the other kinds.
// - A default area (the scene attachments' and the debug tools' areas): a square, a cylinder or an eye trigger around a
//   point.
#define fabsf area_game_fabsf
#include "types.h"
#include "vec.h"
#include "global.h"
#include "area.h"
#include "geometry.h"
#include "db_log.h"
#include "rnd.h"
#include "math_sub.h"
#undef fabsf
#include "../camera/area_edge.h"

extern "C" {
struct AreaCounters { u32 hit_tests, hits, eye_tests, centres, inside_points, inits, bad_types; };
AreaCounters area_cnt;
// Control (PC check only, svc/e2_dump.cpp RE4_SVC_CONTROL "areawide"): every cylinder area 10% wider, every quad's band
// 100 higher. The check must fail.
int area_control;
int collision_point_cone_rev_play_face(Vec* p, GeoCone* cone, Vec* face, f32 margin, f32 angle);
}

namespace {
using areasvc::edge_side;
const char kBadType[] = "AREA_HIT_DATA : AREA_TYPE[%d] invalid.";
bool in_band(const Vec* p, f32 floor, f32 height)
{
    const f32 lift = area_control == 1 ? 100.0f : 0.0f;   // control areawide only
    return !(p->y + 100.0f < floor + lift) && p->y < floor + height;
}
void bad_type(const AreaData* a)
{
    area_cnt.bad_types++;
    pLog->warn(0, 0, kBadType, a->type);
}
}   // namespace

extern "C" int areaHitCheck_xz4(AreaXZ4* q, Vec* pos)
{
    if (!in_band(pos, q->floor, q->height)) return 0;
    const AreaXZ* c = q->p;
    return edge_side(c[0], c[3], pos) >= 0.0f && edge_side(c[0], c[1], pos) <= 0.0f && edge_side(c[2], c[3], pos) <= 0.0f &&
           edge_side(c[2], c[1], pos) >= 0.0f;
}

extern "C" int areaHitCheck_Cylinder(AreaCylinder* c, Vec* pos)
{
    if (!in_band(pos, c->floor, c->height)) return 0;
    const f32 dx = pos->x - c->x, dz = pos->z - c->z;
    const f32 r = area_control == 1 ? c->radius * 1.1f : c->radius;
    return __builtin_sqrtf(dx * dx + dz * dz) < r;
}

int AreaHitCheck(void* area, Vec* pos)
{
    AreaData* a = (AreaData*) area;
    area_cnt.hit_tests++;
    int in = 0;
    switch (a->type) {
    case AREA_TYPE_XZ4: in = areaHitCheck_xz4(&a->u.xz4, pos); break;
    case AREA_TYPE_CYLINDER: in = areaHitCheck_Cylinder(&a->u.cyl, pos); break;
    case AREA_TYPE_EYE: break;
    default: bad_type(a); break;
    }
    area_cnt.hits += in != 0;
    return in;
}

extern "C" int AreaViewCheck(AreaData* area, GeoCone* cone)
{
    if (area->type == AREA_TYPE_XZ4 || area->type == AREA_TYPE_CYLINDER) return 0;
    if (area->type != AREA_TYPE_EYE) {
        bad_type(area);
        return 0;
    }
    area_cnt.eye_tests++;
    const AreaEyeTrigger& e = area->u.eye;
    Vec at = {e.xz, e.floor, e.z}, rot = {e.ang_x, e.ang_y, 0.0f}, look = {0.0f, 0.0f, 1.0f};
    Mtx m;
    RotMatrix(m, &rot);
    look = Vec{m[0][2], m[1][2], m[2][2]};   // the rotation's z axis: where the trigger looks
    return collision_point_cone_rev_play_face(&at, cone, &look, e.radius, e.open == 0.0f ? 3.1415927f : e.open * 0.5f);
}

extern "C" void AreaGetCenterPos(Vec* out, AreaData* area)
{
    area_cnt.centres++;
    switch (area->type) {
    case AREA_TYPE_XZ4: {
        const AreaXZ* c = area->u.xz4.p;
        *out = Vec{(c[0].x + c[1].x + c[2].x + c[3].x) * 0.25f, area->u.xz4.floor, (c[0].z + c[1].z + c[2].z + c[3].z) * 0.25f};
        break;
    }
    case AREA_TYPE_CYLINDER: *out = Vec{area->u.cyl.x, area->u.cyl.floor, area->u.cyl.z}; break;
    case AREA_TYPE_EYE: *out = Vec{area->u.eye.xz, area->u.eye.floor, area->u.eye.z}; break;
    default: bad_type(area); break;
    }
}

extern "C" void AreaGetInsidePos(Vec* out, AreaData* area)
{
    area_cnt.inside_points++;
    if (area->type != AREA_TYPE_XZ4) {
        if (area->type == AREA_TYPE_CYLINDER || area->type == AREA_TYPE_EYE) AreaGetCenterPos(out, area);
        else *out = Vec{0.0f, 0.0f, 0.0f};
        return;
    }
    const AreaXZ* c = area->u.xz4.p;
    const f32 s = fRand0_1(), t = fRand0_1();   // behaviour: across the edges, then between them
    const f32 ax = c[0].x + (c[1].x - c[0].x) * s, az = c[0].z + (c[1].z - c[0].z) * s;   // on edge 0 -> 1
    const f32 bx = c[3].x + (c[2].x - c[3].x) * s, bz = c[3].z + (c[2].z - c[3].z) * s;   // on edge 3 -> 2
    *out = Vec{ax + (bx - ax) * t, area->u.xz4.floor, az + (bz - az) * t};
}

extern "C" void AreaDataInit(AreaData* area, Vec* pos, u8 type, f32 size, f32 height)
{
    area_cnt.inits++;
    area->Be_flag = 1;
    area->x2 = 0;
    area->type = type;
    const f32 half = size * 0.5f;
    switch (type) {
    case AREA_TYPE_XZ4: {
        AreaXZ4& q = area->u.xz4;
        q.floor = pos->y, q.height = height, q.radius = half;
        const f32 sx[4] = {-half, half, half, -half}, sz[4] = {-half, -half, half, half};
        for (int i = 0; i < 4; i++) q.p[i].x = pos->x + sx[i], q.p[i].z = pos->z + sz[i];
        break;
    }
    case AREA_TYPE_CYLINDER: {
        AreaCylinder& c = area->u.cyl;
        c = AreaCylinder{};
        c.x = pos->x, c.z = pos->z, c.floor = pos->y, c.height = height, c.radius = half;
        break;
    }
    case AREA_TYPE_EYE: {
        AreaEyeTrigger& e = area->u.eye;
        e = AreaEyeTrigger{};
        e.xz = pos->x, e.z = pos->z, e.floor = pos->y, e.height = height, e.radius = half;
        break;
    }
    default: bad_type(area); break;
    }
}
