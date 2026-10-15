/* sh4_approx.c: SH4_APPROX_RENDER / SH4_APPROX_LOGIC (game30.mk; lane approx 2026-10-15). NOT bit-exact.
 *
 * Contributed approach: Bruceleeto measured both kernels as gains on his fork (github.com/Bruceleeto/re4dc,
 * dreamcast-port 8e769a9dd8 "re4dc_sh4_MTXConcat via SH4ZAM XMTRX" and fe2aed7945 "re4dc_sincosf through sh4zam
 * (FSCA)"). His note: "To gain from sh4zam you need to be happy with approximations." Here they sit behind two knobs
 * instead of replacing the exact kernels: render-only call sites (include/dolphin/mtx.h RE4DC_RENDER_MTXConcat /
 * RE4DC_RENDER_MTXRotRad) take them with SH4_APPROX_RENDER=1; SH4_APPROX_LOGIC=1 also binds PSMTXConcat itself to
 * re4dc_shz_MTXConcat (ps_alias_sh4.ld) and gives re4dc_sincosf the FSCA path (game30_trig.c).
 *
 * SH4ZAM (MIT, third_party/sh4zam, pin 0fd3a1e1 v0.9.0): shz_xmtrx_load_cols_4x3 + shz_xmtrx_transform_vec4 (one
 * FTRV per row) and shz_sincosf (ftrc of x * 65536 / 2 pi, then FSCA: 1/65536-turn steps, truncated).
 *
 * re4dc_shz_MTXConcat: ab = a x b for 3x4 row matrices. XMTRX columns = b's three rows and (0 0 0 1); each row of a
 * (a_i0 a_i1 a_i2 a_i3) through FTRV gives ab's row i, translation included (a_i3 x 1). ab may alias a or b: b sits in
 * XMTRX before any store, and each row of a is read before its own row of ab is written. XMTRX is clobbered (the
 * game's FTRV users load it for themselves before each use).
 * re4dc_shz_MTXRotRad: PSMTXRotRad with sin / cos from FSCA for |x| <= 0x43490f80 (~201 rad); larger, inf and NaN
 * keep the exact re4dc_sincosf (its sincosf_big path), as fe2aed7945 does. */
#include <stdint.h>
#include <string.h>
#include <sh4zam/shz_xmtrx.h>
#include <sh4zam/shz_trig.h>

typedef float Mtx34[3][4];

void PSMTXRotTrig(float (*m)[4], char axis, float sinA, float cosA);
void re4dc_sincosf(float x, float* s, float* c);

void re4dc_shz_MTXConcat(const float (*a)[4], const float (*b)[4], float (*ab)[4])
{
    shz_xmtrx_load_cols_4x3((const shz_vec4_t*)b[0], (const shz_vec4_t*)b[1], (const shz_vec4_t*)b[2]);
    for (int i = 0; i < 3; i++) {
        shz_vec4_t r = shz_xmtrx_transform_vec4(shz_vec4_init(a[i][0], a[i][1], a[i][2], a[i][3]));
        ab[i][0] = r.x;
        ab[i][1] = r.y;
        ab[i][2] = r.z;
        ab[i][3] = r.w;
    }
}

void re4dc_shz_MTXRotRad(float (*m)[4], char axis, float rad)
{
    uint32_t ix;
    float s, c;
    memcpy(&ix, &rad, 4);
    if ((ix & 0x7fffffffu) > 0x43490f80u) {   /* large, inf or NaN: exact */
        re4dc_sincosf(rad, &s, &c);
    } else {
        shz_sincos_t r = shz_sincosf(rad);
        s = r.sin;
        c = r.cos;
    }
    PSMTXRotTrig(m, axis, s, c);
}
