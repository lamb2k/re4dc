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

## 3. The loading state, memory and the round trip

`CONSOLE_LOOP.md` section 14 (the state and its record), `SERVICES.md` section 50 (what each service returns). Flycast
(plain build, slot std2, a function check; no timing claim), the DOOR scene, run 4 (`E:\RE4DC-Lanes\eng-load1\ev\run4`):

| Load | At tick | Time | Held fields | Loading disc: opens / reads / drive requests |
|---|---:|---:|---:|---|
| village (r101) to farm (r103) | 51 | 304,910 us | 19 | 2 / 7 / 10 |
| farm to village | 141 | 294,571 us | 18 | 2 / 7 / 10 |

Play's disc counters 0 / 0 / 0; ticks per visit 51, 90, 119. The memory marks when each room is ready:

| Mark | KOS heap in use | Behaviour arena in use | Video memory free | Collision pieces | Skeleton tables |
|---|---:|---:|---:|---:|---:|
| village, first (taken before the field counter: see below) | 9,574,000 | 524,192 | 2,639,720 | 2 | 2 |
| farm | 9,559,944 | 768,736 | 2,639,720 | 3 | 2 |
| village again | 9,574,024 | 524,192 | 2,639,720 | 3 | 2 |

Every load step returns what its room took (`E1 LOADSTEP`: the KOS heap after each step; village left at 9,574,024, back
at 9,574,024). What the round trip still shows:
- **24 B** on the KOS heap: KOS's vblank handler node (`vblank.c` `vblank_handler_add`), registered once when the
  field counter starts, after the first marks were taken (`E1 KOSGROW tick 1 +24`). The first marks now come after the
  counter's start, where every later room's are taken (commit 1153bce55; the equality is unchanged). **Run 5 (the final
  code, `ev/run5`): `E1 ROUNDTRIP rooms 101>103>101 loads 2 failed 0 kos-used 9574024/9574024 arena-used 524192/524192
  vram-free 2639720/2639720 col-pieces 2/3 skel-tables 2/2: LEAK col-pieces`**: the KOS heap, the behaviour arena and
  video memory return exactly; the collision pieces do not (R2). Loads 304,924 and 294,585 us, 19 and 18 fields held,
  2 / 7 / 10 each; play 0 / 0 / 0; plays right 260 of 260 bit-identical again.
- **Collision pieces 2 to 3**: the collision service has no release entry (R2); the village's pieces stay registered and
  its tables stay carved.
- Video memory does not move because the renderer has no pack close / reopen (R3): the farm is drawn with the village's
  pack (a logged stub). Not exercised.

Three memory faults the DOOR scene found (each failed loudly, none hung):
1. **The farm's bake beside the village** (run 2): staged as `FARM.PAK`, the bench's farm bake makes the renderer size
   its resident block 1,883,520 B larger (it sizes from `CROSS.PAK` and `FARM.PAK`); the KOS heap then reached 1,466,368 B
   into the behaviour arena before any door (199 overlaps in `E1 MEM`; LEON on the same disc: +417,792 B). Now staged as
   `R103.PAK`; the renderer's sizing is a request (R3).
2. **The room archive on the KOS heap** (run 3): the farm's compacted archive (598,368 B) could not reuse the village's
   freed block (353,824 B); sbrk grew 180,224 B past the arena's start and overwrote the new room heap's header (`ARENA
   alloc FAILED heap 4`, `E1 LOAD FAILED 0 room 101>103: player not created`). Fixed in `core/loader.cpp` as the
   original does it (`read.cpp decodeData`: the room archive on the room heap): LEON's margin 417,792 -> 774,144 B, the
   hill's 290,816 B (about 115 KB before, eng-e1p), heap 4 524,192 / 503,744 B of 2.75 MB; LEON and HILL OK.
3. **The services region** (runs 2 to 4): 1 MB = the skeleton pool (256 KB) and the carve. The village's collision tables
   take 470,240 B; the farm's two pieces need 271,008 + 599,328 B. Without a release (R2) the second farm piece is refused
   (`carve refused 599328`); even with it, pool and farm tables (1,132,480 B) are 83,904 B over the region. The farm walk
   never queried the refused piece (one refusal, no late bake), so play matched the reference; other paths in the farm
   would lack that collision.

## 4. The read-safety wrappers

`core/disc_safe.c`, `SERVICES.md` section 50. Check CDISCF (runs 2 and 4): the first DMA transfer of the first load
reported done without the transfer; `E1 DISCSAFE ... not-landed 1 fallbacks 1 latched 1`, the sector read again ("1
sectors at 514556 read again: ok"), both loads completed (run 4: 0.738 s and 0.597 s with sector reads only, 21 and 23
drive requests against 10). Every clean scene: `marked` about 1,550 DMA reads, `not-landed 0`, `latched 0`. The
stale-flag recovery and the not-ready wait are not exercised by any scene (no Flycast input makes KOS refuse a stream
request or the drive report not ready): console questions.

## 5. The DOOR scene

Fixture `tools/plays_right/fixtures/door-r101-r103.txt` (engine `/cd/DOOR.TXT` and re4ref): the village square's door to
the farm path (r101 AEV area 2, the action key) and back (r103 area 0). Tolerance stated before running: `tolerances.json`
unchanged (position 1 unit per axis, angles 1 degree, motion frame and state exact, discrete hash exact, generator exact).

| Check | Run 4 | Control (must fail) |
|---|---|---|
| Plays right (`plays_right.py`, p a mf ms ps; rng) against re4ref | **260 of 260 ticks, every field bit-identical** (both doors) | re4ref walk-speed=1.02: diverges tick 12 (1.37 units); shift-input=1: tick 10 (ps) |
| Door requests against the rooms' areas (`door_check.py`) | 2 of 2 PASS on the engine's trace and on re4ref's | early=20: FAIL (A not pressed); at0: FAIL (front point outside) |
| Both rooms ran ticks; loads; play disc 0 | 51 / 90 / 119; 2 of 2; 0 / 0 / 0 | CDOORPK (farm archive absent): FAILED "E1 load: missing /cd/st1/r103.arc", exit 1, 11 rows, no hang; CDOORRD (read 10 ticks after the door): FAILED "disc in play: opens 0 reads 1 sectors 1" |
| Round trip | run 4: LEAK kos-used 24 B (the vblank node, before the marks' fix); run 5: **LEAK col-pieces 2/3** (R2), KOS heap, arena and video memory equal | CDOORLK (4 KiB kept), run 5: FAILED LEAK kos-used, 9,574,024 / 9,578,128 (+4,104 B) |

Run 2 (before fault 2's fix, the archive on the KOS heap) diverged at tick 142: back in the village Leon stayed at y
3201.47 against 3101.38, because the returning village's collision tables were refused by the full carve.

## 6. Requests, stubs, what is not done

In the hand-back (`E:\RE4DC-Lanes\eng-load1\HANDBACK.md`): R1 the area check in the default image, R2 the collision
release and the services region's size, R3 the renderer's pack close / reopen and its resident sizing, R4 the farm pack's
HUD fix. Logged stubs: the planted door request (R1), the collision and renderer entries (R2, R3).
