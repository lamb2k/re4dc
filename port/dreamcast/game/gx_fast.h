#pragma once
// GC_CENSUS_TRIM=1 (lane t2exact 2026-10-15, census_trim.mk; exact, render only, default 0): the GC render census's
// GX state calls (#3) read and write gx_stub.cpp's projection / viewport words inline at the hot call sites
// (re4dc_draw_model_part, EspCommonTrans, the ID quad, the actor transaction draw, CameraCurrentProjection) instead of
// through the out-of-line stubs. The same words are copied and stored, in the same order; the viewport's
// alternate-line jitter is the same multiply then add (fp-contract off everywhere; the empty asm keeps the product
// a separate rounding even in an object built with contraction). Other callers keep the stubs.
#if defined(RE4DC_GC_CENSUS_TRIM) && RE4DC_GC_CENSUS_TRIM
#ifdef __cplusplus
extern "C" {
#endif
extern float re4dc_gxf_projection[7];
extern float re4dc_gxf_viewport[6];
#if defined(RE4DC_GXF_JITTER) && RE4DC_GXF_JITTER
extern float re4dc_res_vjitter;
#endif
#ifdef __cplusplus
}
#endif
typedef unsigned int __attribute__((may_alias)) Re4dcGxfWord;
static inline __attribute__((always_inline)) void re4dc_gxf_get_projection(float* p)
{
    Re4dcGxfWord* d = (Re4dcGxfWord*) p;
    const Re4dcGxfWord* s = (const Re4dcGxfWord*) re4dc_gxf_projection;
    d[0] = s[0]; d[1] = s[1]; d[2] = s[2]; d[3] = s[3]; d[4] = s[4]; d[5] = s[5]; d[6] = s[6];
}
static inline __attribute__((always_inline)) void re4dc_gxf_get_viewport(float* vp)
{
    Re4dcGxfWord* d = (Re4dcGxfWord*) vp;
    const Re4dcGxfWord* s = (const Re4dcGxfWord*) re4dc_gxf_viewport;
    d[0] = s[0]; d[1] = s[1]; d[2] = s[2]; d[3] = s[3]; d[4] = s[4]; d[5] = s[5];
#if defined(RE4DC_GXF_JITTER) && RE4DC_GXF_JITTER
    float t = re4dc_res_vjitter * re4dc_gxf_viewport[3];
    __asm__("" : "+f"(t));
    vp[1] += t;
#endif
}
// GXSetProjection(mtx, type): the SDK's compact form [type, m00, m02|m03, m11, m12|m13, m22, m23].
static inline __attribute__((always_inline)) void re4dc_gxf_set_projection(const float mtx[4][4], int type)
{
    float* g = re4dc_gxf_projection;
    g[0] = (float) type;
    g[1] = mtx[0][0];
    g[3] = mtx[1][1];
    g[5] = mtx[2][2];
    g[6] = mtx[2][3];
    if (type == 0) {
        g[2] = mtx[0][2];
        g[4] = mtx[1][2];
    } else {
        g[2] = mtx[0][3];
        g[4] = mtx[1][3];
    }
}
#endif
// Call-site spellings: the inline forms with GC_CENSUS_TRIM=1, the stubs otherwise (knob off: the same source).
#if defined(RE4DC_GC_CENSUS_TRIM) && RE4DC_GC_CENSUS_TRIM
#define RE4DC_GXF_GET_PROJECTION re4dc_gxf_get_projection
#define RE4DC_GXF_GET_VIEWPORT re4dc_gxf_get_viewport
#define RE4DC_GXF_SET_PROJECTION re4dc_gxf_set_projection
#else
#define RE4DC_GXF_GET_PROJECTION GXGetProjectionv
#define RE4DC_GXF_GET_VIEWPORT GXGetViewportv
#define RE4DC_GXF_SET_PROJECTION GXSetProjection
#endif
