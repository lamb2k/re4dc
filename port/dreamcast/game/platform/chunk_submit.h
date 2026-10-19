/* chunk_submit.h: the shared chunk-submit back end (lane scenery19, SCENERY19-STATUS.md "Back-end interface").
 * DRAFT v0: the shape is fixed, the implementation lands with SCENERY_CHUNK. Users: the PS2 world scenery, rigid
 * objects (one object matrix per drawn tick), and skinned characters (lane character-draw-path).
 *
 * Model (Code: Veronica njCnk style): a draw is a stream of chunks under one prebuilt PVR header.
 *   1. re4dc_chunk_begin(): binds the header for a texture/state key (the header table is built once per room or per
 *      key; no per-draw header assembly) and loads the screen matrix for the caller's 3x4 model-to-view matrix.
 *   2. re4dc_chunk_points(): transforms each distinct point once (FTRV, 1/w, outcodes) into the sink's point cache.
 *      A skinned caller may instead write already-transformed view-space points with re4dc_chunk_view_points().
 *   3. re4dc_chunk_strips(): for each strip (u8 count, then u8 corner indices; corner = point index + u,v,colour),
 *      culls whole strips outside one screen edge, sends the rest by store queue, and hands strips crossing
 *      near/far to the existing clipper unchanged. Strip order is kept: the caller owns pass and draw order.
 *   4. re4dc_chunk_end(): releases the store queues and commits counts.
 * Exactness: vertex words equal today's MeshDraw path for the same inputs (same FTRV and projection expressions).
 */
#ifndef RE4DC_CHUNK_SUBMIT_H
#define RE4DC_CHUNK_SUBMIT_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

/* Texture / state key, as the PS2 world part key: crc, fnv, width, height, pass (0 OP, 1 PT, 2 TR), cull (0 none,
 * 1 CCW, 2 CW). */
typedef struct { uint32_t crc, fnv, width, height, pass, cull; } re4dc_chunk_key;

/* One corner: its point, texture coordinates (grid units, scaled by the draw's uv constants) and ARGB1555/4444
 * colour (the draw's colour mode). */
typedef struct { uint8_t point, pad; uint16_t u, v, colour; } re4dc_chunk_corner;

typedef struct {
    const float* projection;   /* 7 floats, GX layout */
    const float* viewport;     /* 6 floats */
    float mv[12];              /* model (or grid) -> view, 3x4 row major */
    float near_distance, far_distance;
    float uv_scale[2], uv_bias[2], uv_offset[2];
    uint32_t colour_mode;      /* 0 ARGB1555, 1 ARGB4444 (vertex alpha) */
    uint32_t alpha;            /* or-mask for opaque corners */
} re4dc_chunk_draw;

typedef struct re4dc_chunk_sink re4dc_chunk_sink; /* opaque, one per open draw (stack storage, see size below) */
enum { RE4DC_CHUNK_SINK_BYTES = 256, RE4DC_CHUNK_MAX_POINTS = 256 };

/* 1 bound, 0 nothing published (caller may fall back), -1 frame aborted. */
int  re4dc_chunk_begin(const re4dc_chunk_key* key, const re4dc_chunk_draw* draw, re4dc_chunk_sink* sink);
/* points: n x 3 int16/uint16 grid positions (mv folds the grid in); returns 1, or -1 on abort. */
int  re4dc_chunk_points(re4dc_chunk_sink* sink, const uint16_t* points, unsigned n);
/* view-space points (skinned callers): n x 3 floats. */
int  re4dc_chunk_view_points(re4dc_chunk_sink* sink, const float* view_xyz, unsigned n);
/* strips: bytes as R4IM (u8 n, n u8 corner indices) addressing corners[]; 1 ok, -1 abort. */
int  re4dc_chunk_strips(re4dc_chunk_sink* sink, const re4dc_chunk_corner* corners, const uint8_t* strips,
                        unsigned strip_bytes);
void re4dc_chunk_end(re4dc_chunk_sink* sink);

#ifdef __cplusplus
}
#endif
#endif
