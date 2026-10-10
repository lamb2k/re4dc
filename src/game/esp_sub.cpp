// game/esp_sub: the shared part of the effect sprites (D:/Bio4/Prog/esp_sub.cpp): the cEsp base
// class members (CommonMove life/motion/colour update, AnmMove texture animation, ChannelSet
// colour + distance fade, ApplyMatrix), the common sprite draw EspCommonTrans with its heat
// shimmer and frame-buffer ("nega") variants, and EspSeqSet, which turns one EspGenWork record
// of an effect sequence into a live esp (or an effect model through EfmSeqSet). EspEstSetSelect
// spawns one record of an est table directly (laser sight, gatling, ...).
#include "atari.h"
#include "light.h"
#include "gx.h"
#include "global.h"
#include "math_sub.h"
#include "esp.h"
#if defined(RE4DC_GAME) && !defined(__PPC__)
#include "native_effect_source.h"
#endif
#include "espgen.h"
#include "obj.h"
#include "scroll.h"
#include "rnd.h"
#include "main_sub.h"
#include "db_log.h"
#include "tpl.h"
#include "trans_ot.h"

// game/trans_lit.cpp
extern "C" void commonEspLightSet(cLight** list, int n);

int GetDrawTmpBufType();        // game/TmpBuf.cpp (C++ linkage)
extern GXTexObj g_Get_tex_obj;  // game/trans.cpp

extern "C" {
static void EspCommonTransShimmer(cEsp* esp, int type, u32 blur);
void EspCommonTransNega(cEsp* esp, u32 type);
f32 EspGetCameraPan();   // game/esp.cpp
int EspEstSetSelect(int owner, int id, int no, cEsp** out, int bNoSuspend);
void GetPosXY(Vec* p0, Vec* p1, Vec* p2, Vec* p3, f32 u, f32 v, Vec* out);
void Esp1b_SpTrans(cEsp* esp);
}

extern f32 ZNEAR;
extern f32 ZFAR;

#define DEG2RAD (3.14f / 180.0f)

#ifndef RE4DC_EFFECT_LEAN
#define RE4DC_EFFECT_LEAN 0
#endif
#ifndef RE4DC_EFFECT_SPRITES
#define RE4DC_EFFECT_SPRITES 0
#endif
#if defined(RE4DC_ESP_SPRITE_FAST) && RE4DC_ESP_SPRITE_FAST && !(RE4DC_EFFECT_LEAN && RE4DC_EFFECT_SPRITES)
#error ESP_SPRITE_FAST needs EFFECT_LEAN=1 and EFFECT_SPRITES=1
#endif
#ifndef RE4DC_EFFECT_PS2_HAZE
#define RE4DC_EFFECT_PS2_HAZE 0
#endif
#ifndef RE4DC_EFFECT_PS2_STREAK
#define RE4DC_EFFECT_PS2_STREAK 0
#endif
#ifndef RE4DC_EFFECT_FADE_CLAMP
#define RE4DC_EFFECT_FADE_CLAMP 0
#endif
#define RE4DC_PS2FX_DRAW (RE4DC_EFFECT_PS2_HAZE || RE4DC_EFFECT_PS2_STREAK)
#if RE4DC_PS2FX_DRAW || RE4DC_EFFECT_FADE_CLAMP
// D367 effect look knobs (effects30.mk EFFECT_PS2_HAZE / EFFECT_PS2_STREAK / EFFECT_FADE_CLAMP / EFFECT_PS2_TOGGLE).
// Render only: they change what a sprite draws, never an effect's state or a Rnd() draw. re4dc_ps2fx holds the
// active features (all built ones; EFFECT_PS2_TOGGLE builds start at none, X + START steps them, warp `fxmode`).
#if RE4DC_PS2FX_DRAW && !RE4DC_EFFECT_SPRITES
#error EFFECT_PS2_HAZE / EFFECT_PS2_STREAK need EFFECT_SPRITES=1
#endif
extern "C" void re4dc_log(const char* fmt, ...);
enum { PS2FX_CLAMP = 1, PS2FX_HAZE = 2, PS2FX_STREAK = 4 };
#define PS2FX_BUILT                                                                                                 \
    ((RE4DC_EFFECT_FADE_CLAMP ? PS2FX_CLAMP : 0) | (RE4DC_EFFECT_PS2_HAZE ? PS2FX_HAZE : 0) |                         \
     (RE4DC_EFFECT_PS2_STREAK ? PS2FX_STREAK : 0))
extern "C" {
#if defined(RE4DC_EFFECT_PS2_TOGGLE) && RE4DC_EFFECT_PS2_TOGGLE
u8 re4dc_ps2fx = 0;
#else
u8 re4dc_ps2fx = PS2FX_BUILT;
#endif
// VMU label: GC (as the base), GF (GC + the fade clamp), PH (PS2 haze), PS (PS2 haze + streak), ST (streak only).
const char* re4dc_ps2fx_label(void)
{
    const unsigned f = re4dc_ps2fx;
    return (f & PS2FX_HAZE) ? ((f & PS2FX_STREAK) ? "PS" : "PH") : (f & PS2FX_STREAK) ? "ST" : (f & PS2FX_CLAMP) ? "GF" : "GC";
}
void re4dc_ps2fx_set(unsigned f)
{
    re4dc_ps2fx = (u8) (f & PS2FX_BUILT);
    re4dc_log("ps2fx: %s (flags %u)\n", re4dc_ps2fx_label(), (unsigned) re4dc_ps2fx);
}
// The next look of GC -> GF -> PH -> PS (the states this build has).
void re4dc_ps2fx_cycle(void)
{
    static const u8 seq[4] = {0, PS2FX_CLAMP, PS2FX_CLAMP | PS2FX_HAZE, PS2FX_CLAMP | PS2FX_HAZE | PS2FX_STREAK};
    int cur = 0;
    for (int i = 0; i < 4; ++i) {
        if ((seq[i] & PS2FX_BUILT) == re4dc_ps2fx) {
            cur = i;
        }
    }
    for (int k = 1; k <= 4; ++k) {
        const u8 c = (u8) (seq[(cur + k) & 3] & PS2FX_BUILT);
        if (c != re4dc_ps2fx) {
            re4dc_ps2fx_set(c);
            return;
        }
    }
}
}
#endif
#if RE4DC_EFFECT_SPRITES
// D367 EFFECT_SPRITES (effects30.mk): the approved effect classes as native PVR sprites. Reads
// game state only (m_Mat, the texture work, ChannelSet's colour, the current GX projection).
#include "native_ui.h"
extern "C" void GXGetProjectionv(f32*);
#ifndef RE4DC_WATER45_NATIVE
#define RE4DC_WATER45_NATIVE 0
#endif
#if RE4DC_WATER45_NATIVE
extern "C" int re4dc_water45_hides(const f32 (*corner)[3]);   // espgen45.cpp
#endif
extern "C" void GXGetViewportv(f32*);
static GXColor s_effect_col; // ChannelSet's final material colour (GXSetChanMatColor)
static int EspSpriteEligible(cEsp* esp)
{
    // Et0a hanging lamps use 0x5e for their source flame/smoke sprites, including
    // the impact fire. Keep the existing class, mask and blend restrictions.
    const u32 owner = esp->info.owner;
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
    // EFFECT_ROOM (bit mask, effects30.mk): plus the room's own effects. 1: est sets of the room owner
    // (0x01; r101's pyre); 2: the room effect sets SstSet starts at room init (0xd0; glows, light
    // shafts, smoke) apart from 4: their haze particles (id 0x15) and mist sheets (id 0x48).
    int room = 0;
    if (owner == 0x01) {
        room = RE4DC_EFFECT_ROOM & 1;
    } else if (owner == 0xD0) {
        room = RE4DC_EFFECT_ROOM & ((esp->m_Id == 0x15 || esp->m_Id == 0x48) ? 4 : 2);
    }
    if (!room && !(owner == 0 || owner == 0x10 || (owner >= 0x34 && owner <= 0x4F) || owner == 0x5E)) {
        return 0;
    }
#else
    if (!(owner == 0 || owner == 0x10 || (owner >= 0x34 && owner <= 0x4F) || owner == 0x5E)) {
        return 0; // muzzle flash (WEPxx), the shot's core effects, blood (EM10)
    }
#endif
    if ((esp->m_Tool_flg & (0x4000 | 0x10000)) || (esp->m_Flg & 0x10) || esp->xA4 != 1) {
        return 0; // mask stage, texture-render target, Esp1b spline, non-blend modes
    }
    return 1;
}
#if RE4DC_PS2FX_DRAW
#include "player.h"
#if RE4DC_EFFECT_PS2_HAZE
// EFFECT_PS2_HAZE: the room generator's camera haze (Esp15, owner 0xd0) drawn as the PS2 release draws it
// (SLUS-211.34 rNNN.dat EFF): a fixed subset of the live sprites (pool slot % every) inside the PS2's smaller
// camera box (depth [0, range), +-0.6 range across), the PS2 size (corners scaled about the centre by the
// steady-state size ratio: Size_base x (1 + Size_plus / (1 - D_size_plus)), PS2 / GC), the PS2 colour and
// alpha with the PS2 fades (near: Work8 30 / 5 -> 3.0 m to 0.5 m; far: the last 30 % of the box) and the
// GC's indoor fade counter. Expected sprites in view = live / every x (range_ps2 / range_gc)^3, the PS2 count.
struct Ps2fxHaze {
    u16 room;
    u8 every;
    u8 r, g, b, a;
    f32 range;
    f32 scale;
};
#if RE4DC_WATER45_NATIVE
#define PS2FX_HAZE_ROOMS 4
#else
#define PS2FX_HAZE_ROOMS 3
#endif
static const Ps2fxHaze kPs2Haze[PS2FX_HAZE_ROOMS] = {
    // r100: GC 60 x 1283.056 mm (+0.011), alpha 70, R 5090.2; PS2 11 x 2000 mm (+0.010), (235,235,210,34), R 5000
    {0x100, 5, 235, 235, 210, 34, 5000.0f, (2000.0f * 2.0f) / (1283.056f * 2.1f)},
    // r101: GC 39 x 1299.956 mm, alpha 25, R 6860.2; PS2 8 x 1900 mm, (255,250,240,35), R 5000
    {0x101, 2, 255, 250, 240, 35, 5000.0f, 1900.0f / 1299.956f},
    // r103: GC 41 x 1283.056 mm, alpha 30, R 7954.4; PS2 11 x 2100 mm, (255,255,225,35), R 5300
    {0x103, 1, 255, 255, 225, 35, 5300.0f, 2100.0f / 1283.056f},
#if RE4DC_WATER45_NATIVE
    // r10b (ROUTE_CH13 WATER45_NATIVE): GC 80 x 1731.403 mm, alpha 20, R 12093.6; PS2 30 x 2100 mm, (180,185,175,30), R 5000
    {0x10b, 1, 180, 185, 175, 30, 5000.0f, 2100.0f / 1731.403f},
#endif
};
static const Ps2fxHaze* Ps2fxHazeFor(cEsp* esp)
{
    if (!(re4dc_ps2fx & PS2FX_HAZE) || esp->m_Id != 0x15 || esp->info.owner != 0xD0) {
        return NULL;
    }
    const u16 room = G_ROOM_ID;
    for (int i = 0; i < PS2FX_HAZE_ROOMS; ++i) {
        if (kPs2Haze[i].room == room) {
            return &kPs2Haze[i];
        }
    }
    return NULL;
}
// esp15.cpp's work (cEsp15::m_Free), read for the indoor fade counter.
struct Ps2fxEsp15Work {
    f32 Range;
    f32 Del_ratio;
    f32 Base_alpha;
    f32 Min_y;
    u8 Room_del_frame;
    u8 Room_del_cnt;
};
class cPs2fxEsp15 : public cEsp {
public:
    Ps2fxEsp15Work m_Free;
};
#endif
#if RE4DC_EFFECT_PS2_STREAK
// EFFECT_PS2_STREAK: r100's house window streaks (sst 0x09, area 2: records 5, 8 and 13 are Esp0a type 0, which
// lays up to 50 static id-0 copies along each record's path at spawn). The PS2 release has none of them: =1 skips
// the copies (the generators, their Rnd() and the copies themselves still run). =2 also draws the PS2 light
// shafts (texture e9, world-oriented, additive): the stairs window's (PS2 sst 0x06, its own area 13) and the back
// window's two (PS2 sst 0x09 records 2/3), at the first copy of record 8 / 13 (the record's own position).
struct Ps2fxStreak {
    u8 tex;
    u16 del_far, del_near;
    Vec anchor;
};
static const Ps2fxStreak kPs2Streak[3] = {
    {0x32, 300, 180, {-85734.398f, 3311.835f, -32300.832f}},   // record 5: side window (PS2 keeps GC 6/7's shafts)
    {0x1f, 200, 100, {-73739.398f, 4998.185f, -32454.699f}},   // record 8: the stairs window glare
    {0x32, 260, 100, {-82371.102f, 2484.679f, -29994.271f}},   // record 13: the back window
};
#if RE4DC_EFFECT_PS2_STREAK >= 2
struct Ps2fxShaft {
    Vec pos;
    f32 ang_x;   // degrees
    f32 w, h;
    u8 r, g, b, a;
    u16 del_far, del_near;   // x10 mm (EspGenWork Del_far * 10)
};
static const Ps2fxShaft kPs2Stairs = {{-73739.398f, 4678.185f, -32454.699f}, 40.0f, 1801.0f, 2700.0f, 255, 255, 235, 34, 380, 180};
static const Ps2fxShaft kPs2Back[2] = {
    {{-82371.102f, 2384.679f, -29994.271f}, 69.0f, 946.666f, 2100.0f, 255, 255, 225, 60, 300, 150},
    {{-82371.102f, 2324.679f, -29994.271f}, 59.0f, 946.666f, 2100.0f, 255, 255, 225, 50, 300, 150},
};
// PS2 r100_11.EAR entry 17 (area 13, xz4): the player test of EffAreaUpdate (pos.y + 100; area.h bounds).
static int Ps2fxInStairsArea()
{
    static const f32 px[4] = {-75353.765625f, -71789.0703125f, -72168.6484375f, -75650.09375f};
    static const f32 pz[4] = {-41277.6953125f, -41237.60546875f, -32265.046875f, -32397.771484375f};
    static const f32 floor = -241.27594f, height = 9921.8984f;
    Vec pos;
    if ((pG->Status_flg[2] & 0x10000) == 0) {
        if (!pPL) {
            return 0;
        }
        pos = pPL->pos;
        pos.y += 100.0f;
    } else {
        pos = pG->Cam.param.pos;
    }
    const f32 x = pos.x, y = pos.y, z = pos.z;
    if (y + 100.0f < floor || y >= floor + height) {
        return 0;
    }
    if ((px[3] - px[0]) * (z - pz[0]) > (pz[3] - pz[0]) * (x - px[0]) ||
        (px[1] - px[0]) * (z - pz[0]) < (pz[1] - pz[0]) * (x - px[0])) {
        return 0;
    }
    if ((px[3] - px[2]) * (z - pz[2]) < (pz[3] - pz[2]) * (x - px[2]) ||
        (px[1] - px[2]) * (z - pz[2]) > (pz[1] - pz[2]) * (x - px[2])) {
        return 0;
    }
    return 1;
}
#endif
#endif
// 0: draw as usual; 1: not drawn (a haze sprite outside the PS2 subset / box, a streak copy); 2: a streak
// anchor (=2: draws the PS2 shafts in its place).
static int Ps2fxClass(cEsp* esp)
{
    if (esp->info.owner != 0xD0) {
        return 0;
    }
#if RE4DC_EFFECT_PS2_HAZE
    if (esp->m_Id == 0x15) {
        const Ps2fxHaze* h = Ps2fxHazeFor(esp);
        if (!h) {
            return 0;
        }
        const u32 slot = (u32) ((u8*) esp - (u8*) g_pEspSys->pEspBuf) / 0x150;
        if (slot % h->every) {
            return 1;
        }
        // esp15.cpp's box axes: the camera side (view x), Cam.up and the view axis
        Vec v, d, up;
        PSMTXMultVec(pG->Cam.v_mat, &esp->m_Pos, &v);
        PSVECSubtract(&esp->m_Pos, &pG->Cam.param.pos, &d);
        up = pG->Cam.up;
        const f32 ul = up.x * up.x + up.y * up.y + up.z * up.z;
        const f32 half = h->range * 0.6f;
        const f32 dy = ul > 0.0f ? (d.x * up.x + d.y * up.y + d.z * up.z) / sqrtf(ul) : v.y;
        if (-v.z >= h->range || v.x > half || v.x < -half || dy > half || dy < -half) {
            return 1;
        }
        return 0;
    }
#endif
#if RE4DC_EFFECT_PS2_STREAK
    if ((re4dc_ps2fx & PS2FX_STREAK) && esp->m_Id == 0 && esp->m_Life_max == 0 && esp->m_Blend_type == 1 &&
        G_ROOM_ID == 0x100) {
        for (int i = 0; i < 3; ++i) {
            const Ps2fxStreak* s = &kPs2Streak[i];
            if (esp->m_Tex_id == s->tex && esp->m_Del_far == s->del_far && esp->m_Del_near == s->del_near) {
#if RE4DC_EFFECT_PS2_STREAK >= 2
                const f32 dx = esp->m_Pos.x - s->anchor.x, dy = esp->m_Pos.y - s->anchor.y, dz = esp->m_Pos.z - s->anchor.z;
                if (i != 0 && dx * dx + dy * dy + dz * dz < 100.0f) {
                    return 2;
                }
#endif
                return 1;
            }
        }
    }
#endif
    return 0;
}
#endif
static void EspSpriteEmit(cEsp* esp)
{
    // GX blend factors 0..7 (ZERO ONE DSTCLR/SRCCLR INVxCLR SRCA INVSRCA DSTA INVDSTA) have the
    // PVR_BLEND_* values 0..7 (PVR "DESTCOLOR" is the other colour on either side).
    // Local corners of g_EspCommonDisplayList in PVR sprite order A(0,1) B(1,1) C(1,0) D(0,0).
    static const f32 cx[4] = {0.0f, 1.0f, 1.0f, 0.0f}, cy[4] = {1.0f, 1.0f, 0.0f, 0.0f};
    static const f32 cu[4] = {0.0f, 1.0f, 1.0f, 0.0f}, cv[4] = {0.0f, 0.0f, 1.0f, 1.0f};
    EspTexWk* tw = &g_pEspSys->Esp_tex_tbl[esp->m_Tex_id];
    if (tw->Owner == 0xD2 || !tw->pTpl || esp->m_Ptn_no >= tw->pTpl->numDescriptors) {
        return;
    }
    const TEXDescriptor* td = TEXGet(tw->pTpl, esp->m_Ptn_no);
    const TEXHeader* th = td->textureHeader;
    Re4dcEffectSprite s;
    s.image.pixels = th->data;
    s.image.palette = NULL;
    s.image.width = th->width;
    s.image.height = th->height;
    s.image.format = th->format;
    s.image.palette_format = 0xffffffffU;
    s.image.palette_bytes = 0;
    if (td->CLUTHeader) {
        s.image.palette = td->CLUTHeader->data;
        s.image.palette_format = td->CLUTHeader->format;
        s.image.palette_bytes = td->CLUTHeader->numEntries * 2;
    }
    f32 P[7], V[6];
    GXGetProjectionv(P);
    GXGetViewportv(V);
    if (V[2] <= 0.0f || V[3] <= 0.0f) {
        return;
    }
    const int ortho = P[0] != 0.0f;
    const f32 near_d = ortho ? 0.0f : P[6] / (P[5] - 1.0f), far_d = ortho ? 0.0f : P[6] / P[5];
    const Mtx& m = esp->m_Mat;
#if RE4DC_WATER45_NATIVE
    f32 corner[4][3];
#endif
    for (int i = 0; i < 4; ++i) {
        const f32 x = m[0][0] * cx[i] + m[0][1] * cy[i] + m[0][2] + m[0][3];
        const f32 y = m[1][0] * cx[i] + m[1][1] * cy[i] + m[1][2] + m[1][3];
        const f32 z = m[2][0] * cx[i] + m[2][1] * cy[i] + m[2][2] + m[2][3];
        f32 px, py, inv;
        if (ortho) {
            px = P[1] * x + P[2];
            py = P[3] * y + P[4];
            inv = 1.0f;
        } else {
            if (-z < near_d || -z > far_d) {
                return; // near/far crossing: drop, never clip
            }
            inv = 1.0f / -z;
            px = (P[1] * x + P[2] * z) * inv;
            py = (P[3] * y + P[4] * z) * inv;
        }
        s.x[i] = (V[2] * 0.5f * px + V[0] + V[2] * 0.5f) * 640.0f / V[2];
        s.y[i] = (-V[3] * 0.5f * py + V[1] + V[3] * 0.5f) * 480.0f / V[3];
        s.z[i] = inv;
        s.u[i] = tw->mtx[0][0] * cu[i] + tw->mtx[0][1] * cv[i] + tw->mtx[0][3];
        s.v[i] = tw->mtx[1][0] * cu[i] + tw->mtx[1][1] * cv[i] + tw->mtx[1][3];
#if RE4DC_WATER45_NATIVE
        corner[i][0] = x;
        corner[i][1] = y;
        corner[i][2] = z;
#endif
    }
#if RE4DC_WATER45_NATIVE
    // WATER45_NATIVE: the GameCube's water writes Z (Espgen45_TransSub GXSetZMode(1, LEQUAL, 1)) before the effect
    // layers, so a sprite wholly under the surface seen from above it is never drawn (r10b's lake mist sheets).
    if (!ortho && re4dc_water45_hides(corner)) {
        return;
    }
#endif
#if RE4DC_EFFECT_PS2_HAZE
    const Ps2fxHaze* hz = ortho ? NULL : Ps2fxHazeFor(esp);
    if (hz) {
        // PS2 size: the camera-facing square scaled about its centre (its anchor is the centre: tex 0x1f Cx/Cy 0)
        const f32 mx = (s.x[0] + s.x[1] + s.x[2] + s.x[3]) * 0.25f, my = (s.y[0] + s.y[1] + s.y[2] + s.y[3]) * 0.25f;
        for (int i = 0; i < 4; ++i) {
            s.x[i] = mx + (s.x[i] - mx) * hz->scale;
            s.y[i] = my + (s.y[i] - my) * hz->scale;
        }
        // PS2 colour and fades from the view depth (every corner of the square has the same z)
        const f32 d = 1.0f / s.z[0];
        const Ps2fxEsp15Work* w = &static_cast<cPs2fxEsp15*>(esp)->m_Free;
        f32 fa = (f32) hz->a;
        if (w->Room_del_frame != 0 && w->Room_del_cnt != 0) {
            const u32 cnt = w->Room_del_cnt < w->Room_del_frame ? w->Room_del_cnt : w->Room_del_frame;
            fa *= 1.0f - (f32) cnt / w->Room_del_frame;
        }
        if (d > hz->range * 0.7f) {
            fa *= 1.0f - (d - hz->range * 0.7f) / (hz->range * 0.3f);
        }
        if (d < 3000.0f) {
            const f32 rate = 1.0f - (3000.0f - d) / 2500.0f;
            fa *= rate > 0.0f ? rate : 0.0f;
        }
        u32 hr = hz->r, hg = hz->g, hb = hz->b, ha = fa > 0.0f ? (u32) fa : 0;
        if (!(esp->m_Flg & 4) && EffIsSetFinalCol()) {
            GXColor fin;
            EffGetFinalCol(&fin);
            hr = hr * fin.r >> 8;
            hg = hg * fin.g >> 8;
            hb = hb * fin.b >> 8;
            ha = ha * fin.a >> 8;
        }
        if (ha == 0) {
            return;
        }
        s.color = (ha << 24) | (hr << 16) | (hg << 8) | hb;
        s.src = esp->xA5 & 7;
        s.dst = esp->xA6 & 7;
        s.screen = 0;
        s.pad = 0;
        re4dc_effect_sprite(&s);
        return;
    }
#endif
    u32 r = s_effect_col.r, g = s_effect_col.g, b = s_effect_col.b, a = s_effect_col.a;
    if (!(esp->m_Tool_flg & 0x40)) {
        if (esp->m_Tool_flg & 0x80) { // TEV colour scale 4
            r = r * 4 > 255 ? 255 : r * 4;
            g = g * 4 > 255 ? 255 : g * 4;
            b = b * 4 > 255 ? 255 : b * 4;
        }
        if (esp->m_Tool_flg & 0x20000) { // TEV alpha scale 4
            a = a * 4 > 255 ? 255 : a * 4;
        }
    }
    s.color = (a << 24) | (r << 16) | (g << 8) | b;
    s.src = esp->xA5 & 7;
    s.dst = esp->xA6 & 7;
    s.screen = ortho;
    s.pad = 0;
    re4dc_effect_sprite(&s);
}
#if defined(RE4DC_COARSE_FX_SPRITES) && RE4DC_COARSE_FX_SPRITES
// COARSE_FX_SPRITES (effects30.mk): a live effect the EspCommonTrans sprite path draws (esp.cpp queues
// it in a drawn coarse image's logic-only pass; coarse.cpp then draws no marker for it). Esp0b (the room
// fires' particles) is EspCommonTrans after an optional camera jitter; esp.cpp queues its common body.
extern EspTransFunc EspTransTbl[0xFF];
extern "C" int re4dc_esp_sprite_class(cEsp* esp)
{
#if defined(RE4DC_NATIVE_LASER) && RE4DC_NATIVE_LASER
    if (esp->m_Id == 0x19) return 1;
#endif
    return (EspTransTbl[esp->m_Id] == EspCommonTrans || esp->m_Id == 0x0B) && EspSpriteEligible(esp);
}
extern "C" float re4dc_fog_gate_far() __attribute__((weak)); // ACTOR_FOG_GATE builds (native_static.cpp)
// 0 for a faded-out effect, or a world-placed sprite effect wholly behind the camera, beyond the fogged View far or outside a
// wide view cone (horizontal tan 1.2, vertical tan 0.9; radius twice the base size + 100): esp.cpp's
// coarse pass does not queue it, so the common body never builds a matrix and colour only for
// re4dc_effect_sprite to cull the sprite. Screen and direct-OT effects are always kept.
#if defined(RE4DC_ESP_SPRITE_FAST) && RE4DC_ESP_SPRITE_FAST
// ESP_SPRITE_FAST: the fogged View far is read once per sprite pass (esp.cpp EspTrans), not once per effect.
static f32 s_vis_far;
extern "C" void re4dc_esp_sprite_pass_begin()
{
    s_vis_far = re4dc_fog_gate_far ? re4dc_fog_gate_far() : 0.0f;
}
#endif
extern "C" int re4dc_esp_coarse_sprite_visible(cEsp* esp)
{
#if defined(RE4DC_NATIVE_LASER) && RE4DC_NATIVE_LASER
    // A beam can cross the view while either endpoint is outside it. Esp19
    // retains source OT checks; its own line adapter clips the full segment.
    if (esp->m_Id == 0x19) return 1;
#endif
#if RE4DC_PS2FX_DRAW
    if (re4dc_ps2fx & (PS2FX_HAZE | PS2FX_STREAK)) {
        const int k = Ps2fxClass(esp);
        if (k) {
            return k == 2;   // a dropped haze sprite / streak copy is not queued; a streak anchor (=2) always is
        }
    }
#endif
    if (!(esp->m_Flg & 1) && esp->m_Col_a < 1.0f) {
        return 0;   // faded out: ChannelSet's alpha is (u8) m_Col_a here (before the final-colour scale), so 0
    }
    if ((u8) (esp->m_Parts_no + 8) <= 5 || (esp->m_Tool_flg & (0x1000 | 0x400000 | 0x400 | 0x800)) ||
        (esp->m_Flg & 8)) {
        return 1;
    }
    Vec w, v;
    if (esp->parent && esp->parent != pEffParentWorld) {
        PSMTXMultVec(esp->parent->mat, &esp->m_Pos, &w);
    } else {
        w = esp->m_Pos;
    }
    PSMTXMultVec(pG->Cam.v_mat, &w, &v);
    const f32 bx = esp->m_Size_base_x, by = esp->m_Size_base_y;
#if RE4DC_EFFECT_PS2_HAZE
    const Ps2fxHaze* hz = Ps2fxHazeFor(esp);
    const f32 r = 2.0f * (bx > by ? bx : by) * esp->m_Size_mul * (hz ? hz->scale : 1.0f) + 100.0f;
#else
    const f32 r = 2.0f * (bx > by ? bx : by) * esp->m_Size_mul + 100.0f;
#endif
    const f32 d = -v.z;
    if (d + r < 0.0f) {
        return 0;
    }
#if defined(RE4DC_ESP_SPRITE_FAST) && RE4DC_ESP_SPRITE_FAST
    const f32 far = s_vis_far;
#else
    const f32 far = re4dc_fog_gate_far ? re4dc_fog_gate_far() : 0.0f;
#endif
    if (far > 0.0f && d - r > far) {
        return 0;
    }
    if (d > r && ((v.x < 0.0f ? -v.x : v.x) - r > 1.2f * d || (v.y < 0.0f ? -v.y : v.y) - r > 0.9f * d)) {
        return 0;
    }
    return 1;
}
#endif
#endif

// The pulled effect is kept in a one-member struct: the original reloads the pointer from its
// stack slot after every store through it (a struct-member slot aliases the member stores).
struct EspPtr {
    cEsp* p;
};

#define ESP_PARTS_SCREEN(esp) ((s8) (esp)->m_Parts_no >= -8 && (s8) (esp)->m_Parts_no <= -3)

// Texture coordinate corners for the sprite orientation (flags bit1: flip s, bit2: flip t;
// screen sprites are drawn upside down). One combined condition and corners built from a `zero`
// variable: each leaf is a jump target where cse knows neither operand of `zero + z`, which
// keeps the adds (nested ifs with literals fold 0 + z). The flip-s leaves add first, copy after.
#define ESP_FLIP_T(esp)                                                                           \
    ((ESP_PARTS_SCREEN(esp) && !((esp)->m_Tool_flg & 4)) || (!ESP_PARTS_SCREEN(esp) && ((esp)->m_Tool_flg & 4)))
#define ESP_TEXCOORD_SET()                                                                        \
    if (esp->m_Tool_flg & 2) {                                                                         \
        if (ESP_FLIP_T(esp)) {                                                                    \
            s0 = zero + z;                                                                        \
            s1 = zero;                                                                            \
            t0 = s0;                                                                              \
            t1 = s1;                                                                              \
        } else {                                                                                  \
            s0 = zero + z;                                                                        \
            t0 = zero;                                                                            \
            s1 = zero;                                                                            \
            t1 = s0;                                                                              \
        }                                                                                         \
    } else {                                                                                      \
        if (ESP_FLIP_T(esp)) {                                                                    \
            s0 = zero;                                                                            \
            s1 = s0 + z;                                                                          \
            t1 = s0;                                                                              \
            t0 = s1;                                                                              \
        } else {                                                                                  \
            s0 = zero;                                                                            \
            s1 = s0 + z;                                                                          \
            t0 = s0;                                                                              \
            t1 = s1;                                                                              \
        }                                                                                         \
    }

// Default Trans (draw) entry of a sprite effect: dispatches to the shimmer / nega variants
// (m_Shimmer_type, Tool_flg 0x2000), sets the blend mode, and when the previous OT entry was not a
// sprite selects the projection (screen ortho 512x448 for parts 0xF8..0xFD, else the camera) and
// the texture; then builds the sprite matrix (billboard / axis-aligned per Tool_flg, camera pan
// for screen sprites), the colour through ChannelSet and draws the quad (mask texture stage when
// Tool_flg 0x4000). Tool_flg 0x100000 forces the alpha compare, 0x808000 disables alpha update.
// Shared sprite draw: the sprite quad (g_EspCommonDisplayList) with the effect's texture, an
// optional mask texture in TEV stage 1, screen-space or camera-relative placement.
#if RE4DC_EFFECT_SPRITES && RE4DC_EFFECT_PS2_STREAK >= 2
#include <string.h>
// EFFECT_PS2_STREAK=2: one PS2 shaft as an effect of its own: a scratch copy of the streak anchor (owner 0xd0,
// world parent, additive blend) given the PS2 record's texture, placement, size, colour and near fade, drawn by
// the common body (ChannelSet's fade, EspSpriteEmit). The copy is a static scratch buffer outside the effect pool;
// no effect state is written.
static void Ps2fxShaft1(const cEsp* anchor, const Ps2fxShaft* q)
{
    static u32 buf[(sizeof(cEsp) + 3) / 4];
    cEsp* t = (cEsp*) buf;
    memcpy(buf, anchor, sizeof(cEsp));
    t->m_Tex_id = 0xE9;
    t->m_Ptn_no = 0;
    t->m_Tool_flg = 0x1;   // world-oriented (low_RotMatrix(m_Ang)), like GC records 6/7
    t->m_Shimmer_type = 0;
    t->m_Pos = q->pos;
    t->m_Ang.x = q->ang_x * DEG2RAD;
    t->m_Ang.y = 0.0f;
    t->m_Ang.z = 0.0f;
    t->m_Size_base_x = q->w;
    t->m_Size_base_y = q->h;
    t->m_Size_mul = 1.0f;
    t->m_Col_r = q->r;
    t->m_Col_g = q->g;
    t->m_Col_b = q->b;
    t->m_Col_a = q->a;
    t->m_Del_far = q->del_far;
    t->m_Del_near = q->del_near;
    EspCommonTrans(t);
}
static void Ps2fxShafts(cEsp* anchor)
{
    const f32 dx = anchor->m_Pos.x - kPs2Streak[1].anchor.x;
    if (dx * dx < 1.0e6f) {   // record 8 (the stairs window): PS2 area 13 only
        if (Ps2fxInStairsArea()) {
            Ps2fxShaft1(anchor, &kPs2Stairs);
        }
    } else {                  // record 13 (the back window)
        Ps2fxShaft1(anchor, &kPs2Back[0]);
        Ps2fxShaft1(anchor, &kPs2Back[1]);
    }
}
#endif
void EspCommonTrans(cEsp* esp)
{
    static int s_proj_type;
    static int s_tex_no;
    static EspAnmData* s_pAnm;
    static int s_ptn_no;
    Mtx inv;
    f32 sx;
    f32 sy;
    f32 ox;
    f32 oy;

    if (esp->m_Shimmer_type != 0) {
        EspCommonTransShimmer(esp, esp->m_Shimmer_pow, esp->m_Shimmer_type);
        return;
    }
    if (esp->m_Tool_flg & 0x2000) {
        EspCommonTransNega(esp, 2);
        return;
    }
#if defined(RE4DC_ESP_SPRITE_FAST) && RE4DC_ESP_SPRITE_FAST
    // ESP_SPRITE_FAST (effects30.mk): under EFFECT_LEAN nothing draws a sprite the native path does not take
    // (no GX draw follows): the body would only build m_Mat and GX state that no draw and no game logic
    // reads. The cached projection / texture are forgotten, so a following sprite that trusts an OT run of
    // sprites (OtGetPrevKind() == 8) sets them itself, as this one would have.
    if (!EspSpriteEligible(esp)) {
        s_proj_type = -1;
        s_tex_no = -1;
        return;
    }
#endif
#if RE4DC_EFFECT_SPRITES && RE4DC_PS2FX_DRAW
    // EFFECT_PS2_HAZE / EFFECT_PS2_STREAK: a haze sprite outside the PS2 subset / box or a streak copy is not
    // drawn (=2: a streak anchor draws the PS2 shafts instead). The cached projection / texture are forgotten,
    // as for an ineligible sprite above.
    if ((re4dc_ps2fx & (PS2FX_HAZE | PS2FX_STREAK)) && EspSpriteEligible(esp)) {
        const int k = Ps2fxClass(esp);
        if (k) {
            s_proj_type = -1;
            s_tex_no = -1;
#if RE4DC_EFFECT_PS2_STREAK >= 2
            if (k == 2) {
                Ps2fxShafts(esp);
                s_proj_type = -1;
                s_tex_no = -1;
            }
#endif
            return;
        }
    }
#endif
#if RE4DC_EFFECT_SPRITES && RE4DC_WATER45_NATIVE
    // WATER45_NATIVE (ROUTE_CH13): r10b's room sheets that the PS2 release dropped (SLUS-211.34 r10b EFF: no GC sst
    // 0x02 mist sheets (tex f2), sst 0x04 cliff / backdrop sheets (f6, cb) and glows (1d), sst 0x06 screen tint
    // (ff); its lake is flat planes, here the native water45 surface) are not drawn, nor est 0x23's white square
    // (the PS2 sets its colour to 0, 0, 0, 0). Render only.
    if (G_ROOM_ID == 0x10b &&
        ((esp->info.owner == 0xD0 && (esp->m_Tex_id == 0xf2 || esp->m_Tex_id == 0xf6 || esp->m_Tex_id == 0xcb ||
                                      esp->m_Tex_id == 0x1d || esp->m_Tex_id == 0xff)) ||
         (esp->info.owner == 0x01 && esp->m_Id == 0 && esp->m_Tex_id == 0))) {
        s_proj_type = -1;
        s_tex_no = -1;
        return;
    }
#endif
#if !RE4DC_EFFECT_LEAN
    GXSetBlendMode(esp->xA4, esp->xA5, esp->xA6, esp->xA7);
#endif
    if (OtGetPrevKind() != 8) {
        if (ESP_PARTS_SCREEN(esp)) {
            Mtx44 proj;
            s_proj_type = 0;
            C_MTXOrtho(proj, 0.0f, 448.0f, 0.0f, 512.0f, 0.0f, -100.0f);
            GXSetProjection(proj, 1);
        } else {
            s_proj_type = 1;
            CameraCurrentProjection();
        }
        if (!EspGetAnmAddr(esp->m_Tex_id, &s_pAnm)) {
            pLog->err(0, 0, "ESP : TexId[%x] no data", esp->m_Tex_id);
            s_tex_no = -1;
            return;
        }
#if !RE4DC_EFFECT_LEAN
        EspTexSet(esp->m_Tex_id, esp->m_Ptn_no);
#endif
        s_tex_no = esp->m_Tex_id;
        s_ptn_no = esp->m_Ptn_no;
#if !RE4DC_EFFECT_LEAN
        esp->CommonStateSet();
        GXClearVtxDesc();
        GXSetVtxDesc(9, 1);
        GXSetVtxDesc(0xA, 1);
        GXSetVtxDesc(0xD, 1);
        GXSetVtxAttrFmt(0, 9, 1, 1, 0);
        GXSetVtxAttrFmt(0, 0xA, 0, 1, 0);
        GXSetVtxAttrFmt(0, 0xD, 1, 1, 0);
#endif
    } else {
        if (ESP_PARTS_SCREEN(esp)) {
            if (s_proj_type != 0) {
                Mtx44 proj;
                s_proj_type = 0;
                C_MTXOrtho(proj, 0.0f, 448.0f, 0.0f, 512.0f, 0.0f, -100.0f);
                GXSetProjection(proj, 1);
            }
        } else {
            if (s_proj_type != 1) {
                s_proj_type = 1;
                CameraCurrentProjection();
            }
        }
        if (s_tex_no != esp->m_Tex_id) {
            if (!EspGetAnmAddr(esp->m_Tex_id, &s_pAnm)) {
                pLog->err(0, 0, "ESP : TexId[%x] no data", esp->m_Tex_id);
                s_tex_no = -1;
                return;
            }
        }
        if (s_tex_no != esp->m_Tex_id || s_ptn_no != esp->m_Ptn_no) {
#if !RE4DC_EFFECT_LEAN
            EspTexSet(esp->m_Tex_id, esp->m_Ptn_no);
#endif
            s_ptn_no = esp->m_Ptn_no;
        }
        s_tex_no = esp->m_Tex_id;
    }
    if (!esp->ChannelSet()) {
        return;
    }
    sx = esp->m_Size_base_x * esp->m_Size_mul;
    sy = esp->m_Size_base_y * esp->m_Size_mul;
    if ((f32) s_pAnm->Cx == 0.0f) {
        ox = -0.5f;
    } else {
        ox = (f32) -s_pAnm->Cx / s_pAnm->Width;
    }
    if ((f32) s_pAnm->Cy == 0.0f) {
        oy = -0.5f;
    } else {
        oy = (f32) s_pAnm->Cy / s_pAnm->Height + -1.0f;
    }
    if (ESP_PARTS_SCREEN(esp)) {
        Mtx m;

        esp->m_Mat[2][2] = 1.0f;
        esp->m_Mat[0][0] = sx;
        esp->m_Mat[0][1] = 0.0f;
        esp->m_Mat[0][2] = 0.0f;
        esp->m_Mat[0][3] = ox * sx;
        esp->m_Mat[1][0] = 0.0f;
        esp->m_Mat[1][1] = sy;
        esp->m_Mat[1][2] = 0.0f;
        esp->m_Mat[1][3] = oy * sy;
        esp->m_Mat[2][0] = 0.0f;
        esp->m_Mat[2][1] = 0.0f;
        esp->m_Mat[2][3] = 0.0f;
        if (esp->m_Tool_flg & 2) {
            esp->m_Mat[0][0] = -sx;
            esp->m_Mat[0][3] = -(ox * sx);
            if (!(esp->m_Tool_flg & 4)) {
                esp->m_Mat[1][1] = -sy;
                esp->m_Mat[1][3] = -(oy * sy);
            }
        } else if (!(esp->m_Tool_flg & 4)) {
            esp->m_Mat[1][1] = -sy;
            esp->m_Mat[1][3] = -(oy * sy);
        }
        low_RotMatrix(m, &esp->m_Ang);
        PSMTXConcat(m, esp->m_Mat, esp->m_Mat);
        esp->m_Mat[0][3] += esp->m_Pos.x;
        esp->m_Mat[1][3] += esp->m_Pos.y;
        esp->m_Mat[2][3] += esp->m_Pos.z;
    } else if (!(esp->m_Tool_flg & 0x80001)) {
        Mtx m;
        Vec p;
        Mtx m2;

        esp->m_Mat[2][2] = 1.0f;
        esp->m_Mat[0][0] = sx;
        esp->m_Mat[0][1] = 0.0f;
        esp->m_Mat[0][2] = 0.0f;
        esp->m_Mat[0][3] = ox * sx;
        esp->m_Mat[1][0] = 0.0f;
        esp->m_Mat[1][1] = sy;
        esp->m_Mat[1][2] = 0.0f;
        esp->m_Mat[1][3] = oy * sy;
        esp->m_Mat[2][0] = 0.0f;
        esp->m_Mat[2][1] = 0.0f;
        esp->m_Mat[2][3] = 0.0f;
        if (esp->m_Tool_flg & 2) {
            esp->m_Mat[0][0] = -sx;
            esp->m_Mat[0][3] = -(ox * sx);
            if (esp->m_Tool_flg & 4) {
                esp->m_Mat[1][1] = -sy;
                esp->m_Mat[1][3] = -(oy * sy);
            }
        } else if (esp->m_Tool_flg & 4) {
            esp->m_Mat[1][1] = -sy;
            esp->m_Mat[1][3] = -(oy * sy);
        }
        PSMTXRotRad(m, 'z', esp->m_Ang.z);
        PSMTXConcat(m, esp->m_Mat, esp->m_Mat);
        PSMTXConcat(pG->Cam.v_mat, esp->parent->mat, m2);
        PSMTXMultVec(m2, &esp->m_Pos, &p);
        esp->m_Mat[0][3] += p.x;
        esp->m_Mat[1][3] += p.y;
        esp->m_Mat[2][3] += p.z;
    } else {
        Mtx m;

        esp->m_Mat[0][0] = sx;
        esp->m_Mat[0][1] = 0.0f;
        esp->m_Mat[2][2] = 1.0f;
        esp->m_Mat[0][2] = 0.0f;
        esp->m_Mat[0][3] = ox * sx;
        esp->m_Mat[1][0] = 0.0f;
        esp->m_Mat[1][1] = sy;
        esp->m_Mat[1][2] = 0.0f;
        esp->m_Mat[1][3] = oy * sy;
        esp->m_Mat[2][0] = 0.0f;
        esp->m_Mat[2][1] = 0.0f;
        esp->m_Mat[2][3] = 0.0f;
        if (esp->m_Tool_flg & 2) {
            esp->m_Mat[0][0] = -sx;
            esp->m_Mat[0][3] = -(ox * sx);
            if (esp->m_Tool_flg & 4) {
                esp->m_Mat[1][1] = -sy;
                esp->m_Mat[1][3] = -(oy * sy);
            }
        } else if (esp->m_Tool_flg & 4) {
            esp->m_Mat[1][1] = -sy;
            esp->m_Mat[1][3] = -(oy * sy);
        }
        low_RotMatrix(m, &esp->m_Ang);
        PSMTXConcat(m, esp->m_Mat, esp->m_Mat);
        if (esp->m_Tool_flg & 0x80000) {
            Mtx m3;
            PSMTXRotRad(m3, 'y', EspGetCameraPan() * (3.1415927f / 180.0f));
            PSMTXConcat(m3, esp->m_Mat, esp->m_Mat);
        }
        esp->m_Mat[0][3] += esp->m_Pos.x;
        esp->m_Mat[1][3] += esp->m_Pos.y;
        esp->m_Mat[2][3] += esp->m_Pos.z;
        PSMTXConcat(esp->parent->mat, esp->m_Mat, esp->m_Mat);
        PSMTXConcat(pG->Cam.v_mat, esp->m_Mat, esp->m_Mat);
    }
#if defined(RE4DC_ESP_SPRITE_FAST) && RE4DC_ESP_SPRITE_FAST
    // Eligible (tested above): the native sprite is the only output. The normal matrix (read by no sprite),
    // the mask stage (ineligible) and the GX draw (EFFECT_LEAN) are skipped.
    EspSpriteEmit(esp);
    return;
#elif RE4DC_EFFECT_SPRITES
    if (EspSpriteEligible(esp)) {
        EspSpriteEmit(esp);
    }
#endif
    PSMTXInverse(esp->m_Mat, inv);
    PSMTXTranspose(inv, inv);
    GXLoadNrmMtxImm(inv, 0);
#if !RE4DC_EFFECT_LEAN
    GXLoadPosMtxImm(esp->m_Mat, 0);
    GXSetCurrentMtx(0);
#endif
    if (esp->m_Tool_flg & 0x4000) {
        int no = esp->m_MaskTex_id;
        EspTexWk* tw = EspGetTexWk(no, 1);
        if (tw->Owner == 0xD2) {
            pLog->err(0, 0, "ESP : Mask_TexId[%x] no data", no);
        } else {
#if RE4DC_EFFECT_LEAN
            GXSetTevColorOp(1, 0, 0, 0, 1, 0); // the only state the native side reads (TEV scale)
#else
            GXTexObj tex;
            GXTlutObj tlut;
            GXTexObj* pTex = &tex;
            GXTlutObj* pTlut = &tlut;
            TEXDescriptor* td = TEXGet(tw->pTpl, esp->m_MaskPtn_no);
            TEXHeader* th = td->textureHeader;

            if (th->format == 8 || th->format == 9) {
                GXInitTexObjCI(pTex, th->data, th->width, th->height, th->format, 0, 0, 0, 1);
                GXInitTlutObj(pTlut, td->CLUTHeader->data, td->CLUTHeader->format, td->CLUTHeader->numEntries);
                GXLoadTlut(pTlut, 1);
            } else {
                GXInitTexObj(pTex, th->data, th->width, th->height, th->format, 0, 0, 0);
            }
            GXLoadTexObj(pTex, 1);
            GXLoadTexMtxImm(tw->mtx, 0x21, 1);
            GXSetTexCoordGen(1, 1, 4, 0x21);
            GXSetNumTevStages(2);
            GXSetNumTexGens(2);
            GXSetTevOrder(1, 1, 1, 4);
            GXSetTevColorIn(1, 0xF, 0xF, 0xF, 0);
            GXSetTevColorOp(1, 0, 0, 0, 1, 0);
            GXSetTevAlphaIn(1, 7, 4, 5, 7);
            if (esp->m_Tool_flg & 0x20000) {
                GXSetTevAlphaOp(1, 0, 0, 2, 1, 0);
            } else {
                GXSetTevAlphaOp(1, 0, 0, 0, 1, 0);
            }
#endif
        }
    }
#if RE4DC_EFFECT_LEAN
    return; // alpha update / Z / dst alpha / alpha compare set and reset, and the draw: GX sinks
#endif
    {
        // The flag word is read into a local for the first test only: with two plain reads the
        // pre-cse jump threading merges the compares; the original kept one compare in cr7.
        u32 sysFlags = pG->Status_flg[1];
        if ((!(sysFlags & 0x80) && (esp->m_Tool_flg & 0x8000)) || ((pG->Status_flg[1] & 0x80) && (esp->m_Tool_flg & 0x800000))) {
            GXSetAlphaUpdate(1);
        }
    }
    if (esp->m_Tool_flg & 0x200000) {
        GXSetZMode(1, 3, 1);
        GXSetDstAlpha(1, 0);
    }
    if (esp->m_Tool_flg & 0x100000) {
        GXSetAlphaCompare(4, 0x80, 1, 4, 0x80);
    }
    if (esp->m_Flg & 0x10) {
        Esp1b_SpTrans(esp);
    } else {
        GXCallDisplayList(g_EspCommonDisplayList, 0x60);
    }
    if (esp->m_Tool_flg & 0x4000) {
        GXSetNumTevStages(1);
        GXSetNumTexGens(1);
    }
    if (esp->m_Tool_flg & 0x200000) {
        GXSetZMode(1, 3, 0);
        GXSetDstAlpha(0, 0);
    }
    if (esp->m_Tool_flg & 0x100000) {
        GXSetAlphaCompare(4, 1, 1, 4, 1);
    }
    if (esp->m_Tool_flg & 0x808000) {
        GXSetAlphaUpdate(0);
    }
}

// Heat shimmer sprite: the frame is copied into a texture and drawn back through an indirect
// texture (blur 1..3 select the warp mode; type scales the distortion).
static void EspCommonTransShimmer(cEsp* esp, int type, u32 blur)
{
    static Mtx Matrix1 = {
        {0.001953125f, 0.0f, 0.0f, 0.0f},
        {0.0f, 1.0f / 448.0f, 0.0f, 0.0f},
        {0.0f, 0.0f, 1.0f, 0.0f},
    };
    static Mtx Matrix2 = {
        {0.001953125f, 0.0f, 0.0f, 0.0f},
        {0.0f, 0.0029762f, -0.167f, 0.0f},
        {0.0f, 0.0f, 1.0f, 0.0f},
    };
    Mtx44 proj;
    Mtx inv;
    EspAnmData* anm;
    GXColor fog;
    f32 sx;
    f32 sy;
    f32 ox;
    f32 oy;
    f32 x0;
    f32 y0;
    f32 z;
    f32 zero;
    f32 s0;
    f32 s1;
    f32 t0;
    f32 t1;
    f32 ofs;
    f32 scale;
    u8 stages;
    int texGens;
    int copyOk;
    void* buf;

    scale = (f32) type * (1.0f / 32.0f) + 1.0f;
    if (!esp->ChannelSet()) {
        return;
    }
    if (!EspGetAnmAddr(esp->m_Tex_id, &anm)) {
        pLog->err(0, 0, "ESP : TexId[%x] no data", esp->m_Tex_id);
        return;
    }
    GXSetCullMode(0);
    GXSetAlphaCompare(4, 1, 1, 4, 1);
    GXSetZMode(1, 3, 0);
    CameraCurrentProjection();
    if (ESP_PARTS_SCREEN(esp)) {
        PSMTXIdentity(esp->m_Mat);
        low_RotMatrix(esp->m_Mat, &esp->m_Ang);
        TransMatrix(esp->m_Mat, &esp->m_Pos);
        C_MTXOrtho(proj, 0.0f, 448.0f, 0.0f, 512.0f, 0.0f, -100.0f);
        GXSetProjection(proj, 1);
    } else if (!(esp->m_Tool_flg & 1)) {
        Vec p;
        Mtx m;

        PSMTXIdentity(esp->m_Mat);
        PSMTXRotRad(esp->m_Mat, 'z', esp->m_Ang.z);
        PSMTXConcat(pG->Cam.v_mat, esp->parent->mat, m);
        PSMTXMultVec(m, &esp->m_Pos, &p);
        esp->m_Mat[0][3] = p.x;
        esp->m_Mat[1][3] = p.y;
        esp->m_Mat[2][3] = p.z;
    } else {
        Mtx m;

        PSMTXIdentity(esp->m_Mat);
        low_RotMatrix(esp->m_Mat, &esp->m_Ang);
        TransMatrix(esp->m_Mat, &esp->m_Pos);
        PSMTXConcat(pG->Cam.v_mat, esp->parent->mat, m);
        PSMTXConcat(m, esp->m_Mat, esp->m_Mat);
    }
    PSMTXInverse(esp->m_Mat, inv);
    PSMTXTranspose(inv, inv);
    GXLoadNrmMtxImm(inv, 0);
    GXLoadPosMtxImm(esp->m_Mat, 0);
    GXSetCurrentMtx(0);
    EspTexSet(esp->m_Tex_id, esp->m_Ptn_no);
    GXSetAlphaCompare(4, 1, 1, 4, 1);
    GXSetBlendMode(esp->xA4, esp->xA5, esp->xA6, esp->xA7);
    GXClearVtxDesc();
    GXSetVtxDesc(9, 1);
    GXSetVtxDesc(0xA, 1);
    GXSetVtxDesc(0xD, 1);
    GXSetVtxAttrFmt(0, 9, 1, 4, 0);
    GXSetVtxAttrFmt(0, 0xA, 0, 1, 0);
    GXSetVtxAttrFmt(0, 0xD, 1, 4, 0);
    sx = esp->m_Size_base_x * esp->m_Size_mul;
    sy = esp->m_Size_base_y * esp->m_Size_mul;
    ox = -anm->Cx;
    oy = (f32) anm->Cy;
    z = 1.0f;
    zero = 0.0f;
    if (ox == zero) {
        ox = -anm->Width * 0.5f;
    }
    if (oy == zero) {
        oy = anm->Height * 0.5f;
    }
    x0 = ox * sx / anm->Width;
    y0 = oy * sy / anm->Height;
    ESP_TEXCOORD_SET()
    GXTexObj tex;
    f32 indMtx[2][3];
    f32 dot;
    texGens = 0;
    copyOk = 1;
    fog.r = fog.g = fog.b = fog.a = 0;
    GXSetFog(0, 0.0f, 0.0f, ZNEAR, ZFAR, fog);
    if (esp->m_Tool_flg & 0x1000) {
        if (GetDrawTmpBufType() == 2) {
            copyOk = 0;
        }
        buf = GetDrawTmpBufAddr(2);
    } else {
        buf = GetDrawTmpBufAddr(1);
    }
    ofs = 56.0f;
    if (pG->Status_flg[1] & 0x08000000) {
        ofs = 0.0f;
    }
    if (copyOk) {
        if (buf == NULL) {
            pLog->warn(0, 0, "Esp0d() : not enough memory");
            return;
        }
        GXSetTexCopySrc(0, (u32) ofs, (u32) Screen.width, (u32) (Screen.height - ofs));
        GXSetTexCopyDst((u32) Screen.width / 2, (u32) ((f32) ((u32) Screen.height / 2) - ofs), 6, 1);
        GXCopyTex(buf, 0);
        GXPixModeSync();
        GXInvalidateTexAll();
    }
    GXInitTexObj(&tex, buf, (u32) Screen.width / 2, (u32) ((f32) ((u32) Screen.height / 2) - ofs), 6, 0, 0, 0);
    GXLoadTexObj(&tex, 1);
    g_Get_tex_obj = tex;
    Mtx tm;
    Mtx pm;
    if (ESP_PARTS_SCREEN(esp)) {
        if (pG->Status_flg[1] & 0x08000000) {
            PSMTXConcat(Matrix1, esp->m_Mat, tm);
        } else {
            PSMTXConcat(Matrix2, esp->m_Mat, tm);
        }
        GXLoadTexMtxImm(tm, 0x1E, 1);
        GXSetTexCoordGen(texGens, 1, 0, 0x1E);
    } else {
        C_MTXLightPerspective(pm, pG->Cam.param.fovy, 1.3333334f, 0.5f, -0.6666667f, 0.5f, 0.5f);
        PSMTXConcat(pm, esp->m_Mat, tm);
        GXLoadTexMtxImm(tm, 0x1E, 0);
        GXSetTexCoordGen(texGens, 0, 0, 0x1E);
    }
    texGens++;
    GXSetNumIndStages(1);
    GXSetTexCoordGen(texGens, 1, 4, 0x3C);
    texGens++;
    GXSetIndTexOrder(0, 1, 0);
    GXSetIndTexCoordScale(0, 0, 0);
    if (ESP_PARTS_SCREEN(esp)) {
        dot = 2500.0f;
    } else {
        Vec dir;
        Vec d;
        Vec p;
        Camera* cam;

        if (esp->parent != pEffParentWorld) {
            PSMTXMultVec(esp->parent->mat, &esp->m_Pos, &p);
        } else {
            p = esp->m_Pos;
        }
        cam = &pG->Cam;
        dir.x = cam->param.at.x - cam->param.pos.x;
        dir.y = cam->param.at.y - cam->param.pos.y;
        dir.z = cam->param.at.z - cam->param.pos.z;
#line 865 "D:/Bio4/Prog/esp_sub.cpp"
        VECNormalize(&dir, &dir);
        d.x = p.x - cam->param.pos.x;
        d.y = p.y - cam->param.pos.y;
        d.z = p.z - cam->param.pos.z;
        dot = PSVECDotProduct(&dir, &d);
    }
    if (dot < 1500.0f) {
        dot = 1500.0f;
    }
    if (blur != 3) {
        indMtx[1][1] = indMtx[0][0] = esp->m_Col_a * (1.0f / 255.0f) * 0.04f * 1000.0f / dot * scale;
        indMtx[0][1] = 0.0f;
        indMtx[0][2] = 0.0f;
        indMtx[1][0] = 0.0f;
        indMtx[1][2] = 0.0f;
    } else {
        static f32 prm1 = 0.5f;
        static f32 prm2 = 0.0f;
        static f32 prm3 = 0.0f;
        static f32 prm4 = Screen.height * 0.5f / Screen.width;

        indMtx[0][0] = prm1;
        indMtx[0][1] = prm2;
        indMtx[0][2] = 0.0f;
        indMtx[1][0] = prm3;
        indMtx[1][1] = prm4;
        indMtx[1][2] = 0.0f;
    }
    GXSetIndTexMtx(1, indMtx, 1);
    {
        u8 signedOfs;
        u8 replace;

        switch (blur) {
        case 1:
            signedOfs = 0;
            replace = 0;
            break;
        case 2:
            signedOfs = 1;
            replace = 0;
            break;
        case 3:
            signedOfs = 0;
            replace = 1;
            break;
        default:
            pLog->err(0, 0, "ESP_SHIMMER : BLUR_TYPE[%x] invalid", blur);
            signedOfs = 0;
            replace = 1;
            break;
        }
        stages = 1;
        GXSetTevIndWarp(0, 0, signedOfs, replace, 1);
    }
    GXSetTevOrder(0, 0, 1, 4);
    GXSetTevColorIn(0, 0xF, 8, 0xA, 0xF);
    GXSetTevColorOp(0, 0, 0, 0, 1, 0);
    GXSetTevAlphaIn(0, 7, 7, 7, 5);
    GXSetTevAlphaOp(0, 0, 0, 0, 1, 0);
    if (esp->m_Tool_flg & 0x4000) {
        int no = esp->m_MaskTex_id;
        EspTexWk* tw = EspGetTexWk(no, 1);
        if (tw->Owner == 0xD2) {
            pLog->err(0, 0, "ESP : Mask_TexId[%x] no data", no);
        } else {
            GXTexObj tex2;
            GXTexObj* pTex = &tex2;
            GXTlutObj* pTlut = (GXTlutObj*) indMtx;
            TEXDescriptor* td = TEXGet(tw->pTpl, esp->m_MaskPtn_no);
            TEXHeader* th = td->textureHeader;

            if (th->format == 8 || th->format == 9) {
                GXInitTexObjCI(pTex, th->data, th->width, th->height, th->format, 0, 0, 0, 1);
                GXInitTlutObj(pTlut, td->CLUTHeader->data, td->CLUTHeader->format, td->CLUTHeader->numEntries);
                GXLoadTlut(pTlut, 1);
            } else {
                GXInitTexObj(pTex, th->data, th->width, th->height, th->format, 0, 0, 0);
            }
            GXLoadTexObj(pTex, 2);
            GXLoadTexMtxImm(tw->mtx, 0x21, 1);
            GXSetTexCoordGen(texGens, 1, 4, 0x21);
            GXSetTevOrder(1, texGens, 2, 4);
            GXSetTevColorIn(1, 0xF, 0xF, 0xF, 0);
            GXSetTevColorOp(1, 0, 0, 0, 1, 0);
            GXSetTevAlphaIn(1, 7, 4, 5, 7);
            if (esp->m_Tool_flg & 0x20000) {
                GXSetTevAlphaOp(1, 0, 0, 2, 1, 0);
            } else {
                GXSetTevAlphaOp(1, 0, 0, 0, 1, 0);
            }
            stages = 2;
            texGens++;
        }
    }
    GXSetNumTevStages(stages);
    GXSetNumTexGens(texGens);
    GXBegin(0x80, 0, 4);
    GXPosition3f32(x0, y0, z);
    GXNormal3s8(0, 1, 0);
    GXTexCoord2f32(s0, t0);
    GXPosition3f32(x0 + sx, y0, z);
    GXNormal3s8(0, 1, 0);
    GXTexCoord2f32(s1, t0);
    GXPosition3f32(x0 + sx, y0 - sy, z);
    GXNormal3s8(0, 1, 0);
    GXTexCoord2f32(s1, t1);
    GXPosition3f32(x0, y0 - sy, z);
    GXNormal3s8(0, 1, 0);
    GXTexCoord2f32(s0, t1);
    GXSetNumTevStages(1);
    GXSetNumTexGens(0);
    GXSetNumIndStages(0);
    GXSetTevDirect(0);
    GXSetTevDirect(1);
    LightMgr.setFog();
}

// Frame-buffer sprite: the frame is copied into a texture and drawn on the sprite quad,
// modulated by the sprite's own texture (type: TEV colour scale 0..2).
void EspCommonTransNega(cEsp* esp, u32 type)
{
    static Mtx Matrix = {
        {0.001953125f, 0.0f, 0.0f, 0.0f},
        {0.0f, 0.0029762f, -0.167f, 0.0f},
        {0.0f, 0.0f, 1.0f, 0.0f},
    };
    Mtx44 proj;
    Mtx inv;
    EspAnmData* anm;
    GXColor fog;
    void* buf;
    f32 sx;
    f32 sy;
    f32 ox;
    f32 oy;
    f32 x0;
    f32 y0;
    f32 z;
    f32 zero;
    f32 s0;
    f32 s1;
    f32 t0;
    f32 t1;

    if (!esp->ChannelSet()) {
        return;
    }
    if (!EspGetAnmAddr(esp->m_Tex_id, &anm)) {
        pLog->err(0, 0, "ESP : TexId[%x] no data", esp->m_Tex_id);
        return;
    }
    CameraCurrentProjection();
    if (ESP_PARTS_SCREEN(esp)) {
        PSMTXIdentity(esp->m_Mat);
        low_RotMatrix(esp->m_Mat, &esp->m_Ang);
        TransMatrix(esp->m_Mat, &esp->m_Pos);
        C_MTXOrtho(proj, 0.0f, 448.0f, 0.0f, 512.0f, 0.0f, -100.0f);
        GXSetProjection(proj, 1);
    } else if (!(esp->m_Tool_flg & 1)) {
        Vec p;
        Mtx m;

        PSMTXIdentity(esp->m_Mat);
        PSMTXRotRad(esp->m_Mat, 'z', esp->m_Ang.z);
        PSMTXConcat(pG->Cam.v_mat, esp->parent->mat, m);
        PSMTXMultVec(m, &esp->m_Pos, &p);
        esp->m_Mat[0][3] = p.x;
        esp->m_Mat[1][3] = p.y;
        esp->m_Mat[2][3] = p.z;
    } else {
        Mtx m;

        PSMTXIdentity(esp->m_Mat);
        low_RotMatrix(esp->m_Mat, &esp->m_Ang);
        TransMatrix(esp->m_Mat, &esp->m_Pos);
        PSMTXConcat(pG->Cam.v_mat, esp->parent->mat, m);
        PSMTXConcat(m, esp->m_Mat, esp->m_Mat);
    }
    GXTexObj tex;
    PSMTXInverse(esp->m_Mat, inv);
    PSMTXTranspose(inv, inv);
    GXLoadNrmMtxImm(inv, 0);
    GXLoadPosMtxImm(esp->m_Mat, 0);
    GXSetCurrentMtx(0);
    EspTexSet(esp->m_Tex_id, esp->m_Ptn_no);
    GXSetBlendMode(esp->xA4, esp->xA5, esp->xA6, esp->xA7);
    esp->CommonStateSet();
    GXClearVtxDesc();
    GXSetVtxDesc(9, 1);
    GXSetVtxDesc(0xA, 1);
    GXSetVtxDesc(0xD, 1);
    GXSetVtxAttrFmt(0, 9, 1, 4, 0);
    GXSetVtxAttrFmt(0, 0xA, 0, 1, 0);
    GXSetVtxAttrFmt(0, 0xD, 1, 4, 0);
    sx = esp->m_Size_base_x * esp->m_Size_mul;
    sy = esp->m_Size_base_y * esp->m_Size_mul;
    ox = -anm->Cx;
    oy = (f32) anm->Cy;
    z = 1.0f;
    zero = 0.0f;
    if (ox == zero) {
        ox = -anm->Width * 0.5f;
    }
    if (oy == zero) {
        oy = anm->Height * 0.5f;
    }
    x0 = ox * sx / anm->Width;
    y0 = oy * sy / anm->Height;
    ESP_TEXCOORD_SET()
    fog.r = fog.g = fog.b = fog.a = 0;
    GXSetFog(0, 0.0f, 0.0f, ZNEAR, ZFAR, fog);
    buf = GetDrawTmpBufAddr(3);
    if (buf == NULL) {
        pLog->warn(0, 0, "Esp0d() : not enough memory");
        return;
    }
    f32 ofs = 56.0f;
    GXSetTexCopySrc(0, (u32) ofs, (u32) Screen.width, (u32) (Screen.height - ofs));
    GXSetTexCopyDst((u32) Screen.width / 2, (u32) ((f32) ((u32) Screen.height / 2) - ofs), 6, 1);
    GXCopyTex(buf, 0);
    GXPixModeSync();
    GXInvalidateTexAll();
    GXInitTexObj(&tex, buf, (u32) Screen.width / 2, (u32) ((f32) ((u32) Screen.height / 2) - ofs), 6, 0, 0, 0);
    GXLoadTexObj(&tex, 1);
    if (ESP_PARTS_SCREEN(esp)) {
        Mtx tm;

        PSMTXConcat(Matrix, esp->m_Mat, tm);
        GXLoadTexMtxImm(tm, 0x1E, 1);
        GXSetTexCoordGen(0, 1, 0, 0x1E);
    } else {
        Mtx tm;
        Mtx pm;

        C_MTXLightPerspective(pm, pG->Cam.param.fovy, 1.3333334f, 0.5f, -0.6666667f, 0.5f, 0.5f);
        PSMTXConcat(pm, esp->m_Mat, tm);
        GXLoadTexMtxImm(tm, 0x1E, 0);
        GXSetTexCoordGen(0, 0, 0, 0x1E);
    }
    GXSetTevOrder(0, 0, 1, 4);
    GXSetTevColorIn(0, 0xF, 0xF, 0xF, 8);
    switch (type) {
    case 0:
        GXSetTevColorOp(0, 0, 0, 0, 1, 0);
        break;
    case 1:
        GXSetTevColorOp(0, 0, 0, 1, 1, 0);
        break;
    case 2:
        GXSetTevColorOp(0, 0, 0, 2, 1, 0);
        break;
    }
    GXSetTevAlphaIn(0, 7, 7, 7, 5);
    GXSetTevAlphaOp(0, 0, 0, 0, 1, 0);
    GXSetTevOrder(1, 0xFF, 0xFF, 4);
    GXSetTevColorIn(1, 0xA, 0xF, 0, 0xF);
    GXSetTevColorOp(1, 0, 0, 0, 1, 0);
    GXSetTevAlphaIn(1, 7, 7, 7, 5);
    GXSetTevAlphaOp(1, 0, 0, 0, 1, 0);
    GXSetNumTexGens(2);
    GXSetTexCoordGen(1, 1, 4, 0x3C);
    GXSetNumTevStages(2);
    GXSetTevOrder(2, 1, 0, 4);
    GXSetTevColorIn(2, 0xF, 0xF, 0xF, 0);
    GXSetTevColorOp(2, 0, 0, 0, 1, 0);
    GXSetTevAlphaIn(2, 7, 0, 4, 7);
    GXSetTevAlphaOp(2, 0, 0, 0, 1, 0);
    GXSetNumTevStages(3);
    GXBegin(0x80, 0, 4);
    GXPosition3f32(x0, y0, z);
    GXNormal3s8(0, 1, 0);
    GXTexCoord2f32(s0, t0);
    GXPosition3f32(x0 + sx, y0, z);
    GXNormal3s8(0, 1, 0);
    GXTexCoord2f32(s1, t0);
    GXPosition3f32(x0 + sx, y0 - sy, z);
    GXNormal3s8(0, 1, 0);
    GXTexCoord2f32(s1, t1);
    GXPosition3f32(x0, y0 - sy, z);
    GXNormal3s8(0, 1, 0);
    GXTexCoord2f32(s0, t1);
    GXSetNumTevStages(1);
    GXSetNumTexGens(0);
    GXSetNumIndStages(0);
    GXSetTevDirect(0);
    GXSetTevDirect(1);
    LightMgr.setFog();
}

// Base move: only reached for an id without its own class; logs the id.
void cEsp::move()
{
    pLog->err(0, 0, "ESP : ESP_ID[%x] move() invalid", m_Id);
}

#if defined(RE4DC_FX_MOVE) && RE4DC_FX_MOVE
// GAME_FX_MOVE (game30.mk, lane fx; exact): CommonMove with ColorUpdate and SQRTF inline, and
// AnmMove with EspGetAnmAddr inline. The same float operations on the same operands, the same
// stores before each PushEsp; the fields from m_Pos to m_D_size_plus are contiguous, so they are
// read through one walking pointer (SH-4 FP loads have no displacement form: a field read is
// otherwise three instructions). The kernel returns why the effect died (the caller pushes it) so
// the =2 check build can run it on a copy beside the source functions and compare every field
// ("FXM" lines).
// SQRTF (math_sub.cpp), inline.
static inline f32 fxSqrtf(f32 x)
{
    if (x <= 0.00001f) {
        return 0.0f;
    }
    return __builtin_sqrtf(x);
}
// ColorUpdate without its PushEsp: 1 when alpha fell below 4 (the caller pushes).
static inline int fxColorKernel(cEsp* e, int life)
{
    const int maxc = e->m_Col_max_cnt;

    if (maxc < life) {
        if (maxc + e->m_Col_start_cnt <= life) {
            f32* q = &e->m_Col_r;   // m_Col_r, g, b, a, then m_Col_d_r, g, b, a
            f32 r, g, b, a, dr, dg, db, da;
            const f32 top = 255.0f;
            FXL(q, r);
            FXL(q, g);
            FXL(q, b);
            FXL(q, a);
            FXL(q, dr);
            FXL(q, dg);
            FXL(q, db);
            FXL(q, da);
            r *= dr;
            g *= dg;
            b *= db;
            a *= da;
            if (r > top) {
                r = top;
            }
            if (g > top) {
                g = top;
            }
            if (b > top) {
                b = top;
            }
            if (a > top) {
                a = top;
            }
            q = &e->m_Col_a + 1;
            FXS(q, a);
            FXS(q, b);
            FXS(q, g);
            FXS(q, r);
            if (a < 4.0f) {
                return 1;
            }
        }
    } else if (maxc != 0) {
        f32 rate = (f32) life / (f32) maxc;
        if (e->m_Blend_type == 3) {
            e->m_Col_r = (f32) e->m_Col_start_r * rate;
            e->m_Col_g = (f32) e->m_Col_start_g * rate;
            e->m_Col_b = (f32) e->m_Col_start_b * rate;
        }
        e->m_Col_a = (f32) e->m_Col_start_a * rate;
    }
    return 0;
}
// CommonMove without its PushEsp calls: 0 alive, 1 died at the scale, 2 at the colour, 3 at the
// life end (the caller pushes, as the source does at each of those points). Inlined, so the code
// stays under the name the link order places (cEsp::CommonMove).
static inline __attribute__((always_inline)) int fxCommonKernel(cEsp* e)
{
    int life;
    f32* q;

    if (e->parent != pEffParentWorld && e->m_Release_time != 0xFF && e->m_Release_time <= e->m_Life_time) {
        e->ApplyMatrix(e->parent->mat);
        e->parent = pEffParentWorld;
    }
    life = e->m_Life_time;
    if (e->m_Pos_start_cnt == 0 || e->m_Pos_start_cnt <= life) {
        f32 px, py, pz, sx, sy, sz, d, ax, ay, az;
        q = &e->m_Pos.x;   // m_Pos, m_Speed, m_D_speed, m_Speed_plus
        FXL(q, px);
        FXL(q, py);
        FXL(q, pz);
        FXL(q, sx);
        FXL(q, sy);
        FXL(q, sz);
        FXL(q, d);
        FXL(q, ax);
        FXL(q, ay);
        FXL(q, az);
        px = px + sx;
        py = py + sy;
        pz = pz + sz;
        sx = sx + ax;
        sy = sy + ay;
        sz = sz + az;
        sx = sx * d;
        sy = sy * d;
        sz = sz * d;
        q = &e->m_D_speed;
        FXS(q, sz);
        FXS(q, sy);
        FXS(q, sx);
        FXS(q, pz);
        FXS(q, py);
        FXS(q, px);
    }
    if (e->m_Size_start_cnt == 0 || e->m_Size_start_cnt <= life) {
        f32 mul, plus, dz;
        q = &e->m_Size_mul;   // m_Size_mul, m_Size_plus, m_D_size_plus
        FXL(q, mul);
        FXL(q, plus);
        FXL(q, dz);
        mul += plus;
        plus *= dz;
        q = &e->m_D_size_plus;
        FXS(q, plus);
        FXS(q, mul);
        if (mul <= 0.0f) {
            return 1;
        }
    }
    {
        f32 gx, gy, gz, hx, hy, hz;
        q = &e->m_Ang.x;   // m_Ang, m_Ang_plus
        FXL(q, gx);
        FXL(q, gy);
        FXL(q, gz);
        FXL(q, hx);
        FXL(q, hy);
        FXL(q, hz);
        gx = gx + hx;
        gy = gy + hy;
        gz = gz + hz;
        q = &e->m_Ang_plus.x;
        FXS(q, gz);
        FXS(q, gy);
        FXS(q, gx);
    }
    if (fxColorKernel(e, life)) {
        return 2;
    }
    if (e->m_Life_max != 0 && e->m_Life_max <= life) {
        return 3;
    }
    e->m_Life_time = life + 1;
    {
        f32 bx, by, mul;
        q = &e->m_Size_base_x;   // m_Size_base_x, m_Size_base_y, m_Size_mul
        FXL(q, bx);
        FXL(q, by);
        FXL(q, mul);
        e->m_Radius = fxSqrtf(bx * bx + by * by) * mul;
    }
    return 0;
}
#if RE4DC_FX_MOVE == 2
// The kernel for callers in other units (esp48's =2 copy): 0 alive, else why it died (not pushed).
extern "C" int re4dc_fx_common_kernel(cEsp* e)
{
    return fxCommonKernel(e);
}
#include <string.h>
extern "C" void re4dc_log(const char* fmt, ...);
static u32 fxmCalls, fxmMis, fxmDead, fxmAnm, fxmAnmMis;
#endif
int cEsp::CommonMove()
{
#if RE4DC_FX_MOVE == 2
    // The kernel on a copy, the source on the live effect; every byte of the two compared.
    u32 copy[0x150 / 4];
    u32 live[0x150 / 4];
    int why;
    int ret;
    u32 i;
    memcpy(copy, this, 0x150);
    why = fxCommonKernel((cEsp*) copy);
    ret = CommonMoveSrc();
    fxmCalls++;
    if ((ret == 0) != (why != 0)) {
        fxmMis++;
    } else if (why == 0) {
        memcpy(live, this, 0x150);
        for (i = 0; i < 0x150 / 4; i++) {
            if (copy[i] != live[i]) {
                fxmMis++;
                break;
            }
        }
    } else {
        fxmDead++;
    }
    if (fxmCalls % 4096 == 0) {
        re4dc_log("FXM calls=%u mismatch=%u dead=%u anm=%u anm_mismatch=%u\n", fxmCalls, fxmMis, fxmDead, fxmAnm,
                  fxmAnmMis);
    }
    return ret;
#else
    if (fxCommonKernel(this)) {
        PushEsp(this);
        return 0;
    }
    return 1;
#endif
}
#endif
#if !(defined(RE4DC_FX_MOVE) && RE4DC_FX_MOVE) || RE4DC_FX_MOVE == 2
// Per-frame update shared by every effect: detaches from the parent parts after m_Release_time
// frames (baking the parent matrix into pos/speed), integrates speed (+Speed_plus, *D_speed) once
// m_Pos_start_cnt has passed, scale (m_Size_mul += m_Size_plus, *D_size_plus; dies at <= 0) once
// m_Size_start_cnt has passed, angle, colour (ColorUpdate), and kills the effect (PushEsp) when
// m_Life_time reaches m_Life_max. Returns 0 when the effect died this frame. Updates m_Radius.
#if defined(RE4DC_FX_MOVE) && RE4DC_FX_MOVE == 2
int cEsp::CommonMoveSrc()
#else
int cEsp::CommonMove()
#endif
{
    if (parent != pEffParentWorld && m_Release_time != 0xFF && m_Release_time <= m_Life_time) {
        ApplyMatrix(parent->mat);
        parent = pEffParentWorld;
    }
    if (m_Pos_start_cnt == 0 || m_Pos_start_cnt <= m_Life_time) {
        PSVECAdd(&m_Pos, &m_Speed, &m_Pos);
        PSVECAdd(&m_Speed, &m_Speed_plus, &m_Speed);
        PSVECScale(&m_Speed, &m_Speed, m_D_speed);
    }
    if (m_Size_start_cnt == 0 || m_Size_start_cnt <= m_Life_time) {
        m_Size_mul += m_Size_plus;
        m_Size_plus *= m_D_size_plus;
        if (m_Size_mul <= 0.0f) {
            PushEsp(this);
            return 0;
        }
    }
    PSVECAdd(&m_Ang, &m_Ang_plus, &m_Ang);
    if (!ColorUpdate()) {
        return 0;
    }
    if (m_Life_max != 0 && m_Life_max <= m_Life_time) {
        PushEsp(this);
        return 0;
    }
    m_Life_time++;
    m_Radius = SQRTF(m_Size_base_x * m_Size_base_x + m_Size_base_y * m_Size_base_y) * m_Size_mul;
    return 1;
}
#endif

// Colour envelope: fades in over the first m_Col_max_cnt frames (alpha, and rgb for Blend_type 3),
// holds for m_Col_start_cnt frames, then multiplies rgba by m_Col_d_* every frame (clamped to 255)
// and kills the effect when alpha drops below 4. Returns 0 when it died.
int cEsp::ColorUpdate()
{
    if (m_Col_max_cnt < m_Life_time) {
        if (m_Col_max_cnt + m_Col_start_cnt <= m_Life_time) {
            m_Col_r *= m_Col_d_r;
            m_Col_g *= m_Col_d_g;
            m_Col_b *= m_Col_d_b;
            m_Col_a *= m_Col_d_a;
            if (m_Col_r > 255.0f) {
                m_Col_r = 255.0f;
            }
            if (m_Col_g > 255.0f) {
                m_Col_g = 255.0f;
            }
            if (m_Col_b > 255.0f) {
                m_Col_b = 255.0f;
            }
            if (m_Col_a > 255.0f) {
                m_Col_a = 255.0f;
            }
            if (m_Col_a < 4.0f) {
                PushEsp(this);
                return 0;
            }
        }
    } else if (m_Col_max_cnt != 0) {
        f32 rate = (f32) m_Life_time / (f32) m_Col_max_cnt;
        if (m_Blend_type == 3) {
            m_Col_r = (f32) m_Col_start_r * rate;
            m_Col_g = (f32) m_Col_start_g * rate;
            m_Col_b = (f32) m_Col_start_b * rate;
        }
        m_Col_a = (f32) m_Col_start_a * rate;
    }
    return 1;
}

// Base per-id parameter set-up: nothing to read (returns 1); ids with their own work override it.
int cEsp::SetFreeWork(EspGenWork* gen, u32* seed)
{
    return 1;
}

// Advances the texture animation: m_Anm_cnt accumulates m_Anm_rate (1/32 frame units) against the
// current pattern's frame count and steps m_Ptn_no; at the end Loop 0 returns 0 (animation over,
// callers stop drawing), 1 restarts, 2 holds the last pattern. Same for the mask animation
// (m_MaskTex_id / m_MaskPtn_no) when Tool_flg 0x4000.
#if defined(RE4DC_FX_MOVE) && RE4DC_FX_MOVE
// AnmMove with EspGetAnmAddr inline (quiet: no error lines, for the =2 copy). Inlined into
// cEsp::AnmMove (the name the link order places).
static inline __attribute__((always_inline)) int fxAnmKernel(cEsp* e, int quiet)
{
    EspTexWk* tw = &g_pEspSys->Esp_tex_tbl[e->m_Tex_id];
    EspAnmData* anm;
    u32 time;

    if (tw->Owner == 0xD2) {
        if (!quiet) {
            pLog->err(0, 0, "ESP : TexId[%x] no data", e->m_Tex_id);
        }
        return 0;
    }
    anm = tw->pAnm;
    if (anm->Data_num == 0) {
        time = 1;
    } else {
        time = anm->Frame_cnt[anm->Frames + e->m_Ptn_no];
    }
    e->m_Anm_cnt += e->m_Anm_rate;
    while ((e->m_Anm_cnt >> 5) > (u16) time) {
        e->m_Ptn_no++;
        e->m_Anm_cnt -= time << 5;
        if (e->m_Ptn_no >= anm->Frames) {
            switch (anm->Loop & 3) {
            case 0:
                return 0;
            case 1:
                e->m_Ptn_no = 0;
                break;
            case 2:
                e->m_Ptn_no = anm->Frames - 1;
                break;
            }
        }
    }
    if (e->m_Tool_flg & 0x4000) {
        tw = &g_pEspSys->Esp_tex_tbl[e->m_MaskTex_id];
        if (tw->Owner == 0xD2) {
            if (!quiet) {
                pLog->err(0, 0, "ESP : MaskTexId[%x] no data", e->m_Tex_id);
            }
            return 0;
        }
        anm = tw->pAnm;
        if (anm->Data_num == 0) {
            time = 1;
        } else {
            time = anm->Frame_cnt[anm->Frames + e->m_MaskPtn_no];
        }
        e->m_MaskAnm_cnt += e->m_Anm_rate;
        while ((e->m_MaskAnm_cnt >> 5) > (u16) time) {
            e->m_MaskPtn_no++;
            e->m_MaskAnm_cnt -= time << 5;
            if (e->m_MaskPtn_no >= anm->Frames) {
                switch (anm->Loop & 3) {
                case 0:
                    return 0;
                case 1:
                    e->m_MaskPtn_no = 0;
                    break;
                case 2:
                    e->m_MaskPtn_no = anm->Frames - 1;
                    break;
                }
            }
        }
    }
    return 1;
}
#if RE4DC_FX_MOVE == 2
extern "C" int re4dc_fx_anm_kernel(cEsp* e, int quiet)
{
    return fxAnmKernel(e, quiet);
}
#endif
int cEsp::AnmMove()
{
#if RE4DC_FX_MOVE == 2
    u32 copy[0x150 / 4];
    int a;
    int b;
    memcpy(copy, this, 0x150);
    a = fxAnmKernel((cEsp*) copy, 1);
    b = AnmMoveSrc();
    fxmAnm++;
    if (a != b || memcmp(copy, this, 0x150) != 0) {
        fxmAnmMis++;
    }
    return b;
#else
    return fxAnmKernel(this, 0);
#endif
}
#endif
#if !(defined(RE4DC_FX_MOVE) && RE4DC_FX_MOVE) || RE4DC_FX_MOVE == 2
#if defined(RE4DC_FX_MOVE) && RE4DC_FX_MOVE == 2
int cEsp::AnmMoveSrc()
#else
int cEsp::AnmMove()
#endif
{
    EspAnmData* anm;
    u32 time;

    if (!EspGetAnmAddr(m_Tex_id, &anm)) {
        pLog->err(0, 0, "ESP : TexId[%x] no data", m_Tex_id);
        return 0;
    }
    if (anm->Data_num == 0) {
        time = 1;
    } else {
        time = anm->Frame_cnt[anm->Frames + m_Ptn_no];
    }
    m_Anm_cnt += m_Anm_rate;
    while ((m_Anm_cnt >> 5) > (u16) time) {
        m_Ptn_no++;
        m_Anm_cnt -= time << 5;
        if (m_Ptn_no >= anm->Frames) {
            switch (anm->Loop & 3) {
            case 0:
                return 0;
            case 1:
                m_Ptn_no = 0;
                break;
            case 2:
                m_Ptn_no = anm->Frames - 1;
                break;
            }
        }
    }
    if (m_Tool_flg & 0x4000) {
        if (!EspGetAnmAddr(m_MaskTex_id, &anm)) {
            pLog->err(0, 0, "ESP : MaskTexId[%x] no data", m_Tex_id);
            return 0;
        }
        if (anm->Data_num == 0) {
            time = 1;
        } else {
            time = anm->Frame_cnt[anm->Frames + m_MaskPtn_no];
        }
        m_MaskAnm_cnt += m_Anm_rate;
        while ((m_MaskAnm_cnt >> 5) > (u16) time) {
            m_MaskPtn_no++;
            m_MaskAnm_cnt -= time << 5;
            if (m_MaskPtn_no >= anm->Frames) {
                switch (anm->Loop & 3) {
                case 0:
                    return 0;
                case 1:
                    m_MaskPtn_no = 0;
                    break;
                case 2:
                    m_MaskPtn_no = anm->Frames - 1;
                    break;
                }
            }
        }
    }
    return 1;
}
#endif

// Sets the sprite's material colour for the draw: lit sprites (Tool_flg 0x40) get the effect light
// list, Tool_flg 0x80/0x20000 select colour/alpha scaling; m_Flg bit 0 premultiplies rgb by alpha
// (additive sprites); the final colour filter (EffGetFinalCol) is applied unless m_Flg bit 2; the
// sprite fades out between m_Del_far and m_Del_near (x10 units along the camera axis). Returns 1
// when the resulting alpha is non-zero (worth drawing).
#line 1730 "D:/Bio4/Prog/esp_sub.cpp"
int cEsp::ChannelSet()
{
    GXColor col;
    GXColor fin;
    Vec p;
    Vec dir;
    Vec d;
    cEspSystem* sys = g_pEspSys;

    if (m_Tool_flg & 0x40) {
#if !RE4DC_EFFECT_LEAN
        GXSetTevOp(0, 0);
        GXSetTevColorIn(0, 0xF, 8, 0xA, 0xF);
#endif
        GXSetTevColorOp(0, 0, 0, 2, 1, 0);
        commonEspLightSet(sys->lightList.p, sys->lightList.num);
    } else {
#if !RE4DC_EFFECT_LEAN
        GXSetTevOp(0, 0);
#endif
        if (m_Tool_flg & 0x80) {
            GXSetTevColorOp(0, 0, 0, 2, 1, 0);
        }
#if !RE4DC_EFFECT_LEAN
        if (m_Tool_flg & 0x20000) {
            GXSetTevAlphaOp(0, 0, 0, 2, 1, 0);
        }
        GXSetNumChans(1);
#endif
        GXSetChanCtrl(4, 0, 0, 0, 0, 0, 2);
    }
    if (m_Flg & 1) {
        col.r = (u8) (m_Col_r * m_Col_a * (1.0f / 255.0f));
        col.g = (u8) (m_Col_g * m_Col_a * (1.0f / 255.0f));
        col.b = (u8) (m_Col_b * m_Col_a * (1.0f / 255.0f));
        col.a = 0xFF;
    } else {
        col.r = (u8) m_Col_r;
        col.g = (u8) m_Col_g;
        col.b = (u8) m_Col_b;
        col.a = (u8) m_Col_a;
    }
    if (!(m_Flg & 4) && EffIsSetFinalCol()) {
        EffGetFinalCol(&fin);
        col.r = (u32) col.r * fin.r >> 8;
        col.g = (u32) col.g * fin.g >> 8;
        col.b = (u32) col.b * fin.b >> 8;
        col.a = (u32) col.a * fin.a >> 8;
    }
    if (m_Del_far != 0) {
        Camera* cam;
        f32 dot;

        if (parent != pEffParentWorld) {
            PSMTXMultVec(parent->mat, &m_Pos, &p);
        } else {
            p = m_Pos;
        }
        cam = &pG->Cam;
        dir.x = cam->param.at.x - cam->param.pos.x;
        dir.y = cam->param.at.y - cam->param.pos.y;
        dir.z = cam->param.at.z - cam->param.pos.z;
#line 1798 "D:/Bio4/Prog/esp_sub.cpp"
        VECNormalize(&dir, &dir);
        d.x = p.x - cam->param.pos.x;
        d.y = p.y - cam->param.pos.y;
        d.z = p.z - cam->param.pos.z;
        dot = PSVECDotProduct(&dir, &d);
        if (dot < m_Del_far * 10.0f) {
            f32 rate = 1.0f - (m_Del_far * 10.0f - dot) / ((m_Del_far - m_Del_near) * 10.0f);
#if RE4DC_EFFECT_FADE_CLAMP
            // EFFECT_FADE_CLAMP: nearer than m_Del_near the rate is negative. The GameCube stores these (u8)
            // casts with psq_st through GQR2 (u8), which saturates to 0 (main.dol 0x8011edd4..0x8011ee5c); SH-4's
            // ftrc + extu.b keeps the low byte of the negative integer, so a sprite inside its near distance was
            // drawn near-opaque (alpha 70 x rate -0.04 -> 254). The rate is clamped at 0, the GameCube's result.
            if ((re4dc_ps2fx & PS2FX_CLAMP) && rate < 0.0f) {
                rate = 0.0f;
            }
#endif
            if (m_Flg & 1) {
                col.r = (u8) (col.r * rate);
                col.g = (u8) (col.g * rate);
                col.b = (u8) (col.b * rate);
            } else {
                col.a = (u8) (col.a * rate);
            }
        }
    }
    GXSetChanMatColor(4, col);
#if RE4DC_EFFECT_SPRITES
    s_effect_col = col;
#endif
    {
        int ret = 0;
        if (col.a != 0) {
            ret = 1;
        }
        return ret;
    }
}

// Transforms position, speed and acceleration by m (world attachment); with Tool_flg bit 0 also
// rotates m_Ang by the matrix.
void cEsp::ApplyMatrix(Mtx m)
{
    Mtx r;

    PSMTXMultVec(m, &m_Pos, &m_Pos);
    PSMTXMultVecSR(m, &m_Speed, &m_Speed);
    PSMTXMultVecSR(m, &m_Speed_plus, &m_Speed_plus);
    if (m_Tool_flg & 1) {
        low_RotMatrix(r, &m_Ang);
        PSMTXConcat(m, r, r);
        Matrix2AxisAngle(r, &m_Ang);
    }
}

// GX state shared by the sprite draws: no culling, alpha compare, Z test without write, one TEV
// stage with texture matrix 0x1E.
void cEsp::CommonStateSet()
{
    GXSetCullMode(0);
    GXSetAlphaCompare(4, 1, 1, 4, 1);
    GXSetZMode(1, 3, 0);
    GXSetNumTevStages(1);
    GXSetTevOrder(0, 0, 0, 4);
    GXSetNumTexGens(1);
    GXSetTexCoordGen(0, 1, 4, 0x1E);
}

// Effects are pool objects: the constructor does nothing (PullEsp clears the work).
cEsp::cEsp()
{
}

// Nothing to release in the base class.
cEsp::~cEsp()
{
}

// Hook run by PushEsp for ids that own external resources (cloth, buffers); empty in the base.
void cEsp::Destruct()
{
}

// Spawns record `no` of est table (owner, id) as one esp at the origin (identity matrix, fixed seed),
// bypassing the sequence timing; only Kind 0 records are allowed. bNoSuspend == 1 marks it with
// Core_flg bit 0 (kept through pauses). Returns 1 with *out = the esp, 0 (with the dummy) on error.
int EspEstSetSelect(int owner, int id, int no, cEsp** out, int bNoSuspend)
{
    EspSeqData* head;
    EspGenWork* rec;
    EspInfo info;
    Mtx m;
    u8 type;

    head = EspGetEstAddr(owner, id, 0);
    if (head == 0) {
        pLog->err(0, 0, "EspEstSetSelect:[%x/0x%02x] OWNER Invalid", owner, id);
        return 0;
    }
    if ((u32) no >= head->num) {
        pLog->err(0, 0, "EspEstSetSelect() : invalid no[%d] MAX=%d", no, head->num);
        return 0;
    }
    u32 seed = 0x12345678;
#if defined(RE4DC_GAME) && !defined(__PPC__)
    EspGenWork scratch;
    EspGenWork* reference = re4dc_effect_ref(head, no);
    rec = re4dc_effect_read(reference, scratch);
#else
    rec = &head->rec[no];
#endif
    type = rec->Kind;
    if (type != 0) {
        if (type == 1) {
            pLog->err(0, 0, "EspEstSetSelect : can't call Espgen.");
            return 0;
        }
        pLog->err(0, 0, "EspEstSetSelect : KIND[%d] is invalid.", type);
        return 0;
    }
    PSMTXIdentity(m);
    memclr_asm(&info, sizeof(info));
    if (bNoSuspend == 1) {
        info.Core_flg |= 1;
    }
#if defined(RE4DC_GAME) && !defined(__PPC__)
    rec = reference;
#endif
    return EspSeqSet(rec, &info, &seed, 0, &m, 0, 0.0f, out, 0, 0) == 1;
}

// Creates one esp from an effect record: Id 0xFC..0xFF are effect models (EfmSeqSet); otherwise
// pulls an esp of that id, copies the record (position/speed/acceleration/angle with the R_*
// random spreads from `seed`, sizes, colours and fade counts, blend table, life, release time,
// shimmer/mask ids, delete distances x10), resolves the parent (Parent_no scroll object unless
// event mode; Parts_no 0xFF = world through *mtx, 0xF8..0xFD screen, 0xFE free, else a parts of
// `model`, Tool_flg 0x20 = rotation only), runs the id's SetFreeWork, then the EspSeqOpt
// overrides/multipliers (speed, size, colour). flg != 0 rotates the speed by `f` radians about y
// (controller angle spread). Returns 1 with *out set; 0 with the dummy esp on failure.
int EspSeqSet(EspGenWork* rec, EspInfo* info, u32* seed, cModel* model, Mtx* mtx, int flg, f32 f, cEsp** out,
              EspSeqOpt* pSct, Vec* pos)
{
#if defined(RE4DC_GAME) && !defined(__PPC__)
    EspGenWork scratch;
    rec = re4dc_effect_read(rec, scratch);
#endif
    static int bl[6][4] = {
        {1, 4, 5, 0}, {1, 4, 1, 0}, {1, 1, 1, 0}, {1, 2, 1, 0}, {1, 2, 0, 0}, {1, 4, 3, 0},
    };
    Vec v;
    Mtx m;
    Mtx m2;
    EspPtr e;
    f32 rnd;
    int ret;
    cModel* parts;

    if ((u8) (rec->Id + 4) <= 3) {
        EfmSeqSet(rec, (EfmCore*) info, seed, model, *mtx, 0, 0.0f, pos);
        *out = EspGetDmyPtr();
        return 1;
    }
    if (rec->Id == 0x3F) {
        pLog->err(0, 0, "ESP : ESP_ID[%x] is invalid.", rec->Id);
        *out = EspGetDmyPtr();
        return 0;
    }
    if (rec->Id != 3 && rec->Id != 9 && rec->Id != 0xC && !EspChkTexId(rec->Tex_id)) {
        pLog->err(0, 0, "ESP : TEX_ID[%x] not initialized.", rec->Tex_id);
        *out = EspGetDmyPtr();
        return 0;
    }
    if (PullEsp(&e.p, rec->Id) != 0) {
        ESP_INFO_SET(e.p, info);
        e.p->m_Id = rec->Id;
        e.p->m_Tex_id = rec->Tex_id;
        e.p->m_Type = rec->Type;
        e.p->m_Parts_no = rec->Parts_no;
        if (!(info->Core_flg & 0x1000) && rec->Parent_no != 0) {
            model = SmdGetObjPtr(rec->Parent_no - 1);
            if (model == 0) {
                pLog->err(0, 0, "ESP : PARENT_NO[%d] Invalid.", rec->Parent_no);
                PushEsp(e.p);
                *out = EspGetDmyPtr();
                return 0;
            }
        }
        e.p->m_Tool_flg = rec->Tool_flg;
        if (e.p->m_Tool_flg & 8) {
            if (fRandSeed1_1(seed) > 0.0f) {
                e.p->m_Tool_flg |= 2;
            } else {
                e.p->m_Tool_flg &= ~2;
            }
        }
        if (e.p->m_Tool_flg & 0x10) {
            if (fRandSeed1_1(seed) > 0.0f) {
                e.p->m_Tool_flg |= 4;
            } else {
                e.p->m_Tool_flg &= ~4;
            }
        }
        e.p->m_Pos = rec->Pos;
        e.p->m_Pos.x += rec->R_pos.x * fRandSeed1_1(seed);
        e.p->m_Pos.y += rec->R_pos.y * fRandSeed1_1(seed);
        e.p->m_Pos.z += rec->R_pos.z * fRandSeed1_1(seed);
        e.p->m_Speed = rec->Speed;
        e.p->m_Speed.x += rec->R_speed.x * fRandSeed1_1(seed);
        e.p->m_Speed.y += rec->R_speed.y * fRandSeed1_1(seed);
        e.p->m_Speed.z += rec->R_speed.z * fRandSeed1_1(seed);
        if (flg) {
            v.x = 0.0f;
            v.y = f;
            v.z = 0.0f;
            RotMatrixZXY(m, &v);
            PSMTXMultVecSR(m, &e.p->m_Speed, &e.p->m_Speed);
        }
        e.p->m_D_speed = rec->D_speed;
        e.p->m_Speed_plus = rec->Speed_plus;
        e.p->m_Speed_plus.x += rec->R_speed_plus.x * fRandSeed1_1(seed);
        e.p->m_Speed_plus.y += rec->R_speed_plus.y * fRandSeed1_1(seed);
        e.p->m_Speed_plus.z += rec->R_speed_plus.z * fRandSeed1_1(seed);
        e.p->m_Ang = rec->Ang;
        e.p->m_Ang.x += rec->R_ang.x * fRandSeed1_1(seed);
        e.p->m_Ang.y += rec->R_ang.y * fRandSeed1_1(seed);
        e.p->m_Ang.z += rec->R_ang.z * fRandSeed1_1(seed);
        PSVECScale(&e.p->m_Ang, &e.p->m_Ang, DEG2RAD);
        e.p->m_Ang_plus = rec->Ang_plus;
        e.p->m_Ang_plus.x += rec->R_ang_plus.x * fRandSeed1_1(seed);
        e.p->m_Ang_plus.y += rec->R_ang_plus.y * fRandSeed1_1(seed);
        e.p->m_Ang_plus.z += rec->R_ang_plus.z * fRandSeed1_1(seed);
        PSVECScale(&e.p->m_Ang_plus, &e.p->m_Ang_plus, DEG2RAD);
        e.p->m_Size_base_x = rec->Size_base_x;
        e.p->m_Size_base_y = rec->Size_base_y;
        e.p->m_Size_mul = 1.0f;
        rnd = rec->R_size_base * fRandSeed1_1(seed);
        e.p->m_Size_base_x += rnd;
        e.p->m_Size_base_y += rnd;
        e.p->m_Size_plus = rec->Size_plus;
        e.p->m_D_size_plus = rec->D_size_plus;
        e.p->m_Col_start_r = rec->Col_start_r;
        e.p->m_Col_start_g = rec->Col_start_g;
        e.p->m_Col_start_b = rec->Col_start_b;
        e.p->m_Col_start_a = rec->Col_start_a;
        e.p->m_Col_r = (f32) rec->Col_start_r;
        e.p->m_Col_g = (f32) rec->Col_start_g;
        e.p->m_Col_b = (f32) rec->Col_start_b;
        e.p->m_Col_a = (f32) rec->Col_start_a;
        e.p->m_Col_d_r = rec->Col_d_r;
        e.p->m_Col_d_g = rec->Col_d_g;
        e.p->m_Col_d_b = rec->Col_d_b;
        e.p->m_Col_d_a = rec->Col_d_a;
        if (rec->Blend_type > 5) {
            pLog->err(0, 0, "ESP : BLEND_TYPE[%d] Invalid.", rec->Blend_type);
            PushEsp(e.p);
            *out = EspGetDmyPtr();
            return 0;
        }
        e.p->m_Blend_type = rec->Blend_type;
        e.p->xA4 = bl[rec->Blend_type][0];
        e.p->xA5 = bl[rec->Blend_type][1];
        e.p->xA6 = bl[rec->Blend_type][2];
        e.p->xA7 = bl[rec->Blend_type][3];
        if (rec->Blend_type == 4) {
            e.p->m_Flg |= 1;
        }
        e.p->m_Col_max_cnt = rec->Col_max_cnt;
        e.p->m_Col_start_cnt = rec->Col_start_cnt;
        e.p->m_Pos_start_cnt = rec->Pos_start_cnt;
        e.p->m_Size_start_cnt = rec->Size_start_cnt;
        e.p->m_Life_max = rec->Life_max;
        e.p->m_Life_time = rec->Life_time;
        e.p->m_Ptn_no = rec->Ptn_no;
        e.p->m_Anm_rate = rec->Anm_rate + 0x20;
        e.p->m_Anm_cnt = rec->Anm_cnt;
        e.p->m_Release_time = rec->Release_time;
        e.p->m_Shimmer_type = rec->Shimmer_type;
        e.p->m_Shimmer_pow = rec->Shimmer_pow;
        e.p->m_MaskTex_id = rec->MaskTex_id;
        e.p->m_Del_far = rec->Del_far * 10;
        e.p->m_Del_near = rec->Del_near * 10;
        if (e.p->m_Shimmer_type != 0) {
            e.p->m_Flg |= 4;
        }
        switch (e.p->m_Parts_no) {
        case 0xFF:
            e.p->parent = pEffParentWorld;
            e.p->ApplyMatrix(*mtx);
            break;
        case 0xF8:
        case 0xF9:
        case 0xFA:
        case 0xFB:
        case 0xFC:
        case 0xFD:
            e.p->parent = pEffParentWorld;
            e.p->m_Pos.x += (*mtx)[0][3];
            e.p->m_Pos.y += (*mtx)[1][3];
            e.p->m_Pos.z += (*mtx)[2][3];
            break;
        case 0xFE:
            e.p->parent = pEffParentWorld;
            if (rec->Release_time != 0) {
                pLog->warn(0, 0, "ESP:ReleaseTime not 0 but no parent.");
            }
            break;
        default:
            if (model == 0) {
                pLog->err(0, 0, "ESP : PARTS_NO[%d] but Not on parts.", e.p->m_Parts_no);
                PushEsp(e.p);
                *out = EspGetDmyPtr();
                return 0;
            }
            if (e.p->m_Parts_no < model->nParts) {
                if (e.p->m_Tool_flg & 0x20) {
                    parts = model->getPartsPtr(e.p->m_Parts_no);
                    PSMTXIdentity(m2);
                    low_RotMatrix(m2, &model->ang);
                    PSMTXMultVecSR(m2, &rec->Pos, &v);
                    m2[0][3] = parts->mat[0][3] + v.x;
                    m2[1][3] = parts->mat[1][3] + v.y;
                    m2[2][3] = parts->mat[2][3] + v.z;
                    e.p->parent = pEffParentWorld;
                    e.p->m_Pos.x = 0.0f;
                    e.p->m_Pos.y = 0.0f;
                    e.p->m_Pos.z = 0.0f;
                    e.p->ApplyMatrix(m2);
                    e.p->m_Pos.x += rec->R_pos.x * fRandSeed1_1(seed);
                    e.p->m_Pos.y += rec->R_pos.y * fRandSeed1_1(seed);
                    e.p->m_Pos.z += rec->R_pos.z * fRandSeed1_1(seed);
                } else {
                    e.p->m_pMod = model;
                    e.p->m_Guid_pMod = model->serial;
                    e.p->parent = model->getPartsPtr(e.p->m_Parts_no);
                    if (pos) {
                        PSVECAdd(&e.p->m_Pos, pos, &e.p->m_Pos);
                    }
                }
            } else {
                pLog->err(0, 0, "ESP : PARTS_NO[%d] is invalid(MAX:%d).", e.p->m_Parts_no, model->nParts);
                PushEsp(e.p);
                *out = EspGetDmyPtr();
                return 0;
            }
            break;
        }
        ret = e.p->SetFreeWork(rec, seed);
        if (pSct) {
            if (pSct->OverWrite_flg & 1) {
                e.p->m_Speed = pSct->Speed;
                e.p->m_Speed.x += rec->R_speed.x * fRandSeed1_1(seed);
                e.p->m_Speed.y += rec->R_speed.y * fRandSeed1_1(seed);
                e.p->m_Speed.z += rec->R_speed.z * fRandSeed1_1(seed);
            }
            if (pSct->OverWrite_flg & 2) {
                e.p->m_Size_base_x = pSct->Size_base_x;
                e.p->m_Size_base_y = pSct->Size_base_y;
            }
            if (pSct->OverWrite_flg & 4) {
                e.p->m_Col_start_r = pSct->Col_start_r;
                e.p->m_Col_start_g = pSct->Col_start_g;
                e.p->m_Col_start_b = pSct->Col_start_b;
                e.p->m_Col_start_a = pSct->Col_start_a;
                e.p->m_Col_r = (f32) pSct->Col_start_r;
                e.p->m_Col_g = (f32) pSct->Col_start_g;
                e.p->m_Col_b = (f32) pSct->Col_start_b;
                e.p->m_Col_a = (f32) pSct->Col_start_a;
            }
            if (pSct->Mul_flg & 1) {
                e.p->m_Speed.x *= pSct->Speed.x;
                e.p->m_Speed.y *= pSct->Speed.y;
                e.p->m_Speed.z *= pSct->Speed.z;
            }
            if (pSct->Mul_flg & 2) {
                e.p->m_Size_base_x *= pSct->Size_base_x;
                e.p->m_Size_base_y *= pSct->Size_base_y;
            }
            if (pSct->Mul_flg & 4) {
                f32 c;
                c = (f32) e.p->m_Col_start_r * (f32) (int) pSct->Col_start_r * (1.0f / 255.0f);
                if (c > 255.0f) {
                    c = 255.0f;
                }
                if (c < 0.0f) {
                    c = 0.0f;
                }
                e.p->m_Col_start_r = (u8) c;
                c = (f32) e.p->m_Col_start_g * (f32) (int) pSct->Col_start_g * (1.0f / 255.0f);
                if (c > 255.0f) {
                    c = 255.0f;
                }
                if (c < 0.0f) {
                    c = 0.0f;
                }
                e.p->m_Col_start_g = (u8) c;
                c = (f32) e.p->m_Col_start_b * (f32) (int) pSct->Col_start_b * (1.0f / 255.0f);
                if (c > 255.0f) {
                    c = 255.0f;
                }
                if (c < 0.0f) {
                    c = 0.0f;
                }
                e.p->m_Col_start_b = (u8) c;
                c = (f32) e.p->m_Col_start_a * (f32) (int) pSct->Col_start_a * (1.0f / 255.0f);
                if (c > 255.0f) {
                    c = 255.0f;
                }
                if (c < 0.0f) {
                    c = 0.0f;
                }
                e.p->m_Col_start_a = (u8) c;
                e.p->m_Col_r = (f32) e.p->m_Col_start_r;
                e.p->m_Col_g = (f32) e.p->m_Col_start_g;
                e.p->m_Col_b = (f32) e.p->m_Col_start_b;
                e.p->m_Col_a = (f32) e.p->m_Col_start_a;
            }
            if (pSct->Add_flg & 1) {
                e.p->m_Speed.x += pSct->Speed.x;
                e.p->m_Speed.y += pSct->Speed.y;
                e.p->m_Speed.z += pSct->Speed.z;
            }
            if (pSct->Add_flg & 2) {
                e.p->m_Size_base_x += pSct->Size_base_x;
                e.p->m_Size_base_y += pSct->Size_base_y;
            }
            if (pSct->Add_flg & 4) {
                f32 c;
                c = (f32) e.p->m_Col_start_r + (f32) (int) pSct->Col_start_r * (1.0f / 255.0f);
                if (c > 255.0f) {
                    c = 255.0f;
                }
                if (c < 0.0f) {
                    c = 0.0f;
                }
                e.p->m_Col_start_r = (u8) c;
                c = (f32) e.p->m_Col_start_g + (f32) (int) pSct->Col_start_g * (1.0f / 255.0f);
                if (c > 255.0f) {
                    c = 255.0f;
                }
                if (c < 0.0f) {
                    c = 0.0f;
                }
                e.p->m_Col_start_g = (u8) c;
                c = (f32) e.p->m_Col_start_b + (f32) (int) pSct->Col_start_b * (1.0f / 255.0f);
                if (c > 255.0f) {
                    c = 255.0f;
                }
                if (c < 0.0f) {
                    c = 0.0f;
                }
                e.p->m_Col_start_b = (u8) c;
                c = (f32) e.p->m_Col_start_a + (f32) (int) pSct->Col_start_a * (1.0f / 255.0f);
                if (c > 255.0f) {
                    c = 255.0f;
                }
                if (c < 0.0f) {
                    c = 0.0f;
                }
                e.p->m_Col_start_a = (u8) c;
                e.p->m_Col_r = (f32) e.p->m_Col_start_r;
                e.p->m_Col_g = (f32) e.p->m_Col_start_g;
                e.p->m_Col_b = (f32) e.p->m_Col_start_b;
                e.p->m_Col_a = (f32) e.p->m_Col_start_a;
            }
        }
    } else {
        ret = 0;
    }
    if (ret == 0) {
        *out = EspGetDmyPtr();
        if (e.p->m_Be_flg & 1) {
            PushEsp(e.p);
        }
        return 0;
    }
    *out = e.p;
    return ret;
}

// Bilinear point of the quad p0 p1 p2 p3 at (u, v).
void GetPosXY(Vec* p0, Vec* p1, Vec* p2, Vec* p3, f32 u, f32 v, Vec* out)
{
    static Vec v0;
    static Vec v1;
    static Vec v2;

    PSVECSubtract(p1, p0, &v0);
    PSVECSubtract(p2, p3, &v1);
    PSVECScale(&v0, &v0, u);
    PSVECScale(&v1, &v1, u);
    PSVECAdd(&v0, p0, &v0);
    PSVECAdd(&v1, p3, &v1);
    PSVECSubtract(&v1, &v0, &v2);
    PSVECScale(&v2, &v2, v);
    PSVECAdd(&v2, &v0, out);
}

// esp1b work at cEsp+0xF8: the quad is subdivided div x div times.
struct Esp1bSpWork {
    u32 div;   // 0x00
    Vec p1;    // 0x04 corner offsets from the unit quad (0,1,1) (1,1,1) (1,0,1) (0,0,1)
    Vec p2;    // 0x10
    Vec p3;    // 0x1C
};

// Draws esp1b's deformed sprite: the unit quad with the three corner offsets of Esp1bSpWork,
// subdivided div x div, as textured quads with an up normal.
void Esp1b_SpTrans(cEsp* esp)
{
    static Vec p0;
    static Vec p1;
    static Vec p2;
    static Vec p3;
    static Vec ret;
    Esp1bSpWork* w = (Esp1bSpWork*) &esp->pad_EC[0xC];
    u32 div;
    u32 i;
    u32 j;
    f32 step;
    f32 u;
    f32 u1;
    f32 v;
    f32 v1;
    f32 tu;
    f32 tu1;
    f32 tv;
    f32 tv1;

    GXClearVtxDesc();
    GXSetVtxDesc(9, 1);
    GXSetVtxDesc(0xA, 1);
    GXSetVtxDesc(0xD, 1);
    GXSetVtxAttrFmt(0, 9, 1, 4, 0);
    GXSetVtxAttrFmt(0, 0xA, 0, 1, 0);
    GXSetVtxAttrFmt(0, 0xD, 1, 4, 0);
    div = w->div;
    p0.x = 0.0f;
    p0.y = 1.0f;
    p0.z = 1.0f;
    p1.x = w->p1.x + 1.0f;
    p1.y = w->p1.y + 1.0f;
    p1.z = w->p1.z + 1.0f;
    p2.x = w->p2.x + 1.0f;
    p2.y = w->p2.y + 0.0f;
    p2.z = w->p2.z + 1.0f;
    p3.x = w->p3.x + 0.0f;
    p3.y = w->p3.y + 0.0f;
    p3.z = w->p3.z + 1.0f;
    GXBegin(0x80, 0, div * 4 * div);
    step = 1.0f / (f32) div;
    v = 0.0f;
    tv = 0.0f;
    for (i = 0; i < div; i++) {
        v1 = v + step;
        tv1 = tv + step;
        u = 0.0f;
        tu = 0.0f;
        for (j = 0; j < div; j++) {
            u1 = u + step;
            tu1 = tu + step;
            GetPosXY(&p0, &p1, &p2, &p3, u, v, &ret);
            GXPosition3f32(ret.x, ret.y, ret.z);
            GXNormal3s8(0, 1, 0);
            GXTexCoord2f32(tu, tv);
            GetPosXY(&p0, &p1, &p2, &p3, u1, v, &ret);
            GXPosition3f32(ret.x, ret.y, ret.z);
            GXNormal3s8(0, 1, 0);
            GXTexCoord2f32(tu1, tv);
            GetPosXY(&p0, &p1, &p2, &p3, u1, v1, &ret);
            GXPosition3f32(ret.x, ret.y, ret.z);
            GXNormal3s8(0, 1, 0);
            GXTexCoord2f32(tu1, tv1);
            GetPosXY(&p0, &p1, &p2, &p3, u, v1, &ret);
            GXPosition3f32(ret.x, ret.y, ret.z);
            GXNormal3s8(0, 1, 0);
            GXTexCoord2f32(tu, tv1);
            u = u1;
            tu = tu1;
        }
        v += step;
        tv += step;
    }
    GXClearVtxDesc();
    GXSetVtxDesc(9, 1);
    GXSetVtxDesc(0xA, 1);
    GXSetVtxDesc(0xD, 1);
    GXSetVtxAttrFmt(0, 9, 1, 1, 0);
    GXSetVtxAttrFmt(0, 0xA, 0, 1, 0);
    GXSetVtxAttrFmt(0, 0xD, 1, 1, 0);
}

// The split object's .sdata is padded to 8 bytes.
asm(".section .sdata; .balign 8");
