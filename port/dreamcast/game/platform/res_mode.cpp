// res_mode.cpp -- RES_MODES (game30.mk; Phase 2 item C0, test builds) and RENDER_OPTION (Phase 2 C6, the player's
// "Rendering: Quality / Standard / Fast" setting): the render resolution and the FSAA scaler at run time. Modes
// (bit n of RES_MODES makes mode n available; RES_MODE is the boot mode):
//   0  640x480 (today; RENDER_OPTION "Quality")
//   1  640x240 rendered (RENDER_OPTION "Standard"): about half the pixel fill
//   2  1280x240 rendered into the FSAA scaler (horizontal halving on write-out): about today's fill, horizontal
//      edge anti-aliasing, vertical softness (PS2-like)
//   3  1280x480 into the FSAA scaler (about twice today's fill; needs the 600-tile allocation: see below)
//   4  320x240 rendered, each pixel shown twice across (video output pixel double; RENDER_OPTION "Fast"): about a
//      quarter of the pixel fill
// The display mode (KOS vid_set_mode 640x480, interlaced on a TV, progressive on VGA) never changes and both frame
// buffers stay 640x480. A 240-line picture is shown in one of two ways:
//   doubled (C0 builds, VGA, RENDER_DOUBLE=1): each frame-buffer line is read twice. TV (480i): both fields read the
//     same 240 lines (FB_R_SIZE modulus 1, odd-field address = even-field address); VGA (480p): FB_R_CTRL line
//     double (bit 1), FB_R_SIZE 240 lines.
//   alternating (RENDER_OPTION on a 480i TV): every frame renders 240 lines with a half-line vertical offset that
//     alternates per frame (odd frames sample half a render line lower: GXGetViewportv's jitter, the GameCube's own
//     GXSetViewportJitter idea) and is written into one parity (even or odd lines) of a frame buffer (write-out
//     start + one line for odd, write-out line stride two lines). The two 640x480 buffers are four half-buffers
//     (A even, A odd, B even, B odd). The display reads field 1 (even lines) from the newest even half and field 2
//     (odd lines) from the newest odd half (FB_R_SOF1 / FB_R_SOF2 may point into different buffers), and each
//     render writes the older half of its parity, which is never on screen. No copy, no extra VRAM; the other half
//     is at most one frame old. The PVR write-out filter cannot blend two renders: the TV's interlace blends them.
// VRAM: KOS allocates the TA object pointer blocks, tile matrices and both 640x480 frame buffers once at pvr_init,
// so the texture pool never moves. Per bank the region [opb, opb + opb_size x (1 + overflow)) is re-cut per mode:
// the mode's initial blocks (bytes per tile x tiles), then the rest as the overflow pool. A mode with more tiles
// than KOS allocated (mode 2: 320 > 300) keeps its tile matrix at the end of that region. Its extra region is paid
// for as TA_HEADROOM pays (one more overflow pool, the vertex buffer one pool smaller), so the texture pool is
// unchanged unless mode 3 is built (KOS then allocates 600 tiles: the pool shrinks by the extra blocks). RENDER_OPTION
// builds modes 0, 1 and 4 only (300 tiles at most): one memory layout for every level.
// Safe point: a mode change is requested (pad chord, setting) and applied at the start of a frame (re4dc_ui_begin)
// after the previous scene was presented, with no scene in the TA, no render running and none completed (KOS
// pvr_set_vbuf_doublebuf's precondition): the tile matrices, TA registers and SCALER_CFG are only written while the
// PVR is idle (issue 9 / issue 11: scaler or TA writes during a render hang the console). The picture on screen is
// held (display registers rewritten every vblank) until the new mode has a complete picture: one flip, or for the
// alternating modes both parities, rendered into the buffer the held picture does not use. The alternating write
// address is chosen right before each render starts (pvr_begin_queued_render, link-time wrap: KOS state only, before
// the render's own register writes), never during a render.
// RENDER_FSAA=1 (game30.mk; 2026-10-14; RES_MODES 9 = modes 0 and 3 since 10-15, LITE dropped): FSAA without the
// 240-line display. Mode 2 as built above shows 240 lines doubled on a 480i TV (FB_R_SIZE modulus 1, odd-field start =
// even-field start), so both fields scan the same rows and the interlace puts field 2 one scan line lower: every
// horizontal edge moves one line up and down 30 times a second (the flicker seen on a console, aa trial 98143f5b).
// Under RENDER_FSAA:
//   mode 2 "FSAA LITE": 1280x240 rendered, SCALER_CFG horizontal halving + vertical scale factor 512 (x2), so the tile
//     write-out itself writes 640x480 (FB_X/Y_CLIP are in written coordinates: rows 480..511 of the 8th tile row are
//     clipped) and the display is Quality's (480 lines, the odd field one line down). Fill as Quality. Whether the
//     scaler interpolates the doubled lines (stable) or repeats them (the old twitter) needs the console.
//   mode 3 "FSAA": 1280x480, horizontal halving, the vertical filter kept (scale factor as Quality: 1025 on a 480i
//     TV), Quality's display. Twice Quality's fill. KOS still allocates 300 tiles (no 600-tile allocation: the
//     texture pool does not shrink, s30); the 600-tile blocks come from kFsaaPools more overflow pools per bank,
//     taken from the top of the vertex buffer ONLY while mode 3 is applied (apply moves the bank's OPB start down and
//     shortens its vertex buffer; leaving mode 3 gives it back). Standard (mode 0) keeps KOS's test 11 layout byte for
//     byte: the vertex buffer stays 2,000,896 B per bank (VRAM-MAP-20261014: benchmark-r101 stores up to 1,756,744 B;
//     a boot-time cut of 230,400 B left 0.8% margin in every mode).
#if defined(RE4DC_RES_MODES) && RE4DC_RES_MODES
#include <kos.h>
#include <dc/pvr.h>
#include <dc/pvr/pvr_regs.h>
#include <dc/video.h>
#include <dc/vblank.h>
#include <arch/irq.h>
extern "C" {
#include "pvr_internal.h"  // KOS internals (C linkage): pvr_state, pvr_sync_reg_buffer
}
#include "re4dc_screen.h"

extern "C" void re4dc_log(const char* fmt, ...);
extern "C" unsigned re4dc_vi_retrace_count(void);

#ifndef RE4DC_RES_MODE
#define RE4DC_RES_MODE 0
#endif
#ifndef RE4DC_RES_ALTERNATE
#define RE4DC_RES_ALTERNATE 0
#endif
#ifndef RE4DC_RENDER_FSAA
#define RE4DC_RENDER_FSAA 0
#endif
static_assert((RE4DC_RES_MODES & ~31) == 0 && (RE4DC_RES_MODES >> RE4DC_RES_MODE & 1), "RES_MODES 1..31, RES_MODE in it");

extern "C" {
int re4dc_screen_w = 640, re4dc_screen_h = 480;
float re4dc_screen_wf = 640.0f, re4dc_screen_hf = 480.0f, re4dc_ui_sx = 1.0f, re4dc_ui_sy = 1.0f;
float re4dc_screen_half_wf = 320.0f, re4dc_screen_half_hf = 240.0f;
// Viewport top offset in render lines for the scene being built: -0.5 on odd alternating frames, else 0
// (gx_stub.cpp GXGetViewportv adds it, scaled to the viewport's units).
float re4dc_res_vjitter = 0.0f;
}

namespace {
constexpr unsigned kModeCount = 5;
struct Mode {
    unsigned short w, lines;
    unsigned char fsaa;
    const char* name;
};
#if RE4DC_RENDER_FSAA
const Mode kModes[kModeCount] = {{640, 480, 0, "R0 640x480"},
                                 {640, 240, 0, "R1 640x240"},
                                 {1280, 240, 1, "R2 FSAA LITE"},
                                 {1280, 480, 1, "R3 FSAA"},
                                 {320, 240, 0, "R4 320x240"}};
// RENDER_FSAA: mode 2 writes its 240 rendered lines as 480 (scaler vertical scale factor 1024 / 512 = 2).
constexpr unsigned kVupMode = 2, kVupFactor = 512;
// Extra KOS overflow pools per bank (300-tile pools, 48,000 B each with 40 words per tile) for mode 3's 600 tiles:
// region 9 x 48,000 = 432,000 B = 96,000 B initial blocks + 14.5 KB tile matrix + 3 overflow pools of 96,000 B.
constexpr unsigned kFsaaPools = 4;
unsigned out_lines(unsigned m) { return m == kVupMode ? 480U : kModes[m].lines; }
uint32_t vscale_keep = ~0U;  // the vertical scale factor before mode 2 (restored when leaving it)
uint32_t fsaa_extra;         // bytes per bank mode 3 borrows from the vertex buffer (kFsaaPools pools, 128-aligned)
uint32_t vsize_kos[2];       // KOS vertex buffer size per bank (the layout every non-FSAA mode keeps)
#else
const Mode kModes[kModeCount] = {{640, 480, 0, "R0 640x480"},
                                 {640, 240, 0, "R1 640x240"},
                                 {1280, 240, 1, "R2 640x240 FSAA"},
                                 {1280, 480, 1, "R3 640x480 FSAA"},
                                 {320, 240, 0, "R4 320x240"}};
#endif
constexpr unsigned kTileMatrixHeader = 0x48;  // KOS PVR_TILE_MATRIX_HEADER_SIZE
unsigned tiles_of(unsigned m) { return (kModes[m].w / 32U) * ((kModes[m].lines + 31U) / 32U); }
unsigned max_tiles()
{
    unsigned t = 0;
    for (unsigned m = 0; m < kModeCount; ++m)
        if ((RE4DC_RES_MODES >> m & 1) && tiles_of(m) > t) t = tiles_of(m);
    return t;
}
// Frame-buffer width of mode m (the FSAA modes write 640 wide after the scaler).
unsigned fb_w(unsigned m) { return kModes[m].fsaa ? 640U : kModes[m].w; }
struct Bank {
    uint32_t opb, region_end, tm_kos;
};
Bank banks[2];
unsigned kos_tiles, tile_bytes, cur = ~0U, applied;
volatile unsigned want = RE4DC_RES_MODE;
bool vga, interlaced, inited;
uint32_t boot_fb_size, boot_fb_cfg1, boot_video_cfg;
uint32_t fb_base[2];  // the two 640x480 frame buffers KOS allocated (VRAM offsets)
unsigned osd_until;
int vbl_handle = -1;
// A 240-line picture on 480i: byte offset added to the odd-field read address of the doubled display (both fields
// read the same lines, so 0). Kept for a possible half-line field alternation of the doubled display; not used.
volatile uint32_t field_offset_bytes = 0;

// ---- Display state -------------------------------------------------------------------------------------------
// What the display registers show. kind: 0 full 480 lines of one buffer, 1 one half doubled (or a 240-line buffer
// doubled), 2 alternating halves. Rewritten every vblank while `hold` or alternating, after KOS's flip.
struct Display {
    unsigned kind, width;     // width: 640 or 320 (pixel double)
    uint32_t sof1, sof2;      // field 1 / field 2 start (VRAM offsets); progressive reads sof1 only
};
volatile bool hold;            // the held picture stays until the new mode has a complete one
Display held, live;
volatile bool alt;             // the current mode alternates (RENDER_OPTION, 240 lines, 480i TV, not FSAA)
unsigned lb;                   // line bytes of the current mode's frame-buffer layout (width x 2)
// Alternating halves: disp[p] = buffer whose parity-p half is on screen; bank_parity[b] = parity of the scene built
// in TA bank b; next_parity toggles per scene; inflight = the half the running render writes.
volatile int disp[2] = {0, 0}, bank_parity[2] = {0, 1}, inflight_p = -1, inflight_buf = 0, seen_view;
int next_parity;
volatile unsigned fill_mask, fill_buf;  // entering an alternating mode: parities rendered into fill_buf so far
volatile int wait_view = -1;            // entering a non-alternating mode: the view before its first flip

uint32_t fb_size_of(unsigned kind, unsigned width)
{
    const uint32_t words = width * 2U / 4U;
    if (kind == 0) return boot_fb_size;
    if (kind == 1) return (words - 1U) | (239U << 10) | (1U << 20);
    // One line skipped between the lines of a field; 239 lines per field: the last line pair (rows 478 / 479) is not
    // shown. Row 479 is the last row of the first KOS buffer, and on Flycast it holds data that is not ours whenever no
    // full 480-line render overwrites it (it showed as a noise line in Standard; c6-fv stills).
    return (words - 1U) | (238U << 10) | ((words + 1U) << 20);
}
void write_display(const Display& d)
{
    PVR_SET(PVR_FB_SIZE, fb_size_of(d.kind, d.width));
    PVR_SET(PVR_FB_CFG_1, (vga && d.kind == 1) ? (boot_fb_cfg1 | 2U) : boot_fb_cfg1);
    PVR_SET(PVR_VIDEO_CFG, d.width == 320 ? (boot_video_cfg | 0x100U) : (boot_video_cfg & ~0x100U));
    PVR_SET(PVR_FB_ADDR, d.sof1);
    if (interlaced && !vga) PVR_SET(PVR_FB_IL_ADDR, d.sof2 + (d.kind == 1 ? field_offset_bytes : 0U));
}
int buf_of(uint32_t addr) { return (addr & (PVR_RAM_SIZE - 1)) >= fb_base[1] ? 1 : 0; }
Display alt_display(unsigned width)
{
    const unsigned l = width * 2U;
    return Display{2, width, fb_base[disp[0]], fb_base[disp[1]] + l};
}
void live_kind_display();
// A flip happened when KOS's view target changed: the render that was in flight is now on screen.
// 240-line modes: the clipped last line (both parities when alternating) of both buffers, kept black (apply and
// again when an alternating fill completes). 32-bit stores only (no byte writes to VRAM).
unsigned last_line;  // bytes of that line pair (0: a 480-line mode)
void clear_last()
{
    if (!last_line) return;
    for (int k = 0; k < 2; ++k) {
        volatile uint32_t* p = reinterpret_cast<volatile uint32_t*>(PVR_RAM_BASE + fb_base[k] + 239U * last_line);
        for (unsigned i = 0; i < last_line / 4U; ++i) p[i] = 0;
    }
}

void note_flip()
{
    const int v = pvr_state.view_target;
    if (v == seen_view) return;
    seen_view = v;
    if (wait_view >= 0 && v != wait_view) {  // a non-alternating mode's first picture: show it
        wait_view = -1;
        hold = false;
        live_kind_display();
    }
    if (inflight_p < 0) return;
    const int p = inflight_p;
    inflight_p = -1;
    if (fill_mask != 3U) {
        fill_mask |= 1U << p;
        if (fill_mask == 3U) {  // both parities of fill_buf rendered: show them, alternate from here
            clear_last();
            disp[0] = disp[1] = int(fill_buf);
            hold = false;
        }
        return;
    }
    disp[p] = inflight_buf;
}
// After KOS's vblank handler (registered later, TAILQ order): it flipped (pvr_sync_view) in this same vblank.
void vblank(uint32_t, void*)
{
    note_flip();
    if (hold) write_display(held);
    else if (alt) write_display(live = alt_display(kModes[cur].w));
    else if (live.kind == 1 && interlaced && !vga) PVR_SET(PVR_FB_IL_ADDR, PVR_GET(PVR_FB_ADDR) + field_offset_bytes);
}
// KOS pvr_init_tile_matrix: the zero header and the initial tile; the tiles follow (apply).
void write_matrix_head(uint32_t tm)
{
    uint32_t* vr = reinterpret_cast<uint32_t*>(PVR_RAM_BASE) + (tm - kTileMatrixHeader) / 4U;
    for (unsigned i = 0; i < kTileMatrixHeader / 4U; ++i) *vr++ = 0;
    vr[0] = 0x10000000U;
    for (unsigned i = 1; i < 6; ++i) vr[i] = 0x80000000U;
}
// The picture on screen now, as one buffer: the display while a new mode gets its first complete picture.
Display current_single(int* buf)
{
#if RE4DC_RENDER_FSAA
    if (cur == ~0U || (!alt && out_lines(cur) == 480)) {
#else
    if (cur == ~0U || (!alt && kModes[cur].lines == 480)) {
#endif
        const int b = buf_of(PVR_GET(PVR_FB_ADDR));
        *buf = b;
        return Display{0, 640, fb_base[b], fb_base[b] + 640U * 2U};
    }
    if (alt) {  // the newest half, doubled (the other buffer is then free)
        const int p = next_parity ^ 1;  // parity of the last scene; its half or the other one is newest
        const int b = disp[p];
        *buf = b;
        const unsigned l = kModes[cur].w * 2U;
        return Display{1, kModes[cur].w, fb_base[b] + unsigned(p) * l, fb_base[b] + unsigned(p) * l};
    }
    const int b = buf_of(PVR_GET(PVR_FB_ADDR));
    *buf = b;
    return Display{1, fb_w(cur), fb_base[b], fb_base[b]};
}
// The PVR is idle (caller): re-cut both banks for mode m.
void apply(unsigned m)
{
    const Mode& M = kModes[m];
    const unsigned tw = M.w / 32U, th = (M.lines + 31U) / 32U, T = tw * th;
    for (unsigned b = 0; b < 2; ++b) {
        volatile pvr_ta_buffers_t* buf = pvr_state.ta_buffers + b;
        const uint32_t* old = reinterpret_cast<const uint32_t*>(PVR_RAM_BASE) + buf->tile_matrix / 4U;
        const bool presort = (old[6] >> 29) & 1U;  // the bank's first tile (WORLD_AUTOSORT switches it per scene)
        const uint32_t tm_bytes = 4U * (6U + 6U * T);
        uint32_t tm = banks[b].tm_kos, end = banks[b].region_end;
#if RE4DC_RENDER_FSAA
        // Mode 3 borrows fsaa_extra from the top of the vertex buffer (it sits right below the OPB region); any other
        // mode returns it. The PVR is idle and the bank holds no scene still to render (caller).
        const uint32_t extra = T > kos_tiles ? fsaa_extra : 0U;
        const uint32_t opb0 = banks[b].opb - extra;
        buf->opb = opb0;
        buf->vertex_size = vsize_kos[b] - extra;
#define RE4DC_RES_OPB0 opb0
#else
#define RE4DC_RES_OPB0 banks[b].opb  // knob off: the code as before (byte-identical image)
#endif
        if (T > kos_tiles) {
            tm = (banks[b].region_end - tm_bytes) & ~127U;
            end = (tm - kTileMatrixHeader) & ~127U;
        }
        const uint32_t initial = tile_bytes * T;
        const int overflow = int((end - RE4DC_RES_OPB0) / initial) - 1;
        buf->opb_size = initial;
        buf->opb_overflow_count = overflow;
        uint32_t accum = 0;
        for (unsigned j = 0; j < PVR_OPB_COUNT; ++j) {
            buf->opb_addresses[j] = RE4DC_RES_OPB0 + accum;
            accum += pvr_state.opb_size[j] * T;
        }
        buf->tile_matrix = tm;
        buf->tile_matrix_size = tm_bytes;
        write_matrix_head(tm);
        uint32_t* vr = reinterpret_cast<uint32_t*>(PVR_RAM_BASE) + tm / 4U + 6U;
        for (unsigned x = 0; x < tw; ++x)
            for (unsigned y = 0; y < th; ++y) {
                const unsigned tn = tw * y + x;
                vr[0] = (y << 8) | (x << 2) | (unsigned(presort) << 29);
                for (unsigned l = 0; l < PVR_OPB_COUNT; ++l)
                    vr[1 + l] = (pvr_state.lists_enabled & BIT(l)) ? buf->opb_addresses[l] + pvr_state.opb_size[l] * tn
                                                                    : 0x80000000U;
                vr += 6;
            }
        vr[-6] |= BIT(31);
        re4dc_log("res: bank %u tiles %u (%ux%u) opb %06x initial %u overflow %d (pool %u B) tile matrix %06x end %06x\n", b, T,
                  tw, th, unsigned(RE4DC_RES_OPB0), unsigned(initial), overflow, unsigned(initial) * unsigned(overflow),
                  unsigned(tm), unsigned(end));
    }
    // The picture to hold until this mode has a complete one (none at boot).
    int held_buf = 0;
    const bool boot = cur == ~0U;
    if (!boot) {
        held = current_single(&held_buf);
        write_display(held);  // at once: a fill render may start before the next vblank
    }
    const bool to_alt = RE4DC_RES_ALTERNATE && M.lines == 240 && !M.fsaa && interlaced && !vga;
    const unsigned w_write = fb_w(m);
    lb = w_write * 2U;
    pvr_state.tw = int(tw);
    pvr_state.th = int(th);
    pvr_state.tsize_const = ((th - 1U) << 16) | (tw - 1U);
    pvr_state.w = int(to_alt ? 2U * w_write : w_write);  // KOS write-out line stride (RENDER_MODULO) = w x 2 bytes
    pvr_state.h = int(th * 32U);
    pvr_state.fsaa = M.fsaa;
    pvr_state.pclip_x = ((w_write - 1U) << 16) | (pvr_state.pclip_x & 0xffffU);
    // A 240-line mode's last line drew noise on the Flycast stills (c6-f-* runs: rows 478/479 of Standard, line 239
    // of Fast; Quality's row 479 is the black letterbox): it is clipped off and kept black (cleared below).
#if RE4DC_RENDER_FSAA
    // Clip in written (after scaler) coordinates: mode 2 writes 480 lines.
    const unsigned ol = out_lines(m);
    pvr_state.pclip_bottom = ol == 480 ? 479U : M.lines - 2U;
    pvr_state.pclip_y = (pvr_state.pclip_bottom << 16) | pvr_state.pclip_top;
    uint32_t scaler = (PVR_GET(PVR_SCALER_CFG) & ~PVR_SCALER_CFG_FSAA) | (M.fsaa ? PVR_SCALER_CFG_FSAA : 0U);
    const uint32_t vnow = scaler & PVR_SCALER_CFG_VSCALE_FACTOR;
    uint32_t vset = vnow;
    if (m == kVupMode) {
        if (vscale_keep == ~0U) vscale_keep = vnow;
        vset = kVupFactor;
    } else if (vscale_keep != ~0U) {
        vset = vscale_keep;  // Quality's factor back (1025 on a 480i TV: the vertical filter)
        vscale_keep = ~0U;
    }
    scaler = (scaler & ~PVR_SCALER_CFG_VSCALE_FACTOR) | vset;
    PVR_SET(PVR_SCALER_CFG, scaler);
#else
    pvr_state.pclip_bottom = M.lines == 480 ? 479U : M.lines - 2U;
    pvr_state.pclip_y = (pvr_state.pclip_bottom << 16) | pvr_state.pclip_top;
    const uint32_t scaler = (PVR_GET(PVR_SCALER_CFG) & ~PVR_SCALER_CFG_FSAA) | (M.fsaa ? PVR_SCALER_CFG_FSAA : 0U);
    PVR_SET(PVR_SCALER_CFG, scaler);
#endif
    pvr_sync_reg_buffer();  // the TA of the current target bank with the new tile count and blocks
    re4dc_screen_w = M.w;
    re4dc_screen_h = M.lines;
    re4dc_screen_wf = float(M.w);
    re4dc_screen_hf = float(M.lines);
    re4dc_screen_half_wf = float(M.w) * 0.5f;
    re4dc_screen_half_hf = float(M.lines) * 0.5f;
    re4dc_ui_sx = float(M.w) / 640.0f;
    re4dc_ui_sy = float(M.lines) / 480.0f;
    re4dc_res_vjitter = 0.0f;
    // Frame buffers: the renders of a non-alternating mode go to the buffer the held picture does not use (KOS
    // writes frame_buffers[view ^ 1] and shows frame_buffers[view] at the flip).
    const int v = pvr_state.view_target;
    inflight_p = -1;
    seen_view = v;
    if (boot) {
        pvr_state.frame_buffers[0].frame = fb_base[0];
        pvr_state.frame_buffers[1].frame = fb_base[1];
    } else {
        pvr_state.frame_buffers[v].frame = fb_base[held_buf];
        pvr_state.frame_buffers[v ^ 1].frame = fb_base[held_buf ^ 1];
    }
    alt = to_alt;
#if RE4DC_RENDER_FSAA
    last_line = ol == 240 ? (to_alt ? 2U * lb : lb) : 0U;
#else
    last_line = M.lines == 240 ? (to_alt ? 2U * lb : lb) : 0U;
#endif
    clear_last();
    if (to_alt) {
        fill_buf = boot ? 1U : unsigned(held_buf ^ 1);
        fill_mask = boot ? 3U : 0U;
        disp[0] = disp[1] = boot ? 0 : held_buf;
        wait_view = -1;
        hold = !boot;
        live = alt_display(M.w);
    } else {
        fill_mask = 3U;
#if RE4DC_RENDER_FSAA
        live = ol == 480 ? Display{0, 640, fb_base[0], fb_base[0] + 640U * 2U} : Display{1, w_write, fb_base[0], fb_base[0]};
#else
        live = M.lines == 480 ? Display{0, 640, fb_base[0], fb_base[0] + 640U * 2U} : Display{1, w_write, fb_base[0], fb_base[0]};
#endif
        wait_view = boot ? -1 : v;
        hold = !boot;
    }
    cur = m;
    ++applied;
    osd_until = re4dc_vi_retrace_count() + 180U;
#if RE4DC_RENDER_FSAA
    re4dc_log("res: mode %u %s applied (scaler %08x, %s, %s, clip y %u, %ux%u tiles)\n", m, M.name,
              unsigned(PVR_GET(PVR_SCALER_CFG)), vga ? "VGA" : interlaced ? "TV 480i" : "TV",
              to_alt ? "alternating lines" : ol == 240 ? "doubled" : m == kVupMode ? "full, scaler x2 vertical" : "full",
              unsigned(pvr_state.pclip_bottom), tw, th);
#else
    re4dc_log("res: mode %u %s applied (scaler %08x, %s, %s)\n", m, M.name, unsigned(PVR_GET(PVR_SCALER_CFG)),
              vga ? "VGA" : interlaced ? "TV 480i" : "TV", to_alt ? "alternating lines" : M.lines == 240 ? "doubled" : "full");
#endif
}
// Non-alternating display of the current mode after its first flip (KOS's pvr_sync_view sets the start address).
void live_kind_display()
{
    if (alt || hold) return;
    const Mode& M = kModes[cur];
#if RE4DC_RENDER_FSAA
    const unsigned ol = out_lines(cur);
    (void)M;
    PVR_SET(PVR_FB_SIZE, fb_size_of(ol == 480 ? 0U : 1U, fb_w(cur)));
    PVR_SET(PVR_FB_CFG_1, (vga && ol == 240) ? (boot_fb_cfg1 | 2U) : boot_fb_cfg1);
#else
    PVR_SET(PVR_FB_SIZE, fb_size_of(M.lines == 480 ? 0U : 1U, fb_w(cur)));
    PVR_SET(PVR_FB_CFG_1, (vga && M.lines == 240) ? (boot_fb_cfg1 | 2U) : boot_fb_cfg1);
#endif
    PVR_SET(PVR_VIDEO_CFG, fb_w(cur) == 320 ? (boot_video_cfg | 0x100U) : (boot_video_cfg & ~0x100U));
}
}  // namespace

// Link-time wrap of KOS's render start (pvr_irq.c / pvr_misc.c, IRQ context, the PVR is about to be told to render):
// for an alternating mode, the write-out start of this render is the older half of its scene's parity.
extern "C" void __real_pvr_begin_queued_render(void);
#if defined(RE4DC_SKY_PLAY) && RE4DC_SKY_PLAY
extern "C" int re4dc_sky_play_render(void);   // native_sky.cpp
#endif
extern "C" void __wrap_pvr_begin_queued_render(void)
{
    if (alt && !pvr_state.curr_to_texture) {
        note_flip();
        const int bank = pvr_state.ta_target ^ pvr_state.vbuf_doublebuf;
        const int p = bank_parity[bank];
        const int b = fill_mask != 3U ? int(fill_buf) : (disp[p] ^ 1);
        inflight_p = p;
        inflight_buf = b;
        pvr_state.frame_buffers[pvr_state.view_target ^ 1].frame = fb_base[b] + unsigned(p) * lb;
    }
#if defined(RE4DC_SKY_PLAY) && RE4DC_SKY_PLAY
    // SKY_PLAY (post30.mk, native_sky.cpp): the same render start with the room's PS2 sky panorama as the background plane
    if (re4dc_sky_play_render()) return;
#endif
    __real_pvr_begin_queued_render();
}

// native_ui.cpp re4dc_ui_init, before pvr_init: the allocation for the largest available mode.
extern "C" unsigned re4dc_res_params(pvr_init_params_t* p)
{
    const unsigned mt = max_tiles();
    unsigned shrink = 0;
#if RE4DC_RENDER_FSAA
    if (mt > 320) {  // mode 3: the KOS 300-tile layout; kFsaaPools pools borrowed from the vertex buffer while it is on
        unsigned words = 0;
        for (unsigned l = 0; l < PVR_OPB_COUNT; ++l) words += unsigned(p->opb_sizes[l]);
        fsaa_extra = (words * 4U * 300U * kFsaaPools + 127U) & ~127U;
        re4dc_log("res: RENDER_FSAA: KOS allocation of 300 tiles (Standard layout); FSAA borrows %u B per bank from the vertex buffer while it is on\n",
                  unsigned(fsaa_extra));
    } else
#endif
    if (mt > 320) {
        p->fsaa_enabled = 1;  // KOS allocates 1280x480 (600 tiles); the boot mode is applied after pvr_init
    } else if (mt > 300) {
        unsigned words = 0;
        for (unsigned l = 0; l < PVR_OPB_COUNT; ++l) words += unsigned(p->opb_sizes[l]);
        shrink = (words * 4U * 300U + 1023U) & ~1023U;  // one more overflow pool, paid by the vertex buffer
        p->opb_overflow_count += 1;
        p->vertex_buf_size -= int(shrink);
    }
    re4dc_log("res: RES_MODES %u boot %u: max tiles %u, %s, vertex buffer %d B per bank (-%u)\n", unsigned(RE4DC_RES_MODES),
              unsigned(RE4DC_RES_MODE), mt, mt > 320 ? "FSAA allocation (600 tiles)" : mt > 300 ? "+1 overflow pool" : "KOS allocation",
              p->vertex_buf_size, shrink);
    return unsigned(p->vertex_buf_size);
}

// native_ui.cpp re4dc_ui_init, after pvr_init (no scene yet).
extern "C" void re4dc_res_init()
{
    vga = vid_mode && vid_mode->cable_type == CT_VGA;
    interlaced = vid_mode && (vid_mode->flags & VID_INTERLACE);
    boot_fb_size = PVR_GET(PVR_FB_SIZE);
    boot_fb_cfg1 = PVR_GET(PVR_FB_CFG_1);
    boot_video_cfg = PVR_GET(PVR_VIDEO_CFG);
    fb_base[0] = pvr_state.frame_buffers[0].frame;
    fb_base[1] = pvr_state.frame_buffers[1].frame;
    kos_tiles = unsigned(pvr_state.tw * pvr_state.th);
    tile_bytes = 0;
    for (unsigned l = 0; l < PVR_OPB_COUNT; ++l) tile_bytes += pvr_state.opb_size[l];
    for (unsigned b = 0; b < 2; ++b) {
        volatile pvr_ta_buffers_t* buf = pvr_state.ta_buffers + b;
        banks[b].opb = buf->opb;
#if RE4DC_RENDER_FSAA
        vsize_kos[b] = buf->vertex_size;
        if (buf->vertex + buf->vertex_size > buf->opb || buf->vertex + buf->vertex_size + 128U <= buf->opb || fsaa_extra >= buf->vertex_size)
            fsaa_extra = 0;  // not the KOS layout this relies on ([vertex | opb]): no borrowing (mode 3 is refused)
#endif
        banks[b].region_end = buf->opb + buf->opb_size * (1U + buf->opb_overflow_count);
        banks[b].tm_kos = buf->tile_matrix;
    }
    re4dc_log("res: KOS tiles %u (%dx%d fsaa %d) bytes per tile %u region %06x..%06x / %06x..%06x frame %06x / %06x +%u texture pool %u %s\n",
              kos_tiles, pvr_state.tw, pvr_state.th, pvr_state.fsaa, tile_bytes, unsigned(banks[0].opb),
              unsigned(banks[0].region_end), unsigned(banks[1].opb), unsigned(banks[1].region_end), unsigned(fb_base[0]),
              unsigned(fb_base[1]), unsigned(pvr_state.frame_buffers[0].frame_size), unsigned(pvr_mem_available()),
              vga ? "VGA" : interlaced ? "TV 480i" : "TV");
    const int o = irq_disable();
    const unsigned boot = RE4DC_RES_MODE;
    cur = ~0U;
    apply(boot);
    hold = false;
    write_display(live);
    irq_restore(o);
    vbl_handle = vblank_handler_add(vblank, nullptr);
    inited = true;
}

extern "C" void re4dc_res_cycle();
// Called once per frame (re4dc_ui_begin), before the frame's scene is built. RES_CYCLE_FRAMES=n (test arms only:
// fixture buttons never fire the pad chord): the next mode every n frames, for the scripted Flycast pass. An
// alternating mode gives the coming scene its parity (the TA bank it is built in) and the viewport jitter.
extern "C" int re4dc_res_pending()
{
#if defined(RE4DC_RES_CYCLE_FRAMES) && RE4DC_RES_CYCLE_FRAMES
    static unsigned frames;
    if (inited && ++frames % unsigned(RE4DC_RES_CYCLE_FRAMES) == 0) re4dc_res_cycle();
#endif
    if (inited && alt) {
        const int p = next_parity;
        next_parity ^= 1;
        bank_parity[pvr_state.ta_target] = p;
        // Odd frames sample half a render line lower: the geometry moves up half a line (viewport top units).
        re4dc_res_vjitter = p ? -0.5f / re4dc_screen_hf : 0.0f;  // half a render line, as a fraction of the height
    }
    return inited && want != cur;
}

// native_ui.cpp re4dc_ui_begin after present_fence(): applies a requested mode if the PVR is idle.
extern "C" void re4dc_res_apply_pending()
{
    const unsigned m = want;
    if (!inited || m == cur) return;
#if RE4DC_RENDER_FSAA
    if (tiles_of(m) > kos_tiles && !fsaa_extra) {  // no borrowed pools (unexpected KOS layout): stay in this mode
        re4dc_log("res: mode %u refused: no FSAA pools\n", m);
        want = cur;
        return;
    }
#endif
    const int o = irq_disable();
    if (pvr_state.ta_busy || pvr_state.render_busy || pvr_state.render_completed || pvr_present_pending() || hold) {
        irq_restore(o);
        return;  // not idle yet (or the previous change still holds its picture): next frame
    }
    apply(m);
    if (alt) {  // this frame's scene: the first fill parity
        next_parity = 0;
        bank_parity[pvr_state.ta_target] = 0;
        next_parity = 1;
    }
    irq_restore(o);
}

// Test builds (pad.cpp chord): the next available mode, applied at the next safe point.
extern "C" void re4dc_res_cycle()
{
#if RE4DC_RENDER_QUALITY_ONLY
    return;  // game30.mk RENDER_QUALITY_ONLY: Quality (mode 0) only
#endif
    unsigned m = cur == ~0U ? 0U : cur;
    for (unsigned i = 0; i < kModeCount; ++i) {
        m = (m + 1U) % kModeCount;
        if (RE4DC_RES_MODES >> m & 1) break;
    }
    want = m;
    re4dc_log("res: mode %u %s requested\n", m, kModes[m].name);
}

extern "C" unsigned re4dc_res_mode() { return cur; }

// option_rows.cpp: Standard / Fast are doubled, not alternating, on a VGA cable.
extern "C" int re4dc_res_vga(void) { return vga ? 1 : 0; }

// RENDER_OPTION (quality.cpp, the stored / file setting: Quality = 0, Standard = 1, Fast = 4): request mode m;
// applied at the next safe point like the chord.
extern "C" void re4dc_res_set(unsigned m)
{
    if (m >= kModeCount || !(RE4DC_RES_MODES >> m & 1)) return;
    if (want != m) re4dc_log("res: mode %u %s requested (setting)\n", m, kModes[m].name);
    want = m;
}

// The on-screen label (native_static.cpp re4dc_look_osd_text): 3 s after each applied change.
extern "C" const char* re4dc_res_osd_text()
{
    if (!applied || cur == ~0U || int(osd_until - re4dc_vi_retrace_count()) <= 0) return nullptr;
    return kModes[cur].name;
}

// crash_screen.cpp show(): the 640x480 display layout back (both frame buffers are always 640x480).
extern "C" void re4dc_res_crash_display()
{
    if (!inited) return;
    hold = false;
    alt = false;
    live = Display{0, 640, PVR_GET(PVR_FB_ADDR) & (PVR_RAM_SIZE - 1), (PVR_GET(PVR_FB_ADDR) & (PVR_RAM_SIZE - 1)) + 1280U};
    write_display(live);
}
#endif
