// Native camera service (lane eng-svc4; rewritten by lane eng-e1j: camera_svc.cpp, cam_eval.cpp, docs/engine/SERVICES.md
// sections 29 and 48). The record the renderer reads is eng_camera.h's.
#pragma once
#include "types.h"

struct CameraCounters {
    u32 frames;        // CameraMove calls
    u32 frustums;      // frustum rebuilds (initPerspective)
    u32 orients;       // frustum orientations (VIEW::orientation)
    u32 orient_cams;   // camera frames (Roll, ZeroRoll, Up)
    u32 tracks;        // camera track reads (CameraMotion::move: one motion-key row each)
    u32 keys;          // lane eng-e1n: track rows converted (at a CameraMotion's making: one a frame and part)
    u32 key_errors;    // lane eng-e1n: tracks not played (keys not accepted, the store full, an export refused),
                       // frames without a row, and cut exports refused (HermiteExport)
    u32 attached;      // attached-camera evaluations
    u32 rails;         // rail exports + fits + evaluations + searches
    u32 projections;   // projection requests (CameraSetProjection; an orthographic one at CameraMove)
    u32 debug_draws;   // debug rails and rays (counted, not drawn)
    u32 blends;        // cut blends stepped (CameraInterpolation::move with frames left)
    u32 smooths;       // smoothing steps (CameraSmooth::move, not snapped)
    u32 areas;         // area containment tests
    u32 probes;        // line-of-sight probes (cameraHitCheck)
    u32 shoulder;      // shoulder camera frames (calcBaseMatrix)
    u32 unit_math;     // lane eng-e1n: cam_extra's matrix calls through the service (inverses, points, directions)
    u32 unit_turns;    // lane eng-e1n: of cam_extra's calls, turns about an axis (the push camera's swing)
};

extern "C" {
extern CameraCounters cam_cnt;
// Controls (re4ref, RE4_SVC_CONTROL; each must make the camera check fail): 1 "camfov": the frustum built for a field of
// view 1 degree wider; 2 "camroll": the roll orientation turned 0.01 rad further; lane eng-e1j: 3 "camsmooth": the
// smoothing off (each step snaps to its target); 4 "caminterp": the cut blend off (it snaps); 5 "camrail": the rail
// evaluated 0.25 further along its parameter. Lane eng-e1n: 6 "camslope": one key's out-tangent 1.25 times steeper in a
// camera track's conversion; 7 "camfollow": the shoulder camera's follow rate 0.5 instead of 0.6; 8 "caminv": the
// push-object camera's player-frame inverse skipped (the identity).
extern int cam_control;
// The camera track store (lane eng-e1n, camera_svc.cpp): bytes in use, the most at once, its size.
void cam_track_store_use(u32* now, u32* peak, u32* size);
}
