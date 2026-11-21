// camera_svc.cpp: the native camera service (lane eng-svc4; rewritten by lane eng-e1j, rulings H-016.1 and H-016.2).
//
// The camera is one engine service. Its state is the renderer's camera record (eng_camera.h: the view matrix, the
// projection terms the renderer uses, the camera it evaluated), written once a tick by CameraMove after the hosted
// controller (cam_ctrl, cam_qfps, cam_extra: which camera, which cut, which routine, which target) has chosen the
// camera. The renderer reads the record in place; nothing copies the camera into a draw layout.
//
// This file: the frame's camera (CameraMove and the record), the projection, the view frustum (VIEW), the camera
// frames (every function of cam_sys.cpp: orientation from eye / target / roll or up, the roll read back, turns about an
// axis, dolly and distance), the stick in camera space, the screen ray, and the camera tracks of cuts and cutscenes
// (CameraMotion: converted once to motion-key rows, read by row; lane eng-e1n). cam_eval.cpp: the evaluation under the
// controller (the cut blend, the
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
#include "player.h"   // lane eng-e1m: the diagnosis lines read Leon's position and matrix
#undef fabsf
#include <stdio.h>   // lane eng-e1l: the record's trace line (snprintf)
#include "camera_svc.h"
#include "eng_camera.h"
#include "cam_math.h"
#include "skel_mk.h"   // lane eng-e1n: camera tracks in the motion-key form

using namespace camsvc;

extern "C" {
CameraCounters cam_cnt;
int cam_control;
EngCamera eng_cam;
EngPubCounters eng_pub;
int eng_pub_copy;
f32 eng_pub_stream[26];   // lane eng-e1n: PUBCOPY's destination
f32 sinf(f32);
f32 cosf(f32);
f32 tanf(f32);
f32 atan2f(f32, f32);
void* memset(void* dst, int c, unsigned int n);
}

namespace {

constexpr f32 kPi = 3.1415927f;
constexpr f32 kAspect = 1.33333333f;   // the frustum's and the projection's (VIEW_ASPECT)
// The renderer's planes (eng_camera.h): the record's depth terms and far plane, the engine's design constants. The
// game's ZNEAR / ZFAR (100, 1,000,000) are the behaviour's and the evaluation's (the frustum, the wall probe).
constexpr f32 kRendererNear = ENG_RENDERER_NEAR;
constexpr f32 kRendererFar = ENG_RENDERER_FAR;

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
// and the renderer's near / far planes (GX's form: x and y scale cot / aspect and cot, depth -n / (f - n) and
// -f n / (f - n)); the renderer's constant words (perspective, the 640 x 480 viewport, its far plane). Lane eng-e1l: the
// planes are the renderer's own constants (before, the game's ZNEAR / ZFAR, both zero in the E1 images, made the depth
// terms 0 x infinity: not numbers, so the renderer's near plane p23 / (p22 - 1) was not a number either).
int eng_cam_nearfar_control;   // RNEARFAR (control): far = near
EngCamCheck eng_cam_check;
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
    const f32 n = kRendererNear, f = eng_cam_nearfar_control ? kRendererNear : kRendererFar;
    const f32 k = 1.0f / (f - n);
    r.proj_type = 0.0f;
    r.p00 = cot / kAspect, r.p02 = 0.0f, r.p11 = cot, r.p12 = 0.0f;
    r.p22 = -n * k, r.p23 = -(f * n) * k;
    r.viewport[0] = 0.0f, r.viewport[1] = 0.0f, r.viewport[2] = 640.0f, r.viewport[3] = 480.0f;
    r.viewport[4] = 0.0f, r.viewport[5] = 1.0f;
    r.zfar = f;
    put((Vec*) r.eye, eye);
    put((Vec*) r.target, V(cam->param.at));
    r.roll = cam->param.roll, r.fovy = cam->param.fovy;
    r.tick++;
    if (r.frozen == 1) r.frozen = 2;
    if (eng_pub_copy) {   // PUBCOPY (control): a forced copy into a draw stream, counted (the selector must fail it)
        __builtin_memcpy(eng_pub_stream, &r, sizeof eng_pub_stream);
        eng_pub.camera++;
    }
}

// The frame's camera: the hosted controller (CamCtrl) decides it and it becomes pG->Cam while the camera is live and
// the debug camera does not hold it (an extra camera wins); the quake offset. Then the service: the field of view (0
// is an error: 50), the distance, the record and the frustum. Stop_flg 0x40000000 freezes the controller.
static void diag_inputs();
void CameraMove()
{
    cam_cnt.frames++;
    diag_inputs();   // lane eng-e1m: the diagnosis lines (no sink: nothing)
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
    eng_cam_diag("cm", &cam->param, sizeof(CameraParam) / 4);   // lane eng-e1m: the frame's camera chosen
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

// The record's finite check (eng_camera.h), once at the end of every tick: a word whose exponent bits are all ones is
// an infinity or not a number. Integer tests on the bits (the renderer and the game are built -ffast-math).
void eng_cam_check_tick(uint32_t tick)
{
    const uint32_t* w = (const uint32_t*) &eng_cam;
    const unsigned words = (unsigned) (&eng_cam.fovy - (const float*) &eng_cam) + 1;   // the 26 and eye .. fov
    eng_cam_check.ticks++;
    for (unsigned i = 0; i < words; i++)
        if ((w[i] & 0x7F800000u) == 0x7F800000u) {
            if (!eng_cam_check.nonfinite_ticks++) {
                eng_cam_check.first_tick = tick;
                eng_cam_check.first_word = i;
                eng_cam_check.first_bits = w[i];
            }
            return;
        }
}

// The diagnosis lines (eng_camera.h; lane eng-e1m): nothing unless a sink is set.
void (*eng_cam_diag_sink)(const char* line, unsigned n);
void eng_cam_diag(const char* tag, const void* words, unsigned n)
{
    if (!eng_cam_diag_sink) return;
    char b[640];
    int k = snprintf(b, sizeof b, "CD n=%lu %s", (unsigned long) cam_cnt.frames, tag);
    const uint32_t* w = (const uint32_t*) words;
    for (unsigned i = 0; i < n && k < (int) sizeof b - 12; i++)
        k += snprintf(b + k, sizeof b - k, "%c%08lx", i ? ',' : ' ', (unsigned long) w[i]);
    b[k++] = '\n';
    eng_cam_diag_sink(b, (unsigned) k);
}

// The camera's inputs as the frame's camera starts (the diagnosis lines): Leon's position, previous position and
// matrix, the shoulder camera's stored player matrix and floor normal, its state words, the smoothing's state.
static void diag_inputs()
{
    if (!eng_cam_diag_sink) return;
    uint32_t w[64];
    unsigned n = 0;
    auto f = [&](f32 v) { __builtin_memcpy(&w[n++], &v, 4); };
    auto i = [&](uint32_t v) { w[n++] = v; };
    const CameraQuasiFPS& q = CamCtrl.m_QuasiFPS;
    if (pPL) {
        f(pPL->pos.x), f(pPL->pos.y), f(pPL->pos.z);
        f(pPL->pos_old.x), f(pPL->pos_old.y), f(pPL->pos_old.z);
        for (int r = 0; r < 3; r++)
            for (int c = 0; c < 4; c++) f(pPL->mat[r][c]);
    }
    eng_cam_diag("pl", w, n);
    n = 0;
    for (int r = 0; r < 3; r++)
        for (int c = 0; c < 4; c++) f(q.m_pl_mat[r][c]);
    if (q.m_p_floor_norm) f(q.m_p_floor_norm->x), f(q.m_p_floor_norm->y), f(q.m_p_floor_norm->z);
    else i(0), i(0), i(0);
    eng_cam_diag("qm", w, n);
    n = 0;
    i(q.m_state), i((uint32_t) (int) q.m_search_cnt), i((uint32_t) (int) q.m_search_frame), i(q.reset), i(q.m_site);
    i((uint32_t) q.m_blend_count), i((uint32_t) q.m_blend_frame);
    f(q.blend_ratio), f(q.angle_x), f(q.angle_y), f(q.m_floor_ratio), f(q.m_walk_ratio);
    f(q.m_Aim.x), f(q.m_Aim.y), f(q.m_Aim.z);
    i(CamSmth.m_flag), f(CamSmth.m_ratio);
    f(CamSmth.param.pos.x), f(CamSmth.param.pos.y), f(CamSmth.param.pos.z);
    f(CamSmth.param.at.x), f(CamSmth.param.at.y), f(CamSmth.param.at.z);
    i((uint32_t) CamCtrl.r0), i((uint32_t) CamCtrl.r1);
    eng_cam_diag("qs", w, n);
    n = 0;   // the game's state words the player's move reads (Status_flg, Debug_flg, Stop_flg) and Leon's stat
    for (int k = 0; k < 4; k++) i(pG->Status_flg[k]);
    for (int k = 0; k < 4; k++) i(pG->Debug_flg[k]);
    i(pG->Stop_flg);
    i(pPL ? pPL->stat : 0);
    eng_cam_diag("gf", w, n);
}

// The record as a trace line (trace runs only): eye, target, roll (radians), fov (degrees) as bit patterns and the
// controller's decisions (area, camera cut, routine, cut blend frames left), as hostref/svc/svc4_dump.cpp writes them to
// cam.txt for the PC camera check.
int eng_cam_trace_line(char* buf, unsigned size, uint32_t tick)
{
    if (!eng_cam.tick) return 0;
    uint32_t b[8];
    __builtin_memcpy(b, eng_cam.eye, 12);
    __builtin_memcpy(b + 3, eng_cam.target, 12);
    __builtin_memcpy(b + 6, &eng_cam.roll, 4);
    __builtin_memcpy(b + 7, &eng_cam.fovy, 4);
    return snprintf(buf, size, "CAMLOG t=%lu e=%08lx,%08lx,%08lx g=%08lx,%08lx,%08lx r=%08lx f=%08lx d=%d,%d,%d,%d\n",
                    (unsigned long) tick, (unsigned long) b[0], (unsigned long) b[1], (unsigned long) b[2],
                    (unsigned long) b[3], (unsigned long) b[4], (unsigned long) b[5], (unsigned long) b[6],
                    (unsigned long) b[7], (int) CamCtrl.areaNo, (int) CamCtrl.cameraNo, (int) CamCtrl.r0,
                    (int) CamCtrl.interp.frame);
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

// ==== camera tracks (cam_motion.cpp's CameraMotion; lane eng-e1n, ruling H-017.2) ====
// A camera motion file (a header, then per part: an eye, target, roll or fov track of three axes, each {key count, key
// frames, keys of value and tangents}) is converted once, when a CameraMotion is made on it (the camera data is loaded:
// a cut's export or an event's file), into the engine's motion-key form (services/skeleton/skel_mk.h): an MkClip whose
// aux rows hold, for every integer frame 0 .. maxFrame, the camera's eight numbers (eye, target, roll in radians, fov in
// degrees), the last row the answer at and past the end. The rows are made by the skeleton's native key decoder
// (skel_mk_decode: the bracket by a binary search on the key frames, then the Hermite segment), the same decoder that
// fills an actor's rows. At run time the track is read by the motion-key evaluator's row rule (mk_row_of): the row of
// the frame. No key search, no key decoding, no history at run time. A camera motion's frame is an integer (every
// caller starts it at one and the clock steps whole frames); a frame without a row is not decoded: the camera holds
// and the sample is counted.
//
// The rows live in the camera service's track store (kTrackStore bytes, below), one block per live CameraMotion (its
// MkClip header, four joints, the rows), released when the CameraMotion is destroyed. A track the store cannot hold,
// a key block the decoder does not accept (keys not starting at frame 0 and rising, a layout without tangents) or a
// cut export the writer refused is not played: the motion ends at its first move with the camera held, counted
// (cam_cnt.key_errors) and logged.

void skel_mk_decode(const u8* keys, u32 type, f32 frame, f32 maxFrame, u32 flags, Vec* out);   // services/skeleton/skel.cpp




namespace {

constexpr u32 kTrackStore = 12288;   // bytes: the largest cut export (6 keys, 152 rows: 4,960 B) twice over
constexpr u32 kTrackStride = 8;      // floats a row: eye x y z, target x y z, roll, fov
constexpr u32 kTrackSlots = 4;
constexpr u32 kTrackHead = sizeof(MkClip) + 4 * sizeof(MkJoint);
alignas(32) u8 g_track_store[kTrackStore];
struct TrackSlot {
    const CameraMotion* owner;
    u32 off, bytes;   // in g_track_store; bytes 0: free
};
TrackSlot g_track_slot[kTrackSlots];
u32 g_track_peak;               // the store's most bytes in use at once
const u8* g_export_refused;     // the destination of the last cut export the writer refused (HermiteExport)

inline u32 rd16(const u8* p) { return p[0] | (p[1] << 8); }
constexpr u8 kKeyBytes[16] = {12, 8, 6, 0, 10, 6, 4, 0, 9, 5, 3, 0, 0, 0, 0, 0};   // with tangents; 0: not accepted

// a key block the decoder answers as the original does: three axes of keys at frame 0 first, strictly rising
bool track_keys_ok(const u8* p, u32 type)
{
    const u32 kb = kKeyBytes[type & 15];
    if (!kb) return false;
    for (int a = 0; a < 3; a++) {
        const u32 n = rd16(p);
        if (n == 0 || rd16(p + 2) != 0) return false;
        for (u32 i = 1; i < n; i++)
            if (rd16(p + 2 + 2 * i) <= rd16(p + 2 * i)) return false;
        p += 2 + 2 * n + n * kb;
    }
    return true;
}

TrackSlot* track_slot_of(const CameraMotion* cm)
{
    for (TrackSlot& s : g_track_slot)
        if (s.bytes && s.owner == cm) return &s;
    return 0;
}

void track_release(const CameraMotion* cm)
{
    if (TrackSlot* s = track_slot_of(cm)) s->bytes = 0, s->owner = 0;
}

// the lowest gap of the store that holds `bytes` (32-byte blocks), or 0
TrackSlot* track_claim(const CameraMotion* cm, u32 bytes)
{
    bytes = (bytes + 31) & ~31u;
    TrackSlot* free_slot = 0;
    for (TrackSlot& s : g_track_slot)
        if (!s.bytes && !free_slot) free_slot = &s;
    if (!free_slot) return 0;
    u32 at = 0;
    for (bool moved = true; moved;) {
        moved = false;
        for (const TrackSlot& s : g_track_slot)
            if (s.bytes && at < s.off + s.bytes && s.off < at + bytes) at = s.off + s.bytes, moved = true;
    }
    if (at + bytes > kTrackStore) return 0;
    free_slot->owner = cm, free_slot->off = at, free_slot->bytes = bytes;
    u32 used = 0;
    for (const TrackSlot& s : g_track_slot)
        if (s.bytes && s.off + s.bytes > used) used = s.off + s.bytes;
    if (used > g_track_peak) g_track_peak = used;
    return free_slot;
}

inline const MkClip* track_clip(const TrackSlot* s) { return (const MkClip*) (g_track_store + s->off); }

// The conversion: the motion file's parts into rows, frames 0 .. maxFrame (the last: each axis's last key).
bool track_convert(CameraMotion* cm, const MotionData* data, const u32* keys)
{
    const u8* d = (const u8*) data;
    const u32 n = d[2];
    const u16_un* info = (const u16_un*) (d + 3);
    const u8* part = d + 3 + 2 * n;
    const u32 maxFrame = (data->maxFrame & 0x3FFF) + 1;   // the clock's maxFrame (the original's + 1)
    for (u32 i = 0; i < n; i++)
        if (part[i] <= 3 && !(keys[i] && track_keys_ok((const u8*) keys[i], info[i] >> 12))) return false;
    const u32 rows = maxFrame + 1;
    TrackSlot* s = track_claim(cm, kTrackHead + rows * kTrackStride * sizeof(f32));
    if (!s) return false;
    MkClip* k = (MkClip*) (g_track_store + s->off);
    memset(k, 0, kTrackHead);
    k->maxFrame = (u16) maxFrame;
    k->n = 4;
    k->nAux = 4;
    k->auxStride = kTrackStride;
    k->oJoint = sizeof(MkClip);
    k->oAux = kTrackHead;
    MkJoint* j = (MkJoint*) ((u8*) k + k->oJoint);
    static const u16 kCol[4] = {0, 3, 6, 7};
    for (int c = 0; c < 4; c++) j[c].pno = (u8) c, j[c].src = MK_AUX, j[c].col = kCol[c];
    f32* row = (f32*) ((u8*) k + k->oAux);
    memset(row, 0, rows * kTrackStride * sizeof(f32));
    for (u32 i = 0; i < n; i++) {
        if (part[i] > 3) continue;
        j[part[i]].info = info[i];
        const u8* kb = (const u8*) keys[i];
        const u32 type = info[i] >> 12;
        // control camslope: the out-tangent of the second key of the first axis 1.25 times steeper (the key block is
        // the caller's: restored after the conversion)
        f32 saved = 0.0f;
        u8* slope = 0;
        if (cam_control == 6 && i == 0 && rd16(kb) > 1 && (type & 15) == 0) {
            slope = (u8*) kb + 2 + 2 * rd16(kb) + 12 + 8;
            __builtin_memcpy(&saved, slope, 4);
            const f32 v = saved * 1.25f;
            __builtin_memcpy(slope, &v, 4);
        }
        for (u32 f = 0; f < rows; f++) {
            Vec v;
            skel_mk_decode(kb, type, (f32) f, (f32) maxFrame, 2, &v);
            f32* r = row + f * kTrackStride;
            switch (part[i]) {
            case 0: r[0] = v.x, r[1] = v.y, r[2] = v.z; break;
            case 1: r[3] = v.x, r[4] = v.y, r[5] = v.z; break;
            case 2: r[6] = v.y; break;
            default: r[7] = v.y * 180.0f / kPi; break;
            }
        }
        if (slope) __builtin_memcpy(slope, &saved, 4);
        cam_cnt.keys += rows;
    }
    return true;
}

}   // namespace

// The motion work as the original sets it up (the key table relocated in place, as the data's other readers expect),
// then the conversion.
CameraMotion::CameraMotion(void* data, int hokan, int flags, f32 frame)
{
    CameraMotionWork* w = &m_info;
    memclr_asm(w, sizeof(CameraMotionWork));
    w->data = (MotionData*) data;
    w->maxFrame = (f32) ((((MotionData*) data)->maxFrame & 0x3FFF) + 1);
    w->nParts = w->data->nParts;
    w->partsInfo = (u16_un*) ((u8*) data + 3);
    w->partsNo = (u8*) data + (w->nParts * 2 + 3);
    u32* tbl = (u32*) ((((u32) w->partsNo + w->nParts) + 3) & ~3u) + 1;
    u32* keys = tbl;
    Re4dcMotionLease lease(data, &keys, tbl);
    if (!lease.external() && (s32) tbl[0] >= 0)
        for (int i = 0; i < w->nParts; i++) tbl[i] += (u32) data;
    w->keyTbl = tbl;
    w->hokan = hokan;
    w->flags = flags;
    w->frame = frame;
    base_mat = NULL;
    end = 0;
    track_release(this);   // a CameraMotion made again in the same storage
    const bool refused = (const u8*) data == g_export_refused;
    if (refused || !track_convert(this, w->data, keys)) {
        cam_cnt.key_errors++;
        pLog->err(0, 0, "CameraMotion: track not converted (%s)", refused ? "the export was refused" : "keys or store");
    }
}

CameraMotion::~CameraMotion()
{
    track_release(this);
    memset(this, 9, 0x200);
}

// The tracks at the current frame: the row (eye, target, roll, fov), the frame, the optional base matrix (an event
// placed in the room), then the clock; `end` when the sequence finished. A motion whose track was not converted ends
// at once with the camera held.
void CameraMotion::move()
{
    CAM_SVC("CameraMotion::move");
    cam_cnt.tracks++;
    CameraMotionWork* w = &m_info;
    const TrackSlot* s = track_slot_of(this);
    const MkClip* k = s ? track_clip(s) : 0;
    const int r = k ? mk_row_of(k, w->frame, w->maxFrame, 2) : -1;
    if (r < 0) {
        param = pG->Cam.param;
        end = 1;
        if (k) cam_cnt.key_errors++;   // a frame without a row
        return;
    }
    const f32* v = mk_aux(k) + (u32) r * k->auxStride;
    param.pos.x = v[0], param.pos.y = v[1], param.pos.z = v[2];
    param.at.x = v[3], param.at.y = v[4], param.at.z = v[5];
    param.roll = v[6];
    param.fovy = v[7];
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

// The track store's use (the report and the PC check): bytes in use now, the most at once, the store's size.
extern "C" void cam_track_store_use(u32* now, u32* peak, u32* size)
{
    u32 used = 0;
    for (const TrackSlot& s : g_track_slot)
        if (s.bytes) used += s.bytes;
    *now = used, *peak = g_track_peak, *size = kTrackStore;
}
// The cut writer's refusal (cam_eval.cpp HermiteExport): the CameraMotion made on that buffer next is not played.
extern "C" void cam_track_export_refused(const u8* buf, int refused)
{
    if (refused) g_export_refused = buf;
    else if (g_export_refused == buf) g_export_refused = 0;
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
