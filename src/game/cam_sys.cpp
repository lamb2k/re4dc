// game/cam_sys.cpp: Camera orientation maths shared by every camera routine. A Camera holds pos /
// at / roll / fovy (param) and the derived orientation matrix `mat` (columns Right, up, Look =
// pos - at). CameraSetOrientation* rebuild the matrix from the parameters; the Rot / Dolly /
// Distance helpers move pos or at and rebuild.

#include "types.h"
#include "re4dc_xm.h" // GAME_SH4ZAM_LOGIC (lane sh4zam-direct)
#include "vec.h"
#include "camera.h"
#include "db_log.h"
#include "math_sub.h"

// Column vectors -> matrix.
#define MTX_SET_COLUMNS(m, c0, c1, c2, c3)                                                    \
    (m)[0][0] = (c0)->x; (m)[1][0] = (c0)->y; (m)[2][0] = (c0)->z;                            \
    (m)[0][1] = (c1)->x; (m)[1][1] = (c1)->y; (m)[2][1] = (c1)->z;                            \
    (m)[0][2] = (c2)->x; (m)[1][2] = (c2)->y; (m)[2][2] = (c2)->z;                            \
    (m)[0][3] = (c3)->x; (m)[1][3] = (c3)->y; (m)[2][3] = (c3)->z

// Column `c` of a matrix as a vector.
static inline void getColumn(Mtx m, int c, Vec* v)
{
    v->x = m[0][c];
    v->y = m[1][c];
    v->z = m[2][c];
}

// Builds a matrix from four column vectors (right, up, look, position).
static inline void setColumns(Mtx m, Vec* c0, Vec* c1, Vec* c2, Vec* c3)
{
    MTX_SET_COLUMNS(m, c0, c1, c2, c3);
}

// Rebuilds mat from pos / at keeping the current `up`: Look = pos - at, Right = up x Look, up
// re-orthogonalised.
void CameraSetOrientationUp(Camera* cam)
{
    PSVECSubtract(&cam->param.pos, &cam->param.at, &cam->Look);
#line 33 "D:/Bio4/Prog/cam_sys.cpp"
    VECNormalize(&cam->Look, &cam->Look);
    PSVECCrossProduct(&cam->up, &cam->Look, &cam->Right);
#line 37 "D:/Bio4/Prog/cam_sys.cpp"
    VECNormalize(&cam->Right, &cam->Right);
    PSVECCrossProduct(&cam->Look, &cam->Right, &cam->up);
    setColumns(cam->mat, &cam->Right, &cam->up, &cam->Look, &cam->param.pos);
}

// Rebuilds mat from pos / at with world up, then rolls right / up about the look axis by
// param.roll; stores up / Look / Right. A vertical look direction keeps the old right vector.
void CameraSetOrientationRoll(Camera* cam)
{
    Vec right;
    Vec up = {0.0f, 1.0f, 0.0f};
    Vec dir;
    Mtx m;

    PSVECSubtract(&cam->param.pos, &cam->param.at, &dir);
    if (dir.x != 0.0f || dir.z != 0.0f) {
        PSVECCrossProduct(&up, &dir, &right);
    } else {
        getColumn(cam->mat, 0, &right);
        if (PSVECMag(&right) == 0.0f) {
            right.x = 1.0f;
            right.y = 0.0f;
            right.z = 0.0f;
        }
    }
    PSVECCrossProduct(&dir, &right, &up);
    PSMTXRotAxisRad(m, &dir, cam->param.roll);
    RE4DC_XM_LOAD(m);
    RE4DC_XM_POINT(m, &right, &right);
    RE4DC_XM_POINT(m, &up, &up);
    if (right.x != 0.0f || right.y != 0.0f || right.z != 0.0f) {
#line 91 "D:/Bio4/Prog/cam_sys.cpp"
        VECNormalize(&right, &right);
    }
    if (up.x != 0.0f || up.y != 0.0f || up.z != 0.0f) {
#line 92 "D:/Bio4/Prog/cam_sys.cpp"
        VECNormalize(&up, &up);
    }
    if (dir.x != 0.0f || dir.y != 0.0f || dir.z != 0.0f) {
#line 93 "D:/Bio4/Prog/cam_sys.cpp"
        VECNormalize(&dir, &dir);
    }
    setColumns(cam->mat, &right, &up, &dir, &cam->param.pos);
    cam->up = up;
    cam->Look = dir;
    cam->Right = right;
}

// Rebuilds mat from pos / at with world up and no roll.
void CameraSetOrientationZeroRoll(Camera* cam)
{
    Vec right;
    Vec up = {0.0f, 1.0f, 0.0f};
    Vec dir;

    PSVECSubtract(&cam->param.pos, &cam->param.at, &dir);
    if (dir.x != 0.0f || dir.z != 0.0f) {
        PSVECCrossProduct(&up, &dir, &right);
    } else {
        getColumn(cam->mat, 0, &right);
        if (PSVECMag(&right) == 0.0f) {
            right.x = 1.0f;
            right.y = 0.0f;
            right.z = 0.0f;
        }
    }
    PSVECCrossProduct(&dir, &right, &up);
#line 149 "D:/Bio4/Prog/cam_sys.cpp"
    VECNormalize(&right, &right);
#line 150 "D:/Bio4/Prog/cam_sys.cpp"
    VECNormalize(&up, &up);
#line 151 "D:/Bio4/Prog/cam_sys.cpp"
    VECNormalize(&dir, &dir);
    setColumns(cam->mat, &right, &up, &dir, &cam->param.pos);
    cam->up = up;
    cam->Look = dir;
    cam->Right = right;
}

// The camera's roll angle (radians): the camera's right vector expressed in the zero-roll frame.
f32 CameraGetRoll(Camera* cam)
{
    Vec v = {1.0f, 0.0f, 0.0f};
    Camera tmp;
    Mtx inv;

    tmp = *cam;
    CameraSetOrientationZeroRoll(&tmp);
    PSMTXInverse(tmp.mat, inv);
    PSMTXMultVecSR(inv, &v, &v);
    PSMTXMultVecSR(cam->mat, &v, &v);
    return atan2f(v.y, v.x);
}

// Rotates the camera (pos, at, up) by `rad` about the axis through `pos`, then rebuilds the
// matrix and recomputes param.roll.
void CameraRotAxisPosRad(Camera* cam, Vec* axis, Vec* pos, f32 rad)
{
    Mtx m;

    MtxRotAxisPosRad(m, axis, pos, rad);
    PSMTXMultVec(m, &cam->param.at, &cam->param.at);
    PSMTXMultVec(m, &cam->param.pos, &cam->param.pos);
    PSMTXMultVecSR(m, &cam->up, &cam->up);
    CameraSetOrientationUp(cam);
    cam->param.roll = CameraGetRoll(cam);
}

// Rotates the target around the camera position about the camera's own X / Y / Z axis (look
// around).
void CameraTargetRot(Camera* cam, char axis, f32 rad)
{
    Vec v;

    switch (axis) {
    case 'X':
    case 'x':
        getColumn(cam->mat, 0, &v);
        break;
    case 'Y':
    case 'y':
        getColumn(cam->mat, 1, &v);
        break;
    case 'Z':
    case 'z':
        getColumn(cam->mat, 2, &v);
        break;
    }
    CameraRotAxisPosRad(cam, &v, &cam->param.pos, rad);
}

// Rotates the camera position around the target about the camera's own X / Y / Z axis (orbit).
void CameraCamposRot(Camera* cam, char axis, f32 rad)
{
    Vec v;

    switch (axis) {
    case 'X':
    case 'x':
        getColumn(cam->mat, 0, &v);
        break;
    case 'Y':
    case 'y':
        getColumn(cam->mat, 1, &v);
        break;
    case 'Z':
    case 'z':
        getColumn(cam->mat, 2, &v);
        break;
    }
    CameraRotAxisPosRad(cam, &v, &cam->param.at, rad);
}

// Translates pos and at by `speed`.
void CameraDolly(Camera* cam, Vec* speed)
{
    PSVECAdd(&cam->param.pos, speed, &cam->param.pos);
    PSVECAdd(&cam->param.at, speed, &cam->param.at);
    CameraSetOrientationUp(cam);
}

// Moves the target to `dist` in front of the camera along the look axis.
void CameraTargetDistance(Camera* cam, f32 dist)
{
    Vec v;

    getColumn(cam->mat, 2, &v);
    PSVECScale(&v, &v, dist);
    PSVECSubtract(&cam->param.pos, &v, &cam->param.at);
    cam->dist = dist;
    CameraSetOrientationUp(cam);
}

// Moves the camera to `dist` behind the target along the look axis.
void CameraCamposDistance(Camera* cam, f32 dist)
{
    Vec v;

    getColumn(cam->mat, 2, &v);
    PSVECScale(&v, &v, dist);
    PSVECAdd(&cam->param.at, &v, &cam->param.pos);
    cam->dist = dist;
    CameraSetOrientationUp(cam);
}

// Sets all four parameters and rebuilds the orientation with roll.
void CameraSetWithRoll(Camera* cam, Vec* pos, Vec* at, f32 roll, f32 fovy)
{
    cam->param.pos = *pos;
    cam->param.at = *at;
    cam->param.roll = roll;
    cam->param.fovy = fovy;
    CameraSetOrientationRoll(cam);
}

// Dead-stripped by the original linker (STRIP_UNUSED); only its DF 0.0 pool remains in .rodata.
static int cam_sys_unused(f64 x)
{
    return x != 0.0;
}
