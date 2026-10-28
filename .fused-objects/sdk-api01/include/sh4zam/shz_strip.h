#ifndef SHZ_STRIP_H
#define SHZ_STRIP_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Projected vertices are 32 bytes: command,x,y,z,u,v,color,offset-color.
 * The caller holds the SQ lock and selects culling/material eligibility.
 * mask=255 preserves ordinary command words; mask=127 synthesizes VERTEX;
 * mask=383 additionally splits actor streams at index bit7 (parity resets).
 * Cull1 keeps positive even-triangle FMAC areas, cull2 negative areas.
 * Internal back runs of length1/2 remain; end runs and longer gaps drop.
 * Preserves r8-r14, FR12-FR15, PR, exact FPSCR and all opposite-bank words.
 * No clipping or material policy is performed by the single-stream API.
 */
typedef struct shz_strip_sq {
    const void *cache;
    const uint8_t *indices;
    uint32_t n,mask,cull;
    uint32_t *q;
    uint32_t sent,pieces;
} shz_strip_sq_t;
void shz_strip_sq(shz_strip_sq_t *context);
/* Count-prefixed world stream. Returns the original count-byte address of
 * the first strip needing clipping, or end. No SQ writes precede that strip's
 * all/any/depth/limit decision. Counters are additive, like the lean walk.
 * all&3 rejects before the clip test; any&3 or n>limit stops before screen
 * rejection. Outcodes are sign-extended bytes; all starts at255, any at0.
 */
typedef struct shz_strip_walk {
    const uint8_t *cursor,*end,*outcodes;
    const void *cache;
    uint32_t limit,cull;
    uint32_t *q;
    uint32_t culled,emitted,accepted_triangles;
} shz_strip_walk_t;
void shz_strip_walk_sq(shz_strip_walk_t *context);
#ifdef __cplusplus
}
static_assert(sizeof(void*)!=4 || sizeof(shz_strip_sq_t)==32,"strip SQ ABI");
#endif
#endif
