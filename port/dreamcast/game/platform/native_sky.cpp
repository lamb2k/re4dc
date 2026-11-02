// SKY_PLAY=1 (lane sky27, user 2026-11-02 "Yes fix the sky"; render only, default 0: this file is not built).
// In normal play look A culls the PS2 world at the view distance, so the room's PS2 sky dome, treeline and backdrop
// cards (native_static.cpp ps2_sky_row; 60-400 m out) are never drawn and the clear colour shows where the PS2 shows
// sky. Drawing those rows costs world geometry every frame; the user's constraint is "It shouldn't impact rendering
// performance". So the rows are baked offline (tools/ps2_sky_bake.py: the PS2 rows of each room, PS2 fog at their
// distance, an equirectangular band 1024 x 256 VQ RGB565 = 66 KiB) and shown as the PVR BACKGROUND PLANE: the ISP fills
// it behind everything for free (it replaces the flat clear colour the background plane already carries). Per frame
// the CPU computes three corner texture coordinates from the camera (a few dozen float operations); no TA geometry.
//
// - Data: dc/native/rXXX/ps2-sky.r4sk (data sets sky27 / sky27c), read once when the room's PS2 world package opens
//   (room entry) straight into texture RAM (room arena class), freed when the package closes. A room without the file
//   keeps the flat clear colour (indoor rooms).
// - Frame: native_static.cpp ps2_pass (pass 0) hands the camera; the corners go into the slot of the TA bank being
//   built. Only when look A's sky is 0 and no scripted camera owns the view (SKY_EVENT=2 draws the real rows then):
//   never the plane and the rows together.
// - Render start (res_mode.cpp's link wrap of KOS pvr_begin_queued_render, IRQ context): when the bank being rendered
//   has armed corners, the KOS function's body runs here with a textured background plane (ISP texture bit, VQ texture
//   control word, x y z u v colour vertices, tag skip 3) instead of the coloured one; otherwise KOS's own runs.
// Nothing here reads or writes game state.
#include <kos.h>
#include <dc/pvr.h>
#include <dc/pvr/pvr_regs.h>
#include <dc/video.h>
#include <cfloat>
#include <cmath>
#include <cstdint>
#include <cstring>
#include "pvr_internal.h"  // KOS internals (C linkage): pvr_state, pvr_bkg layout

extern "C" void re4dc_log(const char* fmt, ...);
extern "C" unsigned re4dc_ui_frame();
#if defined(RE4DC_VRAM_ROOM_ARENA) && RE4DC_VRAM_ROOM_ARENA
extern "C" volatile unsigned re4dc_vram_arena_class;   // vram_pages.cpp: 1 = room (bottom up)
#endif

namespace {
struct Head { char magic[4]; std::uint32_t version; std::uint16_t w, h; std::uint32_t payload; float top, bottom, eye[3]; std::uint32_t reserved[3]; };
static_assert(sizeof(Head) == 48, "R4SK header");

pvr_ptr_t texture;
unsigned loaded_room, tex_w, tex_h, tsp_size;
float el_top, el_bottom;
unsigned st_frames, st_drawn, st_fallback;

struct Corners { float u[3], v[3]; volatile int armed; };
Corners slot[2];

unsigned size_code(unsigned n) { unsigned c = 0; while ((8U << c) < n) ++c; return c; }

void release() {
    if (texture) {
        pvr_mem_free(texture);
        re4dc_log("sky play: room=%03x freed\n", loaded_room);
    }
    texture = nullptr; loaded_room = 0; slot[0].armed = 0; slot[1].armed = 0;
}
}  // namespace

// native_static.cpp, when the room's PS2 world package opens (room entry) or closes (room 0).
extern "C" void re4dc_sky_play_room(unsigned room) {
    if (room == loaded_room && texture) return;
    release();
    if (!room) return;
    char path[48];
    snprintf(path, sizeof(path), "/cd/dc/native/r%03x/ps2-sky.r4sk", room);
    const file_t f = fs_open(path, O_RDONLY);
    if (f == FILEHND_INVALID) { re4dc_log("sky play: room=%03x file=absent\n", room); return; }
    Head h{};
    const char* why = nullptr;
    if (fs_read(f, &h, sizeof(h)) != ssize_t(sizeof(h))) why = "header";
    else if (std::memcmp(h.magic, "R4SK", 4) || h.version != 1U) why = "magic";
    else if (h.w < 8 || h.w > 1024 || h.h < 8 || h.h > 1024 || (h.w & (h.w - 1)) || (h.h & (h.h - 1)) ||
             h.payload != 2048U + unsigned(h.w) * h.h / 4U || !(h.top > h.bottom))
        why = "layout";
    if (!why) {
#if defined(RE4DC_VRAM_ROOM_ARENA) && RE4DC_VRAM_ROOM_ARENA
        const unsigned cls = re4dc_vram_arena_class;
        re4dc_vram_arena_class = 1;
        texture = pvr_mem_malloc(h.payload);
        re4dc_vram_arena_class = cls;
#else
        texture = pvr_mem_malloc(h.payload);
#endif
        if (!texture) why = "no contiguous block";
    }
    if (!why) {
        alignas(32) static std::uint8_t chunk[4096];
        unsigned done = 0;
        while (done < h.payload) {
            const unsigned n = h.payload - done < sizeof(chunk) ? h.payload - done : unsigned(sizeof(chunk));
            if (fs_read(f, chunk, n) != ssize_t(n)) { why = "read"; break; }
            pvr_txr_load(chunk, static_cast<std::uint8_t*>(texture) + done, n);
            done += n;
        }
        if (why) { pvr_mem_free(texture); texture = nullptr; }
    }
    fs_close(f);
    if (why) {
        re4dc_log("sky play: room=%03x FAIL %s free=%u\n", room, why, unsigned(pvr_mem_available()));
        return;
    }
    loaded_room = room; tex_w = h.w; tex_h = h.h; el_top = h.top; el_bottom = h.bottom;
    tsp_size = size_code(h.w) << 3 | size_code(h.h);
    re4dc_log("sky play: room=%03x loaded %ux%u vq bytes=%u vram=%08x free=%u\n", room, tex_w, tex_h, unsigned(h.payload),
              unsigned(std::uintptr_t(texture)), unsigned(pvr_mem_available()));
}

// native_static.cpp ps2_pass (pass 0, the scene being built): active = look A sky 0, no scripted camera, room drawn.
// view = the camera's 3x4 world -> eye matrix (GX: the eye looks down -z), P = GXGetProjectionv, vp = GXGetViewportv.
extern "C" void re4dc_sky_play_frame(int active, unsigned room, const float* view, const float* P, const float* vp) {
    Corners& s = slot[pvr_state.ta_target & 1];
    s.armed = 0;
    if (!active || !texture || room != loaded_room || P[0] != 0.0f || !(P[1] > 0.0f) || !(P[3] > 0.0f) || !(vp[2] > 0.0f) ||
        !(vp[3] > 0.0f))
        return;
    ++st_frames;
    // screen corners in the GX frame (640 x 480 EFB pixels): bottom-left, top-left, bottom-right (the plane's order)
    static const float sx[3] = {0.0f, 0.0f, 640.0f}, sy[3] = {480.0f, 0.0f, 480.0f};
    const float kTau = 6.28318531f, rad = 57.2957795f;
    float u0 = 0.0f;
    for (unsigned i = 0; i < 3; ++i) {
        const float nx = (sx[i] - vp[0]) / vp[2] * 2.0f - 1.0f, ny = 1.0f - (sy[i] - vp[1]) / vp[3] * 2.0f;
        const float xc = (nx + P[2]) / P[1], yc = (ny + P[4]) / P[3];   // eye space, z = -1
        const float dx = view[0] * xc + view[4] * yc - view[8];
        const float dy = view[1] * xc + view[5] * yc - view[9];
        const float dz = view[2] * xc + view[6] * yc - view[10];
        float u = std::atan2(dx, dz) / kTau;
        if (i == 0) { if (u < 0.0f) u += 1.0f; u0 = u; }
        else { float d = u - u0; d -= std::floor(d + 0.5f); u = u0 + d; }
        const float el = std::atan2(dy, std::sqrt(dx * dx + dz * dz)) * rad;
        s.u[i] = u;
        s.v[i] = (el_top - el) / (el_top - el_bottom);
    }
    s.armed = 1;
}

// res_mode.cpp __wrap_pvr_begin_queued_render (IRQ context): 1 = this render was started here with the panorama.
// The body is KOS 804b3195 pvr_misc.c pvr_begin_queued_render with the background plane textured.
extern "C" int re4dc_sky_play_render(void) {
    if (pvr_state.curr_to_texture) return 0;
    const int bank = pvr_state.ta_target ^ pvr_state.vbuf_doublebuf;
    Corners& s = slot[bank & 1];
    if (!s.armed || !texture) { s.armed = 0; return 0; }
    s.armed = 0;
    volatile pvr_ta_buffers_t* tbuf = pvr_state.ta_buffers + bank;
    volatile pvr_frame_buffers_t* rbuf = pvr_state.frame_buffers + (pvr_state.view_target ^ 1);
    const std::uint32_t pos = PVR_GET(PVR_TA_VERTBUF_POS);
    constexpr std::uint32_t kWords = 3 + 3 * 6;
    if (pos + kWords * 4 + 32 > tbuf->vertex + tbuf->vertex_size) { ++st_fallback; return 0; }   // no room: KOS's plane
    const float tw = float(pvr_state.w), th = float(pvr_state.h);
    const std::uint32_t vert_end = (3U << 24) | ((pos - tbuf->vertex) << 1);   // tag skip 3: x y z u v colour
    volatile std::uint32_t* w = reinterpret_cast<volatile std::uint32_t*>(PVR_RAM_BASE | pos);
    auto f = [](float x) { std::uint32_t r; std::memcpy(&r, &x, 4); return r; };
    w[0] = 0x90800000U | (1U << 25);                                   // KOS's ISP word + texture
    w[1] = 0x20800000U | (4U << 8) | (1U << 15) | (1U << 13) | tsp_size; // ONE/ZERO, no fog, D 1.0, clamp V, bilinear, decal
    w[2] = (1U << 30) | (1U << 27) | ((std::uint32_t(std::uintptr_t(texture)) & 0x00fffff8U) >> 3);   // VQ, RGB565, twiddled
    const float xs[3] = {0.0f, 0.0f, tw}, ys[3] = {th, 0.0f, th};
    for (unsigned i = 0; i < 3; ++i) {
        volatile std::uint32_t* v = w + 3 + 6 * i;
        v[0] = f(xs[i]); v[1] = f(ys[i]); v[2] = f(FLT_EPSILON);
        v[3] = f(s.u[i]); v[4] = f(s.v[i]); v[5] = 0xffffffffU;
    }
    PVR_SET(PVR_ISP_TILEMAT_ADDR, tbuf->tile_matrix);
    PVR_SET(PVR_ISP_VERTBUF_ADDR, tbuf->vertex);
    PVR_SET(PVR_RENDER_ADDR, rbuf->frame);
    PVR_SET(PVR_BGPLANE_CFG, vert_end);
    union { float f; std::uint32_t i; } zclip;
    zclip.f = pvr_state.zclip;
    PVR_SET(PVR_BGPLANE_Z, zclip.i);
    PVR_SET(PVR_PCLIP_X, pvr_state.pclip_x);
    PVR_SET(PVR_PCLIP_Y, pvr_state.pclip_y);
    PVR_SET(PVR_RENDER_MODULO, (pvr_state.w * vid_pmode_bpp[vid_mode->pm]) / 8);
    PVR_SET(PVR_ISP_START, PVR_ISP_START_GO);
    if (!(++st_drawn % 1800U))
        re4dc_log("sky play: room=%03x drawn=%u frames=%u fallback=%u u=%d v=%d\n", loaded_room, st_drawn, st_frames,
                  st_fallback, int(s.u[1] * 1000.0f), int(s.v[1] * 1000.0f));
    return 1;
}
