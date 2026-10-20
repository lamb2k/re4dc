// game/area.cpp: trigger volumes (AreaData). An area is an XZ quadrilateral with floor / height
// (AREA_TYPE_XZ4), a vertical cylinder (AREA_TYPE_CYLINDER) or a view-cone trigger
// (AREA_TYPE_EYE). AreaHitCheck / AreaViewCheck are the game-side tests (effect areas, light
// areas, floor attribute areas, scenario triggers); the rest is the debug tool editor and display
// used by the Tools/t_* screens (pad-driven point / radius / height editing, wireframe drawing,
// value and help text).
// Original source: D:/Bio4/Prog/area.cpp.
#include "types.h"
#include "re4dc_xm.h" // GAME_SH4ZAM_LOGIC (lane sh4zam-direct)
#include "vec.h"
#include "global.h"
#include "area.h"
#include "geometry.h"
#include "db_log.h"
#include "db_cam.h"
#include "eprintf.h"
#include "joy.h"
#include "rnd.h"
#include "gx.h"

// dbmodule.cpp primitives. Draw_sphere really takes its Vec by value; this unit declares it with a
// pointer (same ABI: aggregates are passed by reference), so no argument copy is made.
#define PI 3.1415927f

void RotMatrix(Mtx m, Vec* rot);  // game/math_sub.cpp

extern "C" {
void* memset(void* dst, int c, unsigned int n);
f32 sinf(f32 x);
f32 cosf(f32 x);
f32 SQRTF(f32 x);
f32 LIMIT_ANGLE(f32 x);
// game/sub2.cpp; really takes Vec*, declared by value here (same ABI) so the caller copies its Vec.
int GetScreenPos(Vec pos, Vec* scr);
void Draw_line3d(Vec* p0, Vec* p1, u32 color, int blend);
void Draw_poly(Vec* p, u32 color, int zupd);
void Draw_sphere(Vec* pos, f32 r, u32 color, int zcmp, int zupd);
void Draw_corn2(Vec* pos, Vec* dir, f32 len, f32 ang, u32 color);
}

#define AREA_TYPE_ERR "AREA_HIT_DATA : AREA_TYPE[%d] invalid."

// 1 when `pos` is inside area (quad or cylinder types; the eye type never hits). Unknown types
// warn and return 0.
int AreaHitCheck(void* area, Vec* pos)
{
    AreaData* a = (AreaData*) area;
    int ret = 0;

    switch (a->type) {
    case AREA_TYPE_XZ4:
        ret = areaHitCheck_xz4(&a->u.xz4, pos);
        break;
    case AREA_TYPE_CYLINDER:
        ret = areaHitCheck_Cylinder(&a->u.cyl, pos);
        break;
    case AREA_TYPE_EYE:
        break;
    default:
        pLog->warn(0, 0, AREA_TYPE_ERR, a->type);
        ret = 0;
        break;
    }
    return ret;
}

// Point-in-quad test: pos.y must be within [floor - 100, floor + height) and the point on the
// inner side of all four edges (cross products against edges 0-3, 0-1, 2-3, 2-1).
int areaHitCheck_xz4(AreaXZ4* pXz4, Vec* pos)
{
    f32 dz, dx;

    if (pos->y + 100.0f < pXz4->floor || pos->y >= pXz4->floor + pXz4->height) {
        return 0;
    }
    if ((pXz4->p[3].x - pXz4->p[0].x) * (pos->z - pXz4->p[0].z) > (pXz4->p[3].z - pXz4->p[0].z) * (pos->x - pXz4->p[0].x) ||
        (pXz4->p[1].x - pXz4->p[0].x) * (pos->z - pXz4->p[0].z) < (pXz4->p[1].z - pXz4->p[0].z) * (pos->x - pXz4->p[0].x)) {
        return 0;
    }
    if ((pXz4->p[3].x - pXz4->p[2].x) * (pos->z - pXz4->p[2].z) < (pXz4->p[3].z - pXz4->p[2].z) * (pos->x - pXz4->p[2].x) ||
        (pXz4->p[1].x - pXz4->p[2].x) * (pos->z - pXz4->p[2].z) > (pXz4->p[1].z - pXz4->p[2].z) * (pos->x - pXz4->p[2].x)) {
        return 0;
    }
    return 1;
}

// Point-in-cylinder test: same height band, XZ distance from the centre below radius.
int areaHitCheck_Cylinder(AreaCylinder* pCld, Vec* pos)
{
    f32 dx, dz;

    if (pos->y + 100.0f < pCld->floor || pos->y >= pCld->floor + pCld->height) {
        return 0;
    }
    dz = pos->z - pCld->z;
    dx = pos->x - pCld->x;
    return SQRTF(dx * dx + dz * dz) < pCld->radius;
}

// Eye trigger test: 1 when the trigger point (floor + height / 2), looking along ang_x / ang_y,
// sees the view cone `cone` (collision_point_cone_rev_play_face with the trigger's radius and
// opening angle). Quad / cylinder areas return 0.
int AreaViewCheck(AreaData* area, GeoCone* cone)
{
    Vec pos;
    Mtx m;
    Vec dir;
    Vec rot;
    f32 ang;
    int ret = 0;

    switch (area->type) {
    case AREA_TYPE_XZ4:
    case AREA_TYPE_CYLINDER:
        break;
    case AREA_TYPE_EYE:
        if (area->u.eye.open == 0.0f) {
            ang = PI;
        } else {
            ang = area->u.eye.open * 0.5f;
        }
        pos.x = area->u.eye.xz;
        pos.y = area->u.eye.floor;
        pos.z = area->u.eye.z;
        dir.x = 0.0f;
        dir.y = 0.0f;
        dir.z = 1.0f;
        rot.x = area->u.eye.ang_x;
        rot.y = area->u.eye.ang_y;
        rot.z = 0.0f;
        RotMatrix(m, &rot);
        PSMTXMultVecSR(m, &dir, &dir);
        ret = collision_point_cone_rev_play_face(&pos, cone, &dir, area->u.eye.radius, ang);
        break;
    default:
        pLog->warn(0, 0, AREA_TYPE_ERR, area->type);
        ret = 0;
        break;
    }
    return ret;
}

// Centre of the area at floor height (quad: mean of the 4 points).
void AreaGetCenterPos(Vec* out, AreaData* area)
{
    switch (area->type) {
    case AREA_TYPE_XZ4:
        out->x = (area->u.xz4.p[0].x + area->u.xz4.p[1].x + area->u.xz4.p[2].x + area->u.xz4.p[3].x) * 0.25f;
        out->y = area->u.xz4.floor;
        out->z = (area->u.xz4.p[0].z + area->u.xz4.p[1].z + area->u.xz4.p[2].z + area->u.xz4.p[3].z) * 0.25f;
        break;
    case AREA_TYPE_CYLINDER:
        out->x = area->u.cyl.x;
        out->y = area->u.cyl.floor;
        out->z = area->u.cyl.z;
        break;
    case AREA_TYPE_EYE:
        out->x = area->u.eye.xz;
        out->y = area->u.eye.floor;
        out->z = area->u.eye.z;
        break;
    default:
        pLog->warn(0, 0, AREA_TYPE_ERR, area->type);
        break;
    }
}

// A random point inside the area at floor height (bilinear on the quad; the centre for
// cylinder / eye) - enemy spawn points inside an area.
void AreaGetInsidePos(Vec* out, AreaData* area)
{
    switch (area->type) {
    case AREA_TYPE_XZ4: {
        Vec p0 = {area->u.xz4.p[0].x, area->u.xz4.floor, area->u.xz4.p[0].z};
        Vec p1 = {area->u.xz4.p[1].x, area->u.xz4.floor, area->u.xz4.p[1].z};
        Vec p2 = {area->u.xz4.p[2].x, area->u.xz4.floor, area->u.xz4.p[2].z};
        Vec p3 = {area->u.xz4.p[3].x, area->u.xz4.floor, area->u.xz4.p[3].z};
        Vec d01;
        Vec d32;
        Vec v0;
        Vec v3;
        Vec v;
        f32 s, t;

        PSVECSubtract(&p1, &p0, &d01);
        PSVECSubtract(&p2, &p3, &d32);
        s = fRand0_1();
        t = fRand0_1();
        PSVECScale(&d01, &v0, s);
        PSVECScale(&d32, &v3, s);
        PSVECAdd(&v3, &p3, &v3);
        PSVECSubtract(&v3, &p0, &v3);
        PSVECSubtract(&v3, &v0, &v);
        PSVECScale(&v, &v, t);
        PSVECAdd(&v, &v0, out);
        PSVECAdd(out, &p0, out);
        break;
    }
    case AREA_TYPE_CYLINDER:
        out->x = area->u.cyl.x;
        out->y = area->u.cyl.floor;
        out->z = area->u.cyl.z;
        break;
    case AREA_TYPE_EYE:
        out->x = area->u.eye.xz;
        out->y = area->u.eye.floor;
        out->z = area->u.eye.z;
        break;
    default:
        out->x = 0.0f;
        out->y = 0.0f;
        out->z = 0.0f;
        break;
    }
}

// Builds a default area of `type` around `pos`: a size x size square, a cylinder of radius
// size / 2, or an eye trigger with cone length size / 2 and a 60 degree opening.
void AreaDataInit(AreaData* area, Vec* pos, u8 type, f32 size, f32 height)
{
    area->Be_flag = 1;
    area->x2 = 0;
    area->type = type;

    switch (area->type) {
    case AREA_TYPE_XZ4: {
        AreaXZ4* a = &area->u.xz4;
        f32 hs = size * 0.5f;
        a->floor = pos->y;
        a->height = height;
        a->radius = hs;
        a->p[0].x = pos->x - hs;
        a->p[0].z = pos->z - hs;
        a->p[1].x = pos->x + hs;
        a->p[1].z = pos->z - hs;
        a->p[2].x = pos->x + hs;
        a->p[2].z = pos->z + hs;
        a->p[3].x = pos->x - hs;
        a->p[3].z = pos->z + hs;
        break;
    }
    case AREA_TYPE_CYLINDER: {
        AreaCylinder* a = &area->u.cyl;
        a->x = pos->x;
        a->z = pos->z;
        a->floor = pos->y;
        a->height = height;
        a->radius = size * 0.5f;
        a->x14 = 0.0f;
        a->x18 = 0.0f;
        a->x1C = 0.0f;
        a->x20 = 0.0f;
        a->x24 = 0.0f;
        a->x28 = 0.0f;
        break;
    }
    case AREA_TYPE_EYE: {
        AreaEyeTrigger* a = &area->u.eye;
        a->xz = pos->x;
        a->z = pos->z;
        a->floor = pos->y;
        a->height = height;
        a->radius = size * 0.5f;
        a->open = 0.0f;
        a->ang_x = 0.0f;
        a->ang_y = 0.0f;
        a->x1C = 0.0f;
        a->x24 = 0.0f;
        a->x28 = 0.0f;
        break;
    }
    default:
        pLog->warn(0, 0, AREA_TYPE_ERR, area->type);
        break;
    }
}

// Debug draw helper: sphere at `pos` (transformed by mtx when given).
void area_Draw_sphere(Vec pos, f32 r, u32 color, Mtx mtx)
{
    if (mtx) {
        PSMTXMultVec(mtx, &pos, &pos);
    }
    Draw_sphere(&pos, r, color, 0, 0);
}

// Debug draw helper: line between two points (transformed by mtx when given).
void area_Draw_line(Vec pos1, Vec pos2, u32 color, Mtx mtx)
{
    if (mtx) {
        RE4DC_XM_LOAD(mtx);
        RE4DC_XM_POINT(mtx, &pos1, &pos1);
        RE4DC_XM_POINT(mtx, &pos2, &pos2);
    }
    GXSetLineWidth(16, 0);
    Draw_line3d(&pos1, &pos2, color, 0);
    GXSetLineWidth(6, 0);
}

// Debug tool editor step: Y + X cycles the area type (rebuilding a 4000 unit default at the old
// centre), computes the camera-relative move axes and stick deltas (scaled by `rate`), then runs
// the type's editor and draws it in `color`.
void AreaDataEdit(AreaData* area, u32 color, int flag, Mtx mtx, f32 rate)
{
    Vec vx;
    Vec vy;
    Vec v;
    Vec center;
    f32 dx, dy;
    int mode;

    if ((Joy[0].on & JOY_Y) && (Joy[0].trg & JOY_X)) {
        switch (area->type) {
        case AREA_TYPE_XZ4:
            area->type = AREA_TYPE_CYLINDER;
            AreaGetCenterPos(&center, area);
            AreaDataInit(area, &center, area->type, 4000.0f, 4000.0f);
            break;
        case AREA_TYPE_CYLINDER:
            area->type = AREA_TYPE_EYE;
            AreaGetCenterPos(&center, area);
            AreaDataInit(area, &center, area->type, 4000.0f, 4000.0f);
            break;
        case AREA_TYPE_EYE:
            area->type = AREA_TYPE_XZ4;
            AreaGetCenterPos(&center, area);
            AreaDataInit(area, &center, area->type, 4000.0f, 4000.0f);
            break;
        default:
            pLog->warn(0, 0, AREA_TYPE_ERR, area->type);
            return;
        }
    }

    v.x = 1.0f;
    v.y = 0.0f;
    v.z = 0.0f;
    moveOnPlaneXZ(&v, &vx);
    v.x = 0.0f;
    v.y = 1.0f;
    v.z = 0.0f;
    moveOnPlaneXZ(&v, &vy);

    dx = (f32) Joy[0].stickX * 1.3f * rate;
    if (Joy[0].on & 0x10001) {
        dx -= 100.0f;
    }
    if (Joy[0].on & 0x20002) {
        dx += 100.0f;
    }
    dy = (f32) Joy[0].stickY * 1.3f * rate;
    if (Joy[0].on & 0x80008) {
        dy += 100.0f;
    }
    if (Joy[0].on & 0x40004) {
        dy -= 100.0f;
    }

    mode = 0;
    if (Joy[0].on & JOY_Y) {
        mode = 3;
    }
    if (Joy[0].on & JOY_A) {
        mode = 1;
    }
    if (Joy[0].on & JOY_X) {
        mode = 2;
    }
    if ((Joy[0].on & (JOY_Y | JOY_A)) == (JOY_Y | JOY_A)) {
        mode = 4;
    }

    {
        switch (area->type) {
        case AREA_TYPE_XZ4:
            area_xz4_Edit(&area->u.xz4, color, flag, mtx, mode, vx, vy, dx, dy, rate);
            break;
        case AREA_TYPE_CYLINDER:
            area_cylinder_Edit(&area->u.cyl, color, flag, mtx, mode, vx, vy, dx, dy, rate);
            break;
        case AREA_TYPE_EYE:
            area_eye_trigger_Edit(&area->u.eye, color, flag, mtx, mode, vx, vy, dx, dy, rate);
            break;
        default: {
            pLog->warn(0, 0, AREA_TYPE_ERR, area->type);
            Vec zero = {0.0f, 0.0f, 0.0f};
            AreaDataInit(area, &zero, AREA_TYPE_XZ4, 2000.0f, 1000.0f);
            break;
        }
        }
    }
}

// The split object's .sdata (sel/Rcnt below) is 8-byte aligned.
asm(".section .sdata,\"aw\"\n\t.balign 8\n\t.text");

// Quad editor: L / R select a point, A moves the selected point, X moves all four, Y moves the
// floor, Y + B changes the height, Z rotates the quad about its centre; then draws it.
void area_xz4_Edit(AreaXZ4* pXz4, u32 color, int flag, Mtx mtx, u32 mode, Vec vx, Vec vy, f32 dx, f32 dy, f32 rate)
{
    static u32 sel = 0;
    static f32 Rcnt = 0.0f;
    Vec p;
    Vec q;
    Vec t;
    f32 r;
    u32 i;
    f32* px;
    f32* pz;
    f32* d;

    Rcnt += rate * 3.0f;
    if (Rcnt > rate * 90.0f) {
        Rcnt = rate * 45.0f;
    }

    switch (mode) {
    case 0:
        if (Joy[0].rep & 0x10001) {
            sel--;
            Rcnt = rate * 45.0f;
        }
        if (sel > 3) {
            sel = 3;
        }
        if (Joy[0].rep & 0x20002) {
            sel++;
            Rcnt = rate * 45.0f;
        }
        if (sel > 3) {
            sel = 0;
        }
        break;
    case 1:
        // The point is written back through plain float pointers (`*d = v`, no member access): such
        // a store is assumed to alias the static `sel`, which is reloaded before the second store.
        px = &pXz4->p[0].x;
        pz = &pXz4->p[0].z;
        p.x = pXz4->p[sel].x;
        p.y = pXz4->floor;
        p.z = pXz4->p[sel].z;
        PSVECScale(&vx, &t, dx);
        PSVECAdd(&t, &p, &p);
        PSVECScale(&vy, &t, dy);
        PSVECAdd(&t, &p, &p);
        d = px + sel * 2;
        *d = p.x;
        d = pz + sel * 2;
        *d = p.z;
        break;
    case 2:
        for (i = 0; i < 4; i++) {
            p.x = pXz4->p[i].x;
            p.y = pXz4->floor;
            p.z = pXz4->p[i].z;
            PSVECScale(&vx, &t, dx);
            PSVECAdd(&t, &p, &p);
            PSVECScale(&vy, &t, dy);
            PSVECAdd(&t, &p, &p);
            pXz4->p[i].x = p.x;
            pXz4->p[i].z = p.z;
        }
        break;
    case 3:
        pXz4->height += dy;
        break;
    case 4:
        pXz4->floor += dy;
        break;
    }

    r = rate * 100.0f;
    switch (mode) {
    case 0:
        p.x = pXz4->p[sel].x;
        p.y = pXz4->floor;
        p.z = pXz4->p[sel].z;
        area_Draw_sphere(p, Rcnt, 0x00FF00FE, mtx);
        q.x = pXz4->p[sel].x;
        q.y = pXz4->floor + pXz4->height;
        q.z = pXz4->p[sel].z;
        area_Draw_line(p, q, 0xFF00FF00, mtx);
        break;
    case 1:
        p.x = pXz4->p[sel].x;
        p.y = pXz4->floor;
        p.z = pXz4->p[sel].z;
        area_Draw_sphere(p, r, 0xFFFF00FE, mtx);
        break;
    case 2:
        for (i = 0; i < 4; i++) {
            p.x = pXz4->p[i].x;
            p.y = pXz4->floor;
            p.z = pXz4->p[i].z;
            area_Draw_sphere(p, r, 0xFFFF00FE, mtx);
        }
        break;
    case 3:
        for (i = 0; i < 4; i++) {
            p.x = pXz4->p[i].x;
            p.y = pXz4->floor + pXz4->height;
            p.z = pXz4->p[i].z;
            area_Draw_sphere(p, r, 0xFFFF00FE, mtx);
        }
        break;
    case 4:
        for (i = 0; i < 4; i++) {
            p.x = pXz4->p[i].x;
            p.y = pXz4->floor;
            p.z = pXz4->p[i].z;
            area_Draw_sphere(p, r, 0xFFFF00FE, mtx);
            p.y = pXz4->floor + pXz4->height;
            area_Draw_sphere(p, r, 0xFFFF00FE, mtx);
        }
        break;
    }

    area_xz4_Disp(pXz4, color, flag, mtx);
}

// Cylinder editor: A / X move the centre, B changes the radius, Y the floor, Y + B the height;
// then draws it.
void area_cylinder_Edit(AreaCylinder* pCld, u32 color, int flag, Mtx mtx, u32 mode, Vec vx, Vec vy, f32 dx, f32 dy, f32 rate)
{
    Vec p;
    Vec t;
    Vec q;
    Vec c;
    f32 r;
    u32 n = 0;
    u32 start = 0;
    u32 col = 0;
    u32 div = 12;
    u32 j, k;
    f32 ang;

    switch (mode) {
    case 0:
        break;
    case 1:
        pCld->radius += dx;
        if (pCld->radius < 10.0f) {
            pCld->radius = 10.0f;
        }
        break;
    case 2:
        p.x = pCld->x;
        p.y = pCld->floor;
        p.z = pCld->z;
        PSVECScale(&vx, &t, dx);
        PSVECAdd(&t, &p, &p);
        PSVECScale(&vy, &t, dy);
        PSVECAdd(&t, &p, &p);
        pCld->x = p.x;
        pCld->z = p.z;
        break;
    case 3:
        pCld->height += dy;
        break;
    case 4:
        pCld->floor += dy;
        break;
    }

    r = rate * 100.0f;
    switch (mode) {
    case 0:
        start = 0;
        n = 1;
        col = 0x00FF00FE;
        break;
    case 1:
        start = 0;
        n = 1;
        col = 0xFFFF00FE;
        div = 1;
        c.x = pCld->x;
        c.y = pCld->floor;
        c.z = pCld->z;
        area_Draw_sphere(c, r, 0xFFFF00FE, mtx);
        break;
    case 2:
        start = 0;
        n = 1;
        col = 0xFFFF00FE;
        break;
    case 3:
        start = 1;
        n = 2;
        col = 0xFFFF00FE;
        break;
    case 4:
        start = 0;
        n = 2;
        col = 0xFFFF00FE;
        break;
    }

    for (j = start; j < n; j++) {
        if (j == 0) {
            c.y = pCld->floor;
        } else {
            c.y = pCld->floor + pCld->height;
        }
        c.x = pCld->x;
        c.z = pCld->z;
        ang = 0.0f;
        for (k = 0; k < div; k++) {
            q.x = pCld->radius * sinf(ang);
            q.y = 0.0f;
            q.z = pCld->radius * cosf(ang);
            PSVECAdd(&c, &q, &p);
            area_Draw_sphere(p, r, col, mtx);
            ang += 6.28f / (f32) (div - 1);
        }
    }

    area_cylinder_Disp(pCld, color, flag, mtx);
}

// Eye trigger editor: A / X move the point, B changes the cone length, Y the floor / height, Z
// turns the view direction and R the opening angle; then draws it.
void area_eye_trigger_Edit(AreaEyeTrigger* pEtg, u32 color, int flag, Mtx mtx, u32 mode, Vec vx, Vec vy, f32 dx, f32 dy, f32 rate)
{
    Vec p;
    Vec t;
    Vec q;
    Vec c;
    f32 r;
    u32 n = 0;
    u32 col = 0;
    u32 div = 12;
    u32 j, k;
    f32 ang;

    switch (mode) {
    case 0:
        break;
    case 1:
        pEtg->radius += dy * 0.05f;
        if (pEtg->radius < 0.0f) {
            pEtg->radius = 0.0f;
        }
        pEtg->open += dx * 0.0005f;
        if (pEtg->open < 0.0f) {
            pEtg->open = 0.0f;
        }
        if (pEtg->open > 6.28f) {
            pEtg->open = 6.28f;
        }
        break;
    case 2:
        p.x = pEtg->xz;
        p.y = pEtg->floor;
        p.z = pEtg->z;
        PSVECScale(&vx, &t, dx);
        PSVECAdd(&t, &p, &p);
        PSVECScale(&vy, &t, dy);
        PSVECAdd(&t, &p, &p);
        pEtg->xz = p.x;
        pEtg->z = p.z;
        break;
    case 3:
        pEtg->floor += dy;
        break;
    case 4:
        pEtg->ang_x += dy * 0.0005f;
        pEtg->ang_y += dx * 0.0005f;
        pEtg->ang_x = LIMIT_ANGLE(pEtg->ang_x);
        pEtg->ang_y = LIMIT_ANGLE(pEtg->ang_y);
        break;
    }

    r = rate * 80.0f;
    switch (mode) {
    case 0:
        n = 1;
        col = 0x00FF00FE;
        break;
    case 1:
        n = 1;
        col = 0xFFFF00FE;
        div = 1;
        c.x = pEtg->xz;
        c.y = pEtg->floor;
        c.z = pEtg->z;
        area_Draw_sphere(c, r, 0xFFFF00FE, mtx);
        break;
    case 2:
        n = 1;
        col = 0xFFFF00FE;
        break;
    case 3:
        n = 2;
        col = 0xFFFF00FE;
        break;
    case 4:
        n = 0;
        col = 0xFFFF00FE;
        break;
    }

    for (j = 0; j < n; j++) {
        if (j == 0) {
            c.y = pEtg->floor;
        } else {
            c.y = pEtg->floor + pEtg->height;
        }
        c.x = pEtg->xz;
        c.z = pEtg->z;
        ang = 0.0f;
        for (k = 0; k < div; k++) {
            q.x = pEtg->radius * sinf(ang);
            q.y = 0.0f;
            q.z = pEtg->radius * cosf(ang);
            PSVECAdd(&c, &q, &p);
            area_Draw_sphere(p, r, col, mtx);
            ang += 6.28f / (f32) (div - 1);
        }
    }

    area_eye_trigger_Disp(pEtg, color, flag, mtx);
}

// Debug wireframe of the area in `color` (flag: filled / outline variant) by type.
void AreaDataDisp(AreaData* area, u32 color, int flag, Mtx mtx)
{
    switch (area->type) {
    case AREA_TYPE_XZ4:
        area_xz4_Disp(&area->u.xz4, color, flag, mtx);
        break;
    case AREA_TYPE_CYLINDER:
        area_cylinder_Disp(&area->u.cyl, color, flag, mtx);
        break;
    case AREA_TYPE_EYE:
        area_eye_trigger_Disp(&area->u.eye, color, flag, mtx);
        break;
    default: {
        pLog->warn(0, 0, AREA_TYPE_ERR, area->type);
        Vec zero = {0.0f, 0.0f, 0.0f};
        AreaDataInit(area, &zero, AREA_TYPE_XZ4, 2000.0f, 1000.0f);
        break;
    }
    }
}

// Draws the quad prism: the four side polygons from floor to floor + height and the edges.
void area_xz4_Disp(AreaXZ4* pXz4, u32 color, int flag, Mtx mtx)
{
    Vec v[5];
    Vec w[5];
    u32 i;

    for (i = 0; i < 4; i++) {
        v[i].x = pXz4->p[i].x;
        v[i].y = pXz4->floor;
        v[i].z = pXz4->p[i].z;
    }
    v[4].x = pXz4->p[0].x;
    v[4].y = pXz4->floor;
    v[4].z = pXz4->p[0].z;
    for (i = 0; i < 5; i++) {
        w[i] = v[i];
        w[i].y += pXz4->height;
    }
    if (mtx) {
        for (i = 0; i < 5; i++) {
            RE4DC_XM_LOAD(mtx);
            RE4DC_XM_POINT(mtx, &v[i], &v[i]);
            RE4DC_XM_POINT(mtx, &w[i], &w[i]);
        }
    }
    Draw_poly(v, color, 0);
    Draw_poly(&v[2], color, 0);
    if (flag & 1) {
        Vec tri[3];
        u32 col = (color & 0x00FFFFFF) + ((color & 0xFF000000) >> 2);
        tri[0] = v[0];
        tri[1] = v[1];
        tri[2] = w[1];
        Draw_poly(tri, col, 0);
        tri[0] = w[0];
        tri[1] = w[1];
        tri[2] = v[0];
        Draw_poly(tri, col, 0);
        tri[0] = v[1];
        tri[1] = v[2];
        tri[2] = w[2];
        Draw_poly(tri, col, 0);
        tri[0] = w[1];
        tri[1] = w[2];
        tri[2] = v[1];
        Draw_poly(tri, col, 0);
        tri[0] = v[2];
        tri[1] = v[3];
        tri[2] = w[3];
        Draw_poly(tri, col, 0);
        tri[0] = w[2];
        tri[1] = w[3];
        tri[2] = v[2];
        Draw_poly(tri, col, 0);
        tri[0] = v[3];
        tri[1] = v[0];
        tri[2] = w[0];
        Draw_poly(tri, col, 0);
        tri[0] = w[3];
        tri[1] = w[0];
        tri[2] = v[3];
        Draw_poly(tri, col, 0);
    }
    for (i = 0; i < 4; i++) {
        Draw_line3d(&v[i], &v[i + 1], color, 0);
        Draw_line3d(&w[i], &w[i + 1], color, 0);
        Draw_line3d(&v[i], &w[i], color, 0);
    }
}

// Draws the cylinder as a 16-segment ring at the floor and the top with vertical edges.
void area_cylinder_Disp(AreaCylinder* pCld, u32 color, int flag, Mtx mtx)
{
    Vec tri2[3];
    Vec tri[3];
    Vec q;
    Vec c;
    Vec p;
    Vec prev;
    u32 j, k;
    u32 div = 16;
    f32 ang;
    u32 col;

    for (j = 0; j < 2; j++) {
        if (j == 0) {
            c.y = pCld->floor;
        } else {
            c.y = pCld->floor + pCld->height;
        }
        c.x = pCld->x;
        c.z = pCld->z;
        if (mtx) {
            PSMTXMultVec(mtx, &c, &c);
        }
        ang = 0.0f;
        for (k = 0; k < div; k++) {
            q.x = pCld->radius * sinf(ang);
            q.y = 0.0f;
            q.z = pCld->radius * cosf(ang);
            PSVECAdd(&c, &q, &p);
            if (k != 0) {
                Draw_line3d(&prev, &p, color, 0);
            }
            if (j == 0) {
                q.x = 0.0f;
                q.y = pCld->height;
                q.z = 0.0f;
                PSVECAdd(&p, &q, &q);
                Draw_line3d(&p, &q, color, 0);
                if (k != 0) {
                    tri[0] = p;
                    tri[1] = prev;
                    tri[2] = c;
                    Draw_poly(tri, color, 1);
                    if (flag & 1) {
                        col = color & 0x00FFFFFF;
                        col += (color & 0xFF000000) >> 2;
                        tri2[0] = p;
                        tri2[1] = prev;
                        tri2[2] = prev;
                        tri2[2].y += pCld->height;
                        Draw_poly(tri2, col, 0);
                        tri2[0] = p;
                        tri2[1] = prev;
                        tri2[2] = p;
                        tri2[0].y += pCld->height;
                        tri2[1].y += pCld->height;
                        Draw_poly(tri2, col, 0);
                    }
                }
            }
            prev = p;
            ang += 6.2831855f / (f32) (div - 1);
        }
    }
}

// Draws the eye trigger: its point and the view cone (Draw_corn2) of its length / opening.
void area_eye_trigger_Disp(AreaEyeTrigger* pEtg, u32 color, int flag, Mtx mtx)
{
    Vec c;

    c.x = pEtg->xz;
    c.y = pEtg->floor;
    c.z = pEtg->z;
    area_Draw_sphere(c, 10.0f, color, mtx);
    area_Draw_sphere(c, pEtg->radius, color, mtx);
    if (pEtg->open != 0.0f) {
        Mtx m;
        Vec dir;
        Vec rot;
        dir.x = 0.0f;
        dir.y = 0.0f;
        dir.z = 1.0f;
        rot.x = pEtg->ang_x;
        rot.y = pEtg->ang_y;
        rot.z = 0.0f;
        RotMatrix(m, &rot);
        PSMTXMultVecSR(m, &dir, &dir);
        Draw_corn2(&c, &dir, 1000.0f, pEtg->open * 360.0f / 6.28f, color);
    }
}

// Debug text: the area's numeric parameters (points / centre, radius, floor, height, angles)
// printed from screen position x / y.
void AreaDataInfoDisp(AreaData* area, int x, s16 y)
{
    Vec pos;
    Vec scr;

    switch (area->type) {
    case AREA_TYPE_XZ4: {
        AreaXZ4* a = &area->u.xz4;
        eprintf(x, y, 0, 0, "P0[%6.0f,%6.0f]", a->p[0].x, a->p[0].z);
        y += 16;
        eprintf(x, y, 0, 0, "P1[%6.0f,%6.0f]", a->p[1].x, a->p[1].z);
        y += 16;
        eprintf(x, y, 0, 0, "P2[%6.0f,%6.0f]", a->p[2].x, a->p[2].z);
        y += 16;
        eprintf(x, y, 0, 0, "P3[%6.0f,%6.0f]", a->p[3].x, a->p[3].z);
        y += 16;
        eprintf(x, y, 0, 0, "PY[%6.0f]", a->floor);
        y += 16;
        eprintf(x, y, 0, 0, "HEIGHT[%6.0f]", a->height);

        pos.x = a->p[0].x;
        pos.y = a->floor;
        pos.z = a->p[0].z;
        GetScreenPos(pos, &scr);
        eprintf2(6, 12, (int) scr.x + 8, (int) scr.y + 16, 0, 0, "P0");
        pos.x = a->p[1].x;
        pos.y = a->floor;
        pos.z = a->p[1].z;
        GetScreenPos(pos, &scr);
        eprintf2(6, 12, (int) scr.x + 8, (int) scr.y + 16, 0, 0, "P1");
        pos.x = a->p[2].x;
        pos.y = a->floor;
        pos.z = a->p[2].z;
        GetScreenPos(pos, &scr);
        eprintf2(6, 12, (int) scr.x + 8, (int) scr.y + 16, 0, 0, "P2");
        pos.x = a->p[3].x;
        pos.y = a->floor;
        pos.z = a->p[3].z;
        GetScreenPos(pos, &scr);
        eprintf2(6, 12, (int) scr.x + 8, (int) scr.y + 16, 0, 0, "P3");
        break;
    }
    case AREA_TYPE_CYLINDER: {
        AreaCylinder* a = &area->u.cyl;
        eprintf(x, y, 0, 0, "P0[%6.0f,%6.0f,%6.0f]", a->x, a->floor, a->z);
        y += 16;
        eprintf(x, y, 0, 0, "HEIGHT[%6.0f]", a->height);
        y += 16;
        eprintf(x, y, 0, 0, "RADIUS[%6.0f]", a->radius);

        pos.x = a->x;
        pos.y = a->floor;
        pos.z = a->z;
        GetScreenPos(pos, &scr);
        eprintf2(6, 12, (int) scr.x + 8, (int) scr.y + 16, 0, 0, "P0");
        break;
    }
    case AREA_TYPE_EYE: {
        AreaEyeTrigger* a = &area->u.eye;
        eprintf(x, y, 0, 0, "P0[%6.0f,%6.0f,%6.0f]", a->xz, a->floor, a->z);
        y += 16;
        eprintf(x, y, 0, 0, "RADIUS[%6.0f]", a->radius);
        y += 16;
        if (a->open == 0.0f) {
            eprintf(x, y, 0, 0, "OPEN ANGLE[360]");
        } else {
            eprintf(x, y, 0, 0, "OPEN ANGLE[%3.0f]", a->open * 57.295776f);
        }
        y += 16;
        eprintf(x, y, 0, 0, "ANGLE_X[%3.0f]", a->ang_x * 57.295776f);
        y += 16;
        eprintf(x, y, 0, 0, "ANGLE_Y[%3.0f]", a->ang_y * 57.295776f);

        pos.x = a->xz;
        pos.y = a->floor;
        pos.z = a->z;
        GetScreenPos(pos, &scr);
        eprintf2(6, 12, (int) scr.x + 8, (int) scr.y + 16, 0, 0, "P0");
        break;
    }
    }
}

#define HELP_LINE(cond, str)          \
    if (cond) {                       \
        eprintf(x, y, 6, 0, str);     \
    } else {                          \
        eprintf(x, y, 5, 0, str);     \
    }

// Debug text: the pad help of the current editor, highlighting the buttons being held.
void AreaDataHelpDisp(AreaData* area, int x, s16 y)
{
    switch (area->type) {
    case AREA_TYPE_XZ4:
        HELP_LINE(Joy[0].on & 0x30003, " LR: point select");
        y += 16;
        HELP_LINE((Joy[0].on & (JOY_Y | JOY_A)) == JOY_A, "  A: 1 point move");
        y += 16;
        HELP_LINE(Joy[0].on & JOY_X, "  X: all point move");
        y += 16;
        HELP_LINE((Joy[0].on & (JOY_Y | JOY_A)) == JOY_Y, "  Y: height move");
        y += 16;
        HELP_LINE((Joy[0].on & (JOY_Y | JOY_A)) == (JOY_Y | JOY_A), "Y+A: Y pos move");
        y += 16;
        break;
    case AREA_TYPE_CYLINDER:
        HELP_LINE(Joy[0].on & JOY_X, "  X: pos move");
        y += 16;
        HELP_LINE((Joy[0].on & (JOY_Y | JOY_A)) == JOY_A, "  A: radius move");
        y += 16;
        HELP_LINE((Joy[0].on & (JOY_Y | JOY_A)) == JOY_Y, "  Y: height move");
        y += 16;
        HELP_LINE((Joy[0].on & (JOY_Y | JOY_A)) == (JOY_Y | JOY_A), "Y+A: Y pos move");
        y += 16;
        break;
    case AREA_TYPE_EYE:
        HELP_LINE(Joy[0].on & JOY_X, "  X: pos move");
        y += 16;
        HELP_LINE(Joy[0].on & JOY_Y, "  Y: Y pos move");
        y += 16;
        if ((Joy[0].on & (JOY_Y | JOY_A)) == JOY_A) {
            eprintf(x, y, 6, 0, "  A: open angle");
            y += 16;
            eprintf(x, y, 6, 0, "   : radius move");
        } else {
            eprintf(x, y, 5, 0, "  A: open angle");
            y += 16;
            eprintf(x, y, 5, 0, "   : radius move");
        }
        y += 16;
        HELP_LINE((Joy[0].on & (JOY_Y | JOY_A)) == (JOY_Y | JOY_A), "Y+A: front angle");
        y += 16;
        break;
    }
}
