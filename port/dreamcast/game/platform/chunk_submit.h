/* chunk_submit.h: the shared chunk-submit back end (lane scenery19, SCENERY19-STATUS.md "Back-end interface").
 * v1.1 (10-19: + re4dc_chunk_vertices_direct), implemented in platform/chunk_submit.cpp (scenery19.mk: CHUNK_SUBMIT=1, implied by SCENERY_CHUNK).
 * Users: PS2 world scenery, rigid objects (one object matrix per drawn tick), skinned characters
 * (lane character-draw-path).
 *
 * The caller owns binding: it opens its store-queue window and builds its headers as today (exact header words, alpha
 * state, PCW strip length / UV16, COARSE_ONE_SUBMIT's one window per actor). The back end takes over from there:
 *   re4dc_chunk_window_begin()  the caller's open store-queue pointer, a 32-byte aligned cache it lends
 *                               (RE4DC_CHUNK_CACHE_BYTES) and its clipper callback for strips crossing near/far.
 *   re4dc_chunk_header()        sends 8 header words (a header switch inside the window).
 *   points                      re4dc_chunk_points_grid(): FTRV of u16 grid points through the XMTRX the caller
 *                               loaded, 1/w = fsrra(w*w) (HW_LEAN), x*1/w, y*1/w: today's MeshDraw words;
 *                               re4dc_chunk_points_screen(): x, y, 1/w and outcode passed through as-is.
 *   re4dc_chunk_corners()       each corner = a point + its final float u, v words + 32-bit ARGB (the caller computes
 *                               them, so they equal today's words; offset colour 0).
 *   re4dc_chunk_strips()        strips of corner indices, R4IM form (u8 n, then n indices) or actor form (bit 7 on a
 *                               strip's last index). Per strip, from its corners' outcodes: every corner outside one
 *                               depth plane -> dropped; any corner outside a depth plane, or longer than 'limit' ->
 *                               the caller's clipper; every corner outside one screen edge -> culled; else sent by store
 *                               queue with EOL on the last vertex. Strip order is kept.
 *   re4dc_chunk_window_end()    returns the store-queue pointer to the caller (its direct_end).
 * Outcode byte (mesh_fastpath.hpp kChecksAll): bits 5..2 x<0, x>W, y<0, y>H; bit 1 w<near; bit 0 w>far.
 * Limits: 256 corners and 256 points per batch (today's R4IM and actor meshlets fit; split larger ones).
 * Conversion: an R4IM strip "n i0 .. i(n-1)" is the actor strip "i0 .. i(n-2) (i(n-1)|0x80)" when every index < 128.
 */
#ifndef RE4DC_CHUNK_SUBMIT_H
#define RE4DC_CHUNK_SUBMIT_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

enum {
    RE4DC_CHUNK_MAX_CORNERS = 256, RE4DC_CHUNK_MAX_POINTS = 256,
    /* lent cache: 256 x 32-byte vertices, 256 x 16-byte points, 256 corner outcodes, 256 point outcodes */
    RE4DC_CHUNK_CACHE_BYTES = 256 * 32 + 256 * 16 + 256 + 256,
    RE4DC_CHUNK_STRIPS_R4IM = 0, RE4DC_CHUNK_STRIPS_ACTOR = 1
};

/* The caller's clipper for one strip (indices into the current corners, in the given form's index bytes without the
 * count / end bit): 1 done, 0 failed before anything was published, -1 failed after (frame abort). It may write the
 * store queues itself through *re4dc_chunk_sq(). */
typedef int (*re4dc_chunk_clip_fn)(void* ctx, const uint8_t* index, unsigned n, unsigned form);

typedef struct re4dc_chunk_sink {
    uint32_t* sq;               /* store-queue write pointer */
    uint8_t* cache;             /* lent, 32-byte aligned, RE4DC_CHUNK_CACHE_BYTES */
    re4dc_chunk_clip_fn clip; void* clip_ctx;
    unsigned limit;             /* longest strip sent directly (longer ones go to the clipper) */
    unsigned points, corners;   /* current batch sizes */
    unsigned slots, strips, culled, clipped; /* since window_begin: vertices sent, strips sent / culled / clipped */
    const void* vsrc;           /* v1.1: the corners re4dc_chunk_strips reads (the lent cache, or the caller's) */
    const uint8_t* csrc;        /* v1.1: their outcodes */
} re4dc_chunk_sink;

void      re4dc_chunk_window_begin(re4dc_chunk_sink* s, uint32_t* sq, void* cache, unsigned limit,
                                   re4dc_chunk_clip_fn clip, void* clip_ctx);
void      re4dc_chunk_header(re4dc_chunk_sink* s, const uint32_t words[8]);
/* Grid points: n x {x, y, z} u16 at 'stride' bytes through the loaded XMTRX. */
void      re4dc_chunk_points_grid(re4dc_chunk_sink* s, const uint16_t* xyz, unsigned stride, unsigned n,
                                  float near_distance, float far_distance);
/* Screen points: n x {x, y, 1/w} floats and n outcodes, copied as-is. */
void      re4dc_chunk_points_screen(re4dc_chunk_sink* s, const float* xy_invw, const uint8_t* outcodes, unsigned n);
/* Corners: n x point index, n x {u, v} float words, n x ARGB. */
void      re4dc_chunk_corners(re4dc_chunk_sink* s, const uint8_t* point, const float* uv, const uint32_t* argb,
                              unsigned n);
/* v1.1 direct corners (character-draw-path ask, 10-19): the caller's finished PVR vertices are the corners, used in
 * place (no copy): n x 32-byte pvr_vertex_t, 8-byte aligned, flags word PVR_CMD_VERTEX (sent as is; the last vertex of
 * each strip gets EOL), and n outcodes (the bits above). Valid until the next corners call or window end; the caller
 * keeps both arrays unchanged meanwhile. Words sent = the caller's words. */
void      re4dc_chunk_vertices_direct(re4dc_chunk_sink* s, const void* vertices, const uint8_t* outcodes, unsigned n);
const void*    re4dc_chunk_vertices(const re4dc_chunk_sink* s); /* the corners as 32-byte PVR vertices */
const uint8_t* re4dc_chunk_outcodes(const re4dc_chunk_sink* s);
uint32_t**     re4dc_chunk_sq(re4dc_chunk_sink* s);
/* 1 ok, or the clipper's 0 / -1 (the walk stops there). */
int       re4dc_chunk_strips(re4dc_chunk_sink* s, const uint8_t* strips, unsigned strip_bytes, unsigned form);
uint32_t* re4dc_chunk_window_end(re4dc_chunk_sink* s);

#ifdef __cplusplus
}
#endif
#endif
