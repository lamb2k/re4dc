#pragma once
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
int re4dc_effect_line(const Re4dcEffectLine*);
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
