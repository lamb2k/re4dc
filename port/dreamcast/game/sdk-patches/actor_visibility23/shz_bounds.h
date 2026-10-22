/* Proposed generic SH4ZAM API; scalar SH4 interval assembly does not touch XMTRX. */
#ifndef SHZ_BOUNDS_H
#define SHZ_BOUNDS_H
#ifdef __cplusplus
extern "C" {
#endif
typedef struct { float lo, hi; } shz_interval_t;
/* Fail-closed: normal finite inputs or zero only. RN/RZ, PR=SZ=FR=0,
 * exception enables=0. DN may be 0/1: underflow boundary rejects either way.
 * No output is usable unless the function returns nonzero. */
int shz_bounds_mode_supported(unsigned fpscr);
int shz_bounds_point(float x, shz_interval_t* out);
int shz_bounds_add(shz_interval_t a, shz_interval_t b, shz_interval_t* out);
int shz_bounds_mul(shz_interval_t a, shz_interval_t b, shz_interval_t* out);
int shz_bounds_div(shz_interval_t a, shz_interval_t b, shz_interval_t* out);
int shz_bounds_neg(shz_interval_t a, shz_interval_t* out);
/* Row-major affine 3x4 interval matrix, interval vector (x,y,z,1). */
int shz_bounds_affine(const shz_interval_t m[12], const shz_interval_t in[3], shz_interval_t out[3]);
int shz_bounds_inverse(const float m[12], shz_interval_t out[12]);
#ifdef __cplusplus
}
#endif
#endif
