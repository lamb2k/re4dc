// LETTERBOX_CLIP (Phase 2 B5, default 0; this file is built only with the knob on): the gameplay letterbox bars cost
// no fill underneath them. The source draws the bars as two ID-system quads (class 0x30, texture 0x0a/0, colour
// ff000000, blend 0: y 0..59 and 420..480 of 640x480) late in the frame, so the whole scene - mist sprites, fog planes,
// scenery - is rasterised under them first.
//  (c) While both bars were drawn fully opaque in the previous frame, two black opaque polygons at the nearest depth
//      open the frame's opaque list. The ISP then rejects every depth-tested pixel behind them (world-space effect
//      sprites are GEQUAL: all r100 / r101 mist), so the translucent texture + blend work under the bars is skipped.
//      The source bar quads are still drawn on top (black over black: the picture is unchanged).
//  (b) 640x480 render (15 tile rows) only: when both bars are opaque this frame, tile row 0 (y 0..31, wholly under the top
//      bar) gets no translucent / punch-through / modifier lists in the region array of the bank being filled: those
//      tiles render the opaque list only (the bar). Written at scene close, before pvr_scene_finish starts the render
//      that reads it (the TA never reads the region array): no register write, nothing touched mid render. =2 also
//      clips tile row 14 (y 448..479); subtitles and HUD drawn there would vanish, so =2 is a measurement arm only.
// A 240-line render (RES_MODES Fast levels) has no tile row wholly under a bar: (c) only. Bar fades (alpha < 255), the
// sub screen, movies without the bars, title, menus and the crash screen draw no opaque bar quads: nothing applies.
// (c) uses the previous frame's bars (the opaque list opens before the UI runs): the frame after the bars vanish
// without a fade still shows them once.
#include <kos.h>
#include <dc/pvr.h>
extern "C" {
#include "pvr_internal.h"  // KOS internals (C linkage): pvr_state
}
#include "re4dc_screen.h"

extern "C" void re4dc_log(const char* fmt, ...);

namespace {
float cur_top, cur_bot, prev_top, prev_bot;  // the top bar's lower edge, the bottom bar's upper edge (640x480 units)
unsigned cur_mask, prev_mask;                 // bit 0 top bar seen, bit 1 bottom bar
unsigned clipped[2];                          // tile rows (bit 0 row 0, bit 1 row 14) cleared in each bank's region array
uint32_t clipped_tm[2];                       // ... of that tile matrix (res_mode.cpp re-cuts both on a mode change)
unsigned frames, op_frames, clip_frames;
bool op_sent;                                 // this frame's opaque bars are in
constexpr unsigned kEmptyLists = (1U << 1) | (1U << 2) | (1U << 3) | (1U << 4);  // OP modifier, TR, TR modifier, PT

// One tile row of bank b: list pointers of kEmptyLists to "empty" (clear) or as KOS / res_mode lay them out (restore).
void row_lists(volatile pvr_ta_buffers_t* buf, unsigned row, bool clear)
{
    const unsigned tw = unsigned(pvr_state.tw), th = unsigned(pvr_state.th);
    uint32_t* vr = reinterpret_cast<uint32_t*>(PVR_RAM_BASE) + buf->tile_matrix / 4U + 6U;
    for (unsigned x = 0; x < tw; ++x) {
        uint32_t* t = vr + 6U * (x * th + row);  // KOS order: x outer, y inner
        const unsigned tn = tw * row + x;
        for (unsigned l = 0; l < PVR_OPB_COUNT; ++l) {
            if (!(kEmptyLists >> l & 1U)) continue;
            t[1 + l] = (!clear && (pvr_state.lists_enabled & BIT(l))) ? buf->opb_addresses[l] + pvr_state.opb_size[l] * tn
                                                                       : 0x80000000U;
        }
    }
}
}  // namespace

// ui_bridge.cpp re4dc_draw_id_quad, before re4dc_ui_submit: xy are the quad's corners in 640x480 units.
extern "C" void re4dc_lbx_note(unsigned cls, unsigned tex_id, unsigned tex_no, unsigned argb, const float* xy)
{
    if (cls != 0x30 || tex_id != 0x0a || tex_no != 0 || argb != 0xff000000U) return;
    float x0 = xy[0], x1 = xy[0], y0 = xy[1], y1 = xy[1];
    for (unsigned i = 1; i < 4; ++i) {
        x0 = xy[2 * i] < x0 ? xy[2 * i] : x0;
        x1 = xy[2 * i] > x1 ? xy[2 * i] : x1;
        y0 = xy[2 * i + 1] < y0 ? xy[2 * i + 1] : y0;
        y1 = xy[2 * i + 1] > y1 ? xy[2 * i + 1] : y1;
    }
    if (x0 > 1.0f || x1 < 639.0f) return;
    if (y0 <= 1.0f && y1 < 240.0f) { cur_mask |= 1U; cur_top = y1; }
    else if (y1 >= 479.0f && y0 > 240.0f) { cur_mask |= 2U; cur_bot = y0; }
}

// native_ui.cpp stream_open (the frame's first list just begun) and stream_select (a list switch): once per frame, when
// the opaque list is current. send(...) is native_ui's stream_send.
extern "C" void re4dc_lbx_open(int list, void (*send)(const void*, unsigned))
{
    if (list != PVR_LIST_OP_POLY || prev_mask != 3U || op_sent) return;
    op_sent = true;
    struct alignas(32) Packet { pvr_poly_hdr_t h; pvr_vertex_t v[4]; } p;
    pvr_poly_cxt_t c;
    pvr_poly_cxt_col(&c, PVR_LIST_OP_POLY);
    c.gen.culling = PVR_CULLING_NONE;
    c.depth.comparison = PVR_DEPTHCMP_GEQUAL;
    c.depth.write = PVR_DEPTHWRITE_ENABLE;
    pvr_poly_compile(&p.h, &c);
    const float ys[2][2] = {{0.0f, prev_top}, {prev_bot, 480.0f}};
    for (unsigned b = 0; b < 2; ++b) {
        const float xs[4] = {0, 0, 640, 640}, yy[4] = {ys[b][1], ys[b][0], ys[b][1], ys[b][0]};
        for (unsigned k = 0; k < 4; ++k) {
            pvr_vertex_t& v = p.v[k];
            v.flags = k == 3 ? PVR_CMD_VERTEX_EOL : PVR_CMD_VERTEX;
            v.x = RE4DC_UI_X(xs[k]);
            v.y = RE4DC_UI_Y(yy[k]);
            v.z = 2.0f;  // nearer than any scene depth (1/w, w >= the near plane) and the UI's 1.0
            v.u = v.v = 0;
            v.argb = 0xff000000U;
            v.oargb = 0;
        }
        send(&p, sizeof(p));
    }
    ++op_frames;
}

#if defined(RE4DC_LETTERBOX_CULL) && RE4DC_LETTERBOX_CULL
// LETTERBOX_CULL (Makefile): the rows (640x480 units) that (c)'s black polygons cover in the frame being built: exactly
// re4dc_lbx_open's condition and edges (the previous frame's opaque bars). 0: no bars this frame, cull the full frame.
extern "C" int re4dc_lbx_cull_rows(float* top, float* bot)
{
    if (prev_mask != 3U) return 0;
    *top = prev_top;
    *bot = prev_bot;
    return 1;
}
#endif
#if defined(RE4DC_LBX_CENSUS) && RE4DC_LBX_CENSUS
extern "C" unsigned re4dc_lbx_mask(void) { return prev_mask; }  // native_ui.cpp tabin::lbx (tahash.mk)
#endif
#if defined(RE4DC_MCHECK_SAFE) && RE4DC_MCHECK_SAFE
extern "C" {
unsigned re4dc_lbx_rows_last;  // the tile rows cleared for the scene being closed (MCHECK_SAFE log)
}
#endif
// native_ui.cpp stream_close, before pvr_list_finish / pvr_scene_finish: the bank being filled is not rendering.
extern "C" void re4dc_lbx_close(void)
{
    unsigned want = 0;
    if (cur_mask == 3U && RE4DC_SCREEN_W == 640 && RE4DC_SCREEN_H == 480 && pvr_state.tw == 20 && pvr_state.th == 15) {
        if (cur_top >= 32.0f) want |= 1U;
#if RE4DC_LETTERBOX_CLIP >= 2
        if (cur_bot <= 448.0f) want |= 2U;
#endif
    }
    const unsigned b = unsigned(pvr_state.ta_target) & 1U;
    volatile pvr_ta_buffers_t* buf = pvr_state.ta_buffers + b;
    if (clipped_tm[b] != buf->tile_matrix) {  // laid out afresh (boot, a render mode change): nothing cleared
        clipped_tm[b] = buf->tile_matrix;
        clipped[b] = 0;
    }
    if (clipped[b] != want) {
        if ((clipped[b] ^ want) & 1U) row_lists(buf, 0, want & 1U);
        if ((clipped[b] ^ want) & 2U) row_lists(buf, 14, want & 2U);
        clipped[b] = want;
    }
    if (want) ++clip_frames;
#if defined(RE4DC_MCHECK_SAFE) && RE4DC_MCHECK_SAFE
    re4dc_lbx_rows_last = want;  // native_ui.cpp safe_audit_scene (mcheck.mk, test builds only)
#endif
    op_sent = false;
    prev_mask = cur_mask;
    prev_top = cur_top;
    prev_bot = cur_bot;
    cur_mask = 0;
    if ((++frames % 600) == 0)
        re4dc_log("letterbox clip: frames=%u opaque_bars=%u row_clip=%u bars=%u top=%d bottom=%d\n", frames, op_frames,
                  clip_frames, prev_mask, int(prev_top), int(prev_bot));
}
