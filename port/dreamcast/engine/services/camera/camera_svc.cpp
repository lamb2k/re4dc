// camera_svc.cpp: the native camera service (lane eng-svc4; rewritten by lane eng-e1j, rulings H-016.1 and H-016.2).
//
// The camera is one engine service. Its state is the renderer's camera record (eng_camera.h: the view matrix, the
// projection terms the renderer uses, the camera it evaluated), written once a tick by CameraMove after the hosted
// controller (cam_ctrl, cam_qfps, cam_extra: which camera, which cut, which routine, which target) has chosen the
// camera. The renderer reads the record in place; nothing copies the camera into a draw layout.
//
// This file: the frame's camera (CameraMove and the record), the projection, the view frustum (VIEW), the camera
// frames (every function of cam_sys.cpp: orientation from eye / target / roll or up, the roll read back, turns about an
// axis, dolly and distance), the stick in camera space, the screen ray, and the keyed tracks of cutscenes (CameraMotion
// and its key evaluator, from lane eng-svc4). cam_eval.cpp: the evaluation under the controller (the cut blend, the
// smoothing, the rail, the area tests, the line-of-sight probe, the shoulder camera's frame, offsets and wall probe,
// the attached-motion camera, the data relocation).
//
// The engine's own code on SH4ZAM's types (cam_math.h). Same mathematics as the original game; the forms are the
// engine's: a frame is built from its look axis and a horizontal right axis and rolled by one sine / cosine pair (no
// axis-angle matrix), the frustum's planes and bounding sphere are closed forms of the half angles (no plane from three
// corners, no 3 x 3 circumsphere solve), the view matrix is the frame's transpose (no separate look-at build).
// include/math_sub.h defines a static fabsf (the SDK header's) that clashes with the C library's, which SH4ZAM's headers
// declare: renamed while the game headers are read (as services/math/math_svc.cpp does).
#define fabsf camera_svc_game_fabsf
#include "types.h"
#include "vec.h"
#include "global.h"
#include "math_sub.h"
#include "db_log.h"
#include "main_mem.h"
#include "camera.h"
#include "cam_ctrl.h"
#include "cam_extra.h"
#include "cam_motion.h"
#include "motion.h"
#include "model.h"
#include "view.h"
#include "widget.h"
#include "db_cam.h"
#include "joy.h"
#include "quake.h"
#include "main_sub.h"
#include "native_motion.h"
#undef fabsf
#include "camera_svc.h"
#include "eng_camera.h"
#include "cam_math.h"

using namespace camsvc;

extern "C" {
CameraCounters cam_cnt;
int cam_control;
EngCamera eng_cam;
EngPubCounters eng_pub;
int eng_pub_copy;
f32 sinf(f32);
f32 cosf(f32);
f32 tanf(f32);
f32 atan2f(f32, f32);
void* memset(void* dst, int c, unsigned int n);
}

namespace {

constexpr f32 kPi = 3.1415927f;
constexpr f32 kAspect = 1.33333333f;   // the frustum's and the projection's (VIEW_ASPECT)
constexpr f32 kRendererFar = 18750.0f; // the renderer's far plane when the game has none (ZFAR 0)

// ---- camera frames ----
// A camera's axes: right (the matrix's column 0), up (1), look = eye - target (2). The roll turns right and up about
// the look axis: right' = right cos + up sin, up' = up cos - right sin.
struct Axes {
    v3 right, up, look;
};

// From eye and target with world up and a roll. A horizontal right axis is up x look = (look.z, 0, -look.x); a vertical
// look keeps `keep` (the camera's previous right axis), or x when that is zero.
Axes axes_roll(v3 eye, v3 target, f32 roll, v3 keep)
{
    Axes a;
    const v3 d = vsub(eye, target);
    v3 r = (d.x != 0.0f || d.z != 0.0f) ? shz_vec3_init(d.z, 0.0f, -d.x) : keep;
    if (vzero(r)) r = shz_vec3_init(1.0f, 0.0f, 0.0f);
    a.look = vunit(d);
    a.right = vunit(r);
    a.up = vunit(vcross(a.look, a.right));
    if (roll != 0.0f) {
        const f32 c = cosf(roll), s = sinf(roll);
        const v3 r2 = vmix(a.right, c, a.up, s);
        a.up = vmix(a.up, c, a.right, -s);
        a.right = r2;
    }
    return a;
}

// From eye and target keeping an up direction: look = unit(eye - target), right = unit(up x look), up = look x right.
Axes axes_up(v3 eye, v3 target, v3 up)
{
    Axes a;
    a.look = vunit(vsub(eye, target));
    a.right = vunit(vcross(up, a.look));
    a.up = vcross(a.look, a.right);
    return a;
}

void put_axes(Camera* cam, const Axes& a)
{
    Frame f;
    f.left = a.right, f.up = a.up, f.forward = a.look, f.pos = V(cam->param.pos);
    frame_put(cam->mat, f);
    put(&cam->Right, a.right);
    put(&cam->up, a.up);
    put(&cam->Look, a.look);
}

inline v3 column(const Mtx m, int c) { return shz_vec3_init(m[0][c], m[1][c], m[2][c]); }

// A rotation of v by `rad` about the unit axis a (Rodrigues: v cos + (a x v) sin + a (a . v)(1 - cos)).
v3 turn(v3 v, v3 a, f32 c, f32 s) { return vadd(vadd(vscale(v, c), vscale(vcross(a, v), s)), vscale(a, vdot(a, v) * (1.0f - c))); }

}   // namespace

// ==== the camera frames (cam_sys.cpp: the whole unit is camera maths, the engine's) ====

void CameraSetOrientationRoll(Camera* cam)
{
    CAM_SVC("CameraSetOrientationRoll");
    cam_cnt.orient_cams++;
    const f32 roll = cam_control == 2 ? cam->param.roll + 0.01f : cam->param.roll;   // control camroll
    put_axes(cam, axes_roll(V(cam->param.pos), V(cam->param.at), roll, column(cam->mat, 0)));
}

void CameraSetOrientationZeroRoll(Camera* cam)
{
    CAM_SVC("CameraSetOrientationRoll");
    cam_cnt.orient_cams++;
    put_axes(cam, axes_roll(V(cam->param.pos), V(cam->param.at), 0.0f, column(cam->mat, 0)));
}

void CameraSetOrientationUp(Camera* cam)
{
    CAM_SVC("CameraSetOrientationRoll");
    cam_cnt.orient_cams++;
    put_axes(cam, axes_up(V(cam->param.pos), V(cam->param.at), V(cam->up)));
}

// The roll as the original measures it: the camera's frame applied to the zero-roll frame's x row, its angle in the
// world's x-y plane.
f32 CameraGetRoll(Camera* cam)
{
    const Axes z = axes_roll(V(cam->param.pos), V(cam->param.at), 0.0f, column(cam->mat, 0));
    const Frame f = frame_of(cam->mat);
    const v3 v = frame_dir(f, shz_vec3_init(z.right.x, z.up.x, z.look.x));
    return atan2f(v.y, v.x);
}

// The camera (target, eye, up) turned by `rad` about the axis through `pos`; the frame from the new up, the roll read
// back.
void CameraRotAxisPosRad(Camera* cam, Vec* axis, Vec* pos, f32 rad)
{
    const v3 a = vunit(V(axis)), o = V(pos);
    const f32 c = cosf(rad), s = sinf(rad);
    put(&cam->param.at, vadd(o, turn(vsub(V(cam->param.at), o), a, c, s)));
    put(&cam->param.pos, vadd(o, turn(vsub(V(cam->param.pos), o), a, c, s)));
    put(&cam->up, turn(V(cam->up), a, c, s));
    CameraSetOrientationUp(cam);
    cam->param.roll = CameraGetRoll(cam);
}

static int axis_column(char axis) { return axis == 'X' || axis == 'x' ? 0 : axis == 'Y' || axis == 'y' ? 1 : 2; }

void CameraTargetRot(Camera* cam, char axis, f32 rad)
{
    Vec v;
    put(&v, column(cam->mat, axis_column(axis)));
    CameraRotAxisPosRad(cam, &v, &cam->param.pos, rad);
}

void CameraCamposRot(Camera* cam, char axis, f32 rad)
{
    Vec v;
    put(&v, column(cam->mat, axis_column(axis)));
    CameraRotAxisPosRad(cam, &v, &cam->param.at, rad);
}

void CameraDolly(Camera* cam, Vec* speed)
{
    put(&cam->param.pos, vadd(V(cam->param.pos), V(speed)));
    put(&cam->param.at, vadd(V(cam->param.at), V(speed)));
    CameraSetOrientationUp(cam);
}

void CameraTargetDistance(Camera* cam, f32 dist)
{
    put(&cam->param.at, vsub(V(cam->param.pos), vscale(column(cam->mat, 2), dist)));
    cam->dist = dist;
    CameraSetOrientationUp(cam);
}

void CameraCamposDistance(Camera* cam, f32 dist)
{
    put(&cam->param.pos, vadd(V(cam->param.at), vscale(column(cam->mat, 2), dist)));
    cam->dist = dist;
    CameraSetOrientationUp(cam);
}

void CameraSetWithRoll(Camera* cam, Vec* pos, Vec* at, f32 roll, f32 fovy)
{
    cam->param.pos = *pos;
    cam->param.at = *at;
    cam->param.roll = roll;
    cam->param.fovy = fovy;
    CameraSetOrientationRoll(cam);
}

// ==== the view frustum (view.cpp) ====
// Camera space, looking down -z. For a frustum of half-angle tangents tx (x) and ty (y), the planes' outward normals are
// near (0, 0, 1), right (1, 0, tx), top (0, 1, ty), left (-1, 0, tx), bottom (0, -1, ty), far (0, 0, -1), unit length;
// the corners are (+-x, +-y, -z) at the near and the far distance (order: ++, -+, --, +-). The half-width frustum halves
// tx and ty. The full frustum's bounding sphere is centred on the axis, equally far from the near and the far corners.

VIEW View;
u8 ViewHit[0xD00];

void VIEW::gameInit(Camera* cam)
{
    pCam = cam;
    roomInit();
}

void VIEW::roomInit() { init(); }

void VIEW::init()
{
    initPerspective(pCam->param.fovy, kAspect, ZNEAR, ZFAR);
    orientation();
    _old_fovy = pCam->param.fovy;
    _old_zfar = _zfar;
}

void VIEW::move()
{
    if (_old_fovy != pCam->param.fovy || _old_zfar != _zfar) initPerspective(pCam->param.fovy, kAspect, ZNEAR, _zfar);
    orientation();
    _old_fovy = pCam->param.fovy;
    _old_zfar = _zfar;
}

void VIEW::setFarPlane(f32 z) { _zfar = z; }

static void frustum_local(ViewFrustum* b, f32 tx, f32 ty, f32 n, f32 f)
{
    static const s8 sx[4] = {1, -1, -1, 1}, sy[4] = {1, 1, -1, -1};
    for (int i = 0; i < 4; i++) {
        put(&b->point[i], shz_vec3_init(sx[i] * n * tx, sy[i] * n * ty, -n));
        put(&b->point[4 + i], shz_vec3_init(sx[i] * f * tx, sy[i] * f * ty, -f));
    }
    const f32 kx = 1.0f / __builtin_sqrtf(1.0f + tx * tx), ky = 1.0f / __builtin_sqrtf(1.0f + ty * ty);
    put(&b->normal[0], shz_vec3_init(0.0f, 0.0f, 1.0f));
    put(&b->normal[1], shz_vec3_init(kx, 0.0f, tx * kx));
    put(&b->normal[2], shz_vec3_init(0.0f, ky, ty * ky));
    put(&b->normal[3], shz_vec3_init(-kx, 0.0f, tx * kx));
    put(&b->normal[4], shz_vec3_init(0.0f, -ky, ty * ky));
    put(&b->normal[5], shz_vec3_init(0.0f, 0.0f, -1.0f));
}

void VIEW::initPerspective(f32 fovy_, f32 aspect_, f32 znear_, f32 zfar_)
{
    cam_cnt.frustums++;
    _fovy = cam_control == 1 ? fovy_ + 1.0f : fovy_;   // control camfov
    _aspect = aspect_;
    _zfar = zfar_;
    _znear = znear_;
    const f32 ty = tanf(_fovy * (kPi / 360.0f)), tx = ty * aspect_;
    frustum_local(&localFull, tx, ty, _znear, _zfar);
    frustum_local(&local, 0.5f * tx, 0.5f * ty, _znear, _zfar);
    orientation();
    // the sphere: centre (0, 0, c) with |near corner - c| = |far corner - c|
    const f32 n = _znear, f = _zfar;
    const f32 rn2 = n * n * (tx * tx + ty * ty), rf2 = f * f * (tx * tx + ty * ty);
    const f32 c = (rf2 + f * f - rn2 - n * n) / (2.0f * (n - f));
    sphere.center.x = sphere.center.y = 0.0f;
    sphere.center.z = c;
    sphere.radius = __builtin_sqrtf(rn2 + (n + c) * (n + c));
}

// Both frustums and the sphere into world space by the camera's frame.
void VIEW::orientation()
{
    cam_cnt.orients++;
    const Frame m = frame_of(pG->Cam.mat);
    for (int i = 0; i < 6; i++) {
        put(&worldFull.normal[i], frame_dir(m, V(localFull.normal[i])));
        put(&world.normal[i], frame_dir(m, V(local.normal[i])));
    }
    for (int i = 0; i < 8; i++) {
        put(&worldFull.point[i], frame_point(m, V(localFull.point[i])));
        put(&world.point[i], frame_point(m, V(local.point[i])));
    }
    sphereWorld = sphere;
    put(&sphereWorld.center, frame_point(m, V(sphere.center)));
}

// ==== the frame's camera and the record (camera.cpp) ====

int ProjType = 1;

void CameraSetProjection(int type)
{
    ProjType = type;
    cam_cnt.projections++;
}

void CameraCurrentProjection() { CameraSetProjection(ProjType); }

int CameraGetProjection() { return ProjType; }

void CameraGameInit()
{
    Vec at = {0.0f, 0.0f, 0.0f};
    Vec pos = {0.0f, 1000.0f, 2000.0f};
    CameraSetWithRoll(&pG->Cam, &pos, &at, 0.0f, 50.0f);
    ProjType = 1;
    CameraRoomInit();
}

void CameraRoomInit() { CamDbg.m_move_gain = 1.0f; }

// The record: the view matrix is the inverse of the camera's frame built from eye, up and target (rows right, up,
// look; translation -R eye); the projection terms of a perspective of the camera's field of view, the screen's aspect
// and the game's near / far planes (GX's form: x and y scale cot / aspect and cot, depth -n / (f - n) and -f n / (f - n));
// the renderer's constant words (perspective, the 640 x 480 viewport, its far plane).
static void record_write(const Camera* cam)
{
    EngCamera& r = eng_cam;
    if (r.frozen == 2) return;                                   // CAMSTALE (control): the first camera kept
    const Axes a = axes_up(V(cam->param.pos), V(cam->param.at), V(cam->up));
    const v3 eye = V(cam->param.pos);
    const v3 row[3] = {a.right, a.up, a.look};
    for (int i = 0; i < 3; i++) {
        r.view[i][0] = row[i].x, r.view[i][1] = row[i].y, r.view[i][2] = row[i].z;
        r.view[i][3] = -vdot(row[i], eye);
    }
    const f32 cot = 1.0f / tanf(cam->param.fovy * (kPi / 360.0f));
    const f32 k = 1.0f / (ZFAR - ZNEAR);
    r.proj_type = 0.0f;
    r.p00 = cot / kAspect, r.p02 = 0.0f, r.p11 = cot, r.p12 = 0.0f;
    r.p22 = -ZNEAR * k, r.p23 = -(ZFAR * ZNEAR) * k;
    r.viewport[0] = 0.0f, r.viewport[1] = 0.0f, r.viewport[2] = 640.0f, r.viewport[3] = 480.0f;
    r.viewport[4] = 0.0f, r.viewport[5] = 1.0f;
    r.zfar = ZFAR > 0.0f ? ZFAR : kRendererFar;
    put((Vec*) r.eye, eye);
    put((Vec*) r.target, V(cam->param.at));
    r.roll = cam->param.roll, r.fovy = cam->param.fovy;
    r.tick++;
    if (r.frozen == 1) r.frozen = 2;
    if (eng_pub_copy) {   // PUBCOPY (control): a forced copy into a draw stream, counted (the selector must fail it)
        static f32 stream[26];
        __builtin_memcpy(stream, &r, sizeof stream);
        eng_pub.camera++;
    }
}

// The frame's camera: the hosted controller (CamCtrl) decides it and it becomes pG->Cam while the camera is live and
// the debug camera does not hold it (an extra camera wins); the quake offset. Then the service: the field of view (0
// is an error: 50), the distance, the record and the frustum. Stop_flg 0x40000000 freezes the controller.
void CameraMove()
{
    cam_cnt.frames++;
    Camera* cam = &pG->Cam;
    CamCtrl.Check();
    if (!(pG->Stop_flg & 0x40000000)) {
        CamCtrl.Move();
        if ((pG->Status_flg[0] & 0x100) && !(pG->Debug_flg[0] & 0x10000000)) {
            pG->Cam = CamCtrl.camera;
            if (CamCtrl.m_pExtraCamera != 0) pG->Cam = *(Camera*) CamCtrl.m_pExtraCamera;
        }
        CamCtrl.m_pExtraCamera = 0;
        if (!(pG->Stop_flg & 0x10000)) QuakeMove();
    }
    CamDbg.move(cam, &Joy[1], 0);
    CAM_SVC("CameraMove (record, frustum)");
    if (cam->param.fovy == 0.0f) {
        pLog->err(0, 0, "CameraMove(): Fovy = 0.0f");
        cam->param.fovy = 50.0f;
    }
    if (ProjType != 1) cam_cnt.projections++;   // an orthographic request: the renderer draws perspective only
    cam->dist = vdist(V(cam->param.pos), V(cam->param.at));
    record_write(cam);
    View.move();
    CameraDebugInformation();
}

// The stick as a world direction: by the camera's frame, or by the previous camera's while the stick is held through a
// camera cut (the run direction does not flip on a cut).
void CamStick2World(Camera* cam, JOY* joy, Vec* out)
{
    static Mtx mat_prev;
    static int carry_on = 0;
    const v3 s = shz_vec3_init((f32) joy->stickX, 0.0f, (f32) -joy->stickY);
    const bool held = !vzero(s);
    if (CamCtrl.IsChangeCamera() && held) {
        __builtin_memcpy(mat_prev, CamCtrl.prev_mat, sizeof(Mtx));
        carry_on = 1;
    }
    if (!held) carry_on = 0;
    put(out, frame_dir(frame_of(carry_on ? mat_prev : cam->mat), s));
}

ViewFrustum* CameraViewFrustumPtr(Camera* cam)
{
    (void) cam;
    return &View.worldFull;
}

void CameraGetUpVec(Camera* cam, Vec* up) { *up = cam->up; }

void CameraGetLookVec(Camera* cam, Vec* look) { *look = cam->Look; }

void CameraGetLookVecInverse(Camera* cam, Vec* look) { put(look, vscale(V(cam->Look), -1.0f)); }

// The world ray through screen pixel (sx, sy) of the game's 640 x 480 screen: x and y about the centre, z from the
// vertical field of view (-240 cot(fov / 2)), through the camera's frame.
void CamPos2ScrnVec(Vec* out, f32 sx, f32 sy)
{
    const f32 half = pG->Cam.param.fovy * (kPi / 360.0f);
    v3 v = shz_vec3_init((sx - Screen.width * 0.5f) * (640.0f / Screen.width), -(sy - Screen.height * 0.5f) * (480.0f / Screen.height),
                         -(cosf(half) * 240.0f / sinf(half)));
    put(out, frame_dir(frame_of(pG->Cam.mat), v));
}

// ==== keyed tracks: the Hermite key evaluator (motion.cpp's HermiteInterpolation; lane eng-svc4, not rewritten) ====

namespace {

inline u32 rd16(const u8* p) { return p[0] | (p[1] << 8); }
inline f32 key_f32(const u8* d)
{
    f32 v;
    __builtin_memcpy(&v, d, 4);
    return v;
}
inline f32 key_s16(const u8* d) { return (f32) (s16) rd16(d) * 0.0001f; }
inline f32 key_s8(const u8* d) { return (f32) (s8) d[0] * 0.0001f; }

// key layouts: value field, tangent field (0 f32, 1 s16, 2 s8, 3 none), bytes a key; -1 bytes: not a layout
struct KeyLayout {
    u8 val, tan;
    s8 bytes;
};
constexpr KeyLayout kLayouts[16] = {
    {0, 0, 12}, {0, 1, 8}, {0, 2, 6}, {0, 0, -1}, {1, 0, 10}, {1, 1, 6}, {1, 2, 4}, {0, 0, -1},
    {2, 0, 9},  {2, 1, 5}, {2, 2, 3}, {0, 0, -1}, {0, 0, -1}, {0, 0, -1}, {0, 0, -1}, {0, 3, 4},
};
inline f32 key_field(const u8* d, int fmt) { return fmt == 0 ? key_f32(d) : fmt == 1 ? key_s16(d) : key_s8(d); }

void key_pair(u32 type, const u8* d, int i0, int i1, f32* v, f32* t)
{
    const KeyLayout& L = kLayouts[type & 15];
    if (L.bytes < 0) return;
    const int vb = L.val == 0 ? 4 : L.val == 1 ? 2 : 1;
    const int tb = L.tan == 0 ? 4 : L.tan == 1 ? 2 : 1;
    v[0] = key_field(d + i0 * L.bytes, L.val);
    v[1] = key_field(d + i1 * L.bytes, L.val);
    if (L.tan == 3) return;
    t[0] = key_field(d + i0 * L.bytes + vb + tb, L.tan);   // the key's out-tangent
    t[1] = key_field(d + i1 * L.bytes + vb, L.tan);        // the key's in-tangent
}

inline f32 hermite_eval(const f32* p, const f32* v, f32 t)
{
    const f32 t2 = t * t;
    const f32 t3 = t * t2;
    const f32 h01 = -(t3 + t3) + 3.0f * t2;
    const f32 h11 = t3 - t2;
    const f32 h10 = h11 - t2 + t;
    const f32 h00 = -h01 + 1.0f;
    return p[0] * h00 + p[1] * h01 + v[0] * h10 + v[1] * h11;
}

}   // namespace

int HermiteInterpolation(HermitePrm* prm, Vec* out, u16* hist)
{
    cam_cnt.keys++;
    f32 frame = prm->frame;
    const u8* p = prm->key;
    f32* o = (f32*) out;
    f32 r = 0.0f, f0 = 0.0f, f1 = 0.0f;
    f32 val[2], tan[2];
    int ret = 0;
    const KeyLayout& L = kLayouts[prm->type & 15];
    for (int axis = 0; axis < 3; axis++) {
        const int n = (int) rd16(p);
        const u8* frames = p + 2;
        const u8* data = p + n * 2 + 2;
        u16* hp = &hist[axis];
        p = data + (L.bytes < 0 ? -1 : n * L.bytes);
        int cnt = n;
        bool found = false;
        if (prm->maxFrame <= frame) {
            if ((prm->flags & 6) == 4) {
                frame -= prm->maxFrame;
                if (!(prm->flags & 8)) *hp = 0;
            } else {
                key_pair(prm->type, data, n - 1, 0, val, tan);
                cnt = 0;
                found = true;
                r = val[0];
            }
        }
        int idx = (prm->flags & 8) ? 0 : *hp;
        const int last = n - 1;
        if (idx > last) {
            pLog->err(0, 0, "H.I.(): axis=%d, hist=%d nFrm=%d, Invalid key history.", axis, idx, n);
            cam_cnt.key_errors++;
            idx = 0;
            ret = 1;
        }
        for (; cnt != 0; cnt--) {
            f0 = (f32) rd16(frames + 2 * idx);
            if (f0 == frame) {
                key_pair(prm->type, data, idx, 0, val, tan);
                r = val[0];
                if (!(prm->flags & 8)) *hp = idx;
                found = true;
                break;
            }
            if (f0 < frame) {
                const int nx = idx + 1 > last ? 0 : idx + 1;
                f1 = (f32) rd16(frames + 2 * nx);
                if (frame < f1) {
                    key_pair(prm->type, data, idx, nx, val, tan);
                    if (!(prm->flags & 8)) *hp = idx;
                    break;
                }
            }
            if ((prm->flags & 1) || f0 > frame) {
                if (--idx < 0) idx = last;
            } else {
                if (++idx > last) idx = 0;
            }
        }
        if (!found) r = hermite_eval(val, tan, (frame - f0) / (f1 - f0));
        o[axis] = r;
    }
    return ret;
}

// ==== cutscene camera tracks (cam_motion.cpp; lane eng-svc4) ====

CameraMotion::CameraMotion(void* data, int hokan, int flags, f32 frame)
{
    CameraMotionWork* w = &m_info;
    memclr_asm(w, sizeof(CameraMotionWork));
    w->data = (MotionData*) data;
    w->maxFrame = (f32) (((MotionData*) data)->maxFrame & 0x3FFF);
    w->maxFrame += 1.0f;
    w->nParts = w->data->nParts;
    w->partsInfo = (u16_un*) ((u8*) w->data + 3);
    w->partsNo = (u8*) w->data + (w->nParts * 2 + 3);
    u32* tbl = (u32*) ((u32) w->partsNo + w->nParts);
    tbl = (u32*) (((u32) tbl + 3) & ~3);
    tbl++;
    u32* keys = tbl;
    Re4dcMotionLease lease(data, &keys, tbl);
    if (!lease.external() && (s32) tbl[0] >= 0) {
        for (int i = 0; i < w->nParts; i++) tbl[i] += (u32) w->data;
    }
    w->keyTbl = tbl;
    for (int i = 0; i < w->nParts; i++) w->hist[i][0] = w->hist[i][1] = w->hist[i][2] = 0;
    w->hokan = hokan;
    w->flags = flags;
    w->frame = frame;
    w->state = 0;
    base_mat = NULL;
    end = 0;
}

CameraMotion::~CameraMotion() { memset(this, 9, 0x200); }

// The tracks at the current frame (pos, at, roll, fov in radians), the frame, the optional base matrix (an event placed
// in the room), then the clock; `end` when the sequence finished.
void CameraMotion::move()
{
    CAM_SVC("CameraMotion::move");
    cam_cnt.tracks++;
    HermitePrm prm;
    Vec pos, at, fov;
    Vec roll = {0.0f, 0.0f, 0.0f};
    CameraMotionWork* w = &m_info;
    u32* keys = w->keyTbl;
    Re4dcMotionLease lease(w->data, &keys, keys);
    prm.frame = w->frame;
    prm.maxFrame = w->maxFrame;
    prm.flags = 2;
    for (int i = 0; i < w->nParts; i++) {
        prm.type = w->partsInfo[i] >> 12;
        prm.key = (u8*) keys[i];
        Vec* dst = w->partsNo[i] == 0 ? &pos : w->partsNo[i] == 1 ? &at : w->partsNo[i] == 2 ? &roll : w->partsNo[i] == 3 ? &fov : 0;
        if (dst) HermiteInterpolation(&prm, dst, w->hist[i]);
    }
    param.pos = pos;
    param.at = at;
    param.roll = roll.y;
    param.fovy = fov.y * 180.0f / kPi;
    CameraSetOrientationRoll(this);
    if (base_mat) {
        const Frame b = frame_of(*base_mat);
        put(&param.pos, frame_point(b, V(param.pos)));
        put(&param.at, frame_point(b, V(param.at)));
        put(&up, frame_point(b, V(up)));
        CameraSetOrientationUp(this);
    }
    end = CameraSequenceCtrl(&m_info) == 4 ? 1 : 0;
}

u32 CameraSequenceCtrl(CameraMotionWork* w)
{
    if (!(w->flags & 8)) {
        if (w->frame >= w->maxFrame) {
            if (w->flags & 4) {
                w->state = 1;
                w->frame = 0.0f;
            } else {
                w->state = 4;
            }
        } else {
            w->frame += 1.0f;
        }
    }
    return w->state;
}
