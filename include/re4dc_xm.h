// re4dc_xm.h: GAME_SH4ZAM_LOGIC (port/dreamcast/game/game30.mk; lane sh4zam-direct 2026-10-15; GAMEPLAY APPROXIMATION,
// default off). Several vectors through one GameCube Mtx with the SH4ZAM XMTRX API (third_party/sh4zam, MIT,
// Copyright (c) 2025, 2026 Falco Girgis and SH4ZAM Contributors; pin 0fd3a1e1 v0.9.0): the matrix is loaded into XMTRX
// once (shz_xmtrx_load_rows_3x4: the Mtx rows, bottom row 0 0 0 1), then each vector is one FTRV
// (shz_xmtrx_transform_point3 = PSMTXMultVec, shz_xmtrx_transform_vec3 = PSMTXMultVecSR). The SH4ZAM calls are in
// port/dreamcast/game/platform/sh4zam_direct.c (re4dc_zam_xm_*): the game's C++ units cannot include the SH4ZAM
// headers (include/cmath.h declares sinf & co. with C++ linkage).
//
//   RE4DC_XM_LOAD(m);              // XMTRX = m (clobbers XMTRX)
//   RE4DC_XM_POINT(m, &in, &out);  // out = m x (in, 1)
//   RE4DC_XM_DIR(m, &in, &out);    // out = m x (in, 0)
//
// XMTRX ownership: nothing that can reach game code (PSMTXConcat, other XMTRX users) may run between the load and the
// last transform; reload after any such call. Knob off: the macros are the PSMTXMultVec / PSMTXMultVecSR calls, so
// every call site compiles to the previous code.
#pragma once
// No includes: the call sites already declare PSMTXMultVec / Vec (dolphin/types.h would pull include/cmath.h into units
// that declare sinf themselves).
#if defined(RE4DC_SH4ZAM_LOGIC) && RE4DC_SH4ZAM_LOGIC && defined(__sh__)
extern "C" {
void re4dc_zam_xm_load(const float (*m)[4]);
void re4dc_zam_xm_point(const void* src, void* dst); // Vec
void re4dc_zam_xm_dir(const void* src, void* dst);
}
#define RE4DC_XM_ON 1
#define RE4DC_XM_LOAD(m) re4dc_zam_xm_load(m)
#define RE4DC_XM_POINT(m, in, out) re4dc_zam_xm_point((in), (out))
#define RE4DC_XM_DIR(m, in, out) re4dc_zam_xm_dir((in), (out))
#else
#define RE4DC_XM_ON 0
#define RE4DC_XM_LOAD(m) ((void) 0)
#define RE4DC_XM_POINT(m, in, out) PSMTXMultVec((m), (in), (out))
#define RE4DC_XM_DIR(m, in, out) PSMTXMultVecSR((m), (in), (out))
#endif

#if defined(RE4DC_CLOTH_XM_BATCH14) && RE4DC_CLOTH_XM_BATCH14
// Render-only cloth point rows. Both entries preflight the complete input and
// output envelopes before writing. Count is 1..100; strides are byte strides.
// Exact in-place input/output is allowed, shifted overlap is refused. The
// scalar entry preserves the current PSMTXMultVec association for comparison.
// The XM entry owns XMTRX from its one load through its last FTRV: no callback.
extern "C" {
int re4dc_zam_xm_points14_scalar(const float (*matrix)[4],
    const void* source, unsigned source_bytes, unsigned source_stride,
    void* output, unsigned output_bytes, unsigned output_stride, unsigned count);
int re4dc_zam_xm_points14(const float (*matrix)[4],
    const void* source, unsigned source_bytes, unsigned source_stride,
    void* output, unsigned output_bytes, unsigned output_stride, unsigned count);
}
#endif
