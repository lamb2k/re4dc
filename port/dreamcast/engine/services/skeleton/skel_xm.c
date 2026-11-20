/*! \file
 *  \brief   Bone-chain matrix kernel of the native skeleton service (skel_xm.h), on SH4ZAM.
 *  \ingroup engine_skeleton
 *
 *  \author lane eng-svc (RE4 Dreamcast engine line)
 *  \copyright MIT
 */
#include "skel_xm.h"
#include "sh4zam/shz_xmtrx.h"

void skel_xm_load_3x4(const float m[12]) {
    shz_xmtrx_load_transpose_3x4((const shz_mat3x4_t*)m);
}

void skel_xm_apply_3x4(const float m[12]) {
    shz_xmtrx_apply_transpose_3x4((const shz_mat3x4_t*)m);
}

void skel_xm_apply_scale(float x, float y, float z) {
    shz_xmtrx_apply_scale(x, y, z);
}

void skel_xm_store_3x4(float m[12]) {
    shz_xmtrx_store_transpose_3x4((shz_mat3x4_t*)m);
}

void skel_xm_point3(const float in[3], float out[3]) {
    shz_vec3_t p = shz_xmtrx_transform_point3(shz_vec3_init(in[0], in[1], in[2]));
    out[0] = p.x;
    out[1] = p.y;
    out[2] = p.z;
}
