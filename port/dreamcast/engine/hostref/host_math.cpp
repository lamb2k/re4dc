// hostref (game side): the GX state the camera reads back (projection and viewport, kept as the SDK keeps
// them: the Dreamcast port's gx_stub.cpp does the same) and GXProject (the SDK's model-view, compact
// projection and viewport transform), sincosf (GCC may fuse a sinf/cosf pair of one argument into it:
// here it is the game's own fdlibm sinf and cosf, as newlib's sincosf is), and the GX FIFO and draw
// state calls that only drawing code reaches (no effect).
#include "hostref.h"
#include "types.h"
#include "main_sub.h"
#include "gx.h"

extern "C" {
float sinf(float);
float cosf(float);
// Through volatile pointers: GCC would otherwise fuse this very pair back into a call to sincosf.
static float (*volatile host_sinf)(float) = sinf;
static float (*volatile host_cosf)(float) = cosf;
void sincosf(float x, float* s, float* c)
{
    *s = host_sinf(x);
    *c = host_cosf(x);
}
}

static f32 g_projection[7];
static f32 g_viewport[6] = {0.0f, 0.0f, 512.0f, 448.0f, 0.0f, 1.0f};   // main_sub.cpp: Screen 512 x 448

extern "C" {
void GXSetViewport(f32 l, f32 t, f32 w, f32 h, f32 n, f32 f)
{
    g_viewport[0] = l; g_viewport[1] = t; g_viewport[2] = w; g_viewport[3] = h; g_viewport[4] = n; g_viewport[5] = f;
}
void GXGetViewportv(f32* vp) { for (int i = 0; i < 6; i++) vp[i] = g_viewport[i]; }
void GXSetProjection(const f32 mtx[4][4], int type)
{
    // The SDK keeps [type, m00, m02|m03, m11, m12|m13, m22, m23].
    g_projection[0] = (f32) type;
    g_projection[1] = mtx[0][0];
    g_projection[3] = mtx[1][1];
    g_projection[5] = mtx[2][2];
    g_projection[6] = mtx[2][3];
    if (type == 0) {
        g_projection[2] = mtx[0][2];
        g_projection[4] = mtx[1][2];
    } else {
        g_projection[2] = mtx[0][3];
        g_projection[4] = mtx[1][3];
    }
}
void GXGetProjectionv(f32* p) { for (int i = 0; i < 7; i++) p[i] = g_projection[i]; }
void GXProject(f32 x, f32 y, f32 z, const f32 mtx[3][4], const f32* pm, const f32* vp, f32* sx, f32* sy, f32* sz)
{
    f32 vx = mtx[0][0] * x + mtx[0][1] * y + mtx[0][2] * z + mtx[0][3];
    f32 vy = mtx[1][0] * x + mtx[1][1] * y + mtx[1][2] * z + mtx[1][3];
    f32 vz = mtx[2][0] * x + mtx[2][1] * y + mtx[2][2] * z + mtx[2][3];
    f32 px, py, pz, pw;
    if (pm[0] == 0.0f) {
        px = pm[1] * vx + pm[2] * vz;
        py = pm[3] * vy + pm[4] * vz;
        pz = pm[5] * vz + pm[6];
        pw = -vz;
        if (pw == 0.0f) pw = 1e-6f;
        pw = 1.0f / pw;
    } else {
        px = pm[1] * vx + pm[2];
        py = pm[3] * vy + pm[4];
        pz = pm[5] * vz + pm[6];
        pw = 1.0f;
    }
    *sx = vp[2] / 2.0f * px * pw + vp[0] + vp[2] / 2.0f;
    *sy = -(vp[3] / 2.0f) * py * pw + vp[1] + vp[3] / 2.0f;
    *sz = (vp[5] - vp[4]) * pz * pw + vp[5];
}
void PADControlMotor(int, u32) {}   // rumble
}

// The GameCube write-gather FIFO (an absolute linker symbol there): drawing code writes vertices into it.
volatile WGPipe GXWGFifo[1];
