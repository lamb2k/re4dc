# Lane eng-e1j: the camera as one native service, no per-tick conversion

Branch `lane/eng-e1j` from `engine` 736751764. Brief: `E:\RE4DC-Lanes\eng-e1j\BRIEF.md`. Answers the second E1 audit
(`E:\RE4DC-Lanes\audit-e1b\AUDIT-E1B.md` sections 2, 3, 6; rulings H-016.1 and H-016.2). Status: finished, unaudited
(per item below).

## 1. The camera units, function by function

Rule used to sort them. A **decision** chooses: a camera mode, a cut, a routine, a target or offset table, a site, a
state, or the target and eye a routine wants from the player's state and the stick. A **service** evaluates: it
blends or smooths camera parameters, fits, evaluates or searches a spline, tests containment, probes lines of sight,
builds a frame or a matrix, or relocates and reads the camera data. Debug drawing is a logged stub. The default image
links 63 camera functions (FIGHT=1 links 83: the binocular camera and four cam_sys helpers more); every one is below.

### cam_ctrl (the controller)

| Function | Bytes | Kind | Why |
|---|---:|---|---|
| CamCtrlShoulderSetAim, CamCtrlShoulderSetSearchFrame | 20, 12 | decision | setters of the shoulder camera's aim and delay |
| CameraControl::CalcAim | 84 | decision | the aim point: player plus the cut's offset |
| CameraControl::Check | 436 | decision | area check, attach check, the fall camera's state |
| CameraControl::CoreDataRead, RoomDataRead | 36, 56 | decision | install the data (call the relocation) |
| CameraControl::LerpDataSearch | 92 | decision | which blend record a transition uses |
| CameraControl::LowerBinocular, endScope, startPushObject, endPushObject | 144, 156, 56, 168 | decision | mode changes |
| CameraControl::Move, Move [clone .part.0] | 52, 760 | decision | runs the routine of r0, then hands the result to the blend, the smoothing and the frame (services) |
| CameraControl::areaHitCheck | 1076 | decision | which area and cut is active (calls the containment test) |
| CameraControl::checkAttachCamera, registAttachCamera, deleteAttachCamera | 524, 100, 56 | decision | which motion-attached camera holds |
| CameraControl::getCameraDirection, getCameraPitch, resetCameraAngle, getTrajectory | 16, 4, 16, 68 | decision | getters and resets of decision state |
| CameraControl::r0_Debug, r0_Fix, r0_Free, r0_Pan, r0_RailBehind, r0_RailPan, r0_Track | 788, 180, 1540, 304, 3016, 372, 324 | decision | each routine chooses its eye and target from the player and the stick (they call the rail, probe and smoothing services) |
| CameraControl::roomInit, switchCamera | 596, 992 | decision | room start; the cut switch picks the routine |
| CameraControl::Comeback, CutCall, HoldBinocular, IsMotionEnd, SetBinocularRange (FIGHT=1) | 64, 144, 116, 36, 16 | decision | script calls and mode changes |
| **CameraInterpolation::move** | 264 | **service** | blends eye, target, roll, fov over the remaining frames |
| **CameraSmooth::move** | 300 | **service** | quake compensation and exponential smoothing |
| **areaHit** | 184 | **service** | containment of a position in an area (facing range, then the polygon test) |
| **area_hit_p3, area_hit_pN** | 316, 376 | **service** | point in polygon (cross products; crossing count) |
| **cameraHitCheck** | 864 | **service** | the camera's line-of-sight probe: three collision queries, the nearest hit, the partner's cylinder |
| **searchRail** | 528 | **service** | the rail parameter nearest the aim point |
| **CameraControl::calcAddr, cameraDataVersion** | 384, 376 | **service** | relocation of the camera data file, its version read |
| HermiteExport, Parametrize, BSpline, debugDrawRail | (native since eng-svc4) | service | rewritten in this lane (section 2) |

### cam_qfps (the shoulder camera)

| Function | Bytes | Kind | Why |
|---|---:|---|---|
| bindAreaCamera, bindDefaultCamera | 464, 168 | decision | which offset table each type uses |
| calcDepressionRatio | 240 | decision | pitch and yaw look angles from the weapon and the stick |
| checkCameraType | 648 | decision | the transition and ready types from character and weapon |
| init, setAreaData, setBlendCount, setBlendData, setFloorRatio, setPlayerLocation | 204, 668, 24, 180, 12, 44 | decision | state and table set-up |
| move | 1256 | decision | chooses the site and composes the services below; its lateral follow rate (lr_rate) is a tuning rule kept with it |
| **calcBaseMatrix** | 1256 | **service** | the player-space frame: search delay, overrides, floor tilt, crouch drop |
| **calcOffset** | 932 | **service** | blends the offset tables (old to new, up / mid / down by pitch), turns them by the yaw |
| **hitCheck** | 2216 | **service** | the wall probe: three lines from the close point, the nearest hit, the frustum-edge probes |
| **offsetCorrection (both)** | 252, 100 | **service** | keeps each table's close point behind the player |

### cam_extra and cam_sys

| Function | Bytes | Kind | Why |
|---|---:|---|---|
| CameraAttachedToMotion ctor / dtor, CameraLookAt ctor / move / dtor, CameraPushObject ctor / move / dtor | 20 to 924 | decision | each picks its eye and target (the hand it looks at, the push direction, the door to swing round); they call the probe service |
| CameraBinocular ctor / move / setRange / dtor (FIGHT=1) | 652, 776, 36, 76 | decision | the binocular's zoom and aim from the stick |
| CameraAttachedToMotion::move | (native since eng-svc4) | service | rewritten in this lane |
| **IdBinocular::init / move / quit / dtor, IDApplication::init, FocusAnimation::move** (FIGHT=1) | 344, 1412, 204, 4, 4, 212 | **service** | the binocular's ID widget and the focus blur: drawing, not camera decisions |
| **cam_sys, every function** (CameraGetRoll, CameraRotAxisPosRad, CameraSetOrientationZeroRoll, CameraTargetRot in FIGHT=1; the rest unlinked or native) | 132, 108, 648, 212 | **service** | orientation, roll, turns, dolly, distance: camera maths; the unit is no longer allowed |

### Debug

| Function | Bytes | Kind | Why |
|---|---:|---|---|
| **scrHitCheck(cPlayer*) [clone .part.0]** (pl_debug) | 256 | **service** | a scenery ray drawn as debug lines: a logged stub |

### The gap made visible (control)

`allowed_original.txt` now refuses the services above (exception lines, cam_sys not allowed). The baseline maps
(`engine` 736751764 built unchanged, `/dev/shm/eng-e1j/base-*`) against the new list (evidence
`E:\RE4DC-Lanes\eng-e1j\ev\item1`):

| Image | Before (old list) | Baseline map, new list |
|---|---|---|
| default | PASS, SERVICE 0 of 399 | **FAIL**, SERVICE 15 (8,604 B): the 14 camera services and scrHitCheck |
| SENDABLE=1 | PASS, SERVICE 0 of 399 | **FAIL**, SERVICE 15 (8,604 B) |
| FIGHT=1 | FAIL, SERVICE 109 (41,580 B) | FAIL, SERVICE 134 (53,464 B): 25 camera / debug more |
| BOSS=1 | FAIL, SERVICE 58 (18,796 B) | FAIL, SERVICE 73 (27,400 B): 15 more |
