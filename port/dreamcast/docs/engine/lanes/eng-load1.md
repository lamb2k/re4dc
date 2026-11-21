# Lane eng-load1: room-to-room loading through a door (2026-11-21)

Status: **finished, unaudited.** Brief: `E:\RE4DC-Lanes\eng-load1\BRIEF.md`. Hand-back: `E:\RE4DC-Lanes\eng-load1\HANDBACK.md`
(results, numbers, requests). Every number here is **Flycast** (plain build, slot std2: a function check) or PC.

## 1. How the original changes room

Line numbers are `src/` on `engine` (the same on `t15/int` for these files).

| Step | Where | What |
|---|---|---|
| The area check | `game/game.cpp:820` (`gameMainLoop`), `game/sce_at.cpp:577-664` `SceAtCheck`, `:672-808` `sceAtCheck_main` | Each tick, before `ScenarioMove` and the player's move: the player's position + 250 up and a front point 550 ahead (wall-clipped by `SatMgr.hitCheck`) are tested against every enabled AEV area whose `checkType` has the player bit (`sceAtHitCheck`, `:879`; `area.cpp:69` the quadrilateral and height band). A hit area of type 1 is a door: with trigger bit 3 it registers the action button (`ActBtn.set`), else it fires when its trigger bits match the key status (`Status_flg[0]` 0x40000000 A pressed, 0x20000000 A held; set by the player's `checkCtrl`, `pl_class.cpp:958-969`, the tick before) |
| The request | `game/sce_at.cpp:1027-1087` `sceAtFunc_door` | Ashley's veto (`CheckDoorJumpWithAshley`, message 0x67), the lock (`sceInLock` task), else: `Stop_flg` all set and the keys stopped (`KeyStop`); the door's function and argument handed to `SceSys`; `m_door_fade_eff`; `NextPos`, `NextY`; `room_id_prev`, `Part_old`; `next_stage`, `next_room_no`, `next_point`, `door_no`; **`Rno0 = 4`**; `r_continue_cnt = 0`; `System_flg` bit 6 off |
| The fade and the handoff | `game/game.cpp:1469-1545` `gameDoordemo` (routine 4) | `System_flg` 0x1000000, `Stop_flg` all, keys stopped; the fade by `m_door_fade_eff` (0: the 120-frame stop filter, `Filter09`; 1: a 15-frame fade waited for; 2: none); the door's and the exit's functions called; `Disp_flg` all; `DC.initDataUnit`, **`Dvd.ReadCancelAll`, `Aram.DmaCancelAll`, `EmReadInit`** (pending loads cancelled), `ClearOt`; the door sound loaded and waited for (`SndDoorSeLoad`, `SndNextRoomInit`), `DoorSeCall(0)`; then `sub_pos = NextPos`, `sub_angle = NextY`, `room_id = next_room`, `Part = next_point`, `JumpPoint = 0` (not on the debug jump or continue), **`Rno0 = 1`**. Several `TaskSleep` frames: the game's frame counter runs on |
| The stage step | `game/game.cpp:355-427` `gameStageInit` (routine 1) | Continue mode, the r120 costume choice, the disc of the stage (`Dvd.DiscChange`), the game time, the save (`GameSaveSave`), **`StageSet`** (`stage.cpp:218`: on a stage change the stage heap replaced and the messages re-initialised; when the room needs another REL module the room heap replaced and the module linked, `RoomData.linkRelData`; the enemy list read, `readEmList`), **`Rno0 = 2`** |
| The room archive | `game/read.cpp:252` `ReadAreaData` (from `gameRoomInit`, `game.cpp:536`) | `stX/rNNN.das` read to the heap's top and Yz2-decoded into `pG->pRoom` on the iTask; `RTP`, `MDT`, `OSD`, `EMI` pointers set |
| The old port's hooks | `t15/int` `src/game/stage.cpp:231` `re4dc_room_leave` (before `StageSet` overlays heap 4), `game.cpp` `gameRoomMemInit` -> `port/dreamcast/game/ui_bridge.cpp:543` `re4dc_room_enter` (after heap 4 is replaced: packages, warp rig, GC-ASSET, room data file); `read.cpp` native path: the decoded little-endian `stX/rNNN.dar` read through the synchronous DVD shim (`platform/dvd.cpp`) | The old port runs the original routines 4, 1 and 2 as they are; its own room work hangs off these two hooks. The engine runs none of routines 4, 1, 2: it answers routine 4's request itself |
| What is freed | `game/game.cpp:1559-1610` `gameRoomMemInit` (first in `gameRoomInit`) | The room heap replaced (`MemReplaceHeap(3, 4)`: every room record, manager array and room allocation goes with it); the room part of the global work cleared (`pad_16C`, 0x4E00 bytes: `Stop_flg`, room flags, the room data pointers `RoomMes` .. `pOsd`); `Debug_flg[0..1]`, `Status_flg[0..2]` cleared. The core archive (`pArc`), the player and weapon archives stay |
| What is loaded, in order | `game/game.cpp:509-791` `gameRoomInit` (routine 2) | `ReadPlayerData`, `ReadAreaData` (the room data pointers), `ConsInitRoom` (the room's counts), every manager's `roomInit` and `arrayAlloc` sized by the counts (models, parts, enemies, objects, sprites, controllers, lights, damage), lights, effects, primitives, SAT and EAT collision, the areas (`SceAtInit` over AEV and ITA), events, **the player (`EmMgr.create(0, 0)` at `sub_pos`)**, scenery, shadows, effects, item and etc models, cloth, the camera (`CameraRoomInit`, room and core camera data, `CamCtrl.roomInit`), `View.roomInit`, blocks, the enemy set (`EmSetRoomInit`, `RoomData.initRoomSet`), sound, items, sub screen, HUD, BGM, `ScenarioRoomInit` (the room script), the fade in, `RoomData.setPassed`, `DoorSeCall(1)`, `SubScreenWait(15)`, **`Rno0 = 3`** |
| The door's event | `sce_at.cpp:1064-1068`, `game.cpp:1502-1512` | A door may carry a room-script function (`doorFunc`, `doorArg`), called by `gameDoordemo` after the fade-out. The DOOR scene's two doors have none (checked on the records; `core/room_change.cpp` refuses a door that has one) |

## 2. What the engine supplies, and what stays hosted

- **Hosted (the decision):** that a room change happens and where to (the door handler's request: `pG->Rno0 == 4`
  and the destination fields). In the default image the area check itself is not linked (request R1): the DOOR scene
  plants the request from the room's own AEV record at the fixture's tick (a logged stub, `E1 STUB SceAtCheck(door
  request planted: R1)`), and `tools/plays_right/door_check.py` checks each planted request against the record on the
  reference's trace.
- **Engine (services):** the loading state (`core/room_change.cpp`, `core/frame.cpp` `e1_loading_begin / _end`):
  disc access counted as loading, the picture held, play untimed; the room's memory returned (skeleton tables through
  `cModel::releasePartsList`, the collision service's release entry (R2), the renderer's pack entries (R3), the room
  archive, the room heap made again); the next room loaded and set up in `gameRoomInit`'s order (`core/main.cpp`
  `room_init`); the memory map sampled after each load; the read-safety layer under every disc read
  (`core/disc_safe.c`).
- **Re-expressed decision statements** (the handoff `gameDoordemo` and `gameRoomMemInit` make; for the integrator's
  ruling, as H-017.10 asks): listed at the head of `core/room_change.cpp`.
- **Not supplied (not hosted in E1):** the fade (effects not drawn), the door sound, `Dvd.ReadCancelAll` (the engine
  has no reads in flight in play), the disc change, the save, the room script and the enemy set of the new room.
