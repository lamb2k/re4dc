// camera_svc.cpp: the native camera service (lane eng-svc4; camera_svc.h, docs/engine/SERVICES.md section 28).
//
// What it owns:
//   - view.cpp, every function: the view frustum the renderer and the visibility tests read (VIEW View): six planes
//     and eight corners of the full and the half-width frustum in camera space (rebuilt when the field of view or the
//     far plane changes) and in world space (every frame, by the camera matrix), and the full frustum's bounding sphere;
//   - camera.cpp, every function: the frame's camera (CameraMove: the hosted controller decides the camera, then the
//     quake offset, the projection, the distance, the look-at matrix and the frustum), the projection type, the stick
//     direction in camera space, the screen ray;
//   - cam_motion.cpp, every function: the keyed camera tracks of cutscenes (CameraMotion: pos, at, roll and fov tracks
//     evaluated at the frame, an optional base matrix, the sequence clock);
//   - motion.cpp's HermiteInterpolation and its key decoders: one track's three axes at a frame, found from the per-axis
//     key history, in the ten key layouts;
//   - the evaluation functions inside the camera's behaviour units: CameraSetOrientationRoll / Up (cam_sys.cpp: the
//     orientation matrix from pos, at, roll or up), CameraAttachedToMotion::move (cam_extra.cpp: the camera a motion
//     carries, into the world, kept out of walls), and the rail spline of cam_ctrl.cpp (HermiteExport: a rail cut as
//     a keyed track; Parametrize: the B-spline fit; BSpline: the rail at a parameter).
// The camera's decisions (which camera, mode changes, rails, areas, look-at targets) stay the hosted controller's.
// Debug drawing (the rail) draws nothing; it is counted. The projection is not loaded into a graphics API: the renderer
// reads pG->Cam.ProjMat itself.
//
// Arithmetic: the original's, operation for operation and in its order (single precision, contraction off), so the PC
// reference compares bit for bit; matrices and vectors through the SDK interface (PSMTX / PSVEC / C_MTX).
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
#include "camera_svc.h"

extern "C" {
CameraCounters cam_cnt;
int cam_control;
f32 sinf(f32);
f32 cosf(f32);
void* memset(void* dst, int c, unsigned int n);
}

namespace {

constexpr f32 kPi = 3.1415927f;
constexpr f32 kAspect = 1.33333333f;   // the frustum's (VIEW_ASPECT)
constexpr f32 DEG = 0.017453292f;      // degrees to radians (cam_ctrl.cpp)

// the orientation matrix from its four columns (right, up, look, position)
inline void set_columns(Mtx m, const Vec* c0, const Vec* c1, const Vec* c2, const Vec* c3)
{
    m[0][0] = c0->x, m[1][0] = c0->y, m[2][0] = c0->z;
    m[0][1] = c1->x, m[1][1] = c1->y, m[2][1] = c1->z;
    m[0][2] = c2->x, m[1][2] = c2->y, m[2][2] = c2->z;
    m[0][3] = c3->x, m[1][3] = c3->y, m[2][3] = c3->z;
}

// the six planes of a frustum from its corners (outward normals, normalised)
void frustum_planes(ViewFrustum* b)
{
    static const u8 k[6][3] = {{0, 1, 3}, {0, 3, 4}, {0, 4, 1}, {1, 5, 2}, {2, 6, 3}, {4, 7, 5}};
    Vec t1, t2;
    for (int i = 0; i < 6; i++) {
        PSVECSubtract(&b->point[k[i][1]], &b->point[k[i][0]], &t1);
        PSVECSubtract(&b->point[k[i][2]], &b->point[k[i][0]], &t2);
        PSVECCrossProduct(&t1, &t2, &b->normal[i]);
        VECNormalize(&b->normal[i], &b->normal[i]);
    }
}

}   // namespace

// ==== the view frustum (view.cpp) ====

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

// Per frame: the camera-space frustum rebuilt when the field of view or the far plane changed, then oriented.
void VIEW::move()
{
    if (_old_fovy != pCam->param.fovy || _old_zfar != _zfar) initPerspective(pCam->param.fovy, kAspect, ZNEAR, _zfar);
    orientation();
    _old_fovy = pCam->param.fovy;
    _old_zfar = _zfar;
}

void VIEW::setFarPlane(f32 z) { _zfar = z; }

// The camera-space frustum: corners of the near and far rectangles (the half-width frustum: x and y halved), the
// planes, then the full frustum's bounding sphere (the circumsphere of a near corner and three far corners).
void VIEW::initPerspective(f32 fovy_, f32 aspect_, f32 znear_, f32 zfar_)
{
    cam_cnt.frustums++;
    _fovy = cam_control == 1 ? fovy_ + 1.0f : fovy_;
    _aspect = aspect_;
    _zfar = zfar_;
    _znear = znear_;
    const f32 t = sinf(_fovy * 0.5f * 3.1415927f / 180.0f) / cosf(_fovy * 0.5f * 3.1415927f / 180.0f);
    ViewFrustum* b = &localFull;
    const f32 h = _znear * t;
    f32 w = h * aspect_;
    f32 z = -_znear;
    b->point[0] = {w, h, z};
    b->point[1] = {-w, h, z};
    b->point[2] = {-w, -h, z};
    b->point[3] = {w, -h, z};
    const f32 h2 = _zfar * t;
    z = -_zfar;
    w = h2 * aspect_;
    b->point[4] = {w, h2, z};
    b->point[5] = {-w, h2, z};
    b->point[6] = {-w, -h2, z};
    b->point[7] = {w, -h2, z};
    frustum_planes(b);
    local = localFull;
    for (int i = 0; i < 8; i++) {
        local.point[i].x *= 0.5f;
        local.point[i].y *= 0.5f;
    }
    frustum_planes(&local);
    orientation();

    Vec q[4] = {localFull.point[0], localFull.point[4], localFull.point[5], localFull.point[6]};
    const f32 det = (q[1].x - q[0].x) * (q[2].y - q[1].y) * (q[3].z - q[2].z) +
                    (q[2].x - q[1].x) * (q[3].y - q[2].y) * (q[1].z - q[0].z) +
                    (q[3].x - q[2].x) * (q[1].y - q[0].y) * (q[2].z - q[1].z) -
                    (q[1].x - q[0].x) * (q[3].y - q[2].y) * (q[2].z - q[1].z) -
                    (q[2].x - q[1].x) * (q[1].y - q[0].y) * (q[3].z - q[2].z) -
                    (q[3].x - q[2].x) * (q[2].y - q[1].y) * (q[1].z - q[0].z);
    const f32 d0 = PSVECSquareMag(&q[0]) - PSVECSquareMag(&q[1]);
    const f32 d1 = PSVECSquareMag(&q[1]) - PSVECSquareMag(&q[2]);
    const f32 d2 = PSVECSquareMag(&q[2]) - PSVECSquareMag(&q[3]);
    ViewSphere* s = &sphere;
    s->center.x = (d0 * ((q[3].y - q[2].y) * (q[2].z - q[1].z) - (q[2].y - q[1].y) * (q[3].z - q[2].z)) +
                   d1 * ((q[1].y - q[0].y) * (q[3].z - q[2].z) - (q[3].y - q[2].y) * (q[1].z - q[0].z)) +
                   d2 * ((q[2].y - q[1].y) * (q[1].z - q[0].z) - (q[1].y - q[0].y) * (q[2].z - q[1].z))) /
                  (2.0f * det);
    s->center.y = (d0 * ((q[3].z - q[2].z) * (q[2].x - q[1].x) - (q[2].z - q[1].z) * (q[3].x - q[2].x)) +
                   d1 * ((q[1].z - q[0].z) * (q[3].x - q[2].x) - (q[3].z - q[2].z) * (q[1].x - q[0].x)) +
                   d2 * ((q[2].z - q[1].z) * (q[1].x - q[0].x) - (q[1].z - q[0].z) * (q[2].x - q[1].x))) /
                  (2.0f * det);
    s->center.z = (d0 * ((q[3].x - q[2].x) * (q[2].y - q[1].y) - (q[2].x - q[1].x) * (q[3].y - q[2].y)) +
                   d1 * ((q[1].x - q[0].x) * (q[3].y - q[2].y) - (q[3].x - q[2].x) * (q[1].y - q[0].y)) +
                   d2 * ((q[2].x - q[1].x) * (q[1].y - q[0].y) - (q[1].x - q[0].x) * (q[2].y - q[1].y))) /
                  (2.0f * det);
    s->radius = PSVECDistance(&s->center, &q[0]);
}

// Both frustums and the sphere into world space by the camera matrix.
void VIEW::orientation()
{
    cam_cnt.orients++;
    MtxPtr m = pG->Cam.mat;
    for (int i = 0; i < 6; i++) {
        PSMTXMultVecSR(m, &localFull.normal[i], &worldFull.normal[i]);
        PSMTXMultVecSR(m, &local.normal[i], &world.normal[i]);
    }
    for (int i = 0; i < 8; i++) {
        PSMTXMultVec(m, &localFull.point[i], &worldFull.point[i]);
        PSMTXMultVec(m, &local.point[i], &world.point[i]);
    }
    sphereWorld = sphere;
    PSMTXMultVec(m, &sphere.center, &sphereWorld.center);
}

// ==== the frame's camera (camera.cpp) ====

int ProjType = 1;

// The projection type (1 perspective, 2 orthographic); the renderer reads pG->Cam.ProjMat itself.
void CameraSetProjection(int type)
{
    ProjType = type;
    cam_cnt.projections++;
}

void CameraCurrentProjection() { CameraSetProjection(ProjType); }

int CameraGetProjection() { return ProjType; }

// Game start: a default camera (1000 up, 2000 back, fov 50), perspective.
void CameraGameInit()
{
    Vec at = {0.0f, 0.0f, 0.0f};
    Vec pos = {0.0f, 1000.0f, 2000.0f};
    CameraSetWithRoll(&pG->Cam, &pos, &at, 0.0f, 50.0f);
    CameraSetOrientationRoll(&pG->Cam);
    ProjType = 1;
    CameraRoomInit();
}

void CameraRoomInit() { CamDbg.m_move_gain = 1.0f; }

// The frame's camera: the hosted controller (CamCtrl) decides it and it becomes pG->Cam while the camera is live and
// the debug camera does not hold it (an extra camera wins); the quake offset; then the projection (a zero field of
// view is an error: 50), the distance, the look-at matrix and the frustum. Stop_flg 0x40000000 freezes the controller.
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
    if (cam->param.fovy == 0.0f) {
        pLog->err(0, 0, "CameraMove(): Fovy = 0.0f");
        cam->param.fovy = 50.0f;
    }
    if (ProjType == 1) C_MTXPerspective(cam->ProjMat, cam->param.fovy, 1.3333334f, ZNEAR, ZFAR);
    else if (ProjType == 2) C_MTXOrtho(cam->ProjMat, ORTHO_T, ORTHO_B, ORTHO_L, ORTHO_R, 0.0f, ZFAR);
    cam->dist = PSVECDistance(&cam->param.pos, &cam->param.at);
    C_MTXLookAt(cam->v_mat, &cam->param.pos, &cam->up, &cam->param.at);
    View.move();
    CameraDebugInformation();
}

// The stick as a world direction: by the camera matrix, or by the previous camera's while the stick is held through a
// camera cut (the run direction does not flip on a cut).
void CamStick2World(Camera* cam, JOY* joy, Vec* out)
{
    static Mtx mat_prev;
    static int carry_on = 0;
    Vec v = {(f32) joy->stickX, 0.0f, (f32) -joy->stickY};
    const bool held = v.x != 0.0f || v.y != 0.0f || v.z != 0.0f;
    if (CamCtrl.IsChangeCamera() && held) {
        __builtin_memcpy(mat_prev, CamCtrl.prev_mat, sizeof(Mtx));
        carry_on = 1;
    }
    if (!held) carry_on = 0;
    PSMTXMultVecSR(carry_on ? mat_prev : cam->mat, &v, out);
}

ViewFrustum* CameraViewFrustumPtr(Camera* cam)
{
    (void) cam;
    return &View.worldFull;
}

void CameraGetUpVec(Camera* cam, Vec* up) { *up = cam->up; }

void CameraGetLookVec(Camera* cam, Vec* look) { *look = cam->Look; }

void CameraGetLookVecInverse(Camera* cam, Vec* look)
{
    look->x = -cam->Look.x;
    look->y = -cam->Look.y;
    look->z = -cam->Look.z;
}

// The world ray through screen pixel (sx, sy) (640 x 480 units, z from the vertical field of view).
void CamPos2ScrnVec(Vec* out, f32 sx, f32 sy)
{
    f32 ang = pG->Cam.param.fovy;
    out->x = sx - Screen.width * 0.5f;
    out->y = -(sy - Screen.height * 0.5f);
    out->x *= 640.0f / Screen.width;
    ang = ang * 0.5f;
    ang = ang * kPi;
    ang = ang / 180.0f;
    out->y *= 480.0f / Screen.height;
    FSet(out->z, -(cosf(ang) * 240.0f / sinf(ang)));
    PSMTXMultVecSR(pG->Cam.mat, out, out);
}

// ==== orientation (cam_sys.cpp's evaluation functions) ====

// From pos / at keeping the current up: Look = pos - at, Right = up x Look, up made orthogonal.
void CameraSetOrientationUp(Camera* cam)
{
    cam_cnt.orient_cams++;
    PSVECSubtract(&cam->param.pos, &cam->param.at, &cam->Look);
    VECNormalize(&cam->Look, &cam->Look);
    PSVECCrossProduct(&cam->up, &cam->Look, &cam->Right);
    VECNormalize(&cam->Right, &cam->Right);
    PSVECCrossProduct(&cam->Look, &cam->Right, &cam->up);
    set_columns(cam->mat, &cam->Right, &cam->up, &cam->Look, &cam->param.pos);
}

// From pos / at with world up, right and up turned about the look axis by the roll. A vertical look keeps the old
// right vector (or x when it has none).
void CameraSetOrientationRoll(Camera* cam)
{
    cam_cnt.orient_cams++;
    Vec right;
    Vec up = {0.0f, 1.0f, 0.0f};
    Vec dir;
    Mtx m;
    PSVECSubtract(&cam->param.pos, &cam->param.at, &dir);
    if (dir.x != 0.0f || dir.z != 0.0f) {
        PSVECCrossProduct(&up, &dir, &right);
    } else {
        right = {cam->mat[0][0], cam->mat[1][0], cam->mat[2][0]};
        if (PSVECMag(&right) == 0.0f) right = {1.0f, 0.0f, 0.0f};
    }
    PSVECCrossProduct(&dir, &right, &up);
    PSMTXRotAxisRad(m, &dir, cam_control == 2 ? cam->param.roll + 0.01f : cam->param.roll);
    PSMTXMultVec(m, &right, &right);
    PSMTXMultVec(m, &up, &up);
    if (right.x != 0.0f || right.y != 0.0f || right.z != 0.0f) VECNormalize(&right, &right);
    if (up.x != 0.0f || up.y != 0.0f || up.z != 0.0f) VECNormalize(&up, &up);
    if (dir.x != 0.0f || dir.y != 0.0f || dir.z != 0.0f) VECNormalize(&dir, &dir);
    set_columns(cam->mat, &right, &up, &dir, &cam->param.pos);
    cam->up = up;
    cam->Look = dir;
    cam->Right = right;
}

// ==== keyed tracks: the Hermite key evaluator (motion.cpp's HermiteInterpolation) ====

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

// the values of keys i0 and i1 and their out- and in-tangents (a layout without tangents leaves them as they were;
// a missing layout reads nothing)
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

// One track's three axes at prm->frame. Each axis: n key frames then n keys; the key pair around the frame is searched
// from the axis's history index (kept unless flags bit 3; backwards with flags bit 0); a looping track (flags & 6 == 4)
// wraps once, another one holds its last key past the end. The pair, its tangents and the last bracket persist from
// axis to axis (a search that runs out blends the previous pair, as the original). Returns 1 when a history index was
// out of range.
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

// ==== cutscene camera tracks (cam_motion.cpp) ====

// Binds a camera motion file: frame count, track table, key offsets made pointers (once), key history cleared; blend
// ticks `hokan`, flags (bit 2 loop, bit 3 pause), start frame.
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

// Poisoned (memset 9) so a stale pointer shows.
CameraMotion::~CameraMotion() { memset(this, 9, 0x200); }

// The tracks at the current frame (pos, at, roll, fov in radians), the orientation, the optional base matrix (an event
// placed in the room), then the clock; `end` when the sequence finished.
void CameraMotion::move()
{
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
        PSMTXMultVec(*base_mat, &param.pos, &param.pos);
        PSMTXMultVec(*base_mat, &param.at, &param.at);
        PSMTXMultVec(*base_mat, &up, &up);
        CameraSetOrientationUp(this);
    }
    end = CameraSequenceCtrl(&m_info) == 4 ? 1 : 0;
}

// The clock: one frame a tick unless paused (flags bit 3); past the last frame it loops (flags bit 2: state 1) or ends
// (state 4).
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

// ==== the camera a motion carries (cam_extra.cpp's CameraAttachedToMotion::move) ====

// The motion's attached camera tracks (already evaluated with the pose) into the world by their parts' matrix; unless
// the motion is world-space (Mot_attr 0x200), the target is kept in front of the model and the eye out of the scenery.
void CameraAttachedToMotion::move()
{
    AttachCamera* ac = MOTION(m_pModel)->pAttachCam;
    if (ac == 0) return;
    cam_cnt.attached++;
    if (ac->parts[0] != 0xFF) {
        param.pos = ac->out[0];
        PSMTXMultVec(*ac->pMat, &param.pos, &param.pos);
    }
    if (ac->parts[1] != 0xFF) {
        param.at = ac->out[1];
        PSMTXMultVec(*ac->pMat, &param.at, &param.at);
    }
    if (ac->parts[2] != 0xFF) param.roll = ac->out[2].y;
    if (ac->parts[3] != 0xFF) param.fovy = ac->out[3].y * 180.0f / kPi;
    if (!(MOTION(m_pModel)->Mot_attr & 0x200)) {
        Mtx inv;
        Vec pos, at, d, to, from, hit, nrm;
        PSMTXInverse(m_pModel->mat, inv);
        PSMTXMultVec(inv, &param.pos, &pos);
        PSMTXMultVec(inv, &param.at, &at);
        if (at.z > 0.0f && pos.z < 0.0f) {   // the target behind the model's plane: moved onto it
            PSVECSubtract(&at, &pos, &d);
            PSVECScale(&d, &d, -pos.z / d.z);
            PSVECAdd(&pos, &d, &to);
            PSMTXMultVec(m_pModel->mat, &to, &param.at);
        }
        to = param.at;
        from = param.pos;
        if (cameraHitCheck(&hit, &nrm, &to, &from)) param.pos = hit;
    }
    CameraSetOrientationRoll(this);
}

// ==== the rail spline (cam_ctrl.cpp's evaluation functions) ====

namespace {
inline void put16(u8* p, u32 v)
{
    p[0] = (u8) v;
    p[1] = (u8) (v >> 8);
}
inline void put32(u8* p, u32 v) { __builtin_memcpy(p, &v, 4); }
inline void putf(u8*& p, f32 v)
{
    __builtin_memcpy(p, &v, 4);
    p += 4;
}
}   // namespace

// A rail cut as a camera motion file (the CameraMotion format): header, four tracks (pos, at, roll, fov in radians) of
// three axes, each key {value, in-tangent, out-tangent} (f32, layout 0), keys every 30 frames or at the cut's frames;
// tangents from the neighbouring keys. Returns the size.
int CameraControl::HermiteExport(CameraCut* cut, u8* p)
{
    cam_cnt.rails++;
    u8* buf = p;
    put16(p, (cut->num - 1) * 30);
    p += 2;
    *p++ = 4;
    for (int i = 0; i < 4; i++, p += 2) put16(p, i < 2 ? 4 : 2);
    for (int i = 0; i < 4; i++) *p++ = i;
    *p++ = 0;
    put32(p, 0);
    p += 4;
    u8* table = p;
    for (int i = 0; i < 4; i++, p += 4) put32(p, 0);
    const u8* frames = 0;
    for (int i = 0; i < 4; i++) {
        put32(table + 4 * i, p - buf);
        for (int j = 0; j < 3; j++) {
            put16(p, cut->num);
            p += 2;
            frames = p;
            for (int k = 0; k < cut->num; k++, p += 2) put16(p, cut->frames == NULL ? k * 30 : cut->frames[k]);
            for (int k = 0; k < cut->num; k++) {
                const int k1 = k + 1 > cut->num - 1 ? cut->num - 1 : k + 1;
                const int k0 = k - 1 < 0 ? 0 : k - 1;
                f32 v = 0.0f, v0 = 0.0f, v1 = 0.0f;
                switch (i) {
                case 0: v = (&cut->pos[k].x)[j], v0 = (&cut->pos[k0].x)[j], v1 = (&cut->pos[k1].x)[j]; break;
                case 1: v = (&cut->at[k].x)[j], v0 = (&cut->at[k0].x)[j], v1 = (&cut->at[k1].x)[j]; break;
                case 2: v = cut->roll[k], v0 = cut->roll[k0], v1 = cut->roll[k1]; break;
                case 3:
                    v = cut->fovy[k], v0 = cut->fovy[k0], v1 = cut->fovy[k1];
                    v1 *= DEG;
                    v *= DEG;
                    v0 *= DEG;
                    break;
                }
                putf(p, v);
                const f32 dt0 = (f32) (int) (rd16(frames + 2 * k) - rd16(frames + 2 * k0));
                const f32 dt1 = (f32) (int) (rd16(frames + 2 * k1) - rd16(frames + 2 * k));
                f32 tan;
                if (k == 0) tan = (v1 - v) / dt1;
                else if (cut->num - 1 == k) tan = (v - v0) / dt0;
                else tan = (dt1 * ((v - v0) / dt0) + dt0 * ((v1 - v) / dt1)) / (dt0 + dt1);
                tan *= dt0;
                putf(p, tan);
                putf(p, tan);
            }
        }
        for (int rem = (p - buf) % 4; rem != 0 && rem < 4; rem++) *p++ = 0;   // each track 4-byte aligned
    }
    put16(buf, rd16(frames + 2 * (cut->num - 1)));
    return p - buf;
}

// The B-spline of a rail cut (degree min(2, keys - 1)): the de Boor-Cox basis matrix inverted, the control points of
// pos, at, roll and fov solved from the keys (temporary buffers from the allocator).
void Parametrize(CameraCut* cut, CameraBSpline* bs)
{
    cam_cnt.rails++;
    bs->num = cut->num;
    if (bs->num <= 1) return;
    const int n = bs->num;
    f32* B = (f32*) MEM_ALLOC(sizeof(f32) * n * n, 1, 0xd);
    f32* Binv = (f32*) MEM_ALLOC(sizeof(f32) * n * n, 1, 0xd);
    f32* col[8];
    for (int c = 0; c < 8; c++) col[c] = (f32*) MEM_ALLOC(sizeof(f32) * n, 1, 0xd);
    bs->k = 2;
    if (bs->k > n - 1) bs->k = n - 1;
    for (int i = 0; i < n; i++) {
        col[0][i] = cut->pos[i].x, col[1][i] = cut->pos[i].y, col[2][i] = cut->pos[i].z;
        col[3][i] = cut->at[i].x, col[4][i] = cut->at[i].y, col[5][i] = cut->at[i].z;
        col[6][i] = cut->roll[i], col[7][i] = cut->fovy[i];
    }
    for (int i = 0; i < n; i++) de_Boor_Cox(n, NULL, bs->k, (f32) i, &B[n * i]);
    MtxNNInverse(n, B, Binv);
    f32* dst[8] = {bs->px, bs->py, bs->pz, bs->ax, bs->ay, bs->az, bs->roll, bs->fovy};
    for (int c = 0; c < 8; c++) MtxNNMultVecSR(n, n, Binv, col[c], dst[c]);
    Mem_free(B);
    Mem_free(Binv);
    for (int c = 0; c < 8; c++) Mem_free(col[c]);
}

// The rail at parameter bs->t: pos, at, roll and fov (the camera record cleared first).
void BSpline(CameraBSpline* bs, Camera* cam, int)
{
    cam_cnt.rails++;
    memclr_asm(cam, sizeof(Camera));
    de_Boor_CoxF(bs->num, NULL, bs->t, bs->k, bs->basis);
    for (int i = 0; i < bs->num; i++) {
        cam->param.at.x += bs->basis[i] * bs->ax[i];
        cam->param.at.y += bs->basis[i] * bs->ay[i];
        cam->param.at.z += bs->basis[i] * bs->az[i];
        cam->param.pos.x += bs->basis[i] * bs->px[i];
        cam->param.pos.y += bs->basis[i] * bs->py[i];
        cam->param.pos.z += bs->basis[i] * bs->pz[i];
        cam->param.roll += bs->basis[i] * bs->roll[i];
        cam->param.fovy += bs->basis[i] * bs->fovy[i];
    }
}

void CameraControl::debugDrawRail(CameraCut* cut)
{
    (void) cut;
    cam_cnt.debug_draws++;
}
