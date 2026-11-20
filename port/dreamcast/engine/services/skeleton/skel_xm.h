/*! \file
 *  \brief   Bone-chain matrix kernel of the native skeleton service, on SH4ZAM's XMTRX.
 *  \ingroup engine_skeleton
 *
 *  The game's matrices are 3x4 row major (row i = m[i][0..3], the last row 0 0 0 1 implied). XMTRX holds the
 *  parent's world matrix as a 4x4; applying a child's local matrix leaves the child's world matrix in XMTRX, which
 *  the next bone of the chain uses as its parent without a reload. On the SW back-end every element is formed as the
 *  game's C matrix library forms it (the sums commute exactly); on the SH-4 back-end FTRV rounds its own way.
 *
 *  \author lane eng-svc (RE4 Dreamcast engine line)
 *  \copyright MIT
 */
#ifndef SKEL_XM_H
#define SKEL_XM_H

#ifdef __cplusplus
extern "C" {
#endif

/*! Loads XMTRX with the 3x4 row-major matrix \p m (as a 4x4, last row 0 0 0 1). */
void skel_xm_load_3x4(const float m[12]);
/*! XMTRX = XMTRX x \p m (3x4 row major, last row 0 0 0 1). */
void skel_xm_apply_3x4(const float m[12]);
/*! Stores the upper three rows of XMTRX as a 3x4 row-major matrix. */
void skel_xm_store_3x4(float m[12]);
/*! \p out = XMTRX x (\p in, 1): a point through XMTRX. */
void skel_xm_point3(const float in[3], float out[3]);

#ifdef __cplusplus
}
#endif

#endif /* SKEL_XM_H */
