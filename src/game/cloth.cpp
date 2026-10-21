// game/cloth.cpp: grid cloth simulation (esp4e sheets): a nx*ny grid of points joined by springs,
// pulled down by gravity, drawn as triangle strips with the lights of the room.

#include "light.h"
#include "global.h"
#include "model.h"
#include "camera.h"
#include "gx.h"
#include "tpl.h"
#include "cloth.h"
#include "math_sub.h"
#include "main_mem.h"
#include "trans_ot.h"

extern "C" {
// game/trans_lit.cpp
#if defined(RE4DC_CLOTH_LIGHT_ABI_FIX) && RE4DC_CLOTH_LIGHT_ABI_FIX && !defined(__PPC__)
void commonClothLightSet(cLight** list, int n, Vec* pos, f32 radius);
#else
void commonClothLightSet(cLight** list, int n, Vec pos, f32 radius);
#endif
void OSReport(const char* fmt, ...);
}

Cloth ClothWk[8];

// clothTrans builds a temporary cModel for the light setup. The real cModel is 0x320 bytes
// (see the KNOWN DEBT note in docs/matching.md: motion/atari fields still live in cEm/cObj), so an
// unused pad local follows it to keep the original frame layout until cModel carries them itself.

f32 K_PARAM = 7.5f;   // spring constant
f32 G_PARAM = 0.5f;   // gravity
f32 T_PARAM = 0.06f;  // time step
static f32 D_PARAM = 0.006f;  // unused (the 0.006 word after T_PARAM in .sdata; name unknown)

// Boot: marks the 8 cloth works free.
void ClothInit()
{
    int i;

    for (i = 0; i < 8; i++) {
        ClothWk[i].be_flag = 0;
    }
}

// Room start: frees every live cloth's grid memory and marks the works free.
void ClothRoomInit()
{
    ClothInit();
}

// Dead-stripped in the DOL (only its strings and its 0.0f pool survive, ahead of Cloth::Set's
// .rodata): a helper that allocates a Vec and normalises into it. Body unknown; this one
// reproduces the string order (__FILE__ before "VECNormalize:[%s/%d]") and the pool.
static Vec* clothAllocNormal(Vec* dir)
{
#line 120 "D:/Bio4/Prog/cloth.cpp"
    Vec* v = (Vec*) MEM_ALLOC(sizeof(Vec), 1, 13);
    VECNormalize(dir, v);
    return v;
}

// Builds an nx x ny cloth: allocates the vertex / normal / speed grids, lays the points out w
// apart horizontally and h vertically hanging from the top row at pos_ / ang, binds the texture
// (and TLUT) and the owner pointer p_; be_flag 0x31 = live, drawn. The top row (or the top four
// rows in the alternate pin mode) stays fixed.
void Cloth::Set(Vec ang, Vec pos_, u8 nx_, u8 ny_, f32 w, GXTexObj* tex_, f32 h, void* p_, f32 d, GXTlutObj* tlut_,
                int flag_)
{
    Vec zero = {0.0f, 0.0f, 0.0f};
    Vec n = {0.0f, 0.0f, 1.0f};
    Vec* pp;
    Vec* pn;
    Vec* ps;
    u32 rowSize;
    int i;
    int j;

    Wgap = w;
    Hgap = h;
    Scale = d;
    divH = nx_;
    divV = ny_;
    x70 = flag_;
    RotMatrix(mat, &ang);
    TransMatrix(mat, &pos_);
    rowSize = ny_ * sizeof(Vec);
#line 212 "D:/Bio4/Prog/cloth.cpp"
    m_pMem = MEM_ALLOC(nx_ * rowSize * 3, 1, 13);
    if (m_pMem == 0) {
        OSReport("ClothSet(): Can't allocate memory.\n");
        be_flag = 0;
    }
    pp = (Vec*) m_pMem;
    pVer = pp;
    pn = pp + nx_ * ny_;
    pNor = pn;
    ps = pp + nx_ * 2 * ny_;
    pSpd = ps;
    for (j = 0; j < ny_; j++) {
        for (i = 0; i < nx_; i++) {
            pp->x = i * Wgap;
            pp->y = -j * Hgap;
            if (flag_ != 0 && (j >= 0 && j <= 3)) {
                int m = i % 6;
                pp->z = sinf(m * 6.2831855f / 6.0f) * -2.0f;
            } else {
                pp->z = 0.0f;
            }
            *ps = zero;
            *pn = n;
            pp++;
            ps++;
            pn++;
        }
    }
    for (i = 0; i < 120; i++) {
        calcSpeed(0.9f);
        move();
    }
    center.x = Wgap * divH * 0.5f * Scale;
    center.y = 0.0f;
    center.z = 0.0f;
    PSMTXMultVec(mat, &center, &center);
    radius = Wgap * divH * 0.5f * Scale;
    tex = tex_;
    tlut = tlut_;
    pTobjA = p_;
    be_flag = 0x31;
    colR = 0xFF;
    colG = 0xFF;
    colB = 0xFF;
    colA = 0xFF;
    x74 = 0;
}

// Moves the cloth's hanging matrix.
void Cloth::SetPosAng(Vec ang, Vec pos_)
{
    RotMatrix(mat, &ang);
    TransMatrix(mat, &pos_);
}

// Frees the grid memory and the work.
void Cloth::Destroy()
{
    Mem_free(m_pMem);
    be_flag = 0;
}

// Relocates an in-file TPL in place (descriptor / image / CLUT offsets -> pointers), once.
void ClothCalcTplAddr(void* tpl)
{
    TEXPalette* pal = (TEXPalette*) tpl;
    TEXDescriptor* d;
    u32 i;

    if (pal == 0) {
        return;
    }
    if ((s32) pal->descriptorArray < 0) {
        return;
    }
    pal->descriptorArray = (TEXDescriptor*) ((u32) pal->descriptorArray + (u32) pal);
    for (i = 0; i < pal->numDescriptors; i++) {
        d = &pal->descriptorArray[i];
        d->textureHeader = (TEXHeader*) ((u32) pal + (u32) d->textureHeader);
        d->textureHeader->data = (void*) ((u32) pal + (u32) d->textureHeader->data);
        if (d->CLUTHeader != 0) {
            d->CLUTHeader = (CLUTHeader*) ((u32) pal + (u32) d->CLUTHeader);
            d->CLUTHeader->data = (void*) ((u32) pal + (u32) d->CLUTHeader->data);
        }
    }
}

// Initialises a GXTexObj (and TLUT for CI formats) from texture `no` of the TPL; 1 on success.
int ClothTexSetUp(void* tpl, GXTexObj* tex, int no, GXTlutObj* tlut)
{
    TEXDescriptor* d;
    TEXHeader* t;
    CLUTHeader* c;
    int ret = 0;

    ClothCalcTplAddr(tpl);
    d = TEXGet((TEXPalette*) tpl, 0);
    t = d->textureHeader;
    if (t->format >= 8 && t->format <= 9) {
        GXInitTexObjCI(tex, t->data, t->width, t->height, t->format, 0, 0, 0, 0);
        ret = 1;
        c = d->CLUTHeader;
        GXInitTlutObj(tlut, c->data, c->format, c->numEntries);
        GXLoadTlut(tlut, 0);
    } else {
        GXInitTexObj(tex, t->data, t->width, t->height, t->format, 0, 0, 0);
    }
    return ret;
}

// One simulation step of the speeds: spring forces (K_PARAM) toward each neighbour's rest
// distance (Wgap / Hgap), gravity G_PARAM, then the speed scaled by `damping`.
#if defined(RE4DC_CLOTH_SPRING) && RE4DC_CLOTH_SPRING
// GAME_CLOTH_SPRING (game30.mk; lane logic 2026-10-04; exact): every spring is evaluated from both of its ends
// (k toward k+1, then k+1 toward k), and the second evaluation is the first one negated bit for bit: p[a] - p[b]
// is -(p[b] - p[a]), the magnitude squares the components, the factor K (len - gap) / len is the same, and
// (-v) * f is -(v * f). Each spring's force is computed once, at its first end (the right spring of k, the down
// spring of row i), and the other end adds its negation (s + (-v) is s - v) in the source's order: left, right,
// up, down, gravity, damping. A neighbour the source skips (the interior of the pinned top row) has computed
// nothing, so its spring is evaluated as before.
static Vec clothDn[256];
static u8 clothDnOk[256];   // the spring below row i-1's point j: 0 not computed, 1 no force, 2 force in clothDn
#if RE4DC_CLOTH_SPRING == 2
#define calcSpeed calcSpeedSrc
#endif
#endif
#if !(defined(RE4DC_CLOTH_SPRING) && RE4DC_CLOTH_SPRING == 1)
void Cloth::calcSpeed(f32 damping)
{
    Vec v;
    Vec* p = pVer;
    Vec* s = pSpd;
    int i;
    int j;
    int k;
    int w;
    f32 len;

    for (i = 0; i < divV; i++) {
        for (j = 0; j < divH; j++) {
            if (i == 0 && j != 0 && j != divH - 1) {
                continue;
            }
            w = divH;
            k = j + i * w;
            if (j != 0) {
                PSVECSubtract(&p[k - 1], &p[k], &v);
                len = PSVECMag(&v);
                if (len > Wgap) {
                    PSVECScale(&v, &v, K_PARAM * (len - Wgap) / len);
                    PSVECAdd(&v, &s[k], &s[k]);
                }
            }
            if (j != divH - 1) {
                PSVECSubtract(&p[k + 1], &p[k], &v);
                len = PSVECMag(&v);
                if (len > Wgap) {
                    PSVECScale(&v, &v, K_PARAM * (len - Wgap) / len);
                    PSVECAdd(&v, &s[k], &s[k]);
                }
            }
            if (i != 0) {
                PSVECSubtract(&p[k - w], &p[k], &v);
                len = PSVECMag(&v);
                if (len > Hgap) {
                    PSVECScale(&v, &v, K_PARAM * (len - Hgap) / len);
                    PSVECAdd(&v, &s[k], &s[k]);
                }
            }
            if (i != divV - 1) {
                PSVECSubtract(&p[k + w], &p[k], &v);
                len = PSVECMag(&v);
                if (len > Hgap) {
                    PSVECScale(&v, &v, K_PARAM * (len - Hgap) / len);
                    PSVECAdd(&v, &s[k], &s[k]);
                }
            }
            s[k].y -= G_PARAM;
            PSVECScale(&s[k], &s[k], damping);
        }
    }
}
#endif
#if defined(RE4DC_CLOTH_SPRING) && RE4DC_CLOTH_SPRING
#if RE4DC_CLOTH_SPRING == 2
#undef calcSpeed
#endif
// One spring seen from point (px, py, pz): v = n - p, len = |v|; past the rest length `gap` the force
// v * (k (len - gap) / len) is added to the speed (ax, ay, az) and returned in *f. 2 = force, 1 = none.
// The same operations and operands as the source's PSVECSubtract / PSVECMag / PSVECScale / PSVECAdd; the
// point and the speed sit in registers (the source re-read them after every store through s).
static inline __attribute__((always_inline)) int clothSpring(const Vec* n, f32 px, f32 py, f32 pz, f32 gap, f32 kp,
                                                             f32& ax, f32& ay, f32& az, Vec* f)
{
    Vec v;
    f32 len;
    v.x = n->x - px;
    v.y = n->y - py;
    v.z = n->z - pz;
    len = PSVECMag(&v);
    if (len > gap) {
        const f32 r = kp * (len - gap) / len;
        f->x = v.x * r;
        f->y = v.y * r;
        f->z = v.z * r;
        ax = f->x + ax;
        ay = f->y + ay;
        az = f->z + az;
        return 2;
    }
    return 1;
}
#if RE4DC_CLOTH_SPRING == 2
extern "C" void re4dc_log(const char* fmt, ...);
static Vec clothChkIn[2048];
static Vec clothChkNew[2048];
static u32 clothChkCalls, clothChkMis, clothChkBig;
#endif
void Cloth::calcSpeed(f32 damping)
{
#if RE4DC_CLOTH_SPRING == 2
    const u32 npt = (u32) divH * divV;
    const int chk = npt <= 2048;
    if (chk) {
        __builtin_memcpy(clothChkIn, pSpd, npt * sizeof(Vec));
    } else {
        clothChkBig++;
    }
#endif
    const Vec* p = pVer;
    Vec* s = pSpd;
    const int w = divH;
    const int nv = divV;
    const f32 kp = K_PARAM;   // K / G / the gaps do not change during the step (s never aliases them)
    const f32 gp = G_PARAM;
    const f32 wg = Wgap;
    const f32 hg = Hgap;
    int i;
    int j;

    for (i = 0; i < nv; i++) {
        Vec rv;
        int rk = 0;   // the spring from the left neighbour: 0 not computed, 1 no force, 2 force in rv
        for (j = 0; j < w; j++) {
            Vec f;
            if (i == 0 && j != 0 && j != w - 1) {
                rk = 0;
                clothDnOk[j] = 0;
                continue;
            }
            const int k = j + i * w;
            const f32 px = p[k].x;
            const f32 py = p[k].y;
            const f32 pz = p[k].z;
            f32 ax = s[k].x;
            f32 ay = s[k].y;
            f32 az = s[k].z;
            if (j != 0) {
                if (rk == 2) {
                    ax = ax - rv.x;
                    ay = ay - rv.y;
                    az = az - rv.z;
                } else if (rk == 0) {
                    clothSpring(&p[k - 1], px, py, pz, wg, kp, ax, ay, az, &f);
                }
            }
            rk = 0;
            if (j != w - 1) {
                rk = clothSpring(&p[k + 1], px, py, pz, wg, kp, ax, ay, az, &rv);
            }
            if (i != 0) {
                const int dk = clothDnOk[j];
                if (dk == 2) {
                    ax = ax - clothDn[j].x;
                    ay = ay - clothDn[j].y;
                    az = az - clothDn[j].z;
                } else if (dk == 0) {
                    clothSpring(&p[k - w], px, py, pz, hg, kp, ax, ay, az, &f);
                }
            }
            clothDnOk[j] = 0;
            if (i != nv - 1) {
                clothDnOk[j] = clothSpring(&p[k + w], px, py, pz, hg, kp, ax, ay, az, &clothDn[j]);
            }
            ay -= gp;
            s[k].x = ax * damping;
            s[k].y = ay * damping;
            s[k].z = az * damping;
        }
    }
#if RE4DC_CLOTH_SPRING == 2
    if (chk) {
        __builtin_memcpy(clothChkNew, pSpd, npt * sizeof(Vec));
        __builtin_memcpy(pSpd, clothChkIn, npt * sizeof(Vec));
        calcSpeedSrc(damping);
        if (__builtin_memcmp(clothChkNew, pSpd, npt * sizeof(Vec)) != 0) {
            clothChkMis++;
        }
        if (++clothChkCalls % 256 == 0) {
            re4dc_log("CSPR calls=%u mismatch=%u big=%u\n", clothChkCalls, clothChkMis, clothChkBig);
        }
    }
#endif
}
#endif

// A free cloth work in *out; 0 when all 8 are used.
int PullCloth(Cloth** out)
{
    Cloth* c = ClothWk;
    int i;

    *out = 0;
    for (i = 0; i < 8; i++) {
        if ((c->be_flag & 1) == 0) {
            *out = c;
            return 1;
        }
        c++;
    }
    return 0;
}

// Integrates the speeds into the vertex positions (time step T_PARAM), skipping the pinned top
// row(s).
void Cloth::move()
{
    Vec v;
    int i;
    int j;

    for (i = 0; i < divV; i++) {
        if (x70 == 0) {
            if (i == 0) {
                continue;
            }
        } else if (i >= 0 && i <= 3) {
            continue;
        }
        for (j = 0; j < divH; j++) {
            int k = j + divH * i;
            PSVECScale(&pSpd[k], &v, T_PARAM);
            PSVECAdd(&pVer[k], &v, &pVer[k]);
        }
    }
}

// Recomputes the vertex normals from the neighbouring points for lighting.
void Cloth::calcNormal()
{
    Vec a;
    Vec b;
    Vec c;
    int i;
    int j;
    int k;

    for (i = 0; i < divV; i++) {
        for (j = 0; j < divH; j++) {
            u8 w = divH;
            k = j + i * w;
            if (i == divV - 1) {
                pNor[k] = pNor[k - w];
            } else if (j == w - 1) {
                pNor[k] = pNor[k - 1];
            } else {
                PSVECSubtract(&pVer[k + 1], &pVer[k], &a);
                PSVECSubtract(&pVer[k + w], &pVer[k], &b);
                PSVECCrossProduct(&b, &a, &c);
#line 622 "D:/Bio4/Prog/cloth.cpp"
                VECNormalize(&c, &pNor[k]);
            }
        }
    }
}

// Pushes grid point (x, y): adds `power` to its z speed and half to y (bullets / wind).
void Cloth::disturbance(f32 power, u32 x, u32 y)
{
    u32 idx = x + divH * y;

    pSpd[idx].z += power;
    pSpd[idx].y += power * 0.5f;
}

// Draw registration: queues clothTrans in OT 13 for every cloth flagged drawn (be_flag 0x20).
void ClothDraw()
{
    Cloth* c = ClothWk;
    int i;

    for (i = 0; i < 8; i++, c++) {
        if (c->be_flag & 0x20) {
            AddOtDirect(0xD, c, (void (*)()) clothTrans, 0, 0x1000, 0, 0.0f);
        }
    }
}

// Draws the cloth: a temporary cModel picks up the room lights (commonClothLightSet), then one
// two-sided textured triangle strip per row with the vertex normals.
void clothTrans(Cloth* pCL)
{
    Mtx texMtx;
    GXTexObj* tex = pCL->tex;
    void* tex2 = pCL->pTobjA;
    GXTlutObj* tlut = pCL->tlut;
    int nStages;
    int i;
    int j;
    int k;
    int t;
    f32 r;

    CameraSetProjection(1);
    PSMTXIdentity(texMtx);
    GXSetCullMode(0);
    GXSetZMode(1, 3, 1);
    GXSetNumChans(1);
    GXSetTevColorIn(0, 0xF, 8, 0xA, 0xF);
    GXSetTevColorOp(0, 0, 0, 2, 1, 0);
    GXSetTevAlphaIn(0, 7, 4, 5, 7);
    GXSetTevAlphaOp(0, 0, 0, 2, 1, 0);
    GXSetTevOrder(0, 0, 0, 4);
    cModel model;
    u8 modelPad[0x320 - sizeof(cModel)];  // see the cModel size note above
    PSMTXIdentity(model.mat);
    {
        static const Vec p0 = {0.0f, 0.0f, 0.0f};
        static const Vec p1 = {10000.0f, 10000.0f, 10000.0f};
        model.LightInfo.init2(1, 0, &p0, &p1, 0x10);
    }
    model.pos = pCL->center;
    LightMgr.setClothN(&model, 8);
    if (model.LightInfo.Size.x > model.LightInfo.Size.y) {
        r = model.LightInfo.Size.x;
    } else {
        r = model.LightInfo.Size.y;
    }
#if defined(RE4DC_CLOTH_LIGHT_ABI_FIX) && RE4DC_CLOTH_LIGHT_ABI_FIX && !defined(__PPC__)
    commonClothLightSet(model.LightInfo.pLight, 8, &model.pos, r);
#else
    commonClothLightSet(model.LightInfo.pLight, 8, model.pos, r);
#endif
    GXSetChanMatColor(4, pCL->color);
    GXSetNumTexGens(1);
    GXLoadTexObj(tex, 0);
    if (tlut != 0) {
        GXLoadTlut(tlut, 0);
    }
    GXLoadTexMtxImm(texMtx, 0x1E, 1);
    GXSetTexCoordGen2(0, 1, 4, 0x1E, 0, 0x7D);
    if (pCL->x74 == 0) {
        GXSetBlendMode(1, 4, 5, 0);
    } else {
        GXSetBlendMode(1, 1, 1, 0);
        GXSetZMode(1, 3, 0);
    }
    GXSetAlphaCompare(4, 4, 1, 4, 0xFF);
    nStages = 1;
    if (tex2 != 0) {
        nStages = 2;
        GXSetZCompLoc(0);
        GXSetBlendMode(1, 4, 5, 0);
        GXLoadTexObj((GXTexObj*) tex2, 1);
        GXSetTevOrder(1, 0, 1, 4);
        GXSetTevOp(1, 0);
    }
    GXSetNumTevStages(nStages);
    {
        Mtx scale;
        Mtx tmp;
        PSMTXScale(scale, pCL->Scale, pCL->Scale, pCL->Scale);
        PSMTXConcat(pCL->mat, scale, tmp);
        PSMTXConcat(pG->Cam.v_mat, tmp, scale);
        GXLoadPosMtxImm(scale, 0);
        PSMTXInverse(scale, tmp);
        PSMTXTranspose(tmp, scale);
        GXLoadNrmMtxImm(scale, 0);
    }
    GXSetCurrentMtx(0);
    GXClearVtxDesc();
    GXSetVtxDesc(9, 1);
    GXSetVtxDesc(10, 1);
    GXSetVtxDesc(13, 1);
    GXSetVtxAttrFmt(0, 9, 1, 4, 0);
    GXSetVtxAttrFmt(0, 10, 0, 4, 0);
    GXSetVtxAttrFmt(0, 13, 1, 4, 0);
    for (i = 0; i < pCL->divV - 1; i++) {
        GXBegin(0x98, 0, pCL->divH * 2);
        for (j = 0; j < pCL->divH * 2; j++) {
            Vec* pp;
            Vec* pn;
            if (j & 1) {
                k = pCL->divH * (i + 1) + j / 2;
                t = 1;
            } else {
                k = i * pCL->divH + j / 2;
                t = 0;
            }
            pp = &pCL->pVer[k];
            pn = &pCL->pNor[k];
            GXPosition3f32(pp->x, pp->y, pp->z);
            GXNormal3f32(pn->x, pn->y, pn->z);
            GXTexCoord2f32((f32) (j / 2) / (f32) (pCL->divH - 1), (f32) (i + t) / (f32) (pCL->divV - 1));
        }
    }
}
