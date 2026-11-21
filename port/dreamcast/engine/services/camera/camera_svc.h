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
    u32 keys;          // lane eng-e1n: part-frame decodes (one a frame and part of a converted track)
    u32 key_errors;    // lane eng-e1n: tracks not played (keys not accepted, the store full, an export refused),
                       // frames without a row, and cut exports refused (HermiteExport)
    u32 conversions;   // lane eng-e1p: tracks converted (at room load, and by a CameraMotion made on a file)
    u32 play_conversions;   // lane eng-e1p: of those, converted during play (the selector fails a timing scene on one)
    u32 lookups;       // lane eng-e1p: cut switches served by the room's converted track (no export, no conversion)
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
// push-object camera's player-frame inverse skipped (the identity). Lane eng-e1p: 9 "camlate": a CameraMotion made on a
// refused export checks the refusal after it has read the header, taken the lease and relocated the key table (the order
// before lane eng-e1p; the exercise camrefuse's stale-table case must fail).
extern int cam_control;
// The camera track store (lane eng-e1n, camera_svc.cpp): bytes in use, the most at once, its size.
void cam_track_store_use(u32* now, u32* peak, u32* size);
// Lane eng-e1p (H-018.1): the room's camera tracks, converted when the room is loaded. cam_track_room_load exports and
// converts every motion cut (type 6 or 7) of the room's and the core's camera data (relocated: after RoomDataRead and
// CoreDataRead) into the room store, allocated now to the bytes they need; it returns 0, or -1 when the room's tracks
// pass the room store's ceiling (cam_track_limit, 64 KiB), its 56 cuts, or the store cannot be allocated (nothing is
// converted then; the caller refuses the room). cam_track_room reports the last room: motion cuts, tracks converted,
// cuts refused (writer or keys), the bytes the room needs and the store's limit.
int cam_track_room_load(const void* room_cam, const void* core_cam);
void cam_track_room(u32* cuts, u32* tracks, u32* refused, u32* bytes, u32* limit);
// Lane eng-e1p: play brackets (core/frame.cpp: the first to the last picture): a conversion between them is counted as
// a conversion in play. Lab arms read before play: CUTCONV (the cut switch converts as before: the control of the
// conversions-in-play check), CAMSTORE (the store's limit set to `limit` bytes: the control of the room refusal).
void cam_track_in_play(int on);
extern int cam_track_cut_convert;
extern u32 cam_track_limit;
}
