# Engine shell map (M2 groundwork, lane eng-shell-map, 2026-11-19)

Where the original behaviour code touches everything under it today, what that costs on the console, and how the engine
hosts the behaviour with no publication layer. Facts with file:line and counts. Plan: [../ENGINE_PLAN.md](../ENGINE_PLAN.md)
version 2.

**Tiers.** *console* = real Dreamcast. *Flycast* = emulator boot log. *lab33 build* = sizes and references read from the
11-19 lab33 game ELF (DWARF and disassembly); an engine build will differ, so those sizes are *estimates* for the engine.
*estimate* = everything else.

**Reproduce.** Scripts: `E:\RE4DC-Lanes\eng-shell-map\s\` (WSL `/mnt/e/RE4DC-Lanes/eng-shell-map/s/`), outputs in `s/out/`.
Run order: `c14_nml.sh` (function to file map), `pcs_decode.py`, `classify_rows.py`, `service_rank.py`, `rowtop.py`,
`boundary2.py` (from the worktree root, `PYTHONPATH=s/parser`), `callgraph.py`, `closure.py`, `codesplit.py`.
Gate: `python3 gate_doc.py SHELL_MAP.md` re-derives every number tagged `<!-- gate ... -->` from those outputs;
`python3 gate_doc.py --control SHELL_MAP.md` changes one tagged number and must report it (it does: see section 7).

## 0. Whole-frame budget rows, measured (console)

**Source.** Console PC sampler, 1000 Hz, three snaps of about 2 s per scene, slot 157 (Test 27.1-perf31 a37eb4a6),
2026-11-12, cap 4 (`E:\RE4DC-Lanes\perf30\console-20261112-ab31-slot157\*.pcs`, symbols `nmS-157.txt`). The decoder
reads the record format of `port/dreamcast/game/platform/include/pc_sampler.h:28-38` (w0 = tid and pc, w1 = flags,
stage and pr; markers are frame marks). Sample totals equal the independent symbolizer's (`pcsprof-ab31-slot157.txt`):
cross <!-- gate samples.cross=5967 -->5967, bell <!-- gate samples.bell=5972 -->5972,
hay-fork <!-- gate samples.barn-ganado=6018 -->6018, quiet <!-- gate samples.farm-quiet=3977 -->3977.

**Conversion.** ms a picture = row share of all samples in the scene x (1000 / fps of the same capture, from the
capture's own `*.summary.txt`). All threads are sampled; the CPU is busy the whole picture in these scenes.
Script: `classify_rows.py` (rules), output `out/rows.md`, every function with its row in `out/rowfuncs.tsv`.

| Scene (console) | fps | ms a picture | Behaviour | Services | Publication | Drawing | System |
|---|---:|---:|---:|---:|---:|---:|---:|
| Village cross | 18.16 | 55.1 | <!-- gate rows.cross.Behaviour=1.6 -->1.6 | <!-- gate rows.cross.Services=15.5 -->15.5 | <!-- gate rows.cross.Publication=16.3 -->16.3 | <!-- gate rows.cross.Drawing=17.8 -->17.8 | <!-- gate rows.cross.System=3.9 -->3.9 |
| Bell fight | 16.36 | 61.1 | <!-- gate rows.bell.Behaviour=1.6 -->1.6 | <!-- gate rows.bell.Services=17.9 -->17.9 | <!-- gate rows.bell.Publication=17.5 -->17.5 | <!-- gate rows.bell.Drawing=19.7 -->19.7 | <!-- gate rows.bell.System=4.3 -->4.3 |
| Farm, hay-fork view | 10.48 | 95.4 | <!-- gate rows.barn-ganado.Behaviour=1.5 -->1.5 | <!-- gate rows.barn-ganado.Services=26.3 -->26.3 | <!-- gate rows.barn-ganado.Publication=31.4 -->31.4 | <!-- gate rows.barn-ganado.Drawing=30.6 -->30.6 | <!-- gate rows.barn-ganado.System=5.6 -->5.6 |
| Farm, quiet view | 29.06 | 34.4 | <!-- gate rows.farm-quiet.Behaviour=0.7 -->0.7 | <!-- gate rows.farm-quiet.Services=13.0 -->13.0 | <!-- gate rows.farm-quiet.Publication=8.7 -->8.7 | <!-- gate rows.farm-quiet.Drawing=9.0 -->9.0 | <!-- gate rows.farm-quiet.System=2.9 -->2.9 |
| Barn inside (camera not placed: logic valid, drawing not) | 16.48 | 60.7 | 1.4 | 24.0 | 14.5 | 16.6 | 4.1 |
| **Budget (plan section 4, one tick a picture)** | 30 | 33.3 | 5 | 6 | 0 | 14 | 3 |

Unclassified samples: 0.0 ms in every scene (11 samples in 27,903).

**Behaviour and Services are paid per logic tick.** Below 30 fps the game runs more than one tick a picture
(29.97 ticks a second x speed / fps):

| Scene (console) | ticks a picture | Behaviour + Services, ms a tick | logic thread samples, ms a tick | game's own logic-phase timer, ms a tick |
|---|---:|---:|---:|---:|
| Village cross | <!-- gate ticks.cross=1.65 -->1.65 | 10.3 | 9.7 | 9.7 |
| Bell fight | <!-- gate ticks.bell=1.8 -->1.80 | 10.9 | 10.2 | 10.1 |
| Farm, hay-fork view | <!-- gate ticks.barn-ganado=2.01 -->2.01 | 13.9 | 13.2 | 12.4 |
| Farm, quiet view | <!-- gate ticks.farm-quiet=1.03 -->1.03 | 13.3 | 12.6 | 12.5 |

The logic (task) thread's sample time matches the game's own logic-phase timer (`ms10.logic` in the same capture) to
0.1 ms in three scenes and 0.8 ms at the hay-fork view: the sampler and the ms conversion are sound.

**What it says.**
- **Behaviour is small: 0.7 to 1.0 ms a tick** (about 1.6 ms a picture). The plan's estimate was about 5. The hosted
  decisions fit their row with room to spare.
- **Services are 9.4 to 13.1 ms a tick** against a budget of 6. Skeleton and collision alone are 6.7 ms a tick at the
  cross. This row, not behaviour, decides whether hosting works.
- **Publication is 8.7 to 31.4 ms a picture** (25 to 33% of every picture) in 378 functions, flat: the top 12 are
  about 30% of the row.
- **Drawing is 9.0 to 30.6 ms a picture.** At the hay-fork view it is characters (20.9 ms), not the world.

### Rules (first match wins; full table in `classify_rows.py` R[])

| Row | What goes in | Borderline rule used |
|---|---|---|
| Behaviour | Enemy AI (`cEm10::move`, `em10*` decisions), player (`cPlayer`, `pl_*`), camera (`Camera*`, `VIEW::`), events, scenario, rooms, per-object `cObjXX::move`, the rest of `src/game` | Camera is behaviour (it decides). Per-object `move` is behaviour; the walk over the object list is a manager |
| Services | Skeleton and pose (`re4dc_pwc_*`, `re4dc_pmc_*`, `Motion*`, `hermite*`, IK, cloth, `cModel::partsWorldCalc/getPartsPtr/updateOldPos`), collision (`re4dc_line_*`, `cSatMgr::`, `ObjHitCheck`, `At_*`, `cAtariInfo::`, area and floor checks), effect simulation (`EspMove`, `cEsp*::move`, `CommonMove`, `AnmMove`), managers (`cObjMgr::move`, `objMove`, `emMove`, `cEmMgr::`, `aliveCapLive`), enemy body (`getNearPoint`, `RouteCk`, `em10Neck/Waist/Slope/HandSet`), light simulation (`cLightMgr::move`, `lightMove`, `LightArea*`), HUD logic (`idSys*`, `IDSystem::move/trans`, `cMes::`) | HUD logic sits here (the HUD is a service candidate); its quads are Drawing |
| Publication | World selection (`ScenerySelector`, `sg_pick_*`, `box_class`, `dyn::`, fog and far gates, `re4dc_ps2_world_*`), model and light setup (`Trans`, `ModelTrans`, `ModelRender`, `propGate`, `cLightMgr::setModel2`, `LightSetModel`, `lightSet*`, light folds and probes `fast_only_lights` / `probe_*`, actor transaction / lease / owner / registry code, materials, `sob::`, texture-identity lookups, `re4dc_wpal_sh4` palette build, GX emulation `GX*`), effect classification and transform (`EspTrans`, `EspCommonTrans`, `Ps2fx*`, `EspSpriteEligible*`, sprite class / material), ordering tables (`clearOtWork`, `ExecOt`, `AddOt*`, `GetPrimBuff`) | World piece selection counts as publication, as the brief says, although an engine still selects at run time (from a bake). The skin palette build (`wpal`) is publication: it re-derives skinning matrices from the original skeleton. The GX emulation is publication: it translates the original's draw calls |
| Drawing | World transform and emit (`vp::transform_sched`, `walk_lean`, `ps2_pass`, `chunk_emit`, `clip_strip`), character skin and light kernels (`re4dc_avk_*`), meshlet submit (`Part::whole`, `Part::strips`, `pass_positions`, `pass_lights`, `re4dc_actor_submit`), HUD and 2D quads, store-queue and TA calls | Per-vertex light kernels are Drawing; per-part light choice is Publication |
| System | Audio thread (tid 5) and stream thread (tid 6), KOS waits and locks, OS and task-switch shims, pacer, QA link thread (tid 27), diagnostics, pad, disc, card | The QA link (0.2 to 0.3 ms) is not in a product image |
| Helpers | `memcpy`, `memset`, math (`re4dc_sh4_MTX*`, `re4dc_zam_*`, `C_MTX*`, `sqrtf`, `RotMatrix`, ...), locks | Take the row of their **caller** (the sample's PR). When the caller is also a helper (1.0 to 1.2 ms a picture), the thread decides: main thread to Publication, logic thread to Services, others to System |

Limits: a sample counts toward the function it lands in, so code inlined into a caller counts for the caller; one level of
caller (PR) is known, not the stack.

### Top functions per row (ms a picture, console; `rowtop.py`, full lists in `out/rowfuncs.tsv`)

| Row | Function | Cross | Bell | Hay-fork | Quiet |
|---|---|---:|---:|---:|---:|
| Behaviour | `cEm10::move` | 0.12 | 0.10 | 0.11 | 0.02 |
| Behaviour | `CameraSetProjection` | 0.11 | 0.09 | 0.02 | 0.04 |
| Behaviour | `em10SomebodyDamageNowCk` | 0.03 | 0.03 | 0.11 | 0.03 |
| Behaviour | `cPlayer::emSearch` | 0.02 | 0.07 | 0.05 | 0.01 |
| Services | `re4dc_pwc_ftrv_run` (part world matrices) | 1.35 | 1.58 | 2.69 | 1.40 |
| Services | `re4dc_line_leaf2` (collision leaf) | 0.93 | 1.36 | 1.85 | 1.13 |
| Services | `re4dc_pmc_run` (part local matrices) | 0.41 | 0.69 | 1.33 | 0.61 |
| Services | `EspMove` | 0.52 | 0.48 | 0.74 | 0.27 |
| Services | `re4dc_line_walk2` | 0.41 | 0.72 | 0.67 | 0.30 |
| Services | `ObjHitCheck` | 0.43 | 0.46 | 0.62 | 0.29 |
| Services | `MotionMoveCore` | 0.12 | 0.15 | 0.81 | 0.35 |
| Services | `cSatMgr::hitCheck2` | 0.37 | 0.47 | 0.44 | 0.17 |
| Publication | `ScenerySelector::chunk_select` | 1.34 | 1.07 | 0.49 | 0.15 |
| Publication | `EspCommonTrans` | 0.54 | 0.23 | 1.67 | 0.16 |
| Publication | `EspTrans` | 0.82 | 0.65 | 0.74 | 0.60 |
| Publication | `Ps2fxClass` | 0.45 | 0.50 | 1.11 | 0.48 |
| Publication | `re4dc_zam_MTXConcat` (via callers) | 0.15 | 0.14 | 1.41 | 0.03 |
| Publication | `fast_only_lights` (light fold) | 0.16 | 0.27 | 1.36 | 0.00 |
| Publication | `ModelRender` | 0.24 | 0.38 | 0.95 | 0.04 |
| Publication | `memcpy` (via callers) | 0.40 | 0.40 | 0.70 | 0.24 |
| Publication | `re4dc_ps2_world_direct_begin_batch` | 0.53 | 0.48 | 0.43 | 0.11 |
| Publication | `resolve` (image and texture identity) | 0.34 | 0.21 | 0.63 | 0.17 |
| Publication | `re4dc_actor_owned_source` | 0.07 | 0.07 | 1.05 | 0.00 |
| Publication | `Trans` | 0.41 | 0.39 | 0.33 | 0.35 |
| Drawing | `vp::transform_sched<3>` (world) | 3.29 | 3.44 | 2.76 | 0.84 |
| Drawing | `re4dc_avk_pos_skin_u16` | 2.07 | 2.47 | 2.12 | 1.93 |
| Drawing | `re4dc_avk_pos_skin_s16` | 0.48 | 0.25 | 6.58 | 0.10 |
| Drawing | `Part::whole` (meshlet submit) | 1.14 | 1.14 | 3.84 | 1.20 |
| Drawing | `re4dc_actor_submit` | 0.51 | 0.73 | 3.17 | 0.13 |
| Drawing | `vp::walk_lean` | 1.46 | 1.71 | 1.60 | 0.28 |
| System | `audio_step` (audio thread) | 0.28 | 0.23 | 0.30 | 0.14 |
| System | `genwait_wait` (KOS) | 0.32 | 0.39 | 0.52 | 0.30 |

## 1. Boundary inventory

**Scope.** Every C/C++ file under `src/` and `include/` except the SDK sources `src/lib/**` and `include/dolphin/**`.
A call site is a tree-sitter `call_expression` (a function-like macro use counts as a call of the macro);
`new`/`delete` expressions count under memory (578). Service = first name rule in `boundary2.py` SERVICES.
Status = where the lab33 ELF defines the callee (DWARF): *port shim* (`port/dreamcast/game/platform/*`),
*stub* (`gx_stub.cpp`, the GX emulation), *SDK C source* (`platform/sdk/gen`, built from `src/lib` with the
CodeWarrior asm stripped, `port/dreamcast/game/Makefile:45-48`), *original* (the game's own layer above the SDK, in
`src/game`), *macro/inline/unlinked*. Patches: `#if/#ifdef/#ifndef/#elif` lines naming `RE4DC_*` whose region encloses
a site of that service. Output `out/boundary.md`, per callee `out/boundary-funcs.tsv`, per site `out/boundary-sites.tsv`.

| Service | Call sites | Distinct callees | Files calling | port shim | GX stub | SDK C source | original layer | macro / inline / unlinked | RE4DC guard lines around sites (files) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| graphics (GX, `Render*`, `Trans`, OT, debug draw) | <!-- gate boundary.graphics.sites=4732 -->4732 | <!-- gate boundary.graphics.distinct=175 -->175 | 140 | 9 | 96 | 3 | 45 | 22 | 63 (12) |
| memory (heaps, `MEM_ALLOC`, new/delete, cache ops, ARAM) | <!-- gate boundary.memory.sites=1409 -->1409 | 57 | 396 | 16 | 0 | 7 | 29 | 4 | 80 (53) |
| files and disc (`DVD*`, `Dvd*`, `DVD_READ_N`, `Block`) | <!-- gate boundary.files_and_disc.sites=117 -->117 | 34 | 36 | 15 | 0 | 0 | 6 | 13 | 3 (3) |
| audio and movie (`Snd*`, `AX*`, Sofdec) | <!-- gate boundary.audio_and_movie.sites=3758 -->3758 | 316 | 261 | 84 | 0 | 0 | 178 | 54 | 7 (3) |
| pad (`PAD*`, `Pad*`) | <!-- gate boundary.pad.sites=20 -->20 | 11 | 8 | 7 | 0 | 0 | 4 | 0 | 0 (0) |
| memory card (`CARD*`, `Card*`) | <!-- gate boundary.memory_card.sites=78 -->78 | 28 | 13 | 17 | 0 | 0 | 7 | 4 | 1 (1) |
| math (`PSMTX*`, `PSVEC*`, trig, `RotMatrix`, `fRand*`) | <!-- gate boundary.math.sites=9322 -->9322 | 99 | 341 | 18 | 0 | 13 | 44 | 21 | 83 (27) |
| timing (`OSGetTime`, VI retrace, `GetSystemVcnt`, `ProcessTick*`) | <!-- gate boundary.timing.sites=90 -->90 | 22 | 14 | 11 | 0 | 0 | 8 | 3 | 6 (4) |
| threads (`OS*Thread`, semaphores, interrupts, `Task*`) | <!-- gate boundary.threads.sites=389 -->389 | 34 | 67 | 15 | 0 | 0 | 16 | 3 | 10 (6) |

Biggest callees (`out/boundary-funcs.tsv`): graphics `Draw_line3d` 256 (debug), `GXPosition3f32` 220, `GXSetVtxAttrFmt`
195, `GXSetVtxDesc` 193, the TEV setters 113 to 140 each; memory `new/delete` 578, `MEM_CALLOC` 145, `Mem_free` 144,
`MEM_ALLOC` 136, `Debug_alloc` 83; files `DVD_READ_N` 32, `DvdReadN` 22; audio `SndCall` 2349, `SndStop` 309,
`SndStrReq` 176; pad `PadCheckStatus` 5 (the game reads the `Joy[]`/`Key` arrays directly rather than calling);
card `cardMesSet` 25, `CARDGetResultCode` 9; math `PSMTXMultVec` 1165, `PSVECAdd` 904, `PSVECScale` 680, `LIMIT_ANGLE`
560, `fabsf` 546, `TransMatrix` 426, `fRand1_1` 341; timing `ProcessTickGet` 24, `GetSystemVcnt` 16; threads
`TaskSleep` 133, `TaskExit` 51, `OSRestoreInterrupts` 31.

**Patches into original files.** All `RE4DC_` conditional lines in scope: <!-- gate guards.lines=2537 -->2537 in
<!-- gate guards.files=226 -->226 files (`boundary2.py`; `rg` over all of `src`+`include` gives 2557 in 229, `s/c25_guards.sh`),
naming 404 distinct `RE4DC_` macros. Original code also calls 1,802 `re4dc_*` hooks (569 distinct) (`c25_guards.sh`).
Most patched: `trans.cpp` 344 lines, `esp_sub.cpp` 229, `atari.cpp` 122, `at_mod.cpp` 88, `em_set.cpp` 80, `cloth.cpp` 74,
`read.cpp` 73, `espgen45.cpp` 57, `esp.cpp` 56, `main_mem.cpp` 54, `event.cpp` 54, `espgen.cpp` 54 (`c54_topguards.sh`).
The patches sit in the publication and service files, not at the SDK boundary: the guard lines enclosing an SDK or
service call site total at most 253 (a line can enclose sites of two services), a tenth of the 2,537.

**What already exists below the boundary.** The GX emulation `gx_stub.cpp` (386 lines, 109 GX functions,
`c50_port.sh`); KOS-backed OS, DVD, pad, card, VI, audio shims in `port/dreamcast/game/platform/` (67 `.cpp`);
the SDK math built from `src/lib` (`Makefile:45-48`, units `mtx mtxvec mtx44 vec quat OSAlloc`). The old port is 466
source files, 136,172 lines, 1,201 build knobs in `Makefile` and `*.mk` (`c50_port.sh`). Code in the lab33 ELF:
original 1,618,354 B, port 696,032 B, KOS and newlib 240,856 B (`c50_port.sh`, lab33 build).

## 2. The frame

**Today** (`src/game/main.cpp:277` `main`, loop at `:326`). One iteration is one logic tick; the pacer may skip the
drawing of an iteration but never its logic (`main.cpp:337-339`).

1. `re4dc_pace_begin` (draw or skip this iteration), `Render_before`, `ClearOTagR(MainOt)`, `PadRead`, `DebugControl`,
   `Render()` (render set-up, `:357`), `SetPrimBuffPtr`, `ClearOt`, `pG->Frame_cnt++`.
2. **`TaskScheduler()`** (`:367`; `src/game/scheduler.cpp:127`). Each task is an OS thread (`OSCreateThread`
   `scheduler.cpp:172`) that the main thread resumes and then waits for until it calls `TaskSleep` (`:331`) or exits:
   cooperative threads on KOS. The game task runs `gameMainLoop` (`src/game/game.cpp:798`), in this order:
   `UpdateNearClipDist`, `gameStopMove`, `CamCtrl.Check`, `SceAtCheck`, `ScenarioMove`, **`EmMgr.move`**,
   `EmListWaitDelete`, **`pPL->move`**, **`ObjMgr.move`**, `CtrlMgr.move`, `CameraMove`, `EffAreaUpdate`,
   `EspgenMove`, **`EspMove`**, `EspGenLoopMove`, `LightMgr.move`, `DmgMgr.move`, `SatMgr.dieCheck`, `EatMgr.dieCheck`,
   ..., `LightAreaUpdate`, `Cckpt.move`, `SubScreenCall` (`c52_gml2.sh`). Skeleton, collision and effect simulation run
   **inside** these moves, called synchronously by the behaviour (the logic thread in section 0).
3. `IdSys.move`, `IdSys.trans` (HUD), then **`Trans()`** (`src/game/trans.cpp:1236-1468`, 232 lines): `EspTrans`,
   `EspgenTrans`, `CtrlMgr.trans`, `ShadowTrans`, cloth draw, then a walk of `ObjMgr.pAlive` and `EmMgr.pAlive` calling
   each model's trans function (`:1403`, `:1410`, `:1432`): `ModelTrans` / `ModelRender`, which is where the port's
   source visibility, materials, skin and OT order run. This is the publication layer.
4. `Dvd.Watcher`, `SndWatcher`, `FadeControl(0)`, `cMes.Move`, `cMes.Trans`, `CinescoMove`, `Draw_cinesco`,
   `FadeControl(1)`, `DrawOTag(&MainOt[4])`, log, `iTaskScheduler` (interrupt tasks), `Render_done`,
   `Block.checkCommand`, `DC.check`, `Block.checkCondition`, vsync wait, `Render_swap`, `re4dc_pace_end` (29.97 Hz
   anchor clock), `systemResetCheck`.

**What an engine-owned loop must call, in order, to host the behaviour unchanged** (one tick):

| # | Engine step | Why it must be there |
|---|---|---|
| 1 | Latch input into `Joy[]` / `Key` (the arrays `PadRead` fills) | Behaviour reads the arrays, not functions (pad: 20 call sites) |
| 2 | `pG->Frame_cnt++` | Timers and scripts count ticks |
| 3 | `TaskScheduler()` (hosted `scheduler.cpp`) on engine thread primitives | Scripts wait with `TaskSleep` (133 sites); `gameMainLoop` order is the behaviour order |
| 4 | Services called synchronously from inside step 3 (skeleton, collision, effects spawn, managers) | Behaviour reads the results in the same tick |
| 5 | HUD logic (`IdSys.move`, `cMes.Move`, `CinescoMove`, `FadeControl`) or their native equivalents | Fades and messages gate events |
| 6 | Loader and sound status (`Dvd.Watcher`, `Block.check*`, `DC.check`, `SndWatcher`) at the same point in the tick | Room and event scripts poll their completion flags |
| 7 | `iTaskScheduler()` | Interrupt tasks |
| 8 | Engine draw from engine tables (no `Trans`, no OT, no GX) | Replaces step 3 of today's loop |
| 9 | Pacer: one tick a picture at 30 fps; a missed picture runs the next tick without drawing | Same rule as today's catch-up |

## 3. Memory map

**Today.** The program image is KOS's (lab33 build: `.text` 2,575,792 B, `.rodata` 298,336, `.data` 186,468,
`.re4dc_char_data` 425,280, `.bss` 1,042,016; `sh-elf-readelf -S`, `c13_elf.sh`). After it, one arena comes out of the KOS
heap: 13 MiB minus `ARENA_KOS_BYTES` (`port/dreamcast/game/platform/mem.cpp:78`, Makefile `:2727-2732`), stepped down
by 256 KiB until it fits, or to the exact fit with `ARENA_FIT=1` (`mem.cpp`, Makefile `:2733-2738`). The arena is carved
like the GameCube's fixed map (`src/game/main_mem.cpp:142-201`, `platform/mem.cpp`):

| Block (lab33, Flycast boot log `E:\RE4DC-Lanes\lab33\hayfork-repeat\boot.log:11-17,256-579`) | Bytes |
|---|---:|
| Arena (`ARENA_FIT`: request 13,578,240, fit) | 11,812,864 |
| Sound region (`SOUND_REGION_BYTES`; 374,624 used) | 393,216 |
| Core resident archive | 1,360,608 |
| Option resident | 149,920 |
| Player resident | 869,728 |
| Weapon resident | 275,424 |
| OSAlloc heaps (heap 0 at boot; heaps 1 to 4 replace each other upward) | 8,763,968 (8,558 KB) |
| Heap 4, the room heap, at r103 entry (`8c8cc140-8cfbe060`) | 7,282,464, 7,219,360 free after the room file |

Thirteen logical heaps (`include/main_mem.h` `MEM_HEAP_NUM 13`): 0 system, 1 game (`main.cpp:582`), 2 stage and 3 DLL
(`stage.cpp:242-257`), 4 room (`game.cpp:1582` `MemReplaceHeap(3, 4)`), 10 player/weapon window (`game.cpp:1585`),
11 data swap and movie (`cDataSwap.cpp:89`, `sofdec.cpp:537`, 0x500000 on the GameCube), 12 sub-screen
(`sscrn.cpp:674`). 295 `MEM_ALLOC` / `MEM_CALLOC` / `mem_alloc` sites in 191 files (`c33_spawnalloc.sh`).

**In play (console, slot 157 summaries):** heap 4 free 585,760 B at the cross, 621,472 at the bell, 1,116,640 at the
hay-fork view, 1,140,832 at the quiet farm; KOS heap free 3,200 B at the cross and 7,136 at the bell (12.0 MB used);
VRAM free 265,344 B at the cross (largest block 113,856) and 506,872 at the hay-fork view. Room-heap floor in fights:
20 to 86 KB (self-assessment 1.3).

**Who allocates.** At room entry: the room archive (`read.cpp:227,234`), the room's enemy modules and archives
(`read.cpp:722` archive, `:774` module bss, both `MEM_ALLOC(..., 1, 0xD)` into heap 4), the old port's native packs
(boot log `NMRPACK ... heap4_free=7270400->7219360`, `native model slab`). In a fight: enemy archives read on demand
(`EmSetFromList2`), effect pools (`espgen.cpp:212-305` free-size checks), weapon data (`ReadWepData`). A per-tag census
at the fight low point is **not in the evidence** (`HEAP_CENSUS=1` exists, Makefile `:1625-1628`).

**The coupling to program size.** The arena is what the KOS heap has left after the image, so with `ARENA_FIT=1` every
image byte costs heap 4 one byte, and without it a few KB more image costs a 256 KiB step (Makefile `:2733-2746`).
`IMAGE_PAD_BYTES` exists only to pin heap 4 for identity tests (Makefile `:2742-2748`).

**The logic that reads free heap.** No gameplay code reads the free byte count: `OSCheckHeap` is read only by the
exception screen (`exception.cpp:493-606`) and the failure log (`main_mem.cpp:694`). Decisions depend on whether an
allocation **succeeds**: a failed enemy module or archive allocation (`read.cpp:722,774`) means the enemy is not spawned
(`port/dreamcast/docs/D367_THIRTY_FPS_ROUTE.md:468`, em2a.drs needs 276,064 B, 81,600 free in the r100 s20 ambush);
a short heap 4 turns the scoped rifle into the plain rifle (`D367_THIRTY_FPS_ROUTE.md:448`; `re4dc_weapon_revert` is in
the E1 interface, section 5); the crow archive em23.drs did not fit by 172 KB (`D367_HANDOVER.md:86`).

**Proposed engine-owned map (estimate; sizes to be confirmed by the M0 and E1 console runs).**

| Main RAM (16,384 KiB) | KiB | Basis |
|---|---:|---|
| KOS kernel, stacks, newlib | 512 | KOS and newlib code 241 KB (lab33) plus thread stacks |
| Engine core and services (code, data) | 768 | estimate |
| Hosted behaviour code and data | 1,024 | original non-service code in lab33: 926,632 B text, 86,425 B data (`codesplit.py`) |
| Behaviour arena: fixed address and size, independent of the image | 3,072 | estimate; must hold every behaviour allocation of the worst room at cap 4 with margin; sized from a `HEAP_CENSUS` run |
| Engine room pack (world, collision, actor meshes and motions, effect data) | 4,096 | village bake 1.42 MB, farm 1.09 MB (plan section 5) plus characters |
| Engine tables (actors, effects arrays, lights, draw lists) | 512 | estimate |
| Audio (sound region) and stream buffers | 768 | 374,624 B used today plus streams |
| Movie and loading staging (reuses the room pack area during movies) | 0 | the original takes heap 11 for movies |
| Free margin | 5,632 | the GameCube-shaped resident archives (core, player, weapon: 2.5 MB) and heap-4 model, texture and motion data move into the room pack or VRAM |

| VRAM (8,192 KiB) | KiB | Basis |
|---|---:|---|
| Two frame buffers, 640x480, 16 bit | 1,200 | 614,400 B each |
| TA vertex buffers, double buffered | 2,048 | today 1,024 single (`TA_VERTBUF_KB ?= 1024`, `TA_DOUBLEBUF ?= 0`, Makefile `:2891-2892`) |
| Object pointer buffers | 320 | estimate, 16-word bins (`TA_OPB_BINS ?= 16`, `:2893`) |
| World textures (room, resident at entry) | 2,048 | estimate |
| Character textures | 1,280 | estimate |
| Effect atlas, HUD, font | 768 | estimate |
| Reserve | 528 | |

**What the behaviour must still be given so its decisions do not change.**
1. Allocation outcomes that do not depend on the engine: a behaviour arena of fixed address and size, the same 13-heap
   API (`MemCreateHeap`, `MemReplaceHeap`, `MemSetCurrentHeap`, `mem_alloc` with its heap and flag) and the same
   success or failure for every allocation the reference build makes. Where today's game relies on failure (the scoped
   rifle, a skipped enemy archive), the reference fixture names it.
2. The same random sequence. `Rnd`/`fRand*` is one global generator (`src/game/rnd.cpp`). Draws by call site
   (`c53_rng.sh`): behaviour 438, **effects 100**, skeleton 11, drawing 8, collision 5. A native service that stops
   drawing changes every later AI decision. See risk 1.
3. The same global work (`GlobalWork` 34,432 B behind `pG`) and the same actor layouts behaviour reads and writes in
   place: `cModel` 800 B, `cParts` 472, `cEm` and `cPlayer` 3,552, `cObj` 984, `cEsp` 248, `cAtariInfo` 76 (DWARF,
   `c47_dwarfsize.sh`).
4. The same tick order (section 2) and the same input per tick.

## 4. Service candidates, ranked by console cost

Each candidate is costed across rows: its simulation (Services) plus its publication plus its drawing, which is what an
engine service replaces. ms a picture, console (`service_rank.py`, output `out/services.md`).

| Rank | Service candidate | Cross | Bell fight | Hay-fork view | Quiet farm | Functions |
|---:|---|---:|---:|---:|---:|---:|
| 1 | Drawing: characters (publication, skin, submit) | <!-- gate svc.drawing_characters_publication_skin_submit.cross=12.6 -->12.6 | 16.2 | <!-- gate svc.drawing_characters_publication_skin_submit.hayfork=36.1 -->36.1 | 8.0 | 265 |
| 2 | Drawing: world (selection, transform, submit) | <!-- gate svc.drawing_world_selection_transform_submit.cross=13.5 -->13.5 | 13.2 | 10.9 | 3.7 | 76 |
| 3 | Skeleton, pose and skin palette | <!-- gate svc.skeleton_pose_and_skin_palette.cross=5.6 -->5.6 | 6.6 | 14.3 | 7.0 | 74 |
| 4 | Collision queries | <!-- gate svc.collision_queries.cross=5.5 -->5.5 | 6.5 | 6.7 | 3.2 | 67 |
| 5 | Effects (simulation, transform, drawing) | <!-- gate svc.effects_simulation_transform_drawing.cross=4.8 -->4.8 | 4.3 | 9.5 | 3.7 | 89 |
| 6 | Lights (simulation, setup, light kernels) | 2.7 | 3.2 | 4.7 | 1.8 | 38 |
| 7 | HUD (logic and drawing) | 2.0 | 2.4 | 2.4 | 1.6 | 76 |
| 8 | Actor and object managers | 1.0 | 0.8 | 1.1 | 0.6 | 23 |
| 9 | Ordering tables and GX translation | 0.9 | 0.8 | 1.1 | 0.5 | 32 |
| 10 | Enemy body services | 0.1 | 0.2 | 0.3 | 0.1 | 15 |
| | Helpers whose caller is a helper | 1.0 | 0.9 | 1.2 | 0.6 | 45 |

Function lists: `out/services.md` (top ten each, with row) and `out/rowfuncs.tsv` (all).

| Service | Interface behaviour calls (E1 player closure, section 5; all game: `boundary-funcs.tsv`) | Data it owns | Tangle with behaviour |
|---|---|---|---|
| Drawing (characters, world) | None directly: today reached through `Trans` and the per-model trans function | World bake, actor meshes, textures, draw lists | Reads `cModel` position, parts matrices and display flags of every alive unit (`trans.cpp:1403-1441`) |
| Skeleton and pose | 44 in E1: `MotionSetCore`, `MotionMove`, `MotionBlendOff`, `MotionGetSpeed`, `MotionCheckCrossFrame`, `PartsWorldPosCalc`, `HermiteInterpolation`, `ShapeSet/Move/End`, `PlClothSetLeon`, `cModel::motionSet/motionMove/partsWorldCalc/getPartsPtr/updateOldPos/setPos/setAng/partsFixAdjust`, `cMotBase::set/move/adjust`, `getBoundingBox` | Motion data, part hierarchy, part local and world matrices, skin palette | `cModel` (800 B) and its `cParts` chain (472 B a part) are behaviour structs: `cModel` is named in 370 files, 243 of them behaviour; AI reads part world positions (hands, head) |
| Collision queries | 21 in E1: `cSatMgr::hitCheck/getFloor/check`, `ObjHitCheck`, `EmAtCheck`, `EmHitCheck`, `cAtariInfo::init/set/move/setPriority`, `cubeMemoCk`, `YarareAdd`, `EatGetEffectType`; globals `SatMgr`, `EatMgr` | Room SAT/EAT triangles and grids, per-actor volumes | `cAtariInfo` (76 B) lives in the actor; named in 61 files, 48 behaviour; results are used in the same move |
| Effects | 10 in E1 (`EspDataLoad`, `QuakeInit/Move`, water and sand power, `GetWaterHeight`); 78 in the variant-A closure (`EspSet*`, `Efm*`, `EspGenLoopMove`) | About 400 live effects (`fx_live` 361 to 427, console) | `cEsp` (248 B) named in 66 files, 6 behaviour; **100 RNG draws** in effect files |
| Lights | 3 in E1 (`LightMgr`, `cLightMgr::update`, `cLightInfo::init2`) | Room lights, light areas | `cLight` (468 B) named in 52 files, 16 behaviour |
| HUD | 14 in E1 (`Cckpt`, `Cockpit::lifeMeterDisp`, `IDSystem::set/kill/unitPtr`, `MessageControl::MesSet`, `cMes`, `eprintf`) | Id units, message state | Behaviour writes id units directly (`IdSys`) |
| Managers | 15 in E1 (`EmMgr`, `ObjMgr`, `cEm::setStatus/clearStatus/checkStatus`, `cEmMgr::destroy/isBattle`, `cObjMgr::destroy`, `cDmgInfo::*`, `pPL`, `pSUB`) | Alive lists, work arrays | `cEm`/`cObj` named in 275 / 251 files; the alive lists are walked by behaviour and by `Trans` |
| Enemy body | Route and look-at helpers called from `em10` (`getNearPoint`, `RouteCk`, `em10NeckMove`) | Route nodes | Inside the enemy files; cheap (0.1 to 0.3 ms) |

Type reference counts: `c45_tangle.sh` (files outside `src/lib` and `include/dolphin` that name the type; "behaviour"
= `src/em*`, `src/pl*`, `src/wep*`, `src/st*`, `src/Sscrn` and the player, enemy, object, event, camera, game and
stage files of `src/game`).

## 5. M2 design: the smallest engine shell for the village and the farm

### What E1 needs from the original code (link closure, lab33 build)

Seeds: the player and its camera, `src/game/player.cpp pl_class pl_body pl_sub pl_leon pl_wep pl_dmg pl_push pl_knife
pl_debug pl_event cam_ctrl cam_sys cam_qfps cam_extra cam_motion camera view` and `src/wep/pl_handgun.cpp` (19 files).
Edges: every symbol named by an instruction (`bsr`, constant-pool loads for `jsr` and data) plus every function address
stored in a data object (vtables, `Pl_func_tbl`, task tables), from `sh-elf-objdump` of the lab33 ELF (`callgraph.py`,
53,060 edges). A reference into a file the engine replaces (closure.py STOP: drawing, skeleton, collision, effects, lights,
memory, files, audio, pad, card, math, libc, HUD and 2D, debug tools, managers, main loop) is an engine interface, not
followed.

| Variant | Files linked | Code | Data and bss |
|---|---:|---:|---:|
| B: other behaviour domains stubbed (enemies, events, rooms, objects, items, menus), functions as `--gc-sections` keeps them | <!-- gate closure.B.fn.files=22 -->22 | <!-- gate closure.B.fn.code=103856 -->103,856 B | <!-- gate closure.B.fn.data=17678 -->17,678 B |
| B, whole files | 22 | <!-- gate closure.B.file.code=104364 -->104,364 B | 17,678 B |
| A: stop only at engine services, functions | <!-- gate closure.A.fn.files=131 -->131 | <!-- gate closure.A.fn.code=788736 -->788,736 B | 82,915 B |
| A, whole files | <!-- gate closure.A.file.files=135 -->135 | <!-- gate closure.A.file.code=914724 -->914,724 B | 83,219 B |

- **Variant B pulls in only `rnd.cpp`** (and inline bodies of `player.h`, `pl_wep.h`). Largest seeds: `cam_ctrl.cpp`
  18,896 B, `player.cpp` 14,848, `pl_class.cpp` 10,942, `cam_qfps.cpp` 9,614 (`closure.py`, `out/closure.md`).
- **Its engine interface is 175 functions and globals:** skeleton 44, math 26, collision 21, managers 15, HUD and 2D 14,
  debug 12, effects 10, main loop globals 10 (`Joy`, `Key`, `pG`, `pSys`, ortho and clip constants), files 7,
  drawing 6 (filter flags), lights 3, memory 3, audio 2, pad 1, card 1. Plus 72 stubs into other behaviour (26,275 B of
  code behind them: `ActBtn`, `DmgMgr`, water and window checks, events) and 23 hooks of the old port that compile out
  with the `RE4DC_` knobs off. Full list: `out/closure-iface-B.tsv`.
- **Variant A** shows the tangle: through the player, 112 more files come in, including 17 enemy modules (`src/em10` to `src/em2e`), every
  `em*.cpp` object type, `event.cpp`, `dmg.cpp`, `ctrl*.cpp` and `EtcModel.cpp`.
- Limits: calls through a pointer computed at run time are missed; the lab33 objects carry the old port's patches,
  so the sizes are an estimate of an engine build.

### Engine tables and thin setters

The behaviour cannot be changed, so its structs are the setters: the engine's actor table **is** an array of
`cModel`-layout records (with `cParts` chains) that the behaviour writes in place, and the engine reads them in place.
"Thin setter" means the original methods that already write those fields (`cModel::setPos`, `setAng`, `motionSet`) and
the engine functions that replace the service calls above. Nothing converts a behaviour object into a draw object.

| Slice | Engine tables | Setters the hosted behaviour calls (original names, engine bodies) | Original code NOT linked (engine replaces it) |
|---|---|---|---|
| **E1 Leon** | Actor table (`cModel` records: Leon, his weapon); skeleton state (motion, frame, blend) written by `MotionSetCore`/`MotionMove` and evaluated once into `cParts` world matrices and the skin palette; collision tables (room SAT/EAT in engine form, `cAtariInfo` volumes); camera (view matrix written by the hosted camera); HUD table (life, ammo, reticle) read by a native HUD; effect arrays (muzzle flash, hit spark, shell) | The 175 interface functions above, chiefly: skeleton 44, collision 21, managers 15, HUD 14, effects 10, files 7 (`ReadPlayerData`, `ReadWepData`: served from the room pack), memory 3 (`mem_alloc`, `Mem_free`, `new` on the behaviour arena), audio 2 (`SndCall`, `SndStop`) | `trans.cpp`, `trans_lit.cpp`, `trans_ot.cpp` (`Trans`, `ModelTrans`, `ModelRender`, `LightSetModel`, OT), `motion.cpp`, `ik.cpp`, `model.cpp` skeleton bodies, `atari.cpp`, `at_mod.cpp`, `at_sub*.cpp`, `light*.cpp` set-up, `esp*.cpp` trans paths, `gx_stub.cpp`, `main.cpp` loop, `main_mem.cpp` arena carve; the old port's publication code (`native_actor_fast.cpp`, `coarse_actor*`, `native_actor_owner*`, `model_bridge.cpp`, the model and world paths of `native_ui.cpp` and `native_static.cpp`) |
| **E2 fight** (four Ganados) | E1 plus: four more actor rows and their weapons; enemy collision volumes; effect arrays for blood, fire, hit marks with their own simulation; damage records (`cDmgInfo`); route nodes | E1 plus the hosted `src/em10/em10.cpp`, `em_set.cpp` (spawn lists, cap 4 `aliveCapLive`), `em_sub.cpp`, `dmg.cpp`, `em.cpp` base methods; spawn and kill through `cEmMgr::construct` / `destroy` on the actor table; effect spawn through `EspSet*` on engine arrays | E1 plus the effect simulation bodies (`EspMove`, `cEsp*::move`, `EspCommonTrans`, `Ps2fx*`) and `cObjMgr`/`cEmMgr` list walks (engine managers) |

### Build layout

- `port/dreamcast/engine/` (from eng-bench): `core/` (loop, pacer, memory map, loader, audio, input, QA link),
  `services/` (skeleton, collision, effects, lights, HUD, managers, renderer), `host/` (adapters: heap API, thread
  primitives for `scheduler.cpp`, `Joy`/`Key`, file and sound adapters, debug no-ops), `game/` (the hosted original
  file list, built with every `RE4DC_` knob off so the 2,537 guard lines and 1,802 hook calls compile out).
- One image: engine plus the hosted list. The bench image stays engine only.
- Deleted from the old port: all of `port/dreamcast/game` (466 files, 136,172 lines, 1,201 knobs) except what moves
  into `core/`: the KOS audio driver (`audio_aica.cpp`), VMU card (`card.cpp`, `vmu_store.cpp`), disc (`gdrom_mount.cpp`,
  `dvd.cpp`), pad, QA link, PC sampler.

### Order

1. **Core (with E0):** loop of section 2, behaviour arena and 13-heap API, thread primitives for `TaskScheduler`,
   `rnd.cpp` hosted, input arrays, room-pack loader that also serves `ReadPlayerData`/`ReadWepData`.
2. **Actor table and skeleton** (`cModel` records, native motion and parts evaluation, skin palette written once).
3. **Collision** on engine tables behind the 21 E1 entry points.
4. **Player hosted** (19 files), camera and aiming, native HUD, minimal effects with RNG preserved: E1 console run.
5. **E2:** `em10` and its spawn, damage and route files hosted; effects simulation native; managers native; the fight at
   cap 4: E2 console run at the cross, bell, hay-fork and quiet farm.

### The three biggest risks

| Risk | How it would show up |
|---|---|
| **1. Shared random numbers and allocation outcomes.** Effects (100 draws), skeleton (11), drawing (8) and collision (5) take numbers from the one generator the AI uses; heap-4 failures decide spawns and the scoped rifle | The plays-right fixture diverges on the first enemy decision after an effect spawns (the `r=` RNG field of the logic trace, `logic_trace.cpp`, moves first); or an enemy appears or not at a different tick than the reference |
| **2. Publication returns by the back door.** Behaviour owns `cModel`/`cEm`/`cParts` in place; if services and the renderer convert those records each tick instead of reading them, the 8.7 to 31.4 ms row comes back under another name | E1 console profile: functions that read `cModel` fields to fill engine records above 1 ms a picture; Publication row not near 0 |
| **3. Services stay synchronous inside behaviour.** Skeleton and collision are called mid-move and their results used at once (today 6.7 ms a tick for those two at the cross), so they cannot simply be batched or deferred | Services row over 6 ms a tick on console at E2, with the cost spread over many short calls from `pPL->move` and `EmMgr.move` |

## 6. Proving a service plays the same

The first three services after drawing, by console cost: skeleton, collision, effects.

| Service | Record at the boundary (per tick) | Tolerance | Failing control |
|---|---|---|---|
| **Skeleton and pose** | Per actor: motion id, state, frame and speed (`Mot_state`, `Mot_frame`), blend; every `cParts` world matrix; `PartsWorldPosCalc` results the behaviour asked for; events fired by `MotionCheckCrossFrame` | Discrete fields and fired events exact; joint positions within 1 mm, rotations within 0.1 degree (estimate, to be agreed before the checkpoint) | Advance one actor's motion frame by one tick, or feed IK a target 10 mm off: the frame field and the crossing events must mismatch |
| **Collision queries** | Each query in call order: kind (`hitCheck`, `getFloor`, `ObjHitCheck`, `EmAtCheck`), inputs, result (hit, attribute, polygon or actor id), hit point and normal | Hit or miss, attributes and ids exact (collision results never change); points within 0.01 mm of the reference | Raise one floor triangle 1 mm, or drop one wall triangle: the hit list must differ at the first query that touches it |
| **Effects** | Spawn and kill events (type, owner, tick), live count, every effect-to-game call (damage, `EspSetEatEffect`, water hits), RNG state before and after the effect step | Spawn and kill order exact for effects that touch game state; visual-only effects: counts within the density cap, look by still pairs; RNG state exact (risk 1) | Drop one spawn, or delay one kill by a tick: the event list and the RNG state must mismatch |

**Tools that exist.**
- The logic trace (`port/dreamcast/game/logic_trace.cpp`, `LOGIC_TRACE=1`): one line a tick with the RNG state, player
  and enemy discrete state, coordinate and parts hashes, compared by `tools/logic_trace_diff.py`. It has a timing
  control (`RE4DC_LOGIC_TRACE_DELAY_US`). It records whole-game state, so it finds the tick; boundary records find the
  call.
- A host (PC) build of original code: `port/dreamcast/Makefile.host` builds asset tools, the ABI probe and tests, not
  the behaviour. But `tools/motion/host/Makefile:8-18` already compiles the game's own `motion.cpp`, `ik.cpp` and the
  `cModel::partsMatCalc/partsWorldCalc/getPartsPtr` bodies for the PC with stubs: the reference for the skeleton check
  exists.
- **A host build of the E1 behaviour is feasible:** 22 files, about 104 KB of code, against 175 interface functions and
  72 behaviour stubs (section 5). The same files compiled for the PC against a recording of the console engine's service
  results replay the player and give the reference for the plays-right gate.

## 7. Checks and what is not answered

**Gate.** `python3 gate_doc.py SHELL_MAP.md`: every `<!-- gate -->` number re-derived from the scripts' outputs.
Control: `python3 gate_doc.py --control SHELL_MAP.md` changes the cross Publication value by 1.0 ms in a copy and the gate
reports the mismatch. The row rules have their own control: `classify_rows.py --control` moves `EspTrans` into
Behaviour and the cross Behaviour value moves from 1.6 to 2.4 ms. `closure.py --control` drops `pl_handgun.cpp` from
the seeds and the variant-B closure shrinks from 22 files and 103,856 B of code to 21 files and 99,980 B.

**Not answered from the evidence.**
- Worst interval and p99 per row: the sampler gives about 55 samples a picture, too few to split a single picture
  by row; the rows are means over 6 s.
- Heap 4 contents by tag at room entry and at the fight low point (needs a `HEAP_CENSUS=1` run): the behaviour arena's
  3 MiB is an estimate.
- The split of today's heap-4 bytes between behaviour data and model, texture and motion data, so the engine's main RAM
  map is an estimate.
- A current VRAM map document (`VRAM-MAP-*.md`) is not in the repository; the VRAM proposal starts from the console's
  free-VRAM counters and the TA settings.
- Calls through run-time function pointers in the closure (only pointers stored in data objects are followed).
- The engine build's own sizes: closure sizes are from the lab33 build with the old port's patches compiled in.
