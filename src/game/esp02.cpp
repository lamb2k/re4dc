// game/esp02.cpp: effect id 0x02, a one-segment ribbon (strip) sprite: a quad of length
// Size_base_x along the effect's local -x and width Size_base_y, always turned to face the
// camera, with the alpha fading as the segment points at the camera. When the effect leaves its
// parent it keeps the parent matrix (ParMat) so its local motion stays in that frame.

#include "atari.h"
#include "light.h"
#include "gx.h"
#include "global.h"
#include "math_sub.h"
#include "esp.h"

#define ESP02_STRIP_NUM 1
#define ESP_STRIP_PTS_MAX 16

struct Esp02Work {
    Mtx ParMat;   // 0x00 parent matrix at the time the sprite left its parent
    Vec BasePos;  // 0x30 local position
};

// Single-segment camera-facing strip (a stretched sprite from pos along -x).
class cEsp02 : public cEsp {
public:
    Esp02Work m_Free;  // 0xF8

    virtual void move();
    virtual int SetFreeWork(EspGenWork* gen, u32* seed);
};

extern "C" {
void EspStrip02_setup(cEsp02* esp);
void esp02Trans_sub(cEsp02* esp);
}

// EspCreateTbl[0x02] factory.
cEsp* Esp02_Create()
{
    return new cEsp02;
}

// Own update (no position integration): captures the parent matrix on release, applies the scale
// and colour fades and life, advances the animation and rebuilds m_Mat = ParMat * Rot(m_Ang) *
// Trans(BasePos); m_Pos becomes the transformed base position.
void cEsp02::move()
{
    Esp02Work* w = &m_Free;

    if (parent != pEffParentWorld && m_Release_time != 0xFF && m_Release_time <= m_Life_time) {
        PSMTXCopy(parent->mat, w->ParMat);
        parent = pEffParentWorld;
    }
    if (m_Size_start_cnt <= m_Life_time) {
        m_Size_mul += m_Size_plus;
        m_Size_plus *= m_D_size_plus;
        if (m_Size_mul <= 0.0f) {
            PushEsp(this);
            return;
        }
    }
    if (ColorUpdate()) {
        if (m_Life_max != 0 && m_Life_max <= m_Life_time) {
            PushEsp(this);
            return;
        }
        m_Life_time++;
        if (!AnmMove()) {
            PushEsp(this);
            return;
        }
        PSMTXIdentity(m_Mat);
        RotMatrix(m_Mat, &m_Ang);
        TransMatrix(m_Mat, &w->BasePos);
        PSMTXConcat(w->ParMat, m_Mat, m_Mat);
        PSMTXMultVec(m_Mat, &w->BasePos, &m_Pos);
    }
}

#if defined(RE4DC_FX_STRIP21) && RE4DC_FX_STRIP21
extern "C" void re4dc_esp_strip21_color(GXColor);
#endif
// EspTransTbl[0x02]: GX setup then the strip geometry.
extern "C" void Esp02_Trans(cEsp02* esp)
{
    EspStrip02_setup(esp);
    esp02Trans_sub(esp);
}

// Builds the view-space matrix (view * parent * ParMat * local) into m_Mat, binds the texture
// pattern, blend mode and vertex formats for the strip. Screen-mode Parts_no is an error.
void EspStrip02_setup(cEsp02* esp)
{
    Esp02Work* w = &esp->m_Free;
    Mtx id;
    Mtx m;

    CameraCurrentProjection();
    if ((s8)esp->m_Parts_no >= -8 && (s8)esp->m_Parts_no <= -3) {
        pLog->err(0, 0, "EspStrip_Trans():SCREEN MODE is invalid.");
        PushEsp(esp);
        return;
    }
    PSMTXIdentity(esp->m_Mat);
    RotMatrix(esp->m_Mat, &esp->m_Ang);
    TransMatrix(esp->m_Mat, &w->BasePos);
    PSMTXConcat(w->ParMat, esp->m_Mat, esp->m_Mat);
    PSMTXConcat(pG->Cam.v_mat, esp->parent->mat, m);
    PSMTXConcat(m, esp->m_Mat, esp->m_Mat);
    PSMTXIdentity(id);
    GXLoadPosMtxImm(id, 0);
    GXSetCurrentMtx(0);
    EspTexSet(esp->m_Tex_id, esp->m_Ptn_no);
    esp->ChannelSet();
    GXSetBlendMode(esp->xA4, esp->xA5, esp->xA6, esp->xA7);
    esp->CommonStateSet();
    GXClearVtxDesc();
    GXSetVtxDesc(0, 1);
    GXSetVtxDesc(9, 1);
    GXSetVtxDesc(0xD, 1);
    GXSetVtxAttrFmt(0, 9, 1, 4, 0);
    GXSetVtxAttrFmt(0, 0xD, 1, 4, 0);
}

// Builds the segment from the origin to -Size_base_x in m_Mat space, widens it by Size_base_y / 2
// perpendicular to the view, sets the material colour with alpha x (1 - |dir.z|^8) and draws it
// through EspStrip_draw_poly.
void esp02Trans_sub(cEsp02* esp)
{
    Vec dir;
    Vec org;
    Vec pts[ESP_STRIP_PTS_MAX];
    Vec d;
    Vec tmp;
    Vec cross;
    Vec q[2];
    Vec v[4];
    Vec n2;
    f32 half;
    f32 nz;
    u32 i;

    dir.x = -esp->m_Size_base_x;
    dir.y = 0.0f;
    dir.z = 0.0f;
    PSMTXMultVecSR(esp->m_Mat, &dir, &dir);
    org.x = 0.0f;
    org.y = 0.0f;
    org.z = 0.0f;
    PSMTXMultVec(esp->m_Mat, &org, &org);
    pts[0] = org;
    pts[0].x += dir.x;
    pts[0].y += dir.y;
    pts[0].z += dir.z;
    pts[1] = org;
    for (i = 0; i < ESP02_STRIP_NUM; i++) {
        PSVECSubtract(&pts[i + 1], &pts[i], &d);
        tmp = pts[i];
        PSVECCrossProduct(&d, &tmp, &cross);
        if (cross.x == 0.0f && cross.y == 0.0f && cross.z == 0.0f) {
            continue;
        }
#line 243 "D:/Bio4/Prog/esp02.cpp"
        VECNormalize(&cross, &cross);
        half = esp->m_Size_base_y * 0.5f;
        PSVECScale(&cross, &q[0], half);
        PSVECScale(&cross, &q[1], -half);
        if (i == 0) {
            PSVECAdd(&pts[i], &q[0], &v[0]);
            PSVECAdd(&pts[i], &q[1], &v[1]);
        } else {
            v[0] = v[2];
            v[1] = v[3];
        }
        PSVECAdd(&pts[i + 1], &q[0], &v[2]);
        PSVECAdd(&pts[i + 1], &q[1], &v[3]);
#line 267 "D:/Bio4/Prog/esp02.cpp"
        VECNormalize(&d, &n2);
        nz = n2.z;
        if (nz < 0.0f) {
            nz = -nz;
        }
        nz = nz * nz;
        nz = nz * nz;
        nz = nz * nz;
        nz = 1.0f - nz;
        {
            GXColor c;

            c.r = (u8)esp->m_Col_r;
            c.g = (u8)esp->m_Col_g;
            c.b = (u8)esp->m_Col_b;
            c.a = (u8)(esp->m_Col_a * nz);
            GXSetChanMatColor(4, c);
#if defined(RE4DC_FX_STRIP21) && RE4DC_FX_STRIP21
            re4dc_esp_strip21_color(c);
#endif

        }
        EspStrip_draw_poly(esp, i, v, 1, 1);
    }
}

// Records the base position and an identity ParMat; screen-mode Parts_no is rejected.
int cEsp02::SetFreeWork(EspGenWork* gen, u32* seed)
{
    Esp02Work* w = &m_Free;

    w->BasePos = m_Pos;
    PSMTXIdentity(w->ParMat);
    if ((s8)m_Parts_no >= -8 && (s8)m_Parts_no <= -3) {
        pLog->err(0, 0, "EspStrip_Trans():SCREEN MODE is invalid.");
        return 0;
    }
    return 1;
}
