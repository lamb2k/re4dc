// game/filter06: dust / snow / rain particle filter (D:/Bio4/Prog/filter06.cpp). Up to 0x800 line
// particles drift with a speed around the camera and are wrapped back into a box around it; drawn
// as lines whose alpha fades with camera distance and eases to the requested colour. Rooms start it
// through effect controller 44 (Filter06SetParam).
#include "filter.h"
#include "atari.h"
#include "light.h"
#include "gx.h"
#include "main_sub.h"
#include "main_mem.h"
#include "db_log.h"
#include "trans_ot.h"
#include "global.h"
#include "camera.h"
#include "rnd.h"
#include "math_sub.h"

// Dust / snow particle filter: `num` line particles drift with a speed around the camera and
// are wrapped back into a box (LR half width x34, up half height x38, depth x3C) around it.
//
// cParticle06::move: the alphaBase load/product live in r11 in the original (the fast-cast address
// pseudo of `(u8) a` took r9 first, i.e. the loadaddr sat below the `lbz` in the scheduled RTL);
// ours hoists the loadaddr to the block top, so alphaBase is pinned (see the function). The re-read
// mask (`clrlwi rX, rStore, 24`) is reproduced with a volatile asm on `v`.

class cParticle06 {
public:
    Vec m_Pos;       // 0x00
    Vec m_Spd;       // 0x0C
    u8 pad_18[4];
    u8 m_Base_alpha;  // 0x1C
    u8 m_Alpha;      // 0x1D
    u8 pad_1E[2];

    void init(u32 no);
    void move();
};

struct Filter06Work {
    cParticle06* p;  // 0x00
    u32 num;         // 0x04
    Vec spd;         // 0x08
    u8 col[4];       // 0x14  target colour
    u8 cur[4];       // 0x18  current colour
    f32 colF[3];     // 0x1C
    f32 alphaF;      // 0x28
    f32 rate;        // 0x2C  alpha approach rate
    f32 spread;      // 0x30  initial spread around the camera (x 10)
    f32 rangeLR;     // 0x34  half width of the wrap box
    f32 rangeUp;     // 0x38  half height
    f32 rangeDepth;  // 0x3C  depth
    f32 scale;       // 0x40  line length (speed scale)
    u8 alphaMin;     // 0x44
    u8 pad_45[3];
};

extern "C" {
void Filter06Render();
}

Filter06Work flt06;
static Vec cam_vec_LR;

#if defined(RE4DC_RAIN_PS2) && RE4DC_RAIN_PS2
// RAIN_PS2 (effects30.mk; render only): the Filter06 rain the GameCube draws as GX lines (stubbed on the port)
// drawn natively in the PS2 release's amount. Source (SLUS-211.34 / GC r11b EFF, effect controller 0x44): the GC
// starts 1600 lines in colour (170, 170, 170, 60); the PS2 100 lines at alpha 80, same speed. The simulation and
// its Rnd() draws (Filter06SetParam) are unchanged; the first 100 particles are moved and drawn, at alpha x 80 / 60.
#include "native_ui.h"
extern "C" void GXGetViewportv(f32*);
extern "C" void re4dc_log(const char* fmt, ...);
static const u32 kRainPs2Lines = 100;
extern "C" unsigned re4dc_fx_level_rain(unsigned n) __attribute__((weak));
static int Filter06Ps2Rain()
{
    return pG->room_id == 0x11B && flt06.num == 1600 && flt06.col[0] == 170 && flt06.col[1] == 170 &&
           flt06.col[2] == 170 && flt06.col[3] == 60;
}
static int s_rain_pending;       // Filter06Render ran in this image: draw at the source-draw barrier
static Mtx s_rain_view;
static Mtx44 s_rain_proj;
static f32 s_rain_viewport[6];
static u32 s_rain_drawn, s_rain_frames;
#if defined(RE4DC_RAIN_DC) && RE4DC_RAIN_DC
// RAIN_DC (effects30.mk; render only, an approximation of the PS2 rain; lane rain17 2026-10-18). The PS2 draws the
// night-lake rain as ONE full-screen Esp08 sheet (r11b SST set 3 / r11a set 5, owner 0xD0: tex 0xC5, 700x540 of
// 512x448, rgb 180 a 100, 3x1 tiles scrolled 0.09 tile a frame), a whole translucent screen of fill a frame. Here: a
// pool of short vertical gouraud streaks in screen space (the sheet's look: thin, faint, fast, glued to the view),
// each with a depth so walls and characters in front hide it, sent as one TR header plus one strip per streak
// (re4dc_rain_dc_streaks). Private xorshift generator: no Rnd(), no game state; the pool advances by the game frames
// elapsed (pG->Frame_cnt, read only). Shown while the game's own Filter06 rain is queued (r11a / r11b, not indoors),
// its alpha eased in with the rain's (flt06.cur[3]).
#ifndef RE4DC_RAIN_DC_N
#define RE4DC_RAIN_DC_N 160
#endif
#if defined(RE4DC_LAKE_FIX_TOGGLE) && RE4DC_LAKE_FIX_TOGGLE
extern "C" unsigned char re4dc_lake_fix;   // native_ui.cpp (LAKE_FIX_TOGGLE): on = half the streaks drawn
#define RAIN_DC_DRAWN (re4dc_lake_fix ? RE4DC_RAIN_DC_N / 2 : RE4DC_RAIN_DC_N)
#else
#define RAIN_DC_DRAWN RE4DC_RAIN_DC_N
#endif
struct RainDcDrop {
    f32 x, y, d, len, w, a;
};
static RainDcDrop s_raindc[RE4DC_RAIN_DC_N];
static Re4dcRainStreak s_raindc_out[RE4DC_RAIN_DC_N];
static u32 s_raindc_seed = 0x2545F491U, s_raindc_frame, s_raindc_pending, s_raindc_ready, s_raindc_alpha;
static u32 s_raindc_frames, s_raindc_sent;
static f32 s_raindc_area;
#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
// Private default-off render experiment. This signature is not a loaded-record receipt.
static u32 s_raindc_queued_room, s_raindc_queued_frame; // exactly 8 extra bytes
static int Filter06R10cRain()
{
    return pG->room_id == 0x10C && flt06.p != 0 && flt06.num == 1100 &&
           flt06.col[0] == 170 && flt06.col[1] == 170 && flt06.col[2] == 170 && flt06.col[3] == 80 &&
           flt06.rate == 1.0f && flt06.scale == 1.0f && flt06.spd.x == 21.0f &&
           flt06.spd.y == -250.0f && flt06.spd.z == 0.0f && flt06.alphaMin == 0;
}
static void RainDcR10cCancel()
{
    if (s_raindc_queued_room == 0x10C) {
        s_raindc_pending = 0;
        s_raindc_queued_room = 0;
        s_raindc_queued_frame = 0;
    }
}
#endif
static f32 RainDcUnit()
{
    u32 x = s_raindc_seed;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    s_raindc_seed = x;
    return (f32) (x >> 8) * (1.0f / 16777216.0f);
}
static void RainDcSpawn(RainDcDrop* p, int top)
{
    const f32 u = RainDcUnit();
    p->d = 700.0f + 5300.0f * u;                    // view depth, mm
    p->len = 40000.0f / p->d;                       // 57 px near .. 12 px far (the PS2 sheet's streaks: 30-60 px)
    if (p->len < 12.0f) {
        p->len = 12.0f;
    }
    p->w = p->d < 1500.0f ? 1.5f : 1.0f;
    p->a = 110.0f - 60.0f * u;                      // near streaks brighter
    p->x = RainDcUnit() * 640.0f;
    p->y = top ? -p->len - RainDcUnit() * 60.0f : RainDcUnit() * (480.0f + p->len) - p->len;
}
static void RainDcFlush()
{
    if (!s_raindc_pending) {
        return;
    }
#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
    const int r10c = s_raindc_queued_room == 0x10C;
    if (r10c && (s_raindc_queued_frame != pG->Frame_cnt || !Filter06R10cRain() || flt06.cur[3] == 0 ||
                 (pG->Status_flg[1] & 0x02000000) || !Render_checkBlurPermission() ||
                 Screen.width != 512.0f || Screen.height != 448.0f || Filter09GetbUse())) {
        RainDcR10cCancel();
        return;
    }
    s_raindc_queued_room = 0;
    s_raindc_queued_frame = 0;
#endif
    s_raindc_pending = 0;
    u32 now = pG->Frame_cnt, dt = now - s_raindc_frame;
    s_raindc_frame = now;
    if (!s_raindc_ready) {
        for (u32 i = 0; i < RE4DC_RAIN_DC_N; ++i) {
            RainDcSpawn(&s_raindc[i], 0);
        }
        s_raindc_ready = 1;
        dt = 0;
    }
#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
    if (r10c && (pG->Stop_flg & 0x08000000)) {
        dt = 0; // source Stop freezes motion/alpha but still draws
    }
#endif
    if (dt > 4) {
        dt = 4;
    }
#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
    const f32 fade = r10c ? (f32) (s_raindc_alpha > 80 ? 80 : s_raindc_alpha) * (1.0f / 80.0f) :
                           (f32) (s_raindc_alpha > 60 ? 60 : s_raindc_alpha) * (1.0f / 60.0f);
#else
    const f32 fade = (f32) (s_raindc_alpha > 60 ? 60 : s_raindc_alpha) * (1.0f / 60.0f);
#endif
    u32 n = 0;
    f32 area = 0.0f;
    for (u32 i = 0; i < RE4DC_RAIN_DC_N; ++i) {
        RainDcDrop* p = &s_raindc[i];
        p->y += p->len * 1.1f * (f32) dt;          // about 50 px a frame near, as the PS2 sheet's scroll
        if (p->y > 480.0f) {
            RainDcSpawn(p, 1);
        }
#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
        // Experimental sheet-informed profile (r10c 210/120 versus night 180/100), not pixel equivalence.
        const u32 a = r10c ? (u32) (p->a * fade * 1.2f) : (u32) (p->a * fade);
#else
        const u32 a = (u32) (p->a * fade);
#endif
        if (a == 0 || i >= (u32) RAIN_DC_DRAWN) {
            continue;
        }
        Re4dcRainStreak* s = &s_raindc_out[n++];
        s->x = p->x;
        s->y0 = p->y;
        s->y1 = p->y + p->len;
        s->z = 1.0f / p->d;
        s->w = p->w;
#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
        const u32 rgb = r10c ? 0xD2D2D2U : 0xB4B4B4U;
        s->tail = ((a >> 2) << 24) | rgb;
        s->head = (a << 24) | rgb;
#else
        s->tail = ((a >> 2) << 24) | 0xB4B4B4U;     // PS2 sheet colour 180
        s->head = (a << 24) | 0xB4B4B4U;
#endif
        const f32 t = s->y0 > 0.0f ? s->y0 : 0.0f, b = s->y1 < 480.0f ? s->y1 : 480.0f;
        if (b > t) {
            area += (b - t) * s->w;                     // screen area submitted (before depth rejection)
        }
    }
    s_raindc_sent += re4dc_rain_dc_streaks(s_raindc_out, n);
    s_raindc_area += area;
    if (++s_raindc_frames % 120 == 1) {
        re4dc_log("rain dc: frame=%u room=%x streaks=%u sent=%u alpha=%u area_px=%u mean_screens_x1e4=%u\n",
                  (unsigned) pG->Frame_cnt, (unsigned) pG->room_id, (unsigned) n, (unsigned) s_raindc_sent,
                  (unsigned) s_raindc_alpha, (unsigned) area,
                  (unsigned) (s_raindc_area / (f32) s_raindc_frames * (10000.0f / 307200.0f)));
    }
}
#endif
// gx_stub.cpp GXSetDrawSync(0xADEB): after native_ui drained the deferred translucent queue, so each line goes
// straight to the open TR list (re4dc_effect_line: no frame storage). Depth tested, blended as GXSetBlendMode(1, 4, 5).
extern "C" void re4dc_rain_flush()
{
#if defined(RE4DC_RAIN_DC) && RE4DC_RAIN_DC
    RainDcFlush();
#endif
    if (!s_rain_pending) {
        return;
    }
    s_rain_pending = 0;
#if defined(RE4DC_RAIN_DC) && RE4DC_RAIN_DC
    return;   // RAIN_DC draws the rain: the PS2 lines (1 px, alpha 2-15 %, invisible on the PVR) are not drawn
#endif
    const f32* V = s_rain_viewport;
    if (V[2] <= 0.0f || V[3] <= 0.0f || !flt06.p) {
        return;
    }
    const f32 near_d = s_rain_proj[2][3] / (s_rain_proj[2][2] - 1.0f), far_d = s_rain_proj[2][3] / s_rain_proj[2][2];
    const f32 scale = flt06.scale;
    u32 drawn = 0;
    // FX_LEVEL (esp_sub.cpp): the effects-quality dial draws fewer of the moved lines (weak: absent without FX_LEVEL)
    const u32 lines = re4dc_fx_level_rain ? re4dc_fx_level_rain(kRainPs2Lines) : kRainPs2Lines;
    for (u32 i = 0; i < lines && i < flt06.num; ++i) {
        const cParticle06* p = &flt06.p[i];
        const u32 a1 = (u32) p->m_Alpha * 80U / 60U > 255U ? 255U : (u32) p->m_Alpha * 80U / 60U;
        if (a1 == 0) {
            continue;
        }
        Vec w[2] = {p->m_Pos, {p->m_Spd.x * scale + p->m_Pos.x, p->m_Spd.y * scale + p->m_Pos.y, p->m_Spd.z * scale + p->m_Pos.z}};
        Re4dcEffectLine l;
        int ok = 1;
        for (int e = 0; e < 2 && ok; ++e) {
            Vec c;
            PSMTXMultVec(s_rain_view, &w[e], &c);
            const f32 d = -c.z;
            if (d < near_d || d > far_d) {
                ok = 0;
                break;
            }
            const f32 px = (s_rain_proj[0][0] * c.x + s_rain_proj[0][2] * c.z) / d;
            const f32 py = (s_rain_proj[1][1] * c.y + s_rain_proj[1][2] * c.z) / d;
            l.x[e] = (V[2] * 0.5f * px + V[0] + V[2] * 0.5f) * 640.0f / V[2];
            l.y[e] = (-V[3] * 0.5f * py + V[1] + V[3] * 0.5f) * 480.0f / V[3];
            l.z[e] = 1.0f / d;
        }
        if (!ok) {
            continue;
        }
        const u32 r = flt06.cur[0], g = flt06.cur[1], b = flt06.cur[2];
        l.color[0] = ((a1 >> 2) << 24) | ((r >> 2) << 16) | ((g >> 2) << 8) | (b >> 2);
        l.color[1] = (a1 << 24) | (r << 16) | (g << 8) | b;
        l.src = 4;
        l.dst = 5;
        l.depth_test = 1;
        l.blend_mode = 1;
        drawn += re4dc_effect_line(&l) ? 1 : 0;
    }
    s_rain_drawn += drawn;
    if (++s_rain_frames % 120 == 1) {
        re4dc_log("rain ps2: frame=%u lines=%u drawn=%u total=%u alpha=%u\n", (unsigned) pG->Frame_cnt,
                  (unsigned) kRainPs2Lines, (unsigned) drawn, (unsigned) s_rain_drawn, (unsigned) flt06.cur[3]);
    }
}
#endif

// Places particle `no` randomly around the camera within `spread` * 10 units (plus a per-particle offset).
void cParticle06::init(u32 no)
{
    FSet(m_Pos.x, pG->Cam.param.pos.x);
    FSet(m_Pos.y, pG->Cam.param.pos.y);
    FSet(m_Pos.z, pG->Cam.param.pos.z);
    m_Pos.x += flt06.spread * 10.0f * fRand1_1() + (f32) no * 500.0f;
    m_Pos.y += flt06.spread * 10.0f * fRand1_1() + (f32) no * 500.0f;
    m_Pos.z += flt06.spread * 10.0f * fRand1_1() + (f32) no * 500.0f;
    m_Base_alpha = 0x80;
    m_Alpha = 0;
}

// Advances the particle by its speed and wraps it back into the camera box (rangeLR left/right,
// rangeUp, rangeDepth in front); alpha = base * 255/(depth/800), scaled by the current colour alpha,
// not below alphaMin.
void cParticle06::move()
{
    Vec d;
    Vec dir;
    Vec up;
    Vec tmp;
    f32 dot;
    f32 a;
    int n;
    int v;

    PSVECAdd(&m_Pos, &m_Spd, &m_Pos);
    PSVECSubtract(&m_Pos, &pG->Cam.param.pos, &d);
    dot = PSVECDotProduct(&d, &cam_vec_LR);
    if (dot >= 0.0f) {
        n = (int) ((dot + flt06.rangeLR) / (flt06.rangeLR + flt06.rangeLR));
    } else {
        n = (int) ((dot - flt06.rangeLR) / (flt06.rangeLR + flt06.rangeLR));
    }
    if (n != 0) {
        PSVECScale(&cam_vec_LR, &dir, -(flt06.rangeLR * (f32) n + flt06.rangeLR * (f32) n));
        PSVECAdd(&m_Pos, &dir, &m_Pos);
    }
#line 133 "D:/Bio4/Prog/filter06.cpp"
    VECNormalize(&pG->Cam.up, &up);
    PSVECSubtract(&m_Pos, &pG->Cam.param.pos, &d);
    dot = PSVECDotProduct(&d, &up);
    if (dot >= 0.0f) {
        n = (int) ((dot + flt06.rangeUp) / (flt06.rangeUp + flt06.rangeUp));
    } else {
        n = (int) ((dot - flt06.rangeUp) / (flt06.rangeUp + flt06.rangeUp));
    }
    if (n != 0) {
        PSVECScale(&up, &tmp, -(flt06.rangeUp * (f32) n + flt06.rangeUp * (f32) n));
        PSVECAdd(&m_Pos, &tmp, &m_Pos);
    }
    PSVECSubtract(&pG->Cam.param.at, &pG->Cam.param.pos, &dir);
#line 154
    VECNormalize(&dir, &dir);
    PSVECSubtract(&m_Pos, &pG->Cam.param.pos, &d);
    dot = PSVECDotProduct(&d, &dir);
    if (dot >= 0.0f) {
        n = (int) (dot / flt06.rangeDepth);
    } else {
        n = ~(int) (-dot / flt06.rangeDepth);
    }
    if (n != 0) {
        PSVECScale(&dir, &up, -(flt06.rangeDepth * (f32) n));
        PSVECAdd(&m_Pos, &up, &m_Pos);
        PSVECSubtract(&m_Pos, &pG->Cam.param.pos, &d);
        dot = PSVECDotProduct(&d, &dir);
    }
    a = 255.0f / (dot / 800.0f);
    if (a > 255.0f) {
        a = 255.0f;
    }
    {
        // COMPILER-DIFF: #17. The alphaBase load/product live in r11 in the original (the fast-cast
        // address pseudo of `(u8) a` took r9 first); ours gives them r9. Pinned, no code emitted.
        register int ab PPC_REG("r11");
        ab = m_Base_alpha;
        v = (ab * (u8) a) >> 8;
    }
    // the original re-reads `alpha` masked (`clrlwi rX, rStore, 24`) with the `&flt06` pair issued
    // after the store; ours knows the product fits in 8 bits and folds the mask -- the volatile asm
    // hides the range from combine and keeps the address pair below the product (emobj setYarare)
    asm volatile("" : "+r"(v));
    m_Alpha = v;
    v = ((u32) m_Alpha * flt06.cur[3]) >> 8;
    m_Alpha = v;
    if (m_Alpha < flt06.alphaMin) {
        m_Alpha = flt06.alphaMin;
    }
}

// Boot: same as the room init.
void Filter06Init()
{
    Filter06RoomInit();
}

// Room init: no particles, colour black, box 2500/2500/5000, spread 5000.
void Filter06RoomInit()
{
#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
    RainDcR10cCancel();
#endif
    memclr_asm(&flt06, sizeof(flt06));
    flt06.col[0] = 0;
    flt06.col[1] = 0;
    flt06.col[2] = 0;
    flt06.col[3] = 0;
    flt06.cur[0] = 0;
    flt06.cur[1] = 0;
    flt06.cur[2] = 0;
    flt06.cur[3] = 0;
    flt06.colF[0] = 0.0f;
    flt06.colF[1] = 0.0f;
    flt06.colF[2] = 0.0f;
    flt06.alphaF = 0.0f;
    flt06.spread = 5000.0f;
    flt06.rangeLR = 2500.0f;
    flt06.rangeUp = 2500.0f;
    flt06.rangeDepth = 5000.0f;
    flt06.p = 0;
}

// Per-frame (when particles exist): computes the camera right vector, moves every particle unless
// Stop_flg 0x08000000, eases the colour alpha towards the target by `rate`, and queues the render.
// Skipped while the player is in a special effect area (Status_flg[1] 0x02000000, e.g. indoors).
void Filter06Trans()
{
    static int use_filter6 = 1;
    u32 i;

    if (use_filter6 == 0) {
        return;
    }
    if (flt06.num == 0) {
        return;
    }
    if (pG->Status_flg[1] & 0x02000000) {
        return;
    }
    PSVECSubtract(&pG->Cam.param.at, &pG->Cam.param.pos, &cam_vec_LR);
    PSVECCrossProduct(&cam_vec_LR, &pG->Cam.up, &cam_vec_LR);
#line 246
    VECNormalize(&cam_vec_LR, &cam_vec_LR);
    if (!(pG->Stop_flg & 0x08000000)) {
#if defined(RE4DC_RAIN_PS2) && RE4DC_RAIN_PS2
        // RAIN_PS2: in a room with the PS2 recipe only the drawn subset moves (no other reader of the positions).
        const u32 moved = Filter06Ps2Rain() ? kRainPs2Lines : flt06.num;
        for (i = 0; i < moved; i++) {
            flt06.p[i].move();
        }
#else
        for (i = 0; i < flt06.num; i++) {
            flt06.p[i].move();
        }
#endif
        flt06.colF[0] = (f32) flt06.col[0];
        flt06.colF[1] = (f32) flt06.col[1];
        flt06.colF[2] = (f32) flt06.col[2];
        flt06.alphaF += ((f32) (int) flt06.col[3] - flt06.alphaF) * flt06.rate;
        flt06.cur[0] = (u8) flt06.colF[0];
        flt06.cur[1] = (u8) flt06.colF[1];
        flt06.cur[2] = (u8) flt06.colF[2];
        flt06.cur[3] = (u8) flt06.alphaF;
    }
    if (Render_checkBlurPermission()) {
        AddOtDirect(0x12, (void*) 0xCDCDCDCD, Filter06Render, 7, 0x400, 0, 0.0f);
    }
}

// Starts `level` particles (max 0x800; buffer allocated on first use) with speed spd +- spdRand per
// particle, target colour r,g,b,a approached at `rate`, starting alpha, line length scale and
// minimum alpha.
void Filter06SetParam(u32 level, int r, int g, int b, int a, f32 rate, Vec* spd, f32 alpha, Vec* spdRand, f32 scale,
                      int alphaMin)
{
    u32 i;

#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
    RainDcR10cCancel();
#endif
    flt06.num = level;
    if (level > 0x800) {
        flt06.num = 0x800;
    }
    if (flt06.p == 0) {
        cParticle06* p;

#line 280
        p = (cParticle06*) MEM_ALLOC(0x10000, 1, 13);
        flt06.p = p;
        if (p == 0) {
            flt06.num = 0;
            pLog->err(0, 0, "Filter06: not enough memory.");
            return;
        }
    }
    for (i = 0; i < flt06.num; i++) {
        flt06.p[i].init(i);
        flt06.p[i].m_Spd = *spd;
        flt06.p[i].m_Spd.x += spdRand->x * fRand1_1();
        flt06.p[i].m_Spd.y += spdRand->y * fRand1_1();
        flt06.p[i].m_Spd.z += spdRand->z * fRand1_1();
    }
    flt06.col[0] = r;
    flt06.col[1] = g;
    flt06.col[2] = b;
    flt06.col[3] = a;
    flt06.alphaF = alpha;
    flt06.rate = rate;
    flt06.spd = *spd;
    flt06.scale = scale;
    flt06.alphaMin = alphaMin;
}

// OT callback: draws every particle as a line from its position along its speed * scale in the
// current colour with the particle's alpha.
void Filter06Render()
{
    u32 i;
    cParticle06* p;
    f32 scale;

#if defined(RE4DC_RAIN_PS2) && RE4DC_RAIN_PS2
    if (Filter06Ps2Rain()) {
        PSMTXCopy(pG->Cam.v_mat, s_rain_view);
        for (int r = 0; r < 4; ++r) {
            for (int c = 0; c < 4; ++c) {
                s_rain_proj[r][c] = pG->Cam.ProjMat[r][c];
            }
        }
        GXGetViewportv(s_rain_viewport);
        s_rain_pending = 1;
    }
#if defined(RE4DC_RAIN_DC) && RE4DC_RAIN_DC
#if defined(RE4DC_RAIN_R10C_DC) && RE4DC_RAIN_R10C_DC
    // Stamp in the actual OT callback, not the preceding Trans registration.
    // main.cpp increments Frame_cnt only after Render returns; ADEB flush is synchronous inside Render.
    RainDcR10cCancel();
    if (Filter06R10cRain() && flt06.cur[3] != 0) {
        s_raindc_queued_room = 0x10C;
        s_raindc_queued_frame = pG->Frame_cnt;
        s_raindc_pending = 1;
        s_raindc_alpha = flt06.cur[3];
    }
#endif
    if ((pG->room_id == 0x11A || pG->room_id == 0x11B) && flt06.num != 0 && flt06.cur[3] != 0) {
        s_raindc_pending = 1;
        s_raindc_alpha = flt06.cur[3];
    }
#endif
#endif
    GXSetBlendMode(1, 4, 5, 0);
    CameraCurrentProjection();
    GXLoadPosMtxImm(pG->Cam.v_mat, 0);
    GXSetCurrentMtx(0);
    GXSetCullMode(0);
    GXSetZMode(1, 3, 0);
    GXSetNumChans(1);
    GXSetChanCtrl(4, 0, 0, 1, 0, 0, 2);
    GXSetNumTexGens(0);
    GXSetNumTevStages(1);
    GXSetTevOrder(0, 0xFF, 0xFF, 4);
    GXSetTevColorIn(0, 0xF, 0xC, 0xA, 0xF);
    GXSetTevColorOp(0, 0, 0, 0, 1, 0);
    GXSetTevAlphaIn(0, 7, 7, 7, 5);
    GXSetTevAlphaOp(0, 0, 0, 0, 1, 0);
    GXClearVtxDesc();
    GXSetVtxDesc(9, 1);
    GXSetVtxDesc(0xB, 1);
    GXSetVtxAttrFmt(0, 9, 1, 4, 0);
    GXSetVtxAttrFmt(0, 0xB, 1, 5, 0);
    GXEnableTexOffsets(0, 0, 1);
    p = flt06.p;
    scale = flt06.scale;
    for (i = 0; i < flt06.num; i++, p++) {
        GXBegin(0xA8, 0, 2);
        GXPosition3f32(p->m_Pos.x, p->m_Pos.y, p->m_Pos.z);
        GXColor4u8(flt06.cur[0] >> 2, flt06.cur[1] >> 2, flt06.cur[2] >> 2, p->m_Alpha >> 2);
        GXPosition3f32(p->m_Spd.x * scale + p->m_Pos.x, p->m_Spd.y * scale + p->m_Pos.y, p->m_Spd.z * scale + p->m_Pos.z);
        GXColor4u8(flt06.cur[0], flt06.cur[1], flt06.cur[2], p->m_Alpha);
    }
    GXEnableTexOffsets(0, 0, 0);
}
asm(".section .sdata; .balign 32");
