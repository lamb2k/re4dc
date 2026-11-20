// Native math helpers (lane eng-svc5): the engine's bodies for the entry points of the original units math_sub.cpp
// (orientation matrices, Euler matrices, the game's fast sin / cos / sqrt / angle wrap, interpolation, the B-spline
// basis, small dense matrices) and sub2.cpp (yaw between points, turning steps, front cones, distances, rotations,
// screen projection, line and sphere tests, parabola and stop distances). The behaviour keeps calling them by their
// original names (include/math_sub.h). Write-up: docs/engine/SERVICES.md section 32.
//
// Vector arithmetic is SH4ZAM's (shz_vec3_add / sub / scale / cross / dot / magnitude_sqr): with FIPR off (SH4ZAM's
// default) these are the SDK C bodies' operations, so the results are the original's on the PC. Matrices go through the
// engine's SDK math interface (PSMTX*). Square roots are the exact IEEE root on both machines (SSE sqrtss, SH-4 FSQRT);
// SH4ZAM's shz_sqrtf is not used: its SW back-end forms x * (1 / sqrt(x)), not the root its SH-4 back-end gives (a
// SH4ZAM shortcoming, fixed on the submodule's local branch; docs/engine/lanes/eng-svc5.md).
#pragma once
#include "types.h"

struct MathCounters {
    u32 scratch_stack;    // de_Boor_Cox / MtxNNInverse calls served from a stack scratch (no heap traffic)
    u32 scratch_heap;     // calls too large for the scratch: the heap, as the original
    u32 normalize_zero;   // zero vectors given to a normalize (logged and zeroed, as the original)
    u32 series;           // SINF / COSF evaluations (the series; low_RotMatrix's non-zero angles)
};

extern "C" {
extern MathCounters math_cnt;
// Controls (re4ref, RE4_SVC_CONTROL): 1 "mathsin": SINF / COSF without the series' x^9 term (up to 0.07 off near PI);
// 2 "mathmuku": every turning step (Muku, Muku2, Muku3) 5% larger (actors turn faster).
extern int math_control;
}
