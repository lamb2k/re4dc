// game/sub2: small vector / angle helpers used everywhere: yaw between points (GetXZAngle*), the
// clamped turning steps (Muku / Muku2 / Muku3), front cones (Front_check), distances, rotations,
// screen projection (GetScreenPos / Get3DPosFrom2D), line-sphere tests and the parabola / stop
// distance helpers of the throwing and movement code. (D:/Bio4/Prog/sub2.cpp)
#include "types.h"
#include "re4dc_xm.h" // GAME_SH4ZAM_LOGIC (lane sh4zam-direct)
#include "global.h"
#include "atari.h"
#include "model.h"
#include "player.h"
#include "camera.h"
#include "math_sub.h"
#include "gx.h"
#include "db_log.h"

extern "C" {
double atan2(double y, double x);
void GXGetProjectionv(f32* p);
void GXGetViewportv(f32* vp);
void GXProject(f32 x, f32 y, f32 z, const Mtx mtx, const f32* pm, const f32* vp, f32* sx, f32* sy, f32* sz);
}

#define PI2 6.2831855f

#line 30 "D:/Bio4/Prog/sub2.cpp"

// 1 when the XZ point `p` lies inside the convex quad (4 corners in order).
int HitCheckPoint4(Vec* p, Vec* quad)
{
    f32 px = p->x - quad[0].x;
    f32 pz = p->z - quad[0].z;
    f32 ax = quad[1].x - quad[0].x;
    f32 az = quad[1].z - quad[0].z;
    f32 bx = quad[3].x - quad[0].x;
    f32 bz = quad[3].z - quad[0].z;
    f32 cx;
    f32 cz;

    if (ax * pz > az * px || bx * pz < bz * px) {
        return 0;
    }
    cx = quad[2].x - quad[0].x;
    cz = quad[2].z - quad[0].z;
    px -= cx;
    pz -= cz;
    ax -= cx;
    az -= cz;
    bx -= cx;
    bz -= cz;
    if (ax * pz < az * px || bx * pz > bz * px) {
        return 0;
    }
    return 1;
}

// Yaw (radians, -PI..PI) from `from` to `to` on the XZ plane (0 = +Z).
f32 GetXZAngle(Vec* from, Vec* to)
{
    return LIMIT_ANGLE(atan2f(to->x - from->x, to->z - from->z));
}

// Angle from `from` to `to` in the XY plane.
f32 GetXYAngle(Vec* from, Vec* to)
{
    f32 dx = to->x - from->x;
    f32 dy = to->y - from->y;
    return LIMIT_ANGLE(atan2f(dy, dx));
}

// Yaw to `to` relative to a facing `ang` (0 = straight ahead, wrapped to -PI..PI).
f32 GetXZAngleLocal(Vec* from, Vec* to, f32 ang)
{
    return LIMIT_ANGLE(GetXZAngle(from, to) - ang);
}

// Squared distance between two points.
f32 GetDistance(Vec* v0, Vec* v1)
{
    f32 x = v1->x - v0->x;
    f32 y = v1->y - v0->y;
    f32 z = v1->z - v0->z;
    return x * x + y * y + z * z;
}

// Squared distance between two points.
f32 GetDistance(Vec& v0, Vec& v1)
{
    f32 x = v1.x - v0.x;
    f32 y = v1.y - v0.y;
    f32 z = v1.z - v0.z;
    return x * x + y * y + z * z;
}

// Squared XZ distance.
f32 GetDistanceXZ(Vec* v0, Vec* v1)
{
    f32 x = v1->x - v0->x;
    f32 z = v1->z - v0->z;
    return x * x + z * z;
}

// Turn amount toward `target` from facing `ang`: the signed yaw difference clamped to +-limit
// (the usual `ang.y += Muku(...)` turning step).
f32 Muku(Vec* pos, Vec* target, f32 ang, f32 limit)
{
    f32 d = LIMIT_ANGLE(GetXZAngle(pos, target) - ang);
    f32 ret;

    if (d > 0.0f) {
        if (d < limit) {
            limit = d;
        }
    } else {
        if (d > -limit) {
            limit = -d;
        }
    }
    ret = limit;
    if (!(d >= 0.0f)) {
        ret = -ret;
    }
    return ret;
}

// Turn amount from angle `ang` to `target` the short way round, clamped to +-limit.
f32 Muku2(f32 ang, f32 target, f32 limit)
{
    f32 d = target - ang;

    if (d < 0.0f) {
        d += PI2;
    }
    if (d < PI) {
        if (limit > d) {
            limit = d;
        }
    } else {
        d -= PI2;
        if (limit > -d) {
            limit = d;
        } else {
            limit = -limit;
        }
    }
    return limit;
}

// Turn amount from `ang` toward the direction vector `dir`, clamped to +-limit.
f32 Muku3(Vec* dir, f32 ang, f32 limit)
{
    return Muku2(ang, (f32) atan2(dir->x, dir->z), limit);
}

// Dead-stripped in the original (STRIP_UNUSED): only the VECNormalize strings and the 0.0f pools
// survive in .rodata, at this position.
static void sub2_dead1(Vec* v)
{
    VECNormalize(v, v);
}

// Dead-stripped: sign test.
static int sub2_dead2(f32 x)
{
    if (x > 0.0f) {
        return 1;
    }
    return 0;
}

// 1 when `b` is within +-ang of `a`'s facing.
int Front_check(cModel* a, cModel* b, f32 ang)
{
    f32 d = GetXZAngleLocal(&a->pos, &b->pos, a->ang.y);
    int ret = 0;
    if (!(d < -ang) && !(d > ang)) {
        ret = 1;
    }
    return ret;
}

// 1 when point `b` is within +-ang of `a`'s facing.
int Front_check(cModel* a, Vec* b, f32 ang)
{
    f32 d = GetXZAngleLocal(&a->pos, b, a->ang.y);
    int ret = 0;
    if (!(d < -ang) && !(d > ang)) {
        ret = 1;
    }
    return ret;
}

// 1 when `b` is within +-ang of the facing `rot` at `a`.
int Front_check(Vec* a, Vec* b, f32 rot, f32 ang)
{
    f32 d = GetXZAngleLocal(a, b, rot);
    int ret = 0;
    if (!(d < -ang) && !(d > ang)) {
        ret = 1;
    }
    return ret;
}

// Moves `m` by `speed` given in its own (rotated) frame.
void AddSpeed(cModel* m, const Vec* speed)
{
    Vec v;
    Mtx mtx;

    low_RotMatrix(mtx, &m->ang);
    PSMTXMultVec(mtx, speed, &v);
    m->pos.x += v.x;
    m->pos.y += v.y;
    m->pos.z += v.z;
}

// Length of a vector.
f32 RootSumSquare3(Vec* v)
{
    return SQRTF(v->x * v->x + v->y * v->y + v->z * v->z);
}

// Distance between two points.
f32 GetDistance3(Vec* v0, Vec* v1)
{
    Vec d;

    d.x = v1->x - v0->x;
    d.y = v1->y - v0->y;
    d.z = v1->z - v0->z;
    return RootSumSquare3(&d);
}

// Rotates `src` by the Euler angles `rot` (RotMatrix order).
#if defined(RE4DC_ROTVEC_MEMO) && RE4DC_ROTVEC_MEMO
// GAME_ROTVEC_MEMO (game30.mk, square plan; exact): RotVector is a pure function of its input bits
// (low_RotMatrix reads the angles, PSMTXMultVec the src components, neither has a side effect), so a
// hit returns exactly the bits a call computes. cAtariInfo::getPos calls it for every candidate body
// on each of EmAtCheck's ~46 calls per tick, with offsets and angles that rarely change in between.
// Only yaw-only angles are memoised: low_RotMatrix treats rot.x == 0.0f and rot.z == 0.0f (either
// sign) as sin 0 / cos 1, so the matrix then depends on the rot.y bits alone and the key is four
// words. An entry (key, result, valid) is one 32-byte cache line; other angles compute as before.
// =2 (check build): every hit is computed again and compared bit for bit ("RVM" log line).
#ifndef RE4DC_RVM_BITS
#define RE4DC_RVM_BITS 8
#endif
namespace {
typedef u32 __attribute__((may_alias)) RvmWord;
struct RvmEntry {
    u32 k[4];
    u32 r[3];
    u32 valid;
};
RvmEntry rvm[1 << RE4DC_RVM_BITS] __attribute__((aligned(32)));
#if RE4DC_ROTVEC_MEMO == 2
u32 rvmCalls, rvmHits, rvmMis, rvmGeneral;
#endif
}
#if RE4DC_ROTVEC_MEMO == 2
extern "C" void re4dc_log(const char* fmt, ...);
#endif
void RotVector(Vec* src, Vec* rot, Vec* dst)
{
    Mtx mtx;
#if RE4DC_ROTVEC_MEMO == 2
    if ((++rvmCalls & 0xFFFF) == 0) {
        re4dc_log("RVM calls=%u hits=%u mismatch=%u general=%u bits=%u\n", rvmCalls, rvmHits, rvmMis,
                  rvmGeneral, RE4DC_RVM_BITS);
    }
#endif
    if (rot->x != 0.0f || rot->z != 0.0f) {
#if RE4DC_ROTVEC_MEMO == 2
        rvmGeneral++;
#endif
        low_RotMatrix(mtx, rot);
        PSMTXMultVec(mtx, src, dst);
        return;
    }
    const RvmWord* s = (const RvmWord*) src;
    const u32 k0 = s[0], k1 = s[1], k2 = s[2], k3 = ((const RvmWord*) rot)[1];
    const u32 h = ((k0 ^ (k1 << 1) ^ (k2 << 2)) * 0x9E3779B1u) ^ (k3 * 0x85EBCA6Bu);
    RvmEntry& e = rvm[h >> (32 - RE4DC_RVM_BITS)];
    RvmWord* d = (RvmWord*) dst;
    if (e.k[0] == k0 && e.k[1] == k1 && e.k[2] == k2 && e.k[3] == k3 && e.valid) {
#if RE4DC_ROTVEC_MEMO == 2
        Vec ref;
        low_RotMatrix(mtx, rot);
        PSMTXMultVec(mtx, src, &ref);
        const RvmWord* q = (const RvmWord*) &ref;
        rvmHits++;
        if (q[0] != e.r[0] || q[1] != e.r[1] || q[2] != e.r[2]) {
            rvmMis++;
        }
#endif
        const u32 r0 = e.r[0], r1 = e.r[1], r2 = e.r[2];
        d[0] = r0;
        d[1] = r1;
        d[2] = r2;
        return;
    }
    Vec out;

    low_RotMatrix(mtx, rot);
    PSMTXMultVec(mtx, src, &out);
    const RvmWord* o = (const RvmWord*) &out;
    const u32 r0 = o[0], r1 = o[1], r2 = o[2];
    e.k[0] = k0; e.k[1] = k1; e.k[2] = k2; e.k[3] = k3;
    e.r[0] = r0; e.r[1] = r1; e.r[2] = r2;
    e.valid = 1;
    d[0] = r0;
    d[1] = r1;
    d[2] = r2;
}
#else
void RotVector(Vec* src, Vec* rot, Vec* dst)
{
    Mtx mtx;

    low_RotMatrix(mtx, rot);
    PSMTXMultVec(mtx, src, dst);
}
#endif

// Transforms the 8 corners of a box by rotation `rot` and translation `pos`.
void BoxWorldCalc(Vec* src, Vec* dst, Vec* pos, Vec* rot)
{
    Mtx mtx;
    int i;

    RotMatrix(mtx, rot);
    TransMatrix(mtx, pos);
    RE4DC_XM_LOAD(mtx); // one XMTRX load for the 8 corners (GAME_SH4ZAM_LOGIC)
    for (i = 0; i < 8; i++) {
        RE4DC_XM_POINT(mtx, &src[i], &dst[i]);
    }
}

// Projects a world point to screen coordinates with the current camera; returns 1 when it is in
// front of the camera.
int GetScreenPos(Vec* pos, Vec* scr)
{
    f32 proj[7];
    f32 vp[6];
    Vec cam;

    CameraCurrentProjection();
    GXGetProjectionv(proj);
    GXGetViewportv(vp);
    GXProject(pos->x, pos->y, pos->z, pG->Cam.v_mat, proj, vp, &scr->x, &scr->y, &scr->z);
    PSMTXMultVec(pG->Cam.v_mat, pos, &cam);
    return cam.z < -0.0f;
}

// World point under screen position (sx, sy): the camera ray meets height `y` (y == 1e8: the
// scroll collision hit, else the player's height when none), or the far point 20000 away.
void Get3DPosFrom2D(Vec* out, f32 sx, f32 sy, f32 y)
{
    Camera* cam = &pG->Cam;
    Vec far;
    Vec dir;
    Vec hit;

    CamPos2ScrnVec(&dir, sx, sy);
#line 518 "D:/Bio4/Prog/sub2.cpp"
    VECNormalize(&dir, &dir);
    PSVECScale(&dir, &dir, 20000.0f);
    PSVECAdd(&cam->param.pos, &dir, &far);
    if (y == 100000000.0f) {
        if (SatMgr.hitCheck(&cam->param.pos, &far, &hit, 0, 0x40, 0)) {
            *out = hit;
            return;
        }
        y = pPL->pos.y;
    }
    {
        f32 t = (y - cam->param.pos.y) / (far.y - cam->param.pos.y);
        if (t > 0.0f) {
            PSVECScale(&dir, &dir, t);
            PSVECAdd(&cam->param.pos, &dir, out);
        } else {
            *out = far;
        }
    }
}

// Dead-stripped in the original (pools: PI/2, -1, 1, 127 and -1, 1, 0.5, 0).
static s8 sub2_dead3(f32 ang)
{
    f32 v = ang / 1.5707964f;
    if (v < -1.0f) {
        v = -1.0f;
    }
    if (v > 1.0f) {
        v = 1.0f;
    }
    return (s8) (v * 127.0f);
}

// Dead-stripped: clamp to -1..1 and halve.
static f32 sub2_dead4(f32 x)
{
    if (x < -1.0f) {
        x = -1.0f;
    }
    if (x > 1.0f) {
        x = 1.0f;
    }
    x *= 0.5f;
    if (x == 0.0f) {
        return 0.0f;
    }
    return x;
}

// Linear interpolation: out = pos1 * (1 - t) + pos2 * t.
void PosToPos(Vec* pos1, Vec* pos2, Vec* out, f32 t)
{
    Vec ta;
    Vec tb;

    PSVECScale(pos1, &ta, 1.0f - t);
    PSVECScale(pos2, &tb, t);
    PSVECAdd(&ta, &tb, out);
}

// A 2D stick vector (x right, y forward) turned into a world XZ direction relative to the camera
// yaw.
void VecToCamVec(Vec* v, Vec* out)
{
    Mtx mtx;
    Vec t;
    f32 ang;

    t.x = 0.0f;
    t.y = 0.0f;
    t.z = 1.0f;
    PSMTXMultVecSR(pG->Cam.mat, &t, &t);
    ang = atan2f(t.x, t.z);
    t.x = v->x;
    t.y = 0.0f;
    t.z = -v->y;
    PSMTXRotRad(mtx, 'y', ang);
    PSMTXMultVecSR(mtx, &t, out);
}

// Does the segment a-b enter the sphere (c, r)? Returns 1 with the entry point in `out` (a itself
// when it starts inside).
int LineSphereCrossCk(Vec* a, Vec* b, Vec* c, Vec* out, f32 r)
{
    Vec ab;
    Vec ac;
    Vec p;
    Vec q;
    Vec d1;
    Vec d2;
    f32 r2 = r * r;
    f32 dist2;
    f32 len2;
    f32 t;
    f32 h;

    dist2 = (a->x - c->x) * (a->x - c->x) + (a->y - c->y) * (a->y - c->y) + (a->z - c->z) * (a->z - c->z);
    if (dist2 < r2) {
        if (out) {
            *out = *a;
        }
        return 1;
    }
    len2 = (a->x - b->x) * (a->x - b->x) + (a->y - b->y) * (a->y - b->y) + (a->z - b->z) * (a->z - b->z);
    if (len2 <= 0.1f) {
        return 0;
    }
    PSVECSubtract(b, a, &ab);
    PSVECSubtract(c, a, &ac);
    t = PSVECDotProduct(&ab, &ac) / len2;
    PSVECScale(&ab, &p, t);
    PSVECAdd(&p, a, &p);
    t = (p.x - c->x) * (p.x - c->x) + (p.y - c->y) * (p.y - c->y) + (p.z - c->z) * (p.z - c->z);
    if (t >= r2) {
        return 0;
    }
    h = SQRTF(r2 - t);
    PSVECSubtract(a, &p, &q);
    PSVECScale(&q, &q, h / PSVECMag(&q));
    PSVECAdd(&q, &p, &q);
    dist2 = (a->x - q.x) * (a->x - q.x) + (a->y - q.y) * (a->y - q.y) + (a->z - q.z) * (a->z - q.z);
    if (dist2 > len2) {
        return 0;
    }
    PSVECSubtract(a, &q, &d1);
    PSVECSubtract(a, b, &d2);
    if (PSVECDotProduct(&d1, &d2) < 0.0f) {
        return 0;
    }
    PSVECSubtract(b, &q, &d1);
    PSVECSubtract(b, a, &d2);
    if (PSVECDotProduct(&d1, &d2) < 0.0f) {
        return 0;
    }
    if (out) {
        *out = q;
    }
    return 1;
}

// 1 when two spheres overlap.
int SphereHitCk(Vec* pPos1, Vec* pPos2, f32 ra, f32 rb)
{
    Vec d;
    f32 r;

    PSVECSubtract(pPos1, pPos2, &d);
    r = ra + rb;
    return d.x * d.x + d.y * d.y + d.z * d.z < r * r;
}

// Launch velocity (units / frame, gravity 20) that carries a body from `from` to `to` peaking `h`
// above the higher end; h <= 0 gives the straight difference.
void CalcParabolaVector(Vec* out, Vec* from, Vec* to, f32 h)
{
    f32 g = 20.0f;
    f32 t;

    if (h <= 0.0f) {
        PSVECSubtract(to, from, out);
        return;
    }
    if (from->y > to->y) {
        h += from->y;
    } else {
        h += to->y;
    }
    t = SQRTF((h - from->y) * 2.0f / 20.0f);
    t += SQRTF((h - to->y) * 2.0f / 20.0f);
    PSVECSubtract(to, from, out);
    PSVECScale(out, out, 1.0f / t);
    out->y = SQRTF((h - from->y) * 40.0f);
}

// Distance covered while `speed` decelerates by `decel` per frame to 0.
f32 CalcStopDist(f32 speed, f32 decel)
{
    f32 d = 0.0f;

    do {
        d += speed;
        speed -= decel;
    } while (!(speed <= 0.0f));
    return d;
}

// Moves `pos` `dist` units toward `target`; returns 1 (and snaps) when it arrives.
int CalcMovePosDist(Vec* pos, Vec* target, f32 dist)
{
    Vec dir;

    if (GetDistance(pos, target) <= dist * dist) {
        *pos = *target;
        return 1;
    }
    PSVECSubtract(target, pos, &dir);
#line 908 "D:/Bio4/Prog/sub2.cpp"
    VECNormalize(&dir, &dir);
    PSVECScale(&dir, &dir, dist);
    PSVECAdd(pos, &dir, pos);
    return 0;
}

// Dead-stripped in the original (a double 0.0 pool).
static int sub2_dead5(f64 x)
{
    if (x != 0.0) {
        return 1;
    }
    return 0;
}
