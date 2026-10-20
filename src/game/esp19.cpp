// game/esp19.cpp: effect id 0x19, a 3D line from the effect position to the fixed world point Vec0,
// at most `max_laser_dist` (Vec1.x, default 12000) long, whose far end fades to black in
// proportion to the length used. Used for laser sight style beams and tracers.

#include "atari.h"
#include "re4dc_xm.h" // GAME_SH4ZAM_LOGIC (lane sh4zam-direct)
#include "gx.h"
#include "global.h"
#include "math_sub.h"
#include "esp.h"
#if defined(RE4DC_NATIVE_LASER) && RE4DC_NATIVE_LASER
#include "native_ui.h"
extern "C" void GXGetProjectionv(f32*);
extern "C" void GXGetViewportv(f32*);
#endif

struct Esp19Work {
    Vec Vec0;  // 0x00 end point of the line
    f32 max_laser_dist;     // 0x0C maximum length
};

// 3D line effect (laser sight / tracer): draws a line from the effect toward a target point,
// fading the far end.
class cEsp19 : public cEsp {
public:
    Esp19Work m_Free;  // 0xF8

    virtual void move();
    virtual int SetFreeWork(EspGenWork* gen, u32* seed);
};

// EspCreateTbl[0x19] factory.
cEsp* Esp19_Create()
{
    return new cEsp19;
}

// Base update only (no texture animation); marks the effect as never Z-culled (huge m_Radius,
// m_Flg bit1) since the line can span the whole view.
void cEsp19::move()
{
    if (CommonMove()) {
        m_Radius = 100000000.0f;
        m_Flg |= 2;
    }
}

// End point from Vec0, maximum length from Vec1.x (0 -> 12000 units).
int cEsp19::SetFreeWork(EspGenWork* gen, u32* seed)
{
    Esp19Work* w = &m_Free;

    w->Vec0 = *(Vec*)&gen->Vec0.x;
    if (gen->Vec1.x == 0.0f) {
        w->max_laser_dist = 12000.0f;
    } else {
        w->max_laser_dist = gen->Vec1.x;
    }
    return 1;
}

// Draws a 2-vertex GX line from p0 toward p1 in view matrix `mtx`, clipped to `len`, with the
// effect's blend mode; the end vertex colour is scaled by 1 - d / len. Alpha byte 0xFE in
// `color` disables the Z test.
static void Draw_line3d_local_222(Vec* p0, Vec* p1, Mtx mtx, u32 color, cEsp* esp, f32 len)
{
    Vec end;
    Vec dir;
    f32 rate = 1.0f;
    f32 d;
    u8 r, g, b, a;

    GXSetBlendMode(esp->xA4, esp->xA5, esp->xA6, esp->xA7);
    CameraCurrentProjection();
    GXSetCullMode(0);
    if ((color >> 24) == 0xFE) {
        GXSetZMode(0, 3, 1);
    } else {
        GXSetZMode(1, 3, 1);
    }
    GXSetNumChans(1);
    GXSetChanCtrl(4, 0, 0, 1, 0, 0, 2);
    GXSetNumTexGens(0);
    GXSetNumTevStages(1);
    GXSetTevOrder(0, 0xFF, 0xFF, 4);
    GXSetTevOp(0, 4);
    GXClearVtxDesc();
    GXSetVtxDesc(9, 1);
    GXSetVtxDesc(0xB, 1);
    GXSetVtxAttrFmt(0, 9, 1, 4, 0);
    GXSetVtxAttrFmt(0, 0xB, 1, 5, 0);
    GXLoadPosMtxImm(mtx, 0);
    GXSetCurrentMtx(0);
    r = (color >> 16) & 0xFF;
    g = (color >> 8) & 0xFF;
    b = color & 0xFF;
    a = 0xFF;

    end = *p1;
    PSVECSubtract(p1, p0, &dir);
    d = PSVECMag(&dir);
    if (d > len) {
#line 148 "D:/Bio4/Prog/esp19.cpp"
        VECNormalize(&dir, &dir);
        PSVECScale(&dir, &dir, len);
        PSVECAdd(p0, &dir, &end);
        d = len;
    }
    rate = 1.0f - d / len;

#if defined(RE4DC_NATIVE_LASER) && RE4DC_NATIVE_LASER
    // Carry the same final endpoints and vertex colours through the native
    // effect queue. Target/collision, generator and effect lifetime stay source.
    f32 P[7], V[6];
    GXGetProjectionv(P);
    GXGetViewportv(V);
    if (V[2] <= 0.0f || V[3] <= 0.0f) return;
    Vec v[2];
    RE4DC_XM_LOAD(mtx);
    RE4DC_XM_POINT(mtx, p0, &v[0]);
    RE4DC_XM_POINT(mtx, &end, &v[1]);
    const u32 col[2] = {0xff000000U | ((u32)r << 16) | ((u32)g << 8) | b,
        ((u32)(u8)(a * rate) << 24) | ((u32)(u8)(r * rate) << 16) |
        ((u32)(u8)(g * rate) << 8) | (u8)(b * rate)};
    const int ortho = P[0] != 0.0f;
    f32 t0 = 0.0f, t1 = 1.0f;
    if (!ortho) {
        const f32 near_d = P[6] / (P[5] - 1.0f), far_d = P[6] / P[5];
        const f32 d0 = -v[0].z, d1 = -v[1].z, dd = d1 - d0;
        if (dd == 0.0f) {
            if (d0 < near_d || d0 > far_d) return;
        } else {
            f32 enter = (near_d - d0) / dd, leave = (far_d - d0) / dd;
            if (enter > leave) { const f32 swap = enter; enter = leave; leave = swap; }
            if (enter > t0) t0 = enter;
            if (leave < t1) t1 = leave;
            if (t0 > t1) return;
        }
    }
    Re4dcEffectLine line;
    for (int i = 0; i < 2; ++i) {
        const f32 t = i ? t1 : t0;
        const f32 x = v[0].x + (v[1].x - v[0].x) * t;
        const f32 y = v[0].y + (v[1].y - v[0].y) * t;
        const f32 z = v[0].z + (v[1].z - v[0].z) * t;
        const f32 inv = ortho ? 1.0f : 1.0f / -z;
        const f32 px = ortho ? P[1] * x + P[2] : (P[1] * x + P[2] * z) * inv;
        const f32 py = ortho ? P[3] * y + P[4] : (P[3] * y + P[4] * z) * inv;
        line.x[i] = (V[2] * 0.5f * px + V[0] + V[2] * 0.5f) * 640.0f / V[2];
        line.y[i] = (-V[3] * 0.5f * py + V[1] + V[3] * 0.5f) * 480.0f / V[3];
        line.z[i] = inv;
        line.color[i] = 0;
        for (unsigned shift = 0; shift < 32; shift += 8) {
            const f32 c0 = (col[0] >> shift) & 255, c1 = (col[1] >> shift) & 255;
            line.color[i] |= (u32)(u8)(c0 + (c1 - c0) * t) << shift;
        }
    }
    line.src = esp->xA5 & 7; line.dst = esp->xA6 & 7;
    line.depth_test = (color >> 24) != 0xFE; line.blend_mode = esp->xA4;
    re4dc_effect_line(&line);
    return;
#endif
    GXBegin(0xB0, 0, 2);
    GXPosition3f32(p0->x, p0->y, p0->z);
    GXColor4u8(r, g, b, a);
    GXPosition3f32(end.x, end.y, end.z);
    GXColor4u8((u8)(r * rate), (u8)(g * rate), (u8)(b * rate), (u8)(a * rate));
}

// EspTransTbl[0x19]: packs the current colour and draws the line from m_Pos (plus the camera
// quake offset) to Vec0.
extern "C" void Esp19_Trans(cEsp19* esp)
{
    Esp19Work* w = &esp->m_Free;
    Vec p;
    u32 color;

    color = ((u32)esp->m_Col_r << 16) + ((u32)esp->m_Col_g << 8) + (u32)esp->m_Col_b + ((u32)esp->m_Col_a << 24);
    PSVECAdd(&esp->m_Pos, &pG->quake_ofs, &p);
    Draw_line3d_local_222(&p, &w->Vec0, pG->Cam.v_mat, color, esp, w->max_laser_dist);
}
