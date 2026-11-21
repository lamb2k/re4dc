// cam_eval.cpp: the camera service's evaluation under the hosted controller (lane eng-e1j, ruling H-016.1).
//
// The controller (cam_ctrl, cam_qfps, cam_extra, hosted) decides: which area and cut, which routine, which target and
// offset table, which site. Everything it then asks to be evaluated is here, the engine's own code on SH4ZAM's types
// (cam_math.h):
//   - the cut blend and the smoothing (CameraInterpolation::move, CameraSmooth::move): one weighted mix over the
//     camera's eight parameters;
//   - the area containment tests (areaHit, area_hit_p3, area_hit_pN): edge sides and a crossing count;
//   - the camera's line-of-sight probe (cameraHitCheck): the nearest of three collision queries, the partner's body;
//   - the rail (Parametrize, BSpline, searchRail, HermiteExport, debugDrawRail): a B-spline through the cut's keys on
//     the original's knots, fitted by a tridiagonal solve and evaluated on its span, the nearest rail point, the cut as
//     a keyed track;
//   - the attached-motion camera (CameraAttachedToMotion::move);
//   - the shoulder camera's frame, offsets and wall probe (CameraQuasiFPS::calcBaseMatrix, calcOffset, hitCheck,
//     offsetCorrection);
//   - the camera data's relocation and version (CameraControl::calcAddr, cameraDataVersion).
// Same mathematics as the original game; how each form differs is said at each function and in
// docs/engine/lanes/eng-e1j.md. Each entry point is timed as service work (CAM_SVC, cam_math.h).
#define fabsf cam_eval_game_fabsf   // math_sub.h's static fabsf against the C library's (camera_svc.cpp)
#include "types.h"
#include "vec.h"
#include "global.h"
#include "math_sub.h"
#include "db_log.h"
#include "camera.h"
#include "cam_ctrl.h"
#include "cam_extra.h"
#include "cam_qfps.h"
#include "motion.h"
#include "model.h"
#include "player.h"
#include "pl_sub.h"
#include "em.h"
#include "atari.h"
#include "at_mod.h"
#undef fabsf
#include "camera_svc.h"
#include "eng_camera.h"   // lane eng-e1m: the diagnosis lines
#include "cam_math.h"

using namespace camsvc;

extern "C" {
f32 sinf(f32);
f32 cosf(f32);
f32 tanf(f32);
f32 atan2f(f32, f32);
}
extern f32 ZNEAR;
extern f32 g_crouch_cam_z_back;   // cam_qfps.cpp (600)

namespace {
constexpr f32 kPi = 3.1415927f;
constexpr f32 kTwoPi = 6.2831855f;
constexpr f32 kDeg = 0.017453292f;
constexpr f32 kCrouchDrop = 400.0f;   // cam_qfps.cpp's file-static g_crouch_cam_y_down (nothing writes it)

// The camera's parameter block as eight lanes: eye x y z, target x y z, roll, fov.
inline f32* lanes(CameraParam* p) { return &p->pos.x; }
}   // namespace

// ==== the cut blend and the smoothing (cam_ctrl.cpp) ====

// The blend toward the target over the frames left: each tick the camera takes 1 / frames of the target and keeps the
// rest of itself; at 0 frames it is the target. The target is left multiplied by the step's weight, as the original
// leaves its caller's target (a routine that does not rewrite its target each tick sees it so).
void CameraInterpolation::move(CameraParam* p)
{
    CAM_SVC("CameraInterpolation::move");
    if (frame != 0 && cam_control != 4) {   // control caminterp: no blend
        cam_cnt.blends++;
        const f32 w = 1.0f / (f32) frame, keep = 1.0f - w;
        f32* c = lanes(&param);
        f32* t = lanes(p);
        for (int i = 0; i < 8; i++) {
            t[i] *= w;
            c[i] = c[i] * keep + t[i];
        }
        frame--;
    } else {
        frame = 0;
        param = *p;
    }
}

// Exponential smoothing: the camera keeps m_ratio of itself (its eye and target first carried by this tick's quake
// offset) and takes the rest from the target; the reinit flag snaps to the target.
void CameraSmooth::move(CameraParam* p)
{
    CAM_SVC("CameraSmooth::move");
    if ((m_flag & 1) || cam_control == 3) {   // control camsmooth: always snapped
        m_flag &= ~1;
        param = *p;
        return;
    }
    cam_cnt.smooths++;
    eng_cam_diag("si", p, sizeof(CameraParam) / 4);   // lane eng-e1m: the smoothing's target
    const f32 keep = m_ratio, take = 1.0f - m_ratio;
    const v3 q = V(pG->quake_ofs);
    put(&param.pos, vmix(vadd(V(param.pos), q), keep, V(p->pos), take));
    put(&param.at, vmix(vadd(V(param.at), q), keep, V(p->at), take));
    param.roll = param.roll * keep + p->roll * take;
    param.fovy = param.fovy * keep + p->fovy * take;
}

// ==== area containment (cam_ctrl.cpp) ====

namespace {
inline f32 wrap_pi(f32 a)
{
    while (a >= kPi) a -= kTwoPi;
    while (a < -kPi) a += kTwoPi;
    return a;
}
// the area's height band: 100 above the position, base_y up to base_y + height
inline bool in_band(const Vec* pos, const CameraAreaInfo* a)
{
    const f32 y = pos->y + 100.0f;
    return y >= a->base_y && y < a->base_y + a->height;
}
// the side of p from the ground edge a -> b: the y component of (b - a) x (p - a); >= 0 on the area's inner side
inline f32 edge_side(const Vec& a, const Vec& b, const Vec* p) { return (b.z - a.z) * (p->x - a.x) - (b.x - a.x) * (p->z - a.z); }
}   // namespace

// A position in an area: not when the area is off (attr 4); with attr 0x40 the facing must be within 135 degrees of
// the area's direction; then the polygon test of its size.
int areaHit(Vec* pos, CameraAreaInfo* area, f32 dir)
{
    CAM_SVC("areaHit");
    cam_cnt.areas++;
    if (area->attr & 4) return 0;
    if (area->attr & 0x40) {
        const f32 d = wrap_pi(wrap_pi(dir) - area->dir);
        if (d > 2.3561945f || d < -2.3561945f) return 0;
    }
    return area->num > 4 ? area_hit_pN(pos, area) : area_hit_p3(pos, area);
}

// Up to four points: inside when the position is on the inner side of every edge (the original tests the inner wedge
// of two opposite corners: the same edges).
int area_hit_p3(Vec* pos, CameraAreaInfo* area)
{
    if (!in_band(pos, area)) return 0;
    const int n = area->num;
    for (int k = 0; k < n; k++)
        if (edge_side(area->points[k], area->points[(k + 1) % n], pos) < 0.0f) return 0;
    return 1;
}

// More points: the parity of the edges crossed by the ray from the position along (1, 0, 1). An edge counts when the
// ray's line x - z = c meets it at a parameter s in [0, 1) ahead of the position. As the area data was laid out
// against: an edge parallel to the x or the z axis, or to the ray, never counts.
int area_hit_pN(Vec* pos, CameraAreaInfo* area)
{
    if (!in_band(pos, area)) return 0;
    const int n = area->num;
    const f32 c = pos->x - pos->z;
    int count = 0;
    for (int k = 0; k < n; k++) {
        const Vec& a = area->points[k];
        const Vec& b = area->points[(k + 1) % n];
        const f32 dx = b.x - a.x, dz = b.z - a.z;
        if (dx == 0.0f || dz == 0.0f || dx == dz) continue;
        const f32 s = (c - (a.x - a.z)) / (dx - dz);
        if (!(s >= 0.0f && s < 1.0f)) continue;
        if (a.x + dx * s >= pos->x) count++;
    }
    return count & 1;
}

// ==== the camera's line-of-sight probe (cam_ctrl.cpp) ====

// From `from` to `to` against the characters, the objects and the scenery's camera walls: the nearest hit in *pos /
// *nrm. Then the partner (Ashley, id 3): her body made 1000 taller downwards; when the probe's end (the hit, or `to`)
// stands in it (radius x 1.1, on the ground plane), her body 1.33 times wider is probed too and wins when hit.
int cameraHitCheck(Vec* pos, Vec* nrm, Vec* from, Vec* to)
{
    CAM_SVC("cameraHitCheck");
    cam_cnt.probes++;
    struct Hit {
        Vec p, n;
        int hit;
    } h[3];
    h[0].hit = EmHitCheck(&h[0].p, &h[0].n, from, to, 1);
    h[1].hit = ObjHitCheck(&h[1].p, &h[1].n, from, to, 1);
    h[2].hit = SatMgr.hitCheck(from, to, &h[2].p, &h[2].n, 0x8000, 0x1C2810);
    int ret = 0;
    f32 best = 0.0f;
    const v3 o = V(from);
    for (int k = 0; k < 3; k++) {
        if (!h[k].hit) continue;
        const f32 d2 = vlen2(vsub(V(h[k].p), o));
        if (!ret || d2 < best) {
            best = d2;
            *pos = h[k].p;
            *nrm = h[k].n;
            ret = 1;
        }
    }
    if (pSubEm && pSubEm->id == 3) {
        cAtariInfo body = pSubEm->atari;
        cModel* parts = body.m_parts_no != 0 ? pSubEm->getPartsPtr(body.m_parts_no - 1) : pSubEm;
        if (parts) {
            body.m_offset.y -= 1000.0f;
            body.m_height += 1000.0f;
            const v3 base = frame_point(frame_of(parts->mat), V(body.m_offset));
            Vec end = ret ? *pos : *to;
            const f32 r = body.m_radius * 1.1f;
            const f32 gx = end.x - base.x, gz = end.z - base.z;
            if (base.y <= end.y && end.y <= base.y + body.m_height && gx * gx + gz * gz <= r * r) {
                body.m_radius *= 1.33f;
                Vec hp, hn;
                if (ObaLineHitChk(pSubEm, &body, from, &end, &hp, &hn)) {
                    ret = 1;
                    *pos = hp;
                }
            }
        }
    }
    return ret;
}

// ==== the rail (cam_ctrl.cpp) ====
// A rail cut's keys (pos, at, roll, fov) are interpolated by a B-spline of degree k = min(2, keys - 1) on the original's
// knot vector: k + 1 knots at 0, one at (j - k - 1) + (k + 1) / 2 for j = k + 1 .. n - 1, k + 1 at n - 1. The rail
// parameter runs 0 .. n - 1 (key i at i). The basis is evaluated on its span only (de Boor's triangle, k + 1 values);
// the control points are solved from the keys by the collocation matrix, which for these knots is tridiagonal
// (B-spline collocation is totally positive: elimination without pivoting is stable), eight channels at once, no
// heap. The original builds the full n x (k + 1) table, inverts the dense matrix and multiplies, with heap buffers.

namespace {
constexpr int kRailMax = 26;   // CameraBSpline's arrays

inline f32 rail_knot(int n, int k, int j)
{
    const int m = k + 1;
    if (j < m) return 0.0f;
    if (j < n) return (f32) (j - m) + (f32) m * 0.5f;
    return (f32) (n - 1);
}

// The span J (k <= J <= n - 1) with knot J <= t < knot J + 1; the end (t up to n - 1 + 1e-5, the original's closing
// rule) is the last span. -1: t outside the rail (the original's basis is then zero).
int rail_span(int n, int k, f32 t)
{
    if (t < 0.0f || t > (f32) (n - 1) + 0.00001f) return -1;
    for (int j = k; j < n - 1; j++)
        if (t < rail_knot(n, k, j + 1)) return j;
    return n - 1;
}

// The k + 1 basis values N[J - k .. J] at t (The NURBS Book, A2.2).
void rail_basis(int n, int k, int J, f32 t, f32* N)
{
    f32 left[4], right[4];
    N[0] = 1.0f;
    for (int d = 1; d <= k; d++) {
        left[d] = t - rail_knot(n, k, J + 1 - d);
        right[d] = rail_knot(n, k, J + d) - t;
        f32 saved = 0.0f;
        for (int r = 0; r < d; r++) {
            const f32 tmp = N[r] / (right[r + 1] + left[d - r]);
            N[r] = saved + right[r + 1] * tmp;
            saved = left[d - r] * tmp;
        }
        N[d] = saved;
    }
}

// the eight control-point channels of a rail
inline f32* rail_channel(CameraBSpline* bs, int c)
{
    f32* ch[8] = {bs->px, bs->py, bs->pz, bs->ax, bs->ay, bs->az, bs->roll, bs->fovy};
    return ch[c];
}
}   // namespace

// The rail's control points from the cut's keys.
void Parametrize(CameraCut* cut, CameraBSpline* bs)
{
    CAM_SVC("Parametrize");
    cam_cnt.rails++;
    bs->num = cut->num;
    if (bs->num <= 1) return;
    const int n = bs->num < kRailMax ? bs->num : kRailMax;
    const int k = n - 1 < 2 ? n - 1 : 2;
    bs->k = k;
    // rows: sub (column i - 1), diagonal, super (i + 1); right-hand sides: the keys' eight channels
    f32 sub[kRailMax], dia[kRailMax], sup[kRailMax], rhs[kRailMax][8];
    for (int i = 0; i < n; i++) {
        f32 N[3];
        const int J = rail_span(n, k, (f32) i);
        rail_basis(n, k, J, (f32) i, N);
        sub[i] = dia[i] = sup[i] = 0.0f;
        for (int r = 0; r <= k; r++) {
            const int col = J - k + r;
            if (col == i - 1) sub[i] = N[r];
            else if (col == i) dia[i] = N[r];
            else if (col == i + 1) sup[i] = N[r];
        }
        const f32 key[8] = {cut->pos[i].x, cut->pos[i].y, cut->pos[i].z, cut->at[i].x, cut->at[i].y, cut->at[i].z, cut->roll[i], cut->fovy[i]};
        for (int c = 0; c < 8; c++) rhs[i][c] = key[c];
    }
    // forward elimination, then back substitution (Thomas)
    for (int i = 1; i < n; i++) {
        const f32 w = sub[i] / dia[i - 1];
        dia[i] -= w * sup[i - 1];
        for (int c = 0; c < 8; c++) rhs[i][c] -= w * rhs[i - 1][c];
    }
    for (int c = 0; c < 8; c++) {
        f32* out = rail_channel(bs, c);
        out[n - 1] = rhs[n - 1][c] / dia[n - 1];
        for (int i = n - 2; i >= 0; i--) out[i] = (rhs[i][c] - sup[i] * out[i + 1]) / dia[i];
    }
}

// The rail at bs->t: the camera's pos, at, roll and fov from the span's k + 1 control points (only the parameter block
// is the rail's output; the original cleared the whole Camera first).
void BSpline(CameraBSpline* bs, Camera* cam, int)
{
    CAM_SVC("BSpline");
    cam_cnt.rails++;
    const int n = bs->num < kRailMax ? bs->num : kRailMax;
    const f32 t = cam_control == 5 ? bs->t + 0.25f : bs->t;   // control camrail
    f32* out = lanes(&cam->param);
    for (int c = 0; c < 8; c++) out[c] = 0.0f;
    if (n <= 0) return;
    const int k = bs->k;
    const int J = rail_span(n, k, t);
    if (J < 0) return;
    f32 N[3];
    rail_basis(n, k, J, t, N);
    for (int c = 0; c < 8; c++) {
        const f32* p = rail_channel(bs, c) + (J - k);
        f32 s = 0.0f;
        for (int r = 0; r <= k; r++) s += N[r] * p[r];
        out[c] = s;
    }
}

// The rail parameter nearest the aim: the nearest key, unless a segment of the cut's target line holds the aim's
// ground projection strictly between its ends and its point there is nearer (on a tie the key wins). The segment's
// parameter is the ground distance along it over its full length, as the original measures it.
void searchRail(CameraBSpline* bs, CameraCut* cut, Vec* aim, int)
{
    CAM_SVC("searchRail");
    cam_cnt.rails++;
    if (cut->num <= 0) return;
    const v3 q = V(aim);
    int key = 0;
    f32 key_d = 10000000000.0f;
    for (int i = 0; i < cut->num; i++) {
        const f32 d = vdist(q, V(cut->at[i]));
        if (d < key_d) key_d = d, key = i;
    }
    bool found = false;
    f32 seg_d = 10000000000.0f;
    for (int i = 0; i < cut->num - 1; i++) {
        const v3 a = V(cut->at[i]), b = V(cut->at[i + 1]);
        const v3 d = vsub(b, a);
        const v3 g = shz_vec3_init(d.x, 0.0f, d.z);
        const f32 lg = vlen(g);
        const v3 qa = vsub(q, a), qb = vsub(q, b);
        const f32 s = vdot(g, shz_vec3_init(qa.x, 0.0f, qa.z)) / lg;
        const f32 e = vdot(g, shz_vec3_init(qb.x, 0.0f, qb.z)) / lg;
        if (!(s * e < 0.0f)) continue;
        const f32 u = s / vlen(d);
        const f32 dist = vdist(q, vadd(a, vscale(d, u)));
        if (dist < seg_d) {
            seg_d = dist;
            bs->t = (f32) i + u;
            bs->seg = i;
            found = true;
        }
    }
    if (!found || seg_d > key_d) {
        bs->seg = key;
        bs->t = (f32) key;
    }
}

// A rail cut as a camera motion file (the CameraMotion format the keyed-track service reads): a header (frame count,
// four tracks: pos and at of type 4, roll and fov of type 2; part numbers 0..3; an offset table), then per track three
// axes of {key count, key frames, keys {value, tangent, tangent}} (f32), each track 4-byte aligned. Keys are every 30
// frames or at the cut's frames; a key's tangent is the frame-weighted mean of its neighbouring slopes (one-sided at
// the ends) times the frames since the previous key (so 0 at the first key). Fov in radians; roll and fov repeat on
// their three axes. Returns the size.
// Lane eng-e1n (H-017.3): the cut's key count and the file's size are checked before anything is written. The
// destination is a camera motion buffer of kMotionBuffer bytes (cam_ctrl.cpp's CAMERA_MOTION_BUFFER_SIZE: the only one
// the controller exports into). Refused: a count outside 1 .. kRailMax (the cut's frame table), or a file larger than
// the buffer. Nothing is written; the return is the size the file would need (0 for a bad count), which the hosted
// callers compare with their buffer and log as the original does when it is larger; the camera motion they then make
// on the buffer is not played (cam_track_export_refused: the track service refuses that buffer's next motion), so the
// controller leaves the cut at its first move.
// Lane eng-e1p (H-018.1): every motion cut of the room's camera data is exported and converted when the room is loaded
// (camera_svc.cpp cam_track_room_load, through cam_cut_export below); at a cut switch in play the writer is a lookup:
// the room's converted track is handed to the CameraMotion made next on the buffer (cam_track_cut_ready) and nothing is
// written. A cut without a ready track (a cut the room's data does not hold, or the lab arm CUTCONV) is written as
// before and converted by the CameraMotion: a conversion in play, counted (the selector fails a timing scene on it).
extern "C" void cam_track_export_refused(const u8* buf, int refused);    // camera_svc.cpp
extern "C" int cam_track_cut_ready(const CameraCut* cut, const u8* buf);  // camera_svc.cpp
namespace {
constexpr int kMotionBuffer = 0x440;
// header 36 bytes; per track three axes of {count, frames, keys of 12 bytes}, each track padded to 4 bytes
constexpr int export_size(int n) { return 36 + 4 * (((3 * (2 + 2 * n + 12 * n)) + 3) & ~3); }
// the size the cut's file needs, 0 for a count outside 1 .. kRailMax
int export_need(const CameraCut* cut) { return cut->num >= 1 && cut->num <= kRailMax ? export_size(cut->num) : 0; }
int export_write(CameraCut* cut, u8* buf);
}   // namespace
// The room load's writer (camera_svc.cpp): the cut's file into `buf` (kMotionBuffer bytes), or nothing and the size it
// would need (0: a bad count) when the writer refuses it.
extern "C" int cam_cut_export(CameraCut* cut, u8* buf)
{
    const int need = export_need(cut);
    if (need == 0 || need > kMotionBuffer) return need;
    return export_write(cut, buf);
}
int CameraControl::HermiteExport(CameraCut* cut, u8* buf)
{
    CAM_SVC("CameraControl::HermiteExport");
    cam_cnt.rails++;
    const int count = cut->num;
    const int need = export_need(cut);
    if (need == 0 || need > kMotionBuffer) {
        cam_cnt.key_errors++;
        cam_track_export_refused(buf, 1);
        pLog->err(0, 0, "HermiteExport(): cut of %d keys refused (%d bytes, buffer %d)", count, need, kMotionBuffer);
        return need;
    }
    cam_track_export_refused(buf, 0);
    const int ready = cam_track_cut_ready(cut, buf);   // the room's track: a lookup, nothing written
    if (ready < 0) {                                   // a cut the room load refused (its keys): not played
        cam_cnt.key_errors++;
        cam_track_export_refused(buf, 1);
        return need;
    }
    if (ready > 0) return ready;
    return export_write(cut, buf);
}
namespace {
int export_write(CameraCut* cut, u8* buf)
{
    struct Out {
        u8* p;
        void u8_(u32 v) { *p++ = (u8) v; }
        void u16_(u32 v) { u8_(v), u8_(v >> 8); }
        void u32_(u32 v) { __builtin_memcpy(p, &v, 4), p += 4; }
        void f32_(f32 v) { __builtin_memcpy(p, &v, 4), p += 4; }
    } o = {buf};
    const int n = cut->num;
    o.u16_((n - 1) * 30);
    o.u8_(4);
    static const u8 kind[4] = {4, 4, 2, 2};
    for (int i = 0; i < 4; i++) o.u16_(kind[i]);
    for (int i = 0; i < 4; i++) o.u8_(i);
    o.u8_(0);
    o.u32_(0);
    u8* table = o.p;
    for (int i = 0; i < 4; i++) o.u32_(0);
    u16 frame[kRailMax];
    for (int k = 0; k < n && k < kRailMax; k++) frame[k] = cut->frames == NULL ? (u16) (k * 30) : cut->frames[k];
    auto value = [cut](int track, int axis, int k) -> f32 {
        switch (track) {
        case 0: return (&cut->pos[k].x)[axis];
        case 1: return (&cut->at[k].x)[axis];
        case 2: return cut->roll[k];
        default: return cut->fovy[k] * kDeg;
        }
    };
    for (int track = 0; track < 4; track++) {
        const u32 at = (u32) (o.p - buf);
        __builtin_memcpy(table + 4 * track, &at, 4);
        for (int axis = 0; axis < 3; axis++) {
            o.u16_(n);
            for (int k = 0; k < n; k++) o.u16_(frame[k]);
            for (int k = 0; k < n; k++) {
                const int k0 = k > 0 ? k - 1 : 0, k1 = k < n - 1 ? k + 1 : n - 1;
                const f32 v = value(track, axis, k), v0 = value(track, axis, k0), v1 = value(track, axis, k1);
                const f32 dt0 = (f32) ((int) frame[k] - (int) frame[k0]), dt1 = (f32) ((int) frame[k1] - (int) frame[k]);
                f32 slope;
                if (k == 0) slope = (v1 - v) / dt1;
                else if (k == n - 1) slope = (v - v0) / dt0;
                else slope = (dt1 * ((v - v0) / dt0) + dt0 * ((v1 - v) / dt1)) / (dt0 + dt1);
                const f32 tan = slope * dt0;
                o.f32_(v);
                o.f32_(tan);
                o.f32_(tan);
            }
        }
        while ((o.p - buf) % 4) o.u8_(0);
    }
    const u32 last = n > 0 ? frame[n - 1] : 0;
    buf[0] = (u8) last, buf[1] = (u8) (last >> 8);
    return (int) (o.p - buf);
}
}   // namespace

// Debug drawing of the rail: counted, not drawn.
void CameraControl::debugDrawRail(CameraCut* cut)
{
    (void) cut;
    cam_cnt.debug_draws++;
}

// ==== the camera a motion carries (cam_extra.cpp) ====
// The motion's camera channels (evaluated with its pose) into the world by their parts' matrix. Unless the motion is
// world-space (Mot_attr 0x200): a target behind the model's x-y plane while the eye is in front is brought onto the
// plane along the eye-target line (a plane test on the model's axes: n = x axis x y axis; the original inverts the
// model's matrix and works in model space), and the eye is kept out of walls by the probe; then the frame.
void CameraAttachedToMotion::move()
{
    AttachCamera* ac = MOTION(m_pModel)->pAttachCam;
    if (ac == 0) return;
    CAM_SVC("CameraAttachedToMotion::move");
    cam_cnt.attached++;
    const Frame pm = frame_of(*ac->pMat);
    if (ac->parts[0] != 0xFF) put(&param.pos, frame_point(pm, V(ac->out[0])));
    if (ac->parts[1] != 0xFF) put(&param.at, frame_point(pm, V(ac->out[1])));
    if (ac->parts[2] != 0xFF) param.roll = ac->out[2].y;
    if (ac->parts[3] != 0xFF) param.fovy = ac->out[3].y * 180.0f / kPi;
    if (!(MOTION(m_pModel)->Mot_attr & 0x200)) {
        const Frame mm = frame_of(m_pModel->mat);
        v3 nz = vcross(mm.left, mm.up);
        if (vdot(nz, mm.forward) < 0.0f) nz = vscale(nz, -1.0f);   // the model's +z side
        const v3 eye = V(param.pos), tgt = V(param.at);
        const f32 de = vdot(nz, vsub(eye, mm.pos)), dt = vdot(nz, vsub(tgt, mm.pos));
        if (dt > 0.0f && de < 0.0f) put(&param.at, vadd(eye, vscale(vsub(tgt, eye), de / (de - dt))));
        Vec to = param.at, from = param.pos, hit, nrm;
        if (cameraHitCheck(&hit, &nrm, &to, &from)) param.pos = hit;
    }
    CameraSetOrientationRoll(this);
}

// ==== the shoulder camera (cam_qfps.cpp) ====

// The player-space frame the shoulder offsets are placed in: during the search delay the frame faces the aim point
// from the player (a yaw frame at the player), after it the player's matrix; one-shot translation and look overrides;
// while not aiming the up axis tilts toward the floor normal (a filtered ratio of the floor-follow setting) and the
// crouch states drop the frame (stand-crouch 800 down; crouched 400 down and back along the look by
// g_crouch_cam_z_back).
void CameraQuasiFPS::calcBaseMatrix(Mtx m)
{
    CAM_SVC("CameraQuasiFPS::calcBaseMatrix");
    cam_cnt.shoulder++;
    static f32 slope_ratio = 0.33333334f;
    Frame f = frame_of(m);
    m_search_cnt++;
    if (m_search_cnt > m_search_frame) {
        m_search_cnt = m_search_frame;
        m_state |= 1;
    } else {
        const v3 o = shz_vec3_init(m_pl_mat[0][3], m_pl_mat[1][3], m_pl_mat[2][3]);
        const v3 d = vsub(V(m_Aim), o);
        const f32 yaw = atan2f(d.x, d.z), c = cosf(yaw), s = sinf(yaw);
        f.left = shz_vec3_init(c, 0.0f, -s);
        f.up = shz_vec3_init(0.0f, 1.0f, 0.0f);
        f.forward = shz_vec3_init(s, 0.0f, c);
        f.pos = o;
    }
    if (m_state & 1) f = frame_of(m_pl_mat);
    if (!vzero(V(m_pl_ofs))) {
        f.pos = frame_point(f, V(m_pl_ofs));
        m_pl_ofs.x = m_pl_ofs.y = m_pl_ofs.z = 0.0f;
    }
    if (!vzero(V(m_pl_dir))) {
        const v3 right = vunit(vcross(f.up, V(m_pl_dir)));
        f.forward = vcross(right, f.up);
        f.left = right;
        m_pl_dir.x = m_pl_dir.y = m_pl_dir.z = 0.0f;
    }
    if (!pPL->isKamae() && m_p_floor_norm != NULL && !(pG->Status_flg[0] & 0x40000)) {
        Vec up = {0.0f, 1.0f, 0.0f}, nrm = *m_p_floor_norm, tilt;
        const f32 keep = 0.9f;   // the filter's own weight (the original's static f)
        slope_ratio = keep * slope_ratio + (1.0f - keep) * m_floor_ratio;
        put(&tilt, f.up);
        VecInternalDivisionAngle(&up, &nrm, slope_ratio, &tilt, 1.0f - slope_ratio);
        const v3 u = V(tilt);
        const v3 look = vcross(f.left, u);
        f.left = vcross(u, look);
        f.up = u;
        f.forward = look;
        switch (PlGetStatus()) {
        case 0x4000: f.pos.y -= 800.0f; break;
        case 0x8000:
            f.pos = vsub(f.pos, vscale(look, g_crouch_cam_z_back));
            f.pos.y -= kCrouchDrop;
            break;
        }
    }
    frame_put(m, f);
    eng_cam_diag("bm", m, 12);   // lane eng-e1m: the base frame
}

// The tick's shoulder offset: the site's offsets blended from the old table (blend_ratio, counted down over the blend's
// frames) as one mix of their eleven numbers; crouched, the close point 200 lower and further back; the pitch picks
// between the mid site and the up (angle_y > 0) or down (< 0) site, roll and fov from the mid site; then turned about y
// by the yaw angle_x (a sine / cosine pair; the original builds a rotation matrix).
void CameraQuasiFPS::calcOffset(QfpsOfs* out)
{
    CAM_SVC("CameraQuasiFPS::calcOffset");
    if (!(m_state & 8)) {
        m_blend_count--;
        if (m_blend_count > 0) {
            blend_ratio = (f32) m_blend_count / (f32) m_blend_frame;
        } else {
            m_state &= ~4;
            blend_ratio = 0.0f;
        }
    }
    QfpsOfs o[3];
    constexpr int kWords = sizeof(QfpsOfs) / sizeof(f32);
    for (int i = 0; i < 3; i++) {
        if (m_state & 4) {
            const f32 r = blend_ratio, r1 = 1.0f - r;
            const f32* a = &old[i].Campos.x;
            const f32* b = &cur[i].Campos.x;
            f32* d = &o[i].Campos.x;
            for (int w = 0; w < kWords; w++) d[w] = a[w] * r + b[w] * r1;
        } else {
            o[i] = cur[i];
        }
    }
    if (PlGetStatus() == 0x8000)
        for (int i = 0; i < 3; i++) {
            o[i].campos2.y -= kCrouchDrop * 0.5f;
            o[i].campos2.z += g_crouch_cam_z_back;
        }
    const f32 ay = angle_y;
    const QfpsOfs& mid = o[1];
    v3 eye = V(mid.Campos), close = V(mid.campos2), target = V(mid.target);
    if (ay != 0.0f) {
        const QfpsOfs& end = ay > 0.0f ? o[0] : o[2];
        const f32 w = ay > 0.0f ? ay : -ay, w1 = 1.0f - w;
        eye = vmix(V(end.Campos), w, eye, w1);
        target = vmix(V(end.target), w, target, w1);
        close = vmix(V(end.campos2), w, close, w1);
    }
    if (angle_x != 0.0f) {
        const f32 c = cosf(angle_x), s = sinf(angle_x);
        auto yaw = [c, s](v3 v) { return shz_vec3_init(v.x * c + v.z * s, v.y, v.z * c - v.x * s); };
        eye = yaw(eye), close = yaw(close), target = yaw(target);
    }
    put(&out->Campos, eye);
    put(&out->campos2, close);
    put(&out->target, target);
    out->Roll = mid.Roll;
    out->Fovy = mid.Fovy;
    eng_cam_diag("of", out, sizeof(QfpsOfs) / 4);   // lane eng-e1m: the offset
}

// The wall probe, in player space with the base frame m: three probes from the close point toward the camera (the
// middle one and two shifted sideways by the near plane's half width, their shift interpolated along the probe), the
// camera pulled to the hit nearest the close point (plus the near distance toward the close point); when none hits,
// two short side probes at the camera (taken, as in the original, in player coordinates) add the near distance.
void CameraQuasiFPS::hitCheck(Mtx m, QfpsOfs* ofs, CameraParam* out)
{
    CAM_SVC("CameraQuasiFPS::hitCheck");
    const Frame f = frame_of(m);
    const FrameInverse inv = frame_inverse(f);
    const v3 eye = V(ofs->Campos), close = V(ofs->campos2), target = V(ofs->target);
    const v3 up = shz_vec3_init(0.0f, 1.0f, 0.0f);
    const f32 half = ZNEAR * tanf(ofs->Fovy * (kPi / 360.0f)) * 1.3333334f;
    const v3 side_close = vscale(vunit(vcross(vsub(close, target), up)), half);
    const v3 side_eye = vscale(vunit(vcross(vsub(eye, target), up)), half);
    const v3 near = vscale(vunit(vsub(close, eye)), ZNEAR);
    auto probe = [](v3 a, v3 b, v3* hit) {
        Vec from, to, h, n;
        put(&from, a), put(&to, b);
        if (!cameraHitCheck(&h, &n, &from, &to)) return false;
        *hit = V(h);
        return true;
    };
    v3 cand[4];
    int cands = 0;
    v3 hit;
    // the middle probe
    const v3 wa = frame_point(f, close), wb = frame_point(f, eye);
    v3 hitA, hitB, hitC;
    const bool fA = probe(wa, wb, &hit);
    if (fA) hitA = inverse_point(inv, hit);
    // the side probes: the hit back in player space, shifted back to the probe's centre line, plus the near distance
    auto side = [&](f32 sgn, v3* res) {
        const v3 a = frame_point(f, vadd(close, vscale(side_close, sgn))), b = frame_point(f, vadd(eye, vscale(side_eye, sgn)));
        if (!probe(a, b, &hit)) return false;
        const f32 along = vdist(hit, b) / vdist(a, b);
        const v3 shift = vadd(vscale(vsub(side_close, side_eye), along), side_eye);
        *res = vadd(vsub(inverse_point(inv, hit), vscale(shift, sgn)), near);
        return true;
    };
    const bool fB = side(-1.0f, &hitB);
    const bool fC = side(1.0f, &hitC);
    out->pos = ofs->Campos;
    out->at = ofs->target;
    out->roll = ofs->Roll;
    out->fovy = ofs->Fovy;
    if (fA || fB || fC) {
        // the nearest to the close point, in the original's order: the camera, the middle, the left, the right
        if (fA) cand[cands++] = hitA;
        if (fC) cand[cands++] = hitC;
        if (fB) cand[cands++] = hitB;
        v3 best = eye;
        f32 dmin = vdist(eye, close);
        for (int i = 0; i < cands; i++) {
            const f32 d = vdist(cand[i], close);
            if (d < dmin) dmin = d, best = cand[i];
        }
        put(&out->pos, best);
    } else if (probe(eye, vsub(eye, side_eye), &hit) || probe(eye, vadd(eye, side_eye), &hit)) {
        put(&out->pos, vadd(eye, near));
    }
    eng_cam_diag("hc", out, sizeof(CameraParam) / 4);   // lane eng-e1m: the wall probe's camera
}

// Keeps a site's close point at least 320 behind the player: when the camera-to-close line reaches the plane z = -320
// beyond the close point, the close point moves there (the line's parameter s = (-320 - eye.z) / (close.z - eye.z);
// the original normalises the line and compares lengths).
extern "C" void offsetCorrection(QfpsOfs* o)
{
    CAM_SVC("offsetCorrection");
    const v3 eye = V(o->Campos), d = vsub(V(o->campos2), eye);
    const f32 s = (-320.0f - eye.z) / d.z;
    if (s > 1.0f) put(&o->campos2, vadd(eye, vscale(d, s)));
}

// ---- the shoulder camera's tick (lane eng-e1n, ruling H-017.1) ----
// The follow: the shoulder camera's eye and target in player space follow the probed camera sideways (their x) at a
// fixed rate, directly in height and depth (y, z); a reset takes the probed camera as it is. Then both points into the
// world by the base frame. The service's own state (the original keeps the two points in statics of its move).
namespace {
struct ShoulderFollow {
    v3 eye, target;
} g_follow;
constexpr f32 kFollowRate = 0.6f;   // the share of the previous lateral position kept each tick
}   // namespace
void cam_shoulder_follow(const Mtx base, const CameraParam* probed, int reset, CameraParam* out)
{
    CAM_SVC("cam_shoulder_follow");
    const f32 keep = cam_control == 7 ? 0.5f : kFollowRate;   // control camfollow
    const v3 eye = V(probed->pos), target = V(probed->at);
    if (reset) {
        g_follow.eye = eye, g_follow.target = target;
    } else {
        const f32 take = 1.0f - keep;
        g_follow.eye = shz_vec3_init(g_follow.eye.x * keep + eye.x * take, eye.y, eye.z);
        g_follow.target = shz_vec3_init(g_follow.target.x * keep + target.x * take, target.y, target.z);
    }
    const Frame f = frame_of(base);
    put(&out->pos, frame_point(f, g_follow.eye));
    put(&out->at, frame_point(f, g_follow.target));
    out->roll = 0.0f;
    out->fovy = probed->fovy;
}

// The shoulder camera's tick. The original body (cam_qfps.cpp CameraQuasiFPS::move) holds its decisions and the
// follow's arithmetic in one function; the hosted unit's copy is made weak (game/Makefile SPLIT_UNITS) and this body
// is linked. The decisions are the hosted unit's own functions, called here: the camera type and its tables
// (checkCameraType), the site (checkFBLR) and the look angles (calcDepressionRatio); the debug camera (Debug_flg[1]
// 0x20000000) holds the site and the angles. The evaluation is the camera service's: the base frame, the offset blend,
// the wall probe, the follow and the frame. The rest is the record of those decisions: the site's offset tables
// (sites 0, 1 the ready table, 2, 3 the transition table; the odd sites the second row and the blend-from table's
// second side), the smoothing's rate while the player moves (status 2, 4, 8: the walking ratio) and its snap on a
// reset. The debug frustum drawing (debug_mode 0xF) is counted, not drawn.
#if !defined(E1_CAM_ORIG_QFPS_MOVE)   // control build only (game/Makefile CAM_EXTRA): the hosted body linked instead
void CameraQuasiFPS::move()
{
    checkCameraType();
    Mtx base;
    calcBaseMatrix(base);
    const bool debug_holds = (pG->Debug_flg[1] & 0x20000000) != 0;
    if (!debug_holds) m_site = checkFBLR();
    if (m_site <= 3) {
        const int side = m_site & 1;
        cur = (m_site < 2 ? blend_src : blend_dst)[2 * side];
        old = m_site < 2 ? g_readyOfs[15][side] : g_transOfs[6][side];
    }
    if (!debug_holds) calcDepressionRatio();
    QfpsOfs ofs;
    CameraParam probed;
    calcOffset(&ofs);
    hitCheck(base, &ofs, &probed);
    cam_shoulder_follow(base, &probed, reset, &cam.param);
    const u32 st = PlGetStatus();
    if (st == 2 || st == 4 || st == 8) CamSmth.m_ratio = m_walk_ratio;
    if (reset) CamSmth.m_flag |= 1;
    if (pG->debug_mode == 0xF) cam_cnt.debug_draws++;
    reset = 0;
}
#endif

// ---- the camera units' matrix work (lane eng-e1n, ruling H-017.1) ----
// cam_extra's camera bodies (the push-object camera's player-frame inverse, its candidate and offset transforms and its
// swing about the target; the scope's and the binocular's frames) reach their matrix maths here: game/Makefile binds
// the unit's PSMTXInverse, PSMTXMultVec, PSMTXMultVecSR, PSMTXIdentity and MtxRotAxisPosRad to these at link
// (objcopy --redefine-sym on the hosted object), so the bodies keep their decisions (which door, which side) and the
// evaluation is the camera service's. The engine's forms: the inverse from SH4ZAM's adjugate over the determinant
// (frame_inverse), points and directions through a frame, the turn about an axis through a point by Rodrigues' form
// (one sine / cosine pair; the original concatenates a translation, an axis-angle matrix and a translation).
extern "C" u32 cam_mtx_inverse(const Mtx s, Mtx inv)
{
    CAM_SVC("cam_mtx_inverse");
    cam_cnt.unit_math++;
    if (cam_control == 8) {   // control caminv: the inverse skipped (the identity)
        for (int r = 0; r < 3; r++)
            for (int c = 0; c < 4; c++) inv[r][c] = r == c ? 1.0f : 0.0f;
        return 1;
    }
    const Frame f = frame_of(s);
    const FrameInverse fi = frame_inverse(f);
    if (fi.inv_det == 0.0f) return 0;   // singular: inv untouched, as the original
    Frame r;
    // the inverse's axes: the adjugate's columns over the determinant (inverse_point's form); its position: the image
    // of the world origin
    r.left = vscale(fi.adj.col[0], fi.inv_det);
    r.up = vscale(fi.adj.col[1], fi.inv_det);
    r.forward = vscale(fi.adj.col[2], fi.inv_det);
    r.pos = inverse_point(fi, shz_vec3_init(0.0f, 0.0f, 0.0f));
    frame_put(inv, r);
    return 1;
}
extern "C" void cam_mtx_point(const Mtx m, const Vec* s, Vec* d)
{
    CAM_SVC("cam_mtx_point");
    cam_cnt.unit_math++;
    put(d, frame_point(frame_of(m), V(s)));
}
extern "C" void cam_mtx_dir(const Mtx m, const Vec* s, Vec* d)
{
    CAM_SVC("cam_mtx_dir");
    cam_cnt.unit_math++;
    put(d, frame_dir(frame_of(m), V(s)));
}
extern "C" void cam_mtx_identity(Mtx m)
{
    for (int r = 0; r < 3; r++)
        for (int c = 0; c < 4; c++) m[r][c] = r == c ? 1.0f : 0.0f;
}
// a turn of `rad` about the axis through `pos`: the frame's axes are the turned unit axes, its position pos - R pos
extern "C" void cam_mtx_turn_about(Mtx m, Vec* axis, Vec* pos, f32 rad)
{
    CAM_SVC("cam_mtx_turn_about");
    cam_cnt.unit_turns++;
    const v3 a = vunit(V(axis)), o = V(pos);
    const f32 c = cosf(rad), s = sinf(rad);
    auto turn = [&](v3 v) { return vadd(vadd(vscale(v, c), vscale(vcross(a, v), s)), vscale(a, vdot(a, v) * (1.0f - c))); };
    Frame f;
    f.left = turn(shz_vec3_init(1.0f, 0.0f, 0.0f));
    f.up = turn(shz_vec3_init(0.0f, 1.0f, 0.0f));
    f.forward = turn(shz_vec3_init(0.0f, 0.0f, 1.0f));
    f.pos = vsub(o, turn(o));
    frame_put(m, f);
}

// Every default table's first side (its three sites), ready tables 0..13 and transition tables 0..4, at room start.
void CameraQuasiFPS::offsetCorrection()
{
    for (int t = 0; t < 14; t++)
        for (int i = 0; i < 3; i++) ::offsetCorrection(&g_readyOfs[t][0][i]);
    for (int t = 0; t < 5; t++)
        for (int i = 0; i < 3; i++) ::offsetCorrection(&g_transOfs[t][0][i]);
}

// ==== the camera data (cam_ctrl.cpp) ====

namespace {
// a file offset made a pointer: base + offset
struct RelocBy {
    u32 base;
    template <class T> void operator()(T*& p) const { p = (T*) ((u32) p + base); }
};
}   // namespace

// "B40x" -> x (0..4); anything else (the "EMPT" placeholder included) -1.
int cameraDataVersion(char* data)
{
    if (data[0] == 'B' && data[1] == '4' && data[2] == '0' && data[3] >= '0' && data[3] <= '4') return data[3] - '0';
    return -1;
}

// The file's offsets made pointers in place (from version 2): each area record's area and cut, each area's points,
// each cut's key arrays. A record already holding a pointer (negative as an offset) stops it. Version 2 areas take
// attr 3; attr 8 also sets 0x20; up to version 3 attr2 = 1 and attr3 = 0xFF.
CameraDataHeader* CameraControl::calcAddr(CameraDataHeader* b)
{
    CAM_SVC("CameraControl::calcAddr");
    const int ver = cameraDataVersion(b->version);
    if (ver <= 1) return b;
    const u32 base = (u32) b;
    const RelocBy reloc = {base};
    CameraAreaRec* rec = (CameraAreaRec*) (b + 1);
    for (int i = 0; i < b->numArea; i++) {
        if ((s32) rec[i].area < 0) return b;
        reloc(rec[i].area);
        if (rec[i].cut) reloc(rec[i].cut);
    }
    CameraAreaInfo* area = (CameraAreaInfo*) (rec + b->numArea);
    for (int i = 0; i < b->numArea; i++) {
        reloc(area[i].points);
        if (ver == 2) area[i].attr = 3;
        if (area[i].attr & 8) area[i].attr |= 0x20;
        if (ver <= 3) area[i].attr2 = 1, area[i].attr3 = 0xFF;
    }
    CameraCut* cut = (CameraCut*) (area + b->numArea);
    for (int i = 0; i < b->numCut; i++) {
        reloc(cut[i].pos);
        reloc(cut[i].at);
        reloc(cut[i].roll);
        reloc(cut[i].fovy);
        reloc(cut[i].frames);
    }
    return b;
}
