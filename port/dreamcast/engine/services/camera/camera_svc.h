// Native camera service (lane eng-svc4; camera_svc.cpp, docs/engine/SERVICES.md section 28): the frame's camera
// (CameraMove: the controller's decision taken, then the projection, the look-at matrix and the frustum), the view
// frustum (VIEW: planes, corners and bounding sphere, camera and world space), the orientation matrices
// (CameraSetOrientationRoll / Up), the keyed camera tracks (CameraMotion and the Hermite key evaluator), the camera
// attached to a motion, and the rail spline (HermiteExport, Parametrize, BSpline). Engine bodies for the entry points
// of view.cpp, camera.cpp, cam_motion.cpp and motion.cpp's HermiteInterpolation, and for the evaluation functions of
// cam_ctrl.cpp, cam_sys.cpp and cam_extra.cpp; the camera's decisions (which camera, modes, rails, areas, targets)
// stay the hosted controller's.
#pragma once
#include "types.h"

struct CameraCounters {
    u32 frames;        // CameraMove calls
    u32 frustums;      // frustum rebuilds (initPerspective)
    u32 orients;       // frustum orientations (VIEW::orientation)
    u32 orient_cams;   // camera orientation matrices (Roll + Up)
    u32 tracks;        // keyed camera track evaluations (CameraMotion::move)
    u32 keys;          // Hermite key evaluations (HermiteInterpolation, three axes each)
    u32 key_errors;    // of those, with an invalid key history
    u32 attached;      // attached-camera evaluations
    u32 rails;         // rail exports + fits + evaluations
    u32 projections;   // projection loads (CameraSetProjection: the renderer reads pG->Cam.ProjMat)
    u32 debug_draws;   // debug rails (counted, not drawn)
};

extern "C" {
extern CameraCounters cam_cnt;
// Controls (re4ref, RE4_SVC_CONTROL): 1 "camfov": the frustum built for a field of view 1 degree wider; 2 "camroll":
// the roll orientation turned 0.01 rad further.
extern int cam_control;
}
