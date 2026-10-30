#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
#include "draw_fallback_audit.h"
#endif
// game/esp_sub: the shared part of the effect sprites (D:/Bio4/Prog/esp_sub.cpp): the cEsp base
// class members (CommonMove life/motion/colour update, AnmMove texture animation, ChannelSet
// colour + distance fade, ApplyMatrix), the common sprite draw EspCommonTrans with its heat
// shimmer and frame-buffer ("nega") variants, and EspSeqSet, which turns one EspGenWork record
// of an effect sequence into a live esp (or an effect model through EfmSeqSet). EspEstSetSelect
// spawns one record of an est table directly (laser sight, gatling, ...).
#if defined(RE4DC_ESP_CENSUS) && RE4DC_ESP_CENSUS
#include <stdio.h>
static unsigned re4dc_esp_ct[4];
#define ESPCT(i) (re4dc_esp_ct[i]++)
#else
#define ESPCT(i) ((void) 0)
#endif
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
#if defined(RE4DC_ESP1B_GRID03) && RE4DC_ESP1B_GRID03
#if !RE4DC_EFFECT_SPRITES || !RE4DC_EFFECT_LEAN || !RE4DC_FX_STRIP21 || !RE4DC_NATIVE_DRAW_OUTCOMES
#error ESP1B_GRID03 needs EFFECT_SPRITES, EFFECT_LEAN, FX_STRIP21 and NATIVE_DRAW_OUTCOMES
#endif
#endif
#if defined(RE4DC_ESP_SPRITE_FAST) && RE4DC_ESP_SPRITE_FAST && !(RE4DC_EFFECT_LEAN && RE4DC_EFFECT_SPRITES)
#error ESP_SPRITE_FAST needs EFFECT_LEAN=1 and EFFECT_SPRITES=1
#endif
#ifndef RE4DC_PS2_FX_POPULATION
#define RE4DC_PS2_FX_POPULATION 0
#endif
#if RE4DC_PS2_FX_POPULATION
#if !RE4DC_PS2_FX_STAGE1 || !RE4DC_EFFECT_PS2_HAZE
#error PS2_FX_POPULATION needs PS2_FX_STAGE1 and EFFECT_PS2_HAZE
#endif
#include "area.h"
#endif
#if RE4DC_PS2_FX_STAGE1
#include "ps2_fx_population.h"
#endif
#ifndef RE4DC_PS2_FX_ADDITIONS
#define RE4DC_PS2_FX_ADDITIONS 0
#endif
#if RE4DC_PS2_FX_ADDITIONS && (!RE4DC_PS2_FX_POPULATION || !RE4DC_ESP_SPRITE_FAST || !RE4DC_COARSE_FX_SPRITES)
#error PS2_FX_ADDITIONS needs PS2_FX_POPULATION, ESP_SPRITE_FAST and COARSE_FX_SPRITES
#endif
#if defined(RE4DC_R117_FX_QUALIFIED_FALLBACK) && RE4DC_R117_FX_QUALIFIED_FALLBACK && \
    defined(RE4DC_GAME) && !defined(__PPC__)
#if !RE4DC_FX_TRIM || !RE4DC_PS2_FX_ADDITIONS
#error R117_FX_QUALIFIED_FALLBACK needs FX_TRIM and PS2_FX_ADDITIONS
#endif
#define RE4DC_R117_FX_FALLBACK 1
#endif
#ifndef RE4DC_PS2_FX_COMMON_HAZE
#define RE4DC_PS2_FX_COMMON_HAZE 0
#endif
#if RE4DC_PS2_FX_COMMON_HAZE && (!RE4DC_PS2_FX_POPULATION || !RE4DC_ESP_SPRITE_FAST || !RE4DC_COARSE_FX_SPRITES)
#error PS2_FX_COMMON_HAZE needs PS2_FX_POPULATION, ESP_SPRITE_FAST and COARSE_FX_SPRITES
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
#if defined(RE4DC_MIST_CUT)
// MIST_CUT (hwfog.mk, lane mist16 2026-10-16; render only, test arms): the build default of a runtime mask.
// 1: no camera haze sprite (Esp15) and no mist sheet (Esp48) is drawn (the fog-table veil stays); 2: the world's
// translucent mist / backdrop parts (native_static.cpp kMistParts) are not drawn; 4: no other room-table ambient
// sprite (owner 0xd0: window glows / streaks / shafts, smoke, dust); 8: no other effect sprite of any owner (fire,
// torches, sparks, blood, muzzle flash, splashes); 16 (native_static.cpp): diagnostic, no translucent world part at all.
// Generators, Rnd() draws, the pool and every motion run as before.
unsigned re4dc_mist_cut = RE4DC_MIST_CUT;
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
#if defined(RE4DC_FX_STRIP21) && RE4DC_FX_STRIP21
#include "effect_strip_uv21.hpp"
#if defined(RE4DC_EFFECT_UV12) && RE4DC_EFFECT_UV12
#if !RE4DC_NATIVE_DRAW_OUTCOMES || !RE4DC_EFFECT_SPRITES
#error EFFECT_UV12 needs NATIVE_DRAW_OUTCOMES=1 and EFFECT_SPRITES=1
#endif
#include "effect_uv12.hpp"
#endif
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
#include "native_draw_result.hpp"
#endif
// No sprite eligibility, billboard bound or callback substitution for strips.
extern "C" int re4dc_esp_strip21_eligible(cEsp* esp){
    const s8 part=(s8)esp->m_Parts_no;
    return (esp->m_Id==1 || esp->m_Id==2) && !(part>=-8 && part<=-3) &&
        !(esp->m_Tool_flg&(0x10000|0x40|0x4000)) && !(esp->m_Flg&0x10) && esp->xA4==1;
}
extern "C" void re4dc_esp_strip21_color(GXColor color){s_effect_col=color;}
#if defined(RE4DC_FX_TRIM) && RE4DC_FX_TRIM
extern "C" int re4dc_fx_essential_strip_cut(const cEsp* esp);   // FX_TRIM Essential: trails / ribbons not drawn
#endif
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
#define RE4DC_STRIP21_RETURN(state,legacy) return {re4dc::NativeDrawOutcome::state}
extern "C" re4dc::NativeDrawResult re4dc_esp_strip21_draw_result(cEsp* esp,int no,Vec* corners,u8 repeat,int direction){
    if(!esp || !corners)RE4DC_STRIP21_RETURN(UnsupportedBeforePublication,0);
#else
#define RE4DC_STRIP21_RETURN(state,legacy) return legacy
extern "C" int re4dc_esp_strip21_draw(cEsp* esp,int no,Vec* corners,u8 repeat,int direction){
#endif
    if(!re4dc_esp_strip21_eligible(esp))RE4DC_STRIP21_RETURN(UnsupportedBeforePublication,0);
#if defined(RE4DC_FX_TRIM) && RE4DC_FX_TRIM
    if(re4dc_fx_essential_strip_cut(esp))RE4DC_STRIP21_RETURN(PolicySkip,1);
#endif
    EspTexWk* work=&g_pEspSys->Esp_tex_tbl[esp->m_Tex_id];
    if(work->Owner==0xD2 || !work->pTpl || esp->m_Ptn_no>=work->pTpl->numDescriptors)RE4DC_STRIP21_RETURN(UnsupportedBeforePublication,0);
#if defined(RE4DC_EFFECT_UV12) && RE4DC_EFFECT_UV12
    // Keep the existing full-identity class unchanged. For new admissions only,
    // copy the two rows actually loaded by EspTexSet; row 2 cannot affect ST11.
    bool legacy_identity=true;
    for(unsigned r=0;r<3;++r)for(unsigned c=0;c<4;++c)
        if(work->mtx[r][c]!=(r==c?1.0f:0.0f))legacy_identity=false;
    re4dc::effect_uv12::Matrix24 tex_matrix;
    if(!legacy_identity && !re4dc::effect_uv12::capture(work->mtx,tex_matrix))
        RE4DC_STRIP21_RETURN(UnsupportedBeforePublication,0);
#else
    // EspTexSet's matrix is source state. Only its proven identity registration
    // is qualified; custom texture matrices require their separate contract.
    for(unsigned r=0;r<3;++r)for(unsigned c=0;c<4;++c)
        if(work->mtx[r][c]!=(r==c?1.0f:0.0f))RE4DC_STRIP21_RETURN(UnsupportedBeforePublication,0);
#endif
    const TEXDescriptor* descriptor=TEXGet(work->pTpl,esp->m_Ptn_no);
    if(!descriptor || !descriptor->textureHeader)RE4DC_STRIP21_RETURN(UnsupportedBeforePublication,0);
    const TEXHeader* h=descriptor->textureHeader;
#if defined(RE4DC_EFFECT_UV12) && RE4DC_EFFECT_UV12
    // RGB565 has no sampled alpha for the source's alpha > 1 test. The old
    // identity route retains its historical material admission exactly.
    if(!legacy_identity && (h->format!=4 || descriptor->CLUTHeader || h->wrapS || h->wrapT ||
        s_effect_col.a<=1 || (esp->m_Tool_flg&(0x80|0x20000)) || esp->xA5!=4 || esp->xA6!=5))
        RE4DC_STRIP21_RETURN(UnsupportedBeforePublication,0);
#endif
    Re4dcEffectQuad q{};q.image={h->data,NULL,h->width,h->height,h->format,0xffffffffU,0};
    if(descriptor->CLUTHeader){q.image.palette=descriptor->CLUTHeader->data;
        q.image.palette_format=descriptor->CLUTHeader->format;q.image.palette_bytes=descriptor->CLUTHeader->numEntries*2;}
    re4dc::effect_strip21::UV uv[4];if(!re4dc::effect_strip21::source_uv(no,repeat,direction,esp->m_Tool_flg,uv))RE4DC_STRIP21_RETURN(UnsupportedBeforePublication,0);
#if defined(RE4DC_EFFECT_UV12) && RE4DC_EFFECT_UV12
    if(!legacy_identity)for(unsigned i=0;i<4;++i){
        float s,t;if(!re4dc::effect_uv12::transform(tex_matrix,uv[i].u,uv[i].v,s,t))
            RE4DC_STRIP21_RETURN(UnsupportedBeforePublication,0);
        uv[i].u=s;uv[i].v=t;
    }
#endif
    const unsigned order[4]={0,1,3,2};for(unsigned i=0;i<4;++i){q.positions[i][0]=corners[order[i]].x;
        q.positions[i][1]=corners[order[i]].y;q.positions[i][2]=corners[order[i]].z;q.u[i]=uv[i].u;q.v[i]=uv[i].v;}
    unsigned r=s_effect_col.r,g=s_effect_col.g,b=s_effect_col.b,a=s_effect_col.a;
    if(esp->m_Tool_flg&0x80){r=r*4>255?255:r*4;g=g*4>255?255:g*4;b=b*4>255?255:b*4;}
    if(esp->m_Tool_flg&0x20000)a=a*4>255?255:a*4;
    q.color=(a<<24)|(r<<16)|(g<<8)|b;q.src=esp->xA5&7;q.dst=esp->xA6&7;
    q.wrap_s=h->wrapS;q.wrap_t=h->wrapT;
    RE4DC_GXF_GET_PROJECTION(q.projection);RE4DC_GXF_GET_VIEWPORT(q.viewport);
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
    return re4dc_effect_quad_result(&q);
#else
    re4dc_effect_quad(&q);return 1; // admitted source family; queue refusal drops only this segment
#endif
}
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
extern "C" int re4dc_esp_strip21_draw(cEsp* esp,int no,Vec* corners,u8 repeat,int direction){
    // This is routing ownership, never proof that a refused GX sink renders.
    return !re4dc_esp_strip21_draw_result(esp,no,corners,repeat,direction).fallback_allowed();
}
#endif
#undef RE4DC_STRIP21_RETURN
#endif

#if defined(RE4DC_EFFECT_TORCH) && RE4DC_EFFECT_TORCH
// EFFECT_TORCH (effects30.mk): esp0e.cpp sets these around Esp0e_Trans's one-frame screen copy (the glow).
extern "C" {
int re4dc_esp0e_glow;
f32 re4dc_esp0e_depth;
u32 re4dc_esp0e_drawn;
void re4dc_log(const char* fmt, ...);
}
// The torch / lamp objects that own Esp0e glows (et0b 0x5f, et0c 0x60, et10 0x64, et14 0x68 (r11b's cEmTorch),
// et19 0x6d, et1c 0x70, et38 0x8c); et0a's 0x5e is eligible for every class already.
static int EspTorchGlowOwner(u32 owner)
{
    return owner == 0x5F || owner == 0x60 || owner == 0x64 || owner == 0x68 || owner == 0x6D || owner == 0x70 ||
           owner == 0x8C;
}
#endif
#if defined(RE4DC_EFFECT_OWNERS_ALL) && RE4DC_EFFECT_OWNERS_ALL
// EFFECT_OWNERS_ALL (effects30.mk): eligibility by effect class, not owner. Every EspCommonTrans sprite draws natively
// whatever its owner: Leon's own blood / splashes (PL00 0x03), crate / barrel / door / padlock break effects and torches
// (Et owners 0x55..0xbb, door locks 0xc9 / 0xcb), boat, animal, trap and Del Lago effects. The room tables (0x01, 0xd0)
// keep EFFECT_ROOM's rules; the mask / render-target / non-blend checks below still apply. FX_LEVEL budgets the
// admitted owners per frame (never thins, resizes or fades them).
static int EspOwnerAdmitted(u32 owner)
{
    return owner != 0x01 && owner != 0xD0 && !(owner == 0 || owner == 0x10 || (owner >= 0x34 && owner <= 0x4F) ||
                                               owner == 0x5E);
}
#endif
#if defined(RE4DC_LAKE_NIGHT_FX) && RE4DC_LAKE_NIGHT_FX
// LAKE_NIGHT_FX (effects30.mk, issue #30): the night lake's torch flames. r11a / r11b's cEmTorch (et14, owner 0x68)
// draws its flame / smoke sprites through EspCommonTrans; only their Esp0e glow was eligible (EFFECT_TORCH), so the
// flames themselves were never drawn. In those two rooms every owner-0x68 sprite is admitted (the mask / render-target /
// blend checks still apply). Draw time only: no effect state, spawn or Rnd() change.
extern "C" u32 re4dc_lake_fx_seen;
u32 re4dc_lake_fx_seen;
extern "C" void re4dc_log(const char* fmt, ...);
#define re4dc_lake_fx_log re4dc_log
static int EspLakeNightOwner(u32 owner)
{
    return owner == 0x68 && (G_ROOM_ID == 0x11A || G_ROOM_ID == 0x11B);
}
#endif
#if defined(RE4DC_PVR_RTT) && RE4DC_PVR_RTT
extern "C" int re4dc_rtt_capturing();
#endif
#if defined(RE4DC_TRAP_FX) && RE4DC_TRAP_FX
extern "C" void re4dc_log(const char* fmt, ...);
#endif
#if defined(RE4DC_ESP1B_GRID03) && RE4DC_ESP1B_GRID03
static int EspSpriteEligible(cEsp* esp,bool grid03=false)
#define RE4DC_SPLINE_BLOCK03 ((esp->m_Flg & 0x10) && !grid03)
#else
static int EspSpriteEligible(cEsp* esp)
#define RE4DC_SPLINE_BLOCK03 (esp->m_Flg & 0x10)
#endif
{
#if defined(RE4DC_ESP1B_GRID03) && RE4DC_ESP1B_GRID03
    if(grid03 && (esp->m_Id!=0x1b || !(esp->m_Flg&0x10) || EspTransTbl[esp->m_Id]!=EspCommonTrans))return 0;
#endif
#if defined(RE4DC_PVR_RTT) && RE4DC_PVR_RTT
    // PVR_RTT (pvr_rtt.mk): inside a render target's OT bracket its effects draw into the target, whatever the owner.
    // Outside the bracket they never reach the screen: the GC draws them only into the target's EFB area.
    if (esp->m_Tool_flg & 0x10000) {
        return re4dc_rtt_capturing() && !((esp->m_Tool_flg & 0x4000) || RE4DC_SPLINE_BLOCK03 || esp->xA4 != 1);
    }
#endif
    // Et0a hanging lamps use 0x5e for their source flame/smoke sprites, including
    // the impact fire. Keep the existing class, mask and blend restrictions.
    const u32 owner = esp->info.owner;
#if defined(RE4DC_LAKE_NIGHT_FX) && RE4DC_LAKE_NIGHT_FX
    if (EspLakeNightOwner(owner)) {
        const int ok = !((esp->m_Tool_flg & (0x4000 | 0x10000)) || RE4DC_SPLINE_BLOCK03 || esp->xA4 != 1);
        if ((re4dc_lake_fx_seen++ & 0x3FF) == 0) {
            re4dc_lake_fx_log("lake fx: frame=%u room=%x seen=%u id=%x ok=%d\n", (unsigned) pG->Frame_cnt,
                              (unsigned) G_ROOM_ID, (unsigned) re4dc_lake_fx_seen, (unsigned) esp->m_Id, ok);
        }
        return ok;
    }
#endif
#if defined(RE4DC_TRAP_FX) && RE4DC_TRAP_FX
    // TRAP_FX (effects30.mk; lane fix-water-traps23, GitHub #55 item 8): the tripwire bombs' effects (em2a's EFF, effect
    // owner 0x22: the blast em2aTrap2Bomb starts with EstSet 0x22 0 / 4 / 6, and the armed trap's own sprites) were not
    // on the owner whitelist, so the bombs on doors and trees went off with no explosion. Admitted here with the same
    // mask / render-target / blend checks. Draw time only: no effect state, spawn or Rnd() change.
    if (owner == 0x22) {
        static u32 s_trap_room = ~0U;
        const int ok = !((esp->m_Tool_flg & (0x4000 | 0x10000)) || RE4DC_SPLINE_BLOCK03 || esp->xA4 != 1);
        if (s_trap_room != G_ROOM_ID) {
            s_trap_room = G_ROOM_ID;
            re4dc_log("trap fx: room=%03x first owner-22 sprite id=%02x tex=%02x ok=%d\n", (unsigned) G_ROOM_ID,
                      (unsigned) esp->m_Id, (unsigned) esp->m_Tex_id, ok);
        }
        return ok;
    }
#endif
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
#if defined(RE4DC_EFFECT_TORCH) && RE4DC_EFFECT_TORCH
    if (!(re4dc_esp0e_glow && EspTorchGlowOwner(owner)))   // EFFECT_TORCH: an Esp0e glow copy of a torch owner
#endif
#if defined(RE4DC_EFFECT_OWNERS_ALL) && RE4DC_EFFECT_OWNERS_ALL
    if (!EspOwnerAdmitted(owner))
#endif
    if (!room && !(owner == 0 || owner == 0x10 || (owner >= 0x34 && owner <= 0x4F) || owner == 0x5E)) {
        return 0;
    }
#else
#if defined(RE4DC_EFFECT_TORCH) && RE4DC_EFFECT_TORCH
    if (!(re4dc_esp0e_glow && EspTorchGlowOwner(owner)))   // EFFECT_TORCH: an Esp0e glow copy of a torch owner
#endif
    if (!(owner == 0 || owner == 0x10 || (owner >= 0x34 && owner <= 0x4F) || owner == 0x5E)) {
        return 0; // muzzle flash (WEPxx), the shot's core effects, blood (EM10)
    }
#endif
    if ((esp->m_Tool_flg & (0x4000 | 0x10000)) || RE4DC_SPLINE_BLOCK03 || esp->xA4 != 1) {
        return 0; // mask stage, texture-render target, Esp1b spline, non-blend modes
    }
    return 1;
}
#undef RE4DC_SPLINE_BLOCK03
#if defined(RE4DC_ESP1B_GRID03) && RE4DC_ESP1B_GRID03
#include "effect_uv12.hpp"
static int Esp1bGridClass03(cEsp* esp){
    const s8 part=esp?(s8)esp->m_Parts_no:0;
    return esp && esp->m_Id==0x1b && (esp->m_Flg&0x10) && !(part>=-8 && part<=-3) &&
        !esp->m_Shimmer_type && !(esp->m_Tool_flg&(0x40|0x2000|0x4000|0x10000|0x100000|0x200000|0x808000)) &&
        esp->xA5==4 && esp->xA6==5 && EspSpriteEligible(esp,true);
}
static re4dc::NativeDrawResult Esp1bGridDraw03(cEsp*);
#endif
#if RE4DC_PS2FX_DRAW
#include "player.h"
#if RE4DC_EFFECT_PS2_HAZE
// EFFECT_PS2_HAZE: the room generator's camera haze (Esp15, owner 0xd0) drawn as the PS2 release draws it
// (SLUS-211.34 rNNN.dat EFF): a fixed subset of the live sprites (pool slot % every) inside the PS2's smaller
// camera box (depth [0, range), +-0.6 range across), the PS2 size (corners scaled about the centre by the
// steady-state size ratio: Size_base x (1 + Size_plus / (1 - D_size_plus)), PS2 / GC), the PS2 colour and
// alpha with the PS2 fades (near: Work8 30 / 5 -> 3.0 m to 0.5 m; far: the last 30 % of the box) and the
// GC's indoor fade counter. Expected sprites in view = live / every x (range_ps2 / range_gc)^3, the PS2 count.
#ifndef RE4DC_PS2_FX_ROOMS
#define RE4DC_PS2_FX_ROOMS 0
#endif
#ifndef RE4DC_PS2_FX_STAGE1
#define RE4DC_PS2_FX_STAGE1 0
#endif
struct Ps2fxHaze {
    u16 room;
    u8 every;
    u8 r, g, b, a;
    f32 range;
    f32 scale;
#if RE4DC_PS2_FX_ROOMS
    // PS2_FX_ROOMS: the GC generator's box (R_pos.z) this row takes (0: any; r106 has two haze sets) and the PS2 near
    // fade (Work8[0] / Work8[1] x 10 mm; 0: 3000 / 500, the r100 / r101 / r103 rows).
    f32 gc_range;
    f32 near_far, near_near;
#endif
#if RE4DC_PS2_FX_STAGE1
    // Source start RGB disambiguates r105's two generators with the same box. Zero means any RGB.
    // These are spawn fields, not the current colour/alpha or the indoor fade state.
    u8 gc_r, gc_g, gc_b;
    // 0: any; otherwise source Work8[3] + 1. r11d has equal range/RGB but distinct immutable indoor durations.
    u8 gc_room_frames_p1;
    u8 gc_owner; // 0: room-SST owner 0xd0; r200 EST 2 explicitly uses owner 1.
#endif
#if RE4DC_PS2_FX_POPULATION
    u8 gc_count, ps2_count; // audited one-shot emissions; zero preserves the earlier room path
#endif
};
#if RE4DC_WATER45_NATIVE
#define PS2FX_HAZE_ROOMS0 4
#else
#define PS2FX_HAZE_ROOMS0 3
#endif
#if RE4DC_PS2_FX_STAGE1
#define PS2FX_HAZE_ROOMS (PS2FX_HAZE_ROOMS0 + 3 + 19 + 3 * RE4DC_PS2_FX_POPULATION)
#elif RE4DC_PS2_FX_ROOMS
#define PS2FX_HAZE_ROOMS (PS2FX_HAZE_ROOMS0 + 3)
#else
#define PS2FX_HAZE_ROOMS PS2FX_HAZE_ROOMS0
#endif
#if RE4DC_PS2_FX_POPULATION
#define PS2FX_POP_COUNTS(gc, ps2) , gc, ps2
#else
#define PS2FX_POP_COUNTS(gc, ps2)
#endif
static const Ps2fxHaze kPs2Haze[PS2FX_HAZE_ROOMS] = {
    // r100: GC 60 x 1283.056 mm (+0.011), alpha 70, R 5090.2; PS2 11 x 2000 mm (+0.010), (235,235,210,34), R 5000
    {0x100, 5, 235, 235, 210, 34, 5000.0f, (2000.0f * 2.0f) / (1283.056f * 2.1f)},
    // r101: GC 39 x 1299.956 mm, alpha 25, R 6860.2; PS2 8 x 1900 mm, (255,250,240,35), R 5000
    {0x101, 2, 255, 250, 240, 35, 5000.0f, 1900.0f / 1299.956f},
    // r103: GC 41 x 1283.056 mm, alpha 30, R 7954.4; PS2 11 x 2100 mm, (255,255,225,35), R 5300
    {0x103, 1, 255, 255, 225, 35, 5300.0f, 2100.0f / 1283.056f},
#if RE4DC_WATER45_NATIVE
    // r10b (ROUTE_CH13 WATER45_NATIVE): GC 21 x 1731.403 mm, alpha 20, R 12093.6; PS2 10 x 2100 mm, (180,185,175,30), R 5000
    {0x10b, 1, 180, 185, 175, 30, 5000.0f, 2100.0f / 1731.403f},
#endif
#if RE4DC_PS2_FX_ROOMS
    // PS2_FX_ROOMS (worldfx cache r106 / r10a .gc / .ps2 EFF json; steady size Size_base x (1 + Size_plus / 0.01)):
    // r106 sst 0x01 (area 0): GC 30 x 2600 mm (+0.002), (255,255,245,30), R 6500.045, Work8 30/10/30/30;
    //                         PS2 10 x 2000 mm (+0.010), (255,255,245,40), R 5000, Work8 30/5/30/30
    {0x106, 1, 255, 255, 245, 40, 5000.0f, (2000.0f * 2.0f) / (2600.0f * 1.2f), 6500.045f, 3000.0f, 500.0f},
    // r106 sst 0x03 (area 1): GC 30 x 2600 mm (+0.002), (255,253,245,25), R 6484.946, Work8 30/10/30/25;
    //                         PS2 10 x 2000 mm (+0.010), (255,255,245,35), R 4000, Work8 20/10/30/25
    {0x106, 1, 255, 255, 245, 35, 4000.0f, (2000.0f * 2.0f) / (2600.0f * 1.2f), 6484.946f, 2000.0f, 1000.0f},
    // r10a sst 0x04: GC 41 x 1334.167 mm (+0.020), (250,250,235,20), R 6283.557, Work8 40/10/20/15;
    //                PS2 10 x 1700 mm (+0.010), (255,255,238,20), R 4000, Work8 20/10/30/30
    {0x10a, 1, 255, 255, 238, 20, 4000.0f, (1700.0f * 2.0f) / (1334.167f * 3.0f), 0.0f, 2000.0f, 1000.0f},
#endif
#if RE4DC_PS2_FX_STAGE1
    // First decoded stage-1 group, from the GC/PS2 EFF records audited by tools/audit_ps2_fx_recipes.py.
    // The pool-slot stride approximates PS2 counts after source-box clipping; generators and motion stay GC.
    // r102: GC sst 02/0 59 x 1099.956 (+.01), R4000.199 -> PS2 sst 00/1 10 x 1700 (+.01), R5000.
    {0x102, 6, 255, 235, 215, 40, 5000.0f, 1700.0f / 1099.956f, 4000.199f, 3000.0f, 500.0f, 255, 235, 215, 0, 0 PS2FX_POP_COUNTS(59, 10)},
    // r104: GC sst 00/0 21 x 1887.222 (+.03), R5090.199 -> PS2 sst 00/1 11 x 2500 (+.01), R5300.
    {0x104, 2, 225, 225, 200, 46, 5300.0f, (2500.0f * 2.0f) / (1887.222f * 4.0f), 5090.199f, 3500.0f, 500.0f, 225, 225, 200, 0, 0 PS2FX_POP_COUNTS(21, 11)},
    // r105: sst 04/0 (area 0), 05/0 (area 1); each GC 51 x 1283.056 -> PS2 10 x 2100; all +.01.
    {0x105, 5, 225, 225, 205, 36, 5000.0f, 2100.0f / 1283.056f, 5090.199f, 3000.0f, 500.0f, 225, 225, 205, 0, 0 PS2FX_POP_COUNTS(51, 10)},
    {0x105, 5, 255, 255, 235, 28, 5000.0f, 2100.0f / 1283.056f, 5090.199f, 3000.0f, 500.0f, 255, 255, 235, 0, 0 PS2FX_POP_COUNTS(51, 10)},
    // r107: GC sst 00/0 (global) -> PS2 09/2; GC sst 08/0 (area 3) -> PS2 08/0.
    {0x107, 4, 235, 235, 210, 30, 5000.0f, (2000.0f * 2.0f) / (1283.056f * 4.0f), 5090.199f, 3000.0f, 500.0f, 225, 225, 190, 0, 0 PS2FX_POP_COUNTS(40, 11)},
    {0x107, 5, 255, 255, 225, 30, 5000.0f, 2100.0f / 1374.622f, 5853.189f, 3000.0f, 500.0f, 255, 255, 225, 0, 0 PS2FX_POP_COUNTS(71, 9)},
    // Remaining qualified room-SST haze. r10f texture replacement and structural additions are separate.
    // r109: GC sst 01/0 (28 emissions) -> PS2 sst 01/0 (10); source steady-size ratio.
    {0x109, 1, 247, 249, 255, 30, 5000.000f, 0.724137864f, 6484.946f, 3000.0f, 500.0f, 245, 247, 255, 0, 0 PS2FX_POP_COUNTS(28, 10)},
    // r10c: GC sst 01/0 (46 emissions) -> PS2 sst 01/1 (7); source steady-size ratio.
    {0x10c, 6, 165, 175, 175, 68, 5000.000f, 1.714656711f, 5090.199f, 3000.0f, 500.0f, 165, 175, 175, 0, 0 PS2FX_POP_COUNTS(46, 7)},
    // r10e: GC sst 06/0 (66 emissions) -> PS2 sst 06/1 (12); source steady-size ratio.
    {0x10e, 3, 185, 195, 195, 75, 4000.000f, 1.558778828f, 5090.199f, 3000.0f, 500.0f, 165, 175, 175, 0, 0 PS2FX_POP_COUNTS(66, 12)},
    // r111: GC sst 01/0 (53 emissions) -> PS2 sst 01/1 (10); source steady-size ratio.
    {0x111, 2, 255, 255, 255, 57, 4800.000f, 0.974392037f, 6860.199f, 3000.0f, 500.0f, 215, 215, 215, 0, 0 PS2FX_POP_COUNTS(53, 10)},
    // r113: GC sst 00/0 (51 emissions) -> PS2 sst 00/1 (10); source steady-size ratio.
    {0x113, 1, 235, 255, 255, 33, 5000.000f, 1.480839886f, 7954.390f, 3000.0f, 500.0f, 235, 255, 255, 0, 0 PS2FX_POP_COUNTS(51, 10)},
    // r119: GC sst 01/0 (20 emissions) -> PS2 sst 00/1 (10); source steady-size ratio.
    {0x119, 1, 255, 255, 255, 37, 5000.000f, 0.777777705f, 6484.946f, 3000.0f, 500.0f, 255, 255, 255, 0, 0 PS2FX_POP_COUNTS(20, 10)},
    // r11a: GC sst 04/0 (66 emissions) -> PS2 sst 04/1 (10); source steady-size ratio.
    {0x11a, 6, 175, 185, 185, 65, 5000.000f, 1.558778828f, 5090.199f, 3000.0f, 500.0f, 165, 175, 175, 0, 0 PS2FX_POP_COUNTS(66, 10)},
    // r11c: GC sst 01/0 (21 emissions) -> PS2 sst 00/1 (10); source steady-size ratio.
    {0x11c, 1, 250, 250, 255, 28, 5000.000f, 1.282029573f, 6484.946f, 3000.0f, 500.0f, 250, 250, 255, 0, 0 PS2FX_POP_COUNTS(21, 10)},
    // r11d: GC sst 01/0 (26 emissions) -> PS2 sst 00/1 (10); source steady-size ratio.
    {0x11d, 1, 255, 255, 245, 35, 5000.000f, 0.714285648f, 6484.946f, 3000.0f, 500.0f, 255, 255, 245, 31, 0 PS2FX_POP_COUNTS(26, 10)},
    // r11d: GC sst 09/0 (26 emissions) -> PS2 sst 09/0 (10); source steady-size ratio.
    {0x11d, 1, 255, 255, 245, 45, 5000.000f, 0.749999930f, 6484.946f, 3000.0f, 500.0f, 255, 255, 245, 1, 0 PS2FX_POP_COUNTS(26, 10)},
    // r11e: GC sst 00/0 (66 emissions) -> PS2 sst 00/1 (10); source steady-size ratio.
    {0x11e, 6, 175, 175, 155, 50, 5000.000f, 1.558778828f, 5090.199f, 3000.0f, 500.0f, 175, 175, 155, 0, 0 PS2FX_POP_COUNTS(66, 10)},
    // r11f: GC sst 01/0 (59 emissions) -> PS2 sst 00/1 (11); source steady-size ratio.
    {0x11f, 1, 255, 255, 255, 40, 4000.000f, 1.461588282f, 6860.199f, 3000.0f, 500.0f, 255, 255, 245, 0, 0 PS2FX_POP_COUNTS(59, 11)},
    // r200: room EST 02/0, GC 53 -> PS2 12; R200Init spawns owner 1 with no source overrides.
    {0x200, 3, 255, 255, 255, 60, 6000.000f, 1.230810994f, 6860.199f, 3500.0f, 500.0f, 205, 215, 215, 0, 1 PS2FX_POP_COUNTS(53, 12)},
#if RE4DC_PS2_FX_POPULATION
    // r11b needs the population remap: clipping the GC box alone admits only about 2.47 of the 10 targets.
    {0x11b, 1, 178, 185, 185, 30, 5000.0f, (2000.0f * 2.0f) / (1731.402588f * 3.0f),
     12093.557f, 3000.0f, 500.0f, 178, 185, 185, 0, 0 PS2FX_POP_COUNTS(35, 10)},
    // r112 moves the global GC source into PS2 EAR area 5 (read-only draw gate below).
    {0x112, 6, 255, 255, 255, 34, 5000.0f, 1900.0f / 1099.955566f,
     4000.199f, 3000.0f, 500.0f, 255, 255, 255, 0, 0 PS2FX_POP_COUNTS(59, 10)},
    // r10f replaces source tex1e/RGBx4 with the already-resident centered tex1f in the selected draw.
    {0x10f, 5, 165, 165, 165, 40, 4000.0f, 1900.0f / 1300.0f,
     3800.0f, 3000.0f, 500.0f, 155, 155, 155, 0, 0 PS2FX_POP_COUNTS(48, 10)},
#endif
#endif
};
#undef PS2FX_POP_COUNTS
#if RE4DC_PS2_FX_ROOMS
// esp15.cpp's work (cEsp15::m_Free), read for the generator's box (PS2_FX_ROOMS) and the indoor fade counter.
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
#if defined(RE4DC_HW_FOG_HAZE) && RE4DC_HW_FOG_HAZE
extern "C" int re4dc_hwfog_haze(unsigned room, float depth, float indoor);   // game/hwfog.cpp (hwfog.mk)
#endif
static const Ps2fxHaze* Ps2fxHazeFor(cEsp* esp)
{
#if RE4DC_PS2_FX_STAGE1
    if (!(re4dc_ps2fx & PS2FX_HAZE) || esp->m_Id != 0x15 ||
        (esp->info.owner != 0xD0 && esp->info.owner != 1)) {
#else
    if (!(re4dc_ps2fx & PS2FX_HAZE) || esp->m_Id != 0x15 || esp->info.owner != 0xD0) {
#endif
        return NULL;
    }
    const u16 room = G_ROOM_ID;
    for (int i = 0; i < PS2FX_HAZE_ROOMS; ++i) {
        if (kPs2Haze[i].room == room) {
#if RE4DC_PS2_FX_ROOMS
            if (kPs2Haze[i].gc_range != 0.0f) {
                const f32 dr = static_cast<cPs2fxEsp15*>(esp)->m_Free.Range - kPs2Haze[i].gc_range;
                if (dr > 1.0f || dr < -1.0f) {
                    continue;
                }
            }
#endif
#if RE4DC_PS2_FX_STAGE1
            const Ps2fxHaze* h = &kPs2Haze[i];
            if (esp->info.owner != (h->gc_owner ? h->gc_owner : 0xD0)) {
                continue;
            }
            if ((h->gc_r || h->gc_g || h->gc_b) &&
                (esp->m_Col_start_r != h->gc_r || esp->m_Col_start_g != h->gc_g || esp->m_Col_start_b != h->gc_b)) {
                continue;
            }
            if (h->gc_room_frames_p1 &&
                static_cast<cPs2fxEsp15*>(esp)->m_Free.Room_del_frame != h->gc_room_frames_p1 - 1) {
                continue;
            }
#endif
            return &kPs2Haze[i];
        }
    }
    return NULL;
}
#if RE4DC_PS2_FX_POPULATION
// PS2 r112 EAR entry 6 (no 7, area 5), absent from the GC EAR. Use the existing read-only area test.
static AreaXZ4 kPs2Area112 = {
    -22269.951171875f, 20741.060546875f, 3500.0f,
    {{-20988.728515625f, -14207.736328125f}, {5959.01904296875f, -8866.1044921875f},
     {3484.49560546875f, 59716.26953125f}, {-21288.494140625f, 51728.37109375f}}
};
static int s_fx_area112;
static int Ps2fxArea112()
{
    if (g_pEspSys && (g_pEspSys->Add_area_bit & (1U << 5))) return 1;
    Vec pos;
    if ((pG->Status_flg[2] & 0x10000) == 0) {
        if (!pPL) return 0;
        pos = pPL->pos;
        pos.y += 100.0f;
    } else {
        pos = pG->Cam.param.pos;
    }
    return areaHitCheck_xz4(&kPs2Area112, &pos);
}
static ps2fx::Population s_fx_population;
static u32 s_fx_population_frame, s_fx_population_slots;
static u16 s_fx_population_room;
static const u8* s_fx_population_pool;
static unsigned s_fx_population_mask;
static int s_fx_population_valid;
struct Ps2fxPopulationReader {
    bool operator()(unsigned slot, ps2fx::PopulationKey& key) const
    {
        cEsp* esp = (cEsp*)(g_pEspSys->pEspBuf + slot * 0x150);
        if (!(esp->m_Be_flg & 1) || esp->m_Id != 0x15) return false;
        const Ps2fxHaze* h = Ps2fxHazeFor(esp);
        if (!h || !h->gc_count) return false;
        key.recipe = (unsigned short)(h - kPs2Haze);
        key.owner = esp->info.owner;
        key.kind = esp->info.Core_kind;
        key.flags = esp->info.Core_flg;
        key.call = esp->info.Call_no;
        key.core = esp->info.Core_pEm;
        key.source_count = h->gc_count;
        key.target_count = h->ps2_count;
        // An unexpected instance of the signature is explicit fallback, never accepted as the source emitter.
        if (!ps2fx::population_source_matches(h->room, esp->m_Life_max, esp->m_Parts_no,
                esp->m_Tool_flg, esp->m_Tex_id, esp->m_Type, esp->parent == pEffParentWorld)) key.source_count = 0;
        return true;
    }
};
static void Ps2fxPopulationBuild()
{
    s_fx_population_valid = 1;
    if (G_ROOM_ID != 0x112 || s_fx_population_room != G_ROOM_ID) s_fx_area112 = 0;
    if (G_ROOM_ID == 0x112 && !(pG->Stop_flg & 0x20)) s_fx_area112 = Ps2fxArea112();
    s_fx_population_frame = pG->Frame_cnt;
    s_fx_population_room = G_ROOM_ID;
    s_fx_population_pool = g_pEspSys ? g_pEspSys->pEspBuf : NULL;
    s_fx_population_slots = g_pEspSys ? g_pEspSys->nEsp : 0;
    s_fx_population_mask = re4dc_ps2fx;
    int enabled = 0;
    if (re4dc_ps2fx & PS2FX_HAZE) {
        for (unsigned i = 0; i < PS2FX_HAZE_ROOMS; ++i) {
            if (kPs2Haze[i].room == G_ROOM_ID && kPs2Haze[i].gc_count) { enabled = 1; break; }
        }
    }
    if (!enabled || !s_fx_population_pool) {
        s_fx_population.clear(0);
        return;
    }
    s_fx_population.build(s_fx_population_slots, Ps2fxPopulationReader());
    static ps2fx::Population::Stats last;
    static u16 last_room;
    static int reported, last_area;
    const int area_active = G_ROOM_ID == 0x112 ? s_fx_area112 : 1;
    const ps2fx::Population::Stats& st = s_fx_population.stats;
    if (!reported || last_room != G_ROOM_ID || last_area != area_active || !(last == st)) {
        re4dc_log("PS2FXPOP f=%u r=%03x slots=%u candidates=%u groups=%u selected=%u fallback=%u issues=%u area=%d\n",
            (unsigned)pG->Frame_cnt, (unsigned)G_ROOM_ID, st.slots, st.candidates, st.groups,
            st.selected, st.fallback, st.issues, area_active);
        last = st;
        last_area = area_active;
        last_room = G_ROOM_ID;
        reported = 1;
    }
}
static int Ps2fxPopulationState(cEsp* esp, const Ps2fxHaze* h)
{
    if (!h || !h->gc_count) return -1;
    if (!s_fx_population_valid || s_fx_population_frame != pG->Frame_cnt ||
        s_fx_population_room != G_ROOM_ID || !g_pEspSys ||
        s_fx_population_pool != g_pEspSys->pEspBuf || s_fx_population_slots != g_pEspSys->nEsp ||
        s_fx_population_mask != re4dc_ps2fx) Ps2fxPopulationBuild();
    if (!s_fx_population_pool) return -1;
    const u32 offset = (u32)((u8*)esp - s_fx_population_pool);
    if (offset % 0x150 || offset / 0x150 >= s_fx_population_slots) return -1;
    return s_fx_population.state(offset / 0x150);
}
static int Ps2fxPopulationSelected(cEsp* esp)
{
    return Ps2fxPopulationState(esp, Ps2fxHazeFor(esp)) == 1;
}
#endif
#if defined(RE4DC_EFFECT_HAZE_LEAN) && RE4DC_EFFECT_HAZE_LEAN
// EFFECT_HAZE_LEAN bit 2 (STUDY2 M3): about 30 % of the PS2 subset (pool slot % every2 instead of % every) at alpha
// x1.5; the fog table carries the rest of the veil (native_static.cpp re4dc_fog_frame, from re4dc_haze_key()).
static u8 Ps2fxEvery2(u16 room)
{
    return room == 0x100 ? 16 : room == 0x101 ? 7 : room == 0x103 ? 3 : 0;
}
// The haze fade (the GC indoor fade counter, 1 outdoors) in 8 steps and the room (1 r100, 2 r101, 3 r103), as the
// draw last saw it: (step << 4) | room, 0 without a haze room this frame. Read once per frame by the fog code.
static u32 s_haze_key, s_haze_key_frame;
#if defined(RE4DC_EFFECT_HAZE_LEAN_TOGGLE)
// EFFECT_HAZE_LEAN_TOGGLE (test builds): the mask at run time; pad.cpp X + D-pad up + START steps it, native_static.cpp
// shows the name for 3 s (re4dc_haze_lean_osd_text). Order W (none), M1, M2, M3, all.
extern "C" unsigned re4dc_vi_retrace_count(void);
extern "C" void re4dc_log(const char* fmt, ...);
static u32 s_haze_lean_step, s_haze_lean_osd_until;
static const u8 kHazeLeanMask[5] = {0, 1, 4, 2, 7};
static const char* const kHazeLeanText[5] = {"Haze W: base (PS2 haze)", "Haze M1: no GC mist sheets",
                                             "Haze M2: octagon sprites", "Haze M3: fog + 30% sprites", "Haze all: M1+M2+M3"};
#define RE4DC_HZ(bit) (kHazeLeanMask[s_haze_lean_step] & (bit))
extern "C" void re4dc_haze_lean_cycle(void)
{
    s_haze_lean_step = (s_haze_lean_step + 1) % 5;
    s_haze_lean_osd_until = re4dc_vi_retrace_count() + 180U;
    re4dc_log("haze lean: mode %s (mask %u)\n", kHazeLeanText[s_haze_lean_step], (unsigned) kHazeLeanMask[s_haze_lean_step]);
}
extern "C" const char* re4dc_haze_lean_osd_text(void)
{
    return (int) (s_haze_lean_osd_until - re4dc_vi_retrace_count()) > 0 ? kHazeLeanText[s_haze_lean_step] : 0;
}
#else
#define RE4DC_HZ(bit) 1
#endif
extern "C" unsigned re4dc_haze_key(void)
{
    return (pG->Frame_cnt - s_haze_key_frame) <= 2 ? s_haze_key : 0;
}
#endif
#if !RE4DC_PS2_FX_ROOMS
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
#if RE4DC_PS2_FX_ROOMS
// PS2_FX_ROOMS: the other rooms' Esp0a type 0 window streaks the PS2 EFF removed (their static id-0 copies keep
// the record's tex, additive blend and Del_far / Del_near x 10; no other id-0 record of the room has those dels).
struct Ps2fxStreakCut {
    u16 room;
    u8 tex;
    u16 del_far, del_near;
};
#if RE4DC_PS2_FX_STAGE1
#define PS2FX_STREAK_CUTS 7
#else
#define PS2FX_STREAK_CUTS 2
#endif
static const Ps2fxStreakCut kPs2StreakCut[PS2FX_STREAK_CUTS] = {
    {0x106, 0x32, 120, 70},   // r106 sst 0x08 records 2/3, sst 0x09 records 2/3 (windows, alpha 6)
    {0x106, 0x32, 100, 40},   // r106 sst 0x0b record 5 (alpha 4)
#if RE4DC_PS2_FX_STAGE1
    {0x102, 0x08, 250, 100}, // GC sst 01/14 removed; PS2 retains the other two streak signatures.
    {0x104, 0x1e, 800, 600}, // GC sst 00/6 removed; no PS2 Esp0a record.
    {0x107, 0x1e, 800, 600}, // GC sst 03/2 removed; no PS2 Esp0a record.
    {0x10f, 0x52, 100, 50},  // Fifteen GC sst 01 records removed; no PS2 matching streak/direct sprite.
    {0x112, 0x08, 100, 50},  // GC sst 01/15 removed; this does not match the separate EST streak.
#endif
};
#endif
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
#if RE4DC_PS2_FX_STAGE1
// Room-SST Esp48 textures absent from all PS2 Esp48 records in each listed room.
struct Ps2fxSheetCut {
    u16 room;
    u8 tex;
    u8 owner; // 0 means the established room-SST owner 0xd0.
};
static const Ps2fxSheetCut kPs2SheetCut[] = {
    {0x105, 0xd0}, // 2 GC source records
    {0x107, 0xd0}, // 2 GC source records
    {0x108, 0xd0}, // 4 GC source records
    {0x108, 0xcb}, // 2 GC source records
    {0x109, 0x1f}, // 1 GC source records
    {0x109, 0xf6}, // 16 GC source records
    {0x109, 0xcb}, // 11 GC source records
    {0x111, 0xf6}, // 34 GC source records
    {0x111, 0xcb}, // 14 GC source records
    {0x111, 0x33}, // 5 GC source records
    {0x113, 0x33}, // 5 GC source records
    {0x113, 0xf6}, // 44 GC source records
    {0x113, 0xcb}, // 4 GC source records
    {0x118, 0xd0}, // 4 GC source records
    {0x118, 0xcb}, // 1 GC source records
    {0x119, 0x29}, // 9 GC source records
    {0x119, 0x2c}, // 2 GC source records
    {0x119, 0x1f}, // 1 GC source records
    {0x119, 0xf6}, // 15 GC source records
    {0x119, 0x34}, // 4 GC source records
    {0x119, 0xcb}, // 15 GC source records
    {0x11c, 0xcb}, // 3 GC source records
    {0x11c, 0x34}, // 3 GC source records
    {0x11c, 0x33}, // 1 GC source records
    {0x200, 0xf6}, // 14 GC source records
    {0x11c, 0xcb, 1}, // 12 room EST 0a records
    {0x11c, 0x34, 1}, // 4 room EST 0a records
    {0x11c, 0x33, 1}, // 10 room EST 0a records
    {0x11c, 0xf6, 1}, // 19 room EST 0a records
};
#endif
#if defined(RE4DC_PS2_FX_ROOMS_EXT) && RE4DC_PS2_FX_ROOMS_EXT
#if !RE4DC_PS2_FX_ROOMS
#error PS2_FX_ROOMS_EXT needs PS2_FX_ROOMS=1
#endif
// PS2_FX_ROOMS_EXT (effects30.mk; test 11 lane fx): the GC effects the PS2 rNNN.dat EFF deleted in the other chapter 1 /
// 2-1 rooms (decoded GC / PS2 records, tools/audit_ps2_fx_recipes.py --scope inventory): 1 = not drawn. Draw-time only.
//   - room-table mist sheets (Esp48, owner 0xd0 SST / 0x01 EST): no PS2 Esp48 record in r101..r10b, r117..r11b;
//   - r109 SST 2 backdrop sprites (id 0, tex 1f; the PS2 r109 EFF keeps only SST 0 lights and the SST 1 haze);
//   - r101 Esp0a window streak copies (SST 5 #6: tex 32, Del 35/10; SST 7 #13/#14 and SST 12 #0: tex 32, Del 25/4).
//     Their static id-0 copies keep the record's tex and dels (x10); the room's plain id-0 tex 32 records are
//     subtractive (blend type 3) and stay.
extern "C" void re4dc_log(const char* fmt, ...);
static int Ps2fxExtCut(cEsp* esp)
{
    const u16 room = G_ROOM_ID;
    int kind = 0;
    if ((re4dc_ps2fx & PS2FX_HAZE) && esp->m_Id == 0x48 && (esp->info.owner == 0xD0 || esp->info.owner == 0x01) &&
        ((room >= 0x101 && room <= 0x10b) || (room >= 0x117 && room <= 0x11b))) {
        kind = 1;
    } else if ((re4dc_ps2fx & PS2FX_HAZE) && room == 0x109 && esp->info.owner == 0xD0 && esp->m_Id == 0 &&
               esp->m_Tex_id == 0x1f) {
        kind = 2;
    } else if ((re4dc_ps2fx & PS2FX_STREAK) && room == 0x101 && esp->info.owner == 0xD0 && esp->m_Id == 0 &&
               esp->m_Life_max == 0 && esp->m_Tex_id == 0x32 && esp->m_Blend_type != 3 &&
               ((esp->m_Del_far == 350 && esp->m_Del_near == 100) || (esp->m_Del_far == 250 && esp->m_Del_near == 40))) {
        kind = 3;
    }
    if (kind) {
        // One log line per room, kind and texture (the evidence of what the knob removes in each room).
        static u16 s_room;
        static u32 s_seen[4][8];
        if (s_room != room) {
            s_room = room;
            for (int i = 0; i < 4; ++i) for (int j = 0; j < 8; ++j) s_seen[i][j] = 0;
        }
        const u32 t = esp->m_Tex_id;
        if (!(s_seen[kind][t >> 5] & (1U << (t & 31)))) {
            s_seen[kind][t >> 5] |= 1U << (t & 31);
            re4dc_log("ps2fx ext: r%03x %s tex %02x owner %02x blend %u del %u/%u not drawn\n", (unsigned) room,
                      kind == 1 ? "sheet" : kind == 2 ? "backdrop" : "streak", (unsigned) t, (unsigned) esp->info.owner,
                      (unsigned) esp->m_Blend_type, (unsigned) esp->m_Del_far, (unsigned) esp->m_Del_near);
        }
    }
    return kind != 0;
}
#endif
#if defined(RE4DC_FX_MIST_PS2) && RE4DC_FX_MIST_PS2
#if !RE4DC_PS2_FX_STAGE1 || !(defined(RE4DC_PS2_FX_ROOMS_EXT) && RE4DC_PS2_FX_ROOMS_EXT) || !defined(RE4DC_HAZE_SPRITE_CUT)
#error FX_MIST_PS2 needs PS2_FX_STAGE1=1, PS2_FX_ROOMS_EXT=1 and HAZE_SPRITE_CUT=1
#endif
// FX_MIST_PS2 (hwfog.mk, lane fx19): 1 for a mist sheet (Esp48) the PS2 release does not have, by the qualified PS2
// tables above: the room-table sheets of r101..r10b / r117..r11b (Ps2fxExtCut kind 1), kPs2SheetCut's room / texture
// rows, and r100's GameCube sheet textures (EFFECT_HAZE_LEAN M1's list; the PS2 keeps r100's d9 sparks). Independent
// of the runtime PS2 look toggle: HAZE_SPRITE_CUT draws no mist sheet in any case.
extern "C" void re4dc_esp48_dormant(cEsp* esp);      // esp48.cpp
extern "C" int re4dc_esp48_is_dormant(const cEsp* esp);
static u32 s_mist_ps2_n, s_mist_ps2_room = 0xffff;
static int Ps2fxMistGcOnly(const cEsp* esp)
{
    const u16 room = G_ROOM_ID;
    const u32 owner = esp->info.owner, tex = esp->m_Tex_id;
    int cut = 0;    if ((owner == 0xD0 || owner == 0x01) && ((room >= 0x101 && room <= 0x10b) || (room >= 0x117 && room <= 0x11b))) {
        cut = 1;
    } else if (room == 0x100 && owner == 0xD0 &&
               (tex == 0xf6 || tex == 0xcb || tex == 0xd0 || tex == 0xf3 || tex == 0x33)) {
        cut = 1;
    } else {
        for (unsigned i = 0; i < sizeof(kPs2SheetCut) / sizeof(kPs2SheetCut[0]); ++i) {
            if (room == kPs2SheetCut[i].room && tex == kPs2SheetCut[i].tex &&
                owner == (kPs2SheetCut[i].owner ? kPs2SheetCut[i].owner : 0xD0u)) {
                cut = 1;
                break;
            }
        }
    }
    if (cut) {
        if (s_mist_ps2_room != room) {   // one line per room: the previous room's count
            re4dc_log("mist ps2: room=%03x first tex=%02x owner=%02x (prev room %03x: %u sheets not made)\n",
                      (unsigned) room, (unsigned) tex, (unsigned) owner, (unsigned) s_mist_ps2_room, (unsigned) s_mist_ps2_n);
            s_mist_ps2_room = room;
            s_mist_ps2_n = 0;
        }
        if ((++s_mist_ps2_n & 0xFF) == 0) {
            re4dc_log("mist ps2: room=%03x frame=%u %u sheets not made\n", (unsigned) room, (unsigned) pG->Frame_cnt,
                      (unsigned) s_mist_ps2_n);
        }
    }
    return cut;
}
#endif
#if defined(RE4DC_PS2_FX_GEN) && RE4DC_PS2_FX_GEN
#if !RE4DC_PS2_FX_ROOMS
#error PS2_FX_GEN needs PS2_FX_ROOMS=1
#endif
// PS2_FX_GEN (effects30.mk; test 11 lane fx): the GameCube room effects the PS2 release deleted, for every stage-1
// room in one generated table (tools/ps2_fx_parity.py over the GC / PS2 rNNN EFF records: ps2_fx_gen.inc; the
// per-room parity report is docs/PS2_FX_PARITY.md). A matching sprite is not drawn; the hand-qualified rows above
// (haze recipes, streak / sheet cuts, statics) stay as overrides. Draw-time only: generators, Rnd(), pool, motion.
struct Ps2fxGenCutRow {
    u16 room;
    u8 kind, owner, id, tex, blend;   // kind 0 sprite, 1 Esp0a copy, 2 Esp48 sheet, 3 camera haze; blend 0xff: any
    u16 del_far, del_near;            // 0xffff: not tested (copies: x10)
    u8 r, g, b, rgb;                  // rgb: 1 = the start colour is tested
    u16 life;                         // 0xffff: not tested
};
#include "ps2_fx_gen.inc"
static int Ps2fxGenCut(cEsp* esp)
{
    static u16 s_room = 0xffff;
    static u16 s_begin, s_end;
    static u32 s_tex[8], s_seen[(PS2FX_GEN_CUTS + 31) / 32];
    const u16 room = G_ROOM_ID;
    if (room != s_room) {
        s_room = room;
        s_begin = s_end = 0;
        for (int i = 0; i < 8; ++i) s_tex[i] = 0;
        for (unsigned i = 0; i < sizeof(s_seen) / sizeof(s_seen[0]); ++i) s_seen[i] = 0;
        unsigned i = 0;
        while (i < PS2FX_GEN_CUTS && kPs2GenCut[i].room != room) ++i;
        s_begin = (u16) i;
        while (i < PS2FX_GEN_CUTS && kPs2GenCut[i].room == room) {
            s_tex[kPs2GenCut[i].tex >> 5] |= 1U << (kPs2GenCut[i].tex & 31);
            ++i;
        }
        s_end = (u16) i;
    }
    const u32 t = esp->m_Tex_id;
    if (s_begin == s_end || !(re4dc_ps2fx & PS2FX_HAZE) || !(s_tex[(t >> 5) & 7] & (1U << (t & 31)))) {
        return 0;
    }
    for (unsigned i = s_begin; i < s_end; ++i) {
        const Ps2fxGenCutRow& c = kPs2GenCut[i];
        if (c.tex != t || c.owner != esp->info.owner) continue;
        if (c.kind == 2) {
            if (esp->m_Id != 0x48) continue;
        } else if (c.kind == 1) {
            if (esp->m_Id != 0 || esp->m_Del_far != c.del_far || esp->m_Del_near != c.del_near ||
                esp->m_Life_max != c.life) continue;
        } else {
            if (esp->m_Id != c.id) continue;
            if (c.blend != 0xff && esp->m_Blend_type != c.blend) continue;
            if (c.del_far != 0xffff && (esp->m_Del_far != c.del_far || esp->m_Del_near != c.del_near)) continue;
            if (c.life != 0xffff && esp->m_Life_max != c.life) continue;
            if (c.rgb && (esp->m_Col_start_r != c.r || esp->m_Col_start_g != c.g || esp->m_Col_start_b != c.b)) continue;
        }
        if (!(s_seen[i >> 5] & (1U << (i & 31)))) {
            s_seen[i >> 5] |= 1U << (i & 31);
            re4dc_log("ps2fx gen: r%03x row %u kind %u id %02x tex %02x owner %02x not drawn\n", (unsigned) room, i,
                      (unsigned) c.kind, (unsigned) esp->m_Id, (unsigned) t, (unsigned) esp->info.owner);
        }
        return 1;
    }
    return 0;
}
#endif
#if defined(RE4DC_FX_LEVEL)
// FX_LEVEL (effects30.mk; test 11 lane fx): one effects-quality dial over every PS2-derived room effect recipe: the
// room SST / EST table effects (owners 0xd0 / 0x01) with the PS2 look on, the PS2-added haze (PS2_FX_ADDITIONS) and
// r11b's PS2 rain (RAIN_PS2). Draw time only: a thinned particle still spawns, moves and makes its Rnd() draws; spawn
// counts and generator records are never touched. Weapon, enemy and object effects (blood, muzzle flash, torch glows)
// have other owners and are never scaled. re4dc_fx_level is the runtime value (build default FX_LEVEL) that a menu or
// tester toggle can change without a rebuild; the hwfog lane's fog-replaced layers read the same accessors.
struct FxLevel {
    u8 keep_of_8;   // particles drawn per 8: a fixed hash of the pool slot, so the same particles stay (no flicker)
    f32 size;       // quad scale about its centre (translucent fill ~ size^2)
    f32 alpha;      // alpha scale (above 1 keeps a thinned cloud's density)
    f32 far;        // view-depth cap, mm (0: none; camera haze is exempt, it has its own range)
    u16 budget;     // room-effect sprites per frame (0: none)
    u8 rain;        // r11b PS2 rain lines per 100
    u16 owners;     // EFFECT_OWNERS_ALL: admitted-owner sprites per frame (0: none)
};
static const FxLevel kFxLevel[3] = {
    {8, 1.0f, 1.0f, 0.0f, 0, 100, 48},          // 0: PS2 as-is
    {6, 0.9f, 1.15f, 40000.0f, 48, 70, 32},     // 1: reduced
    {4, 0.8f, 1.3f, 25000.0f, 32, 50, 16},      // 2: low
};
enum { FXL_THIN = 1, FXL_SIZE = 2, FXL_ALPHA = 4, FXL_FAR = 8, FXL_BUDGET = 16, FXL_ALL = 31 };
// Per-recipe overrides: the dial parts a matching sprite keeps out of (room 0, id / tex 0xff: any).
struct FxLevelOverride { u16 room; u8 id, tex, skip; };
static const FxLevelOverride kFxLevelOverride[] = {
    {0x000, 0x48, 0xff, FXL_THIN | FXL_BUDGET},                      // a mist sheet is the whole layer
    {0x104, 0x00, 0x08, FXL_ALL}, {0x104, 0x00, 0x1f, FXL_ALL}, {0x104, 0x00, 0xe9, FXL_ALL},   // r104 PS2 statics
};
extern "C" {
u8 re4dc_fx_level = RE4DC_FX_LEVEL;
int re4dc_fx_level_get(void) { return re4dc_fx_level; }
void re4dc_fx_level_set(int level) { re4dc_fx_level = (u8) (level < 0 ? 0 : level > 2 ? 2 : level); }
void re4dc_fx_level_cycle(void) { re4dc_fx_level_set(re4dc_fx_level >= 2 ? 0 : re4dc_fx_level + 1); }
float re4dc_fx_level_size(void) { return kFxLevel[re4dc_fx_level].size; }
float re4dc_fx_level_alpha(void) { return kFxLevel[re4dc_fx_level].alpha; }
unsigned re4dc_fx_level_rain(unsigned n) { return n * kFxLevel[re4dc_fx_level].rain / 100; }
}
static unsigned FxLevelParts(const cEsp* esp)
{
    if (!re4dc_fx_level || !(re4dc_ps2fx & PS2FX_HAZE) || (esp->info.owner != 0xD0 && esp->info.owner != 0x01)) {
        return 0;
    }
    unsigned parts = FXL_ALL;
    if (esp->m_Id == 0x15) parts &= ~FXL_FAR;
    if (esp->m_Id == 0 && esp->m_Life_max <= 1) parts &= ~FXL_THIN;   // a permanent static: thinned, it is a hole
    const u16 room = G_ROOM_ID;
    for (unsigned i = 0; i < sizeof(kFxLevelOverride) / sizeof(kFxLevelOverride[0]); ++i) {
        const FxLevelOverride& o = kFxLevelOverride[i];
        if ((!o.room || o.room == room) && (o.id == 0xff || o.id == esp->m_Id) &&
            (o.tex == 0xff || o.tex == esp->m_Tex_id)) {
            parts &= ~o.skip;
        }
    }
    return parts;
}
static int FxLevelKeep(u32 key)
{
    return ((key * 2654435761U) >> 29) < kFxLevel[re4dc_fx_level].keep_of_8;
}
// Ps2fxClass: 1 = thinned out at this level.
#if defined(RE4DC_LAKE_FIX_TOGGLE) && RE4DC_LAKE_FIX_TOGGLE
extern "C" unsigned char re4dc_lake_fix;   // native_ui.cpp (effects30.mk LAKE_FIX_TOGGLE)
#endif
static int FxLevelThin(cEsp* esp)
{
#if defined(RE4DC_SHORE_FX_LEVEL)
    // SHORE_FX_LEVEL (effects30.mk, lane lake20): the night lake shore (r11b) draws at its own level; every Ps2fxClass
    // call passes here first, so the level follows the room before any sprite or rain line of the frame is drawn.
#if defined(RE4DC_LAKE_FIX_TOGGLE) && RE4DC_LAKE_FIX_TOGGLE
    re4dc_fx_level = (u8) (G_ROOM_ID == 0x11b && re4dc_lake_fix ? RE4DC_SHORE_FX_LEVEL : RE4DC_FX_LEVEL);   // LAKE_FIX_TOGGLE
#else
    re4dc_fx_level = (u8) (G_ROOM_ID == 0x11b ? RE4DC_SHORE_FX_LEVEL : RE4DC_FX_LEVEL);
#endif
#endif
    return (FxLevelParts(esp) & FXL_THIN) && !FxLevelKeep((u32) ((u8*) esp - (u8*) g_pEspSys->pEspBuf) / 0x150);
}
static void FxLevelScale(Re4dcEffectSprite* s, f32 size, f32 alpha)
{
    if (size != 1.0f) {
        const f32 mx = (s->x[0] + s->x[1] + s->x[2] + s->x[3]) * 0.25f, my = (s->y[0] + s->y[1] + s->y[2] + s->y[3]) * 0.25f;
        for (int i = 0; i < 4; ++i) {
            s->x[i] = mx + (s->x[i] - mx) * size;
            s->y[i] = my + (s->y[i] - my) * size;
        }
    }
    if (alpha != 1.0f) {
        const f32 a = (f32) (s->color >> 24) * alpha;
        s->color = (s->color & 0xffffffU) | ((a >= 255.0f ? 255U : (u32) a) << 24);
    }
}
#if defined(RE4DC_FX_TRIM) && RE4DC_FX_TRIM
// FX_TRIM (effects30.mk, lane fx-trim23; render only): the FX_LEVEL dial over EVERY effect sprite, not only the PS2
// room recipes: fire, smoke, dust, sparks, blood, glows of enemies, objects, weapons and rooms. At the emit, after the
// effect has moved, lived and drawn its Rnd(): nothing the game reads changes. Per frame, an effect id keeps its first
// `free` sprites; past them a fixed hash of the pool slot keeps keep_of_8 (the same particles stay: no flicker). Sprites
// deeper than `far` mm or smaller than `min_px` screen pixels are not drawn, and at most `budget` trimmed-class sprites
// a frame. Leon's own effects (owner 0x03: muzzle flash, his blood) and screen-space sprites are never trimmed.
struct FxTrim { u8 free, keep_of_8; f32 far, min_px; u16 budget; };
static const FxTrim kFxTrim[3] = {
    {255, 8, 0.0f, 0.0f, 0},                 // 0: as-is (FX_TRIM_LOG counts only)
    {6, 4, 30000.0f, 24.0f, 48},             // 1: reduced
    {4, 3, 20000.0f, 48.0f, 32},             // 2: low
};
#if defined(RE4DC_FX_TRIM_LOG) && RE4DC_FX_TRIM_LOG
// FX_TRIM_LOG (test only): "fx trim:" every 120 frames, per-frame means: sprites seen / drawn by owner class (r room
// 0x01 / 0xd0, l Leon 0x03, e enemies / animals / objects 0x10..0xcf, o other), drops by reason, and the drawn and seen
// translucent screen area in 1/100 screens (640x480).
static u32 s_ftl_frame0, s_ftl_frames, s_ftl_seen[4], s_ftl_drawn[4], s_ftl_drop[5];
static f32 s_ftl_area_seen, s_ftl_area_drawn;
static u32 s_ftl_unk[64];   // owner << 16 | id << 8 | tex (key 0: owner 0 id 0 tex 0 never logged)
static u32 s_ftl_kind[64];  // the same key | 1 << 24 when not drawn: non-room sprite kinds ("fx ess kinds:")
#endif
static unsigned FxTrimOwnerClass(unsigned owner)
{
    return owner == 0x01 || owner == 0xD0 ? 0 : owner == 0x03 ? 1 : owner >= 0x10 && owner < 0xD0 ? 2 : 3;
}
static f32 FxTrimArea(const Re4dcEffectSprite* s)
{
    f32 a = 0.0f;
    for (int i = 0; i < 4; ++i) {
        const int j = (i + 1) & 3;
        a += s->x[i] * s->y[j] - s->x[j] * s->y[i];
    }
    return a < 0.0f ? -a * 0.5f : a * 0.5f;
}
// "Essential only" (user 10-23; FX_LEVEL=3 = the room dial at 0 + this filter, so the PS2 room-effect
// thinning (Ps2fxClass, which LOGIC_WASTE's effect skip reads) stays as at level 0 and only the emit decides; runtime re4dc_fx_essential): keep the
// effects that carry gameplay (muzzle flash, hit blood, explosions and fire incl. grenades / traps / burning hazards,
// blob shadows; Leon's own effects whole), cut the atmosphere (mist / haze sheets, dust, ambient smoke and sparks,
// glows, light shafts, glare, trails / ribbons) and stack at most kEssLayer sprites of one smoke / spark layer per owner.
// Classes by effect texture id: the core EFF ids (etc/core.das EFF#1) and the room EFF ids are one global id space and
// keep their meaning across rooms (sheets in the lane evidence, texsheets/). Unknown ids: drawn (capped) for enemies,
// objects and weapons, cut for the room's own ambient tables (owners 0x01 / 0xd0).
enum { ESS_KEEP = 1, ESS_LAYER = 2, ESS_CUT = 3, ESS_GLOW = 4 };
static u8 s_ess_class[256];
static void FxEssInit()
{
    static const u8 keep[] = {0x00, 0x01, 0x03, 0x04, 0x06, 0x07, 0x09, 0x0c, 0x0e, 0x0f, 0x10, 0x16, 0x18, 0x19, 0xce,   // blood
                              0x23, 0x1b, 0x26, 0x28, 0x2c, 0x2e, 0xcd, 0x29, 0x85, 0x86,   // explosion, blast ring, fire, flames
                              0xb2,                                                           // blob shadow disc
                              // Ganado EFF (em10): blood, gore, the burst with fire
                              0x37, 0x3b, 0x3c, 0x3f, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0x4a, 0x4b, 0x54};
    static const u8 layer[] = {0x12, 0x1d, 0x1e, 0x1f, 0x24, 0x51, 0x52, 0x53, 0xff, 0xca, 0xc3,   // smoke
                               0x56, 0x57, 0x58, 0x5a, 0xe2, 0xe3,                              // sparks, debris, embers
                               // Ganado EFF (em10): hit debris, dirt and dust puffs, chips, water drops
                               0x36, 0x38, 0x39, 0x3a, 0x3d, 0x3e, 0x40, 0x41, 0x4c, 0x4d, 0x4e, 0x4f, 0x93, 0x95, 0x98, 0x9f,
                               0xa4};
    static const u8 cut[] = {0x5f, 0x6f, 0x72, 0x79, 0xe9, 0x9d,          // dust
                             0xc1};                                       // light shafts, glare
    static const u8 glow[] = {0x08, 0x0b, 0x13, 0x17, 0x1c, 0xf7};       // glows, flares: cut, except owner 0x00's
    for (unsigned i = 0; i < sizeof(keep); ++i) s_ess_class[keep[i]] = ESS_KEEP;
    for (unsigned i = 0; i < sizeof(layer); ++i) s_ess_class[layer[i]] = ESS_LAYER;
    for (unsigned i = 0; i < sizeof(cut); ++i) s_ess_class[cut[i]] = ESS_CUT;
    for (unsigned i = 0; i < sizeof(glow); ++i) s_ess_class[glow[i]] = ESS_GLOW;
}
enum { kEssLayer = 2 };
extern "C" {
u8 re4dc_fx_essential = RE4DC_FX_ESSENTIAL_BOOT;
}
// FX_EARLY_CUT (lane fxcut28, effects30.mk) enables this early Essential decline on its own, without ESP_SETUP_LEAN's
// header sharing: the unconditional cuts return before the matrix / projection / sprite build.
#if ((defined(RE4DC_ESP_SETUP_LEAN) && RE4DC_ESP_SETUP_LEAN) || (defined(RE4DC_FX_EARLY_CUT) && RE4DC_FX_EARLY_CUT == 1)) && \
    !(defined(RE4DC_FX_TRIM_LOG) && RE4DC_FX_TRIM_LOG) && \
    !(defined(RE4DC_ESP_CENSUS) && RE4DC_ESP_CENSUS) && !defined(RE4DC_MIST_CUT)
#define RE4DC_ESP_ESSENTIAL_EARLY 1
// The original late reset points own these stamps. The shortcut is only legal
// after both have already seen this frame; frame rewinds and Essential toggles
// must still clear exactly the same buckets, even in frames containing cuts only.
static u32 s_esp_setup_trim_frame = ~0U, s_esp_setup_ess_frame = ~0U;
#endif
// 1: not drawn under Essential.
#if defined(RE4DC_R117_FX_FALLBACK)
static int Ps2fxPuzzleFallback(const cEsp* esp);
#endif
static int FxEssentialCut(const cEsp* esp, int screen)
{
#if defined(RE4DC_ESP_ESSENTIAL_EARLY)
    u32& s_frame = s_esp_setup_ess_frame;
#else
    static u32 s_frame = ~0U;
#endif
    static u8 s_layer[256];   // (owner ^ tex) buckets: sprites of one layer this frame
    if (!s_ess_class[0x00]) FxEssInit();
    if (s_frame != pG->Frame_cnt) {
        s_frame = pG->Frame_cnt;
        for (int i = 0; i < 256; ++i) s_layer[i] = 0;
    }
    const unsigned owner = esp->info.owner;
    if (owner == 0x03) return 0;                                   // Leon: muzzle flash, his blood, his grenades
    if (esp->m_Id == 0x0e || esp->m_Id == 0x15 || esp->m_Id == 0x48) return 1;   // glows, haze, mist sheets
    if (screen) return 0;
#if defined(RE4DC_R117_FX_FALLBACK)
    if (Ps2fxPuzzleFallback(esp)) return 0;
#endif
    const unsigned c = s_ess_class[esp->m_Tex_id & 0xFF];
    const int room = owner == 0x01 || owner == 0xD0;
    if (c == ESS_KEEP) return 0;
    if (c == ESS_CUT) return 1;
    // Owner 0x00 (core / weapon effects: the hand, incendiary and flash grenade blasts, the laser sight's glint;
    // lane fx-trim23 grenade check 10-23, FX_TRIM_LOG "fx ess kinds") keeps its glows and flares.
    if (c == ESS_GLOW) return owner != 0x00;
    if (room) return 1;                                            // the room's ambient smoke / sparks / leaves / dust
    u8* n = &s_layer[(owner * 31U + esp->m_Tex_id) & 0xFF];          // layers and unknown ids: one thin layer each
    return (*n)++ >= kEssLayer;
}
#if defined(RE4DC_ESP_ESSENTIAL_EARLY)
// Only stateless, unconditional cuts. Layer buckets still count at their
// original post-projection point, so clipped/missing sprites cannot spend them.
// Haze feeds hardware fog and torch glows have draw diagnostics: keep both on
// the original path, even when Essential ultimately declines their sprites.
static int FxEssentialSetupCut(const cEsp* esp, int screen)
{
    if (!re4dc_fx_essential || esp->info.owner == 0x03 ||
        esp->m_Id == 0x15 || esp->m_Id == 0x48 || esp->m_Id == 0x0e) return 0;
#if defined(RE4DC_EFFECT_TORCH) && RE4DC_EFFECT_TORCH
    if (re4dc_esp0e_glow) return 0;
#endif
    if (screen) return 0;
    if (!s_ess_class[0x00]) return 0; // the first eligible late call initializes it
#if defined(RE4DC_R117_FX_FALLBACK)
    if (Ps2fxPuzzleFallback(esp)) return 0;
#endif
    const unsigned c = s_ess_class[esp->m_Tex_id & 0xFF];
    if (c == ESS_KEEP) return 0;
    const int cut = c == ESS_CUT || (c == ESS_GLOW ? esp->info.owner != 0x00 :
                                   esp->info.owner == 0x01 || esp->info.owner == 0xD0);
    // Kept sprites need neither stamp line. Potential cuts still preserve the
    // original late reset points, including frame rewinds and mode switches.
    return cut && s_esp_setup_trim_frame == pG->Frame_cnt && s_esp_setup_ess_frame == pG->Frame_cnt;
}
#endif
// FX_STRIP21 strips (Esp01 / Esp02 trails, ribbons): not drawn under Essential except Leon's.
extern "C" int re4dc_fx_essential_strip_cut(const cEsp* esp)
{
    return re4dc_fx_essential && esp->info.owner != 0x03;
}
// 0: not drawn. reason: 0 drawn, 1 thinned, 2 far, 3 small, 4 budget, 5 essential.
static int FxTrimSprite(const cEsp* esp, const Re4dcEffectSprite* s, f32 area)
{
#if defined(RE4DC_ESP_ESSENTIAL_EARLY)
    u32& s_frame = s_esp_setup_trim_frame;
    static u32 s_used;
#else
    static u32 s_frame = ~0U, s_used;
#endif
    static u8 s_per_id[256];
    if (s_frame != pG->Frame_cnt) {
        s_frame = pG->Frame_cnt;
        s_used = 0;
        for (int i = 0; i < 256; ++i) s_per_id[i] = 0;
    }
    if (re4dc_fx_essential) {
        return FxEssentialCut(esp, s->screen) ? 5 : 0;   // Essential: kinds only (no thinning of what it keeps)
    }
    if (s->screen || esp->info.owner == 0x03) {
        return 0;
    }
    const FxTrim& T = kFxTrim[re4dc_fx_level];
    if (T.keep_of_8 < 8) {
        u8* n = &s_per_id[esp->m_Id & 0xFF];
        if (*n < 255) ++*n;
        if (*n > T.free) {
            const u32 slot = (u32) ((const u8*) esp - (const u8*) g_pEspSys->pEspBuf) / 0x150;
            if (((slot * 2654435761U) >> 29) >= T.keep_of_8) return 1;
        }
    }
    if (T.far > 0.0f && s->z[0] > 0.0f && 1.0f / s->z[0] > T.far && esp->m_Id != 0x0e) {   // Esp0e: torch glows stay
        return 2;
    }
    if (T.min_px > 0.0f && area < T.min_px) {
        return 3;
    }
    if (T.budget && s_used >= T.budget) {
        return 4;
    }
    ++s_used;
    return 0;
}
static int FxLevelSpriteBase(const cEsp* esp, Re4dcEffectSprite* s);
static int FxLevelSprite(const cEsp* esp, Re4dcEffectSprite* s)
{
    const f32 area = FxTrimArea(s);
    const int why = FxTrimSprite(esp, s, area);
    const int drawn = !why && FxLevelSpriteBase(esp, s);
#if defined(RE4DC_FX_TRIM_LOG) && RE4DC_FX_TRIM_LOG
    if (s_ftl_frame0 != pG->Frame_cnt) {
        s_ftl_frame0 = pG->Frame_cnt;
        if (++s_ftl_frames == 120) {
            const u32 F = 120;
            re4dc_log("fx trim: f=%u room=%03x lvl=%u seen r%u l%u e%u o%u drawn r%u l%u e%u o%u drop thin%u far%u small%u budget%u "
                      "ess%u area seen=%u drawn=%u\n", (unsigned) s_ftl_frame0, (unsigned) G_ROOM_ID,
                      (unsigned) re4dc_fx_level + 3U * re4dc_fx_essential,
                      s_ftl_seen[0] / F, s_ftl_seen[1] / F, s_ftl_seen[2] / F, s_ftl_seen[3] / F, s_ftl_drawn[0] / F,
                      s_ftl_drawn[1] / F, s_ftl_drawn[2] / F, s_ftl_drawn[3] / F, s_ftl_drop[0] / F, s_ftl_drop[1] / F,
                      s_ftl_drop[2] / F, s_ftl_drop[3] / F, s_ftl_drop[4] / F, (unsigned) (s_ftl_area_seen / (F * 3072.0f)),
                      (unsigned) (s_ftl_area_drawn / (F * 3072.0f)));
            {   // unclassified texture ids met this window (owner.tex.id), for the Essential table
                char buf[200];
                int k = 0;
                for (int i = 0; i < 64 && s_ftl_unk[i]; ++i) {
                    k += __builtin_snprintf(buf + k, sizeof(buf) - k, " %02x.%02x.%02x", (unsigned) (s_ftl_unk[i] >> 16),
                                  (unsigned) (s_ftl_unk[i] & 0xff), (unsigned) ((s_ftl_unk[i] >> 8) & 0xff));
                    s_ftl_unk[i] = 0;
                    if (k > 180) break;
                }
                for (int i = 0; i < 64; ++i) s_ftl_unk[i] = 0;
                if (k) re4dc_log("fx ess unknown: room=%03x%s\n", (unsigned) G_ROOM_ID, buf);
                k = 0;   // every non-room sprite kind met this window: owner.tex.id + d (drawn) / c (cut)
                for (int i = 0; i < 64 && s_ftl_kind[i]; ++i) {
                    if (k < 180)
                        k += __builtin_snprintf(buf + k, sizeof(buf) - k, " %02x.%02x.%02x%c",
                                                (unsigned) ((s_ftl_kind[i] >> 16) & 0xff), (unsigned) (s_ftl_kind[i] & 0xff),
                                                (unsigned) ((s_ftl_kind[i] >> 8) & 0xff), (s_ftl_kind[i] >> 24) ? 'c' : 'd');
                    s_ftl_kind[i] = 0;
                }
                if (k) re4dc_log("fx ess kinds: room=%03x%s\n", (unsigned) G_ROOM_ID, buf);
            }
            for (int i = 0; i < 4; ++i) s_ftl_seen[i] = s_ftl_drawn[i] = 0;
            for (int i = 0; i < 5; ++i) s_ftl_drop[i] = 0;
            s_ftl_area_seen = s_ftl_area_drawn = 0.0f;
            s_ftl_frames = 0;
        }
    }
    {
        const unsigned c = FxTrimOwnerClass(esp->info.owner);
        if (!s_ess_class[0x00]) FxEssInit();
        if (!s_ess_class[esp->m_Tex_id & 0xFF] && esp->info.owner != 0x03) {
            const u32 key = ((u32) esp->info.owner << 16) | ((u32) esp->m_Id << 8) | esp->m_Tex_id;
            for (int i = 0; i < 64; ++i) {
                if (s_ftl_unk[i] == key) break;
                if (!s_ftl_unk[i]) { s_ftl_unk[i] = key; break; }
            }
        }
        if (c != 0) {
            const u32 key = ((u32) esp->info.owner << 16) | ((u32) esp->m_Id << 8) | esp->m_Tex_id | (drawn ? 0U : 1U << 24);
            for (int i = 0; i < 64; ++i) {
                if (s_ftl_kind[i] == key) break;
                if (!s_ftl_kind[i]) { s_ftl_kind[i] = key; break; }
            }
        }
        ++s_ftl_seen[c];
        s_ftl_area_seen += area;
        if (drawn) {
            ++s_ftl_drawn[c];
            s_ftl_area_drawn += FxTrimArea(s);
        } else if (why) {
            ++s_ftl_drop[why - 1];
        }
    }
#else
    (void) FxTrimOwnerClass;
#endif
    return drawn;
}
static int FxLevelSpriteBase(const cEsp* esp, Re4dcEffectSprite* s)
#else
// EspSpriteEmit: depth cap, per-frame budget, size and alpha (0: not drawn).
static int FxLevelSprite(const cEsp* esp, Re4dcEffectSprite* s)
#endif
{
#if defined(RE4DC_EFFECT_OWNERS_ALL) && RE4DC_EFFECT_OWNERS_ALL
    if (EspOwnerAdmitted(esp->info.owner)) { if (esp->info.owner == 0x03 || !kFxLevel[re4dc_fx_level].owners) return 1;   // PL00 opt-out
        static u32 s_owner_frame, s_owner_used;   // admitted owners: the per-frame budget only
        if (s_owner_frame != pG->Frame_cnt) {
            s_owner_frame = pG->Frame_cnt;
            s_owner_used = 0;
        }
        return s_owner_used++ < kFxLevel[re4dc_fx_level].owners;
    }
#endif
    const unsigned parts = s->screen ? 0 : FxLevelParts(esp);
    if (!parts) {
        return 1;
    }
    const FxLevel& L = kFxLevel[re4dc_fx_level];
    if ((parts & FXL_FAR) && L.far > 0.0f && s->z[0] > 0.0f && 1.0f / s->z[0] > L.far) {
        return 0;
    }
    if ((parts & FXL_BUDGET) && L.budget) {
        static u32 s_frame, s_used;
        if (s_frame != pG->Frame_cnt) {
            s_frame = pG->Frame_cnt;
            s_used = 0;
        }
        if (s_used >= L.budget) {
            return 0;
        }
        ++s_used;
    }
    FxLevelScale(s, (parts & FXL_SIZE) ? L.size : 1.0f, (parts & FXL_ALPHA) ? L.alpha : 1.0f);
    return 1;
}
#endif
// 0: draw as usual; 1: not drawn (a haze sprite outside the PS2 subset / box, a streak copy); 2: a streak
// anchor (=2: draws the PS2 shafts in its place).
#if RE4DC_PS2_FX_ADDITIONS
static int Ps2fxPuzzleSuppress(cEsp* esp);
#endif
#if RE4DC_PS2_FX_COMMON_HAZE
static int Ps2fxCommonHazeSuppress(cEsp* esp);
#endif
#if defined(RE4DC_LOGIC_WASTE) && RE4DC_LOGIC_WASTE && !RE4DC_PS2_FX_COMMON_HAZE
extern "C" u32 re4dc_logic_waste_mask;
static int lwFxInner;
static int lwFxClass(cEsp* esp);   // LOGIC_WASTE bit 0x02 (after Ps2fxClass)
#endif
#line 919   // LOGIC_WASTE blocks keep the knob-off line numbers (EspCommonTrans's __LINE__)
static int Ps2fxClass(cEsp* esp)
{
#if defined(RE4DC_LOGIC_WASTE) && RE4DC_LOGIC_WASTE && !RE4DC_PS2_FX_COMMON_HAZE
    if ((re4dc_logic_waste_mask & 2) && !lwFxInner) {
        return lwFxClass(esp);
    }
#endif
#line 921
#if defined(RE4DC_FX_LEVEL)
    if (FxLevelThin(esp)) {
        return 1;
    }
#endif
#if RE4DC_PS2_FX_COMMON_HAZE
    if(Ps2fxCommonHazeSuppress(esp))return 1;
#endif
#if RE4DC_PS2_FX_ADDITIONS
    if(Ps2fxPuzzleSuppress(esp)) return 1;
#endif
#if RE4DC_PS2_FX_STAGE1
    // Owner 1 is the room's main EST table (game.cpp); its copies keep the owner stamp.
    if (esp->info.owner == 1) {
        if ((re4dc_ps2fx & PS2FX_HAZE) && G_ROOM_ID == 0x10d && esp->m_Id == 0x15) {
            const f32 range = static_cast<cPs2fxEsp15*>(esp)->m_Free.Range;
            if ((esp->m_Tex_id == 0xc6 && range == 500.0f) ||
                (esp->m_Tex_id == 0x1e && range == 1500.0f)) {
                return 1; // Exact special EST15 sources; the PS2 room has neither.
            }
        }
        // Work8[0]=1 gives these static copies life=1, unlike the permanent SST streak copies.
        if ((re4dc_ps2fx & PS2FX_STREAK) && esp->m_Id == 0 && esp->m_Life_max == 1 &&
            esp->m_Blend_type == 1 && esp->m_Tex_id == 0x32) {
            if ((G_ROOM_ID == 0x111 &&
                 ((esp->m_Del_far == 350 && esp->m_Del_near == 100 && esp->m_Col_start_r == 110 &&
                   esp->m_Col_start_g == 115 && esp->m_Col_start_b == 115) ||
                  (esp->m_Del_far == 250 && esp->m_Del_near == 40 && esp->m_Col_start_r == 175 &&
                   esp->m_Col_start_g == 185 && esp->m_Col_start_b == 185))) ||
                (G_ROOM_ID == 0x112 && esp->m_Del_far == 200 && esp->m_Del_near == 100 &&
                 esp->m_Col_start_r == 235 && esp->m_Col_start_g == 245 && esp->m_Col_start_b == 255)) {
                return 1;
            }
        }
    }
#endif
#if RE4DC_PS2_FX_STAGE1
    // Keep source emissions, RNG and pool ownership; omit only the qualified SST/EST sheet draws.
    if ((re4dc_ps2fx & PS2FX_HAZE) && esp->m_Id == 0x48) {
        for (unsigned i = 0; i < sizeof(kPs2SheetCut) / sizeof(kPs2SheetCut[0]); ++i) {
            if (G_ROOM_ID == kPs2SheetCut[i].room && esp->m_Tex_id == kPs2SheetCut[i].tex &&
                esp->info.owner == (kPs2SheetCut[i].owner ? kPs2SheetCut[i].owner : 0xD0)) {
                return 1;
            }
        }
    }
#endif
#if defined(RE4DC_PS2_FX_ROOMS_EXT) && RE4DC_PS2_FX_ROOMS_EXT
    if (Ps2fxExtCut(esp)) {
        return 1;
    }
#endif
#if defined(RE4DC_PS2_FX_GEN) && RE4DC_PS2_FX_GEN
    if (Ps2fxGenCut(esp)) {
        return 1;
    }
#endif
    if (esp->info.owner != 0xD0) {
#if RE4DC_PS2_FX_STAGE1
        if (esp->info.owner != 1 || G_ROOM_ID != 0x200 || esp->m_Id != 0x15) {
            return 0;
        }
#else
        return 0;
#endif
    }
#if RE4DC_EFFECT_PS2_HAZE
    if (esp->m_Id == 0x15) {
        const Ps2fxHaze* h = Ps2fxHazeFor(esp);
        if (!h) {
            return 0;
        }
#if RE4DC_PS2_FX_POPULATION
        const int population = Ps2fxPopulationState(esp, h);
        if (h->room == 0x112 && !s_fx_area112) return 1;
        if (population >= 0) return population ? 0 : 1;
#endif
        const u32 slot = (u32) ((u8*) esp - (u8*) g_pEspSys->pEspBuf) / 0x150;
#if defined(RE4DC_EFFECT_HAZE_LEAN) && (RE4DC_EFFECT_HAZE_LEAN & 2)
        const u8 every2 = RE4DC_HZ(2) ? Ps2fxEvery2(h->room) : 0;
        if (every2) {
            const Ps2fxEsp15Work* w = &static_cast<cPs2fxEsp15*>(esp)->m_Free;
            f32 fade = 1.0f;
            if (w->Room_del_frame != 0 && w->Room_del_cnt != 0) {
                const u32 cnt = w->Room_del_cnt < w->Room_del_frame ? w->Room_del_cnt : w->Room_del_frame;
                fade = 1.0f - (f32) cnt / w->Room_del_frame;
            }
            s_haze_key = ((u32) (fade * 8.0f + 0.5f) << 4) | (h->room == 0x100 ? 1U : h->room == 0x101 ? 2U : 3U);
            s_haze_key_frame = pG->Frame_cnt;
        }
        if (slot % (every2 ? every2 : h->every)) {
            return 1;
        }
#else
        if (slot % h->every) {
            return 1;
        }
#endif
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
#if RE4DC_PS2_FX_ROOMS
    if ((re4dc_ps2fx & PS2FX_STREAK) && esp->m_Id == 0 && esp->m_Life_max == 0 && esp->m_Blend_type == 1) {
        const u16 room = G_ROOM_ID;
        for (int i = 0; i < PS2FX_STREAK_CUTS; ++i) {
            const Ps2fxStreakCut* c = &kPs2StreakCut[i];
            if (c->room == room && esp->m_Tex_id == c->tex && esp->m_Del_far == c->del_far &&
                esp->m_Del_near == c->del_near) {
                return 1;
            }
        }
    }
#endif
#endif
    return 0;
}
#if defined(RE4DC_LOGIC_WASTE) && RE4DC_LOGIC_WASTE && !RE4DC_PS2_FX_COMMON_HAZE
// LOGIC_WASTE bit 0x02 (game30.mk; logic waste census item 2; render only, exact): after the FX level thinning (per pool
// slot, first in the cascade and evaluated here as before) Ps2fxClass's verdict is a function of the sprite's recipe
// fields (id, texture, owner, blend, near / far delete, start colour, life) and the room, re4dc_ps2fx and FX level,
// for every sprite except: the camera haze (id 0x15: population, slot subset, fade key and camera box per frame), r117
// (the puzzle trails, per frame) and the static id-0 copies the r100 streak anchors test by position. Many sprites
// share a recipe, so the verdicts are kept per recipe (64 entries, direct-mapped). The verdict's only other effects are
// the ps2fx ext / gen "not drawn" log lines, printed on the first sighting (a miss) as before. Check mode (0x100):
// every reuse is also computed and compared ("LWF ... mis=" must stay 0).
struct LwFxEntry {
    u32 k[4];
    u32 v;   // verdict + 1 (0: empty)
};
static LwFxEntry lwFx[64];
static u32 lwFxStat[4];
static int lwFxClass(cEsp* esp)
{
    const u16 room = G_ROOM_ID;
    if (esp->m_Id == 0x15 || room == 0x117 || (esp->m_Id == 0 && esp->m_Life_max == 0 && esp->m_Blend_type == 1)) {
        lwFxInner = 1;
        const int r = Ps2fxClass(esp);
        lwFxInner = 0;
        return r;
    }
#if defined(RE4DC_FX_LEVEL)
    if (FxLevelThin(esp)) {
        return 1;
    }
#endif
    u32 k[4];
    k[0] = (u32) esp->m_Id | ((u32) esp->m_Tex_id << 8) | ((u32) esp->info.owner << 16) | ((u32) esp->m_Blend_type << 24);
    k[1] = (u32) esp->m_Del_near | ((u32) esp->m_Del_far << 16);
    k[2] = (u32) esp->m_Col_start_r | ((u32) esp->m_Col_start_g << 8) | ((u32) esp->m_Col_start_b << 16) |
           ((u32) re4dc_ps2fx << 24);
#if defined(RE4DC_FX_LEVEL)
    k[3] = (u32) esp->m_Life_max | ((u32) room << 16) ^ ((u32) re4dc_fx_level << 30);
#else
    k[3] = (u32) esp->m_Life_max | ((u32) room << 16);
#endif
    LwFxEntry& e = lwFx[((k[0] ^ (k[1] * 3) ^ (k[2] * 5) ^ (k[3] * 7)) * 0x9E3779B1u) >> 26];
    lwFxStat[0]++;
    if (e.v && e.k[0] == k[0] && e.k[1] == k[1] && e.k[2] == k[2] && e.k[3] == k[3]) {
        lwFxStat[1]++;
        if (re4dc_logic_waste_mask & 0x100) {
            lwFxInner = 1;
            const int r = Ps2fxClass(esp);
            lwFxInner = 0;
            if ((u32) r + 1 != e.v) {
                lwFxStat[2]++;
            }
        }
        if ((lwFxStat[0] & 0x3FFF) == 0) {
            re4dc_log("LWF calls=%u hits=%u mis=%u\n", lwFxStat[0], lwFxStat[1], lwFxStat[2]);
        }
        return (int) e.v - 1;
    }
    lwFxInner = 1;
    const int r = Ps2fxClass(esp);
    lwFxInner = 0;
    e.k[0] = k[0];
    e.k[1] = k[1];
    e.k[2] = k[2];
    e.k[3] = k[3];
    e.v = (u32) r + 1;
    return r;
}
#endif
#line 1064
#endif
#if RE4DC_PS2_FX_STAGE1
// Three stationary r104 source records differ only in size and RGBA. Source
// position, orientation, near fade, texture anchor and lifetime are unchanged.
struct Ps2fxStatic {
    u8 tex, gc_r, gc_g, gc_b, gc_a, r, g, b, a;
    f32 x, y, z, gc_x, gc_y, ps_x, ps_y;
};
static const Ps2fxStatic kPs2Static104[] = {
    {0x08,255,255,205,140,255,255,195,50,30897.478515625f,29645.291015625f,-26553.146484375f,
     18840.1640625f,18840.1640625f,34300.0f,34300.0f},
    {0x1f,255,255,255,225,255,255,255,200,30897.478515625f,32668.3046875f,-26553.146484375f,
     58542.765625f,58542.765625f,58542.765625f,58542.765625f},
    {0xe9,135,135,125,165,195,195,185,70,-8885.21484375f,2750.64013671875f,16889.587890625f,
     1726.2587890625f,5562.7021484375f,1726.2587890625f,6262.7021484375f}
};
static const Ps2fxStatic* Ps2fxStaticFor(const cEsp* esp)
{
    if (!(re4dc_ps2fx&PS2FX_HAZE) || G_ROOM_ID!=0x104 || esp->info.owner!=0xd0 || esp->m_Id!=0 ||
        esp->m_Tool_flg!=1 || esp->m_Parts_no!=0xfe || esp->parent!=pEffParentWorld || esp->m_Life_max ||
        esp->m_Size_mul!=1.0f || esp->m_Size_plus!=0.0f || (esp->m_Flg&1)) return NULL;
    for(unsigned i=0;i<3;++i) {
        const Ps2fxStatic* row=&kPs2Static104[i];
        if(esp->m_Tex_id==row->tex && esp->m_Col_start_r==row->gc_r && esp->m_Col_start_g==row->gc_g &&
           esp->m_Col_start_b==row->gc_b && esp->m_Col_start_a==row->gc_a &&
           esp->m_Col_r==row->gc_r && esp->m_Col_g==row->gc_g && esp->m_Col_b==row->gc_b && esp->m_Col_a==row->gc_a &&
           esp->m_Size_base_x==row->gc_x && esp->m_Size_base_y==row->gc_y &&
           esp->m_Pos.x==row->x && esp->m_Pos.y==row->y && esp->m_Pos.z==row->z) return row;
    }
    return NULL;
}
static GXColor Ps2fxStaticColor(const cEsp* esp, const Ps2fxStatic* row)
{
    GXColor col={row->r,row->g,row->b,row->a};
    // Preserve ChannelSet's byte truncation order: final colour, then near fade.
    if (!(esp->m_Flg&4) && EffIsSetFinalCol()) {
        GXColor final;EffGetFinalCol(&final);
        col.r=(u32)col.r*final.r>>8; col.g=(u32)col.g*final.g>>8;
        col.b=(u32)col.b*final.b>>8; col.a=(u32)col.a*final.a>>8;
    }
    if(esp->m_Del_far) {
        Vec direction,delta;
        PSVECSubtract(&pG->Cam.param.at,&pG->Cam.param.pos,&direction);
        VECNormalize(&direction,&direction);
        PSVECSubtract(&esp->m_Pos,&pG->Cam.param.pos,&delta);
        const f32 depth=PSVECDotProduct(&direction,&delta);
        if(depth<esp->m_Del_far*10.0f) {
            f32 rate=1.0f-(esp->m_Del_far*10.0f-depth)/((esp->m_Del_far-esp->m_Del_near)*10.0f);
#if RE4DC_EFFECT_FADE_CLAMP
            if((re4dc_ps2fx&PS2FX_CLAMP) && rate<0.0f) rate=0.0f;
#endif
            col.a=(u8)(col.a*rate);
        }
    }
    return col;
}
#endif
#if defined(RE4DC_MIST_CUT)
// MIST_CUT effect classes (mask bits; 2 and 16 are world parts, native_static.cpp): 1 haze / mist (Esp15 camera haze,
// Esp48 mist sheets), 4 window glows / streaks / shafts (room table 0xd0 Esp0a / Esp0e), 32 room dust / smoke /
// particles (the other room table 0xd0 effects), 8 fire / torches / lamps (room EST owner 0x01, torch and lamp owners),
// 64 every other owner (shots, blood, sparks, splashes), 128 water (Esp42 / Esp45, any owner).
static unsigned MistCutClass(cEsp* esp)
{
    const u32 o = esp->info.owner;
    if (esp->m_Id == 0x42 || esp->m_Id == 0x45) return 128;
    if (esp->m_Id == 0x15 || esp->m_Id == 0x48) return 1;
    if (o == 0xD0) return (esp->m_Id == 0x0a || esp->m_Id == 0x0e) ? 4 : 32;
    if (o == 0x01 || o == 0x5E || o == 0x5F || o == 0x60 || o == 0x64 || o == 0x68 || o == 0x6D || o == 0x70 || o == 0x8C) return 8;
    return 64;
}
// Counts of the sprites the mask declined per class, one log line per room / 600 frames.
static u32 s_mist_cut_n[8], s_mist_cut_frame;
static u16 s_mist_cut_room;
static void MistCutNote(unsigned cls)
{
    const unsigned k = cls == 1 ? 0 : cls == 4 ? 1 : cls == 32 ? 2 : cls == 8 ? 3 : cls == 64 ? 4 : 5;
    ++s_mist_cut_n[k];
    if (s_mist_cut_room != G_ROOM_ID || (u32) (pG->Frame_cnt - s_mist_cut_frame) >= 600) {
        re4dc_log("mist cut: mask=%u room=%03x frame=%u haze=%u glow=%u dust=%u fire=%u other=%u water=%u\n",
                  re4dc_mist_cut, (unsigned) G_ROOM_ID, (unsigned) pG->Frame_cnt, (unsigned) s_mist_cut_n[0],
                  (unsigned) s_mist_cut_n[1], (unsigned) s_mist_cut_n[2], (unsigned) s_mist_cut_n[3],
                  (unsigned) s_mist_cut_n[4], (unsigned) s_mist_cut_n[5]);
        s_mist_cut_room = G_ROOM_ID;
        s_mist_cut_frame = pG->Frame_cnt;
        for (int i = 0; i < 8; ++i) s_mist_cut_n[i] = 0;
    }
}
#endif
#if defined(RE4DC_HAZE_SPRITE_CUT)
// HAZE_SPRITE_CUT=1 (hwfog.mk, lane nohaze16 2026-10-16; user "i don't think we need those sprites at all"; render only):
// no haze / mist sprite is drawn in any room: the camera haze around Leon (Esp15, PS2 recipe rows and every other
// Esp15), the mist sheets (Esp48) and the PS2 haze additions (r118 / r11c). The distant haze stays as the PVR fog
// table (HW_FOG_HAZE rows, EFFECT_HAZE_LEAN M3 veil: both are fed before the cut) and every room keeps its own fog.
// Generators, their Rnd() draws, the effect pool, the PS2 population choice and every motion run as before.
static u16 s_haze_cut_room = 0xffff;
static u32 s_haze_cut_n;
static void HazeCutNote(cEsp* esp)
{
    ++s_haze_cut_n;
    if (esp && s_haze_cut_room != G_ROOM_ID) {   // one line per room (proof the cut is active; counts of the previous room)
        re4dc_log("haze cut: room=%03x first id=%02x owner=%02x tex=%02x (prev room %03x: %u sprites)\n",
                  (unsigned) G_ROOM_ID, (unsigned) esp->m_Id, (unsigned) esp->info.owner, (unsigned) esp->m_Tex_id,
                  (unsigned) s_haze_cut_room, (unsigned) s_haze_cut_n);
        s_haze_cut_room = G_ROOM_ID;
        s_haze_cut_n = 0;
    }
}
#endif
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
static re4dc::NativeDrawResult EspSpriteEmitResult03(cEsp* esp){
#include "esp_sprite_outcomes03.inc"
}
#endif
static void EspSpriteEmit(cEsp* esp)
{
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
    // Source OT callbacks keep their void ABI and existing state cadence.
    (void)EspSpriteEmitResult03(esp);
#else
#include "esp_sprite_outcomes03.inc"
#endif
}
#if RE4DC_PS2_FX_COMMON_HAZE
#include "ps2_fx_common_haze.inc"
#endif
#if RE4DC_PS2_FX_ADDITIONS
extern EspgenWork* EspgenArray;
extern u32 nEspgen;
extern "C" int re4dc_room4_state(unsigned*,unsigned*,unsigned*,unsigned*,unsigned*);
static ps2fx::HazeAddition s_fx_addition;
// Shared by additions and each puzzle colour, sequentially. No heap allocation
// or 50-sprite SH4 stack frame; the native queue retains copies, never pointers.
static Re4dcEffectSprite s_stage1_sprites[50];
static const ps2fx::HazeRecipe kPs2Addition118 = {
    2000.0f, {5.0f,0.0f,0.0f}, {0.20000001788139343f,0.20000000298023224f,0.20000000298023224f},
    0x118c0defU, 30,145,155,155,34 // private seed: the source SST uses engine RNG
};
static const ps2fx::HazeRecipe kPs2Addition11c = {
    2100.0f, {-10.0f,-5.0f,-20.0f}, {2.0f,0.0f,-1.0f}, 0x1234567fU, 0,250,250,255,60
};
// Only the prefix is read; identical in espgen02.cpp and espgen00.cpp.
struct Ps2fxGeneratorClock { EspGenWork* record; cModel* model; u32 serial; u16 age, life; };
static int Ps2fxGate11c(unsigned& age, ps2fx::PopulationKey& identity, unsigned& issues)
{
    age = 0;
    if (!EspgenArray || nEspgen > 512) { issues |= 0x100; return 0; }
    EspSeqData* head = EspGetEstAddr(1,6,1);
    if (!head || head->num != 4) { issues |= 0x200; return 0; }
    EspGenWork* refs[4];
    for (unsigned i=0;i<4;++i) {
        refs[i]=re4dc_effect_ref(head,i);
        if(!refs[i]) { issues|=0x200; return 0; }
    }
    ps2fx::GateEvidence gate;
    for (unsigned i=0;i<nEspgen;++i) {
        const EspgenWork* w=&EspgenArray[i];
        if ((w->flag&3)!=1 || w->id!=2 || w->info.owner!=1) continue;
        const Ps2fxGeneratorClock* q=(const Ps2fxGeneratorClock*)w->work;
        unsigned record=0; for(;record<4;++record) if(q->record==refs[record]) break;
        if(record==4) continue;
        const ps2fx::PopulationKey identity={w->info.Call_no,w->info.Core_pEm,0,w->info.Core_flg,0,0,w->info.owner,w->info.Core_kind};
        gate.add(record,identity,q->age,!q->model && q->life==(record%2 ? 130 : 110));
    }
    const int active=gate.finish();
    if(gate.count) { age=gate.clock;identity=gate.key; }
    issues|=gate.issues;
    return active;
}
static void Ps2fxAdditionsDraw()
{
    static u16 room;
    static u8* pool;
    static EspgenWork* generators;
    static ps2fx::PopulationKey gate_identity;
    static unsigned room_generation;
    static int have_gate_identity;
    static unsigned last_issues;
    static int last_active, reported;
    unsigned issues=0, clock=(unsigned)pG->Frame_cnt, first_steps=1;
    if(!g_pEspSys) { s_fx_addition.clear();return; }
    int enabled=0, moving=1, slow=0, draws=0;
    const ps2fx::HazeRecipe* recipe=G_ROOM_ID==0x118 ? &kPs2Addition118 : &kPs2Addition11c;
    if (room!=G_ROOM_ID || pool!=g_pEspSys->pEspBuf || generators!=EspgenArray) {
        s_fx_addition.clear(); room=G_ROOM_ID; pool=g_pEspSys->pEspBuf; generators=EspgenArray; have_gate_identity=0;
        reported=0;
    }
    if(G_ROOM_ID!=0x118 && G_ROOM_ID!=0x11c) return;
    unsigned generation,cells,bytes,stale,refused;
    if(!re4dc_room4_state(&generation,&cells,&bytes,&stale,&refused)) { s_fx_addition.clear();return; }
    if(generation!=room_generation) {
        s_fx_addition.clear();room_generation=generation;have_gate_identity=0;reported=0;
    }
    if ((re4dc_ps2fx&PS2FX_HAZE) && G_ROOM_ID==0x118) {
        // Source-qualified GC and PS2 EARs are identical, including area 6.
        enabled=EffGetAreaState(6)!=0;
        moving=!(pG->Stop_flg&0x08000000) && !(pG->Status_flg[1]&2);
        slow=(pG->Status_flg[3]&0x08000000)!=0;
    } else if ((re4dc_ps2fx&PS2FX_HAZE) && G_ROOM_ID==0x11c) {
        ps2fx::PopulationKey identity;
        enabled=Ps2fxGate11c(clock,identity,issues);
        first_steps=clock; // controller clock already excludes paused/slow logic ticks
        if(enabled && (!have_gate_identity || !(identity==gate_identity))) {
            s_fx_addition.clear();gate_identity=identity;have_gate_identity=1;
        }
    }
    Vec view,side,up;
    PSVECSubtract(&pG->Cam.param.at,&pG->Cam.param.pos,&view);
    PSVECCrossProduct(&view,&pG->Cam.up,&side);
    up=pG->Cam.up;
    if ((view.x==0.0f&&view.y==0.0f&&view.z==0.0f) || (side.x==0.0f&&side.y==0.0f&&side.z==0.0f) ||
        (up.x==0.0f&&up.y==0.0f&&up.z==0.0f)) { enabled=0; issues|=0x1000; }
    ps2fx::HazeCamera camera;
    if(enabled) {
        PSVECNormalize(&view,&view); PSVECNormalize(&side,&side); PSVECNormalize(&up,&up);
        camera.position.x=pG->Cam.param.pos.x; camera.position.y=pG->Cam.param.pos.y; camera.position.z=pG->Cam.param.pos.z;
        camera.view.x=view.x; camera.view.y=view.y; camera.view.z=view.z;
        camera.side.x=side.x; camera.side.y=side.y; camera.side.z=side.z;
        camera.up.x=up.x; camera.up.y=up.y; camera.up.z=up.z;
    }
    s_fx_addition.sample(enabled!=0,clock,first_steps,moving!=0,slow!=0,*recipe,camera,
        (pG->Status_flg[1]&0x02000000)!=0);
    issues|=s_fx_addition.issues;
    if(enabled) {
        EspTexWk* tw=&g_pEspSys->Esp_tex_tbl[0x1f];
        if(tw->Owner==0xd2 || !tw->pTpl || tw->pTpl->numDescriptors!=1 || !tw->pAnm ||
            tw->pAnm->Cx || tw->pAnm->Cy || tw->pAnm->Width!=128 || tw->pAnm->Height!=128 || tw->pAnm->Frames!=1) {
            issues|=0x2000;
        } else {
            const TEXDescriptor* td=TEXGet(tw->pTpl,0);
            const TEXHeader* th=td->textureHeader;
            Re4dcEffectSprite sprite;unsigned count=0;
            sprite.image.pixels=th->data; sprite.image.palette=NULL;
            sprite.image.width=th->width; sprite.image.height=th->height; sprite.image.format=th->format;
            sprite.image.palette_format=0xffffffffU; sprite.image.palette_bytes=0;
            if(td->CLUTHeader) {
                sprite.image.palette=td->CLUTHeader->data; sprite.image.palette_format=td->CLUTHeader->format;
                sprite.image.palette_bytes=td->CLUTHeader->numEntries*2;
            }
            f32 viewport[6]; GXGetViewportv(viewport);
            const Mtx44& projection=pG->Cam.ProjMat;
            const f32 near_d=projection[2][3]/(projection[2][2]-1.0f), far_d=projection[2][3]/projection[2][2];
            if(viewport[2]<=0.0f || viewport[3]<=0.0f || near_d<=0.0f || far_d<=near_d) issues|=0x4000;
#if defined(RE4DC_HAZE_SPRITE_CUT)
            else for(unsigned n=0;n<0U;++n) {   // HAZE_SPRITE_CUT: the addition is sampled as before, no quad is submitted
#else
            else for(unsigned n=0;n<ps2fx::HazeAddition::Count;++n) {
#endif
                const ps2fx::HazeParticle& particle=s_fx_addition.particles[n];
                Vec point={particle.position.x,particle.position.y,particle.position.z}, center;
                PSMTXMultVec(pG->Cam.v_mat,&point,&center);
                center.z+=1.0f; // EspCommonTrans billboard has local z=1.
                const f32 depth=-center.z;
                if(depth<near_d || depth>far_d) continue;
                f32 alpha=s_fx_addition.alpha(*recipe,depth);
                u32 r=recipe->r,g=recipe->g,b=recipe->b,a=alpha>0.0f ? (u32)alpha : 0;
                if(EffIsSetFinalCol()) {
                    GXColor final; EffGetFinalCol(&final);
                    r=r*final.r>>8; g=g*final.g>>8; b=b*final.b>>8; a=a*final.a>>8;
                }
                if(!a) continue;
                const f32 co=cosf(particle.angle),si=sinf(particle.angle),size=particle.size*s_fx_addition.size_mul;
                static const f32 x[4]={-0.5f,0.5f,0.5f,-0.5f},y[4]={0.5f,0.5f,-0.5f,-0.5f};
                static const f32 u[4]={0,1,1,0},v[4]={0,0,1,1};
                for(unsigned i=0;i<4;++i) {
                    const f32 vx=center.x+(co*x[i]-si*y[i])*size,vy=center.y+(si*x[i]+co*y[i])*size;
                    const f32 px=(projection[0][0]*vx+projection[0][2]*center.z)/depth;
                    const f32 py=(projection[1][1]*vy+projection[1][2]*center.z)/depth;
                    sprite.x[i]=(viewport[2]*0.5f*px+viewport[0]+viewport[2]*0.5f)*640.0f/viewport[2];
                    sprite.y[i]=(-viewport[3]*0.5f*py+viewport[1]+viewport[3]*0.5f)*480.0f/viewport[3];
                    sprite.z[i]=1.0f/depth;
                    sprite.u[i]=tw->mtx[0][0]*u[i]+tw->mtx[0][1]*v[i]+tw->mtx[0][3];
                    sprite.v[i]=tw->mtx[1][0]*u[i]+tw->mtx[1][1]*v[i]+tw->mtx[1][3];
                }
                sprite.color=(a<<24)|(r<<16)|(g<<8)|b; sprite.src=4; sprite.dst=5; sprite.screen=0; sprite.pad=0;
#if RE4DC_TA_BIN_DIAG
                sprite.pad|=2;
#endif
#if defined(RE4DC_FX_LEVEL)
                if(re4dc_fx_level) {   // FX_LEVEL: the same dial as the room effects (no budget: 10 particles)
                    if(!FxLevelKeep(n)) continue;
                    FxLevelScale(&sprite,kFxLevel[re4dc_fx_level].size,kFxLevel[re4dc_fx_level].alpha);
                }
#endif
                s_stage1_sprites[count++]=sprite;
            }
            if(!(issues&0x4000)){
                unsigned submitted=0;
                if(re4dc_effect_stage1_batch(s_stage1_sprites,count,5,&submitted))draws=submitted;
                else issues|=0x8000;
            }
        }
    }
    // Counts mean source-equivalent private particles, then submitted visible quads.
    // They are not a claim about PS2 RNG identity or hardware timing.
    if((G_ROOM_ID==0x118 || G_ROOM_ID==0x11c) && (!reported || last_issues!=issues || last_active!=enabled)) {
        re4dc_log("PS2FXADD f=%u r=%03x active=%d particles=%u age=%u submitted=%d issues=%x\n",
            (unsigned)pG->Frame_cnt,(unsigned)G_ROOM_ID,enabled,enabled?10U:0U,s_fx_addition.age,draws,issues);
        reported=1;last_issues=issues;last_active=enabled;
    }
}
#endif
#if RE4DC_PS2_FX_ADDITIONS
// r117's three puzzle trails survive in PS2 with different texture, size,
// colour and Type0 mode. Identify their GC source groups without calling
// CommonMove, Esp0a_Trans, an allocator or RNG on a source or scratch effect.
struct Ps2fxPuzzleGroup { ps2fx::TrailEvidence evidence; cEsp* anchor; };
static Ps2fxPuzzleGroup s_puzzle[3];
static u32 s_puzzle_frame;
static u8* s_puzzle_pool;
static unsigned s_puzzle_active;
#if defined(RE4DC_R117_FX_FALLBACK)
// A refused, complete colour group may use its exact GC copies for this image.
// Reuse the replacement's identity/frame/pool; retain no extra source pointers.
static unsigned s_puzzle_failed, s_puzzle_generation;
#endif
static const f32 kPuzzleX[3]={0.0f,13.888923645019531f,0.0f};
static const f32 kPuzzleY[3]={-280.0f,-279.1667175292969f,-248.0f};
class cPs2fxEsp0a : public cEsp { public: u8 type,base_alpha; };
static int Ps2fxPuzzleColour(const cEsp* e)
{
    if(e->info.owner!=1 || e->info.Core_kind!=2 || e->m_Tex_id!=0xff || e->m_Parts_no!=0 ||
       e->m_Release_time!=0xff || e->m_Ang.x!=0.0f || e->m_Ang.y!=0.0f || e->m_Ang.z!=0.0f || e->m_Size_base_x!=470.0f || e->m_Size_base_y!=470.0f ||
       e->m_Col_start_a!=130 || e->m_Del_far!=200 || e->m_Del_near!=50 || e->m_Blend_type!=1 ||
       !e->parent || e->parent==pEffParentWorld || !e->m_pMod || e->m_Guid_pMod!=e->m_pMod->serial) return -1;
    if(e->m_Col_start_r==50 && !e->m_Col_start_g && !e->m_Col_start_b) return 0;
    if(!e->m_Col_start_r && e->m_Col_start_g==50 && !e->m_Col_start_b) return 1;
    if(!e->m_Col_start_r && !e->m_Col_start_g && e->m_Col_start_b==50) return 2;
    return -1;
}
static ps2fx::TrailIdentity Ps2fxPuzzleIdentity(const cEsp* e,unsigned color)
{
    ps2fx::TrailIdentity value;
    value.key.call=e->info.Call_no;value.key.core=e->info.Core_pEm;value.key.recipe=(u16)color;
    value.key.flags=e->info.Core_flg;value.key.source_count=color==1?50:1;value.key.target_count=0;
    value.key.owner=e->info.owner;value.key.kind=e->info.Core_kind;
    value.parent=(u32)e->parent;value.model=(u32)e->m_pMod;value.serial=e->m_Guid_pMod;
    return value;
}
#if defined(RE4DC_R117_FX_FALLBACK)
static int Ps2fxPuzzleSourceMatches(const cEsp* e,unsigned colors)
{
    if(!pG || G_ROOM_ID!=0x117 || !(re4dc_ps2fx&PS2FX_STREAK) || !colors ||
       s_puzzle_frame!=(u32)pG->Frame_cnt || !g_pEspSys || s_puzzle_pool!=g_pEspSys->pEspBuf || e->m_Id!=0) return 0;
    const int color=Ps2fxPuzzleColour(e);
    if(color<0 || !(colors&(1U<<color)) ||
       !(Ps2fxPuzzleIdentity(e,color)==s_puzzle[color].evidence.identity)) return 0;
    return e->m_Tool_flg==(color==1?0x8000U:0x8400U) && e->m_Life_max==(color==1?0:1) &&
           e->m_Speed.x==0.0f && e->m_Speed.y==0.0f && e->m_Speed.z==0.0f && e->m_Size_plus==0.0f;
}
static int Ps2fxPuzzleFallback(const cEsp* e)
{
    // Successful replacement remains authoritative, including empty/cull-only
    // batches. Unrelated owner-1/0xff sprites receive no exemption.
    if(!s_puzzle_generation || !Ps2fxPuzzleSourceMatches(e,s_puzzle_failed&~s_puzzle_active)) return 0;
    unsigned generation=0,cells,bytes,stale,refused;
    return re4dc_room4_state(&generation,&cells,&bytes,&stale,&refused) && generation==s_puzzle_generation;
}
#endif
static int Ps2fxPuzzleSuppress(cEsp* e)
{
#if defined(RE4DC_R117_FX_FALLBACK)
    return Ps2fxPuzzleSourceMatches(e,s_puzzle_active);
#else
    if(G_ROOM_ID!=0x117 || !(re4dc_ps2fx&PS2FX_STREAK) || !s_puzzle_active ||
       s_puzzle_frame!=(u32)pG->Frame_cnt || !g_pEspSys || s_puzzle_pool!=g_pEspSys->pEspBuf || e->m_Id!=0) return 0;
    const int color=Ps2fxPuzzleColour(e);
    if(color<0 || !(s_puzzle_active&(1U<<color)) ||
       !(Ps2fxPuzzleIdentity(e,color)==s_puzzle[color].evidence.identity)) return 0;
    // Type1's transient copies retain tool 0x8400/life1; green's static copies
    // retain tool 0x8000/life0. Matching starts/parent/call isolate these sources.
    return e->m_Tool_flg==(color==1?0x8000U:0x8400U) && e->m_Life_max==(color==1?0:1) &&
           e->m_Speed.x==0.0f && e->m_Speed.y==0.0f && e->m_Speed.z==0.0f && e->m_Size_plus==0.0f;
#endif
}
extern "C" int ESP_IsActive(cEsp*);
static int Ps2fxPuzzleVisible(cEsp* e)
{
    if(!ESP_IsActive(e) || !(e->m_pMod->be_flag&2) ||
       ((e->info.Core_flg&0x400) && (pG->Status_flg[1]&0x04000000)) ||
       ((pG->Status_flg[1]&2) && !(e->info.Core_flg&0x8000))) return 0;
    return 1;
}
static void Ps2fxPuzzleDraw()
{
    static unsigned last_active,last_issues;static int reported;
    s_puzzle_active=0;s_puzzle_frame=(u32)pG->Frame_cnt;
    s_puzzle_pool=g_pEspSys?g_pEspSys->pEspBuf:NULL;
#if defined(RE4DC_R117_FX_FALLBACK)
    s_puzzle_failed=0;
#endif
    if(G_ROOM_ID!=0x117 || !(re4dc_ps2fx&PS2FX_STREAK)) { reported=0;return; }
    unsigned issues=0,submitted=0,candidates=0;
    for(unsigned c=0;c<3;++c) { s_puzzle[c].evidence.clear(c==1?50:1);s_puzzle[c].anchor=NULL; }
    if(!g_pEspSys || !s_puzzle_pool || g_pEspSys->nEsp>2048) issues|=1;
    else for(unsigned slot=0;slot<g_pEspSys->nEsp;++slot) {
        cEsp* e=(cEsp*)(s_puzzle_pool+slot*0x150);
        if(!(e->m_Be_flg&1) || (e->m_Id!=0 && e->m_Id!=0x0a)) continue;
        const int color=Ps2fxPuzzleColour(e);
        if(color<0 || e->m_Pos.x!=kPuzzleX[color] || e->m_Pos.y!=kPuzzleY[color]) continue;
        unsigned rank=0;
        if(color==1) {
            if(e->m_Id!=0 || e->m_Tool_flg!=0x8000 || e->m_Life_max || e->m_Size_plus!=0.0f ||
               e->m_Speed.x!=0.0f || e->m_Speed.y!=0.0f || e->m_Speed.z!=0.0f ||
               e->m_Pos.z>0.0f || e->m_Pos.z<-12250.0f) continue;
            rank=(unsigned)(-e->m_Pos.z/250.0f);
            if(e->m_Pos.z!=-250.0f*rank) continue;
        } else {
            if(e->m_Id!=0x0a || e->m_Tool_flg!=0x8400 || e->m_Life_max || e->m_Pos.z!=0.0f ||
               e->m_Size_mul!=1.0f || e->m_Speed.x!=0.0f || e->m_Speed.y!=0.0f || e->m_Speed.z!=-250.0f) continue;
            const cPs2fxEsp0a* a=static_cast<cPs2fxEsp0a*>(e);
            if(a->type!=1 || a->base_alpha!=130) continue;
        }
        s_puzzle[color].evidence.add(rank,Ps2fxPuzzleIdentity(e,color));
        if(rank==0) s_puzzle[color].anchor=e;
    }
    EspTexWk* tw=g_pEspSys ? &g_pEspSys->Esp_tex_tbl[0x13] : NULL;
    if(!tw || tw->Owner==0xd2 || !tw->pTpl || tw->pTpl->numDescriptors!=1 || !tw->pAnm ||
       tw->pAnm->Cx || tw->pAnm->Cy || tw->pAnm->Width!=96 || tw->pAnm->Height!=96 || tw->pAnm->Frames!=1) issues|=2;
    f32 viewport[6];GXGetViewportv(viewport);
    const Mtx44& projection=pG->Cam.ProjMat;
    const f32 near_d=projection[2][3]/(projection[2][2]-1.0f),far_d=projection[2][3]/projection[2][2];
    if(viewport[2]<=0.0f || viewport[3]<=0.0f || near_d<=0.0f || far_d<=near_d) issues|=4;
    ps2fx::TrailPoint points[50];const unsigned point_count=ps2fx::puzzle_trail(points);
    for(unsigned color=0;color<3;++color) {
        Ps2fxPuzzleGroup& group=s_puzzle[color];
        if(group.evidence.count && !group.evidence.complete()) issues|=8U<<color;
        if((issues&7) || !group.evidence.complete() || !group.anchor) continue;
        cEsp* source=group.anchor;
        if(!Ps2fxPuzzleVisible(source)) {
            unsigned draws=0;
            if(re4dc_effect_stage1_batch(s_stage1_sprites,0,1,&draws))s_puzzle_active|=1U<<color;
            else issues|=0x100U<<color;
            continue;
        }
        const TEXDescriptor* td=TEXGet(tw->pTpl,0);const TEXHeader* th=td->textureHeader;
        Re4dcEffectSprite sprite;unsigned count=0;
        sprite.image.pixels=th->data;sprite.image.palette=NULL;
        sprite.image.width=th->width;sprite.image.height=th->height;sprite.image.format=th->format;
        sprite.image.palette_format=0xffffffffU;sprite.image.palette_bytes=0;
        if(td->CLUTHeader) {
            sprite.image.palette=td->CLUTHeader->data;sprite.image.palette_format=td->CLUTHeader->format;
            sprite.image.palette_bytes=td->CLUTHeader->numEntries*2;
        }
        Mtx transform;PSMTXConcat(pG->Cam.v_mat,source->parent->mat,transform);
        for(unsigned n=0;n<point_count;++n) {
            ++candidates;
            Vec local={kPuzzleX[color],kPuzzleY[color],points[n].z},center;
            PSMTXMultVec(transform,&local,&center);
            const f32 fade_depth=-center.z;
            center.z+=1.0f;const f32 depth=-center.z;
            if(depth<near_d || depth>far_d) continue;
            u32 r=color==0?110:50,g=color==1?110:50,b=color==2?110:50,a=(u8)points[n].alpha;
            if(!(source->m_Flg&4) && EffIsSetFinalCol()) {
                GXColor final;EffGetFinalCol(&final);
                r=r*final.r>>8;g=g*final.g>>8;b=b*final.b>>8;a=a*final.a>>8;
            }
            if(fade_depth<2000.0f) {
                const f32 near=color==0?1000.0f:500.0f;
                const f32 rate=1.0f-(2000.0f-fade_depth)/(2000.0f-near);
                a=rate>0.0f?(u8)(a*rate):0;
            }
            if(!a) continue;
            r=r*4>255?255:r*4;g=g*4>255?255:g*4;b=b*4>255?255:b*4;a=a*4>255?255:a*4;
            const f32 half=700.0f*points[n].size_mul;
            static const f32 x[4]={-1,1,1,-1},y[4]={1,1,-1,-1};
            static const f32 u[4]={0,1,1,0},v[4]={0,0,1,1};
            for(unsigned i=0;i<4;++i) {
                const f32 vx=center.x+x[i]*half,vy=center.y+y[i]*half;
                const f32 px=(projection[0][0]*vx+projection[0][2]*center.z)/depth;
                const f32 py=(projection[1][1]*vy+projection[1][2]*center.z)/depth;
                sprite.x[i]=(viewport[2]*0.5f*px+viewport[0]+viewport[2]*0.5f)*640.0f/viewport[2];
                sprite.y[i]=(-viewport[3]*0.5f*py+viewport[1]+viewport[3]*0.5f)*480.0f/viewport[3];
                sprite.z[i]=1.0f/depth;sprite.u[i]=tw->mtx[0][0]*u[i]+tw->mtx[0][1]*v[i]+tw->mtx[0][3];
                sprite.v[i]=tw->mtx[1][0]*u[i]+tw->mtx[1][1]*v[i]+tw->mtx[1][3];
            }
            sprite.color=(a<<24)|(r<<16)|(g<<8)|b;sprite.src=4;sprite.dst=1;sprite.screen=0;sprite.pad=0;
            s_stage1_sprites[count++]=sprite;
        }
        unsigned draws=0;
        if(re4dc_effect_stage1_batch(s_stage1_sprites,count,1,&draws)){
            s_puzzle_active|=1U<<color;submitted+=draws;
#if defined(RE4DC_R117_FX_FALLBACK)
        }else{
            if(count)s_puzzle_failed|=1U<<color;
            issues|=0x100U<<color;
        }
#else
        }else issues|=0x100U<<color;
#endif
    }
    if(!reported || last_active!=s_puzzle_active || last_issues!=issues) {
        re4dc_log("PS2FXPUZZLE f=%u active=%x source=%u/%u/%u points=%u candidates=%u submitted=%u issues=%x\n",
            s_puzzle_frame,s_puzzle_active,s_puzzle[0].evidence.count,s_puzzle[1].evidence.count,s_puzzle[2].evidence.count,
            point_count,candidates,submitted,issues);
        reported=1;last_active=s_puzzle_active;last_issues=issues;
    }
}
// Trans prepares image k after Render(k-1). The next Render consumes it while
// Frame_cnt is still k, after native begin/coarse drawing and before effect OTs.
struct Ps2fxStage1Pending {
    u8* pool;EspgenWork* generators;u32 frame;u16 room;
    unsigned slots,generation,generator_count;bool pending;
};
static Ps2fxStage1Pending s_stage1_pending={};
static void Ps2fxStage1Prepare()
{
    s_puzzle_active=0;s_stage1_pending={};
#if defined(RE4DC_R117_FX_FALLBACK)
    s_puzzle_failed=0;s_puzzle_generation=0;
#endif
    if(!pG || !g_pEspSys || !g_pEspSys->pEspBuf || g_pEspSys->nEsp>2048 ||
       nEspgen>512 || (nEspgen && !EspgenArray) ||
       (G_ROOM_ID!=0x117 && G_ROOM_ID!=0x118 && G_ROOM_ID!=0x11c))return;
    unsigned generation=0,cells,bytes,stale,refused;
    if(!re4dc_room4_state(&generation,&cells,&bytes,&stale,&refused) || !generation)return;
    s_stage1_pending={g_pEspSys->pEspBuf,EspgenArray,(u32)pG->Frame_cnt,(u16)G_ROOM_ID,
        g_pEspSys->nEsp,generation,nEspgen,true};
}
// Called only at native begin, before source Render submission. Revalidate
// the pending source image without consuming it or advancing any private clock.
extern "C" unsigned re4dc_ps2_fx_stage1_image(Re4dcUiImage* image)
{
    if(!image)return 0;
    *image={};
    const Ps2fxStage1Pending& ticket=s_stage1_pending;
    if(!ticket.pending || !pG || !g_pEspSys ||
       ticket.frame!=(u32)pG->Frame_cnt || ticket.room!=G_ROOM_ID ||
       ticket.pool!=g_pEspSys->pEspBuf || ticket.slots!=g_pEspSys->nEsp ||
       ticket.generators!=EspgenArray || ticket.generator_count!=nEspgen)return 0;
    unsigned generation=0,cells,bytes,stale,refused;
    if(!re4dc_room4_state(&generation,&cells,&bytes,&stale,&refused) || generation!=ticket.generation)return 0;
    unsigned tex,width;
    if(ticket.room==0x117 && (re4dc_ps2fx&PS2FX_STREAK)){tex=0x13;width=96;}
    else if((ticket.room==0x118 || ticket.room==0x11c) && (re4dc_ps2fx&PS2FX_HAZE)){tex=0x1f;width=128;}
    else return 0;
    const EspTexWk* tw=&g_pEspSys->Esp_tex_tbl[tex];
    if(tw->Owner==0xd2 || !tw->pTpl || tw->pTpl->numDescriptors!=1 || !tw->pAnm ||
       tw->pAnm->Cx || tw->pAnm->Cy || tw->pAnm->Width!=width || tw->pAnm->Height!=width || tw->pAnm->Frames!=1)return 0;
    const TEXDescriptor* td=TEXGet(tw->pTpl,0);
    if(!td || !td->textureHeader || td->CLUTHeader)return 0;
    const TEXHeader* th=td->textureHeader;
    if(!th->data || th->width!=width || th->height!=width || th->format!=1)return 0;
    *image={th->data,NULL,width,width,1,0xffffffffU,0};
    return tex;
}
extern "C" void re4dc_ps2_fx_stage1_render(int coarse,int skipping)
{
    const Ps2fxStage1Pending ticket=s_stage1_pending;s_stage1_pending={};
    // Consume first. A duplicate call cannot replay or revoke a committed colour.
    if(!ticket.pending || !coarse || skipping || !pG || !g_pEspSys ||
       ticket.frame!=(u32)pG->Frame_cnt || ticket.room!=G_ROOM_ID ||
       ticket.pool!=g_pEspSys->pEspBuf || ticket.slots!=g_pEspSys->nEsp ||
       ticket.generators!=EspgenArray || ticket.generator_count!=nEspgen)return;
    unsigned generation=0,cells,bytes,stale,refused;
    if(!re4dc_room4_state(&generation,&cells,&bytes,&stale,&refused) || generation!=ticket.generation)return;
#if defined(RE4DC_R117_FX_FALLBACK)
    s_puzzle_generation=generation;
#endif
    Ps2fxAdditionsDraw();Ps2fxPuzzleDraw();
}
#endif
#if defined(RE4DC_COARSE_FX_SPRITES) && RE4DC_COARSE_FX_SPRITES
// COARSE_FX_SPRITES (effects30.mk): a live effect the EspCommonTrans sprite path draws (esp.cpp queues
// it in a drawn coarse image's logic-only pass; coarse.cpp then draws no marker for it). Esp0b (the room
// fires' particles) is EspCommonTrans after an optional camera jitter; esp.cpp queues its common body.
extern EspTransFunc EspTransTbl[0xFF];
#endif
#if defined(RE4DC_RAIN_PS2_SHEET_REF) && RE4DC_RAIN_PS2_SHEET_REF
// RAIN_PS2_SHEET_REF (effects30.mk; a REFERENCE arm for look and cost only, never in a recipe; lane rain17 2026-10-18):
// the night lake's rain drawn the PS2's way. PS2 r11b.dat EFF#7 SST set 3 rec 67 (r11a set 5): one Esp08 screen sheet,
// tex 0xC5, 700x540 of the 512x448 screen centred, rgb 180, a 100, 3x1 tiles scrolled (-0.003, -0.090) a frame. The
// game's (GameCube) set 3 instances are reused as the anchor: its first sheet (550 base) draws with the PS2 recipe, its
// second (1385 base) is not drawn (the PS2 merged the two). Each wrapped tile is one native effect sprite (<= 8).
// The scroll comes from pG->Frame_cnt (read only). Log "ps2 sheet:" every 120 drawn images.
static u32 s_ps2_sheet_frames;
static f32 Ps2SheetFrac(f32 v)
{
    return v - (f32) (int) v + (v < (f32) (int) v ? 1.0f : 0.0f);
}
static u32 s_ps2_sheet_seen, s_ps2_sheet_notpl, s_ps2_sheet_fade, s_ps2_sheet_tiles, s_ps2_sheet_calls;
extern "C" int re4dc_ps2_rain_sheet(cEsp* esp)
{
    if (esp->m_Id == 0x08 && (s_ps2_sheet_seen++ & 0x3F) == 0) {
        re4dc_log("ps2 sheet seen: frame=%u n=%u owner=%x tex=%x parts=%d base=%d col_a=%d start_a=%u calls=%u notpl=%u fade=%u tiles=%u\n",
                  (unsigned) pG->Frame_cnt, (unsigned) s_ps2_sheet_seen, (unsigned) esp->info.owner,
                  (unsigned) esp->m_Tex_id, (int) (s8) esp->m_Parts_no, (int) esp->m_Size_base_x, (int) esp->m_Col_a,
                  (unsigned) esp->m_Col_start_a, (unsigned) s_ps2_sheet_calls, (unsigned) s_ps2_sheet_notpl,
                  (unsigned) s_ps2_sheet_fade, (unsigned) s_ps2_sheet_tiles);
    }
    if (!(G_ROOM_ID == 0x11A || G_ROOM_ID == 0x11B) || esp->m_Id != 0x08 || esp->info.owner != 0xD0 ||
        esp->m_Tex_id != 0xC5 || !((s8) esp->m_Parts_no >= -8 && (s8) esp->m_Parts_no <= -3)) {
        return 0;
    }
    if (esp->m_Size_base_x > 1000.0f) {
        return 1;
    }
    EspTexWk* tw = &g_pEspSys->Esp_tex_tbl[0xC5];
    ++s_ps2_sheet_calls;
    if (!tw->pTpl || tw->pTpl->numDescriptors == 0) {
        ++s_ps2_sheet_notpl;
        return 1;
    }
    const TEXDescriptor* td = TEXGet(tw->pTpl, 0);
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
    const f32 fade = esp->m_Col_start_a ? esp->m_Col_a / (f32) esp->m_Col_start_a : 1.0f;
    const f32 fa = 100.0f * (fade > 1.0f ? 1.0f : fade);
    if (fa < 1.0f) {
        ++s_ps2_sheet_fade;
        return 1;
    }
    s.color = ((u32) fa << 24) | 0xB4B4B4U;
    s.src = esp->xA5 & 7;
    s.dst = esp->xA6 & 7;
    s.screen = 1;
    s.pad = 0;
    const f32 X0 = (256.0f - 350.0f) * 1.25f, W = 700.0f * 1.25f;
    const f32 Y0 = (224.0f - 270.0f) * (480.0f / 448.0f), H = 540.0f * (480.0f / 448.0f);
    const f32 tileW = W / 3.0f, tileH = H;
    const f32 f = (f32) (pG->Frame_cnt % 100000U);
    const f32 su = Ps2SheetFrac(-0.003f * f), sv = Ps2SheetFrac(-0.090f * f);
    // texture coordinate u runs su .. su + 3 across, v runs sv .. sv + 1 down; cut at the integer wraps
    f32 ucut[6], vcut[3];
    u32 nu = 0, nv = 0;
    ucut[nu++] = su;
    for (int k = 1; k <= 3; ++k) {
        ucut[nu++] = (f32) k;
    }
    ucut[nu++] = su + 3.0f;
    vcut[nv++] = sv;
    vcut[nv++] = 1.0f;
    vcut[nv++] = sv + 1.0f;
    u32 drawn = 0;
    for (u32 j = 0; j + 1 < nv; ++j) {
        const f32 va = vcut[j], vb = vcut[j + 1];
        if (vb - va < 1e-4f) {
            continue;
        }
        const f32 vfl = (f32) (int) va;
        const f32 ya = Y0 + (va - sv) * tileH, yb = Y0 + (vb - sv) * tileH;
        for (u32 i = 0; i + 1 < nu; ++i) {
            const f32 ua = ucut[i], ub = ucut[i + 1];
            if (ub - ua < 1e-4f) {
                continue;
            }
            const f32 ufl = (f32) (int) ua;
            const f32 xa = X0 + (ua - su) * tileW, xb = X0 + (ub - su) * tileW;
            s.x[0] = xa; s.y[0] = ya; s.u[0] = ua - ufl; s.v[0] = va - vfl;
            s.x[1] = xb; s.y[1] = ya; s.u[1] = ub - ufl; s.v[1] = va - vfl;
            s.x[2] = xb; s.y[2] = yb; s.u[2] = ub - ufl; s.v[2] = vb - vfl;
            s.x[3] = xa; s.y[3] = yb; s.u[3] = ua - ufl; s.v[3] = vb - vfl;
            for (int c = 0; c < 4; ++c) {
                s.z[c] = 1.0f;
            }
            drawn += re4dc_effect_sprite(&s) ? 1 : 0;
        }
    }
    s_ps2_sheet_tiles += drawn;
    if (++s_ps2_sheet_frames % 120 == 1) {
        re4dc_log("ps2 sheet: frame=%u room=%x tiles=%u argb=%08x su=%d sv=%d\n", (unsigned) pG->Frame_cnt,
                  (unsigned) G_ROOM_ID, (unsigned) drawn, (unsigned) s.color, (int) (su * 1000), (int) (sv * 1000));
    }
    return 1;
}
#endif
#if defined(RE4DC_COARSE_FX_SPRITES) && RE4DC_COARSE_FX_SPRITES
#if defined(RE4DC_PVR_RTT) && RE4DC_PVR_RTT
extern "C" int re4dc_rtt_core_wanted(u32 core_flg);
#endif
extern "C" int re4dc_esp_sprite_class(cEsp* esp)
{
#if defined(RE4DC_ESP1B_GRID03) && RE4DC_ESP1B_GRID03
    if(Esp1bGridClass03(esp))return EspTransTbl[esp->m_Id]==EspCommonTrans;
#endif
#if defined(RE4DC_FX_STRIP21) && RE4DC_FX_STRIP21
    if(re4dc_esp_strip21_eligible(esp))return 1;
#endif

#if defined(RE4DC_PVR_RTT) && RE4DC_PVR_RTT
    // PVR_RTT (pvr_rtt.mk): a render target's common sprites while a model shows that target (the coarse pass then
    // queues them in the target's OT, where EspSpriteEligible admits them into the capture).
    if (esp->m_Tool_flg & 0x10000) {
        return EspTransTbl[esp->m_Id] == EspCommonTrans && re4dc_rtt_core_wanted(esp->info.Core_flg) &&
               !((esp->m_Tool_flg & 0x4000) || (esp->m_Flg & 0x10) || esp->xA4 != 1);
    }
#endif
#if defined(RE4DC_RAIN_PS2_SHEET_REF) && RE4DC_RAIN_PS2_SHEET_REF
    if (esp->m_Id == 0x08 && esp->info.owner == 0xD0 && esp->m_Tex_id == 0xC5 &&
        (G_ROOM_ID == 0x11A || G_ROOM_ID == 0x11B)) return 1;
#endif
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
#if RE4DC_PS2_FX_POPULATION
    Ps2fxPopulationBuild();
#endif
#if RE4DC_PS2_FX_COMMON_HAZE
    Ps2fxCommonHazePrepare();
#endif
#if RE4DC_PS2_FX_ADDITIONS
    Ps2fxStage1Prepare();
#endif
}
#endif
extern "C" int re4dc_esp_coarse_sprite_visible(cEsp* esp)
{
#if defined(RE4DC_FX_MIST_PS2) && RE4DC_FX_MIST_PS2
    if (esp->m_Id == 0x48 && re4dc_esp48_is_dormant(esp)) {
        return 0;   // FX_MIST_PS2: a dormant GC-only mist sheet (never drawn: HAZE_SPRITE_CUT)
    }
#endif
#if defined(RE4DC_ESP_CUT_EARLY) && RE4DC_ESP_CUT_EARLY && defined(RE4DC_HAZE_SPRITE_CUT)
    // ESP_CUT_EARLY=1 (logiclod20.mk; render only, exact): a sprite HAZE_SPRITE_CUT declines in EspSpriteEmit (every
    // mist sheet, and a camera haze sprite without a PS2 recipe row) is not queued at all, so EspCommonTrans no longer
    // builds its channels, matrix and corners for nothing. PS2 recipe haze sprites still go through (HW_FOG_HAZE reads
    // them before their cut). The cut note is counted here as there.
    if (esp->m_Id == 0x48 || (esp->m_Id == 0x15 && !Ps2fxHazeFor(esp))) {
        HazeCutNote(esp);
        return 0;
    }
#endif
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
#if RE4DC_PS2_FX_POPULATION
    const int population_selected = Ps2fxPopulationSelected(esp);
    if (!population_selected && !(esp->m_Flg & 1) && esp->m_Col_a < 1.0f) {
#else
    if (!(esp->m_Flg & 1) && esp->m_Col_a < 1.0f) {
#endif
        return 0;   // faded out: ChannelSet's alpha is (u8) m_Col_a here (before the final-colour scale), so 0
    }
#if defined(RE4DC_ESP1B_GRID03) && RE4DC_ESP1B_GRID03
    // The live control offsets can extend beyond the ordinary sprite radius.
    // Existing policy/fade cuts above remain; native cells clip the full grid.
    if(Esp1bGridClass03(esp))return 1;
#endif
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
#if RE4DC_PS2_FX_STAGE1
    const Ps2fxStatic* fixed=Ps2fxStaticFor(esp);
    const f32 bx=fixed ? fixed->ps_x : esp->m_Size_base_x, by=fixed ? fixed->ps_y : esp->m_Size_base_y;
#else
    const f32 bx = esp->m_Size_base_x, by = esp->m_Size_base_y;
#endif
#if RE4DC_EFFECT_PS2_HAZE
    const Ps2fxHaze* hz = Ps2fxHazeFor(esp);
#if RE4DC_PS2_FX_POPULATION
    if (population_selected) {
        const f32 ratio = hz->range / hz->gc_range;
        v.x *= ratio; v.y *= ratio; v.z *= ratio;
    }
#endif
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
#if RE4DC_EFFECT_SPRITES && defined(RE4DC_EFFECT_HAZE_LEAN) && (RE4DC_EFFECT_HAZE_LEAN & 1)
extern "C" void re4dc_log(const char* fmt, ...);
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

    ESPCT(0);
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
#if defined(RE4DC_ESP1B_GRID03) && RE4DC_ESP1B_GRID03
    if (!EspSpriteEligible(esp) && !Esp1bGridClass03(esp)) {
#else
    if (!EspSpriteEligible(esp)) {
#endif
        s_proj_type = -1;
        s_tex_no = -1;
        return;
    }
#endif
#if defined(RE4DC_ESP_CUT_EARLY) && RE4DC_ESP_CUT_EARLY && defined(RE4DC_HAZE_SPRITE_CUT)
    // ESP_CUT_EARLY (see re4dc_esp_coarse_sprite_visible): a sprite EspSpriteEmit would decline under HAZE_SPRITE_CUT
    // skips the body. The cached projection / texture are forgotten, as for an ineligible sprite above.
    if (esp->m_Id == 0x48 || (esp->m_Id == 0x15 && !Ps2fxHazeFor(esp))) {
        HazeCutNote(esp);
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
#if RE4DC_EFFECT_SPRITES && defined(RE4DC_EFFECT_HAZE_LEAN) && (RE4DC_EFFECT_HAZE_LEAN & 1)
    // EFFECT_HAZE_LEAN bit 1 (STUDY2 M1): the GameCube mist sheets (id 0x48: tex f6 / cb / d0 / f3 / 33) of r100, r101
    // and r103, which the PS2 release deleted from all three rooms (it keeps r100's small 0x48 / d9 sparks), are not
    // drawn while the PS2 haze look is on. Render only: the generators and the sheets themselves still run.
    if (RE4DC_HZ(1) && (re4dc_ps2fx & PS2FX_HAZE) && esp->info.owner == 0xD0 && esp->m_Id == 0x48 &&
        (G_ROOM_ID == 0x100 || G_ROOM_ID == 0x101 || G_ROOM_ID == 0x103) &&
        (esp->m_Tex_id == 0xf6 || esp->m_Tex_id == 0xcb || esp->m_Tex_id == 0xd0 || esp->m_Tex_id == 0xf3 ||
         esp->m_Tex_id == 0x33)) {
        static u32 s_seen[3];
        const u32 ri = G_ROOM_ID == 0x100 ? 0 : G_ROOM_ID == 0x101 ? 1 : 2;
        const u32 bit = esp->m_Tex_id == 0xf6 ? 1 : esp->m_Tex_id == 0xcb ? 2 : esp->m_Tex_id == 0xd0 ? 4 : esp->m_Tex_id == 0xf3 ? 8 : 16;
        if (!(s_seen[ri] & bit)) {
            s_seen[ri] |= bit;
            re4dc_log("haze lean: r%03x mist sheet tex %02x not drawn\n", (unsigned) G_ROOM_ID, (unsigned) esp->m_Tex_id);
        }
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
    ESPCT(1);
#if RE4DC_PS2_FX_POPULATION
    if (!esp->ChannelSet() && !Ps2fxPopulationSelected(esp)) {
#else
    if (!esp->ChannelSet()) {
#endif
        return;
    }
    ESPCT(2);
#if defined(RE4DC_ESP_ESSENTIAL_EARLY)
    // ChannelSet and the projection/animation cache updates already happened:
    // their state remains available to the next OT callback as before.
    if (re4dc_fx_essential && FxEssentialSetupCut(esp, ESP_PARTS_SCREEN(esp))) return;
#endif
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
        RE4DC_RENDER_MTXConcat(m, esp->m_Mat, esp->m_Mat);
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
        RE4DC_RENDER_MTXRotRad(m, 'z', esp->m_Ang.z);
        RE4DC_RENDER_MTXConcat(m, esp->m_Mat, esp->m_Mat);
        RE4DC_RENDER_MTXConcat(pG->Cam.v_mat, esp->parent->mat, m2);
        RE4DC_RENDER_MTXMultVec(m2, &esp->m_Pos, &p);
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
        RE4DC_RENDER_MTXConcat(m, esp->m_Mat, esp->m_Mat);
        if (esp->m_Tool_flg & 0x80000) {
            Mtx m3;
            RE4DC_RENDER_MTXRotRad(m3, 'y', EspGetCameraPan() * (3.1415927f / 180.0f));
            RE4DC_RENDER_MTXConcat(m3, esp->m_Mat, esp->m_Mat);
        }
        esp->m_Mat[0][3] += esp->m_Pos.x;
        esp->m_Mat[1][3] += esp->m_Pos.y;
        esp->m_Mat[2][3] += esp->m_Pos.z;
        RE4DC_RENDER_MTXConcat(esp->parent->mat, esp->m_Mat, esp->m_Mat);
        RE4DC_RENDER_MTXConcat(pG->Cam.v_mat, esp->m_Mat, esp->m_Mat);
    }
#if defined(RE4DC_ESP1B_GRID03) && RE4DC_ESP1B_GRID03
    if(esp->m_Id==0x1b && (esp->m_Flg&0x10)){
        Esp1b_SpTrans(esp);return; // never replay a partially published grid
    }
#endif
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
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    re4dc::dfa26::hit(re4dc::dfa26::EffectLegacy);
#endif
    RE4DC_RENDER_MTXInverse(esp->m_Mat, inv);
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
#if defined(RE4DC_FX_MIST_PS2) && RE4DC_FX_MIST_PS2
    if (e.p->m_Id == 0x48 && (e.p->m_Be_flg & 1) && Ps2fxMistGcOnly(e.p)) {
        // FX_MIST_PS2 (hwfog.mk): a GC-only mist sheet. Every seed draw above was made and the sheet keeps its pool
        // slot (the pool, its scan order and every other effect stay as before), but it is dormant: no move, no anim,
        // not offered to the sprite pass (esp48.cpp).
        re4dc_esp48_dormant(e.p);
    }
#endif
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
#if defined(RE4DC_ESP1B_GRID03) && RE4DC_ESP1B_GRID03
#include "esp1b_grid03.inc"
#endif

// Draws esp1b's deformed sprite: the unit quad with the three corner offsets of Esp1bSpWork,
// subdivided div x div, as textured quads with an up normal.
void Esp1b_SpTrans(cEsp* esp)
{
#if defined(RE4DC_ESP1B_GRID03) && RE4DC_ESP1B_GRID03
    // EFFECT_LEAN has no rendering GX fallback. Preserve the void callback;
    // typed callers distinguish an unpublished refusal from consumed output.
    (void)Esp1bGridDraw03(esp);return;
#endif
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

#if defined(RE4DC_FX_CORE_TEX_PREP) && RE4DC_FX_CORE_TEX_PREP
#include <cstdint>
#include <cstring>
#include "fx_core_source_prep.inc"
#endif
#if defined(RE4DC_FX_LEVEL_TOGGLE) && RE4DC_FX_LEVEL_TOGGLE && defined(RE4DC_FX_LEVEL)
// FX_LEVEL_TOGGLE (effects30.mk, test builds): pad.cpp Y + START steps re4dc_fx_level 0 -> 1 -> 2 -> 0; native_static.cpp
// shows the level for 3 s through re4dc_look_osd_text. Render only, as the dial itself.
extern "C" unsigned re4dc_vi_retrace_count(void);
extern "C" void re4dc_log(const char* fmt, ...);
static u32 s_fx_level_osd_until;
static const char* const kFxLevelText[3] = {"FX level 0: PS2 effects as-is", "FX level 1: medium effects",
                                            "FX level 2: low effects"};
#if defined(RE4DC_FX_TRIM) && RE4DC_FX_TRIM
extern "C" u8 re4dc_fx_essential;
#endif
extern "C" void re4dc_fx_level_toggle(void)
{
#if defined(RE4DC_FX_TRIM) && RE4DC_FX_TRIM
    // FX_TRIM: 0 -> 1 -> 2 -> Essential (room dial 0 + the Essential filter) -> 0
    if (re4dc_fx_essential) {
        re4dc_fx_essential = 0;
        re4dc_fx_level_set(0);
    } else if (re4dc_fx_level >= 2) {
        re4dc_fx_essential = 1;
        re4dc_fx_level_set(0);
    } else {
        re4dc_fx_level_cycle();
    }
    s_fx_level_osd_until = re4dc_vi_retrace_count() + 180U;
    re4dc_log("fx level: %u essential=%u frame=%u\n", (unsigned) re4dc_fx_level, (unsigned) re4dc_fx_essential,
              pG ? (unsigned) pG->Frame_cnt : 0u);
    return;
#endif
    re4dc_fx_level_cycle();
    s_fx_level_osd_until = re4dc_vi_retrace_count() + 180U;
    re4dc_log("fx level: %u frame=%u\n", (unsigned) re4dc_fx_level, pG ? (unsigned) pG->Frame_cnt : 0u);
}
extern "C" const char* re4dc_fx_level_osd_text(void)
{
#if defined(RE4DC_FX_TRIM) && RE4DC_FX_TRIM
    if (re4dc_fx_essential && (int) (s_fx_level_osd_until - re4dc_vi_retrace_count()) > 0) return "FX level 3: essential only";
#endif
    return (int) (s_fx_level_osd_until - re4dc_vi_retrace_count()) > 0 ? kFxLevelText[re4dc_fx_level % 3] : 0;
}
#endif
