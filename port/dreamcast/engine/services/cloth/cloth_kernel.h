/*! \file
 *  \brief   The cloth chain step as one SH4ZAM kernel (lane eng-svc3): the native cloth service's arithmetic.
 *  \ingroup engine_cloth
 *
 *  One tick of a pendulum chain (PenClothMove / PenClothMove3) on the service's 64-byte link records and the skeleton
 *  service's bone rows. The original makes 3 + Bundle_num passes over a chain's links (the motion and the wind, the
 *  angle limit, Bundle_num constraint passes, the matrices). cloth_k_step() makes Bundle_num + 1: the motion and the
 *  angle limit of a link in one pass (when every upper link comes before its link), the last constraint pass and the
 *  matrices in one (a link's matrix stage runs as soon as no later constraint can move it or its upper link). Every
 *  stage then reads what it reads in the original's order, so the result is the original's. A true single pass
 *  (cloth_k_step_onepass: each link moved, limited, constrained and oriented before the next) was measured and
 *  rejected: its links' mean positions move 11 to 54 units from the original's (svc/cloth_stats.py bound: 2).
 *  cloth_k_step_passes() runs the same per-link stages in the original's pass order (the proof that the kernel's
 *  arithmetic is the original's: bit-identical on the SW back-end).
 *
 *  The arithmetic is SH4ZAM's: dot products and magnitudes through shz_dot6f / shz_mag_sqr3f (FIPR on the SH4),
 *  normalisation through shz_inv_sqrtf_fsrra (FSRRA), square roots through shz_sqrtf_fsrra, angles through
 *  shz_acosf / shz_asinf and shz_sincosf (FSCA). On the SW back-end each of these is formed exactly as the C library
 *  forms it (cloth_kernel_test.c checks every one bit for bit), and the transcendental functions are the C library's.
 *  The volume tests (penClothAtCk, penClothAtCkBorder, penClothAtCkParallel) are native too.
 *
 *  \author lane eng-svc3 (RE4 Dreamcast engine line)
 *  \copyright MIT
 */
#ifndef CLOTH_KERNEL_H
#define CLOTH_KERNEL_H
#include <stdint.h>
#include "pres_rng.h"

#ifdef __cplusplus
extern "C" {
#endif

#define CLOTH_K_NONE 0xFF

typedef struct ClothKVec {
    float x, y, z;
} ClothKVec;

//! A link: the native cloth service's ClothLink (64 B: two operand-cache lines).
typedef struct ClothKLink {
    ClothKVec pos, oldPos, speed, nrm;
    float len;
    uint8_t bone, up, hit, fix;
    uint8_t side[4];      //!< left, right, up-left, up-right links (CLOTH_K_NONE)
    uint32_t pad;
} ClothKLink;

//! A link's cold record: ClothCold (48 B).
typedef struct ClothKCold {
    ClothKVec dir;
    float dist[4];
    ClothKVec fixPos;
    uint32_t pad[2];
} ClothKCold;

//! A collision volume: the layout of PenAt (0x84 B), as the service builds them each tick.
typedef struct ClothKVol {
    int type;             //!< 0 sphere, 1 cylinder
    float mat[3][4];      //!< cylinder space -> world
    float inv[3][4];      //!< world -> cylinder space
    ClothKVec p0, p1;
    float r, len;
} ClothKVol;

//! A volume as the link tests read it (lane eng-cloth1): its centre and radius, 16 B, made once a tick from the
//! ClothKVol list (whose 0x84-byte stride puts the two fields a test reads on two cache lines).
typedef struct ClothKSph {
    float x, y, z, r;
} ClothKSph;

//! One chain's tick.
typedef struct ClothKStep {
    ClothKLink* link;
    const ClothKCold* cold;
    uint32_t n;              //!< links stepped
    uint32_t variant;        //!< 1 PenClothMove, 3 PenClothMove3
    uint32_t flags;          //!< PenCloth::Flag
    uint32_t bundle;         //!< constraint passes (PenCloth::Bundle_num)
    float stretchy;          //!< Move3
    float gravity;
    const float* pGravity;
    float rate;
    const float* pRate;
    const float* pMax;       //!< angle limits (0: none)
    float floorY;
    ClothKVec move;          //!< the root's motion this tick, already scaled (Move_rate)
    int integrate;           //!< 0: Flag 0x20 (no motion step)
    int noGravity;           //!< control
    /* wind (Move1, Flag 0x200 with wind rates): per-link factors precomputed by the caller */
    int wind;
    float spdLen;
    ClothKVec mpos;
    const float* windAng;    //!< per link: sin(phase) + 1, or 1 without phase table (0: none)
    const float* pWindRate;
    float windScale;         //!< 2 under the wind control, else 1
    /* the debug wind (pG->Debug_flg[0] & 0x200) */
    int debugWind;
    ClothKVec globalWind;
    /* bones: the skeleton service's world position rows and world records (SkelBone, 16 floats a bone) */
    float* wx;
    float* wy;
    float* wz;
    float* boneMat;
    /* volumes */
    const ClothKVol* vol;    //!< 0: none this tick
    uint32_t nVol;
    PresRng* rng;            //!< the chain's presentation stream
    /* filled by the kernel at the start of the tick (lane eng-cloth1) */
    const ClothKSph* sph;    //!< the volumes' centres and radii, in the volume list's order
    uint32_t cylMask;        //!< bit i: volume i is a cylinder (never skipped by the parallel test's bound)
} ClothKStep;

//! One tick, the service's default: the original's stages with passes fused where the order allows it (exact).
void cloth_k_step(ClothKStep* s);
//! One tick in the original's pass order (the exactness proof; RE4_SVC_CLOTH_PASSES=4).
void cloth_k_step_passes(ClothKStep* s);
//! One tick in one pass (every stage of a link before the next link): measured and rejected (RE4_SVC_CLOTH_PASSES=1).
void cloth_k_step_onepass(ClothKStep* s);

//! The border volume test, native (the original's pendulum.cpp arithmetic). The plain and the parallel volume tests
//! are the kernel's own (they read the tick's ClothKSph table).
int cloth_k_at_ck_border(ClothKVec* pos, const ClothKVec* up, const ClothKVol* vol, uint32_t n);

//! Counters of the kernel (test and cost indicator).
typedef struct ClothKCounters {
    uint32_t links, passes, normalize, sqrt, acos, rotations, vol_tests, vol_hits;
    uint32_t vol_skips;      //!< parallel sphere tests ended by the reach bound (counted in vol_tests)
} ClothKCounters;
extern ClothKCounters cloth_k_cnt;
//! The control of the parallel test's reach bound: the bound 40 units short (must change the links).
extern int cloth_k_control_bound;

#ifdef __cplusplus
}
#endif
#endif
