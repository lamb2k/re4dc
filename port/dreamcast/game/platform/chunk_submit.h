/* chunk_submit.h: the shared chunk-submit back end (lane scenery19, SCENERY19-STATUS.md "Back-end interface").
 * v1 SHAPE (10-19; implementation lands with SCENERY_CHUNK, r101 scenery first). Users: PS2 world scenery, rigid
 * objects (one object matrix per drawn tick), skinned characters (lane character-draw-path).
 *
 * A draw is a stream of chunks under one prebuilt PVR header:
 *   re4dc_chunk_header_build()  once per material key (room entry / first use): the 32-byte polygon header words,
 *                               with the material's alpha state and PCW bits (strip length, UV16) chosen by the caller.
 *   re4dc_chunk_window_begin()  opens the store-queue window. One window may carry many headers (COARSE_ONE_SUBMIT:
 *                               one window per actor); re4dc_chunk_header() switches header inside it.
 *   points                      each distinct point once: re4dc_chunk_points_grid() (FTRV of u16 grid points through
 *                               the screen matrix of a 3x4 model/grid->view matrix: scenery, rigid objects) or
 *                               re4dc_chunk_points_view() (caller's view-space floats: skinned characters).
 *   corners                     re4dc_chunk_corners(): each corner = a point + its final float u,v words + 32-bit ARGB
 *                               (the caller computes them, so they equal today's words exactly; scenery uses
 *                               re4dc_chunk_corners_u16() which applies today's uv/colour expressions).
 *   re4dc_chunk_strips()        strips of corner indices: whole strips outside one screen edge are culled, strips
 *                               inside near/far go by store queue, the rest go to the existing clipper with the
 *                               draw's own projection (project() context), near/far and header PCW.
 *   re4dc_chunk_window_end()    releases the store queues, commits counts.
 * Limits: a corner batch holds at most RE4DC_CHUNK_MAX_CORNERS corners (today's R4IM meshlets and actor meshlets fit;
 * a caller splits larger ones); points per draw up to 65535 (u16 point indices). Strip order is kept: the caller owns
 * pass and draw order. Exactness: vertex words equal today's paths for the same inputs.
 */
#ifndef RE4DC_CHUNK_SUBMIT_H
#define RE4DC_CHUNK_SUBMIT_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

enum { RE4DC_CHUNK_MAX_CORNERS = 256, RE4DC_CHUNK_SINK_BYTES = 512 };

/* Material key (the PS2 world part key; actors use their texture key the same way). */
typedef struct { uint32_t crc, fnv, width, height, pass, cull; } re4dc_chunk_key;
enum { RE4DC_CHUNK_PCW_STRIP6 = 1, RE4DC_CHUNK_PCW_UV16 = 2, RE4DC_CHUNK_VERTEX_ALPHA = 4 };
typedef struct {
    re4dc_chunk_key key;
    uint32_t alpha_state;   /* the material's alpha / blend state as today's header builder takes it */
    uint32_t flags;         /* RE4DC_CHUNK_PCW_*, RE4DC_CHUNK_VERTEX_ALPHA */
    uint32_t words[8];      /* out: the 32-byte header */
    float u_scale, v_scale; /* out: the bound texture's native UV scale */
} re4dc_chunk_header_t;

typedef struct {
    const float* projection;   /* 7 floats, GX layout: the clipper's project() uses these */
    const float* viewport;     /* 6 floats */
    float near_distance, far_distance;
} re4dc_chunk_view;

typedef struct re4dc_chunk_sink re4dc_chunk_sink; /* opaque; caller storage of RE4DC_CHUNK_SINK_BYTES, 32-aligned */

/* 1 built / bound, 0 nothing published (caller may fall back), -1 frame aborted. */
int  re4dc_chunk_header_build(re4dc_chunk_header_t* h);
int  re4dc_chunk_window_begin(re4dc_chunk_sink* s, const re4dc_chunk_view* v, const re4dc_chunk_header_t* first);
int  re4dc_chunk_header(re4dc_chunk_sink* s, const re4dc_chunk_header_t* h);
/* Points into the sink's cache (index 0..n-1). Grid form: mv is grid->view 3x4 row major. */
int  re4dc_chunk_points_grid(re4dc_chunk_sink* s, const float mv[12], const uint16_t* xyz, unsigned n);
int  re4dc_chunk_points_view(re4dc_chunk_sink* s, const float* view_xyz, unsigned n);
/* Screen-space points passed through as-is (skinned characters project themselves): n x {x, y, 1/w} floats and one
 * outcode byte each, in mesh_fastpath.hpp's kChecksAll layout (bits 5..2 screen x<0, x>W, y<0, y>H; bit 1 w<near;
 * bit 0 w>far). */
int  re4dc_chunk_points_screen(re4dc_chunk_sink* s, const float* xy_invw, const uint8_t* outcodes, unsigned n);
/* Corners: point index, final u/v float words, 32-bit ARGB (offset colour 0). */
int  re4dc_chunk_corners(re4dc_chunk_sink* s, const uint16_t* point, const float* uv, const uint32_t* argb, unsigned n);
/* Strips, in one of two byte forms:
 *   RE4DC_CHUNK_STRIPS_R4IM:  u8 n, then n u8 corner indices (scenery);
 *   RE4DC_CHUNK_STRIPS_ACTOR: u8 corner indices, bit 7 set on a strip's last index (corners < 128 per batch).
 * Conversion: an R4IM strip "n i0 .. i(n-1)" is the actor form "i0 .. i(n-2) (i(n-1)|0x80)" when every index < 128. */
enum { RE4DC_CHUNK_STRIPS_R4IM = 0, RE4DC_CHUNK_STRIPS_ACTOR = 1 };
int  re4dc_chunk_strips(re4dc_chunk_sink* s, const uint8_t* strips, unsigned strip_bytes, unsigned form);
void re4dc_chunk_window_end(re4dc_chunk_sink* s);

#ifdef __cplusplus
}
#endif
#endif
