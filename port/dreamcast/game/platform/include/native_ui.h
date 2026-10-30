#pragma once
#if defined(RE4DC_EFFECT_MASK12) && RE4DC_EFFECT_MASK12
#include "native_draw_result.hpp"
#include "effect_mask12.hpp"
#endif
// Narrow source-ID adapter, not a GX command interpreter.
struct Re4dcUiImage {
    const void* pixels;
    const void* palette;
    unsigned width, height, format, palette_format, palette_bytes;
};
struct Re4dcUiQuad {
    Re4dcUiImage image;
    float xy[8], uv[8];
    unsigned color, blend, masked;
};
#if defined(RE4DC_FX_CORE_TEX_PREP) && RE4DC_FX_CORE_TEX_PREP
#include <cstdint>
// Stack-local proof of one accepted potential draw. No source pointer survives
// the synchronous prepare/recheck; 0x0a descendants and 0x0e copies may still cull.
struct Re4dcFxCoreDemand {
    Re4dcUiImage image;
    const void* game; const void* system; const void* pool; const void* dummy;
    const void* node; const void* buckets; const void* tpl; const void* animation;
    const void* descriptors; const void* header;
    std::uintptr_t prim, cursor;
    unsigned native_frame, source_frame, room_generation, pool_generation;
    unsigned pool_count, prim_bytes, prim_buffer, table, table_max;
    unsigned slot, callback, owner, call_no, accepted;
    unsigned char source[0x150];
};
extern "C" {
// 1: current accepted potential draw; 0: no demand/context; negative: proof refusal.
int re4dc_fx_core_source(unsigned native_frame, Re4dcFxCoreDemand*);
int re4dc_fx_core_current(unsigned native_frame, const Re4dcFxCoreDemand*);
}
#endif
// Source subscreen tile, copied at its existing ordering-table callback.
// Positions are view-space in GX triangle-strip order; colour is source RGBA.
struct Re4dcSubscreenQuad {
    float positions[4][3], projection[7], viewport[6];
    unsigned color, blend, depth_test;
};
// EFFECT_SPRITES (effects30.mk): one projected effect sprite. Corners A,B,C,D in PVR
// sprite order (A-B-C clockwise, D opposite B), screen x/y in 640x480 and z = 1/w.
struct Re4dcEffectSprite {
    Re4dcUiImage image;
    float x[4], y[4], z[4], u[4], v[4];
    unsigned color;                      // ARGB, material colour after TEV scale
    unsigned char src, dst, screen, pad; // PVR blend factors; screen: depth always, no fog
};
// Esp19's two final source endpoints, projected and depth-clipped by its owner.
// One pixel GX line, with the source endpoint colours and blend/depth state.
// RAIN_DC (filter06.cpp): one vertical rain streak, x / y0 (tail) / y1 (head) in 640x480, z = 1/depth, width in
// pixels, tail and head ARGB (gouraud).
struct Re4dcRainStreak {
    float x, y0, y1, z, w;
    unsigned tail, head;
};
extern "C" unsigned re4dc_rain_dc_streaks(const Re4dcRainStreak*, unsigned);
#if defined(RE4DC_FX_STRIP21) && RE4DC_FX_STRIP21
// Source GX quad order, live view-space corners and explicit authored UVs.
// Same deferred FIFO/frame/fence owner as effects; no source pointer retained.
struct Re4dcEffectQuad {
    Re4dcUiImage image;
    float positions[4][3],u[4],v[4],projection[7],viewport[6];
    unsigned color;
    unsigned char src,dst,wrap_s,wrap_t;
};
extern "C" int re4dc_effect_quad(const Re4dcEffectQuad*);
#if defined(RE4DC_FLASHLIGHT_POOL) && RE4DC_FLASHLIGHT_POOL
// FLASHLIGHT_POOL: an additive Gouraud fan in view space, centre colour fading to black at the ring
// (native_flashlight_pool.inc).
struct Re4dcEffectFan {
    float centre[3],ring[16][3],projection[7],viewport[6];
    unsigned n,centre_argb;
};
extern "C" int re4dc_effect_fan(const Re4dcEffectFan*);
#endif
#if defined(RE4DC_CLOTH_NATIVE) && RE4DC_CLOTH_NATIVE
// CLOTH_NATIVE (cloth.cpp clothTrans, esp4e cloth sheets): a cols x rows grid of live view-space points (row major,
// row 0 = the hanging edge) drawn as one PVR strip per row pair, UV = (col/(cols-1), row/(rows-1)) as the source.
struct Re4dcEffectMesh21 {
    Re4dcUiImage image;
    const float* positions;
    unsigned cols,rows;
    float v_top,v_step;   // source t of row 0 and per row (the caller may pass a band of a larger grid)
    float projection[7],viewport[6];
    unsigned color;
    unsigned char src,dst,wrap_s,wrap_t;
};
extern "C" int re4dc_effect_mesh21(const Re4dcEffectMesh21*);
#endif
#endif
struct Re4dcEffectLine {
    float x[2], y[2], z[2];
    unsigned color[2];
    unsigned char src, dst, depth_test, blend_mode;
};
// NATIVE_MES=1 (mes.cpp draw()): one message glyph, the texel window u..u+cw, v..v+ch of a
// GameCube CI4 font sheet (8x8 texel tiles, as on the disc) with its TLUT (GX format 0 IA8,
// 1 RGB565, 2 RGB5A3; big-endian entries), drawn over x0,y0..x1,y1 (640x480) with argb
// modulating the texel, alpha blended (the source SRCALPHA / INVSRCALPHA, TEV modulate).
struct Re4dcUiGlyph {
    const void* sheet;
    const void* clut;
    unsigned sheet_w, sheet_h, format, clut_format, clut_entries;
    int u, v, cw, ch;
    float x0, y0, x1, y1;
    unsigned argb;
};
extern "C" {
int re4dc_effect_sprite(const Re4dcEffectSprite*);
#if defined(RE4DC_EFFECT_MASK12) && RE4DC_EFFECT_MASK12
// Separate material argument; unswitched callers keep the exact sprite ABI.
re4dc::NativeDrawResult re4dc_effect_masked_sprite12_result(const Re4dcEffectSprite*,unsigned material);
#endif
#if defined(RE4DC_PS2_FX_COMMON_HAZE) && RE4DC_PS2_FX_COMMON_HAZE
// Bounded same-texture replacement; returns success even when all quads cull.
// Modifies private scratch coordinates for render resolution. Never uploads.
int re4dc_effect_haze_batch(Re4dcEffectSprite*, unsigned count, unsigned* submitted);
#endif
#if defined(RE4DC_PS2_FX_ADDITIONS) && RE4DC_PS2_FX_ADDITIONS
// One resident-only atomic batch: src4/dst5 up to10, or src4/dst1 up to50.
// Coordinates are private scratch and may be scaled even after a refusal.
int re4dc_effect_stage1_batch(Re4dcEffectSprite*, unsigned count, unsigned dst, unsigned* submitted);
// Read-only descriptor for this frame's qualified source core recipe. The
// native preparation phase validates its core identity before any upload.
// Does not consume the Render ticket or sample/mutate effect state.
unsigned re4dc_ps2_fx_stage1_image(Re4dcUiImage*);
#endif
int re4dc_effect_line(const Re4dcEffectLine*);
#if defined(RE4DC_WATER_PS2) && RE4DC_WATER_PS2
// WATER_PS2 (espgen45.cpp, lane water16): one PS2 water layer, a horizontal plane drawn as an eye-centred grid of
// textured translucent strips (native_ui.cpp, include/native_water_ps2.inc). image.pixels null: untextured.
struct Re4dcWaterLayer {
    Re4dcUiImage image;
    float mv[3][4];                       // plane local (x, 0, z) in mm -> view space
    float eye_x, eye_z, half_x, half_z;   // the eye over the plane and the plane's half extents (local mm)
    float u_per_mm, v_per_mm, u0, v0;     // texture repeats per mm and the scroll offset (repeats)
    float projection[7], viewport[6];     // GX's
    unsigned argb;
    unsigned char src, dst, pad[2];       // PVR blend factors
};
int re4dc_water_layer(const Re4dcWaterLayer*);
#endif
void re4dc_ui_glyph(const Re4dcUiGlyph*);
void re4dc_ui_glyph_fonts_changed();
void re4dc_ui_init();
void re4dc_ui_begin();
void re4dc_ui_present();
// Always called at source Render_swap, including a held picture.
void re4dc_ui_end_frame(int present);
void re4dc_ui_submit(const Re4dcUiQuad*);
int re4dc_subscreen_quad(const Re4dcSubscreenQuad*);
// Same source state; positions[0..1] are the line endpoints, width is GX sixth-pixels.
int re4dc_subscreen_line(const Re4dcSubscreenQuad*, unsigned width);
void re4dc_ui_invalidate_sources();
int re4dc_ui_bind_core(void*,unsigned);
int re4dc_ui_bind_option(void*,unsigned);
void re4dc_ui_unbind_option();
int re4dc_ui_bind_room(void*,unsigned);
void re4dc_ui_retire_room();
int re4dc_ui_bind_player(void*,unsigned);
int re4dc_ui_bind_weapon(void*,unsigned);
void re4dc_ui_unbind_player();
void re4dc_ui_unbind_weapon();
#if defined(RE4DC_ACTOR_PL08_PACK) && RE4DC_ACTOR_PL08_PACK
void re4dc_pl08_pack_player(unsigned file);  // coarse_actor_pl08_pack.inc: after every player archive bind
#endif
int re4dc_ui_bind_enemy(void*,unsigned);
void re4dc_ui_unbind_enemy(void*);
void* re4dc_ui_stage_alloc(unsigned bytes);
void re4dc_ui_stage_free(void* data);
int re4dc_ui_heap_free();
}
