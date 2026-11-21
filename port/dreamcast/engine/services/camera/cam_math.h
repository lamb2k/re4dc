// cam_math.h: the camera service's vector and frame helpers (lane eng-e1j), on SH4ZAM's types.
//
// The arithmetic is plain single precision: SH4ZAM's element-wise vector operations (add, sub, scale, cross, dot with
// FIPR off are the same operations on the PC and the SH-4), exact roots (__builtin_sqrtf: SSE sqrtss, SH-4 FSQRT) and
// true divisions, the toolchain's sinf / cosf / tanf / atan2f. The approximate SH-4 paths (FSRRA, FSCA, FTRV) are not
// used: the camera's frame turns the stick into Leon's walking direction, so the PC check (hostref) and the console must
// compute the same camera.
#pragma once
#include "types.h"
#include "vec.h"
#include "sh4zam/shz_vector.h"
#include "sh4zam/shz_matrix.h"

namespace camsvc {

typedef shz_vec3_t v3;
// A camera or player frame: SH4ZAM's 3x4 (columns: left = the right axis, up, forward = the look axis, pos).
typedef shz_mat3x4_t Frame;

inline v3 V(const Vec& v) { return shz_vec3_init(v.x, v.y, v.z); }
inline v3 V(const Vec* v) { return shz_vec3_init(v->x, v->y, v->z); }
inline void put(Vec* d, v3 v) { d->x = v.x, d->y = v.y, d->z = v.z; }
inline v3 vadd(v3 a, v3 b) { return shz_vec3_add(a, b); }
inline v3 vsub(v3 a, v3 b) { return shz_vec3_sub(a, b); }
inline v3 vscale(v3 a, f32 s) { return shz_vec3_scale(a, s); }
inline v3 vcross(v3 a, v3 b) { return shz_vec3_cross(a, b); }
inline f32 vdot(v3 a, v3 b) { return shz_vec3_dot(a, b); }
inline f32 vlen2(v3 a) { return shz_vec3_magnitude_sqr(a); }
inline f32 vlen(v3 a) { return __builtin_sqrtf(shz_vec3_magnitude_sqr(a)); }
inline f32 vdist(v3 a, v3 b) { return vlen(vsub(a, b)); }
inline bool vzero(v3 a) { return a.x == 0.0f && a.y == 0.0f && a.z == 0.0f; }
// a unit vector (an exact root and a true division); the zero vector stays zero
inline v3 vunit(v3 a)
{
    const f32 l = vlen(a);
    return l != 0.0f ? vscale(a, 1.0f / l) : a;
}
// a * wa + b * wb
inline v3 vmix(v3 a, f32 wa, v3 b, f32 wb) { return vadd(vscale(a, wa), vscale(b, wb)); }

// Frames <-> the game's row-major 3x4 matrices (Mtx: m[row][col], column c is an axis, column 3 the position)
inline Frame frame_of(const Mtx m)
{
    Frame f;
    for (int c = 0; c < 4; c++) f.col[c] = shz_vec3_init(m[0][c], m[1][c], m[2][c]);
    return f;
}
inline void frame_put(Mtx m, const Frame& f)
{
    for (int c = 0; c < 4; c++) m[0][c] = f.col[c].x, m[1][c] = f.col[c].y, m[2][c] = f.col[c].z;
}
// a point and a direction through a frame
inline v3 frame_point(const Frame& f, v3 p) { return vadd(vadd(vadd(vscale(f.left, p.x), vscale(f.up, p.y)), vscale(f.forward, p.z)), f.pos); }
inline v3 frame_dir(const Frame& f, v3 d) { return vadd(vadd(vscale(f.left, d.x), vscale(f.up, d.y)), vscale(f.forward, d.z)); }
// A general frame's inverse map (the axes need not be unit or orthogonal): SH4ZAM's adjugate of the axes, divided by
// the determinant (a true division), applied to p - pos.
struct FrameInverse {
    shz_mat3x3_t adj;   // rows of the inverse, as columns of the adjugate's transpose
    f32 inv_det;
    v3 pos;
};
inline FrameInverse frame_inverse(const Frame& f)
{
    FrameInverse r;
    shz_mat3x3_t axes;
    axes.col[0] = f.left, axes.col[1] = f.up, axes.col[2] = f.forward;
    shz_mat3x3_adjugate(&axes, &r.adj);
    const f32 det = vdot(f.left, vcross(f.up, f.forward));
    r.inv_det = det != 0.0f ? 1.0f / det : 0.0f;
    r.pos = f.pos;
    return r;
}
inline v3 inverse_point(const FrameInverse& r, v3 p)
{
    const v3 d = vsub(p, r.pos);
    const shz_mat3x3_t& a = r.adj;
    // (adj * d) / det, adj's columns from shz_mat3x3_adjugate
    const v3 q = vadd(vadd(vscale(a.col[0], d.x), vscale(a.col[1], d.y)), vscale(a.col[2], d.z));
    return vscale(q, r.inv_det);
}

}   // namespace camsvc

// The services row (lane eng-e1j, audit section 6): each camera service entry point the hosted controller calls is
// timed as service work by the engine's accounting (host/e1_wraps.cpp e1_svc_enter / leave; nested calls count once).
// The PC reference has no accounting: the hooks are weak and absent there.
extern "C" unsigned e1_svc_slot_named(const char* name, unsigned group) __attribute__((weak));
extern "C" void e1_svc_enter(unsigned slot) __attribute__((weak));
extern "C" void e1_svc_leave() __attribute__((weak));
enum { CAM_SVC_GROUP = 6 };   // core/e1_core.h E1_SVC_CAMERA
struct CamSvcScope {
    bool on;
    CamSvcScope(unsigned& slot, const char* name)
    {
        on = e1_svc_enter != 0;
        if (!on) return;
        if (slot == ~0u) slot = e1_svc_slot_named(name, CAM_SVC_GROUP);
        e1_svc_enter(slot);
    }
    ~CamSvcScope()
    {
        if (on) e1_svc_leave();
    }
};
#define CAM_SVC(name)                 \
    static unsigned cam_slot_ = ~0u; \
    CamSvcScope cam_scope_(cam_slot_, name)
