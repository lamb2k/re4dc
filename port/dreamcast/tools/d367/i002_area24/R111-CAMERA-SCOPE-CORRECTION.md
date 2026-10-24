# r111 camera scope correction (append-only)

This supplements e2d53b3d8; old source/receipts remain unchanged. Static current ROOM CAM absence13/14 is authenticated. A claim that the predicate is globally unreachable is NOT established and must not be inferred from that static table.

At frozen78cbd962e:
- CameraControl::CutCall (src/game/cam_ctrl.cpp:564-584) searches the active data's existing area-linked cuts; it logs/refuses a missing number rather than synthesizing one.
- UpCutCall at2329-2348 can switch active data to pG->pCamCore (sel0) or pG->pCamRoom (sel1), then invoke CutCall. The actual t_camera editor callers at1855/1857 select those paths. Core CAM contents and live editor enablement were not qualified in this audit; this is an alternative namespace capability, not proof that an r111 play session reaches13/14.
- RoomDataRead at363-367 replaces the installed room camera data. t_camera's g_pToolCamData callers (105,1877,1923,2825,2932,2967) provide a source path for replacement/edited data. This audit does not prove complete dynamic cut-construction behavior or build/runtime reachability of every editor path.
- Bounded source grep found cameraNo assignments in cam_ctrl only: switchCamera copies cut->camera_no at662 and area/reset paths assign-1. No external direct CamCtrl.cameraNo assignment or cut->camera_no write was found by that search. Pointer aliases, external/event data and every linked-code path have NOT been exhaustively proved absent.
- MotionSet at2504 drives a CameraMotion and flags/parameters without assigning cameraNo. Parameter override is therefore not automatically a new CurrentCameraNo identity.
- R111Main has no local CutCall/UpCutCall call. Its CH22 source predicate reads CurrentCameraNo, then on13/14 hides group1e on an outside-to-inside flag transition; otherwise it restores the group on an inside-to-outside transition (r111.cpp176-189). The original PS2 module has not been newly redisassembled here.

Update order: gameMainLoop calls ScenarioMove at game.cpp809, which calls RoomData.execMainFunc at sce_sys.cpp160 before EvtMgr.Run and SceSys.scheduler. R111Main therefore runs before the ordinary later CameraMove Check/Move at game.cpp852 / camera.cpp113-115. It normally sees the previous controller identity, not a fresh same-frame player-area test. Item/pause/status/debug gates may skip the room main. This does not establish every scheduler/override timing path.

The two-part repair blocker remains, with precise scope: repeated group1e has no common unique-ID binding; original PS2 room cut13/14 has no direct counterpart in the CURRENT STATIC ROOM CAM. Any faithful successor must authenticate the active room/core/editor namespace and transition/update semantics as well as the repeated group's visibility. Blind forwarding, an invented player-area proxy, or treating arbitrary core/editor cut13/14 as PS2 room visibility is unsafe. No runtime implementation is ready or authorized by this correction.
